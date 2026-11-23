"""Breakout range H1 trên kịch bản dựng tay (ATR = 2 → range tối đa cao 6)."""
from core.types import Direction
from mtf.context import MarketContext
from mtf.view import TimeframeView
from signals import range_breakout
from tests.conftest import make_bars

RANGE = [(2002, 2004, 2000, 2002)] * 19 + [(2003, 2003.5, 2001, 2001.5)]  # 20 nến tích lũy, nến cuối giảm = OB
BREAKOUT = [(2001.5, 2008.5, 2001.5, 2008),   # nến phá: đóng trên đỉnh range 2004, thân lớn
            (2008, 2011, 2007, 2010.5),       # tạo FVG [2003.5, 2007] (c1 = nến OB)
            (2010.5, 2012, 2008, 2011)]       # chưa hồi về (không tạo FVG thứ hai)


def _ctx(cfg, rows, direction=Direction.BUY):
    view = TimeframeView("H1", make_bars(rows, "H1", atr=2.0), cfg)
    return MarketContext(view.df["close_time"].iat[-1], {"H1": view}, {}, direction, "H1")


def test_breakout_gives_fvg_and_order_block_setups(cfg):
    setups = {s.key.split(":")[1]: s for s in range_breakout.find(_ctx(cfg, RANGE + BREAKOUT), cfg)}
    assert set(setups) == {"fvg", "order_block"}
    fvg, ob = setups["fvg"], setups["order_block"]
    assert (fvg.zone.low, fvg.zone.high, fvg.invalidation) == (2003.5, 2007, 2002)  # giữa range = 2002
    assert (ob.zone.low, ob.zone.high, ob.invalidation) == (2001, 2003.5, 2001)
    assert fvg.targets == (2008,)  # đỉnh range 2004 + chiều cao 4


def test_no_setup_against_trend_or_after_failed_breakout(cfg):
    assert range_breakout.find(_ctx(cfg, RANGE + BREAKOUT, Direction.SELL), cfg) == []
    failed = RANGE + BREAKOUT + [(2011, 2011, 2000.5, 2000.8)]  # đóng cửa dưới invalidation của cả hai vùng
    assert range_breakout.find(_ctx(cfg, failed), cfg) == []


def test_range_too_tall_or_too_short_is_ignored(cfg):
    tall = [(2002, 2008, 2000, 2002)] * 19 + [RANGE[-1]]  # cao 8 > 3 × ATR
    assert range_breakout.find(_ctx(cfg, tall + BREAKOUT), cfg) == []
    assert range_breakout.find(_ctx(cfg, RANGE[-8:] + BREAKOUT), cfg) == []  # 8 nến < min_bars


def test_setup_expires_after_second_touch(cfg):
    touches = RANGE + BREAKOUT + [(2011, 2011, 2006, 2008), (2008, 2012, 2008, 2011), (2011, 2011, 2006.5, 2009)]
    assert "fvg" not in {s.key.split(":")[1] for s in range_breakout.find(_ctx(cfg, touches), cfg)}
