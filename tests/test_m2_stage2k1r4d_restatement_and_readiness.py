"""M2 Stage 2K.1R4D — restatement/supersession and readiness gate tests.

The expected grid is generated from the filing register (never hand-written);
every expected cell has exactly one status; the gap ledger is recomputed from
the grid; 3y/5y readiness is recomputable; a validator failure makes the gate
NOT_TRUSTED; explicit gaps make the gate GAPS_REMAIN; no PE/PB/PS series, no
score change, no peer acquisition, no M3.
"""

from __future__ import annotations

from pathlib import Path

from ashare_research.pit_valuation.contracts import (
    GATE_GAPS,
    GATE_NOT_TRUSTED,
    load_role_registry,
)
from ashare_research.pit_valuation.readiness import (
    apply_extraction_statuses,
    build_expected_grid,
    build_readiness,
    decide_from_readiness,
    gap_ledger_from_grid,
)

ROOT = Path(__file__).resolve().parents[1]


def _synthetic_evidence() -> dict:
    """A small filing register: 2024 Q1..Q3 + 2024 AR + 2025 Q1."""
    return {
        "schema": "pit_valuation_official_source_evidence_v1",
        "entries": [
            {
                "evidence_id": f"R4D-SSE-{fy}-{rt.upper()}",
                "source_role": "exchange_official",
                "fiscal_year": fy,
                "report_type": rt,
                "period_start": f"{fy}-01-01",
                "period_end": f"{fy}-{end}",
            }
            for fy, rt, end in [
                (2024, "q1", "03-31"),
                (2024, "half_year", "06-30"),
                (2024, "q3", "09-30"),
                (2024, "annual", "12-31"),
                (2025, "q1", "03-31"),
            ]
        ],
    }


def _grid(evidence: dict) -> list[dict]:
    roles = load_role_registry()
    return build_expected_grid(evidence, roles)


# ── grid generation ───────────────────────────────────────────────────────


def test_expected_grid_generated_from_register():
    evidence = _synthetic_evidence()
    grid = _grid(evidence)
    assert grid
    # 5 filings x 4 always-reported roles + share roles on every filing.
    ids = {(g["report_id"], g["role_id"]) for g in grid}
    assert ("R4D-SSE-2024-Q1", "revenue") in ids
    # R4D.1: Q1/Q3 period-end share cells are part of the grid, but they are
    # derived-eligible (the precise count is not directly disclosed in Q1/Q3).
    q1_share = next(
        g for g in grid
        if g["report_id"] == "R4D-SSE-2024-Q1"
        and g["role_id"] == "total_ordinary_shares_at_period_end"
    )
    assert q1_share["expected_direct_disclosure"] is False
    assert q1_share["allowed_derived_fallback"] is True
    ar_share = next(
        g for g in grid
        if g["report_id"] == "R4D-SSE-2024-ANNUAL"
        and g["role_id"] == "total_ordinary_shares_at_period_end"
    )
    assert ar_share["expected_direct_disclosure"] is True


def test_each_expected_cell_has_unique_valid_status():
    grid = _grid(_synthetic_evidence())
    from ashare_research.pit_valuation.contracts import CELL_STATUSES

    for cell in grid:
        assert cell["acquisition_status"] in CELL_STATUSES
    ids = [c["cell_id"] for c in grid]
    assert len(ids) == len(set(ids))


def test_missing_never_written_as_zero():
    grid = _grid(_synthetic_evidence())
    assert all(c["acquisition_status"] != "0" for c in grid)


# ── gap ledger ────────────────────────────────────────────────────────────


def test_gap_ledger_recomputed_from_grid():
    evidence = _synthetic_evidence()
    grid = _grid(evidence)
    # Fill every cell as acquired; the ledger must be empty.
    filled = apply_extraction_statuses(
        grid,
        cells_by_key={
            c["cell_id"]: {"status": "acquired_reported_verified", "fact_ids": ["f"]}
            for c in grid
        },
    )
    gaps = gap_ledger_from_grid(filled)
    assert gaps == []


def test_explicit_gap_appears_in_ledger():
    evidence = _synthetic_evidence()
    grid = _grid(evidence)
    filled = apply_extraction_statuses(
        grid,
        cells_by_key={
            c["cell_id"]: {"status": "acquired_reported_verified", "fact_ids": ["f"]}
            for c in grid
            if c["role_id"] != "revenue"
        },
    )
    gaps = gap_ledger_from_grid(filled)
    assert any(g["role_id"] == "revenue" for g in gaps)
    assert all(g["status"] == "missing_official_filing" for g in gaps)


# ── readiness ─────────────────────────────────────────────────────────────


def test_3y_5y_readiness_recomputable():
    evidence = _synthetic_evidence()
    grid = _grid(evidence)
    filled = apply_extraction_statuses(
        grid,
        cells_by_key={
            c["cell_id"]: {"status": "acquired_reported_verified", "fact_ids": ["f"]}
            for c in grid
        },
    )
    gaps = gap_ledger_from_grid(filled)
    read = build_readiness(evidence, load_role_registry(), filled, gaps)
    # 2024 Q1..2025 Q1 covers the 3y window (2022 Q1+) for PE-TTM roles.
    assert isinstance(read["metrics"]["PE_TTM"]["3y_ready"], bool)
    # 2024 data alone cannot cover the 5y window back to 2020 Q1.
    assert read["metrics"]["PE_TTM"]["5y_ready"] is False


def test_readiness_blocks_on_missing_share_count():
    evidence = _synthetic_evidence()
    grid = _grid(evidence)
    filled = apply_extraction_statuses(
        grid,
        cells_by_key={
            c["cell_id"]: {"status": "acquired_reported_verified", "fact_ids": ["f"]}
            for c in grid
            if c["role_id"] != "total_ordinary_shares_at_period_end"
        },
    )
    gaps = gap_ledger_from_grid(filled)
    read = build_readiness(evidence, load_role_registry(), filled, gaps)
    assert "total_ordinary_shares_at_period_end" in read["metrics"]["PB_MRQ"]["blockers"]


# ── decision gate (fail-closed) ───────────────────────────────────────────


def test_gate_not_trusted_when_validator_fails():
    evidence = _synthetic_evidence()
    grid = _grid(evidence)
    filled = apply_extraction_statuses(
        grid,
        cells_by_key={
            c["cell_id"]: {"status": "acquired_reported_verified", "fact_ids": ["f"]}
            for c in grid
        },
    )
    gaps = gap_ledger_from_grid(filled)
    read = build_readiness(evidence, load_role_registry(), filled, gaps)
    gate = decide_from_readiness(
        read,
        cache_trusted=False,
        extraction_trusted=True,
        identity_trusted=True,
        pit_trusted=True,
    )
    assert gate == GATE_NOT_TRUSTED


def test_gate_gaps_remain_when_explicit_gaps():
    evidence = _synthetic_evidence()
    grid = _grid(evidence)
    filled = apply_extraction_statuses(
        grid,
        cells_by_key={
            c["cell_id"]: {"status": "acquired_reported_verified", "fact_ids": ["f"]}
            for c in grid
            if c["role_id"] != "revenue"
        },
    )
    gaps = gap_ledger_from_grid(filled)
    read = build_readiness(evidence, load_role_registry(), filled, gaps)
    gate = decide_from_readiness(
        read,
        cache_trusted=True,
        extraction_trusted=True,
        identity_trusted=True,
        pit_trusted=True,
    )
    assert gate == GATE_GAPS


def test_gate_ready_requires_warmup():
    # A full grid with only 2024-2025 data cannot satisfy the 5y warm-up.
    evidence = _synthetic_evidence()
    grid = _grid(evidence)
    filled = apply_extraction_statuses(
        grid,
        cells_by_key={
            c["cell_id"]: {"status": "acquired_reported_verified", "fact_ids": ["f"]}
            for c in grid
            if c["role_id"] != "total_ordinary_shares_at_period_end"
        },
    )
    gaps = gap_ledger_from_grid(filled)
    read = build_readiness(evidence, load_role_registry(), filled, gaps)
    gate = decide_from_readiness(
        read,
        cache_trusted=True,
        extraction_trusted=True,
        identity_trusted=True,
        pit_trusted=True,
    )
    assert gate in (GATE_GAPS, GATE_NOT_TRUSTED)


# ── boundaries ────────────────────────────────────────────────────────────


def test_no_pe_pb_ps_series_in_readiness():
    read_output = build_readiness(
        _synthetic_evidence(),
        load_role_registry(),
        _grid(_synthetic_evidence()),
        [],
    )
    for metric in ("PE_TTM", "PB_MRQ", "PS_TTM"):
        assert "series" not in read_output["metrics"][metric]
    assert read_output["historical_pe_pb_ps"] == "NOT_IMPLEMENTED"
    assert read_output["valuation_percentile"] == "NOT_IMPLEMENTED"


def test_score_and_peer_and_m3_unchanged():
    read_output = build_readiness(
        _synthetic_evidence(),
        load_role_registry(),
        _grid(_synthetic_evidence()),
        [],
    )
    assert read_output["peer_acquisition"] == "NOT_ALLOWED"
    assert read_output["m3_started"] is False
    assert read_output["default_db"] == "UNCHANGED"
    assert read_output["production_metric_results"] == "NOT_CREATED"


def test_restatement_rule_original_visible_until_restatement():
    from ashare_research.pit_valuation.reconciliation import build_version_lineage

    chain = build_version_lineage(
        concept_id="net_profit_attributable_to_parent",
        context_id="601857.SH|2025|quarter_ytd|consolidated",
        original_fact_id="orig-1",
        original_value=46809000000,
        original_available_at="2025-04-30",
        later_evidence=["R4D-SSE-2026-Q1"],
        restatement_facts=[
            {
                "fact_id": "rest-1",
                "value": 47452000000,
                "restatement_version": "restated_1",
                "available_at": "2026-04-30",
                "supersedes_fact_id": "orig-1",
            }
        ],
        conflicts=[],
        period_start="2025-01-01",
        period_end="2025-03-31",
    )
    assert chain["supersession"] == "original_visible_until_restatement"
    assert chain["restatement_fact_ids"] == ["rest-1"]
    assert chain["pit_selected_intervals"][0]["visible_from"] == "2026-04-30"


def test_unexplained_conflict_not_auto_selected():
    from ashare_research.pit_valuation.reconciliation import build_version_lineage

    chain = build_version_lineage(
        concept_id="revenue",
        context_id="601857.SH|2025|annual|consolidated",
        original_fact_id="o1",
        original_value=100,
        original_available_at="2026-03-30",
        later_evidence=["x"],
        restatement_facts=[],
        conflicts=["comparative value differs without a restatement note"],
        period_start="2025-01-01",
        period_end="2025-12-31",
    )
    assert chain["conflict_status"] == "source_conflict"
    assert chain["restatement_fact_ids"] == []


# ── synthetic formal pipeline (CI runs this offline) ──────────────────────


def test_synthetic_formal_pipeline_gate(tmp_path):
    """Chain verify -> extract -> facts -> readiness -> gate entirely offline.

    Synthetic official-report fixtures only; no real PDF, no network, no
    default DB.  The gate must be fail-closed (GAPS_REMAIN or NOT_TRUSTED)
    because the synthetic register does not cover the full warm-up window.
    """
    import hashlib

    from ashare_research.pit_valuation import readiness as readiness_mod
    from ashare_research.pit_valuation.extraction import extract_filing
    from ashare_research.pit_valuation.fact_builder import build_reported_fact
    from ashare_research.pit_valuation.source_cache import verify_official_cache

    # Synthetic official cache root (outside the repo).
    cache_root = tmp_path / "cache"
    (cache_root / "objects").mkdir(parents=True)
    pdf_bytes = _valid_minimal_pdf()
    sha = hashlib.sha256(pdf_bytes).hexdigest()
    (cache_root / "objects" / f"{sha}.pdf").write_bytes(pdf_bytes)

    registry = {
        "schema": "pit_valuation_official_cache_registry_v1",
        "objects": [
            {
                "object_key": f"objects/{sha}.pdf",
                "sha256": sha,
                "byte_size": len(pdf_bytes),
                "page_count": 1,
                "media_type": "application/pdf",
                "evidence_ids": ["R4D-SSE-2024-Q1"],
            }
        ],
    }
    ev = {
        "R4D-SSE-2024-Q1": {
            "evidence_id": "R4D-SSE-2024-Q1",
            "announcement_date": "2024-04-30",
            "fiscal_year": 2024,
            "report_type": "q1",
            "period_start": "2024-01-01",
            "period_end": "2024-03-31",
        }
    }
    ver = verify_official_cache(cache_root, registry=registry, evidence_map=ev)
    assert ver["all_objects_ok"]

    # Synthetic CAS page text for the fixture.
    pages = [
        "2.1.2 按中国企业会计准则编制的主要会计数据及财务指标\n"
        "项目 年初至报告期末 上年初至上年报告期末 比上年同期增减\n"
        "营业收入 812,184 732,471 10.9\n"
        "归属于母公司股东的净利润 45,681 43,630 4.7\n"
        "基本每股收益（人民币元） 0.25 0.24 4.7\n"
        "归属于母公司股东权益 1,491,375 1,446,410 3.1\n",
    ]
    spec_pool = load_specs()
    entry = {
        "evidence_id": "R4D-SSE-2024-Q1",
        "announcement_date": "2024-04-30",
        "fiscal_year": 2024,
        "report_type": "q1",
        "proof_url": "https://example.invalid/x.pdf",
        "report_title": "synthetic",
        "source_role": "exchange_official",
    }
    cells = [
        c
        for c in extract_filing(
            Path("x.pdf"),
            entry,
            [s for s in spec_pool if s["report_type"] == "q1"],
            page_texts=pages,
        )
        if c.status == "acquired_reported_verified"
    ]
    # The synthetic fixture has 4 acquired cells.
    assert len(cells) == 4

    # Build facts with a synthetic calendar.  The calendar must include a
    # trading day on/before the announcement (2024-04-30) to cover it; under
    # the R4D.1a fail-closed contract a calendar whose first trading day is
    # after the announcement would be a coverage gap, never a backfill.
    calendar = {
        "calendar_object_id": "synthetic.parquet",
        "calendar_sha256": "0" * 64,
        "trade_dates": ["2024-04-26", "2024-05-06"],
    }
    roles = load_role_registry()
    facts = []
    for cell in cells:
        role = next(r for r in roles["roles"] if r["role_id"] == cell.role_id)
        facts.append(build_reported_fact(cell, entry, role, market_calendar=calendar))
    assert len(facts) == 4
    for fact in facts:
        assert fact["available_at"] == "2024-04-30"
        assert fact["effective_from"] == "2024-05-06"

    # Readiness with the committed (real) register would be misleading here, so
    # build the grid from the synthetic register and assert a fail-closed gate.
    synthetic_evidence = {
        "schema": "pit_valuation_official_source_evidence_v1",
        "entries": [ev["R4D-SSE-2024-Q1"]],
    }
    grid = readiness_mod.build_expected_grid(synthetic_evidence, roles)
    cells_by_key = {
        f"{c.evidence_id}:{c.role_id}": {"status": "acquired_reported_verified", "fact_ids": []}
        for c in cells
    }
    filled = readiness_mod.apply_extraction_statuses(grid, cells_by_key=cells_by_key)
    gaps = readiness_mod.gap_ledger_from_grid(filled)
    read = readiness_mod.build_readiness(synthetic_evidence, roles, filled, gaps)
    gate = readiness_mod.decide_from_readiness(
        read,
        cache_trusted=ver["all_objects_ok"],
        extraction_trusted=True,
        identity_trusted=True,
        pit_trusted=True,
    )
    # Missing cells (weighted shares, share count, 5y window) -> fail closed.
    assert gate in (GATE_GAPS, GATE_NOT_TRUSTED)


def load_specs():
    from ashare_research.pit_valuation.contracts import load_extraction_specs

    return load_extraction_specs()["specs"]


def test_later_comparative_does_not_backfill_history():

    from ashare_research.pit_valuation.extraction import ExtractedCell
    from ashare_research.pit_valuation.reconciliation import detect_restatements

    # Original 2025-Q1 net profit = 46,809 (from the 2025-Q1 filing).
    original = {
        "fact_id": "orig-1",
        "concept_id": "net_profit_attributable_to_parent",
        "context_id": "601857.SH|2025|quarter_ytd|consolidated",
        "value": 46809000000.0,
        "available_at": "2025-04-30",
        "source_id": "r4d:R4D-SSE-2025-Q1",
        "restatement_version": "original",
        "fact_version": 1,
    }
    # The 2026-Q1 filing prints the (追溯后) 47,452 and (追溯前) 46,809.
    cell = ExtractedCell(
        extraction_spec_id="x",
        role_id="net_profit_attributable_to_parent",
        evidence_id="R4D-SSE-2026-Q1",
        report_type="q1",
        fiscal_year=2026,
        raw_token="48,333",
        tokens=["48,333", "47,452", "46,809", "1.9"],
        has_restatement_comparatives=True,
        conversion_multiplier="1000000",
        status="acquired_reported_verified",
    )
    evidence_map = {
        "R4D-SSE-2025-Q1": {
            "evidence_id": "R4D-SSE-2025-Q1",
            "report_type": "q1",
            "fiscal_year": 2025,
            "announcement_date": "2025-04-30",
            "period_end": "2025-03-31",
        },
        "R4D-SSE-2026-Q1": {
            "evidence_id": "R4D-SSE-2026-Q1",
            "report_type": "q1",
            "fiscal_year": 2026,
            "announcement_date": "2026-04-30",
            "period_end": "2026-03-31",
            "proof_url": "https://example.invalid/2026q1.pdf",
        },
    }
    restated, lineage = detect_restatements([cell], [original], evidence_map)
    assert len(restated) == 1
    r = restated[0]
    # The restated value is the (追溯后) comparative, not the original.
    assert r["value"] == 47452000000.0
    # The restated version becomes visible only at the later announcement.
    assert r["available_at"] == "2026-04-30"
    assert r["supersedes_fact_id"] == "orig-1"
    assert r["restatement_version"] == "restated_1"
    # The original fact stays visible before the restatement (PIT interval).
    assert lineage[0]["pit_selected_intervals"][0]["visible_from"] == "2026-04-30"


def _valid_minimal_pdf() -> bytes:
    """A minimal but structurally valid single-page PDF (pypdf-parseable)."""
    objs = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 200 200] >>",
    ]
    out = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for i, o in enumerate(objs, 1):
        offsets.append(len(out))
        out += f"{i} 0 obj\n".encode() + o + b"\nendobj\n"
    xref_pos = len(out)
    out += b"xref\n0 4\n0000000000 65535 f \n"
    for off in offsets[1:]:
        out += f"{off:010d} 00000 n \n".encode()
    out += b"trailer\n<< /Size 4 /Root 1 0 R >>\nstartxref\n"
    out += f"{xref_pos}\n".encode() + b"%%EOF"
    return bytes(out)
