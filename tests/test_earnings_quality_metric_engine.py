"""Decimal and status behavior for earnings-quality formulas."""

from __future__ import annotations

from decimal import Decimal

import pytest

from ashare_research.metrics.earnings_quality_definitions import (
    EarningsQualityMetricDefinitionRegistry,
)
from ashare_research.metrics.engine import MetricEngine
from ashare_research.metrics.models import MetricStatus


def _fact(
    value: int,
    concept_id: str,
    *,
    year: int = 2025,
    fact_id: str | None = None,
) -> dict:
    return {
        "fact_id": fact_id or f"{concept_id}-{year}-{value}",
        "concept_id": concept_id,
        "value": value,
        "unit": "万元",
        "source_tier": "reconciled_derived",
        "eligible_for_metrics": True,
        "fact_version": 1,
        "restatement_version": "original",
        "available_at": f"{year + 1}-03-31",
        "period_end": f"{year}-12-31",
    }


def _compute(metric_id: str, primary: dict | None, secondary: dict | None):
    return MetricEngine.compute(
        EarningsQualityMetricDefinitionRegistry.get(metric_id),
        symbol="601857.SH",
        fiscal_year=2025,
        primary_fact=primary,
        secondary_fact=secondary,
        missing_prior_is_history=secondary is None,
        revision_review_status="not_yet_reviewable",
        as_of_date="2026-03-31",
        created_at="2026-03-31T00:00:00+08:00",
    )[0]


def test_decimal_gross_profit_and_margins():
    revenue = _fact(1000, "revenue")
    cost = _fact(750, "operating_cost")
    profit = _fact(125, "operating_profit")
    gross = _compute("gross_profit", revenue, cost)
    margin = _compute("gross_margin", revenue, cost)
    operating = _compute("operating_profit_margin", profit, revenue)
    assert gross.value == Decimal("250.000000000000")
    assert margin.value == Decimal("0.250000000000")
    assert operating.value == Decimal("0.125000000000")


@pytest.mark.parametrize("metric_id", ["gross_margin", "operating_profit_margin"])
def test_revenue_zero_and_negative_statuses(metric_id: str):
    numerator = (
        _fact(100, "operating_profit")
        if metric_id == "operating_profit_margin"
        else _fact(0, "revenue")
    )
    zero_revenue = _fact(0, "revenue")
    negative_revenue = _fact(-1, "revenue")
    if metric_id == "gross_margin":
        zero = _compute(metric_id, zero_revenue, _fact(10, "operating_cost"))
        negative = _compute(
            metric_id, negative_revenue, _fact(10, "operating_cost")
        )
    else:
        zero = _compute(metric_id, numerator, zero_revenue)
        negative = _compute(metric_id, numerator, negative_revenue)
    assert zero.status == MetricStatus.undefined_zero_denominator
    assert zero.value is None
    assert negative.status == MetricStatus.not_comparable_negative_revenue
    assert negative.value is None


def test_negative_gross_and_operating_profit_are_computed():
    revenue = _fact(100, "revenue")
    cost = _fact(125, "operating_cost")
    operating_profit = _fact(-20, "operating_profit")
    assert _compute("gross_profit", revenue, cost).value == Decimal(
        "-25.000000000000"
    )
    assert _compute("gross_margin", revenue, cost).value == Decimal(
        "-0.250000000000"
    )
    assert _compute(
        "operating_profit_margin", operating_profit, revenue
    ).value == Decimal("-0.200000000000")


def test_yoy_missing_prior_is_insufficient_history():
    current = _fact(100, "net_profit_excluding_non_recurring")
    result = _compute("net_profit_excluding_non_recurring_yoy", current, None)
    assert result.status == MetricStatus.insufficient_history
    assert result.value is None


@pytest.mark.parametrize(
    ("prior", "status"),
    [
        (0, MetricStatus.undefined_zero_denominator),
        (-1, MetricStatus.not_comparable_negative_prior),
    ],
)
def test_yoy_denominator_rules(prior: int, status: MetricStatus):
    result = _compute(
        "net_profit_excluding_non_recurring_yoy",
        _fact(100, "net_profit_excluding_non_recurring"),
        _fact(prior, "net_profit_excluding_non_recurring", year=2024),
    )
    assert result.status == status
    assert result.value is None
