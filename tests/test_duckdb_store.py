"""DuckDB 元数据存储测试。"""

import contextlib
import os
import tempfile

import pytest

from ashare_research.storage.duckdb_store import DuckDBStore


@pytest.fixture
def duckdb_store():
    """创建临时 DuckDB 存储。"""
    tmpdir = tempfile.mkdtemp()
    db_path = os.path.join(tmpdir, "test.duckdb")
    store = DuckDBStore(db_path)
    store.connect()
    store.init_db()
    yield store
    store.close()
    # 清理
    try:
        os.unlink(db_path)
        os.rmdir(tmpdir)
    except Exception:
        pass


class TestDuckDBStore:
    """DuckDB 元数据存储测试。"""

    def test_init_creates_tables(self, duckdb_store):
        result = duckdb_store.query(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        tables = result["name"].tolist()
        assert "data_fetch_runs" in tables
        assert "dataset_registry" in tables
        assert "data_quality_results" in tables

    def test_schema_version_recorded(self, duckdb_store):
        result = duckdb_store.query(
            "SELECT version FROM schema_migrations"
        )
        assert len(result) == 1
        assert result["version"].iloc[0] == "1.0"

    def test_start_and_complete_fetch_run(self, duckdb_store):
        run_id = duckdb_store.start_fetch_run(
            dataset="stock_daily",
            provider="baostock",
            symbol="601857.SH",
            start_date="2026-07-01",
            end_date="2026-07-27",
        )
        assert len(run_id) == 12

        duckdb_store.complete_fetch_run(
            run_id=run_id,
            row_count=100,
            parquet_path="data/parquet/stock_daily/601857.SH.parquet",
            quality_status="passed",
        )

        result = duckdb_store.query(
            "SELECT status, row_count, quality_status FROM data_fetch_runs WHERE run_id = ?",
            [run_id],
        )
        assert result["status"].iloc[0] == "success"
        assert result["row_count"].iloc[0] == 100
        assert result["quality_status"].iloc[0] == "passed"

    def test_failed_fetch_run(self, duckdb_store):
        run_id = duckdb_store.start_fetch_run(
            dataset="stock_daily",
            provider="baostock",
            symbol="601857.SH",
        )
        duckdb_store.fail_fetch_run(
            run_id=run_id,
            error_type="NetworkError",
            error_message="Connection timeout after 30s",
        )

        result = duckdb_store.query(
            "SELECT status, error_type FROM data_fetch_runs WHERE run_id = ?",
            [run_id],
        )
        assert result["status"].iloc[0] == "failed"
        assert result["error_type"].iloc[0] == "NetworkError"

    def test_error_message_sanitization(self, duckdb_store):
        """错误消息中不应包含 Token/Cookie。"""
        run_id = duckdb_store.start_fetch_run(
            dataset="stock_daily", provider="baostock",
        )
        duckdb_store.fail_fetch_run(
            run_id=run_id,
            error_type="AuthError",
            error_message="token=abc123def456ghijklmnopqrstuvwxyz and cookie=secret",
        )

        result = duckdb_store.query(
            "SELECT error_message FROM data_fetch_runs WHERE run_id = ?",
            [run_id],
        )
        msg = result["error_message"].iloc[0]
        assert "abc123" not in msg
        assert "secret" not in msg
        assert "token=***" in msg
        assert "cookie=***" in msg

    def test_quality_result_recording(self, duckdb_store):
        run_id = duckdb_store.start_fetch_run(
            dataset="stock_daily", provider="baostock",
        )
        duckdb_store.record_quality_result(
            run_id=run_id,
            check_name="ohlc_logic",
            status="passed",
            details="All checks OK",
        )
        duckdb_store.record_quality_result(
            run_id=run_id,
            check_name="non_negative",
            status="failed",
            details="close column has negative values",
        )

        result = duckdb_store.query(
            "SELECT check_name, status FROM data_quality_results WHERE run_id = ? ORDER BY id",
            [run_id],
        )
        assert len(result) == 2
        assert result["status"].tolist() == ["passed", "failed"]

    def test_idempotent_init(self, duckdb_store):
        """重复 init_db 不应报错。"""
        duckdb_store.init_db()
        duckdb_store.init_db()

        result = duckdb_store.query(
            "SELECT COUNT(*) as cnt FROM schema_migrations"
        )
        assert result["cnt"].iloc[0] >= 1

    def test_dataset_registry_update_on_complete(self, duckdb_store):
        run_id = duckdb_store.start_fetch_run(
            dataset="stock_daily",
            provider="baostock",
            symbol="601857.SH",
        )

        # 创建临时 parquet 文件
        import pandas as pd
        tmpdir = os.path.dirname(duckdb_store.db_path)
        parquet_path = os.path.join(tmpdir, "test_data.parquet")
        df = pd.DataFrame({
            "symbol": ["601857.SH"] * 3,
            "trade_date": ["2026-07-01", "2026-07-02", "2026-07-03"],
            "close": [10.0, 10.1, 10.2],
            "adjustment": ["none"] * 3,
        })
        df.to_parquet(parquet_path)

        duckdb_store.complete_fetch_run(
            run_id=run_id,
            row_count=3,
            parquet_path=parquet_path,
        )

        info = duckdb_store.get_dataset_info("stock_daily", "601857.SH")
        assert info["registered"] is True
        assert info["row_count"] == 3

        # 清理
        with contextlib.suppress(Exception):
            os.unlink(parquet_path)

    def test_query_parquet(self, duckdb_store):
        """测试直接查询 Parquet。"""
        import pandas as pd
        tmpdir = os.path.dirname(duckdb_store.db_path)
        parquet_path = os.path.join(tmpdir, "query_test.parquet")
        df = pd.DataFrame({
            "symbol": ["601857.SH"] * 2,
            "trade_date": ["2026-07-01", "2026-07-02"],
            "close": [10.0, 10.1],
        })
        df.to_parquet(parquet_path)

        result = duckdb_store.query_parquet(parquet_path)
        assert len(result) == 2

        with contextlib.suppress(Exception):
            os.unlink(parquet_path)
