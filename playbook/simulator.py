"""Khớp lệnh trên nến M5 bid (ask = bid + spread), bảo thủ.

- Lệnh market khớp ở giá mở nến M5 đầu tiên từ lúc lệnh có hiệu lực.
- Lệnh chờ: limit khớp ở giá đặt (hoặc giá mở nếu mở gap qua), stop khớp ở max(giá đặt, giá mở) + trượt giá.
- Nến khớp lệnh chờ chỉ xét SL (không biết TP chạm trước hay sau lúc khớp).
- SL và TP trong cùng một nến → tính SL. Dời SL (hòa vốn) có hiệu lực từ nến sau.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from core.types import Direction
from playbook.orders import CANCEL, EXIT, LIMIT, MARKET, STOP, Event, Order
from risk.sizing import SymbolSpec, lot_size, split_legs


@dataclass
class Bars:
    time: np.ndarray    # giờ mở nến (datetime64[ns, UTC] → int64)
    open: np.ndarray
    high: np.ndarray
    low: np.ndarray
    close: np.ndarray
    spread: np.ndarray  # spread theo giá
    step: pd.Timedelta

    @classmethod
    def from_frame(cls, df: pd.DataFrame, point: float, default_spread_points: float, step: pd.Timedelta) -> "Bars":
        spread = df["spread"].to_numpy(float)
        spread = np.where(spread > 0, spread, default_spread_points) * point
        return cls(df["time"].to_numpy("datetime64[ns]").astype(np.int64), *(df[c].to_numpy(float) for c in
                   ("open", "high", "low", "close")), spread, step)

    def __len__(self) -> int:
        return len(self.time)

    def index_at(self, t: pd.Timestamp | None) -> int:
        """Nến đầu tiên mở từ thời điểm t trở đi (len nếu không có)."""
        if t is None:
            return len(self)
        return int(np.searchsorted(self.time, pd.Timestamp(t).value, side="left"))

    def ts(self, i: int) -> pd.Timestamp:
        return pd.Timestamp(self.time[i], tz="UTC")


@dataclass(frozen=True)
class TrailSeries:
    """Mức dời SL theo cấu trúc trên từng nến gốc: mức swing gần nhất đã xác nhận và vị trí nến gốc lúc xác nhận."""
    level: dict[Direction, np.ndarray]
    confirmed_at: dict[Direction, np.ndarray]


@dataclass
class Leg:
    volume: float
    tp: float | None
    name: str
    exit_price: float | None = None
    exit_reason: str | None = None


@dataclass
class Outcome:
    order: Order
    status: str                       # filled | expired | cancelled | skipped
    reason: str = ""
    start: pd.Timestamp | None = None  # chiếm chỗ (lệnh chờ hoặc vị thế) từ ...
    end: pd.Timestamp | None = None    # ... tới
    entry_time: pd.Timestamp | None = None
    entry: float | None = None
    sl: float | None = None
    tp: float | None = None
    tp1: float | None = None
    spread: float = 0.0
    legs: list[Leg] = field(default_factory=list)
    mfe: float = 0.0
    mae: float = 0.0

    @property
    def volume(self) -> float:
        return sum(leg.volume for leg in self.legs)

    @property
    def risk(self) -> float:
        return abs(self.entry - self.sl)

    def price_pnl(self) -> float:
        d = self.order.direction
        return sum(leg.volume * (leg.exit_price - self.entry) * d for leg in self.legs)

    def r_multiple(self) -> float:
        return self.price_pnl() / (self.volume * self.risk) if self.risk > 0 else 0.0

    @property
    def exit_reason(self) -> str:
        return "+".join(f"{leg.name}:{leg.exit_reason}" for leg in self.legs)


class OrderSimulator:
    def __init__(self, bars: Bars, spec: SymbolSpec, risk_money: float, slippage_points: float,
                 events: list[Event], trails: dict[str, TrailSeries] | None = None) -> None:
        self._b = bars
        self._trails = trails or {}
        self._spec = spec
        self._risk_money = risk_money
        self._slip = slippage_points * spec.point
        self._events = sorted(events, key=lambda e: e.time)

    # ---------- tiện ích ----------
    def start_time(self, order: Order) -> pd.Timestamp | None:
        """Thời điểm lệnh bắt đầu chiếm chỗ: market = nến khớp, lệnh chờ = lúc đặt."""
        if order.kind != MARKET:
            return order.time
        i = self._b.index_at(order.time)
        return self._b.ts(i) if i < len(self._b) else None

    def _first_event(self, order: Order, after: pd.Timestamp, action: str) -> pd.Timestamp | None:
        for event in self._events:
            if event.time > after and event.direction == order.direction and action in event.actions:
                return event.time
        return None

    def _bid_ask(self, sl: slice, direction: Direction) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """open/high/low phía giá thoát lệnh: BUY thoát theo bid, SELL thoát theo ask."""
        b = self._b
        shift = 0.0 if direction == Direction.BUY else b.spread[sl]
        return b.open[sl] + shift, b.high[sl] + shift, b.low[sl] + shift

    # ---------- khớp lệnh ----------
    def _fill(self, order: Order) -> tuple[int, float] | tuple[None, str]:
        b, d = self._b, order.direction
        start = b.index_at(order.time)
        if start >= len(b):
            return None, "no_data"
        if order.kind == MARKET:
            if order.max_spread is not None and b.spread[start] > order.max_spread:
                return None, "spread_too_wide"
            ask_open = b.open[start] + b.spread[start]
            return start, (ask_open + self._slip) if d == Direction.BUY else (b.open[start] - self._slip)
        stop = b.index_at(order.expiry)
        cancel = self._first_event(order, order.time, CANCEL)
        stop = min(stop, b.index_at(cancel)) if cancel is not None else stop
        if stop <= start:
            return None, "expired"
        s = slice(start, stop)
        spr = b.spread[s]
        ask_o, ask_h, ask_l = b.open[s] + spr, b.high[s] + spr, b.low[s] + spr
        bid_o, bid_h, bid_l = b.open[s], b.high[s], b.low[s]
        p = order.price
        if order.kind == LIMIT:
            hit = (ask_l <= p) if d == Direction.BUY else (bid_h >= p)
        elif order.kind == STOP:
            hit = (ask_h >= p) if d == Direction.BUY else (bid_l <= p)
        else:
            raise ValueError(f"loại lệnh không hỗ trợ: {order.kind}")
        if not hit.any():
            return None, "cancelled" if cancel is not None and b.index_at(cancel) == stop else "expired"
        k = int(np.argmax(hit))
        i = start + k
        if order.kind == LIMIT:
            price = min(p, ask_o[k]) if d == Direction.BUY else max(p, bid_o[k])
        else:
            price = (max(p, ask_o[k]) + self._slip) if d == Direction.BUY else (min(p, bid_o[k]) - self._slip)
        return i, float(price)

    # ---------- vòng đời vị thế ----------
    def run(self, order: Order, risk_money: float | None = None) -> Outcome:
        """`risk_money` ghi đè số tiền rủi ro mặc định (vd khi tính theo % equity)."""
        risk = order.planned_risk
        if risk is None or not risk > 0:
            return Outcome(order, "skipped", "bad_stop", order.time, order.time)
        lot = lot_size(self._risk_money if risk_money is None else risk_money, risk, self._spec)
        if lot <= 0:
            return Outcome(order, "skipped", "lot_too_small", order.time, order.time)
        fill_index, value = self._fill(order)
        if fill_index is None:
            end = order.expiry or order.time
            return Outcome(order, "skipped" if order.kind == MARKET else value, value, self.start_time(order) or
                           order.time, end)
        return self._manage(order, fill_index, value, lot)

    def _manage(self, order: Order, f: int, entry: float, lot: float) -> Outcome:
        b, d = self._b, order.direction
        sl = order.sl if order.sl is not None else entry - d * order.sl_dist
        if (entry - sl) * d <= 0:
            return Outcome(order, "skipped", "sl_wrong_side", order.time, b.ts(f))
        tp = order.tp if order.tp is not None and (order.tp - entry) * d > 0 else (
            entry + d * order.tp_dist if order.tp_dist is not None else None)
        risk = abs(entry - sl)
        tp1 = entry + d * order.tp1_dist if order.tp1_dist is not None else None
        volumes = split_legs(lot, order.tp1_fraction, self._spec) if tp1 is not None else (lot,)
        if len(volumes) == 2:
            legs = [Leg(volumes[0], tp1, "tp1"), Leg(volumes[1], tp, "runner")]
            be_dist = None
        else:
            legs = [Leg(lot, tp, "single")]
            be_dist = order.tp1_dist  # không chia được: dời hòa vốn khi tới mức TP1
        if order.be_trigger is not None:
            be_dist = order.be_trigger
        elif order.be_trigger_r is not None:
            be_dist = order.be_trigger_r * risk
        out = Outcome(order, "filled", start=self.start_time(order), entry_time=b.ts(f), entry=entry, sl=sl,
                      tp=tp, tp1=tp1, spread=float(b.spread[f]), legs=legs)
        limit = self._limit_index(order, f)
        sl_kind, i, first_bar = "sl", f, order.kind != MARKET
        while any(leg.exit_price is None for leg in legs):
            if i >= limit:
                self._close_at_limit(out, limit)
                break
            s = slice(i, limit)
            o, h, l = self._bid_ask(s, d)
            open_legs = [leg for leg in legs if leg.exit_price is None]
            stops = self._stops(order, f, s, sl)
            sl_hit = (l <= stops) if d == Direction.BUY else (h >= stops)
            targets = [leg.tp for leg in open_legs if leg.tp is not None]
            near = (min if d == Direction.BUY else max)(targets) if targets else None
            tp_hit = np.zeros_like(sl_hit) if near is None else ((h >= near) if d == Direction.BUY else (l <= near))
            fav = (h - entry) if d == Direction.BUY else (entry - l)
            be_hit = (fav >= be_dist) if be_dist is not None else np.zeros_like(sl_hit)
            if first_bar:
                tp_hit[0] = be_hit[0] = False
            any_hit = sl_hit | tp_hit | be_hit
            if not any_hit.any():
                i = limit
                continue
            k = int(np.argmax(any_hit))
            bar = i + k
            if (stops[k] - sl) * d > 0:
                sl, sl_kind = float(stops[k]), "trail"
            if sl_hit[k]:
                gapped = (o[k] <= sl) if d == Direction.BUY else (o[k] >= sl)
                price = (o[k] if gapped else sl) - d * self._slip
                for leg in open_legs:
                    leg.exit_price, leg.exit_reason = float(price), sl_kind
                out.end = b.ts(bar) + b.step
                break
            if tp_hit[k]:
                for leg in open_legs:
                    if leg.tp is not None and ((h[k] >= leg.tp) if d == Direction.BUY else (l[k] <= leg.tp)):
                        leg.exit_price, leg.exit_reason = float(leg.tp), "tp1" if leg.name == "tp1" else "tp"
                if any(leg.name == "tp1" and leg.exit_reason == "tp1" for leg in legs):
                    be_dist = 0.0  # sau TP1: dời phần còn lại về hòa vốn ngay từ nến sau
                out.end = b.ts(bar) + b.step
            if be_dist is not None and fav[k] >= be_dist:
                new_sl = entry + d * order.be_offset
                if (new_sl - sl) * d > 0:
                    sl, sl_kind = new_sl, "breakeven"
                be_dist = None
            i, first_bar = bar + 1, False
        exit_index = min(b.index_at(out.end), len(b)) if out.end is not None else f + 1
        self._excursion(out, f, max(exit_index, f + 1))
        return out

    def _stops(self, order: Order, f: int, s: slice, sl: float) -> np.ndarray:
        """SL theo từng nến: SL hiện tại, siết thêm theo swing khung lớn xác nhận SAU lúc vào lệnh (chỉ một chiều)."""
        n = s.stop - s.start
        if order.trail is None:
            return np.full(n, sl)
        series, d = self._trails[order.trail], order.direction
        level = np.where(series.confirmed_at[d][s] > f, series.level[d][s], np.nan)
        if d == Direction.BUY:
            return np.maximum.accumulate(np.fmax(sl, level))
        return np.minimum.accumulate(np.fmin(sl, level))

    def _limit_index(self, order: Order, f: int) -> int:
        b = self._b
        fill_time = b.ts(f)
        limits = [len(b)]
        if order.exit_at is not None:
            limits.append(b.index_at(order.exit_at))
        if order.max_hold is not None:
            limits.append(b.index_at(fill_time + order.max_hold))
        exit_event = self._first_event(order, order.time, EXIT)
        if exit_event is not None:
            limits.append(b.index_at(exit_event))
        return max(min(limits), f + 1)

    def _close_at_limit(self, out: Outcome, limit: int) -> None:
        b, d = self._b, out.order.direction
        if limit < len(b):
            o, _, _ = self._bid_ask(slice(limit, limit + 1), d)
            price, reason, end = float(o[0]) - d * self._slip, "time", b.ts(limit)
        else:
            last = len(b) - 1
            price = float(b.close[last] + (0.0 if d == Direction.BUY else b.spread[last]))
            reason, end = "end_of_data", b.ts(last) + b.step
        for leg in out.legs:
            if leg.exit_price is None:
                leg.exit_price, leg.exit_reason = price, reason
        out.end = end

    def _excursion(self, out: Outcome, start: int, stop: int) -> None:
        _, h, l = self._bid_ask(slice(start, stop), out.order.direction)
        if out.order.direction == Direction.BUY:
            out.mfe, out.mae = float(h.max() - out.entry), float(out.entry - l.min())
        else:
            out.mfe, out.mae = float(out.entry - l.min()), float(h.max() - out.entry)
