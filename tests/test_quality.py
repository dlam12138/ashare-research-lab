"""数据质量检查测试。"""

import pandas as pd

from ashare_research.quality.validators import QualityValidator


def make_stock_daily_df(**overrides):
    """创建标准化的 stock_daily 测试 DataFrame。"""
    data = {
        "symbol": ["601857.SH"] * 5,
        "trade_date": [
            "2026-07-20", "2026-07-21", "2026-07-22",
            "2026-07-23", "2026-07-24",
        ],
        "open": [10.0, 10.2, 10.1, 10.3, 10.0],
        "high": [10.5, 10.4, 10.3, 10.6, 10.2],
        "low": [9.8, 10.0, 9.9, 10.1, 9.7],
        "close": [10.2, 10.1, 10.2, 10.5, 10.0],
        "pre_close": [10.1, 10.2, 10.1, 10.2, 10.3],
        "volume": [1e7, 1.2e7, 8e6, 1.5e7, 9e6],
        "amount": [1e8, 1.2e8, 8e7, 1.5e8, 9e7],
        "turnover_rate": [0.5, 0.6, 0.4, 0.7, 0.45],
        "is_trading": [True] * 5,
        "adjustment": ["none"] * 5,
        "source": ["test"] * 5,
        "fetched_at": ["2026-07-27T12:00:00"] * 5,
    }
    data.update(overrides)
    return pd.DataFrame(data)


class TestQualityValidator:
    """数据质量检查器测试。"""

    def setup_method(self):
        self.validator = QualityValidator()

    def test_all_checks_pass(self):
        df = make_stock_daily_df()
        results = self.validator.validate(df, "stock_daily")
        statuses = [r["status"] for r in results]
        assert "failed" not in statuses

    def test_missing_required_fields(self):
        df = make_stock_daily_df()
        df = df.drop(columns=["volume", "amount"])
        results = self.validator.validate(df, "stock_daily")

        req_check = next(r for r in results if r["check_name"] == "required_fields")
        assert req_check["status"] == "failed"
        assert "volume" in req_check["details"]

    def test_duplicate_primary_key(self):
        df = make_stock_daily_df()
        df.loc[4, "trade_date"] = "2026-07-20"  # 重复
        results = self.validator.validate(df, "stock_daily")

        pk_check = next(r for r in results if r["check_name"] == "primary_key_unique")
        assert pk_check["status"] == "failed"
        assert "duplicate" in pk_check["details"].lower()

    def test_negative_price(self):
        df = make_stock_daily_df()
        df.loc[2, "close"] = -1.0
        results = self.validator.validate(df, "stock_daily")

        check = next(r for r in results if r["check_name"] == "non_negative")
        assert check["status"] == "failed"

    def test_ohlc_logic_violation(self):
        df = make_stock_daily_df()
        df.loc[2, "high"] = 9.0  # 低于 open 和 close
        results = self.validator.validate(df, "stock_daily")

        check = next(r for r in results if r["check_name"] == "ohlc_logic")
        assert check["status"] == "failed"

    def test_empty_source(self):
        df = make_stock_daily_df()
        df.loc[0, "source"] = ""
        results = self.validator.validate(df, "stock_daily")

        check = next(r for r in results if r["check_name"] == "source_not_empty")
        assert check["status"] == "failed"

    def test_date_not_parseable(self):
        df = make_stock_daily_df()
        df.loc[0, "trade_date"] = "not-a-date"
        results = self.validator.validate(df, "stock_daily")

        check = next(r for r in results if r["check_name"] == "date_parsing")
        assert check["status"] == "failed"

    def test_index_daily_validation(self):
        df = pd.DataFrame({
            "symbol": ["000001"] * 5,
            "trade_date": [
                "2026-07-20", "2026-07-21", "2026-07-22",
                "2026-07-23", "2026-07-24",
            ],
            "open": [3300, 3310, 3290, 3320, 3330],
            "high": [3320, 3325, 3310, 3340, 3350],
            "low": [3280, 3290, 3270, 3300, 3310],
            "close": [3310, 3290, 3300, 3330, 3340],
            "volume": [1e8, 1.2e8, 8e7, 1.5e8, 9e7],
            "amount": [3e11, 3.5e11, 2.5e11, 4e11, 3e11],
            "source": ["test"] * 5,
            "fetched_at": ["2026-07-27T12:00:00"] * 5,
        })
        results = self.validator.validate(df, "index_daily")
        statuses = [r["status"] for r in results]
        assert "failed" not in statuses

    def test_null_primary_key_values(self):
        df = make_stock_daily_df()
        df.loc[1, "symbol"] = None
        results = self.validator.validate(df, "stock_daily")

        check = next(r for r in results if r["check_name"] == "no_null_keys")
        assert check["status"] == "failed"
