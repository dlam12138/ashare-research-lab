"""Validate the committed M3 Stage 3E closeout boundary without data access."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

EXPECTED = {
    "base": "724322aa9b98d903cf5507302953180bf6d27f20",
    "upstream": "f206780dcb6fd4c3b9d30a92025b75974284afd16eecd24770d2f812256f0031",
    "pipeline": "ab224492ff85f391a29048dfeec740f9bbffb376de3408a5645a4552b51b9d1b",
    "model": "4958351a5c79c0eb96bbfda9ebaaca5e71ab2b07236eaa808b0a92ebc6e9756d",
    "cb_adapter": "9b0df296d4b5d3b7bdf382bd07cf8bdb4410fb6659edfe88da68a16b419fbf78",
    "cb_manifest": "7c3070a64cc5931807a7c35c95fcff66dffa6bb84310304365544c2bda3f8be2",
    "cc_robustness": "8b870ed2b4fe8b52110fbdbf9b6412498939421f018c337ecf3955678c30a527",
    "r1_adapter": "0875afa70a54e062b3ce6a0341d2c5387b3e0f32ff700204d2767dc71eff96d8",
    "r2_adapter": "c2ec3a088563f23106d4869c0c5d66b5f722a71effdf57aa8f35c76c764bbf03",
}


def _read(repo: Path, relative: str) -> dict:
    return json.loads((repo / relative).read_text(encoding="utf-8"))


def validate_closeout(repo_root: str | Path) -> list[str]:
    """Return violations; reads only committed repository JSON and README text."""
    repo = Path(repo_root)
    final = _read(repo, "reports/m3_stage3e_daily_mechanism_final_disposition_v1.json")
    gaps = _read(repo, "reports/m3_stage3e_explicit_evidence_gaps_v1.json")
    decision = _read(repo, "reports/m3_stage3e_milestone_closeout_decision_v1.json")
    cb = _read(repo, "reports/m3_stage3cb_primary_development_result_v1.json")
    cc = _read(repo, "reports/m3_stage3cc_registered_robustness_result_v1.json")
    r2 = _read(repo, "reports/m3_stage3dbr2_recovery_inconclusive_v1.json")
    violations: list[str] = []

    if final["canonical_base"] != EXPECTED["base"]:
        violations.append("Stage3E canonical base changed")
    if final["daily_mechanism_disposition"] != "M3_DAILY_MECHANISM_NOT_ESTABLISHED":
        violations.append("daily mechanism disposition is not exact")
    development = final["development"]
    for key, expected in {
        "primary_decision": "M3_PRIMARY_DEVELOPMENT_POSITIVE_ABNORMAL_PERFORMANCE_NOT_ESTABLISHED",
        "sample_start": "2015-03-16",
        "sample_end": "2022-12-30",
    }.items():
        if development[key] != expected:
            violations.append(f"development {key} changed")
    if (development["nobs"], development["crash_count"]) != (1902, 330):
        violations.append("development counts changed")
    if development["gamma"] != cb["gamma"] or development["bootstrap_ci"] != [
        cb["gamma_ci_lower"], cb["gamma_ci_upper"]
    ]:
        violations.append("development gamma or CI does not match Stage3CB")

    holdout = final["holdout"]
    if holdout["status"] != "UNSEALED_CONSUMED" or not holdout["consumed"]:
        violations.append("holdout consumption status changed")
    if holdout["accepted_primary_execution_count"] != 0 or holdout["primary_statistic_observed"]:
        violations.append("holdout primary was incorrectly accepted")
    if holdout["final_status"] != "M3_HOLDOUT_PRIMARY_INCONCLUSIVE_TECHNICAL_OR_COVERAGE_GAP":
        violations.append("holdout disposition changed")
    if holdout["holdout_gamma"] is not None or holdout["gamma_computed"]:
        violations.append("holdout gamma was incorrectly materialized")
    if holdout["minimum_market_coverage"] >= holdout["coverage_gate"]:
        violations.append("holdout coverage gate is incorrectly passed")

    anchor = cc["primary_anchor"]
    if (
        not anchor["reversal_prohibited"]
        or anchor["primary_decision"] != development["primary_decision"]
    ):
        violations.append("Stage3CC primary anchor was reversed")
    if cc["development_evidence_ceiling"] != 2 or cc["development_evidence_level"] is not None:
        violations.append("development evidence classification changed")
    if not all(value is False for value in cc["threshold_robustness"]["bh_reject"]):
        violations.append("BH threshold result changed")
    for key, value in final["development_robustness"]["registered_not_executed"].items():
        if cc["registered_not_executed"].get(key) != value:
            violations.append(f"registered gap status changed: {key}")
    if r2["accepted_primary_execution_count"] != 0 or r2["gamma_computed"]:
        violations.append("R2 holdout anchor changed")

    if decision["decision"] != "M3_MILESTONE_CONDITIONAL_CLOSEOUT_ALLOWED":
        violations.append("conditional closeout decision changed")
    if decision["milestone_status"] != "CONDITIONALLY_CLOSED":
        violations.append("milestone status changed")
    for key in ("new_holdout_recovery_allowed", "minute_escalation_allowed", "m4_authorized"):
        if decision[key]:
            violations.append(f"unauthorized continuation flag enabled: {key}")

    if len(gaps["gaps"]) != 9 or {item["id"] for item in gaps["gaps"]} != {
        f"GAP_{number:03d}" for number in range(1, 10)
    }:
        violations.append("evidence gap register is incomplete")
    if not all(item["not_automatic_todo"] for item in gaps["gaps"]):
        violations.append("evidence gaps became automatic todos")
    readme = (repo / "README.md").read_text(encoding="utf-8")
    for required in (
        "CONDITIONALLY CLOSED",
        "M3_DAILY_MECHANISM_NOT_ESTABLISHED",
        "0.9736963544070143",
    ):
        if required not in readme:
            violations.append(f"README missing factual marker: {required}")
    if "148 eligible securities" in readme:
        violations.append("README retains stale 148-eligible statement")

    recorded = final["identity_anchors"]
    identity_map = {
        "upstream_inventory_sha256": "upstream",
        "pipeline_sha256": "pipeline",
        "model_sha256": "model",
        "stage3cb_adapter_sha256": "cb_adapter",
        "stage3cb_manifest_sha256": "cb_manifest",
        "stage3cc_robustness_sha256": "cc_robustness",
        "stage3dbr1_adapter_sha256": "r1_adapter",
        "stage3dbr2_adapter_sha256": "r2_adapter",
    }
    for field, expected_key in identity_map.items():
        if recorded[field] != EXPECTED[expected_key]:
            violations.append(f"frozen identity changed: {field}")
    return violations


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("repo_root", nargs="?", default=".")
    args = parser.parse_args()
    violations = validate_closeout(args.repo_root)
    if violations:
        for violation in violations:
            print(f"FAIL: {violation}")
        return 1
    print("PASS: M3 Stage 3E closeout boundary validated; no external data access")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
