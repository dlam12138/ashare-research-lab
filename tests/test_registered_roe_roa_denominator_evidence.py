"""Registered evidence contract for 2024/2025 ROE/ROA denominator facts.

Covers the three Stage 2D-A evidence files: the 2024 and 2025 supplemental
denominator evidence (binding each base bundle, Rule 004, and the
company/exchange balance-sheet values) and the 2024-reviewed-by-2025
restatement evidence (R = 0, both unchanged).
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from ashare_research.facts.contexts import (
    build_context_id,
    compute_period_dates,
)
from ashare_research.facts.models import PeriodType

ROOT = Path(__file__).resolve().parents[1]
BUNDLE_DIR = ROOT / "acceptance/fixtures/official_facts/601857.SH"
SUPP = BUNDLE_DIR / "supplemental"
REVIEWS = ROOT / "acceptance/fixtures/restatements/601857.SH"

CONTRACT = "roe_roa_denominator_official_facts_v1"
REVIEW_CONTRACT = "roe_roa_denominator_restatement_evidence_v1"
CONCEPTS = {"total_assets", "equity_attributable_to_parent"}
RULE_ID = "RECON_OFFICIAL_NUMERIC_004"
RULE_VERSION = "1"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git_blob(path: Path) -> str:
    content = path.read_bytes()
    return hashlib.sha1(  # noqa: S324
        f"blob {len(content)}\0".encode() + content
    ).hexdigest()


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_each_denominator_evidence_binds_its_frozen_base_bundle():
    cases = [
        (SUPP / "2024_roe_roa_denominators.json", BUNDLE_DIR / "2024_annual.json"),
        (SUPP / "2025_roe_roa_denominators.json", BUNDLE_DIR / "2025_annual.json"),
    ]
    for evidence_path, bundle_path in cases:
        evidence = _load(evidence_path)
        assert evidence["contract"] == CONTRACT
        assert evidence["symbol"] == "601857.SH"
        assert evidence["base_bundle_path"] == str(bundle_path.relative_to(ROOT)).replace("\\", "/")
        assert evidence["base_bundle_sha256"] == _sha256(bundle_path)
        assert evidence["base_bundle_git_blob"] == _git_blob(bundle_path)
        assert evidence["accounting_standard"] == "CAS"
        assert evidence["consolidation_scope"] == "consolidated"


def test_evidence_binds_rule_004_and_instant_period():
    for name in ("2024_roe_roa_denominators.json", "2025_roe_roa_denominators.json"):
        evidence = _load(SUPP / name)
        assert evidence["reconciliation_rule_id"] == RULE_ID
        assert evidence["reconciliation_rule_version"] == RULE_VERSION
        assert evidence["period_type"] == "instant"
        year = evidence["fiscal_year"]
        assert evidence["period_end"] == f"{year}-12-31"


def test_two_formal_sources_each_register_exactly_two_facts():
    for name in ("2024_roe_roa_denominators.json", "2025_roe_roa_denominators.json"):
        evidence = _load(SUPP / name)
        bundle = _load(
            BUNDLE_DIR / f"{evidence['fiscal_year']}_annual.json"
        )
        assert set(evidence["sources"]) == {"company", "exchange"}
        for source in ("company", "exchange"):
            assert bundle["documents"][source]["source_tier"] == (
                f"{source}_official"
            )
            facts = evidence["sources"][source]["facts"]
            assert len(facts) == 2
            assert {item["concept_id"] for item in facts} == CONCEPTS


def test_fact_evidence_labels_units_and_manual_review():
    for name in ("2024_roe_roa_denominators.json", "2025_roe_roa_denominators.json"):
        evidence = _load(SUPP / name)
        for source in ("company", "exchange"):
            by_concept = {
                item["concept_id"]: item
                for item in evidence["sources"][source]["facts"]
            }
            assert by_concept["total_assets"]["source_label"] == "资产总计"
            assert by_concept["total_assets"]["evidence_type"] == (
                "audited_consolidated_balance_sheet"
            )
            assert by_concept["equity_attributable_to_parent"]["source_label"] == (
                "归属于母公司股东权益合计"
            )
            assert by_concept["equity_attributable_to_parent"]["evidence_type"] == (
                "audited_consolidated_balance_sheet"
            )
            for item in by_concept.values():
                assert item["raw_unit"] == "人民币百万元"
                assert item["manual_review_status"] == "visually_verified_twice"
                assert int(item["raw_value"]) * 100 == (
                    item["expected_normalized_value"]
                )


def test_company_and_exchange_values_are_exactly_equal():
    for name in ("2024_roe_roa_denominators.json", "2025_roe_roa_denominators.json"):
        evidence = _load(SUPP / name)
        values = {}
        for source in ("company", "exchange"):
            values[source] = {
                item["concept_id"]: item["expected_normalized_value"]
                for item in evidence["sources"][source]["facts"]
            }
        assert values["company"] == values["exchange"]


def test_accounting_identity_check_ties_exactly():
    cases = {
        "2024_roe_roa_denominators.json": {
            "total_current_assets": 590844,
            "total_non_current_assets": 2162163,
            "reported_total_assets": 2753007,
            "equity_attributable_to_parent": 1515371,
            "minority_interest": 194492,
            "reported_total_equity": 1709863,
            "total_liabilities": 1043144,
        },
        "2025_roe_roa_denominators.json": {
            "total_current_assets": 595297,
            "total_non_current_assets": 2232720,
            "reported_total_assets": 2828017,
            "equity_attributable_to_parent": 1586061,
            "minority_interest": 213487,
            "reported_total_equity": 1799548,
            "total_liabilities": 1028469,
        },
    }
    for name, expected in cases.items():
        check = _load(SUPP / name)["accounting_identity_check"]
        assert check["exact_tie_out"] is True
        assert check["scope"] == "consolidated_only"
        computed_assets = (
            expected["total_current_assets"]
            + expected["total_non_current_assets"]
        )
        assert computed_assets == expected["reported_total_assets"]
        assert computed_assets == check["computed_total_assets"]
        computed_equity = (
            expected["equity_attributable_to_parent"]
            + expected["minority_interest"]
        )
        assert computed_equity == expected["reported_total_equity"]
        assert computed_equity == check["computed_total_equity"]
        computed_lps = (
            expected["total_liabilities"] + computed_equity
        )
        assert computed_lps == expected["reported_total_assets"]


def test_2025_evidence_is_not_yet_reviewable_2024_is_reviewed_unchanged():
    e2024 = _load(SUPP / "2024_roe_roa_denominators.json")
    e2025 = _load(SUPP / "2025_roe_roa_denominators.json")
    assert e2024["revision_review_status"] == "reviewed_unchanged"
    assert e2025["revision_review_status"] == "not_yet_reviewable"


def test_2024_reviewed_by_2025_is_unchanged_r_equals_zero():
    path = REVIEWS / "roe_roa_denominators_2024_reviewed_by_2025.json"
    review = _load(path)
    assert review["contract"] == REVIEW_CONTRACT
    assert review["target_fiscal_year"] == 2024
    assert review["evidence_fiscal_year"] == 2025
    assert review["evidence_bundle_path"] == (
        "acceptance/fixtures/official_facts/601857.SH/2025_annual.json"
    )
    assert {item["concept_id"] for item in review["concepts"]} == CONCEPTS
    for item in review["concepts"]:
        computed = item["original_raw_value"] != item["later_comparative_raw_value"]
        assert item["changed"] is computed is False
        assert item["review_status"] == "reviewed_unchanged"
        assert item["disclosed_change_reason"] == "not_applicable_no_change"
        for source in ("company", "exchange"):
            assert item[source]["manual_review_status"] == "visually_verified_twice"


def test_evidence_has_no_local_paths_or_embedded_artifacts():
    for path in [
        SUPP / "2024_roe_roa_denominators.json",
        SUPP / "2025_roe_roa_denominators.json",
        REVIEWS / "roe_roa_denominators_2024_reviewed_by_2025.json",
    ]:
        serialized = path.read_text(encoding="utf-8")
        assert "D:\\" not in serialized
        assert "C:\\" not in serialized
        assert ".png" not in serialized.lower()
        assert "data:image" not in serialized.lower()


def test_two_instant_contexts_are_distinct_from_annual_duration_context():
    """Stage 2D-A registers two instant contexts (2024 / 2025) that must not
    collide with the existing annual duration contexts."""
    annual_2024 = build_context_id("601857.SH", 2024, "annual", "consolidated")
    annual_2025 = build_context_id("601857.SH", 2025, "annual", "consolidated")
    instant_2024 = build_context_id("601857.SH", 2024, "instant", "consolidated")
    instant_2025 = build_context_id("601857.SH", 2025, "instant", "consolidated")
    assert instant_2024 == "601857.SH|2024|instant|consolidated"
    assert instant_2025 == "601857.SH|2025|instant|consolidated"
    assert {instant_2024, instant_2025}.isdisjoint(
        {annual_2024, annual_2025}
    )
    for year in (2024, 2025):
        start, end = compute_period_dates(year, PeriodType.instant)
        assert start == end == f"{year}-12-31"

