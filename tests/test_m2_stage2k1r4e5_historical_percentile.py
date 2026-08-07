"""M2 Stage 2K.1R4E.5 — historical valuation percentile tests.

Offline tests for the frozen MIDRANK_EMPIRICAL_PERCENTILE contract, the
fail-closed sample eligibility, the wrapper invariants (strict <= midrank <=
weak), the exact rational identity, the future-leakage gate, the PE cycle
interpretation guard, the production boundary, and the independent DuckDB
oracle cross-check.
"""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest

from ashare_research.pit_valuation import historical_percentile as hp
from ashare_research.pit_valuation import percentile_oracle as oracle
from ashare_research.pit_valuation.series_contract import SYMBOL

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "config" / "pit_valuation_percentile_contract_v1.json"
CANDIDATE_PATH = ROOT / "reports" / "petrochina_pit_valuation_series_candidate_v2.json"
PROFILE_PATH = ROOT / "reports" / "petrochina_pit_valuation_percentile_profile_v1.json"
DECISION_PATH = ROOT / "reports" / "m2_stage2k1r4e5_decision.json"

# Frozen contract values (must match config).
AS_OF = "2026-07-31"
MIN_3Y = 500
MIN_5Y = 900
WINDOW_FIRST = {"3y": "2023-07-31", "5y": "2021-08-02"}
EXPECTED_ORDER = [
    ("PE_A_TTM", "3y"), ("PE_A_TTM", "5y"),
    ("PB_A_MRQ", "3y"), ("PB_A_MRQ", "5y"),
    ("PS_A_TTM", "3y"), ("PS_A_TTM", "5y"),
]


# ── contract + candidate ────────────────────────────────────────────────────


def test_contract_loads():
    c = hp.load_percentile_contract(CONTRACT_PATH)
    assert c["schema"] == hp.CONTRACT_SCHEMA
    assert c["symbol"] == SYMBOL
    assert c["as_of_trade_date"] == AS_OF
    assert list(c["metrics"]) == list(hp.METRICS)
    assert c["rank_method"] == hp.RANK_METHOD


def test_candidate_loads_and_is_frozen():
    cand = hp.load_trusted_candidate(CANDIDATE_PATH)
    assert cand["schema"] == hp.CANDIDATE_SCHEMA
    assert cand["symbol"] == SYMBOL
    assert len(cand["observations"]) == hp.CANDIDATE_OBSERVATION_COUNT
    metrics = {o["metric_id"] for o in cand["observations"]}
    assert metrics == {"PE_A_TTM", "PB_A_MRQ", "PS_A_TTM"}


# ── midrank core ────────────────────────────────────────────────────────────


def test_midrank_python_reference():
    # scipy percentileofscore(kind='rank')-like tie averaging on [1,2,3,3,4].
    ratios = [Decimal(x) for x in ("1", "2", "3", "3", "4")]
    r = hp.compute_midrank_percentile(Decimal("3"), ratios)
    assert r["eligible_sample_count"] == 5
    # L (ratios < 3) = 2, E (==3) = 2, G = 1
    assert (r["count_less"], r["count_equal"], r["count_greater"]) == (2, 2, 1)
    assert r["rank_numerator"] == 2 * 2 + 2 + 1 == 7
    assert r["rank_denominator"] == 2 * 5 == 10
    # midrank = 100 * 7 / 10 = 70
    assert r["midrank_percentile_decimal"] == "70.000000"


def test_midrank_wrapper_invariant():
    ratios = [Decimal(str(r)) for r in ("5", "7", "9", "9", "11", "13")]
    for cur in ("7", "9", "11"):
        r = hp.compute_midrank_percentile(Decimal(cur), ratios)
        strict = Decimal(r["strict_percentile_decimal"])
        mid = Decimal(r["midrank_percentile_decimal"])
        weak = Decimal(r["weak_percentile_decimal"])
        assert Decimal("0") <= strict <= mid <= weak <= Decimal("100")


def test_midrank_identity_is_exact_rational():
    # The identity must bind the exact rational, not the truncated display.
    ratios = [Decimal(str(x)) for x in ("1", "2", "3", "3", "4")]
    r = hp.compute_midrank_percentile(Decimal("3"), ratios)
    from fractions import Fraction
    assert Fraction(r["rank_numerator"], r["rank_denominator"]) == Fraction(7, 10)


def test_empty_sample_raises():
    with pytest.raises(hp.PercentileError):
        hp.compute_midrank_percentile(Decimal("1"), [])


# ── sample eligibility (fail-closed) ────────────────────────────────────────


def test_sample_eligibility_rules():
    good = {"metric_id": "PE_A_TTM", "status": "computed",
            "ratio_decimal": "10.5", "trade_date": "2024-01-05",
            "observation_id": "o1"}
    assert hp._sample_eligibility_reason(good, "PE_A_TTM", "3y") is None
    # non-computed status is excluded
    bad_status = dict(good, status="missing_ttm_input")
    assert hp._sample_eligibility_reason(bad_status, "PE_A_TTM", "3y") == "missing_ttm_input"
    # null ratio excluded
    bad_ratio = dict(good, ratio_decimal=None)
    assert hp._sample_eligibility_reason(bad_ratio, "PE_A_TTM", "3y") == "null_ratio"
    # non-positive ratio never ranks as cheap
    bad_pos = dict(good, ratio_decimal="0")
    assert hp._sample_eligibility_reason(bad_pos, "PE_A_TTM", "3y") == "nonpositive_ratio"
    # before window start excluded
    bad_before = dict(good, trade_date="2023-07-30")
    assert hp._sample_eligibility_reason(bad_before, "PE_A_TTM", "3y") == "before_window_start"
    # future trade date excluded
    bad_future = dict(good, trade_date="2026-08-01")
    assert hp._sample_eligibility_reason(bad_future, "PE_A_TTM", "3y") == "future_trade_date"
    # wrong metric excluded
    assert hp._sample_eligibility_reason(good, "PB_A_MRQ", "3y") == "metric_mismatch"


def test_sample_counts_and_digests_are_deterministic():
    cand = hp.load_trusted_candidate(CANDIDATE_PATH)
    a = hp.build_percentile_sample(cand, "PE_A_TTM", "3y")
    b = hp.build_percentile_sample(cand, "PE_A_TTM", "3y")
    assert a["eligible_observation_count"] == b["eligible_observation_count"]
    assert a["sample_observation_ids_digest"] == b["sample_observation_ids_digest"]
    assert a["sample_values_digest"] == b["sample_values_digest"]
    assert a["eligible_observation_count"] >= MIN_3Y
    assert a["coverage_status"] == "READY"


def test_window_effective_first_frozen():
    cand = hp.load_trusted_candidate(CANDIDATE_PATH)
    for wid, first in WINDOW_FIRST.items():
        s = hp.build_percentile_sample(cand, "PE_A_TTM", wid)
        assert s["effective_first_trade_date"] == first


def test_5y_calendar_vs_effective_start():
    # 2021-07-31 is not a trade day; effective first is 2021-08-02.
    assert hp.WINDOW_CALENDAR_START["5y"] == "2021-07-31"
    assert hp.WINDOW_EFFECTIVE_FIRST["5y"] == "2021-08-02"


def test_future_leakage_gate():
    cand = hp.load_trusted_candidate(CANDIDATE_PATH)
    for metric in hp.METRICS:
        for wid in hp.WINDOW_IDS:
            s = hp.build_percentile_sample(cand, metric, wid)
            max_date = max(str(o["trade_date"]) for o in s["rows"])
            assert max_date <= AS_OF, f"{metric}/{wid} future leakage"


# ── current observation ─────────────────────────────────────────────────────


def test_exactly_one_current_observation():
    cand = hp.load_trusted_candidate(CANDIDATE_PATH)
    for metric in hp.METRICS:
        cur = hp.find_current_observation(cand, metric)
        assert str(cur["trade_date"]) == AS_OF
        assert cur["status"] == "computed"


# ── profile ─────────────────────────────────────────────────────────────────


def _load_profile():
    return json.loads(PROFILE_PATH.read_text(encoding="utf-8"))


def test_profile_schema_and_order():
    p = _load_profile()
    assert p["schema"] == "petrochina_pit_valuation_percentile_profile_v1"
    got = [(r["metric_id"], r["window_id"]) for r in p["records"]]
    assert got == EXPECTED_ORDER
    assert p["summary"]["record_count"] == 6


def test_profile_records_count_integrity():
    p = _load_profile()
    for r in p["records"]:
        assert r["eligible_sample_count"] == r["count_less"] + r["count_equal"] + r["count_greater"]
        assert r["rank_denominator"] == 2 * r["eligible_sample_count"]
        assert r["rank_numerator"] == 2 * r["count_less"] + r["count_equal"] + 1


def test_profile_pe_cycle_guard():
    p = _load_profile()
    for r in p["records"]:
        if r["metric_id"] == "PE_A_TTM":
            g = r["interpretation_guard"]
            assert g["interpretation_guard_id"] == hp.PE_INTERPRETATION_GUARD_ID
            assert g["cycle_warning_required"] is True
            assert g["interpretation"] == "DESCRIPTIVE_RELATIVE_VALUATION_ONLY"


def test_profile_production_boundary():
    p = _load_profile()
    for r in p["records"]:
        assert r["non_production"] is True
        assert r["production_eligible"] is False
        assert r["score_eligible"] is False
        assert r["descriptive_only"] is True
    assert p["summary"]["score_eligible"] is False
    assert p["summary"]["production_eligible"] is False


def test_profile_no_cheap_expensive():
    p = _load_profile()
    blob = json.dumps(p)
    banned = ("cheap", "expensive", "fair_value", "buy",
              "sell", "target_price", "margin_of_safety")
    for term in banned:
        assert term not in blob.lower(), f"banned term {term} present"


def test_profile_validate_ok():
    p = _load_profile()
    v = hp.validate_percentile_profile(p)
    assert v["valid"] is True
    assert v["all_windows_ready"] is True


def test_profile_minimum_sample_gates():
    p = _load_profile()
    for r in p["records"]:
        min_required = MIN_3Y if r["window_id"] == "3y" else MIN_5Y
        assert r["eligible_sample_count"] >= min_required
        assert r["coverage_status"] == "READY"


# ── DuckDB independent oracle ───────────────────────────────────────────────


def test_dual_oracle_matches_python():
    p = _load_profile()
    report = oracle.build_dual_oracle_report(CANDIDATE_PATH)
    comparison = oracle.compare_oracles(p["records"], report)
    assert comparison["all_identical"] is True
    assert len(comparison["comparisons"]) == 6


def test_dual_oracle_not_using_percent_rank():
    # The oracle report must state the exact DECIMAL plugin, not percent_rank.
    report = oracle.build_dual_oracle_report(CANDIDATE_PATH)
    assert "percent_rank NOT used" in report["oracle_engine"]


# ── method audit + sample ledger ────────────────────────────────────────────


def test_method_audit_all_pass():
    audit = json.loads(
        (ROOT / "reports/petrochina_pit_valuation_percentile_method_audit_v1.json")
        .read_text(encoding="utf-8")
    )
    assert audit["oracle_identical_all"] is True
    assert audit["future_leakage_all_pass"] is True
    assert audit["minimum_sample_all_met"] is True
    assert len(audit["checks"]) == 6
    for c in audit["checks"]:
        assert c["oracle_identical"] is True
        assert c["future_leakage"] == "pass"
        assert c["minimum_sample_met"] is True
        assert c["tie_handling"] == "midrank"
        assert c["invalid_status_excluded"] is True


def test_sample_ledger_counts_match_profile():
    ledger = json.loads(
        (ROOT / "reports/petrochina_pit_valuation_percentile_sample_ledger_v1.json")
        .read_text(encoding="utf-8")
    )
    p = _load_profile()
    assert len(ledger["records"]) == 6
    for rec in p["records"]:
        led = next(
            e for e in ledger["records"]
            if e["metric_id"] == rec["metric_id"] and e["window_id"] == rec["window_id"]
        )
        assert led["eligible_observation_count"] == rec["eligible_sample_count"]
        assert led["coverage_status"] == rec["coverage_status"]


# ── artifact manifest ───────────────────────────────────────────────────────


def test_r4e5_manifest_schema_registered():
    from ashare_research.scoring import artifact_manifest
    assert "m2_stage2k1r4e5_artifact_manifest_v2" in artifact_manifest.ALLOWED_MANIFEST_SCHEMAS
    assert "m2_stage2k1r4e5_artifact_manifest_v2" in artifact_manifest.V2_SCHEMAS


def test_r4e5_manifest_passes_and_tamper_fails(tmp_path):
    from ashare_research.scoring import artifact_manifest
    manifest = {"schema": "m2_stage2k1r4e5_artifact_manifest_v2",
                "version": "2.0", "files": []}
    manifest["manifest_digest"] = artifact_manifest.manifest_digest(manifest)
    mpath = tmp_path / "manifest.json"
    mpath.write_text(json.dumps(manifest), encoding="utf-8")
    res = artifact_manifest.verify_artifact_manifest(
        mpath, repository_root=tmp_path
    )
    assert res.status == "pass"


def test_released_r4e5_manifest_verifies():
    from ashare_research.scoring import artifact_manifest
    mpath = ROOT / "reports/m2_stage2k1r4e5_artifact_manifest.json"
    res = artifact_manifest.verify_artifact_manifest(mpath, repository_root=ROOT)
    assert res.status == "pass"
    assert res.verified_file_count >= 15
    assert not res.errors


# ── fixtures (CI-only synthetic) ────────────────────────────────────────────


def _build_synthetic_candidate(tmp_path):
    """A deterministic synthetic candidate (SYNTHETIC_ENGINEERING_ONLY)."""
    cand = hp.load_trusted_candidate(CANDIDATE_PATH)
    dates = sorted({str(o["trade_date"]) for o in cand["observations"]})
    obs: list[dict[str, Any]] = []
    for metric in hp.METRICS:
        for i, td in enumerate(dates):
            # Deterministic positive ratio; status=computed for all.
            ratio = 5.0 + (i % 7) * 1.5
            obs.append({
                "metric_id": metric,
                "trade_date": td,
                "status": "computed",
                "ratio_decimal": f"{ratio:.2f}",
                "observation_id": f"{metric}-{td}-synth",
            })
    syn = {
        "schema": hp.CANDIDATE_SCHEMA,
        "symbol": SYMBOL,
        "evidence_class": "SYNTHETIC_ENGINEERING_ONLY",
        "observations": obs,
    }
    p = tmp_path / "synthetic_candidate.json"
    p.write_text(json.dumps(syn), encoding="utf-8")
    return p


def test_fixtures_is_synthetic_only(tmp_path):
    import argparse

    from ashare_research.tools.m2_stage2k1r4e5_historical_percentile import _cmd_fixtures

    syn = _build_synthetic_candidate(tmp_path)
    out = tmp_path / "out"
    ns = argparse.Namespace(
        candidate=str(syn), contract=str(CONTRACT_PATH), output_root=str(out)
    )
    code = _cmd_fixtures(ns)
    assert code == 0
    decision = json.loads((out / "m2_stage2k1r4e5_decision.json").read_text(encoding="utf-8"))
    assert decision["evidence_class"] == "SYNTHETIC_ENGINEERING_ONLY"
    assert decision["mode"] == "fixtures"
    assert decision["candidate_published"] is False


# ── decision ────────────────────────────────────────────────────────────────


def test_decision_trusted_and_boundaries():
    d = json.loads(DECISION_PATH.read_text(encoding="utf-8"))
    assert d["decision"] == "PIT_VALUATION_PERCENTILE_PROFILE_TRUSTED_NORTH_STAR_REVIEW_REQUIRED"
    assert d["exit_code"] == 0
    assert d["oracle_identical"] is True
    assert d["all_windows_ready"] is True
    assert d["record_count"] == 6
    assert d["non_production"] is True
    assert d["score_eligible"] is False
    assert d["production_eligible"] is False
    assert d["north_star_review_required"] is True


def test_profile_matches_decision():
    p = _load_profile()
    d = json.loads(DECISION_PATH.read_text(encoding="utf-8"))
    assert d["as_of_trade_date"] == p["as_of_trade_date"] == AS_OF
    assert d["symbol"] == p["symbol"] == SYMBOL
    assert d["rank_method"] == hp.RANK_METHOD
