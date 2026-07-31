"""Accept PetroChina's 2025 ROE/ROA average-balance denominator facts.

This offline runner rebuilds the frozen 132-fact Stage 2C-C.1 / 2C-D
upstream, registers two instant (balance-sheet) contexts, and reconciles
four instant facts -- ``total_assets`` and ``equity_attributable_to_parent``
at 2024-12-31 and 2025-12-31 -- via Rule 004.  It handles the 2024
reviewed-by-2025 restatement (R changed concepts), writes only to a
run-scoped DuckDB, and emits the 2025 average-balance input pairs without
computing any average, ratio, or score.

It never opens a PDF, accesses the shared cache or network, computes a
Metric, or writes the default research database.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import shutil
import tempfile
from dataclasses import asdict
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

from ashare_research.facts.as_of import AsOfQuery
from ashare_research.facts.contexts import build_context_id
from ashare_research.facts.identity import build_fact_id
from ashare_research.facts.repository import FactRepository
from ashare_research.reconciliation.engine import (
    ROE_ROA_DENOMINATOR_RECONCILIATION_RULE,
    ROE_ROA_DENOMINATOR_RULE_ID,
    ROE_ROA_DENOMINATOR_RULE_VERSION,
    ReconciliationEngine,
)
from ashare_research.reconciliation.models import ReconciliationStatus
from ashare_research.reconciliation.service import (
    OfficialFactReconciliationService,
)
from ashare_research.storage.duckdb_store import DuckDBStore
from ashare_research.tools.official_earnings_quality_fact_foundation import (
    DEFAULT_DB,
    DEFAULT_DB_SHA256,
    REVIEW_DIR,
    SYMBOL,
    run_earnings_quality_foundation,
)
from ashare_research.tools.official_fact_acceptance import load_bundle

ROOT = Path(__file__).resolve().parents[3]
BUNDLE_DIR = ROOT / "acceptance/fixtures/official_facts/601857.SH"
SUPP_DIR = BUNDLE_DIR / "supplemental"
DEFAULT_2024_EVIDENCE = SUPP_DIR / "2024_roe_roa_denominators.json"
DEFAULT_2025_EVIDENCE = SUPP_DIR / "2025_roe_roa_denominators.json"
DEFAULT_RESTATEMENT = (
    REVIEW_DIR / "roe_roa_denominators_2024_reviewed_by_2025.json"
)

CONTRACT = "roe_roa_denominator_official_facts_v1"
INTEGRATION_CONTRACT = "roe_roa_denominator_2025_acceptance_v1"
YEARS = (2024, 2025)
CONCEPTS = frozenset({"total_assets", "equity_attributable_to_parent"})
UPSTREAM_FACT_COUNT = 132
UPSTREAM_ELIGIBLE_COUNT = 44
UPSTREAM_PIT_COUNT = 35
UPSTREAM_VERSION_LINKS = 27
UPSTREAM_FACT_ID_SET_SHA256 = (
    "1e5267022b8062acf96fb413f09ecfc737c706b786c9f02a0b1dc3834fab604d"
)
# Contexts: 5 duration (2021-2025) + 2 instant (2024, 2025).
EXPECTED_CONTEXTS = 7


class DenominatorAcceptanceError(ValueError):
    """A deterministic evidence or integration gate failed."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise DenominatorAcceptanceError(message)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git_blob_id(path: Path) -> str:
    content = path.read_bytes()
    header = f"blob {len(content)}\0".encode()
    return hashlib.sha1(header + content).hexdigest()  # noqa: S324


def _id_set_digest(ids: list[str]) -> str:
    payload = json.dumps(sorted(ids), separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()


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


def _load_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    _require(isinstance(value, dict), f"{path.name}: expected JSON object")
    return value


def build_run_id(now: datetime | None = None) -> str:
    timestamp = (now or datetime.now()).strftime("%Y%m%d_%H%M%S_%f")
    return f"roe_roa_denominator_601857_SH_2024_2025_{timestamp}"


def _instant_context_id(fiscal_year: int) -> str:
    return build_context_id(SYMBOL, fiscal_year, "instant", "consolidated")


def _build_instant_context(fiscal_year: int, *, created_at: str) -> dict[str, Any]:
    period = f"{fiscal_year}-12-31"
    return {
        "context_id": _instant_context_id(fiscal_year),
        "symbol": SYMBOL,
        "fiscal_year": fiscal_year,
        "period_type": "instant",
        "period_start": period,
        "period_end": period,
        "instant_or_duration": "instant",
        "consolidation_scope": "consolidated",
        "accounting_standard": "CAS",
        "restatement_version": "original",
        "source_document": f"PetroChina {fiscal_year} annual report",
        "filing_date": period,
        "created_at": created_at,
    }


def _validate_evidence_fact(item: dict[str, Any], source: str, year: int) -> None:
    concept_id = str(item.get("concept_id", ""))
    _require(concept_id in CONCEPTS, f"{source}: unsupported concept")
    _require(
        isinstance(item.get("pdf_page"), int)
        and isinstance(item.get("printed_page"), int),
        f"{source}/{concept_id}: page fields differ",
    )
    for field in (
        "source_page",
        "source_table",
        "source_label",
        "column_label",
        "raw_value",
        "raw_unit",
        "normalization_rule",
        "evidence_type",
        "manual_review_status",
    ):
        _require(bool(str(item.get(field, "")).strip()), (
            f"{source}/{concept_id}: missing {field}"
        ))
    _require(
        item["manual_review_status"] == "visually_verified_twice",
        f"{source}/{concept_id}: manual review differs",
    )
    _require(
        item["evidence_type"] == "audited_consolidated_balance_sheet",
        f"{source}/{concept_id}: evidence type differs",
    )
    raw = int(str(item["raw_value"]))
    normalized = int(item["expected_normalized_value"])
    _require(
        raw * 100 == normalized,
        f"{source}/{concept_id}: million-to-10k conversion differs",
    )
    _require(
        abs(normalized) <= 2**53 - 1,
        f"{source}/{concept_id}: exceeds safe integer range",
    )


def _validate_evidence(
    evidence_path: Path,
    *,
    bundle: dict[str, Any],
) -> dict[str, Any]:
    """Validate one supplemental denominator evidence file in memory."""
    evidence = _load_object(evidence_path)
    base_path = (ROOT / str(evidence.get("base_bundle_path", ""))).resolve()
    expected_base = Path(bundle["_bundle_path"]).resolve()  # type: ignore[arg-type]
    _require(base_path == expected_base, "base bundle path differs")
    _require(
        evidence.get("base_bundle_sha256") == _sha256(expected_base),
        "base bundle SHA-256 differs",
    )
    _require(
        evidence.get("base_bundle_git_blob") == _git_blob_id(expected_base),
        "base bundle Git blob differs",
    )
    _require(evidence.get("contract") == CONTRACT, "evidence contract differs")
    _require(
        evidence.get("symbol") == SYMBOL and evidence.get("fiscal_year")
        == bundle["fiscal_year"],
        "symbol/fiscal_year differs",
    )
    _require(
        evidence.get("period_type") == "instant"
        and evidence.get("period_end")
        == f"{bundle['fiscal_year']}-12-31",
        "instant period differs",
    )
    _require(
        (evidence.get("reconciliation_rule_id"),
         evidence.get("reconciliation_rule_version"))
        == (ROE_ROA_DENOMINATOR_RULE_ID, ROE_ROA_DENOMINATOR_RULE_VERSION),
        "Rule 004 binding differs",
    )
    sources = evidence.get("sources", {})
    _require(
        isinstance(sources, dict) and set(sources) == {"company", "exchange"},
        "exactly company and exchange evidence are required",
    )
    by_source: dict[str, dict[str, dict[str, Any]]] = {}
    for source in ("company", "exchange"):
        document = bundle["documents"][source]
        _require(
            document["source_tier"] == f"{source}_official",
            f"{source}: source tier differs",
        )
        facts = sources[source].get("facts", [])
        _require(
            isinstance(facts, list)
            and len(facts) == 2
            and {item.get("concept_id") for item in facts} == CONCEPTS,
            f"{source}: expected exactly two target facts",
        )
        for item in facts:
            _validate_evidence_fact(item, source, bundle["fiscal_year"])
        by_source[source] = {
            str(item["concept_id"]): item for item in facts
        }
    for concept_id in CONCEPTS:
        _require(
            by_source["company"][concept_id]["expected_normalized_value"]
            == by_source["exchange"][concept_id]["expected_normalized_value"],
            f"{concept_id}: company and exchange values differ",
        )
    return {"evidence": evidence, "by_source": by_source}


def _build_instant_fact(
    template_fact: dict[str, Any],
    evidence_item: dict[str, Any],
    document: dict[str, Any],
    *,
    fiscal_year: int,
    created_at: str,
) -> dict[str, Any]:
    """Build one verified, ineligible instant fact from evidence."""
    normalized = int(evidence_item["expected_normalized_value"])
    period = f"{fiscal_year}-12-31"
    fact = copy.deepcopy(template_fact)
    # Reset derivation fields to a verified raw instant fact.
    fact.update(
        {
            "concept_id": evidence_item["concept_id"],
            "concept_version": "1",
            "value": normalized,
            "unit": "万元",
            "context_id": _instant_context_id(fiscal_year),
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
            "source_page": evidence_item["source_page"],
            "source_table": evidence_item["source_table"],
            "source_label": evidence_item["source_label"],
            "raw_value": int(str(evidence_item["raw_value"])),
            "raw_unit": evidence_item["raw_unit"],
            "normalized_value": normalized,
            "normalization_rule": evidence_item["normalization_rule"],
            "fiscal_year": fiscal_year,
            "report_type": "annual",
            "period_start": period,
            "period_end": period,
            "filing_date": document["announcement_date"],
            "announcement_date": document["announcement_date"],
            "available_at": document["announcement_date"],
            "verification_status": "verified",
            "verification_note": (
                "manually verified twice against registered instant "
                "denominator evidence"
            ),
            "fact_version": 1,
            "restatement_version": "original",
            "supersedes_fact_id": "",
            "eligible_for_metrics": False,
            "created_at": created_at,
        }
    )
    fact["fact_id"] = build_fact_id(fact)
    return fact


def preflight_evidence(
    evidence_2024: str | Path,
    evidence_2025: str | Path,
    *,
    created_at: str,
) -> dict[str, Any]:
    """Validate both supplemental evidence files and preflight all four pairs."""
    path_2024 = Path(evidence_2024)
    path_2025 = Path(evidence_2025)
    bundle_2024 = load_bundle(BUNDLE_DIR / "2024_annual.json")
    bundle_2024["_bundle_path"] = BUNDLE_DIR / "2024_annual.json"  # type: ignore[assignment]
    bundle_2025 = load_bundle(BUNDLE_DIR / "2025_annual.json")
    bundle_2025["_bundle_path"] = BUNDLE_DIR / "2025_annual.json"  # type: ignore[assignment]

    validated = {
        2024: _validate_evidence(path_2024, bundle=bundle_2024),
        2025: _validate_evidence(path_2025, bundle=bundle_2025),
    }
    # Use the revenue template (duration) only as a shape carrier; the instant
    # context/period/value override everything identity-relevant.
    templates = {
        year: {
            src: build_instant_template(bundle, created_at=created_at)
            for src in ("company", "exchange")
        }
        for year, bundle in ((2024, bundle_2024), (2025, bundle_2025))
    }
    source_facts: dict[int, dict[str, dict[str, dict[str, Any]]]] = {}
    preflight_results = []
    engine = ReconciliationEngine(ROE_ROA_DENOMINATOR_RECONCILIATION_RULE)
    for year in YEARS:
        source_facts[year] = {"company": {}, "exchange": {}}
        bundle = bundle_2024 if year == 2024 else bundle_2025
        validated_year = validated[year]
        for concept_id in sorted(CONCEPTS):
            for source in ("company", "exchange"):
                fact = _build_instant_fact(
                    templates[year][source],
                    validated_year["by_source"][source][concept_id],
                    bundle["documents"][source],
                    fiscal_year=year,
                    created_at=created_at,
                )
                source_facts[year][source][concept_id] = fact
            result = engine.reconcile_pair(
                source_facts[year]["company"][concept_id],
                source_facts[year]["exchange"][concept_id],
                now=created_at,
            )
            _require(
                result.status == ReconciliationStatus.matched
                and result.output_fact is not None,
                f"{year}/{concept_id}: Rule 004 preflight did not match",
            )
            preflight_results.append(result)
    return {
        "path_2024": path_2024,
        "path_2025": path_2025,
        "evidence_2024": validated[2024]["evidence"],
        "evidence_2025": validated[2025]["evidence"],
        "source_facts": source_facts,
        "preflight_results": preflight_results,
    }


def build_instant_template(
    bundle: dict[str, Any], *, created_at: str
) -> dict[str, Any]:
    """A minimal shape carrier for instant fact construction.

    All identity-relevant fields are overwritten in ``_build_instant_fact``;
    this template only supplies the canonical fields required by the
    financial_fact schema (``created_at`` etc.).
    """
    document = bundle["documents"]["company"]
    return {
        "symbol": bundle["symbol"],
        "concept_id": "total_assets",
        "concept_version": "1",
        "context_id": _instant_context_id(bundle["fiscal_year"]),
        "source_provider": document["source_provider"],
        "source_id": document["source_id"],
        "source_tier": document["source_tier"],
        "source_document": document["source_document"],
        "source_url": document["final_pdf_url"],
        "source_hash": document["sha256"],
        "fiscal_year": bundle["fiscal_year"],
        "report_type": "annual",
        "period_end": f"{bundle['fiscal_year']}-12-31",
        "filing_date": document["announcement_date"],
        "announcement_date": document["announcement_date"],
        "available_at": document["announcement_date"],
        "verification_status": "verified",
        "is_derived": False,
        "derived_from": "",
        "derivation_definition_id": "",
        "derivation_version": "",
        "input_fact_ids": "",
        "unit": "万元",
        "value": 0,
        "raw_value": 0,
        "raw_unit": "人民币百万元",
        "normalized_value": 0,
        "normalization_rule": "RMB_MILLION_TO_CNY_10K_X100",
        "fact_version": 1,
        "restatement_version": "original",
        "supersedes_fact_id": "",
        "eligible_for_metrics": False,
        "created_at": created_at,
    }


def _resolve_restatement(
    restatement_path: Path,
    preflight: dict[str, Any],
) -> dict[str, Any]:
    """Read the 2024-reviewed-by-2025 restatement evidence and confirm R."""
    review = _load_object(restatement_path)
    _require(
        review.get("contract") == "roe_roa_denominator_restatement_evidence_v1",
        "restatement contract differs",
    )
    _require(
        review.get("target_fiscal_year") == 2024
        and review.get("evidence_fiscal_year") == 2025,
        "restatement target/evidence years differ",
    )
    concepts = review.get("concepts", [])
    _require(
        {item["concept_id"] for item in concepts} == CONCEPTS
        and len(concepts) == 2,
        "restatement concepts differ",
    )
    changed_concepts: list[str] = []
    for item in concepts:
        concept = item["concept_id"]
        original_fact = preflight["source_facts"][2024]["company"][concept]
        computed_changed = int(item["later_comparative_raw_value"]) != int(
            item["original_raw_value"]
        )
        _require(item["changed"] is computed_changed, f"{concept}: flag differs")
        _require(
            int(item["original_raw_value"]) == int(original_fact["raw_value"]),
            f"{concept}: original value differs from preflight",
        )
        if computed_changed:
            changed_concepts.append(concept)
    r = len(changed_concepts)
    _require(r in (0, 1, 2), f"R out of range: {r}")
    return {"review": review, "r": r, "changed_concepts": changed_concepts}


def _collect_acceptance(
    repo: FactRepository,
    *,
    upstream_fact_ids: list[str],
    reconciliations: list[dict[str, Any]],
    restatement: dict[str, Any],
    preflight: dict[str, Any],
) -> dict[str, Any]:
    conn = repo.store.connect()
    r = restatement["r"]
    counts = {
        "contexts": conn.execute(
            "SELECT COUNT(*) FROM fact_contexts"
        ).fetchone()[0],
        "financial_facts": conn.execute(
            "SELECT COUNT(*) FROM financial_facts"
        ).fetchone()[0],
        "raw_ineligible_facts": conn.execute(
            "SELECT COUNT(*) FROM financial_facts "
            "WHERE is_derived=FALSE AND eligible_for_metrics=FALSE"
        ).fetchone()[0],
        "reconciled_eligible_facts": conn.execute(
            "SELECT COUNT(*) FROM financial_facts "
            "WHERE source_tier='reconciled_derived' "
            "AND eligible_for_metrics=TRUE"
        ).fetchone()[0],
        "version_chain_links": conn.execute(
            "SELECT COUNT(*) FROM financial_facts "
            "WHERE supersedes_fact_id <> ''"
        ).fetchone()[0],
        "audit": len(AsOfQuery(repo).get_all_versions_for_audit(SYMBOL)),
        "lineage": conn.execute(
            "SELECT COUNT(*) FROM fact_lineage"
        ).fetchone()[0],
    }
    expected = {
        "contexts": EXPECTED_CONTEXTS,
        "financial_facts": 144 + 3 * r,
        "raw_ineligible_facts": 96 + 2 * r,
        "reconciled_eligible_facts": 48 + r,
        "version_chain_links": 27 + 3 * r,
        "audit": 144 + 3 * r,
        "lineage": 144 + 3 * r,
    }
    _require(counts == expected, f"counts differ: {counts} (expected {expected})")

    current_upstream_ids = [
        row[0]
        for row in conn.execute(
            "SELECT fact_id FROM financial_facts "
            "WHERE fact_id IN (SELECT UNNEST(?)) ORDER BY fact_id",
            [upstream_fact_ids],
        ).fetchall()
    ]
    _require(
        current_upstream_ids == sorted(upstream_fact_ids)
        and _id_set_digest(current_upstream_ids) == UPSTREAM_FACT_ID_SET_SHA256,
        "upstream 132 Fact IDs changed",
    )
    # Rule 001/002/003 lineage must be unchanged.
    _require(
        conn.execute(
            "SELECT COUNT(*) FROM fact_lineage "
            "WHERE reconciliation_rule_id='RECON_OFFICIAL_NUMERIC_001'"
        ).fetchone()[0]
        == 57,
        "Rule 001 lineage changed",
    )
    _require(
        conn.execute(
            "SELECT COUNT(*) FROM fact_lineage "
            "WHERE reconciliation_rule_id='RECON_OFFICIAL_NUMERIC_002'"
        ).fetchone()[0]
        == 18,
        "Rule 002 lineage changed",
    )
    _require(
        conn.execute(
            "SELECT COUNT(*) FROM fact_lineage "
            "WHERE reconciliation_rule_id='RECON_OFFICIAL_NUMERIC_003'"
        ).fetchone()[0]
        == 57,
        "Rule 003 lineage changed",
    )
    rule_004_lineage = conn.execute(
        """SELECT fact_id, source_tier, parent_fact_ids, role,
                  reconciliation_rule_id, reconciliation_rule_version
             FROM fact_lineage
            WHERE reconciliation_rule_id=?
            ORDER BY lineage_id""",
        [ROE_ROA_DENOMINATOR_RULE_ID],
    ).df().to_dict("records")
    # 4 reconciliations x 3 lineage roles = 12 rows (plus 3*r for v2).
    _require(
        len(rule_004_lineage) == 12 + 3 * r
        and {row["reconciliation_rule_version"] for row in rule_004_lineage}
        == {ROE_ROA_DENOMINATOR_RULE_VERSION},
        "Rule 004 lineage differs",
    )

    as_of = AsOfQuery(repo)
    annual_2024 = max(
        d["announcement_date"]
        for d in load_bundle(BUNDLE_DIR / "2024_annual.json")["documents"].values()
    )
    annual_2025 = max(
        d["announcement_date"]
        for d in load_bundle(BUNDLE_DIR / "2025_annual.json")["documents"].values()
    )
    pit_2024_report = as_of.get_latest_available(SYMBOL, annual_2024)
    pit_2025_report = as_of.get_latest_available(SYMBOL, annual_2025)
    _require(len(pit_2024_report) == 30, "PIT at 2024 report availability differs")
    _require(len(pit_2025_report) == 39, "PIT at 2025 report availability differs")

    # changed 2024 instant facts switch v1 -> v2 on the 2025 announcement date.
    for concept in restatement["changed_concepts"]:
        before = as_of.get_latest_available(
            SYMBOL,
            (date.fromisoformat(annual_2025) - timedelta(days=1)).isoformat(),
            [concept],
        )
        on = as_of.get_latest_available(SYMBOL, annual_2025, [concept])
        _require(
            len(before) == 1
            and int(before.iloc[0]["fact_version"]) == 1
            and len(on) == 1
            and int(on.iloc[0]["fact_version"]) == 2,
            f"{concept}: PIT version switch differs",
        )

    # compare_versions must detect changed concepts via AsOfQuery.
    if restatement["changed_concepts"]:
        comparison = as_of.compare_versions(
            SYMBOL,
            restatement["changed_concepts"],
            "2024-12-31",
            (date.fromisoformat(annual_2025) - timedelta(days=1)).isoformat(),
            annual_2025,
        )
        for entry in comparison.values():
            _require(entry["changed"] is True, "compare_versions missed a change")

    final = as_of.get_latest_available(SYMBOL, annual_2025)
    _require(len(final) == 39, "final latest Fact PIT must contain 39 facts")

    output_ids = {
        item["output_fact"]["fact_id"] for item in reconciliations
    }
    instant_rows = final[final["context_id"].str.contains("|instant|", regex=False)]
    _require(
        set(instant_rows[instant_rows["source_tier"] == "reconciled_derived"][
            "fact_id"
        ])
        == output_ids,
        "PIT instant reconciled outputs differ from reconciliation results",
    )
    return {
        "counts": counts,
        "expected_counts": expected,
        "R": r,
        "pit_at_2024_report": {
            "as_of_date": annual_2024,
            "count": len(pit_2024_report),
        },
        "pit_at_2025_report": {
            "as_of_date": annual_2025,
            "count": len(pit_2025_report),
        },
        "final_pit": {
            "as_of_date": annual_2025,
            "count": len(final),
            "fact_ids": final["fact_id"].tolist(),
        },
        "rule_004_lineage": rule_004_lineage,
        "upstream_fact_id_set_sha256": _id_set_digest(current_upstream_ids),
    }


def _build_average_balance_pairs(
    repo: FactRepository,
) -> dict[str, Any]:
    """Register the two 2025 average-balance candidate input pairs.

    Each pair links the latest 2024 instant fact to the 2025 instant fact
    for one concept.  No average is computed; ``ready_for_average`` is
    true only when both members share the same consolidation_scope and unit.
    """
    annual_2025 = max(
        d["announcement_date"]
        for d in load_bundle(BUNDLE_DIR / "2025_annual.json")["documents"].values()
    )
    as_of = AsOfQuery(repo)
    pairs = []
    for concept in sorted(CONCEPTS):
        latest = as_of.get_latest_available(SYMBOL, annual_2025, [concept])
        # One row per period_end instant date (2024-12-31, 2025-12-31).
        # Use the reconciled (eligible) row for each.  consolidation_scope is
        # encoded in context_id (SYMBOL|FY|instant|consolidated), not a column.
        rows = latest[latest["source_tier"] == "reconciled_derived"].sort_values(
            "period_end"
        )
        _require(
            len(rows) == 2,
            f"{concept}: expected two reconciled instant rows for the pair",
        )
        beginning = rows.iloc[0]
        ending = rows.iloc[1]
        _require(
            str(beginning["period_end"]) == "2024-12-31"
            and str(ending["period_end"]) == "2025-12-31",
            f"{concept}: average-balance pair period ordering differs",
        )
        begin_scope = str(beginning["context_id"]).split("|")[-1]
        end_scope = str(ending["context_id"]).split("|")[-1]
        ready = (
            begin_scope == end_scope
            and str(beginning["unit"]) == str(ending["unit"])
        )
        pairs.append(
            {
                "concept_id": concept,
                "fiscal_year": 2025,
                "beginning": {
                    "fact_id": str(beginning["fact_id"]),
                    "period_end": "2024-12-31",
                    "context_id": str(beginning["context_id"]),
                    "consolidation_scope": begin_scope,
                    "unit": str(beginning["unit"]),
                    "value": int(beginning["value"]),
                },
                "ending": {
                    "fact_id": str(ending["fact_id"]),
                    "period_end": "2025-12-31",
                    "context_id": str(ending["context_id"]),
                    "consolidation_scope": end_scope,
                    "unit": str(ending["unit"]),
                    "value": int(ending["value"]),
                },
                "ready_for_average": bool(ready),
            }
        )
    return {
        "contract": "average_balance_input_pairs_v1",
        "fiscal_year": 2025,
        "note": (
            "candidate average-balance inputs only; no average computed"
        ),
        "pairs": pairs,
    }


def _database_path(upstream_dir: Path) -> Path:
    matches = list(upstream_dir.rglob("earnings_quality.duckdb"))
    _require(len(matches) == 1, "upstream run-scoped DuckDB count differs")
    return matches[0]


def run_denominator_acceptance(
    evidence_2024: str | Path,
    evidence_2025: str | Path,
    restatement_path: str | Path,
    output_root: str | Path,
    *,
    run_id: str | None = None,
) -> dict[str, Any]:
    """Execute the complete offline 2025 ROE/ROA denominator acceptance."""
    run_id = run_id or build_run_id()
    run_dir = (
        Path(output_root)
        / SYMBOL
        / "roe_roa_denominator_official_facts"
        / "2024_2025"
        / run_id
    )
    run_dir.mkdir(parents=True, exist_ok=False)
    upstream_dir = run_dir / "upstream_earnings_quality"
    db_path = run_dir / "roe_roa_denominators.duckdb"
    started_at = datetime.now().astimezone().isoformat()
    manifest: dict[str, Any] = {
        "run_id": run_id,
        "status": "failed",
        "transaction_committed": False,
        "offline": True,
        "network_access": False,
        "pdf_access": False,
        "cache_access": False,
        "downloaded": 0,
        "symbol": SYMBOL,
        "years": list(YEARS),
        "integration_contract": INTEGRATION_CONTRACT,
        "evidence_contract": CONTRACT,
        "reconciliation_rule_id": ROE_ROA_DENOMINATOR_RULE_ID,
        "reconciliation_rule_version": ROE_ROA_DENOMINATOR_RULE_VERSION,
        "metric_computation": "not_performed",
        "scoring": "not_implemented",
        "started_at": started_at,
    }
    store: DuckDBStore | None = None
    try:
        default_hash_before = _sha256(DEFAULT_DB)
        created_at = datetime.now().astimezone().isoformat()
        preflight = preflight_evidence(
            evidence_2024, evidence_2025, created_at=created_at,
        )
        restatement = _resolve_restatement(
            Path(restatement_path), preflight,
        )
        with tempfile.TemporaryDirectory(prefix="m2_stage2da_") as temp_root:
            upstream = run_earnings_quality_foundation(
                temp_root, run_id="upstream_132",
            )
            _require(
                upstream["status"] == "passed",
                "Stage 2C-C.1 upstream foundation failed",
            )
            shutil.move(str(upstream["run_directory"]), str(upstream_dir))
        _require(
            upstream["counts"]["financial_facts"] == UPSTREAM_FACT_COUNT
            and upstream["counts"]["eligible_for_metrics"] == UPSTREAM_ELIGIBLE_COUNT
            and upstream["latest_pit_count"] == UPSTREAM_PIT_COUNT
            and upstream["counts"]["version_chain_links"] == UPSTREAM_VERSION_LINKS,
            "Stage 2C-C.1 upstream counts differ",
        )
        source_db = _database_path(upstream_dir)
        upstream_hash_before = _sha256(source_db)
        shutil.copy2(source_db, db_path)
        store = DuckDBStore(str(db_path))
        repo = FactRepository(store)
        conn = store.connect()
        upstream_fact_ids = [
            row[0]
            for row in conn.execute(
                "SELECT fact_id FROM financial_facts ORDER BY fact_id"
            ).fetchall()
        ]
        _require(
            len(upstream_fact_ids) == UPSTREAM_FACT_COUNT
            and _id_set_digest(upstream_fact_ids) == UPSTREAM_FACT_ID_SET_SHA256,
            "Stage 2C-C.1 frozen 132 Fact ID set differs",
        )

        # Register the two instant contexts (must not reuse duration contexts).
        with repo.transaction() as tx:
            repo.store_contexts(
                [
                    _build_instant_context(2024, created_at=created_at),
                    _build_instant_context(2025, created_at=created_at),
                ],
                conn=tx,
            )

        service = OfficialFactReconciliationService(
            repo,
            engine=ReconciliationEngine(
                ROE_ROA_DENOMINATOR_RECONCILIATION_RULE
            ),
        )
        # v1 reconciliations for all four concept-dates.
        persisted = []
        v1_outputs: dict[tuple[int, str], dict[str, Any]] = {}
        for year in YEARS:
            for concept in sorted(CONCEPTS):
                result = service.reconcile_official_pair(
                    preflight["source_facts"][year]["company"][concept],
                    preflight["source_facts"][year]["exchange"][concept],
                )
                _require(
                    result.status == ReconciliationStatus.matched
                    and result.output_fact is not None,
                    f"{year}/{concept}: Rule 004 persistence failed",
                )
                persisted.append(asdict(result))
                v1_outputs[(year, concept)] = result.output_fact

        # v2 reconciliations only for changed 2024 concepts (R-driven).
        v2_persisted = []
        transitions = []
        for concept in restatement["changed_concepts"]:
            later_bundle = load_bundle(BUNDLE_DIR / "2025_annual.json")
            pair: dict[str, dict[str, Any]] = {}
            for source in ("company", "exchange"):
                predecessor = preflight["source_facts"][2024][source][concept]
                document = later_bundle["documents"][source]
                later_raw = int(
                    restatement["review"]["concepts"][
                        next(
                            i
                            for i, c in enumerate(
                                restatement["review"]["concepts"]
                            )
                            if c["concept_id"] == concept
                        )
                    ]["later_comparative_raw_value"]
                )
                fact = copy.deepcopy(predecessor)
                fact.update(
                    value=later_raw * 100,
                    raw_value=later_raw,
                    normalized_value=later_raw * 100,
                    source_provider=document["source_provider"],
                    source_id=document["source_id"],
                    source_tier=document["source_tier"],
                    source_document=document["source_document"],
                    source_url=document["final_pdf_url"],
                    source_hash=document["sha256"],
                    filing_date=document["announcement_date"],
                    announcement_date=document["announcement_date"],
                    available_at=document["announcement_date"],
                    fact_version=2,
                    restatement_version="restated_1",
                    supersedes_fact_id=predecessor["fact_id"],
                    created_at=created_at,
                )
                fact["fact_id"] = build_fact_id(fact)
                pair[source] = fact
            result = service.reconcile_official_pair(
                pair["company"],
                pair["exchange"],
                output_supersedes_fact_id=v1_outputs[(2024, concept)]["fact_id"],
            )
            _require(
                result.output_fact is not None,
                f"2024/{concept}: Rule 004 v2 failed",
            )
            v2_persisted.append(asdict(result))
            transitions.append(
                {
                    "target_fiscal_year": 2024,
                    "concept_id": concept,
                    "available_at": pair["company"]["available_at"],
                    "from_fact_id": v1_outputs[(2024, concept)]["fact_id"],
                    "to_fact_id": result.output_fact["fact_id"],
                }
            )
        all_reconciliations = persisted + v2_persisted

        acceptance = _collect_acceptance(
            repo,
            upstream_fact_ids=upstream_fact_ids,
            reconciliations=all_reconciliations,
            restatement=restatement,
            preflight=preflight,
        )
        average_pairs = _build_average_balance_pairs(repo)
        _require(
            all(pair["ready_for_average"] for pair in average_pairs["pairs"]),
            "average-balance input pair scope/unit mismatch",
        )
        _write_json(
            run_dir / "evidence_manifest.json",
            {
                "contract": CONTRACT,
                "logical_paths": [
                    Path(evidence_2024).name,
                    Path(evidence_2025).name,
                ],
                "base_bundles": ["2024_annual.json", "2025_annual.json"],
                "R": restatement["r"],
                "revision_review_status": {
                    "2024": "reviewed_unchanged",
                    "2025": "not_yet_reviewable",
                },
            },
        )
        _write_json(
            run_dir / "reconciliation_results.json", all_reconciliations
        )
        _write_json(run_dir / "restatement_results.json", transitions)
        _write_json(
            run_dir / "lineage_summary.json",
            {
                "count": len(acceptance["rule_004_lineage"]),
                "rows": acceptance["rule_004_lineage"],
            },
        )
        _write_json(
            run_dir / "latest_fact_snapshot.json", acceptance["final_pit"]
        )
        _write_json(
            run_dir / "average_balance_input_pairs.json", average_pairs
        )
        upstream_hash_after = _sha256(source_db)
        _require(
            upstream_hash_before == upstream_hash_after,
            "acceptance modified upstream foundation DuckDB",
        )
        default_hash_after = _sha256(DEFAULT_DB)
        _require(
            default_hash_before == default_hash_after == DEFAULT_DB_SHA256,
            "default research.duckdb changed",
        )
        manifest.update(
            {
                "status": "passed",
                "transaction_committed": True,
                "R": restatement["r"],
                "upstream": {
                    "status": upstream["status"],
                    "financial_facts": UPSTREAM_FACT_COUNT,
                    "eligible_facts": UPSTREAM_ELIGIBLE_COUNT,
                    "latest_fact_pit": UPSTREAM_PIT_COUNT,
                    "version_chain_links": UPSTREAM_VERSION_LINKS,
                    "fact_id_set_sha256": (
                        acceptance["upstream_fact_id_set_sha256"]
                    ),
                    "sha256_before": upstream_hash_before,
                    "sha256_after": upstream_hash_after,
                },
                "counts": acceptance["counts"],
                "expected_counts": acceptance["expected_counts"],
                "pit_at_2024_report": acceptance["pit_at_2024_report"],
                "pit_at_2025_report": acceptance["pit_at_2025_report"],
                "final_pit": acceptance["final_pit"],
                "new_raw_fact_ids": sorted(
                    preflight["source_facts"][year][source][concept]["fact_id"]
                    for year in YEARS
                    for source in ("company", "exchange")
                    for concept in sorted(CONCEPTS)
                ),
                "new_reconciled_fact_ids": sorted(
                    item["output_fact"]["fact_id"] for item in persisted
                ),
                "v2_reconciled_fact_ids": sorted(
                    item["output_fact"]["fact_id"] for item in v2_persisted
                ),
                "restatement_transitions": transitions,
                "average_balance_input_pairs": average_pairs,
                "default_db_sha256_before": default_hash_before,
                "default_db_sha256_after": default_hash_after,
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
        "# 2025 ROE/ROA denominator official fact acceptance\n\n"
        f"- run_id: `{run_id}`\n"
        f"- status: **{manifest['status']}**\n"
        "- offline: `true`\n"
        f"- transaction_committed: "
        f"`{str(manifest['transaction_committed']).lower()}`\n"
        "- Metric computation: `not performed`\n"
        "- scoring: `not implemented`\n"
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
    parser.add_argument(
        "--evidence-2024", default=str(DEFAULT_2024_EVIDENCE),
    )
    parser.add_argument(
        "--evidence-2025", default=str(DEFAULT_2025_EVIDENCE),
    )
    parser.add_argument(
        "--restatement", default=str(DEFAULT_RESTATEMENT),
    )
    parser.add_argument("--output-root", required=True)
    parser.add_argument("--run-id")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    result = run_denominator_acceptance(
        args.evidence_2024,
        args.evidence_2025,
        args.restatement,
        args.output_root,
        run_id=args.run_id,
    )
    print(json.dumps(_jsonable(result), ensure_ascii=False, indent=2))
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
