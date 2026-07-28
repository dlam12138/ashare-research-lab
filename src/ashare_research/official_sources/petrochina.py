"""M2 Stage 1 — 中国石油 601857.SH 官方数据提供方。"""

from __future__ import annotations

import logging
from datetime import datetime

import akshare as ak
import pandas as pd

from ashare_research.exceptions import EmptyResultError
from ashare_research.facts.contexts import build_context_id
from ashare_research.facts.identity import build_fact_id
from ashare_research.facts.mappings import ConceptMapping
from ashare_research.official_sources.base import OfficialSourceProvider

logger = logging.getLogger(__name__)

# AKShare 报表类型映射
_REPORT_TYPE_MAP: dict[str, str] = {
    "年报": "FY",
    "一季报": "Q1",
    "中报": "H1",
    "三季报": "Q3",
}


class PetroChinaProvider(OfficialSourceProvider):
    """中国石油 601857.SH 官方财务数据提供方。

    当前阶段通过 AKShare 财务接口获取数据。
    """

    provider_name = "petrochina"

    def __init__(self, raw_dir: str = ""):
        super().__init__(raw_dir=raw_dir)
        self.mapping = ConceptMapping()

    def get_financial_statements(
        self, symbol: str, start_year: int, end_year: int
    ) -> pd.DataFrame:
        """获取三大报表，合并为统一事实流。"""
        all_facts: list[dict] = []

        for year in range(start_year, end_year + 1):
            for report_type in ["年报", "一季报", "中报", "三季报"]:
                try:
                    facts = self._fetch_report_facts(symbol, year, report_type)
                    all_facts.extend(facts)
                except Exception as e:
                    logger.warning(
                        f"Failed to fetch {report_type} {year} for {symbol}: {e}"
                    )

        if not all_facts:
            raise EmptyResultError(
                f"No financial facts for {symbol} ({start_year}-{end_year})"
            )

        return pd.DataFrame(all_facts)

    def _fetch_report_facts(
        self, symbol: str, year: int, report_type: str,
    ) -> list[dict]:
        """获取单个报表期的所有事实。"""
        fact_type = _REPORT_TYPE_MAP.get(report_type, "FY")
        period_end = _period_end_date(year, report_type)
        now = datetime.now().isoformat()

        facts: list[dict] = []

        for api_name, report_label in [
            ("stock_financial_profit_by_report_em", "profit"),
            ("stock_financial_balance_sheet_by_report_em", "balance_sheet"),
            ("stock_financial_cash_flow_by_report_em", "cash_flow"),
        ]:
            try:
                api_method = getattr(ak, api_name)
                df = api_method(symbol=symbol)
                if df is None or df.empty:
                    continue

                # 找到对应行
                row = df[df["报告期"] == f"{year}{_report_period_suffix(report_type)}"]
                if row.empty:
                    continue

                fields = self.mapping.get_fields_for_report_type(report_label)
                row_data = row.iloc[0]

                for raw_field, (concept_id, factor) in fields.items():
                    if raw_field not in row_data.index:
                        continue

                    raw_val = row_data[raw_field]
                    if pd.isna(raw_val):
                        continue

                    norm_val = float(raw_val) * factor
                    source_id = (
                        f"petrochina_official::{symbol}::{year}"
                        f"::{fact_type}::{concept_id}"
                    )
                    fact = {
                        "concept_id": concept_id,
                        "concept_version": "1",
                        "symbol": symbol,
                        "value": norm_val,
                        "unit": "CNY",
                        "context_id": build_context_id(
                            symbol, year, fact_type,
                        ),
                        "is_derived": False,
                        "source_provider": self.provider_name,
                        "source_id": source_id,
                        "source_tier": "company_official",
                        "source_document": (
                            f"{year} {report_type}"
                        ),
                        "source_url": "",
                        "source_hash": "",
                        "source_page": "",
                        "source_table": "",
                        "source_label": "",
                        "fact_version": 1,
                        "restatement_version": "original",
                        "supersedes_fact_id": "",
                        "fiscal_year": year,
                        "report_type": fact_type,
                        "period_end": period_end,
                        "filing_date": "",   # AKShare 不提供公告日期
                        "announcement_date": "",
                        "available_at": "",
                        "raw_value": float(raw_val),
                        "raw_unit": "CNY",
                        "normalized_value": norm_val,
                        "normalization_rule": (
                            "identity" if factor == 1.0
                            else f"multiply_by_{factor}"
                        ),
                        "verification_status": "unverified",
                        "verification_note": (
                            "AKShare aggregated; "
                            "requires official report confirmation"
                        ),
                        "eligible_for_metrics": False,
                        "created_at": now,
                    }
                    fact["fact_id"] = build_fact_id(fact)
                    facts.append(fact)
            except Exception as e:
                logger.warning(
                    f"API {api_name} failed for {symbol} {year} "
                    f"{report_type}: {e}"
                )

        return facts

    def get_dividends(
        self, symbol: str, start_year: int, end_year: int
    ) -> pd.DataFrame:
        """获取分红记录。"""
        now = datetime.now().isoformat()
        raw_code = symbol.split(".")[0]

        try:
            df = ak.stock_dividents_detail_em(symbol=raw_code)
            if df is None or df.empty:
                return pd.DataFrame()

            facts: list[dict] = []
            for _, row in df.iterrows():
                try:
                    ex_date = str(row.get("除权除息日", ""))
                    year = int(ex_date[:4]) if ex_date else 0
                    if year < start_year or year > end_year:
                        continue

                    cash_div = row.get("每股派息", 0)
                    if pd.notna(cash_div):
                        source_id = (
                            f"petrochina_official_div::{symbol}"
                            f"::{year}::cash_dividend_per_share"
                        )
                        fact = {
                            "concept_id": "cash_dividend_per_share",
                            "concept_version": "1",
                            "symbol": symbol,
                            "value": float(cash_div),
                            "unit": "CNY_PER_SHARE",
                            "context_id": build_context_id(
                                symbol, year, "FY",
                            ),
                            "is_derived": False,
                            "source_provider": self.provider_name,
                            "source_id": source_id,
                            "source_tier": "company_official",
                            "source_document": f"{year} cash dividend",
                            "fact_version": 1,
                            "restatement_version": "original",
                            "supersedes_fact_id": "",
                            "fiscal_year": year,
                            "report_type": "FY",
                            "period_end": f"{year}-12-31",
                            "filing_date": ex_date,
                            "announcement_date": ex_date,
                            "available_at": ex_date,
                            "raw_value": float(cash_div),
                            "raw_unit": "CNY_PER_SHARE",
                            "normalized_value": float(cash_div),
                            "normalization_rule": "identity",
                            "verification_status": "unverified",
                            "eligible_for_metrics": False,
                            "created_at": now,
                        }
                        fact["fact_id"] = build_fact_id(fact)
                        facts.append(fact)
                except Exception:
                    continue

            return pd.DataFrame(facts)
        except Exception as e:
            logger.warning(f"Dividend fetch failed: {e}")
            return pd.DataFrame()

    def get_buybacks(
        self, symbol: str, start_year: int, end_year: int
    ) -> pd.DataFrame:
        """回购记录（Phase 1 占位）。"""
        return pd.DataFrame()

    def get_shareholder_increases(
        self, symbol: str, start_year: int, end_year: int
    ) -> pd.DataFrame:
        """大股东增持记录（Phase 1 占位）。"""
        return pd.DataFrame()

    def get_audit_opinions(
        self, symbol: str, start_year: int, end_year: int
    ) -> pd.DataFrame:
        """审计意见（Phase 1 占位）。"""
        return pd.DataFrame()


def _report_period_suffix(report_type: str) -> str:
    """AKShare 报告期后缀。"""
    return {
        "年报": "1231",
        "一季报": "0331",
        "中报": "0630",
        "三季报": "0930",
    }.get(report_type, "1231")


def _period_end_date(year: int, report_type: str) -> str:
    """计算报告期截止日。"""
    return {
        "年报": f"{year}-12-31",
        "一季报": f"{year}-03-31",
        "中报": f"{year}-06-30",
        "三季报": f"{year}-09-30",
    }.get(report_type, f"{year}-12-31")
