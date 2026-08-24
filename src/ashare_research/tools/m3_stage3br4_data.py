"""M3 Stage 3B-R4 bounded source acquisition and structural Tier-1 readiness only."""

from __future__ import annotations

import argparse
import ast
import json
import shutil
from pathlib import Path
from typing import Any

import pandas as pd

from ashare_research.mechanism.acquisition_cni import (
    CNI_INDEX_CODE,
    CNI_INDEX_NAME,
    CNI_PUBLISHER,
    acquire_cni_bounded,
    build_cni_returns,
    inspect_akshare_cni_source,
    normalize_cni,
    prove_cni_bounded_raw_response,
)
from ashare_research.mechanism.acquisition_fred_public import (
    FRED_SERIES,
    FRED_SERIES_NAME,
    FRED_UNDERLYING_SOURCE,
    acquire_fred_bounded,
    normalize_fred,
)
from ashare_research.mechanism.acquisition_fred_public import (
    prove_bounded_raw_response as prove_fred_bounded_raw_response,
)
from ashare_research.mechanism.alignment import build_tier1_readiness, summarize_readiness
from ashare_research.mechanism.contracts import (
    assert_no_restricted_research_outputs,
    sha256_file,
)
from ashare_research.mechanism.oil import align_oil_to_a_share
from ashare_research.mechanism.source_manifest import canonical_frame_digest

WARMUP_START = "2014-12-01"
DEVELOPMENT_START = "2015-01-01"
DEVELOPMENT_END = "2022-12-31"
HOLDOUT_START = "2023-01-01"
R1_PROXY = "SH_A_SHARE_EQUAL_WEIGHT_EX_601857_V2"


def _write_csv(path: Path, frame: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False, lineterminator="\n")


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    assert_no_restricted_research_outputs(payload)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=1, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def reuse_r1_market_proxy(external_root: Path, market_root: Path, label: str) -> dict[str, Any]:
    """Copy only the trusted R1 normalized proxy/calendar; never reacquire the market data."""
    source_root = market_root / "normalized_a"
    destination_root = external_root / f"normalized_{label}"
    required = ("trade_calendar.csv", "market_ex_target_v2_proxy.csv")
    for name in required:
        source = source_root / name
        if not source.is_file():
            raise FileNotFoundError(f"R1 trusted market proxy file missing: {source}")
        shutil.copyfile(source, destination_root / name)
    proxy = pd.read_csv(destination_root / "market_ex_target_v2_proxy.csv", dtype=str)
    return {
        "implementation_id": R1_PROXY,
        "status": "TRUSTED_REUSED",
        "rows": int(len(proxy)),
        "logical_sha256": canonical_frame_digest(proxy),
        "source_root": str(source_root),
    }


def normalize_inputs(external_root: Path, label: str, market_root: Path) -> dict[str, Any]:
    root = external_root.resolve()
    normalized = root / f"normalized_{label}"
    oil = normalize_fred(
        root / "raw" / "fred_DCOILBRENTEU.csv",
        normalized / "oil_brent_observations.csv",
        start=WARMUP_START,
        end=DEVELOPMENT_END,
    )
    industry = normalize_cni(
        root / "raw" / "cni_399439_response.json",
        normalized / "industry_399439.csv",
        start=WARMUP_START,
        end=DEVELOPMENT_END,
    )
    market = reuse_r1_market_proxy(root, market_root.resolve(), label)
    return {"oil": oil, "industry": industry, "market_proxy": market, "label": label}


def align_inputs(external_root: Path, label: str) -> dict[str, Any]:
    root = external_root.resolve()
    normalized = root / f"normalized_{label}"
    calendar = pd.read_csv(normalized / "trade_calendar.csv", dtype=str)["trade_date"]
    oil = align_oil_to_a_share(
        pd.read_csv(normalized / "oil_brent_observations.csv", dtype=str), calendar
    )
    industry = build_cni_returns(
        pd.read_csv(normalized / "industry_399439.csv", dtype=str), calendar
    )
    proxy = pd.read_csv(normalized / "market_ex_target_v2_proxy.csv", dtype=str)
    readiness = build_tier1_readiness(proxy, oil, industry)
    _write_csv(normalized / "oil_aligned.csv", oil)
    _write_csv(normalized / "industry_aligned.csv", industry)
    _write_csv(normalized / "tier1_readiness.csv", readiness)
    return {
        "label": label,
        "oil_valid_rows": int(oil["alignment_status"].eq("OIL_ROW_OK").sum()),
        "oil_gap_rows": int(oil["alignment_status"].ne("OIL_ROW_OK").sum()),
        "industry_valid_rows": int(industry["alignment_status"].eq("INDUSTRY_ROW_OK").sum()),
        "industry_gap_rows": int(industry["alignment_status"].ne("INDUSTRY_ROW_OK").sum()),
        "readiness": summarize_readiness(readiness),
    }


def _read_optional(path: Path) -> pd.DataFrame | None:
    return pd.read_csv(path, dtype=str) if path.is_file() else None


def _restore_readiness_types(readiness: pd.DataFrame) -> pd.DataFrame:
    """Restore structural list/bool fields after a CSV round-trip."""
    for column in ("market_proxy_valid", "oil_valid", "industry_valid", "tier1_joint_valid"):
        readiness[column] = readiness[column].eq("True")
    if "invalid_reason_codes" in readiness.columns:
        readiness["invalid_reason_codes"] = readiness["invalid_reason_codes"].map(
            lambda value: ast.literal_eval(value) if isinstance(value, str) else value
        )
    return readiness


def _date_range(frame: pd.DataFrame | None, column: str) -> dict[str, str | None]:
    if frame is None or frame.empty:
        return {"first": None, "last": None}
    dates = pd.to_datetime(frame[column], errors="coerce").dropna()
    return {
        "first": dates.min().date().isoformat() if not dates.empty else None,
        "last": dates.max().date().isoformat() if not dates.empty else None,
    }


def _ab_digests(root: Path, filenames: tuple[str, ...]) -> dict[str, dict[str, str]]:
    result: dict[str, dict[str, str]] = {}
    for name in filenames:
        left, right = (
            _read_optional(root / "normalized_a" / name),
            _read_optional(root / "normalized_b" / name),
        )
        if left is not None and right is not None:
            result[name] = {"a": canonical_frame_digest(left), "b": canonical_frame_digest(right)}
    return result


def generate_reports(external_root: Path, repo_root: Path, label: str = "a") -> dict[str, Any]:
    """Write the R4 provenance/coverage/readiness reports; never write research results."""
    root = external_root.resolve()
    normalized = root / f"normalized_{label}"
    oil_raw_path = root / "raw" / "fred_DCOILBRENTEU.csv"
    cni_raw_path = root / "raw" / "cni_399439_response.json"
    oil = _read_optional(normalized / "oil_brent_observations.csv")
    industry = _read_optional(normalized / "industry_399439.csv")
    oil_aligned = _read_optional(normalized / "oil_aligned.csv")
    industry_aligned = _read_optional(normalized / "industry_aligned.csv")
    readiness = _read_optional(normalized / "tier1_readiness.csv")
    if readiness is not None:
        readiness = _restore_readiness_types(readiness)
    oil_valid = (
        int(oil_aligned["alignment_status"].eq("OIL_ROW_OK").sum())
        if oil_aligned is not None
        else 0
    )
    industry_valid = (
        int(industry_aligned["alignment_status"].eq("INDUSTRY_ROW_OK").sum())
        if industry_aligned is not None
        else 0
    )
    joint_valid = (
        int(readiness["tier1_joint_valid"].astype(str).eq("True").sum())
        if readiness is not None
        else 0
    )
    oil_bounded_proof = (
        prove_fred_bounded_raw_response(oil_raw_path.read_bytes(), end=DEVELOPMENT_END)
        if oil_raw_path.is_file()
        else None
    )
    industry_bounded_proof = (
        prove_cni_bounded_raw_response(cni_raw_path.read_bytes(), end=DEVELOPMENT_END)
        if cni_raw_path.is_file()
        else None
    )
    max_anchor_age = None
    if oil_aligned is not None:
        ages = pd.to_numeric(oil_aligned["oil_anchor_age_days"], errors="coerce").dropna()
        max_anchor_age = int(ages.max()) if not ages.empty else None
    ab_digests = _ab_digests(
        root,
        (
            "oil_brent_observations.csv",
            "industry_399439.csv",
            "oil_aligned.csv",
            "industry_aligned.csv",
            "tier1_readiness.csv",
        ),
    )
    oil_trusted = oil is not None and oil_valid > 0
    industry_trusted = industry is not None and industry_valid > 0
    joint_summary = (
        summarize_readiness(readiness)
        if readiness is not None
        else {
            "total_trading_dates": 0,
            "market_proxy_valid_dates": 0,
            "oil_valid_dates": 0,
            "industry_valid_dates": 0,
            "joint_tier1_valid_dates": 0,
            "first_joint_valid_date": None,
            "last_joint_valid_date": None,
            "gap_dates": 0,
            "gap_reason_counts": {},
        }
    )
    source_registry = {
        "schema_version": "1.0.0",
        "stage": "M3_STAGE3BR4",
        "holdout_status": "SEALED",
        "holdout_read_performed": False,
        "oil": {
            "series": FRED_SERIES,
            "source_name": FRED_SERIES_NAME,
            "underlying_source": FRED_UNDERLYING_SOURCE,
            "transport": "FRED_PUBLIC_GRAPH_CSV",
            "credential_required": False,
            "status": "TRUSTED" if oil_trusted else "NOT_ACQUIRED",
            "raw_sha256": sha256_file(oil_raw_path) if oil_raw_path.is_file() else None,
            "bounded_proof": oil_bounded_proof,
            "raw_date_range": _date_range(oil, "observation_date"),
        },
        "industry": {
            "index_code": CNI_INDEX_CODE,
            "source_name": CNI_INDEX_NAME,
            "publisher": CNI_PUBLISHER,
            "transport": "CNI_OFFICIAL_BOUNDED_ENDPOINT",
            "status": "TRUSTED" if industry_trusted else "NOT_ACQUIRED",
            "raw_sha256": sha256_file(cni_raw_path) if cni_raw_path.is_file() else None,
            "bounded_proof": industry_bounded_proof,
            "source_inspection": inspect_akshare_cni_source(),
            "raw_date_range": _date_range(industry, "trade_date"),
        },
        "market_proxy": {"implementation_id": R1_PROXY, "status": "TRUSTED_REUSED"},
        "shenwan_status": "M3_SHENWAN_INDUSTRY_CONTROL_DEFERRED_NON_BLOCKING",
        "stage3c_status": "M3_STAGE3C_REAL_ANALYSIS_NOT_AUTHORIZED",
    }
    coverage = {
        "schema_version": "1.0.0",
        "stage": "M3_STAGE3BR4",
        "holdout_status": "SEALED",
        "holdout_read_performed": False,
        "oil": {
            "status": "TRUSTED" if oil_trusted else "NOT_ACQUIRED",
            "raw_rows": int(len(oil)) if oil is not None else 0,
            "normalized_rows": int(len(oil)) if oil is not None else 0,
            "aligned_valid_rows": oil_valid,
            "aligned_gap_rows": int(len(oil_aligned) - oil_valid) if oil_aligned is not None else 0,
            "raw_sha256": sha256_file(oil_raw_path) if oil_raw_path.is_file() else None,
            "raw_date_range": _date_range(oil, "observation_date"),
            "max_anchor_age_calendar_days": max_anchor_age,
            "ab_digest": ab_digests.get("oil_aligned.csv"),
        },
        "industry_399439": {
            "status": "TRUSTED" if industry_trusted else "NOT_ACQUIRED",
            "raw_rows": int(len(industry)) if industry is not None else 0,
            "normalized_rows": int(len(industry)) if industry is not None else 0,
            "aligned_valid_rows": industry_valid,
            "aligned_gap_rows": int(len(industry_aligned) - industry_valid)
            if industry_aligned is not None
            else 0,
            "raw_sha256": sha256_file(cni_raw_path) if cni_raw_path.is_file() else None,
            "raw_date_range": _date_range(industry, "trade_date"),
            "ab_digest": ab_digests.get("industry_aligned.csv"),
        },
        "market_proxy": {
            "implementation_id": R1_PROXY,
            "status": "TRUSTED_REUSED",
            "valid_rows": 1902,
            "gap_rows": 68,
        },
        "joint": {"status": "READY" if joint_valid else "NOT_READY", **joint_summary},
        "offline_ab_digests": ab_digests,
        "stage3c_status": "M3_STAGE3C_REAL_ANALYSIS_NOT_AUTHORIZED",
    }
    readiness_report = {
        "schema_version": "1.0.0",
        "stage": "M3_STAGE3BR4",
        "holdout_status": "SEALED",
        "holdout_read_performed": False,
        "market_proxy": "TRUSTED_REUSED_R1",
        "oil": "M3_OIL_CONTROL_V3_TRUSTED" if oil_trusted else "M3_STAGE3BR4_OIL_INPUT_GAP",
        "industry_399439": "M3_CNI_OIL_GAS_INDUSTRY_CONTROL_V2_TRUSTED"
        if industry_trusted
        else "M3_STAGE3BR4_INDUSTRY_INPUT_GAP",
        "joint_tier1": "M3_TIER1_DEVELOPMENT_INPUTS_READY"
        if joint_valid
        else "M3_TIER1_DEVELOPMENT_INPUTS_NOT_READY",
        "coverage": joint_summary,
        "stage3c_pipeline_lock": "M3_STAGE3CA_PIPELINE_LOCK_IMPLEMENTATION_ALLOWED"
        if joint_valid
        else "M3_STAGE3C_NOT_ALLOWED",
        "stage3c_real_analysis": "M3_STAGE3C_REAL_ANALYSIS_NOT_AUTHORIZED",
        "decision": "STOP_FOR_NORTH_STAR_REVIEW",
    }
    joint_manifest = {
        "schema_version": "1.0.0",
        "stage": "M3_STAGE3BR4",
        "holdout_status": "SEALED",
        "holdout_read_performed": False,
        "inputs": {
            "market_proxy": {"implementation_id": R1_PROXY, "status": "TRUSTED_REUSED"},
            "oil": {
                "series": FRED_SERIES,
                "status": "TRUSTED" if oil_trusted else "NOT_ACQUIRED",
                "raw_sha256": sha256_file(oil_raw_path) if oil_raw_path.is_file() else None,
            },
            "industry": {
                "index_code": CNI_INDEX_CODE,
                "status": "TRUSTED" if industry_trusted else "NOT_ACQUIRED",
                "raw_sha256": sha256_file(cni_raw_path) if cni_raw_path.is_file() else None,
            },
        },
        "readiness": "READY" if joint_valid else "NOT_READY",
        "joint_summary": joint_summary,
        "no_holdout_rows": True,
        "stage3c_status": "M3_STAGE3C_REAL_ANALYSIS_NOT_AUTHORIZED",
    }
    development_manifest = {
        "schema_version": "1.0.0",
        "stage": "M3_STAGE3BR4",
        "development_window": {
            "warmup_start": WARMUP_START,
            "development_start": DEVELOPMENT_START,
            "development_end": DEVELOPMENT_END,
        },
        "holdout_status": "SEALED",
        "holdout_read_performed": False,
        "market_proxy": {"implementation_id": R1_PROXY, "status": "TRUSTED_REUSED"},
        "oil": {
            "series": FRED_SERIES,
            "status": "TRUSTED" if oil_trusted else "NOT_ACQUIRED",
            "raw_sha256": sha256_file(oil_raw_path) if oil_raw_path.is_file() else None,
            "ab_digest": canonical_frame_digest(oil) if oil is not None else None,
            "bounded_proof": oil_bounded_proof,
        },
        "industry": {
            "index_code": CNI_INDEX_CODE,
            "status": "TRUSTED" if industry_trusted else "NOT_ACQUIRED",
            "raw_sha256": sha256_file(cni_raw_path) if cni_raw_path.is_file() else None,
            "ab_digest": canonical_frame_digest(industry) if industry is not None else None,
            "bounded_proof": industry_bounded_proof,
        },
        "offline_ab_digests": ab_digests,
        "raw_data_committed_to_git": False,
        "restricted_research_outputs": False,
        "stage3c_status": "M3_STAGE3C_REAL_ANALYSIS_NOT_AUTHORIZED",
    }
    reports = {
        "m3_stage3br4_source_registry_v1.json": source_registry,
        "m3_stage3br4_data_coverage_v1.json": coverage,
        "m3_stage3br4_tier1_readiness_v3.json": readiness_report,
        "m3_stage3br4_development_input_manifest_v1.json": development_manifest,
        "m3_stage3br4_joint_input_manifest_v1.json": joint_manifest,
    }
    for name, payload in reports.items():
        _write_json(Path(repo_root) / "reports" / name, payload)
    return {
        "reports": sorted(reports),
        "joint_valid_rows": joint_valid,
        "oil_trusted": oil_trusted,
        "industry_trusted": industry_trusted,
    }


def run_ab_identity(external_root: Path) -> dict[str, Any]:
    a = external_root / "normalized_a"
    b = external_root / "normalized_b"
    files = (
        "oil_brent_observations.csv",
        "industry_399439.csv",
        "oil_aligned.csv",
        "industry_aligned.csv",
        "tier1_readiness.csv",
    )
    digests: dict[str, dict[str, str]] = {}
    for name in files:
        left, right = _read_optional(a / name), _read_optional(b / name)
        if left is None or right is None:
            raise FileNotFoundError(f"A/B output missing: {name}")
        digests[name] = {"a": canonical_frame_digest(left), "b": canonical_frame_digest(right)}
        if digests[name]["a"] != digests[name]["b"]:
            raise ValueError(f"offline A/B digest mismatch: {name}")
    return {"status": "OFFLINE_AB_IDENTICAL", "digests": digests}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command",
        choices=[
            "probe-oil",
            "acquire-oil",
            "probe-industry",
            "acquire-industry",
            "normalize",
            "align",
            "readiness",
            "reports",
            "run",
        ],
    )
    parser.add_argument("--external-root", required=True, type=Path)
    parser.add_argument("--market-root", type=Path)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--label", choices=["a", "b"], default="a")
    args = parser.parse_args(argv)
    root = args.external_root.resolve()
    if args.command in {"probe-oil", "acquire-oil"}:
        result = acquire_fred_bounded(root, start=WARMUP_START, end=DEVELOPMENT_END)
    elif args.command in {"probe-industry", "acquire-industry"}:
        result = acquire_cni_bounded(root, start=WARMUP_START, end=DEVELOPMENT_END)
    elif args.command == "normalize":
        if args.market_root is None:
            parser.error("--market-root is required for normalize")
        result = normalize_inputs(root, args.label, args.market_root)
    elif args.command == "align":
        result = align_inputs(root, args.label)
    elif args.command == "readiness":
        readiness = pd.read_csv(
            root / f"normalized_{args.label}" / "tier1_readiness.csv", dtype=str
        )
        readiness = _restore_readiness_types(readiness)
        result = summarize_readiness(readiness)
    elif args.command == "reports":
        result = generate_reports(root, args.repo_root, args.label)
    else:
        if args.market_root is None:
            parser.error("--market-root is required for run")
        acquire_fred_bounded(root, start=WARMUP_START, end=DEVELOPMENT_END)
        acquire_cni_bounded(root, start=WARMUP_START, end=DEVELOPMENT_END)
        normalize_inputs(root, "a", args.market_root)
        align_inputs(root, "a")
        normalize_inputs(root, "b", args.market_root)
        align_inputs(root, "b")
        result = {
            "a_b": run_ab_identity(root),
            "reports": generate_reports(root, args.repo_root, "a"),
        }
    print(json.dumps(result, ensure_ascii=False, indent=1, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
