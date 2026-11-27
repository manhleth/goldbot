"""Dữ liệu chart tương tác cho một lệnh/tín hiệu (để người dùng vẽ và nhận xét): nến khung mẫu hình quanh lệnh,
các cạnh trendline bot đã vẽ, mức vào/SL/TP/mục tiêu và điểm thoát. Thời gian trả về là Unix giây UTC."""
from __future__ import annotations

import json
from dataclasses import dataclass

import pandas as pd

from core.timeframes import tf_delta
from data.candles import resample
from journal.db import Journal
from web.services.levels import target_of
from web.services.live_chart import chart_tf
from web.services.mt5_gateway import MT5Gateway
from web.services.signal_chart import AFTER, BASE_TF, base_frame


@dataclass(frozen=True)
class Window:
    pad_bars: int    # nến trước điểm đầu mẫu hình và sau điểm thoát
    max_bars: int    # trần số nến trả về


def _json(value) -> dict | list | None:
    if isinstance(value, str) and value:
        return json.loads(value)
    return value or None


def _edges(journal: Journal, row: dict, meta: dict) -> list:
    """Cạnh mẫu hình: trong meta của chính lệnh; lệnh backtest bỏ cạnh khỏi meta nên lấy từ tín hiệu cùng setup_key."""
    if meta.get("edges"):
        return meta["edges"]
    if not row.get("setup_key"):
        return []
    found = journal.rows("SELECT meta FROM signals WHERE setup_key = ? AND run_id IS ? AND meta IS NOT NULL "
                         "ORDER BY id DESC LIMIT 1", [row["setup_key"], row.get("run_id")])
    return (_json(found[0]["meta"]) or {}).get("edges", []) if found else []


def _ts(value) -> int | None:
    return None if value is None or value == "" else int(pd.Timestamp(value).timestamp())


def _trade(journal: Journal, key: int) -> dict | None:
    rows = journal.rows("SELECT * FROM trades WHERE id = ?", [key])
    if not rows:
        return None
    t = rows[0]
    return {"row": t, "direction": 1 if t["direction"] == "BUY" else -1, "entry_time": t["entry_time"],
            "entry": t["entry"], "sl": t["sl"], "sl_now": None, "tp": t.get("tp1"), "exit_time": t.get("exit_time"),
            "exit_price": None, "r": t.get("r_multiple"), "open": False}


def _leg(journal: Journal, key: int, broker: dict | None) -> dict | None:
    rows = journal.rows("SELECT * FROM live_legs WHERE ticket = ?", [key])
    if not rows:
        return None
    leg = rows[0]
    is_open = leg.get("status") == "open"
    return {"row": leg, "direction": int(leg["direction"]), "entry_time": leg["opened_at"],
            "entry": float(broker["price_open"]) if broker else leg["entry"], "sl": leg.get("initial_sl") or leg["sl"],
            "sl_now": float(broker["sl"]) if broker and broker.get("sl") else leg["sl"],
            "tp": leg.get("tp") or None, "exit_time": None if is_open else leg.get("exit_time"),
            "exit_price": None if is_open else leg.get("exit_price"), "r": None, "open": is_open}


def _signal(journal: Journal, key: int) -> dict | None:
    rows = journal.rows("SELECT * FROM signals WHERE id = ?", [key])
    if not rows:
        return None
    s = rows[0]
    return {"row": s, "direction": 1 if s["direction"] == "BUY" else -1, "entry_time": s["time"], "entry": s.get("entry"),
            "sl": s.get("sl"), "sl_now": None, "tp": s.get("tp1"), "exit_time": None, "exit_price": None, "r": None,
            "open": False}


def load_item(journal: Journal, kind: str, key: int, broker: dict | None) -> dict | None:
    """Lệnh đã đóng (trade), lệnh live (leg) hoặc tín hiệu (signal) dưới dạng chung; None nếu không có."""
    if kind == "trade":
        return _trade(journal, key)
    if kind == "leg":
        return _leg(journal, key, broker)
    if kind == "signal":
        return _signal(journal, key)
    raise ValueError(f"Loại không hợp lệ: {kind}")


def _frame(cfg: dict, gateway: MT5Gateway, tf: str, start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame | None:
    base = base_frame(cfg, gateway, start, end)
    if base is None or base.empty:
        return None
    return base if tf == BASE_TF else resample(base, tf)


def _clip(frame: pd.DataFrame, entry: pd.Timestamp, window: Window, prefer_recent: bool) -> pd.DataFrame:
    if len(frame) <= window.max_bars:
        return frame
    if prefer_recent:
        return frame.iloc[-window.max_bars:]
    i_entry = int(frame["time"].searchsorted(entry))
    i0 = max(0, min(i_entry - window.max_bars // 2, len(frame) - window.max_bars))
    return frame.iloc[i0:i0 + window.max_bars]


def chart_payload(journal: Journal, item: dict, cfg: dict, gateway: MT5Gateway, window: Window,
                  now: pd.Timestamp) -> dict | None:
    """Nến + hình học bot cho chart vẽ tay; None nếu không có dữ liệu nến."""
    row = item["row"]
    meta = _json(row.get("meta")) or {}
    tf = chart_tf(meta, row)
    edges = _edges(journal, row, meta)
    entry_time = pd.Timestamp(item["entry_time"])
    starts = [pd.Timestamp(e[0]) for e in edges] + [entry_time]
    step = tf_delta(tf)
    end_at = pd.Timestamp(item["exit_time"]) if item["exit_time"] else (now if item["open"] else entry_time + AFTER)
    frame = _frame(cfg, gateway, tf, min(starts) - step * window.pad_bars, min(now, end_at + step * window.pad_bars))
    if frame is None or frame.empty:
        return None
    frame = _clip(frame.reset_index(drop=True), entry_time, window, item["open"])
    candles = [{"time": int(t.timestamp()), "open": o, "high": h, "low": lo, "close": c}
               for t, o, h, lo, c in frame[["time", "open", "high", "low", "close"]].itertuples(index=False)]
    return {
        "tf": tf, "candles": candles, "direction": item["direction"], "open": item["open"],
        "entry_time": _ts(entry_time), "entry": item["entry"], "sl": item["sl"], "sl_now": item["sl_now"],
        "tp": item["tp"], "target": target_of(meta, row.get("reasons")), "exit_time": _ts(item["exit_time"]),
        "exit_price": item["exit_price"], "r": item["r"],
        "edges": [[_ts(t1), p1, _ts(t2), p2] for t1, p1, t2, p2 in edges],
        "breakout_time": _ts(meta.get("breakout_time")),
    }


def snapshot(item: dict, kind: str) -> dict:
    """Tóm tắt lệnh lưu kèm nhận xét (để đọc lại/thống kê kể cả khi journal bot đã lưu trữ)."""
    row = item["row"]
    meta = _json(row.get("meta")) or {}
    return {"kind": kind, "setup": row.get("setup"), "setup_key": row.get("setup_key"), "tf": meta.get("tf"),
            "direction": "BUY" if item["direction"] > 0 else "SELL", "entry_time": item["entry_time"],
            "entry": item["entry"], "sl": item["sl"], "tp": item["tp"], "exit_time": item["exit_time"],
            "r": item["r"], "exit_reason": row.get("exit_reason"), "reasons": _json(row.get("reasons")),
            "context": (meta.get("context") or {}).get("lines")}
