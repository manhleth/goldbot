"""Vùng hỗ trợ/kháng cự cứng từ swing khung lớn (D1, H4) và 4 cách dùng trong ONE.

Khung vùng: D1, H4 (từ MarketData) hoặc W1 (gộp nến D1 theo tuần, đóng cửa = nến D1 cuối tuần).
Vùng: gom đỉnh/đáy swing (fractal `swing` nến, đã xác nhận) trong `lookback` nến gần nhất có giá cách nhau ≤ `tol_atr`
× ATR thành một vùng [thấp nhất, cao nhất]; vùng hợp lệ khi có ≥ `min_touches` swing và lần chạm gần nhất cách hiện tại
≤ `max_age` nến của khung đó (vùng quá cũ hết hiệu lực; null = không giới hạn). Vùng chỉ đổi khi có swing mới
được xác nhận, nên tại thời điểm t chỉ dùng swing đã xác nhận trước t (không nhìn trước). Vai trò (hỗ trợ/kháng cự)
theo vị trí giá hiện tại: vùng phía trên = kháng cự, phía dưới = hỗ trợ — vùng vỡ tự đổi vai.

Cách dùng (mỗi mục null = tắt):
- `room`: bỏ lệnh nếu từ giá vào tới vùng cản gần nhất phía trước < `min_r` × khoảng SL (giá vào trong vùng = 0).
- `break_bonus`: nến phá mẫu hình đồng thời đóng cửa vượt qua một vùng cứng → rủi ro lệnh × `risk_mult`.
- `take_partial`: chốt `fraction` khối lượng ở mép gần của vùng cản (lùi `buffer_atr` × ATR), rồi dời SL hòa vốn.
- `bounce`: setup mới — giá chạm vùng hỗ trợ (BUY) / kháng cự (SELL) rồi có pin bar / engulfing ở khung `timeframes`,
  đóng cửa ngoài vùng về phía lệnh; SL ngoài vùng `sl_buffer_atr` × ATR (bỏ nếu > `max_sl_atr` × ATR).
"""
from __future__ import annotations

import dataclasses
from dataclasses import dataclass

import numpy as np
import pandas as pd

from core.types import Direction
from playbook import indicators as ind
from playbook.common import MarketData
from playbook.orders import MARKET, Order
from playbook.retest import Frame, _trigger


@dataclass(frozen=True)
class ZoneBook:
    """Các ảnh chụp vùng: từ `times[i]` trở đi dùng `zones[i]` (mảng N×2: thấp, cao) và `atr[i]`."""
    times: np.ndarray
    zones: list[np.ndarray]
    atr: np.ndarray

    def at(self, t: pd.Timestamp) -> tuple[np.ndarray, float]:
        i = int(np.searchsorted(self.times, np.datetime64(t.tz_convert("UTC").tz_localize(None)), side="right")) - 1
        return (self.zones[i], float(self.atr[i])) if i >= 0 else (np.empty((0, 2)), np.nan)


def _cluster(prices: np.ndarray, index: np.ndarray, tol: float, min_touches: int) -> list[tuple[float, float, int]]:
    """Cụm giá cách giá thấp nhất của cụm ≤ `tol`: (thấp, cao, vị trí lần chạm gần nhất)."""
    return [(lo, hi, max(members)) for lo, hi, members in _groups(prices, index, tol, min_touches)]


def _groups(prices: np.ndarray, index: np.ndarray, tol: float, min_touches: int) -> list[tuple[float, float, list[int]]]:
    """Như `_cluster` nhưng giữ vị trí mọi lần chạm của cụm."""
    out, group = [], []

    def close_group() -> None:
        if len(group) >= min_touches:
            out.append((group[0][0], group[-1][0], sorted(i for _, i in group)))

    for p, i in sorted(zip(prices, index)):
        if group and p - group[0][0] > tol:
            close_group()
            group = []
        group.append((p, i))
    close_group()
    return out


def _snapshots(df: pd.DataFrame, swing: int, lookback: int, max_age: int | None, tol_atr: float, min_touches: int,
               atr_period: int) -> list[tuple[pd.Timestamp, list[tuple[float, float]], float]]:
    """Vùng tại mỗi lần có swing mới xác nhận, và tại lúc một vùng hết tuổi (để vùng cũ biến mất đúng hạn)."""
    is_high, is_low = ind.fractal_swings(df, swing, swing)
    atr = ind.atr(df, atr_period).to_numpy(float)
    prices = np.where(is_high, df["high"].to_numpy(float), np.where(is_low, df["low"].to_numpy(float), np.nan))
    pivots = np.flatnonzero(is_high | is_low)
    checks = {int(s + swing) for s in pivots}  # swing tại s được xác nhận khi nến k đóng
    if max_age is not None:
        checks |= {int(s + max_age + 1) for s in pivots}  # nến đầu tiên vùng chạm lần cuối ở s có thể hết tuổi
    out = []
    for k in sorted(checks):
        if k >= len(df) or not np.isfinite(atr[k]):
            continue
        lo = max(0, k - lookback)
        known = pivots[(pivots >= lo) & (pivots + swing <= k)]
        zones = _cluster(prices[known], known, tol_atr * atr[k], min_touches)
        zones = [(a, b) for a, b, last in zones if max_age is None or k - last <= max_age]
        out.append((df["close_time"].iat[k], zones, atr[k]))
    return out


def current_zones(df: pd.DataFrame, swing: int, lookback: int, max_age: int | None, tol_atr: float, min_touches: int,
                  atr_period: int) -> list[tuple[float, float, list[int]]]:
    """Vùng còn hiệu lực ở nến cuối (cùng quy tắc `_snapshots`), kèm vị trí các đỉnh/đáy swing tạo nên vùng."""
    is_high, is_low = ind.fractal_swings(df, swing, swing)
    k = len(df) - 1
    atr = float(ind.atr(df, atr_period).iat[-1])
    if k < 0 or not np.isfinite(atr):
        return []
    prices = np.where(is_high, df["high"].to_numpy(float), np.where(is_low, df["low"].to_numpy(float), np.nan))
    pivots = np.flatnonzero(is_high | is_low)
    known = pivots[(pivots >= max(0, k - lookback)) & (pivots + swing <= k)]
    groups = _groups(prices[known], known, tol_atr * atr, min_touches)
    return [(lo, hi, m) for lo, hi, m in groups if max_age is None or k - max(m) <= max_age]


def weekly(daily: pd.DataFrame) -> pd.DataFrame:
    """Nến W1 từ D1 (tuần Chủ nhật → thứ Bảy UTC, vàng mở tuần tối Chủ nhật); `close_time` = giờ đóng nến D1 cuối tuần."""
    g = daily.set_index("time").resample("W-SUN", label="left", closed="left")
    out = g.agg({"open": "first", "high": "max", "low": "min", "close": "last", "close_time": "max"})
    return out.dropna(subset=["open"]).reset_index()


def zone_frame(data: MarketData, tf: str) -> pd.DataFrame:
    return weekly(data.frame("D1")) if tf == "W1" else data.frame(tf)


def build_book(data: MarketData, cfg: dict) -> ZoneBook:
    """Gộp vùng của mọi khung trong `cfg["timeframes"]`; ATR tham chiếu = ATR của khung nhỏ nhất (khung cuối)."""
    events = []
    for tf, tc in cfg["timeframes"].items():
        for t, zones, a in _snapshots(zone_frame(data, tf), tc["swing"], tc["lookback"], tc.get("max_age"), cfg["tol_atr"],
                                      cfg["min_touches"], cfg["atr"]):
            events.append((t, tf, zones, a))
    events.sort(key=lambda e: e[0])
    latest: dict[str, list] = {}
    ref_tf = list(cfg["timeframes"])[-1]
    ref_atr = np.nan
    times, books, atrs = [], [], []
    for t, tf, zones, a in events:
        latest[tf] = zones
        if tf == ref_tf:
            ref_atr = a
        times.append(np.datetime64(t.tz_convert("UTC").tz_localize(None)))
        books.append(np.array([z for zs in latest.values() for z in zs], float).reshape(-1, 2))
        atrs.append(ref_atr)
    return ZoneBook(np.array(times, dtype="datetime64[ns]"), books, np.array(atrs, float))


def obstacle(zones: np.ndarray, d: int, entry: float) -> float | None:
    """Khoảng từ giá vào tới mép gần của vùng cản gần nhất phía trước (0 nếu giá vào nằm trong vùng); None = không có."""
    if not len(zones):
        return None
    low, high = zones[:, 0], zones[:, 1]
    ahead = high > entry if d == 1 else low < entry
    if not ahead.any():
        return None
    gaps = np.maximum((low - entry) if d == 1 else (entry - high), 0.0)
    return float(gaps[ahead].min())


def cleared(zones: np.ndarray, d: int, prev_close: float, close: float) -> bool:
    """Nến đóng cửa vượt qua trọn một vùng: trước đó đóng chưa qua mép xa, nay đóng qua mép xa."""
    if not len(zones):
        return False
    far = zones[:, 1] if d == 1 else zones[:, 0]
    return bool((((prev_close - far) * d <= 0) & ((close - far) * d > 0)).any())


def apply_sr(orders: list[Order], book: ZoneBook, cfg: dict) -> list[Order]:
    """Lọc lệnh theo khoảng trống tới vùng cản, tăng rủi ro khi phá vùng, đặt chốt một phần tại vùng cản."""
    out = []
    for o in orders:
        entry = o.meta.get("entry")
        if entry is None or o.sl_dist is None:
            out.append(o)
            continue
        zones, atr = book.at(o.time)
        d = int(o.direction)
        room = obstacle(zones, d, entry)
        if cfg.get("room") and room is not None and room < cfg["room"]["min_r"] * o.sl_dist:
            continue
        changes: dict = {}
        bonus = cfg.get("break_bonus")
        if bonus and o.meta.get("prev_close") is not None and cleared(zones, d, o.meta["prev_close"], entry):
            changes["risk_scale"] = bonus["risk_mult"]
            changes["reasons"] = (*o.reasons, "phá qua vùng S/R cứng")
        part = cfg.get("take_partial")
        if part and room is not None and np.isfinite(atr):
            tp1 = room - part["buffer_atr"] * atr
            if tp1 >= part.get("min_r", 1.0) * o.sl_dist:
                changes.update(tp1_dist=float(tp1), tp1_fraction=part["fraction"])
        out.append(dataclasses.replace(o, **changes) if changes else o)
    return out


def bounce(data: MarketData, book: ZoneBook, cfg: dict, code: str, since: pd.Timestamp | None = None) -> list[Order]:
    """Setup bật vùng: nến chạm vùng hỗ trợ/kháng cự cứng và là nến xác nhận đúng chiều, đóng cửa ngoài vùng."""
    orders = []
    for tf in cfg["timeframes"]:
        df = data.frame(tf)
        f = Frame.of(df)
        atr = ind.atr(df, cfg["atr"]).to_numpy(float)
        start = 1 if since is None else max(1, int(df["close_time"].searchsorted(since, side="right")))
        last = {1: -10**9, -1: -10**9}
        for k in range(start, len(df)):
            a = atr[k]
            if not np.isfinite(a):
                continue
            t = df["close_time"].iat[k]
            zones, _ = book.at(t)
            if not len(zones):
                continue
            for d in (1, -1):
                if k - last[d] < cfg["cooldown_bars"]:
                    continue
                near, far = (zones[:, 1], zones[:, 0]) if d == 1 else (zones[:, 0], zones[:, 1])
                prev_out = (f.c[k - 1] - near) * d > 0              # nến trước đóng ngoài vùng, phía lệnh
                touched = ((f.l[k] if d == 1 else f.h[k]) - near) * d <= 0
                closed_out = (f.c[k] - near) * d > 0
                hit = np.flatnonzero(prev_out & touched & closed_out)
                if not len(hit):
                    continue
                kind = _trigger(f, k, d, cfg["trigger"])
                if kind is None:
                    continue
                z = hit[np.argmax(near[hit] * d)]                    # vùng gần giá nhất
                extreme = f.l[k] if d == 1 else f.h[k]
                anchor = min(extreme, far[z]) if d == 1 else max(extreme, far[z])
                sl = anchor - d * cfg["sl_buffer_atr"] * a
                dist = (f.c[k] - sl) * d
                if not (0 < dist <= cfg["max_sl_atr"] * a):
                    continue
                last[d] = k
                direction = Direction.BUY if d == 1 else Direction.SELL
                lo, hi = zones[z]
                orders.append(Order(
                    f"{code}:zone_bounce@{tf}:{t:%Y%m%d%H%M}:{direction.name}", t, direction, MARKET, sl_dist=float(dist),
                    reasons=(f"zone_bounce {tf}: {kind} tại vùng {'hỗ trợ' if d == 1 else 'kháng cự'} {lo:.2f}–{hi:.2f}",),
                    meta={"tf": tf, "kind": "zone_bounce", "entry": float(f.c[k]), "prev_close": float(f.c[k - 1]),
                          "zone": [float(lo), float(hi)], "breakout_time": str(df["time"].iat[k])}))
    return sorted(orders, key=lambda o: o.time)
