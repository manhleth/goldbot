"""Vùng thanh khoản: đỉnh/đáy ngày trước (PDH/PDL), range các phiên, swing và equal highs/lows của khung setup.

Ngày và phiên tính theo giờ địa phương của `sessions.timezone` (mặc định New York, ngày bắt đầu lúc nửa đêm).
Một mức chỉ được dùng khi phiên tạo ra nó đã kết thúc tại thời điểm t (không look-ahead).
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from typing import Literal

import numpy as np
import pandas as pd

from risk.calendar import minutes
from structure.swings import Swing

STRUCTURAL_KINDS = {"swing", "equal"}
PoolSide = Literal["high", "low"]  # high = thanh khoản phía trên (buy-side), low = phía dưới (sell-side)


@dataclass(frozen=True, slots=True)
class Pool:
    kind: str  # "pdh_pdl" hoặc tên phiên tạo ra mức này
    name: str
    price: float
    side: PoolSide
    available_index: int  # nến đầu tiên mà mức này đã được biết


def _at(day: date, hhmm: str, tz: str) -> pd.Timestamp:
    m = minutes(hhmm)
    # Ngày đổi giờ DST: giờ không tồn tại (vd 02:00 tháng 3) dời lên, giờ lặp lấy lần đầu.
    return pd.Timestamp(datetime.combine(day, time(m // 60, m % 60))).tz_localize(
        tz, nonexistent="shift_forward", ambiguous=True)


def session_bounds(day: date, start: str, end: str, tz: str) -> tuple[pd.Timestamp, pd.Timestamp]:
    """Phiên của ngày `day`. Phiên qua nửa đêm (vd 20:00→00:00) bắt đầu từ tối hôm trước."""
    lo, hi = minutes(start), minutes(end)
    wraps = hi == 0 or lo >= hi
    begin = _at(day - timedelta(days=1) if wraps else day, start, tz)
    finish = _at(day, end, tz) if hi else _at(day, "00:00", tz)
    return begin, finish


def _range(df: pd.DataFrame, local: pd.Series, begin: pd.Timestamp, finish: pd.Timestamp,
           name: str) -> list[Pool]:
    mask = ((local >= begin) & (local < finish)).to_numpy()
    if not mask.any():
        return []
    after = int(np.flatnonzero(mask)[-1]) + 1
    highs, lows = df["high"].to_numpy()[mask], df["low"].to_numpy()[mask]
    return [Pool(name, f"{name}_high", float(highs.max()), "high", after),
            Pool(name, f"{name}_low", float(lows.min()), "low", after)]


def previous_day_pools(df: pd.DataFrame, local: pd.Series, today: date) -> list[Pool]:
    days = local.dt.date
    prior = days[days < today]
    if prior.empty:
        return []
    last_day = prior.iloc[-1]
    mask = (days == last_day).to_numpy()
    after = int(np.flatnonzero(mask)[-1]) + 1
    return [Pool("pdh_pdl", "pdh", float(df["high"].to_numpy()[mask].max()), "high", after),
            Pool("pdh_pdl", "pdl", float(df["low"].to_numpy()[mask].min()), "low", after)]


def liquidity_pools(df: pd.DataFrame, t: pd.Timestamp, kinds: list[str], sessions_cfg: dict) -> list[Pool]:
    """Các mức thanh khoản đã hình thành xong tại t. `kinds` ⊂ {pdh_pdl, <tên phiên trong sessions.windows>}."""
    tz = sessions_cfg["timezone"]
    local = df["time"].dt.tz_convert(tz)
    now = t.tz_convert(tz)
    pools: list[Pool] = []
    for kind in kinds:
        if kind in STRUCTURAL_KINDS:
            continue  # xem structural_pools
        if kind == "pdh_pdl":
            pools += previous_day_pools(df, local, now.date())
            continue
        begin, finish = session_bounds(now.date(), *sessions_cfg["windows"][kind], tz)
        if finish <= now:
            pools += _range(df, local, begin, finish, kind)
    return pools


def structural_pools(swings: list[Swing], kinds: list[str], since_index: int, equal_tolerance: float) -> list[Pool]:
    """Thanh khoản từ cấu trúc khung setup, chỉ xét swing hình thành từ `since_index`:
    - "swing": từng đỉnh/đáy swing (internal liquidity);
    - "equal": hai đỉnh (đáy) swing liên tiếp chênh nhau ≤ `equal_tolerance` — nơi dồn stop loss.
    """
    recent = [s for s in swings if s.index >= since_index]
    pools: list[Pool] = []
    if "swing" in kinds:
        pools += [Pool("swing", f"swing_{s.kind}@{s.time:%m%d%H%M}", s.price, s.kind, s.confirmed_index + 1)
                  for s in recent]
    if "equal" in kinds and equal_tolerance > 0:
        for kind in ("high", "low"):
            same = [s for s in recent if s.kind == kind]
            for a, b in zip(same, same[1:]):
                if abs(a.price - b.price) <= equal_tolerance:
                    price = max(a.price, b.price) if kind == "high" else min(a.price, b.price)
                    pools.append(Pool("equal", f"equal_{kind}s@{b.time:%m%d%H%M}", price, kind, b.confirmed_index + 1))
    return pools
