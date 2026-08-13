"""M2 Stage 1 — 财务事实校验器。"""

from __future__ import annotations

import logging
import math
from datetime import date, datetime
from typing import Any

from ashare_research.facts.concepts import ConceptRegistry
from ashare_research.facts.units import UnitRegistry
from ashare_research.validation.fact_schema import (
    INSTANT_CONCEPTS,
    validate_fact_schema,
)
from ashare_research.validation.results import FactValidationResult

logger = logging.getLogger(__name__)


class FactValidator:
    """财务事实校验器。"""

    schema_version: str = "1.0"

    def __init__(self):
        pass

    @staticmethod
    def _parse_optional_iso_date(
        value: Any, field_name: str,
    ) -> date | None:
        """将可选的 ISO 日期字符串解析为 date，无效日期抛出 ValueError。

        捕获 2025-02-30、2025-13-01 等无效日历日期，
        同时也拒绝空字符串和空白字符串。
        """
        if value is None or (isinstance(value, str) and value.strip() == ""):
            return None
        if not isinstance(value, str):
            raise ValueError(
                f"{field_name}: expected str, got {type(value).__name__}: "
                f"{value!r}"
            )
        try:
            return date.fromisoformat(value.strip())
        except (ValueError, TypeError) as exc:
            raise ValueError(
                f"{field_name}: invalid calendar date: {value!r}"
            ) from exc

    def validate_batch(
        self, facts: list[dict[str, Any]]
    ) -> list[FactValidationResult]:
        """批量校验事实列表。"""
        results: list[FactValidationResult] = []
        now = datetime.now().isoformat()

        for fact in facts:
            results.extend(self.validate_single_fact(fact, now))

        # 跨事实检查
        results.extend(self._check_duplicates(facts, now))

        return results

    def validate_single_fact(
        self, fact: dict[str, Any], now_override: str = "",
    ) -> list[FactValidationResult]:
        """校验单条事实。"""
        now = now_override or datetime.now().isoformat()
        results: list[FactValidationResult] = []
        fid = fact.get("fact_id", "unknown")

        # FACT_SCHEMA_001: 必需字段
        schema_issues = validate_fact_schema(fact)
        if schema_issues:
            results.append(FactValidationResult(
                rule_id="FACT_SCHEMA_001", target_id=fid,
                severity="error", passed=False,
                expected="All required fields present",
                actual=str(schema_issues),
                message=f"Schema issues: {schema_issues}",
                checked_at=now,
            ))
        else:
            results.append(FactValidationResult(
                rule_id="FACT_SCHEMA_001", target_id=fid,
                severity="error", passed=True,
                message="All required fields present",
                checked_at=now,
            ))

        # FACT_VALUE_001: 无 NaN
        val = fact.get("value")
        if val is not None and isinstance(val, float) and math.isnan(val):
            results.append(FactValidationResult(
                rule_id="FACT_VALUE_001", target_id=fid,
                severity="error", passed=False,
                expected="Finite numeric value",
                actual="NaN",
                message="Value is NaN",
                checked_at=now,
            ))
        else:
            results.append(FactValidationResult(
                rule_id="FACT_VALUE_001", target_id=fid,
                severity="error", passed=True,
                message="Value is finite",
                checked_at=now,
            ))

        # FACT_VALUE_002: 无 Inf
        if val is not None and isinstance(val, float) and math.isinf(val):
            results.append(FactValidationResult(
                rule_id="FACT_VALUE_002", target_id=fid,
                severity="error", passed=False,
                expected="Finite numeric value",
                actual="Inf",
                message="Value is Inf",
                checked_at=now,
            ))
        else:
            results.append(FactValidationResult(
                rule_id="FACT_VALUE_002", target_id=fid,
                severity="error", passed=True,
                message="Value is finite",
                checked_at=now,
            ))

        # FACT_UNIT_001: 单位可识别
        unit = fact.get("unit", "")
        if UnitRegistry.validate_unit(unit) or unit in ("CNY", "SHARE",
                                                         "DECIMAL", "TEXT",
                                                         "BOOLEAN",
                                                         "CNY_PER_SHARE"):
            results.append(FactValidationResult(
                rule_id="FACT_UNIT_001", target_id=fid,
                severity="error", passed=True,
                message=f"Unit '{unit}' is valid",
                checked_at=now,
            ))
        else:
            results.append(FactValidationResult(
                rule_id="FACT_UNIT_001", target_id=fid,
                severity="error", passed=False,
                expected="Recognized unit",
                actual=unit,
                message=f"Unrecognized unit: '{unit}'",
                checked_at=now,
            ))

        # FACT_CONCEPT_001: concept_id 已注册
        cid = fact.get("concept_id", "")
        if ConceptRegistry.is_registered(cid):
            results.append(FactValidationResult(
                rule_id="FACT_CONCEPT_001", target_id=fid,
                severity="error", passed=True,
                message=f"Concept '{cid}' registered",
                checked_at=now,
            ))
        elif cid:
            results.append(FactValidationResult(
                rule_id="FACT_CONCEPT_001", target_id=fid,
                severity="error", passed=False,
                expected="Registered concept_id",
                actual=cid,
                message=f"Unregistered concept_id: '{cid}'",
                checked_at=now,
            ))

        # FACT_PERIOD_001: period_start <= period_end, filing_date >= period_end
        pe = fact.get("period_end", "")
        ps = fact.get("period_start", "")
        filing = fact.get("filing_date", "")
        period_ok = True
        try:
            pe_date = self._parse_optional_iso_date(pe, "period_end")
            ps_date = self._parse_optional_iso_date(ps, "period_start")
            filing_date = self._parse_optional_iso_date(filing, "filing_date")
        except ValueError as exc:
            results.append(FactValidationResult(
                rule_id="FACT_PERIOD_001", target_id=fid,
                severity="error", passed=False,
                expected="period_end, period_start, and filing_date "
                         "must be valid calendar dates (ISO 8601, YYYY-MM-DD)",
                actual=str(exc),
                message=str(exc),
                checked_at=now,
            ))
            period_ok = False
        if period_ok:
            if pe_date is None:
                results.append(FactValidationResult(
                    rule_id="FACT_PERIOD_001", target_id=fid,
                    severity="error", passed=False,
                    expected="period_end 必须非空",
                    actual="空或缺失",
                    message="period_end must be non-empty",
                    checked_at=now,
                ))
            elif ps_date is not None and ps_date > pe_date:
                results.append(FactValidationResult(
                    rule_id="FACT_PERIOD_001", target_id=fid,
                    severity="error", passed=False,
                    expected="period_start <= period_end",
                    actual=f"period_start={ps} > period_end={pe}",
                    message=f"period_start {ps} after period_end {pe}",
                    checked_at=now,
                ))
            elif pe_date is not None and filing_date is not None and filing_date < pe_date:
                results.append(FactValidationResult(
                    rule_id="FACT_PERIOD_001", target_id=fid,
                    severity="error", passed=False,
                    expected="filing_date >= period_end",
                    actual=f"filing_date={filing} < period_end={pe}",
                    message=f"filing_date {filing} before period_end {pe}",
                    checked_at=now,
                ))
            else:
                results.append(FactValidationResult(
                    rule_id="FACT_PERIOD_001", target_id=fid,
                    severity="error", passed=True,
                    message="filing_date >= period_end, "
                            "period_start <= period_end",
                    checked_at=now,
                ))

        # FACT_DATE_001: period_end 对所有事实必须是有效日历日期；
        #                period_start 若存在也必须有效。
        try:
            self._parse_optional_iso_date(
                fact.get("period_end", ""), "period_end"
            )
        except ValueError as exc:
            results.append(FactValidationResult(
                rule_id="FACT_DATE_001", target_id=fid,
                severity="error", passed=False,
                expected="period_end 为有效日历日期 (YYYY-MM-DD)",
                actual=str(exc),
                message=str(exc),
                checked_at=now,
            ))
        ps_raw = fact.get("period_start", "")
        if isinstance(ps_raw, str) and ps_raw.strip():
            try:
                self._parse_optional_iso_date(ps_raw, "period_start")
            except ValueError as exc:
                results.append(FactValidationResult(
                    rule_id="FACT_DATE_001", target_id=fid,
                    severity="error", passed=False,
                    expected="period_start 为有效日历日期 (YYYY-MM-DD)",
                    actual=str(exc),
                    message=str(exc),
                    checked_at=now,
                ))
        if not any(r.rule_id == "FACT_DATE_001" for r in results):
            results.append(FactValidationResult(
                rule_id="FACT_DATE_001", target_id=fid,
                severity="error", passed=True,
                message="period_end (and period_start if present) 为有效日期",
                checked_at=now,
            ))

        # FACT_INSTANT_001: 时点概念不得通过相减派生（双源对账派生除外）。
        # 规则文档化本意（rule_registry.py）是禁止"相减"生成时点字段；双源对账
        # 是 company_official + exchange_official 跨来源精确核验，不构成相减派生，
        # 故对 derivation_definition_id == official_dual_source_reconciliation 放行。
        if (
            fact.get("is_derived")
            and cid in INSTANT_CONCEPTS
            and fact.get("derivation_definition_id")
            != "official_dual_source_reconciliation"
        ):
            results.append(FactValidationResult(
                rule_id="FACT_INSTANT_001", target_id=fid,
                severity="error", passed=False,
                expected="Instant concepts must not be derived by subtraction",
                actual=f"Derived instant concept: {cid}",
                message="Instant fact must not be derived by subtraction",
                checked_at=now,
            ))

        # FACT_MISSING_001: 缺失不是 0
        vs = fact.get("verification_status", "")
        if vs == "missing" and fact.get("value") == 0:
            results.append(FactValidationResult(
                rule_id="FACT_MISSING_001", target_id=fid,
                severity="error", passed=False,
                expected="Missing value must not be 0",
                actual="value=0 with status=missing",
                message="Missing data converted to zero",
                checked_at=now,
            ))

        # FACT_ANNOUNCE_001: verified/reconciled 需要有效 announcement_date >= period_end;
        #                     未核验事实的 announcement_date 若存在也必须有效。
        ad = fact.get("announcement_date", "")
        if vs in ("verified", "reconciled"):
            if not (isinstance(ad, str) and ad.strip()):
                results.append(FactValidationResult(
                    rule_id="FACT_ANNOUNCE_001", target_id=fid,
                    severity="error", passed=False,
                    expected="announcement_date 为非空有效日期",
                    actual="空或缺失",
                    message="Verified/reconciled fact lacks announcement_date",
                    checked_at=now,
                ))
            else:
                try:
                    ad_date = self._parse_optional_iso_date(ad, "announcement_date")
                except ValueError as exc:
                    results.append(FactValidationResult(
                        rule_id="FACT_ANNOUNCE_001", target_id=fid,
                        severity="error", passed=False,
                        expected="announcement_date 为有效日历日期 (YYYY-MM-DD)",
                        actual=str(exc),
                        message=str(exc),
                        checked_at=now,
                    ))
                else:
                    pe_raw = fact.get("period_end", "")
                    try:
                        pe_date = self._parse_optional_iso_date(pe_raw, "period_end")
                    except ValueError:
                        pe_date = None
                    if pe_date is not None and ad_date is not None and ad_date < pe_date:
                        results.append(FactValidationResult(
                            rule_id="FACT_ANNOUNCE_001", target_id=fid,
                            severity="error", passed=False,
                            expected="announcement_date >= period_end",
                            actual=f"announcement_date={ad} < period_end={pe_raw}",
                            message=f"announcement_date {ad} before period_end {pe_raw}",
                            checked_at=now,
                        ))
                    else:
                        results.append(FactValidationResult(
                            rule_id="FACT_ANNOUNCE_001", target_id=fid,
                            severity="error", passed=True,
                            message="announcement_date 有效且 >= period_end",
                            checked_at=now,
                        ))
        elif isinstance(ad, str) and ad.strip():
            try:
                self._parse_optional_iso_date(ad, "announcement_date")
            except ValueError as exc:
                results.append(FactValidationResult(
                    rule_id="FACT_ANNOUNCE_001", target_id=fid,
                    severity="error", passed=False,
                    expected="announcement_date 为有效日历日期或空",
                    actual=str(exc),
                    message=str(exc),
                    checked_at=now,
                ))
            else:
                results.append(FactValidationResult(
                    rule_id="FACT_ANNOUNCE_001", target_id=fid,
                    severity="error", passed=True,
                    message="announcement_date 有效",
                    checked_at=now,
                ))

        # FACT_SOURCE_001: 按事实类型分开的来源语义规则。
        #   - verified 原始官方事实：source_tier 必须为 company_official /
        #     exchange_official，且具备来源身份（source_id / source_provider
        #     非空）。candidate_aggregator / reconciled_derived 不得冒充。
        #   - reconciled 派生核验事实：source_tier 必须为 reconciled_derived，
        #     且具备完整派生元数据（provider / derivation / >=2 输入 /
        #     eligible）。不得伪装为原始官方来源。
        #   来源证据（source_document / source_url / source_hash）由
        #   Reconciliation Engine 硬证据门禁（仅对双源输入）与官方 Provider
        #   canonical 入口强制；announcement_date / available_at 由
        #   FACT_ANNOUNCE_001 / FACT_PIT_001 强制。
        if vs == "verified":
            source_tier = fact.get("source_tier", "")
            source_id = fact.get("source_id", "")
            source_provider = fact.get("source_provider", "")
            if (
                not source_id
                or not source_provider
                or source_tier not in (
                    "company_official", "exchange_official",
                )
            ):
                results.append(FactValidationResult(
                    rule_id="FACT_SOURCE_001", target_id=fid,
                    severity="error", passed=False,
                    expected=(
                        "source_id 与 source_provider 非空，且 "
                        "source_tier 为 company_official 或 "
                        "exchange_official"
                    ),
                    actual=(
                        f"source_id={source_id}, "
                        f"source_provider={source_provider}, "
                        f"source_tier={source_tier}"
                    ),
                    message=(
                        "verified 事实必须来自官方来源"
                        "（company_official / exchange_official），"
                        "不得为 candidate_aggregator 或 reconciled_derived"
                    ),
                    checked_at=now,
                ))
        elif vs == "reconciled":
            recon_issues = self._check_reconciled_source(fact, now)
            results.extend(recon_issues)

        # FACT_PIT_001: available_at 若非空须为有效日期；
        #               available_at >= filing_date（若 filing_date 存在）；
        #               eligible_for_metrics=true 时 available_at 必须非空；
        #               verified/reconciled 时 available_at 必须非空且 >= announcement_date。
        eligible = fact.get("eligible_for_metrics", False)
        available_at = fact.get("available_at", "")
        pit_failed = False
        if isinstance(available_at, str) and available_at.strip():
            try:
                aa_date = self._parse_optional_iso_date(available_at, "available_at")
            except ValueError as exc:
                results.append(FactValidationResult(
                    rule_id="FACT_PIT_001", target_id=fid,
                    severity="error", passed=False,
                    expected="available_at 为有效日历日期 (YYYY-MM-DD) 或空",
                    actual=str(exc),
                    message=str(exc),
                    checked_at=now,
                ))
                aa_date = None
                pit_failed = True
        else:
            aa_date = None
        # available_at >= filing_date（若两者均有效）
        if aa_date is not None and not pit_failed:
            filing_raw = fact.get("filing_date", "")
            if isinstance(filing_raw, str) and filing_raw.strip():
                try:
                    filing_date = self._parse_optional_iso_date(filing_raw, "filing_date")
                except ValueError:
                    filing_date = None
                if filing_date is not None and aa_date < filing_date:
                    results.append(FactValidationResult(
                        rule_id="FACT_PIT_001", target_id=fid,
                        severity="error", passed=False,
                        expected="available_at >= filing_date",
                        actual=f"available_at={available_at} < filing_date={filing_raw}",
                        message=f"available_at {available_at} before filing_date {filing_raw}",
                        checked_at=now,
                    ))
                    pit_failed = True
        # eligible_for_metrics=true 时 available_at 必须非空
        if eligible and not pit_failed and aa_date is None:
                results.append(FactValidationResult(
                    rule_id="FACT_PIT_001", target_id=fid,
                    severity="error", passed=False,
                    expected="eligible_for_metrics=true 时 available_at 必须非空",
                    actual="空或缺失",
                    message="PIT 适格事实缺少 available_at",
                    checked_at=now,
                ))
                pit_failed = True
        # verified/reconciled 时 available_at 必须非空且 >= announcement_date
        if vs in ("verified", "reconciled") and not pit_failed:
            if aa_date is None:
                results.append(FactValidationResult(
                    rule_id="FACT_PIT_001", target_id=fid,
                    severity="error", passed=False,
                    expected="verified/reconciled 时 available_at 必须非空",
                    actual="空或缺失",
                    message="verified/reconciled 事实缺少 available_at",
                    checked_at=now,
                ))
                pit_failed = True
            else:
                ad = fact.get("announcement_date", "")
                try:
                    ad_date = self._parse_optional_iso_date(ad, "announcement_date")
                except ValueError:
                    ad_date = None
                if ad_date is not None and aa_date < ad_date:
                    results.append(FactValidationResult(
                        rule_id="FACT_PIT_001", target_id=fid,
                        severity="error", passed=False,
                        expected="available_at >= announcement_date",
                        actual=f"available_at={available_at} < announcement_date={ad}",
                        message=f"available_at {available_at} before announcement_date {ad}",
                        checked_at=now,
                    ))
                    pit_failed = True
                else:
                    results.append(FactValidationResult(
                        rule_id="FACT_PIT_001", target_id=fid,
                        severity="error", passed=True,
                        message="available_at 有效且 >= announcement_date",
                        checked_at=now,
                    ))
        elif not pit_failed and not (eligible or vs in ("verified", "reconciled")):
            pass  # 无需 PIT 检查时产生任何结果
        elif not pit_failed:
            # eligible 且 aa_date 非空（已在上面通过）但没有 verified/reconciled 时报告成功
            results.append(FactValidationResult(
                rule_id="FACT_PIT_001", target_id=fid,
                severity="error", passed=True,
                message="available_at 有效",
                checked_at=now,
            ))

        # FACT_VERSION_001: fact_version==1 → supersedes_fact_id 必须为空；
        #                   fact_version>1 → supersedes_fact_id 必须非空且 != fact_id。
        fv = fact.get("fact_version", 1)
        sfid = fact.get("supersedes_fact_id", "")
        if fv == 1:
            if isinstance(sfid, str) and sfid.strip():
                results.append(FactValidationResult(
                    rule_id="FACT_VERSION_001", target_id=fid,
                    severity="error", passed=False,
                    expected="fact_version=1 时 supersedes_fact_id 必须为空",
                    actual=f"supersedes_fact_id={sfid}",
                    message="Version 1 fact must not reference a superseded fact",
                    checked_at=now,
                ))
            else:
                results.append(FactValidationResult(
                    rule_id="FACT_VERSION_001", target_id=fid,
                    severity="error", passed=True,
                    message="Version 1 fact has no supersedes_fact_id",
                    checked_at=now,
                ))
        elif isinstance(fv, int) and fv > 1:
            if not (isinstance(sfid, str) and sfid.strip()):
                results.append(FactValidationResult(
                    rule_id="FACT_VERSION_001", target_id=fid,
                    severity="error", passed=False,
                    expected="fact_version>1 时 supersedes_fact_id 必须非空",
                    actual="空或缺失",
                    message=f"Version {fv} fact must have supersedes_fact_id",
                    checked_at=now,
                ))
            elif sfid == fid:
                results.append(FactValidationResult(
                    rule_id="FACT_VERSION_001", target_id=fid,
                    severity="error", passed=False,
                    expected="supersedes_fact_id != fact_id",
                    actual=f"supersedes_fact_id={sfid} == fact_id={fid}",
                    message="supersedes_fact_id 不得指向自身",
                    checked_at=now,
                ))
            else:
                results.append(FactValidationResult(
                    rule_id="FACT_VERSION_001", target_id=fid,
                    severity="error", passed=True,
                    message=f"Version {fv} fact with valid supersedes_fact_id",
                    checked_at=now,
                ))

        # FACT_ELIGIBILITY_001: 只有 verified/reconciled 可设置指标适格
        if eligible and vs not in ("verified", "reconciled"):
            results.append(FactValidationResult(
                rule_id="FACT_ELIGIBILITY_001", target_id=fid,
                severity="error", passed=False,
                expected="verification_status 为 verified 或 reconciled",
                actual=f"verification_status={vs}",
                message="只有 verified/reconciled 事实可设置 eligible_for_metrics=true",
                checked_at=now,
            ))

        # FACT_DERIVE_001: 派生结论有输入
        if fact.get("is_derived"):
            inputs = fact.get("input_fact_ids", "")
            if not inputs:
                results.append(FactValidationResult(
                    rule_id="FACT_DERIVE_001", target_id=fid,
                    severity="error", passed=False,
                    expected="At least one input fact",
                    actual="No input_fact_ids",
                    message="Derived fact has no input facts",
                    checked_at=now,
                ))

        return results

    def _check_duplicates(
        self, facts: list[dict[str, Any]], now: str,
    ) -> list[FactValidationResult]:
        """FACT_DUP_001: 检查重复（含版本和来源键）。"""
        seen: set[tuple] = set()
        results: list[FactValidationResult] = []
        for fact in facts:
            key = (
                fact.get("concept_id", ""),
                fact.get("concept_version", "1"),
                fact.get("symbol", ""),
                fact.get("context_id", ""),
                fact.get("source_id", ""),
                str(fact.get("fact_version", 1)),
                fact.get("restatement_version", "original"),
            )
            if key in seen:
                results.append(FactValidationResult(
                    rule_id="FACT_DUP_001",
                    target_id=fact.get("fact_id", ""),
                    severity="error", passed=False,
                    expected=(
                        "Unique (concept_id, concept_version, "
                        "symbol, context_id, source_id, fact_version, "
                        "restatement_version)"
                    ),
                    actual=f"Duplicate key: {key}",
                    message="Duplicate fact detected",
                    checked_at=now,
                ))
            seen.add(key)
        return results

    def _check_reconciled_source(
        self, fact: dict[str, Any], now: str,
    ) -> list[FactValidationResult]:
        """FACT_SOURCE_001 (reconciled 分支): 派生核验事实来源语义。

        仅返回失败项（与 verified 分支一致：通过时不产生结果行）。
        reconciled 事实必须：
          - source_tier == reconciled_derived
          - source_provider == official_reconciliation
          - source_id 非空
          - is_derived == true
          - derivation_definition_id == official_dual_source_reconciliation
          - derivation_version 非空
          - input_fact_ids 至少 2 个不同 fact_id
          - eligible_for_metrics == true
        不得伪装为原始官方来源（company_official / exchange_official）。
        """
        fid = fact.get("fact_id", "unknown")
        raw_inputs = fact.get("input_fact_ids", "")
        if isinstance(raw_inputs, list):
            input_ids = {
                str(x).strip() for x in raw_inputs if str(x).strip()
            }
        else:
            input_ids = {
                s.strip() for s in str(raw_inputs).split(",") if s.strip()
            }
        checks: list[tuple[str, bool, str, str]] = [
            (
                "source_tier",
                fact.get("source_tier", "") == "reconciled_derived",
                "source_tier == reconciled_derived",
                f"source_tier={fact.get('source_tier', '')}",
            ),
            (
                "source_provider",
                fact.get("source_provider", "")
                == "official_reconciliation",
                "source_provider == official_reconciliation",
                f"source_provider={fact.get('source_provider', '')}",
            ),
            (
                "source_id",
                bool(str(fact.get("source_id", "")).strip()),
                "source_id 非空",
                f"source_id={fact.get('source_id', '')}",
            ),
            (
                "is_derived",
                fact.get("is_derived") is True,
                "is_derived == true",
                f"is_derived={fact.get('is_derived')}",
            ),
            (
                "derivation_definition_id",
                fact.get("derivation_definition_id", "")
                == "official_dual_source_reconciliation",
                "derivation_definition_id == "
                "official_dual_source_reconciliation",
                f"derivation_definition_id="
                f"{fact.get('derivation_definition_id', '')}",
            ),
            (
                "derivation_version",
                bool(str(fact.get("derivation_version", "")).strip()),
                "derivation_version 非空",
                f"derivation_version="
                f"{fact.get('derivation_version', '')}",
            ),
            (
                "input_fact_ids",
                len(input_ids) >= 2,
                "input_fact_ids 至少 2 个不同 fact_id",
                f"distinct_inputs={len(input_ids)}",
            ),
            (
                "eligible_for_metrics",
                fact.get("eligible_for_metrics") is True,
                "eligible_for_metrics == true",
                f"eligible_for_metrics="
                f"{fact.get('eligible_for_metrics')}",
            ),
        ]
        return [
            FactValidationResult(
                rule_id="FACT_SOURCE_001", target_id=fid,
                severity="error", passed=False,
                expected=c[2], actual=c[3],
                message=f"reconciled 事实 {c[0]} 不满足派生来源契约",
                checked_at=now,
            )
            for c in checks if not c[1]
        ]
