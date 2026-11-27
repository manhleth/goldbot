"""Số tiền lời/lỗ nếu giá chạm SL / TP / mục tiêu tham khảo của một lệnh (hiển thị trong khung chi tiết lệnh)."""
from __future__ import annotations

import json
import re
from pathlib import Path

from data.history import load_spec, spec_path

_TARGET = re.compile(r"mục tiêu\s+([0-9]+(?:\.[0-9]+)?)")


def price_value(gateway_value: float | None, cfg: dict) -> float:
    """Tiền lời/lỗ khi giá chạy 1 đơn vị với 1 lot: ưu tiên thông số MT5 đang kết nối, không có thì spec đã lưu."""
    if gateway_value:
        return gateway_value
    spec = load_spec(spec_path(Path(cfg["data"]["cache_dir"]), cfg["symbol"]), cfg)
    return spec.tick_value / spec.tick_size


def target_of(meta: str | dict | None, reasons: str | list | None) -> float | None:
    """Mục tiêu measured move: từ meta của mẫu hình; lệnh cũ chưa có meta thì đọc từ dòng lý do."""
    if isinstance(meta, str) and meta:
        meta = json.loads(meta)
    if isinstance(meta, dict) and meta.get("target") is not None:
        return float(meta["target"])
    texts = json.loads(reasons) if isinstance(reasons, str) and reasons.startswith("[") else reasons or []
    for text in texts if isinstance(texts, list) else [texts]:
        found = _TARGET.search(str(text))
        if found:
            return float(found.group(1))
    return None


def money_levels(direction: int, entry: float, volume: float, value: float, levels: dict[str, float | None]) -> dict:
    """{tên: {price, money}}: money > 0 là lời, < 0 là lỗ nếu giá chạm mức đó (chưa tính spread/phí/trượt giá)."""
    out = {}
    for name, price in levels.items():
        if price is None or not price:
            out[name] = None
            continue
        out[name] = {"price": float(price), "money": (float(price) - entry) * direction * volume * value}
    return out
