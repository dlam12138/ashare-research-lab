"""Execute only the pre-outcome-registered Stage 3C-C robustness suite.

This module is orchestration only.  Matrix construction remains delegated to
the immutable Stage 3C-B adapter, and every research calculation remains
delegated to the frozen mechanism functions.
"""

from __future__ import annotations

import argparse
import json
import math
import subprocess
from pathlib import Path
from typing import Any

from ashare_research.mechanism.contracts import sha256_file
from ashare_research.mechanism.crash import add_crash_indicator
from ashare_research.mechanism.model_digest import canonical_digest
from ashare_research.mechanism.regression import fit_primary_ols
from ashare_research.mechanism.robustness import (
    benjamini_hochberg,
    conditional_summary,
    descriptive_summary,
    leave_one_year_out,
    remove_top_extreme_crash_days,
    threshold_robustness,
)
from ashare_research.tools.m3_stage3cb_development import (
    _data_manifest_payload,
    verify_adapter_lock,
    verify_frozen_lock,
)
from ashare_research.tools.m3_stage3cb_inputs import (
    EXPECTED_DIGEST_ALGORITHM,
    Stage3CBInputError,
    load_json,
    locate_known_inputs,
    materialize_analysis_matrix,
    select_locked_development_matrix,
)

STAGE = "M3_STAGE3CC"
CANONICAL_BASE = "4669eebf2e1837053495d56f68ea414bd76c692d"
PRIMARY_DECISION = "M3_PRIMARY_DEVELOPMENT_POSITIVE_ABNORMAL_PERFORMANCE_NOT_ESTABLISHED"
EXPECTED_DATA_MANIFEST_DIGEST = "7c3070a64cc5931807a7c35c95fcff66dffa6bb84310304365544c2bda3f8be2"
EXPECTED_MODEL_DIGEST = "4958351a5c79c0eb96bbfda9ebaaca5e71ab2b07236eaa808b0a92ebc6e9756d"
EXPECTED_UPSTREAM_INVENTORY_SHA = "f206780dcb6fd4c3b9d30a92025b75974284afd16eecd24770d2f812256f0031"
EXPECTED_PIPELINE_DIGEST = "ab224492ff85f391a29048dfeec740f9bbffb376de3408a5645a4552b51b9d1b"
EXPECTED_ADAPTER_DIGEST = "9b0df296d4b5d3b7bdf382bd07cf8bdb4410fb6659edfe88da68a16b419fbf78"
THRESHOLDS = [-0.005, -0.015, -0.02]
BH_Q = 0.05
EXTREME_COUNTS = [1, 3]
REGISTRY_PATH = "reports/m3_stage3ca_robustness_registry_v2.json"
PLAN_PATH = "reports/m3_stage3cc_execution_plan_v1.json"
SCHEMA_PATH = "reports/m3_stage3cc_registered_robustness_result_schema_v1.json"
RUNNER_PATH = "src/ashare_research/tools/m3_stage3cc_registered_robustness.py"
FROZEN_ROBUSTNESS_PATH = "src/ashare_research/mechanism/robustness.py"
FROZEN_REGRESSION_PATH = "src/ashare_research/mechanism/regression.py"
CB_MANIFEST_PATH = "reports/m3_stage3cb_analysis_input_manifest_v1.json"
CB_RESULT_PATH = "reports/m3_stage3cb_primary_development_result_v1.json"


def _root() -> Path:
    return Path(__file__).resolve().parents[3]


def _relative(root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError as exc:
        raise Stage3CBInputError("M3_STAGE3CC_DIGEST_PATH_OUTSIDE_REPOSITORY") from exc


def _current_head() -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=_root(),
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise Stage3CBInputError("M3_STAGE3CC_GIT_HEAD_UNAVAILABLE") from exc
    return result.stdout.strip()


def load_execution_plan(root: Path | None = None) -> dict[str, Any]:
    repo = (root or _root()).resolve()
    plan = load_json(repo / PLAN_PATH)
    expected = {
        "contract_id": "M3_STAGE3CC_EXECUTION_PLAN_V1",
        "stage": STAGE,
        "registry_path": REGISTRY_PATH,
        "registry_sha256": "8163e1c8f3a9956f3de48f824ec3199660395a662af78ec3d613fa068cf9c121",
        "digest_algorithm": EXPECTED_DIGEST_ALGORITHM,
    }
    for key, value in expected.items():
        if plan.get(key) != value:
            raise Stage3CBInputError(f"M3_STAGE3CC_EXECUTION_PLAN_MISMATCH:{key}")
    if sha256_file(repo / REGISTRY_PATH) != plan["registry_sha256"]:
        raise Stage3CBInputError("M3_STAGE3CC_REGISTRY_SHA_MISMATCH")
    execution = plan.get("execution", {})
    exact_execution = {
        "descriptive_summary": "EXECUTE_EXISTING_FUNCTION",
        "conditional_summary": "EXECUTE_EXISTING_FUNCTION",
        "threshold_robustness": "EXECUTE_EXISTING_FUNCTION",
        "thresholds": THRESHOLDS,
        "benjamini_hochberg": "EXECUTE_EXISTING_FUNCTION",
        "benjamini_hochberg_q": BH_Q,
        "remove_top_extreme_crash_days": "EXECUTE_EXISTING_FUNCTION",
        "remove_top_extreme_crash_day_counts": EXTREME_COUNTS,
        "leave_one_calendar_year_out": "EXECUTE_EXISTING_FUNCTION",
        "year_by_year": "EXISTING_DESCRIPTIVE_OUTPUT_ONLY",
    }
    if execution != exact_execution:
        raise Stage3CBInputError("M3_STAGE3CC_EXECUTION_PLAN_SCOPE_MISMATCH")
    gaps = plan.get("not_executed", {})
    if gaps.get("leave_one_event_out") != "NOT_EXECUTED_PREOUTCOME_IMPLEMENTATION_MISSING":
        raise Stage3CBInputError("M3_STAGE3CC_LEAVE_ONE_EVENT_OUT_SCOPE_MISMATCH")
    if gaps.get("alternative_market_proxies") != "NOT_EXECUTED_DATA_NOT_ACQUIRED":
        raise Stage3CBInputError("M3_STAGE3CC_ALTERNATIVE_PROXY_SCOPE_MISMATCH")
    if gaps.get("industry_ex_target") != "NOT_EXECUTED_FUTURE_CANDIDATE":
        raise Stage3CBInputError("M3_STAGE3CC_INDUSTRY_SCOPE_MISMATCH")
    if plan.get("holdout") != {
        "start": "2023-01-01",
        "status": "SEALED",
        "read": False,
        "new_data_acquisition": False,
    }:
        raise Stage3CBInputError("M3_STAGE3CC_HOLDOUT_PLAN_MISMATCH")
    return plan


def load_result_schema(root: Path | None = None) -> dict[str, Any]:
    repo = (root or _root()).resolve()
    schema = load_json(repo / SCHEMA_PATH)
    if schema.get("contract_id") != "M3_STAGE3CC_REGISTERED_ROBUSTNESS_RESULT_SCHEMA_V1":
        raise Stage3CBInputError("M3_STAGE3CC_RESULT_SCHEMA_MISMATCH")
    if schema.get("stage") != STAGE or schema.get("digest_algorithm") != EXPECTED_DIGEST_ALGORITHM:
        raise Stage3CBInputError("M3_STAGE3CC_RESULT_SCHEMA_MISMATCH:identity")
    if schema.get("primary_anchor", {}).get("decision") != PRIMARY_DECISION:
        raise Stage3CBInputError("M3_STAGE3CC_RESULT_SCHEMA_PRIMARY_DECISION_MISMATCH")
    if schema.get("threshold_family") != {
        "thresholds": THRESHOLDS,
        "bh_q": BH_Q,
        "primary_threshold_excluded": -0.01,
    }:
        raise Stage3CBInputError("M3_STAGE3CC_RESULT_SCHEMA_THRESHOLD_MISMATCH")
    if schema.get("extreme_day_counts") != EXTREME_COUNTS:
        raise Stage3CBInputError("M3_STAGE3CC_RESULT_SCHEMA_EXTREME_DAY_MISMATCH")
    return schema


def build_robustness_execution_digest(
    *,
    data_manifest_digest: str,
    model_digest: str,
    root: Path | None = None,
) -> tuple[str, dict[str, Any]]:
    """Bind orchestration/contracts and frozen code using repository-relative keys."""

    repo = (root or _root()).resolve()
    paths = {
        "execution_plan": repo / PLAN_PATH,
        "result_schema": repo / SCHEMA_PATH,
        "robustness_registry": repo / REGISTRY_PATH,
        "runner": repo / RUNNER_PATH,
        "frozen_robustness": repo / FROZEN_ROBUSTNESS_PATH,
        "frozen_regression": repo / FROZEN_REGRESSION_PATH,
    }
    payload = {
        "digest_algorithm": EXPECTED_DIGEST_ALGORITHM,
        "stage": STAGE,
        "execution_plan_path": _relative(repo, paths["execution_plan"]),
        "result_schema_path": _relative(repo, paths["result_schema"]),
        "robustness_registry_sha256": sha256_file(paths["robustness_registry"]),
        "source_hashes": {
            _relative(repo, paths[name]): sha256_file(path)
            for name, path in paths.items()
            if name in {"runner", "frozen_robustness", "frozen_regression"}
        },
        "contract_hashes": {
            _relative(repo, paths[name]): sha256_file(path)
            for name, path in paths.items()
            if name in {"execution_plan", "result_schema", "robustness_registry"}
        },
        "data_manifest_digest": data_manifest_digest,
        "model_digest": model_digest,
    }
    return canonical_digest(payload), payload


def _load_primary_anchor(repo: Path) -> dict[str, Any]:
    result = load_json(repo / CB_RESULT_PATH)
    expected = {
        "nobs": 1902,
        "crash_count": 330,
        "gamma": 0.0005072734676652487,
        "gamma_ci_lower": -0.0021987423016553366,
        "gamma_ci_upper": 0.0033325010311833106,
        "primary_decision": PRIMARY_DECISION,
        "pipeline_digest": EXPECTED_PIPELINE_DIGEST,
        "model_digest": EXPECTED_MODEL_DIGEST,
        "execution_adapter_digest": EXPECTED_ADAPTER_DIGEST,
        "data_manifest_digest": EXPECTED_DATA_MANIFEST_DIGEST,
    }
    for key, value in expected.items():
        if result.get(key) != value:
            raise Stage3CBInputError(f"M3_STAGE3CC_PRIMARY_ANCHOR_MISMATCH:{key}")
    return result


def _assert_close(actual: float, expected: float, key: str) -> None:
    if not math.isclose(actual, expected, rel_tol=1e-12, abs_tol=1e-15):
        raise Stage3CBInputError(f"M3_STAGE3CC_PRIMARY_RECONSTRUCTION_MISMATCH:{key}")


def _reconstruct_primary(sample, anchor: dict[str, Any]):
    crashed = add_crash_indicator(sample)
    fitted = fit_primary_ols(crashed)
    if len(crashed) != anchor["nobs"] or int(crashed["Crash_t"].sum()) != anchor["crash_count"]:
        raise Stage3CBInputError("M3_STAGE3CC_PRIMARY_RECONSTRUCTION_MISMATCH:counts")
    for key in ("alpha", "beta_market", "beta_oil", "beta_industry", "gamma"):
        _assert_close(fitted.coefficients[key], anchor[key], key)
    return crashed, fitted


def _execute_on_sample(sample, anchor: dict[str, Any]) -> dict[str, Any]:
    crashed, fitted = _reconstruct_primary(sample, anchor)
    threshold_results = threshold_robustness(crashed, thresholds=THRESHOLDS)
    p_values = [item["pvalue_two_sided"] for item in threshold_results]
    if any(
        item["estimable"] is not True or value is None
        for item, value in zip(threshold_results, p_values, strict=True)
    ):
        raise Stage3CBInputError("M3_STAGE3CC_FROZEN_ROBUSTNESS_IMPLEMENTATION_FAILURE")
    bh = benjamini_hochberg(p_values, q=BH_Q)

    extreme: dict[str, dict[str, Any]] = {}
    for count in EXTREME_COUNTS:
        filtered, removed_dates = remove_top_extreme_crash_days(crashed, fitted, count)
        refit = fit_primary_ols(filtered)
        extreme[f"remove_top_{count}"] = {
            "count_removed": count,
            "removed_dates": removed_dates,
            "nobs": int(len(filtered)),
            "gamma": refit.gamma,
        }

    return {
        "descriptive": descriptive_summary(crashed),
        "conditional": conditional_summary(crashed),
        "threshold_robustness": {
            "results": threshold_results,
            "bh_q": bh["q"],
            "bh_adjusted_p_values": bh["adjusted_p_values"],
            "bh_reject": bh["reject"],
        },
        "extreme_day": extreme,
        "calendar_year": {"leave_one_year_out": leave_one_year_out(crashed)},
    }


def validate_result_payload(payload: dict[str, Any], root: Path | None = None) -> None:
    """Fail closed if a result attempts to alter the frozen primary boundary."""

    schema = load_result_schema(root)
    missing = [field for field in schema["required_fields"] if field not in payload]
    if missing:
        raise Stage3CBInputError(f"M3_STAGE3CC_RESULT_SCHEMA_MISSING:{','.join(missing)}")
    anchor = payload["primary_anchor"]
    expected = schema["primary_anchor"]
    for key in ("nobs", "crash_count", "gamma", "gamma_ci_lower", "gamma_ci_upper", "decision"):
        result_key = "primary_decision" if key == "decision" else key
        if anchor.get(result_key, anchor.get(key)) != expected[key]:
            raise Stage3CBInputError(f"M3_STAGE3CC_PRIMARY_DECISION_IMMUTABLE:{key}")
    thresholds = payload["threshold_robustness"]["results"]
    if [item.get("threshold") for item in thresholds] != THRESHOLDS:
        raise Stage3CBInputError("M3_STAGE3CC_THRESHOLD_FAMILY_MISMATCH")
    if -0.01 in [item.get("threshold") for item in thresholds]:
        raise Stage3CBInputError("M3_STAGE3CC_PRIMARY_THRESHOLD_IN_BH_FAMILY")
    if payload["threshold_robustness"]["bh_q"] != BH_Q:
        raise Stage3CBInputError("M3_STAGE3CC_BH_Q_MISMATCH")
    if payload["extreme_day"].keys() != {"remove_top_1", "remove_top_3"}:
        raise Stage3CBInputError("M3_STAGE3CC_EXTREME_COUNTS_MISMATCH")
    if payload["registered_not_executed"]["leave_one_event_out"] != (
        "NOT_EXECUTED_PREOUTCOME_IMPLEMENTATION_MISSING"
    ):
        raise Stage3CBInputError("M3_STAGE3CC_LEAVE_ONE_EVENT_OUT_EXECUTED")
    if payload["holdout_read"] is not False or payload["development_evidence_level"] is not None:
        raise Stage3CBInputError("M3_STAGE3CC_FORBIDDEN_EVIDENCE_OR_HOLDOUT_STATE")
    if payload["development_evidence_ceiling"] != 2:
        raise Stage3CBInputError("M3_STAGE3CC_EVIDENCE_CEILING_MISMATCH")


def run_registered_robustness(
    *,
    stage3b_root: Path,
    r1_root: Path,
    r4_root: Path,
    output: Path,
    pre_robustness_ci_head: str,
    confirm_pre_robustness_ci_pass: bool,
) -> dict[str, Any]:
    if not confirm_pre_robustness_ci_pass:
        raise Stage3CBInputError("M3_STAGE3CC_PREEXECUTION_CI_CONFIRMATION_REQUIRED")
    if _current_head() != pre_robustness_ci_head:
        raise Stage3CBInputError("M3_STAGE3CC_CI_HEAD_MISMATCH")
    plan = load_execution_plan()
    load_result_schema()
    identity = verify_frozen_lock()
    adapter_digest = verify_adapter_lock()
    if adapter_digest != EXPECTED_ADAPTER_DIGEST:
        raise Stage3CBInputError("M3_STAGE3CC_EXECUTION_ADAPTER_IDENTITY_MISMATCH")

    # This is the read boundary: all plan, schema, identity and CI gates pass.
    print("STAGE3CC_REAL_ROBUSTNESS_READ_BOUNDARY_REACHED")
    locations = locate_known_inputs(stage3b_root, r1_root, r4_root)
    matrix, meta = materialize_analysis_matrix(locations)
    sample, sample_summary = select_locked_development_matrix(matrix)
    manifest_payload = _data_manifest_payload(meta, sample_summary)
    data_manifest_digest = canonical_digest(manifest_payload)
    committed_manifest = load_json(_root() / CB_MANIFEST_PATH)
    if (
        data_manifest_digest != EXPECTED_DATA_MANIFEST_DIGEST
        or committed_manifest.get("data_manifest_digest") != data_manifest_digest
    ):
        raise Stage3CBInputError("M3_STAGE3CC_DATA_MANIFEST_DRIFT")
    anchor = _load_primary_anchor(_root())
    digest, digest_payload = build_robustness_execution_digest(
        data_manifest_digest=data_manifest_digest,
        model_digest=identity["model_digest"],
    )
    run_a = _execute_on_sample(sample, anchor)
    run_b = _execute_on_sample(sample, anchor)
    encoded_a = json.dumps(run_a, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    encoded_b = json.dumps(run_b, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    if encoded_a != encoded_b:
        raise Stage3CBInputError("M3_STAGE3CC_ROBUSTNESS_NONDETERMINISTIC")

    result = {
        "stage": STAGE,
        "canonical_base": CANONICAL_BASE,
        "upstream_inventory_sha": identity["upstream_inventory_sha256"],
        "pipeline_digest": identity["pipeline_digest"],
        "model_digest": identity["model_digest"],
        "execution_adapter_digest": adapter_digest,
        "data_manifest_digest": data_manifest_digest,
        "robustness_execution_digest": digest,
        "robustness_execution_digest_payload": digest_payload,
        "primary_anchor": {
            "nobs": anchor["nobs"],
            "crash_count": anchor["crash_count"],
            "gamma": anchor["gamma"],
            "gamma_ci_lower": anchor["gamma_ci_lower"],
            "gamma_ci_upper": anchor["gamma_ci_upper"],
            "primary_decision": anchor["primary_decision"],
            "reversal_prohibited": True,
        },
        **run_a,
        "registered_not_executed": {
            **plan["not_executed"],
            "alternative_market_proxies_items": [
                "SH_EQUAL_WEIGHT",
                "A_SHARE_EQUAL_WEIGHT",
                "A_SHARE_MEDIAN_RETURN",
                "ADVANCING_STOCK_RATIO",
                "CSI300",
                "SSE50",
            ],
        },
        "development_evidence_ceiling": 2,
        "development_evidence_level": None,
        "evidence_level_status": (
            "NOT_ASSIGNABLE_BECAUSE_DESCRIPTIVE_RELATIONSHIP_CRITERION_NOT_PRELOCKED"
        ),
        "robustness_trigger_status": (
            "NOT_ASSIGNABLE_BECAUSE_ROBUSTNESS_TRIGGER_CRITERION_NOT_PRELOCKED"
        ),
        "holdout_read": False,
        "same_input_ab": {
            "exact_match": True,
            "data_manifest_digest_a": data_manifest_digest,
            "data_manifest_digest_b": data_manifest_digest,
        },
    }
    validate_result_payload(result)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(result, ensure_ascii=False, indent=1, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage3b-root", required=True, type=Path)
    parser.add_argument("--r1-root", required=True, type=Path)
    parser.add_argument("--r4-root", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--pre-robustness-ci-head", required=True)
    parser.add_argument("--confirm-pre-robustness-ci-pass", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        result = run_registered_robustness(
            stage3b_root=args.stage3b_root,
            r1_root=args.r1_root,
            r4_root=args.r4_root,
            output=args.output,
            pre_robustness_ci_head=args.pre_robustness_ci_head,
            confirm_pre_robustness_ci_pass=args.confirm_pre_robustness_ci_pass,
        )
    except (Stage3CBInputError, ValueError) as exc:
        print(str(exc))
        return 1
    print(json.dumps(result["primary_anchor"], ensure_ascii=False, indent=2, sort_keys=True))
    print("M3_STAGE3CC_REGISTERED_ROBUSTNESS_EXECUTION_COMPLETED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
