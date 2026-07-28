"""Stage 1C-A.2 - Minimal official dual-source reconciliation tests.

Covers: AKShare source-semantics correction, the reconciliation engine's
hard gates, Decimal comparison (match / mismatch / insufficient /
not_comparable), reconciled-fact field contract, original-fact retention,
PIT/audit query semantics, idempotency, conflict, and lineage.

All tests are offline (tmp_path, temporary DuckDB, stubbed AKShare).  No
network, no report download, no real output/.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pandas as pd
import pytest

from ashare_research.exceptions import FactVersionConflictError
from ashare_research.fact_sources.base import FactSourceProvider, SourceTier
from ashare_research.fact_sources.candidates.akshare_financial import (
    AKShareFinancialCandidateProvider,
)
from ashare_research.fact_sources.registry import FactSourceRegistry
from ashare_research.facts.as_of import AsOfQuery
from ashare_research.facts.contexts import build_context_id
from ashare_research.facts.identity import build_fact_id
from ashare_research.facts.repository import FactRepository
from ashare_research.facts.service import FactService
from ashare_research.reconciliation.engine import ReconciliationEngine
from ashare_research.reconciliation.models import ReconciliationStatus
from ashare_research.reconciliation.service import (
    OfficialFactReconciliationService,
)
from ashare_research.storage.duckdb_store import DuckDBStore

SYMBOL = "601857.SH"
CTX_ID = build_context_id(SYMBOL, 2024, "annual")
REVENUE = 2_350_000_000_000.0
HASH64 = "a" * 64


# ── helpers ──────────────────────────────────────────────────────────


def _setup_repo(db_path: str) -> FactRepository:
    store = DuckDBStore(db_path)
    store.connect()
    repo = FactRepository(store)
    repo.ensure_schema()
    # Stage 1C-A.2.1: the service now requires the input context_id to be
    # registered in fact_contexts (it does not auto-create contexts).
    # Seed the canonical context for every repo used by reconciliation.
    _seed_context(repo)
    return repo


def _seed_context(repo: FactRepository) -> None:
    """get_latest_available JOINs fact_contexts, so the context must exist."""
    ctx = {
        "context_id": CTX_ID,
        "symbol": SYMBOL,
        "fiscal_year": 2024,
        "period_type": "annual",
        "period_start": "2024-01-01",
        "period_end": "2024-12-31",
        "instant_or_duration": "duration",
        "consolidation_scope": "consolidated",
        "accounting_standard": "CAS",
        "restatement_version": "original",
        "source_document": "",
        "filing_date": "2025-03-28",
        "created_at": "2026-07-28T00:00:00",
    }
    with repo.transaction() as conn:
        repo.store_contexts([ctx], conn=conn)


def _off_fact(
    *,
    source_tier: str,
    source_id: str,
    source_provider: str,
    value: float = REVENUE,
    concept_id: str = "revenue",
    context_id: str = CTX_ID,
    available_at: str = "2025-03-28",
    announcement_date: str = "2025-03-28",
    source_hash: str = HASH64,
    verification_status: str = "verified",
    eligible_for_metrics: bool = False,
    unit: str = "CNY",
    period_end: str = "2024-12-31",
    **overrides,
) -> dict:
    f = {
        "concept_id": concept_id,
        "concept_version": "1",
        "symbol": SYMBOL,
        "value": value,
        "unit": unit,
        "context_id": context_id,
        "is_derived": False,
        "derived_from": "",
        "derivation_definition_id": "",
        "derivation_version": "",
        "input_fact_ids": "",
        "source_provider": source_provider,
        "source_id": source_id,
        "source_tier": source_tier,
        "source_document": f"{source_provider} 2024 annual report",
        "source_url": f"https://example.com/{source_id}",
        "source_hash": source_hash,
        "source_page": "1",
        "source_table": "",
        "source_label": source_provider,
        "fact_version": 1,
        "restatement_version": "original",
        "supersedes_fact_id": "",
        "fiscal_year": 2024,
        "report_type": "annual",
        "period_end": period_end,
        "filing_date": announcement_date,
        "announcement_date": announcement_date,
        "available_at": available_at,
        "raw_value": value,
        "raw_unit": "CNY",
        "normalized_value": value,
        "normalization_rule": "identity",
        "verification_status": verification_status,
        "verification_note": f"{source_provider} official",
        "eligible_for_metrics": eligible_for_metrics,
        "created_at": "2026-07-28T00:00:00",
    }
    f.update(overrides)
    f["fact_id"] = build_fact_id(f)
    return f


def _company(**kw) -> dict:
    kw.setdefault("source_id", f"{SYMBOL}_company_website::2024::revenue")
    kw.setdefault("source_provider", f"{SYMBOL}_company_website")
    return _off_fact(source_tier="company_official", **kw)


def _exchange(**kw) -> dict:
    kw.setdefault("source_id", f"{SYMBOL}_exchange::2024::revenue")
    kw.setdefault("source_provider", f"{SYMBOL}_exchange")
    return _off_fact(source_tier="exchange_official", **kw)


def _reconcile_service(repo: FactRepository) -> OfficialFactReconciliationService:
    return OfficialFactReconciliationService(repo)


# ── 1. AKShare source semantics ──────────────────────────────────────


class TestAKShareNotOfficial:
    def test_akshare_provider_is_not_registered_as_official(self):
        """The old AKShare 'official' provider is gone; AKShare is candidate."""
        import importlib
        with pytest.raises(ModuleNotFoundError):
            importlib.import_module("ashare_research.official_sources.petrochina")
        # the candidate provider is the only AKShare path
        assert (
            AKShareFinancialCandidateProvider.source_tier
            == SourceTier.candidate_aggregator
        )

    def test_akshare_fact_uses_candidate_source_tier(self):
        """Facts from the AKShare provider carry candidate_aggregator."""
        provider = AKShareFinancialCandidateProvider()
        fake_df = pd.DataFrame([{"报告期": "20241231", "营业收入": 1e11}])

        class _FakeAk:
            def __getattr__(self, _name):
                def _api(*, symbol):  # noqa: ARG001
                    return fake_df
                return _api
        import ashare_research.fact_sources.candidates.akshare_financial as mod
        with patch.object(mod, "ak", _FakeAk()):
            df = provider.get_financial_statements(SYMBOL, 2024, 2024)
        assert not df.empty
        assert all(r["source_tier"] == "candidate_aggregator"
                   for r in df.to_dict("records"))

    def test_official_provider_does_not_fallback_to_akshare(
        self, tmp_path: Path,
    ):
        """official mode with no official provider fails; candidate unused."""
        calls = {"candidate": 0}

        class _CountingCandidate(FactSourceProvider):
            provider_name = "counting_candidate"
            source_tier = SourceTier.candidate_aggregator

            def get_financial_statements(self, s, sy, ey):
                calls["candidate"] += 1
                return pd.DataFrame()
            def get_dividends(self, *a): return pd.DataFrame()
            def get_buybacks(self, *a): return pd.DataFrame()
            def get_shareholder_increases(self, *a): return pd.DataFrame()
            def get_audit_opinions(self, *a): return pd.DataFrame()

        store = DuckDBStore(str(tmp_path / "nofb.duckdb"))
        store.connect()
        repo = FactRepository(store)
        repo.ensure_schema()
        repo.seed_concepts()
        registry = FactSourceRegistry()
        registry.register_candidate(SYMBOL, _CountingCandidate())
        service = FactService(
            fact_repository=repo, source_registry=registry,
            output_root=str(tmp_path / "out"),
        )
        result = service.build_facts(
            symbol=SYMBOL, start_year=2024, end_year=2024,
            source_mode="official",
        )
        assert result["status"] == "failed"
        assert calls["candidate"] == 0
        conn = store.connect()
        n = conn.execute(
            "SELECT COUNT(*) FROM financial_facts WHERE symbol = ?",
            [SYMBOL],
        ).fetchone()[0]
        assert n == 0
        store.close()


# ── 2. Reconciliation engine: matched -> reconciled fact ─────────────


class TestReconciliationMatched:
    def test_company_and_exchange_match_create_reconciled_fact(
        self, tmp_path: Path,
    ):
        repo = _setup_repo(str(tmp_path / "m.duckdb"))
        svc = _reconcile_service(repo)
        result = svc.reconcile_official_pair(_company(), _exchange())
        assert result.status == ReconciliationStatus.matched
        assert result.output_fact is not None
        conn = repo.store.connect()
        n = conn.execute(
            "SELECT COUNT(*) FROM financial_facts WHERE symbol = ?",
            [SYMBOL],
        ).fetchone()[0]
        assert n == 3  # company + exchange + reconciled
        store = repo.store
        store.close()

    def test_reconciled_fact_uses_reconciled_source_tier(
        self, tmp_path: Path,
    ):
        repo = _setup_repo(str(tmp_path / "m.duckdb"))
        svc = _reconcile_service(repo)
        result = svc.reconcile_official_pair(_company(), _exchange())
        rec = result.output_fact
        assert rec["source_tier"] == "reconciled_derived"
        assert rec["verification_status"] == "reconciled"
        assert rec["eligible_for_metrics"] is True

    def test_reconciled_fact_uses_canonical_fact_id(self, tmp_path: Path):
        repo = _setup_repo(str(tmp_path / "m.duckdb"))
        svc = _reconcile_service(repo)
        result = svc.reconcile_official_pair(_company(), _exchange())
        rec = result.output_fact
        assert rec["fact_id"] == build_fact_id(rec)
        # full 64-char sha256
        assert len(rec["fact_id"]) == 64

    def test_reconciled_fact_references_both_inputs(self, tmp_path: Path):
        repo = _setup_repo(str(tmp_path / "m.duckdb"))
        svc = _reconcile_service(repo)
        company = _company()
        exchange = _exchange()
        result = svc.reconcile_official_pair(company, exchange)
        rec = result.output_fact
        stored = {s for s in rec["input_fact_ids"].split(",") if s}
        assert stored == {company["fact_id"], exchange["fact_id"]}
        # stably sorted
        assert rec["input_fact_ids"] == ",".join(
            sorted([company["fact_id"], exchange["fact_id"]]),
        )

    def test_reconciled_available_at_uses_later_input(self, tmp_path: Path):
        repo = _setup_repo(str(tmp_path / "m.duckdb"))
        svc = _reconcile_service(repo)
        company = _company(available_at="2025-03-28")
        exchange = _exchange(available_at="2025-04-10")
        result = svc.reconcile_official_pair(company, exchange)
        assert result.output_fact["available_at"] == "2025-04-10"

    def test_reconciled_announcement_uses_later_input(self, tmp_path: Path):
        repo = _setup_repo(str(tmp_path / "m.duckdb"))
        svc = _reconcile_service(repo)
        company = _company(announcement_date="2025-03-28")
        # available_at must be >= announcement_date for a verified input.
        exchange = _exchange(
            announcement_date="2025-04-10", available_at="2025-04-10",
        )
        result = svc.reconcile_official_pair(company, exchange)
        assert result.output_fact["announcement_date"] == "2025-04-10"


# ── 3. Original fact retention + query semantics ─────────────────────


class TestRetentionAndQueries:
    def _reconciled(self, tmp_path: Path):
        repo = _setup_repo(str(tmp_path / "q.duckdb"))
        _seed_context(repo)
        svc = _reconcile_service(repo)
        company = _company()
        exchange = _exchange()
        result = svc.reconcile_official_pair(company, exchange)
        return repo, company, exchange, result

    def test_original_official_facts_remain_ineligible(self, tmp_path: Path):
        repo, company, exchange, result = self._reconciled(tmp_path)
        conn = repo.store.connect()
        rows = conn.execute(
            """SELECT source_tier, eligible_for_metrics, verification_status
               FROM financial_facts WHERE symbol = ? ORDER BY source_tier""",
            [SYMBOL],
        ).fetchall()
        by_tier = {r[0]: (r[1], r[2]) for r in rows}
        assert by_tier["company_official"] == (False, "verified")
        assert by_tier["exchange_official"] == (False, "verified")
        assert by_tier["reconciled_derived"] == (True, "reconciled")
        repo.store.close()

    def test_default_pit_query_returns_only_reconciled_fact(
        self, tmp_path: Path,
    ):
        repo, company, exchange, result = self._reconciled(tmp_path)
        asof = AsOfQuery(repo)
        df = asof.get_latest_available(SYMBOL, as_of_date="2025-04-01")
        assert len(df) == 1
        assert df.iloc[0]["fact_id"] == result.output_fact["fact_id"]
        assert df.iloc[0]["verification_status"] == "reconciled"
        repo.store.close()

    def test_audit_query_returns_all_three_facts(self, tmp_path: Path):
        repo, company, exchange, result = self._reconciled(tmp_path)
        df = repo.get_all_versions_for_audit(SYMBOL)
        assert len(df) == 3
        fids = set(df["fact_id"].tolist())
        assert fids == {
            company["fact_id"], exchange["fact_id"],
            result.output_fact["fact_id"],
        }
        repo.store.close()


# ── 4. Rejection / not-comparable / insufficient ─────────────────────


class TestReconciliationGates:
    def test_same_source_tier_is_not_comparable(self):
        eng = ReconciliationEngine()
        # both company_official
        result = eng.reconcile_pair(_company(), _company())
        assert result.status == ReconciliationStatus.not_comparable
        assert result.output_fact is None

    def test_candidate_input_is_rejected(self):
        eng = ReconciliationEngine()
        candidate = _off_fact(
            source_tier="candidate_aggregator",
            source_id="akshare::2024::revenue",
            source_provider="akshare",
        )
        result = eng.reconcile_pair(candidate, _exchange())
        assert result.status == ReconciliationStatus.not_comparable

    def test_unverified_input_is_insufficient_evidence(self):
        eng = ReconciliationEngine()
        company = _company(verification_status="unverified")
        result = eng.reconcile_pair(company, _exchange())
        assert result.status == ReconciliationStatus.insufficient_evidence

    def test_missing_source_hash_is_insufficient_evidence(self):
        eng = ReconciliationEngine()
        company = _company(source_hash="")
        result = eng.reconcile_pair(company, _exchange())
        assert result.status == ReconciliationStatus.insufficient_evidence

    def test_different_context_is_not_comparable(self):
        eng = ReconciliationEngine()
        other_ctx = build_context_id(SYMBOL, 2024, "quarter_ytd")
        exchange = _exchange(context_id=other_ctx, period_end="2024-03-31")
        result = eng.reconcile_pair(_company(), exchange)
        assert result.status == ReconciliationStatus.not_comparable

    def test_different_scope_is_not_comparable(self):
        eng = ReconciliationEngine()
        parent_ctx = build_context_id(
            SYMBOL, 2024, "annual", "parent_company",
        )
        exchange = _exchange(context_id=parent_ctx)
        result = eng.reconcile_pair(_company(), exchange)
        assert result.status == ReconciliationStatus.not_comparable

    def test_unsupported_concept_is_insufficient_evidence(self):
        eng = ReconciliationEngine()
        company = _company(concept_id="total_assets")
        exchange = _exchange(concept_id="total_assets")
        result = eng.reconcile_pair(company, exchange)
        assert result.status == ReconciliationStatus.insufficient_evidence


# ── 5. Decimal comparison: match / mismatch ──────────────────────────


class TestDecimalComparison:
    def test_exact_decimal_match_succeeds(self):
        eng = ReconciliationEngine()
        result = eng.reconcile_pair(_company(), _exchange())
        assert result.status == ReconciliationStatus.matched
        assert result.output_fact is not None

    def test_value_mismatch_does_not_create_reconciled_fact(self):
        eng = ReconciliationEngine()
        company = _company(value=2.35e11)
        exchange = _exchange(value=2.36e11)
        result = eng.reconcile_pair(company, exchange)
        assert result.status == ReconciliationStatus.mismatch
        assert result.output_fact is None

    def test_mismatch_records_both_values_and_difference(self):
        eng = ReconciliationEngine()
        company = _company(value=2.35e11)
        exchange = _exchange(value=2.36e11)
        result = eng.reconcile_pair(company, exchange)
        assert result.company_normalized_value
        assert result.exchange_normalized_value
        assert result.absolute_difference
        from decimal import Decimal
        diff = abs(
            Decimal(result.company_normalized_value)
            - Decimal(result.exchange_normalized_value),
        )
        assert Decimal(result.absolute_difference) == diff


# ── 6. Idempotency, conflict, lineage ─────────────────────────────────


class TestIdempotencyConflictLineage:
    def test_reconciliation_repeat_is_idempotent(self, tmp_path: Path):
        repo = _setup_repo(str(tmp_path / "idem.duckdb"))
        svc = _reconcile_service(repo)
        company = _company()
        exchange = _exchange()
        svc.reconcile_official_pair(company, exchange)
        svc.reconcile_official_pair(company, exchange)
        conn = repo.store.connect()
        n = conn.execute(
            "SELECT COUNT(*) FROM financial_facts WHERE symbol = ?",
            [SYMBOL],
        ).fetchone()[0]
        assert n == 3  # no duplicate fact rows on repeat
        repo.store.close()

    def test_reconciliation_changed_payload_conflicts(self, tmp_path: Path):
        """Same reconciled identity but changed value -> conflict, no
        auto-versioning."""
        repo = _setup_repo(str(tmp_path / "conf.duckdb"))
        svc = _reconcile_service(repo)
        # pair A: value 100
        company_a = _company(value=1.0e11, source_id="company_A")
        exchange_a = _exchange(value=1.0e11, source_id="exchange_A")
        svc.reconcile_official_pair(company_a, exchange_a)
        # pair B: different sources (no input conflict) but value 200 ->
        # same reconciled fact_id, different value -> conflict
        company_b = _company(value=2.0e11, source_id="company_B")
        exchange_b = _exchange(value=2.0e11, source_id="exchange_B")
        with pytest.raises(FactVersionConflictError):
            svc.reconcile_official_pair(company_b, exchange_b)
        repo.store.close()

    def test_reconciliation_lineage_references_both_inputs(
        self, tmp_path: Path,
    ):
        repo = _setup_repo(str(tmp_path / "lin.duckdb"))
        svc = _reconcile_service(repo)
        company = _company()
        exchange = _exchange()
        result = svc.reconcile_official_pair(company, exchange)
        conn = repo.store.connect()
        row = conn.execute(
            "SELECT parent_fact_ids, source_provider, source_method "
            "FROM fact_lineage WHERE fact_id = ?",
            [result.output_fact["fact_id"]],
        ).fetchone()
        parents = {s for s in row[0].split(",") if s}
        assert parents == {company["fact_id"], exchange["fact_id"]}
        assert row[1] == "official_reconciliation"
        assert row[2] == "dual_source_reconciliation"
        repo.store.close()
