import pandas as pd
import pytest

from backtest.simulator import Simulator
from core.types import Direction, Setup, Signal, TradePlan, Zone
from risk.sizing import SymbolSpec

SPEC = SymbolSpec(point=0.01, tick_size=0.01, tick_value=1.0, volume_min=0.01, volume_step=0.01, volume_max=100)
MGMT = {"move_to_breakeven": True, "trail_after_tp1": True, "trail_buffer_atr": 0.0, "breakeven_at_r": None}
T = pd.Timestamp("2024-03-06 10:00", tz="UTC")


def _plan(direction=Direction.BUY, entry=100.0, sl=98.0, tp1=103.0, tp2=106.0):
    setup = Setup("fvg_retest", direction, Zone(98.5, 99.5), 98.5, 1, (), "k")
    return TradePlan(Signal(T, setup, "engulfing", 98.5, entry, 50.0, {}), entry, sl, tp1, tp2)


def test_sl_and_tp_in_same_bar_counts_sl_first():
    sim = Simulator(SPEC, 0, MGMT)
    sim.open(_plan(), (0.1, 0.1), T, 0)
    closed = sim.on_bar(100, 104, 97, T, 0)
    assert len(closed) == 1 and closed[0].r_multiple() == pytest.approx(-1.0)


def test_tp1_then_breakeven_runner():
    sim = Simulator(SPEC, 0, MGMT)
    sim.open(_plan(), (0.1, 0.1), T, 0)
    assert sim.on_bar(100, 103.5, 99.5, T, 0) == []  # chạm TP1, runner còn
    pos = sim.open_positions[0]
    assert pos.tp1_done and pos.open_legs[0].sl == 100.0
    closed = sim.on_bar(101, 101.5, 99.0, T, 0)  # quay về hòa vốn
    assert closed[0].r_multiple() == pytest.approx(0.75)  # (0.5*1.5R + 0.5*0R)


def test_gap_through_sl_fills_at_open_with_slippage():
    sim = Simulator(SPEC, 5, MGMT)
    sim.open(_plan(), (0.2,), T, 0)
    closed = sim.on_bar(97.0, 97.5, 96.5, T, 0)
    assert closed[0].legs[0].exit_price == pytest.approx(96.95)


def test_sell_exits_on_ask():
    sim = Simulator(SPEC, 0, MGMT)
    sim.open(_plan(Direction.SELL, entry=100.0, sl=102.0, tp1=97.0, tp2=None), (0.1,), T, 0)
    # bid cao nhất 101.8 nhưng spread 30 điểm → ask 102.1 chạm SL
    closed = sim.on_bar(100, 101.8, 99.9, T, 30)
    assert closed and closed[0].r_multiple() == pytest.approx(-1.0)


def test_invalidation_close_exits_all_legs():
    sim = Simulator(SPEC, 0, MGMT)
    sim.open(_plan(), (0.1, 0.1), T, 0)
    closed = sim.on_invalidation_close(98.2, T, 0)
    assert closed and all(leg.exit_reason == "invalidation" for leg in closed[0].legs)
    assert closed[0].r_multiple() == pytest.approx(-0.9)


def test_breakeven_at_1r_before_tp1():
    sim = Simulator(SPEC, 0, {**MGMT, "breakeven_at_r": 1.0})
    sim.open(_plan(), (0.1, 0.1), T, 0)  # rủi ro 2.0 → 1R = 102
    assert sim.on_bar(100, 101.9, 99.5, T, 0) == [] and sim.open_positions[0].legs[0].sl == 98.0  # chưa tới 1R
    assert sim.on_bar(100, 102.0, 99.5, T, 0) == []
    assert all(leg.sl == 100.0 and leg.sl_kind == "breakeven" for leg in sim.open_positions[0].legs)
    closed = sim.on_bar(101, 101.5, 99.0, T, 0)
    assert closed[0].r_multiple() == pytest.approx(0.0)


def test_breakeven_not_applied_within_same_bar_as_stop():
    sim = Simulator(SPEC, 0, {**MGMT, "breakeven_at_r": 1.0})
    sim.open(_plan(), (0.2,), T, 0)
    closed = sim.on_bar(100, 102.5, 97.5, T, 0)  # không biết thứ tự trong nến → tính SL trước
    assert closed[0].r_multiple() == pytest.approx(-1.0)
