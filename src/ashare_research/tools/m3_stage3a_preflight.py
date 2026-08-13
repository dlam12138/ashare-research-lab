"""Deterministic, offline builder for the M3 Stage 3A research contracts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
FROZEN_CUTOFF = "2026-08-13"
ARTIFACTS = {
    "hypothesis": "m3_stage3a_mechanism_hypothesis_contract_v1.json",
    "data": "m3_stage3a_data_requirements_v1.json",
    "protocol": "m3_stage3a_statistical_protocol_v1.json",
    "decision": "m3_stage3a_preflight_decision_v1.json",
}


def canonical_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=1, sort_keys=True) + "\n"


def build_hypothesis() -> dict[str, Any]:
    return {
        "schema_version": "1.0.0",
        "stage": "M3_STAGE3A",
        "research_mode": "PRE_REGISTERED_DAILY_MECHANISM_RESEARCH",
        "canonical_question": (
            "From 2015-01-01 through the frozen research cutoff, when the Shanghai "
            "market return excluding PetroChina reaches the pre-registered crash "
            "threshold, does 601857.SH exhibit significantly positive abnormal return "
            "after controlling for oil, the petrochemical industry, and principal "
            "market-style alternatives, and what is its estimated offset of that day's "
            "ex-target Shanghai-market decline?"
        ),
        "prohibited_question": "Is PetroChina used to support the market?",
        "interpretation_boundary": {
            "statistical_relationship_only": True,
            "funding_actor_intent_inference_authorized": False,
            "public_daily_data_can_identify_actor_intent": False,
        },
        "target": {"symbol": "601857.SH", "name": "PetroChina"},
        "frequency": "1d",
        "requested_sample": {"start": "2015-01-01", "end": FROZEN_CUTOFF},
        "market_condition": {
            "proxy": "SH_MARKET_EX_601857",
            "operator": "<=",
            "primary_threshold": -0.01,
            "robustness_thresholds": [-0.005, -0.015, -0.02],
            "ex_post_threshold_tuning_allowed": False,
        },
        "primary_hypothesis": {
            "h0": "Crash-day abnormal return is not systematically positive.",
            "h1": "Crash-day abnormal return is positive.",
            "direction": "GREATER_THAN_ZERO",
            "outcome": "abnormal_return",
            "raw_positive_return_is_primary_evidence": False,
        },
        "outcomes": {
            "primary": {
                "id": "abnormal_return",
                "formula": "R_601857_t - E[R_601857_t | pre_registered_controls]",
            },
            "secondary": [
                {"id": "raw_return", "role": "DESCRIPTIVE"},
                {"id": "positive_return_indicator", "role": "DESCRIPTIVE_ONLY"},
                {"id": "market_relative_return", "role": "SECONDARY"},
                {"id": "estimated_index_offset", "role": "SEPARATE_ESTIMATION_PIPELINE"},
            ],
        },
        "falsification": [
            "primary abnormal return is not positive",
            "direction is unstable across pre-registered samples or thresholds",
            "effect is explained by required controls",
            "effect is driven by one or a few extreme dates",
        ],
    }


def build_data_requirements() -> dict[str, Any]:
    return {
        "schema_version": "1.0.0",
        "stage": "M3_STAGE3A",
        "inventory_method": "OFFLINE_INTERFACE_AND_SCHEMA_RECONNAISSANCE_ONLY",
        "network_calls_performed": False,
        "real_data_acquired": False,
        "primary_market_proxy": {
            "id": "SH_MARKET_EX_601857",
            "required_construction": (
                "Point-in-time Shanghai-listed equity return aggregate excluding 601857.SH"
            ),
            "constituent_history": "DATA_ACQUISITION_REQUIRED",
            "historical_weight_history": "DATA_ACQUISITION_REQUIRED",
            "exact_reproducibility": "DATA_ACQUISITION_REQUIRED",
            "fallback_to_sse_composite_allowed": False,
        },
        "secondary_market_proxies": [
            "SH_EQUAL_WEIGHT",
            "A_SHARE_EQUAL_WEIGHT",
            "A_SHARE_MEDIAN_RETURN",
            "ADVANCING_STOCK_RATIO",
            "CSI300",
            "SSE50",
        ],
        "requirements": [
            {
                "id": "target_daily",
                "tier": 1,
                "status": "AVAILABLE",
                "interface": "BaseProvider.get_stock_daily",
            },
            {
                "id": "trade_calendar",
                "tier": 1,
                "status": "AVAILABLE",
                "interface": "BaseProvider.get_trade_calendar",
            },
            {"id": "market_ex_target", "tier": 1, "status": "DATA_ACQUISITION_REQUIRED"},
            {"id": "oil", "tier": 1, "status": "DATA_ACQUISITION_REQUIRED"},
            {"id": "petrochemical_industry", "tier": 1, "status": "DATA_ACQUISITION_REQUIRED"},
            {"id": "dividend_style", "tier": 2, "status": "PROXY_REQUIRED"},
            {"id": "central_soe_style", "tier": 2, "status": "PROXY_REQUIRED"},
            {"id": "large_cap_style", "tier": 2, "status": "ACQUIRABLE"},
            {"id": "usd_cny", "tier": 3, "status": "DATA_ACQUISITION_REQUIRED"},
            {"id": "market_turnover", "tier": 3, "status": "ACQUIRABLE"},
            {"id": "volatility", "tier": 3, "status": "PROXY_REQUIRED"},
            {"id": "small_large_spread", "tier": 3, "status": "PROXY_REQUIRED"},
            {
                "id": "historical_target_index_weight",
                "tier": "CONTRIBUTION",
                "status": "DATA_ACQUISITION_REQUIRED",
            },
        ],
        "oil_point_in_time_policy": {
            "primary": "LATEST_OBSERVABLE_BEFORE_A_SHARE_CLOSE",
            "fallback": "OIL_RETURN_T_MINUS_1",
            "same_day_overseas_close_allowed": False,
            "choice_must_be_frozen_before_results": True,
        },
        "sample_availability_policy": {
            "requested_start": "2015-01-01",
            "requested_end": FROZEN_CUTOFF,
            "effective_primary_start": "MAX_TRUSTWORTHY_START_OF_REQUIRED_PRIMARY_INPUTS",
            "pre_effective_period": "DESCRIPTIVE_ONLY",
            "forward_fill_missing_history_allowed": False,
        },
        "stage3b_required": True,
    }


def build_protocol() -> dict[str, Any]:
    return {
        "schema_version": "1.0.0",
        "stage": "M3_STAGE3A",
        "real_data_execution_authorized": False,
        "analysis_layers": {
            "A_descriptive": [
                "full_sample_correlation", "rolling_60d_correlation", "down_day_return",
                "crash_day_return", "mean", "median", "positive_probability",
                "volume_abnormality", "year_by_year", "market_regimes",
            ],
            "B_conditional": [
                "crash_vs_ordinary_mean_difference", "median_difference",
                "confidence_interval", "effect_size",
            ],
            "C_base_regression": {
                "formula": (
                    "R_601857_t = alpha + beta_market*R_market_ex_target_t + "
                    "beta_oil*R_oil_t + beta_industry*R_industry_t + gamma*Crash_t + epsilon_t"
                ),
                "primary_parameter": "gamma",
            },
            "D_robustness": [
                "threshold_changes", "alternative_market_proxies", "year_splits",
                "leave_extreme_days_out", "moving_block_bootstrap",
                "multiple_testing_correction", "out_of_sample",
            ],
        },
        "controls": {
            "tier_1_required": ["market_ex_target", "oil", "petrochemical_industry"],
            "tier_2_main_alternatives": ["dividend_style", "central_soe_style", "large_cap_style"],
            "tier_3_robustness_only": [
                "usd_cny", "market_turnover", "volatility", "small_large_spread"
            ],
        },
        "bootstrap": {
            "method": "MOVING_BLOCK_BOOTSTRAP",
            "iid_is_primary": False,
            "block_length_rule": "ROUND_N_TO_ONE_THIRD_CAPPED_AT_20_TRADING_DAYS",
            "seed": 20260813,
            "replications": 5000,
            "ci_method": "PERCENTILE_TWO_SIDED_95",
            "change_after_results_allowed": False,
        },
        "multiple_testing": {
            "primary_inference_count": 1,
            "primary_correction": "NONE_PRE_REGISTERED_SINGLE_ENDPOINT",
            "robustness_family_correction": "BENJAMINI_HOCHBERG_FDR",
            "fdr_q": 0.05,
        },
        "out_of_sample": {
            "development": {"start": "2015-01-01", "end": "2022-12-31"},
            "holdout": {"start": "2023-01-01", "end": FROZEN_CUTOFF},
            "holdout_status": "SEALED",
            "unseal_preconditions": ["PIPELINE_LOCKED", "MODEL_DIGEST_LOCKED"],
            "holdout_read_performed": False,
        },
        "extreme_date_robustness": {
            "leave_one_event_out": True,
            "remove_top_absolute_abnormal_returns": [1, 3],
            "winsorization_role": "DESCRIPTIVE_ROBUSTNESS_ONLY",
            "winsorization_primary_allowed": False,
        },
        "index_contribution": {
            "formula": "historical_estimated_weight_t * R_601857_t",
            "offset_ratio_formula": (
                "max(estimated_index_contribution_t, 0) / abs(ex_target_market_decline_t)"
            ),
            "separate_from_abnormal_return": True,
            "official_point_attribution_claim_allowed": False,
            "label_when_weight_not_exact": "ESTIMATED_CONTRIBUTION",
        },
        "evidence_levels": {
            "1": "NO_STABLE_RELATIONSHIP",
            "2": "SURFACE_ASSOCIATION",
            "3": "ABNORMAL_PERFORMANCE_AFTER_MAIN_CONTROLS",
            "4": "STABLE_TIMING_AND_ABNORMAL_TRADING",
            "5": "FUNDING_ACTOR_EVIDENCE",
        },
        "daily_mvp_max_authorized_level": 3,
        "minute_data_required_for_level_4": True,
    }


def build_decision() -> dict[str, Any]:
    return {
        "schema_version": "1.0.0",
        "stage": "M3_STAGE3A",
        "verdict": "PASS",
        "decision": "M3_MECHANISM_RESEARCH_CONTRACT_FROZEN",
        "next_stage": "M3_STAGE3B_DATA_ACQUISITION_AND_NORMALIZATION_ALLOWED",
        "stage3b_started": False,
        "m3_implementation_complete": False,
        "petrochina_abnormal_support_behavior_confirmed": False,
        "real_hypothesis_result_produced": False,
        "real_data_acquisition_performed": False,
        "regression_performed": False,
        "holdout_read_performed": False,
        "primary_proxy_status": "DATA_ACQUISITION_REQUIRED",
        "daily_mvp_max_authorized_evidence_level": 3,
        "prohibited_claims": [
            "PETROCHINA_STABILIZES_THE_MARKET",
            "STATE_OR_FUNDING_ACTOR_INTENT_IDENTIFIED",
            "OFFICIAL_INDEX_POINT_ATTRIBUTION",
        ],
    }


def build_all() -> dict[str, str]:
    payloads = {
        ARTIFACTS["hypothesis"]: build_hypothesis(),
        ARTIFACTS["data"]: build_data_requirements(),
        ARTIFACTS["protocol"]: build_protocol(),
        ARTIFACTS["decision"]: build_decision(),
    }
    return {name: canonical_json(payload) for name, payload in payloads.items()}


def cmd_build(args: argparse.Namespace) -> int:
    args.output_root.mkdir(parents=True, exist_ok=True)
    for name, content in build_all().items():
        (args.output_root / name).write_bytes(content.encode("utf-8"))
    print("decision=M3_MECHANISM_RESEARCH_CONTRACT_FROZEN verdict=PASS")
    return 0


def cmd_verify(args: argparse.Namespace) -> int:
    failures = []
    for name, content in build_all().items():
        path = args.output_root / name
        if not path.is_file():
            failures.append(f"missing artifact: {name}")
            continue
        actual = path.read_text(encoding="utf-8").replace("\r\n", "\n").replace("\r", "\n")
        if actual != content:
            failures.append(f"artifact mismatch: {name}")
    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        return 1
    print("PASS: all M3 Stage 3A preflight contracts are deterministic and exact")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="M3 Stage 3A contract preflight")
    sub = parser.add_subparsers(dest="command", required=True)
    for name, fn in (("build", cmd_build), ("verify", cmd_verify)):
        child = sub.add_parser(name)
        child.add_argument("--output-root", type=Path, default=ROOT / "reports")
        child.set_defaults(func=fn)
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
