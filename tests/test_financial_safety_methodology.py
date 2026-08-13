"""Contract tests for the post-capital-return financial-safety methodology."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "config/value_evaluation_methodology_financial_safety_v1.json"


def _contract() -> dict:
    return json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))


def _methods() -> dict[str, dict]:
    return {item["metric_id"]: item for item in _contract()["methods"]}


def test_contract_has_frozen_scope_and_no_decision_fields():
    contract = _contract()
    assert contract["methodology_id"] == "financial_safety_v1"
    assert contract["version"] == "1"
    assert contract["status"] == "frozen_methodology_contract"
    assert contract["entity_scope"] == "consolidated"
    assert contract["accounting_standard"] == "CAS"
    assert contract["canonical_unit"] == "万元"
    assert all(item["score_eligible"] is False for item in contract["methods"])

    forbidden_keys = {
        "score",
        "weight",
        "weights",
        "threshold",
        "grade",
        "target_price",
        "buy",
        "sell",
    }

    def walk(value):
        if isinstance(value, dict):
            for key, nested in value.items():
                assert key not in forbidden_keys
                yield from walk(nested)
        elif isinstance(value, list):
            for nested in value:
                yield from walk(nested)

    list(walk(contract))


def test_asset_liability_ratio_contract_and_boundaries():
    method = _methods()["asset_liability_ratio"]
    assert method["formula"] == "total_liabilities / total_assets"
    assert method["input_concept_ids"] == ["total_liabilities", "total_assets"]
    assert method["input_roles"] == ["numerator", "denominator"]
    assert method["input_type"] == "instant"
    assert method["period_end_rule"] == "same 12-31"
    assert method["scope"] == "CAS consolidated"
    assert method["unit"] == "ratio"
    assert method["status_rules"] == {
        "missing": "missing_input",
        "denominator_zero": "undefined_zero_denominator",
        "denominator_negative": "not_comparable_negative_denominator",
    }
    assert method["available_at_rule"].startswith("max(")


def test_gross_debt_requires_direct_mutually_exclusive_components():
    method = _methods()["gross_interest_bearing_debt"]
    assert method["input_concept_ids"] == [
        "short_term_borrowings",
        "current_portion_of_interest_bearing_non_current_liabilities",
        "long_term_borrowings",
        "bonds_payable",
        "lease_liabilities",
    ]
    assert len(set(method["input_concept_ids"])) == 5
    assert "total_liabilities" in method["component_policy"]["forbidden_substitution"]
    assert "interest_bearing_debt" in method["component_policy"]["forbidden_substitution"]
    assert "current and long-term portions" in method["component_policy"]["duplicate_policy"]
    assert method["component_policy"]["unavailable_split"] == (
        "blocked; do not infer from total_liabilities"
    )


def test_cash_and_net_debt_keep_canonical_cash_and_negative_net_debt():
    cash = _methods()["cash_coverage_of_interest_bearing_debt"]
    assert cash["formula"] == "cash_and_cash_equivalents / gross_interest_bearing_debt"
    assert cash["status_rules"]["debt_zero"] == "undefined_no_debt"
    assert cash["cash_policy"]["canonical"].startswith("period-end cash_and_cash_equivalents")
    assert cash["cash_policy"]["allowed_explicit_proxy"] == (
        "monetary_funds only when the filing explicitly identifies it as the comparable cash proxy"
    )
    assert cash["cash_policy"]["restricted_cash"].startswith("not canonical")
    assert cash["cash_policy"]["missing_cash"] == "missing_input; never zero"

    net = _methods()["net_interest_bearing_debt"]
    assert net["formula"] == "gross_interest_bearing_debt - cash_and_cash_equivalents"
    assert net["status_rules"]["negative_result"].startswith("computed")
    assert "gross debt" in net["display_policy"]


def test_interest_coverage_and_next_stage_are_blocked():
    method = _methods()["interest_coverage"]
    assert method["formula"] is None
    assert method["methodology_status"] == "blocked"
    assert method["computation_status"] == "blocked"
    assert "operating_profit" in method["status_rules"]["forbidden_guess"]
    assert "finance_expense" in method["status_rules"]["forbidden_guess"]
    assert len(method["blockers"]) == 3


def test_contract_references_explicitly_borrow_and_trim_mature_patterns():
    references = _contract()["references"]
    assert {item["reference_id"] for item in references} == {
        "openbb_provider_mapping_standard_model",
        "financetoolkit_reported_to_derived",
        "arelle_xbrl_fact_context_unit",
        "pandera_stable_rule_ids",
        "great_expectations_checkpoint",
        "openlineage_run_input_output",
    }
    for item in references:
        assert item["borrow"]
        assert item["apply_to"]
        assert item["not_copy"]


def test_supporting_review_and_input_contract_exist():
    assert (ROOT / "docs/post_capital_return_north_star_review.md").exists()
    assert (ROOT / "docs/financial_safety_input_contract.md").exists()
    assert (ROOT / "acceptance/m2_stage2ea_financial_safety_methodology_contract.md").exists()
