"""M2 Stage 2K.1R4F.1 — valuation scoring contract v2 migration static tests.

Offline tests that confirm the R4F.1 v2 migration contract:
  - registry v2 / policy v2 / shadow inputs v2 exist and supersede v1;
  - va_pe/va_pb/va_ps are re-bound to PE_A_TTM / PB_A_MRQ / PS_A_TTM with the
    dual-window percentile benchmark and Decimal-only aggregation;
  - the PE cycle-context hard gap blocks the valuation dimension numeric score
    (insufficient_evidence_cycle_context, no renormalization);
  - blocked != score=0 and the component/weight topology is preserved;
  - the shadow v6 valuation dimension has no numeric score but PB/PS show
    per-component scores; non-valuation dimensions are unchanged from v5;
  - sensitivity v8 re-runs the full sweep and keeps valuation blocked;
  - production scoring / overall score / rank / recommendation / target price /
    peer / M3 all remain prohibited;
  - the engine v1 default path is unchanged (golden regression);
  - the v2 capture is non-production and no numeric score is served.

These are static, read-only tests: they never write, never fetch, and never
change the v1 contracts.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REG_V2 = ROOT / "config" / "value_dimension_scoring_registry_v2.json"
POL_V2 = ROOT / "config" / "value_dimension_scoring_policy_v2.json"
INP_V2 = ROOT / "config" / "value_dimension_scoring_shadow_inputs_v2.json"
SHADOW_V6 = ROOT / "reports" / "petrochina_dimension_scoring_shadow_v6.json"
SHADOW_V5 = ROOT / "reports" / "petrochina_dimension_scoring_shadow_v5.json"
DIFF = ROOT / "reports" / "petrochina_dimension_scoring_shadow_v5_to_v6_diff.json"
SENS_V8 = ROOT / "reports" / "petrochina_dimension_scoring_sensitivity_v8.json"
DECISION = ROOT / "reports" / "m2_stage2k1r4f1_decision.json"
CAP_V5 = ROOT / "reports" / "petrochina_score_input_capsule_v5.json"
MANIFEST = ROOT / "reports" / "m2_stage2k1r4f1_artifact_manifest.json"
DOC = ROOT / "docs" / "valuation_scoring_contract_v2_migration.md"
ACCEPTANCE = ROOT / "acceptance" / "m2_stage2k1r4f1_valuation_scoring_v2_migration.md"

ENGINE = ROOT / "src" / "ashare_research" / "tools" / "m2_stage2k_scoring_shadow.py"

HARD_GAP = "coverage_gap_cycle_context_required"
DIM_STATUS = "insufficient_evidence_cycle_context"
AGG_CONTRACT = "self_history_dual_window_percentile_v1"
RWINDOW_WEIGHTS = {"3y": "0.5", "5y": "0.5"}


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


# ── v2 contracts exist and supersede v1 ──────────────────────────────────────


def test_v2_contracts_exist_and_supersede_v1():
    reg = _load(REG_V2)
    pol = _load(POL_V2)
    inp = _load(INP_V2)
    assert reg["schema"] == "value_dimension_scoring_registry_v2"
    assert reg["supersedes"] == "value_dimension_scoring_registry_v1"
    assert pol["schema"] == "value_dimension_scoring_policy_v2"
    assert pol["supersedes"] == "value_dimension_scoring_policy_v1"
    assert inp["schema"] == "value_dimension_scoring_shadow_inputs_v2"
    assert inp["supersedes"] == "value_dimension_scoring_shadow_inputs_v1"
    assert pol["non_renormalizable_gap_statuses"] == [HARD_GAP]


def test_v2_valuation_components_migrated_to_ttm_mrq_dual_window():
    reg = _load(REG_V2)
    va = reg["dimensions"]["valuation_attractiveness"]["components"]
    assert va["va_pe"]["metric_role"] == "PE_A_TTM"
    assert va["va_pb"]["metric_role"] == "PB_A_MRQ"
    assert va["va_ps"]["metric_role"] == "PS_A_TTM"
    for cid in ("va_pe", "va_pb", "va_ps"):
        assert va[cid]["benchmark_mode"] == "self_history_dual_window_percentile"
        assert va[cid]["transform_version"] == "dual_window_percentile_direction_v1"
        assert AGG_CONTRACT in va[cid]["accepted_contract_versions"]


def test_v2_dual_window_contract_frozen():
    reg = _load(REG_V2)
    assert reg["dual_window_contract"] == AGG_CONTRACT
    assert reg["window_weights"] == RWINDOW_WEIGHTS


# ── PE cycle-context hard gap ────────────────────────────────────────────────


def test_va_pe_hard_gap_blocks_numeric_scoring():
    reg = _load(REG_V2)
    inp = _load(INP_V2)
    pe = reg["dimensions"]["valuation_attractiveness"]["components"]["va_pe"]
    assert pe["numeric_shadow_status"] == HARD_GAP
    assert pe["pe_numeric_scoring_authorized"] is False
    assert pe["pe_blocked_reason"] == "cycle_context_contract_required"
    assert inp["components"]["va_pe"]["status"] == HARD_GAP
    assert inp["components"]["va_pe"]["pe_numeric_scoring_authorized"] is False


def test_pe_topology_preserved_not_zero_not_deleted():
    reg = _load(REG_V2)
    va = reg["dimensions"]["valuation_attractiveness"]
    pe = va["components"]["va_pe"]
    assert pe["weight"] == 0.20  # weight not reassigned
    assert va["subdimensions"]["multiple_position"]["weight"] == 0.60
    assert va["subdimensions"]["yield_position"]["weight"] == 0.40
    dec = _load(DECISION)
    assert dec["pe_missing_not_zero"] is True
    assert dec["pe_component_not_deleted"] is True
    assert dec["pe_weight_not_reassigned"] is True
    assert dec["registered_weight_topology_unchanged"] is True


# ── shadow v6: valuation blocked, PB/PS per-component, non-valuation preserved ─


def test_shadow_v6_valuation_dimension_blocked():
    s6 = _load(SHADOW_V6)
    va = s6["dimensions"]["valuation_attractiveness"]
    assert va["score"] is None
    assert va["band"] is None
    assert va["status"] == DIM_STATUS
    assert va["coverage_ratio"] == 0.6
    assert va["blocked_component_ids"] == ["va_pe"]
    assert "va_dividend_yield" in va["missing_component_ids"]


def test_shadow_v6_pb_ps_have_per_component_scores_but_no_dimension_score():
    s6 = _load(SHADOW_V6)
    va = s6["dimensions"]["valuation_attractiveness"]
    comps = va["components"]
    assert comps["va_pe"]["status"] == HARD_GAP
    assert comps["va_pe"]["score"] is None
    assert comps["va_pb"]["status"] == "computed_shadow"
    assert comps["va_ps"]["status"] == "computed_shadow"
    assert comps["va_pb"]["score"] is not None
    assert comps["va_ps"]["score"] is not None
    # dimension-level numeric score must remain None despite covered PB/PS.
    assert va["score"] is None


def test_shadow_v6_non_valuation_dimensions_unchanged_from_v5():
    s5 = _load(SHADOW_V5)
    s6 = _load(SHADOW_V6)
    for dim in ("enterprise_quality", "value_realization_capacity"):
        assert s5["dimensions"][dim]["score"] == s6["dimensions"][dim]["score"]
        assert s5["dimensions"][dim]["status"] == s6["dimensions"][dim]["status"]


def test_shadow_v6_is_non_production_and_no_numeric_score_served():
    s6 = _load(SHADOW_V6)
    assert s6["non_production"] is True
    assert s6["overall_score_prohibited"] is True
    assert s6["recommendation_prohibited"] is True
    assert s6["score_eligible"] is False
    # no numeric score anywhere in the valuation dimension
    blob = json.dumps(s6["dimensions"]["valuation_attractiveness"], ensure_ascii=False)
    assert '"score": null' in blob


# ── v5->v6 diff ──────────────────────────────────────────────────────────────


def test_diff_records_only_valuation_changed():
    d = _load(DIFF)
    assert d["dimensions_changed"] == ["valuation_attractiveness"]
    assert {p["dimension_id"] for p in d["dimensions_preserved"]} == {
        "enterprise_quality", "value_realization_capacity"
    }
    assert d["pe_numeric_score_produced_in_v6"] is False


# ── sensitivity v8 ───────────────────────────────────────────────────────────


def test_sensitivity_v8_full_rerun_and_valuation_keeps_blocked():
    s = _load(SENS_V8)
    assert s["schema"] == "petrochina_dimension_scoring_sensitivity_v8"
    assert s["base_shadow_status"] == DIM_STATUS
    blocked = [x for x in s["scenarios"] if x["dimension_id"] == "valuation_attractiveness"]
    assert len(blocked) > 0
    for x in blocked:
        assert x["scenario_status"] == DIM_STATUS
        assert x["scenario_score"] is None
    # non-valuation scenarios still produce numeric scores
    eq = [x for x in s["scenarios"] if x["dimension_id"] == "enterprise_quality"]
    assert len(eq) > 0
    assert all(x["scenario_score"] is not None for x in eq)


# ── decision ─────────────────────────────────────────────────────────────────


def test_decision_complete_with_cycle_context_gap_remains():
    d = _load(DECISION)
    assert d["decision"] == "VALUATION_SCORING_V2_MIGRATION_COMPLETE_CYCLE_CONTEXT_GAP_REMAINS"
    assert d["confidence"] == "PASS"
    assert d["va_pe_numeric_score_produced_in_v6"] is False
    assert d["valuation_dimension_status_in_v6"] == DIM_STATUS
    assert d["pe_numeric_scoring_authorized"] is False


def test_decision_prohibits_production_overall_and_peer():
    d = _load(DECISION)
    assert d["production_scoring"] == "NOT_AUTHORIZED"
    assert d["overall_score"] == "PROHIBITED"
    assert d["recommendation"] == "PROHIBITED"
    assert d["rank"] == "PROHIBITED"
    assert d["target_price"] == "PROHIBITED"
    assert d["peer_acquisition"] == "NOT_AUTHORIZED_IN_THIS_STAGE"
    assert d["M3"] == "NOT_STARTED"


# ── engine v1 golden path unchanged ──────────────────────────────────────────


def test_engine_v1_default_path_unchanged():
    import sys

    sys.path.insert(0, str(ROOT / "src"))
    from ashare_research.scoring import shadow as sshadow
    from ashare_research.tools import m2_stage2k_scoring_shadow as stage2k

    cap = _load(ROOT / "reports" / "petrochina_score_input_capsule_v4.json")
    inputs = sshadow._capsule_to_inputs(cap)
    reg = _load(ROOT / "config" / "value_dimension_scoring_registry_v1.json")
    pol = _load(ROOT / "config" / "value_dimension_scoring_policy_v1.json")
    v5 = _load(SHADOW_V5)
    for dim in ("enterprise_quality", "valuation_attractiveness", "value_realization_capacity"):
        r = stage2k.compute_dimension(dim, reg, pol, inputs)
        assert r["score"] == v5["dimensions"][dim]["score"]
        assert r["band"] == v5["dimensions"][dim]["band"]
        assert r["status"] == v5["dimensions"][dim]["status"]


def test_engine_has_v2_cli_args_defaulting_to_v1():
    txt = ENGINE.read_text(encoding="utf-8")
    assert "--registry" in txt
    assert "--policy" in txt
    assert "--inputs" in txt
    assert "CYCLE_CONTEXT_GAP_STATUS" in txt
    assert "self_history_dual_window_percentile" in txt


# ── capsule v5 ───────────────────────────────────────────────────────────────


def test_capsule_v5_binds_dual_window_and_blocks_pe():
    c = _load(CAP_V5)
    assert c["schema"] == "petrochina_score_input_capsule_v5"
    assert c["aggregation_contract_version"] == AGG_CONTRACT
    pe_obs = c["components"]["va_pe"]["observation_set"]
    assert pe_obs["dual_window_percentile_decimal"] == "92.6171555"
    assert c["components"]["va_pe"]["numeric_shadow_status"] == HARD_GAP
    pb_obs = c["components"]["va_pb"]["observation_set"]
    assert pb_obs["dual_window_percentile_decimal"] == "87.9583385"


# ── docs / acceptance / manifest ─────────────────────────────────────────────


def test_doc_reports_migration_and_boundary():
    txt = DOC.read_text(encoding="utf-8")
    assert "VALUATION_SCORING_V2_MIGRATION_COMPLETE_CYCLE_CONTEXT_GAP_REMAINS" in txt
    assert "self_history_dual_window_percentile_v1" in txt
    assert "insufficient_evidence_cycle_context" in txt
    assert "NOT_AUTHORIZED" in txt


def test_acceptance_declares_completion_and_boundary():
    txt = ACCEPTANCE.read_text(encoding="utf-8")
    assert "PASS — LOCAL CANDIDATE" in txt
    assert "PE numeric scoring:" in txt and "BLOCKED" in txt
    assert "Production scoring:" in txt and "NOT AUTHORIZED" in txt
    assert "PE cycle-context method:NOT STARTED" in txt


def test_artifact_manifest_verifies_and_is_default():
    import sys

    sys.path.insert(0, str(ROOT / "src"))
    from ashare_research.scoring import artifact_manifest as am

    v = am.verify_artifact_manifest(MANIFEST, repository_root=ROOT)
    assert v.status == "pass", v.errors
    assert v.verified_file_count > 0
    assert v.schema == "m2_stage2k1r4f1_artifact_manifest_v2"
