"""Synthetic-only M3 Stage 3C-A pipeline smoke and fixture runner."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from ashare_research.mechanism.analysis_contracts import (
    BOOTSTRAP_REPLICATIONS,
    BOOTSTRAP_RNG,
    BOOTSTRAP_SEED,
    DESIGN_COLUMNS,
    UPSTREAM_INVENTORY_NAME,
    AnalysisContractError,
    contract_path,
    enforce_execution_gate,
    load_json_contract,
)
from ashare_research.mechanism.analysis_dataset import (
    prepare_analysis_dataset,
    select_development_sample,
)
from ashare_research.mechanism.bootstrap import moving_block_bootstrap
from ashare_research.mechanism.crash import add_crash_indicator
from ashare_research.mechanism.evidence import (
    evidence_level,
    interpretation_boundary,
    primary_decision,
)
from ashare_research.mechanism.model_digest import build_model_digest, build_pipeline_digest
from ashare_research.mechanism.regression import fit_primary_ols
from ashare_research.mechanism.robustness import (
    benjamini_hochberg,
    conditional_summary,
    descriptive_summary,
    leave_one_year_out,
    remove_top_extreme_crash_days,
    threshold_robustness,
)


def synthetic_fixture(kind: str, n: int = 900) -> pd.DataFrame:
    if kind not in {"positive", "null", "negative", "extreme"}:
        raise ValueError(f"unknown fixture: {kind}")
    rng = np.random.Generator(np.random.PCG64(77))
    dates = pd.date_range("2018-01-02", periods=n, freq="B")
    market = rng.normal(0.0003, 0.012, n)
    oil = rng.normal(0.0002, 0.008, n)
    industry = rng.normal(0.0001, 0.007, n)
    crash = (market <= -0.01).astype(int)
    gamma = {"positive": 0.025, "null": 0.0, "negative": -0.025, "extreme": 0.0}[kind]
    target = 0.001 + 0.8 * market + 0.3 * oil + 0.2 * industry + gamma * crash
    target += rng.normal(0, 0.004, n)
    if kind == "extreme":
        crash_indices = np.flatnonzero(crash)
        if len(crash_indices) < 3:
            crash_indices = np.array([10, 20, 30])
            market[crash_indices] = -0.02
            crash = (market <= -0.01).astype(int)
        target[crash_indices[0]] += 0.25
    return pd.DataFrame(
        {
            "trade_date": dates,
            "target_analysis_return": target,
            "market_ex_target_return": market,
            "oil_return": oil,
            "industry_return": industry,
            "target_valid": True,
            "market_valid": True,
            "oil_valid": True,
            "industry_valid": True,
            "tier1_joint_valid": True,
        }
    )


def _source_paths() -> list[Path]:
    root = Path(__file__).resolve().parents[3]
    return [root / "src/ashare_research/mechanism" / name for name in (
        "analysis_contracts.py", "analysis_dataset.py", "crash.py", "regression.py",
        "bootstrap.py", "robustness.py", "evidence.py", "model_digest.py",
    )]


def run_synthetic(
    kind: str,
    output: Path | None = None,
    bootstrap_replications: int = BOOTSTRAP_REPLICATIONS,
) -> dict:
    contracts = [
        load_json_contract("m3_stage3ca_analysis_pipeline_contract_v2.json"),
        load_json_contract("m3_stage3ca_model_specification_v2.json"),
        load_json_contract("m3_stage3ca_robustness_registry_v2.json"),
        load_json_contract("m3_stage3ca_output_schema_v2.json"),
        load_json_contract(UPSTREAM_INVENTORY_NAME),
    ]
    if contracts[-1]["status"] != "LOCKED_TO_CANONICAL_M3_BYTES":
        raise AnalysisContractError("upstream inventory is not canonical and locked")
    frame = synthetic_fixture(kind)
    enforce_execution_gate("synthetic", frame)
    sample = select_development_sample(prepare_analysis_dataset(frame))
    sample = add_crash_indicator(sample)
    fitted = fit_primary_ols(sample)
    bootstrap = moving_block_bootstrap(
        sample,
        replications=bootstrap_replications,
        seed=BOOTSTRAP_SEED,
        rng_algorithm=BOOTSTRAP_RNG,
    )
    decision = primary_decision(fitted.gamma, bootstrap.gamma_ci_lower)
    desc = descriptive_summary(sample)
    level = evidence_level(
        gamma=fitted.gamma,
        gamma_ci_lower=bootstrap.gamma_ci_lower,
        descriptive_relationship_present=desc["full_sample_correlation"] is not None,
        controls_trusted=True,
        robustness_triggered=kind == "extreme",
    )
    pipeline_digest, pipeline_payload = build_pipeline_digest(_source_paths())
    model_digest, model_payload = build_model_digest(
        pipeline_digest=pipeline_digest,
        contract_paths=[contract_path(name) for name in (
            "m3_stage3ca_analysis_pipeline_contract_v2.json",
            "m3_stage3ca_model_specification_v2.json",
            "m3_stage3ca_robustness_registry_v2.json",
            "m3_stage3ca_output_schema_v2.json",
            UPSTREAM_INVENTORY_NAME,
        )],
        source_paths=_source_paths(),
        dependency_contract={"statsmodels": ">=0.14.6,<0.15", "numpy_rng": "PCG64"},
        upstream_inventory_path=contract_path(UPSTREAM_INVENTORY_NAME),
    )
    threshold_results = threshold_robustness(sample)
    robustness = {
        "pipeline_digest": pipeline_digest,
        "model_digest": model_digest,
        "robustness_triggered": kind == "extreme",
        "descriptive": desc,
        "conditional": conditional_summary(sample),
        "thresholds": threshold_results,
        "leave_one_calendar_year_out": leave_one_year_out(sample),
        "extreme_days": {},
        "threshold_fdr": benjamini_hochberg(
            [item["pvalue_two_sided"] for item in threshold_results if item["estimable"]]
        ),
    }
    for count in (1, 3):
        reduced, dates = remove_top_extreme_crash_days(sample, fitted, count)
        robustness["extreme_days"][str(count)] = {
            "removed_trade_dates": dates,
            "refit_gamma": (
                fit_primary_ols(reduced).gamma
                if len(reduced) >= len(DESIGN_COLUMNS)
                else None
            ),
        }
    primary = {
        "model_id": "M3_STAGE3CAR_PETROCHINA_CRASH_CONTROL_OLS_V2",
        "model_digest": model_digest,
        "data_manifest_digest": "synthetic-fixture-" + kind,
        "sample_start": sample["trade_date"].min().strftime("%Y-%m-%d"),
        "sample_end": sample["trade_date"].max().strftime("%Y-%m-%d"),
        "nobs": int(len(sample)),
        "crash_threshold": -0.01,
        "crash_count": int(sample["Crash_t"].sum()),
        "coefficients": fitted.coefficients,
        "bootstrap": {
            "method": "NON_CIRCULAR_OVERLAPPING_MOVING_BLOCK_BOOTSTRAP",
            "block_length": bootstrap.block_length,
            "replications": bootstrap.replications,
            "seed": bootstrap.seed,
            "rng": bootstrap.rng,
            "gamma_ci_lower": bootstrap.gamma_ci_lower,
            "gamma_ci_upper": bootstrap.gamma_ci_upper,
        },
        "primary_decision": decision,
        "evidence_level": level,
        "interpretation_boundary": interpretation_boundary(level),
    }
    result = {
        "status": "M3_STAGE3CAR_CANONICAL_RECOVERY_ACCEPTED",
        "status_tokens": [
            "M3_STAGE3CAR_CANONICAL_RECOVERY_ACCEPTED",
            "M3_ANALYSIS_PIPELINE_LOCKED_ON_CANONICAL_M3",
            "M3_MODEL_SPECIFICATION_LOCKED_ON_CANONICAL_M3",
            "M3_MODEL_DIGEST_LOCKED_TO_EFFECTIVE_M3_UPSTREAMS",
            "M3_TIER1_DEVELOPMENT_INPUTS_READY",
            "M3_DEVELOPMENT_REAL_ANALYSIS_NOT_EXECUTED",
            "M3_HOLDOUT_REMAINS_SEALED",
            "M3_STAGE3CB_ELIGIBLE_FOR_SEPARATE_NORTH_STAR_AUTHORIZATION",
            "M3_STAGE3CB_NOT_STARTED",
            "STOP_FOR_NORTH_STAR_REVIEW",
        ],
        "fixture": kind,
        "pipeline_digest": pipeline_digest,
        "pipeline_digest_payload": pipeline_payload,
        "model_digest_payload": model_payload,
        "primary": primary,
        "robustness": robustness,
        "execution": {
            "mode": "synthetic",
            "real_development_execution_authorized": False,
            "holdout_execution_authorized": False,
        },
    }
    if output is not None:
        output.mkdir(parents=True, exist_ok=True)
        (output / "analysis_input_manifest.json").write_text(
            json.dumps(
                {
                    "mode": "synthetic",
                    "fixture": kind,
                    "nobs": len(sample),
                    "target_return_definition": "ADJUSTED_CLOSE_TO_CLOSE_SIMPLE_RETURN",
                    "sample_rule": "target_valid AND tier1_joint_valid AND development_date",
                    "real_inputs_read": False,
                    "holdout_sealed": True,
                    "upstream_inventory": UPSTREAM_INVENTORY_NAME,
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        (output / "mechanism_primary_result.json").write_text(
            json.dumps(primary, indent=2), encoding="utf-8"
        )
        (output / "mechanism_robustness_result.json").write_text(
            json.dumps(robustness, indent=2), encoding="utf-8"
        )
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--execution-mode", required=True, choices=["synthetic", "development"]
    )
    parser.add_argument(
        "--fixture", default="positive", choices=["positive", "null", "negative", "extreme"]
    )
    parser.add_argument("--output", type=Path)
    parser.add_argument("--bootstrap-replications", type=int, default=BOOTSTRAP_REPLICATIONS)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.execution_mode != "synthetic":
        print("REAL_ANALYSIS_NOT_AUTHORIZED")
        return 2
    try:
        result = run_synthetic(args.fixture, args.output, args.bootstrap_replications)
    except (AnalysisContractError, ValueError) as exc:
        print(str(exc))
        return 1
    print(json.dumps(result["primary"], indent=2))
    print(result["status"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
