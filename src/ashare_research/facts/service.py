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
       - 验证写入行数与预期一致
       - 提交或回滚
       - 写出 run manifest
   11. 返回结构化结果：run_id, counts, status, manifest
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

import pandas as pd

from ashare_research.derivations.engine import DerivationEngine
from ashare_research.exceptions import FactCheckpointError
from ashare_research.facts.as_of import AsOfQuery
from ashare_research.facts.contexts import create_context
from ashare_research.facts.repository import FactRepository
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

    # ── 公开入口 ──────────────────────────────────────────

    def build_facts(
        self, symbol: str, start_year: int, end_year: int,
    ) -> dict[str, Any]:
        """执行完整的 validate-before-write 事实构建流程。

        Returns:
            dict with run_id, symbol, reported_count, derived_count,
            reported_error_count, derived_error_count,
            context_error_count, checkpoint_error_count,
            total_error_count, status, checkpoint_decision, manifest
        """
        manifest = LineageManifest(symbol=symbol, profile="cyclical")
        manifest.entry.job_name = "build-official-value-facts"
        manifest.entry.code_version = self.schema_version
        run_id = manifest.entry.run_id

        # ── 阶段 1: 获取事实 ──
        try:
            provider = self.registry.get_provider(symbol)
            logger.info(
                f"Fetching facts for {symbol} ({start_year}-{end_year})"
            )
            facts_df = provider.get_financial_statements(
                symbol, start_year, end_year,
            )
        except Exception as exc:
            manifest.complete_manifest(status="failed", error_count=1)
            logger.error(f"Provider fetch failed: {exc}")
            return _build_result(
                manifest, reported_count=0, derived_count=0,
                reported_error_count=1, derived_error_count=0,
                context_error_count=0, checkpoint_error_count=0,
                total_error_count=1,
                checkpoint_decision="failed",
            )

        if facts_df.empty:
            manifest.complete_manifest(status="failed", error_count=1)
            logger.warning(f"No facts returned for {symbol}")
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
            manifest.complete_manifest(
                status="failed",
                error_count=total_error_count,
                warning_count=total_warning_count,
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

        try:
            with self.repo.transaction() as conn:
                # 10a. 种子概念
                self.repo.seed_concepts(conn=conn)

                # 10b. 写入 contexts
                stored_ctx = self.repo.store_contexts(contexts, conn=conn)
                logger.info(f"Stored {stored_ctx} contexts")

                # 10c. 写入 reported facts
                stored_reported = self.repo.store_facts(
                    reported_facts, conn=conn,
                )
                logger.info(f"Stored {stored_reported} reported facts")

                # 10d. 写入 derived facts
                stored_derived = 0
                if derived_facts:
                    stored_derived = self.repo.store_facts(
                        derived_facts, conn=conn,
                    )
                    logger.info(
                        f"Stored {stored_derived} derived facts"
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

                # 10h. 验证写入行数与预期一致
                self._verify_counts(
                    conn=conn,
                    symbol=symbol,
                    expected_reported=len(reported_facts),
                    expected_derived=len(derived_facts),
                )

            logger.info(
                f"Transaction committed — "
                f"{stored_reported} reported + "
                f"{stored_derived} derived facts"
            )

        except Exception as exc:
            manifest.complete_manifest(
                status="failed",
                error_count=total_error_count + 1,
                warning_count=total_warning_count,
            )
            logger.error(
                f"Transaction failed (rolled back): {exc}"
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
        manifest.complete_manifest(
            status=status,
            error_count=total_error_count,
            warning_count=total_warning_count,
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

    @staticmethod
    def _verify_counts(
        conn,
        symbol: str,
        expected_reported: int,
        expected_derived: int,
    ) -> None:
        """在事务内验证写入行数与预期一致。

        失败时抛出 FactCheckpointError 触发回滚。
        """
        result = conn.execute(
            "SELECT is_derived, COUNT(*) "
            "FROM financial_facts "
            "WHERE symbol = ? "
            "GROUP BY is_derived",
            [symbol],
        ).fetchall()

        actual: dict[bool, int] = {False: 0, True: 0}
        for row in result:
            actual[bool(row[0])] = row[1]

        if actual[False] != expected_reported:
            raise FactCheckpointError(
                f"Reported fact count mismatch: "
                f"expected {expected_reported}, wrote {actual[False]}"
            )

        if actual[True] != expected_derived:
            raise FactCheckpointError(
                f"Derived fact count mismatch: "
                f"expected {expected_derived}, wrote {actual[True]}"
            )

        logger.info(
            f"Count verification passed: "
            f"{actual[False]} reported, {actual[True]} derived"
        )


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
