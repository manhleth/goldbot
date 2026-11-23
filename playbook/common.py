"""Tiện ích chung cho các phương pháp: lọc giờ, dựng lệnh market từ mặt nạ tín hiệu."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

import numpy as np
import pandas as pd

from core.types import Direction
from playbook.orders import MARKET, Order
from risk.calendar import minutes


@dataclass(frozen=True)
class MarketData:
    frames: dict[str, pd.DataFrame]  # khung gốc + các khung lớn hơn gộp từ nó theo giờ UTC
    timezone: str                     # múi giờ New York cho các hộp giờ ICT
    point: float                      # đổi spread (point) sang giá
    base: str                         # khung gốc dùng để khớp lệnh (M5 hoặc M15)

    def frame(self, tf: str) -> pd.DataFrame:
        if tf not in self.frames:
            raise ValueError(f"phương pháp cần khung {tf} nhưng khung gốc là {self.base}")
        return self.frames[tf]


def utc_hours_mask(times: pd.Series, hours: list[str] | None, skip_friday: bool) -> np.ndarray:
    """Thời điểm quyết định (giờ đóng nến tín hiệu, UTC) nằm trong [bắt đầu, kết thúc) và không phải thứ Sáu."""
    t = pd.DatetimeIndex(times)
    ok = np.ones(len(t), bool)
    if hours:
        m = t.hour * 60 + t.minute
        ok &= (m >= minutes(hours[0])) & (m < minutes(hours[1]))
    if skip_friday:
        ok &= t.weekday != 4
    return ok


def previous(series: pd.Series) -> pd.Series:
    """Giá trị ở nến [2] khi nến hiện tại là [1]."""
    return series.shift(1)


def market_orders(name: str, df: pd.DataFrame, buy: np.ndarray, sell: np.ndarray,
                  build: Callable[[int, Direction], dict], reasons: Callable[[int, Direction], tuple[str, ...]]
                  ) -> list[Order]:
    """Mỗi nến có tín hiệu → lệnh market có hiệu lực lúc nến đó đóng. `build` trả các trường SL/TP/quản lý."""
    orders: list[Order] = []
    times = df["close_time"]
    for direction, mask in ((Direction.BUY, buy), (Direction.SELL, sell)):
        for i in np.flatnonzero(np.asarray(mask, bool)):
            t = times.iat[i]
            orders.append(Order(key=f"{name}:{t:%Y%m%d%H%M}:{direction.name}", time=t, direction=direction,
                                kind=MARKET, reasons=reasons(i, direction), **build(i, direction)))
    return sorted(orders, key=lambda o: o.time)


def finite(*arrays) -> np.ndarray:
    out = np.ones(len(arrays[0]), bool)
    for a in arrays:
        out &= np.isfinite(np.asarray(a, float))
    return out
