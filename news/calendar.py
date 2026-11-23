"""Lịch tin đã lọc (tiền tệ, mức impact) và các truy vấn theo thời điểm."""
from __future__ import annotations

import bisect
from collections.abc import Iterable, Mapping
from dataclasses import dataclass

import pandas as pd

from core.types import Direction
from news.bias import gold_bias
from news.models import NewsEvent


@dataclass(frozen=True, slots=True)
class ForecastView:
    direction: Direction  # chiều ròng cho vàng (NEUTRAL nếu cân hoặc không có tin)
    score: int
    events: tuple[tuple[NewsEvent, Direction], ...]


class NewsCalendar:
    def __init__(self, events: Iterable[NewsEvent], rules: list[Mapping]) -> None:
        self._events = sorted(events, key=lambda e: e.time)
        self._times = [e.time for e in self._events]
        self._rules = rules

    @property
    def events(self) -> list[NewsEvent]:
        return self._events

    def between(self, start: pd.Timestamp, end: pd.Timestamp) -> list[NewsEvent]:
        lo = bisect.bisect_left(self._times, start)
        hi = bisect.bisect_right(self._times, end)
        return self._events[lo:hi]

    def in_blackout(self, t: pd.Timestamp, minutes: int) -> NewsEvent | None:
        window = pd.Timedelta(minutes=minutes)
        found = self.between(t - window, t + window)
        return found[0] if found else None

    def bias_of(self, event: NewsEvent) -> Direction:
        return gold_bias(event, self._rules)

    def forecast_view(self, t: pd.Timestamp, lookahead_hours: float) -> ForecastView:
        """Tổng chiều kỳ vọng của các tin sắp ra trong (t, t + lookahead]."""
        upcoming = [e for e in self.between(t, t + pd.Timedelta(hours=lookahead_hours)) if e.time > t]
        scored = tuple((e, self.bias_of(e)) for e in upcoming)
        score = sum(int(d) for _, d in scored)
        direction = Direction.BUY if score > 0 else Direction.SELL if score < 0 else Direction.NEUTRAL
        return ForecastView(direction, score, scored)


def build_calendar(events: Iterable[NewsEvent], news_cfg: dict) -> NewsCalendar:
    currencies = set(news_cfg["currencies"])
    impacts = set(news_cfg["impacts"])
    manual = [NewsEvent(_utc(ts), "Manual event", "USD", "High", source="manual")
              for ts in news_cfg.get("manual_events") or []]
    selected = [e for e in events if e.country in currencies and e.impact in impacts]
    return NewsCalendar([*selected, *manual], news_cfg["usd_rules"])


def _utc(value) -> pd.Timestamp:
    ts = pd.Timestamp(value)
    return ts.tz_localize("UTC") if ts.tzinfo is None else ts.tz_convert("UTC")
