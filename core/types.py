"""Kiểu dữ liệu dùng chung giữa các tầng."""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import IntEnum

import pandas as pd


class Direction(IntEnum):
    SELL = -1
    NEUTRAL = 0
    BUY = 1


@dataclass(frozen=True, slots=True)
class Zone:
    low: float
    high: float

    def overlaps(self, low: float, high: float) -> bool:
        return low <= self.high and high >= self.low

    def contains(self, price: float) -> bool:
        return self.low <= price <= self.high


@dataclass(frozen=True, slots=True)
class Setup:
    """Vùng quan tâm ở khung setup, chờ nến trigger ở khung vào lệnh."""

    name: str
    direction: Direction
    zone: Zone
    invalidation: float  # mốc cấu trúc làm vô hiệu setup
    score: int
    reasons: tuple[str, ...]
    key: str  # định danh duy nhất để chống vào lệnh trùng
    targets: tuple[float, ...] = ()  # mục tiêu riêng của setup (vd thanh khoản đối diện), gộp với mức cấu trúc


@dataclass(frozen=True, slots=True, eq=False)
class Signal:
    time: pd.Timestamp  # thời điểm nến trigger đóng (UTC)
    setup: Setup
    trigger: str
    trigger_extreme: float  # đáy (BUY) / đỉnh (SELL) của nến trigger
    close: float  # giá đóng nến trigger (bid)
    rsi: float
    bias: Mapping[str, Direction]

    @property
    def direction(self) -> Direction:
        return self.setup.direction


@dataclass(frozen=True, slots=True, eq=False)
class TradePlan:
    signal: Signal
    entry: float
    sl: float
    tp1: float
    tp2: float | None

    @property
    def risk(self) -> float:
        return abs(self.entry - self.sl)

    @property
    def rr_tp1(self) -> float:
        return abs(self.tp1 - self.entry) / self.risk


@dataclass(frozen=True, slots=True)
class Rejected:
    reason: str
