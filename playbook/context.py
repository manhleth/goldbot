"""Bối cảnh thị trường lúc vào lệnh, ghi vào từng lệnh (meta["context"]) để xem lại: xu hướng H4 theo EMA, trạng thái vĩ
mô W1/D1 (cú phá mẫu hình dài hạn gần nhất), ADX D1. Chỉ dùng nến đã đóng trước thời điểm lệnh.
"""
from __future__ import annotations

import dataclasses

import pandas as pd

from playbook.common import MarketData
from playbook.orders import Order
from structure.indicators import adx

TREND_WORD = {1: "tăng", -1: "giảm", 0: "không rõ"}


def _asof(times: list[pd.Timestamp], frame: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    return pd.merge_asof(pd.DataFrame({"close_time": times}), frame[["close_time", *cols]], on="close_time",
                         direction="backward")


def annotate(orders: list[Order], data: MarketData, trend: pd.DataFrame | None, macro: pd.DataFrame | None,
             adx_cfg: dict) -> list[Order]:
    """`trend`: close_time, trend (+1/−1/0) của bộ lọc xu hướng; `macro`: các mốc đổi trạng thái vĩ mô (playbook/macro)."""
    if not orders:
        return orders
    times = [o.time for o in orders]
    d1 = data.frame(adx_cfg["tf"])
    adx_df = pd.DataFrame({"close_time": d1["close_time"], "adx": adx(d1, adx_cfg["period"]).to_numpy()})
    adx_at = _asof(times, adx_df, ["adx"])["adx"]
    trend_at = _asof(times, trend, ["trend"])["trend"] if trend is not None else None
    macro_at = _asof(times, macro, ["state", "tf", "pattern"]) if macro is not None and not macro.empty else None
    if macro_at is not None:
        since = pd.merge_asof(pd.DataFrame({"close_time": times}), macro[["close_time"]].assign(since=macro["close_time"]),
                              on="close_time", direction="backward")["since"]
    out = []
    for i, o in enumerate(orders):
        ctx: dict = {}
        lines = []
        if trend_at is not None and pd.notna(trend_at.iat[i]):
            ctx["trend_h4"] = int(trend_at.iat[i])
            lines.append(f"Xu hướng H4 (EMA50/EMA200): {TREND_WORD[ctx['trend_h4']]}")
        if macro_at is not None and pd.notna(macro_at["state"].iat[i]):
            ctx["macro"] = int(macro_at["state"].iat[i])
            lines.append(f"Vĩ mô {TREND_WORD[ctx['macro']]} từ {since.iat[i]:%d/%m/%Y} "
                         f"({macro_at['tf'].iat[i]} phá {macro_at['pattern'].iat[i]})")
        if pd.notna(adx_at.iat[i]):
            value = float(adx_at.iat[i])
            ctx["adx_d1"] = round(value, 1)
            phase = "xu hướng mạnh" if value >= adx_cfg["strong"] else "xu hướng yếu / nhiễu" if value < adx_cfg["weak"] \
                else "xu hướng vừa"
            lines.append(f"ADX {adx_cfg['tf']} {value:.0f}: {phase}")
        ctx["lines"] = lines
        out.append(dataclasses.replace(o, meta={**o.meta, "context": ctx}))
    return out
