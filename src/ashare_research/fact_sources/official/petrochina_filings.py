"""M2 Stage 1C-A - 中国石油官方披露 Provider（canonical 身份入口）。

官方来源的真正实现（官网报告、上交所公告、认证文档解析）尚未落地。
本 Provider 当前提供 **manual official fact 的 canonical 加载入口**：
调用方注入已注册的官方手工事实，Provider 在出口强制
``FactIdentity`` / ``build_fact_id()`` 身份契约，使 manual official facts
无法绕过 canonical（Service、Repository 为第二、三层纵深防御）。

不下载、不解析真实报告，不访问网络。
"""

from __future__ import annotations

import logging
from typing import Any

import pandas as pd

from ashare_research.exceptions import SourceDocumentError
from ashare_research.fact_sources.base import FactSourceProvider, SourceTier
from ashare_research.facts.identity import (
    build_fact_id,
    validate_canonical_fact_ids,
)

logger = logging.getLogger(__name__)


class PetroChinaOfficialFilingProvider(FactSourceProvider):
    """中国石油 601857.SH 官方披露 Provider。

    身份契约：通过 ``manual_facts`` 注入的官方手工事实，在出口被强制
    canonical。Provider 不信任调用方传入的 ``fact_id``：每条事实的
    ``fact_id`` 由 :func:`build_fact_id` 从身份字段重算，并经
    :func:`validate_canonical_fact_ids` 校验。任何与 canonical 身份
    不一致的事实都会在此被拒绝，无法进入 Service / Repository。

    ⚠ 真正的官方来源（官网/上交所）尚未实现。未注入 manual_facts 时，
    所有方法 raise ``SourceDocumentError``，不得将 AKShare 候选数据
    冒充官方来源。
    """

    provider_name = "petrochina_official_filing"
    source_tier = SourceTier.company_official

    def __init__(
        self,
        raw_dir: str = "",
        *,
        manual_facts: list[dict[str, Any]] | None = None,
    ) -> None:
        super().__init__(raw_dir=raw_dir)
        # 已注册的官方手工事实（canonical 入口）。None 表示尚未提供
        # 任何官方事实 -> 保持占位 raise 语义。
        self._manual_facts: list[dict[str, Any]] | None = (
            list(manual_facts) if manual_facts is not None else None
        )

    def get_financial_statements(
        self, symbol: str, start_year: int, end_year: int
    ) -> pd.DataFrame:
        """返回已注入的官方手工事实（canonical 强制）。

        若未注入任何 manual_facts，raise ``SourceDocumentError``
        （官方来源尚未实现，不静默返回空，不回退候选来源）。
        """
        if self._manual_facts is None:
            raise SourceDocumentError(
                "PetroChina official filing source not yet implemented. "
                "Use candidate source (--source candidate) for now. "
                "Official fact extraction requires registered manual fact "
                "files or certified document parsing."
            )

        facts = self._enforce_canonical(self._manual_facts)
        if not facts:
            return pd.DataFrame()
        return pd.DataFrame(facts)

    def get_dividends(
        self, symbol: str, start_year: int, end_year: int
    ) -> pd.DataFrame:
        if self._manual_facts is None:
            raise SourceDocumentError(
                "Official dividend source not yet implemented."
            )
        facts = self._enforce_canonical(self._manual_facts)
        return pd.DataFrame(
            [f for f in facts if f.get("concept_id")
             == "cash_dividend_per_share"]
        )

    def get_buybacks(
        self, symbol: str, start_year: int, end_year: int
    ) -> pd.DataFrame:
        if self._manual_facts is None:
            raise SourceDocumentError(
                "Official buyback source not yet implemented."
            )
        return pd.DataFrame()

    def get_shareholder_increases(
        self, symbol: str, start_year: int, end_year: int
    ) -> pd.DataFrame:
        if self._manual_facts is None:
            raise SourceDocumentError(
                "Official shareholder increase source not yet implemented."
            )
        return pd.DataFrame()

    def get_audit_opinions(
        self, symbol: str, start_year: int, end_year: int
    ) -> pd.DataFrame:
        if self._manual_facts is None:
            raise SourceDocumentError(
                "Official audit opinion source not yet implemented."
            )
        return pd.DataFrame()

    @staticmethod
    def _enforce_canonical(
        facts: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """对每条注入事实强制 canonical 身份契约。

        - 重算 ``fact_id``（不信任调用方传入的 id）；
        - ``validate_canonical_fact_ids`` 校验身份字段自洽；
        - 任何不一致在此 raise，manual official facts 无法绕过。

        这是官方来源身份契约的纵深防御第一层；Service 与
        Repository 会再次校验。
        """
        enforced: list[dict[str, Any]] = []
        for fact in facts:
            f = dict(fact)
            # 重算 canonical fact_id，覆盖任何调用方传入的值。
            f["fact_id"] = build_fact_id(f)
            enforced.append(f)
        validate_canonical_fact_ids(enforced)
        return enforced
