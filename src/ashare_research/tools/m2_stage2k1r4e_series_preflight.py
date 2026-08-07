"""M2 Stage 2K.1R4E.1 — thin CLI for the PIT valuation series release gate.

This CLI only parses arguments, calls the pit_valuation package modules, writes
report artifacts and returns a fail-closed exit code.  No formula, join, TTM,
reconciliation or identity logic lives here.

Commands:

    verify-contracts
        Offline validation of every R4E contract (no market cache required).

    formal --market-cache-root <root> --output-root <out>
            [--reported-bundle <path> --reconciled-bundle <path>]
        Validate both pinned market objects, run the daily double-source
        reconciliation, and (only when the full gate passes) build the candidate
        PE/PB/PS series v2 and write all reports.  Fail-closed exit codes.

    fixtures --output-root <out> --fixture-root <root>
        Build the candidate series v2 from synthetic dual-source market fixtures
        (CI only).  Never substitutes for the formal real-data gate.

Exit-code contract (via ``decision_to_exit_code``):

    0 = PIT_VALUATION_SERIES_CANDIDATE_TRUSTED_PERCENTILE_PREFLIGHT_ALLOWED
    1 = PIT_VALUATION_SERIES_GAPS_REMAIN
    2 = PIT_VALUATION_SERIES_NOT_TRUSTED or contract/input/schema/hash/internal failure

``--output-root`` never swallows the real exit code.
"""

from __future__ import annotations

import argparse
import json
import sys
from decimal import Decimal
from pathlib import Path
from typing import Any

from ashare_research.pit_valuation import (
    financial_state,
    provider_roles,
    series_contract,
    series_validation,
    valuation_series,
)
from ashare_research.pit_valuation import (
    market_reconciliation as mkt,
)
from ashare_research.pit_valuation.series_contract import parse_decimal
from ashare_research.scoring import artifact_manifest
from ashare_research.scoring import content_digest as cd

ROOT = Path(__file__).resolve().parents[3]
REPORTS = ROOT / "reports"

DECISION_ALLOWED = "PIT_VALUATION_SERIES_CANDIDATE_TRUSTED_PERCENTILE_PREFLIGHT_ALLOWED"
DECISION_GAPS = "PIT_VALUATION_SERIES_GAPS_REMAIN"
DECISION_NOT_TRUSTED = "PIT_VALUATION_SERIES_NOT_TRUSTED"

MANIFEST_V2_SCHEMA = "m2_stage2k1r4e1_artifact_manifest_v2"
MANIFEST_PATH = "m2_stage2k1r4e1_artifact_manifest.json"

# R4E.4 (registry v4) artifact names.
R4E4_MANIFEST_SCHEMA = "m2_stage2k1r4e4_artifact_manifest_v2"
R4E4_MANIFEST_PATH = "m2_stage2k1r4e4_artifact_manifest.json"
R4E4_DECISION_PATH = "m2_stage2k1r4e4_decision.json"
R4E4_IDENTITY_MIGRATION = "petrochina_pit_valuation_series_identity_migration_v2.json"
R4E4_RECONCILIATION_V2 = "petrochina_market_close_reconciliation_v2.json"
R4E4_LEDGER_V2 = "petrochina_market_close_mismatch_ledger_v2.json"
R4E4_REGISTRY_V4 = "events/market_data_snapshot_registry_v4.json"
R4E4_RECEIPT = "reports/petrochina_tencent_snapshot_promotion_receipt_v1.json"

# R4E.4 release definition files (acceptance / config / docs / code / tests)
# bound into the manifest so the release is auditable end to end.
R4E4_DEFINITION_FILES = [
    "acceptance/m2_stage2k1r4e4_selected_secondary_provider_integration.md",
    "config/pit_valuation_secondary_provider_preflight_v1.json",
    "docs/selected_secondary_provider_integration_contract.md",
    "src/ashare_research/pit_valuation/provider_roles.py",
    "src/ashare_research/pit_valuation/market_reconciliation.py",
    "src/ashare_research/pit_valuation/secondary_provider_preflight.py",
    "src/ashare_research/tools/m2_stage2k1r4e_series_preflight.py",
    "src/ashare_research/tools/m2_stage2k1r4e4_secondary_provider_integration.py",
    "src/ashare_research/scoring/artifact_manifest.py",
    "tests/test_m2_stage2k1r4e4_selected_provider_integration.py",
    "tests/test_m2_stage2k1r4e3_secondary_provider_preflight.py",
]

REPORT_FILES = {
    "timeline": "petrochina_pit_financial_state_timeline_v2.json",
    "candidate": "petrochina_pit_valuation_series_candidate_v2.json",
    "coverage": "petrochina_pit_valuation_series_coverage_v2.json",
    "audit": "petrochina_pit_valuation_series_audit_samples_v2.json",
    "dual": "petrochina_pit_valuation_series_dual_oracle_validation_v2.json",
    "reconciliation": "petrochina_market_close_reconciliation_v1.json",
    "mismatch_ledger": "petrochina_market_close_mismatch_ledger_v1.json",
    "identity": "petrochina_pit_valuation_series_identity_migration_v1.json",
    "decision": "m2_stage2k1r4e1_decision.json",
    "manifest": MANIFEST_PATH,
}


def decision_to_exit_code(decision: str) -> int:
    """Frozen decision -> exit-code mapping (never a constant 0)."""
    if decision == DECISION_ALLOWED:
        return 0
    if decision == DECISION_GAPS:
        return 1
    return 2  # NOT_TRUSTED or any contract/input/schema/hash/internal failure


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


def _load_bundles(args: argparse.Namespace) -> tuple[list[dict], list[dict]]:
    if getattr(args, "reported_bundle", None):
        reported_path = Path(args.reported_bundle)
    else:
        reported_path = REPORTS / "petrochina_pit_denominator_reported_fact_bundle_v1.json"
    if getattr(args, "reconciled_bundle", None):
        reconciled_path = Path(args.reconciled_bundle)
    else:
        reconciled_path = REPORTS / "petrochina_pit_denominator_reconciled_fact_bundle_v1.json"
    reported = json.loads(reported_path.read_text(encoding="utf-8"))["facts"]
    reconciled = json.loads(reconciled_path.read_text(encoding="utf-8"))["facts"]
    return reported, reconciled


def _cmd_verify_contracts(args: argparse.Namespace) -> int:
    digests = series_contract.validate_all_contracts()
    print(json.dumps({"status": "ok", "digests": digests}, indent=1))
    return 0


# ── market double-source gate ──────────────────────────────────────────────


def _reconciliation_meta(
    primary: dict[str, Any],
    secondary: dict[str, Any],
    reconciliation: dict[str, Any],
    ledger_digest: str,
) -> dict[str, Any]:
    """Assemble the market_meta contract consumed by the valuation series."""
    digest = mkt.build_reconciliation_digest(
        primary, secondary, reconciliation, ledger_digest=ledger_digest
    )
    return {
        "primary_provider": primary["provider"],
        "primary_object_sha256": primary["object_sha256"],
        "primary_object_key": primary["object_key"],
        "primary_row_count": primary["row_count"],
        "secondary_provider": secondary["provider"],
        "secondary_object_sha256": secondary["object_sha256"],
        "secondary_object_key": secondary["object_key"],
        "secondary_row_count": secondary["row_count"],
        "secondary_present": True,
        "secondary_verified": True,
        "reconciliation_status": mkt.STATUS_PASS,
        "market_reconciliation_digest": digest,
        "market_rows": primary["row_count"],
        "first_trade_date": primary["first_trade_date"],
        "last_trade_date": primary["last_trade_date"],
        "reconciliation": reconciliation,
    }


def _reconciliation_meta_v2(
    primary: dict[str, Any],
    secondary: dict[str, Any],
    reconciliation: dict[str, Any],
    ledger_digest: str,
) -> dict[str, Any]:
    """v2 market_meta: binds the provider-role identity and the v2 digest."""
    digest = mkt.build_reconciliation_digest_v2(
        primary, secondary, reconciliation, ledger_digest=ledger_digest
    )
    return {
        "primary_provider": primary.get("provider_id", primary.get("provider")),
        "primary_provider_role": primary.get("provider_role", "primary"),
        "primary_transport_library": primary.get("transport_library", ""),
        "primary_underlying_provider": primary.get("underlying_provider", ""),
        "primary_object_sha256": primary["object_sha256"],
        "primary_object_key": primary["object_key"],
        "primary_row_count": primary["row_count"],
        "secondary_provider": secondary.get("provider_id", secondary.get("provider")),
        "secondary_provider_role": secondary.get("provider_role", "secondary"),
        "secondary_transport_library": secondary.get("transport_library", ""),
        "secondary_underlying_provider": secondary.get("underlying_provider", ""),
        "secondary_endpoint_identity": secondary.get("endpoint_identity", ""),
        "secondary_object_sha256": secondary["object_sha256"],
        "secondary_object_key": secondary["object_key"],
        "secondary_row_count": secondary["row_count"],
        "secondary_present": True,
        "secondary_verified": True,
        "reconciliation_status": mkt.STATUS_PASS,
        "market_reconciliation_digest": digest,
        "reconciliation_contract_version": mkt.RECONCILIATION_CONTRACT_VERSION_V2,
        "market_rows": primary["row_count"],
        "first_trade_date": primary["first_trade_date"],
        "last_trade_date": primary["last_trade_date"],
        "reconciliation": reconciliation,
    }


def _validate_against_registry(registry: dict[str, Any], reconciliation: dict[str, Any]) -> None:
    """The real result must match the committed registry claims or fail closed."""
    if reconciliation["common_trade_days"] != registry.get("common_trade_days"):
        raise mkt.MarketReconciliationError(
            "common_trade_days disagrees with registry: "
            f"{reconciliation['common_trade_days']} != {registry.get('common_trade_days')}"
        )
    expected_max = registry.get("close_max_abs_difference")
    if (
        expected_max is not None
        and reconciliation["max_abs_difference"] is not None
        and Decimal(reconciliation["max_abs_difference"]) != Decimal(str(expected_max))
    ):
        raise mkt.MarketReconciliationError(
            "max_abs_difference disagrees with registry: "
            f"{reconciliation['max_abs_difference']} != {expected_max}"
        )
    if registry.get("close_differences_within_0_01") is not True:
        raise mkt.MarketReconciliationError("registry close tolerance not satisfied")


def _run_market_gate(
    cache_root: Path,
    registry: dict[str, Any],
) -> tuple[str, dict[str, Any] | None, dict[str, Any] | None, str]:
    """Load + validate both objects by **role** and reconcile.

    Providers are resolved by ``provider_role`` (registry v4 role schema) or via
    the legacy adapter (provider name -> role).  The formal release path never
    hard-codes a second-source name.  Returns (decision, primary, secondary,
    error).  Raises nothing itself; returns a decision plus a structured-error
    payload on the gap / not-trusted paths.
    """
    # primary must always be present and valid — its absence is a hard failure.
    try:
        primary_entry, secondary_entry = provider_roles.resolve_registry_providers(registry)
        primary = mkt.load_and_validate_market_object_entry(
            registry, cache_root, primary_entry
        )
    except provider_roles.ProviderRoleError as exc:
        return DECISION_NOT_TRUSTED, None, None, str(exc)
    except mkt.MarketObjectInvalidError as exc:
        return DECISION_NOT_TRUSTED, None, None, str(exc)
    except FileNotFoundError as exc:
        return DECISION_NOT_TRUSTED, None, None, str(exc)

    # secondary: absent -> GAPS_REMAIN (engineered contract still trusted).
    try:
        secondary = mkt.load_and_validate_market_object_entry(
            registry, cache_root, secondary_entry
        )
    except mkt.MarketObjectMissingError as exc:
        return DECISION_GAPS, primary, None, str(exc)
    except provider_roles.ProviderRoleError as exc:
        return DECISION_NOT_TRUSTED, primary, None, str(exc)
    except mkt.MarketObjectInvalidError as exc:
        return DECISION_NOT_TRUSTED, primary, None, str(exc)
    except FileNotFoundError as exc:
        return DECISION_GAPS, primary, None, str(exc)

    try:
        reconciliation = mkt.reconcile_market_close_series(primary, secondary)
        _validate_against_registry(registry, reconciliation)
    except (mkt.MarketReconciliationError, ValueError) as exc:
        return DECISION_NOT_TRUSTED, primary, secondary, str(exc)
    return DECISION_ALLOWED, primary, secondary, ""


# ── series + reports ───────────────────────────────────────────────────────


def _build_series(
    *,
    output_root: Path,
    reported: list[dict],
    reconciled: list[dict],
    market_rows: list[dict],
    market_meta: dict,
) -> dict:
    timelines = financial_state.build_financial_state_timelines(reported, reconciled)
    series = valuation_series.build_valuation_series(market_rows, market_meta, timelines)
    verification = series_validation.verify_observations(series)
    coverage = series_validation.build_coverage_report(series, timelines)
    audit = series_validation.select_audit_samples(series, timelines)
    dual = series_validation.validate_dual_oracle(market_rows, timelines)

    timeline_report = {
        "schema": "petrochina_pit_financial_state_timeline_v2",
        "version": "2.0",
        "symbol": series_contract.SYMBOL,
        "summary": financial_state.state_timeline_summary(timelines),
        "timelines": timelines,
    }
    _write_json(output_root / REPORT_FILES["timeline"], timeline_report)
    _write_json(output_root / REPORT_FILES["candidate"], series)
    _write_json(output_root / REPORT_FILES["coverage"], coverage)
    _write_json(output_root / REPORT_FILES["audit"], {"samples": audit})
    _write_json(output_root / REPORT_FILES["dual"], dual)
    return {
        "series": series,
        "verification": verification,
        "coverage": coverage,
        "audit": audit,
        "dual": dual,
        "timelines": timelines,
        "market_meta": market_meta,
    }


def _decide_from_result(result: dict) -> str:
    if not result["dual"]["all_identical"]:
        return DECISION_NOT_TRUSTED
    if not (result["verification"]["identity_consistent"]
            and result["verification"]["ratio_consistent"]):
        return DECISION_NOT_TRUSTED
    all_ready = all(
        result["coverage"]["per_metric"][m]["3y_ready"]
        and result["coverage"]["per_metric"][m]["5y_ready"]
        for m in ("PE_A_TTM", "PB_A_MRQ", "PS_A_TTM")
    )
    if not all_ready:
        return DECISION_GAPS
    return DECISION_ALLOWED


def _write_identity_migration(
    output_root: Path,
    old_series: dict[str, Any],
    new_series: dict[str, Any],
    old_timelines: dict[str, Any],
    new_timelines: dict[str, Any],
) -> None:
    """Compare old (legacy-scheme) vs new (full-lineage) series identities."""
    old_pb = {s["period_end"]: s for s in old_timelines.get("PB_A_MRQ", [])}
    new_pb = {s["period_end"]: s for s in new_timelines.get("PB_A_MRQ", [])}

    pb_migrations: list[dict[str, Any]] = []
    for period_end in sorted(set(old_pb) | set(new_pb)):
        o = old_pb.get(period_end)
        n = new_pb.get(period_end)
        assert o is not None and n is not None, f"PB state missing for {period_end}"
        pb_migrations.append(
            {
                "period_end": period_end,
                "old_financial_state_id": o["financial_state_id"],
                "new_financial_state_id": n["financial_state_id"],
                "old_input_fact_ids": o["input_fact_ids"],
                "new_input_fact_ids": n["input_fact_ids"],
                "old_effective_from": o["effective_from"],
                "new_effective_from": n["effective_from"],
                "old_available_at_max": o["available_at_max"],
                "new_available_at_max": n["available_at_max"],
                "status_unchanged": o["status"] == n["status"],
                "period_end_shares_fact_id": n.get("period_end_shares_fact_id", ""),
            }
        )

    old_by_key = {(o["metric_id"], o["trade_date"]): o for o in old_series["observations"]}
    new_by_key = {(o["metric_id"], o["trade_date"]): o for o in new_series["observations"]}
    obs_migrations: list[dict[str, Any]] = []
    ratio_changed: list[dict[str, Any]] = []
    status_changed: list[dict[str, Any]] = []
    for key in sorted(set(old_by_key) | set(new_by_key)):
        o = old_by_key.get(key)
        n = new_by_key.get(key)
        assert o is not None and n is not None, f"observation missing for {key}"
        obs_migrations.append(
            {
                "metric_id": key[0],
                "trade_date": key[1],
                "old_observation_id": o["observation_id"],
                "new_observation_id": n["observation_id"],
                "old_market_reconciliation_digest": o.get("market_reconciliation_digest", ""),
                "new_market_reconciliation_digest": n.get("market_reconciliation_digest", ""),
                "id_changed": o["observation_id"] != n["observation_id"],
                "ratio_unchanged": (o.get("ratio_decimal") == n.get("ratio_decimal")),
                "status_unchanged": o.get("status") == n.get("status"),
            }
        )
        if o.get("ratio_decimal") != n.get("ratio_decimal"):
            ratio_changed.append(
                {
                    "key": key,
                    "old": o.get("ratio_decimal"),
                    "new": n.get("ratio_decimal"),
                }
            )
        if o.get("status") != n.get("status"):
            status_changed.append({"key": key, "old": o.get("status"), "new": n.get("status")})

    report = {
        "schema": "petrochina_pit_valuation_series_identity_migration_v1",
        "symbol": series_contract.SYMBOL,
        "pb_financial_state_migrations": pb_migrations,
        "observation_identity_migrations": obs_migrations,
        "all_observation_ids_changed": all(m["id_changed"] for m in obs_migrations),
        "all_pb_state_ids_changed": all(
            m["old_financial_state_id"] != m["new_financial_state_id"]
            for m in pb_migrations
        ),
        "ratio_changed_count": len(ratio_changed),
        "status_changed_count": len(status_changed),
        "ratio_changes": ratio_changed,
        "status_changes": status_changed,
        "non_production_unchanged": all(
            o.get("non_production") is True and n.get("non_production") is True
            for o, n in zip(old_series["observations"], new_series["observations"], strict=False)
        ),
    }
    _write_json(output_root / REPORT_FILES["identity"], report)


def _decimal_eq(a: Any, b: Any) -> bool:
    """Decimal-normalized equality: ``6.0`` == ``6`` (float repr vs Decimal str)."""
    if a is None and b is None:
        return True
    if a is None or b is None:
        return False
    try:
        return parse_decimal(str(a)) == parse_decimal(str(b))
    except Exception:  # noqa: BLE001 - non-numeric -> fall back to string equality
        return a == b


def _build_identity_migration_v2(
    old_series: dict[str, Any],
    new_series: dict[str, Any],
) -> dict[str, Any]:
    """Compare the published R4E candidate v1 vs the R4E.4 formal candidate v2.

    Per-observation comparison of ratio, status, financial state and market
    close; identity changes are allowed, unexplained economic changes are not.
    Decimal values are compared with Decimal normalization (``6.0`` == ``6``).
    """
    old_by_key = {(o["metric_id"], o["trade_date"]): o for o in old_series["observations"]}
    new_by_key = {(o["metric_id"], o["trade_date"]): o for o in new_series["observations"]}
    keys = sorted(set(old_by_key) | set(new_by_key))

    ratio_changed: list[dict[str, Any]] = []
    status_changed: list[dict[str, Any]] = []
    financial_state_changed: list[dict[str, Any]] = []
    market_close_changed: list[dict[str, Any]] = []
    id_changed_count = 0
    unmatched_count = 0
    observation_rows: list[dict[str, Any]] = []

    for key in keys:
        o = old_by_key.get(key)
        n = new_by_key.get(key)
        if o is None or n is None:
            unmatched_count += 1
            observation_rows.append(
                {
                    "metric_id": key[0],
                    "trade_date": key[1],
                    "missing_side": "old" if o is None else "new",
                }
            )
            continue
        id_changed = o.get("observation_id") != n.get("observation_id")
        if id_changed:
            id_changed_count += 1
        ratio_unchanged = _decimal_eq(o.get("ratio_decimal"), n.get("ratio_decimal"))
        status_unchanged = o.get("status") == n.get("status")
        fs_unchanged = o.get("financial_state_id") == n.get("financial_state_id")
        mc_unchanged = _decimal_eq(
            o.get("market_close_decimal"), n.get("market_close_decimal")
        )
        observation_rows.append(
            {
                "metric_id": key[0],
                "trade_date": key[1],
                "old_observation_id": o.get("observation_id"),
                "new_observation_id": n.get("observation_id"),
                "id_changed": id_changed,
                "ratio_unchanged": ratio_unchanged,
                "status_unchanged": status_unchanged,
                "financial_state_unchanged": fs_unchanged,
                "market_close_unchanged": mc_unchanged,
            }
        )
        if not ratio_unchanged:
            ratio_changed.append(
                {
                    "metric_id": key[0],
                    "trade_date": key[1],
                    "old": o.get("ratio_decimal"),
                    "new": n.get("ratio_decimal"),
                }
            )
        if not status_unchanged:
            status_changed.append(
                {
                    "metric_id": key[0],
                    "trade_date": key[1],
                    "old": o.get("status"),
                    "new": n.get("status"),
                }
            )
        if not fs_unchanged:
            financial_state_changed.append(
                {
                    "metric_id": key[0],
                    "trade_date": key[1],
                    "old": o.get("financial_state_id", "")[:16],
                    "new": n.get("financial_state_id", "")[:16],
                }
            )
        if not mc_unchanged:
            market_close_changed.append(
                {
                    "metric_id": key[0],
                    "trade_date": key[1],
                    "old": o.get("market_close_decimal"),
                    "new": n.get("market_close_decimal"),
                }
            )

    return {
        "schema": "petrochina_pit_valuation_series_identity_migration_v2",
        "symbol": series_contract.SYMBOL,
        "observation_count": len(keys),
        "unmatched_count": unmatched_count,
        "observation_id_changed_count": id_changed_count,
        "ratio_changed_count": len(ratio_changed),
        "status_changed_count": len(status_changed),
        "financial_state_changed_count": len(financial_state_changed),
        "market_close_changed_count": len(market_close_changed),
        "ratio_changes": ratio_changed,
        "status_changes": status_changed,
        "financial_state_changes": financial_state_changed,
        "market_close_changes": market_close_changed,
        "observations": observation_rows,
    }


def _economic_migration_trusted(migration: dict[str, Any]) -> bool:
    """Economic values (ratio/status/market close) must be unchanged to trust."""
    return (
        migration["ratio_changed_count"] == 0
        and migration["status_changed_count"] == 0
        and migration["market_close_changed_count"] == 0
    )


# ── manifest v2 ────────────────────────────────────────────────────────────


def _relative_logical(repo_root: Path, path: Path) -> str:
    return str(path.resolve().relative_to(repo_root.resolve()).as_posix())


def _write_manifest_v2(output_root: Path, written_files: list[Path]) -> None:
    """Write the verifiable v2 manifest for the text artifacts just produced."""
    _write_manifest_v2_schema(
        output_root, written_files, schema=MANIFEST_V2_SCHEMA, manifest_name=MANIFEST_PATH
    )


def _write_manifest_v2_schema(
    output_root: Path,
    written_files: list[Path],
    *,
    schema: str,
    manifest_name: str,
) -> None:
    files: list[dict[str, Any]] = []
    for path in sorted(written_files, key=lambda p: _relative_logical(ROOT, p)):
        if path.resolve() == (output_root / manifest_name).resolve():
            continue  # manifest never lists itself
        digest = cd.digest_file(path, algorithm="sha256_lf_normalized_bytes_v1")
        files.append(
            {
                "path": _relative_logical(ROOT, path),
                "digest_algorithm": digest.algorithm,
                "sha256": digest.sha256,
                "byte_size": digest.byte_size,
            }
        )
    manifest = {
        "schema": schema,
        "version": "2.0",
        "files": files,
    }
    manifest["manifest_digest"] = artifact_manifest.manifest_digest(manifest)
    _write_json(output_root / manifest_name, manifest)


def _verify_manifest_v2(output_root: Path) -> dict[str, Any]:
    """Verify the just-written v2 manifest against the repository root."""
    return artifact_manifest.verify_artifact_manifest(
        output_root / MANIFEST_PATH, repository_root=ROOT
    ).to_dict()


# ── commands ───────────────────────────────────────────────────────────────


def _cmd_formal(args: argparse.Namespace) -> int:
    try:
        series_contract.validate_all_contracts()
    except Exception as exc:  # noqa: BLE001
        payload = _structured(
            DECISION_NOT_TRUSTED, status="error", failed_contract="contracts",
            error_type=type(exc).__name__, message=str(exc),
        )
        print(json.dumps(payload, indent=1))
        return decision_to_exit_code(DECISION_NOT_TRUSTED)

    reported, reconciled = _load_bundles(args)
    registry = (
        json.loads(Path(args.market_registry).read_text(encoding="utf-8"))
        if getattr(args, "market_registry", None)
        else series_contract.load_market_snapshot_registry()
    )
    cache_root = Path(args.market_cache_root)
    output_root = Path(args.output_root)

    # R4E.4: a v4 registry runs the role-based formal path (v2 reconciliation
    # contract, v2 identity migration, R4E.4 decision/manifest).
    if registry.get("contract") == "market_data_snapshot_registry_v4":
        return _cmd_formal_r4e4(
            args, registry, cache_root, output_root, reported, reconciled
        )

    decision, primary, secondary, err = _run_market_gate(cache_root, registry)

    if decision == DECISION_GAPS:
        # A: secondary pinned object absent — write an explicit gap decision,
        # never publish candidate v2, exit 1.
        decision_payload = {
            "schema": "m2_stage2k1r4e1_decision",
            "version": "2.0",
            "symbol": series_contract.SYMBOL,
            "decision": DECISION_GAPS,
            "market_reconciliation_status": mkt.STATUS_GAPS_REMAIN,
            "akshare_object_recovery": "NOT_FOUND",
            "gap_detail": err,
            "percentile_computed": False,
            "score_eligible": False,
            "production_eligible": False,
        }
        _write_json(output_root / REPORT_FILES["decision"], decision_payload)
        _write_manifest_v2(output_root, [output_root / REPORT_FILES["decision"]])
        print(json.dumps(_structured(
            DECISION_GAPS, status="gap", failed_contract="market_object:akshare",
            error_type="MarketObjectMissingError", message=err,
        ), indent=1))
        return decision_to_exit_code(DECISION_GAPS)

    if decision == DECISION_NOT_TRUSTED:
        # B: secondary present but hash/schema/date/close reconciliation failed.
        payload = _structured(
            DECISION_NOT_TRUSTED, status="error", failed_contract="market_reconciliation",
            error_type=(
                "MarketObjectInvalidError"
                if secondary is None
                else "MarketReconciliationError"
            ),
            message=err,
        )
        print(json.dumps(payload, indent=1))
        return decision_to_exit_code(DECISION_NOT_TRUSTED)

    # C: full double-source gate passed -> build candidate v2.
    assert primary is not None and secondary is not None
    reconciliation = mkt.reconcile_market_close_series(primary, secondary)
    ledger = mkt.build_mismatch_ledger(reconciliation)
    ledger_digest = mkt.build_mismatch_ledger_digest(ledger)
    market_meta = _reconciliation_meta(primary, secondary, reconciliation, ledger_digest)

    result = _build_series(
        output_root=output_root,
        reported=reported,
        reconciled=reconciled,
        market_rows=primary["rows"],
        market_meta=market_meta,
    )
    decision = _decide_from_result(result)

    if decision != DECISION_ALLOWED:
        payload = _structured(
            decision, status="error", failed_contract="series_validation",
            error_type="ReleaseGate", message="series validators/coverage gate failed",
        )
        print(json.dumps(payload, indent=1))
        return decision_to_exit_code(decision)

    # reconciliation + mismatch-ledger + identity + decision reports.
    reconciliation_report = mkt.build_reconciliation_report(
        primary, secondary, reconciliation, ledger_digest=ledger_digest
    )
    _write_json(output_root / REPORT_FILES["reconciliation"], reconciliation_report)
    _write_json(output_root / REPORT_FILES["mismatch_ledger"], ledger)

    # identity migration: compare legacy-scheme reconstruction vs new v2.
    legacy_timelines, legacy_series = _build_legacy_series(reported, reconciled, primary["rows"])
    _write_identity_migration(
        output_root, legacy_series, result["series"], legacy_timelines, result["timelines"]
    )

    decision_payload = {
        "schema": "m2_stage2k1r4e1_decision",
        "version": "2.0",
        "symbol": series_contract.SYMBOL,
        "decision": DECISION_ALLOWED,
        "contracts_trusted": True,
        "financial_state_timeline_trusted": True,
        "dual_oracle_identical": result["dual"]["all_identical"],
        "identity_consistent": result["verification"]["identity_consistent"],
        "ratio_consistent": result["verification"]["ratio_consistent"],
        "market_reconciliation_status": mkt.STATUS_PASS,
        "market_reconciliation_digest": market_meta["market_reconciliation_digest"],
        "common_trade_days": reconciliation["common_trade_days"],
        "max_abs_close_difference": reconciliation["max_abs_difference"],
        "coverage": {
            metric: {
                "3y_ready": result["coverage"]["per_metric"][metric]["3y_ready"],
                "5y_ready": result["coverage"]["per_metric"][metric]["5y_ready"],
            }
            for metric in ("PE_A_TTM", "PB_A_MRQ", "PS_A_TTM")
        },
        "percentile_computed": False,
        "score_eligible": False,
        "production_eligible": False,
    }
    _write_json(output_root / REPORT_FILES["decision"], decision_payload)

    written = [
        output_root / REPORT_FILES[name]
        for name in (
            "timeline", "candidate", "coverage", "audit", "dual",
            "reconciliation", "mismatch_ledger", "identity", "decision",
        )
    ]
    _write_manifest_v2(output_root, written)

    print(json.dumps(_structured(
        DECISION_ALLOWED, status="ok", failed_contract="", message="release gate passed"
    ), indent=1))
    print(f"reconciliation_digest: {market_meta['market_reconciliation_digest']}")
    return decision_to_exit_code(DECISION_ALLOWED)


def _r4e4_fail(
    decision: str,
    output_root: Path,
    failed_contract: str,
    error_type: str,
    message: str,
) -> int:
    """Write the R4E.4 decision + manifest for a fail path and return the code."""
    decision_payload = {
        "schema": "m2_stage2k1r4e4_decision",
        "version": "2.0",
        "symbol": series_contract.SYMBOL,
        "decision": decision,
        "failed_contract": failed_contract,
        "error_type": error_type,
        "message": message,
        "percentile_computed": False,
        "score_eligible": False,
        "production_eligible": False,
    }
    _write_json(output_root / R4E4_DECISION_PATH, decision_payload)
    _write_manifest_v2_schema(
        output_root,
        [output_root / R4E4_DECISION_PATH],
        schema=R4E4_MANIFEST_SCHEMA,
        manifest_name=R4E4_MANIFEST_PATH,
    )
    print(json.dumps(_structured(
        decision, status="error", failed_contract=failed_contract,
        error_type=error_type, message=message,
    ), indent=1))
    return decision_to_exit_code(decision)


def _cmd_formal_r4e4(
    args: argparse.Namespace,
    registry: dict[str, Any],
    cache_root: Path,
    output_root: Path,
    reported: list[dict],
    reconciled: list[dict],
) -> int:
    """R4E.4 formal path: role-based providers, v2 reconciliation, candidate v2."""
    # 1. role-based object validation (fail-closed, never hard-coded names).
    try:
        primary_entry, secondary_entry = provider_roles.resolve_registry_providers(registry)
        primary = mkt.load_and_validate_market_object_entry(
            registry, cache_root, primary_entry
        )
        secondary = mkt.load_and_validate_market_object_entry(
            registry, cache_root, secondary_entry
        )
    except provider_roles.ProviderRoleError as exc:
        return _r4e4_fail(
            DECISION_NOT_TRUSTED, output_root, "provider_roles",
            "ProviderRoleError", str(exc),
        )
    except mkt.MarketObjectMissingError as exc:
        return _r4e4_fail(
            DECISION_GAPS, output_root, "market_object:secondary",
            "MarketObjectMissingError", str(exc),
        )
    except mkt.MarketObjectInvalidError as exc:
        return _r4e4_fail(
            DECISION_NOT_TRUSTED, output_root, "market_object",
            "MarketObjectInvalidError", str(exc),
        )
    except FileNotFoundError as exc:
        return _r4e4_fail(
            DECISION_GAPS, output_root, "market_object",
            "FileNotFoundError", str(exc),
        )

    # 2. real formal v2 reconciliation (recomputed, never reused from R4E.3).
    try:
        reconciliation = mkt.reconcile_market_close_series_v2(primary, secondary)
        ledger = mkt.build_mismatch_ledger_v2(reconciliation)
        ledger_digest = mkt.build_mismatch_ledger_digest(ledger)
        v2_report = mkt.build_reconciliation_report_v2(
            primary, secondary, reconciliation, ledger_digest=ledger_digest
        )
        v2_validation = mkt.validate_reconciliation_report_v2(v2_report)
        if not v2_validation["valid"]:
            raise mkt.MarketReconciliationError(
                f"v2 reconciliation report invalid: {v2_validation['errors']}"
            )
    except (mkt.MarketReconciliationError, ValueError) as exc:
        return _r4e4_fail(
            DECISION_NOT_TRUSTED, output_root, "formal_reconciliation",
            "MarketReconciliationError", str(exc),
        )

    # 3. market_meta binds the v2 digest into every observation.
    market_meta = _reconciliation_meta_v2(primary, secondary, reconciliation, ledger_digest)

    # 4. candidate series + coverage + dual oracle + audit.
    result = _build_series(
        output_root=output_root,
        reported=reported,
        reconciled=reconciled,
        market_rows=primary["rows"],
        market_meta=market_meta,
    )
    decision = _decide_from_result(result)
    if decision != DECISION_ALLOWED:
        return _r4e4_fail(
            decision, output_root, "series_validation", "ReleaseGate",
            "series validators/coverage gate failed",
        )

    # 5. economic migration v2: R4E candidate v1 vs the formal candidate v2.
    old_candidate_path = ROOT / "reports" / "petrochina_pit_valuation_series_candidate_v1.json"
    if not old_candidate_path.is_file():
        return _r4e4_fail(
            DECISION_NOT_TRUSTED, output_root, "economic_migration",
            "V1CandidateMissing", "published candidate v1 not found",
        )
    old_candidate = json.loads(old_candidate_path.read_text(encoding="utf-8"))
    migration = _build_identity_migration_v2(old_candidate, result["series"])
    _write_json(output_root / R4E4_IDENTITY_MIGRATION, migration)
    if not _economic_migration_trusted(migration):
        return _r4e4_fail(
            DECISION_NOT_TRUSTED, output_root, "economic_migration",
            "EconomicValueChanged",
            "ratio/status/market close changed; see identity migration v2 reason ledger",
        )

    # 6. write the v2 reconciliation + ledger (deterministic, same as reconcile mode).
    _write_json(output_root / R4E4_RECONCILIATION_V2, v2_report)
    _write_json(output_root / R4E4_LEDGER_V2, ledger)

    # 7. decision payload.
    decision_payload = {
        "schema": "m2_stage2k1r4e4_decision",
        "version": "2.0",
        "symbol": series_contract.SYMBOL,
        "decision": DECISION_ALLOWED,
        "contracts_trusted": True,
        "financial_state_timeline_trusted": True,
        "dual_oracle_identical": result["dual"]["all_identical"],
        "identity_consistent": result["verification"]["identity_consistent"],
        "ratio_consistent": result["verification"]["ratio_consistent"],
        "provider_role_abstraction": "TRUSTED",
        "registry_v4": "TRUSTED",
        "market_reconciliation_status": mkt.STATUS_PASS,
        "market_reconciliation_digest": market_meta["market_reconciliation_digest"],
        "reconciliation_contract_version": mkt.RECONCILIATION_CONTRACT_VERSION_V2,
        "common_trade_days": reconciliation["common_trade_days"],
        "max_abs_close_difference": reconciliation["max_abs_difference"],
        "differences_over_tolerance_count": reconciliation[
            "differences_over_tolerance_count"
        ],
        "primary_provider_id": market_meta["primary_provider"],
        "secondary_provider_id": market_meta["secondary_provider"],
        "secondary_transport_library": market_meta["secondary_transport_library"],
        "secondary_underlying_provider": market_meta["secondary_underlying_provider"],
        "observation_count": result["series"]["observation_count"],
        "economic_migration": {
            "ratio_changed_count": migration["ratio_changed_count"],
            "status_changed_count": migration["status_changed_count"],
            "financial_state_changed_count": migration["financial_state_changed_count"],
            "market_close_changed_count": migration["market_close_changed_count"],
        },
        "coverage": {
            metric: {
                "3y_ready": result["coverage"]["per_metric"][metric]["3y_ready"],
                "5y_ready": result["coverage"]["per_metric"][metric]["5y_ready"],
            }
            for metric in ("PE_A_TTM", "PB_A_MRQ", "PS_A_TTM")
        },
        "percentile_computed": False,
        "score_eligible": False,
        "production_eligible": False,
    }
    _write_json(output_root / R4E4_DECISION_PATH, decision_payload)

    # 8. R4E.4 manifest (registry v4 + receipt + reconciliation + candidate set
    #    + the acceptance/config/docs/code/tests that define this release).
    written = [
        output_root / REPORT_FILES[name]
        for name in ("timeline", "candidate", "coverage", "audit", "dual")
    ]
    written += [
        output_root / R4E4_IDENTITY_MIGRATION,
        output_root / R4E4_DECISION_PATH,
        output_root / R4E4_RECONCILIATION_V2,
        output_root / R4E4_LEDGER_V2,
        ROOT / R4E4_REGISTRY_V4,
        ROOT / R4E4_RECEIPT,
    ]
    written += [ROOT / rel for rel in R4E4_DEFINITION_FILES]
    _write_manifest_v2_schema(
        output_root,
        written,
        schema=R4E4_MANIFEST_SCHEMA,
        manifest_name=R4E4_MANIFEST_PATH,
    )

    print(json.dumps(_structured(
        DECISION_ALLOWED, status="ok", failed_contract="",
        message="R4E.4 formal release gate passed",
    ), indent=1))
    print(f"formal_reconciliation_digest: {market_meta['market_reconciliation_digest']}")
    return decision_to_exit_code(DECISION_ALLOWED)


def _build_legacy_series(
    reported: list[dict],
    reconciled: list[dict],
    market_rows: list[dict],
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Reconstruct the pre-R4E1 legacy-scheme series for the identity migration.

    Uses the legacy PB binding (equity-only input provenance) and the legacy
    reconciliation digest so the migration report can show which identity fields
    changed and prove economic values are unchanged.
    """
    legacy_timelines = _legacy_timelines(reported, reconciled)
    legacy_meta = {
        "primary_object_sha256": "legacy",
        "secondary_object_sha256": "legacy",
        "market_reconciliation_digest": "legacy-reconciliation-digest",
        "reconciliation_status": "pass",
        "market_rows": len(market_rows),
        "first_trade_date": market_rows[0]["trade_date"],
        "last_trade_date": market_rows[-1]["trade_date"],
    }
    legacy_series = valuation_series.build_valuation_series(
        market_rows, legacy_meta, legacy_timelines
    )
    return legacy_timelines, legacy_series


def _legacy_timelines(
    reported: list[dict], reconciled: list[dict]
) -> dict[str, list[dict[str, Any]]]:
    """Legacy PB scheme: equity-only input_fact_ids, share only as a Decimal."""
    timelines = financial_state.build_financial_state_timelines(reported, reconciled)
    pb = []
    for state in timelines["PB_A_MRQ"]:
        core = {k: v for k, v in state.items() if k not in ("financial_state_id", "state_digest")}
        core["input_fact_ids"] = [core["equity_fact_id"]]
        core["effective_from"] = core["equity_effective_from"]
        core["available_at_max"] = core["equity_available_at"]
        state_id = series_contract.canonical_digest(core)
        pb.append({"financial_state_id": state_id, **core, "state_digest": state_id})
    timelines["PB_A_MRQ"] = pb
    return timelines


def _cmd_fixtures(args: argparse.Namespace) -> int:
    """CI-only synthetic run; never substitutes for the formal candidate."""
    from ashare_research.pit_valuation import fixtures

    try:
        series_contract.validate_all_contracts()
    except Exception as exc:  # noqa: BLE001
        payload = _structured(
            DECISION_NOT_TRUSTED, status="error", failed_contract="contracts",
            error_type=type(exc).__name__, message=str(exc),
        )
        print(json.dumps(payload, indent=1))
        return decision_to_exit_code(DECISION_NOT_TRUSTED)

    reported, reconciled = fixtures.load_fixture_bundles(Path(args.fixture_root))
    primary_rows, secondary_rows, _meta = fixtures.load_fixture_dual_market(
        Path(args.fixture_root)
    )
    output_root = Path(args.output_root)

    primary = {
        "provider": "baostock",
        "object_sha256": "synthetic" + "0" * 57,
        "object_key": "synthetic/baostock.parquet",
        "row_count": len(primary_rows),
        "first_trade_date": primary_rows[0]["trade_date"],
        "last_trade_date": primary_rows[-1]["trade_date"],
        "rows": primary_rows,
    }
    secondary = {
        "provider": "akshare",
        "object_sha256": "synthetic" + "1" * 57,
        "object_key": "synthetic/akshare.parquet",
        "row_count": len(secondary_rows),
        "first_trade_date": secondary_rows[0]["trade_date"],
        "last_trade_date": secondary_rows[-1]["trade_date"],
        "rows": secondary_rows,
    }
    reconciliation = mkt.reconcile_market_close_series(primary, secondary)
    ledger = mkt.build_mismatch_ledger(reconciliation)
    ledger_digest = mkt.build_mismatch_ledger_digest(ledger)
    market_meta = _reconciliation_meta(primary, secondary, reconciliation, ledger_digest)

    result = _build_series(
        output_root=output_root,
        reported=reported,
        reconciled=reconciled,
        market_rows=primary_rows,
        market_meta=market_meta,
    )
    decision = _decide_from_result(result)

    reconciliation_report = mkt.build_reconciliation_report(
        primary, secondary, reconciliation, ledger_digest=ledger_digest
    )
    _write_json(output_root / REPORT_FILES["reconciliation"], reconciliation_report)
    _write_json(output_root / REPORT_FILES["mismatch_ledger"], ledger)

    legacy_timelines, legacy_series = _build_legacy_series(reported, reconciled, primary_rows)
    _write_identity_migration(
        output_root, legacy_series, result["series"], legacy_timelines, result["timelines"]
    )

    decision_payload = {
        "schema": "m2_stage2k1r4e1_decision",
        "version": "2.0",
        "symbol": series_contract.SYMBOL,
        "decision": decision,
        "mode": "fixtures",
        "evidence_class": "SYNTHETIC_ENGINEERING_ONLY",
        "market_reconciliation_status": mkt.STATUS_PASS,
        "market_reconciliation_digest": market_meta["market_reconciliation_digest"],
        "coverage": {
            metric: {
                "3y_ready": result["coverage"]["per_metric"][metric]["3y_ready"],
                "5y_ready": result["coverage"]["per_metric"][metric]["5y_ready"],
            }
            for metric in ("PE_A_TTM", "PB_A_MRQ", "PS_A_TTM")
        },
        "percentile_computed": False,
        "score_eligible": False,
        "production_eligible": False,
    }
    _write_json(output_root / REPORT_FILES["decision"], decision_payload)

    written = [
        output_root / REPORT_FILES[name]
        for name in (
            "timeline", "candidate", "coverage", "audit", "dual",
            "reconciliation", "mismatch_ledger", "identity", "decision",
        )
    ]
    _write_manifest_v2(output_root, written)

    print(json.dumps(_structured(
        decision, status="ok" if decision == DECISION_ALLOWED else "error",
        failed_contract="", message="fixtures run"
    ), indent=1))
    return decision_to_exit_code(decision)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("verify-contracts", help="validate all R4E contracts")

    formal = sub.add_parser("formal", help="build candidate series from real external cache")
    formal.add_argument("--market-cache-root", required=True)
    formal.add_argument("--market-registry", default=None,
                        help="explicit market snapshot registry (e.g. registry v3)")
    formal.add_argument("--output-root", default=str(REPORTS))
    formal.add_argument("--reported-bundle", default=None)
    formal.add_argument("--reconciled-bundle", default=None)

    fixtures = sub.add_parser(
        "fixtures", help="build candidate series from synthetic fixtures (CI)"
    )
    fixtures.add_argument("--fixture-root", required=True)
    fixtures.add_argument("--output-root", default=str(REPORTS))
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "verify-contracts":
        return _cmd_verify_contracts(args)
    if args.command == "formal":
        return _cmd_formal(args)
    if args.command == "fixtures":
        return _cmd_fixtures(args)
    return decision_to_exit_code(DECISION_NOT_TRUSTED)


if __name__ == "__main__":
    sys.exit(main())
