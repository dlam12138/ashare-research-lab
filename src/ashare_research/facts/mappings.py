"""M2 Stage 1 — 源字段 → 标准概念映射。

每个数据提供方（AKShare 等）的原始字段名通过此模块
映射到标准 concept_id，并记录所需单位转换。
"""

from __future__ import annotations

# AKShare 财务接口中文字段名 → (concept_id, 单位转换因子)
# 因子含义: raw_value * factor = normalized_value_in_CNY
_AKSHARE_PROFIT_FIELDS: dict[str, tuple[str, float]] = {
    "营业收入": ("revenue", 1.0),
    "营业总收入": ("revenue", 1.0),
    "营业成本": ("operating_cost", 1.0),
    "营业利润": ("operating_profit", 1.0),
    "利润总额": ("profit_before_tax", 1.0),
    "净利润": ("net_profit", 1.0),
    "归属于母公司所有者的净利润": ("net_profit_attributable_to_parent", 1.0),
    "归属于母公司股东的净利润": ("net_profit_attributable_to_parent", 1.0),
    "归属于母公司所有者的扣除非经常性损益净利润": (
        "net_profit_excluding_non_recurring", 1.0,
    ),
    "基本每股收益": ("basic_eps", 1.0),
    "稀释每股收益": ("diluted_eps", 1.0),
}

_AKSHARE_CASHFLOW_FIELDS: dict[str, tuple[str, float]] = {
    "经营活动产生的现金流量净额": ("operating_cash_flow", 1.0),
    "经营活动现金净流量": ("operating_cash_flow", 1.0),
    "购建固定资产、无形资产和其他长期资产支付的现金": (
        "capital_expenditure_cash", 1.0,
    ),
    "投资活动产生的现金流量净额": ("net_cash_from_investing", 1.0),
    "筹资活动产生的现金流量净额": ("net_cash_from_financing", 1.0),
}

_AKSHARE_BALANCE_FIELDS: dict[str, tuple[str, float]] = {
    "货币资金": ("monetary_funds", 1.0),
    "现金及现金等价物余额": ("cash_and_cash_equivalents", 1.0),
    "短期借款": ("short_term_borrowings", 1.0),
    "长期借款": ("long_term_borrowings", 1.0),
    "应付债券": ("bonds_payable", 1.0),
    "租赁负债": ("lease_liabilities", 1.0),
    "资产总计": ("total_assets", 1.0),
    "总资产": ("total_assets", 1.0),
    "负债合计": ("total_liabilities", 1.0),
    "总负债": ("total_liabilities", 1.0),
    "流动资产合计": ("total_current_assets", 1.0),
    "流动负债合计": ("total_current_liabilities", 1.0),
    "归属于母公司所有者权益": ("equity_attributable_to_parent", 1.0),
    "归属于母公司股东权益": ("equity_attributable_to_parent", 1.0),
    "股东权益合计": ("total_equity", 1.0),
    "所有者权益合计": ("total_equity", 1.0),
    "股本": ("share_capital", 1.0),
    "实收资本": ("share_capital", 1.0),
    "无形资产": ("intangible_assets", 1.0),
    "商誉": ("goodwill", 1.0),
    "存货": ("inventories", 1.0),
    "应收账款": ("accounts_receivable", 1.0),
}

# 全字段映射（按报表类型分组）
ALL_FIELD_MAPS: dict[str, dict[str, tuple[str, float]]] = {
    "profit": _AKSHARE_PROFIT_FIELDS,
    "cash_flow": _AKSHARE_CASHFLOW_FIELDS,
    "balance_sheet": _AKSHARE_BALANCE_FIELDS,
}


class ConceptMapping:
    """源字段 → 标准 concept_id 映射器。"""

    schema_version: str = "1.0"

    def __init__(self):
        self._field_map: dict[str, tuple[str, float]] = {}
        for report_map in ALL_FIELD_MAPS.values():
            self._field_map.update(report_map)

    def map_field(self, raw_field_name: str) -> tuple[str | None, float]:
        """将原始字段名映射到 (concept_id, factor)。

        Returns:
            (concept_id, factor) 或 (None, 1.0) 表示无法识别
        """
        result = self._field_map.get(raw_field_name)
        if result is None:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(
                f"Unrecognized source field: '{raw_field_name}'"
            )
            return None, 1.0
        return result

    def get_concept_id(self, raw_field_name: str) -> str | None:
        """获取原始字段对应的标准概念ID。"""
        concept_id, _ = self.map_field(raw_field_name)
        return concept_id

    def get_unit_conversion(self, raw_field_name: str) -> float:
        """获取单位转换因子。"""
        _, factor = self.map_field(raw_field_name)
        return factor

    def get_all_mappings(self) -> dict[str, tuple[str, float]]:
        """返回全部字段映射。"""
        return dict(self._field_map)

    def get_reverse_map(self) -> dict[str, list[str]]:
        """concept_id → [raw_field_names] 反向映射。"""
        reverse: dict[str, list[str]] = {}
        for raw_name, (concept_id, _) in self._field_map.items():
            if concept_id not in reverse:
                reverse[concept_id] = []
            reverse[concept_id].append(raw_name)
        return reverse

    def get_fields_for_report_type(
        self, report_type: str
    ) -> dict[str, tuple[str, float]]:
        """获取特定报表类型的字段映射。"""
        return ALL_FIELD_MAPS.get(report_type, {})
