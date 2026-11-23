"""Chuyển kết quả phân tích sang JSON cho giao diện (thời gian = giây Unix UTC)."""
from __future__ import annotations

import math

import pandas as pd

from core.types import Direction
from mtf.view import TimeframeView
from signals.engine import Analyzer
from structure.interaction import zone_lifecycle

_MAX_SWINGS = 40


def ts(value) -> int:
    return int(pd.Timestamp(value).timestamp())


def num(value) -> float | None:
    value = float(value)
    return None if math.isnan(value) else value


def candles_payload(df: pd.DataFrame, ema_periods: list[int], bars: int) -> dict:
    tail = df.tail(bars)
    times = [ts(t) for t in tail["time"]]
    candles = [{"time": t, "open": o, "high": h, "low": l, "close": c}
               for t, o, h, l, c in zip(times, tail["open"], tail["high"], tail["low"], tail["close"])]
    ema = {str(p): [{"time": t, "value": num(v)} for t, v in zip(times, tail[f"ema_{p}"]) if not math.isnan(v)]
           for p in ema_periods}
    return {"candles": candles, "ema": ema}


def _overlays(view: TimeframeView) -> dict:
    df = view.df
    times = df["time"]
    fvgs = [{"direction": g.direction.name, "low": g.low, "high": g.high, "start": ts(times.iat[g.index])}
            for g in view.fvgs
            if not zone_lifecycle(df, g.index + 1, g.low, g.high, g.direction).invalidated]
    blocks = [{"direction": b.direction.name, "low": b.low, "high": b.high, "start": ts(times.iat[b.index])}
              for b in view.order_blocks
              if not zone_lifecycle(df, b.break_index + 1, b.low, b.high, b.direction).invalidated]
    zones = [{"low": z.low, "high": z.high, "touches": z.touches, "start": ts(times.iat[z.first_index])}
             for z in view.sr_zones]
    swings = [{"time": ts(s.time), "price": s.price, "kind": s.kind} for s in view.swings[-_MAX_SWINGS:]]
    return {"sr_zones": zones, "fvgs": fvgs, "order_blocks": blocks, "swings": swings, "atr": num(view.atr)}


def analysis_payload(frames: dict[str, pd.DataFrame], cfg: dict, tf: str) -> dict:
    analyzer = Analyzer(cfg)
    trigger_tf = cfg["timeframes"]["trigger"]
    t = frames[trigger_tf]["close_time"].iat[-1]
    ctx = analyzer.context(frames, t)
    if ctx is None:
        return {"ready": False, "message": "Chưa đủ dữ liệu để tính chỉ báo."}
    setups = analyzer.setups(ctx) if ctx.direction != Direction.NEUTRAL else []
    _, signals = analyzer.signals(frames, t)
    view = analyzer.view(frames, tf, t)
    return {
        "ready": True, "time": ts(t), "direction": ctx.direction.name,
        "biases": {k: {"direction": b.direction.name, "score": b.score, "reasons": list(b.reasons)}
                   for k, b in ctx.biases.items()},
        "setups": [{"name": s.name, "direction": s.direction.name, "low": s.zone.low, "high": s.zone.high,
                    "invalidation": s.invalidation, "score": s.score, "reasons": list(s.reasons), "key": s.key}
                   for s in setups],
        "signals": [{"setup": s.setup.name, "direction": s.direction.name, "trigger": s.trigger, "close": s.close,
                     "key": s.setup.key} for s in signals],
        "overlays": _overlays(view) if view is not None else None,
    }
