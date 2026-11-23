"""Mô hình ICT trên kịch bản dựng tay (giờ New York, mùa đông = UTC-5)."""
import pandas as pd

from core.types import Direction
from data.candles import normalize, resample
from mtf.context import MarketContext
from mtf.view import TimeframeView
from signals import judas_swing, sweep_mss_fvg
from structure.liquidity import liquidity_pools, session_bounds, structural_pools
from structure.swings import Swing

NY = "America/New_York"
BASE = (2015.0, 2016.0, 2014.0, 2015.0)
OVERRIDES = {
    "2024-01-09 10:00": (2015, 2016, 2010, 2015),      # PDL 2010
    "2024-01-09 11:00": (2015, 2020, 2014, 2015),      # PDH 2020
    "2024-01-09 21:00": (2015, 2016, 2012.5, 2015),    # đáy range phiên Á 2012.5
    "2024-01-10 03:00": (2015, 2016, 2013, 2015),      # đáy phiên London 2013
    "2024-01-10 06:30": (2015, 2017, 2014, 2015),      # swing high tham chiếu cho MSS
    "2024-01-10 07:30": (2015, 2015.5, 2008, 2011),    # quét thanh khoản (killzone New York)
    "2024-01-10 07:45": (2011, 2012, 2010.5, 2011.5),  # c1
    "2024-01-10 08:00": (2011.5, 2019.5, 2011.2, 2019),  # c2: xung lực, đóng trên 2017 → MSS
    "2024-01-10 08:15": (2019, 2020.5, 2014, 2020),    # c3: FVG [2012, 2014]
    "2024-01-10 08:30": (2020, 2021, 2018, 2020.5),    # chưa hồi về FVG
}


def _scenario() -> pd.DataFrame:
    times = pd.date_range(pd.Timestamp("2024-01-09 00:00", tz=NY), pd.Timestamp("2024-01-10 08:30", tz=NY), freq="15min")
    rows = [OVERRIDES.get(t.strftime("%Y-%m-%d %H:%M"), BASE) for t in times]
    df = pd.DataFrame(rows, columns=["open", "high", "low", "close"]).assign(time=times.tz_convert("UTC"))
    return normalize(df, "M15").assign(atr=3.0)


def _ctx(cfg) -> MarketContext:
    m15 = _scenario()
    h4 = resample(m15.drop(columns="atr"), "H4").assign(atr=10.0)
    views = {"H4": TimeframeView("H4", h4, cfg), "M15": TimeframeView("M15", m15, cfg)}
    return MarketContext(m15["close_time"].iat[-1], views, {}, Direction.BUY, "M15")


def test_session_bounds_wrap_and_dst():
    begin, end = session_bounds(pd.Timestamp("2024-01-10").date(), "20:00", "00:00", NY)
    assert (begin.hour, begin.day, end.hour, end.day) == (20, 9, 0, 10)
    begin, _ = session_bounds(pd.Timestamp("2024-03-10").date(), "02:00", "05:00", NY)  # 02:00 không tồn tại
    assert begin.tz_convert("UTC").hour == 7


def test_liquidity_pools_known_values(cfg):
    df = _scenario()
    pools = {p.name: p.price for p in liquidity_pools(df, df["close_time"].iat[-1], ["pdh_pdl", "asia", "london"], cfg["sessions"])}
    assert pools["pdh"] == 2020 and pools["pdl"] == 2010
    assert pools["asia_low"] == 2012.5 and pools["london_low"] == 2013
    early = pd.Timestamp("2024-01-10 04:00", tz=NY).tz_convert("UTC")  # London chưa kết thúc
    assert "london_low" not in {p.name for p in liquidity_pools(df, early, ["london"], cfg["sessions"])}


def test_sweep_mss_fvg_setup(cfg):
    cfg["ict"]["premium_discount"] = False
    setups = sweep_mss_fvg.find(_ctx(cfg), cfg)
    assert len(setups) == 1  # quét cả đáy London lẫn PDL nhưng cùng một FVG → một setup
    s = setups[0]
    assert (s.zone.low, s.zone.high, s.invalidation) == (2012, 2014, 2008)
    assert 2020 in s.targets  # PDH là thanh khoản phía đối diện


def test_judas_swing_requires_killzone(cfg):
    cfg["ict"]["premium_discount"] = False
    setups = judas_swing.find(_ctx(cfg), cfg)
    assert [s.key.split(":")[1] for s in setups] == ["asia_low"]
    cfg["ict"]["killzones"] = ["london"]  # cú quét lúc 07:30 NY không nằm trong London
    assert judas_swing.find(_ctx(cfg), cfg) == []


def test_no_setup_against_bias(cfg):
    cfg["ict"]["premium_discount"] = False
    ctx = _ctx(cfg)
    bearish = MarketContext(ctx.time, ctx.views, {}, Direction.SELL, "M15")
    assert sweep_mss_fvg.find(bearish, cfg) == []


def test_structural_pools_swing_and_equal():
    t = pd.Timestamp("2024-01-10", tz="UTC")
    swings = [Swing(5, t, 2000.0, "low", 7), Swing(12, t, 2000.08, "low", 14), Swing(20, t, 2010.0, "high", 22),
              Swing(2, t, 1990.0, "low", 4)]
    pools = structural_pools(swings, ["swing", "equal"], since_index=5, equal_tolerance=0.1)
    names = {p.name.split("@")[0]: p for p in pools}
    assert {p.price for p in pools if p.kind == "swing"} == {2000.0, 2000.08, 2010.0}  # swing index 2 quá cũ
    assert names["equal_lows"].price == 2000.0 and names["equal_lows"].available_index == 15
