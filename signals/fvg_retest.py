"""Setup: giá hồi về FVG khung setup cùng chiều bias (lần chạm đầu)."""
from __future__ import annotations

from core.types import Direction, Setup, Zone
from mtf.context import MarketContext
from signals.confluence import confluence
from structure.interaction import zone_lifecycle

NAME = "fvg_retest"


def find(ctx: MarketContext, cfg: dict) -> list[Setup]:
    view, direction = ctx.setup_view, ctx.direction
    max_episodes = cfg["fvg"]["max_touch_episodes"]
    setups: list[Setup] = []
    for gap in view.fvgs:
        if gap.direction != direction:
            continue
        if not zone_lifecycle(view.df, gap.index + 1, gap.low, gap.high, direction).is_first_touch(max_episodes):
            continue
        zone = Zone(gap.low, gap.high)
        score, extra = confluence(zone, direction, ctx, cfg)
        setups.append(Setup(
            name=NAME, direction=direction, zone=zone,
            invalidation=gap.low if direction == Direction.BUY else gap.high,
            score=1 + score,
            reasons=(f"FVG {view.tf} {gap.low:.2f}-{gap.high:.2f}", *extra),
            key=f"{NAME}:{view.tf}:{gap.time:%Y%m%d%H%M}",
        ))
    return setups
