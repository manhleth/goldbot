"""Chart lý do cho một tín hiệu (kể cả tín hiệu bị bỏ): vẽ theo yêu cầu từ nến M15 gộp lên khung mẫu hình (giờ UTC)."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from data.candles import resample
from data.history import cache_path, load_csv
from data.mt5_source import MT5Source
from playbook import chart_svg
from web.services.mt5_gateway import MT5Gateway

BASE_TF = "M15"
LOOKBACK = pd.Timedelta(days=45)   # đủ cho cửa sổ mẫu hình H4 (80 nến ≈ 13 ngày giao dịch) + lề
AFTER = pd.Timedelta(days=3)


def base_frame(cfg: dict, gateway: MT5Gateway, start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame | None:
    """Nến M15 trong khoảng [start, end]: ưu tiên MT5, không có thì cache (lịch sử dài + cache thường)."""
    def fetch(mt5) -> pd.DataFrame:
        return MT5Source(mt5, cfg["symbol"], cfg["data"]["server_time"]).fetch_range(
            BASE_TF, start, end, cfg["data"]["fetch_chunk_bars"])
    df = gateway.call(fetch)
    if df is None or df.empty:
        cache = Path(cfg["data"]["cache_dir"])
        parts = [load_csv(p, BASE_TF) for p in (cache / f"{cfg['symbol']}_{BASE_TF}_long.csv",
                                                 cache_path(cache, cfg["symbol"], BASE_TF)) if p.exists()]
        if not parts:
            return None
        df = pd.concat(parts).drop_duplicates("time", keep="last").sort_values("time")
    return df[(df["time"] >= start) & (df["time"] <= end)].reset_index(drop=True)


def render_signal(signal: dict, cfg: dict, gateway: MT5Gateway, title: str) -> str | None:
    """SVG cho tín hiệu có hình học mẫu hình (meta); None nếu tín hiệu cũ chưa lưu meta hoặc thiếu dữ liệu nến."""
    meta = json.loads(signal["meta"]) if signal.get("meta") else None
    if not meta or not meta.get("tf"):
        return None
    when = pd.Timestamp(signal["time"])
    base = base_frame(cfg, gateway, when - LOOKBACK, when + AFTER)
    if base is None or base.empty:
        return None
    frame = base if meta["tf"] == BASE_TF else resample(base, meta["tf"])
    frame = frame[frame["close_time"] <= when + AFTER].reset_index(drop=True)
    d = 1 if signal["direction"] == "BUY" else -1
    at = frame[frame["close_time"] <= when]
    if at.empty:
        return None
    entry = float(at["close"].iat[-1])  # giá đóng cửa nến phá (lệnh market vào ngay sau đó)
    sl = entry - d * meta["sl_dist"] if meta.get("sl_dist") else entry
    reasons = json.loads(signal["reasons"]) if isinstance(signal.get("reasons"), str) else signal.get("reasons") or []
    view = chart_svg.TradeView(d, when, entry, sl, when, entry, 0.0, title, tuple(reasons), meta)
    return chart_svg.render(frame, view)
