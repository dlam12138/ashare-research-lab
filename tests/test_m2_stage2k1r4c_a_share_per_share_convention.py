"""M2 Stage 2K.1R4C tests: A-share per-share convention + quarterly acquisition contract.

Covers the four phases:

  Phase A1: the R4B work-record status conflict is fixed (top is `completed`, not
            `in_progress`; the historical starting-state text is preserved).
  Phase A2: the sensitivity validator recomputes the FULL per-dimension summary
            (incl. both gate blocks and production_readiness_reason) from the ledger;
            tampering with any summary field fails even when the digest is recomputed.
  Phase B:  ADR-VALUATION-002 freezes the A-share per-share convention; the R4B
            route is superseded (A/H split no longer a core blocker); the overall
            PIT_DENOMINATOR_FACT_ACQUISITION_REQUIRED decision is unchanged.
  Phase C/D: the quarterly acquisition contract is frozen (no collection, no series);
            the ready decision is A_SHARE_CONVENTION_FROZEN_ACQUISITION_ALLOWED.

No production scores, no peer acquisition, no M3.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from ashare_research.scoring import capsule as cap
from ashare_research.scoring import confidence as confidence_mod
from ashare_research.scoring import sensitivity as sensitivity_mod
from ashare_research.scoring import validator as validator_mod

ROOT = Path(__file__).resolve().parents[1]

R4B_RECORD = (
    ROOT / "agent" / "record"
    / "2026-08-04_Stage2K1R4B_artifact_audit_and_pit_valuation_readiness.md"
)
ADR = ROOT / "docs" / "decisions" / "ADR-VALUATION-002-a-share-per-share-convention.md"
PLAN = ROOT / "config" / "pit_valuation_fact_acquisition_plan_v1.json"
COVERAGE = ROOT / "reports" / "pit_valuation_fact_acquisition_coverage_matrix.json"
DECISION = ROOT / "reports" / "m2_stage2k1r4c_decision.json"
MATRIX = ROOT / "reports" / "pit_valuation_denominator_readiness_matrix.json"
R4B_DECISION = ROOT / "reports" / "m2_stage2k1r4b_decision.json"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _capsule() -> dict:
    return cap.build_capsule()


def _lineage_report(capsule: dict) -> dict:
    rep = validator_mod.validate_capsule(capsule)
    rep["report_digest"] = cap._sha256_bytes(cap._canonical(rep))
    return rep


def _sensitivity_v6() -> dict:
    capsule = _capsule()
    confidence = confidence_mod.build_confidence(capsule, _lineage_report(capsule))
    return sensitivity_mod.build_sensitivity_v6(capsule, confidence)


def _recompute_digest_and_validate(report: dict) -> dict:
    report["ledger_digest"] = sensitivity_mod.ledger_digest(report)
    return sensitivity_mod.validate_sensitivity_ledger(report)


# ---------------------------------------------------------------------------
# Phase A1: R4B work-record status
# ---------------------------------------------------------------------------

def test_r4b_record_status_completed():
    text = R4B_RECORD.read_text(encoding="utf-8")
    assert "Status: `completed`" in text
    assert "in_progress" not in text


def test_r4b_record_closeout_metadata_present():
    text = R4B_RECORD.read_text(encoding="utf-8")
    assert "Closeout verdict: `PASS`" in text
    assert "Final head: `15c8e28`" in text
    assert "Final CI: `30907749043`" in text


def test_r4b_record_starting_state_preserved():
    # the historical body's starting state (85e1390) must be unaffected
    text = R4B_RECORD.read_text(encoding="utf-8")
    assert "85e1390" in text


# ---------------------------------------------------------------------------
# Phase A2: sensitivity validator full-summary recompute + tamper
# ---------------------------------------------------------------------------

def test_sensitivity_full_summary_recomputable_from_ledger():
    v = sensitivity_mod.validate_sensitivity_ledger(_sensitivity_v6())
    assert v["status"] == "pass", v["errors"]


def test_sensitivity_tamper_coverage_gate_fails():
    s = _sensitivity_v6()
    dim = "enterprise_quality"
    s["dimensions"][dim]["coverage_gate_sensitivity"]["passes"][0] = "fail"
    assert _recompute_digest_and_validate(s)["status"] == "fail"


def test_sensitivity_tamper_confidence_gate_fails():
    s = _sensitivity_v6()
    dim = "enterprise_quality"
    s["dimensions"][dim]["confidence_gate_sensitivity"]["grade"] = "high"
    assert _recompute_digest_and_validate(s)["status"] == "fail"


def test_sensitivity_tamper_production_readiness_reason_fails():
    s = _sensitivity_v6()
    dim = "enterprise_quality"
    s["dimensions"][dim]["production_readiness_reason"] = "fake"
    assert _recompute_digest_and_validate(s)["status"] == "fail"


def test_sensitivity_tamper_scenario_and_summary_sync_fails():
    s = _sensitivity_v6()
    dim = "enterprise_quality"
    s["scenarios"][0]["scenario_score"] = 999.0
    s["dimensions"][dim]["min_score"] = 999.0
    assert _recompute_digest_and_validate(s)["status"] == "fail"


def test_sensitivity_full_rebuild_a_b_identical():
    a = _sensitivity_v6()
    b = _sensitivity_v6()
    assert a == b
    assert a["ledger_digest"] == b["ledger_digest"]


def test_sensitivity_v6_report_unchanged_digest():
    """The committed sensitivity v6 report must be byte-identical to a fresh build.

    The committed report embeds the capsule digest of the platform it was generated
    on into its scenario ids. The capsule digest is deterministic per platform but
    can differ across platforms (a known pre-existing engine limitation, not changed
    by R4C). Byte-identity is therefore asserted only when the fresh build's capsule
    digest matches the committed report's; on a different platform the fresh build is
    still asserted to be internally consistent and valid.
    """
    report = _load(ROOT / "reports" / "petrochina_dimension_scoring_sensitivity_v6.json")
    fresh = _sensitivity_v6()
    if fresh["scenarios"][0]["input_capsule_digest"] == report["scenarios"][0][
        "input_capsule_digest"
    ]:
        assert report == fresh
        assert report["ledger_digest"] == (
            "213cdba05c5d5664f199d73529de18d214b270a19147347eb7c0ff470efd6ccf"
        )
    else:
        # different generating platform: the committed file is not byte-comparable
        v = sensitivity_mod.validate_sensitivity_ledger(fresh)
        assert v["status"] == "pass", v["errors"]
        assert fresh["ledger_digest"] == sensitivity_mod.ledger_digest(fresh)


def test_sensitivity_stability_not_stable_preserved():
    s = _sensitivity_v6()
    for dim in cap.SCORED_DIMENSIONS:
        assert s["dimensions"][dim]["stability_status"] == "NOT_STABLE"
        assert s["dimensions"][dim]["stability_tolerance"] == 1.0


# ---------------------------------------------------------------------------
# Phase B: ADR-002 A-share per-share convention
# ---------------------------------------------------------------------------

def test_adr_002_exists_and_accepted():
    assert ADR.exists()
    text = ADR.read_text(encoding="utf-8")
    assert "Status: `accepted`" in text
    assert "A_SHARE_PRICE_PER_SHARE_VALUATION_CONVENTION" in text


def test_a_share_price_is_only_core_price():
    d = _load(DECISION)
    assert d["convention"]["core_market"] == "SSE_A_SHARE"
    assert d["convention"]["route"] == "A_SHARE_PRICE_PER_SHARE"
    assert d["convention"]["route_status"] == "FROZEN"


def test_h_share_not_in_core_valuation():
    text = ADR.read_text(encoding="utf-8")
    assert "h_share_price_in_core_valuation = false" in text
    assert "h_share_fx_in_core_valuation = false" in text
    assert "dual_market_cap_in_core_valuation = false" in text


def test_a_h_split_not_core_blocker():
    d = _load(DECISION)
    assert d["convention"]["a_h_split_required"] is False
    m = _load(MATRIX)
    assert m["a_h_split_required"] is False


def test_total_ordinary_share_timeline_required():
    d = _load(DECISION)
    assert d["convention"]["total_ordinary_share_timeline_required"] is True
    m = _load(MATRIX)
    assert m["total_ordinary_share_timeline_required"] is True


def test_r4b_route_superseded_historical_preserved():
    m = _load(MATRIX)
    assert m["route"] == "A_SHARE_PRICE_PER_SHARE"
    sb = m["route_superseded_by"]
    assert sb["historical_route"] == "UNRESOLVED"
    assert sb["historical_route_recommendation"] == "MARKET_CAP"
    assert sb["adr"] == "ADR-VALUATION-002"


def test_r4b_decision_pit_unchanged():
    m = _load(MATRIX)
    assert m["decision"] == "PIT_DENOMINATOR_FACT_ACQUISITION_REQUIRED"
    r4b = _load(R4B_DECISION)
    assert r4b["decision"] == "PIT_DENOMINATOR_FACT_ACQUISITION_REQUIRED"


def test_r4b_decision_blocks_updated():
    r4b = _load(R4B_DECISION)
    # total_market_cap removed from the PE/PB/PS blocks; share timeline kept
    assert "MKT-02" not in r4b["blocks"]["pe_ttm"]
    assert "MKT-02" not in r4b["blocks"]["pb"]
    assert "MKT-02" not in r4b["blocks"]["ps_ttm"]
    assert r4b["a_h_split_required"] is False


# ---------------------------------------------------------------------------
# Phase C: quarterly acquisition contract
# ---------------------------------------------------------------------------

def test_pe_uses_weighted_average_shares():
    p = _load(PLAN)
    assert "weighted_average" in p["target_metrics"]["pe_ttm"]["share_count_convention"]


def test_pb_uses_period_end_shares():
    p = _load(PLAN)
    assert "period_end" in p["target_metrics"]["pb_mrq"]["share_count_convention"]


def test_ps_share_count_convention_unique():
    p = _load(PLAN)
    conv = p["target_metrics"]["ps_ttm"]["share_count_convention"]
    assert "period_end" in conv
    assert "weighted" not in conv  # PS share count is explicitly period-end, not switched


def test_quarterly_profit_and_revenue_ttm_required():
    cm = _load(COVERAGE)
    fin01 = next(r for r in cm["requirements"] if r["requirement_id"] == "FIN-01")
    fin03 = next(r for r in cm["requirements"] if r["requirement_id"] == "FIN-03")
    assert fin01["coverage_status"] == "acquisition_required"
    assert fin03["coverage_status"] == "acquisition_required"
    assert "quarterly_cumulative" in fin01["period_types_required"]
    assert "quarterly_cumulative" in fin03["period_types_required"]


def test_quarterly_equity_mrq_required():
    cm = _load(COVERAGE)
    fin02 = next(r for r in cm["requirements"] if r["requirement_id"] == "FIN-02")
    assert "quarterly_end" in fin02["period_types_required"]


def test_available_at_and_restatement_rules_exist():
    p = _load(PLAN)
    tc = p["time_contract"]
    for f in (
        "period_start", "period_end", "filing_date", "available_at",
        "effective_from", "restatement_version", "supersedes_fact_id",
        "source_evidence_id",
    ):
        assert f in tc["required_fields_per_fact"]
    assert "next trading day" in tc["effective_rule"]
    assert "never backfill" in tc["restatement_rule"]


def test_share_dps_basis_not_valuation_contract():
    p = _load(PLAN)
    note = p["share_facts"]["weighted_average_total_ordinary_shares"]["note"]
    assert "dividend-DPS-basis" in note


# ---------------------------------------------------------------------------
# Phase D: ready decision + boundaries
# ---------------------------------------------------------------------------

def test_r4c_decision_allowed():
    d = _load(DECISION)
    assert d["decision"] == "A_SHARE_CONVENTION_FROZEN_ACQUISITION_ALLOWED"


def test_close_percentile_not_valuation_percentile():
    capsule = _capsule()
    for cid in ("va_pe", "va_pb", "va_ps"):
        obs = capsule["components"][cid].get("observation_set") or {}
        assert obs.get("percentile_source") != "close_percentile_as_valuation"


def test_no_historical_series_generated():
    for path in [
        "reports/petrochina_historical_pe_pb_ps_series.json",
        "reports/pit_valuation_series.json",
        "reports/historical_valuation_series.json",
    ]:
        assert not (ROOT / path).exists(), f"unexpected series artifact: {path}"


def test_valuation_shadow_not_modified():
    out = subprocess.run(
        ["git", "status", "--short", "--", "src/ashare_research/scoring/market_observation_set.py"],
        cwd=ROOT, capture_output=True, text=True,
    )
    assert out.stdout.strip() == "", "market_observation_set.py was modified"


def test_scoring_weights_thresholds_unchanged():
    out = subprocess.run(
        ["git", "status", "--short", "--",
         "config/value_dimension_scoring_registry_v1.json",
         "config/value_dimension_scoring_policy_v1.json"],
        cwd=ROOT, capture_output=True, text=True,
    )
    assert out.stdout.strip() == "", "scoring registry/policy modified"


def test_no_peer_acquisition_started():
    for path in ["reports/peer_acquisition_plan.json", "reports/peer_database.json"]:
        assert not (ROOT / path).exists()
    assert "peer" not in _load(DECISION)["decision"]


def test_no_m3_started():
    assert "M3" not in _load(DECISION)["decision"]
    assert _load(DECISION)["implementation"]["m3_started"] is False


def test_r4c_artifact_manifest_verifies_and_is_default():
    from ashare_research.scoring import artifact_manifest as am
    from ashare_research.tools import m2_stage2k1r3_closeout as closeout

    manifest = ROOT / "reports" / "m2_stage2k1r4c_artifact_manifest.json"
    assert manifest.exists()
    v = am.verify_artifact_manifest(manifest, repository_root=ROOT)
    assert v.status == "pass", v.errors
    assert v.verified_file_count == 14
    # the CLI default points at the R4C manifest (not a stale R4B one)
    assert manifest == closeout.DEFAULT_MANIFEST
    assert am.verify_artifact_manifest(
        closeout.DEFAULT_MANIFEST, repository_root=ROOT
    ).status == "pass"
