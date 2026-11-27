"""Ảnh hiện tại của lệnh đang mở: nến mới nhất của khung mẫu hình, SL ban đầu/hiện tại, giá hiện tại, R thả nổi."""
from __future__ import annotations

import json

import pandas as pd

from core.timeframes import TF_MINUTES, tf_delta
from data.candles import resample
from playbook import chart_svg
from web.services.mt5_gateway import MT5Gateway
from web.services.signal_chart import BASE_TF, base_frame

PATTERN_PAD_BARS = 20  # nến trước điểm đầu mẫu hình


def chart_tf(meta: dict, leg: dict) -> str:
    """Khung vẽ = khung mẫu hình; khung nhỏ hơn nến gốc lấy được (M15) thì vẽ bằng M15."""
    tf = meta.get("tf") or leg.get("trail") or "H1"
    return tf if tf in TF_MINUTES and TF_MINUTES[tf] >= TF_MINUTES[BASE_TF] else BASE_TF


def render_leg_now(leg: dict, broker: dict | None, cfg: dict, gateway: MT5Gateway, now: pd.Timestamp) -> str | None:
    """SVG trạng thái hiện tại của lệnh; None nếu thiếu dữ liệu nến. `broker` = vị thế trên MT5 (giá/SL thực tế)."""
    meta = json.loads(leg["meta"]) if isinstance(leg.get("meta"), str) else (leg.get("meta") or {})
    tf = chart_tf(meta, leg)
    opened = pd.Timestamp(leg["opened_at"])
    starts = [pd.Timestamp(e[0]) for e in meta.get("edges", [])] + [opened]
    base = base_frame(cfg, gateway, min(starts) - tf_delta(tf) * PATTERN_PAD_BARS, now)
    if base is None or base.empty:
        return None
    frame = base if tf == BASE_TF else resample(base, tf)  # nến cuối = nến đang chạy
    d = int(leg["direction"])
    entry = float(broker["price_open"]) if broker else float(leg["entry"])
    price = float(broker["price_current"]) if broker else float(frame["close"].iat[-1])
    initial_sl = float(leg.get("initial_sl") or leg["sl"])
    current_sl = float(broker["sl"]) if broker and broker.get("sl") else float(leg["sl"])
    risk = abs(entry - initial_sl)
    r = (price - entry) * d / risk if risk > 0 else 0.0
    reasons = json.loads(leg["reasons"]) if isinstance(leg.get("reasons"), str) else (leg.get("reasons") or [])
    view = chart_svg.TradeView(d, opened, entry, initial_sl, now, price, r,
                               f"HIỆN TẠI · {leg.get('setup_key') or ''} · {tf}", tuple(reasons), meta,
                               current_sl=current_sl, live=True)
    return chart_svg.render(frame, view)
