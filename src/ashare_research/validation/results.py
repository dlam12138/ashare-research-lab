"""M2 Stage 1 — 校验结果数据结构。"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class FactValidationResult:
    """单次校验的结果。"""
    rule_id: str
    rule_version: str = "1"
    target_id: str = ""
    severity: str = "error"
    passed: bool = True
    expected: str = ""
    actual: str = ""
    message: str = ""
    checked_at: str = ""


@dataclass
class ValidationRun:
    """一次完整校验运行的结果摘要。"""
    validation_run_id: str = ""
    started_at: str = ""
    completed_at: str = ""
    rule_versions: str = ""
    result_count: int = 0
    error_count: int = 0
    warning_count: int = 0
    status: str = "pending"       # pending / passed / failed / conditional_pass
    results: list[FactValidationResult] = field(default_factory=list)


def summarize_results(
    results: list[FactValidationResult],
) -> dict[str, int]:
    """汇总校验结果统计。"""
    error_count = sum(1 for r in results if r.severity == "error" and not r.passed)
    warning_count = sum(1 for r in results if r.severity == "warning" and not r.passed)
    passed_count = sum(1 for r in results if r.passed)
    failed_count = len(results) - passed_count

    return {
        "total": len(results),
        "passed": passed_count,
        "failed": failed_count,
        "error_count": error_count,
        "warning_count": warning_count,
    }


def result_to_dict(result: FactValidationResult) -> dict:
    """序列化为字典。"""
    return {
        "rule_id": result.rule_id,
        "rule_version": result.rule_version,
        "target_id": result.target_id,
        "severity": result.severity,
        "passed": result.passed,
        "expected": result.expected,
        "actual": result.actual,
        "message": result.message,
        "checked_at": result.checked_at,
    }
