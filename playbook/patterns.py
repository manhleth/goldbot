"""Nhận diện mẫu hình trendline dạng vùng (docs/knowledge/chart-patterns.md) trên một hay nhiều khung.

Tại nến k, mẫu hình dựng từ dữ liệu tới nến k-1 (swing đã xác nhận, nến đã đóng); nến k quyết định tín hiệu:
- phá cạnh (đóng cửa vượt cạnh quá `break_atr` × ATR): flag (cùng chiều cán cờ) / channel_break / triangle_break /
  broadening_break; cạnh đơn ≥ `neck_touches` chạm bị thủng: neckline_break.
- bật cạnh kênh song song: channel_bounce (chạm vùng cạnh, đóng cửa quay vào, nến cùng màu).
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from core.types import Direction
from playbook import indicators as ind
from playbook.common import MarketData
from playbook.orders import MARKET, Order, Signals

B, S = Direction.BUY, Direction.SELL
UPPER, LOWER = 1, -1  # cạnh trên nối đỉnh, cạnh dưới nối đáy


@dataclass(frozen=True, slots=True)
class Edge:
    i1: int
    p1: float
    i2: int
    p2: float
    touches: int

    @property
    def slope(self) -> float:
        return (self.p2 - self.p1) / (self.i2 - self.i1)

    def value(self, x: float) -> float:
        return self.p1 + self.slope * (x - self.i1)


@dataclass(frozen=True)
class Bars:
    o: np.ndarray
    h: np.ndarray
    l: np.ndarray
    c: np.ndarray
    atr: np.ndarray
    highs: list[int]  # vị trí swing high đã xác nhận (theo thứ tự)
    lows: list[int]
    confirm: int      # số nến phải để xác nhận swing


def _bars(df: pd.DataFrame, swing: int, atr_period: int) -> Bars:
    is_high, is_low = ind.fractal_swings(df, swing, swing)
    return Bars(*(df[c].to_numpy(float) for c in ("open", "high", "low", "close")),
                ind.atr(df, atr_period).to_numpy(float), list(np.flatnonzero(is_high)), list(np.flatnonzero(is_low)),
                swing)


def _recent(pivots: list[int], last: int, confirm: int, window: int, limit: int) -> list[int]:
    """Swing đã xác nhận tới nến `last` (s + confirm <= last), nằm trong `window` nến gần nhất, tối đa `limit` điểm."""
    out = [s for s in pivots if last - window <= s <= last - confirm]
    return out[-limit:]


def _edge(bars: Bars, side: int, last: int, p: dict, tol: float, break_tol: float, min_touches: int) -> Edge | None:
    """Cạnh qua 2 swing gần đây: mọi swing cùng phía không vượt quá dung sai, không nến nào đóng cửa vượt cạnh từ điểm
    đầu tới `last`. Chọn đường nhiều điểm chạm nhất, rồi điểm thứ hai mới nhất."""
    prices = bars.h if side == UPPER else bars.l
    pts = _recent(bars.highs if side == UPPER else bars.lows, last, bars.confirm, p["window_bars"], p["max_pivots"])
    best: Edge | None = None
    for j in range(len(pts) - 1, 0, -1):
        b = pts[j]
        for a in pts[:j]:
            line = Edge(a, prices[a], b, prices[b], 0)
            on = [q for q in pts if q >= a]
            gap = (np.array([prices[q] - line.value(q) for q in on])) * side  # >0: vượt ra ngoài cạnh
            if (gap > tol).any():
                continue
            seg = np.arange(a, last + 1)
            if ((bars.c[seg] - (line.p1 + line.slope * (seg - a))) * side > break_tol).any():
                continue
            touches = int((np.abs(gap) <= tol).sum())
            if touches >= min_touches and (best is None or touches > best.touches):
                best = Edge(a, prices[a], b, prices[b], touches)
        if best is not None:
            return best  # ưu tiên đường có điểm thứ hai mới nhất
    return None


def _pole(bars: Bars, start: int, p: dict) -> tuple[int, float]:
    """Cán cờ trước điểm bắt đầu mẫu hình: (+1 tăng / -1 giảm / 0, độ dài)."""
    lo = max(0, start - p["pole_bars"])
    up = bars.h[start] - bars.l[lo:start + 1].min()
    down = bars.h[lo:start + 1].max() - bars.l[start]
    length, direction = (up, 1) if up >= down else (down, -1)
    return (direction, float(length)) if length >= p["pole_atr"] * bars.atr[start] else (0, 0.0)


def _shape(upper: Edge, lower: Edge, span: int, height: float, p: dict) -> str:
    change = (upper.slope - lower.slope) * span  # chiều cao thay đổi qua mẫu hình
    if abs(change) <= p["parallel_tol"] * height:
        return "channel"
    return "triangle" if change < 0 else "broadening"


@dataclass(frozen=True)
class Signal:
    k: int
    direction: Direction
    kind: str
    line: float      # giá trị cạnh liên quan tại nến k
    target: float    # measured move
    detail: str
    edges: tuple[Edge, ...] = ()


def scan(df: pd.DataFrame, p: dict, swing: int, start: int = 1) -> list[Signal]:
    """Quét các nến từ vị trí `start` (live chỉ cần quét nến mới; mẫu hình đã bị phá tự mất vì cạnh không còn hợp lệ)."""
    bars = _bars(df, swing, p["atr"])
    out: list[Signal] = []
    seen: set[tuple] = set()
    for k in range(max(1, start), len(df)):
        a = bars.atr[k - 1]
        if not np.isfinite(a):
            continue
        tol, brk = p["zone_atr"] * a, p["break_atr"] * a
        upper = _edge(bars, UPPER, k - 1, p, tol, brk, p["min_touches"])
        lower = _edge(bars, LOWER, k - 1, p, tol, brk, p["min_touches"])
        c, o = bars.c[k], bars.o[k]
        if upper is not None and lower is not None:
            start = min(upper.i1, lower.i1)
            u, lo = upper.value(k), lower.value(k)
            height = u - lo
            span = k - start
            if span >= p["min_bars"] and p["min_height_atr"] * a <= height <= p["max_height_atr"] * a:
                shape = _shape(upper, lower, span, height, p)
                pole_dir, pole_len = _pole(bars, start, p)
                pattern = (upper.i1, upper.i2, lower.i1, lower.i2)
                for d, edge_value in ((B, u), (S, lo)):
                    if (c - edge_value) * d > brk and (pattern, d) not in seen:
                        seen.add((pattern, d))
                        flag = pole_dir == d and pole_len >= p["pole_height_ratio"] * height
                        kind = "flag" if flag else f"{shape}_break"
                        target = edge_value + d * (pole_len if flag else height)
                        out.append(Signal(k, d, kind, edge_value, target,
                                          f"{shape} {span} nến, cao {height:.2f}, chạm {upper.touches}/{lower.touches}",
                                          (upper, lower)))
                if shape == "channel":
                    for d, edge_value, far in ((B, lo, u), (S, u, lo)):
                        zone_hit = (bars.l[k] <= edge_value + tol) if d == B else (bars.h[k] >= edge_value - tol)
                        back_in = (c - edge_value) * d > 0 and (c - o) * d > 0 and abs(c - edge_value) < height / 2
                        key = ("bounce", pattern, d)
                        if zone_hit and back_in and key not in seen:
                            seen.add(key)
                            out.append(Signal(k, d, "channel_bounce", edge_value, far,
                                              f"kênh {span} nến, cao {height:.2f}", (upper, lower)))
                continue
        for side, edge in ((UPPER, upper), (LOWER, lower)):
            neck = edge if edge is not None and edge.touches >= p["neck_touches"] else None
            if neck is None:
                continue
            v = neck.value(k)
            d = B if side == UPPER else S
            key = ("neck", neck.i1, neck.i2, d)
            if (c - v) * d > brk and key not in seen:
                seen.add(key)
                seg = slice(neck.i1, k)
                head = (v - bars.l[seg].min()) if d == B else (bars.h[seg].max() - v)
                out.append(Signal(k, d, "neckline_break", v, v + d * head, f"neckline {neck.touches} chạm", (neck,)))
    return out


def patterns(data: MarketData, p: dict) -> Signals:
    orders: list[Order] = []
    since = p.get("scan_since")  # live: chỉ quét các nến đóng sau thời điểm này
    for tf in p["timeframes"]:
        df = data.frame(tf)
        atr = ind.atr(df, p["atr"]).to_numpy(float)
        start = int(df["close_time"].searchsorted(since, side="right")) if since is not None else 1
        for sig in scan(df, p, p["swing"][tf], start):
            k, d = sig.k, sig.direction
            if sig.kind == "channel_bounce":
                anchor = (min(df["low"].iat[k], sig.line) if d == B else max(df["high"].iat[k], sig.line))
                sl = anchor - d * p["sl_buffer_atr"] * atr[k]
            else:
                sl = sig.line - d * p["sl_break_atr"] * atr[k]
            close = df["close"].iat[k]
            dist = (close - sl) * d
            if not (dist > 0 and np.isfinite(dist)):
                continue
            t = df["close_time"].iat[k]
            tp = sig.target if (sig.target - close) * d > 0 else None
            times = df["time"]
            edges = [[str(times.iat[e.i1]), float(e.p1), str(times.iat[e.i2]), float(e.p2)] for e in sig.edges]
            orders.append(Order(f"{p['code']}:{sig.kind}@{tf}:{t:%Y%m%d%H%M}:{d.name}", t, d, MARKET,
                                sl_dist=float(dist), tp=tp, reasons=(f"{sig.kind} {tf}", sig.detail,
                                                                       f"cạnh {sig.line:.2f}, mục tiêu {sig.target:.2f}"),
                                meta={"tf": tf, "kind": sig.kind, "edges": edges, "line": float(sig.line),
                                      "target": float(sig.target), "breakout_time": str(times.iat[k])}))
    return Signals(sorted(orders, key=lambda o: o.time), [])
