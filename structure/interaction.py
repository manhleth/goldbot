"""Vòng đời tương tác giá với một vùng: số lần chạm, đang chạm, đã bị phá."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from core.types import Direction


@dataclass(frozen=True, slots=True)
class Lifecycle:
    episodes: int  # số đợt chạm riêng biệt (chuỗi nến liên tiếp chạm vùng = 1 đợt)
    ongoing: bool  # nến cuối đang chạm vùng
    invalidated: bool  # đã có nến đóng xuyên hết vùng ngược chiều setup

    def is_first_touch(self, max_episodes: int) -> bool:
        """Còn hiệu lực: chưa bị phá và đợt chạm hiện tại không vượt quá `max_episodes`."""
        if self.invalidated:
            return False
        return self.episodes < max_episodes or (self.episodes == max_episodes and self.ongoing)


def zone_lifecycle(df: pd.DataFrame, start: int, low: float, high: float, direction: Direction) -> Lifecycle:
    """Xét các nến từ vị trí `start` tới cuối. BUY: vùng bị phá khi đóng cửa dưới `low`; SELL: trên `high`."""
    closes = df["close"].to_numpy(dtype=float)[start:]
    if closes.size == 0:
        return Lifecycle(0, False, False)
    lows = df["low"].to_numpy(dtype=float)[start:]
    highs = df["high"].to_numpy(dtype=float)[start:]
    broken = closes < low if direction == Direction.BUY else closes > high
    overlap = (lows <= high) & (highs >= low)
    if broken.any():
        overlap = overlap[: int(np.argmax(broken)) + 1]
    episodes = int(overlap[0]) + int(np.count_nonzero(overlap[1:] & ~overlap[:-1]))
    return Lifecycle(episodes, bool(overlap[-1]), bool(broken.any()))
