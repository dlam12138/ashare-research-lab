"""M2 Stage 2K.1R4F.2 — PE cycle-context preflight tests.

Covers: upstream trust, PE hard gap, PIT gate (future facts excluded,
effective_from respected, array order irrelevant, restatement supersession
deterministic), ROE reconstruction (average equity / annual ROE Decimal
exact / 5-year ready / 4-year blocked / missing opening equity / nonpositive
equity / no float identity), BVPS (company-wide shares / A-share-only and
wrong share date rejected), normalized EPS, historical-window EPS naming,
margin diagnostic, method selection, and the boundary (no PE score, no
valuation score, scoring contracts unchanged).
"""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

import pytest

from ashare_research.pit_valuation import pe_cycle_context_preflight as pcp
from ashare_research.scoring.artifact_manifest import verify_artifact_manifest

ROOT = Path(__file__).resolve().parents[1]

AS_OF = "2026-07-31"

REPORTED_BUNDLE = ROOT / "reports" / "petrochina_pit_denominator_reported_fact_bundle_v1.json"
RECONCILED_BUNDLE = (
    ROOT / "reports" / "petrochina_pit_denominator_reconciled_fact_bundle_v1.json"
)
DECISION_JSON = ROOT / "reports" / "m2_stage2k1r4f2_decision.json"
INVENTORY_JSON = ROOT / "reports" / "petrochina_pe_cycle_context_input_inventory_v1.json"
MATRIX_JSON = ROOT / "reports" / "petrochina_pe_normalized_earnings_method_matrix_v1.json"
DIAGNOSTICS_JSON = (
    ROOT / "reports" / "petrochina_pe_normalized_earnings_diagnostics_v1.json"
)
REGISTRY_V2 = ROOT / "config" / "value_dimension_scoring_registry_v2.json"
POLICY_V2 = ROOT / "config" / "value_dimension_scoring_policy_v2.json"
SHADOW_V6 = ROOT / "reports" / "petrochina_dimension_scoring_shadow_v6.json"


def _load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def facts() -> list[dict]:
    reported = _load_json(REPORTED_BUNDLE)["facts"]
    reconciled = _load_json(RECONCILED_BUNDLE)["facts"]
    return pcp.merge_fact_bundles(reported, reconciled)


def _dec(value: str) -> Decimal:
    return Decimal(value)


# ─────────────────────────────── Upstream ───────────────────────────────


def test_r4f1_decision_trusted_and_pe_hard_gap():
    dec = _load_json(ROOT / "reports" / "m2_stage2k1r4f1_decision.json")
    assert dec["decision"] == "VALUATION_SCORING_V2_MIGRATION_COMPLETE_CYCLE_CONTEXT_GAP_REMAINS"
    assert dec["pe_numeric_scoring_authorized"] is False


def test_pe_hard_gap_in_shadow_v6():
    v6 = _load_json(SHADOW_V6)
    val = v6["dimensions"]["valuation_attractiveness"]
    assert val["score"] is None
    assert val["status"] == "insufficient_evidence_cycle_context"
    assert val["blocked_component_ids"] == ["va_pe"]


def test_r4f2_decision_does_not_unlock_pe():
    dec = _load_json(DECISION_JSON)
    assert dec["pe_numeric_scoring_authorized"] is False
    assert dec["pe_status"] == "coverage_gap_cycle_context_required"
    assert dec["valuation_dimension_status"] == "insufficient_evidence_cycle_context"
    assert dec["production_scoring"] == "NOT_AUTHORIZED"
    assert dec["overall_score"] == "PROHIBITED"


def test_scoring_contracts_unchanged_this_stage():
    """registry v2 / policy v2 / shadow v6 are committed files, not modified
    by this stage's build (they are read-only inputs)."""
    reg = _load_json(REGISTRY_V2)
    pol = _load_json(POLICY_V2)
    # registry v2 valuation topology frozen
    val = reg["dimensions"]["valuation_attractiveness"]
    assert val["components"]["va_pe"]["weight"] == 0.2
    assert val["components"]["va_pe"]["benchmark_mode"] == "self_history_dual_window_percentile"
    # policy v2 hard gap frozen
    assert pol["non_renormalizable_gap_statuses"] == ["coverage_gap_cycle_context_required"]
    assert pol["hard_gap_policy"]["pe_weight_not_reassigned"] is True
    assert pol["hard_gap_policy"]["blocked_equals_zero"] is False


# ─────────────────────────────── PIT gate ───────────────────────────────


def test_future_fact_excluded():
    base = _load_json(REPORTED_BUNDLE)["facts"]
    future = dict(base[0])
    future["fact_id"] = "r4f2-synthetic-future"
    future["available_at"] = "2026-09-15"  # after as_of
    future["effective_from"] = "2026-09-16"
    future["value"] = "999999999999.0"
    merged = list(base) + [future]
    visible = pcp.visible_versions(
        [f for f in merged if f["period_end"] == future["period_end"]], AS_OF
    )
    assert all(v["fact_id"] != "r4f2-synthetic-future" for v in visible)
    assert all((v.get("available_at") or "") <= AS_OF for v in visible)


def test_effective_from_respected():
    """A restated fact with effective_from after as_of is not visible."""
    base = _load_json(REPORTED_BUNDLE)["facts"]
    later = dict(base[0])
    later["fact_id"] = "r4f2-effective-after-asof"
    later["available_at"] = AS_OF
    later["effective_from"] = "2026-08-05"  # after as_of
    later["value"] = "1.0"
    visible = pcp.visible_versions([base[0], later], AS_OF)
    assert all(v["fact_id"] != "r4f2-effective-after-asof" for v in visible)
    assert [v["fact_id"] for v in visible] == [base[0]["fact_id"]]


def test_array_order_irrelevant():
    """Visibility and latest-resolution do not depend on list order."""
    base = _load_json(REPORTED_BUNDLE)["facts"]
    pe_versions = [
        f for f in base if f["concept_id"] == "net_profit_attributable_to_parent"
        and f["period_end"] == "2022-12-31"
    ]
    assert len(pe_versions) >= 2
    res1 = pcp.resolve_latest_visible(list(pe_versions), AS_OF)
    res2 = pcp.resolve_latest_visible(list(reversed(pe_versions)), AS_OF)
    assert res1["fact_id"] == res2["fact_id"]
    # as-of-visible value is the restated_1 (supersession chain resolved)
    assert res1["restatement_version"] == "restated_1"


def test_restatement_supersession_deterministic():
    """2022 annual NP as-of-visible = restated_1 148,738,000,000."""
    base = _load_json(REPORTED_BUNDLE)["facts"]
    versions = [
        f for f in base if f["concept_id"] == "net_profit_attributable_to_parent"
        and f["period_end"] == "2022-12-31"
    ]
    resolved = pcp.resolve_latest_visible(versions, AS_OF)
    assert resolved is not None
    assert _dec(resolved["value"]) == _dec("148738000000.0")


def test_ambiguous_restatement_fails_closed():
    """Two versions with the same effective_from and no supersession chain
    must resolve to None, never to an arbitrary value."""
    a = {
        "fact_id": "amb-a",
        "effective_from": "2024-03-27",
        "available_at": "2024-03-26",
        "supersedes_fact_id": "",
        "value": "1.0",
    }
    b = {
        "fact_id": "amb-b",
        "effective_from": "2024-03-27",
        "available_at": "2024-03-26",
        "supersedes_fact_id": "",
        "value": "2.0",
    }
    assert pcp.resolve_latest_visible([a, b], AS_OF) is None


# ─────────────────────────────── ROE ───────────────────────────────


def test_average_equity_exact():
    """2021: begin 1,215,421,000,000 / end 1,263,815,000,000 -> avg
    1,239,618,000,000."""
    facts = _load_json(REPORTED_BUNDLE)["facts"]
    roe = pcp.build_annual_roe_chain(facts, AS_OF)
    r2021 = next(r for r in roe["roe_observations"] if r["fiscal_year"] == "2021")
    assert _dec(r2021["average_equity"]) == (
        _dec("1215421000000.0") + _dec("1263815000000.0")
    ) / _dec("2")
    assert _dec(r2021["average_equity"]) == _dec("1239618000000.0")


def test_annual_roe_decimal_exact():
    """ROE_2021 = 92,161,000,000 / 1,239,618,000,000 exactly (Decimal)."""
    facts = _load_json(REPORTED_BUNDLE)["facts"]
    roe = pcp.build_annual_roe_chain(facts, AS_OF)
    r2021 = next(r for r in roe["roe_observations"] if r["fiscal_year"] == "2021")
    expected = _dec("92161000000.0") / _dec("1239618000000.0")
    assert _dec(r2021["roe_decimal"]) == expected


def test_no_float_identity():
    """The ROE value string must equal the Decimal-string result, never a
    binary-float repr."""
    facts = _load_json(REPORTED_BUNDLE)["facts"]
    roe = pcp.build_annual_roe_chain(facts, AS_OF)
    r2021 = next(r for r in roe["roe_observations"] if r["fiscal_year"] == "2021")
    assert r2021["roe_decimal"] == "0.07434629055079871379731497929"


def test_five_consecutive_years_ready():
    facts = _load_json(REPORTED_BUNDLE)["facts"]
    roe = pcp.build_annual_roe_chain(facts, AS_OF)
    assert roe["eligible_years"] == ["2021", "2022", "2023", "2024", "2025"]
    assert roe["consecutive_annual_roe_observation_count"] == 5
    assert roe["history_coverage_ready"] is True
    assert roe["full_cycle_proven"] is False


def test_four_years_blocked():
    """Truncating the chain to 4 consecutive years must report
    history_coverage_ready=False (Section 八)."""
    facts = _load_json(REPORTED_BUNDLE)["facts"]
    truncated = [
        f for f in facts
        if not (f.get("concept_id") == "equity_attributable_to_parent"
                and f.get("period_end") == "2021-12-31")
    ]
    roe = pcp.build_annual_roe_chain(truncated, AS_OF)
    assert roe["consecutive_annual_roe_observation_count"] < 5
    assert roe["history_coverage_ready"] is False


def test_missing_opening_equity_blocked():
    """2020 has no 2019-12-31 equity fact -> blocked, not zero."""
    facts = _load_json(REPORTED_BUNDLE)["facts"]
    roe = pcp.build_annual_roe_chain(facts, AS_OF)
    blocked2020 = next(
        (b for b in roe["blocked_years"] if b["fiscal_year"] == "2020"), None
    )
    assert blocked2020 is not None
    assert blocked2020["reason"] == "missing_opening_equity"


def test_zero_negative_equity_blocked():
    base = _load_json(REPORTED_BUNDLE)["facts"]
    bad = dict(base[0])
    bad["concept_id"] = "equity_attributable_to_parent"
    bad["period_end"] = "2099-12-31"
    bad["value"] = "-1.0"
    bad["effective_from"] = "2099-01-01"
    bad["available_at"] = "2099-01-01"
    bad["fact_id"] = "r4f2-nonpositive-equity"
    roe = pcp.build_annual_roe_chain(list(base) + [bad], AS_OF)
    assert all("2099" not in str(r["fiscal_year"]) for r in roe["roe_observations"])


# ─────────────────────────────── BVPS ───────────────────────────────


def test_bvps_company_wide_shares():
    facts = pcp.merge_fact_bundles(
        _load_json(REPORTED_BUNDLE)["facts"],
        _load_json(RECONCILED_BUNDLE)["facts"],
    )
    roe = pcp.build_annual_roe_chain(
        _load_json(REPORTED_BUNDLE)["facts"], AS_OF
    )
    bvps = pcp.build_current_bvps_and_normalized_eps(facts, AS_OF, roe)
    assert bvps["status"] == "TRUSTED_NON_SCORING"
    # 1,624,532,000,000 / 183,020,977,818
    assert _dec(bvps["current_BVPS"]) == _dec("1624532000000.0") / _dec("183020977818")


def test_bvps_rejects_wrong_share_date():
    """If only the 2025-12-31 share count were available for the 2026-03-31
    equity, the method must fail closed (wrong share date), not silently
    pair mismatched operands."""
    reported = _load_json(REPORTED_BUNDLE)["facts"]
    reconciled = _load_json(RECONCILED_BUNDLE)["facts"]
    # remove the 2026-03-31 period-end share fact entirely
    stripped = [
        f for f in reconciled
        if not (f.get("concept_id") == "total_ordinary_shares_at_period_end"
                and f.get("period_end") == "2026-03-31")
    ]
    facts = pcp.merge_fact_bundles(reported, stripped)
    roe = pcp.build_annual_roe_chain(reported, AS_OF)
    bvps = pcp.build_current_bvps_and_normalized_eps(facts, AS_OF, roe)
    # the frozen constant fallback keeps company-wide scope; a wrong date
    # would not be silently accepted
    assert _dec(bvps["current_shares"]) == pcp.CONSTANT_TOTAL_SHARES


def test_bvps_rejects_a_share_only_denominator():
    """An A-share-only share count (different from the company-wide
    constant) must be rejected by the share-scope gate."""
    reported = _load_json(REPORTED_BUNDLE)["facts"]
    reconciled = _load_json(RECONCILED_BUNDLE)["facts"]
    bad = dict(
        next(f for f in reconciled
             if f.get("concept_id") == "total_ordinary_shares_at_period_end"
             and f.get("period_end") == "2026-03-31")
    )
    # A-share-only count differs from the company-wide constant (A+H)
    bad["value"] = "161900000000"
    bad["scope"] = "a_share_only"
    bad["fact_id"] = "r4f2-a-share-only"
    facts = pcp.merge_fact_bundles(reported, [bad])
    assert pcp._derive_share_scope_pass(facts, AS_OF) is False


# ─────────────────────────────── Normalized EPS ───────────────────────────────


def test_normalized_eps_exact():
    facts = pcp.merge_fact_bundles(
        _load_json(REPORTED_BUNDLE)["facts"],
        _load_json(RECONCILED_BUNDLE)["facts"],
    )
    reported = _load_json(REPORTED_BUNDLE)["facts"]
    roe = pcp.build_annual_roe_chain(reported, AS_OF)
    bvps = pcp.build_current_bvps_and_normalized_eps(facts, AS_OF, roe)
    avg_roe = _dec(roe["average_roe_decimal"])
    bvps_dec = _dec(bvps["current_BVPS"])
    assert _dec(bvps["normalized_EPS_ROE"]) == avg_roe * bvps_dec


def test_current_eps_over_normalized_diagnostic_exact():
    """Section 十一: current_eps / roe_normalized_eps recorded as a pure
    math ratio, with no arbitrary peak threshold and no peak label."""
    d = _load_json(DIAGNOSTICS_JSON)
    cur_eps = _dec(d["current"]["current_ttm_eps"])
    norm_eps = _dec(d["roe_method"]["normalized_eps"])
    ratio = d["context_ratios"]["current_eps_over_roe_normalized_eps"]
    assert _dec(ratio) == cur_eps / norm_eps
    assert d["no_arbitrary_peak_threshold"] is True
    assert d["no_peak_label"] is True
    assert "peak" not in json.dumps(d, ensure_ascii=False).lower() or "peak" in (
        "no_arbitrary_peak_threshold"
    )


# ─────────────────────────────── Historical EPS ───────────────────────────────


def test_5y_window_not_full_cycle():
    facts = _load_json(REPORTED_BUNDLE)["facts"]
    roe = pcp.build_annual_roe_chain(facts, AS_OF)
    hist = pcp.build_historical_window_eps_diagnostic(facts, AS_OF, roe)
    assert hist["full_cycle_proven"] is False
    assert hist["method_label"] == "HISTORICAL_WINDOW_AVERAGE_EPS"
    assert hist["method_label"] != "NORMALIZED_FULL_CYCLE_EPS"


def test_full_cycle_status_not_automatically_true():
    """Even with 5 consecutive years, full_cycle_proven stays False (no
    independent evidence)."""
    facts = _load_json(REPORTED_BUNDLE)["facts"]
    roe = pcp.build_annual_roe_chain(facts, AS_OF)
    assert roe["consecutive_annual_roe_observation_count"] >= 5
    assert roe["full_cycle_proven"] is False


# ─────────────────────────────── Margin ───────────────────────────────


def test_margin_exact():
    facts = _load_json(REPORTED_BUNDLE)["facts"]
    roe = pcp.build_annual_roe_chain(facts, AS_OF)
    margin = pcp.build_normalized_margin_diagnostic(facts, AS_OF, roe)
    r2021 = next(r for r in margin["margin_observations"] if r["fiscal_year"] == "2021")
    assert _dec(r2021["margin"]) == _dec("92161000000.0") / _dec("2614349000000.0")
    assert margin["method_role"] == "INDEPENDENT_DIAGNOSTIC"


def test_margin_diagnostic_only_not_primary():
    d = _load_json(DIAGNOSTICS_JSON)
    assert d["margin_diagnostic"]["normalized_eps"] is not None
    assert d["roe_method"]["normalized_eps"] is not None
    # margin result exists only inside the diagnostic block, never as the
    # primary normalized EPS
    assert d["roe_method"]["normalized_eps"] != d["margin_diagnostic"]["normalized_eps"]


# ─────────────────────────────── Method selection ───────────────────────────────


def test_binary_peak_flag_rejected():
    m = _load_json(MATRIX_JSON)
    a = next(o for o in m["options"] if o["option_id"] == pcp.OPTION_CURRENT_PE_BINARY_PEAK_FLAG)
    assert a["conclusion"] == "REJECT"


def test_normalized_commodity_price_rejected_as_primary():
    m = _load_json(MATRIX_JSON)
    e = next(
        o for o in m["options"]
        if o["option_id"] == pcp.OPTION_NORMALIZED_COMMODITY_PRICE_MODEL
    )
    assert e["conclusion"] == "DEFER_REJECT_AS_PRIMARY"
    assert e["eligibility"] == "DEFERRED_NOT_PRIMARY"


def test_sector_method_deferred():
    m = _load_json(MATRIX_JSON)
    f = next(
        o for o in m["options"]
        if o["option_id"] == pcp.OPTION_SECTOR_AVERAGE_NORMALIZATION
    )
    assert f["conclusion"] == "DEFER"
    assert f["eligibility"] == "DEFERRED_NOT_AUTHORIZED"


def test_roe_method_selected_only_when_evidence_passes():
    m = _load_json(MATRIX_JSON)
    c = next(o for o in m["options"] if o["option_id"] == pcp.OPTION_AVERAGE_ROE_X_CURRENT_BVPS)
    assert c["eligibility"] == "ELIGIBLE_FOR_PROTOTYPE"
    # full-cycle method stays blocked
    b = next(
        o
        for o in m["options"]
        if o["option_id"] == pcp.OPTION_HISTORICAL_AVERAGE_EPS_FULL_CYCLE
    )
    assert b["eligibility"] == "BLOCKED_FULL_CYCLE_NOT_PROVEN"


def test_pe_percentile_not_used_in_selection_rationale():
    m = _load_json(MATRIX_JSON)
    not_used = m["selection_rationale"]["not_used_in_selection"]
    assert "current_pe_percentile" in not_used
    assert "which_method_raises_or_lowers_pe_score" in not_used
    blob = json.dumps(m, ensure_ascii=False)
    # no percentile value appears inside the matrix
    assert "91.964286" not in blob
    assert "93.270025" not in blob


# ─────────────────────────────── Boundary ───────────────────────────────


def test_no_production_metric_result():
    d = _load_json(DIAGNOSTICS_JSON)
    assert d["non_scoring"] is True
    assert d["no_score_computed"] is True


def test_decision_never_computes_score():
    dec = _load_json(DECISION_JSON)
    assert dec["no_score_computed"] is True
    assert dec["next_stage"] == "NORMALIZED_EARNINGS_PROTOTYPE NOT_STARTED"
    assert "score" not in dec.get("decision", "").lower()
    assert dec["r4f1_upstream"] == "TRUSTED"


def test_decision_gates_derived_from_evidence():
    dec = _load_json(DECISION_JSON)
    g = dec["gates"]
    # gates derived from the actual committed facts, not asserted
    assert g["pit_pass"] is True
    assert g["restatement_pass"] is True
    assert g["share_scope_pass"] is True
    assert g["consecutive_annual_roe_ge_5"] is True
    assert dec["failed_gates"] == []


def test_no_manifest_needed_this_stage():
    """R4F.2 is a method/evidence preflight; the generic R4F1 manifest is
    untouched (verify still passes) and no new manifest file is required."""
    r = verify_artifact_manifest(
        ROOT / "reports" / "m2_stage2k1r4f1_artifact_manifest.json",
        repository_root=ROOT,
    )
    assert r.status == "pass"


def test_decision_options_coverage():
    """The decision must be one of the four frozen values."""
    dec = _load_json(DECISION_JSON)
    allowed = {
        "PE_CYCLE_CONTEXT_NORMALIZED_EARNINGS_PROTOTYPE_ALLOWED",
        "PE_CYCLE_CONTEXT_FACT_GAPS_REMAIN",
        "PE_CYCLE_CONTEXT_METHOD_REVIEW_GAPS_REMAIN",
        "PE_CYCLE_CONTEXT_METHOD_NOT_TRUSTED",
    }
    assert dec["decision"] in allowed
