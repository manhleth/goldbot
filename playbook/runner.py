"""Chạy backtest từng phương pháp sổ tay trên dữ liệu cache, ghi journal (mỗi phương pháp một run)."""
from __future__ import annotations

import dataclasses
import json
import logging
from collections.abc import Callable
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

from core.timeframes import TF_MINUTES, tf_delta
from core.types import Direction
from data.candles import resample
from data.history import cache_path, load_csv, load_spec, spec_path
from journal.db import Journal
from playbook import chart_svg
from playbook import indicators as ind
from playbook.bias import apply_bias, load_bias
from playbook.common import MarketData
from playbook.learning import gate, paper_trade
from playbook.methods_box import xau05, xau06, xau08, xau09
from playbook.methods_range import channel_edge, range_sweep
from playbook.methods_rsi import rsi_inertia
from playbook.methods_indicator import xau01, xau02, xau03, xau04, xau10, xau11, xau12
from playbook.methods_structure import xau13
from playbook.methods_trendline import tl_bounce, tl_retest
from playbook.methods_unified import unified
from playbook.patterns import patterns
from playbook.orders import Order, Signals
from playbook.portfolio import Limits, simulate
from playbook.simulator import Bars, OrderSimulator, Outcome, TrailSeries
from risk.sizing import SymbolSpec, capped, cent_account
from stats.metrics import summarize, wilson_interval

log = logging.getLogger(__name__)

METHODS: dict[str, Callable[[MarketData, dict], Signals]] = {
    "xau01": xau01, "xau02": xau02, "xau03": xau03, "xau04": xau04, "xau05": xau05, "xau06": xau06,
    "xau08": xau08, "xau09": xau09, "xau10": xau10, "xau11": xau11, "xau12": xau12, "xau13": xau13,
    "tl_bounce": tl_bounce, "tl_retest": tl_retest, "patterns": patterns, "unified": unified,
    "channel_edge": channel_edge, "range_sweep": range_sweep, "rsi_inertia": rsi_inertia,
}
HIGHER = ("M15", "M30", "H1", "H2", "H4", "D1")


def load_playbook(path: Path) -> dict:
    pb = yaml.safe_load(path.read_text(encoding="utf-8"))
    unknown = [name for name, p in pb["methods"].items() if p.get("fn", name) not in METHODS]
    if unknown:
        raise ValueError(f"playbook.yaml có phương pháp chưa cài đặt: {unknown}")
    return pb


def load_market(cfg: dict, base: str = "M5", path: Path | None = None) -> tuple[MarketData, Bars, SymbolSpec]:
    """Nến khung gốc từ cache (hoặc `path`); các khung lớn hơn gộp từ khung gốc theo giờ UTC (quy ước của sổ tay)."""
    cache_dir = Path(cfg["data"]["cache_dir"])
    raw = load_csv(path or cache_path(cache_dir, cfg["symbol"], base), base)
    spec = load_spec(spec_path(cache_dir, cfg["symbol"]), cfg)
    data, bars = build_market(raw, base, cfg, spec)
    return data, bars, spec


def build_market(raw: pd.DataFrame, base: str, cfg: dict, spec: SymbolSpec,
                 now: pd.Timestamp | None = None) -> tuple[MarketData, Bars]:
    """Khung gốc + các khung lớn hơn gộp theo giờ UTC; dùng chung cho backtest và live.

    Live truyền `now`: bỏ nến khung lớn chưa đóng (gộp từ khung gốc nên nến cuối có thể còn dở).
    Có file cache `<symbol>_D1_long.csv` (lệnh `history --tf D1`) thì thêm khung `D1_long` — lịch sử D1 dài cho các
    phân tích dài hạn (playbook/macro.py), vì cửa sổ dữ liệu live chỉ khoảng một năm.
    """
    frames = {base: raw, **{tf: resample(raw, tf) for tf in HIGHER if TF_MINUTES[tf] > TF_MINUTES[base]}}
    long_d1 = Path(cfg["data"]["cache_dir"]) / f"{cfg['symbol']}_D1_long.csv"
    if long_d1.exists():
        frames["D1_long"] = load_csv(long_d1, "D1")
    if now is not None:
        frames = {tf: df[df["close_time"] <= now].reset_index(drop=True) for tf, df in frames.items()}
    bars = Bars.from_frame(raw, spec.point, cfg["backtest"]["default_spread_points"], tf_delta(base))
    return MarketData(frames, cfg["sessions"]["timezone"], spec.point, base), bars


def build_trail(data: MarketData, bars: Bars, tc: dict) -> TrailSeries:
    """Mức SL theo swing khung `tc.tf` (n trái / n phải), lùi thêm `buffer_atr` × ATR; biết được từ lúc swing xác nhận."""
    df = data.frame(tc["tf"])
    n = tc["swing"]
    is_high, is_low = ind.fractal_swings(df, n, n)
    atr = ind.atr(df, tc["atr"]).to_numpy(float)
    bar_times = pd.DataFrame({"time": pd.to_datetime(bars.time, utc=True)})
    level, confirmed = {}, {}
    for d, mask, col in ((Direction.BUY, is_low, "low"), (Direction.SELL, is_high, "high")):
        s = np.flatnonzero(mask[: len(df) - n])
        conf = s + n
        swings = pd.DataFrame({"time": pd.DatetimeIndex(df["close_time"].to_numpy()[conf]).as_unit("ns"),
                               "level": df[col].to_numpy(float)[s] - d * tc["buffer_atr"] * atr[conf]})
        merged = pd.merge_asof(bar_times, swings.dropna().assign(at=lambda x: x["time"]), on="time",
                               direction="backward")
        level[d] = merged["level"].to_numpy(float)
        confirmed[d] = np.where(merged["at"].isna(), -1,
                                np.searchsorted(bars.time, merged["at"].fillna(pd.Timestamp(0, tz="UTC"))
                                                .dt.as_unit("ns").astype("int64").to_numpy(), side="left"))
    return TrailSeries(level, confirmed)


def trail_tfs(variant: dict | None, data: MarketData | None = None) -> list[str]:
    """Các khung dời SL của biến thể; có `data` thì bỏ khung nhỏ hơn khung gốc (không có dữ liệu, vd M5 khi gốc M15)."""
    if not variant or not variant.get("trail"):
        return []
    tf = variant["trail"]["tf"]
    tfs = list(tf) if isinstance(tf, list) else [tf]
    return [t for t in tfs if data is None or t in data.frames]


def trail_key(name: str, tf: str) -> str:
    return f"{name}@{tf}"


def _order_tf(order: Order) -> str | None:
    cls = order.key.split(":")[1] if order.key.count(":") >= 1 else ""
    return cls.split("@")[1] if "@" in cls else None


def _nearest_trail(tf: str | None, tfs: list[str]) -> str:
    """Khung dời SL cho lệnh khung `tf`: chính nó nếu có; không thì khung lớn nhất ≤ tf (vd D1 → H4); không rõ → khung đầu."""
    if tf in tfs:
        return tf
    if tf in TF_MINUTES:
        smaller = [t for t in tfs if TF_MINUTES.get(t, 0) <= TF_MINUTES[tf]]
        if smaller:
            return max(smaller, key=lambda t: TF_MINUTES[t])
    return tfs[0]


def apply_variant(orders: list[Order], variant: dict | None, name: str | None) -> list[Order]:
    """Biến thể quản lý lệnh dùng chung cho mọi phương pháp: bỏ TP cố định, dời SL theo cấu trúc.

    Có nhiều khung dời SL thì mỗi lệnh dùng khung của chính mẫu hình (`loại@khung` trong khoá), nếu không thì khung đầu.
    """
    if not variant:
        return orders
    tfs = trail_tfs(variant)
    out = []
    for o in orders:
        changes: dict = {}
        if not variant.get("take_profit", True) and not o.meta.get("keep_tp"):  # keep_tp: phương pháp tự đặt TP
            changes.update(tp=None, tp_dist=None)
            if not variant.get("keep_partial"):  # keep_partial: giữ chốt một phần (vd tại vùng S/R cứng)
                changes["tp1_dist"] = None
        if tfs and name:
            tf = o.meta.get("trail_tf") or _order_tf(o)  # trail_tf: phương pháp chọn khung gồng riêng (vd D1)
            changes["trail"] = trail_key(name, _nearest_trail(tf, tfs))
        out.append(dataclasses.replace(o, **changes))
    return out


def trade_row(run_id: str, name: str, o: Outcome, spec: SymbolSpec) -> dict:
    risk = o.risk
    return {
        "run_id": run_id, "setup_key": o.order.key, "setup": name, "direction": o.order.direction.name,
        "bias": "", "score": 0, "entry_time": o.entry_time, "exit_time": o.end, "entry": o.entry, "sl": o.sl,
        "tp1": o.tp1 if o.tp1 is not None else o.tp, "tp2": o.tp if o.tp1 is not None else None,
        "volume": o.volume, "r_multiple": o.r_multiple(), "pnl": spec.money(o.price_pnl(), 1.0),
        "exit_reason": o.exit_reason, "mae_r": o.mae / risk if risk else 0.0, "mfe_r": o.mfe / risk if risk else 0.0,
        "spread_entry": o.spread / spec.point, "news": "none", "reasons": list(o.order.reasons),
        "meta": json.dumps({k: v for k, v in o.order.meta.items() if k != "edges"}) if o.order.meta else None,
    }


def save_chart(outcome: Outcome, data: MarketData, folder: Path, title: str) -> str | None:
    """Chart lý do vào lệnh (SVG) cho lệnh có hình học mẫu hình; trả đường dẫn hoặc None."""
    meta = outcome.order.meta
    if not meta.get("tf") or meta["tf"] not in data.frames:
        return None
    view = chart_svg.TradeView(int(outcome.order.direction), outcome.entry_time, outcome.entry, outcome.sl, outcome.end,
                               outcome.legs[0].exit_price, outcome.r_multiple(), title, outcome.order.reasons, meta)
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / (outcome.order.key.replace(":", "_").replace("@", "-") + ".svg")
    path.write_text(chart_svg.render(data.frames[meta["tf"]], view), encoding="utf-8")
    return str(path)


def signal_row(run_id: str, name: str, o: Outcome) -> dict:
    order = o.order
    return {
        "run_id": run_id, "time": order.time, "setup": name, "direction": order.direction.name, "bias": "",
        "zone_low": None, "zone_high": None, "score": 0, "trigger": order.kind, "entry": order.price,
        "sl": order.sl, "tp1": order.tp, "tp2": None, "rr_tp1": None, "accepted": int(o.status == "filled"),
        "reject_reason": None if o.status == "filled" else (o.reason or o.status), "news": "none",
        "reasons": list(order.reasons), "setup_key": order.key,
        "meta": json.dumps({**order.meta, "sl_dist": order.sl_dist}) if order.meta else None,
    }


def _equity_rows(run_id: str, trades: list[dict], initial: float) -> list[dict]:
    rows, equity, peak = [], initial, initial
    for trade in sorted(trades, key=lambda r: r["exit_time"]):
        equity += trade["pnl"]
        peak = max(peak, equity)
        rows.append({"run_id": run_id, "time": trade["exit_time"], "equity": equity,
                     "drawdown_pct": (equity - peak) / peak * 100 if peak > 0 else 0.0})
    return rows


def run_method(name: str, pb: dict, cfg: dict, data: MarketData, bars: Bars, spec: SymbolSpec,
               start: pd.Timestamp, end: pd.Timestamp, journal: Journal, variant: str | None = None,
               trails: dict[str, TrailSeries] | None = None, bias: dict | None = None) -> dict:
    p = {**pb["common"], **pb["methods"][name], "code": name}
    p["initial_equity"] = p["initial_equity"] * p.get("capital_share", 1.0)  # bot chỉ dùng phần vốn được chia
    v = pb["variants"][variant] if variant else None
    signals = METHODS[p.get("fn", name)](data, p)  # `fn`: dùng lại hàm của phương pháp khác với tham số riêng
    history = apply_variant([o for o in signals.orders if o.time < end], v, variant)
    orders = [o for o in history if o.time >= start]
    spec = capped(spec, p.get("max_lot"))  # lot tối đa mỗi lệnh của phương pháp
    sim = OrderSimulator(bars, spec, p["risk_per_trade_money"], cfg["backtest"]["slippage_points"], signals.events,
                         trails, bool(p.get("min_lot_fallback")))
    rejected: list[Outcome] = []
    if bias is None and p.get("channel_bias"):  # bộ lọc hướng khai báo trong chính phương pháp
        fb = cfg["feeds"]["bias"]
        bias = {**p["channel_bias"], "series": load_bias(cfg["feeds"]["db"], fb["channel"], fb["symbol"])}
    if bias:  # chỉ dùng HƯỚNG nhận định của channel làm bộ lọc
        orders, dropped = apply_bias(orders, bias["series"], bias["valid_days"], bias["mode"])
        rejected += dropped
    if p.get("learning"):  # kinh nghiệm = kết quả nháp của mọi tín hiệu trước đó (kể cả trước `start`)
        experience = paper_trade(history, sim)
        orders, gated = gate(orders, experience, p["learning"])
        rejected += gated
        for cls, (n, e) in experience.summary().items():
            print(f"    kinh nghiệm {cls:24s} {n:4d} lệnh nháp, trung bình {e:+.3f}R", flush=True)
    outcomes = simulate(orders, sim, Limits.from_params(p), spec, cfg["sessions"]) + rejected
    run_cfg = {**cfg, "backtest": {**cfg["backtest"], "initial_equity": p["initial_equity"]}, "playbook": p}
    title = p["title"] + ("" if data.base == "M5" else f" [nền {data.base}]") + (f" · {v['title']}" if v else "") +         (f" · hướng channel {bias['mode']} {bias['valid_days']}d" if bias else "")
    run_id = journal.create_run("backtest", {**run_cfg, "variant": v}, {
        "start": str(start), "end": str(end), "method": name, "title": title, "base": data.base, "variant": variant})
    filled = [o for o in outcomes if o.status == "filled"]
    trades = [trade_row(run_id, name, o, spec) for o in filled]
    chart_dir = Path(cfg["journal"]["backtest_db"]).parent / "charts" / run_id
    for row, outcome in zip(trades, filled):
        row["chart"] = save_chart(outcome, data, chart_dir, title)
    journal.insert("trades", trades)
    journal.insert("signals", [signal_row(run_id, name, o) for o in outcomes])
    journal.insert("equity", _equity_rows(run_id, trades, p["initial_equity"]))
    return summary_row(name, {**p, "title": title}, run_id, trades, len(outcomes), start, end)


def summary_row(name: str, p: dict, run_id: str, trades: list[dict], n_orders: int,
                start: pd.Timestamp, end: pd.Timestamp) -> dict:
    row = {"method": name, "title": p["title"], "run_id": run_id, "orders": n_orders, "trades": len(trades)}
    if not trades:
        return row
    df = pd.DataFrame(trades).sort_values("exit_time")
    r, pnl = df["r_multiple"].to_numpy(float), df["pnl"].to_numpy(float)
    s = summarize(r)
    equity = p["initial_equity"] + np.cumsum(pnl)
    peak = np.maximum.accumulate(np.concatenate([[p["initial_equity"]], equity]))[1:]
    mid = start + (end - start) / 2
    entry = pd.to_datetime(df["entry_time"], utc=True)
    halves = [df.loc[entry < mid, "r_multiple"], df.loc[entry >= mid, "r_multiple"]]
    lo, hi = wilson_interval(s["wins"], s["trades"])
    row.update(winrate=s["winrate"], wr_lo=lo, wr_hi=hi, expectancy_r=s["expectancy_r"],
               profit_factor=s["profit_factor"], net=float(pnl.sum()), max_dd_pct=float(((peak - equity) / peak).max() * 100),
               e_first=float(halves[0].mean()) if len(halves[0]) else None,
               e_second=float(halves[1].mean()) if len(halves[1]) else None)
    return row


def apply_overrides(pb: dict, names: list[str], capital: float | None, risk: dict[str, float] | None,
                    capital_by: dict[str, float] | None = None, extra: dict[str, dict] | None = None) -> dict:
    """Ghi đè vốn: `capital` = toàn tài khoản (mỗi phương pháp vẫn nhân `capital_share`), `capital_by` = vốn riêng từng
    phương pháp (bỏ `capital_share`); và % rủi ro từng phương pháp."""
    methods = {name: dict(pb["methods"][name]) for name in names}
    for name, m in methods.items():
        notes = []
        if capital_by and name in capital_by:
            m["initial_equity"], m["capital_share"] = float(capital_by[name]), 1.0
            notes.append(f"vốn {capital_by[name]:g}$")
        elif capital is not None:
            m["initial_equity"] = float(capital)
            notes.append(f"vốn {capital:g}$ × {m.get('capital_share', 1.0):g}")
        if risk and name in risk:
            m["risk_pct"] = float(risk[name])
            notes.append(f"rủi ro {risk[name]:g}%")
        for key, value in ((extra or {}).get(name) or {}).items():  # max_lot, risk_caps
            m[key] = value
            if value:
                notes.append(f"lot tối đa {value:g}" if key == "max_lot" else
                             "chặn rủi ro " + ", ".join(f"≥{c[0]:g}$→{c[1]:g}%" for c in value))
        if notes:  # tên lần chạy ghi đúng thông số đã ghi đè (tiêu đề gốc có thể ghi % rủi ro của config)
            m["title"] = f"{m.get('title', name)} [{', '.join(notes)}]"
    return {**pb, "methods": {**pb["methods"], **methods}}


def run_playbook(cfg: dict, pb_path: Path, start: pd.Timestamp, end: pd.Timestamp,
                 only: list[str] | None = None, base: str = "M5", data_path: Path | None = None,
                 variant: str | None = None, bias: dict | None = None, capital: float | None = None,
                 risk: dict[str, float] | None = None, capital_by: dict[str, float] | None = None,
                 extra: dict[str, dict] | None = None, cent_scale: float | None = None) -> list[dict]:
    """`cent_scale` (vd 0.01): backtest như tài khoản cent — lot tính theo lot cent, `max_lot` (lot thường) quy đổi."""
    pb = load_playbook(pb_path)
    data, bars, spec = load_market(cfg, base, data_path)
    v = pb["variants"][variant] if variant else None
    trails = {trail_key(variant, tf): build_trail(data, bars, {**v["trail"], "tf": tf}) for tf in trail_tfs(v, data)} or None
    if bias:
        fb = cfg["feeds"]["bias"]
        bias = {**bias, "series": load_bias(cfg["feeds"]["db"], fb["channel"], fb["symbol"])}
    names = only or list(pb["methods"])
    pb = apply_overrides(pb, names, capital, risk, capital_by, extra)
    if cent_scale:
        spec = cent_account(spec, cent_scale)
        for name in names:
            m = pb["methods"][name]
            if m.get("max_lot"):
                m["max_lot"] = m["max_lot"] / cent_scale
            m["title"] = f"{m.get('title', name)} [tài khoản cent, lot = lot cent]"
    rows = []
    with Journal(cfg["journal"]["backtest_db"]) as journal:
        for name in names:
            log.info("Phương pháp %s", name)
            rows.append(run_method(name, pb, cfg, data, bars, spec, start, end, journal, variant, trails, bias))
            print(format_row(rows[-1]), flush=True)
            print(f"Run: {rows[-1]['run_id']}", flush=True)
    return rows


def format_row(row: dict) -> str:
    head = f"{row['title'][:44]:44s} lệnh={row['trades']:4d}"
    if not row["trades"]:
        return head + f"  (tín hiệu={row['orders']})"
    pf = row["profit_factor"]
    halves = "/".join("—" if v is None else f"{v:+.2f}" for v in (row["e_first"], row["e_second"]))
    return (head + f"  WR={row['winrate']:.0%} ({row['wr_lo']:.0%}–{row['wr_hi']:.0%})"
            f"  E={row['expectancy_r']:+.3f}R  PF={'∞' if pf is None else f'{pf:.2f}'}"
            f"  lãi={row['net']:+8.2f}$  DD={row['max_dd_pct']:.1f}%  E(nửa đầu/sau)={halves}")
