"""Phương pháp dựa trên chỉ báo: XAU-01, 02, 03, 04, 10, 11, 12. Ký hiệu [1] = nến vừa đóng, [2] = nến trước."""
from __future__ import annotations

import numpy as np
import pandas as pd

from core.types import Direction
from playbook import indicators as ind
from playbook.common import MarketData, finite, market_orders, previous, utc_hours_mask
from playbook.orders import EXIT, Event, Signals

B, S = Direction.BUY, Direction.SELL


def _atr_orders(name: str, df: pd.DataFrame, buy, sell, atr: pd.Series, p: dict, why) -> list:
    a = atr.to_numpy(float)
    return market_orders(name, df, buy, sell,
                         lambda i, d: {"sl_dist": p["sl_atr"] * a[i], "tp_dist": p["tp_atr"] * a[i]}, why)


def xau01(data: MarketData, p: dict) -> Signals:
    """H1: EMA21 > EMA55 > EMA200 (BUY); nến [2] đóng dưới EMA21, nến [1] đóng lại trên EMA21."""
    df = data.frame(p["tf"])
    c = df["close"]
    e1, e2, e3 = (ind.ema(c, n) for n in p["ema"])
    atr = ind.atr(df, p["atr"])
    ok = utc_hours_mask(df["close_time"], p["hours"], p["skip_friday"]) & finite(e3, atr)
    buy = ok & (e1 > e2) & (e2 > e3) & (previous(c) < previous(e1)) & (c > e1)
    sell = ok & (e1 < e2) & (e2 < e3) & (previous(c) > previous(e1)) & (c < e1)
    return Signals(_atr_orders("xau01", df, buy, sell, atr, p, lambda i, d: (f"hồi EMA{p['ema'][0]} {d.name}",)), [])


def xau02(data: MarketData, p: dict) -> Signals:
    """H4: close & EMA50 trên EMA200 (BUY); MACD main cắt lên signal giữa [2] và [1]."""
    df = data.frame(p["tf"])
    c = df["close"]
    fast, slow = ind.ema(c, p["ema"][0]), ind.ema(c, p["ema"][1])
    main, sig = ind.macd(c, *p["macd"])
    atr = ind.atr(df, p["atr"])
    ok = utc_hours_mask(df["close_time"], p["hours"], p["skip_friday"]) & finite(slow, sig, atr)
    up = (previous(main) < previous(sig)) & (main > sig)
    down = (previous(main) > previous(sig)) & (main < sig)
    buy = ok & (c > slow) & (fast > slow) & up
    sell = ok & (c < slow) & (fast < slow) & down
    return Signals(_atr_orders("xau02", df, buy, sell, atr, p, lambda i, d: (f"MACD cắt {d.name} theo EMA200",)), [])


def xau03(data: MarketData, p: dict) -> Signals:
    """H1: râu chạm ngoài Bollinger, close đóng trở vào, RSI cực đoan. TP = dải giữa (dự phòng: khoảng cố định)."""
    df = data.frame(p["tf"])
    lower, mid, upper = ind.bollinger(df["close"], *p["bollinger"])
    r = ind.rsi(df["close"], p["rsi"])
    ok = utc_hours_mask(df["close_time"], p["hours"], p["skip_friday"]) & finite(mid, r)
    buy = ok & (df["low"] <= lower) & (df["close"] > lower) & (r < p["rsi_buy_below"])
    sell = ok & (df["high"] >= upper) & (df["close"] < upper) & (r > p["rsi_sell_above"])
    m = mid.to_numpy(float)
    orders = market_orders("xau03", df, buy, sell, lambda i, d: {
        "sl_dist": p["sl"], "tp": m[i], "tp_dist": p["tp_fallback"],
        "be_trigger": p["be_trigger"], "be_offset": p["be_offset"]}, lambda i, d: (f"Bollinger quay về {d.name}",))
    return Signals(orders, [])


def xau04(data: MarketData, p: dict) -> Signals:
    """M15: Stochastic cắt ở vùng cực, lọc EMA21, giá gần S1/S2 (BUY) hoặc R1/R2 (SELL) của pivot ngày UTC trước."""
    df = data.frame(p["tf"])
    day = data.frame("D1")
    piv = ind.pivots(day).assign(close_time=day["close_time"])
    levels = pd.merge_asof(df[["close_time"]], piv, on="close_time", direction="backward")  # pivot ngày đã đóng
    k, dline = ind.stochastic(df, *p["stochastic"])
    e = ind.ema(df["close"], p["ema"])
    c = df["close"]
    ok = utc_hours_mask(df["close_time"], p["hours"], p["skip_friday"]) & finite(k, dline, e, levels["p"])
    near = p["max_distance"]
    near_support = ((c - levels["s1"]).abs() <= near) | ((c - levels["s2"]).abs() <= near)
    near_resist = ((c - levels["r1"]).abs() <= near) | ((c - levels["r2"]).abs() <= near)
    buy = ok & (previous(k) < previous(dline)) & (k > dline) & (k < p["k_buy_below"]) & (c > e) & near_support
    sell = ok & (previous(k) > previous(dline)) & (k < dline) & (k > p["k_sell_above"]) & (c < e) & near_resist
    orders = market_orders("xau04", df, buy, sell, lambda i, d: {
        "sl_dist": p["sl"], "tp_dist": p["tp2"], "tp1_dist": p["tp1"], "tp1_fraction": p["tp1_fraction"],
        "be_offset": p["be_offset"]}, lambda i, d: (f"pivot + Stochastic {d.name}",))
    return Signals(orders, [])


def _daily_trend(data: MarketData, df: pd.DataFrame, period: int) -> np.ndarray:
    """+1 / -1 theo close nến D1 đã đóng so với EMA(period); 0 khi chưa đủ dữ liệu."""
    day = data.frame("D1")
    trend = np.sign(day["close"] - ind.ema(day["close"], period)).where(day.index >= period, 0)
    merged = pd.merge_asof(df[["close_time"]], pd.DataFrame({"close_time": day["close_time"], "trend": trend}),
                           on="close_time", direction="backward")
    return merged["trend"].fillna(0).to_numpy()


def _m15_atr_build(atr: np.ndarray, p: dict):
    return lambda i, d: {"sl_dist": max(p["sl_atr"] * atr[i], p["sl_min"]), "tp_dist": p["tp_atr"] * atr[i],
                         "max_spread": p["max_spread"]}


def xau10(data: MarketData, p: dict) -> Signals:
    """M15 thuận D1 (close vs EMA50): EMA9 > EMA21, nến chạm EMA9 rồi đóng trên EMA9 và là nến tăng (BUY)."""
    df = data.frame(p["tf"])
    trend = _daily_trend(data, df, p["daily_ema"])
    fast, slow = ind.ema(df["close"], p["ema"][0]), ind.ema(df["close"], p["ema"][1])
    atr = ind.atr(df, p["atr"])
    o, h, l, c = df["open"], df["high"], df["low"], df["close"]
    ok = utc_hours_mask(df["close_time"], p["hours"], p["skip_friday"]) & finite(slow, atr)
    buy = ok & (trend > 0) & (fast > slow) & (l <= fast) & (c > fast) & (c > o)
    sell = ok & (trend < 0) & (fast < slow) & (h >= fast) & (c < fast) & (c < o)
    orders = market_orders("xau10", df, buy, sell, _m15_atr_build(atr.to_numpy(float), p),
                           lambda i, d: (f"hồi EMA{p['ema'][0]} thuận D1 {d.name}",))
    return Signals(orders, [])


def xau11(data: MarketData, p: dict) -> Signals:
    """M15 thuận D1: Stochastic ở [2] trong vùng cực và dưới/trên D, ở [1] cắt ngược lại nhưng chưa rời vùng."""
    df = data.frame(p["tf"])
    trend = _daily_trend(data, df, p["daily_ema"])
    k, dline = ind.stochastic(df, *p["stochastic"])
    atr = ind.atr(df, p["atr"])
    pk, pd_ = previous(k), previous(dline)
    ok = utc_hours_mask(df["close_time"], p["hours"], p["skip_friday"]) & finite(k, dline, atr)
    buy = ok & (trend > 0) & (pk < pd_) & (pk < p["prev_buy_below"]) & (k > dline) & (k < p["now_buy_below"])
    sell = ok & (trend < 0) & (pk > pd_) & (pk > p["prev_sell_above"]) & (k < dline) & (k > p["now_sell_above"])
    orders = market_orders("xau11", df, buy, sell, _m15_atr_build(atr.to_numpy(float), p),
                           lambda i, d: (f"Stochastic thuận D1 {d.name}",))
    return Signals(orders, [])


def xau12(data: MarketData, p: dict) -> Signals:
    """D1 Donchian: vào khi close phá kênh `entry` nến; thoát khi close phá kênh `exit` nến ngược chiều (hoặc SL)."""
    df = data.frame(p["tf"])
    hi_in, lo_in = ind.donchian(df, p["entry"])
    hi_out, lo_out = ind.donchian(df, p["exit"])
    atr = ind.atr(df, p["atr"])
    c = df["close"]
    ok = finite(hi_in, atr)
    buy, sell = ok & (c > hi_in), ok & (c < lo_in)
    a = atr.to_numpy(float)
    orders = market_orders("xau12", df, buy, sell, lambda i, d: {"sl_dist": p["sl_atr"] * a[i]},
                           lambda i, d: (f"Donchian {p['entry']} {d.name}",))
    times = df["close_time"]
    events = [Event(times.iat[i], B, (EXIT,)) for i in np.flatnonzero((c < lo_out).to_numpy())]
    events += [Event(times.iat[i], S, (EXIT,)) for i in np.flatnonzero((c > hi_out).to_numpy())]
    return Signals(orders, events)
