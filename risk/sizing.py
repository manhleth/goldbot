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


def lot_size(risk_money: float, sl_distance: float, spec: SymbolSpec, min_lot_fallback: bool = False) -> float:
    """Lot làm tròn XUỐNG theo bước lot (lỗ tại SL không vượt `risk_money`); dưới lot tối thiểu → 0, hoặc lot tối thiểu
    nếu `min_lot_fallback` (khi đó lỗ tại SL có thể vượt `risk_money`)."""
    per_lot = spec.money(sl_distance, 1.0)
    if per_lot <= 0 or risk_money <= 0:
        return 0.0
    lot = min(floor_to_step(risk_money / per_lot, spec.volume_step), spec.volume_max)
    if lot >= spec.volume_min:
        return lot
    return spec.volume_min if min_lot_fallback else 0.0


def split_legs(lot: float, fraction: float, spec: SymbolSpec) -> tuple[float, ...]:
    """Chia lot thành (chân TP1, chân runner); không chia được thì trả một chân."""
    first = floor_to_step(lot * fraction, spec.volume_step)
    rest = round(lot - first, 8)
    if first >= spec.volume_min and rest >= spec.volume_min:
        return first, rest
    return (lot,)


def capped_risk(base_pct: float, caps, capital: float) -> float:
    """% rủi ro bị chặn theo mốc vốn: `caps` = [[vốn ≥ X$, % tối đa], ...]; dùng mốc cao nhất đã đạt,
    % = min(`base_pct`, % tối đa của mốc). Chưa đạt mốc nào → `base_pct`."""
    pct = base_pct
    for threshold, cap in sorted(caps or [], key=lambda c: c[0]):
        if capital >= float(threshold):
            pct = min(base_pct, float(cap))
    return pct


def cent_account(spec: SymbolSpec, scale: float) -> SymbolSpec:
    """Thông số cho tài khoản cent: 1 lot cent = `scale` lot thường (thường 0.01) → giá trị tick × scale, lot tối đa
    của broker tính theo lot cent. Tiền vẫn tính bằng USD."""
    import dataclasses
    return dataclasses.replace(spec, tick_value=spec.tick_value * scale, volume_max=spec.volume_max / scale)


def capped(spec: SymbolSpec, max_lot: float | None) -> SymbolSpec:
    """Thông số symbol với khối lượng tối đa mỗi lệnh = min(broker, `max_lot`)."""
    if not max_lot:
        return spec
    import dataclasses
    return dataclasses.replace(spec, volume_max=min(spec.volume_max, float(max_lot)))

