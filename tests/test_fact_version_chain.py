"""M2 Stage 1B.4.1 - Repository-aware version chain tests.

Covers FACT_VERSIONCHAIN_001: superseded fact existence, strict +1
version increment, stable identity consistency, no backwards dates,
cycle detection, and PIT restatement switching.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fact_test_helpers import make_verified_fact

from ashare_research.exceptions import VersionChainCycleError
from ashare_research.facts.as_of import AsOfQuery
from ashare_research.facts.identity import build_fact_id
from ashare_research.facts.repository import FactRepository
from ashare_research.storage.duckdb_store import DuckDBStore
from ashare_research.validation.version_chain import VersionChainValidator

SYMBOL = "000001.SZ"


def _setup_repo(db_path: str) -> FactRepository:
    store = DuckDBStore(db_path)
    repo = FactRepository(store)
    repo.ensure_schema()
    return repo


def _versioned_fact(
    *,
    fact_version: int,
    value: float,
    available_at: str,
    supersedes_fact_id: str = "",
    source_id: str = "official_v1",
) -> dict:
    """A verified fact with explicit version lineage fields."""
    base = make_verified_fact(
        symbol=SYMBOL,
        source_id=source_id,
        concept_id="revenue",
        context_id=f"{SYMBOL}|2024|annual|consolidated|original",
        period_end="2024-12-31",
        value=value,
        available_at=available_at,
        announcement_date=available_at,
        filing_date=available_at,
        fact_version=fact_version,
        supersedes_fact_id=supersedes_fact_id,
    )
    base["fact_id"] = build_fact_id(base)
    return base


# ── Pure field rules (FACT_VERSION_001) ─────────────────────────────


class TestVersionFieldRules:
    def test_version_one_cannot_supersede(self, tmp_path: Path):
        _setup_repo(str(tmp_path / "t.duckdb"))
        f = _versioned_fact(
            fact_version=1, value=100.0, available_at="2025-03-30",
            supersedes_fact_id="some-other-id",
        )
        from ashare_research.validation.validator import FactValidator
        results = FactValidator().validate_single_fact(f)
        failed = [r for r in results if r.rule_id == "FACT_VERSION_001"
                  and not r.passed]
        assert len(failed) == 1


# ── Repository-aware chain (FACT_VERSIONCHAIN_001) ──────────────────


class TestVersionChainValidator:
    def test_version_two_requires_superseded_fact_to_exist(self, tmp_path: Path):
        repo = _setup_repo(str(tmp_path / "t.duckdb"))
        v2 = _versioned_fact(
            fact_version=2, value=110.0, available_at="2025-06-01",
            supersedes_fact_id="does-not-exist",
        )
        results = VersionChainValidator(repo).validate(
            [v2], conn=repo.store.connect(),
        )
        assert any(r.rule_id == "FACT_VERSIONCHAIN_001" and not r.passed
                   for r in results)

    def test_superseded_fact_must_exist_in_batch(self, tmp_path: Path):
        repo = _setup_repo(str(tmp_path / "t.duckdb"))
        v1 = _versioned_fact(
            fact_version=1, value=100.0, available_at="2025-03-30",
        )
        v2 = _versioned_fact(
            fact_version=2, value=110.0, available_at="2025-06-01",
            supersedes_fact_id=v1["fact_id"],
        )
        results = VersionChainValidator(repo).validate(
            [v1, v2], conn=repo.store.connect(),
        )
        # v2 found v1 in batch -> pass
        v2_result = [r for r in results if r.target_id == v2["fact_id"]][0]
        assert v2_result.passed

    def test_superseded_fact_must_exist_in_repo(self, tmp_path: Path):
        repo = _setup_repo(str(tmp_path / "t.duckdb"))
        v1 = _versioned_fact(
            fact_version=1, value=100.0, available_at="2025-03-30",
        )
        with repo.transaction() as conn:
            repo.store_facts([v1], conn=conn)
        # now validate a v2 that references the persisted v1
        v2 = _versioned_fact(
            fact_version=2, value=110.0, available_at="2025-06-01",
            supersedes_fact_id=v1["fact_id"],
        )
        results = VersionChainValidator(repo).validate(
            [v2], conn=repo.store.connect(),
        )
        assert results[0].passed

    def test_fact_cannot_supersede_itself(self, tmp_path: Path):
        repo = _setup_repo(str(tmp_path / "t.duckdb"))
        f = _versioned_fact(
            fact_version=2, value=110.0, available_at="2025-06-01",
            supersedes_fact_id="self",
        )
        f["supersedes_fact_id"] = f["fact_id"]
        with pytest.raises(VersionChainCycleError):
            VersionChainValidator(repo).validate(
                [f], conn=repo.store.connect(),
            )

    def test_version_must_increase_by_one(self, tmp_path: Path):
        repo = _setup_repo(str(tmp_path / "t.duckdb"))
        v1 = _versioned_fact(
            fact_version=1, value=100.0, available_at="2025-03-30",
        )
        v3 = _versioned_fact(
            fact_version=3, value=110.0, available_at="2025-06-01",
            supersedes_fact_id=v1["fact_id"],
        )
        results = VersionChainValidator(repo).validate(
            [v1, v3], conn=repo.store.connect(),
        )
        v3_result = [r for r in results if r.target_id == v3["fact_id"]][0]
        assert not v3_result.passed

    def test_version_identity_must_match(self, tmp_path: Path):
        repo = _setup_repo(str(tmp_path / "t.duckdb"))
        v1 = _versioned_fact(
            fact_version=1, value=100.0, available_at="2025-03-30",
            source_id="official_v1",
        )
        # v2 has a different source_id -> different stable identity
        v2 = _versioned_fact(
            fact_version=2, value=110.0, available_at="2025-06-01",
            supersedes_fact_id=v1["fact_id"],
            source_id="different_source",
        )
        results = VersionChainValidator(repo).validate(
            [v1, v2], conn=repo.store.connect(),
        )
        v2_result = [r for r in results if r.target_id == v2["fact_id"]][0]
        assert not v2_result.passed
        assert "mismatched" in v2_result.message.lower() or \
               "mismatch" in v2_result.actual.lower()

    def test_version_available_at_cannot_move_backwards(self, tmp_path: Path):
        repo = _setup_repo(str(tmp_path / "t.duckdb"))
        v1 = _versioned_fact(
            fact_version=1, value=100.0, available_at="2025-06-01",
        )
        v2 = _versioned_fact(
            fact_version=2, value=110.0, available_at="2025-03-01",
            supersedes_fact_id=v1["fact_id"],
        )
        results = VersionChainValidator(repo).validate(
            [v1, v2], conn=repo.store.connect(),
        )
        v2_result = [r for r in results if r.target_id == v2["fact_id"]][0]
        assert not v2_result.passed
        assert "backwards" in v2_result.message.lower()

    def test_version_cycle_is_rejected(self, tmp_path: Path):
        repo = _setup_repo(str(tmp_path / "t.duckdb"))
        # Two distinct version-2 facts (different source_id -> different
        # identity -> different fact_id) that supersede each other.
        a = _versioned_fact(
            fact_version=2, value=110.0, available_at="2025-06-01",
            supersedes_fact_id="placeholder-a",
            source_id="official_cycle_a",
        )
        a["fact_id"] = build_fact_id(a)
        b = _versioned_fact(
            fact_version=2, value=120.0, available_at="2025-06-02",
            supersedes_fact_id="placeholder-b",
            source_id="official_cycle_b",
        )
        b["fact_id"] = build_fact_id(b)
        assert a["fact_id"] != b["fact_id"]
        # A supersedes B, B supersedes A
        a["supersedes_fact_id"] = b["fact_id"]
        b["supersedes_fact_id"] = a["fact_id"]
        with pytest.raises(VersionChainCycleError):
            VersionChainValidator(repo).validate(
                [a, b], conn=repo.store.connect(),
            )

    def test_old_fact_is_preserved(self, tmp_path: Path):
        repo = _setup_repo(str(tmp_path / "t.duckdb"))
        v1 = _versioned_fact(
            fact_version=1, value=100.0, available_at="2025-03-30",
            source_id="official_v1",
        )
        v2 = _versioned_fact(
            fact_version=2, value=110.0, available_at="2025-06-01",
            supersedes_fact_id=v1["fact_id"],
            source_id="official_v1",  # same stable identity
        )
        with repo.transaction() as conn:
            repo.store_facts([v1], conn=conn)
            repo.store_facts([v2], conn=conn)
        # both rows present (different fact_ids because fact_version differs)
        conn = repo.store.connect()
        n = conn.execute(
            "SELECT COUNT(*) FROM financial_facts WHERE symbol = ?",
            [SYMBOL],
        ).fetchone()[0]
        assert n == 2


# ── PIT restatement switching ───────────────────────────────────────


class TestPITRestatementSwitching:
    def _seed_two_versions(self, repo: FactRepository) -> tuple[dict, dict]:
        v1 = _versioned_fact(
            fact_version=1, value=100.0, available_at="2025-03-30",
            source_id="official_v1",
        )
        v2 = _versioned_fact(
            fact_version=2, value=110.0, available_at="2025-06-01",
            supersedes_fact_id=v1["fact_id"],
            source_id="official_v1",
        )
        with repo.transaction() as conn:
            repo.store_facts([v1], conn=conn)
            repo.store_facts([v2], conn=conn)
        return v1, v2

    def test_pit_returns_old_version_before_restatement(self, tmp_path: Path):
        repo = _setup_repo(str(tmp_path / "t.duckdb"))
        v1, v2 = self._seed_two_versions(repo)
        # also need the context for get_latest_available (joins fact_contexts)
        self._seed_context(repo)

        asof = AsOfQuery(repo)
        before = asof.get_latest_available(
            symbol=SYMBOL, as_of_date="2025-05-31",
        )
        assert not before.empty
        assert before.iloc[0]["value"] == 100.0
        assert int(before.iloc[0]["fact_version"]) == 1

    def test_pit_returns_new_version_on_restatement_date(self, tmp_path: Path):
        repo = _setup_repo(str(tmp_path / "t.duckdb"))
        v1, v2 = self._seed_two_versions(repo)
        self._seed_context(repo)

        asof = AsOfQuery(repo)
        on_restatement = asof.get_latest_available(
            symbol=SYMBOL, as_of_date="2025-06-01",
        )
        assert not on_restatement.empty
        assert on_restatement.iloc[0]["value"] == 110.0
        assert int(on_restatement.iloc[0]["fact_version"]) == 2

    def test_audit_query_sees_both_versions(self, tmp_path: Path):
        repo = _setup_repo(str(tmp_path / "t.duckdb"))
        v1, v2 = self._seed_two_versions(repo)
        asof = AsOfQuery(repo)
        audit = asof.get_all_versions_for_audit(symbol=SYMBOL)
        assert len(audit) == 2

    def _seed_context(self, repo: FactRepository) -> None:
        ctx = {
            "context_id": f"{SYMBOL}|2024|annual|consolidated|original",
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
            "filing_date": "2025-03-30",
            "created_at": "2026-07-28T00:00:00",
        }
        with repo.transaction() as conn:
            repo.store_contexts([ctx], conn=conn)
