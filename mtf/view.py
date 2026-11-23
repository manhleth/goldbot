"""Ảnh chụp các nến đã đóng của một khung tại một thời điểm, cấu trúc được tính lười và cache."""
from __future__ import annotations

from functools import cached_property

import pandas as pd

from structure.breaks import StructureBreak, find_breaks
from structure.fvg import FairValueGap, find_fvgs
from structure.order_block import OrderBlock, find_order_blocks
from structure.swings import Swing, find_swings
from structure.zones import SRZone, cluster_zones


class TimeframeView:
    def __init__(self, tf: str, df: pd.DataFrame, cfg: dict) -> None:
        self.tf = tf
        self.df = df
        self._cfg = cfg

    @property
    def last_time(self) -> pd.Timestamp:
        return self.df["time"].iat[-1]

    @property
    def close(self) -> float:
        return float(self.df["close"].iat[-1])

    @property
    def atr(self) -> float:
        return float(self.df["atr"].iat[-1])

    @cached_property
    def swings(self) -> list[Swing]:
        return find_swings(self.df, self._cfg["structure"]["fractal_n"][self.tf])

    @cached_property
    def breaks(self) -> list[StructureBreak]:
        return find_breaks(self.df, self.swings)

    @cached_property
    def sr_zones(self) -> list[SRZone]:
        sc = self._cfg["structure"]
        return cluster_zones(self.swings, sc["zone_cluster_atr"] * self.atr, sc["zone_min_touches"])

    @cached_property
    def fvgs(self) -> list[FairValueGap]:
        fc = self._cfg["fvg"]
        return find_fvgs(self.df, fc["min_size_atr"], fc["impulse_body_atr"])

    @cached_property
    def order_blocks(self) -> list[OrderBlock]:
        oc = self._cfg["order_block"]
        return find_order_blocks(self.df, self.breaks, oc["min_move_atr"], oc["search_bars"])
