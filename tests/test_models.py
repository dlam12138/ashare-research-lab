"""股票代码转换测试。"""

import pytest

from ashare_research.exceptions import CodeFormatError
from ashare_research.models import (
    extract_digits,
    extract_exchange,
    to_baostock_code,
    to_standard_code,
)


class TestCodeConversion:
    """代码格式转换测试。"""

    def test_standard_to_standard(self):
        assert to_standard_code("600000.SH") == "600000.SH"
        assert to_standard_code("000001.SZ") == "000001.SZ"

    def test_baostock_to_standard_sh(self):
        assert to_standard_code("sh.600000") == "600000.SH"
        assert to_standard_code("SH.600000") == "600000.SH"

    def test_baostock_to_standard_sz(self):
        assert to_standard_code("sz.000001") == "000001.SZ"
        assert to_standard_code("SZ.000001") == "000001.SZ"

    def test_digits_only_sh(self):
        """6位数字，6/9开头推断沪市。"""
        assert to_standard_code("600000") == "600000.SH"
        assert to_standard_code("900001") == "900001.SH"

    def test_digits_only_sz(self):
        """0/3/2开头推断深市。"""
        assert to_standard_code("000001") == "000001.SZ"
        assert to_standard_code("300001") == "300001.SZ"
        assert to_standard_code("200001") == "200001.SZ"

    def test_invalid_format(self):
        with pytest.raises(CodeFormatError):
            to_standard_code("abc.600000")

    def test_invalid_digits_only(self):
        """无法推断交易所的数字应报错。"""
        with pytest.raises(CodeFormatError):
            to_standard_code("500001")

    def test_to_baostock_sh(self):
        assert to_baostock_code("600000.SH") == "sh.600000"
        assert to_baostock_code("600000") == "sh.600000"

    def test_to_baostock_sz(self):
        assert to_baostock_code("000001.SZ") == "sz.000001"

    def test_extract_exchange(self):
        assert extract_exchange("600000.SH") == "SH"
        assert extract_exchange("000001.SZ") == "SZ"

    def test_extract_digits(self):
        assert extract_digits("600000.SH") == "600000"
        assert extract_digits("000001.SZ") == "000001"

    def test_whitespace_handling(self):
        assert to_standard_code("  600000.SH  ") == "600000.SH"


class TestModels:
    """数据模型创建测试。"""

    def test_stock_basic_creation(self):
        from ashare_research.models import StockBasic

        sb = StockBasic(
            symbol="601857.SH",
            exchange="SH",
            name="中国石油",
            source="test",
            fetched_at="2026-07-27T12:00:00",
        )
        assert sb.symbol == "601857.SH"
        assert sb.name == "中国石油"

    def test_stock_daily_creation(self):
        from ashare_research.models import StockDaily

        sd = StockDaily(
            symbol="601857.SH",
            trade_date="2026-07-27",
            open=10.0,
            high=10.5,
            low=9.8,
            close=10.2,
            pre_close=10.1,
            volume=1e7,
            amount=1e8,
            source="test",
        )
        assert sd.close == 10.2
        assert sd.volume == 1e7
        assert sd.adjustment == "none"

    def test_fetch_run_defaults(self):
        from ashare_research.models import FetchRun

        run = FetchRun(
            run_id="test123",
            dataset="stock_daily",
            provider="baostock",
        )
        assert run.status == "pending"
        assert run.schema_version == "1.0"
