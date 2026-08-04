"""Fail-closed validators for the M2 Stage 2J conditional-closeout packet."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
REPORTS = ROOT / "reports"

REQUIRED_MODULE_IDS = {
    "data_foundation_dependency",
    "profitability_and_cash_flow_quality",
    "roe",
    "roa",
    "financial_safety",
    "dividend_realization",
    "repurchase_evidence",
    "pit_valuation",
    "valuation_history_and_stress_scenarios",
    "value_realization_layer",
    "risk_veto_layer",
    "roic",
    "one_page_value_profile",
    "scoring",
    "market_mechanism",
}
ALLOWED_MODULE_STATUSES = {
    "complete_trusted",
    "complete_with_explicit_gaps",
    "not_computable_under_strict_evidence_contract",
    "deferred_by_design",
    "not_started",
    "not_trusted",
}
RECOVERABILITY_STATUSES = {
    "finite_new_official_source_available",
    "already_exhausted_registered_source_universe",
    "not_separately_publicly_disclosed",
    "requires_methodology_relaxation",
    "unknown_source_recoverability",
}
ROIC_GAP_IDS = {f"M2G-ROIC-{index:03d}" for index in range(1, 8)}
FORBIDDEN_PROFILE_KEYS = {
    "score",
    "rating",
    "recommendation",
    "target_price",
    "buy",
    "sell",
}


def _load(relative_path: str) -> dict[str, Any]:
    return json.loads((ROOT / relative_path).read_text(encoding="utf-8"))


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


def _source_gap_keys() -> dict[str, set[tuple[Any, ...]]]:
    dividend = _load("events/dividend_source_evidence_2021_2026.json")
    dividend_keys = {
        (entry["source_evidence_id"],)
        for entry in dividend["entries"]
        if entry["source_type"] == "exchange_official"
        and entry["retrieval_status"] != "retrieved"
    }

    risk = _load("events/petrochina_bounded_search_register_v2.json")
    risk_keys = {
        (entry["search_register_id"],)
        for entry in risk["entries"]
        if entry["completeness"] is False
    }

    roic = _load("reports/petrochina_roic_stage2i2r_acquisition_result.json")
    roic_keys = {
        (cell["plan_acquisition_id"], cell["role_id"], cell["fiscal_year"])
        for cell in roic["cells"]
        if cell["extraction_result"] != "acquired_verified"
    }
    return {"stage2f": dividend_keys, "stage2h": risk_keys, "stage2i": roic_keys}


def _canonical_gap_keys(gaps: list[dict[str, Any]]) -> dict[str, set[tuple[Any, ...]]]:
    result: dict[str, set[tuple[Any, ...]]] = {
        "stage2f": set(),
        "stage2h": set(),
        "stage2i": set(),
    }
    for gap in gaps:
        ids = gap["evidence_search_record_ids"]
        stage = gap["originating_stage"]
        if stage == "M2_STAGE_2F1":
            result["stage2f"].add((ids[0],))
        elif stage == "M2_STAGE_2H":
            result["stage2h"].add((ids[0],))
        elif stage == "M2_STAGE_2I2R":
            acquisition_id = ids[0]
            role_by_gap = {
                "M2G-ROIC-001": "tax.operating_tax_expense",
                "M2G-ROIC-002": "invested_capital.associate_investment",
                "M2G-ROIC-003": "invested_capital.associate_investment",
                "M2G-ROIC-004": "invested_capital.joint_venture_investment",
                "M2G-ROIC-005": "invested_capital.joint_venture_investment",
                "M2G-ROIC-006": "invested_capital.non_operating_financial_assets",
                "M2G-ROIC-007": "invested_capital.non_operating_financial_assets",
            }
            fiscal_year = int(gap["fiscal_year_event_period"].removeprefix("FY"))
            result["stage2i"].add(
                (acquisition_id, role_by_gap[gap["gap_id"]], fiscal_year)
            )
    return result


def validate_completion_matrix() -> list[str]:
    errors: list[str] = []
    matrix = _load("reports/m2_value_assessment_completion_matrix.json")
    if matrix.get("schema") != "m2_module_status_v1":
        errors.append("matrix_schema")
    modules = matrix.get("modules", [])
    ids = [module.get("module_id") for module in modules]
    if len(ids) != len(set(ids)):
        errors.append("matrix_duplicate_module")
    if set(ids) != REQUIRED_MODULE_IDS:
        errors.append("matrix_required_modules")
    if matrix.get("milestone_status") != (
        "CONDITIONALLY_CLOSED_WITH_EXPLICIT_EVIDENCE_GAPS"
    ):
        errors.append("matrix_milestone_status")
    if matrix.get("m3_next_step") != "M3_NORTH_STAR_PREFLIGHT_ALLOWED":
        errors.append("matrix_m3_gate")
    for module in modules:
        module_id = module.get("module_id", "unknown")
        if module.get("status") not in ALLOWED_MODULE_STATUSES:
            errors.append(f"matrix_status:{module_id}")
        required_fields = {
            "scope",
            "supported_fiscal_years",
            "methodology_version",
            "acceptance_references",
            "current_artifact_references",
            "evidence_gap_ids",
            "trusted_conclusions",
            "prohibited_interpretations",
            "score_eligible",
            "production_readiness",
            "latest_validated_commit",
            "run_ci_references",
            "superseded_acceptance_references",
        }
        if not required_fields.issubset(module):
            errors.append(f"matrix_fields:{module_id}")
        if module.get("score_eligible") is not False:
            errors.append(f"matrix_score_eligible:{module_id}")
        _require_paths(
            module.get("acceptance_references", []), errors, f"matrix_acceptance:{module_id}"
        )
        _require_paths(
            module.get("current_artifact_references", []),
            errors,
            f"matrix_artifact:{module_id}",
        )
    by_id = {module["module_id"]: module for module in modules}
    if by_id.get("roic", {}).get("status") != (
        "not_computable_under_strict_evidence_contract"
    ):
        errors.append("matrix_roic_status")
    if set(by_id.get("roic", {}).get("evidence_gap_ids", [])) != ROIC_GAP_IDS:
        errors.append("matrix_roic_gaps")
    if by_id.get("scoring", {}).get("status") != "deferred_by_design":
        errors.append("matrix_scoring_status")
    if by_id.get("market_mechanism", {}).get("status") != "not_started":
        errors.append("matrix_market_status")
    return errors


def validate_gap_ledger() -> list[str]:
    errors: list[str] = []
    ledger = _load("reports/m2_explicit_gap_ledger.json")
    if ledger.get("schema") != "m2_explicit_gap_ledger_v1":
        errors.append("gap_schema")
    gaps = ledger.get("gaps", [])
    ids = [gap.get("gap_id") for gap in gaps]
    if len(ids) != len(set(ids)):
        errors.append("gap_duplicate_id")
    required_fields = {
        "gap_id",
        "originating_stage",
        "module",
        "symbol",
        "fiscal_year_event_period",
        "semantic_requirement",
        "status",
        "evidence_search_record_ids",
        "source_record_reference",
        "exact_missing_reason",
        "consequence",
        "affected_outputs",
        "blocks_m2_closeout",
        "blocks_scoring",
        "blocks_m3",
        "recoverability_classification",
        "allowed_future_action",
        "prohibited_fallback",
        "last_reviewed_date",
        "supersession_status",
    }
    for gap in gaps:
        gap_id = gap.get("gap_id", "unknown")
        if not required_fields.issubset(gap):
            errors.append(f"gap_fields:{gap_id}")
        if gap.get("status") != "current_explicit_gap":
            errors.append(f"gap_status:{gap_id}")
        if gap.get("supersession_status") != "current":
            errors.append(f"gap_supersession:{gap_id}")
        if gap.get("recoverability_classification") not in RECOVERABILITY_STATUSES:
            errors.append(f"gap_recoverability:{gap_id}")
        if gap.get("blocks_scoring") is not True:
            errors.append(f"gap_scoring:{gap_id}")
        if not gap.get("prohibited_fallback"):
            errors.append(f"gap_fallback:{gap_id}")

    source = _source_gap_keys()
    canonical = _canonical_gap_keys(gaps)
    for stage in source:
        if source[stage] != canonical[stage]:
            errors.append(f"gap_source_mismatch:{stage}")
    computed_counts = {stage: len(keys) for stage, keys in source.items()}
    count_contract = ledger.get("count_contract", {})
    if count_contract.get("source_counts") != computed_counts:
        errors.append("gap_source_counts")
    if count_contract.get("current_gap_count") != sum(computed_counts.values()):
        errors.append("gap_total_count")
    if len(gaps) != sum(computed_counts.values()):
        errors.append("gap_record_count")
    if {gap["gap_id"] for gap in gaps if gap["module"] == "roic"} != ROIC_GAP_IDS:
        errors.append("gap_roic_ids")
    return errors


def validate_profile() -> list[str]:
    errors: list[str] = []
    profile = _load("reports/petrochina_value_profile.json")
    capital_return = profile.get("capital_return", {})
    roic = capital_return.get("roic", {})
    expected = {
        "status": "not_computable_under_strict_evidence_contract",
        "decision_code": "ROIC_NOT_COMPUTABLE_UNDER_STRICT_EVIDENCE_CONTRACT",
        "shadow_status": "not_run",
        "production_metric_created": False,
        "score_eligible": False,
    }
    for key, value in expected.items():
        if roic.get(key) != value:
            errors.append(f"profile_roic:{key}")
    if set(roic.get("missing_gap_ids", [])) != ROIC_GAP_IDS:
        errors.append("profile_roic_gap_ids")
    forbidden_roic_numeric_keys = {
        "value",
        "value_decimal",
        "numeric_value",
        "estimate",
        "proxy_value",
    }
    if forbidden_roic_numeric_keys & set(roic):
        errors.append("profile_roic_numeric_key")
    if profile.get("integrated_layers", {}).get("roic") != (
        "not_computable_under_strict_evidence_contract"
    ):
        errors.append("profile_integrated_roic")
    if capital_return.get("roe", {}).get("status") != (
        "trusted_existing_results_unchanged"
    ):
        errors.append("profile_roe_status")
    if capital_return.get("roa", {}).get("status") != (
        "trusted_existing_results_unchanged"
    ):
        errors.append("profile_roa_status")
    forbidden = FORBIDDEN_PROFILE_KEYS & _walk_keys(profile)
    if forbidden:
        errors.append(f"profile_forbidden_keys:{sorted(forbidden)}")

    for path in (
        "reports/petrochina_value_profile_2021_2026.md",
        "reports/petrochina_value_profile_one_page.md",
    ):
        text = (ROOT / path).read_text(encoding="utf-8")
        for required in (
            "not_computable_under_strict_evidence_contract",
            "ROIC_NOT_COMPUTABLE_UNDER_STRICT_EVIDENCE_CONTRACT",
            "not_run",
            "false",
        ):
            if required not in text:
                errors.append(f"profile_markdown:{path}:{required}")
        for gap_id in sorted(ROIC_GAP_IDS):
            if gap_id not in text and "M2G-ROIC-001` through `M2G-ROIC-007" not in text:
                errors.append(f"profile_markdown_gap:{path}:{gap_id}")
    return errors


def validate_decision() -> list[str]:
    errors: list[str] = []
    text = (
        ROOT / "docs/decisions/ADR-ROIC-001-strict-evidence-non-computability.md"
    ).read_text(encoding="utf-8")
    required = (
        "Status: `accepted`",
        "ROIC_NOT_COMPUTABLE_UNDER_STRICT_EVIDENCE_CONTRACT",
        "No numeric ROIC",
        "shadow_status=not_run",
        "production_metric_created=false",
        "SCORING_DEFERRED_BY_DESIGN",
        "Reopen conditions",
        "evidence limitation",
    )
    for value in required:
        if value not in text:
            errors.append(f"decision_missing:{value}")
    return errors


def verify_artifact_manifest() -> list[str]:
    errors: list[str] = []
    manifest = _load("reports/m2_stage2j_artifact_manifest.json")
    if manifest.get("schema") != "m2_stage2j_artifact_manifest_v1":
        errors.append("manifest_schema")
    paths: list[str] = []
    for item in manifest.get("files", []):
        path = ROOT / item["logical_path"]
        paths.append(item["logical_path"])
        if not path.is_file():
            errors.append(f"manifest_missing:{item['logical_path']}")
            continue
        payload = path.read_bytes()
        if path.suffix.lower() in {".json", ".md", ".py", ".yml", ".yaml"}:
            payload = path.read_text(encoding="utf-8").replace("\r\n", "\n").encode()
        if len(payload) != item["byte_size"]:
            errors.append(f"manifest_size:{item['logical_path']}")
        if hashlib.sha256(payload).hexdigest() != item["sha256"]:
            errors.append(f"manifest_sha256:{item['logical_path']}")
    if len(paths) != len(set(paths)):
        errors.append("manifest_duplicate_path")
    return errors


def verify_contracts() -> dict[str, Any]:
    checks = {
        "completion_matrix": validate_completion_matrix(),
        "gap_ledger": validate_gap_ledger(),
        "value_profile": validate_profile(),
        "roic_decision": validate_decision(),
    }
    errors = [error for values in checks.values() for error in values]
    return {
        "schema": "m2_stage2j_contract_verification_v1",
        "status": "pass" if not errors else "fail",
        "north_star_decision": "M2_CONDITIONAL_CLOSEOUT_ALLOWED",
        "checks": {key: "pass" if not value else "fail" for key, value in checks.items()},
        "errors": errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "command", choices=("verify-contracts", "verify-artifacts")
    )
    args = parser.parse_args()
    if args.command == "verify-contracts":
        result = verify_contracts()
    else:
        errors = verify_artifact_manifest()
        result = {
            "schema": "m2_stage2j_artifact_verification_v1",
            "status": "pass" if not errors else "fail",
            "errors": errors,
        }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
