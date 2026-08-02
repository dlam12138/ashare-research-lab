"""Stage 2H risk-veto contract, PIT and reproducibility tests."""

from __future__ import annotations

import json
from pathlib import Path

from ashare_research.reproducibility.artifacts import compare_artifact_runs, verify_artifacts
from ashare_research.risk_veto.contracts import RISK_IDS, evaluate_observations
from ashare_research.tools.petrochina_risk_veto_vertical_slice import (
    _input_ledgers,
    build_event_records,
    run_formal,
    run_test_capsule,
    verify_contracts,
)


def test_stage2h_contracts_and_frozen_methodology_pass() -> None:
    result = verify_contracts()
    assert result["status"] == "pass_with_explicit_gaps"
    assert result["risk_contract"]["risk_count"] == 8
    assert result["score_eligible"] is False


def test_formal_runs_are_offline_and_byte_reproducible(tmp_path: Path) -> None:
    first = run_formal(output_root=tmp_path / "a", run_id="risk_run")
    second = run_formal(output_root=tmp_path / "b", run_id="risk_run")
    assert first["status"] == second["status"] == "conditional_pass"
    left = tmp_path / "a" / "risk_run"
    right = tmp_path / "b" / "risk_run"
    assert verify_artifacts(left)["status"] == "pass"
    assert verify_artifacts(right)["status"] == "pass"
    comparison = compare_artifact_runs(left, right)
    assert comparison["status"] == "pass"
    summary = json.loads((left / "summary.json").read_text(encoding="utf-8"))
    assert summary["missing_evidence_risk_ids"] == [
        "formal_regulatory_investigation_or_major_discipline",
        "controlling_shareholder_fund_occupation_or_related_guarantee",
    ]
    assert summary["observed_risk_ids"] == []
    assert summary["default_db_mutated"] is False


def test_pit_filter_does_not_use_later_annual_reports() -> None:
    evidence, events, searches = _input_ledgers()
    early = evaluate_observations(
        symbol="601857.SH",
        as_of_date="2023-03-30",
        events=events,
        search_registers=searches,
        evidence=evidence,
    )
    audit = next(item for item in early if item["risk_id"] == "modified_audit_opinion")
    assert audit["inputs"]["pit_visible_event_count"] == 2
    assert all("2024" not in event_id for event_id in audit["event_ids"])


def test_frozen_non_triggers_remain_non_triggers() -> None:
    events = build_event_records()
    assert all(
        event["status"] != "observed"
        for event in events
        if event["risk_id"]
        in {
            "modified_audit_opinion",
            "material_error_restatement",
            "controlling_shareholder_pledge_risk",
            "material_related_party_transaction_risk",
            "repeated_equity_financing_or_material_dilution",
        }
    )
    assert any(event["classification"] == "common_control_combination" for event in events)
    assert any(event["classification"] == "proposed_or_authorized_only" for event in events)


def test_synthetic_capsule_exercises_triggers_and_correction(tmp_path: Path) -> None:
    result = run_test_capsule(tmp_path, "synthetic")
    assert result["status"] == "pass"
    run_dir = tmp_path / "synthetic"
    summary = json.loads((run_dir / "summary.json").read_text(encoding="utf-8"))
    assert set(summary["triggered_risks"]) == set(RISK_IDS)
    assert summary["correction_supersedes"].startswith("risk_event_")
    assert verify_artifacts(run_dir)["status"] == "pass"
