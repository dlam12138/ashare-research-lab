"""Registered Stage 2D-E consolidated net_profit evidence contract tests.

Validates the nine committed evidence files (five supplemental annual
net_profit evidences + four comparison-column restatement reviews)
against the frozen annual bundles, without opening any PDF, touching the
cache or network, or creating any Fact.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
BUNDLE_DIR = ROOT / "acceptance/fixtures/official_facts/601857.SH"
SUPP_DIR = BUNDLE_DIR / "supplemental"
REVIEW_DIR = ROOT / "acceptance/fixtures/restatements/601857.SH"

YEARS = (2021, 2022, 2023, 2024, 2025)
CONTRACT = "net_profit_official_facts_v1"
REVIEW_CONTRACT = "net_profit_restatement_evidence_v1"
RULE_ID = "RECON_OFFICIAL_NUMERIC_005"
RULE_VERSION = "1"
SYMBOL = "601857.SH"

# Official audited consolidated "净利润" line, RMB millions (current column
# of each year's own annual report).
EXPECTED_RAW = {
    2021: 114687,
    2022: 163977,
    2023: 180291,
    2024: 183747,
    2025: 172005,
}
# Later-year comparative-column values (restatement reviews).
EXPECTED_LATER = {2021: 114687, 2022: 163343, 2023: 180561, 2024: 183747}
EXPECTED_CHANGED = {2021: False, 2022: True, 2023: True, 2024: False}
EXPECTED_REVIEW_STATUS = {
    2021: "reviewed_unchanged",
    2022: "reviewed_changed",
    2023: "reviewed_changed",
    2024: "reviewed_unchanged",
    2025: "not_yet_reviewable",
}
EXPECTED_PAGES = {
    # (company_pdf, company_printed, exchange_pdf, exchange_printed)
    2021: (42, 42, 114, 112),
    2022: (113, 111, 113, 111),
    2023: (114, 112, 114, 112),
    2024: (115, 113, 115, 113),
    2025: (109, 107, 109, 107),
}
# 2021 company text-layer source (scanned audited statements badab8f2
# replaced by the registered results announcement; same source_id).
RESULTS_ANNOUNCEMENT_2021_SHA = (
    "555a24ed0ace306ebb249faefd2d131e960cd008ad22df8929993c40183e4786"
)
COMPANY_SOURCE_ID_2021 = "company_ir:601857.SH:2021:annual:zh-cn"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git_blob(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b"blob %d\x00" % len(data) + data).hexdigest()  # noqa: S324


def _load(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def _evidence(year: int) -> dict:
    return _load(SUPP_DIR / f"{year}_net_profit.json")


def _review(target: int) -> dict:
    return _load(REVIEW_DIR / f"net_profit_{target}_reviewed_by_{target + 1}.json")


@pytest.mark.parametrize("year", YEARS)
def test_each_net_profit_evidence_binds_its_frozen_base_bundle(year: int):
    evidence = _evidence(year)
    bundle_path = ROOT / evidence["base_bundle_path"]
    assert bundle_path == BUNDLE_DIR / f"{year}_annual.json"
    assert evidence["base_bundle_sha256"] == _sha256(bundle_path)
    assert evidence["base_bundle_git_blob"] == _git_blob(bundle_path)


@pytest.mark.parametrize("year", YEARS)
def test_evidence_binds_rule_005_and_duration_period(year: int):
    evidence = _evidence(year)
    assert evidence["contract"] == CONTRACT
    assert evidence["symbol"] == SYMBOL
    assert evidence["fiscal_year"] == year
    assert evidence["reconciliation_rule_id"] == RULE_ID
    assert evidence["reconciliation_rule_version"] == RULE_VERSION
    assert evidence["period_type"] == "duration"
    assert evidence["period_start"] == f"{year}-01-01"
    assert evidence["period_end"] == f"{year}-12-31"
    assert evidence["consolidation_scope"] == "consolidated"
    assert evidence["accounting_standard"] == "CAS"


@pytest.mark.parametrize("year", YEARS)
def test_exactly_one_direct_net_profit_line_per_source(year: int):
    evidence = _evidence(year)
    assert set(evidence["sources"]) == {"company", "exchange"}
    cp, pp = EXPECTED_PAGES[year][0], EXPECTED_PAGES[year][1]
    xp, xpp = EXPECTED_PAGES[year][2], EXPECTED_PAGES[year][3]
    for source, pdf_page, printed_page in (
        ("company", cp, pp),
        ("exchange", xp, xpp),
    ):
        facts = evidence["sources"][source]["facts"]
        assert len(facts) == 1
        item = facts[0]
        assert item["concept_id"] == "net_profit"
        assert item["source_label"] == "净利润"
        assert item["pdf_page"] == pdf_page
        assert item["printed_page"] == printed_page
        assert item["source_page"] == (
            f"PDF page {pdf_page} / printed page {printed_page}"
        )
        assert item["evidence_type"] == "audited_consolidated_income_statement"
        assert item["official_direct_disclosure"] is True
        assert item["manual_review_status"] == "visually_verified_twice"
        assert "利润表" in item["source_table"]


@pytest.mark.parametrize("year", YEARS)
def test_normalized_value_is_raw_times_100(year: int):
    evidence = _evidence(year)
    for source in ("company", "exchange"):
        item = evidence["sources"][source]["facts"][0]
        raw = int(item["raw_value"])
        assert raw == EXPECTED_RAW[year]
        assert item["raw_unit"] == "人民币百万元"
        assert item["normalization_rule"] == "RMB_MILLION_TO_CNY_10K_X100"
        assert item["expected_normalized_value"] == raw * 100


@pytest.mark.parametrize("year", YEARS)
def test_company_and_exchange_values_are_exactly_equal(year: int):
    evidence = _evidence(year)
    company = evidence["sources"]["company"]["facts"][0]
    exchange = evidence["sources"]["exchange"]["facts"][0]
    assert company["expected_normalized_value"] == (
        exchange["expected_normalized_value"]
    )
    assert company["raw_value"] == exchange["raw_value"]


@pytest.mark.parametrize("year", YEARS)
def test_income_statement_bridge_ties_exactly_and_is_not_a_fact_input(year: int):
    """归母 + 少数股东损益 == 净利润 is a cross-check only; the formal
    value is the directly disclosed line."""
    bridge = _evidence(year)["income_statement_bridge"]
    assert bridge["scope"] == "consolidated_only"
    direct = bridge["net_profit_direct_disclosure_line"]
    computed = bridge["computed_attributable_plus_minority"]
    assert computed == (
        bridge["net_profit_attributable_to_parent"]
        + bridge["minority_interest"]
    )
    assert direct == computed == EXPECTED_RAW[year]
    assert bridge["exact_tie_out"] is True
    assert bridge["bridge_status"] == "cross_check_only_not_a_fact_input"
    assert "direct_disclosure_line_only" in bridge["fact_creation"]


def test_2021_company_source_uses_text_layer_results_announcement():
    evidence = _evidence(2021)
    documents = evidence["documents"]
    assert set(documents) == {"company", "exchange"}
    company = documents["company"]
    assert company["sha256"] == RESULTS_ANNOUNCEMENT_2021_SHA
    # Stable identity: the override shares the audited-statements source_id,
    # so no version-chain identity changes.
    assert company["source_id"] == COMPANY_SOURCE_ID_2021
    assert company["source_tier"] == "company_official"
    assert company["document_scope"] == "annual_results_announcement"
    assert company["page_count"] == 44
    exchange = documents["exchange"]
    assert exchange["sha256"].startswith("939de04e")
    assert exchange["source_tier"] == "exchange_official"


@pytest.mark.parametrize("year", (2022, 2023, 2024, 2025))
def test_2022_to_2025_have_no_document_override(year: int):
    assert "documents" not in _evidence(year)


@pytest.mark.parametrize("year", YEARS)
def test_revision_review_status_per_year(year: int):
    assert _evidence(year)["revision_review_status"] == (
        EXPECTED_REVIEW_STATUS[year]
    )


@pytest.mark.parametrize("target", (2021, 2022, 2023, 2024))
def test_restatement_files_bind_years_and_changed_flags(target: int):
    review = _review(target)
    assert review["contract"] == REVIEW_CONTRACT
    assert review["symbol"] == SYMBOL
    assert review["target_fiscal_year"] == target
    assert review["evidence_fiscal_year"] == target + 1
    assert review["evidence_bundle_path"] == (
        f"acceptance/fixtures/official_facts/601857.SH/{target + 1}_annual.json"
    )
    concepts = review["concepts"]
    assert len(concepts) == 1
    item = concepts[0]
    assert item["concept_id"] == "net_profit"
    assert int(item["original_raw_value"]) == EXPECTED_RAW[target]
    assert int(item["later_comparative_raw_value"]) == EXPECTED_LATER[target]
    changed = EXPECTED_LATER[target] != EXPECTED_RAW[target]
    assert item["changed"] is changed
    assert item["changed"] is EXPECTED_CHANGED[target]
    assert (item["review_status"] == "reviewed_changed") is changed
    for source in ("company", "exchange"):
        assert item[source]["manual_review_status"] == "visually_verified_twice"


def test_r_equals_two_changed_years_are_2022_and_2023():
    changed = [
        target
        for target in (2021, 2022, 2023, 2024)
        if _review(target)["concepts"][0]["changed"]
    ]
    assert changed == [2022, 2023]


@pytest.mark.parametrize("target", (2021, 2022, 2023, 2024))
def test_restatement_later_comparative_bridge_ties_exactly(target: int):
    item = _review(target)["concepts"][0]
    later = int(item["later_comparative_raw_value"])
    npap = int(item["later_comparative_attributable_to_parent"])
    mi = int(item["later_comparative_minority_interest"])
    assert item["later_comparative_bridge_exact"] is True
    assert npap + mi == later


def test_no_existing_evidence_modified():
    """Prior-stage evidence Git blobs are frozen (spot-checked set)."""
    frozen = {
        "supplemental/2024_roe_roa_denominators.json":
            "a3ac548347addf54954798c6e3e45a3df708341a",
        "supplemental/2025_roe_roa_denominators.json":
            "6225087821b173eb59debf485ed1619a0c62c22d",
        "supplemental/2021_roe_roa_denominators.json":
            "410ed40578abeb7da6cb2d79bc676739be3a8ec8",
        "supplemental/2021_earnings_quality.json":
            "b9fc99818f19cea4c60c509c55663afcc042dd67",
    }
    for rel, blob in frozen.items():
        path = BUNDLE_DIR / rel
        assert _git_blob(path) == blob, rel
    frozen_reviews = {
        "roe_roa_denominators_2024_reviewed_by_2025.json":
            "868fac3598cda017e3f0f4ef3f2d249c2efa2f24",
        "roe_roa_denominators_2022_reviewed_by_2023.json":
            "fb0308a5c260e50dd397f393e5b9425ff48a419e",
    }
    for rel, blob in frozen_reviews.items():
        assert _git_blob(REVIEW_DIR / rel) == blob, rel


@pytest.mark.parametrize("year", YEARS)
def test_evidence_has_no_local_paths_or_embedded_artifacts(year: int):
    raw = (SUPP_DIR / f"{year}_net_profit.json").read_text(encoding="utf-8")
    assert "D:\\" not in raw
    assert "file://" not in raw
    assert "D:/" not in raw
    assert ".duckdb" not in raw
    assert ".pdf" not in raw or "final_pdf_url" in raw


@pytest.mark.parametrize("target", (2021, 2022, 2023, 2024))
def test_review_has_no_local_paths_or_embedded_artifacts(target: int):
    raw = (
        REVIEW_DIR / f"net_profit_{target}_reviewed_by_{target + 1}.json"
    ).read_text(encoding="utf-8")
    assert "D:\\" not in raw
    assert "file://" not in raw
    assert ".duckdb" not in raw
