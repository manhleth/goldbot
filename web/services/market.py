"""Dữ liệu nến cho giao diện: ưu tiên MT5, không có thì đọc cache CSV của backtest."""
from __future__ import annotations

import threading
import time
from pathlib import Path

import pandas as pd

from core.config import timeframes
from data.history import cache_path, load_csv
from data.mt5_source import MT5Source
from structure.indicators import enrich
from web.services.mt5_gateway import MT5Gateway


def chart_timeframes(cfg: dict) -> list[str]:
    """Khung của phân tích + khung chọn được trên chart (web.chart_timeframes), không trùng."""
    return list(dict.fromkeys([*timeframes(cfg), *cfg["web"].get("chart_timeframes", [])]))


class DataUnavailable(RuntimeError):
    pass


class MarketData:
    def __init__(self, cfg: dict, gateway: MT5Gateway) -> None:
        self._cfg = cfg
        self._gateway = gateway
        self._lock = threading.Lock()
        self._cached: tuple[float, dict[str, pd.DataFrame], str] | None = None

    def frames(self) -> tuple[dict[str, pd.DataFrame], str]:
        """(nến đã enrich theo khung, nguồn 'mt5' | 'cache')."""
        with self._lock:
            ttl = self._cfg["web"]["cache_seconds"]
            if self._cached is not None and time.monotonic() - self._cached[0] < ttl:
                return self._cached[1], self._cached[2]
            raw, source = self._from_mt5(), "mt5"
            if raw is None:
                raw, source = self._from_cache(), "cache"
            frames = {tf: enrich(df, self._cfg["structure"]) for tf, df in raw.items()}
            self._cached = (time.monotonic(), frames, source)
            return frames, source

    def history(self, tf: str, before: pd.Timestamp, count: int) -> tuple[pd.DataFrame | None, str]:
        """Nến cũ hơn `before` để kéo chart về quá khứ: MT5 trước, hết dữ liệu thì cache (file _long rồi file thường)."""
        cfg = self._cfg
        df = self._gateway.call(lambda mt5: MT5Source(mt5, cfg["symbol"], cfg["data"]["server_time"])
                                .fetch_before(tf, before, count))
        if df is not None:
            return df, "mt5"
        cache_dir = Path(cfg["data"]["cache_dir"])
        for path in (cache_dir / f"{cfg['symbol']}_{tf}_long.csv", cache_path(cache_dir, cfg["symbol"], tf)):
            if path.exists():
                old = load_csv(path, tf)
                old = old[old["time"] < before].tail(count).reset_index(drop=True)
                if len(old):
                    return old, "cache"
        return None, "none"

    def _from_mt5(self) -> dict[str, pd.DataFrame] | None:
        cfg = self._cfg
        now = pd.Timestamp.now(tz="UTC")

        def fetch(mt5) -> dict[str, pd.DataFrame]:
            source = MT5Source(mt5, cfg["symbol"], cfg["data"]["server_time"])
            return {tf: source.fetch_last(tf, cfg["data"]["history_bars"][tf], now) for tf in chart_timeframes(cfg)}
        return self._gateway.call(fetch)

    def _from_cache(self) -> dict[str, pd.DataFrame]:
        cache_dir = Path(self._cfg["data"]["cache_dir"])
        frames = {}
        for tf in chart_timeframes(self._cfg):
            path = cache_path(cache_dir, self._cfg["symbol"], tf)
            if not path.exists() and tf not in timeframes(self._cfg):
                continue  # khung chỉ để xem (D1/W1) chưa có cache thì bỏ qua
            if not path.exists():
                raise DataUnavailable(f"Chưa kết nối được MT5 ({self._gateway.error}) và chưa có cache {path.name}.")
            frames[tf] = load_csv(path, tf).tail(self._cfg["data"]["history_bars"][tf]).reset_index(drop=True)
        return frames
