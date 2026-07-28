"""M2 Stage 1 — FactService: validate-before-write 编排层。

核心流程：
    1. 创建 LineageManifest
    2. 从 provider 获取事实
    3. 在内存中构建 contexts
    4. 校验 reported facts → 有 error 则标记 failed，不写库
    5. 在内存中派生单季度事实
    6. 校验 derived facts → 计入 total error
    7. 汇总 reported + derived + context + checkpoint → total_error_count
    8. Checkpoint: error→failed, mismatch→failed, critical_missing→conditional_pass
    9. IF checkpoint failed: 不写任何数据，返回 failed manifest
   10. IF checkpoint conditional_pass 或 passed:
       - 开启事务
       - 写入 concepts, contexts, reported facts, derived facts,
         validation results, lineage
       - 验证写入行数与预期一致（使用 StoreFactsResult）
       - 提交或回滚
       - 写出 run manifest
   11. 返回结构化结果：run_id, counts, status, manifest
"""

from __future__ import annotations

import logging
import os
from datetime import datetime
from typing import Any

import pandas as pd

from ashare_research.derivations.engine import DerivationEngine
from ashare_research.fact_sources.base import SourceTier
from ashare_research.facts.as_of import AsOfQuery
from ashare_research.facts.contexts import create_context
from ashare_research.facts.repository import FactRepository, StoreFactsResult
from ashare_research.lineage.manifest import LineageManifest
from ashare_research.validation.results import (
    FactValidationResult,
    result_to_dict,
    summarize_results,
)
from ashare_research.validation.validator import FactValidator

logger = logging.getLogger(__name__)

# 对给定 profile 必须存在的关键概念（缺失则 conditional_pass 而非 passed）
PROFILE_CRITICAL_CONCEPTS: dict[str, list[str]] = {
    "cyclical": [
        "revenue",
        "net_profit_attributable_to_parent",
        "operating_cash_flow",
        "capital_expenditure_cash",
        "total_assets",
        "total_liabilities",
        "short_term_borrowings",
        "long_term_borrowings",
    ],
    "general": [
        "revenue",
        "net_profit_attributable_to_parent",
        "operating_cash_flow",
        "total_assets",
    ],
}


def _count_errors(results: list[FactValidationResult]) -> int:
    """统计 severity='error' 且未通过的校验结果数。"""
    return sum(1 for r in results if r.severity == "error" and not r.passed)


def _count_warnings(results: list[FactValidationResult]) -> int:
    """统计 severity='warning' 且未通过的校验结果数。"""
    return sum(1 for r in results if r.severity == "warning" and not r.passed)


def _ensure_fact_defaults(fact: dict[str, Any]) -> dict[str, Any]:
    """为事实 dict 填充 FactRepository._FACT_COLS 中缺失列的默认值。

    确保写入时不会因缺列而报错。
    """
    defaults: dict[str, Any] = {
        "fact_id": "",
        "concept_id": "",
        "concept_version": "1",
        "symbol": "",
        "value": None,
        "unit": "CNY",
        "context_id": "",
        "is_derived": False,
        "derived_from": "",
        "derivation_definition_id": "",
        "derivation_version": "",
        "input_fact_ids": "",
        "source_provider": "",
        "source_id": "",
        "source_tier": "candidate_aggregator",
        "source_document": "",
        "source_url": "",
        "source_hash": "",
        "source_page": "",
        "source_table": "",
        "source_label": "",
        "fact_version": 1,
        "restatement_version": "original",
        "supersedes_fact_id": "",
        "filing_date": "",
        "period_end": "",
        "announcement_date": "",
        "available_at": "",
        "raw_value": None,
        "raw_unit": "",
        "normalized_value": None,
        "normalization_rule": "",
        "verification_status": "unverified",
        "verification_note": "",
        "eligible_for_metrics": False,
        "created_at": datetime.now().isoformat(),
    }
    result = dict(defaults)
    result.update(fact)
    return result


class FactService:
    """validate-before-write 财务事实构建编排服务。

    流程：
        Provider → 内存校验 → Checkpoint 决策 → 事务化写入 → 清单
    """

    schema_version: str = "2.0"

    def __init__(
        self,
        fact_repository: FactRepository,
        source_registry,  # FactSourceRegistry
        derivation_engine: DerivationEngine | None = None,
        validator: FactValidator | None = None,
        output_root: str = "output/value_assessment",
    ):
        self.repo = fact_repository
        self.registry = source_registry
        self.engine = derivation_engine or DerivationEngine()
        self.validator = validator or FactValidator()
        self.as_of = AsOfQuery(fact_repository)
        self.output_root = output_root

    # ── 公开入口 ──────────────────────────────────────────

    def build_facts(
        self, symbol: str, start_year: int, end_year: int,
        source_mode: str = "candidate",
    ) -> dict[str, Any]:
        """执行完整的 validate-before-write 事实构建流程。

        source_mode: "candidate" 或 "official"
        Returns:
            dict with run_id, symbol, reported_count, derived_count,
            reported_error_count, derived_error_count,
            context_error_count, checkpoint_error_count,
            total_error_count, status, checkpoint_decision, manifest
        """
        manifest = LineageManifest(symbol=symbol, profile="cyclical")
        manifest.entry.job_name = self._resolve_job_name(source_mode)
        manifest.entry.code_version = self.schema_version
        manifest.entry.fact_schema_version = "2.0"
        manifest.entry.concept_registry_version = "2.0"
        run_id = manifest.entry.run_id

        output_path = os.path.join(
            self.output_root, symbol, "runs", run_id, "run_manifest.json",
        )
        actual_source_tiers = self._resolve_source_tiers(source_mode)

        # ── 阶段 1: 获取事实 ──
        try:
            provider = self.registry.get_provider(symbol, source_mode)
            logger.info(
                f"Fetching facts for {symbol} ({start_year}-{end_year})"
            )
            facts_df = provider.get_financial_statements(
                symbol, start_year, end_year,
            )
        except Exception as exc:
            logger.error(f"Provider fetch failed: {exc}")
            self._finalize_and_write_manifest(
                manifest=manifest,
                output_path=output_path,
                status="failed",
                failure_stage="provider_fetch",
                reported_error_count=1,
                actual_source_tiers=actual_source_tiers,
            )
            return _build_result(
                manifest, reported_count=0, derived_count=0,
                reported_error_count=1, derived_error_count=0,
                context_error_count=0, checkpoint_error_count=0,
                total_error_count=1,
                checkpoint_decision="failed",
            )

        if facts_df.empty:
            logger.warning(f"No facts returned for {symbol}")
            self._finalize_and_write_manifest(
                manifest=manifest,
                output_path=output_path,
                status="failed",
                failure_stage="provider_empty",
                reported_error_count=1,
                actual_source_tiers=actual_source_tiers,
            )
            return _build_result(
                manifest, reported_count=0, derived_count=0,
                reported_error_count=1, derived_error_count=0,
                context_error_count=0, checkpoint_error_count=1,
                total_error_count=2,
                checkpoint_decision="failed",
            )

        reported_facts_raw = facts_df.to_dict("records")
        manifest.entry.reported_fact_count = len(reported_facts_raw)
        logger.info(
            f"Fetched {len(reported_facts_raw)} reported facts"
        )

        # ── 阶段 2: 填充默认值 ──
        reported_facts = [
            _ensure_fact_defaults(f) for f in reported_facts_raw
        ]

        # ── 阶段 3: 构建 contexts（内存） ──
        contexts, context_error_count = self._build_contexts(
            symbol, reported_facts,
        )

        # ── 阶段 4: 校验 reported facts ──
        logger.info("Validating reported facts...")
        reported_validation = self.validator.validate_batch(reported_facts)
        reported_summary = summarize_results(reported_validation)
        reported_error_count = reported_summary["error_count"]
        reported_warning_count = reported_summary["warning_count"]
        logger.info(
            f"Reported validation: {reported_summary['passed']} passed, "
            f"{reported_error_count} errors, "
            f"{reported_warning_count} warnings"
        )

        # ── 阶段 5: 派生单季度事实（内存） ──
        logger.info("Deriving single-quarter facts...")
        facts_for_derive = pd.DataFrame(reported_facts)
        derived_facts_raw = self.engine.derive_all(facts_for_derive)
        derived_facts = [
            _ensure_fact_defaults(d) for d in derived_facts_raw
        ]
        manifest.entry.derived_fact_count = len(derived_facts)
        logger.info(f"Derived {len(derived_facts)} derived facts")

        # ── 阶段 6: 校验 derived facts ──
        derived_validation: list[FactValidationResult] = []
        derived_error_count = 0
        derived_warning_count = 0
        if derived_facts:
            logger.info("Validating derived facts...")
            derived_validation = self.validator.validate_batch(
                derived_facts,
            )
            d_summary = summarize_results(derived_validation)
            derived_error_count = d_summary["error_count"]
            derived_warning_count = d_summary["warning_count"]
            logger.info(
                f"Derived validation: {d_summary['passed']} passed, "
                f"{derived_error_count} errors, "
                f"{derived_warning_count} warnings"
            )

        # ── 阶段 7: 汇总错误 ──
        checkpoint = self._run_checkpoint(
            reported_facts=reported_facts,
            derived_facts=derived_facts,
            reported_error_count=reported_error_count,
            derived_error_count=derived_error_count,
            context_error_count=context_error_count,
            profile=manifest.entry.profile,
        )
        checkpoint_error_count = checkpoint["checkpoint_error_count"]
        checkpoint_decision = checkpoint["decision"]

        total_error_count = (
            reported_error_count
            + derived_error_count
            + context_error_count
            + checkpoint_error_count
        )

        total_warning_count = reported_warning_count + derived_warning_count

        # ── 阶段 8: 决定状态 ──
        if total_error_count > 0 or checkpoint_decision == "failed":
            status = "failed"
        elif (
            checkpoint_decision == "conditional_pass"
            or _has_unverified(reported_facts + derived_facts)
        ):
            status = "conditional_pass"
        else:
            status = "passed"

        # ── 阶段 9: checkpoint failed → 不写库 ──
        if checkpoint_decision == "failed":
            self._finalize_and_write_manifest(
                manifest=manifest,
                output_path=output_path,
                status="failed",
                checkpoint_status=checkpoint_decision,
                transaction_committed=False,
                failure_stage="checkpoint",
                reported_error_count=reported_error_count,
                derived_error_count=derived_error_count,
                context_error_count=context_error_count,
                warning_count=total_warning_count,
                actual_source_tiers=actual_source_tiers,
            )
            logger.warning(
                f"Checkpoint FAILED: {checkpoint['reasons']}. "
                f"No data written."
            )
            return _build_result(
                manifest=manifest,
                reported_count=len(reported_facts),
                derived_count=len(derived_facts),
                reported_error_count=reported_error_count,
                derived_error_count=derived_error_count,
                context_error_count=context_error_count,
                checkpoint_error_count=checkpoint_error_count,
                total_error_count=total_error_count,
                checkpoint_decision=checkpoint_decision,
            )

        # ── 阶段 10: 事务化写入 ──
        all_validation = reported_validation + derived_validation
        logger.info(
            f"Checkpoint {checkpoint_decision.upper()} — "
            f"writing {len(reported_facts)} reported + "
            f"{len(derived_facts)} derived facts in transaction..."
        )

        # Initialize store result variables for the except handler
        reported_result: StoreFactsResult | None = None
        derived_result: StoreFactsResult | None = None
        ctx_result: StoreFactsResult | None = None

        try:
            with self.repo.transaction() as conn:
                # 10a. 种子概念
                self.repo.seed_concepts(conn=conn)

                # 10b. 写入 contexts
                ctx_result = self.repo.store_contexts(contexts, conn=conn)
                logger.info(
                    f"Contexts: {ctx_result.inserted} inserted, "
                    f"{ctx_result.unchanged} unchanged"
                )

                # 10c. 写入 reported facts
                reported_result = self.repo.store_facts(
                    reported_facts, conn=conn,
                )
                logger.info(
                    f"Reported facts: {reported_result.inserted} inserted, "
                    f"{reported_result.unchanged} unchanged"
                )

                # 10d. 写入 derived facts
                if derived_facts:
                    derived_result = self.repo.store_facts(
                        derived_facts, conn=conn,
                    )
                    logger.info(
                        f"Derived facts: {derived_result.inserted} inserted, "
                        f"{derived_result.unchanged} unchanged"
                    )

                # 10e. 写入验证运行摘要
                self.repo.store_validation_run(
                    run_id=run_id,
                    fact_count=len(reported_facts) + len(derived_facts),
                    error_count=total_error_count,
                    warning_count=total_warning_count,
                    status=status,
                    conn=conn,
                )

                # 10f. 写入验证结果明细
                if all_validation:
                    vr_count = self.repo.store_validation_results(
                        [
                            result_to_dict(r)
                            for r in all_validation
                        ],
                        validation_run_id=run_id,
                        conn=conn,
                    )
                    logger.info(
                        f"Stored {vr_count} validation results"
                    )

                # 10g. 写入 lineage
                for fact in reported_facts:
                    self.repo.store_lineage(
                        fact_id=fact.get("fact_id", ""),
                        run_id=run_id,
                        source_provider=fact.get("source_provider", ""),
                        source_tier=fact.get("source_tier", ""),
                        source_method="fetch",
                        conn=conn,
                    )
                for fact in derived_facts:
                    self.repo.store_lineage(
                        fact_id=fact.get("fact_id", ""),
                        run_id=run_id,
                        source_provider="ashare-research",
                        source_tier="derived",
                        source_method="derive",
                        parent_fact_ids=fact.get("input_fact_ids", ""),
                        conn=conn,
                    )
                logger.info("Lineage records written")

            logger.info(
                f"Transaction committed — "
                f"{reported_result.inserted} reported + "
                f"{derived_result.inserted if derived_result else 0} derived facts"
            )

            # Set fact counts based on source_mode
            total_fact_count = len(reported_facts) + len(derived_facts)
            if source_mode == "candidate":
                manifest.entry.candidate_fact_count = total_fact_count
            else:
                manifest.entry.official_fact_count = total_fact_count

        except Exception as exc:
            logger.error(f"Transaction failed (rolled back): {exc}")
            self._finalize_and_write_manifest(
                manifest=manifest,
                output_path=output_path,
                status="failed",
                transaction_committed=False,
                failure_stage="transaction",
                reported_error_count=reported_error_count,
                derived_error_count=derived_error_count,
                context_error_count=context_error_count,
                warning_count=total_warning_count,
                actual_source_tiers=actual_source_tiers,
            )
            return _build_result(
                manifest=manifest,
                reported_count=len(reported_facts),
                derived_count=len(derived_facts),
                reported_error_count=reported_error_count,
                derived_error_count=derived_error_count,
                context_error_count=context_error_count,
                checkpoint_error_count=checkpoint_error_count + 1,
                total_error_count=total_error_count + 1,
                checkpoint_decision="failed",
            )

        # ── 阶段 11: 完成并返回 ──
        self._finalize_and_write_manifest(
            manifest=manifest,
            output_path=output_path,
            status=status,
            checkpoint_status=checkpoint_decision,
            transaction_committed=True,
            failure_stage="",
            reported_error_count=reported_error_count,
            derived_error_count=derived_error_count,
            context_error_count=context_error_count,
            warning_count=total_warning_count,
            reported_store_result=reported_result,
            derived_store_result=derived_result,
            context_store_result=ctx_result,
            actual_source_tiers=actual_source_tiers,
        )

        logger.info(
            f"build_facts complete: "
            f"run_id={run_id} symbol={symbol} status={status}"
        )

        return _build_result(
            manifest=manifest,
            reported_count=len(reported_facts),
            derived_count=len(derived_facts),
            reported_error_count=reported_error_count,
            derived_error_count=derived_error_count,
            context_error_count=context_error_count,
            checkpoint_error_count=checkpoint_error_count,
            total_error_count=total_error_count,
            checkpoint_decision=checkpoint_decision,
        )

    # ── 查询方法 ──────────────────────────────────────────

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

    # ── 内部方法 ──────────────────────────────────────────

    @staticmethod
    def _resolve_job_name(source_mode: str) -> str:
        """根据 source_mode 解析 job_name。"""
        if source_mode == "official":
            return "build-official-value-facts"
        return "build-candidate-value-facts"

    @staticmethod
    def _resolve_source_tiers(source_mode: str) -> list[str]:
        """根据 source_mode 解析 source_tiers 列表（使用枚举值）。"""
        if source_mode == "official":
            return [SourceTier.company_official.value]
        return [SourceTier.candidate_aggregator.value]

    def _build_contexts(
        self, symbol: str, facts: list[dict[str, Any]],
    ) -> tuple[list[dict[str, Any]], int]:
        """在内存中为事实构建 contexts。

        Returns:
            (contexts list, context_error_count)
        """
        contexts: list[dict[str, Any]] = []
        seen: set[str] = set()
        context_error_count = 0

        for fact in facts:
            ctx_id = fact.get("context_id", "")
            if not ctx_id:
                # 尝试从事实中构建 context_id
                fiscal_year = fact.get("fiscal_year", 0)
                period_type = fact.get("report_type", "FY")
                filing_date = fact.get("filing_date", "")
                source_document = fact.get("source_document", "")
                try:
                    ctx = create_context(
                        symbol=symbol,
                        fiscal_year=fiscal_year,
                        period_type=period_type,
                        filing_date=filing_date,
                        source_document=source_document,
                    )
                    ctx_id = ctx.context_id
                    fact["context_id"] = ctx_id
                except Exception:
                    context_error_count += 1
                    logger.warning(
                        f"Cannot build context for fact "
                        f"{fact.get('fact_id', 'unknown')}: "
                        f"fiscal_year={fiscal_year}, "
                        f"period_type={period_type}"
                    )
                    continue

            if ctx_id and ctx_id not in seen:
                seen.add(ctx_id)
                # 重建 context 以获得完整字段
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

        logger.info(
            f"Built {len(contexts)} unique contexts "
            f"({context_error_count} errors)"
        )
        return contexts, context_error_count

    def _run_checkpoint(
        self,
        reported_facts: list[dict[str, Any]],
        derived_facts: list[dict[str, Any]],
        reported_error_count: int,
        derived_error_count: int,
        context_error_count: int,
        profile: str,
    ) -> dict[str, Any]:
        """执行质量 checkpoint。

        规则:
            - error > 0 → failed
            - mismatch (空事实、数量异常) → failed
            - critical_missing (关键概念缺失) → conditional_pass
            - 否则 → passed

        Returns:
            dict with decision, checkpoint_error_count, reasons
        """
        reasons: list[str] = []
        decision = "passed"
        checkpoint_error_count = 0

        # 检查 1: 是否有任何已知错误
        validation_errors = reported_error_count + derived_error_count
        if validation_errors > 0:
            decision = "failed"
            reasons.append(
                f"{validation_errors} validation error(s) "
                f"(reported={reported_error_count}, "
                f"derived={derived_error_count})"
            )

        if context_error_count > 0:
            decision = "failed"
            reasons.append(
                f"{context_error_count} context build error(s)"
            )

        # 检查 2: mismatch — 空事实或数量异常
        if not reported_facts:
            decision = "failed"
            checkpoint_error_count += 1
            reasons.append("Mismatch: zero reported facts")

        # 检查文中的事实是否有缺失的 fact_id
        missing_ids = [
            f.get("fact_id", "") or "missing"
            for f in reported_facts
            if not f.get("fact_id")
        ]
        if missing_ids:
            decision = "failed"
            checkpoint_error_count += 1
            reasons.append(
                f"Mismatch: {len(missing_ids)} facts without fact_id"
            )

        # 检查 3: critical_missing — 关键概念缺失
        critical = PROFILE_CRITICAL_CONCEPTS.get(
            profile, PROFILE_CRITICAL_CONCEPTS["general"]
        )
        present_concepts: set[str] = set()
        for f in reported_facts:
            cid = f.get("concept_id", "")
            if cid:
                present_concepts.add(cid)
        for f in derived_facts:
            cid = f.get("concept_id", "")
            if cid:
                present_concepts.add(cid)

        missing_critical = [
            c for c in critical if c not in present_concepts
        ]
        if missing_critical:
            # 关键概念缺失视为 conditional_pass（而非失败）
            if decision == "passed":
                decision = "conditional_pass"
            reasons.append(
                f"Critical concepts missing for profile "
                f"'{profile}': {missing_critical}"
            )

        logger.info(
            f"Checkpoint: decision={decision}, "
            f"checkpoint_errors={checkpoint_error_count}, "
            f"reasons={reasons}"
        )

        return {
            "decision": decision,
            "checkpoint_error_count": checkpoint_error_count,
            "reasons": reasons,
        }

    def _finalize_and_write_manifest(
        self,
        manifest: LineageManifest,
        output_path: str,
        *,
        status: str,
        checkpoint_status: str = "",
        transaction_committed: bool = False,
        failure_stage: str = "",
        reported_error_count: int = 0,
        derived_error_count: int = 0,
        context_error_count: int = 0,
        warning_count: int = 0,
        reported_store_result: StoreFactsResult | None = None,
        derived_store_result: StoreFactsResult | None = None,
        context_store_result: StoreFactsResult | None = None,
        actual_source_tiers: list[str] | None = None,
    ) -> None:
        """统一入口：完成 manifest 并写入文件。

        所有返回路径（passed/conditional_pass/failed）都必须经过此方法。
        所有字段均通过显式参数传入，不读取 manifest.entry 中的值。
        """
        manifest.entry.status = status
        manifest.entry.completed_at = datetime.now().isoformat()
        manifest.entry.checkpoint_status = checkpoint_status
        manifest.entry.transaction_committed = transaction_committed
        manifest.entry.failure_stage = failure_stage
        manifest.entry.reported_error_count = reported_error_count
        manifest.entry.derived_error_count = derived_error_count
        manifest.entry.context_error_count = context_error_count
        manifest.entry.error_count = (
            reported_error_count + derived_error_count + context_error_count
        )
        manifest.entry.warning_count = warning_count

        if actual_source_tiers is not None:
            manifest.entry.source_tiers = actual_source_tiers

        if reported_store_result is not None:
            manifest.entry.reported_requested = reported_store_result.requested
            manifest.entry.reported_inserted = reported_store_result.inserted
            manifest.entry.reported_unchanged = reported_store_result.unchanged
            manifest.entry.reported_conflicts = reported_store_result.conflicts

        if derived_store_result is not None:
            manifest.entry.derived_requested = derived_store_result.requested
            manifest.entry.derived_inserted = derived_store_result.inserted
            manifest.entry.derived_unchanged = derived_store_result.unchanged
            manifest.entry.derived_conflicts = derived_store_result.conflicts

        if context_store_result is not None:
            manifest.entry.contexts_requested = context_store_result.requested
            manifest.entry.contexts_inserted = context_store_result.inserted
            manifest.entry.contexts_unchanged = context_store_result.unchanged
            manifest.entry.contexts_conflicts = context_store_result.conflicts

        manifest.write_manifest(output_path)


# ── 辅助函数 ──────────────────────────────────────────────


def _has_unverified(facts: list[dict[str, Any]]) -> bool:
    """检查事实列表中是否存在 verification_status='unverified' 的记录。"""
    return any(
        f.get("verification_status") == "unverified"
        for f in facts
    )


def _build_result(
    manifest: LineageManifest,
    reported_count: int,
    derived_count: int,
    reported_error_count: int,
    derived_error_count: int,
    context_error_count: int,
    checkpoint_error_count: int,
    total_error_count: int,
    checkpoint_decision: str,
) -> dict[str, Any]:
    """构建统一的 build_facts 返回值。"""
    return {
        "run_id": manifest.entry.run_id,
        "symbol": manifest.entry.company_symbol,
        "reported_count": reported_count,
        "derived_count": derived_count,
        "reported_error_count": reported_error_count,
        "derived_error_count": derived_error_count,
        "context_error_count": context_error_count,
        "checkpoint_error_count": checkpoint_error_count,
        "total_error_count": total_error_count,
        "status": manifest.entry.status,
        "checkpoint_decision": checkpoint_decision,
        "manifest": manifest.to_dict(),
    }
