"""Stage 2H.1R fixed-universe and canonical-profile contract tests."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from ashare_research.risk_veto.contracts import (
    RISK_IDS,
    RiskVetoContractError,
    _event_identity_payload,
    evaluate_risk_universe_as_of,
    stable_id,
    validate_event_evidence_lineage,
    validate_risk_universe_evaluation,
)
from ashare_research.tools.petrochina_risk_veto_vertical_slice import (
    _input_ledgers,
    run_test_capsule,
)

ROOT = Path(__file__).resolve().parents[1]


def test_historical_and_early_evaluations_keep_all_eight_slots() -> None:
    evidence, events, searches, normalizations = _input_ledgers()
    historical = evaluate_risk_universe_as_of(
        symbol="601857.SH",
        as_of_date="2025-04-01",
        events=events,
        search_registers=searches,
        evidence=evidence,
        normalizations=normalizations,
    )
    early = evaluate_risk_universe_as_of(
        symbol="601857.SH",
        as_of_date="2021-01-01",
        events=events,
        search_registers=searches,
        evidence=evidence,
        normalizations=normalizations,
    )
    assert len(historical["slots"]) == len(early["slots"]) == 8
    assert len(historical["observations"]) == 7
    assert len(early["observations"]) == 0
    missing = next(
        item
        for item in historical["slots"]
        if item["risk_id"] == "formal_regulatory_investigation_or_major_discipline"
    )
    assert missing["observation_emitted"] is False
    assert missing["observation_id"] is None
    assert "no PIT-visible input" in " ".join(missing["missing_reasons"])
    assert all(item["observation_emitted"] is False for item in early["slots"])
    validate_risk_universe_evaluation(historical)
    validate_risk_universe_evaluation(early)


def test_universe_validation_rejects_missing_or_fabricated_slot() -> None:
    evidence, events, searches, normalizations = _input_ledgers()
    record = evaluate_risk_universe_as_of(
        symbol="601857.SH",
        as_of_date="2025-04-01",
        events=events,
        search_registers=searches,
        evidence=evidence,
        normalizations=normalizations,
    )
    tampered = copy.deepcopy(record)
    tampered["slots"] = tampered["slots"][:-1]
    with pytest.raises(RiskVetoContractError, match="exactly eight"):
        validate_risk_universe_evaluation(tampered)
    tampered = copy.deepcopy(record)
    slot = next(item for item in tampered["slots"] if not item["observation_emitted"])
    slot["observation_id"] = "fabricated-observation"
    with pytest.raises(RiskVetoContractError, match="fabricated"):
        validate_risk_universe_evaluation(tampered)


def test_event_input_and_supplemental_evidence_are_derived_and_disjoint() -> None:
    evidence, events, _, normalizations = _input_ledgers()
    target = next(item for item in events if item["risk_id"] == "modified_audit_opinion")
    assert target["input_evidence_ids"]
    assert all(item.startswith("pc-") and "issuer" in item for item in target["input_evidence_ids"])
    assert all("exchange" in item for item in target["supplemental_evidence_ids"])
    assert target["all_evidence_ids"] == sorted(
        set(target["input_evidence_ids"]) | set(target["supplemental_evidence_ids"])
    )
    assert target["input_source_types"] == ["issuer_official"]
    assert target["supplemental_source_types"] == ["exchange_official"]
    original_hash = target["input_lineage_hash"]
    without_supplemental = copy.deepcopy(target)
    without_supplemental["supplemental_evidence_ids"] = []
    without_supplemental["supplemental_source_types"] = []
    without_supplemental["all_evidence_ids"] = list(without_supplemental["input_evidence_ids"])
    evidence_by_id = {item["source_evidence_id"]: item for item in evidence}
    without_supplemental["available_at"] = max(
        evidence_by_id[item]["available_at"] for item in without_supplemental["input_evidence_ids"]
    )
    without_supplemental["event_id"] = stable_id(
        "risk_event", _event_identity_payload(without_supplemental)
    )
    lineage = validate_event_evidence_lineage(without_supplemental, evidence, normalizations)
    assert lineage["input_lineage_hash"] == original_hash
    assert without_supplemental["inputs"] == target["inputs"]
    assert without_supplemental["event_id"] != target["event_id"]
    overlapping = copy.deepcopy(target)
    overlapping["supplemental_evidence_ids"].append(target["input_evidence_ids"][0])
    with pytest.raises(RiskVetoContractError, match="overlap"):
        validate_event_evidence_lineage(overlapping, evidence, normalizations)


def test_canonical_profile_has_one_current_risk_source() -> None:
    profile = json.loads(
        (ROOT / "reports/petrochina_value_profile.json").read_text(encoding="utf-8")
    )
    assert "risk_veto_checks" not in profile
    assert "stage2h_risk_veto" not in profile
    assert len(profile["technical_integrity_checks"]) == 4
    current = profile["current_risk_veto_profile"]
    assert current["expected_risk_count"] == 8
    assert len(current["risk_slots"]) == 8
    assert {item["risk_id"] for item in current["risk_slots"]} == set(RISK_IDS)
    assert profile["legacy_risk_veto_checks"]
    assert all(
        item["legacy"] is True
        and item["current"] is False
        and item["do_not_use_for_current_profile"] is True
        for item in profile["legacy_risk_veto_checks"]
    )
    assert not any(
        item["risk_id"] in {"governance_risk", "audit_risk", "related_party_risk"}
        for item in current["risk_slots"]
    )


def test_json_markdown_and_one_page_expose_the_same_eight_risk_ids() -> None:
    profile = json.loads(
        (ROOT / "reports/petrochina_value_profile.json").read_text(encoding="utf-8")
    )
    risk_ids = [item["risk_id"] for item in profile["current_risk_veto_profile"]["risk_slots"]]
    for relative in (
        "reports/petrochina_value_profile_2021_2026.md",
        "reports/petrochina_value_profile_one_page.md",
        "reports/petrochina_risk_veto_profile_2021_2026.md",
    ):
        text = (ROOT / relative).read_text(encoding="utf-8")
        assert "current_risk_veto_profile" in text or "Canonical current" in text
        assert all(risk_id in text for risk_id in risk_ids)


def test_synthetic_capsule_publishes_v3_universe_and_reproducible_correction(
    tmp_path: Path,
) -> None:
    result = run_test_capsule(tmp_path, "synthetic")
    assert result["status"] == "pass"
    before = json.loads(
        (tmp_path / "synthetic" / "synthetic_risk_universe_before.json").read_text(
            encoding="utf-8"
        )
    )
    after = json.loads(
        (tmp_path / "synthetic" / "synthetic_risk_universe_after.json").read_text(
            encoding="utf-8"
        )
    )
    assert before["contract"] == after["contract"] == "risk_universe_evaluation_v1"
    assert len(before["slots"]) == len(after["slots"]) == 8
    assert len(before["observations"]) == len(after["observations"]) == 8
    assert all(
        item["contract"] == "risk_veto_observation_v3" for item in before["observations"]
    )
