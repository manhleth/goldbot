"""Nến và phân tích cấu trúc cho biểu đồ."""
from __future__ import annotations

import pandas as pd
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
    frames, source = _frames(state)
    if tf not in frames:
        raise HTTPException(400, f"Khung {tf} không có trong web.chart_timeframes")
    return {"source": source, **candles_payload(frames[tf], state.cfg["structure"]["ema"], bars)}


MAX_HISTORY_BARS = 5000


@router.get("/candles/history")
def candles_history(tf: str, before: int, bars: int = 1000, state: AppState = Depends(get_state)) -> dict:
    """Nến cũ hơn `before` (Unix giây UTC) khi kéo chart sang trái; rỗng = hết dữ liệu."""
    if tf not in state.cfg["web"].get("chart_timeframes", []):
        raise HTTPException(400, f"Khung {tf} không có trong web.chart_timeframes")
    df, source = state.market.history(tf, pd.Timestamp(before, unit="s", tz="UTC"), min(bars, MAX_HISTORY_BARS))
    if df is None:
        return {"source": source, "candles": []}
    return {"source": source, "candles": [{"time": int(t.timestamp()), "open": o, "high": h, "low": lo, "close": c}
                                          for t, o, h, lo, c in df[["time", "open", "high", "low", "close"]]
                                          .itertuples(index=False)]}


@router.get("/analysis")
def analysis(tf: str, state: AppState = Depends(get_state)) -> dict:
    _check_tf(state, tf)
    frames, source = _frames(state)
    return {"source": source, **analysis_payload(frames, state.cfg, tf)}
