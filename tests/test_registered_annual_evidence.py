"""Regression tests for committed annual evidence bundles.

These tests read registered JSON only.  They never read local PDFs or access
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


def test_registered_2024_bundle_validates():
    validate_bundle(_load(2024))


def test_registered_2024_bundle_uses_annual_cas_consolidated_zh_cn():
    bundle = _load(2024)
    assert (
        bundle["report_type"],
        bundle["accounting_standard"],
        bundle["consolidation_scope"],
        bundle["language"],
    ) == ("annual", "CAS", "consolidated", "zh-CN")


def test_registered_2024_bundle_has_exact_two_official_sources():
    documents = _load(2024)["documents"]
    assert set(documents) == {"company", "exchange"}
    assert documents["company"]["source_tier"] == "company_official"
    assert documents["exchange"]["source_tier"] == "exchange_official"


def test_registered_2024_bundle_has_exact_six_facts():
    assert len(_load(2024)["facts"]) == 6


def test_registered_2024_bundle_has_exact_three_concepts_per_source():
    facts = _load(2024)["facts"]
    for key in ("company", "exchange"):
        assert {
            fact["concept_id"] for fact in facts if fact["source_key"] == key
        } == EXPECTED_CONCEPTS


def test_registered_2024_source_ids_are_distinct():
    documents = _load(2024)["documents"]
    assert documents["company"]["source_id"] != documents["exchange"]["source_id"]


def test_registered_2024_values_normalize_without_float():
    for registered in _load(2024)["facts"]:
        normalized = normalize_registered_value(registered)
        assert type(normalized) is int
        assert normalized == registered["expected_normalized_value"]


def test_registered_2024_builds_six_canonical_source_facts():
    facts = [fact for group in _facts(_load(2024)).values() for fact in group]
    assert len(facts) == 6
    assert all(fact["fact_id"] == build_fact_id(fact) for fact in facts)


def test_registered_2024_three_pairs_match_in_memory():
    facts = _facts(_load(2024))
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


def test_registered_2024_fact_ids_differ_from_2025():
    ids_2024 = {
        (key, fact["concept_id"]): fact["fact_id"]
        for key, group in _facts(_load(2024)).items()
        for fact in group
    }
    ids_2025 = {
        (key, fact["concept_id"]): fact["fact_id"]
        for key, group in _facts(_load(2025)).items()
        for fact in group
    }
    assert ids_2024.keys() == ids_2025.keys()
    assert all(ids_2024[key] != ids_2025[key] for key in ids_2024)


def test_registered_2024_available_at_uses_later_announcement():
    bundle = _load(2024)
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


def test_registered_2024_context_is_annual_duration():
    context = build_context(_load(2024), created_at="test")
    assert context["context_id"] == "601857.SH|2024|annual|consolidated"
    assert context["instant_or_duration"] == "duration"


def test_registered_2024_bundle_contains_no_local_absolute_paths():
    text = json.dumps(_load(2024), ensure_ascii=False)
    assert str(ROOT) not in text
    assert not PureWindowsPath(text).is_absolute()
