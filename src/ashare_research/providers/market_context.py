"""Capability-specific provider protocols for M3 market-context data."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

import pandas as pd


@runtime_checkable
class CommodityDailyProvider(Protocol):
    """Provider that supplies a specifically identified commodity benchmark."""

    def get_commodity_daily(
        self, benchmark_id: str, start_date: str, end_date: str
    ) -> pd.DataFrame: ...


@runtime_checkable
class IndustryIndexProvider(Protocol):
    """Provider that supplies a frozen industry-index series."""

    def get_industry_index_daily(
        self, symbol: str, start_date: str, end_date: str
    ) -> pd.DataFrame: ...


@runtime_checkable
class HistoricalUniverseProvider(Protocol):
    """Provider that supplies a dated exchange-security snapshot."""

    def get_universe_snapshot(self, trade_date: str, exchange: str = "SH") -> pd.DataFrame: ...


@runtime_checkable
class HistoricalShareProvider(Protocol):
    """Provider that supplies effective-dated issued-share changes."""

    def get_share_history(
        self, symbol: str, start_date: str, end_date: str
    ) -> pd.DataFrame: ...
