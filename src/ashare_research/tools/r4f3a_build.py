"""R4F.3A build — construct backfilled facts, PIT dates, lineage, overlay.

Builds the 8 backfilled Facts (5 target cells original + 3 restated_1
versions from the 2019 AR comparative columns per the Dalian Xitai same-
control acquisition), resolves PIT effective_from against the R4F3A
historical calendar, assembles the reported bundle, the overlay with the
existing trusted fact set, and reruns the R4F.3 readiness engine on the
combined set (before/after).

Reuses: existing R4D/R4F.3 fact shape + FactIdentity + readiness engine;
R4F3A calendar registry + loader + next_trading_day.  Offline only.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from ashare_research.pit_valuation.fact_builder import load_market_calendar  # noqa: E402
from ashare_research.pit_valuation.pe_cycle_context_preflight import (  # noqa: E402
    merge_fact_bundles,
)
from ashare_research.pit_valuation.pe_historical_annual_backfill import (  # noqa: E402
    CONCEPT_EQUITY,
    CONCEPT_NET_PROFIT,
    build_backfill_bundle,
    build_fact,
    build_overlay,
)
from ashare_research.pit_valuation.pe_normalized_earnings_prototype import (  # noqa: E402
    AS_OF_TRADE_DATE,
    WINDOW_3Y,
    WINDOW_5Y,
    build_historical_readiness,
)

CACHE = ROOT / "tmp" / "r4f3a_official_cache"
MARKET_CACHE = ROOT / "tmp" / "market_cache" / "baostock"
R4F3A_REGISTRY = ROOT / "config" / "pit_valuation_market_calendar_registry_r4f3a_v1.json"
SOURCE_EVIDENCE = ROOT / "config" / "pe_3y_historical_backfill_source_evidence_v1.json"
CACHE_REGISTRY = ROOT / "config" / "pe_3y_historical_backfill_cache_registry_v1.json"
REPORTED_BUNDLE_R4D = (
    ROOT / "reports" / "petrochina_pit_denominator_reported_fact_bundle_v1.json"
)
RECONCILED_BUNDLE_R4D = (
    ROOT / "reports" / "petrochina_pit_denominator_reconciled_fact_bundle_v1.json"
)
CANDIDATE_V2 = ROOT / "reports" / "petrochina_pit_valuation_series_candidate_v2.json"
R4F3_READINESS = (
    ROOT / "reports" / "petrochina_pe_normalized_earnings_historical_readiness_v1.json"
)

OUT_REPORTED = (
    ROOT / "reports" / "petrochina_pe_3y_historical_backfill_reported_fact_bundle_v1.json"
)
OUT_OVERLAY = (
    ROOT / "reports" / "petrochina_pe_3y_historical_backfill_overlay_v1.json"
)
OUT_READINESS_AFTER = (
    ROOT / "reports" / "petrochina_pe_normalized_earnings_3y_readiness_after_backfill_v1.json"
)

# Extracted cells (verified against official PDFs by r4f3a_extraction_probe):
#   (concept, period_end, value_million, evidence_id, page_1based)
ORIGINALS = [
    (CONCEPT_EQUITY, "2017-12-31", "1193810", "R4F3A-SSE-2017-AR", 122),
    (CONCEPT_EQUITY, "2018-12-31", "1214570", "R4F3A-SSE-2018-AR", 113),
    (CONCEPT_NET_PROFIT, "2018-12-31", "52585", "R4F3A-SSE-2018-AR", 114),
    (CONCEPT_EQUITY, "2019-12-31", "1230428", "R4F3A-SSE-2019-AR", 114),
    (CONCEPT_NET_PROFIT, "2019-12-31", "45677", "R4F3A-SSE-2019-AR", 115),
]

# Restated_1 values from the 2019 AR comparative columns (Dalian Xitai SCA,
# note 6(2); 2019 AR announced 2020-03-26):
#   (concept, period_end, value_million, evidence_id, page_1based)
RESTATED = [
    # equity-changes statement opening
    (CONCEPT_EQUITY, "2017-12-31", "1192862", "R4F3A-SSE-2019-AR", 118),
    # balance-sheet comparative
    (CONCEPT_EQUITY, "2018-12-31", "1214067", "R4F3A-SSE-2019-AR", 114),
    # income-statement comparative
    (CONCEPT_NET_PROFIT, "2018-12-31", "53030", "R4F3A-SSE-2019-AR", 115),
]


def _load_json(path: Path) -> dict:
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


def _evidence_map() -> dict[str, dict]:
    return {e["evidence_id"]: e for e in _load_json(SOURCE_EVIDENCE)["entries"]}


def _object_sha_by_evidence() -> dict[str, str]:
    reg = _load_json(CACHE_REGISTRY)
    out: dict[str, str] = {}
    for obj in reg["objects"]:
        for eid in obj.get("evidence_ids", []):
            out[eid] = obj["sha256"]
    return out


def _load_existing_facts() -> list[dict]:
    reported = _load_json(REPORTED_BUNDLE_R4D).get("facts", [])
    reconciled = _load_json(RECONCILED_BUNDLE_R4D).get("facts", [])
    return merge_fact_bundles(reported, reconciled)


def _load_observations() -> list[dict]:
    return _load_json(CANDIDATE_V2).get("observations", [])


def _build_cell_dict(concept: str, period_end: str, value_million: str) -> dict:
    from decimal import Decimal

    raw = Decimal(value_million)
    return {
        "concept_id": concept,
        "period_end": period_end,
        "raw_value": str(raw),
        "canonical_value": str(raw * Decimal("1000000")),
        "page_index": 0,  # overwritten per row
        "excerpt_hash": "",
        "status": "acquired_reported_verified",
    }


def build_facts(
    market_calendar: dict, evidence_map: dict, object_sha_map: dict
) -> list[dict]:
    """Build the 8 backfilled Facts (5 original + 3 restated_1)."""
    facts: list[dict] = []

    # originals
    for concept, pe, val, eid, page in ORIGINALS:
        ev = evidence_map[eid]
        cell = _build_cell_dict(concept, pe, val)
        cell["page_index"] = page - 1
        f = build_fact(
            cell, ev, market_calendar=market_calendar, object_sha=object_sha_map[eid]
        )
        facts.append(f)

    # restated_1 (supersede the original of the same logical cell)
    for concept, pe, val, eid, page in RESTATED:
        ev = evidence_map[eid]
        cell = _build_cell_dict(concept, pe, val)
        cell["page_index"] = page - 1
        original = next(
            f
            for f in facts
            if f["concept_id"] == concept
            and f["period_end"] == pe
            and f["restatement_version"] == "original"
        )
        f = build_fact(
            cell,
            ev,
            market_calendar=market_calendar,
            object_sha=object_sha_map[eid],
            restatement_version="restated_1",
            supersedes_fact_id=original["fact_id"],
        )
        facts.append(f)

    return facts


def main() -> int:
    import json as _json

    # load R4F3A calendar (pinned registry)
    registry = _json.loads(R4F3A_REGISTRY.read_text(encoding="utf-8"))
    calendar = load_market_calendar(MARKET_CACHE, registry=registry)

    evidence_map = _evidence_map()
    object_sha_map = _object_sha_by_evidence()

    backfill_facts = build_facts(calendar, evidence_map, object_sha_map)
    for f in backfill_facts:
        print(
            f"{f['concept_id']} {f['period_end']} {f['restatement_version']:>10} "
            f"value={f['value']:.0f} eff={f['effective_from']} avail={f['available_at']}"
            f" supersedes={f['supersedes_fact_id'][:12] or '-'}"
        )

    # reported bundle
    bundle = build_backfill_bundle(backfill_facts)
    OUT_REPORTED.write_text(
        _json.dumps(bundle, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
    )

    # existing trusted set + overlay
    existing = _load_existing_facts()
    overlay = build_overlay(
        existing, backfill_facts, selected_target_facts=backfill_facts
    )
    OUT_OVERLAY.write_text(
        _json.dumps(overlay, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    # combined set for readiness
    combined = existing + backfill_facts
    observations = _load_observations()

    # before readiness (must reproduce R4F.3 committed)
    before = build_historical_readiness(existing, observations)
    after = build_historical_readiness(combined, observations)

    # after readiness + 3y gate
    after_entries = [
        {
            "trade_date": d,
            "status": "READY" if e["status"] == "READY" else "BLOCKED",
        }
        for d, e in sorted(
            (
                (e["trade_date"], e)
                for e in _day_readiness_all(combined, observations)
            ),
            key=lambda t: t[0],
        )
    ]

    after_report = {
        "schema": "pe_normalized_earnings_3y_readiness_after_backfill_v1",
        "symbol": "601857.SH",
        "as_of_trade_date": AS_OF_TRADE_DATE,
        "windows": {
            "3y": {"start": WINDOW_3Y[0], "end": WINDOW_3Y[1]},
            "5y": {"start": WINDOW_5Y[0], "end": WINDOW_5Y[1]},
        },
        "before": {
            "candidate_trade_day_count": before["candidate_trade_day_count"],
            "prototype_ready_trade_days": before["prototype_ready_trade_days"],
            "blocked_trade_days": before["blocked_trade_days"],
            "earliest_ready_trade_date": before["earliest_ready_trade_date"],
            "gap_reason_counts": before["gap_reason_counts"],
            "verdicts": before["verdicts"],
        },
        "after": {
            "candidate_trade_day_count": after["candidate_trade_day_count"],
            "prototype_ready_trade_days": after["prototype_ready_trade_days"],
            "blocked_trade_days": after["blocked_trade_days"],
            "earliest_ready_trade_date": after["earliest_ready_trade_date"],
            "gap_reason_counts": after["gap_reason_counts"],
            "verdicts": after["verdicts"],
        },
        "3y_gate": {
            "required_days": sum(
                1
                for e in after_entries
                if WINDOW_3Y[0] <= e["trade_date"] <= WINDOW_3Y[1]
            ),
            "ready_days": sum(
                1
                for e in after_entries
                if WINDOW_3Y[0] <= e["trade_date"] <= WINDOW_3Y[1]
                and e["status"] == "READY"
            ),
            "blocked_days": sum(
                1
                for e in after_entries
                if WINDOW_3Y[0] <= e["trade_date"] <= WINDOW_3Y[1]
                and e["status"] != "READY"
            ),
        },
        "overlay": {
            "existing_fact_set_digest": overlay["existing_fact_set_digest"],
            "backfill_bundle_digest": overlay["backfill_bundle_digest"],
            "combined_fact_set_digest": overlay["combined_fact_set_digest"],
        },
        "no_forward_fill": True,
        "full_cycle_proven": False,
    }

    # 3y / 5y verdicts from after
    three_ready, three_blocked = _window_blocked(after_entries, WINDOW_3Y)
    five_ready, five_blocked = _window_blocked(after_entries, WINDOW_5Y)
    after_report["after"]["verdicts"]["3Y_HISTORICAL_VALIDATION_READY"] = three_ready
    after_report["after"]["verdicts"]["5Y_HISTORICAL_VALIDATION_READY"] = five_ready
    after_report["3y_gate"]["status"] = (
        "THREE_YEAR_HISTORICAL_VALIDATION_READY"
        if three_ready
        else "BLOCKED"
    )

    OUT_READINESS_AFTER.write_text(
        _json.dumps(after_report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print(f"\nreported bundle: {len(backfill_facts)} facts -> {OUT_REPORTED.name}")
    print(f"overlay: {overlay['combined_fact_count']} combined -> {OUT_OVERLAY.name}")
    print(f"3y gate: {after_report['3y_gate']['status']} "
          f"({after_report['3y_gate']['ready_days']}/"
          f"{after_report['3y_gate']['required_days']} ready)")
    print(f"before earliest ready: {before['earliest_ready_trade_date']}")
    print(f"after earliest ready:  {after['earliest_ready_trade_date']}")
    return 0


def _day_readiness_all(facts, observations):
    from ashare_research.pit_valuation.pe_normalized_earnings_prototype import (
        _day_readiness,
        _trade_days,
    )

    return [_day_readiness(facts, observations, d) for d in _trade_days(observations)]


def _window_blocked(entries, window):
    covered = [e for e in entries if window[0] <= e["trade_date"] <= window[1]]
    blocked = [e for e in covered if e["status"] != "READY"]
    return (len(blocked) == 0), len(blocked)


if __name__ == "__main__":
    sys.exit(main())
