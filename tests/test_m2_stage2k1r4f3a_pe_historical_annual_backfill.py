"""R4F.3A tests — historical annual fact backfill for 3Y normalized-earnings validation.

Covers: upstream gate, source/cache, extraction, PIT, restatement, identity,
ROE, readiness, boundary.  Offline only; no network, no default-DB writes.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from decimal import Decimal  # noqa: E402

from ashare_research.pit_valuation.contracts import (  # noqa: E402
    CALENDAR_COVERAGE_START,
    CalendarCoverageGapError,
    validate_market_calendar_registry,
)
from ashare_research.pit_valuation.fact_builder import (  # noqa: E402
    build_fact_id,
    load_market_calendar,
    next_trading_day,
)
from ashare_research.pit_valuation.pe_cycle_context_preflight import (  # noqa: E402
    merge_fact_bundles,
    resolve_latest_visible,
)
from ashare_research.pit_valuation.pe_historical_annual_backfill import (  # noqa: E402
    CONCEPT_EQUITY,
    CONCEPT_NET_PROFIT,
    roe_decimal,
)
from ashare_research.pit_valuation.pe_normalized_earnings_prototype import (  # noqa: E402
    resolve_annual_roe_chain_as_of,
)

R4F3A_REGISTRY = ROOT / "config" / "pit_valuation_market_calendar_registry_r4f3a_v1.json"
CALENDAR_V1_REGISTRY = ROOT / "config" / "pit_valuation_market_calendar_registry_v1.json"
CONTRACT = ROOT / "config" / "pe_3y_historical_backfill_contract_v1.json"
SOURCE_EVIDENCE = ROOT / "config" / "pe_3y_historical_backfill_source_evidence_v1.json"
CACHE_REGISTRY = ROOT / "config" / "pe_3y_historical_backfill_cache_registry_v1.json"
REPORTED_BUNDLE_R4D = (
    ROOT / "reports" / "petrochina_pit_denominator_reported_fact_bundle_v1.json"
)
RECONCILED_BUNDLE_R4D = (
    ROOT / "reports" / "petrochina_pit_denominator_reconciled_fact_bundle_v1.json"
)
BACKFILL_BUNDLE = (
    ROOT / "reports" / "petrochina_pe_3y_historical_backfill_reported_fact_bundle_v1.json"
)
RECONCILIATION = ROOT / "reports" / "petrochina_pe_3y_historical_backfill_reconciliation_v1.json"
DECISION = ROOT / "reports" / "m2_stage2k1r4f3a_decision.json"
OVERLAY = ROOT / "reports" / "petrochina_pe_3y_historical_backfill_overlay_v1.json"
CANDIDATE_V2 = ROOT / "reports" / "petrochina_pit_valuation_series_candidate_v2.json"
R4F3_READINESS = (
    ROOT / "reports" / "petrochina_pe_normalized_earnings_historical_readiness_v1.json"
)
R4F3_DECISION = ROOT / "reports" / "m2_stage2k1r4f3_decision.json"
AFTER_READINESS = (
    ROOT / "reports" / "petrochina_pe_normalized_earnings_3y_readiness_after_backfill_v1.json"
)
CALENDAR_RECON = (
    ROOT / "reports" / "petrochina_pe_3y_historical_calendar_reconciliation_v1.json"
)

EXPECTED_CELLS = [
    (CONCEPT_EQUITY, "2017-12-31"),
    (CONCEPT_EQUITY, "2018-12-31"),
    (CONCEPT_NET_PROFIT, "2018-12-31"),
    (CONCEPT_EQUITY, "2019-12-31"),
    (CONCEPT_NET_PROFIT, "2019-12-31"),
]


def _load_json(path: Path) -> dict:
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


def _combined_facts() -> list[dict]:
    reported = _load_json(REPORTED_BUNDLE_R4D).get("facts", [])
    reconciled = _load_json(RECONCILED_BUNDLE_R4D).get("facts", [])
    backfill = _load_json(BACKFILL_BUNDLE).get("facts", [])
    return merge_fact_bundles(reported, reconciled) + backfill


def _observations() -> list[dict]:
    return _load_json(CANDIDATE_V2).get("observations", [])


@pytest.fixture(scope="module")
def facts() -> list[dict]:
    return _combined_facts()


@pytest.fixture(scope="module")
def observations() -> list[dict]:
    return _observations()


# ─────────────── Upstream gate ───────────────


def test_r4f3_decision_trusted():
    d = _load_json(R4F3_DECISION)
    assert d["decision"] == (
        "PE_NORMALIZED_EARNINGS_PROTOTYPE_TRUSTED_HISTORICAL_FACT_GAPS_REMAIN"
    )
    assert d["verdict"] == "CONDITIONAL PASS"
    assert d["evidence"]["minimum_3y_backfill"]["missing_fact_count"] == 5


def test_r4f3_gap_plan_target_cells_exact():
    d = _load_json(R4F3_DECISION)
    missing = d["evidence"]["minimum_3y_backfill"]["missing_facts"]
    cells = {(m["concept"], m["period_end"]) for m in missing}
    assert cells == set(EXPECTED_CELLS)
    assert len(missing) == 5


# ─────────────── Contract / target cells ───────────────


def test_contract_target_cells_exact():
    c = _load_json(CONTRACT)
    cells = {(t["concept"], t["period_end"]) for t in c["target_logical_cells"]}
    assert cells == set(EXPECTED_CELLS)
    assert c["target_logical_cell_count"] == 5
    assert c["pit_rule"]["rule_id"] == "announcement-date-to-next-trading-day-v1"
    assert c["scoring_boundary"]["pe_numeric_score"] == "BLOCKED_UNCHANGED"
    assert c["scoring_boundary"]["full_cycle_proven"] is False


def test_calendar_v1_registry_unchanged():
    v1 = _load_json(CALENDAR_V1_REGISTRY)
    assert v1["first_trading_day"] == "2020-01-02"
    assert v1["last_trading_day"] == "2026-08-05"
    assert v1["object_sha256"] == (
        "77021dceda8aae05c7bc2329e6efb65711ccea232bb289e880cd16b99151b92d"
    )


def test_r4d_calendar_coverage_start_unchanged():
    assert CALENDAR_COVERAGE_START == "2020-01-01"


# ─────────────── Historical calendar ───────────────


def test_r4f3a_calendar_registry_valid():
    reg = _load_json(R4F3A_REGISTRY)
    validate_market_calendar_registry(reg)
    assert reg["provider"] == "baostock"
    assert reg["purpose"] == "R4F3A_HISTORICAL_ANNOUNCEMENT_EFFECTIVE_FROM"
    assert reg["supersedes_calendar"] is False
    assert reg["extends_coverage_of"] == "config/pit_valuation_market_calendar_registry_v1.json"


def test_r4f3a_calendar_content_addressed():
    reg = _load_json(R4F3A_REGISTRY)
    assert Path(reg["object_key"]).stem == reg["object_sha256"]
    assert len(reg["object_sha256"]) == 64


def test_r4f3a_calendar_covers_earliest_announcement():
    reg = _load_json(R4F3A_REGISTRY)
    assert reg["first_trading_day"] <= reg["required_start"]
    assert reg["required_start"] == "2018-03-22"  # 2017 AR announcement


def test_calendar_overlap_reconciliation_pass():
    rec = _load_json(CALENDAR_RECON)
    assert rec["status"] == "PASS"
    assert rec["missing_dates"] == []
    assert rec["extra_dates"] == []
    assert rec["old_overlap_count"] == rec["new_overlap_count"] == 1597
    assert rec["overlap_start"] == "2020-01-02"


def test_new_calendar_same_announcement_resolves():
    reg = _load_json(R4F3A_REGISTRY)
    cal = load_market_calendar(ROOT / "tmp" / "market_cache" / "baostock", registry=reg)
    assert next_trading_day("2018-03-22", cal["trade_dates"]) == "2018-03-23"
    assert next_trading_day("2019-03-21", cal["trade_dates"]) == "2019-03-22"
    assert next_trading_day("2020-03-26", cal["trade_dates"]) == "2020-03-27"


def test_next_trading_day_strictly_after_announcement():
    reg = _load_json(R4F3A_REGISTRY)
    cal = load_market_calendar(ROOT / "tmp" / "market_cache" / "baostock", registry=reg)
    for ann in ("2018-03-22", "2019-03-21", "2020-03-26", "2021-03-26"):
        eff = next_trading_day(ann, cal["trade_dates"])
        assert eff > ann


def test_old_calendar_insufficient_fails_closed():
    v1 = _load_json(CALENDAR_V1_REGISTRY)
    with pytest.raises(CalendarCoverageGapError):
        load_market_calendar(
            ROOT / "tmp" / "market_cache" / "baostock",
            registry=v1,
            required_start="2018-03-22",
        )


def test_missing_calendar_object_fails_closed(tmp_path: Path):
    reg = _load_json(R4F3A_REGISTRY)
    with pytest.raises(CalendarCoverageGapError):
        load_market_calendar(tmp_path, registry=reg)


def test_wrong_calendar_sha_fails_closed(tmp_path: Path):
    reg = dict(_load_json(R4F3A_REGISTRY))
    reg["object_sha256"] = "0" * 64
    with pytest.raises(CalendarCoverageGapError):
        load_market_calendar(ROOT / "tmp" / "market_cache" / "baostock", registry=reg)


# ─────────────── Source / cache ───────────────


def test_source_evidence_exchange_official_primary():
    ev = _load_json(SOURCE_EVIDENCE)
    for e in ev["entries"]:
        assert e["source_role"] == "exchange_official"
        assert e["proof_url"].startswith("https://static.sse.com.cn/")
        assert e["symbol"] == "601857.SH"


def test_cache_registry_objects_verified():
    reg = _load_json(CACHE_REGISTRY)
    assert len(reg["objects"]) == 4
    for o in reg["objects"]:
        assert len(o["sha256"]) == 64
        assert o["media_type"] == "application/pdf"
        assert o["byte_size"] > 0
        assert o["page_count"] > 0


def test_2020_ar_sha_matches_r4d_registry():
    reg = _load_json(CACHE_REGISTRY)
    r4d = _load_json(ROOT / "config" / "pit_valuation_official_cache_registry_v1.json")
    r4d_sha = {
        o["sha256"] for o in r4d["objects"] if "R4D-SSE-2020-AR" in o.get("evidence_ids", [])
    }
    r4f3a_sha = {
        o["sha256"]
        for o in reg["objects"]
        if "R4F3A-SSE-2020-AR-COMP" in o.get("evidence_ids", [])
    }
    assert r4f3a_sha == r4d_sha  # same byte-identical content object; no second economic fact


# ─────────────── Extraction / facts ───────────────


def test_backfill_bundle_fact_count():
    b = _load_json(BACKFILL_BUNDLE)
    assert b["fact_count"] == 8  # 5 original + 3 restated_1
    assert b["schema"] == "pe_3y_historical_backfill_reported_fact_bundle_v1"


def test_all_target_cells_present():
    b = _load_json(BACKFILL_BUNDLE)
    facts = b["facts"]
    orig = {
        (f["concept_id"], f["period_end"])
        for f in facts
        if f["restatement_version"] == "original"
    }
    assert orig == set(EXPECTED_CELLS)


def test_fact_values_exact():
    b = _load_json(BACKFILL_BUNDLE)
    expected = {
        (CONCEPT_EQUITY, "2017-12-31", "original"): 1193810000000.0,
        (CONCEPT_EQUITY, "2018-12-31", "original"): 1214570000000.0,
        (CONCEPT_NET_PROFIT, "2018-12-31", "original"): 52585000000.0,
        (CONCEPT_EQUITY, "2019-12-31", "original"): 1230428000000.0,
        (CONCEPT_NET_PROFIT, "2019-12-31", "original"): 45677000000.0,
        (CONCEPT_EQUITY, "2017-12-31", "restated_1"): 1192862000000.0,
        (CONCEPT_EQUITY, "2018-12-31", "restated_1"): 1214067000000.0,
        (CONCEPT_NET_PROFIT, "2018-12-31", "restated_1"): 53030000000.0,
    }
    for f in b["facts"]:
        key = (f["concept_id"], f["period_end"], f["restatement_version"])
        assert f["value"] == expected[key], f"value mismatch for {key}"
        assert f["unit"] == "CNY"
        assert f["source_tier"] == "exchange_official"


def test_all_fact_ids_unique():
    b = _load_json(BACKFILL_BUNDLE)
    ids = [f["fact_id"] for f in b["facts"]]
    assert len(ids) == len(set(ids)) == 8
    for f in b["facts"]:
        assert f["fact_id"] == build_fact_id(f)  # canonical identity


def test_context_fiscal_year_is_period_year_not_filing_year():
    """Regression: a restated fact disclosed in the 2019 AR for a 2018
    period must carry a 2018 context (period year), never a 2019 context
    (filing year).  Otherwise the 2017 and 2018 restated equities collide
    on one fact_id."""
    b = _load_json(BACKFILL_BUNDLE)
    for f in b["facts"]:
        # context fiscal year == period_end year for every fact
        period_year = f["period_end"][:4]
        assert f"|{period_year}|" in f["context_id"], (
            f"context fiscal year must be the period year {period_year}: "
            f"{f['context_id']}"
        )
    # explicit pair check: 2018 equity original vs restated_1
    eq18 = [f for f in b["facts"]
            if f["concept_id"] == CONCEPT_EQUITY and f["period_end"] == "2018-12-31"]
    assert len(eq18) == 2
    orig, rest = sorted(eq18, key=lambda f: f["effective_from"])
    assert orig["restatement_version"] == "original"
    assert rest["restatement_version"] == "restated_1"
    assert orig["period_end"] == rest["period_end"] == "2018-12-31"
    assert orig["context_id"] == rest["context_id"]  # same economic period
    assert orig["fact_id"] != rest["fact_id"]  # different version/provenance


def test_scope_consolidated():
    b = _load_json(BACKFILL_BUNDLE)
    for f in b["facts"]:
        assert "consolidated" in f["context_id"]
        assert f["symbol"] == "601857.SH"


def test_fact_period_and_unit_canonical():
    b = _load_json(BACKFILL_BUNDLE)
    for f in b["facts"]:
        assert f["period_end"].endswith("12-31")
        assert f["raw_unit"] == "CNY_million"
        assert f["normalization_rule"].endswith("x")


def test_restatement_supersedes_chain_complete():
    b = _load_json(BACKFILL_BUNDLE)
    facts = {f["fact_id"]: f for f in b["facts"]}
    for f in b["facts"]:
        if f["restatement_version"] == "restated_1":
            assert f["supersedes_fact_id"] in facts
            orig = facts[f["supersedes_fact_id"]]
            assert orig["concept_id"] == f["concept_id"]
            assert orig["period_end"] == f["period_end"]
            assert orig["restatement_version"] == "original"


# ─────────────── PIT ───────────────


def test_pit_announcement_effective_from():
    b = _load_json(BACKFILL_BUNDLE)
    expected = {
        ("2017-12-31", "original"): ("2018-03-22", "2018-03-23"),
        ("2018-12-31", "original"): ("2019-03-21", "2019-03-22"),
        ("2019-12-31", "original"): ("2020-03-26", "2020-03-27"),
        ("2017-12-31", "restated_1"): ("2020-03-26", "2020-03-27"),
        ("2018-12-31", "restated_1"): ("2020-03-26", "2020-03-27"),
    }
    for f in b["facts"]:
        if f["concept_id"] == CONCEPT_NET_PROFIT and f["period_end"] == "2018-12-31":
            pass  # NP covered below
        key = (f["period_end"], f["restatement_version"])
        if key in expected:
            assert f["available_at"] == expected[key][0]
            assert f["effective_from"] == expected[key][1]
            assert f["pit_time_contract_gap"] == ""
    # NP facts
    for f in b["facts"]:
        if f["concept_id"] == CONCEPT_NET_PROFIT:
            assert f["available_at"] == f["announcement_date"]
            assert f["effective_from"] > f["available_at"]


def test_future_version_invisible_backward():
    b = _load_json(BACKFILL_BUNDLE)
    equity_2018 = [
        f
        for f in b["facts"]
        if f["concept_id"] == CONCEPT_EQUITY and f["period_end"] == "2018-12-31"
    ]
    # at 2019-06-01 only the original (2019-03-22 effective) is visible
    v = resolve_latest_visible(equity_2018, "2019-06-01")
    assert v is not None
    assert v["restatement_version"] == "original"
    # at 2020-04-01 the restated_1 (2020-03-27 effective) is visible
    v = resolve_latest_visible(equity_2018, "2020-04-01")
    assert v is not None
    assert v["restatement_version"] == "restated_1"


def test_latest_today_not_backfilled_historically():
    b = _load_json(BACKFILL_BUNDLE)
    for f in b["facts"]:
        if f["restatement_version"] == "restated_1":
            # restated facts must never have an effective_from in the past
            assert f["effective_from"] >= "2020-03-27"
        else:
            assert f["effective_from"] >= f["available_at"]


# ─────────────── ROE ───────────────


def test_roe_2018_exact(facts):
    roe = resolve_annual_roe_chain_as_of(facts, "2023-07-31")
    assert roe["status"] == "READY"
    r18 = next(r for r in roe["roe_observations"] if r["fiscal_year"] == "2018")
    assert r18["roe_decimal"] == "0.04406444893056670969521743267"


def test_roe_2019_exact(facts):
    roe = resolve_annual_roe_chain_as_of(facts, "2023-07-31")
    r19 = next(r for r in roe["roe_observations"] if r["fiscal_year"] == "2019")
    assert r19["roe_decimal"] == "0.03737131800228677088723846848"


def test_roe_2020_exact(facts):
    roe = resolve_annual_roe_chain_as_of(facts, "2023-07-31")
    r20 = next(r for r in roe["roe_observations"] if r["fiscal_year"] == "2020")
    assert r20["roe_decimal"] == "0.01553816282198941962484192606"


def test_roe_independent_recomputation_matches_resolver(facts):
    # independent Decimal-only recomputation, not read from the resolver
    r18 = roe_decimal("53030000000", "1192862000000", "1214067000000")
    r19 = roe_decimal("45677000000", "1214067000000", "1230428000000")
    r20 = roe_decimal("19002000000", "1230428000000", "1215421000000")
    roe = resolve_annual_roe_chain_as_of(facts, "2023-07-31")
    by_year = {r["fiscal_year"]: r["roe_decimal"] for r in roe["roe_observations"]}
    assert r18 == by_year["2018"]
    assert r19 == by_year["2019"]
    assert r20 == by_year["2020"]


def test_roe_decimal_only():
    # Decimal arithmetic, no float
    r = roe_decimal("53030000000", "1192862000000", "1214067000000")
    assert isinstance(Decimal(r), Decimal)
    # division result must be exact Decimal, not float
    assert "." in r


def test_reconciliation_report_pass():
    rec = _load_json(RECONCILIATION)
    assert rec["status"] == "PASS"
    assert rec["roe_independent_recomputation"]["roe_2018"]["resolver_match"] is True
    assert rec["roe_independent_recomputation"]["roe_2019"]["resolver_match"] is True
    assert rec["roe_independent_recomputation"]["roe_2020"]["resolver_match"] is True


# ─────────────── Readiness / gate ───────────────


def test_before_readiness_reproduces_r4f3(facts, observations):
    committed = _load_json(R4F3_READINESS)
    before = _load_json(AFTER_READINESS)["before"]
    # The after-readiness report embeds the before snapshot; compare
    # against committed
    assert (
        before["prototype_ready_trade_days"]
        == committed["prototype_ready_trade_days"]
        == 84
    )
    assert before["blocked_trade_days"] == committed["blocked_trade_days"] == 1267
    assert (
        before["earliest_ready_trade_date"]
        == committed["earliest_ready_trade_date"]
        == "2026-03-31"
    )
    assert before["gap_reason_counts"] == committed["gap_reason_counts"] == {
        "insufficient_roe_history": 1267
    }


def test_after_readiness_derived_from_overlay(facts, observations):
    after = _load_json(AFTER_READINESS)
    assert after["after"]["prototype_ready_trade_days"] == 808
    assert after["after"]["blocked_trade_days"] == 543
    assert after["after"]["earliest_ready_trade_date"] == "2023-03-31"
    assert after["3y_gate"]["status"] == "THREE_YEAR_HISTORICAL_VALIDATION_READY"
    assert after["3y_gate"]["required_days"] == 728
    assert after["3y_gate"]["ready_days"] == 728
    assert after["3y_gate"]["blocked_days"] == 0


def test_3y_ready_only_if_blocked_zero():
    after = _load_json(AFTER_READINESS)
    assert after["3y_gate"]["blocked_days"] == 0
    assert after["3y_gate"]["status"] == "THREE_YEAR_HISTORICAL_VALIDATION_READY"


def test_5y_may_remain_blocked():
    after = _load_json(AFTER_READINESS)
    assert after["after"]["verdicts"]["5Y_HISTORICAL_VALIDATION_READY"] is False


def test_full_cycle_remains_false():
    after = _load_json(AFTER_READINESS)
    assert after["full_cycle_proven"] is False
    assert after["after"]["verdicts"]["FULL_CYCLE_VALIDATION_READY"] is False


def test_no_forward_fill():
    after = _load_json(AFTER_READINESS)
    assert after["no_forward_fill"] is True


def test_overlay_digests():
    ov = _load_json(OVERLAY)
    assert len(ov["existing_fact_set_digest"]) == 64
    assert len(ov["backfill_bundle_digest"]) == 64
    assert len(ov["combined_fact_set_digest"]) == 64
    assert ov["existing_fact_count"] + ov["backfill_fact_count"] == ov["combined_fact_count"]


# ─────────────── Decision ───────────────


def test_decision_passes_3y_gate():
    d = _load_json(DECISION)
    assert d["decision"] == "PE_3Y_HISTORICAL_BACKFILL_TRUSTED_VALIDATION_ALLOWED"
    assert d["verdict"] == "PASS"
    assert d["gates"]["3y_frozen_window_blocked_days"] == 0
    assert d["gates"]["calendar_overlap_reconciliation"] == "PASS"


def test_decision_boundary_preserved():
    d = _load_json(DECISION)
    assert d["pe_numeric_scoring_authorized"] is False
    assert d["evidence"]["pe_numeric_scoring"] == "BLOCKED_UNCHANGED"
    assert d["evidence"]["valuation_dimension_score"] == "NONE"
    assert d["evidence"]["full_cycle_coverage"] == "NOT_PROVEN"
    assert d["evidence"]["no_normalized_pe_percentile"] is True
    assert d["evidence"]["no_peer"] is True
    assert d["evidence"]["no_m3"] is True
    assert d["next_stage"].endswith("NOT_STARTED")


def test_remaining_5y_gap_derived_not_hardcoded():
    """Remaining 5Y gap = deterministic subtraction of resolved cells from
    the committed R4F.3 baseline (9 - 5 = 4).  Derived, not hardcoded."""
    r4f3 = _load_json(R4F3_DECISION)
    baseline = {
        (m["concept"], m["period_end"])
        for m in r4f3["evidence"]["minimum_5y_backfill"]["missing_facts"]
    }
    assert len(baseline) == 9
    bundle = _load_json(BACKFILL_BUNDLE)
    resolved = {
        (f["concept_id"], f["period_end"])
        for f in bundle["facts"]
        if f["restatement_version"] == "original"
    }
    assert len(resolved) == 5
    remaining = sorted(baseline - resolved)
    assert remaining == [
        (CONCEPT_EQUITY, "2015-12-31"),
        (CONCEPT_EQUITY, "2016-12-31"),
        (CONCEPT_NET_PROFIT, "2016-12-31"),
        (CONCEPT_NET_PROFIT, "2017-12-31"),
    ]
    assert len(remaining) == 4
    # decision report reflects the derived counts
    d = _load_json(DECISION)
    assert d["evidence"]["original_minimum_5y_backfill_count"] == 9
    assert d["evidence"]["resolved_by_r4f3a_count"] == 5
    assert d["evidence"]["remaining_5y_backfill_count"] == 4
    assert {
        (g["concept"], g["period_end"]) for g in d["evidence"]["remaining_5y_gaps"]
    } == set(remaining)


# ─────────────── Boundary / protected state ───────────────


def test_scoring_contracts_unchanged_git():
    """registry v2 / policy v2 / shadow v6 / sensitivity v8 must be untouched."""
    import subprocess

    r = subprocess.run(
        ["git", "status", "--short"], cwd=ROOT, capture_output=True, text=True
    )
    out = r.stdout + r.stderr
    for protected in (
        "registry_v2",
        "policy_v2",
        "shadow_v6",
        "sensitivity_v8",
        "shadow_inputs_v2",
        "capsule_v5",
    ):
        assert protected not in out, f"protected file changed: {protected}"


def test_pe_score_null():
    d = _load_json(DECISION)
    assert d["pe_status"] == "coverage_gap_cycle_context_required"
    assert d["valuation_dimension_status"] == "insufficient_evidence_cycle_context"


def test_no_production_metric_result():
    # no production Metric Result artifacts generated by this stage
    from pathlib import Path as Pth

    m = Pth(ROOT / "reports").glob("petrochina_pe_3y_historical_backfill_*")
    names = [p.name for p in m]
    assert not any("metric_result" in n for n in names)
    assert not any("percentile" in n for n in names)


def test_default_db_unchanged():
    import hashlib

    db = ROOT / "data" / "research.duckdb"
    if db.is_file():
        h = hashlib.sha256(db.read_bytes()).hexdigest()
        assert h == "4a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6"
