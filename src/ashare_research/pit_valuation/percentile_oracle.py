"""M2 Stage 2K.1R4E.5 — independent DuckDB percentile oracle.

A second, independent implementation of the frozen midrank empirical
percentile so the Python core is cross-checked by a different engine.  It reads
the trusted candidate observations into an isolated in-memory DuckDB and
computes, per metric/window, the exact counts N / L / E / G and the exact
rational ``rank_numerator / rank_denominator``.

It deliberately does **not** use ``percent_rank()`` (its ranking convention
differs from the frozen midrank contract) and does **not** use ``cume_dist()``
as the official percentile.  Ratio comparisons are exact ``DECIMAL``
comparisons (``DECIMAL(38,28)`` holds every candidate ratio), never float.

This module never opens the default database and never touches the network.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ashare_research.pit_valuation.series_contract import SYMBOL

from .historical_percentile import (
    AS_OF_TRADE_DATE,
    METRICS,
    RANK_METHOD,
    WINDOW_EFFECTIVE_FIRST,
    WINDOW_IDS,
)

# Exact domain for every candidate ratio (max 2 integer + 28 fractional digits).
_RATIO_TYPE = "DECIMAL(38,28)"


def _load_candidate(candidate_path: Path) -> dict[str, Any]:
    with candidate_path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def _rows(candidate: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "metric_id": o.get("metric_id", ""),
            "trade_date": str(o.get("trade_date", "")),
            "status": o.get("status", ""),
            "ratio_str": (str(o["ratio_decimal"]) if o.get("ratio_decimal") is not None else None),
            "observation_id": o.get("observation_id", ""),
        }
        for o in candidate["observations"]
    ]


def _run_duckdb(candidate: dict[str, Any]) -> dict[str, Any]:
    import duckdb
    import pandas as pd

    rows = _rows(candidate)
    df = pd.DataFrame(rows)
    con = duckdb.connect(":memory:")
    con.register("src", df)
    con.execute(f"""
        CREATE OR REPLACE TEMP TABLE obs AS
        SELECT metric_id, trade_date, status, observation_id,
               TRY_CAST(ratio_str AS {_RATIO_TYPE}) AS ratio
        FROM src
    """)
    results: dict[str, dict[str, Any]] = {}
    for metric in METRICS:
        for wid in WINDOW_IDS:
            eff = WINDOW_EFFECTIVE_FIRST[wid]
            # Independently re-derive the exact as-of current ratio.
            cur = con.execute(
                """
                SELECT ratio
                FROM obs
                WHERE metric_id = ? AND trade_date = ? AND status = 'computed'
                      AND ratio IS NOT NULL
                """,
                [metric, AS_OF_TRADE_DATE],
            ).fetchall()
            if len(cur) != 1:
                raise ValueError(
                    f"{metric}/{wid}: {len(cur)} as-of current ratios (need exactly 1)"
                )
            current = cur[0][0]
            row = con.execute(
                """
                SELECT COUNT(*) AS N,
                       SUM(CASE WHEN ratio < ? THEN 1 ELSE 0 END) AS L,
                       SUM(CASE WHEN ratio = ? THEN 1 ELSE 0 END) AS E,
                       SUM(CASE WHEN ratio > ? THEN 1 ELSE 0 END) AS G
                FROM obs
                WHERE metric_id = ? AND status = 'computed'
                      AND ratio IS NOT NULL AND ratio > 0
                      AND trade_date >= ? AND trade_date <= ?
                """,
                [current, current, current, metric, eff, AS_OF_TRADE_DATE],
            ).fetchone()
            n, less, e, g = int(row[0]), int(row[1]), int(row[2]), int(row[3])
            if n != less + e + g:
                raise ValueError(f"{metric}/{wid}: N != L+E+G in oracle")
            results[f"{metric}/{wid}"] = {
                "N": n,
                "L": less,
                "E": e,
                "G": g,
                "rank_numerator": 2 * less + e + 1,
                "rank_denominator": 2 * n,
            }
    con.close()
    return results


def build_dual_oracle_report(candidate_path: Path) -> dict[str, Any]:
    """Run the independent DuckDB oracle and return its per-window results."""
    candidate = _load_candidate(candidate_path)
    duckdb_results = _run_duckdb(candidate)
    return {
        "schema": "petrochina_pit_valuation_percentile_dual_oracle_v1",
        "version": "1.0",
        "symbol": SYMBOL,
        "as_of_trade_date": AS_OF_TRADE_DATE,
        "rank_method": RANK_METHOD,
        "oracle_engine": "DuckDB in-memory; exact DECIMAL(38,28) comparison; percent_rank NOT used",
        "per_window": duckdb_results,
    }


def compare_oracles(
    python_records: list[dict[str, Any]],
    duckdb_report: dict[str, Any],
) -> dict[str, Any]:
    """Compare the 6 Python records against the DuckDB oracle results.

    Returns a per-window comparison and an ``all_identical`` flag.  Raises
    :class:`ValueError` on any mismatch (NOT_TRUSTED).
    """
    comparisons: list[dict[str, Any]] = []
    all_identical = True
    for rec in python_records:
        key = f"{rec['metric_id']}/{rec['window_id']}"
        db = duckdb_report["per_window"].get(key)
        py = {
            "N": rec["eligible_sample_count"],
            "L": rec["count_less"],
            "E": rec["count_equal"],
            "G": rec["count_greater"],
            "rank_numerator": rec["rank_numerator"],
            "rank_denominator": rec["rank_denominator"],
        }
        identical = db is not None and py == db
        all_identical = all_identical and identical
        comparisons.append(
            {
                "metric_id": rec["metric_id"],
                "window_id": rec["window_id"],
                "python": py,
                "duckdb": db,
                "identical": identical,
            }
        )
    if not all_identical:
        raise ValueError("Python/DuckDB percentile oracle mismatch")
    return {
        "schema": "petrochina_pit_valuation_percentile_dual_oracle_v1",
        "version": "1.0",
        "symbol": SYMBOL,
        "as_of_trade_date": AS_OF_TRADE_DATE,
        "rank_method": RANK_METHOD,
        "all_identical": True,
        "comparisons": comparisons,
    }
