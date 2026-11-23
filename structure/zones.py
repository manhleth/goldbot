"""Vùng hỗ trợ/kháng cự từ cụm swing và phát hiện vùng đổi vai."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from core.types import Direction, Zone
from structure.swings import Swing


@dataclass(frozen=True, slots=True)
class SRZone:
    low: float
    high: float
    touches: int
    first_index: int
    last_index: int

    @property
    def zone(self) -> Zone:
        return Zone(self.low, self.high)


def cluster_zones(swings: list[Swing], tolerance: float, min_touches: int) -> list[SRZone]:
    """Gom swing (cả đỉnh lẫn đáy) có giá cách nhau không quá `tolerance` tính từ swing thấp nhất của cụm."""
    if tolerance <= 0 or not swings:
        return []
    clusters: list[list[Swing]] = []
    for swing in sorted(swings, key=lambda s: s.price):
        if clusters and swing.price - clusters[-1][0].price <= tolerance:
            clusters[-1].append(swing)
        else:
            clusters.append([swing])
    return [
        SRZone(low=min(s.price for s in c), high=max(s.price for s in c), touches=len(c),
               first_index=min(s.index for s in c), last_index=max(s.index for s in c))
        for c in clusters if len(c) >= min_touches
    ]


def last_flip_break(df: pd.DataFrame, zone: SRZone, direction: Direction) -> int | None:
    """Nến gần nhất đóng cửa xuyên hết vùng theo `direction`, ngay sau lần đóng cửa ngoài vùng ở phía đối diện.

    BUY: kháng cự bị phá lên (trước đó đóng dưới vùng, giờ đóng trên vùng). Không xác định được vai → None.
    """
    closes = df["close"].to_numpy(dtype=float)[zone.first_index:]
    side = np.where(closes > zone.high, 1, np.where(closes < zone.low, -1, 0))
    outside = np.flatnonzero(side)
    if outside.size < 2:
        return None
    sides = side[outside]
    flips = np.flatnonzero((sides[1:] == int(direction)) & (sides[:-1] == -int(direction))) + 1
    if flips.size == 0:
        return None
    return zone.first_index + int(outside[flips[-1]])
