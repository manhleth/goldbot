"""Giới hạn danh mục khi mô phỏng: số lệnh cùng lúc, số lệnh mỗi ngày giao dịch, khối lượng theo % equity (lãi kép)."""
from __future__ import annotations

from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass

from playbook.orders import Order
from playbook.simulator import OrderSimulator, Outcome
from risk.management import trading_date
from risk.sizing import SymbolSpec


@dataclass(frozen=True)
class Limits:
    max_positions: int
    max_per_day: int | None = None     # số lệnh KHỚP tối đa mỗi ngày giao dịch (None = không giới hạn)
    risk_pct: float | None = None      # % equity rủi ro mỗi lệnh; None = số tiền cố định của simulator
    initial_equity: float = 1000.0

    @classmethod
    def from_params(cls, p: Mapping) -> "Limits":
        return cls(p["max_positions"], p.get("max_per_day"), p.get("risk_pct"), p["initial_equity"])


def _money(outcome: Outcome, spec: SymbolSpec) -> float:
    return spec.money(outcome.price_pnl(), 1.0)


def simulate(orders: list[Order], sim: OrderSimulator, limits: Limits, spec: SymbolSpec,
             sessions_cfg: Mapping) -> list[Outcome]:
    """Theo thứ tự thời gian: bỏ lệnh khi đã đủ lệnh chờ + vị thế, hoặc đủ số lệnh trong ngày giao dịch."""
    busy: list[Outcome] = []
    filled: list[Outcome] = []
    per_day: Counter = Counter()
    outcomes: list[Outcome] = []
    for order in sorted(orders, key=lambda o: o.time):
        start = sim.start_time(order)
        if start is None:
            continue
        busy = [o for o in busy if o.end is not None and o.end > start]
        day = trading_date(start, sessions_cfg)
        if len(busy) >= limits.max_positions:
            outcomes.append(Outcome(order, "skipped", "max_open_trades"))
            continue
        if limits.max_per_day is not None and per_day[day] >= limits.max_per_day:
            outcomes.append(Outcome(order, "skipped", "max_trades_per_day"))
            continue
        risk_money = None
        if limits.risk_pct is not None:
            equity = limits.initial_equity + sum(_money(o, spec) for o in filled if o.end <= start)
            risk_money = max(equity, 0.0) * limits.risk_pct / 100
        outcome = sim.run(order, risk_money)
        outcomes.append(outcome)
        if outcome.status == "filled":
            per_day[day] += 1
            filled.append(outcome)
        if outcome.start is not None and outcome.end is not None and outcome.end > outcome.start:
            busy.append(outcome)
    return outcomes
