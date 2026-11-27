"""Vẽ chart lý do vào lệnh (SVG thuần, không cần thư viện): nến khung mẫu hình, các cạnh trendline, vào/SL/thoát.

`live=True`: ảnh hiện tại của lệnh đang mở — thêm SL hiện tại (đã dời), giá hiện tại và R thả nổi thay cho điểm thoát.
"""
from __future__ import annotations

from dataclasses import dataclass
from html import escape

import numpy as np
import pandas as pd

W, H = 960, 520
LEFT, RIGHT, TOP, BOTTOM = 12, 78, 92, 34
COLORS = {"bg": "#131722", "grid": "#2a2e39", "text": "#d1d4dc", "muted": "#787b86", "up": "#26a69a",
          "down": "#ef5350", "edge": "#f5f5f5", "entry": "#2962ff", "sl": "#ef5350", "target": "#ffb74d",
          "exit": "#ffeb3b", "sl_now": "#ff9800", "price": "#d1d4dc"}
MAX_BARS = 220


@dataclass(frozen=True)
class TradeView:
    direction: int            # +1 BUY / −1 SELL
    entry_time: pd.Timestamp
    entry: float
    sl: float
    exit_time: pd.Timestamp
    exit_price: float
    r: float
    title: str
    reasons: tuple[str, ...]
    meta: dict
    current_sl: float | None = None  # SL hiện tại của lệnh đang mở (sau khi dời)
    live: bool = False


def _window(df: pd.DataFrame, view: TradeView) -> pd.DataFrame:
    times = df["time"]
    starts = [pd.Timestamp(e[0]) for e in view.meta.get("edges", [])] or [view.entry_time]
    i0 = max(0, int(times.searchsorted(min(starts))) - 5)
    i_entry = int(times.searchsorted(view.entry_time))
    i1 = min(len(df), int(times.searchsorted(view.exit_time)) + 6)
    if i1 - i0 > MAX_BARS and view.live:  # lệnh đang mở giữ lâu: ưu tiên nến gần nhất
        i0 = i1 - MAX_BARS
    elif i1 - i0 > MAX_BARS:  # lệnh giữ quá lâu: ưu tiên phần mẫu hình + đầu lệnh
        i0 = max(i0, i_entry - int(MAX_BARS * 0.65))
        i1 = min(i1, i0 + MAX_BARS)
    return df.iloc[i0:i1].reset_index(drop=True)


def _level(x0: float, x1: float, yy: float, color: str, text: str, dash: str) -> list[str]:
    return [f'<line x1="{x0:.1f}" x2="{x1:.1f}" y1="{yy:.1f}" y2="{yy:.1f}" stroke="{color}" stroke-dasharray="{dash}"/>',
            f'<text x="{x1 - 4:.1f}" y="{yy - 5:.1f}" fill="{color}" font-size="11" text-anchor="end">{escape(text)}</text>']


def render(df: pd.DataFrame, view: TradeView) -> str:
    win = _window(df, view)
    n = len(win)
    times = win["time"]
    target = view.meta.get("target")
    prices = [win["low"].min(), win["high"].max(), view.sl, view.entry, view.exit_price]
    if view.current_sl is not None:
        prices.append(view.current_sl)
    lo, hi = min(prices), max(prices)
    pad = (hi - lo) * 0.06 or 1.0
    lo, hi = lo - pad, hi + pad
    plot_w, plot_h = W - LEFT - RIGHT, H - TOP - BOTTOM
    step = plot_w / max(n, 1)

    def x(i: float) -> float:
        return LEFT + (i + 0.5) * step

    def y(p: float) -> float:
        return TOP + (hi - p) / (hi - lo) * plot_h

    def index_of(t) -> float:
        return float(times.searchsorted(pd.Timestamp(t)))

    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" '
           f'font-family="Segoe UI, Arial, sans-serif">', f'<rect width="{W}" height="{H}" fill="{COLORS["bg"]}"/>']
    for k in range(6):  # lưới + nhãn giá
        p = lo + (hi - lo) * k / 5
        out.append(f'<line x1="{LEFT}" x2="{W - RIGHT}" y1="{y(p):.1f}" y2="{y(p):.1f}" stroke="{COLORS["grid"]}"/>')
        out.append(f'<text x="{W - RIGHT + 6}" y="{y(p) + 4:.1f}" fill="{COLORS["muted"]}" font-size="11">{p:.2f}</text>')
    for k in np.linspace(0, n - 1, 5).astype(int) if n else []:
        out.append(f'<text x="{x(k):.1f}" y="{H - 12}" fill="{COLORS["muted"]}" font-size="11" text-anchor="middle">'
                   f'{times.iat[k]:%d/%m %H:%M}</text>')
    body_w = max(1.0, step * 0.62)
    for i, row in win.iterrows():
        color = COLORS["up"] if row["close"] >= row["open"] else COLORS["down"]
        top, bot = max(row["open"], row["close"]), min(row["open"], row["close"])
        out.append(f'<line x1="{x(i):.1f}" x2="{x(i):.1f}" y1="{y(row["high"]):.1f}" y2="{y(row["low"]):.1f}" '
                   f'stroke="{color}"/>')
        out.append(f'<rect x="{x(i) - body_w / 2:.1f}" y="{y(top):.1f}" width="{body_w:.1f}" '
                   f'height="{max(1.0, y(bot) - y(top)):.1f}" fill="{color}"/>')
    brk = index_of(view.meta.get("breakout_time", view.entry_time))
    for t1, p1, t2, p2 in view.meta.get("edges", []):  # cạnh mẫu hình, kéo dài tới sau nến phá
        a, b = index_of(t1), index_of(t2)
        if b <= a:
            continue
        slope = (p2 - p1) / (b - a)
        end = min(n - 1, brk + 6)
        out.append(f'<line x1="{x(a):.1f}" y1="{y(p1):.1f}" x2="{x(end):.1f}" y2="{y(p1 + slope * (end - a)):.1f}" '
                   f'stroke="{COLORS["edge"]}" stroke-width="2" opacity="0.9"/>')
        for i, p in ((a, p1), (b, p2)):
            out.append(f'<circle cx="{x(i):.1f}" cy="{y(p):.1f}" r="3.5" fill="{COLORS["edge"]}"/>')
    ie, ix = index_of(view.entry_time), min(index_of(view.exit_time), n - 1)
    moved = view.current_sl is not None and abs(view.current_sl - view.sl) >= 0.01
    sl_note = " (chưa dời)" if view.live and not moved else (" ban đầu" if moved else "")
    out.append(f'<line x1="{x(ie):.1f}" x2="{x(ix):.1f}" y1="{y(view.sl):.1f}" y2="{y(view.sl):.1f}" '
               f'stroke="{COLORS["sl"]}" stroke-dasharray="6 4"/>')
    out.append(f'<text x="{x(ie) + 4:.1f}" y="{y(view.sl) + (14 if view.direction > 0 else -6):.1f}" '
               f'fill="{COLORS["sl"]}" font-size="11">SL {view.sl:.2f}{sl_note}</text>')
    if target is not None and lo < target < hi:
        out.append(f'<line x1="{x(ie):.1f}" x2="{x(n - 1):.1f}" y1="{y(target):.1f}" y2="{y(target):.1f}" '
                   f'stroke="{COLORS["target"]}" stroke-dasharray="2 4"/>')
        out.append(f'<text x="{x(ie) + 4:.1f}" y="{y(target) - 5:.1f}" fill="{COLORS["target"]}" font-size="11">'
                   f'measured move {target:.2f}</text>')
    if view.current_sl is not None and abs(view.current_sl - view.sl) >= 0.01:  # MT5 làm tròn giá SL
        out += _level(x(ie), x(n - 1), y(view.current_sl), COLORS["sl_now"], f"SL hiện tại {view.current_sl:.2f}", "4 3")
    if n and times.iat[0] <= view.entry_time:  # điểm vào còn trong khung nhìn
        tri = 9 * view.direction
        ye = y(view.entry)
        out.append(f'<polygon points="{x(ie):.1f},{ye:.1f} {x(ie) - 7:.1f},{ye + tri:.1f} {x(ie) + 7:.1f},{ye + tri:.1f}" '
                   f'fill="{COLORS["entry"]}"/>')
    if view.live:
        out += _level(LEFT, W - RIGHT, y(view.exit_price), COLORS["price"], f"Giá hiện tại {view.exit_price:.2f}", "1 3")
    else:
        out.append(f'<circle cx="{x(ix):.1f}" cy="{y(view.exit_price):.1f}" r="5" fill="none" stroke="{COLORS["exit"]}" '
                   f'stroke-width="2"/>')
    side = "BUY" if view.direction > 0 else "SELL"
    until = "đang mở, R thả nổi" if view.live else f"{view.exit_time:%d/%m/%Y %H:%M}"
    out.append(f'<text x="{LEFT}" y="24" fill="{COLORS["text"]}" font-size="16" font-weight="600">{escape(view.title)}</text>')
    out.append(f'<text x="{LEFT}" y="46" fill="{COLORS["text"]}" font-size="13">{side} {view.entry:.2f} · '
               f'{view.entry_time:%d/%m/%Y %H:%M} UTC → {until} · '
               f'<tspan fill="{COLORS["up"] if view.r > 0 else COLORS["down"]}">{view.r:+.2f}R</tspan></text>')
    out.append(f'<text x="{LEFT}" y="68" fill="{COLORS["muted"]}" font-size="12">'
               f'{escape(" · ".join(view.reasons))}</text>')
    out.append("</svg>")
    return "\n".join(out)
