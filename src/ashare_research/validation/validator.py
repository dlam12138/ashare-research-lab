"""M2 Stage 1 — 财务事实校验器。"""

from __future__ import annotations

import logging
import math
from datetime import datetime
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

        # FACT_PERIOD_001: filing_date >= period_end
        filing = fact.get("filing_date", "")
        period_end = fact.get("period_end", "")
        if filing and period_end and filing < period_end:
            results.append(FactValidationResult(
                rule_id="FACT_PERIOD_001", target_id=fid,
                severity="error", passed=False,
                expected="filing_date >= period_end",
                actual=f"{filing} < {period_end}",
                message="Announcement date precedes report period end",
                checked_at=now,
            ))
        else:
            results.append(FactValidationResult(
                rule_id="FACT_PERIOD_001", target_id=fid,
                severity="error", passed=True,
                message="filing_date >= period_end or not applicable",
                checked_at=now,
            ))

        # FACT_INSTANT_001: 时点概念不是派生（由派生引擎保证，此处仅检查）
        if fact.get("is_derived") and cid in INSTANT_CONCEPTS:
            results.append(FactValidationResult(
                rule_id="FACT_INSTANT_001", target_id=fid,
                severity="error", passed=False,
                expected="Instant concepts must not be derived",
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

        # FACT_ANNOUNCE_001: verified 需要 announcement_date
        if vs == "verified" and not fact.get("announcement_date"):
            results.append(FactValidationResult(
                rule_id="FACT_ANNOUNCE_001", target_id=fid,
                severity="warning", passed=False,
                expected="announcement_date present",
                actual="Missing announcement_date",
                message="Verified fact lacks announcement_date",
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
        """FACT_DUP_001: 检查重复。"""
        seen: set[tuple] = set()
        results: list[FactValidationResult] = []
        for fact in facts:
            key = (fact.get("concept_id", ""),
                   fact.get("symbol", ""),
                   fact.get("context_id", ""))
            if key in seen:
                results.append(FactValidationResult(
                    rule_id="FACT_DUP_001",
                    target_id=fact.get("fact_id", ""),
                    severity="error", passed=False,
                    expected="Unique (concept_id, symbol, context_id)",
                    actual=f"Duplicate key: {key}",
                    message="Duplicate fact detected",
                    checked_at=now,
                ))
            seen.add(key)
        return results
