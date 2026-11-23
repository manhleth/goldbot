import numpy as np
import pandas as pd
import pytest

from core.types import Direction
from structure.breaks import find_breaks
from structure.indicators import adx, atr, ema, rsi
from structure.swings import find_swings
from structure.trend import swing_trend
from tests.conftest import bars_from_closes, make_bars


def test_atr_of_constant_range_equals_range():
    df = make_bars([(10, 11, 9, 10)] * 30)
    assert atr(df, 14).iloc[-1] == pytest.approx(2.0)
    assert atr(df, 14).iloc[:13].isna().all()


def test_ema_of_constant_is_constant():
    assert ema(pd.Series([5.0] * 60), 50).iloc[-1] == pytest.approx(5.0)


def test_rsi_extremes():
    assert rsi(pd.Series(np.arange(1, 40, dtype=float)), 14).iloc[-1] == pytest.approx(100.0)
    assert rsi(pd.Series(np.arange(40, 1, -1, dtype=float)), 14).iloc[-1] == pytest.approx(0.0)


def test_adx_high_in_strong_trend():
    df = bars_from_closes(list(np.arange(100, 160, 1.0)))
    assert adx(df, 14).iloc[-1] > 50


def test_swings_confirmed_after_n_bars_only():
    closes = [10, 11, 12, 15, 12, 11, 10, 9, 8]  # đỉnh tại index 3
    df = bars_from_closes(closes, spread=0)
    swings = find_swings(df, 3)
    highs = [s for s in swings if s.kind == "high"]
    assert [s.index for s in highs] == [3]
    assert highs[0].confirmed_index == 6
    # cắt bớt: chưa đủ 3 nến bên phải thì chưa có swing (không repaint)
    assert not [s for s in find_swings(df.iloc[:6], 3) if s.kind == "high"]


def test_equal_highs_produce_single_swing():
    df = make_bars([(1, 2, 0, 1), (1, 5, 0, 1), (1, 5, 0, 1), (1, 2, 0, 1), (1, 2, 0, 1)])
    assert [s.index for s in find_swings(df, 1) if s.kind == "high"] == [1]


def _zigzag(points, steps=4):
    closes = []
    for a, b in zip(points[:-1], points[1:]):
        closes += list(np.linspace(a, b, steps, endpoint=False))
    closes.append(points[-1])
    return bars_from_closes(closes, spread=0.1)


def test_swing_trend_up_and_down():
    up = _zigzag([100, 110, 104, 116, 108, 122, 112, 125])
    down = _zigzag([125, 112, 122, 108, 116, 104, 110, 100])
    assert swing_trend(find_swings(up, 2)) == Direction.BUY
    assert swing_trend(find_swings(down, 2)) == Direction.SELL


def test_bos_in_uptrend_and_choch_on_reversal():
    df = _zigzag([100, 110, 104, 116, 108, 122, 112, 125, 117, 121, 105])
    swings = find_swings(df, 2)
    breaks = find_breaks(df, swings)
    assert any(b.direction == Direction.BUY and b.kind == "BOS" for b in breaks)
    assert breaks[-1].direction == Direction.SELL and breaks[-1].kind == "CHOCH"
