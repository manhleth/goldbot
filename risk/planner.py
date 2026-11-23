"""Tính SL / TP1 / TP2 từ tín hiệu và cấu trúc."""
from __future__ import annotations

from core.types import Direction, Rejected, Signal, TradePlan
from mtf.context import MarketContext
from mtf.view import TimeframeView


def sl_reference(signal: Signal, anchor: str) -> float:
    """Mốc cấu trúc đặt SL phía sau: invalidation (vd đỉnh/đáy cú quét) hoặc mép xa của vùng setup (vd FVG)."""
    if anchor == "zone":
        zone = signal.setup.zone
        return zone.low if signal.direction == Direction.BUY else zone.high
    return signal.setup.invalidation


def stop_loss(signal: Signal, atr: float, buffer_atr: float, anchor: str = "invalidation") -> float:
    """Ngoài mốc tham chiếu và nến trigger, cộng đệm ATR."""
    d = signal.direction
    ref = (min if d == Direction.BUY else max)(sl_reference(signal, anchor), signal.trigger_extreme)
    return ref - d * buffer_atr * atr


def target_levels(views: list[TimeframeView], direction: Direction, beyond: float,
                  extra: tuple[float, ...] = ()) -> list[float]:
    """Mức đối diện nằm sau `beyond`, gần nhất trước. BUY: cạnh dưới vùng S/R, swing high phía trên, và `extra`."""
    edge_kind = "high" if direction == Direction.BUY else "low"
    levels: set[float] = set(extra)
    for view in views:
        levels.update(z.low if direction == Direction.BUY else z.high for z in view.sr_zones)
        levels.update(s.price for s in view.swings if s.kind == edge_kind)
    return sorted((p for p in levels if (p - beyond) * direction > 0), key=lambda p: (p - beyond) * direction)


def pick_tp1(entry: float, risk: float, direction: Direction, levels: list[float], risk_cfg: dict) -> float | None:
    if risk_cfg["tp1_mode"] == "fixed_rr":
        return entry + direction * risk_cfg["tp1_rr"] * risk
    min_rr = risk_cfg["min_rr_tp1"]

    def rr(price: float) -> float:
        return (price - entry) * direction / risk

    if levels:
        if risk_cfg["tp1_mode"] == "nearest":
            return levels[0] if rr(levels[0]) >= min_rr else None
        return next((p for p in levels if rr(p) >= min_rr), None)
    fallback = risk_cfg.get("tp1_fallback_rr")
    return entry + direction * fallback * risk if fallback else None


def build_plan(signal: Signal, entry: float, ctx: MarketContext, cfg: dict) -> TradePlan | Rejected:
    rc = cfg["risk"]
    d = signal.direction
    atr = ctx.setup_view.atr
    if not atr > 0:
        return Rejected("atr_unavailable")
    sl = stop_loss(signal, atr, rc["sl_buffer_atr"], rc["sl_anchor"])
    risk = (entry - sl) * d
    if risk <= 0:
        return Rejected("sl_wrong_side")
    if risk > rc["sl_max_atr"] * atr:
        return Rejected("sl_too_far")
    levels = target_levels(ctx.views_for(rc["tp1_timeframes"]), d, entry, signal.setup.targets)
    tp1 = pick_tp1(entry, risk, d, levels, rc)
    if tp1 is None:
        return Rejected("tp1_rr_too_low" if levels else "no_tp1_target")
    tp2_levels = target_levels(ctx.views_for(rc["tp2_timeframes"]), d, tp1, signal.setup.targets)
    return TradePlan(signal, entry, sl, tp1, tp2_levels[0] if tp2_levels else None)
