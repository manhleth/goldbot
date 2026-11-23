"""Smoke test API web với config cô lập (không MT5, cache giả lập trong thư mục tạm)."""
from pathlib import Path

import pytest
import yaml
from fastapi.testclient import TestClient

from data.candles import resample
from tests.conftest import ROOT, random_walk_m15
from web.app import create_app


@pytest.fixture(scope="module")
def client(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("web")
    cfg = yaml.safe_load((ROOT / "config.yaml").read_text(encoding="utf-8"))
    cfg["mt5"]["path"] = str(tmp / "no-terminal.exe")
    cfg["data"]["cache_dir"] = str(tmp / "cache")
    cfg["journal"] = {"live_db": str(tmp / "live.db"), "backtest_db": str(tmp / "backtest.db")}
    cfg["news"]["db"] = str(tmp / "news.db")
    for name, bot in cfg["bots"].items():
        bot["journal"] = str(tmp / f"bot_{name}.db")
    cfg["live"]["stop_file"] = str(tmp / "STOP")
    (tmp / "cache").mkdir()
    m5 = random_walk_m15(days=60, tf="M5")  # đủ >200 nến H4 cho EMA200
    for tf in ("M5", "M15", "H1", "H4"):
        frame = m5 if tf == "M5" else resample(m5, tf)
        frame.drop(columns="close_time").to_csv(tmp / "cache" / f"XAUUSD_{tf}.csv", index=False)
    config_path = tmp / "config.yaml"
    config_path.write_text(yaml.safe_dump(cfg, allow_unicode=True), encoding="utf-8")
    return TestClient(create_app(ROOT, config_path)), config_path


def test_status_and_market(client):
    c, _ = client
    status = c.get("/api/status").json()
    assert status["mt5"]["connected"] is False and status["bot"]["running"] is False
    candles = c.get("/api/candles", params={"tf": "M15", "bars": 50}).json()
    assert candles["source"] == "cache" and len(candles["candles"]) == 50 and "50" in candles["ema"]
    analysis = c.get("/api/analysis", params={"tf": "M15"}).json()
    assert analysis["ready"] and set(analysis["biases"]) == {"H4"}
    assert c.get("/api/candles", params={"tf": "D1"}).status_code == 400  # D1 không còn trong config


def test_journal_endpoints_empty(client):
    c, _ = client
    assert c.get("/api/positions").json() == {"legs": [], "unmanaged": []}
    assert c.get("/api/trades", params={"mode": "live"}).json() == []
    assert c.get("/api/report", params={"mode": "live"}).json()["summary"] is None
    assert c.get("/api/report", params={"mode": "backtest"}).status_code == 404
    assert c.get("/api/trades", params={"mode": "x"}).status_code == 400


def test_kill_switch_and_news_import(client):
    c, _ = client
    assert c.post("/api/killswitch", json={"enabled": True}).json()["kill_switch"] is True
    assert c.post("/api/killswitch", json={"enabled": False}).json()["kill_switch"] is False
    csv = b"time,title,country,impact,forecast,previous\n2030-01-10T13:30:00Z,CPI m/m,USD,High,0.4%,0.2%\n"
    assert c.post("/api/news/import", files={"file": ("n.csv", csv)}).json() == {"count": 1}
    events = c.get("/api/news", params={"days_back": 0, "days_ahead": 4000}).json()["events"]
    assert events[-1]["gold"] == "SELL"


def test_config_validation_keeps_file(client):
    c, path = client
    before = Path(path).read_text(encoding="utf-8")
    bad = before.replace("require_demo: true", "require_demo: false")
    assert c.put("/api/config", json={"text": bad}).status_code == 400
    assert Path(path).read_text(encoding="utf-8") == before
