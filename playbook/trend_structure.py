"""Xu hướng theo cấu trúc giá (CHoCH/BOS) và trendline khung lớn — không dùng đường trung bình.

Tại mỗi nến (đã đóng) của khung xu hướng:
- Cấu trúc: đóng cửa vượt đỉnh swing gần nhất đã xác nhận (chưa bị phá) → tăng; thủng đáy swing gần nhất → giảm.
  Cú phá ngược hướng cũ là CHoCH (đổi xu hướng), cùng hướng là BOS (xác nhận).
- Trendline: trendline xu hướng (≥ `min_touches` chạm, dạng vùng) bị đóng cửa phá ngược hướng cấu trúc hiện tại
  → `neutral`: đứng ngoài tới cú phá cấu trúc kế tiếp (BOS cũ → đánh tiếp; CHoCH → đổi chiều);
    `flip`: đảo chiều ngay theo hướng phá tới cú phá cấu trúc kế tiếp.
Kết quả: +1 tăng / -1 giảm / 0 đứng ngoài, theo từng nến.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from core.types import Direction
from playbook import indicators as ind
from playbook.trendlines import LineRules, build

MODES = ("neutral", "flip")


def structure_trend(df: pd.DataFrame, swing: int, mode: str, rules: LineRules, break_atr: float,
                    atr_period: int, use_trendline: bool = True) -> np.ndarray:
    if mode not in MODES:
        raise ValueError(f"mode phải là một trong {MODES}")
    is_high, is_low = ind.fractal_swings(df, swing, swing)
    h, l, c = (df[col].to_numpy(float) for col in ("high", "low", "close"))
    warnings: dict[int, int] = {}
    if use_trendline:
        for brk in build(df, swing, rules, break_atr, atr_period).breaks:
            # đường tăng (nối đáy) bị phá xuống → cảnh báo giảm; đường giảm bị phá lên → cảnh báo tăng
            warnings[brk.index] = -1 if brk.side == Direction.BUY else 1
    n = len(df)
    out = np.zeros(n, dtype=int)
    state, override = 0, None
    last_high = last_low = None
    broken_high = broken_low = -1
    for k in range(n):
        s = k - swing  # swing tại s được xác nhận khi nến k đóng
        if s >= 0 and is_high[s]:
            last_high = s
        if s >= 0 and is_low[s]:
            last_low = s
        if last_high is not None and last_high != broken_high and k > last_high + swing and c[k] > h[last_high]:
            state, override, broken_high = 1, None, last_high
        elif last_low is not None and last_low != broken_low and k > last_low + swing and c[k] < l[last_low]:
            state, override, broken_low = -1, None, last_low
        warn = warnings.get(k)
        if warn is not None and state != 0 and warn == -state:
            override = 0 if mode == "neutral" else warn
        out[k] = state if override is None else override
    return out
