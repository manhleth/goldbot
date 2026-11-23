"""Đọc lịch tuần hiện tại từ feed JSON của ForexFactory."""
from __future__ import annotations

import json
import urllib.request

import pandas as pd

from news.models import NewsEvent

_USER_AGENT = "Mozilla/5.0 (compatible; local-calendar-client)"


def parse_feed(items: list[dict]) -> list[NewsEvent]:
    events = []
    for item in items:
        try:
            when = pd.Timestamp(item["date"]).tz_convert("UTC")
        except (KeyError, ValueError, TypeError):
            continue
        events.append(NewsEvent(when, item.get("title", ""), item.get("country", ""), item.get("impact", ""),
                                item.get("forecast", "") or "", item.get("previous", "") or ""))
    return events


def fetch_week(url: str, timeout: float = 20.0) -> list[NewsEvent]:
    request = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return parse_feed(json.loads(response.read().decode("utf-8")))
