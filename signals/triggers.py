"""Nến xác nhận ở khung vào lệnh: engulfing, pin bar, CHoCH nhỏ."""
from __future__ import annotations

from collections.abc import Callable

from core.types import Direction
from mtf.view import TimeframeView


def is_engulfing(view: TimeframeView, direction: Direction, cfg: dict) -> bool:
    df = view.df
    if len(df) < 2:
        return False
    o, c = df["open"].iat[-1], df["close"].iat[-1]
    po, pc = df["open"].iat[-2], df["close"].iat[-2]
    if direction == Direction.BUY:
        return c > o and pc < po and c >= po and o <= pc
    return c < o and pc > po and c <= po and o >= pc


def is_pin_bar(view: TimeframeView, direction: Direction, cfg: dict) -> bool:
    """Bóng về phía vùng bị từ chối >= ratio * thân, lớn hơn bóng còn lại và >= tỉ lệ tối thiểu của biên độ."""
    tc = cfg["trigger"]
    row = view.df.iloc[-1]
    o, h, l, c = row["open"], row["high"], row["low"], row["close"]
    rng = h - l
    if rng <= 0:
        return False
    body = abs(c - o)
    lower, upper = min(o, c) - l, h - max(o, c)
    wick, other = (lower, upper) if direction == Direction.BUY else (upper, lower)
    return wick >= tc["pin_wick_body_ratio"] * body and wick > other and wick >= tc["pin_min_wick_range"] * rng


def is_mini_choch(view: TimeframeView, direction: Direction, cfg: dict) -> bool:
    last = len(view.df) - 1
    return any(b.index == last and b.direction == direction for b in view.breaks)


TRIGGERS: dict[str, Callable[[TimeframeView, Direction, dict], bool]] = {
    "engulfing": is_engulfing,
    "pin_bar": is_pin_bar,
    "mini_choch": is_mini_choch,
}


def detect_trigger(view: TimeframeView, direction: Direction, cfg: dict) -> str | None:
    for name in cfg["trigger"]["types"]:
        if name in TRIGGERS and TRIGGERS[name](view, direction, cfg):
            return name
    return None
