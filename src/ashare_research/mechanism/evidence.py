"""Frozen primary decision and evidence-level engine."""

from __future__ import annotations

from ashare_research.mechanism.regression import primary_positive_evidence


def evidence_level(
    *,
    gamma: float,
    gamma_ci_lower: float,
    descriptive_relationship_present: bool,
    controls_trusted: bool,
    robustness_triggered: bool,
) -> int:
    if (
        primary_positive_evidence(gamma, gamma_ci_lower)
        and controls_trusted
        and not robustness_triggered
    ):
        level = 3
    elif descriptive_relationship_present:
        level = 2
    else:
        level = 1
    if level > 3:
        raise ValueError("evidence level above 3 is forbidden")
    return level


def primary_decision(gamma: float, gamma_ci_lower: float) -> str:
    if primary_positive_evidence(gamma, gamma_ci_lower):
        return "PRIMARY_POSITIVE_ABNORMAL_PERFORMANCE_ESTABLISHED"
    return "PRIMARY_POSITIVE_ABNORMAL_PERFORMANCE_NOT_ESTABLISHED"


def interpretation_boundary(level: int) -> str:
    if level == 3:
        return "Daily controlled evidence only; no minute-data or funding-actor inference."
    if level == 2:
        return (
            "Surface/descriptive relationship present; controlled primary effect "
            "not established."
        )
    return "Primary positive abnormal performance not established."

