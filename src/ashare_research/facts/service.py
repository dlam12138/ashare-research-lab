"""M2 Stage 1 — FactService: 事实构建编排层。"""

from __future__ import annotations

import logging

import pandas as pd

from ashare_research.derivations.engine import DerivationEngine
from ashare_research.exceptions import AshareDataError
from ashare_research.facts.as_of import AsOfQuery
from ashare_research.facts.contexts import create_context
from ashare_research.facts.repository import FactRepository
from ashare_research.lineage.manifest import LineageManifest
from ashare_research.validation.validator import FactValidator

logger = logging.getLogger(__name__)


class FactService:
    """财务事实构建编排服务。

    流程：
        Provider → 批量事实构建 → 存储 → 校验 → 派生 → 血缘 → 报告
    """

    schema_version: str = "1.0"

    def __init__(
        self,
        fact_repository: FactRepository,
        source_registry,  # OfficialSourceRegistry
        derivation_engine: DerivationEngine | None = None,
        validator: FactValidator | None = None,
    ):
        self.repo = fact_repository
        self.registry = source_registry
        self.engine = derivation_engine or DerivationEngine()
        self.validator = validator or FactValidator()
        self.as_of = AsOfQuery(fact_repository)

    def build_facts(
        self, symbol: str, start_year: int, end_year: int,
    ) -> dict:
        """执行完整的事实构建流程。

        Returns:
            dict with run_id, reported_count, derived_count, status, etc.
        """
        manifest = LineageManifest(symbol=symbol, profile="cyclical")
        manifest.entry.job_name = "build-official-value-facts"
        manifest.entry.code_version = self.schema_version

        try:
            provider = self.registry.get_provider(symbol)

            # 1. 获取财务事实
            logger.info(f"Fetching facts for {symbol} ({start_year}-{end_year})")
            facts_df = provider.get_financial_statements(
                symbol, start_year, end_year,
            )
            if facts_df.empty:
                raise AshareDataError(
                    f"No facts returned for {symbol}"
                )

            reported_facts = facts_df.to_dict("records")
            manifest.entry.reported_fact_count = len(reported_facts)
            logger.info(f"Fetched {len(reported_facts)} reported facts")

            # 2. 存储事实
            stored = self.repo.store_facts(reported_facts)
            logger.info(f"Stored {stored} facts")

            # 3. 构建并存储 contexts
            contexts: list[dict] = []
            seen = set()
            for fact in reported_facts:
                ctx_id = fact.get("context_id", "")
                if ctx_id and ctx_id not in seen:
                    seen.add(ctx_id)
                    ctx = create_context(
                        symbol=symbol,
                        fiscal_year=fact.get("fiscal_year", 0),
                        period_type=fact.get("report_type", "FY"),
                        filing_date=fact.get("filing_date", ""),
                        source_document=fact.get("source_document", ""),
                    )
                    contexts.append({
                        "context_id": ctx.context_id,
                        "symbol": ctx.symbol,
                        "fiscal_year": ctx.fiscal_year,
                        "period_type": ctx.period_type.value,
                        "period_start": ctx.period_start,
                        "period_end": ctx.period_end,
                        "instant_or_duration": (
                            ctx.instant_or_duration.value
                        ),
                        "consolidation_scope": ctx.consolidation_scope.value,
                        "accounting_standard": ctx.accounting_standard,
                        "restatement_version": ctx.restatement_version,
                        "source_document": ctx.source_document,
                        "filing_date": ctx.filing_date,
                        "created_at": ctx.created_at,
                    })
            self.repo.store_contexts(contexts)

            # 4. 校验
            validation_results = self.validator.validate_batch(reported_facts)
            from ashare_research.validation.results import summarize_results
            summary = summarize_results(validation_results)
            logger.info(
                f"Validation: {summary['passed']} passed, "
                f"{summary['failed']} failed"
            )

            # 5. 派生单季度事实
            facts_for_derive = pd.DataFrame(reported_facts)
            derived = self.engine.derive_all(facts_for_derive)
            if derived:
                self.repo.store_facts(derived)
                manifest.entry.derived_fact_count = len(derived)
                logger.info(f"Derived {len(derived)} derived facts")

            # 6. 校验派生事实
            if derived:
                dv_results = self.validator.validate_batch(derived)
                d_summary = summarize_results(dv_results)
                error_count = d_summary["error_count"]

            # 7. 完成 manifest
            manifest.complete_manifest(
                status=(
                    "passed" if summary["error_count"] == 0
                    else "conditional_pass"
                ),
                error_count=summary["error_count"],
                warning_count=summary["warning_count"],
            )

            return {
                "run_id": manifest.entry.run_id,
                "symbol": symbol,
                "reported_count": len(reported_facts),
                "derived_count": len(derived),
                "validation_passed": summary["passed"],
                "validation_failed": summary["failed"],
                "status": manifest.entry.status,
                "manifest": manifest.to_dict(),
            }

        except Exception:
            manifest.complete_manifest(
                status="failed", error_count=1,
            )
            raise

    def get_fact_summary(self, symbol: str) -> dict:
        """获取事实摘要。"""
        return self.repo.get_fact_summary(symbol)

    def query_as_of(
        self, symbol: str, concept_ids: list[str] | None,
        as_of_date: str,
    ) -> pd.DataFrame:
        """PIT 查询。"""
        return self.as_of.query(
            symbol=symbol, concept_ids=concept_ids,
            as_of_date=as_of_date,
        )
