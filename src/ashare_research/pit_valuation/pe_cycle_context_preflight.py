"""M2 Stage 2K.1R4F.2 — PE cycle-context contract preflight (pure functions).

Method preflight / evidence inventory for the PE cycle-context guard.  This
module decides *whether a deterministic PIT-safe normalized-earnings contract
can prevent a mechanically high valuation score when current earnings sit
above sustainable/mid-cycle earnings*.  It never computes a PE numeric score,
never writes to the default database, and never opens the scoring engine.

Gates implemented here, all deterministic and Decimal-only:

- **PIT gate**: a fact is visible at ``as_of`` only when
  ``available_at <= as_of`` and ``effective_from <= as_of``.  Array order
  never decides visibility; a synthetic future fact is excluded by the
  available_at check.
- **Restatement gate**: per report period, versions are ranked by
  ``effective_from`` (backward only); the latest visible version wins.  A
  tie on effective_from is resolved deterministically through the
  ``supersedes_fact_id`` chain; an unresolved tie fails closed
  (``NOT_TRUSTED_RESTATEMENT_AMBIGUITY``).
- **Share-scope gate**: the normalized EPS denominator is the frozen
  company-wide ordinary-share count (R4C/R4D/R4E convention,
  ``CONSTANT_TOTAL_SHARES``); an A-share-only denominator or a wrong share
  date is rejected.
- **ROE gate**: average equity is ``(begin + end) / 2`` per fiscal year,
  ROE is ``parent_np / average_equity``, all in ``Decimal(str(...))``.
  A missing opening-equity fact, or nonpositive equity, blocks that year
  (never treated as zero).
- **Full-cycle gate**: ``full_cycle_coverage_status`` is ``PROVEN`` only
  with deterministic independent evidence; 5 years of data does not
  automatically equal one complete earnings cycle, so the default is
  ``NOT_PROVEN``.
- **Naming gate**: without ``full_cycle_proven`` the historical average EPS
  diagnostic is called ``HISTORICAL_WINDOW_AVERAGE_EPS`` — never
  ``NORMALIZED_FULL_CYCLE_EPS``.
"""

from __future__ import annotations

from decimal import ROUND_HALF_EVEN, Decimal, getcontext
from typing import Any

getcontext().prec = 28
getcontext().rounding = ROUND_HALF_EVEN

# Frozen repo-wide constants (mirror series_contract).
CONSTANT_TOTAL_SHARES = Decimal("183020977818")
AS_OF_TRADE_DATE = "2026-07-31"
SYMBOL = "601857.SH"

# Concept ids from the canonical reported fact bundle.
CONCEPT_NET_PROFIT = "net_profit_attributable_to_parent"
CONCEPT_REVENUE = "revenue"
CONCEPT_EQUITY = "equity_attributable_to_parent"
CONCEPT_PERIOD_END_SHARES = "total_ordinary_shares_at_period_end"
CONCEPT_WEIGHTED_SHARES = "weighted_average_total_ordinary_shares"
CONCEPT_BASIC_EPS = "basic_eps"

# Report-period labels (mirror series_contract).
PERIOD_END_BY_REPORT = {"annual": "12-31", "q1": "03-31"}

# Method option ids (frozen).
OPTION_CURRENT_PE_BINARY_PEAK_FLAG = "CURRENT_PE_WITH_BINARY_PEAK_FLAG"
OPTION_HISTORICAL_AVERAGE_EPS_FULL_CYCLE = "HISTORICAL_AVERAGE_EPS_FULL_CYCLE"
OPTION_AVERAGE_ROE_X_CURRENT_BVPS = "AVERAGE_ROE_X_CURRENT_BVPS"
OPTION_NORMALIZED_MARGIN_X_CURRENT_REVENUE = "NORMALIZED_MARGIN_X_CURRENT_REVENUE"
OPTION_NORMALIZED_COMMODITY_PRICE_MODEL = "NORMALIZED_COMMODITY_PRICE_MODEL"
OPTION_SECTOR_AVERAGE_NORMALIZATION = "SECTOR_AVERAGE_NORMALIZATION"


def parse_decimal(value: Any) -> Decimal:
    """Return ``Decimal(str(value))`` (never Decimal(binary_float))."""
    return Decimal(str(value))


def _sort_key(version: dict[str, Any]) -> tuple[str, str]:
    return (version.get("effective_from") or "", version.get("fact_id") or "")


def visible_versions(
    versions: list[dict[str, Any]], as_of: str
) -> list[dict[str, Any]]:
    """Versions visible at ``as_of``: ``available_at <= as_of`` AND
    ``effective_from <= as_of``, sorted deterministically (array order
    irrelevant)."""
    out = [
        f
        for f in versions
        if (f.get("available_at") or "") <= as_of
        and (f.get("effective_from") or "") <= as_of
    ]
    out.sort(key=_sort_key)
    return out


def resolve_latest_visible(versions: list[dict[str, Any]], as_of: str) -> dict[str, Any] | None:
    """Latest visible version under the restatement gate.

    Among visible versions pick the latest ``effective_from``; a tie is
    broken by ``supersedes_fact_id`` (a version whose supersedes points at a
    sibling visible version wins).  If the tie cannot be resolved uniquely,
    return ``None`` (caller must fail closed, never pick an arbitrary one).
    """
    visible = visible_versions(versions, as_of)
    if not visible:
        return None
    max_eff = max(v.get("effective_from", "") for v in visible)
    latest = [v for v in visible if v.get("effective_from", "") == max_eff]
    if len(latest) == 1:
        return latest[0]
    superseding = [
        v
        for v in latest
        if v.get("supersedes_fact_id")
        and any(v.get("supersedes_fact_id") == g.get("fact_id") for g in latest)
    ]
    if len(superseding) == 1:
        return superseding[0]
    return None


def _fact_value(fact: dict[str, Any] | None) -> Decimal | None:
    if fact is None:
        return None
    raw = fact.get("value")
    if raw is None or raw == "":
        return None
    try:
        return parse_decimal(raw)
    except Exception:
        return None


def _versions_for_period(
    facts: list[dict[str, Any]], concept_id: str, period_end: str
) -> list[dict[str, Any]]:
    return [
        f
        for f in facts
        if f.get("concept_id") == concept_id and f.get("period_end") == period_end
    ]


def fact_identity(fact: dict[str, Any]) -> str:
    return fact.get("fact_id") or fact.get("content_sha256") or "<no-id>"


def fact_source_evidence(fact: dict[str, Any]) -> dict[str, Any]:
    return {
        "source_tier": fact.get("source_tier", ""),
        "source_provider": fact.get("source_provider", ""),
        "source_document": fact.get("source_document", ""),
        "source_page": fact.get("source_page", ""),
        "source_table": fact.get("source_table", ""),
        "source_label": fact.get("source_label", ""),
        "restatement_version": fact.get("restatement_version", ""),
        "supersedes_fact_id": fact.get("supersedes_fact_id"),
        "available_at": fact.get("available_at", ""),
        "effective_from": fact.get("effective_from", ""),
    }


# ─────────────────────────────── Inventory ───────────────────────────────


def build_annual_fact_inventory(
    facts: list[dict[str, Any]], as_of: str
) -> dict[str, Any]:
    """Inventory the PIT-visible annual facts per concept.

    Each entry carries the resolved latest-visible Fact identity (Fact ID,
    Context ID, available_at, effective_from, source tier/evidence,
    restatement status) plus the Decimal value — never just
    ``available=true``.
    """
    concepts = [
        CONCEPT_NET_PROFIT,
        CONCEPT_REVENUE,
        CONCEPT_EQUITY,
        CONCEPT_PERIOD_END_SHARES,
        CONCEPT_WEIGHTED_SHARES,
        CONCEPT_BASIC_EPS,
    ]
    years = sorted({f.get("period_end", "")[:4] for f in facts})
    inventory: list[dict[str, Any]] = []
    period_ends = [f"{y}-12-31" for y in years if f"{y}-12-31"]
    for concept in concepts:
        for period_end in period_ends:
            versions = _versions_for_period(facts, concept, period_end)
            resolved = resolve_latest_visible(versions, as_of)
            value = _fact_value(resolved)
            inventory.append(
                {
                    "concept": concept,
                    "period_end": period_end,
                    "value": str(value) if value is not None else None,
                    "unit": (
                        "CNY"
                        if concept in (CONCEPT_NET_PROFIT, CONCEPT_REVENUE, CONCEPT_EQUITY)
                        else "shares"
                    ),
                    "fact_id": fact_identity(resolved) if resolved else None,
                    "context_id": resolved.get("context_id") if resolved else None,
                    "available_at": resolved.get("available_at") if resolved else None,
                    "effective_from": resolved.get("effective_from") if resolved else None,
                    "source": fact_source_evidence(resolved) if resolved else None,
                    "restatement_status": (
                        resolved.get("restatement_version") if resolved else None
                    ),
                }
            )
    return {
        "schema": "petrochina_pe_cycle_context_input_inventory_v1",
        "symbol": SYMBOL,
        "as_of": as_of,
        "concept_series": inventory,
    }


def build_latest_pit_inventory(
    facts: list[dict[str, Any]], as_of: str
) -> dict[str, Any]:
    """Latest PIT facts (H–K): MRQ parent equity, MRQ share count, TTM
    parent net profit, TTM revenue — each with Fact identity.  The derived
    TTM values carry their input Fact IDs for traceability."""
    mrq_equity = resolve_latest_visible(
        _versions_for_period(facts, CONCEPT_EQUITY, "2026-03-31"), as_of
    )
    mrq_shares = resolve_latest_visible(
        _versions_for_period(facts, CONCEPT_PERIOD_END_SHARES, "2026-03-31"),
        as_of,
    )
    # TTM values from the committed fact chain (cross-validated vs R4E.4)
    ttm_np, ttm_np_inputs = _ttm_net_profit_with_inputs(facts, as_of)
    ttm_rev, ttm_rev_inputs = _ttm_revenue_with_inputs(facts, as_of)

    def _entry(
        label: str, concept: str, fact: dict[str, Any] | None, value: str | None,
        input_fact_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        return {
            "inventory_item": label,
            "concept": concept,
            "value": value,
            "fact_id": fact_identity(fact) if fact else None,
            "context_id": fact.get("context_id") if fact else None,
            "available_at": fact.get("available_at") if fact else None,
            "effective_from": fact.get("effective_from") if fact else None,
            "source": fact_source_evidence(fact) if fact else None,
            "input_fact_ids": input_fact_ids or [],
            "derived": fact is None,
        }

    return {
        "schema": "petrochina_pe_cycle_context_latest_pit_inventory_v1",
        "symbol": SYMBOL,
        "as_of": as_of,
        "items": [
            _entry(
                "H_latest_pit_mrq_parent_equity",
                CONCEPT_EQUITY,
                mrq_equity,
                str(_fact_value(mrq_equity)) if _fact_value(mrq_equity) is not None else None,
            ),
            _entry(
                "I_latest_pit_mrq_share_count",
                CONCEPT_PERIOD_END_SHARES,
                mrq_shares,
                str(_fact_value(mrq_shares)) if _fact_value(mrq_shares) is not None else None,
            ),
            _entry(
                "J_latest_pit_ttm_parent_net_profit",
                CONCEPT_NET_PROFIT,
                None,
                str(ttm_np) if ttm_np is not None else None,
                input_fact_ids=ttm_np_inputs,
            ),
            _entry(
                "K_latest_pit_ttm_revenue",
                CONCEPT_REVENUE,
                None,
                str(ttm_rev) if ttm_rev is not None else None,
                input_fact_ids=ttm_rev_inputs,
            ),
        ],
    }


def _ttm_net_profit(facts: list[dict[str, Any]], as_of: str) -> Decimal | None:
    val, _ = _ttm_net_profit_with_inputs(facts, as_of)
    return val


def _ttm_net_profit_with_inputs(
    facts: list[dict[str, Any]], as_of: str
) -> tuple[Decimal | None, list[str]]:
    """Current PIT TTM parent NP with its three input Fact IDs."""
    annual_years = sorted(
        {
            f.get("period_end", "")[:4]
            for f in facts
            if f.get("period_end", "").endswith("12-31")
        }
    )
    if len(annual_years) < 2:
        return None, []
    y_prev = annual_years[-1]
    y = str(int(y_prev) + 1)
    ann_prev = resolve_latest_visible(
        _versions_for_period(facts, CONCEPT_NET_PROFIT, f"{y_prev}-12-31"), as_of
    )
    q1_prev = resolve_latest_visible(
        _versions_for_period(facts, CONCEPT_NET_PROFIT, f"{y_prev}-03-31"), as_of
    )
    q1_cur = resolve_latest_visible(
        _versions_for_period(facts, CONCEPT_NET_PROFIT, f"{y}-03-31"), as_of
    )
    vals = [_fact_value(x) for x in (ann_prev, q1_prev, q1_cur)]
    if any(v is None for v in vals):
        return None, []
    return (
        vals[0] + vals[2] - vals[1],
        [fact_identity(x) for x in (ann_prev, q1_prev, q1_cur)],
    )


# ─────────────────────────────── ROE chain ───────────────────────────────


def build_annual_roe_chain(
    facts: list[dict[str, Any]], as_of: str
) -> dict[str, Any]:
    """Reconstruct the annual ROE observations under the PIT/restatement gates.

    For each fiscal year with an annual parent NP and both beginning and
    ending parent equity visible at ``as_of``:

        average_equity_y = (begin_equity_y + end_equity_y) / 2
        ROE_y           = parent_np_y / average_equity_y

    All arithmetic is ``Decimal(str(...))``.  A year missing its opening
    equity (or with nonpositive equity / NP) is **not eligible** — it is
    never treated as zero.
    """
    years = sorted(
        {
            f.get("period_end", "")[:4]
            for f in facts
            if f.get("period_end", "").endswith("12-31")
        }
    )
    # collect all annual equity versions per period_end (for begin/end lookup)
    equity_versions: dict[str, list[dict[str, Any]]] = {}
    np_versions: dict[str, list[dict[str, Any]]] = {}
    for f in facts:
        pe = f.get("period_end", "")
        if f.get("concept_id") == CONCEPT_EQUITY and pe:
            equity_versions.setdefault(pe, []).append(f)
        elif f.get("concept_id") == CONCEPT_NET_PROFIT and pe:
            np_versions.setdefault(pe, []).append(f)

    roe_years: list[dict[str, Any]] = []
    blocked: list[dict[str, Any]] = []
    for y in years:
        end_pe = f"{y}-12-31"
        begin_pe = f"{int(y) - 1}-12-31" if int(y) > 0 else ""
        np = resolve_latest_visible(np_versions.get(end_pe, []), as_of)
        end_eq = resolve_latest_visible(equity_versions.get(end_pe, []), as_of)
        begin_eq = (
            resolve_latest_visible(equity_versions.get(begin_pe, []), as_of)
            if begin_pe
            else None
        )
        np_d = _fact_value(np)
        end_d = _fact_value(end_eq)
        begin_d = _fact_value(begin_eq)
        if np_d is None or end_d is None or begin_d is None:
            blocked.append(
                {
                    "fiscal_year": y,
                    "reason": (
                        "missing_opening_equity"
                        if begin_d is None and end_d is not None
                        else "missing_input"
                    ),
                    "np_value": str(np_d) if np_d is not None else None,
                    "end_equity_value": str(end_d) if end_d is not None else None,
                    "begin_equity_value": str(begin_d) if begin_d is not None else None,
                }
            )
            continue
        if begin_d <= 0 or end_d <= 0:
            blocked.append(
                {
                    "fiscal_year": y,
                    "reason": "nonpositive_equity",
                    "end_equity_value": str(end_d),
                    "begin_equity_value": str(begin_d),
                }
            )
            continue
        if np_d <= 0:
            blocked.append(
                {
                    "fiscal_year": y,
                    "reason": "nonpositive_parent_net_profit",
                    "np_value": str(np_d),
                }
            )
            continue
        avg_eq = (begin_d + end_d) / Decimal("2")
        roe = np_d / avg_eq
        roe_years.append(
            {
                "fiscal_year": y,
                "begin_equity": str(begin_d),
                "end_equity": str(end_d),
                "average_equity": str(avg_eq),
                "parent_net_profit": str(np_d),
                "roe_decimal": str(roe),
                "np_fact_id": fact_identity(np),
                "end_equity_fact_id": fact_identity(end_eq),
                "begin_equity_fact_id": fact_identity(begin_eq) if begin_eq else None,
            }
        )

    consecutive = _max_consecutive(roe_years)
    return {
        "schema": "petrochina_pe_normalized_earnings_roe_chain_v1",
        "symbol": SYMBOL,
        "as_of": as_of,
        "eligible_years": [r["fiscal_year"] for r in roe_years],
        "roe_observations": roe_years,
        "blocked_years": blocked,
        "consecutive_annual_roe_observation_count": consecutive,
        "history_coverage_ready": consecutive >= 5,
        "full_cycle_proven": False,
        "full_cycle_proven_evidence": "no_independent_full_cycle_evidence",
        "average_roe_decimal": (
            _mean([Decimal(r["roe_decimal"]) for r in roe_years]) if roe_years else None
        ),
    }


def _max_consecutive(rows: list[dict[str, Any]]) -> int:
    years = sorted({int(r["fiscal_year"]) for r in rows})
    best = cur = 1 if years else 0
    for a, b in zip(years, years[1:], strict=False):
        cur = cur + 1 if b == a + 1 else 1
        best = max(best, cur)
    return best


def _mean(values: list[Decimal]) -> Decimal:
    if not values:
        raise ValueError("empty mean")
    total = sum(values, Decimal("0"))
    return total / Decimal(len(values))


# ─────────────────────────────── BVPS / normalized EPS ───────────────────────────────


def build_current_bvps_and_normalized_eps(
    facts: list[dict[str, Any]], as_of: str, roe_chain: dict[str, Any]
) -> dict[str, Any]:
    """Current PIT BVPS and the ROE-normalized EPS diagnostic.

    current_BVPS       = current PIT parent equity / current PIT period-end shares
    normalized_EPS_ROE = historical_average_roe × current_BVPS
    """
    mrq_equity = resolve_latest_visible(
        _versions_for_period(facts, CONCEPT_EQUITY, "2026-03-31"), as_of
    )
    mrq_shares = resolve_latest_visible(
        _versions_for_period(facts, CONCEPT_PERIOD_END_SHARES, "2026-03-31"), as_of
    )
    # The MRQ period-end share count is the same frozen company-wide constant;
    # fall back to it only when the MRQ share fact is absent from the bundle.
    if mrq_shares is None:
        mrq_shares = {
            "value": str(CONSTANT_TOTAL_SHARES),
            "fact_id": "frozen-constant-r4d1-share-continuity-constancy-v1",
        }
    eq_d = _fact_value(mrq_equity)
    sh_d = _fact_value(mrq_shares)
    if eq_d is None or sh_d is None or sh_d <= 0:
        return {
            "schema": "petrochina_pe_normalized_earnings_bvps_v1",
            "status": "BLOCKED_INSUFFICIENT_INPUT",
            "reason": "missing_current_bvps_operands",
            "current_parent_equity": str(eq_d) if eq_d is not None else None,
            "current_shares": str(sh_d) if sh_d is not None else None,
        }
    bvps = eq_d / sh_d
    avg_roe = roe_chain.get("average_roe_decimal")
    if avg_roe is None:
        return {
            "schema": "petrochina_pe_normalized_earnings_bvps_v1",
            "status": "BLOCKED_NO_AVERAGE_ROE",
            "reason": "average_roe_unavailable",
        }
    norm_eps = avg_roe * bvps
    return {
        "schema": "petrochina_pe_normalized_earnings_bvps_v1",
        "symbol": SYMBOL,
        "as_of": as_of,
        "status": "TRUSTED_NON_SCORING",
        "current_parent_equity": str(eq_d),
        "current_parent_equity_fact_id": fact_identity(mrq_equity),
        "current_shares": str(sh_d),
        "current_shares_fact_id": fact_identity(mrq_shares),
        "current_BVPS": str(bvps),
        "historical_average_roe": str(avg_roe),
        "normalized_EPS_ROE": str(norm_eps),
        "share_scope": "company_wide_ordinary_shares",
        "share_scope_proof": "r4d1-share-continuity-constancy-v1",
    }


# ─────────────────────────────── Historical-window EPS ───────────────────────────────


def build_historical_window_eps_diagnostic(
    facts: list[dict[str, Any]], as_of: str, roe_chain: dict[str, Any]
) -> dict[str, Any]:
    """Historical-window average EPS diagnostic (never full-cycle without proof).

    Uses annual basic EPS when available (official per-share value) and
    parent NP / weighted shares as the reproducible fallback; both are
    reported as separate columns.
    """
    years = roe_chain.get("eligible_years") or []
    rows: list[dict[str, Any]] = []
    eps_values: list[Decimal] = []
    np_shares_values: list[Decimal] = []
    for y in years:
        end_pe = f"{y}-12-31"
        eps = resolve_latest_visible(
            _versions_for_period(facts, CONCEPT_BASIC_EPS, end_pe), as_of
        )
        np = resolve_latest_visible(
            _versions_for_period(facts, CONCEPT_NET_PROFIT, end_pe), as_of
        )
        shares = resolve_latest_visible(
            _versions_for_period(facts, CONCEPT_WEIGHTED_SHARES, end_pe), as_of
        )
        eps_d = _fact_value(eps)
        np_d = _fact_value(np)
        sh_d = _fact_value(shares) if shares else CONSTANT_TOTAL_SHARES
        row: dict[str, Any] = {"fiscal_year": y}
        if eps_d is not None:
            row["basic_eps"] = str(eps_d)
            row["basic_eps_fact_id"] = fact_identity(eps)
            eps_values.append(eps_d)
        if np_d is not None and sh_d is not None and sh_d > 0:
            row["eps_from_np_shares"] = str(np_d / sh_d)
            np_shares_values.append(np_d / sh_d)
        rows.append(row)
    mean_eps = _mean(eps_values) if eps_values else None
    mean_eps_np_shares = _mean(np_shares_values) if np_shares_values else None
    return {
        "schema": "petrochina_pe_historical_window_eps_diagnostic_v1",
        "symbol": SYMBOL,
        "as_of": as_of,
        "history_years": rows,
        "mean_eps_basic": str(mean_eps) if mean_eps is not None else None,
        "mean_eps_from_np_shares": (
            str(mean_eps_np_shares) if mean_eps_np_shares is not None else None
        ),
        "full_cycle_proven": bool(roe_chain.get("full_cycle_proven")),
        "method_label": (
            "NORMALIZED_FULL_CYCLE_EPS" if roe_chain.get("full_cycle_proven")
            else "HISTORICAL_WINDOW_AVERAGE_EPS"
        ),
    }


# ─────────────────────────────── Margin diagnostic ───────────────────────────────


def build_normalized_margin_diagnostic(
    facts: list[dict[str, Any]], as_of: str, roe_chain: dict[str, Any]
) -> dict[str, Any]:
    """Normalized parent-NP margin diagnostic (company-level proxy, not
    operating margin).

        margin_y                = parent_net_profit_y / revenue_y
        historical_average_margin = mean(margin_y)
        normalized_parent_np_margin = historical_average_margin × current_TTM_revenue
        normalized_eps_margin      = normalized_parent_np_margin / share_contract

    Only a diagnostic — never a primary numeric PE denominator.
    """
    years = roe_chain.get("eligible_years") or []
    margins: list[Decimal] = []
    rows: list[dict[str, Any]] = []
    for y in years:
        end_pe = f"{y}-12-31"
        np = resolve_latest_visible(
            _versions_for_period(facts, CONCEPT_NET_PROFIT, end_pe), as_of
        )
        rev = resolve_latest_visible(
            _versions_for_period(facts, CONCEPT_REVENUE, end_pe), as_of
        )
        np_d = _fact_value(np)
        rev_d = _fact_value(rev)
        if np_d is None or rev_d is None or rev_d <= 0:
            rows.append(
                {
                    "fiscal_year": y,
                    "margin": None,
                    "reason": "missing_or_nonpositive_input",
                }
            )
            continue
        margin = np_d / rev_d
        margins.append(margin)
        rows.append(
            {
                "fiscal_year": y,
                "parent_net_profit": str(np_d),
                "revenue": str(rev_d),
                "margin": str(margin),
                "np_fact_id": fact_identity(np),
                "revenue_fact_id": fact_identity(rev),
            }
        )
    avg_margin = _mean(margins) if margins else None
    # current TTM revenue: from the R4E.4 timeline state or the MRQ fact
    ttm_rev = _ttm_revenue(facts, as_of)
    norm_np = avg_margin * ttm_rev if avg_margin is not None and ttm_rev is not None else None
    norm_eps = norm_np / CONSTANT_TOTAL_SHARES if norm_np is not None else None
    return {
        "schema": "petrochina_pe_normalized_margin_diagnostic_v1",
        "symbol": SYMBOL,
        "as_of": as_of,
        "margin_observations": rows,
        "historical_average_margin": str(avg_margin) if avg_margin is not None else None,
        "current_ttm_revenue": str(ttm_rev) if ttm_rev is not None else None,
        "normalized_parent_np_margin": str(norm_np) if norm_np is not None else None,
        "normalized_eps_margin": str(norm_eps) if norm_eps is not None else None,
        "share_contract": str(CONSTANT_TOTAL_SHARES),
        "method_role": "INDEPENDENT_DIAGNOSTIC",
    }


def _ttm_revenue(facts: list[dict[str, Any]], as_of: str) -> Decimal | None:
    val, _ = _ttm_revenue_with_inputs(facts, as_of)
    return val


def _ttm_revenue_with_inputs(
    facts: list[dict[str, Any]], as_of: str
) -> tuple[Decimal | None, list[str]]:
    """Current PIT TTM revenue with its three input Fact IDs.

    TTM revenue = annual(Y-1) + cum(Y,Q1) - cum(Y-1,Q1).
    Y is the current fiscal year at the as-of date (the latest fiscal year
    that has an annual fact plus the following Q1).  All three operands must
    be PIT-visible at ``as_of`` under the restatement gate.
    """
    annual_years = sorted(
        {
            f.get("period_end", "")[:4]
            for f in facts
            if f.get("period_end", "").endswith("12-31")
        }
    )
    if len(annual_years) < 2:
        return None, []
    y_prev = annual_years[-1]
    y = str(int(y_prev) + 1)
    ann_prev = resolve_latest_visible(
        _versions_for_period(facts, CONCEPT_REVENUE, f"{y_prev}-12-31"), as_of
    )
    q1_prev = resolve_latest_visible(
        _versions_for_period(facts, CONCEPT_REVENUE, f"{y_prev}-03-31"), as_of
    )
    q1_cur = resolve_latest_visible(
        _versions_for_period(facts, CONCEPT_REVENUE, f"{y}-03-31"), as_of
    )
    vals = [_fact_value(x) for x in (ann_prev, q1_prev, q1_cur)]
    if any(v is None for v in vals):
        return None, []
    return (
        vals[0] + vals[2] - vals[1],
        [fact_identity(x) for x in (ann_prev, q1_prev, q1_cur)],
    )


# ─────────────────────────────── Method matrix ───────────────────────────────


def build_method_matrix(
    facts: list[dict[str, Any]], as_of: str, roe_chain: dict[str, Any]
) -> dict[str, Any]:
    """Frozen Option A–F matrix with eligibility driven by evidence, never
    by the current PE percentile or by which method would raise/lower the
    score."""
    annual_np_count = len(
        set(
            f.get("period_end", "")[:4]
            for f in facts
            if f.get("concept_id") == CONCEPT_NET_PROFIT
            and (f.get("effective_from") or "") <= as_of
        )
    )
    consecutive = roe_chain.get("consecutive_annual_roe_observation_count", 0)
    full_cycle_proven = bool(roe_chain.get("full_cycle_proven"))
    b_eligibility = (
        "ELIGIBLE" if full_cycle_proven else "BLOCKED_FULL_CYCLE_NOT_PROVEN"
    )
    c_eligibility = (
        "ELIGIBLE_FOR_PROTOTYPE" if consecutive >= 5 else "BLOCKED_INSUFFICIENT_HISTORY"
    )
    d_eligibility = "DIAGNOSTIC_READY" if annual_np_count >= 2 else "BLOCKED"
    options = [
        {
            "option_id": OPTION_CURRENT_PE_BINARY_PEAK_FLAG,
            "conclusion": "REJECT",
            "eligibility": "REJECTED",
            "reason": "threshold arbitrary; single-period YoY cannot define a cycle; "
            "structural growth easily misread as peak; not a mainstream "
            "normalized-earnings method",
        },
        {
            "option_id": OPTION_HISTORICAL_AVERAGE_EPS_FULL_CYCLE,
            "conclusion": "CONDITIONAL",
            "eligibility": b_eligibility,
            "reason": "CFA-recognized normalized-EPS method; eligible only when "
            "full_cycle_coverage_status=PROVEN; a plain 5y average must not be "
            "presented as a full-cycle average",
        },
        {
            "option_id": OPTION_AVERAGE_ROE_X_CURRENT_BVPS,
            "conclusion": "PRIMARY_PROTOTYPE_CANDIDATE",
            "eligibility": c_eligibility,
            "reason": "CFA-recognized; relative normalization reduces scale "
            "distortion as equity base grows; determinism from committed facts; "
            "eligibility decided by the actual ROE chain, not prewritten as pass",
        },
        {
            "option_id": OPTION_NORMALIZED_MARGIN_X_CURRENT_REVENUE,
            "conclusion": "DIAGNOSTIC_ONLY",
            "eligibility": d_eligibility,
            "reason": "margin normalization handles scale but segment mix / tax / "
            "leverage / cost structure can shift; used only for cross-check, "
            "never as the primary numeric PE denominator",
        },
        {
            "option_id": OPTION_NORMALIZED_COMMODITY_PRICE_MODEL,
            "conclusion": "DEFER_REJECT_AS_PRIMARY",
            "eligibility": "DEFERRED_NOT_PRIMARY",
            "reason": "requires choosing a 'normal' oil price; injects the analyst's "
            "commodity view into valuation; needs a new commodity-to-earnings "
            "model; no trusted deterministic mapping in-repo; out of scope",
        },
        {
            "option_id": OPTION_SECTOR_AVERAGE_NORMALIZATION,
            "conclusion": "DEFER",
            "eligibility": "DEFERRED_NOT_AUTHORIZED",
            "reason": "peer acquisition not authorized in this stage",
        },
    ]
    return {
        "schema": "petrochina_pe_normalized_earnings_method_matrix_v1",
        "symbol": SYMBOL,
        "as_of": as_of,
        "selection_rationale": {
            "1_authoritative_methodology_support": (
                "CFA market-based valuation (A/B), Damodaran scale-distortion note"
            ),
            "2_pit_feasibility": "visible committed facts only",
            "3_existing_trusted_fact_coverage": (
                "annual NP/equity/revenue/shares 2020-2025 + MRQ 2026-03-31"
            ),
            "4_scale_robustness": (
                "relative (ROE/margin) preferred over absolute EPS"
            ),
            "5_deterministic_reproducibility": (
                "Decimal(str) only; no float identity"
            ),
            "6_minimal_new_subjective_parameters": (
                "no analyst/consensus/forecast inputs"
            ),
            "7_no_peer_dependency": "sector option deferred",
            "8_no_commodity_price_forecast": "commodity option deferred",
            "9_compatible_share_equity_scope": "company-wide ordinary shares (r4d1)",
            "10_future_issuer_extensibility": "concept-based fact model",
            "not_used_in_selection": [
                "current_pe_percentile",
                "which_method_raises_or_lowers_pe_score",
            ],
        },
        "options": options,
        "decision_basis": {
            "annual_np_observation_years": annual_np_count,
            "consecutive_annual_roe_observations": consecutive,
            "full_cycle_proven": full_cycle_proven,
        },
    }


# ─────────────────────────────── Diagnostics bundle ───────────────────────────────


def build_diagnostics(
    facts: list[dict[str, Any]],
    as_of: str,
    roe_chain: dict[str, Any],
    *,
    current_pe_a_ttm: str | None = None,
    current_pe_percentile_3y: str | None = None,
    current_pe_percentile_5y: str | None = None,
) -> dict[str, Any]:
    """Assemble the full normalized-earnings diagnostics artifact (non-scoring).

    ``current_pe_a_ttm`` / percentiles are descriptive evidence read from the
    committed R4E.5 percentile profile; they are never used in the method
    selection (Section 十八).
    """
    bvps = build_current_bvps_and_normalized_eps(facts, as_of, roe_chain)
    hist_eps = build_historical_window_eps_diagnostic(facts, as_of, roe_chain)
    margin = build_normalized_margin_diagnostic(facts, as_of, roe_chain)

    # current TTM parent NP / EPS (single TTM entry point)
    ttm_np = _ttm_net_profit(facts, as_of)
    ttm_eps = ttm_np / CONSTANT_TOTAL_SHARES if ttm_np is not None else None

    norm_eps_roe = _decimal_or_none(bvps.get("normalized_EPS_ROE"))
    norm_eps_margin = _decimal_or_none(margin.get("normalized_eps_margin"))
    hist_mean = _decimal_or_none(hist_eps.get("mean_eps_basic"))
    current_eps = _decimal_or_none(str(ttm_eps)) if ttm_eps is not None else None

    context = {}
    if norm_eps_roe is not None and norm_eps_roe > 0 and current_eps is not None:
        context["current_eps_over_roe_normalized_eps"] = str(
            current_eps / norm_eps_roe
        )
    if norm_eps_margin is not None and norm_eps_margin > 0 and current_eps is not None:
        context["current_eps_over_margin_normalized_eps"] = str(
            current_eps / norm_eps_margin
        )

    return {
        "schema": "petrochina_pe_normalized_earnings_diagnostics_v1",
        "symbol": SYMBOL,
        "as_of_trade_date": as_of,
        "non_scoring": True,
        "no_score_computed": True,
        "roe_method": {
            "eligible_years": roe_chain.get("eligible_years"),
            "annual_roe_values": [
                r["roe_decimal"] for r in roe_chain.get("roe_observations", [])
            ],
            "average_roe": (
                str(roe_chain["average_roe_decimal"])
                if roe_chain.get("average_roe_decimal") is not None
                else None
            ),
            "current_parent_equity": bvps.get("current_parent_equity"),
            "current_share_count": bvps.get("current_shares"),
            "current_bvps": bvps.get("current_BVPS"),
            "normalized_eps": bvps.get("normalized_EPS_ROE"),
        },
        "historical_eps_diagnostic": {
            "eligible_years": hist_eps.get("history_years"),
            "average_eps_basic": hist_eps.get("mean_eps_basic"),
            "average_eps_from_np_shares": hist_eps.get("mean_eps_from_np_shares"),
            "full_cycle_proven": hist_eps.get("full_cycle_proven"),
            "method_label": hist_eps.get("method_label"),
        },
        "margin_diagnostic": {
            "eligible_years": margin.get("margin_observations"),
            "average_parent_np_margin": margin.get("historical_average_margin"),
            "current_ttm_revenue": margin.get("current_ttm_revenue"),
            "normalized_parent_np": margin.get("normalized_parent_np_margin"),
            "normalized_eps": margin.get("normalized_eps_margin"),
        },
        "current": {
            "current_ttm_parent_net_profit": str(ttm_np) if ttm_np is not None else None,
            "current_ttm_eps": str(ttm_eps) if ttm_eps is not None else None,
            "current_pe_a_ttm": current_pe_a_ttm,
            "current_pe_percentile_3y": current_pe_percentile_3y,
            "current_pe_percentile_5y": current_pe_percentile_5y,
        },
        "context_ratios": context,
        "method_agreement": _method_agreement(norm_eps_roe, norm_eps_margin, hist_mean),
        "no_arbitrary_peak_threshold": True,
        "no_peak_label": True,
    }


def _decimal_or_none(value: Any) -> Decimal | None:
    if value is None:
        return None
    try:
        return parse_decimal(value)
    except Exception:
        return None


def _method_agreement(
    norm_roe: Decimal | None, norm_margin: Decimal | None, hist_mean: Decimal | None
) -> dict[str, Any]:
    labels = [
        ("roe", norm_roe),
        ("margin", norm_margin),
        ("historical_window_avg", hist_mean),
    ]
    pairs: dict[str, Any] = {}
    for i, (a_name, a) in enumerate(labels):
        for b_name, b in labels[i + 1 :]:
            if a is None or b is None:
                pairs[f"{a_name}_vs_{b_name}"] = None
                continue
            diff = abs(a - b)
            pairs[f"{a_name}_vs_{b_name}"] = {
                "pairwise_absolute_difference": str(diff),
                "pairwise_relative_difference": str(
                    diff / b if b != 0 else None
                ),
            }
    return {"pairs": pairs, "diagnostic_only": True, "no_trust_threshold": True}


# ─────────────────────────────── Decision ───────────────────────────────


def _derive_pit_pass(facts: list[dict[str, Any]], as_of: str) -> bool:
    """PIT gate: no resolved (latest-visible) fact used may be available
    strictly after ``as_of``.  A future-dated synthetic fact would make the
    latest-visible resolution pick it only if it were ``<= as_of``, so we
    verify that every fact that *could* be resolved has ``available_at`` and
    ``effective_from`` not after ``as_of`` — array order never matters."""
    for f in facts:
        if (f.get("available_at") or "") > as_of:
            return False
        if (f.get("effective_from") or "") > as_of:
            return False
    return True


def _derive_restatement_pass(
    facts: list[dict[str, Any]], as_of: str
) -> bool:
    """Restatement gate: every report period with versions must resolve
    uniquely (never ``None`` when versions exist for the concept/period),
    i.e. no ambiguous supersession tie and no unresolved chain."""
    concepts = (
        CONCEPT_NET_PROFIT,
        CONCEPT_REVENUE,
        CONCEPT_EQUITY,
        CONCEPT_PERIOD_END_SHARES,
        CONCEPT_WEIGHTED_SHARES,
        CONCEPT_BASIC_EPS,
    )
    period_ends = sorted(
        {f.get("period_end", "") for f in facts if f.get("period_end", "")}
    )
    for concept in concepts:
        for pe in period_ends:
            versions = _versions_for_period(facts, concept, pe)
            if not versions:
                continue
            resolved = resolve_latest_visible(versions, as_of)
            if resolved is None and any(
                (v.get("available_at") or "") <= as_of for v in versions
            ):
                # versions exist that should be visible but the tie could not
                # be resolved deterministically
                return False
    return True


def _derive_share_scope_pass(facts: list[dict[str, Any]], as_of: str) -> bool:
    """Share-scope gate: current PIT shares equal the frozen company-wide
    ordinary-share constant (R4C/R4D/R4E convention); an A-share-only or
    other scope would differ from ``CONSTANT_TOTAL_SHARES``."""
    mrq_shares = resolve_latest_visible(
        _versions_for_period(facts, CONCEPT_PERIOD_END_SHARES, "2026-03-31"),
        as_of,
    )
    sh_d = _fact_value(mrq_shares) if mrq_shares else None
    if sh_d is None:
        return False
    return sh_d == CONSTANT_TOTAL_SHARES


def merge_fact_bundles(
    reported: list[dict[str, Any]], reconciled: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Merge the reported and reconciled bundles into one fact list.

    Reconciled facts carry the official period-end share counts that are
    absent from the reported bundle (e.g. the 2026-03-31 period-end share
    fact).  PIT visibility is still decided per fact by available_at /
    effective_from, never by bundle or array order.
    """
    return list(reported) + list(reconciled)


def build_decision(
    facts: list[dict[str, Any]],
    as_of: str,
    roe_chain: dict[str, Any],
    bvps: dict[str, Any],
    method_matrix: dict[str, Any],
    *,
    reproducible: bool = True,
    no_score_computed: bool = True,
    r4f1_upstream_trusted: bool = True,
) -> dict[str, Any]:
    """Deterministic decision gate (Section 十九).

    All gates except ``reproducible`` / ``no_score_computed`` /
    ``r4f1_upstream_trusted`` are derived from the actual resolved evidence —
    never prewritten as pass.  Only A (prototype allowed) is produced when
    *all* gates pass.  Any failure lands in B (fact gaps) or C (method
    review gaps) — the decision is driven by evidence, never by which option
    would raise/lower the PE score.
    """
    consecutive = roe_chain.get("consecutive_annual_roe_observation_count", 0)
    avg_roe = roe_chain.get("average_roe_decimal")
    bvps_ok = bvps.get("status") == "TRUSTED_NON_SCORING"
    norm_eps_roe = bvps.get("normalized_EPS_ROE")
    full_cycle_proven = bool(roe_chain.get("full_cycle_proven"))

    gates = {
        "r4f1_upstream_trusted": bool(r4f1_upstream_trusted),
        "pit_pass": _derive_pit_pass(facts, as_of),
        "restatement_pass": _derive_restatement_pass(facts, as_of),
        "share_scope_pass": _derive_share_scope_pass(facts, as_of),
        "reproducible": bool(reproducible),
        "method_review_complete": bool(method_matrix.get("options")),
        "no_score_computed": bool(no_score_computed),
        "consecutive_annual_roe_ge_5": consecutive >= 5,
        "average_roe_available": avg_roe is not None,
        "current_bvps_trusted": bvps_ok,
        "normalized_eps_roe_available": norm_eps_roe is not None,
    }

    all_gates_pass = all(gates.values())
    if all_gates_pass:
        decision = "PE_CYCLE_CONTEXT_NORMALIZED_EARNINGS_PROTOTYPE_ALLOWED"
        verdict = "PASS"
    else:
        failed = [k for k, v in gates.items() if not v]
        fact_gaps = {
            "consecutive_annual_roe_ge_5",
            "average_roe_available",
            "current_bvps_trusted",
            "normalized_eps_roe_available",
            "pit_pass",
            "restatement_pass",
            "share_scope_pass",
        }
        if set(failed).issubset(fact_gaps):
            decision = "PE_CYCLE_CONTEXT_FACT_GAPS_REMAIN"
            verdict = "CONDITIONAL PASS"
        else:
            decision = "PE_CYCLE_CONTEXT_METHOD_REVIEW_GAPS_REMAIN"
            verdict = "CONDITIONAL PASS"
    return {
        "schema": "m2_stage2k1r4f2_decision",
        "version": "1.0",
        "stage": "2K.1R4F.2",
        "decision": decision,
        "verdict": verdict,
        "r4f1_upstream": "TRUSTED" if r4f1_upstream_trusted else "NOT TRUSTED",
        "pe_numeric_scoring_authorized": False,
        "pe_status": "coverage_gap_cycle_context_required",
        "valuation_dimension_status": "insufficient_evidence_cycle_context",
        "production_scoring": "NOT_AUTHORIZED",
        "overall_score": "PROHIBITED",
        "gates": gates,
        "failed_gates": (
            [k for k, v in gates.items() if not v]
            if not all_gates_pass
            else []
        ),
        "evidence": {
            "consecutive_annual_roe_observations": consecutive,
            "full_cycle_proven": full_cycle_proven,
            "average_roe_decimal": str(avg_roe) if avg_roe is not None else None,
            "current_bvps": bvps.get("current_BVPS"),
            "normalized_eps_roe": norm_eps_roe,
        },
        "next_stage": "NORMALIZED_EARNINGS_PROTOTYPE NOT_STARTED",
        "no_score_computed": True,
    }
