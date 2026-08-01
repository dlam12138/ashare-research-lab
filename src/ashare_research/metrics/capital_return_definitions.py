"""Versioned definitions for the transparent capital-return metrics.

Stage 2D-D registers the single ROE metric whose inputs are covered by the
Stage 2C duration net-profit facts and the Stage 2D-B instant average-equity
denominator facts.  ROA is intentionally absent: its consolidated
``net_profit`` numerator has no trusted fact yet (see the Stage 2D-C capital
return methodology contract), so its computation stays blocked.
"""

from __future__ import annotations

from dataclasses import dataclass

from ashare_research.metrics.definitions import METRIC_DEFINITION_SCHEMA
from ashare_research.metrics.models import MetricDefinition


@dataclass(frozen=True)
class CapitalReturnMetricDefinition(MetricDefinition):
    """A non-scoring metric definition scoped to capital return."""

    score_eligible: bool = False


class CapitalReturnMetricDefinitionRegistry:
    """The ROE definition, kept outside the previously accepted registries."""

    schema_version = METRIC_DEFINITION_SCHEMA

    DEFINITIONS: dict[str, CapitalReturnMetricDefinition] = {
        "return_on_average_equity_attributable_to_parent": (
            CapitalReturnMetricDefinition(
                metric_id=(
                    "return_on_average_equity_attributable_to_parent"
                ),
                version="1",
                display_name_zh="基于平均归母权益的净资产收益率",
                formula=(
                    "net_profit_attributable_to_parent / "
                    "((opening_equity_attributable_to_parent + "
                    "closing_equity_attributable_to_parent) / 2)"
                ),
                input_concept_ids=(
                    "net_profit_attributable_to_parent",
                    "equity_attributable_to_parent",
                    "equity_attributable_to_parent",
                ),
                input_roles=("numerator", "opening", "closing"),
                unit="ratio",
                score_eligible=False,
            )
        ),
    }

    @classmethod
    def get(cls, metric_id: str) -> CapitalReturnMetricDefinition | None:
        return cls.DEFINITIONS.get(metric_id)

    @classmethod
    def list_all(cls) -> list[CapitalReturnMetricDefinition]:
        return [cls.DEFINITIONS[key] for key in sorted(cls.DEFINITIONS)]
