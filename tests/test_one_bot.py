"""Bot ONE với broker/engine giả: khối lượng theo % equity, SL, dry-run, dời SL, đóng lệnh trong ngày."""
from types import SimpleNamespace

import pandas as pd
import pytest

from core.types import Direction
from execution.one_bot import OneBot
from playbook.live_engine import Decision
from playbook.orders import MARKET, Order
from risk.sizing import SymbolSpec

SPEC = SymbolSpec(point=0.01, tick_size=0.01, tick_value=0.1, volume_min=0.01, volume_step=0.01, volume_max=100)
T = pd.Timestamp("2026-11-23 10:15", tz="UTC")


class FakeBroker:
    def __init__(self, equity=100_000.0):
        self._equity, self.sent, self.modified, self.closed = equity, [], [], []
        self.open = {}

    def quote(self):
        return 3600.0, 3600.2

    def equity(self):
        return self._equity

    def symbol_spec(self):
        return SPEC

    def positions(self):
        return self.open

    def market_order(self, direction, volume, sl, tp, comment):
        self.sent.append((direction, volume, sl, tp, comment))
        self.open[1] = SimpleNamespace(ticket=1, price_open=3600.2, sl=sl)
        return 1

    def modify_sl(self, pos, sl):
        self.modified.append(sl)

    def close_position(self, pos):
        self.closed.append(pos.ticket)


class FakeStore:
    def __init__(self, legs=()):
        self.legs, self.updates = list(legs), []

    def add_leg(self, row):
        self.legs.append(row)

    def open_legs(self):
        return [leg for leg in self.legs if leg.get("status") == "open"]

    def update_leg(self, ticket, **fields):
        self.updates.append((ticket, fields))


class FakeEngine:
    p = {"max_positions": 5, "risk_pct": 5.0, "risk_per_trade_money": 20}

    def __init__(self, level=None):
        self.level = level

    def stop_distance(self, order, price):
        return order.sl_dist

    def trail_level(self, data, bars, tf, direction, entry_time):
        return self.level


def _bot(broker, store, engine, dry_run=False):
    bot = OneBot.__new__(OneBot)
    bot._broker, bot._store, bot._engine, bot._dry_run = broker, store, engine, dry_run
    bot.name, bot.bc, bot._run_id = "swing", {"comment": "ONE-SW"}, "r1"
    bot._charts = None
    bot._chart = lambda *a, **k: None
    return bot


def _decision(sl_dist=30.0):
    order = Order("one_swing:flag@H4:202611231015:BUY", T, Direction.BUY, MARKET, sl_dist=sl_dist,
                  reasons=("flag H4",), meta={}, trail="hold_tf@H4")
    return Decision(order, None)


def test_open_sizes_by_equity_percent_and_sets_sl():
    broker, store = FakeBroker(), FakeStore()
    assert _bot(broker, store, FakeEngine())._open(_decision(), T, data=None)
    direction, volume, sl, tp, comment = broker.sent[0]
    # 5% × 100.000 = 5.000$; SL 30$ → 30 / 0.01 × 0.1 = 300$/lot → 16.66 lot làm tròn xuống
    assert direction == Direction.BUY and volume == pytest.approx(16.66) and tp is None
    assert sl == pytest.approx(3600.2 - 30.0) and comment.startswith("ONE-SW|flag@H4")
    assert store.legs[0]["trail"] == "H4" and store.legs[0]["initial_sl"] == pytest.approx(3570.2)


def test_dry_run_never_sends_orders():
    broker = FakeBroker()
    assert not _bot(broker, FakeStore(), FakeEngine(), dry_run=True)._open(_decision(), T, data=None)
    assert broker.sent == []


def _open_leg(**extra):
    return {"ticket": 1, "status": "open", "direction": 1, "opened_at": T.isoformat(), "trail": "H4",
            "setup_key": "k", "exit_at": None, **extra}


def test_manage_trails_stop_only_when_it_improves_and_is_behind_price():
    broker = FakeBroker()
    broker.open[1] = SimpleNamespace(ticket=1, sl=3570.0)
    _bot(broker, FakeStore([_open_leg()]), FakeEngine(level=3590.0))._manage(None, None, T)
    assert broker.modified == [3590.0]
    broker.modified.clear()
    _bot(broker, FakeStore([_open_leg()]), FakeEngine(level=3560.0))._manage(None, None, T)  # nới SL → bỏ qua
    assert broker.modified == [] and broker.closed == []
    _bot(broker, FakeStore([_open_leg()]), FakeEngine(level=3605.0))._manage(None, None, T)  # mức mới trên giá → đóng
    assert broker.closed == [1]


def test_manage_closes_intraday_trade_at_exit_time():
    broker = FakeBroker()
    broker.open[1] = SimpleNamespace(ticket=1, sl=3570.0)
    leg = _open_leg(exit_at=(T - pd.Timedelta(minutes=1)).isoformat())
    _bot(broker, FakeStore([leg]), FakeEngine(level=3590.0))._manage(None, None, T)
    assert broker.closed == [1] and broker.modified == []
