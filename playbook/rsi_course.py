"""Kiến thức khoá K23 (docs/knowledge/alden-k23.md): RSI + EMA9/WMA45 vẽ trên RSI.

- `rsi_lines(df, cfg)`: RSI(`period`), EMA(`fast`) và WMA(`slow`) của RSI, theo từng nến đã đóng.
- Bộ lọc `apply_rsi_filters(orders, data, cfg)` (mỗi mục null = tắt):
  - `sideway`: sideway "không lực" ở các khung `tfs` (`mode` any/all): RSI trong [`band`] và mọi RSI của `window` nến gần
    nhất nằm trong (`extremes`) → bỏ lệnh.
  - `model`: khung mẫu hình của lệnh phải có "mô hình RSI" cùng chiều (RSI và EMA cùng phía WMA, WMA dốc cùng chiều trong
    `slope_bars` nến) và khung lớn liền kề (`higher`) có RSI cùng phía WMA (cho phép).
"""
from __future__ import annotations

import dataclasses

import numpy as np
import pandas as pd

from playbook.common import MarketData
from playbook.orders import Order
from structure.indicators import ema, rsi


def wma(series: pd.Series, period: int) -> pd.Series:
    weights = np.arange(1, period + 1, dtype=float)
    return series.rolling(period).apply(lambda x: float(np.dot(x, weights) / weights.sum()), raw=True)


def rsi_lines(df: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    r = rsi(df["close"], cfg["period"])
    return pd.DataFrame({"close_time": df["close_time"], "rsi": r, "fast": ema(r, cfg["fast"]), "slow": wma(r, cfg["slow"])})


def _state(data: MarketData, tf: str, cfg: dict, cache: dict) -> pd.DataFrame:
    if tf not in cache:
        cache[tf] = rsi_lines(data.frame(tf), cfg)
    return cache[tf]


def _at(lines: pd.DataFrame, times: pd.Series) -> pd.DataFrame:
    return pd.merge_asof(pd.DataFrame({"close_time": times}), lines, on="close_time", direction="backward")


def _sideway_flags(lines: pd.DataFrame, sc: dict) -> pd.Series:
    lo, hi = sc["band"]
    e_lo, e_hi = sc["extremes"]
    window_max = lines["rsi"].rolling(sc["window"]).max()
    window_min = lines["rsi"].rolling(sc["window"]).min()
    flag = lines["rsi"].between(lo, hi) & (window_max < e_hi) & (window_min > e_lo)
    return pd.DataFrame({"close_time": lines["close_time"], "flag": flag})


def apply_rsi_filters(orders: list[Order], data: MarketData, cfg: dict) -> list[Order]:
    if not orders:
        return orders
    cache: dict[str, pd.DataFrame] = {}
    times = pd.Series([o.time for o in orders])
    keep = np.ones(len(orders), dtype=bool)
    sc = cfg.get("sideway")
    if sc:
        flags = [_at(_sideway_flags(_state(data, tf, cfg, cache), sc), times)["flag"].fillna(False).to_numpy(bool)
                 for tf in sc["tfs"]]
        blocked = np.any(flags, axis=0) if sc.get("mode", "any") == "any" else np.all(flags, axis=0)
        keep &= ~blocked
    mc = cfg.get("model")
    if mc:
        for i, o in enumerate(orders):
            if not keep[i]:
                continue
            tf, d = o.meta.get("tf"), int(o.direction)
            if tf is None:
                continue
            lines = _state(data, tf, cfg, cache)
            k = int(lines["close_time"].searchsorted(o.time, side="right")) - 1
            if k < mc["slope_bars"]:
                keep[i] = False
                continue
            r, f, s = lines["rsi"].iat[k], lines["fast"].iat[k], lines["slow"].iat[k]
            slope = s - lines["slow"].iat[k - mc["slope_bars"]]
            model = (r - s) * d > 0 and (f - s) * d > 0 and slope * d > 0
            higher = mc.get("higher", {}).get(tf)
            if model and higher:
                hl = _state(data, higher, cfg, cache)
                j = int(hl["close_time"].searchsorted(o.time, side="right")) - 1
                model = j >= 0 and (hl["rsi"].iat[j] - hl["slow"].iat[j]) * d > 0
            keep[i] = bool(model)
    return [dataclasses.replace(o, reasons=(*o.reasons, "RSI khoá K23 đạt")) if cfg.get("model") else o
            for o, k in zip(orders, keep) if k]
