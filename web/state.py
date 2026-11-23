"""Các service dùng chung của ứng dụng web."""
from __future__ import annotations

from pathlib import Path

from fastapi import Request

from core.config import load_config
from journal.db import Journal
from news.store import NewsStore
from web.services.market import MarketData
from web.services.mt5_gateway import MT5Gateway
from web.services.processes import ManagedProcess


class AppState:
    def __init__(self, root: Path, config_path: Path) -> None:
        self.root = root
        self.config_path = config_path
        self.bot = ManagedProcess("live", root, config_path)
        self.backtest = ManagedProcess("backtest", root, config_path)
        self.reload()
        self.bots = {name: ManagedProcess(f"bot_{name}", root, config_path) for name in self.cfg.get("bots", {})}

    def reload(self) -> None:
        self.cfg = load_config(self.config_path)
        self.gateway = MT5Gateway(self.cfg)
        self.market = MarketData(self.cfg, self.gateway)
        self.news = NewsStore(self.cfg["news"]["db"])

    def journal(self, mode: str) -> Journal:
        """live | backtest | bot:<tên> (journal riêng của từng bot ONE)."""
        if mode.startswith("bot:"):
            name = mode.split(":", 1)[1]
            if name not in self.cfg.get("bots", {}):
                raise ValueError(f"không có bot {name}")
            return Journal(self.cfg["bots"][name]["journal"])
        if mode not in ("live", "backtest"):
            raise ValueError("mode phải là live, backtest hoặc bot:<tên>")
        return Journal(self.cfg["journal"][f"{mode}_db"])

    @property
    def stop_file(self) -> Path:
        return self.root / self.cfg["live"]["stop_file"]


def get_state(request: Request) -> AppState:
    return request.app.state.app_state


def is_live(mode: str) -> bool:
    return mode == "live" or mode.startswith("bot:")
