"""Offline integration contract for the 2025 earnings-quality acceptance."""

from __future__ import annotations

import ast
import json
import shutil
from pathlib import Path

import duckdb
import pytest
from blob_test_helpers import canonical_worktree_blob

from ashare_research.facts.identity import build_fact_id
from ashare_research.storage.default_db_guard import hash_optional_default_db
from ashare_research.tools.official_earnings_quality_2025_acceptance import (
    CONCEPTS,
    DEFAULT_DB,
    DEFAULT_DB_SHA256,
    DEFAULT_EVIDENCE,
    EXPECTED_COUNTS,
    METRIC_RESULT_COUNT,
    METRIC_RESULT_ID_SET_SHA256,
    STAGE2BA_FACT_ID_SET_SHA256,
    EarningsQualityAcceptanceError,
    run_earnings_quality_acceptance,
)

ROOT = Path(__file__).resolve().parents[1]
TOOL = (
    ROOT
    / "src"
    / "ashare_research"
    / "tools"
    / "official_earnings_quality_2025_acceptance.py"
)
PROTECTED_BLOBS = {
    "src/ashare_research/reconciliation/service.py":
        "62837ed1ce07e94590a62975dbd5c6dc5c8d8c25",
    "src/ashare_research/facts/identity.py":
        "85c84b4ee970a32e878d2945eb45b9f070cfb443",
    "src/ashare_research/facts/as_of.py":
        "d707ec3a9ee161d42f9951e52b946c6f2a569085",
    "src/ashare_research/validation/version_chain.py":
        "292442c314df46379865cdefd1ab311ec7176c91",
    "src/ashare_research/tools/official_capex_cash_fact_foundation.py":
        "08e2745eda9e584232e7c86b611bb02207eb7c35",
    "src/ashare_research/tools/official_fact_metric_foundation.py":
        "e30f1a9b00b2ef07384bcc27c68d5df9762f3b23",
    "src/ashare_research/tools/official_cashflow_metric_extension.py":
        "66e6b97a5adf1530551dbd835cf81b30594204ce",
    "acceptance/m2_stage2ba_petrochina_capex_cash_fact_coverage.md":
        "6f76fb259fb6d1621550fda3e8f7473cf4a69b29",
    "acceptance/m2_stage2bb_petrochina_cashflow_metric_extension.md":
        "1e6ae316c8a79b0a48deaa2b2316b17f559f543e",
    "docs/value_evaluation_methodology_v1.md":
        "6938e35868b940649b4cabe0104dc070f8880886",
    "config/value_evaluation_methodology_v1.json":
        "9a36c28a96a690c52d46acede3ff95bfe907cb33",
    "docs/value_fact_coverage_roadmap.md":
        # Stage 2D-E appended the 2D-D/2D-E status section, then Stage 2J and
        # Stage 2K appended their status sections (append-only; historical
        # baseline text unchanged). Blob advanced 04d323dd... -> a9fa3da1...
        # -> ... -> 0cd48fa1....
        "0cd48fa16dcc5d431b1efce1433c9c7d89d0642a",
    "docs/value_scoring_readiness_gates.md":
        "abb73f82853e831b80879c9f60eb0594472c0738",
    "tests/test_value_evaluation_methodology.py":
        # Cascade: Stage 2D-D closure advanced engine.py blob; this file's
        # engine.py blob ref was updated, advancing its own blob to 6f4c3efd.
        # Stage 2D-F updated the protected engine reference only; this
        # cascade test now points to the current protected test blob.
        "6c2617cba1b6eb580112173b702ad88ca9efe3ab",
    "acceptance/m2_stage2ca_value_evaluation_methodology_baseline.md":
        "2d9bce7dfe6842682567326468b59b12077299b4",
    "acceptance/fixtures/official_facts/601857.SH/2025_annual.json":
        "0ababb5262e6cbf1646e165ccfb3e7bfe2769670",
}


def _sha256(path: Path) -> str:
    return hash_optional_default_db(path, DEFAULT_DB_SHA256)


def _git_blob(path: Path) -> str:
    return canonical_worktree_blob(path)


def _read(run: dict, name: str):
    return json.loads(
        (run["run_directory"] / name).read_text(encoding="utf-8")
    )


@pytest.fixture(scope="module")
def accepted_run(tmp_path_factory: pytest.TempPathFactory) -> dict:
    before = _sha256(DEFAULT_DB)
    result = run_earnings_quality_acceptance(
        DEFAULT_EVIDENCE,
        tmp_path_factory.mktemp("earnings_quality"),
        run_id="earnings_quality_acceptance_test",
    )
    assert _sha256(DEFAULT_DB) == before == DEFAULT_DB_SHA256
    assert result["status"] == "passed", result
    return result


def test_fixed_counts_and_three_matches(accepted_run: dict):
    assert accepted_run["transaction_committed"] is True
    assert accepted_run["upstream"] == {
        "status": "passed",
        "financial_facts": 75,
        "latest_pit": 20,
        "fact_id_set_sha256": STAGE2BA_FACT_ID_SET_SHA256,
    }
    assert accepted_run["counts"] == EXPECTED_COUNTS
    assert accepted_run["reconciliation_statuses"] == [
        "matched",
        "matched",
        "matched",
    ]
    assert len(accepted_run["new_raw_fact_ids"]) == 6
    assert len(accepted_run["new_reconciled_fact_ids"]) == 3


def test_new_facts_are_canonical_and_values_come_from_evidence(
    accepted_run: dict,
):
    evidence = json.loads(DEFAULT_EVIDENCE.read_text(encoding="utf-8"))
    expected = {
        item["concept_id"]: item["expected_normalized_value"]
        for item in evidence["sources"]["company"]["facts"]
    }
    facts = _read(accepted_run, "new_facts.json")
    assert len(facts) == 9
    assert {item["concept_id"] for item in facts} == CONCEPTS
    for item in facts:
        assert item["fact_id"] == build_fact_id(item)
        assert int(item["value"]) == expected[item["concept_id"]]
        assert int(item["fact_version"]) == 1
        assert item["restatement_version"] == "original"
        assert not item["supersedes_fact_id"]
    reconciled = [
        item for item in facts
        if item["source_tier"] == "reconciled_derived"
    ]
    assert {item["fact_id"] for item in reconciled} == set(
        accepted_run["new_reconciled_fact_ids"]
    )
    assert all(item["eligible_for_metrics"] is True for item in reconciled)
    raw = [
        item for item in facts
        if item["source_tier"] in {"company_official", "exchange_official"}
    ]
    assert all(item["eligible_for_metrics"] is False for item in raw)


def test_pit_before_on_and_final_snapshot(accepted_run: dict):
    assert accepted_run["before_pit"] == {
        "as_of_date": "2026-03-29",
        "count": 0,
    }
    assert accepted_run["on_pit"]["as_of_date"] == "2026-03-30"
    assert accepted_run["on_pit"]["count"] == 3
    assert accepted_run["final_pit"]["count"] == 23
    assert accepted_run["final_pit"]["per_year"] == {
        2021: 4,
        2022: 4,
        2023: 4,
        2024: 4,
        2025: 7,
    }


def test_audit_lineage_and_no_new_version_chain(accepted_run: dict):
    assert accepted_run["counts"]["audit"] == 84
    assert accepted_run["counts"]["lineage"] == 84
    assert accepted_run["counts"]["version_chain_links"] == 15
    lineage = _read(accepted_run, "lineage_summary.json")
    assert lineage["count"] == 9
    assert {
        (item["reconciliation_rule_id"], item["reconciliation_rule_version"])
        for item in lineage["rows"]
    } == {("RECON_OFFICIAL_NUMERIC_003", "1")}


def test_2025_revision_status_and_bridge_are_recorded(accepted_run: dict):
    manifest = _read(accepted_run, "run_manifest.json")
    evidence_manifest = _read(accepted_run, "evidence_manifest.json")
    assert manifest["revision_review_status"] == "not_yet_reviewable"
    assert manifest["bridge_status"] == "reconciled"
    assert evidence_manifest["revision_review_status"] == "not_yet_reviewable"
    assert evidence_manifest["bridge_status"] == "reconciled"


def test_original_fact_and_metric_result_ids_are_frozen(accepted_run: dict):
    assert (
        accepted_run["upstream"]["fact_id_set_sha256"]
        == STAGE2BA_FACT_ID_SET_SHA256
        == "7787dad8be434ba04ad9ae3f19855a9e5f85333faa595466a95e6e1afb8d10a1"
    )
    assert accepted_run["frozen_metric_results"] == {
        "count": METRIC_RESULT_COUNT,
        "id_set_sha256": METRIC_RESULT_ID_SET_SHA256,
        "stage2a_id_set_sha256": (
            "671249ca0133cfdf45f0146cd795b1badab8a1e3104a27cb535e83826caf0edf"
        ),
        "artifacts_accessed": False,
    }
    assert METRIC_RESULT_ID_SET_SHA256 == (
        "730484f4abe54298cc53ecdc44d3079c0d2e064a6981047a0b413f6466faa5fa"
    )


def test_repeated_run_has_identical_new_fact_ids(
    accepted_run: dict,
    tmp_path: Path,
):
    repeated = run_earnings_quality_acceptance(
        DEFAULT_EVIDENCE,
        tmp_path,
        run_id="earnings_quality_repeat",
    )
    assert repeated["status"] == "passed"
    assert repeated["new_raw_fact_ids"] == accepted_run["new_raw_fact_ids"]
    assert (
        repeated["new_reconciled_fact_ids"]
        == accepted_run["new_reconciled_fact_ids"]
    )
    assert repeated["counts"] == accepted_run["counts"]


def test_mismatch_stops_before_any_duckdb_write(tmp_path: Path):
    bad = json.loads(DEFAULT_EVIDENCE.read_text(encoding="utf-8"))
    exchange = bad["sources"]["exchange"]["facts"]
    target = next(
        item for item in exchange if item["concept_id"] == "operating_profit"
    )
    target["raw_value"] = str(int(target["raw_value"]) + 1)
    target["expected_normalized_value"] += 100
    bad_path = tmp_path / "bad_evidence.json"
    bad_path.write_text(
        json.dumps(bad, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    result = run_earnings_quality_acceptance(
        bad_path,
        tmp_path / "output",
        run_id="mismatch",
    )
    assert result["status"] == "failed"
    assert result["transaction_committed"] is False
    assert "company and exchange values differ" in result["error"]
    assert list((tmp_path / "output").rglob("*.duckdb")) == []


def test_runner_is_strictly_offline_and_emits_no_metric_or_score(
    accepted_run: dict,
):
    manifest = _read(accepted_run, "run_manifest.json")
    assert manifest["offline"] is True
    assert manifest["network_access"] is False
    assert manifest["pdf_access"] is False
    assert manifest["cache_access"] is False
    assert manifest["downloaded"] == 0
    tree = ast.parse(TOOL.read_text(encoding="utf-8"))
    imported_roots = {
        alias.name.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.Import | ast.ImportFrom)
        for alias in (
            node.names
            if isinstance(node, ast.Import)
            else [ast.alias(node.module or "")]
        )
    }
    assert imported_roots.isdisjoint(
        {
            "requests",
            "httpx",
            "urllib",
            "socket",
            "pdfplumber",
            "pypdf",
            "fitz",
        }
    )
    top_level_files = {
        path.name.lower()
        for path in accepted_run["run_directory"].iterdir()
        if path.is_file()
    }
    assert not any("metric" in name or "score" in name for name in top_level_files)


def test_default_db_and_run_scoped_database_boundary(accepted_run: dict):
    assert (
        accepted_run["default_db_sha256_before"]
        == accepted_run["default_db_sha256_after"]
        == _sha256(DEFAULT_DB)
        == DEFAULT_DB_SHA256
    )
    dbs = list(accepted_run["run_directory"].rglob("*.duckdb"))
    assert len(dbs) == 1
    conn = duckdb.connect(str(dbs[0]), read_only=True)
    try:
        assert conn.execute(
            "SELECT COUNT(*) FROM financial_facts"
        ).fetchone()[0] == 84
    finally:
        conn.close()


def test_protected_runners_reports_methodology_and_bundle_are_unchanged():
    for relative, expected_blob in PROTECTED_BLOBS.items():
        assert _git_blob(ROOT / relative) == expected_blob, relative


def test_failure_cleanup_does_not_touch_committed_evidence(tmp_path: Path):
    copy_path = tmp_path / DEFAULT_EVIDENCE.name
    shutil.copyfile(DEFAULT_EVIDENCE, copy_path)
    before = _sha256(copy_path)
    with pytest.raises(EarningsQualityAcceptanceError):
        from ashare_research.tools.official_earnings_quality_2025_acceptance import (
            preflight_evidence,
        )

        bad = json.loads(copy_path.read_text(encoding="utf-8"))
        bad["base_bundle_sha256"] = "0" * 64
        copy_path.write_text(
            json.dumps(bad, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        preflight_evidence(copy_path, created_at="test")
    assert _sha256(DEFAULT_EVIDENCE) != _sha256(copy_path)
    assert before == _sha256(DEFAULT_EVIDENCE)
