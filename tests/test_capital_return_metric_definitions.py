"""Unit tests for the capital-return metric definition and the three-input
ROE engine branch.  Tests compute ROE from facts (no hard-coded production
values) and assert the two-input path is byte-identical in behaviour."""

from __future__ import annotations

from decimal import Decimal

import pytest

from ashare_research.metrics.capital_return_definitions import (
    CapitalReturnMetricDefinitionRegistry,
)
from ashare_research.metrics.definitions import MetricDefinitionRegistry
from ashare_research.metrics.engine import MetricEngine
from ashare_research.metrics.models import MetricStatus

ROE = CapitalReturnMetricDefinitionRegistry.get(
    "return_on_average_equity_attributable_to_parent"
)


def _fact(value, *, fid="f", version=1, at="2022-04-01", pe="2021-12-31"):
    return {
        "fact_id": fid,
        "fact_version": version,
        "restatement_version": "original" if version == 1 else "restated_1",
        "available_at": at,
        "period_end": pe,
        "value": value,
        "unit": "万元",
        "source_tier": "reconciled_derived",
        "eligible_for_metrics": True,
    }


def test_roe_definition_contract():
    assert ROE.metric_id == "return_on_average_equity_attributable_to_parent"
    assert ROE.version == "1"
    assert ROE.unit == "ratio"
    assert ROE.input_roles == ("numerator", "opening", "closing")
    assert ROE.input_concept_ids == (
        "net_profit_attributable_to_parent",
        "equity_attributable_to_parent",
        "equity_attributable_to_parent",
    )
    assert ROE.formula == (
        "net_profit_attributable_to_parent / "
        "((opening_equity_attributable_to_parent + "
        "closing_equity_attributable_to_parent) / 2)"
    )
    assert ROE.score_eligible is False
    # Registry exposes exactly one definition (ROE only, no ROA).
    assert {
        d.metric_id for d in CapitalReturnMetricDefinitionRegistry.list_all()
    } == {"return_on_average_equity_attributable_to_parent"}


def test_roe_three_input_formula_matches_json_contract():
    import json
    from pathlib import Path

    contract = json.loads(
        Path(
            "config/value_evaluation_methodology_capital_return_v1.json"
        ).read_text(encoding="utf-8")
    )
    roe_json = next(
        m for m in contract["metrics"]
        if m["metric_id"] == "return_on_average_equity_attributable_to_parent"
    )
    assert ROE.formula == roe_json["formula"]
    assert tuple(ROE.input_concept_ids) == tuple(roe_json["input_concepts"])
    assert tuple(ROE.input_roles) == tuple(roe_json["input_roles"])


def test_roe_computed_from_facts_three_lineage_roles():
    # 2021 PetroChina: NP=9,216,100 / avg(121,542,100, 126,381,500)=123,961,800.
    result, lineage = MetricEngine.compute(
        ROE, symbol="601857.SH", fiscal_year=2021,
        primary_fact=_fact(9216100, fid="np"),
        secondary_fact=_fact(121542100, fid="op", pe="2020-12-31"),
        tertiary_fact=_fact(126381500, fid="cl"),
        revision_review_status="reviewed_unchanged",
        as_of_date="2022-04-01", created_at="2026-08-01T00:00:00+08:00",
    )
    assert result.status == MetricStatus.computed
    assert result.value == Decimal("0.074346290551")
    assert result.unit == "ratio"
    assert [row.input_role for row in lineage] == [
        "numerator", "opening", "closing"
    ]
    assert {row.input_fact_id for row in lineage} == {"np", "op", "cl"}
    assert result.available_at == "2022-04-01"


def test_roe_zero_average_equity_is_undefined():
    result, _ = MetricEngine.compute(
        ROE, symbol="601857.SH", fiscal_year=2021,
        primary_fact=_fact(9216100, fid="np"),
        secondary_fact=_fact(0, fid="op"), tertiary_fact=_fact(0, fid="cl"),
        revision_review_status="x", as_of_date="2022-04-01",
        created_at="2026-08-01T00:00:00+08:00",
    )
    assert result.status == MetricStatus.undefined_zero_denominator
    assert result.value is None


def test_roe_negative_average_equity_is_not_comparable():
    result, _ = MetricEngine.compute(
        ROE, symbol="601857.SH", fiscal_year=2021,
        primary_fact=_fact(9216100, fid="np"),
        secondary_fact=_fact(-100, fid="op"), tertiary_fact=_fact(-100, fid="cl"),
        revision_review_status="x", as_of_date="2022-04-01",
        created_at="2026-08-01T00:00:00+08:00",
    )
    assert result.status == MetricStatus.not_comparable_negative_denominator
    assert result.value is None


def test_roe_missing_closing_is_missing_input():
    result, _ = MetricEngine.compute(
        ROE, symbol="601857.SH", fiscal_year=2021,
        primary_fact=_fact(9216100, fid="np"),
        secondary_fact=_fact(121542100, fid="op", pe="2020-12-31"),
        tertiary_fact=None,
        revision_review_status="x", as_of_date="2022-04-01",
        created_at="2026-08-01T00:00:00+08:00",
    )
    assert result.status == MetricStatus.missing_input
    assert "closing" in result.missing_input_description


def test_roe_missing_opening_is_missing_input():
    result, _ = MetricEngine.compute(
        ROE, symbol="601857.SH", fiscal_year=2021,
        primary_fact=_fact(9216100, fid="np"),
        secondary_fact=None, tertiary_fact=_fact(126381500, fid="cl"),
        revision_review_status="x", as_of_date="2022-04-01",
        created_at="2026-08-01T00:00:00+08:00",
    )
    assert result.status == MetricStatus.missing_input


def test_roe_result_id_is_canonical():
    from ashare_research.metrics.identity import (
        build_metric_result_id,
    )

    result, _ = MetricEngine.compute(
        ROE, symbol="601857.SH", fiscal_year=2021,
        primary_fact=_fact(9216100, fid="np"),
        secondary_fact=_fact(121542100, fid="op", pe="2020-12-31"),
        tertiary_fact=_fact(126381500, fid="cl"),
        revision_review_status="reviewed_unchanged",
        as_of_date="2022-04-01", created_at="2026-08-01T00:00:00+08:00",
    )
    assert result.metric_result_id == build_metric_result_id(result)


def test_two_input_path_is_byte_identical_to_prior_behavior():
    """A two-input metric computed with the new signature must yield the same
    result id and value as before the tertiary_fact extension."""
    revenue_yoy = MetricDefinitionRegistry.get("revenue_yoy")
    result, lineage = MetricEngine.compute(
        revenue_yoy, symbol="601857.SH", fiscal_year=2022,
        primary_fact=_fact(100, fid="c", pe="2022-12-31"),
        secondary_fact=_fact(80, fid="p", pe="2021-12-31", at="2022-04-01"),
        revision_review_status="reviewed_unchanged",
        as_of_date="2022-04-01", created_at="2026-08-01T00:00:00+08:00",
    )
    # tertiary_fact defaults to None and must not appear in lineage/ids.
    assert result.status == MetricStatus.computed
    assert result.value == Decimal("0.250000000000")
    assert [row.input_role for row in lineage] == ["current", "prior"]
    assert result.input_fact_ids == ("c", "p")
    # Explicit tertiary=None also leaves the two-input result unchanged.
    result2, _ = MetricEngine.compute(
        revenue_yoy, symbol="601857.SH", fiscal_year=2022,
        primary_fact=_fact(100, fid="c", pe="2022-12-31"),
        secondary_fact=_fact(80, fid="p", pe="2021-12-31", at="2022-04-01"),
        tertiary_fact=None,
        revision_review_status="reviewed_unchanged",
        as_of_date="2022-04-01", created_at="2026-08-01T00:00:00+08:00",
    )
    assert result2.metric_result_id == result.metric_result_id


def test_invalid_fact_unit_rejected():
    bad = _fact(9216100, fid="np")
    bad["unit"] = "CNY"
    from ashare_research.metrics.engine import MetricInputError

    with pytest.raises(MetricInputError):
        MetricEngine.compute(
            ROE, symbol="601857.SH", fiscal_year=2021,
            primary_fact=bad,
            secondary_fact=_fact(121542100, fid="op", pe="2020-12-31"),
            tertiary_fact=_fact(126381500, fid="cl"),
            revision_review_status="x", as_of_date="2022-04-01",
            created_at="2026-08-01T00:00:00+08:00",
        )


# --- Stage 2D-D closure: input role-binding contract ---------------------
# Inputs bind by their declared role position.  A missing middle input must
# never let a later input inherit the vacated role, and a present input's
# role must match its slot, not its position among the non-None survivors.


def test_missing_opening_keeps_closing_in_closing_role():
    """opening (secondary) absent, closing (tertiary) present: closing must
    still bind to the 'closing' role, not be shifted into 'opening'."""
    result, lineage = MetricEngine.compute(
        ROE, symbol="601857.SH", fiscal_year=2021,
        primary_fact=_fact(9216100, fid="np"),
        secondary_fact=None, tertiary_fact=_fact(126381500, fid="cl"),
        revision_review_status="x", as_of_date="2022-04-01",
        created_at="2026-08-01T00:00:00+08:00",
    )
    assert result.status == MetricStatus.missing_input
    roles = {row.input_fact_id: row.input_role for row in lineage}
    assert roles == {"np": "numerator", "cl": "closing"}
    # The absent opening's role must not be stolen by the present closing.
    assert "opening" not in roles.values()


def test_missing_numerator_keeps_opening_and_closing_roles():
    """numerator (primary) absent, opening + closing present: neither must
    shift forward into the numerator slot."""
    result, lineage = MetricEngine.compute(
        ROE, symbol="601857.SH", fiscal_year=2021,
        primary_fact=None,
        secondary_fact=_fact(121542100, fid="op", pe="2020-12-31"),
        tertiary_fact=_fact(126381500, fid="cl"),
        revision_review_status="x", as_of_date="2022-04-01",
        created_at="2026-08-01T00:00:00+08:00",
    )
    assert result.status == MetricStatus.missing_input
    roles = {row.input_fact_id: row.input_role for row in lineage}
    assert roles == {"op": "opening", "cl": "closing"}
    assert "numerator" not in roles.values()


def test_missing_closing_keeps_numerator_and_opening_roles():
    """closing (tertiary) absent: the two present inputs retain their
    declared roles and the result is missing_input on 'closing'."""
    result, lineage = MetricEngine.compute(
        ROE, symbol="601857.SH", fiscal_year=2021,
        primary_fact=_fact(9216100, fid="np"),
        secondary_fact=_fact(121542100, fid="op", pe="2020-12-31"),
        tertiary_fact=None,
        revision_review_status="x", as_of_date="2022-04-01",
        created_at="2026-08-01T00:00:00+08:00",
    )
    assert result.status == MetricStatus.missing_input
    assert "closing" in result.missing_input_description
    roles = {row.input_fact_id: row.input_role for row in lineage}
    assert roles == {"np": "numerator", "op": "opening"}


def test_two_role_definition_rejects_non_none_tertiary():
    """A two-role metric given a non-None tertiary_fact must raise instead of
    silently absorbing an untracked input."""
    from ashare_research.metrics.engine import MetricInputError

    revenue_yoy = MetricDefinitionRegistry.get("revenue_yoy")
    with pytest.raises(MetricInputError):
        MetricEngine.compute(
            revenue_yoy, symbol="601857.SH", fiscal_year=2022,
            primary_fact=_fact(100, fid="c", pe="2022-12-31"),
            secondary_fact=_fact(80, fid="p", pe="2021-12-31", at="2022-04-01"),
            tertiary_fact=_fact(999, fid="stray"),
            revision_review_status="reviewed_unchanged",
            as_of_date="2022-04-01", created_at="2026-08-01T00:00:00+08:00",
        )


def test_input_fact_ids_and_lineage_are_one_to_one():
    """Every input_fact_id has exactly one lineage row and vice versa, for a
    fully-computed ROE, a missing-input ROE, and a two-input metric."""
    cases = []

    full, full_lineage = MetricEngine.compute(
        ROE, symbol="601857.SH", fiscal_year=2021,
        primary_fact=_fact(9216100, fid="np"),
        secondary_fact=_fact(121542100, fid="op", pe="2020-12-31"),
        tertiary_fact=_fact(126381500, fid="cl"),
        revision_review_status="reviewed_unchanged",
        as_of_date="2022-04-01", created_at="2026-08-01T00:00:00+08:00",
    )
    cases.append((full, full_lineage))

    partial, partial_lineage = MetricEngine.compute(
        ROE, symbol="601857.SH", fiscal_year=2021,
        primary_fact=_fact(9216100, fid="np"),
        secondary_fact=None, tertiary_fact=_fact(126381500, fid="cl"),
        revision_review_status="x", as_of_date="2022-04-01",
        created_at="2026-08-01T00:00:00+08:00",
    )
    cases.append((partial, partial_lineage))

    revenue_yoy = MetricDefinitionRegistry.get("revenue_yoy")
    two, two_lineage = MetricEngine.compute(
        revenue_yoy, symbol="601857.SH", fiscal_year=2022,
        primary_fact=_fact(100, fid="c", pe="2022-12-31"),
        secondary_fact=_fact(80, fid="p", pe="2021-12-31", at="2022-04-01"),
        revision_review_status="reviewed_unchanged",
        as_of_date="2022-04-01", created_at="2026-08-01T00:00:00+08:00",
    )
    cases.append((two, two_lineage))

    for result, lineage in cases:
        lineage_ids = [row.input_fact_id for row in lineage]
        assert len(lineage_ids) == len(result.input_fact_ids)
        assert set(lineage_ids) == set(result.input_fact_ids)
        # No duplicate fact_id across the lineage (one role per bound input).
        assert len(lineage_ids) == len(set(lineage_ids))
        # Each lineage role is the declared role for that slot.
        assert len({row.input_role for row in lineage}) == len(lineage)
