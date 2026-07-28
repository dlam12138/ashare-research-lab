"""Shared test helpers for M2 fact tests.

``make_test_fact`` builds a fully-populated fact dict whose ``fact_id``
is always the canonical identity hash (see
:mod:`ashare_research.facts.identity`).  An explicit ``fact_id`` passed
in *overrides* is **ignored** so that no test can smuggle in a
non-canonical id -- the Repository and Service boundaries reject those.

Because fact_id is derived from the identity fields
(symbol, concept_id, concept_version, context_id, source_id,
fact_version, restatement_version, derivation_definition_id,
derivation_version), tests that need several *distinct* facts must vary
one of those fields (typically ``concept_id`` or ``source_id``).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from ashare_research.facts.identity import build_fact_id

# Canonical column order, matching FactRepository._FACT_COLS so that
# dicts produced here are directly storable.
FACT_COLS: list[str] = [
    "fact_id", "concept_id", "concept_version", "symbol",
    "value", "unit", "context_id", "is_derived", "derived_from",
    "derivation_definition_id", "derivation_version",
    "input_fact_ids", "source_provider", "source_id",
    "source_tier", "source_document", "source_url",
    "source_hash", "source_page", "source_table", "source_label",
    "fact_version", "restatement_version",
    "supersedes_fact_id", "filing_date", "period_end",
    "announcement_date", "available_at", "raw_value",
    "raw_unit", "normalized_value", "normalization_rule",
    "verification_status", "verification_note",
    "eligible_for_metrics", "created_at",
]


def make_test_fact(**overrides: Any) -> dict[str, Any]:
    """Create a minimal valid fact dict with a canonical ``fact_id``.

    Defaults describe a *candidate* (unverified) fact.  Pass overrides
    to turn it into a verified/official fact or to vary identity fields.

    ``fact_id`` is always recomputed from the identity fields; any
    ``fact_id`` in *overrides* is discarded.
    """
    base: dict[str, Any] = {
        "concept_id": "revenue",
        "concept_version": "1",
        "symbol": "000001.SZ",
        "value": 1000.0,
        "unit": "CNY",
        "context_id": "000001.SZ|2024|annual|consolidated",
        "is_derived": False,
        "derived_from": "",
        "derivation_definition_id": "",
        "derivation_version": "",
        "input_fact_ids": "",
        "source_provider": "test_provider",
        "source_id": "test_source",
        "source_tier": "candidate_aggregator",
        "source_document": "",
        "source_url": "",
        "source_hash": "",
        "source_page": "",
        "source_table": "",
        "source_label": "",
        "fact_version": 1,
        "restatement_version": "original",
        "supersedes_fact_id": "",
        "filing_date": "2025-03-28",
        "period_end": "2024-12-31",
        "announcement_date": "2025-03-28",
        "available_at": "2025-03-28",
        "raw_value": 1000.0,
        "raw_unit": "CNY",
        "normalized_value": 1000.0,
        "normalization_rule": "",
        "verification_status": "unverified",
        "verification_note": "",
        "eligible_for_metrics": False,
        "created_at": "2026-07-28T00:00:00",
    }
    base.update(overrides)
    # Canonical fact_id only -- never trust a caller-supplied id.
    base.pop("fact_id", None)
    base["fact_id"] = build_fact_id(base)
    return base


def make_verified_fact(**overrides: Any) -> dict[str, Any]:
    """A verified, metrics-eligible, company-official fact.

    Suitable for PIT queries (which filter on verified/reconciled +
    eligible_for_metrics with a non-empty available_at).
    """
    overrides.setdefault("verification_status", "verified")
    overrides.setdefault("source_tier", "company_official")
    overrides.setdefault("eligible_for_metrics", True)
    overrides.setdefault("source_id", "official_report_2025")
    return make_test_fact(**overrides)


def make_canonical_fact(**overrides: Any) -> dict[str, Any]:
    """Alias kept for readability at call sites."""
    return make_test_fact(**overrides)


def now_iso() -> str:
    """Stable ISO timestamp for tests (avoids Date.now in workflows)."""
    return datetime.now().isoformat()
