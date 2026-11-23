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

    def _from_mt5(self) -> dict[str, pd.DataFrame] | None:
        cfg = self._cfg
        now = pd.Timestamp.now(tz="UTC")

        def fetch(mt5) -> dict[str, pd.DataFrame]:
            source = MT5Source(mt5, cfg["symbol"], cfg["data"]["server_time"])
            return {tf: source.fetch_last(tf, cfg["data"]["history_bars"][tf], now) for tf in timeframes(cfg)}
        return self._gateway.call(fetch)

    def _from_cache(self) -> dict[str, pd.DataFrame]:
        cache_dir = Path(self._cfg["data"]["cache_dir"])
        frames = {}
        for tf in timeframes(self._cfg):
            path = cache_path(cache_dir, self._cfg["symbol"], tf)
            if not path.exists():
                raise DataUnavailable(f"Chưa kết nối được MT5 ({self._gateway.error}) và chưa có cache {path.name}.")
            frames[tf] = load_csv(path, tf).tail(self._cfg["data"]["history_bars"][tf]).reset_index(drop=True)
        return frames
