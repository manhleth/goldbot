"""Quy đổi giờ server broker (MT5) sang UTC."""
from __future__ import annotations

import numpy as np
import pandas as pd

from core.config import ConfigError

NY_CLOSE = "ny_close"  # server = giờ New York + 7h (GMT+2 mùa đông, GMT+3 mùa hè)
_NY_TZ = "America/New_York"
_NY_CLOSE_SHIFT = pd.Timedelta(hours=7)


def _fixed_offset(server_time) -> pd.Timedelta:
    if isinstance(server_time, bool) or not isinstance(server_time, (int, float)):
        raise ConfigError(f"data.server_time không hợp lệ: {server_time!r} (dùng '{NY_CLOSE}' hoặc số giờ)")
    return pd.Timedelta(hours=server_time)


def server_to_utc(times: pd.Series, server_time) -> pd.Series:
    """`times` là giờ đồng hồ của server (naive). Trả về Series tz-aware UTC."""
    naive = pd.to_datetime(times)
    if naive.dt.tz is not None:
        naive = naive.dt.tz_localize(None)
    if server_time == NY_CLOSE:
        local = (naive - _NY_CLOSE_SHIFT).dt.tz_localize(
            _NY_TZ, ambiguous=np.ones(len(naive), dtype=bool), nonexistent="shift_forward")
        return local.dt.tz_convert("UTC")
    return (naive - _fixed_offset(server_time)).dt.tz_localize("UTC")


def utc_to_server(ts: pd.Timestamp, server_time) -> pd.Timestamp:
    """Giờ đồng hồ server (naive) tương ứng với thời điểm UTC."""
    utc = ts.tz_convert("UTC") if ts.tzinfo else ts.tz_localize("UTC")
    if server_time == NY_CLOSE:
        return utc.tz_convert(_NY_TZ).tz_localize(None) + _NY_CLOSE_SHIFT
    return utc.tz_localize(None) + _fixed_offset(server_time)
