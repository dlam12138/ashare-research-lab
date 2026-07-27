"""Baostock 免费数据适配器。

负责：
- 股票基础信息
- 交易日历
- A股个股日线

要求：
- 登录和登出有明确生命周期
- 即使请求失败也能安全登出
- 上游错误码必须转成项目异常
- 日期和代码格式验证
"""

from __future__ import annotations

import logging
from datetime import datetime

import baostock as bs
import pandas as pd

from ashare_research.exceptions import (
    AshareDataError,
    AuthenticationError,
    DateRangeError,
    EmptyResultError,
    NetworkError,
)
from ashare_research.models import to_baostock_code
from ashare_research.providers.base import BaseProvider

logger = logging.getLogger(__name__)

# Baostock 字段映射
_STOCK_BASIC_COLUMNS = {
    "code": "symbol",
    "code_name": "name",
    "ipoDate": "list_date",
    "outDate": "delist_date",
    "type": "type",
    "status": "status",
}

_STOCK_DAILY_COLUMNS = {
    "date": "trade_date",
    "code": "symbol",
    "open": "open",
    "high": "high",
    "low": "low",
    "close": "close",
    "preclose": "pre_close",
    "volume": "volume",
    "amount": "amount",
    "turn": "turnover_rate",
    "tradestatus": "is_trading",
    "isST": "is_st",
}

_REQUIRED_DAILY_FIELDS = [
    "date", "code", "open", "high", "low", "close", "preclose", "volume", "amount",
]


class BaostockProvider(BaseProvider):
    """Baostock 数据提供方。"""

    provider_name = "baostock"

    def __init__(self, raw_dir: str = ""):
        super().__init__(raw_dir=raw_dir)
        self._logged_in = False

    def login(self) -> None:
        """登录 Baostock。"""
        try:
            lg = bs.login()
            if lg.error_code != "0":
                raise AuthenticationError(
                    f"Baostock login failed: {lg.error_code} {lg.error_msg}"
                )
            self._logged_in = True
            logger.info("Baostock login successful")
        except Exception as e:
            if isinstance(e, AuthenticationError):
                raise
            raise NetworkError(f"Baostock login network error: {e}") from e

    def logout(self) -> None:
        """安全登出。即使有错也执行。"""
        if self._logged_in:
            try:
                bs.logout()
            except Exception as e:
                logger.warning(f"Baostock logout warning: {e}")
            finally:
                self._logged_in = False
                logger.info("Baostock logout complete")

    def _ensure_login(self) -> None:
        """确保已登录。"""
        if not self._logged_in:
            self.login()

    def _check_response(self, rs: object) -> None:
        """检查 Baostock 响应是否成功。"""
        if rs.error_code != "0":
            msg = rs.error_msg if hasattr(rs, "error_msg") else "Unknown error"
            raise AshareDataError(
                f"Baostock error [{rs.error_code}]: {msg}"
            )

    def _validate_date_format(self, date_str: str) -> None:
        """验证日期格式 YYYY-MM-DD。"""
        try:
            datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError as e:
            raise DateRangeError(
                f"Invalid date format: {date_str}, expected YYYY-MM-DD"
            ) from e

    # ── 接口实现 ────────────────────────────────────────────

    def get_stock_basic(self) -> pd.DataFrame:
        """获取全部A股基础信息。

        过滤条件：仅保留 type=1（股票），排除指数、基金等。
        """
        self._ensure_login()
        now = datetime.now().isoformat()

        try:
            rs = bs.query_stock_basic()
            self._check_response(rs)

            data = []
            while rs.next():
                row = rs.get_row_data()
                data.append(row)

            if not data:
                raise EmptyResultError("No stock basic data returned")

            df = pd.DataFrame(data, columns=rs.fields)
            self._save_raw_response(df, "stock_basic")
            df = df.rename(columns=_STOCK_BASIC_COLUMNS)

            # 仅保留 A 股股票（type=1）
            # Baostock type: 1=股票, 2=指数, 3=其他
            if "type" in df.columns:
                df = df[df["type"] == "1"].copy()

            if df.empty:
                raise EmptyResultError("No A-share stocks after filtering")

            # 标准化代码
            from ashare_research.models import to_standard_code

            df["symbol"] = df["symbol"].apply(to_standard_code)

            # 确定交易所
            df["exchange"] = df["symbol"].str.extract(r"\.(SH|SZ)$")

            # 推断板块（基于代码规则）
            def _classify_board(code: str) -> str:
                code = str(code).split(".")[0]
                if code.startswith("688"):
                    return "kcb"      # 科创板
                elif code.startswith("300") or code.startswith("301"):
                    return "cyb"      # 创业板
                elif code.startswith("8") or code.startswith("4"):
                    return "bj"       # 北交所
                elif code.startswith("6") or code.startswith("9"):
                    return "sh_main"  # 沪市主板
                elif code.startswith("0") or code.startswith("2"):
                    return "sz_main"  # 深市主板
                return "other"

            df["board"] = df["symbol"].apply(_classify_board)

            # 添加元数据
            df["source"] = self.provider_name
            df["fetched_at"] = now

            # 保留必要字段
            keep_cols = [
                "symbol", "exchange", "name", "board", "list_date",
                "delist_date", "status", "source", "fetched_at",
            ]
            return df[keep_cols]

        except Exception:
            self.logout()
            raise

    def get_trade_calendar(
        self, start_date: str, end_date: str, exchange: str = "SH"
    ) -> pd.DataFrame:
        """获取交易日历。"""
        self._ensure_login()
        self._validate_date_format(start_date)
        self._validate_date_format(end_date)
        now = datetime.now().isoformat()

        try:
            rs = bs.query_trade_dates(start_date=start_date, end_date=end_date)
            self._check_response(rs)

            data = []
            while rs.next():
                row = rs.get_row_data()
                data.append(row)

            if not data:
                raise EmptyResultError(
                    f"No trade dates for {start_date} to {end_date}"
                )

            df = pd.DataFrame(data, columns=rs.fields)
            self._save_raw_response(df, "trade_calendar")

            # Baostock 返回 calendar_date 和 is_trading_day(0/1)
            df = df.rename(columns={
                "calendar_date": "trade_date",
                "is_trading_day": "is_open_raw",
            })
            df["is_open"] = df["is_open_raw"] == "1"
            df["exchange"] = exchange
            df["source"] = self.provider_name
            df["fetched_at"] = now

            return df[["trade_date", "exchange", "is_open", "source", "fetched_at"]]

        except Exception:
            self.logout()
            raise

    def get_stock_daily(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        adjustment: str = "none",
    ) -> pd.DataFrame:
        """获取个股日线。"""
        self._ensure_login()
        self._validate_date_format(start_date)
        self._validate_date_format(end_date)

        bs_code = to_baostock_code(symbol)
        now = datetime.now().isoformat()

        # 复权参数：3 = 不复权, 2 = 前复权, 1 = 后复权
        # Baostock 官方文档: https://pypi.org/project/baostock/
        frequency_map = {"none": "d", "qfq": "d", "hfq": "d"}
        adjust_map = {"none": "3", "qfq": "2", "hfq": "1"}

        if adjustment not in frequency_map:
            raise ValueError(
                f"Invalid adjustment: {adjustment}, must be one of: "
                f"{list(frequency_map.keys())}"
            )

        frequency = frequency_map[adjustment]
        adjust_flag = adjust_map[adjustment]

        try:
            rs = bs.query_history_k_data_plus(
                bs_code,
                "date,code,open,high,low,close,preclose,volume,amount,"
                "turn,tradestatus",
                start_date=start_date,
                end_date=end_date,
                frequency=frequency,
                adjustflag=adjust_flag,
            )
            self._check_response(rs)

            data = []
            while rs.next():
                row = rs.get_row_data()
                data.append(row)

            if not data:
                raise EmptyResultError(
                    f"No stock daily data for {symbol} ({start_date} to {end_date})"
                )

            df = pd.DataFrame(data, columns=rs.fields)
            self._save_raw_response(df, "stock_daily", bs_code)
            df = df.rename(columns=_STOCK_DAILY_COLUMNS)

            # 标准化代码
            from ashare_research.models import to_standard_code

            df["symbol"] = df["symbol"].apply(to_standard_code)

            # 类型转换
            for col in ["open", "high", "low", "close", "pre_close",
                         "volume", "amount"]:
                df[col] = pd.to_numeric(df[col], errors="coerce")

            # 换手率
            df["turnover_rate"] = pd.to_numeric(df["turnover_rate"], errors="coerce")

            # 交易状态：1=正常交易
            df["is_trading"] = df["is_trading"] == "1"

            # 复权标记
            df["adjustment"] = adjustment

            # 元数据
            df["source"] = self.provider_name
            df["fetched_at"] = now

            keep_cols = [
                "symbol", "trade_date", "open", "high", "low", "close",
                "pre_close", "volume", "amount", "turnover_rate",
                "is_trading", "adjustment", "source", "fetched_at",
            ]
            return df[keep_cols]

        except Exception:
            self.logout()
            raise

    def get_index_daily(
        self, symbol: str, start_date: str, end_date: str
    ) -> pd.DataFrame:
        """Baostock 不直接支持指数日线，返回 EmptyResultError。"""
        raise EmptyResultError(
            "Baostock does not support index daily data. Use akshare provider."
        )

    def __enter__(self):
        self.login()
        return self

    def __exit__(self, *args):
        self.logout()
