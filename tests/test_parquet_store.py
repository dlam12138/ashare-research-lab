"""Parquet 存储层测试。"""

import os
import tempfile

import pandas as pd
import pytest

from ashare_research.exceptions import AshareDataError
from ashare_research.storage.parquet_store import (
    get_parquet_info,
    read_parquet,
    write_parquet,
)


@pytest.fixture
def temp_parquet_dir():
    """创建临时 Parquet 目录。"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def sample_stock_daily_df():
    return pd.DataFrame({
        "symbol": ["601857.SH"] * 5,
        "trade_date": [
            "2026-07-20", "2026-07-21", "2026-07-22",
            "2026-07-23", "2026-07-24",
        ],
        "open": [10.0, 10.2, 10.1, 10.3, 10.0],
        "high": [10.5, 10.4, 10.3, 10.6, 10.2],
        "low": [9.8, 10.0, 9.9, 10.1, 9.7],
        "close": [10.2, 10.1, 10.2, 10.5, 10.0],
        "volume": [1e7, 1.2e7, 8e6, 1.5e7, 9e6],
        "amount": [1e8, 1.2e8, 8e7, 1.5e8, 9e7],
        "adjustment": ["none"] * 5,
        "source": ["test"] * 5,
        "fetched_at": ["2026-07-27"] * 5,
    })


class TestParquetStore:
    """Parquet 存储测试。"""

    def test_write_and_read(self, temp_parquet_dir, sample_stock_daily_df):
        path = write_parquet(
            sample_stock_daily_df,
            temp_parquet_dir,
            "stock_daily",
            "601857.SH",
        )
        assert os.path.exists(path)

        df = read_parquet(temp_parquet_dir, "stock_daily", "601857.SH")
        assert len(df) == 5
        assert list(df.columns) == list(sample_stock_daily_df.columns)

    def test_date_filtering(self, temp_parquet_dir, sample_stock_daily_df):
        write_parquet(sample_stock_daily_df, temp_parquet_dir, "stock_daily", "601857.SH")

        df = read_parquet(
            temp_parquet_dir, "stock_daily", "601857.SH",
            start_date="2026-07-22",
        )
        assert len(df) == 3

        df = read_parquet(
            temp_parquet_dir, "stock_daily", "601857.SH",
            end_date="2026-07-21",
        )
        assert len(df) == 2

    def test_append_mode_dedup(self, temp_parquet_dir, sample_stock_daily_df):
        """追加模式去重：新数据覆盖旧数据。"""
        write_parquet(sample_stock_daily_df, temp_parquet_dir, "stock_daily", "601857.SH")

        # 新数据：部分重叠，部分新增
        new_data = pd.DataFrame({
            "symbol": ["601857.SH"] * 3,
            "trade_date": ["2026-07-24", "2026-07-25", "2026-07-26"],
            "open": [11.0, 11.1, 11.2],
            "high": [11.5, 11.4, 11.5],
            "low": [10.8, 10.9, 11.0],
            "close": [11.3, 11.2, 11.5],
            "volume": [1e7, 1.1e7, 1.2e7],
            "amount": [1.1e8, 1.2e8, 1.3e8],
            "adjustment": ["none"] * 3,
            "source": ["test"] * 3,
            "fetched_at": ["2026-07-28"] * 3,
        })

        write_parquet(
            new_data, temp_parquet_dir, "stock_daily", "601857.SH",
            mode="append",
        )

        df = read_parquet(temp_parquet_dir, "stock_daily", "601857.SH")
        # 5 original - 1 overlap (2026-07-24) + 3 new = 7
        assert len(df) == 7
        # 覆盖行应使用新数据
        overlap = df[df["trade_date"] == "2026-07-24"]
        assert overlap.iloc[0]["close"] == 11.3

    def test_empty_write_fails(self, temp_parquet_dir):
        with pytest.raises(AshareDataError):
            write_parquet(pd.DataFrame(), temp_parquet_dir, "stock_daily", "test.SH")

    def test_get_info(self, temp_parquet_dir, sample_stock_daily_df):
        write_parquet(sample_stock_daily_df, temp_parquet_dir, "stock_daily", "601857.SH")

        info = get_parquet_info(temp_parquet_dir, "stock_daily", "601857.SH")
        assert info["exists"] is True
        assert info["rows"] == 5
        assert info["date_min"] == "2026-07-20"
        assert info["date_max"] == "2026-07-24"

    def test_info_nonexistent(self, temp_parquet_dir):
        info = get_parquet_info(temp_parquet_dir, "stock_daily", "nonexistent.SH")
        assert info["exists"] is False

    def test_index_daily_partition(self, temp_parquet_dir):
        df = pd.DataFrame({
            "symbol": ["000001"] * 3,
            "trade_date": ["2026-07-20", "2026-07-21", "2026-07-22"],
            "open": [3300.0, 3310.0, 3290.0],
            "high": [3320.0, 3325.0, 3310.0],
            "low": [3280.0, 3290.0, 3270.0],
            "close": [3310.0, 3290.0, 3320.0],
            "volume": [1e8, 1.2e8, 8e7],
            "amount": [3e11, 3.5e11, 2.5e11],
            "source": ["test"] * 3,
            "fetched_at": ["2026-07-27"] * 3,
        })
        path = write_parquet(df, temp_parquet_dir, "index_daily", "000001")
        assert os.path.exists(path)
        assert "000001.parquet" in path

    def test_stock_basic_primary_key(self, temp_parquet_dir):
        df = pd.DataFrame({
            "symbol": ["601857.SH", "600519.SH"],
            "exchange": ["SH", "SH"],
            "name": ["中国石油", "贵州茅台"],
            "source": ["test", "test"],
            "fetched_at": ["2026-07-27", "2026-07-27"],
        })
        write_parquet(df, temp_parquet_dir, "stock_basic")
        df_read = read_parquet(temp_parquet_dir, "stock_basic")
        assert len(df_read) == 2
