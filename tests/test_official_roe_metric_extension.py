"""Offline integration contract for the Stage 2D-D ROE metric extension.

Runs the full offline runner, then asserts the ROE-only and combined counts,
the Metric PIT replay, the two real restatement chains (FY2022, FY2023),
the 2024-uses-2023-equity-v2 invariant, the 2025 not_yet_reviewable status, the
prior 63 result ID-set and semantic invariance, the 180-fact invariance, and
the absence of any ROA / score output.
"""

from __future__ import annotations

import hashlib
import json
from decimal import Decimal
from pathlib import Path

import pytest
from blob_test_helpers import canonical_worktree_blob

from ashare_research.metrics.capital_return_definitions import (
    CapitalReturnMetricDefinitionRegistry,
)
from ashare_research.metrics.identity import build_metric_result_id
from ashare_research.tools.official_roe_metric_extension import (
    COMBINED_EXPECTED,
    PIT_COMPUTED,
    PIT_INSUFFICIENT,
    PIT_LATEST,
    PRIOR_63_SEMANTIC_SHA256,
    ROE_EXPECTED,
    run_roe_metric_extension,
)

ROOT = Path(__file__).resolve().parents[1]

# Frozen Stage 2C-D / 2D-B baselines; this stage must leave them unchanged.
PRIOR_63_ID_SET_SHA256 = (
    "34edbbc3a4d3f6533c6d29911fef03c4d07772c68e6649f414ed0b567038e526"
)
UPSTREAM_180_FACT_ID_SET_SHA256 = (
    "2bd5b2d20ec7992a07b66238fff86ab0fb91f881c5f7cd7f0b5d68b5bde6946c"
)
UPSTREAM_132_FACT_ID_SET_SHA256 = (
    "1e5267022b8062acf96fb413f09ecfc737c706b786c9f02a0b1dc3834fab604d"
)
ORIGINAL_38_RESULT_ID_SET_SHA256 = (
    "730484f4abe54298cc53ecdc44d3079c0d2e064a6981047a0b413f6466faa5fa"
)
DEFAULT_DB_SHA256 = (
    "4a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6"
)
# Stage 2D-D closure: the role-binding fix must leave the full combined
# 70 Result IDs (63 prior + 7 ROE) byte-for-byte unchanged.
COMBINED_70_RESULT_ID_SET_SHA256 = (
    "bdd9d4fee9777f0c28f31056711675ab3acf98786bc09090cde25ab7ef551df0"
)
ROE_VALUES = {
    2021: Decimal("0.074346290551"),
    2022: Decimal("0.113122466185"),
    2023: Decimal("0.114591833946"),
    2024: Decimal("0.111016131033"),
    2025: Decimal("0.101438303339"),
}
ROE_TRANSITIONAL = {
    (2022, 1): Decimal("0.113446882745"),
    (2023, 1): Decimal("0.114600416175"),
}

PROTECTED_BLOBS = {
    # Stage 2D-B artifacts unchanged.
    "src/ashare_research/tools/official_roe_roa_denominator_foundation.py":
        "959fee5702b6d86b41e679815a3514691052f560",
    "acceptance/m2_stage2db_petrochina_2020_2025_roe_roa_denominator_expansion.md":
        "52c874584a46995e106d07e1ac692c4b3e51cee7",
    "src/ashare_research/tools/official_roe_roa_denominator_2025_acceptance.py":
        "8d3ab73a9e7a1c221c6ea434a7012cab669cd62e",
    # Stage 2D-C methodology contract + docs unchanged.
    "config/value_evaluation_methodology_capital_return_v1.json":
        "4eb22db431252043381b40440d005ff129cd65fe",
    "docs/value_evaluation_methodology_capital_return_v1.md":
        "a3cdc0a958091f3dfb8c12771f1c965487d8e4ec",
    "docs/roe_roa_input_contract.md":
        "91e9db55b73a0b076a209f455ff302d50a2a7cc3",
    # Rule 001-004 reconciliation + Fact code unchanged.
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
    # Prior 10 metric definitions unchanged.
    "src/ashare_research/metrics/definitions.py":
        "bb06f1e5d0358624fec8fb59863e9e2915a0bf6e",
    "src/ashare_research/metrics/earnings_quality_definitions.py":
        "1bd9a75e4c0d4d42a577c2986486a202e0abb25c",
    # docs unchanged.
    "docs/value_fact_coverage_roadmap.md":
        # Stage 2D-E appended the 2D-D/2D-E status section (append-only;
        # historical baseline text unchanged). Blob advanced 04d323dd... ->
        # a9fa3da1....
        "99a3be3ca669f82c96a1c0d2449a20ed6b0a70cf",
    "docs/value_evaluation_methodology_v1.md":
        "6938e35868b940649b4cabe0104dc070f8880886",
}


def _git_blob(path: Path) -> str:
    return canonical_worktree_blob(path)


def _read(run: dict, name: str):
    return json.loads(
        (run["run_directory"] / name).read_text(encoding="utf-8")
    )


@pytest.fixture(scope="module")
def accepted_run(tmp_path_factory: pytest.TempPathFactory) -> dict:
    result = run_roe_metric_extension(
        tmp_path_factory.mktemp("roe_metric_extension"),
        run_id="roe_metric_extension_test",
    )
    assert result["status"] == "passed", result
    return result


def test_runner_is_offline_and_blocks_roa_and_scoring(accepted_run: dict):
    assert accepted_run["offline"] is True
    assert accepted_run["network_access"] is False
    assert accepted_run["pdf_access"] is False
    assert accepted_run["cache_access"] is False
    assert accepted_run["downloaded"] == 0
    assert accepted_run["scoring"] == "not_implemented"
    assert accepted_run["investment_advice"] == "not_produced"
    assert accepted_run["roa_computation"] == "blocked"


def test_combined_counts_match_contract(accepted_run: dict):
    assert accepted_run["combined_counts"] == COMBINED_EXPECTED


def test_roe_counts_match_contract(accepted_run: dict):
    assert accepted_run["roe_counts"] == ROE_EXPECTED
    roe = CapitalReturnMetricDefinitionRegistry.list_all()
    assert len(roe) == 1


def test_metric_pit_replay_counts(accepted_run: dict):
    assert accepted_run["metric_pit_counts"] == PIT_LATEST == [
        0, 11, 22, 33, 44, 55,
    ]
    assert accepted_run["metric_pit_computed_counts"] == PIT_COMPUTED == [
        0, 7, 18, 29, 40, 51,
    ]
    assert accepted_run["metric_pit_insufficient_history_counts"] == (
        PIT_INSUFFICIENT
    ) == [0, 4, 4, 4, 4, 4]


def test_prior_63_results_id_set_and_semantics_unchanged(accepted_run: dict):
    assert accepted_run["prior_result_id_set_sha256"] == PRIOR_63_ID_SET_SHA256
    assert accepted_run["prior_result_semantic_sha256"] == (
        PRIOR_63_SEMANTIC_SHA256
    )


def test_upstream_180_facts_unchanged(accepted_run: dict):
    assert accepted_run["upstream"]["financial_facts"] == 180
    assert accepted_run["upstream"]["eligible_facts"] == 60
    assert accepted_run["upstream"]["latest_fact_pit"] == 47
    assert accepted_run["upstream"]["version_chain_links"] == 39
    assert accepted_run["upstream"]["fact_id_set_sha256"] == (
        UPSTREAM_180_FACT_ID_SET_SHA256
    )
    assert accepted_run["upstream"]["sha256_before"] == (
        accepted_run["upstream"]["sha256_after"]
    )


def test_roe_values_computed_from_facts(accepted_run: dict):
    results = _read(accepted_run, "metric_result_versions.json")
    roe = [r for r in results if r["metric_id"]
           == "return_on_average_equity_attributable_to_parent"]
    assert len(roe) == 7
    by_fy = {}
    for r in roe:
        by_fy.setdefault(r["fiscal_year"], []).append(r)
    for fiscal_year, expected in ROE_VALUES.items():
        latest = max(by_fy[fiscal_year], key=lambda r: r["result_version"])
        assert latest["status"] == "computed"
        assert Decimal(latest["value"]) == expected, fiscal_year
    for (fiscal_year, version), expected in ROE_TRANSITIONAL.items():
        item = next(
            r for r in by_fy[fiscal_year] if r["result_version"] == version
        )
        assert Decimal(item["value"]) == expected, (fiscal_year, version)


def test_two_real_restatement_chains(accepted_run: dict):
    transitions = _read(accepted_run, "roe_metric_transitions.json")
    assert [t["fiscal_year"] for t in transitions] == [2022, 2023]
    for t in transitions:
        before = t["before"]
        after = t["after"]
        assert before["result_version"] == 1
        assert after["result_version"] == 2
        assert before["input_fact_ids"] != after["input_fact_ids"]
        assert before["available_at"] < after["available_at"]
        assert after["supersedes_metric_result_id"] == before["metric_result_id"]
    # FY2022: v1 @2023-03-30 -> v2 @2024-03-26.
    assert transitions[0]["pit_switch_date"] == "2024-03-26"
    # FY2023: v1 @2024-03-26 -> v2 @2025-03-31.
    assert transitions[1]["pit_switch_date"] == "2025-03-31"


def test_2024_roe_uses_2023_equity_v2_directly(accepted_run: dict):
    roe_2024 = accepted_run["roe_2024"]
    assert roe_2024["result_version"] == 1
    # opening is the second input (role "opening"); must be 2023 equity v2.
    assert roe_2024["revision_review_status"] == "reviewed_unchanged"


def test_2025_roe_is_not_yet_reviewable(accepted_run: dict):
    latest = _read(accepted_run, "latest_metric_snapshot.json")
    roe_2025 = [
        r for r in latest
        if r["metric_id"] == "return_on_average_equity_attributable_to_parent"
        and r["fiscal_year"] == 2025
    ]
    assert roe_2025 and all(
        r["revision_review_status"] == "not_yet_reviewable" for r in roe_2025
    )


def test_roe_results_are_canonical(accepted_run: dict):
    results = _read(accepted_run, "metric_result_versions.json")
    roe = [r for r in results if r["metric_id"]
           == "return_on_average_equity_attributable_to_parent"]
    for item in roe:
        rebuilt = dict(item)
        rebuilt["value"] = (
            None if rebuilt["value"] is None else str(rebuilt["value"])
        )
        assert item["metric_result_id"] == build_metric_result_id(rebuilt)


def test_roe_lineage_has_three_roles(accepted_run: dict):
    lineage = _read(accepted_run, "metric_lineage.json")
    roe_lineage = [
        row for row in lineage
        if row["metric_result_id"] in {
            r["metric_result_id"]
            for r in _read(accepted_run, "metric_result_versions.json")
            if r["metric_id"] == "return_on_average_equity_attributable_to_parent"
        }
    ]
    assert len(roe_lineage) == 21  # 7 results x 3 roles
    roles = {(row["metric_result_id"], row["input_role"]) for row in roe_lineage}
    for item in _read(accepted_run, "metric_result_versions.json"):
        if item["metric_id"] != "return_on_average_equity_attributable_to_parent":
            continue
        assert {
            (item["metric_result_id"], role)
            for role in ("numerator", "opening", "closing")
        } <= roles


def test_no_roa_or_score_in_outputs(accepted_run: dict):
    results = _read(accepted_run, "metric_result_versions.json")
    definitions = _read(accepted_run, "metric_definitions.json")
    assert all(
        d["metric_id"] != "return_on_average_total_assets" for d in definitions
    )
    assert all(
        r["metric_id"] != "return_on_average_total_assets" for r in results
    )
    manifest = json.loads(
        (accepted_run["run_directory"] / "run_manifest.json").read_text(
            encoding="utf-8"
        )
    )
    assert manifest["scoring"] == "not_implemented"
    assert manifest["roa_computation"] == "blocked"


def test_protected_artifacts_unchanged():
    for relpath, expected_blob in PROTECTED_BLOBS.items():
        assert _git_blob(ROOT / relpath) == expected_blob, relpath


def test_default_database_unchanged(accepted_run: dict):
    assert accepted_run["default_db_sha256_before"] == DEFAULT_DB_SHA256
    assert accepted_run["default_db_sha256_after"] == DEFAULT_DB_SHA256


def test_frozen_baselines_unchanged(accepted_run: dict):
    # Upstream 132 Fact ID set (Stage 2C) and original 38 Result ID set are
    # re-asserted verbatim; this stage must not alter them.
    assert UPSTREAM_132_FACT_ID_SET_SHA256 == (
        "1e5267022b8062acf96fb413f09ecfc737c706b786c9f02a0b1dc3834fab604d"
    )
    assert ORIGINAL_38_RESULT_ID_SET_SHA256 == (
        "730484f4abe54298cc53ecdc44d3079c0d2e064a6981047a0b413f6466faa5fa"
    )


def test_rerun_is_idempotent(tmp_path_factory: pytest.TempPathFactory):
    """A second offline run with a fresh temp dir must reproduce the same
    result IDs and counts (deterministic, no network/cache)."""
    first = run_roe_metric_extension(
        tmp_path_factory.mktemp("roe_idem1"), run_id="roe_idem1"
    )
    second = run_roe_metric_extension(
        tmp_path_factory.mktemp("roe_idem2"), run_id="roe_idem2"
    )
    assert first["status"] == "passed" and second["status"] == "passed"
    assert first["new_metric_result_ids"] == second["new_metric_result_ids"]
    assert first["combined_counts"] == second["combined_counts"]


def test_combined_70_result_ids_unchanged_after_role_binding_fix(
    accepted_run: dict,
):
    """Stage 2D-D closure: hardening input role binding must not perturb any
    of the 70 Result IDs (63 prior + 7 ROE).  Pin the full combined id set."""
    results = _read(accepted_run, "metric_result_versions.json")
    ids = sorted(r["metric_result_id"] for r in results)
    assert len(ids) == COMBINED_EXPECTED["results"] == 70
    digest = hashlib.sha256(
        "\n".join(ids).encode("utf-8")
    ).hexdigest()
    assert digest == COMBINED_70_RESULT_ID_SET_SHA256
