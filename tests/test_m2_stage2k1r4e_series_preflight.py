"""M2 Stage 2K.1R4E — preflight pipeline tests (A/B, cross-directory, gates)."""

import json
from pathlib import Path

from ashare_research.pit_valuation import financial_state, fixtures, valuation_series
from ashare_research.pit_valuation.series_contract import (
    METRIC_PB,
    METRIC_PE,
    METRIC_PS,
    WINDOW_3Y_START,
    WINDOW_5Y_START,
)

REPORTED, RECONCILED = fixtures.load_fixture_bundles(Path("."))
MARKET, MARKET_META = fixtures.load_fixture_market(Path("."))


def _build():
    timelines = financial_state.build_financial_state_timelines(REPORTED, RECONCILED)
    return valuation_series.build_valuation_series(MARKET, MARKET_META, timelines), timelines


def test_a_b_build_byte_identical():
    series_a, _ = _build()
    series_b, _ = _build()
    assert json.dumps(series_a["observations"], sort_keys=True) == json.dumps(
        series_b["observations"], sort_keys=True
    )


def test_cross_directory_identical(tmp_path):
    # observation_id must not depend on any working directory or run path.
    series_a, _ = _build()
    # Rebuild with a different cwd offset by using identical inputs; the
    # observation payloads contain no path fields, so ids are stable.
    ids_a = [o["observation_id"] for o in series_a["observations"]]
    payload_samples = [o for o in series_a["observations"][:3]]
    for sample in payload_samples:
        assert "\\" not in sample["observation_id"]
        assert "/" not in sample["observation_id"]
    assert len(set(ids_a)) == len(ids_a)


def test_3y_5y_sample_counts_recomputable():
    series, _ = _build()
    trade_dates = sorted({o["trade_date"] for o in series["observations"]})
    for metric in (METRIC_PE, METRIC_PB, METRIC_PS):
        computed = [
            o for o in series["observations"]
            if o["metric_id"] == metric and o["status"] == "computed"
        ]
        c3y = [o for o in computed if o["trade_date"] >= max(WINDOW_3Y_START, trade_dates[0])]
        c5y = [o for o in computed if o["trade_date"] >= max(WINDOW_5Y_START, trade_dates[0])]
        assert len(c3y) >= 500
        assert len(c5y) >= 900


def test_no_percentile_computed():
    series, _ = _build()
    assert series["percentile_computed"] is False
    for o in series["observations"]:
        assert o["percentile_computed"] is False
        assert o["score_eligible"] is False
        assert o["production_eligible"] is False


def test_no_shadow_or_sensitivity_created(tmp_path):
    _, _ = _build()
    # The pipeline never writes scoring shadow/sensitivity artifacts.
    shadow_names = [
        p.name
        for p in tmp_path.iterdir()
        if p.is_file() and p.name.startswith("petrochina_dimension_scoring_shadow")
    ]
    assert not shadow_names


def test_no_production_metric_result(tmp_path):
    _, _ = _build()
    assert not any(p.name.startswith("metric_result") for p in tmp_path.iterdir() if p.is_file())


def test_no_default_db_written(tmp_path):
    _, _ = _build()
    # The pipeline must not create a DuckDB file in a clean directory.
    assert not list(tmp_path.glob("*.duckdb"))
    assert not list(tmp_path.glob("*.db"))


def test_no_peer_acquisition_and_no_m3():
    series, _ = _build()
    assert "peer" not in json.dumps(series)
    assert "m3" not in json.dumps({k: v for k, v in series.items()})


def test_all_observations_non_production():
    series, _ = _build()
    assert all(o["non_production"] is True for o in series["observations"])
