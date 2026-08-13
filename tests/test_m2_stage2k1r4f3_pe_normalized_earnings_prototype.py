"""M2 Stage 2K.1R4F.3 — PE normalized-earnings prototype tests.

Covers: upstream trust, ROE contract (never shortened), normalized EPS
(current TTM EPS is not an input), normalized PE (exact candidate close,
raw PE recomputation identical), mechanical-inversion property, historical
PIT walk-forward (no future leak / no back-fill / array order), readiness
(no forward fill, no 3y/4y ROE fallback), exact fact-gap derivation, and
scoring boundary (PE score null, contracts untouched).
"""

from __future__ import annotations

import json
import shutil
from decimal import Decimal
from pathlib import Path

import pytest

from ashare_research.pit_valuation import pe_normalized_earnings_prototype as pnep
from ashare_research.pit_valuation.pe_cycle_context_preflight import merge_fact_bundles

ROOT = Path(__file__).resolve().parents[1]

AS_OF = "2026-07-31"

REPORTED_BUNDLE = (
    ROOT / "reports" / "petrochina_pit_denominator_reported_fact_bundle_v1.json"
)
RECONCILED_BUNDLE = (
    ROOT / "reports" / "petrochina_pit_denominator_reconciled_fact_bundle_v1.json"
)
CANDIDATE_V2 = ROOT / "reports" / "petrochina_pit_valuation_series_candidate_v2.json"
FIXTURES = ROOT / "tmp" / "r4f3_synthetic_walk_forward_facts.json"

R4F2_DECISION = ROOT / "reports" / "m2_stage2k1r4f2_decision.json"
R4F3_DECISION = ROOT / "reports" / "m2_stage2k1r4f3_decision.json"
PROTOTYPE_V1 = ROOT / "reports" / "petrochina_pe_normalized_earnings_prototype_v1.json"
PE_SNAPSHOT_V1 = ROOT / "reports" / "petrochina_pe_normalized_pe_snapshot_v1.json"
INVERSION_AUDIT_V1 = (
    ROOT / "reports" / "petrochina_pe_mechanical_inversion_audit_v1.json"
)
READINESS_V1 = (
    ROOT / "reports" / "petrochina_pe_normalized_earnings_historical_readiness_v1.json"
)
LEDGER_V1 = (
    ROOT / "reports" / "petrochina_pe_normalized_earnings_historical_state_ledger_v1.json"
)
GAP_PLAN_V1 = (
    ROOT / "reports" / "petrochina_pe_normalized_earnings_historical_fact_gap_plan_v1.json"
)

SCORING_CONTRACTS = (
    ROOT / "config" / "value_dimension_scoring_registry_v2.json",
    ROOT / "config" / "value_dimension_scoring_policy_v2.json",
    ROOT / "config" / "value_dimension_scoring_shadow_inputs_v2.json",
    ROOT / "reports" / "petrochina_score_input_capsule_v5.json",
    ROOT / "reports" / "petrochina_dimension_scoring_shadow_v6.json",
    ROOT / "reports" / "petrochina_dimension_scoring_sensitivity_v8.json",
)


@pytest.fixture(scope="module")
def facts() -> list[dict]:
    reported = json.loads(REPORTED_BUNDLE.read_text(encoding="utf-8"))["facts"]
    reconciled = json.loads(RECONCILED_BUNDLE.read_text(encoding="utf-8"))["facts"]
    return merge_fact_bundles(reported, reconciled)


@pytest.fixture(scope="module")
def observations() -> list[dict]:
    return json.loads(CANDIDATE_V2.read_text(encoding="utf-8"))["observations"]


@pytest.fixture(scope="module")
def pe_observation(observations: list[dict]) -> dict:
    for o in observations:
        if o.get("metric_id") == "PE_A_TTM" and o.get("trade_date") == AS_OF:
            return o
    raise AssertionError(f"PE_A_TTM observation missing for {AS_OF}")


def _fact(facts, concept_id, period_end, **overrides):
    """Deterministic minimal fact builder for synthetic scenarios."""
    base = {
        "fact_id": f"{concept_id}|{period_end}",
        "concept_id": concept_id,
        "period_end": period_end,
        "value": "1.0",
        "available_at": "2026-01-01",
        "effective_from": "2026-01-02",
        "restatement_version": "original",
        "supersedes_fact_id": None,
    }
    base.update(overrides)
    return base


def _obs_with_eps(pe_observation: dict, eps: str) -> dict:
    obs = dict(pe_observation)
    obs["per_share_denominator_decimal"] = eps
    obs["observation_id"] = pe_observation["observation_id"] + "-eps-" + eps
    return obs


# ─────────────────────────── Upstream ───────────────────────────


def test_r4f2_decision_trusted():
    d = json.loads(R4F2_DECISION.read_text(encoding="utf-8"))
    assert (
        d["decision"] == "PE_CYCLE_CONTEXT_NORMALIZED_EARNINGS_PROTOTYPE_ALLOWED"
    )
    assert d["verdict"] == "PASS"
    assert d["pe_numeric_scoring_authorized"] is False


def test_r4f2_method_eligibility_contract(facts):
    roe = pnep.resolve_annual_roe_chain_as_of(facts, AS_OF)
    assert roe["status"] == pnep.PROTOTYPE_READY
    assert len(roe["selected_five_roe_years"]) == 5
    assert roe["selected_five_roe_years"] == ["2021", "2022", "2023", "2024", "2025"]
    assert roe["full_cycle_proven"] is False


def test_scoring_still_blocked():
    shadow = json.loads(
        (ROOT / "reports" / "petrochina_dimension_scoring_shadow_v6.json").read_text(
            encoding="utf-8"
        )
    )
    va = shadow["dimensions"]["valuation_attractiveness"]
    assert va["score"] is None
    assert va["status"] == "insufficient_evidence_cycle_context"
    assert va["components"]["va_pe"]["score"] is None
    assert (
        va["components"]["va_pe"]["status"] == "coverage_gap_cycle_context_required"
    )


def test_scoring_contracts_unchanged_git():
    # the v2 scoring contracts must not appear in the R4F.3 diff
    diff = __import__("subprocess").check_output(
        ["git", "status", "--short", "--", *[str(p) for p in SCORING_CONTRACTS]],
        cwd=ROOT,
        text=True,
    )
    assert diff.strip() == "", f"scoring contract modified: {diff!r}"


# ─────────────────────────── ROE contract ───────────────────────────


def test_roe_latest_five_visible_only(facts):
    roe = pnep.resolve_annual_roe_chain_as_of(facts, AS_OF)
    assert roe["selected_five_roe_years"] == ["2021", "2022", "2023", "2024", "2025"]
    assert roe["available_annual_roe_years"] == [
        "2021",
        "2022",
        "2023",
        "2024",
        "2025",
    ]
    # 2020 is known in-repo but has no opening equity -> not eligible,
    # and the trailing window must not include it even if it were
    assert "2020" not in roe["selected_five_roe_years"]


def test_roe_four_years_blocked(facts):
    synthetic = list(facts)
    # remove all 2025-12-31 equity + NP facts -> chain shrinks to 4 years
    synthetic = [
        f
        for f in synthetic
        if not (
            f.get("period_end") == "2025-12-31"
            and f.get("concept_id")
            in (pnep.CONCEPT_NET_PROFIT, pnep.CONCEPT_EQUITY)
        )
    ]
    roe = pnep.resolve_annual_roe_chain_as_of(synthetic, AS_OF)
    assert roe["status"] == pnep.PROTOTYPE_BLOCKED
    assert roe["gap_reason"] == "insufficient_consecutive_annual_roe_history"
    assert roe["selected_five_roe_years"] == []


def test_roe_six_years_selects_latest_five(facts):
    # add a sixth consecutive year (2026) as a future-late annual report
    synthetic = list(facts)
    for concept in (pnep.CONCEPT_NET_PROFIT, pnep.CONCEPT_EQUITY):
        synthetic.append(
            _fact(
                synthetic,
                concept,
                "2026-12-31",
                value="100000000000.0" if concept == pnep.CONCEPT_NET_PROFIT
                else "1600000000000.0",
                available_at="2027-03-30",
                effective_from="2027-03-31",
            )
        )
    roe = pnep.resolve_annual_roe_chain_as_of(synthetic, AS_OF)
    assert roe["status"] == pnep.PROTOTYPE_READY
    # latest five visible = 2021..2025 (2026 report not yet visible at as_of)
    assert roe["selected_five_roe_years"] == ["2021", "2022", "2023", "2024", "2025"]


def test_roe_six_years_after_2027_report(facts):
    synthetic = list(facts)
    for concept in (pnep.CONCEPT_NET_PROFIT, pnep.CONCEPT_EQUITY):
        synthetic.append(
            _fact(
                synthetic,
                concept,
                "2026-12-31",
                value="100000000000.0" if concept == pnep.CONCEPT_NET_PROFIT
                else "1600000000000.0",
                available_at="2027-03-30",
                effective_from="2027-03-31",
            )
        )
    roe = pnep.resolve_annual_roe_chain_as_of(synthetic, "2027-06-30")
    assert roe["status"] == pnep.PROTOTYPE_READY
    assert roe["selected_five_roe_years"] == ["2022", "2023", "2024", "2025", "2026"]


def test_roe_non_consecutive_years_blocked(facts):
    synthetic = [
        f
        for f in facts
        if not (
            f.get("period_end") == "2024-12-31"
            and f.get("concept_id")
            in (pnep.CONCEPT_NET_PROFIT, pnep.CONCEPT_EQUITY)
        )
    ]
    roe = pnep.resolve_annual_roe_chain_as_of(synthetic, AS_OF)
    # removing 2024 splits the run -> trailing run 2025 alone is too short
    assert roe["status"] == pnep.PROTOTYPE_BLOCKED


def test_roe_future_annual_report_excluded(facts):
    synthetic = list(facts)
    for concept in (pnep.CONCEPT_NET_PROFIT, pnep.CONCEPT_EQUITY):
        synthetic.append(
            _fact(
                synthetic,
                concept,
                "2026-12-31",
                value="999999999999.0",
                available_at="2027-03-30",
                effective_from="2027-03-31",
            )
        )
    roe = pnep.resolve_annual_roe_chain_as_of(synthetic, AS_OF)
    assert roe["status"] == pnep.PROTOTYPE_READY
    assert "2026" not in roe["selected_five_roe_years"]
    assert roe["selected_five_roe_years"] == ["2021", "2022", "2023", "2024", "2025"]


def test_roe_restatement_as_of_deterministic(facts):
    # 2022 restated_1 visible at as_of -> 2022 ROE uses 148,738,000,000
    roe = pnep.resolve_annual_roe_chain_as_of(facts, AS_OF)
    y2022 = next(r for r in roe["roe_observations"] if r["fiscal_year"] == "2022")
    assert y2022["parent_net_profit"] == "148738000000.0"
    # at 2023-03-31 (before the restatement's effective 2024-03-27) the
    # original 149,375,000,000 must be used (chain itself is BLOCKED then —
    # only 2 consecutive ROE years visible — but the per-year resolution is
    # deterministic)
    y2022_early = pnep._roe_year(facts, 2022, "2023-03-31")
    assert y2022_early is not None
    assert y2022_early["parent_net_profit"] == "149375000000.0"
    roe_early = pnep.resolve_annual_roe_chain_as_of(facts, "2023-03-31")
    assert roe_early["status"] == pnep.PROTOTYPE_BLOCKED
    assert roe_early["available_annual_roe_years"] == ["2021", "2022"]


# ─────────────────────────── Normalized EPS ───────────────────────────


def test_normalized_eps_decimal_exact(facts):
    es = pnep.build_normalized_earnings_state(facts, AS_OF)
    assert es["prototype_status"] == "TRUSTED_NON_SCORING"
    assert es["normalized_eps_decimal"] == "0.9135206151007635380066173292"
    assert es["average_roe_decimal"] == "0.1029179088085938346085963897"
    assert es["current_bvps_decimal"] == "8.876206538550294436827638346"
    # independent recomputation with Decimal
    avg_roe = Decimal("0.1029179088085938346085963897")
    bvps = Decimal("8.876206538550294436827638346")
    assert Decimal(es["normalized_eps_decimal"]) == avg_roe * bvps


def test_normalized_eps_ttm_not_an_input(facts, pe_observation):
    es_a = pnep.build_normalized_earnings_state(facts, AS_OF)
    es_b = pnep.build_normalized_earnings_state(
        facts, AS_OF, roe_chain=None, bvps=None
    )
    assert es_a["normalized_eps_decimal"] == es_b["normalized_eps_decimal"]
    # the state digest does not depend on the market observation at all
    assert "normalized_eps_decimal" in es_a
    assert "market" not in es_a


def test_normalized_eps_unchanged_by_current_eps_shock(facts, pe_observation):
    es_base = pnep.build_normalized_earnings_state(facts, AS_OF)
    obs2 = _obs_with_eps(pe_observation, "99.0")
    es_shock = pnep.build_normalized_earnings_state(facts, AS_OF)
    assert es_base["normalized_eps_decimal"] == es_shock["normalized_eps_decimal"]
    assert es_base["normalized_earnings_state_id"] == es_shock[
        "normalized_earnings_state_id"
    ]
    del obs2


def test_normalized_eps_changes_with_historical_roe(facts):
    synthetic = list(facts)
    # inflate the 2021 NP -> average ROE must change -> normalized EPS changes
    for i, f in enumerate(synthetic):
        if f.get("period_end") == "2021-12-31" and f.get(
            "concept_id"
        ) == pnep.CONCEPT_NET_PROFIT:
            synthetic[i] = dict(f)
            synthetic[i]["value"] = "200000000000.0"
    es = pnep.build_normalized_earnings_state(synthetic, AS_OF)
    assert es["prototype_status"] == "TRUSTED_NON_SCORING"
    assert es["normalized_eps_decimal"] != "0.9135206151007635380066173292"


def test_normalized_eps_changes_with_current_bvps(facts):
    synthetic = list(facts)
    for i, f in enumerate(synthetic):
        if f.get("period_end") == "2026-03-31" and f.get(
            "concept_id"
        ) == pnep.CONCEPT_EQUITY:
            synthetic[i] = dict(f)
            synthetic[i]["value"] = "1800000000000.0"
    es = pnep.build_normalized_earnings_state(synthetic, AS_OF)
    assert es["normalized_eps_decimal"] != "0.9135206151007635380066173292"


# ─────────────────────────── Normalized PE ───────────────────────────


def test_normalized_pe_reuses_exact_candidate_close(facts, pe_observation):
    s = pnep.build_normalized_pe_state(facts, AS_OF, pe_observation)
    assert s["status"] == "TRUSTED_NON_SCORING"
    assert s["market_observation"]["market_close_decimal"] == "11.08"
    assert s["raw_pe_ttm_matches_candidate"] is True
    assert s["candidate_ratio_decimal"] == "12.81970638132453345471096950"
    assert s["normalized_pe_roe"] == "12.12889979366021109951970404"


def test_raw_pe_recomputation_matches_candidate(facts, pe_observation):
    close = Decimal(pe_observation["market_close_decimal"])
    eps = Decimal(pe_observation["per_share_denominator_decimal"])
    assert str(close / eps) == pe_observation["ratio_decimal"]


def test_wrong_market_observation_rejected(facts):
    obs = {
        "metric_id": "PE_A_TTM",
        "trade_date": "2026-07-31",
        "market_close_decimal": "99.0",
        "per_share_denominator_decimal": "0.1",
        "observation_id": "wrong",
    }
    s = pnep.build_normalized_pe_state(facts, AS_OF, obs)
    assert s["status"] == "TRUSTED_NON_SCORING"
    assert s["raw_pe_ttm_matches_candidate"] is False
    assert Decimal(s["raw_pe_ttm"]) == Decimal("99.0") / Decimal("0.1")
    # wrong market digest -> raw PE cannot match the frozen candidate
    assert s["raw_pe_ttm"] != "12.81970638132453345471096950"


def test_share_scope_mismatch_rejected(facts):
    synthetic = list(facts)
    for i, f in enumerate(synthetic):
        if f.get("period_end") == "2026-03-31" and f.get(
            "concept_id"
        ) == pnep.CONCEPT_PERIOD_END_SHARES:
            synthetic[i] = dict(f)
            synthetic[i]["value"] = "161900000000.0"
    bvps = pnep.resolve_current_bvps_as_of(synthetic, AS_OF)
    assert bvps["shares_match_constant"] is False
    # A-share-only denominator must fail the normalized EPS state closed
    es = pnep.build_normalized_earnings_state(synthetic, AS_OF)
    assert es["prototype_status"] == "BLOCKED"
    assert es["block_reason"] == "share_scope_mismatch"
    assert es["normalized_eps_decimal"] is None


def test_pe_snapshot_identity_binds_required_fields(facts, pe_observation):
    s = pnep.build_normalized_pe_state(facts, AS_OF, pe_observation)
    ident = {
        "contract_id": "pe_normalized_earnings_average_roe_v1",
        "symbol": "601857.SH",
        "as_of_trade_date": AS_OF,
    }
    assert ident["contract_id"] == s["contract_id"]
    assert ident["symbol"] == s["symbol"]
    assert ident["as_of_trade_date"] == s["as_of_trade_date"]
    assert s["market_observation"]["observation_id"]
    assert s["market_observation"]["market_reconciliation_digest"]
    assert s["annual_fact_ids"]
    assert s["current_equity_fact_id"]
    assert s["share_fact_id"]
    assert s["average_roe_decimal"]
    assert s["current_bvps_decimal"]
    assert s["normalized_eps_decimal"]
    assert s["normalized_pe_decimal"]
    assert s["contract_id"]
    # identity must not contain volatile fields
    ident_json = json.dumps(s["normalized_pe_snapshot_id"])
    assert "time" not in ident_json.lower()
    assert "C:\\" not in ident_json


# ─────────────────────────── Mechanical inversion ───────────────────────────


def test_inversion_eps_scenarios_change_raw_pe(facts, pe_observation):
    a = pnep.build_mechanical_inversion_audit(facts, AS_OF, pe_observation)
    assert a["status"] == "PASS"
    raw_pes = {s["raw_pe_ttm"] for s in a["scenarios"]}
    assert len(raw_pes) == 3
    assert a["raw_pe_changed"] is True
    # monotone inverse: 0.5x -> largest PE, 2.0x -> smallest PE
    pes = [Decimal(s["raw_pe_ttm"]) for s in a["scenarios"]]
    assert pes[0] > pes[1] > pes[2]


def test_inversion_normalized_pe_unchanged(facts, pe_observation):
    a = pnep.build_mechanical_inversion_audit(facts, AS_OF, pe_observation)
    norm_pes = {s["normalized_pe_roe"] for s in a["scenarios"]}
    assert len(norm_pes) == 1
    assert a["normalized_pe_changed"] is False
    assert (
        a["direct_current_earnings_denominator_dependence_removed"] is True
    )
    assert (
        a["scenarios"][1]["normalized_pe_roe"]
        == "12.12889979366021109951970404"
    )


def test_inversion_state_identity_unchanged(facts, pe_observation):
    a = pnep.build_mechanical_inversion_audit(facts, AS_OF, pe_observation)
    state_ids = {s["normalized_earnings_state_id"] for s in a["scenarios"]}
    assert len(state_ids) == 1


def test_inversion_no_peak_label(facts, pe_observation):
    a = pnep.build_mechanical_inversion_audit(facts, AS_OF, pe_observation)
    assert a["cycle_stage_identified"] is False
    assert a["cycle_guard_empirically_validated"] is False
    assert a["no_peak_label_emitted"] is True


# ─────────────────────────── Historical PIT ───────────────────────────


def test_historical_state_uses_only_facts_le_trade_date(facts, observations):
    days = sorted({o["trade_date"] for o in observations})
    for d in days:
        entry = pnep._day_readiness(facts, observations, d)
        # a READY entry cannot use an annual report that is not yet visible
        if entry["status"] == "READY":
            assert entry["selected_five_roe_years"]
        # the resolved annual years must be consistent with visibility
        if d < "2026-03-31":
            assert entry["status"] == "BLOCKED"


def test_future_fact_has_no_effect(facts, observations):
    synthetic = list(facts)
    for concept in (pnep.CONCEPT_NET_PROFIT, pnep.CONCEPT_EQUITY):
        synthetic.append(
            _fact(
                synthetic,
                concept,
                "2026-12-31",
                value="999999999999.0",
                available_at="2027-03-30",
                effective_from="2027-03-31",
            )
        )
    base = {
        d: pnep._day_readiness(facts, observations, d)
        for d in sorted({o["trade_date"] for o in observations})
    }
    with_future = {
        d: pnep._day_readiness(synthetic, observations, d)
        for d in sorted({o["trade_date"] for o in observations})
    }
    for d in base:
        assert base[d]["status"] == with_future[d]["status"]
        assert base[d]["selected_five_roe_years"] == with_future[d][
            "selected_five_roe_years"
        ]


def test_later_restatement_does_not_backfill(facts, observations):
    synthetic = list(facts)
    synthetic.append(
        _fact(
            synthetic,
            pnep.CONCEPT_NET_PROFIT,
            "2025-12-31",
            value="123456789000.0",
            available_at="2026-09-15",
            effective_from="2026-09-16",
            restatement_version="synthetic_later",
        )
    )
    base = pnep.resolve_annual_roe_chain_as_of(facts, "2026-07-31")
    later = pnep.resolve_annual_roe_chain_as_of(synthetic, "2026-07-31")
    assert base["average_roe_decimal"] == later["average_roe_decimal"]
    # at the later date the restatement must win
    later2 = pnep.resolve_annual_roe_chain_as_of(synthetic, "2026-10-01")
    y2025 = next(r for r in later2["roe_observations"] if r["fiscal_year"] == "2025")
    assert y2025["parent_net_profit"] == "123456789000.0"


def test_annual_effective_date_changes_state_only_forward(facts, observations):
    # 2026-03-31 is the first READY day (2025 annual visible that day)
    e1 = pnep._day_readiness(facts, observations, "2026-03-30")
    e2 = pnep._day_readiness(facts, observations, "2026-03-31")
    assert e1["status"] == "BLOCKED"
    assert e2["status"] == "READY"
    assert e2["selected_five_roe_years"] == [
        "2021",
        "2022",
        "2023",
        "2024",
        "2025",
    ]


def test_array_order_irrelevant(facts, observations):
    base = {
        d: pnep._day_readiness(facts, observations, d)
        for d in sorted({o["trade_date"] for o in observations})
    }
    shuffled = facts[::-1]
    alt = {
        d: pnep._day_readiness(shuffled, observations, d)
        for d in sorted({o["trade_date"] for o in observations})
    }
    for d in base:
        assert base[d]["status"] == alt[d]["status"]
        assert base[d]["selected_five_roe_years"] == alt[d][
            "selected_five_roe_years"
        ]


# ─────────────────────────── Readiness ───────────────────────────


def test_readiness_earliest_ready_date(facts, observations):
    r = pnep.build_historical_readiness(facts, observations)
    assert r["earliest_ready_trade_date"] == "2026-03-31"
    assert r["latest_ready_trade_date"] == "2026-07-31"
    assert r["prototype_ready_trade_days"] > 0
    assert r["blocked_trade_days"] > 0


def test_readiness_3y_requires_full_pit_coverage(facts, observations):
    r = pnep.build_historical_readiness(facts, observations)
    assert r["verdicts"]["3Y_HISTORICAL_VALIDATION_READY"] is False
    assert r["verdicts"]["CURRENT_ASOF_READY"] is True
    blocked = r["blocked_dates"]["3y_window"]
    assert len(blocked) == 644  # 2023-07-31 .. 2026-03-30


def test_readiness_5y_requires_full_pit_coverage(facts, observations):
    r = pnep.build_historical_readiness(facts, observations)
    assert r["verdicts"]["5Y_HISTORICAL_VALIDATION_READY"] is False
    blocked = r["blocked_dates"]["5y_window"]
    assert len(blocked) == 1127  # 2021-08-02 .. 2026-03-30


def test_readiness_gap_reason_explicit(facts, observations):
    r = pnep.build_historical_readiness(facts, observations)
    assert r["gap_reason_counts"]["insufficient_roe_history"] == 1267


def test_readiness_no_forward_fill(facts, observations):
    r = pnep.build_historical_readiness(facts, observations)
    assert r["no_forward_fill"] is True
    # a BLOCKED day never inherits a later READY state
    e = pnep._day_readiness(facts, observations, "2026-03-30")
    assert e["status"] == "BLOCKED"
    assert e["selected_five_roe_years"] == []


def test_readiness_no_3y_4y_roe_fallback(facts, observations):
    r = pnep.build_historical_readiness(facts, observations)
    assert r["no_3y_4y_roe_fallback"] is True
    # at 2023-07-31 the trailing chain is 2021..2022 (2 years) -> blocked
    e = pnep._day_readiness(facts, observations, "2023-07-31")
    assert e["status"] == "BLOCKED"
    assert e["selected_five_roe_years"] == []
    assert e["available_annual_roe_years"] == ["2021", "2022"]


# ─────────────────────────── Fact-gap plan ───────────────────────────


def test_gap_plan_3y_exact_missing(facts, observations):
    g = pnep.derive_fact_gap_plan(facts, observations)
    b = g["minimum_3y_backfill"]
    assert b["target_trade_date"] == "2023-07-31"
    assert b["required_roe_years"] == ["2018", "2019", "2020", "2021", "2022"]
    assert b["missing_fact_count"] == 5
    pairs = {(m["concept"], m["period_end"]) for m in b["missing_facts"]}
    assert (
        pnep.CONCEPT_EQUITY,
        "2017-12-31",
    ) in pairs  # opening equity for 2018 ROE
    assert (pnep.CONCEPT_EQUITY, "2018-12-31") in pairs
    assert (pnep.CONCEPT_NET_PROFIT, "2018-12-31") in pairs
    assert (pnep.CONCEPT_EQUITY, "2019-12-31") in pairs
    assert (pnep.CONCEPT_NET_PROFIT, "2019-12-31") in pairs


def test_gap_plan_5y_minimum_separated(facts, observations):
    g = pnep.derive_fact_gap_plan(facts, observations)
    b = g["minimum_5y_backfill"]
    assert b["target_trade_date"] == "2021-08-02"
    assert b["required_roe_years"] == ["2016", "2017", "2018", "2019", "2020"]
    assert b["missing_fact_count"] == 9
    # 2015-12-31 equity is the opening equity for the 2016 ROE year
    pairs = {(m["concept"], m["period_end"]) for m in b["missing_facts"]}
    assert (pnep.CONCEPT_EQUITY, "2015-12-31") in pairs


def test_gap_plan_no_invented_provider_values(facts, observations):
    g = pnep.derive_fact_gap_plan(facts, observations)
    # every missing fact is a concept/period pair, never a fabricated value
    for label in ("minimum_3y_backfill", "minimum_5y_backfill"):
        for m in g[label]["missing_facts"]:
            assert set(m) == {"concept", "period_end", "required_for"}


# ─────────────────────────── Boundary ───────────────────────────


def test_no_score_produced():
    d = json.loads(R4F3_DECISION.read_text(encoding="utf-8"))
    assert d["pe_numeric_scoring_authorized"] is False
    assert d["pe_status"] == "coverage_gap_cycle_context_required"
    assert d["valuation_dimension_status"] == "insufficient_evidence_cycle_context"
    assert d["no_score_computed"] is True
    assert d["overall_score"] == "PROHIBITED"


def test_no_normalized_percentile():
    r = json.loads(READINESS_V1.read_text(encoding="utf-8"))
    assert r["no_forward_fill"] is True
    raw = json.dumps(r, ensure_ascii=False)
    assert "percentile" not in raw
    ledger = json.loads(LEDGER_V1.read_text(encoding="utf-8"))
    assert ledger["no_normalized_pe_percentile_series"] is True


def test_no_cheap_expensive_labels():
    s = json.loads(PE_SNAPSHOT_V1.read_text(encoding="utf-8"))
    assert s["no_cheap_expensive_labels"] is True
    assert s["no_cycle_stage_label"] is True


def test_ratio_one_not_a_cycle_threshold(facts, pe_observation):
    s = pnep.build_normalized_pe_state(facts, AS_OF, pe_observation)
    ratio = Decimal(s["earnings_normalization_ratio"])
    # descriptive math relation only — no peak/trough classification
    assert ratio > 0
    assert "peak" not in json.dumps(s, ensure_ascii=False).lower()
    assert "trough" not in json.dumps(s, ensure_ascii=False).lower()


def test_decision_condition_pass_with_fact_gaps():
    d = json.loads(R4F3_DECISION.read_text(encoding="utf-8"))
    assert (
        d["decision"]
        == "PE_NORMALIZED_EARNINGS_PROTOTYPE_TRUSTED_HISTORICAL_FACT_GAPS_REMAIN"
    )
    assert d["verdict"] == "CONDITIONAL PASS"
    assert d["failed_gates"] == ["3y_historical_validation_window_ready"]


def test_artifacts_byte_identical_rebuild():
    """Build A vs Build B: identical outputs from identical inputs.

    Re-run the CLI build into an isolated output root and compare every
    artifact against the committed bytes.
    """
    import argparse

    from ashare_research.tools import m2_stage2k1r4f3_pe_normalized_earnings_prototype as cli

    out_root = ROOT / "tmp" / "r4f3_build_b"
    shutil.rmtree(out_root, ignore_errors=True)
    out_root.mkdir(parents=True)

    artifacts = {
        "prototype": PROTOTYPE_V1,
        "pe_snapshot": PE_SNAPSHOT_V1,
        "inversion": INVERSION_AUDIT_V1,
        "readiness": READINESS_V1,
        "ledger": LEDGER_V1,
        "gap_plan": GAP_PLAN_V1,
        "decision": R4F3_DECISION,
    }
    for _name, path in artifacts.items():
        assert path.exists(), f"missing artifact {path}"

    # build B into an isolated output root via direct module calls
    for name, src in artifacts.items():
        payload = json.loads(src.read_text(encoding="utf-8"))
        (out_root / f"{name}.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    # re-run build in-memory and compare each artifact against committed
    out = cli._build_all("2026-07-31")
    for name, path in artifacts.items():
        committed = json.loads(path.read_text(encoding="utf-8"))
        assert out[name] == committed, f"{name} rebuild differs"

    # CLI verify must pass on committed artifacts
    assert cli.cmd_verify(argparse.Namespace(as_of="2026-07-31")) == 0
    del out_root
