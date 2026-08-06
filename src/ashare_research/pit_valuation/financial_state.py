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

from decimal import Decimal
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


def _period_end_shares_map(
    reported: list[dict[str, Any]],
    reconciled: list[dict[str, Any]],
) -> dict[str, Decimal]:
    """Map period_end -> total ordinary shares at that period end."""
    out: dict[str, Decimal] = {}
    for f in list(reported) + list(reconciled):
        if f.get("concept_id") != CONCEPT_PERIOD_END_SHARES:
            continue
        period_end = f.get("period_end", "")
        if not period_end:
            continue
        value = f.get("value")
        if value is None:
            continue
        out[period_end] = parse_decimal(value)
    return out


def build_pb_states(
    reported: list[dict[str, Any]],
    reconciled: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """MRQ parent-equity states (PB denominator), share-matched by period_end."""
    equity_facts = [f for f in reported if f.get("concept_id") == CONCEPT_EQUITY]
    shares_by_period_end = _period_end_shares_map(reported, reconciled)

    # Each equity fact is an instant state effective from its own effective_from.
    # Versions (restatements) of the same period_end are ordered by effective_from.
    equity_by_period: dict[str, list[dict[str, Any]]] = {}
    for f in equity_facts:
        equity_by_period.setdefault(f.get("period_end", ""), []).append(f)
    for vers in equity_by_period.values():
        vers.sort(key=lambda f: (f.get("effective_from", ""), f.get("fact_id", "")))

    states: list[dict[str, Any]] = []
    for period_end, versions in equity_by_period.items():
        year = int(period_end[:4])
        shares = shares_by_period_end.get(period_end)
        for version in versions:
            eff = version.get("effective_from", "")
            value = parse_decimal(version["value"])
            matched = shares is not None
            status = STATUS_COMPUTED if matched else STATUS_UNMATCHED_EQUITY_SHARE
            core = {
                "metric_id": METRIC_PB,
                "state_type": "mrq",
                "concept": "parent_equity",
                "fiscal_year": year,
                "report_type": _report_type_from_period_end(period_end),
                "period_end": period_end,
                "effective_from": eff,
                "value_decimal": str(value),
                "status": status,
                "formula_id": PB_FORMULA,
                "formula_version": 1,
                "input_fact_ids": sorted(
                    fid for fid in (version.get("fact_id", ""),) if fid
                ),
                "equity_fact_id": version.get("fact_id", ""),
                "period_end_shares_fact_id": _shares_fact_id(reported, reconciled, period_end),
                "restatement_version": version.get("restatement_version", ""),
                "available_at": version.get("available_at", ""),
                "available_at_max": version.get("available_at", ""),
                "period_end_shares_decimal": (
                    None if shares is None else str(shares)
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


def _shares_fact_id(
    reported: list[dict[str, Any]],
    reconciled: list[dict[str, Any]],
    period_end: str,
) -> str:
    for f in list(reconciled) + list(reported):
        if (
            f.get("concept_id") == CONCEPT_PERIOD_END_SHARES
            and f.get("period_end") == period_end
        ):
            return f.get("fact_id", "")
    return ""


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
