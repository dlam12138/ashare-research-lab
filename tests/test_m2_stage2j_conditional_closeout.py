from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

from ashare_research.tools import m2_stage2j_closeout as stage2j

ROOT = Path(__file__).parents[1]


def _load(path: str):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def test_completion_matrix_contract_passes_and_has_every_module_once():
    assert stage2j.validate_completion_matrix() == []
    matrix = _load("reports/m2_value_assessment_completion_matrix.json")
    modules = matrix["modules"]
    ids = [module["module_id"] for module in modules]
    assert set(ids) == stage2j.REQUIRED_MODULE_IDS
    assert len(ids) == len(set(ids)) == 15
    assert set(matrix["allowed_statuses"]) == stage2j.ALLOWED_MODULE_STATUSES
    assert matrix["north_star_decision"] == "M2_SCORING_ADDENDUM_REOPENED"
    assert matrix["m3_next_step"] == "M3_NORTH_STAR_PREFLIGHT_ALLOWED"


def test_completion_matrix_keeps_roic_scoring_and_m3_fail_closed():
    matrix = _load("reports/m2_value_assessment_completion_matrix.json")
    by_id = {module["module_id"]: module for module in matrix["modules"]}
    assert (
        by_id["roic"]["status"]
        == "not_computable_under_strict_evidence_contract"
    )
    assert set(by_id["roic"]["evidence_gap_ids"]) == stage2j.ROIC_GAP_IDS
    assert by_id["roic"]["score_eligible"] is False
    assert by_id["scoring"]["status"] == "scoring_addendum_reopened"
    assert by_id["market_mechanism"]["status"] == "not_started"
    assert all(module["score_eligible"] is False for module in matrix["modules"])


def test_gap_ledger_recomputes_all_source_counts_without_duplicates():
    assert stage2j.validate_gap_ledger() == []
    ledger = _load("reports/m2_explicit_gap_ledger.json")
    source = stage2j._source_gap_keys()
    assert ledger["count_contract"]["source_counts"] == {
        stage: len(keys) for stage, keys in source.items()
    }
    assert ledger["count_contract"]["current_gap_count"] == sum(
        len(keys) for keys in source.values()
    )
    ids = [gap["gap_id"] for gap in ledger["gaps"]]
    assert len(ids) == len(set(ids)) == 18
    assert all(gap["supersession_status"] == "current" for gap in ledger["gaps"])


def test_gap_ledger_preserves_source_records_and_prohibited_fallbacks():
    ledger = _load("reports/m2_explicit_gap_ledger.json")
    gaps = ledger["gaps"]
    assert sum(gap["originating_stage"] == "M2_STAGE_2F1" for gap in gaps) == 9
    assert sum(gap["originating_stage"] == "M2_STAGE_2H" for gap in gaps) == 2
    assert sum(gap["originating_stage"] == "M2_STAGE_2I2R" for gap in gaps) == 7
    assert all(gap["status"] == "current_explicit_gap" for gap in gaps)
    assert all(gap["blocks_scoring"] is True for gap in gaps)
    assert all(gap["blocks_m2_closeout"] is False for gap in gaps)
    assert all(gap["blocks_m3"] is False for gap in gaps)
    assert all(gap["prohibited_fallback"] for gap in gaps)
    assert {
        gap["recoverability_classification"] for gap in gaps
    }.issubset(stage2j.RECOVERABILITY_STATUSES)


def test_source_gap_removal_or_resolution_cannot_silently_pass(monkeypatch):
    original = stage2j._load

    def forged(path: str):
        result = original(path)
        if path == "events/dividend_source_evidence_2021_2026.json":
            result = copy.deepcopy(result)
            gap = next(
                entry
                for entry in result["entries"]
                if entry["source_evidence_id"] == "2021-interim-exchange"
            )
            gap["retrieval_status"] = "retrieved"
        return result

    monkeypatch.setattr(stage2j, "_load", forged)
    assert "gap_source_mismatch:stage2f" in stage2j.validate_gap_ledger()


def test_roic_profile_status_has_no_numeric_branch_and_preserves_roe_roa():
    assert stage2j.validate_profile() == []
    profile = _load("reports/petrochina_value_profile.json")
    capital = profile["capital_return"]
    roic = capital["roic"]
    assert capital["roe"]["status"] == "trusted_existing_results_unchanged"
    assert capital["roa"]["status"] == "trusted_existing_results_unchanged"
    assert roic["status"] == "not_computable_under_strict_evidence_contract"
    assert roic["shadow_status"] == "not_run"
    assert roic["production_metric_created"] is False
    assert roic["score_eligible"] is False
    assert set(roic["missing_gap_ids"]) == stage2j.ROIC_GAP_IDS
    assert not {
        "value",
        "value_decimal",
        "numeric_value",
        "estimate",
        "proxy_value",
    } & set(roic)


def test_profile_has_no_score_rating_trade_or_recommendation_keys():
    profile = _load("reports/petrochina_value_profile.json")
    assert not stage2j.FORBIDDEN_PROFILE_KEYS & stage2j._walk_keys(profile)
    assert profile["score_eligible"] is False


def test_roic_decision_record_freezes_evidence_limitation_and_reopening():
    assert stage2j.validate_decision() == []
    text = (
        ROOT / "docs/decisions/ADR-ROIC-001-strict-evidence-non-computability.md"
    ).read_text(encoding="utf-8")
    assert "ROIC_NOT_COMPUTABLE_UNDER_STRICT_EVIDENCE_CONTRACT" in text
    assert "tax-rate proxy" in text.lower()
    assert "Associate/JV residual allocation" in text
    assert "unsupported non-operating-asset deduction" in text.lower()
    assert "poor capital returns" in " ".join(text.lower().split())
    assert "third-party terminal" in text


def test_north_star_review_has_four_options_seven_gaps_and_no_numeric_weighting():
    text = (ROOT / "docs/post_roic_north_star_review.md").read_text(
        encoding="utf-8"
    )
    for option in (
        "CONTINUE_ROIC_OFFICIAL_SOURCE_RESEARCH",
        "RELAX_ROIC_METHOD_AND_USE_PROXIES",
        "FREEZE_ROIC_NOT_COMPUTABLE_AND_CONDITIONALLY_CLOSE_M2",
        "BLOCK_M2_INDEFINITELY_UNTIL_ROIC_EXISTS",
    ):
        assert option in text
    assert "Decision: `M2_CONDITIONAL_CLOSEOUT_ALLOWED`" in text
    assert all(gap_id in text for gap_id in stage2j.ROIC_GAP_IDS)
    assert "There is no numeric weighting" in text


def test_closeout_wording_and_scoring_boundary_are_exact():
    # Immutable Stage 2J packet artifacts keep the historical closeout wording.
    immutable = (
        "acceptance/m2_value_assessment_mvp_conditional_closeout.md",
        "reports/m2_stage2j_closeout_summary.md",
    )
    for path in immutable:
        text = (ROOT / path).read_text(encoding="utf-8")
        assert "Milestone 2: CONDITIONALLY CLOSED WITH EXPLICIT EVIDENCE GAPS" in text
    # The protected roadmap keeps Stage 2K reopening history; README is current.
    roadmap = (ROOT / "docs/value_fact_coverage_roadmap.md").read_text(encoding="utf-8")
    assert "Milestone 2: CONDITIONALLY CLOSED; SCORING ADDENDUM REOPENED" in roadmap
    current = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "Milestone 2: CONDITIONALLY CLOSED; SCORING ADDENDUM CONDITIONALLY CLOSED" in current
    assert "PE_NUMERIC_SCORING_DEFERRED_FROZEN_5Y_VALIDATION_NOT_TESTABLE" in current
    assert "M3 Stage 3A research contracts are frozen" in current
    assert "Stage 3B completed" in current
    assert "fail-closed" in current
    assert "Stage 3B-R1 primary-proxy resolution is current" in current
    assert "No real mechanism inference" in current
    packet = (ROOT / "reports/m2_stage2j_closeout_summary.md").read_text(
        encoding="utf-8"
    )
    assert "SCORING_DEFERRED_BY_DESIGN" in packet
    assert "Market mechanism: NOT STARTED" in packet
    assert "Next-stage implementation: NOT STARTED" in packet


def test_stage2j_manifest_recomputes_every_canonical_text_artifact():
    assert stage2j.verify_artifact_manifest() == []
    manifest = _load("reports/m2_stage2j_artifact_manifest.json")
    assert manifest["north_star_decision"] == "M2_SCORING_ADDENDUM_REOPENED"
    for item in manifest["files"]:
        path = ROOT / item["logical_path"]
        payload = path.read_text(encoding="utf-8").replace("\r\n", "\n").encode()
        assert len(payload) == item["byte_size"]
        assert hashlib.sha256(payload).hexdigest() == item["sha256"]


def test_clean_clone_contract_has_no_network_default_db_or_absolute_paths():
    source = (
        ROOT / "src/ashare_research/tools/m2_stage2j_closeout.py"
    ).read_text(encoding="utf-8")
    for forbidden in (
        "requests",
        "httpx",
        "urllib",
        "socket",
        "data/research.duckdb",
        "D:\\\\",
        "/home/",
        "/tmp/",
    ):
        assert forbidden not in source
    manifest = _load("reports/m2_stage2j_artifact_manifest.json")
    assert all(not Path(item["logical_path"]).is_absolute() for item in manifest["files"])


def test_combined_contract_verification_passes():
    result = stage2j.verify_contracts()
    assert result["status"] == "pass", result["errors"]
    assert result["north_star_decision"] == "M2_SCORING_ADDENDUM_REOPENED"
