"""Ảnh hiện tại của lệnh đang mở: có SL hiện tại, giá hiện tại, R thả nổi theo giá MT5."""
import json

import numpy as np
import pandas as pd

from data.candles import normalize
from web.services.live_chart import render_leg_now

NOW = pd.Timestamp("2026-11-25 16:00", tz="UTC")


class FakeGateway:
    def __init__(self, frame):
        self.frame = frame

    def call(self, fn):
        return self.frame


def _m15(n=400):
    t = pd.date_range(NOW - pd.Timedelta(minutes=15 * n), periods=n, freq="15min")
    c = 3500 + np.cumsum(np.sin(np.arange(n) / 7.0))
    return normalize(pd.DataFrame({"time": t, "open": c, "high": c + 2, "low": c - 2, "close": c + 0.5}), "M15")


def test_render_leg_now_shows_current_sl_price_and_floating_r():
    leg = {"ticket": 1, "direction": -1, "entry": 3520.0, "sl": 3540.0, "initial_sl": 3545.0,
           "opened_at": (NOW - pd.Timedelta(hours=10)).isoformat(), "setup_key": "one_day:flag@H1:x:SELL",
           "reasons": json.dumps(["flag H1"]), "trail": "H1",
           "meta": json.dumps({"tf": "H1", "edges": [[str(NOW - pd.Timedelta(days=2)), 3530.0,
                                                       str(NOW - pd.Timedelta(days=1)), 3525.0]]})}
    broker = {"price_open": 3520.0, "price_current": 3507.5, "sl": 3530.0}
    svg = render_leg_now(leg, broker, {}, FakeGateway(_m15()), NOW)
    assert svg is not None and svg.startswith("<svg")
    assert "SL hiện tại 3530.00" in svg and "Giá hiện tại 3507.50" in svg
    assert "+0.50R" in svg and "đang mở" in svg   # (3520 − 3507.5) / 25 = +0.5R
