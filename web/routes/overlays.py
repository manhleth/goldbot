"""Lớp vẽ của bot trên chart chính: vùng S/R cứng, trendline đa tỉ lệ, cạnh mẫu hình các setup đã quét."""
from __future__ import annotations

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException

from web.services.bot_overlays import method_of, setups
from web.state import AppState, get_state

router = APIRouter(prefix="/api")


@router.get("/bot-overlays")
def bot_overlays(mode: str = "bot:swing", run: str | None = None, since: int | None = None,
                 state: AppState = Depends(get_state)) -> dict:
    """`mode`/`run` = nguồn lệnh đang chọn (bot hoặc một lần backtest); `since` = Unix giây của nến đầu trên chart."""
    try:
        journal = state.journal(mode)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    with journal:
        method, run_id = method_of(state.cfg, journal, mode, run)
        start = pd.Timestamp(since, unit="s", tz="UTC") if since else None
        found = setups(journal, run_id, start, state.cfg["web"]["bot_overlays"]["setups_limit"])
    try:
        structure = state.overlays.structure(method)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    return {**structure, "setups": found}
