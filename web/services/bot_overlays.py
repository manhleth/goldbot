"""Lớp vẽ của bot trên chart chính — đúng code bot dùng: vùng S/R cứng (playbook/sr_zones.py), trendline đa tỉ lệ
đang hiệu lực / vừa bị phá còn trong cửa sổ retest (playbook/tl_scales.py), cạnh mẫu hình của các tín hiệu đã quét.
Thời gian trả về là Unix giây UTC."""
from __future__ import annotations

import json
import threading
import time
from pathlib import Path

import pandas as pd

from core.timeframes import tf_delta
from data.history import load_spec, spec_path
from playbook import indicators as ind
from playbook.common import MarketData
from playbook.runner import build_market, load_playbook
from playbook.sr_zones import current_zones, weekly, zone_frame
from playbook.trendlines import Line, LineRules, build
from web.services.mt5_gateway import MT5Gateway
from web.services.signal_chart import BASE_TF, base_frame


def _ts(t) -> int:
    return int(pd.Timestamp(t).timestamp())


TF_RANK = {"W1": 0, "D1": 1, "H4": 2, "H2": 3, "H1": 4}


def _until(df: pd.DataFrame, tf: str, until: int) -> int:
    """Thời điểm của nến thứ `until` (có thể vượt nến cuối) của khung `tf`."""
    return _ts(df["time"].iat[-1] + (until - (len(df) - 1)) * tf_delta(tf))


def _zone_source(data: MarketData, sr: dict, tf: str) -> pd.DataFrame:
    """Nến dựng vùng của khung `tf`: theo `sr.frames` (D1_long = lịch sử D1 dài nối nến D1 gần nhất), mặc định như bot."""
    if (sr.get("frames") or {}).get(tf) != "D1_long" or "D1_long" not in data.frames:
        return zone_frame(data, tf)
    daily = pd.concat([data.frames["D1_long"], data.frame("D1")]).drop_duplicates("time", keep="last")
    daily = daily.sort_values("time").reset_index(drop=True)
    return weekly(daily) if tf == "W1" else daily


def key_zones(data: MarketData, sr: dict, each_side: int, extend_bars: int) -> list[dict]:
    """Vùng S/R quan trọng kiểu "đỉnh/đáy trong quá khứ": `each_side` vùng kháng cự gần nhất phía trên, hỗ trợ gần
    nhất phía dưới (và vùng giá đang nằm trong). Vùng chồng nhau giữa các khung → giữ khung lớn / nhiều chạm hơn.
    Mỗi vùng kèm các lần chạm (đỉnh/đáy swing tạo nên vùng) để đánh dấu Đỉnh 1, 2… / Đáy 1, 2…"""
    cands = []
    for tf, tc in sr["timeframes"].items():
        df = _zone_source(data, sr, tf)
        is_high, _ = ind.fractal_swings(df, tc["swing"], tc["swing"])
        for lo, hi, members in current_zones(df, tc["swing"], tc["lookback"], tc.get("max_age"), sr["tol_atr"],
                                            sr["min_touches"], sr["atr"]):
            touches = [{"t": _ts(df["time"].iat[m]), "p": float(df["high" if is_high[m] else "low"].iat[m]),
                        "kind": "high" if is_high[m] else "low"} for m in members]
            cands.append({"tf": tf, "low": float(lo), "high": float(hi), "touches": touches,
                          "start": touches[0]["t"], "extend_to": _until(df, tf, len(df) - 1 + extend_bars)})
    cands.sort(key=lambda z: (TF_RANK.get(z["tf"], 9), -len(z["touches"])))
    kept: list[dict] = []
    for z in cands:
        if not any(z["low"] <= k["high"] and k["low"] <= z["high"] for k in kept):
            kept.append(z)
    price = float(data.frame(data.base)["close"].iat[-1])
    above = sorted((z for z in kept if z["low"] > price), key=lambda z: z["low"])[:each_side]
    below = sorted((z for z in kept if z["high"] < price), key=lambda z: -z["high"])[:each_side]
    inside = [z for z in kept if z["low"] <= price <= z["high"]]
    return ([{**z, "role": "resistance"} for z in above] + [{**z, "role": "support"} for z in below]
            + [{**z, "role": "inside"} for z in inside])


def _line_touches(df: pd.DataFrame, line: Line, side: int, swing: int, tol: float) -> list[dict]:
    """Đỉnh (đường nối đỉnh) / đáy (nối đáy) swing nằm trên đường trong dung sai, từ điểm đầu tới nay."""
    is_high, is_low = ind.fractal_swings(df, swing, swing)
    col, mask = ("low", is_low) if side > 0 else ("high", is_high)
    prices = df[col].to_numpy(float)
    idx = [i for i in range(line.i1, len(df)) if mask[i] and abs(prices[i] - float(line.value(i))) <= tol]
    return [{"t": _ts(df["time"].iat[i]), "p": float(prices[i])} for i in idx]


def key_trendlines(data: MarketData, tls: dict, ov: dict) -> list[dict]:
    """Trendline quan trọng nhất: mỗi phía (nối đáy / nối đỉnh) `lines_each_side` đường còn hiệu lực có điểm
    = số chạm × độ dài (thời gian) cao nhất, cộng đường đã phá đang được retest (giá cách đường ≤ `broken_near_atr` × ATR,
    còn trong cửa sổ retest). Dò ở mọi khung/cỡ swing của `tl_scales`."""
    r, rt = tls["rules"], tls["retest"]
    rules = LineRules(r["min_touches"], r["touch_tol_atr"], r.get("channel_min_touches", 99), r["max_pivots"],
                      r.get("any_slope", True))
    cands = []
    for tf in tls["timeframes"]:
        df = data.frame(tf)
        last = len(df) - 1
        atr = float(ind.atr(df, tls["atr"]).iat[-1])
        price = float(df["close"].iat[-1])
        step = tf_delta(tf).total_seconds()
        for swing in tls["swings"]:
            series = build(df, swing, rules, tls["break_atr"], tls["atr"])
            found = [(line, int(side), "active", last + ov["extend_bars"])
                     for side, line in (series.active or {}).items() if line is not None]
            for brk in series.breaks:
                window = max(rt["min_bars"], int(round(rt["span_frac"] * (brk.index - brk.line.i1))))
                near = abs(float(brk.line.value(last)) - price) <= ov["broken_near_atr"] * atr
                if brk.index + window >= last and near:
                    found.append((brk.line, int(brk.side), "broken", brk.index + window))
            for line, side, state, until in found:
                cands.append({"df": df, "tf": tf, "swing": swing, "line": line, "side": side, "state": state,
                              "until": until, "atr": atr, "score": line.touches * (last - line.i1) * step})
    out, seen = [], set()
    for side in (1, -1):
        for state, limit in (("active", ov["lines_each_side"]), ("broken", ov["lines_each_side"])):
            best = sorted((c for c in cands if c["side"] == side and c["state"] == state), key=lambda c: -c["score"])
            for c in best[:limit]:
                line, df = c["line"], c["df"]
                key = (c["tf"], side, line.i1, line.i2)
                if key in seen:
                    continue
                seen.add(key)
                t = df["time"]
                out.append({"tf": c["tf"], "swing": c["swing"], "side": side, "state": state, "touches": line.touches,
                            "points": [[_ts(t.iat[line.i1]), float(line.p1)], [_ts(t.iat[line.i2]), float(line.p2)]],
                            "extend_to": _until(df, c["tf"], c["until"]),
                            "marks": _line_touches(df, line, side, c["swing"], rules.touch_tol_atr * c["atr"])})
    return out


def setups(journal, run_id: str | None, since: pd.Timestamp | None, limit: int) -> list[dict]:
    """Tín hiệu đã quét (có hình học mẫu hình) từ `since`, mới nhất trước."""
    where, params = ["meta IS NOT NULL"], []
    if run_id:
        where.append("run_id = ?")
        params.append(run_id)
    if since is not None:
        where.append("time >= ?")
        params.append(since.isoformat())
    rows = journal.rows(f"SELECT id, time, setup, setup_key, direction, accepted, reject_reason, meta FROM signals "
                        f"WHERE {' AND '.join(where)} ORDER BY time DESC LIMIT ?", [*params, limit])
    out = []
    for s in rows:
        meta = json.loads(s["meta"])
        if not meta.get("edges"):
            continue
        out.append({"id": s["id"], "time": _ts(s["time"]), "direction": s["direction"], "key": s["setup_key"] or s["setup"],
                    "tf": meta.get("tf"), "accepted": bool(s["accepted"]), "reject": s["reject_reason"],
                    "breakout": _ts(meta.get("breakout_time") or s["time"]),
                    "edges": [[_ts(t1), float(p1), _ts(t2), float(p2)] for t1, p1, t2, p2 in meta["edges"]]})
    return out


class BotOverlays:
    """Dựng thị trường từ nến M15 (MT5, không có thì cache) và tính vùng/trendline theo phương pháp; cache theo TTL."""

    def __init__(self, cfg: dict, gateway: MT5Gateway, root: Path) -> None:
        self._cfg = cfg
        self._oc = cfg["web"]["bot_overlays"]
        self._gateway = gateway
        self._root = root
        self._lock = threading.Lock()
        self._cache: dict[str, tuple[float, dict]] = {}

    def _market(self, now: pd.Timestamp) -> MarketData | None:
        base = base_frame(self._cfg, self._gateway, now - pd.Timedelta(days=self._oc["history_days"]), now)
        if base is None or base.empty:
            return None
        spec = load_spec(spec_path(Path(self._cfg["data"]["cache_dir"]), self._cfg["symbol"]), self._cfg)
        return build_market(base, BASE_TF, self._cfg, spec, now)[0]

    def structure(self, method: str) -> dict:
        """{method, sr, trendlines} cho phương pháp `method` (playbook.yaml)."""
        with self._lock:
            hit = self._cache.get(method)
            if hit and time.monotonic() - hit[0] < self._oc["cache_seconds"]:
                return hit[1]
            pb = load_playbook(self._root / self._cfg["bot_common"]["playbook"])
            if method not in pb["methods"]:
                raise ValueError(f"Không có phương pháp {method} trong playbook.yaml")
            p = pb["methods"][method]
            tls = p.get("tl_scales") or pb["methods"][self._oc["trendlines_from"]]["tl_scales"]
            data = self._market(pd.Timestamp.now(tz="UTC"))
            if data is None:
                return {"method": method, "sr": [], "trendlines": [], "error": "Không lấy được nến (MT5/cache)"}
            oc = self._oc
            sr = oc.get("sr") or p.get("sr")
            payload = {"method": method,
                       "sr": key_zones(data, sr, oc["zones_each_side"], oc["extend_bars"]) if sr else [],
                       "trendlines": key_trendlines(data, tls, oc)}
            self._cache[method] = (time.monotonic(), payload)
            return payload


def method_of(cfg: dict, journal, mode: str, run: str | None) -> tuple[str, str | None]:
    """(phương pháp, run_id lọc tín hiệu) ứng với nguồn đang chọn: bot → method của bot; backtest → method của run."""
    default = cfg["web"]["bot_overlays"]["default_method"]
    if mode.startswith("bot:"):
        return cfg["bots"][mode[4:]]["method"], None
    if mode == "backtest":
        run_id = run or journal.latest_run("backtest")
        rows = journal.rows("SELECT params FROM runs WHERE run_id = ?", [run_id]) if run_id else []
        params = json.loads(rows[0]["params"]) if rows and rows[0]["params"] else {}
        return params.get("method") or default, run_id
    return default, None

