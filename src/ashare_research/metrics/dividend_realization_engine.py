"""Decimal engine for the additive dividend realization metrics."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime
from decimal import ROUND_HALF_EVEN, Context, Decimal, localcontext
from typing import Any

from ashare_research.metrics.engine import CANONICAL_QUANTUM, MetricInputError
from ashare_research.metrics.identity import build_metric_result_id
from ashare_research.metrics.models import MetricDefinition, MetricLineage, MetricResult

DECIMAL_PRECISION = 28
DIVIDEND_CURRENCY = {"CNY", "CNY_PER_SHARE"}
DIVIDEND_STATUS_UNDEFINED_NO_DIVIDEND = "undefined_no_dividend"


def _items(value: Any) -> list[dict[str, Any]]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _value(fact: dict[str, Any], *, role: str) -> Decimal:
    raw = fact.get("value")
    try:
        value = Decimal(str(raw))
    except Exception as exc:
        raise MetricInputError(f"{role} fact value is not Decimal-parsable") from exc
    if not value.is_finite():
        raise MetricInputError(f"{role} fact value must be finite")
    if fact.get("source_tier") == "reconciled_derived":
        if fact.get("eligible_for_metrics") is not True:
            raise MetricInputError(f"{role} fact must be eligible_for_metrics")
    else:
        raise MetricInputError(f"{role} fact must be reconciled_derived")
    return value


def _lineage(result_id: str, role: str, fact: dict[str, Any]) -> MetricLineage:
    return MetricLineage(
        metric_result_id=result_id,
        input_fact_id=str(fact["fact_id"]),
        input_role=role,
        input_fact_version=int(fact.get("fact_version", 1)),
        input_restatement_version=str(fact.get("restatement_version", "original")),
        input_available_at=str(fact.get("available_at", "")),
    )


class DividendRealizationMetricEngine:
    """Compute four metrics with event-list role bindings."""

    @staticmethod
    def compute(
        definition: MetricDefinition,
        *,
        symbol: str,
        fiscal_year: int,
        role_facts: dict[str, list[dict[str, Any]] | dict[str, Any] | None],
        revision_review_status: str,
        as_of_date: str,
        result_version: int = 1,
        supersedes_metric_result_id: str = "",
        created_at: str | None = None,
        missing_description: str = "",
    ) -> tuple[MetricResult, list[MetricLineage]]:
        if set(role_facts) != set(definition.input_roles):
            raise MetricInputError("role_facts must match dividend definition roles")
        bindings = {role: _items(role_facts.get(role)) for role in definition.input_roles}
        missing_roles = [role for role in definition.input_roles if not bindings[role]]
        present = [(role, fact) for role in definition.input_roles for fact in bindings[role]]
        for role, fact in present:
            _value(fact, role=role)
        input_fact_ids = tuple(str(fact["fact_id"]) for _role, fact in present)
        available_at = max(
            (str(fact.get("available_at", "")) for _role, fact in present),
            default=as_of_date,
        )
        period_end = f"{fiscal_year}-12-31"
        status = "computed"
        value: Decimal | None = None
        missing = missing_description
        if missing_roles and not missing:
            missing = (
                f"missing eligible dividend inputs: {','.join(missing_roles)}; "
                f"fiscal_year={fiscal_year}"
            )
        if missing:
            status = "missing_input"
        else:
            values = {
                role: sum((_value(fact, role=role) for fact in facts), Decimal(0))
                for role, facts in bindings.items()
            }
            with localcontext(Context(prec=DECIMAL_PRECISION, rounding=ROUND_HALF_EVEN)):
                if definition.metric_id == "cash_dividend_payout_ratio":
                    dividend = values["implemented_dividend"]
                    profit = values["net_profit"] * Decimal(10000)
                    if dividend == 0:
                        status = DIVIDEND_STATUS_UNDEFINED_NO_DIVIDEND
                    elif profit == 0:
                        status = "undefined_zero_denominator"
                    else:
                        value = (dividend / profit).quantize(
                            CANONICAL_QUANTUM, rounding=ROUND_HALF_EVEN
                        )
                elif definition.metric_id == "operating_cash_flow_dividend_coverage":
                    dividend = values["implemented_dividend"]
                    if dividend == 0:
                        status = DIVIDEND_STATUS_UNDEFINED_NO_DIVIDEND
                    else:
                        value = (
                            (values["operating_cash_flow"] * Decimal(10000)) / dividend
                        ).quantize(CANONICAL_QUANTUM, rounding=ROUND_HALF_EVEN)
                elif definition.metric_id == "free_cash_flow_proxy_dividend_coverage":
                    dividend = values["implemented_dividend"]
                    if dividend == 0:
                        status = DIVIDEND_STATUS_UNDEFINED_NO_DIVIDEND
                    else:
                        fcf = (
                            values["operating_cash_flow"] - values["cash_paid_for_fixed_assets"]
                        ) * Decimal(10000)
                        value = (fcf / dividend).quantize(
                            CANONICAL_QUANTUM, rounding=ROUND_HALF_EVEN
                        )
                elif definition.metric_id == "implemented_cash_dividend_per_share":
                    value = values["implemented_per_share"].quantize(
                        CANONICAL_QUANTUM, rounding=ROUND_HALF_EVEN
                    )
                else:
                    raise MetricInputError(f"unsupported dividend metric: {definition.metric_id}")
        result = MetricResult(
            metric_id=definition.metric_id,
            metric_definition_version=definition.version,
            symbol=symbol,
            fiscal_year=fiscal_year,
            period_end=period_end,
            result_version=result_version,
            supersedes_metric_result_id=supersedes_metric_result_id,
            status=status,  # additive status strings intentionally do not change Metric Schema
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
        lineage = [_lineage(result.metric_result_id, role, fact) for role, fact in present]
        return result, lineage
