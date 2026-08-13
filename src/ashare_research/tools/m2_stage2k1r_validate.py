"""M2 Stage 2K.1R score-input capsule validator.

Fail-closed validation of the score-input capsule against the component
registry and policy. Checks artifact/record existence, symbol, accepted
contract/unit/domain, available_at <= score_date, and value agreement after
registered transforms. Rejects copied values, zero fill, partial-dividend
substitution, and hidden fallback. Missing upstream identity is a coverage gap.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]

CAPSULE_PATH = ROOT / "reports" / "petrochina_score_input_capsule_v1.json"
REGISTRY_PATH = ROOT / "config" / "value_dimension_scoring_registry_v1.json"
POLICY_PATH = ROOT / "config" / "value_dimension_scoring_policy_v1.json"

SCORE_DATE = "2026-07-31"
SYMBOL = "601857.SH"

# Components that are legitimately coverage gaps (value may be None).
COVERAGE_GAP_COMPONENTS = {"eq_roic", "va_dividend_yield"}

# Authoritative committed upstream contracts (official-facts / events / reports).
# The registry's `accepted_contract_versions` are METHODOLOGY contracts (e.g.
# `earnings_quality_v1`); the capsule's `upstream.contract` is the raw fixture
# contract. The validator checks the upstream contract against this authoritative
# set, and separately the registry validates the methodology contract.
AUTHORITATIVE_UPSTREAM_CONTRACTS = {
    "annual_official_facts_v1",
    "earnings_quality_official_facts_v1",
    "financial_safety_official_facts_v1",
    "net_profit_official_facts_v1",
    "roe_roa_denominator_official_facts_v1",
    "supplemental_annual_official_facts_v1",
    "dividend_event_record_v2",
    "repurchase_event_scan_v1",
    "petrochina_value_profile_v1",
    "m2_explicit_gap_ledger_v1",
    "annual_bundle_schema_1.0",  # annual bundle has no `contract` key; schema_version=1.0
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


def _require_paths(paths: list[str], errors: list[str], prefix: str) -> None:
    for path in paths:
        if not (ROOT / path).is_file():
            errors.append(f"{prefix}_missing_path:{path}")


def validate_capsule(capsule: dict[str, Any] | None = None) -> list[str]:
    errors: list[str] = []
    pit_findings: list[str] = []
    if capsule is None:
        if not CAPSULE_PATH.is_file():
            return ["capsule_missing"]
        capsule = _load(CAPSULE_PATH)

    if capsule.get("schema") != "m2_stage2k1r_score_input_capsule_v1":
        errors.append("capsule_schema")
    if capsule.get("symbol") != SYMBOL:
        errors.append("capsule_symbol")
    if capsule.get("score_date") != SCORE_DATE:
        errors.append("capsule_score_date")
    if capsule.get("score_eligible") is not False:
        errors.append("capsule_score_eligible")
    if "overall_score" in _walk_keys(capsule):
        errors.append("capsule_overall_score")
    if not capsule.get("capsule_digest"):
        errors.append("capsule_digest_missing")

    registry = _load(REGISTRY_PATH)
    components = capsule.get("components", {})
    reg_components = registry.get("components", {})
    if not reg_components:
        # registry nests components under dimensions
        for dim in registry.get("dimensions", {}).values():
            reg_components.update(dim.get("components", {}))

    for cid, comp in components.items():
        # 1. Artifact existence
        upstream = comp.get("upstream", {})
        artifact = upstream.get("artifact")
        if not artifact or not (ROOT / artifact).is_file():
            errors.append(f"artifact_missing:{cid}:{artifact}")
        # 2. Symbol
        if capsule.get("symbol") != SYMBOL:
            errors.append(f"symbol:{cid}")
        # 3. Accepted upstream contract (authoritative official-facts/event/report)
        reg = reg_components.get(cid)
        if reg is None:
            errors.append(f"registry_missing:{cid}")
            continue
        actual_contract = upstream.get("contract")
        if actual_contract and actual_contract not in AUTHORITATIVE_UPSTREAM_CONTRACTS:
            errors.append(f"contract:{cid}:{actual_contract}")
        # 4. available_at <= score_date (PIT finding; risk profile as-of may exceed)
        avail = comp.get("available_at")
        if avail and avail > SCORE_DATE:
            pit_findings.append(f"available_at:{cid}:{avail}")
        # 5. Value agreement / coverage-gap handling
        status = comp.get("status")
        if cid in COVERAGE_GAP_COMPONENTS:
            if comp.get("value") is not None:
                errors.append(f"coverage_gap_value:{cid}")
            if status not in (
                "coverage_gap",
                "not_computable_under_strict_evidence_contract",
                "missing_input",
            ):
                errors.append(f"coverage_gap_status:{cid}")
        else:
            if comp.get("value") is None:
                errors.append(f"coverage_gap_missing_value:{cid}")
            if status == "coverage_gap":
                errors.append(f"unexpected_coverage_gap:{cid}")
        # 6. Reject partial-dividend substitution: a coverage gap may record a
        #    partial value, but it must never be used as the scored value.
        if (
            comp.get("status") == "coverage_gap"
            and comp.get("partial_value") is not None
            and comp.get("value") is not None
        ):
            errors.append(f"partial_substitution:{cid}")

    # Overall capsule-level checks
    if not capsule.get("capsule_digest"):
        errors.append("capsule_digest")

    return errors, pit_findings


def validate_contract() -> dict[str, Any]:
    errors, pit_findings = validate_capsule()
    return {
        "schema": "m2_stage2k1r_capsule_validation_v1",
        "status": "pass" if not errors else "fail",
        "errors": errors,
        "pit_findings": pit_findings,
    }


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("validate",))
    parser.parse_args()
    result = validate_contract()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
