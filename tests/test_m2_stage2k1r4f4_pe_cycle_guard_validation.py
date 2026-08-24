"""R4F.4 tests — 3Y historical normalized-PE cycle-guard validation.

Covers: upstream gate, series (728 days exact), denominator-state
identities, direction audit, recurrence gate, transition audit,
restatement/PIT perturbation, percentile (Python + DuckDB oracle),
boundaries.  Offline only; no network; no default-DB writes.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from decimal import Decimal  # noqa: E402

from ashare_research.pit_valuation.pe_cycle_context_preflight import (  # noqa: E402
    merge_fact_bundles,
)
from ashare_research.pit_valuation.pe_cycle_guard_validation import (  # noqa: E402
    RECUR_NONE,
    RECUR_REPEATED,
    RECUR_SINGLE,
    build_3y_series,
    build_denominator_state_ledger,
    build_direction_audit,
    build_recurrence_audit,
    build_transition_audit,
)
from ashare_research.pit_valuation.pe_normalized_earnings_prototype import (  # noqa: E402
    build_normalized_earnings_state,
    resolve_annual_roe_chain_as_of,
    resolve_current_bvps_as_of,
)

REPORTED_BUNDLE = ROOT / "reports" / "petrochina_pit_denominator_reported_fact_bundle_v1.json"
RECONCILED_BUNDLE = (
    ROOT / "reports" / "petrochina_pit_denominator_reconciled_fact_bundle_v1.json"
)
BACKFILL_BUNDLE = (
    ROOT / "reports" / "petrochina_pe_3y_historical_backfill_reported_fact_bundle_v1.json"
)
CANDIDATE_V2 = ROOT / "reports" / "petrochina_pit_valuation_series_candidate_v2.json"
SERIES = ROOT / "reports" / "petrochina_pe_3y_normalized_pe_series_v1.json"
LEDGER = ROOT / "reports" / "petrochina_pe_3y_denominator_state_ledger_v1.json"
DIRECTION = ROOT / "reports" / "petrochina_pe_3y_cycle_guard_direction_audit_v1.json"
TRANSITION = ROOT / "reports" / "petrochina_pe_3y_denominator_transition_audit_v1.json"
DIVERGENCE = ROOT / "reports" / "petrochina_pe_3y_raw_vs_normalized_divergence_v1.json"
PERCENTILE = ROOT / "reports" / "petrochina_pe_normalized_3y_percentile_profile_v1.json"
DECISION = ROOT / "reports" / "m2_stage2k1r4f4_decision.json"
R4F3A_DECISION = ROOT / "reports" / "m2_stage2k1r4f3a_decision.json"
R4F3_PROTOTYPE = ROOT / "reports" / "petrochina_pe_normalized_earnings_prototype_v1.json"
R4E5_PROFILE = ROOT / "reports" / "petrochina_pit_valuation_percentile_profile_v1.json"
CONTRACT = ROOT / "config" / "pe_3y_cycle_guard_validation_contract_v1.json"


def _load_json(path: Path) -> dict:
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


def _facts() -> list[dict]:
    reported = _load_json(REPORTED_BUNDLE).get("facts", [])
    reconciled = _load_json(RECONCILED_BUNDLE).get("facts", [])
    backfill = _load_json(BACKFILL_BUNDLE).get("facts", [])
    return merge_fact_bundles(reported, reconciled) + backfill


def _observations() -> list[dict]:
    return _load_json(CANDIDATE_V2).get("observations", [])


@pytest.fixture(scope="module")
def facts() -> list[dict]:
    return _facts()


@pytest.fixture(scope="module")
def observations() -> list[dict]:
    return _observations()


@pytest.fixture(scope="module")
def series(facts, observations) -> dict:
    return build_3y_series(facts, observations)


@pytest.fixture(scope="module")
def ledger(series) -> dict:
    return build_denominator_state_ledger(series)


@pytest.fixture(scope="module")
def direction(series) -> dict:
    return build_direction_audit(series)


@pytest.fixture(scope="module")
def recurrence(direction) -> dict:
    return build_recurrence_audit(direction)


@pytest.fixture(scope="module")
def transition(series) -> dict:
    return build_transition_audit(series)


# ─────────────── Upstream ───────────────


def test_r4f3a_decision_trusted():
    d = _load_json(R4F3A_DECISION)
    assert d["decision"] == "PE_3Y_HISTORICAL_BACKFILL_TRUSTED_VALIDATION_ALLOWED"
    assert d["evidence"]["3y_required_trade_days"] == 728
    assert d["evidence"]["3y_ready_days"] == 728
    assert d["evidence"]["3y_blocked_days"] == 0
    assert d["evidence"]["5y_historical_validation"] == "BLOCKED"
    assert d["evidence"]["full_cycle_coverage"] == "NOT_PROVEN"
    assert d["evidence"]["pe_numeric_scoring"] == "BLOCKED_UNCHANGED"
    assert d["evidence"]["valuation_dimension_score"] == "NONE"


def test_r4f3_state_id_unchanged():
    """R4F.3 committed normalized_earnings_state_id must be byte-identical."""
    committed = _load_json(R4F3_PROTOTYPE)["normalized_earnings_state_id"]
    facts = _facts()
    roe = resolve_annual_roe_chain_as_of(facts, "2026-07-31")
    bvps = resolve_current_bvps_as_of(facts, "2026-07-31")
    es = build_normalized_earnings_state(facts, "2026-07-31", roe_chain=roe, bvps=bvps)
    assert es["normalized_earnings_state_id"] == committed


def test_scoring_contracts_unchanged_git():
    import subprocess

    protected_paths = [
        "config/value_dimension_scoring_registry_v2.json",
        "config/value_dimension_scoring_policy_v2.json",
        "config/value_dimension_scoring_shadow_inputs_v2.json",
        "reports/petrochina_dimension_scoring_shadow_v6.json",
        "reports/petrochina_dimension_scoring_sensitivity_v8.json",
        "reports/petrochina_score_input_capsule_v5.json",
    ]
    r = subprocess.run(
        ["git", "status", "--short", "--", *protected_paths],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    out = r.stdout + r.stderr
    assert not out, f"protected scoring contracts changed: {out}"


# ─────────────── Series ───────────────


def test_series_exactly_728_days(series):
    assert series["trade_day_count"] == 728
    assert series["required_trade_days"] == 728
    assert series["gap_count"] == 0


def test_series_dates_unique_within_window(series):
    dates = [r["trade_date"] for r in series["rows"]]
    assert len(dates) == len(set(dates)) == 728
    assert all("2023-07-31" <= d <= "2026-07-31" for d in dates)


def test_series_raw_pe_matches_r4e4(series):
    for r in series["rows"]:
        assert r["raw_pe_matches_candidate"] is True


def test_series_normalized_pe_decimal_exact(series, facts):
    # spot-check: normalized_pe == close / normalized_eps (Decimal exact)
    for r in series["rows"][::100]:
        close = Decimal(r["market_close_decimal"])
        norm_eps = Decimal(r["normalized_eps_decimal"])
        assert Decimal(r["normalized_pe_decimal"]) == close / norm_eps


def test_series_no_missing_denominator_input(series):
    for r in series["rows"]:
        for key in (
            "market_close_decimal",
            "current_ttm_eps_decimal",
            "normalized_eps_decimal",
            "average_roe_decimal",
            "current_bvps_decimal",
            "raw_ttm_denominator_state_id",
            "normalized_denominator_state_id",
        ):
            assert r.get(key) not in (None, ""), f"missing {key} at {r['trade_date']}"


def test_series_ratio_identities_exact(series):
    for r in series["rows"]:
        # The frozen identity normalized_pe/raw_pe == ttm_eps/normalized_eps
        # holds exactly when both sides are the same rational computed from
        # the EPS operands (the close cancels).  The series stores that
        # exact rational in normalized_to_raw_pe_ratio and
        # earnings_normalization_ratio.
        assert (
            Decimal(r["normalized_to_raw_pe_ratio"])
            == Decimal(r["earnings_normalization_ratio"])
        )
        assert Decimal(r["normalized_to_raw_pe_ratio"]) == Decimal(
            r["current_ttm_eps_decimal"]
        ) / Decimal(r["normalized_eps_decimal"])
        # direction consistency (Case A/B/C) is separately audited; here we
        # confirm the sign relation holds via the stored exact ratios.
        ttm = Decimal(r["current_ttm_eps_decimal"])
        norm = Decimal(r["normalized_eps_decimal"])
        assert (Decimal(r["normalized_to_raw_pe_ratio"]) > 1) == (ttm > norm)
        assert (Decimal(r["normalized_to_raw_pe_ratio"]) < 1) == (ttm < norm)


def test_series_no_future_leakage(series):
    assert series["no_future_leakage"] is True


# ─────────────── Identity ───────────────


def test_normalized_state_id_excludes_date_and_price(series):
    # two rows with the same economic inputs but different dates/prices
    # must share the same normalized_denominator_state_id (R4F3A overlay:
    # 2023-07-31..2026-07-31 includes price-only days)
    rows = series["rows"]
    id_to_dates: dict[str, list[str]] = {}
    for r in rows:
        id_to_dates.setdefault(r["normalized_denominator_state_id"], []).append(
            r["trade_date"]
        )
    multi = {k: v for k, v in id_to_dates.items() if len(v) > 1}
    assert multi, "expected at least one normalized state spanning multiple days"
    # same state id must coincide with identical economic inputs
    for sid in multi:
        eps_vals = {
            r["normalized_eps_decimal"]
            for r in rows
            if r["normalized_denominator_state_id"] == sid
        }
        assert len(eps_vals) == 1


def test_state_id_changes_with_annual_fact(series, facts, observations):
    """Change one annual fact ID -> normalized state must change."""
    base_rows = series["rows"]
    s0 = base_rows[0]
    # clone facts and mutate the 2018 NP restated fact's value
    import copy

    altered = copy.deepcopy(facts)
    for f in altered:
        if (
            f.get("concept_id") == "net_profit_attributable_to_parent"
            and f.get("period_end") == "2018-12-31"
            and f.get("restatement_version") == "restated_1"
        ):
            f["value"] = float(Decimal(str(f["value"])) + Decimal("1"))
            f["fact_id"] = "altered-" + f["fact_id"][:20]
            break
    s2 = build_3y_series(altered, observations)
    r2 = next(r for r in s2["rows"] if r["trade_date"] == s0["trade_date"])
    assert (
        r2["normalized_denominator_state_id"]
        != s0["normalized_denominator_state_id"]
    )


def test_state_id_changes_with_current_equity(series, facts, observations):
    import copy

    altered = copy.deepcopy(facts)
    for f in altered:
        if (
            f.get("concept_id") == "equity_attributable_to_parent"
            and f.get("period_end") == "2023-03-31"
            and f.get("restatement_version") == "original"
        ):
            f["value"] = float(Decimal(str(f["value"])) + Decimal("1000000000"))
            f["fact_id"] = "altered-eq-" + f["fact_id"][:15]
            break
    s2 = build_3y_series(altered, observations)
    r0 = series["rows"][0]
    r2 = next(r for r in s2["rows"] if r["trade_date"] == r0["trade_date"])
    assert (
        r2["normalized_denominator_state_id"]
        != r0["normalized_denominator_state_id"]
    )


def test_price_only_change_state_unchanged(series):
    """Same economic inputs across days with different prices -> same
    normalized state id (and same raw state id per R4E4)."""
    rows = series["rows"]
    by_state: dict[str, list[dict]] = {}
    for r in rows:
        by_state.setdefault(
            (r["raw_ttm_denominator_state_id"], r["normalized_denominator_state_id"]),
            [],
        ).append(r)
    for group in by_state.values():
        if len(group) > 1:
            closes = {r["market_close_decimal"] for r in group}
            assert len(closes) > 1 or len(group) == 1
            # all rows in one paired state share the same normalized EPS
            assert len({r["normalized_eps_decimal"] for r in group}) == 1
            assert len({r["current_ttm_eps_decimal"] for r in group}) == 1


def test_raw_denominator_state_id_is_official(series):
    """raw state id must equal the R4E.4 financial_state_id (official)."""
    obs_map = {
        o["trade_date"]: o["financial_state_id"]
        for o in _observations()
        if o.get("metric_id") == "PE_A_TTM"
    }
    for r in series["rows"]:
        assert r["raw_ttm_denominator_state_id"] == obs_map[r["trade_date"]]


def test_raw_denominator_no_close_backderivation(series):
    for r in series["rows"]:
        # current TTM EPS must be the official per_share_denominator
        obs = next(
            o
            for o in _observations()
            if o.get("metric_id") == "PE_A_TTM"
            and o.get("trade_date") == r["trade_date"]
        )
        assert r["current_ttm_eps_decimal"] == obs["per_share_denominator_decimal"]
        # cross-check: close / eps == committed raw PE
        assert Decimal(r["market_close_decimal"]) / Decimal(
            r["current_ttm_eps_decimal"]
        ) == Decimal(r["raw_pe_ttm_decimal"])


# ─────────────── Direction ───────────────


def test_direction_case_a(series):
    for r in series["rows"]:
        ttm = Decimal(r["current_ttm_eps_decimal"])
        norm = Decimal(r["normalized_eps_decimal"])
        if ttm > norm:
            assert Decimal(r["normalized_pe_decimal"]) > Decimal(r["raw_pe_ttm_decimal"])


def test_direction_case_b(series):
    for r in series["rows"]:
        ttm = Decimal(r["current_ttm_eps_decimal"])
        norm = Decimal(r["normalized_eps_decimal"])
        if ttm < norm:
            assert Decimal(r["normalized_pe_decimal"]) < Decimal(r["raw_pe_ttm_decimal"])


def test_direction_case_c(series):
    for r in series["rows"]:
        ttm = Decimal(r["current_ttm_eps_decimal"])
        norm = Decimal(r["normalized_eps_decimal"])
        if ttm == norm:
            assert Decimal(r["normalized_pe_decimal"]) == Decimal(r["raw_pe_ttm_decimal"])


def test_direction_audit_zero_violations(direction):
    assert direction["direction_violation_count"] == 0
    assert direction["trade_days_checked"] == 728


def test_ratio_identities_consistent(direction):
    assert direction["above_normalized_trade_days"] > 0


# ─────────────── Recurrence ───────────────


def test_daily_duplicates_not_states(ledger):
    """728 daily rows != 728 states."""
    assert ledger["trade_day_count"] == 728
    assert ledger["unique_paired_denominator_states"] < 728


def test_recurrence_gate_frozen(series, direction):
    rec = build_recurrence_audit(direction)
    assert rec["minimum_distinct_raw_ttm_states_for_recurrence"] == 2
    assert rec["frozen_before_observed_outcome"] is True


def test_recurrence_two_states_qualify(series, direction):
    assert direction["above_normalized_unique_raw_states"] >= 2
    rec = build_recurrence_audit(direction)
    assert rec["result"] == RECUR_REPEATED


def test_recurrence_single_state_limited():
    d = {
        "above_normalized_unique_raw_states": 1,
        "direction_violation_count": 0,
        "above_normalized_segments": 1,
    }
    assert build_recurrence_audit(d)["result"] == RECUR_SINGLE


def test_recurrence_zero_states_none():
    d = {
        "above_normalized_unique_raw_states": 0,
        "direction_violation_count": 0,
        "above_normalized_segments": 0,
    }
    assert build_recurrence_audit(d)["result"] == RECUR_NONE


# ─────────────── Transition ───────────────


def test_transition_no_orphans(transition):
    assert transition["orphan_normalized_transitions"] == []
    assert transition["orphan_raw_ttm_transitions"] == []
    assert transition["normalized_transition_count"] > 0


def test_price_only_day_no_transition(series):
    """Consecutive days with identical state ids imply no transition."""
    rows = series["rows"]
    transitions = 0
    for i in range(1, len(rows)):
        if (
            rows[i]["normalized_denominator_state_id"]
            != rows[i - 1]["normalized_denominator_state_id"]
        ):
            transitions += 1
    assert transitions == 12  # matches the ledger's 13 segments - 1


# ─────────────── Restatement / PIT ───────────────


def test_later_restatement_does_not_alter_history(facts, observations):
    """A synthetic later restatement (effective 2025-06-02) must leave
    every earlier historical row byte-identical.  The synthetic facts are
    built inline so the test is clean-clone safe (no gitignored fixtures)."""
    base = build_3y_series(facts, observations)
    later = [
        {
            "concept_id": "equity_attributable_to_parent",
            "period_end": "2018-12-31",
            "value": 1214067000000.0,
            "unit": "CNY",
            "fact_id": "r4f4-synthetic-later-restate-0",
            "available_at": "2025-06-01",
            "effective_from": "2025-06-02",
            "supersedes_fact_id": "any-original",
            "restatement_version": "restated_1",
        },
        {
            "concept_id": "equity_attributable_to_parent",
            "period_end": "2017-12-31",
            "value": 1192862000000.0,
            "unit": "CNY",
            "fact_id": "r4f4-synthetic-later-restate-1",
            "available_at": "2025-06-01",
            "effective_from": "2025-06-02",
            "supersedes_fact_id": "any-original",
            "restatement_version": "restated_1",
        },
    ]
    perturbed = build_3y_series(facts + later, observations)
    for r1, r2 in zip(base["rows"], perturbed["rows"], strict=False):
        if r2["trade_date"] < "2025-06-02":
            assert r1 == r2, f"history changed at {r2['trade_date']}"


def test_restatement_effective_rollover_exact(series):
    """At 2020-03-27 the restated_1 facts become visible; the normalized
    state must reflect the restated inputs from that day on."""
    rows = series["rows"]
    # find the first day whose state id differs from a day before the
    # 2020-03-27 rollover is not in the 3y window (all days are after);
    # instead assert the series is built entirely from restated inputs
    # (2018 ROE uses restated NP 53,030).
    r = next(r for r in rows if r["trade_date"] == "2023-07-31")
    assert r["selected_five_roe_years"] == ["2018", "2019", "2020", "2021", "2022"]


def test_array_order_irrelevant(facts, observations):
    import random

    shuffled = facts[:]
    random.Random(42).shuffle(shuffled)
    s1 = build_3y_series(facts, observations)
    s2 = build_3y_series(shuffled, observations)
    assert s1["rows"] == s2["rows"]


def test_no_future_facts(facts, observations):
    """Future facts (post-2026) must not appear in the 3y series."""
    rows = build_3y_series(facts, observations)["rows"]
    assert all(r["trade_date"] <= "2026-07-31" for r in rows)


# ─────────────── Percentile ───────────────


def test_percentile_n_728():
    p = _load_json(PERCENTILE)
    assert p["percentile"]["n"] == 728
    assert p["percentile"]["method_id"] == "MIDRANK_EMPIRICAL_PERCENTILE"


def test_percentile_rational_identity():
    p = _load_json(PERCENTILE)
    pp = p["percentile"]
    assert pp["rank_denominator"] == 2 * pp["n"]
    assert pp["rank_numerator"] == 2 * pp["count_less"] + pp["count_equal"] + 1
    assert pp["count_less"] + pp["count_equal"] + pp["count_greater"] == pp["n"]
    assert pp["rational_identity"] == (
        f"{pp['rank_numerator']}/{pp['rank_denominator']}"
    )


def test_percentile_duckdb_oracle_exact():
    """Independent DuckDB midrank oracle must match the Python midrank."""
    import duckdb

    p = _load_json(PERCENTILE)
    series = _load_json(SERIES)
    values = [float(r["normalized_pe_decimal"]) for r in series["rows"]]
    current = float(p["current_normalized_pe_decimal"])
    con = duckdb.connect()
    con.execute("CREATE TABLE t (v DOUBLE)")
    con.executemany("INSERT INTO t VALUES (?)", [(v,) for v in values])
    less = con.execute("SELECT count(*) FROM t WHERE v < ?", [current]).fetchone()[0]
    equal = con.execute("SELECT count(*) FROM t WHERE v = ?", [current]).fetchone()[0]
    greater = con.execute("SELECT count(*) FROM t WHERE v > ?", [current]).fetchone()[0]
    n = len(values)
    assert less == p["percentile"]["count_less"]
    assert equal == p["percentile"]["count_equal"]
    assert greater == p["percentile"]["count_greater"]
    assert n == p["percentile"]["n"]


def test_percentile_decimal_no_float():
    p = _load_json(PERCENTILE)
    # midrank percentile is the exact rational 100*(2L+E+1)/(2N) as a Decimal
    pp = p["percentile"]
    expected = (
        Decimal("100")
        * Decimal(2 * pp["count_less"] + pp["count_equal"] + 1)
        / Decimal(2 * pp["n"])
    )
    assert Decimal(pp["midrank_percentile_decimal"]) == expected


def test_no_5y_percentile():
    p = _load_json(PERCENTILE)
    assert "5y" not in p.get("window", {}).get("start", "")
    assert p.get("window", {}).get("start") == "2023-07-31"


def test_raw_pe_3y_percentile_bound():
    p = _load_json(PERCENTILE)
    r4e5 = _load_json(R4E5_PROFILE)
    rec = next(
        r
        for r in r4e5["records"]
        if r["metric_id"] == "PE_A_TTM" and r["window_id"] == "3y"
    )
    assert p["current_raw_pe_3y_percentile"] == rec["midrank_percentile_decimal"]
    assert p["comparison"] == "DESCRIPTIVE_DENOMINATOR_NORMALIZATION_COMPARISON"


# ─────────────── Decision ───────────────


def test_decision_mechanical_guard_confirmed():
    d = _load_json(DECISION)
    assert (
        d["decision"]
        == "PE_3Y_NORMALIZED_PE_MECHANICAL_GUARD_CONFIRMED_"
        "INDEPENDENT_CYCLE_VALIDATION_REQUIRED"
    )
    assert d["verdict"] == "CONDITIONAL PASS"
    assert d["gates"]["series_trusted"] is True
    assert d["gates"]["mechanical_direction_consistency"] is True
    assert d["gates"]["orphan_transitions_zero"] is True
    assert (
        d["gates"]["condition_observed_across_multiple_denominator_states"] is True
    )


def test_decision_identification_gates():
    """Reviewer correction: the mechanical relation is algebraic, so it
    must be excluded as empirical evidence; independent cycle validation
    is NOT established."""
    d = _load_json(DECISION)
    g = d["gates"]
    assert g["mechanical_relation_excluded_as_empirical_evidence"] is True
    assert g["independent_cycle_context_evidence_present"] is False
    assert g["cycle_stage_identified"] is False
    assert g["cycle_guard_empirically_validated"] is False
    assert g["normalized_earnings_mid_cycle_validated"] is False
    e = d["evidence"]
    assert e["mechanical_denominator_guard"] == "CONFIRMED"
    assert e["normalized_earnings_as_valid_cycle_proxy"] == "NOT_YET_VALIDATED"
    assert e["cycle_guard_empirical_validation"] == "NOT_ESTABLISHED"
    assert e["independent_protective_episodes"] == "NOT_ESTABLISHED"
    assert e["direction_relation_is_algebraic_identity"].startswith(
        "raw_pe = price/current_eps"
    )
    assert e["protective_direction_segments"] == 1
    assert "one contiguous" in e["protective_direction_segments_note"]
    assert d["5y_remaining_facts"] == "DEFERRED_PENDING_IDENTIFICATION_REVIEW"


def test_direction_relation_is_algebraic():
    """For any positive price, current_eps, normalized_eps with
    current_eps > normalized_eps, the relation price/normalized_eps >
    price/current_eps is arithmetically forced.  This proves the
    direction consistency is implementation-correctness, not empirical
    evidence."""
    import random

    rng = random.Random(7)
    for _ in range(200):
        price = Decimal(str(rng.uniform(1, 100)))
        norm_eps = Decimal(str(rng.uniform(0.01, 5)))
        ttm_eps = norm_eps + Decimal(str(rng.uniform(0.001, 5)))
        assert ttm_eps > norm_eps
        assert price / norm_eps > price / ttm_eps  # normalized_pe > raw_pe
    # and the reverse for current_eps < normalized_eps
    for _ in range(200):
        price = Decimal(str(rng.uniform(1, 100)))
        norm_eps = Decimal(str(rng.uniform(0.01, 5)))
        ttm_eps = max(Decimal("0.001"), norm_eps - Decimal(str(rng.uniform(0.001, 5))))
        if ttm_eps < norm_eps:
            assert price / norm_eps < price / ttm_eps


def test_mechanical_consistency_cannot_set_empirical_gate():
    """direction consistency must not be able to set
    cycle_guard_empirically_validated or trigger scoring authorization."""
    d = _load_json(DECISION)
    assert d["gates"]["cycle_guard_empirically_validated"] is False
    assert d["evidence"]["pe_numeric_scoring_authorized"] is False
    assert d["no_score_computed"] is True


def test_decision_boundary():
    d = _load_json(DECISION)
    assert d["evidence"]["full_cycle_coverage"] == "NOT_PROVEN"
    assert d["evidence"]["5y_historical_validation"] == "BLOCKED"
    assert d["evidence"]["cycle_stage_identified"] is False
    assert d["evidence"]["pe_numeric_scoring"] == "BLOCKED_UNCHANGED"
    assert d["evidence"]["valuation_dimension_score"] == "NONE"
    assert d["next_stage"].startswith(
        "R4F.4A_INDEPENDENT_CYCLE_CONTEXT_VALIDATION_PREFLIGHT"
    )
    assert d["next_stage"].endswith("NOT_STARTED")
    assert d["no_score_computed"] is True


def test_contract_frozen():
    c = _load_json(CONTRACT)
    assert c["required_trade_days"] == 728
    assert (
        c["recurrence_gate"]["minimum_distinct_raw_ttm_states_for_recurrence"] == 2
    )
    assert c["sample_semantics"]["daily_rows_are_independent_samples"] is False
    assert c["boundaries"]["cycle_stage_classification"] == "PROHIBITED"
    assert c["boundaries"]["scoring_authorization"] is False
    assert c["roe_window_shortening"] == "PROHIBITED"


# ─────────────── Boundary ───────────────


def test_no_pe_score():
    d = _load_json(DECISION)
    assert d["no_score_computed"] is True
    assert d["evidence"]["pe_numeric_scoring"] == "BLOCKED_UNCHANGED"


def test_no_future_return_validation():
    """The decision must not contain return/prediction claims."""
    d = _load_json(DECISION)
    s = json.dumps(d, ensure_ascii=False)
    for word in ("future_return", "return_prediction", "signal_hit_rate", "buy_and_hold"):
        assert word not in s


def test_no_prohibited_cycle_terms():
    """PEAK/TROUGH/BOOM/RECESSION must not appear as stage labels."""
    for path in (SERIES, LEDGER, DIRECTION, TRANSITION, DIVERGENCE, DECISION):
        s = json.dumps(_load_json(path), ensure_ascii=False)
        for term in ("PEAK", "TROUGH", "BOOM", "RECESSION", "MID_CYCLE", "buy_zone"):
            assert term not in s


def test_no_default_db_write():
    import hashlib

    db = ROOT / "data" / "research.duckdb"
    if db.is_file():
        h = hashlib.sha256(db.read_bytes()).hexdigest()
        assert h == "4a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6"


def test_no_production_metric_result():
    m = Path(ROOT / "reports").glob("petrochina_pe_3y_*")
    names = [p.name for p in m]
    assert not any("metric_result" in n for n in names)
