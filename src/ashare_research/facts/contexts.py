"""M2 Stage 1 — FactContext 构建与解析。

每个财务事实必须关联一个明确的 context：
    哪家公司 + 哪个期间 + 什么口径 + 是否重述
"""

from __future__ import annotations

from datetime import datetime

from ashare_research.facts.models import (
    ConsolidationScope,
    FactContext,
    InstantOrDuration,
    PeriodType,
)


def build_context_id(
    symbol: str,
    fiscal_year: int,
    period_type: str,
    consolidation_scope: str = "consolidated",
) -> str:
    """构建唯一 context_id。

    context_id 跨重述保持稳定：它只标识“哪家公司 + 哪个期间 + 什么
    口径”这一经济现实，不包含 ``restatement_version``。重述
    (original -> restated_1) 是对同一 context 的重新报告，因此
    ``restatement_version`` 作为事实级属性沿版本链变化，而
    ``context_id`` 不变。这是 ``VersionChainValidator`` 检查 C
    （要求 context_id 跨版本一致）与真实重述版本链同时成立的必要
    条件。

    格式: SYMBOL|FY|PERIOD_TYPE|SCOPE
    示例: 601857.SH|2025|annual|consolidated
    """
    return f"{symbol}|{fiscal_year}|{period_type}|{consolidation_scope}"


def parse_context_id(context_id: str) -> dict[str, str | int]:
    """解析 context_id 为各组成部分。

    restatement_version 不再编码进 context_id，故不在此返回；
    事实的 restatement_version 应从事实行本身读取。
    """
    parts = context_id.split("|")
    keys = ["symbol", "fiscal_year", "period_type",
            "consolidation_scope"]
    result: dict[str, str | int] = {}
    for i, key in enumerate(keys):
        if i < len(parts):
            result[key] = int(parts[i]) if key == "fiscal_year" else parts[i]
    return result


def parse_period_type(period_type: str) -> PeriodType:
    """标准化期间类型字符串。"""
    mapping = {
        "annual": PeriodType.annual,
        "FY": PeriodType.annual,
        "Q1": PeriodType.quarter_ytd,
        "Q2": PeriodType.half_year_ytd,
        "Q3": PeriodType.three_quarter_ytd,
        "Q4": PeriodType.quarter_ytd,
        "quarter_ytd": PeriodType.quarter_ytd,
        "half_year_ytd": PeriodType.half_year_ytd,
        "three_quarter_ytd": PeriodType.three_quarter_ytd,
        "single_quarter": PeriodType.single_quarter,
        "instant": PeriodType.instant,
    }
    return mapping.get(period_type, PeriodType.annual)


def parse_period_label(label: str) -> dict:
    """解析期间标签如 '2021FY', '2024Q2', '2025H1'。

    Returns:
        dict with keys: fiscal_year, period_type, quarter (if applicable)
    """
    import re

    # 2021FY, 2021 年度
    m = re.match(r"^(\d{4})\s*(FY|年度)?$", label)
    if m:
        return {"fiscal_year": int(m.group(1)),
                "period_type": "annual", "quarter": None}

    # 2024Q2, 2025Q3_YTD
    m = re.match(r"^(\d{4})\s*Q([1-4])(?:_YTD)?$", label)
    if m:
        q = int(m.group(2))
        ptype = {
            1: "quarter_ytd", 2: "half_year_ytd",
            3: "three_quarter_ytd", 4: "quarter_ytd",
        }
        return {"fiscal_year": int(m.group(1)),
                "period_type": ptype[q], "quarter": q}

    # 2025H1
    m = re.match(r"^(\d{4})\s*H([12])$", label)
    if m:
        return {"fiscal_year": int(m.group(1)),
                "period_type": "half_year_ytd", "quarter": None}

    return {"fiscal_year": None, "period_type": "annual", "quarter": None}


def is_duration(period_type: PeriodType) -> bool:
    """区间型事实（利润表/现金流量表值）可以相减。"""
    return period_type not in (PeriodType.instant,)


def is_instant(period_type: PeriodType) -> bool:
    """时点型事实（资产负债表值）不得相减。"""
    return period_type == PeriodType.instant


def compute_period_dates(
    fiscal_year: int, period_type: PeriodType
) -> tuple[str, str]:
    """计算期间的起止日期。

    Returns:
        (period_start, period_end) as YYYY-MM-DD
    """
    if period_type == PeriodType.annual:
        return f"{fiscal_year}-01-01", f"{fiscal_year}-12-31"
    if period_type == PeriodType.quarter_ytd:
        return f"{fiscal_year}-01-01", f"{fiscal_year}-03-31"
    if period_type == PeriodType.half_year_ytd:
        return f"{fiscal_year}-01-01", f"{fiscal_year}-06-30"
    if period_type == PeriodType.three_quarter_ytd:
        return f"{fiscal_year}-01-01", f"{fiscal_year}-09-30"
    if period_type == PeriodType.single_quarter:
        return "", ""
    if period_type == PeriodType.instant:
        return f"{fiscal_year}-12-31", f"{fiscal_year}-12-31"
    return "", ""


def create_context(
    symbol: str,
    fiscal_year: int,
    period_type: str,
    consolidation_scope: str = "consolidated",
    filing_date: str = "",
    source_document: str = "",
    restatement_version: str = "original",
    accounting_standard: str = "CAS",
) -> FactContext:
    """便捷创建 FactContext。

    ``restatement_version`` 仅存入 FactContext 的同名名义字段，
    不进入 ``context_id``（见 :func:`build_context_id`）。
    """
    pt = parse_period_type(period_type)
    start, end = compute_period_dates(fiscal_year, pt)

    return FactContext(
        context_id=build_context_id(
            symbol, fiscal_year, period_type,
            consolidation_scope,
        ),
        symbol=symbol,
        fiscal_year=fiscal_year,
        period_type=pt,
        period_start=start,
        period_end=end,
        instant_or_duration=(
            InstantOrDuration.instant
            if pt == PeriodType.instant
            else InstantOrDuration.duration
        ),
        consolidation_scope=ConsolidationScope(consolidation_scope),
        accounting_standard=accounting_standard,
        restatement_version=restatement_version,
        source_document=source_document,
        filing_date=filing_date,
        created_at=datetime.now().isoformat(),
    )
