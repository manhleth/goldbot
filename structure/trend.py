"""Xu hướng theo chuỗi swing: HH+HL = tăng, LH+LL = giảm, còn lại = đi ngang."""
from __future__ import annotations

from core.types import Direction
from structure.swings import Swing, of_kind


def swing_trend(swings: list[Swing]) -> Direction:
    highs = [s.price for s in of_kind(swings, "high")][-2:]
    lows = [s.price for s in of_kind(swings, "low")][-2:]
    if len(highs) < 2 or len(lows) < 2:
        return Direction.NEUTRAL
    if highs[1] > highs[0] and lows[1] > lows[0]:
        return Direction.BUY
    if highs[1] < highs[0] and lows[1] < lows[0]:
        return Direction.SELL
    return Direction.NEUTRAL
