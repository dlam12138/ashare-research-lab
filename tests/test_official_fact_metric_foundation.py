"""Integration contracts for the Stage 2A metric foundation."""

from __future__ import annotations

import ast
import hashlib
import json
from decimal import ROUND_HALF_EVEN, Context, Decimal, localcontext
from pathlib import Path

import duckdb
import pytest

from ashare_research.tools.official_fact_metric_foundation import (
    run_metric_foundation,
)
from ashare_research.tools.official_fact_multi_year_integration import (
    EXPECTED_YEARS,
)

ROOT = Path(__file__).resolve().parents[1]
BUNDLE_DIR = ROOT / "acceptance" / "fixtures" / "official_facts" / "601857.SH"
EVIDENCE_DIR = ROOT / "acceptance" / "fixtures" / "restatements" / "601857.SH"
BUNDLE_PATHS = [BUNDLE_DIR / f"{year}_annual.json" for year in EXPECTED_YEARS]
EVIDENCE_PATHS = [
    EVIDENCE_DIR / f"{year}_reviewed_by_{year + 1}_annual.json"
    for year in EXPECTED_YEARS[:-1]
]
TOOL_PATH = (
    ROOT
    / "src"
    / "ashare_research"
    / "tools"
    / "official_fact_metric_foundation.py"
)
DEFAULT_DB = ROOT / "data" / "research.duckdb"
DERIVATION_FILES = [
    ROOT / "src" / "ashare_research" / "derivations" / name
    for name in ("definitions.py", "engine.py")
]
STAGE1DB_FILES = [
    ROOT
    / "src"
    / "ashare_research"
    / "tools"
    / "official_fact_restatement_integration.py",
    ROOT
    / "acceptance"
    / "m2_stage1db_petrochina_restatement_evidence_and_version_chains.md",
]


@pytest.fixture(scope="module")
def completed_run(tmp_path_factory: pytest.TempPathFactory) -> dict:
    result = run_metric_foundation(
        BUNDLE_PATHS,
        EVIDENCE_PATHS,
        tmp_path_factory.mktemp("metric_output"),
        run_id="metric_test",
    )
    assert result["status"] == "passed", result
    return result


def _read(run: dict, name: str):
    return json.loads(
        (run["run_directory"] / name).read_text(encoding="utf-8")
    )


def _upstream_db(run: dict) -> Path:
    matches = list(
        (run["run_directory"] / "upstream_restatement").rglob(
            "restatement_integration.duckdb"
        )
    )
    assert len(matches) == 1
    return matches[0]


def test_upstream_and_metric_fixed_counts(completed_run: dict):
    assert completed_run["upstream"]["financial_facts"] == 57
    assert completed_run["upstream"]["latest_pit"] == 15
    assert completed_run["counts"] == {
        "metric_definitions": 4,
        "metric_result_rows": 26,
        "computed_result_versions": 23,
        "insufficient_history_result_versions": 3,
        "metric_result_version_links": 6,
        "metric_lineage_rows": 49,
    }
    assert (
        completed_run["latest_metric_count"],
        completed_run["latest_computed"],
        completed_run["latest_insufficient_history"],
    ) == (20, 17, 3)


def test_metric_pit_snapshots_have_expected_counts(completed_run: dict):
    assert completed_run["metric_pit_counts"] == [0, 4, 8, 12, 16, 20]
    assert completed_run["metric_pit_computed_counts"] == [0, 1, 5, 9, 13, 17]


def test_2021_yoy_is_insufficient_history_not_zero(completed_run: dict):
    latest = _read(completed_run, "latest_metric_snapshot.json")
    yoy = [
        item
        for item in latest
        if item["fiscal_year"] == 2021 and item["metric_id"].endswith("_yoy")
    ]
    assert len(yoy) == 3
    assert {item["status"] for item in yoy} == {"insufficient_history"}
    assert all(item["value"] is None for item in yoy)
    assert all("fiscal_year=2020" in item["missing_input_description"] for item in yoy)


def test_all_lineage_inputs_are_eligible_reconciled_facts(completed_run: dict):
    lineage = _read(completed_run, "metric_lineage.json")
    ids = {item["input_fact_id"] for item in lineage}
    con = duckdb.connect(str(_upstream_db(completed_run)), read_only=True)
    try:
        rows = con.execute(
            """SELECT fact_id, source_tier, eligible_for_metrics
               FROM financial_facts WHERE fact_id IN (
                 SELECT UNNEST(?)
               )""",
            [list(ids)],
        ).fetchall()
    finally:
        con.close()
    assert len(rows) == len(ids)
    assert all(row[1] == "reconciled_derived" and row[2] is True for row in rows)


def test_latest_values_follow_committed_facts_and_decimal_formulas(
    completed_run: dict,
):
    latest = _read(completed_run, "latest_metric_snapshot.json")
    con = duckdb.connect(str(_upstream_db(completed_run)), read_only=True)
    try:
        values = {
            row[0]: int(row[1])
            for row in con.execute(
                "SELECT fact_id, value FROM financial_facts"
            ).fetchall()
        }
    finally:
        con.close()
    with localcontext(Context(prec=28, rounding=ROUND_HALF_EVEN)):
        for item in latest:
            if item["status"] != "computed":
                continue
            inputs = [Decimal(values[fact_id]) for fact_id in item["input_fact_ids"]]
            expected = (
                inputs[0] / inputs[1] - Decimal(1)
                if item["formula"] == "(current / prior) - 1"
                else inputs[0] / inputs[1]
            ).quantize(Decimal("0.000000000001"), rounding=ROUND_HALF_EVEN)
            assert item["value"] == str(expected)


def test_restatements_naturally_create_six_metric_version_chains(
    completed_run: dict,
):
    transitions = _read(
        completed_run, "restatement_metric_transitions.json"
    )
    assert {
        (item["fiscal_year"], item["metric_id"]) for item in transitions
    } == {
        (2022, "net_profit_attributable_to_parent_yoy"),
        (2022, "operating_cash_flow_to_attributable_net_profit"),
        (2023, "revenue_yoy"),
        (2023, "net_profit_attributable_to_parent_yoy"),
        (2023, "operating_cash_flow_yoy"),
        (2023, "operating_cash_flow_to_attributable_net_profit"),
    }
    for item in transitions:
        assert item["before"]["result_version"] == 1
        assert item["after"]["result_version"] == 2
        assert (
            item["after"]["supersedes_metric_result_id"]
            == item["before"]["metric_result_id"]
        )
        assert item["after"]["input_fact_ids"] != item["before"]["input_fact_ids"]
        assert item["after"]["value"] != item["before"]["value"]


def test_2024_yoy_first_versions_use_2023_v2(completed_run: dict):
    versions = _read(completed_run, "metric_result_versions.json")
    yoy_2024 = [
        item
        for item in versions
        if item["fiscal_year"] == 2024 and item["metric_id"].endswith("_yoy")
    ]
    assert len(yoy_2024) == 3
    assert {item["result_version"] for item in yoy_2024} == {1}
    con = duckdb.connect(str(_upstream_db(completed_run)), read_only=True)
    try:
        prior_versions = {
            row[0]: row[1]
            for row in con.execute(
                "SELECT fact_id, fact_version FROM financial_facts"
            ).fetchall()
        }
    finally:
        con.close()
    assert all(prior_versions[item["input_fact_ids"][1]] == 2 for item in yoy_2024)


def test_2025_results_are_computed_but_not_yet_reviewable(completed_run: dict):
    latest = _read(completed_run, "latest_metric_snapshot.json")
    rows = [item for item in latest if item["fiscal_year"] == 2025]
    assert len(rows) == 4
    assert {item["status"] for item in rows} == {"computed"}
    assert {item["revision_review_status"] for item in rows} == {
        "not_yet_reviewable"
    }


def test_metric_availability_never_precedes_any_input(completed_run: dict):
    versions = _read(completed_run, "metric_result_versions.json")
    lineage = _read(completed_run, "metric_lineage.json")
    by_result: dict[str, list[dict]] = {}
    for row in lineage:
        by_result.setdefault(row["metric_result_id"], []).append(row)
    for result in versions:
        inputs = by_result.get(result["metric_result_id"], [])
        if inputs:
            assert result["available_at"] == max(
                item["input_available_at"] for item in inputs
            )


def test_repeated_runs_have_identical_ids_and_values(
    completed_run: dict,
    tmp_path: Path,
):
    second = run_metric_foundation(
        BUNDLE_PATHS,
        EVIDENCE_PATHS,
        tmp_path,
        run_id="metric_repeat",
    )
    assert second["status"] == "passed"
    first_versions = _read(completed_run, "metric_result_versions.json")
    second_versions = _read(second, "metric_result_versions.json")
    first = {
        item["metric_result_id"]: (item["value"], item["status"])
        for item in first_versions
    }
    repeated = {
        item["metric_result_id"]: (item["value"], item["status"])
        for item in second_versions
    }
    assert repeated == first


def test_output_contract_has_no_absolute_paths_or_scores(completed_run: dict):
    expected = {
        "upstream_restatement",
        "metrics.duckdb",
        "metric_definitions.json",
        "metric_result_versions.json",
        "latest_metric_snapshot.json",
        "metric_pit_snapshots.json",
        "restatement_metric_transitions.json",
        "metric_lineage.json",
        "gap_inventory.json",
        "run_manifest.json",
        "acceptance_summary.md",
    }
    assert {item.name for item in completed_run["run_directory"].iterdir()} == expected
    for path in completed_run["run_directory"].iterdir():
        if path.is_file() and path.suffix != ".duckdb":
            text = path.read_text(encoding="utf-8")
            assert str(ROOT) not in text
            assert "D:\\" not in text
            assert '"score"' not in text
    con = duckdb.connect(
        str(completed_run["run_directory"] / "metrics.duckdb"),
        read_only=True,
    )
    try:
        tables = {
            row[0]
            for row in con.execute(
                "SELECT table_name FROM information_schema.tables"
            ).fetchall()
        }
    finally:
        con.close()
    assert all("score" not in name for name in tables)


def test_gap_inventory_is_missing_coverage_not_zero(completed_run: dict):
    inventory = _read(completed_run, "gap_inventory.json")
    assert inventory["status"] == "unsupported_fact_coverage"
    assert len(inventory["items"]) == 8
    assert all(item["value"] is None for item in inventory["items"])
    assert {item["reason"] for item in inventory["items"]} == {
        "missing_fact_coverage"
    }


def test_tool_imports_no_network_or_pdf_packages():
    tree = ast.parse(TOOL_PATH.read_text(encoding="utf-8"))
    imported = {
        alias.name.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.Import | ast.ImportFrom)
        for alias in (
            node.names
            if isinstance(node, ast.Import)
            else [ast.alias(node.module or "")]
        )
    }
    assert imported.isdisjoint(
        {"requests", "httpx", "urllib", "socket", "pdfplumber", "pypdf", "fitz"}
    )


def test_run_preserves_default_database_and_protected_sources(tmp_path: Path):
    default_before = hashlib.sha256(DEFAULT_DB.read_bytes()).hexdigest()
    protected = {
        path: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in [*DERIVATION_FILES, *STAGE1DB_FILES]
    }
    result = run_metric_foundation(
        BUNDLE_PATHS,
        EVIDENCE_PATHS,
        tmp_path,
        run_id="metric_immutable",
    )
    assert result["status"] == "passed"
    assert hashlib.sha256(DEFAULT_DB.read_bytes()).hexdigest() == default_before
    assert protected == {
        path: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in protected
    }
