"""Offline M2 Stage 2F PetroChina dividend realization vertical slice.

The runner rebuilds the prior financial-safety foundation in a run-scoped
temporary directory, reconciles only committed dividend evidence through Rule
007, and replays the five annual-report PIT dates with AsOfQuery.  It never
opens the default database, shared PDF cache, network, or a PDF parser.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import tempfile
import traceback
from dataclasses import asdict
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from ashare_research.events.dividend import (
    DIVIDEND_EVENT_CONTRACT,
    build_dividend_event_id,
    validate_dividend_event,
)
from ashare_research.facts.as_of import AsOfQuery
from ashare_research.facts.identity import build_fact_id
from ashare_research.facts.repository import FactRepository
from ashare_research.metrics.dividend_realization_definitions import (
    DividendRealizationMetricDefinitionRegistry,
)
from ashare_research.metrics.dividend_realization_engine import (
    DividendRealizationMetricEngine,
)
from ashare_research.metrics.models import MetricDefinition, MetricLineage, MetricResult
from ashare_research.metrics.repository import MetricRepository
from ashare_research.reconciliation.dividend import (
    DIVIDEND_RULE_ID,
    DIVIDEND_RULE_VERSION,
    DividendNumericReconciliationEngine,
)
from ashare_research.reconciliation.models import ReconciliationStatus
from ashare_research.reconciliation.service import OfficialFactReconciliationService
from ashare_research.storage.duckdb_store import DuckDBStore
from ashare_research.tools.official_earnings_quality_fact_foundation import (
    DEFAULT_DB,
    DEFAULT_DB_SHA256,
    SYMBOL,
)
from ashare_research.tools.official_financial_safety_vertical_slice import (
    run_financial_safety_vertical_slice,
)

ROOT = Path(__file__).resolve().parents[3]
EVENTS_PATH = ROOT / "events/dividend_events_2021_2026.json"
REPURCHASE_PATH = ROOT / "events/repurchase_event_scan_2021_2026.json"
SUPPLEMENTAL_DIR = ROOT / "acceptance/fixtures/official_facts/601857.SH/supplemental"
YEARS = (2021, 2022, 2023, 2024, 2025)
ANNUAL_REPORT_DATES = [
    "2022-04-01",
    "2023-03-30",
    "2024-03-26",
    "2025-03-31",
    "2026-03-30",
]
LATEST_AS_OF_DATE = "2026-07-01"
DIVIDEND_EVENT_TYPES = ("interim", "final")
CONCEPTS = ("cash_dividend_total", "cash_dividend_per_share", "share_capital")
CONTRACT = "dividend_realization_vertical_slice_v1"
RECONCILIATION_ENGINE = DividendNumericReconciliationEngine()


class DividendVerticalSliceError(ValueError):
    """A deterministic Stage 2F gate failed."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise DividendVerticalSliceError(message)


def _write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8"
    )


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _url_hash(url: str) -> str:
    """Deterministic evidence locator hash used when PDFs remain uncommitted."""
    return hashlib.sha256(url.encode()).hexdigest()


def _id_set_digest(ids: list[str]) -> str:
    return hashlib.sha256(json.dumps(sorted(ids), separators=(",", ":")).encode()).hexdigest()


def _semantic_digest(results: list[MetricResult]) -> str:
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
    rows = []
    for result in results:
        data = asdict(result)
        rows.append(
            {
                field: str(data[field])
                if field in {"status", "value"} and data[field] is not None
                else data[field]
                for field in fields
            }
        )
    return hashlib.sha256(
        json.dumps(
            sorted(rows, key=lambda row: row["metric_result_id"]),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
    ).hexdigest()


def _metric_result_from_json(item: dict[str, Any]) -> MetricResult:
    return MetricResult(
        metric_result_id=str(item.get("metric_result_id", "")),
        metric_id=str(item["metric_id"]),
        metric_definition_version=str(item["metric_definition_version"]),
        symbol=str(item["symbol"]),
        fiscal_year=int(item["fiscal_year"]),
        period_end=str(item["period_end"]),
        result_version=int(item["result_version"]),
        supersedes_metric_result_id=str(item.get("supersedes_metric_result_id", "")),
        status=item["status"],
        value=Decimal(str(item["value"])) if item.get("value") is not None else None,
        unit=str(item["unit"]),
        formula=str(item["formula"]),
        available_at=str(item["available_at"]),
        input_fact_ids=tuple(item.get("input_fact_ids", [])),
        missing_input_description=str(item.get("missing_input_description", "")),
        revision_review_status=str(item.get("revision_review_status", "")),
        created_at=str(item.get("created_at", "")),
    )


def _load_foundation_metrics(
    foundation_dir: Path,
) -> tuple[list[MetricDefinition], list[MetricResult], list[MetricLineage]]:
    definitions = [
        MetricDefinition(
            metric_id=item["metric_id"],
            version=item["version"],
            display_name_zh=item["display_name_zh"],
            formula=item["formula"],
            input_concept_ids=tuple(item["input_concept_ids"]),
            input_roles=tuple(item["input_roles"]),
            unit=item["unit"],
        )
        for item in _load_json(foundation_dir / "metric_definitions.json")
    ]
    results = [
        _metric_result_from_json(item)
        for item in _load_json(foundation_dir / "metric_result_versions.json")
    ]
    lineage = [MetricLineage(**item) for item in _load_json(foundation_dir / "metric_lineage.json")]
    return definitions, results, lineage


def _validate_event_ledger() -> list[dict[str, Any]]:
    ledger = _load_json(EVENTS_PATH)
    _require(ledger.get("contract") == DIVIDEND_EVENT_CONTRACT, "dividend event contract differs")
    _require(ledger.get("symbol") == SYMBOL, "dividend event symbol differs")
    events = ledger.get("events")
    _require(isinstance(events, list) and len(events) == 10, "dividend event count differs")
    by_year: dict[int, list[dict[str, Any]]] = {year: [] for year in YEARS}
    for raw in events:
        event = dict(raw)
        event["contract"] = DIVIDEND_EVENT_CONTRACT
        event["symbol"] = SYMBOL
        event["event_stage"] = "paid/implemented"
        event["market_scope"] = ledger["market_scope"]
        event["currency"] = ledger["currency"]
        event["share_class"] = ledger["share_class"]
        event["event_id"] = build_dividend_event_id(
            SYMBOL, int(event["source_fiscal_year"]), str(event["event_type"])
        )
        event["event_chain"] = [
            {"stage": "proposal", "date": event["proposal_date"]},
            {"stage": "shareholder_approved", "date": event["shareholder_approved_date"]},
            {"stage": "implementation_announced", "date": event["implementation_announced_date"]},
            {"stage": "paid/implemented", "date": event["payment_date"]},
        ]
        event["source_documents"] = [
            {
                "source_tier": "company_official",
                "source_id": (
                    f"company_ir:{SYMBOL}:{event['source_fiscal_year']}:"
                    f"{event['event_type']}:dividend"
                ),
                "source_document": "PetroChina dividend implementation announcement",
                "source_url": event["company_url"],
                "source_hash": _url_hash(event["company_url"]),
                "source_page": event["source_page"],
            },
            {
                "source_tier": "exchange_official",
                "source_id": (
                    f"sse:{SYMBOL}:{event['source_fiscal_year']}:{event['event_type']}:dividend"
                ),
                "source_document": "SSE dividend implementation disclosure",
                "source_url": event["exchange_url"],
                "source_hash": _url_hash(event["exchange_url"]),
                "source_page": event["source_page"],
            },
        ]
        validate_dividend_event(event)
        by_year[int(event["source_fiscal_year"])].append(event)
    for year, year_events in by_year.items():
        _require(
            {event["event_type"] for event in year_events} == set(DIVIDEND_EVENT_TYPES),
            f"FY{year} event types differ",
        )
        supplemental = _load_json(SUPPLEMENTAL_DIR / f"{year}_dividend_realization.json")
        _require(
            supplemental["contract"] == "dividend_realization_official_facts_v1",
            f"FY{year} supplemental contract differs",
        )
        _require(
            supplemental["dual_official_exact_match"] is True,
            f"FY{year} dual-official match not proven",
        )
        _require(
            supplemental["reconciliation_rule_id"] == DIVIDEND_RULE_ID
            and supplemental["reconciliation_rule_version"] == DIVIDEND_RULE_VERSION,
            f"FY{year} Rule007 binding differs",
        )
        expected = sorted(
            (item["event_type"], item["cash_dividend_total"], item["cash_dividend_per_share"])
            for item in year_events
        )
        actual = sorted(
            (item["event_type"], item["cash_dividend_total"], item["cash_dividend_per_share"])
            for item in supplemental["events"]
        )
        _require(expected == actual, f"FY{year} supplemental event values differ")
    return [
        event
        for year in YEARS
        for event in sorted(
            by_year[year], key=lambda item: DIVIDEND_EVENT_TYPES.index(item["event_type"])
        )
    ]


def _context(event: dict[str, Any]) -> dict[str, Any]:
    year = int(event["source_fiscal_year"])
    period_type = "half_year_ytd" if event["event_type"] == "interim" else "annual"
    period_end = f"{year}-06-30" if period_type == "half_year_ytd" else f"{year}-12-31"
    return {
        "context_id": f"{SYMBOL}|{year}|dividend_{event['event_type']}|consolidated",
        "symbol": SYMBOL,
        "fiscal_year": year,
        "period_type": f"dividend_{event['event_type']}",
        "period_start": f"{year}-01-01",
        "period_end": period_end,
        "instant_or_duration": "duration",
        "consolidation_scope": "consolidated",
        "accounting_standard": "CAS",
        "restatement_version": "original",
        "source_document": "PetroChina dividend implementation announcement",
        "filing_date": event["announcement_date"],
        "created_at": event["announcement_date"],
    }


def _source_fact(
    event: dict[str, Any], concept_id: str, document: dict[str, Any], *, created_at: str
) -> dict[str, Any]:
    year = int(event["source_fiscal_year"])
    period_end = f"{year}-06-30" if event["event_type"] == "interim" else f"{year}-12-31"
    unit = "CNY_PER_SHARE" if concept_id == "cash_dividend_per_share" else "CNY"
    raw_value: Any = (
        event["cash_dividend_per_share"]
        if concept_id == "cash_dividend_per_share"
        else event["cash_dividend_total"]
        if concept_id == "cash_dividend_total"
        else event["share_capital_on_record_date"]
    )
    value = Decimal(str(raw_value))
    source_id = f"{document['source_id']}:{event['event_id']}:{concept_id}"
    fact = {
        "concept_id": concept_id,
        "concept_version": "1",
        "symbol": SYMBOL,
        "value": value,
        "unit": unit,
        "context_id": _context(event)["context_id"],
        "is_derived": False,
        "derived_from": "",
        "derivation_definition_id": "",
        "derivation_version": "",
        "input_fact_ids": "",
        "source_provider": "petrochina_dividend_announcement_registry",
        "source_id": source_id,
        "source_tier": document["source_tier"],
        "source_document": document["source_document"],
        "source_url": document["source_url"],
        "source_hash": document["source_hash"],
        "source_page": document["source_page"],
        "source_table": "分红派息实施公告",
        "source_label": concept_id,
        "fact_version": 1,
        "restatement_version": "original",
        "supersedes_fact_id": "",
        "fiscal_year": year,
        "report_type": "interim" if event["event_type"] == "interim" else "annual",
        "period_start": f"{year}-01-01",
        "period_end": period_end,
        "filing_date": event["announcement_date"],
        "announcement_date": event["announcement_date"],
        "available_at": event["available_at"],
        "raw_value": value,
        "raw_unit": unit,
        "normalized_value": value,
        "normalization_rule": "identity",
        "verification_status": "verified",
        "verification_note": (
            "official implementation announcement; event stage is paid/implemented"
        ),
        "eligible_for_metrics": False,
        "created_at": created_at,
        "event_id": event["event_id"],
    }
    fact["fact_id"] = build_fact_id(fact)
    return fact


def _reconcile_events(
    repo: FactRepository, events: list[dict[str, Any]], *, created_at: str
) -> dict[str, Any]:
    conn = repo.store.connect()
    repo.store_contexts([_context(event) for event in events], conn=conn)
    service = OfficialFactReconciliationService(repo, engine=RECONCILIATION_ENGINE)
    outputs: list[dict[str, Any]] = []
    reconciliations: list[dict[str, Any]] = []
    for event in events:
        documents = {item["source_tier"]: item for item in event["source_documents"]}
        for concept_id in CONCEPTS:
            company_fact = _source_fact(
                event, concept_id, documents["company_official"], created_at=created_at
            )
            exchange_fact = _source_fact(
                event, concept_id, documents["exchange_official"], created_at=created_at
            )
            result = service.reconcile_official_pair(company_fact, exchange_fact)
            _require(
                result.status == ReconciliationStatus.matched,
                f"{event['event_id']}/{concept_id} Rule007 failed: {result.decision_reason}",
            )
            _require(
                result.output_fact is not None,
                f"{event['event_id']}/{concept_id} has no reconciled output",
            )
            output = dict(result.output_fact)
            output["event_id"] = event["event_id"]
            outputs.append(output)
            reconciliations.append(asdict(result))
    return {"outputs": outputs, "reconciliations": reconciliations}


def _fact_rows(as_of: AsOfQuery, as_of_date: str, concept_ids: list[str]) -> list[dict[str, Any]]:
    return as_of.get_latest_available(SYMBOL, as_of_date, concept_ids).to_dict("records")


def _event_facts_by_year(
    as_of: AsOfQuery, as_of_date: str, concept_id: str
) -> dict[int, list[dict[str, Any]]]:
    rows = _fact_rows(as_of, as_of_date, [concept_id])
    result: dict[int, list[dict[str, Any]]] = {year: [] for year in YEARS}
    for row in rows:
        year = int(row.get("fiscal_year") or str(row["period_end"])[:4])
        if year in result and row.get("source_tier") == "reconciled_derived":
            result[year].append(row)
    return result


def _annual_foundation_rows(
    as_of: AsOfQuery, as_of_date: str, concept_id: str
) -> dict[int, dict[str, Any]]:
    rows = _fact_rows(as_of, as_of_date, [concept_id])
    return {
        int(str(row["period_end"])[:4]): row
        for row in rows
        if row.get("period_end", "").endswith("12-31")
        and row.get("source_tier") == "reconciled_derived"
    }


def _complete_roles(
    as_of: AsOfQuery, as_of_date: str, fiscal_year: int
) -> tuple[dict[str, list[dict[str, Any]]], str] | tuple[None, str]:
    dividends = {
        concept: _event_facts_by_year(as_of, as_of_date, concept).get(fiscal_year, [])
        for concept in ("cash_dividend_total", "cash_dividend_per_share")
    }
    event_types = {
        event["event_type"]: event
        for event in _validate_event_ledger()
        if int(event["source_fiscal_year"]) == fiscal_year
        and date.fromisoformat(event["available_at"]) <= date.fromisoformat(as_of_date)
    }
    if set(event_types) != set(DIVIDEND_EVENT_TYPES):
        missing_stage = next(stage for stage in DIVIDEND_EVENT_TYPES if stage not in event_types)
        return None, f"missing implemented event_stage={missing_stage}; fiscal_year={fiscal_year}"
    if any(len(items) != 2 for items in dividends.values()):
        return None, f"event facts are incomplete; fiscal_year={fiscal_year}"
    net_profit = _annual_foundation_rows(
        as_of, as_of_date, "net_profit_attributable_to_parent"
    ).get(fiscal_year)
    operating_cash_flow = _annual_foundation_rows(as_of, as_of_date, "operating_cash_flow").get(
        fiscal_year
    )
    capex = _annual_foundation_rows(as_of, as_of_date, "cash_paid_for_fixed_assets").get(
        fiscal_year
    )
    if any(item is None for item in (net_profit, operating_cash_flow, capex)):
        return None, f"financial foundation input is incomplete; fiscal_year={fiscal_year}"
    return {
        "implemented_dividend": dividends["cash_dividend_total"],
        "net_profit": [net_profit],
        "operating_cash_flow": [operating_cash_flow],
        "cash_paid_for_fixed_assets": [capex],
        "implemented_per_share": dividends["cash_dividend_per_share"],
    }, ""


def _build_metrics(as_of: AsOfQuery, *, created_at: str) -> dict[str, Any]:
    results: list[MetricResult] = []
    lineage: list[MetricLineage] = []
    definitions = DividendRealizationMetricDefinitionRegistry.list_all()
    for fiscal_year in YEARS:
        roles, missing = _complete_roles(as_of, LATEST_AS_OF_DATE, fiscal_year)
        if roles is None:
            continue
        for definition in definitions:
            definition_roles = {role: roles[role] for role in definition.input_roles}
            result, rows = DividendRealizationMetricEngine.compute(
                definition,
                symbol=SYMBOL,
                fiscal_year=fiscal_year,
                role_facts=definition_roles,
                revision_review_status="not_yet_reviewable"
                if fiscal_year == 2025
                else "reviewed_unchanged",
                as_of_date=LATEST_AS_OF_DATE,
                created_at=created_at,
            )
            results.append(result)
            lineage.extend(rows)
    return {"definitions": definitions, "results": results, "lineage": lineage}


def _build_pit(as_of: AsOfQuery) -> dict[str, Any]:
    snapshots = []
    event_transitions = []
    for as_of_date in ANNUAL_REPORT_DATES:
        computed = 0
        available_events = []
        for year in YEARS:
            roles, missing = _complete_roles(as_of, as_of_date, year)
            if roles is not None:
                computed += len(DividendRealizationMetricDefinitionRegistry.list_all())
            else:
                available_events.append({"fiscal_year": year, "gap": missing})
        snapshots.append(
            {
                "as_of_date": as_of_date,
                "available_event_count": sum(
                    len(
                        _event_facts_by_year(as_of, as_of_date, "cash_dividend_total").get(year, [])
                    )
                    for year in YEARS
                ),
                "computed_metric_count": computed,
                "missing_or_incomplete_years": available_events,
            }
        )
    for event in _validate_event_ledger():
        event_transitions.append(
            {
                "event_id": event["event_id"],
                "source_fiscal_year": event["source_fiscal_year"],
                "event_type": event["event_type"],
                "available_at": event["available_at"],
                "payment_date": event["payment_date"],
            }
        )
    return {
        "annual_report_dates": snapshots,
        "latest_as_of_date": LATEST_AS_OF_DATE,
        "event_transitions": event_transitions,
    }


def _metric_counts(repo: MetricRepository, as_of_date: str) -> dict[str, int]:
    conn = repo.connect()
    latest = repo.latest_results(as_of_date)
    return {
        "definitions": conn.execute("SELECT COUNT(*) FROM metric_definitions").fetchone()[0],
        "results": conn.execute("SELECT COUNT(*) FROM metric_results").fetchone()[0],
        "computed": conn.execute(
            "SELECT COUNT(*) FROM metric_results WHERE status='computed'"
        ).fetchone()[0],
        "insufficient": conn.execute(
            "SELECT COUNT(*) FROM metric_results WHERE status='insufficient_history'"
        ).fetchone()[0],
        "missing_input": conn.execute(
            "SELECT COUNT(*) FROM metric_results WHERE status='missing_input'"
        ).fetchone()[0],
        "links": conn.execute(
            "SELECT COUNT(*) FROM metric_results WHERE supersedes_metric_result_id <> ''"
        ).fetchone()[0],
        "lineage": conn.execute("SELECT COUNT(*) FROM metric_lineage").fetchone()[0],
        "final_latest": len(latest),
        "final_computed": sum(row["status"] == "computed" for row in latest),
    }


def run_dividend_realization_vertical_slice(
    output_root: str | Path, *, run_id: str | None = None
) -> dict[str, Any]:
    run_id = (
        run_id
        or f"dividend_realization_601857_SH_2021_2025_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
    )
    run_dir = (
        Path(output_root)
        / "value_assessment"
        / SYMBOL
        / "dividend_realization_vertical_slice"
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
        "contract": CONTRACT,
        "rule_id": DIVIDEND_RULE_ID,
        "rule_version": DIVIDEND_RULE_VERSION,
        "offline": True,
        "network_access": False,
        "pdf_access": False,
        "shared_cache_access": False,
        "default_database_access": False,
        "roic_computation": "not_performed",
        "scoring": "not_implemented",
        "started_at": started_at,
    }
    metrics_repo: MetricRepository | None = None
    upstream_store: DuckDBStore | None = None
    foundation_tmp_dir: Path | None = None
    try:
        default_before = _sha256(DEFAULT_DB)
        _require(default_before == DEFAULT_DB_SHA256, "default DB baseline differs")
        events = _validate_event_ledger()
        repurchase = _load_json(REPURCHASE_PATH)
        _require(
            repurchase.get("status") == "bounded_search_no_event_found",
            "buyback scan status differs",
        )
        _require(
            repurchase.get("events") == []
            and repurchase.get("no_zero_valued_fact_created") is True,
            "buyback zero fact was created",
        )

        foundation_tmp_dir = Path(tempfile.mkdtemp(prefix="m2_stage2f_foundation_"))
        foundation = run_financial_safety_vertical_slice(
            foundation_tmp_dir, run_id=f"{run_id}__foundation"
        )
        _require(foundation["status"] == "passed", "financial-safety foundation rebuild failed")
        foundation_dir = Path(foundation["run_directory"])
        upstream_candidates = sorted(foundation_tmp_dir.rglob("net_profit.duckdb"))
        _require(
            len(upstream_candidates) == 1,
            f"foundation net_profit DuckDB count differs: {len(upstream_candidates)}",
        )
        upstream_db = upstream_candidates[0]
        upstream_store = DuckDBStore(str(upstream_db))
        upstream_repo = FactRepository(upstream_store)
        upstream_conn = upstream_store.connect()
        if True:
            old_fact_ids = [
                row[0]
                for row in upstream_conn.execute(
                    "SELECT fact_id FROM financial_facts ORDER BY fact_id"
                ).fetchall()
            ]
            _require(
                len(old_fact_ids) == 354, f"frozen 354 Fact baseline differs: {len(old_fact_ids)}"
            )
            old_definitions, old_results, old_lineage = _load_foundation_metrics(foundation_dir)
            _require(
                len(old_definitions) == 16 and len(old_results) == 102,
                "frozen 16-definition/102-result baseline differs",
            )
            old_ids_digest = _id_set_digest([item.metric_result_id for item in old_results])
            old_semantic_digest = _semantic_digest(old_results)
            created_at = datetime.now().astimezone().isoformat()
            _reconcile_events(upstream_repo, events, created_at=created_at)
            new_fact_count = upstream_conn.execute(
                "SELECT COUNT(*) FROM financial_facts"
            ).fetchone()[0] - len(old_fact_ids)
            _require(new_fact_count == 90, f"Rule007 Fact delta differs: {new_fact_count}")
            as_of = AsOfQuery(upstream_repo)
            metrics = _build_metrics(as_of, created_at=created_at)
            definitions = [*old_definitions, *metrics["definitions"]]
            results = [*old_results, *metrics["results"]]
            lineage = [*old_lineage, *metrics["lineage"]]
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
            pit = _build_pit(as_of)
            latest_rows = metrics_repo.latest_results(LATEST_AS_OF_DATE)
            final_fact_ids = [
                row[0]
                for row in upstream_conn.execute(
                    "SELECT fact_id FROM financial_facts ORDER BY fact_id"
                ).fetchall()
            ]
            _require(
                set(old_fact_ids).issubset(final_fact_ids), "old Fact IDs changed or disappeared"
            )
            _require(
                _id_set_digest([item.metric_result_id for item in old_results]) == old_ids_digest,
                "old 102 Metric Result IDs changed",
            )
            _require(
                _semantic_digest(old_results) == old_semantic_digest,
                "old 102 Metric Result semantics changed",
            )
            _require(
                all(
                    item.metric_id not in {"return_on_invested_capital", "interest_coverage"}
                    for item in results
                ),
                "blocked metric leaked",
            )
            _require(
                all(
                    getattr(item, "score_eligible", False) is False
                    for item in metrics["definitions"]
                ),
                "dividend metric became score eligible",
            )
            default_after = _sha256(DEFAULT_DB)
            _require(default_before == default_after == DEFAULT_DB_SHA256, "default DB changed")
            _write_json(
                run_dir / "dividend_event_ledger.json",
                {"contract": DIVIDEND_EVENT_CONTRACT, "events": events},
            )
            _write_json(
                run_dir / "dividend_fact_coverage.json",
                {
                    "rule_id": DIVIDEND_RULE_ID,
                    "event_count": len(events),
                    "numeric_fact_count": new_fact_count,
                    "reconciled_fact_count": upstream_conn.execute(
                        "SELECT COUNT(*) FROM financial_facts "
                        "WHERE source_tier='reconciled_derived' "
                        "AND derivation_version=? "
                        "AND source_id LIKE '%RECON_OFFICIAL_NUMERIC_007%'",
                        [DIVIDEND_RULE_VERSION],
                    ).fetchone()[0],
                    "years": {
                        str(year): {
                            "expected_event_types": list(DIVIDEND_EVENT_TYPES),
                            "status": "complete_in_latest"
                            if any(item["source_fiscal_year"] == year for item in events)
                            else "missing",
                        }
                        for year in YEARS
                    },
                },
            )
            _write_json(
                run_dir / "dividend_metric_results.json",
                [asdict(item) for item in metrics["results"]],
            )
            _write_json(run_dir / "repurchase_event_register.json", repurchase)
            _write_json(run_dir / "pit_transitions.json", pit)
            _write_json(run_dir / "metric_definitions.json", [asdict(item) for item in definitions])
            _write_json(run_dir / "metric_result_versions.json", [asdict(item) for item in results])
            _write_json(run_dir / "latest_metric_snapshot.json", latest_rows)
            _write_json(run_dir / "metric_pit_snapshots.json", pit["annual_report_dates"])
            _write_json(run_dir / "metric_lineage.json", [asdict(item) for item in lineage])
            _write_json(run_dir / "definitions.json", [asdict(item) for item in definitions])
            _write_json(run_dir / "results.json", [asdict(item) for item in results])
            _write_json(run_dir / "latest.json", latest_rows)
            _write_json(run_dir / "PIT.json", pit["annual_report_dates"])
            _write_json(run_dir / "transitions.json", pit["event_transitions"])
            _write_json(run_dir / "lineage.json", [asdict(item) for item in lineage])
            combined_counts = _metric_counts(metrics_repo, LATEST_AS_OF_DATE)
            manifest.update(
                {
                    "status": "passed",
                    "completed_at": completed_at,
                    "fact_counts": {
                        "old_facts": len(old_fact_ids),
                        "new_rule007_facts": new_fact_count,
                        "final_facts": len(final_fact_ids),
                    },
                    "old_metric_baseline": {
                        "definitions": len(old_definitions),
                        "results": len(old_results),
                        "id_set_sha256": old_ids_digest,
                        "semantic_sha256": old_semantic_digest,
                    },
                    "dividend_metric_counts": {
                        "definitions": len(metrics["definitions"]),
                        "results": len(metrics["results"]),
                        "computed": sum(item.status == "computed" for item in metrics["results"]),
                        "lineage": len(metrics["lineage"]),
                    },
                    "combined_counts": combined_counts,
                    "pit_snapshots": pit["annual_report_dates"],
                    "default_db_sha256_before": default_before,
                    "default_db_sha256_after": default_after,
                    "run_scoped_database": metrics_path.name,
                    "valuation_pit_foundation": "allowed",
                }
            )
            upstream_store.close()
            upstream_store = None
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
        if foundation_tmp_dir is not None:
            shutil.rmtree(foundation_tmp_dir, ignore_errors=True)
    _write_json(run_dir / "run_manifest.json", manifest)
    summary = "# PetroChina dividend realization vertical slice\n\n"
    summary += f"- status: **{manifest['status']}**\n"
    summary += "- offline: `true`\n"
    summary += "- ROIC: `not performed`\n"
    summary += "- scoring: `not implemented`\n"
    summary += "- buyback evidence: `bounded_search_no_event_found`\n"
    if "combined_counts" in manifest:
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
    result = run_dividend_realization_vertical_slice(args.output_root, run_id=args.run_id)
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
