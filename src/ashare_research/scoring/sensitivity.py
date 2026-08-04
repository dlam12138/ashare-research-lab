"""M2 Stage 2K.1R4A sensitivity v5.

Restores the full 6 scenario classes from the Stage 2K.1R2 sensitivity v3
baseline that were lost in the v4 refactor (problem #5):

  1. weight perturbation
  2. leave-one-component-out
  3. coverage-threshold perturbation
  4. frozen transform alternatives
  5. confidence-threshold perturbation (evaluated, never mutates the coverage gate)
  6. missing-ROIC scenarios (enterprise_quality only)

The coverage gate and confidence gate remain independent. stability_tolerance
is frozen and never relaxed; NOT_STABLE is preserved unless the frozen scenario
set independently proves otherwise. Confidence is read from the executed
confidence v3 report (or derived from the capsule source tiers when not passed).
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

from ashare_research.scoring import capsule as cap
from ashare_research.scoring import confidence as confidence_mod
from ashare_research.scoring import shadow as shadow_mod
from ashare_research.tools import m2_stage2k_scoring_shadow as stage2k

TRANSFORM_ALTERNATIVES = (0.95, 1.05)
COVERAGE_THRESHOLDS = (0.4, 0.6, 0.8, 0.95)
CONFIDENCE_THRESHOLDS = (0.6, 0.7, 0.8)

# Confidence grade -> numeric value (for gate comparison).
GRADE_VALUE = {"low": 0.4, "medium": 0.7, "high": 0.9}


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _perturb_registry_weight(registry, dim, cid, factor):
    reg = copy.deepcopy(registry)
    reg["dimensions"][dim]["components"][cid]["weight"] = (
        float(registry["dimensions"][dim]["components"][cid]["weight"]) * factor
    )
    return reg


def _snapshot_breakpoints() -> dict[str, list[tuple[float, float]]]:
    return {cid: list(bp) for cid, bp in stage2k._ABSOLUTE_BREAKPOINTS.items()}


def _restore_breakpoints(snapshot: dict[str, list[tuple[float, float]]]) -> None:
    stage2k._ABSOLUTE_BREAKPOINTS.clear()
    stage2k._ABSOLUTE_BREAKPOINTS.update(snapshot)


def _run_transform_scenario(capsule, registry, dim, factor, snapshot):
    reg = copy.deepcopy(registry)
    for cid, comp in reg["dimensions"][dim]["components"].items():
        if comp.get("benchmark_mode") == "absolute_contract":
            bp = stage2k._ABSOLUTE_BREAKPOINTS.get(cid)
            if bp:
                stage2k._ABSOLUTE_BREAKPOINTS[cid] = [
                    (x * factor, y) for x, y in bp
                ]
    try:
        return _run_for_registry(capsule, reg)[dim]
    finally:
        _restore_breakpoints(snapshot)


def _capsule_with_roic(capsule, mode):
    c = copy.deepcopy(capsule)
    roic = c["components"]["eq_roic"]
    roic["score_scenario"] = mode
    if mode == "synthetic_neutral":
        roic["selected_value_decimal"] = "0.10"
        roic["is_synthetic"] = True
        roic["note"] = "synthetic neutral test value, never a company fact"
    return c


def _run_for_registry(capsule, registry):
    inputs = shadow_mod._capsule_to_inputs(capsule)
    policy = cap._load(cap.POLICY_PATH)
    out = {}
    for dim in cap.SCORED_DIMENSIONS:
        out[dim] = stage2k.compute_dimension(dim, registry, policy, inputs)
    return out


def _score_band(dim_result):
    return dim_result.get("score"), dim_result.get("band"), dim_result.get("status")


def _confidence_grade(confidence, capsule, dim):
    """Read the executed confidence v3 grade, or derive it from the capsule's
    source tiers when no confidence report is passed."""
    if confidence is not None:
        grade = confidence["dimensions"][dim]["grade"]
    else:
        grade = _derive_grade(capsule, dim)
    return grade, GRADE_VALUE.get(grade, 0.4)


def _derive_grade(capsule, dim):
    tiers = []
    for comp in capsule["components"].values():
        if comp["dimension_id"] != dim:
            continue
        tier = comp["resolved_source_tier"]
        obs = comp.get("observation_set") or {}
        if dim == "valuation_attractiveness" and obs.get("percentile_3y") is None:
            tier = "coverage_gap"
        tiers.append(confidence_mod._tier_grade(tier))
    present = [g for g in tiers if g != "low"]
    if not present:
        return "low"
    return min(present, key=lambda g: confidence_mod.GRADE_ORDER[g])


def build_sensitivity(
    capsule: dict[str, Any], confidence: dict[str, Any] | None = None
) -> dict[str, Any]:
    registry = cap._load(cap.REGISTRY_PATH)
    base = _run_for_registry(capsule, registry)
    dimensions: dict[str, Any] = {}

    for dim in cap.SCORED_DIMENSIONS:
        outcomes: list[tuple[float | None, str | None, str | None]] = []
        base_score, base_band, base_status = _score_band(base[dim])

        # 1. weight perturbation
        for cid in registry["dimensions"][dim]["components"]:
            for factor in (1.25, 0.75):
                reg = _perturb_registry_weight(registry, dim, cid, factor)
                outcomes.append(_score_band(_run_for_registry(capsule, reg)[dim]))

        # 2. leave-one-component-out
        for cid in registry["dimensions"][dim]["components"]:
            reg = copy.deepcopy(registry)
            reg["dimensions"][dim]["components"] = {
                k: v for k, v in registry["dimensions"][dim]["components"].items()
                if k != cid
            }
            outcomes.append(_score_band(_run_for_registry(capsule, reg)[dim]))

        # 3. coverage-threshold perturbation (score-relevant: a coverage gate
        # decides whether the dimension is scored at all).
        coverage_passes: list[str] = []
        for gate in COVERAGE_THRESHOLDS:
            reg = copy.deepcopy(registry)
            reg["dimensions"][dim]["minimum_coverage_gate"] = gate
            r = _run_for_registry(capsule, reg)[dim]
            outcomes.append(_score_band(r))
            coverage_passes.append(
                "pass" if r.get("status") != "insufficient_evidence" else "fail"
            )

        # 4. frozen transform alternatives (absolute-contract breakpoint scaling)
        snapshot = _snapshot_breakpoints()
        for factor in TRANSFORM_ALTERNATIVES:
            outcomes.append(
                _score_band(_run_transform_scenario(capsule, registry, dim, factor, snapshot))
            )

        # 5. confidence-threshold sensitivity: evaluated against the executed
        # confidence grade. NEVER mutates minimum_coverage_gate.
        grade, grade_value = _confidence_grade(confidence, capsule, dim)
        confidence_passes: list[str] = [
            "pass" if grade_value >= cth else "fail" for cth in CONFIDENCE_THRESHOLDS
        ]

        # 6. missing-ROIC scenarios (enterprise_quality only)
        if dim == "enterprise_quality":
            for mode in ("synthetic_neutral", "no_roic"):
                c = _capsule_with_roic(capsule, mode)
                reg = copy.deepcopy(registry)
                if mode == "no_roic":
                    reg["dimensions"][dim]["components"] = {
                        k: v
                        for k, v in registry["dimensions"][dim]["components"].items()
                        if k != "eq_roic"
                    }
                outcomes.append(_score_band(_run_for_registry(c, reg)[dim]))

        scores = [s for s, b, st in outcomes if s is not None]
        insufficient = sum(1 for s, b, st in outcomes if st == "insufficient_evidence")
        veto_blocked = sum(1 for s, b, st in outcomes if st == "blocked_by_risk_veto")
        min_score = min(scores) if scores else None
        max_score = max(scores) if scores else None
        max_delta = (max_score - min_score) if scores else None
        bands = [b for s, b, st in outcomes if b is not None]
        band_flips = sum(1 for b in bands if b != base_band)
        tolerance = float(registry["dimensions"][dim].get("stability_tolerance", 1.0))
        stable = (
            max_delta is not None
            and max_delta <= tolerance
            and band_flips == 0
            and insufficient == 0
            and veto_blocked == 0
        )

        dimensions[dim] = {
            "dimension_id": dim,
            "base_score": base_score,
            "base_band": base_band,
            "min_score": min_score,
            "max_score": max_score,
            "max_score_delta": None if max_delta is None else round(max_delta, 4),
            "band_flip_count": band_flips,
            "insufficient_evidence_count": insufficient,
            "veto_block_count": veto_blocked,
            "scenario_count": len(outcomes),
            "stability_status": "STABLE" if stable else "NOT_STABLE",
            "stability_tolerance": tolerance,
            "production_readiness_reason": (
                "dimension stable across frozen scenario set"
                if stable
                else "dimension band or coverage changes under a frozen scenario"
            ),
            "coverage_gate_sensitivity": {
                "thresholds": list(COVERAGE_THRESHOLDS),
                "passes": coverage_passes,
                "gate_never_mutated_by_confidence": True,
            },
            "confidence_gate_sensitivity": {
                "grade": grade,
                "grade_value": grade_value,
                "thresholds": list(CONFIDENCE_THRESHOLDS),
                "passes": confidence_passes,
                "coverage_gate_not_mutated": True,
            },
        }

    return {
        "schema": "petrochina_dimension_scoring_sensitivity_v5",
        "version": "5.0",
        "non_production": True,
        "research_methodology_test_only": True,
        "overall_score_prohibited": True,
        "recommendation_prohibited": True,
        "score_eligible": False,
        "thresholds_frozen_before_rerun": True,
        "synthetic_values_are_not_company_facts": True,
        "gates_separated": {
            "coverage_gate": (
                "perturbs minimum_coverage_gate; decides whether a dimension is scored"
            ),
            "confidence_gate": (
                "evaluates executed confidence grade; never mutates coverage gate"
            ),
        },
        "confidence_contract": "value_dimension_scoring_confidence_v3",
        "dimensions": dimensions,
    }
