"""Khung thời gian hỗ trợ."""
from __future__ import annotations

import pandas as pd

TF_MINUTES: dict[str, int] = {"M1": 1, "M5": 5, "M15": 15, "M30": 30, "H1": 60, "H2": 120, "H4": 240, "D1": 1440, "W1": 10080}


def tf_delta(tf: str) -> pd.Timedelta:
    try:
        return pd.Timedelta(minutes=TF_MINUTES[tf])
    except KeyError:
        raise ValueError(f"Khung thời gian không hỗ trợ: {tf}") from None
