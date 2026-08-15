"""Fail-closed Stage 3B contract and sample-boundary validation."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from datetime import date
from pathlib import Path
from typing import Any

import pandas as pd

from ashare_research.exceptions import SchemaValidationError

WARMUP_START = date(2014, 12, 1)
DEVELOPMENT_START = date(2015, 1, 1)
DEVELOPMENT_END = date(2022, 12, 31)
HOLDOUT_START = date(2023, 1, 1)

STAGE3A_FROZEN_SHA256 = {
    "m3_stage3a_mechanism_hypothesis_contract_v1.json": (
        "1b5a042432a01d26ce3801a558322b6d0bc20627914ae6bb590aea0da1e7dc28"
    ),
    "m3_stage3a_data_requirements_v1.json": (
        "261d692db3ac30bb7c09249203224d9ef7c4141a5259effb92913d412542b35f"
    ),
    "m3_stage3a_statistical_protocol_v1.json": (
        "f8a5b505e36725082a382d5012fdd8e004613dca124ac5bbde41f1a5029eb83e"
    ),
}

# Stage 3B v1 fail-closed contracts remain immutable and are never replaced by code reuse.
STAGE3B_V1_FROZEN_SHA256 = {
    "m3_stage3b_primary_proxy_contract_v1.json": (
        "135fe2dbb50aaa203a9fc57648665d6f73359f2ca0662edba37e2d8cde05b4b8"
    ),
    "m3_stage3b_return_and_timing_contract_v1.json": (
        "dd8c1350089cf76bc81221e1721d2515e72e76f037e57ad124c989d3432bf319"
    ),
    "m3_stage3b_source_registry_v1.json": (
        "ce8f2a622c42d203369d2b2992945b5e2b948b612893c44344abd65939368e73"
    ),
    "m3_stage3b_data_coverage_v1.json": (
        "983086f370c0ce5091dd6ba57326dfd3c5a9b9635b26e7fb669c55d26ae92ede"
    ),
    "m3_stage3b_development_input_manifest_v1.json": (
        "b564e3432e727d829f4769179b1cf2d8a19ae1dc5371c88a3c0fee34c20bfb79"
    ),
}

# Stage 3B-R1 pre-outcome artifacts remain immutable and are never replaced by code reuse.
STAGE3BR1_FROZEN_SHA256 = {
    "m3_stage3br1_primary_proxy_contract_v2.json": (
        "bab6878cf16b904eeb5bc48cb2b92350313ec503c25627bf614bd31af0a21e6a"
    ),
    "m3_stage3br1_primary_proxy_resolution_v1.json": (
        "3db30142bfabec46726955b6f96a8af9b03ed82a93e749ef36376892cfe1668b"
    ),
    "m3_stage3br1_source_registry_v1.json": (
        "122b84182da69826b17677a9fefe019c847e442348756e6c7c18cc08b2f694ce"
    ),
    "m3_stage3br1_development_proxy_manifest_v1.json": (
        "275b6a31d733a87cd5ff9a797e173093f82e4badada608fcb79d236bcc5e6fe0"
    ),
    "m3_stage3br1_data_coverage_v1.json": (
        "6437a02dd23285568666ee06a453a1332117a6cdbc79384f454ea8f96edbf31f"
    ),
}

# Stage 3B-R2 pre-outcome artifacts remain immutable and are never replaced by code reuse.
STAGE3BR2_FROZEN_SHA256 = {
    "m3_stage3br2_oil_timing_resolution_v1.json": (
        "a5e2a247efc2f0fc3a22ee4d4b4f49fe9eca04915d0524fd8fdebef13d3f3233"
    ),
    "m3_stage3br2_oil_contract_v2.json": (
        "908fc0611334816b1a6f0f531611afcf601a8625989d1dcdd0a491e4942446f1"
    ),
    "m3_stage3br2_source_registry_v1.json": (
        "9a957f336c1385231be720a3640a1d9cdd06a2dbb97ea8ce9d03f9ca63831453"
    ),
    "m3_stage3br2_development_input_manifest_v1.json": (
        "81ef5dde1b7a777621b48c29c99b62e96184cd08b862dc4d2edd297641ee7f78"
    ),
    "m3_stage3br2_data_coverage_v1.json": (
        "30c14d7a89024c2f1d9169ad83438a7211824ef1c3f078a465132eab221a5bf2"
    ),
    "m3_stage3br2_tier1_readiness_v1.json": (
        "5aca78d2f251ed9401f3dffea64482805a8ec0f69c777227dbdf4e12106cad88"
    ),
}

# Stage 3B-R3 pre-outcome acquisition-unblock artifacts remain immutable.
STAGE3BR3_FROZEN_SHA256 = {
    "m3_stage3br3_source_resolution_v1.json": (
        "e3b29c25c38c62fdd92f51aa3ca5ad0548fb705ff5406831ba582fcc2af15ff7"
    ),
    "m3_stage3br3_oil_development_manifest_v1.json": (
        "d57f8fe507458c77430990286875f9eea87cbecb262461c03db04e3041966bf6"
    ),
    "m3_stage3br3_industry_development_manifest_v1.json": (
        "57250cc7113c69adf1663baf7d750bdc5bc348ca00ef6d39d8b7eda42f08b148"
    ),
    "m3_stage3br3_data_coverage_v1.json": (
        "cde3f4a24513571a0643282fee2c3da9b682c5e567892f30fe814a9833c6469b"
    ),
    "m3_stage3br3_tier1_readiness_v2.json": (
        "cc169d130ce2d83b242ec32322bd3e173efd0443f5e26e722446d99a0ef4486d"
    ),
    "m3_stage3br3_joint_input_manifest_v1.json": (
        "f950de6ebc40a1c2bd616720715590f2cf7e82c670023a9effee4fb000f120e0"
    ),
}

RESTRICTED_RESEARCH_OUTPUT_KEYS = frozenset(
    {
        "abnormal_return",
        "alpha",
        "beta",
        "bootstrap_result",
        "confidence_interval",
        "correlation",
        "crash_day_count",
        "effect_size",
        "evidence_level",
        "gamma",
        "p_value",
        "positive_probability",
    }
)


class Stage3BContractError(SchemaValidationError):
    """A Stage 3B input or artifact violates a frozen contract."""


def sha256_file(path: str | Path) -> str:
    """Return the lowercase SHA-256 of a file's exact bytes."""
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_frozen_artifacts(
    report_dir: str | Path, expected: dict[str, str]
) -> dict[str, str]:
    """Verify every frozen artifact against its accepted exact-byte hash."""
    root = Path(report_dir)
    actual: dict[str, str] = {}
    for name, wanted in expected.items():
        path = root / name
        if not path.is_file():
            raise Stage3BContractError(f"missing frozen artifact: {name}")
        actual[name] = sha256_file(path)
        if actual[name] != wanted:
            raise Stage3BContractError(f"frozen artifact changed: {name}")
    return actual


def verify_stage3a_frozen(report_dir: str | Path) -> dict[str, str]:
    """Verify all frozen Stage 3A contracts against their accepted exact-byte hashes."""
    return verify_frozen_artifacts(report_dir, STAGE3A_FROZEN_SHA256)


def verify_stage3b_v1_frozen(report_dir: str | Path) -> dict[str, str]:
    """Verify all frozen Stage 3B v1 contracts against their accepted exact-byte hashes."""
    return verify_frozen_artifacts(report_dir, STAGE3B_V1_FROZEN_SHA256)


def verify_stage3br1_frozen(report_dir: str | Path) -> dict[str, str]:
    """Verify all frozen Stage 3B-R1 artifacts against their accepted exact-byte hashes."""
    return verify_frozen_artifacts(report_dir, STAGE3BR1_FROZEN_SHA256)


def verify_stage3br2_frozen(report_dir: str | Path) -> dict[str, str]:
    """Verify all frozen Stage 3B-R2 artifacts against their accepted exact-byte hashes."""
    return verify_frozen_artifacts(report_dir, STAGE3BR2_FROZEN_SHA256)


def verify_stage3br3_frozen(report_dir: str | Path) -> dict[str, str]:
    """Verify all frozen Stage 3B-R3 artifacts against their accepted exact-byte hashes."""
    return verify_frozen_artifacts(report_dir, STAGE3BR3_FROZEN_SHA256)


def load_contract(path: str | Path, required_keys: set[str]) -> dict[str, Any]:
    """Load a JSON object and enforce its minimal Stage 3B envelope."""
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise Stage3BContractError(f"invalid contract {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise Stage3BContractError(f"contract must be a JSON object: {path}")
    missing = sorted(required_keys - payload.keys())
    if missing:
        raise Stage3BContractError(f"contract missing keys {missing}: {path}")
    if payload.get("stage") != "M3_STAGE3B" or payload.get("schema_version") != "1.0.0":
        raise Stage3BContractError(f"unexpected Stage 3B envelope: {path}")
    return payload


def validate_development_dates(
    frame: pd.DataFrame,
    *,
    date_column: str = "trade_date",
    allow_warmup: bool = True,
) -> pd.Series:
    """Parse dates and reject any row outside the authorized warm-up/development range."""
    if date_column not in frame.columns:
        raise Stage3BContractError(f"missing date column: {date_column}")
    dates = pd.to_datetime(frame[date_column], errors="coerce").dt.date
    if dates.isna().any():
        raise Stage3BContractError(f"invalid {date_column} value")
    earliest = WARMUP_START if allow_warmup else DEVELOPMENT_START
    if (dates < earliest).any():
        raise Stage3BContractError(f"row precedes authorized start {earliest.isoformat()}")
    if (dates >= HOLDOUT_START).any():
        raise Stage3BContractError("sealed holdout row rejected")
    return dates


def study_sample(frame: pd.DataFrame, *, date_column: str = "trade_date") -> pd.DataFrame:
    """Return development rows only; warm-up rows are always excluded."""
    dates = validate_development_dates(frame, date_column=date_column, allow_warmup=True)
    return frame.loc[dates >= DEVELOPMENT_START].reset_index(drop=True)


def _walk_keys(value: Any) -> list[str]:
    keys: list[str] = []
    if isinstance(value, Mapping):
        for key, child in value.items():
            keys.append(str(key).lower())
            keys.extend(_walk_keys(child))
    elif isinstance(value, Sequence) and not isinstance(value, str | bytes | bytearray):
        for child in value:
            keys.extend(_walk_keys(child))
    return keys


def assert_no_restricted_research_outputs(payload: Any) -> None:
    """Reject Stage 3B manifest/coverage payloads containing inference-result fields."""
    found = sorted(RESTRICTED_RESEARCH_OUTPUT_KEYS.intersection(_walk_keys(payload)))
    if found:
        raise Stage3BContractError(f"restricted Stage 3B research output keys: {found}")
