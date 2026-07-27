"""数据提供方统一接口。"""

from abc import ABC, abstractmethod

import pandas as pd


class BaseProvider(ABC):
    """数据提供方抽象基类。

    所有数据源必须实现此接口，返回标准化的 DataFrame。
    不直接写数据库，不把上游异常静默转为空 DataFrame。
    """

    provider_name: str = "base"

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
