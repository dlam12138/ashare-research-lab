"""Versioned definitions for the cash-flow metric extension."""

from __future__ import annotations

from ashare_research.metrics.definitions import METRIC_DEFINITION_SCHEMA
from ashare_research.metrics.models import MetricDefinition


class CashFlowMetricDefinitionRegistry:
    """Definitions intentionally kept outside the Stage 2A registry."""

    schema_version = METRIC_DEFINITION_SCHEMA

    DEFINITIONS: dict[str, MetricDefinition] = {
        "cash_based_free_cash_flow_proxy": MetricDefinition(
            metric_id="cash_based_free_cash_flow_proxy",
            version="1",
            display_name_zh="现金口径自由现金流代理",
            formula="operating_cash_flow - cash_paid_for_fixed_assets",
            input_concept_ids=(
                "operating_cash_flow",
                "cash_paid_for_fixed_assets",
            ),
            input_roles=(
                "operating_cash_flow",
                "cash_paid_for_fixed_assets",
            ),
            unit="万元",
        ),
        "cash_paid_for_fixed_assets_to_revenue": MetricDefinition(
            metric_id="cash_paid_for_fixed_assets_to_revenue",
            version="1",
            display_name_zh="购建长期资产现金支出/营业收入比率",
            formula="cash_paid_for_fixed_assets / revenue",
            input_concept_ids=("cash_paid_for_fixed_assets", "revenue"),
            input_roles=("cash_paid_for_fixed_assets", "revenue"),
        ),
    }

    @classmethod
    def get(cls, metric_id: str) -> MetricDefinition | None:
        return cls.DEFINITIONS.get(metric_id)

    @classmethod
    def list_all(cls) -> list[MetricDefinition]:
        return [cls.DEFINITIONS[key] for key in sorted(cls.DEFINITIONS)]
