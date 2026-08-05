"""M2 Stage 2K.1R4D — coverage matrix, gap ledger and three-state readiness.

The expected grid is generated from the frozen filing register (filing periods
x required roles x applicable contexts), never hand-written.  Every expected
cell carries exactly one status; the gap ledger is recomputed from the grid.
Readiness is judged per metric (PE-TTM / PB-MRQ / PS-TTM) for the 3y and 5y
warm-up windows.  The decision gate is fail-closed.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ashare_research.pit_valuation.contracts import (
    PERIOD_TYPE_BY_REPORT,
    SYMBOL,
    decide_gate,
)

ROOT = Path(__file__).resolve().parents[3]

# Required roles per metric (from the frozen acquisition plan).
METRIC_ROLES = {
    "PE_TTM": ["net_profit_attributable_to_parent", "weighted_average_total_ordinary_shares"],
    "PB_MRQ": ["equity_attributable_to_parent", "total_ordinary_shares_at_period_end"],
    "PS_TTM": ["revenue", "total_ordinary_shares_at_period_end"],
}

# Warm-up windows.  A 5y window from 2021-07-31 needs quarterly cumulative
# data from 2020 Q1; a 3y window needs 2022 Q1 onwards.
WARMUP_3Y = {"start_year": 2022, "start_report": "q1"}
WARMUP_5Y = {"start_year": 2020, "start_report": "q1"}

# Roles that are only disclosed (or derivable from) half-year and annual
# filings.  The weighted-average share count is expected for every period
# (PE-TTM needs it for Q1/Q3 too), so only the period-end share count is
# restricted to half-year/annual filings.
PERIOD_END_SHARE_ROLE = "total_ordinary_shares_at_period_end"
INTERIM_ANNUAL_TYPES = ("half_year", "annual")


def build_expected_grid(evidence: dict[str, Any], roles: dict[str, Any]) -> list[dict[str, Any]]:
    """Generate the expected cell grid from the filing register.

    One grid row per filing period (exchange_official evidence only) x every
    required role (reported and derived).  A byte-identical issuer alias
    shares the same filing period and must not double the grid.
    """
    grid: list[dict[str, Any]] = []
    all_roles = [r["role_id"] for r in roles["roles"]]
    filings = [
        e for e in evidence["entries"] if e.get("source_role") == "exchange_official"
    ]
    for entry in sorted(filings, key=lambda e: (e["fiscal_year"], e["report_type"])):
        for role_id in all_roles:
            report_type = entry["report_type"]
            role = next(r for r in roles["roles"] if r["role_id"] == role_id)
            if role_id == PERIOD_END_SHARE_ROLE:
                # The precise period-end share count is directly disclosed in
                # half-year/annual filings; for Q1/Q3 it may only be derived
                # from the frozen share-continuity constant (never guessed).
                # The Q1/Q3 cells are always part of the grid; whether they are
                # acquired depends on the register trust, not on the grid shape.
                expected_direct = report_type in INTERIM_ANNUAL_TYPES
            else:
                expected_direct = role["direct_or_derived"] == "reported"
            period_type = (
                "instant"
                if role["instant_or_duration"] == "instant"
                else PERIOD_TYPE_BY_REPORT[report_type]
            )
            grid.append(
                {
                    "cell_id": f"{entry['evidence_id']}:{role_id}",
                    "report_id": entry["evidence_id"],
                    "role_id": role_id,
                    "concept_id": role["concept_id"],
                    "fiscal_year": entry["fiscal_year"],
                    "report_type": report_type,
                    "period_type": period_type,
                    "period_start": f"{entry['fiscal_year']}-01-01",
                    "period_end": entry["period_end"],
                    "instant_or_duration": role["instant_or_duration"],
                    "required": "required"
                    if role_id in METRIC_ROLES["PE_TTM"] + METRIC_ROLES["PB_MRQ"]
                    + METRIC_ROLES["PS_TTM"]
                    else "optional",
                    "expected_direct_disclosure": expected_direct,
                    "allowed_derived_fallback": (
                        role_id == "weighted_average_total_ordinary_shares"
                        or role_id == PERIOD_END_SHARE_ROLE
                    ),
                    "acquisition_status": "missing_official_filing",
                    "fact_ids": [],
                    "gap_ids": [],
                }
            )
    return grid


def apply_extraction_statuses(
    grid: list[dict[str, Any]],
    *,
    cells_by_key: dict[str, dict[str, Any]],
    status_overrides: dict[str, str] | None = None,
) -> list[dict[str, Any]]:
    """Merge extraction outcomes into the expected grid."""
    status_overrides = status_overrides or {}
    for cell in grid:
        key = cell["cell_id"]
        detail = cells_by_key.get(key)
        if detail is None:
            cell["acquisition_status"] = "missing_official_filing"
            if key in status_overrides:
                cell["acquisition_status"] = status_overrides[key]
            continue
        status = detail.get("status", "missing_official_filing")
        cell["acquisition_status"] = status
        cell["fact_ids"] = detail.get("fact_ids", [])
        cell["gap_ids"] = detail.get("gap_ids", [])
    return grid


def validate_coverage_fact_gap_binding(
    grid: list[dict[str, Any]],
    gaps: list[dict[str, Any]],
    facts: list[dict[str, Any]],
    *,
    require_acquired_fact_ids: bool = True,
) -> dict[str, Any]:
    """Bidirectional integrity check between grid, gap ledger and fact bundles.

    - every acquired cell must reference a real ``fact_id`` present in the
      bundles;
    - every non-acquired (gap) cell must reference a real ``gap_id`` present
      in the ledger;
    - every ledger gap must bind back to a grid cell carrying its ``gap_id``;
    - every bundle fact must be referenced by exactly one grid cell.

    Returns ``{ok, errors, ...}``.  Any violation fails the binding closed.
    """
    errors: list[str] = []
    bundle_fact_ids = {f["fact_id"] for f in facts}
    ledger_by_gap = {g["gap_id"]: g for g in gaps}
    grid_by_cell = {c["cell_id"]: c for c in grid}
    acquired_statuses = {
        "acquired_reported_verified",
        "acquired_dual_official_reconciled",
        "acquired_reconciled_derived",
    }

    referenced_fact_ids: set[str] = set()
    for cell in grid:
        cell_id = cell["cell_id"]
        status = cell["acquisition_status"]
        fact_ids = cell.get("fact_ids") or []
        gap_ids = cell.get("gap_ids") or []
        if status in acquired_statuses:
            if require_acquired_fact_ids and not fact_ids:
                errors.append(f"acquired cell {cell_id} has no fact_id")
            for fid in fact_ids:
                referenced_fact_ids.add(fid)
                if fid not in bundle_fact_ids:
                    errors.append(f"cell {cell_id} references unknown fact {fid}")
        else:
            if not gap_ids:
                errors.append(f"non-acquired cell {cell_id} has no gap_id")
            for gid in gap_ids:
                if gid not in ledger_by_gap:
                    errors.append(f"cell {cell_id} references unknown gap {gid}")
                elif ledger_by_gap[gid]["cell_id"] != cell_id:
                    errors.append(f"gap {gid} cell binding mismatch")

    for gap in gaps:
        cell = grid_by_cell.get(gap["cell_id"])
        if cell is None:
            errors.append(
                f"ledger gap {gap['gap_id']} references missing cell {gap['cell_id']}"
            )
        elif gap["gap_id"] not in (cell.get("gap_ids") or []):
            errors.append(f"grid cell {gap['cell_id']} does not bind gap {gap['gap_id']}")

    for fid in bundle_fact_ids:
        refs = [c for c in grid if fid in (c.get("fact_ids") or [])]
        if len(refs) != 1:
            errors.append(f"fact {fid} referenced by {len(refs)} grid cells (expected 1)")

    return {
        "ok": not errors,
        "errors": errors,
        "grid_cells": len(grid),
        "gap_ledger_entries": len(gaps),
        "bundle_facts": len(facts),
        "referenced_fact_count": len(referenced_fact_ids),
    }


def gap_ledger_from_grid(grid: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Recompute the gap ledger from the grid (never hand-written).

    Also binds each gap back to its grid cell by writing the ``gap_id`` onto
    the cell, so cell -> gap and gap -> cell are both traceable.
    """
    gaps: list[dict[str, Any]] = []
    for cell in grid:
        status = cell["acquisition_status"]
        if status in (
                "acquired_reported_verified",
                "acquired_dual_official_reconciled",
                "acquired_reconciled_derived",
                "not_applicable",
            ):
            continue
        description = ""
        if status == "weighted_average_share_ambiguous_due_to_eps_rounding":
            description = (
                "basic EPS is rounded to 2-3 decimals; parent net profit / "
                "basic EPS cannot uniquely determine the weighted-average "
                "share count (report directly discloses no weighted-average "
                "share count)"
            )
        gap_id = f"R4D-{cell['report_id']}-{cell['role_id']}"
        cell["gap_ids"] = [gap_id]
        gaps.append(
            {
                "gap_id": gap_id,
                "cell_id": cell["cell_id"],
                "report_id": cell["report_id"],
                "role_id": cell["role_id"],
                "fiscal_year": cell["fiscal_year"],
                "report_type": cell["report_type"],
                "period_end": cell["period_end"],
                "status": status,
                "description": description,
            }
        )
    return gaps


def readiness_for_metric(
    metric_id: str,
    grid: list[dict[str, Any]],
    gaps: list[dict[str, Any]],
) -> dict[str, Any]:
    """Compute direct/derived coverage and 3y/5y readiness for one metric."""
    roles = METRIC_ROLES[metric_id]
    relevant = [c for c in grid if c["role_id"] in roles]
    acquired_statuses = {
        "acquired_reported_verified",
        "acquired_dual_official_reconciled",
        "acquired_reconciled_derived",
    }

    def window_ready(window: dict[str, int], role_id: str) -> bool:
        start_year = window["start_year"]
        expected = [
            c
            for c in relevant
            if c["role_id"] == role_id and c["fiscal_year"] >= start_year
        ]
        if not expected:
            return False
        # The register must actually cover the window start; a register that
        # only spans recent years cannot satisfy a 5y warm-up.
        earliest = min(
            c["fiscal_year"] for c in relevant if c["role_id"] == role_id
        )
        if earliest > start_year:
            return False
        acquired = [
            c for c in expected if c["acquisition_status"] in acquired_statuses
        ]
        return len(acquired) == len(expected)

    per_role: dict[str, dict[str, Any]] = {}
    for role_id in roles:
        role_cells = [c for c in relevant if c["role_id"] == role_id]
        acquired = [c for c in role_cells if c["acquisition_status"] in acquired_statuses]
        missing = [c for c in role_cells if c["acquisition_status"] == "missing_official_filing"]
        conflict = [c for c in role_cells if c["acquisition_status"] == "source_conflict"]
        per_role[role_id] = {
            "direct_fact_coverage": sum(
                1 for c in acquired
                if c["acquisition_status"]
                in ("acquired_reported_verified", "acquired_dual_official_reconciled")
            ),
            "derived_fact_coverage": sum(
                1 for c in acquired if c["acquisition_status"] == "acquired_reconciled_derived"
            ),
            "missing_cells": [c["cell_id"] for c in missing],
            "conflict_cells": [c["cell_id"] for c in conflict],
            "earliest_pit_ready_date": min((c["period_end"] for c in acquired), default=""),
            "latest_pit_ready_date": max((c["period_end"] for c in acquired), default=""),
            "3y_ready": window_ready(WARMUP_3Y, role_id),
            "5y_ready": window_ready(WARMUP_5Y, role_id),
        }

    role_ids = list(per_role.keys())
    return {
        "metric_id": metric_id,
        "roles": per_role,
        "3y_ready": all(per_role[r]["3y_ready"] for r in role_ids),
        "5y_ready": all(per_role[r]["5y_ready"] for r in role_ids),
        "blockers": [
            r for r in role_ids
            if not (per_role[r]["3y_ready"] or per_role[r]["5y_ready"])
        ],
        "prohibited_fallback": "no third-party or commercial per-share fallback is allowed",
    }


def build_readiness(
    evidence: dict[str, Any],
    roles: dict[str, Any],
    grid: list[dict[str, Any]],
    gaps: list[dict[str, Any]],
) -> dict[str, Any]:
    """Assemble the readiness report and the three-state gate inputs."""
    metrics = {
        "PE_TTM": readiness_for_metric("PE_TTM", grid, gaps),
        "PB_MRQ": readiness_for_metric("PB_MRQ", grid, gaps),
        "PS_TTM": readiness_for_metric("PS_TTM", grid, gaps),
    }
    explicit_gaps = len(gaps)
    source_conflicts = sum(1 for g in gaps if g["status"] == "source_conflict")

    # The gate is fail-closed.  The caller supplies the engineering-trust flags.
    return {
        "symbol": SYMBOL,
        "metrics": metrics,
        "explicit_gaps": explicit_gaps,
        "source_conflicts": source_conflicts,
        "default_db": "UNCHANGED",
        "production_metric_results": "NOT_CREATED",
        "historical_pe_pb_ps": "NOT_IMPLEMENTED",
        "valuation_percentile": "NOT_IMPLEMENTED",
        "peer_acquisition": "NOT_ALLOWED",
        "m3_started": False,
    }


def decide_from_readiness(
    readiness: dict[str, Any],
    *,
    cache_trusted: bool,
    extraction_trusted: bool,
    identity_trusted: bool,
    pit_trusted: bool,
) -> str:
    """Three-state gate driven by the readiness report."""
    gaps = readiness["explicit_gaps"]
    conflicts = readiness["source_conflicts"]
    warmup_ready = any(
        readiness["metrics"][m]["3y_ready"] or readiness["metrics"][m]["5y_ready"]
        for m in ("PE_TTM", "PB_MRQ", "PS_TTM")
    )
    return decide_gate(
        cache_trusted=cache_trusted,
        extraction_trusted=extraction_trusted,
        identity_trusted=identity_trusted,
        pit_trusted=pit_trusted,
        source_conflicts=conflicts,
        explicit_gaps=gaps,
        warmup_ready=warmup_ready,
    )


def write_report(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
    )
