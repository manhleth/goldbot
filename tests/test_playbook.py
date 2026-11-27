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


def test_intraday_rules_close_before_friday_early_close():
    from playbook.methods_unified import _intraday
    rules = {"last_entry": "15:30", "flat": "16:30", "day_start": "17:00",
             "friday": {"last_entry": "14:30", "flat": "15:30"}}
    ny = "America/New_York"
    at = lambda s: pd.Timestamp(s, tz=ny).tz_convert("UTC")  # noqa: E731
    orders = [Order("thu", at("2026-07-23 10:00"), B, MARKET, sl_dist=1),     # thứ Năm → đóng 16:30
              Order("fri", at("2026-07-24 10:00"), B, MARKET, sl_dist=1),     # thứ Sáu → đóng 15:30
              Order("late", at("2026-07-24 14:45"), B, MARKET, sl_dist=1),    # thứ Sáu sau 14:30 → bỏ
              Order("thu_eve", at("2026-07-23 18:00"), B, MARKET, sl_dist=1)]  # tối thứ Năm = ngày giao dịch thứ Sáu
    out = {o.key: o.exit_at.tz_convert(ny).strftime("%a %H:%M") for o in _intraday(orders, ny, rules)}
    assert out == {"thu": "Thu 16:30", "fri": "Fri 15:30", "thu_eve": "Fri 15:30"}


def test_structure_trend_bos_trendline_warning_and_choch():
    from playbook.trend_structure import structure_trend
    from playbook.trendlines import LineRules
    pts = [(0, 100), (3, 106), (6, 101), (9, 108), (12, 102), (15, 110), (18, 103), (21, 109), (23, 103.0),
           (25, 105), (28, 100), (30, 99)]
    df = _zigzag(pts, 31)
    rules = LineRules(3, 0.3, 2, 8)
    neutral = structure_trend(df, 2, "neutral", rules, 0.2, 3)
    flip = structure_trend(df, 2, "flip", rules, 0.2, 3)
    assert list(neutral[9:23]) == [1] * 14 and list(neutral[23:27]) == [0] * 4 and list(neutral[27:]) == [-1] * 4
    assert list(flip[23:]) == [-1] * 8  # đảo chiều ngay khi trendline tăng bị phá
    no_tl = structure_trend(df, 2, "neutral", rules, 0.2, 3, use_trendline=False)
    assert list(no_tl[23:27]) == [1] * 4  # chỉ cấu trúc: vẫn tăng tới khi CHoCH


def test_weekend_rules_hold_overnight_and_close_friday():
    from playbook.methods_unified import _weekend
    rules = {"day_start": "17:00", "last_entry": "14:30", "flat": "15:30"}
    ny = "America/New_York"
    at = lambda s: pd.Timestamp(s, tz=ny).tz_convert("UTC")  # noqa: E731
    orders = [Order("sun", at("2026-07-19 19:00"), B, MARKET, sl_dist=1),     # tối Chủ nhật = phiên tuần mới
              Order("wed", at("2026-07-22 10:00"), B, MARKET, sl_dist=1),
              Order("fri", at("2026-07-24 10:00"), B, MARKET, sl_dist=1),
              Order("late", at("2026-07-24 14:45"), B, MARKET, sl_dist=1)]  # thứ Sáu sau 14:30 → bỏ
    out = {o.key: o.exit_at.tz_convert(ny).strftime("%m-%d %H:%M") for o in _weekend(orders, ny, rules)}
    assert out == {"sun": "07-24 15:30", "wed": "07-24 15:30", "fri": "07-24 15:30"}


def test_tf_hours_limits_timeframe_to_session():
    from playbook.methods_unified import _tf_hours
    ny = "America/New_York"
    at = lambda s: pd.Timestamp(s, tz=ny).tz_convert("UTC")  # noqa: E731
    orders = [Order("m15_ny", at("2026-07-22 09:00"), B, MARKET, sl_dist=1, meta={"tf": "M15"}),
              Order("m15_asia", at("2026-07-22 20:00"), B, MARKET, sl_dist=1, meta={"tf": "M15"}),
              Order("h1_asia", at("2026-07-22 20:00"), B, MARKET, sl_dist=1, meta={"tf": "H1"})]
    kept = _tf_hours(orders, ny, {"M15": ["07:00", "16:00"]})
    assert [o.key for o in kept] == ["m15_ny", "h1_asia"]


def test_session_exit_asia_same_day_others_next_day_capped_friday():
    from playbook.methods_unified import _session_exit
    rules = {"day_start": "17:00", "friday": {"last_entry": "14:30", "flat": "15:30"},
             "windows": [{"from": "17:00", "to": "02:00", "flat": "16:30", "days": 0},
                         {"from": "02:00", "to": "17:00", "flat": "16:30", "days": 1}]}
    ny = "America/New_York"
    at = lambda s: pd.Timestamp(s, tz=ny).tz_convert("UTC")  # noqa: E731
    orders = [Order("asia", at("2026-07-21 20:00"), B, MARKET, sl_dist=1),   # tối thứ Ba = ngày giao dịch thứ Tư
              Order("ny", at("2026-07-22 09:00"), B, MARKET, sl_dist=1),     # thứ Tư → 16:30 thứ Năm
              Order("thu", at("2026-07-23 10:00"), B, MARKET, sl_dist=1),    # thứ Năm → thứ Sáu đóng sớm 15:30
              Order("late", at("2026-07-24 15:00"), B, MARKET, sl_dist=1)]   # thứ Sáu sau 14:30 → bỏ
    out = {o.key: o.exit_at.tz_convert(ny).strftime("%a %H:%M") for o in _session_exit(orders, ny, rules)}
    assert out == {"asia": "Wed 16:30", "ny": "Thu 16:30", "thu": "Fri 15:30"}



def test_trail_tfs_skips_frames_missing_from_data():
    from types import SimpleNamespace
    from playbook.runner import trail_tfs
    v = {"trail": {"tf": ["M5", "M15", "H2"]}}
    assert trail_tfs(v) == ["M5", "M15", "H2"]
    assert trail_tfs(v, SimpleNamespace(frames={"M15": None, "H2": None})) == ["M15", "H2"]


def test_edge_pick_longest_and_wick_pierce():
    """Ba đỉnh giảm dần, đỉnh giữa vượt đường thẳng nối đỉnh đầu–cuối 0.5 ATR: chỉ nhận khi cho phép râu xuyên."""
    import numpy as np
    from playbook.patterns import UPPER, Bars, _edge
    n = 40
    h = np.full(n, 90.0); low = h - 5; c = h - 2; o = c
    for i, v in ((5, 110.0), (15, 107.0), (25, 100.0), (32, 98.0)):
        h[i] = v
    bars = Bars(o, h, low, c, np.full(n, 2.0), [5, 15, 25, 32], [], 3)
    p = {"window_bars": 80, "max_pivots": 8, "zone_atr": 0.3}
    strict = _edge(bars, UPPER, n - 1, {**p, "edge_pick": "longest"}, 0.6, 0.4, 2)
    loose = _edge(bars, UPPER, n - 1, {**p, "edge_pick": "longest", "pierce_atr": 1.0}, 0.6, 0.4, 2)
    newest = _edge(bars, UPPER, n - 1, {**p, "pierce_atr": 1.0}, 0.6, 0.4, 2)
    assert (loose.i1, loose.i2) == (5, 32)          # dài nhất: râu đỉnh 15 xuyên 1.44 ≤ 2.0 vẫn nhận
    assert (strict.i1, strict.i2) == (5, 15)        # không cho xuyên (≤ 0.6): chỉ còn đường ngắn 5→15
    assert newest.i2 == 32                          # mặc định: điểm neo thứ hai mới nhất


def test_edge_pick_list_builds_one_scan_per_mode():
    from playbook.patterns import _picks
    p = {"zone_atr": 0.3, "edge_pick": [{"pick": "touches", "pierce_atr": 1.0}, "newest"]}
    out = _picks(p)
    assert [(q["edge_pick"], q.get("pierce_atr")) for q in out] == [("touches", 1.0), ("newest", None)]
    assert _picks({"zone_atr": 0.3})[0]["edge_pick"] == "newest"


def test_min_lot_fallback_uses_minimum_volume_instead_of_skipping():
    from risk.sizing import lot_size
    # SL 30$ = 3.000$/lot → rủi ro 5$ chỉ đủ 0.0016 lot < tối thiểu 0.01
    assert lot_size(5.0, 30.0, SPEC) == 0.0
    assert lot_size(5.0, 30.0, SPEC, min_lot_fallback=True) == SPEC.volume_min


def test_regime_exit_trend_trails_d1_sideways_takes_profit_early():
    import numpy as np
    from playbook.common import MarketData
    from playbook.regime import apply_regime_exit
    from playbook.runner import apply_variant
    days = pd.date_range("2026-01-01", periods=60, freq="D", tz="UTC")
    trend = np.arange(60) * 10.0 + 1000                       # tăng đều → ADX cao
    d1 = pd.DataFrame({"time": days, "open": trend, "high": trend + 3, "low": trend - 3, "close": trend + 2,
                       "close_time": days + pd.Timedelta(days=1)})
    wave = 1000 + 20 * np.sin(np.arange(60) / 2.0)          # dao động quanh 1000 → ADX thấp
    flat = d1.assign(open=wave, high=wave + 6, low=wave - 6, close=wave)
    cfg = {"adx": {"tf": "D1", "period": 14, "threshold": 25}, "trend": {"trail_tf": "D1"}, "sideways": {"tp_r": 1.5}}
    order = Order("one:flag@H4:x:BUY", days[-1] + pd.Timedelta(days=1), B, MARKET, sl_dist=10.0, tp=2000.0)
    up = apply_regime_exit([order], MarketData({"D1": d1}, "UTC", 0.01, "M15"), cfg)[0]
    side = apply_regime_exit([order], MarketData({"D1": flat}, "UTC", 0.01, "M15"), cfg)[0]
    assert up.meta["regime"] == "trend" and up.meta["trail_tf"] == "D1" and up.tp == 2000.0
    assert side.meta["regime"] == "sideways" and side.tp is None and side.tp_dist == 15.0
    variant = {"take_profit": False, "trail": {"tf": ["H4", "D1"]}}
    v_up, v_side = apply_variant([up, side], variant, "hold")
    assert v_up.trail == "hold@D1" and v_up.tp is None           # xu hướng: bỏ TP, gồng theo D1
    assert v_side.trail == "hold@H4" and v_side.tp_dist == 15.0   # đi ngang: giữ TP 1.5R


def test_macro_blocks_orders_against_last_w1_breakout_and_scales_aligned_risk():
    from playbook.macro import apply_macro
    t0 = pd.Timestamp("2024-03-31", tz="UTC")
    series = pd.DataFrame({"close_time": [t0 - pd.Timedelta(days=700), t0], "state": [-1, 1]})
    buy = Order("b", t0 + pd.Timedelta(days=3), B, MARKET, sl_dist=1)
    sell = Order("s", t0 + pd.Timedelta(days=3), S, MARKET, sl_dist=1)
    early = Order("e", t0 - pd.Timedelta(days=900), B, MARKET, sl_dist=1)     # trước mọi cú phá → trạng thái 0
    out = apply_macro([early, buy, sell], series, {"mode": "block_against", "risk_with": 1.5, "risk_neutral": 0.5})
    assert [o.key for o in out] == ["e", "b"]
    assert out[0].risk_scale == 0.5 and out[1].risk_scale == 1.5 and out[1].meta["macro"] == 1


def test_macro_confirmed_break_needs_long_pattern_and_holding_closes(monkeypatch):
    import numpy as np
    from playbook.macro import confirmed_breaks
    from playbook.patterns import Edge, Signal
    import playbook.macro as macro
    n = 80
    t = pd.date_range("2020-01-05", periods=n, freq="7D", tz="UTC")
    close = np.full(n, 100.0)
    close[61:64] = [112.0, 113.0, 109.0]                        # phá ở nến 60, giữ 2 nến rồi thủng lại
    df = pd.DataFrame({"time": t, "close": close, "close_time": t + pd.Timedelta(days=7)})
    flat = Edge(0, 110.0, 40, 110.0, 3)
    sigs = [Signal(60, B, "neckline_break", 110.0, 130.0, "", (flat,)),            # dài 60 nến
            Signal(60, B, "neckline_break", 110.0, 130.0, "", (Edge(50, 110.0, 55, 110.0, 3),))]  # chỉ 10 nến
    monkeypatch.setattr(macro, "scan_all", lambda df_, p, swing: sigs)
    two = confirmed_breaks(df, {"patterns": {}, "swing": 3, "min_span": 52, "confirm_bars": 2})
    three = confirmed_breaks(df, {"patterns": {}, "swing": 3, "min_span": 52, "confirm_bars": 3})
    assert [(x[0], x[1]) for x in two] == [(df["close_time"].iat[62], 1)]   # mẫu hình 10 nến bị loại
    assert three == []                                                       # nến thứ 3 đóng lại dưới cạnh


def test_rsi_course_wma_and_sideway_flag():
    import numpy as np
    from playbook.rsi_course import _sideway_flags, wma
    s = pd.Series(np.arange(1.0, 11.0))
    assert wma(s, 3).iat[-1] == pytest.approx((8 * 1 + 9 * 2 + 10 * 3) / 6)
    t = pd.date_range("2026-01-01", periods=30, freq="4h", tz="UTC")
    calm = pd.DataFrame({"close_time": t, "rsi": 50 + 5 * np.sin(np.arange(30))})
    spiky = calm.assign(rsi=np.r_[np.full(25, 50.0), [75, 55, 52, 50, 49]])
    cfg = {"band": [40, 60], "extremes": [30, 70], "window": 10}
    assert bool(_sideway_flags(calm, cfg)["flag"].iat[-1])
    assert not bool(_sideway_flags(spiky, cfg)["flag"].iat[-1])   # vừa có RSI 75 trong 10 nến → có lực


def test_lock_steps_move_stop_to_locked_profit():
    # vào 100 (SL 90 → R = 10): lên 121 (≥ 2R → khoá +0.5R = 105), rồi rơi về 100 → thoát ở 105, +0.5R
    rows = [(100, 100, 100, 100), (100, 121, 100, 120), (120, 120, 100, 100), (100, 100, 100, 100)]
    order = Order("k", _t(0), B, MARKET, sl_dist=10, lock_steps=((2.0, 0.5), (4.0, 2.0)))
    out = _sim(rows).run(order)
    assert out.legs[0].exit_reason == "lock" and out.legs[0].exit_price == pytest.approx(105.0)


def test_capped_risk_and_lot_cap():
    from risk.sizing import capped, capped_risk, lot_size
    caps = [[5000, 5.0], [500, 10.0]]
    assert capped_risk(20.0, caps, 300) == 20.0 and capped_risk(20.0, caps, 500) == 10.0
    assert capped_risk(20.0, caps, 8000) == 5.0 and capped_risk(3.0, caps, 8000) == 3.0   # không tăng rủi ro
    assert lot_size(1_000_000, 10.0, capped(SPEC, 5)) == 5.0          # trần 5 lot
    assert capped(SPEC, None) is SPEC
