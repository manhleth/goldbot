"""Guard chỉ-demo với MT5 giả lập."""
from types import SimpleNamespace

import pytest

from core.types import Direction
from execution.mt5_broker import DemoAccountRequired, MT5Broker


class FakeMT5:
    ACCOUNT_TRADE_MODE_DEMO, ACCOUNT_TRADE_MODE_REAL = 0, 2
    ACCOUNT_MARGIN_MODE_RETAIL_HEDGING = 2

    def __init__(self, trade_mode):
        self.trade_mode = trade_mode
        self.sent = []

    def account_info(self):
        return SimpleNamespace(trade_mode=self.trade_mode, margin_mode=2, equity=1000.0)

    def order_send(self, request):
        self.sent.append(request)


def test_real_account_blocks_everything():
    mt5 = FakeMT5(FakeMT5.ACCOUNT_TRADE_MODE_REAL)
    broker = MT5Broker(mt5, "XAUUSD", 1, 10, 0)
    with pytest.raises(DemoAccountRequired):
        broker.ensure_demo()
    with pytest.raises(DemoAccountRequired):
        broker._send({"action": 1})
    assert mt5.sent == []


def test_demo_account_passes_guard():
    MT5Broker(FakeMT5(FakeMT5.ACCOUNT_TRADE_MODE_DEMO), "XAUUSD", 1, 10, 0).ensure_demo()
