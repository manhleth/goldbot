"""Sửa config.yaml và xem log."""
from __future__ import annotations

import shutil

import pandas as pd
import yaml
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from core.config import ConfigError, validate
from signals.registry import enabled_finders
from web.services.processes import tail_file
from web.state import AppState, get_state

router = APIRouter(prefix="/api")
LOG_FILES = ("live", "backtest", "web", "bot_swing", "bot_day")


class ConfigBody(BaseModel):
    text: str


@router.get("/config")
def get_config(state: AppState = Depends(get_state)) -> dict:
    return {"text": state.config_path.read_text(encoding="utf-8")}


@router.put("/config")
def put_config(body: ConfigBody, state: AppState = Depends(get_state)) -> dict:
    try:
        cfg = yaml.safe_load(body.text)
        validate(cfg)
        enabled_finders(cfg)
    except (yaml.YAMLError, ConfigError, KeyError, TypeError) as exc:
        raise HTTPException(400, f"Config không hợp lệ: {exc}") from exc
    backup = state.config_path.with_name(f"config.{pd.Timestamp.now():%Y%m%d-%H%M%S}.bak.yaml")
    shutil.copyfile(state.config_path, backup)
    state.config_path.write_text(body.text, encoding="utf-8")
    state.reload()
    return {"saved": True, "backup": backup.name, "bot_running": state.bot.is_running()}


@router.get("/logs/{name}")
def logs(name: str, lines: int = 300, state: AppState = Depends(get_state)) -> dict:
    if name not in LOG_FILES:
        raise HTTPException(404, f"Log không tồn tại. Có: {LOG_FILES}")
    return {"text": tail_file(state.root / "logs" / f"{name}.log", lines)}
