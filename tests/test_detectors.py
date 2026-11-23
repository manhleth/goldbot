import numpy as np
import pandas as pd

from core.types import Direction
from structure.breaks import StructureBreak
from structure.fvg import find_fvgs
from structure.interaction import zone_lifecycle
from structure.order_block import find_order_blocks
from structure.sweep import find_sweep
from structure.swings import Swing
from structure.trendline import first_break, latest_trendline
from structure.zones import SRZone, cluster_zones, last_flip_break
from tests.conftest import make_bars

T0 = pd.Timestamp("2024-01-01", tz="UTC")


def _swing(index, price, kind="high", n=1):
    return Swing(index, T0, price, kind, index + n)


def test_cluster_zones_groups_within_tolerance():
    swings = [_swing(1, 100.0), _swing(5, 100.4, "low"), _swing(9, 103.0), _swing(12, 100.2)]
    zones = cluster_zones(swings, tolerance=0.5, min_touches=2)
    assert len(zones) == 1
    z = zones[0]
    assert (z.low, z.high, z.touches, z.first_index, z.last_index) == (100.0, 100.4, 3, 1, 12)


def test_last_flip_break_requires_prior_opposite_side():
    closes = [99, 100.2, 99, 98, 101.5, 101]  # dưới vùng → phá lên tại index 4
    df = make_bars([(c, c + 0.1, c - 0.1, c) for c in closes])
    zone = SRZone(100.0, 100.5, 2, 0, 1)
    assert last_flip_break(df, zone, Direction.BUY) == 4
    assert last_flip_break(df, zone, Direction.SELL) is None
    bounce = make_bars([(c, c + 0.1, c - 0.1, c) for c in [100.2, 101, 102]])  # chỉ ở trên → không rõ vai
    assert last_flip_break(bounce, zone, Direction.BUY) is None


def test_zone_lifecycle_counts_episodes_and_invalidation():
    rows = [(105, 106, 104, 105), (103, 103.5, 101.5, 103), (104, 105, 103.5, 104), (102, 102.5, 101.8, 102)]
    df = make_bars(rows)
    lc = zone_lifecycle(df, 0, 101.0, 102.0, Direction.BUY)
    assert (lc.episodes, lc.ongoing, lc.invalidated) == (2, True, False)
    assert not lc.is_first_touch(1)
    first = zone_lifecycle(df.iloc[:2], 0, 101.0, 102.0, Direction.BUY)
    assert first.is_first_touch(1)
    broken = make_bars(rows + [(102, 102, 100, 100.5)])
    assert zone_lifecycle(broken, 0, 101.0, 102.0, Direction.BUY).invalidated


def test_fvg_bullish_with_filters():
    rows = [(100, 101, 99, 100.5), (100.5, 106, 100.4, 105.8), (105.8, 107, 102, 106)]
    df = make_bars(rows, atr=3.0)
    gaps = find_fvgs(df, min_size_atr=0.3, impulse_body_atr=1.0)
    assert len(gaps) == 1
    g = gaps[0]
    assert (g.direction, g.low, g.high, g.index) == (Direction.BUY, 101, 102, 2)
    assert find_fvgs(df.assign(atr=10.0), 0.3, 1.0) == []  # thân c2 nhỏ so với ATR → loại


def test_fvg_bearish():
    rows = [(106, 107, 105, 105.5), (105.5, 105.6, 100, 100.2), (100.2, 104, 99, 99.5)]
    gaps = find_fvgs(make_bars(rows, atr=3.0), 0.3, 1.0)
    assert [(g.direction, g.low, g.high) for g in gaps] == [(Direction.SELL, 104, 105)]


def test_order_block_last_bearish_candle_before_bos():
    rows = [(100, 101, 99, 100), (100, 102, 99.5, 101.5), (101.5, 101.6, 99, 99.2),  # 2 = nến giảm cuối
            (99.2, 103, 99.1, 102.8), (102.8, 106, 102.5, 105.5)]
    df = make_bars(rows, atr=1.5)
    swing = Swing(1, T0, 102.0, "high", 2)
    brk = StructureBreak(4, Direction.BUY, 102.0, swing, "BOS")
    blocks = find_order_blocks(df, [brk], min_move_atr=2.0, search_bars=5)
    assert [(b.index, b.low, b.high) for b in blocks] == [(2, 99, 101.6)]
    assert find_order_blocks(df.assign(atr=10.0), [brk], 2.0, 5) == []


def test_sweep_below_swing_low_closing_back_inside():
    rows = [(101, 102, 100.5, 101.5)] * 2 + [(101, 101.2, 99, 100)] + [(100.5, 102, 100.2, 101.8)] * 3 + \
           [(101.5, 101.8, 98.5, 100.6)]
    df = make_bars(rows)
    swings = [Swing(2, T0, 99.0, "low", 4)]
    sweep = find_sweep(df, swings, Direction.BUY, max_age=3)
    assert sweep is not None and (sweep.index, sweep.level, sweep.extreme) == (6, 99.0, 98.5)
    closed_below = df.copy()
    closed_below.loc[6, "close"] = 98.8
    assert find_sweep(closed_below, swings, Direction.BUY, 3) is None


def test_trendline_break_detection():
    closes = [110, 108, 106, 104, 105, 107, 105, 103, 101, 102, 101, 100, 99, 103]
    rows = [(c, c + 0.5, c - 0.5, c) for c in closes]
    df = make_bars(rows, atr=1.0)
    swings = [Swing(0, T0, 110.5, "high", 2), Swing(5, T0, 107.5, "high", 7)]
    line = latest_trendline(df, swings, "high", max_pivots=6)
    assert line is not None and (line.i1, line.i2) == (0, 5)
    brk = first_break(df, line)
    # đường: 110.5 - 0.6*i → tại i=13: 102.7; close 103 vượt 0.3
    assert brk is not None and brk.index == 13
    assert np.isclose(brk.distance, 0.3)
