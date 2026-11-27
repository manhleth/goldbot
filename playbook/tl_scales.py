"""Phá trendline ĐA TỈ LỆ + retest: không cố định số ngày của trendline.

Trendline được dò ở nhiều cỡ swing (`swings`, vd fractal 3 / 5 / 8 / 13 nến mỗi bên) trên mỗi khung (`timeframes`):
swing càng lớn thì các điểm neo càng thưa → đường tự dài ra (vài ngày tới nhiều tháng) mà không cần quy định độ dài.
Mỗi cỡ dùng playbook/trendlines.py (nhân quả): đường nối ≥ `min_touches` đỉnh/đáy swing, không nến nào đóng cửa xuyên
từ điểm đầu tới lúc phá; râu được xuyên tới `touch_tol_atr` × ATR. Độ dốc tuỳ ý (`any_slope`, mặc định bật): hỗ trợ có
thể đi xuống (đáy kênh giảm, nêm), kháng cự có thể đi lên.
1. Phá: nến đóng cửa vượt đường quá `break_atr` × ATR. Đường nối đáy bị phá xuống → SELL; nối đỉnh bị phá lên → BUY.
   Cùng một cú phá thấy ở nhiều cỡ swing → giữ đường dài nhất (đáng tin nhất).
2. Retest: giá quay lại vùng đường (± `zone_atr` × ATR) trong khoảng `retest.span_frac` × độ dài đường (tối thiểu
   `retest.min_bars` nến) — đường càng dài thì chờ retest càng lâu; đóng cửa quay vào trong quá `invalid_atr` → huỷ.
3. Vào lệnh: nến pin bar / engulfing ở khung xác nhận (`confirm_tf`) đóng cửa phía đã phá (playbook/retest.py).
   SL = đỉnh/đáy từ lúc chạm ± `sl_buffer_atr` × ATR, bỏ nếu xa hơn `max_sl_atr` × ATR. Không đặt TP (gồng theo biến thể).
Khoá lệnh `<code>:tl_retest@<tf>:...`.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from core.types import Direction
from playbook import indicators as ind
from playbook.common import MarketData
from playbook.orders import MARKET, Order
from playbook.retest import Frame, confirm_entry
from playbook.trendlines import LineBreak, LineRules, build

KIND = "tl_retest"


def _breaks(df: pd.DataFrame, p: dict) -> list[LineBreak]:
    """Cú phá ở mọi cỡ swing; cùng nến + cùng chiều thì giữ đường có điểm đầu xa nhất."""
    r = p["rules"]
    rules = LineRules(r["min_touches"], r["touch_tol_atr"], r.get("channel_min_touches", 99), r["max_pivots"],
                      r.get("any_slope", True))
    best: dict[tuple[int, int], LineBreak] = {}
    for swing in p["swings"]:
        for brk in build(df, swing, rules, p["break_atr"], p["atr"]).breaks:
            key = (brk.index, int(brk.side))
            if key not in best or brk.line.i1 < best[key].line.i1:
                best[key] = brk
    return sorted(best.values(), key=lambda b: b.index)


def _order(code: str, tf: str, brk: LineBreak, hit: tuple[int, float, str], pf: pd.DataFrame, cf: pd.DataFrame,
           close: float, confirm: str) -> Order:
    j, sl, candle = hit
    d = Direction(-int(brk.side))
    t = cf["close_time"].iat[j]
    line, k, times = brk.line, brk.index, pf["time"]
    span = k - line.i1
    what = "đáy" if brk.side == Direction.BUY else "đỉnh"
    return Order(
        f"{code}:{KIND}@{tf}:{t:%Y%m%d%H%M}:{d.name}", t, d, MARKET, sl_dist=float((close - sl) * int(d)), tp=None,
        reasons=(f"phá trendline {tf} nối {line.touches} {what} ({span} nến, từ {times.iat[line.i1]:%d/%m/%Y})",
                 f"retest đường {line.value(k):.2f}, {candle} {confirm} xác nhận"),
        meta={"tf": tf, "kind": KIND, "line": float(line.value(k)), "breakout_time": str(times.iat[k]),
              "edges": [[str(times.iat[line.i1]), float(line.p1), str(times.iat[line.i2]), float(line.p2)]]})


def tl_retest(data: MarketData, p: dict, code: str, since: pd.Timestamp | None = None) -> list[Order]:
    """`p`: mục `tl_scales` của phương pháp; `since` (live): chỉ trả lệnh từ thời điểm này."""
    orders: list[Order] = []
    rt = p["retest"]
    for tf in p["timeframes"]:
        pf, cf = data.frame(tf), data.frame(p["confirm_tf"][tf])
        cfr = Frame.of(cf)
        atr = ind.atr(pf, p["atr"]).to_numpy(float)
        used: set[tuple[int, int]] = set()  # mỗi đường vào tối đa một lệnh
        for brk in _breaks(pf, p):
            k = brk.index
            ident = (brk.line.i1, int(brk.side))
            if ident in used or not np.isfinite(atr[k]):
                continue
            until = k + max(rt["min_bars"], int(round(rt["span_frac"] * (k - brk.line.i1))))
            hit = confirm_entry(-int(brk.side), brk.line, pf, k, until, atr[k], cf, cfr, rt)
            if hit is None:
                continue
            used.add(ident)
            order = _order(code, tf, brk, hit, pf, cf, float(cfr.c[hit[0]]), p["confirm_tf"][tf])
            if since is None or order.time >= since:
                orders.append(order)
    return sorted(orders, key=lambda o: o.time)
