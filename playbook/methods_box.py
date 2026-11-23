"""Phương pháp hộp theo giờ: XAU-05 (hộp Á UTC), XAU-06 (hộp London), XAU-08 (mở cửa New York), XAU-09 (Á giờ NY)."""
from __future__ import annotations

import numpy as np
import pandas as pd

from core.types import Direction
from playbook.common import MarketData
from playbook.orders import LIMIT, MARKET, STOP, Order, Signals
from risk.calendar import minutes

B, S = Direction.BUY, Direction.SELL


def _at(day: pd.Timestamp, hhmm: str) -> pd.Timestamp:
    return day + pd.Timedelta(minutes=minutes(hhmm))


def _box(m5: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    i, j = m5["time"].searchsorted(start), m5["time"].searchsorted(end)
    return m5.iloc[i:j]


def xau05(data: MarketData, p: dict) -> Signals:
    """Hộp 00:00–07:00 UTC (đủ nến, rộng tối thiểu) → Buy Stop trên đỉnh, Sell Stop dưới đáy; hủy lúc `cancel`."""
    m5 = data.frame(data.base)
    step = m5["time"].iat[1] - m5["time"].iat[0]
    box_minutes = minutes(p["box"][1]) - minutes(p["box"][0])
    need = p["min_coverage"] * pd.Timedelta(minutes=box_minutes) / step  # đủ nến (M5: 84, M15: 28)
    orders: list[Order] = []
    for day in pd.DatetimeIndex(m5["time"]).normalize().unique():
        if day.weekday() >= 4:  # bỏ thứ Sáu và cuối tuần
            continue
        box = _box(m5, _at(day, p["box"][0]), _at(day, p["box"][1]))
        if len(box) < need:
            continue
        hi, lo = float(box["high"].max()), float(box["low"].min())
        if hi - lo < p["min_width"]:
            continue
        t0 = _at(day, p["box"][1])
        first = _box(m5, t0, t0 + pd.Timedelta(minutes=5))
        if first.empty:
            continue
        bid = float(first["open"].iat[0])
        ask = bid + float(first["spread"].iat[0]) * data.point
        expiry = _at(day, p["cancel"])
        buy_at, sell_at = hi + p["offset"], lo - p["offset"]
        if ask < buy_at:
            sl = lo - p["sl_offset"]
            orders.append(Order(f"xau05:{day:%Y%m%d}:BUY", t0, B, STOP, price=buy_at, sl=sl,
                                tp=buy_at + p["tp_r"] * (buy_at - sl), expiry=expiry,
                                reasons=(f"hộp Á {lo:.2f}-{hi:.2f}",)))
        if bid > sell_at:
            sl = hi + p["sl_offset"]
            orders.append(Order(f"xau05:{day:%Y%m%d}:SELL", t0, S, STOP, price=sell_at, sl=sl,
                                tp=sell_at - p["tp_r"] * (sl - sell_at), expiry=expiry,
                                reasons=(f"hộp Á {lo:.2f}-{hi:.2f}",)))
    return Signals(orders, [])


def xau06(data: MarketData, p: dict) -> Signals:
    """Hộp London (M15 09:15–10:45 UTC) → nến M15 đóng vượt hộp ± `confirm` → market; đóng hết lúc `flat`."""
    m5, m15 = data.frame(data.base), data.frame("M15")
    pip, point = p["pip"], data.point
    m5_times = m5["time"]
    orders: list[Order] = []
    for day in pd.DatetimeIndex(m15["time"]).normalize().unique():
        if day.weekday() >= 5:
            continue
        box = _box(m15, _at(day, p["box"][0]), _at(day, p["box"][1]))
        if len(box) < p["box_bars"]:
            continue
        hi, lo = float(box["high"].max()), float(box["low"].min())
        bars = _box(m15, _at(day, p["signal"][0]), _at(day, p["signal"][1]) + pd.Timedelta(minutes=1))
        flat = _at(day, p["flat"])
        for _, bar in bars.iterrows():
            t = bar["close_time"]
            direction = B if bar["close"] > hi + p["confirm"] else S if bar["close"] < lo - p["confirm"] else None
            if direction is None:
                continue
            k = int(m5_times.searchsorted(t))
            if k >= len(m5):
                continue
            spread = float(m5["spread"].iat[k]) * point
            dist = max(spread + p["min_points"] * point, p["min_pips"] * pip) + spread
            orders.append(Order(f"xau06:{t:%Y%m%d%H%M}:{direction.name}", t, direction, MARKET, sl_dist=dist,
                                tp_dist=dist, exit_at=flat, reasons=(f"phá hộp London {lo:.2f}-{hi:.2f}",)))
    return Signals(orders, [])


def _sweep_fvg_order(name: str, bars: pd.DataFrame, box_hi: float, box_lo: float, p: dict, expiry: pd.Timestamp,
                     sl_from_session: bool, skip_both_sides: bool) -> Order | None:
    """Ca đầu tiên trong cửa sổ: giá quét một biên hộp rồi tạo FVG ngược chiều cú quét → lệnh limit ở mép FVG."""
    h, l = bars["high"].to_numpy(float), bars["low"].to_numpy(float)
    swept_low = swept_high = None
    for c in range(len(bars)):
        if swept_low is None and l[c] < box_lo:
            swept_low = c
        if swept_high is None and h[c] > box_hi:
            swept_high = c
        if skip_both_sides and swept_low is not None and swept_high is not None:
            return None
        if c < 2:
            continue
        a = c - 2
        t = bars["close_time"].iat[c]
        if swept_low is not None and a >= swept_low and l[c] - h[a] >= p["fvg_min"]:
            price = float(l[c])
            ref = float(l[:c + 1].min()) if sl_from_session else float(l[a])
            sl = ref - p["sl_offset"]
            return Order(f"{name}:{t:%Y%m%d%H%M}:BUY", t, B, LIMIT, price=price, sl=sl,
                         tp=price + p["tp_r"] * (price - sl), expiry=expiry, be_trigger_r=p["be_r"],
                         reasons=(f"quét đáy hộp {box_lo:.2f}", f"FVG {h[a]:.2f}-{l[c]:.2f}"))
        if swept_high is not None and a >= swept_high and l[a] - h[c] >= p["fvg_min"]:
            price = float(h[c])
            ref = float(h[:c + 1].max()) if sl_from_session else float(h[a])
            sl = ref + p["sl_offset"]
            return Order(f"{name}:{t:%Y%m%d%H%M}:SELL", t, S, LIMIT, price=price, sl=sl,
                         tp=price - p["tp_r"] * (sl - price), expiry=expiry, be_trigger_r=p["be_r"],
                         reasons=(f"quét đỉnh hộp {box_hi:.2f}", f"FVG {h[c]:.2f}-{l[a]:.2f}"))
    return None


def _ny_days(m5: pd.DataFrame, tz: str) -> pd.DatetimeIndex:
    local = pd.DatetimeIndex(m5["time"]).tz_convert(tz)
    return local.normalize().unique()


def _local(day: pd.Timestamp, hhmm: str) -> pd.Timestamp:
    """Giờ địa phương `hhmm` của ngày `day` (đã có tz) → UTC, xử lý DST."""
    naive = day.tz_localize(None) + pd.Timedelta(minutes=minutes(hhmm))
    return naive.tz_localize(day.tz, nonexistent="shift_forward", ambiguous=True).tz_convert("UTC")


def xau08(data: MarketData, p: dict) -> Signals:
    """Hộp 6 nến M5 09:30–09:55 NY; trong 10:00–12:00 NY quét biên + FVG ngược chiều → limit ở mép FVG."""
    m5 = data.frame("M5")
    orders: list[Order] = []
    for day in _ny_days(m5, data.timezone):
        if day.weekday() >= 5:
            continue
        box = _box(m5, _local(day, p["box"][0]), _local(day, p["box"][1]))
        if len(box) < p["box_bars"]:
            continue
        start, end = _local(day, p["window"][0]), _local(day, p["window"][1])
        order = _sweep_fvg_order("xau08", _box(m5, start, end), float(box["high"].max()), float(box["low"].min()),
                                 p, end, sl_from_session=False, skip_both_sides=True)
        if order is not None:
            orders.append(order)
    return Signals(orders, [])


def xau09(data: MarketData, p: dict) -> Signals:
    """Hộp Á 20:00–02:00 NY; trong 02:00–05:00 NY quét biên + FVG ngược chiều → limit; SL ngoài cực trị London."""
    m5 = data.frame("M5")
    orders: list[Order] = []
    for day in _ny_days(m5, data.timezone):
        if day.weekday() >= 5:
            continue
        box = _box(m5, _local(day - pd.Timedelta(days=1), p["box"][0]), _local(day, p["box"][1]))
        if len(box) < p["box_bars"]:
            continue
        start, end = _local(day, p["window"][0]), _local(day, p["window"][1])
        order = _sweep_fvg_order("xau09", _box(m5, start, end), float(box["high"].max()), float(box["low"].min()),
                                 p, end, sl_from_session=True, skip_both_sides=False)
        if order is not None:
            orders.append(order)
    return Signals(orders, [])
