from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ashare_research.pit_valuation.pe_independent_cycle_validation_preflight import (  # noqa: E402
    ABOVE,
    NOT_MATURED,
    add_fiscal_quarters,
    assert_preflight_has_no_future_values,
    build_outcome_readiness,
    derive_episode_inventory,
)


def load(name: str) -> dict:
    return json.loads((ROOT / name).read_text(encoding="utf-8"))


@pytest.fixture
def decision():
    return load("reports/m2_stage2k1r4f4a_decision.json")


@pytest.fixture
def episodes():
    return load("reports/petrochina_pe_independent_cycle_episode_inventory_v1.json")


@pytest.fixture
def readiness():
    return load("reports/petrochina_pe_independent_cycle_outcome_readiness_v1.json")


def test_upstream_r4f4_corrected_semantics():
    upstream = load("reports/m2_stage2k1r4f4_decision.json")
    assert upstream["verdict"] == "CONDITIONAL PASS"
    assert upstream["evidence"]["3y_series_trade_days"] == 728
    assert upstream["evidence"]["mechanical_denominator_guard"] == "CONFIRMED"
    assert upstream["gates"]["mechanical_relation_excluded_as_empirical_evidence"]
    assert not upstream["gates"]["independent_cycle_context_evidence_present"]
    assert not upstream["gates"]["cycle_guard_empirically_validated"]
    assert not upstream["gates"]["normalized_earnings_mid_cycle_validated"]
    assert not upstream["evidence"]["pe_numeric_scoring_authorized"]


def test_option_matrix_all_required_dispositions():
    matrix = load("reports/petrochina_pe_independent_cycle_validation_option_matrix_v1.json")
    got = {row["id"]: row["status"] for row in matrix["options"]}
    assert got == {
        "A": "REJECT_AS_INDEPENDENT_EVIDENCE",
        "B": "SELECT_PRIMARY",
        "C": "SELECT_AS_PRIMARY_FALSIFICATION_METRIC",
        "D": "SELECT_SECONDARY_CONTEXT_CANDIDATE",
        "E": "DIAGNOSTIC_ONLY",
        "F": "DEFERRED",
        "G": "REJECT_OUT_OF_SCOPE",
        "H": "REJECT",
    }
    assert matrix["future_outcomes_inspected_for_selection"] is False


def test_episode_is_machine_derived_contiguous_regime(episodes):
    upstream = load("reports/petrochina_pe_3y_cycle_guard_direction_audit_v1.json")
    assert episodes["candidate_contiguous_regimes"] == upstream["above_normalized_segments"] == 1
    assert episodes["valid_onset_anchored_episodes"] == 0
    assert episodes["episodes"][0]["raw_state_count"] == 11
    assert episodes["daily_rows_are_independent_episodes"] is False
    assert episodes["no_pe_value_used"] and episodes["no_future_fact_used"]


def test_left_censored_regime_not_claimed_as_onset(episodes):
    assert episodes["observed_onset_count"] == 0
    assert episodes["observed_episode_onsets"] == 0
    assert episodes["left_censored_episode_count"] == 1
    assert episodes["episodes"][0]["onset_observed"] is False
    regime = episodes["episodes"][0]
    assert regime["first_observed_trade_date"] == "2023-07-31"
    assert regime["true_onset_trade_date"] == "UNKNOWN_OUTSIDE_3Y_WINDOW"
    assert regime["first_observed_trade_date"] != regime["true_onset_trade_date"]


def test_synthetic_sign_transition_creates_one_episode():
    ledger = {
        "segments": [
            {
                "direction": "CURRENT_EPS_BELOW_NORMALIZED_PROXY",
                "raw_ttm_denominator_state_id": "r0",
                "normalized_denominator_state_id": "n0",
                "start_trade_date": "2020-01-01",
                "end_trade_date": "2020-01-01",
                "current_ttm_eps_decimal": "1",
                "normalized_eps_decimal": "2",
            },
            {
                "direction": ABOVE,
                "raw_ttm_denominator_state_id": "r1",
                "normalized_denominator_state_id": "n1",
                "start_trade_date": "2020-05-01",
                "end_trade_date": "2020-08-01",
                "current_ttm_eps_decimal": "2",
                "normalized_eps_decimal": "1",
            },
            {
                "direction": ABOVE,
                "raw_ttm_denominator_state_id": "r2",
                "normalized_denominator_state_id": "n2",
                "start_trade_date": "2020-08-02",
                "end_trade_date": "2020-10-01",
                "current_ttm_eps_decimal": "3",
                "normalized_eps_decimal": "1",
            },
        ]
    }
    timeline = {
        "timelines": {
            "PE_A_TTM": [
                {
                    "financial_state_id": "r1",
                    "period_end": "2020-03-31",
                    "available_at_max": "2020-04-30",
                    "effective_from": "2020-05-01",
                }
            ]
        }
    }
    norm = {
        "n1": {
            "current_bvps_decimal": "10",
            "selected_five_roe_years": ["2015"],
            "anchor_fact_ids": ["f"],
            "anchor_available_at_effective_identities": [],
        }
    }
    result = derive_episode_inventory(ledger, timeline, norm)
    assert result["episode_count"] == 1
    assert result["episodes"][0]["onset_observed"] is True
    assert result["episodes"][0]["raw_state_count"] == 2
    assert result["episodes"][0]["anchor_status"] == "IDENTIFIED_AT_OBSERVED_ONSET"
    assert result["episodes"][0]["anchor_trade_date"] == "2020-05-01"


def test_left_censored_regime_cannot_create_formal_anchor(episodes):
    regime = episodes["episodes"][0]
    assert regime["anchor_status"] == "NOT_IDENTIFIABLE_LEFT_CENSORED"
    assert regime["left_censored_episode_anchor_policy"] == (
        "PROHIBIT_FIRST_OBSERVED_DATE_SUBSTITUTION"
    )
    for key in (
        "episode_id",
        "anchor_trade_date",
        "anchor_raw_financial_state_id",
        "anchor_normalized_denominator_state_id",
        "anchor_raw_period_end",
        "anchor_current_ttm_eps",
        "anchor_normalized_eps",
        "anchor_fact_ids",
    ):
        assert regime[key] is None
    assert regime["future_references_present"] is False
    assert not any(
        key.startswith("future_") and key != "future_references_present" for key in regime
    )


def test_exact_fiscal_horizons_only():
    assert add_fiscal_quarters("2023-03-31", 4) == "2024-03-31"
    assert add_fiscal_quarters("2023-03-31", 8) == "2025-03-31"
    with pytest.raises(ValueError):
        add_fiscal_quarters("2023-03-31", 1)


def test_readiness_is_metadata_only(readiness):
    assert readiness["read_mode"] == "METADATA_ONLY_READINESS"
    assert readiness["future_eps_values_read"] is False
    assert readiness["partial_quarter_proxy"] is False
    assert readiness["forecast_fallback"] is False
    assert readiness["candidate_regimes_with_4q_target_metadata_available"] == 1
    assert readiness["candidate_regimes_with_8q_target_metadata_available"] == 1
    assert readiness["protocol_valid_mature_4q_episode_count"] == 0
    assert readiness["protocol_valid_mature_8q_episode_count"] == 0
    assert readiness["current_3y_validation_executable"] is False
    assert (
        readiness["current_3y_validation_block_reason"] == "NO_OBSERVED_EPISODE_ONSET_LEFT_CENSORED"
    )
    assert_preflight_has_no_future_values(readiness)


def test_missing_target_is_not_matured_not_zero(episodes):
    empty = {"timelines": {"PE_A_TTM": []}}
    result = build_outcome_readiness(episodes, empty)
    target = result["existing_financial_state_target_coverage"][0]["horizons"]["4q"]
    assert target["metadata_status"] == NOT_MATURED
    assert target["protocol_valid_maturity"] is False
    assert target["future_financial_state_id"] is None
    assert "future_eps" not in target


def test_future_value_fields_fail_closed():
    with pytest.raises(ValueError):
        assert_preflight_has_no_future_values({"future_eps_decimal": "0.9"})
    with pytest.raises(ValueError):
        assert_preflight_has_no_future_values({"value_decimal": "1"})


def test_future_metadata_cannot_change_anchor_ledger(episodes):
    before = json.dumps(episodes, sort_keys=True, separators=(",", ":"))
    timeline = load("reports/petrochina_pit_financial_state_timeline_v2.json")
    timeline["timelines"]["PE_A_TTM"].append(
        {
            "financial_state_id": "future",
            "period_end": "2099-12-31",
            "status": "computed",
            "available_at_max": "2100-01-01",
            "effective_from": "2100-01-02",
            "input_fact_ids": ["future"],
        }
    )
    _ = build_outcome_readiness(episodes, timeline)
    after = json.dumps(episodes, sort_keys=True, separators=(",", ":"))
    assert before == after


def test_5y_justification_is_identification_based():
    report = load("reports/petrochina_pe_5y_backfill_identification_justification_v1.json")
    assert report["remaining_logical_gaps"] == 4
    assert report["remaining_logical_facts"] == [
        {"period_end": "2015-12-31", "concept": "parent_equity"},
        {"period_end": "2016-12-31", "concept": "parent_equity"},
        {"period_end": "2016-12-31", "concept": "parent_net_profit"},
        {"period_end": "2017-12-31", "concept": "parent_net_profit"},
    ]
    assert report["status"] == "ACQUISITION_JUSTIFIED_FOR_INDEPENDENT_VALIDATION"
    assert report["primary_justification"] == (
        "RECOVER_LEFT_CENSORED_EPISODE_ONSET_IF_PRESENT_WITHIN_5Y_WINDOW"
    )
    assert report["secondary_justification"] == (
        "EXPAND_OPPORTUNITY_FOR_ADDITIONAL_INDEPENDENT_EPISODES"
    )
    assert not any(report["backfill_guarantees"].values())
    assert report["automatic_extension_beyond_5y"] == "PROHIBITED"
    assert report["stop_expansion_result_if_valid_episodes_lt_2"] == (
        "INDEPENDENT_VALIDATION_NOT_TESTABLE_WITH_FROZEN_5Y_HISTORY"
    )
    assert report["stop_expansion_action"] == "STOP_FOR_NORTH_STAR_REVIEW"
    assert report["acquisition_performed"] is False
    assert report["percentile_rationale_used"] is False


def test_brent_is_feasibility_only():
    report = load("reports/petrochina_pe_external_cycle_context_source_preflight_v1.json")
    assert report["candidate"] == "US EIA Europe Brent Spot Price FOB"
    assert report["downloaded_values"] is False
    assert report["formal_series_used"] is False
    assert report["standalone_scoring_unlock_gate"] is False
    assert report["brent_price_threshold"] is None
    assert "SECONDARY_SOURCE_FEASIBLE" in report["status"]
    assert "PIT_PUBLICATION_CONTRACT_UNRESOLVED" in report["status"]


def test_decision_gate_and_scoring_boundaries(decision):
    assert (
        decision["decision"]
        == "PE_INDEPENDENT_CYCLE_VALIDATION_PROTOCOL_FROZEN_5Y_BACKFILL_REQUIRED"
    )
    assert decision["verdict"] == "PASS"
    assert decision["pe_numeric_scoring"] == "BLOCKED_UNCHANGED"
    assert decision["overall_score"] == "PROHIBITED"
    assert decision["normalized_earnings_mid_cycle_validity"] == "NOT_YET_VALIDATED"
    assert decision["cycle_guard_empirical_validation"] == "NOT_ESTABLISHED"
    assert decision["no_outcome_validation_executed"]
    evidence = decision["evidence"]
    assert evidence["3y_valid_onset_anchored_episodes"] == 0
    assert evidence["candidate_regimes_with_4q_target_metadata_available"] == 1
    assert evidence["protocol_valid_mature_4q_episode_count"] == 0
    assert evidence["current_3y_validation_executable"] is False


def test_contract_has_frozen_primary_and_benchmark():
    contract = load("config/pe_independent_cycle_validation_contract_v1.json")
    assert contract["primary_method"] == "FUTURE_REALIZED_EARNINGS_REVERSION_TO_FROZEN_ANCHOR"
    assert contract["horizons"]["primary"] == "+4_FISCAL_QUARTERS"
    assert contract["horizons"]["secondary"] == "+8_FISCAL_QUARTERS"
    assert (
        contract["metrics"]["benchmark"]
        == "FROZEN_NORMALIZED_ANCHOR_VS_CURRENT_EARNINGS_PERSISTENCE"
    )
    assert contract["anchor_freeze"]["future_normalized_eps_may_replace_anchor"] is False
    assert contract["anchor_freeze"]["left_censored_episode_anchor_policy"] == (
        "PROHIBIT_FIRST_OBSERVED_DATE_SUBSTITUTION"
    )
    assert contract["boundaries"]["automatic_history_extension_beyond_5y"] == "PROHIBITED"


def test_cli_verify():
    result = subprocess.run(
        [
            sys.executable,
            "src/ashare_research/tools/m2_stage2k1r4f4a_independent_cycle_validation_preflight.py",
            "verify",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_protected_artifact_hashes_unchanged():
    expected = {
        "config/value_dimension_scoring_registry_v2.json": (
            "9e43b1a296b6acd85b7b12ef2ee6b3f645b1252978e4a60fdb287d1ca279317d"
        ),
        "config/value_dimension_scoring_policy_v2.json": (
            "4c35a5363ba352433f807079dfc2af8bf7ddbf35f6f36d168f6dd06cbc89a3c8"
        ),
        "config/value_dimension_scoring_shadow_inputs_v2.json": (
            "63cf68add74b1518b277a2f2e3814fe5014eba47ea24a074f568e140ccc4dec2"
        ),
        "reports/petrochina_score_input_capsule_v5.json": (
            "ea6f50a41c98a428d02fded48787917ad68e24c334c3d9ab4b66dbb49a00418c"
        ),
        "reports/petrochina_dimension_scoring_shadow_v6.json": (
            "a3c14ad9c4b5900ab8492b9f0e79608683fa66363d43e0c1c268f025356068fc"
        ),
        "reports/petrochina_dimension_scoring_sensitivity_v8.json": (
            "d6c1750456cada19ca53fa18eff25c17bde692946c26d9651f36eeeb6e43e559"
        ),
    }
    for name, digest in expected.items():
        canonical = subprocess.check_output(["git", "show", f"HEAD:{name}"], cwd=ROOT)
        assert hashlib.sha256(canonical).hexdigest() == digest
    db = ROOT / "data" / "research.duckdb"
    assert hashlib.sha256(db.read_bytes()).hexdigest() == (
        "4a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6"
    )


def test_no_artifact_manifest_or_production_result():
    assert not (ROOT / "reports/m2_stage2k1r4f4a_artifact_manifest.json").exists()
    assert not (ROOT / "reports/petrochina_pe_independent_cycle_outcomes_v1.json").exists()


def test_no_protected_source_changes_from_this_stage():
    changed = subprocess.run(
        ["git", "diff", "--name-only"], cwd=ROOT, capture_output=True, text=True, check=True
    ).stdout
    for name in (
        "config/value_dimension_scoring_registry_v2.json",
        "config/value_dimension_scoring_policy_v2.json",
        "config/value_dimension_scoring_shadow_inputs_v2.json",
        "reports/petrochina_score_input_capsule_v5.json",
        "reports/petrochina_dimension_scoring_shadow_v6.json",
        "reports/petrochina_dimension_scoring_sensitivity_v8.json",
    ):
        assert name not in changed
