from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

from ashare_research.tools import m2_stage2k_scoring_shadow as stage2k

ROOT = Path(__file__).parents[1]

DIMENSIONS = [
    "enterprise_quality",
    "valuation_attractiveness",
    "value_realization_capacity",
    "risk_and_evidence_integrity",
]
FORBIDDEN = {
    "overall_score",
    "rank",
    "recommendation",
    "target_price",
    "buy",
    "sell",
    "upside_probability",
    "portfolio_weight",
}


def _load(path: str):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def _walk_keys(value):
    if isinstance(value, dict):
        found = set(value)
        for child in value.values():
            found.update(_walk_keys(child))
        return found
    if isinstance(value, list):
        found = set()
        for child in value:
            found.update(_walk_keys(child))
        return found
    return set()


# --- Scoring ontology ---


def test_exactly_four_dimensions_and_no_overall_score():
    registry = _load("config/value_dimension_scoring_registry_v1.json")
    assert list(registry["dimensions"].keys()) == DIMENSIONS
    assert registry["dimension_order"] == DIMENSIONS
    assert not FORBIDDEN & _walk_keys(registry)
    assert registry["overall_score_prohibited"] is True
    assert registry["score_eligible"] is False


def test_no_overall_score_key_in_shadow_or_policy():
    shadow = _load("reports/petrochina_dimension_scoring_shadow_v1.json")
    policy = _load("config/value_dimension_scoring_policy_v1.json")
    assert not FORBIDDEN & _walk_keys(shadow)
    assert not FORBIDDEN & _walk_keys(policy)
    assert shadow["overall_score_prohibited"] is True
    assert shadow["recommendation_prohibited"] is True
    assert shadow["score_eligible"] is False


def test_every_component_binds_to_metric_role_and_has_required_fields():
    registry = _load("config/value_dimension_scoring_registry_v1.json")
    required = {
        "dimension_id",
        "subdimension_id",
        "component_id",
        "metric_role",
        "accepted_contract_versions",
        "direction",
        "benchmark_mode",
        "transform_version",
        "valid_domain",
        "outlier_policy",
        "missingness_policy",
        "minimum_history",
        "weight",
        "weight_rationale",
        "sensitivity_range",
        "score_contribution_cap",
        "evidence_requirements",
        "pit_requirements",
        "cycle_interpretation_rule",
        "prohibited_fallback",
        "score_eligibility",
        "reviewer_status",
    }
    seen = set()
    for dim in DIMENSIONS:
        for cid, comp in registry["dimensions"][dim]["components"].items():
            assert cid not in seen
            seen.add(cid)
            assert required.issubset(comp), f"{cid} missing {required - set(comp)}"
            assert comp["metric_role"], cid
            assert comp["score_eligibility"] is False, cid


def test_no_weights_across_top_level_dimensions():
    policy = _load("config/value_dimension_scoring_policy_v1.json")
    assert policy["no_cross_dimension_weights"] is True
    assert policy["no_overall_score"] is True


# --- Missingness and coverage ---


def test_missing_maps_to_coverage_gap_not_zero():
    inputs = _load("config/value_dimension_scoring_shadow_inputs_v1.json")
    assert inputs["components"]["eq_roic"]["value"] is None
    assert inputs["components"]["va_dividend_yield"]["value"] is None
    shadow = _load("reports/petrochina_dimension_scoring_shadow_v1.json")
    eq = shadow["dimensions"]["enterprise_quality"]
    assert "eq_roic" in eq["missing_component_ids"]
    va = shadow["dimensions"]["valuation_attractiveness"]
    assert "va_dividend_yield" in va["missing_component_ids"]
    # ROIC is not represented as a zero score anywhere.
    for dim in DIMENSIONS:
        for cid, res in shadow["dimensions"][dim]["components"].items():
            if cid in ("eq_roic", "va_dividend_yield"):
                assert res["score"] is None
                assert res["status"] == "coverage_gap"


def test_coverage_ratio_and_effective_weights_reported():
    shadow = _load("reports/petrochina_dimension_scoring_shadow_v1.json")
    eq = shadow["dimensions"]["enterprise_quality"]
    assert eq["coverage_ratio"] == 0.9
    # effective weights are renormalized and sum to 1.0
    eff = eq["effective_weights"]
    assert abs(sum(eff.values()) - 1.0) < 1e-6
    # original weights are below the effective weights (renormalization)
    assert any(v < 1.0 for v in eff.values())


def test_below_gate_returns_insufficient_evidence_no_numeric_score():
    registry = _load("config/value_dimension_scoring_registry_v1.json")
    policy = _load("config/value_dimension_scoring_policy_v1.json")
    inputs = _load("config/value_dimension_scoring_shadow_inputs_v1.json")
    # Force a high coverage gate so enterprise_quality (0.9) flips.
    reg = copy.deepcopy(registry)
    for dim in DIMENSIONS:
        reg["dimensions"][dim]["minimum_coverage_gate"] = 0.95
    out = stage2k.compute_shadow(reg, policy, inputs)["dimensions"]["enterprise_quality"]
    assert out["status"] == "insufficient_evidence"
    assert out["score"] is None
    assert out["band"] is None


def test_roic_gap_lowers_coverage_without_becoming_zero():
    registry = _load("config/value_dimension_scoring_registry_v1.json")
    policy = _load("config/value_dimension_scoring_policy_v1.json")
    inputs = _load("config/value_dimension_scoring_shadow_inputs_v1.json")
    # With eq_roic removed entirely, coverage would be higher than 0.9.
    reg = copy.deepcopy(registry)
    reg["dimensions"]["enterprise_quality"]["components"] = {
        k: v
        for k, v in registry["dimensions"]["enterprise_quality"]["components"].items()
        if k != "eq_roic"
    }
    out = stage2k.compute_shadow(reg, policy, inputs)["dimensions"]["enterprise_quality"]
    assert out["coverage_ratio"] == 1.0
    # The live registry reports 0.9 because eq_roic is present but uncovered.
    assert registry["dimensions"]["enterprise_quality"]["components"]["eq_roic"][
        "missingness_policy"
    ] == "coverage_gap_not_zero"


# --- Benchmarks and PIT ---


def test_self_history_percentile_is_direction_checked():
    registry = _load("config/value_dimension_scoring_registry_v1.json")
    policy = _load("config/value_dimension_scoring_policy_v1.json")
    inputs = _load("config/value_dimension_scoring_shadow_inputs_v1.json")
    shadow = stage2k.compute_shadow(registry, policy, inputs)
    va = shadow["dimensions"]["valuation_attractiveness"]
    # PE is lower_better: score = (1 - percentile); high percentile -> low score.
    assert va["components"]["va_pe"]["score"] < 40
    # FCF yield is higher_better: score = percentile; low percentile -> low score.
    assert va["components"]["va_fcf_yield"]["score"] < 40
    # PE percentile is high (0.92) so the score is low -> the dimension is E.
    assert va["band"] == "E"


def test_peer_benchmark_not_used_and_peer_present_as_future():
    registry = _load("config/value_dimension_scoring_registry_v1.json")
    for dim in DIMENSIONS:
        for comp in registry["dimensions"][dim]["components"].values():
            assert comp["benchmark_mode"] != "peer_percentile"
    peer = (ROOT / "docs/value_dimension_scoring_peer_preflight.md").read_text(
        encoding="utf-8"
    )
    assert "acquire a broad peer dataset" in " ".join(peer.split())


# --- Weights and sensitivity ---


def test_weights_sum_to_one_within_each_dimension():
    registry = _load("config/value_dimension_scoring_registry_v1.json")
    for dim in DIMENSIONS:
        total = sum(
            float(c["weight"]) for c in registry["dimensions"][dim]["components"].values()
        )
        assert abs(total - 1.0) < 1e-6, dim


def test_weight_perturbation_and_leave_one_out_are_deterministic():
    registry = _load("config/value_dimension_scoring_registry_v1.json")
    policy = _load("config/value_dimension_scoring_policy_v1.json")
    inputs = _load("config/value_dimension_scoring_shadow_inputs_v1.json")
    a = stage2k.run_sensitivity(registry, policy, inputs)
    b = stage2k.run_sensitivity(registry, policy, inputs)
    assert json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)


def test_risk_veto_cannot_be_averaged_away():
    registry = _load("config/value_dimension_scoring_registry_v1.json")
    policy = _load("config/value_dimension_scoring_policy_v1.json")
    inputs = _load("config/value_dimension_scoring_shadow_inputs_v1.json")
    reg = copy.deepcopy(registry)
    # Trigger a risk veto.
    reg["dimensions"]["risk_and_evidence_integrity"]["components"]["rk_veto_triggered"][
        "direction"
    ] = "lower_better"
    modified_inputs = copy.deepcopy(inputs)
    modified_inputs["components"]["rk_veto_triggered"]["value"] = 1
    out = stage2k.compute_shadow(reg, policy, modified_inputs)["dimensions"][
        "risk_and_evidence_integrity"
    ]
    assert out["status"] == "blocked_by_risk_veto"
    assert out["score"] is None


def test_thresholds_frozen_before_shadow_is_explicit():
    methodology = (ROOT / "docs/value_dimension_scoring_methodology_v1.md").read_text(
        encoding="utf-8"
    )
    assert "Thresholds and transforms are frozen before the PetroChina shadow run" in methodology
    assert "No threshold is selected after inspecting which result is more attractive" in " ".join(
        methodology.split()
    )


# --- Shadow safeguards ---


def test_shadow_is_deterministic_and_marked_non_production():
    registry = _load("config/value_dimension_scoring_registry_v1.json")
    policy = _load("config/value_dimension_scoring_policy_v1.json")
    inputs = _load("config/value_dimension_scoring_shadow_inputs_v1.json")
    a = stage2k.compute_shadow(registry, policy, inputs)
    b = stage2k.compute_shadow(registry, policy, inputs)
    assert json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)
    assert a["non_production"] is True
    assert a["research_methodology_test_only"] is True
    assert a["score_eligible"] is False


def test_canonical_production_value_profile_remains_score_free():
    profile = _load("reports/petrochina_value_profile.json")
    assert profile["score_eligible"] is False
    assert not FORBIDDEN & _walk_keys(profile)


def test_no_production_scoring_table_or_metric_result_created():
    # The engine writes only JSON reports; it must not create production tables.
    source = (ROOT / "src/ashare_research/tools/m2_stage2k_scoring_shadow.py").read_text(
        encoding="utf-8"
    )
    assert "CREATE TABLE" not in source
    assert "metric_results" not in source


def test_engine_has_no_network_no_db_no_absolute_path_no_llm():
    source = (ROOT / "src/ashare_research/tools/m2_stage2k_scoring_shadow.py").read_text(
        encoding="utf-8"
    )
    for forbidden in (
        "requests",
        "httpx",
        "urllib",
        "socket",
        "duckdb",
        "data/research.duckdb",
        "D:\\\\",
        "openai",
        "anthropic",
        "llm",
    ):
        assert forbidden not in source.lower()


def test_registry_and_policy_validation_passes():
    result = stage2k.validate_and_emit()
    assert result["contract_errors"] == [], result["contract_errors"]


def test_shadow_contract_verification_passes():
    shadow = _load("reports/petrochina_dimension_scoring_shadow_v1.json")
    assert shadow["schema"] == "petrochina_dimension_scoring_shadow_v1"
    assert set(shadow["dimensions"].keys()) == set(DIMENSIONS)
    assert shadow["dimensions"]["enterprise_quality"]["missing_component_ids"] == ["eq_roic"]


def test_no_recommendation_or_ranking_wording_in_shadow():
    shadow = _load("reports/petrochina_dimension_scoring_shadow_v1.json")
    text = json.dumps(shadow, ensure_ascii=False).lower()
    for phrase in ("therefore buy", "overall attractive", "sell", "target price"):
        assert phrase not in text


def test_stage2k_artifact_manifest_recomputes_every_deliverable():
    manifest = _load("reports/m2_stage2k_artifact_manifest.json")
    assert manifest["schema"] == "m2_stage2k_artifact_manifest_v1"
    assert manifest["north_star_decision"] == "M2_SCORING_ADDENDUM_REOPENED"
    assert manifest["stage2k_decision"] == "PEER_BENCHMARK_ACQUISITION_REQUIRED"
    paths = [item["logical_path"] for item in manifest["files"]]
    assert len(paths) == len(set(paths))
    for item in manifest["files"]:
        path = ROOT / item["logical_path"]
        payload = path.read_text(encoding="utf-8").replace("\r\n", "\n").encode()
        assert len(payload) == item["byte_size"]
        assert hashlib.sha256(payload).hexdigest() == item["sha256"]
