"""Stage 2D-E net_profit fact foundation integration tests.

Runs the complete offline runner (rebuilds the frozen 180-fact Stage 2D-B
base and the frozen 70-Result Stage 2D-D metric base, then registers the
2021-2025 consolidated net_profit facts via Rule 005 with the R=2
restatement chains) and asserts the dynamic counts, PIT semantics,
version chains, readiness registry, baseline invariance and protected
artifacts.  No PDF, cache or network access; no ROA/ROIC/score.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from blob_test_helpers import canonical_worktree_blob

from ashare_research.facts.identity import build_fact_id
from ashare_research.storage.default_db_guard import hash_optional_default_db
from ashare_research.storage.duckdb_store import DuckDBStore
from ashare_research.tools.official_net_profit_fact_foundation import (
    run_net_profit_foundation,
)

ROOT = Path(__file__).resolve().parents[1]

# ── frozen baselines (Stage 2D-B / 2C-D / 2D-D) ──────────────────────
UPSTREAM_180_FACT_ID_SET_SHA256 = (
    "2bd5b2d20ec7992a07b66238fff86ab0fb91f881c5f7cd7f0b5d68b5bde6946c"
)
UPSTREAM_132_FACT_ID_SET_SHA256 = (
    "1e5267022b8062acf96fb413f09ecfc737c706b786c9f02a0b1dc3834fab604d"
)
PRIOR_63_ID_SET_SHA256 = (
    "34edbbc3a4d3f6533c6d29911fef03c4d07772c68e6649f414ed0b567038e526"
)
PRIOR_63_SEMANTIC_SHA256 = (
    "e988394fd21570ae84807fca7400393f2666aa357ddb4ad1b7c5735c7c2ba053"
)
COMBINED_70_RESULT_ID_SET_SHA256 = (
    "bdd9d4fee9777f0c28f31056711675ab3acf98786bc09090cde25ab7ef551df0"
)
DEFAULT_DB = ROOT / "data/research.duckdb"
DEFAULT_DB_SHA256 = (
    "4a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6"
)

# ── Stage 2D-E contract values ───────────────────────────────────────
EXPECTED_R = 2
EXPECTED_COUNTS = {
    "contexts": 11,
    "financial_facts": 201,        # 195 + 3R
    "raw_ineligible_facts": 134,   # 130 + 2R
    "reconciled_eligible_facts": 67,  # 65 + R
    "version_chain_links": 45,     # 39 + 3R
    "audit": 201,                  # 195 + 3R
    "lineage": 201,                # 195 + 3R
}
EXPECTED_ANNUAL_PIT = {2021: 12, 2022: 22, 2023: 32, 2024: 42, 2025: 52}
EXPECTED_FINAL_PIT = 52
COMBINED_EXPECTED = {
    "definitions": 11, "results": 70, "computed": 66,
    "insufficient_history": 4, "version_links": 15, "lineage": 143,
    "final_latest": 55, "final_computed": 51,
}
ROE_EXPECTED = {
    "definitions": 1, "result_versions": 7, "computed_versions": 7,
    "insufficient_history_versions": 0, "version_links": 2,
    "lineage_rows": 21, "final_latest": 5,
}
# Official audited consolidated "净利润" line (万元 = RMB million x100).
NET_PROFIT_V1 = {
    2021: 11468700,
    2022: 16397700,
    2023: 18029100,
    2024: 18374700,
    2025: 17200500,
}
NET_PROFIT_V2 = {2022: 16334300, 2023: 18056100}
EXPECTED_LATEST = {
    2021: (1, NET_PROFIT_V1[2021], "2022-04-01", "original",
           "reviewed_unchanged"),
    2022: (2, NET_PROFIT_V2[2022], "2024-03-26", "restated_1",
           "reviewed_changed"),
    2023: (2, NET_PROFIT_V2[2023], "2025-03-31", "restated_1",
           "reviewed_changed"),
    2024: (1, NET_PROFIT_V1[2024], "2025-03-31", "original",
           "reviewed_unchanged"),
    2025: (1, NET_PROFIT_V1[2025], "2026-03-30", "original",
           "not_yet_reviewable"),
}
PIT_SWITCH_DATES = {2022: "2024-03-26", 2023: "2025-03-31"}

# ── protected artifacts ──────────────────────────────────────────────
PROTECTED_BLOBS = {
    # --- Stage 2D-B artifacts (unchanged by 2D-E) ---
    "src/ashare_research/tools/official_roe_roa_denominator_foundation.py":
        "959fee5702b6d86b41e679815a3514691052f560",
    "acceptance/m2_stage2db_petrochina_2020_2025_roe_roa_denominator_expansion.md":
        "52c874584a46995e106d07e1ac692c4b3e51cee7",
    "src/ashare_research/tools/official_roe_roa_denominator_2025_acceptance.py":
        "8d3ab73a9e7a1c221c6ea434a7012cab669cd62e",
    # --- Stage 2D-C frozen methodology contract (unchanged) ---
    "config/value_evaluation_methodology_capital_return_v1.json":
        "4eb22db431252043381b40440d005ff129cd65fe",
    "docs/value_evaluation_methodology_capital_return_v1.md":
        "a3cdc0a958091f3dfb8c12771f1c965487d8e4ec",
    "docs/roe_roa_input_contract.md":
        "91e9db55b73a0b076a209f455ff302d50a2a7cc3",
    # --- Stage 2D-D artifacts (unchanged by 2D-E) ---
    "src/ashare_research/tools/official_roe_metric_extension.py":
        "4840740423d3cc29f183240c59488dc0f78e05de",
    "acceptance/m2_stage2dd_petrochina_roe_metric_extension.md":
        "41754c3ef7790633bf7ceffeab251bb547cc3c8e",
    "src/ashare_research/metrics/capital_return_definitions.py":
        # Stage 2D-F appends the ROA definition while preserving the frozen
        # ROE definition and legacy runner view.
        "b13b7b44c86b4dcf93562fc98f0f10923a81ec7a",
    "src/ashare_research/metrics/models.py":
        "9c979146b9917dd2bffddf39b0b6388852f501aa",
    "src/ashare_research/metrics/engine.py":
        "44d9d18697313809bb170775e3126d94435de123",
    "src/ashare_research/metrics/identity.py":
        "2073a297df7de10194b29fc634d162ca544deb36",
    "src/ashare_research/metrics/definitions.py":
        "bb06f1e5d0358624fec8fb59863e9e2915a0bf6e",
    "src/ashare_research/metrics/earnings_quality_definitions.py":
        "1bd9a75e4c0d4d42a577c2986486a202e0abb25c",
    # --- Rule 001-004 + Fact code ---
    "src/ashare_research/reconciliation/engine.py":
        # Stage 2D-E added Rule 005 (RECON_OFFICIAL_NUMERIC_005,
        # net_profit only) as a pure additive rule object; Rule 001-004
        # semantics/outputs/identities are unchanged. Blob advanced from
        # 459adfc7... to 828d7051....
        "828d7051bd273c15139a3fc3cfd51cec2dfece1b",
    "src/ashare_research/reconciliation/service.py":
        "62837ed1ce07e94590a62975dbd5c6dc5c8d8c25",
    "src/ashare_research/validation/validator.py":
        "4f90195f7d5aca44b8830760dca66a757bd19dc4",
    "src/ashare_research/validation/version_chain.py":
        "292442c314df46379865cdefd1ab311ec7176c91",
    "src/ashare_research/facts/as_of.py":
        "d707ec3a9ee161d42f9951e52b946c6f2a569085",
    "src/ashare_research/facts/identity.py":
        "85c84b4ee970a32e878d2945eb45b9f070cfb443",
    "src/ashare_research/facts/concepts.py":
        "f3a9d425c75a19a54313508d9b0f73b459a467f2",
    # --- docs ---
    "docs/value_evaluation_methodology_v1.md":
        "6938e35868b940649b4cabe0104dc070f8880886",
    "docs/value_fact_coverage_roadmap.md":
        # Stage 2D-E appended the 2D-D/2D-E status section, then Stage 2J and
        # Stage 2K appended their status sections (append-only; historical
        # baseline text unchanged). Blob advanced 04d323dd... -> a9fa3da1...
        # -> ... -> 0cd48fa1....
        "0cd48fa16dcc5d431b1efce1433c9c7d89d0642a",
    "docs/value_scoring_readiness_gates.md":
        "abb73f82853e831b80879c9f60eb0594472c0738",
    # --- Stage 2D-E runner (this stage) ---
    "src/ashare_research/tools/official_net_profit_fact_foundation.py":
        "40673b7953750530aeca8ea3744beda0ba8265db",
}


def _git_blob(path: Path) -> str:
    return canonical_worktree_blob(path)


def _sha256(path: Path) -> str:
    return hash_optional_default_db(path, DEFAULT_DB_SHA256)


@pytest.fixture(scope="module")
def accepted_run(tmp_path_factory: pytest.TempPathFactory) -> dict:
    run_root = tmp_path_factory.mktemp("net_profit_foundation")
    result = run_net_profit_foundation(
        run_root, run_id="net_profit_foundation_test",
    )
    assert result["status"] == "passed", result.get("error")
    return result


def _read(run: dict, name: str):
    return json.loads(
        (Path(run["run_directory"]) / name).read_text(encoding="utf-8")
    )


def test_runner_is_offline_and_blocks_roa_and_scoring(accepted_run: dict):
    manifest = accepted_run
    assert manifest["offline"] is True
    assert manifest["network_access"] is False
    assert manifest["pdf_access"] is False
    assert manifest["cache_access"] is False
    assert manifest["downloaded"] == 0
    assert manifest["transaction_committed"] is True
    assert manifest["metric_computation"] == "not_performed"
    assert manifest["roa_computation"] == "blocked"
    assert manifest["roic_computation"] == "not_performed"
    assert manifest["scoring"] == "not_implemented"
    assert manifest["investment_advice"] == "not_produced"
    assert manifest["R"] == EXPECTED_R


def test_counts_match_contract(accepted_run: dict):
    assert accepted_run["counts"] == EXPECTED_COUNTS
    assert accepted_run["expected_counts"] == EXPECTED_COUNTS


def test_upstream_180_facts_and_70_results_unchanged(accepted_run: dict):
    upstream = accepted_run["upstream"]
    assert upstream["financial_facts"] == 180
    assert upstream["eligible_facts"] == 60
    assert upstream["latest_fact_pit"] == 47
    assert upstream["version_chain_links"] == 39
    assert upstream["fact_id_set_sha256"] == UPSTREAM_180_FACT_ID_SET_SHA256
    assert upstream["sha256_before"] == upstream["sha256_after"]
    baseline = upstream["metric_result_baseline"]
    assert baseline["result_count"] == 70
    assert baseline["id_set_sha256_newline"] == (
        COMBINED_70_RESULT_ID_SET_SHA256
    )
    assert baseline["roe_result_versions"] == 7
    assert baseline["sha256_before"] == baseline["sha256_after"]
    assert upstream["combined_counts"] == COMBINED_EXPECTED
    assert upstream["roe_counts"] == ROE_EXPECTED
    assert upstream["prior_result_id_set_sha256"] == PRIOR_63_ID_SET_SHA256
    assert upstream["prior_result_semantic_sha256"] == (
        PRIOR_63_SEMANTIC_SHA256
    )


def test_annual_pit_and_final_pit(accepted_run: dict):
    assert accepted_run["annual_pit"] == {
        str(k): v for k, v in EXPECTED_ANNUAL_PIT.items()
    } or accepted_run["annual_pit"] == EXPECTED_ANNUAL_PIT
    assert accepted_run["final_pit"]["count"] == EXPECTED_FINAL_PIT
    assert accepted_run["final_pit"]["as_of_date"] == "2026-03-30"


def test_two_real_restatement_chains(accepted_run: dict):
    transitions = accepted_run["restatement_transitions"]
    assert [t["target_fiscal_year"] for t in transitions] == [2022, 2023]
    for transition in transitions:
        target = transition["target_fiscal_year"]
        assert transition["concept_id"] == "net_profit"
        assert transition["from_fact_id"] != transition["to_fact_id"]
        assert transition["available_at"] <= PIT_SWITCH_DATES[target]
    v2_ids = accepted_run["v2_reconciled_fact_ids"]
    assert sorted(t["to_fact_id"] for t in transitions) == v2_ids


def test_readiness_registry_covers_2021_2025(accepted_run: dict):
    readiness = accepted_run["net_profit_input_readiness"]
    assert readiness["contract"] == "net_profit_input_readiness_v1"
    assert readiness["symbol"] == "601857.SH"
    assert readiness["concept_id"] == "net_profit"
    assert readiness["scope"] == "consolidated"
    assert readiness["all_years_ready"] is True
    assert readiness["roa_numerator_fact_coverage_blocker_cleared"] is True
    assert readiness["roa_computation"] == "not_performed"
    assert readiness["roic_computation"] == "not_performed"
    assert readiness["scoring"] == "not_implemented"
    years = readiness["years"]
    assert [y["fiscal_year"] for y in years] == [2021, 2022, 2023, 2024, 2025]
    for entry in years:
        fy = entry["fiscal_year"]
        version, value, available_at, restated, review = EXPECTED_LATEST[fy]
        assert entry["fact_version"] == version
        assert entry["value"] == value
        assert entry["available_at"] == available_at
        assert entry["restatement_version"] == restated
        assert entry["revision_review_status"] == review
        assert entry["scope"] == "consolidated"
        assert entry["unit"] == "万元"
        assert entry["ready_for_roa_numerator"] is True
        assert len(entry["fact_id"]) == 64


def test_net_profit_values_match_official_evidence(accepted_run: dict):
    """v1 current-column values and v2 comparative-column values must be
    exactly the official RMB-million values x100."""
    reconciliations = _read(accepted_run, "reconciliation_results.json")
    # 5 v1 + 2 v2 = 7 reconciliations, all matched.
    assert len(reconciliations) == 7
    outputs = {
        (
            item["output_fact"]["period_end"],
            item["output_fact"]["fact_version"],
        ): int(item["output_fact"]["value"])
        for item in reconciliations
    }
    for year, value in NET_PROFIT_V1.items():
        assert outputs[(f"{year}-12-31", 1)] == value
    for year, value in NET_PROFIT_V2.items():
        assert outputs[(f"{year}-12-31", 2)] == value
    for item in reconciliations:
        assert item["status"] == "matched"
        assert item["rule_id"] == "RECON_OFFICIAL_NUMERIC_005"
        assert item["rule_version"] == "1"


def test_net_profit_fact_ids_are_canonical(accepted_run: dict):
    db_path = Path(accepted_run["run_directory"]) / "net_profit.duckdb"
    store = DuckDBStore(str(db_path))
    try:
        frame = store.connect().execute(
            "SELECT * FROM financial_facts WHERE concept_id='net_profit'"
        ).df()
    finally:
        store.close()
    # 10 v1 raw + 5 v1 reconciled + 4 v2 raw + 2 v2 reconciled = 21.
    assert len(frame) == 21
    for _, row in frame.iterrows():
        fact = row.to_dict()
        assert fact["fact_id"] == build_fact_id(fact)
        # Duration facts only: period_end is {year}-12-31 and the context
        # is the annual duration context of the same year.
        period_end = str(fact["period_end"])
        year = period_end[:4]
        assert period_end == f"{year}-12-31"
        assert str(fact["context_id"]) == (
            f"601857.SH|{year}|annual|consolidated"
        )


def test_no_new_context_registered(accepted_run: dict):
    db_path = Path(accepted_run["run_directory"]) / "net_profit.duckdb"
    store = DuckDBStore(str(db_path))
    try:
        conn = store.connect()
        contexts = conn.execute(
            "SELECT COUNT(*) FROM fact_contexts"
        ).fetchone()[0]
        net_profit_contexts = {
            row[0]
            for row in conn.execute(
                "SELECT DISTINCT context_id FROM financial_facts "
                "WHERE concept_id='net_profit'"
            ).fetchall()
        }
    finally:
        store.close()
    assert contexts == 11
    # All net_profit facts reuse the existing annual duration contexts.
    assert net_profit_contexts == {
        f"601857.SH|{year}|annual|consolidated"
        for year in (2021, 2022, 2023, 2024, 2025)
    }


def test_rule_lineage_split_is_frozen(accepted_run: dict):
    db_path = Path(accepted_run["run_directory"]) / "net_profit.duckdb"
    store = DuckDBStore(str(db_path))
    try:
        conn = store.connect()
        per_rule = dict(
            conn.execute(
                "SELECT reconciliation_rule_id, COUNT(*) FROM fact_lineage "
                "GROUP BY reconciliation_rule_id"
            ).fetchall()
        )
    finally:
        store.close()
    # Rule 001/002/003/004 unchanged from upstream; Rule 005 new.
    assert per_rule["RECON_OFFICIAL_NUMERIC_001"] == 57
    assert per_rule["RECON_OFFICIAL_NUMERIC_002"] == 18
    assert per_rule["RECON_OFFICIAL_NUMERIC_003"] == 57
    assert per_rule["RECON_OFFICIAL_NUMERIC_004"] == 48
    # (5 v1 + 2 v2) x 3 roles.
    assert per_rule["RECON_OFFICIAL_NUMERIC_005"] == 21
    assert sum(per_rule.values()) == 201
    lineage = _read(accepted_run, "lineage_summary.json")
    assert lineage["count"] == 21
    roles = {row["role"] for row in lineage["rows"]}
    assert roles == {
        "reconciliation_input_company",
        "reconciliation_input_exchange",
        "reconciliation_output",
    }


def test_no_roa_or_score_in_outputs(accepted_run: dict):
    run_dir = Path(accepted_run["run_directory"])
    for path in run_dir.iterdir():
        name = path.name.lower()
        assert "score" not in name
        assert "roa" not in name or name == "net_profit_input_readiness.json"
    readiness = _read(accepted_run, "net_profit_input_readiness.json")
    assert "return_on_average_total_assets" not in json.dumps(readiness)


def test_protected_artifacts_unchanged():
    for rel, blob in PROTECTED_BLOBS.items():
        path = ROOT / rel
        assert _git_blob(path) == blob, rel


def test_default_database_unchanged(accepted_run: dict):
    assert accepted_run["default_db_sha256_before"] == DEFAULT_DB_SHA256
    assert accepted_run["default_db_sha256_after"] == DEFAULT_DB_SHA256
    assert _sha256(DEFAULT_DB) == DEFAULT_DB_SHA256


def test_frozen_baseline_digests_self_consistent():
    assert len(UPSTREAM_132_FACT_ID_SET_SHA256) == 64
    assert len(PRIOR_63_ID_SET_SHA256) == 64
    assert len(COMBINED_70_RESULT_ID_SET_SHA256) == 64


def test_rerun_is_idempotent(tmp_path_factory: pytest.TempPathFactory):
    first = run_net_profit_foundation(
        tmp_path_factory.mktemp("np_idem_1"), run_id="np_idem_1",
    )
    second = run_net_profit_foundation(
        tmp_path_factory.mktemp("np_idem_2"), run_id="np_idem_2",
    )
    assert first["status"] == "passed"
    assert second["status"] == "passed"
    assert first["new_raw_fact_ids"] == second["new_raw_fact_ids"]
    assert first["new_reconciled_fact_ids"] == (
        second["new_reconciled_fact_ids"]
    )
    assert first["v2_reconciled_fact_ids"] == second["v2_reconciled_fact_ids"]
    assert first["counts"] == second["counts"] == EXPECTED_COUNTS
    assert first["net_profit_input_readiness"] == (
        second["net_profit_input_readiness"]
    )
