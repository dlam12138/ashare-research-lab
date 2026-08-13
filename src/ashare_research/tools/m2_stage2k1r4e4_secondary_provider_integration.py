"""M2 Stage 2K.1R4E.4 — selected secondary provider integration CLI.

Thin CLI for the R4E.4 provider integration: it parses arguments, calls the
pit_valuation package modules, writes report artifacts and returns a fail-closed
exit code.  No formula, join, reconciliation or identity logic lives here.

Modes:

    promote --r4e3-cache-root <root> --formal-cache-root <root> --output-root <out>
        Locate the R4E.3 selected Tencent object (``d760923a…``), verify its
        file SHA-256, canonical table digest, row count and date range, and copy
        it content-addressed (byte-identical) into the formal external market
        cache.  Also promotes the pinned Baostock primary ``c6771aa5…``.  Writes
        ``petrochina_tencent_snapshot_promotion_receipt_v1.json``.

    registry-draft [--output-root <out>]
        Write the draft registry v4
        (``integration_status = PENDING_REAL_RECONCILIATION``,
        ``reconciliation_status = pending``).  Offline; never writes a pass.

    reconcile --registry <path> --cache-root <root> --output-root <out>
        Load and validate both pinned objects by role, run the real formal
        double-source reconciliation (v2 contract), write the v2 reconciliation
        report + mismatch ledger, and finalize the registry v4
        (``integration_status = COMPLETE``, ``reconciliation_status = pass``)
        only after the reconciliation actually passes.

    verify --registry <path>
        Offline: validate the registry v4 role contract and report its state.

    fixtures --fixture-root <root> --cache-root <root> --output-root <out>
        CI-only synthetic run with synthetic dual-source objects
        (``evidence_class = SYNTHETIC_ENGINEERING_ONLY``); never substitutes for
        the real provider selection.

Exit codes: 0 = ok, 1 = gaps / not trusted.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

from ashare_research.pit_valuation import (
    market_reconciliation as mkt,
)
from ashare_research.pit_valuation import (
    provider_roles,
    series_contract,
)
from ashare_research.pit_valuation import (
    secondary_provider_preflight as spp,
)

ROOT = Path(__file__).resolve().parents[3]
REPORTS = ROOT / "reports"
EVENTS = ROOT / "events"

# R4E.3 selected Tencent object identity (frozen from the R4E.3 decision).
R4E3_TENCENT_OBJECT_SHA = (
    "d760923aae952d9ba400d792d4155b4c6dfa3b728210de64001aa6024c8f7dd7"
)
R4E3_TENCENT_TABLE_DIGEST = (
    "e6cbee888949b13c0ee47a6193d58026ad6da72a332ffd66948ee4bc4b908cda"
)
R4E3_TENCENT_ENDPOINT = "web.ifzq.gtimg.cn"
R4E3_TENCENT_TRANSPORT = "akshare"
R4E3_TENCENT_UNDERLYING = "tencent"

# Pinned Baostock primary (registry v3, carried into registry v4).
PRIMARY_BAOSTOCK_SHA = (
    "c6771aa57b0210ee558a91c7bdb87cc346ce910a395eda057cb9d7224475ab67"
)
PRIMARY_BAOSTOCK_TABLE_DIGEST = (
    "ba4f83185b9644e157e4439aaea26d8692db7043f6d3ce06dc502549d60dc96c"
)

# R4E.3 preflight digests bound into registry v4.
R4E3_COMPARISON_DIGEST = (
    "21a1ad83f3f6de6e6260c3db210793bf5ba7290946b4398e3d69636df7dc0013"
)
R4E3_MISMATCH_LEDGER_DIGEST = (
    "d1dba16ca46cdd059e745e88b95298bbf2192eca929c51e004893f37f8928b8c"
)

REGISTRY_V4_REL = "events/market_data_snapshot_registry_v4.json"
RECEIPT_REL = "reports/petrochina_tencent_snapshot_promotion_receipt_v1.json"
RECONCILIATION_V2_REL = "reports/petrochina_market_close_reconciliation_v2.json"
LEDGER_V2_REL = "reports/petrochina_market_close_mismatch_ledger_v2.json"

# Report file names (relative to an output root).
RECEIPT_NAME = "petrochina_tencent_snapshot_promotion_receipt_v1.json"
RECONCILIATION_V2_NAME = "petrochina_market_close_reconciliation_v2.json"
LEDGER_V2_NAME = "petrochina_market_close_mismatch_ledger_v2.json"
DECISION_V2_NAME = "m2_stage2k1r4e4_decision.json"

# Frozen registry v4 contract values.
SYMBOL = series_contract.SYMBOL
REQUIRED_TRADE_DAYS = 1351
FIRST_TRADE_DATE = "2021-01-04"
LAST_TRADE_DATE = "2026-07-31"

STATUS_PENDING = "pending"
STATUS_PENDING_RECON = "PENDING_REAL_RECONCILIATION"
STATUS_COMPLETE = "COMPLETE"

DECISION_NOT_TRUSTED = "PIT_VALUATION_SERIES_NOT_TRUSTED"


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
    )


def _structured(decision: str, *, status: str, failed_contract: str = "",
                error_type: str = "", message: str = "") -> dict[str, Any]:
    return {
        "status": status,
        "decision": decision,
        "exit_code": 2 if decision == DECISION_NOT_TRUSTED else 1,
        "failed_contract": failed_contract,
        "error_type": error_type,
        "message": message,
    }


# ── object verification (offline, content-addressed) ───────────────────────


def _load_normalized_rows(path: Path) -> list[dict[str, Any]]:
    """Read a canonical parquet object back into normalized rows (R4E.3 layout)."""
    import pandas as pd

    df = pd.read_parquet(path)
    rows: list[dict[str, Any]] = []
    for _, r in df.iterrows():
        rows.append({c: r[c] for c in df.columns})
    return rows


def verify_object_identity(
    path: Path,
    *,
    expected_sha: str,
    expected_table_digest: str,
    expected_row_count: int,
    expected_first: str,
    expected_last: str,
) -> dict[str, Any]:
    """Independently recompute an object's identity; raises ValueError on any mismatch.

    Never trusts the file name; never trusts a pre-written digest.  The canonical
    table digest is recomputed over the normalized rows.
    """
    data = path.read_bytes()
    actual_sha = _sha256_bytes(data)
    if actual_sha != expected_sha:
        raise ValueError(
            f"object sha mismatch: {actual_sha[:12]}... != {expected_sha[:12]}..."
        )
    rows = _load_normalized_rows(path)
    table_digest = spp.canonical_table_digest(rows)
    if table_digest != expected_table_digest:
        raise ValueError("object canonical table digest mismatch")
    trade_dates = sorted({str(r["trade_date"])[:10] for r in rows})
    if len(trade_dates) != expected_row_count:
        raise ValueError(
            f"object row_count {len(trade_dates)} != {expected_row_count}"
        )
    if trade_dates[0] != expected_first or trade_dates[-1] != expected_last:
        raise ValueError(
            f"object date range {trade_dates[0]}..{trade_dates[-1]} "
            f"!= {expected_first}..{expected_last}"
        )
    return {
        "sha256": actual_sha,
        "table_digest": table_digest,
        "row_count": len(trade_dates),
        "first_trade_date": trade_dates[0],
        "last_trade_date": trade_dates[-1],
    }


def _promote_byte_identical(src: Path, formal_root: Path, rel_key: str) -> str:
    """Copy an object byte-identical (content-addressed).  Returns the new SHA-256."""
    data = src.read_bytes()
    target = formal_root / rel_key
    target.parent.mkdir(parents=True, exist_ok=True)
    if not target.is_file():
        target.write_bytes(data)
    if target.read_bytes() != data:
        raise ValueError(f"promoted object not byte-identical: {rel_key}")
    return _sha256_bytes(target.read_bytes())


def validate_endpoint_identity(rows: list[dict[str, Any]], expected: str) -> None:
    """Reject rows that do not carry the frozen R4E.3 endpoint identity.

    Raises ValueError when any row's ``endpoint_identity`` is not the expected
    one.  Separate from :func:`verify_object_identity` so the endpoint binding
    is independently testable offline.
    """
    row_endpoints = {str(r.get("endpoint_identity", "")) for r in rows}
    if row_endpoints != {expected}:
        raise ValueError(f"tencent endpoint identity mismatch: {row_endpoints}")


# ── promote ────────────────────────────────────────────────────────────────


def promote_selected_tencent(
    *,
    r4e3_cache_root: Path,
    formal_cache_root: Path,
) -> dict[str, Any]:
    """Verify and promote the R4E.3 selected object into the formal cache.

    Both the primary (baostock ``c6771aa5…``) and the secondary Tencent object
    (``d760923a…``) are promoted byte-identical.  Raises ValueError on any
    identity mismatch; never falls back to Sina.
    """
    primary_src = r4e3_cache_root / "baostock" / f"{PRIMARY_BAOSTOCK_SHA}.parquet"
    tencent_src = (
        r4e3_cache_root / "r4e3" / "tencent_via_akshare"
        / f"{R4E3_TENCENT_OBJECT_SHA}.parquet"
    )
    if not primary_src.is_file():
        raise FileNotFoundError(f"primary baostock object absent: {primary_src}")
    if not tencent_src.is_file():
        raise FileNotFoundError(f"R4E.3 tencent object absent: {tencent_src}")

    verify_object_identity(
        primary_src,
        expected_sha=PRIMARY_BAOSTOCK_SHA,
        expected_table_digest=PRIMARY_BAOSTOCK_TABLE_DIGEST,
        expected_row_count=REQUIRED_TRADE_DAYS,
        expected_first=FIRST_TRADE_DATE,
        expected_last=LAST_TRADE_DATE,
    )
    tencent_identity = verify_object_identity(
        tencent_src,
        expected_sha=R4E3_TENCENT_OBJECT_SHA,
        expected_table_digest=R4E3_TENCENT_TABLE_DIGEST,
        expected_row_count=REQUIRED_TRADE_DAYS,
        expected_first=FIRST_TRADE_DATE,
        expected_last=LAST_TRADE_DATE,
    )
    # The normalized rows must carry the frozen R4E.3 endpoint identity.
    tencent_rows = _load_normalized_rows(tencent_src)
    validate_endpoint_identity(tencent_rows, R4E3_TENCENT_ENDPOINT)

    primary_key = f"baostock/{PRIMARY_BAOSTOCK_SHA}.parquet"
    tencent_key = f"r4e4/tencent_via_akshare/{R4E3_TENCENT_OBJECT_SHA}.parquet"
    primary_formal_sha = _promote_byte_identical(
        primary_src, formal_cache_root, primary_key
    )
    tencent_formal_sha = _promote_byte_identical(
        tencent_src, formal_cache_root, tencent_key
    )
    if tencent_formal_sha != R4E3_TENCENT_OBJECT_SHA:
        raise ValueError("promoted tencent object sha changed")

    return {
        "schema": "petrochina_tencent_snapshot_promotion_receipt_v1",
        "version": "1.0",
        "symbol": SYMBOL,
        "source_stage": "R4E.3",
        "selected_provider": "tencent_via_akshare",
        "selected_object_sha256": R4E3_TENCENT_OBJECT_SHA,
        "selected_table_digest": R4E3_TENCENT_TABLE_DIGEST,
        "formal_cache_object_sha256": tencent_formal_sha,
        "formal_cache_object_key": tencent_key,
        "row_count": tencent_identity["row_count"],
        "date_range": [tencent_identity["first_trade_date"], tencent_identity["last_trade_date"]],
        "transport_library": R4E3_TENCENT_TRANSPORT,
        "underlying_provider": R4E3_TENCENT_UNDERLYING,
        "endpoint_identity": R4E3_TENCENT_ENDPOINT,
        "promotion_mode": "byte_identical_content_addressed_copy",
        "byte_identity_preserved": True,
        "primary_object_sha256": PRIMARY_BAOSTOCK_SHA,
        "primary_table_digest": PRIMARY_BAOSTOCK_TABLE_DIGEST,
        "primary_formal_cache_object_key": primary_key,
        "primary_formal_cache_object_sha256": primary_formal_sha,
    }


def _cmd_promote(args: argparse.Namespace) -> int:
    try:
        receipt = promote_selected_tencent(
            r4e3_cache_root=Path(args.r4e3_cache_root),
            formal_cache_root=Path(args.formal_cache_root),
        )
    except Exception as exc:  # noqa: BLE001
        print(json.dumps(_structured(
            DECISION_NOT_TRUSTED, status="error", failed_contract="promotion",
            error_type=type(exc).__name__, message=str(exc)), indent=1))
        return 2
    _write_json(Path(args.output_root) / RECEIPT_NAME, receipt)
    print(json.dumps({"status": "ok", "receipt": receipt}, indent=1))
    return 0


# ── registry v4 ────────────────────────────────────────────────────────────


def build_registry_v4() -> dict[str, Any]:
    """Build the registry v4 draft (offline, deterministic)."""
    decision_payload = json.loads(
        (REPORTS / "m2_stage2k1r4e3_decision.json").read_text(encoding="utf-8")
    )
    r4e3_decision_digest = series_contract.canonical_digest(decision_payload)
    return {
        "contract": "market_data_snapshot_registry_v4",
        "schema_version": "4.0",
        "supersedes_registry": "events/market_data_snapshot_registry_v3.json",
        "supersession_reason": "selected_alternative_secondary_provider_formally_integrated",
        "data_class": "external_real_data_cache",
        "symbol": SYMBOL,
        "adjustment": "none",
        "currency": "CNY",
        "close_unit": "CNY/share",
        "frequency": "daily",
        "date_range": {
            "requested_start": "2021-01-01",
            "requested_end": "2026-07-31",
            "actual_start": FIRST_TRADE_DATE,
            "actual_end": LAST_TRADE_DATE,
        },
        "required_trade_days": REQUIRED_TRADE_DAYS,
        "providers": [
            {
                "provider_id": "baostock_primary",
                "provider_role": "primary",
                "transport_library": "baostock",
                "underlying_provider": "baostock",
                "provider_version": "0.9.3",
                "object_key": f"baostock/{PRIMARY_BAOSTOCK_SHA}.parquet",
                "sha256": PRIMARY_BAOSTOCK_SHA,
                "table_digest": PRIMARY_BAOSTOCK_TABLE_DIGEST,
                "ab_stability": "ACQUISITION_STABLE",
                "row_count": REQUIRED_TRADE_DAYS,
                "first_trade_date": FIRST_TRADE_DATE,
                "last_trade_date": LAST_TRADE_DATE,
                "adjustment": "none",
            },
            {
                "provider_id": "tencent_via_akshare",
                "provider_role": "secondary",
                "transport_library": R4E3_TENCENT_TRANSPORT,
                "underlying_provider": R4E3_TENCENT_UNDERLYING,
                "provider_version": "1.18.79",
                "endpoint_identity": R4E3_TENCENT_ENDPOINT,
                "object_key": f"r4e4/tencent_via_akshare/{R4E3_TENCENT_OBJECT_SHA}.parquet",
                "sha256": R4E3_TENCENT_OBJECT_SHA,
                "table_digest": R4E3_TENCENT_TABLE_DIGEST,
                "ab_stability": "ACQUISITION_STABLE",
                "row_count": REQUIRED_TRADE_DAYS,
                "first_trade_date": FIRST_TRADE_DATE,
                "last_trade_date": LAST_TRADE_DATE,
                "adjustment": "none",
            },
        ],
        "ab_stability": "ACQUISITION_STABLE",
        "integration_status": STATUS_PENDING_RECON,
        "reconciliation_status": STATUS_PENDING,
        "r4e3_decision_digest": r4e3_decision_digest,
        "r4e3_comparison_digest": R4E3_COMPARISON_DIGEST,
        "r4e3_mismatch_ledger_digest": R4E3_MISMATCH_LEDGER_DIGEST,
        "reconciliation_contract_version": mkt.RECONCILIATION_CONTRACT_VERSION_V2,
        "evidence_class": "external_real_data_cache",
    }


def _cmd_registry_draft(args: argparse.Namespace) -> int:
    try:
        registry = build_registry_v4()
        provider_roles.validate_provider_roles(registry)
    except Exception as exc:  # noqa: BLE001
        print(json.dumps(_structured(
            DECISION_NOT_TRUSTED, status="error", failed_contract="registry_v4_draft",
            error_type=type(exc).__name__, message=str(exc)), indent=1))
        return 2
    _write_json(ROOT / REGISTRY_V4_REL, registry)
    print(json.dumps({
        "status": "ok",
        "registry": REGISTRY_V4_REL,
        "integration_status": registry["integration_status"],
        "reconciliation_status": registry["reconciliation_status"],
    }, indent=1))
    return 0


# ── reconcile (real formal) ────────────────────────────────────────────────


def run_formal_reconciliation(
    *,
    registry: dict[str, Any],
    cache_root: Path,
) -> dict[str, Any]:
    """Load both objects by role, run the v2 reconciliation, and produce the
    v2 reports + the finalized registry delta.  Raises on any failure."""
    primary_entry, secondary_entry = provider_roles.resolve_registry_providers(registry)
    primary = mkt.load_and_validate_market_object_entry(registry, cache_root, primary_entry)
    secondary = mkt.load_and_validate_market_object_entry(
        registry, cache_root, secondary_entry
    )
    reconciliation = mkt.reconcile_market_close_series_v2(primary, secondary)
    ledger = mkt.build_mismatch_ledger_v2(reconciliation)
    ledger_digest = mkt.build_mismatch_ledger_digest(ledger)
    report = mkt.build_reconciliation_report_v2(
        primary, secondary, reconciliation, ledger_digest=ledger_digest
    )
    validation = mkt.validate_reconciliation_report_v2(report)
    if not validation["valid"]:
        raise ValueError(f"v2 reconciliation report invalid: {validation['errors']}")
    return {
        "primary": primary,
        "secondary": secondary,
        "reconciliation": reconciliation,
        "ledger": ledger,
        "ledger_digest": ledger_digest,
        "report": report,
        "reconciliation_digest": report["reconciliation_digest"],
    }


def _cmd_reconcile(args: argparse.Namespace) -> int:
    registry_path = Path(args.registry)
    try:
        registry = json.loads(registry_path.read_text(encoding="utf-8"))
        if registry.get("contract") != "market_data_snapshot_registry_v4":
            raise ValueError("registry is not v4")
        if registry.get("integration_status") != STATUS_PENDING_RECON:
            raise ValueError("registry v4 is not in PENDING_REAL_RECONCILIATION state")
        result = run_formal_reconciliation(
            registry=registry, cache_root=Path(args.cache_root)
        )
    except Exception as exc:  # noqa: BLE001
        print(json.dumps(_structured(
            DECISION_NOT_TRUSTED, status="error", failed_contract="formal_reconciliation",
            error_type=type(exc).__name__, message=str(exc)), indent=1))
        return 2

    _write_json(Path(args.output_root) / RECONCILIATION_V2_NAME, result["report"])
    _write_json(Path(args.output_root) / LEDGER_V2_NAME, result["ledger"])

    # Finalize the registry v4 only after the real formal reconciliation passed.
    reconciliation = result["reconciliation"]
    registry["integration_status"] = STATUS_COMPLETE
    registry["reconciliation_status"] = mkt.STATUS_PASS
    registry["reconciliation"] = {
        "contract_version": mkt.RECONCILIATION_CONTRACT_VERSION_V2,
        "common_trade_days": reconciliation["common_trade_days"],
        "primary_only_dates": reconciliation["primary_only_dates"],
        "secondary_only_dates": reconciliation["secondary_only_dates"],
        "max_abs_difference": reconciliation["max_abs_difference"],
        "nonzero_difference_count": reconciliation["nonzero_difference_count"],
        "differences_over_tolerance_count": reconciliation[
            "differences_over_tolerance_count"
        ],
        "daily_comparison_digest": reconciliation.get("daily_comparison_digest", ""),
        "mismatch_ledger_digest": result["ledger_digest"],
        "formal_reconciliation_digest": result["reconciliation_digest"],
    }
    _write_json(ROOT / REGISTRY_V4_REL, registry)
    print(json.dumps({
        "status": "ok",
        "reconciliation_status": mkt.STATUS_PASS,
        "integration_status": STATUS_COMPLETE,
        "common_trade_days": reconciliation["common_trade_days"],
        "max_abs_difference": reconciliation["max_abs_difference"],
        "differences_over_tolerance_count": reconciliation[
            "differences_over_tolerance_count"
        ],
        "reconciliation_digest": result["reconciliation_digest"],
    }, indent=1))
    return 0


# ── verify ─────────────────────────────────────────────────────────────────


def _cmd_verify(args: argparse.Namespace) -> int:
    try:
        registry = json.loads(Path(args.registry).read_text(encoding="utf-8"))
        if registry.get("contract") != "market_data_snapshot_registry_v4":
            raise ValueError("registry is not v4")
        summary = provider_roles.validate_provider_roles(registry)
        if registry.get("integration_status") not in (
            STATUS_PENDING_RECON, STATUS_COMPLETE
        ):
            raise ValueError(
                f"unexpected integration_status {registry.get('integration_status')!r}"
            )
    except Exception as exc:  # noqa: BLE001
        print(json.dumps(_structured(
            DECISION_NOT_TRUSTED, status="error", failed_contract="registry_v4_verify",
            error_type=type(exc).__name__, message=str(exc)), indent=1))
        return 2
    print(json.dumps({
        "status": "ok",
        "integration_status": registry["integration_status"],
        "reconciliation_status": registry["reconciliation_status"],
        "providers": summary,
    }, indent=1))
    return 0


# ── fixtures (CI, synthetic only) ──────────────────────────────────────────


def _cmd_fixtures(args: argparse.Namespace) -> int:
    """CI-only synthetic run; never substitutes for the real provider selection."""
    from ashare_research.pit_valuation import fixtures

    try:
        series_contract.validate_all_contracts()
        primary_rows, secondary_rows, _meta = fixtures.load_fixture_dual_market(
            Path(args.fixture_root)
        )
    except Exception as exc:  # noqa: BLE001
        print(json.dumps(_structured(
            DECISION_NOT_TRUSTED, status="error", failed_contract="fixtures_input",
            error_type=type(exc).__name__, message=str(exc)), indent=1))
        return 2

    cache_root = Path(args.cache_root)
    output_root = Path(args.output_root)
    # Write the synthetic dual-source objects into the cache as content-addressed
    # parquet so the role-based loader + v2 reconciliation are exercised.  The
    # fixture market rows carry only close; add the canonical loader columns.
    import pandas as pd

    def _loader_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [
            {
                "symbol": SYMBOL,
                "trade_date": r["trade_date"],
                "close": r["close"],
                "is_trading": True,
            }
            for r in rows
        ]

    primary_raw = _loader_rows(primary_rows)
    secondary_raw = _loader_rows(secondary_rows)
    primary_obj = f"baostock/{'0' * 64}.parquet"
    secondary_obj = f"r4e4/tencent_via_akshare/{'1' * 64}.parquet"
    p_path = cache_root / primary_obj
    s_path = cache_root / secondary_obj
    p_path.parent.mkdir(parents=True, exist_ok=True)
    s_path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(primary_raw).to_parquet(p_path)
    pd.DataFrame(secondary_raw).to_parquet(s_path)

    registry = {
        "contract": "market_data_snapshot_registry_v4",
        "symbol": SYMBOL,
        "integration_status": STATUS_PENDING_RECON,
        "reconciliation_status": STATUS_PENDING,
        "providers": [
            {
                "provider_id": "baostock_primary",
                "provider_role": "primary",
                "transport_library": "baostock",
                "underlying_provider": "baostock",
                "object_key": primary_obj,
                "sha256": _sha256_bytes(p_path.read_bytes()),
                "table_digest": spp.canonical_table_digest(primary_raw),
                "row_count": len(primary_raw),
                "first_trade_date": primary_raw[0]["trade_date"],
                "last_trade_date": primary_raw[-1]["trade_date"],
                "adjustment": "none",
            },
            {
                "provider_id": "tencent_via_akshare",
                "provider_role": "secondary",
                "transport_library": "akshare",
                "underlying_provider": "tencent",
                "endpoint_identity": "fixture.invalid",
                "object_key": secondary_obj,
                "sha256": _sha256_bytes(s_path.read_bytes()),
                "table_digest": spp.canonical_table_digest(secondary_raw),
                "row_count": len(secondary_raw),
                "first_trade_date": secondary_raw[0]["trade_date"],
                "last_trade_date": secondary_raw[-1]["trade_date"],
                "adjustment": "none",
            },
        ],
    }
    try:
        result = run_formal_reconciliation(registry=registry, cache_root=cache_root)
    except Exception as exc:  # noqa: BLE001
        print(json.dumps(_structured(
            DECISION_NOT_TRUSTED, status="error", failed_contract="fixtures_reconcile",
            error_type=type(exc).__name__, message=str(exc)), indent=1))
        return 2

    _write_json(output_root / RECONCILIATION_V2_NAME, result["report"])
    _write_json(output_root / LEDGER_V2_NAME, result["ledger"])
    decision_payload = {
        "schema": "m2_stage2k1r4e4_decision",
        "version": "2.0",
        "symbol": SYMBOL,
        "decision": "PIT_VALUATION_SERIES_CANDIDATE_TRUSTED_PERCENTILE_PREFLIGHT_ALLOWED",
        "mode": "fixtures",
        "evidence_class": "SYNTHETIC_ENGINEERING_ONLY",
        "reconciliation_status": mkt.STATUS_PASS,
        "reconciliation_digest": result["reconciliation_digest"],
        "percentile_computed": False,
        "score_eligible": False,
        "production_eligible": False,
    }
    _write_json(output_root / DECISION_V2_NAME, decision_payload)
    print(json.dumps({"status": "ok", "message": "fixtures synthetic run"}, indent=1))
    return 0


# ── parser ─────────────────────────────────────────────────────────────────


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    promote = sub.add_parser("promote", help="promote the R4E.3 selected object")
    promote.add_argument("--r4e3-cache-root", required=True)
    promote.add_argument("--formal-cache-root", required=True)
    promote.add_argument("--output-root", default=str(REPORTS))

    sub.add_parser("registry-draft", help="write the draft registry v4")

    reconcile = sub.add_parser("reconcile", help="real formal v2 reconciliation")
    reconcile.add_argument("--registry", default=str(ROOT / REGISTRY_V4_REL))
    reconcile.add_argument("--cache-root", required=True)
    reconcile.add_argument("--output-root", default=str(REPORTS))

    verify = sub.add_parser("verify", help="verify the registry v4 role contract")
    verify.add_argument("--registry", default=str(ROOT / REGISTRY_V4_REL))

    fixtures = sub.add_parser("fixtures", help="CI-only synthetic run")
    fixtures.add_argument("--fixture-root", required=True)
    fixtures.add_argument("--cache-root", required=True)
    fixtures.add_argument("--output-root", default=str(REPORTS))
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "promote":
        return _cmd_promote(args)
    if args.command == "registry-draft":
        return _cmd_registry_draft(args)
    if args.command == "reconcile":
        return _cmd_reconcile(args)
    if args.command == "verify":
        return _cmd_verify(args)
    if args.command == "fixtures":
        return _cmd_fixtures(args)
    return 2


if __name__ == "__main__":
    sys.exit(main())
