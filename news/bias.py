"""Quy đổi dự báo tin kinh tế Mỹ thành chiều kỳ vọng cho vàng (xác định, cấu hình được).

Mỗi quy tắc: `match` (chuỗi con trong tiêu đề, không phân biệt hoa thường) và `usd` = +1 nếu số cao hơn → USD mạnh,
-1 nếu số cao hơn → USD yếu. Vàng ngược chiều USD. Quy tắc đầu tiên khớp được dùng.
"""
from __future__ import annotations

import re
from collections.abc import Iterable, Mapping

from core.types import Direction
from news.models import NewsEvent

_NUMBER = re.compile(r"^\s*(-?\d+(?:\.\d+)?)\s*([%KMBT]?)\s*$", re.IGNORECASE)
_SCALE = {"": 1.0, "%": 1.0, "K": 1e3, "M": 1e6, "B": 1e9, "T": 1e12}


def parse_value(text: str) -> float | None:
    """'0.3%' → 0.3, '201K' → 201000, '-134.4B' → -1.344e11; không phải số → None."""
    match = _NUMBER.match(text or "")
    if not match:
        return None
    return float(match.group(1)) * _SCALE[match.group(2).upper()]


def usd_polarity(title: str, rules: Iterable[Mapping]) -> int:
    lowered = title.lower()
    for rule in rules:
        if rule["match"].lower() in lowered:
            return int(rule["usd"])
    return 0


def gold_bias(event: NewsEvent, rules: Iterable[Mapping]) -> Direction:
    """Chiều kỳ vọng cho vàng từ (forecast - previous); thiếu số, bằng nhau hoặc không có quy tắc → NEUTRAL."""
    forecast, previous = parse_value(event.forecast), parse_value(event.previous)
    polarity = usd_polarity(event.title, rules)
    if forecast is None or previous is None or polarity == 0 or forecast == previous:
        return Direction.NEUTRAL
    usd = polarity if forecast > previous else -polarity
    return Direction(-usd)
