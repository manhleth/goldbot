"""Chạy backtest phương pháp ONE nền từ giao diện: chọn phương pháp, giai đoạn, vốn và % rủi ro từng phương pháp."""
from __future__ import annotations

import json
import re
from pathlib import Path

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from core.timeframes import TF_MINUTES
from playbook.runner import load_playbook
from web.state import AppState, get_state

router = APIRouter(prefix="/api/backtest")
_RUN_LINE = re.compile(r"^Run: (\S+)", re.MULTILINE)
BASE_TF = "M15"            # cùng khung gốc với bot live
FAMILY = "unified"         # chỉ các phương pháp họ ONE
VARIANT = "hold_tf"        # quản lý lệnh như bot live


class BacktestRequest(BaseModel):
    start: str
    end: str
    methods: list[str] = Field(min_length=1)
    capital: dict[str, float] = Field(min_length=1)   # vốn riêng từng phương pháp ($)
    risk: dict[str, float] = {}
    max_lot: dict[str, float] = {}                    # lot tối đa mỗi lệnh theo phương pháp
    risk_caps: dict[str, list[list[float]]] = {}      # [[vốn ≥ X$, % tối đa], ...] theo phương pháp
    refresh: bool = False
    cent: bool = False                                # tài khoản cent (1 lot cent = 0.01 lot thường)


CENT_SCALE = 0.01


def _methods(state: AppState) -> dict[str, dict]:
    pb = load_playbook(state.root / "playbook.yaml")
    bots = {bc["method"]: name for name, bc in state.cfg.get("bots", {}).items()}
    out = {}
    for name, m in pb["methods"].items():
        tfs = (m.get("patterns") or {}).get("timeframes", [])
        if m.get("fn") != FAMILY or any(TF_MINUTES[tf] < TF_MINUTES[BASE_TF] for tf in tfs):
            continue  # chỉ họ ONE, và khung mẫu hình phải ≥ khung gốc (M5 cần dữ liệu nền M5)
        out[name] = {"name": name, "title": m.get("title", name), "risk_pct": m.get("risk_pct"),
                     "capital_share": m.get("capital_share", 1.0), "bot": bots.get(name),
                     "max_lot": m.get("max_lot"), "risk_caps": m.get("risk_caps")}
    return out


@router.get("/methods")
def methods(state: AppState = Depends(get_state)) -> list[dict]:
    """Phương pháp ONE trong playbook.yaml; phương pháp đang chạy live (bot) đứng trước."""
    return sorted(_methods(state).values(), key=lambda m: (m["bot"] is None, m["name"]))


@router.post("")
def start(body: BacktestRequest, state: AppState = Depends(get_state)) -> dict:
    try:
        start_ts, end_ts = pd.Timestamp(body.start), pd.Timestamp(body.end)
    except ValueError as exc:
        raise HTTPException(400, "Ngày không hợp lệ (định dạng YYYY-MM-DD)") from exc
    if start_ts >= end_ts:
        raise HTTPException(400, "Ngày bắt đầu phải trước ngày kết thúc")
    known = _methods(state)
    unknown = [m for m in body.methods if m not in known]
    if unknown:
        raise HTTPException(400, f"Không có phương pháp: {', '.join(unknown)}")
    bad = {k: v for k, v in body.risk.items() if k not in body.methods or not 0 < v <= 100}
    if bad:
        raise HTTPException(400, f"% rủi ro không hợp lệ: {bad}")
    missing = [m for m in body.methods if not body.capital.get(m, 0) > 0]
    if missing:
        raise HTTPException(400, f"Thiếu vốn (> 0) cho: {', '.join(missing)}")
    data = Path(state.cfg["data"]["cache_dir"]) / f"{state.cfg['symbol']}_{BASE_TF}_long.csv"
    args = ["playbook", "--from", f"{start_ts:%Y-%m-%d}", "--to", f"{end_ts:%Y-%m-%d}", "--only", ",".join(body.methods),
            "--base", BASE_TF, "--data", str(data), "--variant", VARIANT,
            "--capital-by", ",".join(f"{m}={body.capital[m]:g}" for m in body.methods)]
    if body.risk:
        args += ["--risk", ",".join(f"{k}={v:g}" for k, v in body.risk.items())]
    extra = {m: {k: v for k, v in (("max_lot", body.max_lot.get(m)), ("risk_caps", body.risk_caps.get(m))) if v}
             for m in body.methods}
    extra = {m: v for m, v in extra.items() if v}
    if extra:
        args += ["--overrides", json.dumps(extra)]
    if body.cent:
        args += ["--cent", f"{CENT_SCALE:g}"]
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
    run_ids = _RUN_LINE.findall(log)
    return {"running": state.backtest.is_running(), "exit_code": state.backtest.exit_code(),
            "run_id": run_ids[0] if run_ids else None, "run_ids": run_ids,
            "log": "".join(log.splitlines(True)[-lines:])}


@router.post("/stop")
def stop(state: AppState = Depends(get_state)) -> dict:
    state.backtest.stop()
    return {"running": state.backtest.is_running()}
