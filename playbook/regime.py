"""Thoát lệnh theo trạng thái thị trường lúc vào lệnh (đo trên nến đã đóng của khung `adx.tf`).

- Xu hướng (ADX ≥ `threshold`, có thể làm mượt `smooth` nến): gồng theo đỉnh/đáy khung `trend.trail_tf` (vd D1) —
  lệnh có thể giữ hàng tuần/tháng nếu xu hướng còn.
- Đi ngang (ADX < ngưỡng): chốt sớm ở `sideways.tp_r` × rủi ro; `max_hold_days` (tuỳ chọn) đóng nếu giữ quá lâu.
Mỗi mục null = giữ nguyên cách quản lý mặc định cho trạng thái đó.
"""
from __future__ import annotations

import dataclasses

import pandas as pd

from playbook.common import MarketData
from playbook.orders import Order
from structure.indicators import adx


def regime_series(data: MarketData, cfg: dict) -> pd.DataFrame:
    """ADX theo từng nến đã đóng của khung `tf`: cột close_time, adx."""
    df = data.frame(cfg["tf"])
    value = adx(df, cfg["period"])
    if cfg.get("smooth"):
        value = value.rolling(cfg["smooth"]).mean()
    return pd.DataFrame({"close_time": df["close_time"], "adx": value.to_numpy()})


def apply_regime_exit(orders: list[Order], data: MarketData, cfg: dict) -> list[Order]:
    if not orders:
        return orders
    series = regime_series(data, cfg["adx"])
    times = pd.DataFrame({"close_time": [o.time for o in orders]})
    values = pd.merge_asof(times, series, on="close_time", direction="backward")["adx"].to_numpy()
    out = []
    for o, value in zip(orders, values):
        if pd.isna(value) or o.sl_dist is None:
            out.append(o)
            continue
        trending = value >= cfg["adx"]["threshold"]
        rule = cfg.get("trend") if trending else cfg.get("sideways")
        label = f"{'xu hướng' if trending else 'đi ngang'} (ADX {cfg['adx']['tf']} {value:.0f})"
        meta = {**o.meta, "regime": "trend" if trending else "sideways"}
        changes: dict = {"reasons": (*o.reasons, label)}
        if rule and trending and rule.get("trail_tf"):
            meta["trail_tf"] = rule["trail_tf"]
        elif rule and not trending:
            meta["keep_tp"] = True
            changes.update(tp=None, tp_dist=rule["tp_r"] * o.sl_dist)
            if rule.get("max_hold_days"):
                changes["max_hold"] = pd.Timedelta(days=rule["max_hold_days"])
        out.append(dataclasses.replace(o, meta=meta, **changes))
    return out
