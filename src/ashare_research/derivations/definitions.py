"""M2 Stage 1 — 派生事实定义注册表。

所有派生公式必须版本化，不得散落在报告模板或 CLI 中。
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class DerivationDefinition:
    """版本化派生规则定义。"""
    definition_id: str
    version: str = "1"
    output_concept_id: str = ""
    input_concept_ids: list[str] = field(default_factory=list)
    expression: str = ""
    description: str = ""
    applicable_profiles: list[str] = field(
        default_factory=lambda: ["general", "cyclical"]
    )


class DerivationRegistry:
    """派生公式注册表。"""

    schema_version: str = "1.0"

    DERIVATIONS: dict[str, DerivationDefinition] = {
        "free_cash_flow": DerivationDefinition(
            definition_id="free_cash_flow",
            version="1",
            output_concept_id="free_cash_flow",
            input_concept_ids=[
                "operating_cash_flow",
                "capital_expenditure_cash",
            ],
            expression="operating_cash_flow - capital_expenditure_cash",
            description=(
                "自由现金流 = 经营活动现金流净额 - 资本开支（现金）"
            ),
        ),
        "interest_bearing_debt": DerivationDefinition(
            definition_id="interest_bearing_debt",
            version="1",
            output_concept_id="interest_bearing_debt",
            input_concept_ids=[
                "short_term_borrowings",
                "long_term_borrowings",
                "bonds_payable",
                "lease_liabilities",
            ],
            expression=(
                "short_term_borrowings + long_term_borrowings "
                "+ bonds_payable + lease_liabilities"
            ),
            description="有息负债 = 短期借款 + 长期借款 + 应付债券 + 租赁负债",
        ),
        "single_quarter_revenue": DerivationDefinition(
            definition_id="single_quarter_revenue",
            version="1",
            output_concept_id="revenue",
            input_concept_ids=["revenue"],
            expression=(
                "Q1 = Q1_YTD; Q2 = H1_YTD - Q1_YTD; "
                "Q3 = Q3_YTD - H1_YTD; Q4 = FY - Q3_YTD"
            ),
            description="从累计利润表值还原单季度营收",
        ),
        "single_quarter_net_profit": DerivationDefinition(
            definition_id="single_quarter_net_profit",
            version="1",
            output_concept_id="net_profit_attributable_to_parent",
            input_concept_ids=["net_profit_attributable_to_parent"],
            expression=(
                "Q1 = Q1_YTD; Q2 = H1_YTD - Q1_YTD; "
                "Q3 = Q3_YTD - H1_YTD; Q4 = FY - Q3_YTD"
            ),
            description="从累计利润表值还原单季度归母净利润",
        ),
        "single_quarter_operating_cf": DerivationDefinition(
            definition_id="single_quarter_operating_cf",
            version="1",
            output_concept_id="operating_cash_flow",
            input_concept_ids=["operating_cash_flow"],
            expression=(
                "Q1 = Q1_YTD; Q2 = H1_YTD - Q1_YTD; "
                "Q3 = Q3_YTD - H1_YTD; Q4 = FY - Q3_YTD"
            ),
            description="从累计现金流量表值还原单季度经营现金流",
        ),
    }

    # 可以应用单季度派生逻辑的概念列表
    SINGLE_QUARTER_DERIVABLE: list[str] = [
        "revenue",
        "operating_cost",
        "operating_profit",
        "profit_before_tax",
        "net_profit",
        "net_profit_attributable_to_parent",
        "net_profit_excluding_non_recurring",
        "operating_cash_flow",
        "capital_expenditure_cash",
        "net_cash_from_investing",
        "net_cash_from_financing",
    ]

    @classmethod
    def get(cls, definition_id: str) -> DerivationDefinition | None:
        return cls.DERIVATIONS.get(definition_id)

    @classmethod
    def list_all(cls) -> list[DerivationDefinition]:
        return list(cls.DERIVATIONS.values())

    @classmethod
    def is_single_quarter_derivable(cls, concept_id: str) -> bool:
        return concept_id in cls.SINGLE_QUARTER_DERIVABLE
