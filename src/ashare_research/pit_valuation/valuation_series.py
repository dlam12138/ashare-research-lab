"""M2 Stage 2K.1R4E — candidate PE/PB/PS valuation series.

Joins the A-share close (exact ``trade_date`` match) to the PIT-visible
financial state (backward ``effective_from <= trade_date``), computes the
candidate per-share-denominator and ratio in ``Decimal``, and builds a
deterministic observation identity.  The output is non-production and never
computes a valuation percentile.
"""

from __future__ import annotations

import hashlib
from decimal import Decimal
from pathlib import Path
from typing import Any

from ashare_research.pit_valuation.series_contract import (
    CONSTANT_TOTAL_SHARES,
    METRIC_PB,
    METRIC_PE,
    METRIC_PS,
    STATUS_BLOCKED_MARKET_CACHE,
    STATUS_COMPUTED,
    STATUS_MISSING_FINANCIAL_STATE,
    STATUS_MISSING_TTM_INPUT,
    STATUS_NONPOSITIVE_EARNINGS,
    STATUS_NONPOSITIVE_EQUITY,
    STATUS_NONPOSITIVE_PE_SHARES,
    STATUS_NONPOSITIVE_REVENUE,
    STATUS_NONPOSITIVE_WA_SHARES,
    STATUS_UNMATCHED_EQUITY_SHARE,
    STATUS_ZERO_DENOMINATOR,
    SYMBOL,
    canonical_digest,
    parse_decimal,
)
from ashare_research.pit_valuation.temporal_join import python_backward_join

OBSERVATION_SCHEMA = "petrochina_pit_valuation_series_observation_v1"
OBSERVATION_VERSION = "1.0"


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_primary_market_cache(
    cache_root: Path,
    registry: dict[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Load the baostock primary market frame and probe the akshare secondary.

    The baostock object is content-addressed and verified against the registry.
    The akshare secondary object is probed; when absent the market
    reconciliation is recorded as ``BLOCKED_EXTERNAL_MARKET_CACHE_UNAVAILABLE``
    (never network-refreshed, never switched provider).
    """
    import pandas as pd

    providers = {p["provider"]: p for p in registry["providers"]}
    primary = providers["baostock"]
    secondary = providers["akshare"]

    primary_path = (cache_root / primary["object_key"]).resolve()
    if not primary_path.is_file():
        raise FileNotFoundError(
            f"missing primary market cache: {primary['object_key']}"
        )
    actual = _sha256_bytes(primary_path.read_bytes())
    if actual != primary["sha256"]:
        raise ValueError(f"primary market cache sha mismatch: {actual[:12]}...")

    df = pd.read_parquet(primary_path)
    rows = [
        {"trade_date": str(r["trade_date"]), "close": float(r["close"])}
        for _, r in df.iterrows()
        if str(r["symbol"]) == SYMBOL and bool(r.get("is_trading", True))
    ]
    rows.sort(key=lambda r: r["trade_date"])

    secondary_path = (cache_root / secondary["object_key"]).resolve()
    secondary_present = secondary_path.is_file()
    secondary_verified = False
    if secondary_present:
        secondary_verified = (
            _sha256_bytes(secondary_path.read_bytes()) == secondary["sha256"]
        )

    reconciliation_status = (
        "pass"
        if secondary_present and secondary_verified
        else STATUS_BLOCKED_MARKET_CACHE
    )
    meta = {
        "primary_provider": "baostock",
        "primary_object_sha256": primary["sha256"],
        "primary_object_key": primary["object_key"],
        "primary_row_count": primary["row_count"],
        "secondary_provider": "akshare",
        "secondary_object_sha256": secondary["sha256"],
        "secondary_object_key": secondary["object_key"],
        "secondary_present": secondary_present,
        "secondary_verified": secondary_verified,
        "reconciliation_status": reconciliation_status,
        "reconciliation_contract_digest": canonical_digest(
            {
                "common_trade_days": registry.get("common_trade_days"),
                "close_max_abs_difference": registry.get("close_max_abs_difference"),
                "close_differences_within_0_01": registry.get("close_differences_within_0_01"),
                "reconciliation_status": registry.get("reconciliation_status"),
            }
        ),
        "market_rows": len(rows),
        "first_trade_date": rows[0]["trade_date"] if rows else "",
        "last_trade_date": rows[-1]["trade_date"] if rows else "",
    }
    return rows, meta


def _close_digest(close: Decimal) -> str:
    return canonical_digest({"close": str(close)})


def _compute_observation(
    *,
    metric_id: str,
    trade_date: str,
    close: Decimal,
    market_meta: dict[str, Any],
    state: dict[str, Any] | None,
) -> dict[str, Any]:
    """Compute one observation's ratio/status and assembled payload."""
    formula_id = {
        METRIC_PE: "pe-a-ttm-v1",
        METRIC_PB: "pb-a-mrq-v1",
        METRIC_PS: "ps-a-ttm-v1",
    }[metric_id]

    if state is None:
        status = STATUS_MISSING_FINANCIAL_STATE
        per_share_denominator: Decimal | None = None
        ratio: Decimal | None = None
        exclusion_reason = "no financial state visible at trade date"
    elif state.get("status") == STATUS_MISSING_TTM_INPUT:
        status = STATUS_MISSING_TTM_INPUT
        per_share_denominator = None
        ratio = None
        exclusion_reason = "missing prior-year TTM input"
    else:
        ratio, status, per_share_denominator, exclusion_reason = _compute_ratio(
            metric_id, close, state
        )

    # Audit operands: the financial numerator and the share basis used for the
    # per-share denominator, so a human can recompute the ratio independently.
    numerator = None if state is None else state.get("value_decimal")
    share_basis = None
    if state is not None:
        if metric_id == METRIC_PB:
            share_basis = state.get("period_end_shares_decimal")
        else:
            share_basis = state.get("share_basis_decimal")

    close_decimal_str = str(close)
    close_digest = _close_digest(close)
    payload = {
        "schema": OBSERVATION_SCHEMA,
        "version": OBSERVATION_VERSION,
        "metric_id": metric_id,
        "symbol": SYMBOL,
        "trade_date": trade_date,
        "market_close_decimal": close_decimal_str,
        "market_close_digest": close_digest,
        "primary_market_object_sha256": market_meta["primary_object_sha256"],
        "secondary_market_object_sha256": market_meta["secondary_object_sha256"],
        "market_reconciliation_digest": market_meta["market_reconciliation_digest"],
        "market_reconciliation_status": market_meta["reconciliation_status"],
        "financial_state_id": state.get("financial_state_id", "") if state else "",
        "financial_state_effective_from": state.get("effective_from", "") if state else "",
        "financial_state_available_at_max": state.get("available_at_max", "") if state else "",
        "financial_state_value_decimal": numerator,
        "share_basis_decimal": share_basis,
        "input_fact_ids": state.get("input_fact_ids", []) if state else [],
        "share_continuity_proof_id": state.get("share_continuity_proof_id", "") if state else "",
        "formula_id": formula_id,
        "formula_version": 1,
        "per_share_denominator_decimal": (
            None if per_share_denominator is None else str(per_share_denominator)
        ),
        "ratio_decimal": None if ratio is None else str(ratio),
        "status": status,
        "exclusion_reason": exclusion_reason,
        "non_production": True,
        "percentile_computed": False,
        "score_eligible": False,
        "production_eligible": False,
    }
    payload["observation_id"] = canonical_digest(payload)
    return payload


def _compute_ratio(
    metric_id: str,
    close: Decimal,
    state: dict[str, Any],
) -> tuple[Decimal | None, str, Decimal | None, str]:
    """Compute the ratio and per-share denominator for one metric."""
    value = None if state.get("value_decimal") is None else Decimal(state["value_decimal"])
    if metric_id == METRIC_PE:
        if value is None:
            return None, STATUS_MISSING_TTM_INPUT, None, "missing TTM input"
        if value <= 0:
            return None, STATUS_NONPOSITIVE_EARNINGS, None, "TTM parent net profit <= 0"
        if CONSTANT_TOTAL_SHARES <= 0:
            return (
                None,
                STATUS_NONPOSITIVE_WA_SHARES,
                None,
                "weighted-average shares <= 0",
            )
        denom = value / CONSTANT_TOTAL_SHARES
        if denom == 0:
            return None, STATUS_ZERO_DENOMINATOR, None, "zero per-share denominator"
        return close / denom, STATUS_COMPUTED, denom, ""

    if metric_id == METRIC_PB:
        if value is None:
            return None, STATUS_UNMATCHED_EQUITY_SHARE, None, "missing equity value"
        if value <= 0:
            return None, STATUS_NONPOSITIVE_EQUITY, None, "parent equity <= 0"
        shares_raw = state.get("period_end_shares_decimal")
        if not shares_raw:
            return (
                None,
                STATUS_UNMATCHED_EQUITY_SHARE,
                None,
                "no matching period-end shares context",
            )
        shares = Decimal(shares_raw)
        if shares <= 0:
            return None, STATUS_NONPOSITIVE_PE_SHARES, None, "period-end shares <= 0"
        denom = value / shares
        if denom == 0:
            return None, STATUS_ZERO_DENOMINATOR, None, "zero per-share denominator"
        return close / denom, STATUS_COMPUTED, denom, ""

    # PS_A_TTM
    if value is None:
        return None, STATUS_MISSING_TTM_INPUT, None, "missing TTM input"
    if value <= 0:
        return None, STATUS_NONPOSITIVE_REVENUE, None, "TTM revenue <= 0"
    if CONSTANT_TOTAL_SHARES <= 0:
        return None, STATUS_NONPOSITIVE_PE_SHARES, None, "shares <= 0"
    denom = value / CONSTANT_TOTAL_SHARES
    if denom == 0:
        return None, STATUS_ZERO_DENOMINATOR, None, "zero per-share denominator"
    return close / denom, STATUS_COMPUTED, denom, ""


def build_valuation_series(
    market_rows: list[dict[str, Any]],
    market_meta: dict[str, Any],
    timelines: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    """Build the candidate PE/PB/PS observations for every market trade date."""
    if not market_rows:
        raise ValueError("empty market frame")
    observations: list[dict[str, Any]] = []
    for metric_id in (METRIC_PE, METRIC_PB, METRIC_PS):
        joined = python_backward_join(market_rows, timelines[metric_id])
        for row in sorted(market_rows, key=lambda r: r["trade_date"]):
            trade_date = row["trade_date"]
            close = parse_decimal(row["close"])
            state = joined.get(trade_date)
            observations.append(
                _compute_observation(
                    metric_id=metric_id,
                    trade_date=trade_date,
                    close=close,
                    market_meta=market_meta,
                    state=state,
                )
            )
    observations.sort(key=lambda o: (o["metric_id"], o["trade_date"]))
    return {
        "schema": "petrochina_pit_valuation_series_candidate_v1",
        "version": "1.0",
        "symbol": SYMBOL,
        "non_production": True,
        "percentile_computed": False,
        "market_rows": len(market_rows),
        "observation_count": len(observations),
        "market_meta": market_meta,
        "observations": observations,
    }
