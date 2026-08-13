"""M2 Stage 2K.1R4E — series contract tests."""

from decimal import Decimal

import pytest

from ashare_research.pit_valuation import series_contract


def test_validate_all_contracts_returns_four_digests():
    digests = series_contract.validate_all_contracts()
    assert set(digests) == {
        "formula_registry_digest",
        "methodology_v2_digest",
        "market_snapshot_registry_digest",
        "share_continuity_register_digest",
    }
    for digest in digests.values():
        assert len(digest) == 64


def test_methodology_v2_supersedes_v1():
    methodology = series_contract.load_methodology_v2()
    assert methodology["supersedes"] == "value_evaluation_methodology_valuation_pit_v1"
    assert methodology["production_eligible"] is False
    assert methodology["score_eligible"] is False
    series_contract.validate_methodology_v2(methodology)


def test_formula_registry_freeze():
    registry = series_contract.load_formula_registry()
    series_contract.validate_formula_registry(registry)
    metric_ids = {f["metric_id"] for f in registry["formulas"]}
    assert metric_ids == {"PE_A_TTM", "PB_A_MRQ", "PS_A_TTM"}
    for formula in registry["formulas"]:
        assert formula["unit"] == "dimensionless"
        assert formula["prohibited_fallbacks"]


def test_parse_decimal_never_uses_binary_float():
    # Decimal(str(181.0)) == Decimal('181'); Decimal(181.0) would be lossy.
    assert series_contract.parse_decimal(181.0) == Decimal("181")
    assert series_contract.parse_decimal("101.25") == Decimal("101.25")
    assert series_contract.parse_decimal(Decimal("7")) == Decimal("7")


def test_status_enum_frozen():
    assert "computed" in series_contract.STATUS_ENUM
    assert "missing_ttm_input" in series_contract.STATUS_ENUM
    assert "BLOCKED_EXTERNAL_MARKET_CACHE_UNAVAILABLE" in series_contract.STATUS_ENUM
    assert "nonpositive_earnings" in series_contract.STATUS_ENUM


def test_first_trade_day_at_or_after():
    dates = ["2021-07-30", "2021-08-02", "2021-08-03"]
    # 2021-07-31 (Saturday) is not a trade day -> first trade day is 2021-08-02.
    assert series_contract.first_trade_day_at_or_after("2021-07-31", dates) == "2021-08-02"
    assert series_contract.first_trade_day_at_or_after("2021-08-02", dates) == "2021-08-02"


def test_invalid_market_snapshot_registry_rejected():
    registry = series_contract.load_market_snapshot_registry()
    bad = dict(registry)
    bad["reconciliation_status"] = "fail"
    with pytest.raises(ValueError):
        series_contract.validate_market_snapshot_registry(bad)


def test_constant_shares_frozen():
    assert Decimal("183020977818") == series_contract.CONSTANT_TOTAL_SHARES
