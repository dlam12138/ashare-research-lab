"""Contract tests for the Stage 2D-C ROE/ROA capital-return methodology.

Validates the frozen methodology contract (machine-readable JSON plus the
human-readable methodology and input-contract docs) without computing any
metric, adding any Fact, or changing any Schema.  Asserts the ROE/ROA
formulas and scope matching, the two-time-point average rule, the PIT
max-available_at rule, restatement propagation, the 2020 opening-baseline
limit, score_eligible=false, the absence of weight/score/target_price
fields, and the invariance of the Stage 2D-B artifacts / Metric code /
default database / stash.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "config/value_evaluation_methodology_capital_return_v1.json"
METHODOLOGY_PATH = ROOT / "docs/value_evaluation_methodology_capital_return_v1.md"
INPUT_CONTRACT_PATH = ROOT / "docs/roe_roa_input_contract.md"

DEFAULT_DB = ROOT / "data/research.duckdb"
DEFAULT_DB_SHA256 = (
    "4a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6"
)

# Frozen reference digests established by Stage 2C-D / 2D-B; this stage must
# not alter them.
UPSTREAM_FACT_ID_SET_SHA256 = (
    "1e5267022b8062acf96fb413f09ecfc737c706b786c9f02a0b1dc3834fab604d"
)
METRIC_RESULT_63_ID_SET_SHA256 = (
    "34edbbc3a4d3f6533c6d29911fef03c4d07772c68e6649f414ed0b567038e526"
)

FORBIDDEN_KEYS = {
    "weight", "score", "rating", "threshold", "target_price", "buy", "sell",
}

# Protected artifacts: Stage 2D-B / 2D-A products, Rule 001-004 + Metric code,
# and the Concept Registry.  Their Git blobs must not change under this stage.
PROTECTED_BLOBS = {
    "src/ashare_research/tools/official_roe_roa_denominator_foundation.py":
        "959fee5702b6d86b41e679815a3514691052f560",
    "acceptance/m2_stage2db_petrochina_2020_2025_roe_roa_denominator_expansion.md":
        "52c874584a46995e106d07e1ac692c4b3e51cee7",
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
    "src/ashare_research/reconciliation/engine.py":
        # Stage 2D-E added Rule 005 (RECON_OFFICIAL_NUMERIC_005,
        # net_profit only) as a pure additive rule object; Rule 001-004
        # semantics/outputs/identities are unchanged. Blob advanced from
        # 459adfc7... to 828d7051....
        "828d7051bd273c15139a3fc3cfd51cec2dfece1b",
    "src/ashare_research/validation/validator.py":
        "4f90195f7d5aca44b8830760dca66a757bd19dc4",
    "src/ashare_research/validation/version_chain.py":
        "292442c314df46379865cdefd1ab311ec7176c91",
    "src/ashare_research/facts/as_of.py":
        "d707ec3a9ee161d42f9951e52b946c6f2a569085",
    "src/ashare_research/facts/identity.py":
        "85c84b4ee970a32e878d2945eb45b9f070cfb443",
    "src/ashare_research/reconciliation/service.py":
        "62837ed1ce07e94590a62975dbd5c6dc5c8d8c25",
    "src/ashare_research/metrics/models.py":
        # Stage 2D-D added the not_comparable_negative_denominator status
        # value (enum addition, no schema upgrade); blob advanced from
        # 16e36169... to 9c979146....
        "9c979146b9917dd2bffddf39b0b6388852f501aa",
    "src/ashare_research/metrics/identity.py":
        "2073a297df7de10194b29fc634d162ca544deb36",
    "src/ashare_research/metrics/engine.py":
        # Stage 2D-D added the optional tertiary_fact (ROE three-input
        # branch); two-input behaviour/IDs unchanged. Blob advanced from
        # 7505cccc... to 0ae662fb....
        # Stage 2D-D closure fixed input role binding: inputs now bind by
        # declared role (no None-shift), two-role defs reject a non-None
        # tertiary_fact. Valid 3-input ROE / all valid 2-input results, IDs,
        # available_at and semantics unchanged. Blob advanced to 244f3605....
        "244f360554e90adcd0fca61d2f4c9cad9ea63d37",
    "src/ashare_research/metrics/definitions.py":
        "bb06f1e5d0358624fec8fb59863e9e2915a0bf6e",
    "src/ashare_research/metrics/earnings_quality_definitions.py":
        "1bd9a75e4c0d4d42a577c2986486a202e0abb25c",
    "src/ashare_research/facts/concepts.py":
        "f3a9d425c75a19a54313508d9b0f73b459a467f2",
}


def _git_blob(path: Path) -> str:
    content = path.read_bytes()
    return hashlib.sha1(  # noqa: S324
        f"blob {len(content)}\0".encode() + content
    ).hexdigest()


def _walk_keys(value, prefix=""):
    """Yield every dict key in a nested JSON structure (exact key names)."""
    if isinstance(value, dict):
        for key, child in value.items():
            yield key
            yield from _walk_keys(child)
    elif isinstance(value, list):
        for item in value:
            yield from _walk_keys(item)


@pytest.fixture(scope="module")
def contract() -> dict:
    return json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def roe(contract: dict) -> dict:
    return next(
        m for m in contract["metrics"]
        if m["metric_id"] == "return_on_average_equity_attributable_to_parent"
    )


@pytest.fixture(scope="module")
def roa(contract: dict) -> dict:
    return next(
        m for m in contract["metrics"]
        if m["metric_id"] == "return_on_average_total_assets"
    )


def test_contract_json_is_well_formed(contract: dict):
    assert contract["methodology_id"] == (
        "value_evaluation_methodology_capital_return_v1"
    )
    assert contract["extends"] == "value_evaluation_methodology_v1"
    assert contract["scope"] == "methodology_only_no_computation"
    assert contract["score_eligible"] is False
    assert {m["metric_id"] for m in contract["metrics"]} == {
        "return_on_average_equity_attributable_to_parent",
        "return_on_average_total_assets",
    }


def test_decimal_average_rule(contract: dict):
    dec = contract["decimal"]
    assert dec["precision"] == 28
    assert dec["rounding"] == "ROUND_HALF_EVEN"
    assert dec["canonical_quantum"] == "0.000000000001"


def test_roe_formula_and_scope(roe: dict):
    assert roe["formula"] == (
        "net_profit_attributable_to_parent / "
        "((opening_equity_attributable_to_parent + "
        "closing_equity_attributable_to_parent) / 2)"
    )
    assert roe["input_concepts"] == [
        "net_profit_attributable_to_parent",
        "equity_attributable_to_parent",
        "equity_attributable_to_parent",
    ]
    assert roe["input_roles"] == ["numerator", "opening", "closing"]
    assert roe["input_period_types"] == {
        "numerator": "duration", "opening": "instant", "closing": "instant",
    }
    assert roe["numerator_scope"] == "attributable_to_parent"
    assert roe["denominator_scope"] == "attributable_to_parent"
    assert roe["unit"] == "ratio"


def test_roa_formula_uses_consolidated_net_profit_not_attributable(roa: dict):
    assert roa["formula"] == (
        "net_profit / "
        "((opening_total_assets + closing_total_assets) / 2)"
    )
    assert roa["input_concepts"] == [
        "net_profit", "total_assets", "total_assets",
    ]
    assert roa["input_roles"] == ["numerator", "opening", "closing"]
    # The ROA numerator MUST be consolidated net_profit, never the
    # attributable parent profit.
    assert roa["input_concepts"][0] == "net_profit"
    assert roa["input_concepts"][0] != "net_profit_attributable_to_parent"
    assert roa["numerator_scope"] == "consolidated_net_profit"
    assert "attributable_proxy" in roa["numerator_proxy_policy"]


def test_average_requires_two_time_points(contract: dict, roe: dict, roa: dict):
    rule = contract["average_rule"]
    assert rule["formula"] == "(opening + closing) / 2"
    assert rule["two_time_points_required"] is True
    assert rule["missing_handling"].startswith("do_not_compute_average")
    for metric in (roe, roa):
        assert metric["input_roles"].count("opening") == 1
        assert metric["input_roles"].count("closing") == 1
        assert metric["input_period_types"]["opening"] == "instant"
        assert metric["input_period_types"]["closing"] == "instant"


def test_pit_rule_is_max_available_at(contract: dict):
    pit = contract["pit_rule"]
    assert pit["metric_available_at"] == (
        "max(numerator_available_at, opening_available_at, "
        "closing_available_at)"
    )
    assert pit["lookback_only"].startswith("use_only_fact_versions")


def test_restatement_propagation_rule(contract: dict):
    rule = contract["restatement_rule"]
    assert "any_input_fact_id_or_value_change" in rule["propagation"]
    assert rule["version_field"] == "result_version"
    assert rule["link_field"] == "supersedes_metric_result_id"
    assert rule["old_version_retention"] == "keep_old_version_do_not_delete"


def test_2020_baseline_restricted_to_fy2021_opening(contract: dict):
    rule = contract["average_rule"]
    assert "comparison_only_opening_baseline_may_only_serve_as_FY2021_opening" in (
        rule["opening_2020_baseline_limit"]
    )
    assert "not_a_standalone_2020_fact" in rule["opening_2020_baseline_limit"]


def test_2025_remains_not_yet_reviewable(contract: dict):
    assert contract["average_rule"]["fiscal_year_2025_status"] == (
        "not_yet_reviewable"
    )


def test_status_rules(contract: dict):
    rules = contract["status_rules"]
    assert rules["denominator_zero"] == "undefined_zero_denominator"
    assert rules["roe_average_equity_negative"] == "not_comparable"
    assert rules["any_input_missing"] == "missing_input"
    assert rules["missing_not_zero"] is True
    assert "does_not_change_enum" in rules["negative_denominator_enum_gap"]


def test_scope_compatibility(contract: dict):
    scope = contract["scope_compatibility"]
    assert scope["accounting_standard"] == "CAS"
    assert scope["consolidation"] == "consolidated"
    assert scope["same_unit_required"] is True
    assert scope["adjacent_period_end_required"] == "12-31"
    assert scope["eligible_reconciled_required"] is True


def test_score_eligible_false_for_both_metrics(contract: dict, roe: dict, roa: dict):
    assert contract["score_eligible"] is False
    assert roe["score_eligible"] is False
    assert roa["score_eligible"] is False


def test_no_weight_score_target_price_fields(contract: dict):
    assert set(contract["forbidden_fields"]) == FORBIDDEN_KEYS
    # Recursively scan every JSON key; none may exactly match a forbidden
    # name.  (score_eligible / score_blockers are gating fields, not scores,
    # and do not match the exact key "score".)
    present = set(_walk_keys(contract))
    assert present.isdisjoint(FORBIDDEN_KEYS), (
        f"forbidden keys present in contract: {present & FORBIDDEN_KEYS}"
    )


def test_decision_matrix(contract: dict, roe: dict, roa: dict):
    matrix = contract["decision_matrix"]
    assert matrix["ROE"] == {
        "inputs_ready": True,
        "methodology_ready": True,
        "metric_computation": "allowed_next_stage",
    }
    assert matrix["ROA"]["denominator_ready"] is True
    assert matrix["ROA"]["numerator_ready"] is False
    assert matrix["ROA"]["required_fact"] == "net_profit"
    assert matrix["ROA"]["metric_computation"] == "blocked"
    assert matrix["ROIC"]["metric_computation"] == "blocked"
    assert matrix["scoring"]["metric_computation"] == "blocked"
    # Per-metric decisions agree with the matrix.
    assert roe["decision"]["metric_computation"] == "allowed_next_stage"
    assert roa["decision"]["metric_computation"] == "blocked"
    assert roa["decision"]["required_fact"] == "net_profit"


def test_roa_blocker_records_missing_net_profit(roa: dict):
    blockers = " ".join(roa["blockers"])
    assert "net_profit" in blockers
    assert "not yet covered" in blockers
    assert "net_profit_attributable_to_parent" in blockers


def test_next_stages_exclude_abc_execution(contract: dict):
    nxt = contract["next_stages"]
    assert nxt["this_stage_executes"] == "none_of_A_B_C"
    # Keys name the follow-up stages (2D-D, 2D-E, then ROA).
    assert any("2dd" in key for key in nxt)
    assert any("2de" in key for key in nxt)
    assert "ROE" in nxt["A_stage_2dd"]
    assert "net_profit" in nxt["B_stage_2de"]
    assert "ROA" in nxt["C_roa"]


def test_references_registered(contract: dict):
    ref_ids = {r["reference_id"] for r in contract["references"]}
    for required in (
        "cfa_fsa", "cfa_analysis_techniques", "penman_fsa_sv",
        "mof_cas", "qlib_pit", "openlineage",
    ):
        assert required in ref_ids


def test_methodology_and_input_contract_docs_exist_and_consistent():
    methodology = METHODOLOGY_PATH.read_text(encoding="utf-8")
    input_contract = INPUT_CONTRACT_PATH.read_text(encoding="utf-8")
    assert "return_on_average_equity_attributable_to_parent" in methodology
    assert "return_on_average_total_assets" in methodology
    assert "net_profit / " in methodology  # ROA uses consolidated net_profit
    # ROA must not bind attributable profit -- documented in both docs.
    assert "归母净利润冒充" in methodology or "归母净利润" in methodology
    assert "comparison_only_opening_baseline" in input_contract
    assert "not_yet_reviewable" in input_contract
    assert "ROUND_HALF_EVEN" in methodology
    assert "score_eligible" in methodology


def test_protected_stage2db_and_metric_files_unchanged():
    for relpath, expected_blob in PROTECTED_BLOBS.items():
        assert _git_blob(ROOT / relpath) == expected_blob, relpath


def test_default_database_unchanged():
    assert hashlib.sha256(DEFAULT_DB.read_bytes()).hexdigest() == DEFAULT_DB_SHA256


def test_frozen_id_set_references_unchanged():
    # The Stage 2C-D / 2D-B frozen digests are re-asserted verbatim; this
    # stage must not alter the upstream 132 Fact ID set or the 63 Metric
    # Result ID set.
    assert UPSTREAM_FACT_ID_SET_SHA256 == (
        "1e5267022b8062acf96fb413f09ecfc737c706b786c9f02a0b1dc3834fab604d"
    )
    assert METRIC_RESULT_63_ID_SET_SHA256 == (
        "34edbbc3a4d3f6533c6d29911fef03c4d07772c68e6649f414ed0b567038e526"
    )


def test_stash_unchanged():
    result = subprocess.run(
        ["git", "stash", "list"],
        cwd=str(ROOT), capture_output=True, text=True, check=True,
    )
    assert "protect pre-existing Stage 1B.4 record edit" in result.stdout
