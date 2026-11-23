"""Kết nối terminal MT5."""
from __future__ import annotations

import os
from typing import Any


def connect(cfg: dict) -> Any:
    """Khởi tạo MT5 và chọn symbol. Trả về module MetaTrader5 đã kết nối."""
    import MetaTrader5 as mt5

    conn = cfg["mt5"]
    kwargs: dict[str, Any] = {}
    if conn.get("path"):
        kwargs["path"] = conn["path"]
    if conn.get("login"):
        kwargs["login"] = int(conn["login"])
        kwargs["server"] = conn.get("server")
        password = os.environ.get(conn.get("password_env") or "")
        if password:
            kwargs["password"] = password
    if not mt5.initialize(**kwargs):
        raise ConnectionError(f"MT5 initialize lỗi: {mt5.last_error()}")
    if not mt5.symbol_select(cfg["symbol"], True):
        mt5.shutdown()
        raise ConnectionError(f"Không chọn được symbol {cfg['symbol']}: {mt5.last_error()}")
    return mt5
