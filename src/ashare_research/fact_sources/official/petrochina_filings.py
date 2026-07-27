"""M2 Stage 1B — 中国石油官方披露 Provider（空骨架）。

官方来源尚未实现。当前仅保留接口，明确标记为 pending。
将来消费：中国石油官网报告、上交所正式公告、已注册的官方手工事实文件。
"""

from __future__ import annotations

import pandas as pd

from ashare_research.exceptions import SourceDocumentError
from ashare_research.fact_sources.base import FactSourceProvider, SourceTier


class PetroChinaOfficialFilingProvider(FactSourceProvider):
    """中国石油 601857.SH 官方披露 Provider。

    ⚠ 当前官方来源尚未实现，所有方法返回空或报错。
    不得将 AKShare 候选数据冒充官方来源。
    """

    provider_name = "petrochina_official_filing"
    source_tier = SourceTier.company_official

    def get_financial_statements(
        self, symbol: str, start_year: int, end_year: int
    ) -> pd.DataFrame:
        raise SourceDocumentError(
            "PetroChina official filing source not yet implemented. "
            "Use candidate source (--source candidate) for now. "
            "Official fact extraction requires registered manual fact "
            "files or certified document parsing."
        )

    def get_dividends(
        self, symbol: str, start_year: int, end_year: int
    ) -> pd.DataFrame:
        raise SourceDocumentError(
            "Official dividend source not yet implemented."
        )

    def get_buybacks(
        self, symbol: str, start_year: int, end_year: int
    ) -> pd.DataFrame:
        raise SourceDocumentError(
            "Official buyback source not yet implemented."
        )

    def get_shareholder_increases(
        self, symbol: str, start_year: int, end_year: int
    ) -> pd.DataFrame:
        raise SourceDocumentError(
            "Official shareholder increase source not yet implemented."
        )

    def get_audit_opinions(
        self, symbol: str, start_year: int, end_year: int
    ) -> pd.DataFrame:
        raise SourceDocumentError(
            "Official audit opinion source not yet implemented."
        )
