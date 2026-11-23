"""Bộ lọc hướng từ nhận định của channel (bảng `calls` trong feeds db): chỉ dùng HƯỚNG, không dùng mục tiêu.

Tại thời điểm lệnh t: hướng = nhận định (up/down) gần nhất của `symbol` đăng trước t và còn trong `valid_days`.
- mode `strict`: chỉ giữ lệnh cùng hướng; không có nhận định còn hiệu lực → bỏ (`no_channel_bias`).
- mode `block_against`: chỉ bỏ lệnh ngược hướng (`against_channel_bias`).
"""
from __future__ import annotations

import pandas as pd

from feeds.store import FeedStore
from playbook.orders import Order
from playbook.simulator import Outcome

MODES = ("strict", "block_against")


def load_bias(db: str, channel: str, symbol: str) -> pd.DataFrame:
    with FeedStore(db) as store:
        calls = store.calls(channel)
    calls = calls[(calls.is_analysis == 1) & (calls.symbol == symbol) & calls.direction.isin(["up", "down"])]
    out = pd.DataFrame({"time": pd.to_datetime(calls["time"], utc=True),
                        "bias": calls["direction"].map({"up": 1, "down": -1})})
    return out.sort_values("time").reset_index(drop=True)


def apply_bias(orders: list[Order], bias: pd.DataFrame, valid_days: int, mode: str) -> tuple[list[Order], list[Outcome]]:
    if mode not in MODES:
        raise ValueError(f"bias mode phải là một trong {MODES}")
    kept: list[Order] = []
    rejected: list[Outcome] = []
    times = bias["time"]
    for order in orders:
        i = int(times.searchsorted(order.time, side="left")) - 1  # nhận định đăng TRƯỚC lúc lệnh
        active = i >= 0 and order.time - times.iat[i] <= pd.Timedelta(days=valid_days)
        if not active:
            (kept.append(order) if mode == "block_against" else rejected.append(Outcome(order, "skipped", "no_channel_bias")))
            continue
        if int(bias["bias"].iat[i]) == int(order.direction):
            kept.append(order)
        else:
            rejected.append(Outcome(order, "skipped", "against_channel_bias"))
    return kept, rejected
