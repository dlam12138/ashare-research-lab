"""M2 Stage 1B — 事实来源提供方统一接口。

区分候选来源（candidate_aggregator）与官方来源（company_official/exchange_official）。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum

import pandas as pd


class SourceTier(str, Enum):
    """来源等级。"""
    candidate_aggregator = "candidate_aggregator"   # AKShare等第三方聚合
    company_official = "company_official"           # 公司官网/年报
    exchange_official = "exchange_official"         # 交易所正式披露


@dataclass
class FactSource:
    """事实来源元数据。"""
    source_id: str
    source_provider: str
    source_tier: SourceTier
    source_document: str = ""
    source_url: str = ""
    source_hash: str = ""
    verification_status: str = "unverified"


class FactSourceProvider(ABC):
    """事实来源提供方抽象基类。

    所有候选和官方来源必须明确声明 source_tier。
    """

    provider_name: str = "fact_source_base"
    source_tier: SourceTier = SourceTier.candidate_aggregator

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
        ...

    @abstractmethod
    def get_dividends(
        self, symbol: str, start_year: int, end_year: int
    ) -> pd.DataFrame:
        ...

    @abstractmethod
    def get_buybacks(
        self, symbol: str, start_year: int, end_year: int
    ) -> pd.DataFrame:
        ...

    @abstractmethod
    def get_shareholder_increases(
        self, symbol: str, start_year: int, end_year: int
    ) -> pd.DataFrame:
        ...

    @abstractmethod
    def get_audit_opinions(
        self, symbol: str, start_year: int, end_year: int
    ) -> pd.DataFrame:
        ...
