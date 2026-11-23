"""Chỉ báo cho sổ tay (nhân quả: giá trị tại nến i chỉ dùng dữ liệu tới nến i)."""
from __future__ import annotations

import numpy as np
import pandas as pd

from structure.indicators import atr, ema, rsi

__all__ = ["atr", "ema", "rsi", "macd", "bollinger", "stochastic", "donchian", "pivots", "fractal_swings"]


def macd(close: pd.Series, fast: int, slow: int, signal: int) -> tuple[pd.Series, pd.Series]:
    main = ema(close, fast) - ema(close, slow)
    return main, ema(main, signal)


def bollinger(close: pd.Series, period: int, width: float) -> tuple[pd.Series, pd.Series, pd.Series]:
    mid = close.rolling(period).mean()
    std = close.rolling(period).std(ddof=0)
    return mid - width * std, mid, mid + width * std


def stochastic(df: pd.DataFrame, k_period: int, k_smooth: int, d_period: int) -> tuple[pd.Series, pd.Series]:
    low, high = df["low"].rolling(k_period).min(), df["high"].rolling(k_period).max()
    raw = 100 * (df["close"] - low) / (high - low).replace(0, np.nan)
    k = raw.rolling(k_smooth).mean()
    return k, k.rolling(d_period).mean()


def donchian(df: pd.DataFrame, period: int) -> tuple[pd.Series, pd.Series]:
    """Đỉnh/đáy của `period` nến TRƯỚC nến hiện tại (để so close hiện tại với kênh)."""
    return df["high"].rolling(period).max().shift(1), df["low"].rolling(period).min().shift(1)


def pivots(day: pd.DataFrame) -> pd.DataFrame:
    """Pivot cổ điển từ nến ngày: P, R1, R2, S1, S2."""
    h, l, c = day["high"], day["low"], day["close"]
    p = (h + l + c) / 3
    return pd.DataFrame({"p": p, "r1": 2 * p - l, "s1": 2 * p - h, "r2": p + (h - l), "s2": p - (h - l)})


def fractal_swings(df: pd.DataFrame, left: int, right: int) -> tuple[np.ndarray, np.ndarray]:
    """Mảng bool: nến là swing high / swing low (cao/thấp hơn hẳn `left` nến trái và `right` nến phải).

    Swing ở vị trí s chỉ được biết khi nến s + right đã đóng.
    """
    h, l = df["high"].to_numpy(float), df["low"].to_numpy(float)
    n = len(df)
    is_high, is_low = np.zeros(n, bool), np.zeros(n, bool)
    for s in range(left, n - right):
        hs, ls = h[s - left:s + right + 1], l[s - left:s + right + 1]
        others_h, others_l = np.delete(hs, left), np.delete(ls, left)
        is_high[s] = h[s] > others_h.max()
        is_low[s] = l[s] < others_l.min()
    return is_high, is_low
