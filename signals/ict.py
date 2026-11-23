"""Lõi mô hình ICT: quét thanh khoản → phá cấu trúc ngược lại (MSS) bằng xung lực tạo FVG → chờ giá hồi về FVG.

BUY (SELL đối xứng):
1. Nến i quét xuống dưới một mức thanh khoản phía dưới (low[i] < mức), mức đó chưa bị chạm từ lúc hình thành.
   Mức thanh khoản: PDH/PDL, range phiên, swing gần đây, equal highs/lows (theo `ict.sweep_pools`).
2. Trong `mss_max_bars` nến sau, có nến k đóng cửa trên swing high gần nhất hình thành trước nến i (MSS).
3. Trong đoạn i..k+1 có FVG tăng (xung lực); lấy FVG gần MSS nhất làm vùng vào lệnh.
4. Setup còn hiệu lực khi: chưa quá `setup_expiry_bars` nến kể từ MSS, FVG chưa bị phá và đang ở lần chạm đầu,
   (tuỳ chọn) FVG nằm ở nửa discount của dealing range H4.
Invalidation = đáy thấp nhất từ lúc quét tới MSS.
"""
from __future__ import annotations

from collections.abc import Callable

import numpy as np
import pandas as pd

from core.types import Direction, Setup, Zone
from mtf.context import MarketContext
from mtf.view import TimeframeView
from risk.calendar import in_sessions
from signals.confluence import confluence
from structure.fvg import FairValueGap, find_fvgs
from structure.interaction import zone_lifecycle
from structure.liquidity import Pool, liquidity_pools, structural_pools
from structure.swings import Swing, of_kind

SweepFilter = Callable[[pd.Timestamp], bool]


def _in_discount_half(zone: Zone, direction: Direction, ctx: MarketContext, cfg: dict) -> bool:
    """Dealing range = swing high & swing low gần nhất của khung bias; BUY ở nửa dưới, SELL ở nửa trên."""
    view = ctx.views[cfg["timeframes"]["bias"][0]]
    highs, lows = of_kind(view.swings, "high"), of_kind(view.swings, "low")
    if not highs or not lows:
        return False
    equilibrium = (highs[-1].price + lows[-1].price) / 2
    mid = (zone.low + zone.high) / 2
    return mid < equilibrium if direction == Direction.BUY else mid > equilibrium


def _first_sweep(df: pd.DataFrame, pool: Pool, direction: Direction, start: int) -> int | None:
    """Nến đầu tiên (từ lúc mức hình thành) chạm qua mức; None nếu chưa có hoặc chạm trước `start`."""
    begin = pool.available_index
    if begin >= len(df):
        return None
    if direction == Direction.BUY:
        hits = df["low"].to_numpy()[begin:] < pool.price
    else:
        hits = df["high"].to_numpy()[begin:] > pool.price
    if not hits.any():
        return None
    i = begin + int(np.argmax(hits))
    return i if i >= start else None


def _reference_swing(swings: list[Swing], direction: Direction, sweep_index: int) -> Swing | None:
    """Swing ngược phía gần nhất hình thành trước nến quét (BUY: swing high)."""
    kind = "high" if direction == Direction.BUY else "low"
    candidates = [s for s in of_kind(swings, kind) if s.index < sweep_index]
    return candidates[-1] if candidates else None


def _mss_index(df: pd.DataFrame, swing: Swing, direction: Direction, sweep_index: int, max_bars: int) -> int | None:
    closes = df["close"].to_numpy()
    stop = min(len(df), sweep_index + max_bars + 1)
    for k in range(sweep_index + 1, stop):
        if swing.confirmed_index >= k:
            continue
        if (closes[k] > swing.price) if direction == Direction.BUY else (closes[k] < swing.price):
            return k
    return None


def _displacement_fvg(gaps: list[FairValueGap], direction: Direction, sweep_index: int, mss: int,
                      last: int) -> FairValueGap | None:
    found = [g for g in gaps if g.direction == direction and sweep_index + 1 <= g.index <= min(mss + 1, last)]
    return found[-1] if found else None


def _extreme(df: pd.DataFrame, direction: Direction, start: int, stop: int) -> float:
    if direction == Direction.BUY:
        return float(df["low"].to_numpy()[start:stop + 1].min())
    return float(df["high"].to_numpy()[start:stop + 1].max())


def sweep_mss_setups(ctx: MarketContext, cfg: dict, name: str, pool_kinds: list[str],
                     sweep_filter: SweepFilter | None = None) -> list[Setup]:
    view: TimeframeView = ctx.setup_view
    direction = ctx.direction
    ic = cfg["ict"]
    df = view.df
    last = len(df) - 1
    t = df["close_time"].iat[-1]
    kinds = sorted({*pool_kinds, *ic["target_pools"]})
    pools = liquidity_pools(df, t, kinds, cfg["sessions"])
    pools += structural_pools(view.swings, kinds, max(0, last - ic["structure_pool_bars"]),
                              ic["equal_tolerance_atr"] * view.atr)
    entry_side = "low" if direction == Direction.BUY else "high"
    target_side = "high" if direction == Direction.BUY else "low"
    targets = tuple(p.price for p in pools if p.side == target_side)
    sweepable = [p for p in pools if p.side == entry_side and p.kind in pool_kinds]
    gaps = find_fvgs(df, ic["fvg_min_size_atr"], ic["impulse_body_atr"])
    lookback_start = max(0, last - ic["lookback_bars"])
    setups: list[Setup] = []
    used_gaps: set[int] = set()
    for pool in sweepable:
        i = _first_sweep(df, pool, direction, lookback_start)
        if i is None or (sweep_filter is not None and not sweep_filter(df["time"].iat[i])):
            continue
        swing = _reference_swing(view.swings, direction, i)
        if swing is None:
            continue
        k = _mss_index(df, swing, direction, i, ic["mss_max_bars"])
        if k is None or last - k > ic["setup_expiry_bars"]:
            continue
        gap = _displacement_fvg(gaps, direction, i, k, last)
        if gap is None or gap.index in used_gaps:
            continue
        zone = Zone(gap.low, gap.high)
        if not zone_lifecycle(df, gap.index + 1, gap.low, gap.high, direction).is_first_touch(ic["max_touch_episodes"]):
            continue
        if ic["premium_discount"] and not _in_discount_half(zone, direction, ctx, cfg):
            continue
        used_gaps.add(gap.index)
        score, extra = confluence(zone, direction, ctx, cfg)
        times = df["time"]
        setups.append(Setup(
            name=name, direction=direction, zone=zone, invalidation=_extreme(df, direction, i, k),
            score=1 + score,
            reasons=(f"quét {pool.name} {pool.price:.2f} lúc {times.iat[i]:%m-%d %H:%M} UTC",
                     f"MSS: đóng cửa phá swing {swing.price:.2f} lúc {times.iat[k]:%m-%d %H:%M} UTC",
                     f"FVG {view.tf} {gap.low:.2f}-{gap.high:.2f}", *extra),
            key=f"{name}:{pool.name}:{times.iat[i]:%Y%m%d%H%M}",
            targets=targets,
        ))
    return setups


def in_killzone(cfg: dict) -> SweepFilter:
    return lambda ts: in_sessions(ts, cfg["ict"]["killzones"], cfg["sessions"])
