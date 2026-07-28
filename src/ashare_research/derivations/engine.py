"""M2 Stage 1 — 派生事实计算引擎。

仅实现：单季度还原、自由现金流、有息负债。
不实现 TTM、YoY、CAGR 或任何评分指标。
"""

from __future__ import annotations

import logging
from datetime import datetime

import pandas as pd

from ashare_research.facts.identity import build_fact_id

logger = logging.getLogger(__name__)


class DerivationEngine:
    """派生事实计算引擎。"""

    schema_version: str = "1.0"

    @staticmethod
    def derive_single_quarter(
        facts_df: pd.DataFrame,
        concept_id: str,
    ) -> list[dict]:
        """从累计值还原单季度值。

        规则:
            Q1 = Q1_YTD 直接使用
            Q2 = H1_YTD - Q1_YTD
            Q3 = Q3_YTD - H1_YTD
            Q4 = FY - Q3_YTD

        Args:
            facts_df: 含 concept_id, value, fiscal_year, report_type, period_end 列
            concept_id: 要还原的概念ID

        Returns:
            list of dict: derived fact entries
        """
        df = facts_df[facts_df["concept_id"] == concept_id].copy()
        if df.empty:
            return []

        # 按财年分组
        derived: list[dict] = []
        now = datetime.now().isoformat()

        for year in df["fiscal_year"].unique():
            year_df = df[df["fiscal_year"] == year]
            # 按 report_type 索引
            by_type = {}
            for _, row in year_df.iterrows():
                by_type[row["report_type"]] = row

            # 取本财年首个可用 symbol（同财年同概念应一致）
            symbol = str(year_df.iloc[0]["symbol"])

            # Q1 直接使用 Q1_YTD
            if "Q1" in by_type:
                derived.append(_make_single_q_fact(
                    by_type["Q1"], concept_id, 1, "Q1", now,
                ))

            # Q2 = H1 - Q1
            if "H1" in by_type and "Q1" in by_type:
                val = by_type["H1"]["value"] - by_type["Q1"]["value"]
                derived.append(_make_single_q_fact_dict(
                    concept_id, year, 2, "Q2", val, now,
                    [by_type["H1"]["fact_id"], by_type["Q1"]["fact_id"]],
                    symbol=symbol,
                ))

            # Q3 = Q3_YTD - H1
            if "Q3" in by_type and "H1" in by_type:
                val = by_type["Q3"]["value"] - by_type["H1"]["value"]
                derived.append(_make_single_q_fact_dict(
                    concept_id, year, 3, "Q3", val, now,
                    [by_type["Q3"]["fact_id"], by_type["H1"]["fact_id"]],
                    symbol=symbol,
                ))

            # Q4 = FY - Q3_YTD
            if "FY" in by_type and "Q3" in by_type:
                val = by_type["FY"]["value"] - by_type["Q3"]["value"]
                derived.append(_make_single_q_fact_dict(
                    concept_id, year, 4, "Q4", val, now,
                    [by_type["FY"]["fact_id"], by_type["Q3"]["fact_id"]],
                    symbol=symbol,
                ))

        return derived

    @staticmethod
    def derive_free_cash_flow(
        facts_df: pd.DataFrame,
    ) -> list[dict]:
        """计算自由现金流 = 经营现金流 - 资本开支。"""
        ocf = facts_df[facts_df["concept_id"] == "operating_cash_flow"]
        capex = facts_df[
            facts_df["concept_id"] == "capital_expenditure_cash"
        ]
        if ocf.empty or capex.empty:
            return []

        now = datetime.now().isoformat()
        derived: list[dict] = []

        for _, ocf_row in ocf.iterrows():
            year = ocf_row["fiscal_year"]
            rtype = ocf_row["report_type"]
            capex_match = capex[
                (capex["fiscal_year"] == year)
                & (capex["report_type"] == rtype)
            ]
            if capex_match.empty:
                continue

            fcf_val = ocf_row["value"] - capex_match.iloc[0]["value"]
            derived.append(_make_single_q_fact_dict(
                "free_cash_flow", year, 0, rtype, fcf_val, now,
                [ocf_row["fact_id"], capex_match.iloc[0]["fact_id"]],
                derivation_id="free_cash_flow",
                symbol=str(ocf_row["symbol"]),
                period_end=str(ocf_row.get("period_end", "")),
            ))

        return derived

    @staticmethod
    def derive_interest_bearing_debt(
        facts_df: pd.DataFrame,
    ) -> list[dict]:
        """计算有息负债（仅时点值，资产负债表）。"""
        components = [
            "short_term_borrowings", "long_term_borrowings",
            "bonds_payable", "lease_liabilities",
        ]
        now = datetime.now().isoformat()
        derived: list[dict] = []

        # 按财年分组，每个财年汇总一次
        for year in facts_df["fiscal_year"].unique():
            year_df = facts_df[facts_df["fiscal_year"] == year]
            total = 0.0
            input_ids: list[str] = []
            for comp in components:
                comp_df = year_df[year_df["concept_id"] == comp]
                if not comp_df.empty:
                    total += comp_df.iloc[0]["value"]
                    input_ids.append(comp_df.iloc[0]["fact_id"])

            if input_ids:
                derived.append(_make_single_q_fact_dict(
                    "interest_bearing_debt", year, 0, "FY",
                    total, now, input_ids,
                    derivation_id="interest_bearing_debt",
                    symbol=str(year_df.iloc[0]["symbol"]),
                    period_end=str(year_df.iloc[0].get("period_end", "")),
                ))

        return derived

    @staticmethod
    def derive_all(
        facts_df: pd.DataFrame,
        concept_ids_for_single_q: list[str] | None = None,
    ) -> list[dict]:
        """运行所有适用派生。

        Args:
            facts_df: 含所有必要列的已报告事实 DataFrame
            concept_ids_for_single_q: 需要还原单季度的概念列表。
                None 时使用默认列表。

        Returns:
            所有派生事实的 dict 列表
        """
        if concept_ids_for_single_q is None:
            from ashare_research.derivations.definitions import (
                DerivationRegistry,
            )
            concept_ids_for_single_q = (
                DerivationRegistry.SINGLE_QUARTER_DERIVABLE
            )

        all_derived: list[dict] = []

        for cid in concept_ids_for_single_q:
            sq = DerivationEngine.derive_single_quarter(facts_df, cid)
            all_derived.extend(sq)

        fcf = DerivationEngine.derive_free_cash_flow(facts_df)
        all_derived.extend(fcf)

        debt = DerivationEngine.derive_interest_bearing_debt(facts_df)
        all_derived.extend(debt)

        return all_derived


def _make_single_q_fact(
    row, concept_id: str, quarter: int,
    period_type: str, now: str,
) -> dict:
    """从 DataFrame row 构建单季度派生事实 dict（Q1 直接使用）。

    fact_id 由 canonical build_fact_id 计算，因此派生事实的身份
    与已报告事实遵循同一套契约。
    """
    derivation_id = f"single_quarter_{concept_id}"
    fact: dict = {
        "concept_id": concept_id,
        "concept_version": str(row.get("concept_version", "1") or "1"),
        "symbol": row["symbol"],
        "value": row["value"],
        "unit": row.get("unit", "CNY"),
        "context_id": f"{row['symbol']}|{row['fiscal_year']}"
                       f"|single_quarter_q{quarter}|consolidated|original",
        "is_derived": True,
        "derived_from": row.get("fact_id", ""),
        "derivation_definition_id": derivation_id,
        "derivation_version": "1",
        "input_fact_ids": row.get("fact_id", ""),
        "fact_version": 1,
        "restatement_version": "original",
        "source_id": f"derived::{derivation_id}",
        "fiscal_year": row["fiscal_year"],
        "report_type": f"single_q{quarter}",
        "period_end": row.get("period_end", ""),
        "source_provider": row.get("source_provider", ""),
        "filing_date": row.get("filing_date", ""),
        "announcement_date": row.get("announcement_date", ""),
        "available_at": row.get("available_at", ""),
        "verification_status": "derived",
        "created_at": now,
    }
    fact["fact_id"] = build_fact_id(fact)
    return fact


def _make_single_q_fact_dict(
    concept_id: str, year: int, quarter: int,
    period_type: str, value: float, now: str,
    input_fact_ids: list[str],
    derivation_id: str = "",
    *,
    symbol: str,
    period_end: str = "",
) -> dict:
    """构建单季度/派生事实 dict（Q2/Q3/Q4 差值计算）。

    ``symbol`` 为必填关键字参数（修复此前硬编码 601857.SH 的缺陷），
    ``period_end`` 继承自源事实的报告期，fact_id 由 canonical
    build_fact_id 计算。
    """
    if not derivation_id:
        derivation_id = f"single_quarter_{concept_id}"
    sq_label = f"single_q{quarter}" if quarter > 0 else period_type
    fact: dict = {
        "concept_id": concept_id,
        "concept_version": "1",
        "symbol": symbol,
        "value": value,
        "unit": "CNY",
        "context_id": f"{symbol}|{year}|single_quarter_q{quarter}"
                       f"|consolidated|original",
        "is_derived": True,
        "derived_from": ",".join(input_fact_ids),
        "derivation_definition_id": derivation_id,
        "derivation_version": "1",
        "input_fact_ids": ",".join(input_fact_ids),
        "fact_version": 1,
        "restatement_version": "original",
        "source_id": f"derived::{derivation_id}",
        "fiscal_year": year,
        "report_type": sq_label,
        "period_end": period_end,
        "source_provider": "ashare-research",
        "filing_date": "",
        "announcement_date": "",
        "available_at": "",
        "verification_status": "derived",
        "created_at": now,
    }
    fact["fact_id"] = build_fact_id(fact)
    return fact
