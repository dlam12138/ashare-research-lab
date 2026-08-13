from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ashare_research.pit_valuation.pe_5y_historical_annual_backfill import (  # noqa: E402
    TARGETS,
    artifact_digest_map,
    build_decision,
    canonical_concept,
    validate_target_dependencies,
)
from ashare_research.pit_valuation.pe_independent_cycle_validation_preflight import (  # noqa: E402
    assert_preflight_has_no_future_values,
)


def load(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


@pytest.fixture
def facts() -> list[dict]:
    return load("reports/petrochina_pe_5y_historical_backfill_reported_fact_bundle_v1.json")[
        "facts"
    ]


def test_upstream_authorizes_only_exact_remaining_four_cells():
    upstream = load("reports/m2_stage2k1r4f4a_decision.json")
    gaps = load("reports/petrochina_pe_5y_backfill_identification_justification_v1.json")
    assert upstream["decision"] == (
        "PE_INDEPENDENT_CYCLE_VALIDATION_PROTOCOL_FROZEN_5Y_BACKFILL_REQUIRED"
    )
    assert gaps["remaining_logical_gaps"] == 4
    assert gaps["automatic_extension_beyond_5y"] == "PROHIBITED"
    assert gaps["acquisition_performed"] is False


def test_target_contract_is_exact_and_canonical():
    contract = load("config/pe_5y_independent_cycle_backfill_contract_v1.json")
    check = validate_target_dependencies(contract["target_logical_cells"])
    assert check["status"] == "PASS"
    assert check["target_logical_cell_count"] == 4
    assert not check["missing"] and not check["extra"]
    assert {(r["period_end"], r["concept_id"]) for r in contract["target_logical_cells"]} == set(
        TARGETS
    )


def test_planning_aliases_never_become_fact_concepts(facts):
    assert canonical_concept("parent_equity") == "equity_attributable_to_parent"
    assert canonical_concept("parent_net_profit") == "net_profit_attributable_to_parent"
    with pytest.raises(ValueError):
        canonical_concept("equity")
    assert not {"parent_equity", "parent_net_profit"} & {f["concept_id"] for f in facts}


def test_official_source_metadata_and_bounded_scan():
    evidence = load("config/pe_5y_historical_backfill_source_evidence_v1.json")
    entries = evidence["entries"]
    assert evidence["required_start"] == "2016-03-24"
    assert evidence["automatic_2014_or_earlier_scan"] == "PROHIBITED"
    assert {r["fiscal_year"] for r in entries} == set(range(2015, 2021))
    assert all(r["source_role"] == "exchange_official" for r in entries)
    assert all(r["document_url"].startswith("https://static.sse.com.cn/") for r in entries)
    assert entries[0]["announcement_date"] == "2016-03-24"
    assert entries[1]["announcement_date"] == "2017-03-31"


def test_cache_registry_pins_all_six_official_objects():
    registry = load("config/pe_5y_historical_backfill_cache_registry_v1.json")
    objects = registry["objects"]
    assert len(objects) == 6
    assert len({r["sha256"] for r in objects}) == 6
    assert "c1a6fbffcc210020e672410400646e0c9fe2097f5de43047a24b950ae7930cea" in {
        r["sha256"] for r in objects
    }


def test_extraction_is_four_verified_consolidated_cells():
    extraction = load("reports/petrochina_pe_5y_historical_backfill_extraction_v1.json")
    assert extraction["logical_cell_count"] == extraction["resolved_logical_cell_count"] == 4
    assert extraction["wrong_scope_rejected"]
    assert not extraction["ocr_used"] and not extraction["llm_value_entry_used"]
    assert all(r["scope"] == "CONSOLIDATED" for r in extraction["rows"])
    assert all(
        r["extraction_method"] == "PDF_TEXT_LAYER_PLUS_VISUAL_PAGE_VERIFICATION"
        for r in extraction["rows"]
    )


def test_exact_reported_values_and_contexts(facts):
    actual = {(f["period_end"], f["concept_id"]): f for f in facts}
    assert (
        actual[("2015-12-31", "equity_attributable_to_parent")]["normalized_value"]
        == 1179968000000.0
    )
    assert (
        actual[("2016-12-31", "equity_attributable_to_parent")]["normalized_value"]
        == 1189319000000.0
    )
    assert (
        actual[("2016-12-31", "net_profit_attributable_to_parent")]["normalized_value"]
        == 7900000000.0
    )
    assert (
        actual[("2017-12-31", "net_profit_attributable_to_parent")]["normalized_value"]
        == 22793000000.0
    )
    assert all(f["unit"] == "CNY" and f["source_tier"] == "exchange_official" for f in facts)
    assert all("|consolidated" in f["context_id"] for f in facts)


def test_fact_pit_uses_announcement_and_next_trading_day(facts):
    by_period = {(f["period_end"], f["concept_id"]): f for f in facts}
    f2015 = by_period[("2015-12-31", "equity_attributable_to_parent")]
    f2016 = by_period[("2016-12-31", "equity_attributable_to_parent")]
    assert (f2015["available_at"], f2015["effective_from"]) == ("2016-03-24", "2016-03-25")
    assert (f2016["available_at"], f2016["effective_from"]) == ("2017-03-31", "2017-04-05")
    assert all(f["pit_time_contract_gap"] == "" for f in facts)


def test_lineage_preserves_originals_without_invented_restatements():
    lineage = load("reports/petrochina_pe_5y_historical_backfill_version_lineage_v1.json")
    assert lineage["actual_fact_records"] == 4
    assert lineage["restatement_versions"] == 0
    assert lineage["restatement_ambiguity"] is False
    assert all(
        c["version_count"] == 1 and not c["later_value_overwrite"] for c in lineage["chains"]
    )
    assert all(c["status"] == "RESOLVED_NO_RESTATEMENT" for c in lineage["chains"])


def test_side_by_side_calendar_is_exact_on_protected_overlap():
    report = load("reports/petrochina_pe_5y_historical_calendar_reconciliation_v1.json")
    assert report["old_calendar_unchanged"] and report["status"] == "PASS"
    assert report["old_count"] == report["new_overlap_count"] == 2330
    assert report["missing_dates"] == report["extra_dates"] == 0
    assert report["target_pit_calendar_gaps"] == 0
    assert report["new_calendar_range"]["start"] == "2016-01-04"


def test_roe_reconciliation_is_decimal_exact():
    report = load("reports/petrochina_pe_5y_historical_backfill_reconciliation_v1.json")
    assert report["roe_2016_decimal"] == "0.006668672896107563161406786092"
    assert report["roe_2017_decimal"] == "0.01913624531469271226661618072"
    assert report["roe_2016_match"] and report["roe_2017_match"]
    assert report["disclosed_weighted_average_roe_role"] == "CROSS_CHECK_DIAGNOSTIC_ONLY"


def test_frozen_5y_readiness_is_complete_without_fill():
    readiness = load(
        "reports/petrochina_pe_normalized_earnings_5y_readiness_after_backfill_v1.json"
    )
    assert readiness["window"] == {"start": "2021-08-02", "end": "2026-07-31"}
    assert readiness["5y_gate"] == {
        "required_days": 1211,
        "ready_days": 1211,
        "blocked_days": 0,
        "status": "READY",
    }
    assert readiness["engine"] == "R4F3_NORMALIZED_EARNINGS_READINESS_REUSED"
    assert readiness["no_forward_fill"]
    assert readiness["engine_result"]["no_3y_4y_roe_fallback"]


def test_episode_series_has_no_pe_or_future_outcome_fields():
    series = load("reports/petrochina_pe_5y_normalized_earnings_episode_series_v1.json")
    assert series["trade_day_count"] == series["required_trade_days"] == 1211
    assert series["gap_count"] == 0
    assert series["future_values_present"] is False
    assert series["normalized_pe_percentile_present"] is False
    assert not any("pe_" in key.lower() for row in series["rows"] for key in row)


def test_left_censored_5y_regime_is_not_an_episode_anchor():
    inventory = load("reports/petrochina_pe_independent_cycle_episode_inventory_5y_v1.json")
    assert inventory["candidate_contiguous_regimes"] == 1
    assert inventory["valid_onset_anchored_episodes"] == 0
    assert inventory["left_censored_episode_count"] == 1
    regime = inventory["episodes"][0]
    assert regime["first_observed_trade_date"] == "2021-08-02"
    assert regime["true_onset_trade_date"] == "UNKNOWN_OUTSIDE_5Y_WINDOW"
    assert regime["anchor_status"] == "NOT_IDENTIFIABLE_LEFT_CENSORED"
    assert regime["episode_id"] is None and regime["anchor_trade_date"] is None


def test_outcome_readiness_is_metadata_only_and_not_executable():
    outcome = load("reports/petrochina_pe_independent_cycle_outcome_readiness_5y_v1.json")
    assert outcome["read_mode"] == "METADATA_ONLY_READINESS"
    assert outcome["future_eps_values_read"] is False
    assert outcome["protocol_valid_mature_4q_episode_count"] == 0
    assert outcome["protocol_valid_mature_8q_episode_count"] == 0
    assert outcome["current_5y_validation_executable"] is False
    assert (
        outcome["primary_4q_execution_gate"]
        == "INDEPENDENT_VALIDATION_NOT_TESTABLE_WITH_FROZEN_5Y_HISTORY"
    )
    assert_preflight_has_no_future_values(outcome)


def test_final_stop_rule_and_scoring_boundary():
    decision = load("reports/m2_stage2k1r4f4a1_decision.json")
    assert decision["verdict"] == "PASS"
    assert decision["backfill_trusted"] is True
    assert decision["frozen_5y_readiness"] == "READY"
    assert decision["independent_validation_executable"] is False
    assert decision["decision"].endswith("NOT_TESTABLE_WITH_FROZEN_5Y_HISTORY")
    assert decision["automatic_history_extension_beyond_5y"] == "PROHIBITED"
    assert decision["next_action"] == "STOP_FOR_NORTH_STAR_REVIEW"
    assert decision["stop_action"] == "STOP_FOR_NORTH_STAR_REVIEW"
    assert decision["next_stage"] == "NONE_PENDING_NORTH_STAR_REVIEW"
    assert decision["brent"] == "NOT_ACQUIRED"
    assert decision["pe_numeric_scoring"] == "BLOCKED_UNCHANGED"
    assert decision["valuation_score"] == "NONE"
    assert decision["overall_score"] == "PROHIBITED"
    assert decision["full_cycle_coverage"] == "NOT_PROVEN"
    assert decision["normalized_earnings_mid_cycle_validity"] == "NOT_YET_VALIDATED"
    assert decision["cycle_guard_empirical_validation"] == "NOT_ESTABLISHED"


def test_decision_fails_closed_when_readiness_is_incomplete():
    extraction = {"resolved_logical_cell_count": 4}
    readiness = {"5y_gate": {"ready_days": 1210, "blocked_days": 1}}
    inventory = {"valid_onset_anchored_episodes": 0}
    outcome = {
        "protocol_valid_mature_4q_episode_count": 0,
        "protocol_valid_mature_8q_episode_count": 0,
    }
    result = build_decision(extraction, readiness, inventory, outcome, {"status": "PASS"})
    assert result["decision"] == "PE_5Y_BACKFILL_FACT_GAPS_REMAIN"
    assert result["verdict"] == "CONDITIONAL PASS"


def test_artifact_digest_is_deterministic():
    payloads = {"decision": load("reports/m2_stage2k1r4f4a1_decision.json")}
    assert artifact_digest_map(payloads) == artifact_digest_map(json.loads(json.dumps(payloads)))
    digest = artifact_digest_map(payloads)["decision"]
    assert (
        len(digest) == 64
        and digest
        == hashlib.sha256(
            (json.dumps(payloads["decision"], ensure_ascii=False, indent=1) + "\n").encode("utf-8")
        ).hexdigest()
    )


def test_all_eleven_artifacts_have_offline_deterministic_a_b_encoding():
    paths = [
        "reports/petrochina_pe_5y_historical_backfill_extraction_v1.json",
        "reports/petrochina_pe_5y_historical_backfill_reported_fact_bundle_v1.json",
        "reports/petrochina_pe_5y_historical_backfill_version_lineage_v1.json",
        "reports/petrochina_pe_5y_historical_backfill_overlay_v1.json",
        "reports/petrochina_pe_5y_historical_calendar_reconciliation_v1.json",
        "reports/petrochina_pe_5y_historical_backfill_reconciliation_v1.json",
        "reports/petrochina_pe_normalized_earnings_5y_readiness_after_backfill_v1.json",
        "reports/petrochina_pe_5y_normalized_earnings_episode_series_v1.json",
        "reports/petrochina_pe_independent_cycle_episode_inventory_5y_v1.json",
        "reports/petrochina_pe_independent_cycle_outcome_readiness_5y_v1.json",
        "reports/m2_stage2k1r4f4a1_decision.json",
    ]
    build_a = {
        path: (json.dumps(load(path), ensure_ascii=False, indent=1) + "\n").encode()
        for path in paths
    }
    build_b = {
        path: (json.dumps(load(path), ensure_ascii=False, indent=1) + "\n").encode()
        for path in reversed(paths)
    }
    assert len(build_a) == 11
    assert build_a == build_b


def test_clean_clone_tests_do_not_require_external_inputs():
    source = Path(__file__).read_text(encoding="utf-8")
    forbidden = (
        "tm" + "p/",
        "r4f4a1_official" + "_cache",
        "market" + "_cache",
    )
    assert not any(token in source for token in forbidden)


def test_no_forbidden_new_artifact_names():
    names = [p.name.lower() for p in (ROOT / "reports").glob("*r4f4a1*")]
    assert not any(
        any(token in name for token in ("score", "percentile", "brent", "outcome_value"))
        for name in names
    )
