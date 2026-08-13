"""Versioned definitions for the transparent earnings-quality metrics."""

from __future__ import annotations

from dataclasses import dataclass

from ashare_research.metrics.definitions import METRIC_DEFINITION_SCHEMA
from ashare_research.metrics.models import MetricDefinition


@dataclass(frozen=True)
class EarningsQualityMetricDefinition(MetricDefinition):
    """A non-scoring metric definition scoped to earnings quality."""

    score_eligible: bool = False


class EarningsQualityMetricDefinitionRegistry:
    """Definitions kept outside the two previously accepted registries."""

    schema_version = METRIC_DEFINITION_SCHEMA

    DEFINITIONS: dict[str, EarningsQualityMetricDefinition] = {
        "net_profit_excluding_non_recurring_yoy": EarningsQualityMetricDefinition(
            metric_id="net_profit_excluding_non_recurring_yoy",
            version="1",
            display_name_zh="扣非归母净利润同比",
            formula="(current / prior) - 1",
            input_concept_ids=(
                "net_profit_excluding_non_recurring",
                "net_profit_excluding_non_recurring",
            ),
            input_roles=("current", "prior"),
        ),
        "gross_profit": EarningsQualityMetricDefinition(
            metric_id="gross_profit",
            version="1",
            display_name_zh="毛利润（营业收入减营业成本）",
            formula="revenue - operating_cost",
            input_concept_ids=("revenue", "operating_cost"),
            input_roles=("revenue", "operating_cost"),
            unit="万元",
        ),
        "gross_margin": EarningsQualityMetricDefinition(
            metric_id="gross_margin",
            version="1",
            display_name_zh="毛利率",
            formula="(revenue - operating_cost) / revenue",
            input_concept_ids=("revenue", "operating_cost"),
            input_roles=("revenue", "operating_cost"),
        ),
        "operating_profit_margin": EarningsQualityMetricDefinition(
            metric_id="operating_profit_margin",
            version="1",
            display_name_zh="营业利润率",
            formula="operating_profit / revenue",
            input_concept_ids=("operating_profit", "revenue"),
            input_roles=("operating_profit", "revenue"),
        ),
    }

    @classmethod
    def get(cls, metric_id: str) -> EarningsQualityMetricDefinition | None:
        return cls.DEFINITIONS.get(metric_id)

    @classmethod
    def list_all(cls) -> list[EarningsQualityMetricDefinition]:
        return [cls.DEFINITIONS[key] for key in sorted(cls.DEFINITIONS)]
