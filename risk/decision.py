"""Chuỗi quyết định một tín hiệu: lọc → tin tức → kế hoạch SL/TP → giới hạn rủi ro → khối lượng."""
from __future__ import annotations

from dataclasses import dataclass

from core.types import Rejected, Signal, TradePlan
from mtf.context import MarketContext
from news.calendar import NewsCalendar
from news.filter import alignment, forecast_view, news_reason
from risk.guard import AccountSnapshot, block_reason
from risk.planner import build_plan
from risk.sizing import SymbolSpec, lot_size, risk_budget, split_legs
from signals.filters import filter_reason


@dataclass(frozen=True, slots=True, eq=False)
class Decision:
    plan: TradePlan | None
    legs: tuple[float, ...]
    reason: str | None
    news: str = "none"  # aligned / against / neutral / none — để thống kê hiệu quả bộ lọc tin

    @property
    def accepted(self) -> bool:
        return self.reason is None


def decide(signal: Signal, ctx: MarketContext, entry: float, snapshot: AccountSnapshot, spread_points: float,
           spec: SymbolSpec, cfg: dict, calendar: NewsCalendar, allow_split: bool = True) -> Decision:
    view = forecast_view(signal, calendar, cfg["news"])
    tag = alignment(signal.direction, view)
    reason = filter_reason(signal, cfg) or news_reason(signal, calendar, view, cfg["news"])
    if reason:
        return Decision(None, (), reason, tag)
    plan = build_plan(signal, entry, ctx, cfg)
    if isinstance(plan, Rejected):
        return Decision(None, (), plan.reason, tag)
    reason = block_reason(plan, snapshot, signal.time, spread_points, cfg)
    if reason:
        return Decision(plan, (), reason, tag)
    lot = lot_size(risk_budget(snapshot.equity, cfg["risk"]), plan.risk, spec)
    if lot <= 0:
        return Decision(plan, (), "lot_below_minimum", tag)
    legs = split_legs(lot, cfg["management"]["split_tp1_fraction"], spec) if allow_split else (lot,)
    return Decision(plan, legs, None, tag)
