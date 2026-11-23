"""Setup: phá trendline ngược bias (sóng hồi) rồi retest đường trong tối đa K nến."""
from __future__ import annotations

import numpy as np

from core.types import Direction, Setup, Zone
from mtf.context import MarketContext
from signals.confluence import confluence
from structure.trendline import first_break, latest_trendline

NAME = "trendline_break_retest"


def find(ctx: MarketContext, cfg: dict) -> list[Setup]:
    view, direction = ctx.setup_view, ctx.direction
    tc = cfg["trendline"]
    df = view.df
    # BUY: phá lên trendline giảm (nối các đỉnh); SELL: phá xuống trendline tăng (nối các đáy)
    line = latest_trendline(df, view.swings, "high" if direction == Direction.BUY else "low", tc["max_pivots"])
    if line is None:
        return []
    brk = first_break(df, line)
    if brk is None or brk.distance < tc["break_atr"] * df["atr"].iat[brk.index]:
        return []
    forming = len(df)  # chỉ số nến khung setup đang hình thành
    if forming - brk.index > tc["retest_max_bars"]:
        return []
    after = np.arange(brk.index + 1, forming)
    closes = df["close"].to_numpy(dtype=float)[after]
    failed = (closes < line.value(after)) if direction == Direction.BUY else (closes > line.value(after))
    if after.size and failed.any():
        return []
    level = float(line.value(forming))
    tol = tc["retest_tolerance_atr"] * view.atr
    zone = Zone(level - tol, level + tol)
    score, extra = confluence(zone, direction, ctx, cfg)
    t1, t2 = df["time"].iat[line.i1], df["time"].iat[line.i2]
    return [Setup(
        name=NAME, direction=direction, zone=zone,
        invalidation=zone.low if direction == Direction.BUY else zone.high,
        score=1 + score,
        reasons=(f"trendline {view.tf} {t1:%m-%d %H:%M}→{t2:%m-%d %H:%M} bị phá tại "
                 f"{df['time'].iat[brk.index]:%m-%d %H:%M}, retest quanh {level:.2f}", *extra),
        key=f"{NAME}:{view.tf}:{t1:%Y%m%d%H%M}:{t2:%Y%m%d%H%M}",
    )]
