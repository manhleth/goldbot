"""Mô phỏng khớp lệnh trên nến khung vào lệnh.

Quy ước giá: nến là giá bid. BUY thoát theo bid, SELL thoát theo ask (= bid + spread).
Bảo thủ: nếu SL và TP cùng nằm trong một nến thì tính SL trước; nến mở gap qua SL thì khớp ở giá mở.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from core.types import Direction, TradePlan
from mtf.view import TimeframeView
from risk.management import breakeven_due, breaks_invalidation, improves, trail_stop
from risk.sizing import SymbolSpec

TP1_LEG, RUNNER_LEG, SINGLE_LEG = "tp1", "runner", "single"


@dataclass
class Leg:
    name: str
    volume: float
    tp: float | None
    sl: float
    sl_kind: str = "sl"
    exit_price: float | None = None
    exit_time: pd.Timestamp | None = None
    exit_reason: str | None = None

    @property
    def is_open(self) -> bool:
        return self.exit_price is None

    def close(self, price: float, time: pd.Timestamp, reason: str) -> None:
        self.exit_price, self.exit_time, self.exit_reason = price, time, reason


@dataclass
class SimPosition:
    plan: TradePlan
    entry_time: pd.Timestamp
    spread_entry: float
    legs: list[Leg]
    mae: float = 0.0  # khoảng giá bất lợi lớn nhất
    mfe: float = 0.0  # khoảng giá thuận lợi lớn nhất
    tp1_done: bool = False
    news: str = "none"

    @property
    def direction(self) -> Direction:
        return self.plan.signal.direction

    @property
    def open_legs(self) -> list[Leg]:
        return [leg for leg in self.legs if leg.is_open]

    @property
    def is_open(self) -> bool:
        return any(leg.is_open for leg in self.legs)

    @property
    def volume(self) -> float:
        return sum(leg.volume for leg in self.legs)

    @property
    def exit_time(self) -> pd.Timestamp:
        return max(leg.exit_time for leg in self.legs)

    @property
    def exit_reason(self) -> str:
        return "+".join(f"{leg.name}:{leg.exit_reason}" for leg in self.legs)

    def price_pnl(self, mark: float | None = None) -> float:
        """Lãi/lỗ theo đơn vị giá × lot; chân còn mở được định giá ở `mark`."""
        total = 0.0
        for leg in self.legs:
            price = leg.exit_price if leg.exit_price is not None else mark
            if price is not None:
                total += leg.volume * (price - self.plan.entry) * self.direction
        return total

    def r_multiple(self) -> float:
        return self.price_pnl() / (self.volume * self.plan.risk)


@dataclass
class Simulator:
    spec: SymbolSpec
    slippage_points: float
    management: dict
    open_positions: list[SimPosition] = field(default_factory=list)

    @property
    def _slip(self) -> float:
        return self.slippage_points * self.spec.point

    def _exit_shift(self, direction: Direction, spread_points: float) -> float:
        return 0.0 if direction == Direction.BUY else spread_points * self.spec.point

    def open(self, plan: TradePlan, volumes: tuple[float, ...], time: pd.Timestamp, spread_points: float,
             news: str = "none") -> SimPosition:
        if len(volumes) == 2:
            legs = [Leg(TP1_LEG, volumes[0], plan.tp1, plan.sl), Leg(RUNNER_LEG, volumes[1], plan.tp2, plan.sl)]
        else:
            legs = [Leg(SINGLE_LEG, volumes[0], plan.tp1, plan.sl)]
        position = SimPosition(plan, time, spread_points, legs, news=news)
        self.open_positions.append(position)
        return position

    def _prune(self) -> list[SimPosition]:
        closed = [p for p in self.open_positions if not p.is_open]
        self.open_positions = [p for p in self.open_positions if p.is_open]
        return closed

    def on_bar(self, o: float, h: float, l: float, t: pd.Timestamp, spread_points: float) -> list[SimPosition]:
        for position in self.open_positions:
            self._step(position, o, h, l, t, spread_points)
        return self._prune()

    def _step(self, pos: SimPosition, o: float, h: float, l: float, t: pd.Timestamp, spread_points: float) -> None:
        d = pos.direction
        shift = self._exit_shift(d, spread_points)
        op, hi, lo = o + shift, h + shift, l + shift
        entry = pos.plan.entry
        pos.mfe = max(pos.mfe, (hi - entry) if d == Direction.BUY else (entry - lo))
        pos.mae = max(pos.mae, (entry - lo) if d == Direction.BUY else (hi - entry))
        tp1_filled = False
        for leg in pos.open_legs:
            if (lo <= leg.sl) if d == Direction.BUY else (hi >= leg.sl):
                gapped = (op <= leg.sl) if d == Direction.BUY else (op >= leg.sl)
                leg.close((op if gapped else leg.sl) - d * self._slip, t, leg.sl_kind)
            elif leg.tp is not None and ((hi >= leg.tp) if d == Direction.BUY else (lo <= leg.tp)):
                leg.close(leg.tp, t, "tp2" if leg.name == RUNNER_LEG else "tp1")
                tp1_filled |= leg.name == TP1_LEG
        if tp1_filled:
            pos.tp1_done = True
        reached_r = breakeven_due(pos.mfe, pos.plan.risk, self.management["breakeven_at_r"])
        if reached_r or (tp1_filled and self.management["move_to_breakeven"]):
            for leg in pos.open_legs:
                self._move_sl(leg, entry, "breakeven", d)

    @staticmethod
    def _move_sl(leg: Leg, level: float, kind: str, direction: Direction) -> None:
        if improves(direction, level, leg.sl):
            leg.sl, leg.sl_kind = level, kind

    def trail(self, view: TimeframeView) -> None:
        if not self.management["trail_after_tp1"]:
            return
        buffer = self.management["trail_buffer_atr"] * view.atr
        for pos in self.open_positions:
            if not pos.tp1_done:
                continue
            for leg in pos.open_legs:
                level = trail_stop(pos.direction, view.swings, leg.sl, view.close, buffer)
                if level is not None:
                    self._move_sl(leg, level, "trail", pos.direction)

    def on_invalidation_close(self, close: float, t: pd.Timestamp, spread_points: float) -> list[SimPosition]:
        """Nến khung invalidation đóng cửa phá mốc setup → đóng toàn bộ ở giá thị trường."""
        for pos in self.open_positions:
            d = pos.direction
            if breaks_invalidation(d, close, pos.plan.signal.setup.invalidation):
                fill = close + self._exit_shift(d, spread_points) - d * self._slip
                for leg in pos.open_legs:
                    leg.close(fill, t, "invalidation")
        return self._prune()

    def close_where(self, predicate, close: float, t: pd.Timestamp, spread_points: float,
                    reason: str) -> list[SimPosition]:
        """Đóng toàn bộ các vị thế thoả `predicate` ở giá thị trường (vd hết giờ giao dịch trong ngày)."""
        for pos in self.open_positions:
            if predicate(pos):
                fill = close + self._exit_shift(pos.direction, spread_points) - pos.direction * self._slip
                for leg in pos.open_legs:
                    leg.close(fill, t, reason)
        return self._prune()

    def floating_money(self, close: float, spread_points: float) -> float:
        total = 0.0
        for pos in self.open_positions:
            mark = close + self._exit_shift(pos.direction, spread_points)
            open_pnl = sum(leg.volume * (mark - pos.plan.entry) * pos.direction for leg in pos.open_legs)
            total += self.spec.money(open_pnl, 1.0)
        return total
