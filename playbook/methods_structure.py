"""XAU-13: phá cấu trúc M15 thuận D1 → hồi Fibonacci 61.8–78.6% chồng FVG → Buy/Sell Limit giữa vùng hồi."""
from __future__ import annotations

import numpy as np
import pandas as pd

from core.types import Direction
from playbook import indicators as ind
from playbook.common import MarketData, utc_hours_mask
from playbook.methods_indicator import _daily_trend
from playbook.orders import LIMIT, Event, Order, Signals

B, S = Direction.BUY, Direction.SELL


def structure_breaks(df: pd.DataFrame, n: int) -> list[tuple[int, Direction, int]]:
    """(nến phá, chiều, vị trí swing bị phá): close đầu tiên vượt swing gần nhất đã xác nhận (n trái / n phải)."""
    is_high, is_low = ind.fractal_swings(df, n, n)
    h, l, c = (df[col].to_numpy(float) for col in ("high", "low", "close"))
    out: list[tuple[int, Direction, int]] = []
    last_high = last_low = None
    broken: set[int] = set()
    for k in range(len(df)):
        s = k - n  # swing tại s được xác nhận khi nến k = s + n đóng
        if s >= 0 and is_high[s]:
            last_high = s
        if s >= 0 and is_low[s]:
            last_low = s
        if last_high is not None and last_high not in broken and k > last_high + n and c[k] > h[last_high]:
            broken.add(last_high)
            out.append((k, B, last_high))
        if last_low is not None and last_low not in broken and k > last_low + n and c[k] < l[last_low]:
            broken.add(last_low)
            out.append((k, S, last_low))
    return out


def _last_swing_before(mask: np.ndarray, k: int, n: int) -> int | None:
    """Swing đã xác nhận gần nhất tại nến k (vị trí s với s + n <= k)."""
    idx = np.flatnonzero(mask[: max(0, k - n + 1)])
    return int(idx[-1]) if idx.size else None


def xau13(data: MarketData, p: dict) -> Signals:
    df = data.frame(p["tf"])
    n = p["swing"]
    atr = ind.atr(df, p["atr"]).to_numpy(float)
    trend = _daily_trend(data, df, p["daily_ema"])
    allowed = utc_hours_mask(df["close_time"], p["hours"], p["skip_friday"])
    is_high, is_low = ind.fractal_swings(df, n, n)
    h, l, c = (df[col].to_numpy(float) for col in ("high", "low", "close"))
    times = df["close_time"]
    step = times.iat[1] - times.iat[0]
    breaks = structure_breaks(df, n)
    events = [Event(times.iat[k], S if d == B else B) for k, d, _ in breaks]  # phá ngược chiều → thoát/hủy
    orders: list[Order] = []
    for k, d, _ in breaks:
        if not (allowed[k] and np.isfinite(atr[k]) and trend[k] == d):
            continue
        base = _last_swing_before(is_low if d == B else is_high, k, n)
        if base is None:
            continue
        top, bottom = (h[k], l[base]) if d == B else (l[k], h[base])
        leg = (top - bottom) * d
        if leg < p["min_leg_atr"] * atr[k]:
            continue
        z1 = top - d * p["fib"][0] * leg
        z2 = top - d * p["fib"][1] * leg
        zlo, zhi = min(z1, z2), max(z1, z2)
        if not _fvg_overlaps(h, l, k, p["fvg_lookback"], d, zlo, zhi):
            continue
        price = (zlo + zhi) / 2
        if (c[k] - price) * d <= 0:  # giá phải còn ở phía đặt được lệnh limit
            continue
        sl = bottom - d * p["sl_atr"] * atr[k]
        risk = abs(price - sl)
        if not (p["sl_min_atr"] * atr[k] <= risk <= p["sl_max_atr"] * atr[k]):
            continue
        t = times.iat[k]
        orders.append(Order(f"xau13:{t:%Y%m%d%H%M}:{d.name}", t, d, LIMIT, price=price, sl=sl,
                            tp=price + d * p["tp_r"] * risk, expiry=t + p["expiry_bars"] * step,
                            max_hold=p["max_hold_bars"] * step,
                            reasons=(f"phá cấu trúc {d.name}", f"vùng hồi {zlo:.2f}-{zhi:.2f}")))
    return Signals(orders, events)


def _fvg_overlaps(h: np.ndarray, l: np.ndarray, k: int, lookback: int, d: Direction, zlo: float, zhi: float) -> bool:
    """Có FVG cùng chiều (nến c trong `lookback` nến tới k) giao với vùng [zlo, zhi]."""
    for c in range(max(2, k - lookback + 1), k + 1):
        a = c - 2
        glo, ghi = (h[a], l[c]) if d == B else (h[c], l[a])
        if ghi > glo and glo < zhi and ghi > zlo:
            return True
    return False
