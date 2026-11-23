"""Bộ lọc tin tức cho một tín hiệu: blackout quanh tin + dự báo ngược chiều."""
from __future__ import annotations

from core.types import Direction, Signal
from news.calendar import ForecastView, NewsCalendar


def forecast_view(signal: Signal, calendar: NewsCalendar, news_cfg: dict) -> ForecastView:
    return calendar.forecast_view(signal.time, news_cfg["lookahead_hours"])


def alignment(signal_direction: Direction, view: ForecastView) -> str:
    if view.direction == Direction.NEUTRAL:
        return "neutral" if view.events else "none"
    return "aligned" if view.direction == signal_direction else "against"


def news_reason(signal: Signal, calendar: NewsCalendar, view: ForecastView, news_cfg: dict) -> str | None:
    if not news_cfg["enabled"]:
        return None
    if calendar.in_blackout(signal.time, news_cfg["blackout_minutes"]) is not None:
        return "news_blackout"
    rule = news_cfg["forecast_rule"]
    tag = alignment(signal.direction, view)
    if rule == "block_against" and tag == "against":
        return "news_forecast_against"
    if rule == "require_aligned" and tag != "aligned":
        return "news_forecast_not_aligned"
    return None
