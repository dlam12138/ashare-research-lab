"""Stage 3D-B frozen primary execution and aggregate evidence writer."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from ashare_research.mechanism.bootstrap import moving_block_bootstrap
from ashare_research.mechanism.crash import add_crash_indicator
from ashare_research.mechanism.model_digest import canonical_digest
from ashare_research.mechanism.regression import fit_primary_ols
from ashare_research.mechanism.source_manifest import canonical_frame_digest
from ashare_research.tools.m3_stage3db_oos_identity import (
    MODEL_DIGEST,
    build_oos_execution_adapter_digest,
)
from ashare_research.tools.m3_stage3db_oos_inputs import (
    HOLDOUT_END,
    HOLDOUT_START,
    WARMUP_START,
    build_oos_analysis_matrix,
)

UPSTREAM = "f206780dcb6fd4c3b9d30a92025b75974284afd16eecd24770d2f812256f0031"
PIPELINE = "ab224492ff85f391a29048dfeec740f9bbffb376de3408a5645a4552b51b9d1b"
DATA_MANIFEST_PATH = "reports/m3_stage3db_oos_analysis_input_manifest_v1.json"
RESULT_PATH = "reports/m3_stage3db_holdout_primary_result_v1.json"
AUTH_PATH = "reports/m3_stage3db_execution_authorization_v1.json"
MARKER_NAME = "holdout_unseal_event.json"
PRIMARY_THRESHOLD = -0.01
BOOTSTRAP_METHOD = "NON_CIRCULAR_OVERLAPPING_MOVING_BLOCK_BOOTSTRAP"


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_oos_matrix(root: Path) -> tuple[pd.DataFrame, dict[str, Any]]:
    normalized = root / "normalized_a"
    target = pd.read_csv(normalized / "target_returns.csv")
    target["trade_date"] = pd.to_datetime(target["trade_date"], errors="raise")
    target["target_analysis_return"] = pd.to_numeric(
        target["target_analysis_return"], errors="coerce"
    )
    target["target_valid"] = target["target_valid"].astype(str).str.lower().eq("true")
    market = pd.read_csv(normalized / "market_ex_target_v2_proxy.csv")
    market["trade_date"] = pd.to_datetime(market["trade_date"], errors="raise")
    oil = pd.read_csv(normalized / "oil_aligned.csv")
    industry = pd.read_csv(normalized / "industry_aligned.csv")
    readiness = pd.read_csv(normalized / "tier1_readiness.csv")
    for frame in (oil, industry, readiness):
        frame[frame.columns[0]] = pd.to_datetime(frame[frame.columns[0]], errors="raise")
    for column in ("market_proxy_valid", "oil_valid", "industry_valid", "tier1_joint_valid"):
        readiness[column] = readiness[column].astype(str).str.lower().eq("true")
    matrix, summary = build_oos_analysis_matrix(target, market, oil, industry, readiness)
    return matrix, summary


def build_oos_data_manifest(root: Path, adapter_digest: str) -> dict[str, Any]:
    matrix, summary = load_oos_matrix(root)
    normalized = root / "normalized_a"
    raw = root / "raw"
    source_paths = sorted(path for path in raw.rglob("*") if path.is_file())
    source_records = []
    for path in source_paths:
        source_records.append(
            {
                "path": path.relative_to(raw).as_posix(),
                "raw_sha256": __import__("hashlib").sha256(path.read_bytes()).hexdigest(),
            }
        )
    files = {
        path.name: canonical_frame_digest(pd.read_csv(path))
        for path in (
            normalized / "target_returns.csv",
            normalized / "market_ex_target_v2_proxy.csv",
            normalized / "oil_aligned.csv",
            normalized / "industry_aligned.csv",
            normalized / "tier1_readiness.csv",
        )
    }
    payload = {
        "stage": "M3_STAGE3DB",
        "holdout_start": HOLDOUT_START.date().isoformat(),
        "holdout_end": HOLDOUT_END.date().isoformat(),
        "warmup_start": WARMUP_START.date().isoformat(),
        "source_identities": {
            "target": "Baostock:sh.601857:qfq:daily",
            "market": "SH_A_SHARE_EQUAL_WEIGHT_EX_601857_V2",
            "oil": "FRED_PUBLIC_GRAPH_CSV:DCOILBRENTEU:underlying EIA",
            "industry": "CNI:399439:国证石油天然气指数",
        },
        "raw_sources": source_records,
        "normalized_logical_sha": files,
        "market_coverage_summary": {
            "coverage_gate": 0.99,
            "rows": int(len(pd.read_csv(normalized / "market_ex_target_v2_proxy.csv"))),
        },
        "joint_readiness_summary": {
            "rows": int(len(pd.read_csv(normalized / "tier1_readiness.csv"))),
            "tier1_valid_count": summary["tier1_valid_count"],
        },
        "target_valid_count": summary["target_valid_count"],
        "tier1_valid_count": summary["tier1_valid_count"],
        "final_nobs": summary["final_nobs"],
        "sample_start": summary["sample_start"],
        "sample_end": summary["sample_end"],
        "canonical_matrix_digest": summary["canonical_matrix_digest"],
        "upstream_inventory_sha": UPSTREAM,
        "pipeline_digest": PIPELINE,
        "model_digest": MODEL_DIGEST,
        "oos_execution_adapter_digest": adapter_digest,
        "holdout_read": True,
        "holdout_extension": False,
    }
    payload["oos_data_manifest_digest"] = canonical_digest(payload)
    return payload


def _primary_once(matrix: pd.DataFrame) -> dict[str, Any]:
    crashed = add_crash_indicator(matrix)
    if len(crashed) == 0 or crashed["Crash_t"].nunique() < 2:
        raise ValueError("M3_STAGE3DB_OOS_NOT_ESTIMABLE_CRASH_CLASSES")
    design = crashed.loc[:, ["const", "market_ex_target_return", "oil_return", "industry_return"]]
    if int(__import__("numpy").linalg.matrix_rank(design.to_numpy(dtype=float))) < design.shape[1]:
        raise ValueError("M3_STAGE3DB_OOS_NOT_ESTIMABLE_DESIGN_RANK")
    fitted = fit_primary_ols(crashed)
    bootstrap = moving_block_bootstrap(
        crashed, replications=5000, seed=20260813, rng_algorithm="PCG64"
    )
    return {
        "alpha": fitted.coefficients["alpha"],
        "beta_market": fitted.coefficients["beta_market"],
        "beta_oil": fitted.coefficients["beta_oil"],
        "beta_industry": fitted.coefficients["beta_industry"],
        "gamma": fitted.gamma,
        "nobs": int(len(crashed)),
        "crash_count": int(crashed["Crash_t"].sum()),
        "block_length": bootstrap.block_length,
        "replications": bootstrap.replications,
        "seed": bootstrap.seed,
        "rng": bootstrap.rng,
        "gamma_ci_lower": bootstrap.gamma_ci_lower,
        "gamma_ci_upper": bootstrap.gamma_ci_upper,
    }


def execute_one_shot(root: Path, external_root: Path) -> dict[str, Any]:
    marker = external_root / MARKER_NAME
    if not marker.is_file():
        raise ValueError("M3_STAGE3DB_UNSEAL_MARKER_REQUIRED")
    auth = _load(root / AUTH_PATH)
    adapter_digest, _ = build_oos_execution_adapter_digest(root)
    if auth.get("oos_execution_adapter_digest") != adapter_digest:
        raise ValueError("M3_STAGE3DB_ADAPTER_IDENTITY_MISMATCH")
    manifest = _load(root / DATA_MANIFEST_PATH)
    matrix, summary = load_oos_matrix(external_root)
    if manifest.get("oos_data_manifest_digest") != canonical_digest(
        {key: value for key, value in manifest.items() if key != "oos_data_manifest_digest"}
    ):
        raise ValueError("M3_STAGE3DB_DATA_MANIFEST_DIGEST_MISMATCH")
    if manifest.get("canonical_matrix_digest") != summary["canonical_matrix_digest"]:
        raise ValueError("M3_STAGE3DB_MATRIX_IDENTITY_MISMATCH")
    run_a = _primary_once(matrix)
    run_b = _primary_once(matrix)
    if json.dumps(run_a, sort_keys=True) != json.dumps(run_b, sort_keys=True):
        raise ValueError("M3_STAGE3DB_OOS_EXECUTION_NONDETERMINISTIC")
    positive = run_a["gamma"] > 0 and run_a["gamma_ci_lower"] > 0
    holdout_decision = "POSITIVE" if positive else "NOT_ESTABLISHED"
    disposition = (
        "M3_DEVELOPMENT_NOT_ESTABLISHED_HOLDOUT_POSITIVE_CROSS_PERIOD_INSTABILITY"
        if positive
        else "M3_DAILY_MECHANISM_NOT_SUPPORTED_ACROSS_DEVELOPMENT_AND_HOLDOUT"
    )
    result = {
        "stage": "M3_STAGE3DB",
        "model_id": "M3_STAGE3DB_PETROCHINA_HOLDOUT_PRIMARY_OLS_V1",
        "upstream_inventory_sha": UPSTREAM,
        "pipeline_digest": PIPELINE,
        "model_digest": MODEL_DIGEST,
        "oos_execution_adapter_digest": adapter_digest,
        "oos_data_manifest_digest": manifest["oos_data_manifest_digest"],
        "sample_start": run_a["nobs"] and summary["sample_start"],
        "sample_end": summary["sample_end"],
        "nobs": run_a["nobs"],
        "crash_threshold": PRIMARY_THRESHOLD,
        "crash_count": run_a["crash_count"],
        "alpha": run_a["alpha"],
        "beta_market": run_a["beta_market"],
        "beta_oil": run_a["beta_oil"],
        "beta_industry": run_a["beta_industry"],
        "gamma": run_a["gamma"],
        "bootstrap_method": BOOTSTRAP_METHOD,
        "block_length": run_a["block_length"],
        "replications": 5000,
        "seed": 20260813,
        "rng": "PCG64",
        "gamma_ci_lower": run_a["gamma_ci_lower"],
        "gamma_ci_upper": run_a["gamma_ci_upper"],
        "holdout_primary_decision": holdout_decision,
        "development_primary_anchor": (
            "M3_PRIMARY_DEVELOPMENT_POSITIVE_ABNORMAL_PERFORMANCE_NOT_ESTABLISHED"
        ),
        "final_disposition": disposition,
        "interpretation_boundary": {
            "development_primary_reversal_allowed": False,
            "causal_interpretation_allowed": False,
            "funding_actor_interpretation_allowed": False,
            "minute_level_auto_escalation_allowed": False,
            "robustness_executed": False,
            "holdout_extension": False,
            "stage3da_case": "B" if positive else "A",
        },
    }
    schema = _load(root / "reports/m3_stage3db_holdout_primary_result_schema_v1.json")
    if set(result) != set(schema["allowed_fields"]):
        raise ValueError("M3_STAGE3DB_RESULT_SCHEMA_FIELDS")
    return result
