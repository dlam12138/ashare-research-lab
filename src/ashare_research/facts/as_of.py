"""M2 Stage 1 — Point-in-Time 查询引擎。

所有下游查询必须通过 as_of_date 门禁，
禁止直接读取未过滤的完整事实集。
"""

from __future__ import annotations

import logging
from typing import Any

import pandas as pd

from ashare_research.exceptions import PointInTimeError
from ashare_research.facts.repository import FactRepository

logger = logging.getLogger(__name__)


class AsOfQuery:
    """PIT 查询引擎。"""

    schema_version: str = "1.0"

    def __init__(self, repository: FactRepository):
        self.repository = repository

    def query(
        self,
        symbol: str,
        concept_ids: list[str] | None = None,
        as_of_date: str = "",
        start_year: int | None = None,
        end_year: int | None = None,
    ) -> pd.DataFrame:
        """查询截至指定日期已公开的事实。

        Args:
            symbol: 股票代码
            concept_ids: 概念ID列表，None 表示全部
            as_of_date: PIT 截止日期 YYYY-MM-DD
            start_year: 起始财年
            end_year: 截止财年

        Returns:
            仅包含 available_at <= as_of_date 的事实

        Raises:
            PointInTimeError: as_of_date 为空时
        """
        if not as_of_date:
            raise PointInTimeError(
                "as_of_date is required for PIT queries. "
                "Use get_all_versions_for_audit() for unfiltered access."
            )

        return self.repository.query_facts(
            symbol=symbol,
            concept_ids=concept_ids,
            start_year=start_year,
            end_year=end_year,
            as_of_date=as_of_date,
        )

    def get_latest(
        self, symbol: str, concept_ids: list[str] | None = None,
    ) -> pd.DataFrame:
        """获取最新已公开事实（不限 PIT 日期）。"""
        return self.repository.query_facts(
            symbol=symbol, concept_ids=concept_ids,
        )

    def get_all_versions_for_audit(
        self, symbol: str, concept_ids: list[str] | None = None,
    ) -> pd.DataFrame:
        """审计用：获取所有版本事实（不限制 available_at）。

        此方法名称明确表明它是调试/审计接口，不应在分析代码中使用。
        """
        return self.repository.query_facts(
            symbol=symbol, concept_ids=concept_ids,
        )

    def compare_versions(
        self, symbol: str, concept_ids: list[str],
        date1: str, date2: str,
    ) -> dict[str, Any]:
        """比较两个时点的事实版本差异，检测重述。

        Returns:
            dict: {concept_id: {date1_value, date2_value, changed}}
        """
        df1 = self.query(symbol, concept_ids, as_of_date=date1)
        df2 = self.query(symbol, concept_ids, as_of_date=date2)

        comparison: dict[str, Any] = {}
        for cid in concept_ids:
            v1 = df1[df1["concept_id"] == cid]
            v2 = df2[df2["concept_id"] == cid]
            val1 = v1["value"].iloc[0] if not v1.empty else None
            val2 = v2["value"].iloc[0] if not v2.empty else None
            comparison[cid] = {
                f"value_at_{date1}": val1,
                f"value_at_{date2}": val2,
                "changed": val1 != val2 if val1 is not None else None,
            }

        return comparison
