"""Offline acceptance runner for manually registered official financial facts.

This module deliberately performs no discovery, download, PDF extraction, OCR,
or network access.  It verifies local evidence against a reviewed JSON bundle,
constructs canonical facts, preflights every pair in memory, and only then
persists through the existing reconciliation service into a run-scoped DuckDB.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from dataclasses import asdict
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from ashare_research.facts.as_of import AsOfQuery
from ashare_research.facts.concepts import ConceptRegistry
from ashare_research.facts.contexts import build_context_id
from ashare_research.facts.identity import build_fact_id
from ashare_research.facts.repository import FactRepository
from ashare_research.reconciliation.engine import (
    SUPPORTED_CONCEPTS,
    ReconciliationEngine,
)
from ashare_research.reconciliation.models import ReconciliationStatus
from ashare_research.reconciliation.service import OfficialFactReconciliationService
from ashare_research.storage.duckdb_store import DuckDBStore
from ashare_research.validation.validator import FactValidator

SCHEMA_VERSION = "1.0"
ACCEPTANCE_CONTRACT = "annual_official_facts_v1"
NORMALIZATION_RULE = "RMB_MILLION_TO_CNY_10K_X100"
RAW_UNIT = "人民币百万元"
CANONICAL_UNIT = "万元"
SAFE_INTEGER_MAX = 2**53 - 1
EXPECTED_CONCEPTS = frozenset(SUPPORTED_CONCEPTS)
DOCUMENT_KEYS = ("company", "exchange")
SOURCE_TIERS = {
    "company": "company_official",
    "exchange": "exchange_official",
}
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_INTEGER = re.compile(r"^-?(?:0|[1-9]\d*)$")
_A_SHARE_SYMBOL = re.compile(r"^\d{6}\.(SH|SZ)$")


class AcceptanceError(ValueError):
    """A deterministic acceptance gate failed."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise AcceptanceError(message)


def load_bundle(path: str | Path) -> dict[str, Any]:
    """Read and validate a registered evidence bundle."""
    bundle = json.loads(Path(path).read_text(encoding="utf-8"))
    validate_bundle(bundle)
    return bundle


def expected_annual_period(fiscal_year: int) -> tuple[str, str]:
    """Return the natural-calendar duration for one annual evidence bundle."""
    return (
        f"{fiscal_year:04d}-01-01",
        f"{fiscal_year:04d}-12-31",
    )


def canonical_report_title(bundle: dict[str, Any]) -> str:
    """Build the context-level report title without replacing source titles."""
    return f"{bundle['company_name']}{bundle['fiscal_year']}年年度报告"


def build_run_id(
    symbol: str,
    fiscal_year: int,
    now: datetime | None = None,
) -> str:
    """Build a stable annual run identity with injectable time for tests."""
    timestamp = (now or datetime.now()).strftime("%Y%m%d_%H%M%S_%f")
    return (
        f"annual_official_{symbol.replace('.', '_')}_"
        f"{fiscal_year}_{timestamp}"
    )


def validate_bundle(bundle: dict[str, Any]) -> None:
    """Validate the deliberately narrow annual official-fact contract."""
    _require(bundle.get("schema_version") == SCHEMA_VERSION, "unsupported bundle schema")
    symbol = bundle.get("symbol")
    _require(
        isinstance(symbol, str) and _A_SHARE_SYMBOL.fullmatch(symbol) is not None,
        "symbol must be six digits followed by .SH or .SZ",
    )
    company_name = bundle.get("company_name")
    _require(
        isinstance(company_name, str) and bool(company_name.strip()),
        "company_name must be a non-empty string",
    )
    fiscal_year = bundle.get("fiscal_year")
    _require(
        type(fiscal_year) is int and 1990 <= fiscal_year <= 9999,
        "fiscal_year must be an integer from 1990 through 9999",
    )
    expected_start, expected_end = expected_annual_period(fiscal_year)
    context_fields = {
        "report_type": "annual",
        "period_start": expected_start,
        "period_end": expected_end,
        "accounting_standard": "CAS",
        "consolidation_scope": "consolidated",
        "language": "zh-CN",
    }
    for field, expected in context_fields.items():
        _require(bundle.get(field) == expected, f"{field} must be {expected!r}")

    documents = bundle.get("documents")
    _require(isinstance(documents, dict), "documents must be an object")
    _require(set(documents) == set(DOCUMENT_KEYS), "company and exchange documents required")
    source_ids: set[str] = set()
    for key in DOCUMENT_KEYS:
        document = documents[key]
        _require(
            document.get("source_tier") == SOURCE_TIERS[key],
            f"{key} source_tier must be {SOURCE_TIERS[key]}",
        )
        for field in (
            "source_provider",
            "source_id",
            "source_document",
            "landing_url",
            "pdf_url",
            "final_pdf_url",
            "announcement_date",
            "retrieved_at",
            "content_type",
        ):
            _require(bool(document.get(field)), f"{key}.{field} is required")
        _require(
            _SHA256.fullmatch(str(document.get("sha256", ""))) is not None,
            f"{key}.sha256 must be lowercase SHA-256",
        )
        _require(document.get("content_length", 0) > 0, f"{key}.content_length required")
        _require(document.get("page_count", 0) > 0, f"{key}.page_count required")
        try:
            date.fromisoformat(document["announcement_date"])
            datetime.fromisoformat(document["retrieved_at"])
        except (TypeError, ValueError) as exc:
            raise AcceptanceError(f"{key} has invalid date evidence") from exc
        source_ids.add(document["source_id"])
    _require(len(source_ids) == 2, "official source_id values must be distinct")

    facts = bundle.get("facts")
    _require(isinstance(facts, list), "facts must be a list")
    _require(len(facts) == 6, "bundle must contain exactly six source facts")
    observed: set[tuple[str, str]] = set()
    concepts_by_source = {key: set() for key in DOCUMENT_KEYS}
    for fact in facts:
        key = fact.get("source_key")
        _require(key in DOCUMENT_KEYS, "fact source_key must be company or exchange")
        concept = fact.get("concept_id")
        _require(concept in EXPECTED_CONCEPTS, f"unsupported concept: {concept!r}")
        identity = (key, concept)
        _require(identity not in observed, f"duplicate source fact: {identity}")
        observed.add(identity)
        concepts_by_source[key].add(concept)
        for field in ("source_page", "source_table", "source_label", "column_label"):
            _require(bool(fact.get(field)), f"{key}/{concept} requires {field}")
        normalize_registered_value(fact)
    for key, concepts in concepts_by_source.items():
        _require(concepts == EXPECTED_CONCEPTS, f"{key} must have exact three concepts")

    relationship = bundle.get("document_relationship")
    _require(
        relationship in {"byte_identical", "same_report_different_bytes"},
        "document_relationship is invalid",
    )
    same_hash = documents["company"]["sha256"] == documents["exchange"]["sha256"]
    _require(
        (same_hash and relationship == "byte_identical")
        or (not same_hash and relationship == "same_report_different_bytes"),
        "document_relationship does not agree with registered hashes",
    )


def normalize_registered_value(fact: dict[str, Any]) -> int:
    """Convert an integer RMB-million string to exact integer RMB-10k."""
    raw = fact.get("raw_value")
    _require(
        isinstance(raw, str) and _INTEGER.fullmatch(raw) is not None,
        "raw_value integer string required",
    )
    _require(fact.get("raw_unit") == RAW_UNIT, f"raw_unit must be {RAW_UNIT}")
    _require(
        fact.get("normalization_rule") == NORMALIZATION_RULE,
        f"normalization_rule must be {NORMALIZATION_RULE}",
    )
    try:
        normalized = Decimal(raw) * Decimal("100")
    except InvalidOperation as exc:
        raise AcceptanceError("raw_value is not a valid Decimal") from exc
    _require(normalized == normalized.to_integral_value(), "normalized value must be integral")
    value = int(normalized)
    _require(abs(value) <= SAFE_INTEGER_MAX, "normalized value exceeds safe integer range")
    expected = fact.get("expected_normalized_value")
    _require(type(expected) is int, "expected_normalized_value must be a JSON integer")
    _require(value == expected, "expected_normalized_value mismatch")
    return value


def verify_local_pdf(path: str | Path, document: dict[str, Any]) -> dict[str, Any]:
    """Verify local bytes against registered evidence without parsing facts."""
    pdf = Path(path)
    _require(pdf.is_file(), f"local PDF not found: {pdf.name}")
    digest = hashlib.sha256()
    length = 0
    prefix = b""
    with pdf.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            if not prefix:
                prefix = chunk[:5]
            digest.update(chunk)
            length += len(chunk)
    _require(prefix == b"%PDF-", f"{pdf.name} does not have a PDF magic header")
    actual_hash = digest.hexdigest()
    _require(actual_hash == document["sha256"], f"{pdf.name} SHA-256 mismatch")
    _require(length == document["content_length"], f"{pdf.name} content length mismatch")
    _require(
        document["content_type"].lower() == "application/pdf",
        "content_type must be application/pdf",
    )
    return {
        "logical_name": pdf.name,
        "sha256": actual_hash,
        "content_length": length,
        "page_count": document["page_count"],
        "magic_header": "%PDF-",
        "verified": True,
    }


def build_context(bundle: dict[str, Any], *, created_at: str) -> dict[str, Any]:
    filing_date = max(doc["announcement_date"] for doc in bundle["documents"].values())
    return {
        "context_id": build_context_id(
            bundle["symbol"],
            bundle["fiscal_year"],
            bundle["report_type"],
            bundle["consolidation_scope"],
        ),
        "symbol": bundle["symbol"],
        "fiscal_year": bundle["fiscal_year"],
        "period_type": bundle["report_type"],
        "period_start": bundle["period_start"],
        "period_end": bundle["period_end"],
        "instant_or_duration": "duration",
        "consolidation_scope": bundle["consolidation_scope"],
        "accounting_standard": bundle["accounting_standard"],
        "restatement_version": "original",
        "source_document": canonical_report_title(bundle),
        "filing_date": filing_date,
        "created_at": created_at,
    }


def build_source_facts(
    bundle: dict[str, Any],
    *,
    created_at: str,
) -> dict[str, list[dict[str, Any]]]:
    """Construct six canonical verified, ineligible official facts."""
    context_id = build_context_id(
        bundle["symbol"],
        bundle["fiscal_year"],
        bundle["report_type"],
        bundle["consolidation_scope"],
    )
    result: dict[str, list[dict[str, Any]]] = {key: [] for key in DOCUMENT_KEYS}
    for registered in bundle["facts"]:
        key = registered["source_key"]
        document = bundle["documents"][key]
        concept = ConceptRegistry.get(registered["concept_id"])
        _require(concept is not None, f"concept is not registered: {registered['concept_id']}")
        value = normalize_registered_value(registered)
        fact: dict[str, Any] = {
            "fact_version": 1,
            "concept_id": registered["concept_id"],
            "concept_version": concept.version,
            "symbol": bundle["symbol"],
            "value": value,
            "unit": CANONICAL_UNIT,
            "context_id": context_id,
            "is_derived": False,
            "derived_from": "",
            "derivation_definition_id": "",
            "derivation_version": "",
            "input_fact_ids": "",
            "source_provider": document["source_provider"],
            "source_id": document["source_id"],
            "source_tier": document["source_tier"],
            "source_document": document["source_document"],
            "source_url": document["final_pdf_url"],
            "source_hash": document["sha256"],
            "source_page": registered["source_page"],
            "source_table": registered["source_table"],
            "source_label": registered["source_label"],
            "supersedes_fact_id": "",
            "fiscal_year": bundle["fiscal_year"],
            "report_type": bundle["report_type"],
            "period_start": bundle["period_start"],
            "period_end": bundle["period_end"],
            "filing_date": document["announcement_date"],
            "announcement_date": document["announcement_date"],
            "available_at": document["announcement_date"],
            "restatement_version": "original",
            "raw_value": int(registered["raw_value"]),
            "raw_unit": registered["raw_unit"],
            "normalized_value": value,
            "normalization_rule": registered["normalization_rule"],
            "verification_status": "verified",
            "verification_note": "manually verified against audited consolidated statement",
            "eligible_for_metrics": False,
            "created_at": created_at,
        }
        fact["fact_id"] = build_fact_id(fact)
        result[key].append(fact)
    for facts in result.values():
        facts.sort(key=lambda item: item["concept_id"])
    return result


def _jsonable(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    if hasattr(value, "item"):
        return value.item()
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return value


def _write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(_jsonable(value), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _public_source_manifest(bundle: dict[str, Any], checks: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": bundle["schema_version"],
        "symbol": bundle["symbol"],
        "document_relationship": bundle["document_relationship"],
        "documents": {
            key: {
                **bundle["documents"][key],
                "local_verification": checks[key],
            }
            for key in DOCUMENT_KEYS
        },
        "independent_content_sources": False,
    }


def run_acceptance(
    bundle_path: str | Path,
    company_pdf: str | Path,
    exchange_pdf: str | Path,
    output_root: str | Path,
    *,
    run_id: str | None = None,
) -> dict[str, Any]:
    """Run the complete offline acceptance and return its manifest."""
    bundle = load_bundle(bundle_path)
    run_id = run_id or build_run_id(bundle["symbol"], bundle["fiscal_year"])
    run_dir = (
        Path(output_root)
        / bundle["symbol"]
        / "annual_official_facts"
        / str(bundle["fiscal_year"])
        / run_id
    )
    run_dir.mkdir(parents=True, exist_ok=False)
    db_path = run_dir / "acceptance.duckdb"
    started_at = datetime.now().astimezone().isoformat()

    manifest: dict[str, Any] = {
        "run_id": run_id,
        "status": "failed",
        "transaction_committed": False,
        "offline": True,
        "symbol": bundle["symbol"],
        "company_name": bundle["company_name"],
        "fiscal_year": bundle["fiscal_year"],
        "report_type": bundle["report_type"],
        "period_start": bundle["period_start"],
        "period_end": bundle["period_end"],
        "accounting_standard": bundle["accounting_standard"],
        "consolidation_scope": bundle["consolidation_scope"],
        "language": bundle["language"],
        "acceptance_contract": ACCEPTANCE_CONTRACT,
        "bundle_schema_version": bundle["schema_version"],
        "fact_schema_version": FactRepository.schema_version,
        "database": "acceptance.duckdb",
        "started_at": started_at,
    }
    checks: dict[str, Any] = {}
    repo: FactRepository | None = None
    store: DuckDBStore | None = None
    try:
        checks["company"] = verify_local_pdf(company_pdf, bundle["documents"]["company"])
        checks["exchange"] = verify_local_pdf(exchange_pdf, bundle["documents"]["exchange"])
        _write_json(run_dir / "source_manifest.json", _public_source_manifest(bundle, checks))

        created_at = datetime.now().isoformat()
        source_facts = build_source_facts(bundle, created_at=created_at)
        all_source_facts = source_facts["company"] + source_facts["exchange"]
        validation = FactValidator().validate_batch(all_source_facts)
        validation_errors = [
            asdict(item) for item in validation if item.severity == "error" and not item.passed
        ]
        _require(not validation_errors, f"source fact validation failed: {validation_errors}")

        engine = ReconciliationEngine()
        preflight = []
        company_by_concept = {fact["concept_id"]: fact for fact in source_facts["company"]}
        exchange_by_concept = {fact["concept_id"]: fact for fact in source_facts["exchange"]}
        for concept_id in sorted(EXPECTED_CONCEPTS):
            result = engine.reconcile_pair(
                company_by_concept[concept_id],
                exchange_by_concept[concept_id],
                now=created_at,
            )
            preflight.append(asdict(result))

        _write_json(run_dir / "company_facts.json", source_facts["company"])
        _write_json(run_dir / "exchange_facts.json", source_facts["exchange"])
        _write_json(run_dir / "reconciliation_results.json", preflight)

        # Create the isolated database only after document and fact validation.
        # It exists on reconciliation mismatch so the failure can prove zero facts.
        store = DuckDBStore(str(db_path))
        store.connect()
        repo = FactRepository(store)
        repo.ensure_schema()
        _require(
            all(item["status"] == ReconciliationStatus.matched for item in preflight),
            "all reconciliation pairs must match before persistence",
        )

        context = build_context(bundle, created_at=created_at)
        with repo.transaction() as conn:
            repo.store_contexts([context], conn=conn)

        service = OfficialFactReconciliationService(repo)
        persisted_results = []
        for concept_id in sorted(EXPECTED_CONCEPTS):
            result = service.reconcile_official_pair(
                company_by_concept[concept_id],
                exchange_by_concept[concept_id],
            )
            persisted_results.append(asdict(result))

        manifest["transaction_committed"] = True
        reconciled_facts = [item["output_fact"] for item in persisted_results]
        as_of = AsOfQuery(repo)
        latest_date = max(doc["announcement_date"] for doc in bundle["documents"].values())
        before_date = (date.fromisoformat(latest_date) - timedelta(days=1)).isoformat()
        pit_before = as_of.get_latest_available(
            bundle["symbol"], before_date, sorted(EXPECTED_CONCEPTS)
        )
        pit_after = as_of.get_latest_available(
            bundle["symbol"], latest_date, sorted(EXPECTED_CONCEPTS)
        )
        audit = as_of.get_all_versions_for_audit(bundle["symbol"], sorted(EXPECTED_CONCEPTS))
        conn = store.connect()
        lineage_df = conn.execute(
            """SELECT fact_id, run_id, source_tier, parent_fact_ids, role,
                      reconciliation_rule_id, reconciliation_rule_version
               FROM fact_lineage ORDER BY lineage_id"""
        ).df()
        counts = {
            "contexts": conn.execute("SELECT COUNT(*) FROM fact_contexts").fetchone()[0],
            "financial_facts": conn.execute("SELECT COUNT(*) FROM financial_facts").fetchone()[0],
            "company_original": conn.execute(
                "SELECT COUNT(*) FROM financial_facts WHERE source_tier='company_official'"
            ).fetchone()[0],
            "exchange_original": conn.execute(
                "SELECT COUNT(*) FROM financial_facts WHERE source_tier='exchange_official'"
            ).fetchone()[0],
            "reconciled": conn.execute(
                "SELECT COUNT(*) FROM financial_facts WHERE source_tier='reconciled_derived'"
            ).fetchone()[0],
            "lineage": len(lineage_df),
            "pit_before": len(pit_before),
            "pit_after": len(pit_after),
            "audit": len(audit),
        }
        expected_counts = {
            "contexts": 1,
            "financial_facts": 9,
            "company_original": 3,
            "exchange_original": 3,
            "reconciled": 3,
            "lineage": 9,
            "pit_before": 0,
            "pit_after": 3,
            "audit": 9,
        }
        _require(counts == expected_counts, f"acceptance counts differ: {counts}")
        _require(
            all(fact["eligible_for_metrics"] is True for fact in reconciled_facts),
            "reconciled facts must be eligible",
        )
        _write_json(run_dir / "reconciled_facts.json", reconciled_facts)
        _write_json(run_dir / "lineage_summary.json", lineage_df.to_dict("records"))
        manifest.update(
            {
                "status": "passed",
                "latest_available_at": latest_date,
                "counts": counts,
                "source_hash_validation": "passed",
                "completed_at": datetime.now().astimezone().isoformat(),
            }
        )
    except Exception as exc:
        manifest["error_type"] = type(exc).__name__
        manifest["error"] = str(exc)
        manifest["completed_at"] = datetime.now().astimezone().isoformat()
    finally:
        if store is not None:
            store.close()

    _write_json(run_dir / "run_manifest.json", manifest)
    summary = (
        f"# Annual official fact acceptance\n\n"
        f"- symbol: `{bundle['symbol']}`\n"
        f"- fiscal_year: `{bundle['fiscal_year']}`\n"
        f"- run_id: `{run_id}`\n"
        f"- status: **{manifest['status']}**\n"
        f"- offline: `true`\n"
        f"- database: `acceptance.duckdb` (run-scoped)\n"
        f"- transaction_committed: `{str(manifest['transaction_committed']).lower()}`\n"
        f"- fact_schema_version: `{FactRepository.schema_version}`\n"
        f"- acceptance_contract: `{ACCEPTANCE_CONTRACT}`\n"
    )
    if "counts" in manifest:
        summary += "\n## Counts\n\n" + "\n".join(
            f"- {key}: {value}" for key, value in manifest["counts"].items()
        ) + "\n"
    if "error" in manifest:
        summary += f"\n## Failure\n\n{manifest['error']}\n"
    (run_dir / "acceptance_summary.md").write_text(summary, encoding="utf-8")
    return {**manifest, "run_directory": run_dir}


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", required=True)
    parser.add_argument("--company-pdf", required=True)
    parser.add_argument("--exchange-pdf", required=True)
    parser.add_argument("--output-root", required=True)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    result = run_acceptance(
        args.bundle, args.company_pdf, args.exchange_pdf, args.output_root
    )
    print(json.dumps(_jsonable(result), ensure_ascii=False, indent=2))
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
