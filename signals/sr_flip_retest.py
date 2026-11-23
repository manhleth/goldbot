"""Setup: vùng S/R bị phá theo chiều bias, giá quay lại retest lần đầu (đổi vai)."""
from __future__ import annotations

from core.types import Direction, Setup
from mtf.context import MarketContext
from signals.confluence import confluence
from structure.interaction import zone_lifecycle
from structure.zones import last_flip_break

NAME = "sr_flip_retest"


def find(ctx: MarketContext, cfg: dict) -> list[Setup]:
    view, direction = ctx.setup_view, ctx.direction
    fc = cfg["sr_flip"]
    last = len(view.df) - 1
    setups: list[Setup] = []
    for sr in view.sr_zones:
        k = last_flip_break(view.df, sr, direction)
        if k is None or last - k > fc["max_bars_since_break"]:
            continue
        if not zone_lifecycle(view.df, k + 1, sr.low, sr.high, direction).is_first_touch(fc["max_touch_episodes"]):
            continue
        score, extra = confluence(sr.zone, direction, ctx, cfg)
        setups.append(Setup(
            name=NAME, direction=direction, zone=sr.zone,
            invalidation=sr.low if direction == Direction.BUY else sr.high,
            score=1 + score,
            reasons=(f"S/R {view.tf} {sr.low:.2f}-{sr.high:.2f} ({sr.touches} chạm) bị phá tại "
                     f"{view.df['time'].iat[k]:%Y-%m-%d %H:%M}", *extra),
            key=f"{NAME}:{view.tf}:{sr.low:.2f}:{view.df['time'].iat[k]:%Y%m%d%H%M}",
        ))
    return setups
