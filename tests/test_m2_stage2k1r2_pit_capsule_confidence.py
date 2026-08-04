"""M2 Stage 2K.1R2 tests: dual-clock PIT, capsule validation, percentile
lineage, confidence v2, confidence-gate sensitivity, shadow v3."

Covers the finite contract correction over Stage 2K.1R. No production scores,
no peer acquisition.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ashare_research.tools import m2_stage2k1r2_capsule as capsule_mod
from ashare_research.tools import m2_stage2k1r2_confidence as confidence_mod
from ashare_research.tools import m2_stage2k1r2_sensitivity as sensitivity_mod
from ashare_research.tools import m2_stage2k1r2_shadow as shadow_mod
from ashare_research.tools import m2_stage2k1r2_validate as validate_mod

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"
CONFIG = ROOT / "config"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _capsule() -> dict:
    return capsule_mod.build_capsule()


# ---------------------------------------------------------------------------
# 1. Dual-clock time contract
# ---------------------------------------------------------------------------

def test_time_contract_frozen_fields():
    tc = _load(CONFIG / "value_dimension_scoring_time_contract_v1.json")
    assert tc["market_data_as_of_date"] == "2026-07-31"
    assert tc["research_evidence_as_of"] == "2026-08-02"
    assert tc["scorecard_formed_at"] == "2026-08-02"
    assert tc["timezone"] == "Asia/Shanghai"
    assert tc["version"] == "1.0"
    assert tc["legacy_score_date_fields"]["score_date"]["legacy"] is True


def test_scorecard_formed_at_derived_from_inputs():
    capsule = _capsule()
    formed = capsule["time_contract"]["scorecard_formed_at"]
    max_avail = max(
        (c.get("available_at") or "" for c in capsule["components"].values()),
        default="",
    )
    assert formed >= max_avail


def test_risk_observations_within_research_evidence_as_of():
    capsule = _capsule()
    research_as_of = capsule["time_contract"]["research_evidence_as_of"]
    for _, comp in capsule["components"].items():
        if comp.get("upstream_ref_type") == "risk_observation":
            assert comp["available_at"] <= research_as_of


# ---------------------------------------------------------------------------
# 2. Capsule v2 structure
# ---------------------------------------------------------------------------

def test_capsule_has_24_components_and_all_score_input_ids():
    capsule = _capsule()
    assert capsule["schema"] == "m2_stage2k1r2_score_input_capsule_v2"
    assert capsule["component_count"] == 24
    assert all(v.get("score_input_id") for v in capsule["components"].values())


def test_capsule_score_eligible_false_and_no_overall():
    capsule = _capsule()
    assert capsule["score_eligible"] is False
    assert capsule["overall_score_prohibited"] is True
    assert capsule["recommendation_prohibited"] is True


def test_capsule_upstream_refs_typed():
    capsule = _capsule()
    for cid, comp in capsule["components"].items():
        assert comp["upstream_refs"], f"{cid} missing upstream_refs"
        for u in comp["upstream_refs"]:
            assert u["artifact"]
            assert u["artifact"].startswith(("acceptance/", "events/", "reports/"))


def test_capsule_values_are_decimal_strings():
    capsule = _capsule()
    for cid, comp in capsule["components"].items():
        if comp.get("value") is not None:
            assert isinstance(comp["value"], str), f"{cid} value not str"
            assert comp["transform_output"] == comp["value"]


def test_capsule_observation_set_digest():
    capsule = _capsule()
    os_ = capsule["components"]["va_pe"]["observation_set"]
    assert os_["observation_set_digest"]
    assert os_["provider_sha256"] == (
    "defd0b9507c0d87cf9d12864923eb24573e4edee28d7b67b9ce319ab4d91a764"
)
    assert os_["row_count"] == 1351


def test_capsule_digest_recomputable():
    capsule = _capsule()
    recomputed = capsule_mod.capsule_digest(capsule)
    assert recomputed == capsule["capsule_digest"]


# ---------------------------------------------------------------------------
# 3. Fail-closed validator
# ---------------------------------------------------------------------------

def test_validator_passes_on_clean_capsule():
    capsule = _capsule()
    result = validate_mod.validate_capsule(capsule)
    assert result["status"] == "pass"
    assert result["error_count"] == 0


def test_validator_fails_on_tampered_value():
    capsule = _capsule()
    capsule["components"]["eq_roe"]["value"] = "0.999"
    capsule["components"]["eq_roe"]["transform_output"] = "0.999"
    result = validate_mod.validate_capsule(capsule)
    assert result["status"] == "fail"
    assert any("eq_roe" in e and "mismatch" in e for e in result["errors"])


def test_validator_fails_on_tampered_digest():
    capsule = _capsule()
    capsule["capsule_digest"] = "0" * 64
    result = validate_mod.validate_capsule(capsule)
    assert result["status"] == "fail"
    assert any("capsule_digest mismatch" in e for e in result["errors"])


def test_validator_fails_on_tampered_score_input_id():
    capsule = _capsule()
    capsule["components"]["eq_roe"]["score_input_id"] = "0" * 64
    result = validate_mod.validate_capsule(capsule)
    assert result["status"] == "fail"
    assert any("eq_roe: score_input_id mismatch" in e for e in result["errors"])


def test_validator_rejects_future_available_at():
    capsule = _capsule()
    capsule["components"]["eq_roe"]["available_at"] = "2026-08-03"
    result = validate_mod.validate_capsule(capsule)
    assert result["status"] == "fail"
    assert any("available_at" in e and "scorecard_formed_at" in e for e in result["errors"])


def test_validator_rejects_future_trade_date():
    capsule = _capsule()
    capsule["components"]["va_pe"]["trade_date"] = "2026-08-01"
    result = validate_mod.validate_capsule(capsule)
    assert result["status"] == "fail"
    assert any("trade_date" in e and "market_data_as_of_date" in e for e in result["errors"])


def test_validator_rejects_missing_upstream_record():
    capsule = _capsule()
    capsule["components"]["eq_roe"]["upstream_refs"][0]["record_id"] = "does.not.exist"
    result = validate_mod.validate_capsule(capsule)
    assert result["status"] == "fail"
    assert any("record_id not found" in e for e in result["errors"])


# ---------------------------------------------------------------------------
# 4. Percentile observation-set lineage
# ---------------------------------------------------------------------------

def test_percentile_contract_pit_exclusion():
    contract = _load(CONFIG / "value_dimension_scoring_percentile_contract_v1.json")
    assert contract["pit_exclusion_policy"]["scope_end"] == "market_data_as_of_date"
    assert contract["pit_exclusion_policy"]["excluded_observation_count"] == 0


def test_percentile_report_digest_matches_capsule():
    report = _load(REPORTS / "petrochina_valuation_percentile_observation_sets_v1.json")
    capsule = _capsule()
    rep_digest = report["observation_sets"][
    "valuation_2021_2026_common_days"
]["observation_set_digest"]
    cap_digest = capsule["components"]["va_pe"]["observation_set"]["observation_set_digest"]
    assert rep_digest == cap_digest


def test_percentile_dividend_yield_is_gap():
    report = _load(REPORTS / "petrochina_valuation_percentile_observation_sets_v1.json")
    assert report["metrics"]["trailing_12m_announced_dividend_yield"]["gap"] is True
    assert report["metrics"]["a_share_price_to_latest_annual_parent_earnings"]["gap"] is False


# ---------------------------------------------------------------------------
# 5. Confidence v2
# ---------------------------------------------------------------------------

def test_confidence_executes_source_tiers():
    capsule = _capsule()
    result = confidence_mod.compute_confidence(capsule)
    assert result["version"] == "2.0"
    dims = [
        "enterprise_quality",
        "valuation_attractiveness",
        "value_realization_capacity",
        "risk_and_evidence_integrity",
    ]
    for dim in dims:
        assert result["dimensions"][dim]["grade"] in ("low", "medium", "high")


def test_confidence_coverage_gap_reasons():
    capsule = _capsule()
    result = confidence_mod.compute_confidence(capsule)
    eq = result["dimensions"]["enterprise_quality"]
    assert any("coverage_gap:eq_roic" in r for r in eq["reasons"])
    assert "M2G-ROIC-001" in eq["supporting_ids"]
    val = result["dimensions"]["valuation_attractiveness"]
    assert any("coverage_gap:va_dividend_yield" in r for r in val["reasons"])


# ---------------------------------------------------------------------------
# 6. Sensitivity v3: confidence-gate vs coverage-gate separation
# ---------------------------------------------------------------------------

def test_sensitivity_gates_separated():
    result = sensitivity_mod.compute_sensitivity(_capsule())
    assert result["version"] == "3.0"
    assert result["gates_separated"]["coverage_gate"]
    assert result["gates_separated"]["confidence_gate"]
    for dim in ["enterprise_quality", "valuation_attractiveness", "value_realization_capacity"]:
        info = result["dimensions"][dim]
        assert info["coverage_gate_sensitivity"]["gate_never_mutated_by_confidence"] is True
        assert info["confidence_gate_sensitivity"]["coverage_gate_not_mutated"] is True


def test_sensitivity_preserves_not_stable():
    result = sensitivity_mod.compute_sensitivity(_capsule())
    for dim in ["enterprise_quality", "valuation_attractiveness", "value_realization_capacity"]:
        assert result["dimensions"][dim]["stability_status"] == "NOT_STABLE"
        assert result["dimensions"][dim]["stability_tolerance"] == 1.0


def test_sensitivity_confidence_grade_passes_tiers():
    result = sensitivity_mod.compute_sensitivity(_capsule())
    for dim in ["enterprise_quality", "valuation_attractiveness", "value_realization_capacity"]:
        fg = result["dimensions"][dim]["confidence_gate_sensitivity"]
        # all dimensions are medium = 0.7
        assert fg["grade"] == "medium"
        assert fg["grade_value"] == 0.7
        assert fg["passes"] == ["pass", "pass", "fail"]


# ---------------------------------------------------------------------------
# 7. Shadow v3
# ---------------------------------------------------------------------------

def test_shadow_matches_stage2k_scores():
    result = shadow_mod.compute_shadow(_capsule())
    assert result["status"] == "pass"
    assert result["dimensions"]["enterprise_quality"]["score"] == pytest.approx(73.47, abs=0.01)
    assert result["dimensions"]["valuation_attractiveness"]["score"] == pytest.approx(
    12.17, abs=0.01
)
    assert result["dimensions"]["value_realization_capacity"]["score"] == pytest.approx(
        70.13, abs=0.01
    )


def test_shadow_formed_at_derived():
    result = shadow_mod.compute_shadow(_capsule())
    assert result["scorecard_formed_at"] == "2026-08-02"
    assert result["max_input_available_at"] == "2026-08-02"
    assert result["scorecard_formed_at"] >= result["max_input_available_at"]


def test_shadow_risk_no_merged_score():
    result = shadow_mod.compute_shadow(_capsule())
    risk = result["dimensions"]["risk_and_evidence_integrity"]
    assert risk["no_merged_numeric_score"] is True
    assert "risk_veto_status" in risk
    assert "evidence_integrity" in risk


def test_shadow_blocked_on_invalid_capsule():
    capsule = _capsule()
    capsule["components"]["eq_roe"]["transform_output"] = "0.999"
    capsule["components"]["eq_roe"]["value"] = "0.999"
    result = shadow_mod.compute_shadow(capsule)
    assert result["status"] == "blocked_by_validation"
    assert result["scorecard"] is None
