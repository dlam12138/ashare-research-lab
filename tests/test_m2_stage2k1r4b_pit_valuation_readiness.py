"""M2 Stage 2K.1R4B Phase B tests: PIT valuation readiness evidence.

These tests verify only the readiness artifacts (the review doc and the data
availability matrix). They do NOT verify any valuation series, because none is
implemented this round. The assertions pin the honest decision
(PIT_DENOMINATOR_FACT_ACQUISITION_REQUIRED) and the product boundaries.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from ashare_research.scoring import capsule as cap

ROOT = Path(__file__).resolve().parents[1]

ALLOWED_DECISIONS = {
    "PIT_VALUATION_IMPLEMENTATION_ALLOWED",
    "PIT_DENOMINATOR_FACT_ACQUISITION_REQUIRED",
    "EXTERNAL_DAILY_VALUATION_SOURCE_PREFLIGHT_REQUIRED",
    "PIT_VALUATION_NOT_FEASIBLE_UNDER_CURRENT_CONTRACT",
}

ALLOWED_COVERAGE = {
    "ready_trusted",
    "ready_with_explicit_limitations",
    "partial",
    "missing",
    "not_trusted",
}


def _matrix() -> dict:
    return json.loads(
        (ROOT / "reports" / "pit_valuation_denominator_readiness_matrix.json").read_text(
            encoding="utf-8"
        )
    )


def _review_doc() -> str:
    return (ROOT / "docs" / "pit_valuation_denominator_readiness_review.md").read_text(
        encoding="utf-8"
    )


def _reqs() -> list[dict]:
    return _matrix()["requirements"]


# ---------------------------------------------------------------------------
# PE / PB / PS coverage
# ---------------------------------------------------------------------------

def test_pe_pb_ps_all_present():
    reqs = _reqs()
    metric_ids = {r["metric_id"] for r in reqs}
    assert any("pe_ttm" in m for m in metric_ids)
    assert any(m == "pb_equity" for m in metric_ids)
    assert any("ps_ttm" in m for m in metric_ids)


def test_three_denominator_metrics_mapped():
    # PE-TTM, PB, PS-TTM each have a dedicated requirement row
    names = {r["metric_id"] for r in _reqs()}
    assert {"pe_ttm_net_profit", "pb_equity", "ps_ttm_revenue"} <= names


# ---------------------------------------------------------------------------
# 3y / 5y windows and warm-up
# ---------------------------------------------------------------------------

def test_three_five_year_and_warmup_independent_fields():
    for r in _reqs():
        assert "blocks_3y" in r
        assert "blocks_5y" in r
        assert "warmup_start_required" in r
        assert isinstance(r["blocks_3y"], bool)
        assert isinstance(r["blocks_5y"], bool)
        assert isinstance(r["warmup_start_required"], bool)


def test_ttm_denominators_require_warmup():
    # TTM reconstruction needs warm-up financial data before the window start
    for r in _reqs():
        if r["metric_id"] in {"pe_ttm_net_profit", "ps_ttm_revenue"}:
            assert r["warmup_start_required"] is True


# ---------------------------------------------------------------------------
# available_at is a required field
# ---------------------------------------------------------------------------

def test_available_at_required_field():
    for r in _reqs():
        assert isinstance(r["available_at_available"], bool)
        assert any("available_at" in f for f in r["required_fields"])


# ---------------------------------------------------------------------------
# restatement policy
# ---------------------------------------------------------------------------

def test_restatement_policy_exists():
    reqs = _reqs()
    restated = [
        r for r in reqs
        if "restatement" in r["metric_id"]
        or "restatement" in " ".join(r["required_fields"])
    ]
    assert restated, "no restatement-related requirement row found"
    time02 = [r for r in reqs if r["requirement_id"] == "TIME-02"]
    assert time02 and time02[0]["coverage_status"] == "ready_trusted"


# ---------------------------------------------------------------------------
# route decision
# ---------------------------------------------------------------------------

def test_route_decision_clear():
    m = _matrix()
    # R4C supersedes the R4B route: A-share per-share convention (ADR-002) is frozen.
    assert m["route"] == "A_SHARE_PRICE_PER_SHARE"
    assert m["route_status"] == "FROZEN"
    assert m["core_market"] == "SSE_A_SHARE"
    assert m["a_h_split_required"] is False
    assert m["total_ordinary_share_timeline_required"] is True
    # the historical R4B judgement is preserved, not erased
    sb = m["route_superseded_by"]
    assert sb["historical_route"] == "UNRESOLVED"
    assert sb["historical_route_recommendation"] == "MARKET_CAP"
    assert sb["adr"] == "ADR-VALUATION-002"


# ---------------------------------------------------------------------------
# close proxy banned
# ---------------------------------------------------------------------------

def test_close_proxy_banned():
    doc = _review_doc()
    assert "CLOSE_PRICE_PROXY" in doc or "close-price proxy" in doc.lower()
    # the decision must not be the close-proxy path
    assert _matrix()["decision"] != "PIT_VALUATION_IMPLEMENTATION_ALLOWED"


# ---------------------------------------------------------------------------
# current-denominator backfill banned
# ---------------------------------------------------------------------------

def test_current_denominator_backfill_banned():
    doc = _review_doc()
    lower = doc.lower()
    assert "backfill" in lower
    assert "no current-denominator backfill" in lower or "never backfill" in lower


# ---------------------------------------------------------------------------
# each gap has a source reference
# ---------------------------------------------------------------------------

def test_each_gap_has_source_reference():
    for r in _reqs():
        if r["coverage_status"] in {"missing", "partial", "not_trusted"}:
            assert r["gap_ids"], f"{r['requirement_id']} has no gap_ids"
            assert all(g.startswith("PITG-") for g in r["gap_ids"])


# ---------------------------------------------------------------------------
# final decision
# ---------------------------------------------------------------------------

def test_decision_in_allowed_enum():
    assert _matrix()["decision"] in ALLOWED_DECISIONS


def test_decision_is_acquisition_required():
    assert _matrix()["decision"] == "PIT_DENOMINATOR_FACT_ACQUISITION_REQUIRED"


def test_decision_consistent_with_matrix_state():
    m = _matrix()
    reqs = m["requirements"]
    # the TTM denominators and market-cap numerator are missing/partial
    missing = {r["requirement_id"] for r in reqs if r["coverage_status"] == "missing"}
    assert "FIN-01" in missing  # PE-TTM quarterly profit missing
    assert "FIN-03" in missing  # PS-TTM quarterly revenue missing
    assert "MKT-02" in missing  # total_market_cap missing
    # market price side is ready
    mkt01 = next(r for r in reqs if r["requirement_id"] == "MKT-01")
    assert mkt01["coverage_status"] == "ready_trusted"


def test_coverage_statuses_valid_enum():
    for r in _reqs():
        assert r["coverage_status"] in ALLOWED_COVERAGE


# ---------------------------------------------------------------------------
# no series generated / no boundary violation
# ---------------------------------------------------------------------------

def test_no_historical_series_generated():
    # no new valuation series artifact was created
    for path in [
        "reports/petrochina_historical_pe_pb_ps_series.json",
        "reports/pit_valuation_series.json",
        "reports/historical_valuation_series.json",
    ]:
        assert not (ROOT / path).exists(), f"unexpected series artifact: {path}"


def test_no_observation_series_file_created():
    # the Stage 2G valuation observations are unchanged (git-tracked, not modified)
    out = subprocess.run(
        ["git", "status", "--short", "--", "runs/stage2g/stage2g_valuation_pit_20260801/"],
        cwd=ROOT, capture_output=True, text=True,
    )
    assert out.stdout.strip() == "", f"Stage 2G valuation artifacts modified: {out.stdout}"


def test_market_observation_set_business_semantics_unchanged():
    # the observation-set builder must be untouched by this round
    out = subprocess.run(
        ["git", "status", "--short", "--", "src/ashare_research/scoring/market_observation_set.py"],
        cwd=ROOT, capture_output=True, text=True,
    )
    assert out.stdout.strip() == "", "market_observation_set.py was modified"


def test_scoring_weights_thresholds_unchanged():
    # registry weights and policy thresholds must be unchanged by this round
    out = subprocess.run(
        ["git", "status", "--short", "--",
         "config/value_dimension_scoring_registry_v1.json",
         "config/value_dimension_scoring_policy_v1.json"],
        cwd=ROOT, capture_output=True, text=True,
    )
    assert out.stdout.strip() == "", "scoring registry/policy modified"


def test_no_production_score_generated():
    # decision is not IMPLEMENTATION_ALLOWED; no production score source
    assert _matrix()["decision"] != "PIT_VALUATION_IMPLEMENTATION_ALLOWED"
    assert _matrix()["non_production"] is True
    assert _matrix()["score_eligible"] is False


def test_no_peer_acquisition_started():
    assert "peer" not in _matrix()["decision"]
    # no new peer acquisition artifact
    for path in ["reports/peer_acquisition_plan.json", "reports/peer_database.json"]:
        assert not (ROOT / path).exists()


def test_no_m3_started():
    doc = _review_doc()
    assert "not start" in doc.lower() or "no m3" in doc.lower() or "peer" in doc.lower()
    assert "M3" not in _matrix()["decision"]


def test_valuation_attractiveness_not_interpretable():
    # unchanged: the valuation dimension is a non-production shadow
    capsule = cap.build_capsule()
    for cid in ("va_pe", "va_pb", "va_ps"):
        obs = capsule["components"][cid].get("observation_set") or {}
        assert obs.get("percentile_source") != "close_percentile_as_valuation"


def test_review_doc_mentions_route_a_and_b():
    doc = _review_doc()
    assert "Route A" in doc and "Route B" in doc
    lower = doc.lower()
    assert ("market cap" in lower or "market-cap" in lower)
    assert ("per share" in lower or "per-share" in lower)
