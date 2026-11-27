"""Setup "sau quán tính" theo khoá K23 (docs/knowledge/alden-k23.md).

Khung `tf` (H1/H4) có nến đóng với RSI ≥ `inertia` (≤ 100 − inertia cho chiều giảm) = quán tính. Theo dõi tới `window`
nến `tf`: đỉnh sóng = cao nhất từ nến quán tính; đáy sóng = thấp nhất `impulse_bars` nến trước đó. Huỷ khi nến `tf` đóng
với RSI < `hold_rsi` hoặc giá đóng cửa hồi quá `max_retrace` của sóng. Trong lúc giá đang hồi (đóng cửa dưới đỉnh), nến
`trigger_tf` (M15) có RSI cắt lên `trigger_rsi` → BUY (chiều giảm đối xứng). Khung lớn liền kề (`higher`) phải có RSI ≥ 50
(cho phép). SL = thấp nhất của nhịp hồi − `sl_buffer_atr` × ATR `tf`; không TP cố định (gồng theo biến thể).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from core.types import Direction
from playbook import indicators as ind
from playbook.common import MarketData
from playbook.orders import MARKET, Order, Signals
from structure.indicators import rsi


def _events(df: pd.DataFrame, r: np.ndarray, p: dict) -> list[tuple[int, int]]:
    out, last = [], {1: -10**9, -1: -10**9}
    for k in range(len(df)):
        for d, hit in ((1, r[k] >= p["inertia"]), (-1, r[k] <= 100 - p["inertia"])):
            if hit and k - last[d] > p["window"]:
                out.append((k, d))
                last[d] = k
            elif hit:
                last[d] = k
    return out


def rsi_inertia(data: MarketData, p: dict) -> Signals:
    tf, ttf = p["tf"], p["trigger_tf"]
    df, tdf = data.frame(tf), data.frame(ttf)
    h, l, c = (df[col].to_numpy(float) for col in ("high", "low", "close"))
    r = rsi(df["close"], p["period"]).to_numpy(float)
    atr = ind.atr(df, p["atr"]).to_numpy(float)
    tr = rsi(tdf["close"], p["period"]).to_numpy(float)
    th, tl, tc = (tdf[col].to_numpy(float) for col in ("high", "low", "close"))
    ttimes = tdf["close_time"]
    hr = None
    if p.get("higher"):
        hdf = data.frame(p["higher"])
        hr = pd.DataFrame({"close_time": hdf["close_time"], "rsi": rsi(hdf["close"], p["period"]).to_numpy(float)})
    orders = []
    for k, d in _events(df, r, p):
        start = max(0, k - p["impulse_bars"])
        base = l[start:k + 1].min() if d > 0 else h[start:k + 1].max()
        end = min(len(df) - 1, k + p["window"])
        extreme = h[k] if d > 0 else l[k]
        cancel = end
        for j in range(k + 1, end + 1):
            extreme = max(extreme, h[j]) if d > 0 else min(extreme, l[j])
            retrace = (extreme - c[j]) * d / abs(extreme - base) if extreme != base else 0.0
            if (r[j] - 50) * d < (p["hold_rsi"] - 50) or retrace > p["max_retrace"]:
                cancel = j
                break
        t0, t1 = df["close_time"].iat[k], df["close_time"].iat[cancel]
        a = int(ttimes.searchsorted(t0, side="right"))
        b = int(ttimes.searchsorted(t1, side="right"))
        peak, pull = (h[k] if d > 0 else l[k]), None
        for m in range(max(a, 1), b):
            peak = max(peak, th[m]) if d > 0 else min(peak, tl[m])
            low = tl[m] if d > 0 else th[m]
            pull = low if pull is None else (min(pull, low) if d > 0 else max(pull, low))
            in_pullback = (peak - tc[m]) * d > 0
            crossed = (tr[m] - p["trigger_rsi"]) * d > 0 >= (tr[m - 1] - p["trigger_rsi"]) * d
            if not (in_pullback and crossed):
                continue
            t = tdf["close_time"].iat[m]
            if hr is not None:
                j = int(hr["close_time"].searchsorted(t, side="right")) - 1
                if j < 0 or (hr["rsi"].iat[j] - 50) * d <= 0:
                    break
            sl = pull - d * p["sl_buffer_atr"] * atr[k]
            dist = (tc[m] - sl) * d
            if dist <= 0 or dist > p["max_sl_atr"] * atr[k]:
                break
            direction = Direction.BUY if d > 0 else Direction.SELL
            orders.append(Order(f"{p['code']}:rsi_inertia@{tf}:{t:%Y%m%d%H%M}:{direction.name}", t, direction, MARKET,
                                sl_dist=float(dist),
                                reasons=(f"quán tính RSI {tf} ({r[k]:.0f}) lúc {df['time'].iat[k]:%d/%m %H:%M}",
                                         f"nhịp hồi nông, RSI {ttf} cắt {p['trigger_rsi']}"),
                                meta={"tf": tf, "kind": "rsi_inertia", "entry": float(tc[m])}))
            break
    return Signals(sorted(orders, key=lambda o: o.time), [])
