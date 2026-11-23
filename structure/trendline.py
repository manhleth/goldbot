"""Trendline nối 2 swing và phát hiện phá vỡ (đơn vị trục x = chỉ số nến)."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from structure.swings import Swing, SwingKind, of_kind


@dataclass(frozen=True, slots=True)
class Trendline:
    kind: SwingKind  # "high": trendline giảm nối các đỉnh; "low": trendline tăng nối các đáy
    i1: int
    p1: float
    i2: int
    p2: float

    @property
    def slope(self) -> float:
        return (self.p2 - self.p1) / (self.i2 - self.i1)

    def value(self, index):
        return self.p1 + self.slope * (np.asarray(index) - self.i1)


@dataclass(frozen=True, slots=True)
class LineBreak:
    index: int
    distance: float  # khoảng giá đóng cửa vượt đường


def _slopes_correctly(kind: SwingKind, first: Swing, second: Swing) -> bool:
    return second.price < first.price if kind == "high" else second.price > first.price


def _respected(closes: np.ndarray, line: Trendline) -> bool:
    """Không có nến đóng cửa xuyên đường giữa hai điểm chạm."""
    idx = np.arange(line.i1 + 1, line.i2)
    if idx.size == 0:
        return True
    seg, vals = closes[idx], line.value(idx)
    return bool((seg <= vals).all()) if line.kind == "high" else bool((seg >= vals).all())


def latest_trendline(df: pd.DataFrame, swings: list[Swing], kind: SwingKind, max_pivots: int) -> Trendline | None:
    """Trendline hợp lệ có điểm chạm thứ hai mới nhất."""
    pivots = of_kind(swings, kind)[-max_pivots:]
    closes = df["close"].to_numpy(dtype=float)
    for j in range(len(pivots) - 1, 0, -1):
        for i in range(j - 1, -1, -1):
            a, b = pivots[i], pivots[j]
            if not _slopes_correctly(kind, a, b):
                continue
            line = Trendline(kind, a.index, a.price, b.index, b.price)
            if _respected(closes, line):
                return line
    return None


def first_break(df: pd.DataFrame, line: Trendline) -> LineBreak | None:
    """Nến đầu tiên sau điểm chạm thứ hai đóng cửa xuyên đường."""
    closes = df["close"].to_numpy(dtype=float)
    idx = np.arange(line.i2 + 1, len(closes))
    if idx.size == 0:
        return None
    vals = line.value(idx)
    crossed = closes[idx] > vals if line.kind == "high" else closes[idx] < vals
    if not crossed.any():
        return None
    pos = int(np.argmax(crossed))
    return LineBreak(int(idx[pos]), float(abs(closes[idx[pos]] - vals[pos])))
