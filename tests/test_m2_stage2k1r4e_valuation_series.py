"""M2 Stage 2K.1R4E — valuation-series computation tests."""

from decimal import Decimal
from pathlib import Path

from ashare_research.pit_valuation import financial_state, fixtures, valuation_series
from ashare_research.pit_valuation.series_contract import (
    METRIC_PE,
    canonical_digest,
)

REPORTED, RECONCILED = fixtures.load_fixture_bundles(Path("."))
MARKET, MARKET_META = fixtures.load_fixture_market(Path("."))


def _series():
    timelines = financial_state.build_financial_state_timelines(REPORTED, RECONCILED)
    return valuation_series.build_valuation_series(MARKET, MARKET_META, timelines)


def test_ratio_recomputed_from_decimal_operands():
    series = _series()
    for obs in series["observations"]:
        if obs["status"] != "computed":
            assert obs["ratio_decimal"] is None
            continue
        close = Decimal(obs["market_close_decimal"])
        numerator = Decimal(obs["financial_state_value_decimal"])
        shares = Decimal(obs["share_basis_decimal"])
        expected = close / (numerator / shares)
        assert str(expected) == obs["ratio_decimal"]


def test_no_decimal_float_path():
    # All financial values enter via Decimal(str(value)); the fixtures store
    # integer-valued floats whose str() is exact.
    for fact in REPORTED:
        Decimal(str(fact["value"]))
    for row in MARKET:
        Decimal(str(row["close"]))


def test_negative_earnings_never_produce_negative_pe():
    # Build a synthetic fact set with a negative net-profit fact and ensure no
    # negative PE ratio is emitted.
    from ashare_research.pit_valuation.series_contract import canonical_digest

    # Replace a computable annual input. The former first-row Q1 input had
    # no prior-year dependencies, so it could not exercise negative earnings;
    # retaining its old ID also introduced an unrelated same-day candidate.
    original = next(f for f in REPORTED
                    if f["concept_id"] == "net_profit_attributable_to_parent"
                    and f["period_end"] == "2024-12-31")
    neg = dict(original)
    neg["value"] = -5000000000.0
    payload = {
        "concept_id": neg["concept_id"],
        "symbol": neg["symbol"],
        "period_end": neg["period_end"],
        "value": neg["value"],
        "available_at": neg["available_at"],
        "effective_from": neg["effective_from"],
        "restatement_version": "original",
        "supersedes_fact_id": "",
        "source_id": "r4d:SYN-NEG",
    }
    neg["fact_id"] = canonical_digest(payload)
    facts = [neg] + [f for f in REPORTED if f["fact_id"] != original["fact_id"]]
    timelines = financial_state.build_financial_state_timelines(facts, RECONCILED)
    series = valuation_series.build_valuation_series(MARKET, MARKET_META, timelines)
    negative_state_ids = {s["financial_state_id"] for s in timelines[METRIC_PE]
                          if s["period_end"] == "2024-12-31"}
    negative_observations = [obs for obs in series["observations"]
                             if obs.get("financial_state_id") in negative_state_ids]
    assert negative_observations
    assert all(obs["status"] == "nonpositive_earnings" for obs in negative_observations)
    assert all(obs["ratio_decimal"] is None for obs in negative_observations)
    for obs in series["observations"]:
        if obs["metric_id"] == METRIC_PE and obs["status"] == "computed":
            assert float(obs["ratio_decimal"]) > 0


def test_missing_not_written_as_zero():
    series = _series()
    for obs in series["observations"]:
        if obs["status"] != "computed":
            assert obs["ratio_decimal"] is None
            assert obs["per_share_denominator_decimal"] is None


def test_observation_id_recomputable():
    series = _series()
    for obs in series["observations"]:
        payload = {k: v for k, v in obs.items() if k != "observation_id"}
        assert canonical_digest(payload) == obs["observation_id"]


def test_observation_id_changes_with_fact_id():
    series_a = _series()
    ids_a = {o["observation_id"] for o in series_a["observations"]}
    # Change an input fact id and confirm the observation-id set changes.
    mutated = [dict(f) for f in REPORTED]
    payload = {
        "concept_id": mutated[0]["concept_id"],
        "symbol": mutated[0]["symbol"],
        "period_end": mutated[0]["period_end"],
        "value": mutated[0]["value"],
        "available_at": mutated[0]["available_at"],
        "effective_from": mutated[0]["effective_from"],
        "restatement_version": "original",
        "supersedes_fact_id": "",
        "source_id": "r4d:SYN-MUTATED",
    }
    mutated[0]["fact_id"] = canonical_digest(payload)
    timelines = financial_state.build_financial_state_timelines(mutated, RECONCILED)
    series_b = valuation_series.build_valuation_series(MARKET, MARKET_META, timelines)
    ids_b = {o["observation_id"] for o in series_b["observations"]}
    assert ids_a != ids_b


def test_observation_id_changes_with_market_sha():
    series_a = _series()
    obs_a = series_a["observations"][0]
    meta_b = dict(MARKET_META)
    meta_b["primary_object_sha256"] = "x" * 64
    timelines_b = financial_state.build_financial_state_timelines(REPORTED, RECONCILED)
    series_b = valuation_series.build_valuation_series(MARKET, meta_b, timelines_b)
    obs_b = series_b["observations"][0]
    assert obs_a["observation_id"] != obs_b["observation_id"]


def test_no_percentile_field():
    series = _series()
    assert series["percentile_computed"] is False
    for obs in series["observations"]:
        assert obs["percentile_computed"] is False
        assert obs["score_eligible"] is False
        assert obs["production_eligible"] is False
        assert "valuation_percentile" not in obs
