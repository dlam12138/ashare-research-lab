"""M2 Stage 2K.1R2 evidence confidence v2 builder.

Executes the source-tier registry against the v2 capsule: every component's
source_tier is looked up in the contract to produce a per-component grade, and
the dimension grade is the fail-closed weakest grade among its components.
Confidence is kept separate from both the score and the coverage gate.

No hand-assigned grades; no merging confidence into score.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]

CONTRACT = ROOT / "config" / "value_dimension_scoring_confidence_v2.json"
CAPSULE = ROOT / "reports" / "petrochina_score_input_capsule_v2.json"

DIMENSION_ORDER = [
    "enterprise_quality",
    "valuation_attractiveness",
    "value_realization_capacity",
    "risk_and_evidence_integrity",
]

GRADE_ORDER = {"low": 0, "medium": 1, "high": 2}


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def compute_confidence(capsule: dict[str, Any] | None = None) -> dict[str, Any]:
    contract = _load(CONTRACT)
    if capsule is None:
        capsule = _load(CAPSULE)
    tier_registry = contract["source_tier_registry"]

    # per-component executed grades
    component_grades: dict[str, dict[str, Any]] = {}
    for cid, comp in capsule["components"].items():
        tier = comp.get("source_tier")
        grade = tier_registry.get(tier, {}).get("grade", "low")
        gap_ids = comp.get("gap_ids", [])
        component_grades[cid] = {
            "component_id": cid,
            "source_tier": tier,
            "grade": grade,
            "gap_ids": gap_ids,
        }

    dimensions: dict[str, Any] = {}
    for dim in DIMENSION_ORDER:
        dim_comps = _components_in_dimension(capsule, dim)

        reasons: list[str] = []
        supporting_ids: list[str] = []
        present_grades: list[str] = []
        has_gap = False
        for cid in dim_comps:
            cg = component_grades[cid]
            if cg["source_tier"] == "coverage_gap":
                has_gap = True
                reasons.append(f"coverage_gap:{cid}")
                supporting_ids.extend(cg["gap_ids"] or [cid])
                continue
            present_grades.append(cg["grade"])
            if cg["grade"] == "low":
                reasons.append(f"low_source_tier:{cid}")
                supporting_ids.extend(cg["gap_ids"] or [cid])

        # Weakest grade among present evidence; a coverage gap caps the
        # dimension at "medium" (documented gap, not zero evidence).
        if present_grades:
            dim_grade = min(present_grades, key=lambda g: GRADE_ORDER[g])
            if has_gap and GRADE_ORDER[dim_grade] > GRADE_ORDER["medium"]:
                dim_grade = "medium"
        else:
            dim_grade = "low"
        dimensions[dim] = {
            "dimension_id": dim,
            "grade": dim_grade,
            "component_grades": [component_grades[cid] for cid in dim_comps],
            "reasons": reasons,
            "supporting_ids": supporting_ids,
        }

    return {
        "schema": "petrochina_dimension_evidence_confidence_v2",
        "version": "2.0",
        "symbol": capsule["symbol"],
        "time_contract": capsule["time_contract"],
        "capsule_digest": capsule["capsule_digest"],
        "non_production": True,
        "research_methodology_test_only": True,
        "overall_score_prohibited": True,
        "recommendation_prohibited": True,
        "score_eligible": False,
        "confidence_contract": "value_dimension_scoring_confidence_v2",
        "confidence_separate_from_score": True,
        "confidence_separate_from_coverage": True,
        "source_tier_registry": contract["source_tier_registry"],
        "dimensions": dimensions,
    }


def _components_in_dimension(capsule: dict[str, Any], dim: str) -> list[str]:
    return [cid for cid, comp in capsule["components"].items() if comp.get("dimension_id") == dim]


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("compute",))
    parser.add_argument(
        "--output", default="reports/petrochina_dimension_scoring_confidence_v2.json"
    )
    args = parser.parse_args()
    result = compute_confidence()
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": "pass", "output": str(out)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
