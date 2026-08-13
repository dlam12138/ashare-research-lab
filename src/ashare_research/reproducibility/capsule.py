"""Portable canonical Fact and synthetic market capsule builders."""

from __future__ import annotations

import csv
import hashlib
import json
import shutil
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any

import duckdb

from ashare_research.facts.identity import validate_canonical_fact_ids
from ashare_research.facts.repository import FactRepository
from ashare_research.storage.duckdb_store import DuckDBStore
from ashare_research.validation.version_chain import VersionChainValidator

from .artifacts import sha256_file

SNAPSHOT_CONTRACT = "stage2g_canonical_fact_snapshot_v1"
SNAPSHOT_MANIFEST = "snapshot_manifest.json"
FACTS_FILE = "facts.json"
CONTEXTS_FILE = "contexts.json"
LINEAGE_FILE = "lineage.json"
MARKET_FIXTURE_DIR = "market_test_capsule_v1"
MARKET_FILE = "market_rows.csv"
CAPSULE_MANIFEST = "capsule_manifest.json"
CAPSULE_SCHEMA_VERSION = "stage2g_test_capsule_v1"
DETERMINISTIC_BUILD_TIME = "2026-08-02T00:00:00+08:00"


def _json_default(value: Any) -> Any:
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, date):
        return value.isoformat()
    raise TypeError(type(value).__name__)


def _stable_json_bytes(value: Any) -> bytes:
    return (
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
            default=_json_default,
        )
        + "\n"
    ).encode("utf-8")


def _write_stable(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_bytes(_stable_json_bytes(value))
    temporary.replace(path)


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _as_jsonable(value: Any) -> Any:
    if isinstance(value, Decimal):
        return format(value, "f")
    if hasattr(value, "item"):
        return _as_jsonable(value.item())
    if isinstance(value, dict):
        return {str(key): _as_jsonable(child) for key, child in value.items()}
    if isinstance(value, list):
        return [_as_jsonable(child) for child in value]
    return value


def _selected_contexts_and_lineage(fact_db: Path, facts: list[dict[str, Any]]) -> tuple[list, list]:
    connection = duckdb.connect(str(fact_db), read_only=True)
    try:
        context_ids = sorted({str(fact["context_id"]) for fact in facts})
        fact_ids = sorted({str(fact["fact_id"]) for fact in facts})
        context_df = connection.execute(
            "SELECT * FROM fact_contexts WHERE context_id IN (SELECT UNNEST(?)) "
            "ORDER BY context_id",
            [context_ids],
        ).df()
        lineage_df = connection.execute(
            "SELECT * FROM fact_lineage WHERE fact_id IN (SELECT UNNEST(?)) ORDER BY lineage_id",
            [fact_ids],
        ).df()
        return (
            [_as_jsonable(row) for row in context_df.to_dict(orient="records")],
            [_as_jsonable(row) for row in lineage_df.to_dict(orient="records")],
        )
    finally:
        connection.close()


def export_facts(fact_db: Path | str, output_dir: Path | str) -> dict[str, Any]:
    """Export the bounded Stage 2G PIT read model from a supplied DB.

    The source is opened read-only through the existing repository/PIT
    interfaces.  No default DB is inferred and no input is modified.
    """

    from ashare_research.tools.petrochina_valuation_and_value_profile import (
        _load_canonical_facts,
    )

    source = Path(fact_db)
    if not source.is_file():
        raise FileNotFoundError(f"missing_input: canonical fact DB not found: {source}")
    facts, metadata = _load_canonical_facts(source)
    validate_canonical_fact_ids(facts)
    contexts, lineage = _selected_contexts_and_lineage(source, facts)
    exported_facts = []
    for fact in sorted(facts, key=lambda row: str(row["fact_id"])):
        record = {
            key: _as_jsonable(value)
            for key, value in fact.items()
            if key not in {"lineage", "rn", "value_cny", "currency", "source_evidence_ids"}
        }
        record["value_decimal"] = format(Decimal(str(fact["value"])), "f")
        record["lineage_ids"] = [
            int(row["lineage_id"])
            for row in lineage
            if str(row["fact_id"]) == str(fact["fact_id"])
        ]
        exported_facts.append(record)
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    _write_stable(out / FACTS_FILE, exported_facts)
    _write_stable(out / CONTEXTS_FILE, sorted(contexts, key=lambda row: str(row["context_id"])))
    _write_stable(out / LINEAGE_FILE, sorted(lineage, key=lambda row: int(row["lineage_id"])))
    facts_hash = sha256_file(out / FACTS_FILE)
    manifest = {
        "contract": SNAPSHOT_CONTRACT,
        "schema_version": "2.1",
        "symbol": "601857.SH",
        "row_count": len(exported_facts),
        "context_count": len(contexts),
        "lineage_count": len(lineage),
        "concept_coverage": metadata["required_concept_coverage"],
        "available_at_range": {
            "min": min(
                str(row["available_at"]) for row in exported_facts if row.get("available_at")
            ),
            "max": max(
                str(row["available_at"]) for row in exported_facts if row.get("available_at")
            ),
        },
        "identity_validation": "pass",
        "version_chain_validation": "pass",
        "facts_sha256": facts_hash,
        "generator_version": "stage2g-reproducibility-exporter-1",
        "logical_source_db_sha256": sha256_file(source),
        "logical_source_db_name": source.name,
        "export_command": (
            "python -m ashare_research.tools.stage2g_reproducibility export-facts "
            "--fact-db <path> --output <dir>"
        ),
        "authority": "canonical export/read model; not a new source of truth",
        "used_fact_ids": sorted(str(row["fact_id"]) for row in exported_facts),
    }
    _write_stable(out / SNAPSHOT_MANIFEST, manifest)
    return manifest


def validate_snapshot(snapshot_dir: Path | str) -> dict[str, Any]:
    root = Path(snapshot_dir)
    manifest = _read_json(root / SNAPSHOT_MANIFEST)
    if manifest.get("contract") != SNAPSHOT_CONTRACT:
        raise ValueError("unsupported canonical Fact snapshot contract")
    facts = _read_json(root / FACTS_FILE)
    contexts = _read_json(root / CONTEXTS_FILE)
    lineage = _read_json(root / LINEAGE_FILE)
    if sha256_file(root / FACTS_FILE) != manifest.get("facts_sha256"):
        raise ValueError("canonical Fact snapshot hash mismatch")
    if len(facts) != manifest.get("row_count") or len(contexts) != manifest.get("context_count"):
        raise ValueError("canonical Fact snapshot row count mismatch")
    if any("value_decimal" not in fact for fact in facts):
        raise ValueError("canonical Fact snapshot is missing lossless decimal values")
    validate_canonical_fact_ids(facts)
    context_ids = {str(row["context_id"]) for row in contexts}
    missing_contexts = sorted(
        {str(fact["context_id"]) for fact in facts} - context_ids
    )
    if missing_contexts:
        raise ValueError(f"canonical Fact snapshot missing contexts: {missing_contexts}")
    return {
        "status": "pass",
        "row_count": len(facts),
        "context_count": len(contexts),
        "lineage_count": len(lineage),
        "facts_sha256": manifest["facts_sha256"],
        "manifest": manifest,
        "facts": facts,
        "contexts": contexts,
        "lineage": lineage,
    }


def build_temp_fact_db(
    snapshot_dir: Path | str,
    output_path: Path | str,
) -> Path:
    """Build an isolated DuckDB using repository schema and snapshot rows."""

    snapshot = validate_snapshot(snapshot_dir)
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        target.unlink()
    store = DuckDBStore(str(target))
    repository = FactRepository(store)
    repository.ensure_schema_v2(git_commit="stage2g-test-capsule")
    connection = store.connect()
    connection.execute(
        "UPDATE fact_schema_meta SET applied_at = ? WHERE schema_name = 'financial_facts'",
        [DETERMINISTIC_BUILD_TIME],
    )
    repository.store_contexts(snapshot["contexts"], conn=connection)
    fact_columns = set(repository._FACT_COLS)
    rows = []
    for fact in snapshot["facts"]:
        row = {key: fact.get(key, "") for key in fact_columns}
        row["value"] = float(Decimal(str(fact["value_decimal"])))
        rows.append(row)
    repository.store_facts(rows, conn=connection)
    for lineage in snapshot["lineage"]:
        connection.execute(
            """INSERT INTO fact_lineage
               (lineage_id, fact_id, run_id, source_provider, source_tier,
                source_method, raw_file_path, staging_file_path, fetch_run_id,
                parent_fact_ids, role, reconciliation_rule_id,
                reconciliation_rule_version, recorded_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            [
                lineage.get("lineage_id"),
                lineage.get("fact_id", ""),
                lineage.get("run_id", ""),
                lineage.get("source_provider", ""),
                lineage.get("source_tier", ""),
                lineage.get("source_method", ""),
                lineage.get("raw_file_path", ""),
                lineage.get("staging_file_path", ""),
                lineage.get("fetch_run_id", ""),
                lineage.get("parent_fact_ids", ""),
                lineage.get("role", ""),
                lineage.get("reconciliation_rule_id", ""),
                lineage.get("reconciliation_rule_version", ""),
                lineage.get("recorded_at", ""),
            ],
        )
    validate_canonical_fact_ids(rows)
    results = VersionChainValidator(repository).validate(rows, conn=connection)
    failed = [result.target_id for result in results if not result.passed]
    if failed:
        raise ValueError(f"temporary canonical version chain failed: {failed}")
    connection.close()
    store._conn = None
    return target


def _synthetic_dates() -> list[str]:
    import pandas as pd

    all_dates = list(pd.bdate_range("2021-01-04", "2026-07-31"))
    protected = {
        "2021-01-04",
        "2021-09-17",
        "2022-06-28",
        "2022-09-20",
        "2023-06-28",
        "2023-09-20",
        "2024-06-26",
        "2024-09-18",
        "2024-09-19",
        "2025-06-25",
        "2025-09-17",
        "2026-06-26",
        "2026-07-31",
    }
    candidates = [
        value
        for index, value in enumerate(all_dates)
        if index % 13 == 0 and value.strftime("%Y-%m-%d") not in protected
    ]
    remove = {value for value in candidates[: len(all_dates) - 1351]}
    return [value.strftime("%Y-%m-%d") for value in all_dates if value not in remove]


def build_synthetic_market_fixture(output_dir: Path | str) -> dict[str, Any]:
    """Create a deterministic, explicitly synthetic, unadjusted market series."""

    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    rows = []
    previous = Decimal("3.80")
    for index, trade_date in enumerate(_synthetic_dates()):
        close = (
            Decimal("3.80")
            + Decimal(index % 97) / Decimal("100")
            + Decimal(index // 251) / Decimal("1000")
        )
        open_price = close - Decimal("0.01")
        high = close + Decimal("0.02")
        low = open_price - Decimal("0.02")
        rows.append(
            {
                "symbol": "601857.SH",
                "trade_date": trade_date,
                "open": format(open_price, "f"),
                "high": format(high, "f"),
                "low": format(low, "f"),
                "close": format(close, "f"),
                "pre_close": format(previous, "f"),
                "volume": str(1000000 + index * 100),
                "amount": format(close * Decimal(1000000 + index * 100), "f"),
                "turnover_rate": format(
                    Decimal("0.10") + Decimal(index % 10) / Decimal("100"), "f"
                ),
            }
        )
        previous = close
    if (
        len(rows) != 1351
        or rows[0]["trade_date"] != "2021-01-04"
        or rows[-1]["trade_date"] != "2026-07-31"
    ):
        raise AssertionError("synthetic market calendar contract changed")
    target = root / MARKET_FILE
    with target.open("w", encoding="utf-8", newline="\n") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    digest = sha256_file(target)
    registry = {
        "contract": "market_data_snapshot_registry_v2",
        "schema_version": "2.0",
        "data_class": "synthetic_test_only",
        "symbol": "601857.SH",
        "date_range": {"start": rows[0]["trade_date"], "end": rows[-1]["trade_date"]},
        "providers": [
            {
                "provider": "synthetic_provider_a",
                "provider_version": "algorithm-1",
                "logical_name": "synthetic_unadjusted_market_a",
                "object_key": MARKET_FILE,
                "snapshot_sha256": digest,
                "sha256": digest,
                "date_range": {"start": rows[0]["trade_date"], "end": rows[-1]["trade_date"]},
                "row_count": len(rows),
                "adjustment": "none",
                "fields_units": {"close": "CNY/share", "volume": "share", "amount": "CNY"},
                "retrieval_status": "synthetic_test_only",
                "reconciliation_status": "same_synthetic_series",
            },
            {
                "provider": "synthetic_provider_b",
                "provider_version": "algorithm-1",
                "logical_name": "synthetic_unadjusted_market_b",
                "object_key": MARKET_FILE,
                "snapshot_sha256": digest,
                "sha256": digest,
                "date_range": {"start": rows[0]["trade_date"], "end": rows[-1]["trade_date"]},
                "row_count": len(rows),
                "adjustment": "none",
                "fields_units": {"close": "CNY/share", "volume": "share", "amount": "CNY"},
                "retrieval_status": "synthetic_test_only",
                "reconciliation_status": "same_synthetic_series",
            },
        ],
        "common_trade_days": len(rows),
        "close_max_abs_difference": 0.0,
        "reconciliation_status": "pass_synthetic_test_only",
        "network_used": False,
        "redistribution_basis": "generated_from_committed_algorithm_parameters; not provider data",
    }
    return {"rows": rows, "sha256": digest, "registry": registry}


def build_test_capsule(
    output_dir: Path | str,
    *,
    committed_snapshot_dir: Path | str,
) -> dict[str, Any]:
    """Build a complete portable capsule in a caller-owned directory."""

    out = Path(output_dir)
    if out.exists():
        raise FileExistsError(f"refusing to overwrite existing test capsule: {out}")
    out.mkdir(parents=True, exist_ok=True)
    snapshot = validate_snapshot(committed_snapshot_dir)
    snapshot_out = out / "canonical_fact_snapshot_v1"
    snapshot_out.mkdir(parents=True, exist_ok=True)
    for filename in (FACTS_FILE, CONTEXTS_FILE, LINEAGE_FILE, SNAPSHOT_MANIFEST):
        shutil.copyfile(Path(committed_snapshot_dir) / filename, snapshot_out / filename)
    market_out = out / MARKET_FIXTURE_DIR
    market = build_synthetic_market_fixture(market_out)
    registry_path = out / "market_data_snapshot_registry_v2.json"
    _write_stable(registry_path, market["registry"])
    temp_db = out / "temporary_fact.duckdb"
    build_temp_fact_db(snapshot_out, temp_db)
    capsule_files = [
        snapshot_out / FACTS_FILE,
        snapshot_out / CONTEXTS_FILE,
        snapshot_out / LINEAGE_FILE,
        snapshot_out / SNAPSHOT_MANIFEST,
        market_out / MARKET_FILE,
        registry_path,
    ]
    manifest = {
        "contract": CAPSULE_SCHEMA_VERSION,
        "generated_at": DETERMINISTIC_BUILD_TIME,
        "mode": "test_capsule",
        "network_used": False,
        "default_db_mutated": False,
        "inputs": {
            "canonical_fact_snapshot": {
                "relative_path": "canonical_fact_snapshot_v1",
                "sha256": snapshot["facts_sha256"],
                "row_count": snapshot["row_count"],
                "authoritative": False,
                "test_only": True,
            },
            "market_snapshot": {
                "relative_path": f"{MARKET_FIXTURE_DIR}/{MARKET_FILE}",
                "sha256": market["sha256"],
                "row_count": len(market["rows"]),
                "authoritative": False,
                "test_only": True,
            },
        },
        "outputs": [
            {
                "relative_path": str(path.relative_to(out)).replace("\\", "/"),
                "sha256": sha256_file(path),
            }
            for path in sorted(capsule_files, key=lambda item: str(item.relative_to(out)))
        ],
        "real_input_separation": (
            "test-only synthetic and canonical export/read-model inputs; "
            "never a real-mode fallback"
        ),
    }
    manifest["logical_digest"] = hashlib.sha256(
        json.dumps(manifest, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        .encode("utf-8")
    ).hexdigest()
    _write_stable(out / CAPSULE_MANIFEST, manifest)
    return manifest


def verify_capsule_manifest(capsule_dir: Path | str) -> dict[str, Any]:
    root = Path(capsule_dir)
    manifest = _read_json(root / CAPSULE_MANIFEST)
    if manifest.get("contract") != CAPSULE_SCHEMA_VERSION:
        raise ValueError("unsupported test capsule manifest")
    for output in manifest.get("outputs", []):
        relative = Path(output["relative_path"])
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError("capsule manifest contains an unsafe path")
        path = root / relative
        if not path.is_file() or sha256_file(path) != output["sha256"]:
            raise ValueError(f"capsule artifact mismatch: {output['relative_path']}")
    validate_snapshot(root / "canonical_fact_snapshot_v1")
    expected_digest = hashlib.sha256(
        json.dumps(
            {key: value for key, value in manifest.items() if key != "logical_digest"},
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
    if manifest.get("logical_digest") != expected_digest:
        raise ValueError("capsule manifest logical digest mismatch")
    return manifest


def compare_capsules(left_dir: Path | str, right_dir: Path | str) -> dict[str, Any]:
    """Compare independent capsule builds, including every manifest output."""

    left = Path(left_dir)
    right = Path(right_dir)
    left_manifest = verify_capsule_manifest(left)
    right_manifest = verify_capsule_manifest(right)
    differences: list[str] = []
    if left_manifest.get("logical_digest") != right_manifest.get("logical_digest"):
        differences.append("logical_digest_diff")
    if left_manifest != right_manifest:
        differences.append("capsule_manifest_diff")
    left_outputs = {
        item["relative_path"]: item["sha256"] for item in left_manifest.get("outputs", [])
    }
    right_outputs = {
        item["relative_path"]: item["sha256"] for item in right_manifest.get("outputs", [])
    }
    if left_outputs != right_outputs:
        differences.append("capsule_output_checksums_diff")
    return {
        "status": "fail" if differences else "pass",
        "differences": differences,
        "left": {
            "logical_digest": left_manifest.get("logical_digest"),
            "output_count": len(left_outputs),
        },
        "right": {
            "logical_digest": right_manifest.get("logical_digest"),
            "output_count": len(right_outputs),
        },
    }
