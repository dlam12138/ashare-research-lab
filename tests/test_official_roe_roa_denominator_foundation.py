"""Offline integration contract for the 2020-2025 ROE/ROA denominator foundation.

Runs the full offline runner, then asserts the dynamic acceptance counts
(R = 4: 180 facts / 11 contexts), the annual PIT snapshots (11/20/29/38/47),
the four v2 restatement transitions with stable source_id, the ten
average-balance input pairs (including the 2020 opening baseline), and the
invariance of every protected upstream artifact (Stage 2C/2D-A reports and
runners, Rule 001-004 code, the 132 Fact IDs, the 63 Metric Result IDs, the
2024/2025 evidence, and the default research database).
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from ashare_research.facts.identity import build_fact_id
from ashare_research.tools.official_roe_roa_denominator_foundation import (
    CONCEPTS,
    DEFAULT_DB,
    DEFAULT_DB_SHA256,
    EXPECTED_ANNUAL_PIT,
    EXPECTED_CONTEXTS,
    EXPECTED_R,
    UPSTREAM_FACT_ID_SET_SHA256,
    YEARS,
    run_denominator_foundation,
)

ROOT = Path(__file__).resolve().parents[1]

# 63 Metric Result / 38 original Result ID set digests (Stage 2C-D frozen
# baseline).  The runner rebuilds the 132-fact / 63-metric upstream; these
# prove those identities survive unchanged alongside the new instant facts.
METRIC_RESULT_63_ID_SET_SHA256 = (
    "34edbbc3a4d3f6533c6d29911fef03c4d07772c68e6649f414ed0b567038e526"
)
ORIGINAL_38_RESULT_ID_SET_SHA256 = (
    "730484f4abe54298cc53ecdc44d3079c0d2e064a6981047a0b413f6466faa5fa"
)

# Protected artifacts: their Git blobs must not change under this stage.
# Includes the Stage 2C/2D-A upstream (carried verbatim from the 2D-A test),
# the Stage 2D-A runner/report/evidence (2D-B must not alter them), and this
# stage's own new runner/report/evidence/restatements at their final blobs.
PROTECTED_BLOBS = {
    # --- Stage 2C upstream (carried from 2D-A test) ---
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
        "459adfc7506d02c8a04935fa1f110e497748ac87",
    "src/ashare_research/validation/validator.py":
        "4f90195f7d5aca44b8830760dca66a757bd19dc4",
    "docs/value_evaluation_methodology_v1.md":
        "6938e35868b940649b4cabe0104dc070f8880886",
    "docs/value_fact_coverage_roadmap.md":
        "9d737e00d36e711a93c9cad001c5343829de0de9",
    "docs/value_scoring_readiness_gates.md":
        "abb73f82853e831b80879c9f60eb0594472c0738",
    # --- Stage 2D-A artifacts (unchanged by 2D-B) ---
    "src/ashare_research/tools/official_roe_roa_denominator_2025_acceptance.py":
        "8d3ab73a9e7a1c221c6ea434a7012cab669cd62e",
    "acceptance/m2_stage2da_petrochina_2025_roe_roa_denominator_facts.md":
        "2b9b06d45c270d762a8b3071e43fb5960ab50a6f",
    "acceptance/fixtures/official_facts/601857.SH/supplemental/2024_roe_roa_denominators.json":
        "a3ac548347addf54954798c6e3e45a3df708341a",
    "acceptance/fixtures/official_facts/601857.SH/supplemental/2025_roe_roa_denominators.json":
        "6225087821b173eb59debf485ed1619a0c62c22d",
    "acceptance/fixtures/restatements/601857.SH/roe_roa_denominators_2024_reviewed_by_2025.json":
        "868fac3598cda017e3f0f4ef3f2d249c2efa2f24",
    # --- Stage 2D-B artifacts (this stage) ---
    "src/ashare_research/tools/official_roe_roa_denominator_foundation.py":
        "959fee5702b6d86b41e679815a3514691052f560",
    "acceptance/m2_stage2db_petrochina_2020_2025_roe_roa_denominator_expansion.md":
        "52c874584a46995e106d07e1ac692c4b3e51cee7",
    "acceptance/fixtures/official_facts/601857.SH/supplemental/2020_opening_roe_roa_denominators_from_2021.json":
        "c02fb3ad88d2f6a78c5ce28504751c119932a345",
    "acceptance/fixtures/official_facts/601857.SH/supplemental/2021_roe_roa_denominators.json":
        "410ed40578abeb7da6cb2d79bc676739be3a8ec8",
    "acceptance/fixtures/official_facts/601857.SH/supplemental/2022_roe_roa_denominators.json":
        "5fb0e9b403b86b042e79347dbbe60d49ebf5e416",
    "acceptance/fixtures/official_facts/601857.SH/supplemental/2023_roe_roa_denominators.json":
        "cd11b488578ea24c20f5c0b96eb09712eae6d1d2",
    "acceptance/fixtures/restatements/601857.SH/roe_roa_denominators_2021_reviewed_by_2022.json":
        "d105b097cfceb4f0c07ce1dc7c723103ff0e2c6e",
    "acceptance/fixtures/restatements/601857.SH/roe_roa_denominators_2022_reviewed_by_2023.json":
        "fb0308a5c260e50dd397f393e5b9425ff48a419e",
    "acceptance/fixtures/restatements/601857.SH/roe_roa_denominators_2023_reviewed_by_2024.json":
        "8552ad816eeee3335c84c662f7e1f4be16c044f7",
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


@pytest.fixture(scope="module")
def accepted_run(tmp_path_factory: pytest.TempPathFactory) -> dict:
    before = _sha256(DEFAULT_DB)
    result = run_denominator_foundation(
        tmp_path_factory.mktemp("roe_roa_denominator_foundation"),
        run_id="roe_roa_denominator_foundation_test",
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


def test_dynamic_counts_match_r_equals_four_contract(accepted_run: dict):
    assert accepted_run["R"] == EXPECTED_R == 4
    assert accepted_run["counts"] == {
        "contexts": EXPECTED_CONTEXTS,
        "financial_facts": 180,
        "raw_ineligible_facts": 120,
        "reconciled_eligible_facts": 60,
        "version_chain_links": 39,
        "audit": 180,
        "lineage": 180,
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


def test_annual_pit_snapshots_and_final_count(accepted_run: dict):
    assert accepted_run["annual_pit"] == EXPECTED_ANNUAL_PIT == {
        2021: 11, 2022: 20, 2023: 29, 2024: 38, 2025: 47,
    }
    assert accepted_run["final_pit"]["count"] == 47


def test_new_reconciled_facts_are_canonical_and_from_rule_004(
    accepted_run: dict,
):
    # 12 v1 reconciliations (6 years x 2 concepts) + 4 v2 (R changed).
    assert len(accepted_run["new_reconciled_fact_ids"]) == 12
    assert len(accepted_run["v2_reconciled_fact_ids"]) == 4
    assert len(accepted_run["restatement_transitions"]) == 4
    results = _read(accepted_run, "reconciliation_results.json")
    assert len(results) == 16
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
    # 12 v1 x 3 + 4 v2 x 3 = 48.
    assert lineage["count"] == 48
    assert {
        (item["reconciliation_rule_id"], item["reconciliation_rule_version"])
        for item in lineage["rows"]
    } == {("RECON_OFFICIAL_NUMERIC_004", "1")}
    # Rule 001/002/003 lineage must be unchanged from the Stage 2C upstream
    # (57 / 18 / 57).  Query the run-scoped DB directly for independence.
    import duckdb

    db = accepted_run["run_directory"] / "roe_roa_denominators.duckdb"
    con = duckdb.connect(str(db), read_only=True)
    for rule_id, expected_n in (
        ("RECON_OFFICIAL_NUMERIC_001", 57),
        ("RECON_OFFICIAL_NUMERIC_002", 18),
        ("RECON_OFFICIAL_NUMERIC_003", 57),
    ):
        count = con.execute(
            "SELECT COUNT(*) FROM fact_lineage WHERE reconciliation_rule_id=?",
            [rule_id],
        ).fetchone()[0]
        assert count == expected_n, f"{rule_id} lineage changed: {count}"
    con.close()


def test_new_raw_facts_are_verified_ineligible_instant(accepted_run: dict):
    raw_ids = accepted_run["new_raw_fact_ids"]
    # 6 years x 2 sources x 2 concepts = 24 raw v1 facts.
    assert len(raw_ids) == 24
    import duckdb

    db = accepted_run["run_directory"] / "roe_roa_denominators.duckdb"
    con = duckdb.connect(str(db), read_only=True)
    rows = con.execute(
        "SELECT fact_id, source_tier, verification_status, "
        "eligible_for_metrics, period_end, context_id "
        "FROM financial_facts WHERE fact_id IN (SELECT UNNEST(?))",
        [raw_ids],
    ).df().to_dict("records")
    con.close()
    assert len(rows) == 24
    assert all(
        row["source_tier"] in {"company_official", "exchange_official"}
        and row["verification_status"] == "verified"
        and row["eligible_for_metrics"] is False
        for row in rows
    )
    assert {row["period_end"] for row in rows} == {
        f"{year}-12-31" for year in YEARS
    }
    assert {row["context_id"] for row in rows} == {
        f"601857.SH|{year}|instant|consolidated" for year in YEARS
    }


def test_v2_raw_facts_keep_source_id_stable(accepted_run: dict):
    """The v2 raw facts must keep source_id identical to their v1 predecessor
    (VersionChainValidator check C); only the 2D-A latent bug changed it."""
    import duckdb

    transitions = accepted_run["restatement_transitions"]
    db = accepted_run["run_directory"] / "roe_roa_denominators.duckdb"
    con = duckdb.connect(str(db), read_only=True)
    for transition in transitions:
        target = transition["target_fiscal_year"]
        concept = transition["concept_id"]
        for source_tier in ("company_official", "exchange_official"):
            rows = con.execute(
                "SELECT fact_id, source_id, fact_version, available_at "
                "FROM financial_facts "
                "WHERE period_end = ? AND source_tier = ? AND concept_id = ? "
                "AND is_derived = FALSE ORDER BY fact_version",
                [f"{target}-12-31", source_tier, concept],
            ).df().to_dict("records")
            assert len(rows) == 2, (
                f"{target}/{concept}/{source_tier}: expected v1+v2 raw"
            )
            assert rows[0]["fact_version"] == 1 and rows[1]["fact_version"] == 2
            assert rows[0]["source_id"] == rows[1]["source_id"], (
                f"{target}/{concept}/{source_tier}: source_id changed"
            )
            assert rows[1]["available_at"] >= rows[0]["available_at"]
    con.close()


def test_average_balance_input_pairs_are_ready(accepted_run: dict):
    pairs = accepted_run["average_balance_input_pairs"]["pairs"]
    assert len(pairs) == 10  # 5 fiscal years x 2 concepts
    assert {pair["concept_id"] for pair in pairs} == CONCEPTS
    assert {pair["fiscal_year"] for pair in pairs} == {2021, 2022, 2023, 2024, 2025}
    # Latest-available instant value per (year, concept) as of the final
    # announcement date.  2022 and 2023 carry v2 restated values (R = 4);
    # every other year is v1.  Values are in 万元 (raw 百万元 x 100).
    latest_available = {
        (2020, "total_assets"): 248840000,
        (2020, "equity_attributable_to_parent"): 121542100,
        (2021, "total_assets"): 250253300,
        (2021, "equity_attributable_to_parent"): 126381500,
        (2022, "total_assets"): 267066600,           # v2 restated
        (2022, "equity_attributable_to_parent"): 136586600,  # v2 restated
        (2023, "total_assets"): 275923700,           # v2 restated
        (2023, "equity_attributable_to_parent"): 145133300,  # v2 restated
        (2024, "total_assets"): 275300700,
        (2024, "equity_attributable_to_parent"): 151537100,
        (2025, "total_assets"): 282801700,
        (2025, "equity_attributable_to_parent"): 158606100,
    }
    by_fy = {(p["fiscal_year"], p["concept_id"]): p for p in pairs}
    for fy in (2021, 2022, 2023, 2024, 2025):
        for concept in CONCEPTS:
            pair = by_fy[(fy, concept)]
            assert pair["ready_for_average"] is True
            assert (
                pair["beginning"]["consolidation_scope"]
                == pair["ending"]["consolidation_scope"]
                == "consolidated"
            )
            assert pair["beginning"]["unit"] == pair["ending"]["unit"] == "万元"
            assert pair["beginning"]["period_end"] == f"{fy - 1}-12-31"
            assert pair["ending"]["period_end"] == f"{fy}-12-31"
            assert pair["beginning"]["value"] == latest_available[(fy - 1, concept)]
            assert pair["ending"]["value"] == latest_available[(fy, concept)]
    # 2020 opening baseline drives the FY2021 beginning; v2 restated values
    # drive the FY2022/FY2023 endings (and thus FY2023/FY2024 beginnings).
    assert by_fy[(2021, "total_assets")]["beginning"]["value"] == 248840000
    assert by_fy[(2021, "equity_attributable_to_parent")]["beginning"]["value"] == (
        121542100
    )
    assert by_fy[(2022, "total_assets")]["ending"]["value"] == 267066600
    assert by_fy[(2023, "total_assets")]["ending"]["value"] == 275923700


def test_protected_upstream_blobs_are_unchanged():
    for relpath, expected_blob in PROTECTED_BLOBS.items():
        assert _git_blob(ROOT / relpath) == expected_blob, relpath


def test_default_database_unchanged(accepted_run: dict):
    assert accepted_run["default_db_sha256_before"] == (
        accepted_run["default_db_sha256_after"]
    )
    assert accepted_run["default_db_sha256_after"] == DEFAULT_DB_SHA256


def test_upstream_fact_and_metric_id_sets_unchanged(accepted_run: dict):
    assert accepted_run["upstream"]["fact_id_set_sha256"] == (
        UPSTREAM_FACT_ID_SET_SHA256
    )
    assert METRIC_RESULT_63_ID_SET_SHA256 == (
        "34edbbc3a4d3f6533c6d29911fef03c4d07772c68e6649f414ed0b567038e526"
    )
    assert ORIGINAL_38_RESULT_ID_SET_SHA256 == (
        "730484f4abe54298cc53ecdc44d3079c0d2e064a6981047a0b413f6466faa5fa"
    )
