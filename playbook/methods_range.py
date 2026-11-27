"""Phương pháp cho thị trường biên độ thấp / xu hướng nhiễu ("giảm trong tăng, tăng trong giảm").

A. `channel_edge` — vào ở cạnh kênh D1 (bài học kênh giảm 03→11/2022):
   kênh D1 hồi quy (playbook/channel_regime.channel_series: `period`, `min_r2`, `min_slope_atr`); tại nến `tf` (H4) đã
   đóng, cạnh kênh được chiếu theo độ dốc từ nến D1 đóng gần nhất. Kênh giảm: nến chạm cạnh trên (± `zone_atr` × ATR D1)
   rồi đóng cửa là nến giảm, nằm dưới cạnh → SELL; kênh tăng ngược lại. SL = râu nến ± `sl_buffer_atr` × ATR `tf`;
   TP = cạnh đối diện; bỏ nếu R:R < `min_rr` hoặc SL > `max_sl_atr` × ATR `tf`.
B. `range_sweep` — quét thanh khoản ở biên range D1:
   range = đỉnh/đáy `range_days` nến D1 đã đóng gần nhất, chỉ khi hiệu suất xu hướng (|thay đổi| / quãng đường) <
   `max_er` và bề rộng trong [`min_width_atr`, `max_width_atr`] × ATR D1. Nến `tf` (M15) đâm qua biên (râu vượt ≤
   `max_sweep_atr` × ATR D1) rồi đóng cửa quay lại trong range → vào ngược chiều. SL = râu quét ± `sl_buffer_atr` × ATR `tf`;
   TP = giữa range (`tp_frac` = 0.5) tính từ biên quét; bỏ nếu R:R < `min_rr`. Mỗi biên chỉ một lệnh mỗi ngày.
Cả hai đặt TP cố định (meta `keep_tp`), không dùng gồng SL.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from core.types import Direction
from playbook import indicators as ind
from playbook.channel_regime import channel_series
from playbook.common import MarketData
from playbook.orders import MARKET, Order, Signals


def _order(code: str, kind: str, tf: str, t: pd.Timestamp, d: int, close: float, sl: float, tp: float,
           reasons: tuple[str, ...], meta: dict) -> Order:
    direction = Direction.BUY if d > 0 else Direction.SELL
    return Order(f"{code}:{kind}@{tf}:{t:%Y%m%d%H%M}:{direction.name}", t, direction, MARKET,
                 sl_dist=float((close - sl) * d), tp=float(tp), reasons=reasons,
                 meta={"tf": tf, "kind": kind, "entry": float(close), "target": float(tp), "keep_tp": True, **meta})


def _channel_state(data: MarketData, p: dict) -> pd.DataFrame:
    """Theo từng nến D1 đã đóng: chiều kênh, cạnh trên/dưới tại nến đó, độ dốc/ngày, ATR D1."""
    d1 = data.frame("D1")
    cs = channel_series(d1, p)
    period, c, h, l = p["period"], d1["close"].to_numpy(float), d1["high"].to_numpy(float), d1["low"].to_numpy(float)
    x = np.arange(period, dtype=float)
    top = np.full(len(d1), np.nan)
    bottom = np.full(len(d1), np.nan)
    slope = np.full(len(d1), np.nan)
    for k in np.flatnonzero(cs["dir"].to_numpy() != 0):
        s = slice(k - period, k)
        b, a = np.polyfit(x, c[s], 1)
        fit = a + b * x
        mid = a + b * period
        top[k], bottom[k], slope[k] = mid + (h[s] - fit).max(), mid + (l[s] - fit).min(), b
    return pd.DataFrame({"close_time": d1["close_time"], "dir": cs["dir"], "top": top, "bottom": bottom,
                         "slope": slope, "atr_d1": ind.atr(d1, p["atr"]).to_numpy(float)})


def channel_edge(data: MarketData, p: dict) -> Signals:
    tf = p["tf"]
    df = data.frame(tf)
    state = pd.merge_asof(df[["close_time"]], _channel_state(data, p).rename(columns={"close_time": "d1_close"}),
                          left_on="close_time", right_on="d1_close", direction="backward")
    o, h, l, c = (df[col].to_numpy(float) for col in ("open", "high", "low", "close"))
    atr = ind.atr(df, p["atr"]).to_numpy(float)
    days = ((df["close_time"] - state["d1_close"]).dt.total_seconds() / 86400).to_numpy()
    orders = []
    for k in range(1, len(df)):
        d = int(state["dir"].iat[k]) if pd.notna(state["dir"].iat[k]) else 0
        if d == 0 or not np.isfinite(atr[k]):
            continue
        shift = state["slope"].iat[k] * days[k]
        top, bottom, zone = state["top"].iat[k] + shift, state["bottom"].iat[k] + shift, p["zone_atr"] * state["atr_d1"].iat[k]
        edge, far = (top, bottom) if d < 0 else (bottom, top)
        touched = (h[k] >= edge - zone) if d < 0 else (l[k] <= edge + zone)
        rejected = (c[k] - o[k]) * d > 0 and (c[k] - edge) * d > 0
        if not (touched and rejected):
            continue
        sl = (h[k] if d < 0 else l[k]) - d * p["sl_buffer_atr"] * atr[k]
        risk, reward = (c[k] - sl) * d, (far - c[k]) * d
        if risk <= 0 or risk > p["max_sl_atr"] * atr[k] or reward < p["min_rr"] * risk:
            continue
        t = df["close_time"].iat[k]
        orders.append(_order(p["code"], "channel_edge", tf, t, d, c[k], sl, far,
                             (f"kênh D1 {'giảm' if d < 0 else 'tăng'}: chạm cạnh {edge:.2f}, đóng cửa quay vào",
                              f"mục tiêu cạnh đối diện {far:.2f}"), {"edge": float(edge)}))
    return Signals(orders, [])


def _ranges(data: MarketData, p: dict) -> pd.DataFrame:
    """Range D1 tại mỗi nến D1 đã đóng: hi, lo của `range_days` nến gần nhất, hợp lệ hay không."""
    d1 = data.frame("D1")
    n = p["range_days"]
    hi, lo = d1["high"].rolling(n).max(), d1["low"].rolling(n).min()
    path = d1["close"].diff().abs().rolling(n).sum()
    er = (d1["close"] - d1["close"].shift(n)).abs() / path
    atr = ind.atr(d1, p["atr"])
    width = (hi - lo) / atr
    ok = (er < p["max_er"]) & (width >= p["min_width_atr"]) & (width <= p["max_width_atr"])
    return pd.DataFrame({"d1_close": d1["close_time"], "hi": hi, "lo": lo, "atr_d1": atr, "ok": ok})


def range_sweep(data: MarketData, p: dict) -> Signals:
    tf = p["tf"]
    df = data.frame(tf)
    rg = pd.merge_asof(df[["close_time"]], _ranges(data, p), left_on="close_time", right_on="d1_close",
                       direction="backward")
    h, l, c = (df[col].to_numpy(float) for col in ("high", "low", "close"))
    atr = ind.atr(df, p["atr"]).to_numpy(float)
    used: set[tuple] = set()
    orders = []
    for k in range(1, len(df)):
        if not bool(rg["ok"].iat[k]) or not np.isfinite(atr[k]):
            continue
        hi, lo, a_d1 = rg["hi"].iat[k], rg["lo"].iat[k], rg["atr_d1"].iat[k]
        for d, edge, poke in ((-1, hi, h[k] - hi), (1, lo, lo - l[k])):
            back = (c[k] - edge) * d > 0
            key = (rg["d1_close"].iat[k], d)
            if not (0 < poke <= p["max_sweep_atr"] * a_d1 and back) or key in used:
                continue
            extreme = h[k] if d < 0 else l[k]
            sl = extreme - d * p["sl_buffer_atr"] * atr[k]
            tp = edge + d * p["tp_frac"] * (hi - lo)
            risk, reward = (c[k] - sl) * d, (tp - c[k]) * d
            if risk <= 0 or reward < p["min_rr"] * risk:
                continue
            used.add(key)
            t = df["close_time"].iat[k]
            orders.append(_order(p["code"], "range_sweep", tf, t, d, c[k], sl, tp,
                                 (f"quét {'đỉnh' if d < 0 else 'đáy'} range D1 {lo:.2f}–{hi:.2f} rồi đóng cửa quay vào",
                                  f"mục tiêu giữa range {tp:.2f}"), {"range": [float(lo), float(hi)]}))
    return Signals(orders, [])
