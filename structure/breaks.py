"""BOS / CHoCH: nến đóng cửa phá swing gần nhất."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np
import pandas as pd

from core.types import Direction
from structure.swings import Swing, of_kind
from structure.trend import swing_trend

BreakKind = Literal["BOS", "CHOCH"]


@dataclass(frozen=True, slots=True)
class StructureBreak:
    index: int
    direction: Direction
    level: float
    swing: Swing
    kind: BreakKind


def find_breaks(df: pd.DataFrame, swings: list[Swing]) -> list[StructureBreak]:
    """Một swing chỉ được tính là "swing gần nhất" cho tới khi swing cùng loại kế tiếp được xác nhận.

    Phá cùng chiều xu hướng (tính từ các swing đã biết trước nến phá) = BOS, ngược chiều = CHoCH.
    """
    closes = df["close"].to_numpy(dtype=float)
    out: list[StructureBreak] = []
    for kind, direction in (("high", Direction.BUY), ("low", Direction.SELL)):
        same = of_kind(swings, kind)
        for pos, swing in enumerate(same):
            start = swing.confirmed_index + 1
            stop = same[pos + 1].confirmed_index + 1 if pos + 1 < len(same) else len(closes)
            segment = closes[start:stop]
            crossed = segment > swing.price if direction == Direction.BUY else segment < swing.price
            if not crossed.any():
                continue
            k = start + int(np.argmax(crossed))
            trend = swing_trend([s for s in swings if s.confirmed_index < k])
            kind_ = "CHOCH" if trend == -direction else "BOS"
            out.append(StructureBreak(k, direction, swing.price, swing, kind_))
    out.sort(key=lambda b: b.index)
    return out
