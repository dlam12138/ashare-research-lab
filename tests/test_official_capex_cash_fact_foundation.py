"""Stage 2B-A supplemental evidence and offline integration acceptance."""

from __future__ import annotations

import ast
import hashlib
import json
import shutil
from pathlib import Path

import duckdb
import pytest
from blob_test_helpers import canonical_worktree_blob

from ashare_research.facts.identity import build_fact_id
from ashare_research.storage.default_db_guard import hash_optional_default_db
from ashare_research.tools.official_capex_cash_fact_foundation import (
    CAPEX_CONCEPT,
    UPSTREAM_FACT_ID_SET_SHA256,
    CapexCashFoundationError,
    preflight_capex_restatements,
    preflight_supplemental_evidence,
    run_capex_cash_foundation,
)
from ashare_research.tools.official_fact_metric_foundation import (
    run_metric_foundation,
)

BUNDLES = [
    Path(f"acceptance/fixtures/official_facts/601857.SH/{year}_annual.json")
    for year in range(2021, 2026)
]
UPSTREAM_EVIDENCE = [
    Path(
        "acceptance/fixtures/restatements/601857.SH/"
        f"{year}_reviewed_by_{year + 1}_annual.json"
    )
    for year in range(2021, 2025)
]
SUPPLEMENTAL = [
    Path(
        "acceptance/fixtures/official_facts/601857.SH/supplemental/"
        f"{year}_capex_cash.json"
    )
    for year in range(2021, 2026)
]
CAPEX_REVIEWS = [
    Path(
        "acceptance/fixtures/restatements/601857.SH/"
        f"capex_cash_{year}_reviewed_by_{year + 1}.json"
    )
    for year in range(2021, 2025)
]
DEFAULT_DB = Path("data/research.duckdb")
DEFAULT_DB_SHA256 = (
    "4a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6"
)
METRIC_RESULT_ID_SET_SHA256 = (
    "671249ca0133cfdf45f0146cd795b1badab8a1e3104a27cb535e83826caf0edf"
)
PROTECTED_BLOBS = {
    "src/ashare_research/tools/official_fact_multi_year_integration.py":
        "57a7dbadb8f944fb4062edf93435dbf0c42c2e29",
    "src/ashare_research/tools/official_fact_restatement_integration.py":
        "ee67e2eed45f7e6932c3b9c0b0ece65c8304316f",
    "src/ashare_research/tools/official_fact_metric_foundation.py":
        "e30f1a9b00b2ef07384bcc27c68d5df9762f3b23",
    "acceptance/m2_stage1da_petrochina_2021_2025_multi_year_integration.md":
        "4f648262df97f191b815ccfc5167ef3bb1320aee",
    "acceptance/m2_stage1db_petrochina_restatement_evidence_and_version_chains.md":
        "b350770c33d57367a3a3d82fb6eb1ddb55a2ef2e",
    "acceptance/m2_stage2a_petrochina_minimal_transparent_metrics.md":
        "d61b48db73a344a0759572d249a0594ba945f50e",
}


def _sha256(path: Path) -> str:
    return hash_optional_default_db(path, DEFAULT_DB_SHA256)


def _git_blob(path: Path) -> str:
    return canonical_worktree_blob(path)


def _compact_id_digest(ids: list[str]) -> str:
    payload = json.dumps(sorted(ids), separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()


@pytest.fixture(scope="module")
def preflight():
    supplemental = preflight_supplemental_evidence(
        BUNDLES,
        SUPPLEMENTAL,
        created_at="2026-07-30T13:00:00+08:00",
    )
    restatements = preflight_capex_restatements(
        supplemental,
        CAPEX_REVIEWS,
        BUNDLES,
        created_at="2026-07-30T13:00:00+08:00",
    )
    return supplemental, restatements


@pytest.fixture(scope="module")
def accepted_run(tmp_path_factory):
    root = tmp_path_factory.mktemp("capex_foundation")
    default_hash_before = _sha256(DEFAULT_DB)
    result = run_capex_cash_foundation(
        BUNDLES,
        UPSTREAM_EVIDENCE,
        SUPPLEMENTAL,
        CAPEX_REVIEWS,
        root,
        run_id="capex_acceptance",
    )
    assert _sha256(DEFAULT_DB) == default_hash_before == DEFAULT_DB_SHA256
    return result


def test_supplemental_files_bind_exact_base_bundle_hash_and_blob(preflight):
    supplemental, _ = preflight
    assert len(supplemental["records"]) == 5
    for record in supplemental["records"]:
        evidence = record["evidence"]
        base = Path(evidence["base_bundle_path"])
        assert _sha256(base) == evidence["base_bundle_sha256"]
        assert _git_blob(base) == evidence["base_bundle_git_blob"]


def test_bad_base_binding_fails_before_any_fact_write(tmp_path: Path):
    bad = json.loads(SUPPLEMENTAL[0].read_text(encoding="utf-8"))
    bad["base_bundle_sha256"] = "0" * 64
    bad_path = tmp_path / SUPPLEMENTAL[0].name
    bad_path.write_text(
        json.dumps(bad, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    with pytest.raises(CapexCashFoundationError, match="SHA-256 differs"):
        preflight_supplemental_evidence(
            BUNDLES,
            [bad_path, *SUPPLEMENTAL[1:]],
            created_at="test",
        )
    assert list(tmp_path.glob("*.duckdb")) == []


def test_five_v1_pairs_are_canonical_and_matched(preflight):
    supplemental, _ = preflight
    for record in supplemental["records"]:
        assert record["preflight_result"].status.value == "matched"
        output = record["preflight_result"].output_fact
        assert output is not None and output["fact_id"] == build_fact_id(output)
        for fact in record["source_facts"].values():
            assert fact["fact_id"] == build_fact_id(fact)
            assert fact["concept_id"] == CAPEX_CONCEPT
            assert fact["eligible_for_metrics"] is False


def test_real_reviews_create_only_the_changed_2023_chain(preflight):
    _, restatements = preflight
    assert [
        item["changed"] for item in restatements["comparisons"]
    ] == [False, False, True, False]
    assert restatements["changed_count"] == 1
    pair = restatements["changed_pairs"][0]
    assert pair["target_fiscal_year"] == 2023
    for fact in (pair["company_fact"], pair["exchange_fact"]):
        assert fact["fact_version"] == 2
        assert fact["restatement_version"] == "restated_1"
        assert fact["supersedes_fact_id"]
        assert fact["fact_id"] == build_fact_id(fact)


def test_mismatch_fails_with_no_duckdb_or_partial_write(tmp_path: Path):
    bad_dir = tmp_path / "evidence"
    bad_dir.mkdir()
    copied = []
    for source in SUPPLEMENTAL:
        target = bad_dir / source.name
        shutil.copyfile(source, target)
        copied.append(target)
    bad = json.loads(copied[-1].read_text(encoding="utf-8"))
    bad["exchange"]["raw_value"] = "292788"
    bad["exchange"]["expected_normalized_value"] = 29278800
    copied[-1].write_text(
        json.dumps(bad, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    result = run_capex_cash_foundation(
        BUNDLES,
        UPSTREAM_EVIDENCE,
        copied,
        CAPEX_REVIEWS,
        tmp_path / "output",
        run_id="mismatch",
    )
    assert result["status"] == "failed"
    assert result["transaction_committed"] is False
    assert "company and exchange values differ" in result["error"]
    assert list((tmp_path / "output").rglob("*.duckdb")) == []


def test_integration_counts_pit_lineage_and_version_switch(accepted_run):
    assert accepted_run["status"] == "passed"
    assert accepted_run["transaction_committed"] is True
    assert accepted_run["changed_year_count"] == 1
    assert accepted_run["review_status_2025"] == "not_yet_reviewable"
    assert accepted_run["upstream"] == {
        "status": "passed",
        "financial_facts": 57,
        "latest_pit": 15,
        "fact_id_set_sha256": UPSTREAM_FACT_ID_SET_SHA256,
    }
    assert accepted_run["counts"] == {
        "fact_contexts": 5,
        "upstream_financial_facts": 57,
        "new_company_facts": 6,
        "new_exchange_facts": 6,
        "new_reconciled_facts": 6,
        "company_facts": 25,
        "exchange_facts": 25,
        "raw_facts": 50,
        "reconciled_facts": 25,
        "financial_facts": 75,
        "eligible_for_metrics": 25,
        "version_chain_links": 15,
        "lineage": 75,
        "audit": 75,
    }
    assert accepted_run["latest_pit_snapshot"]["count"] == 20
    transition = json.loads(
        (
            accepted_run["run_directory"] / "pit_transitions.json"
        ).read_text(encoding="utf-8")
    )
    assert len(transition) == 1
    assert transition[0]["before_date"] == "2025-03-30"
    assert transition[0]["on_date"] == "2025-03-31"
    assert transition[0]["supersedes_fact_id"] == transition[0]["before_fact_id"]


def test_upstream_57_ids_and_base_three_concept_pit_are_unchanged(accepted_run):
    db = (
        accepted_run["run_directory"]
        / "upstream_restatement"
        / "restatement_integration.duckdb"
    )
    conn = duckdb.connect(str(db), read_only=True)
    upstream_ids = [
        row[0]
        for row in conn.execute(
            "SELECT fact_id FROM financial_facts WHERE concept_id <> ?",
            [CAPEX_CONCEPT],
        ).fetchall()
    ]
    assert len(upstream_ids) == 57
    assert _compact_id_digest(upstream_ids) == UPSTREAM_FACT_ID_SET_SHA256
    assert conn.execute(
        """SELECT COUNT(*) FROM fact_lineage
            WHERE reconciliation_rule_id='RECON_OFFICIAL_NUMERIC_001'"""
    ).fetchone()[0] == 57
    assert conn.execute(
        """SELECT COUNT(*) FROM fact_lineage
            WHERE reconciliation_rule_id='RECON_OFFICIAL_NUMERIC_002'"""
    ).fetchone()[0] == 18
    conn.close()


def test_repeated_run_has_identical_new_fact_ids(tmp_path: Path, accepted_run):
    repeated = run_capex_cash_foundation(
        BUNDLES,
        UPSTREAM_EVIDENCE,
        SUPPLEMENTAL,
        CAPEX_REVIEWS,
        tmp_path,
        run_id="repeated",
    )
    assert repeated["status"] == "passed"
    assert (
        repeated["new_v1_reconciled_fact_ids"]
        == accepted_run["new_v1_reconciled_fact_ids"]
    )
    assert (
        repeated["new_v2_reconciled_fact_ids"]
        == accepted_run["new_v2_reconciled_fact_ids"]
    )


def test_tool_has_no_network_pdf_metric_or_score_behavior(accepted_run):
    source_path = Path(
        "src/ashare_research/tools/official_capex_cash_fact_foundation.py"
    )
    tree = ast.parse(source_path.read_text(encoding="utf-8"))
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
        {"requests", "httpx", "urllib", "socket", "pdfplumber", "pypdf"}
    )
    output_names = {
        path.name.lower()
        for path in accepted_run["run_directory"].rglob("*")
        if path.is_file()
    }
    assert not any("metric" in name or "score" in name for name in output_names)


def test_stage2a_all_metric_result_ids_are_frozen(tmp_path: Path):
    metric = run_metric_foundation(
        BUNDLES,
        UPSTREAM_EVIDENCE,
        tmp_path,
        run_id="metric_regression",
    )
    assert metric["status"] == "passed"
    rows = json.loads(
        (
            metric["run_directory"] / "metric_result_versions.json"
        ).read_text(encoding="utf-8")
    )
    ids = [row["metric_result_id"] for row in rows]
    assert len(ids) == 26
    assert _compact_id_digest(ids) == METRIC_RESULT_ID_SET_SHA256


def test_protected_tools_reports_and_registered_evidence_are_unchanged():
    for path, expected_blob in PROTECTED_BLOBS.items():
        assert _git_blob(Path(path)) == expected_blob
    assert [_git_blob(path) for path in BUNDLES] == [
        "cb85f84c3a1459f3a909e36bd6482c8d8124d1a4",
        "7076195f3532ead9f0278f97691fe552fdb2ff54",
        "6612148ea91b2004605b98e0c8fe799a4d2686ea",
        "03a2ec2813c31676aebed20e4df50042f42f140b",
        "0ababb5262e6cbf1646e165ccfb3e7bfe2769670",
    ]
    assert [_git_blob(path) for path in UPSTREAM_EVIDENCE] == [
        "65e25075b91d3d1d15a7761571cca18e931a9f8b",
        "e141a0c4b45994ee7d331d9af874ab0c1d8e20ac",
        "62d8e20cc728b7def157e4fb781918cf12d09e21",
        "8127b566849c811b04f69a180205d0be592738e6",
    ]
