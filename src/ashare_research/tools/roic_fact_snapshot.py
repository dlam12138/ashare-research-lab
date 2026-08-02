"""Stage 2I.1R canonical Fact inventory v2 exporter and validator.

The exporter opens an explicitly supplied canonical Fact database read-only.
It is a read model exporter, not an ingestion path and not a ROIC metric
calculation.  The committed JSON inventory is sufficient for clean-clone
readiness checks without shipping a DuckDB binary.
"""

from __future__ import annotations

import hashlib
import json
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import duckdb

from ashare_research.facts.as_of import AsOfQuery
from ashare_research.facts.identity import validate_canonical_fact_ids
from ashare_research.facts.repository import FactRepository
from ashare_research.storage.duckdb_store import DuckDBStore

ROOT = Path(__file__).resolve().parents[3]
INVENTORY_V2_PATH = ROOT / "config" / "roic_canonical_fact_inventory_v2.json"
SNAPSHOT_SCHEMA = "roic_canonical_fact_inventory_v2"
EXPORT_RUN_ID = "stage2i1r_roic_inventory_v2"
EXPORT_TIME = "2026-08-02T00:00:00+08:00"
SYMBOL = "601857.SH"


def repository_pit_probe(
    fact_db: Path | str,
    *,
    symbol: str = SYMBOL,
    as_of_date: str = "2026-08-02",
) -> dict[str, Any]:
    """Run the existing repository PIT gate on an explicit read-only DB.

    The DuckDB connection is injected into the existing repository store as a
    read-only connection; no schema initialization or write path is invoked.
    """
    path = Path(fact_db)
    store = DuckDBStore(str(path))
    connection = duckdb.connect(str(path), read_only=True)
    store._conn = connection
    try:
        frame = AsOfQuery(FactRepository(store)).query(
            symbol=symbol,
            as_of_date=as_of_date,
            include_unverified=True,
        )
        return {
            "symbol": symbol,
            "as_of_date": as_of_date,
            "visible_rows": int(len(frame)),
            "symbol_values": sorted({str(value) for value in frame["symbol"].unique()})
            if not frame.empty
            else [],
        }
    finally:
        connection.close()
        store._conn = None


def _jsonable(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, date | datetime):
        return value.isoformat()
    if isinstance(value, Decimal):
        return format(value, "f")
    if hasattr(value, "item"):
        return _jsonable(value.item())
    return value


def _stable_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, default=_jsonable) + "\n"
    ).encode("utf-8")


def _sha256_bytes(value: Any) -> str:
    return hashlib.sha256(_stable_bytes(value)).hexdigest()


def _query_rows(
    connection: duckdb.DuckDBPyConnection,
    sql: str,
    params: list[Any],
) -> list[dict[str, Any]]:
    frame = connection.execute(sql, params).df()
    return [
        {str(key): _jsonable(value) for key, value in row.items()}
        for row in frame.to_dict(orient="records")
    ]


def _source_evidence(
    fact: dict[str, Any], by_id: dict[str, dict[str, Any]]
) -> list[dict[str, Any]]:
    raw = str(fact.get("input_fact_ids") or "")
    ids = sorted({item.strip() for item in raw.split(",") if item.strip()})
    evidence = []
    for fact_id in ids:
        parent = by_id.get(fact_id)
        if parent is None:
            continue
        evidence.append(
            {
                "fact_id": fact_id,
                "source_id": parent.get("source_id", ""),
                "source_type": parent.get("source_tier", ""),
                "source_tier": parent.get("source_tier", ""),
                "source_locator": parent.get("source_url", "") or parent.get("source_document", ""),
                "source_document": parent.get("source_document", ""),
                "source_page": parent.get("source_page", ""),
                "content_sha256": parent.get("source_hash", ""),
            }
        )
    return evidence


def _complete_fact(
    fact: dict[str, Any], context: dict[str, Any], by_id: dict[str, dict[str, Any]]
) -> dict[str, Any]:
    record = {
        "fact_id": fact.get("fact_id", ""),
        "concept_id": fact.get("concept_id", ""),
        "concept_version": fact.get("concept_version", "1"),
        "symbol": fact.get("symbol", ""),
        "context_id": fact.get("context_id", ""),
        "value_decimal": format(Decimal(str(fact.get("value"))), "f"),
        "unit": fact.get("unit", ""),
        "currency": "CNY" if fact.get("unit") == "万元" else "",
        "period_start": context.get("period_start", ""),
        "period_end": fact.get("period_end", "") or context.get("period_end", ""),
        "period_type": context.get("period_type", ""),
        "scope": context.get("consolidation_scope", ""),
        "accounting_standard": context.get("accounting_standard", ""),
        "is_derived": bool(fact.get("is_derived", False)),
        "derivation_definition_id": fact.get("derivation_definition_id", ""),
        "derivation_version": fact.get("derivation_version", ""),
        "input_fact_ids": fact.get("input_fact_ids", ""),
        "source_id": fact.get("source_id", ""),
        "source_type": fact.get("source_tier", ""),
        "source_tier": fact.get("source_tier", ""),
        "source_provider": fact.get("source_provider", ""),
        "source_locator": fact.get("source_url", "") or fact.get("source_document", ""),
        "source_document": fact.get("source_document", ""),
        "source_page": fact.get("source_page", ""),
        "source_table": fact.get("source_table", ""),
        "source_label": fact.get("source_label", ""),
        "content_sha256": fact.get("source_hash", ""),
        "verification_status": fact.get("verification_status", ""),
        "verification_note": fact.get("verification_note", ""),
        "eligible_for_metrics": bool(fact.get("eligible_for_metrics", False)),
        "filing_date": fact.get("filing_date", ""),
        "announcement_date": fact.get("announcement_date", ""),
        "available_at": fact.get("available_at", ""),
        "fact_version": int(fact.get("fact_version", 1)),
        "restatement_version": fact.get("restatement_version", "original"),
        "supersedes_fact_id": fact.get("supersedes_fact_id", "") or None,
        "source_evidence": _source_evidence(fact, by_id),
    }
    return {key: _jsonable(value) for key, value in record.items()}


def export_inventory(
    fact_db: Path | str,
    output_path: Path | str,
    *,
    symbol: str = SYMBOL,
) -> dict[str, Any]:
    """Export all canonical rows for *symbol* from an explicit read-only DB."""
    source_path = Path(fact_db)
    if not source_path.is_file():
        raise FileNotFoundError(f"canonical Fact DB not found: {source_path}")
    connection = duckdb.connect(str(source_path), read_only=True)
    try:
        # Symbol is constrained on both fact and context to prevent cross-entity
        # joins or a same-concept row from another issuer entering the inventory.
        fact_rows = _query_rows(
            connection,
            """
            SELECT f.*
            FROM financial_facts f
            JOIN fact_contexts c ON c.context_id = f.context_id
            WHERE f.symbol = ? AND c.symbol = ?
            ORDER BY f.fact_id
            """,
            [symbol, symbol],
        )
        context_rows = _query_rows(
            connection,
            """
            SELECT c.* FROM fact_contexts c
            WHERE c.symbol = ? ORDER BY c.context_id
            """,
            [symbol],
        )
        lineage_rows = _query_rows(
            connection,
            """
            SELECT l.* FROM fact_lineage l
            JOIN financial_facts f ON f.fact_id = l.fact_id
            WHERE f.symbol = ? ORDER BY l.lineage_id
            """,
            [symbol],
        )
    finally:
        connection.close()

    by_id = {str(row["fact_id"]): row for row in fact_rows}
    contexts = {str(row["context_id"]): row for row in context_rows}
    if len(by_id) != len(fact_rows):
        raise ValueError("canonical Fact DB contains duplicate fact_id rows")
    if any(str(row.get("context_id")) not in contexts for row in fact_rows):
        raise ValueError("canonical Fact DB contains a fact without its Context")
    # The repository's identity function is the final identity gate.
    validate_canonical_fact_ids(fact_rows)
    complete_facts = [
        _complete_fact(row, contexts[str(row["context_id"])], by_id) for row in fact_rows
    ]
    sources = {}
    for fact in complete_facts:
        for source_record in [
            {
                "source_id": fact["source_id"],
                "source_type": fact["source_type"],
                "source_tier": fact["source_tier"],
                "source_locator": fact["source_locator"],
                "content_sha256": fact["content_sha256"],
            },
            *fact["source_evidence"],
        ]:
            key = json.dumps(source_record, ensure_ascii=False, sort_keys=True)
            sources[key] = source_record
    source_rows = sorted(sources.values(), key=lambda row: json.dumps(row, sort_keys=True))
    snapshot_payload = {
        "symbol": symbol,
        "facts": complete_facts,
        "contexts": context_rows,
        "sources": source_rows,
        "lineage": lineage_rows,
    }
    inventory = {
        "schema": SNAPSHOT_SCHEMA,
        "snapshot_schema": "facts_contexts_sources_lineage_lossless_decimal_v2",
        "export_run_id": EXPORT_RUN_ID,
        "input_db_sha256": hashlib.sha256(source_path.read_bytes()).hexdigest(),
        "exported_at": EXPORT_TIME,
        "symbol": symbol,
        "fact_count": len(complete_facts),
        "eligible_fact_count": sum(fact["eligible_for_metrics"] for fact in complete_facts),
        "context_count": len(context_rows),
        "source_count": len(source_rows),
        "lineage_count": len(lineage_rows),
        "facts": complete_facts,
        "contexts": context_rows,
        "sources": source_rows,
        "lineage": lineage_rows,
        "snapshot_sha256": _sha256_bytes(snapshot_payload),
        "authority": "trusted canonical Fact DB export; read-only; no DuckDB binary committed",
    }
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(_stable_bytes(inventory))
    return inventory


def load_inventory(path: Path | str = INVENTORY_V2_PATH) -> dict[str, Any]:
    inventory = json.loads(Path(path).read_text(encoding="utf-8"))
    validate_inventory(inventory)
    return inventory


def validate_inventory(inventory: dict[str, Any]) -> None:
    if inventory.get("schema") != SNAPSHOT_SCHEMA:
        raise ValueError("unsupported ROIC inventory schema")
    required = {"facts", "contexts", "sources", "lineage", "snapshot_sha256", "input_db_sha256"}
    if not required.issubset(inventory):
        raise ValueError(f"inventory missing fields: {sorted(required - set(inventory))}")
    facts = inventory["facts"]
    contexts = {str(row["context_id"]): row for row in inventory["contexts"]}
    if len(facts) != inventory.get("fact_count") or len(contexts) != inventory.get("context_count"):
        raise ValueError("inventory count mismatch")
    if any(not fact.get("value_decimal") for fact in facts):
        raise ValueError("inventory must preserve every value as value_decimal")
    identity_rows = []
    for fact in facts:
        if str(fact.get("context_id")) not in contexts:
            raise ValueError(f"inventory fact has missing Context: {fact.get('fact_id')}")
        identity_rows.append(
            {
                "fact_id": fact["fact_id"],
                "concept_id": fact["concept_id"],
                "concept_version": fact.get("concept_version", "1"),
                "symbol": fact["symbol"],
                "context_id": fact["context_id"],
                "source_id": fact.get("source_id", ""),
                "fact_version": fact.get("fact_version", 1),
                "restatement_version": fact.get("restatement_version", "original"),
                "derivation_definition_id": fact.get("derivation_definition_id", ""),
                "derivation_version": fact.get("derivation_version", ""),
            }
        )
    validate_canonical_fact_ids(identity_rows)
    snapshot_payload = {
        "symbol": inventory["symbol"],
        "facts": facts,
        "contexts": inventory["contexts"],
        "sources": inventory["sources"],
        "lineage": inventory["lineage"],
    }
    if inventory["snapshot_sha256"] != _sha256_bytes(snapshot_payload):
        raise ValueError("ROIC inventory snapshot hash mismatch")
