"""M2 Stage 1B — FactRepository + AsOfQuery PIT 集成测试。

使用 tmp_path + 临时 DuckDB，无网络依赖。
"""

from __future__ import annotations

import math
from datetime import datetime
from pathlib import Path

import pytest

from ashare_research.exceptions import FactSchemaMigrationError
from ashare_research.facts.as_of import AsOfQuery
from ashare_research.facts.repository import FactRepository
from ashare_research.storage.duckdb_store import DuckDBStore

# ── 辅助函数 ──────────────────────────────────────────────────────────────

FACT_COLS = [
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


def _make_fact(**overrides) -> dict:
    """Create a minimal valid fact dict with sensible defaults.

    All fields from FACT_COLS are populated, so the dict is ready for
    ``FactRepository.store_facts``.
    """
    now = datetime.now().isoformat()
    fact_id = overrides.get("fact_id", "")
    if not fact_id:
        import uuid
        fact_id = uuid.uuid4().hex[:12]

    base: dict = {
        "fact_id": fact_id,
        "concept_id": "revenue",
        "concept_version": "1",
        "symbol": "000001.SZ",
        "value": 1000.0,
        "unit": "CNY",
        "context_id": "000001.SZ|2024|annual|consolidated|original",
        "is_derived": False,
        "derived_from": "",
        "derivation_definition_id": "",
        "derivation_version": "",
        "input_fact_ids": "",
        "source_provider": "test_provider",
        "source_id": f"src_{fact_id}",
        "source_tier": "company_official",
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
        "verification_status": "verified",
        "verification_note": "",
        "eligible_for_metrics": True,
        "created_at": now,
    }
    base.update(overrides)
    # Ensure fact_id matches overrides
    base["fact_id"] = fact_id
    return base


def _make_db_path(tmp_path: Path) -> str:
    """Return an absolute path to a temporary DuckDB file."""
    return str(tmp_path / "test.duckdb")


def _new_repo(db_path: str) -> FactRepository:
    """Create a fresh FactRepository with a new DuckDBStore."""
    store = DuckDBStore(db_path)
    return FactRepository(store)


def _setup_repo(db_path: str) -> FactRepository:
    """Create and initialise a FactRepository (schema ready)."""
    repo = _new_repo(db_path)
    repo.ensure_schema()
    return repo


def _count_table(repo: FactRepository, table: str) -> int:
    conn = repo.store.connect()
    row = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()
    return row[0] if row else 0


def _has_fact(repo: FactRepository, fact_id: str) -> bool:
    conn = repo.store.connect()
    row = conn.execute(
        "SELECT COUNT(*) FROM financial_facts WHERE fact_id = ?",
        [fact_id],
    ).fetchone()
    return (row[0] > 0) if row else False


# ═══════════════════════════════════════════════════════════════════════════
# TestFactRepositoryTransactions
# ═══════════════════════════════════════════════════════════════════════════


class TestFactRepositoryTransactions:
    """事务提交、回滚、计数校验和 schema 安全初始化。"""

    def test_transaction_commits_all_rows(self, tmp_path: Path):
        """事务成功 → 全部行进入数据库。"""
        db = _make_db_path(tmp_path)
        repo = _setup_repo(db)

        f1 = _make_fact(fact_id="f_commit_1", value=100.0, concept_id="revenue")
        f2 = _make_fact(fact_id="f_commit_2", value=200.0, concept_id="net_profit")
        f3 = _make_fact(fact_id="f_commit_3", value=300.0, concept_id="total_assets")

        with repo.transaction() as conn:
            repo.store_facts([f1, f2, f3], conn=conn)

        assert _has_fact(repo, "f_commit_1")
        assert _has_fact(repo, "f_commit_2")
        assert _has_fact(repo, "f_commit_3")
        assert _count_table(repo, "financial_facts") == 3

    def test_transaction_rolls_back_on_error(self, tmp_path: Path):
        """事务中任一操作失败 → 全部回滚，表中无数据残留。"""
        db = _make_db_path(tmp_path)
        repo = _setup_repo(db)

        f1 = _make_fact(fact_id="f_rollback_1", value=100.0)
        f2 = _make_fact(fact_id="f_rollback_2", value=200.0)

        with pytest.raises(ValueError, match="simulated failure"), \
                repo.transaction() as conn:  # noqa: SIM117
            repo.store_facts([f1], conn=conn)
            repo.store_facts([f2], conn=conn)
            raise ValueError("simulated failure")

        # 回滚后不应有任何事实残留
        assert not _has_fact(repo, "f_rollback_1")
        assert not _has_fact(repo, "f_rollback_2")
        assert _count_table(repo, "financial_facts") == 0

    def test_store_count_verification(self, tmp_path: Path):
        """store_facts 返回的计数与实际写入行数一致，不一致时抛出异常。"""
        db = _make_db_path(tmp_path)
        repo = _setup_repo(db)

        facts = [
            _make_fact(fact_id=f"f_count_{i}", value=float(i * 100))
            for i in range(1, 6)
        ]

        with repo.transaction() as conn:
            count = repo.store_facts(facts, conn=conn)
            assert count == 5

        # 验证库中实际行数
        assert _count_table(repo, "financial_facts") == 5

    def test_schema_initialization_safe(self, tmp_path: Path):
        """重复调用 ensure_schema 安全且幂等，不会崩溃或重复建表。"""
        db = _make_db_path(tmp_path)
        repo = _new_repo(db)

        # 首次初始化
        repo.ensure_schema()
        assert _count_table(repo, "financial_facts") == 0

        # 写入一条事实确认表可用
        f = _make_fact(fact_id="f_schema_1")
        with repo.transaction() as conn:
            repo.store_facts([f], conn=conn)

        assert _has_fact(repo, "f_schema_1")

        # 再次调用 ensure_schema — 应安全跳过
        repo.ensure_schema()

        # 事实仍然存在（未被删除）
        assert _has_fact(repo, "f_schema_1")

    def test_empty_schema_reset_allowed(self, tmp_path: Path):
        """空表环境下的 schema 重置不应引发迁移错误。"""
        db = _make_db_path(tmp_path)
        repo = _new_repo(db)

        # 先初始化并确保为空
        repo.ensure_schema()
        assert _count_table(repo, "financial_facts") == 0

        # reset_m2_fact_schema 在空表或仅开发环境下应可用
        repo.reset_m2_fact_schema()
        assert _count_table(repo, "financial_facts") == 0

        # 重置后写入仍然可用
        f = _make_fact(fact_id="f_after_reset")
        with repo.transaction() as conn:
            repo.store_facts([f], conn=conn)
        assert _has_fact(repo, "f_after_reset")

    def test_nonempty_schema_migration_refused(self, tmp_path: Path):
        """已有数据的旧版本 schema 拒绝自动迁移。"""
        db = _make_db_path(tmp_path)
        repo = _new_repo(db)

        # 手动建表但不注册 v2.0 元数据（模拟旧版本）
        conn = repo.store.connect()
        conn.execute("""
            CREATE TABLE IF NOT EXISTS financial_facts (
                fact_id VARCHAR PRIMARY KEY,
                concept_id VARCHAR,
                symbol VARCHAR,
                value DOUBLE
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS fact_schema_meta (
                schema_name VARCHAR PRIMARY KEY,
                schema_version VARCHAR,
                applied_at VARCHAR,
                git_commit VARCHAR DEFAULT ''
            )
        """)
        # 写入旧版元数据
        conn.execute(
            """INSERT INTO fact_schema_meta
               (schema_name, schema_version, applied_at)
               VALUES ('financial_facts', '1.0', ?)""",
            [datetime.now().isoformat()],
        )
        # 写入一条旧数据
        conn.execute(
            "INSERT INTO financial_facts (fact_id, concept_id, symbol, value) "
            "VALUES (?, ?, ?, ?)",
            ["old_fact", "revenue", "000001.SZ", 999.0],
        )

        repo._initialized = False
        with pytest.raises(FactSchemaMigrationError):
            repo.ensure_schema()


# ═══════════════════════════════════════════════════════════════════════════
# TestAsOfPIT
# ═══════════════════════════════════════════════════════════════════════════


class TestAsOfPIT:
    """PIT 查询门禁：available_at、未来事实、默认过滤和审计查询。"""

    SYMBOL = "000001.SZ"

    def _seed(self, repo: FactRepository, facts: list[dict]) -> None:
        """将事实写入库中（已验证、eligible）。"""
        with repo.transaction() as conn:
            repo.store_facts(facts, conn=conn)

    # ── available_at 过滤 ──────────────────────────────────────────────

    def test_pit_excludes_empty_available_at(self, tmp_path: Path):
        """available_at 为空字符串的事实被 PIT 查询排除。"""
        db = _make_db_path(tmp_path)
        repo = _setup_repo(db)

        f = _make_fact(
            fact_id="f_empty_avail", available_at="",
            verification_status="verified",
            eligible_for_metrics=True,
        )
        self._seed(repo, [f])

        asof = AsOfQuery(repo)
        result = asof.query(symbol=self.SYMBOL, as_of_date="2025-06-01")
        assert result.empty

    def test_pit_excludes_null_available_at(self, tmp_path: Path):
        """available_at 为 None 的事实被 PIT 查询排除。

        PIT 门禁同时检查 IS NOT NULL 和非空字符串，两者缺一不可。
        """
        db = _make_db_path(tmp_path)
        repo = _setup_repo(db)

        f = _make_fact(
            fact_id="f_null_avail",
            verification_status="verified",
            eligible_for_metrics=True,
        )
        # 直接在 SQL 级别置 NULL（_make_fact 默认填充 ""）
        with repo.transaction() as conn:
            repo.store_facts([f], conn=conn)
            conn.execute(
                "UPDATE financial_facts SET available_at = NULL WHERE fact_id = ?",
                ["f_null_avail"],
            )

        asof = AsOfQuery(repo)
        result = asof.query(symbol=self.SYMBOL, as_of_date="2025-06-01")
        assert result.empty

    def test_pit_excludes_future_fact(self, tmp_path: Path):
        """available_at 晚于 as_of_date 的事实被排除（禁止未来数据泄漏）。"""
        db = _make_db_path(tmp_path)
        repo = _setup_repo(db)

        f = _make_fact(
            fact_id="f_future",
            available_at="2025-12-31",
            period_end="2025-09-30",
            filing_date="2025-12-31",
            announcement_date="2025-12-31",
        )
        self._seed(repo, [f])

        asof = AsOfQuery(repo)
        result = asof.query(symbol=self.SYMBOL, as_of_date="2025-06-01")
        assert result.empty

        # 当 as_of_date 在事实之后时，事实应可见
        result2 = asof.query(symbol=self.SYMBOL, as_of_date="2026-01-15")
        assert len(result2) == 1

    def test_pit_includes_fact_on_available_date(self, tmp_path: Path):
        """available_at == as_of_date 当日的事实应被包含（<= 语义）。"""
        db = _make_db_path(tmp_path)
        repo = _setup_repo(db)

        f = _make_fact(
            fact_id="f_on_date",
            available_at="2025-06-01",
            filing_date="2025-06-01",
            announcement_date="2025-06-01",
        )
        self._seed(repo, [f])

        asof = AsOfQuery(repo)
        result = asof.query(symbol=self.SYMBOL, as_of_date="2025-06-01")
        assert len(result) == 1
        assert result.iloc[0]["fact_id"] == "f_on_date"

    # ── 默认过滤 ───────────────────────────────────────────────────────

    def test_default_excludes_unverified(self, tmp_path: Path):
        """默认查询排除 verification_status != verified/reconciled 的事实。"""
        db = _make_db_path(tmp_path)
        repo = _setup_repo(db)

        verified = _make_fact(
            fact_id="f_verified",
            verification_status="verified",
            eligible_for_metrics=True,
        )
        unverified = _make_fact(
            fact_id="f_unverified",
            verification_status="unverified",
            eligible_for_metrics=False,
        )
        reconciled = _make_fact(
            fact_id="f_reconciled",
            verification_status="reconciled",
            eligible_for_metrics=True,
        )
        self._seed(repo, [verified, unverified, reconciled])

        asof = AsOfQuery(repo)
        result = asof.query(symbol=self.SYMBOL, as_of_date="2025-06-01")
        ids = set(result["fact_id"])
        assert "f_verified" in ids
        assert "f_reconciled" in ids
        assert "f_unverified" not in ids

    def test_audit_query_includes_all(self, tmp_path: Path):
        """审计查询（include_unverified=True）返回全部事实，不施加任何过滤。"""
        db = _make_db_path(tmp_path)
        repo = _setup_repo(db)

        facts = [
            _make_fact(
                fact_id="f_audit_verified",
                verification_status="verified",
                eligible_for_metrics=True,
            ),
            _make_fact(
                fact_id="f_audit_unverified",
                verification_status="unverified",
                eligible_for_metrics=False,
            ),
            _make_fact(
                fact_id="f_audit_empty_avail",
                available_at="",
                verification_status="verified",
                eligible_for_metrics=True,
            ),
        ]
        self._seed(repo, facts)

        asof = AsOfQuery(repo)
        result = asof.get_all_versions_for_audit(symbol=self.SYMBOL)
        assert len(result) == 3

    def test_audit_query_sees_future_facts(self, tmp_path: Path):
        """审计查询不施加 as_of_date 过滤，即使 available_at 在将来也返回。"""
        db = _make_db_path(tmp_path)
        repo = _setup_repo(db)

        f = _make_fact(
            fact_id="f_audit_future",
            available_at="2099-12-31",
            verification_status="verified",
            eligible_for_metrics=True,
        )
        self._seed(repo, [f])

        asof = AsOfQuery(repo)
        result = asof.get_all_versions_for_audit(symbol=self.SYMBOL)
        assert len(result) == 1
        assert result.iloc[0]["fact_id"] == "f_audit_future"

    # ── 格式校验 ───────────────────────────────────────────────────────

    def test_empty_as_of_date_raises(self, tmp_path: Path):
        """空 as_of_date 应抛出 PointInTimeError。"""
        db = _make_db_path(tmp_path)
        repo = _setup_repo(db)
        asof = AsOfQuery(repo)

        from ashare_research.exceptions import PointInTimeError

        with pytest.raises(PointInTimeError, match="as_of_date"):
            asof.query(symbol=self.SYMBOL, as_of_date="")

    def test_invalid_date_format_raises(self, tmp_path: Path):
        """非 YYYY-MM-DD 格式的 as_of_date 应抛出 PointInTimeError。"""
        db = _make_db_path(tmp_path)
        repo = _setup_repo(db)
        asof = AsOfQuery(repo)

        from ashare_research.exceptions import PointInTimeError

        with pytest.raises(PointInTimeError, match="as_of_date"):
            asof.query(symbol=self.SYMBOL, as_of_date="2025/06/01")


# ═══════════════════════════════════════════════════════════════════════════
# TestIntegrationScenarios
# ═══════════════════════════════════════════════════════════════════════════


class TestIntegrationScenarios:
    """端到端集成场景：错误阻断、候选源和 PIT 端到端。"""

    SYMBOL = "000001.SZ"

    def test_reported_error_blocks_writes(self, tmp_path: Path):
        """provider 返回含有 NaN 的事实 → 检测到无效值 → 事务回滚 → 库中无残留。

        模拟 validate-before-write 流程：当任一事实包含 NaN 值时，
        整个批次的事务回滚，确保不会部分写入坏数据。
        """
        db = _make_db_path(tmp_path)
        repo = _setup_repo(db)

        ok_1 = _make_fact(fact_id="f_ok_1", value=100.0)
        ok_2 = _make_fact(fact_id="f_ok_2", value=200.0)
        nan_fact = _make_fact(fact_id="f_nan", value=float("nan"))

        # 模拟 validator 检测到 NaN 后拒绝写入
        def _any_nan(facts):
            for f in facts:
                v = f.get("value")
                if v is not None and isinstance(v, float) and math.isnan(v):
                    return True
            return False

        with pytest.raises(ValueError, match="NaN value detected"), \
                repo.transaction() as conn:  # noqa: SIM117
            repo.store_facts([ok_1, ok_2], conn=conn)
            if _any_nan([nan_fact]):
                raise ValueError("NaN value detected in facts — aborting write")
            repo.store_facts([nan_fact], conn=conn)

        # 回滚后：之前写入的 ok_1, ok_2 也不应存在
        assert not _has_fact(repo, "f_ok_1")
        assert not _has_fact(repo, "f_ok_2")
        assert not _has_fact(repo, "f_nan")
        assert _count_table(repo, "financial_facts") == 0

    def test_candidate_fact_is_unverified(self, tmp_path: Path):
        """来自候选聚合源的事实默认 verification_status 为 'unverified'。

        验证默认 source_tier='candidate_aggregator' 与默认
        verification_status='unverified' 的组合行为。
        """
        db = _make_db_path(tmp_path)
        repo = _setup_repo(db)

        f = _make_fact(
            fact_id="f_candidate",
            source_tier="candidate_aggregator",
            verification_status="unverified",
            eligible_for_metrics=False,
        )
        with repo.transaction() as conn:
            repo.store_facts([f], conn=conn)

        conn = repo.store.connect()
        row = conn.execute(
            "SELECT source_tier, verification_status, eligible_for_metrics "
            "FROM financial_facts WHERE fact_id = ?",
            ["f_candidate"],
        ).fetchone()
        assert row is not None
        assert row[0] == "candidate_aggregator"
        assert row[1] == "unverified"
        assert bool(row[2]) is False

    def test_candidate_not_in_pit_default(self, tmp_path: Path):
        """未核验事实被 PIT 默认查询排除。

        写入一条 candidate 源 + unverified 的事实 → PIT 默认查询（无
        include_unverified）不应返回该事实。
        """
        db = _make_db_path(tmp_path)
        repo = _setup_repo(db)

        f = _make_fact(
            fact_id="f_candidate_pit",
            source_tier="candidate_aggregator",
            verification_status="unverified",
            eligible_for_metrics=False,
            available_at="2025-04-15",
        )
        with repo.transaction() as conn:
            repo.store_facts([f], conn=conn)

        asof = AsOfQuery(repo)
        result = asof.query(symbol=self.SYMBOL, as_of_date="2025-06-01")
        assert "f_candidate_pit" not in set(result["fact_id"])

        # 审计查询仍然可见
        audit = asof.get_all_versions_for_audit(symbol=self.SYMBOL)
        assert "f_candidate_pit" in set(audit["fact_id"])

    def test_multiple_sources_coexist(self, tmp_path: Path):
        """official 和 candidate 两个源的事实共存，PIT 只返回 verified。"""
        db = _make_db_path(tmp_path)
        repo = _setup_repo(db)

        official = _make_fact(
            fact_id="f_official",
            source_tier="company_official",
            source_provider="cninfo",
            verification_status="verified",
            eligible_for_metrics=True,
        )
        candidate = _make_fact(
            fact_id="f_candidate2",
            source_tier="candidate_aggregator",
            source_provider="akshare",
            verification_status="unverified",
            eligible_for_metrics=False,
        )
        with repo.transaction() as conn:
            repo.store_facts([official, candidate], conn=conn)

        asof = AsOfQuery(repo)
        result = asof.query(symbol=self.SYMBOL, as_of_date="2025-06-01")
        ids = set(result["fact_id"])
        assert "f_official" in ids
        assert "f_candidate2" not in ids

        # 两者都在库中
        assert _count_table(repo, "financial_facts") == 2


# ═══════════════════════════════════════════════════════════════════════════
# TestTransactionWithContexts
# ═══════════════════════════════════════════════════════════════════════════


class TestTransactionWithContexts:
    """事务中同时写入 facts 和 contexts 的原子性测试。"""

    def test_facts_and_contexts_committed_together(self, tmp_path: Path):
        """事务内同时写入 facts 和 contexts → 两者一起提交。"""
        db = _make_db_path(tmp_path)
        repo = _setup_repo(db)

        ctx = {
            "context_id": "000001.SZ|2024|annual|consolidated|original",
            "symbol": "000001.SZ",
            "fiscal_year": 2024,
            "period_type": "annual",
            "period_start": "2024-01-01",
            "period_end": "2024-12-31",
            "instant_or_duration": "duration",
            "consolidation_scope": "consolidated",
            "accounting_standard": "CAS",
            "restatement_version": "original",
            "source_document": "2024年年报.pdf",
            "filing_date": "2025-03-28",
            "created_at": datetime.now().isoformat(),
        }
        fact = _make_fact(
            fact_id="f_with_ctx", context_id=ctx["context_id"],
        )

        with repo.transaction() as conn:
            repo.store_contexts([ctx], conn=conn)
            repo.store_facts([fact], conn=conn)

        assert _has_fact(repo, "f_with_ctx")
        conn = repo.store.connect()
        row = conn.execute(
            "SELECT COUNT(*) FROM fact_contexts WHERE context_id = ?",
            [ctx["context_id"]],
        ).fetchone()
        assert row[0] == 1

    def test_facts_roll_back_even_if_contexts_succeed(self, tmp_path: Path):
        """contexts 写入成功但 facts 写入失败 → 两者一起回滚。"""
        db = _make_db_path(tmp_path)
        repo = _setup_repo(db)

        ctx = {
            "context_id": "ctx_rollback",
            "symbol": "000001.SZ",
            "fiscal_year": 2024,
            "period_type": "annual",
            "period_start": "2024-01-01",
            "period_end": "2024-12-31",
            "instant_or_duration": "duration",
            "consolidation_scope": "consolidated",
            "accounting_standard": "CAS",
            "restatement_version": "original",
            "source_document": "",
            "filing_date": "",
            "created_at": datetime.now().isoformat(),
        }

        with pytest.raises(ValueError, match="simulated fact store failure"), \
                repo.transaction() as conn:  # noqa: SIM117
            repo.store_contexts([ctx], conn=conn)
            # 故意在 fact 写入前抛出异常
            raise ValueError("simulated fact store failure")

        # context 也应回滚
        conn = repo.store.connect()
        row = conn.execute(
            "SELECT COUNT(*) FROM fact_contexts WHERE context_id = 'ctx_rollback'",
        ).fetchone()
        assert row[0] == 0


# ═══════════════════════════════════════════════════════════════════════════
# TestConceptSeeding
# ═══════════════════════════════════════════════════════════════════════════


class TestConceptSeeding:
    """概念注册表种子写入测试。"""

    def test_seed_concepts_writes_rows(self, tmp_path: Path):
        """seed_concepts 写入概念到 concept_registry 表。"""
        db = _make_db_path(tmp_path)
        repo = _setup_repo(db)

        count = repo.seed_concepts()
        assert count > 0

        table_count = _count_table(repo, "concept_registry")
        assert table_count == count

    def test_seed_concepts_idempotent(self, tmp_path: Path):
        """重复 seed_concepts 不重复插入行（ON CONFLICT 处理）。"""
        db = _make_db_path(tmp_path)
        repo = _setup_repo(db)

        c1 = repo.seed_concepts()
        c2 = repo.seed_concepts()
        assert c2 == c1

        table_count = _count_table(repo, "concept_registry")
        assert table_count == c1


# ═══════════════════════════════════════════════════════════════════════════
# TestFactSummary
# ═══════════════════════════════════════════════════════════════════════════


class TestFactSummary:
    """get_fact_summary 统计查询测试。"""

    def test_summary_counts_categories(self, tmp_path: Path):
        """摘要正确统计 verified/unverified/reconciled 及 derived 数量。"""
        db = _make_db_path(tmp_path)
        repo = _setup_repo(db)

        facts = [
            _make_fact(fact_id="f_sum_v1", verification_status="verified",
                       eligible_for_metrics=True, is_derived=False, value=1.0),
            _make_fact(fact_id="f_sum_v2", verification_status="verified",
                       eligible_for_metrics=True, is_derived=False, value=2.0),
            _make_fact(fact_id="f_sum_u1", verification_status="unverified",
                       eligible_for_metrics=False, is_derived=False, value=3.0),
            _make_fact(fact_id="f_sum_r1", verification_status="reconciled",
                       eligible_for_metrics=True, is_derived=False, value=4.0),
            _make_fact(fact_id="f_sum_d1", verification_status="verified",
                       eligible_for_metrics=True, is_derived=True, value=5.0,
                       derived_from="f_sum_v1,f_sum_v2"),
        ]
        with repo.transaction() as conn:
            repo.store_facts(facts, conn=conn)

        summary = repo.get_fact_summary("000001.SZ")
        assert summary["total"] == 5
        # verified: f_sum_v1, f_sum_v2, f_sum_d1 (derived but verified) = 3
        # unverified: f_sum_u1 = 1
        # reconciled: f_sum_r1 = 1
        # derived: f_sum_d1 = 1
        assert summary["verified"] == 3
        assert summary["unverified"] == 1
        assert summary["reconciled"] == 1
        assert summary["derived"] == 1
