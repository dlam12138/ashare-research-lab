"""M2 Stage 2K.1R4D.1 — thin CLI for official quarterly denominator acquisition.

This CLI only: parses arguments, calls the pit_valuation package modules,
writes report artifacts, and returns an exit code.  No extraction regex, fact
formula, or readiness logic lives here.

Commands:

    acquire   --official-cache-root <external-root>
    formal    --official-cache-root <external-root>
              --market-cache-root <verified-market-root>
              --output-root <isolated-output>
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from ashare_research.pit_valuation import contracts, readiness, source_cache
from ashare_research.pit_valuation.contracts import (
    CACHE_REGISTRY_PATH,
    PERIOD_TYPE_BY_REPORT,
    load_extraction_specs,
    load_role_registry,
    load_source_evidence,
)

ROOT = Path(__file__).resolve().parents[3]
REPORTS = ROOT / "reports"


def _cmd_verify_contracts(args: argparse.Namespace) -> int:
    """Validate every R4D contract (offline, no cache required)."""
    digests = contracts.validate_all_contracts()
    print(json.dumps(digests, indent=1))
    return 0


def _cmd_acquire(args: argparse.Namespace) -> int:
    """Validate contracts, then acquire the official external cache."""
    contracts.validate_all_contracts()
    result = source_cache.acquire(args.official_cache_root)
    registered = []
    for obj in result.get("objects", []):
        registered.append(
            {
                "object_key": obj["object_key"],
                "sha256": obj["sha256"],
                "byte_size": obj["byte_size"],
                "page_count": obj["page_count"],
                "media_type": "application/pdf",
                "evidence_ids": obj["evidence_ids"],
                "reporting_period": obj["reporting_period"],
                "registry_version": "1",
            }
        )
    source_cache.write_cache_registry(CACHE_REGISTRY_PATH, registered)
    (REPORTS / "petrochina_pit_denominator_source_cache_verification_v1.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
    )
    print(json.dumps(result, ensure_ascii=False, indent=1)[:4000])
    return 0 if result.get("all_objects_ok", False) else 2


def _concept_to_role(concept_id: str, roles: dict) -> str:
    for r in roles["roles"]:
        if r["concept_id"] == concept_id:
            return r["role_id"]
    return concept_id


def _fact_cell_key(fact: dict, roles: dict) -> str | None:
    """Grid cell key (evidence_id:role_id) for a fact.

    Derived facts carry ``r4d:<evidence_id>`` source_id; restated facts are
    mapped to their superseded original's cell by the caller.
    """
    source_id = fact.get("source_id", "")
    if not source_id.startswith("r4d:"):
        return None
    eid = source_id.split(":", 1)[1]
    role_id = _concept_to_role(fact.get("concept_id", ""), roles)
    return f"{eid}:{role_id}"


def _build_derived_fact(
    d: dict,
    role: dict,
    ev_by_id: dict,
    calendar: dict,
) -> dict:
    """Build a reconciled_derived fact from a constancy derivation record."""
    from ashare_research.facts.identity import build_fact_id
    from ashare_research.pit_valuation.contracts import CalendarCoverageGapError
    from ashare_research.pit_valuation.fact_builder import next_trading_day

    eid = d["evidence_id"]
    entry = ev_by_id.get(eid, {})
    fy = d["fiscal_year"]
    rt = d["report_type"]
    period_end = d["period_end"]
    is_instant = role["instant_or_duration"] == "instant"
    if is_instant:
        context_id = f"601857.SH|{fy}|instant|consolidated|{period_end}"
    else:
        context_id = f"601857.SH|{fy}|{PERIOD_TYPE_BY_REPORT[rt]}|consolidated"
    announcement_date = entry.get("announcement_date", "")
    effective_from = ""
    pit_time_contract_gap = ""
    pit_derivation: dict = {}
    if announcement_date and calendar.get("trade_dates"):
        try:
            effective_from = next_trading_day(announcement_date, calendar["trade_dates"])
            pit_derivation = {
                "rule_id": "announcement-date-to-next-trading-day-v1",
                "calendar_object_id": calendar.get("calendar_object_id", ""),
                "calendar_sha256": calendar.get("calendar_sha256", ""),
                "input_announcement_date": announcement_date,
                "selected_next_trading_day": effective_from,
            }
        except CalendarCoverageGapError:
            # Fail-closed: the calendar does not cover the announcement, so the
            # PIT time contract is unresolved.  Never backfill to the nearest
            # calendar boundary.
            effective_from = ""
            pit_time_contract_gap = "calendar_coverage_gap"
    fact: dict = {
        "fact_id": "",
        "fact_version": 1,
        "concept_id": role["concept_id"],
        "concept_version": role["concept_version"],
        "symbol": "601857.SH",
        "value": float(d["value"]),
        "unit": role["canonical_unit"],
        "context_id": context_id,
        "is_derived": True,
        "derivation_definition_id": d.get(
            "derivation_definition_id", "r4d1-share-continuity-constancy-v1"
        ),
        "derivation_version": d.get("derivation_version", "1"),
        "input_fact_ids": "",
        "source_tier": "reconciled_derived",
        "source_id": f"r4d:{eid}",
        "source_document": entry.get("proof_url", ""),
        "source_hash": "",
        "source_object_sha256": "",
        "excerpt_hash": "",
        "filing_date": announcement_date,
        "period_end": period_end,
        "restatement_version": "original",
        "announcement_date": announcement_date,
        "available_at": announcement_date,
        "effective_from": effective_from,
        "pit_time_contract_gap": pit_time_contract_gap,
        "effective_from_derivation": pit_derivation,
        "calendar_object_id": calendar.get("calendar_object_id", ""),
        "calendar_sha256": calendar.get("calendar_sha256", ""),
        "normalization_rule": "share-continuity-constancy",
        "verification_status": "verified",
        "verification_note": d.get("note", ""),
        "eligible_for_metrics": True,
        "created_at": "",
    }
    fact["fact_id"] = build_fact_id(fact)
    return fact


def _cmd_formal(args: argparse.Namespace) -> int:
    """Offline formal verification, extraction, facts, readiness."""
    if args.official_cache_root is None or args.market_cache_root is None:
        print("formal requires --official-cache-root and --market-cache-root", file=sys.stderr)
        return 2
    contracts.validate_all_contracts()
    ver = source_cache.verify_official_cache(args.official_cache_root)
    if not ver.get("all_objects_ok", False):
        print("official cache verification failed", file=sys.stderr)
        return 2

    from ashare_research.pit_valuation.extraction import (
        _page_texts,
        extract_filing,
        extract_share_capital,
    )
    from ashare_research.pit_valuation.fact_builder import (
        build_fact_id_migration_report,
        build_reported_fact,
        build_share_capital_fact,
        load_market_calendar,
        load_role,
        write_isolated_bundles,
    )
    from ashare_research.pit_valuation.reconciliation import detect_restatements
    from ashare_research.pit_valuation.share_continuity import (
        constancy_derivation_available,
        derive_period_end_shares_from_constancy,
        derive_weighted_average_shares_from_constancy,
    )

    evidence = load_source_evidence()
    specs = load_extraction_specs()
    roles = load_role_registry()
    # The calendar must resolve every in-scope announcement to a real next
    # trading day; the earliest announcement is the binding start constraint
    # (2020 Q1 reports announced ~2020-04-30; the 2020-01-01 boundary itself is
    # a statutory holiday and is not a trading day).
    exchange_entries = [
        e for e in evidence["entries"] if e["source_role"] == "exchange_official"
    ]
    earliest_announcement = min(
        e["announcement_date"] for e in exchange_entries
    )
    calendar = load_market_calendar(
        args.market_cache_root, required_start=earliest_announcement
    )
    ev_by_id = {e["evidence_id"]: e for e in evidence["entries"]}
    cache_root = Path(args.official_cache_root).resolve()
    registry = contracts.load_cache_registry()

    obj_by_evidence: dict[str, Path] = {}
    object_sha_by_evidence: dict[str, str] = {}
    for obj in registry["objects"]:
        for eid in obj["evidence_ids"]:
            obj_by_evidence[eid] = cache_root / obj["object_key"]
            object_sha_by_evidence[eid] = obj["sha256"]

    reported: list[dict] = []
    all_cells: list = []
    # Economic facts are built once per filing from the exchange_official
    # object.  A byte-identical issuer alias shares the same content object
    # and is recorded via the cache registry's evidence aliases; it never
    # produces a second economic fact.
    for entry in evidence["entries"]:
        if entry["source_role"] != "exchange_official":
            continue
        eid = entry["evidence_id"]
        pdf = obj_by_evidence.get(eid)
        if pdf is None or not pdf.is_file():
            continue
        filing_specs = [s for s in specs["specs"] if s["report_type"] == entry["report_type"]]
        # Extract page texts once per filing and reuse for every cell.
        pages = _page_texts(pdf)
        cells = extract_filing(pdf, entry, filing_specs, page_texts=pages)
        all_cells.extend(cells)
        obj_sha = object_sha_by_evidence.get(eid, "")
        for cell in cells:
            role = load_role(cell.role_id)
            if cell.status != "acquired_reported_verified":
                continue
            reported.append(
                build_reported_fact(
                    cell, entry, role, market_calendar=calendar, object_sha=obj_sha
                )
            )
        # Precise period-end share count (half-year and annual only).
        if entry["report_type"] in ("half_year", "annual"):
            share_role = load_role("total_ordinary_shares_at_period_end")
            share_spec = next(
                s for s in specs["specs"] if s["role_id"] == "total_ordinary_shares_at_period_end"
            )
            scell = extract_share_capital(pdf, entry, share_spec, page_texts=pages)
            if scell.status == "acquired_reported_verified":
                reported.append(
                    build_share_capital_fact(
                        scell, entry, share_role, market_calendar=calendar, object_sha=obj_sha
                    )
                )

    # Restatement / supersession lineage from comparative columns.
    restated_facts, lineage_records = detect_restatements(
        all_cells,
        reported,
        ev_by_id,
        market_calendar=calendar,
        object_sha_by_evidence=object_sha_by_evidence,
    )
    reported.extend(restated_facts)

    # Fail-closed on the PIT time contract: a fact whose effective_from is
    # unresolved (calendar coverage gap) is not PIT-ready and must not enter
    # the reported bundle.  Its grid cell becomes an explicit
    # pit_time_contract gap — the announcement is never backfilled to the
    # nearest calendar boundary.
    pit_gapped_keys: set[str] = set()
    bundled: list[dict] = []
    for f in reported:
        if f.get("pit_time_contract_gap"):
            key = _fact_cell_key(f, roles)
            if key:
                pit_gapped_keys.add(key)
        else:
            bundled.append(f)
    reported = bundled

    # Share-continuity constancy derivation (reconciled bundle).
    register = contracts.load_share_continuity_register()
    constancy = constancy_derivation_available(register)
    exchange = [
        e for e in evidence["entries"] if e["source_role"] == "exchange_official"
    ]
    reconciled: list[dict] = []
    if constancy:
        for d in derive_period_end_shares_from_constancy(register, exchange):
            role = next(
                r for r in roles["roles"]
                if r["role_id"] == "total_ordinary_shares_at_period_end"
            )
            reconciled.append(_build_derived_fact(d, role, ev_by_id, calendar))
        for d in derive_weighted_average_shares_from_constancy(register, exchange):
            role = next(
                r for r in roles["roles"]
                if r["role_id"] == "weighted_average_total_ordinary_shares"
            )
            reconciled.append(_build_derived_fact(d, role, ev_by_id, calendar))
    else:
        # Weighted-average share count is not derivable: the report never
        # discloses it and the constancy evidence is not trusted.  The cells
        # stay explicit gaps (recorded below).
        pass

    write_isolated_bundles(
        Path(args.output_root).resolve(),
        reported=reported,
        reconciled=reconciled,
        evidence=evidence,
    )

    # Coverage matrix + gap ledger + fact/gap binding + readiness.
    grid = readiness.build_expected_grid(evidence, roles)
    cells_by_key: dict[str, dict] = {}
    direct_cell: dict[str, str] = {}
    for f in reported:
        if f.get("restatement_version") == "restated_1":
            continue
        key = _fact_cell_key(f, roles)
        if key is not None:
            direct_cell[f["fact_id"]] = key
    for f in reported:
        if f.get("restatement_version") == "restated_1":
            key = direct_cell.get(f.get("supersedes_fact_id", ""))
            if key is None:
                continue
        else:
            key = _fact_cell_key(f, roles)
            if key is None:
                continue
        meta = cells_by_key.setdefault(
            key, {"status": "acquired_reported_verified", "fact_ids": [], "gap_ids": []}
        )
        meta["fact_ids"].append(f["fact_id"])
    for f in reconciled:
        key = _fact_cell_key(f, roles)
        if key is None:
            continue
        meta = cells_by_key.setdefault(
            key, {"status": "acquired_reconciled_derived", "fact_ids": [], "gap_ids": []}
        )
        meta["status"] = "acquired_reconciled_derived"
        meta["fact_ids"].append(f["fact_id"])

    status_overrides: dict[str, str] = {}
    for cell in grid:
        if cell["cell_id"] in pit_gapped_keys:
            # Unresolved PIT time contract (calendar coverage gap), fail-closed.
            status_overrides[cell["cell_id"]] = "calendar_coverage_gap"
        elif (
            cell["role_id"] == "weighted_average_total_ordinary_shares"
            and cell["cell_id"] not in cells_by_key
        ):
            status_overrides[cell["cell_id"]] = (
                "weighted_average_share_ambiguous_due_to_eps_rounding"
            )
    grid = readiness.apply_extraction_statuses(
        grid, cells_by_key=cells_by_key, status_overrides=status_overrides
    )
    gaps = readiness.gap_ledger_from_grid(grid)
    binding = readiness.validate_coverage_fact_gap_binding(
        grid, gaps, reported + reconciled
    )
    read = readiness.build_readiness(evidence, roles, grid, gaps)
    gate = readiness.decide_from_readiness(
        read,
        cache_trusted=ver["all_objects_ok"],
        extraction_trusted=True,
        identity_trusted=True,
        pit_trusted=True,
    )

    out = Path(args.output_root).resolve()
    out.mkdir(parents=True, exist_ok=True)
    readiness.write_report(out / "petrochina_pit_denominator_acquisition_coverage_v1.json", {
        "schema": "pit_denominator_acquisition_coverage_v1",
        "grid": grid,
        "cell_count": len(grid),
    })
    readiness.write_report(out / "petrochina_pit_denominator_gap_ledger_v1.json", {
        "schema": "pit_denominator_gap_ledger_v1",
        "gaps": gaps,
        "gap_count": len(gaps),
    })
    readiness.write_report(out / "petrochina_pit_denominator_readiness_v1.json", {
        "schema": "pit_denominator_readiness_v1",
        "decision": gate,
        "readiness": read,
    })
    readiness.write_report(out / "petrochina_pit_denominator_version_lineage_v1.json", {
        "schema": "pit_denominator_version_lineage_v1",
        "symbol": "601857.SH",
        "chains": lineage_records,
        "chain_count": len(lineage_records),
        "restated_fact_count": len(restated_facts),
    })
    readiness.write_report(out / "petrochina_pit_denominator_share_continuity_v1.json", register)

    # Context-v2 fact-id migration (old R4D v1 reported bundle -> Context v2).
    old_bundle = REPORTS / "petrochina_pit_denominator_reported_fact_bundle_v1.json"
    if old_bundle.exists():
        old_facts = json.load(old_bundle.open(encoding="utf-8"))["facts"]
        migration = build_fact_id_migration_report(old_facts)
        readiness.write_report(
            out / "petrochina_pit_denominator_fact_id_migration_v1.json", migration
        )
    readiness.write_report(
        out / "petrochina_pit_denominator_coverage_binding_validation_v1.json", binding
    )
    print(
        json.dumps(
            {
                "gate": gate,
                "reported": len(reported),
                "reconciled": len(reconciled),
                "gaps": len(gaps),
                "constancy": constancy,
                "binding_ok": binding["ok"],
            },
            indent=1,
        )
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="m2_stage2k1r4d_acquire_denominators",
        description="M2 Stage 2K.1R4D official quarterly valuation denominator acquisition",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_verify = sub.add_parser("verify-contracts", help="validate all R4D contracts")
    p_verify.set_defaults(func=_cmd_verify_contracts)

    p_acquire = sub.add_parser("acquire", help="download official filings into the external cache")
    p_acquire.add_argument("--official-cache-root", type=Path, required=True)
    p_acquire.set_defaults(func=_cmd_acquire)

    p_formal = sub.add_parser("formal", help="offline verify + extract + facts + readiness")
    p_formal.add_argument("--official-cache-root", type=Path, required=True)
    p_formal.add_argument("--market-cache-root", type=Path, required=True)
    p_formal.add_argument("--output-root", type=Path, required=True)
    p_formal.set_defaults(func=_cmd_formal)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
