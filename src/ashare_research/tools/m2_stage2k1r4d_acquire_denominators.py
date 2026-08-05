"""M2 Stage 2K.1R4D — thin CLI for official quarterly denominator acquisition.

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

    # Extract facts from the verified cache.
    from ashare_research.pit_valuation.extraction import (
        extract_filing,
        extract_share_capital,
    )
    from ashare_research.pit_valuation.fact_builder import (
        build_reported_fact,
        build_share_capital_fact,
        load_market_calendar,
        load_role,
        write_isolated_bundles,
    )

    evidence = load_source_evidence()
    specs = load_extraction_specs()
    roles = load_role_registry()
    calendar = load_market_calendar(args.market_cache_root)
    ev_by_id = {e["evidence_id"]: e for e in evidence["entries"]}
    cache_root = Path(args.official_cache_root).resolve()
    registry = contracts.load_cache_registry()

    obj_by_evidence: dict[str, Path] = {}
    for obj in registry["objects"]:
        for eid in obj["evidence_ids"]:
            obj_by_evidence[eid] = cache_root / obj["object_key"]

    reported: list[dict] = []
    cells_meta: list[dict] = []
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
            cells_meta.append({"evidence_id": eid, "status": "missing_official_filing"})
            continue
        filing_specs = [s for s in specs["specs"] if s["report_type"] == entry["report_type"]]
        # Extract page texts once per filing and reuse for every cell, so a
        # large annual report is never parsed twice.
        from ashare_research.pit_valuation.extraction import _page_texts

        pages = _page_texts(pdf)
        cells = extract_filing(pdf, entry, filing_specs, page_texts=pages)
        all_cells.extend(cells)
        for cell in cells:
            role = load_role(cell.role_id)
            if cell.status != "acquired_reported_verified":
                cells_meta.append(
                    {"evidence_id": eid, "role_id": cell.role_id, "status": cell.status}
                )
                continue
            fact = build_reported_fact(cell, entry, role, market_calendar=calendar)
            reported.append(fact)
            cells_meta.append(
                {
                    "evidence_id": eid,
                    "role_id": cell.role_id,
                    "status": cell.status,
                    "fact_id": fact["fact_id"],
                    "value": fact["value"],
                }
            )
        # Precise period-end share count (half-year and annual only).
        if entry["report_type"] in ("half_year", "annual"):
            share_role = load_role("total_ordinary_shares_at_period_end")
            share_spec = next(
                s for s in specs["specs"] if s["role_id"] == "total_ordinary_shares_at_period_end"
            )
            scell = extract_share_capital(pdf, entry, share_spec, page_texts=pages)
            if scell.status == "acquired_reported_verified":
                fact = build_share_capital_fact(scell, entry, share_role, market_calendar=calendar)
                reported.append(fact)
                cells_meta.append(
                    {
                        "evidence_id": eid,
                        "role_id": "total_ordinary_shares_at_period_end",
                        "status": scell.status,
                        "fact_id": fact["fact_id"],
                        "value": fact["value"],
                    }
                )
            else:
                cells_meta.append(
                    {
                        "evidence_id": eid,
                        "role_id": "total_ordinary_shares_at_period_end",
                        "status": scell.status,
                    }
                )

    # Restatement / supersession lineage from comparative columns.
    from ashare_research.pit_valuation.reconciliation import detect_restatements

    ev_by_id = {e["evidence_id"]: e for e in evidence["entries"]}
    restated_facts, lineage_records = detect_restatements(all_cells, reported, ev_by_id)
    reported.extend(restated_facts)

    # Weighted-average-share derivation (reconciled bundle).
    from decimal import Decimal

    from ashare_research.pit_valuation.reconciliation import (
        derive_weighted_average_shares,
    )

    reconciled: list[dict] = []
    shares_meta: list[dict] = []
    fact_by_key: dict[str, dict] = {}
    for f in reported:
        fact_by_key[f"{f['source_id']}:{f['concept_id']}"] = f
    for entry in evidence["entries"]:
        if entry["source_role"] != "exchange_official":
            continue
        eid = entry["evidence_id"]
        profit = next(
            (
                f
                for f in reported
                if f["source_id"] == f"r4d:{eid}"
                and f["concept_id"] == "net_profit_attributable_to_parent"
            ),
            None,
        )
        eps = next(
            (
                f
                for f in reported
                if f["source_id"] == f"r4d:{eid}" and f["concept_id"] == "basic_eps"
            ),
            None,
        )
        if profit is None or eps is None:
            shares_meta.append(
                {
                    "evidence_id": eid,
                    "status": "missing_operands",
                    "note": "profit or EPS not acquired",
                }
            )
            continue
        der = derive_weighted_average_shares(
            profit_yuan=Decimal(str(profit["value"])),
            eps=Decimal(str(eps["value"])),
        )
        if der.status == "exact_derivation":
            role = load_role("weighted_average_total_ordinary_shares")
            from ashare_research.pit_valuation.contracts import PERIOD_TYPE_BY_REPORT

            period_type = PERIOD_TYPE_BY_REPORT[entry["report_type"]]
            fact = {
                "fact_id": "",
                "fact_version": 1,
                "concept_id": role["concept_id"],
                "concept_version": role["concept_version"],
                "symbol": "601857.SH",
                "value": float(str(der.derived_value)),
                "unit": role["canonical_unit"],
                "context_id": f"601857.SH|{entry['fiscal_year']}|{period_type}|consolidated",
                "is_derived": True,
                "derivation_definition_id": "r4d-weighted-average-shares-v1",
                "derivation_version": "1",
                "input_fact_ids": f"{profit['fact_id']},{eps['fact_id']}",
                "source_tier": "reconciled_derived",
                "source_id": f"r4d:derived:{eid}",
                "source_hash": "",
                "available_at": entry["announcement_date"],
                "restatement_version": "original",
                "eligible_for_metrics": True,
                "normalization_rule": "profit/eps",
            }
            from ashare_research.facts.identity import build_fact_id

            fact["fact_id"] = build_fact_id(fact)
            reconciled.append(fact)
            shares_meta.append(
                {"evidence_id": eid, "status": "exact_derivation", "fact_id": fact["fact_id"]}
            )
        else:
            shares_meta.append(
                {
                    "evidence_id": eid,
                    "status": der.status,
                    "note": der.notes,
                    "implied_low": str(der.implied_low) if der.implied_low else None,
                    "implied_high": str(der.implied_high) if der.implied_high else None,
                }
            )

    write_isolated_bundles(
        Path(args.output_root).resolve(),
        reported=reported,
        reconciled=reconciled,
        evidence=evidence,
    )

    # Coverage matrix + gap ledger + readiness.
    grid = readiness.build_expected_grid(evidence, roles)
    cells_by_key: dict[str, dict] = {}
    for m in cells_meta:
        if "role_id" in m:
            cell_id = f"{m['evidence_id']}:{m['role_id']}"
            cells_by_key[cell_id] = m
    for m in shares_meta:
        cell_id = f"{m['evidence_id']}:weighted_average_total_ordinary_shares"
        if m["status"] == "exact_derivation":
            status = "acquired_reconciled_derived"
        elif m["status"] == "ambiguous_due_to_eps_rounding":
            status = "weighted_average_share_ambiguous_due_to_eps_rounding"
        else:
            status = "not_separately_disclosed"
        cells_by_key[cell_id] = {"status": status, "fact_ids": [m.get("fact_id", "")]}
    grid = readiness.apply_extraction_statuses(grid, cells_by_key=cells_by_key)
    gaps = readiness.gap_ledger_from_grid(grid)
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
    print(
        json.dumps(
            {
                "gate": gate,
                "reported": len(reported),
                "reconciled": len(reconciled),
                "gaps": len(gaps),
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
