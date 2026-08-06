"""M2 Stage 2K.1R4E — TTM parent net profit / revenue state construction.

Builds the PIT-visible trailing-twelve-month states for a duration fact
(``net_profit_attributable_to_parent`` or ``revenue``) from the reported fact
bundle, handling restatement / supersession with the frozen window rule:

- annual state:    TTM_Y   = latest visible annual value for Y
- Q1/H1/Q3 state:  TTM_Y_P = annual(Y-1) + cumulative(Y,P) - cumulative(Y-1,P)

Only one report period is "current" at a time (the latest with
``effective_from <= t``).  A state is emitted only within its own current
window ``[start, next-period-start)``; a restatement of an input that becomes
effective strictly inside the window produces an additional state, while a
restatement that coincides with the period being superseded is folded into the
next period's state (never backfilled).  All arithmetic uses ``Decimal``.

This module never reads scoring artifacts and never opens the default database.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from ashare_research.pit_valuation.series_contract import (
    CONSTANT_TOTAL_SHARES,
    METRIC_PE,
    PERIOD_END_BY_REPORT,
    SHARE_CONTINUITY_PROOF_ID,
    STATUS_COMPUTED,
    STATUS_MISSING_TTM_INPUT,
    canonical_digest,
    parse_decimal,
)

_REPORT_ORDER = {"q1": 0, "half_year": 1, "q3": 2, "annual": 3}
_LAST = "9999-12-31"


def _concept_label(metric_id: str) -> str:
    return (
        "parent_net_profit"
        if metric_id == METRIC_PE or "net_profit" in metric_id.lower()
        else "revenue"
    )


def period_key_from_period_end(period_end: str) -> tuple[int, str] | None:
    """Return ``(fiscal_year, report_type)`` for a ``PeriodEnd`` date."""
    mm_dd = period_end[5:]
    for report_type, suffix in PERIOD_END_BY_REPORT.items():
        if mm_dd == suffix:
            return int(period_end[:4]), report_type
    return None


def _versions_for_period(
    facts: list[dict[str, Any]], year: int, report_type: str
) -> list[dict[str, Any]]:
    """Sort the facts for a ``(year, report_type)`` by effective_from."""
    period_end = f"{year}-{PERIOD_END_BY_REPORT[report_type]}"
    versions = [f for f in facts if f.get("period_end") == period_end]
    versions.sort(key=lambda f: (f.get("effective_from") or "", f.get("fact_id", "")))
    return versions


def _primary_start(versions: list[dict[str, Any]]) -> str:
    """The earliest effective_from among the versions of a report period."""
    return versions[0]["effective_from"]


def _latest_visible(versions: list[dict[str, Any]], at: str) -> dict[str, Any] | None:
    """Latest version with ``effective_from <= at`` (backward only)."""
    visible = [f for f in versions if f.get("effective_from", "") <= at]
    return visible[-1] if visible else None


def _fact_value(fact: dict[str, Any] | None) -> Decimal | None:
    if fact is None:
        return None
    return parse_decimal(fact["value"])


def _state_id(payload: dict[str, Any]) -> str:
    """Deterministic financial_state_id from the canonical payload."""
    return canonical_digest(payload)


def _all_period_starts(
    facts: list[dict[str, Any]],
) -> dict[tuple[int, str], str]:
    """Primary effective_from for every report period present in the bundle."""
    periods: dict[tuple[int, str], list[dict[str, Any]]] = {}
    for f in facts:
        key = period_key_from_period_end(f.get("period_end", ""))
        if key is None:
            continue
        periods.setdefault(key, []).append(f)
    return {key: _primary_start(vers) for key, vers in periods.items()}


def _next_start(after: tuple[int, str], starts: dict[tuple[int, str], str]) -> str:
    """The primary start of the next report period after ``after`` in report order."""
    ordered = sorted(starts.keys(), key=lambda k: (k[0], _REPORT_ORDER[k[1]]))
    idx = ordered.index(after)
    if idx + 1 < len(ordered):
        return starts[ordered[idx + 1]]
    return _LAST


def build_ttm_states(
    facts: list[dict[str, Any]],
    concept_id: str,
    *,
    metric_id: str,
    formula_id: str,
    formula_version: int = 1,
) -> list[dict[str, Any]]:
    """Build the PIT-visible TTM state timeline for one duration concept.

    ``facts`` is the reported bundle for ``concept_id`` (original + restated
    versions).  Returns a list of states sorted by ``effective_from``.

    Each state carries the frozen TTM identity: current/prior/prior-annual Fact
    IDs, restatement versions, available_at/effective_from per input, max input
    available_at, formula id/version, ``financial_state_id`` and a canonical
    state digest.  A missing prior input yields ``missing_ttm_input``.
    """
    concept_facts = [f for f in facts if f.get("concept_id") == concept_id]
    starts = _all_period_starts(concept_facts)
    ordered_periods = sorted(starts.keys(), key=lambda k: (k[0], _REPORT_ORDER[k[1]]))

    states: list[dict[str, Any]] = []
    for year, report_type in ordered_periods:
        is_annual = report_type == "annual"
        current_versions = _versions_for_period(concept_facts, year, report_type)
        start = starts[(year, report_type)]
        end = _next_start((year, report_type), starts)
        if not current_versions:
            continue

        if is_annual:
            states.extend(
                _annual_states(
                    concept_facts,
                    year,
                    current_versions,
                    start,
                    end,
                    metric_id=metric_id,
                    formula_id=formula_id,
                    formula_version=formula_version,
                )
            )
        else:
            states.extend(
                _interim_states(
                    concept_facts,
                    year,
                    report_type,
                    current_versions,
                    start,
                    end,
                    metric_id=metric_id,
                    formula_id=formula_id,
                    formula_version=formula_version,
                )
            )
    states.sort(key=lambda s: s["effective_from"])
    return states


def _annual_states(
    facts: list[dict[str, Any]],
    year: int,
    current_versions: list[dict[str, Any]],
    start: str,
    end: str,
    *,
    metric_id: str,
    formula_id: str,
    formula_version: int,
) -> list[dict[str, Any]]:
    """TTM states for an annual period: TTM = latest visible annual value."""
    out: list[dict[str, Any]] = []
    for version in current_versions:
        eff = version.get("effective_from", "")
        if not (start <= eff < end):
            continue
        value = _fact_value(version)
        out.append(
            _make_ttm_state(
                metric_id=metric_id,
                formula_id=formula_id,
                formula_version=formula_version,
                year=year,
                report_type="annual",
                period_end=f"{year}-12-31",
                effective_from=eff,
                value=value,
                status=STATUS_COMPUTED if value is not None else STATUS_MISSING_TTM_INPUT,
                current_fact=version,
                prior_cum=None,
                prior_annual=None,
                available_at_max=version.get("available_at", ""),
            )
        )
    return out


def _interim_states(
    facts: list[dict[str, Any]],
    year: int,
    report_type: str,
    current_versions: list[dict[str, Any]],
    start: str,
    end: str,
    *,
    metric_id: str,
    formula_id: str,
    formula_version: int,
) -> list[dict[str, Any]]:
    """TTM states for a Q1/H1/Q3 period with restatement-aware transitions."""
    prior_cum_versions = _versions_for_period(facts, year - 1, report_type)
    prior_annual_versions = _versions_for_period(facts, year - 1, "annual")

    # A missing prior input forms a single explicit missing_ttm_input state.
    if not prior_cum_versions or not prior_annual_versions:
        return [
            _make_ttm_state(
                metric_id=metric_id,
                formula_id=formula_id,
                formula_version=formula_version,
                year=year,
                report_type=report_type,
                period_end=f"{year}-{PERIOD_END_BY_REPORT[report_type]}",
                effective_from=start,
                value=None,
                status=STATUS_MISSING_TTM_INPUT,
                current_fact=_latest_visible(current_versions, start),
                prior_cum=None,
                prior_annual=None,
                available_at_max=_latest_visible(current_versions, start).get("available_at", ""),
            )
        ]

    # Transition points: every slot effective_from within [start, end).
    transition_points = {
        v.get("effective_from", "")
        for v in current_versions + prior_cum_versions + prior_annual_versions
        if start <= v.get("effective_from", "") < end
    }
    transition_points.add(start)
    out: list[dict[str, Any]] = []
    for eff in sorted(transition_points):
        current = _latest_visible(current_versions, eff)
        prior_cum = _latest_visible(prior_cum_versions, eff)
        prior_annual = _latest_visible(prior_annual_versions, eff)
        if current is None:
            continue
        value = _ttm_value(current, prior_cum, prior_annual)
        available_at_max = max(
            current.get("available_at", ""),
            prior_cum.get("available_at", ""),
            prior_annual.get("available_at", ""),
        )
        out.append(
            _make_ttm_state(
                metric_id=metric_id,
                formula_id=formula_id,
                formula_version=formula_version,
                year=year,
                report_type=report_type,
                period_end=f"{year}-{PERIOD_END_BY_REPORT[report_type]}",
                effective_from=eff,
                value=value,
                status=STATUS_COMPUTED if value is not None else STATUS_MISSING_TTM_INPUT,
                current_fact=current,
                prior_cum=prior_cum,
                prior_annual=prior_annual,
                available_at_max=available_at_max,
            )
        )
    return out


def _ttm_value(
    current: dict[str, Any],
    prior_cum: dict[str, Any] | None,
    prior_annual: dict[str, Any] | None,
) -> Decimal | None:
    """TTM = annual(Y-1) + cumulative(Y,P) - cumulative(Y-1,P)."""
    if prior_cum is None or prior_annual is None:
        return None
    return (
        _fact_value(prior_annual)
        + _fact_value(current)
        - _fact_value(prior_cum)
    )


def _make_ttm_state(
    *,
    metric_id: str,
    formula_id: str,
    formula_version: int,
    year: int,
    report_type: str,
    period_end: str,
    effective_from: str,
    value: Decimal | None,
    status: str,
    current_fact: dict[str, Any] | None,
    prior_cum: dict[str, Any] | None,
    prior_annual: dict[str, Any] | None,
    available_at_max: str,
) -> dict[str, Any]:
    """Assemble one TTM state with the frozen identity contract."""
    restatement_versions = {
        "current_cumulative": current_fact.get("restatement_version", "") if current_fact else "",
        "prior_year_same_period": prior_cum.get("restatement_version", "") if prior_cum else "",
        "prior_annual": prior_annual.get("restatement_version", "") if prior_annual else "",
    }
    input_available_at = {
        "current_cumulative": current_fact.get("available_at", "") if current_fact else "",
        "prior_year_same_period": prior_cum.get("available_at", "") if prior_cum else "",
        "prior_annual": prior_annual.get("available_at", "") if prior_annual else "",
    }
    input_effective_from = {
        "current_cumulative": current_fact.get("effective_from", "") if current_fact else "",
        "prior_year_same_period": prior_cum.get("effective_from", "") if prior_cum else "",
        "prior_annual": prior_annual.get("effective_from", "") if prior_annual else "",
    }
    input_fact_ids = sorted(
        fid for fid in (
            current_fact.get("fact_id", "") if current_fact else "",
            prior_cum.get("fact_id", "") if prior_cum else "",
            prior_annual.get("fact_id", "") if prior_annual else "",
        )
        if fid
    )
    core = {
        "metric_id": metric_id,
        "state_type": "ttm",
        "concept": _concept_label(metric_id),
        "fiscal_year": year,
        "report_type": report_type,
        "period_end": period_end,
        "effective_from": effective_from,
        "value_decimal": None if value is None else str(value),
        "status": status,
        "formula_id": formula_id,
        "formula_version": formula_version,
        "input_fact_ids": input_fact_ids,
        "current_cumulative_fact_id": current_fact.get("fact_id", "") if current_fact else "",
        "prior_year_same_period_fact_id": prior_cum.get("fact_id", "") if prior_cum else "",
        "prior_annual_fact_id": prior_annual.get("fact_id", "") if prior_annual else "",
        "restatement_versions": restatement_versions,
        "input_available_at": input_available_at,
        "input_effective_from": input_effective_from,
        "available_at_max": available_at_max,
        "share_basis_decimal": str(CONSTANT_TOTAL_SHARES),
        "share_continuity_proof_id": SHARE_CONTINUITY_PROOF_ID,
    }
    state_id = _state_id(core)
    return {
        "financial_state_id": state_id,
        **core,
        "state_digest": state_id,
    }
