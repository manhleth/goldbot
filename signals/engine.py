"""Bộ phân tích dùng chung cho backtest và live: dữ liệu đã đóng tại t → bối cảnh → setup → tín hiệu."""
from __future__ import annotations

import pandas as pd

from core.config import confirm_timeframes
from core.types import Direction, Setup, Signal
from data.candles import closed_end
from mtf.bias import Bias, combine_biases, timeframe_bias
from mtf.context import MarketContext
from mtf.view import TimeframeView
from signals.confirm import confirm
from signals.registry import enabled_finders

_REQUIRED_COLUMNS = ("atr", "adx", "rsi")


class Analyzer:
    """Giữ cache theo nến cuối của từng khung để không tính lại khi khung lớn chưa có nến mới."""

    def __init__(self, cfg: dict) -> None:
        self._cfg = cfg
        tfs = cfg["timeframes"]
        self._bias_tfs: list[str] = list(tfs["bias"])
        self._setup_tf: str = tfs["setup"]
        self._confirm_tfs: list[str] = confirm_timeframes(cfg)
        self._windows: dict[str, int] = cfg["data"]["window_bars"]
        self._required = (*_REQUIRED_COLUMNS, *(f"ema_{p}" for p in cfg["structure"]["ema"]))
        self._finders = enabled_finders(cfg)
        self._views: dict[str, TimeframeView] = {}
        self._biases: dict[tuple[str, pd.Timestamp], Bias] = {}
        self._setups: tuple[tuple, list[Setup]] | None = None

    def view(self, frames: dict[str, pd.DataFrame], tf: str, t: pd.Timestamp) -> TimeframeView | None:
        """Các nến của khung `tf` đã đóng tại t (cửa sổ cố định), None nếu chỉ báo chưa đủ dữ liệu."""
        df = frames[tf]
        end = closed_end(df, t)
        if end == 0:
            return None
        cached = self._views.get(tf)
        if cached is not None and cached.last_time == df["time"].iat[end - 1]:
            return cached
        window = df.iloc[max(0, end - self._windows[tf]):end].reset_index(drop=True)
        if window[list(self._required)].iloc[-1].isna().any():
            return None
        view = TimeframeView(tf, window, self._cfg)
        self._views[tf] = view
        return view

    def _bias(self, view: TimeframeView) -> Bias:
        key = (view.tf, view.last_time)
        if key not in self._biases:
            self._biases[key] = timeframe_bias(view, self._cfg)
        return self._biases[key]

    def context(self, frames: dict[str, pd.DataFrame], t: pd.Timestamp) -> MarketContext | None:
        views: dict[str, TimeframeView] = {}
        for tf in dict.fromkeys([*self._bias_tfs, self._setup_tf]):
            view = self.view(frames, tf, t)
            if view is None:
                return None
            views[tf] = view
        biases = {tf: self._bias(views[tf]) for tf in self._bias_tfs}
        direction = combine_biases((b.direction for b in biases.values()), self._cfg["bias"]["combine"])
        return MarketContext(t, views, biases, direction, self._setup_tf)

    def setups(self, ctx: MarketContext) -> list[Setup]:
        key = (ctx.direction, tuple((tf, v.last_time) for tf, v in ctx.views.items()))
        if self._setups is None or self._setups[0] != key:
            found = [setup for finder in self._finders for setup in finder(ctx, self._cfg)]
            self._setups = (key, found)
        return self._setups[1]

    def signals(self, frames: dict[str, pd.DataFrame], t: pd.Timestamp) -> tuple[MarketContext | None, list[Signal]]:
        ctx = self.context(frames, t)
        if ctx is None or ctx.direction == Direction.NEUTRAL:
            return ctx, []
        setups = self.setups(ctx)
        if not setups:
            return ctx, []
        views = [v for v in (self.view(frames, tf, t) for tf in self._confirm_tfs)
                 if v is not None and v.df["close_time"].iat[-1] == t]  # chỉ khung vừa đóng nến tại t
        bias = {tf: b.direction for tf, b in ctx.biases.items()}
        out: list[Signal] = []
        for setup in setups:
            for view in views:
                trig = confirm(setup, view, self._cfg)
                if trig is not None:
                    name = trig.name if len(self._confirm_tfs) == 1 else f"{trig.name}@{view.tf}"
                    out.append(Signal(t, setup, name, trig.extreme, trig.close, trig.rsi, bias))
                    break
        return ctx, out
