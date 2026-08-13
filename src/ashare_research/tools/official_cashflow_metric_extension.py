"""Build the offline Stage 2B-B cash-flow metric extension.

The tool rebuilds the accepted Stage 2B-A 75-fact foundation, reads only
eligible reconciled facts through ``AsOfQuery``, preserves all Stage 2A
metric identities, and adds two explicitly scoped cash-flow metrics in a
fresh metric database.  It does not access the network, PDFs, or the shared
official-PDF cache.
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
from ashare_research.metrics.cashflow_definitions import (
    CashFlowMetricDefinitionRegistry,
)
from ashare_research.metrics.definitions import MetricDefinitionRegistry
from ashare_research.metrics.engine import MetricEngine
from ashare_research.metrics.models import MetricLineage, MetricResult
from ashare_research.metrics.repository import MetricRepository
from ashare_research.storage.duckdb_store import DuckDBStore
from ashare_research.tools.official_capex_cash_fact_foundation import (
    CAPEX_CONCEPT,
    run_capex_cash_foundation,
)
from ashare_research.tools.official_fact_metric_foundation import (
    build_metric_versions,
)
from ashare_research.tools.official_fact_multi_year_integration import (
    EXPECTED_SYMBOL,
    EXPECTED_YEARS,
)

CASHFLOW_METRIC_EXTENSION_CONTRACT = "cashflow_metric_extension_v1"
ALL_CONCEPTS = frozenset(
    {
        "revenue",
        "net_profit_attributable_to_parent",
        "operating_cash_flow",
        CAPEX_CONCEPT,
    }
)
STAGE2A_METRIC_RESULT_ID_SET_SHA256 = (
    "671249ca0133cfdf45f0146cd795b1badab8a1e3104a27cb535e83826caf0edf"
)
STAGE2BA_FACT_ID_SET_SHA256 = (
    "7787dad8be434ba04ad9ae3f19855a9e5f85333faa595466a95e6e1afb8d10a1"
)
EXPECTED_LATEST_VALUES = {
    (2021, "cash_based_free_cash_flow_proxy"): "7590600.000000000000",
    (2021, "cash_paid_for_fixed_assets_to_revenue"): "0.101579016421",
    (2022, "cash_based_free_cash_flow_proxy"): "15001600.000000000000",
    (2022, "cash_paid_for_fixed_assets_to_revenue"): "0.075251445819",
    (2023, "cash_based_free_cash_flow_proxy"): "17433900.000000000000",
    (2023, "cash_paid_for_fixed_assets_to_revenue"): "0.093768877713",
    (2024, "cash_based_free_cash_flow_proxy"): "10388100.000000000000",
    (2024, "cash_paid_for_fixed_assets_to_revenue"): "0.103013259786",
    (2025, "cash_based_free_cash_flow_proxy"): "11972100.000000000000",
    (2025, "cash_paid_for_fixed_assets_to_revenue"): "0.102214057824",
}
EXPECTED_2023_TRANSITIONS = {
    "cash_based_free_cash_flow_proxy": {
        "before_inputs": (
            "7eb6dbc54c5804849fc89cbfb3cb6434406d8cb4e38d29498f2c5eafbd8d1289",
            "5fde7bb54b26f2528b72cc04cc6a28289455e25f1faa4d78dceb9988e82e5a55",
        ),
        "before_value": "17407700.000000000000",
        "after_inputs": (
            "109d4cdd03072680a5cb5325bbb38b40fcb0f834aac8661daa8db0c7ff0564c4",
            "b6dbcb21298994846d241b265f8847e2819642b47259732bd45670f953f0d510",
        ),
        "after_value": "17433900.000000000000",
    },
    "cash_paid_for_fixed_assets_to_revenue": {
        "before_inputs": (
            "5fde7bb54b26f2528b72cc04cc6a28289455e25f1faa4d78dceb9988e82e5a55",
            "9a181c95213fbd68920bcf490a3903e8d608cf86505a4ff5524710b0c188e2a7",
        ),
        "before_value": "0.093828586535",
        "after_inputs": (
            "b6dbcb21298994846d241b265f8847e2819642b47259732bd45670f953f0d510",
            "1e15d297a93bb8d290dd7a9282fa14473ccc38b1f2d4927caf1007ec5b2fb3f8",
        ),
        "after_value": "0.093768877713",
    },
}
GAPS = (
    "扣非净利润",
    "毛利率和一般净利率",
    "非经常性损益",
    "ROE / ROA / ROIC",
    "财务安全",
    "分红与回购",
    "估值",
)


class CashFlowMetricExtensionError(ValueError):
    """A deterministic Stage 2B-B acceptance gate failed."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise CashFlowMetricExtensionError(message)


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


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _id_set_digest(ids: list[str]) -> str:
    payload = json.dumps(sorted(ids), separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()


def build_run_id(now: datetime | None = None) -> str:
    timestamp = (now or datetime.now()).strftime("%Y%m%d_%H%M%S_%f")
    return f"cashflow_metric_extension_601857_SH_2021_2025_{timestamp}"


def _load_json(path: str | Path) -> dict[str, Any]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    _require(isinstance(value, dict), f"{path}: evidence must be an object")
    return value


def _review_statuses(
    upstream_evidence_paths: list[str | Path],
    capex_review_paths: list[str | Path],
) -> dict[int, dict[str, bool]]:
    """Derive concept review status exclusively from committed evidence."""
    reviewed: dict[int, dict[str, bool]] = {}
    for path in upstream_evidence_paths:
        evidence = _load_json(path)
        year = int(evidence["target_fiscal_year"])
        concepts = evidence.get("concepts", [])
        _require(
            isinstance(concepts, list) and concepts,
            f"{path}: restatement concepts are missing",
        )
        reviewed[year] = {
            str(item["concept_id"]): bool(item["changed"])
            for item in concepts
        }
    for path in capex_review_paths:
        evidence = _load_json(path)
        year = int(evidence["target_fiscal_year"])
        _require(year in reviewed, f"{path}: target year is not registered")
        _require(
            evidence.get("concept_id") == CAPEX_CONCEPT,
            f"{path}: capex concept differs",
        )
        reviewed[year][CAPEX_CONCEPT] = bool(evidence["changed"])
    _require(
        set(reviewed) == set(EXPECTED_YEARS[:-1]),
        "review evidence years must be exactly 2021 through 2024",
    )
    for year, concepts in reviewed.items():
        _require(
            set(concepts) == ALL_CONCEPTS,
            f"{year}: review evidence does not cover all four concepts",
        )
    return reviewed


def _metric_review_status(
    fiscal_year: int,
    concept_ids: tuple[str, ...],
    reviewed: dict[int, dict[str, bool]],
) -> str:
    if fiscal_year == EXPECTED_YEARS[-1]:
        return "not_yet_reviewable"
    _require(fiscal_year in reviewed, f"missing review evidence for {fiscal_year}")
    return (
        "reviewed_changed"
        if any(reviewed[fiscal_year][concept] for concept in set(concept_ids))
        else "reviewed_unchanged"
    )


def _snapshot_facts(frame) -> dict[int, dict[str, dict[str, Any]]]:
    facts: dict[int, dict[str, dict[str, Any]]] = {}
    for row in frame.to_dict("records"):
        year = int(str(row["period_end"])[:4])
        concept = str(row["concept_id"])
        _require(concept not in facts.setdefault(year, {}), "duplicate PIT fact")
        facts[year][concept] = row
    for year, by_concept in facts.items():
        _require(
            set(by_concept) == ALL_CONCEPTS,
            f"{year}: PIT snapshot does not have four concepts",
        )
        for fact in by_concept.values():
            _require(
                fact["source_tier"] == "reconciled_derived"
                and bool(fact["eligible_for_metrics"]),
                "metric input is raw or ineligible",
            )
    return facts


def _changed(old: MetricResult, candidate: MetricResult) -> bool:
    return (
        old.value != candidate.value
        or old.status != candidate.status
        or old.input_fact_ids != candidate.input_fact_ids
    )


def _normalize_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for row in rows:
        item = dict(row)
        if isinstance(item.get("input_fact_ids"), str):
            item["input_fact_ids"] = json.loads(item["input_fact_ids"])
        item["value"] = (
            str(item["value"]) if item.get("value") is not None else None
        )
        normalized.append(item)
    return normalized


def build_cashflow_metric_versions(
    as_of: AsOfQuery,
    available_dates: list[str],
    reviewed: dict[int, dict[str, bool]],
    *,
    created_at: str,
) -> dict[str, Any]:
    """Replay Fact PIT and emit only semantically distinct new versions."""
    latest_by_key: dict[tuple[str, int, str, str], MetricResult] = {}
    all_results: list[MetricResult] = []
    all_lineage: list[MetricLineage] = []

    for as_of_date in available_dates:
        frame = as_of.get_latest_available(
            EXPECTED_SYMBOL,
            as_of_date,
            sorted(ALL_CONCEPTS),
        )
        facts = _snapshot_facts(frame)
        for fiscal_year in sorted(facts):
            for definition in CashFlowMetricDefinitionRegistry.list_all():
                primary = facts[fiscal_year][definition.input_concept_ids[0]]
                secondary = facts[fiscal_year][definition.input_concept_ids[1]]
                review_status = _metric_review_status(
                    fiscal_year,
                    definition.input_concept_ids,
                    reviewed,
                )
                candidate, _ = MetricEngine.compute(
                    definition,
                    symbol=EXPECTED_SYMBOL,
                    fiscal_year=fiscal_year,
                    primary_fact=primary,
                    secondary_fact=secondary,
                    revision_review_status=review_status,
                    as_of_date=as_of_date,
                    created_at=created_at,
                )
                key = (
                    EXPECTED_SYMBOL,
                    fiscal_year,
                    definition.metric_id,
                    definition.version,
                )
                previous = latest_by_key.get(key)
                if previous is not None and not _changed(previous, candidate):
                    continue
                result, lineage = MetricEngine.compute(
                    definition,
                    symbol=EXPECTED_SYMBOL,
                    fiscal_year=fiscal_year,
                    primary_fact=primary,
                    secondary_fact=secondary,
                    result_version=(
                        previous.result_version + 1 if previous else 1
                    ),
                    supersedes_metric_result_id=(
                        previous.metric_result_id if previous else ""
                    ),
                    revision_review_status=review_status,
                    as_of_date=as_of_date,
                    created_at=created_at,
                )
                latest_by_key[key] = result
                all_results.append(result)
                all_lineage.extend(lineage)
    return {
        "results": all_results,
        "lineage": all_lineage,
        "latest": sorted(
            latest_by_key.values(),
            key=lambda item: (item.fiscal_year, item.metric_id),
        ),
    }


def _acceptance(
    repo: MetricRepository,
    *,
    stage2a: dict[str, Any],
    cashflow: dict[str, Any],
    available_dates: list[str],
    upstream_fact_ids: list[str],
) -> dict[str, Any]:
    conn = repo.connect()
    counts = {
        "metric_definitions": conn.execute(
            "SELECT COUNT(*) FROM metric_definitions"
        ).fetchone()[0],
        "metric_result_rows": conn.execute(
            "SELECT COUNT(*) FROM metric_results"
        ).fetchone()[0],
        "computed_result_versions": conn.execute(
            "SELECT COUNT(*) FROM metric_results WHERE status='computed'"
        ).fetchone()[0],
        "insufficient_history_result_versions": conn.execute(
            "SELECT COUNT(*) FROM metric_results "
            "WHERE status='insufficient_history'"
        ).fetchone()[0],
        "metric_result_version_links": conn.execute(
            "SELECT COUNT(*) FROM metric_results "
            "WHERE supersedes_metric_result_id <> ''"
        ).fetchone()[0],
        "metric_lineage_rows": conn.execute(
            "SELECT COUNT(*) FROM metric_lineage"
        ).fetchone()[0],
    }
    expected_counts = {
        "metric_definitions": 6,
        "metric_result_rows": 38,
        "computed_result_versions": 35,
        "insufficient_history_result_versions": 3,
        "metric_result_version_links": 8,
        "metric_lineage_rows": 73,
    }
    _require(counts == expected_counts, f"metric counts differ: {counts}")

    first = date.fromisoformat(available_dates[0])
    snapshot_dates = [(first - timedelta(days=1)).isoformat(), *available_dates]
    snapshots: list[dict[str, Any]] = []
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
        [item["count"] for item in snapshots] == [0, 6, 12, 18, 24, 30],
        "Metric PIT counts differ",
    )
    _require(
        [item["computed"] for item in snapshots] == [0, 3, 9, 15, 21, 27],
        "computed Metric PIT counts differ",
    )
    _require(
        [item["insufficient_history"] for item in snapshots]
        == [0, 3, 3, 3, 3, 3],
        "insufficient-history Metric PIT counts differ",
    )

    latest = _normalize_rows(repo.latest_results(available_dates[-1]))
    _require(len(latest) == 30, "latest metric snapshot must contain 30 rows")
    new_latest = [
        row
        for row in latest
        if row["metric_id"] in CashFlowMetricDefinitionRegistry.DEFINITIONS
    ]
    _require(len(new_latest) == 10, "latest cash-flow snapshot differs")
    actual_values = {
        (int(row["fiscal_year"]), str(row["metric_id"])): row["value"]
        for row in new_latest
    }
    _require(
        actual_values == EXPECTED_LATEST_VALUES,
        f"latest cash-flow values differ: {actual_values}",
    )
    _require(
        all(row["status"] == "computed" for row in new_latest),
        "latest cash-flow metrics must all be computed",
    )
    _require(
        all(
            row["revision_review_status"] == "not_yet_reviewable"
            for row in new_latest
            if row["fiscal_year"] == 2025
        ),
        "2025 cash-flow review status differs",
    )

    stage2a_results = stage2a["results"]
    stage2a_ids = [item.metric_result_id for item in stage2a_results]
    _require(len(stage2a_ids) == 26, "Stage 2A result count changed")
    _require(
        _id_set_digest(stage2a_ids) == STAGE2A_METRIC_RESULT_ID_SET_SHA256,
        "Stage 2A Metric Result ID set changed",
    )
    stored_stage2a = [
        row
        for row in _normalize_rows(repo.all_results())
        if row["metric_id"] in MetricDefinitionRegistry.DEFINITIONS
    ]
    expected_stage2a = {
        item.metric_result_id: (
            str(item.value) if item.value is not None else None,
            str(item.status),
            list(item.input_fact_ids),
            item.supersedes_metric_result_id,
        )
        for item in stage2a_results
    }
    actual_stage2a = {
        row["metric_result_id"]: (
            row["value"],
            row["status"],
            row["input_fact_ids"],
            row["supersedes_metric_result_id"],
        )
        for row in stored_stage2a
    }
    _require(
        actual_stage2a == expected_stage2a,
        "Stage 2A values, statuses, inputs, or chains changed",
    )

    versioned = [
        result
        for result in cashflow["results"]
        if result.result_version > 1
    ]
    _require(
        {(item.fiscal_year, item.metric_id) for item in versioned}
        == {
            (2023, "cash_based_free_cash_flow_proxy"),
            (2023, "cash_paid_for_fixed_assets_to_revenue"),
        },
        "cash-flow version-chain keys differ",
    )
    by_id = {item.metric_result_id: item for item in cashflow["results"]}
    transitions: list[dict[str, Any]] = []
    for after in versioned:
        before = by_id[after.supersedes_metric_result_id]
        expected = EXPECTED_2023_TRANSITIONS[after.metric_id]
        _require(
            before.result_version == 1
            and after.result_version == 2
            and after.available_at == "2025-03-31"
            and before.input_fact_ids == expected["before_inputs"]
            and str(before.value) == expected["before_value"]
            and after.input_fact_ids == expected["after_inputs"]
            and str(after.value) == expected["after_value"],
            f"{after.metric_id}: 2023 transition differs",
        )
        transitions.append(
            {
                "fiscal_year": after.fiscal_year,
                "metric_id": after.metric_id,
                "before": asdict(before),
                "after": asdict(after),
                "pit_before_date": "2025-03-30",
                "pit_switch_date": "2025-03-31",
            }
        )

    _require(
        len(upstream_fact_ids) == 75
        and _id_set_digest(upstream_fact_ids) == STAGE2BA_FACT_ID_SET_SHA256,
        "Stage 2B-A 75 Fact ID set changed",
    )
    return {
        "counts": counts,
        "snapshots": snapshots,
        "latest": latest,
        "transitions": transitions,
        "stage2a_result_id_set_sha256": _id_set_digest(stage2a_ids),
        "upstream_fact_id_set_sha256": _id_set_digest(upstream_fact_ids),
    }


def run_cashflow_metric_extension(
    bundle_paths: list[str | Path],
    upstream_evidence_paths: list[str | Path],
    supplemental_paths: list[str | Path],
    capex_review_paths: list[str | Path],
    output_root: str | Path,
    *,
    run_id: str | None = None,
) -> dict[str, Any]:
    """Execute the complete offline Stage 2B-B acceptance."""
    run_id = run_id or build_run_id()
    run_dir = (
        Path(output_root)
        / EXPECTED_SYMBOL
        / "cashflow_metric_extension"
        / "2021_2025"
        / run_id
    )
    run_dir.mkdir(parents=True, exist_ok=False)
    upstream_dir = run_dir / "upstream_capex_cash"
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
        "symbol": EXPECTED_SYMBOL,
        "years": list(EXPECTED_YEARS),
        "contract": CASHFLOW_METRIC_EXTENSION_CONTRACT,
        "fact_schema_version": FactRepository.schema_version,
        "metric_schema_version": MetricRepository.schema_version,
        "metric_definition_schema_version": (
            CashFlowMetricDefinitionRegistry.schema_version
        ),
        "database": metrics_path.name,
        "upstream_directory": upstream_dir.name,
        "started_at": started_at,
    }
    metrics_repo: MetricRepository | None = None
    upstream_store: DuckDBStore | None = None
    try:
        reviewed = _review_statuses(
            upstream_evidence_paths,
            capex_review_paths,
        )
        with tempfile.TemporaryDirectory(prefix="m2_stage2bb_") as temp_root:
            upstream = run_capex_cash_foundation(
                bundle_paths,
                upstream_evidence_paths,
                supplemental_paths,
                capex_review_paths,
                temp_root,
                run_id="upstream",
            )
            _require(upstream["status"] == "passed", "Stage 2B-A upstream failed")
            shutil.move(str(upstream["run_directory"]), str(upstream_dir))
            upstream["run_directory"] = upstream_dir
        _require(
            upstream["counts"]["financial_facts"] == 75
            and upstream["latest_pit_snapshot"]["count"] == 20
            and upstream["counts"]["eligible_for_metrics"] == 25,
            "Stage 2B-A upstream counts differ",
        )

        upstream_db = (
            upstream_dir
            / "upstream_restatement"
            / "restatement_integration.duckdb"
        )
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
            len(upstream_fact_ids) == 75
            and _id_set_digest(upstream_fact_ids)
            == STAGE2BA_FACT_ID_SET_SHA256,
            "Stage 2B-A Fact ID set differs",
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
        stage2a_reviewed = {
            year: {
                concept: changed
                for concept, changed in concepts.items()
                if concept != CAPEX_CONCEPT
            }
            for year, concepts in reviewed.items()
        }
        stage2a = build_metric_versions(
            as_of,
            available_dates,
            stage2a_reviewed,
            created_at=created_at,
        )
        cashflow = build_cashflow_metric_versions(
            as_of,
            available_dates,
            reviewed,
            created_at=created_at,
        )
        definitions = [
            *MetricDefinitionRegistry.list_all(),
            *CashFlowMetricDefinitionRegistry.list_all(),
        ]
        results = [*stage2a["results"], *cashflow["results"]]
        lineage = [*stage2a["lineage"], *cashflow["lineage"]]

        metrics_repo = MetricRepository(str(metrics_path))
        metrics_repo.ensure_schema(applied_at=created_at)
        completed_at = datetime.now().astimezone().isoformat()
        with metrics_repo.transaction() as metrics_conn:
            metrics_repo.store_definitions(definitions, conn=metrics_conn)
            metrics_repo.store_results(
                results,
                lineage,
                conn=metrics_conn,
            )
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
            available_dates=available_dates,
            upstream_fact_ids=upstream_fact_ids,
        )

        upstream_store.close()
        upstream_store = None
        upstream_hash_after = _sha256(upstream_db)
        _require(
            upstream_hash_before == upstream_hash_after,
            "metric read modified Stage 2B-A upstream DuckDB",
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
            run_dir / "latest_metric_snapshot.json",
            acceptance["latest"],
        )
        _write_json(
            run_dir / "metric_pit_snapshots.json",
            acceptance["snapshots"],
        )
        _write_json(
            run_dir / "cashflow_metric_transitions.json",
            acceptance["transitions"],
        )
        _write_json(
            run_dir / "metric_lineage.json",
            [asdict(item) for item in lineage],
        )
        _write_json(
            run_dir / "gap_inventory.json",
            {
                "status": "unsupported_fact_coverage",
                "items": [
                    {
                        "name": item,
                        "value": None,
                        "reason": "missing_fact_coverage",
                    }
                    for item in GAPS
                ],
            },
        )
        manifest.update(
            {
                "status": "passed",
                "transaction_committed": True,
                "upstream": {
                    "status": upstream["status"],
                    "financial_facts": upstream["counts"]["financial_facts"],
                    "latest_pit": upstream["latest_pit_snapshot"]["count"],
                    "eligible_facts": upstream["counts"]["eligible_for_metrics"],
                    "fact_id_set_sha256": (
                        acceptance["upstream_fact_id_set_sha256"]
                    ),
                    "sha256_before": upstream_hash_before,
                    "sha256_after": upstream_hash_after,
                },
                "counts": acceptance["counts"],
                "latest_metric_count": len(acceptance["latest"]),
                "latest_computed": sum(
                    row["status"] == "computed"
                    for row in acceptance["latest"]
                ),
                "latest_insufficient_history": sum(
                    row["status"] == "insufficient_history"
                    for row in acceptance["latest"]
                ),
                "metric_pit_counts": [
                    item["count"] for item in acceptance["snapshots"]
                ],
                "metric_pit_computed_counts": [
                    item["computed"] for item in acceptance["snapshots"]
                ],
                "metric_pit_insufficient_history_counts": [
                    item["insufficient_history"]
                    for item in acceptance["snapshots"]
                ],
                "stage2a_result_versions": len(stage2a["results"]),
                "stage2a_result_id_set_sha256": (
                    acceptance["stage2a_result_id_set_sha256"]
                ),
                "new_cashflow_result_versions": len(cashflow["results"]),
                "new_cashflow_version_links": len(
                    acceptance["transitions"]
                ),
                "completed_at": completed_at,
            }
        )
    except Exception as exc:
        manifest["error_type"] = type(exc).__name__
        manifest["error"] = str(exc)
        manifest["completed_at"] = datetime.now().astimezone().isoformat()
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
        "# Cash-flow metric extension\n\n"
        f"- run_id: `{run_id}`\n"
        f"- status: **{manifest['status']}**\n"
        "- offline: `true`\n"
        "- network_access: `false`\n"
        "- pdf_access: `false`\n"
        "- cache_access: `false`\n"
        "- downloaded: `0`\n"
        f"- transaction_committed: "
        f"`{str(manifest['transaction_committed']).lower()}`\n"
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
    result = run_cashflow_metric_extension(
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
