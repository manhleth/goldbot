"""Nạp nến từ MT5, quy đổi về UTC, chỉ trả nến đã đóng."""
from __future__ import annotations

from typing import Any

import pandas as pd

from core.timeframes import tf_delta
from data.candles import DataError, closed_only, normalize
from data.server_time import server_to_utc, utc_to_server
from risk.sizing import SymbolSpec

_RANGE_PAD = pd.Timedelta(days=3)  # bù sai lệch giờ server khi xin dữ liệu theo khoảng


class MT5Source:
    def __init__(self, mt5: Any, symbol: str, server_time) -> None:
        self._mt5 = mt5
        self._symbol = symbol
        self._server_time = server_time

    def _timeframe(self, tf: str) -> int:
        return getattr(self._mt5, f"TIMEFRAME_{tf}")

    def _to_frame(self, rates, tf: str) -> pd.DataFrame:
        if rates is None or len(rates) == 0:
            raise DataError(f"MT5 không trả dữ liệu {self._symbol} {tf}: {self._mt5.last_error()}")
        raw = pd.DataFrame(rates)
        raw["time"] = server_to_utc(pd.to_datetime(raw["time"], unit="s"), self._server_time)
        return normalize(raw, tf)

    def fetch_last(self, tf: str, count: int, now: pd.Timestamp) -> pd.DataFrame:
        rates = self._mt5.copy_rates_from_pos(self._symbol, self._timeframe(tf), 0, count + 1)
        return closed_only(self._to_frame(rates, tf), now).tail(count).reset_index(drop=True)

    def fetch_before(self, tf: str, before: pd.Timestamp, count: int) -> pd.DataFrame | None:
        """`count` nến mở trước `before` (UTC); None nếu MT5 không còn dữ liệu cũ hơn (giới hạn Max bars in chart)."""
        when = utc_to_server(before, self._server_time).to_pydatetime()
        rates = self._mt5.copy_rates_from(self._symbol, self._timeframe(tf), when, count + 1)
        if rates is None or len(rates) == 0:
            return None
        df = self._to_frame(rates, tf)
        df = df[df["time"] < before].tail(count).reset_index(drop=True)
        return df if len(df) else None

    def fetch_range(self, tf: str, start: pd.Timestamp, end: pd.Timestamp, chunk_bars: int) -> pd.DataFrame:
        """Tải theo từng đoạn `chunk_bars` nến vì MT5 từ chối yêu cầu quá lớn trong một lần gọi."""
        lo = utc_to_server(start - _RANGE_PAD, self._server_time)
        hi = utc_to_server(end + _RANGE_PAD, self._server_time)
        step = tf_delta(tf) * chunk_bars
        parts = []
        cursor = lo
        while cursor < hi:
            stop = min(cursor + step, hi)
            rates = self._mt5.copy_rates_range(self._symbol, self._timeframe(tf), cursor.to_pydatetime(),
                                               stop.to_pydatetime())
            if rates is None:
                raise DataError(f"MT5 không trả dữ liệu {self._symbol} {tf} ({cursor} → {stop}): "
                                f"{self._mt5.last_error()}")
            if len(rates):
                parts.append(pd.DataFrame(rates))
            cursor = stop
        if not parts:
            raise DataError(f"MT5 không có dữ liệu {self._symbol} {tf} trong giai đoạn yêu cầu")
        df = self._to_frame(pd.concat(parts, ignore_index=True), tf)
        return df[(df["time"] >= start) & (df["close_time"] <= end)].reset_index(drop=True)

    def symbol_spec(self) -> SymbolSpec:
        info = self._mt5.symbol_info(self._symbol)
        if info is None:
            raise DataError(f"Không đọc được symbol_info {self._symbol}")
        return SymbolSpec(point=info.point, tick_size=info.trade_tick_size, tick_value=info.trade_tick_value,
                          volume_min=info.volume_min, volume_step=info.volume_step, volume_max=info.volume_max)
