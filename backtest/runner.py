"""Chạy backtest end-to-end: nạp dữ liệu → enrich → mô phỏng → ghi journal."""
from __future__ import annotations

import logging

import pandas as pd

from backtest.engine import Backtester, BacktestResult
from core.config import config_hash
from core.mt5_client import connect
from data.history import load_history
from data.mt5_source import MT5Source
from journal.db import Journal
from news.calendar import build_calendar
from news.store import NewsStore
from structure.indicators import enrich

log = logging.getLogger(__name__)


def run_backtest(cfg: dict, start: pd.Timestamp, end: pd.Timestamp, refresh: bool = False) -> tuple[str, Journal]:
    def source_factory() -> MT5Source:
        return MT5Source(connect(cfg), cfg["symbol"], cfg["data"]["server_time"])

    raw, spec = load_history(cfg, start, end, refresh, source_factory)
    frames = {tf: enrich(df, cfg["structure"]) for tf, df in raw.items()}
    calendar = build_calendar(NewsStore(cfg["news"]["db"]).all(), cfg["news"])
    covered = calendar.between(start, end)
    log.info("Lịch tin trong giai đoạn backtest: %d sự kiện%s", len(covered),
             "" if covered else " — bộ lọc tin sẽ không có tác dụng (nhập CSV lịch sử trên web)")
    journal = Journal(cfg["journal"]["backtest_db"])
    run_id = journal.create_run("backtest", cfg, {"start": str(start), "end": str(end), "news_events": len(covered),
                                                  "config_hash": config_hash(cfg), "symbol_spec": spec.as_dict()})
    print(f"Run: {run_id}", flush=True)
    log.info("Backtest %s: %s → %s", run_id, start.date(), end.date())
    result = Backtester(cfg, frames, spec, run_id, calendar).run(start, end)
    save_result(journal, result)
    log.info("Xong: %d tín hiệu, %d lệnh", len(result.signals), len(result.trades))
    return run_id, journal


def save_result(journal: Journal, result: BacktestResult) -> None:
    journal.insert("signals", result.signals)
    journal.insert("trades", result.trades)
    journal.insert("equity", result.equity)
