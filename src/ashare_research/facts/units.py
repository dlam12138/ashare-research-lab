"""M2 Stage 1 — 单位字典与标准化转换。

所有财务数值必须通过单位注册表验证和转换。
不得使用自由字符串表示单位。
"""

from __future__ import annotations

from enum import StrEnum

from ashare_research.exceptions import UnitConversionError


class Unit(StrEnum):
    CNY = "CNY"                        # 人民币元
    CNY_PER_SHARE = "CNY_PER_SHARE"    # 人民币元/股
    SHARE = "SHARE"                    # 股
    DECIMAL = "DECIMAL"                # 小数（如 0.125 表示 12.5%）
    PERCENT = "PERCENT"                # 百分比（如 12.5）
    TEXT = "TEXT"                      # 文本
    BOOLEAN = "BOOLEAN"                # 布尔值


# 单位别名映射（输入 → 标准 enum）
UNIT_ALIASES: dict[str, Unit] = {
    "CNY": Unit.CNY,
    "元": Unit.CNY,
    "人民币元": Unit.CNY,
    "亿元": Unit.CNY,          # 通过因子转换
    "万元": Unit.CNY,          # 通过因子转换
    "CNY_PER_SHARE": Unit.CNY_PER_SHARE,
    "元/股": Unit.CNY_PER_SHARE,
    "SHARE": Unit.SHARE,
    "股": Unit.SHARE,
    "DECIMAL": Unit.DECIMAL,
    "PERCENT": Unit.PERCENT,
    "%": Unit.PERCENT,
    "TEXT": Unit.TEXT,
    "BOOLEAN": Unit.BOOLEAN,
    "bool": Unit.BOOLEAN,
}

# 单位转换因子表（源 → 目标 → 乘数）
# 所有金额统一转为 CNY 元
UNIT_CONVERSIONS: dict[str, dict[str, float]] = {
    "亿元": {Unit.CNY.value: 100_000_000.0},
    "万元": {Unit.CNY.value: 10_000.0},
    "元": {Unit.CNY.value: 1.0},
    "CNY": {Unit.CNY.value: 1.0},
    "%": {Unit.DECIMAL.value: 0.01},
    "PERCENT": {Unit.DECIMAL.value: 0.01},
}


class UnitRegistry:
    """单位注册表和转换引擎。

    用法:
        registry = UnitRegistry()
        normalized = registry.normalize_amount(1234.5, "亿元")
        # → (12_345_000_000.0, "CNY", "multiply_by_100_000_000")
    """

    schema_version: str = "1.0"

    @staticmethod
    def parse_unit(raw_unit: str) -> Unit | None:
        """从原始单位字符串解析为标准 Unit。"""
        return UNIT_ALIASES.get(raw_unit)

    @staticmethod
    def validate_unit(unit: str) -> bool:
        """验证单位字符串是否可识别。"""
        return unit in UNIT_ALIASES

    @staticmethod
    def convert(
        value: float,
        from_unit: str,
        to_unit: str,
    ) -> float:
        """在已知单位间转换数值。

        Raises:
            UnitConversionError: 转换不支持
        """
        if from_unit == to_unit:
            return value

        conversions = UNIT_CONVERSIONS.get(from_unit, {})
        if to_unit in conversions:
            return value * conversions[to_unit]

        raise UnitConversionError(
            f"Unsupported conversion: {from_unit} → {to_unit}"
        )

    @staticmethod
    def normalize_amount(
        value: float,
        raw_unit: str,
    ) -> tuple[float, str, str]:
        """将原始数值标准化为内部统一单位。

        Returns:
            (normalized_value, target_unit, normalization_rule)

        Raises:
            UnitConversionError: 无法识别的单位
        """
        unit = UNIT_ALIASES.get(raw_unit)
        if unit is None:
            raise UnitConversionError(
                f"Unrecognized unit: '{raw_unit}'"
            )

        # 数值单位 → 统一 CNY
        if unit == Unit.CNY:
            factor = 1.0
            rule = "identity"
            if raw_unit in UNIT_CONVERSIONS:
                for _target, factor_val in UNIT_CONVERSIONS[raw_unit].items():
                    factor = factor_val
                    break
                rule = f"multiply_by_{int(factor):,}"

            if raw_unit == "CNY" or raw_unit == "元":
                rule = "identity"
                factor = 1.0

            return value * factor, Unit.CNY.value, rule

        # 百分比 → DECIMAL
        if unit == Unit.PERCENT:
            return value * 0.01, Unit.DECIMAL.value, "divide_by_100"

        # 其他直接通过
        return value, unit.value, "identity"


# 模块级单例
_registry: UnitRegistry | None = None


def get_unit_registry() -> UnitRegistry:
    global _registry
    if _registry is None:
        _registry = UnitRegistry()
    return _registry
