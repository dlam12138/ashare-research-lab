"""M2 Stage 2K.1R4F.2 — PE cycle-context preflight CLI.

Thin command-line entry point over ``pe_cycle_context_preflight`` (pure
functions).  Modes:

- ``inventory``  — build the input inventory artifact
- ``build``      — build inventory + ROE chain + BVPS + historical EPS +
                   margin + diagnostics + method matrix + decision
- ``verify``     — re-run ``build`` from the same inputs and compare
                   byte-for-byte with the committed artifacts
- ``fixtures``   — write a deterministic synthetic future-fact bundle used
                   by the PIT-gate tests (excluded, never leaks)

Never fetches the network and never writes to the default database.  Inputs
are explicit committed artifact paths.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from ashare_research.pit_valuation import pe_cycle_context_preflight as pcp

ROOT = Path(__file__).resolve().parents[3]

REPORTED_BUNDLE = ROOT / "reports" / "petrochina_pit_denominator_reported_fact_bundle_v1.json"
RECONCILED_BUNDLE = (
    ROOT / "reports" / "petrochina_pit_denominator_reconciled_fact_bundle_v1.json"
)
TIMELINE = ROOT / "reports" / "petrochina_pit_financial_state_timeline_v2.json"
PERCENTILE_PROFILE = (
    ROOT / "reports" / "petrochina_pit_valuation_percentile_profile_v1.json"
)

INVENTORY_OUT = ROOT / "reports" / "petrochina_pe_cycle_context_input_inventory_v1.json"
METHOD_MATRIX_OUT = (
    ROOT / "reports" / "petrochina_pe_normalized_earnings_method_matrix_v1.json"
)
DIAGNOSTICS_OUT = (
    ROOT / "reports" / "petrochina_pe_normalized_earnings_diagnostics_v1.json"
)
DECISION_OUT = ROOT / "reports" / "m2_stage2k1r4f2_decision.json"


def _load_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


def _load_facts() -> list[dict[str, Any]]:
    reported = _load_json(REPORTED_BUNDLE).get("facts")
    reconciled = _load_json(RECONCILED_BUNDLE).get("facts")
    if not isinstance(reported, list) or not isinstance(reconciled, list):
        raise SystemExit("invalid fact bundles (expected 'facts' lists)")
    return pcp.merge_fact_bundles(reported, reconciled)


def _load_pe_evidence() -> dict[str, Any]:
    profile = _load_json(PERCENTILE_PROFILE)
    records = profile.get("records", [])
    pe = [r for r in records if r.get("metric_id") == "PE_A_TTM"]
    three = next((r for r in pe if r.get("window_id") == "3y"), None)
    five = next((r for r in pe if r.get("window_id") == "5y"), None)
    return {
        "current_pe_a_ttm": (
            three.get("current_ratio_decimal") if three else None
        ),
        "current_pe_percentile_3y": (
            three.get("midrank_percentile_decimal") if three else None
        ),
        "current_pe_percentile_5y": (
            five.get("midrank_percentile_decimal") if five else None
        ),
        "current_pe_observation_id": (
            three.get("current_observation_id") if three else None
        ),
        "current_pe_record_id_3y": (
            three.get("percentile_record_id") if three else None
        ),
        "current_pe_record_id_5y": (
            five.get("percentile_record_id") if five else None
        ),
    }


def _build_all(as_of: str) -> dict[str, dict[str, Any]]:
    facts = _load_facts()
    pe = _load_pe_evidence()
    inventory = pcp.build_annual_fact_inventory(facts, as_of)
    latest = pcp.build_latest_pit_inventory(facts, as_of)
    latest["items"].append(
        {
            "inventory_item": "L_r4e5_pe_a_ttm_current_observation",
            "concept": "PE_A_TTM",
            "value": pe.get("current_pe_a_ttm"),
            "percentile_3y": pe.get("current_pe_percentile_3y"),
            "percentile_5y": pe.get("current_pe_percentile_5y"),
            "current_observation_id": pe.get("current_pe_observation_id"),
            "percentile_record_id_3y": pe.get("current_pe_record_id_3y"),
            "percentile_record_id_5y": pe.get("current_pe_record_id_5y"),
            "as_of_trade_date": as_of,
        }
    )
    inventory["latest_pit"] = latest
    roe = pcp.build_annual_roe_chain(facts, as_of)
    bvps = pcp.build_current_bvps_and_normalized_eps(facts, as_of, roe)
    hist_eps = pcp.build_historical_window_eps_diagnostic(facts, as_of, roe)
    margin = pcp.build_normalized_margin_diagnostic(facts, as_of, roe)
    diagnostics = pcp.build_diagnostics(
        facts,
        as_of,
        roe,
        current_pe_a_ttm=pe.get("current_pe_a_ttm"),
        current_pe_percentile_3y=pe.get("current_pe_percentile_3y"),
        current_pe_percentile_5y=pe.get("current_pe_percentile_5y"),
    )
    matrix = pcp.build_method_matrix(facts, as_of, roe)
    decision = pcp.build_decision(facts, as_of, roe, bvps, matrix)
    return {
        "inventory": inventory,
        "roe": roe,
        "bvps": bvps,
        "hist_eps": hist_eps,
        "margin": margin,
        "diagnostics": diagnostics,
        "matrix": matrix,
        "decision": decision,
    }


def _write(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def cmd_inventory(args: argparse.Namespace) -> int:
    out = _build_all(args.as_of)
    _write(INVENTORY_OUT, out["inventory"])
    print(
        f"inventory written: {INVENTORY_OUT} "
        f"({len(out['inventory']['concept_series'])} annual entries + latest PIT)"
    )
    return 0


def cmd_build(args: argparse.Namespace) -> int:
    out = _build_all(args.as_of)
    _write(INVENTORY_OUT, out["inventory"])
    _write(METHOD_MATRIX_OUT, out["matrix"])
    _write(DIAGNOSTICS_OUT, out["diagnostics"])
    _write(DECISION_OUT, out["decision"])
    print(f"decision: {out['decision']['decision']} ({out['decision']['verdict']})")
    print(
        "consecutive annual ROE observations: "
        f"{out['roe']['consecutive_annual_roe_observation_count']}"
    )
    print(f"full_cycle_proven: {out['roe']['full_cycle_proven']}")
    print("PE numeric scoring: BLOCKED_UNCHANGED")
    return 0


def cmd_verify(args: argparse.Namespace) -> int:
    out = _build_all(args.as_of)
    failures = 0
    for name, path in (
        ("inventory", INVENTORY_OUT),
        ("matrix", METHOD_MATRIX_OUT),
        ("diagnostics", DIAGNOSTICS_OUT),
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
    """Write a deterministic synthetic future-fact bundle for PIT-gate tests."""
    base = _load_facts()
    synthetic = []
    for i, f in enumerate(base):
        if f.get("concept_id") != pcp.CONCEPT_NET_PROFIT:
            continue
        # future availability — must be excluded by the PIT gate
        sf = dict(f)
        sf["fact_id"] = f"r4f2-synthetic-future-{i}"
        sf["available_at"] = "2026-09-15"
        sf["effective_from"] = "2026-09-16"
        sf["value"] = "999999999999.0"
        sf["restatement_version"] = "synthetic_future"
        sf["supersedes_fact_id"] = None
        synthetic.append(sf)
    out_path = args.output
    out_path.write_text(
        json.dumps(
            {"schema": "r4f2_synthetic_future_fact_bundle_v1", "facts": synthetic},
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"fixtures written: {out_path} ({len(synthetic)} future facts)")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="m2_stage2k1r4f2_pe_cycle_context_preflight",
        description="PE cycle-context preflight (inventory / build / verify / fixtures)",
    )
    parser.add_argument("mode", choices=["inventory", "build", "verify", "fixtures"])
    parser.add_argument(
        "--as-of",
        default="2026-07-31",
        help="PIT as-of date (default 2026-07-31)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "tmp" / "r4f2_synthetic_future_facts.json",
        help="output path for fixtures mode",
    )
    args = parser.parse_args(argv)
    if args.mode == "inventory":
        return cmd_inventory(args)
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
