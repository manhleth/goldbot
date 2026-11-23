"""Vòng lặp live-demo: mỗi khi nến khung vào lệnh đóng → đồng bộ lệnh, quản lý, tìm tín hiệu mới."""
from __future__ import annotations

import logging
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pandas as pd

from core.config import timeframes
from core.timeframes import tf_delta
from core.types import Direction, TradePlan
from data.mt5_source import MT5Source
from execution.live_store import LiveStore
from execution.mt5_broker import BrokerError, DemoAccountRequired, MT5Broker
from journal.db import Journal
from journal.rows import bias_label, signal_row
from news.calendar import build_calendar
from news.store import NewsStore
from risk.decision import Decision, decide
from risk.guard import AccountSnapshot, register_result
from risk.management import breakeven_due, breaks_invalidation, improves, must_flatten, trail_stop
from signals.engine import Analyzer
from structure.indicators import enrich

log = logging.getLogger(__name__)

SETUP_ABBR = {"fvg_retest": "FVG", "sr_flip_retest": "SRF", "sweep_reversal": "SWP", "trendline_break_retest": "TLB",
              "sweep_mss_fvg": "MSS", "judas_swing": "JDS", "range_breakout": "RBO"}


def shutdown_file(root: Path) -> Path:
    """File yêu cầu bot dừng êm (giao diện web tạo file này)."""
    return root / "run" / "bot.shutdown"


def seconds_until_next_close(now: pd.Timestamp, tf: str, delay: float) -> float:
    step = tf_delta(tf)
    next_close = now.floor(f"{int(step.total_seconds() // 60)}min") + step + pd.Timedelta(seconds=delay)
    return max(1.0, (next_close - now).total_seconds())


class LiveTrader:
    def __init__(self, cfg: dict, journal: Journal, connect: Callable[[dict], Any], root: Path) -> None:
        self._cfg = cfg
        self._journal = journal
        self._store = LiveStore(journal)
        self._connect = connect
        self._stop_file = root / cfg["live"]["stop_file"]
        self._analyzer = Analyzer(cfg)
        self._tfs = timeframes(cfg)
        self._trigger_tf = cfg["timeframes"]["trigger"]
        self._mg = cfg["management"]
        self._broker: MT5Broker | None = None
        self._source: MT5Source | None = None
        self._news = NewsStore(cfg["news"]["db"])
        self._shutdown_file = shutdown_file(root)
        self._run_id = journal.create_run("live", cfg)

    # ---------- kết nối ----------
    def _ensure_connection(self) -> MT5Broker:
        if self._broker is not None and self._broker.is_connected():
            return self._broker
        mt5 = self._connect(self._cfg)
        conn, data = self._cfg["mt5"], self._cfg["data"]
        broker = MT5Broker(mt5, self._cfg["symbol"], conn["magic"], conn["deviation_points"], data["server_time"])
        broker.ensure_demo()
        if self._journal.get_kv("live_initial_equity") is None:
            self._journal.set_kv("live_initial_equity", str(broker.equity()))
        self._broker, self._source = broker, MT5Source(mt5, self._cfg["symbol"], data["server_time"])
        log.info("Đã kết nối MT5 (demo). Hedging: %s", broker.supports_hedging())
        return broker

    def _drop_connection(self) -> None:
        self._broker = self._source = None

    def _sleep(self, seconds: float) -> bool:
        """Ngủ nhưng thức dậy mỗi giây để kiểm tra yêu cầu dừng. Trả True nếu phải dừng."""
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            if self._shutdown_file.exists():
                return True
            time.sleep(min(1.0, max(0.0, deadline - time.monotonic())))
        return self._shutdown_file.exists()

    def run_forever(self) -> None:
        self._shutdown_file.unlink(missing_ok=True)
        backoff = self._cfg["live"]["reconnect_backoff_seconds"]
        failures = 0
        while True:
            try:
                self._ensure_connection()
                self.cycle(pd.Timestamp.now(tz="UTC"))
                self._journal.set_kv("heartbeat", pd.Timestamp.now(tz="UTC").isoformat())
                failures = 0
                wait = seconds_until_next_close(pd.Timestamp.now(tz="UTC"), self._trigger_tf,
                                                self._cfg["live"]["poll_delay_seconds"])
            except DemoAccountRequired:
                raise
            except Exception:  # noqa: BLE001 — giữ bot sống qua lỗi mạng/terminal, log đầy đủ
                log.exception("Lỗi vòng lặp, sẽ kết nối lại")
                self._drop_connection()
                wait = backoff[min(failures, len(backoff) - 1)]
                failures += 1
            if self._sleep(wait):
                self._shutdown_file.unlink(missing_ok=True)
                log.info("Nhận yêu cầu dừng — bot thoát (lệnh đang mở vẫn giữ SL/TP trên MT5).")
                return

    # ---------- một chu kỳ ----------
    def cycle(self, now: pd.Timestamp) -> None:
        hist = self._cfg["data"]["history_bars"]
        frames = {tf: enrich(self._source.fetch_last(tf, hist[tf], now), self._cfg["structure"]) for tf in self._tfs}
        t = frames[self._trigger_tf]["close_time"].iat[-1]
        if self._store.last_bar() == t.isoformat():
            return
        self._broker.ensure_demo()
        self._sync(frames)
        self._manage(frames, t)
        self._sync(frames)
        self._enter(frames, t)
        self._store.set_last_bar(t.isoformat())

    # ---------- đồng bộ lệnh đã đóng ----------
    def _sync(self, frames: dict[str, pd.DataFrame]) -> None:
        positions = self._broker.positions()
        bar = frames[self._trigger_tf].iloc[-1]
        touched: set[str] = set()
        for leg in self._store.open_legs():
            if leg["ticket"] in positions:
                self._update_excursion(leg, bar)
                continue
            result = self._broker.closed_result(leg["ticket"])
            if result is None:
                continue
            self._store.update_leg(leg["ticket"], status="closed", exit_price=result.price, exit_time=result.time,
                                   exit_reason=result.reason, profit=result.profit)
            touched.add(leg["setup_key"])
        for key in touched:
            self._after_leg_closed(key, positions)

    def _update_excursion(self, leg: dict, bar: pd.Series) -> None:
        d = leg["direction"]
        fav = (bar["high"] - leg["entry"]) if d == Direction.BUY else (leg["entry"] - bar["low"])
        adv = (leg["entry"] - bar["low"]) if d == Direction.BUY else (bar["high"] - leg["entry"])
        self._store.update_leg(leg["ticket"], mfe=max(leg["mfe"] or 0.0, fav), mae=max(leg["mae"] or 0.0, adv))

    def _after_leg_closed(self, key: str, positions: dict[int, Any]) -> None:
        legs = self._store.legs_by_key(key)
        still_open = [leg for leg in legs if leg["status"] == "open"]
        tp1_hit = any(leg["leg"] == "tp1" and leg["exit_reason"] == "tp" for leg in legs)
        if tp1_hit and self._mg["move_to_breakeven"]:
            for leg in still_open:
                pos = positions.get(leg["ticket"])
                if pos is not None and improves(Direction(leg["direction"]), leg["entry"], pos.sl):
                    self._broker.modify_sl(pos, leg["entry"])
                    self._store.update_leg(leg["ticket"], sl=leg["entry"])
                    log.info("%s: TP1 đạt, dời SL runner về hòa vốn", key)
        if not still_open:
            self._record_trade(legs)

    def _record_trade(self, legs: list[dict]) -> None:
        first = legs[0]
        d = first["direction"]
        volume = sum(leg["volume"] for leg in legs)
        risk = abs(first["entry"] - first["initial_sl"])
        price_pnl = sum(leg["volume"] * (leg["exit_price"] - leg["entry"]) * d for leg in legs)
        r = price_pnl / (volume * risk) if risk > 0 else 0.0
        exit_time = max(pd.Timestamp(leg["exit_time"]) for leg in legs)
        self._journal.insert("trades", [{
            "run_id": first["run_id"], "setup_key": first["setup_key"], "setup": first["setup"],
            "direction": Direction(d).name, "bias": first["bias"], "score": first["score"],
            "entry_time": first["opened_at"], "exit_time": exit_time, "entry": first["entry"],
            "sl": first["initial_sl"], "tp1": first["tp1"], "tp2": first["tp2"], "volume": volume,
            "r_multiple": r, "pnl": sum(leg["profit"] or 0.0 for leg in legs),
            "exit_reason": "+".join(f"{leg['leg']}:{leg['exit_reason']}" for leg in legs),
            "mae_r": max(leg["mae"] or 0.0 for leg in legs) / risk if risk else 0.0,
            "mfe_r": max(leg["mfe"] or 0.0 for leg in legs) / risk if risk else 0.0,
            "spread_entry": first["spread_entry"], "news": first["news"], "reasons": first["reasons"],
        }])
        streak = register_result(self._store.streak(), r, exit_time, self._cfg["risk"])
        self._store.save_streak(streak)
        equity = self._broker.equity()
        self._journal.insert("equity", [{"run_id": self._run_id, "time": exit_time, "equity": equity,
                                         "drawdown_pct": None}])
        log.info("Đóng lệnh %s: %+.2fR", first["setup_key"], r)

    # ---------- quản lý lệnh đang mở ----------
    def _manage(self, frames: dict[str, pd.DataFrame], t: pd.Timestamp) -> None:
        open_keys = self._store.open_by_key()
        if not open_keys:
            return
        positions = self._broker.positions()
        self._breakeven(open_keys, positions)
        trail_df = frames[self._mg["trail_tf"]]
        if self._mg["trail_after_tp1"] and trail_df["close_time"].iat[-1] == t:
            view = self._analyzer.view(frames, self._mg["trail_tf"], t)
            if view is not None:
                self._trail(open_keys, positions, view)
        for key, legs in open_keys.items():
            if must_flatten(pd.Timestamp(legs[0]["opened_at"]), t, self._mg, self._cfg["sessions"]):
                log.info("%s: tới giờ đóng lệnh (flat_time) → đóng lệnh", key)
                for leg in legs:
                    if leg["ticket"] in positions:
                        self._broker.close_position(positions[leg["ticket"]])
        inval_df = frames[self._mg["invalidation_tf"]]
        if inval_df["close_time"].iat[-1] == t:
            close = float(inval_df["close"].iat[-1])
            for key, legs in open_keys.items():
                if breaks_invalidation(Direction(legs[0]["direction"]), close, legs[0]["invalidation"]):
                    log.info("%s: nến %s đóng phá invalidation → đóng lệnh", key, self._mg["invalidation_tf"])
                    for leg in legs:
                        if leg["ticket"] in positions:
                            self._broker.close_position(positions[leg["ticket"]])

    def _breakeven(self, open_keys: dict[str, list[dict]], positions: dict[int, Any]) -> None:
        """Giá đã chạy thuận đủ `breakeven_at_r` → dời SL về giá vào; nếu giá đã quay về sau giá vào thì đóng luôn."""
        at_r = self._mg["breakeven_at_r"]
        bid, ask = self._broker.quote()
        for key, legs in open_keys.items():
            first = legs[0]
            d = Direction(first["direction"])
            risk = abs(first["entry"] - first["initial_sl"])
            if not breakeven_due(max(leg["mfe"] or 0.0 for leg in legs), risk, at_r):
                continue
            exit_price = bid if d == Direction.BUY else ask
            for leg in legs:
                pos = positions.get(leg["ticket"])
                if pos is None or not improves(d, leg["entry"], pos.sl):
                    continue
                if (exit_price - leg["entry"]) * d > 0:
                    self._broker.modify_sl(pos, leg["entry"])
                    self._store.update_leg(leg["ticket"], sl=leg["entry"])
                    log.info("%s: đạt %.1fR → dời SL %s về hòa vốn", key, at_r, leg["leg"])
                else:
                    self._broker.close_position(pos)
                    log.info("%s: đã đạt %.1fR nhưng giá quay về điểm vào → đóng %s", key, at_r, leg["leg"])

    def _trail(self, open_keys: dict[str, list[dict]], positions: dict[int, Any], view) -> None:
        buffer = self._mg["trail_buffer_atr"] * view.atr
        for key, legs in open_keys.items():
            if not any(leg["leg"] == "tp1" and leg["exit_reason"] == "tp" for leg in self._store.legs_by_key(key)):
                continue
            for leg in legs:
                pos = positions.get(leg["ticket"])
                if pos is None:
                    continue
                level = trail_stop(Direction(leg["direction"]), view.swings, pos.sl, view.close, buffer)
                if level is not None:
                    self._broker.modify_sl(pos, level)
                    self._store.update_leg(leg["ticket"], sl=level)

    # ---------- vào lệnh mới ----------
    def _enter(self, frames: dict[str, pd.DataFrame], t: pd.Timestamp) -> None:
        if self._stop_file.exists():
            log.warning("Có file %s → không mở lệnh mới", self._stop_file.name)
            return
        nc = self._cfg["news"]
        if nc["enabled"]:
            self._news.refresh_if_stale(nc["source_url"], pd.Timestamp.now(tz="UTC"), nc["refresh_minutes"])
        ctx, signals = self._analyzer.signals(frames, t)
        if not signals:
            return
        calendar = build_calendar(self._news.all(), nc)
        spec = self._broker.symbol_spec()
        hedging = self._broker.supports_hedging()
        for signal in sorted(signals, key=lambda s: -s.setup.score):
            if self._store.key_traded(signal.setup.key):
                continue
            bid, ask = self._broker.quote()
            entry = ask if signal.direction == Direction.BUY else bid
            spread = (ask - bid) / spec.point
            equity = self._broker.equity()
            snapshot = AccountSnapshot(equity, self._store.day_start_equity(str(t.date()), equity),
                                       self._store.exposures(), self._store.streak())
            decision = decide(signal, ctx, entry, snapshot, spread, spec, self._cfg, calendar, allow_split=hedging)
            self._journal.insert("signals", [signal_row(self._run_id, signal, decision)])
            log.info("Tín hiệu %s %s (%s): %s", signal.setup.name, signal.direction.name, signal.trigger,
                     "VÀO LỆNH" if decision.accepted else decision.reason)
            if decision.accepted:
                self._open(decision, spread, t)

    def _open(self, decision: Decision, spread: float, t: pd.Timestamp) -> None:
        plan: TradePlan = decision.plan
        signal, setup = plan.signal, plan.signal.setup
        names = ("tp1", "runner") if len(decision.legs) == 2 else ("single",)
        targets = (plan.tp1, plan.tp2) if len(decision.legs) == 2 else (plan.tp1,)
        for name, volume, tp in zip(names, decision.legs, targets):
            try:
                ticket = self._broker.market_order(signal.direction, volume, plan.sl, tp,
                                                   f"{SETUP_ABBR.get(setup.name, setup.name)}|{name}")
            except BrokerError:
                log.exception("Không gửi được chân %s của %s", name, setup.key)
                continue
            self._store.add_leg({
                "ticket": ticket, "run_id": self._run_id, "setup_key": setup.key, "setup": setup.name, "leg": name,
                "direction": int(signal.direction), "volume": volume, "entry": self._fill_price(ticket, plan.entry),
                "initial_sl": plan.sl, "sl": plan.sl, "tp": tp, "tp1": plan.tp1, "tp2": plan.tp2,
                "invalidation": setup.invalidation, "zone_low": setup.zone.low, "zone_high": setup.zone.high,
                "bias": bias_label(signal.bias), "score": setup.score, "reasons": list(setup.reasons),
                "spread_entry": spread, "news": decision.news, "opened_at": t, "status": "open",
                "mae": 0.0, "mfe": 0.0,
            })
            log.info("Đã mở %s %s %.2f lot SL %.2f TP %s (ticket %d)", setup.key, name, volume, plan.sl, tp, ticket)

    def _fill_price(self, ticket: int, fallback: float) -> float:
        pos = self._broker.positions().get(ticket)
        return float(pos.price_open) if pos is not None else fallback
