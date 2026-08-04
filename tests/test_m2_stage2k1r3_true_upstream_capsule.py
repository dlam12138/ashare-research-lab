"""M2 Stage 2K.1R3 tests: true upstream record binding, verified market
observation-set closeout, capsule v3 + fail-closed recompute validator,
source-tier confidence, shadow v4, sensitivity v4, composite tamper.

Covers the true upstream record binding closeout. No production scores, no
peer acquisition, no committed-percentile fallback.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from ashare_research.scoring import market_observation_set as mos
from ashare_research.tools import m2_stage2k1r3_closeout as closeout

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config"
REPORTS = ROOT / "reports"
EVENTS = ROOT / "events"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _capsule() -> dict:
    return closeout.build_capsule()


# ---------------------------------------------------------------------------
# 1. upstream registry (true record binding)
# ---------------------------------------------------------------------------

def test_upstream_registry_24_components_with_resolvers():
    reg = _load(CONFIG / "value_dimension_scoring_upstream_registry_v1.json")
    assert reg["schema"] == "value_dimension_scoring_upstream_registry_v1"
    assert len(reg["components"]) == 24
    for c in reg["components"]:
        assert c["resolver_id"]
        assert c["artifact_contract"]
        assert c["selector"]
        assert c["allowed_source_tiers"]
        assert c["prohibited_fallbacks"]


def test_source_tier_bindings_registry_present():
    reg = _load(CONFIG / "value_dimension_scoring_upstream_registry_v1.json")
    bindings = reg["source_tier_bindings"]
    assert "canonical_fact_bundle_resolver" in bindings
    assert "market_manifest_resolver" in bindings
    assert "gap_ledger_resolver" in bindings
    assert "dividend_event_resolver" in bindings
    assert "risk_profile_resolver" in bindings
    assert "repurchase_search_resolver" in bindings


def test_transform_registry_layer_separation():
    reg = _load(CONFIG / "value_dimension_scoring_transform_registry_v2.json")
    assert reg["layer_separation"]["layer_1"].startswith(
        "upstream records -> financial/valuation metric values"
    )
    assert reg["layer_separation"]["layer_2"].startswith(
        "metric values -> dimension component scores"
    )
    assert "gross_margin_v1" in reg["transforms"]
    assert "manual_constant" in reg["prohibited_fallbacks"]


# ---------------------------------------------------------------------------
# 2. capsule v3 true record binding
# ---------------------------------------------------------------------------

def test_capsule_v3_24_components_with_resolved_records():
    capsule = _capsule()
    assert capsule["schema"] == "petrochina_score_input_capsule_v3"
    assert capsule["component_count"] == 24
    for cid, comp in capsule["components"].items():
        # every component binds concrete upstream records, not just a file
        assert comp["resolved_records"], f"{cid} has no resolved_records"
        assert comp["operand_record_ids"], f"{cid} has no operand records"
        assert comp["score_input_id"]
        assert comp["validator_must_rebuild"] is True
        assert comp["transform_inputs_role"] == "derived_snapshot_only"
        # capsule never self-reports source tier; it is derived by the resolver
        assert comp["resolved_source_tier"] in comp["resolved_records"][0].get("source_tier", "") \
            or comp["resolved_source_tier"] == "computed_from_verified_canonical_inputs"


def test_capsule_v3_does_not_trust_old_capsule():
    # the capsule is built from the registry + resolvers, not from a previous
    # capsule's transform_inputs
    capsule = _capsule()
    for comp in capsule["components"].values():
        assert comp["transform_inputs_role"] == "derived_snapshot_only"
        assert comp["validator_must_rebuild"] is True


def test_capsule_v3_non_production_and_no_overall():
    capsule = _capsule()
    assert capsule["score_eligible"] is False
    assert capsule["overall_score_prohibited"] is True
    assert capsule["recommendation_prohibited"] is True
    assert capsule["non_production"] is True


def test_all_components_share_expected_sources():
    capsule = _capsule()
    for comp in capsule["components"].values():
        assert comp["dimension_id"] in {
            "enterprise_quality",
            "valuation_attractiveness",
            "value_realization_capacity",
            "risk_and_evidence_integrity",
        }


# ---------------------------------------------------------------------------
# 3. risk count semantics
# ---------------------------------------------------------------------------

def test_risk_counts_correct():
    capsule = _capsule()
    # no veto triggered; only 2 slots have missing evidence, 6 are bounded-search clean
    assert capsule["components"]["rk_veto_triggered"]["selected_value_decimal"] == "0"
    assert capsule["components"]["rk_missing_evidence_slots"]["selected_value_decimal"] == "2"
    assert capsule["components"]["rk_gap_count"]["selected_value_decimal"] == "18"
    assert capsule["components"]["eq_roic"]["selected_value_decimal"] == "7"


def test_dividend_coverage_sums_across_events():
    capsule = _capsule()
    # FY2025 has interim (0.22) + final (0.25) = 0.47 DPS
    assert float(capsule["components"]["vr_dps"]["selected_value_decimal"]) == 0.47


# ---------------------------------------------------------------------------
# 4. validator recomputes from upstream
# ---------------------------------------------------------------------------

def test_validator_passes():
    capsule = _capsule()
    result = closeout.validate_capsule(capsule)
    assert result["status"] == "pass", result["errors"]


def test_validator_detects_self_reported_inputs():
    capsule = _capsule()
    tampered = json.loads(json.dumps(capsule))
    comp = tampered["components"]["eq_gross_margin"]
    comp["transform_inputs"] = {"revenue": "999999", "operating_cost": "1"}
    comp["selected_value_decimal"] = "0.999999"
    comp["score_input_id"] = "0" * 64
    tampered["capsule_digest"] = closeout.capsule_digest(tampered)
    result = closeout.validate_capsule(tampered)
    assert result["status"] == "fail"
    assert any("upstream_recomputed_value_mismatch" in e for e in result["errors"])
    assert any("score_input_id_mismatch" in e for e in result["errors"])


def test_validator_detects_self_reported_source_tier():
    capsule = _capsule()
    tampered = json.loads(json.dumps(capsule))
    tampered["components"]["eq_roe"]["resolved_source_tier"] = "coverage_gap"
    tampered["capsule_digest"] = closeout.capsule_digest(tampered)
    result = closeout.validate_capsule(tampered)
    assert result["status"] == "fail"
    assert any("source_tier_mismatch" in e for e in result["errors"])


def test_validator_rejects_missing_component():
    capsule = _capsule()
    tampered = json.loads(json.dumps(capsule))
    del tampered["components"]["eq_roic"]
    tampered["component_count"] = len(tampered["components"])
    tampered["capsule_digest"] = closeout.capsule_digest(tampered)
    result = closeout.validate_capsule(tampered)
    assert result["status"] == "fail"
    assert any("missing from capsule" in e for e in result["errors"])


def test_validator_rejects_capsule_digest_tamper():
    capsule = _capsule()
    tampered = json.loads(json.dumps(capsule))
    tampered["capsule_digest"] = "0" * 64
    result = closeout.validate_capsule(tampered)
    assert result["status"] == "fail"
    assert any("capsule_digest_mismatch" in e for e in result["errors"])


def test_validator_ignores_capsule_record_snapshot():
    # the validator recomputes records from upstream; a capsule snapshot with a
    # wrong raw_value/record_digest but a correct score_input_id still passes
    capsule = _capsule()
    tampered = json.loads(json.dumps(capsule))
    rec = tampered["components"]["eq_gross_margin"]["resolved_records"][0]
    rec["raw_value"] = "999999"
    rec["record_digest"] = "0" * 64
    tampered["capsule_digest"] = closeout.capsule_digest(tampered)
    result = closeout.validate_capsule(tampered)
    assert result["status"] == "pass"


def test_pt_no_evidence_after_scorecard_formed():
    capsule = _capsule()
    formed = capsule["time_contract"]["scorecard_formed_at"]
    for cid, comp in capsule["components"].items():
        aa = (comp.get("available_at") or "").split("T")[0]
        assert aa <= formed, f"{cid} available_at {aa} after scorecard {formed}"


def test_source_tiers_allowed_by_binding():
    capsule = _capsule()
    reg = _load(CONFIG / "value_dimension_scoring_upstream_registry_v1.json")
    by_id = {c["component_id"]: c for c in reg["components"]}
    for cid, comp in capsule["components"].items():
        spec = by_id[cid]
        assert comp["resolved_source_tier"] in spec["allowed_source_tiers"], cid


# ---------------------------------------------------------------------------
# 5. real market observation set (verified external cache)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def real_cache_env(tmp_path_factory):
    """Build a real-cache root from the committed baostock external snapshot and
    a baostock-only registry (the akshare provider snapshot is not in the repo)."""
    src_parquet = (
        ROOT / "runs" / "stage2g" / "stage2g_valuation_pit_20260801"
        / "stock_daily_snapshot.parquet"
    )
    if not src_parquet.is_file():
        pytest.skip("real baostock snapshot not present in repo")
    reg = _load(EVENTS / "market_data_snapshot_registry.json")
    baostock = [p for p in reg["providers"] if p["logical_name"].startswith("601857.SH_baostock")]
    assert len(baostock) == 1
    cache_root = tmp_path_factory.mktemp("real_cache")
    target = cache_root / baostock[0]["object_key"]
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src_parquet, target)
    reg["providers"] = baostock
    reg_path = tmp_path_factory.mktemp("reg") / "market_registry_baostock_only.json"
    reg_path.write_text(json.dumps(reg, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"cache_root": cache_root, "registry": reg_path}


def test_real_observation_set_from_external_cache(real_cache_env):
    result = mos.build_observation_set(
        registry_path=real_cache_env["registry"],
        mode="real_research",
        cache_root=real_cache_env["cache_root"],
        fixture_root=None,
        symbol="601857.SH",
        market_data_as_of_date="2026-07-31",
        scorecard_formed_at="2026-08-02",
    )
    assert result["market_validation_mode"] == "external_verified_cache"
    assert result["real_market_verified"] is True
    os_ = result["observation_set"]
    assert os_["excluded_observation_count"] == 0
    assert os_["exclusion_reasons"] == ["trade_date > market_data_as_of_date"]
    assert os_["provider_object_sha256"].startswith("defd0b95")
    assert os_["percentile_3y_close"] is not None
    assert os_["percentile_5y_close"] is not None
    assert os_["observation_set_digest"]


def test_real_capsule_uses_cache_recomputed_price_percentiles(real_cache_env):
    capsule = closeout.build_capsule(
        market_cache_root=real_cache_env["cache_root"],
        market_validation_mode="external_verified_cache",
        market_registry=real_cache_env["registry"],
    )
    assert capsule["real_market_verified"] is True
    for metric in ("va_pe", "va_pb", "va_ps"):
        obs = capsule["components"][metric]["observation_set"]
        assert obs["percentile_source"] == "external_cache_recomputed"
        assert obs["percentile_3y"] is not None
    # yield metrics are not cache-recomputable from the daily close cache
    for metric in ("va_fcf_yield", "va_dividend_yield"):
        obs = capsule["components"][metric]["observation_set"]
        assert obs["percentile_3y"] is None
    # real-mode capsule still validates
    result = closeout.validate_capsule(
        capsule,
        market_cache_root=real_cache_env["cache_root"],
        market_registry=real_cache_env["registry"],
    )
    assert result["status"] == "pass", result["errors"]


# ---------------------------------------------------------------------------
# 6. confidence, shadow, sensitivity
# ---------------------------------------------------------------------------

def test_confidence_grades_by_derived_source_tier():
    capsule = _capsule()
    lineage_report = closeout.validate_capsule(capsule)
    lineage_report["report_digest"] = closeout._sha256_bytes(closeout._canonical(lineage_report))
    confidence = closeout.build_confidence(capsule, lineage_report)
    assert confidence["schema"] == "petrochina_dimension_evidence_confidence_v3"
    assert confidence["dimensions"]["enterprise_quality"]["grade"] == "medium"
    # valuation has a coverage gap (va_dividend_yield has no manifest percentile)
    reasons = confidence["dimensions"]["valuation_attractiveness"]["reasons"]
    assert any("coverage_gap:va_dividend_yield" in r for r in reasons)


def test_shadow_runs_with_no_overall_score():
    capsule = _capsule()
    lineage_report = closeout.validate_capsule(capsule)
    lineage_report["report_digest"] = closeout._sha256_bytes(closeout._canonical(lineage_report))
    confidence = closeout.build_confidence(capsule, lineage_report)
    shadow = closeout.build_shadow(capsule, confidence)
    assert shadow["schema"] == "petrochina_dimension_scoring_shadow_v4"
    assert shadow["status"] == "pass"
    assert shadow["overall_score_prohibited"] is True
    assert shadow["recommendation_prohibited"] is True
    assert shadow["score_eligible"] is False
    # risk dimension is status outputs, never a merged numeric score
    assert shadow["dimensions"]["risk_and_evidence_integrity"]["no_merged_numeric_score"] is True


def test_sensitivity_not_stable_and_no_production():
    capsule = _capsule()
    sensitivity = closeout.build_sensitivity(capsule)
    assert sensitivity["schema"] == "petrochina_dimension_scoring_sensitivity_v4"
    assert sensitivity["overall_score_prohibited"] is True
    assert sensitivity["score_eligible"] is False
    # honest conclusion: NOT_STABLE across each scored dimension
    for dim in ("enterprise_quality", "valuation_attractiveness", "value_realization_capacity"):
        assert sensitivity["dimensions"][dim]["stability_status"] == "NOT_STABLE"
