"""M2 Stage 1B — FactRepository: 事务化 DuckDB 事实存储。

关键变更：
- 事务化写入（全部成功或全部回滚）
- 不再静默吞掉异常
- PIT 查询强制排除空 available_at
- Schema v2.0 + migration safety
"""

from __future__ import annotations

import contextlib
import logging
from datetime import datetime
from typing import Any

import pandas as pd

from ashare_research.exceptions import (
    FactPersistenceError,
    FactSchemaMigrationError,
)
from ashare_research.storage.duckdb_store import DuckDBStore

logger = logging.getLogger(__name__)

FACT_SCHEMA_V2_SQL = """
CREATE TABLE IF NOT EXISTS fact_schema_meta (
    schema_name VARCHAR PRIMARY KEY,
    schema_version VARCHAR NOT NULL,
    applied_at VARCHAR NOT NULL,
    git_commit VARCHAR DEFAULT ''
);

CREATE TABLE IF NOT EXISTS financial_facts (
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

CREATE TABLE IF NOT EXISTS fact_contexts (
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

CREATE TABLE IF NOT EXISTS concept_registry (
    concept_id VARCHAR NOT NULL,
    version VARCHAR NOT NULL DEFAULT '1',
    display_name VARCHAR NOT NULL DEFAULT '',
    display_name_zh VARCHAR DEFAULT '',
    description VARCHAR DEFAULT '',
    parent_concept_id VARCHAR DEFAULT '',
    category VARCHAR NOT NULL DEFAULT '',
    statement_type VARCHAR DEFAULT '',
    instant_or_duration VARCHAR DEFAULT 'duration',
    canonical_unit VARCHAR DEFAULT '',
    created_at VARCHAR NOT NULL DEFAULT '',
    PRIMARY KEY (concept_id, version)
);

CREATE TABLE IF NOT EXISTS fact_lineage (
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

CREATE SEQUENCE IF NOT EXISTS fact_lineage_seq START 1;

CREATE TABLE IF NOT EXISTS fact_validation_runs (
    validation_run_id VARCHAR PRIMARY KEY,
    started_at VARCHAR NOT NULL,
    completed_at VARCHAR DEFAULT '',
    fact_count INTEGER DEFAULT 0,
    error_count INTEGER DEFAULT 0,
    warning_count INTEGER DEFAULT 0,
    status VARCHAR DEFAULT 'pending'
);

CREATE TABLE IF NOT EXISTS fact_validation_results (
    id INTEGER PRIMARY KEY,
    validation_run_id VARCHAR NOT NULL,
    fact_id VARCHAR NOT NULL,
    rule_id VARCHAR NOT NULL,
    rule_version VARCHAR DEFAULT '1',
    severity VARCHAR DEFAULT 'error',
    passed BOOLEAN DEFAULT TRUE,
    expected VARCHAR DEFAULT '',
    actual VARCHAR DEFAULT '',
    message VARCHAR DEFAULT '',
    checked_at VARCHAR NOT NULL DEFAULT ''
);

CREATE SEQUENCE IF NOT EXISTS fact_validation_seq START 1;
"""


class FactRepository:
    """事务化财务事实仓库。"""

    schema_version: str = "2.0"

    def __init__(self, duckdb_store: DuckDBStore):
        self.store = duckdb_store
        self._initialized = False

    # ── Schema ──────────────────────────────────────────

    def ensure_schema(self, git_commit: str = "") -> None:
        """安全初始化或迁移 schema v2.0。

        规则：
        - 无 M2 表 → 创建 2.0
        - 1.0 表非空 → 默认停止（抛出异常）
        - 不触及 Milestone 1 的表
        """
        self.ensure_schema_v2(git_commit)

    def ensure_schema_v2(self, git_commit: str = "") -> None:
        """安全初始化或迁移至 schema v2.0。

        规则：
        - 无 M2 表 → 创建 2.0
        - 已有 v2.0 → 无操作
        - 非空旧版本表 → 抛出 FactSchemaMigrationError（拒绝自动迁移）
        - 空表 → 重建为 v2.0（仅开发环境）
        - 不触及 Milestone 1 的表
        """
        conn = self.store.connect()
        existing = conn.execute(
            "SELECT name FROM sqlite_master "
            "WHERE type='table' AND name='financial_facts'"
        ).fetchone()

        if existing is None:
            # 全新创建
            self._create_v2_tables(conn, FACT_SCHEMA_V2_SQL)
            now = datetime.now().isoformat()
            conn.execute(
                """INSERT INTO fact_schema_meta
                   (schema_name, schema_version, applied_at, git_commit)
                   VALUES ('financial_facts', '2.0', ?, ?)""",
                [now, git_commit],
            )
            logger.info("FactRepository schema v2.0 created")
        else:
            # 检查 fact_schema_meta 是否存在（v1 可能有事实表但无元数据表）
            meta_exists = conn.execute(
                "SELECT name FROM sqlite_master "
                "WHERE type='table' AND name='fact_schema_meta'"
            ).fetchone()
            if meta_exists is None:
                # v1 旧表存在但没有元数据表 → 检查是否为空
                count = conn.execute(
                    "SELECT COUNT(*) FROM financial_facts"
                ).fetchone()[0]
                if count > 0:
                    raise FactSchemaMigrationError(
                        f"Cannot auto-migrate: financial_facts has "
                        f"{count} existing rows from schema v1, "
                        f"but fact_schema_meta table is missing. "
                        f"Use reset_m2_fact_schema() for dev reset."
                    )
                # 空表：重建为 v2
                self._rebuild_schema(conn, git_commit)
                self._initialized = True
                return

            meta = conn.execute(
                "SELECT schema_version FROM fact_schema_meta "
                "WHERE schema_name='financial_facts'"
            ).fetchone()

            if meta and meta[0] == "2.0":
                logger.info("FactRepository already at schema v2.0")
            else:
                count = conn.execute(
                    "SELECT COUNT(*) FROM financial_facts"
                ).fetchone()[0]
                if count > 0:
                    raise FactSchemaMigrationError(
                        f"Cannot auto-migrate: financial_facts has "
                        f"{count} existing rows. Use reset_m2_fact_schema() "
                        f"for development environments only."
                    )
                self._rebuild_schema(conn, git_commit)

        self._initialized = True

    def _create_v2_tables(self, conn, schema_sql: str) -> None:
        """从 SQL 字符串创建所有 v2 表。"""
        for stmt in schema_sql.split(";"):
            stmt = stmt.strip()
            if stmt:
                conn.execute(stmt)

    def store_schema_meta(
        self, schema_name: str, schema_version: str,
        git_commit: str = "", conn=None,
    ) -> None:
        """记录 schema 迁移元数据。

        用于在事务中与其他写入一起原子提交 schema 版本记录。
        """
        close_conn = False
        if conn is None:
            conn = self.store.connect()
            close_conn = True
        try:
            now = datetime.now().isoformat()
            conn.execute(
                """INSERT OR REPLACE INTO fact_schema_meta
                   (schema_name, schema_version, applied_at, git_commit)
                   VALUES (?, ?, ?, ?)""",
                [schema_name, schema_version, now, git_commit],
            )
        finally:
            if close_conn:
                pass  # DuckDB manages connection lifecycle

    def _rebuild_schema(self, conn, git_commit: str) -> None:
        """仅用于开发环境的空表重建。"""
        for table in ["financial_facts", "fact_contexts",
                       "concept_registry", "fact_lineage",
                       "fact_validation_runs",
                       "fact_validation_results",
                       "fact_schema_meta"]:
            conn.execute(f"DROP TABLE IF EXISTS {table}")
        self._create_v2_tables(conn, FACT_SCHEMA_V2_SQL)
        now = datetime.now().isoformat()
        conn.execute(
            """INSERT INTO fact_schema_meta
               (schema_name, schema_version, applied_at, git_commit)
               VALUES ('financial_facts', '2.0', ?, ?)""",
            [now, git_commit],
        )

    def reset_m2_fact_schema(self) -> None:
        """警告：仅开发环境：完全重置 M2 事实表。不影响 Milestone 1 表。"""
        conn = self.store.connect()
        self._rebuild_schema(conn, "")
        logger.warning("M2 fact schema completely reset — DEV ONLY")

    # ── 事务 ────────────────────────────────────────────

    @contextlib.contextmanager
    def transaction(self):
        """事务上下文管理器。

        用法:
            with repo.transaction() as conn:
                repo.store_facts(facts, conn=conn)
                repo.store_contexts(contexts, conn=conn)
                repo.store_schema_meta('financial_facts', '2.0', conn=conn)
        """
        conn = self.store.connect()
        conn.execute("BEGIN TRANSACTION")
        try:
            yield conn
        except Exception:
            conn.execute("ROLLBACK")
            raise
        else:
            conn.execute("COMMIT")

    # ── 种子 ────────────────────────────────────────────

    def seed_concepts(self, conn=None) -> int:
        """将概念注册表种子写入 DuckDB。

        使用 INSERT ON CONFLICT 避免覆盖已有版本。
        """
        from ashare_research.facts.concepts import ConceptRegistry

        close_conn = False
        if conn is None:
            conn = self.store.connect()
            close_conn = True

        count = 0
        now = datetime.now().isoformat()

        try:
            for concept in ConceptRegistry.list_all():
                conn.execute(
                    """INSERT INTO concept_registry
                       (concept_id, version, display_name,
                        display_name_zh, description, parent_concept_id,
                        category, statement_type, instant_or_duration,
                        canonical_unit, created_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                       ON CONFLICT (concept_id, version) DO UPDATE SET
                        display_name=excluded.display_name,
                        display_name_zh=excluded.display_name_zh,
                        canonical_unit=excluded.canonical_unit""",
                    [
                        concept.concept_id, concept.version,
                        concept.display_name,
                        concept.display_name_zh,
                        concept.description,
                        concept.parent_concept_id,
                        concept.category.value,
                        concept.statement_type,
                        concept.instant_or_duration.value,
                        concept.canonical_unit,
                        now,
                    ],
                )
                count += 1
        finally:
            if close_conn:
                pass  # DuckDB manages connection lifecycle

        logger.info(f"Seeded {count} concepts")
        return count

    # ── 存储（事务化） ──────────────────────────────────

    _FACT_COLS = [
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

    _CTX_COLS = [
        "context_id", "symbol", "fiscal_year", "period_type",
        "period_start", "period_end", "instant_or_duration",
        "consolidation_scope", "accounting_standard",
        "restatement_version", "source_document",
        "filing_date", "created_at",
    ]

    def store_facts(
        self, facts: list[dict[str, Any]], conn=None,
    ) -> int:
        """事务化批量写入事实。

        任意一条失败 → 抛出 FactPersistenceError（调用方负责回滚）。
        写入后验证实际行数与预期一致。
        """
        close_conn = False
        if conn is None:
            conn = self.store.connect()
            close_conn = True

        try:
            # 记录写入前计数用于后续验证
            before = conn.execute(
                "SELECT COUNT(*) FROM financial_facts"
            ).fetchone()[0]

            placeholders = ", ".join(["?"] * len(self._FACT_COLS))
            col_names = ", ".join(self._FACT_COLS)

            for fact in facts:
                vals = []
                for col in self._FACT_COLS:
                    vals.append(fact.get(col, ""))
                conn.execute(
                    f"INSERT OR REPLACE INTO financial_facts "
                    f"({col_names}) VALUES ({placeholders})",
                    vals,
                )

            # 验证写入数量与预期一致
            after = conn.execute(
                "SELECT COUNT(*) FROM financial_facts"
            ).fetchone()[0]
            actual_inserted = after - before
            expected = len(facts)

            if actual_inserted != expected:
                raise FactPersistenceError(
                    f"Fact count mismatch after store: "
                    f"expected {expected}, got {actual_inserted}"
                )

            return actual_inserted
        except FactPersistenceError:
            raise
        except Exception as e:
            raise FactPersistenceError(
                f"Failed to store facts: {e}"
            ) from e
        finally:
            if close_conn:
                pass  # DuckDB manages connection lifecycle

    def store_contexts(
        self, contexts: list[dict[str, Any]], conn=None,
    ) -> int:
        """事务化批量写入事实上下文。

        任意一条失败 → 抛出 FactPersistenceError。
        """
        close_conn = False
        if conn is None:
            conn = self.store.connect()
            close_conn = True
        try:
            for ctx in contexts:
                vals = [ctx.get(col, "") for col in self._CTX_COLS]
                placeholders = ", ".join(["?"] * len(vals))
                col_names = ", ".join(self._CTX_COLS)
                conn.execute(
                    f"INSERT OR REPLACE INTO fact_contexts "
                    f"({col_names}) VALUES ({placeholders})",
                    vals,
                )
            return len(contexts)
        except Exception as e:
            raise FactPersistenceError(
                f"Failed to store contexts: {e}"
            ) from e
        finally:
            if close_conn:
                pass  # DuckDB manages connection lifecycle

    def store_validation_run(
        self, run_id: str, fact_count: int = 0,
        error_count: int = 0, warning_count: int = 0,
        status: str = "pending", conn=None,
    ) -> None:
        """记录一次验证运行。

        可选传入 conn 以参与外部事务。
        """
        close_conn = False
        if conn is None:
            conn = self.store.connect()
            close_conn = True
        try:
            now = datetime.now().isoformat()
            conn.execute(
                """INSERT OR REPLACE INTO fact_validation_runs
                   (validation_run_id, started_at, completed_at,
                    fact_count, error_count, warning_count, status)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                [run_id, now, now, fact_count, error_count,
                 warning_count, status],
            )
        finally:
            if close_conn:
                pass  # DuckDB manages connection lifecycle

    def store_validation_results(
        self, results: list[dict[str, Any]],
        validation_run_id: str, conn=None,
    ) -> int:
        """批量写入验证结果。

        可选传入 conn 以参与外部事务。
        返回写入条数。
        """
        close_conn = False
        if conn is None:
            conn = self.store.connect()
            close_conn = True
        try:
            count = 0
            for r in results:
                conn.execute(
                    """INSERT INTO fact_validation_results
                       (id, validation_run_id, fact_id, rule_id,
                        rule_version, severity, passed,
                        expected, actual, message, checked_at)
                       VALUES (nextval('fact_validation_seq'),
                        ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    [
                        validation_run_id,
                        r.get("target_id", ""),
                        r.get("rule_id", ""),
                        r.get("rule_version", "1"),
                        r.get("severity", "error"),
                        r.get("passed", True),
                        r.get("expected", ""),
                        r.get("actual", ""),
                        r.get("message", ""),
                        r.get("checked_at", ""),
                    ],
                )
                count += 1
            return count
        finally:
            if close_conn:
                pass  # DuckDB manages connection lifecycle

    def store_lineage(
        self, fact_id: str, run_id: str = "",
        source_provider: str = "", source_tier: str = "",
        source_method: str = "",
        raw_path: str = "", staging_path: str = "",
        fetch_run_id: str = "", parent_fact_ids: str = "",
        conn=None,
    ) -> None:
        """记录单条事实的数据沿袭。

        可选传入 conn 以参与外部事务。
        """
        close_conn = False
        if conn is None:
            conn = self.store.connect()
            close_conn = True
        try:
            now = datetime.now().isoformat()
            conn.execute(
                """INSERT INTO fact_lineage
                   (lineage_id, fact_id, run_id, source_provider,
                    source_tier, source_method,
                    raw_file_path, staging_file_path,
                    fetch_run_id, parent_fact_ids, recorded_at)
                   VALUES (nextval('fact_lineage_seq'),
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                [fact_id, run_id, source_provider, source_tier,
                 source_method,
                 raw_path, staging_path, fetch_run_id,
                 parent_fact_ids, now],
            )
        finally:
            if close_conn:
                pass  # DuckDB manages connection lifecycle

    # ── 查询 ────────────────────────────────────────────

    def query_facts(
        self,
        symbol: str,
        concept_ids: list[str] | None = None,
        start_year: int | None = None,
        end_year: int | None = None,
        as_of_date: str | None = None,
        include_unverified: bool = False,
    ) -> pd.DataFrame:
        """查询事实。

        PIT 查询：仅返回 available_at 非空且 <= as_of_date 的事实。
        默认过滤未核验事实（include_unverified=True 仅用于审计）。
        """
        conn = self.store.connect()
        query = "SELECT * FROM financial_facts WHERE symbol = ?"
        params: list = [symbol]

        if concept_ids:
            placeholders = ", ".join(["?"] * len(concept_ids))
            query += f" AND concept_id IN ({placeholders})"
            params.extend(concept_ids)

        if start_year:
            query += (
                " AND CAST(SUBSTR(period_end,1,4) AS INTEGER) >= ?"
            )
            params.append(start_year)

        if end_year:
            query += (
                " AND CAST(SUBSTR(period_end,1,4) AS INTEGER) <= ?"
            )
            params.append(end_year)

        if as_of_date:
            # PIT 门禁：available_at 必须非空且非空字符串且 <= as_of_date
            query += (
                " AND available_at IS NOT NULL"
                " AND available_at <> ''"
                " AND available_at <= ?"
            )
            params.append(as_of_date)

        # 默认过滤：仅返回 verified/reconciled + eligible_for_metrics
        if not include_unverified:
            query += (
                " AND verification_status IN ('verified', 'reconciled')"
                " AND eligible_for_metrics = TRUE"
            )

        query += " ORDER BY period_end, concept_id, fact_version DESC"

        return conn.execute(query, params).df()

    def get_latest_available(
        self,
        symbol: str,
        as_of_date: str,
        concept_ids: list[str] | None = None,
        consolidation_scope: str = "consolidated",
    ) -> pd.DataFrame:
        """获取截至指定日期的每个事实键的最新版本。

        使用 ROW_NUMBER() 窗口函数选择最新版本。
        PIT 门禁：available_at 必须非空且非空字符串且 <= as_of_date。
        """
        conn = self.store.connect()

        concept_filter = ""
        params: list = [symbol, as_of_date]
        if concept_ids:
            placeholders = ", ".join(["?"] * len(concept_ids))
            concept_filter = f" AND concept_id IN ({placeholders})"
            params[1:1] = concept_ids

        query = f"""
            SELECT * FROM (
                SELECT f.*,
                    ROW_NUMBER() OVER (
                        PARTITION BY f.symbol, f.concept_id, f.period_end,
                                     c.consolidation_scope
                        ORDER BY f.available_at DESC, f.fact_version DESC,
                                 f.created_at DESC
                    ) AS rn
                FROM financial_facts f
                JOIN fact_contexts c ON f.context_id = c.context_id
                WHERE f.symbol = ?
                  {concept_filter}
                  AND c.consolidation_scope = ?
                  AND f.available_at IS NOT NULL
                  AND f.available_at <> ''
                  AND f.available_at <= ?
                  AND f.verification_status IN ('verified', 'reconciled')
                  AND f.eligible_for_metrics = TRUE
            ) sub
            WHERE sub.rn = 1
            ORDER BY sub.period_end, sub.concept_id
        """
        params_with_scope = [symbol]
        if concept_ids:
            params_with_scope.extend(concept_ids)
        params_with_scope.append(consolidation_scope)
        params_with_scope.append(as_of_date)
        return conn.execute(query, params_with_scope).df()

    def get_fact_summary(self, symbol: str) -> dict[str, Any]:
        """返回指定 symbol 的事实摘要统计。"""
        conn = self.store.connect()
        result = conn.execute(
            """SELECT
                 COUNT(*) as total,
                 SUM(CASE WHEN is_derived THEN 1 ELSE 0 END) as derived,
                 SUM(CASE WHEN verification_status='verified'
                     THEN 1 ELSE 0 END) as verified,
                 SUM(CASE WHEN verification_status='reconciled'
                     THEN 1 ELSE 0 END) as reconciled,
                 SUM(CASE WHEN verification_status='unverified'
                     THEN 1 ELSE 0 END) as unverified
               FROM financial_facts WHERE symbol = ?""",
            [symbol],
        ).df()
        if result.empty:
            return {}
        return result.iloc[0].to_dict()

    def get_all_versions_for_audit(
        self,
        symbol: str,
        concept_ids: list[str] | None = None,
    ) -> pd.DataFrame:
        """审计专用：返回所有版本（不含 PIT 过滤）。

        此方法返回空 available_at、unverified 和旧版本。
        不得在正式分析代码中调用。
        """
        return self.query_facts(
            symbol=symbol,
            concept_ids=concept_ids,
            include_unverified=True,
        )
