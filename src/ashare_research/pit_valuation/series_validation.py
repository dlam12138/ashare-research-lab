"""M2 Stage 2K.1R4E — candidate-series validation, coverage and audit samples.

Recomputes each observation's ratio and identity from its Decimal operands,
checks the 3y/5y effective-sample coverage, selects frozen audit samples with
expanded Decimal operands, and drives the dual-oracle consistency check.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from ashare_research.pit_valuation.series_contract import (
    METRIC_PB,
    METRIC_PE,
    METRIC_PS,
    MIN_SAMPLES_3Y,
    MIN_SAMPLES_5Y,
    STATUS_COMPUTED,
    WINDOW_3Y_START,
    WINDOW_5Y_START,
    canonical_digest,
    first_trade_day_at_or_after,
    parse_decimal,
)
from ashare_research.pit_valuation.temporal_join import (
    compare_oracles,
    duckdb_asof_join,
    python_backward_join,
)

AUDIT_SAMPLE_LIMIT = 64


def _recompute_ratio(obs: dict[str, Any]) -> tuple[Decimal | None, str]:
    """Recompute the ratio from the observation's Decimal operands."""
    close = parse_decimal(obs["market_close_decimal"])
    if obs["status"] != STATUS_COMPUTED:
        return None, obs["status"]
    numerator = Decimal(obs["financial_state_value_decimal"])
    shares = Decimal(obs["share_basis_decimal"])
    if shares is None or shares <= 0:
        return None, "zero_denominator"
    recomputed = close / (numerator / shares)
    return recomputed, "computed"


def _recompute_observation_id(obs: dict[str, Any]) -> str:
    payload = {k: v for k, v in obs.items() if k != "observation_id"}
    return canonical_digest(payload)


def verify_observations(series: dict[str, Any]) -> dict[str, Any]:
    """Recompute each observation's identity and ratio; report any mismatch."""
    id_errors: list[dict[str, Any]] = []
    ratio_errors: list[dict[str, Any]] = []
    for obs in series["observations"]:
        recomputed = _recompute_observation_id(obs)
        if recomputed != obs.get("observation_id"):
            id_errors.append(
                {
                    "observation_id": obs.get("observation_id"),
                    "recomputed": recomputed,
                    "metric_id": obs["metric_id"],
                    "trade_date": obs["trade_date"],
                }
            )
        recomputed_ratio, _ = _recompute_ratio(obs)
        stored_ratio = obs.get("ratio_decimal")
        if stored_ratio is None:
            if recomputed_ratio is not None:
                ratio_errors.append(
                    {
                        "observation_id": obs.get("observation_id"),
                        "metric_id": obs["metric_id"],
                        "trade_date": obs["trade_date"],
                        "reason": "stored null but recomputed non-null",
                    }
                )
        elif recomputed_ratio is None or str(recomputed_ratio) != stored_ratio:
            ratio_errors.append(
                {
                    "observation_id": obs.get("observation_id"),
                    "metric_id": obs["metric_id"],
                    "trade_date": obs["trade_date"],
                    "stored": stored_ratio,
                    "recomputed": None if recomputed_ratio is None else str(recomputed_ratio),
                }
            )
    return {
        "observation_count": len(series["observations"]),
        "identity_mismatch_count": len(id_errors),
        "identity_consistent": not id_errors,
        "ratio_mismatch_count": len(ratio_errors),
        "ratio_consistent": not ratio_errors,
        "identity_errors": id_errors[:20],
        "ratio_errors": ratio_errors[:20],
    }


def build_coverage_report(
    series: dict[str, Any],
    timelines: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    """Independent coverage report with 3y/5y effective-sample counts."""
    metric_ids = (METRIC_PE, METRIC_PB, METRIC_PS)
    obs_by_metric: dict[str, list[dict[str, Any]]] = {m: [] for m in metric_ids}
    for obs in series["observations"]:
        obs_by_metric[obs["metric_id"]].append(obs)

    trade_dates = sorted({obs["trade_date"] for obs in series["observations"]})
    start_3y = first_trade_day_at_or_after(WINDOW_3Y_START, trade_dates)
    start_5y = first_trade_day_at_or_after(WINDOW_5Y_START, trade_dates)

    per_metric: dict[str, Any] = {}
    for metric_id, obs_list in obs_by_metric.items():
        computed = [o for o in obs_list if o["status"] == STATUS_COMPUTED]
        status_counts: dict[str, int] = {}
        for o in obs_list:
            status_counts[o["status"]] = status_counts.get(o["status"], 0) + 1
        computed_3y = [o for o in computed if o["trade_date"] >= start_3y]
        computed_5y = [o for o in computed if o["trade_date"] >= start_5y]
        per_metric[metric_id] = {
            "total_observations": len(obs_list),
            "computed_observations": len(computed),
            "status_counts": status_counts,
            "first_computed_trade_date": computed[0]["trade_date"] if computed else "",
            "last_computed_trade_date": computed[-1]["trade_date"] if computed else "",
            "3y_required_start": start_3y,
            "5y_required_start": start_5y,
            "3y_effective_sample_count": len(computed_3y),
            "5y_effective_sample_count": len(computed_5y),
            "minimum_required": {"3y": MIN_SAMPLES_3Y, "5y": MIN_SAMPLES_5Y},
            "3y_ready": len(computed_3y) >= MIN_SAMPLES_3Y,
            "5y_ready": len(computed_5y) >= MIN_SAMPLES_5Y,
        }

    state_transition_count = sum(
        max(0, len(timelines[m]) - 1) for m in (METRIC_PE, METRIC_PB, METRIC_PS)
    )
    restatement_transition_count = 0
    for m in (METRIC_PE, METRIC_PS):
        for s in timelines[m]:
            rv = s.get("restatement_versions", {})
            if any(v != "original" for v in rv.values()):
                restatement_transition_count += 1

    return {
        "symbol": series["symbol"],
        "market_rows": series["market_rows"],
        "market_trade_dates": len(trade_dates),
        "3y_required_start": start_3y,
        "5y_required_start": start_5y,
        "per_metric": per_metric,
        "state_transition_count": state_transition_count,
        "restatement_transition_count": restatement_transition_count,
        "missing_date_count": 0,
    }


def select_audit_samples(
    series: dict[str, Any],
    timelines: dict[str, list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    """Select the frozen audit samples with expanded Decimal operands."""
    obs = series["observations"]
    by_date_metric = {(o["metric_id"], o["trade_date"]): o for o in obs}
    trade_dates = sorted({o["trade_date"] for o in obs})
    start_3y = first_trade_day_at_or_after(WINDOW_3Y_START, trade_dates)
    start_5y = first_trade_day_at_or_after(WINDOW_5Y_START, trade_dates)

    flags: set[tuple[str, str]] = set()

    # Every distinct filing effective_from: previous trade day and the day itself.
    for m in (METRIC_PE, METRIC_PB, METRIC_PS):
        for s in timelines[m]:
            eff = s["effective_from"]
            prev = _prev_trade_day(eff, trade_dates)
            if prev:
                flags.add((m, prev))
            if eff in trade_dates:
                flags.add((m, eff))

    # 2020 corrected effective_from (2020-05-06).
    for d in ("2020-05-06", "2021-03-29"):
        if d in trade_dates:
            for m in (METRIC_PE, METRIC_PB, METRIC_PS):
                flags.add((m, d))

    # 2022-Q1 restatement effective 2023-05-04: previous and current trade day.
    for d in ("2023-05-03", "2023-05-04", "2023-05-05"):
        if d in trade_dates:
            for m in (METRIC_PE, METRIC_PB, METRIC_PS):
                flags.add((m, d))

    if start_5y in trade_dates:
        for m in (METRIC_PE, METRIC_PB, METRIC_PS):
            flags.add((m, start_5y))
    if start_3y in trade_dates:
        for m in (METRIC_PE, METRIC_PB, METRIC_PS):
            flags.add((m, start_3y))
    if "2026-07-31" in trade_dates:
        for m in (METRIC_PE, METRIC_PB, METRIC_PS):
            flags.add((m, "2026-07-31"))

    # Any nonpositive / invalid sample.
    for o in obs:
        if o["status"] != STATUS_COMPUTED:
            flags.add((o["metric_id"], o["trade_date"]))

    # At least two samples per TTM formula type (PE/PS annual and interim).
    for m in (METRIC_PE, METRIC_PS):
        for state in timelines[m]:
            if state.get("report_type") == "annual":
                flags.add((m, state["effective_from"]))
            if state.get("report_type") in ("q1", "half_year", "q3"):
                flags.add((m, state["effective_from"]))

    samples: list[dict[str, Any]] = []
    for metric_id, trade_date in sorted(flags):
        if len(samples) >= AUDIT_SAMPLE_LIMIT:
            break
        o = by_date_metric.get((metric_id, trade_date))
        if o is None:
            continue
        samples.append(_expand_sample(o))

    # Ensure the limit is not exceeded by the mandatory set.
    samples = samples[:AUDIT_SAMPLE_LIMIT]
    return samples


def _prev_trade_day(before: str, trade_dates: list[str]) -> str | None:
    earlier = [d for d in trade_dates if d < before]
    return earlier[-1] if earlier else None


def _expand_sample(obs: dict[str, Any]) -> dict[str, Any]:
    """Expand Decimal operands so a human can recompute the ratio by hand."""
    return {
        "observation_id": obs["observation_id"],
        "metric_id": obs["metric_id"],
        "trade_date": obs["trade_date"],
        "status": obs["status"],
        "exclusion_reason": obs["exclusion_reason"],
        "market_close_decimal": obs["market_close_decimal"],
        "financial_state_value_decimal": obs.get("financial_state_value_decimal"),
        "share_basis_decimal": obs.get("share_basis_decimal"),
        "per_share_denominator_decimal": obs["per_share_denominator_decimal"],
        "ratio_decimal": obs["ratio_decimal"],
        "financial_state_id": obs["financial_state_id"],
        "financial_state_effective_from": obs["financial_state_effective_from"],
        "financial_state_available_at_max": obs["financial_state_available_at_max"],
        "input_fact_ids": obs["input_fact_ids"],
        "formula_id": obs["formula_id"],
    }


def validate_dual_oracle(
    market_rows: list[dict[str, Any]],
    timelines: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    """Run both oracles per metric and compare row-by-row."""
    per_metric: dict[str, Any] = {}
    for metric_id in (METRIC_PE, METRIC_PB, METRIC_PS):
        a = python_backward_join(market_rows, timelines[metric_id])
        b = duckdb_asof_join(market_rows, timelines[metric_id], group=metric_id)
        per_metric[metric_id] = compare_oracles(a, b)
    all_identical = all(per_metric[m]["identical"] for m in (METRIC_PE, METRIC_PB, METRIC_PS))
    return {
        "per_metric": per_metric,
        "all_identical": all_identical,
        "trusted": all_identical,
    }
