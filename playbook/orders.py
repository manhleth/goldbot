"""Lệnh do phương pháp sinh ra và sự kiện thoát/hủy theo chiều."""
from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from core.types import Direction

MARKET, LIMIT, STOP = "market", "limit", "stop"
EXIT, CANCEL = "exit", "cancel"


@dataclass(frozen=True, slots=True)
class Order:
    key: str
    time: pd.Timestamp                 # có hiệu lực từ thời điểm này (giờ đóng nến tín hiệu)
    direction: Direction
    kind: str                          # market | limit | stop
    price: float | None = None         # giá lệnh chờ
    sl: float | None = None            # SL tuyệt đối
    tp: float | None = None            # TP tuyệt đối; lệnh market: nếu không nằm phía có lãi thì dùng tp_dist
    sl_dist: float | None = None       # lệnh market: khoảng SL tính từ giá khớp
    tp_dist: float | None = None
    tp1_dist: float | None = None      # chốt một phần ở khoảng này rồi dời SL về hòa vốn (+ be_offset)
    tp1_fraction: float = 0.5
    be_trigger: float | None = None    # giá chạy thuận khoảng này (từ giá khớp) → dời SL về giá vào + be_offset
    be_trigger_r: float | None = None  # như trên, theo bội số rủi ro ban đầu
    be_offset: float = 0.0
    expiry: pd.Timestamp | None = None  # lệnh chờ hết hạn
    exit_at: pd.Timestamp | None = None  # đóng vị thế tại thời điểm này
    max_hold: pd.Timedelta | None = None
    max_spread: float | None = None    # lệnh market: bỏ nếu spread (giá) lúc khớp vượt mức này
    trail: str | None = None           # tên chuỗi mức dời SL theo cấu trúc (đỉnh/đáy swing khung lớn)
    risk_scale: float = 1.0            # hệ số nhân số tiền rủi ro của lệnh (vd phá qua vùng S/R cứng)
    lock_steps: tuple = ()             # khoá lãi theo bậc: ((chạy thuận R, dời SL tới +R), ...)
    reasons: tuple[str, ...] = ()
    meta: dict = field(default_factory=dict, compare=False)  # hình học mẫu hình để vẽ chart lý do (khung, các cạnh)

    @property
    def planned_risk(self) -> float | None:
        """Khoảng SL dự kiến để tính lot (lệnh chờ: từ giá đặt; market: sl_dist)."""
        if self.sl_dist is not None:
            return self.sl_dist
        if self.price is not None and self.sl is not None:
            return abs(self.price - self.sl)
        return None


@dataclass(frozen=True, slots=True)
class Event:
    """Tại `time`: đóng vị thế (exit) và/hoặc hủy lệnh chờ (cancel) theo `direction`."""
    time: pd.Timestamp
    direction: Direction
    actions: tuple[str, ...] = (EXIT, CANCEL)


@dataclass(frozen=True, slots=True)
class Signals:
    orders: list[Order]
    events: list[Event]
