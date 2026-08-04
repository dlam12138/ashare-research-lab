"""M2 Stage 2K.1R per-dimension evidence-confidence computation.

Separates score/band from coverage from evidence_confidence. Reads the
score-input capsule, the component registry, the gap ledger, and the versioned
confidence contract, and emits a per-dimension confidence status/grade with
reasons and supporting IDs. ROIC absence lowers enterprise coverage/confidence
but is never zero; risk vetoes remain non-compensatory.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]

CAPSULE_PATH = ROOT / "reports" / "petrochina_score_input_capsule_v1.json"
REGISTRY_PATH = ROOT / "config" / "value_dimension_scoring_registry_v1.json"
CONFIDENCE_PATH = ROOT / "config" / "value_dimension_scoring_confidence_v1.json"
GAP_LEDGER_PATH = ROOT / "reports" / "m2_explicit_gap_ledger.json"

SCORE_DATE = "2026-07-31"

DIMENSIONS = [
    "enterprise_quality",
    "valuation_attractiveness",
    "value_realization_capacity",
    "risk_and_evidence_integrity",
]

# Dimension -> component ids (from the registry).
DIMENSION_COMPONENTS = {
    "enterprise_quality": [
        "eq_gross_margin", "eq_operating_margin", "eq_np_yoy", "eq_ocf_np",
        "eq_roe", "eq_roa", "eq_roic", "eq_asset_liability", "eq_cash_coverage",
    ],
    "valuation_attractiveness": [
        "va_pe", "va_pb", "va_ps", "va_fcf_yield", "va_dividend_yield",
    ],
    "value_realization_capacity": [
        "vr_ocf_dividend_coverage", "vr_fcf_dividend_coverage",
        "vr_payout_ratio", "vr_dps", "vr_repurchase",
    ],
    "risk_and_evidence_integrity": [
        "rk_veto_triggered", "rk_missing_evidence_slots", "rk_gap_count",
        "rk_pit_integrity", "rk_evidence_freshness",
    ],
}

# Stage gap -> dimension it lowers.
GAP_DIMENSION = {
    "stage2f": "value_realization_capacity",  # 9 dividend exchange-payload gaps
    "stage2h": "risk_and_evidence_integrity",  # 2 missing risk evidence slots
    "stage2i": "enterprise_quality",          # 7 ROIC gaps
}


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _gap_ids_by_stage(ledger: dict[str, Any]) -> dict[str, list[str]]:
    by_stage: dict[str, list[str]] = {"stage2f": [], "stage2h": [], "stage2i": []}
    for gap in ledger.get("gaps", []):
        stage = gap.get("originating_stage")
        if stage == "M2_STAGE_2F1":
            by_stage["stage2f"].append(gap["gap_id"])
        elif stage == "M2_STAGE_2H":
            by_stage["stage2h"].append(gap["gap_id"])
        elif stage == "M2_STAGE_2I2R":
            by_stage["stage2i"].append(gap["gap_id"])
    return by_stage


def _compute_grade(
    dimension_id: str,
    capsule_components: dict[str, Any],
    conf: dict[str, Any],
    pit_findings: list[str],
    gap_ids_by_stage: dict[str, list[str]],
) -> dict[str, Any]:
    comp_ids = DIMENSION_COMPONENTS[dimension_id]
    reasons: list[str] = []
    supporting_ids: list[str] = []
    grade = conf["grade_rules"]["start_grade"]  # "high"

    # 1. input verification
    unverified = [
        cid for cid in comp_ids
        if capsule_components.get(cid, {}).get("value") is None
        and cid not in ("eq_roic", "va_dividend_yield")
    ]
    if unverified:
        grade = "not_trusted"
        reasons.append(f"input_unverified:{','.join(unverified)}")
        supporting_ids.extend(unverified)

    # 2. coverage-gap components (ROIC / dividend yield) lower but never zero
    for cid in comp_ids:
        status = capsule_components.get(cid, {}).get("status")
        if status == "not_computable_under_strict_evidence_contract":
            reasons.append(f"roic_gap_present:{cid}")
            supporting_ids.extend(conf["roic_rule"]["gap_ids"])
        elif status == "coverage_gap":
            reasons.append(f"coverage_gap:{cid}")
            # a missing/partial input (e.g. dividend yield) is incomplete
            # evidence and lowers confidence, never a zero.
            grade = "medium"
            supporting_ids.append(cid)

    # 3. stage gap effects
    for stage, dim in GAP_DIMENSION.items():
        if dim == dimension_id and gap_ids_by_stage[stage]:
            supporting_ids.extend(gap_ids_by_stage[stage])
    if dimension_id == "value_realization_capacity" and gap_ids_by_stage["stage2f"]:
        grade = "medium"
        reasons.append("dividend_exchange_payload_gaps_present")
    if dimension_id == "risk_and_evidence_integrity" and gap_ids_by_stage["stage2h"]:
        grade = "medium"
        reasons.append("risk_missing_evidence_slots_present")
    if dimension_id == "enterprise_quality" and gap_ids_by_stage["stage2i"]:
        grade = "medium"
        reasons.append("roic_gaps_present")

    # 4. freshness / PIT findings
    for cid in comp_ids:
        for finding in pit_findings:
            if finding.startswith(f"available_at:{cid}:"):
                grade = "medium"
                reasons.append(f"pit_finding_available_at_after_score_date:{cid}")
                supporting_ids.append(cid)

    # 5. benchmark completeness (percentile sample counts) — only for computed
    #    percentiles; a coverage-gap component has no percentile to check.
    for cid in comp_ids:
        comp = capsule_components.get(cid, {})
        if not comp.get("status_is_computed"):
            continue
        eff = comp.get("effective_samples") or {}
        mn = comp.get("minimum_samples") or {}
        if isinstance(eff, dict) and isinstance(mn, dict):
            for window in ("3y", "5y"):
                if window in eff and window in mn and eff[window] < mn[window]:
                    grade = "low"
                    reasons.append(f"benchmark_completeness_below_minimum:{cid}:{window}")

    # 6. non-compensatory veto: if a veto is triggered, the dimension is blocked
    veto = capsule_components.get("rk_veto_triggered", {}).get("value", 0)
    if dimension_id == "risk_and_evidence_integrity" and int(veto or 0) > 0:
        grade = "not_trusted"
        reasons.append("risk_veto_triggered_non_compensatory")

    # de-duplicate supporting ids, keep order
    seen = set()
    supporting_ids = [i for i in supporting_ids if not (i in seen or seen.add(i))]

    return {
        "dimension_id": dimension_id,
        "grade": grade,
        "reasons": reasons,
        "supporting_ids": supporting_ids,
    }


def compute_confidence(
    capsule: dict[str, Any] | None = None,
    pit_findings: list[str] | None = None,
) -> dict[str, Any]:
    if capsule is None:
        capsule = _load(CAPSULE_PATH)
    if pit_findings is None:
        pit_findings = []
    conf = _load(CONFIDENCE_PATH)
    ledger = _load(GAP_LEDGER_PATH)
    gap_ids_by_stage = _gap_ids_by_stage(ledger)
    components = capsule.get("components", {})

    dimensions: dict[str, Any] = {}
    for dim in DIMENSIONS:
        dimensions[dim] = _compute_grade(
            dim, components, conf, pit_findings, gap_ids_by_stage
        )

    return {
        "schema": "petrochina_dimension_evidence_confidence_v1",
        "version": "1.0",
        "symbol": capsule.get("symbol"),
        "score_date": capsule.get("score_date"),
        "non_production": True,
        "research_methodology_test_only": True,
        "overall_score_prohibited": True,
        "recommendation_prohibited": True,
        "score_eligible": False,
        "confidence_contract": conf["schema"],
        "confidence_separate_from_score": True,
        "dimensions": dimensions,
    }


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("compute",))
    parser.parse_args()
    result = compute_confidence()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
