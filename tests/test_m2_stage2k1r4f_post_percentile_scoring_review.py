"""M2 Stage 2K.1R4F — post-percentile scoring north-star review static tests.

Offline tests that confirm the R4F review/decision contract:
  - the R4E.5 trusted percentile upstream is trusted and identity-verified;
  - the three old metric roles and the legacy 3y-only engine behavior are
    identified;
  - exactly five window options are considered and six-component double
    weighting is rejected;
  - the dual-window single-component model is selected with fixed 0.5/0.5
    Decimal weights;
  - no actual percentile value is used as option-choice rationale;
  - PE numeric scoring is blocked pending a cycle-context guard;
  - PB/PS migration is non-production only;
  - the v1 scoring files are not modified and remain immutable;
  - overall score is prohibited and production scoring is not authorized.

These are static, read-only tests: they never write, never fetch, and never
compute a score.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

GAP_MATRIX_PATH = ROOT / "reports" / "petrochina_valuation_scoring_contract_gap_matrix_v1.json"
OPTION_MATRIX_PATH = ROOT / "reports" / "petrochina_post_percentile_scoring_option_matrix_v1.json"
MIGRATION_PLAN_PATH = ROOT / "reports" / "petrochina_valuation_scoring_migration_plan_v1.json"
DECISION_PATH = ROOT / "reports" / "m2_stage2k1r4f_decision.json"
DOC_PATH = ROOT / "docs" / "post_percentile_scoring_north_star_review.md"
ACCEPTANCE_PATH = ROOT / "acceptance" / (
    "m2_stage2k1r4f_post_percentile_scoring_north_star_review.md"
)

R4E5_DECISION_PATH = ROOT / "reports" / "m2_stage2k1r4e5_decision.json"
R4E5_PROFILE_PATH = ROOT / "reports" / "petrochina_pit_valuation_percentile_profile_v1.json"
REGISTRY_V1_PATH = ROOT / "config" / "value_dimension_scoring_registry_v1.json"
POLICY_V1_PATH = ROOT / "config" / "value_dimension_scoring_policy_v1.json"

# The six actual midrank percentile values are frozen here ONLY as sentinel
# values that must never appear in the option-choice rationale.  They are
# reported for transparency in the north-star doc and are NOT part of the
# decision basis.
EVIDENCE_ONLY_PERCENTILES = {
    "91.964286",  # PE 3y / PS 3y
    "93.270025",  # PE 5y
    "84.958791",  # PB 3y
    "90.957886",  # PB 5y
    "95.169282",  # PS 5y
}

RWINDOW = ("3y", "5y")
RWINDOW_WEIGHTS = {"3y": "0.5", "5y": "0.5"}


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


# ── R4E.5 upstream is trusted ───────────────────────────────────────────────


def test_r4e5_upstream_is_trusted():
    d = _load(R4E5_DECISION_PATH)
    assert d["decision"] == "PIT_VALUATION_PERCENTILE_PROFILE_TRUSTED_NORTH_STAR_REVIEW_REQUIRED"
    assert d["record_count"] == 6
    assert d["oracle_identical"] is True
    assert d["all_windows_ready"] is True
    assert d["non_production"] is True
    assert d["score_eligible"] is False


def test_r4e5_profile_has_six_records_and_dual_windows():
    p = _load(R4E5_PROFILE_PATH)
    assert p["schema"] == "petrochina_pit_valuation_percentile_profile_v1"
    records = p["records"]
    assert len(records) == 6
    windows = {r["window_id"] for r in records}
    assert windows == set(RWINDOW)
    metrics = {r["metric_id"] for r in records}
    assert metrics == {"PE_A_TTM", "PB_A_MRQ", "PS_A_TTM"}


# ── gap matrix: old roles + engine behavior + migration required ────────────


def test_gap_matrix_identifies_three_old_metric_roles():
    g = _load(GAP_MATRIX_PATH)
    roles = {
        gaps["gap_id"]: gaps["old_metric_role"]
        for gaps in g["gaps"]
        if gaps["gap_id"].endswith("_semantic")
    }
    assert roles["va_pe_semantic"] == "a_share_price_to_latest_annual_parent_earnings"
    assert roles["va_pb_semantic"] == "a_share_price_to_latest_year_end_parent_equity"
    assert roles["va_ps_semantic"] == "a_share_price_to_latest_annual_revenue"


def test_gap_matrix_identifies_legacy_3y_only_engine():
    g = _load(GAP_MATRIX_PATH)
    wid = next(x for x in g["gaps"] if x["gap_id"] == "history_windows")
    assert "percentile_3y only" in wid["old_engine_behavior"]
    mid = next(x for x in g["gaps"] if x["gap_id"] == "percentile_methodology")
    assert "legacy self-history percentile" in mid["old_engine"]


def test_gap_matrix_requires_migration_and_keeps_production_blocked():
    g = _load(GAP_MATRIX_PATH)
    statuses = {x["gap_id"]: x["status"] for x in g["gaps"]}
    assert statuses["pe_cycle_handling"] == "NUMERIC_CYCLE_GUARD_GAP"
    assert statuses["production_state"] == "PRODUCTION_BLOCK_RETAINS"


# ── option matrix: five options, six-component rejected, dual-window accepted ─


def test_option_matrix_has_exactly_five_options():
    m = _load(OPTION_MATRIX_PATH)
    assert len(m["options"]) == 5
    assert {o["option_id"] for o in m["options"]} == {"A", "B", "C", "D", "E"}


def test_six_separate_components_rejected_for_double_counting():
    m = _load(OPTION_MATRIX_PATH)
    c = next(o for o in m["options"] if o["option_id"] == "C")
    assert c["verdict"] == "REJECT"
    assert c["axes"]["avoids_double_counting"] == "NO (same metric scored twice per window)"
    assert c["axes"]["preserves_component_topology"] == "NO (six components replace three)"


def test_dual_window_single_component_selected():
    m = _load(OPTION_MATRIX_PATH)
    sel = m["selected_option"]
    assert sel["option_id"] == "D"
    assert sel["name"] == "DUAL_WINDOW_SINGLE_COMPONENT"
    assert sel["aggregation_contract_version"] == "self_history_dual_window_percentile_v1"
    assert sel["window_weights"] == RWINDOW_WEIGHTS


def test_actual_percentiles_not_used_as_option_rationale():
    m = _load(OPTION_MATRIX_PATH)
    blob = json.dumps(m, ensure_ascii=False)
    for pct in EVIDENCE_ONLY_PERCENTILES:
        assert pct not in blob, f"actual percentile {pct} leaked into option-choice rationale"


# ── migration plan: contract + cycle guard + boundaries ─────────────────────


def test_migration_plan_freezes_dual_window_contract():
    p = _load(MIGRATION_PLAN_PATH)
    assert p["current_registry"]["status"] == "IMMUTABLE_HISTORY"
    assert p["target_registry"]["supersedes"] == "value_dimension_scoring_registry_v1"
    assert p["target_policy"]["supersedes"] == "value_dimension_scoring_policy_v1"
    assert p["window_contract"]["contract"] == "self_history_dual_window_percentile_v1"
    assert p["window_contract"]["window_weights"] == RWINDOW_WEIGHTS
    assert p["window_contract"]["expanding_percentile"] == "NOT_REQUIRED"
    assert p["dual_window_aggregation"]["method"] == "EQUAL_WEIGHT_3Y_5Y_DECIMAL_MEAN"


def test_migration_plan_blocks_pe_and_prohibits_outcomes():
    p = _load(MIGRATION_PLAN_PATH)
    assert p["cycle_guard_requirement"]["pe_numeric_scoring"] == "NOT_AUTHORIZED"
    for prohibited in p["explicitly_not_authorized"]:
        assert prohibited in {
            "production_scoring", "overall_score", "rank",
            "recommendation", "buy/sell call", "target_price",
            "peer_percentile", "M3",
        }


def test_migration_plan_retains_weights_and_old_shadow_identity():
    p = _load(MIGRATION_PLAN_PATH)
    weights = p["component_topology_and_weights_retained"]["valuation_attractiveness"]
    assert weights["multiple_position"] == "0.60"
    assert weights["yield_position"] == "0.40"
    assert p["old_shadow_status"]["status"] == "VALID_HISTORICAL_NON_PRODUCTION_RESULT"
    assert p["old_shadow_status"]["valuation_percentile_inputs"] == "SUPERSEDED_FOR_FUTURE_SHADOWS"


# ── decision: block PE, allow PB/PS non-production, prohibit overall ────────


def test_decision_block_pe_and_allow_pbps_non_production():
    d = _load(DECISION_PATH)
    assert d["decision"] == "VALUATION_SCORING_CONTRACT_MIGRATION_REQUIRED"
    assert d["selected_window_contract"] == "DUAL_WINDOW_SINGLE_COMPONENT"
    assert d["selected_aggregation"] == "EQUAL_WEIGHT_3Y_5Y_DECIMAL_MEAN"
    assert d["pe_numeric_scoring"] == "BLOCKED_PENDING_CYCLE_CONTEXT_GUARD"
    assert d["pb_numeric_shadow"] == "ALLOWED_AFTER_V2_MIGRATION"
    assert d["ps_numeric_shadow"] == "ALLOWED_AFTER_V2_MIGRATION"
    assert d["shadow_refresh"] == "ALLOWED_AFTER_V2_MIGRATION"


def test_decision_prohibits_overall_and_production():
    d = _load(DECISION_PATH)
    assert d["production_scoring"] == "NOT_AUTHORIZED"
    assert d["overall_score"] == "PROHIBITED"
    assert d["peer_acquisition"] == "NOT_AUTHORIZED_IN_THIS_STAGE"
    assert d["M3"] == "NOT_STARTED"
    assert d["next_stage"] == (
        "M2_STAGE_2K1R4F1_VALUATION_SCORING_CONTRACT_V2_MIGRATION_AND_SHADOW_REFRESH"
    )


def test_decision_independent_of_actual_percentile_values():
    d = _load(DECISION_PATH)
    assert d["decision_independent_of_actual_percentile_values"] is True
    assert d["method_selection_governance"] == "HARD_RULE_NO_PERCENTILE_PEEKING"


def test_decision_expanding_percentile_deferred_not_required():
    d = _load(DECISION_PATH)
    assert d["expanding_percentile"] == "DEFERRED_NOT_REQUIRED"


def test_decision_semantic_migrations():
    d = _load(DECISION_PATH)
    mig = {m["component_id"]: m for m in d["semantic_migrations"]}
    assert mig["va_pe"] == {
        "component_id": "va_pe",
        "old_role": "a_share_price_to_latest_annual_parent_earnings",
        "old_semantic": "ANNUAL",
        "new_role": "PE_A_TTM",
        "new_semantic": "TTM",
    }
    assert mig["va_pb"]["old_semantic"] == "YEAR_END"
    assert mig["va_pb"]["new_role"] == "PB_A_MRQ"
    assert mig["va_pb"]["new_semantic"] == "MRQ"
    assert mig["va_ps"]["old_semantic"] == "ANNUAL"
    assert mig["va_ps"]["new_role"] == "PS_A_TTM"
    assert mig["va_ps"]["new_semantic"] == "TTM"


def test_decision_pe_block_is_not_zero_and_preserves_topology():
    d = _load(DECISION_PATH)
    assert d["pe_numeric_scoring_authorized"] is False
    assert d["pe_blocked_reason"] == "cycle_context_contract_required"
    # blocked != score=0, and the component/weight topology is preserved.
    assert d["pe_missing_not_zero"] is True
    assert d["pe_component_not_deleted"] is True
    assert d["pe_weight_not_reassigned"] is True
    assert d["registered_weight_topology_unchanged"] is True


# ── v1 scoring files are immutable / unmodified ─────────────────────────────


def test_v1_scoring_files_present_and_immutable_markers():
    reg = _load(REGISTRY_V1_PATH)
    pol = _load(POLICY_V1_PATH)
    assert reg["schema"] == "value_dimension_scoring_registry_v1"
    assert pol["schema"] == "value_dimension_scoring_policy_v1"
    # The v2 files must NOT exist yet (R4F freezes the plan, R4F1 creates them).
    assert not (ROOT / "config" / "value_dimension_scoring_registry_v2.json").exists()
    assert not (ROOT / "config" / "value_dimension_scoring_policy_v2.json").exists()


def test_decision_weights_are_fixed_half_half():
    d = _load(DECISION_PATH)
    assert d["window_weights"] == RWINDOW_WEIGHTS


# ── docs / acceptance reflect the review boundary ───────────────────────────


def test_doc_reports_decision_and_boundary():
    txt = DOC_PATH.read_text(encoding="utf-8")
    assert "VALUATION_SCORING_CONTRACT_MIGRATION_REQUIRED" in txt
    assert "DUAL_WINDOW_SINGLE_COMPONENT" in txt
    assert "NOT_AUTHORIZED" in txt
    assert "choose a method because of PetroChina's current percentile" in txt


def test_acceptance_declares_review_only():
    txt = ACCEPTANCE_PATH.read_text(encoding="utf-8")
    assert "Scoring implementation: NOT STARTED" in txt
    assert "Registry v2:            NOT CREATED" in txt
    assert "Policy v2:              NOT CREATED" in txt
    assert "Shadow refresh:         NOT RUN" in txt
    assert "Sensitivity re-run:     NOT RUN" in txt
    assert "Artifact manifest:      NOT REQUIRED (review-only stage)" in txt
    # After the CI closeout the acceptance records the actual git state.
    assert "COMMITTED + PUSHED" in txt
    assert "Remote CI: **GREEN**" in txt
    assert "PASS — LOCAL CANDIDATE" in txt
