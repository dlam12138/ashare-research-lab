"""Build the offline 2021-2025 earnings-quality metric extension."""

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
    STAGE2A_METRIC_RESULT_ID_SET_SHA256,
    build_cashflow_metric_versions,
)
from ashare_research.tools.official_cashflow_metric_extension import (
    _review_statuses as cashflow_review_statuses,
)
from ashare_research.tools.official_earnings_quality_fact_foundation import (
    DEFAULT_DB,
    DEFAULT_DB_SHA256,
    REVIEW_DIR,
    SYMBOL,
    run_earnings_quality_foundation,
)
from ashare_research.tools.official_fact_metric_foundation import (
    build_metric_versions,
)

ROOT = Path(__file__).resolve().parents[3]
CONTRACT = "earnings_quality_metric_extension_v1"
YEARS = (2021, 2022, 2023, 2024, 2025)
EARNINGS_CONCEPTS = frozenset(
    {
        "revenue",
        "net_profit_excluding_non_recurring",
        "operating_cost",
        "operating_profit",
    }
)
CAPEX_CONCEPT = "cash_paid_for_fixed_assets"
ORIGINAL_38_RESULT_ID_SET_SHA256 = (
    "730484f4abe54298cc53ecdc44d3079c0d2e064a6981047a0b413f6466faa5fa"
)
ORIGINAL_38_RESULT_SEMANTIC_SHA256 = (
    "f665e33775c40a1b8e092c1345978f5f8fd5650cec90c5a87a931dfba2726890"
)
UPSTREAM_132_FACT_ID_SET_SHA256 = (
    "1e5267022b8062acf96fb413f09ecfc737c706b786c9f02a0b1dc3834fab604d"
)
UPSTREAM_84_FACT_ID_SET_SHA256 = (
    "020835fc129658059f680a3a854aa59b3ace199704c6cd70c3815dca29e29b87"
)
EXPECTED_COUNTS = {
    "metric_definitions": 10,
    "metric_result_versions": 63,
    "computed_result_versions": 59,
    "insufficient_history_result_versions": 4,
    "metric_version_links": 13,
    "metric_lineage_rows": 122,
}
NEW_EXPECTED_COUNTS = {
    "definitions": 4,
    "result_versions": 25,
    "computed_versions": 24,
    "insufficient_history_versions": 1,
    "version_links": 5,
    "lineage_rows": 49,
    "final_latest": 20,
    "final_computed": 19,
    "final_insufficient_history": 1,
}
GAP_CLOSED = (
    "扣非归母净利润事实覆盖",
    "毛利润",
    "毛利率",
    "营业利润率",
)
GAP_OPEN = (
    "非经常性损益独立 Fact",
    "ROE / ROA / ROIC",
    "财务安全",
    "分红与回购",
    "估值",
    "治理与风险否决项",
    "行业与同行基准",
)


class EarningsQualityMetricExtensionError(ValueError):
    """A deterministic Stage 2C-D acceptance gate failed."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise EarningsQualityMetricExtensionError(message)


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
    value = json.loads(path.read_text(encoding="utf-8"))
    _require(isinstance(value, dict), f"{path.name}: JSON object required")
    return value


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _id_set_digest(ids: list[str]) -> str:
    payload = json.dumps(sorted(ids), separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()


def _result_semantic_digest(results: list[MetricResult]) -> str:
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
                field: (
                    str(data[field])
                    if field in {"status", "value"} and data[field] is not None
                    else data[field]
                )
                for field in fields
            }
        )
    payload = json.dumps(
        sorted(rows, key=lambda item: item["metric_result_id"]),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode()).hexdigest()


def build_run_id(now: datetime | None = None) -> str:
    timestamp = (now or datetime.now()).strftime("%Y%m%d_%H%M%S_%f")
    return (
        "earnings_quality_metric_extension_601857_SH_2021_2025_"
        f"{timestamp}"
    )


def _evidence_paths(prefix: str) -> list[Path]:
    return [
        REVIEW_DIR / f"{prefix}{year}_reviewed_by_{year + 1}.json"
        for year in YEARS[:-1]
    ]


def _annual_review_paths() -> list[Path]:
    return [
        REVIEW_DIR / f"{year}_reviewed_by_{year + 1}_annual.json"
        for year in YEARS[:-1]
    ]


def _earnings_review_statuses() -> dict[int, dict[str, bool]]:
    reviewed: dict[int, dict[str, bool]] = {}
    for path in _evidence_paths("earnings_quality_"):
        evidence = _load_json(path)
        year = int(evidence["target_fiscal_year"])
        reviewed[year] = {
            str(item["concept_id"]): bool(item["changed"])
            for item in evidence["concepts"]
        }
    _require(set(reviewed) == set(YEARS[:-1]), "earnings review years differ")
    for year, concepts in reviewed.items():
        _require(
            set(concepts)
            == {
                "net_profit_excluding_non_recurring",
                "operating_cost",
                "operating_profit",
            },
            f"{year}: earnings review concepts differ",
        )
    return reviewed


def _earnings_review_status(
    fiscal_year: int,
    definition,
    reviewed: dict[int, dict[str, bool]],
) -> str:
    if fiscal_year == YEARS[-1]:
        return "not_yet_reviewable"
    concept_years = [
        (fiscal_year, definition.input_concept_ids[0]),
        (fiscal_year, definition.input_concept_ids[1]),
    ]
    if definition.formula == "(current / prior) - 1":
        concept_years[1] = (fiscal_year - 1, definition.input_concept_ids[1])
    changed = []
    for year, concept in concept_years:
        if concept == "revenue":
            annual = _load_json(
                REVIEW_DIR / f"{year}_reviewed_by_{year + 1}_annual.json"
            )
            flags = {
                str(item["concept_id"]): bool(item["changed"])
                for item in annual["concepts"]
            }
            changed.append(flags[concept])
        elif year in reviewed:
            changed.append(reviewed[year][concept])
    return "reviewed_changed" if any(changed) else "reviewed_unchanged"


def _snapshot_facts(frame) -> dict[int, dict[str, dict[str, Any]]]:
    facts: dict[int, dict[str, dict[str, Any]]] = {}
    for row in frame.to_dict("records"):
        year = int(str(row["period_end"])[:4])
        concept = str(row["concept_id"])
        _require(concept not in facts.setdefault(year, {}), "duplicate PIT fact")
        facts[year][concept] = row
    for year, by_concept in facts.items():
        _require(
            set(by_concept) == EARNINGS_CONCEPTS,
            f"{year}: earnings PIT concepts differ",
        )
        _require(
            all(
                item["source_tier"] == "reconciled_derived"
                and bool(item["eligible_for_metrics"])
                for item in by_concept.values()
            ),
            "earnings metric input is raw or ineligible",
        )
    return facts


def _changed(old: MetricResult, candidate: MetricResult) -> bool:
    return (
        old.value != candidate.value
        or old.status != candidate.status
        or old.input_fact_ids != candidate.input_fact_ids
    )


def build_earnings_metric_versions(
    as_of: AsOfQuery,
    available_dates: list[str],
    reviewed: dict[int, dict[str, bool]],
    *,
    created_at: str,
) -> dict[str, Any]:
    """Replay Fact PIT and emit only semantically distinct new versions."""
    latest_by_key: dict[tuple[str, int, str, str], MetricResult] = {}
    results: list[MetricResult] = []
    lineage: list[MetricLineage] = []
    for as_of_date in available_dates:
        frame = as_of.get_latest_available(
            SYMBOL, as_of_date, sorted(EARNINGS_CONCEPTS)
        )
        facts = _snapshot_facts(frame)
        for fiscal_year in sorted(facts):
            for definition in EarningsQualityMetricDefinitionRegistry.list_all():
                primary = facts[fiscal_year][definition.input_concept_ids[0]]
                if definition.formula == "(current / prior) - 1":
                    secondary = facts.get(fiscal_year - 1, {}).get(
                        definition.input_concept_ids[1]
                    )
                else:
                    secondary = facts[fiscal_year][definition.input_concept_ids[1]]
                review_status = _earnings_review_status(
                    fiscal_year, definition, reviewed
                )
                arguments = {
                    "definition": definition,
                    "symbol": SYMBOL,
                    "fiscal_year": fiscal_year,
                    "primary_fact": primary,
                    "secondary_fact": secondary,
                    "missing_prior_is_history": (
                        fiscal_year == YEARS[0]
                        and definition.formula == "(current / prior) - 1"
                    ),
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
    stage2a: dict[str, Any],
    cashflow: dict[str, Any],
    earnings: dict[str, Any],
    available_dates: list[str],
    upstream_fact_ids: list[str],
    as_of: AsOfQuery,
) -> dict[str, Any]:
    conn = repo.connect()
    counts = {
        "metric_definitions": conn.execute(
            "SELECT COUNT(*) FROM metric_definitions"
        ).fetchone()[0],
        "metric_result_versions": conn.execute(
            "SELECT COUNT(*) FROM metric_results"
        ).fetchone()[0],
        "computed_result_versions": conn.execute(
            "SELECT COUNT(*) FROM metric_results WHERE status='computed'"
        ).fetchone()[0],
        "insufficient_history_result_versions": conn.execute(
            "SELECT COUNT(*) FROM metric_results "
            "WHERE status='insufficient_history'"
        ).fetchone()[0],
        "metric_version_links": conn.execute(
            "SELECT COUNT(*) FROM metric_results "
            "WHERE supersedes_metric_result_id <> ''"
        ).fetchone()[0],
        "metric_lineage_rows": conn.execute(
            "SELECT COUNT(*) FROM metric_lineage"
        ).fetchone()[0],
    }
    _require(counts == EXPECTED_COUNTS, f"combined metric counts differ: {counts}")

    new_counts = {
        "definitions": len(EarningsQualityMetricDefinitionRegistry.list_all()),
        "result_versions": len(earnings["results"]),
        "computed_versions": sum(
            str(item.status) == "computed" for item in earnings["results"]
        ),
        "insufficient_history_versions": sum(
            str(item.status) == "insufficient_history"
            for item in earnings["results"]
        ),
        "version_links": sum(
            bool(item.supersedes_metric_result_id) for item in earnings["results"]
        ),
        "lineage_rows": len(earnings["lineage"]),
        "final_latest": len(earnings["latest"]),
        "final_computed": sum(
            str(item.status) == "computed" for item in earnings["latest"]
        ),
        "final_insufficient_history": sum(
            str(item.status) == "insufficient_history"
            for item in earnings["latest"]
        ),
    }
    _require(
        new_counts == NEW_EXPECTED_COUNTS,
        f"earnings metric counts differ: {new_counts}",
    )

    first = date.fromisoformat(available_dates[0])
    snapshot_dates = [(first - timedelta(days=1)).isoformat(), *available_dates]
    snapshots = []
    for as_of_date in snapshot_dates:
        rows = _normalize_rows(repo.latest_results(as_of_date))
        snapshots.append(
            {
                "as_of_date": as_of_date,
                "count": len(rows),
                "computed": sum(row["status"] == "computed" for row in rows),
                "insufficient_history": sum(
                    row["status"] == "insufficient_history" for row in rows
                ),
                "metric_result_ids": [
                    row["metric_result_id"] for row in rows
                ],
            }
        )
    _require(
        [item["count"] for item in snapshots] == [0, 10, 20, 30, 40, 50],
        "Metric PIT latest counts differ",
    )
    _require(
        [item["computed"] for item in snapshots] == [0, 6, 16, 26, 36, 46],
        "Metric PIT computed counts differ",
    )
    _require(
        [item["insufficient_history"] for item in snapshots]
        == [0, 4, 4, 4, 4, 4],
        "Metric PIT insufficient counts differ",
    )

    old_results = [*stage2a["results"], *cashflow["results"]]
    old_ids = [item.metric_result_id for item in old_results]
    _require(
        len(old_ids) == 38
        and _id_set_digest(old_ids) == ORIGINAL_38_RESULT_ID_SET_SHA256,
        "original 38 Metric Result IDs changed",
    )
    old_semantic_digest = _result_semantic_digest(old_results)
    _require(
        old_semantic_digest == ORIGINAL_38_RESULT_SEMANTIC_SHA256,
        "original 38 Metric Result semantics changed",
    )
    _require(
        len(stage2a["results"]) == 26
        and _id_set_digest(
            [item.metric_result_id for item in stage2a["results"]]
        )
        == STAGE2A_METRIC_RESULT_ID_SET_SHA256,
        "Stage 2A result identities changed",
    )

    versioned = [
        item for item in earnings["results"] if item.result_version > 1
    ]
    expected_keys = {
        (2022, "net_profit_excluding_non_recurring_yoy"),
        (2023, "net_profit_excluding_non_recurring_yoy"),
        (2023, "gross_profit"),
        (2023, "gross_margin"),
        (2023, "operating_profit_margin"),
    }
    _require(
        {(item.fiscal_year, item.metric_id) for item in versioned}
        == expected_keys,
        "earnings metric version-chain keys differ",
    )
    by_id = {item.metric_result_id: item for item in earnings["results"]}
    transitions = []
    for after in versioned:
        before = by_id[after.supersedes_metric_result_id]
        _require(
            before.result_version == 1
            and after.result_version == 2
            and before.input_fact_ids != after.input_fact_ids
            and before.available_at < after.available_at,
            f"{after.metric_id}/{after.fiscal_year}: chain differs",
        )
        transitions.append(
            {
                "fiscal_year": after.fiscal_year,
                "metric_id": after.metric_id,
                "before": asdict(before),
                "after": asdict(after),
                "pit_before_date": (
                    date.fromisoformat(after.available_at)
                    - timedelta(days=1)
                ).isoformat(),
                "pit_switch_date": after.available_at,
            }
        )

    facts_final = _snapshot_facts(
        as_of.get_latest_available(
            SYMBOL, available_dates[-1], sorted(EARNINGS_CONCEPTS)
        )
    )
    yoy_2024 = next(
        item
        for item in earnings["results"]
        if item.fiscal_year == 2024
        and item.metric_id == "net_profit_excluding_non_recurring_yoy"
    )
    prior_2023 = facts_final[2023]["net_profit_excluding_non_recurring"]
    _require(
        yoy_2024.result_version == 1
        and int(prior_2023["fact_version"]) == 2
        and yoy_2024.input_fact_ids[1] == prior_2023["fact_id"],
        "2024 adjusted-profit YoY did not start with 2023 v2",
    )
    _require(
        all(
            item.revision_review_status == "not_yet_reviewable"
            for item in earnings["latest"]
            if item.fiscal_year == 2025
        ),
        "2025 earnings review status differs",
    )
    _require(
        len(upstream_fact_ids) == 132
        and _id_set_digest(upstream_fact_ids)
        == UPSTREAM_132_FACT_ID_SET_SHA256,
        "upstream 132 Fact IDs changed",
    )
    latest = _normalize_rows(repo.latest_results(available_dates[-1]))
    return {
        "counts": counts,
        "new_counts": new_counts,
        "snapshots": snapshots,
        "latest": latest,
        "transitions": transitions,
        "yoy_2024": asdict(yoy_2024),
        "original_result_id_set_sha256": _id_set_digest(old_ids),
        "original_result_semantic_sha256": old_semantic_digest,
        "upstream_fact_id_set_sha256": _id_set_digest(upstream_fact_ids),
    }


def run_earnings_quality_metric_extension(
    output_root: str | Path, *, run_id: str | None = None
) -> dict[str, Any]:
    """Execute the complete offline Stage 2C-D acceptance."""
    run_id = run_id or build_run_id()
    run_dir = (
        Path(output_root)
        / "value_assessment"
        / SYMBOL
        / "earnings_quality_metric_extension"
        / "2021_2025"
        / run_id
    )
    run_dir.mkdir(parents=True, exist_ok=False)
    upstream_dir = run_dir / "upstream_earnings_quality"
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
        "upstream_directory": upstream_dir.name,
        "scoring": "not_implemented",
        "investment_advice": "not_produced",
        "started_at": started_at,
    }
    metrics_repo = None
    upstream_store = None
    try:
        default_before = _sha256(DEFAULT_DB)
        with tempfile.TemporaryDirectory(prefix="m2_stage2cd_") as temp_root:
            upstream = run_earnings_quality_foundation(
                temp_root, run_id="upstream"
            )
            _require(
                upstream["status"] == "passed",
                "Stage 2C-C.1 upstream failed",
            )
            shutil.move(str(upstream["run_directory"]), str(upstream_dir))
        _require(
            upstream["counts"]["financial_facts"] == 132
            and upstream["counts"]["eligible_for_metrics"] == 44
            and upstream["latest_pit_count"] == 35
            and upstream["counts"]["version_chain_links"] == 27,
            "Stage 2C-C.1 upstream counts differ",
        )
        _require(
            upstream["upstream_fact_id_set_sha256"]
            == UPSTREAM_84_FACT_ID_SET_SHA256,
            "original 84 Fact IDs changed",
        )
        upstream_db = upstream_dir / "earnings_quality.duckdb"
        upstream_hash_before = _sha256(upstream_db)
        upstream_store = DuckDBStore(str(upstream_db))
        upstream_repo = FactRepository(upstream_store)
        conn = upstream_store.connect()
        upstream_fact_ids = [
            row[0]
            for row in conn.execute(
                "SELECT fact_id FROM financial_facts ORDER BY fact_id"
            ).fetchall()
        ]
        _require(
            _id_set_digest(upstream_fact_ids) == UPSTREAM_132_FACT_ID_SET_SHA256,
            "Stage 2C-C.1 132 Fact IDs changed",
        )
        available_dates = [
            row[0]
            for row in conn.execute(
                """SELECT DISTINCT available_at FROM financial_facts
                   WHERE source_tier='reconciled_derived'
                     AND eligible_for_metrics=TRUE
                   ORDER BY available_at"""
            ).fetchall()
        ]
        _require(len(available_dates) == 5, "expected five Fact PIT dates")
        as_of = AsOfQuery(upstream_repo)
        created_at = datetime.now().astimezone().isoformat()

        annual_paths = _annual_review_paths()
        capex_paths = _evidence_paths("capex_cash_")
        reviewed = cashflow_review_statuses(annual_paths, capex_paths)
        stage2a_reviewed = {
            year: {
                concept: changed
                for concept, changed in concepts.items()
                if concept != CAPEX_CONCEPT
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
            as_of,
            available_dates,
            _earnings_review_statuses(),
            created_at=created_at,
        )
        definitions = [
            *MetricDefinitionRegistry.list_all(),
            *CashFlowMetricDefinitionRegistry.list_all(),
            *EarningsQualityMetricDefinitionRegistry.list_all(),
        ]
        results = [
            *stage2a["results"],
            *cashflow["results"],
            *earnings["results"],
        ]
        lineage = [
            *stage2a["lineage"],
            *cashflow["lineage"],
            *earnings["lineage"],
        ]

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
            stage2a=stage2a,
            cashflow=cashflow,
            earnings=earnings,
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
            run_dir / "earnings_quality_metric_transitions.json",
            acceptance["transitions"],
        )
        _write_json(
            run_dir / "metric_lineage.json",
            [asdict(item) for item in lineage],
        )
        methodology = _load_json(
            ROOT / "config/value_evaluation_methodology_earnings_quality_v1.json"
        )
        _write_json(run_dir / "methodology_extension.json", methodology)
        gap_inventory = {
            "closed": [
                {"name": item, "status": "closed"} for item in GAP_CLOSED
            ],
            "open": [
                {
                    "name": item,
                    "status": "missing",
                    "value": None,
                    "reason": "missing_fact_or_methodology_coverage",
                }
                for item in GAP_OPEN
            ],
        }
        _write_json(run_dir / "gap_inventory.json", gap_inventory)
        manifest.update(
            status="passed",
            transaction_committed=True,
            upstream={
                "status": upstream["status"],
                "financial_facts": upstream["counts"]["financial_facts"],
                "eligible_facts": upstream["counts"]["eligible_for_metrics"],
                "latest_fact_pit": upstream["latest_pit_count"],
                "version_chain_links": upstream["counts"]["version_chain_links"],
                "fact_id_set_sha256": acceptance["upstream_fact_id_set_sha256"],
                "sha256_before": upstream_hash_before,
                "sha256_after": upstream_hash_after,
            },
            counts=acceptance["counts"],
            new_earnings_counts=acceptance["new_counts"],
            latest_metric_count=len(acceptance["latest"]),
            latest_computed=sum(
                item["status"] == "computed" for item in acceptance["latest"]
            ),
            latest_insufficient_history=sum(
                item["status"] == "insufficient_history"
                for item in acceptance["latest"]
            ),
            metric_pit_counts=[
                item["count"] for item in acceptance["snapshots"]
            ],
            metric_pit_computed_counts=[
                item["computed"] for item in acceptance["snapshots"]
            ],
            metric_pit_insufficient_history_counts=[
                item["insufficient_history"] for item in acceptance["snapshots"]
            ],
            original_result_versions=38,
            original_result_id_set_sha256=(
                acceptance["original_result_id_set_sha256"]
            ),
            original_result_semantic_sha256=(
                acceptance["original_result_semantic_sha256"]
            ),
            new_metric_result_ids=sorted(
                item.metric_result_id for item in earnings["results"]
            ),
            new_metric_version_links=acceptance["transitions"],
            yoy_2024=acceptance["yoy_2024"],
            default_db_sha256_before=default_before,
            default_db_sha256_after=default_after,
            gap_inventory=gap_inventory,
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
        "# Earnings-quality metric extension\n\n"
        f"- run_id: `{run_id}`\n"
        f"- status: **{manifest['status']}**\n"
        "- offline: `true`\n"
        "- network_access: `false`\n"
        "- pdf_access: `false`\n"
        "- cache_access: `false`\n"
        "- downloaded: `0`\n"
        "- scoring: `not implemented`\n"
        "- investment advice: `not produced`\n"
    )
    if "counts" in manifest:
        summary += "\n## Counts\n\n" + "\n".join(
            f"- {key}: {value}" for key, value in manifest["counts"].items()
        ) + "\n"
    if "error" in manifest:
        summary += f"\n## Failure\n\n{manifest['error']}\n"
    (run_dir / "acceptance_summary.md").write_text(summary, encoding="utf-8")
    return {**manifest, "run_directory": run_dir}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", required=True)
    parser.add_argument("--run-id")
    args = parser.parse_args(argv)
    result = run_earnings_quality_metric_extension(
        args.output_root, run_id=args.run_id
    )
    print(json.dumps(_jsonable(result), ensure_ascii=False, indent=2))
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
