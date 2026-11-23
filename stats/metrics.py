"""Chỉ số thống kê trên chuỗi R-multiple."""
from __future__ import annotations

import math
from collections.abc import Sequence

import numpy as np


def wilson_interval(wins: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return 0.0, 0.0
    p = wins / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return max(0.0, centre - half), min(1.0, centre + half)


def max_drawdown(curve: np.ndarray) -> float:
    if curve.size == 0:
        return 0.0
    running = np.maximum.accumulate(np.concatenate([[0.0], curve]))
    return float((running[1:] - curve).max())


def longest_streak(mask: np.ndarray) -> int:
    best = current = 0
    for flag in mask:
        current = current + 1 if flag else 0
        best = max(best, current)
    return best


def summarize(r_values: Sequence[float]) -> dict:
    """Thắng = R > 0. Expectancy = winrate*avgWin - (1-winrate)*avgLoss (avgLoss là độ lớn)."""
    r = np.asarray(r_values, dtype=float)
    n = int(r.size)
    wins_mask = r > 0
    wins = int(wins_mask.sum())
    win_r, loss_r = r[wins_mask], r[~wins_mask]
    winrate = wins / n if n else 0.0
    avg_win = float(win_r.mean()) if win_r.size else 0.0
    avg_loss = float(-loss_r.mean()) if loss_r.size else 0.0
    gross_loss = float(-loss_r.sum())
    lo, hi = wilson_interval(wins, n)
    return {
        "trades": n, "wins": wins, "winrate": winrate, "winrate_ci_low": lo, "winrate_ci_high": hi,
        "avg_win_r": avg_win, "avg_loss_r": avg_loss,
        "expectancy_r": winrate * avg_win - (1 - winrate) * avg_loss,
        "profit_factor": float(win_r.sum()) / gross_loss if gross_loss > 0 else math.inf if wins else 0.0,
        "total_r": float(r.sum()), "max_dd_r": max_drawdown(np.cumsum(r)),
        "longest_losing_streak": longest_streak(r < 0),
    }
