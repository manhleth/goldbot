import pandas as pd
import pytest

from core.config import ConfigError, validate
from data.candles import closed_end, closed_only, resample
from data.server_time import server_to_utc, utc_to_server
from tests.conftest import make_bars


def test_normalize_adds_close_time_and_sorts():
    df = make_bars([(1, 2, 0.5, 1.5), (1.5, 2.5, 1, 2)], "H1")
    assert list(df["close_time"] - df["time"]) == [pd.Timedelta(hours=1)] * 2


def test_closed_only_drops_forming_bar():
    df = make_bars([(1, 2, 0, 1)] * 3, "H1")  # 00:00, 01:00, 02:00
    now = pd.Timestamp("2024-01-01 02:30", tz="UTC")
    assert len(closed_only(df, now)) == 2
    assert closed_end(df, pd.Timestamp("2024-01-01 02:00", tz="UTC")) == 2


def test_server_time_ny_close_follows_us_dst():
    winter = server_to_utc(pd.Series([pd.Timestamp("2024-01-10 10:00")]), "ny_close").iat[0]
    summer = server_to_utc(pd.Series([pd.Timestamp("2024-07-10 10:00")]), "ny_close").iat[0]
    assert winter == pd.Timestamp("2024-01-10 08:00", tz="UTC")  # GMT+2
    assert summer == pd.Timestamp("2024-07-10 07:00", tz="UTC")  # GMT+3


def test_server_time_fixed_offset_roundtrip():
    utc = server_to_utc(pd.Series([pd.Timestamp("2024-03-01 12:00")]), 2).iat[0]
    assert utc == pd.Timestamp("2024-03-01 10:00", tz="UTC")
    assert utc_to_server(utc, 2) == pd.Timestamp("2024-03-01 12:00")
    assert utc_to_server(pd.Timestamp("2024-07-10 07:00", tz="UTC"), "ny_close") == pd.Timestamp("2024-07-10 10:00")


def test_invalid_server_time_rejected():
    with pytest.raises(ConfigError):
        server_to_utc(pd.Series([pd.Timestamp("2024-01-01")]), "abc")


def test_resample_m15_to_h1():
    df = make_bars([(1, 2, 0.5, 1.5), (1.5, 3, 1, 2), (2, 2.5, 0.2, 1), (1, 1.2, 0.9, 1.1)], "M15")
    h1 = resample(df, "H1")
    assert len(h1) == 1
    row = h1.iloc[0]
    assert (row["open"], row["high"], row["low"], row["close"]) == (1, 3, 0.2, 1.1)


def test_config_requires_demo(cfg):
    cfg["account"]["require_demo"] = False
    with pytest.raises(ConfigError):
        validate(cfg)
