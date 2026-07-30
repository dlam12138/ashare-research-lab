"""Offline integration contract for Stage 2C-D."""

from __future__ import annotations

import json
from pathlib import Path

import duckdb
import pytest

from ashare_research.tools.official_earnings_quality_metric_extension import (
    EXPECTED_COUNTS,
    NEW_EXPECTED_COUNTS,
    ORIGINAL_38_RESULT_ID_SET_SHA256,
    UPSTREAM_132_FACT_ID_SET_SHA256,
    run_earnings_quality_metric_extension,
)

EXPECTED_LATEST = {
    (2021, "net_profit_excluding_non_recurring_yoy"): (
        "insufficient_history",
        None,
    ),
    (2021, "gross_profit"): ("computed", "54284500.000000000000"),
    (2021, "gross_margin"): ("computed", "0.207640601924"),
    (2021, "operating_profit_margin"): ("computed", "0.069684651896"),
    (2022, "net_profit_excluding_non_recurring_yoy"): (
        "computed",
        "0.710622821031",
    ),
    (2022, "gross_profit"): ("computed", "71123200.000000000000"),
    (2022, "gross_margin"): ("computed", "0.219572501202"),
    (2022, "operating_profit_margin"): ("computed", "0.074884684859"),
    (2023, "net_profit_excluding_non_recurring_yoy"): (
        "computed",
        "0.100604957124",
    ),
    (2023, "gross_profit"): ("computed", "70980700.000000000000"),
    (2023, "gross_margin"): ("computed", "0.235596180578"),
    (2023, "operating_profit_margin"): ("computed", "0.084147965422"),
    (2024, "net_profit_excluding_non_recurring_yoy"): (
        "computed",
        "-0.075255217756",
    ),
    (2024, "gross_profit"): ("computed", "66275800.000000000000"),
    (2024, "gross_margin"): ("computed", "0.225582806696"),
    (2024, "operating_profit_margin"): ("computed", "0.086891644296"),
    (2025, "net_profit_excluding_non_recurring_yoy"): (
        "computed",
        "-0.067033303133",
    ),
    (2025, "gross_profit"): ("computed", "61834800.000000000000"),
    (2025, "gross_margin"): ("computed", "0.215868281346"),
    (2025, "operating_profit_margin"): ("computed", "0.081892664923"),
}
NEW_IDS = {
    "net_profit_excluding_non_recurring_yoy",
    "gross_profit",
    "gross_margin",
    "operating_profit_margin",
}


@pytest.fixture(scope="module")
def two_runs(tmp_path_factory):
    root = tmp_path_factory.mktemp("stage2cd")
    first = run_earnings_quality_metric_extension(root, run_id="first")
    second = run_earnings_quality_metric_extension(root, run_id="second")
    return first, second


def _latest_new(result: dict) -> list[dict]:
    path = Path(result["run_directory"]) / "latest_metric_snapshot.json"
    rows = json.loads(path.read_text(encoding="utf-8"))
    return [row for row in rows if row["metric_id"] in NEW_IDS]


def test_run_counts_pit_and_audit_flags(two_runs):
    result, _ = two_runs
    assert result["status"] == "passed"
    assert result["transaction_committed"] is True
    assert result["offline"] is True
    assert result["network_access"] is False
    assert result["pdf_access"] is False
    assert result["cache_access"] is False
    assert result["downloaded"] == 0
    assert result["counts"] == EXPECTED_COUNTS
    assert result["new_earnings_counts"] == NEW_EXPECTED_COUNTS
    assert result["latest_metric_count"] == 50
    assert result["latest_computed"] == 46
    assert result["latest_insufficient_history"] == 4
    assert result["metric_pit_counts"] == [0, 10, 20, 30, 40, 50]
    assert result["metric_pit_computed_counts"] == [0, 6, 16, 26, 36, 46]
    assert result["metric_pit_insufficient_history_counts"] == [0, 4, 4, 4, 4, 4]


def test_latest_values_and_2025_review_status(two_runs):
    result, _ = two_runs
    rows = _latest_new(result)
    actual = {
        (int(row["fiscal_year"]), row["metric_id"]): (
            row["status"],
            row["value"],
        )
        for row in rows
    }
    assert actual == EXPECTED_LATEST
    assert all(
        row["revision_review_status"] == "not_yet_reviewable"
        for row in rows
        if row["fiscal_year"] == 2025
    )


def test_exactly_five_new_chains_and_2024_starts_with_prior_v2(two_runs):
    result, _ = two_runs
    transitions = result["new_metric_version_links"]
    assert {
        (item["fiscal_year"], item["metric_id"]) for item in transitions
    } == {
        (2022, "net_profit_excluding_non_recurring_yoy"),
        (2023, "net_profit_excluding_non_recurring_yoy"),
        (2023, "gross_profit"),
        (2023, "gross_margin"),
        (2023, "operating_profit_margin"),
    }
    assert all(
        item["before"]["result_version"] == 1
        and item["after"]["result_version"] == 2
        and item["after"]["supersedes_metric_result_id"]
        == item["before"]["metric_result_id"]
        for item in transitions
    )
    assert result["yoy_2024"]["result_version"] == 1
    upstream_db = (
        Path(result["run_directory"])
        / "upstream_earnings_quality"
        / "earnings_quality.duckdb"
    )
    prior_id = result["yoy_2024"]["input_fact_ids"][1]
    row = duckdb.connect(str(upstream_db), read_only=True).execute(
        "SELECT fact_version, restatement_version FROM financial_facts "
        "WHERE fact_id=?",
        [prior_id],
    ).fetchone()
    assert row == (2, "restated_1")


def test_only_eligible_reconciled_inputs_and_no_score_schema(two_runs):
    result, _ = two_runs
    run_dir = Path(result["run_directory"])
    versions = json.loads(
        (run_dir / "metric_result_versions.json").read_text(encoding="utf-8")
    )
    fact_ids = {
        fact_id for row in versions for fact_id in row["input_fact_ids"]
    }
    upstream_db = run_dir / "upstream_earnings_quality/earnings_quality.duckdb"
    conn = duckdb.connect(str(upstream_db), read_only=True)
    count = conn.execute(
        """SELECT COUNT(*) FROM financial_facts
           WHERE fact_id IN (SELECT UNNEST(?))
             AND source_tier='reconciled_derived'
             AND eligible_for_metrics=TRUE""",
        [sorted(fact_ids)],
    ).fetchone()[0]
    assert count == len(fact_ids)
    metric_conn = duckdb.connect(str(run_dir / "metrics.duckdb"), read_only=True)
    tables = {
        row[0]
        for row in metric_conn.execute(
            "SELECT table_name FROM information_schema.tables"
        ).fetchall()
    }
    assert not any("score" in name.lower() for name in tables)
    assert not any("score" in path.name.lower() for path in run_dir.iterdir())


def test_frozen_ids_read_only_upstream_and_deterministic_rerun(two_runs):
    first, second = two_runs
    assert first["original_result_id_set_sha256"] == (
        ORIGINAL_38_RESULT_ID_SET_SHA256
    )
    assert first["upstream"]["fact_id_set_sha256"] == (
        UPSTREAM_132_FACT_ID_SET_SHA256
    )
    assert first["upstream"]["sha256_before"] == first["upstream"]["sha256_after"]
    assert first["default_db_sha256_before"] == first["default_db_sha256_after"]
    assert first["new_metric_result_ids"] == second["new_metric_result_ids"]
    assert first["counts"] == second["counts"]
    assert [
        (row["fiscal_year"], row["metric_id"], row["status"], row["value"])
        for row in _latest_new(first)
    ] == [
        (row["fiscal_year"], row["metric_id"], row["status"], row["value"])
        for row in _latest_new(second)
    ]


def test_required_artifacts_and_relative_manifest(two_runs):
    result, _ = two_runs
    run_dir = Path(result["run_directory"])
    assert {
        "upstream_earnings_quality",
        "metrics.duckdb",
        "metric_definitions.json",
        "metric_result_versions.json",
        "latest_metric_snapshot.json",
        "metric_pit_snapshots.json",
        "earnings_quality_metric_transitions.json",
        "metric_lineage.json",
        "methodology_extension.json",
        "gap_inventory.json",
        "run_manifest.json",
        "acceptance_summary.md",
    } <= {path.name for path in run_dir.iterdir()}
    manifest_text = (run_dir / "run_manifest.json").read_text(encoding="utf-8")
    assert "D:\\\\" not in manifest_text
    assert str(run_dir.resolve()) not in manifest_text
