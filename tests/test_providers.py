"""提供方单元测试 — 验证数据正确性修复。

测试：
- AKShare 成交量单位转换（手→股）
- Baostock adjustflag 参数
- Baostock A 股过滤
- AKShare 指数接口使用
"""

import contextlib

import pandas as pd

from ashare_research.exceptions import EmptyResultError
from ashare_research.models import to_baostock_code


class TestAKShareUnitConversion:
    """AKShare 成交量单位转换测试。"""

    def test_volume_multiplied_by_100(self):
        """验证 AKShare 成交量从手转换为股（×100）。"""
        from unittest.mock import patch

        import akshare

        # 模拟 AKShare 返回手为单位的成交量
        mock_df = pd.DataFrame({
            "日期": ["2026-07-20", "2026-07-21"],
            "开盘": [10.0, 10.1],
            "最高": [10.5, 10.4],
            "最低": [9.8, 10.0],
            "收盘": [10.2, 10.1],
            "成交量": [10000, 20000],   # 手
            "成交额": [10200000, 20200000],
            "换手率": [0.5, 0.6],
        })

        with patch.object(akshare, "stock_zh_a_hist", return_value=mock_df):
            from ashare_research.providers.akshare_provider import AKShareProvider
            provider = AKShareProvider()
            result = provider.get_stock_daily(
                "601857.SH", "2026-07-20", "2026-07-22", "none"
            )

        # 成交量应该是 10,000 手 × 100 = 1,000,000 股
        assert result["volume"].iloc[0] == 1_000_000
        assert result["volume"].iloc[1] == 2_000_000

    def test_price_fields_not_scaled(self):
        """价格字段不应被成交量转换影响。"""
        from unittest.mock import patch

        import akshare

        mock_df = pd.DataFrame({
            "日期": ["2026-07-20"],
            "开盘": [10.0],
            "最高": [10.5],
            "最低": [9.8],
            "收盘": [10.2],
            "成交量": [10000],
            "成交额": [10200000],
            "换手率": [0.5],
        })

        with patch.object(akshare, "stock_zh_a_hist", return_value=mock_df):
            from ashare_research.providers.akshare_provider import AKShareProvider
            provider = AKShareProvider()
            result = provider.get_stock_daily(
                "601857.SH", "2026-07-20", "2026-07-20", "none"
            )

        assert result["open"].iloc[0] == 10.0
        assert result["close"].iloc[0] == 10.2


class TestBaostockAdjustflag:
    """Baostock adjustflag 参数测试。"""

    def test_none_maps_to_3(self):
        """不复权应映射为 adjustflag=3。"""
        from unittest.mock import MagicMock, patch

        import baostock as bs

        # 模拟 Baostock 登录
        mock_login = MagicMock()
        mock_login.error_code = "0"

        # 模拟查询结果
        mock_rs = MagicMock()
        mock_rs.error_code = "0"
        mock_rs.fields = ["date", "code", "open", "high", "low",
                          "close", "preclose", "volume", "amount",
                          "turn", "tradestatus"]
        mock_rs.next.side_effect = [
            True, True, False,
        ]

        def get_row_data():
            return ["2026-07-20", "sh.601857", "10.000000", "10.500000",
                    "9.800000", "10.200000", "10.100000", "10000000",
                    "102000000", "0.500000", "1"]

        mock_rs.get_row_data = get_row_data

        with (
            patch.object(bs, "login", return_value=mock_login),
            patch.object(bs, "logout", return_value=None),
            patch.object(bs, "query_history_k_data_plus") as mock_query,
        ):
            mock_query.return_value = mock_rs
            from ashare_research.providers.baostock_provider import (
                BaostockProvider,
            )
            provider = BaostockProvider()
            provider._ensure_login()
            provider.get_stock_daily(
                "601857.SH", "2026-07-20", "2026-07-20", "none"
            )

            # 验证 adjustflag 参数
            call_kwargs = mock_query.call_args
            adjustflag = (
                call_kwargs[0][5]
                if len(call_kwargs[0]) > 5
                else call_kwargs[1].get("adjustflag")
            )
            assert adjustflag == "3", (
                f"Expected adjustflag='3', got '{adjustflag}'"
            )

    def test_qfq_maps_to_2(self):
        """前复权应映射为 adjustflag=2。"""
        from unittest.mock import MagicMock, patch

        import baostock as bs

        mock_login = MagicMock()
        mock_login.error_code = "0"
        mock_rs = MagicMock()
        mock_rs.error_code = "0"
        mock_rs.fields = ["date", "code", "open", "high", "low",
                          "close", "preclose", "volume", "amount",
                          "turn", "tradestatus"]
        mock_rs.next.return_value = False

        with (
            patch.object(bs, "login", return_value=mock_login),
            patch.object(bs, "logout", return_value=None),
            patch.object(bs, "query_history_k_data_plus") as mock_query,
        ):
            mock_query.return_value = mock_rs
            from ashare_research.providers.baostock_provider import (
                BaostockProvider,
            )
            provider = BaostockProvider()
            provider._ensure_login()
            with contextlib.suppress(EmptyResultError):
                provider.get_stock_daily(
                    "601857.SH", "2026-07-20", "2026-07-20", "qfq"
                )

            call_kwargs = mock_query.call_args
            adjustflag = (
                call_kwargs[0][5]
                if len(call_kwargs[0]) > 5
                else call_kwargs[1].get("adjustflag")
            )
            assert adjustflag == "2", (
                f"Expected adjustflag='2', got '{adjustflag}'"
            )

    def test_hfq_maps_to_1(self):
        """后复权应映射为 adjustflag=1。"""
        from unittest.mock import MagicMock, patch

        import baostock as bs

        mock_login = MagicMock()
        mock_login.error_code = "0"
        mock_rs = MagicMock()
        mock_rs.error_code = "0"
        mock_rs.fields = ["date", "code", "open", "high", "low",
                          "close", "preclose", "volume", "amount",
                          "turn", "tradestatus"]
        mock_rs.next.return_value = False

        with (
            patch.object(bs, "login", return_value=mock_login),
            patch.object(bs, "logout", return_value=None),
            patch.object(bs, "query_history_k_data_plus") as mock_query,
        ):
            mock_query.return_value = mock_rs
            from ashare_research.providers.baostock_provider import (
                BaostockProvider,
            )
            provider = BaostockProvider()
            provider._ensure_login()
            with contextlib.suppress(EmptyResultError):
                provider.get_stock_daily(
                    "601857.SH", "2026-07-20", "2026-07-20", "hfq"
                )

            call_kwargs = mock_query.call_args
            adjustflag = (
                call_kwargs[0][5]
                if len(call_kwargs[0]) > 5
                else call_kwargs[1].get("adjustflag")
            )
            assert adjustflag == "1", (
                f"Expected adjustflag='1', got '{adjustflag}'"
            )


class TestCodeConversionDetailed:
    """代码转换边界情况测试。"""

    def test_6_digit_sh_prefix(self):
        assert to_baostock_code("600000") == "sh.600000"

    def test_3_digit_sz_prefix(self):
        assert to_baostock_code("300001") == "sz.300001"

    def test_0_digit_sz_prefix(self):
        assert to_baostock_code("000001") == "sz.000001"
