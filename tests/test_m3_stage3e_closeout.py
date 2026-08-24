"""Repository-only tests for the M3 Stage 3E closeout boundary."""

from __future__ import annotations

import json
from pathlib import Path

from ashare_research.tools.m3_stage3e_closeout_check import validate_closeout

ROOT = Path(__file__).resolve().parents[1]


def _load(name: str) -> dict:
    return json.loads((ROOT / "reports" / name).read_text(encoding="utf-8"))


def test_closeout_validator_passes_without_external_data() -> None:
    assert validate_closeout(ROOT) == []


def test_final_disposition_has_exact_daily_status() -> None:
    final = _load("m3_stage3e_daily_mechanism_final_disposition_v1.json")
    assert final["daily_mechanism_disposition"] == "M3_DAILY_MECHANISM_NOT_ESTABLISHED"
    assert final["stop_condition"] == "STOP_FOR_NORTH_STAR_REVIEW"


def test_development_primary_is_frozen_and_not_established() -> None:
    final = _load("m3_stage3e_daily_mechanism_final_disposition_v1.json")
    development = final["development"]
    assert development["primary_decision"] == (
        "M3_PRIMARY_DEVELOPMENT_POSITIVE_ABNORMAL_PERFORMANCE_NOT_ESTABLISHED"
    )
    assert (development["sample_start"], development["sample_end"]) == (
        "2015-03-16",
        "2022-12-30",
    )
    assert (development["nobs"], development["crash_count"]) == (1902, 330)


def test_development_gamma_and_ci_are_frozen() -> None:
    final = _load("m3_stage3e_daily_mechanism_final_disposition_v1.json")
    assert final["development"]["gamma"] == 0.0005072734676652487
    assert final["development"]["bootstrap_ci"] == [
        -0.0021987423016553366,
        0.0033325010311833106,
    ]


def test_registered_robustness_is_complete_but_nonconfirmatory() -> None:
    final = _load("m3_stage3e_daily_mechanism_final_disposition_v1.json")
    robustness = final["development_robustness"]
    assert robustness["status"] == "M3_REGISTERED_EXECUTABLE_DEVELOPMENT_ROBUSTNESS_COMPLETED"
    assert robustness["all_threshold_bh_reject"] is False
    assert robustness["threshold_gamma_direction"] == "MIXED"
    assert robustness["leave_one_year_out_direction"] == "MIXED"


def test_registered_unexecuted_gap_statuses_are_preserved() -> None:
    final = _load("m3_stage3e_daily_mechanism_final_disposition_v1.json")
    assert set(final["development_robustness"]["registered_not_executed"]) == {
        "leave_one_event_out",
        "alternative_market_proxies",
        "industry_ex_target",
        "volume_abnormality",
        "market_regimes",
    }


def test_identity_recovery_facts_are_recorded() -> None:
    final = _load("m3_stage3e_daily_mechanism_final_disposition_v1.json")
    recovery = final["identity_recovery"]
    assert (recovery["resolution_total"], recovery["resolved_total"]) == (159, 159)
    assert (recovery["resolved_a"], recovery["resolved_b"]) == (146, 13)
    assert (recovery["unresolved_total"], recovery["extra_expansion_total"]) == (0, 0)
    assert recovery["conflicts_resolved"] == 6
    assert recovery["true_required_missing"] == 57


def test_holdout_is_consumed_but_has_no_primary_statistic() -> None:
    final = _load("m3_stage3e_daily_mechanism_final_disposition_v1.json")
    holdout = final["holdout"]
    assert holdout["status"] == "UNSEALED_CONSUMED"
    assert holdout["accepted_primary_execution_count"] == 0
    assert holdout["primary_statistic_observed"] is False
    assert holdout["final_status"] == "M3_HOLDOUT_PRIMARY_INCONCLUSIVE_TECHNICAL_OR_COVERAGE_GAP"


def test_holdout_coverage_gate_remains_failed_closed() -> None:
    final = _load("m3_stage3e_daily_mechanism_final_disposition_v1.json")
    holdout = final["holdout"]
    assert holdout["minimum_market_coverage"] == 0.9736963544070143
    assert holdout["minimum_market_coverage"] < holdout["coverage_gate"]
    assert holdout["true_required_missing"] == 57
    assert holdout["invalid_proxy_rows"] == 535


def test_holdout_gamma_and_computation_flags_are_absent_or_false() -> None:
    final = _load("m3_stage3e_daily_mechanism_final_disposition_v1.json")
    holdout = final["holdout"]
    assert holdout["holdout_gamma"] is None
    assert all(holdout[key] is False for key in (
        "market_proxy_materialized",
        "FRED_requested",
        "CNI_requested",
        "Crash_computed",
        "OLS_executed",
        "bootstrap_executed",
        "gamma_computed",
    ))


def test_evidence_ceiling_and_numeric_level_are_preserved() -> None:
    final = _load("m3_stage3e_daily_mechanism_final_disposition_v1.json")
    assert final["evidence"]["ceiling"] == "M3_DEVELOPMENT_EVIDENCE_CEILING_LEVEL_2"
    assert final["evidence"]["numeric_level"] is None
    assert final["evidence"]["level_status"] == "M3_FINAL_NUMERIC_EVIDENCE_LEVEL_UNASSIGNED"


def test_further_recovery_and_escalation_are_not_authorized() -> None:
    final = _load("m3_stage3e_daily_mechanism_final_disposition_v1.json")
    assert final["further_holdout_recovery"]["authorized"] is False
    assert final["minute_level"]["authorized"] is False
    assert final["minute_level"]["status"] == "M3_MINUTE_LEVEL_ESCALATION_NOT_JUSTIFIED"
    assert final["index_contribution"]["authorized"] is False


def test_gap_register_has_nine_nonautomatic_gaps() -> None:
    gaps = _load("m3_stage3e_explicit_evidence_gaps_v1.json")["gaps"]
    assert [item["id"] for item in gaps] == [f"GAP_{number:03d}" for number in range(1, 10)]
    assert all(item["status"] == "OPEN_EXPLICIT_EVIDENCE_GAP" for item in gaps)
    assert all(item["not_automatic_todo"] is True for item in gaps)


def test_conditional_closeout_does_not_authorize_next_stage() -> None:
    decision = _load("m3_stage3e_milestone_closeout_decision_v1.json")
    assert decision["decision"] == "M3_MILESTONE_CONDITIONAL_CLOSEOUT_ALLOWED"
    assert decision["milestone_status"] == "CONDITIONALLY_CLOSED"
    assert decision["full_evidence_completion"] is False
    assert all(decision[key] is False for key in (
        "new_holdout_recovery_allowed",
        "minute_escalation_allowed",
        "index_contribution_authorized",
        "m4_authorized",
        "m5_authorized",
    ))


def test_readme_has_current_closeout_facts_and_no_stale_148_claim() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "CONDITIONALLY CLOSED" in readme
    assert "M3_DAILY_MECHANISM_NOT_ESTABLISHED" in readme
    assert "0.9736963544070143" in readme
    assert "148 eligible securities" not in readme
