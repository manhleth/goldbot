"""Nến và phân tích cấu trúc cho biểu đồ."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from core.config import timeframes
from web.services.analysis import analysis_payload, candles_payload
from web.services.market import DataUnavailable
from web.state import AppState, get_state

router = APIRouter(prefix="/api")


def _frames(state: AppState):
    try:
        return state.market.frames()
    except DataUnavailable as exc:
        raise HTTPException(503, str(exc)) from exc


def _check_tf(state: AppState, tf: str) -> None:
    if tf not in timeframes(state.cfg):
        raise HTTPException(400, f"Khung {tf} không có trong config")


@router.get("/candles")
def candles(tf: str, bars: int = 600, state: AppState = Depends(get_state)) -> dict:
    _check_tf(state, tf)
    frames, source = _frames(state)
    return {"source": source, **candles_payload(frames[tf], state.cfg["structure"]["ema"], bars)}


@router.get("/analysis")
def analysis(tf: str, state: AppState = Depends(get_state)) -> dict:
    _check_tf(state, tf)
    frames, source = _frames(state)
    return {"source": source, **analysis_payload(frames, state.cfg, tf)}
