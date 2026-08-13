"""Regression tests for the committed 2023 annual evidence bundle.

These tests read registered JSON only. They never read local PDFs or access
the network, and they do not duplicate registered financial values.
"""

from __future__ import annotations

import json
from pathlib import Path, PureWindowsPath

from ashare_research.facts.identity import build_fact_id
from ashare_research.reconciliation.engine import ReconciliationEngine
from ashare_research.reconciliation.models import ReconciliationStatus
from ashare_research.tools.official_fact_acceptance import (
    EXPECTED_CONCEPTS,
    build_context,
    build_source_facts,
    normalize_registered_value,
    validate_bundle,
)

ROOT = Path(__file__).resolve().parents[1]
BUNDLE_DIR = ROOT / "acceptance" / "fixtures" / "official_facts" / "601857.SH"


def _load(year: int) -> dict:
    return json.loads(
        (BUNDLE_DIR / f"{year}_annual.json").read_text(encoding="utf-8")
    )


def _facts(bundle: dict) -> dict[str, list[dict]]:
    return build_source_facts(bundle, created_at="2026-07-29T00:00:00")


def test_registered_2023_bundle_validates():
    validate_bundle(_load(2023))


def test_registered_2023_bundle_uses_annual_cas_consolidated_zh_cn():
    bundle = _load(2023)
    assert (
        bundle["report_type"],
        bundle["accounting_standard"],
        bundle["consolidation_scope"],
        bundle["language"],
    ) == ("annual", "CAS", "consolidated", "zh-CN")


def test_registered_2023_bundle_has_exact_two_official_sources():
    documents = _load(2023)["documents"]
    assert set(documents) == {"company", "exchange"}
    assert documents["company"]["source_tier"] == "company_official"
    assert documents["exchange"]["source_tier"] == "exchange_official"


def test_registered_2023_bundle_has_exact_six_facts():
    assert len(_load(2023)["facts"]) == 6


def test_registered_2023_bundle_has_exact_three_concepts_per_source():
    facts = _load(2023)["facts"]
    for key in ("company", "exchange"):
        assert {
            fact["concept_id"] for fact in facts if fact["source_key"] == key
        } == EXPECTED_CONCEPTS


def test_registered_2023_source_ids_are_distinct():
    documents = _load(2023)["documents"]
    assert documents["company"]["source_id"] != documents["exchange"]["source_id"]


def test_registered_2023_values_normalize_without_float():
    for registered in _load(2023)["facts"]:
        normalized = normalize_registered_value(registered)
        assert type(normalized) is int
        assert normalized == registered["expected_normalized_value"]


def test_registered_2023_builds_six_canonical_source_facts():
    facts = [fact for group in _facts(_load(2023)).values() for fact in group]
    assert len(facts) == 6
    assert all(fact["fact_id"] == build_fact_id(fact) for fact in facts)


def test_registered_2023_three_pairs_match_in_memory():
    facts = _facts(_load(2023))
    by_source = {
        key: {fact["concept_id"]: fact for fact in group}
        for key, group in facts.items()
    }
    results = [
        ReconciliationEngine().reconcile_pair(
            by_source["company"][concept],
            by_source["exchange"][concept],
        )
        for concept in sorted(EXPECTED_CONCEPTS)
    ]
    assert [result.status for result in results] == [
        ReconciliationStatus.matched
    ] * 3


def test_registered_2023_fact_ids_differ_from_later_years():
    ids_by_year = {
        year: {
            (key, fact["concept_id"]): fact["fact_id"]
            for key, group in _facts(_load(year)).items()
            for fact in group
        }
        for year in (2023, 2024, 2025)
    }
    assert ids_by_year[2023].keys() == ids_by_year[2024].keys()
    assert ids_by_year[2023].keys() == ids_by_year[2025].keys()
    assert all(
        ids_by_year[2023][key] != ids_by_year[year][key]
        for year in (2024, 2025)
        for key in ids_by_year[2023]
    )


def test_registered_2023_available_at_uses_later_announcement():
    bundle = _load(2023)
    facts = _facts(bundle)
    company = {fact["concept_id"]: fact for fact in facts["company"]}
    exchange = {fact["concept_id"]: fact for fact in facts["exchange"]}
    later = max(
        document["announcement_date"]
        for document in bundle["documents"].values()
    )
    for concept in EXPECTED_CONCEPTS:
        result = ReconciliationEngine().reconcile_pair(
            company[concept], exchange[concept]
        )
        assert result.output_fact["available_at"] == later


def test_registered_2023_context_is_annual_duration():
    context = build_context(_load(2023), created_at="test")
    assert context["context_id"] == "601857.SH|2023|annual|consolidated"
    assert context["instant_or_duration"] == "duration"


def test_registered_2023_bundle_contains_no_local_absolute_paths():
    text = json.dumps(_load(2023), ensure_ascii=False)
    assert str(ROOT) not in text
    assert not PureWindowsPath(text).is_absolute()
