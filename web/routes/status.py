"""Trạng thái hệ thống và điều khiển bot."""
from __future__ import annotations

import json
import logging

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from execution import bot_settings
from risk.sizing import capped_risk
from execution.live import shutdown_file
from execution.one_bot import bot_shutdown_file
from news.calendar import build_calendar
from web.services.analysis import ts
from web.state import AppState, get_state

router = APIRouter(prefix="/api")
log = logging.getLogger(__name__)


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


def _bot_summary(state: AppState, name: str, bc: dict, floating: float, now: pd.Timestamp) -> dict:
    """Thẻ bot kiểu 3Commas: trạng thái, cấu hình rủi ro, lãi/lỗ, tín hiệu gần nhất, kinh nghiệm lớp học."""
    from playbook.runner import load_playbook
    from risk.management import trading_date

    p = load_playbook(state.root / state.cfg["bot_common"]["playbook"])["methods"][bc["method"]]
    with state.journal(f"bot:{name}") as journal:
        trades = journal.frame("SELECT r_multiple, pnl, exit_time FROM trades")
        last = journal.rows("SELECT time, setup_key, direction, accepted, reject_reason FROM signals "
                            "ORDER BY time DESC LIMIT 1")
        open_legs = journal.rows("SELECT COUNT(*) AS n FROM live_legs WHERE status = 'open'")[0]["n"]
        heartbeat, experience = journal.get_kv("heartbeat"), journal.get_kv("experience")
        initial = journal.get_kv("live_initial_equity")
        share = float(journal.get_kv("capital_share") or 1.0)
        capital = bot_settings.capital(journal, share, float(initial or 0.0))
        custom_capital = bool(journal.get_kv(bot_settings.KEY_CAPITAL))
        risk = bot_settings.risk_pct(journal, p.get("risk_pct"))
        custom_risk = bool(journal.get_kv(bot_settings.KEY_RISK))
        lot_cap = bot_settings.max_lot(journal, p.get("max_lot"))
        caps = bot_settings.risk_caps(journal, p.get("risk_caps"))
        risk_now = capped_risk(risk, caps, capital) if risk else risk
    today = trading_date(now, state.cfg["sessions"])
    if len(trades):
        exits = pd.to_datetime(trades["exit_time"], utc=True, format="mixed")
        pnl_today = float(trades.loc[[trading_date(t, state.cfg["sessions"]) == today for t in exits], "pnl"].sum())
    else:
        pnl_today = 0.0
    return {
        "name": name, "method": bc["method"], "title": p.get("title", bc["method"]), "magic": bc["magic"],
        "running": state.bots[name].is_running(), "heartbeat": heartbeat, "open": open_legs,
        "risk_pct": risk, "risk_custom": custom_risk, "risk_default": p.get("risk_pct"),
        "capital": capital, "capital_custom": custom_capital, "risk_now": risk_now,
        "max_lot": lot_cap, "risk_caps": caps,
        "max_positions": p.get("max_positions"), "max_per_day": p.get("max_per_day"),
        "trades": int(len(trades)), "wins": int((trades["r_multiple"] > 0).sum()) if len(trades) else 0,
        "pnl_total": float(trades["pnl"].sum()) if len(trades) else 0.0, "pnl_today": pnl_today,
        "r_total": float(trades["r_multiple"].sum()) if len(trades) else 0.0, "floating": floating,
        "last_signal": last[0] if last else None, "initial_equity": float(initial) * share if initial else None,
        "capital_share": share,
        "experience": json.loads(experience) if experience else {},
    }


class BotSettings(BaseModel):
    capital: float | None = None    # None = vốn mặc định (equity ban đầu × phần vốn + lãi/lỗ của bot)
    risk_pct: float | None = None   # None = % rủi ro trong playbook.yaml
    max_lot: float | None = None    # None = theo playbook.yaml
    risk_caps: list[list[float]] | None = None    # [[vốn ≥ X$, % tối đa], ...]; [] = không chặn; None = theo playbook


@router.post("/bots/{name}/settings")
def save_bot_settings(name: str, body: BotSettings, state: AppState = Depends(get_state)) -> dict:
    """Đặt vốn và % rủi ro cho bot live; bot dùng giá trị mới từ lệnh kế tiếp (không cần khởi động lại)."""
    if name not in state.cfg.get("bots", {}):
        raise HTTPException(404, f"Không có bot {name}")
    log.info("Lưu thiết lập bot %s: %s", name, body.model_dump())
    with state.journal(f"bot:{name}") as journal:
        try:
            bot_settings.save(journal, body.capital, body.risk_pct, pd.Timestamp.now(tz="UTC"), body.max_lot,
                              body.risk_caps)
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc
    return {"ok": True}


@router.get("/bots/summary")
def bots_summary(state: AppState = Depends(get_state)) -> list[dict]:
    positions = state.gateway.positions()
    now = pd.Timestamp.now(tz="UTC")
    out = []
    for name, bc in state.cfg.get("bots", {}).items():
        floating = sum(p["profit"] + p.get("swap", 0.0) for p in positions.values() if p["bot"] == name)
        out.append(_bot_summary(state, name, bc, floating, now))
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
