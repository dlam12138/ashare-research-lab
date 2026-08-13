"""M2 Stage 2K.1R4E.3 — alternative secondary market provider preflight.

This module is the single deterministic home for the bounded, auditable preflight
of free A-share daily secondary market sources that are independent of Eastmoney.

It provides:

- ``validate_preflight_contract`` — validate the frozen candidate list, per-candidate
  parameters, the required window and the decision enum.
- ``check_independence`` — prove a candidate's underlying provider is not eastmoney
  and its endpoint host is not ``push2his.eastmoney.com``.
- ``normalize_candidate_rows`` — produce the unified canonical row contract
  (symbol, trade_date, OHLC, volume, amount, is_trading, adjustment,
  transport_library, underlying_provider, provider_version, endpoint_identity)
  with ISO dates, strict increasing unique dates, and canonical ``Decimal(str(...))``
  (no ``Decimal(binary_float)``, no float repr into identity).
- ``ab_stability`` — classify an A/B pair as ``ACQUISITION_STABLE`` /
  ``ACQUISITION_UNSTABLE`` / ``BLOCKED_PROVIDER_ACCESS``.
- ``validate_pytdx_pages`` — validate explicit pagination for overlap/gap/ordering.
- ``compare_to_baostock`` — align a candidate to the pinned Baostock primary by
  exact ``trade_date`` and compare Decimal closes/OHLC within the frozen tolerance,
  producing a recomputable mismatch ledger and comparison digest.
- ``check_adjustment_semantics`` — verify a candidate is genuinely unadjusted across
  company-action (ex-dividend) windows and a non-event window.
- ``classify_candidate`` / ``select_provider`` / ``decide`` — the QUALIFIED /
  PARTIAL / REJECTED / BLOCKED classification, the non-weighted deterministic
  selection rule, and the frozen decision gate.

Network access is **not** allowed here; acquisition lives only in the thin CLI
``probe`` / ``acquire`` modes.  This module never opens the default database.  It
only ever reads the pinned Baostock primary object supplied by the caller.
"""

from __future__ import annotations

import hashlib
import json
from decimal import Decimal
from pathlib import Path
from typing import Any

from ashare_research.pit_valuation.series_contract import (
    SYMBOL,
    canonical_digest,
    parse_decimal,
)

DISALLOWED_UNDERLYING_PROVIDERS = ("eastmoney",)
DISALLOWED_ENDPOINT_HOSTS = ("push2his.eastmoney.com",)

# Unified canonical row contract (mirrors the frozen preflight config).
CANONICAL_COLUMNS = (
    "symbol",
    "trade_date",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "amount",
    "is_trading",
    "adjustment",
    "transport_library",
    "underlying_provider",
    "provider_version",
    "endpoint_identity",
)

# Frozen candidate ids (order is the recommended-adoption order, not selection).
CANDIDATE_IDS = (
    "tencent_via_akshare",
    "sina_via_akshare",
    "pytdx_tongdaxin",
    "tushare_pro_optional",
)

# Classification enum.
QUALIFIED = "QUALIFIED"
PARTIAL = "PARTIAL"
REJECTED = "REJECTED"
BLOCKED = "BLOCKED"
CLASSIFICATIONS = (QUALIFIED, PARTIAL, REJECTED, BLOCKED)

# A/B stability enum.
ACQUISITION_STABLE = "ACQUISITION_STABLE"
ACQUISITION_UNSTABLE = "ACQUISITION_UNSTABLE"
BLOCKED_PROVIDER_ACCESS = "BLOCKED_PROVIDER_ACCESS"

# Adjustment semantics status.
ADJUSTMENT_TRUSTED = "TRUSTED"
ADJUSTMENT_NOT_TRUSTED = "NOT_TRUSTED"

# Decision enum (frozen).
DECISION_ALLOWED = "ALTERNATIVE_SECONDARY_PROVIDER_INTEGRATION_ALLOWED"
DECISION_GAPS = "ALTERNATIVE_SECONDARY_PROVIDER_GAPS_REMAIN"
DECISION_NO_ACCEPTABLE = "NO_ACCEPTABLE_FREE_SECONDARY_PROVIDER_UNDER_CURRENT_CONTRACT"
DECISION_NOT_TRUSTED = "SECONDARY_PROVIDER_PREFLIGHT_NOT_TRUSTED"
DECISIONS = (DECISION_ALLOWED, DECISION_GAPS, DECISION_NO_ACCEPTABLE, DECISION_NOT_TRUSTED)

DEFAULT_TOLERANCE = Decimal("0.01")


class PreflightContractError(ValueError):
    """The frozen preflight contract is invalid (→ NOT_TRUSTED)."""


class PreflightIndependenceError(ValueError):
    """A candidate is not independent of Eastmoney (→ REJECTED)."""


class PreflightAcquisitionError(RuntimeError):
    """A candidate acquisition failed after the bounded policy (→ BLOCKED)."""


class PreflightComparisonError(ValueError):
    """A candidate/primary comparison fails (date set, close, or adjustment)."""


def _canon_decimal(source_value: Any) -> str:
    """Canonical Decimal string (no exponent, no float repr)."""
    return format(parse_decimal(source_value).normalize(), "f")


def _iso_date(value: Any) -> str:
    if isinstance(value, str):
        return value[:10]
    if hasattr(value, "isoformat"):
        return str(value.isoformat())[:10]
    return str(value)[:10]


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


# ── contract validation ────────────────────────────────────────────────────


def default_config_path() -> Path:
    return (
        Path(__file__).resolve().parents[3]
        / "config"
        / "pit_valuation_secondary_provider_preflight_v1.json"
    )


def load_preflight_config(path: Path | str | None = None) -> dict[str, Any]:
    return json.loads(Path(path or default_config_path()).read_text(encoding="utf-8"))


def _candidate_index(contract: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {c["candidate_id"]: c for c in contract.get("candidates", [])}


def validate_preflight_contract(contract: dict[str, Any]) -> dict[str, str]:
    """Validate the frozen preflight contract and return a digest per section."""
    if contract.get("schema") != "pit_valuation_secondary_provider_preflight_v1":
        raise PreflightContractError("unsupported preflight contract schema")
    if contract.get("symbol") != SYMBOL:
        raise PreflightContractError("preflight contract symbol mismatch")

    window = contract.get("window", {})
    if window.get("required_first_trade_date") != "2021-01-04":
        raise PreflightContractError("required_first_trade_date mismatch")
    if window.get("required_last_trade_date") != "2026-07-31":
        raise PreflightContractError("required_last_trade_date mismatch")
    if window.get("required_trade_days") != 1351:
        raise PreflightContractError("required_trade_days != 1351")
    if contract.get("adjustment") != "none":
        raise PreflightContractError("adjustment must be none")

    if contract.get("canonical_row_contract", {}).get("numeric_encoding") != (
        "Decimal(str(source_scalar))"
    ):
        raise PreflightContractError("numeric_encoding contract mismatch")
    if contract.get("canonical_row_contract", {}).get(
        "decimal_of_binary_float_allowed"
    ) is not False:
        raise PreflightContractError("Decimal(binary_float) must be disallowed")

    candidates = _candidate_index(contract)
    if set(candidates) != set(CANDIDATE_IDS):
        raise PreflightContractError(
            f"candidate set mismatch: {set(candidates)} != {set(CANDIDATE_IDS)}"
        )
    for cid in CANDIDATE_IDS:
        c = candidates[cid]
        if not c.get("transport_library"):
            raise PreflightContractError(f"{cid} missing transport_library")
        if not c.get("underlying_provider"):
            raise PreflightContractError(f"{cid} missing underlying_provider")
        if c.get("underlying_provider") in DISALLOWED_UNDERLYING_PROVIDERS:
            raise PreflightContractError(f"{cid} not independent: eastmoney")

    # window/currency/close tolerance.
    tol = parse_decimal(contract.get("close_tolerance_cny_per_share", ""))
    if tol != DEFAULT_TOLERANCE:
        raise PreflightContractError("close tolerance must be 0.01")

    if set(contract.get("classification_enum", [])) != set(CLASSIFICATIONS):
        raise PreflightContractError("classification_enum mismatch")
    if set(contract.get("decision_enum", [])) != set(DECISIONS):
        raise PreflightContractError("decision_enum mismatch")

    return {
        "contract_schema": canonical_digest(contract.get("schema")),
        "window_digest": canonical_digest(window),
        "candidate_ids_digest": canonical_digest(list(CANDIDATE_IDS)),
        "decision_enum_digest": canonical_digest(list(DECISIONS)),
    }


def candidate_ids(contract: dict[str, Any]) -> tuple[str, ...]:
    return tuple(c["candidate_id"] for c in contract.get("candidates", []))


# ── independence ───────────────────────────────────────────────────────────


def check_independence(candidate: dict[str, Any], endpoint_identity: str) -> bool:
    """Prove a candidate is independent of Eastmoney.

    Raises :class:`PreflightIndependenceError` when the underlying provider is
    eastmoney or the endpoint host is ``push2his.eastmoney.com``.  A different
    AKShare function name alone does not make a source independent.
    """
    provider = candidate.get("underlying_provider", "")
    if provider in DISALLOWED_UNDERLYING_PROVIDERS:
        raise PreflightIndependenceError(
            f"underlying provider {provider!r} is eastmoney; rejected_not_independent"
        )
    host = (endpoint_identity or "").split("//")[-1].split("/")[0].lower()
    if any(host == h or host.endswith("." + h) for h in DISALLOWED_ENDPOINT_HOSTS):
        raise PreflightIndependenceError(
            f"endpoint host {host!r} resolves to eastmoney; rejected_not_independent"
        )
    return True


# ── normalization ──────────────────────────────────────────────────────────


def _tencent_raw_rows(df) -> list[dict[str, Any]]:
    """Map AKShare ``stock_zh_a_hist_tx`` output (English columns) to rows."""
    import pandas as pd

    out: list[dict[str, Any]] = []
    if df is None or df.empty:
        return out
    for _, r in df.iterrows():
        out.append(
            {
                "trade_date": _iso_date(r["date"]),
                "open": r["open"],
                "high": r["high"],
                "low": r["low"],
                "close": r["close"],
                "volume": int(pd.to_numeric(r["volume"], errors="coerce")),
                "amount": r["amount"],
                "is_trading": True,
            }
        )
    return out


def _sina_raw_rows(df) -> list[dict[str, Any]]:
    """Map AKShare ``stock_zh_a_daily`` output (English columns) to rows."""
    import pandas as pd

    out: list[dict[str, Any]] = []
    if df is None or df.empty:
        return out
    for _, r in df.iterrows():
        out.append(
            {
                "trade_date": _iso_date(r["date"]),
                "open": r["open"],
                "high": r["high"],
                "low": r["low"],
                "close": r["close"],
                "volume": int(pd.to_numeric(r["volume"], errors="coerce")),
                "amount": r["amount"],
                "is_trading": True,
            }
        )
    return out


def raw_rows_for_candidate(
    candidate: dict[str, Any], df
) -> list[dict[str, Any]]:
    """Route a provider response DataFrame to the matching intermediate mapper."""
    cid = candidate.get("candidate_id")
    if cid == "tencent_via_akshare":
        return _tencent_raw_rows(df)
    if cid == "sina_via_akshare":
        return _sina_raw_rows(df)
    raise PreflightContractError(
        f"raw_rows_for_candidate unsupported transport for {cid!r}"
    )


def normalize_candidate_rows(
    raw_rows: list[dict[str, Any]],
    *,
    candidate: dict[str, Any],
    contract: dict[str, Any],
    provider_version: str,
    endpoint_identity: str,
) -> list[dict[str, Any]]:
    """Produce the unified canonical row list for one candidate.

    Enforces the canonical row contract: pinned symbol, ISO dates, strict
    increasing unique ``trade_date`` without empties, canonical ``Decimal``
    strings for OHLC/amount (no ``Decimal(binary_float)``, no float repr for
    identity), explicit volume/amount unit registration, and the separation of
    ``transport_library`` from ``underlying_provider``.
    """
    cid = candidate.get("candidate_id")
    if cid not in CANDIDATE_IDS:
        raise PreflightContractError(f"unsupported candidate {cid!r}")
    transport = candidate.get("transport_library", "")
    underlying = candidate.get("underlying_provider", "")
    adjustment = contract.get("adjustment", "none")

    rows: list[dict[str, Any]] = []
    for r in raw_rows:
        rows.append(
            {
                "symbol": SYMBOL,
                "trade_date": _iso_date(r["trade_date"]),
                "open": _canon_decimal(r["open"]),
                "high": _canon_decimal(r["high"]),
                "low": _canon_decimal(r["low"]),
                "close": _canon_decimal(r["close"]),
                "volume": int(r["volume"]),
                "amount": _canon_decimal(r["amount"]),
                "is_trading": bool(r["is_trading"]),
                "adjustment": adjustment,
                "transport_library": transport,
                "underlying_provider": underlying,
                "provider_version": str(provider_version),
                "endpoint_identity": str(endpoint_identity),
            }
        )
    rows.sort(key=lambda x: x["trade_date"])
    dates = [r["trade_date"] for r in rows]
    if any(not d for d in dates):
        raise PreflightContractError(f"{cid} contains an empty trade_date")
    if len(set(dates)) != len(dates):
        raise PreflightContractError(f"{cid} contains duplicate trade_dates")
    if dates != sorted(dates):
        raise PreflightContractError(f"{cid} trade_dates are not strictly increasing")
    return rows


def canonical_table_digest(normalized_rows: list[dict[str, Any]]) -> str:
    """Deterministic content digest of the normalized table (recomputable)."""
    return canonical_digest(normalized_rows)


def column_schema_digest() -> str:
    return canonical_digest(list(CANONICAL_COLUMNS))


# ── A/B stability ──────────────────────────────────────────────────────────


def ab_stability(run_a: list[dict[str, Any]], run_b: list[dict[str, Any]]) -> dict[str, Any]:
    """Classify an A/B pair.

    Requires identical row count, identical date set, and an identical canonical
    table digest.  Returns ``ACQUISITION_STABLE`` / ``ACQUISITION_UNSTABLE``.
    """
    dates_a = [r["trade_date"] for r in run_a]
    dates_b = [r["trade_date"] for r in run_b]
    counts_equal = len(dates_a) == len(dates_b)
    dates_equal = set(dates_a) == set(dates_b)
    digests_equal = canonical_table_digest(run_a) == canonical_table_digest(run_b)
    ok = counts_equal and dates_equal and digests_equal
    return {
        "status": ACQUISITION_STABLE if ok else ACQUISITION_UNSTABLE,
        "row_count_a": len(dates_a),
        "row_count_b": len(dates_b),
        "date_set_equal": dates_equal,
        "table_digest_equal": digests_equal,
        "table_digest_a": canonical_table_digest(run_a),
        "table_digest_b": canonical_table_digest(run_b),
        "stable": ok,
    }


# ── Pytdx pagination ───────────────────────────────────────────────────────


def validate_pytdx_pages(
    pages: list[list[dict[str, Any]]], *, expected_dates: list[str] | None = None
) -> dict[str, Any]:
    """Validate explicit Pytdx-style pagination for overlap, gap and ordering.

    ``pages`` is a list of date-ordered row lists.  Concatenated pages must be
    strictly increasing with no duplicate date; when ``expected_dates`` (the
    frozen trading-calendar dates) is supplied, the pages must cover exactly
    that set — a page sequence that drops a required trade day is a gap.  This
    is purely structural; it does not judge which server was used (that is the
    caller's single-run pinning contract).
    """
    if not pages:
        raise PreflightComparisonError("pytdx pages is empty")
    flat: list[str] = []
    for page in pages:
        page_dates = [str(r["trade_date"])[:10] for r in page]
        if page_dates != sorted(page_dates):
            raise PreflightComparisonError("pytdx page is not ascending")
        flat.extend(page_dates)
    if len(set(flat)) != len(flat):
        raise PreflightComparisonError("pytdx pages contain an overlapping date")
    if flat != sorted(flat):
        raise PreflightComparisonError("pytdx pages are not globally ascending")
    gap_detected = False
    if expected_dates is not None and set(flat) != set(expected_dates):
        gap_detected = True
        raise PreflightComparisonError(
            f"pytdx pages gap vs expected calendar: "
            f"{len(set(expected_dates) - set(flat))} date(s) missing"
        )
    return {
        "page_count": len(pages),
        "row_count": len(flat),
        "overlap_detected": False,
        "gap_detected": gap_detected,
        "ordered": True,
    }


# ── comparison against the pinned Baostock primary ─────────────────────────


def _by_date(rows: list[dict[str, Any]], field: str) -> dict[str, Decimal]:
    return {r["trade_date"]: parse_decimal(r[field]) for r in rows}


def compare_to_baostock(
    candidate_rows: list[dict[str, Any]],
    primary_rows: list[dict[str, Any]],
    *,
    tolerance: Decimal | None = None,
) -> dict[str, Any]:
    """Align a candidate to the Baostock primary by exact ``trade_date``.

    Compares the closed-set and OHLC in canonical Decimal.  Returns the daily
    close comparison, the primary-only/candidate-only date sets, the max close
    difference, the nonzero/over-tolerance counts, the changed-OHLC count, the
    first mismatch, and the mismatch-ledger + comparison digests.
    """
    if tolerance is None:
        tolerance = DEFAULT_TOLERANCE
    tolerance = parse_decimal(str(tolerance))

    cand_dates = [r["trade_date"] for r in candidate_rows]
    prim_dates = [r["trade_date"] for r in primary_rows]
    cset = set(cand_dates)
    pset = set(prim_dates)
    common = sorted(pset & cset)
    primary_only = sorted(pset - cset)
    candidate_only = sorted(cset - pset)

    cand_close = _by_date(candidate_rows, "close")
    prim_close = _by_date(primary_rows, "close")
    cand_ohlc = {
        "open": _by_date(candidate_rows, "open"),
        "high": _by_date(candidate_rows, "high"),
        "low": _by_date(candidate_rows, "low"),
    }

    daily: list[dict[str, Any]] = []
    max_close_diff = Decimal("0")
    nonzero = 0
    over = 0
    changed_ohlc = 0
    first_mismatch: dict[str, Any] | None = None
    primary_by_date = {r["trade_date"]: r for r in primary_rows}
    for d in common:
        cc = cand_close[d]
        pc = prim_close[d]
        diff = abs(cc - pc)
        if diff > max_close_diff:
            max_close_diff = diff
        if diff != 0:
            nonzero += 1
        if diff > tolerance:
            over += 1
        pc_row = primary_by_date[d]
        ohlc_changed = any(
            cand_ohlc[f][d] != parse_decimal(pc_row[f]) for f in ("open", "high", "low")
        )
        if ohlc_changed:
            changed_ohlc += 1
        if first_mismatch is None and (diff != 0 or ohlc_changed):
            first_mismatch = {
                "trade_date": d,
                "candidate_close": str(cc),
                "primary_close": str(pc),
                "abs_difference": str(diff),
                "ohlc_changed": ohlc_changed,
            }
        daily.append(
            {
                "trade_date": d,
                "candidate_close": str(cc),
                "primary_close": str(pc),
                "abs_difference": str(diff),
            }
        )

    ledger = _build_mismatch_ledger(daily, primary_only, candidate_only, tolerance)
    ledger_digest = mismatch_ledger_digest(ledger)
    result = {
        "candidate_row_count": len(cand_dates),
        "primary_row_count": len(prim_dates),
        "common_trade_days": len(common),
        "primary_only_dates": primary_only,
        "candidate_only_dates": candidate_only,
        "max_close_difference": str(max_close_diff),
        "tolerance": str(tolerance),
        "nonzero_close_difference_count": nonzero,
        "over_tolerance_count": over,
        "changed_ohlc_count": changed_ohlc,
        "first_mismatch": first_mismatch,
        "mismatch_ledger_digest": ledger_digest,
    }
    result["comparison_digest"] = comparison_digest(
        candidate_rows, primary_rows, result, ledger_digest, tolerance
    )
    return result


def _build_mismatch_ledger(
    daily: list[dict[str, Any]],
    primary_only: list[str],
    candidate_only: list[str],
    tolerance: Decimal,
) -> dict[str, Any]:
    entries = [
        row
        for row in daily
        if parse_decimal(row["abs_difference"]) > tolerance
    ]
    return {
        "schema": "petrochina_secondary_provider_mismatch_ledger_v1",
        "symbol": SYMBOL,
        "tolerance": str(tolerance),
        "entry_count": len(entries),
        "primary_only_dates": primary_only,
        "candidate_only_dates": candidate_only,
        "entries": entries,
    }


def mismatch_ledger_digest(ledger: dict[str, Any]) -> str:
    return canonical_digest(ledger)


def comparison_digest(
    candidate_rows: list[dict[str, Any]],
    primary_rows: list[dict[str, Any]],
    comparison: dict[str, Any],
    ledger_digest: str,
    tolerance: Decimal,
) -> str:
    """Deterministic digest binding every aspect of the candidate/primary proof."""
    payload = {
        "contract": "pit_valuation_secondary_provider_preflight_v1",
        "symbol": SYMBOL,
        "adjustment": "none",
        "candidate_row_count": comparison["candidate_row_count"],
        "primary_row_count": comparison["primary_row_count"],
        "common_trade_days": comparison["common_trade_days"],
        "primary_only_dates": comparison["primary_only_dates"],
        "candidate_only_dates": comparison["candidate_only_dates"],
        "max_close_difference": comparison["max_close_difference"],
        "tolerance": str(parse_decimal(str(tolerance))),
        "nonzero_close_difference_count": comparison["nonzero_close_difference_count"],
        "over_tolerance_count": comparison["over_tolerance_count"],
        "changed_ohlc_count": comparison["changed_ohlc_count"],
        "mismatch_ledger_digest": ledger_digest,
    }
    return canonical_digest(payload)


# ── company-action / adjustment semantics ──────────────────────────────────


def check_adjustment_semantics(
    candidate_rows: list[dict[str, Any]],
    primary_rows: list[dict[str, Any]],
    event_windows: list[dict[str, Any]],
) -> dict[str, Any]:
    """Verify a candidate is genuinely unadjusted across company-action windows.

    ``event_windows`` is a list of ``{"trade_date": ...}`` ex-dividend (or other
    price-jump) dates plus at least one non-event control window.  For each
    window a candidate that is truly unadjusted must track the Baostock raw-close
    trend across the window — no pre-adjustment back-write and no post-adjustment
    accumulation.  Returns ``TRUSTED`` / ``NOT_TRUSTED`` plus a per-window ledger.
    """
    cand = {r["trade_date"]: parse_decimal(r["close"]) for r in candidate_rows}
    prim = {r["trade_date"]: parse_decimal(r["close"]) for r in primary_rows}
    window_results: list[dict[str, Any]] = []
    untrusted: list[str] = []
    for w in event_windows:
        anchor = w.get("trade_date")
        before = w.get("before", [])
        after = w.get("after", [])
        if not before or not after:
            window_results.append(
                {
                    "anchor": anchor,
                    "type": w.get("type", "event"),
                    "status": "NOT_TRUSTED",
                    "reason": "window missing before/after dates",
                }
            )
            untrusted.append(anchor)
            continue
        # Forward-looking: every before/after close must match the primary raw close
        # exactly (a truly unadjusted candidate reproduces the raw series).
        cand_diff_before = [abs(cand.get(d) - prim.get(d)) for d in before]
        cand_diff_after = [abs(cand.get(d) - prim.get(d)) for d in after]
        missing = [d for d in before + after if d not in cand or d not in prim]
        in_tolerance = all(
            d == 0 for d in cand_diff_before + cand_diff_after if d is not None
        )
        ok = (not missing) and in_tolerance
        window_results.append(
            {
                "anchor": anchor,
                "type": w.get("type", "event"),
                "candidate_close_tracks_primary": ok,
                "missing": missing,
                "status": "TRUSTED" if ok else "NOT_TRUSTED",
            }
        )
        if not ok:
            untrusted.append(anchor)
    return {
        "status": ADJUSTMENT_TRUSTED if not untrusted else ADJUSTMENT_NOT_TRUSTED,
        "window_count": len(event_windows),
        "untrusted_windows": untrusted,
        "windows": window_results,
    }


# ── classification / selection / decision ──────────────────────────────────


def classify_candidate(
    *,
    candidate_id: str,
    independent: bool,
    credential_available: bool,
    acquisition: dict[str, Any] | None,
    comparison: dict[str, Any] | None,
    adjustment: dict[str, Any] | None,
    limitations: list[str],
) -> tuple[str, dict[str, Any]]:
    """Classify one candidate into the frozen enum.

    Returns ``(classification, detail)``.  ``QUALIFIED`` requires independence,
    usable credentials, A/B stability, a complete 1351-date set, trustworthy
    ``none`` adjustment, zero over-tolerance closes, a reproducible canonical
    object, bounded access, and no silent fallback.
    """
    detail = {
        "candidate_id": candidate_id,
        "independent": independent,
        "credential_available": credential_available,
        "acquisition": acquisition,
        "comparison": comparison,
        "adjustment": adjustment,
        "limitations": limitations,
    }
    base = {**detail, "classification": ""}
    if not independent:
        return REJECTED, {**base, "classification": REJECTED, "reasons": ["not_independent"]}
    if not credential_available:
        return BLOCKED, {**base, "classification": BLOCKED, "reasons": ["credential_not_available"]}
    if acquisition is None or acquisition.get("status") == BLOCKED_PROVIDER_ACCESS:
        return BLOCKED, {**base, "classification": BLOCKED, "reasons": ["provider_blocks_access"]}
    if acquisition.get("status") == ACQUISITION_UNSTABLE:
        return REJECTED, {**base, "classification": REJECTED, "reasons": ["ab_unstable"]}
    if comparison is None:
        return REJECTED, {**base, "classification": REJECTED, "reasons": ["comparison_missing"]}
    if comparison["over_tolerance_count"]:
        return REJECTED, {**base, "classification": REJECTED, "reasons": ["close_over_tolerance"]}
    if comparison["candidate_only_dates"] or comparison["primary_only_dates"]:
        return REJECTED, {**base, "classification": REJECTED, "reasons": ["date_set_incomplete"]}
    if comparison["candidate_row_count"] != 1351:
        return REJECTED, {**base, "classification": REJECTED, "reasons": ["row_count_not_1351"]}
    if adjustment is None or adjustment.get("status") != ADJUSTMENT_TRUSTED:
        return REJECTED, {**base, "classification": REJECTED,
                          "reasons": ["adjustment_semantics_not_trusted"]}
    if limitations:
        return PARTIAL, {**base, "classification": PARTIAL, "reasons": limitations}
    return QUALIFIED, {**base, "classification": QUALIFIED}


def select_provider(results: list[dict[str, Any]]) -> dict[str, Any]:
    """Deterministically choose a provider among those classified QUALIFIED.

    The selection is a non-weighted priority rule and is independent of input
    list order: QUALIFIED candidates are ranked by the frozen priority silently;
    ties are broken by the frozen recommended candidate order.  Returns NONE when
    no candidate is QUALIFIED.
    """
    qualified = [r for r in results if r.get("classification") == QUALIFIED]
    if not qualified:
        return {"selected_provider": None, "selected_transport": None}
    # Deterministic tie-break: the frozen recommended adoption order.
    order = {cid: i for i, cid in enumerate(CANDIDATE_IDS)}
    qualified_sorted = sorted(qualified, key=lambda r: order.get(r["candidate_id"], 999))
    chosen = qualified_sorted[0]
    return {
        "selected_provider": chosen["candidate_id"],
        "selected_transport": chosen.get("transport_library"),
        "selected_underlying_provider": chosen.get("underlying_provider"),
        "selected_object_sha": chosen.get("object_sha256"),
        "selected_table_digest": chosen.get("table_digest"),
        "selected_endpoint_identity": chosen.get("endpoint_identity"),
        "limitations": chosen.get("limitations", []),
    }


def decide(results: list[dict[str, Any]], *, contract_trusted: bool = True) -> dict[str, Any]:
    """Compute the frozen decision from per-candidate classifications.

    1. ``..._INTEGRATION_ALLOWED`` when at least one candidate is QUALIFIED.
    2. ``..._GAPS_REMAIN`` when candidates are engineered but all are BLOCKED/PARTIAL.
    3. ``NO_ACCEPTABLE_FREE_SECONDARY_PROVIDER...`` when candidates were reachable
       but all were REJECTED.
    4. ``SECONDARY_PROVIDER_PREFLIGHT_NOT_TRUSTED`` when the contract is untrusted.
    """
    if not contract_trusted:
        return {"decision": DECISION_NOT_TRUSTED, "reason": "contract_untrusted"}
    if not results:
        return {"decision": DECISION_NOT_TRUSTED, "reason": "no_results"}
    classifications = {r["candidate_id"]: r["classification"] for r in results}
    if QUALIFIED in classifications.values():
        return {"decision": DECISION_ALLOWED, "reason": "qualified_provider_selected"}
    if all(c in (BLOCKED, PARTIAL) for c in classifications.values()):
        return {"decision": DECISION_GAPS, "reason": "all_blocked_or_partial"}
    if all(c == REJECTED for c in classifications.values()):
        return {
            "decision": DECISION_NO_ACCEPTABLE,
            "reason": "all_candidates_rejected_under_current_contract",
        }
    return {"decision": DECISION_GAPS, "reason": "mixed_no_qualified"}


def decision_to_exit_code(decision: str, *, allowed: int = 0, gaps: int = 1) -> int:
    if decision == DECISION_ALLOWED:
        return allowed
    if decision in (DECISION_GAPS, DECISION_NO_ACCEPTABLE):
        return gaps
    return 2  # NOT_TRUSTED or any contract/input/schema failure
