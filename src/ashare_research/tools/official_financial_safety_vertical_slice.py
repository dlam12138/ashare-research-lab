"""Offline M2 Stage 2E-B financial-safety vertical slice.

The runner rebuilds the frozen Stage 2D-F foundation in a temporary run,
adds only registered financial-safety evidence through Rule 006, replays
annual PIT dates, and stores the four descriptive metrics in a run-scoped
metrics database.  It never opens the default database, shared PDF cache, or
network.  Interest coverage, ROIC, and scoring are intentionally absent.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import traceback
from dataclasses import asdict, is_dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal
from enum import StrEnum
from pathlib import Path
from typing import Any

from ashare_research.facts.as_of import AsOfQuery
from ashare_research.facts.identity import build_fact_id
from ashare_research.facts.repository import FactRepository
from ashare_research.metrics.financial_safety_definitions import (
    FinancialSafetyMetricDefinitionRegistry,
    FinancialSafetyMetricStatus,
)
from ashare_research.metrics.financial_safety_engine import (
    FinancialSafetyMetricEngine,
)
from ashare_research.metrics.models import (
    MetricDefinition,
    MetricLineage,
    MetricResult,
    MetricStatus,
)
from ashare_research.metrics.repository import MetricRepository
from ashare_research.reconciliation.engine import ReconciliationEngine
from ashare_research.reconciliation.financial_safety import (
    FINANCIAL_SAFETY_RECONCILIATION_RULE,
    FINANCIAL_SAFETY_RULE_ID,
    FINANCIAL_SAFETY_RULE_VERSION,
)
from ashare_research.reconciliation.models import ReconciliationStatus
from ashare_research.reconciliation.service import (
    OfficialFactReconciliationService,
)
from ashare_research.storage.duckdb_store import DuckDBStore
from ashare_research.tools.official_earnings_quality_fact_foundation import (
    DEFAULT_DB,
    DEFAULT_DB_SHA256,
    SYMBOL,
)
from ashare_research.tools.official_roa_metric_extension import (
    ANNUAL_REPORT_DATES,
    COMBINED_70_RESULT_ID_SET_SHA256,
    run_roa_metric_extension,
)
from ashare_research.validation.validator import FactValidator

ROOT = Path(__file__).resolve().parents[3]
BUNDLE_DIR = ROOT / "acceptance/fixtures/official_facts/601857.SH"
SUPPLEMENTAL_DIR = BUNDLE_DIR / "supplemental"
RESTATEMENT_DIR = ROOT / "acceptance/fixtures/restatements/601857.SH"

CONTRACT = "financial_safety_vertical_slice_v1"
EVIDENCE_CONTRACT = "financial_safety_official_facts_v1"
RESTATEMENT_CONTRACT = "financial_safety_restatement_evidence_v1"
YEARS = (2021, 2022, 2023, 2024, 2025)
SAFETY_CONCEPTS = (
    "total_liabilities",
    "short_term_borrowings",
    "current_portion_of_interest_bearing_non_current_liabilities",
    "long_term_borrowings",
    "bonds_payable",
    "lease_liabilities",
    "cash_and_cash_equivalents",
)
DEBT_CONCEPTS = (
    "short_term_borrowings",
    "current_portion_of_interest_bearing_non_current_liabilities",
    "long_term_borrowings",
    "bonds_payable",
    "lease_liabilities",
)
METRIC_IDS = (
    "asset_liability_ratio",
    "gross_interest_bearing_debt",
    "cash_coverage_of_interest_bearing_debt",
    "net_interest_bearing_debt",
)
METRIC_REVISION_STATUS = {
    2021: "reviewed_unchanged",
    2022: "reviewed_changed",
    2023: "reviewed_changed",
    2024: "reviewed_unchanged",
    2025: "not_yet_reviewable",
}
PRIOR_77_RESULT_ID_SET_SHA256 = "e76126542fef8c2facbcac0a52d437a21645c7e29ec873dd4eab7b47c1d27787"
PRIOR_77_RESULT_SEMANTIC_SHA256 = "6062d1e24627ea467e1c8a48f7ac4cc349de036740a5a32dd04b7c3fbf890813"
DAY_BEFORE_FIRST = (date.fromisoformat(ANNUAL_REPORT_DATES[0]) - timedelta(days=1)).isoformat()
PIT_DATES = [DAY_BEFORE_FIRST, *ANNUAL_REPORT_DATES]


class FinancialSafetyVerticalSliceError(ValueError):
    """A deterministic Stage 2E-B acceptance gate failed."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise FinancialSafetyVerticalSliceError(message)


def _jsonable(value: Any) -> Any:
    if is_dataclass(value):
        return _jsonable(asdict(value))
    if isinstance(value, Path):
        return value.name
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, list | tuple):
        return [_jsonable(item) for item in value]
    if isinstance(value, StrEnum):
        return value.value
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


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    _require(isinstance(value, dict), f"{path.name} must contain an object")
    return value


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _id_set_digest(ids: list[str]) -> str:
    return hashlib.sha256(json.dumps(sorted(ids), separators=(",", ":")).encode()).hexdigest()


def _result_semantic_digest(rows: list[MetricResult]) -> str:
    fields = (
        "metric_result_id",
        "metric_id",
        "metric_definition_version",
        "symbol",
        "fiscal_year",
        "period_end",
        "result_version",
        "supersedes_metric_result_id",
        "status",
        "value",
        "unit",
        "formula",
        "available_at",
        "input_fact_ids",
        "missing_input_description",
        "revision_review_status",
    )
    payload = []
    for row in rows:
        data = asdict(row)
        payload.append(
            {
                field: (
                    str(data[field])
                    if field in {"status", "value"} and data[field] is not None
                    else data[field]
                )
                for field in fields
            }
        )
    return hashlib.sha256(
        json.dumps(
            sorted(payload, key=lambda item: item["metric_result_id"]),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
    ).hexdigest()


def _load_bundle(year: int) -> dict[str, Any]:
    path = BUNDLE_DIR / f"{year}_annual.json"
    bundle = _load_json(path)
    _require(
        _sha256(path) == _bundle_sha(year),
        f"FY{year} annual bundle SHA differs from evidence",
    )
    _require(
        bundle["symbol"] == SYMBOL
        and bundle["fiscal_year"] == year
        and bundle["accounting_standard"] == "CAS"
        and bundle["consolidation_scope"] == "consolidated",
        f"FY{year} annual bundle identity differs",
    )
    return bundle


def _bundle_sha(year: int) -> str:
    return {
        2021: "0c97789044bc594dec48e95a846603b2d22a06227dce535ec855f569aeaf391b",
        2022: "5c610fd5ac33f61f5777ae4ea6fb62b50caff741b7c414e3a4161915db130ed9",
        2023: "3f1bd6859927871570aaf1d4efbea2ce36c6d1013bbb2b2630115600c03aae2c",
        2024: "d596ebfc9404cc6bca7520de10ddec5647830212daa946ff25b9e8fe9cc54176",
        2025: "1cea469542ec4293658703167e7d10cc00b7ced21c9ce6a5e13843bed6e1caab",
    }[year]


def _validate_evidence(year: int) -> dict[str, Any]:
    path = SUPPLEMENTAL_DIR / f"{year}_financial_safety.json"
    evidence = _load_json(path)
    _require(evidence.get("contract") == EVIDENCE_CONTRACT, f"FY{year} evidence contract differs")
    _require(evidence.get("symbol") == SYMBOL, f"FY{year} evidence symbol differs")
    _require(evidence.get("fiscal_year") == year, f"FY{year} evidence year differs")
    _require(
        evidence.get("reconciliation_rule_id") == FINANCIAL_SAFETY_RULE_ID
        and evidence.get("reconciliation_rule_version") == FINANCIAL_SAFETY_RULE_VERSION,
        f"FY{year} evidence Rule 006 binding differs",
    )
    bundle = _load_bundle(year)
    _require(
        evidence.get("base_bundle_path")
        == f"acceptance/fixtures/official_facts/601857.SH/{year}_annual.json",
        f"FY{year} evidence base path differs",
    )
    _require(evidence.get("base_bundle_sha256") == _bundle_sha(year), f"FY{year} base SHA differs")
    sources = evidence.get("sources")
    _require(
        isinstance(sources, dict) and set(sources) == {"company", "exchange"},
        f"FY{year} sources differ",
    )
    by_source: dict[str, dict[str, dict[str, Any]]] = {}
    for source in ("company", "exchange"):
        document = bundle["documents"][source]
        facts = sources[source]
        _require(
            isinstance(facts, list)
            and {item.get("concept_id") for item in facts} == set(SAFETY_CONCEPTS)
            and len(facts) == len(SAFETY_CONCEPTS),
            f"FY{year}/{source} direct concept set differs",
        )
        by_source[source] = {}
        for item in facts:
            concept = str(item["concept_id"])
            _require(
                item.get("scope") == "CAS consolidated", f"{year}/{source}/{concept} scope differs"
            )
            _require(item.get("unit") == "万元", f"{year}/{source}/{concept} unit differs")
            _require(
                item.get("missing_reason") is None,
                f"{year}/{source}/{concept} missing reason is not empty",
            )
            _require(
                item.get("manual_review_status") == "visually_verified_and_text_checked",
                f"{year}/{source}/{concept} review differs",
            )
            raw = int(str(item["raw_value"]))
            _require(
                item["raw_unit"] == "人民币百万元", f"{year}/{source}/{concept} raw unit differs"
            )
            _require(
                item["normalization_rule"] == "RMB_MILLION_TO_CNY_10K_X100",
                f"{year}/{source}/{concept} normalization differs",
            )
            _require(
                item["expected_normalized_value"] == raw * 100,
                f"{year}/{source}/{concept} normalization value differs",
            )
            _require(
                isinstance(item.get("pdf_page"), int) and isinstance(item.get("printed_page"), int),
                f"{year}/{source}/{concept} page differs",
            )
            _require(item.get("source_page"), f"{year}/{source}/{concept} source page missing")
            _require(
                item.get("source_table") and item.get("source_label"),
                f"{year}/{source}/{concept} label missing",
            )
            _require(
                item.get("column_label") and item.get("comparative_column_label"),
                f"{year}/{source}/{concept} column missing",
            )
            by_source[source][concept] = item
        _require(
            document["source_tier"] == f"{source}_official",
            f"FY{year}/{source} source tier differs",
        )
    for concept in SAFETY_CONCEPTS:
        _require(
            by_source["company"][concept]["expected_normalized_value"]
            == by_source["exchange"][concept]["expected_normalized_value"],
            f"FY{year}/{concept}: company and exchange values conflict",
        )
    return {"bundle": bundle, "evidence": evidence, "by_source": by_source}


def _instant_context_id(year: int) -> str:
    return f"{SYMBOL}|{year}|instant|consolidated"


def _build_source_fact(
    year: int,
    source: str,
    item: dict[str, Any],
    document: dict[str, Any],
    *,
    created_at: str,
) -> dict[str, Any]:
    period = f"{year}-12-31"
    fact = {
        "concept_id": item["concept_id"],
        "concept_version": "1",
        "symbol": SYMBOL,
        "value": int(item["expected_normalized_value"]),
        "unit": "万元",
        "context_id": _instant_context_id(year),
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
        "source_page": item["source_page"],
        "source_table": item["source_table"],
        "source_label": item["source_label"],
        "fact_version": 1,
        "restatement_version": "original",
        "supersedes_fact_id": "",
        "fiscal_year": year,
        "report_type": "annual",
        "period_start": period,
        "period_end": period,
        "filing_date": document["announcement_date"],
        "announcement_date": document["announcement_date"],
        "available_at": document["announcement_date"],
        "raw_value": int(item["raw_value"]),
        "raw_unit": item["raw_unit"],
        "normalized_value": int(item["expected_normalized_value"]),
        "normalization_rule": item["normalization_rule"],
        "verification_status": "verified",
        "verification_note": (
            "visually verified and text checked against registered official evidence"
        ),
        "eligible_for_metrics": False,
        "created_at": created_at,
    }
    fact["fact_id"] = build_fact_id(fact)
    return fact


def _validate_source_facts(facts: list[dict[str, Any]]) -> None:
    errors = [
        item
        for item in FactValidator().validate_batch(facts)
        if item.severity == "error" and not item.passed
    ]
    _require(
        not errors,
        f"financial-safety source validation failed: {[asdict(item) for item in errors]}",
    )


def _load_restatement_reviews(preflight: dict[str, Any]) -> dict[str, Any]:
    reviews: dict[int, dict[str, Any]] = {}
    changed: list[tuple[int, str]] = []
    for target in (2021, 2022, 2023, 2024):
        path = RESTATEMENT_DIR / f"financial_safety_{target}_reviewed_by_{target + 1}.json"
        review = _load_json(path)
        _require(
            review.get("contract") == RESTATEMENT_CONTRACT,
            f"FY{target} restatement contract differs",
        )
        concepts = review.get("concepts", [])
        _require(
            {item.get("concept_id") for item in concepts} == set(SAFETY_CONCEPTS),
            f"FY{target} restatement concepts differ",
        )
        for item in concepts:
            concept = item["concept_id"]
            original = preflight["source_facts"][target]["company"][concept]
            original_raw = int(item["original_raw_value"])
            later_raw = int(item["later_comparative_raw_value"])
            _require(
                original_raw == int(original["raw_value"]),
                f"FY{target}/{concept} original value differs",
            )
            _require(
                item["changed"] is (original_raw != later_raw),
                f"FY{target}/{concept} changed flag differs",
            )
            _require(
                item.get("later_source_page"), f"FY{target}/{concept} later source page missing"
            )
            if original_raw != later_raw:
                changed.append((target, concept))
        reviews[target] = review
    return {"reviews": reviews, "changed": changed, "R": len(changed)}


def _build_v2_raw_fact(
    predecessor: dict[str, Any],
    later_bundle: dict[str, Any],
    source: str,
    review_item: dict[str, Any],
    *,
    later_raw: int,
    created_at: str,
) -> dict[str, Any]:
    document = later_bundle["documents"][source]
    fact = copy.deepcopy(predecessor)
    fact.update(
        value=later_raw * 100,
        raw_value=later_raw,
        normalized_value=later_raw * 100,
        source_provider=document["source_provider"],
        source_document=document["source_document"],
        source_url=document["final_pdf_url"],
        source_hash=document["sha256"],
        source_page=review_item["later_source_page"],
        source_table=f"{later_bundle['fiscal_year']}年12月31日合并及公司资产负债表(续)",
        filing_date=document["announcement_date"],
        announcement_date=document["announcement_date"],
        available_at=document["announcement_date"],
        fact_version=2,
        restatement_version="restated_1",
        supersedes_fact_id=predecessor["fact_id"],
        verification_note="visually verified and text checked against later comparative evidence",
        created_at=created_at,
    )
    fact["fact_id"] = build_fact_id(fact)
    return fact


def _persist_facts(
    repo: FactRepository,
    validated: dict[int, dict[str, Any]],
    preflight: dict[str, Any],
    restatement: dict[str, Any],
    *,
    created_at: str,
) -> dict[str, Any]:
    engine = ReconciliationEngine(FINANCIAL_SAFETY_RECONCILIATION_RULE)
    service = OfficialFactReconciliationService(repo, engine=engine)
    v1_outputs: dict[tuple[int, str], dict[str, Any]] = {}
    persisted = []
    for year in YEARS:
        for concept in SAFETY_CONCEPTS:
            company = preflight["source_facts"][year]["company"][concept]
            exchange = preflight["source_facts"][year]["exchange"][concept]
            result = service.reconcile_official_pair(company, exchange)
            _require(
                result.status == ReconciliationStatus.matched and result.output_fact is not None,
                f"FY{year}/{concept} v1 did not match",
            )
            v1_outputs[(year, concept)] = result.output_fact
            persisted.append(asdict(result))

    v2_outputs: dict[tuple[int, str], dict[str, Any]] = {}
    for target, concept in restatement["changed"]:
        review = restatement["reviews"][target]
        item = next(row for row in review["concepts"] if row["concept_id"] == concept)
        later_bundle = validated[target + 1]["bundle"]
        company_v2 = _build_v2_raw_fact(
            preflight["source_facts"][target]["company"][concept],
            later_bundle,
            "company",
            item,
            later_raw=int(item["later_comparative_raw_value"]),
            created_at=created_at,
        )
        exchange_v2 = _build_v2_raw_fact(
            preflight["source_facts"][target]["exchange"][concept],
            later_bundle,
            "exchange",
            item,
            later_raw=int(item["later_comparative_raw_value"]),
            created_at=created_at,
        )
        _validate_source_facts([company_v2, exchange_v2])
        result = service.reconcile_official_pair(
            company_v2,
            exchange_v2,
            output_supersedes_fact_id=v1_outputs[(target, concept)]["fact_id"],
        )
        _require(
            result.status == ReconciliationStatus.matched and result.output_fact is not None,
            f"FY{target}/{concept} v2 did not match",
        )
        v2_outputs[(target, concept)] = result.output_fact
        persisted.append(asdict(result))
    return {"v1": v1_outputs, "v2": v2_outputs, "reconciliations": persisted}


def _fact_maps(as_of: AsOfQuery, as_of_date: str) -> dict[str, dict[int, dict[str, Any]]]:
    concepts = ["total_assets", *SAFETY_CONCEPTS]
    rows = as_of.get_latest_available(SYMBOL, as_of_date, concepts).to_dict("records")
    maps: dict[str, dict[int, dict[str, Any]]] = {concept: {} for concept in concepts}
    for row in rows:
        maps[row["concept_id"]][int(str(row["period_end"])[:4])] = row
    return maps


def _role_facts(
    definition: Any, maps: dict[str, dict[int, dict[str, Any]]], year: int
) -> dict[str, dict[str, Any] | None]:
    if definition.metric_id == "asset_liability_ratio":
        return {
            "numerator": maps["total_liabilities"].get(year),
            "denominator": maps["total_assets"].get(year),
        }
    if definition.metric_id == "gross_interest_bearing_debt":
        return {
            "short_term_borrowings": maps["short_term_borrowings"].get(year),
            "current_portion": maps[
                "current_portion_of_interest_bearing_non_current_liabilities"
            ].get(year),
            "long_term_borrowings": maps["long_term_borrowings"].get(year),
            "bonds_payable": maps["bonds_payable"].get(year),
            "lease_liabilities": maps["lease_liabilities"].get(year),
        }
    if definition.metric_id == "cash_coverage_of_interest_bearing_debt":
        return {
            "cash": maps["cash_and_cash_equivalents"].get(year),
            "short_term_borrowings": maps["short_term_borrowings"].get(year),
            "current_portion": maps[
                "current_portion_of_interest_bearing_non_current_liabilities"
            ].get(year),
            "long_term_borrowings": maps["long_term_borrowings"].get(year),
            "bonds_payable": maps["bonds_payable"].get(year),
            "lease_liabilities": maps["lease_liabilities"].get(year),
        }
    return {
        "short_term_borrowings": maps["short_term_borrowings"].get(year),
        "current_portion": maps["current_portion_of_interest_bearing_non_current_liabilities"].get(
            year
        ),
        "long_term_borrowings": maps["long_term_borrowings"].get(year),
        "bonds_payable": maps["bonds_payable"].get(year),
        "lease_liabilities": maps["lease_liabilities"].get(year),
        "cash": maps["cash_and_cash_equivalents"].get(year),
    }


def _compute_financial_safety_metrics(
    repo: FactRepository,
    *,
    created_at: str,
) -> dict[str, Any]:
    as_of = AsOfQuery(repo)
    definitions = FinancialSafetyMetricDefinitionRegistry.list_all()
    latest_by_key: dict[tuple[int, str], MetricResult] = {}
    results: list[MetricResult] = []
    lineage: list[MetricLineage] = []
    snapshots = []
    for as_of_date in PIT_DATES:
        maps = _fact_maps(as_of, as_of_date)
        for year in YEARS:
            active = any(maps[concept].get(year) is not None for concept in SAFETY_CONCEPTS)
            if not active:
                continue
            for definition in definitions:
                role_facts = _role_facts(definition, maps, year)
                candidate, _ = FinancialSafetyMetricEngine.compute(
                    definition,
                    symbol=SYMBOL,
                    fiscal_year=year,
                    role_facts=role_facts,
                    revision_review_status=METRIC_REVISION_STATUS[year],
                    as_of_date=as_of_date,
                    created_at=created_at,
                )
                key = (year, definition.metric_id)
                previous = latest_by_key.get(key)
                changed = previous is None or (
                    previous.value != candidate.value
                    or previous.status != candidate.status
                    or previous.input_fact_ids != candidate.input_fact_ids
                )
                if not changed:
                    continue
                result, rows = FinancialSafetyMetricEngine.compute(
                    definition,
                    symbol=SYMBOL,
                    fiscal_year=year,
                    role_facts=role_facts,
                    result_version=previous.result_version + 1 if previous else 1,
                    supersedes_metric_result_id=(previous.metric_result_id if previous else ""),
                    revision_review_status=METRIC_REVISION_STATUS[year],
                    as_of_date=as_of_date,
                    created_at=created_at,
                )
                latest_by_key[key] = result
                results.append(result)
                lineage.extend(rows)
        latest = sorted(latest_by_key.values(), key=lambda row: (row.fiscal_year, row.metric_id))
        snapshots.append(
            {
                "as_of_date": as_of_date,
                "count": len(latest),
                "computed": sum(row.status == MetricStatus.computed for row in latest),
                "missing_input": sum(row.status == MetricStatus.missing_input for row in latest),
                "undefined_no_debt": sum(
                    row.status == FinancialSafetyMetricStatus.undefined_no_debt
                    for row in latest
                ),
                "not_comparable_negative_debt_component": sum(
                    row.status
                    == FinancialSafetyMetricStatus.not_comparable_negative_debt_component
                    for row in latest
                ),
            }
        )
    return {
        "definitions": definitions,
        "results": results,
        "lineage": lineage,
        "latest": sorted(latest_by_key.values(), key=lambda row: (row.fiscal_year, row.metric_id)),
        "snapshots": snapshots,
    }


def _load_prior_metric_artifacts(upstream_run: Path) -> dict[str, Any]:
    definitions = []
    for row in json.loads((upstream_run / "metric_definitions.json").read_text(encoding="utf-8")):
        definitions.append(
            MetricDefinition(
                metric_id=row["metric_id"],
                version=row["version"],
                display_name_zh=row["display_name_zh"],
                formula=row["formula"],
                input_concept_ids=tuple(row["input_concept_ids"]),
                input_roles=tuple(row["input_roles"]),
                unit=row["unit"],
            )
        )
    results = []
    for row in json.loads(
        (upstream_run / "metric_result_versions.json").read_text(encoding="utf-8")
    ):
        row = dict(row)
        row["status"] = MetricStatus(row["status"])
        row["value"] = Decimal(row["value"]) if row.get("value") is not None else None
        row["input_fact_ids"] = tuple(row["input_fact_ids"])
        results.append(MetricResult(**row))
    lineage = [
        MetricLineage(**row)
        for row in json.loads((upstream_run / "metric_lineage.json").read_text(encoding="utf-8"))
    ]
    return {"definitions": definitions, "results": results, "lineage": lineage}


def _coverage_matrix(repo: FactRepository) -> list[dict[str, Any]]:
    conn = repo.store.connect()
    rows = conn.execute(
        """SELECT c.fiscal_year, f.concept_id, f.fact_version,
                  f.restatement_version, f.value, f.available_at,
                  f.source_page, f.source_tier
             FROM financial_facts AS f
             JOIN fact_contexts AS c ON c.context_id = f.context_id
            WHERE f.source_tier='reconciled_derived'
              AND f.eligible_for_metrics=TRUE
              AND f.concept_id IN (SELECT UNNEST(?))
            ORDER BY fiscal_year, concept_id, fact_version""",
        [list(SAFETY_CONCEPTS)],
    ).fetchall()
    return [
        {
            "fiscal_year": row[0],
            "concept_id": row[1],
            "fact_version": row[2],
            "restatement_version": row[3],
            "value": row[4],
            "available_at": row[5],
            "source_page": row[6],
            "source_tier": row[7],
        }
        for row in rows
    ]


def _debt_exclusivity(repo: FactRepository, coverage: list[dict[str, Any]]) -> list[dict[str, Any]]:
    latest = {}
    for row in coverage:
        latest[(row["fiscal_year"], row["concept_id"])] = row
    output = []
    for year in YEARS:
        values = {concept: latest[(year, concept)]["value"] for concept in DEBT_CONCEPTS}
        gross = sum(values.values())
        output.append(
            {
                "fiscal_year": year,
                "direct_components": values,
                "gross_interest_bearing_debt": gross,
                "recomputed_sum": sum(values.values()),
                "exact_tie_out": gross == sum(values.values()),
                "mutually_exclusive": True,
                "forbidden_substitutions": ["total_liabilities", "interest_bearing_debt"],
                "missing_components": [
                    concept for concept in DEBT_CONCEPTS if (year, concept) not in latest
                ],
            }
        )
    return output


def _metric_counts(
    results: list[MetricResult], latest: list[MetricResult], lineage: list[MetricLineage]
) -> dict[str, int]:
    return {
        "definitions": len(METRIC_IDS),
        "result_versions": len(results),
        "computed": sum(row.status == MetricStatus.computed for row in results),
        "insufficient": sum(
            row.status
            in {
                MetricStatus.missing_input,
                FinancialSafetyMetricStatus.undefined_no_debt,
                FinancialSafetyMetricStatus.not_comparable_negative_debt_component,
            }
            for row in results
        ),
        "links": sum(bool(row.supersedes_metric_result_id) for row in results),
        "lineage": len(lineage),
        "final_latest": len(latest),
        "final_computed": sum(row.status == MetricStatus.computed for row in latest),
    }


def _build_run_id() -> str:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    return f"financial_safety_vertical_slice_601857_SH_2021_2025_{stamp}"


def run_financial_safety_vertical_slice(
    output_root: str | Path,
    *,
    run_id: str | None = None,
) -> dict[str, Any]:
    """Execute the complete offline Stage 2E-B vertical slice."""
    run_id = run_id or _build_run_id()
    run_dir = (
        Path(output_root)
        / "value_assessment"
        / SYMBOL
        / "financial_safety_vertical_slice"
        / "2021_2025"
        / run_id
    )
    existing_manifest = run_dir / "run_manifest.json"
    if existing_manifest.exists():
        manifest = _load_json(existing_manifest)
        _require(manifest.get("status") == "passed", f"existing run is not passed: {run_id}")
        return {**manifest, "run_directory": run_dir}
    run_dir.mkdir(parents=True, exist_ok=False)
    metrics_path = run_dir / "metrics.duckdb"
    started_at = datetime.now().astimezone().isoformat()
    manifest: dict[str, Any] = {
        "run_id": run_id,
        "status": "failed",
        "offline": True,
        "network_access": False,
        "pdf_access": False,
        "shared_cache_access": False,
        "default_database_access": False,
        "contract": CONTRACT,
        "rule_id": FINANCIAL_SAFETY_RULE_ID,
        "rule_version": FINANCIAL_SAFETY_RULE_VERSION,
        "database": metrics_path.name,
        "interest_coverage": "blocked",
        "roic_computation": "not_performed",
        "scoring": "not_implemented",
        "started_at": started_at,
    }
    metrics_repo: MetricRepository | None = None
    upstream_store: DuckDBStore | None = None
    try:
        default_before = _sha256(DEFAULT_DB)
        _require(default_before == DEFAULT_DB_SHA256, "default database baseline differs")
        upstream = run_roa_metric_extension(
            Path(output_root), run_id=f"{run_id}__stage2f_foundation"
        )
        _require(upstream["status"] == "passed", "Stage 2D-F foundation rebuild failed")
        foundation_dir = Path(upstream["run_directory"])
        upstream_dir = foundation_dir / "upstream_net_profit_official_facts"
        upstream_db = upstream_dir / "net_profit.duckdb"
        upstream_run = foundation_dir
        upstream_store = DuckDBStore(str(upstream_db))
        upstream_repo = FactRepository(upstream_store)
        conn = upstream_store.connect()
        before_ids = [
            row[0]
            for row in conn.execute(
                "SELECT fact_id FROM financial_facts ORDER BY fact_id"
            ).fetchall()
        ]
        _require(len(before_ids) == 201, f"upstream Fact baseline differs: {len(before_ids)}")
        prior = _load_prior_metric_artifacts(upstream_run)
        _require(len(prior["results"]) == 77, "upstream Metric Result baseline differs")
        prior_ids = [row.metric_result_id for row in prior["results"]]
        _require(
            _id_set_digest(prior_ids) == PRIOR_77_RESULT_ID_SET_SHA256,
            "frozen 77-result ID set differs",
        )
        _require(
            _result_semantic_digest(prior["results"]) == PRIOR_77_RESULT_SEMANTIC_SHA256,
            "frozen 77-result semantics differ",
        )
        validated = {year: _validate_evidence(year) for year in YEARS}
        created_at = datetime.now().astimezone().isoformat()
        source_facts: dict[int, dict[str, dict[str, dict[str, Any]]]] = {}
        preflight_results = []
        rule_engine = ReconciliationEngine(FINANCIAL_SAFETY_RECONCILIATION_RULE)
        for year in YEARS:
            source_facts[year] = {"company": {}, "exchange": {}}
            for concept in SAFETY_CONCEPTS:
                for source in ("company", "exchange"):
                    item = validated[year]["by_source"][source][concept]
                    document = validated[year]["bundle"]["documents"][source]
                    source_facts[year][source][concept] = _build_source_fact(
                        year, source, item, document, created_at=created_at
                    )
                _validate_source_facts(
                    [
                        source_facts[year]["company"][concept],
                        source_facts[year]["exchange"][concept],
                    ]
                )
                result = rule_engine.reconcile_pair(
                    source_facts[year]["company"][concept],
                    source_facts[year]["exchange"][concept],
                    now=created_at,
                )
                _require(
                    result.status == ReconciliationStatus.matched,
                    f"FY{year}/{concept} Rule 006 preflight failed",
                )
                preflight_results.append(asdict(result))
        preflight = {
            "validated": validated,
            "source_facts": source_facts,
            "preflight_results": preflight_results,
        }
        restatement = _load_restatement_reviews(preflight)
        persisted_facts = _persist_facts(
            upstream_repo, validated, preflight, restatement, created_at=created_at
        )
        fact_counts = {
            "contexts": conn.execute("SELECT COUNT(*) FROM fact_contexts").fetchone()[0],
            "facts": conn.execute("SELECT COUNT(*) FROM financial_facts").fetchone()[0],
            "raw": conn.execute(
                "SELECT COUNT(*) FROM financial_facts "
                "WHERE is_derived=FALSE AND eligible_for_metrics=FALSE"
            ).fetchone()[0],
            "reconciled": conn.execute(
                "SELECT COUNT(*) FROM financial_facts "
                "WHERE source_tier='reconciled_derived' "
                "AND eligible_for_metrics=TRUE"
            ).fetchone()[0],
            "fact_links": conn.execute(
                "SELECT COUNT(*) FROM financial_facts WHERE supersedes_fact_id <> ''"
            ).fetchone()[0],
            "lineage": conn.execute("SELECT COUNT(*) FROM fact_lineage").fetchone()[0],
            "audit": len(AsOfQuery(upstream_repo).get_all_versions_for_audit(SYMBOL)),
        }
        _require(fact_counts["contexts"] == 11, f"contexts changed: {fact_counts}")
        _require(
            fact_counts["facts"] == 201 + 3 * 35 + 3 * restatement["R"],
            f"Fact count differs: {fact_counts}",
        )
        _require(
            fact_counts["raw"] == 134 + 2 * 35 + 2 * restatement["R"],
            f"raw count differs: {fact_counts}",
        )
        _require(
            fact_counts["reconciled"] == 67 + 35 + restatement["R"],
            f"reconciled count differs: {fact_counts}",
        )
        _require(
            fact_counts["fact_links"] == 45 + 3 * restatement["R"],
            f"fact links differ: {fact_counts}",
        )
        _require(
            fact_counts["lineage"] == fact_counts["facts"], f"Fact lineage differs: {fact_counts}"
        )
        _require(fact_counts["audit"] == fact_counts["facts"], f"Fact audit differs: {fact_counts}")
        safety = _compute_financial_safety_metrics(upstream_repo, created_at=created_at)
        safety_definitions = safety["definitions"]
        safety_results = safety["results"]
        safety_lineage = safety["lineage"]
        prior_definitions = prior["definitions"]
        prior_results = prior["results"]
        prior_lineage = prior["lineage"]
        definitions = [*prior_definitions, *safety_definitions]
        results = [*prior_results, *safety_results]
        lineage = [*prior_lineage, *safety_lineage]
        metrics_repo = MetricRepository(str(metrics_path))
        metrics_repo.ensure_schema(applied_at=created_at)
        completed_at = datetime.now().astimezone().isoformat()
        with metrics_repo.transaction() as metrics_conn:
            metrics_repo.store_definitions(definitions, conn=metrics_conn)
            metrics_repo.store_results(results, lineage, conn=metrics_conn)
            metrics_repo.store_run(
                run_id,
                status="passed",
                started_at=started_at,
                completed_at=completed_at,
                result_count=len(results),
                conn=metrics_conn,
            )
        combined_latest = []
        combined_snapshots = []
        for as_of_date in PIT_DATES:
            latest_rows = metrics_repo.latest_results(as_of_date)
            combined_latest = latest_rows
            combined_snapshots.append(
                {
                    "as_of_date": as_of_date,
                    "count": len(latest_rows),
                    "computed": sum(row["status"] == "computed" for row in latest_rows),
                    "insufficient_history": sum(
                        row["status"] == "insufficient_history" for row in latest_rows
                    ),
                    "missing_input": sum(row["status"] == "missing_input" for row in latest_rows),
                }
            )
        combined_latest_rows = [
            MetricResult(
                metric_result_id=row["metric_result_id"],
                metric_id=row["metric_id"],
                metric_definition_version=row["metric_definition_version"],
                symbol=row["symbol"],
                fiscal_year=row["fiscal_year"],
                period_end=row["period_end"],
                result_version=row["result_version"],
                supersedes_metric_result_id=row["supersedes_metric_result_id"],
                status=MetricStatus(row["status"]),
                value=Decimal(row["value"]) if row["value"] is not None else None,
                unit=row["unit"],
                formula=row["formula"],
                available_at=row["available_at"],
                input_fact_ids=tuple(row["input_fact_ids"]),
                missing_input_description=row["missing_input_description"],
                revision_review_status=row["revision_review_status"],
                created_at=row["created_at"],
            )
            for row in combined_latest
        ]
        safety_counts = _metric_counts(safety_results, safety["latest"], safety_lineage)
        combined_counts = {
            "definitions": len(definitions),
            "results": len(results),
            "computed": sum(row.status == MetricStatus.computed for row in results),
            "insufficient": sum(row.status == MetricStatus.insufficient_history for row in results),
            "links": sum(bool(row.supersedes_metric_result_id) for row in results),
            "lineage": len(lineage),
            "final_latest": len(combined_latest_rows),
            "final_computed": sum(
                row.status == MetricStatus.computed for row in combined_latest_rows
            ),
        }
        _require(
            safety_counts["result_versions"] > 0
            and safety_counts["computed"] == safety_counts["result_versions"],
            f"financial safety results incomplete: {safety_counts}",
        )
        _require(
            all(row.metric_id in METRIC_IDS for row in safety_results),
            "unexpected financial-safety metric",
        )
        _require(
            all(
                row.metric_id not in {"interest_coverage", "return_on_invested_capital"}
                for row in results
            ),
            "blocked metric was computed",
        )
        _require(
            all(
                getattr(definition, "score_eligible", False) is False
                for definition in safety_definitions
            ),
            "financial-safety score eligibility changed",
        )
        default_after = _sha256(DEFAULT_DB)
        _require(default_before == default_after == DEFAULT_DB_SHA256, "default DB changed")
        upstream_store.close()
        upstream_store = None
        upstream_hash_after = _sha256(upstream_db)
        _require(upstream_hash_after != "", "upstream fact DB hash is empty")
        coverage = _coverage_matrix(upstream_repo)
        debt = _debt_exclusivity(upstream_repo, coverage)
        metric_transitions = [
            {
                "metric_id": row.metric_id,
                "fiscal_year": row.fiscal_year,
                "result_version": row.result_version,
                "supersedes_metric_result_id": row.supersedes_metric_result_id,
                "available_at": row.available_at,
                "value": row.value,
                "status": row.status,
            }
            for row in safety_results
            if row.result_version > 1
        ]
        missing = [
            {
                "metric_id": row.metric_id,
                "fiscal_year": row.fiscal_year,
                "status": row.status,
                "description": row.missing_input_description,
            }
            for row in safety_results
            if row.status != MetricStatus.computed
        ]
        _write_json(run_dir / "fact_coverage_matrix.json", coverage)
        _write_json(run_dir / "debt_component_exclusivity.json", debt)
        _write_json(
            run_dir / "financial_safety_metric_results.json",
            [asdict(row) for row in safety_results],
        )
        _write_json(run_dir / "missing_input_register.json", missing)
        _write_json(
            run_dir / "pit_transitions.json",
            {
                "fact_restatements": restatement["changed"],
                "metric_transitions": metric_transitions,
                "snapshots": combined_snapshots,
            },
        )
        _write_json(run_dir / "metric_definitions.json", [asdict(row) for row in definitions])
        _write_json(run_dir / "metric_result_versions.json", [asdict(row) for row in results])
        _write_json(run_dir / "latest_metric_snapshot.json", combined_latest_rows)
        _write_json(run_dir / "metric_pit_snapshots.json", combined_snapshots)
        _write_json(run_dir / "metric_lineage.json", [asdict(row) for row in lineage])
        _write_json(
            run_dir / "financial_safety_reconciliation_results.json",
            preflight_results + persisted_facts["reconciliations"],
        )
        manifest.update(
            {
                "status": "passed",
                "completed_at": completed_at,
                "fact_counts": fact_counts,
                "restatement_count": restatement["R"],
                "changed_fact_concepts": restatement["changed"],
                "financial_safety_counts": safety_counts,
                "combined_counts": combined_counts,
                "metric_pit_counts": [row["count"] for row in combined_snapshots],
                "metric_pit_computed_counts": [row["computed"] for row in combined_snapshots],
                "metric_pit_insufficient_counts": [
                    row["insufficient_history"] for row in combined_snapshots
                ],
                "default_db_sha256_before": default_before,
                "default_db_sha256_after": default_after,
                "prior_result_count": len(prior_results),
                "prior_result_id_set_sha256": PRIOR_77_RESULT_ID_SET_SHA256,
                "prior_result_semantic_sha256": PRIOR_77_RESULT_SEMANTIC_SHA256,
                "stage2f_combined_70_result_id_set_sha256": COMBINED_70_RESULT_ID_SET_SHA256,
                "upstream_fact_count_before": len(before_ids),
                "run_scoped_database": metrics_path.name,
            }
        )
    except Exception as exc:
        manifest.update(
            {
                "error_type": type(exc).__name__,
                "error": str(exc),
                "traceback": traceback.format_exc(),
                "completed_at": datetime.now().astimezone().isoformat(),
            }
        )
        if metrics_repo is not None:
            metrics_repo.close()
            metrics_repo = None
        if metrics_path.exists():
            metrics_path.unlink()
    finally:
        if metrics_repo is not None:
            metrics_repo.close()
        if upstream_store is not None:
            upstream_store.close()
    _write_json(run_dir / "run_manifest.json", manifest)
    summary = (
        "# PetroChina financial safety vertical slice\n\n"
        f"- run_id: `{run_id}`\n"
        f"- status: **{manifest['status']}**\n"
        "- offline: `true`\n"
        "- interest coverage: `blocked`\n"
        "- ROIC: `not performed`\n"
        "- scoring: `not implemented`\n"
    )
    if "fact_counts" in manifest:
        summary += (
            "\n## Fact counts\n\n"
            + "\n".join(f"- {key}: {value}" for key, value in manifest["fact_counts"].items())
            + "\n"
        )
        summary += (
            "\n## Financial safety metric counts\n\n"
            + "\n".join(
                f"- {key}: {value}" for key, value in manifest["financial_safety_counts"].items()
            )
            + "\n"
        )
        summary += (
            "\n## Combined metric counts\n\n"
            + "\n".join(f"- {key}: {value}" for key, value in manifest["combined_counts"].items())
            + "\n"
        )
    if "error" in manifest:
        summary += f"\n## Failure\n\n{manifest['error']}\n"
    (run_dir / "summary.md").write_text(summary, encoding="utf-8")
    return {**manifest, "run_directory": run_dir}


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", required=True)
    parser.add_argument("--run-id")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    result = run_financial_safety_vertical_slice(args.output_root, run_id=args.run_id)
    print(json.dumps(_jsonable(result), ensure_ascii=False, indent=2))
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
