"""Stage 2E-B financial-safety definitions, boundaries, and offline PIT slice."""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

import pytest

from ashare_research.facts.concepts import ConceptRegistry
from ashare_research.metrics.financial_safety_definitions import (
    FinancialSafetyMetricDefinitionRegistry,
    FinancialSafetyMetricStatus,
)
from ashare_research.metrics.financial_safety_engine import (
    FinancialSafetyMetricEngine,
)
from ashare_research.metrics.identity import validate_canonical_metric_result_id
from ashare_research.metrics.models import MetricStatus
from ashare_research.reconciliation.engine import DEFAULT_NUMERIC_RECONCILIATION_RULE
from ashare_research.reconciliation.financial_safety import (
    FINANCIAL_SAFETY_RECONCILIATION_RULE,
)
from ashare_research.reconciliation.financial_safety_derivation import (
    CURRENT_PORTION_COMPONENT_IDS,
    CURRENT_PORTION_CONCEPT_ID,
    DERIVATION_DEFINITION_ID,
    build_current_portion_fact,
)
from ashare_research.tools.official_financial_safety_vertical_slice import (
    DIRECT_SAFETY_CONCEPTS,
    METRIC_IDS,
    PIT_DATES,
    run_financial_safety_vertical_slice,
)

ROOT = Path(__file__).resolve().parents[1]
SAFETY_CONCEPTS = {
    "total_liabilities",
    "short_term_borrowings",
    "current_portion_of_interest_bearing_non_current_liabilities",
    "long_term_borrowings",
    "bonds_payable",
    "lease_liabilities",
    "cash_and_cash_equivalents",
}


def _fact(value: int, fact_id: str, available_at: str = "2023-03-30") -> dict:
    return {
        "fact_id": fact_id,
        "fact_version": 1,
        "restatement_version": "original",
        "available_at": available_at,
        "period_end": "2022-12-31",
        "value": value,
        "unit": "万元",
        "source_tier": "reconciled_derived",
        "eligible_for_metrics": True,
    }


def _compute(metric_id: str, values: dict[str, int | None]):
    definition = FinancialSafetyMetricDefinitionRegistry.get(metric_id)
    assert definition is not None
    roles = {
        role: _fact(value, f"{role}-id") if value is not None else None
        for role, value in values.items()
    }
    return FinancialSafetyMetricEngine.compute(
        definition,
        symbol="601857.SH",
        fiscal_year=2022,
        role_facts=roles,
        revision_review_status="reviewed_changed",
        as_of_date="2023-03-30",
        created_at="2026-08-01T00:00:00+08:00",
    )


def test_financial_safety_concepts_rule_and_definitions_are_additive():
    assert "current_portion_of_interest_bearing_non_current_liabilities" in ConceptRegistry.CONCEPTS
    assert all(concept in ConceptRegistry.CONCEPTS for concept in CURRENT_PORTION_COMPONENT_IDS)
    assert FINANCIAL_SAFETY_RECONCILIATION_RULE.rule_id == "RECON_OFFICIAL_NUMERIC_006"
    assert FINANCIAL_SAFETY_RECONCILIATION_RULE.version == "1"
    assert FINANCIAL_SAFETY_RECONCILIATION_RULE.supported_concepts == set(DIRECT_SAFETY_CONCEPTS)
    assert DEFAULT_NUMERIC_RECONCILIATION_RULE.supported_concepts == frozenset(
        {"revenue", "net_profit_attributable_to_parent", "operating_cash_flow"}
    )
    assert tuple(FinancialSafetyMetricDefinitionRegistry.DEFINITIONS) == METRIC_IDS
    assert "interest_coverage" not in FinancialSafetyMetricDefinitionRegistry.DEFINITIONS
    for definition in FinancialSafetyMetricDefinitionRegistry.list_all():
        assert definition.version == "1"
        assert definition.score_eligible is False
        assert len(definition.input_roles) == len(definition.input_concept_ids)


def test_metric_engine_financial_safety_boundaries_and_lineage():
    ratio, ratio_lineage = _compute("asset_liability_ratio", {"numerator": 3, "denominator": 2})
    assert ratio.status == MetricStatus.computed
    assert ratio.value == Decimal("1.500000000000")
    assert [row.input_role for row in ratio_lineage] == ["numerator", "denominator"]

    zero, _ = _compute("asset_liability_ratio", {"numerator": 3, "denominator": 0})
    negative, _ = _compute("asset_liability_ratio", {"numerator": 3, "denominator": -2})
    assert zero.status == MetricStatus.undefined_zero_denominator
    assert negative.status == MetricStatus.not_comparable_negative_denominator

    debt_values = {
        "short_term_borrowings": 1,
        "current_portion": 2,
        "long_term_borrowings": 3,
        "bonds_payable": 4,
        "lease_liabilities": 5,
    }
    gross, lineage = _compute("gross_interest_bearing_debt", debt_values)
    assert gross.value == Decimal("15.000000000000")
    assert [row.input_role for row in lineage] == list(debt_values)
    for row in lineage:
        assert row.input_fact_id in gross.input_fact_ids

    missing = dict(debt_values)
    missing["current_portion"] = None
    missing_result, missing_lineage = _compute("gross_interest_bearing_debt", missing)
    assert missing_result.status == MetricStatus.missing_input
    assert missing_result.input_fact_ids == tuple(row.input_fact_id for row in missing_lineage)
    assert all(row.input_role != "current_portion" for row in missing_lineage)

    no_debt, _ = _compute(
        "cash_coverage_of_interest_bearing_debt",
        {"cash": 10, **{role: 0 for role in debt_values}},
    )
    negative_debt, _ = _compute(
        "cash_coverage_of_interest_bearing_debt",
        {"cash": 10, **{**debt_values, "bonds_payable": -1}},
    )
    net_debt, _ = _compute("net_interest_bearing_debt", {**debt_values, "cash": 20})
    assert no_debt.status == FinancialSafetyMetricStatus.undefined_no_debt
    assert (
        negative_debt.status
        == FinancialSafetyMetricStatus.not_comparable_negative_debt_component
    )
    assert net_debt.status == MetricStatus.computed
    assert net_debt.value == Decimal("-5.000000000000")
    validate_canonical_metric_result_id(net_debt)


def test_official_evidence_has_dual_source_and_four_reviewed_changes():
    expected_changes = {
        (2022, "total_liabilities"),
        (2023, "total_liabilities"),
        (2023, "lease_liabilities"),
        (2023, "current_portion_of_lease_liabilities"),
    }
    changed = set()
    for year in range(2021, 2026):
        evidence = json.loads(
            (
                ROOT
                / (
                    "acceptance/fixtures/official_facts/601857.SH/supplemental/"
                    f"{year}_financial_safety.json"
                )
            ).read_text(encoding="utf-8")
        )
        assert set(evidence["sources"]) == {"company", "exchange"}
        company = {row["concept_id"]: row for row in evidence["sources"]["company"]}
        exchange = {row["concept_id"]: row for row in evidence["sources"]["exchange"]}
        assert set(company) == SAFETY_CONCEPTS
        assert {row["expected_normalized_value"] for row in company.values()} == {
            row["expected_normalized_value"] for row in exchange.values()
        }
        composition = evidence["current_portion_composition"]
        assert composition["proof_status"] == "proven"
        for source in ("company", "exchange"):
            note = composition[source]
            assert [row["concept_id"] for row in note["interest_bearing_components"]] == list(
                CURRENT_PORTION_COMPONENT_IDS
            )
            assert note["aggregate_raw_value"] == sum(
                row["raw_value"] for row in note["interest_bearing_components"]
            ) + sum(row["raw_value"] for row in note["excluded_components"])
        if year < 2025:
            review = json.loads(
                (
                    ROOT
                    / (
                        "acceptance/fixtures/restatements/601857.SH/"
                        f"financial_safety_{year}_reviewed_by_{year + 1}.json"
                    )
                ).read_text(encoding="utf-8")
            )
            changed.update((year, concept) for concept in review["canonical_changed_concepts"])
            if review["rejected_aggregate_concepts"]:
                assert "current_portion_of_interest_bearing_non_current_liabilities" in {
                    row["concept_id"] for row in review["concepts"] if row["changed"]
                }
    assert changed == expected_changes


def test_official_runner_counts_pit_values_and_idempotence(tmp_path):
    result = run_financial_safety_vertical_slice(tmp_path, run_id="financial-safety-test")
    assert result["status"] == "passed"
    assert result["fact_counts"] == {
        "contexts": 11,
        "facts": 354,
        "raw": 232,
        "reconciled": 122,
        "fact_links": 58,
        "lineage": 354,
        "audit": 354,
    }
    assert result["financial_safety_counts"] == {
        "definitions": 4,
        "result_versions": 25,
        "computed": 25,
        "insufficient": 0,
        "links": 5,
        "lineage": 116,
        "final_latest": 20,
        "final_computed": 20,
    }
    assert result["combined_counts"] == {
        "definitions": 16,
        "results": 102,
        "computed": 98,
        "insufficient": 4,
        "links": 22,
        "lineage": 280,
        "final_latest": 80,
        "final_computed": 76,
    }
    assert result["metric_pit_counts"] == [0, 16, 32, 48, 64, 80]
    assert result["metric_pit_computed_counts"] == [0, 12, 28, 44, 60, 76]
    assert result["metric_pit_insufficient_counts"] == [0, 4, 4, 4, 4, 4]
    assert result["prior_result_count"] == 77
    assert result["default_db_sha256_before"] == result["default_db_sha256_after"]
    assert result["debt_component_proof_status"] == {
        2021: "proven", 2022: "proven", 2023: "proven", 2024: "proven", 2025: "proven",
    }
    assert result["rejected_statement_aggregate"] == CURRENT_PORTION_CONCEPT_ID

    run_dir = Path(result["run_directory"])
    result_rows = json.loads(
        (run_dir / "financial_safety_metric_results.json").read_text(encoding="utf-8")
    )
    assert {row["metric_id"] for row in result_rows} == set(METRIC_IDS)
    assert all("interest_coverage" not in json.dumps(row) for row in result_rows)
    assert all("return_on_invested_capital" not in json.dumps(row) for row in result_rows)
    assert all(
        row["revision_review_status"] == "not_yet_reviewable"
        for row in result_rows
        if row["fiscal_year"] == 2025
    )
    derivation = json.loads(
        (run_dir / "current_portion_derivation.json").read_text(encoding="utf-8")
    )
    assert derivation["definition_id"] == DERIVATION_DEFINITION_ID
    assert len(derivation["derived_facts"]) == 6
    assert {row["fact_version"] for row in derivation["derived_facts"]} == {1, 2}
    assert all(len(row["input_fact_ids"].split(",")) == 3 for row in derivation["derived_facts"])
    assert all(row["eligible_for_metrics"] for row in derivation["derived_facts"])
    assert PIT_DATES == [
        "2022-03-31",
        "2022-04-01",
        "2023-03-30",
        "2024-03-26",
        "2025-03-31",
        "2026-03-30",
    ]

    rerun = run_financial_safety_vertical_slice(tmp_path, run_id="financial-safety-test")
    assert rerun["status"] == "passed"
    assert rerun["combined_counts"] == result["combined_counts"]


def test_current_portion_derivation_rejects_missing_or_non_reconciled_component():
    base = {
        "symbol": "601857.SH",
        "context_id": "601857.SH|2023|instant|consolidated",
        "period_end": "2023-12-31",
        "period_start": "",
        "unit": "万元",
        "filing_date": "2024-03-26",
        "available_at": "2024-03-26",
        "source_tier": "reconciled_derived",
        "is_derived": True,
        "derivation_definition_id": "official_dual_source_reconciliation",
        "eligible_for_metrics": True,
    }
    facts = {}
    for index, concept in enumerate(CURRENT_PORTION_COMPONENT_IDS):
        fact = dict(base, concept_id=concept, fact_id=f"component-{index}", value=100)
        facts[concept] = fact
    result = build_current_portion_fact(facts, created_at="2026-08-01T00:00:00+08:00")
    assert result["value"] == 300
    assert result["derivation_definition_id"] == DERIVATION_DEFINITION_ID
    missing = dict(facts)
    missing.pop(CURRENT_PORTION_COMPONENT_IDS[-1])
    with pytest.raises(ValueError):
        build_current_portion_fact(missing)
