"""Swing high/low theo fractal N nến (chỉ trả swing đã được xác nhận)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np
import pandas as pd
from numpy.lib.stride_tricks import sliding_window_view

SwingKind = Literal["high", "low"]


@dataclass(frozen=True, slots=True)
class Swing:
    index: int  # vị trí trong DataFrame truyền vào
    time: pd.Timestamp
    price: float
    kind: SwingKind
    confirmed_index: int  # nến mà sau khi đóng swing mới được biết


def find_swings(df: pd.DataFrame, n: int) -> list[Swing]:
    """Nến i là swing high nếu high[i] > N nến trước và >= N nến sau (tương tự cho low).

    Nghiêm ngặt bên trái để hai đỉnh bằng nhau chỉ sinh một swing.
    """
    width = 2 * n + 1
    if n < 1 or len(df) < width:
        return []
    highs = df["high"].to_numpy(dtype=float)
    lows = df["low"].to_numpy(dtype=float)
    hw = sliding_window_view(highs, width)
    lw = sliding_window_view(lows, width)
    is_high = (hw[:, n] > hw[:, :n].max(axis=1)) & (hw[:, n] >= hw[:, n + 1:].max(axis=1))
    is_low = (lw[:, n] < lw[:, :n].min(axis=1)) & (lw[:, n] <= lw[:, n + 1:].min(axis=1))
    times = df["time"]
    swings = [Swing(int(i + n), times.iat[i + n], float(highs[i + n]), "high", int(i + 2 * n))
              for i in np.flatnonzero(is_high)]
    swings += [Swing(int(i + n), times.iat[i + n], float(lows[i + n]), "low", int(i + 2 * n))
               for i in np.flatnonzero(is_low)]
    swings.sort(key=lambda s: (s.index, s.kind))
    return swings


def of_kind(swings: list[Swing], kind: SwingKind) -> list[Swing]:
    return [s for s in swings if s.kind == kind]
