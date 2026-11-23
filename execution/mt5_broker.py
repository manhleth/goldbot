"""Gửi lệnh / quản lý vị thế qua MT5. Mọi lệnh đều kiểm tra lại tài khoản demo trước khi gửi."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import pandas as pd

from core.types import Direction
from data.server_time import server_to_utc
from risk.sizing import SymbolSpec

log = logging.getLogger(__name__)


class BrokerError(RuntimeError):
    pass


class DemoAccountRequired(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class ClosedResult:
    price: float
    time: pd.Timestamp
    profit: float
    reason: str


class MT5Broker:
    def __init__(self, mt5: Any, symbol: str, magic: int, deviation: int, server_time) -> None:
        self._mt5 = mt5
        self._symbol = symbol
        self._magic = magic
        self._deviation = deviation
        self._server_time = server_time

    # ---------- tài khoản ----------
    def is_connected(self) -> bool:
        info = self._mt5.terminal_info()
        return info is not None and bool(info.connected)

    def _account(self):
        info = self._mt5.account_info()
        if info is None:
            raise BrokerError(f"Không đọc được account_info: {self._mt5.last_error()}")
        return info

    def ensure_demo(self) -> None:
        if self._account().trade_mode != self._mt5.ACCOUNT_TRADE_MODE_DEMO:
            raise DemoAccountRequired("Tài khoản MT5 KHÔNG phải demo — bot dừng, không đặt lệnh.")

    def supports_hedging(self) -> bool:
        return self._account().margin_mode == self._mt5.ACCOUNT_MARGIN_MODE_RETAIL_HEDGING

    def equity(self) -> float:
        return float(self._account().equity)

    # ---------- symbol ----------
    def _symbol_info(self):
        info = self._mt5.symbol_info(self._symbol)
        if info is None:
            raise BrokerError(f"Không đọc được symbol_info {self._symbol}")
        return info

    def symbol_spec(self) -> SymbolSpec:
        info = self._symbol_info()
        return SymbolSpec(point=info.point, tick_size=info.trade_tick_size, tick_value=info.trade_tick_value,
                          volume_min=info.volume_min, volume_step=info.volume_step, volume_max=info.volume_max)

    def quote(self) -> tuple[float, float]:
        tick = self._mt5.symbol_info_tick(self._symbol)
        if tick is None:
            raise BrokerError(f"Không có giá {self._symbol}")
        return float(tick.bid), float(tick.ask)

    def _filling(self) -> int:
        mode = self._symbol_info().filling_mode
        if mode & 1:
            return self._mt5.ORDER_FILLING_FOK
        if mode & 2:
            return self._mt5.ORDER_FILLING_IOC
        return self._mt5.ORDER_FILLING_RETURN

    def _round(self, price: float) -> float:
        return round(price, self._symbol_info().digits)

    # ---------- vị thế ----------
    def positions(self) -> dict[int, Any]:
        found = self._mt5.positions_get(symbol=self._symbol) or ()
        return {p.ticket: p for p in found if p.magic == self._magic}

    def _send(self, request: dict) -> Any:
        self.ensure_demo()
        result = self._mt5.order_send(request)
        if result is None or result.retcode != self._mt5.TRADE_RETCODE_DONE:
            detail = self._mt5.last_error() if result is None else f"{result.retcode} {result.comment}"
            raise BrokerError(f"order_send lỗi: {detail} | {request}")
        return result

    def market_order(self, direction: Direction, volume: float, sl: float, tp: float | None, comment: str) -> int:
        bid, ask = self.quote()
        buy = direction == Direction.BUY
        result = self._send({
            "action": self._mt5.TRADE_ACTION_DEAL, "symbol": self._symbol, "volume": float(volume),
            "type": self._mt5.ORDER_TYPE_BUY if buy else self._mt5.ORDER_TYPE_SELL,
            "price": ask if buy else bid, "sl": self._round(sl), "tp": self._round(tp) if tp else 0.0,
            "deviation": self._deviation, "magic": self._magic, "comment": comment[:31],
            "type_time": self._mt5.ORDER_TIME_GTC, "type_filling": self._filling(),
        })
        return int(result.order)

    def modify_sl(self, position: Any, sl: float) -> None:
        self._send({"action": self._mt5.TRADE_ACTION_SLTP, "symbol": self._symbol, "position": position.ticket,
                    "sl": self._round(sl), "tp": position.tp})

    def close_position(self, position: Any) -> None:
        bid, ask = self.quote()
        buy = position.type == self._mt5.POSITION_TYPE_BUY
        self._send({
            "action": self._mt5.TRADE_ACTION_DEAL, "symbol": self._symbol, "volume": position.volume,
            "type": self._mt5.ORDER_TYPE_SELL if buy else self._mt5.ORDER_TYPE_BUY, "position": position.ticket,
            "price": bid if buy else ask, "deviation": self._deviation, "magic": self._magic,
            "comment": "invalidation", "type_time": self._mt5.ORDER_TIME_GTC, "type_filling": self._filling(),
        })

    def closed_result(self, ticket: int) -> ClosedResult | None:
        deals = self._mt5.history_deals_get(position=ticket)
        if not deals:
            return None
        exits = [d for d in deals if d.entry in (self._mt5.DEAL_ENTRY_OUT, self._mt5.DEAL_ENTRY_OUT_BY)]
        if not exits:
            return None
        last = exits[-1]
        reason = {self._mt5.DEAL_REASON_SL: "sl", self._mt5.DEAL_REASON_TP: "tp"}.get(last.reason, "market")
        profit = sum(d.profit + d.commission + d.swap for d in deals)
        when = server_to_utc(pd.Series(pd.to_datetime([last.time], unit="s")), self._server_time).iat[0]
        return ClosedResult(float(last.price), when, float(profit), reason)
