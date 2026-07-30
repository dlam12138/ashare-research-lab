from copy import deepcopy
from decimal import Decimal

import pytest

from ashare_research.metrics.definitions import MetricDefinitionRegistry
from ashare_research.metrics.engine import MetricEngine, MetricInputError
from ashare_research.metrics.identity import build_metric_result_id
from ashare_research.metrics.models import MetricStatus


def _fact(concept: str, value: int, year: int = 2022) -> dict:
    return {
        "fact_id": f"{concept}-{year}-{value}",
        "concept_id": concept,
        "value": value,
        "unit": "万元",
        "source_tier": "reconciled_derived",
        "eligible_for_metrics": True,
        "fact_version": 1,
        "restatement_version": "original",
        "available_at": f"{year + 1}-03-30",
        "period_end": f"{year}-12-31",
    }


def _compute(metric_id: str, first: dict | None, second: dict | None, **kwargs):
    return MetricEngine.compute(
        MetricDefinitionRegistry.get(metric_id),
        symbol="601857.SH",
        fiscal_year=2022,
        primary_fact=first,
        secondary_fact=second,
        revision_review_status="reviewed_unchanged",
        as_of_date="2023-03-30",
        **kwargs,
    )


def test_decimal_yoy_is_quantized_without_float_division():
    result, lineage = _compute(
        "revenue_yoy",
        _fact("revenue", 3),
        _fact("revenue", 2, 2021),
    )
    assert result.value == Decimal("0.500000000000")
    assert result.status == MetricStatus.computed
    assert [item.input_role for item in lineage] == ["current", "prior"]


def test_ratio_uses_decimal_and_role_order():
    result, lineage = _compute(
        "operating_cash_flow_to_attributable_net_profit",
        _fact("operating_cash_flow", 10),
        _fact("net_profit_attributable_to_parent", 4),
    )
    assert result.value == Decimal("2.500000000000")
    assert [item.input_role for item in lineage] == ["numerator", "denominator"]


@pytest.mark.parametrize(
    ("prior", "status"),
    [
        (0, MetricStatus.undefined_zero_denominator),
        (-1, MetricStatus.not_comparable_negative_prior),
    ],
)
def test_yoy_non_comparable_prior(prior: int, status: MetricStatus):
    result, _ = _compute(
        "revenue_yoy",
        _fact("revenue", 10),
        _fact("revenue", prior, 2021),
    )
    assert result.status == status
    assert result.value is None


def test_ratio_non_positive_profit():
    result, _ = _compute(
        "operating_cash_flow_to_attributable_net_profit",
        _fact("operating_cash_flow", 10),
        _fact("net_profit_attributable_to_parent", 0),
    )
    assert result.status == MetricStatus.not_comparable_non_positive_profit
    assert result.value is None


def test_insufficient_history_is_not_zero_and_records_current_only():
    result, lineage = _compute(
        "revenue_yoy",
        _fact("revenue", 10),
        None,
        missing_prior_is_history=True,
    )
    assert result.status == MetricStatus.insufficient_history
    assert result.value is None
    assert "fiscal_year=2021" in result.missing_input_description
    assert len(lineage) == 1
    assert lineage[0].input_role == "current"


def test_missing_current_input_is_not_zero():
    result, lineage = _compute("revenue_yoy", None, None)
    assert result.status == MetricStatus.missing_input
    assert result.value is None
    assert lineage == []


def test_metric_inputs_reject_raw_ineligible_or_unsafe_values():
    fact = _fact("revenue", 10)
    for field, value in (
        ("source_tier", "company_official"),
        ("eligible_for_metrics", False),
        ("unit", "元"),
        ("value", float("inf")),
        ("value", 2**53),
    ):
        invalid = {**fact, field: value}
        with pytest.raises(MetricInputError):
            _compute("revenue_yoy", invalid, _fact("revenue", 9, 2021))


def test_identity_ignores_created_at_but_changes_with_inputs():
    result, _ = _compute(
        "revenue_yoy",
        _fact("revenue", 10),
        _fact("revenue", 9, 2021),
    )
    changed_time = deepcopy(result)
    changed_time.created_at = "2099-01-01"
    assert build_metric_result_id(changed_time) == result.metric_result_id
    changed_input = deepcopy(result)
    changed_input.input_fact_ids = ("different", *result.input_fact_ids[1:])
    assert build_metric_result_id(changed_input) != result.metric_result_id
