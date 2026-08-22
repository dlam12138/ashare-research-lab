"""Immutable Stage 3C-B input locator and analysis-matrix materializer.

This adapter is deliberately separate from the frozen Stage 3C-A mechanism
implementation. It accepts only explicitly supplied, previously registered
external capsule roots, verifies bytes before parsing, rejects holdout tokens,
and constructs only the ten-column pre-model analysis matrix. It never creates
``Crash_t`` or any inference result.
"""

from __future__ import annotations

import hashlib
import io
import json
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

import pandas as pd

from ashare_research.mechanism.analysis_contracts import (
    ANALYSIS_COLUMNS,
    DEVELOPMENT_END,
    DEVELOPMENT_START,
    HOLDOUT_START,
    repository_root,
)
from ashare_research.mechanism.analysis_dataset import select_development_sample
from ashare_research.mechanism.contracts import sha256_file
from ashare_research.mechanism.normalization import normalize_daily_observations
from ashare_research.mechanism.source_manifest import canonical_frame_digest

ADAPTER_DIGEST_ALGORITHM = "M3_REPOSITORY_RELATIVE_EXECUTION_ADAPTER_DIGEST_V1"
AUTHORIZATION_CONTRACT = "m3_stage3cb_execution_authorization_v1.json"
RESULT_SCHEMA_CONTRACT = "m3_stage3cb_primary_result_schema_v1.json"
ADAPTER_SOURCE_PATHS = (
    "src/ashare_research/tools/m3_stage3cb_inputs.py",
    "src/ashare_research/tools/m3_stage3cb_development.py",
)
ADAPTER_CONTRACT_PATHS = (
    "reports/m3_stage3cb_execution_authorization_v1.json",
    "reports/m3_stage3cb_primary_result_schema_v1.json",
)
EXPECTED_UPSTREAM_INVENTORY_SHA256 = (
    "f206780dcb6fd4c3b9d30a92025b75974284afd16eecd24770d2f812256f0031"
)
EXPECTED_PIPELINE_DIGEST = (
    "ab224492ff85f391a29048dfeec740f9bbffb376de3408a5645a4552b51b9d1b"
)
EXPECTED_MODEL_DIGEST = (
    "4958351a5c79c0eb96bbfda9ebaaca5e71ab2b07236eaa808b0a92ebc6e9756d"
)
EXPECTED_DIGEST_ALGORITHM = "M3_REPOSITORY_RELATIVE_DIGEST_V2"
EXPECTED_TARGET_RAW_SHA256 = (
    "e5700ddfa965db80efd12188b8529c3d5f6f42fdfeabe08135e0663a106b2ee2"
)
EXPECTED_TARGET_LOGICAL_SHA256 = (
    "c0485b55e07551a1a98c1f4cd33f3791814b6c3df6c1351d4ca634a97eebb1ab"
)
EXPECTED_MARKET_PROXY = "SH_A_SHARE_EQUAL_WEIGHT_EX_601857_V2"
EXPECTED_MARKET_ROWS = 1970
EXPECTED_MARKET_VALID_ROWS = 1902
EXPECTED_MARKET_GAP_ROWS = 68
EXPECTED_OIL_RAW_SHA256 = (
    "185080c6937d09b1dc3a2db46746a8e9bbdac5d17d8165596e9211fcc45e2d53"
)
EXPECTED_OIL_ALIGNED_DIGEST = (
    "1de98bf258b2a21090b46b179485dace61fc9b3027587b61a652970e1e20e5f7"
)
EXPECTED_INDUSTRY_RAW_SHA256 = (
    "c80a609c6dc1ff461b6010f0b1ebcd2230095f466af4f257be91d74faf9afee6"
)
EXPECTED_INDUSTRY_ALIGNED_DIGEST = (
    "a0bb7fa659f56e5f325f09b112d62443e26391b7d961b193689cff56172a6567"
)
EXPECTED_TIER1_READINESS_DIGEST = (
    "801e877568d83021e71ebafe977e6b26d571155c2f61c6ca8f8ee265f90e264c"
)
_DATE_TOKEN = re.compile(rb"(?<!\d)(20\d{2})[-/]?(\d{2})[-/]?(\d{2})(?!\d)")


class Stage3CBInputError(ValueError):
    """Raised when a Stage 3C-B input or adapter contract is invalid."""


@dataclass(frozen=True)
class InputLocations:
    stage3b_root: Path
    r1_root: Path
    r4_root: Path
    target_raw: Path
    market_proxy: Path
    oil_raw: Path
    oil_aligned: Path
    industry_raw: Path
    industry_aligned: Path
    tier1_readiness: Path


def _canonical_digest(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _repository_relative(path: Path) -> str:
    root = repository_root().resolve()
    resolved = path.resolve()
    try:
        return resolved.relative_to(root).as_posix()
    except ValueError as exc:
        raise Stage3CBInputError("EXECUTION_ADAPTER_PATH_OUTSIDE_REPOSITORY") from exc


def build_execution_adapter_digest() -> tuple[str, dict[str, Any]]:
    """Build an adapter-only digest from logical repository paths and exact bytes."""

    root = repository_root()
    source_hashes = {
        _repository_relative(root / path): sha256_file(root / path)
        for path in ADAPTER_SOURCE_PATHS
    }
    contract_hashes = {
        _repository_relative(root / path): sha256_file(root / path)
        for path in ADAPTER_CONTRACT_PATHS
    }
    payload = {
        "digest_algorithm": ADAPTER_DIGEST_ALGORITHM,
        "scope": (
            "stage3cb_authorization,primary_result_schema,known_input_locator,"
            "matrix_materializer,cli"
        ),
        "contract_hashes": contract_hashes,
        "source_hashes": source_hashes,
    }
    return _canonical_digest(payload), payload


def write_execution_adapter_digest_report(destination: Path) -> dict[str, Any]:
    digest, payload = build_execution_adapter_digest()
    report = {
        "adapter_digest": digest,
        "digest_algorithm": ADAPTER_DIGEST_ALGORITHM,
        "schema_version": "1.0.0",
        "stage": "M3_STAGE3CB",
        "status": "LOCKED_PRE_EXECUTION",
        **payload,
    }
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(report, ensure_ascii=False, indent=1, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return report


def load_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise Stage3CBInputError(f"invalid JSON contract: {path}") from exc
    if not isinstance(payload, dict):
        raise Stage3CBInputError(f"JSON contract must be an object: {path}")
    return payload


def verify_authorization_contract(root: Path | None = None) -> dict[str, Any]:
    repo = (root or repository_root()).resolve()
    contract = load_json(repo / "reports" / AUTHORIZATION_CONTRACT)
    expected = {
        "contract_id": "M3_STAGE3CB_EXECUTION_AUTHORIZATION_V1",
        "stage": "M3_STAGE3CB",
        "execution_mode": "DEVELOPMENT_PRIMARY_ONLY",
        "status": "PRE_EXECUTION_LOCK",
        "canonical_base": "ef1d1fab4b93ed680004430d72e49c27cb5e874e",
        "upstream_inventory_sha256": EXPECTED_UPSTREAM_INVENTORY_SHA256,
        "pipeline_digest": EXPECTED_PIPELINE_DIGEST,
        "model_digest": EXPECTED_MODEL_DIGEST,
        "digest_algorithm": EXPECTED_DIGEST_ALGORITHM,
        "development_start": "2015-03-16",
        "development_end": "2022-12-30",
        "holdout_start": "2023-01-01",
        "robustness_allowed": False,
        "holdout_allowed": False,
    }
    for key, value in expected.items():
        if contract.get(key) != value:
            raise Stage3CBInputError(f"M3_STAGE3CB_AUTHORIZATION_MISMATCH:{key}")
    if contract.get("primary_crash_threshold") != -0.01:
        raise Stage3CBInputError("M3_STAGE3CB_AUTHORIZATION_MISMATCH:threshold")
    if contract.get("bootstrap") != {
        "replications": 5000,
        "rng": "PCG64",
        "seed": 20260813,
        "ci": "PERCENTILE_2_5_97_5",
    }:
        raise Stage3CBInputError("M3_STAGE3CB_AUTHORIZATION_MISMATCH:bootstrap")
    return contract


def verify_result_schema(root: Path | None = None) -> dict[str, Any]:
    repo = (root or repository_root()).resolve()
    schema = load_json(repo / "reports" / RESULT_SCHEMA_CONTRACT)
    if schema.get("contract_id") != "M3_STAGE3CB_PRIMARY_RESULT_SCHEMA_V1":
        raise Stage3CBInputError("M3_STAGE3CB_RESULT_SCHEMA_MISMATCH")
    if schema.get("evidence_status") != "PENDING_STAGE3CC_REGISTERED_ROBUSTNESS":
        raise Stage3CBInputError("M3_STAGE3CB_RESULT_SCHEMA_MISMATCH:evidence_status")
    if schema.get("value_constraints", {}).get("evidence_level", "missing") is not None:
        raise Stage3CBInputError("M3_STAGE3CB_RESULT_SCHEMA_MISMATCH:evidence_level")
    return schema


def _safe_child(root: Path, relative: str) -> Path:
    rel = Path(relative)
    if rel.is_absolute() or not rel.parts:
        raise Stage3CBInputError("INPUT_LOCATOR_PATH_NOT_RELATIVE")
    candidate = (root.resolve() / rel).resolve()
    try:
        candidate.relative_to(root.resolve())
    except ValueError as exc:
        raise Stage3CBInputError("INPUT_LOCATOR_PATH_ESCAPES_ROOT") from exc
    return candidate


def _manifest_dataset(manifest: dict[str, Any], dataset_id: str) -> dict[str, Any]:
    for entry in manifest.get("datasets", []):
        if entry.get("dataset_id") == dataset_id:
            return entry
    raise Stage3CBInputError(f"manifest dataset missing: {dataset_id}")


def locate_known_inputs(
    stage3b_root: Path,
    r1_root: Path,
    r4_root: Path,
) -> InputLocations:
    """Resolve only the three registered external capsule roots; never scan disk."""

    repo = repository_root()
    stage3b_manifest = load_json(repo / "reports/m3_stage3b_development_input_manifest_v1.json")
    target = _manifest_dataset(stage3b_manifest, "target_daily_qfq")
    if target.get("raw_file_path") != "baostock/601857_SH_qfq.csv":
        raise Stage3CBInputError("TARGET_MANIFEST_IDENTITY_MISMATCH")

    r1_coverage = load_json(repo / "reports/m3_stage3br1_data_coverage_v1.json")
    proxy = r1_coverage.get("market_ex_target_v2", {})
    if (
        proxy.get("instrument_id") != EXPECTED_MARKET_PROXY
        or proxy.get("rows") != EXPECTED_MARKET_ROWS
        or proxy.get("ok_rows") != EXPECTED_MARKET_VALID_ROWS
        or proxy.get("gap_rows") != EXPECTED_MARKET_GAP_ROWS
    ):
        raise Stage3CBInputError("MARKET_PROXY_MANIFEST_IDENTITY_MISMATCH")

    r4_manifest = load_json(repo / "reports/m3_stage3br4_development_input_manifest_v1.json")
    if (
        r4_manifest.get("oil", {}).get("raw_sha256") != EXPECTED_OIL_RAW_SHA256
        or r4_manifest.get("industry", {}).get("raw_sha256") != EXPECTED_INDUSTRY_RAW_SHA256
        or r4_manifest.get("oil", {}).get("bounded_proof", {}).get("raw_date_scan") != "PASSED"
        or r4_manifest.get("industry", {}).get("bounded_proof", {}).get("raw_date_scan")
        != "PASSED"
    ):
        raise Stage3CBInputError("R4_MANIFEST_IDENTITY_MISMATCH")
    if (
        r4_manifest.get("offline_ab_digests", {}).get("oil_aligned.csv", {}).get("a")
        != EXPECTED_OIL_ALIGNED_DIGEST
    ):
        raise Stage3CBInputError("R4_OIL_ALIGNED_IDENTITY_MISMATCH")
    if (
        r4_manifest.get("offline_ab_digests", {}).get("industry_aligned.csv", {}).get("a")
        != EXPECTED_INDUSTRY_ALIGNED_DIGEST
    ):
        raise Stage3CBInputError("R4_INDUSTRY_ALIGNED_IDENTITY_MISMATCH")
    if (
        r4_manifest.get("offline_ab_digests", {}).get("tier1_readiness.csv", {}).get("a")
        != EXPECTED_TIER1_READINESS_DIGEST
    ):
        raise Stage3CBInputError("R4_TIER1_READINESS_IDENTITY_MISMATCH")

    stage3b = stage3b_root.resolve()
    r1 = r1_root.resolve()
    r4 = r4_root.resolve()
    return InputLocations(
        stage3b_root=stage3b,
        r1_root=r1,
        r4_root=r4,
        target_raw=_safe_child(stage3b, target["raw_file_path"]),
        market_proxy=_safe_child(r1, "normalized_a/market_ex_target_v2_proxy.csv"),
        oil_raw=_safe_child(r4, "raw/fred_DCOILBRENTEU.csv"),
        oil_aligned=_safe_child(r4, "normalized_a/oil_aligned.csv"),
        industry_raw=_safe_child(r4, "raw/cni_399439_response.json"),
        industry_aligned=_safe_child(r4, "normalized_a/industry_aligned.csv"),
        tier1_readiness=_safe_child(r4, "normalized_a/tier1_readiness.csv"),
    )


def _scan_raw_dates(raw: bytes, label: str) -> dict[str, Any]:
    dates: list[str] = []
    for year, month, day in _DATE_TOKEN.findall(raw):
        try:
            value = date(int(year), int(month), int(day))
        except ValueError:
            continue
        dates.append(value.isoformat())
        if value >= HOLDOUT_START:
            raise Stage3CBInputError(f"HOLDOUT_RAW_DATE_REJECTED:{label}:{value.isoformat()}")
    return {
        "date_token_count": len(dates),
        "date_min": min(dates) if dates else None,
        "date_max": max(dates) if dates else None,
        "holdout_scan": "PASSED",
    }


def _read_hash_first(
    path: Path, expected_sha256: str | None, label: str
) -> tuple[bytes, str, dict[str, Any]]:
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise Stage3CBInputError(f"INPUT_LOCATOR_MISSING:{label}") from exc
    actual = hashlib.sha256(raw).hexdigest()
    if expected_sha256 is not None and actual != expected_sha256:
        raise Stage3CBInputError(f"REAL_INPUT_HASH_MISMATCH:{label}")
    proof = _scan_raw_dates(raw, label)
    return raw, actual, proof


def _parse_csv(raw: bytes, label: str) -> pd.DataFrame:
    try:
        return pd.read_csv(io.BytesIO(raw), dtype=str)
    except Exception as exc:  # noqa: BLE001 - adapter boundary converts parser failures
        raise Stage3CBInputError(f"INPUT_PARSE_FAILURE:{label}") from exc


def _verify_control_raw(path: Path, expected_sha256: str, label: str) -> dict[str, Any]:
    raw, actual, proof = _read_hash_first(path, expected_sha256, label)
    if path.suffix.lower() == ".json":
        try:
            payload = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise Stage3CBInputError(f"INPUT_PARSE_FAILURE:{label}") from exc
        if not isinstance(payload, dict | list):
            raise Stage3CBInputError(f"INPUT_SCHEMA_FAILURE:{label}")
    else:
        frame = _parse_csv(raw, label)
        if frame.empty:
            raise Stage3CBInputError(f"INPUT_SCHEMA_FAILURE:{label}:empty")
    return {"raw_sha256": actual, "bounded_proof": proof}


def materialize_qfq_close_to_close(
    frame: pd.DataFrame, *, adjustment: str = "qfq"
) -> pd.DataFrame:
    """Materialize only the frozen adjusted close-to-close target return."""

    if adjustment != "qfq":
        raise Stage3CBInputError("TARGET_ADJUSTMENT_MUST_BE_QFQ")
    required = {"date", "code", "close"}
    if not required.issubset(frame.columns):
        raise Stage3CBInputError("TARGET_QFQ_SCHEMA_FAILURE")
    if not frame["code"].astype(str).str.lower().eq("sh.601857").all():
        raise Stage3CBInputError("TARGET_IDENTITY_FAILURE")
    dates = pd.to_datetime(frame["date"], errors="coerce")
    closes = pd.to_numeric(frame["close"], errors="coerce")
    if dates.isna().any() or closes.isna().any() or closes.le(0).any():
        raise Stage3CBInputError("TARGET_QFQ_VALUE_FAILURE")
    if dates.duplicated().any() or (dates.dt.date >= HOLDOUT_START).any():
        raise Stage3CBInputError("TARGET_DATE_OR_HOLDOUT_FAILURE")
    source = frame.assign(date=dates, close=closes).sort_values("date", kind="mergesort")
    returns = source["close"].pct_change(fill_method=None)
    return pd.DataFrame(
        {
            "trade_date": source["date"].reset_index(drop=True),
            "target_analysis_return": returns.reset_index(drop=True),
            "target_valid": returns.notna().reset_index(drop=True),
        }
    )


def _materialize_target(path: Path) -> tuple[pd.DataFrame, dict[str, Any]]:
    raw, actual, proof = _read_hash_first(path, EXPECTED_TARGET_RAW_SHA256, "target_daily_qfq")
    frame = _parse_csv(raw, "target_daily_qfq")
    required = {"date", "code", "close"}
    if not required.issubset(frame.columns):
        raise Stage3CBInputError("TARGET_QFQ_SCHEMA_FAILURE")
    if not frame["code"].astype(str).str.lower().eq("sh.601857").all():
        raise Stage3CBInputError("TARGET_IDENTITY_FAILURE")
    dates = pd.to_datetime(frame["date"], errors="coerce")
    closes = pd.to_numeric(frame["close"], errors="coerce")
    if dates.isna().any() or closes.isna().any() or closes.le(0).any():
        raise Stage3CBInputError("TARGET_QFQ_VALUE_FAILURE")
    if dates.duplicated().any() or (dates.dt.date >= HOLDOUT_START).any():
        raise Stage3CBInputError("TARGET_DATE_OR_HOLDOUT_FAILURE")
    source = frame.assign(date=dates, close=closes).sort_values("date", kind="mergesort")
    trade_dates = pd.to_datetime(source["date"])
    close_time = (
        trade_dates.dt.tz_localize("Asia/Shanghai") + pd.Timedelta(hours=15)
    ).dt.tz_convert("UTC")
    normalized_input = pd.DataFrame(
        {
            "trade_date": trade_dates,
            "observation_time": close_time,
            "available_at": close_time,
            "value": pd.to_numeric(source["close"], errors="raise"),
        }
    )
    normalized = normalize_daily_observations(
        normalized_input,
        dataset_id="target_daily_qfq",
        instrument_id="601857.SH",
        currency="CNY",
        adjustment="qfq",
        source_name="Baostock",
        source_endpoint="query_history_k_data_plus",
        source_version="00.9.30",
        raw_sha256=actual,
    )
    logical = canonical_frame_digest(normalized)
    if logical != EXPECTED_TARGET_LOGICAL_SHA256:
        raise Stage3CBInputError("TARGET_LOGICAL_IDENTITY_FAILURE")
    returns = pd.to_numeric(normalized["value"], errors="raise").pct_change(fill_method=None)
    result = pd.DataFrame(
        {
            "trade_date": normalized["trade_date"],
            "target_analysis_return": returns,
            "target_valid": returns.notna(),
        }
    )
    return result, {
        "dataset_id": "target_daily_qfq",
        "raw_file_path": "baostock/601857_SH_qfq.csv",
        "raw_sha256": actual,
        "logical_sha256": logical,
        "rows": int(len(result)),
        "date_start": result["trade_date"].min().date().isoformat(),
        "date_end": result["trade_date"].max().date().isoformat(),
        "target_return_definition": "ADJUSTED_CLOSE_TO_CLOSE_SIMPLE_RETURN",
        "bounded_proof": proof,
    }


def _load_market_proxy(path: Path) -> tuple[pd.DataFrame, dict[str, Any]]:
    raw, raw_sha, proof = _read_hash_first(path, None, "market_proxy")
    frame = _parse_csv(raw, "market_proxy")
    required = {"trade_date", "return", "row_status"}
    if not required.issubset(frame.columns):
        raise Stage3CBInputError("MARKET_PROXY_SCHEMA_FAILURE")
    dates = pd.to_datetime(frame["trade_date"], errors="coerce")
    returns = pd.to_numeric(frame["return"], errors="coerce")
    if dates.isna().any() or dates.duplicated().any() or (dates.dt.date >= HOLDOUT_START).any():
        raise Stage3CBInputError("MARKET_PROXY_DATE_FAILURE")
    valid = frame["row_status"].eq("PROXY_ROW_OK") & returns.notna()
    if len(frame) != EXPECTED_MARKET_ROWS or int(valid.sum()) != EXPECTED_MARKET_VALID_ROWS:
        raise Stage3CBInputError("M3_STAGE3CB_MARKET_PROXY_IDENTITY_FAILURE")
    if int((~valid).sum()) != EXPECTED_MARKET_GAP_ROWS:
        raise Stage3CBInputError("M3_STAGE3CB_MARKET_PROXY_IDENTITY_FAILURE")
    result = pd.DataFrame(
        {
            "trade_date": dates,
            "market_ex_target_return": returns,
            "market_valid": valid.astype(bool),
        }
    )
    return result, {
        "implementation_id": EXPECTED_MARKET_PROXY,
        "logical_sha256": canonical_frame_digest(frame),
        "file_sha256": raw_sha,
        "rows": int(len(frame)),
        "valid_rows": int(valid.sum()),
        "gap_rows": int((~valid).sum()),
        "bounded_proof": proof,
    }


def _load_aligned(
    path: Path,
    *,
    label: str,
    expected_digest: str,
    date_column: str,
    return_column: str,
    status_column: str,
    ok_status: str,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    raw, file_sha, proof = _read_hash_first(path, None, label)
    frame = _parse_csv(raw, label)
    required = {date_column, return_column, status_column}
    if not required.issubset(frame.columns):
        raise Stage3CBInputError(f"{label.upper()}_SCHEMA_FAILURE")
    logical = canonical_frame_digest(frame)
    if logical != expected_digest:
        raise Stage3CBInputError(f"{label.upper()}_LOGICAL_IDENTITY_FAILURE")
    dates = pd.to_datetime(frame[date_column], errors="coerce")
    values = pd.to_numeric(frame[return_column], errors="coerce")
    if dates.isna().any() or dates.duplicated().any() or (dates.dt.date >= HOLDOUT_START).any():
        raise Stage3CBInputError(f"{label.upper()}_DATE_FAILURE")
    valid = frame[status_column].eq(ok_status) & values.notna()
    return pd.DataFrame(
        {
            "trade_date": dates,
            return_column: values,
            f"{label}_valid": valid.astype(bool),
        }
    ), {
        "logical_sha256": logical,
        "file_sha256": file_sha,
        "rows": int(len(frame)),
        "valid_rows": int(valid.sum()),
        "bounded_proof": proof,
    }


def _load_readiness(path: Path) -> tuple[pd.DataFrame, dict[str, Any]]:
    raw, file_sha, proof = _read_hash_first(path, None, "tier1_readiness")
    frame = _parse_csv(raw, "tier1_readiness")
    if canonical_frame_digest(frame) != EXPECTED_TIER1_READINESS_DIGEST:
        raise Stage3CBInputError("M3_STAGE3CB_TIER1_READINESS_IDENTITY_FAILURE")
    required = {
        "trade_date",
        "market_proxy_valid",
        "oil_valid",
        "industry_valid",
        "tier1_joint_valid",
    }
    if not required.issubset(frame.columns):
        raise Stage3CBInputError("TIER1_READINESS_SCHEMA_FAILURE")
    dates = pd.to_datetime(frame["trade_date"], errors="coerce")
    if dates.isna().any() or dates.duplicated().any() or (dates.dt.date >= HOLDOUT_START).any():
        raise Stage3CBInputError("TIER1_READINESS_DATE_FAILURE")
    flags = frame.loc[
        :, ["market_proxy_valid", "oil_valid", "industry_valid", "tier1_joint_valid"]
    ].apply(
        lambda column: column.astype(str).str.lower().eq("true")
    )
    result = flags.copy()
    result.insert(0, "trade_date", dates)
    summary = {
        "logical_sha256": EXPECTED_TIER1_READINESS_DIGEST,
        "file_sha256": file_sha,
        "rows": int(len(frame)),
        "market_valid_rows": int(flags["market_proxy_valid"].sum()),
        "oil_valid_rows": int(flags["oil_valid"].sum()),
        "industry_valid_rows": int(flags["industry_valid"].sum()),
        "tier1_joint_valid_rows": int(flags["tier1_joint_valid"].sum()),
        "first_joint_valid": dates.loc[flags["tier1_joint_valid"]].min().date().isoformat(),
        "last_joint_valid": dates.loc[flags["tier1_joint_valid"]].max().date().isoformat(),
        "bounded_proof": proof,
    }
    if summary["rows"] != EXPECTED_MARKET_ROWS or summary["tier1_joint_valid_rows"] != 1902:
        raise Stage3CBInputError("M3_STAGE3CB_TIER1_READINESS_IDENTITY_FAILURE")
    return result, summary


def build_exact_date_analysis_matrix(
    target: pd.DataFrame,
    market: pd.DataFrame,
    oil: pd.DataFrame,
    industry: pd.DataFrame,
    readiness: pd.DataFrame,
    *,
    enforce_expected_identity: bool = True,
) -> pd.DataFrame:
    """Join adapter inputs by exact trade date and return only the frozen schema."""

    oil = oil.rename(columns={"oil_aligned_valid": "oil_valid"})
    industry = industry.rename(columns={"industry_aligned_valid": "industry_valid"})
    frames = [target, market, oil, industry, readiness]
    date_sets = {
        frozenset(pd.to_datetime(frame["trade_date"], errors="raise")) for frame in frames
    }
    if len(date_sets) != 1:
        raise Stage3CBInputError("EXACT_DATE_JOIN_KEY_MISMATCH")
    matrix = frames[0]
    for other in frames[1:]:
        matrix = matrix.merge(other, on="trade_date", how="inner", validate="one_to_one")
    if enforce_expected_identity and len(matrix) != EXPECTED_MARKET_ROWS:
        raise Stage3CBInputError("EXACT_DATE_JOIN_ROW_COUNT_FAILURE")
    # The exact merge creates suffixes for source validity flags; normalize only
    # those adapter-owned fields and keep the frozen analysis schema unchanged.
    if not matrix["market_valid"].eq(matrix["market_proxy_valid"]).all():
        raise Stage3CBInputError("TIER1_MARKET_FLAG_MISMATCH")
    if "oil_valid_x" in matrix:
        if not matrix["oil_valid_x"].eq(matrix["oil_valid_y"]).all():
            raise Stage3CBInputError("TIER1_OIL_FLAG_MISMATCH")
        matrix["oil_valid"] = matrix["oil_valid_x"]
        matrix = matrix.drop(columns=["oil_valid_x", "oil_valid_y"])
    if "industry_valid_x" in matrix:
        if not matrix["industry_valid_x"].eq(matrix["industry_valid_y"]).all():
            raise Stage3CBInputError("TIER1_INDUSTRY_FLAG_MISMATCH")
        matrix["industry_valid"] = matrix["industry_valid_x"]
        matrix = matrix.drop(columns=["industry_valid_x", "industry_valid_y"])
    if not matrix["tier1_joint_valid"].eq(
        matrix["market_proxy_valid"] & matrix["oil_valid"] & matrix["industry_valid"]
    ).all():
        raise Stage3CBInputError("TIER1_JOINT_FLAG_MISMATCH")
    matrix = matrix.drop(columns=["market_proxy_valid"])
    matrix = matrix.loc[:, list(ANALYSIS_COLUMNS)]
    matrix = matrix.sort_values("trade_date", kind="mergesort").reset_index(drop=True)
    if enforce_expected_identity and (
        matrix["trade_date"].min().date() >= DEVELOPMENT_START
        or matrix["trade_date"].max().date() != DEVELOPMENT_END
    ):
        raise Stage3CBInputError("DEVELOPMENT_BOUNDARY_FAILURE")
    return matrix


def materialize_analysis_matrix(locations: InputLocations) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Hash and parse known inputs, then exact-join the ten-column matrix."""

    target, target_meta = _materialize_target(locations.target_raw)
    oil_raw_meta = _verify_control_raw(
        locations.oil_raw, EXPECTED_OIL_RAW_SHA256, "oil_raw_DCOILBRENTEU"
    )
    industry_raw_meta = _verify_control_raw(
        locations.industry_raw, EXPECTED_INDUSTRY_RAW_SHA256, "industry_raw_CNI_399439"
    )
    market, market_meta = _load_market_proxy(locations.market_proxy)
    oil, oil_meta = _load_aligned(
        locations.oil_aligned,
        label="oil_aligned",
        expected_digest=EXPECTED_OIL_ALIGNED_DIGEST,
        date_column="a_share_trade_date",
        return_column="oil_return",
        status_column="alignment_status",
        ok_status="OIL_ROW_OK",
    )
    industry, industry_meta = _load_aligned(
        locations.industry_aligned,
        label="industry_aligned",
        expected_digest=EXPECTED_INDUSTRY_ALIGNED_DIGEST,
        date_column="trade_date",
        return_column="industry_return",
        status_column="alignment_status",
        ok_status="INDUSTRY_ROW_OK",
    )
    readiness, readiness_meta = _load_readiness(locations.tier1_readiness)
    matrix = build_exact_date_analysis_matrix(target, market, oil, industry, readiness)
    meta = {
        "target": target_meta,
        "market_proxy": market_meta,
        "oil_raw": oil_raw_meta,
        "oil_aligned": oil_meta,
        "industry_raw": industry_raw_meta,
        "industry_aligned": industry_meta,
        "tier1_readiness": readiness_meta,
        "canonical_matrix_digest": canonical_frame_digest(matrix),
        "joined_rows": int(len(matrix)),
        "target_valid_rows": int(matrix["target_valid"].sum()),
        "tier1_joint_valid_rows": int(matrix["tier1_joint_valid"].sum()),
    }
    return matrix, meta


def select_locked_development_matrix(matrix: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Apply the locked selector without fabricating values for invalid rows."""

    if list(matrix.columns) != list(ANALYSIS_COLUMNS):
        raise Stage3CBInputError("ANALYSIS_MATRIX_SCHEMA_FAILURE")
    candidate = matrix.loc[matrix["target_valid"] & matrix["tier1_joint_valid"]].copy()
    if candidate.empty:
        raise Stage3CBInputError("DEVELOPMENT_SAMPLE_EMPTY")
    sample = select_development_sample(candidate)
    excluded = matrix.loc[
        ~(
            matrix["target_valid"]
            & matrix["tier1_joint_valid"]
            & matrix["trade_date"].dt.date.ge(DEVELOPMENT_START)
            & matrix["trade_date"].dt.date.le(DEVELOPMENT_END)
        )
    ]
    target_invalid = matrix.loc[~matrix["target_valid"]]
    return sample, {
        "all_joined_rows": int(len(matrix)),
        "target_valid_rows": int(matrix["target_valid"].sum()),
        "tier1_joint_valid_rows": int(matrix["tier1_joint_valid"].sum()),
        "final_nobs": int(len(sample)),
        "target_invalid_count": int(len(target_invalid)),
        "target_invalid_reason_counts": {
            "NO_PREVIOUS_VALID_QFQ_CLOSE": int(len(target_invalid))
        },
        "tier1_invalid_count": int((~matrix["tier1_joint_valid"]).sum()),
        "excluded_dates": [value.date().isoformat() for value in excluded["trade_date"]],
        "sample_start": sample["trade_date"].min().date().isoformat(),
        "sample_end": sample["trade_date"].max().date().isoformat(),
    }


def validate_execution_mode(mode: str) -> None:
    if mode != "development-primary":
        raise Stage3CBInputError("M3_STAGE3CB_DEVELOPMENT_PRIMARY_ONLY")
