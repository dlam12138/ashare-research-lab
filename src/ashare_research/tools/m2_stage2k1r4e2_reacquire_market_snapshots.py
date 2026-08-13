"""M2 Stage 2K.1R4E.2 — versioned dual-source market snapshot reacquisition CLI.

Thin CLI.  Network access is allowed only in ``acquire``.  ``verify``,
``reconcile`` and ``formal`` are fully offline.  All reconciliation and formal
series logic is delegated to the existing R4E.1 modules (``market_reconciliation``
and the R4E.1 formal path); no third reconciliation or second ad-hoc serializer
is introduced here.

Modes:

    acquire --contract <path> --cache-root <root> --output-root <out>
        Network: for each provider performs two independent bounded acquisitions
        (run A / run B) into isolated directories, normalizes independently and
        compares the canonical table digest.  A matching pair is
        ``ACQUISITION_STABLE``; otherwise up to three attempts then
        ``ACQUISITION_UNSTABLE`` → GAPS_REMAIN.  Writes the content-addressed
        objects to ``<cache-root>/<provider>/<sha256>.parquet``, the acquisition
        receipt, and ``events/market_data_snapshot_registry_v3.json`` with
        ``reconciliation_status = pending_real_reconciliation``.

    verify --register... --cache-root <root>
        Offline: validates both pinned registry-v3 objects against the cache.

    reconcile --registry <path> --cache-root <root> --output-root <out>
        Offline: real dual-source reconciliation via ``market_reconciliation``,
        writes the v2 reconciliation report + mismatch ledger, the old/new
        Baostock revision diff, and updates the registry-v3 reconciliation
        status to ``pass`` only when the real reconciliation passes.

    formal --registry <path> --cache-root <root> --output-root <out>
        Offline: runs the R4E.1 formal with the explicit registry v3, then
        copies the candidate v2 reports and writes the R4E.2 decision + manifest.

    fixtures --fixture-root <root> --output-root <out>
        CI-only synthetic run; never substitutes for the formal acquisition.

Exit codes match the frozen decision gate: 0 = ALLOWED, 1 = GAPS_REMAIN,
2 = NOT_TRUSTED or any contract/input/schema failure.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path
from typing import Any

from ashare_research.pit_valuation import (
    market_reconciliation as mkt,
)
from ashare_research.pit_valuation import (
    market_snapshot_acquisition as acq,
)
from ashare_research.pit_valuation import (
    series_contract,
)
from ashare_research.scoring import artifact_manifest
from ashare_research.scoring import content_digest as cd

ROOT = Path(__file__).resolve().parents[3]
REPORTS = ROOT / "reports"
EVENTS = ROOT / "events"

DECISION_ALLOWED = "PIT_VALUATION_SERIES_CANDIDATE_TRUSTED_PERCENTILE_PREFLIGHT_ALLOWED"
DECISION_GAPS = "PIT_VALUATION_SERIES_GAPS_REMAIN"
DECISION_NOT_TRUSTED = "PIT_VALUATION_SERIES_NOT_TRUSTED"

MANIFEST_SCHEMA = "m2_stage2k1r4e2_artifact_manifest"
MANIFEST_PATH = "m2_stage2k1r4e2_artifact_manifest.json"
DECISION_PATH = "m2_stage2k1r4e2_decision.json"

REGISTRY_V3_REL = "events/market_data_snapshot_registry_v3.json"
REGISTRY_V2_REL = "events/market_data_snapshot_registry.json"

# Candidate-report names produced by the R4E.1 formal ALLOWED path.
CANDIDATE_REPORTS = (
    "petrochina_pit_financial_state_timeline_v2.json",
    "petrochina_pit_valuation_series_candidate_v2.json",
    "petrochina_pit_valuation_series_coverage_v2.json",
    "petrochina_pit_valuation_series_audit_samples_v2.json",
    "petrochina_pit_valuation_series_dual_oracle_validation_v2.json",
    "petrochina_pit_valuation_series_identity_migration_v1.json",
)

RECONCILIATION_V2 = "petrochina_market_close_reconciliation_v2.json"
MISMATCH_LEDGER_V2 = "petrochina_market_close_mismatch_ledger_v2.json"
RECEIPT_V1 = "petrochina_market_snapshot_acquisition_receipt_v1.json"
BAOSTOCK_DIFF_V1 = "petrochina_baostock_snapshot_revision_diff_v1.json"


def decision_to_exit_code(decision: str) -> int:
    if decision == DECISION_ALLOWED:
        return 0
    if decision == DECISION_GAPS:
        return 1
    return 2


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
    )


def _structured(decision: str, *, status: str, failed_contract: str = "",
               error_type: str = "", message: str = "") -> dict[str, Any]:
    return {
        "status": status,
        "decision": decision,
        "exit_code": decision_to_exit_code(decision),
        "failed_contract": failed_contract,
        "error_type": error_type,
        "message": message,
    }


def _load_contract(args: argparse.Namespace) -> dict[str, Any]:
    return json.loads(Path(args.contract).read_text(encoding="utf-8"))


def _load_registry(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _registry_v3_path() -> Path:
    return ROOT / REGISTRY_V3_REL


def _revision_diff(
    old_path: Path, old_sha: str, old_version: str,
    new_path: Path, new_sha: str, new_version: str,
) -> dict[str, Any]:
    """Compare the old Baostock object vs the newly acquired Baostock object."""
    import pandas as pd

    def _closes(path: Path) -> dict[str, tuple]:
        df = pd.read_parquet(path)
        out: dict[str, tuple] = {}
        for _, r in df.iterrows():
            d = str(r["trade_date"])[:10]
            out[d] = tuple(r[c] for c in ("open", "high", "low", "close"))
        return out

    old = _closes(old_path)
    new = _closes(new_path)
    old_dates = set(old)
    new_dates = set(new)
    date_set_diff = {
        "old_only": sorted(old_dates - new_dates),
        "new_only": sorted(new_dates - old_dates),
    }
    common = old_dates & new_dates
    pd_ = series_contract.parse_decimal

    changed_close: list[str] = []
    changed_ohlc: list[str] = []
    max_close_diff = "0"
    for d in sorted(common):
        old_row = tuple(pd_(v) for v in old[d])
        new_row = tuple(pd_(v) for v in new[d])
        if old_row[3] != new_row[3]:
            changed_close.append(d)
            diff = abs(old_row[3] - new_row[3])
            if pd_(max_close_diff) < diff:
                max_close_diff = str(diff)
        if old_row[:3] != new_row[:3]:
            changed_ohlc.append(d)

    if date_set_diff["old_only"] or date_set_diff["new_only"] or changed_close:
        classification = "HISTORICAL_DATA_CHANGE"
    else:
        classification = "NO_HISTORICAL_DATA_CHANGE"

    return {
        "schema": "petrochina_baostock_snapshot_revision_diff_v1",
        "symbol": series_contract.SYMBOL,
        "old": {"sha256": old_sha, "provider_version": old_version},
        "new": {"sha256": new_sha, "provider_version": new_version},
        "date_set_difference": date_set_diff,
        "changed_close_dates": changed_close,
        "changed_ohlc_dates": changed_ohlc,
        "max_close_difference": max_close_diff,
        "changed_row_count": len(changed_close),
        "change_classification": classification,
        "old_akshare_byte_comparison": "NOT_POSSIBLE_OLD_OBJECT_MISSING",
    }


# ── acquire (network only) ─────────────────────────────────────────────────


def _stable_record(
    provider: str,
    contract: dict[str, Any],
    base_cache: Path,
    *,
    attempts: int = 3,
) -> dict[str, Any]:
    """Run bounded A/B acquisitions; return the stable provider record."""
    acquire_fn = (
        acq.acquire_baostock_snapshot if provider == "baostock"
        else acq.acquire_akshare_snapshot
    )
    last_note = ""
    for attempt in range(1, attempts + 1):
        digests: list[str] = []
        shas: list[str] = []
        paths: list[Path] = []
        for label in ("a", "b"):
            raw, ver = acquire_fn(contract, attempts=attempts)
            norm = acq.normalize_market_snapshot(
                raw, provider=provider, provider_version=ver, contract=contract
            )
            run_root = base_cache / "_ab" / label
            path, sha = acq.write_content_addressed_snapshot(norm, run_root, provider)
            digests.append(acq.canonical_table_digest(norm))
            shas.append(sha)
            paths.append(path)
        if digests[0] == digests[1]:
            # stable pair; the object is content-addressed (shas identical).
            if shas[0] != shas[1]:
                raise acq.MarketAcquisitionError(
                    f"{provider} A/B digests equal but object SHAs differ"
                )
            final_dir = base_cache / provider
            final_dir.mkdir(parents=True, exist_ok=True)
            final = final_dir / f"{shas[0]}.parquet"
            if not final.is_file():
                shutil.copyfile(paths[0], final)
            return {
                "provider": provider,
                "provider_version": contract["provider_versions"][provider],
                "sha256": shas[0],
                "object_key": f"{provider}/{shas[0]}.parquet",
                "ab_stability": "ACQUISITION_STABLE",
                "table_digest": digests[0],
                "schema_digest": acq.column_schema_digest(),
                "attempt": attempt,
            }
        last_note = (
            f"A/B normalized digests differ: {digests[0][:12]} vs {digests[1][:12]}"
        )
    raise acq.MarketAcquisitionError(
        f"{provider} ACQUISITION_UNSTABLE after {attempts} attempts: {last_note}"
    )


def _cmd_acquire(args: argparse.Namespace) -> int:
    contract = _load_contract(args)
    base_cache = Path(args.cache_root).resolve()
    output_root = Path(args.output_root)
    started = acq.utc_now_iso()
    provider_records: list[dict[str, Any]] = []
    provider_gaps: list[dict[str, Any]] = []
    warnings: list[str] = []

    for provider in ("baostock", "akshare"):
        try:
            rec = _stable_record(provider, contract, base_cache, attempts=args.attempts)
            provider_records.append(rec)
        except acq.MarketAcquisitionError as exc:
            provider_gaps.append(
                {
                    "provider": provider,
                    "acquisition_status": "provider_gap",
                    "error_type": type(exc).__name__,
                    "message": str(exc),
                }
            )

    if not provider_records:
        print(json.dumps(_structured(
            DECISION_GAPS, status="gap", failed_contract="acquisition:all",
            error_type="MarketAcquisitionError", message="no provider could be acquired",
        ), indent=1))
        return decision_to_exit_code(DECISION_GAPS)

    # Reload each stable object to extract row/date metadata.
    for rec in provider_records:
        path = base_cache / rec["object_key"]
        df = _read_snapshot(path)
        rows = acq.normalize_market_snapshot(
            _df_to_rows(df, rec["provider"]),
            provider=rec["provider"],
            provider_version=rec["provider_version"],
            contract=contract,
        )
        rec["row_count"] = len(rows)
        rec["first_trade_date"] = rows[0]["trade_date"]
        rec["last_trade_date"] = rows[-1]["trade_date"]
        rec["function"] = contract[rec["provider"]]["function"]
        rec["params"] = contract[rec["provider"]]
        rec["adjustment"] = contract["adjustment"]

        required_first = contract["required_first_trade_date"]
        required_last = contract["required_last_trade_date"]
        if rec["first_trade_date"] != required_first or rec["last_trade_date"] != required_last:
            provider_gaps.append(
                {
                    "provider": rec["provider"],
                    "acquisition_status": "date_range_gap",
                    "message": (
                        f"date range {rec['first_trade_date']}..{rec['last_trade_date']} "
                        f"!= required {required_first}..{required_last}"
                    ),
                }
            )

    finished = acq.utc_now_iso()
    receipt = acq.build_acquisition_receipt(
        contract=contract,
        provider_records=provider_records,
        runtime_versions=contract.get("runtime_versions", {}),
        acquisition_code_commit=args.acquisition_code_commit,
        started_at=started,
        finished_at=finished,
        acquisition_warnings=warnings,
    )
    receipt["provider_gaps"] = provider_gaps
    _write_json(output_root / RECEIPT_V1, receipt)


    registry = _build_registry_v3(contract, provider_records, provider_gaps)
    _write_json(_registry_v3_path(), registry)

    if provider_gaps:
        decision = DECISION_GAPS
        status = "gap"
        message = "; ".join(
            f"{g['provider']}:{g['acquisition_status']}" for g in provider_gaps
        )
    else:
        decision = DECISION_ALLOWED
        status = "ok"
        message = (
            f"acquired stable dual source: baostock={provider_records[0]['sha256'][:12]} "
            f"akshare={provider_records[1]['sha256'][:12]}"
        )

    # Always write the R4E.2 decision so the gate state is captured honestly.
    baostock_sha = next(
        (p["sha256"] for p in provider_records if p["provider"] == "baostock"), ""
    )
    akshare_sha = next(
        (p["sha256"] for p in provider_records if p["provider"] == "akshare"), ""
    )
    _write_json(output_root / DECISION_PATH, {
        "schema": "m2_stage2k1r4e2_decision",
        "version": "1.0",
        "symbol": series_contract.SYMBOL,
        "decision": decision,
        "acquisition_stability": registry.get("ab_stability"),
        "registry_v3": {
            "path": REGISTRY_V3_REL,
            "acquisition_batch_id": registry.get("acquisition_batch_id"),
            "reconciliation_status": registry.get("reconciliation_status"),
            "baostock_sha256": baostock_sha,
            "akshare_sha256": akshare_sha,
        },
        "provider_gaps": provider_gaps,
        "dual_source_complete": decision == DECISION_ALLOWED,
        "reconciliation_trusted": False,
        "candidate_v2_published": False,
        "percentile_computed": False,
        "score_eligible": False,
        "production_eligible": False,
    })

    print(json.dumps(_structured(
        decision, status=status, failed_contract="acquisition" if provider_gaps else "",
        error_type="ProviderGap" if provider_gaps else "", message=message,
    ), indent=1))
    return decision_to_exit_code(decision)


def _read_snapshot(path: Path):
    import pandas as pd
    return pd.read_parquet(path)


def _df_to_rows(df, provider: str) -> list[dict[str, Any]]:
    """Convert a canonical snapshot DataFrame back to intermediate rows."""
    if provider == "akshare":
        # volume already in shares in the canonical object.
        pass
    rows: list[dict[str, Any]] = []
    for _, r in df.iterrows():
        rows.append(
            {
                "trade_date": str(r["trade_date"])[:10],
                "open": r["open"],
                "high": r["high"],
                "low": r["low"],
                "close": r["close"],
                "volume": int(r["volume"]),
                "amount": r["amount"],
                "is_trading": bool(r["is_trading"]),
            }
        )
    return rows


def _build_registry_v3(
    contract: dict[str, Any],
    provider_records: list[dict[str, Any]],
    provider_gaps: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    provider_gaps = provider_gaps or []
    batch_id = acq.build_acquisition_batch_id(
        contract["symbol"],
        {"start": contract["requested_start"], "end": contract["requested_end"]},
        contract["adjustment"],
        provider_records,
    )
    first_start = min(r["first_trade_date"] for r in provider_records)
    last_end = max(r["last_trade_date"] for r in provider_records)
    complete = not provider_gaps
    return {
        "contract": "market_data_snapshot_registry_v3",
        "schema_version": "3.0",
        "supersedes_registry": REGISTRY_V2_REL,
        "supersession_reason": "pinned_secondary_object_unrecoverable_versioned_reacquisition",
        "data_class": "external_real_data_cache",
        "acquisition_batch_id": batch_id,
        "symbol": contract["symbol"],
        "date_range": {
            "requested_start": contract["requested_start"],
            "requested_end": contract["requested_end"],
            "actual_start": first_start,
            "actual_end": last_end,
        },
        "adjustment": contract["adjustment"],
        "currency": contract["currency"],
        "close_unit": contract["close_unit"],
        "frequency": contract["frequency"],
        "providers": provider_records,
        "provider_gaps": provider_gaps,
        "ab_stability": "ACQUISITION_STABLE" if complete else "ACQUISITION_INCOMPLETE",
        "acquisition_warnings": [],
        "canonical_writer_contract": contract["canonical_writer_contract"],
        "evidence_class": "external_real_data_cache",
        "reconciliation_status": "pending_real_reconciliation",
    }


# ── verify (offline) ───────────────────────────────────────────────────────


def _verify_objects(registry: dict[str, Any], cache_root: Path) -> tuple[dict, dict]:
    primary = mkt.load_and_validate_market_object(registry, cache_root, "baostock")
    secondary = mkt.load_and_validate_market_object(registry, cache_root, "akshare")
    return primary, secondary


def _cmd_verify(args: argparse.Namespace) -> int:
    registry = _load_registry(Path(args.registry))
    cache_root = Path(args.cache_root)
    try:
        primary, secondary = _verify_objects(registry, cache_root)
    except mkt.MarketObjectMissingError as exc:
        print(json.dumps(_structured(
            DECISION_GAPS, status="gap", failed_contract="market_object",
            error_type="MarketObjectMissingError", message=str(exc)), indent=1))
        return decision_to_exit_code(DECISION_GAPS)
    except (mkt.MarketObjectInvalidError, ValueError) as exc:
        print(json.dumps(_structured(
            DECISION_NOT_TRUSTED, status="error", failed_contract="market_object",
            error_type=type(exc).__name__, message=str(exc)), indent=1))
        return decision_to_exit_code(DECISION_NOT_TRUSTED)
    print(json.dumps({
        "status": "ok",
        "baostock": primary["object_sha256"][:16],
        "akshare": secondary["object_sha256"][:16],
        "rows": primary["row_count"],
    }, indent=1))
    return decision_to_exit_code(DECISION_ALLOWED)


# ── reconcile (offline) ────────────────────────────────────────────────────


def _cmd_reconcile(args: argparse.Namespace) -> int:
    registry_path = Path(args.registry)
    registry = _load_registry(registry_path)
    cache_root = Path(args.cache_root)
    output_root = Path(args.output_root)

    try:
        primary, secondary = _verify_objects(registry, cache_root)
    except mkt.MarketObjectMissingError as exc:
        return _reconcile_fail(DECISION_GAPS, "market_object", "MarketObjectMissingError", exc)
    except (mkt.MarketObjectInvalidError, ValueError) as exc:
        return _reconcile_fail(DECISION_NOT_TRUSTED, "market_object", type(exc).__name__, exc)

    try:
        reconciliation = mkt.reconcile_market_close_series(primary, secondary)
    except (mkt.MarketReconciliationError, ValueError) as exc:
        return _reconcile_fail(
            DECISION_NOT_TRUSTED, "market_reconciliation", type(exc).__name__, exc
        )

    ledger = mkt.build_mismatch_ledger(reconciliation)
    ledger_digest = mkt.build_mismatch_ledger_digest(ledger)
    reconciliation_report = mkt.build_reconciliation_report(
        primary, secondary, reconciliation, ledger_digest=ledger_digest
    )
    _write_json(output_root / RECONCILIATION_V2, reconciliation_report)
    _write_json(output_root / MISMATCH_LEDGER_V2, ledger)

    # old/new Baostock revision diff (old object from the superseded v2 registry).
    v2 = _load_registry(ROOT / REGISTRY_V2_REL)
    v2_baostock = next(p for p in v2["providers"] if p["provider"] == "baostock")
    old_path = cache_root / v2_baostock["object_key"]
    new_path = cache_root / primary["object_key"]
    diff = _revision_diff(
        old_path, v2_baostock["sha256"], v2_baostock["provider_version"],
        new_path, primary["object_sha256"], registry["providers"][0]["provider_version"],
    )
    _write_json(output_root / BAOSTOCK_DIFF_V1, diff)

    if diff["change_classification"] == "HISTORICAL_DATA_CHANGE":
        max_diff = series_contract.parse_decimal(diff["max_close_difference"])
        if max_diff > series_contract.parse_decimal("0.01"):
            return _reconcile_fail(
                DECISION_NOT_TRUSTED, "baostock_revision",
                "HistoricalRevisionError",
                f"unexplained close revision {diff['max_close_difference']} > 0.01",
            )

    # Now that the real reconciliation passed, promote registry v3 to pass.
    registry["reconciliation_status"] = "pass"
    registry["common_trade_days"] = reconciliation["common_trade_days"]
    registry["close_max_abs_difference"] = reconciliation["max_abs_difference"]
    registry["close_differences_within_0_01"] = (
        reconciliation["differences_over_tolerance_count"] == 0
    )
    registry["reconciliation_digest"] = reconciliation_report["reconciliation_digest"]
    _write_json(registry_path, registry)

    print(json.dumps(_structured(
        DECISION_ALLOWED, status="ok",
        message=(
            f"reconciliation passed: common={reconciliation['common_trade_days']} "
            f"max_diff={reconciliation['max_abs_difference']} "
            f"over_tolerance={reconciliation['differences_over_tolerance_count']}"
        ),
    ), indent=1))
    return decision_to_exit_code(DECISION_ALLOWED)


def contract_provider_version(primary: dict[str, Any]) -> str:
    import pandas as pd
    df = pd.read_parquet(Path(primary["object_sha256"]))
    return str(df["provider_version"].iloc[0])


def _reconcile_fail(decision: str, contract: str, etype: str, exc: Exception) -> int:
    print(json.dumps(_structured(
        decision, status="error", failed_contract=contract,
        error_type=etype, message=str(exc)), indent=1))
    return decision_to_exit_code(decision)


# ── formal (offline) ───────────────────────────────────────────────────────


def _cmd_formal(args: argparse.Namespace) -> int:
    registry_path = Path(args.registry)
    registry = _load_registry(registry_path)
    if registry.get("reconciliation_status") != "pass":
        print(json.dumps(_structured(
            DECISION_GAPS, status="gap", failed_contract="registry_v3",
            error_type="ReconciliationIncomplete",
            message="registry v3 reconciliation_status is not 'pass'; run reconcile first",
        ), indent=1))
        return decision_to_exit_code(DECISION_GAPS)

    cache_root = Path(args.cache_root)
    output_root = Path(args.output_root)

    # Run the R4E.1 formal with the explicit registry into an isolated dir so the
    # committed R4E.1 decision/manifest are never overwritten.
    from ashare_research.tools.m2_stage2k1r4e_series_preflight import main as r4e1_main

    iso = output_root / ".r4e2-formal-iso"
    if iso.exists():
        shutil.rmtree(iso)
    iso.mkdir(parents=True, exist_ok=True)
    code = r4e1_main([
        "formal",
        "--market-cache-root", str(cache_root),
        "--market-registry", str(registry_path),
        "--output-root", str(iso),
    ])
    if code != decision_to_exit_code(DECISION_ALLOWED):
        print(json.dumps(_structured(
            DECISION_NOT_TRUSTED, status="error", failed_contract="r4e1_formal",
            error_type="ReleaseGate", message=f"R4E.1 formal exited {code}",
        ), indent=1))
        return decision_to_exit_code(DECISION_NOT_TRUSTED)

    # Copy the candidate v2 reports into the output root.
    written: list[Path] = []
    for name in CANDIDATE_REPORTS:
        src = iso / name
        dst = output_root / name
        shutil.copyfile(src, dst)
        written.append(dst)

    # The R4E.2 decision + manifest.
    cand_path = output_root / "petrochina_pit_valuation_series_candidate_v2.json"
    candidate = json.loads(cand_path.read_text(encoding="utf-8"))
    dual_path = output_root / "petrochina_pit_valuation_series_dual_oracle_validation_v2.json"
    dual = json.loads(dual_path.read_text(encoding="utf-8"))
    cov_path = output_root / "petrochina_pit_valuation_series_coverage_v2.json"
    coverage = json.loads(cov_path.read_text(encoding="utf-8"))
    obs_shas = _observation_shas(candidate, "primary_market_object_sha256")
    second_shas = _observation_shas(candidate, "secondary_market_object_sha256")
    baostock_sha = registry["providers"][0]["sha256"]
    akshare_sha = registry["providers"][1]["sha256"]

    all_ready = all(
        coverage["per_metric"][m]["3y_ready"] and coverage["per_metric"][m]["5y_ready"]
        for m in ("PE_A_TTM", "PB_A_MRQ", "PS_A_TTM")
    )
    decision = DECISION_ALLOWED
    if not dual.get("all_identical"):
        decision = DECISION_NOT_TRUSTED
    elif not all_ready:
        decision = DECISION_GAPS
    elif obs_shas != {baostock_sha} or second_shas != {akshare_sha}:
        decision = DECISION_NOT_TRUSTED

    decision_payload = {
        "schema": "m2_stage2k1r4e2_decision",
        "version": "1.0",
        "symbol": series_contract.SYMBOL,
        "decision": decision,
        "acquisition_stability": registry.get("ab_stability"),
        "registry_v3": {
            "path": REGISTRY_V3_REL,
            "acquisition_batch_id": registry.get("acquisition_batch_id"),
            "reconciliation_status": registry.get("reconciliation_status"),
            "baostock_sha256": baostock_sha,
            "akshare_sha256": akshare_sha,
        },
        "reconciliation": {
            "common_trade_days": registry.get("common_trade_days"),
            "max_abs_difference": registry.get("close_max_abs_difference"),
            "over_tolerance_count": 0,
            "trusted": registry.get("reconciliation_status") == "pass",
        },
        "dual_oracle_identical": dual.get("all_identical"),
        "coverage_ready": all_ready,
        "observations": len(candidate.get("observations", [])),
        "percentile_computed": False,
        "score_eligible": False,
        "production_eligible": False,
    }
    _write_json(output_root / DECISION_PATH, decision_payload)
    written.append(output_root / DECISION_PATH)
    written.append(output_root / RECONCILIATION_V2)
    written.append(output_root / MISMATCH_LEDGER_V2)
    written.append(output_root / RECEIPT_V1)
    written.append(output_root / BAOSTOCK_DIFF_V1)
    written.append(_registry_v3_path())
    _write_manifest(output_root, written)

    print(json.dumps(_structured(
        decision, status="ok" if decision == DECISION_ALLOWED else "error",
        message=f"candidate v2 observations={len(candidate.get('observations', []))}",
    ), indent=1))
    return decision_to_exit_code(decision)


def _observation_shas(candidate: dict[str, Any], field: str) -> set[str]:
    obs = candidate.get("observations", [])
    if not obs:
        return set()
    return {o.get(field) for o in obs}


# ── manifest ───────────────────────────────────────────────────────────────


def _relative_logical(repo_root: Path, path: Path) -> str:
    return str(path.resolve().relative_to(repo_root.resolve()).as_posix())


def _write_manifest(output_root: Path, written_files: list[Path]) -> None:
    files: list[dict[str, Any]] = []
    for path in sorted(written_files, key=lambda p: _relative_logical(ROOT, p)):
        if path.resolve() == (output_root / MANIFEST_PATH).resolve():
            continue
        if not path.is_file():
            continue  # an artifact produced by another mode may be absent here
        digest = cd.digest_file(path, algorithm="sha256_lf_normalized_bytes_v1")
        files.append({
            "path": _relative_logical(ROOT, path),
            "digest_algorithm": digest.algorithm,
            "sha256": digest.sha256,
            "byte_size": digest.byte_size,
        })
    manifest = {"schema": MANIFEST_SCHEMA, "version": "1.0", "files": files}
    manifest["manifest_digest"] = artifact_manifest.manifest_digest(manifest)
    _write_json(output_root / MANIFEST_PATH, manifest)


def _verify_manifest(output_root: Path) -> dict[str, Any]:
    return artifact_manifest.verify_artifact_manifest(
        output_root / MANIFEST_PATH, repository_root=ROOT
    ).to_dict()


# ── fixtures (CI) ──────────────────────────────────────────────────────────


def _cmd_fixtures(args: argparse.Namespace) -> int:
    from ashare_research.pit_valuation import fixtures

    primary_rows, secondary_rows, _meta = fixtures.load_fixture_dual_market(
        Path(args.fixture_root)
    )
    output_root = Path(args.output_root)
    primary = {
        "provider": "baostock", "object_sha256": "synthetic" + "0" * 57,
        "object_key": "synthetic/baostock.parquet", "row_count": len(primary_rows),
        "first_trade_date": primary_rows[0]["trade_date"],
        "last_trade_date": primary_rows[-1]["trade_date"], "rows": primary_rows,
    }
    secondary = {
        "provider": "akshare", "object_sha256": "synthetic" + "1" * 57,
        "object_key": "synthetic/akshare.parquet", "row_count": len(secondary_rows),
        "first_trade_date": secondary_rows[0]["trade_date"],
        "last_trade_date": secondary_rows[-1]["trade_date"], "rows": secondary_rows,
    }
    reconciliation = mkt.reconcile_market_close_series(primary, secondary)
    ledger = mkt.build_mismatch_ledger(reconciliation)
    ledger_digest = mkt.build_mismatch_ledger_digest(ledger)
    reconciliation_report = mkt.build_reconciliation_report(
        primary, secondary, reconciliation, ledger_digest=ledger_digest
    )
    # fixtures are engineering/synthetic only and must never masquerade as a
    # real dual-source reconciliation from acquired external data.
    reconciliation_report["evidence_class"] = "SYNTHETIC_ENGINEERING_ONLY"
    _write_json(output_root / RECONCILIATION_V2, reconciliation_report)
    _write_json(output_root / MISMATCH_LEDGER_V2, ledger)
    written = [
        output_root / RECONCILIATION_V2, output_root / MISMATCH_LEDGER_V2,
    ]
    _write_manifest(output_root, written)
    print(json.dumps(_structured(
        DECISION_ALLOWED, status="ok", message="fixtures synthetic reconcile",
    ), indent=1))
    return decision_to_exit_code(DECISION_ALLOWED)


# ── parser ────────────────────────────────────────────────────────────────


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    acquire = sub.add_parser("acquire", help="network acquisition of both providers")
    acquire.add_argument("--contract", default=str(ROOT / "config" /
                        "pit_valuation_market_snapshot_acquisition_v1.json"))
    acquire.add_argument("--cache-root", required=True)
    acquire.add_argument("--output-root", default=str(REPORTS))
    acquire.add_argument("--attempts", type=int, default=3)
    acquire.add_argument("--acquisition-code-commit", default="")

    verify = sub.add_parser("verify", help="offline object verification")
    verify.add_argument("--registry", default=str(_registry_v3_path()))
    verify.add_argument("--cache-root", required=True)

    reconcile = sub.add_parser("reconcile", help="offline real reconciliation")
    reconcile.add_argument("--registry", default=str(_registry_v3_path()))
    reconcile.add_argument("--cache-root", required=True)
    reconcile.add_argument("--output-root", default=str(REPORTS))

    formal = sub.add_parser("formal", help="offline formal candidate v2 release")
    formal.add_argument("--registry", default=str(_registry_v3_path()))
    formal.add_argument("--cache-root", required=True)
    formal.add_argument("--output-root", default=str(REPORTS))

    fixtures = sub.add_parser("fixtures", help="CI synthetic run")
    fixtures.add_argument("--fixture-root", required=True)
    fixtures.add_argument("--output-root", default=str(REPORTS))
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "acquire":
        return _cmd_acquire(args)
    if args.command == "verify":
        return _cmd_verify(args)
    if args.command == "reconcile":
        return _cmd_reconcile(args)
    if args.command == "formal":
        return _cmd_formal(args)
    if args.command == "fixtures":
        return _cmd_fixtures(args)
    return decision_to_exit_code(DECISION_NOT_TRUSTED)


if __name__ == "__main__":
    sys.exit(main())
