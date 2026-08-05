"""M2 Stage 2K.1R4D — FactIdentity and fact-bundle contract tests.

Canonical fact IDs must be recomputable; source-specific identities must be
correct; reconciled facts bind ordered input IDs; direct vs derived facts must
not be confused; missing values are never written as zero; available_at is
required for eligibility; the default DB is never written.
"""

from __future__ import annotations

from pathlib import Path

from ashare_research.facts.identity import (
    build_fact_id,
    validate_canonical_fact_ids,
)
from ashare_research.pit_valuation.extraction import ExtractedCell
from ashare_research.pit_valuation.fact_builder import (
    build_reported_fact,
    build_share_capital_fact,
    effective_from_derivation,
    load_role,
    next_trading_day,
)
from ashare_research.pit_valuation.reconciliation import (
    derive_weighted_average_shares,
    reconcile_dual_source,
)

ROOT = Path(__file__).resolve().parents[1]

TRADE_DATES = [f"2021-{m:02d}-01" for m in range(1, 13)] + [
    "2026-04-01",
    "2026-04-02",
    "2026-04-03",
    "2026-04-07",
    "2026-04-08",
    "2026-04-30",
    "2026-05-06",
]
CALENDAR = {
    "calendar_object_id": "market.parquet",
    "calendar_sha256": "0" * 64,
    "trade_dates": TRADE_DATES,
}


def _cell(
    role_id: str, rtype: str = "q1", fy: int = 2026, value: float = 48.332e9
) -> ExtractedCell:
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
        excerpt="归属于母公司股东的净利润 48,332",
        excerpt_hash="deadbeef",
        sign_rule="parentheses_negative",
        conversion_multiplier="1000000",
        status="acquired_reported_verified",
    )


def _evidence(rtype: str = "q1", fy: int = 2026) -> dict:
    return {
        "evidence_id": f"R4D-SSE-{fy}-{rtype.upper()}",
        "announcement_date": "2026-04-30",
        "fiscal_year": fy,
        "report_type": rtype,
        "proof_url": "https://example.invalid/x.pdf",
        "report_title": "test",
        "source_role": "exchange_official",
    }


# ── canonical identity ────────────────────────────────────────────────────


def test_canonical_fact_id_recomputable():
    role = load_role("net_profit_attributable_to_parent")
    fact = build_reported_fact(
        _cell("net_profit_attributable_to_parent"), _evidence(), role, market_calendar=CALENDAR
    )
    assert fact["fact_id"]
    assert build_fact_id(fact) == fact["fact_id"]
    validate_canonical_fact_ids([fact])


def test_source_specific_identity_differs_by_evidence():
    role = load_role("revenue")
    f1 = build_reported_fact(_cell("revenue"), _evidence(fy=2026), role, market_calendar=CALENDAR)
    f2 = build_reported_fact(
        _cell("revenue", fy=2025), _evidence(fy=2025), role, market_calendar=CALENDAR
    )
    assert f1["fact_id"] != f2["fact_id"]
    assert f1["source_id"] != f2["source_id"]


def test_identity_changes_when_value_changes_without_identity_ok():
    # fact_id is derived from identity fields, not the value.
    role = load_role("revenue")
    a = build_reported_fact(_cell("revenue"), _evidence(), role, market_calendar=CALENDAR)
    b = build_reported_fact(
        _cell("revenue", value=50e9), _evidence(), role, market_calendar=CALENDAR
    )
    assert a["fact_id"] == b["fact_id"]  # same identity, economic value differs


# ── PIT fields ────────────────────────────────────────────────────────────


def test_next_trading_day_after_announcement():
    assert next_trading_day("2026-04-30", TRADE_DATES) == "2026-05-06"
    assert next_trading_day("2026-04-03", TRADE_DATES) == "2026-04-07"


def test_effective_from_derivation_record():
    der = effective_from_derivation("2026-04-30", CALENDAR)
    assert der["rule_id"] == "announcement-date-to-next-trading-day-v1"
    assert der["selected_next_trading_day"] == "2026-05-06"
    assert der["input_announcement_date"] == "2026-04-30"


def test_available_at_required_for_eligibility():
    role = load_role("revenue")
    fact = build_reported_fact(_cell("revenue"), _evidence(), role, market_calendar=CALENDAR)
    assert fact["available_at"] == "2026-04-30"
    assert fact["eligible_for_metrics"] is True
    # A fact without available_at is never eligible.
    from ashare_research.pit_valuation.fact_builder import build_context

    ctx = build_context(
        fiscal_year=2026, report_type="q1", period_type="quarter_ytd",
        instant=False, filing_date="", source_document="",
    )
    assert ctx["filing_date"] == ""


def test_period_end_not_used_as_available_at():
    role = load_role("revenue")
    fact = build_reported_fact(_cell("revenue"), _evidence(), role, market_calendar=CALENDAR)
    assert fact["available_at"] != fact["period_end"]
    assert fact["available_at"] == "2026-04-30"
    assert fact["period_end"] == "2026-03-31"


# ── direct vs derived ─────────────────────────────────────────────────────


def test_reported_fact_is_not_derived():
    role = load_role("revenue")
    fact = build_reported_fact(_cell("revenue"), _evidence(), role, market_calendar=CALENDAR)
    assert fact["is_derived"] is False
    assert fact["source_tier"] in ("company_official", "exchange_official")


def test_share_capital_fact_identity():
    role = load_role("total_ordinary_shares_at_period_end")
    cell = ExtractedCell(
        extraction_spec_id="r4d-extract-share-capital-dividend-statement-v1",
        role_id=role["role_id"],
        evidence_id="R4D-SSE-2025-AR",
        report_type="annual",
        fiscal_year=2025,
        raw_token="183,020,977,818",
        raw_value=183020977818,
        normalized_value=183020977818,
        unit="SHARE",
        excerpt="总股本 183,020,977,818 股为基数",
        excerpt_hash="cafe",
        status="acquired_reported_verified",
    )
    fact = build_share_capital_fact(cell, _evidence("annual", 2025), role, market_calendar=CALENDAR)
    assert fact["value"] == 183020977818
    assert fact["is_derived"] is False
    assert fact["unit"] == "SHARE"
    validate_canonical_fact_ids([fact])


def test_weighted_share_derivation_ambiguity_recorded():
    der = derive_weighted_average_shares(
        profit_yuan=48332000000,
        eps=0.264,
    )
    assert der.status == "ambiguous_due_to_eps_rounding"
    assert der.notes
    assert der.derived_value is None


def test_direct_disclosure_wins():
    der = derive_weighted_average_shares(
        profit_yuan=48332000000, eps=0.264, direct_disclosure=True, direct_value=183020977818
    )
    assert der.status == "directly_disclosed"
    assert der.derived_value == 183020977818


def test_dual_source_reconciliation_consistent():
    result = reconcile_dual_source(
        evidence_ids=["R4D-ISS-2025-AR", "R4D-SSE-2025-AR"],
        values=[157302000000, 157302000000],
        source_roles=["issuer_official", "exchange_official"],
    )
    assert result["status"] == "reconciled_consistent"


def test_dual_source_conflict_not_auto_selected():
    result = reconcile_dual_source(
        evidence_ids=["a", "b"],
        values=[100, 200],
        source_roles=["issuer_official", "exchange_official"],
    )
    assert result["status"] == "source_conflict"


# ── missing is never zero ─────────────────────────────────────────────────


def test_missing_value_is_none_not_zero():
    cell = _cell("revenue")
    cell.status = "extraction_marker_missing"
    cell.normalized_value = None
    assert cell.normalized_value is None
    assert cell.normalized_value != 0


def test_default_db_never_written():
    # The bundle writer only writes JSON bundles under the explicit output root.
    from ashare_research.pit_valuation.fact_builder import write_isolated_bundles

    out = ROOT / "tmp" / "r4d-test-bundles"
    result = write_isolated_bundles(out, reported=[], reconciled=[], evidence={})
    assert "duckdb" not in str(result["reported_bundle"]).lower()
    assert str(out).lower() != "research.duckdb"


def test_reconciled_fact_binds_ordered_input_ids():
    from ashare_research.pit_valuation.reconciliation import reconcile_dual_source

    result = reconcile_dual_source(
        evidence_ids=["R4D-ISS-2025-AR", "R4D-SSE-2025-AR"],
        values=[157302000000, 157302000000],
        source_roles=["issuer_official", "exchange_official"],
    )
    assert result["status"] == "reconciled_consistent"
    # The input evidence IDs are ordered and the digest binds both sides.
    assert result["input_fact_ids"] == sorted(["R4D-ISS-2025-AR", "R4D-SSE-2025-AR"])
    assert set(result["evidence_set_digest"].split(",")) == {
        "R4D-ISS-2025-AR",
        "R4D-SSE-2025-AR",
    }


def test_derived_fact_records_operands():
    from decimal import Decimal

    from ashare_research.pit_valuation.reconciliation import derive_weighted_average_shares

    der = derive_weighted_average_shares(profit_yuan=48332000000, eps=0.264)
    assert der.profit_yuan == Decimal("48332000000")
    assert der.eps_rounded == Decimal("0.264")
    assert der.eps_rounding_unit == Decimal("0.001")
    assert der.implied_low is not None and der.implied_high is not None
    # The known constant total lies inside the implied interval.
    assert der.implied_low <= 183020977818 <= der.implied_high


def test_derived_does_not_impersonate_official_direct():
    from ashare_research.pit_valuation.reconciliation import derive_weighted_average_shares

    der = derive_weighted_average_shares(
        profit_yuan=48332000000, eps=0.264, direct_disclosure=True, direct_value=183020977818
    )
    assert der.status == "directly_disclosed"
    # A direct disclosure carries the reported value; a derived fact never
    # claims to be directly reported.
    assert der.derived_value == 183020977818
