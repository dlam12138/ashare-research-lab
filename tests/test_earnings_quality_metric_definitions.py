"""Definition contract for earnings-quality transparent metrics."""

from ashare_research.metrics.cashflow_definitions import (
    CashFlowMetricDefinitionRegistry,
)
from ashare_research.metrics.definitions import MetricDefinitionRegistry
from ashare_research.metrics.earnings_quality_definitions import (
    EarningsQualityMetricDefinitionRegistry,
)


def test_four_definitions_are_unique_versioned_and_non_scoring():
    definitions = EarningsQualityMetricDefinitionRegistry.list_all()
    assert EarningsQualityMetricDefinitionRegistry.schema_version == "1.0"
    assert len(definitions) == 4
    assert len({item.metric_id for item in definitions}) == 4
    assert {item.version for item in definitions} == {"1"}
    assert all(item.score_eligible is False for item in definitions)


def test_existing_registries_remain_disjoint_and_unchanged():
    assert len(MetricDefinitionRegistry.list_all()) == 4
    assert len(CashFlowMetricDefinitionRegistry.list_all()) == 2
    old_ids = {
        item.metric_id
        for item in [
            *MetricDefinitionRegistry.list_all(),
            *CashFlowMetricDefinitionRegistry.list_all(),
        ]
    }
    new_ids = {
        item.metric_id
        for item in EarningsQualityMetricDefinitionRegistry.list_all()
    }
    assert old_ids.isdisjoint(new_ids)


def test_formulas_inputs_and_units_are_explicit():
    registry = EarningsQualityMetricDefinitionRegistry
    assert registry.get("net_profit_excluding_non_recurring_yoy").formula == (
        "(current / prior) - 1"
    )
    assert registry.get("gross_profit").formula == "revenue - operating_cost"
    assert registry.get("gross_profit").unit == "万元"
    assert registry.get("gross_margin").formula == (
        "(revenue - operating_cost) / revenue"
    )
    assert registry.get("operating_profit_margin").formula == (
        "operating_profit / revenue"
    )
    assert {
        concept
        for definition in registry.list_all()
        for concept in definition.input_concept_ids
    } == {
        "revenue",
        "net_profit_excluding_non_recurring",
        "operating_cost",
        "operating_profit",
    }
