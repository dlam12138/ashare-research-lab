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
from collections import Counter
from dataclasses import dataclass
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

# Sensitivity v6 ledger contract version.
SCENARIO_CONTRACT_VERSION = "1.0"

# The six frozen scenario classes (v3 baseline restored in v5, kept in v6).
SCENARIO_TYPES = (
    "weight_perturbation",
    "leave_one_component_out",
    "coverage_threshold",
    "transform_alternative",
    "confidence_threshold",
    "missing_roic",
)

# The three missing-ROIC sub-scenarios (enterprise_quality only).
MISSING_ROIC_MODES = ("current_gap", "synthetic_neutral", "no_roic_component")


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


# ---------------------------------------------------------------------------
# Sensitivity v6 — auditable per-scenario ledger
# ---------------------------------------------------------------------------

@dataclass
class SensitivityScenario:
    """One typed sensitivity scenario. ``scenario_id`` is deterministically
    derived from the canonical semantic payload (no absolute paths, no run
    directory, no JSON indentation, no generation time)."""

    scenario_id: str
    scenario_type: str
    dimension_id: str
    component_id: str | None
    changed_parameter: str
    base_parameter_value: Any
    scenario_parameter_value: Any
    base_score: float | None
    scenario_score: float | None
    base_band: str | None
    scenario_band: str | None
    score_delta: float | None
    base_status: str | None
    scenario_status: str | None
    coverage: float | None
    confidence_grade: str | None
    release_allowed: bool
    blocked_reason: str | None
    veto_status: bool
    is_synthetic: bool
    not_company_fact: bool
    not_publishable: bool
    excluded_from_base_result: bool
    input_capsule_digest: str
    registry_digest: str
    scenario_contract_version: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "scenario_id": self.scenario_id,
            "scenario_type": self.scenario_type,
            "dimension_id": self.dimension_id,
            "component_id": self.component_id,
            "changed_parameter": self.changed_parameter,
            "base_parameter_value": self.base_parameter_value,
            "scenario_parameter_value": self.scenario_parameter_value,
            "base_score": self.base_score,
            "scenario_score": self.scenario_score,
            "base_band": self.base_band,
            "scenario_band": self.scenario_band,
            "score_delta": self.score_delta,
            "base_status": self.base_status,
            "scenario_status": self.scenario_status,
            "coverage": self.coverage,
            "confidence_grade": self.confidence_grade,
            "release_allowed": self.release_allowed,
            "blocked_reason": self.blocked_reason,
            "veto_status": self.veto_status,
            "is_synthetic": self.is_synthetic,
            "not_company_fact": self.not_company_fact,
            "not_publishable": self.not_publishable,
            "excluded_from_base_result": self.excluded_from_base_result,
            "input_capsule_digest": self.input_capsule_digest,
            "registry_digest": self.registry_digest,
            "scenario_contract_version": self.scenario_contract_version,
        }


def _scenario_id(
    *,
    scenario_type: str,
    dimension_id: str,
    component_id: str | None,
    changed_parameter: str,
    base_parameter_value: Any,
    scenario_parameter_value: Any,
    input_capsule_digest: str | None,
    registry_digest: str,
) -> str:
    """Deterministic scenario identity: canonical payload of the semantic
    parameters only. Excludes absolute paths, the run directory, JSON
    indentation, and any generation timestamp."""
    payload = {
        "scenario_type": scenario_type,
        "dimension_id": dimension_id,
        "component_id": component_id,
        "changed_parameter": changed_parameter,
        "base_parameter_value": base_parameter_value,
        "scenario_parameter_value": scenario_parameter_value,
        "input_capsule_digest": input_capsule_digest,
        "registry_digest": registry_digest,
        "scenario_contract_version": SCENARIO_CONTRACT_VERSION,
    }
    return cap._sha256_bytes(cap._canonical(payload))


def _mk_scenario(
    *,
    scenario_type: str,
    dimension_id: str,
    component_id: str | None,
    changed_parameter: str,
    base_parameter_value: Any,
    scenario_parameter_value: Any,
    base_score: float | None,
    base_band: str | None,
    base_status: str | None,
    result: dict[str, Any],
    grade: str | None,
    capsule_digest: str | None,
    registry_digest: str,
    is_synthetic: bool = False,
    not_company_fact: bool = False,
    not_publishable: bool = False,
    excluded_from_base_result: bool = False,
    release_allowed_override: bool | None = None,
    blocked_reason_override: str | None = None,
) -> SensitivityScenario:
    scenario_score = result.get("score")
    scenario_band = result.get("band")
    scenario_status = result.get("status")
    coverage = result.get("coverage_ratio")
    veto_status = scenario_status == "blocked_by_risk_veto"
    score_delta = (
        None
        if (scenario_score is None or base_score is None)
        else round(scenario_score - base_score, 4)
    )
    if release_allowed_override is not None:
        release_allowed = release_allowed_override
        blocked_reason = blocked_reason_override
    else:
        release_allowed = scenario_status == "ordinal_shadow"
        blocked_reason = None
        if veto_status:
            blocked_reason = "risk_veto"
        elif scenario_status == "insufficient_evidence":
            blocked_reason = "insufficient_evidence"
    sid = _scenario_id(
        scenario_type=scenario_type,
        dimension_id=dimension_id,
        component_id=component_id,
        changed_parameter=changed_parameter,
        base_parameter_value=base_parameter_value,
        scenario_parameter_value=scenario_parameter_value,
        input_capsule_digest=capsule_digest,
        registry_digest=registry_digest,
    )
    return SensitivityScenario(
        scenario_id=sid,
        scenario_type=scenario_type,
        dimension_id=dimension_id,
        component_id=component_id,
        changed_parameter=changed_parameter,
        base_parameter_value=base_parameter_value,
        scenario_parameter_value=scenario_parameter_value,
        base_score=base_score,
        scenario_score=scenario_score,
        base_band=base_band,
        scenario_band=scenario_band,
        score_delta=score_delta,
        base_status=base_status,
        scenario_status=scenario_status,
        coverage=coverage,
        confidence_grade=grade,
        release_allowed=release_allowed,
        blocked_reason=blocked_reason,
        veto_status=veto_status,
        is_synthetic=is_synthetic,
        not_company_fact=not_company_fact,
        not_publishable=not_publishable,
        excluded_from_base_result=excluded_from_base_result,
        input_capsule_digest=capsule_digest or "",
        registry_digest=registry_digest,
        scenario_contract_version=SCENARIO_CONTRACT_VERSION,
    )


def _summary_from_ledger(
    dimension_id: str,
    scenarios: list[SensitivityScenario],
    tolerance: float,
) -> dict[str, Any]:
    """Recompute a dimension's summary entirely from its ledger scenarios. This
    is the single source of truth used both to build the report and to validate
    it; any summary that cannot be derived from the ledger is a validator error."""
    if not scenarios:
        return {
            "dimension_id": dimension_id,
            "base_score": None,
            "base_band": None,
            "min_score": None,
            "max_score": None,
            "max_score_delta": None,
            "band_flip_count": 0,
            "insufficient_evidence_count": 0,
            "confidence_block_count": 0,
            "veto_block_count": 0,
            "scenario_count": 0,
            "scenario_type_counts": {},
            "stability_tolerance": tolerance,
            "stability_status": "NOT_STABLE",
            "production_readiness_reason": (
                "no scenarios in ledger; cannot verify stability"
            ),
        }
    base_score = scenarios[0].base_score
    base_band = scenarios[0].base_band
    scores = [s.scenario_score for s in scenarios if s.scenario_score is not None]
    min_score = min(scores) if scores else None
    max_score = max(scores) if scores else None
    max_delta = max_score - min_score if scores else None
    band_flips = sum(
        1 for s in scenarios if s.scenario_band is not None and s.scenario_band != base_band
    )
    insufficient = sum(1 for s in scenarios if s.scenario_status == "insufficient_evidence")
    veto = sum(1 for s in scenarios if s.scenario_status == "blocked_by_risk_veto")
    conf_block = sum(
        1
        for s in scenarios
        if s.scenario_type == "confidence_threshold" and not s.release_allowed
    )
    type_counts = dict(Counter(s.scenario_type for s in scenarios))
    stable = (
        max_delta is not None
        and max_delta <= tolerance
        and band_flips == 0
        and insufficient == 0
        and veto == 0
    )
    return {
        "dimension_id": dimension_id,
        "base_score": base_score,
        "base_band": base_band,
        "min_score": min_score,
        "max_score": max_score,
        "max_score_delta": None if max_delta is None else round(max_delta, 4),
        "band_flip_count": band_flips,
        "insufficient_evidence_count": insufficient,
        "confidence_block_count": conf_block,
        "veto_block_count": veto,
        "scenario_count": len(scenarios),
        "scenario_type_counts": type_counts,
        "stability_tolerance": tolerance,
        "stability_status": "STABLE" if stable else "NOT_STABLE",
        "production_readiness_reason": (
            "dimension stable across frozen scenario set"
            if stable
            else "dimension band or coverage changes under a frozen scenario"
        ),
    }


def _ledger_summary_gate_blocks(
    summary: dict[str, Any],
    scenarios: list[SensitivityScenario],
    grade: str,
    grade_value: float,
) -> dict[str, Any]:
    """Attach the coverage/confidence gate blocks, derived from the ledger so
    the summary stays reproducible from it."""
    cov_rows = [s for s in scenarios if s.scenario_type == "coverage_threshold"]
    cov_passes = [
        "pass" if s.scenario_status != "insufficient_evidence" else "fail" for s in cov_rows
    ]
    conf_rows = [s for s in scenarios if s.scenario_type == "confidence_threshold"]
    conf_passes = ["pass" if s.release_allowed else "fail" for s in conf_rows]
    summary["coverage_gate_sensitivity"] = {
        "thresholds": list(COVERAGE_THRESHOLDS),
        "passes": cov_passes,
        "gate_never_mutated_by_confidence": True,
    }
    summary["confidence_gate_sensitivity"] = {
        "grade": grade,
        "grade_value": grade_value,
        "thresholds": list(CONFIDENCE_THRESHOLDS),
        "passes": conf_passes,
        "coverage_gate_not_mutated": True,
    }
    return summary


def _confidence_grade_from_ledger(
    scenarios: list[SensitivityScenario],
) -> tuple[str, float]:
    """Recover the executed confidence grade solely from the ledger. The
    confidence-threshold scenarios carry the numeric grade as their
    ``base_parameter_value``; the grade string is the reverse lookup of
    ``GRADE_VALUE``. Used by the validator so it never trusts the stored
    summary's ``confidence_gate_sensitivity`` block."""
    conf = [s for s in scenarios if s.scenario_type == "confidence_threshold"]
    if not conf:
        return "low", 0.4
    value = conf[0].base_parameter_value
    grade = next((g for g, v in GRADE_VALUE.items() if v == value), "low")
    return grade, value


def recompute_dimension_summary_from_ledger(
    dimension_id: str,
    scenarios: list[SensitivityScenario],
    tolerance: float,
    confidence_grade: str,
    confidence_grade_value: float,
) -> dict[str, Any]:
    """Recompute a dimension's FULL summary (base metrics, gate blocks, and
    ``production_readiness_reason``) entirely from its ledger scenarios. This is
    the single source of truth used by both ``build_sensitivity_v6`` and
    ``validate_sensitivity_ledger``; any summary field that cannot be derived
    from the ledger is a validator error."""
    summary = _summary_from_ledger(dimension_id, scenarios, tolerance)
    return _ledger_summary_gate_blocks(summary, scenarios, confidence_grade, confidence_grade_value)


def build_sensitivity_v6(
    capsule: dict[str, Any], confidence: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Build the sensitivity v6 report with a full per-scenario ledger.

    The six frozen scenario classes are unchanged from v5. The summary of every
    scored dimension is recomputed entirely from the ledger (never from a
    side-channel), and the confidence-threshold scenarios are included in
    ``scenario_count``, ``scenario_type_counts``, and ``confidence_block_count``.
    ``stability_tolerance`` stays frozen at 1.0; NOT_STABLE is preserved unless
    the frozen scenario set independently proves otherwise.
    """
    registry = cap._load(cap.REGISTRY_PATH)
    policy = cap._load(cap.POLICY_PATH)
    registry_digest = cap._sha256_bytes(cap._canonical(registry))
    capsule_digest = capsule.get("capsule_digest")
    base = _run_for_registry(capsule, registry)
    all_scenarios: list[SensitivityScenario] = []
    dimensions: dict[str, Any] = {}

    for dim in cap.SCORED_DIMENSIONS:
        base_result = base[dim]
        base_score, base_band, base_status = _score_band(base_result)
        grade, grade_value = _confidence_grade(confidence, capsule, dim)
        default_gate = float(
            registry["dimensions"][dim].get(
                "minimum_coverage_gate", policy["default_coverage_gate"]
            )
        )
        scenarios: list[SensitivityScenario] = []

        # 1. weight perturbation
        for cid in registry["dimensions"][dim]["components"]:
            base_w = float(registry["dimensions"][dim]["components"][cid]["weight"])
            for factor in (1.25, 0.75):
                reg = _perturb_registry_weight(registry, dim, cid, factor)
                r = _run_for_registry(capsule, reg)[dim]
                scenarios.append(
                    _mk_scenario(
                        scenario_type="weight_perturbation",
                        dimension_id=dim,
                        component_id=cid,
                        changed_parameter="weight",
                        base_parameter_value=base_w,
                        scenario_parameter_value=round(base_w * factor, 6),
                        base_score=base_score,
                        base_band=base_band,
                        base_status=base_status,
                        result=r,
                        grade=grade,
                        capsule_digest=capsule_digest,
                        registry_digest=registry_digest,
                    )
                )

        # 2. leave-one-component-out
        for cid in registry["dimensions"][dim]["components"]:
            reg = copy.deepcopy(registry)
            reg["dimensions"][dim]["components"] = {
                k: v
                for k, v in registry["dimensions"][dim]["components"].items()
                if k != cid
            }
            r = _run_for_registry(capsule, reg)[dim]
            scenarios.append(
                _mk_scenario(
                    scenario_type="leave_one_component_out",
                    dimension_id=dim,
                    component_id=cid,
                    changed_parameter="component_removed",
                    base_parameter_value=cid,
                    scenario_parameter_value=None,
                    base_score=base_score,
                    base_band=base_band,
                    base_status=base_status,
                    result=r,
                    grade=grade,
                    capsule_digest=capsule_digest,
                    registry_digest=registry_digest,
                )
            )

        # 3. coverage-threshold perturbation
        for gate in COVERAGE_THRESHOLDS:
            reg = copy.deepcopy(registry)
            reg["dimensions"][dim]["minimum_coverage_gate"] = gate
            r = _run_for_registry(capsule, reg)[dim]
            scenarios.append(
                _mk_scenario(
                    scenario_type="coverage_threshold",
                    dimension_id=dim,
                    component_id=None,
                    changed_parameter="coverage_gate",
                    base_parameter_value=default_gate,
                    scenario_parameter_value=gate,
                    base_score=base_score,
                    base_band=base_band,
                    base_status=base_status,
                    result=r,
                    grade=grade,
                    capsule_digest=capsule_digest,
                    registry_digest=registry_digest,
                )
            )

        # 4. frozen transform alternatives (absolute-contract breakpoint scaling)
        snapshot = _snapshot_breakpoints()
        for factor in TRANSFORM_ALTERNATIVES:
            r = _run_transform_scenario(capsule, registry, dim, factor, snapshot)
            scenarios.append(
                _mk_scenario(
                    scenario_type="transform_alternative",
                    dimension_id=dim,
                    component_id=None,
                    changed_parameter="breakpoint_scale",
                    base_parameter_value=1.0,
                    scenario_parameter_value=factor,
                    base_score=base_score,
                    base_band=base_band,
                    base_status=base_status,
                    result=r,
                    grade=grade,
                    capsule_digest=capsule_digest,
                    registry_digest=registry_digest,
                )
            )

        # 5. confidence-threshold sensitivity (evaluated, never mutates coverage)
        for cth in CONFIDENCE_THRESHOLDS:
            release = grade_value >= cth
            scenarios.append(
                _mk_scenario(
                    scenario_type="confidence_threshold",
                    dimension_id=dim,
                    component_id=None,
                    changed_parameter="confidence_threshold",
                    base_parameter_value=grade_value,
                    scenario_parameter_value=cth,
                    base_score=base_score,
                    base_band=base_band,
                    base_status=base_status,
                    result=base_result,
                    grade=grade,
                    capsule_digest=capsule_digest,
                    registry_digest=registry_digest,
                    release_allowed_override=release,
                    blocked_reason_override=None if release else "confidence_block",
                )
            )

        # 6. missing-ROIC scenarios (enterprise_quality only)
        if dim == "enterprise_quality":
            # current_gap: the real base state (ROIC is a coverage gap); an
            # explicit audit scenario even though it matches the base result.
            scenarios.append(
                _mk_scenario(
                    scenario_type="missing_roic",
                    dimension_id=dim,
                    component_id="eq_roic",
                    changed_parameter="roic_mode",
                    base_parameter_value="current_gap",
                    scenario_parameter_value="current_gap",
                    base_score=base_score,
                    base_band=base_band,
                    base_status=base_status,
                    result=base_result,
                    grade=grade,
                    capsule_digest=capsule_digest,
                    registry_digest=registry_digest,
                )
            )
            # synthetic_neutral: a synthetic ROIC value, never a company fact.
            c_synth = _capsule_with_roic(capsule, "synthetic_neutral")
            r_synth = _run_for_registry(c_synth, registry)[dim]
            scenarios.append(
                _mk_scenario(
                    scenario_type="missing_roic",
                    dimension_id=dim,
                    component_id="eq_roic",
                    changed_parameter="roic_mode",
                    base_parameter_value="current_gap",
                    scenario_parameter_value="synthetic_neutral",
                    base_score=base_score,
                    base_band=base_band,
                    base_status=base_status,
                    result=r_synth,
                    grade=grade,
                    capsule_digest=capsule_digest,
                    registry_digest=registry_digest,
                    is_synthetic=True,
                    not_company_fact=True,
                    not_publishable=True,
                    excluded_from_base_result=True,
                )
            )
            # no_roic_component: ROIC removed from the registry entirely.
            reg_no = copy.deepcopy(registry)
            reg_no["dimensions"][dim]["components"] = {
                k: v
                for k, v in registry["dimensions"][dim]["components"].items()
                if k != "eq_roic"
            }
            r_no = _run_for_registry(capsule, reg_no)[dim]
            scenarios.append(
                _mk_scenario(
                    scenario_type="missing_roic",
                    dimension_id=dim,
                    component_id="eq_roic",
                    changed_parameter="roic_mode",
                    base_parameter_value="current_gap",
                    scenario_parameter_value="no_roic_component",
                    base_score=base_score,
                    base_band=base_band,
                    base_status=base_status,
                    result=r_no,
                    grade=grade,
                    capsule_digest=capsule_digest,
                    registry_digest=registry_digest,
                )
            )

        tolerance = float(registry["dimensions"][dim].get("stability_tolerance", 1.0))
        summary = recompute_dimension_summary_from_ledger(
            dim, scenarios, tolerance, grade, grade_value
        )
        dimensions[dim] = summary
        all_scenarios.extend(s.to_dict() for s in scenarios)

    report = {
        "schema": "petrochina_dimension_scoring_sensitivity_v6",
        "version": "6.0",
        "scenario_contract_version": SCENARIO_CONTRACT_VERSION,
        "scenarios": all_scenarios,
        "dimensions": dimensions,
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
    }
    report["ledger_digest"] = ledger_digest(report)
    return report


def ledger_digest(report: dict[str, Any]) -> str:
    """Digest of the full sensitivity v6 report, excluding the ledger_digest
    field itself (no recursive hashing)."""
    payload = {k: v for k, v in report.items() if k != "ledger_digest"}
    return cap._sha256_bytes(cap._canonical(payload))


def validate_sensitivity_ledger(report: dict[str, Any]) -> dict[str, Any]:
    """Independently recompute every dimension's summary and the ledger digest
    from the ledger. Any inconsistency is a validation failure."""
    errors: list[str] = []
    expected_digest = ledger_digest(report)
    if report.get("ledger_digest") != expected_digest:
        errors.append("ledger_digest mismatch")
    if report.get("schema") != "petrochina_dimension_scoring_sensitivity_v6":
        errors.append("schema is not sensitivity_v6")
    scenarios = report.get("scenarios", [])
    for dim in cap.SCORED_DIMENSIONS:
        dim_scen = [s for s in scenarios if s.get("dimension_id") == dim]
        tolerance = float(
            report["dimensions"][dim].get("stability_tolerance", 1.0)
        )
        objs = []
        for s in dim_scen:
            try:
                objs.append(SensitivityScenario(**s))
            except TypeError as exc:  # noqa: BLE001 - malformed ledger entry
                errors.append(f"{dim}: malformed scenario entry: {exc}")
                continue
        recomputed = recompute_dimension_summary_from_ledger(
            dim,
            objs,
            tolerance,
            *_confidence_grade_from_ledger(objs),
        )
        current = report["dimensions"][dim]
        for key, rv in recomputed.items():
            if key == "dimension_id":
                continue
            if current.get(key) != rv:
                errors.append(
                    f"{dim}.{key}: ledger recompute {rv!r} != report {current.get(key)!r}"
                )
    return {"status": "pass" if not errors else "fail", "errors": errors}
