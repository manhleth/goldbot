"""Bộ khớp lệnh sổ tay: market/limit/stop, SL trước TP, hòa vốn, chốt một phần, sự kiện thoát, giới hạn vị thế."""
import pandas as pd
import pytest

from core.types import Direction
from playbook.methods_structure import structure_breaks
from playbook.orders import EXIT, LIMIT, MARKET, STOP, Event, Order
from playbook.portfolio import Limits, simulate
from playbook.simulator import Bars, OrderSimulator
from risk.sizing import SymbolSpec
from tests.conftest import make_bars

SPEC = SymbolSpec(point=0.01, tick_size=0.01, tick_value=1.0, volume_min=0.01, volume_step=0.01, volume_max=100)
T0 = pd.Timestamp("2024-01-01", tz="UTC")
B, S = Direction.BUY, Direction.SELL


def _bars(rows, spread_points=0.0):
    df = make_bars(rows, "M5").assign(spread=spread_points)
    return Bars.from_frame(df, SPEC.point, 0.0, pd.Timedelta(minutes=5))


def _sim(rows, events=(), spread_points=0.0):
    return OrderSimulator(_bars(rows, spread_points), SPEC, 100.0, 0.0, list(events))


def _t(i):
    return T0 + pd.Timedelta(minutes=5 * i)


def test_market_fills_at_next_open_and_hits_tp():
    sim = _sim([(100, 100.5, 99.5, 100), (100, 101, 99.8, 100.8), (100.8, 103, 100.5, 102.5)])
    out = sim.run(Order("k", _t(1), B, MARKET, sl_dist=1.0, tp_dist=2.0))
    assert out.entry == 100 and out.legs[0].exit_reason == "tp" and out.r_multiple() == pytest.approx(2.0)


def test_sl_counts_first_when_both_in_same_bar():
    sim = _sim([(100, 100, 100, 100), (100, 103, 98, 100)])
    out = sim.run(Order("k", _t(1), B, MARKET, sl_dist=1.0, tp_dist=2.0))
    assert out.r_multiple() == pytest.approx(-1.0)


def test_limit_fill_bar_checks_only_sl():
    rows = [(100, 100, 100, 100), (100, 103, 98.9, 101), (101, 101.5, 100.5, 101)]
    out = _sim(rows).run(Order("k", _t(0), B, LIMIT, price=99.0, sl=98.0, tp=101.0))
    # nến 1 chạm limit 99 và lên tới 103, nhưng TP chỉ xét từ nến sau → nến 2 chạm TP 101
    assert out.entry == 99.0 and out.legs[0].exit_reason == "tp" and out.entry_time == _t(1)


def test_stop_order_gap_fills_at_open_and_expiry():
    rows = [(100, 100.5, 99.5, 100), (102, 103, 101.5, 102.5)]
    out = _sim(rows).run(Order("k", _t(0), B, STOP, price=101.0, sl=99.0, tp=110.0))
    assert out.entry == 102.0  # mở gap qua giá stop
    expired = _sim(rows).run(Order("k", _t(0), B, STOP, price=105.0, sl=99.0, tp=110.0, expiry=_t(2)))
    assert expired.status == "expired"


def test_breakeven_by_r_then_stopped_at_entry():
    rows = [(100, 100, 100, 100), (100, 101.6, 99.5, 101), (101, 101.2, 99.0, 99.5)]
    out = _sim(rows).run(Order("k", _t(1), B, MARKET, sl_dist=1.0, tp_dist=2.0, be_trigger_r=1.5))
    assert out.legs[0].exit_reason == "breakeven" and out.r_multiple() == pytest.approx(0.0)


def test_partial_tp1_then_runner_breakeven_with_offset():
    rows = [(100, 100, 100, 100), (100, 101.2, 99.8, 101), (101, 101.1, 99.5, 100)]
    out = _sim(rows).run(Order("k", _t(1), B, MARKET, sl_dist=1.5, tp_dist=2.0, tp1_dist=1.0, be_offset=0.1))
    reasons = {leg.name: leg.exit_reason for leg in out.legs}
    assert reasons == {"tp1": "tp1", "runner": "breakeven"}
    assert out.legs[1].exit_price == pytest.approx(100.1)


def test_exit_event_closes_at_next_open():
    rows = [(100, 100, 100, 100), (100, 100.5, 99.8, 100.2), (100.4, 100.6, 100.3, 100.5)]
    sim = _sim(rows, events=[Event(_t(2), B, (EXIT,))])
    out = sim.run(Order("k", _t(1), B, MARKET, sl_dist=5.0))
    assert out.legs[0].exit_reason == "time" and out.legs[0].exit_price == 100.4


def test_sell_uses_ask_for_exit():
    sim = _sim([(100, 100, 100, 100), (100, 100.9, 99.5, 100)], spread_points=20)  # spread 0.20
    out = sim.run(Order("k", _t(1), S, MARKET, sl_dist=1.0))
    assert out.entry == 100 and out.legs[0].exit_reason == "sl"  # ask cao nhất 101.1 > SL 101


def test_max_positions_blocks_overlapping_orders():
    rows = [(100, 100.2, 99.9, 100)] * 10
    sim = _sim(rows)
    orders = [Order("a", _t(1), B, MARKET, sl_dist=5.0, exit_at=_t(5)), Order("b", _t(3), B, MARKET, sl_dist=5.0),
              Order("c", _t(5), B, MARKET, sl_dist=5.0, exit_at=_t(7))]
    sessions = {"timezone": "America/New_York", "trading_day_start": "17:00"}
    statuses = [o.status for o in simulate(orders, sim, Limits(1), SPEC, sessions)]
    assert statuses == ["filled", "skipped", "filled"]  # c khớp đúng lúc a đóng


def test_structure_breaks_first_close_beyond_confirmed_swing():
    rows = [(10, 11, 9, 10), (10, 12, 9.5, 11), (11, 15, 10, 14), (14, 14.5, 12, 13), (13, 13.5, 11, 12),
            (12, 12.5, 10.5, 11), (11, 14, 10.8, 13.8), (13.8, 16, 13, 15.5), (15.5, 17, 15, 16.5)]
    breaks = structure_breaks(make_bars(rows, "M15"), 2)
    assert (7, B, 2) in breaks  # swing high 15 ở nến 2 (xác nhận ở nến 4), nến 7 đóng 15.5 > 15


def test_structure_trail_only_uses_swings_confirmed_after_entry():
    import numpy as np
    from playbook.simulator import TrailSeries
    rows = [(100, 100, 100, 100), (100, 101, 99.8, 100.8), (100.8, 103, 100.5, 102.8), (102.8, 104, 102, 103.5),
            (103.5, 103.6, 101.4, 101.6)]
    n = len(rows)
    level = {B: np.array([99.9, 99.9, 99.9, 101.5, 101.5]), S: np.full(n, np.nan)}
    confirmed = {B: np.array([0, 0, 0, 3, 3]), S: np.full(n, -1)}  # swing 99.9 có trước lúc vào → bỏ qua
    sim = OrderSimulator(_bars(rows), SPEC, 100.0, 0.0, [], {"t": TrailSeries(level, confirmed)})
    out = sim.run(Order("k", _t(1), B, MARKET, sl_dist=1.0, trail="t"))
    assert out.legs[0].exit_reason == "trail" and out.legs[0].exit_price == 101.5


def _zigzag(points, n):
    """Nến đi qua các đỉnh/đáy cho trước (nội suy tuyến tính), open = giữa hai close liền nhau."""
    import numpy as np
    xs, ys = zip(*points)
    closes = np.interp(np.arange(n), xs, ys)
    rows = []
    for i in range(n):
        o = (closes[i - 1] + closes[i]) / 2 if i else closes[0]
        rows.append((o, max(o, closes[i]) + 0.1, min(o, closes[i]) - 0.1, closes[i]))
    return make_bars(rows, "H1")


def test_trendline_needs_three_touches_and_detects_channel():
    import numpy as np
    from playbook.trendlines import LineRules, build
    # đáy 98/100/102 ở nến 2/8/14 thẳng hàng, đỉnh 105/107/109 song song phía trên, sau đó giá thủng đường
    df = _zigzag([(0, 101), (2, 98), (5, 105), (8, 100), (11, 107), (14, 102), (17, 109), (22, 96)], 24)
    rules = LineRules(min_touches=3, touch_tol_atr=0.3, channel_min_touches=2, max_pivots=8)
    tl = build(df, swing=2, rules=rules, break_atr=0.2, atr_period=3)
    low2 = df["low"].iat[2]
    line_at = lambda i: low2 + (i - 2) * (df["low"].iat[8] - low2) / 6  # noqa: E731
    assert tl.value[B][16] == pytest.approx(line_at(16))
    assert tl.channel[B][16] == pytest.approx(line_at(16) + (df["high"].iat[5] - line_at(5)))
    assert any(b.side == B and b.line.touches == 3 for b in tl.breaks)
    four = build(df, swing=2, rules=LineRules(4, 0.3, 2, 8), break_atr=0.2, atr_period=3)
    assert np.isnan(four.value[B][16])  # chỉ có 3 điểm chạm → không đủ 4


PATTERN_P = {"atr": 3, "window_bars": 30, "max_pivots": 8, "min_touches": 2, "neck_touches": 3, "zone_atr": 0.3,
             "break_atr": 0.2, "min_bars": 12, "min_height_atr": 1.5, "max_height_atr": 12, "parallel_tol": 0.3,
             "pole_bars": 20, "pole_atr": 4.0, "pole_height_ratio": 1.0}


def test_pattern_scan_finds_channel_breakout_up():
    from playbook.patterns import scan
    pts = [(0, 100), (3, 106), (6, 101), (9, 107), (12, 102), (15, 108), (18, 103), (21, 109), (24, 104), (27, 118),
           (30, 119)]
    df = _zigzag(pts, 31)
    signals = scan(df, PATTERN_P, swing=2)
    breaks = [s for s in signals if s.kind.endswith("_break") or s.kind == "flag"]
    assert breaks and breaks[0].direction == B and breaks[0].k == 26
    assert breaks[0].kind in ("channel_break", "flag")
    assert breaks[0].target > breaks[0].line  # measured move phía trên cạnh bị phá


def test_learning_gate_uses_only_closed_paper_results():
    from playbook.learning import Experience, gate
    t = lambda h: T0 + pd.Timedelta(hours=h)  # noqa: E731
    exp = Experience({"flag@H4": [t(1), t(2), t(3)], "bad@H4": [t(1), t(2)]},
                     {"flag@H4": [1.0, -1.0, 2.0], "bad@H4": [-1.0, -0.5]})
    lc = {"min_trades": 2, "window": 20, "min_expectancy": 0.0}
    orders = [Order("p:flag@H4:a:BUY", t(1.5), B, MARKET, sl_dist=1.0),   # mới có 1 kết quả → chưa đủ
              Order("p:flag@H4:b:BUY", t(3.5), B, MARKET, sl_dist=1.0),   # 3 kết quả, TB +0.67R → vào
              Order("p:bad@H4:c:BUY", t(5), B, MARKET, sl_dist=1.0)]      # TB âm → ngưng
    accepted, rejected = gate(orders, exp, lc)
    assert [o.key for o in accepted] == ["p:flag@H4:b:BUY"]
    assert [r.reason for r in rejected] == ["learning_insufficient", "learning_negative"]


def test_channel_bias_filter_uses_only_earlier_calls():
    from playbook.bias import apply_bias
    bias = pd.DataFrame({"time": [T0, T0 + pd.Timedelta(days=10)], "bias": [1, -1]})
    t = lambda d: T0 + pd.Timedelta(days=d)  # noqa: E731
    orders = [Order("a", t(5), B, MARKET, sl_dist=1), Order("b", t(10), B, MARKET, sl_dist=1),  # lúc 10: chưa biết bài mới
              Order("c", t(11), B, MARKET, sl_dist=1), Order("d", t(100), S, MARKET, sl_dist=1)]
    kept, rejected = apply_bias(orders, bias, valid_days=60, mode="block_against")
    assert [o.key for o in kept] == ["a", "b", "d"] and [r.reason for r in rejected] == ["against_channel_bias"]
    kept, rejected = apply_bias(orders, bias, valid_days=60, mode="strict")
    assert [o.key for o in kept] == ["a", "b"] and {r.reason for r in rejected} == {"against_channel_bias", "no_channel_bias"}
