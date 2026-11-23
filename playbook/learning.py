"""Rút kinh nghiệm từ kết quả: mọi tín hiệu được trade nháp; chỉ vào lệnh thật với loại tín hiệu có thành tích gần đây dương.

Loại tín hiệu = phần thứ hai của khoá lệnh (vd `flag@H4`). Tại thời điểm tín hiệu t, bot chỉ dùng kết quả nháp đã đóng
trước t (không nhìn trước): chưa đủ `min_trades` → `learning_insufficient`; trung bình R của `window` kết quả gần nhất
≤ `min_expectancy` → `learning_negative`. Tất định, giải thích được, ghi lý do vào journal.
"""
from __future__ import annotations

from bisect import bisect_right
from collections import defaultdict
from dataclasses import dataclass

import numpy as np
import pandas as pd

from playbook.orders import Order
from playbook.simulator import OrderSimulator, Outcome


def lesson_class(order: Order) -> str:
    return order.key.split(":")[1]


@dataclass(frozen=True)
class Experience:
    """Kết quả nháp theo loại tín hiệu, sắp theo giờ đóng lệnh."""
    ends: dict[str, list[pd.Timestamp]]
    results: dict[str, list[float]]

    def before(self, cls: str, t: pd.Timestamp) -> list[float]:
        return self.results.get(cls, [])[: bisect_right(self.ends.get(cls, []), t)]

    def summary(self) -> dict[str, tuple[int, float]]:
        return {cls: (len(r), float(np.mean(r))) for cls, r in sorted(self.results.items()) if r}


def paper_trade(orders: list[Order], sim: OrderSimulator) -> Experience:
    rows: dict[str, list[tuple[pd.Timestamp, float]]] = defaultdict(list)
    for order in orders:
        out = sim.run(order)
        if out.status == "filled":
            rows[lesson_class(order)].append((out.end, out.r_multiple()))
    ends, results = {}, {}
    for cls, items in rows.items():
        items.sort(key=lambda x: x[0])
        ends[cls] = [e for e, _ in items]
        results[cls] = [r for _, r in items]
    return Experience(ends, results)


def gate(candidates: list[Order], experience: Experience, lc: dict) -> tuple[list[Order], list[Outcome]]:
    accepted: list[Order] = []
    rejected: list[Outcome] = []
    for order in candidates:
        past = experience.before(lesson_class(order), order.time)
        if len(past) < lc["min_trades"]:
            rejected.append(Outcome(order, "skipped", "learning_insufficient"))
        elif float(np.mean(past[-lc["window"]:])) <= lc["min_expectancy"]:
            rejected.append(Outcome(order, "skipped", "learning_negative"))
        else:
            accepted.append(order)
    return accepted, rejected
