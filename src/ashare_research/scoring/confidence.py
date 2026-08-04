"""M2 Stage 2K.1R4A confidence.

Confidence v3 reads ONLY the validated lineage source tiers (never the
capsule's claimed source_tier). A valuation component with no computed
percentile is a coverage gap even when its manifest source tier is medium.
"""

from __future__ import annotations

from typing import Any

from ashare_research.scoring import capsule as cap

GRADE_ORDER = {"low": 0, "medium": 1, "high": 2}


def _tier_grade(tier: str) -> str:
    return {
        "computed_from_verified_canonical_inputs": "high",
        "canonical_fact_verified": "high",
        "event_verified": "medium",
        "committed_computed_report": "medium",
        "external_manifest_only": "medium",
        "bounded_search_complete": "medium",
        "external_verified_market_cache": "high",
        "coverage_gap": "low",
    }.get(tier, "low")


def build_confidence(capsule: dict[str, Any], lineage_report: dict[str, Any]) -> dict[str, Any]:
    """Confidence v3 reads ONLY the validated lineage source tiers, never the
    capsule's claimed source_tier."""
    if lineage_report.get("status") != "pass":
        return {
            "schema": "petrochina_dimension_evidence_confidence_v3",
            "version": "3.0",
            "symbol": cap.SYMBOL,
            "status": "blocked_by_lineage_validation",
            "confidence": None,
        }
    grades: dict[str, list[str]] = {d: [] for d in cap.DIMENSIONS}
    reasons: dict[str, list[str]] = {d: [] for d in cap.DIMENSIONS}
    supporting: dict[str, list[str]] = {d: [] for d in cap.DIMENSIONS}
    for cid, comp in capsule["components"].items():
        dim = comp["dimension_id"]
        tier = comp["resolved_source_tier"]
        # A valuation component with no computed percentile is a coverage gap
        # even though its manifest source tier is medium.
        obs = comp.get("observation_set") or {}
        if dim == "valuation_attractiveness" and obs.get("percentile_3y") is None:
            tier = "coverage_gap"
        grades[dim].append(_tier_grade(tier))
        if tier == "coverage_gap":
            reasons[dim].append(f"coverage_gap:{cid}")
            supporting[dim].extend(comp.get("gap_ids") or [cid])
    dims = {}
    for dim in cap.DIMENSIONS:
        present = [g for g in grades[dim] if g != "low"]
        has_gap = any(g == "low" for g in grades[dim])
        grade = (
            min(present, key=lambda g: GRADE_ORDER[g])
            if present
            else "low"
        )
        if has_gap and GRADE_ORDER[grade] > 1:
            grade = "medium"
        dims[dim] = {
            "dimension_id": dim,
            "grade": grade,
            "reasons": reasons[dim],
            "supporting_ids": supporting[dim],
        }
    return {
        "schema": "petrochina_dimension_evidence_confidence_v3",
        "version": "3.0",
        "symbol": cap.SYMBOL,
        "time_contract": capsule["time_contract"],
        "capsule_digest": capsule["capsule_digest"],
        "lineage_report_digest": lineage_report.get("report_digest"),
        "source_tier_registry_digest": cap._sha256_bytes(
            cap._canonical(cap._load(cap.UPSTREAM_REGISTRY)["source_tier_bindings"])
        ),
        "non_production": True,
        "overall_score_prohibited": True,
        "recommendation_prohibited": True,
        "score_eligible": False,
        "dimensions": dims,
    }
