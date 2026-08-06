"""M2 Stage 2K.1R4E — PIT-visible financial-state timelines for PE/PB/PS.

Constructs the per-metric financial-state timeline from the reported and
reconciled fact bundles:

- PE_A_TTM: TTM parent net profit states (weighted-average shares = constant).
- PS_A_TTM: TTM revenue states (trade-date-effective shares = constant).
- PB_A_MRQ: latest-visible parent-equity states, each matched to the total
  ordinary shares at the *same* period_end and the same PIT-visible reporting
  context.

Handles supersession and restatement PIT visibility.  Never reads scoring
artifacts and never opens the default database.
"""

from __future__ import annotations

from typing import Any

from ashare_research.pit_valuation.series_contract import (
    METRIC_PB,
    METRIC_PE,
    METRIC_PS,
    SHARE_CONTINUITY_PROOF_ID,
    STATUS_COMPUTED,
    STATUS_UNMATCHED_EQUITY_SHARE,
    canonical_digest,
    parse_decimal,
)
from ashare_research.pit_valuation.ttm import build_ttm_states

PE_FORMULA = "pe-a-ttm-v1"
PB_FORMULA = "pb-a-mrq-v1"
PS_FORMULA = "ps-a-ttm-v1"

CONCEPT_NET_PROFIT = "net_profit_attributable_to_parent"
CONCEPT_REVENUE = "revenue"
CONCEPT_EQUITY = "equity_attributable_to_parent"
CONCEPT_PERIOD_END_SHARES = "total_ordinary_shares_at_period_end"
CONCEPT_WEIGHTED_SHARES = "weighted_average_total_ordinary_shares"


def _state_id(payload: dict[str, Any]) -> str:
    return canonical_digest(payload)


def build_pe_states(reported: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """TTM parent net profit states (PE denominator)."""
    states = build_ttm_states(
        reported,
        CONCEPT_NET_PROFIT,
        metric_id=METRIC_PE,
        formula_id=PE_FORMULA,
    )
    return states


def build_ps_states(reported: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """TTM revenue states (PS denominator)."""
    return build_ttm_states(
        reported,
        CONCEPT_REVENUE,
        metric_id=METRIC_PS,
        formula_id=PS_FORMULA,
    )


def _period_end_shares_facts(
    reported: list[dict[str, Any]],
    reconciled: list[dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    """Map period_end -> list of period-end share Facts (reported + reconciled)."""
    out: dict[str, list[dict[str, Any]]] = {}
    for f in list(reported) + list(reconciled):
        if f.get("concept_id") != CONCEPT_PERIOD_END_SHARES:
            continue
        period_end = f.get("period_end", "")
        if not period_end:
            continue
        out.setdefault(period_end, []).append(f)
    return out


def _select_period_end_share(
    share_facts: list[dict[str, Any]],
    effective_from: str,
) -> dict[str, Any] | None:
    """Deterministically select the PIT-visible share Fact for an equity version.

    A share Fact is visible at ``effective_from`` only when its own
    ``effective_from <= effective_from`` (backward only).  Among visible
    versions pick the latest ``effective_from``; a tie is resolved by
    supersession (a version whose ``supersedes_fact_id`` points at a sibling
    visible version wins).  Never relies on list order; if the tie cannot be
    resolved uniquely it fails closed (raises).
    """
    if not share_facts:
        return None
    visible = [
        f for f in share_facts
        if f.get("effective_from", "") and f.get("effective_from", "") <= effective_from
    ]
    if not visible:
        return None
    max_eff = max(f.get("effective_from", "") for f in visible)
    latest = [f for f in visible if f.get("effective_from", "") == max_eff]
    if len(latest) == 1:
        return latest[0]
    # Multiple versions share the same effective_from: resolve by supersession.
    superseding = [
        f for f in latest
        if f.get("supersedes_fact_id")
        and any(f.get("supersedes_fact_id") == g.get("fact_id") for g in latest)
    ]
    if len(superseding) == 1:
        return superseding[0]
    raise ValueError(
        f"cannot uniquely select period-end share Fact at effective_from "
        f"{effective_from} (candidates: {[f.get('fact_id','') for f in latest]})"
    )


def build_pb_states(
    reported: list[dict[str, Any]],
    reconciled: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """MRQ parent-equity states (PB denominator), share-matched by period_end.

    Every PB state binds the *complete* equity + period-end-share input Facts:
    ``equity_fact_id``, ``period_end_shares_fact_id``, ``input_fact_ids``
    (both, sorted), both inputs' ``available_at``/``effective_from``,
    ``available_at_max`` and ``effective_from`` as the maximum of the two
    inputs, the same ``period_end``, the same PIT-visible reporting context,
    and the share-continuity proof id.  When the share Fact is not yet
    PIT-visible at the equity's effective_from the state is not made effective
    early: it is ``unmatched_equity_share_context``.
    """
    equity_facts = [f for f in reported if f.get("concept_id") == CONCEPT_EQUITY]
    shares_by_period_end = _period_end_shares_facts(reported, reconciled)

    equity_by_period: dict[str, list[dict[str, Any]]] = {}
    for f in equity_facts:
        equity_by_period.setdefault(f.get("period_end", ""), []).append(f)
    for vers in equity_by_period.values():
        vers.sort(key=lambda f: (f.get("effective_from", ""), f.get("fact_id", "")))

    states: list[dict[str, Any]] = []
    for period_end, versions in equity_by_period.items():
        year = int(period_end[:4])
        share_facts = shares_by_period_end.get(period_end, [])
        for version in versions:
            equity_fact_id = version.get("fact_id", "")
            equity_eff = version.get("effective_from", "")
            equity_avail = version.get("available_at", "")
            value = parse_decimal(version["value"])

            share = _select_period_end_share(share_facts, equity_eff)
            matched = share is not None
            status = STATUS_COMPUTED if matched else STATUS_UNMATCHED_EQUITY_SHARE
            share_fact_id = share.get("fact_id", "") if matched else ""
            share_eff = share.get("effective_from", "") if matched else ""
            share_avail = share.get("available_at", "") if matched else ""
            input_fact_ids = sorted(fid for fid in (equity_fact_id, share_fact_id) if fid)
            effective_from = max(equity_eff, share_eff) if matched else equity_eff
            available_at_max = max(equity_avail, share_avail) if matched else equity_avail

            core = {
                "metric_id": METRIC_PB,
                "state_type": "mrq",
                "concept": "parent_equity",
                "fiscal_year": year,
                "report_type": _report_type_from_period_end(period_end),
                "period_end": period_end,
                "effective_from": effective_from,
                "value_decimal": str(value),
                "status": status,
                "formula_id": PB_FORMULA,
                "formula_version": 1,
                "input_fact_ids": input_fact_ids,
                "equity_fact_id": equity_fact_id,
                "equity_available_at": equity_avail,
                "equity_effective_from": equity_eff,
                "period_end_shares_fact_id": share_fact_id,
                "period_end_shares_available_at": share_avail,
                "period_end_shares_effective_from": share_eff,
                "restatement_version": version.get("restatement_version", ""),
                "available_at": version.get("available_at", ""),
                "available_at_max": available_at_max,
                "period_end_shares_decimal": (
                    None if share is None else str(parse_decimal(share["value"]))
                ),
                "share_continuity_proof_id": SHARE_CONTINUITY_PROOF_ID,
            }
            state_id = _state_id(core)
            states.append({"financial_state_id": state_id, **core, "state_digest": state_id})
    states.sort(key=lambda s: s["effective_from"])
    return states


def _report_type_from_period_end(period_end: str) -> str:
    return {
        "03-31": "q1",
        "06-30": "half_year",
        "09-30": "q3",
        "12-31": "annual",
    }.get(period_end[5:], "")


def build_financial_state_timelines(
    reported: list[dict[str, Any]],
    reconciled: list[dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    """Build the PE/PB/PS state timelines and a summary."""
    pe = build_pe_states(reported)
    pb = build_pb_states(reported, reconciled)
    ps = build_ps_states(reported)
    return {METRIC_PE: pe, METRIC_PB: pb, METRIC_PS: ps}


def state_timeline_summary(timelines: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    return {
        metric: {
            "state_count": len(states),
            "computed_count": sum(1 for s in states if s["status"] == STATUS_COMPUTED),
            "missing_ttm_input_count": sum(
                1 for s in states if s["status"] == "missing_ttm_input"
            ),
            "first_effective_from": states[0]["effective_from"] if states else "",
            "last_effective_from": states[-1]["effective_from"] if states else "",
        }
        for metric, states in timelines.items()
    }
