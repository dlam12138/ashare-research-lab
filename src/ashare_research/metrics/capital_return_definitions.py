"""Versioned definitions for the transparent capital-return metrics.

The capital-return registry contains the transparent ROE and ROA definitions.
Their input coverage and computation are staged separately by the offline
acceptance runners; the definitions themselves remain non-scoring.
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
    """Ordered definitions for the transparent capital-return layer."""

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
        "return_on_average_total_assets": CapitalReturnMetricDefinition(
            metric_id="return_on_average_total_assets",
            version="1",
            display_name_zh="基于平均总资产的资产收益率",
            formula=(
                "net_profit / "
                "((opening_total_assets + closing_total_assets) / 2)"
            ),
            input_concept_ids=("net_profit", "total_assets", "total_assets"),
            input_roles=("numerator", "opening", "closing"),
            unit="ratio",
            score_eligible=False,
        ),
    }

    @classmethod
    def get(cls, metric_id: str) -> CapitalReturnMetricDefinition | None:
        return cls.DEFINITIONS.get(metric_id)

    @classmethod
    def list_all(
        cls, *, include_roa: bool = False
    ) -> list[CapitalReturnMetricDefinition]:
        """List definitions while preserving the frozen Stage 2D-D view.

        The legacy ROE runner calls this method without arguments and must
        continue rebuilding the frozen 70-result baseline. Stage 2D-F opts
        into the appended ROA definition explicitly; both views retain the
        canonical sorted order, with ROE before ROA.
        """
        keys = sorted(cls.DEFINITIONS)
        if not include_roa:
            keys = [
                key for key in keys
                if key != "return_on_average_total_assets"
            ]
        return [cls.DEFINITIONS[key] for key in keys]
