"""M2 Stage 1B — 事实来源注册表。

管理候选来源和官方来源的分开注册。
"""

from __future__ import annotations

from ashare_research.exceptions import AshareDataError
from ashare_research.fact_sources.base import FactSourceProvider, SourceTier


class FactSourceRegistry:
    """事实来源注册表。

    区分候选来源（candidate）和官方来源（official）。
    下游必须能识别来源等级。
    """

    def __init__(self):
        self._candidates: dict[str, FactSourceProvider] = {}
        self._officials: dict[str, FactSourceProvider] = {}

    def register_candidate(
        self, symbol: str, provider: FactSourceProvider,
    ) -> None:
        """注册候选来源（如 AKShare 聚合数据）。"""
        self._candidates[symbol] = provider

    def register_official(
        self, symbol: str, provider: FactSourceProvider,
    ) -> None:
        """注册官方来源（如公司官网/交易所披露）。"""
        self._officials[symbol] = provider

    def get_candidate(self, symbol: str) -> FactSourceProvider:
        if symbol not in self._candidates:
            raise AshareDataError(
                f"No candidate source registered for {symbol}"
            )
        return self._candidates[symbol]

    def get_official(self, symbol: str) -> FactSourceProvider | None:
        return self._officials.get(symbol)

    def get_provider(
        self, symbol: str, source_mode: str = "candidate",
    ) -> FactSourceProvider:
        """获取指定来源模式的提供方。

        source_mode="official" 时，若官方来源未启用或未注册，
        抛出 AshareDataError（不得回退到候选来源）。
        """
        if source_mode == "official":
            provider = self._officials.get(symbol)
            if provider is None:
                raise AshareDataError(
                    f"No official source registered for {symbol}. "
                    f"Official source is not yet implemented. "
                    f"Use --source candidate for AKShare candidate data."
                )
            return provider

        # candidate mode (default)
        if symbol not in self._candidates:
            raise AshareDataError(
                f"No candidate source registered for {symbol}"
            )
        return self._candidates[symbol]

    def get_source_tier(
        self, symbol: str, source_mode: str = "candidate",
    ) -> SourceTier:
        if source_mode == "official":
            return SourceTier.company_official
        return SourceTier.candidate_aggregator

    def list_candidates(self) -> list[str]:
        return list(self._candidates.keys())

    def list_officials(self) -> list[str]:
        return list(self._officials.keys())
