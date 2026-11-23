"""Setup ICT 2022: quét PDH/PDL hoặc range phiên London → MSS → hồi về FVG."""
from __future__ import annotations

from core.types import Setup
from mtf.context import MarketContext
from signals.ict import sweep_mss_setups

NAME = "sweep_mss_fvg"


def find(ctx: MarketContext, cfg: dict) -> list[Setup]:
    return sweep_mss_setups(ctx, cfg, NAME, cfg["ict"]["sweep_pools"])
