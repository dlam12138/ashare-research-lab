from ashare_research.metrics.cashflow_definitions import (
    CashFlowMetricDefinitionRegistry,
)
from ashare_research.metrics.definitions import (
    METRIC_DEFINITION_SCHEMA,
    MetricDefinitionRegistry,
)


def test_cashflow_definitions_are_unique_versioned_and_separate():
    definitions = CashFlowMetricDefinitionRegistry.list_all()
    assert CashFlowMetricDefinitionRegistry.schema_version == "1.0"
    assert CashFlowMetricDefinitionRegistry.schema_version == (
        METRIC_DEFINITION_SCHEMA
    )
    assert len(definitions) == 2
    assert len({item.metric_id for item in definitions}) == 2
    assert {item.version for item in definitions} == {"1"}
    assert len(MetricDefinitionRegistry.list_all()) == 4
    assert set(MetricDefinitionRegistry.DEFINITIONS) == {
        "revenue_yoy",
        "net_profit_attributable_to_parent_yoy",
        "operating_cash_flow_yoy",
        "operating_cash_flow_to_attributable_net_profit",
    }


def test_cashflow_definition_contract_is_explicit():
    free_cash_flow = CashFlowMetricDefinitionRegistry.get(
        "cash_based_free_cash_flow_proxy"
    )
    assert free_cash_flow is not None
    assert free_cash_flow.display_name_zh == "现金口径自由现金流代理"
    assert (
        free_cash_flow.formula
        == "operating_cash_flow - cash_paid_for_fixed_assets"
    )
    assert free_cash_flow.input_concept_ids == (
        "operating_cash_flow",
        "cash_paid_for_fixed_assets",
    )
    assert free_cash_flow.input_roles == (
        "operating_cash_flow",
        "cash_paid_for_fixed_assets",
    )
    assert free_cash_flow.unit == "万元"

    intensity = CashFlowMetricDefinitionRegistry.get(
        "cash_paid_for_fixed_assets_to_revenue"
    )
    assert intensity is not None
    assert intensity.display_name_zh == "购建长期资产现金支出/营业收入比率"
    assert intensity.formula == "cash_paid_for_fixed_assets / revenue"
    assert intensity.input_concept_ids == (
        "cash_paid_for_fixed_assets",
        "revenue",
    )
    assert intensity.input_roles == (
        "cash_paid_for_fixed_assets",
        "revenue",
    )
    assert intensity.unit == "ratio"
