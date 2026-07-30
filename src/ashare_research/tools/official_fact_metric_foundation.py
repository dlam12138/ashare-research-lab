"""Build the Stage 2A PIT-aware metric foundation from trusted facts."""

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
from ashare_research.metrics.definitions import MetricDefinitionRegistry
from ashare_research.metrics.engine import MetricEngine
from ashare_research.metrics.models import MetricLineage, MetricResult
from ashare_research.metrics.repository import MetricRepository
from ashare_research.storage.duckdb_store import DuckDBStore
from ashare_research.tools.official_fact_multi_year_integration import (
    EXPECTED_SYMBOL,
)
from ashare_research.tools.official_fact_restatement_integration import (
    run_integration as run_restatement_integration,
)

METRIC_FOUNDATION_CONTRACT = "minimal_transparent_metrics_v1"
EXPECTED_YEARS = (2021, 2022, 2023, 2024, 2025)
EXPECTED_CONCEPTS = {
    "revenue",
    "net_profit_attributable_to_parent",
    "operating_cash_flow",
}
GAPS = (
    "扣非净利润增长",
    "毛利率与一般净利率",
    "非经常性损益占比",
    "自由现金流与资本开支强度",
    "ROE / ROA / ROIC",
    "财务安全指标",
    "分红、回购",
    "估值指标",
)


class MetricFoundationError(ValueError):
    """A deterministic Stage 2A acceptance gate failed."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise MetricFoundationError(message)


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


def build_run_id(now: datetime | None = None) -> str:
    timestamp = (now or datetime.now()).strftime("%Y%m%d_%H%M%S_%f")
    return f"metric_foundation_601857_SH_2021_2025_{timestamp}"


def _review_statuses(evidence_paths: list[str | Path]) -> dict[int, dict[str, bool]]:
    reviewed: dict[int, dict[str, bool]] = {}
    for path in evidence_paths:
        evidence = json.loads(Path(path).read_text(encoding="utf-8"))
        year = int(evidence["target_fiscal_year"])
        reviewed[year] = {
            item["concept_id"]: bool(item["changed"])
            for item in evidence["concepts"]
        }
    _require(set(reviewed) == {2021, 2022, 2023, 2024}, "evidence years differ")
    return reviewed


def _metric_review_status(
    fiscal_year: int,
    concept_ids: tuple[str, ...],
    reviewed: dict[int, dict[str, bool]],
) -> str:
    if fiscal_year == 2025:
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
        facts.setdefault(year, {})[str(row["concept_id"])] = row
    for year, by_concept in facts.items():
        _require(
            set(by_concept) == EXPECTED_CONCEPTS,
            f"{year} PIT snapshot does not have three concepts",
        )
        for fact in by_concept.values():
            _require(
                fact["source_tier"] == "reconciled_derived"
                and bool(fact["eligible_for_metrics"]),
                "metric snapshot contains a raw or ineligible fact",
            )
    return facts


def _changed(
    old: MetricResult,
    candidate: MetricResult,
) -> bool:
    return (
        old.value != candidate.value
        or old.status != candidate.status
        or old.input_fact_ids != candidate.input_fact_ids
    )


def _normalize_stored_results(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for row in rows:
        item = dict(row)
        if isinstance(item.get("input_fact_ids"), str):
            item["input_fact_ids"] = json.loads(item["input_fact_ids"])
        normalized.append(item)
    return normalized


def build_metric_versions(
    as_of: AsOfQuery,
    available_dates: list[str],
    reviewed: dict[int, dict[str, bool]],
    *,
    created_at: str,
) -> dict[str, Any]:
    """Replay Fact PIT snapshots and return only distinct metric versions."""
    latest_by_key: dict[tuple[str, int, str, str], MetricResult] = {}
    all_results: list[MetricResult] = []
    all_lineage: list[MetricLineage] = []
    source_snapshots: list[dict[str, Any]] = []

    for as_of_date in available_dates:
        frame = as_of.get_latest_available(
            EXPECTED_SYMBOL,
            as_of_date,
            sorted(EXPECTED_CONCEPTS),
        )
        facts = _snapshot_facts(frame)
        source_snapshots.append(
            {
                "as_of_date": as_of_date,
                "fact_count": len(frame),
                "fact_ids": frame["fact_id"].tolist(),
            }
        )
        for fiscal_year in sorted(facts):
            for definition in MetricDefinitionRegistry.list_all():
                primary = facts[fiscal_year].get(
                    definition.input_concept_ids[0]
                )
                if definition.formula == "(current / prior) - 1":
                    secondary = facts.get(fiscal_year - 1, {}).get(
                        definition.input_concept_ids[1]
                    )
                else:
                    secondary = facts[fiscal_year].get(
                        definition.input_concept_ids[1]
                    )
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
                    missing_prior_is_history=(
                        fiscal_year == EXPECTED_YEARS[0]
                        and definition.formula == "(current / prior) - 1"
                    ),
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
                    missing_prior_is_history=(
                        fiscal_year == EXPECTED_YEARS[0]
                        and definition.formula == "(current / prior) - 1"
                    ),
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
        "source_snapshots": source_snapshots,
    }


def _acceptance(
    repo: MetricRepository,
    built: dict[str, Any],
    available_dates: list[str],
    upstream_repo: FactRepository,
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
    expected = {
        "metric_definitions": 4,
        "metric_result_rows": 26,
        "computed_result_versions": 23,
        "insufficient_history_result_versions": 3,
        "metric_result_version_links": 6,
        "metric_lineage_rows": 49,
    }
    _require(counts == expected, f"metric counts differ: {counts}")

    first = date.fromisoformat(available_dates[0])
    snapshot_dates = [(first - timedelta(days=1)).isoformat(), *available_dates]
    snapshots: list[dict[str, Any]] = []
    for as_of_date in snapshot_dates:
        rows = repo.latest_results(as_of_date)
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
        [item["count"] for item in snapshots] == [0, 4, 8, 12, 16, 20],
        "Metric PIT counts differ",
    )
    _require(
        [item["computed"] for item in snapshots] == [0, 1, 5, 9, 13, 17],
        "computed Metric PIT counts differ",
    )
    latest = _normalize_stored_results(
        repo.latest_results(available_dates[-1])
    )
    _require(len(latest) == 20, "latest metric snapshot must contain 20 rows")
    _require(
        sum(row["status"] == "insufficient_history" for row in latest) == 3,
        "latest metric snapshot must contain three insufficient-history rows",
    )

    versioned = [result for result in built["results"] if result.result_version > 1]
    _require(len(versioned) == 6, "exactly six metric version links are required")
    changed_keys = {(item.fiscal_year, item.metric_id) for item in versioned}
    _require(
        changed_keys
        == {
            (2022, "net_profit_attributable_to_parent_yoy"),
            (2022, "operating_cash_flow_to_attributable_net_profit"),
            (2023, "revenue_yoy"),
            (2023, "net_profit_attributable_to_parent_yoy"),
            (2023, "operating_cash_flow_yoy"),
            (2023, "operating_cash_flow_to_attributable_net_profit"),
        },
        f"metric restatement propagation differs: {changed_keys}",
    )

    transitions: list[dict[str, Any]] = []
    by_id = {item.metric_result_id: item for item in built["results"]}
    for result in versioned:
        predecessor = by_id[result.supersedes_metric_result_id]
        _require(
            result.value != predecessor.value
            and result.input_fact_ids != predecessor.input_fact_ids,
            "versioned metric must change value and inputs",
        )
        transitions.append(
            {
                "fiscal_year": result.fiscal_year,
                "metric_id": result.metric_id,
                "before": asdict(predecessor),
                "after": asdict(result),
            }
        )

    upstream_as_of = AsOfQuery(upstream_repo)
    facts_2025 = _snapshot_facts(
        upstream_as_of.get_latest_available(
            EXPECTED_SYMBOL,
            "2025-03-31",
            sorted(EXPECTED_CONCEPTS),
        )
    )
    yoy_2024 = [
        result
        for result in built["results"]
        if result.fiscal_year == 2024
        and result.formula == "(current / prior) - 1"
    ]
    _require(len(yoy_2024) == 3, "2024 must have three YoY results")
    for result in yoy_2024:
        prior_concept = MetricDefinitionRegistry.get(
            result.metric_id
        ).input_concept_ids[1]
        prior = facts_2025[2023][prior_concept]
        _require(
            int(prior["fact_version"]) == 2
            and result.input_fact_ids[1] == prior["fact_id"],
            "2024 YoY did not use the 2023 v2 prior fact",
        )
    _require(
        all(
            result.revision_review_status == "not_yet_reviewable"
            for result in built["latest"]
            if result.fiscal_year == 2025
        ),
        "2025 metric revision status differs",
    )
    return {
        "counts": counts,
        "snapshots": snapshots,
        "latest": latest,
        "transitions": transitions,
        "yoy_2024": [asdict(item) for item in yoy_2024],
    }


def run_metric_foundation(
    bundle_paths: list[str | Path],
    evidence_paths: list[str | Path],
    output_root: str | Path,
    *,
    run_id: str | None = None,
) -> dict[str, Any]:
    run_id = run_id or build_run_id()
    run_dir = (
        Path(output_root)
        / EXPECTED_SYMBOL
        / "metric_foundation"
        / "2021_2025"
        / run_id
    )
    run_dir.mkdir(parents=True, exist_ok=False)
    upstream_root = run_dir / "upstream_restatement"
    metrics_path = run_dir / "metrics.duckdb"
    started_at = datetime.now().astimezone().isoformat()
    manifest: dict[str, Any] = {
        "run_id": run_id,
        "status": "failed",
        "transaction_committed": False,
        "offline": True,
        "symbol": EXPECTED_SYMBOL,
        "years": list(EXPECTED_YEARS),
        "metric_foundation_contract": METRIC_FOUNDATION_CONTRACT,
        "metric_schema_version": MetricRepository.schema_version,
        "database": metrics_path.name,
        "upstream_directory": "upstream_restatement",
        "started_at": started_at,
    }
    metrics_repo: MetricRepository | None = None
    upstream_store: DuckDBStore | None = None
    try:
        # Stage 1D-B has its own nested output hierarchy. Execute it under a
        # short temporary root to stay below Windows path limits, then move
        # the completed run directory into this run's required evidence
        # folder.
        with tempfile.TemporaryDirectory(prefix="m2_stage2a_") as temp_root:
            upstream = run_restatement_integration(
                bundle_paths,
                evidence_paths,
                temp_root,
                run_id="upstream",
            )
            _require(
                upstream["status"] == "passed",
                "upstream restatement failed",
            )
            shutil.move(str(upstream["run_directory"]), str(upstream_root))
            upstream["run_directory"] = upstream_root
        _require(
            upstream["counts"]["financial_facts"] == 57
            and upstream["latest_pit_snapshot"]["count"] == 15,
            "upstream fact acceptance counts differ",
        )
        upstream_db = (
            upstream["run_directory"] / "restatement_integration.duckdb"
        )
        upstream_hash_before = hashlib.sha256(upstream_db.read_bytes()).hexdigest()
        upstream_store = DuckDBStore(str(upstream_db))
        upstream_repo = FactRepository(upstream_store)
        as_of = AsOfQuery(upstream_repo)
        available_dates = [
            row[0]
            for row in upstream_store.connect().execute(
                """SELECT DISTINCT available_at FROM financial_facts
                   WHERE source_tier='reconciled_derived'
                     AND eligible_for_metrics=TRUE
                   ORDER BY available_at"""
            ).fetchall()
        ]
        _require(len(available_dates) == 5, "expected five Fact PIT dates")
        reviewed = _review_statuses(evidence_paths)
        created_at = datetime.now().astimezone().isoformat()
        built = build_metric_versions(
            as_of, available_dates, reviewed, created_at=created_at,
        )

        metrics_repo = MetricRepository(str(metrics_path))
        metrics_repo.ensure_schema(applied_at=created_at)
        completed_at = datetime.now().astimezone().isoformat()
        with metrics_repo.transaction() as conn:
            metrics_repo.store_definitions(
                MetricDefinitionRegistry.list_all(), conn=conn,
            )
            metrics_repo.store_results(
                built["results"], built["lineage"], conn=conn,
            )
            metrics_repo.store_run(
                run_id,
                status="passed",
                started_at=started_at,
                completed_at=completed_at,
                result_count=len(built["results"]),
                conn=conn,
            )
        acceptance = _acceptance(
            metrics_repo, built, available_dates, upstream_repo,
        )
        upstream_store.close()
        upstream_store = None
        upstream_hash_after = hashlib.sha256(upstream_db.read_bytes()).hexdigest()
        _require(
            upstream_hash_before == upstream_hash_after,
            "metric read modified upstream restatement DuckDB",
        )

        _write_json(
            run_dir / "metric_definitions.json",
            [asdict(item) for item in MetricDefinitionRegistry.list_all()],
        )
        _write_json(
            run_dir / "metric_result_versions.json",
            [asdict(item) for item in built["results"]],
        )
        _write_json(run_dir / "latest_metric_snapshot.json", acceptance["latest"])
        _write_json(run_dir / "metric_pit_snapshots.json", acceptance["snapshots"])
        _write_json(
            run_dir / "restatement_metric_transitions.json",
            acceptance["transitions"],
        )
        _write_json(
            run_dir / "metric_lineage.json",
            [asdict(item) for item in built["lineage"]],
        )
        _write_json(
            run_dir / "gap_inventory.json",
            {
                "status": "unsupported_fact_coverage",
                "items": [
                    {"name": item, "value": None, "reason": "missing_fact_coverage"}
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
                    "sha256_before": upstream_hash_before,
                    "sha256_after": upstream_hash_after,
                },
                "counts": acceptance["counts"],
                "latest_metric_count": len(acceptance["latest"]),
                "latest_computed": sum(
                    row["status"] == "computed" for row in acceptance["latest"]
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
        "# Minimal transparent metric foundation\n\n"
        f"- run_id: `{run_id}`\n"
        f"- status: **{manifest['status']}**\n"
        "- offline: `true`\n"
        f"- transaction_committed: `{str(manifest['transaction_committed']).lower()}`\n"
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
    parser.add_argument("--output-root", required=True)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    result = run_metric_foundation(
        args.bundle, args.evidence, args.output_root,
    )
    print(json.dumps(_jsonable(result), ensure_ascii=False, indent=2))
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
