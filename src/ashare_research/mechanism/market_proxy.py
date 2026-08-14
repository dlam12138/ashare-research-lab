"""PIT-safe ex-target Shanghai market proxy construction."""

from __future__ import annotations

import pandas as pd

from ashare_research.exceptions import DuplicateKeyError
from ashare_research.mechanism.contracts import Stage3BContractError, validate_development_dates

TARGET_SYMBOL = "601857.SH"
REQUIRED_UNIVERSE_COLUMNS = {
    "trade_date",
    "symbol",
    "eligible",
    "eligibility_reason",
    "shares",
    "price",
    "reference_price",
    "membership_is_pit",
    "shares_are_pit",
    "corporate_action_verified",
    "methodology_regime",
    "universe_basis",
    "source_ref",
}


def _expected_regime(trade_dates: pd.Series) -> pd.Series:
    boundary = pd.Timestamp("2020-07-22")
    return pd.Series(
        [
            "SSE_COMPOSITE_PRE_20200722" if value < boundary else "SSE_COMPOSITE_FROM_20200722"
            for value in trade_dates
        ],
        index=trade_dates.index,
    )


def build_market_ex_target_proxy(
    universe: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Build daily simple price returns using verified start-of-day market-cap weights.

    ``reference_price`` is the official event-neutral price reference for the return interval.
    This makes corporate-action/divisor handling explicit rather than inferring it from close data.
    """
    missing = sorted(REQUIRED_UNIVERSE_COLUMNS - set(universe.columns))
    if missing:
        raise Stage3BContractError(f"primary proxy input missing columns: {missing}")
    frame = universe.copy()
    frame["trade_date"] = pd.to_datetime(validate_development_dates(frame, allow_warmup=True))
    if frame.duplicated(["trade_date", "symbol"]).any():
        raise DuplicateKeyError("duplicate primary proxy symbol/date")
    forbidden_bases = {"CURRENT_CONSTITUENTS", "SURVIVORSHIP_ONLY", "FUTURE_BACKFILL"}
    used_bases = set(frame["universe_basis"].dropna().astype(str))
    if used_bases.intersection(forbidden_bases):
        raise Stage3BContractError("non-PIT or survivorship-only universe rejected")

    eligible = frame.loc[frame["eligible"].astype(bool)].copy()
    if eligible.empty:
        raise Stage3BContractError("missing eligible primary proxy input")
    for flag in ["membership_is_pit", "shares_are_pit", "corporate_action_verified"]:
        if not eligible[flag].astype(bool).all():
            raise Stage3BContractError(f"unverified Tier-1 input: {flag}")
    expected = _expected_regime(eligible["trade_date"])
    if not eligible["methodology_regime"].astype(str).eq(expected).all():
        raise Stage3BContractError("historical methodology regime mismatch")

    for column in ["shares", "price", "reference_price"]:
        eligible[column] = pd.to_numeric(eligible[column], errors="coerce")
    if eligible[["shares", "price", "reference_price"]].isna().any().any():
        raise Stage3BContractError("invalid market proxy numeric input")
    if (eligible[["shares", "price", "reference_price"]] <= 0).any().any():
        raise Stage3BContractError("non-positive market proxy numeric input")

    eligible["target_excluded"] = eligible["symbol"].eq(TARGET_SYMBOL)
    calculation = eligible.loc[~eligible["target_excluded"]].copy()
    if calculation.empty or calculation["symbol"].eq(TARGET_SYMBOL).any():
        raise Stage3BContractError("target exclusion failed")
    calculation["market_cap"] = calculation["reference_price"] * calculation["shares"]
    calculation["security_return"] = (
        calculation["price"] / calculation["reference_price"] - 1.0
    )
    calculation["weighted_change"] = (
        calculation["market_cap"] * calculation["security_return"]
    )
    grouped = calculation.groupby("trade_date", sort=True, observed=True)
    denominator = grouped["market_cap"].sum()
    if (denominator <= 0).any():
        raise Stage3BContractError("zero primary proxy denominator")
    daily_return = grouped["weighted_change"].sum() / denominator
    proxy = pd.DataFrame(
        {
            "dataset_id": "market_ex_target",
            "instrument_id": "SH_MARKET_EX_601857",
            "trade_date": daily_return.index,
            "return": daily_return.to_numpy(),
            "constituent_count": grouped.size().to_numpy(),
            "quality_status": "NORMALIZED_PIT_VERIFIED",
            "schema_version": "1.0.0",
        }
    )
    proxy["value"] = (1.0 + proxy["return"]).cumprod() * 100.0

    audit_columns = [
        "trade_date",
        "symbol",
        "eligible",
        "eligibility_reason",
        "shares",
        "price",
        "target_excluded",
        "source_ref",
    ]
    return proxy, eligible.loc[:, audit_columns].sort_values(
        ["trade_date", "symbol"], kind="mergesort"
    ).reset_index(drop=True)
