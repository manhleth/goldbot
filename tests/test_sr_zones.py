"""Vùng S/R cứng: gom swing thành vùng, khoảng trống tới vùng cản, phá qua vùng, áp vào lệnh ONE."""
import numpy as np
import pandas as pd
import pytest

from core.types import Direction
from playbook.orders import MARKET, Order
from playbook.sr_zones import ZoneBook, _cluster, apply_sr, cleared, obstacle

T0 = pd.Timestamp("2026-03-02 12:00", tz="UTC")
CFG = {"room": {"min_r": 1.5}, "break_bonus": {"risk_mult": 1.5},
       "take_partial": {"fraction": 0.5, "buffer_atr": 0.1, "min_r": 1.0}}


def test_cluster_groups_swings_within_tolerance_and_needs_min_touches():
    prices = np.array([100.0, 100.4, 103.0, 106.0, 106.3, 106.5, 110.0])
    index = np.array([1, 9, 3, 2, 12, 5, 7])
    assert _cluster(prices, index, 0.5, 2) == [(100.0, 100.4, 9), (106.0, 106.5, 12)]


def test_obstacle_is_gap_to_nearest_zone_ahead_and_zero_inside_zone():
    zones = np.array([[95.0, 96.0], [104.0, 105.0], [110.0, 111.0]])
    assert obstacle(zones, 1, 100.0) == pytest.approx(4.0)
    assert obstacle(zones, -1, 100.0) == pytest.approx(4.0)
    assert obstacle(zones, 1, 104.5) == 0.0
    assert obstacle(zones, 1, 112.0) is None


def test_cleared_when_close_crosses_far_edge():
    zones = np.array([[104.0, 105.0]])
    assert cleared(zones, 1, 104.5, 105.5)
    assert not cleared(zones, 1, 105.2, 106.0)   # đã ở trên vùng từ trước
    assert cleared(zones, -1, 104.5, 103.5)


def _order(entry, sl_dist, prev_close):
    return Order("one:flag@H4:x:BUY", T0, Direction.BUY, MARKET, sl_dist=sl_dist, reasons=("flag",),
                 meta={"entry": entry, "prev_close": prev_close})


def test_apply_sr_filters_no_room_scales_risk_on_break_and_sets_partial():
    book = ZoneBook(np.array([np.datetime64("2026-03-01")], dtype="datetime64[ns]"),
                    [np.array([[99.0, 100.0], [106.0, 107.0]])], np.array([1.0]))
    blocked = _order(103.0, 2.5, 102.5)        # vùng cản cách 3 < 1.5 × 2.5
    broke = _order(101.0, 2.0, 99.5)           # đóng cửa vượt vùng 99–100; vùng cản cách 5 ≥ 3
    out = apply_sr([blocked, broke], book, CFG)
    assert len(out) == 1
    o = out[0]
    assert o.risk_scale == 1.5 and o.tp1_dist == pytest.approx(5.0 - 0.1) and o.tp1_fraction == 0.5
    assert "phá qua vùng S/R cứng" in o.reasons


def test_zone_expires_after_max_age_bars_since_last_touch():
    from playbook.sr_zones import _snapshots
    n = 60
    t = pd.date_range("2026-01-01", periods=n, freq="4h", tz="UTC")
    base = np.full(n, 100.0)
    high, low = base + 1, base - 1
    for i in (5, 15):            # hai đỉnh ~110 → một vùng kháng cự, chạm lần cuối ở nến 15
        high[i] = 110.0 + (i == 15) * 0.2
    df = pd.DataFrame({"time": t, "open": base, "high": high, "low": low, "close": base,
                       "close_time": t + pd.Timedelta(hours=4)})
    snaps = _snapshots(df, 2, 100, 10, 0.5, 2, 3)
    has_zone = {k: any(a >= 109 for a, _ in zones) for k, (tt, zones, _) in enumerate(snaps)}
    times = [tt for tt, _, _ in snaps]
    alive = [tt for (tt, zones, _) in snaps if any(a >= 109 for a, _ in zones)]
    assert alive and max(alive) < df["close_time"].iat[15 + 10 + 1]   # tới nến 26 vùng đã hết hạn
    assert times[-1] >= df["close_time"].iat[26] and not has_zone[len(snaps) - 1]


def test_weekly_bars_from_daily_close_with_last_daily_bar():
    from playbook.sr_zones import weekly
    days = pd.date_range("2026-03-02", periods=10, freq="D", tz="UTC")   # thứ Hai 2/3 → thứ Tư 11/3
    d = pd.DataFrame({"time": days, "open": np.arange(10.0), "high": np.arange(10.0) + 1,
                      "low": np.arange(10.0) - 1, "close": np.arange(10.0) + 0.5, "close_time": days + pd.Timedelta(days=1)})
    w = weekly(d)
    assert len(w) == 2 and w["high"].iat[0] == 6.0 and w["close"].iat[0] == 5.5   # thứ Hai 2/3 → thứ Bảy 7/3
    assert w["close_time"].iat[0] == pd.Timestamp("2026-03-08", tz="UTC") and w["close_time"].iat[1] == days[-1] + pd.Timedelta(days=1)
