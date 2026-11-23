import pandas as pd
import pytest

from core.types import Direction, Setup, Signal, TradePlan, Zone
from risk.calendar import in_blocked_window, in_news_blackout, in_window_minutes, parse_events, session_of
from risk.guard import AccountSnapshot, Exposure, LossStreak, block_reason, register_result
from risk.management import breaks_invalidation, must_flatten, trail_stop
from risk.planner import pick_tp1, stop_loss
from risk.sizing import SymbolSpec, lot_size, risk_budget, split_legs
from structure.swings import Swing

SPEC = SymbolSpec(point=0.01, tick_size=0.01, tick_value=1.0, volume_min=0.01, volume_step=0.01, volume_max=100)
T = pd.Timestamp("2024-03-06 10:00", tz="UTC")  # thứ Tư


def _signal(direction=Direction.BUY, invalidation=99.0, extreme=99.5):
    setup = Setup("fvg_retest", direction, Zone(99.0, 100.0), invalidation, 1, (), "k")
    return Signal(T, setup, "engulfing", extreme, 101.0, 50.0, {"D1": direction})


def test_lot_size_rounds_down_and_respects_min():
    # rủi ro 100$; SL 5.00 giá = 500 tick * 1$ = 500$/lot → 0.2 lot
    assert lot_size(100, 5.0, SPEC) == pytest.approx(0.2)
    assert lot_size(100, 3.0, SPEC) == pytest.approx(0.33)
    assert lot_size(1, 50.0, SPEC) == 0.0


def test_risk_budget_modes():
    assert risk_budget(1000, {"sizing": "fixed_money", "risk_per_trade_money": 20}) == 20
    assert risk_budget(1000, {"sizing": "percent", "risk_per_trade_pct": 1.5}) == pytest.approx(15)


def test_fixed_money_risk_never_exceeds_budget():
    spec = SymbolSpec(point=0.01, tick_size=0.01, tick_value=0.1, volume_min=0.01, volume_step=0.01, volume_max=100)
    for distance in (3.7, 12.3, 27.9, 55.5):
        lot = lot_size(20, distance, spec)
        assert spec.money(distance, lot) <= 20 + 1e-9


def test_split_legs():
    assert split_legs(0.33, 0.5, SPEC) == (0.16, 0.17)
    assert split_legs(0.01, 0.5, SPEC) == (0.01,)


def test_stop_loss_below_lowest_anchor_plus_buffer():
    assert stop_loss(_signal(extreme=98.0), atr=2.0, buffer_atr=0.3) == pytest.approx(97.4)
    sell = _signal(Direction.SELL, invalidation=101.0, extreme=100.5)
    assert stop_loss(sell, atr=2.0, buffer_atr=0.3) == pytest.approx(101.6)


def test_stop_loss_behind_zone_far_edge():
    buy = _signal(invalidation=97.0, extreme=99.5)  # vùng (99, 100), đáy cú quét 97
    assert stop_loss(buy, atr=2.0, buffer_atr=0.3, anchor="zone") == pytest.approx(98.4)
    assert stop_loss(_signal(invalidation=97.0, extreme=98.5), atr=2.0, buffer_atr=0.3, anchor="zone") == pytest.approx(97.9)
    sell = _signal(Direction.SELL, invalidation=102.0, extreme=99.8)
    assert stop_loss(sell, atr=2.0, buffer_atr=0.3, anchor="zone") == pytest.approx(100.6)


def test_pick_tp1_modes():
    rc = {"min_rr_tp1": 1.5, "tp1_mode": "nearest", "tp1_fallback_rr": None}
    assert pick_tp1(100, 2, Direction.BUY, [102, 104], rc) is None  # gần nhất chỉ 1R
    assert pick_tp1(100, 2, Direction.BUY, [103, 104], rc) == 103
    assert pick_tp1(100, 2, Direction.BUY, [102, 104], {**rc, "tp1_mode": "first_valid"}) == 104
    assert pick_tp1(100, 2, Direction.BUY, [], rc) is None
    assert pick_tp1(100, 2, Direction.BUY, [], {**rc, "tp1_fallback_rr": 2.0}) == 104
    fixed = {**rc, "tp1_mode": "fixed_rr", "tp1_rr": 2.0}
    assert pick_tp1(100, 2, Direction.BUY, [101], fixed) == 104
    assert pick_tp1(100, 2, Direction.SELL, [], fixed) == 96


def _plan(direction=Direction.BUY):
    return TradePlan(_signal(direction), 101.0, 97.0, 107.0, None)


def _snap(equity=10_000, day_start=10_000, exposures=(), streak=LossStreak()):
    return AccountSnapshot(equity, day_start, tuple(exposures), streak)


def test_guard_reasons(cfg):
    cfg["risk"]["entry_sessions"] = []
    plan = _plan()
    assert block_reason(plan, _snap(), T, 20, cfg) is None
    assert block_reason(plan, _snap(equity=9_690), T, 20, cfg) == "daily_loss_limit"
    assert block_reason(plan, _snap(exposures=[Exposure(Direction.SELL, Zone(1, 2))] * 2), T, 20, cfg) == \
        "max_open_trades"
    assert block_reason(plan, _snap(exposures=[Exposure(Direction.BUY, Zone(99.5, 100.5))]), T, 20, cfg) == \
        "same_direction_same_zone"
    assert block_reason(plan, _snap(), T, 60, cfg) == "spread_too_wide"
    assert block_reason(plan, _snap(streak=LossStreak(0, T + pd.Timedelta(hours=1))), T, 20, cfg) == \
        "paused_after_losses"
    friday_late = pd.Timestamp("2024-03-08 21:00", tz="UTC")
    assert block_reason(plan, _snap(), friday_late, 20, cfg) == "blocked_window"


def test_loss_streak_pauses_and_resets(cfg):
    streak = LossStreak()
    for _ in range(3):
        streak = register_result(streak, -1.0, T, cfg["risk"])
    assert streak.count == 3 and streak.paused_until is None
    streak = register_result(streak, -1.0, T, cfg["risk"])
    assert streak.count == 0 and streak.paused_until == T + pd.Timedelta(hours=8)
    assert register_result(LossStreak(2), 0.0, T, cfg["risk"]).count == 2
    assert register_result(LossStreak(2), 1.2, T, cfg["risk"]).count == 0


def test_calendar_helpers(cfg):
    assert session_of(pd.Timestamp("2024-01-10 08:00", tz="UTC"), cfg["sessions"]) == "london"   # 03:00 NY
    assert session_of(pd.Timestamp("2024-07-10 08:00", tz="UTC"), cfg["sessions"]) == "london"   # 04:00 NY (DST)
    assert session_of(pd.Timestamp("2024-01-10 01:00", tz="UTC"), cfg["sessions"]) == "asia"     # 20:00 NY
    assert in_blocked_window(pd.Timestamp("2024-03-09 10:00", tz="UTC"), cfg["blocked_windows_utc"])  # thứ Bảy
    events = parse_events(["2024-03-06T13:30:00Z"])
    assert in_news_blackout(pd.Timestamp("2024-03-06 13:00", tz="UTC"), events, 30)
    assert not in_news_blackout(pd.Timestamp("2024-03-06 12:59", tz="UTC"), events, 30)


def test_trail_and_invalidation():
    swings = [Swing(1, T, 98.0, "low", 3), Swing(5, T, 100.0, "low", 7)]
    assert trail_stop(Direction.BUY, swings, 97.0, 103.0, 0.0) == 100.0
    assert trail_stop(Direction.BUY, swings, 100.5, 103.0, 0.0) is None
    assert breaks_invalidation(Direction.BUY, 98.9, 99.0)
    assert not breaks_invalidation(Direction.SELL, 98.9, 99.0)


def test_killzone_and_flat_time(cfg):
    cfg["risk"]["entry_sessions"] = ["london", "newyork"]
    plan = _plan()
    ny_open = pd.Timestamp("2024-01-10 12:30", tz="UTC")   # 07:30 NY
    midday = pd.Timestamp("2024-01-10 16:30", tz="UTC")    # 11:30 NY
    assert block_reason(plan, _snap(), ny_open, 20, cfg) is None
    assert block_reason(plan, _snap(), midday, 20, cfg) == "outside_killzone"
    entry = ny_open
    daily, off = {"flat_time": "16:00", "flat_weekday": None}, {"flat_time": None, "flat_weekday": None}
    assert not must_flatten(entry, pd.Timestamp("2024-01-10 20:45", tz="UTC"), daily, cfg["sessions"])  # 15:45 NY
    assert must_flatten(entry, pd.Timestamp("2024-01-10 21:00", tz="UTC"), daily, cfg["sessions"])      # 16:00 NY
    assert must_flatten(entry, pd.Timestamp("2024-01-11 06:00", tz="UTC"), daily, cfg["sessions"])      # ngày sau
    assert not must_flatten(entry, pd.Timestamp("2024-01-11 06:00", tz="UTC"), off, cfg["sessions"])


def test_weekly_flat_holds_overnight_until_friday(cfg):
    weekly = {"flat_time": "16:00", "flat_weekday": 4}
    sunday_open = pd.Timestamp("2024-01-07 23:30", tz="UTC")  # CN 18:30 NY = ngày giao dịch thứ Hai
    s = cfg["sessions"]
    assert not must_flatten(sunday_open, pd.Timestamp("2024-01-10 21:00", tz="UTC"), weekly, s)  # T4 16:00 NY
    assert not must_flatten(sunday_open, pd.Timestamp("2024-01-12 20:55", tz="UTC"), weekly, s)  # T6 15:55 NY
    assert must_flatten(sunday_open, pd.Timestamp("2024-01-12 21:00", tz="UTC"), weekly, s)      # T6 16:00 NY
    assert must_flatten(sunday_open, pd.Timestamp("2024-01-14 23:30", tz="UTC"), weekly, s)      # tuần sau
    cfg["management"].update(weekly)
    cfg["blocked_windows_utc"] = []
    assert block_reason(_plan(), _snap(), pd.Timestamp("2024-01-12 21:30", tz="UTC"), 20, cfg) == "after_flat_time"
    assert block_reason(_plan(), _snap(), pd.Timestamp("2024-01-11 21:30", tz="UTC"), 20, cfg) is None


def test_window_wraps_midnight():
    assert in_window_minutes(21 * 60, "20:00", "00:00") and not in_window_minutes(60, "20:00", "00:00")
    assert in_window_minutes(30, "23:00", "02:00") and not in_window_minutes(12 * 60, "23:00", "02:00")
