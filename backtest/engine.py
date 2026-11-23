"""Vòng lặp backtest: cùng Analyzer/decide với live, khớp lệnh bằng Simulator."""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from backtest.simulator import SimPosition, Simulator
from core.types import Direction
from journal.rows import bias_label, signal_row
from news.calendar import NewsCalendar
from risk.decision import decide
from risk.guard import AccountSnapshot, Exposure, LossStreak, register_result
from risk.management import must_flatten
from risk.sizing import SymbolSpec
from signals.engine import Analyzer


@dataclass
class BacktestResult:
    signals: list[dict] = field(default_factory=list)
    trades: list[dict] = field(default_factory=list)
    equity: list[dict] = field(default_factory=list)


class Backtester:
    def __init__(self, cfg: dict, frames: dict[str, pd.DataFrame], spec: SymbolSpec, run_id: str,
                 calendar: NewsCalendar) -> None:
        self._cfg = cfg
        self._frames = frames
        self._calendar = calendar
        self._spec = spec
        self._run_id = run_id
        mg, bt = cfg["management"], cfg["backtest"]
        self._trigger_tf = cfg["timeframes"]["trigger"]
        self._trail_tf = mg["trail_tf"]
        self._inval_tf = mg["invalidation_tf"]
        self._default_spread = float(bt["default_spread_points"])
        self._analyzer = Analyzer(cfg)
        self._sim = Simulator(spec, float(bt["slippage_points"]), mg)
        self._balance = float(bt["initial_equity"])
        self._peak = self._balance
        self._day: object = None
        self._day_start = self._balance
        self._streak = LossStreak()
        self._used_keys: set[str] = set()
        self.result = BacktestResult()

    # ---------- vòng lặp ----------
    def run(self, start: pd.Timestamp, end: pd.Timestamp) -> BacktestResult:
        df = self._frames[self._trigger_tf]
        o, h, l, c, spreads = (df[col].to_numpy(dtype=float) for col in ("open", "high", "low", "close", "spread"))
        close_times = df["close_time"].tolist()
        bars = np.flatnonzero(((df["time"] >= start) & (df["time"] < end)).to_numpy())
        trail_closes = set(self._frames[self._trail_tf]["close_time"])
        inval = self._frames[self._inval_tf]
        inval_close = dict(zip(inval["close_time"], inval["close"]))
        mg, sessions = self._cfg["management"], self._cfg["sessions"]
        for i in bars:
            t = close_times[i]
            spread = spreads[i] if spreads[i] > 0 else self._default_spread
            self._roll_day(t, c[i], spread)
            self._record_closed(self._sim.on_bar(o[i], h[i], l[i], t, spread))
            if t in trail_closes:
                view = self._analyzer.view(self._frames, self._trail_tf, t)
                if view is not None:
                    self._sim.trail(view)
            if t in inval_close:
                self._record_closed(self._sim.on_invalidation_close(float(inval_close[t]), t, spread))
            self._record_closed(self._sim.close_where(
                lambda p: must_flatten(p.entry_time, t, mg, sessions), c[i], t, spread, "flat_time"))
            self._update_peak(c[i], spread)
            self._enter(t, c[i], spread)
        if len(bars):
            self._snapshot_equity(close_times[bars[-1]], c[bars[-1]], self._default_spread)
        return self.result

    # ---------- vào lệnh ----------
    def _fill_price(self, direction: Direction, close: float, spread: float) -> float:
        point = self._spec.point
        slip = self._cfg["backtest"]["slippage_points"] * point
        return close + spread * point + slip if direction == Direction.BUY else close - slip

    def _snapshot(self, close: float, spread: float) -> AccountSnapshot:
        exposures = tuple(Exposure(p.direction, p.plan.signal.setup.zone) for p in self._sim.open_positions)
        return AccountSnapshot(self._equity(close, spread), self._day_start, exposures, self._streak)

    def _enter(self, t: pd.Timestamp, close: float, spread: float) -> None:
        ctx, signals = self._analyzer.signals(self._frames, t)
        for signal in sorted(signals, key=lambda s: -s.setup.score):
            if signal.setup.key in self._used_keys:
                continue
            entry = self._fill_price(signal.direction, close, spread)
            decision = decide(signal, ctx, entry, self._snapshot(close, spread), spread, self._spec, self._cfg,
                              self._calendar)
            self.result.signals.append(signal_row(self._run_id, signal, decision))
            if decision.accepted:
                self._sim.open(decision.plan, decision.legs, t, spread, decision.news)
                self._used_keys.add(signal.setup.key)

    # ---------- kết quả & equity ----------
    def _record_closed(self, positions: list[SimPosition]) -> None:
        for pos in positions:
            r = pos.r_multiple()
            pnl = self._spec.money(pos.price_pnl(), 1.0)
            self._balance += pnl
            self._streak = register_result(self._streak, r, pos.exit_time, self._cfg["risk"])
            self.result.trades.append(self._trade_row(pos, r, pnl))
            self._snapshot_equity(pos.exit_time, None, None)

    def _trade_row(self, pos: SimPosition, r: float, pnl: float) -> dict:
        plan, setup = pos.plan, pos.plan.signal.setup
        return {
            "run_id": self._run_id, "setup_key": setup.key, "setup": setup.name, "direction": pos.direction.name,
            "bias": bias_label(plan.signal.bias), "score": setup.score, "entry_time": pos.entry_time,
            "exit_time": pos.exit_time, "entry": plan.entry, "sl": plan.sl, "tp1": plan.tp1, "tp2": plan.tp2,
            "volume": pos.volume, "r_multiple": r, "pnl": pnl, "exit_reason": pos.exit_reason,
            "mae_r": pos.mae / plan.risk, "mfe_r": pos.mfe / plan.risk, "spread_entry": pos.spread_entry,
            "news": pos.news, "reasons": list(setup.reasons),
        }

    def _equity(self, close: float, spread: float) -> float:
        return self._balance + self._sim.floating_money(close, spread)

    def _update_peak(self, close: float, spread: float) -> None:
        self._peak = max(self._peak, self._equity(close, spread))

    def _snapshot_equity(self, t: pd.Timestamp, close: float | None, spread: float | None) -> None:
        equity = self._balance if close is None else self._equity(close, spread)
        self._peak = max(self._peak, equity)
        drawdown = (self._peak - equity) / self._peak * 100 if self._peak > 0 else 0.0
        self.result.equity.append({"run_id": self._run_id, "time": t, "equity": equity, "drawdown_pct": drawdown})

    def _roll_day(self, t: pd.Timestamp, close: float, spread: float) -> None:
        day = t.date()
        if day != self._day:
            self._day = day
            self._day_start = self._equity(close, spread)
            self._snapshot_equity(t, close, spread)
