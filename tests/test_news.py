import pandas as pd
import pytest

from core.types import Direction, Setup, Signal, Zone
from news.bias import gold_bias, parse_value
from news.calendar import build_calendar
from news.filter import alignment, forecast_view, news_reason
from news.forexfactory import parse_feed
from news.models import NewsEvent
from news.store import NewsStore

T = pd.Timestamp("2026-11-24 10:00", tz="UTC")


def _event(title, forecast, previous, hours=5, impact="High", country="USD"):
    return NewsEvent(T + pd.Timedelta(hours=hours), title, country, impact, forecast, previous)


def _signal(direction):
    setup = Setup("fvg_retest", direction, Zone(1, 2), 1, 1, (), "k")
    return Signal(T, setup, "engulfing", 1, 2, 50, {})


@pytest.mark.parametrize("text,value", [("0.3%", 0.3), ("201K", 201_000), ("-134.4B", -134.4e9), ("49.7", 49.7),
                                        ("", None), ("n/a", None)])
def test_parse_value(text, value):
    assert parse_value(text) == (pytest.approx(value) if value is not None else None)


def test_gold_bias_from_forecast(cfg):
    rules = cfg["news"]["usd_rules"]
    assert gold_bias(_event("Core CPI m/m", "0.4%", "0.3%"), rules) == Direction.SELL  # lạm phát cao → USD mạnh
    assert gold_bias(_event("Unemployment Rate", "4.3%", "4.1%"), rules) == Direction.BUY
    assert gold_bias(_event("Unemployment Claims", "210K", "201K"), rules) == Direction.BUY  # khớp Claims trước
    assert gold_bias(_event("FOMC Statement", "", ""), rules) == Direction.NEUTRAL
    assert gold_bias(_event("Core PCE Price Index m/m", "0.3%", "0.3%"), rules) == Direction.NEUTRAL


def test_calendar_filters_and_forecast_view(cfg):
    events = [_event("Non-Farm Employment Change", "180K", "150K"),
              _event("CPI m/m", "0.2%", "0.4%", hours=6),
              _event("Prelim GDP q/q", "3.5%", "3.4%", hours=7),
              _event("German PMI", "50", "40", country="EUR"),
              _event("HPI m/m", "0.2%", "0.3%", impact="Low"),
              _event("Retail Sales m/m", "0.9%", "0.1%", hours=30)]  # ngoài 24h
    cal = build_calendar(events, cfg["news"])
    assert len(cal.events) == 4
    view = cal.forecast_view(T, 24)
    assert view.score == -1 and view.direction == Direction.SELL  # NFP(-1) + CPI(+1) + GDP(-1)
    assert alignment(Direction.BUY, view) == "against"
    assert alignment(Direction.SELL, view) == "aligned"


def test_news_reason_rules(cfg):
    nc = cfg["news"]
    cal = build_calendar([_event("CPI m/m", "0.5%", "0.3%")], nc)  # vàng SELL
    buy, sell = _signal(Direction.BUY), _signal(Direction.SELL)
    assert news_reason(buy, cal, forecast_view(buy, cal, nc), nc) == "news_forecast_against"
    assert news_reason(sell, cal, forecast_view(sell, cal, nc), nc) is None
    nc["forecast_rule"] = "off"
    assert news_reason(buy, cal, forecast_view(buy, cal, nc), nc) is None
    blackout = build_calendar([_event("CPI m/m", "", "", hours=0.25)], {**nc, "forecast_rule": "block_against"})
    assert news_reason(buy, blackout, forecast_view(buy, blackout, nc), nc) == "news_blackout"


def test_parse_feed_converts_to_utc():
    events = parse_feed([{"title": "CPI m/m", "country": "USD", "date": "2026-11-25T08:30:00-05:00",
                          "impact": "High", "forecast": "0.3%", "previous": "0.4%"}, {"bad": 1}])
    assert len(events) == 1 and events[0].time == pd.Timestamp("2026-11-25 13:30", tz="UTC")


def test_store_upsert_and_csv(tmp_path):
    store = NewsStore(tmp_path / "news.db")
    store.upsert([_event("CPI m/m", "0.3%", "0.4%")])
    store.upsert([_event("CPI m/m", "0.5%", "0.4%")])  # cùng key → cập nhật
    assert [e.forecast for e in store.all()] == ["0.5%"]
    csv = b"time,title,country,impact,forecast,previous\n2024-01-11T13:30:00Z,CPI m/m,USD,High,0.2%,0.1%\n"
    assert store.import_csv(csv) == 1
    assert len(store.all()) == 2
