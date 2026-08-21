"""Frozen market-proxy crash construction."""

from __future__ import annotations

import pandas as pd

from ashare_research.mechanism.analysis_contracts import (
    PRIMARY_CRASH_THRESHOLD,
    AnalysisContractError,
)


def add_crash_indicator(
    frame: pd.DataFrame,
    threshold: float = PRIMARY_CRASH_THRESHOLD,
) -> pd.DataFrame:
    """Add ``Crash_t`` using only SH_MARKET_EX_601857 return."""

    if "market_ex_target_return" not in frame.columns:
        raise AnalysisContractError("market_ex_target_return is required for Crash_t")
    result = frame.copy()
    result["Crash_t"] = (
        pd.to_numeric(result["market_ex_target_return"], errors="raise") <= threshold
    ).astype(int)
    return result

