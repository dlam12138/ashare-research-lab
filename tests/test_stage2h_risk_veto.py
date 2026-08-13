"""Stage 2H.1 search PIT, supersession and evidence-lineage tests."""

from __future__ import annotations

import copy
from pathlib import Path

import pytest

from ashare_research.risk_veto.contracts import (
    RISK_IDS,
    RiskVetoContractError,
    evaluate_observations,
    select_search_register_as_of,
    validate_event_evidence_lineage,
    validate_observation,
    validate_search_register_chain,
)
from ashare_research.tools.petrochina_risk_veto_vertical_slice import (
    _input_ledgers,
    _synthetic_registers,
    build_event_records,
    run_formal,
    run_test_capsule,
    verify_contracts,
)


def test_stage2h1_contracts_and_frozen_methodology_pass() -> None:
    result = verify_contracts()
    assert result["status"] == "pass_with_explicit_gaps"
    assert result["risk_contract"]["risk_count"] == 8
    assert result["risk_contract"]["normalization_count"] == 105
    assert result["official_registry"]["evidence_alias_mapping"] == "complete"
    assert result["official_cache_required_for_formal"] is True
    assert result["score_eligible"] is False


def test_formal_real_mode_requires_explicit_cache_and_does_not_publish(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="official-cache-root"):
        run_formal(output_root=tmp_path, run_id="real_without_cache")


def test_search_register_is_pit_visible_only_when_available_and_covered() -> None:
    registers = _synthetic_registers()
    risk_id = "modified_audit_opinion"
    assert select_search_register_as_of(risk_id, "2025-01-01", registers) is None
    selected = select_search_register_as_of(risk_id, "2025-01-02", registers)
    assert selected is not None
    late_coverage = copy.deepcopy(registers)
    late_coverage[0]["coverage_end"] = "2025-01-03"
    assert select_search_register_as_of(risk_id, "2025-01-02", late_coverage) is None


def test_search_register_chain_rejects_cross_risk_reverse_time_and_branches() -> None:
    base = _synthetic_registers()[0]
    parent = copy.deepcopy(base)
    parent["search_register_id"] = "synthetic-chain-parent"
    child = copy.deepcopy(base)
    child["search_register_id"] = "synthetic-chain-child"
    child["supersedes_search_register_id"] = parent["search_register_id"]
    child["available_at"] = "2025-01-03T00:00:00+00:00"
    child["query_completed_at"] = "2025-01-03T00:00:00+00:00"
    validate_search_register_chain([parent, child])
    cross_risk = copy.deepcopy(child)
    cross_risk["search_register_id"] = "synthetic-cross-risk"
    cross_risk["risk_id"] = "going_concern_material_uncertainty"
    with pytest.raises(RiskVetoContractError, match="crosses risk"):
        validate_search_register_chain([parent, cross_risk])
    reverse = copy.deepcopy(child)
    reverse["search_register_id"] = "synthetic-reverse"
    reverse["available_at"] = "2025-01-01T00:00:00+00:00"
    reverse["query_completed_at"] = "2025-01-01T00:00:00+00:00"
    with pytest.raises(RiskVetoContractError, match="reverse availability"):
        validate_search_register_chain([parent, reverse])
    branch = copy.deepcopy(child)
    branch["search_register_id"] = "synthetic-branch"
    branch["available_at"] = "2025-01-04T00:00:00+00:00"
    branch["query_completed_at"] = "2025-01-04T00:00:00+00:00"
    with pytest.raises(RiskVetoContractError, match="conflicting branches"):
        validate_search_register_chain([parent, child, branch])


def test_historical_run_keeps_missing_search_evidence_explicit(tmp_path: Path) -> None:
    # Current v2 registers are available in 2026, so the 2025 PIT cannot use
    # them.  The observation remains missing_evidence, never a negative result.
    evidence, events, searches, normalizations = _input_ledgers()
    observations = evaluate_observations(
        symbol="601857.SH",
        as_of_date="2025-04-01",
        events=events,
        search_registers=searches,
        evidence=evidence,
        normalizations=normalizations,
    )
    assert observations
    assert all(item["status"] == "missing_evidence" for item in observations)
    assert all(
        "no PIT-visible search register" in " ".join(item["missing_reasons"])
        for item in observations
    )


def test_event_inputs_are_reconstructed_from_normalized_evidence() -> None:
    evidence, events, _, normalizations = _input_ledgers()
    assert len(normalizations) == 105
    target = next(
        item for item in events if item["risk_id"] == "material_related_party_transaction_risk"
    )
    tampered = copy.deepcopy(target)
    tampered["inputs"]["non_market"] = True
    with pytest.raises(RiskVetoContractError, match="not reconstructible"):
        validate_event_evidence_lineage(tampered, evidence, normalizations)
    unresolved = copy.deepcopy(target)
    unresolved_norm = next(
        item
        for item in normalizations
        if item["normalization_id"] in unresolved["normalization_ids"]
    )
    unresolved_norm["verification_status"] = "unresolved_conflict"
    with pytest.raises(RiskVetoContractError, match="unresolved normalization"):
        validate_event_evidence_lineage(unresolved, evidence, normalizations)


def test_frozen_boundaries_remain_non_triggers() -> None:
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


def test_synthetic_capsule_exercises_triggers_correction_and_reproducibility(
    tmp_path: Path,
) -> None:
    first = run_test_capsule(tmp_path / "a", "synthetic")
    second = run_test_capsule(tmp_path / "b", "synthetic")
    assert first["status"] == second["status"] == "pass"
    assert set(item["risk_id"] for item in first["before"] if item["status"] == "observed") == set(
        RISK_IDS
    )
    after_modified = next(
        item for item in first["after"] if item["risk_id"] == "modified_audit_opinion"
    )
    assert after_modified["status"] == "not_observed_within_bounded_evidence"
    assert after_modified["superseded_event_ids"]
    from ashare_research.reproducibility.artifacts import compare_artifact_runs, verify_artifacts

    left = tmp_path / "a" / "synthetic"
    right = tmp_path / "b" / "synthetic"
    assert verify_artifacts(left)["status"] == "pass"
    assert verify_artifacts(right)["status"] == "pass"
    assert compare_artifact_runs(left, right)["status"] == "pass"


def test_observation_availability_and_ids_are_contract_fields(tmp_path: Path) -> None:
    result = run_test_capsule(tmp_path, "synthetic")
    record = copy.deepcopy(result["before"][0])
    assert record["available_at"] == record["conclusion_available_at"]
    assert record["active_event_ids"]
    assert "search_register_id" in record
    record["available_at"] = "2025-01-04T00:00:00+00:00"
    with pytest.raises(RiskVetoContractError, match="available_at must equal"):
        validate_observation(record)
