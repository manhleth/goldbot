"""Chuỗi trendline nhân quả trên một khung: tại mỗi nến biết trendline tăng/giảm đang hiệu lực, kênh giá và các lần phá.

Trendline tăng (BUY) đi qua đáy swing mới nhất và một đáy cũ hơn thấp hơn; hợp lệ khi:
- có ít nhất `min_touches` đáy swing nằm trên đường (cách đường ≤ `touch_tol_atr` × ATR),
- không đáy swing nào thủng đường quá dung sai và không nến nào đóng cửa dưới đường cho tới lúc xác nhận.
Kênh giá: đường song song qua đỉnh swing xa nhất phía trên; hợp lệ khi có ≥ `channel_min_touches` đỉnh chạm (dung sai như trên).
Đường hiệu lực tới khi có nến đóng cửa phá qua quá `break_atr` × ATR hoặc bị đường mới thay. Trendline giảm đối xứng.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from core.types import Direction
from playbook import indicators as ind


@dataclass(frozen=True, slots=True)
class Line:
    i1: int
    p1: float
    i2: int
    p2: float
    touches: int
    channel: float | None = None  # khoảng cách tới đường kênh song song phía đối diện (None = không có kênh)

    @property
    def slope(self) -> float:
        return (self.p2 - self.p1) / (self.i2 - self.i1)

    def value(self, index) -> np.ndarray | float:
        return self.p1 + self.slope * (np.asarray(index, float) - self.i1)


@dataclass(frozen=True, slots=True)
class LineBreak:
    index: int          # nến đóng cửa phá đường
    line: Line
    side: Direction     # BUY: đường tăng (nối đáy) bị phá xuống; SELL: đường giảm (nối đỉnh) bị phá lên


@dataclass(frozen=True)
class TrendlineSeries:
    value: dict[Direction, np.ndarray]    # giá trị đường đang hiệu lực tại nến (NaN nếu không có)
    slope: dict[Direction, np.ndarray]    # độ dốc đường (giá / nến) để ngoại suy trong nến đang chạy
    channel: dict[Direction, np.ndarray]  # giá trị đường kênh đối diện (NaN nếu không có kênh)
    line_id: dict[Direction, np.ndarray]  # mã đường (vị trí điểm thứ hai) để đếm số lần vào lệnh mỗi đường
    breaks: list[LineBreak]


@dataclass(frozen=True)
class LineRules:
    min_touches: int
    touch_tol_atr: float
    channel_min_touches: int
    max_pivots: int


def _channel(line: Line, side: Direction, opposite: list[int], prices: np.ndarray, tol: float,
             min_touches: int) -> float | None:
    """Khoảng cách kênh: đỉnh (BUY) xa đường nhất sau điểm đầu; đủ số điểm chạm thì là kênh."""
    pts = [o for o in opposite if o > line.i1]
    if len(pts) < min_touches:
        return None
    dist = (prices[pts] - line.value(pts)) * side
    width = float(dist.max())
    if width <= 0 or int((dist >= width - tol).sum()) < min_touches:
        return None
    return width


def _candidate(pivots: list[int], prices: np.ndarray, opposite: list[int], opp_prices: np.ndarray,
               closes: np.ndarray, k: int, side: Direction, tol: float, rules: LineRules) -> Line | None:
    """Đường qua điểm mới nhất có nhiều điểm chạm nhất (≥ min_touches), không bị xuyên; ưu tiên điểm đầu gần hơn."""
    recent = pivots[-rules.max_pivots:]
    b = recent[-1]
    best: Line | None = None
    for a in reversed(recent[:-1]):
        if (prices[b] - prices[a]) * side <= 0:
            continue
        probe = Line(a, prices[a], b, prices[b], 0)
        on = [p for p in recent if a <= p <= b]
        gap = (prices[on] - probe.value(on)) * side  # >0: nằm đúng phía; <0: xuyên đường
        if (gap < -tol).any():
            continue
        idx = np.arange(a + 1, k + 1)
        if ((closes[idx] - probe.value(idx)) * side < 0).any():
            continue
        touches = int((np.abs(gap) <= tol).sum())
        if touches >= rules.min_touches and (best is None or touches > best.touches):
            best = Line(a, prices[a], b, prices[b], touches)
    if best is None:
        return None
    width = _channel(best, side, opposite, opp_prices, tol, rules.channel_min_touches)
    return Line(best.i1, best.p1, best.i2, best.p2, best.touches, width)


def build(df: pd.DataFrame, swing: int, rules: LineRules, break_atr: float, atr_period: int) -> TrendlineSeries:
    is_high, is_low = ind.fractal_swings(df, swing, swing)
    lows, highs, closes = (df[c].to_numpy(float) for c in ("low", "high", "close"))
    atr = ind.atr(df, atr_period).to_numpy(float)
    n = len(df)
    sides = (Direction.BUY, Direction.SELL)
    value = {d: np.full(n, np.nan) for d in sides}
    channel = {d: np.full(n, np.nan) for d in sides}
    slope = {d: np.full(n, np.nan) for d in sides}
    line_id = {d: np.full(n, -1) for d in sides}
    pivots: dict[Direction, list[int]] = {d: [] for d in sides}
    active: dict[Direction, Line | None] = {d: None for d in sides}
    breaks: list[LineBreak] = []
    prices = {Direction.BUY: lows, Direction.SELL: highs}
    masks = {Direction.BUY: is_low, Direction.SELL: is_high}
    for k in range(n):
        s = k - swing  # swing tại s được xác nhận khi nến k đóng
        if s >= 0:
            for side in sides:
                if masks[side][s]:
                    pivots[side].append(s)
        for side in sides:
            other = Direction(-int(side))
            if s >= 0 and np.isfinite(atr[k]) and (masks[side][s] or masks[other][s]) and pivots[side]:
                fresh = _candidate(pivots[side], prices[side], pivots[other], prices[other], closes, k, side,
                                   rules.touch_tol_atr * atr[k], rules)
                if fresh is not None:
                    active[side] = fresh
            line = active[side]
            if line is None:
                continue
            v = float(line.value(k))
            if np.isfinite(atr[k]) and (v - closes[k]) * side > break_atr * atr[k]:
                breaks.append(LineBreak(k, line, side))
                active[side] = None
                continue
            value[side][k], line_id[side][k], slope[side][k] = v, line.i2, line.slope
            if line.channel is not None:
                channel[side][k] = v + side * line.channel
    return TrendlineSeries(value, slope, channel, line_id, breaks)
