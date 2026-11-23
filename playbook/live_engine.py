"""Bộ máy quyết định live cho một phương pháp sổ tay (không đụng MT5) — dùng đúng code của backtest.

Mỗi chu kỳ: dữ liệu khung gốc đã đóng → tín hiệu mới (chỉ quét nến mới) → lọc hướng channel → lớp học kinh nghiệm
(kết quả nháp trên lịch sử, làm mới định kỳ) → danh sách lệnh đề xuất kèm lý do từ chối. Mức dời SL theo cấu trúc
tính từ cùng chuỗi swing như backtest.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from core.types import Direction
from playbook.bias import apply_bias, load_bias
from playbook.common import MarketData
from playbook.learning import Experience, gate, paper_trade
from playbook.orders import Order
from playbook.runner import METHODS, apply_variant, build_market, build_trail, trail_tfs
from playbook.simulator import Bars, OrderSimulator, Outcome
from risk.sizing import SymbolSpec


@dataclass(frozen=True)
class Decision:
    order: Order
    reject: str | None  # None = được vào lệnh


class OneEngine:
    def __init__(self, cfg: dict, pb: dict, method: str, variant: str, spec: SymbolSpec) -> None:
        self._cfg = cfg
        self.p = {**pb["common"], **pb["methods"][method], "code": method}
        self.variant_name = variant
        self.variant = pb["variants"][variant]
        self._fn = METHODS[self.p.get("fn", method)]
        self._spec = spec
        self._experience: Experience | None = None
        self.experience_at: pd.Timestamp | None = None

    # ---------- dữ liệu ----------
    def market(self, base: pd.DataFrame, base_tf: str, now: pd.Timestamp) -> tuple[MarketData, Bars]:
        return build_market(base, base_tf, self._cfg, self._spec, now)

    def _signals(self, data: MarketData, since: pd.Timestamp | None) -> list[Order]:
        p = dict(self.p)
        if since is not None:
            p["scan_since"] = since
            if "patterns" in p:
                p["patterns"] = {**p["patterns"], "scan_since": since}
        orders = self._fn(data, p).orders
        return apply_variant(orders, self.variant, self.variant_name)

    # ---------- kinh nghiệm ----------
    def refresh_experience(self, data: MarketData, bars: Bars, now: pd.Timestamp) -> dict[str, tuple[int, float]]:
        """Trade nháp mọi tín hiệu trong lịch sử đang có (cùng bộ mô phỏng với backtest)."""
        trails = {f"{self.variant_name}@{tf}": build_trail(data, bars, {**self.variant["trail"], "tf": tf})
                  for tf in trail_tfs(self.variant)} or None
        sim = OrderSimulator(bars, self._spec, self.p["risk_per_trade_money"],
                             self._cfg["backtest"]["slippage_points"], [], trails)
        self._experience = paper_trade(self._signals(data, None), sim)
        self.experience_at = now
        return self._experience.summary()

    def needs_refresh(self, now: pd.Timestamp, hours: float) -> bool:
        return self.experience_at is None or now - self.experience_at >= pd.Timedelta(hours=hours)

    # ---------- quyết định ----------
    def decide(self, data: MarketData, since: pd.Timestamp) -> list[Decision]:
        """Tín hiệu hình thành sau `since`, kèm lý do bị lọc (nếu có)."""
        orders = [o for o in self._signals(data, since) if o.time > since]
        dropped: list[Outcome] = []
        if self.p.get("channel_bias"):
            fb = self._cfg["feeds"]["bias"]
            series = load_bias(self._cfg["feeds"]["db"], fb["channel"], fb["symbol"])
            orders, against = apply_bias(orders, series, self.p["channel_bias"]["valid_days"],
                                         self.p["channel_bias"]["mode"])
            dropped += against
        if self.p.get("learning"):
            if self._experience is None:
                raise RuntimeError("chưa có kinh nghiệm: gọi refresh_experience trước")
            orders, gated = gate(orders, self._experience, self.p["learning"])
            dropped += gated
        return [Decision(o, None) for o in orders] + [Decision(o.order, o.reason) for o in dropped]

    def experience_summary(self) -> dict[str, tuple[int, float]]:
        return self._experience.summary() if self._experience is not None else {}

    # ---------- dời SL ----------
    def trail_level(self, data: MarketData, bars: Bars, tf: str, direction: Direction,
                    entry_time: pd.Timestamp) -> float | None:
        """Mức SL theo swing khung `tf` xác nhận SAU lúc vào lệnh, tại nến gốc mới nhất (như backtest)."""
        if not self.variant.get("trail"):
            return None
        series = build_trail(data, bars, {**self.variant["trail"], "tf": tf})
        fill = bars.index_at(entry_time)
        last = len(bars) - 1
        if last < 0 or series.confirmed_at[direction][last] <= fill:
            return None
        level = float(series.level[direction][last])
        return level if np.isfinite(level) else None

    def stop_distance(self, order: Order, price: float) -> float | None:
        """Khoảng SL khi vào lệnh ở `price` (market): SL tuyệt đối nếu có, nếu không dùng sl_dist."""
        if order.sl is not None:
            dist = (price - order.sl) * int(order.direction)
        else:
            dist = order.sl_dist
        return float(dist) if dist is not None and dist > 0 else None
