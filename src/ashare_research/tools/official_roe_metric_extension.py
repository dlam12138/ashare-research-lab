"""Build the offline 2021-2025 ROE metric extension.

Stage 2D-D computes the transparent ``return_on_average_equity_attributable_to_parent``
metric from the Stage 2D-B 180-fact foundation: the duration
``net_profit_attributable_to_parent`` numerator (Stage 2C coverage) divided by the
arithmetic mean of the opening and closing instant
``equity_attributable_to_parent`` facts (Stage 2D-B coverage).  It rebuilds and
freezes the upstream 180-fact set and the prior 63 metric results, then replays
the Fact PIT at the five annual-report availability dates to emit the ROE
versions -- including two real restatement chains (FY2022, FY2023) that arise
naturally from the underlying profit and equity restatements.

It never accesses the network, a PDF, or the shared cache, never opens the
default research database, and never computes ROA, ROIC, or a score.  ROA stays
blocked because no consolidated ``net_profit`` numerator fact is covered yet.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import tempfile
from dataclasses import asdict
from datetime import date, datetime, timedelta
from decimal import Decimal
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
from ashare_research.metrics.engine import MetricEngine
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

ROOT = Path(__file__).resolve().parents[3]
CONTRACT = "roe_metric_extension_v1"
YEARS = (2021, 2022, 2023, 2024, 2025)
ROE_METRIC_ID = "return_on_average_equity_attributable_to_parent"
NUMERATOR_CONCEPT = "net_profit_attributable_to_parent"
DENOMINATOR_CONCEPT = "equity_attributable_to_parent"
# Annual report availability dates (max of company/exchange announcement) from
# the Stage 2D-B foundation.  The instant equity facts and the duration profit
# facts share exactly these five availability dates.
ANNUAL_REPORT_DATES = [
    "2022-04-01",
    "2023-03-30",
    "2024-03-26",
    "2025-03-31",
    "2026-03-30",
]
# ROE-only expected counts (R = 2 restatement chains).
ROE_EXPECTED = {
    "definitions": 1,
    "result_versions": 7,
    "computed_versions": 7,
    "insufficient_history_versions": 0,
    "version_links": 2,
    "lineage_rows": 21,
    "final_latest": 5,
}
# Combined (prior 10 definitions + ROE) expected counts.
COMBINED_EXPECTED = {
    "definitions": 11,
    "results": 70,
    "computed": 66,
    "insufficient_history": 4,
    "version_links": 15,
    "lineage": 143,
    "final_latest": 55,
    "final_computed": 51,
}
# Metric PIT replay counts (combined) at [day-before-first, *five dates].
PIT_LATEST = [0, 11, 22, 33, 44, 55]
PIT_COMPUTED = [0, 7, 18, 29, 40, 51]
PIT_INSUFFICIENT = [0, 4, 4, 4, 4, 4]
# Accepted ROE values (computed from facts, not hard-coded in production).
ROE_VALUES = {
    2021: Decimal("0.074346290551"),
    2022: Decimal("0.113122466185"),
    2023: Decimal("0.114591833946"),
    2024: Decimal("0.111016131033"),
    2025: Decimal("0.101438303339"),
}
ROE_TRANSITIONAL = {
    (2022, 1): Decimal("0.113446882745"),
    (2023, 1): Decimal("0.114600416175"),
}


class ROEMetricExtensionError(ValueError):
    """A deterministic Stage 2D-D acceptance gate failed."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ROEMetricExtensionError(message)


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
        ensure_ascii=False, sort_keys=True, separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode()).hexdigest()


def build_run_id(now: datetime | None = None) -> str:
    timestamp = (now or datetime.now()).strftime("%Y%m%d_%H%M%S_%f")
    return f"roe_metric_extension_601857_SH_2021_2025_{timestamp}"


def _roe_review_status(fiscal_year: int) -> str:
    """Derive the ROE revision_review_status from committed review evidence.

    The 2021/2022/2023 denominator and profit reviews live in the
    ``roe_roa_denominators_{y}_reviewed_by_{y+1}.json`` and
    ``{y}_reviewed_by_{y+1}_annual.json`` files.  2024's ROE denominator and
    profit are unchanged; 2025 is not yet reviewable.
    """
    if fiscal_year == 2025:
        return "not_yet_reviewable"
    if fiscal_year == 2024:
        return "reviewed_unchanged"
    denominators = _load_json(
        REVIEW_DIR / f"roe_roa_denominators_{fiscal_year}_reviewed_by_"
        f"{fiscal_year + 1}.json"
    )
    annual = _load_json(
        REVIEW_DIR / f"{fiscal_year}_reviewed_by_{fiscal_year + 1}_annual.json"
    )
    denom_changed = any(
        item["concept_id"] == DENOMINATOR_CONCEPT and item["changed"]
        for item in denominators["concepts"]
    )
    profit_changed = any(
        item["concept_id"] == NUMERATOR_CONCEPT and item["changed"]
        for item in annual["concepts"]
    )
    return "reviewed_changed" if (denom_changed or profit_changed) else (
        "reviewed_unchanged"
    )


def _changed(old: MetricResult, candidate: MetricResult) -> bool:
    return (
        old.value != candidate.value
        or old.status != candidate.status
        or old.input_fact_ids != candidate.input_fact_ids
    )


def build_roe_metric_versions(
    as_of: AsOfQuery,
    available_dates: list[str],
    *,
    created_at: str,
) -> dict[str, Any]:
    """Replay the Fact PIT and emit only semantically distinct ROE versions."""
    definition = CapitalReturnMetricDefinitionRegistry.get(ROE_METRIC_ID)
    latest_by_key: dict[tuple[str, int, str, str], MetricResult] = {}
    results: list[MetricResult] = []
    lineage: list[MetricLineage] = []
    for as_of_date in available_dates:
        numerator_frame = as_of.get_latest_available(
            SYMBOL, as_of_date, [NUMERATOR_CONCEPT]
        )
        denominator_frame = as_of.get_latest_available(
            SYMBOL, as_of_date, [DENOMINATOR_CONCEPT]
        )
        numerators = {
            int(str(row["period_end"])[:4]): row
            for row in numerator_frame.to_dict("records")
        }
        denominators = {
            int(str(row["period_end"])[:4]): row
            for row in denominator_frame.to_dict("records")
        }
        for fiscal_year in sorted(numerators):
            if fiscal_year not in denominators:
                continue
            closing_year = fiscal_year
            opening_year = fiscal_year - 1
            numerator = numerators[closing_year]
            closing = denominators.get(closing_year)
            opening = denominators.get(opening_year)
            review_status = _roe_review_status(fiscal_year)
            arguments = {
                "definition": definition,
                "symbol": SYMBOL,
                "fiscal_year": fiscal_year,
                "primary_fact": numerator,
                "secondary_fact": opening,
                "tertiary_fact": closing,
                "revision_review_status": review_status,
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


def _acceptance(
    repo: MetricRepository,
    *,
    roe: dict[str, Any],
    stage2a: dict[str, Any],
    cashflow: dict[str, Any],
    earnings: dict[str, Any],
    available_dates: list[str],
    upstream_fact_ids: list[str],
    as_of: AsOfQuery,
) -> dict[str, Any]:
    conn = repo.connect()
    combined_counts = {
        "definitions": conn.execute(
            "SELECT COUNT(*) FROM metric_definitions"
        ).fetchone()[0],
        "results": conn.execute(
            "SELECT COUNT(*) FROM metric_results"
        ).fetchone()[0],
        "computed": conn.execute(
            "SELECT COUNT(*) FROM metric_results WHERE status='computed'"
        ).fetchone()[0],
        "insufficient_history": conn.execute(
            "SELECT COUNT(*) FROM metric_results "
            "WHERE status='insufficient_history'"
        ).fetchone()[0],
        "version_links": conn.execute(
            "SELECT COUNT(*) FROM metric_results "
            "WHERE supersedes_metric_result_id <> ''"
        ).fetchone()[0],
        "lineage": conn.execute(
            "SELECT COUNT(*) FROM metric_lineage"
        ).fetchone()[0],
    }
    latest = _normalize_rows(repo.latest_results(available_dates[-1]))
    combined_counts["final_latest"] = len(latest)
    combined_counts["final_computed"] = sum(
        item["status"] == "computed" for item in latest
    )
    _require(
        combined_counts == COMBINED_EXPECTED,
        f"combined metric counts differ: {combined_counts}",
    )

    # ROE-only counts.
    roe_results = roe["results"]
    roe_counts = {
        "definitions": len(CapitalReturnMetricDefinitionRegistry.list_all()),
        "result_versions": len(roe_results),
        "computed_versions": sum(
            str(item.status) == "computed" for item in roe_results
        ),
        "insufficient_history_versions": sum(
            str(item.status) == "insufficient_history" for item in roe_results
        ),
        "version_links": sum(
            bool(item.supersedes_metric_result_id) for item in roe_results
        ),
        "lineage_rows": len(roe["lineage"]),
        "final_latest": len(roe["latest"]),
    }
    _require(
        roe_counts == ROE_EXPECTED,
        f"ROE metric counts differ: {roe_counts}",
    )

    # Metric PIT replay (combined) at six snapshot dates.
    first = date.fromisoformat(available_dates[0])
    snapshot_dates = [(first - timedelta(days=1)).isoformat(), *available_dates]
    snapshots = []
    for as_of_date in snapshot_dates:
        rows = _normalize_rows(repo.latest_results(as_of_date))
        snapshots.append({
            "as_of_date": as_of_date,
            "count": len(rows),
            "computed": sum(
                row["status"] == "computed" for row in rows
            ),
            "insufficient_history": sum(
                row["status"] == "insufficient_history" for row in rows
            ),
        })
    _require(
        [item["count"] for item in snapshots] == PIT_LATEST,
        f"Metric PIT latest counts differ: "
        f"{[item['count'] for item in snapshots]}",
    )
    _require(
        [item["computed"] for item in snapshots] == PIT_COMPUTED,
        f"Metric PIT computed counts differ: "
        f"{[item['computed'] for item in snapshots]}",
    )
    _require(
        [item["insufficient_history"] for item in snapshots] == PIT_INSUFFICIENT,
        f"Metric PIT insufficient counts differ: "
        f"{[item['insufficient_history'] for item in snapshots]}",
    )

    # Prior 63 result ID set + semantics unchanged.
    prior_results = [
        *stage2a["results"], *cashflow["results"], *earnings["results"]
    ]
    prior_ids = [item.metric_result_id for item in prior_results]
    _require(
        len(prior_ids) == 63
        and _id_set_digest(prior_ids) == EXPECTED_COUNTS_REF_DIGEST,
        "prior 63 Metric Result ID set changed",
    )
    _require(
        _result_semantic_digest(prior_results) == PRIOR_63_SEMANTIC_SHA256,
        "prior 63 Metric Result semantics changed",
    )

    # Accepted ROE values.
    roe_by_fy_version = {
        (item.fiscal_year, item.result_version): item
        for item in roe_results
    }
    for fiscal_year, expected in ROE_VALUES.items():
        latest_roe = max(
            (item for item in roe_results if item.fiscal_year == fiscal_year),
            key=lambda item: item.result_version,
        )
        _require(
            latest_roe.status == "computed"
            and latest_roe.value == expected,
            f"ROE {fiscal_year} value differs: {latest_roe.value}",
        )
    for (fiscal_year, version), expected in ROE_TRANSITIONAL.items():
        item = roe_by_fy_version.get((fiscal_year, version))
        _require(
            item is not None
            and item.status == "computed"
            and item.value == expected,
            f"ROE {fiscal_year} v{version} transitional value differs",
        )

    # Two real restatement chains (FY2022, FY2023).
    versioned = [item for item in roe_results if item.result_version > 1]
    _require(
        {(item.fiscal_year, item.metric_id) for item in versioned}
        == {(2022, ROE_METRIC_ID), (2023, ROE_METRIC_ID)},
        "ROE version-chain keys differ",
    )
    by_id = {item.metric_result_id: item for item in roe_results}
    transitions = []
    for after in versioned:
        before = by_id[after.supersedes_metric_result_id]
        _require(
            before.result_version == 1
            and after.result_version == 2
            and before.input_fact_ids != after.input_fact_ids
            and before.available_at < after.available_at,
            f"ROE {after.fiscal_year} chain differs",
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
        [t["fiscal_year"] for t in transitions] == [2022, 2023],
        "ROE transition order differs",
    )

    # FY2024 v1 must use 2023 equity v2 directly (no fake version).
    roe_2024 = next(
        item for item in roe_results
        if item.fiscal_year == 2024 and item.result_version == 1
    )
    final_equity = as_of.get_latest_available(
        SYMBOL, available_dates[-1], [DENOMINATOR_CONCEPT]
    )
    eq_2023 = final_equity[
        final_equity["period_end"] == "2023-12-31"
    ].iloc[0]
    _require(
        int(eq_2023["fact_version"]) == 2
        and roe_2024.input_fact_ids[1] == str(eq_2023["fact_id"]),
        "ROE 2024 opening did not use 2023 equity v2",
    )

    # FY2025 not_yet_reviewable.
    _require(
        all(
            item.revision_review_status == "not_yet_reviewable"
            for item in roe["latest"] if item.fiscal_year == 2025
        ),
        "ROE 2025 review status differs",
    )
    # No ROA / no scoring.
    _require(
        all(
            item.metric_id != "return_on_average_total_assets"
            for item in roe_results
        ),
        "ROA was unexpectedly computed",
    )

    _require(
        len(upstream_fact_ids) == 180
        and _id_set_digest(upstream_fact_ids) == UPSTREAM_180_FACT_ID_SET_SHA256,
        "upstream 180 Fact IDs changed",
    )
    return {
        "combined_counts": combined_counts,
        "roe_counts": roe_counts,
        "snapshots": snapshots,
        "latest": latest,
        "transitions": transitions,
        "roe_2024": asdict(roe_2024),
        "prior_result_id_set_sha256": _id_set_digest(prior_ids),
        "prior_result_semantic_sha256": _result_semantic_digest(prior_results),
        "upstream_fact_id_set_sha256": _id_set_digest(upstream_fact_ids),
    }


# Prior 63 result ID-set digest (frozen Stage 2C-D / 2D-B baseline).  Both the
# ID-set and the semantic digests are derived from the 63 prior results rebuilt
# from the 180-fact foundation; this stage must leave them unchanged.
EXPECTED_COUNTS_REF_DIGEST = (
    "34edbbc3a4d3f6533c6d29911fef03c4d07772c68e6649f414ed0b567038e526"
)
PRIOR_63_SEMANTIC_SHA256 = (
    "e988394fd21570ae84807fca7400393f2666aa357ddb4ad1b7c5735c7c2ba053"
)
UPSTREAM_180_FACT_ID_SET_SHA256 = (
    "2bd5b2d20ec7992a07b66238fff86ab0fb91f881c5f7cd7f0b5d68b5bde6946c"
)


def run_roe_metric_extension(
    output_root: str | Path, *, run_id: str | None = None
) -> dict[str, Any]:
    """Execute the complete offline Stage 2D-D acceptance."""
    run_id = run_id or build_run_id()
    run_dir = (
        Path(output_root)
        / "value_assessment"
        / SYMBOL
        / "roe_metric_extension"
        / "2021_2025"
        / run_id
    )
    run_dir.mkdir(parents=True, exist_ok=False)
    upstream_dir = run_dir / "upstream_roe_roa_denominators"
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
        "investment_advice": "not_produced",
        "roa_computation": "blocked",
        "started_at": started_at,
    }
    metrics_repo = None
    upstream_store = None
    try:
        default_before = _sha256(DEFAULT_DB)
        with tempfile.TemporaryDirectory(prefix="m2_stage2dd_") as temp_root:
            upstream = run_denominator_foundation(
                temp_root, run_id="upstream"
            )
            _require(
                upstream["status"] == "passed",
                "Stage 2D-B upstream failed",
            )
            shutil.move(str(upstream["run_directory"]), str(upstream_dir))
        _require(
            upstream["counts"]["financial_facts"] == 180
            and upstream["counts"]["reconciled_eligible_facts"] == 60
            and upstream["final_pit"]["count"] == 47
            and upstream["counts"]["version_chain_links"] == 39,
            "Stage 2D-B upstream counts differ",
        )
        upstream_db = upstream_dir / "roe_roa_denominators.duckdb"
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
            as_of, available_dates, _earnings_review_statuses(),
            created_at=created_at,
        )
        roe = build_roe_metric_versions(
            as_of, available_dates, created_at=created_at
        )
        definitions = [
            *MetricDefinitionRegistry.list_all(),
            *CashFlowMetricDefinitionRegistry.list_all(),
            *EarningsQualityMetricDefinitionRegistry.list_all(),
            *CapitalReturnMetricDefinitionRegistry.list_all(),
        ]
        results = [
            *stage2a["results"], *cashflow["results"],
            *earnings["results"], *roe["results"],
        ]
        lineage = [
            *stage2a["lineage"], *cashflow["lineage"],
            *earnings["lineage"], *roe["lineage"],
        ]

        metrics_repo = MetricRepository(str(metrics_path))
        metrics_repo.ensure_schema(applied_at=created_at)
        completed_at = datetime.now().astimezone().isoformat()
        with metrics_repo.transaction() as metrics_conn:
            metrics_repo.store_definitions(definitions, conn=metrics_conn)
            metrics_repo.store_results(results, lineage, conn=metrics_conn)
            metrics_repo.store_run(
                run_id, status="passed", started_at=started_at,
                completed_at=completed_at, result_count=len(results),
                conn=metrics_conn,
            )
        acceptance = _acceptance(
            metrics_repo, roe=roe, stage2a=stage2a, cashflow=cashflow,
            earnings=earnings, available_dates=available_dates,
            upstream_fact_ids=upstream_fact_ids, as_of=as_of,
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

        _write_json(
            run_dir / "metric_definitions.json",
            [asdict(item) for item in definitions],
        )
        _write_json(
            run_dir / "metric_result_versions.json",
            [asdict(item) for item in results],
        )
        _write_json(
            run_dir / "latest_metric_snapshot.json", acceptance["latest"]
        )
        _write_json(
            run_dir / "metric_pit_snapshots.json", acceptance["snapshots"]
        )
        _write_json(
            run_dir / "roe_metric_transitions.json",
            acceptance["transitions"],
        )
        _write_json(
            run_dir / "metric_lineage.json",
            [asdict(item) for item in lineage],
        )
        methodology = _load_json(
            ROOT / "config/value_evaluation_methodology_capital_return_v1.json"
        )
        _write_json(run_dir / "methodology_extension.json", methodology)
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
                "sha256_before": upstream_hash_before,
                "sha256_after": upstream_hash_after,
            },
            combined_counts=acceptance["combined_counts"],
            roe_counts=acceptance["roe_counts"],
            latest_metric_count=len(acceptance["latest"]),
            latest_computed=sum(
                item["status"] == "computed" for item in acceptance["latest"]
            ),
            metric_pit_counts=[item["count"] for item in acceptance["snapshots"]],
            metric_pit_computed_counts=[
                item["computed"] for item in acceptance["snapshots"]
            ],
            metric_pit_insufficient_history_counts=[
                item["insufficient_history"] for item in acceptance["snapshots"]
            ],
            prior_result_id_set_sha256=(
                acceptance["prior_result_id_set_sha256"]
            ),
            prior_result_semantic_sha256=(
                acceptance["prior_result_semantic_sha256"]
            ),
            new_metric_result_ids=sorted(
                item.metric_result_id for item in roe["results"]
            ),
            new_metric_version_links=acceptance["transitions"],
            roe_2024=acceptance["roe_2024"],
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
        "# ROE metric extension\n\n"
        f"- run_id: `{run_id}`\n"
        f"- status: **{manifest['status']}**\n"
        "- offline: `true`\n"
        "- scoring: `not implemented`\n"
        "- roa_computation: `blocked`\n"
    )
    if "combined_counts" in manifest:
        summary += "\n## Combined counts\n\n" + "\n".join(
            f"- {k}: {v}" for k, v in manifest["combined_counts"].items()
        ) + "\n\n## ROE counts\n\n" + "\n".join(
            f"- {k}: {v}" for k, v in manifest["roe_counts"].items()
        ) + "\n"
    if "error" in manifest:
        summary += f"\n## Failure\n\n{manifest['error']}\n"
    (run_dir / "acceptance_summary.md").write_text(summary, encoding="utf-8")
    return {**manifest, "run_directory": run_dir}


# Imported here (after the function bodies) to keep the module importable even
# before the 2D-B foundation is available at module load time.
from ashare_research.tools.official_roe_roa_denominator_foundation import (  # noqa: E402
    run_denominator_foundation,
)


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", required=True)
    parser.add_argument("--run-id")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    result = run_roe_metric_extension(args.output_root, run_id=args.run_id)
    print(json.dumps(_jsonable(result), ensure_ascii=False, indent=2))
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
