"""Build the offline 2021-2025 earnings-quality official Fact foundation."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import shutil
import tempfile
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any

from ashare_research.facts.as_of import AsOfQuery
from ashare_research.facts.identity import build_fact_id
from ashare_research.facts.repository import FactRepository
from ashare_research.reconciliation.engine import (
    EARNINGS_QUALITY_RECONCILIATION_RULE,
    EARNINGS_QUALITY_RULE_ID,
    ReconciliationEngine,
)
from ashare_research.reconciliation.models import ReconciliationStatus
from ashare_research.reconciliation.service import OfficialFactReconciliationService
from ashare_research.storage.duckdb_store import DuckDBStore
from ashare_research.tools.earnings_quality_document_contract import (
    EXPECTED_CONCEPTS,
    validate_earnings_quality_document_contract,
)
from ashare_research.tools.official_earnings_quality_2025_acceptance import (
    DEFAULT_DB,
    DEFAULT_DB_SHA256,
    run_earnings_quality_acceptance,
)
from ashare_research.tools.official_fact_acceptance import (
    build_source_facts,
    load_bundle,
)
from ashare_research.validation.validator import FactValidator

ROOT = Path(__file__).resolve().parents[3]
BUNDLE_DIR = ROOT / "acceptance/fixtures/official_facts/601857.SH"
REVIEW_DIR = ROOT / "acceptance/fixtures/restatements/601857.SH"
SYMBOL = "601857.SH"
CONTRACT = "earnings_quality_fact_foundation_v1"
REVIEW_CONTRACT = "earnings_quality_restatement_evidence_v1"
EXPECTED_R = 4
EXPECTED_COUNTS = {
    "fact_contexts": 5,
    "upstream_financial_facts": 84,
    "financial_facts": 132,
    "company_facts": 44,
    "exchange_facts": 44,
    "reconciled_facts": 44,
    "raw_facts": 88,
    "eligible_for_metrics": 44,
    "version_chain_links": 27,
    "audit": 132,
    "lineage": 132,
    "rule_003_reconciliations": 19,
    "rule_003_lineage": 57,
}


class EarningsQualityFoundationError(ValueError):
    """An offline evidence or integration gate failed."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise EarningsQualityFoundationError(message)


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    _require(isinstance(value, dict), f"{path.name}: object required")
    return value


def _write(path: Path, value: Any) -> None:
    def convert(item: Any) -> Any:
        if isinstance(item, Path):
            return str(item)
        if isinstance(item, dict):
            return {str(key): convert(val) for key, val in item.items()}
        if isinstance(item, list | tuple):
            return [convert(val) for val in item]
        if hasattr(item, "item"):
            return item.item()
        return item

    path.write_text(
        json.dumps(convert(value), ensure_ascii=False, indent=2, default=str) + "\n",
        encoding="utf-8",
    )


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _id_digest(ids: list[str]) -> str:
    raw = json.dumps(sorted(ids), separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


def _build_fact(
    template: dict[str, Any],
    item: dict[str, Any],
    document: dict[str, Any],
    *,
    created_at: str,
) -> dict[str, Any]:
    fact = copy.deepcopy(template)
    normalized = int(item["expected_normalized_value"])
    fact.update(
        concept_id=item["concept_id"],
        concept_version="1",
        value=normalized,
        unit="万元",
        source_provider=document.get("source_provider", template["source_provider"]),
        source_document=document["source_document"],
        source_url=document["source_url"],
        source_hash=document["source_hash"],
        source_page=item["source_page"],
        source_table=item["source_table"],
        source_label=item["source_label"],
        raw_value=int(item["raw_value"]),
        raw_unit=item["raw_unit"],
        normalized_value=normalized,
        normalization_rule=item["normalization_rule"],
        filing_date=document["announcement_date"],
        announcement_date=document["announcement_date"],
        available_at=document["announcement_date"],
        verification_note=(
            f"visually verified twice; document_key={item['document_key']}; "
            f"document_scope={item['document_scope']}"
        ),
        fact_version=1,
        restatement_version="original",
        supersedes_fact_id="",
        eligible_for_metrics=False,
        created_at=created_at,
    )
    fact["fact_id"] = build_fact_id(fact)
    errors = [
        result
        for result in FactValidator().validate_single_fact(fact)
        if result.severity == "error" and not result.passed
    ]
    _require(not errors, f"{item['concept_id']}: Fact validation failed")
    return fact


def _preflight(created_at: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    records = []
    for year in range(2021, 2025):
        bundle_path = BUNDLE_DIR / f"{year}_annual.json"
        evidence_path = BUNDLE_DIR / "supplemental" / f"{year}_earnings_quality.json"
        bundle = load_bundle(bundle_path)
        evidence = validate_earnings_quality_document_contract(
            _load(evidence_path), bundle
        )
        _require(
            evidence["base_bundle_sha256"] == _sha(bundle_path),
            f"{year}: base bundle digest differs",
        )
        templates = {
            source: {
                fact["concept_id"]: fact
                for fact in build_source_facts(bundle, created_at=created_at)[source]
            }
            for source in ("company", "exchange")
        }
        by_source = {}
        for source in ("company", "exchange"):
            by_source[source] = {}
            for item in evidence["sources"][source]["facts"]:
                fact = _build_fact(
                    templates[source]["revenue"],
                    item,
                    evidence["documents"][item["document_key"]],
                    created_at=created_at,
                )
                by_source[source][item["concept_id"]] = fact
        for concept in EXPECTED_CONCEPTS:
            _require(
                by_source["company"][concept]["value"]
                == by_source["exchange"][concept]["value"],
                f"{year}/{concept}: official values differ",
            )
        bridge = evidence["non_recurring_bridge"]
        item_total = sum(int(item["amount"]) for item in bridge["items"])
        computed = (
            item_total
            + int(bridge["income_tax_effect"])
            + int(bridge["minority_interest_effect"])
        )
        direct = (
            int(bridge["net_profit_attributable_to_parent"])
            - int(bridge["net_profit_excluding_non_recurring"])
        )
        _require(
            item_total == int(bridge["item_subtotal"])
            and computed == direct == int(bridge["reported_final_net_effect"])
            and bridge["exact_tie_out"] is True,
            f"{year}: non-recurring bridge does not tie exactly",
        )
        if year == 2021:
            _require(
                bridge["bridge_status"] == "reconciled_cross_document"
                and bridge["company_itemized_bridge_available"] is False
                and bridge["exchange_itemized_bridge_available"] is True,
                "2021 cross-document bridge scope differs",
            )
        records.append(
            {"year": year, "evidence": evidence, "source_facts": by_source}
        )

    reviews = []
    for year in range(2021, 2025):
        review = _load(
            REVIEW_DIR / f"earnings_quality_{year}_reviewed_by_{year + 1}.json"
        )
        _require(review.get("contract") == REVIEW_CONTRACT, "review contract differs")
        original = next(item for item in records if item["year"] == year)
        for item in review["concepts"]:
            concept = item["concept_id"]
            predecessor = original["source_facts"]["company"][concept]
            changed = int(item["later_comparative_raw_value"]) != int(
                item["original_raw_value"]
            )
            _require(item["changed"] is changed, f"{year}/{concept}: flag differs")
            _require(
                int(item["original_raw_value"]) == int(predecessor["raw_value"]),
                f"{year}/{concept}: original value differs",
            )
            if changed:
                reviews.append({"year": year, "item": item, "record": original})
    _require(len(reviews) == EXPECTED_R, f"R differs: {len(reviews)}")
    return records, reviews


def run_earnings_quality_foundation(
    output_root: str | Path, *, run_id: str | None = None
) -> dict[str, Any]:
    """Rebuild the frozen 84-fact upstream and add reviewed Rule 003 facts."""
    run_id = run_id or datetime.now().strftime("earnings_quality_%Y%m%d_%H%M%S_%f")
    run_dir = Path(output_root) / SYMBOL / "earnings_quality_fact_foundation" / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    manifest: dict[str, Any] = {
        "contract": CONTRACT,
        "run_id": run_id,
        "status": "failed",
        "transaction_committed": False,
        "offline": True,
        "network_access": False,
        "pdf_access": False,
        "cache_access": False,
        "downloaded": 0,
    }
    store = None
    try:
        default_before = _sha(DEFAULT_DB)
        created_at = datetime.now().astimezone().isoformat()
        records, changed = _preflight(created_at)
        with tempfile.TemporaryDirectory(prefix="stage2cc1_") as temp_root:
            upstream = run_earnings_quality_acceptance(
                BUNDLE_DIR / "supplemental/2025_earnings_quality.json",
                temp_root,
                run_id="upstream_2025",
            )
            _require(upstream["status"] == "passed", "upstream acceptance failed")
            source_db = next(Path(upstream["run_directory"]).rglob("*.duckdb"))
            db_path = run_dir / "earnings_quality.duckdb"
            shutil.copy2(source_db, db_path)
        store = DuckDBStore(str(db_path))
        repo = FactRepository(store)
        upstream_fact_ids = [
            row[0]
            for row in store.connect().execute(
                "SELECT fact_id FROM financial_facts ORDER BY fact_id"
            ).fetchall()
        ]
        _require(len(upstream_fact_ids) == 84, "upstream Fact count differs")
        upstream_fact_id_set_sha256 = _id_digest(upstream_fact_ids)
        service = OfficialFactReconciliationService(
            repo, engine=ReconciliationEngine(EARNINGS_QUALITY_RECONCILIATION_RULE)
        )
        v1_results = []
        v1_outputs = {}
        for record in records:
            for concept in sorted(EXPECTED_CONCEPTS):
                result = service.reconcile_official_pair(
                    record["source_facts"]["company"][concept],
                    record["source_facts"]["exchange"][concept],
                )
                _require(
                    result.status == ReconciliationStatus.matched
                    and result.output_fact is not None,
                    f"{record['year']}/{concept}: v1 failed",
                )
                v1_results.append(asdict(result))
                v1_outputs[(record["year"], concept)] = result.output_fact

        v2_results = []
        transitions = []
        for change in changed:
            year = change["year"]
            item = change["item"]
            concept = item["concept_id"]
            later_bundle = load_bundle(BUNDLE_DIR / f"{year + 1}_annual.json")
            pair = {}
            for source in ("company", "exchange"):
                predecessor = change["record"]["source_facts"][source][concept]
                document = later_bundle["documents"][source]
                fact = copy.deepcopy(predecessor)
                raw = int(item["later_comparative_raw_value"])
                fact.update(
                    value=raw * 100,
                    raw_value=raw,
                    normalized_value=raw * 100,
                    source_provider=document["source_provider"],
                    source_document=document["source_document"],
                    source_url=document.get("final_pdf_url") or document["pdf_url"],
                    source_hash=document["sha256"],
                    source_page=f"PDF comparative disclosure for {year}",
                    filing_date=document["announcement_date"],
                    announcement_date=document["announcement_date"],
                    available_at=document["announcement_date"],
                    fact_version=2,
                    restatement_version="restated_1",
                    supersedes_fact_id=predecessor["fact_id"],
                    verification_note=(
                        f"visually verified comparative; "
                        f"{item['disclosed_change_reason']}"
                    ),
                    created_at=created_at,
                )
                fact["fact_id"] = build_fact_id(fact)
                pair[source] = fact
            result = service.reconcile_official_pair(
                pair["company"],
                pair["exchange"],
                output_supersedes_fact_id=v1_outputs[(year, concept)]["fact_id"],
            )
            _require(result.output_fact is not None, f"{year}/{concept}: v2 failed")
            v2_results.append(asdict(result))
            transitions.append(
                {
                    "target_fiscal_year": year,
                    "concept_id": concept,
                    "available_at": pair["company"]["available_at"],
                    "from_fact_id": v1_outputs[(year, concept)]["fact_id"],
                    "to_fact_id": result.output_fact["fact_id"],
                }
            )

        conn = store.connect()
        counts = {
            "fact_contexts": conn.execute(
                "SELECT COUNT(*) FROM fact_contexts"
            ).fetchone()[0],
            "upstream_financial_facts": len(upstream_fact_ids),
            "financial_facts": conn.execute(
                "SELECT COUNT(*) FROM financial_facts"
            ).fetchone()[0],
            "company_facts": conn.execute(
                "SELECT COUNT(*) FROM financial_facts "
                "WHERE source_tier='company_official'"
            ).fetchone()[0],
            "exchange_facts": conn.execute(
                "SELECT COUNT(*) FROM financial_facts "
                "WHERE source_tier='exchange_official'"
            ).fetchone()[0],
            "reconciled_facts": conn.execute(
                "SELECT COUNT(*) FROM financial_facts "
                "WHERE source_tier='reconciled_derived'"
            ).fetchone()[0],
            "raw_facts": conn.execute(
                "SELECT COUNT(*) FROM financial_facts WHERE is_derived=FALSE"
            ).fetchone()[0],
            "eligible_for_metrics": conn.execute(
                "SELECT COUNT(*) FROM financial_facts "
                "WHERE eligible_for_metrics=TRUE"
            ).fetchone()[0],
            "version_chain_links": conn.execute(
                "SELECT COUNT(*) FROM financial_facts "
                "WHERE supersedes_fact_id <> ''"
            ).fetchone()[0],
            "audit": len(AsOfQuery(repo).get_all_versions_for_audit(SYMBOL)),
            "lineage": conn.execute("SELECT COUNT(*) FROM fact_lineage").fetchone()[0],
            "rule_003_reconciliations": 3 + len(v1_results) + len(v2_results),
            "rule_003_lineage": conn.execute(
                "SELECT COUNT(*) FROM fact_lineage WHERE reconciliation_rule_id=?",
                [EARNINGS_QUALITY_RULE_ID],
            ).fetchone()[0],
        }
        _require(counts == EXPECTED_COUNTS, f"counts differ: {counts}")
        persisted_upstream_ids = {
            row[0]
            for row in conn.execute(
                "SELECT fact_id FROM financial_facts "
                "WHERE fact_id IN (SELECT UNNEST(?))",
                [upstream_fact_ids],
            ).fetchall()
        }
        _require(
            persisted_upstream_ids == set(upstream_fact_ids),
            "original 84 Fact IDs changed",
        )
        latest_date = conn.execute(
            "SELECT MAX(available_at) FROM financial_facts"
        ).fetchone()[0]
        latest = AsOfQuery(repo).get_latest_available(SYMBOL, latest_date)
        _require(len(latest) == 35, "final PIT count differs")
        annual_pit = [0]
        as_of = AsOfQuery(repo)
        for year in range(2021, 2026):
            bundle = load_bundle(BUNDLE_DIR / f"{year}_annual.json")
            availability = max(
                document["announcement_date"]
                for document in bundle["documents"].values()
            )
            annual_pit.append(len(as_of.get_latest_available(SYMBOL, availability)))
        _require(annual_pit == [0, 7, 14, 21, 28, 35], "annual PIT differs")
        fact_ids = [
            row[0]
            for row in conn.execute(
                "SELECT fact_id FROM financial_facts ORDER BY fact_id"
            ).fetchall()
        ]
        lineage = conn.execute(
            "SELECT * FROM fact_lineage ORDER BY lineage_id"
        ).df().to_dict("records")
        new_fact_ids = sorted(set(fact_ids) - set(upstream_fact_ids))
        version_chains = conn.execute(
            """SELECT fact_id, concept_id, source_tier, fact_version,
                      restatement_version, supersedes_fact_id, available_at
                 FROM financial_facts WHERE supersedes_fact_id <> ''
                 ORDER BY period_end, concept_id, source_tier"""
        ).df().to_dict("records")
        _write(run_dir / "evidence_manifest.json", {"years": list(range(2021, 2026))})
        _write(run_dir / "reconciliation_results.json", v1_results + v2_results)
        _write(run_dir / "restatement_results.json", transitions)
        _write(
            run_dir / "latest_fact_snapshot.json",
            {"as_of_date": latest_date, "count": len(latest), "rows": latest},
        )
        _write(run_dir / "lineage_summary.json", {"count": len(lineage), "rows": lineage})
        manifest.update(
            status="passed",
            transaction_committed=True,
            R=len(changed),
            counts=counts,
            latest_pit_count=len(latest),
            annual_cumulative_pit=annual_pit,
            upstream_fact_id_count=len(upstream_fact_ids),
            upstream_fact_id_set_sha256=upstream_fact_id_set_sha256,
            frozen_metric_results=upstream["frozen_metric_results"],
            new_fact_ids=new_fact_ids,
            version_chains=version_chains,
            fact_id_set_sha256=_id_digest(fact_ids),
            metric_computation="not_performed",
            scoring="not_implemented",
            default_db_sha256_before=default_before,
            default_db_sha256_after=_sha(DEFAULT_DB),
        )
        _require(
            default_before == manifest["default_db_sha256_after"] == DEFAULT_DB_SHA256,
            "default database changed",
        )
    except Exception as exc:
        manifest.update(error_type=type(exc).__name__, error=str(exc))
    finally:
        if store is not None:
            store.close()
    _write(run_dir / "run_manifest.json", manifest)
    (run_dir / "acceptance_summary.md").write_text(
        f"# Earnings-quality foundation\n\n- status: **{manifest['status']}**\n"
        f"- run_id: `{run_id}`\n- R: `{manifest.get('R', 'n/a')}`\n",
        encoding="utf-8",
    )
    return {**manifest, "run_directory": run_dir}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", required=True)
    parser.add_argument("--run-id")
    args = parser.parse_args(argv)
    result = run_earnings_quality_foundation(args.output_root, run_id=args.run_id)
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
