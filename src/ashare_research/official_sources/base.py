"""M2 Stage 1 — 官方数据源提供方统一接口。"""

from __future__ import annotations

from abc import ABC, abstractmethod

import pandas as pd


class OfficialSourceProvider(ABC):
    """官方财务数据提供方抽象基类。

    所有官方来源（年度报告、交易所披露等）必须实现此接口。
    继承 BaseProvider 的 raw_dir 和 _save_raw_response() 模式。
    """

    provider_name: str = "official_base"

    def __init__(self, raw_dir: str = ""):
        self.raw_dir = raw_dir
        self._last_raw_path: str = ""

    @property
    def last_raw_path(self) -> str:
        return self._last_raw_path

    def reset_last_raw_path(self) -> None:
        self._last_raw_path = ""

    def _save_raw_response(
        self, df: pd.DataFrame, dataset: str, symbol: str = ""
    ) -> str:
        """保存上游原始响应快照（复用 BaseProvider 模式）。"""
        import os
        from datetime import datetime
        from pathlib import Path

        from ashare_research.exceptions import RawPersistenceError

        if not self.raw_dir:
            self._last_raw_path = ""
            return ""

        target_dir = Path(self.raw_dir) / self.provider_name / dataset
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        safe_symbol = symbol.replace(".", "_") if symbol else "all"
        filename = f"{safe_symbol}_{timestamp}.parquet"
        final_path = target_dir / filename

        tmp_path = target_dir / f".{filename}.tmp"
        try:
            target_dir.mkdir(parents=True, exist_ok=True)
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
    def get_financial_statements(
        self, symbol: str, start_year: int, end_year: int
    ) -> pd.DataFrame:
        """获取财务报表数据（利润表、资产负债表、现金流量表）。

        Returns DataFrame columns:
            symbol, report_type, fiscal_year, period_end,
            filing_date, concept_id, value, unit, raw_value,
            raw_unit, source_document
        """
        ...

    @abstractmethod
    def get_dividends(
        self, symbol: str, start_year: int, end_year: int
    ) -> pd.DataFrame:
        """获取分红记录。"""
        ...

    @abstractmethod
    def get_buybacks(
        self, symbol: str, start_year: int, end_year: int
    ) -> pd.DataFrame:
        """获取回购记录。"""
        ...

    @abstractmethod
    def get_shareholder_increases(
        self, symbol: str, start_year: int, end_year: int
    ) -> pd.DataFrame:
        """获取大股东增持记录。"""
        ...

    @abstractmethod
    def get_audit_opinions(
        self, symbol: str, start_year: int, end_year: int
    ) -> pd.DataFrame:
        """获取审计意见。"""
        ...
