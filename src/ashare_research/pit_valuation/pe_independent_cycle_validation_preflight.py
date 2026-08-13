"""Independent cycle-context validation preflight (R4F.4A).

This module deliberately stops before outcome evaluation.  It may inspect
financial-state metadata, but never reads a future state's earnings value.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

ABOVE = "CURRENT_EPS_ABOVE_NORMALIZED_PROXY"
MATURED = "MATURED"
NOT_MATURED = "NOT_MATURED"


def add_fiscal_quarters(period_end: str, quarters: int) -> str:
    """Advance an exact fiscal quarter-end identity (4Q/8Q only)."""
    if quarters not in {4, 8}:
        raise ValueError("only the pre-registered 4Q and 8Q horizons are allowed")
    value = date.fromisoformat(period_end)
    return value.replace(year=value.year + quarters // 4).isoformat()


def _timeline_index(timeline: dict[str, Any]) -> dict[str, dict[str, Any]]:
    states = timeline.get("timelines", {}).get("PE_A_TTM", [])
    return {state["financial_state_id"]: state for state in states}


def _period_index(timeline: dict[str, Any]) -> dict[str, dict[str, Any]]:
    states = timeline.get("timelines", {}).get("PE_A_TTM", [])
    return {state["period_end"]: state for state in states if state.get("status") == "computed"}


def derive_episode_inventory(
    ledger: dict[str, Any],
    timeline: dict[str, Any],
    normalized_states: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Backward-compatible 3Y wrapper (output remains byte-identical)."""
    return derive_episode_inventory_for_window(
        "3y", "2023-07-31", ledger, timeline, normalized_states
    )


def derive_episode_inventory_for_window(
    window_id: str,
    window_start: str,
    ledger: dict[str, Any],
    timeline: dict[str, Any],
    normalized_states: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Derive contiguous above-normalized regimes using t-state data only.

    A regime already active on the first observed state is retained as a
    left-censored candidate episode.  It is never represented as an observed
    sign-transition onset.
    """
    if window_id not in {"3y", "5y"}:
        raise ValueError("window_id must be 3y or 5y")
    left_censored_key = f"left_censored_at_{window_id}_window_start"
    unknown_onset = f"UNKNOWN_OUTSIDE_{window_id.upper()}_WINDOW"
    state_by_id = _timeline_index(timeline)
    episodes: list[dict[str, Any]] = []
    active: dict[str, Any] | None = None
    previous_direction: str | None = None
    for segment in ledger["segments"]:
        is_above = segment["direction"] == ABOVE
        if is_above and active is None:
            left_censored = previous_direction is None
            raw_state = state_by_id[segment["raw_ttm_denominator_state_id"]]
            norm = normalized_states[segment["normalized_denominator_state_id"]]
            raw_fact_identities = []
            raw_roles = (
                ("current_cumulative", "current_cumulative_fact_id"),
                ("prior_year_same_period", "prior_year_same_period_fact_id"),
                ("prior_annual", "prior_annual_fact_id"),
            )
            for role, key in raw_roles:
                fact_id = raw_state.get(key)
                if fact_id:
                    raw_fact_identities.append(
                        {
                            "fact_id": fact_id,
                            "role": f"raw_ttm_{role}",
                            "period_end": None,
                            "available_at": raw_state.get("input_available_at", {}).get(role),
                            "effective_from": raw_state.get("input_effective_from", {}).get(role),
                        }
                    )
            anchor_fact_ids = list(
                dict.fromkeys(
                    norm["anchor_fact_ids"] + [item["fact_id"] for item in raw_fact_identities]
                )
            )
            anchor_identifiable = not left_censored
            active = {
                "candidate_regime_id": f"above-normalized-regime-{len(episodes) + 1:03d}",
                "episode_id": (
                    f"above-normalized-episode-{len(episodes) + 1:03d}"
                    if anchor_identifiable
                    else None
                ),
                "episode_semantics": "ABOVE_NORMALIZED_EARNINGS_EPISODE",
                "onset_rule": "FIRST_RAW_TTM_STATE_AFTER_EARNINGS_EXCESS_NONPOSITIVE_TO_POSITIVE",
                "onset_observed": not left_censored,
                left_censored_key: left_censored,
                "first_observed_trade_date": segment["start_trade_date"],
                "true_onset_trade_date": (
                    segment["start_trade_date"] if anchor_identifiable else unknown_onset
                ),
                "anchor_status": (
                    "IDENTIFIED_AT_OBSERVED_ONSET"
                    if anchor_identifiable
                    else "NOT_IDENTIFIABLE_LEFT_CENSORED"
                ),
                "left_censored_episode_anchor_policy": (
                    "PROHIBIT_FIRST_OBSERVED_DATE_SUBSTITUTION"
                ),
                "candidate_reference_raw_financial_state_id": segment[
                    "raw_ttm_denominator_state_id"
                ],
                "candidate_reference_raw_period_end": raw_state["period_end"],
                "anchor_trade_date": segment["start_trade_date"] if anchor_identifiable else None,
                "anchor_raw_financial_state_id": (
                    segment["raw_ttm_denominator_state_id"] if anchor_identifiable else None
                ),
                "anchor_normalized_denominator_state_id": (
                    segment["normalized_denominator_state_id"] if anchor_identifiable else None
                ),
                "anchor_raw_period_end": raw_state["period_end"] if anchor_identifiable else None,
                "anchor_current_ttm_eps": (
                    segment["current_ttm_eps_decimal"] if anchor_identifiable else None
                ),
                "anchor_normalized_eps": (
                    segment["normalized_eps_decimal"] if anchor_identifiable else None
                ),
                "anchor_current_bvps": norm["current_bvps_decimal"]
                if anchor_identifiable
                else None,
                "anchor_selected_roe_years": (
                    norm["selected_five_roe_years"] if anchor_identifiable else None
                ),
                "anchor_fact_ids": anchor_fact_ids if anchor_identifiable else None,
                "anchor_available_at_effective_identities": (
                    norm["anchor_available_at_effective_identities"] + raw_fact_identities
                    if anchor_identifiable
                    else None
                ),
                "raw_state_available_at": (
                    raw_state["available_at_max"] if anchor_identifiable else None
                ),
                "raw_state_effective_from": (
                    raw_state["effective_from"] if anchor_identifiable else None
                ),
                "raw_state_count": 0,
                "end_trade_date": segment["end_trade_date"],
                "future_references_present": False,
            }
            if anchor_identifiable and Decimal(active["anchor_current_ttm_eps"]) <= Decimal(
                active["anchor_normalized_eps"]
            ):
                raise ValueError("episode anchor must have positive earnings excess")
        if is_above and active is not None:
            active["raw_state_count"] += 1
            active["end_trade_date"] = segment["end_trade_date"]
        elif not is_above and active is not None:
            episodes.append(active)
            active = None
        previous_direction = segment["direction"]
    if active is not None:
        episodes.append(active)
    payload = {
        "schema": (
            "petrochina_pe_independent_cycle_episode_inventory_v1"
            if window_id == "3y"
            else "petrochina_pe_independent_cycle_episode_inventory_5y_v1"
        ),
        "symbol": "601857.SH",
        "validation_unit": "INDEPENDENT_EPISODE_ONSET",
        "episode_semantics": "INDEPENDENT_CONTIGUOUS_ABOVE_NORMALIZED_REGIME",
        "daily_rows_are_independent_episodes": False,
        "candidate_contiguous_regimes": len(episodes),
        "episode_count": len(episodes),
        "observed_onset_count": sum(e["onset_observed"] for e in episodes),
        "observed_onsets": sum(e["onset_observed"] for e in episodes),
        "observed_episode_onsets": sum(e["onset_observed"] for e in episodes),
        "left_censored_episode_count": sum(e[left_censored_key] for e in episodes),
        "left_censored_regimes": sum(e[left_censored_key] for e in episodes),
        "valid_onset_anchored_episodes": sum(
            e["anchor_status"] == "IDENTIFIED_AT_OBSERVED_ONSET" for e in episodes
        ),
        "first_observed_trade_date": (
            episodes[0]["first_observed_trade_date"] if len(episodes) == 1 else None
        ),
        "true_onset_trade_date": (
            episodes[0]["true_onset_trade_date"] if len(episodes) == 1 else None
        ),
        "left_censored_episode_anchor_policy": ("PROHIBIT_FIRST_OBSERVED_DATE_SUBSTITUTION"),
        "no_pe_value_used": True,
        "no_future_fact_used": True,
        "anchor_ledger_separate_from_outcomes": True,
        "candidate_regimes": episodes,
        "episodes": episodes,
    }
    if window_id == "5y":
        payload["window_id"] = "5y"
        payload["window_start"] = window_start
    return payload


def build_outcome_readiness(inventory: dict[str, Any], timeline: dict[str, Any]) -> dict[str, Any]:
    """Backward-compatible 3Y wrapper (output remains byte-identical)."""
    return build_outcome_readiness_for_window("3y", inventory, timeline)


def build_outcome_readiness_for_window(
    window_id: str, inventory: dict[str, Any], timeline: dict[str, Any]
) -> dict[str, Any]:
    """Resolve only target-state metadata; future value fields are never read."""
    if window_id not in {"3y", "5y"}:
        raise ValueError("window_id must be 3y or 5y")
    by_period = _period_index(timeline)
    latest = max(by_period) if by_period else None
    rows: list[dict[str, Any]] = []
    missing: list[str] = []
    for episode in inventory["candidate_regimes"]:
        row: dict[str, Any] = {
            "candidate_regime_id": episode["candidate_regime_id"],
            "episode_id": episode["episode_id"],
            "anchor_status": episode["anchor_status"],
            "metadata_reference_policy": (
                "CANDIDATE_FIRST_OBSERVED_REFERENCE_METADATA_ONLY"
                if episode["anchor_status"] == "NOT_IDENTIFIABLE_LEFT_CENSORED"
                else "TRUE_ONSET_ANCHOR"
            ),
            "horizons": {},
        }
        for quarters, label in ((4, "4q"), (8, "8q")):
            reference_period_end = (
                episode["anchor_raw_period_end"] or episode["candidate_reference_raw_period_end"]
            )
            target = add_fiscal_quarters(reference_period_end, quarters)
            state = by_period.get(target)
            if state is None:
                missing.append(target)
                resolved = {
                    "target_period_end": target,
                    "metadata_status": NOT_MATURED,
                    "protocol_valid_maturity": False,
                    "future_financial_state_id": None,
                    "period_end": None,
                    "available_at": None,
                    "effective_from": None,
                }
            else:
                resolved = {
                    "target_period_end": target,
                    "metadata_status": MATURED,
                    "protocol_valid_maturity": (
                        episode["anchor_status"] == "IDENTIFIED_AT_OBSERVED_ONSET"
                    ),
                    "future_financial_state_id": state["financial_state_id"],
                    "period_end": state["period_end"],
                    "available_at": state["available_at_max"],
                    "effective_from": state["effective_from"],
                    "constituent_fact_ids": state["input_fact_ids"],
                }
            row["horizons"][label] = resolved
        rows.append(row)
    metadata4 = sum(r["horizons"]["4q"]["metadata_status"] == MATURED for r in rows)
    metadata8 = sum(r["horizons"]["8q"]["metadata_status"] == MATURED for r in rows)
    valid4 = sum(r["horizons"]["4q"]["protocol_valid_maturity"] for r in rows)
    valid8 = sum(r["horizons"]["8q"]["protocol_valid_maturity"] for r in rows)
    payload = {
        "schema": (
            "petrochina_pe_independent_cycle_outcome_readiness_v1"
            if window_id == "3y"
            else "petrochina_pe_independent_cycle_outcome_readiness_5y_v1"
        ),
        "symbol": "601857.SH",
        "read_mode": "METADATA_ONLY_READINESS",
        "permitted_fields": [
            "financial_state_id",
            "period_end",
            "available_at",
            "effective_from",
            "input_fact_ids",
            "existence",
            "maturity",
        ],
        "forbidden_fields": ["value_decimal", "per_share_denominator_decimal", "future_eps"],
        "future_eps_values_read": False,
        "partial_quarter_proxy": False,
        "forecast_fallback": False,
        "3y_candidate_regime_count": inventory["candidate_contiguous_regimes"],
        "3y_valid_onset_anchored_episode_count": inventory["valid_onset_anchored_episodes"],
        "candidate_regimes_with_4q_target_metadata_available": metadata4,
        "candidate_regimes_with_8q_target_metadata_available": metadata8,
        "protocol_valid_mature_4q_episode_count": valid4,
        "protocol_valid_mature_8q_episode_count": valid8,
        "current_3y_validation_executable": valid4 >= 2,
        "current_3y_validation_block_reason": (
            None if valid4 >= 2 else "NO_OBSERVED_EPISODE_ONSET_LEFT_CENSORED"
        ),
        "current_3y_validation_reason": (
            None if valid4 >= 2 else "LEFT_CENSORED_EPISODE_ONSET_NOT_OBSERVED"
        ),
        "5y_historical_extension_needed": valid4 < 2,
        "existing_financial_state_target_coverage": rows,
        "earliest_missing_target_period": min(missing) if missing else None,
        "latest_available_target_period": latest,
    }
    if window_id == "5y":
        for key in (
            "3y_candidate_regime_count",
            "3y_valid_onset_anchored_episode_count",
            "current_3y_validation_executable",
            "current_3y_validation_block_reason",
            "current_3y_validation_reason",
            "5y_historical_extension_needed",
        ):
            payload.pop(key, None)
        payload.update(
            {
                "5y_candidate_regime_count": inventory["candidate_contiguous_regimes"],
                "valid_onset_anchored_episode_count": inventory["valid_onset_anchored_episodes"],
                "current_5y_validation_executable": valid4 >= 2,
                "primary_4q_execution_gate": (
                    "INDEPENDENT_OUTCOME_VALIDATION_EXECUTION_READY"
                    if valid4 >= 2
                    else "INDEPENDENT_VALIDATION_NOT_TESTABLE_WITH_FROZEN_5Y_HISTORY"
                ),
                "8q_robustness_readiness": ("READY" if valid8 >= 2 else "8Q_ROBUSTNESS_PARTIAL"),
            }
        )
    return payload


def derive_5y_justification(inventory: dict[str, Any], readiness: dict[str, Any]) -> dict[str, Any]:
    needed = readiness["protocol_valid_mature_4q_episode_count"] < 2
    return {
        "schema": "petrochina_pe_5y_backfill_identification_justification_v1",
        "remaining_logical_gaps": 4,
        "remaining_logical_facts": [
            {"period_end": "2015-12-31", "concept": "parent_equity"},
            {"period_end": "2016-12-31", "concept": "parent_equity"},
            {"period_end": "2016-12-31", "concept": "parent_net_profit"},
            {"period_end": "2017-12-31", "concept": "parent_net_profit"},
        ],
        "prior_status": "DEFERRED_PENDING_IDENTIFICATION_REVIEW",
        "status": (
            "ACQUISITION_JUSTIFIED_FOR_INDEPENDENT_VALIDATION" if needed else "STILL_DEFERRED"
        ),
        "primary_justification": (
            "RECOVER_LEFT_CENSORED_EPISODE_ONSET_IF_PRESENT_WITHIN_5Y_WINDOW"
            if needed
            else "NOT_REQUIRED"
        ),
        "primary_justification_short": "RECOVER_LEFT_CENSORED_EPISODE_ONSET",
        "secondary_justification": (
            "EXPAND_OPPORTUNITY_FOR_ADDITIONAL_INDEPENDENT_EPISODES" if needed else "NOT_REQUIRED"
        ),
        "secondary_justification_short": "EXPAND_INDEPENDENT_EPISODE_HISTORY",
        "three_year_candidate_regime_count": inventory["candidate_contiguous_regimes"],
        "three_year_valid_onset_anchored_episode_count": inventory["valid_onset_anchored_episodes"],
        "three_year_left_censored_episode_count": inventory["left_censored_episode_count"],
        "backfill_guarantees": {
            "true_onset_recovery": False,
            "at_least_two_independent_episodes": False,
            "executable_validation": False,
            "favorable_outcome": False,
        },
        "permitted_post_backfill_results": [
            "TRUE_ONSET_RECOVERED_AND_ADDITIONAL_EPISODES",
            "TRUE_ONSET_RECOVERED_BUT_ONLY_ONE_EPISODE",
            "REGIME_STILL_LEFT_CENSORED_AT_5Y_START",
            "NO_ADDITIONAL_EPISODES",
        ],
        "frozen_history_limit": "5Y",
        "automatic_extension_beyond_5y": "PROHIBITED",
        "stop_expansion_result_if_valid_episodes_lt_2": (
            "INDEPENDENT_VALIDATION_NOT_TESTABLE_WITH_FROZEN_5Y_HISTORY"
        ),
        "stop_expansion_action": "STOP_FOR_NORTH_STAR_REVIEW",
        "longer_history_requires": "NEW_NORTH_STAR_METHOD_VALUE_REVIEW",
        "acquisition_performed": False,
        "percentile_rationale_used": False,
        "next_stage_only": (
            "R4F.4A1_REMAINING_5Y_ANNUAL_FACT_BACKFILL_FOR_INDEPENDENT_CYCLE_VALIDATION"
        ),
    }


def assert_preflight_has_no_future_values(payload: Any) -> None:
    """Fail closed if a preflight artifact contains a future outcome amount."""
    forbidden = {
        "future_eps",
        "future_eps_decimal",
        "future_realized_ttm_eps",
        "value_decimal",
        "per_share_denominator_decimal",
    }
    if isinstance(payload, dict):
        overlap = forbidden.intersection(payload)
        if overlap:
            raise ValueError(f"future outcome value field forbidden: {sorted(overlap)}")
        for value in payload.values():
            assert_preflight_has_no_future_values(value)
    elif isinstance(payload, list):
        for value in payload:
            assert_preflight_has_no_future_values(value)
