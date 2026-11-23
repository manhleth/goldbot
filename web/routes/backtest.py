"""Chạy backtest nền từ giao diện."""
from __future__ import annotations

import re

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from web.state import AppState, get_state

router = APIRouter(prefix="/api/backtest")
_RUN_LINE = re.compile(r"^Run: (\S+)", re.MULTILINE)


class BacktestRequest(BaseModel):
    start: str
    end: str
    refresh: bool = False


@router.post("")
def start(body: BacktestRequest, state: AppState = Depends(get_state)) -> dict:
    try:
        start_ts, end_ts = pd.Timestamp(body.start), pd.Timestamp(body.end)
    except ValueError as exc:
        raise HTTPException(400, "Ngày không hợp lệ (định dạng YYYY-MM-DD)") from exc
    if start_ts >= end_ts:
        raise HTTPException(400, "Ngày bắt đầu phải trước ngày kết thúc")
    args = ["backtest", "--from", f"{start_ts:%Y-%m-%d}", "--to", f"{end_ts:%Y-%m-%d}"]
    if body.refresh:
        args.append("--refresh")
    try:
        state.backtest.start(args)
    except RuntimeError as exc:
        raise HTTPException(409, str(exc)) from exc
    return {"running": True}


@router.get("/status")
def status(lines: int = 60, state: AppState = Depends(get_state)) -> dict:
    log = state.backtest.tail(2000)
    match = _RUN_LINE.search(log)
    return {"running": state.backtest.is_running(), "exit_code": state.backtest.exit_code(),
            "run_id": match.group(1) if match else None, "log": "".join(log.splitlines(True)[-lines:])}


@router.post("/stop")
def stop(state: AppState = Depends(get_state)) -> dict:
    state.backtest.stop()
    return {"running": state.backtest.is_running()}
