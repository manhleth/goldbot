"""Setup phá có lực + retest: lực phá, BOS sau phá, nến xác nhận, tìm điểm vào retest ở khung nhỏ."""
import numpy as np
import pandas as pd

from core.types import Direction
from playbook.patterns import Edge, Signal
from playbook.retest import Frame, _bos_bar, _entry, _strong_bar, _trigger

T0 = pd.Timestamp("2026-01-05", tz="UTC")
STRENGTH = {"body_atr": 1.0, "close_pos": 0.3, "min_break_atr": 0.5, "volume_mult": 1.5, "volume_bars": 3}
P = {"retest_bars": 4, "zone_atr": 0.3, "invalid_atr": 0.2, "sl_buffer_atr": 0.3, "max_sl_atr": 2.0,
     "trigger": {"pin_wick_body_ratio": 2.0, "pin_min_wick_range": 0.5}}


def _frame(rows, minutes=60, volume=None, start=T0):
    o, h, l, c = (np.array(x, float) for x in zip(*rows))
    t = start + pd.to_timedelta(np.arange(len(rows)) * minutes, unit="min")
    v = np.full(len(rows), 100.0) if volume is None else np.array(volume, float)
    return pd.DataFrame({"time": t, "open": o, "high": h, "low": l, "close": c, "tick_volume": v,
                         "close_time": t + pd.Timedelta(minutes=minutes)})


def test_strong_bar_needs_body_close_distance_and_volume():
    rows = [(100, 101, 99, 100)] * 3 + [(100, 103, 99.9, 102.9)]
    strong = Frame.of(_frame(rows, volume=[100, 100, 100, 200]))
    assert _strong_bar(strong, 3, 1, 101.5, 2.0, STRENGTH)
    assert not _strong_bar(strong, 3, 1, 102.5, 2.0, STRENGTH)  # đóng cửa chỉ cách cạnh 0.4 < 0.5 × ATR = 1.0
    weak_volume = Frame.of(_frame(rows, volume=[100, 100, 100, 120]))
    assert not _strong_bar(weak_volume, 3, 1, 101.5, 2.0, STRENGTH)
    long_wick = Frame.of(_frame([*rows[:3], (100, 106, 99.9, 102.9)], volume=[100, 100, 100, 200]))
    assert not _strong_bar(long_wick, 3, 1, 101.5, 2.0, STRENGTH)  # đóng cửa xa đỉnh nến


def test_bos_bar_finds_close_above_last_confirmed_swing_high():
    rows = [(100, 101, 99, 100), (100, 105, 100, 104), (104, 104, 101, 102), (102, 103, 100, 101),
            (101, 104, 100, 103), (103, 107, 102, 106)]
    f = Frame.of(_frame(rows))
    highs, lows = np.array([1]), np.array([], int)
    assert _bos_bar(f, highs, lows, 1, 4, 1, 3) == 5   # nến 5 đóng 106 > đỉnh swing 105
    assert _bos_bar(f, highs, lows, 1, 4, 1, 1) is None
    assert _bos_bar(f, highs, lows, 1, 4, 1, None) == 4  # tắt điều kiện BOS


def test_trigger_detects_engulfing_and_pin_bar():
    f = Frame.of(_frame([(101, 101.2, 99.8, 100), (99.9, 101.6, 99.8, 101.5), (100, 100.2, 98, 100.1)]))
    assert _trigger(f, 1, 1, P["trigger"]) == "engulfing"
    assert _trigger(f, 2, 1, P["trigger"]) == "pin_bar"
    assert _trigger(f, 2, -1, P["trigger"]) is None


def _sig(k=1):
    edge = Edge(0, 100.0, 1, 100.0, 2)  # cạnh nằm ngang ở 100
    return Signal(k, Direction.BUY, "triangle_break", 100.0, 110.0, "", (edge, Edge(0, 90.0, 1, 90.0, 2)))


def test_entry_waits_for_touch_then_trigger_and_sets_sl_below_retest_low():
    pattern = _frame([(99, 100, 98, 99.5), (99.5, 103, 99.4, 102.8), (102.8, 103, 100, 101),
                      (101, 102, 99.8, 101.5), (101.5, 103, 101, 102.5), (102.5, 104, 102, 103.5)])
    confirm = _frame([(102.8, 103, 102, 102.5)] * 4 +                       # giờ 2: chưa chạm vùng 100 ± 0.6
                     [(101.2, 101.3, 100.2, 100.5), (100.5, 100.6, 100.1, 100.2),  # giờ 3: chạm vùng
                      (100.1, 100.4, 99.9, 100.0), (100.05, 100.3, 98.5, 100.2)] +  # pin bar đáy 98.5
                     [(100.2, 101, 100, 100.9)] * 8, minutes=15, start=T0 + pd.Timedelta(hours=2))
    sig = _sig()
    hit = _entry(sig, sig.edges[0], pattern, 1, 2.0, confirm, Frame.of(confirm), P)
    assert hit is not None
    j, sl, kind = hit
    assert (j, kind) == (7, "pin_bar") and sl == 98.5 - 0.3 * 2.0


def test_entry_cancelled_when_price_closes_back_inside_pattern():
    pattern = _frame([(99, 100, 98, 99.5), (99.5, 103, 99.4, 102.8), (102.8, 103, 98, 99), (99, 100, 98, 99)])
    confirm = _frame([(101, 101, 99, 99.2), (99.2, 99.5, 98, 99.4)] + [(100, 103, 98, 102.9)] * 6, minutes=15, start=T0 + pd.Timedelta(hours=2))
    sig = _sig()
    assert _entry(sig, sig.edges[0], pattern, 1, 2.0, confirm, Frame.of(confirm), P) is None
