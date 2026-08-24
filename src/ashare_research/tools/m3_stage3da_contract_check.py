"""Offline validator for the M3 Stage 3D-A holdout contract freeze.

This module is governance-only.  It reads committed JSON contracts and
development metadata, recomputes already-frozen repository digests, and
emits a readiness envelope.  It intentionally has no data provider, network,
matrix, regression, bootstrap, or holdout execution path.
"""

from __future__ import annotations

import argparse
import json
from hashlib import sha256
from pathlib import Path
from typing import Any

from ashare_research.tools.m3_stage3cb_development import (
    verify_adapter_lock,
    verify_frozen_lock,
)

STAGE = "M3_STAGE3DA"
BASELINE = "e33373be513ef36f407bc5662caa6e9e2f2e5943"
PRIMARY = "M3_PRIMARY_DEVELOPMENT_POSITIVE_ABNORMAL_PERFORMANCE_NOT_ESTABLISHED"
ROBUSTNESS = "M3_REGISTERED_EXECUTABLE_DEVELOPMENT_ROBUSTNESS_COMPLETED"
HOLDOUT_START = "2023-01-01"
HOLDOUT_END = "2026-08-13"
DECISION = "ALLOW_ONE_FROZEN_OOS_PRIMARY_EXECUTION_AFTER_SEPARATE_STAGE3DB_AUTHORIZATION"
DATA_MANIFEST = "7c3070a64cc5931807a7c35c95fcff66dffa6bb84310304365544c2bda3f8be2"
UPSTREAM = "f206780dcb6fd4c3b9d30a92025b75974284afd16eecd24770d2f812256f0031"
PIPELINE = "ab224492ff85f391a29048dfeec740f9bbffb376de3408a5645a4552b51b9d1b"
MODEL = "4958351a5c79c0eb96bbfda9ebaaca5e71ab2b07236eaa808b0a92ebc6e9756d"
ADAPTER = "9b0df296d4b5d3b7bdf382bd07cf8bdb4410fb6659edfe88da68a16b419fbf78"
ROBUSTNESS_DIGEST = "8b870ed2b4fe8b52110fbdbf9b6412498939421f018c337ecf3955678c30a527"
DECISION_PATH = "reports/m3_stage3da_holdout_unseal_decision_v1.json"
EXECUTION_PATH = "reports/m3_stage3da_frozen_oos_execution_contract_v1.json"
POLICY_PATH = "reports/m3_stage3da_holdout_interpretation_policy_v1.json"
CB_MANIFEST_PATH = "reports/m3_stage3cb_analysis_input_manifest_v1.json"
CB_RESULT_PATH = "reports/m3_stage3cb_primary_development_result_v1.json"
CC_RESULT_PATH = "reports/m3_stage3cc_registered_robustness_result_v1.json"
CC_PLAN_PATH = "reports/m3_stage3cc_execution_plan_v1.json"
CC_SCHEMA_PATH = "reports/m3_stage3cc_registered_robustness_result_schema_v1.json"
CC_REGISTRY_PATH = "reports/m3_stage3ca_robustness_registry_v2.json"
CC_RUNNER_PATH = "src/ashare_research/tools/m3_stage3cc_registered_robustness.py"
FROZEN_ROBUSTNESS_PATH = "src/ashare_research/mechanism/robustness.py"
FROZEN_REGRESSION_PATH = "src/ashare_research/mechanism/regression.py"


class Stage3DAContractError(ValueError):
    """Raised when the immutable Stage 3D-A contract is not ready."""


def _root() -> Path:
    return Path(__file__).resolve().parents[3]


def _load(root: Path, relative: str) -> dict[str, Any]:
    path = root / relative
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise Stage3DAContractError(f"M3_STAGE3DA_CONTRACT_LOAD_FAILED:{relative}") from exc
    if not isinstance(payload, dict):
        raise Stage3DAContractError(f"M3_STAGE3DA_CONTRACT_NOT_OBJECT:{relative}")
    return payload


def _require(condition: bool, code: str) -> None:
    if not condition:
        raise Stage3DAContractError(code)


def _repository_relative(root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError as exc:
        raise Stage3DAContractError("M3_STAGE3DA_DIGEST_PATH_OUTSIDE_REPOSITORY") from exc


def _canonical_digest(payload: dict[str, Any]) -> str:
    encoded = json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode()
    return sha256(encoded).hexdigest()


def _recompute_robustness_execution_digest(
    root: Path, *, data_manifest_digest: str, model_digest: str
) -> str:
    """Rebuild only the Stage 3C-C hash envelope; never import research execution code."""

    paths = {
        "execution_plan": root / CC_PLAN_PATH,
        "result_schema": root / CC_SCHEMA_PATH,
        "robustness_registry": root / CC_REGISTRY_PATH,
        "runner": root / CC_RUNNER_PATH,
        "frozen_robustness": root / FROZEN_ROBUSTNESS_PATH,
        "frozen_regression": root / FROZEN_REGRESSION_PATH,
    }
    for path in paths.values():
        _require(path.is_file(), f"M3_STAGE3DA_DIGEST_SOURCE_MISSING:{path.name}")
    source_names = ("runner", "frozen_robustness", "frozen_regression")
    contract_names = ("execution_plan", "result_schema", "robustness_registry")
    payload = {
        "digest_algorithm": "M3_REPOSITORY_RELATIVE_DIGEST_V2",
        "stage": "M3_STAGE3CC",
        "execution_plan_path": _repository_relative(root, paths["execution_plan"]),
        "result_schema_path": _repository_relative(root, paths["result_schema"]),
        "robustness_registry_sha256": sha256(paths["robustness_registry"].read_bytes()).hexdigest(),
        "source_hashes": {
            _repository_relative(root, paths[name]): sha256(paths[name].read_bytes()).hexdigest()
            for name in source_names
        },
        "contract_hashes": {
            _repository_relative(root, paths[name]): sha256(paths[name].read_bytes()).hexdigest()
            for name in contract_names
        },
        "data_manifest_digest": data_manifest_digest,
        "model_digest": model_digest,
    }
    return _canonical_digest(payload)


def validate_decision_contract(contract: dict[str, Any]) -> None:
    _require(contract.get("contract_id") == "M3_STAGE3DA_HOLDOUT_UNSEAL_DECISION_V1", "DECISION_ID")
    _require(contract.get("stage") == STAGE, "DECISION_STAGE")
    _require(contract.get("canonical_base") == BASELINE, "DECISION_BASELINE")
    _require(contract.get("development_primary_decision") == PRIMARY, "PRIMARY_REVERSAL")
    _require(contract.get("development_robustness_status") == ROBUSTNESS, "ROBUSTNESS_ANCHOR")
    _require(contract.get("development_evidence_ceiling") == 2, "EVIDENCE_CEILING")
    _require(contract.get("development_evidence_level") is None, "EVIDENCE_LEVEL")
    _require(contract.get("holdout_status") == "SEALED", "HOLDOUT_STATUS")
    for key in ("holdout_read", "holdout_download", "holdout_parse", "holdout_hash"):
        _require(contract.get(key) is False, f"{key.upper()}_MUST_BE_FALSE")
    _require(contract.get("holdout_start") == HOLDOUT_START, "HOLDOUT_START")
    _require(contract.get("holdout_end") == HOLDOUT_END, "HOLDOUT_END")
    _require(contract.get("unseal_decision") == DECISION, "UNSEAL_DECISION")
    _require(contract.get("stage3db_requires_separate_authorization") is True, "SEPARATE_AUTH")
    _require(contract.get("stage3db_status") == "NOT_STARTED", "STAGE3DB_STARTED")
    _require(contract.get("minute_level_authorized") is False, "MINUTE_ESCALATION")
    _require(contract.get("index_contribution_authorized") is False, "INDEX_EXECUTION")
    boundary = contract.get("interpretation_boundary", {})
    _require(boundary.get("holdout_purpose") == "FROZEN_OUT_OF_SAMPLE_FALSIFICATION", "PURPOSE")
    _require(boundary.get("causal_interpretation_allowed") is False, "CAUSAL_BOUNDARY")
    _require(boundary.get("funding_actor_interpretation_allowed") is False, "ACTOR_BOUNDARY")
    _require(boundary.get("minute_level_auto_escalation_allowed") is False, "MINUTE_BOUNDARY")
    _require(
        boundary.get("positive_holdout_does_not_establish_overall_primary") is True,
        "OVERALL_BOUNDARY",
    )


def validate_execution_contract(contract: dict[str, Any]) -> None:
    _require(
        contract.get("contract_id") == "M3_STAGE3DA_FROZEN_OOS_EXECUTION_CONTRACT_V1",
        "EXECUTION_ID",
    )
    _require(contract.get("stage") == STAGE, "EXECUTION_STAGE")
    _require(contract.get("canonical_base") == BASELINE, "EXECUTION_BASELINE")
    _require(
        contract.get("digest_algorithm") == "M3_REPOSITORY_RELATIVE_DIGEST_V2",
        "DIGEST_ALGORITHM",
    )
    for key, expected in {
        "expected_upstream_inventory_sha": UPSTREAM,
        "expected_pipeline_digest": PIPELINE,
        "expected_model_digest": MODEL,
        "expected_stage3cb_execution_adapter_digest": ADAPTER,
        "expected_development_data_manifest_digest": DATA_MANIFEST,
        "expected_stage3cc_robustness_execution_digest": ROBUSTNESS_DIGEST,
    }.items():
        _require(contract.get(key) == expected, f"IDENTITY:{key}")
    _require(contract.get("holdout_start") == HOLDOUT_START, "EXECUTION_HOLDOUT_START")
    _require(contract.get("holdout_end") == HOLDOUT_END, "EXECUTION_HOLDOUT_END")
    _require(contract.get("execution_scope") == "FROZEN_PRIMARY_ONLY", "EXECUTION_SCOPE")
    _require(contract.get("accepted_execution_max_count") == 1, "EXECUTION_COUNT")
    _require(contract.get("ab_reproducibility_rerun_allowed") is True, "AB_POLICY")
    ab = contract.get("ab_reproducibility_rerun_policy", {})
    _require(ab.get("counts_as_new_research_trial") is False, "AB_NEW_TRIAL")
    _require(ab.get("requires_identical_immutable_analysis_matrix") is True, "AB_MATRIX")
    _require(ab.get("requires_identical_contract_and_identity_digests") is True, "AB_IDENTITY")
    _require(contract.get("primary_threshold") == -0.01, "PRIMARY_THRESHOLD")
    _require(contract.get("bootstrap_replications") == 5000, "BOOTSTRAP_REPLICATIONS")
    _require(contract.get("bootstrap_seed") == 20260813, "BOOTSTRAP_SEED")
    _require(contract.get("bootstrap_rng") == "PCG64", "BOOTSTRAP_RNG")
    _require(
        contract.get("bootstrap_method") == "NON_CIRCULAR_OVERLAPPING_MOVING_BLOCK_BOOTSTRAP",
        "BOOTSTRAP_METHOD",
    )
    _require(contract.get("bootstrap_ci") == "TWO_SIDED_PERCENTILE_95", "BOOTSTRAP_CI")
    _require(contract.get("regression_estimator") == "statsmodels OLS", "ESTIMATOR")
    for key in (
        "new_model_allowed",
        "new_threshold_allowed",
        "new_proxy_allowed",
        "new_controls_allowed",
        "robustness_search_allowed",
        "holdout_extension_allowed",
    ):
        _require(contract.get(key) is False, f"FORBIDDEN_OPTION:{key}")
    _require(contract.get("stage3db_authorization_required") is True, "EXECUTION_AUTH")
    rule = contract.get("primary_decision_rule", {})
    _require(
        rule.get("positive") == "gamma_holdout > 0 AND holdout_bootstrap_95ci_lower > 0",
        "DECISION_RULE",
    )
    for key in (
        "p_value_substitution_allowed",
        "t_stat_substitution_allowed",
        "r_squared_substitution_allowed",
        "descriptive_mean_substitution_allowed",
        "alternative_threshold_substitution_allowed",
    ):
        _require(rule.get(key) is False, f"DECISION_SUBSTITUTION:{key}")


def validate_interpretation_policy(policy: dict[str, Any]) -> None:
    _require(
        policy.get("contract_id") == "M3_STAGE3DA_HOLDOUT_INTERPRETATION_POLICY_V1",
        "POLICY_ID",
    )
    _require(policy.get("stage") == STAGE, "POLICY_STAGE")
    _require(policy.get("holdout_can_reverse_development_primary") is False, "POLICY_REVERSAL")
    _require(policy.get("development_primary_reversal_allowed") is False, "POLICY_PRIMARY_REVERSAL")
    _require(policy.get("development_rescue_by_holdout_allowed") is False, "POLICY_RESCUE")
    _require(policy.get("causal_interpretation_allowed") is False, "POLICY_CAUSAL")
    _require(policy.get("funding_actor_interpretation_allowed") is False, "POLICY_ACTOR")
    _require(policy.get("minute_level_auto_escalation_allowed") is False, "POLICY_MINUTE")
    cases = {item.get("case_id"): item for item in policy.get("cases", [])}
    _require(set(cases) == {"A", "B", "C"}, "POLICY_CASES")
    expected = {
        "A": "M3_DAILY_MECHANISM_NOT_SUPPORTED_ACROSS_DEVELOPMENT_AND_HOLDOUT",
        "B": "M3_DEVELOPMENT_NOT_ESTABLISHED_HOLDOUT_POSITIVE_CROSS_PERIOD_INSTABILITY",
        "C": "M3_HOLDOUT_PRIMARY_INCONCLUSIVE_TECHNICAL_OR_COVERAGE_GAP",
    }
    for case_id, disposition in expected.items():
        _require(
            cases[case_id].get("final_disposition") == disposition,
            f"POLICY_DISPOSITION:{case_id}",
        )
        _require(
            cases[case_id].get("overall_primary_established") is False,
            f"POLICY_OVERALL:{case_id}",
        )


def _verify_identity(root: Path, execution: dict[str, Any]) -> dict[str, str]:
    try:
        frozen = verify_frozen_lock()
        adapter = verify_adapter_lock()
    except Exception as exc:  # normalize all identity failures to a fail-closed code
        raise Stage3DAContractError("M3_STAGE3DA_IDENTITY_GATE_FAILED") from exc
    _require(frozen["upstream_inventory_sha256"] == UPSTREAM, "IDENTITY_UPSTREAM")
    _require(frozen["pipeline_digest"] == PIPELINE, "IDENTITY_PIPELINE")
    _require(frozen["model_digest"] == MODEL, "IDENTITY_MODEL")
    _require(adapter == ADAPTER, "IDENTITY_ADAPTER")
    manifest = _load(root, CB_MANIFEST_PATH)
    result = _load(root, CB_RESULT_PATH)
    robustness = _load(root, CC_RESULT_PATH)
    _require(manifest.get("data_manifest_digest") == DATA_MANIFEST, "IDENTITY_MANIFEST")
    _require(manifest.get("holdout_read") is False, "IDENTITY_MANIFEST_HOLDOUT")
    _require(result.get("primary_decision") == PRIMARY, "IDENTITY_PRIMARY_RESULT")
    _require(result.get("data_manifest_digest") == DATA_MANIFEST, "IDENTITY_PRIMARY_MANIFEST")
    _require(
        robustness.get("robustness_execution_digest") == ROBUSTNESS_DIGEST,
        "IDENTITY_ROBUSTNESS",
    )
    _require(robustness.get("holdout_read") is False, "IDENTITY_ROBUSTNESS_HOLDOUT")
    recomputed = _recompute_robustness_execution_digest(
        root, data_manifest_digest=DATA_MANIFEST, model_digest=MODEL
    )
    _require(recomputed == ROBUSTNESS_DIGEST, "IDENTITY_ROBUSTNESS_RECOMPUTE")
    _require(
        execution.get("expected_upstream_inventory_sha") == frozen["upstream_inventory_sha256"],
        "IDENTITY_CONTRACT_UPSTREAM",
    )
    return {
        "upstream_inventory_sha": frozen["upstream_inventory_sha256"],
        "pipeline_digest": frozen["pipeline_digest"],
        "model_digest": frozen["model_digest"],
        "execution_adapter_digest": adapter,
        "development_data_manifest_digest": DATA_MANIFEST,
        "robustness_execution_digest": ROBUSTNESS_DIGEST,
    }


def verify_repository_contracts(root: Path | None = None) -> dict[str, Any]:
    repo = (root or _root()).resolve()
    decision = _load(repo, DECISION_PATH)
    execution = _load(repo, EXECUTION_PATH)
    policy = _load(repo, POLICY_PATH)
    validate_decision_contract(decision)
    validate_execution_contract(execution)
    validate_interpretation_policy(policy)
    identity = _verify_identity(repo, execution)
    checks = {
        "decision_contract": "PASS",
        "execution_contract": "PASS",
        "interpretation_policy": "PASS",
        "identity_gate": "PASS",
        "holdout_boundary": "PASS",
        "forbidden_options": "PASS",
        "holdout_read": "PASS",
        "network_acquisition": "PASS",
    }
    return {
        "schema": "m3_stage3da_contract_readiness_v1",
        "stage": STAGE,
        "status": "PASS",
        "canonical_base": BASELINE,
        "holdout_status": "SEALED",
        "holdout_read": False,
        "holdout_start": HOLDOUT_START,
        "holdout_end": HOLDOUT_END,
        "stage3db_status": "NOT_STARTED",
        "stage3db_eligible_for_separate_authorization": True,
        "checks": checks,
        "identity": identity,
        "stop_condition": "STOP_FOR_NORTH_STAR_REVIEW",
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("verify-contracts",))
    parser.add_argument("--output", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        report = verify_repository_contracts()
    except Stage3DAContractError as exc:
        print(str(exc))
        return 1
    encoded = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded, encoding="utf-8", newline="\n")
    print(encoded, end="")
    print("M3_STAGE3DA_HOLDOUT_CONTRACT_READY")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
