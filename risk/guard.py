"""Giới hạn rủi ro tài khoản trước khi mở lệnh."""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from core.types import Direction, TradePlan, Zone
from risk.calendar import in_blocked_window, in_sessions
from risk.management import past_flat_time


@dataclass(frozen=True, slots=True)
class Exposure:
    direction: Direction
    zone: Zone


@dataclass(frozen=True, slots=True)
class LossStreak:
    count: int = 0
    paused_until: pd.Timestamp | None = None


@dataclass(frozen=True, slots=True)
class AccountSnapshot:
    equity: float
    day_start_equity: float
    exposures: tuple[Exposure, ...]
    streak: LossStreak


def register_result(streak: LossStreak, r_multiple: float, time: pd.Timestamp, risk_cfg: dict) -> LossStreak:
    """Cập nhật chuỗi thua; đủ ngưỡng thì tạm dừng và đặt lại bộ đếm. Hòa vốn (R=0) không đổi chuỗi."""
    if r_multiple > 0:
        return LossStreak(0, streak.paused_until)
    if r_multiple == 0:
        return streak
    count = streak.count + 1
    if count >= risk_cfg["max_consecutive_losses"]:
        return LossStreak(0, time + pd.Timedelta(hours=risk_cfg["consecutive_loss_pause_hours"]))
    return LossStreak(count, streak.paused_until)


def block_reason(plan: TradePlan, snap: AccountSnapshot, now: pd.Timestamp, spread_points: float,
                 cfg: dict) -> str | None:
    rc = cfg["risk"]
    if snap.streak.paused_until is not None and now < snap.streak.paused_until:
        return "paused_after_losses"
    if snap.day_start_equity > 0 and \
            (snap.day_start_equity - snap.equity) / snap.day_start_equity * 100 >= rc["max_daily_loss_pct"]:
        return "daily_loss_limit"
    if len(snap.exposures) >= rc["max_open_trades"]:
        return "max_open_trades"
    zone = plan.signal.setup.zone
    if any(e.direction == plan.signal.direction and e.zone.overlaps(zone.low, zone.high) for e in snap.exposures):
        return "same_direction_same_zone"
    if spread_points > rc["max_spread_points"]:
        return "spread_too_wide"
    if in_blocked_window(now, cfg.get("blocked_windows_utc") or []):
        return "blocked_window"
    if not in_sessions(now, rc["entry_sessions"], cfg["sessions"]):
        return "outside_killzone"
    if past_flat_time(now, cfg["management"], cfg["sessions"]):
        return "after_flat_time"
    return None
