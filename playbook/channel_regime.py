"""Kênh xu hướng D1 (hồi quy tuyến tính) — bài học năm 2022: vàng giảm trong một kênh D1 rõ ràng (03→11/2022) nhưng
phá mẫu hình H2/H4 theo cả hai chiều đều lỗ (bán đúng đáy kênh rồi bị nhịp hồi quét SL; mua theo nhịp hồi ngược kênh).

Tại mỗi nến D1 đã đóng k: hồi quy giá đóng cửa `period` nến kết thúc ở k-1 → đường giữa; dải kênh = đường giữa + độ lệch
lớn nhất của high/low so với đường giữa trong cửa sổ. Kênh hợp lệ khi R² ≥ `min_r2` và quãng dốc (độ dốc × period)
≥ `min_slope_atr` × ATR D1. Chiều kênh = dấu độ dốc. Nến k đóng cửa vượt ra ngoài dải ngược chiều kênh quá `break_atr`
× ATR → kênh bị phá, đứng ngoài `cooldown` nến. `pos` = vị trí giá đóng cửa trong kênh (0 = đáy, 1 = đỉnh).

Áp vào lệnh (`apply_channel`): kênh đang chạy → bỏ lệnh ngược chiều kênh; lệnh cùng chiều chỉ nhận ở phía "đắt"
(SELL khi pos ≥ `min_pos`, BUY khi pos ≤ 1 − `min_pos`). Lệnh được giữ mang meta `channel` để bộ lọc vĩ mô không chặn.
"""
from __future__ import annotations

import dataclasses

import numpy as np
import pandas as pd

from playbook import indicators as ind
from playbook.common import MarketData
from playbook.orders import Order


def channel_series(df: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    n, period = len(df), cfg["period"]
    h, l, c = (df[col].to_numpy(float) for col in ("high", "low", "close"))
    atr = ind.atr(df, cfg["atr"]).to_numpy(float)
    x = np.arange(period, dtype=float)
    direction = np.zeros(n, dtype=int)
    pos = np.full(n, np.nan)
    blocked_until = -1
    for k in range(period + 1, n):
        s = slice(k - period, k)
        slope, icept = np.polyfit(x, c[s], 1)
        fit = icept + slope * x
        ss = ((c[s] - c[s].mean()) ** 2).sum()
        r2 = 1 - ((c[s] - fit) ** 2).sum() / ss if ss > 0 else 0.0
        up, dn = (h[s] - fit).max(), (l[s] - fit).min()
        mid_k = icept + slope * period
        top, bottom = mid_k + up, mid_k + dn
        d = int(np.sign(slope)) if r2 >= cfg["min_r2"] and abs(slope) * period >= cfg["min_slope_atr"] * atr[k - 1] else 0
        broke = d and ((c[k] - (top if d < 0 else bottom)) * -d > cfg["break_atr"] * atr[k - 1])
        if broke:
            blocked_until = k + cfg["cooldown"]
        if k <= blocked_until:
            d = 0
        direction[k] = d
        pos[k] = (c[k] - bottom) / (top - bottom) if top > bottom else np.nan
    return pd.DataFrame({"close_time": df["close_time"], "dir": direction, "pos": pos})


def apply_channel(orders: list[Order], data: MarketData, cfg: dict) -> list[Order]:
    if not orders:
        return orders
    series = channel_series(data.frame("D1"), cfg)
    times = pd.DataFrame({"close_time": [o.time for o in orders]})
    state = pd.merge_asof(times, series, on="close_time", direction="backward")
    out = []
    for o, d, p in zip(orders, state["dir"].fillna(0).astype(int), state["pos"]):
        if d == 0:
            out.append(o)
            continue
        side = int(o.direction)
        cheap_side = p >= cfg["min_pos"] if d < 0 else p <= 1 - cfg["min_pos"]
        if side != d or not cheap_side:
            continue
        label = f"kênh D1 {'giảm' if d < 0 else 'tăng'}, giá ở {p:.0%} kênh"
        out.append(dataclasses.replace(o, reasons=(*o.reasons, label), meta={**o.meta, "channel": d}))
    return out
