"""M2 Stage 2K.1R4D.1a — Historical market calendar and PIT time contract.

Covers the R4D.1a closeout:

- the extended calendar (2020 Q1 .. evidence cutoff) resolves 2020 Q1
  announcements to a real next trading day (no more 2021-01-04 backfill);
- weekend and statutory-holiday announcements map to the next trading day;
- a calendar that does not cover an announcement fails closed
  (``calendar_coverage_gap``), never backfilled to the nearest boundary;
- 2020 facts keep ``available_at`` unchanged while only ``effective_from`` is
  fixed;
- the calendar fix does not change fact ids (calendar is not an identity
  field), so the migration report shows zero changes;
- 3y/5y readiness is recomputed independently and a PIT time-contract gap
  fails the gate closed (pit_time_contract_gaps > 0 -> NOT_TRUSTED).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from ashare_research.pit_valuation.contracts import (
    GAP_CLASS_PIT_TIME_CONTRACT,
    CalendarCoverageGapError,
)
from ashare_research.pit_valuation.extraction import ExtractedCell
from ashare_research.pit_valuation.fact_builder import (
    _pit_time_from_calendar,
    build_fact_id_migration_report,
    build_reported_fact,
    effective_from_derivation,
    load_role,
    next_trading_day,
)

ROOT = Path(__file__).resolve().parents[1]

# 2020 trading days around Q1/H1/Q3/annual announcements and the May Day /
# National Day holidays.  May 1 2020 was a Friday statutory holiday; 2020-05-04
# and 2020-05-05 were also holidays, so the next trading day after 2020-04-30
# (Thursday) is 2020-05-06 (Wednesday).
FULL_TRADE_DATES = [
    "2020-01-02",
    "2020-01-03",
    "2020-01-06",
    "2020-04-29",
    "2020-04-30",
    "2020-05-06",
    "2020-05-07",
    "2020-05-08",
    "2020-05-11",
    "2020-08-28",
    "2020-08-31",
    "2020-10-30",
    "2020-11-02",
    "2021-03-26",
    "2021-03-29",
    "2026-04-30",
    "2026-05-06",
    "2026-08-05",
]
FULL_CALENDAR = {
    "calendar_object_id": (
        "77021dceda8aae05c7bc2329e6efb65711ccea232bb289e880cd16b99151b92d.parquet"
    ),
    "calendar_sha256": (
        "77021dceda8aae05c7bc2329e6efb65711ccea232bb289e880cd16b99151b92d"
    ),
    "trade_dates": FULL_TRADE_DATES,
}

# The pre-R4D.1a calendar began 2021-01-04 and could not resolve 2020 facts.
SHORT_TRADE_DATES = ["2021-01-04", "2021-01-05", "2021-03-26", "2021-03-29"] + [
    d for d in FULL_TRADE_DATES if d.startswith("2026")
]
SHORT_CALENDAR = {
    "calendar_object_id": (
        "defd0b9507c0d87cf9d12864923eb24573e4edee28d7b67b9ce319ab4d91a764.parquet"
    ),
    "calendar_sha256": (
        "defd0b9507c0d87cf9d12864923eb24573e4edee28d7b67b9ce319ab4d91a764"
    ),
    "trade_dates": SHORT_TRADE_DATES,
}


def _cell(role_id: str, rtype: str, fy: int, value: float = 48.332e9) -> ExtractedCell:
    return ExtractedCell(
        extraction_spec_id=f"r4d-extract-{rtype}-{role_id}-v1",
        role_id=role_id,
        evidence_id=f"R4D-SSE-{fy}-{rtype.upper()}",
        report_type=rtype,
        fiscal_year=fy,
        raw_token="48,332",
        raw_value=value,
        normalized_value=value,
        unit="CNY_million",
        sign_rule="as_reported",
        conversion_multiplier=1,
        page_index=3,
        excerpt="48,332",
        excerpt_hash="abc123",
        status="acquired_reported_verified",
    )


def _evidence(announcement: str, eid: str = "R4D-SSE-2020-Q1") -> dict:
    return {
        "evidence_id": eid,
        "issuer": "PetroChina",
        "symbol": "601857.SH",
        "report_type": "q1",
        "fiscal_year": 2020,
        "period_start": "2020-01-01",
        "period_end": "2020-03-31",
        "announcement_date": announcement,
        "reporting_language": "zh",
        "source_role": "exchange_official",
        "proof_url": "https://example.invalid/R4D-SSE-2020-Q1.pdf",
        "supersedes_document_id": None,
        "report_title": "2020 Q1 report",
    }


# ── 1. 2020 Q1 announcement -> real next trading day ───────────────────────


def test_2020_q1_announcement_maps_to_real_next_trading_day():
    # 2020-04-30 (Thu) -> 2020-05-06 (Wed), skipping the May Day holiday block.
    assert next_trading_day("2020-04-30", FULL_TRADE_DATES) == "2020-05-06"
    der = effective_from_derivation("2020-04-30", FULL_CALENDAR)
    assert der["selected_next_trading_day"] == "2020-05-06"
    assert der["calendar_object_id"] == FULL_CALENDAR["calendar_object_id"]


# ── 2. weekend announcement -> next trading day ────────────────────────────


def test_weekend_announcement_maps_to_next_trading_day():
    # 2020-05-08 was a Friday; the next trading day is Monday 2020-05-11.
    assert next_trading_day("2020-05-08", FULL_TRADE_DATES) == "2020-05-11"


# ── 3. holiday announcement crossing suspension ────────────────────────────


def test_holiday_announcement_crosses_suspension():
    # 2020-04-30 -> 2020-05-06 crosses the May Day statutory holiday block
    # (2020-05-01/05-04/05-05 non-trading) plus the 05-02/05-03 weekend.
    assert next_trading_day("2020-04-30", FULL_TRADE_DATES) == "2020-05-06"
    # National Day block: 2020-10-30 (Fri) -> 2020-11-02 (Mon).
    assert next_trading_day("2020-10-30", FULL_TRADE_DATES) == "2020-11-02"


# ── 4. calendar start later than announcement -> fail closed ───────────────


def test_calendar_start_later_than_announcement_fails_closed():
    assert SHORT_TRADE_DATES[0] == "2021-01-04"
    with pytest.raises(CalendarCoverageGapError):
        next_trading_day("2020-04-30", SHORT_TRADE_DATES)


def test_effective_from_derivation_raises_on_short_calendar():
    with pytest.raises(CalendarCoverageGapError):
        effective_from_derivation("2020-04-30", SHORT_CALENDAR)


# ── 5. no uniform backfill to 2021-01-04 ───────────────────────────────────


def test_no_uniform_backfill_to_2021_01_04():
    role = load_role("revenue")
    fact = build_reported_fact(
        _cell("revenue", "q1", 2020), _evidence("2020-04-30"), role,
        market_calendar=SHORT_CALENDAR,
    )
    # Fail-closed: effective_from is unresolved, never 2021-01-04.
    assert fact["effective_from"] == ""
    assert fact["pit_time_contract_gap"] == "calendar_coverage_gap"
    assert fact["available_at"] == "2020-04-30"


# ── 6. available_at unchanged, only effective_from fixed ───────────────────


def test_2020_facts_available_at_unchanged_effective_from_fixed():
    role = load_role("revenue")
    short_fact = build_reported_fact(
        _cell("revenue", "q1", 2020), _evidence("2020-04-30"), role,
        market_calendar=SHORT_CALENDAR,
    )
    fixed_fact = build_reported_fact(
        _cell("revenue", "q1", 2020), _evidence("2020-04-30"), role,
        market_calendar=FULL_CALENDAR,
    )
    # available_at is the announcement date in both cases.
    assert short_fact["available_at"] == "2020-04-30"
    assert fixed_fact["available_at"] == "2020-04-30"
    # effective_from is the only thing that changes.
    assert short_fact["effective_from"] == ""
    assert fixed_fact["effective_from"] == "2020-05-06"
    assert fixed_fact["effective_from_derivation"]["selected_next_trading_day"] == "2020-05-06"
    assert fixed_fact["calendar_object_id"] == FULL_CALENDAR["calendar_object_id"]


# ── 7. calendar fix does not change fact ids (migration 0) ─────────────────


def test_calendar_fix_does_not_change_fact_ids():
    role = load_role("revenue")
    short_fact = build_reported_fact(
        _cell("revenue", "q1", 2020), _evidence("2020-04-30"), role,
        market_calendar=SHORT_CALENDAR,
    )
    fixed_fact = build_reported_fact(
        _cell("revenue", "q1", 2020), _evidence("2020-04-30"), role,
        market_calendar=FULL_CALENDAR,
    )
    # The calendar (and effective_from) is not an identity field, so the
    # fact_id is unchanged by the calendar fix.
    assert short_fact["fact_id"] == fixed_fact["fact_id"]


def test_migration_report_shows_zero_changes_for_calendar_fix():
    role = load_role("revenue")
    fixed = build_reported_fact(
        _cell("revenue", "q1", 2020), _evidence("2020-04-30"), role,
        market_calendar=FULL_CALENDAR,
    )
    report = build_fact_id_migration_report([fixed])
    assert report["entry_count"] == 1
    assert report["changed_count"] == 0
    assert report["entries"][0]["old_fact_id"] == report["entries"][0]["new_fact_id"]


# ── pit-time helper: gap classification ────────────────────────────────────


def test_pit_time_from_calendar_gap_classification():
    eff, gap, der = _pit_time_from_calendar("2020-04-30", FULL_CALENDAR)
    assert eff == "2020-05-06"
    assert gap == ""
    assert der["rule_id"] == "announcement-date-to-next-trading-day-v1"
    eff2, gap2, der2 = _pit_time_from_calendar("2020-04-30", SHORT_CALENDAR)
    assert eff2 == ""
    assert gap2 == "calendar_coverage_gap"
    assert der2 == {}


# ── 8. 3y/5y readiness recomputed; pit gap fails gate closed ───────────────


def test_readiness_pit_time_gap_fails_gate_closed():
    from ashare_research.pit_valuation import readiness
    from ashare_research.pit_valuation.contracts import load_role_registry, load_source_evidence

    evidence = load_source_evidence()
    roles = load_role_registry()
    grid = readiness.build_expected_grid(evidence, roles)
    # Seed every cell as acquired so the only gap is the injected PIT gap,
    # isolating the pit_time_contract failure.
    for cell in grid:
        cell["acquisition_status"] = "acquired_reported_verified"
        cell["fact_ids"] = ["r4d-test"]
    # Mark one 2020 cell as a calendar coverage gap (as the pre-fix calendar
    # would have), then recompute ledger + readiness + gate.
    gap_cell = next(
        c for c in grid if c["fiscal_year"] == 2020 and c["report_type"] == "q1"
    )
    gap_cell["acquisition_status"] = "calendar_coverage_gap"
    gap_cell["fact_ids"] = []
    gaps = readiness.gap_ledger_from_grid(grid)
    read = readiness.build_readiness(evidence, roles, grid, gaps)
    assert read["economic_fact_gaps"] == 0
    assert read["pit_time_contract_gaps"] == 1
    assert all(g["gap_class"] == GAP_CLASS_PIT_TIME_CONTRACT for g in gaps)
    gate = readiness.decide_from_readiness(
        read, cache_trusted=True, extraction_trusted=True,
        identity_trusted=True, pit_trusted=True,
    )
    assert gate == "PIT_DENOMINATOR_ACQUISITION_NOT_TRUSTED"


def test_readiness_no_pit_gap_is_ready():
    from ashare_research.pit_valuation import readiness
    from ashare_research.pit_valuation.contracts import load_role_registry, load_source_evidence

    evidence = load_source_evidence()
    roles = load_role_registry()
    grid = readiness.build_expected_grid(evidence, roles)
    # Seed every cell as acquired so the grid closes with no gaps.
    for cell in grid:
        cell["acquisition_status"] = "acquired_reported_verified"
        cell["fact_ids"] = ["r4d-test"]
    gaps = readiness.gap_ledger_from_grid(grid)
    read = readiness.build_readiness(evidence, roles, grid, gaps)
    assert read["pit_time_contract_gaps"] == 0
    gate = readiness.decide_from_readiness(
        read, cache_trusted=True, extraction_trusted=True,
        identity_trusted=True, pit_trusted=True,
    )
    assert gate == "PIT_DENOMINATOR_FACTS_READY_FOR_SERIES_PREFLIGHT"
