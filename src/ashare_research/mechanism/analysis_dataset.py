"""Validated and canonicalized Stage 3C-A analysis input."""

from __future__ import annotations

import numpy as np
import pandas as pd

from ashare_research.mechanism.analysis_contracts import (
    ANALYSIS_COLUMNS,
    DEVELOPMENT_END,
    DEVELOPMENT_START,
    RETURN_COLUMNS,
    AnalysisContractError,
)

FORBIDDEN_TARGET_COLUMNS = {
    "target_unadjusted_return",
    "unadjusted_target_return",
    "raw_target_return",
}


def prepare_analysis_dataset(frame: pd.DataFrame) -> pd.DataFrame:
    """Validate, sort, and return a defensive copy of the analysis table."""

    if not isinstance(frame, pd.DataFrame):
        raise AnalysisContractError("analysis input must be a pandas DataFrame")
    missing = [column for column in ANALYSIS_COLUMNS if column not in frame.columns]
    if missing:
        raise AnalysisContractError(f"missing analysis columns: {missing}")
    forbidden = sorted(FORBIDDEN_TARGET_COLUMNS.intersection(frame.columns))
    if forbidden:
        raise AnalysisContractError(
            "target adjusted/unadjusted series mixing is forbidden: "
            + ", ".join(forbidden)
        )
    result = frame.loc[:, list(ANALYSIS_COLUMNS)].copy()
    result["trade_date"] = pd.to_datetime(result["trade_date"], errors="raise")
    if result["trade_date"].duplicated().any():
        raise AnalysisContractError("duplicate trade_date")
    for column in RETURN_COLUMNS:
        result[column] = pd.to_numeric(result[column], errors="raise")
        if not np.isfinite(result[column].to_numpy(dtype=float)).all():
            raise AnalysisContractError(f"non-finite return: {column}")
    for column in (
        "target_valid",
        "market_valid",
        "oil_valid",
        "industry_valid",
        "tier1_joint_valid",
    ):
        if result[column].isna().any():
            raise AnalysisContractError(f"missing validity flag: {column}")
        if not result[column].map(lambda value: isinstance(value, bool | np.bool_)).all():
            raise AnalysisContractError(f"validity flag must be boolean: {column}")
        result[column] = result[column].astype(bool)
    return result.sort_values("trade_date", kind="mergesort").reset_index(drop=True)


def select_development_sample(frame: pd.DataFrame) -> pd.DataFrame:
    """Apply the frozen validity and development-date rule."""

    result = prepare_analysis_dataset(frame)
    dates = result["trade_date"].dt.date
    date_mask = (dates >= DEVELOPMENT_START) & (dates <= DEVELOPMENT_END)
    valid_mask = result["target_valid"] & result["tier1_joint_valid"]
    selected = result.loc[date_mask & valid_mask].copy()
    if selected.empty:
        raise AnalysisContractError("development sample is empty")
    return selected.reset_index(drop=True)

