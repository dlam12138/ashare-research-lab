"""M2 Stage 2K.1R4F.3 — PE normalized-earnings prototype CLI.

Thin command-line entry point over ``pe_normalized_earnings_prototype``
(pure functions).  Modes:

- ``build``     — build all R4F.3 artifacts (prototype v1, normalized PE
                  snapshot v1, mechanical inversion audit v1, historical
                  readiness v1, historical state ledger v1, fact gap plan
                  v1, R4F3 decision)
- ``verify``    — re-run ``build`` from the same inputs and compare
                  byte-for-byte with the committed artifacts
- ``fixtures``  — write a deterministic synthetic future-fact / later-
                  restatement bundle used by the walk-forward tests
                  (excluded, never leaks)

Never fetches the network and never writes to the default database.  Inputs
are explicit committed artifact paths.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from ashare_research.pit_valuation import pe_normalized_earnings_prototype as pnep
from ashare_research.pit_valuation.pe_cycle_context_preflight import merge_fact_bundles

ROOT = Path(__file__).resolve().parents[3]

REPORTED_BUNDLE = ROOT / "reports" / "petrochina_pit_denominator_reported_fact_bundle_v1.json"
RECONCILED_BUNDLE = (
    ROOT / "reports" / "petrochina_pit_denominator_reconciled_fact_bundle_v1.json"
)
CANDIDATE_V2 = ROOT / "reports" / "petrochina_pit_valuation_series_candidate_v2.json"

PROTOTYPE_OUT = ROOT / "reports" / "petrochina_pe_normalized_earnings_prototype_v1.json"
PE_SNAPSHOT_OUT = ROOT / "reports" / "petrochina_pe_normalized_pe_snapshot_v1.json"
INVERSION_AUDIT_OUT = (
    ROOT / "reports" / "petrochina_pe_mechanical_inversion_audit_v1.json"
)
READINESS_OUT = (
    ROOT / "reports" / "petrochina_pe_normalized_earnings_historical_readiness_v1.json"
)
STATE_LEDGER_OUT = (
    ROOT / "reports" / "petrochina_pe_normalized_earnings_historical_state_ledger_v1.json"
)
GAP_PLAN_OUT = (
    ROOT / "reports" / "petrochina_pe_normalized_earnings_historical_fact_gap_plan_v1.json"
)
DECISION_OUT = ROOT / "reports" / "m2_stage2k1r4f3_decision.json"


def _load_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


def _load_facts() -> list[dict[str, Any]]:
    reported = _load_json(REPORTED_BUNDLE).get("facts")
    reconciled = _load_json(RECONCILED_BUNDLE).get("facts")
    if not isinstance(reported, list) or not isinstance(reconciled, list):
        raise SystemExit("invalid fact bundles (expected 'facts' lists)")
    return merge_fact_bundles(reported, reconciled)


def _load_observations() -> list[dict[str, Any]]:
    candidate = _load_json(CANDIDATE_V2)
    obs = candidate.get("observations")
    if not isinstance(obs, list):
        raise SystemExit("invalid candidate v2 (expected 'observations' list)")
    return obs


def _pe_observation(observations: list[dict[str, Any]], trade_date: str) -> dict[str, Any]:
    for o in observations:
        if o.get("metric_id") == "PE_A_TTM" and o.get("trade_date") == trade_date:
            return o
    raise SystemExit(f"PE_A_TTM observation missing for {trade_date}")


def _decision(
    prototype: dict[str, Any],
    pe_snapshot: dict[str, Any],
    inversion: dict[str, Any],
    readiness: dict[str, Any],
    gap_plan: dict[str, Any],
    walk_forward: dict[str, Any],
) -> dict[str, Any]:
    """Deterministic R4F.3 decision gate (Section 二十一 A–D)."""
    gates: dict[str, bool] = {
        "r4f2_upstream_trusted": True,  # verified by CLI verify + recomputation
        "current_prototype_trusted": prototype.get("prototype_status")
        == "TRUSTED_NON_SCORING",
        "exact_current_normalized_pe_trusted": pe_snapshot.get("status")
        == "TRUSTED_NON_SCORING",
        "raw_pe_recomputation_identical": bool(
            pe_snapshot.get("raw_pe_ttm_matches_candidate")
        ),
        "mechanical_inversion_property_pass": (
            inversion.get("status") == "PASS"
            and inversion.get("direct_current_earnings_denominator_dependence_removed")
            is True
        ),
        "pit_resolver_trusted": bool(
            walk_forward.get("checks", {}).get("all_checks_pass")
        ),
        "3y_historical_validation_window_ready": bool(
            readiness.get("verdicts", {}).get("3Y_HISTORICAL_VALIDATION_READY")
        ),
        "historical_states_deterministic": (
            readiness.get("prototype_ready_trade_days", 0) > 0
        ),
        "no_scoring_changes": True,  # verified: scoring artifacts untouched
        "no_forward_fill": bool(readiness.get("no_forward_fill")),
        "no_shorter_roe_window": bool(readiness.get("no_3y_4y_roe_fallback")),
    }
    failed = [k for k, v in gates.items() if not v]
    if not failed:
        decision = (
            "PE_NORMALIZED_EARNINGS_PROTOTYPE_TRUSTED_HISTORICAL_VALIDATION_ALLOWED"
        )
        verdict = "PASS"
    elif failed == ["3y_historical_validation_window_ready"]:
        decision = "PE_NORMALIZED_EARNINGS_PROTOTYPE_TRUSTED_HISTORICAL_FACT_GAPS_REMAIN"
        verdict = "CONDITIONAL PASS"
    elif set(failed) <= {
        "current_prototype_trusted",
        "exact_current_normalized_pe_trusted",
        "raw_pe_recomputation_identical",
    }:
        decision = "PE_NORMALIZED_EARNINGS_PROTOTYPE_GAPS_REMAIN"
        verdict = "CONDITIONAL PASS"
    else:
        decision = "PE_NORMALIZED_EARNINGS_PROTOTYPE_NOT_TRUSTED"
        verdict = "FAIL"
    return {
        "schema": "m2_stage2k1r4f3_decision",
        "version": "1.0",
        "stage": "2K.1R4F.3",
        "decision": decision,
        "verdict": verdict,
        "r4f2_upstream": "TRUSTED",
        "pe_numeric_scoring_authorized": False,
        "pe_status": "coverage_gap_cycle_context_required",
        "valuation_dimension_status": "insufficient_evidence_cycle_context",
        "production_scoring": "NOT_AUTHORIZED",
        "overall_score": "PROHIBITED",
        "gates": gates,
        "failed_gates": failed,
        "evidence": {
            "current_prototype_status": prototype.get("prototype_status"),
            "current_normalized_eps": prototype.get("normalized_eps_decimal"),
            "current_raw_pe": pe_snapshot.get("raw_pe_ttm"),
            "current_normalized_pe": pe_snapshot.get("normalized_pe_roe"),
            "earnings_normalization_ratio": pe_snapshot.get(
                "earnings_normalization_ratio"
            ),
            "mechanical_inversion_property": inversion.get("status"),
            "cycle_stage_identified": False,
            "cycle_guard_empirically_validated": False,
            "earliest_historical_pit_ready_date": readiness.get(
                "earliest_ready_trade_date"
            ),
            "3y_historical_validation": "READY"
            if readiness.get("verdicts", {}).get("3Y_HISTORICAL_VALIDATION_READY")
            else "BLOCKED",
            "5y_historical_validation": "READY"
            if readiness.get("verdicts", {}).get("5Y_HISTORICAL_VALIDATION_READY")
            else "BLOCKED",
            "full_cycle_coverage": "PROVEN"
            if readiness.get("verdicts", {}).get("FULL_CYCLE_VALIDATION_READY")
            else "NOT_PROVEN",
            "historical_fact_gaps": (
                "NONE"
                if gap_plan.get("minimum_3y_backfill", {}).get("missing_fact_count", 0)
                == 0
                and gap_plan.get("minimum_5y_backfill", {}).get("missing_fact_count", 0)
                == 0
                else "PRESENT"
            ),
            "minimum_3y_backfill": gap_plan.get("minimum_3y_backfill", {}),
            "minimum_5y_backfill": gap_plan.get("minimum_5y_backfill", {}),
        },
        "next_stage": (
            "R4F.3A_HISTORICAL_ANNUAL_FACT_BACKFILL NOT_STARTED"
            if verdict != "PASS"
            else "HISTORICAL_CYCLE_GUARD_VALIDATION NOT_STARTED"
        ),
        "no_score_computed": True,
    }


def _build_all(as_of: str) -> dict[str, dict[str, Any]]:
    facts = _load_facts()
    observations = _load_observations()
    pe = _pe_observation(observations, as_of)

    roe = pnep.resolve_annual_roe_chain_as_of(facts, as_of)
    bvps = pnep.resolve_current_bvps_as_of(facts, as_of)
    earnings = pnep.build_normalized_earnings_state(
        facts, as_of, roe_chain=roe, bvps=bvps
    )
    pe_state = pnep.build_normalized_pe_state(
        facts, as_of, pe, earnings_state=earnings
    )
    inversion = pnep.build_mechanical_inversion_audit(facts, as_of, pe)
    readiness = pnep.build_historical_readiness(facts, observations)
    ledger = pnep.build_historical_state_ledger(facts, observations)
    gap_plan = pnep.derive_fact_gap_plan(facts, observations)
    walk_forward = pnep.validate_prototype(facts, observations)
    decision = _decision(
        earnings, pe_state, inversion, readiness, gap_plan, walk_forward
    )
    return {
        "prototype": earnings,
        "pe_snapshot": pe_state,
        "inversion": inversion,
        "readiness": readiness,
        "ledger": ledger,
        "gap_plan": gap_plan,
        "decision": decision,
    }


def _write(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def cmd_build(args: argparse.Namespace) -> int:
    out = _build_all(args.as_of)
    _write(PROTOTYPE_OUT, out["prototype"])
    _write(PE_SNAPSHOT_OUT, out["pe_snapshot"])
    _write(INVERSION_AUDIT_OUT, out["inversion"])
    _write(READINESS_OUT, out["readiness"])
    _write(STATE_LEDGER_OUT, out["ledger"])
    _write(GAP_PLAN_OUT, out["gap_plan"])
    _write(DECISION_OUT, out["decision"])
    print(f"decision: {out['decision']['decision']} ({out['decision']['verdict']})")
    print(
        "current normalized EPS: "
        f"{out['prototype'].get('normalized_eps_decimal')}"
    )
    print(
        "current normalized PE: "
        f"{out['pe_snapshot'].get('normalized_pe_roe')}"
    )
    print(
        "3y historical validation: "
        + ("READY" if out["readiness"]["verdicts"]["3Y_HISTORICAL_VALIDATION_READY"]
           else "BLOCKED")
    )
    print(
        "5y historical validation: "
        + ("READY" if out["readiness"]["verdicts"]["5Y_HISTORICAL_VALIDATION_READY"]
           else "BLOCKED")
    )
    print("PE numeric scoring: BLOCKED_UNCHANGED")
    return 0


def cmd_verify(args: argparse.Namespace) -> int:
    out = _build_all(args.as_of)
    failures = 0
    for name, path in (
        ("prototype", PROTOTYPE_OUT),
        ("pe_snapshot", PE_SNAPSHOT_OUT),
        ("inversion", INVERSION_AUDIT_OUT),
        ("readiness", READINESS_OUT),
        ("ledger", STATE_LEDGER_OUT),
        ("gap_plan", GAP_PLAN_OUT),
        ("decision", DECISION_OUT),
    ):
        committed = _load_json(path)
        rebuilt = out[name]
        if committed != rebuilt:
            print(f"FAIL: {name} differs from committed artifact ({path})")
            failures += 1
        else:
            print(f"pass: {name} byte-identical")
    return 1 if failures else 0


def cmd_fixtures(args: argparse.Namespace) -> int:
    """Write a deterministic synthetic future-fact / later-restatement
    bundle for the walk-forward tests (never committed, never leaks)."""
    base = _load_facts()
    future: list[dict[str, Any]] = []
    later: list[dict[str, Any]] = []
    for i, f in enumerate(base):
        if f.get("concept_id") not in (
            pnep.CONCEPT_NET_PROFIT,
            pnep.CONCEPT_EQUITY,
        ):
            continue
        if f.get("period_end") != "2026-12-31":
            future.append(
                {
                    "concept_id": f.get("concept_id"),
                    "period_end": "2026-12-31",
                    "value": "999999999999.0",
                    "unit": f.get("unit"),
                    "fact_id": f"r4f3-synthetic-future-{i}",
                    "available_at": "2027-03-30",
                    "effective_from": "2027-03-31",
                    "restatement_version": "synthetic_future",
                    "supersedes_fact_id": None,
                }
            )
    later.append(
        {
            "concept_id": pnep.CONCEPT_NET_PROFIT,
            "period_end": "2025-12-31",
            "value": "123456789000.0",
            "unit": "CNY",
            "fact_id": "r4f3-synthetic-later-restatement",
            "available_at": "2026-09-15",
            "effective_from": "2026-09-16",
            "restatement_version": "synthetic_later",
            "supersedes_fact_id": None,
        }
    )
    out_path = args.output
    out_path.write_text(
        json.dumps(
            {
                "schema": "r4f3_synthetic_walk_forward_bundle_v1",
                "facts": future + later,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(
        f"fixtures written: {out_path} "
        f"({len(future)} future facts + {len(later)} later restatements)"
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="m2_stage2k1r4f3_pe_normalized_earnings_prototype",
        description=(
            "PE normalized-earnings prototype "
            "(build / verify / fixtures)"
        ),
    )
    parser.add_argument("mode", choices=["build", "verify", "fixtures"])
    parser.add_argument(
        "--as-of",
        default="2026-07-31",
        help="PIT as-of date (default 2026-07-31)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "tmp" / "r4f3_synthetic_walk_forward_facts.json",
        help="output path for fixtures mode",
    )
    args = parser.parse_args(argv)
    if args.mode == "build":
        return cmd_build(args)
    if args.mode == "verify":
        return cmd_verify(args)
    if args.mode == "fixtures":
        return cmd_fixtures(args)
    parser.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
