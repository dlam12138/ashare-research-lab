"""Contracts for registered restatement evidence and its offline integration."""

from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path

import pytest

from ashare_research.facts.identity import build_fact_id
from ashare_research.facts.repository import FactRepository
from ashare_research.storage.duckdb_store import DuckDBStore
from ashare_research.tools.official_fact_multi_year_integration import (
    EXPECTED_YEARS,
    preflight_bundles,
)
from ashare_research.tools.official_fact_restatement_integration import (
    EXPECTED_TARGET_YEARS,
    RESTATEMENT_CONTRACT,
    RestatementIntegrationError,
    preflight_restatements,
    run_integration,
)

ROOT = Path(__file__).resolve().parents[1]
BUNDLE_DIR = ROOT / "acceptance" / "fixtures" / "official_facts" / "601857.SH"
EVIDENCE_DIR = ROOT / "acceptance" / "fixtures" / "restatements" / "601857.SH"
BUNDLE_PATHS = [BUNDLE_DIR / f"{year}_annual.json" for year in EXPECTED_YEARS]
EVIDENCE_PATHS = [
    EVIDENCE_DIR / f"{year}_reviewed_by_{year + 1}_annual.json"
    for year in EXPECTED_TARGET_YEARS
]
TOOL_PATH = (
    ROOT
    / "src"
    / "ashare_research"
    / "tools"
    / "official_fact_restatement_integration.py"
)
DEFAULT_DB = ROOT / "data" / "research.duckdb"


def _annual() -> dict:
    return preflight_bundles(
        BUNDLE_PATHS,
        created_at="2026-07-30T00:00:00+08:00",
    )


def _restatements(paths: list[Path] | None = None) -> dict:
    return preflight_restatements(
        _annual(),
        list(paths or EVIDENCE_PATHS),
        created_at="2026-07-30T00:00:00+08:00",
    )


@pytest.fixture(scope="module")
def completed_run(tmp_path_factory: pytest.TempPathFactory) -> dict:
    result = run_integration(
        BUNDLE_PATHS,
        EVIDENCE_PATHS,
        tmp_path_factory.mktemp("restatement_output"),
        run_id="restatement_601857_SH_2021_2025_test",
    )
    assert result["status"] == "passed", result
    return result


def test_four_registered_evidence_files_load():
    result = _restatements()
    assert result["changed_count"] == 4
    assert len(result["records"]) == 4
    assert len(result["comparisons"]) == 12
    assert all(
        record["evidence"]["contract"] == RESTATEMENT_CONTRACT
        for record in result["records"]
    )


def test_changed_matrix_comes_from_registered_comparisons():
    comparisons = _restatements()["comparisons"]
    changed = {
        (item["target_fiscal_year"], item["concept_id"])
        for item in comparisons
        if item["changed"]
    }
    assert changed == {
        (2022, "net_profit_attributable_to_parent"),
        (2023, "revenue"),
        (2023, "net_profit_attributable_to_parent"),
        (2023, "operating_cash_flow"),
    }


def test_change_flags_are_derived_from_values():
    for item in _restatements()["comparisons"]:
        assert item["changed"] is (
            item["original_raw_value"] != item["later_comparative_raw_value"]
        )


def test_evidence_documents_match_registered_annual_bundles():
    annual_by_year = {
        record["bundle"]["fiscal_year"]: record["bundle"]
        for record in _annual()["records"]
    }
    for path in EVIDENCE_PATHS:
        evidence = json.loads(path.read_text(encoding="utf-8"))
        bundle = annual_by_year[evidence["evidence_fiscal_year"]]
        assert evidence["document_relationship"] == bundle["document_relationship"]
        for source in ("company", "exchange"):
            actual = evidence["documents"][source]
            expected = bundle["documents"][source]
            assert actual["sha256"] == expected["sha256"]
            assert actual["content_length"] == expected["content_length"]
            assert actual["page_count"] == expected["page_count"]
            assert actual["announcement_date"] == expected["announcement_date"]
            assert actual["source_url"] in {
                expected["pdf_url"],
                expected["final_pdf_url"],
            }


def test_evidence_original_ids_and_values_equal_annual_baseline():
    result = _restatements()
    original_by_key = {
        (
            record["bundle"]["fiscal_year"],
            source,
            fact["concept_id"],
        ): fact
        for record in _annual()["records"]
        for source in ("company", "exchange")
        for fact in record["source_facts"][source]
    }
    for record in result["records"]:
        evidence = record["evidence"]
        for concept in evidence["concepts"]:
            for source in ("company", "exchange"):
                fact = original_by_key[
                    evidence["target_fiscal_year"],
                    source,
                    concept["concept_id"],
                ]
                assert concept["original_fact_ids"][source] == fact["fact_id"]
                assert concept["original_raw_value"] == str(fact["raw_value"])


def test_changed_v2_facts_keep_stable_logical_source_identity():
    annual_facts = {
        fact["fact_id"]: fact
        for record in _annual()["records"]
        for source in ("company", "exchange")
        for fact in record["source_facts"][source]
    }
    for pair in _restatements()["changed_pairs"]:
        for source in ("company", "exchange"):
            fact = pair[f"{source}_fact"]
            predecessor = annual_facts[fact["supersedes_fact_id"]]
            assert fact["source_id"] == predecessor["source_id"]
            assert fact["source_tier"] == predecessor["source_tier"]
            assert fact["context_id"] == predecessor["context_id"]
            assert fact["fact_id"] == build_fact_id(fact)
            assert fact["fact_version"] == 2
            assert fact["restatement_version"] == "restated_1"


def test_every_changed_pair_matches_in_memory():
    pairs = _restatements()["changed_pairs"]
    assert len(pairs) == 4
    assert {pair["preflight_result"]["status"] for pair in pairs} == {"matched"}
    assert all(pair["preflight_result"]["output_fact"] for pair in pairs)


def test_invalid_evidence_fails_before_database_creation(tmp_path: Path):
    evidence = json.loads(EVIDENCE_PATHS[0].read_text(encoding="utf-8"))
    evidence["concepts"][0]["later_comparative_raw_value"] = "1"
    invalid = tmp_path / EVIDENCE_PATHS[0].name
    invalid.write_text(json.dumps(evidence, ensure_ascii=False), encoding="utf-8")
    paths = [invalid, *EVIDENCE_PATHS[1:]]
    with pytest.raises(RestatementIntegrationError, match="changed flag"):
        _restatements(paths)

    result = run_integration(
        BUNDLE_PATHS,
        paths,
        tmp_path,
        run_id="restatement_failed_preflight",
    )
    assert result["status"] == "failed"
    assert result["transaction_committed"] is False
    assert not (result["run_directory"] / "restatement_integration.duckdb").exists()


def test_dynamic_counts_use_observed_r(completed_run: dict):
    assert completed_run["changed_concept_years"] == 4
    assert completed_run["counts"] == {
        "fact_contexts": 5,
        "company_facts": 19,
        "exchange_facts": 19,
        "original_raw_facts": 38,
        "reconciled_facts": 19,
        "financial_facts": 57,
        "eligible_for_metrics": 19,
        "ineligible_raw_facts": 38,
        "version_chain_links": 12,
        "lineage": 57,
        "audit": 57,
    }


def test_each_changed_concept_has_three_version_links(completed_run: dict):
    chains = json.loads(
        (completed_run["run_directory"] / "version_chains.json").read_text(
            encoding="utf-8"
        )
    )
    assert len(chains) == 12
    grouped: dict[tuple[str, str], list[dict]] = {}
    for row in chains:
        grouped.setdefault((row["period_end"], row["concept_id"]), []).append(row)
        assert row["fact_version"] == 2
        assert row["restatement_version"] == "restated_1"
        assert len(row["supersedes_fact_id"]) == 64
    assert len(grouped) == 4
    assert all(
        {item["source_tier"] for item in rows}
        == {
            "company_official",
            "exchange_official",
            "reconciled_derived",
        }
        for rows in grouped.values()
    )


def test_unchanged_comparisons_create_no_version_chain(completed_run: dict):
    changed_keys = {
        (f"{item['target_fiscal_year']}-12-31", item["concept_id"])
        for item in _restatements()["comparisons"]
        if item["changed"]
    }
    chains = json.loads(
        (completed_run["run_directory"] / "version_chains.json").read_text(
            encoding="utf-8"
        )
    )
    assert {(item["period_end"], item["concept_id"]) for item in chains} == changed_keys


def test_pit_switches_from_v1_to_v2_on_later_availability(completed_run: dict):
    transitions = json.loads(
        (completed_run["run_directory"] / "pit_transitions.json").read_text(
            encoding="utf-8"
        )
    )
    expected = {
        (item["target_fiscal_year"], item["concept_id"]): item
        for item in _restatements()["comparisons"]
        if item["changed"]
    }
    assert len(transitions) == 4
    for item in transitions:
        evidence = expected[item["target_fiscal_year"], item["concept_id"]]
        assert item["before_value"] == int(evidence["original_raw_value"]) * 100
        assert (
            item["on_value"]
            == int(evidence["later_comparative_raw_value"]) * 100
        )
        assert item["supersedes_fact_id"] == item["before_fact_id"]
        assert item["on_fact_id"] != item["before_fact_id"]


def test_compare_versions_detects_all_four_changes(completed_run: dict):
    comparisons = completed_run["compare_versions"]
    assert len(comparisons) == 4
    assert all(item["changed"] is True for item in comparisons)


def test_final_pit_snapshot_has_one_fact_per_year_and_concept(completed_run: dict):
    assert completed_run["base_pit_snapshot_counts"] == [0, 3, 6, 9, 12, 15]
    latest = completed_run["latest_pit_snapshot"]
    assert latest["as_of_date"] == "2026-03-30"
    assert latest["count"] == 15
    assert len(set(latest["fact_ids"])) == 15


def test_original_45_fact_ids_are_unchanged_in_restatement_database(
    completed_run: dict,
):
    expected = {
        fact["fact_id"]
        for record in _annual()["records"]
        for source in ("company", "exchange")
        for fact in record["source_facts"][source]
    }
    expected.update(
        result["output_fact"]["fact_id"]
        for record in _annual()["records"]
        for result in record["preflight_results"]
    )
    store = DuckDBStore(
        str(completed_run["run_directory"] / "restatement_integration.duckdb")
    )
    try:
        repo = FactRepository(store)
        repo.ensure_schema()
        actual = set(
            store.connect()
            .execute(
                "SELECT fact_id FROM financial_facts WHERE fact_version=1"
            )
            .df()["fact_id"]
        )
    finally:
        store.close()
    assert len(expected) == 45
    assert actual == expected


def test_output_manifest_set_and_no_absolute_paths(completed_run: dict):
    expected = {
        "restatement_integration.duckdb",
        "evidence_manifest.json",
        "comparison_results.json",
        "version_chains.json",
        "pit_transitions.json",
        "lineage_summary.json",
        "run_manifest.json",
        "acceptance_summary.md",
    }
    assert {path.name for path in completed_run["run_directory"].iterdir()} == expected
    for name in expected - {"restatement_integration.duckdb"}:
        content = (completed_run["run_directory"] / name).read_text(encoding="utf-8")
        assert str(ROOT) not in content
        assert "D:\\" not in content


def test_2025_is_not_yet_reviewable_and_creates_no_v2(completed_run: dict):
    assert completed_run["review_status_2025"] == "not_yet_reviewable"
    chains = json.loads(
        (completed_run["run_directory"] / "version_chains.json").read_text(
            encoding="utf-8"
        )
    )
    assert all(item["period_end"] != "2025-12-31" for item in chains)


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


def test_run_does_not_modify_default_database(tmp_path: Path):
    before = hashlib.sha256(DEFAULT_DB.read_bytes()).hexdigest()
    result = run_integration(
        BUNDLE_PATHS,
        EVIDENCE_PATHS,
        tmp_path,
        run_id="restatement_default_db_immutability",
    )
    assert result["status"] == "passed"
    assert hashlib.sha256(DEFAULT_DB.read_bytes()).hexdigest() == before
