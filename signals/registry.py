"""Danh sách setup; bật/tắt qua config `enabled_setups`."""
from __future__ import annotations

from collections.abc import Callable

from core.config import ConfigError
from core.types import Setup
from mtf.context import MarketContext
from signals import (fvg_retest, judas_swing, range_breakout, sr_flip_retest, sweep_mss_fvg, sweep_reversal,
                     trendline_break_retest)

SetupFinder = Callable[[MarketContext, dict], list[Setup]]

SETUP_FINDERS: dict[str, SetupFinder] = {
    fvg_retest.NAME: fvg_retest.find,
    sr_flip_retest.NAME: sr_flip_retest.find,
    sweep_reversal.NAME: sweep_reversal.find,
    trendline_break_retest.NAME: trendline_break_retest.find,
    sweep_mss_fvg.NAME: sweep_mss_fvg.find,
    judas_swing.NAME: judas_swing.find,
    range_breakout.NAME: range_breakout.find,
}


def enabled_finders(cfg: dict) -> list[SetupFinder]:
    unknown = [name for name in cfg["enabled_setups"] if name not in SETUP_FINDERS]
    if unknown:
        raise ConfigError(f"setup không tồn tại: {unknown}. Có: {sorted(SETUP_FINDERS)}")
    return [SETUP_FINDERS[name] for name in cfg["enabled_setups"]]
