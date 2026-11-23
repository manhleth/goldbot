"""Quét thanh khoản: wick vượt swing gần nhất nhưng đóng cửa quay lại."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from core.types import Direction
from structure.swings import Swing, of_kind


@dataclass(frozen=True, slots=True)
class Sweep:
    direction: Direction  # BUY = quét đáy rồi đóng lên trên
    index: int
    level: float  # giá swing bị quét
    extreme: float  # đáy/đỉnh của nến quét


def _active_swing(pivots: list[Swing], closes: np.ndarray, i: int, direction: Direction) -> Swing | None:
    """Swing gần nhất đã xác nhận trước nến i và chưa bị đóng cửa phá."""
    for swing in reversed(pivots):
        if swing.confirmed_index >= i:
            continue
        between = closes[swing.index + 1:i]
        broken = (between < swing.price).any() if direction == Direction.BUY else (between > swing.price).any()
        if not broken:
            return swing
    return None


def find_sweep(df: pd.DataFrame, swings: list[Swing], direction: Direction, max_age: int) -> Sweep | None:
    """Sweep gần nhất trong `max_age` nến cuối."""
    pivots = of_kind(swings, "low" if direction == Direction.BUY else "high")
    h, l, c = (df[col].to_numpy(dtype=float) for col in ("high", "low", "close"))
    last = len(df) - 1
    for i in range(last, max(-1, last - max_age), -1):
        swing = _active_swing(pivots, c, i, direction)
        if swing is None:
            continue
        if direction == Direction.BUY and l[i] < swing.price < c[i]:
            return Sweep(direction, i, swing.price, float(l[i]))
        if direction == Direction.SELL and c[i] < swing.price < h[i]:
            return Sweep(direction, i, swing.price, float(h[i]))
    return None
