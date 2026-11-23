"""Báo cáo thống kê dạng văn bản, kèm breakdown và cảnh báo cỡ mẫu."""
from __future__ import annotations

import pandas as pd

from risk.calendar import session_of
from stats.metrics import summarize

BREAKDOWNS = (("SETUP", "setup"), ("CHIỀU", "direction"), ("PHIÊN", "session"), ("BIAS", "bias"),
              ("TIN TỨC (dự báo so với chiều lệnh)", "news"), ("GIAI ĐOẠN (quý) — kiểm tra độ ổn định", "period"))
_COLUMNS = ["trades", "winrate", "winrate_ci_low", "winrate_ci_high", "avg_win_r", "avg_loss_r",
            "expectancy_r", "profit_factor", "total_r", "max_dd_r", "longest_losing_streak"]


def verdict(n: int, stats_cfg: dict) -> str:
    if n < stats_cfg["min_trades_any"]:
        return f"Chỉ {n} lệnh (< {stats_cfg['min_trades_any']}): KHÔNG kết luận gì."
    if n < stats_cfg["min_trades_reliable"]:
        return f"{n} lệnh (< {stats_cfg['min_trades_reliable']}): chưa đủ tin cậy, chỉ tham khảo."
    return f"{n} lệnh: đủ cỡ mẫu tối thiểu; vẫn cần kiểm tra ổn định giữa các giai đoạn và forward test."


def breakdown(trades: pd.DataFrame, by: str) -> pd.DataFrame:
    rows = {key: summarize(group["r_multiple"]) for key, group in trades.groupby(by, sort=True)}
    return pd.DataFrame.from_dict(rows, orient="index")[_COLUMNS]


def with_dimensions(trades: pd.DataFrame, sessions: dict) -> pd.DataFrame:
    """`sessions` = mục `sessions` của config (múi giờ + các phiên)."""
    out = trades.copy()
    entry = pd.to_datetime(out["entry_time"], utc=True, format="ISO8601")
    out["session"] = [session_of(ts, sessions) for ts in entry]
    out["period"] = entry.dt.tz_localize(None).dt.to_period("Q").astype(str)
    return out


def _fmt(df: pd.DataFrame) -> str:
    return df.to_string(float_format=lambda v: f"{v:.3f}")


def build_report(trades: pd.DataFrame, equity: pd.DataFrame, cfg: dict) -> str:
    lines = ["=" * 72, "BÁO CÁO THỐNG KÊ (đơn vị chính: R-multiple, đã tính spread + slippage)", "=" * 72]
    n = len(trades)
    lines.append(verdict(n, cfg["stats"]))
    if n == 0:
        return "\n".join(lines)
    total = summarize(trades["r_multiple"])
    lines += [
        "",
        f"Số lệnh           : {total['trades']}",
        f"Tỉ lệ thắng       : {total['winrate']:.1%}  (Wilson 95%: {total['winrate_ci_low']:.1%} – "
        f"{total['winrate_ci_high']:.1%})",
        f"R TB thắng / thua : {total['avg_win_r']:.2f} / {total['avg_loss_r']:.2f}",
        f"Expectancy        : {total['expectancy_r']:+.3f} R/lệnh",
        f"Profit factor     : {total['profit_factor']:.2f}",
        f"Tổng R            : {total['total_r']:+.2f}",
        f"Max drawdown (R)  : {total['max_dd_r']:.2f}",
        f"Chuỗi thua dài nhất: {total['longest_losing_streak']}",
    ]
    if not equity.empty:
        lines.append(f"Max drawdown (%)  : {equity['drawdown_pct'].max():.2f}%  | Equity cuối: "
                     f"{equity['equity'].iloc[-1]:,.2f}")
    if total["expectancy_r"] > 0 and total["winrate_ci_low"] * total["avg_win_r"] - \
            (1 - total["winrate_ci_low"]) * total["avg_loss_r"] <= 0:
        lines.append("Lưu ý: expectancy dương, nhưng nếu tỉ lệ thắng thật ở cận dưới Wilson thì expectancy ≤ 0 "
                     "→ chưa chứng minh được edge.")
    enriched = with_dimensions(trades, cfg["sessions"])
    for title, column in BREAKDOWNS:
        if column in enriched.columns:
            lines += ["", f"--- Theo {title} ---", _fmt(breakdown(enriched, column))]
    lines += ["", "--- Lý do thoát ---", trades["exit_reason"].value_counts().to_string()]
    return "\n".join(lines)


def signal_summary(signals: pd.DataFrame) -> str:
    if signals.empty:
        return "Không có tín hiệu nào."
    rejected = signals[signals["accepted"] == 0]
    lines = [f"Tín hiệu: {len(signals)} | vào lệnh: {int(signals['accepted'].sum())} | bỏ qua: {len(rejected)}"]
    if not rejected.empty:
        lines += ["Lý do bỏ qua:", rejected["reject_reason"].value_counts().to_string()]
    return "\n".join(lines)
