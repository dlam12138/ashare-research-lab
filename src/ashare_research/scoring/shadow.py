"""M2 Stage 2K.1R4A shadow scoring + risk status.

Builds the shadow v5 from the capsule and the confidence report. The risk
dimension is status outputs only (never a merged numeric score). The risk
status is a finite enum that never emits ``clear``: when no veto is triggered
but evidence is still missing it reports ``no_trigger_observed_with_missing_evidence``
instead of the previous misleading ``clear`` (problem #4). A complete absence
of risk is never claimed.
"""

from __future__ import annotations

from typing import Any

from ashare_research.scoring import capsule as cap

# Finite risk status enum. ``clear`` is intentionally absent.
RISK_STATUS_ENUM = {
    "blocked_by_risk_veto",
    "no_trigger_observed_with_missing_evidence",
    "no_trigger_observed_within_bounded_evidence",
    "not_trusted",
}


def _capsule_to_inputs(capsule: dict[str, Any]) -> dict[str, Any]:
    components: dict[str, Any] = {}
    for cid, comp in capsule["components"].items():
        entry: dict[str, Any] = {
            "value": comp.get("selected_value_decimal"),
            "status": (
                "present" if comp.get("selected_value_decimal") is not None else "coverage_gap"
            ),
            "source": (
                comp.get("resolved_records", [{}])[0].get("artifact_logical_path", "")
                if comp.get("resolved_records")
                else ""
            ),
            "score_input_id": comp.get("score_input_id"),
        }
        # ROIC remains a coverage gap for scoring: gap_count is evidence-integrity
        # signal, not a computable ROIC value. A score_scenario may override this
        # for sensitivity scenarios that synthesize a neutral ROIC value.
        if cid == "eq_roic":
            scenario = comp.get("score_scenario")
            if scenario == "synthetic_neutral":
                entry["value"] = comp.get("selected_value_decimal")
                entry["status"] = "synthetic_neutral"
                entry["is_synthetic"] = True
            else:
                entry["value"] = None
                entry["status"] = "not_computable_under_strict_evidence_contract"
        if comp.get("observation_set") and comp["observation_set"].get("percentile_3y") is not None:
            entry["percentile_3y"] = comp["observation_set"]["percentile_3y"]
        if comp.get("observation_set") and comp["observation_set"].get("percentile_5y") is not None:
            entry["percentile_5y"] = comp["observation_set"]["percentile_5y"]
        components[cid] = entry
    return {
        "schema": "m2_stage2k1r3_shadow_inputs_v1",
        "symbol": capsule["symbol"],
        "score_date": capsule["time_contract"]["scorecard_formed_at"],
        "non_production": True,
        "overall_score_prohibited": True,
        "recommendation_prohibited": True,
        "score_eligible": False,
        "components": components,
    }


def build_shadow(capsule: dict[str, Any], confidence: dict[str, Any]) -> dict[str, Any]:
    from ashare_research.tools import m2_stage2k_scoring_shadow as stage2k

    registry = cap._load(cap.REGISTRY_PATH)
    policy = cap._load(cap.POLICY_PATH)
    inputs = _capsule_to_inputs(capsule)
    dims: dict[str, Any] = {}
    for dim in cap.SCORED_DIMENSIONS:
        result = stage2k.compute_dimension(dim, registry, policy, inputs)
        result["evidence_confidence"] = confidence["dimensions"][dim]
        dims[dim] = result
    dims[cap.RISK_DIMENSION] = {
        "dimension_id": cap.RISK_DIMENSION,
        "representation": "status_outputs",
        "risk_veto_status": _risk_status(capsule),
        "evidence_integrity": confidence["dimensions"][cap.RISK_DIMENSION],
        "no_merged_numeric_score": True,
    }
    return {
        "schema": "petrochina_dimension_scoring_shadow_v5",
        "version": "5.0",
        "symbol": capsule["symbol"],
        "time_contract": capsule["time_contract"],
        "capsule_digest": capsule["capsule_digest"],
        "non_production": True,
        "overall_score_prohibited": True,
        "recommendation_prohibited": True,
        "score_eligible": False,
        "status": "pass",
        "dimensions": dims,
    }


def _risk_status(capsule: dict[str, Any]) -> dict[str, Any]:
    """Risk status with correct semantics. Never emits ``clear``. When there is
    no trigger but evidence is still missing, the honest status is
    ``no_trigger_observed_with_missing_evidence``. A complete absence of risk
    is never claimed."""
    veto = capsule["components"].get("rk_veto_triggered", {}).get("selected_value_decimal")
    missing = capsule["components"].get("rk_missing_evidence_slots", {}).get(
        "selected_value_decimal"
    )
    try:
        veto_n = int(veto) if veto is not None else None
    except (TypeError, ValueError):
        veto_n = None
    try:
        missing_n = int(missing) if missing is not None else None
    except (TypeError, ValueError):
        missing_n = None

    if veto_n is None or missing_n is None:
        status = "not_trusted"
    elif veto_n > 0:
        status = "blocked_by_risk_veto"
    elif missing_n > 0:
        status = "no_trigger_observed_with_missing_evidence"
    else:
        status = "no_trigger_observed_within_bounded_evidence"

    assert status in RISK_STATUS_ENUM, f"risk status {status} not in enum"
    return {
        "status": status,
        "triggered_count": 0 if veto_n is None else veto_n,
        "missing_evidence_slots": 0 if missing_n is None else missing_n,
        "complete_absence_claim": False,
        "non_compensatory": True,
    }
