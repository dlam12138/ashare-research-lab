"""M2 Stage 2K.1R4D.1 — Context v2, restatement metadata and share-continuity.

Covers the governance-closeout fixes:

- instant Facts get a period-end-qualified Context v2 (one context per report
  period, not one per year);
- the old->new Fact ID migration report only changes instant facts;
- restated Facts are rebuilt from the later filing (all source + PIT fields,
  ``effective_from`` recomputed from the restatement announcement date);
- share continuity register -> constancy derivation of Q1/Q3 period-end and
  weighted-average share counts;
- coverage <-> fact/gap bidirectional binding validation.
"""

from __future__ import annotations

from pathlib import Path

from ashare_research.pit_valuation.fact_builder import (
    build_context_v2,
    build_fact_id_migration_report,
    next_trading_day,
)
from ashare_research.pit_valuation.readiness import validate_coverage_fact_gap_binding
from ashare_research.pit_valuation.share_continuity import (
    build_share_continuity_register,
    classify_share_change,
    constancy_derivation_available,
    derive_period_end_shares_from_constancy,
    derive_weighted_average_shares_from_constancy,
)

ROOT = Path(__file__).resolve().parents[1]

TRADE_DATES = [
    "2023-04-28",
    "2026-04-30",
    "2026-05-06",
]
CALENDAR = {
    "calendar_object_id": "market.parquet",
    "calendar_sha256": "0" * 64,
    "trade_dates": TRADE_DATES,
}


# ── Context v2 ─────────────────────────────────────────────────────────────


def test_context_v2_instant_includes_period_end():
    q1 = build_context_v2(
        fiscal_year=2023, report_type="q1", period_type="instant",
        instant=True, filing_date="2023-04-30", source_document="x",
    )
    annual = build_context_v2(
        fiscal_year=2023, report_type="annual", period_type="instant",
        instant=True, filing_date="2024-03-30", source_document="x",
    )
    assert q1["context_id"] == "601857.SH|2023|instant|consolidated|2023-03-31"
    assert annual["context_id"] == "601857.SH|2023|instant|consolidated|2023-12-31"
    assert q1["context_id"] != annual["context_id"]


def test_context_v2_duration_unchanged():
    c = build_context_v2(
        fiscal_year=2023, report_type="q1", period_type="quarter_ytd",
        instant=False, filing_date="2023-04-30", source_document="x",
    )
    assert c["context_id"] == "601857.SH|2023|quarter_ytd|consolidated"


def test_context_v2_stable_across_restatement():
    q1 = build_context_v2(
        fiscal_year=2022, report_type="q1", period_type="instant",
        instant=True, filing_date="2023-04-30", source_document="later",
    )
    # restatement_version is never encoded into context_id.
    assert q1["restatement_version"] == "original"
    assert "restated" not in q1["context_id"]


# ── Fact ID migration ──────────────────────────────────────────────────────


def _instant_fact(period_end: str, source_id: str) -> dict:
    return {
        "fact_id": "",
        "concept_id": "equity_attributable_to_parent",
        "concept_version": "1",
        "symbol": "601857.SH",
        "context_id": "601857.SH|2023|instant|consolidated",
        "source_id": source_id,
        "fact_version": 1,
        "restatement_version": "original",
        "period_end": period_end,
    }


def _duration_fact(source_id: str) -> dict:
    return {
        "fact_id": "",
        "concept_id": "revenue",
        "concept_version": "1",
        "symbol": "601857.SH",
        "context_id": "601857.SH|2023|quarter_ytd|consolidated",
        "source_id": source_id,
        "fact_version": 1,
        "restatement_version": "original",
        "period_end": "2023-03-31",
    }


def test_migration_only_changes_instant_facts():
    from ashare_research.facts.identity import build_fact_id

    inst = _instant_fact("2023-03-31", "r4d:R4D-SSE-2023-Q1")
    inst["fact_id"] = build_fact_id(inst)
    dur = _duration_fact("r4d:R4D-SSE-2023-Q1")
    dur["fact_id"] = build_fact_id(dur)
    mig = build_fact_id_migration_report([inst, dur])
    assert mig["changed_count"] == 1
    entry = next(e for e in mig["entries"] if e["concept_id"] == "equity_attributable_to_parent")
    assert entry["new_context_id"].endswith("|2023-03-31")
    assert entry["new_fact_id"] != entry["old_fact_id"]
    dur_entry = next(e for e in mig["entries"] if e["concept_id"] == "revenue")
    assert dur_entry["changed"] is False


# ── Restatement metadata rebuild ───────────────────────────────────────────


def test_restated_fact_rebuilds_source_and_pit():
    from ashare_research.pit_valuation.extraction import ExtractedCell
    from ashare_research.pit_valuation.reconciliation import detect_restatements

    original = {
        "fact_id": "orig-1",
        "concept_id": "net_profit_attributable_to_parent",
        "context_id": "601857.SH|2025|quarter_ytd|consolidated",
        "value": 46809000000.0,
        "available_at": "2025-04-30",
        "announcement_date": "2025-04-30",
        "filing_date": "2025-04-30",
        "effective_from": "2025-05-06",
        "source_id": "r4d:R4D-SSE-2025-Q1",
        "source_document": "https://old.invalid/2025q1.pdf",
        "source_url": "https://old.invalid/2025q1.pdf",
        "source_label": "old label",
        "source_page": "1",
        "source_hash": "old-object",
        "source_object_sha256": "old-object",
        "excerpt_hash": "old-excerpt",
        "source_provider": "exchange_official",
        "source_tier": "exchange_official",
        "restatement_version": "original",
        "fact_version": 1,
    }
    cell = ExtractedCell(
        extraction_spec_id="x",
        role_id="net_profit_attributable_to_parent",
        evidence_id="R4D-SSE-2026-Q1",
        report_type="q1",
        fiscal_year=2026,
        page_index=2,
        raw_token="48,333",
        tokens=["48,333", "47,452", "46,809", "1.9"],
        has_restatement_comparatives=True,
        conversion_multiplier="1000000",
        excerpt_hash="new-excerpt-hash",
        status="acquired_reported_verified",
    )
    evidence_map = {
        "R4D-SSE-2025-Q1": {
            "evidence_id": "R4D-SSE-2025-Q1",
            "report_type": "q1",
            "fiscal_year": 2025,
            "announcement_date": "2025-04-30",
            "period_end": "2025-03-31",
            "proof_url": "https://old.invalid/2025q1.pdf",
            "report_title": "old label",
            "source_role": "exchange_official",
        },
        "R4D-SSE-2026-Q1": {
            "evidence_id": "R4D-SSE-2026-Q1",
            "report_type": "q1",
            "fiscal_year": 2026,
            "announcement_date": "2026-04-30",
            "period_end": "2026-03-31",
            "proof_url": "https://new.invalid/2026q1.pdf",
            "report_title": "2026 Q1 report",
            "source_role": "exchange_official",
        },
    }
    restated, _ = detect_restatements(
        [cell],
        [original],
        evidence_map,
        market_calendar=CALENDAR,
        object_sha_by_evidence={"R4D-SSE-2026-Q1": "new-object-sha"},
    )
    assert len(restated) == 1
    r = restated[0]
    # Source fields rebuilt entirely from the later filing.
    assert r["source_id"] == "r4d:R4D-SSE-2026-Q1"
    assert r["source_document"] == "https://new.invalid/2026q1.pdf"
    assert r["source_url"] == "https://new.invalid/2026q1.pdf"
    assert r["source_label"] == "2026 Q1 report"
    assert r["source_page"] == "3"  # page_index 2 -> page 3
    assert r["source_hash"] == "new-object-sha"
    assert r["source_object_sha256"] == "new-object-sha"
    assert r["excerpt_hash"] == "new-excerpt-hash"
    # PIT fields recomputed from the restatement announcement date.
    assert r["announcement_date"] == "2026-04-30"
    assert r["available_at"] == "2026-04-30"
    assert r["filing_date"] == "2026-04-30"
    assert r["effective_from"] == next_trading_day("2026-04-30", TRADE_DATES)
    assert r["effective_from"] == "2026-05-06"
    # The context is the superseded original's (same economic period).
    assert r["context_id"] == "601857.SH|2025|quarter_ytd|consolidated"


# ── Share continuity register ──────────────────────────────────────────────


def test_share_change_classifier():
    assert classify_share_change("关于2023年度利润分配方案的公告") is False
    assert classify_share_change("2022年年度权益分派实施公告") is False
    assert classify_share_change("资本公积转增股本实施公告") is True
    assert classify_share_change("关于回购股份并注销的公告") is True
    # a standing buyback general-authority opinion is not an executed change
    assert classify_share_change("关于股东大会给予董事会回购股份一般性授权的独立意见") is False


def _base_facts() -> list[dict]:
    return [
        {"period_end": "2020-06-30", "value": 183020977818, "source_id": "r4d:x-h1"},
        {"period_end": "2020-12-31", "value": 183020977818, "source_id": "r4d:x-ar"},
        {"period_end": "2021-06-30", "value": 183020977818, "source_id": "r4d:x-h1-21"},
    ]


def test_register_constant_and_trusted():
    reg = build_share_continuity_register(
        [
            {"TITLE": "关于2023年度利润分配方案的公告", "SSEDATE": "2024-03-26", "URL": "u1"},
            {"TITLE": "2022年年度权益分派实施公告", "SSEDATE": "2023-06-20", "URL": "u2"},
        ],
        _base_facts(),
        search_start="2020-01-01",
        search_end="2026-08-02",
        source_label="test",
    )
    assert reg["share_count_constant"] is True
    assert reg["constant_value"] == 183020977818
    assert reg["trust"] == "trusted"
    assert reg["share_changing_action_count"] == 0
    assert constancy_derivation_available(reg)


def test_register_not_trusted_when_share_change():
    reg = build_share_continuity_register(
        [
            {"TITLE": "资本公积转增股本实施公告", "SSEDATE": "2022-06-20", "URL": "u1"},
        ],
        _base_facts(),
        search_start="2020-01-01",
        search_end="2026-08-02",
        source_label="test",
    )
    assert reg["share_changing_action_count"] == 1
    assert reg["trust"] == "not_trusted"
    assert constancy_derivation_available(reg) is False


def test_register_not_constant_when_bases_differ():
    reg = build_share_continuity_register(
        [],
        [
            {"period_end": "2020-06-30", "value": 183020977818, "source_id": "a"},
            {"period_end": "2020-12-31", "value": 190000000000, "source_id": "b"},
        ],
        search_start="2020-01-01",
        search_end="2026-08-02",
        source_label="test",
    )
    assert reg["share_count_constant"] is False
    assert constancy_derivation_available(reg) is False


def test_constancy_derivations():
    reg = build_share_continuity_register([], _base_facts(), search_start="2020-01-01",
                                           search_end="2026-08-02", source_label="t")
    filings = [
        {"evidence_id": "x-q1", "report_type": "q1", "fiscal_year": 2021,
         "period_end": "2021-03-31"},
        {"evidence_id": "x-h1", "report_type": "half_year", "fiscal_year": 2021,
         "period_end": "2021-06-30"},
        {"evidence_id": "x-q3", "report_type": "q3", "fiscal_year": 2021,
         "period_end": "2021-09-30"},
        {"evidence_id": "x-ar", "report_type": "annual", "fiscal_year": 2021,
         "period_end": "2021-12-31"},
    ]
    pe = derive_period_end_shares_from_constancy(reg, filings)
    assert [p["report_type"] for p in pe] == ["q1", "q3"]
    assert all(p["value"] == 183020977818 for p in pe)
    assert all(p["status"] == "acquired_reconciled_derived" for p in pe)
    wa = derive_weighted_average_shares_from_constancy(reg, filings)
    assert len(wa) == 4
    assert all(w["value"] == 183020977818 for w in wa)


def test_constancy_derivations_blocked_when_not_trusted():
    reg = {"trust": "not_trusted", "share_count_constant": True, "constant_value": 183020977818}
    assert constancy_derivation_available(reg) is False
    assert derive_period_end_shares_from_constancy(reg, [{"report_type": "q1"}]) == []
    assert derive_weighted_average_shares_from_constancy(reg, [{"report_type": "q1"}]) == []


# ── Coverage <-> fact/gap binding ──────────────────────────────────────────


def test_binding_ok_for_complete_grid():
    grid = [
        {
            "cell_id": "a:rev",
            "acquisition_status": "acquired_reported_verified",
            "fact_ids": ["f1"],
            "gap_ids": [],
        },
        {
            "cell_id": "b:wa",
            "acquisition_status": "acquired_reconciled_derived",
            "fact_ids": ["f2"],
            "gap_ids": [],
        },
    ]
    gaps = []
    facts = [{"fact_id": "f1"}, {"fact_id": "f2"}]
    binding = validate_coverage_fact_gap_binding(grid, gaps, facts)
    assert binding["ok"] is True
    assert binding["errors"] == []


def test_binding_rejects_missing_fact_id():
    grid = [
        {
            "cell_id": "a:rev",
            "acquisition_status": "acquired_reported_verified",
            "fact_ids": [],
            "gap_ids": [],
        }
    ]
    binding = validate_coverage_fact_gap_binding(grid, [], [{"fact_id": "f1"}])
    assert binding["ok"] is False
    assert any("no fact_id" in e for e in binding["errors"])


def test_binding_rejects_unknown_fact_and_unbound_gap():
    grid = [
        {
            "cell_id": "a:rev",
            "acquisition_status": "acquired_reported_verified",
            "fact_ids": ["ghost"],
            "gap_ids": [],
        },
        {
            "cell_id": "c:eq",
            "acquisition_status": "missing_official_filing",
            "fact_ids": [],
            "gap_ids": ["R4D-c-eq"],
        },
    ]
    gaps = [
        {
            "gap_id": "R4D-c-eq",
            "cell_id": "c:eq",
        }
    ]
    facts = [{"fact_id": "f1"}]
    binding = validate_coverage_fact_gap_binding(grid, gaps, facts)
    assert binding["ok"] is False
    assert any("unknown fact" in e for e in binding["errors"])
    # f1 is never referenced by exactly one cell.
    assert any("referenced by 0" in e for e in binding["errors"])


def test_binding_rejects_gap_without_gap_id():
    grid = [
        {
            "cell_id": "c:eq",
            "acquisition_status": "missing_official_filing",
            "fact_ids": [],
            "gap_ids": [],
        }
    ]
    binding = validate_coverage_fact_gap_binding(grid, [], [{"fact_id": "f1"}])
    assert binding["ok"] is False
    assert any("no gap_id" in e for e in binding["errors"])
