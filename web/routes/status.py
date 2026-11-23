"""Trạng thái hệ thống và điều khiển bot."""
from __future__ import annotations

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from execution.live import shutdown_file
from execution.one_bot import bot_shutdown_file
from news.calendar import build_calendar
from web.services.analysis import ts
from web.state import AppState, get_state

router = APIRouter(prefix="/api")


class KillSwitch(BaseModel):
    enabled: bool


def _news_status(state: AppState) -> dict:
    nc = state.cfg["news"]
    now = pd.Timestamp.now(tz="UTC")
    calendar = build_calendar(state.news.all(), nc)
    blackout = calendar.in_blackout(now, nc["blackout_minutes"])
    upcoming = calendar.between(now, now + pd.Timedelta(days=7))
    nxt = upcoming[0] if upcoming else None
    return {"blackout": blackout.title if blackout else None,
            "next": {"title": nxt.title, "time": ts(nxt.time)} if nxt else None}


@router.get("/status")
def status(state: AppState = Depends(get_state)) -> dict:
    with state.journal("live") as journal:
        heartbeat = journal.get_kv("heartbeat")
    account, quote = state.gateway.account(), state.gateway.quote()  # thử kết nối trước khi đọc trạng thái lỗi
    return {
        "symbol": state.cfg["symbol"],
        "mt5": {"connected": state.gateway.connected, "error": state.gateway.error, "account": account,
                "quote": quote},
        "bot": {"running": state.bot.is_running(), "heartbeat": heartbeat},
        "bots": _bots(state),
        "kill_switch": state.stop_file.exists(),
        "backtest_running": state.backtest.is_running(),
        "news": _news_status(state),
        "timeframes": state.cfg["timeframes"],
    }


def _bots(state: AppState) -> list[dict]:
    out = []
    for name, bc in state.cfg.get("bots", {}).items():
        with state.journal(f"bot:{name}") as journal:
            heartbeat = journal.get_kv("heartbeat")
            open_legs = journal.rows("SELECT COUNT(*) AS n FROM live_legs WHERE status = 'open'")[0]["n"]
        out.append({"name": name, "method": bc["method"], "running": state.bots[name].is_running(),
                    "heartbeat": heartbeat, "open": open_legs})
    return out


def _managed(state: AppState, name: str):
    if name not in state.bots:
        raise HTTPException(404, f"không có bot {name}")
    return state.bots[name]


@router.post("/bots/{name}/start")
def start_named_bot(name: str, state: AppState = Depends(get_state)) -> dict:
    try:
        _managed(state, name).start(["bot", "--name", name])
    except RuntimeError as exc:
        raise HTTPException(409, str(exc)) from exc
    return {"running": True}


@router.post("/bots/{name}/stop")
def stop_named_bot(name: str, state: AppState = Depends(get_state)) -> dict:
    proc = _managed(state, name)
    proc.stop(graceful_file=bot_shutdown_file(state.root, name))
    return {"running": proc.is_running()}


@router.post("/bot/start")
def start_bot(state: AppState = Depends(get_state)) -> dict:
    try:
        state.bot.start(["live"])
    except RuntimeError as exc:
        raise HTTPException(409, str(exc)) from exc
    return {"running": True}


@router.post("/bot/stop")
def stop_bot(state: AppState = Depends(get_state)) -> dict:
    state.bot.stop(graceful_file=shutdown_file(state.root))
    return {"running": state.bot.is_running()}


@router.get("/bot/log")
def bot_log(lines: int = 300, state: AppState = Depends(get_state)) -> dict:
    return {"text": state.bot.tail(lines)}


@router.post("/killswitch")
def kill_switch(body: KillSwitch, state: AppState = Depends(get_state)) -> dict:
    if body.enabled:
        state.stop_file.touch()
    else:
        state.stop_file.unlink(missing_ok=True)
    return {"kill_switch": state.stop_file.exists()}
