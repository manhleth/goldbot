"""Chỉ số theo tiền và dữ liệu cho biểu đồ thống kê (đường equity, drawdown, theo tháng, phân bố R)."""
from __future__ import annotations

import math

import numpy as np
import pandas as pd


def equity_curve(trades: pd.DataFrame, initial_equity: float) -> pd.DataFrame:
    """Equity sau mỗi lệnh đóng (sắp theo giờ đóng) kèm drawdown tính từ đỉnh gần nhất."""
    ordered = trades.sort_values("exit_time")
    equity = initial_equity + ordered["pnl"].cumsum().to_numpy(dtype=float)
    peak = np.maximum.accumulate(np.concatenate([[initial_equity], equity]))[1:]
    return pd.DataFrame({
        "time": pd.to_datetime(ordered["exit_time"], utc=True, format="ISO8601").to_numpy(),
        "equity": equity,
        "drawdown": equity - peak,
        "drawdown_pct": np.where(peak > 0, (equity - peak) / peak * 100, 0.0),
    })


def money_summary(trades: pd.DataFrame, initial_equity: float) -> dict:
    pnl = trades["pnl"].to_numpy(dtype=float)
    wins, losses = pnl[pnl > 0], pnl[pnl <= 0]
    curve = equity_curve(trades, initial_equity)
    hold = (pd.to_datetime(trades["exit_time"], utc=True, format="ISO8601")
            - pd.to_datetime(trades["entry_time"], utc=True, format="ISO8601")).dt.total_seconds() / 3600
    gross_loss = float(-losses.sum())
    return {
        "initial_equity": initial_equity,
        "final_equity": float(curve["equity"].iat[-1]),
        "net_profit": float(pnl.sum()),
        "return_pct": float(pnl.sum()) / initial_equity * 100 if initial_equity else None,
        "gross_profit": float(wins.sum()),
        "gross_loss": gross_loss,
        "profit_factor": float(wins.sum()) / gross_loss if gross_loss > 0 else (math.inf if wins.size else 0.0),
        "avg_win": float(wins.mean()) if wins.size else 0.0,
        "avg_loss": float(-losses.mean()) if losses.size else 0.0,
        "largest_win": float(wins.max()) if wins.size else 0.0,
        "largest_loss": float(-losses.min()) if losses.size else 0.0,
        "expectancy": float(pnl.mean()),
        "max_drawdown": float(-curve["drawdown"].min()),
        "max_drawdown_pct": float(-curve["drawdown_pct"].min()),
        "avg_hold_hours": float(hold.mean()),
    }


def monthly(trades: pd.DataFrame) -> list[dict]:
    exits = pd.to_datetime(trades["exit_time"], utc=True, format="ISO8601").dt.tz_localize(None)
    grouped = trades.assign(month=exits.dt.to_period("M").astype(str)).groupby("month", sort=True)
    return [{"month": month, "pnl": float(g["pnl"].sum()), "r": float(g["r_multiple"].sum()), "trades": int(len(g)),
             "winrate": float((g["r_multiple"] > 0).mean())} for month, g in grouped]


def r_histogram(r_values: pd.Series, bin_width: float = 0.5) -> list[dict]:
    """Số lệnh theo khoảng R, khoảng rỗng ở giữa vẫn giữ để trục liên tục."""
    r = r_values.to_numpy(dtype=float)
    if r.size == 0:
        return []
    lo = math.floor(r.min() / bin_width) * bin_width
    hi = math.floor(r.max() / bin_width) * bin_width + bin_width
    edges = np.arange(lo, hi + bin_width / 2, bin_width)
    counts, _ = np.histogram(r, bins=edges)
    return [{"from": float(a), "to": float(b), "count": int(n)} for a, b, n in zip(edges[:-1], edges[1:], counts)]
