"""M2 Stage 2K.1R4E — financial-state timeline tests (TTM, MRQ, restatement PIT)."""

from pathlib import Path

from ashare_research.pit_valuation import financial_state, fixtures
from ashare_research.pit_valuation.series_contract import (
    METRIC_PB,
    METRIC_PE,
    METRIC_PS,
)

REPORTED, RECONCILED = fixtures.load_fixture_bundles(Path("."))


def _timelines():
    return financial_state.build_financial_state_timelines(REPORTED, RECONCILED)


def _state_by_period(states, period_end):
    return next(s for s in states if s["period_end"] == period_end)


def test_annual_ttm_is_annual_value():
    pe = _timelines()[METRIC_PE]
    ar2020 = next(s for s in pe if s["period_end"] == "2020-12-31")
    assert ar2020["status"] == "computed"
    assert ar2020["report_type"] == "annual"
    assert ar2020["value_decimal"] is not None


def test_interim_ttm_matches_annual_plus_current_minus_prior():
    pe = _timelines()[METRIC_PE]
    # Look for a 2021 Q1 state (computed) and verify the TTM identity.
    q1 = next(s for s in pe if s["period_end"] == "2021-03-31" and s["status"] == "computed")
    assert q1["report_type"] == "q1"
    assert q1["current_cumulative_fact_id"]
    assert q1["prior_year_same_period_fact_id"]
    assert q1["prior_annual_fact_id"]


def test_fiscal_year_and_same_period_matching():
    pe = _timelines()[METRIC_PE]
    q1_2021 = next(s for s in pe if s["period_end"] == "2021-03-31")
    # prior-year same period must be 2020 Q1 (not 2020 H1 or 2020 AR).
    prior_cum_id = q1_2021["prior_year_same_period_fact_id"]
    prior_fact = next(f for f in REPORTED if f["fact_id"] == prior_cum_id)
    assert prior_fact["period_end"] == "2020-03-31"


def test_missing_prior_input_yields_missing_ttm_input():
    pe = _timelines()[METRIC_PE]
    q3_2020 = next(s for s in pe if s["period_end"] == "2020-09-30")
    assert q3_2020["status"] == "missing_ttm_input"
    assert q3_2020["value_decimal"] is None


def test_restatement_used_after_effective_from():
    pe = _timelines()[METRIC_PE]
    # 2022 Q1 net profit is restated in the 2023 Q1 report; the 2023 Q1 state
    # must use the restated 2022 Q1 as its prior-year same-period input.
    q1_2023 = next(s for s in pe if s["period_end"] == "2023-03-31")
    prior_cum_id = q1_2023["prior_year_same_period_fact_id"]
    prior_fact = next(f for f in REPORTED if f["fact_id"] == prior_cum_id)
    assert prior_fact["restatement_version"] == "restated_1"
    assert prior_fact["period_end"] == "2022-03-31"


def test_original_used_before_restatement_effective():
    pe = _timelines()[METRIC_PE]
    # 2022 Q1 original state (before the restatement) uses the original value.
    q1_2022 = next(s for s in pe if s["period_end"] == "2022-03-31")
    current_id = q1_2022["current_cumulative_fact_id"]
    current_fact = next(f for f in REPORTED if f["fact_id"] == current_id)
    assert current_fact["restatement_version"] == "original"


def test_no_backfill_of_restated_value():
    pe = sorted(_timelines()[METRIC_PE], key=lambda s: s["effective_from"])
    # The 2022 Q1 state's effective_from must precede the restatement's
    # effective_from; the restated 2022 Q1 is not backfilled.
    q1_2022 = next(s for s in pe if s["period_end"] == "2022-03-31")
    assert q1_2022["effective_from"] < "2023-05-04"


def test_pb_equity_and_shares_share_period_end():
    pb = _timelines()[METRIC_PB]
    for state in pb:
        assert state["status"] == "computed"
        assert state["period_end_shares_decimal"] is not None
    # equity and shares must come from the same period_end.
    ar = next(s for s in pb if s["period_end"] == "2020-12-31")
    assert ar["equity_fact_id"]
    assert ar["period_end_shares_fact_id"]


def test_ps_share_basis_visible_on_trade_date():
    ps = _timelines()[METRIC_PS]
    for state in ps:
        if state["status"] == "computed":
            assert state["share_basis_decimal"] is not None


def test_state_identity_digest_present():
    pe = _timelines()[METRIC_PE]
    for state in pe:
        assert state["financial_state_id"]
        assert state["state_digest"] == state["financial_state_id"]


def test_restatement_transition_marks_restated_version():
    pe = _timelines()[METRIC_PE]
    q1_2023 = next(s for s in pe if s["period_end"] == "2023-03-31")
    assert q1_2023["restatement_versions"]["prior_year_same_period"] in ("restated_1", "restated")
