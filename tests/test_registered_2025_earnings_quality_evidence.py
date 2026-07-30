"""Registered evidence contract for 2025 earnings-quality facts."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from ashare_research.tools.official_earnings_quality_2025_acceptance import (
    CONCEPTS,
    CONTRACT,
    DEFAULT_EVIDENCE,
    preflight_evidence,
)

ROOT = Path(__file__).resolve().parents[1]
BASE = (
    ROOT
    / "acceptance"
    / "fixtures"
    / "official_facts"
    / "601857.SH"
    / "2025_annual.json"
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git_blob(path: Path) -> str:
    content = path.read_bytes()
    return hashlib.sha1(  # noqa: S324
        f"blob {len(content)}\0".encode() + content
    ).hexdigest()


def _evidence() -> dict:
    return json.loads(DEFAULT_EVIDENCE.read_text(encoding="utf-8"))


def test_evidence_binds_the_frozen_2025_base_bundle():
    evidence = _evidence()
    assert evidence["contract"] == CONTRACT
    assert evidence["base_bundle_path"] == (
        "acceptance/fixtures/official_facts/601857.SH/2025_annual.json"
    )
    assert evidence["base_bundle_sha256"] == _sha256(BASE)
    assert evidence["base_bundle_git_blob"] == _git_blob(BASE)
    assert evidence["base_bundle_git_blob"] == (
        "0ababb5262e6cbf1646e165ccfb3e7bfe2769670"
    )


def test_two_formal_sources_each_register_exactly_three_facts():
    evidence = _evidence()
    bundle = json.loads(BASE.read_text(encoding="utf-8"))
    assert set(evidence["sources"]) == {"company", "exchange"}
    for source in ("company", "exchange"):
        assert bundle["documents"][source]["source_tier"] == (
            f"{source}_official"
        )
        facts = evidence["sources"][source]["facts"]
        assert len(facts) == 3
        assert {item["concept_id"] for item in facts} == CONCEPTS


def test_fact_evidence_types_labels_units_and_manual_review():
    evidence = _evidence()
    for source in ("company", "exchange"):
        by_concept = {
            item["concept_id"]: item
            for item in evidence["sources"][source]["facts"]
        }
        assert by_concept["operating_cost"]["evidence_type"] == (
            "audited_consolidated_income_statement"
        )
        assert by_concept["operating_cost"]["source_label"] == "减：营业成本"
        assert by_concept["operating_cost"]["sign_convention"] == (
            "expense_magnitude_positive"
        )
        assert by_concept["operating_profit"]["evidence_type"] == (
            "audited_consolidated_income_statement"
        )
        assert by_concept["operating_profit"]["source_label"] == "营业利润"
        adjusted = by_concept["net_profit_excluding_non_recurring"]
        assert adjusted["evidence_type"] == "annual_report_direct_disclosure"
        assert adjusted["source_label"] == (
            "归属于母公司股东的扣除非经常性损益的净利润"
        )
        for item in by_concept.values():
            assert item["raw_unit"] == "人民币百万元"
            assert item["manual_review_status"] == "visually_verified_twice"
            assert int(item["raw_value"]) * 100 == (
                item["expected_normalized_value"]
            )


def test_company_and_exchange_values_are_exactly_equal():
    evidence = _evidence()
    values = {}
    for source in ("company", "exchange"):
        values[source] = {
            item["concept_id"]: item["expected_normalized_value"]
            for item in evidence["sources"][source]["facts"]
        }
    assert values["company"] == values["exchange"]


def test_non_recurring_bridge_is_complete_and_exact():
    bridge = _evidence()["non_recurring_bridge"]
    required = {
        "net_profit_attributable_to_parent",
        "net_profit_excluding_non_recurring",
        "attributable_difference",
        "items",
        "item_subtotal",
        "income_tax_effect",
        "minority_interest_effect",
        "reported_final_net_effect",
        "computed_final_net_effect",
        "sign_convention",
        "exact_tie_out",
        "bridge_status",
        "evidence_pages",
        "fact_creation",
    }
    assert required <= bridge.keys()
    item_total = sum(item["amount"] for item in bridge["items"])
    final = (
        item_total
        + bridge["income_tax_effect"]
        + bridge["minority_interest_effect"]
    )
    assert item_total == bridge["item_subtotal"]
    assert final == bridge["reported_final_net_effect"]
    assert final == (
        bridge["net_profit_attributable_to_parent"]
        - bridge["net_profit_excluding_non_recurring"]
    )
    assert bridge["exact_tie_out"] is True
    assert bridge["bridge_status"] == "reconciled"
    assert bridge["fact_creation"] == "not_a_financial_facts_input"


def test_preflight_builds_canonical_matched_pairs():
    result = preflight_evidence(created_at="evidence-test")
    assert len(result["preflight_results"]) == 3
    assert {
        item.output_fact["concept_id"]
        for item in result["preflight_results"]
        if item.output_fact is not None
    } == CONCEPTS
    assert {item.status.value for item in result["preflight_results"]} == {
        "matched"
    }


def test_evidence_has_no_local_paths_or_embedded_artifacts():
    evidence = _evidence()
    serialized = json.dumps(evidence, ensure_ascii=False)
    assert "D:\\" not in serialized
    assert "C:\\" not in serialized
    assert ".png" not in serialized.lower()
    assert "data:image" not in serialized.lower()
    assert not any(
        key in evidence for key in ("local_pdf", "screenshot", "pdf_bytes")
    )
