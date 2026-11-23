from __future__ import annotations

import copy
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from core.config import load_config
from data.candles import normalize

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session")
def base_cfg() -> dict:
    return load_config(ROOT / "config.yaml")


@pytest.fixture
def cfg(base_cfg) -> dict:
    return copy.deepcopy(base_cfg)


def legacy_profile(cfg: dict) -> dict:
    """Hồ sơ phương pháp cũ (D1/H4 → H1 → M15, bias chỉ báo) để test các setup cũ."""
    cfg["timeframes"] = {"bias": ["D1", "H4"], "setup": "H1", "trigger": "M15"}
    cfg["enabled_setups"] = ["fvg_retest", "trendline_break_retest", "sweep_reversal", "sr_flip_retest"]
    cfg["bias"]["method"] = "indicators"
    cfg["risk"].update(entry_sessions=[], tp1_timeframes=["H1"], tp2_timeframes=["H4", "D1"],
                       tp1_mode="first_valid", sl_anchor="invalidation")
    cfg["management"].update(flat_time=None, trail_tf="H1", invalidation_tf="H4", breakeven_at_r=None)
    cfg["structure"]["fractal_n"].update(M15=3, H4=5)
    cfg["trigger"]["types"] = ["engulfing", "pin_bar", "mini_choch"]
    return cfg


def ict_profile(cfg: dict) -> dict:
    """Hồ sơ ICT intraday v0.5 (H4 → M15 → M5, killzone, đóng 16:00 NY hằng ngày)."""
    cfg["timeframes"] = {"bias": ["H4"], "setup": "M15", "trigger": "M5"}
    cfg["enabled_setups"] = ["sweep_mss_fvg", "judas_swing"]
    cfg["risk"].update(entry_sessions=["london", "newyork"], tp1_timeframes=["M15"])
    cfg["management"].update(trail_tf="M15", invalidation_tf="M15", flat_time="16:00", flat_weekday=None)
    return cfg


def make_bars(rows, tf: str = "H1", start: str = "2024-01-01", atr: float | None = None) -> pd.DataFrame:
    """rows: danh sách (open, high, low, close)."""
    step = {"M5": "5min", "M15": "15min", "H1": "1h", "H4": "4h", "D1": "1D"}[tf]
    times = pd.date_range(start, periods=len(rows), freq=step, tz="UTC")
    df = normalize(pd.DataFrame(rows, columns=["open", "high", "low", "close"]).assign(time=times), tf)
    if atr is not None:
        df["atr"] = atr
    return df


def bars_from_closes(closes, tf: str = "H1", spread: float = 0.5, atr: float | None = None) -> pd.DataFrame:
    rows = []
    prev = closes[0]
    for c in closes:
        rows.append((prev, max(prev, c) + spread, min(prev, c) - spread, c))
        prev = c
    return make_bars(rows, tf, atr=atr)


def random_walk_m15(days: int, seed: int = 7, start: str = "2024-01-01", price: float = 2000.0,
                    tf: str = "M15") -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    minutes = {"M5": 5, "M15": 15}[tf]
    n = days * 24 * 60 // minutes
    times = pd.date_range(start, periods=n, freq=f"{minutes}min", tz="UTC")
    drift = np.sin(np.arange(n) / 600) * 0.15  # tạo các đoạn xu hướng
    closes = price + np.cumsum(drift + rng.normal(0, 1.2, n))
    opens = np.concatenate([[price], closes[:-1]])
    wick = np.abs(rng.normal(0, 0.8, n))
    df = pd.DataFrame({"time": times, "open": opens, "close": closes,
                       "high": np.maximum(opens, closes) + wick, "low": np.minimum(opens, closes) - wick,
                       "spread": 20.0})
    weekday = df["time"].dt.day_of_week
    return normalize(df[weekday < 5], tf)
