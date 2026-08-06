"""M2 Stage 2K.1R4E — deterministic synthetic fixtures for CI.

These fixtures exercise the frozen formula and PIT time semantics (annual/Q1/
H1/Q3 TTM, restatement PIT behaviour, exact price join, backward financial-state
join, constant share basis) without any real market cache.  They are used only
by the ``fixtures`` CLI command and the offline test suite; they never stand in
for the formal candidate series.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from ashare_research.pit_valuation.series_contract import (
    CONSTANT_TOTAL_SHARES,
    SYMBOL,
    canonical_digest,
)

REPORT_TYPES_ORDER = ("q1", "half_year", "q3", "annual")
PERIOD_END = {"q1": "03-31", "half_year": "06-30", "q3": "09-30", "annual": "12-31"}

# Deterministic synthetic values (CNY).  Base values scaled per year/period.
_NET_PROFIT_BASE = 40000000000
_REVENUE_BASE = 900000000000
_EQUITY_BASE = 1500000000000


def _fact(
    concept_id: str,
    year: int,
    report_type: str,
    value: float,
    effective_from: str,
    available_at: str,
    *,
    restatement_version: str = "original",
    supersedes_fact_id: str = "",
    source_id: str = "",
) -> dict[str, Any]:
    period_end = f"{year}-{PERIOD_END[report_type]}"
    payload = {
        "concept_id": concept_id,
        "symbol": SYMBOL,
        "period_end": period_end,
        "value": value,
        "available_at": available_at,
        "effective_from": effective_from,
        "restatement_version": restatement_version,
        "supersedes_fact_id": supersedes_fact_id,
        "source_id": source_id,
    }
    fact = {
        "fact_id": canonical_digest(payload),
        "concept_id": concept_id,
        "symbol": SYMBOL,
        "value": value,
        "period_end": period_end,
        "available_at": available_at,
        "effective_from": effective_from,
        "restatement_version": restatement_version,
        "supersedes_fact_id": supersedes_fact_id,
        "source_id": source_id,
        "context_id": f"{SYMBOL}|{year}||consolidated",
    }
    return fact


def _effective_from(year: int, report_type: str) -> str:
    """Deterministic next-trade-day approximation for a filing."""
    end = f"{year}-{PERIOD_END[report_type]}"
    base = date.fromisoformat(end) + timedelta(days=30)
    # Step to a weekday (deterministic).
    while base.weekday() >= 5:
        base += timedelta(days=1)
    return base.isoformat()


def load_fixture_bundles(fixture_root: Any) -> tuple[list[dict], list[dict]]:
    """Return deterministic synthetic reported/reconciled fact bundles."""
    reported: list[dict] = []
    for year in range(2020, 2027):
        for report_type in REPORT_TYPES_ORDER:
            if year == 2026 and report_type != "q1":
                continue
            eff = _effective_from(year, report_type)
            avail = _effective_from(year, report_type)
            period_end = f"{year}-{PERIOD_END[report_type]}"
            # net_profit / revenue are cumulative; equity is instant period-end.
            reported.append(
                _fact(
                    "net_profit_attributable_to_parent",
                    year,
                    report_type,
                    float(_NET_PROFIT_BASE * (year - 2019) + _cumulative_seed(report_type)),
                    eff,
                    avail,
                    source_id=f"r4d:SYN-{year}-{report_type}",
                )
            )
            reported.append(
                _fact(
                    "revenue",
                    year,
                    report_type,
                    float(_REVENUE_BASE * (year - 2019) + _cumulative_seed(report_type)),
                    eff,
                    avail,
                    source_id=f"r4d:SYN-{year}-{report_type}",
                )
            )
            reported.append(
                _fact(
                    "equity_attributable_to_parent",
                    year,
                    report_type,
                    float(_EQUITY_BASE + (year - 2019) * 30000000000 + _period_seed(report_type)),
                    eff,
                    avail,
                    source_id=f"r4d:SYN-{year}-{report_type}",
                )
            )
            if report_type in ("half_year", "annual"):
                reported.append(
                    _fact(
                        "total_ordinary_shares_at_period_end",
                        year,
                        report_type,
                        float(CONSTANT_TOTAL_SHARES),
                        eff,
                        avail,
                        source_id=f"r4d:SYN-{year}-{report_type}",
                    )
                )
            _ = period_end

    # A restatement: 2022 Q1 net profit announced again (restated) in 2023 Q1.
    q1_2022_orig = next(
        f for f in reported
        if f["concept_id"] == "net_profit_attributable_to_parent"
        and f["period_end"] == "2022-03-31" and f["restatement_version"] == "original"
    )
    reported.append(
        _fact(
            "net_profit_attributable_to_parent",
            2022,
            "q1",
            float(_NET_PROFIT_BASE * 3 + 123456789),
            _effective_from(2023, "q1"),
            _effective_from(2023, "q1"),
            restatement_version="restated_1",
            supersedes_fact_id=q1_2022_orig["fact_id"],
            source_id="r4d:SYN-2023-q1",
        )
    )

    # Reconciled: derived Q1/Q3 period-end shares and weighted shares (constant).
    reconciled: list[dict] = []
    for year in range(2020, 2027):
        for report_type in REPORT_TYPES_ORDER:
            if year == 2026 and report_type != "q1":
                continue
            eff = _effective_from(year, report_type)
            avail = _effective_from(year, report_type)
            if report_type in ("q1", "q3"):
                reconciled.append(
                    _fact(
                        "total_ordinary_shares_at_period_end",
                        year,
                        report_type,
                        float(CONSTANT_TOTAL_SHARES),
                        eff,
                        avail,
                        source_id=f"r4d:SYN-{year}-{report_type}",
                    )
                )
            reconciled.append(
                _fact(
                    "weighted_average_total_ordinary_shares",
                    year,
                    report_type,
                    float(CONSTANT_TOTAL_SHARES),
                    eff,
                    avail,
                    source_id=f"r4d:SYN-{year}-{report_type}",
                )
            )
    return reported, reconciled


def _cumulative_seed(report_type: str) -> int:
    return {"q1": 0, "half_year": 3000000000, "q3": 6000000000, "annual": 9000000000}[report_type]


def _period_seed(report_type: str) -> int:
    return {"q1": 0, "half_year": -1000000000, "q3": 2000000000, "annual": 4000000000}[report_type]


def load_fixture_market(fixture_root: Any) -> tuple[list[dict], list[dict]]:
    """Deterministic synthetic A-share close series (no real cache)."""
    rows: list[dict] = []
    d = date(2021, 1, 4)
    end = date(2026, 7, 31)
    close = 5.0
    while d <= end:
        if d.weekday() < 5:
            close = round(close + 0.01, 2)
            rows.append({"trade_date": d.isoformat(), "close": close})
        d += timedelta(days=1)
    meta = {
        "primary_provider": "baostock",
        "primary_object_sha256": "synthetic" + "0" * 57,
        "primary_object_key": "synthetic/baostock.parquet",
        "primary_row_count": len(rows),
        "secondary_provider": "akshare",
        "secondary_object_sha256": "synthetic" + "1" * 57,
        "secondary_object_key": "synthetic/akshare.parquet",
        "secondary_present": True,
        "secondary_verified": True,
        "reconciliation_status": "pass",
        "reconciliation_contract_digest": "synthetic-reconciliation",
        "market_rows": len(rows),
        "first_trade_date": rows[0]["trade_date"],
        "last_trade_date": rows[-1]["trade_date"],
    }
    return rows, meta
