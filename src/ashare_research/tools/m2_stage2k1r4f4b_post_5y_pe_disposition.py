"""Thin offline verifier and deterministic builder for R4F.4B disposition."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]

UPSTREAM_DECISIONS = {
    "R4F": (
        ROOT / "reports/m2_stage2k1r4f_decision.json",
        "VALUATION_SCORING_CONTRACT_MIGRATION_REQUIRED",
    ),
    "R4F.1": (
        ROOT / "reports/m2_stage2k1r4f1_decision.json",
        "VALUATION_SCORING_V2_MIGRATION_COMPLETE_CYCLE_CONTEXT_GAP_REMAINS",
    ),
    "R4F.2": (
        ROOT / "reports/m2_stage2k1r4f2_decision.json",
        "PE_CYCLE_CONTEXT_NORMALIZED_EARNINGS_PROTOTYPE_ALLOWED",
    ),
    "R4F.3": (
        ROOT / "reports/m2_stage2k1r4f3_decision.json",
        "PE_NORMALIZED_EARNINGS_PROTOTYPE_TRUSTED_HISTORICAL_FACT_GAPS_REMAIN",
    ),
    "R4F.3A": (
        ROOT / "reports/m2_stage2k1r4f3a_decision.json",
        "PE_3Y_HISTORICAL_BACKFILL_TRUSTED_VALIDATION_ALLOWED",
    ),
    "R4F.4": (
        ROOT / "reports/m2_stage2k1r4f4_decision.json",
        "PE_3Y_NORMALIZED_PE_MECHANICAL_GUARD_CONFIRMED_INDEPENDENT_CYCLE_VALIDATION_REQUIRED",
    ),
    "R4F.4A": (
        ROOT / "reports/m2_stage2k1r4f4a_decision.json",
        "PE_INDEPENDENT_CYCLE_VALIDATION_PROTOCOL_FROZEN_5Y_BACKFILL_REQUIRED",
    ),
    "R4F.4A1": (
        ROOT / "reports/m2_stage2k1r4f4a1_decision.json",
        "PE_5Y_BACKFILL_TRUSTED_INDEPENDENT_VALIDATION_NOT_TESTABLE_WITH_FROZEN_5Y_HISTORY",
    ),
}

READINESS = ROOT / "reports/petrochina_pe_normalized_earnings_5y_readiness_after_backfill_v1.json"
INVENTORY = ROOT / "reports/petrochina_pe_independent_cycle_episode_inventory_5y_v1.json"
OUTCOME = ROOT / "reports/petrochina_pe_independent_cycle_outcome_readiness_5y_v1.json"
POLICY = ROOT / "config/value_dimension_scoring_policy_v2.json"
SHADOW = ROOT / "reports/petrochina_dimension_scoring_shadow_v6.json"

PROTECTED_SHA256 = {
    "reports/m2_stage2k1r4f_decision.json": (
        "73ee0ccb444551882adc07745e881c4947ed3ecbf484264bfa5b7787107fa207"
    ),
    "config/value_dimension_scoring_registry_v2.json": (
        "9e43b1a296b6acd85b7b12ef2ee6b3f645b1252978e4a60fdb287d1ca279317d"
    ),
    "config/value_dimension_scoring_policy_v2.json": (
        "4c35a5363ba352433f807079dfc2af8bf7ddbf35f6f36d168f6dd06cbc89a3c8"
    ),
    "reports/petrochina_dimension_scoring_shadow_v6.json": (
        "a3c14ad9c4b5900ab8492b9f0e79608683fa66363d43e0c1c268f025356068fc"
    ),
    "reports/m2_stage2k1r4f4a_decision.json": (
        "a4378408060fdda90c771fb97e7eed2460500c62c5b7858d251378225d23cfe0"
    ),
    "reports/m2_stage2k1r4f4a1_decision.json": (
        "564efbc1fb6c1f929ec08980f94a70877e90133ac7c5fb0a01f5dae9162cc41d"
    ),
}

ARTIFACTS = {
    "matrix_json": "m2_stage2k1r4f4b_pe_method_disposition_matrix_v1.json",
    "matrix_md": "m2_stage2k1r4f4b_pe_method_disposition_matrix_v1.md",
    "decision": "m2_stage2k1r4f4b_pe_disposition_decision_v1.json",
}


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def canonical_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=1) + "\n"


def sha256(path: Path) -> str:
    text = path.read_text(encoding="utf-8").replace("\r\n", "\n").replace("\r", "\n")
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def verify_upstream() -> list[str]:
    failures: list[str] = []
    for stage, (path, expected) in UPSTREAM_DECISIONS.items():
        actual = load(path).get("decision")
        if actual != expected:
            failures.append(f"{stage} decision: expected {expected}, got {actual}")

    readiness = load(READINESS)["5y_gate"]
    expected_readiness = {
        "required_days": 1211,
        "ready_days": 1211,
        "blocked_days": 0,
        "status": "READY",
    }
    if readiness != expected_readiness:
        failures.append(f"5Y readiness mismatch: {readiness!r}")

    inventory = load(INVENTORY)
    inventory_expected = {
        "candidate_contiguous_regimes": 1,
        "observed_onset_count": 0,
        "left_censored_episode_count": 1,
        "valid_onset_anchored_episodes": 0,
    }
    for key, expected in inventory_expected.items():
        if inventory.get(key) != expected:
            failures.append(f"inventory {key}: expected {expected}, got {inventory.get(key)}")

    outcome = load(OUTCOME)
    outcome_expected = {
        "protocol_valid_mature_4q_episode_count": 0,
        "protocol_valid_mature_8q_episode_count": 0,
        "future_eps_values_read": False,
        "current_5y_validation_executable": False,
    }
    for key, expected in outcome_expected.items():
        if outcome.get(key) != expected:
            failures.append(f"outcome {key}: expected {expected}, got {outcome.get(key)}")

    upstream = load(UPSTREAM_DECISIONS["R4F.4A1"][0])
    boundary_expected = {
        "automatic_history_extension_beyond_5y": "PROHIBITED",
        "brent": "NOT_ACQUIRED",
        "pe_numeric_scoring": "BLOCKED_UNCHANGED",
        "production_scoring": "NOT_AUTHORIZED",
        "next_action": "STOP_FOR_NORTH_STAR_REVIEW",
    }
    for key, expected in boundary_expected.items():
        if upstream.get(key) != expected:
            failures.append(f"R4F.4A1 {key}: expected {expected}, got {upstream.get(key)}")

    policy = load(POLICY)
    shadow = load(SHADOW)["dimensions"]["valuation_attractiveness"]
    if not policy["missingness_rules"]["missing_never_zero"]:
        failures.append("R4F.1 missing-never-zero policy is not frozen")
    if policy["hard_gap_policy"]["blocked_equals_zero"]:
        failures.append("R4F.1 hard gap is incorrectly equal to zero")
    if not shadow["score"] is shadow["band"] is None:
        failures.append("valuation score/band must both remain null")
    if shadow["components"]["va_pe"]["score"] is not None:
        failures.append("PE component score must remain null")
    if shadow["eligible_weight"] != 1.0 or shadow["covered_weight"] != 0.6:
        failures.append("registered valuation weights changed or were renormalized")

    for relative, expected in PROTECTED_SHA256.items():
        actual = sha256(ROOT / relative)
        if actual != expected:
            failures.append(f"protected hash mismatch: {relative}: {actual}")
    return failures


def build_matrix() -> dict[str, Any]:
    return {
        "schema": "m2_stage2k1r4f4b_pe_method_disposition_matrix_v1",
        "stage": "M2_STAGE_2K1R4F4B",
        "subject": "601857.SH",
        "basis": "FROZEN_5Y_INDEPENDENT_VALIDATION_NOT_TESTABLE",
        "selection_rule": (
            "SELECT_THE_MOST_AUDITABLE_NORTH_STAR_ALIGNED_OPTION_"
            "WITHOUT_EX_POST_SCOPE_EXPANSION"
        ),
        "candidates": [
            {
                "candidate": "EXTEND_HISTORY_GT_5Y",
                "north_star_value": "MEDIUM",
                "methodological_risk": "HIGH",
                "scope_expansion": "HIGH",
                "incremental_data_cost": "HIGH",
                "reusability": "MEDIUM",
                "current_protocol_allowed": False,
                "acquisition_performed": False,
                "decision": "REJECT_FOR_CURRENT_M2",
                "reason": (
                    "Would change the pre-frozen 5Y stop boundary after observing the result."
                ),
            },
            {
                "candidate": "ADD_COMMODITY_AND_INDUSTRY_CYCLE_CONTEXT",
                "north_star_value": "HIGH",
                "methodological_value": "HIGH",
                "methodological_risk": "MEDIUM",
                "scope_expansion": "MEDIUM_HIGH",
                "belongs_to_m2": "WEAK",
                "belongs_to_m3": "STRONG",
                "current_protocol_allowed": False,
                "acquisition_performed": False,
                "decision": "DEFER_TO_MECHANISM_RESEARCH",
                "reason": (
                    "Oil and industry controls are North-Star mechanism variables, not an "
                    "ex-post rescue for M2 PE scoring."
                ),
            },
            {
                "candidate": "MULTI_ISSUER_OR_PEER_VALIDATION",
                "north_star_value": "MEDIUM",
                "methodological_value": "MEDIUM",
                "methodological_risk": "MEDIUM",
                "scope_expansion": "VERY_HIGH",
                "peer_dependency": "HIGH",
                "current_m2_need": "LOW",
                "current_protocol_allowed": False,
                "acquisition_performed": False,
                "decision": "DEFER",
                "reason": (
                    "The MVP requires one demonstrator; peer acquisition would turn this "
                    "bounded disposition into an industry study."
                ),
            },
            {
                "candidate": "KEEP_PE_DESCRIPTIVE_DEFER_NUMERIC_SCORING",
                "north_star_value": "HIGH",
                "methodological_value": "HIGH",
                "methodological_risk": "LOW",
                "scope_expansion": "LOW",
                "auditability": "HIGH",
                "future_reopenable": True,
                "current_protocol_allowed": True,
                "acquisition_performed": False,
                "decision": "SELECT",
                "reason": (
                    "Retains trusted descriptive evidence while limiting claims to what "
                    "frozen evidence can support."
                ),
            },
        ],
        "selected_candidate": "KEEP_PE_DESCRIPTIVE_DEFER_NUMERIC_SCORING",
        "new_economic_fact_acquisition": False,
        "future_outcome_read": False,
        "m3_implementation": False,
    }


def build_decision() -> dict[str, Any]:
    return {
        "schema": "m2_stage2k1r4f4b_pe_disposition_decision_v1",
        "stage": "M2_STAGE_2K1R4F4B",
        "subject": "601857.SH",
        "decision": "PE_NUMERIC_SCORING_DEFERRED_FROZEN_5Y_VALIDATION_NOT_TESTABLE",
        "verdict": "PASS",
        "upstream_decision": (
            "PE_5Y_BACKFILL_TRUSTED_INDEPENDENT_VALIDATION_"
            "NOT_TESTABLE_WITH_FROZEN_5Y_HISTORY"
        ),
        "pe_evidence": {
            "raw_pe": "TRUSTED",
            "historical_percentile_3y": "TRUSTED",
            "historical_percentile_5y": "TRUSTED",
            "normalized_pe_cycle_context_methodology": "RETAINED_AS_RESEARCH_HISTORY",
            "cycle_context_independent_validation": "NOT_TESTABLE_WITH_FROZEN_5Y",
            "numeric_scoring_authorized": False,
        },
        "frozen_5y_evidence": {
            "required_days": 1211,
            "ready_days": 1211,
            "blocked_days": 0,
            "candidate_regimes": 1,
            "observed_onsets": 0,
            "left_censored_regimes": 1,
            "valid_onset_episodes": 0,
            "mature_4q": 0,
            "mature_8q": 0,
            "future_eps_values_read": False,
        },
        "scoring_policy": {
            "pe_component_score": None,
            "pe_zero_imputation": False,
            "weight_redistribution": False,
            "registered_weight_topology_unchanged": True,
            "valuation_dimension_score": None,
            "valuation_dimension_numeric_score": False,
            "pb_ps_component_shadow_retained": True,
            "production_scoring": False,
            "overall_score": False,
            "ranking": False,
            "recommendation": False,
            "target_price": False,
        },
        "scope_boundary": {
            "history_extension_beyond_frozen_5y": False,
            "commodity_or_industry_cycle_acquisition": False,
            "peer_issuer_acquisition": False,
            "new_pe_percentile_computation": False,
            "future_outcome_read": False,
            "default_db_modification": False,
            "upstream_artifact_rewrite": False,
            "m3_implementation": False,
        },
        "m2_status": {
            "milestone": "CONDITIONALLY_CLOSED",
            "scoring_addendum": "CONDITIONAL_CLOSEOUT_ALLOWED",
            "fully_complete": False,
        },
        "method_reopen_gate": {
            "allowed_reasons": [
                "NEW_PRE_REGISTERED_METHOD",
                "NEW_INDEPENDENT_EVIDENCE_CLASS",
                "NORTH_STAR_MATERIAL_CHANGE",
            ],
            "prohibited_reasons": [
                "MORE_HISTORY_ONLY",
                "THRESHOLD_TUNING_AFTER_RESULT",
                "OUTCOME_DRIVEN_METHOD_SELECTION",
            ],
        },
        "next_stage": {
            "stage": "M3_NORTH_STAR_PREFLIGHT",
            "preflight_allowed": True,
            "implementation_authorized": False,
            "automatic_start": False,
        },
    }


def matrix_markdown(matrix: dict[str, Any]) -> str:
    rows = [
        "# M2 Stage 2K.1R4F.4B — PE method disposition matrix",
        "",
        (
            "Frozen basis: 5Y readiness is complete, but the only candidate regime is "
            "left-censored, so independent validation is not testable inside the frozen window."
        ),
        "",
        "| Candidate | North-Star value | Method risk | Scope | Current protocol | Decision |",
        "|---|---|---|---|---|---|",
    ]
    for item in matrix["candidates"]:
        rows.append(
            (
                "| {candidate} | {north_star_value} | {methodological_risk} | "
                "{scope_expansion} | {allowed} | {decision} |"
            ).format(
                **item, allowed="YES" if item["current_protocol_allowed"] else "NO"
            )
        )
    rows.extend(
        [
            "",
            "## Selected disposition",
            "",
            (
                "`KEEP_PE_DESCRIPTIVE_DEFER_NUMERIC_SCORING` is selected. Raw PE and "
                "trusted 3Y/5Y percentiles remain descriptive evidence. The normalized-"
                "earnings/cycle-context work remains auditable research history, but it "
                "does not authorize a PE number."
            ),
            "",
            (
                "Commodity and industry controls (including Brent/WTI concepts) are "
                "deferred and were not acquired. They belong to a separately authorized "
                "mechanism-research design, not an ex-post M2 scoring rescue. Peer evidence "
                "and history beyond the frozen 5Y boundary were likewise not acquired."
            ),
            "",
            (
                "The existing fail-closed policy remains intact: PE is null rather than "
                "zero, PB/PS weights are not enlarged, and valuation and overall numeric "
                "scores are not produced."
            ),
        ]
    )
    return "\n".join(rows) + "\n"


def build_all() -> dict[str, str]:
    failures = verify_upstream()
    if failures:
        raise ValueError("upstream verification failed:\n" + "\n".join(failures))
    matrix = build_matrix()
    decision = build_decision()
    return {
        ARTIFACTS["matrix_json"]: canonical_json(matrix),
        ARTIFACTS["matrix_md"]: matrix_markdown(matrix),
        ARTIFACTS["decision"]: canonical_json(decision),
    }


def cmd_verify_upstream(_: argparse.Namespace) -> int:
    failures = verify_upstream()
    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        return 1
    print("PASS: R4F through R4F.4A1 decisions and protected hashes")
    print("PASS: 5Y=1211/1211; candidates/onsets/left-censored/valid=1/0/1/0")
    print("PASS: mature4/mature8=0/0; future_eps_values_read=false")
    print("PASS: PE and valuation score remain null; weights not renormalized")
    return 0


def cmd_build(args: argparse.Namespace) -> int:
    args.output_root.mkdir(parents=True, exist_ok=True)
    for name, content in build_all().items():
        (args.output_root / name).write_text(content, encoding="utf-8")
    print("decision=PE_NUMERIC_SCORING_DEFERRED_FROZEN_5Y_VALIDATION_NOT_TESTABLE verdict=PASS")
    return 0


def cmd_verify(args: argparse.Namespace) -> int:
    failures = verify_upstream()
    expected = build_all() if not failures else {}
    for name, content in expected.items():
        path = args.output_root / name
        if not path.is_file() or path.read_text(encoding="utf-8") != content:
            failures.append(f"committed artifact mismatch: {name}")
    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        return 1
    print("PASS: upstream and all R4F.4B committed artifacts")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="R4F.4B post-5Y PE disposition")
    sub = parser.add_subparsers(dest="command", required=True)
    upstream = sub.add_parser("verify-upstream")
    upstream.set_defaults(func=cmd_verify_upstream)
    for name, fn in (("build", cmd_build), ("verify", cmd_verify)):
        child = sub.add_parser(name)
        child.add_argument("--output-root", type=Path, default=ROOT / "reports")
        child.set_defaults(func=fn)
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
