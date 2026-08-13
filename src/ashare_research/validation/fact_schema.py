"""M2 Stage 1 — 财务事实模式定义。"""

from __future__ import annotations

# 各类型事实的必需字段
REQUIRED_FIELDS: dict[str, list[str]] = {
    "financial_fact": [
        "fact_id", "concept_id", "symbol", "value",
        "unit", "context_id", "filing_date", "period_end",
        "source_provider", "verification_status", "created_at",
    ],
}

# 资产类概念（非负）
NON_NEGATIVE_CONCEPTS: set[str] = {
    "total_assets", "total_equity",
    "equity_attributable_to_parent", "share_capital",
    "monetary_funds", "cash_and_cash_equivalents",
    "total_current_assets", "inventories", "accounts_receivable",
    "intangible_assets", "goodwill",
}

# 区间型概念（利润表/现金流量表，可以相减）
DURATION_CONCEPTS: set[str] = {
    "revenue", "operating_cost", "operating_profit",
    "profit_before_tax", "net_profit",
    "net_profit_attributable_to_parent",
    "net_profit_excluding_non_recurring",
    "basic_eps", "diluted_eps",
    "operating_cash_flow",
    "capital_expenditure_cash",
    "cash_paid_for_fixed_assets",
    "cash_paid_for_intangible_assets",
    "cash_paid_for_long_term_assets",
    "net_cash_from_investing",
    "net_cash_from_financing",
    "free_cash_flow",
}

# 时点型概念（资产负债表，不得相减）
INSTANT_CONCEPTS: set[str] = {
    "total_assets", "total_liabilities",
    "total_current_assets", "total_current_liabilities",
    "equity_attributable_to_parent", "total_equity",
    "share_capital", "monetary_funds",
    "cash_and_cash_equivalents",
    "short_term_borrowings", "long_term_borrowings",
    "bonds_payable", "lease_liabilities",
    "interest_bearing_debt",
    "intangible_assets", "goodwill",
    "inventories", "accounts_receivable",
}


def validate_fact_schema(fact: dict) -> list[dict]:
    """验证单条事实的必需字段。

    Returns:
        list of {field, status, message}
    """
    issues: list[dict] = []
    required = REQUIRED_FIELDS.get("financial_fact", [])

    for field in required:
        if field not in fact or fact[field] is None:
            issues.append({
                "field": field,
                "status": "failed",
                "message": f"Missing required field: {field}",
            })

    # 数值字段不能是 NaN
    if "value" in fact:
        import math
        val = fact["value"]
        if val is not None and isinstance(val, float) and math.isnan(val):
            issues.append({
                "field": "value",
                "status": "failed",
                "message": "Value is NaN",
            })

    return issues
