"""Tính khối lượng lệnh theo số tiền rủi ro và thông số symbol."""
from __future__ import annotations

import math
from dataclasses import asdict, dataclass

SIZING_MODES = ("fixed_money", "percent")


@dataclass(frozen=True, slots=True)
class SymbolSpec:
    point: float
    tick_size: float
    tick_value: float  # tiền lãi/lỗ của 1 lot khi giá chạy 1 tick
    volume_min: float
    volume_step: float
    volume_max: float

    def as_dict(self) -> dict:
        return asdict(self)

    def money(self, price_distance: float, volume: float) -> float:
        return price_distance / self.tick_size * self.tick_value * volume


def floor_to_step(value: float, step: float) -> float:
    return round(math.floor(value / step + 1e-9) * step, 8)


def risk_budget(equity: float, risk_cfg: dict) -> float:
    """Số tiền tối đa chấp nhận mất nếu chạm SL: cố định (USD) hoặc theo % equity."""
    mode = risk_cfg["sizing"]
    if mode == "fixed_money":
        return float(risk_cfg["risk_per_trade_money"])
    if mode == "percent":
        return equity * risk_cfg["risk_per_trade_pct"] / 100.0
    raise ValueError(f"risk.sizing không hợp lệ: {mode}")


def lot_size(risk_money: float, sl_distance: float, spec: SymbolSpec) -> float:
    """Lot làm tròn XUỐNG theo bước lot (lỗ tại SL không vượt `risk_money`); 0 nếu dưới lot tối thiểu."""
    per_lot = spec.money(sl_distance, 1.0)
    if per_lot <= 0 or risk_money <= 0:
        return 0.0
    lot = min(floor_to_step(risk_money / per_lot, spec.volume_step), spec.volume_max)
    return lot if lot >= spec.volume_min else 0.0


def split_legs(lot: float, fraction: float, spec: SymbolSpec) -> tuple[float, ...]:
    """Chia lot thành (chân TP1, chân runner); không chia được thì trả một chân."""
    first = floor_to_step(lot * fraction, spec.volume_step)
    rest = round(lot - first, 8)
    if first >= spec.volume_min and rest >= spec.volume_min:
        return first, rest
    return (lot,)
