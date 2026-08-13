"""Document-scope contract for earnings-quality official evidence."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from ashare_research.tools.earnings_quality_document_contract import (
    EarningsQualityDocumentContractError,
    normalize_earnings_quality_evidence,
    validate_earnings_quality_document_contract,
)

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "acceptance/fixtures/official_facts/601857.SH/2025_annual.json"
EVIDENCE = (
    ROOT
    / "acceptance/fixtures/official_facts/601857.SH/supplemental"
    / "2025_earnings_quality.json"
)


def _base() -> dict:
    return json.loads(BASE.read_text(encoding="utf-8"))


def _legacy() -> dict:
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def _scoped() -> tuple[dict, dict]:
    base = _base()
    evidence = normalize_earnings_quality_evidence(_legacy(), base)
    announcement_key = "company_annual_results_announcement"
    company_document = copy.deepcopy(
        evidence["documents"]["company_full_annual_report"]
    )
    for legacy_key in ("final_pdf_url", "pdf_url", "sha256"):
        company_document.pop(legacy_key, None)
    company_document.update(
        {
            "document_key": announcement_key,
            "source_document": (
                "中国石油天然气股份有限公司二零二一年度业绩公告（年度报告摘要）"
            ),
            "document_scope": "annual_results_announcement",
            "source_url": "https://www.petrochina.com.cn/formal-annual-results.pdf",
            "source_hash": "a" * 64,
            "issuer": "中国石油天然气股份有限公司",
            "stock_code": "601857",
            "fiscal_year": evidence["fiscal_year"],
            "formal_annual_disclosure": True,
            "direct_financial_data_disclosure": True,
        }
    )
    evidence["documents"][announcement_key] = company_document
    adjusted = next(
        fact
        for fact in evidence["sources"]["company"]["facts"]
        if fact["concept_id"] == "net_profit_excluding_non_recurring"
    )
    adjusted.update(
        {
            "document_key": announcement_key,
            "source_document": company_document["source_document"],
            "document_scope": company_document["document_scope"],
            "source_url": company_document["source_url"],
            "source_hash": company_document["source_hash"],
            "evidence_scope": "annual_results_announcement_direct_disclosure",
        }
    )
    return evidence, base


def test_frozen_2025_evidence_normalizes_without_file_change():
    before = EVIDENCE.read_bytes()
    normalized = validate_earnings_quality_document_contract(_legacy(), _base())
    assert EVIDENCE.read_bytes() == before
    assert set(normalized["documents"]) == {
        "company_full_annual_report",
        "exchange_full_annual_report",
    }
    assert all(
        fact["document_key"].startswith(source_key)
        for source_key, source in normalized["sources"].items()
        for fact in source["facts"]
    )


def test_annual_results_announcement_can_carry_adjusted_profit():
    evidence, base = _scoped()
    normalized = validate_earnings_quality_document_contract(evidence, base)
    adjusted = next(
        fact
        for fact in normalized["sources"]["company"]["facts"]
        if fact["concept_id"] == "net_profit_excluding_non_recurring"
    )
    assert adjusted["document_scope"] == "annual_results_announcement"


def test_ordinary_news_release_is_not_a_formal_annual_scope():
    evidence, base = _scoped()
    document = evidence["documents"]["company_annual_results_announcement"]
    document["source_document"] = "中国石油2021年度业绩新闻稿"
    with pytest.raises(EarningsQualityDocumentContractError, match="news release"):
        validate_earnings_quality_document_contract(evidence, base)


@pytest.mark.parametrize(
    "field",
    ["issuer", "stock_code", "fiscal_year", "formal_annual_disclosure"],
)
def test_annual_summary_requires_issuer_code_year_and_formal_identity(field: str):
    evidence, base = _scoped()
    document = evidence["documents"]["company_annual_results_announcement"]
    document["document_scope"] = "annual_report_summary"
    document[field] = None
    adjusted = next(
        fact
        for fact in evidence["sources"]["company"]["facts"]
        if fact["concept_id"] == "net_profit_excluding_non_recurring"
    )
    adjusted["document_scope"] = "annual_report_summary"
    with pytest.raises(EarningsQualityDocumentContractError, match=field):
        validate_earnings_quality_document_contract(evidence, base)


@pytest.mark.parametrize("concept_id", ["operating_cost", "operating_profit"])
def test_announcement_cannot_carry_audited_statement_concepts(concept_id: str):
    evidence, base = _scoped()
    fact = next(
        item
        for item in evidence["sources"]["company"]["facts"]
        if item["concept_id"] == concept_id
    )
    document = evidence["documents"]["company_annual_results_announcement"]
    fact.update(
        {
            "document_key": document["document_key"],
            "source_document": document["source_document"],
            "document_scope": document["document_scope"],
            "source_url": document["source_url"],
            "source_hash": document["source_hash"],
            "evidence_scope": "annual_results_announcement_direct_disclosure",
        }
    )
    with pytest.raises(
        EarningsQualityDocumentContractError,
        match="document scope cannot carry concept",
    ):
        validate_earnings_quality_document_contract(evidence, base)


def test_one_stable_source_id_can_bind_different_formal_documents():
    evidence, base = _scoped()
    normalized = validate_earnings_quality_document_contract(evidence, base)
    company_documents = {
        fact["document_key"] for fact in normalized["sources"]["company"]["facts"]
    }
    assert company_documents == {
        "company_full_annual_report",
        "company_annual_results_announcement",
    }
    assert {
        normalized["documents"][key]["source_id"] for key in company_documents
    } == {base["documents"]["company"]["source_id"]}


def test_document_key_and_bound_metadata_must_match_registry():
    evidence, base = _scoped()
    adjusted = next(
        fact
        for fact in evidence["sources"]["company"]["facts"]
        if fact["concept_id"] == "net_profit_excluding_non_recurring"
    )
    adjusted["source_hash"] = "b" * 64
    with pytest.raises(EarningsQualityDocumentContractError, match="binding differs"):
        validate_earnings_quality_document_contract(evidence, base)


def test_announcement_cannot_be_mislabeled_as_full_report():
    evidence, base = _scoped()
    adjusted = next(
        fact
        for fact in evidence["sources"]["company"]["facts"]
        if fact["concept_id"] == "net_profit_excluding_non_recurring"
    )
    adjusted["document_scope"] = "full_annual_report"
    with pytest.raises(EarningsQualityDocumentContractError, match="binding differs"):
        validate_earnings_quality_document_contract(evidence, base)


def test_independent_content_sources_remains_false():
    evidence, base = _scoped()
    evidence["independent_content_sources"] = True
    with pytest.raises(EarningsQualityDocumentContractError, match="not independent"):
        validate_earnings_quality_document_contract(evidence, base)
