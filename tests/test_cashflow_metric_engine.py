from decimal import Decimal
from pathlib import Path

import pytest

from ashare_research.metrics.cashflow_definitions import (
    CashFlowMetricDefinitionRegistry,
)
from ashare_research.metrics.definitions import MetricDefinitionRegistry
from ashare_research.metrics.engine import MetricEngine
from ashare_research.metrics.models import MetricStatus


def _fact(concept: str, value: int, year: int = 2023) -> dict:
    return {
        "fact_id": f"{concept}-{year}-{value}",
        "concept_id": concept,
        "value": value,
        "unit": "万元",
        "source_tier": "reconciled_derived",
        "eligible_for_metrics": True,
        "fact_version": 1,
        "restatement_version": "original",
        "available_at": f"{year + 1}-03-30",
        "period_end": f"{year}-12-31",
    }


def _cashflow_compute(
    metric_id: str,
    primary: dict | None,
    secondary: dict | None,
):
    return MetricEngine.compute(
        CashFlowMetricDefinitionRegistry.get(metric_id),
        symbol="601857.SH",
        fiscal_year=2023,
        primary_fact=primary,
        secondary_fact=secondary,
        revision_review_status="reviewed_unchanged",
        as_of_date="2024-03-30",
    )


def _stage2a_compute(metric_id: str, primary: dict, secondary: dict):
    return MetricEngine.compute(
        MetricDefinitionRegistry.get(metric_id),
        symbol="601857.SH",
        fiscal_year=2023,
        primary_fact=primary,
        secondary_fact=secondary,
        revision_review_status="reviewed_unchanged",
        as_of_date="2024-03-30",
    )[0]


def test_free_cash_flow_proxy_uses_exact_quantized_decimal_subtraction():
    result, lineage = _cashflow_compute(
        "cash_based_free_cash_flow_proxy",
        _fact("operating_cash_flow", 10),
        _fact("cash_paid_for_fixed_assets", 3),
    )
    assert result.status == MetricStatus.computed
    assert result.value == Decimal("7.000000000000")
    assert result.unit == "万元"
    assert [item.input_role for item in lineage] == [
        "operating_cash_flow",
        "cash_paid_for_fixed_assets",
    ]


def test_free_cash_flow_proxy_allows_negative_result():
    result, _ = _cashflow_compute(
        "cash_based_free_cash_flow_proxy",
        _fact("operating_cash_flow", 3),
        _fact("cash_paid_for_fixed_assets", 10),
    )
    assert result.status == MetricStatus.computed
    assert result.value == Decimal("-7.000000000000")


def test_cash_paid_to_revenue_uses_half_even_decimal_division():
    result, lineage = _cashflow_compute(
        "cash_paid_for_fixed_assets_to_revenue",
        _fact("cash_paid_for_fixed_assets", 2),
        _fact("revenue", 3),
    )
    assert result.status == MetricStatus.computed
    assert result.value == Decimal("0.666666666667")
    assert [item.input_role for item in lineage] == [
        "cash_paid_for_fixed_assets",
        "revenue",
    ]


@pytest.mark.parametrize(
    ("revenue", "expected"),
    [
        (0, MetricStatus.undefined_zero_denominator),
        (-1, MetricStatus.not_comparable_negative_revenue),
    ],
)
def test_cash_paid_to_non_positive_revenue_has_explicit_status(
    revenue: int,
    expected: MetricStatus,
):
    result, _ = _cashflow_compute(
        "cash_paid_for_fixed_assets_to_revenue",
        _fact("cash_paid_for_fixed_assets", 2),
        _fact("revenue", revenue),
    )
    assert result.status == expected
    assert result.value is None


def test_missing_cashflow_input_is_not_zero():
    result, lineage = _cashflow_compute(
        "cash_based_free_cash_flow_proxy",
        _fact("operating_cash_flow", 10),
        None,
    )
    assert result.status == MetricStatus.missing_input
    assert result.value is None
    assert len(lineage) == 1


def test_existing_formula_results_and_statuses_are_unchanged():
    yoy = _stage2a_compute(
        "revenue_yoy",
        _fact("revenue", 3),
        _fact("revenue", 2, 2022),
    )
    ratio = _stage2a_compute(
        "operating_cash_flow_to_attributable_net_profit",
        _fact("operating_cash_flow", 10),
        _fact("net_profit_attributable_to_parent", 4),
    )
    non_positive = _stage2a_compute(
        "operating_cash_flow_to_attributable_net_profit",
        _fact("operating_cash_flow", 10),
        _fact("net_profit_attributable_to_parent", 0),
    )
    assert (yoy.status, yoy.value) == (
        MetricStatus.computed,
        Decimal("0.500000000000"),
    )
    assert (ratio.status, ratio.value) == (
        MetricStatus.computed,
        Decimal("2.500000000000"),
    )
    assert non_positive.status == (
        MetricStatus.not_comparable_non_positive_profit
    )
    assert non_positive.value is None


def test_metric_engine_does_not_convert_inputs_to_float():
    source = Path("src/ashare_research/metrics/engine.py").read_text(
        encoding="utf-8"
    )
    assert "float(" not in source
