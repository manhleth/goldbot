"""Kiểm chứng nhận định (đã ghi nhãn) với giá thật sau thời điểm đăng.

Giá tham chiếu = giá mở nến H1 đầu tiên sau lúc đăng (không dùng gì trước đó → không nhìn trước).
- Đúng hướng tại các mốc `horizons` (giá đóng cửa mốc đó so với giá tham chiếu, theo hướng nhận định).
- Mục tiêu đầu tiên vs vùng vô hiệu: cái nào chạm trước trong `max_days` (dùng high/low H1; cùng nến → tính vô hiệu).
- R nếu làm theo: vào ở giá tham chiếu, SL = vô hiệu, TP = mục tiêu đầu tiên (chỉ khi có cả hai và đúng phía).
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

UP, DOWN = "up", "down"


@dataclass(frozen=True)
class Call:
    post_id: int
    time: pd.Timestamp
    symbol: str
    direction: str
    targets: tuple[float, ...]
    invalidation: float | None
    levels_comparable: bool  # mức giá trong nhận định so được với chuỗi giá (False với ETF thay thế)


def _first(mask: np.ndarray) -> int | None:
    idx = np.flatnonzero(mask)
    return int(idx[0]) if idx.size else None


def evaluate(call: Call, prices: pd.DataFrame, horizons: dict[str, pd.Timedelta], max_days: int) -> dict:
    sign = 1 if call.direction == UP else -1
    start = int(prices["time"].searchsorted(call.time, side="right"))
    if start >= len(prices):
        return {"post_id": call.post_id, "status": "no_data"}
    p0 = float(prices["open"].iat[start])
    out: dict = {"post_id": call.post_id, "status": "ok", "ref_price": p0}
    times = prices["time"]
    for name, delta in horizons.items():
        j = int(times.searchsorted(call.time + delta, side="right")) - 1
        if j <= start or times.iat[-1] < call.time + delta:
            out[f"ret_{name}"] = None
            continue
        out[f"ret_{name}"] = sign * (float(prices["close"].iat[j]) / p0 - 1) * 100
    stop = int(times.searchsorted(call.time + pd.Timedelta(days=max_days), side="right"))
    window = prices.iloc[start:stop]
    hi, lo = window["high"].to_numpy(float), window["low"].to_numpy(float)
    favorable = (hi / p0 - 1) * 100 if sign > 0 else (1 - lo / p0) * 100
    adverse = (1 - lo / p0) * 100 if sign > 0 else (hi / p0 - 1) * 100
    out["max_favorable_pct"] = float(favorable.max()) if favorable.size else None
    out["max_adverse_pct"] = float(adverse.max()) if adverse.size else None
    if not call.levels_comparable:
        return out
    targets = [t for t in call.targets if (t - p0) * sign > 0]
    target = min(targets, key=lambda t: abs(t - p0)) if targets else None
    inval = call.invalidation if call.invalidation is not None and (p0 - call.invalidation) * sign > 0 else None
    hit_t = _first((hi >= target) if sign > 0 else (lo <= target)) if target is not None else None
    hit_i = _first((lo <= inval) if sign > 0 else (hi >= inval)) if inval is not None else None
    if hit_t is not None and (hit_i is None or hit_t < hit_i):
        out["outcome"], k = "target", hit_t
    elif hit_i is not None:
        out["outcome"], k = "invalidated", hit_i
    else:
        out["outcome"], k = "open", None
    out["target"], out["invalidation"] = target, inval
    out["days_to_outcome"] = None if k is None else (times.iat[start + k] - call.time).total_seconds() / 86400
    if target is not None and inval is not None and out["outcome"] != "open":
        out["r"] = abs(target - p0) / abs(p0 - inval) if out["outcome"] == "target" else -1.0
    return out
