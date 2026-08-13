"""Registered 2021-2025 earnings-quality evidence contract."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from ashare_research.tools.earnings_quality_document_contract import (
    validate_earnings_quality_document_contract,
)

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "acceptance/fixtures/official_facts/601857.SH"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_all_five_years_validate_and_bind_each_fact_to_a_document():
    for year in range(2021, 2026):
        bundle_path = FIXTURES / f"{year}_annual.json"
        evidence = _load(FIXTURES / "supplemental" / f"{year}_earnings_quality.json")
        normalized = validate_earnings_quality_document_contract(
            evidence, _load(bundle_path)
        )
        assert evidence["base_bundle_sha256"] == hashlib.sha256(
            bundle_path.read_bytes()
        ).hexdigest()
        assert normalized["independent_content_sources"] is False
        assert all(
            fact["document_key"] in normalized["documents"]
            for source in normalized["sources"].values()
            for fact in source["facts"]
        )


def test_2021_uses_scoped_company_documents_and_stable_source_identity():
    evidence = _load(FIXTURES / "supplemental/2021_earnings_quality.json")
    documents = evidence["documents"]
    assert documents["company_audited_financial_statements"]["document_scope"] == (
        "audited_financial_statements"
    )
    assert documents["company_annual_results_announcement"]["document_scope"] == (
        "annual_results_announcement"
    )
    assert {
        documents[key]["source_id"]
        for key in (
            "company_audited_financial_statements",
            "company_annual_results_announcement",
        )
    } == {"company_ir:601857.SH:2021:annual:zh-cn"}
    assert evidence["non_recurring_bridge"]["bridge_status"] == (
        "reconciled_cross_document"
    )


def test_2021_announcement_cache_registration_is_exact():
    document = _load(
        FIXTURES / "supplemental/2021_earnings_quality.json"
    )["documents"]["company_annual_results_announcement"]
    assert document["source_hash"] == (
        "555a24ed0ace306ebb249faefd2d131e960cd008ad22df8929993c40183e4786"
    )
    assert document["content_length"] == 1_195_800
    assert document["page_count"] == 44
