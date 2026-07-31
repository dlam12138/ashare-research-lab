"""Registered evidence contract for 2020-2023 ROE/ROA denominator facts.

Covers the four Stage 2D-B evidence files (the 2020 opening-baseline taken
from the 2021 annual report's comparison column, plus the 2021/2022/2023
instant denominator evidence binding each base bundle, Rule 004, and the
company/exchange balance-sheet values) and the three restatement evidence
files (2021<-2022 R = 0, 2022<-2023 R = 2, 2023<-2024 R = 2).  This test
validates the evidence in isolation -- it does not run the foundation runner.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from ashare_research.facts.contexts import build_context_id

ROOT = Path(__file__).resolve().parents[1]
BUNDLE_DIR = ROOT / "acceptance/fixtures/official_facts/601857.SH"
SUPP = BUNDLE_DIR / "supplemental"
REVIEWS = ROOT / "acceptance/fixtures/restatements/601857.SH"

CONTRACT = "roe_roa_denominator_official_facts_v1"
REVIEW_CONTRACT = "roe_roa_denominator_restatement_evidence_v1"
CONCEPTS = {"total_assets", "equity_attributable_to_parent"}
RULE_ID = "RECON_OFFICIAL_NUMERIC_004"
RULE_VERSION = "1"
SYMBOL = "601857.SH"

EVIDENCE_FILES = {
    2020: SUPP / "2020_opening_roe_roa_denominators_from_2021.json",
    2021: SUPP / "2021_roe_roa_denominators.json",
    2022: SUPP / "2022_roe_roa_denominators.json",
    2023: SUPP / "2023_roe_roa_denominators.json",
}
# 2020/2021 base bundle is the 2021 annual report (it hosts the 2020
# comparison column); 2022/2023 use their own annual bundle.
BASE_BUNDLE = {
    2020: BUNDLE_DIR / "2021_annual.json",
    2021: BUNDLE_DIR / "2021_annual.json",
    2022: BUNDLE_DIR / "2022_annual.json",
    2023: BUNDLE_DIR / "2023_annual.json",
}

# Accounting-identity breakdown per year (RMB million), verified against the
# audited consolidated balance sheet current/comparison columns.
IDENTITY = {
    2020: {"cur": 486767, "non": 2001633, "ta": 2488400, "eq": 1215421,
           "min": 151464, "te": 1366885, "liab": 1121515},
    2021: {"cur": 480838, "non": 2021695, "ta": 2502533, "eq": 1263815,
           "min": 145309, "te": 1409124, "liab": 1093409},
    2022: {"cur": 613867, "non": 2059884, "ta": 2673751, "eq": 1369576,
           "min": 168527, "te": 1538103, "liab": 1135648},
    2023: {"cur": 658520, "non": 2094190, "ta": 2752710, "eq": 1446410,
           "min": 184211, "te": 1630621, "liab": 1122089},
}


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
    for year, evidence_path in EVIDENCE_FILES.items():
        bundle_path = BASE_BUNDLE[year]
        evidence = _load(evidence_path)
        assert evidence["contract"] == CONTRACT
        assert evidence["symbol"] == SYMBOL
        assert evidence["fiscal_year"] == year
        assert evidence["base_bundle_path"] == (
            str(bundle_path.relative_to(ROOT)).replace("\\", "/")
        )
        assert evidence["base_bundle_sha256"] == _sha256(bundle_path)
        assert evidence["base_bundle_git_blob"] == _git_blob(bundle_path)
        assert evidence["accounting_standard"] == "CAS"
        assert evidence["consolidation_scope"] == "consolidated"


def test_evidence_binds_rule_004_and_instant_period():
    for year, evidence_path in EVIDENCE_FILES.items():
        evidence = _load(evidence_path)
        assert evidence["reconciliation_rule_id"] == RULE_ID
        assert evidence["reconciliation_rule_version"] == RULE_VERSION
        assert evidence["period_type"] == "instant"
        assert evidence["period_end"] == f"{year}-12-31"


def test_two_formal_sources_each_register_exactly_two_facts():
    for evidence_path in EVIDENCE_FILES.values():
        evidence = _load(evidence_path)
        assert set(evidence["sources"]) == {"company", "exchange"}
        for source in ("company", "exchange"):
            facts = evidence["sources"][source]["facts"]
            assert len(facts) == 2
            assert {item["concept_id"] for item in facts} == CONCEPTS


def test_2020_and_2021_company_source_uses_text_layer_results_announcement():
    """The 2021 annual bundle's company audited statements (badab8f2) is a
    scanned image PDF with no text layer; the evidence overrides the company
    source with the registered 2021 results announcement 555a24ed, which
    shares the company_ir source_id with badab8f2 (version-chain stable)."""
    for year in (2020, 2021):
        evidence = _load(EVIDENCE_FILES[year])
        override = evidence["documents"]
        assert set(override) == {"company", "exchange"}
        company = override["company"]
        assert company["sha256"].startswith("555a24ed")
        assert company["source_id"] == "company_ir:601857.SH:2021:annual:zh-cn"
        assert company["source_tier"] == "company_official"
        # The exchange source stays the registered 2021 SSE filing.
        assert override["exchange"]["sha256"].startswith("939de04e")
        assert override["exchange"]["source_id"] == (
            "sse:601857.SH:2021:annual:zh-cn"
        )


def test_2022_and_2023_have_no_document_override():
    for year in (2022, 2023):
        evidence = _load(EVIDENCE_FILES[year])
        assert "documents" not in evidence


def test_fact_evidence_labels_units_and_manual_review():
    for evidence_path in EVIDENCE_FILES.values():
        evidence = _load(evidence_path)
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
                assert abs(item["expected_normalized_value"]) <= 2**53 - 1


def test_company_and_exchange_values_are_exactly_equal():
    for evidence_path in EVIDENCE_FILES.values():
        evidence = _load(evidence_path)
        values = {}
        for source in ("company", "exchange"):
            values[source] = {
                item["concept_id"]: item["expected_normalized_value"]
                for item in evidence["sources"][source]["facts"]
            }
        assert values["company"] == values["exchange"]


def test_accounting_identity_check_ties_exactly():
    for year, evidence_path in EVIDENCE_FILES.items():
        check = _load(evidence_path)["accounting_identity_check"]
        ident = IDENTITY[year]
        assert check["exact_tie_out"] is True
        assert check["scope"] == "consolidated_only"
        # Identity 1: current + non-current = total assets.
        assert ident["cur"] + ident["non"] == ident["ta"]
        assert check["computed_total_assets"] == ident["ta"]
        assert check["reported_total_assets"] == ident["ta"]
        # Identity 2: parent equity + minority = total equity.
        assert ident["eq"] + ident["min"] == ident["te"]
        assert check["computed_total_equity"] == ident["te"]
        assert check["reported_total_equity"] == ident["te"]
        # Identity 3: liabilities + equity = total assets.
        assert ident["liab"] + ident["te"] == ident["ta"]
        assert check["computed_liabilities_plus_equity"] == ident["ta"]
        assert check["reported_liabilities_plus_equity"] == ident["ta"]


def test_revision_review_status_per_year():
    assert (
        _load(EVIDENCE_FILES[2020])["revision_review_status"]
        == "comparison_only_opening_baseline"
    )
    assert (
        _load(EVIDENCE_FILES[2021])["revision_review_status"]
        == "reviewed_unchanged"
    )
    for year in (2022, 2023):
        assert (
            _load(EVIDENCE_FILES[year])["revision_review_status"]
            == "reviewed_changed"
        )


def test_2020_opening_baseline_uses_2021_report_comparison_column():
    evidence = _load(EVIDENCE_FILES[2020])
    assert evidence["limitations"]
    serialized = json.dumps(evidence, ensure_ascii=False)
    assert "comparison_only_opening_baseline" in serialized
    for source in ("company", "exchange"):
        for item in evidence["sources"][source]["facts"]:
            # source_table carries the REPORT year (2021); column_label the
            # DATA year (2020 comparison column).
            assert "2021" in item["source_table"]
            assert "2020" in item["column_label"]


def test_2020_opening_baseline_available_at_is_later_2021_announcement_date():
    documents = _load(EVIDENCE_FILES[2020])["documents"]
    company = documents["company"]
    exchange = documents["exchange"]
    # The 2021 results announcement (company) filed 2022-03-31; the 2021 SSE
    # annual report (exchange) announced 2022-04-01.  available_at is the later
    # of the two, so the 2020 opening baseline is only available from 2022-04-01.
    assert company["announcement_date"] == "2022-03-31"
    assert exchange["announcement_date"] == "2022-04-01"
    assert max(company["announcement_date"], exchange["announcement_date"]) == (
        "2022-04-01"
    )


def test_2021_reviewed_by_2022_is_unchanged_r_equals_zero():
    review = _load(REVIEWS / "roe_roa_denominators_2021_reviewed_by_2022.json")
    assert review["contract"] == REVIEW_CONTRACT
    assert review["target_fiscal_year"] == 2021
    assert review["evidence_fiscal_year"] == 2022
    assert review["evidence_bundle_path"] == (
        "acceptance/fixtures/official_facts/601857.SH/2022_annual.json"
    )
    assert {item["concept_id"] for item in review["concepts"]} == CONCEPTS
    for item in review["concepts"]:
        computed = item["original_raw_value"] != item["later_comparative_raw_value"]
        assert item["changed"] is computed is False
        assert item["review_status"] == "reviewed_unchanged"
        assert item["disclosed_change_reason"] == "not_applicable_no_change"


def test_2022_reviewed_by_2023_changed_r_equals_two():
    review = _load(REVIEWS / "roe_roa_denominators_2022_reviewed_by_2023.json")
    assert review["contract"] == REVIEW_CONTRACT
    assert review["target_fiscal_year"] == 2022
    assert review["evidence_fiscal_year"] == 2023
    assert review["evidence_bundle_path"] == (
        "acceptance/fixtures/official_facts/601857.SH/2023_annual.json"
    )
    for item in review["concepts"]:
        assert item["changed"] is True
        assert item["review_status"] == "reviewed_changed"
        assert item["disclosed_change_reason"] == (
            "Interpretation 16 / IAS 12 revisions"
        )


def test_2023_reviewed_by_2024_changed_r_equals_two():
    review = _load(REVIEWS / "roe_roa_denominators_2023_reviewed_by_2024.json")
    assert review["contract"] == REVIEW_CONTRACT
    assert review["target_fiscal_year"] == 2023
    assert review["evidence_fiscal_year"] == 2024
    assert review["evidence_bundle_path"] == (
        "acceptance/fixtures/official_facts/601857.SH/2024_annual.json"
    )
    for item in review["concepts"]:
        assert item["changed"] is True
        assert item["review_status"] == "reviewed_changed"
        assert item["disclosed_change_reason"].startswith(
            "Common-control business combination"
        )
        assert "2024-10-29" in item["disclosed_change_reason"]


def test_restatements_register_two_concepts_with_manual_review():
    for year in (2021, 2022, 2023):
        review = _load(
            REVIEWS / f"roe_roa_denominators_{year}_reviewed_by_{year + 1}.json"
        )
        assert {item["concept_id"] for item in review["concepts"]} == CONCEPTS
        for item in review["concepts"]:
            for source in ("company", "exchange"):
                assert item[source]["manual_review_status"] == (
                    "visually_verified_twice"
                )


def test_evidence_has_no_local_paths_or_embedded_artifacts():
    paths = list(EVIDENCE_FILES.values()) + [
        REVIEWS / "roe_roa_denominators_2021_reviewed_by_2022.json",
        REVIEWS / "roe_roa_denominators_2022_reviewed_by_2023.json",
        REVIEWS / "roe_roa_denominators_2023_reviewed_by_2024.json",
    ]
    for path in paths:
        serialized = path.read_text(encoding="utf-8")
        assert "D:\\" not in serialized
        assert "C:\\" not in serialized
        assert ".png" not in serialized.lower()
        assert "data:image" not in serialized.lower()


def test_instant_contexts_are_distinct_from_duration():
    """Stage 2D-B registers four instant contexts (2020-2023) that must not
    collide with the existing annual duration contexts."""
    for year in (2020, 2021, 2022, 2023):
        instant = build_context_id(SYMBOL, year, "instant", "consolidated")
        annual = build_context_id(SYMBOL, year, "annual", "consolidated")
        assert instant == f"{SYMBOL}|{year}|instant|consolidated"
        assert instant != annual
