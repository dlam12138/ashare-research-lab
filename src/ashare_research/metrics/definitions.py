"""The minimal, explicit, versioned metric definition registry."""

from __future__ import annotations

from ashare_research.metrics.models import MetricDefinition

METRIC_DEFINITION_SCHEMA = "1.0"


class MetricDefinitionRegistry:
    schema_version = METRIC_DEFINITION_SCHEMA

    DEFINITIONS: dict[str, MetricDefinition] = {
        "revenue_yoy": MetricDefinition(
            metric_id="revenue_yoy",
            version="1",
            display_name_zh="营业收入同比",
            formula="(current / prior) - 1",
            input_concept_ids=("revenue", "revenue"),
            input_roles=("current", "prior"),
        ),
        "net_profit_attributable_to_parent_yoy": MetricDefinition(
            metric_id="net_profit_attributable_to_parent_yoy",
            version="1",
            display_name_zh="归属于母公司股东的净利润同比",
            formula="(current / prior) - 1",
            input_concept_ids=(
                "net_profit_attributable_to_parent",
                "net_profit_attributable_to_parent",
            ),
            input_roles=("current", "prior"),
        ),
        "operating_cash_flow_yoy": MetricDefinition(
            metric_id="operating_cash_flow_yoy",
            version="1",
            display_name_zh="经营活动产生的现金流量净额同比",
            formula="(current / prior) - 1",
            input_concept_ids=("operating_cash_flow", "operating_cash_flow"),
            input_roles=("current", "prior"),
        ),
        "operating_cash_flow_to_attributable_net_profit": MetricDefinition(
            metric_id="operating_cash_flow_to_attributable_net_profit",
            version="1",
            display_name_zh="经营现金流/归母净利润比率",
            formula="numerator / denominator",
            input_concept_ids=(
                "operating_cash_flow",
                "net_profit_attributable_to_parent",
            ),
            input_roles=("numerator", "denominator"),
        ),
    }

    @classmethod
    def get(cls, metric_id: str) -> MetricDefinition | None:
        return cls.DEFINITIONS.get(metric_id)

    @classmethod
    def list_all(cls) -> list[MetricDefinition]:
        return [cls.DEFINITIONS[key] for key in sorted(cls.DEFINITIONS)]
