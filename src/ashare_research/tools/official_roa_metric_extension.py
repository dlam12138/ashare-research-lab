"""Build the offline 2021-2025 consolidated ROA metric extension.

Stage 2D-F calls the Stage 2D-E net-profit foundation.  That foundation in
turn rebuilds the Stage 2D-B facts and Stage 2D-D 70-result baseline.  This
runner then replays the five annual-report PIT dates and computes only
``return_on_average_total_assets`` from the reconciled ``net_profit`` duration
fact and adjacent reconciled ``total_assets`` instant facts.

The average balance is calculated in the Metric Engine; no average-balance
Fact is created.  The runner is deliberately offline and run-scoped: it does
not open the default database, shared cache, PDFs, or network, and it emits no
ROIC or scoring output.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import tempfile
from dataclasses import asdict
from datetime import date, datetime, timedelta
from decimal import ROUND_HALF_EVEN, Context, Decimal, localcontext
from pathlib import Path
from typing import Any

from ashare_research.facts.as_of import AsOfQuery
from ashare_research.facts.repository import FactRepository
from ashare_research.metrics.capital_return_definitions import (
    CapitalReturnMetricDefinitionRegistry,
)
from ashare_research.metrics.cashflow_definitions import (
    CashFlowMetricDefinitionRegistry,
)
from ashare_research.metrics.definitions import MetricDefinitionRegistry
from ashare_research.metrics.earnings_quality_definitions import (
    EarningsQualityMetricDefinitionRegistry,
)
from ashare_research.metrics.engine import CANONICAL_QUANTUM, MetricEngine
from ashare_research.metrics.identity import validate_canonical_metric_result_id
from ashare_research.metrics.models import MetricLineage, MetricResult
from ashare_research.metrics.repository import MetricRepository
from ashare_research.storage.duckdb_store import DuckDBStore
from ashare_research.tools.official_cashflow_metric_extension import (
    _review_statuses as cashflow_review_statuses,
)
from ashare_research.tools.official_cashflow_metric_extension import (
    build_cashflow_metric_versions,
)
from ashare_research.tools.official_earnings_quality_fact_foundation import (
    DEFAULT_DB,
    DEFAULT_DB_SHA256,
    REVIEW_DIR,
    SYMBOL,
)
from ashare_research.tools.official_earnings_quality_metric_extension import (
    _earnings_review_statuses,
    build_earnings_metric_versions,
)
from ashare_research.tools.official_fact_metric_foundation import (
    build_metric_versions,
)
from ashare_research.tools.official_net_profit_fact_foundation import (
    run_net_profit_foundation,
)
from ashare_research.tools.official_roe_metric_extension import (
    EXPECTED_COUNTS_REF_DIGEST,
    PRIOR_63_SEMANTIC_SHA256,
    UPSTREAM_180_FACT_ID_SET_SHA256,
    build_roe_metric_versions,
)

ROOT = Path(__file__).resolve().parents[3]
CONTRACT = "roa_metric_extension_v1"
YEARS = (2021, 2022, 2023, 2024, 2025)
ROA_METRIC_ID = "return_on_average_total_assets"
NUMERATOR_CONCEPT = "net_profit"
DENOMINATOR_CONCEPT = "total_assets"
ANNUAL_REPORT_DATES = [
    "2022-04-01",
    "2023-03-30",
    "2024-03-26",
    "2025-03-31",
    "2026-03-30",
]
REVISION_REVIEW_STATUS = {
    2021: "reviewed_unchanged",
    2022: "reviewed_changed",
    2023: "reviewed_changed",
    2024: "reviewed_unchanged",
    2025: "not_yet_reviewable",
}
ROA_EXPECTED = {
    "definitions": 1,
    "result_versions": 7,
    "computed_versions": 7,
    "insufficient_history_versions": 0,
    "version_links": 2,
    "lineage_rows": 21,
    "final_latest": 5,
}
COMBINED_EXPECTED = {
    "definitions": 12,
    "results": 77,
    "computed": 73,
    "insufficient_history": 4,
    "version_links": 17,
    "lineage": 164,
    "final_latest": 60,
    "final_computed": 56,
}
PIT_LATEST = [0, 12, 24, 36, 48, 60]
PIT_COMPUTED = [0, 8, 20, 32, 44, 56]
PIT_INSUFFICIENT = [0, 4, 4, 4, 4, 4]
COMBINED_70_RESULT_ID_SET_SHA256 = (
    "bdd9d4fee9777f0c28f31056711675ab3acf98786bc09090cde25ab7ef551df0"
)


class ROAMetricExtensionError(ValueError):
    """A deterministic Stage 2D-F acceptance gate failed."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ROAMetricExtensionError(message)


def _jsonable(value: Any) -> Any:
    if isinstance(value, Path):
        return value.name
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, list | tuple):
        return [_jsonable(item) for item in value]
    if isinstance(value, date | datetime):
        return value.isoformat()
    if hasattr(value, "item"):
        return value.item()
    return value


def _write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(_jsonable(value), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _id_set_digest(ids: list[str]) -> str:
    payload = json.dumps(sorted(ids), separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()


def _newline_id_set_digest(ids: list[str]) -> str:
    return hashlib.sha256("\n".join(sorted(ids)).encode()).hexdigest()


def _result_semantic_digest(results: list[MetricResult]) -> str:
    fields = (
        "metric_result_id", "metric_id", "metric_definition_version", "symbol",
        "fiscal_year", "period_end", "result_version",
        "supersedes_metric_result_id", "status", "value", "unit", "formula",
        "available_at", "input_fact_ids", "missing_input_description",
        "revision_review_status",
    )
    rows = []
    for result in results:
        data = asdict(result)
        rows.append({
            field: (
                str(data[field])
                if field in {"status", "value"} and data[field] is not None
                else data[field]
            )
            for field in fields
        })
    payload = json.dumps(
        sorted(rows, key=lambda item: item["metric_result_id"]),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode()).hexdigest()


def build_run_id(now: datetime | None = None) -> str:
    timestamp = (now or datetime.now()).strftime("%Y%m%d_%H%M%S_%f")
    return f"roa_metric_extension_601857_SH_2021_2025_{timestamp}"


def _changed(old: MetricResult, candidate: MetricResult) -> bool:
    return (
        old.value != candidate.value
        or old.status != candidate.status
        or old.input_fact_ids != candidate.input_fact_ids
    )


def _validate_input_fact(
    row: dict[str, Any], *, concept: str, fiscal_year: int, instant: bool,
) -> None:
    period_type = "instant" if instant else "annual"
    _require(row["concept_id"] == concept, f"unexpected concept for {concept}")
    _require(row["unit"] == "万元", f"{concept} unit differs")
    _require(row["source_tier"] == "reconciled_derived", f"{concept} source tier differs")
    _require(row["eligible_for_metrics"] is True, f"{concept} is not eligible")
    expected_context = f"{SYMBOL}|{fiscal_year}|{period_type}|consolidated"
    _require(row["context_id"] == expected_context, f"{concept} context differs")
    _require(str(row["period_end"]) == f"{fiscal_year}-12-31", f"{concept} period differs")


def build_roa_metric_versions(
    as_of: AsOfQuery,
    available_dates: list[str],
    *,
    created_at: str,
    revision_review_status: dict[int, str] | None = None,
) -> dict[str, Any]:
    """Replay Fact PIT and emit only semantically distinct ROA versions."""
    _require(available_dates == ANNUAL_REPORT_DATES, "Fact PIT dates differ")
    definition = CapitalReturnMetricDefinitionRegistry.get(ROA_METRIC_ID)
    _require(definition is not None, "ROA definition is not registered")
    statuses = revision_review_status or REVISION_REVIEW_STATUS
    latest_by_key: dict[tuple[str, int, str, str], MetricResult] = {}
    results: list[MetricResult] = []
    lineage: list[MetricLineage] = []
    for as_of_date in available_dates:
        numerator_frame = as_of.get_latest_available(
            SYMBOL, as_of_date, [NUMERATOR_CONCEPT]
        )
        assets_frame = as_of.get_latest_available(
            SYMBOL, as_of_date, [DENOMINATOR_CONCEPT]
        )
        numerators = {
            int(str(row["period_end"])[:4]): row
            for row in numerator_frame.to_dict("records")
        }
        assets = {
            int(str(row["period_end"])[:4]): row
            for row in assets_frame.to_dict("records")
        }
        for fiscal_year in sorted(numerators):
            numerator = numerators[fiscal_year]
            opening = assets.get(fiscal_year - 1)
            closing = assets.get(fiscal_year)
            _validate_input_fact(
                numerator,
                concept=NUMERATOR_CONCEPT,
                fiscal_year=fiscal_year,
                instant=False,
            )
            if opening is not None:
                _validate_input_fact(
                    opening,
                    concept=DENOMINATOR_CONCEPT,
                    fiscal_year=fiscal_year - 1,
                    instant=True,
                )
            if closing is not None:
                _validate_input_fact(
                    closing,
                    concept=DENOMINATOR_CONCEPT,
                    fiscal_year=fiscal_year,
                    instant=True,
                )
            arguments = {
                "definition": definition,
                "symbol": SYMBOL,
                "fiscal_year": fiscal_year,
                "primary_fact": numerator,
                "secondary_fact": opening,
                "tertiary_fact": closing,
                "revision_review_status": statuses[fiscal_year],
                "as_of_date": as_of_date,
                "created_at": created_at,
            }
            candidate, _ = MetricEngine.compute(**arguments)
            key = (SYMBOL, fiscal_year, definition.metric_id, definition.version)
            previous = latest_by_key.get(key)
            if previous is not None and not _changed(previous, candidate):
                continue
            result, rows = MetricEngine.compute(
                **arguments,
                result_version=previous.result_version + 1 if previous else 1,
                supersedes_metric_result_id=(
                    previous.metric_result_id if previous else ""
                ),
            )
            latest_by_key[key] = result
            results.append(result)
            lineage.extend(rows)
    return {
        "results": results,
        "lineage": lineage,
        "latest": sorted(
            latest_by_key.values(),
            key=lambda item: (item.fiscal_year, item.metric_id),
        ),
    }


def _normalize_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized = []
    for row in rows:
        item = dict(row)
        if isinstance(item.get("input_fact_ids"), str):
            item["input_fact_ids"] = json.loads(item["input_fact_ids"])
        item["value"] = (
            str(item["value"]) if item.get("value") is not None else None
        )
        normalized.append(item)
    return normalized


def _direct_roa_value(
    numerator: dict[str, Any], opening: dict[str, Any], closing: dict[str, Any]
) -> Decimal:
    with localcontext(Context(prec=28, rounding=ROUND_HALF_EVEN)):
        average = (
            Decimal(str(opening["value"])) + Decimal(str(closing["value"]))
        ) / Decimal(2)
        return (Decimal(str(numerator["value"])) / average).quantize(
            CANONICAL_QUANTUM,
            rounding=ROUND_HALF_EVEN,
        )


def _acceptance(
    repo: MetricRepository,
    *,
    roa: dict[str, Any],
    stage2a: dict[str, Any],
    cashflow: dict[str, Any],
    earnings: dict[str, Any],
    roe: dict[str, Any],
    available_dates: list[str],
    upstream_fact_ids: list[str],
    as_of: AsOfQuery,
) -> dict[str, Any]:
    conn = repo.connect()
    combined_counts = {
        "definitions": conn.execute("SELECT COUNT(*) FROM metric_definitions").fetchone()[0],
        "results": conn.execute("SELECT COUNT(*) FROM metric_results").fetchone()[0],
        "computed": conn.execute(
            "SELECT COUNT(*) FROM metric_results WHERE status='computed'"
        ).fetchone()[0],
        "insufficient_history": conn.execute(
            "SELECT COUNT(*) FROM metric_results WHERE status='insufficient_history'"
        ).fetchone()[0],
        "version_links": conn.execute(
            "SELECT COUNT(*) FROM metric_results WHERE supersedes_metric_result_id <> ''"
        ).fetchone()[0],
        "lineage": conn.execute("SELECT COUNT(*) FROM metric_lineage").fetchone()[0],
    }
    latest = _normalize_rows(repo.latest_results(available_dates[-1]))
    combined_counts["final_latest"] = len(latest)
    combined_counts["final_computed"] = sum(item["status"] == "computed" for item in latest)
    _require(
        combined_counts == COMBINED_EXPECTED,
        f"combined metric counts differ: {combined_counts}",
    )

    roa_results = roa["results"]
    roa_counts = {
        "definitions": 1,
        "result_versions": len(roa_results),
        "computed_versions": sum(str(item.status) == "computed" for item in roa_results),
        "insufficient_history_versions": sum(
            str(item.status) == "insufficient_history" for item in roa_results
        ),
        "version_links": sum(bool(item.supersedes_metric_result_id) for item in roa_results),
        "lineage_rows": len(roa["lineage"]),
        "final_latest": len(roa["latest"]),
    }
    _require(roa_counts == ROA_EXPECTED, f"ROA metric counts differ: {roa_counts}")

    first = date.fromisoformat(available_dates[0])
    snapshots = []
    for as_of_date in [(first - timedelta(days=1)).isoformat(), *available_dates]:
        rows = _normalize_rows(repo.latest_results(as_of_date))
        snapshots.append({
            "as_of_date": as_of_date,
            "count": len(rows),
            "computed": sum(row["status"] == "computed" for row in rows),
            "insufficient_history": sum(
                row["status"] == "insufficient_history" for row in rows
            ),
        })
    _require(
        [item["count"] for item in snapshots] == PIT_LATEST,
        f"Metric PIT latest counts differ: {snapshots}",
    )
    _require(
        [item["computed"] for item in snapshots] == PIT_COMPUTED,
        f"Metric PIT computed counts differ: {snapshots}",
    )
    _require(
        [item["insufficient_history"] for item in snapshots] == PIT_INSUFFICIENT,
        f"Metric PIT insufficient counts differ: {snapshots}",
    )

    prior_results = [
        *stage2a["results"], *cashflow["results"], *earnings["results"], *roe["results"]
    ]
    prior_ids = [item.metric_result_id for item in prior_results]
    _require(
        len(prior_results) == 70
        and _newline_id_set_digest(prior_ids)
        == COMBINED_70_RESULT_ID_SET_SHA256,
        "prior 70 Metric Result ID set changed",
    )
    _require(
        _id_set_digest([
            item.metric_result_id
            for item in [
                *stage2a["results"], *cashflow["results"], *earnings["results"]
            ]
        ])
        == EXPECTED_COUNTS_REF_DIGEST,
        "prior 63 Metric Result ID set changed",
    )
    _require(
        _result_semantic_digest([*stage2a["results"], *cashflow["results"], *earnings["results"]])
        == PRIOR_63_SEMANTIC_SHA256,
        "prior 63 Metric Result semantics changed",
    )
    for item in prior_results:
        validate_canonical_metric_result_id(item)

    final_numerator = as_of.get_latest_available(SYMBOL, available_dates[-1], [NUMERATOR_CONCEPT])
    final_assets = as_of.get_latest_available(SYMBOL, available_dates[-1], [DENOMINATOR_CONCEPT])
    numerators = {
        int(str(row["period_end"])[:4]): row
        for row in final_numerator.to_dict("records")
    }
    assets = {
        int(str(row["period_end"])[:4]): row
        for row in final_assets.to_dict("records")
    }
    latest_values = {}
    for fiscal_year in YEARS:
        expected = _direct_roa_value(
            numerators[fiscal_year], assets[fiscal_year - 1], assets[fiscal_year]
        )
        latest_item = next(
            item for item in roa["latest"] if item.fiscal_year == fiscal_year
        )
        _require(
            latest_item.value == expected,
            f"ROA {fiscal_year} value differs: {latest_item.value}",
        )
        latest_values[fiscal_year] = latest_item.value

    transitions = []
    versioned = [item for item in roa_results if item.result_version > 1]
    _require(
        {(item.fiscal_year, item.metric_id) for item in versioned}
        == {(2022, ROA_METRIC_ID), (2023, ROA_METRIC_ID)},
        "ROA version-chain keys differ",
    )
    by_id = {item.metric_result_id: item for item in roa_results}
    for after in sorted(versioned, key=lambda item: item.fiscal_year):
        before = by_id[after.supersedes_metric_result_id]
        _require(
            before.result_version == 1
            and after.result_version == 2
            and before.input_fact_ids != after.input_fact_ids
            and before.available_at < after.available_at,
            f"ROA {after.fiscal_year} chain differs",
        )
        transitions.append({
            "fiscal_year": after.fiscal_year,
            "metric_id": after.metric_id,
            "before": asdict(before),
            "after": asdict(after),
            "pit_before_date": (
                date.fromisoformat(after.available_at) - timedelta(days=1)
            ).isoformat(),
            "pit_switch_date": after.available_at,
        })
    _require(
        [item["fiscal_year"] for item in transitions] == [2022, 2023],
        "ROA transition order differs",
    )
    _require(
        [item["pit_switch_date"] for item in transitions] == ["2024-03-26", "2025-03-31"],
        "ROA transition dates differ",
    )

    roa_2024 = next(item for item in roa_results if item.fiscal_year == 2024)
    assets_2023 = assets[2023]
    _require(
        int(assets_2023["fact_version"]) == 2
        and roa_2024.input_fact_ids[1] == str(assets_2023["fact_id"]),
        "ROA 2024 opening did not use 2023 assets v2",
    )
    _require(
        all(
            item.revision_review_status == "not_yet_reviewable"
            for item in roa["latest"] if item.fiscal_year == 2025
        ),
        "ROA 2025 review status differs",
    )
    _require(
        all(
            item.metric_id != "return_on_invested_capital"
            for item in [*roa_results, *prior_results]
        ),
        "ROIC was unexpectedly computed",
    )
    _require(
        len(upstream_fact_ids) == 201,
        "201 Fact foundation changed",
    )
    return {
        "combined_counts": combined_counts,
        "roa_counts": roa_counts,
        "snapshots": snapshots,
        "latest": latest,
        "roa_latest_values": latest_values,
        "transitions": transitions,
        "roa_2024": asdict(roa_2024),
        "prior_result_id_set_sha256": _id_set_digest(prior_ids),
        "prior_result_id_set_sha256_newline": _newline_id_set_digest(prior_ids),
        "prior_result_semantic_sha256": _result_semantic_digest(
            [*stage2a["results"], *cashflow["results"], *earnings["results"]]
        ),
        "upstream_fact_id_set_sha256": _id_set_digest(upstream_fact_ids),
    }


def run_roa_metric_extension(
    output_root: str | Path, *, run_id: str | None = None
) -> dict[str, Any]:
    """Execute the complete offline Stage 2D-F acceptance."""
    run_id = run_id or build_run_id()
    run_dir = (
        Path(output_root)
        / "value_assessment"
        / SYMBOL
        / "roa_metric_extension"
        / "2021_2025"
        / run_id
    )
    run_dir.mkdir(parents=True, exist_ok=False)
    upstream_dir = run_dir / "upstream_net_profit_official_facts"
    metrics_path = run_dir / "metrics.duckdb"
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
        "contract": CONTRACT,
        "metric_schema_version": MetricRepository.schema_version,
        "database": metrics_path.name,
        "scoring": "not_implemented",
        "roic_computation": "not_performed",
        "investment_advice": "not_produced",
        "started_at": started_at,
    }
    metrics_repo = None
    upstream_store = None
    try:
        default_before = _sha256(DEFAULT_DB)
        with tempfile.TemporaryDirectory(prefix="m2_stage2f_") as temp_root:
            upstream = run_net_profit_foundation(temp_root, run_id="upstream")
            _require(upstream["status"] == "passed", "Stage 2D-E upstream failed")
            shutil.move(str(upstream["run_directory"]), str(upstream_dir))
        _require(
            upstream["counts"] == {
                "contexts": 11,
                "financial_facts": 201,
                "raw_ineligible_facts": 134,
                "reconciled_eligible_facts": 67,
                "version_chain_links": 45,
                "audit": 201,
                "lineage": 201,
            },
            f"Stage 2D-E counts differ: {upstream['counts']}",
        )
        upstream_db = upstream_dir / "net_profit.duckdb"
        upstream_hash_before = _sha256(upstream_db)
        upstream_store = DuckDBStore(str(upstream_db))
        upstream_repo = FactRepository(upstream_store)
        conn = upstream_store.connect()
        upstream_fact_ids = [
            row[0] for row in conn.execute(
                "SELECT fact_id FROM financial_facts ORDER BY fact_id"
            ).fetchall()
        ]
        available_dates = [
            row[0] for row in conn.execute(
                """SELECT DISTINCT available_at FROM financial_facts
                   WHERE source_tier='reconciled_derived'
                     AND eligible_for_metrics=TRUE
                   ORDER BY available_at"""
            ).fetchall()
        ]
        _require(available_dates == ANNUAL_REPORT_DATES, "Fact PIT dates differ")
        as_of = AsOfQuery(upstream_repo)
        created_at = datetime.now().astimezone().isoformat()

        annual_paths = [
            REVIEW_DIR / f"{year}_reviewed_by_{year + 1}_annual.json"
            for year in YEARS[:-1]
        ]
        capex_paths = [
            REVIEW_DIR / f"capex_cash_{year}_reviewed_by_{year + 1}.json"
            for year in YEARS[:-1]
        ]
        reviewed = cashflow_review_statuses(annual_paths, capex_paths)
        stage2a_reviewed = {
            year: {
                concept: changed
                for concept, changed in concepts.items()
                if concept != "cash_paid_for_fixed_assets"
            }
            for year, concepts in reviewed.items()
        }
        stage2a = build_metric_versions(
            as_of, available_dates, stage2a_reviewed, created_at=created_at
        )
        cashflow = build_cashflow_metric_versions(
            as_of, available_dates, reviewed, created_at=created_at
        )
        earnings = build_earnings_metric_versions(
            as_of, available_dates, _earnings_review_statuses(), created_at=created_at
        )
        roe = build_roe_metric_versions(as_of, available_dates, created_at=created_at)
        roa = build_roa_metric_versions(
            as_of,
            available_dates,
            created_at=created_at,
        )
        definitions = [
            *MetricDefinitionRegistry.list_all(),
            *CashFlowMetricDefinitionRegistry.list_all(),
            *EarningsQualityMetricDefinitionRegistry.list_all(),
            *CapitalReturnMetricDefinitionRegistry.list_all(include_roa=True),
        ]
        results = [
            *stage2a["results"], *cashflow["results"],
            *earnings["results"], *roe["results"], *roa["results"],
        ]
        lineage = [
            *stage2a["lineage"], *cashflow["lineage"],
            *earnings["lineage"], *roe["lineage"], *roa["lineage"],
        ]
        _require(
            {item.metric_id for item in definitions}
            == {
                *{item.metric_id for item in MetricDefinitionRegistry.list_all()},
                *{item.metric_id for item in CashFlowMetricDefinitionRegistry.list_all()},
                *{item.metric_id for item in EarningsQualityMetricDefinitionRegistry.list_all()},
                "return_on_average_equity_attributable_to_parent",
                ROA_METRIC_ID,
            },
            "metric definitions contain an unexpected metric",
        )

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
        acceptance = _acceptance(
            metrics_repo,
            roa=roa,
            stage2a=stage2a,
            cashflow=cashflow,
            earnings=earnings,
            roe=roe,
            available_dates=available_dates,
            upstream_fact_ids=upstream_fact_ids,
            as_of=as_of,
        )
        upstream_store.close()
        upstream_store = None
        upstream_hash_after = _sha256(upstream_db)
        _require(
            upstream_hash_before == upstream_hash_after,
            "metric read modified upstream DuckDB",
        )
        default_after = _sha256(DEFAULT_DB)
        _require(
            default_before == default_after == DEFAULT_DB_SHA256,
            "default research.duckdb changed",
        )

        _write_json(run_dir / "metric_definitions.json", [asdict(item) for item in definitions])
        _write_json(run_dir / "metric_result_versions.json", [asdict(item) for item in results])
        _write_json(run_dir / "latest_metric_snapshot.json", acceptance["latest"])
        _write_json(run_dir / "metric_pit_snapshots.json", acceptance["snapshots"])
        _write_json(run_dir / "roa_metric_transitions.json", acceptance["transitions"])
        _write_json(run_dir / "metric_lineage.json", [asdict(item) for item in lineage])
        manifest.update(
            status="passed",
            transaction_committed=True,
            upstream={
                "status": upstream["status"],
                "financial_facts": upstream["counts"]["financial_facts"],
                "eligible_facts": upstream["counts"]["reconciled_eligible_facts"],
                "latest_fact_pit": upstream["final_pit"]["count"],
                "version_chain_links": upstream["counts"]["version_chain_links"],
                "fact_id_set_sha256": acceptance["upstream_fact_id_set_sha256"],
                "stage2d_combined_counts": upstream["upstream"]["combined_counts"],
                "stage2d_combined_result_id_set_sha256": COMBINED_70_RESULT_ID_SET_SHA256,
                "stage2d_prior_result_id_set_sha256": EXPECTED_COUNTS_REF_DIGEST,
                "stage2d_prior_result_semantic_sha256": PRIOR_63_SEMANTIC_SHA256,
                "stage2d_upstream_fact_id_set_sha256": UPSTREAM_180_FACT_ID_SET_SHA256,
                "sha256_before": upstream_hash_before,
                "sha256_after": upstream_hash_after,
            },
            combined_counts=acceptance["combined_counts"],
            roa_counts=acceptance["roa_counts"],
            latest_metric_count=len(acceptance["latest"]),
            latest_computed=sum(item["status"] == "computed" for item in acceptance["latest"]),
            metric_pit_counts=[item["count"] for item in acceptance["snapshots"]],
            metric_pit_computed_counts=[item["computed"] for item in acceptance["snapshots"]],
            metric_pit_insufficient_history_counts=[
                item["insufficient_history"] for item in acceptance["snapshots"]
            ],
            roa_latest_values=acceptance["roa_latest_values"],
            new_metric_result_ids=sorted(item.metric_result_id for item in roa["results"]),
            new_metric_version_links=acceptance["transitions"],
            roa_2024=acceptance["roa_2024"],
            default_db_sha256_before=default_before,
            default_db_sha256_after=default_after,
            completed_at=completed_at,
        )
    except Exception as exc:
        manifest.update(
            error_type=type(exc).__name__,
            error=str(exc),
            completed_at=datetime.now().astimezone().isoformat(),
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
        "# ROA metric extension\n\n"
        f"- run_id: `{run_id}`\n"
        f"- status: **{manifest['status']}**\n"
        "- offline: `true`\n"
        "- ROIC computation: `not performed`\n"
        "- scoring: `not implemented`\n"
    )
    if "combined_counts" in manifest:
        summary += "\n## Combined counts\n\n" + "\n".join(
            f"- {key}: {value}" for key, value in manifest["combined_counts"].items()
        ) + "\n\n## ROA counts\n\n" + "\n".join(
            f"- {key}: {value}" for key, value in manifest["roa_counts"].items()
        ) + "\n"
    if "error" in manifest:
        summary += f"\n## Failure\n\n{manifest['error']}\n"
    (run_dir / "acceptance_summary.md").write_text(summary, encoding="utf-8")
    return {**manifest, "run_directory": run_dir}


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", required=True)
    parser.add_argument("--run-id")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    result = run_roa_metric_extension(args.output_root, run_id=args.run_id)
    print(json.dumps(_jsonable(result), ensure_ascii=False, indent=2))
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
