"""Offline CLI for R4F.4A independent cycle-validation preflight."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))

from ashare_research.pit_valuation.pe_independent_cycle_validation_preflight import (  # noqa: E402
    assert_preflight_has_no_future_values,
    build_outcome_readiness,
    derive_5y_justification,
    derive_episode_inventory,
)
from ashare_research.pit_valuation.pe_normalized_earnings_prototype import (  # noqa: E402
    build_normalized_earnings_state,
    resolve_annual_roe_chain_as_of,
    resolve_current_bvps_as_of,
)
from ashare_research.tools.m2_stage2k1r4f4_pe_cycle_guard_validation import (  # noqa: E402
    _load_facts,
)

LEDGER = ROOT / "reports" / "petrochina_pe_3y_denominator_state_ledger_v1.json"
TIMELINE = ROOT / "reports" / "petrochina_pit_financial_state_timeline_v2.json"
EPISODES = ROOT / "reports" / "petrochina_pe_independent_cycle_episode_inventory_v1.json"
READINESS = ROOT / "reports" / "petrochina_pe_independent_cycle_outcome_readiness_v1.json"
JUSTIFICATION = ROOT / "reports" / "petrochina_pe_5y_backfill_identification_justification_v1.json"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def normalized_anchor_states(ledger: dict) -> dict[str, dict]:
    facts = _load_facts()
    states = {}
    fact_index = {fact.get("fact_id"): fact for fact in facts}
    for segment in ledger["segments"]:
        if segment["normalized_denominator_state_id"] in states:
            continue
        day = segment["start_trade_date"]
        state = build_normalized_earnings_state(
            facts,
            day,
            roe_chain=resolve_annual_roe_chain_as_of(facts, day),
            bvps=resolve_current_bvps_as_of(facts, day),
        )
        ids = []
        for record in state["annual_fact_ids"]:
            ids.extend(
                record[key] for key in ("np_fact_id", "begin_equity_fact_id", "end_equity_fact_id")
            )
        ids.extend([state["current_equity_fact_id"], state["share_fact_id"]])
        ids = list(dict.fromkeys(ids))
        states[segment["normalized_denominator_state_id"]] = {
            "current_bvps_decimal": state["current_bvps_decimal"],
            "selected_five_roe_years": [r["fiscal_year"] for r in state["annual_roe_observations"]],
            "anchor_fact_ids": ids,
            "anchor_available_at_effective_identities": [
                {
                    "fact_id": fid,
                    "period_end": fact_index[fid].get("period_end"),
                    "available_at": fact_index[fid].get("available_at"),
                    "effective_from": fact_index[fid].get("effective_from"),
                }
                for fid in ids
            ],
        }
    return states


def build() -> tuple[dict, dict, dict]:
    ledger, timeline = load(LEDGER), load(TIMELINE)
    inventory = derive_episode_inventory(ledger, timeline, normalized_anchor_states(ledger))
    readiness = build_outcome_readiness(inventory, timeline)
    justification = derive_5y_justification(inventory, readiness)
    for payload in (inventory, readiness, justification):
        assert_preflight_has_no_future_values(payload)
    return inventory, readiness, justification


def review(_: argparse.Namespace) -> int:
    inventory, readiness, justification = build()
    print(
        f"episodes={inventory['episode_count']} "
        f"left_censored={inventory['left_censored_episode_count']}"
    )
    print(
        "target_metadata_4q="
        f"{readiness['candidate_regimes_with_4q_target_metadata_available']} "
        "target_metadata_8q="
        f"{readiness['candidate_regimes_with_8q_target_metadata_available']}"
    )
    print(
        "valid_mature_4q="
        f"{readiness['protocol_valid_mature_4q_episode_count']} "
        "valid_mature_8q="
        f"{readiness['protocol_valid_mature_8q_episode_count']}"
    )
    print(f"5y={justification['status']}")
    return 0


def readiness(_: argparse.Namespace) -> int:
    inventory, ready, justification = build()
    write(EPISODES, inventory)
    write(READINESS, ready)
    write(JUSTIFICATION, justification)
    return review(_)


def verify(_: argparse.Namespace) -> int:
    rebuilt = build()
    failed = False
    for path, payload in zip((EPISODES, READINESS, JUSTIFICATION), rebuilt, strict=True):
        ok = load(path) == payload
        print(f"{'pass' if ok else 'FAIL'}: {path.name}")
        failed |= not ok
    return int(failed)


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    for name, func in (("review", review), ("readiness", readiness), ("verify", verify)):
        child = sub.add_parser(name)
        child.set_defaults(func=func)
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
