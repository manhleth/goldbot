"""Điểm cộng confluence cho một vùng setup."""
from __future__ import annotations

from core.types import Direction, Zone
from mtf.context import MarketContext
from structure.interaction import zone_lifecycle
from structure.sweep import find_sweep
from structure.zones import last_flip_break


def confluence(zone: Zone, direction: Direction, ctx: MarketContext, cfg: dict) -> tuple[int, tuple[str, ...]]:
    view = ctx.setup_view
    reasons: list[str] = []
    if any(z.zone.overlaps(zone.low, zone.high) and last_flip_break(view.df, z, direction) is not None
           for z in view.sr_zones):
        reasons.append("trùng vùng S/R đổi vai")
    higher = ctx.views.get(cfg["confluence"]["higher_tf"])
    if higher is not None and any(
            g.direction == direction and g.low <= zone.low and zone.high <= g.high
            and not zone_lifecycle(higher.df, g.index + 1, g.low, g.high, direction).invalidated
            for g in higher.fvgs):
        reasons.append(f"nằm trong FVG {higher.tf}")
    if any(b.direction == direction and zone.overlaps(b.low, b.high) for b in view.order_blocks):
        reasons.append("trùng order block")
    if find_sweep(view.df, view.swings, direction, cfg["sweep"]["max_age_bars"]) is not None:
        reasons.append("có sweep thanh khoản gần đây")
    return len(reasons), tuple(reasons)
