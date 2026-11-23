"""Chuẩn hoá nến và cắt dữ liệu theo thời điểm (không look-ahead)."""
from __future__ import annotations

import pandas as pd

from core.timeframes import tf_delta

OHLC = ["open", "high", "low", "close"]
COLUMNS = ["time", *OHLC, "tick_volume", "spread"]


class DataError(RuntimeError):
    pass


def normalize(raw: pd.DataFrame, tf: str) -> pd.DataFrame:
    """Chuẩn hoá về schema chung; cột `time` là giờ mở nến (UTC), thêm `close_time`."""
    missing = {"time", *OHLC} - set(raw.columns)
    if missing:
        raise DataError(f"dữ liệu nến thiếu cột: {sorted(missing)}")
    df = raw.copy()
    df["time"] = pd.to_datetime(df["time"], utc=True)
    for col in ("tick_volume", "spread"):
        if col not in df.columns:
            df[col] = 0.0
    df = df[COLUMNS].astype({col: float for col in [*OHLC, "tick_volume", "spread"]})
    df = df.drop_duplicates("time", keep="last").sort_values("time").reset_index(drop=True)
    df["close_time"] = df["time"] + tf_delta(tf)
    return df


def closed_only(df: pd.DataFrame, now: pd.Timestamp) -> pd.DataFrame:
    return df[df["close_time"] <= now].reset_index(drop=True)


def closed_end(df: pd.DataFrame, t: pd.Timestamp) -> int:
    """Số nến đã đóng tại thời điểm t (vị trí kết thúc, không gồm)."""
    return int(df["close_time"].searchsorted(t, side="right"))


def resample(df: pd.DataFrame, tf: str) -> pd.DataFrame:
    """Gộp nến nhỏ thành khung lớn hơn (căn theo UTC). Dùng cho CSV chỉ có khung nhỏ và cho test."""
    rule = f"{int(tf_delta(tf).total_seconds() // 60)}min"
    grouped = df.set_index("time").resample(rule, label="left", closed="left")
    out = grouped.agg({"open": "first", "high": "max", "low": "min", "close": "last",
                       "tick_volume": "sum", "spread": "max"}).dropna(subset=["open"])
    return normalize(out.reset_index(), tf)
