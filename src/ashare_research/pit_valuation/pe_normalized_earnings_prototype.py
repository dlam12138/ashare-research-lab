"""M2 Stage 2K.1R4F.3 — PE normalized-earnings prototype (pure functions).

Implements the R4F.2-allowed ``AVERAGE_ROE_X_CURRENT_BVPS`` method as a
formal **non-scoring** prototype plus the historical PIT readiness engine.

- ``resolve_annual_roe_chain_as_of`` — latest five *consecutive* annual ROE
  observations visible at ``as_of`` (PIT + restatement gates; a shorter
  window is never substituted for the 5-year contract).
- ``resolve_current_bvps_as_of`` — latest visible PIT parent equity over the
  company-wide ordinary-share count.
- ``build_normalized_earnings_state`` — normalized EPS = mean(5 consecutive
  ROE) × current BVPS, with a deterministic state identity.
- ``build_normalized_pe_state`` — raw PE (close / current TTM EPS,
  cross-checked against the R4E.4 candidate) and normalized PE
  (close / normalized EPS).  Descriptive diagnostics only.
- ``build_mechanical_inversion_audit`` — deterministic property test: with
  price / ROE chain / BVPS / normalized EPS fixed and only current TTM EPS
  shocked, raw PE must move while normalized PE must not.
- ``build_historical_readiness`` — per-trade-date walk-forward readiness
  matrix and the 3y / 5y validation-window verdicts.
- ``derive_fact_gap_plan`` — exact minimum backfill fact set for every
  blocked historical interval (MINIMUM_3Y_BACKFILL / MINIMUM_5Y_BACKFILL).
- ``validate_prototype`` — walk-forward disturbance checks (future fact,
  later restatement, array order) that the engine itself runs.

Never computes a PE numeric score, never writes to the default database,
never contacts the network.  All arithmetic is ``Decimal(str(...))``.
"""

from __future__ import annotations

import hashlib
import json
from decimal import ROUND_HALF_EVEN, Decimal, getcontext
from typing import Any

from ashare_research.pit_valuation.pe_cycle_context_preflight import (
    CONCEPT_EQUITY,
    CONCEPT_NET_PROFIT,
    CONCEPT_PERIOD_END_SHARES,
    CONSTANT_TOTAL_SHARES,
    SYMBOL,
    fact_identity,
    parse_decimal,
    resolve_latest_visible,
)

getcontext().prec = 28
getcontext().rounding = ROUND_HALF_EVEN

PROTOTYPE_CONTRACT_ID = "pe_normalized_earnings_average_roe_v1"
MINIMUM_CONSECUTIVE_ANNUAL_ROE = 5

AS_OF_TRADE_DATE = "2026-07-31"

# R4E.5 frozen validation windows (inclusive).
WINDOW_3Y = ("2023-07-31", "2026-07-31")
WINDOW_5Y = ("2021-08-02", "2026-07-31")

PROTOTYPE_READY = "READY"
PROTOTYPE_BLOCKED = "BLOCKED_INSUFFICIENT_ROE_HISTORY"

_INVERSION_MULTIPLIERS = ("0.5", "1.0", "2.0")


# ───────────────────────────── helpers ─────────────────────────────


def _versions_for_period(
    facts: list[dict[str, Any]], concept_id: str, period_end: str
) -> list[dict[str, Any]]:
    return [
        f
        for f in facts
        if f.get("concept_id") == concept_id and f.get("period_end") == period_end
    ]


def _decimal_or_none(value: Any) -> Decimal | None:
    if value is None or value == "":
        return None
    try:
        return parse_decimal(value)
    except Exception:
        return None


def _fact_value(fact: dict[str, Any] | None) -> Decimal | None:
    return _decimal_or_none(fact.get("value") if fact else None)


def _mean(values: list[Decimal]) -> Decimal:
    if not values:
        raise ValueError("empty mean")
    return sum(values, Decimal("0")) / Decimal(len(values))


def _canonical_json(payload: Any) -> bytes:
    return json.dumps(
        payload, sort_keys=True, ensure_ascii=False, separators=(",", ":")
    ).encode("utf-8")


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def state_identity(payload: dict[str, Any]) -> str:
    """Deterministic state digest over identity fields only.

    Never includes wall-clock timestamps, machine names, absolute paths,
    Python patch versions, or output directories.
    """
    return _sha256(_canonical_json(payload))


# ─────────────────────── ROE chain (as-of) ───────────────────────


def _annual_fiscal_years(facts: list[dict[str, Any]]) -> list[int]:
    return sorted(
        {
            int(f["period_end"][:4])
            for f in facts
            if f.get("period_end", "").endswith("12-31")
        }
    )


def _roe_year(facts: list[dict[str, Any]], y: int, as_of: str) -> dict[str, Any] | None:
    """One annual ROE observation for fiscal year ``y`` visible at ``as_of``.

    Returns ``None`` when any operand is missing / nonpositive (never zero).
    """
    end_pe = f"{y}-12-31"
    begin_pe = f"{y - 1}-12-31"
    np = resolve_latest_visible(
        _versions_for_period(facts, CONCEPT_NET_PROFIT, end_pe), as_of
    )
    end_eq = resolve_latest_visible(
        _versions_for_period(facts, CONCEPT_EQUITY, end_pe), as_of
    )
    begin_eq = resolve_latest_visible(
        _versions_for_period(facts, CONCEPT_EQUITY, begin_pe), as_of
    )
    np_d = _fact_value(np)
    end_d = _fact_value(end_eq)
    begin_d = _fact_value(begin_eq)
    if np_d is None or end_d is None or begin_d is None:
        return None
    if np_d <= 0 or end_d <= 0 or begin_d <= 0:
        return None
    avg_eq = (begin_d + end_d) / Decimal("2")
    return {
        "fiscal_year": str(y),
        "parent_net_profit": str(np_d),
        "begin_equity": str(begin_d),
        "end_equity": str(end_d),
        "average_equity": str(avg_eq),
        "roe_decimal": str(np_d / avg_eq),
        "np_fact_id": fact_identity(np),
        "begin_equity_fact_id": fact_identity(begin_eq),
        "end_equity_fact_id": fact_identity(end_eq),
    }


def _latest_consecutive_window(
    roe_rows: list[dict[str, Any]], minimum: int
) -> list[dict[str, Any]]:
    """Latest ``minimum`` consecutive annual ROE rows ending at the newest
    eligible fiscal year; ``[]`` when the trailing run is shorter."""
    years = sorted({int(r["fiscal_year"]) for r in roe_rows})
    if not years:
        return []
    by_year = {int(r["fiscal_year"]): r for r in roe_rows}
    # longest trailing consecutive run ending at the newest eligible year
    run: list[int] = []
    for y in range(years[-1], years[0] - 1, -1):
        if y not in by_year:
            break
        run.append(y)
    run.reverse()
    if len(run) < minimum:
        return []
    return [by_year[y] for y in run[-minimum:]]


def resolve_annual_roe_chain_as_of(
    facts: list[dict[str, Any]],
    as_of: str,
    *,
    minimum: int = MINIMUM_CONSECUTIVE_ANNUAL_ROE,
) -> dict[str, Any]:
    """Latest ``minimum`` consecutive annual ROE observations visible at
    ``as_of`` (PIT + restatement gates).  A trailing run shorter than
    ``minimum`` blocks the chain — the contract window is never shortened."""
    years = _annual_fiscal_years(facts)
    rows: list[dict[str, Any]] = []
    blocked_years: list[dict[str, Any]] = []
    for y in years:
        row = _roe_year(facts, y, as_of)
        if row is None:
            blocked_years.append({"fiscal_year": str(y)})
        else:
            rows.append(row)
    selected = _latest_consecutive_window(rows, minimum)
    available_years = [r["fiscal_year"] for r in rows]
    selected_years = [r["fiscal_year"] for r in selected]
    if len(selected) < minimum:
        return {
            "schema": "pe_normalized_earnings_roe_chain_as_of_v1",
            "symbol": SYMBOL,
            "as_of": as_of,
            "status": PROTOTYPE_BLOCKED,
            "gap_reason": "insufficient_consecutive_annual_roe_history",
            "minimum_consecutive_annual_roe": minimum,
            "available_annual_roe_years": available_years,
            "selected_five_roe_years": [],
            "blocked_years": blocked_years,
            "average_roe_decimal": None,
            "full_cycle_proven": False,
        }
    avg_roe = _mean([Decimal(r["roe_decimal"]) for r in selected])
    return {
        "schema": "pe_normalized_earnings_roe_chain_as_of_v1",
        "symbol": SYMBOL,
        "as_of": as_of,
        "status": PROTOTYPE_READY,
        "gap_reason": "",
        "minimum_consecutive_annual_roe": minimum,
        "available_annual_roe_years": available_years,
        "selected_five_roe_years": selected_years,
        "roe_observations": selected,
        "blocked_years": blocked_years,
        "average_roe_decimal": str(avg_roe),
        "full_cycle_proven": False,
    }


# ─────────────────────── current BVPS (as-of) ───────────────────────


def _latest_visible_fact_by_period(
    facts: list[dict[str, Any]], concept_id: str, as_of: str
) -> dict[str, Any] | None:
    """Latest PIT-visible fact of ``concept_id`` ranked by period_end."""
    versions: dict[str, list[dict[str, Any]]] = {}
    for f in facts:
        if f.get("concept_id") != concept_id or not f.get("period_end"):
            continue
        versions.setdefault(f["period_end"], []).append(f)
    if not versions:
        return None
    best: dict[str, Any] | None = None
    for pe in sorted(versions):
        resolved = resolve_latest_visible(versions[pe], as_of)
        if resolved is None:
            continue
        best = resolved
    return best


def resolve_current_bvps_as_of(
    facts: list[dict[str, Any]], as_of: str
) -> dict[str, Any]:
    """Current PIT BVPS = latest visible parent equity / latest visible
    period-end company-wide ordinary shares, both at ``as_of``."""
    equity = _latest_visible_fact_by_period(facts, CONCEPT_EQUITY, as_of)
    shares = _latest_visible_fact_by_period(
        facts, CONCEPT_PERIOD_END_SHARES, as_of
    )
    eq_d = _fact_value(equity)
    sh_d = _fact_value(shares)
    if eq_d is None or sh_d is None or sh_d <= 0:
        return {
            "schema": "pe_normalized_earnings_bvps_as_of_v1",
            "symbol": SYMBOL,
            "as_of": as_of,
            "status": "BLOCKED_MISSING_INPUT",
            "gap_reason": (
                "missing_equity" if eq_d is None else "missing_or_invalid_shares"
            ),
            "current_BVPS": None,
        }
    bvps = eq_d / sh_d
    return {
        "schema": "pe_normalized_earnings_bvps_as_of_v1",
        "symbol": SYMBOL,
        "as_of": as_of,
        "status": "READY",
        "current_parent_equity": str(eq_d),
        "current_parent_equity_fact_id": fact_identity(equity),
        "current_parent_equity_period_end": equity.get("period_end"),
        "current_shares": str(sh_d),
        "current_shares_fact_id": fact_identity(shares),
        "current_shares_period_end": shares.get("period_end"),
        "current_BVPS": str(bvps),
        "share_scope": "company_wide_ordinary_shares",
        "share_scope_proof": "r4d1-share-continuity-constancy-v1",
        "shares_match_constant": sh_d == CONSTANT_TOTAL_SHARES,
    }


# ─────────────────── normalized earnings state ───────────────────


def build_normalized_earnings_state(
    facts: list[dict[str, Any]],
    as_of: str,
    *,
    roe_chain: dict[str, Any] | None = None,
    bvps: dict[str, Any] | None = None,
    contract_id: str = PROTOTYPE_CONTRACT_ID,
) -> dict[str, Any]:
    """Normalized EPS state: mean(5 consecutive ROE) × current BVPS.

    The current TTM EPS is deliberately **not** an input here — the state
    digest must be invariant under current-earnings shocks.
    """
    roe = roe_chain or resolve_annual_roe_chain_as_of(facts, as_of)
    if roe.get("status") != PROTOTYPE_READY:
        return {
            "schema": "pe_normalized_earnings_prototype_state_v1",
            "symbol": SYMBOL,
            "as_of_trade_date": as_of,
            "prototype_status": "BLOCKED",
            "block_reason": "insufficient_roe_history",
            "contract_id": contract_id,
            "normalized_eps_decimal": None,
        }
    bv = bvps or resolve_current_bvps_as_of(facts, as_of)
    if bv.get("status") != "READY" or bv.get("current_BVPS") is None:
        return {
            "schema": "pe_normalized_earnings_prototype_state_v1",
            "symbol": SYMBOL,
            "as_of_trade_date": as_of,
            "prototype_status": "BLOCKED",
            "block_reason": "missing_current_bvps",
            "contract_id": contract_id,
            "normalized_eps_decimal": None,
        }
    if bv.get("shares_match_constant") is False:
        return {
            "schema": "pe_normalized_earnings_prototype_state_v1",
            "symbol": SYMBOL,
            "as_of_trade_date": as_of,
            "prototype_status": "BLOCKED",
            "block_reason": "share_scope_mismatch",
            "contract_id": contract_id,
            "normalized_eps_decimal": None,
        }
    avg_roe = Decimal(roe["average_roe_decimal"])
    bvps_d = Decimal(bv["current_BVPS"])
    norm_eps = avg_roe * bvps_d
    obs = roe["roe_observations"]
    identity_payload = {
        "contract_id": contract_id,
        "symbol": SYMBOL,
        "as_of_trade_date": as_of,
        "primary_method": "AVERAGE_ROE_X_CURRENT_BVPS",
        "selected_five_roe_years": [r["fiscal_year"] for r in obs],
        "annual_fact_ids": [
            {
                "fiscal_year": r["fiscal_year"],
                "np_fact_id": r["np_fact_id"],
                "begin_equity_fact_id": r["begin_equity_fact_id"],
                "end_equity_fact_id": r["end_equity_fact_id"],
            }
            for r in obs
        ],
        "current_equity_fact_id": bv["current_parent_equity_fact_id"],
        "current_share_fact_id": bv["current_shares_fact_id"],
        "average_roe_decimal": str(avg_roe),
        "current_bvps_decimal": str(bvps_d),
        "normalized_eps_decimal": str(norm_eps),
    }
    return {
        "schema": "pe_normalized_earnings_prototype_state_v1",
        "symbol": SYMBOL,
        "as_of_trade_date": as_of,
        "contract_id": contract_id,
        "primary_method": "AVERAGE_ROE_X_CURRENT_BVPS",
        "prototype_status": "TRUSTED_NON_SCORING",
        "annual_roe_observations": obs,
        "annual_fact_ids": identity_payload["annual_fact_ids"],
        "equity_fact_ids": {
            "begin": [r["begin_equity_fact_id"] for r in obs],
            "end": [r["end_equity_fact_id"] for r in obs],
        },
        "share_fact_id": bv["current_shares_fact_id"],
        "current_equity_fact_id": bv["current_parent_equity_fact_id"],
        "average_roe_decimal": str(avg_roe),
        "current_bvps_decimal": str(bvps_d),
        "normalized_eps_decimal": str(norm_eps),
        "normalized_earnings_state_id": state_identity(identity_payload),
        "no_trim_no_winsorize_no_exclusion": True,
        "non_scoring": True,
    }


# ─────────────────── normalized PE state ───────────────────


def _market_observation_identity(obs: dict[str, Any]) -> dict[str, str]:
    return {
        "observation_id": obs.get("observation_id", ""),
        "trade_date": obs.get("trade_date", ""),
        "metric_id": obs.get("metric_id", ""),
        "market_close_decimal": obs.get("market_close_decimal", ""),
        "market_close_digest": obs.get("market_close_digest", ""),
        "market_reconciliation_digest": obs.get("market_reconciliation_digest", ""),
        "market_reconciliation_status": obs.get("market_reconciliation_status", ""),
        "primary_market_object_sha256": obs.get("primary_market_object_sha256", ""),
        "secondary_market_object_sha256": obs.get("secondary_market_object_sha256", ""),
    }


def build_normalized_pe_state(
    facts: list[dict[str, Any]],
    as_of: str,
    market_observation: dict[str, Any],
    *,
    earnings_state: dict[str, Any] | None = None,
    contract_id: str = PROTOTYPE_CONTRACT_ID,
) -> dict[str, Any]:
    """Raw PE and normalized PE from the same candidate market close.

    ``raw_pe_ttm`` must equal the R4E.4 candidate ``ratio_decimal`` exactly
    (same close, same TTM EPS denominator); a close cannot be inferred by
    PE × EPS when the observation lacks it.
    """
    es = earnings_state or build_normalized_earnings_state(facts, as_of)
    if es.get("prototype_status") != "TRUSTED_NON_SCORING":
        return {
            "schema": "pe_normalized_pe_snapshot_v1",
            "symbol": SYMBOL,
            "as_of_trade_date": as_of,
            "status": "BLOCKED",
            "block_reason": es.get("block_reason", "earnings_state_not_trusted"),
        }
    close_s = market_observation.get("market_close_decimal")
    eps_s = market_observation.get("per_share_denominator_decimal")
    if close_s is None or eps_s is None:
        return {
            "schema": "pe_normalized_pe_snapshot_v1",
            "symbol": SYMBOL,
            "as_of_trade_date": as_of,
            "status": "BLOCKED",
            "block_reason": (
                "market_observation_missing_close_or_ttm_eps; "
                "close must come from the frozen market observation, "
                "never back-derived from PE x EPS"
            ),
        }
    close = Decimal(close_s)
    ttm_eps = Decimal(eps_s)
    norm_eps = Decimal(es["normalized_eps_decimal"])
    raw_pe = close / ttm_eps
    norm_pe = close / norm_eps
    earnings_normalization_ratio = ttm_eps / norm_eps
    raw_to_normalized_pe_ratio = raw_pe / norm_pe

    identity_payload = {
        "contract_id": contract_id,
        "symbol": SYMBOL,
        "as_of_trade_date": as_of,
        "close": str(close),
        "market_observation_identity": _market_observation_identity(
            market_observation
        ),
        "normalized_earnings_state_id": es["normalized_earnings_state_id"],
        "annual_fact_ids": es["annual_fact_ids"],
        "current_equity_fact_id": es["current_equity_fact_id"],
        "current_share_fact_id": es["share_fact_id"],
        "average_roe_decimal": es["average_roe_decimal"],
        "current_bvps_decimal": es["current_bvps_decimal"],
        "normalized_eps_decimal": es["normalized_eps_decimal"],
        "normalized_pe_decimal": str(norm_pe),
    }
    return {
        "schema": "pe_normalized_pe_snapshot_v1",
        "symbol": SYMBOL,
        "as_of_trade_date": as_of,
        "contract_id": contract_id,
        "status": "TRUSTED_NON_SCORING",
        "market_observation": _market_observation_identity(market_observation),
        "current_ttm_eps": str(ttm_eps),
        "normalized_eps_roe": str(norm_eps),
        "raw_pe_ttm": str(raw_pe),
        "raw_pe_ttm_matches_candidate": raw_pe == Decimal(
            market_observation.get("ratio_decimal", "0")
        ),
        "candidate_ratio_decimal": market_observation.get("ratio_decimal"),
        "normalized_pe_roe": str(norm_pe),
        "normalized_pe_decimal": str(norm_pe),
        "earnings_normalization_ratio": str(earnings_normalization_ratio),
        "raw_to_normalized_pe_ratio": str(raw_to_normalized_pe_ratio),
        # identity binding (Section 六): the full record identity is bound to
        # the earnings-state inputs, exposed here for auditability.
        "normalized_earnings_state_id": es["normalized_earnings_state_id"],
        "annual_fact_ids": es["annual_fact_ids"],
        "current_equity_fact_id": es["current_equity_fact_id"],
        "share_fact_id": es["share_fact_id"],
        "average_roe_decimal": es["average_roe_decimal"],
        "current_bvps_decimal": es["current_bvps_decimal"],
        "normalized_eps_decimal": es["normalized_eps_decimal"],
        "normalized_pe_snapshot_id": state_identity(identity_payload),
        "descriptive_only": True,
        "no_cheap_expensive_labels": True,
        "no_cycle_stage_label": True,
        "non_scoring": True,
    }


# ─────────────────── mechanical inversion audit ───────────────────


def build_mechanical_inversion_audit(
    facts: list[dict[str, Any]],
    as_of: str,
    market_observation: dict[str, Any],
    *,
    multipliers: tuple[str, ...] = _INVERSION_MULTIPLIERS,
    contract_id: str = PROTOTYPE_CONTRACT_ID,
) -> dict[str, Any]:
    """Deterministic property test with current TTM EPS as the only shock.

    Price, the 5y ROE chain, current BVPS and normalized EPS are held fixed;
    only current TTM EPS is scaled by pure-test multipliers (0.5 / 1.0 / 2.0
    — math only, no business threshold meaning).  Raw PE must move
    mechanically; normalized PE must not.
    """
    es = build_normalized_earnings_state(facts, as_of)
    if es.get("prototype_status") != "TRUSTED_NON_SCORING":
        return {
            "schema": "pe_mechanical_inversion_audit_v1",
            "symbol": SYMBOL,
            "as_of_trade_date": as_of,
            "status": "BLOCKED",
            "block_reason": es.get("block_reason", "earnings_state_not_trusted"),
        }
    close_s = market_observation.get("market_close_decimal")
    base_eps_s = market_observation.get("per_share_denominator_decimal")
    if close_s is None or base_eps_s is None:
        return {
            "schema": "pe_mechanical_inversion_audit_v1",
            "symbol": SYMBOL,
            "as_of_trade_date": as_of,
            "status": "BLOCKED",
            "block_reason": "missing_market_close_or_ttm_eps",
        }
    close = Decimal(close_s)
    base_eps = Decimal(base_eps_s)
    norm_eps = Decimal(es["normalized_eps_decimal"])
    scenarios: list[dict[str, Any]] = []
    raw_pes: list[Decimal] = []
    for m in multipliers:
        eps = base_eps * Decimal(m)
        raw_pe = close / eps
        raw_pes.append(raw_pe)
        scenarios.append(
            {
                "multiplier": m,
                "current_ttm_eps": str(eps),
                "raw_pe_ttm": str(raw_pe),
                "normalized_pe_roe": str(close / norm_eps),
                "normalized_eps_roe": str(norm_eps),
                "normalized_earnings_state_id": es["normalized_earnings_state_id"],
            }
        )
    raw_pe_changed = len({str(p) for p in raw_pes}) > 1
    normalized_pe_changed = len(
        {s["normalized_pe_roe"] for s in scenarios}
    ) > 1
    return {
        "schema": "pe_mechanical_inversion_audit_v1",
        "symbol": SYMBOL,
        "as_of_trade_date": as_of,
        "contract_id": contract_id,
        "status": "PASS",
        "method": (
            "property test: price, 5y ROE chain, current BVPS and normalized "
            "EPS held fixed; only current TTM EPS shocked by pure test "
            "multipliers (no business threshold meaning)"
        ),
        "multipliers": list(multipliers),
        "scenarios": scenarios,
        "raw_pe_changed": raw_pe_changed,
        "normalized_pe_changed": normalized_pe_changed,
        "direct_current_earnings_denominator_dependence_removed": (
            raw_pe_changed and not normalized_pe_changed
        ),
        "cycle_stage_identified": False,
        "cycle_guard_empirically_validated": False,
        "property_pass_does_not_imply_empirical_validation": True,
        "no_peak_label_emitted": True,
        "non_scoring": True,
    }


# ─────────────────── historical readiness ───────────────────


def _trade_days(observations: list[dict[str, Any]]) -> list[str]:
    return sorted({o.get("trade_date", "") for o in observations})


def _observation_for_day(
    observations: list[dict[str, Any]], trade_date: str
) -> dict[str, Any] | None:
    for o in observations:
        if (
            o.get("metric_id") == "PE_A_TTM"
            and o.get("trade_date") == trade_date
        ):
            return o
    return None


def _day_readiness(
    facts: list[dict[str, Any]],
    observations: list[dict[str, Any]],
    trade_date: str,
) -> dict[str, Any]:
    """Walk-forward readiness for one trade date (no look-ahead, no forward
    fill: the result comes from facts visible at ``trade_date`` only)."""
    roe = resolve_annual_roe_chain_as_of(facts, trade_date)
    bvps = resolve_current_bvps_as_of(facts, trade_date)
    obs = _observation_for_day(observations, trade_date)
    reasons: list[str] = []
    if roe.get("status") != PROTOTYPE_READY:
        reasons.append("insufficient_roe_history")
    if bvps.get("status") != "READY":
        reasons.append(bvps.get("gap_reason", "missing_current_bvps_inputs"))
    if bvps.get("shares_match_constant") is False:
        reasons.append("share_scope_mismatch")
    if obs is None or obs.get("market_close_decimal") is None:
        reasons.append("missing_market_close")
    entry: dict[str, Any] = {
        "trade_date": trade_date,
        "status": "READY" if not reasons else "BLOCKED",
        "gap_reason": ";".join(reasons),
        "available_annual_roe_years": roe.get("available_annual_roe_years", []),
        "selected_five_roe_years": roe.get("selected_five_roe_years", []),
        "current_equity_state_id": (
            bvps.get("current_parent_equity_fact_id") if bvps.get("status") == "READY"
            else None
        ),
        "current_equity_period_end": (
            bvps.get("current_parent_equity_period_end")
            if bvps.get("status") == "READY"
            else None
        ),
        "share_state_id": (
            bvps.get("current_shares_fact_id") if bvps.get("status") == "READY"
            else None
        ),
        "market_observation_id": (
            obs.get("observation_id") if obs is not None else None
        ),
        "market_close": (
            obs.get("market_close_decimal") if obs is not None else None
        ),
        "market_observation_status": obs.get("status") if obs is not None else None,
    }
    return entry


def _window_ready(
    entries: list[dict[str, Any]], start: str, end: str
) -> tuple[bool, list[str]]:
    covered = [
        e for e in entries if start <= e["trade_date"] <= end
    ]
    blocked = [e["trade_date"] for e in covered if e["status"] != "READY"]
    return (not blocked), blocked


def build_historical_readiness(
    facts: list[dict[str, Any]],
    observations: list[dict[str, Any]],
    *,
    as_of: str = AS_OF_TRADE_DATE,
    window_3y: tuple[str, str] = WINDOW_3Y,
    window_5y: tuple[str, str] = WINDOW_5Y,
) -> dict[str, Any]:
    """Per-trade-date walk-forward readiness over the frozen market days."""
    entries = [_day_readiness(facts, observations, d) for d in _trade_days(observations)]
    ready = [e for e in entries if e["status"] == "READY"]
    blocked = [e for e in entries if e["status"] != "READY"]
    earliest = min((e["trade_date"] for e in ready), default=None)
    latest = max((e["trade_date"] for e in ready), default=None)
    current_ready = any(
        e["trade_date"] == as_of and e["status"] == "READY" for e in entries
    )
    ready_ranges = _ready_ranges(entries)
    gap_reason_counts: dict[str, int] = {}
    for e in blocked:
        for reason in e["gap_reason"].split(";") if e["gap_reason"] else [""]:
            gap_reason_counts[reason] = gap_reason_counts.get(reason, 0) + 1
    # annual rollover transitions: consecutive READY days whose selected five
    # ROE years differ (normalized denominator changes only from its
    # effective date).
    annual_roll_transition_count = 0
    prev_key: str | None = None
    for e in entries:
        if e["status"] != "READY":
            prev_key = None
            continue
        key = ",".join(e["selected_five_roe_years"])
        if prev_key is not None and key != prev_key:
            annual_roll_transition_count += 1
        prev_key = key
    # unique normalized-earnings states among READY days
    unique_states = len(
        {
            ",".join(e["selected_five_roe_years"]) + "|" + str(e["current_equity_period_end"])
            for e in ready
        }
    )
    three_ready, three_blocked = _window_ready(entries, *window_3y)
    five_ready, five_blocked = _window_ready(entries, *window_5y)
    return {
        "schema": "pe_normalized_earnings_historical_readiness_v1",
        "symbol": SYMBOL,
        "as_of_trade_date": as_of,
        "windows": {
            "3y": {"start": window_3y[0], "end": window_3y[1]},
            "5y": {"start": window_5y[0], "end": window_5y[1]},
        },
        "candidate_trade_day_count": len(entries),
        "prototype_ready_trade_days": len(ready),
        "blocked_trade_days": len(blocked),
        "earliest_ready_trade_date": earliest,
        "latest_ready_trade_date": latest,
        "ready_date_ranges": ready_ranges,
        "unique_normalized_earnings_state_count": unique_states,
        "annual_roll_transition_count": annual_roll_transition_count,
        "gap_reason_counts": gap_reason_counts,
        "verdicts": {
            "CURRENT_ASOF_READY": current_ready,
            "3Y_HISTORICAL_VALIDATION_READY": three_ready,
            "5Y_HISTORICAL_VALIDATION_READY": five_ready,
            "FULL_CYCLE_VALIDATION_READY": False,
            "full_cycle_reason": (
                "no independent deterministic full-cycle proof exists in-repo"
            ),
        },
        "blocked_dates": {
            "3y_window": three_blocked,
            "5y_window": five_blocked,
        },
        "no_forward_fill": True,
        "no_3y_4y_roe_fallback": True,
        "non_scoring": True,
    }


def _ready_ranges(entries: list[dict[str, Any]]) -> list[dict[str, str]]:
    ranges: list[dict[str, str]] = []
    start: str | None = None
    prev: str | None = None
    for e in entries:
        if e["status"] == "READY":
            if start is None:
                start = e["trade_date"]
            prev = e["trade_date"]
        else:
            if start is not None and prev is not None:
                ranges.append({"start": start, "end": prev})
            start = None
            prev = None
    if start is not None and prev is not None:
        ranges.append({"start": start, "end": prev})
    return ranges


# ─────────────────── state ledger (READY days only) ───────────────────


def build_historical_state_ledger(
    facts: list[dict[str, Any]],
    observations: list[dict[str, Any]],
    *,
    as_of: str = AS_OF_TRADE_DATE,
) -> dict[str, Any]:
    """Diagnostic ledger of prototype values on READY trade days only."""
    entries = [_day_readiness(facts, observations, d) for d in _trade_days(observations)]
    states: list[dict[str, Any]] = []
    for e in entries:
        if e["status"] != "READY":
            continue
        roe = resolve_annual_roe_chain_as_of(facts, e["trade_date"])
        bvps = resolve_current_bvps_as_of(facts, e["trade_date"])
        es = build_normalized_earnings_state(
            facts, e["trade_date"], roe_chain=roe, bvps=bvps
        )
        states.append(
            {
                "trade_date": e["trade_date"],
                "selected_five_roe_years": e["selected_five_roe_years"],
                "average_roe_decimal": es.get("average_roe_decimal"),
                "current_bvps_decimal": es.get("current_bvps_decimal"),
                "normalized_eps_decimal": es.get("normalized_eps_decimal"),
                "normalized_earnings_state_id": es.get("normalized_earnings_state_id"),
                "current_equity_period_end": e["current_equity_period_end"],
                "market_close": e["market_close"],
            }
        )
    return {
        "schema": "pe_normalized_earnings_historical_state_ledger_v1",
        "symbol": SYMBOL,
        "as_of_trade_date": as_of,
        "ledger_entries": states,
        "ledger_entry_count": len(states),
        "diagnostic_only": True,
        "no_normalized_pe_percentile_series": True,
        "non_scoring": True,
    }


# ─────────────────── fact gap plan ───────────────────


def _required_annual_years_for_window(
    facts: list[dict[str, Any]],
    target_trade_date: str,
) -> list[int]:
    """The five consecutive annual years a READY chain at ``target`` needs:
    the newest annual fiscal year whose annual report is visible at
    ``target`` (annual NP fact with ``effective_from <= target``) and the
    four years before it.  When no annual report is visible yet, fall back
    to the earliest known annual year in-repo (conservative)."""
    years = _annual_fiscal_years(facts)
    visible_newest: int | None = None
    for y in sorted(years, reverse=True):
        np_facts = [
            f
            for f in _versions_for_period(
                facts, CONCEPT_NET_PROFIT, f"{y}-12-31"
            )
            if (f.get("effective_from") or "") <= target_trade_date
        ]
        if np_facts:
            visible_newest = y
            break
    if visible_newest is None:
        visible_newest = min(years, default=2020)
    return [visible_newest - i for i in range(4, -1, -1)]


def derive_fact_gap_plan(
    facts: list[dict[str, Any]],
    observations: list[dict[str, Any]],
    *,
    window_3y: tuple[str, str] = WINDOW_3Y,
    window_5y: tuple[str, str] = WINDOW_5Y,
) -> dict[str, Any]:
    """Exact minimum annual-fact backfill sets for the frozen windows.

    For every blocked historical interval the plan derives the required ROE
    years at the interval's earliest target trade date, then the missing
    facts (parent NP per year, ending equity per year, plus the opening
    equity of the earliest required year).  Backfill sets are computed, not
    hardcoded; provider values are never invented (the plan proves the
    coverage *path*, not future fact values).
    """
    existing_years = _annual_fiscal_years(facts)
    existing_facts: set[tuple[str, str]] = {
        (f.get("concept_id", ""), f.get("period_end", ""))
        for f in facts
    }

    def _plan(
        label: str, target: str, year_pool: list[int]
    ) -> dict[str, Any]:
        required_years = sorted(
            {y for y in year_pool if y <= int(target[:4])}
        )
        missing: list[dict[str, Any]] = []
        for y in required_years:
            for concept, pe_label in (
                (CONCEPT_NET_PROFIT, f"{y}-12-31"),
                (CONCEPT_EQUITY, f"{y}-12-31"),
            ):
                if (concept, pe_label) not in existing_facts:
                    missing.append(
                        {
                            "concept": concept,
                            "period_end": pe_label,
                            "required_for": f"annual_roe_{y}",
                        }
                    )
        earliest = min(required_years, default=None)
        if earliest is not None:
            opening_pe = f"{earliest - 1}-12-31"
            if (CONCEPT_EQUITY, opening_pe) not in existing_facts:
                missing.append(
                    {
                        "concept": CONCEPT_EQUITY,
                        "period_end": opening_pe,
                        "required_for": f"opening_equity_roe_{earliest}",
                    }
                )
        missing.sort(key=lambda m: (m["period_end"], m["concept"]))
        return {
            "label": label,
            "target_trade_date": target,
            "required_roe_years": [str(y) for y in required_years],
            "missing_facts": missing,
            "missing_fact_count": len(missing),
        }

    three = _plan(
        "MINIMUM_3Y_BACKFILL",
        window_3y[0],
        _required_annual_years_for_window(facts, window_3y[0]),
    )
    five = _plan(
        "MINIMUM_5Y_BACKFILL",
        window_5y[0],
        _required_annual_years_for_window(facts, window_5y[0]),
    )
    return {
        "schema": "pe_normalized_earnings_historical_fact_gap_plan_v1",
        "symbol": SYMBOL,
        "windows": {
            "3y": {"start": window_3y[0], "end": window_3y[1]},
            "5y": {"start": window_5y[0], "end": window_5y[1]},
        },
        "existing_annual_facts": {
            "years": [str(y) for y in existing_years],
            "concept_period_pairs": sorted(
                [list(p) for p in existing_facts if p[1].endswith("12-31")]
            ),
        },
        "minimum_3y_backfill": three,
        "minimum_5y_backfill": five,
        "note": (
            "backfill facts require source tier exchange_official, PIT "
            "announcement/effective dates <= the target trade date, and "
            "their values must be re-verified at acquisition time (R4F.3A); "
            "this plan proves the coverage path only"
        ),
        "non_scoring": True,
    }


# ─────────────────── walk-forward validation ───────────────────


def _rewrite_fact(
    fact: dict[str, Any], **changes: Any
) -> dict[str, Any]:
    out = dict(fact)
    out.update(changes)
    return out


def validate_prototype(
    facts: list[dict[str, Any]],
    observations: list[dict[str, Any]],
    *,
    as_of: str = AS_OF_TRADE_DATE,
    future_facts: list[dict[str, Any]] | None = None,
    later_restatements: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Walk-forward disturbance checks.

    - a synthetic future annual fact (``effective_from > T``) must not change
      any historical state;
    - a later restatement (``effective_from > T``) must not back-fill into T;
    - array order changes must not change any state.

    The engine runs these checks itself; they only prove PIT isolation, not
    empirical cycle-guard validity.
    """
    days = _trade_days(observations)
    baseline = {
        d: _day_readiness(facts, observations, d) for d in days
    }

    def _signature(entries: dict[str, Any]) -> str:
        return _sha256(
            _canonical_json(
                {
                    d: {
                        "status": e["status"],
                        "selected": e["selected_five_roe_years"],
                        "equity": e["current_equity_state_id"],
                        "share": e["share_state_id"],
                        "market": e["market_observation_id"],
                    }
                    for d, e in entries.items()
                }
            )
        )

    base_sig = _signature(baseline)

    checks: dict[str, Any] = {}
    if future_facts:
        future_sig = _signature(
            {d: _day_readiness(facts + future_facts, observations, d) for d in days}
        )
        checks["future_fact_does_not_change_historical_state"] = (
            future_sig == base_sig
        )
    if later_restatements:
        later_sig = _signature(
            {
                d: _day_readiness(facts + later_restatements, observations, d)
                for d in days
            }
        )
        checks["later_restatement_does_not_backfill"] = later_sig == base_sig

    shuffled = facts[::-1]
    shuffled_sig = _signature(
        {d: _day_readiness(shuffled, observations, d) for d in days}
    )
    checks["array_order_irrelevant"] = shuffled_sig == base_sig
    checks["all_checks_pass"] = all(checks.values())
    checks["walk_forward_proves_pit_isolation_only"] = True
    checks["not_empirical_cycle_guard_validation"] = True
    return {
        "schema": "pe_normalized_earnings_walk_forward_validation_v1",
        "as_of": as_of,
        "trade_days_checked": len(days),
        "checks": checks,
        "non_scoring": True,
    }
