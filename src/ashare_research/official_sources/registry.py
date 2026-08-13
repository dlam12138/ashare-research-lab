"""M2 Stage 1 — 官方数据源注册表。"""

from __future__ import annotations

from ashare_research.exceptions import AshareDataError
from ashare_research.official_sources.base import OfficialSourceProvider


class OfficialSourceRegistry:
    """管理股票代码到官方数据提供方的映射。"""

    def __init__(self):
        self._providers: dict[str, OfficialSourceProvider] = {}

    def register(
        self, symbol: str, provider: OfficialSourceProvider
    ) -> None:
        """为指定标的注册官方数据提供方。"""
        self._providers[symbol] = provider

    def get_provider(self, symbol: str) -> OfficialSourceProvider:
        """获取标的对应提供方。

        Raises:
            AshareDataError: 未注册
        """
        if symbol not in self._providers:
            raise AshareDataError(
                f"No official source provider registered for {symbol}"
            )
        return self._providers[symbol]

    def list_symbols(self) -> list[str]:
        """列出所有已注册标的。"""
        return list(self._providers.keys())
