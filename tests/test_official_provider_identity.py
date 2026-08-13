"""Stage 1C-A - Official provider canonical identity contract (3 layers).

The old AKShare-based ``PetroChinaProvider`` (official_sources/petrochina.py)
has been deleted in Stage 1C-A.2 because it duplicated the candidate provider
while mislabeling AKShare data as ``company_official``.  The sole company
official entry point is now ``PetroChinaOfficialFilingProvider``.

Layer 1 (Provider): ``PetroChinaOfficialFilingProvider`` forces manual facts
canonical at the provider exit; a wrong fact_id is recomputed.

Layer 2 (Service): the official build path accepts canonical facts and
rejects a non-canonical injection.

Layer 3 (Repository): store_facts rejects a non-canonical official fact.

No test accesses the network.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from ashare_research.exceptions import (
    FactIdentityError,
    SourceDocumentError,
)
from ashare_research.fact_sources.base import FactSourceProvider, SourceTier
from ashare_research.fact_sources.official.petrochina_filings import (
    PetroChinaOfficialFilingProvider,
)
from ashare_research.fact_sources.registry import FactSourceRegistry
from ashare_research.facts.contexts import build_context_id
from ashare_research.facts.identity import build_fact_id
from ashare_research.facts.repository import FactRepository
from ashare_research.facts.service import FactService
from ashare_research.storage.duckdb_store import DuckDBStore

SYMBOL = "601857.SH"


# ── helpers ──────────────────────────────────────────────────────────


def _canonical_official_fact(
    *, value: float = 1e11, source_id: str | None = None,
    fact_version: int = 1, restatement_version: str = "original",
    available_at: str = "2025-03-28",
) -> dict:
    f = {
        "concept_id": "revenue",
        "concept_version": "1",
        "symbol": SYMBOL,
        "value": value,
        "unit": "CNY",
        "context_id": build_context_id(SYMBOL, 2024, "annual"),
        "is_derived": False,
        "source_provider": "petrochina_official_filing",
        "source_id": source_id or "pc_official::2024::revenue",
        "source_tier": "company_official",
        "source_document": "2024 annual report",
        "fact_version": fact_version,
        "restatement_version": restatement_version,
        "supersedes_fact_id": "",
        "fiscal_year": 2024,
        "report_type": "annual",
        "period_end": "2024-12-31",
        "filing_date": available_at,
        "announcement_date": available_at,
        "available_at": available_at,
        "raw_value": value,
        "raw_unit": "CNY",
        "normalized_value": value,
        "normalization_rule": "identity",
        "verification_status": "verified",
        "eligible_for_metrics": True,
        "created_at": "2026-07-28T00:00:00",
    }
    f["fact_id"] = build_fact_id(f)
    return f


# ── Layer 1: PetroChinaOfficialFilingProvider (fact_sources) ──────────


class TestOfficialFilingProviderCanonical:
    def test_no_manual_facts_raises_not_empty(self, tmp_path: Path):
        p = PetroChinaOfficialFilingProvider()
        with __import__("pytest").raises(SourceDocumentError):
            p.get_financial_statements(SYMBOL, 2024, 2024)

    def test_manual_facts_forced_canonical(self):
        fact = _canonical_official_fact()
        p = PetroChinaOfficialFilingProvider(manual_facts=[fact])
        df = p.get_financial_statements(SYMBOL, 2024, 2024)
        assert len(df) == 1
        assert df.iloc[0]["fact_id"] == build_fact_id(fact)

    def test_wrong_fact_id_is_recomputed_not_trusted(self):
        """A caller-supplied fact_id is overwritten by the canonical one."""
        fact = _canonical_official_fact()
        fact["fact_id"] = "DELIBERATELY_WRONG"
        p = PetroChinaOfficialFilingProvider(manual_facts=[fact])
        df = p.get_financial_statements(SYMBOL, 2024, 2024)
        assert df.iloc[0]["fact_id"] == build_fact_id(fact)
        assert df.iloc[0]["fact_id"] != "DELIBERATELY_WRONG"

    def test_fact_version_change_changes_fact_id(self):
        f1 = _canonical_official_fact(fact_version=1)
        f2 = _canonical_official_fact(fact_version=2)
        assert f1["fact_id"] != f2["fact_id"]

    def test_source_id_change_changes_fact_id(self):
        f1 = _canonical_official_fact(source_id="src_a")
        f2 = _canonical_official_fact(source_id="src_b")
        assert f1["fact_id"] != f2["fact_id"]


# ── Layer 2: Service rejects non-canonical official facts ────────────


class TestServiceOfficialLayer:
    def _service(self, tmp_path: Path, provider: FactSourceProvider):
        db = str(tmp_path / "svc.duckdb")
        store = DuckDBStore(db)
        store.connect()
        repo = FactRepository(store)
        repo.ensure_schema()
        repo.seed_concepts()
        registry = FactSourceRegistry()
        registry.register_official(SYMBOL, provider)
        service = FactService(
            fact_repository=repo, source_registry=registry,
            output_root=str(tmp_path / "out"),
        )
        return service, repo, store

    def test_service_accepts_canonical_official_facts(self, tmp_path: Path):
        fact = _canonical_official_fact()
        provider = PetroChinaOfficialFilingProvider(manual_facts=[fact])
        service, repo, store = self._service(tmp_path, provider)
        result = service.build_facts(
            symbol=SYMBOL, start_year=2024, end_year=2024,
            source_mode="official",
        )
        assert result["status"] != "failed"
        conn = store.connect()
        n = conn.execute(
            "SELECT COUNT(*) FROM financial_facts WHERE symbol = ?",
            [SYMBOL],
        ).fetchone()[0]
        assert n >= 1
        store.close()

    def test_service_rejects_non_canonical_official_facts(
        self, tmp_path: Path,
    ):
        """A provider that smuggles in a non-canonical id is rejected."""
        fact = _canonical_official_fact()
        fact["fact_id"] = "TAMPERED_ID"

        class _TamperProvider(FactSourceProvider):
            provider_name = "tamper_official"
            source_tier = SourceTier.company_official

            def get_financial_statements(self, s, sy, ey):
                return pd.DataFrame([dict(fact)])

            def get_dividends(self, *a):
                return pd.DataFrame()
            def get_buybacks(self, *a):
                return pd.DataFrame()
            def get_shareholder_increases(self, *a):
                return pd.DataFrame()
            def get_audit_opinions(self, *a):
                return pd.DataFrame()

        service, repo, store = self._service(tmp_path, _TamperProvider())
        result = service.build_facts(
            symbol=SYMBOL, start_year=2024, end_year=2024,
            source_mode="official",
        )
        assert result["status"] == "failed"
        conn = store.connect()
        n = conn.execute(
            "SELECT COUNT(*) FROM financial_facts WHERE symbol = ?",
            [SYMBOL],
        ).fetchone()[0]
        assert n == 0
        store.close()


# ── Layer 3: Repository rejects non-canonical official facts ──────────


class TestRepositoryOfficialLayer:
    def test_store_rejects_non_canonical_official_fact(self, tmp_path: Path):
        store = DuckDBStore(str(tmp_path / "repo.duckdb"))
        store.connect()
        repo = FactRepository(store)
        repo.ensure_schema()
        fact = _canonical_official_fact()
        fact["fact_id"] = "NOT_CANONICAL"
        import pytest
        with pytest.raises(FactIdentityError), \
                repo.transaction() as conn:
            repo.store_facts([fact], conn=conn)
        store.close()

    def test_store_accepts_canonical_official_fact(self, tmp_path: Path):
        store = DuckDBStore(str(tmp_path / "repo2.duckdb"))
        store.connect()
        repo = FactRepository(store)
        repo.ensure_schema()
        fact = _canonical_official_fact()
        with repo.transaction() as conn:
            res = repo.store_facts([fact], conn=conn)
        assert res.inserted == 1
        store.close()
