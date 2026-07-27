"""M2 Stage 1 — FactRepository: DuckDB 事实存储。

包装现有 DuckDBStore，管理 5 张新表的 CRUD。
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

import pandas as pd

from ashare_research.storage.duckdb_store import DuckDBStore

logger = logging.getLogger(__name__)

FACT_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS financial_facts (
    fact_id VARCHAR PRIMARY KEY,
    concept_id VARCHAR NOT NULL,
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
    source_document VARCHAR DEFAULT '',
    source_page VARCHAR DEFAULT '',
    source_table VARCHAR DEFAULT '',
    source_label VARCHAR DEFAULT '',
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
    concept_id VARCHAR PRIMARY KEY,
    version VARCHAR DEFAULT '1',
    display_name VARCHAR NOT NULL DEFAULT '',
    display_name_zh VARCHAR DEFAULT '',
    description VARCHAR DEFAULT '',
    parent_concept_id VARCHAR DEFAULT '',
    category VARCHAR NOT NULL DEFAULT '',
    statement_type VARCHAR DEFAULT '',
    instant_or_duration VARCHAR DEFAULT 'duration',
    canonical_unit VARCHAR DEFAULT '',
    created_at VARCHAR NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS fact_lineage (
    lineage_id INTEGER PRIMARY KEY,
    fact_id VARCHAR NOT NULL,
    source_provider VARCHAR NOT NULL DEFAULT '',
    source_method VARCHAR DEFAULT '',
    raw_file_path VARCHAR DEFAULT '',
    staging_file_path VARCHAR DEFAULT '',
    fetch_run_id VARCHAR DEFAULT '',
    parent_fact_ids VARCHAR DEFAULT '',
    recorded_at VARCHAR NOT NULL DEFAULT ''
);

CREATE SEQUENCE IF NOT EXISTS fact_lineage_seq START 1;

CREATE TABLE IF NOT EXISTS fact_validation_results (
    id INTEGER PRIMARY KEY,
    fact_id VARCHAR NOT NULL,
    rule_name VARCHAR NOT NULL,
    status VARCHAR NOT NULL DEFAULT '',
    details VARCHAR DEFAULT '',
    checked_at VARCHAR NOT NULL DEFAULT ''
);

CREATE SEQUENCE IF NOT EXISTS fact_validation_seq START 1;
"""


class FactRepository:
    """财务事实仓库。

    包装 DuckDBStore，不创建新连接。
    """

    schema_version: str = "1.0"

    def __init__(self, duckdb_store: DuckDBStore):
        self.store = duckdb_store
        self._initialized = False

    def init_schema(self) -> None:
        """创建 M2 Stage 1 所需的表。"""
        conn = self.store.connect()
        # 分条执行以避免多语句问题
        for stmt in FACT_SCHEMA_SQL.split(";"):
            stmt = stmt.strip()
            if stmt and not stmt.startswith("--"):
                try:
                    conn.execute(stmt)
                except Exception:
                    pass  # CREATE IF NOT EXISTS 安全
        self._initialized = True
        logger.info("FactRepository schema initialized")

    def seed_concepts(self) -> int:
        """将概念注册表种子写入 DuckDB。"""
        from ashare_research.facts.concepts import ConceptRegistry

        conn = self.store.connect()
        count = 0
        now = datetime.now().isoformat()

        for concept in ConceptRegistry.list_all():
            conn.execute(
                """INSERT OR REPLACE INTO concept_registry
                   (concept_id, version, display_name, display_name_zh,
                    description, parent_concept_id, category,
                    statement_type, instant_or_duration,
                    canonical_unit, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                [
                    concept.concept_id,
                    concept.version,
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

        logger.info(f"Seeded {count} concepts")
        return count

    def store_facts(self, facts: list[dict[str, Any]]) -> int:
        """INSERT OR REPLACE 写入事实。"""
        conn = self.store.connect()
        count = 0
        cols = [
            "fact_id", "concept_id", "symbol", "value", "unit",
            "context_id", "is_derived", "derived_from",
            "derivation_definition_id", "derivation_version",
            "input_fact_ids", "source_provider", "source_document",
            "filing_date", "period_end", "announcement_date",
            "available_at", "raw_value", "raw_unit",
            "normalized_value", "normalization_rule",
            "verification_status", "verification_note",
            "eligible_for_metrics", "created_at",
        ]

        for fact in facts:
            vals = []
            for col in cols:
                val = fact.get(col, "")
                if isinstance(val, bool):
                    val = str(val).lower()
                elif val is None:
                    val = None
                vals.append(val)

            placeholders = ", ".join(["?"] * len(vals))
            col_names = ", ".join(cols)

            try:
                conn.execute(
                    f"INSERT OR REPLACE INTO financial_facts "
                    f"({col_names}) VALUES ({placeholders})",
                    vals,
                )
                count += 1
            except Exception as e:
                logger.error(
                    f"Failed to store fact {fact.get('fact_id', '?')}: {e}"
                )

        return count

    def store_contexts(self, contexts: list[dict[str, Any]]) -> int:
        """存储事实上下文。"""
        conn = self.store.connect()
        count = 0
        cols = [
            "context_id", "symbol", "fiscal_year", "period_type",
            "period_start", "period_end", "instant_or_duration",
            "consolidation_scope", "accounting_standard",
            "restatement_version", "source_document",
            "filing_date", "created_at",
        ]

        for ctx in contexts:
            vals = [ctx.get(col, "") for col in cols]
            placeholders = ", ".join(["?"] * len(vals))
            col_names = ", ".join(cols)

            try:
                conn.execute(
                    f"INSERT OR REPLACE INTO fact_contexts "
                    f"({col_names}) VALUES ({placeholders})",
                    vals,
                )
                count += 1
            except Exception as e:
                logger.error(f"Failed to store context: {e}")

        return count

    def query_facts(
        self,
        symbol: str,
        concept_ids: list[str] | None = None,
        start_year: int | None = None,
        end_year: int | None = None,
        as_of_date: str | None = None,
    ) -> pd.DataFrame:
        """查询事实，支持 PIT 过滤。"""
        conn = self.store.connect()
        query = "SELECT * FROM financial_facts WHERE symbol = ?"
        params: list = [symbol]

        if concept_ids:
            placeholders = ", ".join(["?"] * len(concept_ids))
            query += f" AND concept_id IN ({placeholders})"
            params.extend(concept_ids)

        if start_year:
            query += " AND CAST(SUBSTR(period_end,1,4) AS INTEGER) >= ?"
            params.append(start_year)

        if end_year:
            query += " AND CAST(SUBSTR(period_end,1,4) AS INTEGER) <= ?"
            params.append(end_year)

        if as_of_date:
            query += " AND (available_at = '' OR available_at <= ?)"
            params.append(as_of_date)

        query += " ORDER BY period_end, concept_id"

        return conn.execute(query, params).df()

    def record_lineage(
        self, fact_id: str, source_provider: str = "",
        raw_path: str = "", staging_path: str = "",
        fetch_run_id: str = "", parent_fact_ids: str = "",
    ) -> None:
        """记录事实血缘。"""
        conn = self.store.connect()
        now = datetime.now().isoformat()
        conn.execute(
            """INSERT INTO fact_lineage
               (lineage_id, fact_id, source_provider,
                raw_file_path, staging_file_path,
                fetch_run_id, parent_fact_ids, recorded_at)
               VALUES (nextval('fact_lineage_seq'), ?, ?, ?, ?, ?, ?, ?)""",
            [fact_id, source_provider, raw_path, staging_path,
             fetch_run_id, parent_fact_ids, now],
        )

    def record_validation_result(
        self, fact_id: str, rule_name: str,
        status: str, details: str = "",
    ) -> None:
        """记录校验结果。"""
        conn = self.store.connect()
        now = datetime.now().isoformat()
        conn.execute(
            """INSERT INTO fact_validation_results
               (id, fact_id, rule_name, status, details, checked_at)
               VALUES (nextval('fact_validation_seq'), ?, ?, ?, ?, ?)""",
            [fact_id, rule_name, status, details, now],
        )

    def get_fact_summary(self, symbol: str) -> dict[str, Any]:
        """获取事实摘要统计。"""
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
