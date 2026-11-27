"""Phương pháp hợp nhất: phá cấu trúc theo xu hướng H4, gồng theo đỉnh/đáy H4, có học kinh nghiệm.

Nguồn kiến thức: XAU-02 (lọc xu hướng EMA50/EMA200 H4), XAU-05 (phá hộp phiên Á), mẫu hình trendline dạng vùng
(docs/knowledge/chart-patterns.md, docs/knowledge/mj-capital.md: cờ, tam giác, kênh, neckline).
- `triggers`: các loại điểm vào được bật (`patterns`, `asia_box`, `retest` = phá có lực + retest, playbook/retest.py,
  `tl_retest` = phá trendline đa tỉ lệ + retest, playbook/tl_scales.py, cấu hình ở `tl_scales`).
- `trend_filter`: chiều được phép theo khung `tf`: `method: ema` (close & EMA nhanh so với EMA chậm) hoặc
  `structure` (CHoCH/BOS + trendline khung lớn, playbook/trend_structure.py); null = không lọc.
- `intraday` (tuỳ chọn): không vào lệnh từ `last_entry` tới đầu ngày giao dịch mới; mọi lệnh đóng lúc `flat`
  (giờ theo `sessions.timezone`, New York) của ngày giao dịch đó.
- `patterns.tf_hours` (tuỳ chọn): {khung: [bắt đầu, kết thúc]} giờ địa phương — mẫu hình khung đó chỉ được vào lệnh
  trong khung giờ này (vd M15 chỉ phiên New York); khung không liệt kê thì không giới hạn.
- `session_exit` (tuỳ chọn): giờ đóng theo phiên vào lệnh — mỗi mục `windows` {from, to (giờ vào lệnh), flat,
  days (số ngày giao dịch giữ thêm; null = tới cuối tuần)}; không lệnh nào giữ qua `friday.flat`.
- `sr` (tuỳ chọn): vùng hỗ trợ/kháng cự cứng D1/H4 (playbook/sr_zones.py) — lọc khoảng trống, thưởng rủi ro khi phá
  vùng, chốt một phần tại vùng cản; `triggers` có `zone_bounce` = setup bật vùng.
- `profit_lock` (tuỳ chọn): [[chạy thuận R, khoá SL tại +R], ...] — chốt sớm để lệnh lãi không quay thành lỗ.
- `breakeven` (tuỳ chọn): {at_r, offset_r} — giá chạy thuận ≥ at_r × rủi ro thì dời SL về giá vào + offset_r × rủi ro.
- `channel` (tuỳ chọn): kênh xu hướng D1 (playbook/channel_regime.py) — ưu tiên hơn `macro`.
- `macro` (tuỳ chọn): trạng thái vĩ mô theo cú phá mẫu hình W1 (playbook/macro.py) — chặn lệnh ngược chiều, hệ số rủi ro.
- `rsi_course` (tuỳ chọn): bộ lọc RSI theo khoá K23 (playbook/rsi_course.py).
- `context` (tuỳ chọn): ghi bối cảnh lúc vào lệnh vào meta (playbook/context.py): xu hướng H4, vĩ mô, ADX.
- `regime_exit` (tuỳ chọn): thoát theo trạng thái thị trường lúc vào lệnh (playbook/regime.py).
- `weekend` (tuỳ chọn): giữ lệnh qua đêm, chỉ đóng lúc `flat` thứ Sáu; không vào lệnh từ `last_entry` thứ Sáu
  tới phiên tuần mới.
Mọi lệnh mang khoá `<code>:<loại>@<khung>:...` để lớp học kinh nghiệm chấm điểm theo loại.
"""
from __future__ import annotations

import dataclasses

import numpy as np
import pandas as pd

from core.types import Direction
from playbook import indicators as ind
from playbook.common import MarketData
from playbook.methods_box import xau05
from playbook.orders import Order, Signals
from playbook.patterns import patterns
from playbook.channel_regime import apply_channel
from playbook.context import annotate
from playbook.macro import apply_macro, macro_series
from playbook.regime import apply_regime_exit
from playbook.rsi_course import apply_rsi_filters
from playbook.retest import retest
from playbook.sr_zones import apply_sr, bounce, build_book
from playbook.tl_scales import tl_retest
from playbook.trend_structure import structure_trend
from playbook.trendlines import LineRules
from risk.calendar import in_window, minutes


def _ema_trend(df: pd.DataFrame, tf_cfg: dict) -> np.ndarray:
    """Close và EMA nhanh cùng phía so với EMA chậm."""
    fast, slow = tf_cfg["fast"], tf_cfg["slow"]
    c = df["close"]
    f, s = ind.ema(c, fast), ind.ema(c, slow)
    trend = np.where((c > s) & (f > s), 1, np.where((c < s) & (f < s), -1, 0))
    return np.where(np.arange(len(df)) >= slow, trend, 0)


def _structure_trend(df: pd.DataFrame, tf_cfg: dict) -> np.ndarray:
    """CHoCH/BOS + trendline khung lớn (playbook/trend_structure.py)."""
    rules = LineRules(tf_cfg["min_touches"], tf_cfg["touch_tol_atr"], tf_cfg["channel_min_touches"],
                      tf_cfg["max_pivots"])
    return structure_trend(df, tf_cfg["swing"], tf_cfg["mode"], rules, tf_cfg["break_atr"], tf_cfg["atr"],
                           tf_cfg.get("use_trendline", True))


TREND_METHODS = {"ema": _ema_trend, "structure": _structure_trend}


def _trend(data: MarketData, tf_cfg: dict) -> pd.DataFrame:
    df = data.frame(tf_cfg["tf"])
    trend = TREND_METHODS[tf_cfg.get("method", "ema")](df, tf_cfg)
    return pd.DataFrame({"close_time": df["close_time"], "trend": trend})


def _aligned(orders: list[Order], trend: pd.DataFrame) -> list[Order]:
    if not orders:
        return orders
    times = pd.DataFrame({"close_time": [o.time for o in orders]})
    state = pd.merge_asof(times, trend, on="close_time", direction="backward")["trend"].fillna(0).to_numpy()
    return [o for o, t in zip(orders, state) if t == int(o.direction)]


def _tf_hours(orders: list[Order], tz: str, windows: dict) -> list[Order]:
    """Bỏ lệnh của khung có giới hạn giờ nếu thời điểm vào (giờ địa phương) nằm ngoài [bắt đầu, kết thúc)."""
    def allowed(o: Order) -> bool:
        window = windows.get(o.meta.get("tf"))
        return window is None or in_window(o.time.tz_convert(tz), *window)
    return [o for o in orders if allowed(o)]


def _rekey(orders: list[Order], code: str, kind: str) -> list[Order]:
    return [dataclasses.replace(o, key=f"{code}:{kind}:{o.time:%Y%m%d%H%M}:{o.direction.name}") for o in orders]


FRIDAY = 4


def _breakeven(orders: list[Order], rules: dict) -> list[Order]:
    """Dời SL về hòa vốn (+ offset_r × rủi ro) khi giá chạy thuận at_r × rủi ro."""
    return [dataclasses.replace(o, be_trigger_r=rules["at_r"], be_offset=rules.get("offset_r", 0.0) * o.sl_dist)
            if o.sl_dist else o for o in orders]


def _intraday(orders: list[Order], tz: str, rules: dict) -> list[Order]:
    """Lệnh trong ngày: bỏ lệnh từ `last_entry` tới `day_start` (giờ địa phương), đặt giờ đóng = `flat` cùng ngày.

    Ngày giao dịch thứ Sáu dùng `friday.last_entry` / `friday.flat` (sàn đóng vàng sớm, có tuần nến cuối 15:55 NY):
    đóng lệnh sau giờ sàn đóng = bị giữ qua cuối tuần, dính gap.
    """
    out = []
    day_start = minutes(rules["day_start"])
    friday = rules.get("friday") or {}
    for o in orders:
        local = o.time.tz_convert(tz)
        m = local.hour * 60 + local.minute
        day = local.normalize() + (pd.Timedelta(days=1) if m >= day_start else pd.Timedelta(0))
        today = friday if day.weekday() == FRIDAY and friday else rules
        last, flat = minutes(today["last_entry"]), minutes(today["flat"])
        if day == local.normalize() and m >= last:  # cùng ngày giao dịch, đã quá giờ vào lệnh cuối
            continue
        exit_at = (day + pd.Timedelta(minutes=flat)).tz_convert("UTC")
        out.append(dataclasses.replace(o, exit_at=exit_at))
    return out


def _trading_day(local: pd.Timestamp, day_start: int) -> pd.Timestamp:
    """Ngày giao dịch (giờ địa phương, 00:00) chứa thời điểm `local`; ngày mới bắt đầu lúc `day_start` hôm trước."""
    m = local.hour * 60 + local.minute
    return local.normalize() + (pd.Timedelta(days=1) if m >= day_start else pd.Timedelta(0))


def _weekend(orders: list[Order], tz: str, rules: dict) -> list[Order]:
    """Giữ lệnh qua đêm, đóng hết lúc `flat` của thứ Sáu trong tuần; bỏ lệnh từ `last_entry` thứ Sáu."""
    out = []
    day_start, last, flat = minutes(rules["day_start"]), minutes(rules["last_entry"]), minutes(rules["flat"])
    for o in orders:
        local = o.time.tz_convert(tz)
        friday = _trading_day(local, day_start)
        friday += pd.Timedelta(days=(FRIDAY - friday.weekday()) % 7)
        if local.normalize() == friday and local.hour * 60 + local.minute >= last:
            continue
        out.append(dataclasses.replace(o, exit_at=(friday + pd.Timedelta(minutes=flat)).tz_convert("UTC")))
    return out


def _session_exit(orders: list[Order], tz: str, rules: dict) -> list[Order]:
    """Giờ đóng lệnh theo phiên lúc vào lệnh; mọi lệnh đóng chậm nhất `friday.flat`, bỏ lệnh từ `friday.last_entry`."""
    out = []
    day_start, fri = minutes(rules["day_start"]), rules["friday"]
    for o in orders:
        local = o.time.tz_convert(tz)
        day = _trading_day(local, day_start)
        friday = day + pd.Timedelta(days=(FRIDAY - day.weekday()) % 7)
        if local.normalize() == friday and local.hour * 60 + local.minute >= minutes(fri["last_entry"]):
            continue
        rule = next((w for w in rules["windows"] if in_window(local, w["from"], w["to"])), None)
        if rule is None:
            continue
        target = friday if rule.get("days") is None else min(day + pd.Timedelta(days=rule["days"]), friday)
        flat = fri["flat"] if target == friday else rule["flat"]
        out.append(dataclasses.replace(o, exit_at=(target + pd.Timedelta(minutes=minutes(flat))).tz_convert("UTC")))
    return out


def unified(data: MarketData, p: dict) -> Signals:
    orders: list[Order] = []
    if "patterns" in p["triggers"]:
        found = patterns(data, {**p["patterns"], "code": p["code"]}).orders
        allowed = {f"{k}@{tf}" for k in p["patterns"]["kinds"] for tf in p["patterns"]["timeframes"]}
        orders += _tf_hours([o for o in found if o.key.split(":")[1] in allowed], data.timezone,
                            p["patterns"].get("tf_hours") or {})
    if "asia_box" in p["triggers"]:
        orders += _rekey(xau05(data, p["asia_box"]).orders, p["code"], "asia_box@M5")
    book = build_book(data, p["sr"]) if p.get("sr") else None
    if "zone_bounce" in p["triggers"]:
        orders += bounce(data, book, {**p["sr"]["bounce"], "atr": p["sr"]["atr"]}, p["code"],
                         p["patterns"].get("scan_since"))
    orders.sort(key=lambda o: o.time)
    trend = _trend(data, p["trend_filter"]) if p["trend_filter"] else None
    if trend is not None:
        orders = _aligned(orders, trend)
    if "retest" in p["triggers"]:  # chiều theo cấu trúc khung lớn riêng (playbook/retest.py), không qua lọc EMA
        orders = sorted(orders + retest(data, p["patterns"], p["retest"], p["code"]),
                        key=lambda o: o.time)
    if "tl_retest" in p["triggers"]:  # phá trendline đa tỉ lệ + retest (playbook/tl_scales.py): chiều = chiều phá
        orders = sorted(orders + tl_retest(data, p["tl_scales"], p["code"]), key=lambda o: o.time)
    if book is not None:
        orders = apply_sr(orders, book, p["sr"])
    if p.get("channel"):
        orders = apply_channel(orders, data, p["channel"])
    macro = macro_series(data, p["macro"]) if p.get("macro") else None
    if macro is not None:
        orders = apply_macro(orders, macro, p["macro"])
    if p.get("rsi_course"):
        orders = apply_rsi_filters(orders, data, p["rsi_course"])
    if p.get("regime_exit"):
        orders = apply_regime_exit(orders, data, p["regime_exit"])
    if p.get("breakeven"):
        orders = _breakeven(orders, p["breakeven"])
    if p.get("profit_lock"):
        steps = tuple((float(t), float(r)) for t, r in p["profit_lock"])
        orders = [dataclasses.replace(o, lock_steps=steps) for o in orders]
    if p.get("intraday"):
        orders = _intraday(orders, data.timezone, p["intraday"])
    if p.get("session_exit"):
        orders = _session_exit(orders, data.timezone, p["session_exit"])
    if p.get("weekend"):
        orders = _weekend(orders, data.timezone, p["weekend"])
    if p.get("context"):
        orders = annotate(orders, data, trend, macro, p["context"]["adx"])
    return Signals(orders, [])
