"""M2 Stage 2K.1R4E — dual-oracle temporal join tests."""

from pathlib import Path

from ashare_research.pit_valuation import financial_state, fixtures, temporal_join
from ashare_research.pit_valuation.series_contract import METRIC_PE

REPORTED, RECONCILED = fixtures.load_fixture_bundles(Path("."))
MARKET, _ = fixtures.load_fixture_market(Path("."))


def _pe_timeline():
    return financial_state.build_financial_state_timelines(REPORTED, RECONCILED)[METRIC_PE]


def test_backward_join_selects_latest_state():
    states = _pe_timeline()
    joined = temporal_join.python_backward_join(MARKET, states)
    # A trade date well after the last state must select the latest state.
    last_eff = max(s["effective_from"] for s in states)
    sample = [
        d for d in sorted(MARKET, key=lambda r: r["trade_date"])
        if d["trade_date"] > last_eff
    ]
    if sample:
        selected = joined[sample[0]["trade_date"]]
        assert selected["effective_from"] == last_eff


def test_backward_join_before_first_state_is_none():
    states = _pe_timeline()
    first_eff = min(s["effective_from"] for s in states)
    early = [d for d in MARKET if d["trade_date"] < first_eff]
    if early:
        assert joined_for(early[0]["trade_date"], states) is None


def joined_for(trade_date, states):
    return temporal_join.python_backward_join(MARKET, states)[trade_date]


def test_no_forward_or_nearest_join():
    states = _pe_timeline()
    # A trade date before the first state must yield None (no forward/nearest).
    first_eff = min(s["effective_from"] for s in states)
    assert all(
        temporal_join.python_backward_join(MARKET, states)[d["trade_date"]] is None
        for d in MARKET
        if d["trade_date"] < first_eff
    )


def test_python_and_duckdb_identical():
    states = _pe_timeline()
    a = temporal_join.python_backward_join(MARKET, states)
    b = temporal_join.duckdb_asof_join(MARKET, states, group="PE_A_TTM")
    cmp = temporal_join.compare_oracles(a, b)
    assert cmp["identical"]
    assert cmp["mismatch_count"] == 0


def test_duckdb_never_writes_default_db():
    # The DuckDB oracle uses an in-memory connection; no file db is created.

    states = _pe_timeline()
    temporal_join.duckdb_asof_join(MARKET, states, group="PE_A_TTM")
    # No .duckdb file should be produced in the working directory.
    assert not Path("research.duckdb").exists()


def test_dedup_keeps_latest_report_period_on_tie():
    s1 = {
        "effective_from": "2023-05-04",
        "fiscal_year": 2022,
        "report_type": "q1",
        "financial_state_id": "a",
    }
    s2 = {
        "effective_from": "2023-05-04",
        "fiscal_year": 2023,
        "report_type": "q1",
        "financial_state_id": "b",
    }
    deduped = temporal_join.dedup_states_by_effective_from([s1, s2])
    assert len(deduped) == 1
    assert deduped[0]["financial_state_id"] == "b"
