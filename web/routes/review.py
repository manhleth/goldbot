"""Vẽ tay + nhận xét lệnh: lưu/đọc nét vẽ theo scope, dữ liệu chart tương tác của từng lệnh, danh sách đã nhận xét."""
from __future__ import annotations

import logging

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from journal.reviews import ReviewStore
from web.services.review_chart import Window, chart_payload, load_item, snapshot
from web.state import AppState, get_state

router = APIRouter(prefix="/api")
log = logging.getLogger(__name__)
KINDS = ("trade", "leg", "signal")


class Point(BaseModel):
    t: int          # Unix giây UTC
    p: float        # giá


class Shape(BaseModel):
    id: str
    kind: str       # trend | hline | zone
    role: str       # khóa trong review.roles (vd note / right / wrong)
    points: list[Point]
    text: str | None = None


class Annotation(BaseModel):
    shapes: list[Shape] | None = None
    verdict: str | None = None
    errors: list[str] | None = None
    note: str | None = None
    item: dict | None = None    # {kind, mode, key}: để lưu kèm tóm tắt lệnh


def _cfg(state: AppState) -> dict:
    return state.cfg["review"]


def _store(state: AppState) -> ReviewStore:
    return ReviewStore(state.root / _cfg(state)["db"])


def _item(state: AppState, kind: str, mode: str, key: int) -> dict:
    if kind not in KINDS:
        raise HTTPException(400, f"Loại không hợp lệ: {kind}")
    try:
        journal = state.journal(mode)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    broker = state.gateway.positions().get(key) if kind == "leg" else None
    with journal:
        item = load_item(journal, kind, key, broker)
    if item is None:
        raise HTTPException(404, "Không có lệnh/tín hiệu này")
    return item


@router.get("/review/options")
def options(state: AppState = Depends(get_state)) -> dict:
    """Vai trò nét vẽ, kết luận và danh sách lỗi (cấu hình trong config.yaml mục review)."""
    cfg = _cfg(state)
    return {k: cfg[k] for k in ("roles", "verdicts", "error_tags")}


@router.get("/review-chart/{kind}/{mode}/{key}")
def review_chart(kind: str, mode: str, key: int, state: AppState = Depends(get_state)) -> dict:
    item = _item(state, kind, mode, key)
    cfg = _cfg(state)
    with state.journal(mode) as journal:
        payload = chart_payload(journal, item, state.cfg, state.gateway, Window(cfg["pad_bars"], cfg["max_bars"]),
                                pd.Timestamp.now(tz="UTC"))
    if payload is None:
        raise HTTPException(404, "Không lấy được nến để vẽ (MT5 chưa kết nối và cache không có khoảng này)")
    return payload


@router.get("/reviews")
def reviews(state: AppState = Depends(get_state)) -> list[dict]:
    with _store(state) as store:
        return store.reviewed()


@router.get("/review/{scope:path}")
def get_annotation(scope: str, state: AppState = Depends(get_state)) -> dict:
    with _store(state) as store:
        return store.get(scope) or {"scope": scope, "shapes": [], "verdict": None, "errors": [], "note": None}


@router.put("/review/{scope:path}")
def save_annotation(scope: str, body: Annotation, state: AppState = Depends(get_state)) -> dict:
    values = body.model_dump(exclude_unset=True, exclude={"item"})
    if "shapes" in values:
        values["shapes"] = [s.model_dump() for s in body.shapes or []]
    if body.item:
        item = _item(state, body.item["kind"], body.item["mode"], int(body.item["key"]))
        values["snapshot"] = {**snapshot(item, body.item["kind"]), "mode": body.item["mode"]}
    log.info("Lưu nhận xét %s: %s", scope, {k: v for k, v in values.items() if k != "snapshot"})
    with _store(state) as store:
        return store.save(scope, values, pd.Timestamp.now(tz="UTC"))
