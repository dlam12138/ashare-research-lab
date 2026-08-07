"""M2 Stage 2K.1R4E.3 — alternative secondary market provider preflight CLI.

Thin CLI.  Network access is allowed only in ``probe`` and ``acquire``.
``verify-contracts``, ``compare`` and ``fixtures`` are fully offline.  All
contract/normalization/comparison/classification/decision logic is delegated to
the ``secondary_provider_preflight`` module; no ad-hoc serializer is introduced
here.

Modes:

    verify-contracts [--config <path>]
        Offline: validate the frozen candidate list, params, window and decision
        enum.

    probe --cache-root <root> --output-root <out> [--config <path>]
        Network: one minimal reachability test per source.  No formal object is
        written.  Writes ``petrochina_secondary_provider_probe_v1.json``.

    acquire --cache-root <root> --output-root <out> [--config <path>]
        Network: for each reachable candidate performs two independent bounded
        acquisitions (run A / run B) into isolated directories, normalizes
        independently and compares the canonical table digest.  Writes the
        content-addressed objects to the external cache (never committed) and
        updates the probe report with the A/B stability.

    compare --cache-root <root> --output-root <out> [--config <path>]
        Offline: compare each reachable candidate against the pinned Baostock
        primary ``c6771aa5…``, run the company-action adjustment check, classify
        each candidate, apply the deterministic selection rule and the decision
        gate, and write the comparison matrix, mismatch ledger, decision and
        manifest.

    fixtures --fixture-root <root> --output-root <out>
        CI-only synthetic run (``evidence_class = SYNTHETIC_ENGINEERING_ONLY``);
        never substitutes for a real provider selection.

Exit codes match the frozen decision gate: 0 = INTEGRATION_ALLOWED,
1 = GAPS_REMAIN / NO_ACCEPTABLE, 2 = NOT_TRUSTED or any contract/input/schema
failure.
"""

from __future__ import annotations

import argparse
import contextlib
import json
import sys
from pathlib import Path
from typing import Any

from ashare_research.pit_valuation import secondary_provider_preflight as spp
from ashare_research.pit_valuation import series_contract
from ashare_research.scoring import artifact_manifest
from ashare_research.scoring import content_digest as cd

ROOT = Path(__file__).resolve().parents[3]
REPORTS = ROOT / "reports"
CONFIG = ROOT / "config" / "pit_valuation_secondary_provider_preflight_v1.json"

# Pinned Baostock primary (registry v3), the baseline for every comparison.
PRIMARY_BAOSTOCK_SHA = "c6771aa57b0210ee558a91c7bdb87cc346ce910a395eda057cb9d7224475ab67"
PRIMARY_OBJECT_REL = (
    "tmp/market_cache/baostock/"
    "c6771aa57b0210ee558a91c7bdb87cc346ce910a395eda057cb9d7224475ab67.parquet"
)

MANIFEST_SCHEMA = "m2_stage2k1r4e3_artifact_manifest"
MANIFEST_PATH = "m2_stage2k1r4e3_artifact_manifest.json"
DECISION_PATH = "m2_stage2k1r4e3_decision.json"
PROBE_REPORT = "petrochina_secondary_provider_probe_v1.json"
COMPARISON_MATRIX = "petrochina_secondary_provider_comparison_matrix_v1.json"
MISMATCH_LEDGER = "petrochina_secondary_provider_mismatch_ledger_v1.json"

DIVIDEND_EVENTS = ROOT / "events" / "dividend_events_2021_2026_v2.json"

OUTPUT_REPORTS = (
    PROBE_REPORT,
    COMPARISON_MATRIX,
    MISMATCH_LEDGER,
    DECISION_PATH,
    MANIFEST_PATH,
)


def decision_to_exit_code(decision: str) -> int:
    return spp.decision_to_exit_code(decision)


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


def _load_config(path: str | None) -> dict[str, Any]:
    return json.loads(Path(path or CONFIG).read_text(encoding="utf-8"))


def _candidate(cnf: dict[str, Any], cid: str) -> dict[str, Any]:
    return next(c for c in cnf["candidates"] if c["candidate_id"] == cid)


def _registered_endpoint(candidate: dict[str, Any]) -> str:
    return candidate.get("endpoints", [""])[0]


# ── acquisition (network only) ─────────────────────────────────────────────


def _acquire_akshare_candidate(
    candidate: dict[str, Any], *, attempts: int = 3
) -> tuple[list[dict[str, Any]], str]:
    """Fetch one AKShare-backed candidate over the frozen window.

    Network only.  Bounded retries; a failed interface call is a provider gap.
    """
    import akshare as ak

    fn = getattr(ak, candidate["function"])
    kwargs = {
        "symbol": candidate["symbol"],
        "start_date": candidate["start_date"],
        "end_date": candidate["end_date"],
    }
    if "adjust" in candidate:
        kwargs["adjust"] = candidate["adjust"]
    last_error = ""
    for attempt in range(1, attempts + 1):
        try:
            df = fn(**kwargs)
            if df is None or df.empty:
                raise spp.PreflightAcquisitionError("candidate returned no rows")
            return spp.raw_rows_for_candidate(candidate, df)
        except Exception as exc:  # noqa: BLE001 - any failure is a bounded retry
            last_error = f"{type(exc).__name__}: {exc}"
            if attempt < attempts:
                import time

                time.sleep(1.5 * attempt)
    raise spp.PreflightAcquisitionError(
        f"{candidate['candidate_id']} acquisition failed after {attempts} attempts: {last_error}"
    )


def _acquire_candidate(
    candidate: dict[str, Any], *, attempts: int = 3
) -> tuple[list[dict[str, Any]], str, str]:
    """Route a candidate to its transport acquisition. Returns (rows, version, endpoint)."""
    cid = candidate["candidate_id"]
    if cid in ("tencent_via_akshare", "sina_via_akshare"):
        rows = _acquire_akshare_candidate(candidate, attempts=attempts)
        return rows, "akshare", _registered_endpoint(candidate)
    if cid == "pytdx_tongdaxin":
        return _acquire_pytdx_candidate(candidate, attempts=attempts)
    raise spp.PreflightAcquisitionError(
        f"{cid} transport not wired for acquisition"
    )


# Known TongdaXin quote servers (public, auditable). The single-run pinning
# contract holds: one server per complete A/B run, recorded in the endpoint
# identity; a failed server is never silently switched mid-run.
PYTDX_SERVERS = (
    ("119.147.212.81", 7709),
    ("180.153.39.51", 7709),
    ("114.80.63.12", 7709),
    ("124.160.88.183", 7709),
)


def _acquire_pytdx_candidate(
    candidate: dict[str, Any], *, attempts: int = 3
) -> tuple[list[dict[str, Any]], str, str]:
    """Fetch TongdaXin daily K bars for ``sh601857`` via pytdx with explicit paging.

    Network only.  A complete run pins a single server (recorded in the returned
    endpoint identity); pagination is validated for overlap/gap/ordering.  Servers
    that are unreachable are a provider block (fail-closed), never silently
    mixed into a partial object.  When the pytdx package is absent the candidate
    is ``optional_dependency_not_available`` (→ BLOCKED), not a total-preflight
    failure.
    """
    try:
        from pytdx.hq import TdxHq_API
    except ModuleNotFoundError as exc:
        raise spp.PreflightAcquisitionError(
            "pytdx_tongdaxin optional_dependency_not_available; "
            "pytdx is not installed in this environment"
        ) from exc

    last_error = ""
    for attempt in range(1, attempts + 1):
        for host, port in PYTDX_SERVERS:
            api = TdxHq_API()
            try:
                if not api.connect(host, port):
                    continue
                # Fetch daily bars in bounded pages (category 9 = daily, market 1 = SH).
                pages: list[list[dict[str, Any]]] = []
                start = 0
                page_size = 800
                while True:
                    bars = api.get_security_bars(9, 1, "601857", start, page_size)
                    if not bars:
                        break
                    pages.append(
                        [
                            {
                                "trade_date": _pytdx_date(b["datetime"]),
                                "open": b["open"], "high": b["high"],
                                "low": b["low"], "close": b["close"],
                                "volume": int(b["vol"]), "amount": b["amount"],
                                "is_trading": True,
                            }
                            for b in bars
                        ]
                    )
                    if len(bars) < page_size:
                        break
                    start += page_size
                # Validate pagination structure (overlap/gap/ordering).
                spp.validate_pytdx_pages(pages, expected_dates=None)
                rows: list[dict[str, Any]] = []
                for page in pages:
                    rows.extend(page)
                if not rows:
                    raise spp.PreflightAcquisitionError("pytdx returned no rows")
                return rows, "pytdx", f"{host}:{port}"
            except Exception as exc:  # noqa: BLE001 - any failure is a bounded retry
                last_error = f"{type(exc).__name__}: {exc}"
            finally:
                with contextlib.suppress(Exception):  # disconnect must not mask
                    api.disconnect()
        if attempt < attempts:
            import time

            time.sleep(1.5 * attempt)
    raise spp.PreflightAcquisitionError(
        f"pytdx_tongdaxin acquisition failed after {attempts} attempts: {last_error}"
    )


def _pytdx_date(value: Any) -> str:
    """Convert a pytdx datetime ``YYYY-MM-DD ...`` to an ISO date."""
    s = str(value)
    return s[:10]


def _pytdx_runtime_version() -> str | None:
    """Optional transport runtime version; ``None`` when pytdx is not installed.

    pytdx is a **non-core** dependency: a clean clone without it must still
    import and run the Tencent/Sina paths.  The import is delayed so the module
    never fails to load when pytdx is absent.
    """
    try:
        from importlib import metadata as md

        return md.version("pytdx")
    except Exception:  # noqa: BLE001 - absent package or broken metadata
        return None


def pytdx_core_dependency() -> bool:
    """Whether pytdx is a core dependency of the preflight (always False)."""
    return False


def _akshare_runtime_version() -> str:
    """Runtime akshare package version for provider-independence evidence."""
    try:
        from importlib import metadata as md

        return md.version("akshare")
    except Exception:  # noqa: BLE001 - metadata unavailable
        return "unknown"


def _probe_candidate(
    candidate: dict[str, Any], *, attempts: int = 1
) -> dict[str, Any]:
    """One minimal reachability test; never writes a formal object."""
    cid = candidate["candidate_id"]
    if cid == "tushare_pro_optional":
        # No token is present in this environment -> credential_not_available
        # (not a failure, per the frozen contract).
        return {
            "candidate_id": cid,
            "transport_library": "tushare",
            "underlying_provider": "tushare_pro",
            "reachable": False,
            "credential_not_available": True,
            "not_a_failure": True,
            "status": "credential_not_available",
            "message": "no tushare token present; candidate not evaluated",
        }
    if cid == "pytdx_tongdaxin" and _pytdx_runtime_version() is None:
        return {
            "candidate_id": cid,
            "transport_library": "pytdx",
            "underlying_provider": "tongdaxin_quote_server",
            "reachable": False,
            "dependency_not_available": True,
            "status": "dependency_not_available",
            "reason": "optional_dependency_not_available",
            "message": "pytdx is not installed; optional dependency not available",
        }
    try:
        rows, _version, endpoint = _acquire_candidate(candidate, attempts=attempts)
        return {
            "candidate_id": cid,
            "transport_library": candidate["transport_library"],
            "underlying_provider": candidate["underlying_provider"],
            "reachable": True,
            "rows_returned": len(rows),
            "endpoint_identity": endpoint,
            "status": "reachable",
        }
    except Exception as exc:  # noqa: BLE001 - any failure is a provider block
        return {
            "candidate_id": cid,
            "transport_library": candidate["transport_library"],
            "underlying_provider": candidate["underlying_provider"],
            "reachable": False,
            "status": "blocked",
            "error_type": type(exc).__name__,
            "message": str(exc),
        }


# ── content-addressed write ────────────────────────────────────────────────


def _write_candidate_object(
    rows: list[dict[str, Any]], cache_root: Path, cid: str
) -> tuple[Path, str]:
    import pandas as pd

    if not rows:
        raise spp.PreflightComparisonError(f"{cid} has no rows to write")
    df = pd.DataFrame(rows, columns=list(spp.CANONICAL_COLUMNS))
    df = df.reset_index(drop=True)
    root = Path(cache_root).resolve() / "r4e3" / cid
    root.mkdir(parents=True, exist_ok=True)
    tmp = root / f".tmp-{__import__('uuid').uuid4().hex}.parquet"
    import hashlib

    try:
        df.to_parquet(tmp, index=False, engine="pyarrow")
        data = tmp.read_bytes()
        sha = hashlib.sha256(data).hexdigest()
        final = root / f"{sha}.parquet"
        if not final.is_file():
            tmp.replace(final)
        else:
            tmp.unlink()
    except Exception:
        if tmp.exists():
            tmp.unlink()
        raise
    return final, sha


def _read_candidate_object(obj_key: str, cache_root: Path, cid: str) -> list[dict[str, Any]]:
    import pandas as pd

    df = pd.read_parquet(Path(cache_root) / "r4e3" / cid / obj_key)
    rows: list[dict[str, Any]] = []
    for _, r in df.iterrows():
        rows.append(
            {
                "symbol": str(r["symbol"]),
                "trade_date": str(r["trade_date"])[:10],
                "open": str(r["open"]),
                "high": str(r["high"]),
                "low": str(r["low"]),
                "close": str(r["close"]),
                "volume": int(r["volume"]),
                "amount": str(r["amount"]),
                "is_trading": bool(r["is_trading"]),
                "adjustment": str(r["adjustment"]),
                "transport_library": str(r["transport_library"]),
                "underlying_provider": str(r["underlying_provider"]),
                "provider_version": str(r["provider_version"]),
                "endpoint_identity": str(r["endpoint_identity"]),
            }
        )
    return rows


# ── verify-contracts (offline) ─────────────────────────────────────────────


def _cmd_verify_contracts(args: argparse.Namespace) -> int:
    try:
        cnf = _load_config(args.config)
        digests = spp.validate_preflight_contract(cnf)
    except Exception as exc:  # noqa: BLE001
        print(json.dumps(_structured(
            spp.DECISION_NOT_TRUSTED, status="error", failed_contract="preflight_contract",
            error_type=type(exc).__name__, message=str(exc)), indent=1))
        return decision_to_exit_code(spp.DECISION_NOT_TRUSTED)
    print(json.dumps({"status": "ok", "digests": digests}, indent=1))
    return decision_to_exit_code(spp.DECISION_ALLOWED)


# ── probe (network only) ───────────────────────────────────────────────────


def _cmd_probe(args: argparse.Namespace) -> int:
    cnf = _load_config(args.config)
    output_root = Path(args.output_root)
    results = []
    for c in cnf["candidates"]:
        results.append(_probe_candidate(c, attempts=1))
    report = {
        "schema": "petrochina_secondary_provider_probe_v1",
        "version": "1.0",
        "symbol": series_contract.SYMBOL,
        "window": cnf["window"],
        "pytdx_probe_runtime_version": _pytdx_runtime_version(),
        "pytdx_core_dependency": pytdx_core_dependency(),
        "candidates": results,
    }
    _write_json(output_root / PROBE_REPORT, report)
    print(json.dumps({"status": "ok", "probe": results}, indent=1))
    return 0


# ── acquire (network only) ─────────────────────────────────────────────────


def _cmd_acquire(args: argparse.Namespace) -> int:
    cnf = _load_config(args.config)
    cache_root = Path(args.cache_root)
    output_root = Path(args.output_root)
    acquisition_records: list[dict[str, Any]] = []
    for c in cnf["candidates"]:
        cid = c["candidate_id"]
        if cid == "tushare_pro_optional":
            acquisition_records.append(
                {
                    "candidate_id": cid,
                    "status": "credential_not_available",
                    "not_a_failure": True,
                }
            )
            continue
        try:
            # Bounded A/B pair.
            digests: list[str] = []
            shas: list[str] = []
            obj_keys: list[str] = []
            for _label in ("a", "b"):
                rows, version, endpoint = _acquire_candidate(c, attempts=args.attempts)
                spp.check_independence(c, endpoint)
                norm = spp.normalize_candidate_rows(
                    rows, candidate=c, contract=cnf,
                    provider_version=version, endpoint_identity=endpoint,
                )
                path, sha = _write_candidate_object(norm, cache_root, cid)
                digests.append(spp.canonical_table_digest(norm))
                shas.append(sha)
                obj_keys.append(path.name)
            ab = spp.ab_stability(
                _read_candidate_object(obj_keys[0], cache_root, cid),
                _read_candidate_object(obj_keys[1], cache_root, cid),
            )
            acquisition_records.append(
                {
                    "candidate_id": cid,
                    "transport_library": c["transport_library"],
                    "underlying_provider": c["underlying_provider"],
                    "endpoint_identity": _registered_endpoint(c),
                    "independent": True,
                    "status": ab["status"],
                    "stable": ab["stable"],
                    "row_count_a": ab["row_count_a"],
                    "row_count_b": ab["row_count_b"],
                    "table_digest": ab["table_digest_a"],
                    "object_sha256": shas[0],
                    "object_key": f"{cid}/{obj_keys[0]}",
                    "attempt": args.attempts,
                }
            )
        except spp.PreflightIndependenceError as exc:
            acquisition_records.append(
                {
                    "candidate_id": cid,
                    "status": "rejected_not_independent",
                    "error_type": "PreflightIndependenceError",
                    "message": str(exc),
                }
            )
        except Exception as exc:  # noqa: BLE001
            acquisition_records.append(
                {
                    "candidate_id": cid,
                    "status": spp.BLOCKED_PROVIDER_ACCESS,
                    "error_type": type(exc).__name__,
                    "message": str(exc),
                }
            )

    # Update the probe report with acquisition results.
    probe_path = output_root / PROBE_REPORT
    if probe_path.is_file():
        probe = json.loads(probe_path.read_text(encoding="utf-8"))
    else:
        probe = {
            "schema": "petrochina_secondary_provider_probe_v1",
            "symbol": series_contract.SYMBOL,
            "window": cnf["window"],
            "candidates": [],
        }
    probe["acquisition"] = acquisition_records
    _write_json(probe_path, probe)
    print(json.dumps({"status": "ok", "acquisition": acquisition_records}, indent=1))
    return 0


# ── baostock primary + event windows (offline) ─────────────────────────────


def _load_primary_rows() -> list[dict[str, Any]]:
    import pandas as pd

    path = ROOT / PRIMARY_OBJECT_REL
    df = pd.read_parquet(path)
    rows: list[dict[str, Any]] = []
    for _, r in df.iterrows():
        rows.append(
            {
                "trade_date": str(r["trade_date"])[:10],
                "open": str(r["open"]),
                "high": str(r["high"]),
                "low": str(r["low"]),
                "close": str(r["close"]),
                "is_trading": bool(r["is_trading"]),
            }
        )
    return rows


def _event_windows(primary_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Build 3 ex-dividend windows + 1 non-event window from the dividend events."""
    import json as _json

    ev = _json.loads(DIVIDEND_EVENTS.read_text(encoding="utf-8"))
    anchors = [e["payment_date"] for e in ev["events"] if e.get("payment_date")]
    trade_dates = [r["trade_date"] for r in primary_rows]

    def _nearest_after(anchor: str) -> str:
        for d in trade_dates:
            if d >= anchor:
                return d
        return trade_dates[-1]

    def _window(anchor: str, wtype: str) -> dict[str, Any]:
        center = _nearest_after(anchor)
        idx = trade_dates.index(center)
        before = trade_dates[max(0, idx - 2):idx]
        after = trade_dates[idx + 1:idx + 3]
        return {
            "trade_date": center,
            "type": wtype,
            "before": before,
            "after": after,
        }

    windows = [_window(a, "ex_dividend") for a in anchors[:3]]
    # A non-event control window (mid-year 2024, no concentrated dividend).
    control = _window("2024-01-15", "control_non_event")
    windows.append(control)
    return windows


# ── compare (offline) ──────────────────────────────────────────────────────


def _cmd_compare(args: argparse.Namespace) -> int:
    cnf = _load_config(args.config)
    cache_root = Path(args.cache_root)
    output_root = Path(args.output_root)

    probe_path = output_root / PROBE_REPORT
    if not probe_path.is_file():
        print(json.dumps(_structured(
            spp.DECISION_NOT_TRUSTED, status="error", failed_contract="probe_report",
            error_type="ProbeMissing", message="run probe/acquire first"), indent=1))
        return decision_to_exit_code(spp.DECISION_NOT_TRUSTED)
    probe = json.loads(probe_path.read_text(encoding="utf-8"))
    acq_by_id = {r["candidate_id"]: r for r in probe.get("acquisition", [])}

    primary_rows = _load_primary_rows()
    windows = _event_windows(primary_rows)
    results: list[dict[str, Any]] = []
    all_ledgers: list[dict[str, Any]] = []

    for c in cnf["candidates"]:
        cid = c["candidate_id"]
        acq = acq_by_id.get(cid)
        if acq is None or acq.get("status") != "ACQUISITION_STABLE":
            reason = (
                str(acq.get("message", acq.get("status", "blocked")))
                if acq else "not_acquired"
            )
            results.append(
                {
                    "candidate_id": cid,
                    "classification": spp.BLOCKED,
                    "independent": False,
                    "comparison": None,
                    "adjustment": None,
                    "limitations": [reason],
                }
            )
            continue
        cand_rows = _read_candidate_object(acq["object_key"].split("/")[1], cache_root, cid)
        comparison = spp.compare_to_baostock(cand_rows, primary_rows)
        adjustment = spp.check_adjustment_semantics(cand_rows, primary_rows, windows)
        classification, detail = spp.classify_candidate(
            candidate_id=cid,
            independent=True,
            credential_available=True,
            acquisition=acq,
            comparison=comparison,
            adjustment=adjustment,
            limitations=[],
        )
        first_trade_date = min(r["trade_date"] for r in cand_rows)
        last_trade_date = max(r["trade_date"] for r in cand_rows)
        row_count = len(cand_rows)
        provider_version = cand_rows[0].get("provider_version") if cand_rows else None
        endpoint_host = acq.get("endpoint_identity")
        underlying = acq.get("underlying_provider")
        detail.update(
            {
                "object_sha256": acq.get("object_sha256"),
                "table_digest": acq.get("table_digest"),
                "transport_library": acq.get("transport_library"),
                "underlying_provider": underlying,
                "endpoint_identity": endpoint_host,
                "row_count": row_count,
                "first_trade_date": first_trade_date,
                "last_trade_date": last_trade_date,
                "provider_version": provider_version,
                "comparison_digest": comparison.get("comparison_digest"),
                "mismatch_ledger_digest": comparison.get("mismatch_ledger_digest"),
                "independence_evidence": {
                    "transport_library": acq.get("transport_library"),
                    "underlying_provider": underlying,
                    "endpoint_host": endpoint_host,
                    "function_name": c.get("function"),
                    "request_parameters": {
                        "symbol": c.get("symbol"),
                        "start_date": c.get("start_date"),
                        "end_date": c.get("end_date"),
                        "adjust": c.get("adjust"),
                    },
                    "provider_version": _akshare_runtime_version(),
                    "endpoint_host_not_push2his_eastmoney_com": (
                        endpoint_host != "push2his.eastmoney.com"
                    ),
                    "underlying_provider_not_eastmoney": underlying != "eastmoney",
                },
            }
        )
        results.append(detail)
        all_ledgers.append(
            {
                "candidate_id": cid,
                "tolerance": comparison["tolerance"],
                "entry_count": comparison["over_tolerance_count"],
                "mismatch_ledger_digest": comparison["mismatch_ledger_digest"],
                "primary_only_dates": comparison["primary_only_dates"],
                "candidate_only_dates": comparison["candidate_only_dates"],
            }
        )

    selection = spp.select_provider(results)
    decision = spp.decide(results, contract_trusted=True)

    detail_by_id = {r["candidate_id"]: r for r in results}
    sel = selection.get("selected_provider")
    sel_detail = detail_by_id.get(sel) if sel else None

    mismatch_ledger = {
        "schema": "petrochina_secondary_provider_mismatch_ledger_v1",
        "symbol": series_contract.SYMBOL,
        "tolerance": "0.01",
        "candidates": all_ledgers,
    }
    comparison_matrix = {
        "schema": "petrochina_secondary_provider_comparison_matrix_v1",
        "symbol": series_contract.SYMBOL,
        "primary_provider": "baostock",
        "primary_object_sha256": PRIMARY_BAOSTOCK_SHA,
        "tolerance": "0.01",
        "event_windows": windows,
        "matrix": [
            {
                "candidate_id": r["candidate_id"],
                "classification": r["classification"],
                "comparison": r.get("comparison"),
                "adjustment": r.get("adjustment"),
                "limitations": r.get("limitations", []),
                "object_sha256": r.get("object_sha256"),
                "table_digest": r.get("table_digest"),
                "independence_evidence": r.get("independence_evidence"),
            }
            for r in results
        ],
    }

    _write_json(output_root / COMPARISON_MATRIX, comparison_matrix)
    _write_json(output_root / MISMATCH_LEDGER, mismatch_ledger)

    decision_payload = {
        "schema": "m2_stage2k1r4e3_decision",
        "version": "1.0",
        "symbol": series_contract.SYMBOL,
        "decision": decision["decision"],
        "reason": decision.get("reason"),
        "selected_provider": selection.get("selected_provider"),
        "selected_transport": selection.get("selected_transport"),
        "selected_underlying_provider": selection.get("selected_underlying_provider"),
        "selected_provider_dependency": (
            sel_detail.get("transport_library") if sel_detail else None
        ),
        "selected_object_sha256": selection.get("selected_object_sha"),
        "selected_table_digest": selection.get("selected_table_digest"),
        "selected_endpoint_identity": selection.get("selected_endpoint_identity"),
        "selected_row_count": sel_detail.get("row_count") if sel_detail else None,
        "selected_first_trade_date": (
            sel_detail.get("first_trade_date") if sel_detail else None
        ),
        "selected_last_trade_date": (
            sel_detail.get("last_trade_date") if sel_detail else None
        ),
        "selected_comparison_digest": (
            sel_detail.get("comparison_digest") if sel_detail else None
        ),
        "selected_mismatch_ledger_digest": (
            sel_detail.get("mismatch_ledger_digest") if sel_detail else None
        ),
        "pytdx_probe_runtime_version": _pytdx_runtime_version(),
        "pytdx_core_dependency": pytdx_core_dependency(),
        "limitations": selection.get("limitations", []),
        "candidates": [
            {
                "candidate_id": r["candidate_id"],
                "classification": r["classification"],
            }
            for r in results
        ],
        "registry_v3_unchanged": True,
        "candidate_v2_published": False,
        "percentile_computed": False,
        "scoring_unchanged": True,
        "default_db_unchanged": True,
        "peer_acquisition": "NOT_ALLOWED",
        "m3_started": False,
    }
    _write_json(output_root / DECISION_PATH, decision_payload)

    written = [
        output_root / COMPARISON_MATRIX,
        output_root / MISMATCH_LEDGER,
        output_root / DECISION_PATH,
        output_root / PROBE_REPORT,
    ]
    _write_manifest(output_root, written)

    print(json.dumps(_structured(
        decision["decision"],
        status="ok" if decision["decision"] == spp.DECISION_ALLOWED else "info",
        message=(
            f"selected={selection.get('selected_provider')} "
            f"classifications={ {r['candidate_id']: r['classification'] for r in results} }"
        ),
    ), indent=1))
    return decision_to_exit_code(decision["decision"])


# ── manifest ───────────────────────────────────────────────────────────────


def _relative_logical(repo_root: Path, path: Path) -> str:
    return str(path.resolve().relative_to(repo_root.resolve()).as_posix())


def _write_manifest(output_root: Path, written_files: list[Path]) -> None:
    files: list[dict[str, Any]] = []
    for path in sorted(written_files, key=lambda p: _relative_logical(ROOT, p)):
        if path.resolve() == (output_root / MANIFEST_PATH).resolve():
            continue
        if not path.is_file():
            continue
        digest = cd.digest_file(path, algorithm="sha256_lf_normalized_bytes_v1")
        files.append(
            {
                "path": _relative_logical(ROOT, path),
                "digest_algorithm": digest.algorithm,
                "sha256": digest.sha256,
                "byte_size": digest.byte_size,
            }
        )
    manifest = {"schema": MANIFEST_SCHEMA, "version": "1.0", "files": files}
    manifest["manifest_digest"] = artifact_manifest.manifest_digest(manifest)
    _write_json(output_root / MANIFEST_PATH, manifest)


# ── fixtures (CI) ──────────────────────────────────────────────────────────


def _cmd_fixtures(args: argparse.Namespace) -> int:
    from datetime import date, timedelta

    output_root = Path(args.output_root)
    # Build a synthetic 1351-row candidate that fully matches itself (offset 0),
    # so the classification/decision logic is exercised end-to-end on CI.
    dates: list[str] = []
    d = date(2021, 1, 4)
    while len(dates) < 1351:
        if d.weekday() < 5:
            dates.append(d.isoformat())
        d += timedelta(days=1)
    close = 5.0
    cand_rows: list[dict[str, Any]] = []
    for td in dates:
        close += 0.01
        cand_rows.append(
            {
                "symbol": series_contract.SYMBOL,
                "trade_date": td,
                "open": "5.00", "high": "5.10", "low": "4.90",
                "close": "5.00",
                "volume": 1000000, "amount": "8700000.0",
                "is_trading": True, "adjustment": "none",
                "transport_library": "akshare", "underlying_provider": "tencent",
                "provider_version": "fixture", "endpoint_identity": "fixture.invalid",
            }
        )
    comparison = spp.compare_to_baostock(cand_rows, cand_rows)
    # A real window with before/after trade days so adjustment semantics is trusted.
    windows = [
        {
            "trade_date": cand_rows[500]["trade_date"], "type": "fixture",
            "before": [r["trade_date"] for r in cand_rows[497:500]],
            "after": [r["trade_date"] for r in cand_rows[501:503]],
        }
    ]
    adjustment = spp.check_adjustment_semantics(cand_rows, cand_rows, windows)
    classification, detail = spp.classify_candidate(
        candidate_id="tencent_via_akshare", independent=True, credential_available=True,
        acquisition={"status": "ACQUISITION_STABLE"}, comparison=comparison,
        adjustment=adjustment, limitations=[],
    )
    results = [detail]
    decision = spp.decide(results, contract_trusted=True)
    selection = spp.select_provider(results)
    decision_payload = {
        "schema": "m2_stage2k1r4e3_decision",
        "version": "1.0",
        "symbol": series_contract.SYMBOL,
        "decision": decision["decision"],
        "mode": "fixtures",
        "evidence_class": "SYNTHETIC_ENGINEERING_ONLY",
        "selected_provider": selection.get("selected_provider"),
        "candidates": [{"candidate_id": "tencent_via_akshare", "classification": classification}],
        "registry_v3_unchanged": True,
        "candidate_v2_published": False,
        "percentile_computed": False,
        "scoring_unchanged": True,
        "default_db_unchanged": True,
        "peer_acquisition": "NOT_ALLOWED",
        "m3_started": False,
    }
    _write_json(output_root / DECISION_PATH, decision_payload)
    print(json.dumps(_structured(
        decision["decision"], status="ok", message="fixtures synthetic preflight",
    ), indent=1))
    return decision_to_exit_code(decision["decision"])


# ── parser ─────────────────────────────────────────────────────────────────


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    vc = sub.add_parser("verify-contracts", help="offline contract validation")
    vc.add_argument("--config", default=str(CONFIG))

    probe = sub.add_parser("probe", help="network reachability probe")
    probe.add_argument("--config", default=str(CONFIG))
    probe.add_argument("--output-root", default=str(REPORTS))

    acquire = sub.add_parser("acquire", help="network A/B acquisition")
    acquire.add_argument("--config", default=str(CONFIG))
    acquire.add_argument("--cache-root", required=True)
    acquire.add_argument("--output-root", default=str(REPORTS))
    acquire.add_argument("--attempts", type=int, default=3)

    compare = sub.add_parser("compare", help="offline comparison vs Baostock")
    compare.add_argument("--config", default=str(CONFIG))
    compare.add_argument("--cache-root", required=True)
    compare.add_argument("--output-root", default=str(REPORTS))

    fixtures = sub.add_parser("fixtures", help="CI-only synthetic run")
    fixtures.add_argument("--config", default=str(CONFIG))
    fixtures.add_argument("--fixture-root", required=True)
    fixtures.add_argument("--output-root", default=str(REPORTS))
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "verify-contracts":
        return _cmd_verify_contracts(args)
    if args.command == "probe":
        return _cmd_probe(args)
    if args.command == "acquire":
        return _cmd_acquire(args)
    if args.command == "compare":
        return _cmd_compare(args)
    if args.command == "fixtures":
        return _cmd_fixtures(args)
    return decision_to_exit_code(spp.DECISION_NOT_TRUSTED)


if __name__ == "__main__":
    sys.exit(main())
