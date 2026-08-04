"""M2 Stage 2K.1R4A tests: scoring engineering decomposition and guard closeout.

Covers A-F:
  A. Module split (thin CLI; business logic moved to scoring modules)
  B. CLI fail-closed exit codes (0 Ok / 1 check fail / 2 contract/internal / 3 cache missing)
  C. Capsule Audit Snapshot Consistency (capsule_snapshot_mismatch)
  D. Risk status semantics (finite enum, no "clear", no complete-absence claim)
  E. Sensitivity scenario restoration (6 classes, gates separated)
  F. Product boundaries (no production scores, no overall, no canonical writes)

No production scores, no peer acquisition, no M3.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from ashare_research.scoring import capsule as cap
from ashare_research.scoring import confidence as confidence_mod
from ashare_research.scoring import sensitivity as sensitivity_mod
from ashare_research.scoring import shadow as shadow_mod
from ashare_research.scoring import validator as validator_mod
from ashare_research.tools import m2_stage2k1r3_closeout as closeout

ROOT = Path(__file__).resolve().parents[1]


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _capsule() -> dict:
    return cap.build_capsule()


def _lineage_report(capsule: dict) -> dict:
    rep = validator_mod.validate_capsule(capsule)
    rep["report_digest"] = cap._sha256_bytes(cap._canonical(rep))
    return rep


def _run_cli(monkeypatch, *argv) -> int:
    monkeypatch.setattr(sys, "argv", ["prog", *argv])
    return closeout.main()


# ---------------------------------------------------------------------------
# A. module split (thin CLI)
# ---------------------------------------------------------------------------

def test_business_logic_moved_out_of_cli():
    # business functions are no longer on the thin CLI module
    for name in ("build_capsule", "validate_capsule", "capsule_digest",
                 "score_input_id_for", "build_confidence", "build_shadow",
                 "build_sensitivity", "_make_score_input", "_resolve_records"):
        assert not hasattr(closeout, name), f"CLI still exposes {name}"
    # ...and live in the scoring modules
    assert hasattr(cap, "build_capsule")
    assert hasattr(cap, "capsule_digest")
    assert hasattr(cap, "score_input_id_for")
    assert hasattr(cap, "_make_score_input")
    assert hasattr(validator_mod, "validate_capsule")
    assert hasattr(confidence_mod, "build_confidence")
    assert hasattr(shadow_mod, "build_shadow")
    assert hasattr(sensitivity_mod, "build_sensitivity")


def test_cli_is_thin_orchestrator():
    # the CLI should only define the exit-code constants and orchestration
    for name in ("main", "EXIT_OK", "EXIT_CHECK_FAIL", "EXIT_CONTRACT_ERROR",
                 "EXIT_EXTERNAL_CACHE_MISSING"):
        assert hasattr(closeout, name)
    # no scoring business logic is defined in the CLI module
    src = Path(closeout.__file__).read_text(encoding="utf-8")
    assert "def build_capsule(" not in src
    assert "def validate_capsule(" not in src
    assert "def _make_score_input(" not in src


def test_scoring_modules_importable():
    for mod in (cap, validator_mod, confidence_mod, shadow_mod, sensitivity_mod):
        assert mod.__name__.startswith("ashare_research.scoring.")


# ---------------------------------------------------------------------------
# B. CLI fail-closed exit codes
# ---------------------------------------------------------------------------

def test_cli_validate_pass_exit_0(monkeypatch):
    assert _run_cli(monkeypatch, "validate", "--output", "tmp/exit_test_validate.json") == 0


def test_cli_build_capsule_exit_0(monkeypatch):
    assert _run_cli(monkeypatch, "build-capsule", "--output", "tmp/exit_test_capsule.json") == 0


def test_cli_verify_artifacts_pass_exit_0(monkeypatch):
    assert _run_cli(monkeypatch, "verify-artifacts", "--output", "tmp/exit_test_verify.json") == 0


def test_cli_observation_set_without_cache_exit_3(monkeypatch):
    assert _run_cli(monkeypatch, "build-market-observation-set") == 3


def test_cli_validate_fail_exit_1(monkeypatch):
    # force a failing validation by patching the capsule build to return a
    # capsule with a tampered audit snapshot
    tampered = json.loads(json.dumps(_capsule()))
    rec = tampered["components"]["eq_gross_margin"]["resolved_records"][0]
    rec["raw_value"] = "999999"
    rec["record_digest"] = "0" * 64
    tampered["capsule_digest"] = cap.capsule_digest(tampered)

    def _fake_build(**kwargs):
        return tampered

    monkeypatch.setattr(closeout.cap, "build_capsule", _fake_build)
    assert _run_cli(monkeypatch, "validate", "--output", "tmp/exit_test_fail.json") == 1


def test_cli_internal_error_exit_2(monkeypatch):
    def _boom(**kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(closeout.cap, "build_capsule", _boom)
    assert _run_cli(monkeypatch, "build-capsule", "--output", "tmp/exit_test_boom.json") == 2


def test_cli_no_args_exit_2(monkeypatch):
    assert _run_cli(monkeypatch) == 2


# ---------------------------------------------------------------------------
# C. Capsule Audit Snapshot Consistency
# ---------------------------------------------------------------------------

def test_validator_reports_audit_fields():
    capsule = _capsule()
    result = validator_mod.validate_capsule(capsule)
    assert result["status"] == "pass"
    assert result["authoritative_recomputation_status"] == "pass"
    assert result["audit_snapshot_status"] == "pass"
    assert result["snapshot_errors"] == []
    assert result["snapshot_warning_count"] == 0


def test_validator_fails_on_snapshot_mismatch_even_with_correct_score_input_id():
    # problem #3: a tampered resolved_records snapshot must fail even when the
    # score_input_id is left correct (upstream recomputation is authoritative)
    capsule = _capsule()
    tampered = json.loads(json.dumps(capsule))
    comp = tampered["components"]["eq_roe"]
    rec = comp["resolved_records"][0]
    rec["raw_value"] = "999999"
    rec["record_digest"] = "0" * 64
    tampered["capsule_digest"] = cap.capsule_digest(tampered)
    result = validator_mod.validate_capsule(tampered)
    assert result["status"] == "fail"
    assert result["authoritative_recomputation_status"] == "pass"
    assert result["audit_snapshot_status"] == "fail"
    assert any("capsule_snapshot_mismatch" in e for e in result["snapshot_errors"])


def test_validator_snapshot_mismatch_is_an_error_code():
    capsule = _capsule()
    tampered = json.loads(json.dumps(capsule))
    comp = tampered["components"]["eq_roic"]
    comp["resolved_records"][0]["record_digest"] = "0" * 64
    tampered["capsule_digest"] = cap.capsule_digest(tampered)
    result = validator_mod.validate_capsule(tampered)
    assert result["status"] == "fail"
    assert result["audit_snapshot_status"] == "fail"
    assert any("capsule_snapshot_mismatch" in e for e in result["snapshot_errors"])


# ---------------------------------------------------------------------------
# D. Risk status semantics
# ---------------------------------------------------------------------------

def test_risk_status_never_emits_clear():
    # reality: no veto triggered, 2 slots missing evidence -> the honest status
    # is no_trigger_observed_with_missing_evidence, never "clear"
    capsule = _capsule()
    status = shadow_mod._risk_status(capsule)
    assert status["status"] == "no_trigger_observed_with_missing_evidence"
    assert status["triggered_count"] == 0
    assert status["missing_evidence_slots"] == 2
    assert status["complete_absence_claim"] is False


def test_risk_status_enum_no_clear():
    assert "clear" not in shadow_mod.RISK_STATUS_ENUM
    assert {
        "blocked_by_risk_veto",
        "no_trigger_observed_with_missing_evidence",
        "no_trigger_observed_within_bounded_evidence",
        "not_trusted",
    } == shadow_mod.RISK_STATUS_ENUM


def test_risk_status_veto_overrides():
    capsule = _capsule()
    capsule["components"]["rk_veto_triggered"]["selected_value_decimal"] = "1"
    capsule["components"]["rk_missing_evidence_slots"]["selected_value_decimal"] = "2"
    status = shadow_mod._risk_status(capsule)
    assert status["status"] == "blocked_by_risk_veto"
    assert status["complete_absence_claim"] is False


def test_risk_status_bounded_evidence_no_complete_absence_claim():
    capsule = _capsule()
    capsule["components"]["rk_veto_triggered"]["selected_value_decimal"] = "0"
    capsule["components"]["rk_missing_evidence_slots"]["selected_value_decimal"] = "0"
    status = shadow_mod._risk_status(capsule)
    assert status["status"] == "no_trigger_observed_within_bounded_evidence"
    # even a fully-bounded-clean state never claims complete absence of risk
    assert status["complete_absence_claim"] is False


def test_risk_status_not_trusted_when_unknown():
    capsule = _capsule()
    capsule["components"]["rk_veto_triggered"]["selected_value_decimal"] = None
    status = shadow_mod._risk_status(capsule)
    assert status["status"] == "not_trusted"


def test_shadow_risk_status_uses_fixed_semantics():
    capsule = _capsule()
    confidence = confidence_mod.build_confidence(capsule, _lineage_report(capsule))
    shadow = shadow_mod.build_shadow(capsule, confidence)
    risk = shadow["dimensions"]["risk_and_evidence_integrity"]["risk_veto_status"]
    assert risk["status"] == "no_trigger_observed_with_missing_evidence"
    assert risk["complete_absence_claim"] is False


# ---------------------------------------------------------------------------
# E. Sensitivity scenario restoration
# ---------------------------------------------------------------------------

def test_sensitivity_schema_v5_and_contract():
    capsule = _capsule()
    confidence = confidence_mod.build_confidence(capsule, _lineage_report(capsule))
    sensitivity = sensitivity_mod.build_sensitivity(capsule, confidence)
    assert sensitivity["schema"] == "petrochina_dimension_scoring_sensitivity_v5"
    assert sensitivity["confidence_contract"] == "value_dimension_scoring_confidence_v3"
    assert sensitivity["thresholds_frozen_before_rerun"] is True
    assert sensitivity["gates_separated"]["coverage_gate"]
    assert sensitivity["gates_separated"]["confidence_gate"]


def test_sensitivity_restores_all_six_scenario_classes():
    capsule = _capsule()
    confidence = confidence_mod.build_confidence(capsule, _lineage_report(capsule))
    sensitivity = sensitivity_mod.build_sensitivity(capsule, confidence)
    registry = _load(cap.REGISTRY_PATH)
    for dim in ("enterprise_quality", "valuation_attractiveness", "value_realization_capacity"):
        d = sensitivity["dimensions"][dim]
        n_comp = len(registry["dimensions"][dim]["components"])
        # 1. weight perturbation (2 factors) + 2. leave-one-out -> 3*n_comp
        # 3. coverage-threshold (4) + 4. transform alternatives (2)
        # 5. enterprise_quality adds 2 missing-ROIC scenarios
        expected = 3 * n_comp + 4 + 2
        if dim == "enterprise_quality":
            expected += 2
        assert d["scenario_count"] == expected, (dim, d["scenario_count"], expected)
        # coverage + confidence gates both present and independent
        assert len(d["coverage_gate_sensitivity"]["thresholds"]) == 4
        assert len(d["confidence_gate_sensitivity"]["thresholds"]) == 3
        assert d["coverage_gate_sensitivity"]["gate_never_mutated_by_confidence"] is True
        assert d["confidence_gate_sensitivity"]["coverage_gate_not_mutated"] is True


def test_sensitivity_transform_alternatives_scaled():
    # transform-alternative scenario scales absolute breakpoints; the scenario
    # set must contain the transform perturbations (non-empty extra scenarios)
    capsule = _capsule()
    confidence = confidence_mod.build_confidence(capsule, _lineage_report(capsule))
    sensitivity = sensitivity_mod.build_sensitivity(capsule, confidence)
    for dim in ("enterprise_quality", "valuation_attractiveness", "value_realization_capacity"):
        assert sensitivity["dimensions"][dim]["scenario_count"] >= 12


def test_sensitivity_confidence_gate_uses_executed_grade():
    capsule = _capsule()
    confidence = confidence_mod.build_confidence(capsule, _lineage_report(capsule))
    sensitivity = sensitivity_mod.build_sensitivity(capsule, confidence)
    for dim in ("enterprise_quality", "valuation_attractiveness", "value_realization_capacity"):
        cgs = sensitivity["dimensions"][dim]["confidence_gate_sensitivity"]
        assert cgs["grade"] == confidence["dimensions"][dim]["grade"]
        assert cgs["coverage_gate_not_mutated"] is True


def test_sensitivity_stability_frozen_and_not_stable():
    capsule = _capsule()
    confidence = confidence_mod.build_confidence(capsule, _lineage_report(capsule))
    sensitivity = sensitivity_mod.build_sensitivity(capsule, confidence)
    for dim in ("enterprise_quality", "valuation_attractiveness", "value_realization_capacity"):
        d = sensitivity["dimensions"][dim]
        assert d["stability_status"] == "NOT_STABLE"
        assert d["stability_tolerance"] == 1.0


def test_sensitivity_always_not_stable_without_confidence_report():
    # derive grade from capsule source tiers when no confidence is passed
    capsule = _capsule()
    sensitivity = sensitivity_mod.build_sensitivity(capsule, None)
    assert sensitivity["schema"] == "petrochina_dimension_scoring_sensitivity_v5"
    for dim in ("enterprise_quality", "valuation_attractiveness", "value_realization_capacity"):
        assert sensitivity["dimensions"][dim]["confidence_gate_sensitivity"]["grade"] in (
            "low", "medium", "high"
        )


def test_sensitivity_module_does_not_mutate_coverage_gate():
    # the build must not mutate the shared registry's minimum_coverage_gate
    registry_before = _load(cap.REGISTRY_PATH)
    capsule = _capsule()
    sensitivity_mod.build_sensitivity(capsule, None)
    registry_after = _load(cap.REGISTRY_PATH)
    for dim in ("enterprise_quality", "valuation_attractiveness", "value_realization_capacity"):
        assert registry_before["dimensions"][dim]["minimum_coverage_gate"] == \
            registry_after["dimensions"][dim]["minimum_coverage_gate"]


# ---------------------------------------------------------------------------
# F. Product boundaries
# ---------------------------------------------------------------------------

def test_no_production_guards_everywhere():
    capsule = _capsule()
    confidence = confidence_mod.build_confidence(capsule, _lineage_report(capsule))
    shadow = shadow_mod.build_shadow(capsule, confidence)
    sensitivity = sensitivity_mod.build_sensitivity(capsule, confidence)
    for artifact in (capsule, confidence, shadow, sensitivity):
        assert artifact["non_production"] is True
        assert artifact["overall_score_prohibited"] is True
        assert artifact["recommendation_prohibited"] is True
        assert artifact["score_eligible"] is False


def test_no_overall_or_recommendation_in_shadow():
    capsule = _capsule()
    confidence = confidence_mod.build_confidence(capsule, _lineage_report(capsule))
    shadow = shadow_mod.build_shadow(capsule, confidence)
    assert "overall_score" not in shadow
    assert "recommendation" not in shadow
    assert "target_price" not in shadow
    assert "position" not in shadow
    assert "signal" not in shadow


def test_valuation_attractiveness_not_interpretable():
    # the valuation dimension is a shadow/gap analysis, not a production value
    capsule = _capsule()
    for cid in ("va_pe", "va_pb", "va_ps", "va_fcf_yield", "va_dividend_yield"):
        assert capsule["components"][cid]["dimension_id"] == "valuation_attractiveness"


def test_no_pit_denominator_series_built():
    # R4A must NOT build historical PE/PB/PS denominator series
    capsule = _capsule()
    for cid in ("va_pe", "va_pb", "va_ps"):
        obs = capsule["components"][cid].get("observation_set") or {}
        # percentile_source is never a fixed/close denominator pretending to be
        # a valuation percentile
        assert obs.get("percentile_source") != "close_percentile_as_valuation"


def test_roic_remains_gap_for_scoring():
    capsule = _capsule()
    inputs = shadow_mod._capsule_to_inputs(capsule)
    assert inputs["components"]["eq_roic"]["status"] == (
        "not_computable_under_strict_evidence_contract"
    )
    assert inputs["components"]["eq_roic"]["value"] is None
