"""M2 Stage 2K.1R4E.1 — dual-source market reconciliation and release gate.

This module is the single, deterministic home for the market double-source
proof:

- ``load_and_validate_market_object`` loads one provider object (baostock or
  akshare) from the caller-supplied content cache and verifies it *independently*
  against the frozen registry: object key, regular-file existence, real SHA-256,
  Parquet readability, row count, required columns, symbol, adjustment, trade_date
  uniqueness/ordering, first/last date, trading-row count, and Decimal-parseable
  closes.  It never scans other Parquet to substitute, never marks a provider
  ``pass`` from a pre-written registry flag, and never checks only the SHA.
- ``reconcile_market_close_series`` aligns the two verified objects by exact
  ``trade_date`` and recomputes the daily close comparison in canonical Decimal
  (``Decimal(str(...))``; ``float(...)`` and ``Decimal(binary_float)`` both
  prohibited).  The tolerance is read from the versioned formula-registry
  contract, never scattered as a literal.
- ``build_mismatch_ledger`` / ``build_reconciliation_digest`` produce the ledger
  of over-tolerance differences and a digest that binds both object SHAs, row
  counts, date range, tolerance, the date-set summary, the daily close comparison
  summary, the ledger digest, and the reconciliation contract version.

Fail-closed: any object missing is ``MarketObjectMissingError`` (GAPS_REMAIN);
any object invalid, date-set mismatch, schema mismatch, or close beyond tolerance
is ``MarketObjectInvalidError`` / ``MarketReconciliationError`` → the
``PIT_VALUATION_SERIES_NOT_TRUSTED`` status.  This module never opens the default
database and never performs a network refresh.
"""

from __future__ import annotations

import hashlib
from decimal import Decimal
from pathlib import Path
from typing import Any

from ashare_research.pit_valuation import provider_roles
from ashare_research.pit_valuation.series_contract import (
    SYMBOL,
    canonical_digest,
    close_tolerance_decimal,
    parse_decimal,
)

RECONCILIATION_CONTRACT_VERSION = "pit_valuation_market_double_source_reconciliation_v1"
# v2 contract: binds the provider-role identity (provider_id / role / transport /
# underlying / endpoint / table digest) plus the daily comparison digest.  The
# v1 digest remains the historical contract and is never recomputed as v2.
RECONCILIATION_CONTRACT_VERSION_V2 = "pit_valuation_market_double_source_reconciliation_v2"

# Statuses surfaced to the CLI / decision layer.
STATUS_PASS = "pass"
STATUS_GAPS_REMAIN = "BLOCKED_EXTERNAL_MARKET_CACHE_UNAVAILABLE"
STATUS_NOT_TRUSTED = "PIT_VALUATION_SERIES_NOT_TRUSTED"

REQUIRED_COLUMNS = ("symbol", "trade_date", "close", "is_trading")


class MarketObjectMissingError(FileNotFoundError):
    """The pinned provider content object is absent (→ GAPS_REMAIN)."""


class MarketObjectInvalidError(ValueError):
    """A present provider object fails validation (→ NOT_TRUSTED)."""


class MarketReconciliationError(ValueError):
    """The dual-source reconciliation fails (→ NOT_TRUSTED)."""


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _iso_date(value: Any) -> str:
    """Normalise a date/datetime/str to an ISO ``YYYY-MM-DD`` string."""
    if isinstance(value, str):
        return value[:10]
    from datetime import date, datetime

    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    return str(value)[:10]


def _registry_provider(registry: dict[str, Any], provider: str) -> dict[str, Any]:
    for p in registry.get("providers", []):
        if p.get("provider") == provider:
            return p
    raise MarketObjectInvalidError(f"provider {provider!r} not in market snapshot registry")


# ── single-object load + validation ────────────────────────────────────────


def load_and_validate_market_object(
    registry: dict[str, Any],
    cache_root: Path,
    provider: str,
) -> dict[str, Any]:
    """Load and independently validate one provider market object by legacy name.

    A thin wrapper over :func:`load_and_validate_market_object_entry` that
    resolves the entry by the legacy ``provider`` name (kept for the v1/v2/v3
    registries and the R4E.1 contract tests).  The formal R4E.4 path resolves
    entries by role and calls the entry loader directly — it never hard-codes a
    second-source name.
    """
    entry = _registry_provider(registry, provider)
    return load_and_validate_market_object_entry(registry, cache_root, entry)


def load_and_validate_market_object_entry(
    registry: dict[str, Any],
    cache_root: Path,
    entry: dict[str, Any],
) -> dict[str, Any]:
    """Load and independently validate one provider market object from its entry.

    Supports both the v4 role-schema entries (``provider_id`` / ``provider_role``
    / ``transport_library`` / ``underlying_provider``) and the legacy v2/v3
    entries (``provider`` name).  Returns a dict with the parsed trading rows
    (each ``{"trade_date": str, "close": Decimal}``), the per-object validation
    metadata, and the role identity.  Raises :class:`MarketObjectMissingError`
    when the pinned object is absent and :class:`MarketObjectInvalidError` on any
    validation failure.
    """
    provider = provider_roles.entry_provider_id(entry, registry=registry)
    role = provider_roles.entry_role(entry, registry=registry)
    object_key = entry.get("object_key", "")
    expected_sha = entry.get("sha256", "")
    expected_row_count = entry.get("row_count")
    expected_adjustment = entry.get("adjustment", "")
    entry_range = entry.get("date_range", {}) or {}
    expected_start = entry_range.get("start") or entry.get("first_trade_date", "")
    expected_end = entry_range.get("end") or entry.get("last_trade_date", "")

    if not object_key:
        raise MarketObjectInvalidError(f"{provider} missing object_key in registry")
    if len(expected_sha) != 64:
        raise MarketObjectInvalidError(f"{provider} missing registry sha256")

    path = (Path(cache_root) / object_key).resolve()
    if not path.is_file():
        raise MarketObjectMissingError(
            f"pinned {provider} market object absent: {object_key}"
        )
    if not path.is_file() or not path.is_absolute():
        # regular-file check is below; is_absolute is always true after resolve.
        pass

    actual_sha = _sha256_bytes(path.read_bytes())
    if actual_sha != expected_sha:
        raise MarketObjectInvalidError(
            f"{provider} object sha mismatch: {actual_sha[:12]}... != {expected_sha[:12]}..."
        )

    try:
        import pandas as pd

        df = pd.read_parquet(path)
    except Exception as exc:  # noqa: BLE001 - any parquet read failure is fatal
        raise MarketObjectInvalidError(f"{provider} parquet not readable: {exc}") from exc

    missing_cols = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing_cols:
        raise MarketObjectInvalidError(
            f"{provider} missing required columns: {missing_cols}"
        )

    if len(df) != expected_row_count:
        raise MarketObjectInvalidError(
            f"{provider} row_count {len(df)} != registry {expected_row_count}"
        )

    if expected_adjustment != "none":
        raise MarketObjectInvalidError(
            f"{provider} registry adjustment must be none (got {expected_adjustment!r})"
        )

    # symbol: every row must be the pinned symbol.
    symbols = {str(s) for s in df["symbol"].dropna().unique()}
    if symbols != {SYMBOL}:
        raise MarketObjectInvalidError(f"{provider} symbol set mismatch: {symbols}")

    tdates = df["trade_date"].tolist()
    if any(pd.isna(d) for d in tdates):
        raise MarketObjectInvalidError(f"{provider} trade_date contains nulls")
    iso_dates = [_iso_date(d) for d in tdates]
    if len(set(iso_dates)) != len(iso_dates):
        raise MarketObjectInvalidError(f"{provider} trade_date is not unique")
    if iso_dates != sorted(iso_dates):
        raise MarketObjectInvalidError(f"{provider} trade_date is not strictly increasing")

    # trading rows: is_trading must be true for the registry row count.
    trading = [iso_dates[i] for i, v in enumerate(df["is_trading"].tolist()) if bool(v)]
    if len(trading) != expected_row_count:
        raise MarketObjectInvalidError(
            f"{provider} trading rows {len(trading)} != registry {expected_row_count}"
        )

    first, last = iso_dates[0], iso_dates[-1]
    if expected_start and first != expected_start:
        raise MarketObjectInvalidError(
            f"{provider} first date {first} != registry {expected_start}"
        )
    if expected_end and last != expected_end:
        raise MarketObjectInvalidError(
            f"{provider} last date {last} != registry {expected_end}"
        )

    # close: non-null, finite, Decimal-parseable via canonical string.
    rows: list[dict[str, Any]] = []
    closes = df["close"].tolist()
    for i, d in enumerate(iso_dates):
        if bool(df["is_trading"].iloc[i]) is False:
            continue
        c = closes[i]
        if c is None or (hasattr(c, "isna") and bool(c.isna())):
            raise MarketObjectInvalidError(f"{provider} close null at {d}")
        try:
            dec = parse_decimal(str(c))
        except Exception as exc:  # noqa: BLE001
            raise MarketObjectInvalidError(
                f"{provider} close not Decimal-parseable at {d}: {exc}"
            ) from exc
        if not dec.is_finite():
            raise MarketObjectInvalidError(f"{provider} close non-finite at {d}")
        rows.append({"trade_date": d, "close": dec})

    if len(rows) != expected_row_count:
        raise MarketObjectInvalidError(
            f"{provider} parsed rows {len(rows)} != registry {expected_row_count}"
        )

    return {
        "provider": provider,
        "provider_id": provider_roles.entry_provider_id(entry, registry=registry),
        "provider_role": role,
        "transport_library": entry.get("transport_library", ""),
        "underlying_provider": entry.get("underlying_provider", ""),
        "endpoint_identity": entry.get("endpoint_identity", ""),
        "table_digest": entry.get("table_digest", ""),
        "object_key": object_key,
        "object_sha256": expected_sha,
        "actual_sha256": actual_sha,
        "row_count": len(rows),
        "first_trade_date": rows[0]["trade_date"],
        "last_trade_date": rows[-1]["trade_date"],
        "adjustment": expected_adjustment,
        "rows": rows,
    }


# ── daily Decimal double-source reconciliation ────────────────────────────


def _by_date(rows: list[dict[str, Any]]) -> dict[str, Decimal]:
    return {r["trade_date"]: r["close"] for r in rows}


def _reconcile_core(
    primary: dict[str, Any],
    secondary: dict[str, Any],
    *,
    tolerance: Decimal,
) -> dict[str, Any]:
    """Shared daily Decimal comparison; role-neutral ``primary_close``/``secondary_close``.

    Raises :class:`MarketReconciliationError` on any date-set / schema conflict or
    an over-tolerance close.  The economic result is provider-name independent.
    """
    primary_rows = primary["rows"]
    secondary_rows = secondary["rows"]
    primary_dates = [r["trade_date"] for r in primary_rows]
    secondary_dates = [r["trade_date"] for r in secondary_rows]

    pset = set(primary_dates)
    sset = set(secondary_dates)
    if len(primary_dates) != len(pset) or len(secondary_dates) != len(sset):
        raise MarketReconciliationError("duplicate trade_date within a provider object")
    common = pset & sset
    primary_only = sorted(pset - sset)
    secondary_only = sorted(sset - pset)

    p_close = _by_date(primary_rows)
    s_close = _by_date(secondary_rows)

    daily: list[dict[str, Any]] = []
    max_abs = Decimal("0")
    nonzero = 0
    over = 0
    for d in sorted(common):
        pc = p_close[d]
        sc = s_close[d]
        diff = abs(pc - sc)
        if diff > max_abs:
            max_abs = diff
        if diff != 0:
            nonzero += 1
        if diff > tolerance:
            over += 1
        daily.append(
            {
                "trade_date": d,
                "primary_close": str(pc),
                "secondary_close": str(sc),
                "abs_difference": str(diff),
            }
        )

    if primary_only or secondary_only:
        raise MarketReconciliationError(
            "date sets disagree: "
            f"primary_only={len(primary_only)} secondary_only={len(secondary_only)}"
        )
    if over:
        raise MarketReconciliationError(
            f"{over} close difference(s) exceed tolerance {tolerance}"
        )

    return {
        "primary_trade_days": len(primary_dates),
        "secondary_trade_days": len(secondary_dates),
        "common_trade_days": len(common),
        "primary_only_dates": primary_only,
        "secondary_only_dates": secondary_only,
        "duplicate_dates": [],
        "daily_comparison": daily,
        "max_abs_difference": str(max_abs),
        "nonzero_difference_count": nonzero,
        "differences_over_tolerance_count": over,
        "tolerance": str(tolerance),
    }


def reconcile_market_close_series(
    primary: dict[str, Any],
    secondary: dict[str, Any],
    *,
    tolerance: Decimal | None = None,
) -> dict[str, Any]:
    """Align two validated objects by exact ``trade_date`` and compare daily (v1).

    v1 contract: preserves the historical output exactly (daily rows carry the
    legacy ``baostock_close`` / ``akshare_close`` labels).  Raises
    :class:`MarketReconciliationError` on any date-set / schema conflict or an
    over-tolerance close.
    """
    if tolerance is None:
        tolerance = close_tolerance_decimal()
    tol = parse_decimal(str(tolerance))

    core = _reconcile_core(primary, secondary, tolerance=tol)
    daily = []
    for r in core["daily_comparison"]:
        daily.append(
            {
                "trade_date": r["trade_date"],
                "baostock_close": r["primary_close"],
                "akshare_close": r["secondary_close"],
                "abs_difference": r["abs_difference"],
            }
        )
    return {
        "primary_trade_days": core["primary_trade_days"],
        "secondary_trade_days": core["secondary_trade_days"],
        "common_trade_days": core["common_trade_days"],
        "primary_only_dates": core["primary_only_dates"],
        "secondary_only_dates": core["secondary_only_dates"],
        "duplicate_dates": [],
        "daily_comparison": daily,
        "max_abs_difference": core["max_abs_difference"],
        "nonzero_difference_count": core["nonzero_difference_count"],
        "differences_over_tolerance_count": core["differences_over_tolerance_count"],
        "tolerance": str(tol),
    }


def reconcile_market_close_series_v2(
    primary: dict[str, Any],
    secondary: dict[str, Any],
    *,
    tolerance: Decimal | None = None,
) -> dict[str, Any]:
    """v2: role-neutral daily labels plus a daily-comparison digest.

    The economic comparison is identical to v1; only the identity contract is
    upgraded (role-neutral labels + ``daily_comparison_digest`` bound into the
    v2 reconciliation digest).
    """
    if tolerance is None:
        tolerance = close_tolerance_decimal()
    tol = parse_decimal(str(tolerance))
    core = _reconcile_core(primary, secondary, tolerance=tol)
    core["daily_comparison_digest"] = canonical_digest(core["daily_comparison"])
    return core


def build_mismatch_ledger(
    reconciliation: dict[str, Any],
    *,
    tolerance: Decimal | None = None,
) -> dict[str, Any]:
    """Project the over-tolerance differences into a standalone mismatch ledger."""
    if tolerance is None:
        tolerance = close_tolerance_decimal()
    tol = parse_decimal(str(tolerance))
    entries: list[dict[str, Any]] = []
    for row in reconciliation.get("daily_comparison", []):
        if Decimal(row["abs_difference"]) > tol:
            entries.append(
                {
                    "trade_date": row["trade_date"],
                    "baostock_close": row["baostock_close"],
                    "akshare_close": row["akshare_close"],
                    "abs_difference": row["abs_difference"],
                    "tolerance": str(tol),
                    "severity": "over_tolerance",
                }
            )
    return {
        "schema": "petrochina_market_close_mismatch_ledger_v1",
        "symbol": SYMBOL,
        "tolerance": str(tol),
        "entry_count": len(entries),
        "entries": entries,
    }


# ── digest + report ────────────────────────────────────────────────────────


def build_reconciliation_digest(
    primary: dict[str, Any],
    secondary: dict[str, Any],
    reconciliation: dict[str, Any],
    *,
    tolerance: Decimal | None = None,
    ledger_digest: str = "",
) -> str:
    """Deterministic digest binding every aspect of the double-source proof.

    Binds both object SHAs, row counts, date range, tolerance, the date-set
    summary, the daily close-comparison summary, the mismatch-ledger digest and
    the reconciliation contract version — never just a few pre-written registry
    fields.
    """
    if tolerance is None:
        tolerance = close_tolerance_decimal()
    daily_summary = {
        "max_abs_difference": reconciliation["max_abs_difference"],
        "nonzero_difference_count": reconciliation["nonzero_difference_count"],
        "differences_over_tolerance_count": reconciliation["differences_over_tolerance_count"],
    }
    payload = {
        "contract_version": RECONCILIATION_CONTRACT_VERSION,
        "symbol": SYMBOL,
        "adjustment": "none",
        "primary_provider": primary["provider"],
        "primary_object_sha256": primary["object_sha256"],
        "primary_row_count": primary["row_count"],
        "primary_date_range": [primary["first_trade_date"], primary["last_trade_date"]],
        "secondary_provider": secondary["provider"],
        "secondary_object_sha256": secondary["object_sha256"],
        "secondary_row_count": secondary["row_count"],
        "secondary_date_range": [secondary["first_trade_date"], secondary["last_trade_date"]],
        "tolerance": str(parse_decimal(str(tolerance))),
        "date_set_summary": {
            "primary_trade_days": reconciliation["primary_trade_days"],
            "secondary_trade_days": reconciliation["secondary_trade_days"],
            "common_trade_days": reconciliation["common_trade_days"],
            "primary_only_dates": reconciliation["primary_only_dates"],
            "secondary_only_dates": reconciliation["secondary_only_dates"],
        },
        "daily_close_comparison_summary": daily_summary,
        "mismatch_ledger_digest": ledger_digest,
    }
    return canonical_digest(payload)


def build_mismatch_ledger_digest(ledger: dict[str, Any]) -> str:
    """SHA-256 of the mismatch ledger's canonical payload (excluding no field)."""
    return canonical_digest(ledger)


def build_reconciliation_report(
    primary: dict[str, Any],
    secondary: dict[str, Any],
    reconciliation: dict[str, Any],
    *,
    tolerance: Decimal | None = None,
    ledger_digest: str = "",
) -> dict[str, Any]:
    """Assemble the committed double-source reconciliation report."""
    if tolerance is None:
        tolerance = close_tolerance_decimal()
    digest = build_reconciliation_digest(
        primary, secondary, reconciliation, tolerance=tolerance, ledger_digest=ledger_digest
    )
    return {
        "schema": "petrochina_market_close_reconciliation_v1",
        "symbol": SYMBOL,
        "adjustment": "none",
        "primary_provider": {
            "provider": primary["provider"],
            "object_sha256": primary["object_sha256"],
            "object_key": primary["object_key"],
            "row_count": primary["row_count"],
            "date_range": [primary["first_trade_date"], primary["last_trade_date"]],
        },
        "secondary_provider": {
            "provider": secondary["provider"],
            "object_sha256": secondary["object_sha256"],
            "object_key": secondary["object_key"],
            "row_count": secondary["row_count"],
            "date_range": [secondary["first_trade_date"], secondary["last_trade_date"]],
        },
        "common_trade_days": reconciliation["common_trade_days"],
        "tolerance": str(parse_decimal(str(tolerance))),
        "max_abs_difference": reconciliation["max_abs_difference"],
        "nonzero_difference_count": reconciliation["nonzero_difference_count"],
        "differences_over_tolerance_count": reconciliation["differences_over_tolerance_count"],
        "primary_only_dates": reconciliation["primary_only_dates"],
        "secondary_only_dates": reconciliation["secondary_only_dates"],
        "mismatch_ledger_digest": ledger_digest,
        "reconciliation_status": STATUS_PASS,
        "reconciliation_digest": digest,
    }


def validate_reconciliation_report(report: dict[str, Any]) -> dict[str, Any]:
    """Validate a committed reconciliation report against the contract."""
    errors: list[str] = []
    if report.get("schema") != "petrochina_market_close_reconciliation_v1":
        errors.append("schema mismatch")
    if report.get("symbol") != SYMBOL:
        errors.append("symbol mismatch")
    if report.get("adjustment") != "none":
        errors.append("adjustment mismatch")
    if report.get("reconciliation_status") != STATUS_PASS:
        errors.append("reconciliation_status not pass")
    # digest must be recomputable from the fields actually present in the report.
    try:
        primary = report.get("primary_provider", {})
        secondary = report.get("secondary_provider", {})
        recomputed = build_reconciliation_digest(
            {
                "provider": primary.get("provider"),
                "object_sha256": primary.get("object_sha256"),
                "row_count": primary.get("row_count"),
                "first_trade_date": primary.get("date_range", [None, None])[0],
                "last_trade_date": primary.get("date_range", [None, None])[1],
            },
            {
                "provider": secondary.get("provider"),
                "object_sha256": secondary.get("object_sha256"),
                "row_count": secondary.get("row_count"),
                "first_trade_date": secondary.get("date_range", [None, None])[0],
                "last_trade_date": secondary.get("date_range", [None, None])[1],
            },
            {
                "max_abs_difference": report.get("max_abs_difference"),
                "nonzero_difference_count": report.get("nonzero_difference_count"),
                "differences_over_tolerance_count": report.get(
                    "differences_over_tolerance_count"
                ),
                "primary_trade_days": report.get("common_trade_days"),
                "secondary_trade_days": report.get("common_trade_days"),
                "common_trade_days": report.get("common_trade_days"),
                "primary_only_dates": report.get("primary_only_dates", []),
                "secondary_only_dates": report.get("secondary_only_dates", []),
            },
            tolerance=report.get("tolerance"),
            ledger_digest=report.get("mismatch_ledger_digest", ""),
        )
        if recomputed != report.get("reconciliation_digest"):
            errors.append("reconciliation_digest mismatch")
    except Exception as exc:  # noqa: BLE001
        errors.append(f"reconciliation_digest not recomputable: {exc}")
    return {"valid": not errors, "errors": errors}


# ── v2 role-bound reconciliation contract ──────────────────────────────────


def build_mismatch_ledger_v2(
    reconciliation: dict[str, Any],
    *,
    tolerance: Decimal | None = None,
) -> dict[str, Any]:
    """v2 mismatch ledger with role-neutral close labels."""
    if tolerance is None:
        tolerance = close_tolerance_decimal()
    tol = parse_decimal(str(tolerance))
    entries: list[dict[str, Any]] = []
    for row in reconciliation.get("daily_comparison", []):
        if Decimal(row["abs_difference"]) > tol:
            entries.append(
                {
                    "trade_date": row["trade_date"],
                    "primary_close": row["primary_close"],
                    "secondary_close": row["secondary_close"],
                    "abs_difference": row["abs_difference"],
                    "tolerance": str(tol),
                    "severity": "over_tolerance",
                }
            )
    return {
        "schema": "petrochina_market_close_mismatch_ledger_v2",
        "symbol": SYMBOL,
        "tolerance": str(tol),
        "entry_count": len(entries),
        "entries": entries,
    }


def build_reconciliation_digest_v2(
    primary: dict[str, Any],
    secondary: dict[str, Any],
    reconciliation: dict[str, Any],
    *,
    tolerance: Decimal | None = None,
    ledger_digest: str = "",
) -> str:
    """v2 deterministic digest binding the provider-role identity and daily proof.

    Binds, per the frozen v2 contract: contract version, symbol, adjustment,
    primary role identity (provider_id / role / underlying_provider / object SHA
    / row count), secondary role identity (provider_id / role / transport_library
    / underlying_provider / endpoint_identity / object SHA / table_digest / row
    count), date range, tolerance, the date-set digest, the daily close comparison
    digest, the daily comparison summary and the mismatch-ledger digest.
    """
    if tolerance is None:
        tolerance = close_tolerance_decimal()
    tol = parse_decimal(str(tolerance))
    date_set_summary = {
        "primary_trade_days": reconciliation["primary_trade_days"],
        "secondary_trade_days": reconciliation["secondary_trade_days"],
        "common_trade_days": reconciliation["common_trade_days"],
        "primary_only_dates": reconciliation["primary_only_dates"],
        "secondary_only_dates": reconciliation["secondary_only_dates"],
    }
    daily_summary = {
        "max_abs_difference": reconciliation["max_abs_difference"],
        "nonzero_difference_count": reconciliation["nonzero_difference_count"],
        "differences_over_tolerance_count": reconciliation["differences_over_tolerance_count"],
    }
    payload = {
        "contract_version": RECONCILIATION_CONTRACT_VERSION_V2,
        "symbol": SYMBOL,
        "adjustment": "none",
        "primary": {
            "provider_id": primary.get("provider_id", primary.get("provider")),
            "provider_role": primary.get("provider_role", "primary"),
            "underlying_provider": primary.get("underlying_provider", ""),
            "object_sha256": primary["object_sha256"],
            "row_count": primary["row_count"],
        },
        "secondary": {
            "provider_id": secondary.get("provider_id", secondary.get("provider")),
            "provider_role": secondary.get("provider_role", "secondary"),
            "transport_library": secondary.get("transport_library", ""),
            "underlying_provider": secondary.get("underlying_provider", ""),
            "endpoint_identity": secondary.get("endpoint_identity", ""),
            "object_sha256": secondary["object_sha256"],
            "table_digest": secondary.get("table_digest", ""),
            "row_count": secondary["row_count"],
        },
        "date_range": [primary["first_trade_date"], primary["last_trade_date"]],
        "tolerance": str(tol),
        "date_set_digest": canonical_digest(date_set_summary),
        "daily_close_comparison_digest": reconciliation.get(
            "daily_comparison_digest", ""
        ),
        "daily_close_comparison_summary": daily_summary,
        "mismatch_ledger_digest": ledger_digest,
    }
    return canonical_digest(payload)


def build_reconciliation_report_v2(
    primary: dict[str, Any],
    secondary: dict[str, Any],
    reconciliation: dict[str, Any],
    *,
    tolerance: Decimal | None = None,
    ledger_digest: str = "",
) -> dict[str, Any]:
    """Assemble the committed v2 double-source reconciliation report."""
    if tolerance is None:
        tolerance = close_tolerance_decimal()
    tol = parse_decimal(str(tolerance))
    digest = build_reconciliation_digest_v2(
        primary, secondary, reconciliation, tolerance=tol, ledger_digest=ledger_digest
    )
    return {
        "schema": "petrochina_market_close_reconciliation_v2",
        "symbol": SYMBOL,
        "adjustment": "none",
        "reconciliation_contract_version": RECONCILIATION_CONTRACT_VERSION_V2,
        "primary_provider": {
            "provider_id": primary.get("provider_id", primary.get("provider")),
            "provider_role": primary.get("provider_role", "primary"),
            "transport_library": primary.get("transport_library", ""),
            "underlying_provider": primary.get("underlying_provider", ""),
            "object_sha256": primary["object_sha256"],
            "object_key": primary["object_key"],
            "row_count": primary["row_count"],
            "date_range": [primary["first_trade_date"], primary["last_trade_date"]],
        },
        "secondary_provider": {
            "provider_id": secondary.get("provider_id", secondary.get("provider")),
            "provider_role": secondary.get("provider_role", "secondary"),
            "transport_library": secondary.get("transport_library", ""),
            "underlying_provider": secondary.get("underlying_provider", ""),
            "endpoint_identity": secondary.get("endpoint_identity", ""),
            "object_sha256": secondary["object_sha256"],
            "table_digest": secondary.get("table_digest", ""),
            "object_key": secondary["object_key"],
            "row_count": secondary["row_count"],
            "date_range": [secondary["first_trade_date"], secondary["last_trade_date"]],
        },
        "common_trade_days": reconciliation["common_trade_days"],
        "tolerance": str(tol),
        "max_abs_difference": reconciliation["max_abs_difference"],
        "nonzero_difference_count": reconciliation["nonzero_difference_count"],
        "differences_over_tolerance_count": reconciliation["differences_over_tolerance_count"],
        "primary_only_dates": reconciliation["primary_only_dates"],
        "secondary_only_dates": reconciliation["secondary_only_dates"],
        "daily_comparison_digest": reconciliation.get("daily_comparison_digest", ""),
        "mismatch_ledger_digest": ledger_digest,
        "reconciliation_status": STATUS_PASS,
        "reconciliation_digest": digest,
    }


def validate_reconciliation_report_v2(report: dict[str, Any]) -> dict[str, Any]:
    """Validate a committed v2 reconciliation report against the contract."""
    errors: list[str] = []
    if report.get("schema") != "petrochina_market_close_reconciliation_v2":
        errors.append("schema mismatch")
    if report.get("symbol") != SYMBOL:
        errors.append("symbol mismatch")
    if report.get("adjustment") != "none":
        errors.append("adjustment mismatch")
    if report.get("reconciliation_status") != STATUS_PASS:
        errors.append("reconciliation_status not pass")
    try:
        primary = report.get("primary_provider", {})
        secondary = report.get("secondary_provider", {})
        recomputed = build_reconciliation_digest_v2(
            {
                "provider_id": primary.get("provider_id"),
                "provider_role": primary.get("provider_role"),
                "underlying_provider": primary.get("underlying_provider"),
                "object_sha256": primary.get("object_sha256"),
                "row_count": primary.get("row_count"),
                "first_trade_date": primary.get("date_range", [None, None])[0],
                "last_trade_date": primary.get("date_range", [None, None])[1],
            },
            {
                "provider_id": secondary.get("provider_id"),
                "provider_role": secondary.get("provider_role"),
                "transport_library": secondary.get("transport_library"),
                "underlying_provider": secondary.get("underlying_provider"),
                "endpoint_identity": secondary.get("endpoint_identity"),
                "object_sha256": secondary.get("object_sha256"),
                "table_digest": secondary.get("table_digest"),
                "row_count": secondary.get("row_count"),
                "first_trade_date": secondary.get("date_range", [None, None])[0],
                "last_trade_date": secondary.get("date_range", [None, None])[1],
            },
            {
                "max_abs_difference": report.get("max_abs_difference"),
                "nonzero_difference_count": report.get("nonzero_difference_count"),
                "differences_over_tolerance_count": report.get(
                    "differences_over_tolerance_count"
                ),
                "primary_trade_days": report.get("common_trade_days"),
                "secondary_trade_days": report.get("common_trade_days"),
                "common_trade_days": report.get("common_trade_days"),
                "primary_only_dates": report.get("primary_only_dates", []),
                "secondary_only_dates": report.get("secondary_only_dates", []),
                "daily_comparison_digest": report.get("daily_comparison_digest", ""),
            },
            tolerance=report.get("tolerance"),
            ledger_digest=report.get("mismatch_ledger_digest", ""),
        )
        if recomputed != report.get("reconciliation_digest"):
            errors.append("reconciliation_digest mismatch")
    except Exception as exc:  # noqa: BLE001
        errors.append(f"reconciliation_digest not recomputable: {exc}")
    return {"valid": not errors, "errors": errors}
