"""AKShare 免费数据适配器。

第一版优先负责：
- 指数历史日线
- 必要的备用公开数据

要求：
- 中文字段做集中映射
- 检查必需字段是否存在
- 字段变化时明确失败
- 不允许字段缺失后悄悄生成错误数据
"""

from __future__ import annotations

import logging
from datetime import datetime

import akshare as ak
import pandas as pd

from ashare_research.exceptions import (
    AshareDataError,
    EmptyResultError,
    FieldMissingError,
    NetworkError,
)
from ashare_research.models import to_standard_code
from ashare_research.providers.base import BaseProvider

logger = logging.getLogger(__name__)

# AKShare 字段映射（中→英）
_INDEX_DAILY_COLUMNS: dict[str, str] = {
    "date": "trade_date",
    "open": "open",
    "high": "high",
    "low": "low",
    "close": "close",
    "volume": "volume",
    "outstanding_share": None,  # 不保留
    "turnover": None,
}

# 备用映射（不同版本字段名可能不同）
_INDEX_DAILY_ALIASES: dict[str, str] = {
    "日期": "date",
    "开盘": "open",
    "最高": "high",
    "最低": "low",
    "收盘": "close",
    "成交量": "volume",
    "成交额": "amount",
}

# 指数日线必需字段（标准化前，原始字段）
_REQUIRED_INDEX_FIELDS = ["date", "open", "high", "low", "close"]


class AKShareProvider(BaseProvider):
    """AKShare 数据提供方。"""

    provider_name = "akshare"

    def _normalize_index_fields(self, df: pd.DataFrame) -> pd.DataFrame:
        """将 AKShare 的中文字段名映射为英文，并检查必需字段。"""
        # 先做别名映射
        df = df.rename(columns=_INDEX_DAILY_ALIASES)

        # 检查必需字段
        missing = [f for f in _REQUIRED_INDEX_FIELDS if f not in df.columns]
        if missing:
            available = list(df.columns)
            raise FieldMissingError(
                missing_fields=missing,
                source=f"AKShare (available: {available})",
            )

        return df

    # ── 接口实现 ────────────────────────────────────────────

    def get_stock_basic(self) -> pd.DataFrame:
        """AKShare 第一版不用于股票基础信息。"""
        raise EmptyResultError(
            "AKShare stock basic not implemented in phase 1. Use baostock provider."
        )

    def get_trade_calendar(
        self, start_date: str, end_date: str, exchange: str = "SH"
    ) -> pd.DataFrame:
        """AKShare 第一版不用于交易日历。"""
        raise EmptyResultError(
            "AKShare trade calendar not implemented in phase 1. Use baostock provider."
        )

    def get_stock_daily(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        adjustment: str = "none",
    ) -> pd.DataFrame:
        """通过 AKShare 获取个股日线（备用）。"""
        now = datetime.now().isoformat()
        std_code = to_standard_code(symbol)

        try:
            # AKShare 使用不带后缀的代码格式
            digits = std_code.split(".")[0]

            adjust_param = adjustment if adjustment != "none" else ""

            df = ak.stock_zh_a_hist(
                symbol=digits,
                period="daily",
                start_date=start_date.replace("-", ""),
                end_date=end_date.replace("-", ""),
                adjust=adjust_param if adjust_param else "",
            )

            if df is None or df.empty:
                raise EmptyResultError(
                    f"No stock daily data from AKShare for {symbol}"
                )

            # 标准化
            df = df.copy()
            df = df.rename(columns={
                "日期": "trade_date",
                "开盘": "open",
                "最高": "high",
                "最低": "low",
                "收盘": "close",
                "成交量": "volume",
                "成交额": "amount",
                "换手率": "turnover_rate",
            })

            # 检查必需字段
            required = ["trade_date", "open", "high", "low", "close", "volume", "amount"]
            missing = [f for f in required if f not in df.columns]
            if missing:
                raise FieldMissingError(
                    missing_fields=missing,
                    source="AKShare stock_zh_a_hist",
                )

            # 类型转换
            for col in ["open", "high", "low", "close"]:
                df[col] = pd.to_numeric(df[col], errors="coerce")
            df["volume"] = pd.to_numeric(df["volume"], errors="coerce")
            df["amount"] = pd.to_numeric(df["amount"], errors="coerce")

            df["symbol"] = std_code
            df["adjustment"] = adjustment
            df["source"] = self.provider_name
            df["fetched_at"] = now

            # 添加缺失字段的默认值
            if "pre_close" not in df.columns:
                df["pre_close"] = None
            if "is_trading" not in df.columns:
                df["is_trading"] = True

            keep_cols = [
                "symbol", "trade_date", "open", "high", "low", "close",
                "pre_close", "volume", "amount", "turnover_rate",
                "is_trading", "adjustment", "source", "fetched_at",
            ]
            return df[[c for c in keep_cols if c in df.columns]]

        except (AshareDataError, FieldMissingError, EmptyResultError):
            raise
        except Exception as e:
            raise NetworkError(f"AKShare stock daily request failed: {e}") from e

    def get_index_daily(
        self, symbol: str, start_date: str, end_date: str
    ) -> pd.DataFrame:
        """通过 AKShare 获取指数日线。

        Args:
            symbol: 指数代码，如 000001（上证指数）, 399001（深证成指）
        """
        now = datetime.now().isoformat()

        try:
            df = ak.stock_zh_index_daily(symbol=f"sh{symbol}")

            if df is None or df.empty:
                raise EmptyResultError(
                    f"No index daily data from AKShare for {symbol}"
                )

            df = self._normalize_index_fields(df)

            # 标准化列名：date → trade_date
            df = df.rename(columns={"date": "trade_date"})

            # 类型转换
            for col in ["open", "high", "low", "close"]:
                df[col] = pd.to_numeric(df[col], errors="coerce")
            df["volume"] = pd.to_numeric(df["volume"], errors="coerce")
            df["amount"] = pd.to_numeric(df.get("amount", 0), errors="coerce")

            # 过滤日期范围
            df["trade_date"] = df["trade_date"].astype(str)
            mask = (df["trade_date"] >= start_date) & (df["trade_date"] <= end_date)
            df = df[mask]

            if df.empty:
                raise EmptyResultError(
                    f"No index daily data in range {start_date} to {end_date} for {symbol}"
                )

            df["symbol"] = symbol
            df["source"] = self.provider_name
            df["fetched_at"] = now

            if "amount" not in df.columns:
                df["amount"] = 0.0

            keep_cols = [
                "symbol", "trade_date", "open", "high", "low", "close",
                "volume", "amount", "source", "fetched_at",
            ]
            return df[keep_cols].reset_index(drop=True)

        except (AshareDataError, FieldMissingError, EmptyResultError):
            raise
        except Exception as e:
            raise NetworkError(f"AKShare index daily request failed: {e}") from e
