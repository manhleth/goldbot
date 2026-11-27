"""Lớp vẽ của bot trên chart chính: trendline đa tỉ lệ (đang hiệu lực / vừa phá) và cạnh mẫu hình của setup."""
import json

import pandas as pd

from journal.db import Journal
from web.services.bot_overlays import key_trendlines, setups
from tests.test_tl_scales import P, Data, _frame


def test_key_trendlines_keep_strongest_per_side_and_broken_line_being_retested():
    ov = {"extend_bars": 10, "lines_each_side": 1, "broken_near_atr": 50}
    lines = key_trendlines(Data(_frame()), {**P, "swings": [3, 8]}, ov)
    broken = [x for x in lines if x["state"] == "broken" and x["side"] == 1]
    assert len(broken) == 1, lines                        # tối đa 1 đường mỗi phía mỗi trạng thái
    line = broken[0]
    assert line["touches"] >= 3 and line["points"][0][0] < line["points"][1][0] < line["extend_to"]
    assert len(line["marks"]) >= 3                        # đánh dấu các đáy chạm đường
    far = key_trendlines(Data(_frame()), {**P, "swings": [3, 8]}, {**ov, "broken_near_atr": 0.01})
    assert not [x for x in far if x["state"] == "broken"]  # giá không còn ở gần đường đã phá → không vẽ


def test_setups_return_pattern_edges_of_run_since(tmp_path):
    edge = ["2026-11-01 00:00+00:00", 3500.0, "2026-11-03 00:00+00:00", 3520.0]
    with Journal(tmp_path / "j.db") as j:
        j.insert("signals", [
            {"run_id": "r1", "time": "2026-11-04T08:00:00+00:00", "setup": "flag", "setup_key": "one:flag@H4:x:BUY",
             "direction": "BUY", "accepted": 1, "meta": json.dumps({"tf": "H4", "edges": [edge],
                                                                    "breakout_time": "2026-11-04 04:00+00:00"})},
            {"run_id": "r2", "time": "2026-11-05T08:00:00+00:00", "setup": "flag", "setup_key": None, "direction": "SELL", "accepted": 0,
             "meta": json.dumps({"tf": "H4", "edges": [edge]})},
        ])
        out = setups(j, "r1", pd.Timestamp("2026-11-01", tz="UTC"), 10)
    assert len(out) == 1 and out[0]["accepted"] and out[0]["tf"] == "H4"
    assert out[0]["edges"][0][1] == 3500.0 and out[0]["breakout"] == int(pd.Timestamp("2026-11-04 04:00Z").timestamp())
