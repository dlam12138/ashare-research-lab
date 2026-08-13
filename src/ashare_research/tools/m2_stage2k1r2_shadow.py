"""M2 Stage 2K.1R2 shadow scorecard v3 (fail-closed, v2 capsule).

Reads the v2 score-input capsule and the dual-clock time contract. Fail-closed:
if the v2 validator reports any error, no formal shadow scorecard is produced
(per time-contract rule 4). Risk dimension is reported as separate status
outputs (risk_veto_status + evidence_integrity), never a merged numeric score.
Confidence v2 is executed from the capsule's source tiers and attached to each
dimension. The v1 shadow v2 report is preserved as history.

scorecard_formed_at is derived from / verified against the maximum included
input available_at, never hand-hardcoded.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ashare_research.tools import m2_stage2k1r2_confidence as confidence_mod
from ashare_research.tools import m2_stage2k1r2_validate as validate_mod
from ashare_research.tools import m2_stage2k_scoring_shadow as stage2k

ROOT = Path(__file__).resolve().parents[3]
CAPSULE_PATH = ROOT / "reports" / "petrochina_score_input_capsule_v2.json"
REGISTRY_PATH = ROOT / "config" / "value_dimension_scoring_registry_v1.json"
POLICY_PATH = ROOT / "config" / "value_dimension_scoring_policy_v1.json"

DIMENSIONS = [
    "enterprise_quality",
    "valuation_attractiveness",
    "value_realization_capacity",
    "risk_and_evidence_integrity",
]
RISK_DIMENSION = "risk_and_evidence_integrity"


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _capsule_to_inputs(capsule: dict[str, Any], registry: dict[str, Any]) -> dict[str, Any]:
    """Convert the v2 capsule into the shadow-inputs shape the Stage 2K scoring
    primitives expect (value/status/source/percentiles)."""

    def _score_date(capsule: dict[str, Any]) -> str | None:
        return capsule.get("score_date") or capsule.get(
            "time_contract", {}
        ).get("scorecard_formed_at")

    components: dict[str, Any] = {}
    for cid, comp in capsule["components"].items():
        upstream_refs = comp.get("upstream_refs") or []
        entry: dict[str, Any] = {
            "value": comp.get("value"),
            "status": comp.get("status", "present"),
            "source": upstream_refs[0].get("artifact", "") if upstream_refs else "",
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
        "schema": "m2_stage2k1r2_shadow_inputs_v1",
        "symbol": capsule["symbol"],
        "score_date": _score_date(capsule),
        "market_data_as_of_date": capsule.get("time_contract", {}).get("market_data_as_of_date"),
        "scorecard_formed_at": capsule.get("time_contract", {}).get("scorecard_formed_at"),
        "non_production": True,
        "research_methodology_test_only": True,
        "overall_score_prohibited": True,
        "recommendation_prohibited": True,
        "score_eligible": False,
        "components": components,
    }


def _risk_status(capsule: dict[str, Any]) -> dict[str, Any]:
    comps = capsule["components"]
    veto_raw = comps.get("rk_veto_triggered", {}).get("value")
    missing_raw = comps.get("rk_missing_evidence_slots", {}).get("value")
    try:
        veto = int(veto_raw) if veto_raw is not None else 0
    except (TypeError, ValueError):
        veto = 0
    try:
        missing = int(missing_raw) if missing_raw is not None else 0
    except (TypeError, ValueError):
        missing = 0
    missing_ids = [
        comps.get("rk_missing_evidence_slots", {})
        .get("upstream_refs", [{}])[0]
        .get("record_id", "")
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

    validation = validate_mod.validate_capsule(capsule)
    formed_at = capsule.get("time_contract", {}).get("scorecard_formed_at")
    max_available = max(
        (c.get("available_at") or "" for c in capsule["components"].values()),
        default="",
    )
    formed_at_ok = formed_at is not None and formed_at >= max_available

    # Fail-closed: any validator error blocks a formal shadow scorecard.
    if validation["status"] != "pass" or not formed_at_ok:
        return {
            "schema": "petrochina_dimension_scoring_shadow_v3",
            "version": "3.0",
            "symbol": capsule["symbol"],
            "non_production": True,
            "research_methodology_test_only": True,
            "overall_score_prohibited": True,
            "recommendation_prohibited": True,
            "score_eligible": False,
            "status": "blocked_by_validation",
            "validation": {
                "status": validation["status"],
                "error_count": validation["error_count"],
                "errors": validation["errors"],
                "scorecard_formed_at_derived_ok": formed_at_ok,
            },
            "scorecard": None,
        }

    confidence = confidence_mod.compute_confidence(capsule)

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
        "schema": "petrochina_dimension_scoring_shadow_v3",
        "version": "3.0",
        "symbol": capsule["symbol"],
        "time_contract": capsule["time_contract"],
        "capsule_digest": capsule["capsule_digest"],
        "non_production": True,
        "research_methodology_test_only": True,
        "overall_score_prohibited": True,
        "recommendation_prohibited": True,
        "score_eligible": False,
        "status": "pass",
        "validation": {
            "status": validation["status"],
            "error_count": validation["error_count"],
            "scorecard_formed_at_derived_ok": formed_at_ok,
        },
        "scorecard_formed_at": formed_at,
        "max_input_available_at": max_available,
        "dimensions": dimensions,
    }


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("compute",))
    parser.add_argument("--output", default="reports/petrochina_dimension_scoring_shadow_v3.json")
    args = parser.parse_args()
    result = compute_shadow()
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "output": str(out)}, ensure_ascii=False))
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
