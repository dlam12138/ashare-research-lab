"""Build PetroChina's audited 2021-2025 restatement version chains offline.

The tool reads committed annual bundles and restatement evidence only. It
reuses the accepted annual builders, reconciliation engine/service, version
chain validator, repository, and PIT query implementation. It never downloads
or parses a PDF and writes only to a run-scoped DuckDB.
"""

from __future__ import annotations

import argparse
import copy
import json
from dataclasses import asdict
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

from ashare_research.facts.as_of import AsOfQuery
from ashare_research.facts.identity import build_fact_id
from ashare_research.facts.repository import FactRepository
from ashare_research.reconciliation.engine import ReconciliationEngine
from ashare_research.reconciliation.models import ReconciliationStatus
from ashare_research.reconciliation.service import OfficialFactReconciliationService
from ashare_research.storage.duckdb_store import DuckDBStore
from ashare_research.tools.official_fact_acceptance import EXPECTED_CONCEPTS
from ashare_research.tools.official_fact_multi_year_integration import (
    EXPECTED_SYMBOL,
    EXPECTED_YEARS,
    preflight_bundles,
)
from ashare_research.validation.validator import FactValidator

RESTATEMENT_CONTRACT = "restatement_evidence_v1"
INTEGRATION_CONTRACT = "restatement_version_chains_v1"
EXPECTED_TARGET_YEARS = (2021, 2022, 2023, 2024)


class RestatementIntegrationError(ValueError):
    """A deterministic restatement evidence or integration gate failed."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RestatementIntegrationError(message)


def _jsonable(value: Any) -> Any:
    if isinstance(value, Path):
        return value.name
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, list | tuple):
        return [_jsonable(item) for item in value]
    if hasattr(value, "item"):
        return value.item()
    if isinstance(value, date | datetime):
        return value.isoformat()
    return value


def _write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(_jsonable(value), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def build_run_id(now: datetime | None = None) -> str:
    timestamp = (now or datetime.now()).strftime("%Y%m%d_%H%M%S_%f")
    return f"restatement_601857_SH_2021_2025_{timestamp}"


def load_restatement_evidence(path: str | Path) -> dict[str, Any]:
    evidence = json.loads(Path(path).read_text(encoding="utf-8"))
    _require(isinstance(evidence, dict), f"{path}: evidence must be an object")
    return evidence


def preflight_restatements(
    annual_preflight: dict[str, Any],
    evidence_paths: list[str | Path],
    *,
    created_at: str,
) -> dict[str, Any]:
    """Validate evidence and construct every changed v2 pair in memory."""
    _require(len(evidence_paths) == 4, "exactly four evidence files are required")
    annual_by_year = {
        record["bundle"]["fiscal_year"]: record
        for record in annual_preflight["records"]
    }
    loaded = [
        (Path(path), load_restatement_evidence(path))
        for path in evidence_paths
    ]
    loaded.sort(key=lambda item: item[1].get("target_fiscal_year", 0))
    _require(
        tuple(item[1].get("target_fiscal_year") for item in loaded)
        == EXPECTED_TARGET_YEARS,
        "evidence target years must be exactly 2021 through 2024",
    )

    engine = ReconciliationEngine()
    validator = FactValidator()
    evidence_records: list[dict[str, Any]] = []
    changed_pairs: list[dict[str, Any]] = []
    comparisons: list[dict[str, Any]] = []

    for path, evidence in loaded:
        target_year = evidence["target_fiscal_year"]
        evidence_year = evidence.get("evidence_fiscal_year")
        _require(
            evidence.get("contract") == RESTATEMENT_CONTRACT,
            f"{path.name}: unexpected evidence contract",
        )
        _require(
            evidence_year == target_year + 1,
            f"{path.name}: evidence year must immediately follow target year",
        )
        _require(evidence.get("symbol") == EXPECTED_SYMBOL, "symbol differs")
        for field, expected in {
            "accounting_standard": "CAS",
            "consolidation_scope": "consolidated",
            "language": "zh-CN",
        }.items():
            _require(
                evidence.get(field) == expected,
                f"{path.name}: {field} differs",
            )

        original_record = annual_by_year[target_year]
        evidence_record = annual_by_year[evidence_year]
        relationship = evidence.get("document_relationship")
        _require(
            relationship == evidence_record["bundle"]["document_relationship"],
            f"{path.name}: document relationship differs from annual bundle",
        )
        for source in ("company", "exchange"):
            document = evidence.get("documents", {}).get(source, {})
            annual_document = evidence_record["bundle"]["documents"][source]
            _require(
                document.get("source_tier") == annual_document["source_tier"],
                f"{path.name}: {source} source tier differs",
            )
            _require(
                document.get("source_provider")
                == annual_document["source_provider"],
                f"{path.name}: {source} source provider differs",
            )
            _require(
                document.get("source_document")
                == annual_document["source_document"],
                f"{path.name}: {source} source document differs",
            )
            _require(
                document.get("source_url")
                in {
                    annual_document["pdf_url"],
                    annual_document["final_pdf_url"],
                },
                f"{path.name}: {source} source URL is not registered",
            )
            for field in (
                "announcement_date",
                "sha256",
                "content_length",
                "page_count",
            ):
                _require(
                    document.get(field) == annual_document[field],
                    f"{path.name}: {source} {field} differs",
                )
            _require(
                bool(document.get("retrieved_at")),
                f"{path.name}: {source} retrieved_at is required",
            )

        concepts = evidence.get("concepts", [])
        _require(
            {item.get("concept_id") for item in concepts} == EXPECTED_CONCEPTS,
            f"{path.name}: concepts differ from the three-concept contract",
        )
        original_by_source = {
            source: {
                fact["concept_id"]: fact
                for fact in original_record["source_facts"][source]
            }
            for source in ("company", "exchange")
        }
        reconciled_v1 = {
            item["output_fact"]["concept_id"]: item["output_fact"]
            for item in original_record["preflight_results"]
        }

        for item in sorted(concepts, key=lambda value: value["concept_id"]):
            concept_id = item["concept_id"]
            original_raw = str(item.get("original_raw_value", ""))
            later_raw = str(item.get("later_comparative_raw_value", ""))
            expected_changed = original_raw != later_raw
            _require(
                item.get("changed") is expected_changed,
                f"{path.name}/{concept_id}: changed flag differs from values",
            )
            _require(
                item.get("review_status")
                == ("reviewed_changed" if expected_changed else "reviewed_unchanged"),
                f"{path.name}/{concept_id}: review status differs",
            )
            _require(
                item.get("raw_unit") == "人民币百万元",
                f"{path.name}/{concept_id}: raw unit differs",
            )
            for source in ("company", "exchange"):
                original = original_by_source[source][concept_id]
                _require(
                    item["original_fact_ids"].get(source)
                    == original["fact_id"],
                    f"{path.name}/{concept_id}: {source} original Fact ID differs",
                )
                _require(
                    original_raw == str(original["raw_value"]),
                    f"{path.name}/{concept_id}: original value differs",
                )
                reference = item.get(source, {})
                _require(
                    all(reference.get(field) for field in ("page", "table", "label", "column")),
                    f"{path.name}/{concept_id}: {source} reference incomplete",
                )

            comparison = {
                "target_fiscal_year": target_year,
                "evidence_fiscal_year": evidence_year,
                "concept_id": concept_id,
                "original_raw_value": original_raw,
                "later_comparative_raw_value": later_raw,
                "raw_unit": item["raw_unit"],
                "changed": expected_changed,
                "disclosed_change_reason": item["disclosed_change_reason"],
                "review_status": item["review_status"],
            }
            comparisons.append(comparison)
            if not expected_changed:
                continue

            v2_by_source: dict[str, dict[str, Any]] = {}
            for source in ("company", "exchange"):
                predecessor = original_by_source[source][concept_id]
                document = evidence["documents"][source]
                reference = item[source]
                v2 = copy.deepcopy(predecessor)
                normalized_value = int(later_raw) * 100
                v2.update(
                    {
                        "fact_version": 2,
                        "restatement_version": "restated_1",
                        "supersedes_fact_id": predecessor["fact_id"],
                        "value": normalized_value,
                        "raw_value": int(later_raw),
                        "normalized_value": normalized_value,
                        "source_provider": document["source_provider"],
                        "source_document": document["source_document"],
                        "source_url": document["source_url"],
                        "source_hash": document["sha256"],
                        "source_page": reference["page"],
                        "source_table": reference["table"],
                        "source_label": reference["label"],
                        "filing_date": document["announcement_date"],
                        "announcement_date": document["announcement_date"],
                        "available_at": document["announcement_date"],
                        "verification_note": (
                            f"reviewed comparative column in {evidence_year} "
                            f"annual report; {item['disclosed_change_reason']}"
                        ),
                        "created_at": created_at,
                    }
                )
                # source_id and source_tier intentionally remain the stable
                # logical identity of the target-year official fact chain.
                v2["fact_id"] = build_fact_id(v2)
                errors = [
                    asdict(result)
                    for result in validator.validate_single_fact(v2)
                    if result.severity == "error" and not result.passed
                ]
                _require(
                    not errors,
                    f"{path.name}/{concept_id}/{source}: v2 validation failed: {errors}",
                )
                v2_by_source[source] = v2

            preflight_result = engine.reconcile_pair(
                v2_by_source["company"],
                v2_by_source["exchange"],
                now=created_at,
            )
            _require(
                preflight_result.status == ReconciliationStatus.matched
                and preflight_result.output_fact is not None,
                f"{path.name}/{concept_id}: v2 pair did not match",
            )
            changed_pairs.append(
                {
                    "target_fiscal_year": target_year,
                    "evidence_fiscal_year": evidence_year,
                    "concept_id": concept_id,
                    "company_fact": v2_by_source["company"],
                    "exchange_fact": v2_by_source["exchange"],
                    "reconciled_v1_fact_id": reconciled_v1[concept_id]["fact_id"],
                    "available_at": max(
                        evidence["documents"][source]["announcement_date"]
                        for source in ("company", "exchange")
                    ),
                    "preflight_result": asdict(preflight_result),
                }
            )

        evidence_records.append(
            {
                "logical_path": f"601857.SH/{path.name}",
                "evidence": evidence,
            }
        )

    _require(len(comparisons) == 12, "exactly 12 comparisons are required")
    _require(len(changed_pairs) > 0, "no changed concepts were found")
    return {
        "records": evidence_records,
        "comparisons": comparisons,
        "changed_pairs": changed_pairs,
        "changed_count": len(changed_pairs),
        "review_status_2025": "not_yet_reviewable",
    }


def _persist_original_baseline(
    repo: FactRepository,
    annual_preflight: dict[str, Any],
) -> None:
    with repo.transaction() as conn:
        repo.store_contexts(
            [record["context"] for record in annual_preflight["records"]],
            conn=conn,
        )
    service = OfficialFactReconciliationService(repo)
    for record in annual_preflight["records"]:
        by_source = {
            source: {
                fact["concept_id"]: fact
                for fact in record["source_facts"][source]
            }
            for source in ("company", "exchange")
        }
        for concept_id in sorted(EXPECTED_CONCEPTS):
            result = service.reconcile_official_pair(
                by_source["company"][concept_id],
                by_source["exchange"][concept_id],
            )
            _require(
                result.status == ReconciliationStatus.matched,
                f"baseline reconciliation failed for "
                f"{record['bundle']['fiscal_year']}/{concept_id}",
            )


def _select_period_fact(
    snapshot: Any,
    *,
    period_end: str,
    concept_id: str,
) -> dict[str, Any]:
    selected = snapshot[
        (snapshot["period_end"] == period_end)
        & (snapshot["concept_id"] == concept_id)
    ]
    _require(len(selected) == 1, f"PIT selection differs for {period_end}/{concept_id}")
    return selected.iloc[0].to_dict()


def _collect_acceptance(
    repo: FactRepository,
    restatements: dict[str, Any],
) -> dict[str, Any]:
    conn = repo.store.connect()
    changed_count = restatements["changed_count"]
    expected_counts = {
        "fact_contexts": 5,
        "company_facts": 15 + changed_count,
        "exchange_facts": 15 + changed_count,
        "original_raw_facts": 30 + 2 * changed_count,
        "reconciled_facts": 15 + changed_count,
        "financial_facts": 45 + 3 * changed_count,
        "eligible_for_metrics": 15 + changed_count,
        "ineligible_raw_facts": 30 + 2 * changed_count,
        "version_chain_links": 3 * changed_count,
        "lineage": 45 + 3 * changed_count,
        "audit": 45 + 3 * changed_count,
    }
    audit = AsOfQuery(repo).get_all_versions_for_audit(
        EXPECTED_SYMBOL, sorted(EXPECTED_CONCEPTS),
    )
    counts = {
        "fact_contexts": conn.execute("SELECT COUNT(*) FROM fact_contexts").fetchone()[0],
        "company_facts": conn.execute(
            "SELECT COUNT(*) FROM financial_facts WHERE source_tier='company_official'"
        ).fetchone()[0],
        "exchange_facts": conn.execute(
            "SELECT COUNT(*) FROM financial_facts WHERE source_tier='exchange_official'"
        ).fetchone()[0],
        "original_raw_facts": conn.execute(
            "SELECT COUNT(*) FROM financial_facts WHERE is_derived=FALSE"
        ).fetchone()[0],
        "reconciled_facts": conn.execute(
            "SELECT COUNT(*) FROM financial_facts WHERE source_tier='reconciled_derived'"
        ).fetchone()[0],
        "financial_facts": conn.execute("SELECT COUNT(*) FROM financial_facts").fetchone()[0],
        "eligible_for_metrics": conn.execute(
            "SELECT COUNT(*) FROM financial_facts WHERE eligible_for_metrics=TRUE"
        ).fetchone()[0],
        "ineligible_raw_facts": conn.execute(
            "SELECT COUNT(*) FROM financial_facts "
            "WHERE is_derived=FALSE AND eligible_for_metrics=FALSE"
        ).fetchone()[0],
        "version_chain_links": conn.execute(
            "SELECT COUNT(*) FROM financial_facts WHERE supersedes_fact_id <> ''"
        ).fetchone()[0],
        "lineage": conn.execute("SELECT COUNT(*) FROM fact_lineage").fetchone()[0],
        "audit": len(audit),
    }
    _require(counts == expected_counts, f"dynamic counts differ: {counts}")

    chains = conn.execute(
        """SELECT fact_id, concept_id, source_tier, fact_version,
                  restatement_version, supersedes_fact_id, available_at,
                  value, period_end
           FROM financial_facts
           WHERE supersedes_fact_id <> ''
           ORDER BY period_end, concept_id, source_tier"""
    ).df().to_dict("records")
    _require(len(chains) == 3 * changed_count, "version-chain link count differs")

    as_of = AsOfQuery(repo)
    transitions: list[dict[str, Any]] = []
    comparisons: list[dict[str, Any]] = []
    for pair in restatements["changed_pairs"]:
        available = date.fromisoformat(pair["available_at"])
        before = (available - timedelta(days=1)).isoformat()
        on = available.isoformat()
        period_end = f"{pair['target_fiscal_year']}-12-31"
        concept_id = pair["concept_id"]
        before_fact = _select_period_fact(
            as_of.get_latest_available(
                EXPECTED_SYMBOL, before, [concept_id],
            ),
            period_end=period_end,
            concept_id=concept_id,
        )
        on_fact = _select_period_fact(
            as_of.get_latest_available(EXPECTED_SYMBOL, on, [concept_id]),
            period_end=period_end,
            concept_id=concept_id,
        )
        _require(
            int(before_fact["fact_version"]) == 1
            and int(on_fact["fact_version"]) == 2,
            f"PIT version switch failed for {period_end}/{concept_id}",
        )
        _require(
            on_fact["supersedes_fact_id"] == before_fact["fact_id"],
            f"PIT predecessor differs for {period_end}/{concept_id}",
        )
        version_comparison = as_of.compare_versions(
            EXPECTED_SYMBOL,
            [concept_id],
            period_end,
            before,
            on,
        )
        matching_comparisons = [
            value
            for value in version_comparison.values()
            if value["concept_id"] == concept_id
            and value["period_end"] == period_end
        ]
        _require(
            len(matching_comparisons) == 1
            and matching_comparisons[0]["changed"] is True,
            f"compare_versions did not detect {period_end}/{concept_id}",
        )
        transitions.append(
            {
                "target_fiscal_year": pair["target_fiscal_year"],
                "concept_id": concept_id,
                "before_date": before,
                "before_fact_id": before_fact["fact_id"],
                "before_value": before_fact["value"],
                "on_date": on,
                "on_fact_id": on_fact["fact_id"],
                "on_value": on_fact["value"],
                "supersedes_fact_id": on_fact["supersedes_fact_id"],
            }
        )
        comparisons.append(matching_comparisons[0])

    latest_date = conn.execute(
        "SELECT MAX(available_at) FROM financial_facts"
    ).fetchone()[0]
    latest = as_of.get_latest_available(
        EXPECTED_SYMBOL, latest_date, sorted(EXPECTED_CONCEPTS),
    )
    _require(len(latest) == 15, "final PIT snapshot must contain 15 facts")
    _require(
        set(latest["source_tier"]) == {"reconciled_derived"}
        and all(bool(value) for value in latest["eligible_for_metrics"]),
        "final PIT snapshot must contain only eligible reconciled facts",
    )
    per_key = latest.groupby(["period_end", "concept_id"]).size()
    _require(len(per_key) == 15 and all(int(value) == 1 for value in per_key), "PIT keys differ")

    lineage = conn.execute(
        """SELECT fact_id, run_id, source_tier, parent_fact_ids, role,
                  reconciliation_rule_id, reconciliation_rule_version
           FROM fact_lineage ORDER BY lineage_id"""
    ).df().to_dict("records")
    return {
        "counts": counts,
        "expected_counts": expected_counts,
        "version_chains": chains,
        "pit_transitions": transitions,
        "compare_versions": comparisons,
        "latest_snapshot": {
            "as_of_date": latest_date,
            "count": len(latest),
            "fact_ids": latest["fact_id"].tolist(),
        },
        "lineage": lineage,
        "audit_fact_ids": audit["fact_id"].tolist(),
    }


def run_integration(
    bundle_paths: list[str | Path],
    evidence_paths: list[str | Path],
    output_root: str | Path,
    *,
    run_id: str | None = None,
) -> dict[str, Any]:
    """Execute the offline restatement integration in a new run directory."""
    run_id = run_id or build_run_id()
    run_dir = (
        Path(output_root)
        / EXPECTED_SYMBOL
        / "restatement_version_chains"
        / "2021_2025"
        / run_id
    )
    run_dir.mkdir(parents=True, exist_ok=False)
    db_path = run_dir / "restatement_integration.duckdb"
    manifest: dict[str, Any] = {
        "run_id": run_id,
        "status": "failed",
        "transaction_committed": False,
        "offline": True,
        "symbol": EXPECTED_SYMBOL,
        "years": list(EXPECTED_YEARS),
        "integration_contract": INTEGRATION_CONTRACT,
        "restatement_evidence_contract": RESTATEMENT_CONTRACT,
        "fact_schema_version": FactRepository.schema_version,
        "database": db_path.name,
        "review_status_2025": "not_yet_reviewable",
        "started_at": datetime.now().astimezone().isoformat(),
    }
    store: DuckDBStore | None = None
    try:
        created_at = datetime.now().astimezone().isoformat()
        annual = preflight_bundles(bundle_paths, created_at=created_at)
        restatements = preflight_restatements(
            annual, evidence_paths, created_at=created_at,
        )
        _write_json(
            run_dir / "evidence_manifest.json",
            {
                "contract": RESTATEMENT_CONTRACT,
                "records": restatements["records"],
                "review_status_2025": "not_yet_reviewable",
            },
        )
        _write_json(run_dir / "comparison_results.json", restatements["comparisons"])

        store = DuckDBStore(str(db_path))
        store.connect()
        repo = FactRepository(store)
        repo.ensure_schema()
        _persist_original_baseline(repo, annual)
        service = OfficialFactReconciliationService(repo)
        persisted_results: list[dict[str, Any]] = []
        for pair in restatements["changed_pairs"]:
            result = service.reconcile_official_pair(
                pair["company_fact"],
                pair["exchange_fact"],
                output_supersedes_fact_id=pair["reconciled_v1_fact_id"],
            )
            _require(
                result.status == ReconciliationStatus.matched
                and result.output_fact is not None,
                f"v2 persistence failed for "
                f"{pair['target_fiscal_year']}/{pair['concept_id']}",
            )
            persisted_results.append(asdict(result))

        acceptance = _collect_acceptance(repo, restatements)
        _write_json(run_dir / "version_chains.json", acceptance["version_chains"])
        _write_json(run_dir / "pit_transitions.json", acceptance["pit_transitions"])
        _write_json(
            run_dir / "lineage_summary.json",
            {"count": len(acceptance["lineage"]), "rows": acceptance["lineage"]},
        )
        manifest.update(
            {
                "status": "passed",
                "transaction_committed": True,
                "changed_concept_years": restatements["changed_count"],
                "counts": acceptance["counts"],
                "latest_pit_snapshot": acceptance["latest_snapshot"],
                "compare_versions": acceptance["compare_versions"],
                "new_reconciled_fact_ids": [
                    item["output_fact"]["fact_id"] for item in persisted_results
                ],
                "completed_at": datetime.now().astimezone().isoformat(),
            }
        )
    except Exception as exc:
        manifest["error_type"] = type(exc).__name__
        manifest["error"] = str(exc)
        manifest["completed_at"] = datetime.now().astimezone().isoformat()
        if store is not None:
            store.close()
            store = None
        if db_path.exists():
            db_path.unlink()
    finally:
        if store is not None:
            store.close()

    _write_json(run_dir / "run_manifest.json", manifest)
    summary = (
        "# Restatement evidence and version chains\n\n"
        f"- run_id: `{run_id}`\n"
        f"- status: **{manifest['status']}**\n"
        "- symbol: `601857.SH`\n"
        "- fiscal years: `2021—2025`\n"
        "- offline: `true`\n"
        f"- transaction_committed: `{str(manifest['transaction_committed']).lower()}`\n"
        "- 2025 review_status: `not_yet_reviewable`\n"
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
    parser.add_argument("--bundle", action="append", required=True)
    parser.add_argument("--evidence", action="append", required=True)
    parser.add_argument("--output-root", required=True)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    result = run_integration(
        args.bundle, args.evidence, args.output_root,
    )
    print(json.dumps(_jsonable(result), ensure_ascii=False, indent=2))
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
