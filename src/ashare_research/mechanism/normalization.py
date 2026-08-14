"""Typed normalization and point-in-time alignment for Stage 3B inputs."""

from __future__ import annotations

from datetime import time

import pandas as pd

from ashare_research.exceptions import DuplicateKeyError
from ashare_research.mechanism.contracts import (
    Stage3BContractError,
    validate_development_dates,
)

NORMALIZED_COLUMNS = [
    "dataset_id",
    "instrument_id",
    "trade_date",
    "observation_time",
    "available_at",
    "value",
    "return",
    "currency",
    "adjustment",
    "source_name",
    "source_endpoint",
    "source_version",
    "raw_sha256",
    "schema_version",
    "quality_status",
]


def normalize_daily_observations(
    frame: pd.DataFrame,
    *,
    dataset_id: str,
    instrument_id: str,
    currency: str,
    adjustment: str,
    source_name: str,
    source_endpoint: str,
    source_version: str,
    raw_sha256: str,
) -> pd.DataFrame:
    """Normalize daily values without silently inventing missing source metadata."""
    required = {"trade_date", "observation_time", "available_at", "value"}
    missing = sorted(required - set(frame.columns))
    if missing:
        raise Stage3BContractError(f"normalization input missing columns: {missing}")
    if not raw_sha256 or len(raw_sha256) != 64:
        raise Stage3BContractError("raw_sha256 must be a 64-character digest")

    result = frame.loc[:, sorted(required)].copy()
    dates = validate_development_dates(result, allow_warmup=True)
    result["trade_date"] = pd.to_datetime(dates)
    result["observation_time"] = pd.to_datetime(
        result["observation_time"], errors="coerce", utc=True
    )
    result["available_at"] = pd.to_datetime(result["available_at"], errors="coerce", utc=True)
    result["value"] = pd.to_numeric(result["value"], errors="coerce")
    if result[["observation_time", "available_at", "value"]].isna().any().any():
        raise Stage3BContractError("normalization input has invalid timestamp or value")
    if (result["available_at"] < result["observation_time"]).any():
        raise Stage3BContractError("available_at precedes observation_time")
    if result["trade_date"].duplicated().any():
        raise DuplicateKeyError(f"duplicate trade_date for {dataset_id}")

    result = result.sort_values("trade_date", kind="mergesort").reset_index(drop=True)
    result["return"] = result["value"].pct_change(fill_method=None)
    result["dataset_id"] = dataset_id
    result["instrument_id"] = instrument_id
    result["currency"] = currency
    result["adjustment"] = adjustment
    result["source_name"] = source_name
    result["source_endpoint"] = source_endpoint
    result["source_version"] = source_version
    result["raw_sha256"] = raw_sha256.lower()
    result["schema_version"] = "1.0.0"
    result["quality_status"] = "NORMALIZED"
    return result.loc[:, NORMALIZED_COLUMNS]


def align_latest_observable_before_a_share_close(
    a_share_dates: pd.Series,
    observations: pd.DataFrame,
) -> pd.DataFrame:
    """As-of align observations using release availability, never date-string equality."""
    required = {"available_at", "observation_time", "value"}
    missing = sorted(required - set(observations.columns))
    if missing:
        raise Stage3BContractError(f"alignment input missing columns: {missing}")
    calendar = pd.DataFrame({"trade_date": pd.to_datetime(a_share_dates, errors="coerce")})
    if calendar["trade_date"].isna().any():
        raise Stage3BContractError("invalid A-share trade date")
    validate_development_dates(calendar, allow_warmup=True)
    calendar["a_share_close"] = (
        calendar["trade_date"].dt.tz_localize("Asia/Shanghai")
        + pd.Timedelta(hours=time(15, 0).hour)
    ).dt.tz_convert("UTC")

    values = observations.copy()
    values["available_at"] = pd.to_datetime(values["available_at"], errors="coerce", utc=True)
    values["observation_time"] = pd.to_datetime(
        values["observation_time"], errors="coerce", utc=True
    )
    if values[["available_at", "observation_time"]].isna().any().any():
        raise Stage3BContractError("unproven oil timestamp")
    if values["available_at"].duplicated().any():
        raise DuplicateKeyError("duplicate available_at in alignment input")
    values = values.sort_values("available_at", kind="mergesort")
    calendar = calendar.sort_values("a_share_close", kind="mergesort")
    aligned = pd.merge_asof(
        calendar,
        values,
        left_on="a_share_close",
        right_on="available_at",
        direction="backward",
        allow_exact_matches=True,
    )
    if aligned["value"].isna().any():
        raise Stage3BContractError("missing latest observable before A-share close")
    if (aligned["available_at"] > aligned["a_share_close"]).any():
        raise Stage3BContractError("future overseas observation aligned")
    return aligned.reset_index(drop=True)
