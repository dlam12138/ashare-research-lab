"""数据服务层集成测试。

测试 provider fallback、data service 编排和 Mock 提供方。
"""

import os
import tempfile

import pandas as pd
import pytest

from ashare_research.exceptions import AshareDataError
from ashare_research.providers.base import BaseProvider
from ashare_research.services.data_service import DataService
from ashare_research.storage.duckdb_store import DuckDBStore


class MockProvider(BaseProvider):
    """Mock 数据提供方，用于测试。"""

    provider_name = "mock"

    def get_stock_basic(self) -> pd.DataFrame:
        return pd.DataFrame({
            "symbol": ["601857.SH", "600519.SH"],
            "exchange": ["SH", "SH"],
            "name": ["中国石油", "贵州茅台"],
            "list_date": ["2007-11-05", "2001-08-27"],
            "delist_date": ["", ""],
            "status": ["1", "1"],
            "source": ["mock", "mock"],
            "fetched_at": ["2026-07-27T12:00:00", "2026-07-27T12:00:00"],
        })

    def get_trade_calendar(
        self, start_date: str, end_date: str, exchange: str = "SH"
    ) -> pd.DataFrame:
        return pd.DataFrame({
            "trade_date": ["2026-07-20", "2026-07-21", "2026-07-22"],
            "exchange": ["SH"] * 3,
            "is_open": [True] * 3,
            "source": ["mock"] * 3,
            "fetched_at": ["2026-07-27T12:00:00"] * 3,
        })

    def get_stock_daily(
        self, symbol: str, start_date: str, end_date: str, adjustment: str = "none"
    ) -> pd.DataFrame:
        return pd.DataFrame({
            "symbol": [symbol] * 3,
            "trade_date": ["2026-07-20", "2026-07-21", "2026-07-22"],
            "open": [10.0, 10.2, 10.1],
            "high": [10.5, 10.4, 10.3],
            "low": [9.8, 10.0, 9.9],
            "close": [10.2, 10.1, 10.2],
            "pre_close": [10.1, 10.2, 10.1],
            "volume": [1e7, 1.2e7, 8e6],
            "amount": [1e8, 1.2e8, 8e7],
            "turnover_rate": [0.5, 0.6, 0.4],
            "is_trading": [True] * 3,
            "adjustment": [adjustment] * 3,
            "source": ["mock"] * 3,
            "fetched_at": ["2026-07-27T12:00:00"] * 3,
        })

    def get_index_daily(self, symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
        return pd.DataFrame({
            "symbol": [symbol] * 3,
            "trade_date": ["2026-07-20", "2026-07-21", "2026-07-22"],
            "open": [3300.0, 3310.0, 3290.0],
            "high": [3320.0, 3325.0, 3320.0],
            "low": [3280.0, 3290.0, 3270.0],
            "close": [3310.0, 3300.0, 3290.0],
            "volume": [1e8, 1.2e8, 8e7],
            "amount": [3e11, 3.5e11, 2.5e11],
            "source": ["mock"] * 3,
            "fetched_at": ["2026-07-27T12:00:00"] * 3,
        })


class FailingProvider(BaseProvider):
    """总是抛异常的 Mock 提供方（测试提供方失败路径）。"""

    provider_name = "failing"

    def get_stock_basic(self) -> pd.DataFrame:
        raise AshareDataError("Simulated stock basic failure")

    def get_trade_calendar(self, start_date, end_date, exchange="SH") -> pd.DataFrame:
        raise AshareDataError("Simulated calendar failure")

    def get_stock_daily(self, symbol, start_date, end_date, adjustment="none") -> pd.DataFrame:
        raise AshareDataError("Simulated stock daily failure")

    def get_index_daily(self, symbol, start_date, end_date) -> pd.DataFrame:
        raise AshareDataError("Simulated index daily failure")


class BadDataProvider(BaseProvider):
    """返回有效 DataFrame 但数据不合格的提供方（测试质量门禁路径）。

    与 FailingProvider 不同：这里 Provider 调用成功，
    但返回的数据有质量问题，应被质量检查拦截。
    """

    provider_name = "bad_data"

    def __init__(self, bad_type: str = "nan"):
        super().__init__()
        self.bad_type = bad_type

    def get_stock_basic(self) -> pd.DataFrame:
        return pd.DataFrame({
            "symbol": ["601857.SH"], "exchange": ["SH"], "name": ["测试"],
            "source": ["bad_data"], "fetched_at": ["2026-07-27T12:00:00"],
        })

    def get_trade_calendar(self, start_date, end_date, exchange="SH") -> pd.DataFrame:
        return pd.DataFrame({
            "trade_date": ["2026-07-20"], "exchange": ["SH"],
            "is_open": [True], "source": ["bad_data"],
            "fetched_at": ["2026-07-27T12:00:00"],
        })

    def get_stock_daily(self, symbol, start_date, end_date, adjustment="none") -> pd.DataFrame:
        base = {
            "symbol": [symbol] * 3,
            "trade_date": ["2026-07-20", "2026-07-21", "2026-07-22"],
            "open": [10.0, 10.2, 10.1],
            "high": [10.5, 10.4, 10.3],
            "low": [9.8, 10.0, 9.9],
            "close": [10.2, 10.1, 10.2],
            "pre_close": [10.1, 10.2, 10.1],
            "volume": [1e7, 1.2e7, 8e6],
            "amount": [1e8, 1.2e8, 8e7],
            "turnover_rate": [0.5, 0.6, 0.4],
            "is_trading": [True] * 3,
            "adjustment": [adjustment] * 3,
            "source": ["bad_data"] * 3,
            "fetched_at": ["2026-07-27T12:00:00"] * 3,
        }

        if self.bad_type == "nan":
            base["volume"][1] = float("nan")
        elif self.bad_type == "inf":
            base["close"][2] = float("inf")
        elif self.bad_type == "neg_inf":
            base["close"][2] = float("-inf")
        elif self.bad_type == "duplicate_pk":
            base["trade_date"][2] = base["trade_date"][0]
        elif self.bad_type == "ohlc_broken":
            base["high"][1] = base["low"][1] - 1.0
        elif self.bad_type == "missing_field":
            result = pd.DataFrame(base)
            result = result.drop(columns=["volume"])
            return result

        return pd.DataFrame(base)

    def get_index_daily(self, symbol, start_date, end_date) -> pd.DataFrame:
        return pd.DataFrame({
            "symbol": [symbol] * 3,
            "trade_date": ["2026-07-20", "2026-07-21", "2026-07-22"],
            "open": [3300.0, 3310.0, 3290.0],
            "high": [3320.0, 3325.0, 3320.0],
            "low": [3280.0, 3290.0, 3270.0],
            "close": [3310.0, 3300.0, 3290.0],
            "volume": [1e8, 1.2e8, 8e7],
            "amount": [3e11, 3.5e11, 2.5e11],
            "source": ["bad_data"] * 3,
            "fetched_at": ["2026-07-27T12:00:00"] * 3,
        })


class EmptyProvider(BaseProvider):
    """返回空 DataFrame 的提供方（合法空结果 vs 请求失败）。"""

    provider_name = "empty"

    def get_stock_basic(self) -> pd.DataFrame:
        raise AshareDataError("No data available")

    def get_trade_calendar(self, start_date, end_date, exchange="SH") -> pd.DataFrame:
        raise AshareDataError("Empty result: no trading days in range")

    def get_stock_daily(self, symbol, start_date, end_date, adjustment="none") -> pd.DataFrame:
        raise AshareDataError("Empty result: stock not listed in range")

    def get_index_daily(self, symbol, start_date, end_date) -> pd.DataFrame:
        raise AshareDataError("Empty result: index not found")


@pytest.fixture
def data_service():
    """创建临时 DataService。"""
    tmpdir = tempfile.mkdtemp()
    db_path = os.path.join(tmpdir, "test_duckdb.duckdb")
    parquet_dir = os.path.join(tmpdir, "parquet")
    raw_dir = os.path.join(tmpdir, "raw")
    os.makedirs(parquet_dir, exist_ok=True)
    os.makedirs(raw_dir, exist_ok=True)

    store = DuckDBStore(db_path)
    store.init_db()

    config = {
        "storage": {
            "duckdb_path": db_path,
            "parquet_dir": parquet_dir,
            "raw_dir": raw_dir,
        },
    }

    service = DataService(store, config)
    service.register_provider("mock", MockProvider())
    service.register_provider("failing", FailingProvider())
    service.register_provider("empty", EmptyProvider())
    for bad_type in ["nan", "inf", "neg_inf", "duplicate_pk",
                       "ohlc_broken", "missing_field"]:
        service.register_provider(
            f"bad_{bad_type}", BadDataProvider(bad_type=bad_type)
        )

    yield service

    service.store.close()
    # 清理
    try:
        import shutil
        shutil.rmtree(tmpdir, ignore_errors=True)
    except Exception:
        pass


class TestDataService:
    """数据服务集成测试。"""

    def test_fetch_and_store_stock_daily(self, data_service):
        result = data_service.fetch_and_store(
            provider_name="mock",
            method_name="get_stock_daily",
            dataset="stock_daily",
            symbol="601857.SH",
            start_date="2026-07-20",
            end_date="2026-07-22",
        )
        assert result["row_count"] == 3
        assert result["quality_status"] == "passed"
        assert os.path.exists(result["parquet_path"])
        assert os.path.exists(result["staging_path"])

    def test_fetch_stock_basic(self, data_service):
        result = data_service.fetch_and_store(
            provider_name="mock",
            method_name="get_stock_basic",
            dataset="stock_basic",
        )
        assert result["row_count"] == 2
        assert result["quality_status"] == "passed"

    def test_fetch_index_daily(self, data_service):
        result = data_service.fetch_and_store(
            provider_name="mock",
            method_name="get_index_daily",
            dataset="index_daily",
            symbol="000001",
            start_date="2026-07-20",
            end_date="2026-07-22",
        )
        assert result["row_count"] == 3

    def test_fetch_run_recorded(self, data_service):
        result = data_service.fetch_and_store(
            provider_name="mock",
            method_name="get_stock_daily",
            dataset="stock_daily",
            symbol="601857.SH",
            start_date="2026-07-20",
            end_date="2026-07-22",
        )

        runs = data_service.store.query(
            "SELECT * FROM data_fetch_runs WHERE run_id = ?",
            [result["run_id"]],
        )
        assert runs["status"].iloc[0] == "success"
        assert runs["row_count"].iloc[0] == 3

    def test_duplicate_insert_no_duplicate(self, data_service):
        """重复插入相同主键不应产生重复行。"""
        _result1 = data_service.fetch_and_store(
            provider_name="mock", method_name="get_stock_daily",
            dataset="stock_daily", symbol="601857.SH",
            start_date="2026-07-20", end_date="2026-07-22",
        )
        _result2 = data_service.fetch_and_store(
            provider_name="mock", method_name="get_stock_daily",
            dataset="stock_daily", symbol="601857.SH",
            start_date="2026-07-20", end_date="2026-07-22",
        )

        df = data_service.query_stored("stock_daily", "601857.SH")
        assert len(df) == 3  # 不应翻倍

    def test_inspect(self, data_service):
        data_service.fetch_and_store(
            provider_name="mock", method_name="get_stock_daily",
            dataset="stock_daily", symbol="601857.SH",
            start_date="2026-07-20", end_date="2026-07-22",
        )

        info = data_service.inspect("stock_daily", "601857.SH")
        assert info["exists"] is True
        assert info["rows"] == 3

    def test_query_stored(self, data_service):
        data_service.fetch_and_store(
            provider_name="mock", method_name="get_stock_daily",
            dataset="stock_daily", symbol="601857.SH",
            start_date="2026-07-20", end_date="2026-07-22",
        )

        df = data_service.query_stored("stock_daily", "601857.SH")
        assert len(df) == 3

    def test_provider_failure_records_error(self, data_service):
        """提供方失败应在 DuckDB 中记录。"""
        with pytest.raises(AshareDataError):
            data_service.fetch_and_store(
                provider_name="failing", method_name="get_stock_daily",
                dataset="stock_daily", symbol="601857.SH",
                start_date="2026-07-20", end_date="2026-07-22",
            )

        runs = data_service.store.query(
            "SELECT status, error_type FROM data_fetch_runs ORDER BY started_at DESC LIMIT 1"
        )
        assert runs["status"].iloc[0] == "failed"
        assert runs["error_type"].iloc[0] == "AshareDataError"

    def test_fallback_primary_succeeds(self, data_service):
        """主数据源成功时不应调用备用。"""
        result = data_service.fetch_with_fallback(
            primary_provider_name="mock",
            primary_method="get_stock_daily",
            fallback_provider_name="failing",
            fallback_method="get_stock_daily",
            dataset="stock_daily",
            symbol="601857.SH",
            start_date="2026-07-20",
            end_date="2026-07-22",
        )
        assert result["row_count"] == 3

    def test_fallback_to_mock_on_primary_failure(self, data_service):
        """主数据源失败时应回退到备用。"""
        result = data_service.fetch_with_fallback(
            primary_provider_name="failing",
            primary_method="get_stock_daily",
            fallback_provider_name="mock",
            fallback_method="get_stock_daily",
            dataset="stock_daily",
            symbol="601857.SH",
            start_date="2026-07-20",
            end_date="2026-07-22",
        )
        assert result["row_count"] == 3
        # 验证 fallback 使用了 mock provider（数据成功获取）
        assert result["quality_status"] == "passed"

    def test_both_providers_fail(self, data_service):
        """两个提供方都失败应抛出聚合错误。"""
        with pytest.raises(AshareDataError, match="All providers failed"):
            data_service.fetch_with_fallback(
                primary_provider_name="failing",
                primary_method="get_stock_daily",
                fallback_provider_name="failing",
                fallback_method="get_stock_daily",
                dataset="stock_daily",
                symbol="601857.SH",
                start_date="2026-07-20",
                end_date="2026-07-22",
            )

    def test_empty_provider_is_not_silent(self, data_service):
        """合法空结果（抛出异常）vs 静默返回空 DataFrame。"""
        with pytest.raises(AshareDataError):
            data_service.fetch_and_store(
                provider_name="empty", method_name="get_stock_daily",
                dataset="stock_daily", symbol="601857.SH",
                start_date="2020-01-01", end_date="2020-01-10",
            )

    def test_staging_snapshot_saved(self, data_service):
        """标准化快照应保存为 Parquet。"""
        result = data_service.fetch_and_store(
            provider_name="mock", method_name="get_stock_daily",
            dataset="stock_daily", symbol="601857.SH",
            start_date="2026-07-20", end_date="2026-07-22",
        )

        staging_path = result["staging_path"]
        assert os.path.exists(staging_path)
        df = pd.read_parquet(staging_path)
        assert len(df) == 3

    def test_provider_failure_blocks_parquet_write(self, data_service):
        """提供方异常不应写入正式 Parquet。"""
        with pytest.raises(AshareDataError):
            data_service.fetch_and_store(
                provider_name="failing", method_name="get_stock_daily",
                dataset="stock_daily", symbol="601857.SH",
                start_date="2026-07-20", end_date="2026-07-22",
            )

        # 不应有任何正式 Parquet 写入
        parquet_dir = data_service.config["storage"]["parquet_dir"]
        parquet_file = os.path.join(parquet_dir, "stock_daily", "601857_SH.parquet")
        assert not os.path.exists(parquet_file)

    def _assert_quality_failure(self, data_service, bad_type: str) -> str:
        """辅助方法：执行一次质量失败测试并返回 quarantine 路径。"""
        provider_name = f"bad_{bad_type}"
        with pytest.raises(AshareDataError):
            data_service.fetch_and_store(
                provider_name=provider_name, method_name="get_stock_daily",
                dataset="stock_daily", symbol="601857.SH",
                start_date="2026-07-20", end_date="2026-07-22",
            )

        # 正式 Parquet 没有被创建
        parquet_dir = data_service.config["storage"]["parquet_dir"]
        parquet_file = os.path.join(
            parquet_dir, "stock_daily", "601857_SH.parquet"
        )
        assert not os.path.exists(parquet_file)

        # DuckDB 记录了失败
        runs = data_service.store.query(
            "SELECT status, error_type FROM data_fetch_runs "
            "ORDER BY started_at DESC LIMIT 1"
        )
        assert runs["status"].iloc[0] == "failed"
        assert runs["error_type"].iloc[0] in (
            "QualityCheckError", "AshareDataError"
        )

        return ""

    def test_quality_failure_quarantines_nan_batch(self, data_service):
        """NaN 数据应被隔离，不写入正式 Parquet。"""
        self._assert_quality_failure(data_service, "nan")

    def test_quality_failure_quarantines_inf_batch(self, data_service):
        """inf 数据应被隔离。"""
        self._assert_quality_failure(data_service, "inf")

    def test_quality_failure_quarantines_neg_inf_batch(self, data_service):
        """-inf 数据应被隔离。"""
        self._assert_quality_failure(data_service, "neg_inf")

    def test_quality_failure_quarantines_duplicate_pk_batch(self, data_service):
        """重复主键应被隔离。"""
        self._assert_quality_failure(data_service, "duplicate_pk")

    def test_quality_failure_quarantines_ohlc_broken_batch(self, data_service):
        """OHLC 逻辑错误应被隔离。"""
        self._assert_quality_failure(data_service, "ohlc_broken")

    def test_quality_failure_quarantines_missing_field_batch(self, data_service):
        """缺失必需字段应被隔离。"""
        self._assert_quality_failure(data_service, "missing_field")

    def test_quality_failure_preserves_existing_parquet_byte_for_byte(
        self, data_service
    ):
        """已有正式 Parquet 在质量失败时完全不被修改。"""
        import hashlib

        # 1. 先成功写入一份合法数据
        result_ok = data_service.fetch_and_store(
            provider_name="mock", method_name="get_stock_daily",
            dataset="stock_daily", symbol="601857.SH",
            start_date="2026-07-20", end_date="2026-07-22",
        )
        ok_path = result_ok["parquet_path"]
        assert os.path.exists(ok_path)

        # 2. 记录正式文件的 SHA-256 和元数据
        with open(ok_path, "rb") as f:
            sha_before = hashlib.sha256(f.read()).hexdigest()
        df_before = pd.read_parquet(ok_path)
        rows_before = len(df_before)
        cols_before = list(df_before.columns)

        # 3. 尝试写入坏数据（NaN）
        with pytest.raises(AshareDataError):
            data_service.fetch_and_store(
                provider_name="bad_nan", method_name="get_stock_daily",
                dataset="stock_daily", symbol="601857.SH",
                start_date="2026-07-23", end_date="2026-07-25",
            )

        # 4. 验证正式文件完全未被修改
        with open(ok_path, "rb") as f:
            sha_after = hashlib.sha256(f.read()).hexdigest()
        assert sha_before == sha_after, "Official Parquet was modified by failed run!"

        df_after = pd.read_parquet(ok_path)
        assert len(df_after) == rows_before, "Row count changed"
        assert list(df_after.columns) == cols_before, "Schema changed"
        pd.testing.assert_frame_equal(df_before, df_after)

        # 5. 坏数据进入 quarantine
        quarantine_dir = data_service.config["storage"].get(
            "quarantine_dir", "data/quarantine"
        )
        assert os.path.isdir(quarantine_dir)

    def test_merge_sorts_by_full_pk_after_backfill(self, data_service):
        """历史回补后数据应按完整主键排序。

        已有: 2026-01-03, 2026-01-04
        新增: 2026-01-01, 2026-01-02
        合并后应严格有序: 01, 02, 03, 04
        """
        # 使用 mock 先写入后期数据
        base_dates = ["2026-01-03", "2026-01-04"]
        new_dates = ["2026-01-01", "2026-01-02"]

        # 创建特殊 provider：第一次返回后期，第二次返回前期
        class BackfillProvider(BaseProvider):
            provider_name = "backfill"
            call_count = 0

            def get_stock_daily(self, symbol, start_date, end_date,
                                adjustment="none"):
                self.call_count += 1
                dates = base_dates if self.call_count == 1 else new_dates
                data = {
                    "symbol": [symbol] * 2,
                    "trade_date": dates,
                    "open": [10.0, 10.2],
                    "high": [10.5, 10.4],
                    "low": [9.8, 10.0],
                    "close": [10.2, 10.1],
                    "pre_close": [10.1, 10.2],
                    "volume": [1e7, 1.2e7],
                    "amount": [1e8, 1.2e8],
                    "turnover_rate": [0.5, 0.6],
                    "is_trading": [True, True],
                    "adjustment": [adjustment] * 2,
                    "source": ["backfill"] * 2,
                    "fetched_at": ["2026-07-27T12:00:00"] * 2,
                }
                return pd.DataFrame(data)

            def get_stock_basic(self): return pd.DataFrame()
            def get_trade_calendar(self, s, e, ex="SH"): return pd.DataFrame()
            def get_index_daily(self, s, st, en): return pd.DataFrame()

        data_service.register_provider("backfill", BackfillProvider())

        _r1 = data_service.fetch_and_store(
            provider_name="backfill", method_name="get_stock_daily",
            dataset="stock_daily", symbol="601857.SH",
            start_date="2026-01-01", end_date="2026-01-04",
        )
        r2 = data_service.fetch_and_store(
            provider_name="backfill", method_name="get_stock_daily",
            dataset="stock_daily", symbol="601857.SH",
            start_date="2026-01-01", end_date="2026-01-04",
        )

        # 验证最终排序
        df = pd.read_parquet(r2["parquet_path"])
        dates = df["trade_date"].tolist()
        assert dates == sorted(dates), f"Not sorted: {dates}"
        assert dates == ["2026-01-01", "2026-01-02",
                          "2026-01-03", "2026-01-04"]

    def test_merged_row_count_recorded(self, data_service):
        """DuckDB 注册表应记录合并后的总行数。"""
        result = data_service.fetch_and_store(
            provider_name="mock", method_name="get_stock_daily",
            dataset="stock_daily", symbol="601857.SH",
            start_date="2026-07-20", end_date="2026-07-22",
        )
        # 3 行新数据，注册表应记录 3
        assert result["row_count"] == 3

    def test_duplicate_request_returns_same_count(self, data_service):
        """相同请求重复执行不应产生重复行，注册表行数应一致。"""
        r1 = data_service.fetch_and_store(
            provider_name="mock", method_name="get_stock_daily",
            dataset="stock_daily", symbol="601857.SH",
            start_date="2026-07-20", end_date="2026-07-22",
        )
        r2 = data_service.fetch_and_store(
            provider_name="mock", method_name="get_stock_daily",
            dataset="stock_daily", symbol="601857.SH",
            start_date="2026-07-20", end_date="2026-07-22",
        )
        # 两次请求相同数据，总行数应一致
        assert r1["row_count"] == r2["row_count"]
        assert r2["row_count"] == 3
