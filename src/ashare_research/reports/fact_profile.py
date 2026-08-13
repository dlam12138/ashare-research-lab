"""M2 Stage 1 — Markdown 事实档案报告。"""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd


class FactProfileReport:
    """生成结构化的 Markdown 事实报告。"""

    schema_version: str = "1.0"

    def generate(
        self,
        symbol: str,
        fact_repository: Any,
        fact_service: Any,
        output_dir: str,
        git_commit: str = "",
    ) -> str:
        """生成完整的事实档案 Markdown 报告。

        Returns:
            str: 报告文件路径
        """
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        lines: list[str] = []

        # 收集数据
        all_facts = fact_repository.query_facts(symbol=symbol)
        summary = fact_repository.get_fact_summary(symbol)

        # 分类
        df = all_facts
        reported = df[df["is_derived"] == "false"] if not df.empty else df
        derived = df[df["is_derived"] == "true"] if not df.empty else df

        # ── Header ──
        lines.append("# 601857.SH 中国石油 — 官方财务事实档案")
        lines.append("")
        lines.append(f"> 生成时间：{now}")
        lines.append(f"> 数据截至：{now}")
        lines.append(f"> Git 提交：{git_commit or 'N/A'}")
        lines.append("")
        lines.append(
            "> [!IMPORTANT] "
            "本报告仅为官方财务事实层，不包含估值评分、投资判断或买卖建议。"
        )
        lines.append("")

        # ── 1. 公司简介 ──
        lines.append("## 1. 公司和研究范围")
        lines.append("")
        lines.append("| 项目 | 内容 |")
        lines.append("|------|------|")
        lines.append("| 公司 | 中国石油天然气股份有限公司 |")
        lines.append("| 股票代码 | 601857.SH |")
        lines.append("| 公司类型 | cyclical |")
        lines.append("| 报告币种 | CNY |")
        lines.append("| 会计准则 | CAS |")
        lines.append("| 合并口径 | consolidated |")
        lines.append("| 研究年度 | 2021—2025 |")
        lines.append("| 研究季度 | 2024Q2—2026Q1 |")
        lines.append("")

        # ── 2. 官方来源 ──
        lines.append("## 2. 官方来源")
        lines.append("")
        lines.append("- AKShare 财务数据接口（stock_financial_*_by_report_em）")
        lines.append("- 来源级别：二级（第三方聚合接口，需交叉核验）")
        lines.append("")

        # ── 3. 事实摘要 ──
        lines.append("## 3. 数据摘要")
        lines.append("")
        total = summary.get("total", 0)
        lines.append(f"- 已报告事实：{summary.get('total', 0) - summary.get('derived', 0)} 条")
        lines.append(f"- 派生事实：{summary.get('derived', 0)} 条")
        lines.append(f"- 总计：{total} 条")
        lines.append(f"- verified：{summary.get('verified', 0)} 条")
        lines.append(f"- reconciled：{summary.get('reconciled', 0)} 条")
        lines.append(f"- unverified：{summary.get('unverified', 0)} 条")
        lines.append("")

        # ── 4. 年度利润表 ──
        lines.append("## 4. 年度利润表")
        lines.append("")
        income_concepts = [
            "revenue", "operating_profit", "profit_before_tax",
            "net_profit_attributable_to_parent",
            "net_profit_excluding_non_recurring",
            "basic_eps",
        ]
        income_df = reported[
            reported["concept_id"].isin(income_concepts)
        ] if not reported.empty else pd.DataFrame()
        if not income_df.empty:
            lines.append(_build_pivot_table(
                income_df, income_concepts, "Annual Income Statement"
            ))
        else:
            lines.append("（暂无数据）")
        lines.append("")

        # ── 5. 年度资产负债表 ──
        lines.append("## 5. 年度资产负债表（时点值）")
        lines.append("")
        bs_concepts = [
            "total_assets", "total_liabilities",
            "equity_attributable_to_parent", "share_capital",
            "monetary_funds", "interest_bearing_debt",
        ]
        bs_df = reported[
            reported["concept_id"].isin(bs_concepts)
        ] if not reported.empty else pd.DataFrame()
        if not bs_df.empty:
            lines.append(_build_pivot_table(
                bs_df, bs_concepts, "Annual Balance Sheet"
            ))
        else:
            lines.append("（暂无数据）")
        lines.append("")

        # ── 6. 年度现金流量表 ──
        lines.append("## 6. 年度现金流量表")
        lines.append("")
        cf_concepts = [
            "operating_cash_flow", "capital_expenditure_cash",
            "free_cash_flow",
        ]
        cf_df = reported[
            reported["concept_id"].isin(cf_concepts)
        ] if not reported.empty else pd.DataFrame()
        if not cf_df.empty:
            lines.append(_build_pivot_table(
                cf_df, cf_concepts, "Annual Cash Flow"
            ))
        else:
            lines.append("（暂无数据）")
        lines.append("")

        # ── 7. 单季度派生 ──
        lines.append("## 7. 单季度派生事实")
        lines.append("")
        if not derived.empty:
            sq_derived = derived[derived["report_type"].str.contains(
                "single_q", na=False
            )]
            lines.append(f"单季度派生事实：{len(sq_derived)} 条")
        else:
            lines.append("（暂无派生事实）")
        lines.append("")

        # ── 8. 阶段声明 ──
        lines.append("## 8. 阶段声明")
        lines.append("")
        lines.append(
            "本报告仅展示 Milestone 2 Stage 1 的官方财务事实层。"
        )
        lines.append("以下内容尚未实现：")
        lines.append("- 企业质量评分")
        lines.append("- 估值吸引力分析")
        lines.append("- 现金流质量评估")
        lines.append("- 财务安全评分")
        lines.append("- 风险否决项检查")
        lines.append("- 投资结论或买卖建议")
        lines.append("")

        # ── 写入文件 ──
        output_path = Path(output_dir) / symbol / f"{symbol}.fact_profile.md"
        output_path.parent.mkdir(parents=True, exist_ok=True)

        content = "\n".join(lines)

        # 原子写入
        tmp_path = output_path.parent / f".{output_path.name}.tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            f.write(content)
        os.replace(tmp_path, str(output_path))

        return str(output_path)


def _build_pivot_table(
    df: pd.DataFrame, concept_ids: list[str], title: str,
) -> str:
    """构建概念×年度的 Markdown 表格。"""
    lines: list[str] = []

    if df.empty:
        return f"（{title}：暂无数据）"

    # 按 concept_id + 财年 构建
    from ashare_research.facts.concepts import ConceptRegistry

    # 获取可用财年
    years = sorted(df["fiscal_year"].dropna().unique())

    if not len(years):
        return f"（{title}：无财年数据）"

    # 表头
    header = "| 指标 | " + " | ".join(str(y) for y in years) + " |"
    sep = "|" + "|".join(" --- " for _ in range(len(years) + 1)) + "|"
    lines.append(header)
    lines.append(sep)

    # 数据行
    for cid in concept_ids:
        concept = ConceptRegistry.get(cid)
        name = concept.display_name_zh if concept else cid
        row_vals = [name]
        for year in years:
            match = df[
                (df["concept_id"] == cid)
                & (df["fiscal_year"] == year)
            ]
            if not match.empty:
                val = match.iloc[0]["value"]
                if isinstance(val, float) and abs(val) >= 1e8:
                    row_vals.append(f"{val / 1e8:.2f} 亿")
                else:
                    row_vals.append(str(val))
            else:
                row_vals.append("—")
        lines.append("| " + " | ".join(row_vals) + " |")

    return "\n".join(lines)
