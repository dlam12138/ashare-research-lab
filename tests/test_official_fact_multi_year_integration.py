"""Contract tests for the five-year official-fact integration tool."""

from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path

import pytest

from ashare_research.facts.identity import build_fact_id
from ashare_research.storage.default_db_guard import hash_optional_default_db
from ashare_research.tools.official_fact_multi_year_integration import (
    EXPECTED_YEARS,
    MultiYearIntegrationError,
    preflight_bundles,
    run_integration,
)

ROOT = Path(__file__).resolve().parents[1]
BUNDLE_DIR = ROOT / "acceptance" / "fixtures" / "official_facts" / "601857.SH"
BUNDLE_PATHS = [BUNDLE_DIR / f"{year}_annual.json" for year in EXPECTED_YEARS]
TOOL_PATH = (
    ROOT
    / "src"
    / "ashare_research"
    / "tools"
    / "official_fact_multi_year_integration.py"
)
ANNUAL_RUNNER_PATH = (
    ROOT
    / "src"
    / "ashare_research"
    / "tools"
    / "official_fact_acceptance.py"
)
DEFAULT_DB = ROOT / "data" / "research.duckdb"
DEFAULT_DB_ABSENT_SENTINEL = "default-db-not-present-in-clean-clone"


def _preflight(paths: list[Path] | None = None) -> dict:
    return preflight_bundles(
        list(paths or BUNDLE_PATHS),
        created_at="2026-07-30T00:00:00",
    )


def _mutated_bundle(tmp_path: Path, year: int, **updates: object) -> Path:
    bundle = json.loads((BUNDLE_DIR / f"{year}_annual.json").read_text(encoding="utf-8"))
    bundle.update(updates)
    path = tmp_path / f"{year}_annual.json"
    path.write_text(json.dumps(bundle, ensure_ascii=False), encoding="utf-8")
    return path


@pytest.fixture(scope="module")
def completed_run(tmp_path_factory: pytest.TempPathFactory) -> dict:
    output_root = tmp_path_factory.mktemp("multi_year_output")
    result = run_integration(
        BUNDLE_PATHS,
        output_root,
        run_id="multi_year_official_601857_SH_2021_2025_test",
    )
    assert result["status"] == "passed", result
    return result


def test_five_registered_bundles_load():
    preflight = _preflight()
    assert [record["bundle"]["fiscal_year"] for record in preflight["records"]] == list(
        EXPECTED_YEARS
    )


def test_years_must_be_exactly_2021_through_2025():
    with pytest.raises(MultiYearIntegrationError, match="exactly five"):
        _preflight(BUNDLE_PATHS[:-1])


def test_duplicate_year_fails(tmp_path: Path):
    del tmp_path
    with pytest.raises(MultiYearIntegrationError, match="duplicate year"):
        _preflight([*BUNDLE_PATHS[:-1], BUNDLE_PATHS[-2]])


def test_missing_year_fails(tmp_path: Path):
    replacement = _mutated_bundle(
        tmp_path,
        2025,
        fiscal_year=2026,
        period_start="2026-01-01",
        period_end="2026-12-31",
    )
    with pytest.raises(MultiYearIntegrationError, match="exactly 2021 through 2025"):
        _preflight([*BUNDLE_PATHS[:-1], replacement])


def test_different_symbol_fails(tmp_path: Path):
    replacement = _mutated_bundle(tmp_path, 2025, symbol="000001.SZ")
    with pytest.raises(MultiYearIntegrationError, match="symbol must be"):
        _preflight([*BUNDLE_PATHS[:-1], replacement])


def test_different_accounting_basis_fails(tmp_path: Path):
    replacement = _mutated_bundle(tmp_path, 2025, accounting_standard="IFRS")
    with pytest.raises(ValueError, match="accounting_standard"):
        _preflight([*BUNDLE_PATHS[:-1], replacement])


def test_five_contexts_are_canonical_and_unique():
    contexts = _preflight()["contexts"]
    assert [item["context_id"] for item in contexts] == [
        f"601857.SH|{year}|annual|consolidated" for year in EXPECTED_YEARS
    ]


def test_thirty_original_fact_ids_are_canonical_and_unique():
    facts = [
        fact
        for record in _preflight()["records"]
        for source in ("company", "exchange")
        for fact in record["source_facts"][source]
    ]
    assert len(facts) == 30
    assert len({fact["fact_id"] for fact in facts}) == 30
    assert all(fact["fact_id"] == build_fact_id(fact) for fact in facts)


def test_fifteen_in_memory_reconciliations_match():
    results = [
        result
        for record in _preflight()["records"]
        for result in record["preflight_results"]
    ]
    assert len(results) == 15
    assert {item["status"] for item in results} == {"matched"}
    assert all(item["output_fact"] is not None for item in results)


def test_failed_preflight_creates_no_database(tmp_path: Path):
    result = run_integration(
        BUNDLE_PATHS[:-1],
        tmp_path,
        run_id="multi_year_official_601857_SH_2021_2025_failed",
    )
    assert result["status"] == "failed"
    assert result["transaction_committed"] is False
    assert not (result["run_directory"] / "integration.duckdb").exists()


def test_multi_year_write_has_fixed_total_counts(completed_run: dict):
    assert completed_run["counts"] == {
        "fact_contexts": 5,
        "company_original": 15,
        "exchange_original": 15,
        "original_total": 30,
        "reconciled": 15,
        "financial_facts": 45,
        "eligible_for_metrics": 15,
        "ineligible_originals": 30,
        "reconciliation_matched": 15,
        "lineage": 45,
        "audit": 45,
    }


def test_each_year_has_nine_facts_and_nine_lineage_rows(completed_run: dict):
    annual = json.loads(
        (completed_run["run_directory"] / "annual_integration_results.json").read_text(
            encoding="utf-8"
        )
    )
    assert [item["fiscal_year"] for item in annual] == list(EXPECTED_YEARS)
    for item in annual:
        assert (
            item["company_original"],
            item["exchange_original"],
            item["reconciled"],
            item["facts"],
            item["lineage"],
        ) == (3, 3, 3, 9, 9)


def test_integrated_fact_ids_equal_preflight_ids(completed_run: dict):
    expected = {
        fact["fact_id"]
        for record in _preflight()["records"]
        for source in ("company", "exchange")
        for fact in record["source_facts"][source]
    }
    expected.update(
        result["output_fact"]["fact_id"]
        for record in _preflight()["records"]
        for result in record["preflight_results"]
    )
    annual = json.loads(
        (completed_run["run_directory"] / "annual_integration_results.json").read_text(
            encoding="utf-8"
        )
    )
    actual = {fact_id for item in annual for fact_id in item["fact_ids"]}
    assert len(expected) == 45
    assert actual == expected


def test_pit_cumulative_snapshots_are_0_3_6_9_12_15(completed_run: dict):
    snapshots = json.loads(
        (completed_run["run_directory"] / "pit_snapshots.json").read_text(
            encoding="utf-8"
        )
    )
    assert [item["count"] for item in snapshots] == [0, 3, 6, 9, 12, 15]
    assert [item["fiscal_years"] for item in snapshots] == [
        [],
        [2021],
        [2021, 2022],
        [2021, 2022, 2023],
        [2021, 2022, 2023, 2024],
        [2021, 2022, 2023, 2024, 2025],
    ]


def test_final_snapshot_excludes_original_ineligible_facts(completed_run: dict):
    snapshots = json.loads(
        (completed_run["run_directory"] / "pit_snapshots.json").read_text(
            encoding="utf-8"
        )
    )
    reconciled_ids = {
        result["output_fact"]["fact_id"]
        for record in _preflight()["records"]
        for result in record["preflight_results"]
    }
    assert set(snapshots[-1]["fact_ids"]) == reconciled_ids


def test_manifest_contains_bundle_hashes_without_absolute_paths(completed_run: dict):
    manifest_path = completed_run["run_directory"] / "input_bundle_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert len(manifest["bundles"]) == 5
    assert all(len(item["sha256"]) == 64 for item in manifest["bundles"])
    text = manifest_path.read_text(encoding="utf-8")
    assert str(ROOT) not in text
    assert "D:\\" not in text


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


def test_run_does_not_modify_single_year_runner_or_default_database(tmp_path: Path):
    runner_before = hashlib.sha256(ANNUAL_RUNNER_PATH.read_bytes()).hexdigest()
    database_before = hash_optional_default_db(DEFAULT_DB, DEFAULT_DB_ABSENT_SENTINEL)
    result = run_integration(
        BUNDLE_PATHS,
        tmp_path,
        run_id="multi_year_official_601857_SH_2021_2025_immutability",
    )
    assert result["status"] == "passed"
    assert hashlib.sha256(ANNUAL_RUNNER_PATH.read_bytes()).hexdigest() == runner_before
    assert hash_optional_default_db(DEFAULT_DB, DEFAULT_DB_ABSENT_SENTINEL) == database_before


def test_no_restatement_versions_are_created(completed_run: dict):
    annual = json.loads(
        (completed_run["run_directory"] / "annual_integration_results.json").read_text(
            encoding="utf-8"
        )
    )
    assert sum(len(item["fact_ids"]) for item in annual) == 45
    assert completed_run["fact_schema_version"] == "2.1"
