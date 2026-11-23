import pandas as pd
import pytest

from stats.metrics import longest_streak, max_drawdown, summarize, wilson_interval
from stats.report import build_report

import numpy as np


def test_wilson_interval_known_value():
    lo, hi = wilson_interval(22, 40)  # 55% trên 40 lệnh
    assert lo == pytest.approx(0.3982, abs=1e-3) and hi == pytest.approx(0.6928, abs=1e-3)
    assert lo < 0.45  # không khác biệt có ý nghĩa với 45%


def test_summarize_expectancy_and_pf():
    s = summarize([2.0, -1.0, 2.0, -1.0, -1.0])
    assert s["winrate"] == pytest.approx(0.4)
    assert s["expectancy_r"] == pytest.approx(0.4 * 2 - 0.6 * 1)
    assert s["profit_factor"] == pytest.approx(4 / 3)
    assert s["longest_losing_streak"] == 2


def test_drawdown_and_streak():
    assert max_drawdown(np.cumsum([1, -1, -1, 2, -3])) == pytest.approx(3.0)
    assert longest_streak(np.array([True, True, False, True])) == 2


def test_report_warns_on_small_sample(cfg):
    trades = pd.DataFrame({"r_multiple": [1.5, -1.0], "setup": ["a", "b"], "direction": ["BUY", "SELL"],
                           "bias": ["D1=BUY", "D1=SELL"], "entry_time": ["2024-01-02T08:00:00+00:00"] * 2,
                           "exit_reason": ["tp1:tp1", "single:sl"]})
    text = build_report(trades, pd.DataFrame(), cfg)
    assert "KHÔNG kết luận" in text and "Theo SETUP" in text
