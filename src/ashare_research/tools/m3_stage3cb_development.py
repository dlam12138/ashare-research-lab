"""Single frozen Stage 3C-B development-primary execution entrypoint."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any

from ashare_research.mechanism.analysis_contracts import (
    BOOTSTRAP_REPLICATIONS,
    BOOTSTRAP_RNG,
    BOOTSTRAP_SEED,
    contract_path,
    repository_root,
)
from ashare_research.mechanism.bootstrap import moving_block_bootstrap
from ashare_research.mechanism.crash import add_crash_indicator
from ashare_research.mechanism.evidence import primary_decision
from ashare_research.mechanism.model_digest import (
    build_model_digest,
    build_pipeline_digest,
    canonical_digest,
)
from ashare_research.mechanism.regression import fit_primary_ols
from ashare_research.tools.m3_stage3cb_inputs import (
    ADAPTER_DIGEST_ALGORITHM,
    EXPECTED_DIGEST_ALGORITHM,
    EXPECTED_MODEL_DIGEST,
    EXPECTED_PIPELINE_DIGEST,
    EXPECTED_UPSTREAM_INVENTORY_SHA256,
    Stage3CBInputError,
    build_execution_adapter_digest,
    load_json,
    locate_known_inputs,
    materialize_analysis_matrix,
    select_locked_development_matrix,
    validate_execution_mode,
    verify_authorization_contract,
    verify_result_schema,
)

FROZEN_SOURCE_PATHS = tuple(
    repository_root() / "src/ashare_research/mechanism" / name
    for name in (
        "analysis_contracts.py",
        "analysis_dataset.py",
        "crash.py",
        "regression.py",
        "bootstrap.py",
        "robustness.py",
        "evidence.py",
        "model_digest.py",
    )
)
FROZEN_CONTRACT_NAMES = (
    "m3_stage3ca_analysis_pipeline_contract_v2.json",
    "m3_stage3ca_model_specification_v2.json",
    "m3_stage3ca_robustness_registry_v2.json",
    "m3_stage3ca_output_schema_v2.json",
    "m3_stage3car_effective_upstream_sha_inventory_v1.json",
)


def verify_frozen_lock() -> dict[str, str]:
    """Recompute and verify the Stage 3C-A/R2 identity without reading data."""

    pipeline_digest, _ = build_pipeline_digest(FROZEN_SOURCE_PATHS)
    model_digest, _ = build_model_digest(
        pipeline_digest=pipeline_digest,
        contract_paths=[contract_path(name) for name in FROZEN_CONTRACT_NAMES],
        source_paths=FROZEN_SOURCE_PATHS,
        dependency_contract={"statsmodels": ">=0.14.6,<0.15", "numpy_rng": "PCG64"},
        upstream_inventory_path=contract_path(
            "m3_stage3car_effective_upstream_sha_inventory_v1.json"
        ),
    )
    upstream_sha = __import__("hashlib").sha256(
        contract_path("m3_stage3car_effective_upstream_sha_inventory_v1.json").read_bytes()
    ).hexdigest()
    actual = {
        "upstream_inventory_sha256": upstream_sha,
        "pipeline_digest": pipeline_digest,
        "model_digest": model_digest,
        "digest_algorithm": EXPECTED_DIGEST_ALGORITHM,
    }
    expected = {
        "upstream_inventory_sha256": EXPECTED_UPSTREAM_INVENTORY_SHA256,
        "pipeline_digest": EXPECTED_PIPELINE_DIGEST,
        "model_digest": EXPECTED_MODEL_DIGEST,
        "digest_algorithm": EXPECTED_DIGEST_ALGORITHM,
    }
    if actual != expected:
        raise Stage3CBInputError("M3_STAGE3CB_LOCK_IDENTITY_MISMATCH")
    return actual


def verify_adapter_lock() -> str:
    report_path = repository_root() / "reports/m3_stage3cb_execution_adapter_digest_v1.json"
    report = load_json(report_path)
    digest, payload = build_execution_adapter_digest()
    if report.get("adapter_digest") != digest:
        raise Stage3CBInputError("M3_STAGE3CB_EXECUTION_ADAPTER_DIGEST_MISMATCH")
    if report.get("digest_algorithm") != ADAPTER_DIGEST_ALGORITHM:
        raise Stage3CBInputError("M3_STAGE3CB_EXECUTION_ADAPTER_ALGORITHM_MISMATCH")
    for key in ("contract_hashes", "source_hashes", "scope"):
        if report.get(key) != payload.get(key):
            raise Stage3CBInputError(f"M3_STAGE3CB_EXECUTION_ADAPTER_PAYLOAD_MISMATCH:{key}")
    return digest


def _current_head() -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repository_root(),
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise Stage3CBInputError("M3_STAGE3CB_GIT_HEAD_UNAVAILABLE") from exc
    return result.stdout.strip()


def _primary_run(sample) -> dict[str, Any]:
    crashed = add_crash_indicator(sample)
    fitted = fit_primary_ols(crashed)
    boot = moving_block_bootstrap(
        crashed,
        replications=BOOTSTRAP_REPLICATIONS,
        seed=BOOTSTRAP_SEED,
        rng_algorithm=BOOTSTRAP_RNG,
    )
    decision = primary_decision(fitted.gamma, boot.gamma_ci_lower)
    if decision == "PRIMARY_POSITIVE_ABNORMAL_PERFORMANCE_ESTABLISHED":
        primary = "M3_PRIMARY_DEVELOPMENT_POSITIVE_ABNORMAL_PERFORMANCE_ESTABLISHED"
        boundary = (
            "在冻结的 development 样本、冻结的市场/Brent/行业控制和-1% crash 定义下，"
            "中国石油表现出正的受控异常表现，且预注册 moving-block bootstrap 95% CI 下界大于 0。"
            " registered robustness 尚未执行；holdout 尚未读取；不能推断护盘、国家队、政策干预、"
            "资金主体意图或因果关系。"
        )
    else:
        primary = "M3_PRIMARY_DEVELOPMENT_POSITIVE_ABNORMAL_PERFORMANCE_NOT_ESTABLISHED"
        boundary = (
            "冻结的 development primary specification 未建立正的受控异常表现。"
            " registered robustness 尚未执行；holdout 尚未读取；不能推断护盘、国家队、政策干预、"
            "资金主体意图或因果关系。"
        )
    return {
        "alpha": fitted.coefficients["alpha"],
        "beta_market": fitted.coefficients["beta_market"],
        "beta_oil": fitted.coefficients["beta_oil"],
        "beta_industry": fitted.coefficients["beta_industry"],
        "gamma": fitted.coefficients["gamma"],
        "crash_count": int(crashed["Crash_t"].sum()),
        "crash_threshold": -0.01,
        "block_length": boot.block_length,
        "replications": boot.replications,
        "seed": boot.seed,
        "rng": boot.rng,
        "bootstrap_method": "NON_CIRCULAR_OVERLAPPING_MOVING_BLOCK_BOOTSTRAP",
        "gamma_ci_lower": boot.gamma_ci_lower,
        "gamma_ci_upper": boot.gamma_ci_upper,
        "primary_decision": primary,
        "interpretation_boundary": boundary,
    }


def _data_manifest_payload(meta: dict[str, Any], sample_summary: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "1.0.0",
        "stage": "M3_STAGE3CB",
        "holdout_read": False,
        "holdout_status": "SEALED",
        "upstream_inventory_sha256": EXPECTED_UPSTREAM_INVENTORY_SHA256,
        "pipeline_digest": EXPECTED_PIPELINE_DIGEST,
        "model_digest": EXPECTED_MODEL_DIGEST,
        "digest_algorithm": EXPECTED_DIGEST_ALGORITHM,
        "execution_adapter_digest": verify_adapter_lock(),
        "sources": {
            "target": meta["target"],
            "market_proxy": meta["market_proxy"],
            "oil_raw": meta["oil_raw"],
            "oil_aligned": meta["oil_aligned"],
            "industry_raw": meta["industry_raw"],
            "industry_aligned": meta["industry_aligned"],
            "tier1_readiness": meta["tier1_readiness"],
        },
        "sample": sample_summary,
        "canonical_matrix_digest": meta["canonical_matrix_digest"],
        "matrix_join": "EXACT_TRADE_DATE_INNER_JOIN_ONLY",
        "target_valid_count": meta["target_valid_rows"],
        "tier1_valid_count": meta["tier1_joint_valid_rows"],
    }


def run_primary(
    *,
    stage3b_root: Path,
    r1_root: Path,
    r4_root: Path,
    output: Path,
    preexecution_ci_head: str,
    confirm_preexecution_ci_pass: bool,
) -> dict[str, Any]:
    validate_execution_mode("development-primary")
    if not confirm_preexecution_ci_pass:
        raise Stage3CBInputError("M3_STAGE3CB_PREEXECUTION_CI_CONFIRMATION_REQUIRED")
    authorization = verify_authorization_contract()
    verify_result_schema()
    lock = verify_frozen_lock()
    adapter_digest = verify_adapter_lock()
    if _current_head() != preexecution_ci_head:
        raise Stage3CBInputError("M3_STAGE3CB_CI_HEAD_MISMATCH")

    locations = locate_known_inputs(stage3b_root, r1_root, r4_root)
    matrix, meta = materialize_analysis_matrix(locations)
    sample, sample_summary = select_locked_development_matrix(matrix)
    manifest_payload = _data_manifest_payload(meta, sample_summary)
    data_manifest_digest = canonical_digest(manifest_payload)
    manifest = {**manifest_payload, "data_manifest_digest": data_manifest_digest}

    # Same-input A/B is executed against the same immutable in-memory matrix.
    run_a = _primary_run(sample)
    run_b = _primary_run(sample)
    if run_a != run_b:
        raise Stage3CBInputError("M3_STAGE3CB_REAL_EXECUTION_NONDETERMINISTIC")
    primary = {
        "model_id": "M3_STAGE3CB_PETROCHINA_DEVELOPMENT_PRIMARY_OLS_V1",
        "pipeline_digest": lock["pipeline_digest"],
        "model_digest": lock["model_digest"],
        "execution_adapter_digest": adapter_digest,
        "data_manifest_digest": data_manifest_digest,
        "sample_start": sample_summary["sample_start"],
        "sample_end": sample_summary["sample_end"],
        "nobs": sample_summary["final_nobs"],
        **run_a,
        "evidence_level": None,
        "evidence_status": "PENDING_STAGE3CC_REGISTERED_ROBUSTNESS",
    }
    output.mkdir(parents=True, exist_ok=True)
    (output / "analysis_input_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=1, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    (output / "primary_result.json").write_text(
        json.dumps(primary, ensure_ascii=False, indent=1, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    (output / "same_input_ab.json").write_text(
        json.dumps(
            {
                "data_manifest_digest_a": data_manifest_digest,
                "data_manifest_digest_b": data_manifest_digest,
                "model_digest_a": lock["model_digest"],
                "model_digest_b": lock["model_digest"],
                "execution_adapter_digest_a": adapter_digest,
                "execution_adapter_digest_b": adapter_digest,
                "primary_result_a": primary,
                "primary_result_b": primary,
                "exact_match": True,
            },
            ensure_ascii=False,
            indent=1,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return {
        "status": "M3_STAGE3CB_REAL_EXECUTION_COMPLETED",
        "authorization_mode": authorization["execution_mode"],
        "preexecution_ci_head": preexecution_ci_head,
        "outcome_read_boundary": "REAL_OUTCOME_READ_BOUNDARY_REACHED",
        "primary": primary,
        "data_manifest": manifest,
        "same_input_ab": {"exact_match": True, "data_manifest_digest": data_manifest_digest},
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execution-mode", required=True, choices=["development-primary"])
    parser.add_argument("--stage3b-root", required=True, type=Path)
    parser.add_argument("--r1-root", required=True, type=Path)
    parser.add_argument("--r4-root", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--preexecution-ci-head", required=True)
    parser.add_argument("--confirm-preexecution-ci-pass", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        result = run_primary(
            stage3b_root=args.stage3b_root,
            r1_root=args.r1_root,
            r4_root=args.r4_root,
            output=args.output,
            preexecution_ci_head=args.preexecution_ci_head,
            confirm_preexecution_ci_pass=args.confirm_preexecution_ci_pass,
        )
    except (Stage3CBInputError, ValueError) as exc:
        print(str(exc))
        return 1
    print(json.dumps(result["primary"], ensure_ascii=False, indent=2, sort_keys=True))
    print(result["status"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
