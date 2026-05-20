import pandas as pd

def swing_points(df, lb=5):
    highs, lows = [], []
    for i in range(lb, len(df) - lb):
        w = df.iloc[i-lb:i+lb+1]
        if df["high"].iloc[i] == w["high"].max():
            highs.append({"price": round(df["high"].iloc[i],2),
                          "date": str(df["datetime"].iloc[i].date())})
        if df["low"].iloc[i] == w["low"].min():
            lows.append({"price": round(df["low"].iloc[i],2),
                         "date": str(df["datetime"].iloc[i].date())})
    return highs[-4:], lows[-4:]

def order_blocks(df, n=6):
    obs = []
    for i in range(1, len(df)-1):
        c, nx = df.iloc[i], df.iloc[i+1]
        body_ratio = abs(nx["close"]-nx["open"]) / max(nx["high"]-nx["low"], 0.1)
        if body_ratio < 0.55:
            continue
        if c["close"] < c["open"] and nx["close"] > nx["open"]:
            obs.append({"type":"bullish","high":round(c["high"],2),
                        "low":round(c["low"],2),"mid":round((c["high"]+c["low"])/2,2),
                        "date":str(c["datetime"].date())})
        if c["close"] > c["open"] and nx["close"] < nx["open"]:
            obs.append({"type":"bearish","high":round(c["high"],2),
                        "low":round(c["low"],2),"mid":round((c["high"]+c["low"])/2,2),
                        "date":str(c["datetime"].date())})
    return obs[-n:]

def fair_value_gaps(df, min_gap=2.5):
    fvgs = []
    for i in range(1, len(df)-1):
        p, c, n = df.iloc[i-1], df.iloc[i], df.iloc[i+1]
        if n["low"] > p["high"] and (n["low"]-p["high"]) >= min_gap:
            fvgs.append({"type":"bullish","upper":round(n["low"],2),
                         "lower":round(p["high"],2),"mid":round((n["low"]+p["high"])/2,2),
                         "date":str(c["datetime"].date())})
        if n["high"] < p["low"] and (p["low"]-n["high"]) >= min_gap:
            fvgs.append({"type":"bearish","upper":round(p["low"],2),
                         "lower":round(n["high"],2),"mid":round((p["low"]+n["high"])/2,2),
                         "date":str(c["datetime"].date())})
    return fvgs[-8:]

def liquidity_levels(df, tol=1.5):
    eq_h, eq_l = [], []
    highs = df["high"].values
    lows  = df["low"].values
    for i in range(len(df)-1):
        for j in range(i+1, min(i+15, len(df))):
            if abs(highs[i]-highs[j]) <= tol:
                eq_h.append(round((highs[i]+highs[j])/2, 2))
            if abs(lows[i]-lows[j]) <= tol:
                eq_l.append(round((lows[i]+lows[j])/2, 2))
    current = df["close"].iloc[-1]
    eq_h = sorted(set(eq_h), key=lambda x: abs(x-current))[:4]
    eq_l = sorted(set(eq_l), key=lambda x: abs(x-current))[:4]
    return sorted(eq_h, reverse=True), sorted(eq_l, reverse=True)

def equilibrium(df, lookback=20):
    hi = df["high"].tail(lookback).max()
    lo = df["low"].tail(lookback).min()
    eq = (hi + lo) / 2
    return {
        "swing_high":    round(hi, 2),
        "swing_low":     round(lo, 2),
        "equilibrium":   round(eq, 2),
        "premium_zone":  round((hi+eq)/2, 2),
        "discount_zone": round((lo+eq)/2, 2),
    }

def market_structure(df):
    highs, lows = swing_points(df)
    if len(highs) < 2 or len(lows) < 2:
        return "RANGING"
    hh = highs[-1]["price"] > highs[-2]["price"]
    hl = lows[-1]["price"]  > lows[-2]["price"]
    lh = highs[-1]["price"] < highs[-2]["price"]
    ll = lows[-1]["price"]  < lows[-2]["price"]
    if hh and hl: return "BULLISH"
    if lh and ll: return "BEARISH"
    return "RANGING"

def build_context(tfs: dict) -> dict:
    daily  = tfs["daily"]
    h4     = tfs["h4"]
    weekly = tfs["weekly"]

    d_sh,  d_sl  = swing_points(daily)
    w_sh,  w_sl  = swing_points(weekly, lb=3)
    h4_sh, h4_sl = swing_points(h4)

    latest = daily.iloc[-1]
    prev   = daily.iloc[-2]

    return {
        "latest_candle": {
            "date":        str(latest["datetime"].date()),
            "open":        round(latest["open"],2),
            "high":        round(latest["high"],2),
            "low":         round(latest["low"],2),
            "close":       round(latest["close"],2),
            "type":        "bullish" if latest["close"] > latest["open"] else "bearish",
            "body_size":   round(abs(latest["close"]-latest["open"]),2),
            "upper_wick":  round(latest["high"] - max(latest["close"],latest["open"]),2),
            "lower_wick":  round(min(latest["close"],latest["open"]) - latest["low"],2),
            "range":       round(latest["high"]-latest["low"],2),
        },
        "prev_candle": {
            "close": round(prev["close"],2),
            "high":  round(prev["high"],2),
            "low":   round(prev["low"],2),
        },
        "structure": {
            "weekly": market_structure(weekly),
            "daily":  market_structure(daily),
            "h4":     market_structure(h4),
        },
        "swing_points": {
            "weekly": {"highs": w_sh, "lows": w_sl},
            "daily":  {"highs": d_sh, "lows": d_sl},
            "h4":     {"highs": h4_sh,"lows": h4_sl},
        },
        "order_blocks": {
            "daily": order_blocks(daily, 6),
            "h4":    order_blocks(h4, 8),
        },
        "fvg": {
            "daily": fair_value_gaps(daily),
            "h4":    fair_value_gaps(h4),
        },
        "liquidity": {
            "equal_highs": liquidity_levels(daily)[0],
            "equal_lows":  liquidity_levels(daily)[1],
        },
        "equilibrium":    equilibrium(daily),
        "h4_equilibrium": equilibrium(h4),
    }