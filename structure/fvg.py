"""Fair Value Gap 3 nến."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from core.types import Direction


@dataclass(frozen=True, slots=True)
class FairValueGap:
    direction: Direction
    low: float
    high: float
    index: int  # vị trí nến c3 (FVG được biết khi c3 đóng)
    time: pd.Timestamp  # giờ đóng c3


def find_fvgs(df: pd.DataFrame, min_size_atr: float, impulse_body_atr: float) -> list[FairValueGap]:
    """Bullish: low[c3] > high[c1]; bearish: high[c3] < low[c1].

    Lọc: kích thước >= min_size_atr*ATR, thân c2 >= impulse_body_atr*ATR và cùng màu với xung lực (ATR tại c3).
    """
    if len(df) < 3:
        return []
    o, h, l, c, a = (df[col].to_numpy(dtype=float) for col in ("open", "high", "low", "close", "atr"))
    h1, l1 = h[:-2], l[:-2]
    o2, c2 = o[1:-1], c[1:-1]
    h3, l3, atr3 = h[2:], l[2:], a[2:]
    body_ok = np.abs(c2 - o2) >= impulse_body_atr * atr3
    bull = (l3 - h1 >= min_size_atr * atr3) & (l3 > h1) & body_ok & (c2 > o2)
    bear = (l1 - h3 >= min_size_atr * atr3) & (h3 < l1) & body_ok & (c2 < o2)
    close_times = df["close_time"]
    gaps = [FairValueGap(Direction.BUY, float(h1[i]), float(l3[i]), int(i + 2), close_times.iat[i + 2])
            for i in np.flatnonzero(bull)]
    gaps += [FairValueGap(Direction.SELL, float(h3[i]), float(l1[i]), int(i + 2), close_times.iat[i + 2])
             for i in np.flatnonzero(bear)]
    gaps.sort(key=lambda g: g.index)
    return gaps
