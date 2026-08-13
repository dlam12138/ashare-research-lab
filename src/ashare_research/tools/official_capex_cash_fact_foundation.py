"""Build PetroChina's 2021-2025 capex-cash official fact foundation.

The tool is deliberately offline.  It validates committed supplemental and
restatement evidence, calls the accepted Stage 1D-B integration to rebuild
the frozen 57-fact upstream, then adds only
``cash_paid_for_fixed_assets`` using ``RECON_OFFICIAL_NUMERIC_002`` v1.
It never opens a PDF, accesses the network, computes a Metric, or writes the
default research database.
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
from ashare_research.facts.identity import build_fact_id
from ashare_research.facts.repository import FactRepository
from ashare_research.reconciliation.engine import (
    CAPEX_CASH_RECONCILIATION_RULE,
    SUPPLEMENTAL_RULE_ID,
    SUPPLEMENTAL_RULE_VERSION,
    ReconciliationEngine,
)
from ashare_research.reconciliation.models import ReconciliationStatus
from ashare_research.reconciliation.service import (
    OfficialFactReconciliationService,
)
from ashare_research.storage.duckdb_store import DuckDBStore
from ashare_research.tools.official_fact_acceptance import EXPECTED_CONCEPTS
from ashare_research.tools.official_fact_multi_year_integration import (
    EXPECTED_SYMBOL,
    EXPECTED_YEARS,
    preflight_bundles,
)
from ashare_research.tools.official_fact_restatement_integration import (
    run_integration as run_restatement_integration,
)
from ashare_research.validation.validator import FactValidator

SUPPLEMENTAL_CONTRACT = "supplemental_annual_official_facts_v1"
CAPEX_RESTATEMENT_CONTRACT = "capex_cash_restatement_evidence_v1"
INTEGRATION_CONTRACT = "capex_cash_fact_foundation_v1"
CAPEX_CONCEPT = "cash_paid_for_fixed_assets"
ALL_CONCEPTS = frozenset({*EXPECTED_CONCEPTS, CAPEX_CONCEPT})
EXPECTED_TARGET_YEARS = (2021, 2022, 2023, 2024)
UPSTREAM_FACT_COUNT = 57
UPSTREAM_LATEST_PIT_COUNT = 15
UPSTREAM_FACT_ID_SET_SHA256 = (
    "e2afd5d39ae97f2488f5e9a713fda578174c38c5ea13e37d12e8844a8f29d829"
)


class CapexCashFoundationError(ValueError):
    """A deterministic evidence or integration gate failed."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise CapexCashFoundationError(message)


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


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git_blob_id(path: Path) -> str:
    content = path.read_bytes()
    header = f"blob {len(content)}\0".encode()
    return hashlib.sha1(header + content).hexdigest()  # noqa: S324


def _id_set_digest(fact_ids: list[str]) -> str:
    payload = json.dumps(sorted(fact_ids), separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()


def build_run_id(now: datetime | None = None) -> str:
    timestamp = (now or datetime.now()).strftime("%Y%m%d_%H%M%S_%f")
    return f"capex_cash_foundation_601857_SH_2021_2025_{timestamp}"


def _load_json(path: str | Path) -> dict[str, Any]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    _require(isinstance(value, dict), f"{path}: evidence must be an object")
    return value


def _validate_bound_file(
    evidence: dict[str, Any],
    *,
    path_field: str,
    sha_field: str,
    blob_field: str,
    actual_path: Path,
    label: str,
) -> None:
    registered = Path(str(evidence.get(path_field, ""))).resolve()
    _require(registered == actual_path.resolve(), f"{label}: path differs")
    _require(
        evidence.get(sha_field) == _sha256(actual_path),
        f"{label}: SHA-256 differs",
    )
    _require(
        evidence.get(blob_field) == _git_blob_id(actual_path),
        f"{label}: Git blob differs",
    )


def _build_capex_fact(
    template: dict[str, Any],
    evidence: dict[str, Any],
    *,
    created_at: str,
) -> dict[str, Any]:
    raw_value = int(str(evidence["raw_value"]))
    normalized = int(evidence["expected_normalized_value"])
    _require(
        raw_value * 100 == normalized,
        "supplemental normalized value must be exact million-to-10k x100",
    )
    fact = copy.deepcopy(template)
    fact.update(
        {
            "concept_id": CAPEX_CONCEPT,
            "concept_version": "1",
            "value": normalized,
            "source_page": evidence["source_page"],
            "source_table": evidence["source_table"],
            "source_label": evidence["source_label"],
            "raw_value": raw_value,
            "raw_unit": evidence["raw_unit"],
            "normalized_value": normalized,
            "normalization_rule": evidence["normalization_rule"],
            "verification_note": (
                "manually verified twice against audited consolidated "
                "cash flow statement"
            ),
            "created_at": created_at,
        }
    )
    fact["fact_id"] = build_fact_id(fact)
    return fact


def preflight_supplemental_evidence(
    bundle_paths: list[str | Path],
    supplemental_paths: list[str | Path],
    *,
    created_at: str,
) -> dict[str, Any]:
    """Validate all base bindings and construct five v1 pairs in memory."""
    _require(len(bundle_paths) == 5, "exactly five annual bundles are required")
    _require(
        len(supplemental_paths) == 5,
        "exactly five supplemental evidence files are required",
    )
    annual = preflight_bundles(bundle_paths, created_at=created_at)
    annual_by_year = {
        int(record["bundle"]["fiscal_year"]): record
        for record in annual["records"]
    }
    bundle_paths_by_year = {
        int(json.loads(Path(path).read_text(encoding="utf-8"))["fiscal_year"]):
        Path(path)
        for path in bundle_paths
    }
    loaded = [(Path(path), _load_json(path)) for path in supplemental_paths]
    loaded.sort(key=lambda item: int(item[1].get("fiscal_year", 0)))
    _require(
        tuple(int(item[1].get("fiscal_year", 0)) for item in loaded)
        == EXPECTED_YEARS,
        "supplemental years must be exactly 2021 through 2025",
    )

    engine = ReconciliationEngine(CAPEX_CASH_RECONCILIATION_RULE)
    validator = FactValidator()
    records: list[dict[str, Any]] = []
    for path, evidence in loaded:
        year = int(evidence["fiscal_year"])
        _require(
            evidence.get("contract") == SUPPLEMENTAL_CONTRACT,
            f"{path.name}: unexpected supplemental contract",
        )
        _require(evidence.get("symbol") == EXPECTED_SYMBOL, "symbol differs")
        _require(
            evidence.get("concept_id") == CAPEX_CONCEPT,
            f"{path.name}: concept differs",
        )
        expected_review = (
            "not_yet_reviewable"
            if year == 2025
            else ("reviewed_changed" if year == 2023 else "reviewed_unchanged")
        )
        _require(
            evidence.get("restatement_review_status") == expected_review,
            f"{path.name}: restatement review status differs",
        )
        bundle_path = bundle_paths_by_year[year]
        _validate_bound_file(
            evidence,
            path_field="base_bundle_path",
            sha_field="base_bundle_sha256",
            blob_field="base_bundle_git_blob",
            actual_path=bundle_path,
            label=path.name,
        )

        annual_record = annual_by_year[year]
        by_source = {
            source: {
                fact["concept_id"]: fact
                for fact in annual_record["source_facts"][source]
            }
            for source in ("company", "exchange")
        }
        source_facts: dict[str, dict[str, Any]] = {}
        for source in ("company", "exchange"):
            item = evidence.get(source, {})
            _require(
                all(
                    item.get(field) not in (None, "")
                    for field in (
                        "source_page",
                        "pdf_page",
                        "printed_page",
                        "source_table",
                        "source_label",
                        "column_label",
                        "source_display_value",
                        "raw_value",
                        "raw_unit",
                        "normalization_rule",
                        "expected_normalized_value",
                        "manual_review_status",
                    )
                ),
                f"{path.name}: {source} evidence is incomplete",
            )
            _require(
                item["source_label"]
                == "购建固定资产、油气资产、无形资产和其他长期资产支付的现金",
                f"{path.name}: source label differs",
            )
            _require(
                item["column_label"] == f"{year}年度合并",
                f"{path.name}: {source} did not use target-year consolidated column",
            )
            _require(
                item["raw_unit"] == "人民币百万元"
                and item["normalization_rule"]
                == "RMB_MILLION_TO_CNY_10K_X100"
                and item["manual_review_status"] == "visually_verified_twice",
                f"{path.name}: {source} evidence contract differs",
            )
            source_facts[source] = _build_capex_fact(
                by_source[source]["operating_cash_flow"],
                item,
                created_at=created_at,
            )
            errors = [
                asdict(result)
                for result in validator.validate_single_fact(source_facts[source])
                if result.severity == "error" and not result.passed
            ]
            _require(
                not errors,
                f"{path.name}/{source}: source validation failed: {errors}",
            )
        _require(
            source_facts["company"]["raw_value"]
            == source_facts["exchange"]["raw_value"],
            f"{path.name}: company and exchange values differ",
        )
        result = engine.reconcile_pair(
            source_facts["company"],
            source_facts["exchange"],
            now=created_at,
        )
        _require(
            result.status == ReconciliationStatus.matched
            and result.output_fact is not None,
            f"{path.name}: supplemental reconciliation did not match",
        )
        records.append(
            {
                "path": path,
                "evidence": evidence,
                "bundle": annual_record["bundle"],
                "source_facts": source_facts,
                "preflight_result": result,
            }
        )
    return {"annual": annual, "records": records}


def preflight_capex_restatements(
    supplemental: dict[str, Any],
    review_paths: list[str | Path],
    bundle_paths: list[str | Path],
    *,
    created_at: str,
) -> dict[str, Any]:
    """Validate four comparisons and construct only real changed v2 pairs."""
    _require(
        len(review_paths) == 4,
        "exactly four capex restatement reviews are required",
    )
    annual_by_year = {
        int(record["bundle"]["fiscal_year"]): record
        for record in supplemental["annual"]["records"]
    }
    supplement_by_year = {
        int(record["evidence"]["fiscal_year"]): record
        for record in supplemental["records"]
    }
    bundle_paths_by_year = {
        int(json.loads(Path(path).read_text(encoding="utf-8"))["fiscal_year"]):
        Path(path)
        for path in bundle_paths
    }
    loaded = [(Path(path), _load_json(path)) for path in review_paths]
    loaded.sort(key=lambda item: int(item[1].get("target_fiscal_year", 0)))
    _require(
        tuple(int(item[1].get("target_fiscal_year", 0)) for item in loaded)
        == EXPECTED_TARGET_YEARS,
        "capex review target years must be exactly 2021 through 2024",
    )

    engine = ReconciliationEngine(CAPEX_CASH_RECONCILIATION_RULE)
    validator = FactValidator()
    comparisons: list[dict[str, Any]] = []
    changed_pairs: list[dict[str, Any]] = []
    records: list[dict[str, Any]] = []
    for path, evidence in loaded:
        target_year = int(evidence["target_fiscal_year"])
        evidence_year = int(evidence["evidence_fiscal_year"])
        _require(
            evidence.get("contract") == CAPEX_RESTATEMENT_CONTRACT,
            f"{path.name}: unexpected capex review contract",
        )
        _require(
            evidence.get("symbol") == EXPECTED_SYMBOL
            and evidence.get("concept_id") == CAPEX_CONCEPT,
            f"{path.name}: symbol or concept differs",
        )
        _require(
            evidence_year == target_year + 1,
            f"{path.name}: evidence year must immediately follow target year",
        )
        evidence_bundle_path = bundle_paths_by_year[evidence_year]
        _validate_bound_file(
            evidence,
            path_field="evidence_bundle_path",
            sha_field="evidence_bundle_sha256",
            blob_field="evidence_bundle_git_blob",
            actual_path=evidence_bundle_path,
            label=path.name,
        )
        original_record = supplement_by_year[target_year]
        original_raw = str(evidence.get("original_raw_value", ""))
        later_raw = str(evidence.get("later_comparative_raw_value", ""))
        _require(
            original_raw
            == str(original_record["source_facts"]["company"]["raw_value"])
            == str(original_record["source_facts"]["exchange"]["raw_value"]),
            f"{path.name}: original value differs from supplemental evidence",
        )
        _require(
            evidence.get("raw_unit") == "人民币百万元",
            f"{path.name}: raw unit differs",
        )
        changed = original_raw != later_raw
        _require(
            evidence.get("changed") is changed,
            f"{path.name}: changed flag differs from values",
        )
        _require(
            evidence.get("review_status")
            == ("reviewed_changed" if changed else "reviewed_unchanged"),
            f"{path.name}: review status differs",
        )
        later_record = annual_by_year[evidence_year]
        for source in ("company", "exchange"):
            reference = evidence.get(source, {})
            document = later_record["bundle"]["documents"][source]
            _require(
                reference.get("announcement_date")
                == document["announcement_date"],
                f"{path.name}: {source} announcement date differs",
            )
            _require(
                all(
                    reference.get(field) not in (None, "")
                    for field in (
                        "source_page",
                        "pdf_page",
                        "printed_page",
                        "source_table",
                        "source_label",
                        "column_label",
                        "source_display_value",
                        "manual_review_status",
                    )
                ),
                f"{path.name}: {source} review reference incomplete",
            )
            _require(
                reference["column_label"] == f"{target_year}年度合并"
                and reference["manual_review_status"]
                == "visually_verified_twice",
                f"{path.name}: {source} comparison contract differs",
            )

        comparisons.append(
            {
                "target_fiscal_year": target_year,
                "evidence_fiscal_year": evidence_year,
                "concept_id": CAPEX_CONCEPT,
                "original_raw_value": original_raw,
                "later_comparative_raw_value": later_raw,
                "raw_unit": evidence["raw_unit"],
                "changed": changed,
                "disclosed_change_reason": evidence["disclosed_change_reason"],
                "review_status": evidence["review_status"],
            }
        )
        if changed:
            v2_by_source: dict[str, dict[str, Any]] = {}
            for source in ("company", "exchange"):
                predecessor = original_record["source_facts"][source]
                document = later_record["bundle"]["documents"][source]
                reference = evidence[source]
                normalized = int(later_raw) * 100
                v2 = copy.deepcopy(predecessor)
                v2.update(
                    {
                        "fact_version": 2,
                        "restatement_version": "restated_1",
                        "supersedes_fact_id": predecessor["fact_id"],
                        "value": normalized,
                        "raw_value": int(later_raw),
                        "normalized_value": normalized,
                        "source_provider": document["source_provider"],
                        "source_document": document["source_document"],
                        "source_url": (
                            document.get("final_pdf_url")
                            or document["pdf_url"]
                        ),
                        "source_hash": document["sha256"],
                        "source_page": reference["source_page"],
                        "source_table": reference["source_table"],
                        "source_label": reference["source_label"],
                        "filing_date": document["announcement_date"],
                        "announcement_date": document["announcement_date"],
                        "available_at": document["announcement_date"],
                        "verification_note": (
                            f"reviewed comparative column in {evidence_year} "
                            f"annual report; "
                            f"{evidence['disclosed_change_reason']}"
                        ),
                        "created_at": created_at,
                    }
                )
                v2["fact_id"] = build_fact_id(v2)
                errors = [
                    asdict(result)
                    for result in validator.validate_single_fact(v2)
                    if result.severity == "error" and not result.passed
                ]
                _require(
                    not errors,
                    f"{path.name}/{source}: v2 validation failed: {errors}",
                )
                v2_by_source[source] = v2
            result = engine.reconcile_pair(
                v2_by_source["company"],
                v2_by_source["exchange"],
                now=created_at,
            )
            _require(
                result.status == ReconciliationStatus.matched
                and result.output_fact is not None,
                f"{path.name}: v2 reconciliation did not match",
            )
            changed_pairs.append(
                {
                    "target_fiscal_year": target_year,
                    "evidence_fiscal_year": evidence_year,
                    "company_fact": v2_by_source["company"],
                    "exchange_fact": v2_by_source["exchange"],
                    "reconciled_v1_fact_id": (
                        original_record["preflight_result"].output_fact["fact_id"]
                    ),
                    "available_at": max(
                        v2_by_source[source]["available_at"]
                        for source in ("company", "exchange")
                    ),
                    "preflight_result": result,
                }
            )
        records.append({"path": path, "evidence": evidence})
    _require(len(changed_pairs) == 1, "real evidence must produce C = 1")
    return {
        "records": records,
        "comparisons": comparisons,
        "changed_pairs": changed_pairs,
        "changed_count": len(changed_pairs),
        "review_status_2025": "not_yet_reviewable",
    }


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
    _require(len(selected) == 1, f"PIT selection differs for {period_end}")
    return selected.iloc[0].to_dict()


def _collect_acceptance(
    repo: FactRepository,
    *,
    changed_pairs: list[dict[str, Any]],
    upstream_fact_ids: list[str],
    upstream_latest_ids: list[str],
) -> dict[str, Any]:
    conn = repo.store.connect()
    changed_count = len(changed_pairs)
    expected_counts = {
        "fact_contexts": 5,
        "upstream_financial_facts": 57,
        "new_company_facts": 5 + changed_count,
        "new_exchange_facts": 5 + changed_count,
        "new_reconciled_facts": 5 + changed_count,
        "company_facts": 24 + changed_count,
        "exchange_facts": 24 + changed_count,
        "raw_facts": 48 + 2 * changed_count,
        "reconciled_facts": 24 + changed_count,
        "financial_facts": 72 + 3 * changed_count,
        "eligible_for_metrics": 24 + changed_count,
        "version_chain_links": 12 + 3 * changed_count,
        "lineage": 72 + 3 * changed_count,
        "audit": 72 + 3 * changed_count,
    }
    audit = AsOfQuery(repo).get_all_versions_for_audit(
        EXPECTED_SYMBOL, sorted(ALL_CONCEPTS),
    )
    counts = {
        "fact_contexts": conn.execute(
            "SELECT COUNT(*) FROM fact_contexts"
        ).fetchone()[0],
        "upstream_financial_facts": conn.execute(
            "SELECT COUNT(*) FROM financial_facts WHERE concept_id <> ?",
            [CAPEX_CONCEPT],
        ).fetchone()[0],
        "new_company_facts": conn.execute(
            """SELECT COUNT(*) FROM financial_facts
                WHERE concept_id=? AND source_tier='company_official'""",
            [CAPEX_CONCEPT],
        ).fetchone()[0],
        "new_exchange_facts": conn.execute(
            """SELECT COUNT(*) FROM financial_facts
                WHERE concept_id=? AND source_tier='exchange_official'""",
            [CAPEX_CONCEPT],
        ).fetchone()[0],
        "new_reconciled_facts": conn.execute(
            """SELECT COUNT(*) FROM financial_facts
                WHERE concept_id=? AND source_tier='reconciled_derived'""",
            [CAPEX_CONCEPT],
        ).fetchone()[0],
        "company_facts": conn.execute(
            "SELECT COUNT(*) FROM financial_facts "
            "WHERE source_tier='company_official'"
        ).fetchone()[0],
        "exchange_facts": conn.execute(
            "SELECT COUNT(*) FROM financial_facts "
            "WHERE source_tier='exchange_official'"
        ).fetchone()[0],
        "raw_facts": conn.execute(
            "SELECT COUNT(*) FROM financial_facts WHERE is_derived=FALSE"
        ).fetchone()[0],
        "reconciled_facts": conn.execute(
            "SELECT COUNT(*) FROM financial_facts "
            "WHERE source_tier='reconciled_derived'"
        ).fetchone()[0],
        "financial_facts": conn.execute(
            "SELECT COUNT(*) FROM financial_facts"
        ).fetchone()[0],
        "eligible_for_metrics": conn.execute(
            "SELECT COUNT(*) FROM financial_facts "
            "WHERE eligible_for_metrics=TRUE"
        ).fetchone()[0],
        "version_chain_links": conn.execute(
            "SELECT COUNT(*) FROM financial_facts "
            "WHERE supersedes_fact_id <> ''"
        ).fetchone()[0],
        "lineage": conn.execute(
            "SELECT COUNT(*) FROM fact_lineage"
        ).fetchone()[0],
        "audit": len(audit),
    }
    _require(counts == expected_counts, f"dynamic counts differ: {counts}")

    current_ids = [
        row[0]
        for row in conn.execute(
            """SELECT fact_id FROM financial_facts
               WHERE concept_id <> ? ORDER BY fact_id""",
            [CAPEX_CONCEPT],
        ).fetchall()
    ]
    _require(
        sorted(current_ids) == sorted(upstream_fact_ids),
        "frozen upstream 57 Fact IDs changed",
    )
    _require(
        _id_set_digest(current_ids) == UPSTREAM_FACT_ID_SET_SHA256,
        "frozen upstream Fact ID digest changed",
    )

    latest_date = conn.execute(
        "SELECT MAX(available_at) FROM financial_facts"
    ).fetchone()[0]
    as_of = AsOfQuery(repo)
    latest = as_of.get_latest_available(
        EXPECTED_SYMBOL, latest_date, sorted(ALL_CONCEPTS),
    )
    _require(len(latest) == 20, "final PIT snapshot must contain 20 facts")
    _require(
        set(latest["source_tier"]) == {"reconciled_derived"}
        and all(bool(value) for value in latest["eligible_for_metrics"]),
        "final PIT must contain only eligible reconciled facts",
    )
    per_key = latest.groupby(["period_end", "concept_id"]).size()
    _require(
        len(per_key) == 20 and all(int(value) == 1 for value in per_key),
        "final PIT keys differ",
    )
    latest_upstream = latest[latest["concept_id"].isin(EXPECTED_CONCEPTS)]
    _require(
        sorted(latest_upstream["fact_id"].tolist())
        == sorted(upstream_latest_ids),
        "base three-concept PIT Fact IDs changed",
    )

    transitions: list[dict[str, Any]] = []
    for pair in changed_pairs:
        available = date.fromisoformat(pair["available_at"])
        before = (available - timedelta(days=1)).isoformat()
        on = available.isoformat()
        period_end = f"{pair['target_fiscal_year']}-12-31"
        before_fact = _select_period_fact(
            as_of.get_latest_available(
                EXPECTED_SYMBOL, before, [CAPEX_CONCEPT],
            ),
            period_end=period_end,
            concept_id=CAPEX_CONCEPT,
        )
        on_fact = _select_period_fact(
            as_of.get_latest_available(
                EXPECTED_SYMBOL, on, [CAPEX_CONCEPT],
            ),
            period_end=period_end,
            concept_id=CAPEX_CONCEPT,
        )
        _require(
            int(before_fact["fact_version"]) == 1
            and int(on_fact["fact_version"]) == 2
            and on_fact["supersedes_fact_id"] == before_fact["fact_id"],
            "capex PIT version switch failed",
        )
        transitions.append(
            {
                "target_fiscal_year": pair["target_fiscal_year"],
                "before_date": before,
                "before_fact_id": before_fact["fact_id"],
                "before_value": before_fact["value"],
                "on_date": on,
                "on_fact_id": on_fact["fact_id"],
                "on_value": on_fact["value"],
                "supersedes_fact_id": on_fact["supersedes_fact_id"],
            }
        )

    lineage = conn.execute(
        """SELECT fact_id, run_id, source_tier, parent_fact_ids, role,
                  reconciliation_rule_id, reconciliation_rule_version
             FROM fact_lineage ORDER BY lineage_id"""
    ).df().to_dict("records")
    supplemental_lineage = [
        row for row in lineage
        if row["reconciliation_rule_id"] == SUPPLEMENTAL_RULE_ID
    ]
    _require(
        len(supplemental_lineage) == 3 * (5 + changed_count)
        and {
            row["reconciliation_rule_version"] for row in supplemental_lineage
        } == {SUPPLEMENTAL_RULE_VERSION},
        "supplemental lineage rule binding differs",
    )
    version_chains = conn.execute(
        """SELECT fact_id, concept_id, source_tier, fact_version,
                  restatement_version, supersedes_fact_id, available_at,
                  value, period_end
             FROM financial_facts
            WHERE supersedes_fact_id <> ''
            ORDER BY period_end, concept_id, source_tier"""
    ).df().to_dict("records")
    return {
        "counts": counts,
        "expected_counts": expected_counts,
        "latest_snapshot": {
            "as_of_date": latest_date,
            "count": len(latest),
            "fact_ids": latest["fact_id"].tolist(),
        },
        "pit_transitions": transitions,
        "version_chains": version_chains,
        "lineage": lineage,
        "audit_fact_ids": audit["fact_id"].tolist(),
        "upstream_fact_id_set_sha256": _id_set_digest(current_ids),
    }


def run_capex_cash_foundation(
    bundle_paths: list[str | Path],
    upstream_evidence_paths: list[str | Path],
    supplemental_paths: list[str | Path],
    capex_review_paths: list[str | Path],
    output_root: str | Path,
    *,
    run_id: str | None = None,
) -> dict[str, Any]:
    """Execute the complete offline Stage 2B-A acceptance."""
    run_id = run_id or build_run_id()
    run_dir = (
        Path(output_root)
        / EXPECTED_SYMBOL
        / "capex_cash_fact_foundation"
        / "2021_2025"
        / run_id
    )
    run_dir.mkdir(parents=True, exist_ok=False)
    upstream_dir = run_dir / "upstream_restatement"
    started_at = datetime.now().astimezone().isoformat()
    manifest: dict[str, Any] = {
        "run_id": run_id,
        "status": "failed",
        "transaction_committed": False,
        "offline": True,
        "symbol": EXPECTED_SYMBOL,
        "years": list(EXPECTED_YEARS),
        "integration_contract": INTEGRATION_CONTRACT,
        "supplemental_contract": SUPPLEMENTAL_CONTRACT,
        "capex_restatement_contract": CAPEX_RESTATEMENT_CONTRACT,
        "reconciliation_rule_id": SUPPLEMENTAL_RULE_ID,
        "reconciliation_rule_version": SUPPLEMENTAL_RULE_VERSION,
        "fact_schema_version": FactRepository.schema_version,
        "database": "upstream_restatement/restatement_integration.duckdb",
        "started_at": started_at,
    }
    store: DuckDBStore | None = None
    db_path: Path | None = None
    try:
        created_at = datetime.now().astimezone().isoformat()
        supplemental = preflight_supplemental_evidence(
            bundle_paths, supplemental_paths, created_at=created_at,
        )
        capex_restatements = preflight_capex_restatements(
            supplemental,
            capex_review_paths,
            bundle_paths,
            created_at=created_at,
        )

        with tempfile.TemporaryDirectory(prefix="m2_stage2ba_") as temp_root:
            upstream = run_restatement_integration(
                bundle_paths,
                upstream_evidence_paths,
                temp_root,
                run_id="upstream",
            )
            _require(upstream["status"] == "passed", "Stage 1D-B upstream failed")
            shutil.move(str(upstream["run_directory"]), str(upstream_dir))
            upstream["run_directory"] = upstream_dir
        _require(
            upstream["counts"]["financial_facts"] == UPSTREAM_FACT_COUNT
            and upstream["latest_pit_snapshot"]["count"]
            == UPSTREAM_LATEST_PIT_COUNT,
            "Stage 1D-B upstream counts differ",
        )

        db_path = upstream_dir / "restatement_integration.duckdb"
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
            and _id_set_digest(upstream_fact_ids)
            == UPSTREAM_FACT_ID_SET_SHA256,
            "Stage 1D-B Fact ID set differs",
        )
        upstream_latest_ids = list(
            upstream["latest_pit_snapshot"]["fact_ids"]
        )

        service = OfficialFactReconciliationService(
            repo,
            engine=ReconciliationEngine(CAPEX_CASH_RECONCILIATION_RULE),
        )
        persisted_v1: list[dict[str, Any]] = []
        for record in supplemental["records"]:
            result = service.reconcile_official_pair(
                record["source_facts"]["company"],
                record["source_facts"]["exchange"],
            )
            _require(
                result.status == ReconciliationStatus.matched
                and result.output_fact is not None,
                f"{record['evidence']['fiscal_year']}: v1 persistence failed",
            )
            persisted_v1.append(asdict(result))

        persisted_v2: list[dict[str, Any]] = []
        for pair in capex_restatements["changed_pairs"]:
            result = service.reconcile_official_pair(
                pair["company_fact"],
                pair["exchange_fact"],
                output_supersedes_fact_id=pair["reconciled_v1_fact_id"],
            )
            _require(
                result.status == ReconciliationStatus.matched
                and result.output_fact is not None,
                f"{pair['target_fiscal_year']}: v2 persistence failed",
            )
            persisted_v2.append(asdict(result))

        acceptance = _collect_acceptance(
            repo,
            changed_pairs=capex_restatements["changed_pairs"],
            upstream_fact_ids=upstream_fact_ids,
            upstream_latest_ids=upstream_latest_ids,
        )
        _write_json(
            run_dir / "supplemental_evidence_manifest.json",
            {
                "contract": SUPPLEMENTAL_CONTRACT,
                "records": [
                    {
                        "logical_path": (
                            f"601857.SH/supplemental/{record['path'].name}"
                        ),
                        "evidence": record["evidence"],
                    }
                    for record in supplemental["records"]
                ],
            },
        )
        _write_json(
            run_dir / "capex_restatement_reviews.json",
            {
                "contract": CAPEX_RESTATEMENT_CONTRACT,
                "comparisons": capex_restatements["comparisons"],
                "review_status_2025": "not_yet_reviewable",
            },
        )
        _write_json(
            run_dir / "reconciliation_results.json",
            {"v1": persisted_v1, "v2": persisted_v2},
        )
        _write_json(
            run_dir / "version_chains.json",
            acceptance["version_chains"],
        )
        _write_json(
            run_dir / "pit_transitions.json",
            acceptance["pit_transitions"],
        )
        _write_json(
            run_dir / "latest_fact_snapshot.json",
            acceptance["latest_snapshot"],
        )
        _write_json(
            run_dir / "lineage_summary.json",
            {"count": len(acceptance["lineage"]), "rows": acceptance["lineage"]},
        )
        manifest.update(
            {
                "status": "passed",
                "transaction_committed": True,
                "upstream": {
                    "status": upstream["status"],
                    "financial_facts": UPSTREAM_FACT_COUNT,
                    "latest_pit": UPSTREAM_LATEST_PIT_COUNT,
                    "fact_id_set_sha256": (
                        acceptance["upstream_fact_id_set_sha256"]
                    ),
                },
                "changed_year_count": capex_restatements["changed_count"],
                "review_status_2025": "not_yet_reviewable",
                "counts": acceptance["counts"],
                "latest_pit_snapshot": acceptance["latest_snapshot"],
                "new_v1_reconciled_fact_ids": [
                    item["output_fact"]["fact_id"] for item in persisted_v1
                ],
                "new_v2_reconciled_fact_ids": [
                    item["output_fact"]["fact_id"] for item in persisted_v2
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
        if db_path is not None and db_path.exists():
            db_path.unlink()
    finally:
        if store is not None:
            store.close()

    _write_json(run_dir / "run_manifest.json", manifest)
    summary = (
        "# Capex cash official fact foundation\n\n"
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
    parser.add_argument("--bundle", action="append", required=True)
    parser.add_argument("--evidence", action="append", required=True)
    parser.add_argument("--supplemental", action="append", required=True)
    parser.add_argument("--capex-review", action="append", required=True)
    parser.add_argument("--output-root", required=True)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    result = run_capex_cash_foundation(
        args.bundle,
        args.evidence,
        args.supplemental,
        args.capex_review,
        args.output_root,
    )
    print(json.dumps(_jsonable(result), ensure_ascii=False, indent=2))
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
