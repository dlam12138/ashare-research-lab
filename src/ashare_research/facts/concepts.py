"""M2 Stage 1 — 版本化概念注册表。

每个财务指标必须有稳定的 concept_id，不得在代码中随处手写。
"""

from __future__ import annotations

from ashare_research.facts.models import Concept, ConceptCategory, InstantOrDuration


class ConceptRegistry:
    """财务概念注册表。

    用法:
        registry = ConceptRegistry()
        concept = registry.get("revenue")
        income_items = registry.get_by_category(ConceptCategory.income_statement)
    """

    schema_version: str = "2.0"

    # 静态概念定义 — 外层 key 为 concept_id，内层 key 为版本号
    CONCEPTS: dict[str, dict[str, Concept]] = {
        # ── 利润表 ──
        "revenue": {
            "1": Concept(
                concept_id="revenue", version="1",
                display_name="Revenue", display_name_zh="营业收入",
                category=ConceptCategory.income_statement,
                canonical_unit="CNY",
                aliases=["营业收入", "营业总收入"],
            ),
        },
        "operating_cost": {
            "1": Concept(
                concept_id="operating_cost", version="1",
                display_name="Operating Cost", display_name_zh="营业成本",
                category=ConceptCategory.income_statement,
                canonical_unit="CNY",
                aliases=["营业成本"],
            ),
        },
        "operating_profit": {
            "1": Concept(
                concept_id="operating_profit", version="1",
                display_name="Operating Profit", display_name_zh="营业利润",
                category=ConceptCategory.income_statement,
                canonical_unit="CNY",
                aliases=["营业利润"],
            ),
        },
        "profit_before_tax": {
            "1": Concept(
                concept_id="profit_before_tax", version="1",
                display_name="Profit Before Tax", display_name_zh="利润总额",
                category=ConceptCategory.income_statement,
                canonical_unit="CNY",
                aliases=["利润总额"],
            ),
        },
        "net_profit": {
            "1": Concept(
                concept_id="net_profit", version="1",
                display_name="Net Profit", display_name_zh="净利润",
                category=ConceptCategory.income_statement,
                canonical_unit="CNY",
                aliases=["净利润"],
            ),
        },
        "net_profit_attributable_to_parent": {
            "1": Concept(
                concept_id="net_profit_attributable_to_parent", version="1",
                display_name="Net Profit Attributable to Parent",
                display_name_zh="归属于母公司股东的净利润",
                category=ConceptCategory.income_statement,
                canonical_unit="CNY",
                aliases=["归属于母公司所有者的净利润", "归母净利润"],
            ),
        },
        "net_profit_excluding_non_recurring": {
            "1": Concept(
                concept_id="net_profit_excluding_non_recurring", version="1",
                display_name="Net Profit Excl. Non-Recurring",
                display_name_zh="扣除非经常性损益后净利润",
                category=ConceptCategory.income_statement,
                canonical_unit="CNY",
                aliases=["扣非净利润", "归属于母公司所有者的扣除非经常性损益净利润"],
            ),
        },
        "basic_eps": {
            "1": Concept(
                concept_id="basic_eps", version="1",
                display_name="Basic EPS", display_name_zh="基本每股收益",
                category=ConceptCategory.per_share,
                canonical_unit="CNY_PER_SHARE",
                aliases=["基本每股收益"],
            ),
        },
        "diluted_eps": {
            "1": Concept(
                concept_id="diluted_eps", version="1",
                display_name="Diluted EPS", display_name_zh="稀释每股收益",
                category=ConceptCategory.per_share,
                canonical_unit="CNY_PER_SHARE",
                aliases=["稀释每股收益"],
            ),
        },

        # ── 现金流量表 ──
        "operating_cash_flow": {
            "1": Concept(
                concept_id="operating_cash_flow", version="1",
                display_name="Operating Cash Flow",
                display_name_zh="经营活动现金流净额",
                category=ConceptCategory.cash_flow,
                canonical_unit="CNY",
                aliases=["经营活动产生的现金流量净额", "经营活动现金净流量"],
            ),
        },
        "cash_paid_for_fixed_assets": {
            "1": Concept(
                concept_id="cash_paid_for_fixed_assets", version="1",
                display_name="Cash Paid for Fixed Assets",
                display_name_zh="购建固定资产无形资产支付的现金",
                category=ConceptCategory.cash_flow,
                canonical_unit="CNY",
                aliases=["购建固定资产、无形资产和其他长期资产支付的现金"],
            ),
        },
        "cash_paid_for_intangible_assets": {
            "1": Concept(
                concept_id="cash_paid_for_intangible_assets", version="1",
                display_name="Cash Paid for Intangible Assets",
                display_name_zh="购建无形资产支付的现金",
                category=ConceptCategory.cash_flow,
                canonical_unit="CNY",
            ),
        },
        "cash_paid_for_long_term_assets": {
            "1": Concept(
                concept_id="cash_paid_for_long_term_assets", version="1",
                display_name="Cash Paid for Long-Term Assets",
                display_name_zh="购建长期资产支付的现金",
                category=ConceptCategory.cash_flow,
                canonical_unit="CNY",
            ),
        },
        "capital_expenditure_cash": {
            "1": Concept(
                concept_id="capital_expenditure_cash", version="1",
                display_name="Capital Expenditure (Cash)",
                display_name_zh="资本开支（现金）",
                category=ConceptCategory.cash_flow,
                canonical_unit="CNY",
                aliases=["资本支出"],
            ),
        },
        "free_cash_flow": {
            "1": Concept(
                concept_id="free_cash_flow", version="1",
                display_name="Free Cash Flow", display_name_zh="自由现金流",
                category=ConceptCategory.cash_flow,
                canonical_unit="CNY",
            ),
        },
        "net_cash_from_investing": {
            "1": Concept(
                concept_id="net_cash_from_investing", version="1",
                display_name="Net Cash from Investing",
                display_name_zh="投资活动现金流净额",
                category=ConceptCategory.cash_flow,
                canonical_unit="CNY",
                aliases=["投资活动产生的现金流量净额"],
            ),
        },
        "net_cash_from_financing": {
            "1": Concept(
                concept_id="net_cash_from_financing", version="1",
                display_name="Net Cash from Financing",
                display_name_zh="筹资活动现金流净额",
                category=ConceptCategory.cash_flow,
                canonical_unit="CNY",
                aliases=["筹资活动产生的现金流量净额"],
            ),
        },

        # ── 资产负债表（时点值） ──
        "cash_and_cash_equivalents": {
            "1": Concept(
                concept_id="cash_and_cash_equivalents", version="1",
                display_name="Cash and Cash Equivalents",
                display_name_zh="现金及现金等价物",
                category=ConceptCategory.balance_sheet,
                canonical_unit="CNY",
                instant_or_duration=InstantOrDuration.instant,
                aliases=["现金及现金等价物余额"],
            ),
        },
        "monetary_funds": {
            "1": Concept(
                concept_id="monetary_funds", version="1",
                display_name="Monetary Funds", display_name_zh="货币资金",
                category=ConceptCategory.balance_sheet,
                canonical_unit="CNY",
                instant_or_duration=InstantOrDuration.instant,
                aliases=["货币资金"],
            ),
        },
        "short_term_borrowings": {
            "1": Concept(
                concept_id="short_term_borrowings", version="1",
                display_name="Short-Term Borrowings",
                display_name_zh="短期借款",
                category=ConceptCategory.balance_sheet,
                canonical_unit="CNY",
                instant_or_duration=InstantOrDuration.instant,
                aliases=["短期借款"],
            ),
        },
        "long_term_borrowings": {
            "1": Concept(
                concept_id="long_term_borrowings", version="1",
                display_name="Long-Term Borrowings",
                display_name_zh="长期借款",
                category=ConceptCategory.balance_sheet,
                canonical_unit="CNY",
                instant_or_duration=InstantOrDuration.instant,
                aliases=["长期借款"],
            ),
        },
        "bonds_payable": {
            "1": Concept(
                concept_id="bonds_payable", version="1",
                display_name="Bonds Payable", display_name_zh="应付债券",
                category=ConceptCategory.balance_sheet,
                canonical_unit="CNY",
                instant_or_duration=InstantOrDuration.instant,
                aliases=["应付债券"],
            ),
        },
        "lease_liabilities": {
            "1": Concept(
                concept_id="lease_liabilities", version="1",
                display_name="Lease Liabilities", display_name_zh="租赁负债",
                category=ConceptCategory.balance_sheet,
                canonical_unit="CNY",
                instant_or_duration=InstantOrDuration.instant,
                aliases=["租赁负债"],
            ),
        },
        "interest_bearing_debt": {
            "1": Concept(
                concept_id="interest_bearing_debt", version="1",
                display_name="Interest-Bearing Debt", display_name_zh="有息负债",
                category=ConceptCategory.balance_sheet,
                canonical_unit="CNY",
                instant_or_duration=InstantOrDuration.instant,
            ),
        },
        "total_assets": {
            "1": Concept(
                concept_id="total_assets", version="1",
                display_name="Total Assets", display_name_zh="资产总计",
                category=ConceptCategory.balance_sheet,
                canonical_unit="CNY",
                instant_or_duration=InstantOrDuration.instant,
                aliases=["资产总计", "总资产"],
            ),
        },
        "total_liabilities": {
            "1": Concept(
                concept_id="total_liabilities", version="1",
                display_name="Total Liabilities", display_name_zh="负债合计",
                category=ConceptCategory.balance_sheet,
                canonical_unit="CNY",
                instant_or_duration=InstantOrDuration.instant,
                aliases=["负债合计", "总负债"],
            ),
        },
        "total_current_assets": {
            "1": Concept(
                concept_id="total_current_assets", version="1",
                display_name="Total Current Assets",
                display_name_zh="流动资产合计",
                category=ConceptCategory.balance_sheet,
                canonical_unit="CNY",
                instant_or_duration=InstantOrDuration.instant,
                aliases=["流动资产合计"],
            ),
        },
        "total_current_liabilities": {
            "1": Concept(
                concept_id="total_current_liabilities", version="1",
                display_name="Total Current Liabilities",
                display_name_zh="流动负债合计",
                category=ConceptCategory.balance_sheet,
                canonical_unit="CNY",
                instant_or_duration=InstantOrDuration.instant,
                aliases=["流动负债合计"],
            ),
        },
        "equity_attributable_to_parent": {
            "1": Concept(
                concept_id="equity_attributable_to_parent", version="1",
                display_name="Equity Attributable to Parent",
                display_name_zh="归属于母公司股东权益",
                category=ConceptCategory.balance_sheet,
                canonical_unit="CNY",
                instant_or_duration=InstantOrDuration.instant,
                aliases=["归属于母公司所有者权益", "归母权益"],
            ),
        },
        "total_equity": {
            "1": Concept(
                concept_id="total_equity", version="1",
                display_name="Total Equity", display_name_zh="股东权益合计",
                category=ConceptCategory.balance_sheet,
                canonical_unit="CNY",
                instant_or_duration=InstantOrDuration.instant,
                aliases=["所有者权益合计", "股东权益合计"],
            ),
        },
        "share_capital": {
            "1": Concept(
                concept_id="share_capital", version="1",
                display_name="Share Capital", display_name_zh="股本",
                category=ConceptCategory.balance_sheet,
                canonical_unit="CNY",
                instant_or_duration=InstantOrDuration.instant,
                aliases=["实收资本", "股本"],
            ),
        },
        "intangible_assets": {
            "1": Concept(
                concept_id="intangible_assets", version="1",
                display_name="Intangible Assets", display_name_zh="无形资产",
                category=ConceptCategory.balance_sheet,
                canonical_unit="CNY",
                instant_or_duration=InstantOrDuration.instant,
            ),
        },
        "goodwill": {
            "1": Concept(
                concept_id="goodwill", version="1",
                display_name="Goodwill", display_name_zh="商誉",
                category=ConceptCategory.balance_sheet,
                canonical_unit="CNY",
                instant_or_duration=InstantOrDuration.instant,
            ),
        },
        "inventories": {
            "1": Concept(
                concept_id="inventories", version="1",
                display_name="Inventories", display_name_zh="存货",
                category=ConceptCategory.balance_sheet,
                canonical_unit="CNY",
                instant_or_duration=InstantOrDuration.instant,
            ),
        },
        "accounts_receivable": {
            "1": Concept(
                concept_id="accounts_receivable", version="1",
                display_name="Accounts Receivable", display_name_zh="应收账款",
                category=ConceptCategory.balance_sheet,
                canonical_unit="CNY",
                instant_or_duration=InstantOrDuration.instant,
            ),
        },

        # ── 股东回报 ──
        "cash_dividend_total": {
            "1": Concept(
                concept_id="cash_dividend_total", version="1",
                display_name="Cash Dividend Total",
                display_name_zh="现金分红总额",
                category=ConceptCategory.dividend,
                canonical_unit="CNY",
                aliases=["现金分红总额", "分红总额"],
            ),
        },
        "cash_dividend_per_share": {
            "1": Concept(
                concept_id="cash_dividend_per_share", version="1",
                display_name="Cash Dividend Per Share",
                display_name_zh="每股现金分红",
                category=ConceptCategory.dividend,
                canonical_unit="CNY_PER_SHARE",
                aliases=["每股股利", "每股分红"],
            ),
        },
        "dividend_payout_ratio": {
            "1": Concept(
                concept_id="dividend_payout_ratio", version="1",
                display_name="Dividend Payout Ratio",
                display_name_zh="分红支付率",
                category=ConceptCategory.dividend,
                canonical_unit="DECIMAL",
            ),
        },
        "shares_repurchased": {
            "1": Concept(
                concept_id="shares_repurchased", version="1",
                display_name="Shares Repurchased", display_name_zh="回购股数",
                category=ConceptCategory.buyback,
                canonical_unit="SHARE",
            ),
        },
        "repurchase_amount": {
            "1": Concept(
                concept_id="repurchase_amount", version="1",
                display_name="Repurchase Amount", display_name_zh="回购金额",
                category=ConceptCategory.buyback,
                canonical_unit="CNY",
            ),
        },
        "ownership_increase_shares": {
            "1": Concept(
                concept_id="ownership_increase_shares", version="1",
                display_name="Ownership Increase Shares",
                display_name_zh="增持股数",
                category=ConceptCategory.shareholder_increase,
                canonical_unit="SHARE",
            ),
        },
        "ownership_increase_amount": {
            "1": Concept(
                concept_id="ownership_increase_amount", version="1",
                display_name="Ownership Increase Amount",
                display_name_zh="增持金额",
                category=ConceptCategory.shareholder_increase,
                canonical_unit="CNY",
            ),
        },

        # ── 审计与报告 ──
        "audit_opinion": {
            "1": Concept(
                concept_id="audit_opinion", version="1",
                display_name="Audit Opinion", display_name_zh="审计意见",
                category=ConceptCategory.audit_report,
                canonical_unit="TEXT",
            ),
        },
        "going_concern_uncertainty": {
            "1": Concept(
                concept_id="going_concern_uncertainty", version="1",
                display_name="Going Concern Uncertainty",
                display_name_zh="持续经营重大不确定性",
                category=ConceptCategory.audit_report,
                canonical_unit="BOOLEAN",
            ),
        },
        "financial_restatement": {
            "1": Concept(
                concept_id="financial_restatement", version="1",
                display_name="Financial Restatement",
                display_name_zh="财务重述",
                category=ConceptCategory.audit_report,
                canonical_unit="BOOLEAN",
            ),
        },
        "report_currency": {
            "1": Concept(
                concept_id="report_currency", version="1",
                display_name="Report Currency", display_name_zh="报告币种",
                category=ConceptCategory.audit_report,
                canonical_unit="TEXT",
            ),
        },
        "accounting_standard": {
            "1": Concept(
                concept_id="accounting_standard", version="1",
                display_name="Accounting Standard",
                display_name_zh="会计准则",
                category=ConceptCategory.audit_report,
                canonical_unit="TEXT",
            ),
        },
    }

    @classmethod
    def _resolve_default(cls, versions: dict[str, Concept]) -> Concept | None:
        """从版本字典中解析默认版本（优先 version="1"，否则返回任意版本）。"""
        if not versions:
            return None
        return versions.get("1") or next(iter(versions.values()))

    @classmethod
    def get(cls, concept_id: str) -> Concept | None:
        """按 ID 获取概念定义（向后兼容，返回默认版本）。"""
        versions = cls.CONCEPTS.get(concept_id)
        if versions is None:
            return None
        return cls._resolve_default(versions)

    @classmethod
    def get_versioned(cls, concept_id: str, version: str = "1") -> Concept | None:
        """按 ID 和版本获取概念定义。"""
        versions = cls.CONCEPTS.get(concept_id)
        if versions is None:
            return None
        return versions.get(version)

    @classmethod
    def get_by_category(cls, category: ConceptCategory) -> list[Concept]:
        """获取指定分类下所有概念（每个 concept_id 返回默认版本）。"""
        result: list[Concept] = []
        for versions in cls.CONCEPTS.values():
            c = cls._resolve_default(versions)
            if c is not None and c.category == category:
                result.append(c)
        return result

    @classmethod
    def is_registered(cls, concept_id: str) -> bool:
        """检查概念是否已注册。"""
        return concept_id in cls.CONCEPTS

    @classmethod
    def list_all(cls) -> list[Concept]:
        """列出所有注册概念（每个 concept_id 返回默认版本）。"""
        result: list[Concept] = []
        for versions in cls.CONCEPTS.values():
            c = cls._resolve_default(versions)
            if c is not None:
                result.append(c)
        return result

    @classmethod
    def get_canonical_unit(cls, concept_id: str) -> str:
        """获取概念的标准单位。"""
        c = cls.get(concept_id)
        return c.canonical_unit if c else ""

    @classmethod
    def is_instant(cls, concept_id: str) -> bool:
        """判断概念是否为时点值（资产负债表）。"""
        c = cls.get(concept_id)
        return (
            c.instant_or_duration == InstantOrDuration.instant
            if c else False
        )
