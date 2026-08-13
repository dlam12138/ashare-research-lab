from ashare_research.metrics.definitions import (
    METRIC_DEFINITION_SCHEMA,
    MetricDefinitionRegistry,
)


def test_four_metric_definitions_are_unique_and_versioned():
    definitions = MetricDefinitionRegistry.list_all()
    assert METRIC_DEFINITION_SCHEMA == "1.0"
    assert len(definitions) == 4
    assert len({item.metric_id for item in definitions}) == 4
    assert {item.version for item in definitions} == {"1"}
    assert {item.unit for item in definitions} == {"ratio"}


def test_metric_names_and_formulas_are_explicit():
    registry = MetricDefinitionRegistry
    assert registry.get("revenue_yoy").formula == "(current / prior) - 1"
    assert (
        registry.get("net_profit_attributable_to_parent_yoy").display_name_zh
        == "归属于母公司股东的净利润同比"
    )
    ratio = registry.get(
        "operating_cash_flow_to_attributable_net_profit"
    )
    assert ratio.display_name_zh == "经营现金流/归母净利润比率"
    assert ratio.formula == "numerator / denominator"
