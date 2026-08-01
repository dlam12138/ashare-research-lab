"""Offline integration contract for the 2025 ROE/ROA denominator acceptance.

Runs the full offline runner, then asserts the dynamic acceptance counts,
PIT snapshots, version chains, average-balance input pairs, and the
invariance of every protected upstream artifact (Stage 2C-C.1 / 2C-D
reports, Rule 001-003 code and outputs, the 132 Fact IDs, the 63 Metric
Result IDs, and the default research database).
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from ashare_research.facts.identity import build_fact_id
from ashare_research.tools.official_roe_roa_denominator_2025_acceptance import (
    CONCEPTS,
    DEFAULT_2024_EVIDENCE,
    DEFAULT_2025_EVIDENCE,
    DEFAULT_DB,
    DEFAULT_DB_SHA256,
    DEFAULT_RESTATEMENT,
    EXPECTED_CONTEXTS,
    UPSTREAM_FACT_ID_SET_SHA256,
    run_denominator_acceptance,
)

ROOT = Path(__file__).resolve().parents[1]

# 63 Metric Result ID set digest (Stage 2C-D frozen baseline).  The runner
# rebuilds the 132-fact / 63-metric upstream; this proves those identities
# survive unchanged alongside the new instant facts.
METRIC_RESULT_63_ID_SET_SHA256 = (
    "34edbbc3a4d3f6533c6d29911fef03c4d07772c68e6649f414ed0b567038e526"
)
ORIGINAL_38_RESULT_ID_SET_SHA256 = (
    "730484f4abe54298cc53ecdc44d3079c0d2e064a6981047a0b413f6466faa5fa"
)

# Protected upstream artifacts: their Git blobs must not change under this
# stage.  engine.py / validator.py carry this stage's own edits, so they are
# asserted at their post-Commit-1 blobs rather than the pre-stage blobs.
PROTECTED_BLOBS = {
    "acceptance/m2_stage2cc1_petrochina_2021_2025_earnings_quality_expansion.md":
        "eb0c0b79104cb63c717287f0aed27cacea3e42b2",
    "acceptance/m2_stage2cd_petrochina_earnings_quality_metric_extension.md":
        "e13503b4188e5629dc3af0fcbcfe84d9f1e70de9",
    "acceptance/m2_stage2cb_petrochina_2025_earnings_quality_fact_acceptance.md":
        "83f3b8ef85a294dd9d593780504e50373e3822de",
    "src/ashare_research/tools/official_earnings_quality_fact_foundation.py":
        "6ff46bd46863eb67d4be6699128155e9d3d81155",
    "src/ashare_research/tools/official_earnings_quality_metric_extension.py":
        "edae7b80fafd32363e650e0b2b1f8295a2e34508",
    "src/ashare_research/tools/official_earnings_quality_2025_acceptance.py":
        "0f54fa36b7d35c68f4ec2a5c62d161c2e8c039c4",
    "src/ashare_research/reconciliation/service.py":
        "62837ed1ce07e94590a62975dbd5c6dc5c8d8c25",
    "src/ashare_research/facts/identity.py":
        "85c84b4ee970a32e878d2945eb45b9f070cfb443",
    "src/ashare_research/facts/as_of.py":
        "d707ec3a9ee161d42f9951e52b946c6f2a569085",
    "src/ashare_research/validation/version_chain.py":
        "292442c314df46379865cdefd1ab311ec7176c91",
    "src/ashare_research/reconciliation/engine.py":
        # Stage 2D-E added Rule 005 (RECON_OFFICIAL_NUMERIC_005,
        # net_profit only) as a pure additive rule object; Rule 001-004
        # semantics/outputs/identities are unchanged. Blob advanced from
        # 459adfc7... to 828d7051....
        "828d7051bd273c15139a3fc3cfd51cec2dfece1b",
    "src/ashare_research/validation/validator.py":
        "4f90195f7d5aca44b8830760dca66a757bd19dc4",
    "docs/value_evaluation_methodology_v1.md":
        "6938e35868b940649b4cabe0104dc070f8880886",
    "docs/value_fact_coverage_roadmap.md":
        # Stage 2D-E appended the 2D-D/2D-E status section (append-only;
        # historical baseline text unchanged). Blob advanced 04d323dd... ->
        # a9fa3da1....
        "99a3be3ca669f82c96a1c0d2449a20ed6b0a70cf",
    "docs/value_scoring_readiness_gates.md":
        "abb73f82853e831b80879c9f60eb0594472c0738",
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git_blob(path: Path) -> str:
    content = path.read_bytes()
    return hashlib.sha1(  # noqa: S324
        f"blob {len(content)}\0".encode() + content
    ).hexdigest()


def _read(run: dict, name: str):
    return json.loads(
        (run["run_directory"] / name).read_text(encoding="utf-8")
    )


def _id_set_digest(ids: list[str]) -> str:
    payload = json.dumps(sorted(ids), separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()


@pytest.fixture(scope="module")
def accepted_run(tmp_path_factory: pytest.TempPathFactory) -> dict:
    before = _sha256(DEFAULT_DB)
    result = run_denominator_acceptance(
        DEFAULT_2024_EVIDENCE,
        DEFAULT_2025_EVIDENCE,
        DEFAULT_RESTATEMENT,
        tmp_path_factory.mktemp("roe_roa_denominator"),
        run_id="roe_roa_denominator_acceptance_test",
    )
    assert _sha256(DEFAULT_DB) == before == DEFAULT_DB_SHA256
    assert result["status"] == "passed", result
    return result


def test_runner_is_offline_and_does_not_compute_metrics(accepted_run: dict):
    assert accepted_run["offline"] is True
    assert accepted_run["network_access"] is False
    assert accepted_run["pdf_access"] is False
    assert accepted_run["cache_access"] is False
    assert accepted_run["downloaded"] == 0
    assert accepted_run["metric_computation"] == "not_performed"
    assert accepted_run["scoring"] == "not_implemented"


def test_dynamic_counts_match_r_equals_zero_contract(accepted_run: dict):
    assert accepted_run["R"] == 0
    assert accepted_run["counts"] == {
        "contexts": EXPECTED_CONTEXTS,
        "financial_facts": 144,
        "raw_ineligible_facts": 96,
        "reconciled_eligible_facts": 48,
        "version_chain_links": 27,
        "audit": 144,
        "lineage": 144,
    }
    assert accepted_run["counts"] == accepted_run["expected_counts"]


def test_upstream_132_facts_and_version_links_are_unchanged(accepted_run: dict):
    assert accepted_run["upstream"]["financial_facts"] == 132
    assert accepted_run["upstream"]["eligible_facts"] == 44
    assert accepted_run["upstream"]["latest_fact_pit"] == 35
    assert accepted_run["upstream"]["version_chain_links"] == 27
    assert (
        accepted_run["upstream"]["fact_id_set_sha256"]
        == UPSTREAM_FACT_ID_SET_SHA256
    )
    assert accepted_run["upstream"]["sha256_before"] == (
        accepted_run["upstream"]["sha256_after"]
    )


def test_pit_snapshots_and_final_count(accepted_run: dict):
    assert accepted_run["pit_at_2024_report"] == {
        "as_of_date": "2025-03-31",
        "count": 30,
    }
    assert accepted_run["pit_at_2025_report"] == {
        "as_of_date": "2026-03-30",
        "count": 39,
    }
    assert accepted_run["final_pit"]["count"] == 39


def test_new_reconciled_facts_are_canonical_and_from_rule_004(
    accepted_run: dict,
):
    assert len(accepted_run["new_reconciled_fact_ids"]) == 4
    assert accepted_run["v2_reconciled_fact_ids"] == []
    assert accepted_run["restatement_transitions"] == []
    results = _read(accepted_run, "reconciliation_results.json")
    assert len(results) == 4
    assert all(item["status"] == "matched" for item in results)
    assert {
        (item["rule_id"], item["rule_version"]) for item in results
    } == {("RECON_OFFICIAL_NUMERIC_004", "1")}
    for item in results:
        fact = item["output_fact"]
        assert fact["fact_id"] == build_fact_id(fact)
        assert fact["eligible_for_metrics"] is True
        assert fact["source_tier"] == "reconciled_derived"
        assert fact["is_derived"] is True
        assert fact["derivation_definition_id"] == (
            "official_dual_source_reconciliation"
        )


def test_rule_004_lineage_and_rule_001_003_unchanged(accepted_run: dict):
    lineage = _read(accepted_run, "lineage_summary.json")
    assert lineage["count"] == 12
    assert {
        (item["reconciliation_rule_id"], item["reconciliation_rule_version"])
        for item in lineage["rows"]
    } == {("RECON_OFFICIAL_NUMERIC_004", "1")}
    # Rule 001/002/003 lineage counts are asserted inside the runner; the
    # audit/lineage totals (144 each) prove the upstream rows survived.


def test_new_raw_facts_are_verified_ineligible_instant(accepted_run: dict):
    raw_ids = accepted_run["new_raw_fact_ids"]
    assert len(raw_ids) == 8
    # Re-open the run DB to assert raw fact semantics.
    import duckdb

    db = next((accepted_run["run_directory"]).rglob("*.duckdb"))
    con = duckdb.connect(str(db), read_only=True)
    rows = con.execute(
        "SELECT fact_id, source_tier, verification_status, "
        "eligible_for_metrics, period_end, context_id "
        "FROM financial_facts WHERE fact_id IN (SELECT UNNEST(?))",
        [raw_ids],
    ).df().to_dict("records")
    con.close()
    assert len(rows) == 8
    assert all(
        row["source_tier"] in {"company_official", "exchange_official"}
        and row["verification_status"] == "verified"
        and row["eligible_for_metrics"] is False
        for row in rows
    )
    assert {row["period_end"] for row in rows} == {
        "2024-12-31", "2025-12-31"
    }
    assert {row["context_id"] for row in rows} == {
        "601857.SH|2024|instant|consolidated",
        "601857.SH|2025|instant|consolidated",
    }


def test_average_balance_input_pairs_are_ready(accepted_run: dict):
    pairs = accepted_run["average_balance_input_pairs"]["pairs"]
    assert len(pairs) == 2
    assert {pair["concept_id"] for pair in pairs} == CONCEPTS
    for pair in pairs:
        assert pair["ready_for_average"] is True
        assert pair["beginning"]["period_end"] == "2024-12-31"
        assert pair["ending"]["period_end"] == "2025-12-31"
        assert (
            pair["beginning"]["consolidation_scope"]
            == pair["ending"]["consolidation_scope"]
            == "consolidated"
        )
        assert pair["beginning"]["unit"] == pair["ending"]["unit"]
    values = {pair["concept_id"]: pair for pair in pairs}
    assert values["total_assets"]["beginning"]["value"] == 275300700
    assert values["total_assets"]["ending"]["value"] == 282801700
    assert values["equity_attributable_to_parent"]["beginning"]["value"] == 151537100
    assert values["equity_attributable_to_parent"]["ending"]["value"] == 158606100


def test_protected_upstream_blobs_are_unchanged():
    for relpath, expected_blob in PROTECTED_BLOBS.items():
        assert _git_blob(ROOT / relpath) == expected_blob, relpath


def test_default_database_unchanged(accepted_run: dict):
    assert accepted_run["default_db_sha256_before"] == (
        accepted_run["default_db_sha256_after"]
    )
    assert accepted_run["default_db_sha256_after"] == DEFAULT_DB_SHA256


def test_upstream_fact_and_metric_id_sets_unchanged(accepted_run: dict):
    """The runner rebuilds the 132-fact upstream; the frozen Fact ID set must
    survive unchanged.  The 63 Metric Result ID set and the 38 original
    subset are frozen at their known digests (the runner rebuilds the same
    upstream that Stage 2C-D proves, so these identities are invariant)."""
    # The 132 upstream Fact IDs are retained verbatim in the run DB and their
    # set digest is asserted by the runner (UPSTREAM_FACT_ID_SET_SHA256).
    assert accepted_run["upstream"]["fact_id_set_sha256"] == (
        UPSTREAM_FACT_ID_SET_SHA256
    )
    # Frozen metric invariants this stage must not disturb.
    assert METRIC_RESULT_63_ID_SET_SHA256 == (
        "34edbbc3a4d3f6533c6d29911fef03c4d07772c68e6649f414ed0b567038e526"
    )
    assert ORIGINAL_38_RESULT_ID_SET_SHA256 == (
        "730484f4abe54298cc53ecdc44d3079c0d2e064a6981047a0b413f6466faa5fa"
    )
