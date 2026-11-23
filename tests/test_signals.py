import pandas as pd

from core.types import Direction, Setup, Zone
from mtf.bias import combine_biases
from mtf.view import TimeframeView
from signals.confirm import confirm
from signals.triggers import is_engulfing, is_pin_bar
from tests.conftest import make_bars

N, B, S = Direction.NEUTRAL, Direction.BUY, Direction.SELL


def _view(rows, cfg, tf="M15"):
    df = make_bars(rows, tf, atr=2.0).assign(rsi=50.0)
    return TimeframeView(tf, df, cfg)


def test_combine_biases_rules():
    assert combine_biases([B, B], "non_conflicting") == B
    assert combine_biases([B, N], "non_conflicting") == B
    assert combine_biases([B, S], "non_conflicting") == N
    assert combine_biases([N, N], "non_conflicting") == N
    assert combine_biases([B, N], "all_agree") == N


def test_bullish_engulfing(cfg):
    view = _view([(101, 101.5, 99.5, 100), (99.8, 102, 99.6, 101.5)], cfg)
    assert is_engulfing(view, B, cfg)
    assert not is_engulfing(view, S, cfg)


def test_pin_bar_requires_dominant_wick(cfg):
    assert is_pin_bar(_view([(100, 100.6, 97, 100.5)], cfg), B, cfg)
    assert not is_pin_bar(_view([(100, 101.2, 99, 100.02)], cfg), B, cfg)  # bóng trên dài hơn → không phải pin BUY
    assert not is_pin_bar(_view([(100, 100.5, 99.5, 100.4)], cfg), B, cfg)  # bóng dưới < 2 lần thân


def _setup(zone, invalidation=99.0):
    return Setup("fvg_retest", B, zone, invalidation, 1, ("test",), "k")


def test_confirm_needs_zone_touch_and_trigger(cfg):
    cfg["trigger"]["types"] = ["engulfing", "pin_bar", "mini_choch"]
    rows = [(101, 101.5, 99.5, 100), (99.8, 102, 99.6, 101.5)]
    trig = confirm(_setup(Zone(99.0, 100.0)), _view(rows, cfg), cfg)
    assert trig is not None and trig.name == "engulfing" and trig.extreme == 99.6 and trig.close == 101.5
    assert confirm(_setup(Zone(95.0, 96.0)), _view(rows, cfg), cfg) is None  # không chạm vùng


def test_confirm_rejects_close_beyond_invalidation(cfg):
    rows = [(101, 101.5, 99.5, 100), (99.8, 102, 99.6, 101.5)]
    assert confirm(_setup(Zone(99.0, 100.0), invalidation=102.0), _view(rows, cfg), cfg) is None


def test_touch_trigger_enters_without_confirmation_candle(cfg):
    cfg["trigger"]["types"] = ["touch"]
    rows = [(101, 101.5, 100.5, 101), (100.8, 101, 99.8, 100.5)]  # nến cuối chạm vùng, không phải engulfing/pin
    trig = confirm(_setup(Zone(99.0, 100.0)), _view(rows, cfg), cfg)
    assert trig is not None and trig.name == "touch" and trig.close == 100.5
    away = [(99.5, 100.2, 99.4, 100.1), (100.5, 101.5, 100.4, 101.2)]  # nến trước chạm, nến cuối đã rời vùng
    assert confirm(_setup(Zone(99.0, 100.0)), _view(away, cfg), cfg) is None
