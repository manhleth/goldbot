"""Quy tắc quản lý lệnh đang mở (dùng chung cho backtest và live)."""
from __future__ import annotations

from collections.abc import Mapping

import pandas as pd

from core.types import Direction
from risk.calendar import minute_of_day, minutes, to_local
from structure.swings import Swing, of_kind


def improves(direction: Direction, new_sl: float, current_sl: float) -> bool:
    return (new_sl - current_sl) * direction > 0


def breakeven_due(favorable: float, risk: float, at_r: float | None) -> bool:
    """Giá đã chạy thuận được `at_r` lần rủi ro ban đầu → dời SL về giá vào. None = tắt."""
    return at_r is not None and risk > 0 and favorable >= at_r * risk


def trail_stop(direction: Direction, swings: list[Swing], current_sl: float, last_close: float,
               buffer: float) -> float | None:
    """SL mới theo swing ngược chiều gần nhất (BUY: swing low), chỉ khi tốt hơn SL hiện tại và nằm phía sau giá."""
    pivots = of_kind(swings, "low" if direction == Direction.BUY else "high")
    if not pivots:
        return None
    candidate = pivots[-1].price - direction * buffer
    if improves(direction, candidate, current_sl) and (last_close - candidate) * direction > 0:
        return candidate
    return None


def breaks_invalidation(direction: Direction, close: float, invalidation: float) -> bool:
    return (invalidation - close) * direction > 0


def trading_date(ts: pd.Timestamp, sessions_cfg: Mapping):
    """Ngày giao dịch: ngày mới bắt đầu lúc `sessions.trading_day_start` (giờ địa phương, vd 17:00 New York)."""
    shift = pd.Timedelta(minutes=24 * 60 - minutes(sessions_cfg["trading_day_start"]))
    return (to_local(ts, sessions_cfg) + shift).date()


def past_flat_time(now: pd.Timestamp, mg: Mapping, sessions_cfg: Mapping) -> bool:
    """Đã tới giờ đóng lệnh: hằng ngày từ `flat_time`, hoặc (nếu đặt `flat_weekday`) từ `flat_time` của ngày đó trong tuần."""
    flat_time, weekday = mg["flat_time"], mg["flat_weekday"]
    if not flat_time:
        return False
    after = minute_of_day(to_local(now, sessions_cfg)) >= minutes(flat_time)
    if weekday is None:
        return after
    day = trading_date(now, sessions_cfg).weekday()
    return day > weekday or (day == weekday and after)


def must_flatten(entry_time: pd.Timestamp, now: pd.Timestamp, mg: Mapping, sessions_cfg: Mapping) -> bool:
    """Đóng lệnh khi tới giờ đóng, hoặc đã sang ngày (chế độ ngày) / tuần giao dịch (chế độ tuần) khác lúc vào."""
    if not mg["flat_time"]:
        return False
    if mg["flat_weekday"] is None:
        moved_on = to_local(now, sessions_cfg).date() > to_local(entry_time, sessions_cfg).date()
    else:
        week = lambda ts: trading_date(ts, sessions_cfg).isocalendar()[:2]  # noqa: E731
        moved_on = week(now) != week(entry_time)
    return moved_on or past_flat_time(now, mg, sessions_cfg)
