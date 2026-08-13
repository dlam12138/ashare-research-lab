"""R4F.3A thin CLI — verify-contracts / acquire / formal / recheck-readiness.

Orchestration only: argument parsing and command dispatch.  All regex,
FactIdentity, restatement, and PIT logic lives in the pit_valuation modules
(``pe_historical_annual_backfill.py``) and the R4D/R4F.3 reused functions.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from ashare_research.pit_valuation.contracts import (  # noqa: E402
    validate_market_calendar_registry,
)
from ashare_research.pit_valuation.fact_builder import load_market_calendar  # noqa: E402
from ashare_research.pit_valuation.source_cache import (  # noqa: E402
    fetch_official_pdf,
    sha256_bytes,
)

R4F3A_REGISTRY = ROOT / "config" / "pit_valuation_market_calendar_registry_r4f3a_v1.json"
CALENDAR_V1_REGISTRY = ROOT / "config" / "pit_valuation_market_calendar_registry_v1.json"
CONTRACT = ROOT / "config" / "pe_3y_historical_backfill_contract_v1.json"
SOURCE_EVIDENCE = ROOT / "config" / "pe_3y_historical_backfill_source_evidence_v1.json"
CACHE_REGISTRY = ROOT / "config" / "pe_3y_historical_backfill_cache_registry_v1.json"
EXTRACTION_SPECS = ROOT / "config" / "pe_3y_historical_backfill_extraction_specs_v1.json"


def _load_json(path: Path) -> dict:
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


def cmd_verify_contracts(args: argparse.Namespace) -> int:
    """Validate every R4F3A contract; check calendar overlap."""
    from ashare_research.pit_valuation.fact_builder import next_trading_day

    contract = _load_json(CONTRACT)
    if contract["schema"] != "pe_3y_historical_backfill_contract_v1":
        print("FAIL: contract schema")
        return 1
    if contract["target_logical_cell_count"] != 5:
        print("FAIL: target_logical_cell_count != 5")
        return 1
    ev = _load_json(SOURCE_EVIDENCE)
    for e in ev["entries"]:
        if e["source_role"] != "exchange_official":
            print(f"FAIL: {e['evidence_id']} not exchange_official")
            return 1
    cache = _load_json(CACHE_REGISTRY)
    for o in cache["objects"]:
        if len(o["sha256"]) != 64 or o["media_type"] != "application/pdf":
            print(f"FAIL: cache object {o['object_key']}")
            return 1
    reg = _load_json(R4F3A_REGISTRY)
    validate_market_calendar_registry(reg)
    # overlap reconciliation vs calendar v1: compare the pinned v1 object's
    # trading dates against the R4F3A calendar.  v1's own required_start
    # (2020-01-01, a statutory holiday) is deliberately NOT applied here —
    # the overlap comparison itself is the semantic proof.
    v1 = _load_json(CALENDAR_V1_REGISTRY)
    cal_new = load_market_calendar(args.market_cache_root, registry=reg)
    v1_obj = v1["object_key"]
    import pandas as pd

    v1_path = Path(args.market_cache_root).resolve() / v1_obj
    v1_df = pd.read_parquet(v1_path)
    old_days = set(str(d) for d in v1_df["trade_date"].tolist())
    new_days = set(cal_new["trade_dates"])
    overlap_start = max(sorted(old_days)[0], sorted(new_days)[0])
    overlap_end = min(sorted(old_days)[-1], sorted(new_days)[-1])
    old_in = {d for d in old_days if overlap_start <= d <= overlap_end}
    new_in = {d for d in new_days if overlap_start <= d <= overlap_end}
    missing = old_in - new_in
    extra = new_in - old_in
    if missing or extra or old_days - new_days:
        print(
            f"FAIL: calendar overlap mismatch "
            f"(missing {len(missing)}, extra {len(extra)})"
        )
        return 1
    # earliest announcement resolvable
    first = min(e["announcement_date"] for e in ev["entries"])
    try:
        eff = next_trading_day(first, cal_new["trade_dates"])
    except Exception as exc:
        print(f"FAIL: earliest announcement {first} unresolvable: {exc}")
        return 1
    print(
        f"pass: contracts OK; calendar overlap OK (v1 {len(old_in)} = "
        f"new {len(new_in)}); earliest announcement {first} -> {eff}"
    )
    return 0


def cmd_acquire(args: argparse.Namespace) -> int:
    """Download missing official PDFs into the external cache (network)."""
    from pypdf import PdfReader

    ev = _load_json(SOURCE_EVIDENCE)
    reg = _load_json(CACHE_REGISTRY)
    cache_root = Path(args.official_cache_root).resolve()
    objects = cache_root / "objects"
    objects.mkdir(parents=True, exist_ok=True)
    existing = {o["sha256"] for o in reg["objects"]}
    for e in ev["entries"]:
        url = e["proof_url"]
        data = fetch_official_pdf(url, retries=3)
        digest = sha256_bytes(data)
        target = objects / f"{digest}.pdf"
        if not target.is_file():
            target.write_bytes(data)
        pages = len(PdfReader(str(target)).pages)
        if digest not in existing:
            reg["objects"].append(
                {
                    "object_key": f"objects/{digest}.pdf",
                    "sha256": digest,
                    "byte_size": len(data),
                    "page_count": pages,
                    "media_type": "application/pdf",
                    "evidence_ids": [e["evidence_id"]],
                    "registry_version": "r4f3a-v1",
                    "reporting_period": f"{e['fiscal_year']}-annual",
                    "announcement_date": e["announcement_date"],
                }
            )
        print(f"acquired {e['evidence_id']}: {digest[:16]}… {len(data)}B {pages}p")
    CACHE_REGISTRY.write_text(
        json.dumps(reg, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"cache registry updated: {len(reg['objects'])} objects")
    return 0


def cmd_formal(args: argparse.Namespace) -> int:
    """Fully offline: verify cache, extract, build facts, overlay, readiness."""
    import subprocess

    # 1. verify cached objects exist and match registry
    reg = _load_json(CACHE_REGISTRY)
    cache_root = Path(args.official_cache_root).resolve()
    for o in reg["objects"]:
        p = cache_root / o["object_key"]
        if not p.is_file():
            print(f"FAIL: cache object missing {o['object_key']}")
            return 1
        if sha256_bytes(p.read_bytes()) != o["sha256"]:
            print(f"FAIL: cache object hash mismatch {o['object_key']}")
            return 1
    print(f"pass: {len(reg['objects'])} cache objects verified (offline)")
    # 2. extraction + build via the internal orchestration modules
    rc1 = subprocess.call(
        [sys.executable, str(ROOT / "src/ashare_research/tools/r4f3a_extraction_probe.py")]
    )
    if rc1 != 0:
        print("FAIL: extraction probe")
        return rc1
    rc2 = subprocess.call(
        [sys.executable, str(ROOT / "src/ashare_research/tools/r4f3a_build.py")]
    )
    if rc2 != 0:
        print("FAIL: build")
        return rc2
    print("formal: extraction + build OK")
    return 0


def cmd_recheck_readiness(args: argparse.Namespace) -> int:
    """Rerun the R4F.3 readiness engine on the overlay (offline)."""
    import subprocess

    rc = subprocess.call(
        [sys.executable, str(ROOT / "src/ashare_research/tools/r4f3a_build.py")]
    )
    if rc != 0:
        print("FAIL: recheck-readiness")
        return rc
    after_path = (
        ROOT / "reports"
        / "petrochina_pe_normalized_earnings_3y_readiness_after_backfill_v1.json"
    )
    after = _load_json(after_path)
    print(
        f"3y gate: {after['3y_gate']['status']} "
        f"({after['3y_gate']['ready_days']}/{after['3y_gate']['required_days']} ready, "
        f"{after['3y_gate']['blocked_days']} blocked)"
    )
    print(
        f"earliest ready: {after['after']['earliest_ready_trade_date']} | "
        f"5y: {after['after']['verdicts']['5Y_HISTORICAL_VALIDATION_READY']}"
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="R4F3A PE historical backfill CLI")
    sub = p.add_subparsers(dest="command", required=True)

    pv = sub.add_parser("verify-contracts", help="validate contracts + calendar overlap")
    pv.add_argument("--market-cache-root", type=Path, default=ROOT / "tmp/market_cache/baostock")
    pv.set_defaults(func=cmd_verify_contracts)

    pa = sub.add_parser("acquire", help="download official PDFs (network)")
    pa.add_argument("--official-cache-root", type=Path, required=True)
    pa.set_defaults(func=cmd_acquire)

    pf = sub.add_parser("formal", help="offline verify + extract + build")
    pf.add_argument("--official-cache-root", type=Path, required=True)
    pf.set_defaults(func=cmd_formal)

    pr = sub.add_parser("recheck-readiness", help="rerun readiness on overlay")
    pr.set_defaults(func=cmd_recheck_readiness)

    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
