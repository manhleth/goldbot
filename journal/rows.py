"""Chuyển đối tượng nghiệp vụ thành dòng journal (dùng chung cho backtest và live)."""
from __future__ import annotations

from collections.abc import Mapping

from core.types import Direction, Signal
from risk.decision import Decision


def bias_label(bias: Mapping[str, Direction]) -> str:
    return ",".join(f"{tf}={d.name}" for tf, d in bias.items())


def signal_row(run_id: str, signal: Signal, decision: Decision) -> dict:
    plan = decision.plan
    setup = signal.setup
    return {
        "run_id": run_id, "time": signal.time, "setup": setup.name, "direction": signal.direction.name,
        "bias": bias_label(signal.bias), "zone_low": setup.zone.low, "zone_high": setup.zone.high,
        "score": setup.score, "trigger": signal.trigger,
        "entry": plan.entry if plan else None, "sl": plan.sl if plan else None,
        "tp1": plan.tp1 if plan else None, "tp2": plan.tp2 if plan else None,
        "rr_tp1": plan.rr_tp1 if plan else None,
        "accepted": int(decision.accepted), "reject_reason": decision.reason, "news": decision.news,
        "reasons": list(setup.reasons), "setup_key": setup.key,
    }
