"""Lịch tin kinh tế và chiều kỳ vọng cho vàng."""
from __future__ import annotations

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, UploadFile

from news.calendar import build_calendar
from web.services.analysis import ts
from web.state import AppState, get_state

router = APIRouter(prefix="/api/news")


@router.get("")
def calendar(days_back: int = 1, days_ahead: int = 7, state: AppState = Depends(get_state)) -> dict:
    nc = state.cfg["news"]
    now = pd.Timestamp.now(tz="UTC")
    cal = build_calendar(state.news.all(), nc)
    view = cal.forecast_view(now, nc["lookahead_hours"])
    events = cal.between(now - pd.Timedelta(days=days_back), now + pd.Timedelta(days=days_ahead))
    blackout = cal.in_blackout(now, nc["blackout_minutes"])
    last = state.news.last_refresh()
    return {
        "enabled": nc["enabled"], "rule": nc["forecast_rule"], "lookahead_hours": nc["lookahead_hours"],
        "last_refresh": last.isoformat() if last is not None else None,
        "blackout": blackout.title if blackout else None,
        "outlook": {"direction": view.direction.name, "score": view.score},
        "events": [{"time": ts(e.time), "title": e.title, "country": e.country, "impact": e.impact,
                    "forecast": e.forecast, "previous": e.previous, "gold": cal.bias_of(e).name,
                    "past": bool(e.time <= now), "source": e.source} for e in events],
    }


@router.post("/refresh")
def refresh(state: AppState = Depends(get_state)) -> dict:
    try:
        count = state.news.refresh(state.cfg["news"]["source_url"], pd.Timestamp.now(tz="UTC"))
    except Exception as exc:  # noqa: BLE001 — trả lỗi mạng cho giao diện
        raise HTTPException(502, f"Không tải được lịch tin: {exc}") from exc
    return {"count": count}


@router.post("/import")
async def import_csv(file: UploadFile, state: AppState = Depends(get_state)) -> dict:
    try:
        count = state.news.import_csv(await file.read())
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    return {"count": count}
