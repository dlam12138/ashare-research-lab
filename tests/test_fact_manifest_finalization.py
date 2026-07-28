"""M2 Stage 1B.4.1 - manifest finalization timing tests.

The run must be marked ``finalized`` only *after* a successful
``write_manifest``.  A write failure must raise
``LineagePersistenceError`` and leave the run unfinalized, never
reported as successful.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest import mock

import pandas as pd
import pytest

from ashare_research.exceptions import LineagePersistenceError
from ashare_research.fact_sources.base import FactSourceProvider, SourceTier
from ashare_research.fact_sources.registry import FactSourceRegistry
from ashare_research.facts.identity import build_fact_id
from ashare_research.facts.repository import FactRepository
from ashare_research.facts.service import FactService
from ashare_research.storage.duckdb_store import DuckDBStore

SYMBOL = "601857.SH"


class _StubProvider(FactSourceProvider):
    provider_name = "manifest_stub"
    source_tier = SourceTier.candidate_aggregator

    def get_financial_statements(self, symbol, sy, ey):
        from datetime import datetime
        now = datetime.now().isoformat()
        f = {
            "concept_id": "revenue", "concept_version": "1",
            "symbol": symbol, "value": 1e11, "unit": "CNY",
            "context_id": f"{symbol}|{sy}|FY|consolidated",
            "source_provider": self.provider_name,
            "source_id": f"stub::{symbol}::{sy}",
            "source_tier": "candidate_aggregator",
            "fact_version": 1, "fiscal_year": sy,
            "report_type": "FY", "period_end": f"{sy}-12-31",
            "filing_date": f"{sy + 1}-03-28",
            "announcement_date": f"{sy + 1}-03-28",
            "available_at": f"{sy + 1}-03-28",
            "verification_status": "unverified",
            "eligible_for_metrics": False,
            "restatement_version": "original",
            "raw_value": 1e11, "raw_unit": "CNY",
            "normalized_value": 1e11,
            "created_at": now,
        }
        f["fact_id"] = build_fact_id(f)
        return pd.DataFrame([f])

    def get_dividends(self, *a): return pd.DataFrame()
    def get_buybacks(self, *a): return pd.DataFrame()
    def get_shareholder_increases(self, *a): return pd.DataFrame()
    def get_audit_opinions(self, *a): return pd.DataFrame()


def _build_service(tmp_path: Path) -> tuple[FactService, FactRepository, DuckDBStore]:
    db_path = str(tmp_path / "mf.duckdb")
    store = DuckDBStore(db_path)
    store.connect()
    repo = FactRepository(store)
    repo.ensure_schema()
    repo.seed_concepts()
    registry = FactSourceRegistry()
    registry.register_candidate(SYMBOL, _StubProvider())
    svc = FactService(
        fact_repository=repo, source_registry=registry,
        output_root=str(tmp_path / "out"),
    )
    return svc, repo, store


class TestManifestFinalization:
    def test_manifest_finalized_after_successful_write(self, tmp_path: Path):
        svc, repo, store = _build_service(tmp_path)
        svc.build_facts(SYMBOL, 2025, 2025, source_mode="candidate")
        assert svc._build_run_state is not None
        assert svc._build_run_state.finalized is True
        assert svc._build_run_state.manifest_path
        assert Path(svc._build_run_state.manifest_path).is_file()
        store.close()

    def test_manifest_not_finalized_before_write(self, tmp_path: Path):
        svc, repo, store = _build_service(tmp_path)
        # before any build, no run state exists -> not finalized
        assert svc._build_run_state is None
        store.close()

    def test_manifest_write_failure_raises(self, tmp_path: Path):
        svc, repo, store = _build_service(tmp_path)
        # patch the lowest-level atomic replace to raise
        with mock.patch(
            "ashare_research.lineage.manifest.os.replace",
            side_effect=OSError("disk full"),
        ), pytest.raises(LineagePersistenceError, match="run manifest"):
            svc.build_facts(SYMBOL, 2025, 2025, source_mode="candidate")
        store.close()

    def test_manifest_write_failure_leaves_run_unfinalized(self, tmp_path: Path):
        svc, repo, store = _build_service(tmp_path)
        with mock.patch(
            "ashare_research.lineage.manifest.os.replace",
            side_effect=OSError("disk full"),
        ), pytest.raises(LineagePersistenceError):
            svc.build_facts(SYMBOL, 2025, 2025, source_mode="candidate")
        # the build succeeded up to manifest write; run must NOT be finalized
        assert svc._build_run_state is not None
        assert svc._build_run_state.finalized is False
        store.close()

    def test_manifest_write_failure_is_not_reported_as_passed(
        self, tmp_path: Path,
    ):
        svc, repo, store = _build_service(tmp_path)
        with mock.patch(
            "ashare_research.lineage.manifest.os.replace",
            side_effect=OSError("disk full"),
        ), pytest.raises(LineagePersistenceError):
            svc.build_facts(SYMBOL, 2025, 2025, source_mode="candidate")
        # no manifest file written
        manifests = list(Path(str(tmp_path / "out")).rglob("run_manifest.json"))
        assert manifests == []
        store.close()

    def test_each_run_writes_exactly_one_manifest(self, tmp_path: Path):
        svc, repo, store = _build_service(tmp_path)
        svc.build_facts(SYMBOL, 2025, 2025, source_mode="candidate")
        svc.build_facts(SYMBOL, 2025, 2025, source_mode="candidate")
        manifests = list(Path(str(tmp_path / "out")).rglob("run_manifest.json"))
        assert len(manifests) == 2
        run_ids = set()
        for m in manifests:
            with open(m, encoding="utf-8") as f:
                run_ids.add(json.load(f)["run_id"])
        assert len(run_ids) == 2
        store.close()

    def test_unexpected_derivation_error_writes_failed_manifest(
        self, tmp_path: Path,
    ):
        svc, repo, store = _build_service(tmp_path)
        # force derivation to blow up
        def _boom(_df):
            raise RuntimeError("derivation crashed")
        svc.engine.derive_all = _boom  # type: ignore[assignment]
        # wrap in try so the unexpected-error path writes a failed manifest
        with pytest.raises(RuntimeError, match="Unexpected failure"):
            svc.build_facts(SYMBOL, 2025, 2025, source_mode="candidate")
        manifests = list(Path(str(tmp_path / "out")).rglob("run_manifest.json"))
        assert len(manifests) == 1
        with open(manifests[0], encoding="utf-8") as f:
            data = json.load(f)
        assert data["status"] == "failed"
        store.close()
