"""M2 Stage 2K.1R4E.5 — historical valuation percentile core.

Deterministic, offline home for the non-production historical valuation
percentile profile of PE_A_TTM / PB_A_MRQ / PS_A_TTM at the frozen as-of
trade date, using the frozen ``MIDRANK_EMPIRICAL_PERCENTILE`` contract.

Key properties:

- The **only** valuation input is a trusted candidate artifact
  (``reports/petrochina_pit_valuation_series_candidate_v2.json``).  This module
  never re-downloads market data, never recomputes PE/PB/PS, never touches the
  registry cache, never queries the default DB, and never reads from the old
  close-percentile or shadow-score inputs.
- Percentile ranking uses **Decimal** comparison only (never float).  The
  midrank identity binds the exact rational ``rank_numerator /
  rank_denominator``, so display rounding never affects identity.
- Sample eligibility is fail-closed: only ``status == "computed"`` with a
  strictly-positive ``ratio_decimal`` within the window enters ``N``.  Every
  other observation (missing input, non-positive denominator/earnings, null
  ratio, every non-computed status) stays in the exclusion ledger and never
  leaks into the sample.  Non-positive PE is never ranked as cheap.
- The as-of current observation is included in the sample (``include_current``)
  and must be found exactly (metric_id + trade_date == as_of + computed).
- PIT safety is re-proven on the sample: no sample ``trade_date`` may exceed
  the as-of date.

This module never opens a database and never touches the network.
"""

from __future__ import annotations

import json
from decimal import ROUND_HALF_UP, Decimal, localcontext
from pathlib import Path
from typing import Any

from ashare_research.pit_valuation.series_contract import SYMBOL, canonical_digest, parse_decimal

# Frozen contract identities (mirror config/pit_valuation_percentile_contract_v1.json).
CONTRACT_SCHEMA = "pit_valuation_historical_percentile_v1"
RANK_METHOD = "MIDRANK_EMPIRICAL_PERCENTILE"
AS_OF_TRADE_DATE = "2026-07-31"
METRICS = ("PE_A_TTM", "PB_A_MRQ", "PS_A_TTM")
WINDOW_IDS = ("3y", "5y")
MINIMUM_3Y = 500
MINIMUM_5Y = 900
WINDOW_EFFECTIVE_FIRST = {"3y": "2023-07-31", "5y": "2021-08-02"}
WINDOW_CALENDAR_START = {"3y": "2023-07-31", "5y": "2021-07-31"}

# Eligible status alone is not enough; a non-computed ratio must never rank.
STATUS_COMPUTED = "computed"

# Interpretation guard (PE only; the north-star hard requirement).
PE_INTERPRETATION_GUARD_ID = "low_pe_not_automatic_undervaluation_v1"
INTERPRETATION_DESCRIPTIVE = "DESCRIPTIVE_RELATIVE_VALUATION_ONLY"

# Candidate contract identities (the trusted upstream artifact).
CANDIDATE_SCHEMA = "petrochina_pit_valuation_series_candidate_v1"
CANDIDATE_OBSERVATION_COUNT = 4053
CANDIDATE_METRICS = frozenset(METRICS)


class PercentileError(ValueError):
    """The percentile profile violates a frozen R4E.5 contract."""


def _percentile_decimal(numerator: int, denominator: int) -> Decimal:
    """numerator / denominator as a high-precision Decimal.

    Callers pass the fully-scaled numerator (i.e. already multiplied by 100).
    """
    with localcontext() as ctx:
        ctx.prec = 60
        return Decimal(numerator) / Decimal(denominator)


def _display_decimal(value: Decimal) -> str:
    """6-decimal display form (identity is bound to the exact rational, not this)."""
    return str(value.quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP))


def _load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def load_percentile_contract(path: Path) -> dict[str, Any]:
    """Load and structurally validate the frozen percentile contract."""
    contract = _load_json(path)
    if contract.get("schema") != CONTRACT_SCHEMA:
        raise PercentileError(f"contract schema mismatch: {contract.get('schema')}")
    if contract.get("symbol") != SYMBOL:
        raise PercentileError(f"contract symbol mismatch: {contract.get('symbol')}")
    if contract.get("as_of_trade_date") != AS_OF_TRADE_DATE:
        raise PercentileError(
            f"contract as_of mismatch: {contract.get('as_of_trade_date')}"
        )
    if list(contract.get("metrics", [])) != list(METRICS):
        raise PercentileError(f"contract metrics mismatch: {contract.get('metrics')}")
    if contract.get("rank_method") != RANK_METHOD:
        raise PercentileError(f"contract rank_method mismatch: {contract.get('rank_method')}")
    for wid in WINDOW_IDS:
        w = contract.get("windows", {}).get(wid, {})
        if w.get("effective_first_trade_date") != WINDOW_EFFECTIVE_FIRST[wid]:
            raise PercentileError(f"contract {wid} effective start mismatch")
        if w.get("calendar_start") != WINDOW_CALENDAR_START[wid]:
            raise PercentileError(f"contract {wid} calendar start mismatch")
        if w.get("minimum_sample_count") != (MINIMUM_3Y if wid == "3y" else MINIMUM_5Y):
            raise PercentileError(f"contract {wid} minimum mismatch")
    return contract


def _file_sha256(path: Path) -> str:
    import hashlib

    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_trusted_candidate(candidate_path: Path) -> dict[str, Any]:
    """Load and verify the trusted candidate artifact (R4E.4 candidate v2).

    Verifies schema, symbol, metric set, observation count, and that every
    observation carries a non-empty observation_id.  Any tamper raises
    :class:`PercentileError` -> PIT_VALUATION_PERCENTILE_NOT_TRUSTED.
    """
    candidate = _load_json(candidate_path)
    if candidate.get("schema") != CANDIDATE_SCHEMA:
        raise PercentileError(f"candidate schema mismatch: {candidate.get('schema')}")
    if candidate.get("symbol") != SYMBOL:
        raise PercentileError(f"candidate symbol mismatch: {candidate.get('symbol')}")
    obs = candidate.get("observations")
    if not isinstance(obs, list) or len(obs) != CANDIDATE_OBSERVATION_COUNT:
        n_obs = len(obs) if isinstance(obs, list) else "?"
        raise PercentileError(
            f"candidate observation_count {n_obs} != {CANDIDATE_OBSERVATION_COUNT}"
        )
    metric_set = {o.get("metric_id") for o in obs}
    if metric_set != set(CANDIDATE_METRICS):
        raise PercentileError(f"candidate metric set mismatch: {metric_set}")
    for o in obs:
        if not o.get("observation_id"):
            raise PercentileError("candidate observation missing observation_id")
    return candidate


def _sample_eligibility_reason(obs: dict[str, Any], metric_id: str, wid: str) -> str | None:
    """Return the exclusion reason for one observation in a window, or None if eligible."""
    if obs.get("metric_id") != metric_id:
        return "metric_mismatch"
    if obs.get("status") != STATUS_COMPUTED:
        return obs.get("status") or "non_computed_status"
    ratio = obs.get("ratio_decimal")
    if ratio is None:
        return "null_ratio"
    try:
        r = parse_decimal(str(ratio))
    except Exception:
        return "unparseable_ratio"
    if r <= 0:
        return "nonpositive_ratio"
    td = str(obs.get("trade_date", ""))
    if td < WINDOW_EFFECTIVE_FIRST[wid]:
        return "before_window_start"
    if td > AS_OF_TRADE_DATE:
        return "future_trade_date"
    return None


def build_percentile_sample(
    candidate: dict[str, Any],
    metric_id: str,
    wid: str,
) -> dict[str, Any]:
    """Build the eligible sample for one metric/window.

    Returns a :class:`PercentileSampleSummary`-shaped dict with the eligible
    observation rows, the exclusion ledger, and recomputable digests.
    """
    if metric_id not in METRICS:
        raise PercentileError(f"unknown metric {metric_id}")
    if wid not in WINDOW_IDS:
        raise PercentileError(f"unknown window {wid}")

    eligible: list[dict[str, Any]] = []
    excluded: list[dict[str, Any]] = []
    excluded_status: dict[str, int] = {}
    for o in candidate["observations"]:
        if o.get("metric_id") != metric_id:
            continue
        reason = _sample_eligibility_reason(o, metric_id, wid)
        if reason is None:
            eligible.append(o)
        else:
            excluded.append(o)
            excluded_status[reason] = excluded_status.get(reason, 0) + 1

    # order-independent digests
    ids = sorted(o["observation_id"] for o in eligible)
    values = sorted(
        (str(parse_decimal(str(o["ratio_decimal"]))), o["observation_id"])
        for o in eligible
    )
    sample_ids_digest = canonical_digest(ids)
    values_digest = canonical_digest(values)

    min_required = MINIMUM_3Y if wid == "3y" else MINIMUM_5Y
    coverage_status = "READY" if len(eligible) >= min_required else "INSUFFICIENT"

    return {
        "metric_id": metric_id,
        "window_id": wid,
        "calendar_start": WINDOW_CALENDAR_START[wid],
        "effective_first_trade_date": WINDOW_EFFECTIVE_FIRST[wid],
        "as_of_trade_date": AS_OF_TRADE_DATE,
        "eligible_observation_count": len(eligible),
        "excluded_observation_count": len(excluded),
        "excluded_status_counts": excluded_status,
        "sample_observation_ids_digest": sample_ids_digest,
        "sample_values_digest": values_digest,
        "minimum_required": min_required,
        "coverage_status": coverage_status,
        "rows": eligible,
        "excluded_rows": excluded,
    }


def find_current_observation(candidate: dict[str, Any], metric_id: str) -> dict[str, Any]:
    """Exactly one computed observation at the as-of date for the metric."""
    matches = [
        o
        for o in candidate["observations"]
        if o.get("metric_id") == metric_id
        and str(o.get("trade_date", "")) == AS_OF_TRADE_DATE
        and o.get("status") == STATUS_COMPUTED
        and o.get("ratio_decimal") is not None
    ]
    if len(matches) != 1:
        raise PercentileGapsError(
            f"{metric_id}: {len(matches)} computed as-of observations (need exactly 1)"
        )
    return matches[0]


class PercentileGapsError(PercentileError):
    """A required as-of observation or minimum sample is missing (GAPS_REMAIN)."""


def compute_midrank_percentile(
    current_ratio: Decimal,
    sample_ratios: list[Decimal],
) -> dict[str, Any]:
    """Compute the midrank / strict / weak empirical percentile for one sample.

    The sample includes the current observation (``include_current``).  All
    comparisons are exact Decimal comparisons.  Returns exact integer counts
    and the exact rational ``rank_numerator / rank_denominator``.
    """
    N = len(sample_ratios)  # noqa: N806  # contract rank-statistic vocabulary
    if N == 0:
        raise PercentileError("empty sample (N=0)")
    L = sum(1 for r in sample_ratios if r < current_ratio)  # noqa: N806
    E = sum(1 for r in sample_ratios if r == current_ratio)  # noqa: N806
    G = sum(1 for r in sample_ratios if r > current_ratio)  # noqa: N806
    if N != L + E + G:
        raise PercentileError(f"N={N} != L+E+G={L + E + G}")

    rank_numerator = 2 * L + E + 1
    rank_denominator = 2 * N

    strict = _percentile_decimal(100 * L, N)
    weak = _percentile_decimal(100 * (L + E), N)
    midrank = _percentile_decimal(100 * rank_numerator, rank_denominator)

    return {
        "eligible_sample_count": N,
        "count_less": L,
        "count_equal": E,
        "count_greater": G,
        "rank_numerator": rank_numerator,
        "rank_denominator": rank_denominator,
        "strict_percentile_decimal": _display_decimal(strict),
        "weak_percentile_decimal": _display_decimal(weak),
        "midrank_percentile_decimal": _display_decimal(midrank),
        "strict_percentile_full": str(strict),
        "weak_percentile_full": str(weak),
        "midrank_percentile_full": str(midrank),
        "tie_count": E,
        "tie_fraction": _display_decimal(Decimal(E) / Decimal(N)) if N else "0",
    }


def build_percentile_record(
    candidate: dict[str, Any],
    metric_id: str,
    wid: str,
    *,
    candidate_artifact_digest: str,
    contract_version: str,
) -> dict[str, Any]:
    """Build one non-production percentile record for a metric/window."""
    current = find_current_observation(candidate, metric_id)
    current_ratio = parse_decimal(str(current["ratio_decimal"]))

    sample = build_percentile_sample(candidate, metric_id, wid)
    ratios = [parse_decimal(str(o["ratio_decimal"])) for o in sample["rows"]]
    rank = compute_midrank_percentile(current_ratio, ratios)

    # PIT gate: no sample trade_date may exceed as_of.
    max_sample_date = max(str(o["trade_date"]) for o in sample["rows"])
    if max_sample_date > AS_OF_TRADE_DATE:
        raise PercentileError("future leakage: sample trade_date > as_of")

    min_required = MINIMUM_3Y if wid == "3y" else MINIMUM_5Y
    coverage_ready = len(ratios) >= min_required

    is_pe = metric_id == "PE_A_TTM"
    guard = (
        {
            "interpretation_guard_id": PE_INTERPRETATION_GUARD_ID,
            "interpretation": INTERPRETATION_DESCRIPTIVE,
            "cycle_warning_required": True,
        }
        if is_pe
        else {
            "interpretation": INTERPRETATION_DESCRIPTIVE,
            "descriptive_only": True,
        }
    )

    record = {
        "schema": "petrochina_pit_valuation_percentile_record_v1",
        "version": "1.0",
        "symbol": SYMBOL,
        "metric_id": metric_id,
        "window_id": wid,
        "calendar_start": WINDOW_CALENDAR_START[wid],
        "effective_first_trade_date": WINDOW_EFFECTIVE_FIRST[wid],
        "as_of_trade_date": AS_OF_TRADE_DATE,
        "current_observation_id": current["observation_id"],
        "current_ratio_decimal": str(current_ratio),
        "eligible_sample_count": rank["eligible_sample_count"],
        "excluded_sample_count": sample["excluded_observation_count"],
        "count_less": rank["count_less"],
        "count_equal": rank["count_equal"],
        "count_greater": rank["count_greater"],
        "rank_numerator": rank["rank_numerator"],
        "rank_denominator": rank["rank_denominator"],
        "strict_percentile_decimal": rank["strict_percentile_decimal"],
        "weak_percentile_decimal": rank["weak_percentile_decimal"],
        "midrank_percentile_decimal": rank["midrank_percentile_decimal"],
        "method_id": RANK_METHOD,
        "contract_version": contract_version,
        "candidate_artifact_digest": candidate_artifact_digest,
        "sample_observation_ids_digest": sample["sample_observation_ids_digest"],
        "sample_values_digest": sample["sample_values_digest"],
        "interpretation_guard": guard,
        "non_production": True,
        "descriptive_only": True,
        "score_eligible": False,
        "production_eligible": False,
        "coverage_status": "READY" if coverage_ready else "INSUFFICIENT",
    }
    record["percentile_record_id"] = _percentile_record_id(record)
    return record


def _percentile_record_id(record: dict[str, Any]) -> str:
    """Deterministic identity bound to every ranking-relevant field.

    Never binds absolute path, wall-clock time, Python version, machine name,
    or the output directory.
    """
    core = {
        "schema": record["schema"],
        "version": record["version"],
        "symbol": record["symbol"],
        "metric_id": record["metric_id"],
        "window_id": record["window_id"],
        "calendar_start": record["calendar_start"],
        "effective_first_trade_date": record["effective_first_trade_date"],
        "as_of_trade_date": record["as_of_trade_date"],
        "current_observation_id": record["current_observation_id"],
        "current_ratio_decimal": record["current_ratio_decimal"],
        "candidate_artifact_digest": record["candidate_artifact_digest"],
        "sample_observation_ids_digest": record["sample_observation_ids_digest"],
        "sample_values_digest": record["sample_values_digest"],
        "eligible_sample_count": record["eligible_sample_count"],
        "excluded_sample_count": record["excluded_sample_count"],
        "count_less": record["count_less"],
        "count_equal": record["count_equal"],
        "count_greater": record["count_greater"],
        "rank_numerator": record["rank_numerator"],
        "rank_denominator": record["rank_denominator"],
        "method_id": record["method_id"],
        "contract_version": record["contract_version"],
        "interpretation_guard_id": record["interpretation_guard"].get(
            "interpretation_guard_id", "descriptive_guard"
        ),
    }
    return canonical_digest(core)


def build_percentile_profile(
    candidate_path: Path,
    *,
    candidate_artifact_digest: str,
    contract_version: str,
    r4e4_decision_digest: str,
    market_reconciliation_digest: str,
) -> dict[str, Any]:
    """Build the six non-production percentile records in the frozen order.

    Order: PE 3y, PE 5y, PB 3y, PB 5y, PS 3y, PS 5y.
    """
    candidate = load_trusted_candidate(candidate_path)
    records: list[dict[str, Any]] = []
    for metric in METRICS:
        for wid in WINDOW_IDS:
            records.append(
                build_percentile_record(
                    candidate,
                    metric,
                    wid,
                    candidate_artifact_digest=candidate_artifact_digest,
                    contract_version=contract_version,
                )
            )

    all_ready = all(r["coverage_status"] == "READY" for r in records)
    return {
        "schema": "petrochina_pit_valuation_percentile_profile_v1",
        "version": "1.0",
        "symbol": SYMBOL,
        "as_of_trade_date": AS_OF_TRADE_DATE,
        "input": {
            "candidate_schema": CANDIDATE_SCHEMA,
            "candidate_artifact_digest": candidate_artifact_digest,
            "r4e4_decision_digest": r4e4_decision_digest,
            "market_reconciliation_digest": market_reconciliation_digest,
        },
        "method": {
            "contract": contract_version,
            "rank_method": RANK_METHOD,
            "include_current": True,
            "decimal_policy": "Decimal only; rational identity",
            "window_policy": "calendar-year window mapped to actual trade days",
            "invalid_observation_policy": "status==computed and ratio>0 only",
        },
        "records": records,
        "summary": {
            "all_windows_ready": all_ready,
            "record_count": len(records),
            "oracle_identical": None,
            "future_leakage_check": "pass",
            "cycle_guard_present": True,
            "non_production": True,
            "score_eligible": False,
            "production_eligible": False,
        },
    }


def validate_percentile_profile(profile: dict[str, Any]) -> dict[str, Any]:
    """Validate a built profile; returns a structured result (raises on violation)."""
    errors: list[str] = []
    records = profile.get("records", [])
    if len(records) != 6:
        errors.append(f"record_count {len(records)} != 6")
    expected_order = [
        ("PE_A_TTM", "3y"), ("PE_A_TTM", "5y"),
        ("PB_A_MRQ", "3y"), ("PB_A_MRQ", "5y"),
        ("PS_A_TTM", "3y"), ("PS_A_TTM", "5y"),
    ]
    got_order = [(r.get("metric_id"), r.get("window_id")) for r in records]
    if got_order != expected_order:
        errors.append(f"record order mismatch: {got_order}")
    for r in records:
        mid = f"{r.get('metric_id')}{r.get('window_id')}"
        if not (r.get("count_less", -1) >= 0 and r.get("count_equal", -1) >= 0
                and r.get("count_greater", -1) >= 0):
            errors.append(f"{mid}: negative count")
        if r.get("eligible_sample_count") != (
            r.get("count_less") + r.get("count_equal") + r.get("count_greater")
        ):
            errors.append(f"{mid}: N != L+E+G")
        if r.get("rank_denominator", 0) <= 0:
            errors.append(f"{mid}: bad denominator")
        if r.get("metric_id") == "PE_A_TTM" and not r.get(
            "interpretation_guard", {}
        ).get("cycle_warning_required"):
            errors.append(f"{mid}: missing cycle guard")
        if r.get("non_production") is not True or r.get("production_eligible") is not False:
            errors.append(f"{mid}: production boundary violated")
    return {
        "valid": not errors,
        "errors": errors,
        "record_count": len(records),
        "all_windows_ready": all(r.get("coverage_status") == "READY" for r in records),
    }
