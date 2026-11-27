"""Phá mô hình có lực + cấu trúc khung lớn cùng chiều + retest cạnh vừa phá, vào bằng nến xác nhận khung nhỏ.

Mỗi cú phá mẫu hình (playbook/patterns.py, không gồm channel_bounce) ở khung mẫu hình `tf`:
1. Lực phá (mỗi điều kiện null = tắt), tại nến phá k:
   - `body_atr`: thân nến ≥ N × ATR và đóng cửa trong `close_pos` phần biên độ phía chiều phá;
   - `min_break_atr`: đóng cửa cách cạnh ≥ N × ATR;
   - `volume_mult`: tick volume ≥ N × trung bình `volume_bars` nến trước;
   - `bos_bars`: trong N nến tính từ k, có nến đóng cửa vượt đỉnh (BUY) / thủng đáy (SELL) swing gần nhất đã xác nhận.
2. Retest: trong `retest_bars` nến khung mẫu hình sau khi đủ lực, giá khung xác nhận (`confirm_tf[tf]`) chạm vùng
   cạnh vừa phá (± `zone_atr` × ATR). Đóng cửa quay vào trong cạnh quá `invalid_atr` × ATR → huỷ.
3. Sau khi chạm: nến pin bar / engulfing đúng chiều, đóng cửa ở phía đã phá → vào lệnh giá đóng cửa.
   SL = đáy (BUY) / đỉnh (SELL) thấp/cao nhất từ lúc chạm ± `sl_buffer_atr` × ATR; SL > `max_sl_atr` × ATR → bỏ.
4. Chiều: xu hướng cấu trúc (CHoCH/BOS, playbook/trend_structure.py) của khung `structure_tf[tf]` tại lúc vào
   phải cùng chiều lệnh — không dùng EMA.
Khoá lệnh `<code>:retest_<loại>@<tf>:...` để học kinh nghiệm và thống kê riêng.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from core.types import Direction
from playbook import indicators as ind
from playbook.common import MarketData
from playbook.orders import MARKET, Order
from playbook.patterns import Edge, Signal, scan
from playbook.trend_structure import structure_trend
from playbook.trendlines import LineRules

B = Direction.BUY


@dataclass(frozen=True)
class Frame:
    o: np.ndarray
    h: np.ndarray
    l: np.ndarray
    c: np.ndarray
    v: np.ndarray

    @classmethod
    def of(cls, df: pd.DataFrame) -> Frame:
        return cls(*(df[col].to_numpy(float) for col in ("open", "high", "low", "close", "tick_volume")))


def _broken_edge(sig: Signal) -> Edge:
    if len(sig.edges) == 1:
        return sig.edges[0]
    upper, lower = sig.edges
    return upper if sig.direction == B else lower


def _strong_bar(f: Frame, k: int, d: int, line: float, atr: float, s: dict) -> bool:
    rng = f.h[k] - f.l[k]
    if s.get("body_atr") is not None:
        if (f.c[k] - f.o[k]) * d < s["body_atr"] * atr or rng <= 0:
            return False
        extreme = f.h[k] if d == 1 else f.l[k]
        if abs(extreme - f.c[k]) > s["close_pos"] * rng:
            return False
    if s.get("min_break_atr") is not None and (f.c[k] - line) * d < s["min_break_atr"] * atr:
        return False
    if s.get("volume_mult") is not None:
        n = s["volume_bars"]
        if k < n or f.v[k] < s["volume_mult"] * f.v[k - n:k].mean():
            return False
    return True


def _bos_bar(f: Frame, highs: np.ndarray, lows: np.ndarray, swing: int, k: int, d: int, bars: int | None) -> int | None:
    """Nến đầu tiên trong [k, k + bars) đóng cửa vượt swing gần nhất (đã xác nhận tại k) theo chiều d; None nếu không."""
    if bars is None:
        return k
    pivots = highs if d == 1 else lows
    known = pivots[pivots + swing <= k]
    if not len(known):
        return None
    level = (f.h if d == 1 else f.l)[known[-1]]
    for j in range(k, min(k + bars, len(f.c))):
        if (f.c[j] - level) * d > 0:
            return j
    return None


def _trigger(f: Frame, j: int, d: int, t: dict) -> str | None:
    o, h, l, c = f.o[j], f.h[j], f.l[j], f.c[j]
    if j > 0:
        po, pc = f.o[j - 1], f.c[j - 1]
        if (c - o) * d > 0 and (pc - po) * d < 0 and (c - po) * d >= 0 and (pc - o) * d >= 0:
            return "engulfing"
    rng, body = h - l, abs(c - o)
    lower, upper = min(o, c) - l, h - max(o, c)
    wick, other = (lower, upper) if d == 1 else (upper, lower)
    if rng > 0 and wick >= t["pin_wick_body_ratio"] * body and wick > other and wick >= t["pin_min_wick_range"] * rng:
        return "pin_bar"
    return None


def _entry(sig: Signal, edge: Edge, pf: pd.DataFrame, ready: int, atr: float, cf: pd.DataFrame, cfr: Frame,
           p: dict) -> tuple[int, float, str] | None:
    """Tìm nến xác nhận retest ở khung nhỏ: (vị trí nến, SL, loại nến) hoặc None."""
    return confirm_entry(int(sig.direction), edge, pf, ready, sig.k + p["retest_bars"], atr, cf, cfr, p)


def confirm_entry(d: int, edge, pf: pd.DataFrame, ready: int, until: int, atr: float, cf: pd.DataFrame, cfr: Frame,
                  p: dict) -> tuple[int, float, str] | None:
    """Retest đường `edge` (có .value(chỉ số nến khung mẫu hình)) từ nến `ready` tới nến `until` của khung mẫu hình:
    chạm vùng ± zone_atr, nến pin/engulfing khung nhỏ đóng cửa ở phía đã phá → (vị trí nến, SL, loại nến); đóng cửa quay
    vào trong quá invalid_atr → huỷ. Tham số trong `p`: zone_atr, invalid_atr, sl_buffer_atr, max_sl_atr, trigger."""
    start = int(cf["time"].searchsorted(pf["close_time"].iat[ready], side="left"))
    last = min(until, len(pf) - 1)
    stop = int(cf["time"].searchsorted(pf["close_time"].iat[last], side="left"))
    pattern_idx = pf["time"].searchsorted(cf["time"].iloc[start:stop], side="right") - 1
    zone, invalid = p["zone_atr"] * atr, p["invalid_atr"] * atr
    extreme = None
    for j, x in zip(range(start, stop), pattern_idx):
        line = edge.value(x)
        if (cfr.c[j] - line) * d < -invalid:
            return None
        far_side = cfr.l[j] if d == 1 else cfr.h[j]
        if extreme is None and (far_side - line) * d > zone:
            continue
        extreme = far_side if extreme is None else (min(extreme, far_side) if d == 1 else max(extreme, far_side))
        kind = _trigger(cfr, j, d, p["trigger"])
        if kind and (cfr.c[j] - line) * d > 0:
            sl = extreme - d * p["sl_buffer_atr"] * atr
            return (j, sl, kind) if (cfr.c[j] - sl) * d <= p["max_sl_atr"] * atr else None
    return None


def _structure(data: MarketData, tf: str, s: dict) -> pd.DataFrame:
    df = data.frame(tf)
    rules = LineRules(s["min_touches"], s["touch_tol_atr"], s["channel_min_touches"], s["max_pivots"])
    trend = structure_trend(df, s["swing"][tf], s["mode"], rules, s["break_atr"], s["atr"], s["use_trendline"])
    return pd.DataFrame({"close_time": df["close_time"], "trend": trend})


def _aligned(orders: list[Order], trend: pd.DataFrame) -> list[Order]:
    if not orders:
        return orders
    times = pd.DataFrame({"close_time": [o.time for o in orders]})
    state = pd.merge_asof(times, trend, on="close_time", direction="backward")["trend"].fillna(0).to_numpy()
    return [o for o, t in zip(orders, state) if t == int(o.direction)]


def retest(data: MarketData, pat: dict, p: dict, code: str) -> list[Order]:
    """`pat`: tham số quét mẫu hình (playbook/patterns.py, có thể kèm `scan_since`); `p`: mục `retest` của phương pháp."""
    orders: list[Order] = []
    since = pat.get("scan_since")
    lookback = p["retest_bars"] + (p["strength"].get("bos_bars") or 0) + 1
    for tf in p["timeframes"]:
        pf, cf = data.frame(tf), data.frame(p["confirm_tf"][tf])
        pfr, cfr = Frame.of(pf), Frame.of(cf)
        swing = pat["swing"][tf]
        atr = ind.atr(pf, pat["atr"]).to_numpy(float)
        is_high, is_low = ind.fractal_swings(pf, swing, swing)
        highs, lows = np.flatnonzero(is_high), np.flatnonzero(is_low)
        start = 1 if since is None else max(1, int(pf["close_time"].searchsorted(since, side="right")) - lookback)
        found = []
        for sig in scan(pf, pat, swing, start):
            k, d = sig.k, int(sig.direction)
            if sig.kind not in p["kinds"] or not np.isfinite(atr[k]):
                continue
            if not _strong_bar(pfr, k, d, sig.line, atr[k], p["strength"]):
                continue
            ready = _bos_bar(pfr, highs, lows, swing, k, d, p["strength"].get("bos_bars"))
            if ready is None:
                continue
            edge = _broken_edge(sig)
            hit = _entry(sig, edge, pf, ready, atr[k], cf, cfr, p)
            if hit is None:
                continue
            j, sl, candle = hit
            t, close = cf["close_time"].iat[j], cfr.c[j]
            tp = sig.target if (sig.target - close) * d > 0 else None
            times = pf["time"]
            edges = [[str(times.iat[e.i1]), float(e.p1), str(times.iat[e.i2]), float(e.p2)] for e in sig.edges]
            kind = f"retest_{sig.kind}"
            found.append(Order(
                f"{code}:{kind}@{tf}:{t:%Y%m%d%H%M}:{sig.direction.name}", t, sig.direction, MARKET,
                sl_dist=float((close - sl) * d), tp=tp,
                reasons=(f"{sig.kind} {tf} phá có lực, retest cạnh {edge.value(k):.2f}",
                         f"{candle} {p['confirm_tf'][tf]} xác nhận, cấu trúc {p['structure_tf'][tf]} cùng chiều",
                         sig.detail, f"mục tiêu {sig.target:.2f}"),
                meta={"tf": tf, "kind": kind, "edges": edges, "line": float(sig.line), "target": float(sig.target),
                      "breakout_time": str(times.iat[k])}))
        found.sort(key=lambda o: o.time)
        orders += _aligned(found, _structure(data, p["structure_tf"][tf], p["structure"]))
    return sorted(orders, key=lambda o: o.time)
