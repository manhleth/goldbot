"""Phương pháp hợp nhất: phá cấu trúc theo xu hướng H4, gồng theo đỉnh/đáy H4, có học kinh nghiệm.

Nguồn kiến thức: XAU-02 (lọc xu hướng EMA50/EMA200 H4), XAU-05 (phá hộp phiên Á), mẫu hình trendline dạng vùng
(docs/knowledge/chart-patterns.md, docs/knowledge/mj-capital.md: cờ, tam giác, kênh, neckline).
- `triggers`: các loại điểm vào được bật (`patterns`, `asia_box`).
- `trend_filter`: chỉ BUY khi close và EMA nhanh > EMA chậm trên `trend_tf`; SELL ngược lại (false = không lọc).
- `intraday` (tuỳ chọn): không vào lệnh từ `last_entry` tới đầu ngày giao dịch mới; mọi lệnh đóng lúc `flat`
  (giờ theo `sessions.timezone`, New York) của ngày giao dịch đó.
Mọi lệnh mang khoá `<code>:<loại>@<khung>:...` để lớp học kinh nghiệm chấm điểm theo loại.
"""
from __future__ import annotations

import dataclasses

import numpy as np
import pandas as pd

from core.types import Direction
from playbook import indicators as ind
from playbook.common import MarketData
from playbook.methods_box import xau05
from playbook.orders import Order, Signals
from playbook.patterns import patterns
from risk.calendar import minutes


def _trend(data: MarketData, tf: str, fast: int, slow: int) -> pd.DataFrame:
    df = data.frame(tf)
    c = df["close"]
    f, s = ind.ema(c, fast), ind.ema(c, slow)
    trend = np.where((c > s) & (f > s), 1, np.where((c < s) & (f < s), -1, 0))
    trend = np.where(np.arange(len(df)) >= slow, trend, 0)
    return pd.DataFrame({"close_time": df["close_time"], "trend": trend})


def _aligned(orders: list[Order], trend: pd.DataFrame) -> list[Order]:
    if not orders:
        return orders
    times = pd.DataFrame({"close_time": [o.time for o in orders]})
    state = pd.merge_asof(times, trend, on="close_time", direction="backward")["trend"].fillna(0).to_numpy()
    return [o for o, t in zip(orders, state) if t == int(o.direction)]


def _rekey(orders: list[Order], code: str, kind: str) -> list[Order]:
    return [dataclasses.replace(o, key=f"{code}:{kind}:{o.time:%Y%m%d%H%M}:{o.direction.name}") for o in orders]


def _intraday(orders: list[Order], tz: str, rules: dict) -> list[Order]:
    """Lệnh trong ngày: bỏ lệnh từ `last_entry` tới `day_start` (giờ địa phương), đặt giờ đóng = `flat` cùng ngày."""
    out = []
    last, flat, day_start = (minutes(rules[k]) for k in ("last_entry", "flat", "day_start"))
    for o in orders:
        local = o.time.tz_convert(tz)
        m = local.hour * 60 + local.minute
        if last <= m < day_start:
            continue
        day = local.normalize() + (pd.Timedelta(days=1) if m >= day_start else pd.Timedelta(0))
        exit_at = (day + pd.Timedelta(minutes=flat)).tz_convert("UTC")
        out.append(dataclasses.replace(o, exit_at=exit_at))
    return out


def unified(data: MarketData, p: dict) -> Signals:
    orders: list[Order] = []
    if "patterns" in p["triggers"]:
        found = patterns(data, {**p["patterns"], "code": p["code"]}).orders
        allowed = {f"{k}@{tf}" for k in p["patterns"]["kinds"] for tf in p["patterns"]["timeframes"]}
        orders += [o for o in found if o.key.split(":")[1] in allowed]
    if "asia_box" in p["triggers"]:
        orders += _rekey(xau05(data, p["asia_box"]).orders, p["code"], "asia_box@M5")
    orders.sort(key=lambda o: o.time)
    if p["trend_filter"]:
        tf = p["trend_filter"]
        orders = _aligned(orders, _trend(data, tf["tf"], tf["fast"], tf["slow"]))
    if p.get("intraday"):
        orders = _intraday(orders, data.timezone, p["intraday"])
    return Signals(orders, [])
