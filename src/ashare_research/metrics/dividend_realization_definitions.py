"""Transparent, non-score-eligible dividend realization metrics."""

from __future__ import annotations

from dataclasses import dataclass

from ashare_research.metrics.models import MetricDefinition


@dataclass(frozen=True)
class DividendRealizationMetricDefinition(MetricDefinition):
    score_eligible: bool = False


class DividendRealizationMetricDefinitionRegistry:
    schema_version = "1.0"
    DEFINITIONS = {
        "cash_dividend_payout_ratio": DividendRealizationMetricDefinition(
            metric_id="cash_dividend_payout_ratio",
            version="1",
            display_name_zh="已实施现金分红支付率",
            formula="implemented_cash_dividend_total / net_profit_attributable_to_parent",
            input_concept_ids=("cash_dividend_total", "net_profit_attributable_to_parent"),
            input_roles=("implemented_dividend", "net_profit"),
            unit="ratio",
        ),
        "operating_cash_flow_dividend_coverage": DividendRealizationMetricDefinition(
            metric_id="operating_cash_flow_dividend_coverage",
            version="1",
            display_name_zh="经营现金流分红覆盖倍数",
            formula="operating_cash_flow / implemented_cash_dividend_total",
            input_concept_ids=("operating_cash_flow", "cash_dividend_total"),
            input_roles=("operating_cash_flow", "implemented_dividend"),
            unit="ratio",
        ),
        "free_cash_flow_proxy_dividend_coverage": DividendRealizationMetricDefinition(
            metric_id="free_cash_flow_proxy_dividend_coverage",
            version="1",
            display_name_zh="自由现金流代理分红覆盖倍数",
            formula=(
                "(operating_cash_flow - cash_paid_for_fixed_assets) / "
                "implemented_cash_dividend_total"
            ),
            input_concept_ids=(
                "operating_cash_flow",
                "cash_paid_for_fixed_assets",
                "cash_dividend_total",
            ),
            input_roles=(
                "operating_cash_flow",
                "cash_paid_for_fixed_assets",
                "implemented_dividend",
            ),
            unit="ratio",
        ),
        "implemented_cash_dividend_per_share": DividendRealizationMetricDefinition(
            metric_id="implemented_cash_dividend_per_share",
            version="1",
            display_name_zh="已实施现金分红每股金额",
            formula="sum(implemented_cash_dividend_per_share_events)",
            input_concept_ids=("cash_dividend_per_share",),
            input_roles=("implemented_per_share",),
            unit="CNY_PER_SHARE",
        ),
    }

    @classmethod
    def get(cls, metric_id: str) -> DividendRealizationMetricDefinition | None:
        return cls.DEFINITIONS.get(metric_id)

    @classmethod
    def list_all(cls) -> list[DividendRealizationMetricDefinition]:
        return list(cls.DEFINITIONS.values())
