"""Lưu dồn lịch tin vào SQLite (feed chỉ có tuần hiện tại) và nhập lịch sử từ CSV."""
from __future__ import annotations

import io
import logging
import sqlite3
from pathlib import Path

import pandas as pd

from news.forexfactory import fetch_week
from news.models import NewsEvent

log = logging.getLogger(__name__)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS news_events (
    key TEXT PRIMARY KEY, time TEXT, title TEXT, country TEXT, impact TEXT,
    forecast TEXT, previous TEXT, source TEXT
);
CREATE INDEX IF NOT EXISTS idx_news_time ON news_events(time);
CREATE TABLE IF NOT EXISTS news_meta (key TEXT PRIMARY KEY, value TEXT);
"""
CSV_COLUMNS = ["time", "title", "country", "impact", "forecast", "previous"]


class NewsStore:
    def __init__(self, path: str | Path) -> None:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self._path = str(path)
        with self._connect() as conn:
            conn.executescript(_SCHEMA)

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self._path, timeout=10)

    def upsert(self, events: list[NewsEvent]) -> int:
        rows = [(e.key, e.time.isoformat(), e.title, e.country, e.impact, e.forecast, e.previous, e.source)
                for e in events]
        with self._connect() as conn:
            conn.executemany("INSERT INTO news_events VALUES (?, ?, ?, ?, ?, ?, ?, ?) ON CONFLICT(key) DO UPDATE SET "
                             "impact = excluded.impact, forecast = excluded.forecast, previous = excluded.previous",
                             rows)
        return len(rows)

    def all(self) -> list[NewsEvent]:
        with self._connect() as conn:
            rows = conn.execute("SELECT time, title, country, impact, forecast, previous, source "
                                "FROM news_events ORDER BY time").fetchall()
        return [NewsEvent(pd.Timestamp(r[0]), r[1], r[2], r[3], r[4] or "", r[5] or "", r[6]) for r in rows]

    def last_refresh(self) -> pd.Timestamp | None:
        with self._connect() as conn:
            row = conn.execute("SELECT value FROM news_meta WHERE key = 'last_refresh'").fetchone()
        return pd.Timestamp(row[0]) if row else None

    def _mark_refreshed(self, when: pd.Timestamp) -> None:
        with self._connect() as conn:
            conn.execute("INSERT INTO news_meta VALUES ('last_refresh', ?) "
                         "ON CONFLICT(key) DO UPDATE SET value = excluded.value", [when.isoformat()])

    def refresh(self, url: str, now: pd.Timestamp) -> int:
        count = self.upsert(fetch_week(url))
        self._mark_refreshed(now)
        log.info("Đã cập nhật %d tin từ ForexFactory", count)
        return count

    def refresh_if_stale(self, url: str, now: pd.Timestamp, max_age_minutes: float) -> bool:
        """Không bao giờ ném lỗi mạng ra ngoài: lỗi chỉ log, bot vẫn chạy với dữ liệu đã lưu."""
        last = self.last_refresh()
        if last is not None and now - last < pd.Timedelta(minutes=max_age_minutes):
            return False
        try:
            self.refresh(url, now)
            return True
        except Exception:  # noqa: BLE001
            log.exception("Không tải được lịch tin, dùng dữ liệu đã lưu")
            return False

    def import_csv(self, content: bytes) -> int:
        """CSV cột: time (UTC hoặc có múi giờ), title, country, impact, forecast, previous."""
        df = pd.read_csv(io.BytesIO(content), dtype=str).fillna("")
        missing = set(CSV_COLUMNS) - set(df.columns)
        if missing:
            raise ValueError(f"CSV thiếu cột: {sorted(missing)}")
        times = pd.to_datetime(df["time"], utc=True, format="mixed")
        events = [NewsEvent(t, r.title, r.country, r.impact, r.forecast, r.previous, "csv")
                  for t, r in zip(times, df.itertuples(index=False))]
        return self.upsert(events)
