"""Offline integration contract for the Stage 2B-B metric extension."""

from __future__ import annotations

import ast
import hashlib
import json
from decimal import ROUND_HALF_EVEN, Context, Decimal, localcontext
from pathlib import Path

import duckdb
import pytest
from blob_test_helpers import canonical_worktree_blob

from ashare_research.metrics.cashflow_definitions import (
    CashFlowMetricDefinitionRegistry,
)
from ashare_research.metrics.definitions import MetricDefinitionRegistry
from ashare_research.storage.default_db_guard import hash_optional_default_db
from ashare_research.tools.official_cashflow_metric_extension import (
    EXPECTED_2023_TRANSITIONS,
    EXPECTED_LATEST_VALUES,
    STAGE2A_METRIC_RESULT_ID_SET_SHA256,
    STAGE2BA_FACT_ID_SET_SHA256,
    run_cashflow_metric_extension,
)

ROOT = Path(__file__).resolve().parents[1]
BUNDLE_DIR = ROOT / "acceptance" / "fixtures" / "official_facts" / "601857.SH"
EVIDENCE_DIR = ROOT / "acceptance" / "fixtures" / "restatements" / "601857.SH"
BUNDLES = [BUNDLE_DIR / f"{year}_annual.json" for year in range(2021, 2026)]
UPSTREAM_EVIDENCE = [
    EVIDENCE_DIR / f"{year}_reviewed_by_{year + 1}_annual.json"
    for year in range(2021, 2025)
]
SUPPLEMENTAL = [
    BUNDLE_DIR / "supplemental" / f"{year}_capex_cash.json"
    for year in range(2021, 2026)
]
CAPEX_REVIEWS = [
    EVIDENCE_DIR / f"capex_cash_{year}_reviewed_by_{year + 1}.json"
    for year in range(2021, 2025)
]
DEFAULT_DB = ROOT / "data" / "research.duckdb"
DEFAULT_DB_SHA256 = (
    "4a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6"
)
TOOL_PATH = (
    ROOT
    / "src"
    / "ashare_research"
    / "tools"
    / "official_cashflow_metric_extension.py"
)
PROTECTED_BLOBS = {
    "src/ashare_research/tools/official_fact_metric_foundation.py":
        "e30f1a9b00b2ef07384bcc27c68d5df9762f3b23",
    "src/ashare_research/tools/official_capex_cash_fact_foundation.py":
        "08e2745eda9e584232e7c86b611bb02207eb7c35",
    "acceptance/m2_stage2a_petrochina_minimal_transparent_metrics.md":
        "d61b48db73a344a0759572d249a0594ba945f50e",
    "acceptance/m2_stage2ba_petrochina_capex_cash_fact_coverage.md":
        "6f76fb259fb6d1621550fda3e8f7473cf4a69b29",
    "acceptance/fixtures/official_facts/601857.SH/2021_annual.json":
        "cb85f84c3a1459f3a909e36bd6482c8d8124d1a4",
    "acceptance/fixtures/official_facts/601857.SH/2022_annual.json":
        "7076195f3532ead9f0278f97691fe552fdb2ff54",
    "acceptance/fixtures/official_facts/601857.SH/2023_annual.json":
        "6612148ea91b2004605b98e0c8fe799a4d2686ea",
    "acceptance/fixtures/official_facts/601857.SH/2024_annual.json":
        "03a2ec2813c31676aebed20e4df50042f42f140b",
    "acceptance/fixtures/official_facts/601857.SH/2025_annual.json":
        "0ababb5262e6cbf1646e165ccfb3e7bfe2769670",
    "acceptance/fixtures/restatements/601857.SH/"
    "2021_reviewed_by_2022_annual.json":
        "65e25075b91d3d1d15a7761571cca18e931a9f8b",
    "acceptance/fixtures/restatements/601857.SH/"
    "2022_reviewed_by_2023_annual.json":
        "e141a0c4b45994ee7d331d9af874ab0c1d8e20ac",
    "acceptance/fixtures/restatements/601857.SH/"
    "2023_reviewed_by_2024_annual.json":
        "62d8e20cc728b7def157e4fb781918cf12d09e21",
    "acceptance/fixtures/restatements/601857.SH/"
    "2024_reviewed_by_2025_annual.json":
        "8127b566849c811b04f69a180205d0be592738e6",
    "acceptance/fixtures/official_facts/601857.SH/supplemental/"
    "2021_capex_cash.json":
        "400a2d257cefbfada87aa09af3b4259282de30a1",
    "acceptance/fixtures/official_facts/601857.SH/supplemental/"
    "2022_capex_cash.json":
        "dd1a8f8898f3f4e38f9c354a8b7699e867b4d970",
    "acceptance/fixtures/official_facts/601857.SH/supplemental/"
    "2023_capex_cash.json":
        "2dd5eb6e8effe266da9adc64b16e0b4498055243",
    "acceptance/fixtures/official_facts/601857.SH/supplemental/"
    "2024_capex_cash.json":
        "5bb74c2657a231471834606a4984292e7f7184bb",
    "acceptance/fixtures/official_facts/601857.SH/supplemental/"
    "2025_capex_cash.json":
        "8ed3ed8d8fcde927a020a55d113e559ee8e63124",
    "acceptance/fixtures/restatements/601857.SH/"
    "capex_cash_2021_reviewed_by_2022.json":
        "6202af4528b0b9b5c1abd369adb3b8bc4f8015d5",
    "acceptance/fixtures/restatements/601857.SH/"
    "capex_cash_2022_reviewed_by_2023.json":
        "f9c366d34f501778791fb2759a5a136730ccf5da",
    "acceptance/fixtures/restatements/601857.SH/"
    "capex_cash_2023_reviewed_by_2024.json":
        "2928555300850c1c66284c9257e9ee0e4d1cb321",
    "acceptance/fixtures/restatements/601857.SH/"
    "capex_cash_2024_reviewed_by_2025.json":
        "67e667c878608b979e74874bec836298f2b66b94",
}


def _sha256(path: Path) -> str:
    return hash_optional_default_db(path, DEFAULT_DB_SHA256)


def _git_blob(path: Path) -> str:
    return canonical_worktree_blob(path)


def _id_digest(ids: list[str]) -> str:
    payload = json.dumps(sorted(ids), separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()


def _read(run: dict, name: str):
    return json.loads(
        (run["run_directory"] / name).read_text(encoding="utf-8")
    )


def _upstream_db(run: dict) -> Path:
    matches = list(
        (run["run_directory"] / "upstream_capex_cash").rglob(
            "restatement_integration.duckdb"
        )
    )
    assert len(matches) == 1
    return matches[0]


@pytest.fixture(scope="module")
def accepted_run(tmp_path_factory: pytest.TempPathFactory) -> dict:
    default_before = _sha256(DEFAULT_DB)
    result = run_cashflow_metric_extension(
        BUNDLES,
        UPSTREAM_EVIDENCE,
        SUPPLEMENTAL,
        CAPEX_REVIEWS,
        tmp_path_factory.mktemp("cashflow_metric_extension"),
        run_id="cashflow_extension_test",
    )
    assert result["status"] == "passed", result
    assert _sha256(DEFAULT_DB) == default_before == DEFAULT_DB_SHA256
    return result


def test_upstream_and_fixed_metric_counts(accepted_run: dict):
    assert accepted_run["upstream"]["financial_facts"] == 75
    assert accepted_run["upstream"]["latest_pit"] == 20
    assert accepted_run["upstream"]["eligible_facts"] == 25
    assert (
        accepted_run["upstream"]["fact_id_set_sha256"]
        == STAGE2BA_FACT_ID_SET_SHA256
    )
    assert accepted_run["counts"] == {
        "metric_definitions": 6,
        "metric_result_rows": 38,
        "computed_result_versions": 35,
        "insufficient_history_result_versions": 3,
        "metric_result_version_links": 8,
        "metric_lineage_rows": 73,
    }
    assert (
        accepted_run["latest_metric_count"],
        accepted_run["latest_computed"],
        accepted_run["latest_insufficient_history"],
    ) == (30, 27, 3)


def test_metric_pit_snapshots_have_exact_counts(accepted_run: dict):
    assert accepted_run["metric_pit_counts"] == [0, 6, 12, 18, 24, 30]
    assert accepted_run["metric_pit_computed_counts"] == [
        0, 3, 9, 15, 21, 27,
    ]
    assert accepted_run["metric_pit_insufficient_history_counts"] == [
        0, 3, 3, 3, 3, 3,
    ]


def test_six_definitions_are_explicitly_composed(accepted_run: dict):
    definitions = _read(accepted_run, "metric_definitions.json")
    assert len(definitions) == 6
    assert {item["metric_id"] for item in definitions} == {
        *MetricDefinitionRegistry.DEFINITIONS,
        *CashFlowMetricDefinitionRegistry.DEFINITIONS,
    }
    assert len(MetricDefinitionRegistry.list_all()) == 4


def test_new_latest_values_are_derived_from_committed_facts(
    accepted_run: dict,
):
    latest = _read(accepted_run, "latest_metric_snapshot.json")
    new_rows = [
        item
        for item in latest
        if item["metric_id"] in CashFlowMetricDefinitionRegistry.DEFINITIONS
    ]
    assert len(new_rows) == 10
    con = duckdb.connect(str(_upstream_db(accepted_run)), read_only=True)
    try:
        fact_values = {
            row[0]: Decimal(str(row[1]))
            for row in con.execute(
                "SELECT fact_id, value FROM financial_facts"
            ).fetchall()
        }
    finally:
        con.close()
    actual = {}
    with localcontext(Context(prec=28, rounding=ROUND_HALF_EVEN)):
        for row in new_rows:
            inputs = [
                fact_values[fact_id] for fact_id in row["input_fact_ids"]
            ]
            if (
                row["metric_id"]
                == "cash_based_free_cash_flow_proxy"
            ):
                expected = inputs[0] - inputs[1]
            else:
                expected = inputs[0] / inputs[1]
            expected = expected.quantize(
                Decimal("0.000000000001"),
                rounding=ROUND_HALF_EVEN,
            )
            assert row["value"] == str(expected)
            actual[(row["fiscal_year"], row["metric_id"])] = row["value"]
    assert actual == EXPECTED_LATEST_VALUES


def test_only_two_2023_new_version_chains_are_created(accepted_run: dict):
    transitions = _read(
        accepted_run,
        "cashflow_metric_transitions.json",
    )
    assert {
        (item["fiscal_year"], item["metric_id"]) for item in transitions
    } == {
        (2023, "cash_based_free_cash_flow_proxy"),
        (2023, "cash_paid_for_fixed_assets_to_revenue"),
    }
    for transition in transitions:
        before = transition["before"]
        after = transition["after"]
        expected = EXPECTED_2023_TRANSITIONS[transition["metric_id"]]
        assert transition["pit_before_date"] == "2025-03-30"
        assert transition["pit_switch_date"] == "2025-03-31"
        assert before["result_version"] == 1
        assert after["result_version"] == 2
        assert (
            after["supersedes_metric_result_id"]
            == before["metric_result_id"]
        )
        assert tuple(before["input_fact_ids"]) == expected["before_inputs"]
        assert before["value"] == expected["before_value"]
        assert tuple(after["input_fact_ids"]) == expected["after_inputs"]
        assert after["value"] == expected["after_value"]
        assert after["available_at"] == "2025-03-31"


def test_other_years_have_no_new_metric_version_chain(accepted_run: dict):
    versions = _read(accepted_run, "metric_result_versions.json")
    new_versions = [
        item
        for item in versions
        if item["metric_id"] in CashFlowMetricDefinitionRegistry.DEFINITIONS
    ]
    assert len(new_versions) == 12
    assert {
        item["fiscal_year"]
        for item in new_versions
        if item["result_version"] > 1
    } == {2023}
    assert all(
        item["result_version"] == 1
        for item in new_versions
        if item["fiscal_year"] in {2021, 2022, 2024, 2025}
    )


def test_2025_new_metrics_are_not_yet_reviewable(accepted_run: dict):
    latest = _read(accepted_run, "latest_metric_snapshot.json")
    rows = [
        item
        for item in latest
        if item["fiscal_year"] == 2025
        and item["metric_id"] in CashFlowMetricDefinitionRegistry.DEFINITIONS
    ]
    assert len(rows) == 2
    assert {item["status"] for item in rows} == {"computed"}
    assert {item["revision_review_status"] for item in rows} == {
        "not_yet_reviewable"
    }


def test_lineage_uses_only_eligible_reconciled_facts(accepted_run: dict):
    lineage = _read(accepted_run, "metric_lineage.json")
    assert len(lineage) == 73
    ids = {item["input_fact_id"] for item in lineage}
    con = duckdb.connect(str(_upstream_db(accepted_run)), read_only=True)
    try:
        rows = con.execute(
            """SELECT fact_id, source_tier, eligible_for_metrics
               FROM financial_facts
              WHERE fact_id IN (SELECT UNNEST(?))""",
            [list(ids)],
        ).fetchall()
    finally:
        con.close()
    assert len(rows) == len(ids)
    assert all(
        source_tier == "reconciled_derived" and eligible is True
        for _, source_tier, eligible in rows
    )


def test_stage2a_26_results_and_six_chains_are_frozen(accepted_run: dict):
    versions = _read(accepted_run, "metric_result_versions.json")
    old = [
        item
        for item in versions
        if item["metric_id"] in MetricDefinitionRegistry.DEFINITIONS
    ]
    assert len(old) == 26
    assert (
        _id_digest([item["metric_result_id"] for item in old])
        == STAGE2A_METRIC_RESULT_ID_SET_SHA256
        == accepted_run["stage2a_result_id_set_sha256"]
    )
    assert sum(bool(item["supersedes_metric_result_id"]) for item in old) == 6


def test_stage2ba_75_fact_ids_are_frozen(accepted_run: dict):
    con = duckdb.connect(str(_upstream_db(accepted_run)), read_only=True)
    try:
        ids = [
            row[0]
            for row in con.execute(
                "SELECT fact_id FROM financial_facts"
            ).fetchall()
        ]
    finally:
        con.close()
    assert len(ids) == 75
    assert _id_digest(ids) == STAGE2BA_FACT_ID_SET_SHA256


def test_repeated_run_has_identical_ids_values_and_counts(
    accepted_run: dict,
    tmp_path: Path,
):
    repeated = run_cashflow_metric_extension(
        BUNDLES,
        UPSTREAM_EVIDENCE,
        SUPPLEMENTAL,
        CAPEX_REVIEWS,
        tmp_path,
        run_id="cashflow_extension_repeat",
    )
    assert repeated["status"] == "passed"
    first_versions = _read(accepted_run, "metric_result_versions.json")
    second_versions = _read(repeated, "metric_result_versions.json")
    first = {
        item["metric_result_id"]: (
            item["value"],
            item["status"],
            item["input_fact_ids"],
        )
        for item in first_versions
    }
    second = {
        item["metric_result_id"]: (
            item["value"],
            item["status"],
            item["input_fact_ids"],
        )
        for item in second_versions
    }
    assert second == first
    assert repeated["counts"] == accepted_run["counts"]


def test_upstream_duckdb_is_read_only_and_default_db_is_unchanged(
    accepted_run: dict,
):
    assert (
        accepted_run["upstream"]["sha256_before"]
        == accepted_run["upstream"]["sha256_after"]
        == _sha256(_upstream_db(accepted_run))
    )
    assert _sha256(DEFAULT_DB) == DEFAULT_DB_SHA256


def test_offline_boundary_and_output_contract(accepted_run: dict):
    assert accepted_run["offline"] is True
    assert accepted_run["network_access"] is False
    assert accepted_run["pdf_access"] is False
    assert accepted_run["cache_access"] is False
    assert accepted_run["downloaded"] == 0
    expected_files = {
        "upstream_capex_cash",
        "metrics.duckdb",
        "metric_definitions.json",
        "metric_result_versions.json",
        "latest_metric_snapshot.json",
        "metric_pit_snapshots.json",
        "cashflow_metric_transitions.json",
        "metric_lineage.json",
        "gap_inventory.json",
        "run_manifest.json",
        "acceptance_summary.md",
    }
    assert {item.name for item in accepted_run["run_directory"].iterdir()} == (
        expected_files
    )
    manifest_text = (
        accepted_run["run_directory"] / "run_manifest.json"
    ).read_text(encoding="utf-8")
    assert str(ROOT) not in manifest_text
    gaps = _read(accepted_run, "gap_inventory.json")
    names = {item["name"] for item in gaps["items"]}
    assert names == {
        "扣非净利润",
        "毛利率和一般净利率",
        "非经常性损益",
        "ROE / ROA / ROIC",
        "财务安全",
        "分红与回购",
        "估值",
    }
    assert not any("自由现金流" in name or "资本开支强度" in name for name in names)
    con = duckdb.connect(
        str(accepted_run["run_directory"] / "metrics.duckdb"),
        read_only=True,
    )
    try:
        tables = {
            row[0]
            for row in con.execute("SHOW TABLES").fetchall()
        }
    finally:
        con.close()
    assert not any("score" in table.lower() for table in tables)
    assert not any(
        "score" in item.name.lower()
        for item in accepted_run["run_directory"].iterdir()
    )


def test_tool_has_no_network_pdf_or_cache_access_code():
    source = TOOL_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imports = {
        alias.name.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.Import | ast.ImportFrom)
        for alias in (
            node.names
            if isinstance(node, ast.Import)
            else [ast.alias(node.module or "")]
        )
    }
    assert imports.isdisjoint(
        {
            "requests",
            "httpx",
            "urllib",
            "socket",
            "playwright",
            "fitz",
            "pypdf",
            "pdfplumber",
            "pytesseract",
        }
    )
    assert "official-pdfs" not in source
    assert "research.duckdb" not in source


def test_all_protected_inputs_keep_their_frozen_blobs():
    for relative, expected in PROTECTED_BLOBS.items():
        assert _git_blob(ROOT / relative) == expected, relative
