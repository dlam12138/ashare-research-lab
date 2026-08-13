"""Thin offline CLI for R4F.4A1 build / verify / external evidence checks."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))

from ashare_research.pit_valuation.fact_builder import load_market_calendar  # noqa: E402
from ashare_research.pit_valuation.pe_5y_historical_annual_backfill import (  # noqa: E402
    artifact_digest_map,
    build_decision,
    build_episode_series,
    build_extraction_report,
    build_fact_bundle,
    build_lineage,
    build_new_facts,
    build_overlay,
    canonical_json,
    independent_roe_reconciliation,
    normalized_anchor_states,
    validate_target_dependencies,
)
from ashare_research.pit_valuation.pe_cycle_context_preflight import (  # noqa: E402
    merge_fact_bundles,
)
from ashare_research.pit_valuation.pe_independent_cycle_validation_preflight import (  # noqa: E402
    assert_preflight_has_no_future_values,
    build_outcome_readiness_for_window,
    derive_episode_inventory_for_window,
)
from ashare_research.pit_valuation.pe_normalized_earnings_prototype import (  # noqa: E402
    WINDOW_5Y,
    build_historical_readiness,
)

CONTRACT = ROOT / "config" / "pe_5y_independent_cycle_backfill_contract_v1.json"
EVIDENCE = ROOT / "config" / "pe_5y_historical_backfill_source_evidence_v1.json"
CACHE_REGISTRY = ROOT / "config" / "pe_5y_historical_backfill_cache_registry_v1.json"
SPECS = ROOT / "config" / "pe_5y_historical_backfill_extraction_specs_v1.json"
CALENDAR_REGISTRY = ROOT / "config" / "pit_valuation_market_calendar_registry_r4f4a1_v1.json"
OLD_CALENDAR_REGISTRY = ROOT / "config" / "pit_valuation_market_calendar_registry_r4f3a_v1.json"
REPORTED = ROOT / "reports" / "petrochina_pit_denominator_reported_fact_bundle_v1.json"
RECONCILED = ROOT / "reports" / "petrochina_pit_denominator_reconciled_fact_bundle_v1.json"
R4F3A = ROOT / "reports" / "petrochina_pe_3y_historical_backfill_reported_fact_bundle_v1.json"
OBSERVATIONS = ROOT / "reports" / "petrochina_pit_valuation_series_candidate_v2.json"
TIMELINE = ROOT / "reports" / "petrochina_pit_financial_state_timeline_v2.json"

ARTIFACT_PATHS = {
    "extraction": "petrochina_pe_5y_historical_backfill_extraction_v1.json",
    "bundle": "petrochina_pe_5y_historical_backfill_reported_fact_bundle_v1.json",
    "lineage": "petrochina_pe_5y_historical_backfill_version_lineage_v1.json",
    "overlay": "petrochina_pe_5y_historical_backfill_overlay_v1.json",
    "calendar": "petrochina_pe_5y_historical_calendar_reconciliation_v1.json",
    "reconciliation": "petrochina_pe_5y_historical_backfill_reconciliation_v1.json",
    "readiness": "petrochina_pe_normalized_earnings_5y_readiness_after_backfill_v1.json",
    "episode_series": "petrochina_pe_5y_normalized_earnings_episode_series_v1.json",
    "inventory": "petrochina_pe_independent_cycle_episode_inventory_5y_v1.json",
    "outcome": "petrochina_pe_independent_cycle_outcome_readiness_5y_v1.json",
    "decision": "m2_stage2k1r4f4a1_decision.json",
}


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def evidence_map() -> dict[str, dict[str, Any]]:
    return {row["evidence_id"]: row for row in load(EVIDENCE)["entries"]}


def sha_map() -> dict[str, str]:
    out: dict[str, str] = {}
    for obj in load(CACHE_REGISTRY)["objects"]:
        for evidence_id in obj["evidence_ids"]:
            out[evidence_id] = obj["sha256"]
    return out


def existing_facts() -> list[dict[str, Any]]:
    base = merge_fact_bundles(load(REPORTED)["facts"], load(RECONCILED)["facts"])
    return base + load(R4F3A)["facts"]


def calendar_reconciliation(market_cache_root: Path) -> dict[str, Any]:
    import pandas as pd

    old_reg, new_reg = load(OLD_CALENDAR_REGISTRY), load(CALENDAR_REGISTRY)
    old = pd.read_parquet(market_cache_root / old_reg["object_key"])
    new = pd.read_parquet(market_cache_root / new_reg["object_key"])
    old_days = set(old["trade_date"].astype(str))
    new_days = set(new["trade_date"].astype(str))
    overlap_start, overlap_end = min(old_days), max(old_days)
    new_overlap = {day for day in new_days if overlap_start <= day <= overlap_end}
    missing, extra = sorted(old_days - new_overlap), sorted(new_overlap - old_days)
    evidence_dates = [row["announcement_date"] for row in load(EVIDENCE)["entries"]]
    target_gaps = [
        day for day in evidence_dates if not any(candidate > day for candidate in new_days)
    ]
    return {
        "schema": "petrochina_pe_5y_historical_calendar_reconciliation_v1",
        "symbol": "601857.SH",
        "old_r4f3a_sha256": old_reg["object_sha256"],
        "new_r4f4a1_sha256": new_reg["object_sha256"],
        "old_calendar_unchanged": True,
        "new_calendar_range": {
            "start": min(new_days),
            "end": max(new_days),
        },
        "required_start": min(evidence_dates),
        "overlap_start": overlap_start,
        "overlap_end": overlap_end,
        "old_count": len(old_days),
        "new_overlap_count": len(new_overlap),
        "missing": missing,
        "extra": extra,
        "missing_dates": len(missing),
        "extra_dates": len(extra),
        "target_pit_calendar_gaps": len(target_gaps),
        "status": "PASS" if not missing and not extra and not target_gaps else "FAIL",
    }


def build_all(market_cache_root: Path) -> dict[str, dict[str, Any]]:
    contract = load(CONTRACT)
    dependency = validate_target_dependencies(contract["target_logical_cells"])
    if dependency["status"] != "PASS":
        raise ValueError("target dependency contract failed")
    registry = load(CALENDAR_REGISTRY)
    calendar = load_market_calendar(market_cache_root, registry=registry)
    specs = load(SPECS)["specs"]
    evidence = evidence_map()
    hashes = sha_map()
    new_facts = build_new_facts(specs, evidence, hashes, calendar)
    existing = existing_facts()
    combined = existing + new_facts
    observations = load(OBSERVATIONS)["observations"]
    extraction = build_extraction_report(specs, hashes)
    bundle = build_fact_bundle(new_facts)
    lineage = build_lineage(new_facts)
    overlay = build_overlay(existing, new_facts)
    calendar_report = calendar_reconciliation(market_cache_root)
    reconciliation = independent_roe_reconciliation(combined)
    raw_readiness = build_historical_readiness(combined, observations)
    blocked = raw_readiness["blocked_dates"]["5y_window"]
    readiness = {
        "schema": "petrochina_pe_normalized_earnings_5y_readiness_after_backfill_v1",
        "symbol": "601857.SH",
        "window": {"start": WINDOW_5Y[0], "end": WINDOW_5Y[1]},
        "5y_gate": {
            "required_days": 1211,
            "ready_days": 1211 - len(blocked),
            "blocked_days": len(blocked),
            "status": "READY" if not blocked else "BLOCKED",
        },
        "engine": "R4F3_NORMALIZED_EARNINGS_READINESS_REUSED",
        "engine_result": raw_readiness,
        "no_forward_fill": True,
    }
    episode_series, ledger = build_episode_series(combined, observations)
    timeline = load(TIMELINE)
    inventory = derive_episode_inventory_for_window(
        "5y",
        WINDOW_5Y[0],
        ledger,
        timeline,
        normalized_anchor_states(ledger, combined),
    )
    outcome = build_outcome_readiness_for_window("5y", inventory, timeline)
    decision = build_decision(extraction, readiness, inventory, outcome, calendar_report)
    artifacts = {
        "extraction": extraction,
        "bundle": bundle,
        "lineage": lineage,
        "overlay": overlay,
        "calendar": calendar_report,
        "reconciliation": reconciliation,
        "readiness": readiness,
        "episode_series": episode_series,
        "inventory": inventory,
        "outcome": outcome,
        "decision": decision,
    }
    for payload in artifacts.values():
        assert_preflight_has_no_future_values(payload)
    return artifacts


def write_all(root: Path, artifacts: dict[str, dict[str, Any]]) -> None:
    root.mkdir(parents=True, exist_ok=True)
    for name, payload in artifacts.items():
        (root / ARTIFACT_PATHS[name]).write_text(canonical_json(payload), encoding="utf-8")


def cmd_build(args: argparse.Namespace) -> int:
    artifacts = build_all(args.market_cache_root)
    write_all(args.output_root, artifacts)
    decision = artifacts["decision"]
    print(f"decision={decision['decision']} verdict={decision['verdict']}")
    print(
        f"5y={decision['5y_ready_days']}/1211 episodes="
        f"{decision['valid_onset_anchored_episodes']} mature4="
        f"{decision['protocol_valid_mature_4q_episode_count']}"
    )
    return 0


def cmd_verify(args: argparse.Namespace) -> int:
    artifacts = build_all(args.market_cache_root)
    failures = 0
    for name, payload in artifacts.items():
        path = args.output_root / ARTIFACT_PATHS[name]
        ok = path.is_file() and load(path) == payload
        print(f"{'pass' if ok else 'FAIL'}: {path.name}")
        failures += int(not ok)
    return int(failures > 0)


def cmd_external_verify(args: argparse.Namespace) -> int:
    roots = {
        "r4f4a1": args.r4f4a1_cache_root,
        "r4f3a_reused": args.r4f3a_cache_root,
    }
    failures = 0
    for obj in load(CACHE_REGISTRY)["objects"]:
        path = roots[obj["cache_namespace"]] / obj["object_key"]
        digest = hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else ""
        ok = digest == obj["sha256"]
        print(f"{'pass' if ok else 'FAIL'}: {obj['sha256']} ({obj['cache_namespace']})")
        failures += int(not ok)
    return int(failures > 0)


def cmd_digest(args: argparse.Namespace) -> int:
    print(json.dumps(artifact_digest_map(build_all(args.market_cache_root)), indent=2))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="R4F4A1 frozen-5Y backfill CLI")
    sub = parser.add_subparsers(dest="command", required=True)
    for name, fn in (
        ("build", cmd_build),
        ("verify", cmd_verify),
        ("digest", cmd_digest),
    ):
        child = sub.add_parser(name)
        child.add_argument(
            "--market-cache-root",
            type=Path,
            default=ROOT / "tmp" / "market_cache" / "baostock",
        )
        child.add_argument("--output-root", type=Path, default=ROOT / "reports")
        child.set_defaults(func=fn)
    external = sub.add_parser("external-verify")
    external.add_argument(
        "--r4f4a1-cache-root",
        type=Path,
        default=ROOT / "tmp" / "r4f4a1_official_cache",
    )
    external.add_argument(
        "--r4f3a-cache-root",
        type=Path,
        default=ROOT / "tmp" / "r4f3a_official_cache",
    )
    external.set_defaults(func=cmd_external_verify)
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
