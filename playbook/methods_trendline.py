"""Phương pháp trendline: trendline vẽ trên khung `line_tf`, xác nhận điểm vào trên khung `tf` (bằng hoặc nhỏ hơn).

- tl_bounce: giá chạm trendline rồi nến khung `tf` đóng cửa bật lại (nến cùng màu) → market.
- tl_retest: trendline bị phá (nến khung `line_tf` đóng cửa xuyên đường), giá quay lại test đường vừa phá và nến khung
  `tf` đóng cửa giữ được phía bên kia trong `retest_max_bars` nến → market. Đóng cửa ngược qua đường trước → hủy.
Chiều lệnh do chính trendline quyết định (đường tăng → BUY, đường giảm → SELL); `trend_tf` (tuỳ chọn) thêm lọc chiều
bằng trendline khung lớn hơn. Trendline cần ≥ `min_touches` điểm chạm; `require_channel` = chỉ vào khi có kênh giá.
SL: dưới (trên) min(low nến vào, giá trị đường) − `sl_buffer_atr` × ATR khung `tf`. TP: `tp_r` × rủi ro.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from core.types import Direction
from playbook import indicators as ind
from playbook.common import MarketData, utc_hours_mask
from playbook.orders import MARKET, Order, Signals
from playbook.trendlines import LineRules, TrendlineSeries, build

B, S = Direction.BUY, Direction.SELL


@dataclass(frozen=True)
class Projected:
    """Trendline khung lớn chiếu lên từng nến khung xác nhận (đã đóng tại giờ đóng nến đó)."""
    df: pd.DataFrame
    line: TrendlineSeries
    position: np.ndarray            # vị trí (theo nến khung trendline, có phần lẻ) tại giờ đóng nến xác nhận
    value: dict[Direction, np.ndarray]
    channel: dict[Direction, np.ndarray]
    line_id: dict[Direction, np.ndarray]
    atr: np.ndarray
    trend: np.ndarray | None        # chiều khung `trend_tf` (+1/−1/0) hoặc None nếu không lọc


def _trend(series: TrendlineSeries) -> np.ndarray:
    """Chiều theo trendline đang hiệu lực; có cả hai thì lấy đường có điểm chạm thứ hai mới hơn."""
    up, down = series.line_id[B], series.line_id[S]
    return np.where((up >= 0) & (up >= down), 1, np.where(down >= 0, -1, 0))


def _rules(p: dict) -> LineRules:
    return LineRules(p["min_touches"], p["touch_tol_atr"], p["channel_min_touches"], p["max_pivots"])


def _project(data: MarketData, p: dict) -> Projected:
    df, big = data.frame(p["tf"]), data.frame(p["line_tf"])
    line = build(big, p["swing"], _rules(p), p["break_atr"], p["atr"])
    step = big["close_time"].iat[1] - big["close_time"].iat[0]
    closes = big["close_time"].to_numpy()
    j = np.searchsorted(closes, df["close_time"].to_numpy(), side="right") - 1  # nến trendline đã đóng gần nhất
    valid = j >= 0
    jj = np.where(valid, j, 0)
    frac = np.where(valid, (df["close_time"].to_numpy() - closes[jj]) / step, np.nan)
    value, channel, line_id = {}, {}, {}
    for d in (B, S):
        v, slope = line.value[d][jj], line.slope[d][jj]
        value[d] = np.where(valid, v + slope * frac, np.nan)
        channel[d] = np.where(valid, line.channel[d][jj] + slope * frac, np.nan)
        line_id[d] = np.where(valid, line.line_id[d][jj], -1)
    trend = None
    if p.get("trend_tf"):
        top = data.frame(p["trend_tf"])
        t = _trend(build(top, p["swing"], _rules(p), p["break_atr"], p["atr"]))
        merged = pd.merge_asof(df[["close_time"]], pd.DataFrame({"close_time": top["close_time"], "trend": t}),
                               on="close_time", direction="backward")
        trend = merged["trend"].fillna(0).to_numpy()
    return Projected(df, line, jj + frac, value, channel, line_id, ind.atr(df, p["atr"]).to_numpy(float), trend)


def _order(name: str, pr: Projected, k: int, d: Direction, line_value: float, p: dict, why: str) -> Order | None:
    df, atr = pr.df, pr.atr[k]
    low, high, close = df["low"].iat[k], df["high"].iat[k], df["close"].iat[k]
    buffer = p["sl_buffer_atr"] * atr
    sl = (min(low, line_value) - buffer) if d == B else (max(high, line_value) + buffer)
    dist = (close - sl) * d
    if not dist > 0:
        return None
    t = df["close_time"].iat[k]
    return Order(f"{name}:{t:%Y%m%d%H%M}:{d.name}", t, d, MARKET, sl_dist=float(dist), tp_dist=p["tp_r"] * float(dist),
                 reasons=(why, f"trendline {p['line_tf']} {line_value:.2f}", f"xác nhận {p['tf']}"))


def _trend_ok(pr: Projected, k: int, d: Direction) -> bool:
    return pr.trend is None or pr.trend[k] == d


def tl_bounce(data: MarketData, p: dict) -> Signals:
    pr = _project(data, p)
    o, h, l, c = (pr.df[col].to_numpy(float) for col in ("open", "high", "low", "close"))
    allowed = utc_hours_mask(pr.df["close_time"], p.get("hours"), p.get("skip_friday", False))
    used: dict[tuple[Direction, int], int] = {}
    orders: list[Order] = []
    for k in range(len(pr.df)):
        for d in (B, S):
            v = pr.value[d][k]
            if not (allowed[k] and np.isfinite(v) and np.isfinite(pr.atr[k]) and _trend_ok(pr, k, d)):
                continue
            if p["require_channel"] and not np.isfinite(pr.channel[d][k]):
                continue
            tol = p["touch_atr"] * pr.atr[k]
            touched = (l[k] <= v + tol) if d == B else (h[k] >= v - tol)
            held = (c[k] - v) * d > 0 and (c[k] - o[k]) * d > 0
            key = (d, int(pr.line_id[d][k]))
            if not (touched and held) or used.get(key, 0) >= p["max_entries_per_line"]:
                continue
            order = _order(p["code"], pr, k, d, float(v), p, "bật trendline")
            if order is not None:
                used[key] = used.get(key, 0) + 1
                orders.append(order)
    return Signals(orders, [])


def tl_retest(data: MarketData, p: dict) -> Signals:
    pr = _project(data, p)
    h, l, c = (pr.df[col].to_numpy(float) for col in ("high", "low", "close"))
    allowed = utc_hours_mask(pr.df["close_time"], p.get("hours"), p.get("skip_friday", False))
    big_close = data.frame(p["line_tf"])["close_time"]
    confirm_close = pr.df["close_time"]
    orders: list[Order] = []
    for brk in pr.line.breaks:
        d = Direction(-int(brk.side))  # phá đường giảm (nối đỉnh) → BUY; phá đường tăng → SELL
        if p["require_channel"] and brk.line.channel is None:
            continue
        start = int(confirm_close.searchsorted(big_close.iat[brk.index], side="left")) + 1  # sau nến phá
        for k in range(start, min(start + p["retest_max_bars"], len(pr.df))):
            v = float(brk.line.value(pr.position[k]))
            if not np.isfinite(pr.atr[k]) or (v - c[k]) * d > p["break_atr"] * pr.atr[k]:
                break  # đóng cửa ngược qua đường → breakout thất bại
            tol = p["touch_atr"] * pr.atr[k]
            touched = (l[k] <= v + tol) if d == B else (h[k] >= v - tol)
            if touched and (c[k] - v) * d > 0:
                if allowed[k] and _trend_ok(pr, k, d):
                    order = _order(p["code"], pr, k, d, v, p, "phá trendline + retest")
                    if order is not None:
                        orders.append(order)
                break  # chỉ xét lần retest đầu tiên
    return Signals(sorted(orders, key=lambda x: x.time), [])
