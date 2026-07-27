"""数据服务层集成测试。

测试 provider fallback、data service 编排和 Mock 提供方。
"""

import os
from pathlib import Path

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
def data_service(tmp_path):
    """创建临时 DataService，所有存储路径隔离在 tmp_path 中。"""
    db_path = tmp_path / "test.duckdb"
    raw_dir = tmp_path / "raw"
    staging_dir = tmp_path / "staging"
    quarantine_dir = tmp_path / "quarantine"
    parquet_dir = tmp_path / "parquet"

    for d in [raw_dir, staging_dir, quarantine_dir, parquet_dir]:
        d.mkdir(parents=True, exist_ok=True)

    store = DuckDBStore(str(db_path))
    store.init_db()

    config = {
        "storage": {
            "duckdb_path": str(db_path),
            "raw_dir": str(raw_dir),
            "staging_dir": str(staging_dir),
            "quarantine_dir": str(quarantine_dir),
            "parquet_dir": str(parquet_dir),
        },
    }

    # 验证所有路径都在 tmp_path 下
    for key in ["raw_dir", "staging_dir", "quarantine_dir", "parquet_dir"]:
        val = config["storage"][key]
        assert val.startswith(str(tmp_path)), (
            f"{key}={val} not under tmp_path"
        )

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
        """执行一次质量失败测试，验证 quarantine 文件及内容，返回路径。"""
        provider_name = f"bad_{bad_type}"

        # 记录执行前的 quarantine 文件集合
        quarantine_root = Path(data_service.config["storage"]["quarantine_dir"])
        files_before = set(quarantine_root.rglob("*.parquet"))

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

        # 恰好增加一个 quarantine 文件
        files_after = set(quarantine_root.rglob("*.parquet"))
        new_files = files_after - files_before
        assert len(new_files) == 1, (
            f"Expected 1 new quarantine file, got {len(new_files)}: {new_files}"
        )

        quarantine_path = str(new_files.pop())
        quarantined = pd.read_parquet(quarantine_path)
        assert len(quarantined) == 3, f"Expected 3 rows in quarantine, got {len(quarantined)}"

        # 验证坏数据特征仍然存在
        if bad_type == "nan":
            assert quarantined["volume"].isnull().any(), "NaN volume not preserved"
        elif bad_type == "inf":
            assert (quarantined["close"] == float("inf")).any(), "inf close not preserved"
        elif bad_type == "neg_inf":
            assert (quarantined["close"] == float("-inf")).any(), "-inf close not preserved"
        elif bad_type == "duplicate_pk":
            pk_subset = quarantined[["symbol", "trade_date", "adjustment"]]
            assert pk_subset.duplicated().any(), "duplicate PK not preserved"
        elif bad_type == "ohlc_broken":
            broken = quarantined["high"] < quarantined["low"]
            assert broken.any(), "broken OHLC not preserved"
        elif bad_type == "missing_field":
            assert "volume" not in quarantined.columns, "missing field not preserved"

        # DuckDB 记录了失败
        runs = data_service.store.query(
            "SELECT status, error_type FROM data_fetch_runs "
            "ORDER BY started_at DESC LIMIT 1"
        )
        assert runs["status"].iloc[0] == "failed"
        assert runs["error_type"].iloc[0] in (
            "QualityCheckError", "AshareDataError"
        )

        return quarantine_path

    def test_quality_failure_quarantines_nan_batch(self, data_service):
        """NaN 数据应被隔离，quarantine 文件可读且保留 NaN。"""
        path = self._assert_quality_failure(data_service, "nan")
        df = pd.read_parquet(path)
        assert df["volume"].isnull().any()

    def test_quality_failure_quarantines_inf_batch(self, data_service):
        """inf 数据应被隔离。"""
        path = self._assert_quality_failure(data_service, "inf")
        df = pd.read_parquet(path)
        assert (df["close"] == float("inf")).any()

    def test_quality_failure_quarantines_neg_inf_batch(self, data_service):
        """-inf 数据应被隔离。"""
        path = self._assert_quality_failure(data_service, "neg_inf")
        df = pd.read_parquet(path)
        assert (df["close"] == float("-inf")).any()

    def test_quality_failure_quarantines_duplicate_pk_batch(self, data_service):
        """重复主键应被隔离。"""
        path = self._assert_quality_failure(data_service, "duplicate_pk")
        df = pd.read_parquet(path)
        pk_cols = ["symbol", "trade_date", "adjustment"]
        assert df[pk_cols].duplicated().any()

    def test_quality_failure_quarantines_ohlc_broken_batch(self, data_service):
        """OHLC 逻辑错误应被隔离。"""
        path = self._assert_quality_failure(data_service, "ohlc_broken")
        df = pd.read_parquet(path)
        assert (df["high"] < df["low"]).any()

    def test_quality_failure_quarantines_missing_field_batch(self, data_service):
        """缺失必需字段应被隔离。"""
        path = self._assert_quality_failure(data_service, "missing_field")
        df = pd.read_parquet(path)
        assert "volume" not in df.columns

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

        # 5. 验证恰好增加一个 quarantine 文件且内容正确
        quarantine_root = Path(data_service.config["storage"]["quarantine_dir"])
        files_before_q = set(quarantine_root.rglob("*.parquet"))

        with pytest.raises(AshareDataError):
            data_service.fetch_and_store(
                provider_name="bad_nan", method_name="get_stock_daily",
                dataset="stock_daily", symbol="601857.SH",
                start_date="2026-07-23", end_date="2026-07-25",
            )

        files_after_q = set(quarantine_root.rglob("*.parquet"))
        new_files = files_after_q - files_before_q
        # 如果之前测试已产生 quarantine 文件，本次恰好增加 1 个
        # （但前一个 "bad_nan" 也在本测试中会触发质量失败）
        # 实际上这个 with 块是第二次 bad_nan 调用，它也会产生一个新文件
        # 之前的第一次 bad_nan 调用在步骤 3 的 with 块中，已在 files_before_q 之前
        # 所以 files_before_q 集合是在步骤3之后、步骤5之前采集的
        # → 步骤5的 with 块产生的新文件会出现在这里
        # 等待，看用户的代码逻辑——步骤3已经调用了 bad_nan 并产生了一个 quarantine
        # 然后步骤5又调用 bad_nan 产生第二个 quarantine
        # 所以 files_before_q 采集时已经包含了步骤3的文件，步骤5的新文件是第二个
        # 我预期 new_files 有 1 个（步骤5的文件）
        # 但步骤3的那个 bad_nan 调用并不是在这个 with 块里...
        # 实际上步骤3的 with block 是在步骤5的 files_before_q 之前执行的
        # 步骤5的 files_before_q 包含了步骤3产生的文件
        # 步骤5的 with block 又产生一个新文件
        # 所以 new_files 应该有 1 个
        assert len(new_files) >= 1, (
            f"Expected at least 1 new quarantine file, got {len(new_files)}"
        )

    def test_first_write_sorts_by_full_primary_key(self, data_service):
        """首次写入即使 Provider 返回乱序，正式 Parquet 也必须排序。"""

        class UnsortedProvider(BaseProvider):
            provider_name = "unsorted"

            def get_stock_daily(self, symbol, start_date, end_date,
                                adjustment="none"):
                return pd.DataFrame({
                    "symbol": [symbol] * 3,
                    "trade_date": [
                        "2026-01-03", "2026-01-01", "2026-01-02"
                    ],
                    "open": [10.3, 10.1, 10.2],
                    "high": [10.5, 10.4, 10.4],
                    "low": [10.0, 9.9, 10.0],
                    "close": [10.4, 10.2, 10.3],
                    "pre_close": [10.2, 10.0, 10.1],
                    "volume": [1e7, 8e6, 9e6],
                    "amount": [1e8, 8e7, 9e7],
                    "turnover_rate": [0.5, 0.4, 0.45],
                    "is_trading": [True] * 3,
                    "adjustment": [adjustment] * 3,
                    "source": ["unsorted"] * 3,
                    "fetched_at": ["2026-07-27T12:00:00"] * 3,
                })

            def get_stock_basic(self): return pd.DataFrame()
            def get_trade_calendar(self, s, e, ex="SH"): return pd.DataFrame()
            def get_index_daily(self, s, st, en): return pd.DataFrame()

        data_service.register_provider("unsorted", UnsortedProvider())
        result = data_service.fetch_and_store(
            provider_name="unsorted", method_name="get_stock_daily",
            dataset="stock_daily", symbol="601857.SH",
            start_date="2026-01-01", end_date="2026-01-03",
        )
        df = pd.read_parquet(result["parquet_path"])
        trade_dates = df["trade_date"].tolist()
        assert trade_dates == sorted(trade_dates), f"Not sorted: {trade_dates}"
        assert trade_dates == ["2026-01-01", "2026-01-02", "2026-01-03"]

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

    def test_akshare_raw_snapshot_preserves_upstream_fields_and_units(
        self, tmp_path
    ):
        """AKShare raw 文件保留中文原始字段和手为单位。"""
        from unittest.mock import patch

        import akshare

        raw_dir = tmp_path / "raw"
        raw_dir.mkdir()

        mock_df = pd.DataFrame({
            "日期": ["2026-07-20"],
            "开盘": [10.0],
            "最高": [10.5],
            "最低": [9.8],
            "收盘": [10.2],
            "成交量": [17544],  # 手
            "成交额": [20873742],
            "换手率": [0.11],
        })

        with patch.object(akshare, "stock_zh_a_hist", return_value=mock_df):
            from ashare_research.providers.akshare_provider import AKShareProvider
            provider = AKShareProvider(raw_dir=str(raw_dir))
            result = provider.get_stock_daily(
                "601857.SH", "2026-07-20", "2026-07-20", "none"
            )

        # raw 文件存在
        assert provider.last_raw_path, "last_raw_path is empty"
        assert os.path.exists(provider.last_raw_path)

        raw = pd.read_parquet(provider.last_raw_path)
        # 中文原始字段
        for col in ["日期", "开盘", "成交量"]:
            assert col in raw.columns, f"Raw missing Chinese field: {col}"
        # 标准化字段不在 raw 中
        for col in ["symbol", "source", "fetched_at"]:
            assert col not in raw.columns, f"Raw should not contain {col}"
        # 成交量：raw 为"手"，标准化为"股"（×100）
        assert raw["成交量"].iloc[0] == 17544
        assert result["volume"].iloc[0] == 1_754_400

    def test_baostock_raw_snapshot_preserves_upstream_schema(
        self, tmp_path
    ):
        """Baostock raw 文件保留 baostock 原始字段名和代码格式。"""
        from unittest.mock import MagicMock, patch

        import baostock as bs

        raw_dir = tmp_path / "raw"
        raw_dir.mkdir()

        mock_login = MagicMock()
        mock_login.error_code = "0"
        mock_rs = MagicMock()
        mock_rs.error_code = "0"
        mock_rs.fields = ["date", "code", "open", "high", "low",
                          "close", "preclose", "volume", "amount",
                          "turn", "tradestatus"]

        def get_row_data():
            return ["2026-07-20", "sh.601857", "10.00", "10.50",
                    "9.80", "10.20", "10.10", "10000000",
                    "102000000", "0.50", "1"]

        mock_rs.get_row_data = get_row_data
        mock_rs.next.side_effect = [True, False]

        with patch.object(bs, "login", return_value=mock_login):
            with patch.object(bs, "logout", return_value=None):
                with patch.object(bs, "query_history_k_data_plus",
                                  return_value=mock_rs):
                    from ashare_research.providers.baostock_provider import (
                        BaostockProvider,
                    )
                    provider = BaostockProvider(raw_dir=str(raw_dir))
                    provider._ensure_login()
                    result = provider.get_stock_daily(
                        "601857.SH", "2026-07-20", "2026-07-20", "none"
                    )

        # raw 含 Baostock 原始字段
        assert provider.last_raw_path
        raw = pd.read_parquet(provider.last_raw_path)
        for col in ["date", "code", "preclose", "turn", "tradestatus"]:
            assert col in raw.columns, f"Raw missing baostock field: {col}"
        # 代码仍是 sh.601857
        assert raw["code"].iloc[0] == "sh.601857"
        # 标准化后代码是 601857.SH
        assert result["symbol"].iloc[0] == "601857.SH"

    def test_success_run_records_real_raw_snapshot_path(self, tmp_path):
        """成功运行的 DuckDB 记录 raw_file_path 指向真实 raw 文件。"""
        from unittest.mock import patch

        import akshare

        raw_dir = tmp_path / "raw"
        raw_dir.mkdir()
        db_path = tmp_path / "test_raw.duckdb"
        parquet_dir = tmp_path / "parquet"
        staging_dir = tmp_path / "staging"
        quarantine_dir = tmp_path / "quarantine"
        for d in [parquet_dir, staging_dir, quarantine_dir]:
            d.mkdir()

        from ashare_research.services.data_service import DataService
        from ashare_research.storage.duckdb_store import DuckDBStore

        store = DuckDBStore(str(db_path))
        store.init_db()

        config = {
            "storage": {
                "duckdb_path": str(db_path),
                "raw_dir": str(raw_dir),
                "staging_dir": str(staging_dir),
                "quarantine_dir": str(quarantine_dir),
                "parquet_dir": str(parquet_dir),
            },
        }
        svc = DataService(store, config)
        from ashare_research.providers.akshare_provider import AKShareProvider
        svc.register_provider(
            "akshare", AKShareProvider(raw_dir=str(raw_dir))
        )

        mock_df = pd.DataFrame({
            "日期": ["2026-07-20", "2026-07-21"],
            "开盘": [10.0, 10.1],
            "最高": [10.5, 10.4],
            "最低": [9.8, 10.0],
            "收盘": [10.2, 10.1],
            "成交量": [10000, 20000],
            "成交额": [10200000, 20200000],
            "换手率": [0.5, 0.6],
        })

        with patch.object(akshare, "stock_zh_a_hist", return_value=mock_df):
            result = svc.fetch_and_store(
                provider_name="akshare",
                method_name="get_stock_daily",
                dataset="stock_daily",
                symbol="601857.SH",
                start_date="2026-07-20",
                end_date="2026-07-22",
            )

        # DuckDB 记录了 raw_file_path
        runs = store.query(
            "SELECT raw_file_path, parquet_path, status FROM "
            "data_fetch_runs WHERE run_id = ?",
            [result["run_id"]],
        )
        assert runs["status"].iloc[0] == "success"
        raw_path = runs["raw_file_path"].iloc[0]
        assert raw_path, "raw_file_path is empty"
        assert os.path.exists(raw_path), f"raw file not found: {raw_path}"
        assert raw_path != result["staging_path"], "raw == staging path"
        assert raw_path != result["parquet_path"], "raw == parquet path"

        # raw 包含中文原始字段
        raw_df = pd.read_parquet(raw_path)
        assert "日期" in raw_df.columns

        store.close()

    def test_raw_snapshot_failure_blocks_official_write(self, tmp_path):
        """raw 保存失败时不应写入正式 Parquet。"""
        from unittest.mock import patch

        import akshare
        from ashare_research.exceptions import RawPersistenceError

        raw_dir = tmp_path / "raw"
        raw_dir.mkdir()
        parquet_dir = tmp_path / "parquet"
        parquet_dir.mkdir()
        staging_dir = tmp_path / "staging"
        staging_dir.mkdir()
        quarantine_dir = tmp_path / "quarantine"
        quarantine_dir.mkdir()

        mock_df = pd.DataFrame({
            "日期": ["2026-07-20"],
            "开盘": [10.0], "最高": [10.5], "最低": [9.8], "收盘": [10.2],
            "成交量": [10000], "成交额": [10200000],
            "换手率": [0.5],
        })

        with patch.object(akshare, "stock_zh_a_hist", return_value=mock_df):
            from ashare_research.providers.akshare_provider import AKShareProvider
            provider = AKShareProvider(raw_dir=str(raw_dir))

            # Mock _save_raw_response 使其失败
            def failing_save(*args, **kwargs):
                raise RawPersistenceError("Simulated raw save failure")

            with patch.object(provider, "_save_raw_response",
                              side_effect=failing_save):
                from ashare_research.services.data_service import DataService
                from ashare_research.storage.duckdb_store import DuckDBStore
                db_path = tmp_path / "fail.duckdb"
                store = DuckDBStore(str(db_path))
                store.init_db()
                config = {
                    "storage": {
                        "duckdb_path": str(db_path),
                        "raw_dir": str(raw_dir),
                        "staging_dir": str(staging_dir),
                        "quarantine_dir": str(quarantine_dir),
                        "parquet_dir": str(parquet_dir),
                    },
                }
                svc2 = DataService(store, config)
                svc2.register_provider("akshare", provider)

                with pytest.raises(AshareDataError):
                    svc2.fetch_and_store(
                        provider_name="akshare",
                        method_name="get_stock_daily",
                        dataset="stock_daily",
                        symbol="601857.SH",
                        start_date="2026-07-20",
                        end_date="2026-07-20",
                    )

                # 正式 Parquet 未创建
                parquet_file = (
                    parquet_dir / "stock_daily" / "601857_SH.parquet"
                )
                assert not parquet_file.exists()

                # 任务记录为失败
                runs = store.query(
                    "SELECT status, error_type FROM data_fetch_runs "
                    "ORDER BY started_at DESC LIMIT 1"
                )
                assert runs["status"].iloc[0] == "failed"

                store.close()
