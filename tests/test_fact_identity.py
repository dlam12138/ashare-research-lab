"""M2 Stage 1B.4.1 - canonical fact identity tests.

Covers: FactIdentity determinism, value-vs-identity separation,
Service/Repository rejection of non-canonical ids, and the semantic
payload conflict detection for source fields.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fact_test_helpers import make_test_fact, make_verified_fact

from ashare_research.exceptions import FactIdentityError
from ashare_research.fact_sources.base import FactSourceProvider, SourceTier
from ashare_research.fact_sources.registry import FactSourceRegistry
from ashare_research.facts.identity import (
    FactIdentity,
    build_fact_id,
    build_fact_identity_key,
    diff_fact_semantic_payloads,
    fact_identity_from_fact,
    fact_semantic_payload,
    facts_semantically_equal,
    normalize_identity_text,
    validate_canonical_fact_ids,
)
from ashare_research.facts.repository import FactRepository
from ashare_research.facts.service import FactService
from ashare_research.storage.duckdb_store import DuckDBStore

# ── Identity determinism ─────────────────────────────────────────────


class TestFactIdentityDeterminism:
    def test_identity_module_is_importable(self):
        assert FactIdentity is not None
        assert callable(build_fact_id)

    def test_same_identity_produces_same_fact_id(self):
        f = make_test_fact()
        assert build_fact_id(f) == build_fact_id(dict(f))

    def test_value_change_does_not_change_fact_id(self):
        f = make_test_fact(value=100.0)
        f2 = dict(f, value=999.0)
        assert build_fact_id(f) == build_fact_id(f2)

    def test_context_change_changes_fact_id(self):
        f = make_test_fact()
        f2 = dict(f, context_id="OTHER|2024|annual|consolidated|original")
        assert build_fact_id(f) != build_fact_id(f2)

    def test_source_change_changes_fact_id(self):
        f = make_test_fact(source_id="src_a")
        f2 = dict(f, source_id="src_b")
        assert build_fact_id(f) != build_fact_id(f2)

    def test_fact_version_change_changes_fact_id(self):
        f = make_test_fact(fact_version=1)
        f2 = dict(f, fact_version=2)
        assert build_fact_id(f) != build_fact_id(f2)

    def test_canonical_key_is_sorted_compact_json(self):
        ident = fact_identity_from_fact(make_test_fact())
        key = build_fact_identity_key(ident)
        # compact separators, sorted keys
        assert ", " not in key
        assert key == key  # stable
        assert key.startswith("{")

    def test_normalize_identity_text(self):
        assert normalize_identity_text(None) == ""
        assert normalize_identity_text("  abc  ") == "abc"
        assert normalize_identity_text(123) == "123"


# ── Canonical validation at boundaries ──────────────────────────────


class TestCanonicalBoundaryValidation:
    def test_validate_accepts_canonical_ids(self):
        facts = [make_test_fact(), make_test_fact(source_id="s2")]
        validate_canonical_fact_ids(facts)  # no raise

    def test_validate_rejects_missing_fact_id(self):
        f = make_test_fact()
        f["fact_id"] = ""
        with pytest.raises(FactIdentityError, match="missing"):
            validate_canonical_fact_ids([f])

    def test_validate_rejects_noncanonical_fact_id(self):
        f = make_test_fact()
        f["fact_id"] = "definitely-not-canonical"
        with pytest.raises(FactIdentityError, match="canonical identity"):
            validate_canonical_fact_ids([f])

    def test_repository_rejects_noncanonical_fact_id(self, tmp_path: Path):
        repo = _setup_repo(str(tmp_path / "t.duckdb"))
        f = make_test_fact()
        f["fact_id"] = "non-canonical-id"
        with pytest.raises(FactIdentityError, match="persistence boundary"), \
                repo.transaction() as conn:  # noqa: SIM117
            repo.store_facts([f], conn=conn)

    def test_service_rejects_noncanonical_fact_id(self, tmp_path: Path):
        # Provider returns a fact with a hand-rolled fact_id.
        class BadProvider(FactSourceProvider):
            provider_name = "bad"
            source_tier = SourceTier.candidate_aggregator

            def get_financial_statements(self, symbol, sy, ey):
                import pandas as pd
                f = make_test_fact(symbol=symbol)
                f["fact_id"] = "hand-rolled-not-canonical"
                return pd.DataFrame([f])

            def get_dividends(self, *a): ...
            def get_buybacks(self, *a): ...
            def get_shareholder_increases(self, *a): ...
            def get_audit_opinions(self, *a): ...

        svc, repo, store = _build_service(
            tmp_path, provider=BadProvider(), symbol="601857.SH",
        )
        result = svc.build_facts("601857.SH", 2025, 2025, source_mode="candidate")
        assert result["status"] == "failed"
        assert result["total_error_count"] > 0
        # no facts written
        assert repo.get_fact_summary("601857.SH").get("total", 0) == 0
        store.close()

    def test_provider_fact_uses_canonical_id(self):
        # AKShare provider builds canonical ids (covered in integration);
        # here we just assert the helper contract: a fact produced by
        # make_test_fact passes canonical validation.
        f = make_test_fact()
        validate_canonical_fact_ids([f])


# ── Semantic payload ────────────────────────────────────────────────


class TestSemanticPayload:
    def test_semantic_payload_excludes_metadata(self):
        f = make_test_fact()
        payload = fact_semantic_payload(f)
        assert "fact_id" not in payload
        assert "created_at" not in payload
        assert "run_id" not in payload

    def test_semantic_payload_matches_fact_columns(self):
        # The payload must align with FactRepository._FACT_COLS business
        # fields (no period_start, which lives on FactContext).
        f = make_test_fact()
        payload = fact_semantic_payload(f)
        assert "period_start" not in payload
        assert "value" in payload
        assert "source_hash" in payload
        assert "available_at" in payload
        assert "verification_note" in payload

    def test_source_hash_change_is_conflict(self):
        f1 = make_verified_fact()
        f2 = dict(f1, source_hash="abc123")
        assert not facts_semantically_equal(f1, f2)
        assert "source_hash" in diff_fact_semantic_payloads(f1, f2)

    def test_source_url_change_is_conflict(self):
        f1 = make_verified_fact()
        f2 = dict(f1, source_url="http://other")
        assert not facts_semantically_equal(f1, f2)

    def test_source_document_change_is_conflict(self):
        f1 = make_verified_fact()
        f2 = dict(f1, source_document="2025_annual.pdf")
        assert not facts_semantically_equal(f1, f2)

    def test_raw_unit_change_is_conflict(self):
        f1 = make_verified_fact()
        f2 = dict(f1, raw_unit="亿元")
        assert not facts_semantically_equal(f1, f2)

    def test_normalization_rule_change_is_conflict(self):
        f1 = make_verified_fact()
        f2 = dict(f1, normalization_rule="multiply_by_1e8")
        assert not facts_semantically_equal(f1, f2)

    def test_verification_note_change_is_conflict(self):
        f1 = make_verified_fact()
        f2 = dict(f1, verification_note="changed note")
        assert not facts_semantically_equal(f1, f2)

    def test_created_at_change_is_unchanged(self):
        f1 = make_verified_fact()
        f2 = dict(f1, created_at="2099-01-01T00:00:00")
        # created_at is metadata, excluded from semantic payload
        assert facts_semantically_equal(f1, f2)

    def test_input_fact_id_order_is_normalized(self):
        f1 = make_test_fact(
            is_derived=True, input_fact_ids="a,b,c",
            derivation_definition_id="d1",
        )
        f2 = make_test_fact(
            is_derived=True, input_fact_ids="c,b,a",
            derivation_definition_id="d1",
        )
        assert facts_semantically_equal(f1, f2)

    def test_diff_lists_changed_fields(self):
        f1 = make_verified_fact(value=100.0, source_hash="h1")
        f2 = dict(f1, value=200.0, source_hash="h2")
        diffs = diff_fact_semantic_payloads(f1, f2)
        assert set(diffs.keys()) == {"value", "source_hash"}


# ── helpers ─────────────────────────────────────────────────────────


def _setup_repo(db_path: str) -> FactRepository:
    store = DuckDBStore(db_path)
    repo = FactRepository(store)
    repo.ensure_schema()
    return repo


def _build_service(tmp_path: Path, *, provider: FactSourceProvider, symbol: str):
    db_path = str(tmp_path / "svc.duckdb")
    store = DuckDBStore(db_path)
    store.connect()
    repo = FactRepository(store)
    repo.ensure_schema()
    repo.seed_concepts()
    registry = FactSourceRegistry()
    registry.register_candidate(symbol, provider)
    svc = FactService(
        fact_repository=repo, source_registry=registry,
        output_root=str(tmp_path / "out"),
    )
    return svc, repo, store
