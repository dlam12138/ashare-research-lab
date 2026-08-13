"""M2 Stage 2K.1R non-production shadow engine (capsule-backed).

Reads the score-input capsule (committed-artifact-only) plus the registry,
policy, and confidence contract, and emits a four-dimension shadow scorecard
with score/coverage/evidence_confidence separated per dimension. The risk
dimension is reported as separate `risk_veto_status` and `evidence_integrity`
outputs (no single merged numeric score), per the semantic reassessment.

No production scores, no overall score, no ranking, no recommendation, no
target price. score_eligible stays false.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ashare_research.tools import m2_stage2k1r_confidence as confidence_mod
from ashare_research.tools import m2_stage2k1r_validate as validate_mod
from ashare_research.tools import m2_stage2k_scoring_shadow as stage2k

ROOT = Path(__file__).resolve().parents[3]
CONFIG = ROOT / "config"
REPORTS = ROOT / "reports"

REGISTRY_PATH = CONFIG / "value_dimension_scoring_registry_v1.json"
POLICY_PATH = CONFIG / "value_dimension_scoring_policy_v1.json"
CAPSULE_PATH = REPORTS / "petrochina_score_input_capsule_v1.json"

DIMENSIONS = [
    "enterprise_quality",
    "valuation_attractiveness",
    "value_realization_capacity",
    "risk_and_evidence_integrity",
]

# Risk dimension is reported as separate statuses, not a merged numeric score.
RISK_DIMENSION = "risk_and_evidence_integrity"


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _capsule_to_inputs(capsule: dict[str, Any], registry: dict[str, Any]) -> dict[str, Any]:
    """Convert the capsule's components into the shadow-inputs shape the
    Stage 2K scoring primitives expect (value/status/source/percentiles)."""
    components: dict[str, Any] = {}
    for cid, comp in capsule["components"].items():
        entry: dict[str, Any] = {
            "value": comp.get("value"),
            "status": comp.get("status", "present"),
            "source": comp.get("upstream", {}).get("artifact", ""),
            "score_input_id": comp.get("score_input_id"),
        }
        if comp.get("percentile_3y") is not None:
            entry["percentile_3y"] = comp["percentile_3y"]
        if comp.get("percentile_5y") is not None:
            entry["percentile_5y"] = comp["percentile_5y"]
        if comp.get("available_at"):
            entry["available_at"] = comp["available_at"]
        components[cid] = entry
    return {
        "schema": "m2_stage2k1r_shadow_inputs_v1",
        "symbol": capsule["symbol"],
        "score_date": capsule["score_date"],
        "non_production": True,
        "research_methodology_test_only": True,
        "overall_score_prohibited": True,
        "recommendation_prohibited": True,
        "score_eligible": False,
        "components": components,
    }


def _risk_status(capsule: dict[str, Any]) -> dict[str, Any]:
    comps = capsule["components"]
    veto = int(comps.get("rk_veto_triggered", {}).get("value") or 0)
    missing = int(comps.get("rk_missing_evidence_slots", {}).get("value") or 0)
    missing_ids = [
        comps.get("rk_missing_evidence_slots", {}).get("upstream", {}).get("record_id", "")
    ]
    return {
        "status": "clear" if veto == 0 else "blocked_by_risk_veto",
        "triggered_count": veto,
        "missing_evidence_slots": missing,
        "missing_evidence_ids": missing_ids,
        "non_compensatory": True,
    }


def _evidence_integrity(capsule: dict[str, Any], confidence: dict[str, Any]) -> dict[str, Any]:
    dim = confidence["dimensions"][RISK_DIMENSION]
    return {
        "grade": dim["grade"],
        "reasons": dim["reasons"],
        "supporting_ids": dim["supporting_ids"],
    }


def compute_shadow(capsule: dict[str, Any] | None = None) -> dict[str, Any]:
    if capsule is None:
        capsule = _load(CAPSULE_PATH)
    registry = _load(REGISTRY_PATH)
    policy = _load(POLICY_PATH)
    inputs = _capsule_to_inputs(capsule, registry)
    errors, pit_findings = validate_mod.validate_capsule(capsule)
    confidence = confidence_mod.compute_confidence(capsule, pit_findings)

    dimensions: dict[str, Any] = {}
    for dim in DIMENSIONS:
        if dim == RISK_DIMENSION:
            dimensions[dim] = {
                "dimension_id": dim,
                "representation": "status_outputs",
                "risk_veto_status": _risk_status(capsule),
                "evidence_integrity": _evidence_integrity(capsule, confidence),
                "evidence_confidence": confidence["dimensions"][dim],
                "no_merged_numeric_score": True,
            }
        else:
            result = stage2k.compute_dimension(dim, registry, policy, inputs)
            result["evidence_confidence"] = confidence["dimensions"][dim]
            dimensions[dim] = result

    return {
        "schema": "petrochina_dimension_scoring_shadow_v2",
        "version": "2.0",
        "symbol": capsule["symbol"],
        "score_date": capsule["score_date"],
        "non_production": True,
        "research_methodology_test_only": True,
        "overall_score_prohibited": True,
        "recommendation_prohibited": True,
        "score_eligible": False,
        "capsule_digest": capsule["capsule_digest"],
        "input_verification": {"status": "pass" if not errors else "fail", "errors": errors},
        "pit_findings": pit_findings,
        "dimensions": dimensions,
        "confidence": {d: confidence["dimensions"][d] for d in DIMENSIONS},
    }


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("compute", "validate"))
    parser.add_argument("--output", default="")
    args = parser.parse_args()
    shadow = compute_shadow()
    if args.command == "compute" and args.output:
        out = Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(shadow, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps({"status": "pass", "output": str(out)}, ensure_ascii=False))
        return 0
    print(json.dumps(shadow, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
