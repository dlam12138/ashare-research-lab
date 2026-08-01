"""Formula engine for the additive Stage 2E-B financial-safety layer."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime
from decimal import ROUND_HALF_EVEN, Context, Decimal, localcontext
from typing import Any

from ashare_research.metrics.engine import (
    CANONICAL_QUANTUM,
    MetricInputError,
    _fact_integer,
    _lineage,
)
from ashare_research.metrics.financial_safety_definitions import (
    FinancialSafetyMetricStatus,
)
from ashare_research.metrics.identity import build_metric_result_id
from ashare_research.metrics.models import (
    MetricDefinition,
    MetricLineage,
    MetricResult,
    MetricStatus,
)

DECIMAL_PRECISION = 28


class FinancialSafetyMetricEngine:
    """Compute only the four registered safety metrics with explicit roles."""

    @staticmethod
    def compute(
        definition: MetricDefinition,
        *,
        symbol: str,
        fiscal_year: int,
        role_facts: dict[str, dict[str, Any] | None],
        revision_review_status: str,
        as_of_date: str,
        result_version: int = 1,
        supersedes_metric_result_id: str = "",
        created_at: str | None = None,
    ) -> tuple[MetricResult, list[MetricLineage]]:
        expected_roles = set(definition.input_roles)
        if set(role_facts) != expected_roles:
            raise MetricInputError(
                "role_facts must contain exactly the definition input roles"
            )
        bindings = [
            (role, role_facts[role]) for role in definition.input_roles
        ]
        present = [(role, fact) for role, fact in bindings if fact is not None]
        for _role, fact in present:
            _fact_integer(fact)
        input_fact_ids = tuple(str(fact["fact_id"]) for _role, fact in present)
        available_at = (
            max(str(fact["available_at"]) for _role, fact in present)
            if present
            else as_of_date
        )
        primary_fact = bindings[0][1]
        period_end = (
            str(primary_fact["period_end"])
            if primary_fact is not None
            else f"{fiscal_year}-12-31"
        )
        missing_role = next(
            (role for role, fact in bindings if fact is None), None
        )
        status: MetricStatus | FinancialSafetyMetricStatus = MetricStatus.computed
        value: Decimal | None = None
        missing = ""
        if missing_role is not None:
            role_index = definition.input_roles.index(missing_role)
            status = MetricStatus.missing_input
            missing = (
                f"role={missing_role};"
                f"concept_id={definition.input_concept_ids[role_index]};"
                f"fiscal_year={fiscal_year}"
            )
        else:
            role_values = {
                role: Decimal(_fact_integer(fact))
                for role, fact in bindings
                if fact is not None
            }
            with localcontext(
                Context(prec=DECIMAL_PRECISION, rounding=ROUND_HALF_EVEN)
            ):
                if definition.metric_id == "asset_liability_ratio":
                    denominator = role_values["denominator"]
                    if denominator == 0:
                        status = MetricStatus.undefined_zero_denominator
                    elif denominator < 0:
                        status = MetricStatus.not_comparable_negative_denominator
                    else:
                        value = (
                            role_values["numerator"] / denominator
                        ).quantize(CANONICAL_QUANTUM, rounding=ROUND_HALF_EVEN)
                elif definition.metric_id == "gross_interest_bearing_debt":
                    value_or_status = _gross_debt(role_values)
                    if isinstance(value_or_status, Decimal):
                        value = value_or_status
                    else:
                        status = value_or_status
                elif definition.metric_id == "cash_coverage_of_interest_bearing_debt":
                    gross = _gross_debt(role_values)
                    if not isinstance(gross, Decimal):
                        status = gross
                    elif gross == 0:
                        status = FinancialSafetyMetricStatus.undefined_no_debt
                    else:
                        value = (
                            role_values["cash"] / gross
                        ).quantize(CANONICAL_QUANTUM, rounding=ROUND_HALF_EVEN)
                elif definition.metric_id == "net_interest_bearing_debt":
                    gross = _gross_debt(role_values)
                    if not isinstance(gross, Decimal):
                        status = gross
                    else:
                        value = (gross - role_values["cash"]).quantize(
                            CANONICAL_QUANTUM, rounding=ROUND_HALF_EVEN
                        )
                else:
                    raise MetricInputError(
                        f"unsupported financial-safety metric: {definition.metric_id}"
                    )
        result = MetricResult(
            metric_id=definition.metric_id,
            metric_definition_version=definition.version,
            symbol=symbol,
            fiscal_year=fiscal_year,
            period_end=period_end,
            result_version=result_version,
            supersedes_metric_result_id=supersedes_metric_result_id,
            status=status,
            value=value,
            unit=definition.unit,
            formula=definition.formula,
            available_at=available_at,
            input_fact_ids=input_fact_ids,
            missing_input_description=missing,
            revision_review_status=revision_review_status,
            created_at=created_at or datetime.now().isoformat(),
        )
        result = replace(result, metric_result_id=build_metric_result_id(result))
        lineage = [
            _lineage(result.metric_result_id, role, fact)
            for role, fact in present
        ]
        return result, lineage


def _gross_debt(
    values: dict[str, Decimal],
) -> Decimal | FinancialSafetyMetricStatus:
    roles = (
        "short_term_borrowings",
        "current_portion",
        "long_term_borrowings",
        "bonds_payable",
        "lease_liabilities",
    )
    if any(values[role] < 0 for role in roles):
        return FinancialSafetyMetricStatus.not_comparable_negative_debt_component
    return sum((values[role] for role in roles), Decimal(0)).quantize(
        CANONICAL_QUANTUM, rounding=ROUND_HALF_EVEN
    )
