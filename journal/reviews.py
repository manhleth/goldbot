"""Nét vẽ tay + nhận xét của người dùng cho chart chung và từng lệnh/tín hiệu (SQLite riêng, không phụ thuộc journal bot).

`scope` là khóa ổn định: "chart:<symbol>" cho chart chung, "setup:<mode>:[<run_id>:]<setup_key>" cho một ý tưởng lệnh
(lệnh đang mở → đã đóng và tín hiệu dùng chung), "<kind>:<mode>:<run_id>:<id>" khi không có setup_key. Bot không tự học từ đây: dữ liệu dùng để đọc lại, tìm lỗi lặp lại
rồi đề xuất sửa quy tắc và backtest lại (quy tắc vào lệnh vẫn xác định).
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pandas as pd

SCHEMA = """
CREATE TABLE IF NOT EXISTS annotations (
    scope TEXT PRIMARY KEY, shapes TEXT, verdict TEXT, errors TEXT, note TEXT, snapshot TEXT, updated_at TEXT
);
"""
JSON_FIELDS = ("shapes", "errors", "snapshot")
FIELDS = ("shapes", "verdict", "errors", "note", "snapshot")


def _decode(row: sqlite3.Row) -> dict:
    out = dict(row)
    for key in JSON_FIELDS:
        out[key] = json.loads(out[key]) if out.get(key) else None
    return out


class ReviewStore:
    def __init__(self, path: str | Path) -> None:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(path))
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(SCHEMA)

    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> ReviewStore:
        return self

    def __exit__(self, *_exc) -> None:
        self.close()

    def get(self, scope: str) -> dict | None:
        row = self._conn.execute("SELECT * FROM annotations WHERE scope = ?", [scope]).fetchone()
        return _decode(row) if row else None

    def save(self, scope: str, values: dict, now: pd.Timestamp) -> dict:
        """Ghi đè các trường có trong `values` (trường vắng mặt giữ nguyên)."""
        current = self.get(scope) or {}
        merged = {k: values[k] if k in values else current.get(k) for k in FIELDS}
        row = [scope, *[json.dumps(merged[k], ensure_ascii=False) if k in JSON_FIELDS and merged[k] is not None
                         else merged[k] for k in FIELDS], now.isoformat()]
        self._conn.execute(f"INSERT OR REPLACE INTO annotations (scope, {', '.join(FIELDS)}, updated_at) "
                           f"VALUES ({', '.join('?' * (len(FIELDS) + 2))})", row)
        self._conn.commit()
        return self.get(scope)

    def reviewed(self) -> list[dict]:
        """Mọi lệnh/tín hiệu đã có nhận xét hoặc nét vẽ (bỏ chart chung), mới nhất trước."""
        rows = self._conn.execute("SELECT * FROM annotations WHERE scope NOT LIKE 'chart:%' "
                                  "ORDER BY updated_at DESC").fetchall()
        return [_decode(r) for r in rows]
