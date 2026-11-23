"""Breakout range tích lũy theo xu hướng khung lớn, vào lệnh khi giá hồi về FVG / order block của sóng phá.

BUY (SELL đối xứng), trên khung setup (H1):
1. Range: chuỗi >= `min_bars` nến liền trước nến phá, cao - thấp <= `max_height_atr` × ATR.
   Lấy range dài nhất (tối đa `max_bars`) còn thoả điều kiện.
2. Nến phá b: nến tăng đóng cửa trên đỉnh range, thân >= `breakout_body_atr` × ATR, chiều = xu hướng khung bias.
3. Vùng vào lệnh (theo `zones`):
   - fvg: FVG tăng hình thành trong sóng phá (c3 nằm trong b .. b + `leg_bars`).
   - order_block: nến giảm cuối cùng trước nến phá (tìm lùi tối đa `ob_search_bars` nến).
4. Setup còn hiệu lực khi: chưa quá `setup_expiry_bars` nến kể từ nến phá, chưa có nến đóng cửa dưới invalidation,
   vùng chưa bị phá và đang ở lần chạm đầu.
Invalidation = thấp hơn giữa mép dưới vùng và giữa range (breakout thất bại khi giá đóng cửa sâu lại vào range).
Mục tiêu = đỉnh range + `measured_move` × chiều cao range.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from core.types import Direction, Setup, Zone
from mtf.context import MarketContext
from signals.confluence import confluence
from structure.fvg import find_fvgs
from structure.interaction import zone_lifecycle

NAME = "range_breakout"


@dataclass(frozen=True, slots=True)
class Breakout:
    start: int  # nến đầu range
    index: int  # nến phá
    low: float
    high: float

    @property
    def height(self) -> float:
        return self.high - self.low

    @property
    def mid(self) -> float:
        return (self.high + self.low) / 2


@dataclass(frozen=True, slots=True)
class EntryZone:
    kind: str
    zone: Zone
    index: int  # nến mà vùng được biết (để xét vòng đời từ nến sau)


def _range_before(h: np.ndarray, l: np.ndarray, a: np.ndarray, b: int, rc: dict) -> tuple[int, float, float] | None:
    """Range dài nhất kết thúc ở nến b-1 còn thoả giới hạn chiều cao; None nếu ngắn hơn `min_bars`."""
    limit = rc["max_height_atr"] * a[b - 1]
    best = None
    hi, lo = -np.inf, np.inf
    for length in range(1, min(rc["max_bars"], b) + 1):
        j = b - length
        hi, lo = max(hi, h[j]), min(lo, l[j])
        if hi - lo > limit:
            break
        if length >= rc["min_bars"]:
            best = (j, float(lo), float(hi))
    return best


def find_breakouts(df, direction: Direction, rc: dict) -> list[Breakout]:
    """Các nến phá range theo `direction` trong `lookback_bars` nến gần nhất."""
    o, h, l, c, a = (df[col].to_numpy(dtype=float) for col in ("open", "high", "low", "close", "atr"))
    last = len(df) - 1
    out: list[Breakout] = []
    for b in range(max(rc["min_bars"], last - rc["lookback_bars"]), last + 1):
        body = (c[b] - o[b]) * direction
        if not body >= rc["breakout_body_atr"] * a[b]:
            continue
        found = _range_before(h, l, a, b, rc)
        if found is None:
            continue
        start, lo, hi = found
        if (c[b] > hi) if direction == Direction.BUY else (c[b] < lo):
            out.append(Breakout(start, b, lo, hi))
    return out


def _entry_zones(df, brk: Breakout, direction: Direction, rc: dict, gaps) -> list[EntryZone]:
    last = len(df) - 1
    zones: list[EntryZone] = []
    if "fvg" in rc["zones"]:
        stop = min(brk.index + rc["leg_bars"], last)
        zones += [EntryZone("fvg", Zone(g.low, g.high), g.index) for g in gaps
                  if g.direction == direction and brk.index <= g.index <= stop]
    if "order_block" in rc["zones"]:
        o, c = df["open"].to_numpy(dtype=float), df["close"].to_numpy(dtype=float)
        for j in range(brk.index - 1, max(-1, brk.index - 1 - rc["ob_search_bars"]), -1):
            if (c[j] - o[j]) * direction < 0:
                zones.append(EntryZone("order_block", Zone(float(df["low"].iat[j]), float(df["high"].iat[j])),
                                       brk.index))
                break
    return zones


def _failed(df, brk: Breakout, invalidation: float, direction: Direction) -> bool:
    closes = df["close"].to_numpy(dtype=float)[brk.index + 1:]
    return bool(((invalidation - closes) * direction > 0).any())


def find(ctx: MarketContext, cfg: dict) -> list[Setup]:
    direction = ctx.direction
    if direction == Direction.NEUTRAL:
        return []
    rc = cfg["range_breakout"]
    view = ctx.setup_view
    df = view.df
    last = len(df) - 1
    gaps = find_fvgs(df, rc["fvg_min_size_atr"], rc["impulse_body_atr"])
    times = df["time"]
    setups: list[Setup] = []
    seen: set[tuple[float, float]] = set()
    for brk in find_breakouts(df, direction, rc):
        if last - brk.index > rc["setup_expiry_bars"]:
            continue
        edge = brk.high if direction == Direction.BUY else brk.low
        target = edge + direction * rc["measured_move"] * brk.height
        for ez in _entry_zones(df, brk, direction, rc, gaps):
            zone = ez.zone
            far_edge = zone.low if direction == Direction.BUY else zone.high
            invalidation = (min if direction == Direction.BUY else max)(far_edge, brk.mid)
            if (zone.low, zone.high) in seen or _failed(df, brk, invalidation, direction):
                continue
            life = zone_lifecycle(df, ez.index + 1, zone.low, zone.high, direction)
            if not life.is_first_touch(rc["max_touch_episodes"]):
                continue
            seen.add((zone.low, zone.high))
            score, extra = confluence(zone, direction, ctx, cfg)
            setups.append(Setup(
                name=NAME, direction=direction, zone=zone, invalidation=invalidation, score=1 + score,
                reasons=(f"range {view.tf} {brk.index - brk.start} nến {brk.low:.2f}-{brk.high:.2f}",
                         f"phá range lúc {times.iat[brk.index]:%m-%d %H:%M} UTC",
                         f"{ez.kind} {zone.low:.2f}-{zone.high:.2f}", *extra),
                key=f"{NAME}:{ez.kind}:{times.iat[brk.index]:%Y%m%d%H%M}:{ez.index}",
                targets=(target,),
            ))
    return setups
