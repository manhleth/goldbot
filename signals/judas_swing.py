"""Setup Judas swing: trong killzone, giá quét đỉnh/đáy range phiên Á (cú lừa ngược bias) → MSS → hồi về FVG."""
from __future__ import annotations

from core.types import Setup
from mtf.context import MarketContext
from signals.ict import in_killzone, sweep_mss_setups

NAME = "judas_swing"


def find(ctx: MarketContext, cfg: dict) -> list[Setup]:
    return sweep_mss_setups(ctx, cfg, NAME, [cfg["ict"]["asian_session"]], sweep_filter=in_killzone(cfg))
