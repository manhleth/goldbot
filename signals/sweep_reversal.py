"""Setup: quét thanh khoản tại vùng S/R rồi đóng cửa quay lại, cùng chiều bias."""
from __future__ import annotations

from core.types import Direction, Setup, Zone
from mtf.context import MarketContext
from signals.confluence import confluence
from structure.interaction import zone_lifecycle
from structure.sweep import Sweep, find_sweep

NAME = "sweep_reversal"


def _at_sr_zone(sweep: Sweep, ctx: MarketContext, cfg: dict) -> bool:
    sc = cfg["sweep"]
    for view in ctx.views_for(sc["zone_timeframes"]):
        tol = sc["zone_tolerance_atr"] * view.atr
        if any(z.low - tol <= sweep.level <= z.high + tol for z in view.sr_zones):
            return True
    return False


def find(ctx: MarketContext, cfg: dict) -> list[Setup]:
    view, direction = ctx.setup_view, ctx.direction
    sc = cfg["sweep"]
    sweep = find_sweep(view.df, view.swings, direction, sc["max_age_bars"])
    if sweep is None or (sc["require_sr_zone"] and not _at_sr_zone(sweep, ctx, cfg)):
        return []
    pad = sc["entry_zone_atr"] * view.atr
    if direction == Direction.BUY:
        zone = Zone(sweep.extreme, sweep.level + pad)
    else:
        zone = Zone(sweep.level - pad, sweep.extreme)
    if zone_lifecycle(view.df, sweep.index + 1, zone.low, zone.high, direction).invalidated:
        return []
    score, extra = confluence(zone, direction, ctx, cfg)
    sweep_time = view.df["time"].iat[sweep.index]
    return [Setup(
        name=NAME, direction=direction, zone=zone, invalidation=sweep.extreme,
        score=1 + score,
        reasons=(f"sweep {view.tf} mức {sweep.level:.2f}, wick {sweep.extreme:.2f}", *extra),
        key=f"{NAME}:{view.tf}:{sweep_time:%Y%m%d%H%M}",
    )]
