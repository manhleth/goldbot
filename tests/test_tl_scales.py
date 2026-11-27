"""Phá trendline đa tỉ lệ + retest: đường nối đáy dài bị phá xuống, giá quay lên chạm đường rồi nến engulfing giảm → SELL."""
import numpy as np
import pandas as pd

from core.types import Direction
from data.candles import normalize
from playbook.tl_scales import _breaks, tl_retest

P = {"timeframes": ["H4"], "swings": [3, 8], "rules": {"min_touches": 3, "touch_tol_atr": 0.3, "max_pivots": 12},
     "break_atr": 0.2, "atr": 14, "confirm_tf": {"H4": "H4"},
     "retest": {"span_frac": 0.5, "min_bars": 3, "zone_atr": 0.5, "invalid_atr": 0.5, "sl_buffer_atr": 0.3,
                "max_sl_atr": 3.0, "trigger": {"pin_wick_body_ratio": 2.0, "pin_min_wick_range": 0.5}}}


class Data:
    def __init__(self, df):
        self.df = df

    def frame(self, tf):
        return self.df


def _frame():
    """120 nến dao động trên đường đáy tăng (chạm ~6 lần), phá xuống, hồi lên chạm đường, engulfing giảm, rơi tiếp."""
    n = 120
    i = np.arange(n, dtype=float)
    line = 100 + 0.1 * i
    close = line + 5 + 4 * np.sin(2 * np.pi * i / 20 - np.pi / 2)
    tail = [line[-1] + 0.1 * k for k in range(1, 15)]
    path = [t - d for t, d in zip(tail, [3, 6, 9, 10, 8, 5, 2, 0.5, 0.5, 4, 8, 11, 13, 15])]
    close = np.concatenate([close, path])
    prev = np.concatenate([[close[0]], close[:-1]])
    opens = prev + 0.3 * (close - prev)  # mở cửa lệch về phía đóng cửa → đáy/đỉnh swing là duy nhất
    opens[n + 9] = close[n + 8] + 0.2  # nến engulfing giảm sau nến tăng chạm đường
    opens[n + 8] = close[n + 7] - 0.5
    high = np.maximum(opens, close) + 1
    low = np.minimum(opens, close) - 1
    t = pd.date_range("2026-01-01", periods=len(close), freq="4h", tz="UTC")
    return normalize(pd.DataFrame({"time": t, "open": opens, "high": high, "low": low, "close": close,
                                   "tick_volume": 100}), "H4")


def test_long_support_break_then_retest_gives_sell_with_long_line():
    df = _frame()
    breaks = [b for b in _breaks(df, P) if b.side == Direction.BUY]
    assert breaks and breaks[0].line.touches >= 3 and breaks[0].index > 115
    orders = tl_retest(Data(df), P, "t")
    assert len(orders) == 1
    o = orders[0]
    assert o.direction == Direction.SELL and o.key.startswith("t:tl_retest@H4:") and o.sl_dist > 0
    assert o.meta["edges"] and "phá trendline H4" in o.reasons[0]
