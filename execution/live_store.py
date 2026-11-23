"""Trạng thái live lưu trong SQLite để khởi động lại không mất dấu lệnh."""
from __future__ import annotations

import json
from collections import defaultdict

import pandas as pd

from core.types import Direction, Zone
from journal.db import Journal
from risk.guard import Exposure, LossStreak


class LiveStore:
    def __init__(self, journal: Journal) -> None:
        self._j = journal

    # ---------- chân lệnh ----------
    def add_leg(self, row: dict) -> None:
        self._j.insert("live_legs", [row])

    def update_leg(self, ticket: int, **fields) -> None:
        self._j.update("live_legs", "ticket", ticket, fields)

    def open_legs(self) -> list[dict]:
        return self._j.rows("SELECT * FROM live_legs WHERE status = 'open'")

    def legs_by_key(self, key: str) -> list[dict]:
        return self._j.rows("SELECT * FROM live_legs WHERE setup_key = ? ORDER BY ticket", [key])

    def key_traded(self, key: str) -> bool:
        return bool(self._j.rows("SELECT 1 FROM live_legs WHERE setup_key = ? LIMIT 1", [key]))

    def open_by_key(self) -> dict[str, list[dict]]:
        grouped: dict[str, list[dict]] = defaultdict(list)
        for leg in self.open_legs():
            grouped[leg["setup_key"]].append(leg)
        return dict(grouped)

    def exposures(self) -> tuple[Exposure, ...]:
        return tuple(Exposure(Direction(legs[0]["direction"]), Zone(legs[0]["zone_low"], legs[0]["zone_high"]))
                     for legs in self.open_by_key().values())

    # ---------- trạng thái ----------
    def day_start_equity(self, today: str, equity: float) -> float:
        key = f"day_start:{today}"
        stored = self._j.get_kv(key)
        if stored is None:
            self._j.set_kv(key, str(equity))
            return equity
        return float(stored)

    def streak(self) -> LossStreak:
        raw = self._j.get_kv("loss_streak")
        if raw is None:
            return LossStreak()
        data = json.loads(raw)
        paused = pd.Timestamp(data["paused_until"]) if data.get("paused_until") else None
        return LossStreak(data["count"], paused)

    def save_streak(self, streak: LossStreak) -> None:
        paused = streak.paused_until.isoformat() if streak.paused_until is not None else None
        self._j.set_kv("loss_streak", json.dumps({"count": streak.count, "paused_until": paused}))

    def last_bar(self) -> str | None:
        return self._j.get_kv("last_bar")

    def set_last_bar(self, value: str) -> None:
        self._j.set_kv("last_bar", value)
