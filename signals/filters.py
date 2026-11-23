"""Bộ lọc mức tín hiệu (không phải tín hiệu độc lập)."""
from __future__ import annotations

from core.types import Direction, Signal


def filter_reason(signal: Signal, cfg: dict) -> str | None:
    fc = cfg["filters"]
    if signal.setup.score < fc["min_score"]:
        return "score_below_min"
    if not fc["rsi_enabled"]:
        return None
    if signal.direction == Direction.BUY and signal.rsi >= fc["rsi_overbought"]:
        return "rsi_overbought"
    if signal.direction == Direction.SELL and signal.rsi <= fc["rsi_oversold"]:
        return "rsi_oversold"
    return None
