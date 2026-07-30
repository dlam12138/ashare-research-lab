"""Decimal-only calculation engine for the four Stage 2A metrics."""

from __future__ import annotations

import math
from dataclasses import replace
from datetime import datetime
from decimal import ROUND_HALF_EVEN, Context, Decimal, localcontext
from typing import Any

from ashare_research.metrics.identity import build_metric_result_id
from ashare_research.metrics.models import (
    MetricDefinition,
    MetricLineage,
    MetricResult,
    MetricStatus,
)

DECIMAL_PRECISION = 28
CANONICAL_QUANTUM = Decimal("0.000000000001")
MAX_SAFE_INTEGER = 2**53 - 1


class MetricInputError(ValueError):
    """A fact cannot safely be used by the metric layer."""


def _fact_integer(fact: dict[str, Any]) -> int:
    value = fact.get("value")
    if isinstance(value, bool) or value is None:
        raise MetricInputError("metric fact value must be a finite integer")
    if isinstance(value, Decimal):
        if not value.is_finite() or value != value.to_integral_value():
            raise MetricInputError("metric fact value must be a finite integer")
        integer = int(value)
    elif isinstance(value, int):
        integer = value
    elif isinstance(value, float):
        if not math.isfinite(value) or not value.is_integer():
            raise MetricInputError("metric fact value must be a finite integer")
        integer = int(value)
    else:
        raise MetricInputError("metric fact value must be numeric")
    if abs(integer) > MAX_SAFE_INTEGER:
        raise MetricInputError("metric fact value exceeds 2^53-1")
    if fact.get("unit") != "万元":
        raise MetricInputError("metric fact unit must be 万元")
    if fact.get("source_tier") != "reconciled_derived":
        raise MetricInputError("metric input must be reconciled_derived")
    if fact.get("eligible_for_metrics") is not True:
        raise MetricInputError("metric input must be eligible_for_metrics")
    return integer


def _lineage(
    metric_result_id: str,
    role: str,
    fact: dict[str, Any],
) -> MetricLineage:
    return MetricLineage(
        metric_result_id=metric_result_id,
        input_fact_id=str(fact["fact_id"]),
        input_role=role,
        input_fact_version=int(fact["fact_version"]),
        input_restatement_version=str(fact["restatement_version"]),
        input_available_at=str(fact["available_at"]),
    )


class MetricEngine:
    """Compute one deterministic metric result from role-bound facts."""

    @staticmethod
    def compute(
        definition: MetricDefinition,
        *,
        symbol: str,
        fiscal_year: int,
        primary_fact: dict[str, Any] | None,
        secondary_fact: dict[str, Any] | None,
        missing_prior_is_history: bool = False,
        result_version: int = 1,
        supersedes_metric_result_id: str = "",
        revision_review_status: str,
        as_of_date: str,
        created_at: str | None = None,
    ) -> tuple[MetricResult, list[MetricLineage]]:
        facts = [
            fact for fact in (primary_fact, secondary_fact) if fact is not None
        ]
        for fact in facts:
            _fact_integer(fact)
        input_fact_ids = tuple(str(fact["fact_id"]) for fact in facts)
        available_at = (
            max(str(fact["available_at"]) for fact in facts)
            if facts else as_of_date
        )
        period_end = (
            str(primary_fact["period_end"])
            if primary_fact is not None
            else f"{fiscal_year}-12-31"
        )
        status = MetricStatus.computed
        value: Decimal | None = None
        missing = ""

        if primary_fact is None:
            status = MetricStatus.missing_input
            missing = (
                f"role={definition.input_roles[0]};"
                f"concept_id={definition.input_concept_ids[0]};"
                f"fiscal_year={fiscal_year}"
            )
        elif secondary_fact is None:
            status = (
                MetricStatus.insufficient_history
                if missing_prior_is_history
                else MetricStatus.missing_input
            )
            missing = (
                f"role={definition.input_roles[1]};"
                f"concept_id={definition.input_concept_ids[1]};"
                f"fiscal_year={fiscal_year - 1}"
            )
        else:
            primary = Decimal(_fact_integer(primary_fact))
            secondary = Decimal(_fact_integer(secondary_fact))
            with localcontext(
                Context(prec=DECIMAL_PRECISION, rounding=ROUND_HALF_EVEN)
            ):
                if definition.formula == "(current / prior) - 1":
                    if secondary == 0:
                        status = MetricStatus.undefined_zero_denominator
                    elif secondary < 0:
                        status = MetricStatus.not_comparable_negative_prior
                    else:
                        value = (primary / secondary - Decimal(1)).quantize(
                            CANONICAL_QUANTUM,
                            rounding=ROUND_HALF_EVEN,
                        )
                elif definition.formula == "numerator / denominator":
                    if secondary <= 0:
                        status = (
                            MetricStatus.not_comparable_non_positive_profit
                        )
                    else:
                        value = (primary / secondary).quantize(
                            CANONICAL_QUANTUM,
                            rounding=ROUND_HALF_EVEN,
                        )
                else:
                    raise ValueError(
                        f"unsupported metric formula: {definition.formula}"
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
        result = replace(
            result,
            metric_result_id=build_metric_result_id(result),
        )
        lineage = [
            _lineage(result.metric_result_id, role, fact)
            for role, fact in zip(
                definition.input_roles, facts, strict=False,
            )
        ]
        return result, lineage
