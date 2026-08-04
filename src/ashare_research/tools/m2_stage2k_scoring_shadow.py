"""Fail-closed, deterministic non-production dimension-scoring shadow engine.

M2 Stage 2K. This module reads only committed JSON contracts and produces a
non-production four-dimension shadow scorecard plus a sensitivity report. It
never creates production scores, tables, Metric Results, or registry entries,
and it never computes an overall score.

The engine is offline and deterministic: no network, no database, no PRNG, no
absolute paths. Every input binds to a stable component ID in the registry.
"""

from __future__ import annotations

import argparse
import copy
import json
import math
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
CONFIG = ROOT / "config"
REPORTS = ROOT / "reports"

REGISTRY_PATH = CONFIG / "value_dimension_scoring_registry_v1.json"
POLICY_PATH = CONFIG / "value_dimension_scoring_policy_v1.json"
INPUTS_PATH = CONFIG / "value_dimension_scoring_shadow_inputs_v1.json"

DIMENSIONS = [
    "enterprise_quality",
    "valuation_attractiveness",
    "value_realization_capacity",
    "risk_and_evidence_integrity",
]

FORBIDDEN_OUTPUT_KEYS = {
    "overall_score",
    "rank",
    "recommendation",
    "target_price",
    "upside_probability",
    "portfolio_weight",
    "buy",
    "sell",
}

# Frozen transforms. Keys are (component_id, benchmark_mode, transform_version).
# Each value is a list of (x, y) breakpoints; score is piecewise-linear in x.
_ABSOLUTE_BREAKPOINTS: dict[str, list[tuple[float, float]]] = {
    "eq_gross_margin": [(0.0, 0.0), (0.20, 40.0), (0.30, 80.0), (0.40, 100.0)],
    "eq_operating_margin": [(0.0, 0.0), (0.08, 40.0), (0.15, 80.0), (0.25, 100.0)],
    "eq_np_yoy": [(-0.5, 0.0), (0.0, 40.0), (0.10, 80.0), (0.30, 100.0)],
    "eq_ocf_np": [(0.0, 0.0), (1.0, 40.0), (1.5, 60.0), (2.0, 80.0), (3.0, 100.0)],
    "eq_roe": [(0.0, 0.0), (0.06, 40.0), (0.10, 80.0), (0.20, 100.0)],
    "eq_roa": [(0.0, 0.0), (0.03, 40.0), (0.05, 80.0), (0.10, 100.0)],
    "eq_asset_liability": [(0.70, 0.0), (0.60, 40.0), (0.40, 80.0), (0.20, 100.0)],
    "eq_cash_coverage": [(0.0, 0.0), (0.30, 40.0), (0.50, 80.0), (1.0, 100.0)],
    "vr_ocf_dividend_coverage": [(0.0, 0.0), (1.0, 40.0), (3.0, 60.0), (5.0, 80.0), (10.0, 100.0)],
    "vr_fcf_dividend_coverage": [
        (0.0, 0.0), (0.5, 20.0), (1.0, 40.0), (1.5, 60.0), (2.0, 80.0), (3.0, 100.0)
    ],
    "vr_payout_ratio": [
        (0.0, 0.0), (0.30, 40.0), (0.40, 80.0), (0.60, 80.0), (0.80, 40.0), (1.0, 0.0)
    ],
    "vr_dps": [(0.0, 0.0), (0.20, 40.0), (0.40, 80.0), (0.60, 100.0)],
    "rk_gap_count": [(0.0, 100.0), (9.0, 60.0), (18.0, 40.0), (30.0, 0.0)],
    "rk_missing_evidence_slots": [(0.0, 100.0), (1.0, 80.0), (2.0, 60.0), (4.0, 40.0), (8.0, 0.0)],
}

_CATEGORICAL_SCORES = {
    "rk_veto_triggered": (0, 100.0),  # (triggered_value, score_when_zero)
    "rk_pit_integrity": {"pass": 100.0, "partial": 60.0, "fail": 0.0},
    "rk_evidence_freshness": {"current": 100.0, "stale": 40.0, "missing": 0.0},
    "vr_repurchase": {"no_event_found": 50.0, "event_found": 100.0},
}


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _walk_keys(value: Any) -> set[str]:
    if isinstance(value, dict):
        found = set(value)
        for child in value.values():
            found.update(_walk_keys(child))
        return found
    if isinstance(value, list):
        found: set[str] = set()
        for child in value:
            found.update(_walk_keys(child))
        return found
    return set()


def _piecewise(x: float, points: list[tuple[float, float]]) -> float:
    points = sorted(points, key=lambda p: p[0])
    if x <= points[0][0]:
        return points[0][1]
    if x >= points[-1][0]:
        return points[-1][1]
    for (x0, y0), (x1, y1) in zip(points, points[1:], strict=False):
        if x0 <= x <= x1:
            if x1 == x0:
                return y0
            return y0 + (x - x0) / (x1 - x0) * (y1 - y0)
    return points[-1][1]


def _band(score: float, band_map: dict[str, list[int]]) -> str:
    for name in ("A", "B", "C", "D", "E"):
        lo, hi = band_map[name]
        if lo <= score < hi:
            return name
    return "E"


def _component_score(
    component_id: str,
    component: dict[str, Any],
    raw: dict[str, Any],
    band_map: dict[str, list[int]],
) -> dict[str, Any]:
    """Return {score, status, eligible, covered, source, note} for one component."""
    direction = component.get("direction", "higher_better")
    benchmark = component.get("benchmark_mode", "absolute_contract")

    value = raw.get("value")
    status = raw.get("status", "present")

    # Coverage gap: present in registry but not computable (ROIC / dividend yield).
    if value is None or status == "not_computable_under_strict_evidence_contract":
        return {
            "score": None,
            "status": "coverage_gap",
            "eligible": True,
            "covered": False,
            "source": raw.get("source", ""),
            "note": "missing input is never zero; it is a coverage gap",
        }
    if status == "missing_input":
        return {
            "score": None,
            "status": "coverage_gap",
            "eligible": True,
            "covered": False,
            "source": raw.get("source", ""),
            "note": "missing input is never zero; it is a coverage gap",
        }

    if benchmark == "self_history_percentile":
        pct = raw.get("percentile_3y")
        if pct is None:
            return {
                "score": None,
                "status": "coverage_gap",
                "eligible": True,
                "covered": False,
                "source": raw.get("source", ""),
                "note": "no PIT percentile; not eligible",
            }
        pct = float(pct)
        score = (1.0 - pct) * 100.0 if direction == "lower_better" else pct * 100.0
        return {
            "score": round(score, 4),
            "status": "computed_shadow",
            "eligible": True,
            "covered": True,
            "source": raw.get("source", ""),
            "note": f"self-history percentile 3y={pct:.4f}",
        }

    if benchmark == "binary_or_categorical_evidence":
        if component_id in _CATEGORICAL_SCORES:
            mapping = _CATEGORICAL_SCORES[component_id]
            if isinstance(mapping, dict):
                score = mapping.get(str(value))
            else:
                triggered, score_when_zero = mapping
                score = score_when_zero if int(value) == triggered else 0.0
            if score is None:
                return {
                    "score": None,
                    "status": "coverage_gap",
                    "eligible": True,
                    "covered": False,
                    "source": raw.get("source", ""),
                    "note": "unrecognized categorical value",
                }
            return {
                "score": round(score, 4),
                "status": "computed_shadow",
                "eligible": True,
                "covered": True,
                "source": raw.get("source", ""),
                "note": f"categorical value={value}",
            }
        # Numeric-count evidence components (e.g. gap counts) use the frozen
        # piecewise transform even though their benchmark mode is categorical.
        points = _ABSOLUTE_BREAKPOINTS.get(component_id)
        if points:
            try:
                score = _piecewise(float(value), points)
            except (TypeError, ValueError):
                return {
                    "score": None,
                    "status": "coverage_gap",
                    "eligible": True,
                    "covered": False,
                    "source": raw.get("source", ""),
                    "note": "non-numeric categorical value",
                }
            return {
                "score": round(score, 4),
                "status": "computed_shadow",
                "eligible": True,
                "covered": True,
                "source": raw.get("source", ""),
                "note": f"categorical count={value}",
            }

    if benchmark == "absolute_contract":
        points = _ABSOLUTE_BREAKPOINTS.get(component_id)
        if not points:
            return {
                "score": None,
                "status": "not_trusted",
                "eligible": True,
                "covered": False,
                "source": raw.get("source", ""),
                "note": "no frozen transform registered",
            }
        try:
            score = _piecewise(float(value), points)
        except (TypeError, ValueError):
            return {
                "score": None,
                "status": "coverage_gap",
                "eligible": True,
                "covered": False,
                "source": raw.get("source", ""),
                "note": "non-numeric value",
            }
        return {
            "score": round(score, 4),
            "status": "computed_shadow",
            "eligible": True,
            "covered": True,
            "source": raw.get("source", ""),
            "note": "absolute_contract band",
        }

    return {
        "score": None,
        "status": "not_trusted",
        "eligible": True,
        "covered": False,
        "source": raw.get("source", ""),
        "note": "unsupported benchmark mode",
    }


def compute_dimension(
    dimension_id: str,
    registry: dict[str, Any],
    policy: dict[str, Any],
    inputs: dict[str, Any],
) -> dict[str, Any]:
    dim = registry["dimensions"][dimension_id]
    band_map = policy["band_map"]
    gate = dim.get("minimum_coverage_gate", policy["default_coverage_gate"])
    components = dim["components"]
    raw = inputs["components"]

    component_results: dict[str, Any] = {}
    eligible_weight = 0.0
    covered_weight = 0.0
    for cid, comp in components.items():
        weight = float(comp["weight"])
        eligible_weight += weight
        res = _component_score(cid, comp, raw.get(cid, {}), band_map)
        component_results[cid] = res
        if res["covered"]:
            covered_weight += weight

    coverage_ratio = covered_weight / eligible_weight if eligible_weight else 0.0
    missing_ids = [cid for cid, res in component_results.items() if not res["covered"]]

    # Veto gate: any triggered risk veto blocks the dimension.
    veto_triggered = int(raw.get("rk_veto_triggered", {}).get("value", 0))
    if veto_triggered > 0:
        return {
            "dimension_id": dimension_id,
            "score": None,
            "band": None,
            "status": "blocked_by_risk_veto",
            "eligible_weight": round(eligible_weight, 4),
            "covered_weight": round(covered_weight, 4),
            "coverage_ratio": round(coverage_ratio, 4),
            "missing_component_ids": missing_ids,
            "risk_veto_flags": {"triggered": veto_triggered},
            "components": component_results,
        }

    if coverage_ratio < gate:
        return {
            "dimension_id": dimension_id,
            "score": None,
            "band": None,
            "status": "insufficient_evidence",
            "eligible_weight": round(eligible_weight, 4),
            "covered_weight": round(covered_weight, 4),
            "coverage_ratio": round(coverage_ratio, 4),
            "missing_component_ids": missing_ids,
            "components": component_results,
        }

    # Weighted score over covered components with renormalization.
    weighted = 0.0
    effective_weights: dict[str, float] = {}
    for cid, res in component_results.items():
        if res["covered"]:
            weight = float(components[cid]["weight"])
            eff = weight / covered_weight
            effective_weights[cid] = round(eff, 6)
            weighted += eff * res["score"]

    score = round(weighted, 4)
    band = _band(score, band_map)
    return {
        "dimension_id": dimension_id,
        "score": score,
        "band": band,
        "status": "ordinal_shadow",
        "eligible_weight": round(eligible_weight, 4),
        "covered_weight": round(covered_weight, 4),
        "coverage_ratio": round(coverage_ratio, 4),
        "missing_component_ids": missing_ids,
        "effective_weights": effective_weights,
        "components": component_results,
    }


def compute_shadow(
    registry: dict[str, Any],
    policy: dict[str, Any],
    inputs: dict[str, Any],
) -> dict[str, Any]:
    dimensions = {}
    for dimension_id in DIMENSIONS:
        dimensions[dimension_id] = compute_dimension(
            dimension_id, registry, policy, inputs
        )
    return {
        "schema": "petrochina_dimension_scoring_shadow_v1",
        "version": "1.0",
        "symbol": inputs["symbol"],
        "score_date": inputs["score_date"],
        "non_production": True,
        "research_methodology_test_only": True,
        "overall_score_prohibited": True,
        "recommendation_prohibited": True,
        "score_eligible": False,
        "dimensions": dimensions,
        "risk_slots": inputs["risk_slots"],
        "gaps": inputs["gaps"],
    }


def _validate_contracts(
    registry: dict[str, Any],
    policy: dict[str, Any],
    inputs: dict[str, Any],
) -> list[str]:
    errors: list[str] = []
    if list(registry.get("dimensions", {}).keys()) != DIMENSIONS:
        errors.append("registry_dimensions")
    if "overall_score" in _walk_keys(registry):
        errors.append("registry_overall_score")
    if "overall_score" in _walk_keys(policy):
        errors.append("policy_overall_score")
    if list(registry.get("dimension_order", [])) != DIMENSIONS:
        errors.append("registry_dimension_order")
    for dim in DIMENSIONS:
        d = registry["dimensions"][dim]
        comp_sum = sum(float(c["weight"]) for c in d["components"].values())
        if not math.isclose(comp_sum, 1.0, abs_tol=1e-6):
            errors.append(f"registry_weight_sum:{dim}")
        for cid, comp in d["components"].items():
            if not comp.get("metric_role"):
                errors.append(f"registry_metric_role:{cid}")
            if not comp.get("direction"):
                errors.append(f"registry_direction:{cid}")
            if not comp.get("benchmark_mode"):
                errors.append(f"registry_benchmark:{cid}")
            if not comp.get("transform_version"):
                errors.append(f"registry_transform:{cid}")
            if not comp.get("prohibited_fallback"):
                errors.append(f"registry_fallback:{cid}")
            if comp.get("score_eligibility") is not False:
                errors.append(f"registry_score_eligible:{cid}")
    if "overall_score" in _walk_keys(inputs):
        errors.append("inputs_overall_score")
    return errors


def run_sensitivity(
    registry: dict[str, Any],
    policy: dict[str, Any],
    inputs: dict[str, Any],
) -> dict[str, Any]:
    """Run weight perturbation, leave-one-out, and coverage-gate sensitivity."""
    base = compute_shadow(registry, policy, inputs)
    results: dict[str, Any] = {"base": base, "perturbations": {}, "leave_one_out": {}}

    for dim in DIMENSIONS:
        perturbed = {}
        components = registry["dimensions"][dim]["components"]
        for cid in components:
            for sign, factor in (("plus", 1.25), ("minus", 0.75)):
                reg = copy.deepcopy(registry)
                reg["dimensions"][dim]["components"][cid]["weight"] = (
                    float(components[cid]["weight"]) * factor
                )
                out = compute_shadow(reg, policy, inputs)["dimensions"][dim]
                perturbed[f"{cid}_{sign}"] = {
                    "score": out["score"],
                    "band": out["band"],
                    "status": out["status"],
                }
        results["perturbations"][dim] = perturbed

        # leave-one-component-out
        loo = {}
        for cid in components:
            reg = copy.deepcopy(registry)
            reg["dimensions"][dim]["components"] = {
                k: v for k, v in components.items() if k != cid
            }
            out = compute_shadow(reg, policy, inputs)["dimensions"][dim]
            loo[cid] = {"score": out["score"], "band": out["band"], "status": out["status"]}
        results["leave_one_out"][dim] = loo

    # coverage-gate perturbation (perturb each dimension's own gate)
    gate_results = {}
    for gate in (0.4, 0.6, 0.8, 0.95):
        reg = copy.deepcopy(registry)
        for dim in DIMENSIONS:
            reg["dimensions"][dim]["minimum_coverage_gate"] = gate
        out = compute_shadow(reg, policy, inputs)
        gate_results[str(gate)] = {
            dim: {"score": out["dimensions"][dim]["score"],
                  "band": out["dimensions"][dim]["band"],
                  "status": out["dimensions"][dim]["status"]}
            for dim in DIMENSIONS
        }
    results["coverage_gate"] = gate_results

    return {"schema": "petrochina_dimension_scoring_sensitivity_v1", **results}


def validate_and_emit() -> dict[str, Any]:
    registry = _load(REGISTRY_PATH)
    policy = _load(POLICY_PATH)
    inputs = _load(INPUTS_PATH)
    errors = _validate_contracts(registry, policy, inputs)
    shadow = compute_shadow(registry, policy, inputs)
    sensitivity = run_sensitivity(registry, policy, inputs)
    return {
        "contract_errors": errors,
        "shadow": shadow,
        "sensitivity": sensitivity,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("compute", "validate"))
    parser.add_argument("--output", default="")
    args = parser.parse_args()

    result = validate_and_emit()
    if args.command == "compute" and args.output:
        out = Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps({"status": "pass", "output": str(out)}, ensure_ascii=False))
        return 0
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if not result["contract_errors"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
