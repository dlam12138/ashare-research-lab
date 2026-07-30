"""Integrate five accepted annual official-fact bundles into one DuckDB.

This is deliberately a thin, offline orchestration layer. It reads committed
JSON bundles, reuses the annual acceptance builders and validators, performs
all reconciliation pairs in memory, and only then creates a run-scoped
database through the existing repository and reconciliation service.
"""

from __future__ import annotations

import argparse
import hashlib
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
from ashare_research.tools.official_fact_acceptance import (
    ACCEPTANCE_CONTRACT,
    EXPECTED_CONCEPTS,
    build_context,
    build_source_facts,
    load_bundle,
)
from ashare_research.validation.validator import FactValidator

INTEGRATION_CONTRACT = "multi_year_official_facts_v1"
EXPECTED_SYMBOL = "601857.SH"
EXPECTED_YEARS = (2021, 2022, 2023, 2024, 2025)
EXPECTED_CONTEXT_FIELDS = {
    "report_type": "annual",
    "accounting_standard": "CAS",
    "consolidation_scope": "consolidated",
    "language": "zh-CN",
}


class MultiYearIntegrationError(ValueError):
    """A deterministic multi-year integration gate failed."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise MultiYearIntegrationError(message)


def build_run_id(now: datetime | None = None) -> str:
    """Build an injectable, run-scoped integration identity."""
    timestamp = (now or datetime.now()).strftime("%Y%m%d_%H%M%S_%f")
    return f"multi_year_official_601857_SH_2021_2025_{timestamp}"


def _git_blob_id(content: bytes) -> str:
    header = f"blob {len(content)}\0".encode()
    return hashlib.sha1(header + content).hexdigest()  # noqa: S324


def _logical_bundle_name(path: Path) -> str:
    return f"{path.parent.name}/{path.name}"


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


def preflight_bundles(
    bundle_paths: list[str | Path],
    *,
    created_at: str,
) -> dict[str, Any]:
    """Validate and construct all five years before any database exists."""
    _require(len(bundle_paths) == 5, "exactly five bundle paths are required")

    loaded: list[dict[str, Any]] = []
    records: list[dict[str, Any]] = []
    seen_fact_ids: set[str] = set()
    contexts: list[dict[str, Any]] = []
    all_source_facts: list[dict[str, Any]] = []
    preflight_results: list[dict[str, Any]] = []
    validator = FactValidator()
    engine = ReconciliationEngine()

    for raw_path in bundle_paths:
        path = Path(raw_path)
        content = path.read_bytes()
        bundle = load_bundle(path)
        loaded.append({"path": path, "content": content, "bundle": bundle})

    years = [item["bundle"]["fiscal_year"] for item in loaded]
    _require(len(set(years)) == 5, "fiscal years must be unique; duplicate year found")
    _require(
        tuple(sorted(years)) == EXPECTED_YEARS,
        "fiscal years must be exactly 2021 through 2025",
    )
    symbols = {item["bundle"]["symbol"] for item in loaded}
    _require(symbols == {EXPECTED_SYMBOL}, f"symbol must be {EXPECTED_SYMBOL}")
    company_names = {item["bundle"]["company_name"] for item in loaded}
    _require(len(company_names) == 1, "company_name must match across all bundles")
    for item in loaded:
        bundle = item["bundle"]
        for field, expected in EXPECTED_CONTEXT_FIELDS.items():
            _require(
                bundle[field] == expected,
                f"{field} differs from multi-year contract",
            )

    for loaded_record in loaded:
        path = loaded_record["path"]
        content = loaded_record["content"]
        bundle = loaded_record["bundle"]
        year = bundle["fiscal_year"]
        context = build_context(bundle, created_at=created_at)
        source_facts = build_source_facts(bundle, created_at=created_at)
        facts = source_facts["company"] + source_facts["exchange"]
        _require(len(facts) == 6, f"{year} must construct six original facts")
        _require(
            all(fact["fact_version"] == 1 for fact in facts),
            f"{year} facts must use fact_version 1",
        )
        _require(
            all(fact["restatement_version"] == "original" for fact in facts),
            f"{year} facts must remain original",
        )
        _require(
            all(fact["fact_id"] == build_fact_id(fact) for fact in facts),
            f"{year} source facts must have canonical Fact IDs",
        )
        fact_ids = {fact["fact_id"] for fact in facts}
        _require(len(fact_ids) == 6, f"{year} source Fact IDs must be unique")
        _require(
            seen_fact_ids.isdisjoint(fact_ids),
            f"{year} source Fact IDs overlap another year",
        )
        seen_fact_ids.update(fact_ids)

        validation = validator.validate_batch(facts)
        errors = [
            asdict(item)
            for item in validation
            if item.severity == "error" and not item.passed
        ]
        _require(not errors, f"{year} source fact validation failed: {errors}")

        by_source = {
            source: {fact["concept_id"]: fact for fact in source_facts[source]}
            for source in ("company", "exchange")
        }
        year_results: list[dict[str, Any]] = []
        for concept_id in sorted(EXPECTED_CONCEPTS):
            result = engine.reconcile_pair(
                by_source["company"][concept_id],
                by_source["exchange"][concept_id],
                now=created_at,
            )
            _require(
                result.status == ReconciliationStatus.matched
                and result.output_fact is not None,
                f"{year}/{concept_id} reconciliation did not match",
            )
            year_results.append(asdict(result))
        _require(len(year_results) == 3, f"{year} must have three matched pairs")

        latest_available_at = max(
            document["announcement_date"]
            for document in bundle["documents"].values()
        )
        records.append(
            {
                "path": path,
                "logical_path": _logical_bundle_name(path),
                "sha256": hashlib.sha256(content).hexdigest(),
                "git_blob_id": _git_blob_id(content),
                "bundle": bundle,
                "context": context,
                "source_facts": source_facts,
                "preflight_results": year_results,
                "latest_available_at": latest_available_at,
            }
        )
        contexts.append(context)
        all_source_facts.extend(facts)
        preflight_results.extend(year_results)

    _require(len(contexts) == 5, "exactly five contexts are required")
    _require(len({item["context_id"] for item in contexts}) == 5, "contexts must be unique")
    _require(len(all_source_facts) == 30, "exactly 30 original facts are required")
    _require(len(seen_fact_ids) == 30, "all original Fact IDs must be unique")
    _require(len(preflight_results) == 15, "exactly 15 reconciliations are required")

    records.sort(key=lambda item: item["bundle"]["fiscal_year"])
    return {
        "records": records,
        "company_name": next(iter(company_names)),
        "contexts": contexts,
        "source_fact_count": len(all_source_facts),
        "reconciliation_count": len(preflight_results),
    }


def _input_manifest(preflight: dict[str, Any]) -> dict[str, Any]:
    return {
        "integration_contract": INTEGRATION_CONTRACT,
        "annual_acceptance_contract": ACCEPTANCE_CONTRACT,
        "symbol": EXPECTED_SYMBOL,
        "bundles": [
            {
                "logical_path": record["logical_path"],
                "sha256": record["sha256"],
                "git_blob_id": record["git_blob_id"],
                "fiscal_year": record["bundle"]["fiscal_year"],
                "latest_available_at": record["latest_available_at"],
                "context_id": record["context"]["context_id"],
                "concepts": sorted(EXPECTED_CONCEPTS),
                "original_fact_ids": {
                    source: [
                        fact["fact_id"]
                        for fact in record["source_facts"][source]
                    ]
                    for source in ("company", "exchange")
                },
            }
            for record in preflight["records"]
        ],
    }


def _collect_acceptance(
    repo: FactRepository,
    store: DuckDBStore,
    preflight: dict[str, Any],
) -> dict[str, Any]:
    conn = store.connect()
    as_of = AsOfQuery(repo)
    concepts = sorted(EXPECTED_CONCEPTS)
    audit = as_of.get_all_versions_for_audit(EXPECTED_SYMBOL, concepts)
    lineage = conn.execute(
        """SELECT fact_id, run_id, source_tier, parent_fact_ids, role,
                  reconciliation_rule_id, reconciliation_rule_version
           FROM fact_lineage ORDER BY lineage_id"""
    ).df()

    counts = {
        "fact_contexts": conn.execute(
            "SELECT COUNT(*) FROM fact_contexts"
        ).fetchone()[0],
        "company_original": conn.execute(
            "SELECT COUNT(*) FROM financial_facts "
            "WHERE source_tier='company_official'"
        ).fetchone()[0],
        "exchange_original": conn.execute(
            "SELECT COUNT(*) FROM financial_facts "
            "WHERE source_tier='exchange_official'"
        ).fetchone()[0],
        "original_total": conn.execute(
            "SELECT COUNT(*) FROM financial_facts WHERE is_derived=FALSE"
        ).fetchone()[0],
        "reconciled": conn.execute(
            "SELECT COUNT(*) FROM financial_facts "
            "WHERE source_tier='reconciled_derived'"
        ).fetchone()[0],
        "financial_facts": conn.execute(
            "SELECT COUNT(*) FROM financial_facts"
        ).fetchone()[0],
        "eligible_for_metrics": conn.execute(
            "SELECT COUNT(*) FROM financial_facts WHERE eligible_for_metrics=TRUE"
        ).fetchone()[0],
        "ineligible_originals": conn.execute(
            "SELECT COUNT(*) FROM financial_facts "
            "WHERE is_derived=FALSE AND eligible_for_metrics=FALSE"
        ).fetchone()[0],
        "reconciliation_matched": preflight["reconciliation_count"],
        "lineage": len(lineage),
        "audit": len(audit),
    }
    expected_counts = {
        "fact_contexts": 5,
        "company_original": 15,
        "exchange_original": 15,
        "original_total": 30,
        "reconciled": 15,
        "financial_facts": 45,
        "eligible_for_metrics": 15,
        "ineligible_originals": 30,
        "reconciliation_matched": 15,
        "lineage": 45,
        "audit": 45,
    }
    _require(counts == expected_counts, f"integration counts differ: {counts}")

    annual_results: list[dict[str, Any]] = []
    for record in preflight["records"]:
        year = record["bundle"]["fiscal_year"]
        rows = conn.execute(
            """SELECT f.fact_id, f.concept_id, f.source_tier,
                      f.eligible_for_metrics
               FROM financial_facts f
               JOIN fact_contexts c ON f.context_id = c.context_id
               WHERE c.fiscal_year = ?
               ORDER BY source_tier, concept_id""",
            [year],
        ).df()
        annual_lineage = conn.execute(
            """SELECT COUNT(*) FROM fact_lineage l
               JOIN financial_facts f ON l.fact_id = f.fact_id
               JOIN fact_contexts c ON f.context_id = c.context_id
               WHERE c.fiscal_year = ?""",
            [year],
        ).fetchone()[0]
        annual = {
            "fiscal_year": year,
            "context_id": record["context"]["context_id"],
            "company_original": int((rows["source_tier"] == "company_official").sum()),
            "exchange_original": int((rows["source_tier"] == "exchange_official").sum()),
            "reconciled": int((rows["source_tier"] == "reconciled_derived").sum()),
            "facts": len(rows),
            "lineage": annual_lineage,
            "latest_available_at": record["latest_available_at"],
            "fact_ids": rows["fact_id"].tolist(),
        }
        _require(
            {
                "company_original": annual["company_original"],
                "exchange_original": annual["exchange_original"],
                "reconciled": annual["reconciled"],
                "facts": annual["facts"],
                "lineage": annual["lineage"],
            }
            == {
                "company_original": 3,
                "exchange_original": 3,
                "reconciled": 3,
                "facts": 9,
                "lineage": 9,
            },
            f"{year} annual counts differ",
        )
        annual_results.append(annual)

    first_date = date.fromisoformat(preflight["records"][0]["latest_available_at"])
    snapshot_dates = [(first_date - timedelta(days=1)).isoformat()]
    snapshot_dates.extend(
        record["latest_available_at"] for record in preflight["records"]
    )
    pit_snapshots: list[dict[str, Any]] = []
    for index, as_of_date in enumerate(snapshot_dates):
        snapshot = as_of.get_latest_available(
            EXPECTED_SYMBOL,
            as_of_date,
            concepts,
        )
        expected_count = index * 3
        _require(
            len(snapshot) == expected_count,
            f"PIT snapshot {as_of_date} expected {expected_count} facts",
        )
        if not snapshot.empty:
            _require(
                set(snapshot["source_tier"]) == {"reconciled_derived"},
                "PIT snapshots must contain only reconciled facts",
            )
            _require(
                all(bool(value) for value in snapshot["eligible_for_metrics"]),
                "PIT snapshots must contain only eligible facts",
            )
            visible_years = {
                int(period_end[:4]) for period_end in snapshot["period_end"]
            }
            expected_years = set(EXPECTED_YEARS[:index])
            _require(
                visible_years == expected_years,
                f"PIT snapshot {as_of_date} exposed incorrect fiscal years",
            )
            snapshot_years = snapshot["period_end"].str.slice(0, 4).astype(int)
            per_year = snapshot.assign(_fiscal_year=snapshot_years).groupby(
                "_fiscal_year"
            )["concept_id"].nunique()
            _require(
                all(int(count) == 3 for count in per_year),
                "each visible PIT year must contain three concepts",
            )
        pit_snapshots.append(
            {
                "as_of_date": as_of_date,
                "count": len(snapshot),
                "fiscal_years": (
                    sorted(
                        {
                            int(period_end[:4])
                            for period_end in snapshot["period_end"]
                        }
                    )
                    if not snapshot.empty
                    else []
                ),
                "fact_ids": snapshot["fact_id"].tolist(),
            }
        )

    facts = conn.execute(
        """SELECT f.fact_id, c.fiscal_year, f.concept_id, f.source_tier,
                  f.fact_version, f.restatement_version,
                  f.supersedes_fact_id, f.available_at
           FROM financial_facts f
           JOIN fact_contexts c ON f.context_id = c.context_id
           ORDER BY c.fiscal_year, f.source_tier, f.concept_id"""
    ).df()
    _require(set(facts["fact_version"].astype(int)) == {1}, "fact_version must remain 1")
    _require(
        set(facts["restatement_version"]) == {"original"},
        "no restatement version may be created",
    )
    _require(
        all(not value for value in facts["supersedes_fact_id"]),
        "supersedes_fact_id must remain empty",
    )
    expected_available = {
        record["bundle"]["fiscal_year"]: record["latest_available_at"]
        for record in preflight["records"]
    }
    reconciled = facts[facts["source_tier"] == "reconciled_derived"]
    _require(
        all(
            row.available_at == expected_available[int(row.fiscal_year)]
            for row in reconciled.itertuples()
        ),
        "reconciled available_at must preserve each annual publication date",
    )

    return {
        "counts": counts,
        "annual_results": annual_results,
        "pit_snapshots": pit_snapshots,
        "lineage": lineage.to_dict("records"),
        "audit_fact_ids": audit["fact_id"].tolist(),
    }


def run_integration(
    bundle_paths: list[str | Path],
    output_root: str | Path,
    *,
    run_id: str | None = None,
) -> dict[str, Any]:
    """Execute the five-year offline integration and return its manifest."""
    run_id = run_id or build_run_id()
    run_dir = (
        Path(output_root)
        / EXPECTED_SYMBOL
        / "multi_year_official_facts"
        / "2021_2025"
        / run_id
    )
    run_dir.mkdir(parents=True, exist_ok=False)
    db_path = run_dir / "integration.duckdb"
    started_at = datetime.now().astimezone().isoformat()
    manifest: dict[str, Any] = {
        "run_id": run_id,
        "status": "failed",
        "transaction_committed": False,
        "offline": True,
        "symbol": EXPECTED_SYMBOL,
        "years": list(EXPECTED_YEARS),
        "integration_contract": INTEGRATION_CONTRACT,
        "annual_acceptance_contract": ACCEPTANCE_CONTRACT,
        "fact_schema_version": FactRepository.schema_version,
        "database": "integration.duckdb",
        "started_at": started_at,
    }
    store: DuckDBStore | None = None
    try:
        created_at = datetime.now().isoformat()
        preflight = preflight_bundles(bundle_paths, created_at=created_at)
        input_manifest = _input_manifest(preflight)
        _write_json(run_dir / "input_bundle_manifest.json", input_manifest)
        _write_json(
            run_dir / "annual_integration_results.json",
            [
                {
                    "fiscal_year": record["bundle"]["fiscal_year"],
                    "context": record["context"],
                    "source_facts": record["source_facts"],
                    "preflight_results": record["preflight_results"],
                }
                for record in preflight["records"]
            ],
        )

        store = DuckDBStore(str(db_path))
        store.connect()
        repo = FactRepository(store)
        repo.ensure_schema()
        with repo.transaction() as conn:
            repo.store_contexts(
                [record["context"] for record in preflight["records"]],
                conn=conn,
            )

        service = OfficialFactReconciliationService(repo)
        for record in preflight["records"]:
            source_facts = record["source_facts"]
            by_source = {
                source: {
                    fact["concept_id"]: fact for fact in source_facts[source]
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
                    f"persisted reconciliation failed: "
                    f"{record['bundle']['fiscal_year']}/{concept_id}",
                )

        acceptance = _collect_acceptance(repo, store, preflight)
        manifest.update(
            {
                "status": "passed",
                "transaction_committed": True,
                "company_name": preflight["company_name"],
                "counts": acceptance["counts"],
                "pit_snapshot_counts": [
                    item["count"] for item in acceptance["pit_snapshots"]
                ],
                "completed_at": datetime.now().astimezone().isoformat(),
            }
        )
        _write_json(
            run_dir / "annual_integration_results.json",
            acceptance["annual_results"],
        )
        _write_json(run_dir / "pit_snapshots.json", acceptance["pit_snapshots"])
        _write_json(
            run_dir / "lineage_summary.json",
            {
                "count": len(acceptance["lineage"]),
                "rows": acceptance["lineage"],
            },
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
        "# Multi-year official fact integration\n\n"
        f"- run_id: `{run_id}`\n"
        f"- status: **{manifest['status']}**\n"
        "- symbol: `601857.SH`\n"
        "- fiscal years: `2021—2025`\n"
        "- offline: `true`\n"
        "- database: `integration.duckdb` (run-scoped)\n"
        f"- transaction_committed: "
        f"`{str(manifest['transaction_committed']).lower()}`\n"
        f"- fact_schema_version: `{FactRepository.schema_version}`\n"
    )
    if "counts" in manifest:
        summary += "\n## Counts\n\n" + "\n".join(
            f"- {key}: {value}" for key, value in manifest["counts"].items()
        ) + "\n"
    if "error" in manifest:
        summary += f"\n## Failure\n\n{manifest['error']}\n"
    (run_dir / "integration_summary.md").write_text(summary, encoding="utf-8")
    return {**manifest, "run_directory": run_dir}


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", action="append", required=True)
    parser.add_argument("--output-root", required=True)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    result = run_integration(args.bundle, args.output_root)
    print(json.dumps(_jsonable(result), ensure_ascii=False, indent=2))
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
