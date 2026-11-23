"""Bot live phương pháp ONE trên MT5 DEMO: mỗi bot một tiến trình, magic + journal riêng, chạy song song được.

Chu kỳ (mỗi khi nến khung gốc đóng):
1. cập nhật nến khung gốc (cache lịch sử + MT5), bỏ nến khung lớn chưa đóng;
2. làm mới kinh nghiệm (trade nháp lịch sử) theo chu kỳ `experience_refresh_hours`;
3. đồng bộ lệnh đã đóng → journal trades (+ chart lý do có điểm thoát);
4. quản lý lệnh mở: đóng lệnh trong ngày khi tới giờ, dời SL theo đỉnh/đáy khung mẫu hình (chỉ siết);
5. tín hiệu mới → lọc (hướng channel, kinh nghiệm, số lệnh, STOP) → lệnh market có SL, ghi lý do + chart.
Mọi lệnh đi qua MT5Broker._send → kiểm tra tài khoản DEMO trước mỗi lệnh.
"""
from __future__ import annotations

import json
import logging
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pandas as pd

from core.types import Direction
from data.history import load_csv
from data.mt5_source import MT5Source
from execution.live import seconds_until_next_close
from execution.live_store import LiveStore
from execution.mt5_broker import BrokerError, DemoAccountRequired, MT5Broker
from journal.db import Journal
from playbook import chart_svg
from playbook.live_engine import Decision, OneEngine
from playbook.runner import load_playbook, signal_row
from playbook.simulator import Outcome
from risk.management import improves, trading_date
from risk.sizing import lot_size

log = logging.getLogger(__name__)


def bot_shutdown_file(root: Path, name: str) -> Path:
    return root / "run" / f"bot_{name}.shutdown"


class OneBot:
    def __init__(self, cfg: dict, name: str, connect: Callable[[dict], Any], root: Path, dry_run: bool = False) -> None:
        self._cfg = cfg
        self._dry_run = dry_run  # chạy đủ quy trình nhưng không gửi lệnh (kiểm tra an toàn)
        self.name = name
        self.bc = {**cfg["bot_common"], **cfg["bots"][name]}
        self._root = root
        self._connect = connect
        self._pb = load_playbook(root / self.bc["playbook"])
        self._journal = Journal(self.bc["journal"])
        self._store = LiveStore(self._journal)
        self._broker: MT5Broker | None = None
        self._source: MT5Source | None = None
        self._engine: OneEngine | None = None
        self._base: pd.DataFrame | None = None
        self._stop_file = root / cfg["live"]["stop_file"]
        self._shutdown = bot_shutdown_file(root, name)
        self._charts = Path(self.bc["journal"]).parent / "charts" / f"live_{name}"
        p = {**self._pb["common"], **self._pb["methods"][self.bc["method"]]}
        self._run_id = self._journal.create_run("live", {**cfg, "bot": self.bc, "playbook": p})

    # ---------- kết nối & dữ liệu ----------
    def _ensure(self) -> MT5Broker:
        if self._broker is not None and self._broker.is_connected():
            return self._broker
        mt5 = self._connect(self._cfg)
        conn = self._cfg["mt5"]
        broker = MT5Broker(mt5, self._cfg["symbol"], self.bc["magic"], conn["deviation_points"],
                           self._cfg["data"]["server_time"])
        broker.ensure_demo()
        if self._journal.get_kv("live_initial_equity") is None:
            self._journal.set_kv("live_initial_equity", str(broker.equity()))
        self._broker, self._source = broker, MT5Source(mt5, self._cfg["symbol"], self._cfg["data"]["server_time"])
        self._engine = OneEngine(self._cfg, self._pb, self.bc["method"], self.bc["variant"], broker.symbol_spec())
        log.info("[%s] Đã kết nối MT5 DEMO, magic %s, phương pháp %s", self.name, self.bc["magic"], self.bc["method"])
        return broker

    def _refresh_base(self, now: pd.Timestamp) -> pd.DataFrame:
        tf = self.bc["base_tf"]
        if self._base is None:
            cache = Path(self.bc["cache_file"])
            self._base = load_csv(cache, tf) if cache.exists() else None
        fresh = self._source.fetch_last(tf, self.bc["fetch_bars"], now)
        merged = fresh if self._base is None else pd.concat([self._base, fresh])
        merged = merged.drop_duplicates("time", keep="last").sort_values("time")
        keep = now - pd.Timedelta(days=self.bc["history_days"])
        self._base = merged[merged["time"] >= keep].reset_index(drop=True)
        return self._base

    # ---------- vòng lặp ----------
    def run_forever(self) -> None:
        self._shutdown.unlink(missing_ok=True)
        backoff = self._cfg["live"]["reconnect_backoff_seconds"]
        failures = 0
        while True:
            try:
                self._ensure()
                self.cycle(pd.Timestamp.now(tz="UTC"))
                self._journal.set_kv("heartbeat", pd.Timestamp.now(tz="UTC").isoformat())
                failures = 0
                wait = seconds_until_next_close(pd.Timestamp.now(tz="UTC"), self.bc["base_tf"],
                                                self.bc["poll_delay_seconds"])
            except DemoAccountRequired:
                raise
            except Exception:  # noqa: BLE001 — giữ bot sống qua lỗi mạng/terminal
                log.exception("[%s] Lỗi chu kỳ, sẽ kết nối lại", self.name)
                self._broker = None
                wait = backoff[min(failures, len(backoff) - 1)]
                failures += 1
            if self._sleep(wait):
                self._shutdown.unlink(missing_ok=True)
                log.info("[%s] Dừng theo yêu cầu (lệnh đang mở vẫn giữ SL trên MT5).", self.name)
                return

    def _sleep(self, seconds: float) -> bool:
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            if self._shutdown.exists():
                return True
            time.sleep(min(1.0, max(0.0, deadline - time.monotonic())))
        return self._shutdown.exists()

    def cycle(self, now: pd.Timestamp) -> None:
        base = self._refresh_base(now)
        t = base["close_time"].iat[-1]
        if self._store.last_bar() == t.isoformat():
            return
        self._broker.ensure_demo()
        engine = self._engine
        if engine.needs_refresh(now, self.bc["experience_refresh_hours"]):
            full, full_bars = engine.market(base, self.bc["base_tf"], now)
            summary = engine.refresh_experience(full, full_bars, now)
            self._journal.set_kv("experience", json.dumps(summary, ensure_ascii=False))
            log.info("[%s] Kinh nghiệm: %s", self.name,
                     ", ".join(f"{k} {n} lệnh nháp {e:+.2f}R" for k, (n, e) in summary.items()))
        window = base[base["time"] >= now - pd.Timedelta(days=self.bc["signal_days"])].reset_index(drop=True)
        data, bars = engine.market(window, self.bc["base_tf"], now)
        self._sync(data)
        self._manage(data, bars, now)
        self._enter(data, t, now)
        self._store.set_last_bar(t.isoformat())

    # ---------- đồng bộ lệnh đã đóng ----------
    def _sync(self, data) -> None:
        positions = self._broker.positions()
        for leg in self._store.open_legs():
            if leg["ticket"] in positions:
                continue
            result = self._broker.closed_result(leg["ticket"])
            if result is None:
                continue
            self._store.update_leg(leg["ticket"], status="closed", exit_price=result.price, exit_time=result.time,
                                   exit_reason=result.reason, profit=result.profit)
            self._record_trade({**leg, "exit_price": result.price, "exit_time": result.time,
                                "exit_reason": result.reason, "profit": result.profit}, data)

    def _record_trade(self, leg: dict, data) -> None:
        d = int(leg["direction"])
        risk = abs(leg["entry"] - leg["initial_sl"])
        r = (leg["exit_price"] - leg["entry"]) * d / risk if risk > 0 else 0.0
        chart = self._chart(leg, data, pd.Timestamp(leg["exit_time"]), leg["exit_price"], r)
        self._journal.insert("trades", [{
            "run_id": leg["run_id"], "setup_key": leg["setup_key"], "setup": leg["setup"],
            "direction": Direction(d).name, "bias": "", "score": 0, "entry_time": leg["opened_at"],
            "exit_time": leg["exit_time"], "entry": leg["entry"], "sl": leg["initial_sl"], "tp1": None, "tp2": None,
            "volume": leg["volume"], "r_multiple": r, "pnl": leg["profit"] or 0.0, "exit_reason": leg["exit_reason"],
            "mae_r": None, "mfe_r": None, "spread_entry": leg["spread_entry"], "news": "none",
            "reasons": json.loads(leg["reasons"]) if leg["reasons"] else [], "chart": chart,
        }])
        self._journal.insert("equity", [{"run_id": self._run_id, "time": leg["exit_time"],
                                         "equity": self._broker.equity(), "drawdown_pct": None}])
        log.info("[%s] Đóng %s: %+.2fR, %+.2f$", self.name, leg["setup_key"], r, leg["profit"] or 0.0)

    # ---------- quản lý lệnh mở ----------
    def _manage(self, data, bars, now: pd.Timestamp) -> None:
        positions = self._broker.positions()
        bid, ask = self._broker.quote()
        for leg in self._store.open_legs():
            pos = positions.get(leg["ticket"])
            if pos is None:
                continue
            d = Direction(int(leg["direction"]))
            if leg.get("exit_at") and now >= pd.Timestamp(leg["exit_at"]):
                self._broker.close_position(pos)
                log.info("[%s] %s: hết giờ trong ngày → đóng", self.name, leg["setup_key"])
                continue
            if not leg.get("trail"):
                continue
            level = self._engine.trail_level(data, bars, leg["trail"], d, pd.Timestamp(leg["opened_at"]))
            if level is None or not improves(d, level, pos.sl):
                continue
            exit_price = bid if d == Direction.BUY else ask
            if (exit_price - level) * d > 0:
                self._broker.modify_sl(pos, level)
                self._store.update_leg(leg["ticket"], sl=level)
                log.info("[%s] %s: dời SL %.2f → %.2f (đỉnh/đáy %s)", self.name, leg["setup_key"], pos.sl, level,
                         leg["trail"])
            else:  # giá đã vượt mức SL mới (như backtest: thoát ở giá mở nến kế)
                self._broker.close_position(pos)
                log.info("[%s] %s: giá đã phá đỉnh/đáy %s → đóng", self.name, leg["setup_key"], leg["trail"])

    # ---------- vào lệnh ----------
    def _enter(self, data, t: pd.Timestamp, now: pd.Timestamp) -> None:
        step = self._base["close_time"].iat[-1] - self._base["time"].iat[-1]
        since = pd.Timestamp(self._journal.get_kv("last_signal_time") or (t - step).isoformat())
        decisions = sorted(self._engine.decide(data, since), key=lambda x: x.order.time)
        for decision in decisions:
            reason = decision.reject or self._block_reason(decision, t, step)
            accepted = reason is None and self._open(decision, now, data)
            self._journal.insert("signals", [signal_row(
                self._run_id, self.bc["method"],
                Outcome(decision.order, "filled" if accepted else "skipped", "" if accepted else (reason or "order_failed")))])
            log.info("[%s] Tín hiệu %s: %s", self.name, decision.order.key, "VÀO LỆNH" if accepted else reason)
        if decisions:
            self._journal.set_kv("last_signal_time", max(x.order.time for x in decisions).isoformat())
        elif since < t - step:
            self._journal.set_kv("last_signal_time", (t - step).isoformat())

    def _block_reason(self, decision: Decision, t: pd.Timestamp, step: pd.Timedelta) -> str | None:
        p = self._engine.p
        if self._stop_file.exists():
            return "stop_file"
        if decision.order.time < t - step:
            return "stale_signal"  # tín hiệu cũ (vd bot vừa khởi động) → không đuổi theo
        if len(self._broker.positions()) >= p["max_positions"]:
            return "max_open_trades"
        if p.get("max_per_day"):
            today = trading_date(t, self._cfg["sessions"])
            opened = [leg for leg in self._journal.rows("SELECT opened_at FROM live_legs")
                      if trading_date(pd.Timestamp(leg["opened_at"]), self._cfg["sessions"]) == today]
            if len(opened) >= p["max_per_day"]:
                return "max_trades_per_day"
        return None

    def _open(self, decision: Decision, now: pd.Timestamp, data) -> bool:
        order, p = decision.order, self._engine.p
        d = order.direction
        bid, ask = self._broker.quote()
        price = ask if d == Direction.BUY else bid
        dist = self._engine.stop_distance(order, price)
        if dist is None:
            return False
        spec = self._broker.symbol_spec()
        risk_money = self._broker.equity() * p["risk_pct"] / 100 if p.get("risk_pct") else p["risk_per_trade_money"]
        volume = lot_size(risk_money, dist, spec)
        if volume <= 0:
            return False
        sl = price - int(d) * dist
        kind = order.key.split(":")[1]
        if self._dry_run:
            log.info("[%s] DRY-RUN: sẽ mở %s %s %.2f lot @ %.2f SL %.2f (rủi ro %.0f$)", self.name, d.name, kind,
                     volume, price, sl, risk_money)
            return False
        try:
            ticket = self._broker.market_order(d, volume, sl, None, f"{self.bc['comment']}|{kind}")
        except BrokerError:
            log.exception("[%s] Không gửi được lệnh %s", self.name, order.key)
            return False
        pos = self._broker.positions().get(ticket)
        entry = float(pos.price_open) if pos is not None else price
        leg = {
            "ticket": ticket, "run_id": self._run_id, "setup_key": order.key, "setup": kind, "leg": "single",
            "direction": int(d), "volume": volume, "entry": entry, "initial_sl": sl, "sl": sl, "tp": None,
            "tp1": None, "tp2": None, "invalidation": None, "zone_low": None, "zone_high": None, "bias": "",
            "score": 0, "reasons": list(order.reasons), "spread_entry": (ask - bid) / spec.point, "news": "none",
            "opened_at": now, "status": "open", "mae": 0.0, "mfe": 0.0, "meta": json.dumps(order.meta),
            "exit_at": order.exit_at.isoformat() if order.exit_at is not None else None,
            "trail": order.trail.split("@")[1] if order.trail else None, "bot": self.name,
        }
        leg["chart"] = self._chart({**leg, "reasons": json.dumps(leg["reasons"])}, data, now, entry, 0.0)
        self._store.add_leg(leg)
        log.info("[%s] Đã mở %s %s %.2f lot @ %.2f SL %.2f (rủi ro %.0f$, ticket %d) — %s", self.name, d.name, kind,
                 volume, entry, sl, risk_money, ticket, " · ".join(order.reasons))
        return True

    def _chart(self, leg: dict, data, exit_time: pd.Timestamp, exit_price: float, r: float) -> str | None:
        meta = json.loads(leg["meta"]) if isinstance(leg.get("meta"), str) else (leg.get("meta") or {})
        if not meta.get("tf") or meta["tf"] not in data.frames:
            return None
        reasons = json.loads(leg["reasons"]) if isinstance(leg.get("reasons"), str) else leg.get("reasons") or []
        view = chart_svg.TradeView(int(leg["direction"]), pd.Timestamp(leg["opened_at"]), leg["entry"],
                                   leg["initial_sl"], exit_time, exit_price, r,
                                   f"BOT {self.name.upper()} · {leg['setup']}", tuple(reasons), meta)
        self._charts.mkdir(parents=True, exist_ok=True)
        path = self._charts / f"{leg['setup_key'].replace(':', '_').replace('@', '-')}.svg"
        path.write_text(chart_svg.render(data.frames[meta["tf"]], view), encoding="utf-8")
        return str(path)
