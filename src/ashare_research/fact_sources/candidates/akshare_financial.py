"""M2 Stage 1B — AKShare 金融数据候选来源提供方。

⚠ AKShare 是候选聚合来源（candidate_aggregator），不是官方披露。
   所有事实标记为 unverified，eligible_for_metrics=false。
   不得将候选数据冒充官方数据用于评分或估值。
"""

from __future__ import annotations

import logging
from datetime import datetime

import akshare as ak
import pandas as pd

from ashare_research.exceptions import EmptyResultError
from ashare_research.fact_sources.base import FactSourceProvider, SourceTier
from ashare_research.facts.identity import build_fact_id
from ashare_research.facts.mappings import ConceptMapping

logger = logging.getLogger(__name__)

_REPORT_TYPE_MAP: dict[str, str] = {
    "年报": "FY",
    "一季报": "Q1",
    "中报": "H1",
    "三季报": "Q3",
}


class AKShareFinancialCandidateProvider(FactSourceProvider):
    """AKShare 聚合财务数据 — 候选来源。

    数据来自 AKShare 第三方聚合接口。
    所有事实的 verification_status = "unverified"。
    eligible_for_metrics = false。
    source_tier = candidate_aggregator。

    官方核验完成后才能升级为 verified。
    """

    provider_name = "akshare_financial_candidate"
    source_tier = SourceTier.candidate_aggregator

    def __init__(self, raw_dir: str = ""):
        super().__init__(raw_dir=raw_dir)
        self.mapping = ConceptMapping()

    def get_financial_statements(
        self, symbol: str, start_year: int, end_year: int
    ) -> pd.DataFrame:
        all_facts: list[dict] = []

        for year in range(start_year, end_year + 1):
            for report_type in ["年报", "一季报", "中报", "三季报"]:
                try:
                    facts = self._fetch_report_facts(
                        symbol, year, report_type,
                    )
                    all_facts.extend(facts)
                except Exception as e:
                    logger.warning(
                        f"Failed {report_type} {year}: {e}"
                    )

        if not all_facts:
            raise EmptyResultError(
                f"No facts for {symbol} ({start_year}-{end_year})"
            )
        return pd.DataFrame(all_facts)

    def _fetch_report_facts(
        self, symbol: str, year: int, report_type: str,
    ) -> list[dict]:
        fact_type = _REPORT_TYPE_MAP.get(report_type, "FY")
        period_end = _period_end_date(year, report_type)
        now = datetime.now().isoformat()
        source_id = f"akshare::{symbol}::{year}::{fact_type}"
        facts: list[dict] = []

        for api_name, report_label in [
            ("stock_financial_profit_by_report_em", "profit"),
            ("stock_financial_balance_sheet_by_report_em",
             "balance_sheet"),
            ("stock_financial_cash_flow_by_report_em", "cash_flow"),
        ]:
            try:
                api_method = getattr(ak, api_name)
                df = api_method(symbol=symbol)
                if df is None or df.empty:
                    continue

                suffix = _report_period_suffix(report_type)
                row = df[df["报告期"] == f"{year}{suffix}"]
                if row.empty:
                    continue

                fields = self.mapping.get_fields_for_report_type(
                    report_label,
                )
                row_data = row.iloc[0]

                for raw_field, (concept_id, factor) in fields.items():
                    if raw_field not in row_data.index:
                        continue
                    raw_val = row_data[raw_field]
                    if pd.isna(raw_val):
                        continue

                    norm_val = float(raw_val) * factor

                    fact = {
                        "concept_id": concept_id,
                        "concept_version": "1",
                        "symbol": symbol,
                        "value": norm_val,
                        "unit": "CNY",
                        "context_id": (
                            f"{symbol}|{year}|{fact_type}"
                            f"|consolidated|original"
                        ),
                        "is_derived": False,
                        "source_provider": self.provider_name,
                        "source_id": source_id,
                        "source_tier": self.source_tier.value,
                        "source_document": f"AKShare {year} {report_type}",
                        "source_url": "",
                        "source_hash": "",
                        "fact_version": 1,
                        "fiscal_year": year,
                        "report_type": fact_type,
                        "period_end": period_end,
                        "filing_date": "",
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
                            "AKShare candidate aggregator; "
                            "requires official report confirmation"
                        ),
                        "eligible_for_metrics": False,
                        "created_at": now,
                        "restatement_version": "original",
                        "supersedes_fact_id": "",
                    }
                    fact["fact_id"] = build_fact_id(fact)
                    facts.append(fact)
            except Exception as e:
                logger.warning(f"API {api_name} failed: {e}")

        return facts

    def get_dividends(
        self, symbol: str, start_year: int, end_year: int
    ) -> pd.DataFrame:
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
                        source_id = f"akshare::dividend::{symbol}::{year}"
                        fact = {
                            "concept_id": "cash_dividend_per_share",
                            "concept_version": "1",
                            "symbol": symbol,
                            "value": float(cash_div),
                            "unit": "CNY_PER_SHARE",
                            "fiscal_year": year,
                            "report_type": "FY",
                            "period_end": f"{year}-12-31",
                            "source_provider": self.provider_name,
                            "source_id": source_id,
                            "source_tier": self.source_tier.value,
                            "fact_version": 1,
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
        return pd.DataFrame()

    def get_shareholder_increases(
        self, symbol: str, start_year: int, end_year: int
    ) -> pd.DataFrame:
        return pd.DataFrame()

    def get_audit_opinions(
        self, symbol: str, start_year: int, end_year: int
    ) -> pd.DataFrame:
        return pd.DataFrame()


def _report_period_suffix(report_type: str) -> str:
    return {
        "年报": "1231", "一季报": "0331",
        "中报": "0630", "三季报": "0930",
    }.get(report_type, "1231")


def _period_end_date(year: int, report_type: str) -> str:
    return {
        "年报": f"{year}-12-31", "一季报": f"{year}-03-31",
        "中报": f"{year}-06-30", "三季报": f"{year}-09-30",
    }.get(report_type, f"{year}-12-31")
