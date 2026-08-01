"""Stage 2E-B financial-safety metric definitions.

The registry is additive and deliberately separate from the frozen capital-
return registry.  Debt-based metrics bind their expanded direct facts so the
lineage graph never hides a current/long-term component or substitutes total
liabilities for gross debt.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from ashare_research.metrics.models import MetricDefinition


@dataclass(frozen=True)
class FinancialSafetyMetricDefinition(MetricDefinition):
    """A descriptive-only financial-safety definition."""

    score_eligible: bool = False


FINANCIAL_SAFETY_METRIC_DEFINITION_SCHEMA = "1.0"


class FinancialSafetyMetricStatus(StrEnum):
    """Statuses owned by the additive financial-safety extension."""

    undefined_no_debt = "undefined_no_debt"
    not_comparable_negative_debt_component = (
        "not_comparable_negative_debt_component"
    )


class FinancialSafetyMetricDefinitionRegistry:
    """Ordered, explicit registry for the four Stage 2E-B metrics."""

    schema_version = FINANCIAL_SAFETY_METRIC_DEFINITION_SCHEMA

    DEFINITIONS: dict[str, FinancialSafetyMetricDefinition] = {
        "asset_liability_ratio": FinancialSafetyMetricDefinition(
            metric_id="asset_liability_ratio",
            version="1",
            display_name_zh="资产负债率",
            formula="total_liabilities / total_assets",
            input_concept_ids=("total_liabilities", "total_assets"),
            input_roles=("numerator", "denominator"),
            unit="ratio",
        ),
        "gross_interest_bearing_debt": FinancialSafetyMetricDefinition(
            metric_id="gross_interest_bearing_debt",
            version="1",
            display_name_zh="总有息负债",
            formula=(
                "short_term_borrowings + "
                "current_portion_of_interest_bearing_non_current_liabilities + "
                "long_term_borrowings + bonds_payable + lease_liabilities"
            ),
            input_concept_ids=(
                "short_term_borrowings",
                "current_portion_of_interest_bearing_non_current_liabilities",
                "long_term_borrowings",
                "bonds_payable",
                "lease_liabilities",
            ),
            input_roles=(
                "short_term_borrowings",
                "current_portion",
                "long_term_borrowings",
                "bonds_payable",
                "lease_liabilities",
            ),
            unit="万元",
        ),
        "cash_coverage_of_interest_bearing_debt": FinancialSafetyMetricDefinition(
            metric_id="cash_coverage_of_interest_bearing_debt",
            version="1",
            display_name_zh="现金覆盖有息负债",
            formula="cash_and_cash_equivalents / gross_interest_bearing_debt",
            input_concept_ids=(
                "cash_and_cash_equivalents",
                "short_term_borrowings",
                "current_portion_of_interest_bearing_non_current_liabilities",
                "long_term_borrowings",
                "bonds_payable",
                "lease_liabilities",
            ),
            input_roles=(
                "cash",
                "short_term_borrowings",
                "current_portion",
                "long_term_borrowings",
                "bonds_payable",
                "lease_liabilities",
            ),
            unit="ratio",
        ),
        "net_interest_bearing_debt": FinancialSafetyMetricDefinition(
            metric_id="net_interest_bearing_debt",
            version="1",
            display_name_zh="净有息负债",
            formula="gross_interest_bearing_debt - cash_and_cash_equivalents",
            input_concept_ids=(
                "short_term_borrowings",
                "current_portion_of_interest_bearing_non_current_liabilities",
                "long_term_borrowings",
                "bonds_payable",
                "lease_liabilities",
                "cash_and_cash_equivalents",
            ),
            input_roles=(
                "short_term_borrowings",
                "current_portion",
                "long_term_borrowings",
                "bonds_payable",
                "lease_liabilities",
                "cash",
            ),
            unit="万元",
        ),
    }

    @classmethod
    def get(cls, metric_id: str) -> FinancialSafetyMetricDefinition | None:
        return cls.DEFINITIONS.get(metric_id)

    @classmethod
    def list_all(cls) -> list[FinancialSafetyMetricDefinition]:
        return [cls.DEFINITIONS[key] for key in cls.DEFINITIONS]
