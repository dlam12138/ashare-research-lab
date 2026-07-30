"""Versioned metric definitions, results, and input lineage."""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from enum import StrEnum


class MetricStatus(StrEnum):
    computed = "computed"
    insufficient_history = "insufficient_history"
    missing_input = "missing_input"
    undefined_zero_denominator = "undefined_zero_denominator"
    not_comparable_negative_prior = "not_comparable_negative_prior"
    not_comparable_non_positive_profit = "not_comparable_non_positive_profit"
    not_comparable_negative_revenue = "not_comparable_negative_revenue"


@dataclass(frozen=True)
class MetricDefinition:
    metric_id: str
    version: str
    display_name_zh: str
    formula: str
    input_concept_ids: tuple[str, ...]
    input_roles: tuple[str, ...]
    unit: str = "ratio"


@dataclass
class MetricResult:
    metric_result_id: str = ""
    metric_id: str = ""
    metric_definition_version: str = "1"
    symbol: str = ""
    fiscal_year: int = 0
    period_end: str = ""
    result_version: int = 1
    supersedes_metric_result_id: str = ""
    status: MetricStatus = MetricStatus.missing_input
    value: Decimal | None = None
    unit: str = "ratio"
    formula: str = ""
    available_at: str = ""
    input_fact_ids: tuple[str, ...] = field(default_factory=tuple)
    missing_input_description: str = ""
    revision_review_status: str = ""
    created_at: str = ""


@dataclass(frozen=True)
class MetricLineage:
    metric_result_id: str
    input_fact_id: str
    input_role: str
    input_fact_version: int
    input_restatement_version: str
    input_available_at: str
