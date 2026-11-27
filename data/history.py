"""Cache CSV dữ liệu lịch sử; tự tải từ MT5 khi cache thiếu hoặc không phủ đủ giai đoạn."""
from __future__ import annotations

import json
import logging
from collections.abc import Callable
from pathlib import Path

import pandas as pd

from core.config import timeframes
from core.timeframes import tf_delta
from data.candles import normalize
from data.mt5_source import MT5Source
from risk.sizing import SymbolSpec

log = logging.getLogger(__name__)

_WEEKEND_FACTOR = 1.6  # đổi số nến sang số ngày lịch (bù cuối tuần/ngày nghỉ)
_COVER_SLACK = pd.Timedelta(days=7)


def cache_path(cache_dir: Path, symbol: str, tf: str) -> Path:
    return cache_dir / f"{symbol}_{tf}.csv"


def spec_path(cache_dir: Path, symbol: str) -> Path:
    return cache_dir / f"{symbol}_spec.json"


def warmup_start(start: pd.Timestamp, tf: str, bars: int) -> pd.Timestamp:
    return start - tf_delta(tf) * int(bars * _WEEKEND_FACTOR)


def _covers(df: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp) -> bool:
    if df.empty:
        return False
    now = pd.Timestamp.now(tz="UTC")
    return df["time"].iat[0] <= start + _COVER_SLACK and df["close_time"].iat[-1] >= min(end, now) - _COVER_SLACK


def load_csv(path: Path, tf: str) -> pd.DataFrame:
    return normalize(pd.read_csv(path), tf)


def load_history(cfg: dict, start: pd.Timestamp, end: pd.Timestamp, refresh: bool,
                 source_factory: Callable[[], MT5Source]) -> tuple[dict[str, pd.DataFrame], SymbolSpec]:
    """Trả nến (chưa enrich) cho mọi khung, gồm cả đoạn warm-up trước `start`."""
    cache_dir = Path(cfg["data"]["cache_dir"])
    cache_dir.mkdir(parents=True, exist_ok=True)
    symbol = cfg["symbol"]
    source: MT5Source | None = None
    frames: dict[str, pd.DataFrame] = {}
    for tf in timeframes(cfg):
        path = cache_path(cache_dir, symbol, tf)
        tf_start = warmup_start(start, tf, cfg["data"]["history_bars"][tf])
        cached = load_csv(path, tf) if path.exists() and not refresh else None
        if cached is not None and _covers(cached, tf_start, end):
            frames[tf] = cached
            continue
        source = source or source_factory()
        log.info("Tải %s %s từ %s tới %s", symbol, tf, tf_start.date(), end.date())
        frames[tf] = source.fetch_range(tf, tf_start, end, cfg["data"]["fetch_chunk_bars"])
        frames[tf].drop(columns="close_time").to_csv(path, index=False)
        if not _covers(frames[tf], tf_start, end):
            log.warning("MT5 chỉ có %s %s từ %s (cần từ %s). Tăng 'Max bars in chart' trong MT5 nếu thiếu.",
                        symbol, tf, frames[tf]["time"].iat[0].date(), tf_start.date())
    if source is not None:
        save_spec(spec_path(cache_dir, symbol), source.symbol_spec())
    return frames, load_spec(spec_path(cache_dir, symbol), cfg)


def save_spec(path: Path, spec: SymbolSpec) -> None:
    path.write_text(json.dumps(spec.as_dict(), indent=2), encoding="utf-8")


def load_spec(path: Path, cfg: dict) -> SymbolSpec:
    if path.exists():
        return SymbolSpec(**json.loads(path.read_text(encoding="utf-8")))
    return SymbolSpec(**cfg["backtest"]["symbol_spec"])
