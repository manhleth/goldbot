"""Khung giờ: phiên giao dịch theo múi giờ cấu hình (mặc định New York, tự theo DST), tin tức, giờ cấm (UTC)."""
from __future__ import annotations

from collections.abc import Iterable, Mapping

import pandas as pd

DAY_MINUTES = 24 * 60


def minutes(hhmm: str) -> int:
    hours, mins = hhmm.split(":")
    return int(hours) * 60 + int(mins)


def minute_of_day(ts: pd.Timestamp) -> int:
    return ts.hour * 60 + ts.minute


def in_window_minutes(minute: int, start: str, end: str) -> bool:
    """[start, end) trong ngày; end "00:00" = nửa đêm; start > end = qua nửa đêm."""
    lo, hi = minutes(start), minutes(end) or DAY_MINUTES
    if lo < hi:
        return lo <= minute < hi
    return minute >= lo or minute < hi


def in_window(ts: pd.Timestamp, start: str, end: str) -> bool:
    return in_window_minutes(minute_of_day(ts), start, end)


def to_local(ts: pd.Timestamp, sessions_cfg: Mapping) -> pd.Timestamp:
    return ts.tz_convert(sessions_cfg["timezone"])


def in_sessions(ts: pd.Timestamp, names: Iterable[str], sessions_cfg: Mapping) -> bool:
    """True nếu `names` rỗng (không giới hạn) hoặc ts nằm trong một phiên được liệt kê."""
    names = list(names)
    if not names:
        return True
    local = to_local(ts, sessions_cfg)
    windows = sessions_cfg["windows"]
    return any(in_window(local, *windows[name]) for name in names)


def session_of(ts: pd.Timestamp, sessions_cfg: Mapping) -> str:
    local = to_local(ts, sessions_cfg)
    for name, (start, end) in sessions_cfg["windows"].items():
        if in_window(local, start, end):
            return name
    return "other"


def in_blocked_window(ts: pd.Timestamp, windows: Iterable[Mapping]) -> bool:
    """Giờ cấm theo UTC (vd cuối tuần)."""
    return any(ts.weekday() in w["days"] and in_window(ts, w["start"], w["end"]) for w in windows)


def parse_events(raw: Iterable) -> list[pd.Timestamp]:
    events = []
    for item in raw:
        ts = pd.Timestamp(item)
        events.append(ts.tz_localize("UTC") if ts.tzinfo is None else ts.tz_convert("UTC"))
    return events


def in_news_blackout(ts: pd.Timestamp, events: Iterable[pd.Timestamp], minutes_: int) -> bool:
    window = pd.Timedelta(minutes=minutes_)
    return any(abs(ts - event) <= window for event in events)
