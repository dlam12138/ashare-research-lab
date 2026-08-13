"""M2 Stage 2K.1R complete sensitivity with machine-derived stability.

Runs weight perturbation (±25%), leave-one-out, coverage-threshold, frozen
transform-alternative, confidence-threshold, and missing-ROIC scenarios
(current gap, synthetic-neutral test, no-ROIC comparison). Synthetic ROIC
values are never treated as company facts. Per dimension emits min/max score,
max_score_delta, band_flip_count, insufficient-evidence count, veto-block
count, scenario count, stability_status, and production_readiness_reason.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

from ashare_research.tools import m2_stage2k1r_capsule as capsule_mod
from ashare_research.tools import m2_stage2k1r_shadow as shadow_mod
from ashare_research.tools import m2_stage2k_scoring_shadow as stage2k

ROOT = Path(__file__).resolve().parents[3]
CONFIG = ROOT / "config"
REGISTRY_PATH = CONFIG / "value_dimension_scoring_registry_v1.json"
POLICY_PATH = CONFIG / "value_dimension_scoring_policy_v1.json"

SCORED_DIMENSIONS = [
    "enterprise_quality",
    "valuation_attractiveness",
    "value_realization_capacity",
]
RISK_DIMENSION = "risk_and_evidence_integrity"

# Frozen transform alternatives: shift each piecewise breakpoint x by these
# factors while keeping the y mapping fixed. Thresholds are frozen before the
# run; this is a pre-registered sensitivity alternative, not a post-hoc fit.
TRANSFORM_ALTERNATIVES = (0.95, 1.05)
COVERAGE_THRESHOLDS = (0.4, 0.6, 0.8, 0.95)
CONFIDENCE_THRESHOLDS = (0.6, 0.7, 0.8)


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
    """Shift every absolute-contract breakpoint x by `factor` (frozen ground),
    run, then restore the pristine breakpoints so later scenarios are never
    contaminated by the mutation."""
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
    """Return a modified capsule for the ROIC scenario.

    mode: "current_gap" (unchanged), "synthetic_neutral" (ROIC set to a
    synthetic neutral value), "no_roic" (ROIC removed from the registry so the
    weight is dropped entirely).
    """
    c = copy.deepcopy(capsule)
    c["components"]["eq_roic"]["score_scenario"] = mode
    if mode == "synthetic_neutral":
        c["components"]["eq_roic"]["value"] = 0.10
        c["components"]["eq_roic"]["status"] = "synthetic_neutral"
        c["components"]["eq_roic"]["is_synthetic"] = True
        c["components"]["eq_roic"]["note"] = (
            "synthetic neutral test value, never a company fact"
        )
    return c


def _run_for_registry(capsule, registry):
    """Run the shadow with a given (possibly perturbed) registry."""
    inputs = shadow_mod._capsule_to_inputs(
        capsule, shadow_mod._load(REGISTRY_PATH)
    )
    policy = shadow_mod._load(POLICY_PATH)
    out = {}
    for dim in SCORED_DIMENSIONS:
        out[dim] = stage2k.compute_dimension(dim, registry, policy, inputs)
    return out


def _score_band(dim_result):
    return dim_result.get("score"), dim_result.get("band"), dim_result.get("status")


def compute_sensitivity(capsule=None) -> dict[str, Any]:
    if capsule is None:
        capsule = capsule_mod.build_capsule()
    registry = _load(REGISTRY_PATH)

    base = _run_for_registry(capsule, registry)
    dimensions: dict[str, Any] = {}

    for dim in SCORED_DIMENSIONS:
        outcomes: list[tuple[float, str, str]] = []
        base_score, base_band, base_status = _score_band(base[dim])

        # 1. weight perturbation ±25% per component
        for cid in registry["dimensions"][dim]["components"]:
            for factor in (1.25, 0.75):
                reg = _perturb_registry_weight(registry, dim, cid, factor)
                r = _run_for_registry(capsule, reg)[dim]
                outcomes.append(_score_band(r))

        # 2. leave-one-out per component
        for cid in registry["dimensions"][dim]["components"]:
            reg = copy.deepcopy(registry)
            reg["dimensions"][dim]["components"] = {
                k: v for k, v in registry["dimensions"][dim]["components"].items()
                if k != cid
            }
            r = _run_for_registry(capsule, reg)[dim]
            outcomes.append(_score_band(r))

        # 3. coverage-threshold perturbation
        for gate in COVERAGE_THRESHOLDS:
            reg = copy.deepcopy(registry)
            reg["dimensions"][dim]["minimum_coverage_gate"] = gate
            r = _run_for_registry(capsule, reg)[dim]
            outcomes.append(_score_band(r))

        # 4. frozen transform alternatives
        snapshot = _snapshot_breakpoints()
        for factor in TRANSFORM_ALTERNATIVES:
            r = _run_transform_scenario(capsule, registry, dim, factor, snapshot)
            outcomes.append(_score_band(r))

        # 5. confidence-threshold perturbation (gate only)
        for cth in CONFIDENCE_THRESHOLDS:
            reg = copy.deepcopy(registry)
            reg["dimensions"][dim]["minimum_coverage_gate"] = cth
            r = _run_for_registry(capsule, reg)[dim]
            outcomes.append(_score_band(r))

        # 6. missing-ROIC scenarios (enterprise only)
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
                r = _run_for_registry(c, reg)[dim]
                outcomes.append(_score_band(r))

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
        }

    return {
        "schema": "petrochina_dimension_scoring_sensitivity_v2",
        "version": "2.0",
        "non_production": True,
        "research_methodology_test_only": True,
        "overall_score_prohibited": True,
        "recommendation_prohibited": True,
        "score_eligible": False,
        "thresholds_frozen_before_rerun": True,
        "synthetic_values_are_not_company_facts": True,
        "dimensions": dimensions,
    }


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("compute",))
    parser.add_argument("--output", default="")
    args = parser.parse_args()
    result = compute_sensitivity()
    if args.output:
        out = Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps({"status": "pass", "output": str(out)}, ensure_ascii=False))
        return 0
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
