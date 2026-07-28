"""M2 Stage 1 — 统一财务事实模型。

定义 Fact, FactContext, Concept, ReportedFact, DerivedFact 等核心数据结构。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

# ── 枚举 ────────────────────────────────────────────────────


class PeriodType(StrEnum):
    annual = "annual"
    quarter_ytd = "quarter_ytd"
    half_year_ytd = "half_year_ytd"
    three_quarter_ytd = "three_quarter_ytd"
    single_quarter = "single_quarter"
    instant = "instant"


class InstantOrDuration(StrEnum):
    instant = "instant"
    duration = "duration"


class ConsolidationScope(StrEnum):
    consolidated = "consolidated"
    parent_company = "parent_company"
    unknown = "unknown"


class VerificationStatus(StrEnum):
    verified = "verified"
    reconciled = "reconciled"
    unverified = "unverified"
    mismatch = "mismatch"
    missing = "missing"
    not_applicable = "not_applicable"


class ConceptCategory(StrEnum):
    balance_sheet = "balance_sheet"
    income_statement = "income_statement"
    cash_flow = "cash_flow"
    dividend = "dividend"
    buyback = "buyback"
    shareholder_increase = "shareholder_increase"
    audit_report = "audit_report"
    per_share = "per_share"


class ReportType(StrEnum):
    annual = "annual"
    q1 = "q1"
    half_year = "half_year"
    q3 = "q3"
    quarterly = "quarterly"


class SourceTier(StrEnum):
    candidate_aggregator = "candidate_aggregator"
    company_official = "company_official"
    exchange_official = "exchange_official"


# ── 核心数据类 ──────────────────────────────────────────────


@dataclass
class FactContext:
    """财务事实上下文 — 报告期 + 口径 + 重述版本。

    格式: SYMBOL|FY|PERIOD_TYPE|SCOPE
    示例: 601857.SH|2025|annual|consolidated
    重述版本不编码进 context_id，见 facts.contexts.build_context_id。
    """
    context_id: str
    symbol: str
    fiscal_year: int
    period_type: PeriodType
    period_start: str = ""      # YYYY-MM-DD
    period_end: str = ""        # YYYY-MM-DD
    instant_or_duration: InstantOrDuration = InstantOrDuration.duration
    consolidation_scope: ConsolidationScope = ConsolidationScope.consolidated
    accounting_standard: str = "CAS"
    restatement_version: str = "original"
    source_document: str = ""
    filing_date: str = ""       # 公告日期 YYYY-MM-DD
    created_at: str = ""


@dataclass
class Concept:
    """版本化概念定义。

    每个财务指标对应一个唯一 concept_id，不得在代码中随处手写指标名。
    """
    concept_id: str
    version: str = "1"
    display_name: str = ""
    display_name_zh: str = ""
    description: str = ""
    parent_concept_id: str = ""
    category: ConceptCategory = ConceptCategory.income_statement
    statement_type: str = ""
    instant_or_duration: InstantOrDuration = InstantOrDuration.duration
    canonical_unit: str = "CNY"
    allowed_scopes: list[str] = field(default_factory=lambda: ["consolidated"])
    aliases: list[str] = field(default_factory=list)
    created_at: str = ""


@dataclass
class Fact:
    """财务事实 — 原子级数据点。

    每个 Fact 对应 (concept_id, symbol, context_id) 的唯一组合。
    同时包含原始值和标准化值的完整追踪。
    """
    fact_id: str = ""
    fact_version: int = 1
    concept_id: str = ""
    concept_version: str = "1"
    symbol: str = ""
    value: float | None = None
    unit: str = ""
    context_id: str = ""
    is_derived: bool = field(default=False)
    derived_from: str = ""               # 逗号分隔的源 fact_id
    supersedes_fact_id: str = ""
    derivation_definition_id: str = ""
    derivation_version: str = ""
    input_fact_ids: str = ""             # 逗号分隔
    source_provider: str = ""
    source_document: str = ""
    source_page: str = ""
    source_table: str = ""
    source_label: str = ""
    source_tier: SourceTier = SourceTier.candidate_aggregator
    source_id: str = ""
    source_url: str = ""
    source_hash: str = ""
    filing_date: str = ""               # 财报公告日期
    period_end: str = ""                # 报告期截止日
    restatement_version: str = "original"
    announcement_date: str = ""          # 此事实可用的日期
    available_at: str = ""              # PIT 门禁字段
    raw_value: float | None = None
    raw_unit: str = ""
    normalized_value: float | None = None
    normalization_rule: str = ""
    verification_status: VerificationStatus = VerificationStatus.unverified
    verification_note: str = ""
    eligible_for_metrics: bool = False
    created_at: str = ""


@dataclass
class ReportedFact(Fact):
    """直接来自官方披露的事实（非派生）。

    is_derived 始终为 False。
    """
    is_derived: bool = False


@dataclass
class DerivedFact(Fact):
    """通过版本化公式从 ReportedFact 生成的事实。

    is_derived 始终为 True，必须记录 derivation_definition_id 和 input_fact_ids。
    """
    is_derived: bool = True


@dataclass
class FactSet:
    """事实集合 — 包含所有已报告和派生事实以及元数据。"""
    schema_version: str = "1.0"
    symbol: str = ""
    reported_facts: list[Fact] = field(default_factory=list)
    derived_facts: list[Fact] = field(default_factory=list)
    contexts: list[FactContext] = field(default_factory=list)
    concepts: list[Concept] = field(default_factory=list)
    generated_at: str = ""
    git_commit: str = ""
