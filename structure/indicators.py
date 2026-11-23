"""Chỉ báo kỹ thuật (đều là nhân quả: giá trị tại t chỉ dùng dữ liệu <= t)."""
from __future__ import annotations

import numpy as np
import pandas as pd


def ema(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(span=period, adjust=False, min_periods=period).mean()


def wilder(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()


def true_range(df: pd.DataFrame) -> pd.Series:
    prev_close = df["close"].shift(1)
    ranges = pd.concat([df["high"] - df["low"], (df["high"] - prev_close).abs(),
                        (df["low"] - prev_close).abs()], axis=1)
    return ranges.max(axis=1)


def atr(df: pd.DataFrame, period: int) -> pd.Series:
    return wilder(true_range(df), period)


def rsi(close: pd.Series, period: int) -> pd.Series:
    delta = close.diff()
    gain = wilder(delta.clip(lower=0.0), period)
    loss = wilder(-delta.clip(upper=0.0), period)
    value = 100.0 - 100.0 / (1.0 + gain / loss)
    return value.where(loss != 0, 100.0).where(gain.notna())


def adx(df: pd.DataFrame, period: int) -> pd.Series:
    up = df["high"].diff()
    down = -df["low"].diff()
    plus_dm = up.where((up > down) & (up > 0), 0.0)
    minus_dm = down.where((down > up) & (down > 0), 0.0)
    tr = wilder(true_range(df), period)
    plus_di = 100.0 * wilder(plus_dm, period) / tr
    minus_di = 100.0 * wilder(minus_dm, period) / tr
    dx = 100.0 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
    return wilder(dx, period)


def enrich(df: pd.DataFrame, structure_cfg: dict) -> pd.DataFrame:
    """Thêm cột atr, ema_<p>, rsi, adx."""
    out = df.copy()
    out["atr"] = atr(out, structure_cfg["atr_period"])
    for period in structure_cfg["ema"]:
        out[f"ema_{period}"] = ema(out["close"], period)
    out["rsi"] = rsi(out["close"], structure_cfg["rsi_period"])
    out["adx"] = adx(out, structure_cfg["adx_period"])
    return out
