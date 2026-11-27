"""Vốn và % rủi ro của từng bot live, chỉnh từ giao diện (lưu trong kv của journal bot, bot đọc lại ở mỗi lệnh mới).

- Vốn mặc định: equity lúc bot chạy lần đầu × `capital_share` + lãi/lỗ đã chốt của chính bot.
- Vốn đặt tay (`capital_base`, `capital_since`): số tiền đặt + lãi/lỗ đã chốt của bot kể từ lúc đặt.
- % rủi ro đặt tay (`risk_pct`) thay cho `risk_pct` trong playbook.yaml; để trống = theo playbook.
- Lot tối đa (`max_lot`) và mốc chặn rủi ro theo vốn (`risk_caps`, JSON [[vốn ≥ X$, % tối đa], ...]); để trống =
  theo playbook (`max_lot`, `risk_caps` của phương pháp).
"""
from __future__ import annotations

import json

from typing import Protocol

import pandas as pd

KEY_CAPITAL, KEY_SINCE, KEY_RISK = "capital_base", "capital_since", "risk_pct"
KEY_MAX_LOT, KEY_CAPS = "max_lot", "risk_caps"
MAX_RISK_PCT = 50.0


class KV(Protocol):
    def get_kv(self, key: str) -> str | None: ...
    def set_kv(self, key: str, value: str) -> None: ...
    def rows(self, sql: str, params=()) -> list[dict]: ...


def _utc(value) -> pd.Timestamp:
    ts = pd.Timestamp(value)
    return ts.tz_localize("UTC") if ts.tzinfo is None else ts


def _float(value: str | None) -> float | None:
    return float(value) if value not in (None, "") else None


def capital(journal: KV, share: float, fallback_equity: float) -> float:
    """Vốn hiện tại của bot (≥ 0)."""
    base = _float(journal.get_kv(KEY_CAPITAL))
    if base is not None:
        since = _utc(journal.get_kv(KEY_SINCE) or "1970-01-01")
        rows = journal.rows("SELECT exit_time, pnl FROM trades WHERE pnl IS NOT NULL")
        realized = sum(float(r["pnl"]) for r in rows if _utc(r["exit_time"]) >= since)
        return max(base + realized, 0.0)
    initial = _float(journal.get_kv("live_initial_equity")) or fallback_equity
    realized = journal.rows("SELECT COALESCE(SUM(pnl), 0) AS s FROM trades")[0]["s"]
    return max(initial * share + float(realized), 0.0)


def risk_pct(journal: KV, default: float | None) -> float | None:
    return _float(journal.get_kv(KEY_RISK)) or default


def max_lot(journal: KV, default: float | None) -> float | None:
    return _float(journal.get_kv(KEY_MAX_LOT)) or default


def risk_caps(journal: KV, default) -> list:
    raw = journal.get_kv(KEY_CAPS)
    return json.loads(raw) if raw else (default or [])


def save(journal: KV, capital_base: float | None, risk: float | None, now: pd.Timestamp,
         lot_cap: float | None = None, caps: list | None = None) -> None:
    """Đặt vốn / % rủi ro / lot tối đa / mốc chặn rủi ro; None = bỏ đặt tay (quay về mặc định).
    Mốc: `[]` = không chặn (khác None = dùng mốc trong playbook)."""
    if lot_cap is not None and lot_cap <= 0:
        raise ValueError("Lot tối đa phải > 0")
    for threshold, pct in caps or []:
        if not (float(threshold) > 0 and 0 < float(pct) <= MAX_RISK_PCT):
            raise ValueError("Mốc rủi ro: vốn phải > 0 và % trong (0, 50]")
    if capital_base is not None and capital_base <= 0:
        raise ValueError("Vốn phải > 0")
    if risk is not None and not 0 < risk <= MAX_RISK_PCT:
        raise ValueError(f"% rủi ro phải trong (0, {MAX_RISK_PCT:g}]")
    journal.set_kv(KEY_CAPITAL, "" if capital_base is None else f"{capital_base:g}")
    journal.set_kv(KEY_SINCE, "" if capital_base is None else now.isoformat())
    journal.set_kv(KEY_RISK, "" if risk is None else f"{risk:g}")
    journal.set_kv(KEY_MAX_LOT, "" if lot_cap is None else f"{lot_cap:g}")
    journal.set_kv(KEY_CAPS, "" if caps is None else json.dumps(caps))  # [] = không chặn, None = theo playbook
