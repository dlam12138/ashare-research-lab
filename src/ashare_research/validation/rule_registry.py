"""M2 Stage 1 — 财务事实验证规则注册表。"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ValidationRule:
    """版本化验证规则。"""
    rule_id: str
    version: str = "1"
    severity: str = "error"       # error / warning
    applies_to: str = "FinancialFact"
    description: str = ""


class FactValidationRuleRegistry:
    """财务事实验证规则注册表。"""

    schema_version: str = "1.0"

    RULES: dict[str, ValidationRule] = {
        "FACT_SCHEMA_001": ValidationRule(
            rule_id="FACT_SCHEMA_001", version="1",
            severity="error", applies_to="FinancialFact",
            description="所有必需字段存在且非空",
        ),
        "FACT_VALUE_001": ValidationRule(
            rule_id="FACT_VALUE_001", version="1",
            severity="error", applies_to="FinancialFact",
            description="数值字段不含 NaN",
        ),
        "FACT_VALUE_002": ValidationRule(
            rule_id="FACT_VALUE_002", version="1",
            severity="error", applies_to="FinancialFact",
            description="数值字段不含 Inf",
        ),
        "FACT_UNIT_001": ValidationRule(
            rule_id="FACT_UNIT_001", version="1",
            severity="error", applies_to="FinancialFact",
            description="单位属于已注册单位",
        ),
        "FACT_CONCEPT_001": ValidationRule(
            rule_id="FACT_CONCEPT_001", version="1",
            severity="error", applies_to="FinancialFact",
            description="concept_id 已在概念注册表中",
        ),
        "FACT_SOURCE_001": ValidationRule(
            rule_id="FACT_SOURCE_001", version="1",
            severity="error", applies_to="FinancialFact",
            description=(
                "verified/reconciled 事实必须有 source_id 且 source_tier "
                "为 company_official 或 exchange_official（非 candidate_aggregator）"
            ),
        ),
        "FACT_PERIOD_001": ValidationRule(
            rule_id="FACT_PERIOD_001", version="1",
            severity="error", applies_to="FinancialFact",
            description="filing_date 不得早于 period_end",
        ),
        "FACT_CONTEXT_001": ValidationRule(
            rule_id="FACT_CONTEXT_001", version="1",
            severity="warning", applies_to="FinancialFact",
            description="context_id 必须包含所有必要字段",
        ),
        "FACT_DUP_001": ValidationRule(
            rule_id="FACT_DUP_001", version="1",
            severity="error", applies_to="FinancialFact",
            description="同一 context 下同一 concept 不得重复",
        ),
        "FACT_INSTANT_001": ValidationRule(
            rule_id="FACT_INSTANT_001", version="1",
            severity="error", applies_to="DerivedFact",
            description="时点字段（资产负债表）不得通过相减生成",
        ),
        "FACT_MISSING_001": ValidationRule(
            rule_id="FACT_MISSING_001", version="1",
            severity="error", applies_to="FinancialFact",
            description="缺失值不得被转换为 0",
        ),
        "FACT_DERIVE_001": ValidationRule(
            rule_id="FACT_DERIVE_001", version="1",
            severity="error", applies_to="DerivedFact",
            description="派生事实必须有至少一个输入事实",
        ),
        "FACT_DERIVE_002": ValidationRule(
            rule_id="FACT_DERIVE_002", version="1",
            severity="error", applies_to="DerivedFact",
            description="派生公式版本必须存在于注册表中",
        ),
        "FACT_PIT_001": ValidationRule(
            rule_id="FACT_PIT_001", version="1",
            severity="error", applies_to="FinancialFact",
            description="PIT 适格事实的 available_at 必须非空且为有效日期格式",
        ),
        "FACT_ANNOUNCE_001": ValidationRule(
            rule_id="FACT_ANNOUNCE_001", version="1",
            severity="error", applies_to="FinancialFact",
            description="verified 事实必须有 announcement_date",
        ),
        "FACT_ELIGIBILITY_001": ValidationRule(
            rule_id="FACT_ELIGIBILITY_001", version="1",
            severity="error", applies_to="FinancialFact",
            description="只有 verified/reconciled 事实可设置 eligible_for_metrics=true",
        ),
        "FACT_VERSION_001": ValidationRule(
            rule_id="FACT_VERSION_001", version="1",
            severity="error", applies_to="FinancialFact",
            description=(
                "fact_version=1 时 supersedes_fact_id 必须为空；"
                "fact_version>1 时 supersedes_fact_id 必须非空且 != fact_id"
            ),
        ),
    }

    @classmethod
    def get(cls, rule_id: str) -> ValidationRule | None:
        return cls.RULES.get(rule_id)

    @classmethod
    def list_by_severity(cls, severity: str) -> list[ValidationRule]:
        return [r for r in cls.RULES.values() if r.severity == severity]

    @classmethod
    def list_all(cls) -> list[ValidationRule]:
        return list(cls.RULES.values())
