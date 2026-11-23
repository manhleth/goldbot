"""Bối cảnh thị trường đa khung tại một thời điểm."""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from core.types import Direction
from mtf.bias import Bias
from mtf.view import TimeframeView


@dataclass(frozen=True)
class MarketContext:
    time: pd.Timestamp
    views: dict[str, TimeframeView]
    biases: dict[str, Bias]
    direction: Direction
    setup_tf: str

    @property
    def setup_view(self) -> TimeframeView:
        return self.views[self.setup_tf]

    def views_for(self, tfs: list[str]) -> list[TimeframeView]:
        return [self.views[tf] for tf in tfs if tf in self.views]
