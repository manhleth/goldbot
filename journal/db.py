"""Nhật ký SQLite: runs, signals, trades, equity (+ bảng trạng thái cho live)."""
from __future__ import annotations

import json
import sqlite3
import uuid
from collections.abc import Iterable, Mapping
from pathlib import Path

import pandas as pd
import yaml

from core.config import config_hash

SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
    run_id TEXT PRIMARY KEY, mode TEXT, created_at TEXT, config_hash TEXT, config TEXT, params TEXT
);
CREATE TABLE IF NOT EXISTS signals (
    id INTEGER PRIMARY KEY AUTOINCREMENT, run_id TEXT, time TEXT, setup TEXT, direction TEXT, bias TEXT,
    zone_low REAL, zone_high REAL, score INTEGER, trigger TEXT, entry REAL, sl REAL, tp1 REAL, tp2 REAL,
    rr_tp1 REAL, accepted INTEGER, reject_reason TEXT, news TEXT, reasons TEXT, setup_key TEXT
);
CREATE TABLE IF NOT EXISTS trades (
    id INTEGER PRIMARY KEY AUTOINCREMENT, run_id TEXT, setup_key TEXT, setup TEXT, direction TEXT, bias TEXT,
    score INTEGER, entry_time TEXT, exit_time TEXT, entry REAL, sl REAL, tp1 REAL, tp2 REAL, volume REAL,
    r_multiple REAL, pnl REAL, exit_reason TEXT, mae_r REAL, mfe_r REAL, spread_entry REAL, news TEXT, reasons TEXT
);
CREATE TABLE IF NOT EXISTS equity (
    id INTEGER PRIMARY KEY AUTOINCREMENT, run_id TEXT, time TEXT, equity REAL, drawdown_pct REAL
);
CREATE TABLE IF NOT EXISTS live_legs (
    ticket INTEGER PRIMARY KEY, run_id TEXT, setup_key TEXT, setup TEXT, leg TEXT, direction INTEGER,
    volume REAL, entry REAL, initial_sl REAL, sl REAL, tp REAL, tp1 REAL, tp2 REAL, invalidation REAL,
    zone_low REAL, zone_high REAL, bias TEXT, score INTEGER, reasons TEXT, spread_entry REAL, news TEXT, opened_at TEXT,
    status TEXT, exit_price REAL, exit_time TEXT, exit_reason TEXT, profit REAL, mae REAL, mfe REAL
);
CREATE TABLE IF NOT EXISTS kv (key TEXT PRIMARY KEY, value TEXT);
CREATE INDEX IF NOT EXISTS idx_trades_run ON trades(run_id);
CREATE INDEX IF NOT EXISTS idx_signals_run ON signals(run_id);
"""


def _to_sql(value):
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    if isinstance(value, (list, tuple, dict)):
        return json.dumps(value, ensure_ascii=False, default=str)
    return value


class Journal:
    def __init__(self, path: str | Path) -> None:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(path))
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(SCHEMA)
        self._migrate()

    def _migrate(self) -> None:
        """Thêm cột mới cho journal cũ (không mất dữ liệu)."""
        added = (("trades", ("chart", "meta")), ("signals", ("meta",)),
                 ("live_legs", ("meta", "exit_at", "trail", "chart", "bot")))
        for table, columns in added:
            existing = {row[1] for row in self._conn.execute(f"PRAGMA table_info({table})")}
            for column in columns:
                if column not in existing:
                    self._conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} TEXT")
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> "Journal":
        return self

    def __exit__(self, *_exc) -> None:
        self.close()

    def create_run(self, mode: str, cfg: dict, params: Mapping | None = None) -> str:
        run_id = f"{mode}-{pd.Timestamp.now(tz='UTC'):%Y%m%d-%H%M%S}-{uuid.uuid4().hex[:6]}"
        self.insert("runs", [{
            "run_id": run_id, "mode": mode, "created_at": pd.Timestamp.now(tz="UTC"),
            "config_hash": config_hash(cfg), "config": yaml.safe_dump(cfg, allow_unicode=True, sort_keys=False),
            "params": dict(params or {}),
        }])
        return run_id

    def insert(self, table: str, rows: Iterable[Mapping]) -> None:
        rows = list(rows)
        if not rows:
            return
        columns = list(rows[0].keys())
        sql = f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({', '.join('?' * len(columns))})"
        self._conn.executemany(sql, [[_to_sql(row[c]) for c in columns] for row in rows])
        self._conn.commit()

    def update(self, table: str, key_column: str, key, fields: Mapping) -> None:
        assignments = ", ".join(f"{column} = ?" for column in fields)
        self._conn.execute(f"UPDATE {table} SET {assignments} WHERE {key_column} = ?",
                           [*(_to_sql(v) for v in fields.values()), key])
        self._conn.commit()

    def rows(self, sql: str, params: Iterable = ()) -> list[dict]:
        return [dict(r) for r in self._conn.execute(sql, list(params)).fetchall()]

    def frame(self, sql: str, params: Iterable = ()) -> pd.DataFrame:
        return pd.read_sql_query(sql, self._conn, params=list(params))

    def latest_run(self, mode: str | None = None) -> str | None:
        sql = "SELECT run_id FROM runs" + (" WHERE mode = ?" if mode else "") + " ORDER BY created_at DESC LIMIT 1"
        found = self.rows(sql, [mode] if mode else [])
        return found[0]["run_id"] if found else None

    def get_kv(self, key: str) -> str | None:
        found = self.rows("SELECT value FROM kv WHERE key = ?", [key])
        return found[0]["value"] if found else None

    def set_kv(self, key: str, value: str) -> None:
        self._conn.execute("INSERT INTO kv (key, value) VALUES (?, ?) "
                           "ON CONFLICT(key) DO UPDATE SET value = excluded.value", [key, value])
        self._conn.commit()
