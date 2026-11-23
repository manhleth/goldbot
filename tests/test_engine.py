"""Kiểm thử tích hợp: không look-ahead và backtest chạy trọn vòng."""
import math

import pandas as pd
import pytest

from backtest.engine import Backtester
from data.candles import closed_only, resample
from news.calendar import build_calendar
from risk.sizing import SymbolSpec
from signals.engine import Analyzer
from structure.indicators import enrich
from tests.conftest import ict_profile, legacy_profile, random_walk_m15

SPEC = SymbolSpec(point=0.01, tick_size=0.01, tick_value=1.0, volume_min=0.01, volume_step=0.01, volume_max=100)


def _relaxed(cfg):
    legacy_profile(cfg)
    cfg["structure"]["adx_min"] = 0
    cfg["bias"]["min_score"] = 1
    cfg["structure"]["ema"] = [20, 50]
    cfg["bias"]["slope_ema"] = 20
    cfg["data"]["window_bars"] = {"D1": 60, "H4": 150, "H1": 200, "M15": 120}
    cfg["risk"]["tp1_fallback_rr"] = 2.0
    cfg["risk"]["tp1_mode"] = "first_valid"
    cfg["blocked_windows_utc"] = []
    return cfg


@pytest.fixture(scope="module")
def frames_raw():
    m15 = random_walk_m15(days=140)
    return {"M15": m15, "H1": resample(m15, "H1"), "H4": resample(m15, "H4"), "D1": resample(m15, "D1")}


def _enriched(raw, cfg):
    return {tf: enrich(df, cfg["structure"]) for tf, df in raw.items()}


def test_no_lookahead(frames_raw, cfg):
    cfg = _relaxed(cfg)
    full = _enriched(frames_raw, cfg)
    times = full["M15"]["close_time"]
    checkpoints = [times.iat[i] for i in range(len(times) // 2, len(times), 997)]
    compared = 0
    for t in checkpoints:
        truncated = _enriched({tf: closed_only(df, t) for tf, df in frames_raw.items()}, cfg)
        ctx_a, sig_a = Analyzer(cfg).signals(full, t)
        ctx_b, sig_b = Analyzer(cfg).signals(truncated, t)
        assert (ctx_a is None) == (ctx_b is None)
        if ctx_a is None:
            continue
        compared += 1
        assert ctx_a.direction == ctx_b.direction
        assert {k: b.score for k, b in ctx_a.biases.items()} == {k: b.score for k, b in ctx_b.biases.items()}
        a, b = Analyzer(cfg), Analyzer(cfg)
        assert [s.key for s in a.setups(ctx_a)] == [s.key for s in b.setups(ctx_b)]
        assert [(s.setup.key, s.trigger) for s in sig_a] == [(s.setup.key, s.trigger) for s in sig_b]
    assert compared >= 3


def test_backtest_runs_end_to_end(frames_raw, cfg):
    cfg = _relaxed(cfg)
    frames = _enriched(frames_raw, cfg)
    start = frames["M15"]["time"].iat[0] + pd.Timedelta(days=70)
    end = frames["M15"]["time"].iat[-1]
    result = Backtester(cfg, frames, SPEC, "test", build_calendar([], cfg["news"])).run(start, end)
    assert result.signals, "phải sinh ra ít nhất một tín hiệu trên dữ liệu mẫu"
    for trade in result.trades:
        assert math.isfinite(trade["r_multiple"]) and trade["r_multiple"] >= -1.5
        assert trade["exit_time"] >= trade["entry_time"]
    assert all(row["equity"] > 0 for row in result.equity)


def test_ict_backtest_runs_end_to_end(cfg):
    m5 = random_walk_m15(days=60, seed=5, tf="M5")
    raw = {"M5": m5, "M15": resample(m5, "M15"), "H4": resample(m5, "H4")}
    ict_profile(cfg)
    cfg["structure"]["ema"] = [20, 50]
    cfg["bias"]["slope_ema"] = 20
    frames = _enriched(raw, cfg)
    start = m5["time"].iat[0] + pd.Timedelta(days=25)
    result = Backtester(cfg, frames, SPEC, "ict", build_calendar([], cfg["news"])).run(start, m5["time"].iat[-1])
    for trade in result.trades:
        assert trade["setup"] in ("sweep_mss_fvg", "judas_swing")
        entry = pd.Timestamp(trade["entry_time"]).tz_convert("America/New_York")
        exit_ = pd.Timestamp(trade["exit_time"]).tz_convert("America/New_York")
        assert entry.date() == exit_.date() and exit_.hour < 17  # intraday, đóng trước cuối phiên


@pytest.fixture(scope="module")
def breakout_raw():
    m5 = random_walk_m15(days=75, seed=11, tf="M5")
    return {"M5": m5, "M15": resample(m5, "M15"), "H1": resample(m5, "H1"), "H4": resample(m5, "H4")}


def _breakout_cfg(cfg):
    cfg["structure"]["ema"] = [20, 50]
    cfg["bias"]["slope_ema"] = 20
    cfg["range_breakout"].update(max_height_atr=6.0, breakout_body_atr=0.5)  # dữ liệu ngẫu nhiên: nới để có setup
    return cfg


def test_range_breakout_no_lookahead(breakout_raw, cfg):
    cfg = _breakout_cfg(cfg)
    full = _enriched(breakout_raw, cfg)
    times = full["M5"]["close_time"]
    compared = 0
    for i in range(len(times) // 2, len(times), 1201):
        t = times.iat[i]
        truncated = _enriched({tf: closed_only(df, t) for tf, df in breakout_raw.items()}, cfg)
        ctx_a, sig_a = Analyzer(cfg).signals(full, t)
        ctx_b, sig_b = Analyzer(cfg).signals(truncated, t)
        if ctx_a is None:
            assert ctx_b is None
            continue
        compared += 1
        assert [s.key for s in Analyzer(cfg).setups(ctx_a)] == [s.key for s in Analyzer(cfg).setups(ctx_b)]
        assert [(s.setup.key, s.trigger) for s in sig_a] == [(s.setup.key, s.trigger) for s in sig_b]
    assert compared >= 3


def test_range_breakout_backtest_holds_overnight_and_flattens_friday(breakout_raw, cfg):
    cfg = _breakout_cfg(cfg)
    frames = _enriched(breakout_raw, cfg)
    m5 = frames["M5"]
    result = Backtester(cfg, frames, SPEC, "rbo", build_calendar([], cfg["news"])).run(
        m5["time"].iat[0] + pd.Timedelta(days=30), m5["time"].iat[-1])
    assert result.signals
    for trade in result.trades:
        assert trade["setup"] == "range_breakout"
        exit_ = pd.Timestamp(trade["exit_time"]).tz_convert("America/New_York")
        assert not (exit_.weekday() == 4 and exit_.hour >= 17) and exit_.weekday() != 5  # đóng trước cuối tuần
