"""Lệnh đang mở, lịch sử lệnh, tín hiệu, các lần chạy và báo cáo thống kê."""
from __future__ import annotations

import math
from pathlib import Path

import pandas as pd
import yaml
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse

from stats.metrics import summarize
from stats.money import equity_curve, money_summary, monthly, r_histogram
from stats.report import BREAKDOWNS, breakdown, build_report, signal_summary, verdict, with_dimensions
from web.state import AppState, get_state, is_live

router = APIRouter(prefix="/api")


def _clean(records: list[dict]) -> list[dict]:
    return [{k: (None if isinstance(v, float) and not math.isfinite(v) else v) for k, v in r.items()} for r in records]


def _run_filter(journal, mode: str, run: str | None) -> tuple[str, list]:
    """live: mặc định mọi lần chạy; backtest: mặc định lần gần nhất."""
    if run == "all" or (run is None and is_live(mode)):
        return "", []
    run_id = run or journal.latest_run(mode)
    if run_id is None:
        raise HTTPException(404, "Chưa có lần chạy nào")
    return " WHERE run_id = ?", [run_id]


def _journal(state: AppState, mode: str):
    try:
        return state.journal(mode)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.get("/runs")
def runs(mode: str = "backtest", state: AppState = Depends(get_state)) -> list[dict]:
    with _journal(state, mode) as journal:
        rows = journal.rows("SELECT r.run_id, r.created_at, r.config_hash, r.params, "
                            "(SELECT COUNT(*) FROM trades t WHERE t.run_id = r.run_id) AS trades, "
                            "(SELECT SUM(r_multiple) FROM trades t WHERE t.run_id = r.run_id) AS total_r "
                            "FROM runs r WHERE r.mode = ? ORDER BY r.created_at DESC LIMIT 100",
                            ["live" if is_live(mode) else mode])
    return _clean(rows)


@router.get("/trades")
def trades(mode: str = "live", run: str | None = None, limit: int = 2000, state: AppState = Depends(get_state)):
    with _journal(state, mode) as journal:
        where, params = _run_filter(journal, mode, run)
        rows = journal.rows(f"SELECT * FROM trades{where} ORDER BY entry_time DESC LIMIT ?", [*params, limit])
    return _clean(rows)


@router.get("/charts/{mode}/{trade_id}")
def trade_chart(mode: str, trade_id: int, state: AppState = Depends(get_state)) -> FileResponse:
    """Chart lý do vào lệnh (SVG) của một lệnh; chỉ phục vụ file nằm trong thư mục charts của journal."""
    with _journal(state, mode) as journal:
        rows = journal.rows("SELECT chart FROM trades WHERE id = ?", [trade_id])
    if not rows or not rows[0].get("chart"):
        raise HTTPException(404, "Lệnh này không có chart")
    path = Path(rows[0]["chart"]).resolve()
    allowed = (state.root / "journal" / "charts").resolve()
    if allowed not in path.parents or not path.is_file():
        raise HTTPException(404, "Không tìm thấy chart")
    return FileResponse(path, media_type="image/svg+xml")


@router.get("/signals")
def signals(mode: str = "live", run: str | None = None, limit: int = 500, state: AppState = Depends(get_state)):
    with _journal(state, mode) as journal:
        where, params = _run_filter(journal, mode, run)
        rows = journal.rows(f"SELECT * FROM signals{where} ORDER BY time DESC LIMIT ?", [*params, limit])
    return _clean(rows)


@router.get("/positions")
def positions(state: AppState = Depends(get_state)) -> dict:
    legs = []
    for mode in ["live", *(f"bot:{name}" for name in state.cfg.get("bots", {}))]:
        with state.journal(mode) as journal:
            legs += journal.rows("SELECT * FROM live_legs WHERE status = 'open' ORDER BY ticket")
    broker = state.gateway.positions()
    for leg in legs:
        leg["broker"] = broker.pop(leg["ticket"], None)
    return {"legs": _clean(legs), "unmanaged": list(broker.values())}


def _initial_equity(journal, mode: str, run_id: str | None, cfg: dict) -> float:
    """Backtest: vốn ban đầu ghi trong config của chính lần chạy; live: equity lúc bot kết nối lần đầu."""
    if is_live(mode):
        stored = journal.get_kv("live_initial_equity")
        return float(stored) if stored else float(cfg["backtest"]["initial_equity"])
    found = journal.rows("SELECT config FROM runs WHERE run_id = ?", [run_id])
    if found:
        return float(yaml.safe_load(found[0]["config"])["backtest"]["initial_equity"])
    return float(cfg["backtest"]["initial_equity"])


def _ts(value) -> int:
    return int(pd.Timestamp(value).timestamp())


@router.get("/report")
def report(mode: str = "backtest", run: str | None = None, state: AppState = Depends(get_state)) -> dict:
    cfg = state.cfg
    with _journal(state, mode) as journal:
        where, params = _run_filter(journal, mode, run)
        trades_df = journal.frame(f"SELECT * FROM trades{where} ORDER BY exit_time", params)
        equity_df = journal.frame(f"SELECT * FROM equity{where} ORDER BY time", params)
        signals_df = journal.frame(f"SELECT * FROM signals{where}", params)
        initial = _initial_equity(journal, mode, params[0] if params else None, cfg)
    rejected = signals_df[signals_df["accepted"] == 0] if not signals_df.empty else signals_df
    result = {
        "run": params[0] if params else "all", "verdict": verdict(len(trades_df), cfg["stats"]),
        "summary": None, "money": None, "breakdowns": {}, "equity_curve": [], "monthly": [], "r_histogram": [],
        "signals": {"total": int(len(signals_df)), "accepted": int(signals_df["accepted"].sum()) if len(signals_df) else 0,
                    "rejected": {str(k): int(v) for k, v in rejected["reject_reason"].value_counts().items()}
                    if len(rejected) else {}},
        "max_drawdown_floating_pct": float(equity_df["drawdown_pct"].max())
        if not equity_df.empty and equity_df["drawdown_pct"].notna().any() else None,
        "text": signal_summary(signals_df) + "\n\n" + build_report(trades_df, equity_df, cfg),
    }
    if trades_df.empty:
        return result
    trades_df["pnl"] = trades_df["pnl"].fillna(0.0)
    result["summary"] = _clean([summarize(trades_df["r_multiple"])])[0]
    result["money"] = _clean([money_summary(trades_df, initial)])[0]
    enriched = with_dimensions(trades_df, cfg["sessions"])
    for title, column in BREAKDOWNS:
        if column in enriched.columns:
            table = breakdown(enriched, column)
            table["pnl"] = enriched.groupby(column)["pnl"].sum()
            result["breakdowns"][title] = _clean(table.reset_index(names="key").to_dict("records"))
    curve = equity_curve(trades_df, initial)
    result["equity_curve"] = [{"time": _ts(t), "equity": float(e), "drawdown_pct": float(d)}
                              for t, e, d in zip(curve["time"], curve["equity"], curve["drawdown_pct"])]
    result["monthly"] = monthly(trades_df)
    result["r_histogram"] = r_histogram(trades_df["r_multiple"])
    return result
