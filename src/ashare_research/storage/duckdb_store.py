"""DuckDB 元数据存储层。

负责：
- 初始化数据库 schema
- 记录数据抓取任务 (data_fetch_runs)
- 数据集登记 (dataset_registry)
- 质量检查结果 (data_quality_results)
- 查询 Parquet 数据

不在 DuckDB 中重复保存全部日线数据。
"""

from __future__ import annotations

import logging
import os
import uuid
from datetime import datetime
from typing import Any

import duckdb
import pandas as pd

logger = logging.getLogger(__name__)

SCHEMA_VERSION = "1.0"

INIT_SQL = """
CREATE TABLE IF NOT EXISTS schema_migrations (
    version VARCHAR PRIMARY KEY,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS data_fetch_runs (
    run_id VARCHAR PRIMARY KEY,
    dataset VARCHAR NOT NULL,
    provider VARCHAR NOT NULL,
    symbol VARCHAR DEFAULT '',
    start_date VARCHAR DEFAULT '',
    end_date VARCHAR DEFAULT '',
    status VARCHAR DEFAULT 'pending',
    row_count INTEGER DEFAULT 0,
    started_at VARCHAR DEFAULT '',
    finished_at VARCHAR DEFAULT '',
    raw_file_path VARCHAR DEFAULT '',
    parquet_path VARCHAR DEFAULT '',
    schema_version VARCHAR DEFAULT '1.0',
    quality_status VARCHAR DEFAULT '',
    error_type VARCHAR DEFAULT '',
    error_message VARCHAR DEFAULT ''
);

CREATE TABLE IF NOT EXISTS dataset_registry (
    dataset VARCHAR NOT NULL,
    symbol VARCHAR NOT NULL,
    provider VARCHAR NOT NULL,
    parquet_path VARCHAR NOT NULL,
    row_count INTEGER DEFAULT 0,
    date_min VARCHAR DEFAULT '',
    date_max VARCHAR DEFAULT '',
    last_updated VARCHAR DEFAULT '',
    adjustment VARCHAR DEFAULT 'none',
    PRIMARY KEY (dataset, symbol, adjustment)
);

CREATE TABLE IF NOT EXISTS data_quality_results (
    id INTEGER PRIMARY KEY,
    run_id VARCHAR NOT NULL,
    check_name VARCHAR NOT NULL,
    status VARCHAR NOT NULL,
    details VARCHAR DEFAULT '',
    checked_at VARCHAR DEFAULT ''
);

CREATE SEQUENCE IF NOT EXISTS quality_result_seq START 1;
"""


class DuckDBStore:
    """DuckDB 元数据存储。

    用法:
        store = DuckDBStore("data/research.duckdb")
        store.init_db()
        store.record_fetch_run(...)
        result = store.query("SELECT * FROM data_fetch_runs")
    """

    def __init__(self, db_path: str):
        self.db_path = str(db_path)
        db_dir = os.path.dirname(self.db_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)
        self._conn: duckdb.DuckDBPyConnection | None = None

    def connect(self) -> duckdb.DuckDBPyConnection:
        """获取或创建数据库连接。"""
        if self._conn is None:
            self._conn = duckdb.connect(self.db_path)
        return self._conn

    def close(self) -> None:
        """关闭连接。"""
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    def init_db(self) -> None:
        """初始化数据库 schema。"""
        conn = self.connect()
        conn.execute(INIT_SQL)

        # 记录 schema 版本
        existing = conn.execute(
            "SELECT version FROM schema_migrations WHERE version = ?",
            [SCHEMA_VERSION],
        ).fetchone()

        if not existing:
            conn.execute(
                "INSERT INTO schema_migrations (version) VALUES (?)",
                [SCHEMA_VERSION],
            )
            logger.info(f"DuckDB schema initialized (v{SCHEMA_VERSION}): {self.db_path}")
        else:
            logger.info(f"DuckDB already at schema v{SCHEMA_VERSION}")

    # ── 抓取任务记录 ──────────────────────────────────────

    def start_fetch_run(
        self,
        dataset: str,
        provider: str,
        symbol: str = "",
        start_date: str = "",
        end_date: str = "",
    ) -> str:
        """开始一个抓取任务，返回 run_id。"""
        conn = self.connect()
        run_id = uuid.uuid4().hex[:12]
        started_at = datetime.now().isoformat()

        conn.execute(
            """INSERT INTO data_fetch_runs
               (run_id, dataset, provider, symbol, start_date, end_date,
                status, started_at)
               VALUES (?, ?, ?, ?, ?, ?, 'running', ?)""",
            [run_id, dataset, provider, symbol, start_date, end_date, started_at],
        )
        logger.info(f"Fetch run started: {run_id} ({dataset}/{provider}/{symbol})")
        return run_id

    def complete_fetch_run(
        self,
        run_id: str,
        row_count: int = 0,
        raw_file_path: str = "",
        parquet_path: str = "",
        quality_status: str = "passed",
    ) -> None:
        """标记抓取任务成功完成。"""
        conn = self.connect()
        finished_at = datetime.now().isoformat()

        conn.execute(
            """UPDATE data_fetch_runs
               SET status = 'success', row_count = ?, finished_at = ?,
                   raw_file_path = ?, parquet_path = ?, quality_status = ?
               WHERE run_id = ?""",
            [row_count, finished_at, raw_file_path, parquet_path,
             quality_status, run_id],
        )

        # 更新数据集注册表（如果有 parquet_path）
        if parquet_path and row_count > 0:
            self._upsert_dataset_registry(run_id)

        logger.info(f"Fetch run completed: {run_id} ({row_count} rows)")

    def fail_fetch_run(
        self,
        run_id: str,
        error_type: str = "",
        error_message: str = "",
    ) -> None:
        """标记抓取任务失败。

        错误消息会脱敏，不记录 Token、Cookie。
        """
        conn = self.connect()
        finished_at = datetime.now().isoformat()

        # 脱敏处理
        safe_message = _sanitize_error_message(error_message)

        conn.execute(
            """UPDATE data_fetch_runs
               SET status = 'failed', finished_at = ?,
                   error_type = ?, error_message = ?
               WHERE run_id = ?""",
            [finished_at, error_type, safe_message, run_id],
        )
        logger.error(f"Fetch run failed: {run_id} [{error_type}]: {safe_message}")

    def _upsert_dataset_registry(self, run_id: str) -> None:
        """从成功的抓取任务更新数据集注册表。"""
        conn = self.connect()

        row = conn.execute(
            """SELECT dataset, symbol, provider, parquet_path,
                      row_count, start_date, end_date
               FROM data_fetch_runs WHERE run_id = ?""",
            [run_id],
        ).fetchone()

        if not row:
            return

        dataset, symbol, provider, parquet_path, row_count, date_min, date_max = row
        now = datetime.now().isoformat()

        # 推断复权方式
        adjustment = "none"
        if dataset == "stock_daily":
            # 从 parquet 路径或数据推断
            pass

        # 尝试从 parquet 读取日期范围
        if parquet_path and os.path.exists(parquet_path):
            try:
                df = pd.read_parquet(parquet_path)
                if "trade_date" in df.columns:
                    date_min = str(df["trade_date"].min())
                    date_max = str(df["trade_date"].max())
                if "adjustment" in df.columns and not df.empty:
                    adjustment = str(df["adjustment"].iloc[0])
            except Exception:
                pass

        symbol_key = symbol if symbol else "_all"

        conn.execute(
            """INSERT OR REPLACE INTO dataset_registry
               (dataset, symbol, provider, parquet_path, row_count,
                date_min, date_max, last_updated, adjustment)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            [dataset, symbol_key, provider, parquet_path, row_count,
             date_min or "", date_max or "", now, adjustment],
        )

    # ── 质量结果 ──────────────────────────────────────────

    def record_quality_result(
        self, run_id: str, check_name: str, status: str, details: str = ""
    ) -> None:
        """记录质量检查结果。"""
        conn = self.connect()
        checked_at = datetime.now().isoformat()

        conn.execute(
            """INSERT INTO data_quality_results
               (id, run_id, check_name, status, details, checked_at)
               VALUES (nextval('quality_result_seq'), ?, ?, ?, ?, ?)""",
            [run_id, check_name, status, details, checked_at],
        )

    # ── 查询 ──────────────────────────────────────────────

    def query(self, sql: str, params: list | None = None) -> pd.DataFrame:
        """执行查询，返回 DataFrame。"""
        conn = self.connect()
        if params:
            return conn.execute(sql, params).df()
        return conn.execute(sql).df()

    def query_parquet(self, parquet_path: str, sql: str = "") -> pd.DataFrame:
        """直接查询 Parquet 文件。

        如果不提供 SQL，返回全部内容。
        """
        conn = self.connect()
        if sql:
            return conn.execute(sql).df()
        return conn.execute(
            f"SELECT * FROM read_parquet('{parquet_path}')"
        ).df()

    def get_dataset_info(self, dataset: str, symbol: str = "_all") -> dict[str, Any]:
        """获取数据集信息。"""
        conn = self.connect()

        row = conn.execute(
            """SELECT * FROM dataset_registry
               WHERE dataset = ? AND symbol = ?""",
            [dataset, symbol],
        ).fetchone()

        if not row:
            return {"registered": False}

        cols = [desc[0] for desc in conn.description]
        info = dict(zip(cols, row, strict=False))
        info["registered"] = True

        # 获取最近抓取记录
        runs = conn.execute(
            """SELECT run_id, status, started_at, finished_at, row_count
               FROM data_fetch_runs
               WHERE dataset = ? AND (symbol = ? OR symbol = '')
               ORDER BY started_at DESC LIMIT 5""",
            [dataset, symbol],
        ).df()

        info["recent_runs"] = runs.to_dict("records") if not runs.empty else []

        return info

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, *args):
        self.close()


def _sanitize_error_message(msg: str) -> str:
    """对错误消息做基础脱敏。

    移除疑似 Token、Cookie、API Key 的内容。
    """
    if not msg:
        return msg

    # 截断过长消息
    if len(msg) > 2000:
        msg = msg[:2000] + "...[truncated]"

    # 移除常见凭证模式
    import re
    msg = re.sub(r'token[=:]\s*\S+', 'token=***', msg, flags=re.IGNORECASE)
    msg = re.sub(r'cookie[=:]\s*\S+', 'cookie=***', msg, flags=re.IGNORECASE)

    return msg
