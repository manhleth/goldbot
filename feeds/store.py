"""Lưu bài đăng channel vào SQLite (idempotent theo channel + post_id)."""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pandas as pd

from feeds.telegram_public import Post

SCHEMA = """
CREATE TABLE IF NOT EXISTS posts (
    channel TEXT, post_id INTEGER, time TEXT, text TEXT, photos TEXT, views TEXT, edited INTEGER, fetched_at TEXT,
    PRIMARY KEY (channel, post_id)
);
CREATE TABLE IF NOT EXISTS calls (
    channel TEXT, post_id INTEGER, time TEXT, symbol TEXT, is_analysis INTEGER, timeframe TEXT, direction TEXT,
    price_at_chart REAL, targets TEXT, invalidation REAL, horizon TEXT, tools TEXT, fib_levels TEXT, drawing TEXT,
    confidence TEXT, note TEXT, label_source TEXT, PRIMARY KEY (channel, post_id)
);
CREATE TABLE IF NOT EXISTS media (
    channel TEXT, post_id INTEGER, idx INTEGER, url TEXT, path TEXT, PRIMARY KEY (channel, post_id, idx)
);
"""


class FeedStore:
    def __init__(self, path: str | Path) -> None:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(path))
        self._conn.executescript(SCHEMA)

    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> "FeedStore":
        return self

    def __exit__(self, *_exc) -> None:
        self.close()

    def upsert(self, posts: list[Post]) -> int:
        """Ghi/cập nhật bài; trả số bài mới."""
        if not posts:
            return 0
        known = self.known_ids(posts[0].channel)
        now = pd.Timestamp.now(tz="UTC").isoformat()
        self._conn.executemany(
            "INSERT OR REPLACE INTO posts VALUES (?,?,?,?,?,?,?,?)",
            [(p.channel, p.post_id, p.time.isoformat(), p.text, json.dumps(p.photos), p.views, int(p.edited), now)
             for p in posts])
        self._conn.commit()
        return sum(p.post_id not in known for p in posts)

    def known_ids(self, channel: str) -> set[int]:
        return {row[0] for row in self._conn.execute("SELECT post_id FROM posts WHERE channel = ?", [channel])}

    def oldest_id(self, channel: str) -> int | None:
        row = self._conn.execute("SELECT MIN(post_id) FROM posts WHERE channel = ?", [channel]).fetchone()
        return row[0]

    def posts(self, channel: str) -> pd.DataFrame:
        return pd.read_sql("SELECT * FROM posts WHERE channel = ? ORDER BY post_id", self._conn, params=[channel])

    def missing_media(self, channel: str, only_ids: set[int] | None = None) -> list[tuple[int, int, str]]:
        rows = self._conn.execute("SELECT post_id, photos FROM posts WHERE channel = ?", [channel]).fetchall()
        rows = [r for r in rows if only_ids is None or r[0] in only_ids]
        have = {(r[0], r[1]) for r in self._conn.execute("SELECT post_id, idx FROM media WHERE channel = ?", [channel])}
        return [(pid, i, url) for pid, photos in rows for i, url in enumerate(json.loads(photos))
                if (pid, i) not in have]

    def save_calls(self, channel: str, labels: list[dict]) -> None:
        """Nhãn nhận định (ghi tay hoặc đọc ảnh), một dòng mỗi bài."""
        cols = ("post_id", "time", "symbol", "is_analysis", "timeframe", "direction", "price_at_chart", "targets",
                "invalidation", "horizon", "tools", "fib_levels", "drawing", "confidence", "note", "label_source")
        rows = []
        for lab in labels:
            values = [json.dumps(lab.get(c) or [], ensure_ascii=False) if c in ("targets", "tools", "fib_levels")
                      else (int(bool(lab.get(c))) if c == "is_analysis" else lab.get(c)) for c in cols]
            rows.append([channel, *values])
        self._conn.executemany(f"INSERT OR REPLACE INTO calls VALUES ({','.join('?' * (len(cols) + 1))})", rows)
        self._conn.commit()

    def calls(self, channel: str) -> pd.DataFrame:
        return pd.read_sql("SELECT * FROM calls WHERE channel = ? ORDER BY post_id", self._conn, params=[channel])

    def add_media(self, channel: str, post_id: int, idx: int, url: str, path: str) -> None:
        self._conn.execute("INSERT OR REPLACE INTO media VALUES (?,?,?,?,?)", [channel, post_id, idx, url, path])
        self._conn.commit()
