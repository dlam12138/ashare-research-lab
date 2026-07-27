"""数据提供方统一接口。"""

from __future__ import annotations

import os
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path

import pandas as pd

from ashare_research.exceptions import RawPersistenceError


class BaseProvider(ABC):
    """数据提供方抽象基类。

    所有数据源必须实现此接口，返回标准化的 DataFrame。
    不直接写数据库，不把上游异常静默转为空 DataFrame。

    子类可调用 _save_raw_response() 在上游响应被标准化前保存原始快照。
    """

    provider_name: str = "base"

    def __init__(self, raw_dir: str = ""):
        """初始化提供方。

        Args:
            raw_dir: 原始响应保存根目录，为空则不保存。
        """
        self.raw_dir = raw_dir
        self._last_raw_path: str = ""

    @property
    def last_raw_path(self) -> str:
        """最近一次抓取保存的原始响应路径。"""
        return self._last_raw_path

    def reset_last_raw_path(self) -> None:
        """清空上次 raw 路径，避免新方法遗漏保存时复用旧路径。"""
        self._last_raw_path = ""

    def _save_raw_response(
        self, df: pd.DataFrame, dataset: str, symbol: str = ""
    ) -> str:
        """在标准化之前保存上游原始响应。

        保留上游字段名、上游原始单位和格式，不做任何转换。
        使用原子写入（临时文件 + 重命名）。

        Returns:
            str: 原始文件路径

        Raises:
            RawPersistenceError: raw_dir 已配置但写入失败
        """
        if not self.raw_dir:
            self._last_raw_path = ""
            return ""

        target_dir = Path(self.raw_dir) / self.provider_name / dataset
        target_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        safe_symbol = symbol.replace(".", "_") if symbol else "all"
        filename = f"{safe_symbol}_{timestamp}.parquet"
        final_path = target_dir / filename

        # 原子写入
        tmp_path = target_dir / f".{filename}.tmp"
        try:
            df.to_parquet(tmp_path, index=False, engine="pyarrow")
            os.replace(tmp_path, str(final_path))
            self._last_raw_path = str(final_path)
        except Exception as e:
            if tmp_path.exists():
                tmp_path.unlink()
            self._last_raw_path = ""
            raise RawPersistenceError(
                f"Failed to save raw response to {final_path}: {e}"
            ) from e

        return self._last_raw_path

    @abstractmethod
    def get_stock_basic(self) -> pd.DataFrame:
        """获取股票基础信息。

        Returns:
            DataFrame with columns:
                symbol, exchange, name, list_date, delist_date, status, source, fetched_at
        """
        ...

    @abstractmethod
    def get_trade_calendar(
        self, start_date: str, end_date: str, exchange: str = "SH"
    ) -> pd.DataFrame:
        """获取交易日历。

        Returns:
            DataFrame with columns:
                trade_date, exchange, is_open, source, fetched_at
        """
        ...

    @abstractmethod
    def get_stock_daily(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        adjustment: str = "none",
    ) -> pd.DataFrame:
        """获取个股日线。

        Returns:
            DataFrame with columns:
                symbol, trade_date, open, high, low, close, pre_close,
                volume, amount, turnover_rate, is_trading, adjustment,
                source, fetched_at
        """
        ...

    @abstractmethod
    def get_index_daily(
        self, symbol: str, start_date: str, end_date: str
    ) -> pd.DataFrame:
        """获取指数日线。

        Returns:
            DataFrame with columns:
                symbol, trade_date, open, high, low, close,
                volume, amount, source, fetched_at
        """
        ...
