"""Order block bản đơn giản: nến ngược màu cuối cùng trước xung lực tạo BOS."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from core.types import Direction
from structure.breaks import StructureBreak


@dataclass(frozen=True, slots=True)
class OrderBlock:
    direction: Direction
    low: float
    high: float
    index: int
    break_index: int


def _last_opposite_candle(o: np.ndarray, c: np.ndarray, origin: int, search_bars: int, bearish: bool) -> int | None:
    for j in range(origin, max(-1, origin - search_bars - 1), -1):
        if (c[j] < o[j]) if bearish else (c[j] > o[j]):
            return j
    return None


def find_order_blocks(df: pd.DataFrame, breaks: list[StructureBreak], min_move_atr: float,
                      search_bars: int) -> list[OrderBlock]:
    o, h, l, c, a = (df[col].to_numpy(dtype=float) for col in ("open", "high", "low", "close", "atr"))
    blocks: list[OrderBlock] = []
    seen: set[int] = set()
    for brk in breaks:
        lo, hi = brk.swing.index, brk.index
        bullish = brk.direction == Direction.BUY
        origin = lo + int(np.argmin(l[lo:hi + 1]) if bullish else np.argmax(h[lo:hi + 1]))
        j = _last_opposite_candle(o, c, origin, search_bars, bearish=bullish)
        if j is None or j in seen:
            continue
        move = (h[j:hi + 1].max() - l[j]) if bullish else (h[j] - l[j:hi + 1].min())
        if not move >= min_move_atr * a[hi]:
            continue
        seen.add(j)
        blocks.append(OrderBlock(brk.direction, float(l[j]), float(h[j]), j, hi))
    return blocks
