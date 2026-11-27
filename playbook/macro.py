"""Trạng thái vĩ mô theo cú phá mẫu hình DÀI HẠN (W1, D1): sau khi một vùng tích lũy/xu hướng lâu dài bị phá, thị
trường thường đi một chiều rất lâu (vd vàng phá tam giác W1 2020–2024 tháng 3/2024 rồi tăng gần như liên tục).

Mỗi khung trong `frames` (W1 gộp từ D1 bằng playbook/sr_zones.weekly; D1 lấy từ MarketData):
- quét mẫu hình bằng playbook/patterns.scan_all với `patterns`;
- chỉ nhận cú phá của mẫu hình kéo dài ≥ `min_span` nến (tính từ điểm neo đầu tiên, áp dụng cho mọi loại kể cả neckline);
- xác nhận: `confirm_bars` nến kế tiếp đều đóng cửa ngoài cạnh vừa phá; trạng thái đổi lúc nến xác nhận cuối đóng.
Trạng thái = chiều của cú phá dài hạn đã xác nhận gần nhất (khung nào cũng được), giữ tới cú phá ngược chiều; trước đó = 0.
- `mode`: block_against = bỏ lệnh ngược trạng thái (trạng thái 0 không chặn); `risk_with` / `risk_neutral` (tuỳ chọn):
  hệ số rủi ro cho lệnh cùng chiều trạng thái / khi chưa có trạng thái.
"""
from __future__ import annotations

import dataclasses

import pandas as pd

from playbook.common import MarketData
from playbook.orders import Order
from playbook.patterns import Edge, Signal, scan_all
from playbook.sr_zones import weekly


def _daily(data: MarketData) -> pd.DataFrame:
    """D1 gộp từ khung gốc, nối thêm phần cũ hơn từ lịch sử D1 dài (`D1_long`) nếu có."""
    d1 = data.frame("D1")
    long = data.frames.get("D1_long")
    if long is None or long.empty:
        return d1
    older = long[long["time"] < d1["time"].iat[0]] if len(d1) else long
    return pd.concat([older, d1], ignore_index=True)


def _frame(data: MarketData, tf: str) -> pd.DataFrame:
    if tf == "W1":
        return weekly(_daily(data))
    return _daily(data) if tf == "D1" else data.frame(tf)


def _broken_edge(sig: Signal) -> Edge:
    if len(sig.edges) == 1:
        return sig.edges[0]
    upper, lower = sig.edges
    return upper if int(sig.direction) > 0 else lower


def confirmed_breaks(df: pd.DataFrame, fc: dict) -> list[tuple[pd.Timestamp, int, str]]:
    """(thời điểm xác nhận, chiều, mô tả) cho các cú phá mẫu hình dài ≥ min_span nến, giữ được confirm_bars nến."""
    close = df["close"].to_numpy(float)
    out = []
    for sig in scan_all(df, fc["patterns"], fc["swing"]):
        if sig.kind.endswith("_bounce") or not sig.edges:
            continue
        span = sig.k - min(e.i1 for e in sig.edges)
        last = sig.k + fc["confirm_bars"]
        if span < fc["min_span"] or last >= len(df):
            continue
        d, edge = int(sig.direction), _broken_edge(sig)
        if all((close[j] - edge.value(j)) * d > 0 for j in range(sig.k + 1, last + 1)):
            out.append((df["close_time"].iat[last], d, f"{sig.kind} {span} nến"))
    return out


def macro_series(data: MarketData, cfg: dict) -> pd.DataFrame:
    """Các mốc đổi trạng thái: close_time, state (+1/−1), khung, mô tả mẫu hình."""
    events = sorted((t, d, tf, what) for tf, fc in cfg["frames"].items()
                    for t, d, what in confirmed_breaks(_frame(data, tf), fc))
    rows, state = [], 0
    for t, d, tf, what in events:
        if d != state:
            state = d
            rows.append((t, d, tf, what))
    return pd.DataFrame(rows, columns=["close_time", "state", "tf", "pattern"])


def apply_macro(orders: list[Order], series: pd.DataFrame, cfg: dict) -> list[Order]:
    if not orders or series.empty:
        return orders
    times = pd.DataFrame({"close_time": [o.time for o in orders]})
    states = pd.merge_asof(times, series[["close_time", "state"]], on="close_time",
                           direction="backward")["state"].fillna(0).astype(int)
    out = []
    for o, state in zip(orders, states):
        d = int(o.direction)
        if cfg.get("mode") == "block_against" and state and d != state and not o.meta.get("channel"):  # kênh D1 ưu tiên
            continue
        scale = cfg.get("risk_with") if state == d else (cfg.get("risk_neutral") if state == 0 else None)
        label = f"vĩ mô {'tăng' if state > 0 else 'giảm' if state < 0 else 'chưa rõ'}"
        changes: dict = {"reasons": (*o.reasons, label), "meta": {**o.meta, "macro": state}}
        if scale:
            changes["risk_scale"] = o.risk_scale * scale
        out.append(dataclasses.replace(o, **changes))
    return out
