"""Kết nối MT5 riêng của giao diện web (bot chạy tiến trình khác). Mọi lệnh gọi MT5 đi qua một lock."""
from __future__ import annotations

import logging
import threading
import time
from collections.abc import Callable
from typing import Any, TypeVar

from core.mt5_client import connect

log = logging.getLogger(__name__)
T = TypeVar("T")

_RETRY_SECONDS = 15.0


class MT5Gateway:
    def __init__(self, cfg: dict) -> None:
        self._cfg = cfg
        self._lock = threading.RLock()
        self._mt5: Any = None
        self._last_attempt = 0.0
        self.error: str | None = None

    def _ensure(self) -> Any:
        if self._mt5 is not None:
            info = self._mt5.terminal_info()
            if info is not None and info.connected:
                return self._mt5
            self._mt5 = None
        if time.monotonic() - self._last_attempt < _RETRY_SECONDS:
            return None
        self._last_attempt = time.monotonic()
        try:
            self._mt5 = connect(self._cfg)
            self.error = None
        except Exception as exc:  # noqa: BLE001 — MT5 chưa mở / chưa đăng nhập: giao diện vẫn chạy bằng cache
            self.error = str(exc)
            self._mt5 = None
        return self._mt5

    def call(self, fn: Callable[[Any], T]) -> T | None:
        with self._lock:
            mt5 = self._ensure()
            if mt5 is None:
                return None
            try:
                return fn(mt5)
            except Exception as exc:  # noqa: BLE001
                log.exception("Lỗi gọi MT5")
                self.error = str(exc)
                self._mt5 = None
                return None

    @property
    def connected(self) -> bool:
        return self._mt5 is not None

    def account(self) -> dict | None:
        def read(mt5) -> dict | None:
            info = mt5.account_info()
            if info is None:
                return None
            return {"login": info.login, "server": info.server, "name": info.name, "currency": info.currency,
                    "balance": info.balance, "equity": info.equity, "margin_free": info.margin_free,
                    "demo": info.trade_mode == mt5.ACCOUNT_TRADE_MODE_DEMO,
                    "hedging": info.margin_mode == mt5.ACCOUNT_MARGIN_MODE_RETAIL_HEDGING}
        return self.call(read)

    def positions(self) -> dict[int, dict]:
        symbol, magic = self._cfg["symbol"], self._cfg["mt5"]["magic"]

        def read(mt5) -> dict[int, dict]:
            found = mt5.positions_get(symbol=symbol) or ()
            return {p.ticket: {"ticket": p.ticket, "volume": p.volume, "price_open": p.price_open,
                               "price_current": p.price_current, "sl": p.sl, "tp": p.tp, "profit": p.profit,
                               "buy": p.type == mt5.POSITION_TYPE_BUY, "comment": p.comment}
                    for p in found if p.magic == magic}
        return self.call(read) or {}

    def quote(self) -> dict | None:
        symbol = self._cfg["symbol"]

        def read(mt5) -> dict | None:
            tick = mt5.symbol_info_tick(symbol)
            info = mt5.symbol_info(symbol)
            if tick is None or info is None:
                return None
            return {"bid": tick.bid, "ask": tick.ask, "spread_points": round((tick.ask - tick.bid) / info.point)}
        return self.call(read)
