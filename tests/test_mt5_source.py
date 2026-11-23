"""Tải lịch sử theo đoạn với MT5 giả lập."""
from datetime import datetime

import numpy as np
import pandas as pd

from data.mt5_source import MT5Source


class FakeMT5:
    TIMEFRAME_H1 = 16385
    MAX_SPAN_HOURS = 500  # giả lập MT5 từ chối yêu cầu quá lớn

    def __init__(self):
        self.calls = []

    def copy_rates_range(self, symbol, tf, lo: datetime, hi: datetime):
        self.calls.append((lo, hi))
        if (hi - lo).total_seconds() / 3600 > self.MAX_SPAN_HOURS:
            return None
        times = pd.date_range(pd.Timestamp(lo).ceil("h"), pd.Timestamp(hi), freq="h", inclusive="left")
        out = np.zeros(len(times), dtype=[("time", "i8"), ("open", "f8"), ("high", "f8"), ("low", "f8"),
                                          ("close", "f8"), ("tick_volume", "i8"), ("spread", "i4")])
        out["time"] = (times - pd.Timestamp("1970-01-01")) // pd.Timedelta(seconds=1)
        out["open"] = out["close"] = 2000.0
        out["high"], out["low"] = 2001.0, 1999.0
        return out

    def last_error(self):
        return (-2, "Invalid params")


def test_fetch_range_in_chunks_without_gaps_or_duplicates():
    mt5 = FakeMT5()
    source = MT5Source(mt5, "XAUUSD", 0)
    start, end = pd.Timestamp("2024-01-01", tz="UTC"), pd.Timestamp("2024-03-01", tz="UTC")
    df = source.fetch_range("H1", start, end, chunk_bars=300)
    assert len(mt5.calls) > 1
    assert df["time"].iat[0] == start and df["close_time"].iat[-1] == end
    assert df["time"].is_unique and (df["time"].diff().dropna() == pd.Timedelta(hours=1)).all()
