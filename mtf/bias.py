"""Bias từng khung và gộp bias đa khung."""
from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

import numpy as np

from core.types import Direction
from mtf.view import TimeframeView
from structure.trend import swing_trend


@dataclass(frozen=True, slots=True)
class Bias:
    direction: Direction
    score: int
    reasons: tuple[str, ...]


def _sign(value: float) -> int:
    return 0 if np.isnan(value) else int(np.sign(value))


BIAS_METHODS = ("indicators", "smc")


def smc_bias(view: TimeframeView) -> Bias:
    """Thuần SMC: chiều của lần phá cấu trúc (BOS/CHoCH) gần nhất."""
    if not view.breaks:
        return Bias(Direction.NEUTRAL, 0, ("chưa có phá cấu trúc",))
    last = view.breaks[-1]
    when = view.df["time"].iat[last.index]
    side = "lên" if last.direction == Direction.BUY else "xuống"
    return Bias(last.direction, int(last.direction), (f"{last.kind} {side} phá {last.level:.2f} lúc {when:%m-%d %H:%M} UTC",))


def timeframe_bias(view: TimeframeView, cfg: dict) -> Bias:
    if cfg["bias"]["method"] == "smc":
        return smc_bias(view)
    return indicator_bias(view, cfg)


def indicator_bias(view: TimeframeView, cfg: dict) -> Bias:
    """Điểm = cấu trúc swing + vị trí giá so với từng EMA + độ dốc EMA; ADX dưới ngưỡng → NEUTRAL."""
    sc, bc = cfg["structure"], cfg["bias"]
    df = view.df
    close = view.close
    slope_col = f"ema_{bc['slope_ema']}"
    components = {"structure": int(swing_trend(view.swings))}
    for period in sc["ema"]:
        components[f"close_vs_ema{period}"] = _sign(close - df[f"ema_{period}"].iat[-1])
    if len(df) > bc["slope_bars"]:
        components[f"ema{bc['slope_ema']}_slope"] = _sign(
            df[slope_col].iat[-1] - df[slope_col].iat[-1 - bc["slope_bars"]])
    score = sum(components.values())
    reasons = tuple(f"{name}={value:+d}" for name, value in components.items())
    adx_value = float(df["adx"].iat[-1])
    if not adx_value > sc["adx_min"]:
        return Bias(Direction.NEUTRAL, score, (*reasons, f"adx={adx_value:.1f}<=min"))
    if score >= bc["min_score"]:
        return Bias(Direction.BUY, score, reasons)
    if score <= -bc["min_score"]:
        return Bias(Direction.SELL, score, reasons)
    return Bias(Direction.NEUTRAL, score, reasons)


def combine_biases(directions: Iterable[Direction], mode: str) -> Direction:
    """non_conflicting: không khung nào ngược nhau và có ít nhất 1 khung có chiều.
    all_agree: mọi khung cùng một chiều."""
    values = list(directions)
    active = {d for d in values if d != Direction.NEUTRAL}
    if len(active) != 1:
        return Direction.NEUTRAL
    if mode == "all_agree" and Direction.NEUTRAL in values:
        return Direction.NEUTRAL
    if mode not in ("non_conflicting", "all_agree"):
        raise ValueError(f"bias.combine không hợp lệ: {mode}")
    return active.pop()
