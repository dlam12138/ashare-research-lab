"""Stage 1C-A.2.1 - Reconciliation contract consistency closure tests.

Covers the six contract fixes: single SourceTier enum, FACT_SOURCE_001
verified/reconciled split, full service validation (incl. context
existence + FACT_RECON_INPUT_001), cross-unit comparison order, v1 万元
integral numeric storage (no float, safe-integer range), symbol-agnostic
source_id, lineage roles, revalidation, and idempotency.

All tests are offline (tmp_path, temporary DuckDB).  No network, no report
download, no real output/.  A second symbol (600519.SH) proves the engine
is not bound to PetroChina.
"""

from __future__ import annotations

import inspect
import json
from contextlib import contextmanager
from dataclasses import replace
from pathlib import Path

import pytest

from ashare_research.exceptions import (
    FactVersionConflictError,
    ReconciliationValidationError,
)
from ashare_research.facts.as_of import AsOfQuery
from ashare_research.facts.contexts import build_context_id
from ashare_research.facts.identity import build_fact_id
from ashare_research.facts.repository import FactRepository
from ashare_research.reconciliation.engine import (
    RULE_ID,
    RULE_VERSION,
    ReconciliationEngine,
    build_reconciliation_source_id,
)
from ashare_research.reconciliation.models import ReconciliationStatus
from ashare_research.reconciliation.service import (
    OfficialFactReconciliationService,
)
from ashare_research.storage.duckdb_store import DuckDBStore
from ashare_research.validation.validator import FactValidator

SYMBOL_A = "601857.SH"
SYMBOL_B = "600519.SH"
HASH64 = "a" * 64
REVENUE_YUAN = 2_350_000_000_000.0  # 元 -> 235_000_000 万元


# ── helpers ──────────────────────────────────────────────────────────


def _ctx(symbol: str) -> str:
    return build_context_id(symbol, 2024, "annual")


def _seed_context(repo: FactRepository, symbol: str) -> None:
    ctx = {
        "context_id": _ctx(symbol),
        "symbol": symbol,
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


def _setup_repo(db_path: str, symbol: str = SYMBOL_A) -> FactRepository:
    store = DuckDBStore(db_path)
    store.connect()
    repo = FactRepository(store)
    repo.ensure_schema()
    _seed_context(repo, symbol)
    return repo


def _off_fact(
    symbol: str,
    *,
    source_tier: str,
    source_id: str,
    source_provider: str,
    value: float = REVENUE_YUAN,
    unit: str = "CNY",
    concept_id: str = "revenue",
    available_at: str = "2025-03-28",
    announcement_date: str = "2025-03-28",
    source_hash: str = HASH64,
    **overrides,
) -> dict:
    f = {
        "concept_id": concept_id,
        "concept_version": "1",
        "symbol": symbol,
        "value": value,
        "unit": unit,
        "context_id": _ctx(symbol),
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
        "period_end": "2024-12-31",
        "filing_date": announcement_date,
        "announcement_date": announcement_date,
        "available_at": available_at,
        "raw_value": value,
        "raw_unit": unit,
        "normalized_value": value,
        "normalization_rule": "identity",
        "verification_status": "verified",
        "verification_note": f"{source_provider} official",
        "eligible_for_metrics": False,
        "created_at": "2026-07-28T00:00:00",
    }
    f.update(overrides)
    f["fact_id"] = build_fact_id(f)
    return f


def _company(symbol: str = SYMBOL_A, **kw) -> dict:
    kw.setdefault("source_id", f"{symbol}_company_website::2024::revenue")
    kw.setdefault("source_provider", f"{symbol}_company_website")
    return _off_fact(symbol, source_tier="company_official", **kw)


def _exchange(symbol: str = SYMBOL_A, **kw) -> dict:
    kw.setdefault("source_id", f"{symbol}_exchange::2024::revenue")
    kw.setdefault("source_provider", f"{symbol}_exchange")
    return _off_fact(symbol, source_tier="exchange_official", **kw)


def _svc(repo: FactRepository) -> OfficialFactReconciliationService:
    return OfficialFactReconciliationService(repo)


def _expected_source_id(symbol: str) -> str:
    return build_reconciliation_source_id(symbol, RULE_ID, RULE_VERSION)


class _OutputMutatingEngine(ReconciliationEngine):
    def __init__(self, **changes) -> None:
        super().__init__()
        self.changes = changes

    def reconcile_pair(self, company_fact, exchange_fact, *, now=None):
        result = super().reconcile_pair(
            company_fact, exchange_fact, now=now,
        )
        assert result.output_fact is not None
        output = dict(result.output_fact)
        output.update(self.changes)
        output["fact_id"] = build_fact_id(output)
        return replace(result, output_fact=output)


class _BadLineageService(OfficialFactReconciliationService):
    @staticmethod
    def _build_reconciliation_lineage(
        company_fact, exchange_fact, output_fact, run_id,
    ):
        rows = OfficialFactReconciliationService._build_reconciliation_lineage(
            company_fact, exchange_fact, output_fact, run_id,
        )
        rows[2]["parent_fact_ids"] = "wrong_parent_a,wrong_parent_b"
        return rows


class _SwappedRoleLineageService(OfficialFactReconciliationService):
    @staticmethod
    def _build_reconciliation_lineage(
        company_fact, exchange_fact, output_fact, run_id,
    ):
        rows = OfficialFactReconciliationService._build_reconciliation_lineage(
            company_fact, exchange_fact, output_fact, run_id,
        )
        rows[0]["fact_id"], rows[1]["fact_id"] = (
            rows[1]["fact_id"], rows[0]["fact_id"],
        )
        return rows


class _FailingMetaRepository(FactRepository):
    def store_schema_meta(self, *args, **kwargs) -> None:
        raise RuntimeError("simulated metadata write failure")


LEGACY_SCHEMA_V20_SQL = """
CREATE TABLE fact_schema_meta (
    schema_name VARCHAR PRIMARY KEY,
    schema_version VARCHAR NOT NULL,
    applied_at VARCHAR NOT NULL,
    git_commit VARCHAR DEFAULT ''
);
CREATE TABLE financial_facts (
    fact_id VARCHAR PRIMARY KEY,
    concept_id VARCHAR NOT NULL,
    concept_version VARCHAR DEFAULT '1',
    symbol VARCHAR NOT NULL,
    value DOUBLE,
    unit VARCHAR NOT NULL DEFAULT 'CNY',
    context_id VARCHAR NOT NULL,
    is_derived BOOLEAN DEFAULT FALSE,
    derived_from VARCHAR DEFAULT '',
    derivation_definition_id VARCHAR DEFAULT '',
    derivation_version VARCHAR DEFAULT '',
    input_fact_ids VARCHAR DEFAULT '',
    source_provider VARCHAR NOT NULL DEFAULT '',
    source_id VARCHAR DEFAULT '',
    source_tier VARCHAR DEFAULT 'candidate_aggregator',
    source_document VARCHAR DEFAULT '',
    source_url VARCHAR DEFAULT '',
    source_hash VARCHAR DEFAULT '',
    source_page VARCHAR DEFAULT '',
    source_table VARCHAR DEFAULT '',
    source_label VARCHAR DEFAULT '',
    fact_version INTEGER DEFAULT 1,
    restatement_version VARCHAR DEFAULT 'original',
    supersedes_fact_id VARCHAR DEFAULT '',
    filing_date VARCHAR DEFAULT '',
    period_end VARCHAR DEFAULT '',
    announcement_date VARCHAR DEFAULT '',
    available_at VARCHAR DEFAULT '',
    raw_value DOUBLE,
    raw_unit VARCHAR DEFAULT '',
    normalized_value DOUBLE,
    normalization_rule VARCHAR DEFAULT '',
    verification_status VARCHAR DEFAULT 'unverified',
    verification_note VARCHAR DEFAULT '',
    eligible_for_metrics BOOLEAN DEFAULT FALSE,
    created_at VARCHAR NOT NULL DEFAULT ''
);
CREATE TABLE fact_contexts (
    context_id VARCHAR PRIMARY KEY,
    symbol VARCHAR NOT NULL,
    fiscal_year INTEGER NOT NULL,
    period_type VARCHAR NOT NULL,
    period_start VARCHAR DEFAULT '',
    period_end VARCHAR DEFAULT '',
    instant_or_duration VARCHAR DEFAULT 'duration',
    consolidation_scope VARCHAR DEFAULT 'consolidated',
    accounting_standard VARCHAR DEFAULT 'CAS',
    restatement_version VARCHAR DEFAULT 'original',
    source_document VARCHAR DEFAULT '',
    filing_date VARCHAR DEFAULT '',
    created_at VARCHAR NOT NULL DEFAULT ''
);
CREATE TABLE fact_lineage (
    lineage_id INTEGER PRIMARY KEY,
    fact_id VARCHAR NOT NULL,
    run_id VARCHAR DEFAULT '',
    source_provider VARCHAR NOT NULL DEFAULT '',
    source_tier VARCHAR DEFAULT '',
    source_method VARCHAR DEFAULT '',
    raw_file_path VARCHAR DEFAULT '',
    staging_file_path VARCHAR DEFAULT '',
    fetch_run_id VARCHAR DEFAULT '',
    parent_fact_ids VARCHAR DEFAULT '',
    recorded_at VARCHAR NOT NULL DEFAULT ''
);
CREATE SEQUENCE fact_lineage_seq START 2;
"""


def _legacy_schema_20_repo(db_path: str) -> FactRepository:
    """Create and seed the exact relevant physical schema from 86696b8."""
    store = DuckDBStore(db_path)
    conn = store.connect()
    for statement in LEGACY_SCHEMA_V20_SQL.split(";"):
        if statement.strip():
            conn.execute(statement)
    conn.execute(
        "INSERT INTO fact_schema_meta VALUES "
        "('financial_facts', '2.0', '2026-07-27T00:00:00', '86696b8')"
    )
    conn.execute(
        """INSERT INTO fact_contexts
           (context_id, symbol, fiscal_year, period_type, period_end,
            created_at)
           VALUES ('legacy_ctx', '601857.SH', 2024, 'annual',
                   '2024-12-31', '2026-07-27T00:00:00')"""
    )
    conn.execute(
        """INSERT INTO financial_facts
           (fact_id, concept_id, symbol, value, unit, context_id,
            source_provider, source_id, created_at)
           VALUES ('legacy_fact', 'revenue', '601857.SH', 123456.0,
                   '万元', 'legacy_ctx', 'legacy_provider', 'legacy_source',
                   '2026-07-27T00:00:00')"""
    )
    conn.execute(
        """INSERT INTO fact_lineage
           (lineage_id, fact_id, run_id, source_provider, source_tier,
            source_method, parent_fact_ids, recorded_at)
           VALUES (1, 'legacy_fact', 'legacy_run', 'legacy_provider',
                   'company_official', 'legacy_fetch', '',
                   '2026-07-27T00:00:00')"""
    )
    return FactRepository(store)


def _assert_prewrite_rejection(
    repo: FactRepository,
    service: OfficialFactReconciliationService,
) -> None:
    transaction_entered = {"value": False}
    original_transaction = repo.transaction

    @contextmanager
    def tracked_transaction():
        transaction_entered["value"] = True
        with original_transaction() as conn:
            yield conn

    repo.transaction = tracked_transaction  # type: ignore[method-assign]
    with pytest.raises(ReconciliationValidationError) as exc:
        service.reconcile_official_pair(_company(), _exchange())
    assert "FACT_RECON_INPUT_001" in str(exc.value)
    assert transaction_entered["value"] is False
    conn = repo.store.connect()
    assert conn.execute(
        "SELECT COUNT(*) FROM financial_facts"
    ).fetchone()[0] == 0
    assert conn.execute(
        "SELECT COUNT(*) FROM fact_lineage"
    ).fetchone()[0] == 0


# ── 1. SourceTier single enum ───────────────────────────────────────


class TestSourceTierSingleEnum:
    def test_only_one_source_tier_enum_exists(self):
        import ast

        src_root = Path("src/ashare_research")
        defs = []
        for py in src_root.rglob("*.py"):
            tree = ast.parse(py.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef) and node.name == "SourceTier":
                    defs.append(str(py))
        assert [Path(path).as_posix() for path in defs] == [
            "src/ashare_research/facts/models.py"
        ], defs

    def test_fact_source_base_reuses_fact_model_source_tier(self):
        from ashare_research.fact_sources.base import SourceTier as BaseTier
        from ashare_research.facts.models import SourceTier as ModelTier
        assert BaseTier is ModelTier
        assert hasattr(BaseTier, "reconciled_derived")

    def test_reconciliation_status_strenum_compatibility(self):
        status = ReconciliationStatus.matched
        assert str(status) == "matched"
        assert status == "matched"
        assert json.dumps({"status": status}) == '{"status": "matched"}'

    def test_reconciled_source_tier_is_shared_across_layers(self):
        from ashare_research.fact_sources.base import SourceTier as BaseTier
        from ashare_research.facts.models import SourceTier as ModelTier
        from ashare_research.facts.service import SourceTier as SvcTier
        assert BaseTier is SvcTier is ModelTier


# ── 2. FACT_SOURCE_001 verified / reconciled split ──────────────────


class TestFactSourceRule:
    def _v(self):
        return FactValidator()

    def test_verified_company_fact_passes_source_rule(self):
        results = self._v().validate_single_fact(_company())
        src = [r for r in results if r.rule_id == "FACT_SOURCE_001"]
        assert not any(not r.passed for r in src)

    def test_verified_exchange_fact_passes_source_rule(self):
        results = self._v().validate_single_fact(_exchange())
        src = [r for r in results if r.rule_id == "FACT_SOURCE_001"]
        assert not any(not r.passed for r in src)

    def test_verified_candidate_fact_fails_source_rule(self):
        cand = _off_fact(
            SYMBOL_A, source_tier="candidate_aggregator",
            source_id="akshare::rev", source_provider="akshare",
        )
        results = self._v().validate_single_fact(cand)
        src = [r for r in results if r.rule_id == "FACT_SOURCE_001"]
        assert any(not r.passed for r in src)

    def test_reconciled_derived_fact_passes_source_rule(self, tmp_path: Path):
        repo = _setup_repo(str(tmp_path / "r.duckdb"))
        result = _svc(repo).reconcile_official_pair(_company(), _exchange())
        rec = result.output_fact
        results = self._v().validate_single_fact(rec)
        src = [r for r in results if r.rule_id == "FACT_SOURCE_001"]
        assert not any(not r.passed for r in src), src

    def test_reconciled_fact_with_company_source_tier_fails(self):
        rec = _off_fact(
            SYMBOL_A, source_tier="company_official",
            source_id=_expected_source_id(SYMBOL_A),
            source_provider="official_reconciliation",
            verification_status="reconciled", eligible_for_metrics=True,
            is_derived=True, derivation_definition_id="official_dual_source_reconciliation",
            derivation_version="1",
            input_fact_ids=",".join(["id_a", "id_b"]),
        )
        results = FactValidator().validate_single_fact(rec)
        src = [r for r in results if r.rule_id == "FACT_SOURCE_001"]
        assert any(not r.passed for r in src)

    def test_reconciled_fact_without_two_inputs_fails(self):
        rec = _off_fact(
            SYMBOL_A, source_tier="reconciled_derived",
            source_id=_expected_source_id(SYMBOL_A),
            source_provider="official_reconciliation",
            verification_status="reconciled", eligible_for_metrics=True,
            is_derived=True, derivation_definition_id="official_dual_source_reconciliation",
            derivation_version="1", input_fact_ids="only_one_id",
        )
        results = FactValidator().validate_single_fact(rec)
        src = [r for r in results if r.rule_id == "FACT_SOURCE_001"]
        assert any(not r.passed for r in src)

    def test_reconciled_fact_without_derivation_metadata_fails(self):
        rec = _off_fact(
            SYMBOL_A, source_tier="reconciled_derived",
            source_id=_expected_source_id(SYMBOL_A),
            source_provider="official_reconciliation",
            verification_status="reconciled", eligible_for_metrics=True,
            is_derived=True, derivation_definition_id="",
            derivation_version="",
            input_fact_ids=",".join(["id_a", "id_b"]),
        )
        results = FactValidator().validate_single_fact(rec)
        src = [r for r in results if r.rule_id == "FACT_SOURCE_001"]
        assert any(not r.passed for r in src)

    def test_reconciled_fact_with_wrong_provider_fails(self):
        rec = _off_fact(
            SYMBOL_A, source_tier="reconciled_derived",
            source_id=_expected_source_id(SYMBOL_A),
            source_provider="not_official_reconciliation",
            verification_status="reconciled", eligible_for_metrics=True,
            is_derived=True, derivation_definition_id="official_dual_source_reconciliation",
            derivation_version="1",
            input_fact_ids=",".join(["id_a", "id_b"]),
        )
        results = FactValidator().validate_single_fact(rec)
        src = [r for r in results if r.rule_id == "FACT_SOURCE_001"]
        assert any(not r.passed for r in src)


# ── 3. Service full validation ──────────────────────────────────────


class TestServiceFullValidation:
    def test_service_runs_full_validator_on_company_input(self, tmp_path: Path):
        repo = _setup_repo(str(tmp_path / "s.duckdb"))
        # company input missing available_at -> FACT_PIT_001 validator error
        # (the service validates inputs before calling the engine)
        bad_company = _company(available_at="")
        with pytest.raises(ReconciliationValidationError):
            _svc(repo).reconcile_official_pair(bad_company, _exchange())

    def test_service_runs_full_validator_on_exchange_input(self, tmp_path: Path):
        repo = _setup_repo(str(tmp_path / "s.duckdb"))
        bad_exchange = _exchange(announcement_date="2024-06-30")
        with pytest.raises(ReconciliationValidationError):
            _svc(repo).reconcile_official_pair(_company(), bad_exchange)

    def test_service_runs_full_validator_on_output(self, tmp_path: Path):
        """Output fact is validated; a monkeypatched bad output is rejected
        and nothing is written."""
        repo = _setup_repo(str(tmp_path / "s.duckdb"))
        svc = _svc(repo)

        original = svc.engine._build_reconciled_fact

        def _bad_output(company, exchange, matched_value, *, now):
            fact = original(company, exchange, matched_value, now=now)
            fact["source_provider"] = "wrong"  # breaks FACT_SOURCE_001
            return fact

        svc.engine._build_reconciled_fact = _bad_output  # type: ignore
        with pytest.raises(ReconciliationValidationError):
            svc.reconcile_official_pair(_company(), _exchange())
        conn = repo.store.connect()
        n = conn.execute(
            "SELECT COUNT(*) FROM financial_facts WHERE symbol = ?",
            [SYMBOL_A],
        ).fetchone()[0]
        assert n == 0  # rolled back, nothing written
        repo.store.close()

    def test_service_rejects_missing_context(self, tmp_path: Path):
        store = DuckDBStore(str(tmp_path / "nc.duckdb"))
        store.connect()
        repo = FactRepository(store)
        repo.ensure_schema()
        # no context seeded
        with pytest.raises(ReconciliationValidationError) as ei:
            _svc(repo).reconcile_official_pair(_company(), _exchange())
        assert _ctx(SYMBOL_A) in str(ei.value)
        store.close()

    def test_service_rejects_invalid_source_pair(self, tmp_path: Path):
        repo = _setup_repo(str(tmp_path / "sp.duckdb"))
        # two company_official inputs -> engine not_comparable, no write
        result = _svc(repo).reconcile_official_pair(_company(), _company())
        assert result.status == ReconciliationStatus.not_comparable
        assert result.output_fact is None
        conn = repo.store.connect()
        n = conn.execute(
            "SELECT COUNT(*) FROM financial_facts WHERE symbol = ?",
            [SYMBOL_A],
        ).fetchone()[0]
        assert n == 0
        repo.store.close()

    def test_service_does_not_write_on_validation_error(self, tmp_path: Path):
        repo = _setup_repo(str(tmp_path / "nw.duckdb"))
        with pytest.raises(ReconciliationValidationError):
            _svc(repo).reconcile_official_pair(
                _company(available_at=""), _exchange(),
            )
        conn = repo.store.connect()
        n = conn.execute(
            "SELECT COUNT(*) FROM financial_facts WHERE symbol = ?",
            [SYMBOL_A],
        ).fetchone()[0]
        assert n == 0
        repo.store.close()

    def test_service_writes_all_rows_in_one_transaction(self, tmp_path: Path):
        repo = _setup_repo(str(tmp_path / "tx.duckdb"))
        result = _svc(repo).reconcile_official_pair(_company(), _exchange())
        conn = repo.store.connect()
        facts = conn.execute(
            "SELECT COUNT(*) FROM financial_facts WHERE symbol = ?",
            [SYMBOL_A],
        ).fetchone()[0]
        lin = conn.execute(
            "SELECT COUNT(*) FROM fact_lineage WHERE run_id LIKE 'recon_%'",
        ).fetchone()[0]
        assert facts == 3  # company + exchange + reconciled
        assert lin == 3   # input_company + input_exchange + output
        assert result.output_fact is not None
        repo.store.close()

    def test_service_rolls_back_on_lineage_failure(self, tmp_path: Path):
        """If lineage write fails mid-transaction, the whole txn rolls back
        (no reconciled fact, no input facts)."""
        repo = _setup_repo(str(tmp_path / "rb.duckdb"))
        svc = _svc(repo)
        original_lineage = repo.store_lineage
        calls = {"n": 0}

        def _failing_lineage(*args, **kwargs):
            calls["n"] += 1
            if calls["n"] == 3:  # 3rd lineage row (the output) -> fail
                raise RuntimeError("simulated lineage failure")
            return original_lineage(*args, **kwargs)

        repo.store_lineage = _failing_lineage  # type: ignore
        with pytest.raises(RuntimeError):
            svc.reconcile_official_pair(_company(), _exchange())
        conn = repo.store.connect()
        n = conn.execute(
            "SELECT COUNT(*) FROM financial_facts WHERE symbol = ?",
            [SYMBOL_A],
        ).fetchone()[0]
        assert n == 0  # transaction rolled back
        repo.store.close()

    def test_output_input_ids_must_match_actual_pair(self, tmp_path: Path):
        repo = _setup_repo(str(tmp_path / "wrong_inputs.duckdb"))
        engine = _OutputMutatingEngine(
            input_fact_ids="other_fact_a,other_fact_b",
            derived_from="other_fact_a,other_fact_b",
        )
        svc = OfficialFactReconciliationService(repo, engine=engine)
        _assert_prewrite_rejection(repo, svc)
        repo.store.close()

    def test_output_derived_from_must_match_input_ids(self, tmp_path: Path):
        repo = _setup_repo(str(tmp_path / "wrong_derived.duckdb"))
        engine = _OutputMutatingEngine(
            derived_from="other_fact_a,other_fact_b",
        )
        svc = OfficialFactReconciliationService(repo, engine=engine)
        _assert_prewrite_rejection(repo, svc)
        repo.store.close()

    def test_output_lineage_parents_must_match_input_ids(
        self, tmp_path: Path,
    ):
        repo = _setup_repo(str(tmp_path / "wrong_lineage.duckdb"))
        svc = _BadLineageService(repo)
        _assert_prewrite_rejection(repo, svc)
        repo.store.close()

    def test_lineage_roles_must_match_actual_fact_ids(self, tmp_path: Path):
        repo = _setup_repo(str(tmp_path / "swapped_roles.duckdb"))
        svc = _SwappedRoleLineageService(repo)
        _assert_prewrite_rejection(repo, svc)
        repo.store.close()

    @pytest.mark.parametrize(
        ("input_fact_ids", "derived_from"),
        [
            ("one_input_only", "one_input_only"),
            (
                "other_fact_a,other_fact_b,other_fact_c",
                "other_fact_a,other_fact_b,other_fact_c",
            ),
        ],
        ids=["missing_input", "extra_third_input"],
    )
    def test_output_must_reference_exactly_two_actual_inputs(
        self, tmp_path: Path, input_fact_ids: str, derived_from: str,
    ):
        repo = _setup_repo(
            str(tmp_path / f"{input_fact_ids[:5]}.duckdb")
        )
        engine = _OutputMutatingEngine(
            input_fact_ids=input_fact_ids,
            derived_from=derived_from,
        )
        svc = OfficialFactReconciliationService(repo, engine=engine)
        _assert_prewrite_rejection(repo, svc)
        repo.store.close()


class TestLineageSchemaV21Migration:
    def test_existing_schema_20_migrates_lineage_columns(
        self, tmp_path: Path,
    ):
        repo = _legacy_schema_20_repo(
            str(tmp_path / "migrate_columns.duckdb")
        )

        repo.ensure_schema()

        conn = repo.store.connect()
        columns = {
            row[1] for row in repo.store.connect().execute(
                "PRAGMA table_info('fact_lineage')"
            ).fetchall()
        }
        assert {
            "role",
            "reconciliation_rule_id",
            "reconciliation_rule_version",
        } <= columns
        assert conn.execute(
            "SELECT schema_version FROM fact_schema_meta"
        ).fetchone() == ("2.1",)
        assert conn.execute(
            """SELECT role, reconciliation_rule_id,
                      reconciliation_rule_version
               FROM fact_lineage"""
        ).fetchone() == ("", "", "")
        repo.store.close()

    def test_existing_schema_20_with_rows_preserves_data(
        self, tmp_path: Path,
    ):
        repo = _legacy_schema_20_repo(str(tmp_path / "migrate_rows.duckdb"))
        repo.ensure_schema()

        conn = repo.store.connect()
        assert conn.execute(
            "SELECT COUNT(*), MIN(value), MAX(value) FROM financial_facts"
        ).fetchone() == (1, 123456.0, 123456.0)
        assert conn.execute(
            "SELECT COUNT(*), MIN(fiscal_year) FROM fact_contexts"
        ).fetchone() == (1, 2024)
        assert conn.execute(
            "SELECT fact_id, run_id, source_provider FROM fact_lineage"
        ).fetchone() == (
            "legacy_fact", "legacy_run", "legacy_provider",
        )
        repo.store.close()

    def test_schema_version_is_bumped_for_lineage_change(
        self, tmp_path: Path,
    ):
        repo = _legacy_schema_20_repo(
            str(tmp_path / "schema_version.duckdb")
        )
        repo.ensure_schema()
        assert FactRepository.schema_version == "2.1"
        version = repo.store.connect().execute(
            "SELECT schema_version FROM fact_schema_meta "
            "WHERE schema_name = 'financial_facts'"
        ).fetchone()[0]
        assert version == "2.1"
        repo.store.close()

    def test_schema_20_migration_is_idempotent(self, tmp_path: Path):
        repo = _legacy_schema_20_repo(
            str(tmp_path / "migrate_idempotent.duckdb")
        )
        repo.ensure_schema()
        repo.ensure_schema()
        conn = repo.store.connect()
        assert conn.execute(
            "SELECT COUNT(*) FROM financial_facts"
        ).fetchone() == (1,)
        assert conn.execute(
            "SELECT COUNT(*) FROM fact_lineage"
        ).fetchone() == (1,)
        assert conn.execute(
            "SELECT schema_version FROM fact_schema_meta"
        ).fetchone() == ("2.1",)
        repo.store.close()

    def test_schema_20_migration_failure_rolls_back(self, tmp_path: Path):
        repo = _legacy_schema_20_repo(
            str(tmp_path / "migrate_rollback.duckdb")
        )
        failing_repo = _FailingMetaRepository(repo.store)

        with pytest.raises(Exception, match="metadata write failure"):
            failing_repo.ensure_schema()

        conn = repo.store.connect()
        columns = {
            row[1] for row in conn.execute(
                "PRAGMA table_info('fact_lineage')"
            ).fetchall()
        }
        assert "role" not in columns
        assert "reconciliation_rule_id" not in columns
        assert "reconciliation_rule_version" not in columns
        assert conn.execute(
            "SELECT schema_version FROM fact_schema_meta"
        ).fetchone() == ("2.0",)
        assert conn.execute(
            "SELECT COUNT(*) FROM financial_facts"
        ).fetchone() == (1,)
        assert conn.execute(
            "SELECT COUNT(*) FROM fact_lineage"
        ).fetchone() == (1,)
        repo.store.close()


# ── 4. Cross-unit comparison order ──────────────────────────────────


class TestCrossUnitComparison:
    def test_cny_and_yuan_match(self):
        eng = ReconciliationEngine()
        company = _company(unit="CNY", value=REVENUE_YUAN)
        exchange = _exchange(unit="元", value=REVENUE_YUAN)
        r = eng.reconcile_pair(company, exchange)
        assert r.status == ReconciliationStatus.matched

    def test_wan_yuan_matches_yuan_after_conversion(self):
        eng = ReconciliationEngine()
        company = _company(unit="万元", value=23_500.0)
        exchange = _exchange(unit="元", value=235_000_000.0)
        r = eng.reconcile_pair(company, exchange)
        assert r.status == ReconciliationStatus.matched

    def test_yi_yuan_matches_wan_yuan_after_conversion(self):
        eng = ReconciliationEngine()
        company = _company(unit="亿元", value=1.0)
        exchange = _exchange(unit="万元", value=10_000.0)
        r = eng.reconcile_pair(company, exchange)
        assert r.status == ReconciliationStatus.matched

    def test_cross_unit_mismatch_is_detected_after_conversion(self):
        eng = ReconciliationEngine()
        company = _company(unit="万元", value=23_500.0)
        exchange = _exchange(unit="元", value=236_000_000.0)  # 23_600 万元
        r = eng.reconcile_pair(company, exchange)
        assert r.status == ReconciliationStatus.mismatch
        assert r.output_fact is None

    def test_unsupported_unit_is_not_comparable(self):
        eng = ReconciliationEngine()
        company = _company(unit="SHARE", value=1_000.0)
        exchange = _exchange(unit="元", value=235_000_000.0)
        r = eng.reconcile_pair(company, exchange)
        assert r.status == ReconciliationStatus.not_comparable

    def test_unit_is_not_compared_before_normalization(self):
        """Different units (万元 vs 元) must NOT fail the identity gate;
        they are resolved by conversion and match when equal."""
        eng = ReconciliationEngine()
        company = _company(unit="万元", value=23_500.0)
        exchange = _exchange(unit="元", value=235_000_000.0)
        r = eng.reconcile_pair(company, exchange)
        assert r.status == ReconciliationStatus.matched
        assert "unit" not in r.decision_reason


# ── 5. v1 numeric storage semantics ──────────────────────────────────


class TestNumericStorageSemantics:
    def test_fractional_canonical_value_is_insufficient(self):
        eng = ReconciliationEngine()
        # 235_000_001 元 -> 23_500.0001 万元 (non-integral) -> insufficient
        company = _company(unit="元", value=235_000_001.0)
        exchange = _exchange(unit="元", value=235_000_000.0)
        r = eng.reconcile_pair(company, exchange)
        assert r.status == ReconciliationStatus.insufficient_evidence
        assert r.output_fact is None
        assert "integral" in r.decision_reason

    def test_unsafe_integer_range_is_insufficient(self):
        eng = ReconciliationEngine()
        # 1e16 万元 exceeds 2**53 - 1
        company = _company(unit="万元", value=1e16)
        exchange = _exchange(unit="万元", value=1e16)
        r = eng.reconcile_pair(company, exchange)
        assert r.status == ReconciliationStatus.insufficient_evidence
        assert r.output_fact is None
        assert "safe" in r.decision_reason

    def test_output_fact_does_not_use_float_conversion(self, tmp_path: Path):
        repo = _setup_repo(str(tmp_path / "nf.duckdb"))
        rec = _svc(repo).reconcile_official_pair(_company(), _exchange()).output_fact
        assert isinstance(rec["value"], int)
        assert not isinstance(rec["value"], float)
        assert isinstance(rec["raw_value"], int)
        assert isinstance(rec["normalized_value"], int)

    def test_output_fact_uses_integral_canonical_unit(self, tmp_path: Path):
        repo = _setup_repo(str(tmp_path / "iu.duckdb"))
        rec = _svc(repo).reconcile_official_pair(_company(), _exchange()).output_fact
        assert rec["unit"] == "万元"
        assert rec["raw_unit"] == "万元"
        assert rec["value"] == int(rec["value"])
        # 2.35e12 元 / 10000 == 235_000_000 万元
        assert rec["value"] == 235_000_000

    def test_decimal_comparison_does_not_use_math_isclose(self):
        import ashare_research.reconciliation.engine as eng_mod
        src = inspect.getsource(eng_mod)
        assert "math.isclose" not in src
        # the canonical value path must not coerce through float()
        assert "float(matched_value)" not in src

    def test_engine_does_not_use_math_isclose_import(self):
        import ashare_research.reconciliation.engine as eng_mod
        assert not hasattr(eng_mod, "math") or "isclose" not in dir(
            getattr(eng_mod, "math", object()),
        )


# ── 6. Symbol-agnostic source_id ────────────────────────────────────


class TestSymbolAgnosticSourceId:
    def test_source_id_does_not_contain_petrochina(self):
        sid = build_reconciliation_source_id(SYMBOL_A, RULE_ID, RULE_VERSION)
        assert "petrochina" not in sid.lower()
        assert sid == _expected_source_id(SYMBOL_A)

    def test_source_id_does_not_contain_sse(self):
        sid = build_reconciliation_source_id(SYMBOL_A, RULE_ID, RULE_VERSION)
        assert "sse" not in sid.lower()

    def test_source_id_changes_with_symbol(self):
        a = build_reconciliation_source_id(SYMBOL_A, RULE_ID, RULE_VERSION)
        b = build_reconciliation_source_id(SYMBOL_B, RULE_ID, RULE_VERSION)
        assert a != b
        assert SYMBOL_B in b

    def test_source_id_changes_with_rule_version(self):
        v1 = build_reconciliation_source_id(SYMBOL_A, RULE_ID, "1")
        v2 = build_reconciliation_source_id(SYMBOL_A, RULE_ID, "2")
        assert v1 != v2

    def test_source_id_is_stable(self):
        a = build_reconciliation_source_id(SYMBOL_A, RULE_ID, RULE_VERSION)
        b = build_reconciliation_source_id(SYMBOL_A, RULE_ID, RULE_VERSION)
        assert a == b

    def test_second_symbol_uses_same_engine_without_new_module(
        self, tmp_path: Path,
    ):
        repo = _setup_repo(str(tmp_path / "sb.duckdb"), symbol=SYMBOL_B)
        company = _company(SYMBOL_B)
        exchange = _exchange(SYMBOL_B)
        result = _svc(repo).reconcile_official_pair(company, exchange)
        assert result.status == ReconciliationStatus.matched
        rec = result.output_fact
        assert rec["source_id"] == _expected_source_id(SYMBOL_B)
        assert SYMBOL_B in rec["source_id"]
        # the engine module has no petrochina / 601857 / sse literals
        import ashare_research.reconciliation.engine as eng_mod
        src = inspect.getsource(eng_mod)
        assert "petrochina" not in src.lower()
        assert "601857" not in src
        repo.store.close()


# ── 7. Revalidation & query ─────────────────────────────────────────


class TestRevalidationAndQuery:
    def _reconciled(self, tmp_path: Path):
        repo = _setup_repo(str(tmp_path / "rv.duckdb"))
        company = _company()
        exchange = _exchange()
        result = _svc(repo).reconcile_official_pair(company, exchange)
        return repo, company, exchange, result

    def test_reconciled_fact_passes_full_fact_validator(self, tmp_path: Path):
        repo, company, exchange, result = self._reconciled(tmp_path)
        rec = result.output_fact
        results = FactValidator().validate_single_fact(rec)
        errors = [r for r in results if r.severity == "error" and not r.passed]
        assert errors == [], errors

    def test_verify_run_accepts_reconciled_derived_fact(self, tmp_path: Path):
        repo, company, exchange, result = self._reconciled(tmp_path)
        conn = repo.store.connect()
        facts_df = conn.execute(
            "SELECT * FROM financial_facts WHERE symbol = ?", [SYMBOL_A],
        ).df()
        facts = facts_df.to_dict("records")
        results = FactValidator().validate_batch(facts)
        errors = [r for r in results if r.severity == "error" and not r.passed]
        assert errors == [], errors
        # specifically no FACT_SOURCE_001 error on the reconciled fact
        rec_errors = [
            r for r in results
            if r.rule_id == "FACT_SOURCE_001"
            and r.target_id == result.output_fact["fact_id"]
            and not r.passed
        ]
        assert rec_errors == []
        repo.store.close()

    def test_default_pit_returns_only_reconciled_fact(self, tmp_path: Path):
        repo, company, exchange, result = self._reconciled(tmp_path)
        df = AsOfQuery(repo).get_latest_available(SYMBOL_A, "2025-04-01")
        assert len(df) == 1
        assert df.iloc[0]["fact_id"] == result.output_fact["fact_id"]
        assert df.iloc[0]["verification_status"] == "reconciled"
        repo.store.close()

    def test_audit_query_returns_all_three_facts(self, tmp_path: Path):
        repo, company, exchange, result = self._reconciled(tmp_path)
        df = repo.get_all_versions_for_audit(SYMBOL_A)
        assert len(df) == 3
        fids = set(df["fact_id"].tolist())
        assert fids == {
            company["fact_id"], exchange["fact_id"],
            result.output_fact["fact_id"],
        }
        repo.store.close()


# ── 8. Lineage roles ────────────────────────────────────────────────


class TestLineageRoles:
    def _reconciled(self, tmp_path: Path):
        repo = _setup_repo(str(tmp_path / "lr.duckdb"))
        company = _company()
        exchange = _exchange()
        result = _svc(repo).reconcile_official_pair(company, exchange)
        return repo, company, exchange, result

    def test_reconciled_input_ids_match_persisted_inputs(self, tmp_path: Path):
        repo, company, exchange, result = self._reconciled(tmp_path)
        conn = repo.store.connect()
        row = conn.execute(
            "SELECT input_fact_ids FROM financial_facts WHERE fact_id = ?",
            [result.output_fact["fact_id"]],
        ).fetchone()
        stored = {s for s in row[0].split(",") if s}
        assert stored == {company["fact_id"], exchange["fact_id"]}
        repo.store.close()

    def test_lineage_distinguishes_company_and_exchange_inputs(
        self, tmp_path: Path,
    ):
        repo, company, exchange, result = self._reconciled(tmp_path)
        conn = repo.store.connect()
        rows = conn.execute(
            "SELECT fact_id, role, source_tier FROM fact_lineage "
            "WHERE run_id LIKE 'recon_%' ORDER BY role",
        ).fetchall()
        roles = {r[1] for r in rows}
        assert roles == {
            "reconciliation_input_company",
            "reconciliation_input_exchange",
            "reconciliation_output",
        }
        by_role = {r[1]: (r[0], r[2]) for r in rows}
        assert by_role["reconciliation_input_company"][0] == company["fact_id"]
        assert by_role["reconciliation_input_company"][1] == "company_official"
        assert by_role["reconciliation_input_exchange"][0] == exchange["fact_id"]
        assert by_role["reconciliation_input_exchange"][1] == "exchange_official"
        assert by_role["reconciliation_output"][0] == result.output_fact["fact_id"]
        assert by_role["reconciliation_output"][1] == "reconciled_derived"
        repo.store.close()

    def test_candidate_fact_cannot_appear_in_reconciliation_lineage(
        self, tmp_path: Path,
    ):
        repo, company, exchange, result = self._reconciled(tmp_path)
        conn = repo.store.connect()
        rows = conn.execute(
            "SELECT DISTINCT source_tier FROM fact_lineage "
            "WHERE run_id LIKE 'recon_%'",
        ).fetchall()
        tiers = {r[0] for r in rows}
        assert "candidate_aggregator" not in tiers
        repo.store.close()

    def test_reconciliation_rule_version_is_recorded_in_lineage(
        self, tmp_path: Path,
    ):
        repo, company, exchange, result = self._reconciled(tmp_path)
        conn = repo.store.connect()
        rows = conn.execute(
            "SELECT reconciliation_rule_id, reconciliation_rule_version "
            "FROM fact_lineage WHERE run_id LIKE 'recon_%'",
        ).fetchall()
        assert rows
        for rule_id, rule_ver in rows:
            assert rule_id == RULE_ID
            assert rule_ver == RULE_VERSION
        repo.store.close()


# ── 9. Idempotency ──────────────────────────────────────────────────


class TestIdempotencyClosure:
    def test_reconciliation_repeat_is_unchanged(self, tmp_path: Path):
        repo = _setup_repo(str(tmp_path / "ic.duckdb"))
        svc = _svc(repo)
        r1 = svc.reconcile_official_pair(_company(), _exchange())
        r2 = svc.reconcile_official_pair(_company(), _exchange())
        assert r1.output_fact["fact_id"] == r2.output_fact["fact_id"]
        conn = repo.store.connect()
        n = conn.execute(
            "SELECT COUNT(*) FROM financial_facts WHERE symbol = ?",
            [SYMBOL_A],
        ).fetchone()[0]
        assert n == 3  # no duplicate fact rows
        repo.store.close()

    def test_changed_reconciled_payload_conflicts(self, tmp_path: Path):
        repo = _setup_repo(str(tmp_path / "cf.duckdb"))
        svc = _svc(repo)
        a = _company(value=1.0e11, source_id="company_A")
        b = _exchange(value=1.0e11, source_id="exchange_A")
        svc.reconcile_official_pair(a, b)
        c = _company(value=2.0e11, source_id="company_B")
        d = _exchange(value=2.0e11, source_id="exchange_B")
        with pytest.raises(FactVersionConflictError):
            svc.reconcile_official_pair(c, d)
        repo.store.close()

    def test_reconciliation_lineage_is_idempotent_per_run(self, tmp_path: Path):
        repo = _setup_repo(str(tmp_path / "lp.duckdb"))
        svc = _svc(repo)
        svc.reconcile_official_pair(_company(), _exchange())
        conn = repo.store.connect()
        run_ids = [
            r[0] for r in conn.execute(
                "SELECT DISTINCT run_id FROM fact_lineage "
                "WHERE run_id LIKE 'recon_%'",
            ).fetchall()
        ]
        assert len(run_ids) == 1  # exactly one run from one call
        per_run = conn.execute(
            "SELECT COUNT(*) FROM fact_lineage WHERE run_id = ?", [run_ids[0]],
        ).fetchone()[0]
        assert per_run == 3  # 3 rows per run, not duplicated
        repo.store.close()

    def test_second_run_creates_new_lineage_without_new_fact_row(
        self, tmp_path: Path,
    ):
        repo = _setup_repo(str(tmp_path / "sr.duckdb"))
        svc = _svc(repo)
        svc.reconcile_official_pair(_company(), _exchange())
        svc.reconcile_official_pair(_company(), _exchange())
        conn = repo.store.connect()
        facts = conn.execute(
            "SELECT COUNT(*) FROM financial_facts WHERE symbol = ?",
            [SYMBOL_A],
        ).fetchone()[0]
        lineage = conn.execute(
            "SELECT COUNT(*) FROM fact_lineage WHERE run_id LIKE 'recon_%'",
        ).fetchone()[0]
        runs = conn.execute(
            "SELECT COUNT(DISTINCT run_id) FROM fact_lineage "
            "WHERE run_id LIKE 'recon_%'",
        ).fetchone()[0]
        assert facts == 3       # facts idempotent
        assert lineage == 6    # two runs, 3 rows each
        assert runs == 2
        repo.store.close()
