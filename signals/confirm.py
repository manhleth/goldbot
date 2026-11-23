"""Xác nhận setup bằng nến trigger ở khung vào lệnh."""
from __future__ import annotations

from dataclasses import dataclass

from core.types import Direction, Setup
from mtf.view import TimeframeView
from signals.triggers import detect_trigger

TOUCH = "touch"  # nến vào lệnh chạm vùng setup và đóng cửa chưa phá invalidation (không cần nến xác nhận)


@dataclass(frozen=True, slots=True)
class Trigger:
    name: str
    extreme: float
    close: float
    rsi: float


def confirm(setup: Setup, view: TimeframeView, cfg: dict) -> Trigger | None:
    """Nến trigger (hoặc nến ngay trước) phải chạm vùng setup, đóng cửa chưa phá invalidation, và là nến xác nhận."""
    df = view.df
    recent = df.iloc[-cfg["trigger"]["zone_lookback_bars"]:]
    zone = setup.zone
    if not ((recent["low"] <= zone.high) & (recent["high"] >= zone.low)).any():
        return None
    last = df.iloc[-1]
    if (last["close"] - setup.invalidation) * setup.direction <= 0:
        return None
    touching = bool(last["low"] <= zone.high and last["high"] >= zone.low)
    name = TOUCH if TOUCH in cfg["trigger"]["types"] and touching else detect_trigger(view, setup.direction, cfg)
    if name is None:
        return None
    extreme = last["low"] if setup.direction == Direction.BUY else last["high"]
    return Trigger(name, float(extreme), float(last["close"]), float(last["rsi"]))
