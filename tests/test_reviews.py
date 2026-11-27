"""Vẽ tay + nhận xét lệnh: kho lưu theo scope và dữ liệu chart tương tác của một lệnh."""
import json

import numpy as np
import pandas as pd

from data.candles import normalize
from journal.db import Journal
from journal.reviews import ReviewStore
from web.services.review_chart import Window, chart_payload, load_item, snapshot

NOW = pd.Timestamp("2026-11-25 16:00", tz="UTC")


class FakeGateway:
    def __init__(self, frame):
        self.frame = frame

    def call(self, fn):
        return self.frame


def _m15(n=1200):
    t = pd.date_range(NOW - pd.Timedelta(minutes=15 * n), periods=n, freq="15min")
    c = 3500 + np.cumsum(np.sin(np.arange(n) / 7.0))
    return normalize(pd.DataFrame({"time": t, "open": c, "high": c + 2, "low": c - 2, "close": c + 0.5}), "M15")


def test_store_merges_fields_and_lists_reviewed(tmp_path):
    with ReviewStore(tmp_path / "r.db") as store:
        shape = {"id": "a", "kind": "trend", "role": "wrong", "points": [{"t": 1, "p": 2.0}, {"t": 3, "p": 4.0}]}
        store.save("trade:bot:swing:r1:5", {"shapes": [shape]}, NOW)
        saved = store.save("trade:bot:swing:r1:5", {"verdict": "bad", "errors": ["wrong_edge"]}, NOW)
        assert saved["shapes"] == [shape] and saved["verdict"] == "bad" and saved["errors"] == ["wrong_edge"]
        store.save("chart:XAUUSD", {"shapes": []}, NOW)
        assert [r["scope"] for r in store.reviewed()] == ["trade:bot:swing:r1:5"]   # chart chung không phải nhận xét


def test_chart_payload_uses_signal_edges_when_trade_meta_lacks_them(tmp_path):
    entry, exit_ = NOW - pd.Timedelta(days=4), NOW - pd.Timedelta(days=2)
    edge = [str(NOW - pd.Timedelta(days=6)), 3530.0, str(NOW - pd.Timedelta(days=5)), 3525.0]
    with Journal(tmp_path / "j.db") as j:
        j.insert("signals", [{"run_id": "r1", "time": entry.isoformat(), "setup": "flag", "direction": "SELL",
                              "setup_key": "k1", "meta": json.dumps({"tf": "H1", "edges": [edge]})}])
        j.insert("trades", [{"run_id": "r1", "setup_key": "k1", "setup": "flag", "direction": "SELL",
                             "entry_time": entry.isoformat(), "exit_time": exit_.isoformat(), "entry": 3520.0,
                             "sl": 3540.0, "tp1": 3480.0, "volume": 0.1, "r_multiple": 1.2,
                             "meta": json.dumps({"tf": "H1", "target": 3470.0})}])
        item = load_item(j, "trade", 1, None)
        out = chart_payload(j, item, {}, FakeGateway(_m15()), Window(10, 500), NOW)
    assert out["tf"] == "H1" and out["direction"] == -1 and out["target"] == 3470.0
    assert out["edges"][0][1] == 3530.0 and out["edges"][0][0] == int(pd.Timestamp(edge[0]).timestamp())
    times = [c["time"] for c in out["candles"]]
    assert times == sorted(times) and times[0] <= out["edges"][0][0] and times[-1] >= out["exit_time"]
    assert snapshot(item, "trade")["r"] == 1.2


def test_review_report_counts_errors_and_lists_shapes():
    from stats.review_report import build
    cfg = {"verdicts": [{"key": "bad", "label": "Lệnh sai"}], "roles": [{"key": "wrong", "label": "Sai"}],
           "error_tags": [{"key": "wrong_edge", "label": "Vào sai biên"}]}
    rows = [{"scope": "setup:bot:swing:k1", "verdict": "bad", "errors": ["wrong_edge"], "note": "nên sell biên trên",
             "snapshot": {"setup_key": "k1", "direction": "SELL", "r": -1.0, "entry": 3520.0},
             "shapes": [{"kind": "trend", "role": "wrong", "points": [{"t": 0, "p": 1.0}, {"t": 3600, "p": 2.0}]}]}]
    text = build(rows, cfg)
    assert "- Vào sai biên: 1" in text and "-1.00R trên 1 lệnh" in text
    assert "Sai · trend: 1970-01-01 00:00 @ 1.00 → 1970-01-01 01:00 @ 2.00" in text and "nên sell biên trên" in text
