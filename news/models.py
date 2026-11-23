"""Sự kiện lịch kinh tế."""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True, slots=True)
class NewsEvent:
    time: pd.Timestamp  # UTC
    title: str
    country: str
    impact: str  # High / Medium / Low / Holiday
    forecast: str = ""
    previous: str = ""
    source: str = "forexfactory"

    @property
    def key(self) -> str:
        return f"{self.time.isoformat()}|{self.country}|{self.title}"
