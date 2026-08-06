"""M2 Stage 2K.1R4E — dual-oracle backward temporal join.

Two independent implementations of the frozen financial-state join:

- A. Pure-Python ordered backward sweep: market rows strictly increasing by
  ``trade_date``, financial states strictly increasing by ``effective_from``,
  a single forward cursor, at most one state per trade date.
- B. DuckDB ASOF LEFT JOIN run only in an isolated in-memory database, grouped
  by symbol/metric, on ``trade_date >= effective_from``.

Orthogonal to the than-engine: the two oracles must agree row-by-row on the
selected ``financial_state_id``, ``effective_from``, ``input_fact_ids``,
``value_decimal`` and ``status`` or the series is not trusted.  The DuckDB
oracle never writes the default database.
"""

from __future__ import annotations

from typing import Any

_REPORT_ORDER = {"q1": 0, "half_year": 1, "q3": 2, "annual": 3}


def dedup_states_by_effective_from(states: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Collapse states sharing an ``effective_from`` to the latest report period.

    The frozen timeline requires strictly increasing ``effective_from``.  If a
    restatement of an older period coincides with a newer period's primary
    effective_from, the later report period wins (it is the current state).
    """
    best: dict[str, dict[str, Any]] = {}
    for state in states:
        eff = state.get("effective_from", "")
        cur = best.get(eff)
        if cur is None or _period_rank(state) > _period_rank(cur):
            best[eff] = state
    return [best[e] for e in sorted(best.keys())]


def _period_rank(state: dict[str, Any]) -> tuple[int, int]:
    return (
        int(state.get("fiscal_year", -1)),
        _REPORT_ORDER.get(state.get("report_type", ""), -1),
    )


def _selected_fields(state: dict[str, Any] | None) -> dict[str, Any] | None:
    if state is None:
        return None
    return {
        "financial_state_id": state.get("financial_state_id", ""),
        "effective_from": state.get("effective_from", ""),
        "value_decimal": state.get("value_decimal"),
        "status": state.get("status", ""),
        "fiscal_year": state.get("fiscal_year"),
        "report_type": state.get("report_type", ""),
        "period_end": state.get("period_end", ""),
        "input_fact_ids": state.get("input_fact_ids"),
        "available_at_max": state.get("available_at_max", ""),
        "share_basis_decimal": state.get("share_basis_decimal"),
        "period_end_shares_decimal": state.get("period_end_shares_decimal"),
        "share_continuity_proof_id": state.get("share_continuity_proof_id", ""),
    }


# ── Oracle A: pure-Python ordered backward sweep ──────────────────────────


def python_backward_join(
    market_rows: list[dict[str, Any]],
    states: list[dict[str, Any]],
) -> dict[str, dict[str, Any] | None]:
    """Backward join: latest state with ``effective_from <= trade_date``.

    ``market_rows`` must be strictly increasing by ``trade_date``; ``states``
    strictly increasing by ``effective_from``.  A single cursor advances through
    the states; each trade date keeps the most recent state seen so far.
    """
    ordered = dedup_states_by_effective_from(states)
    result: dict[str, dict[str, Any] | None] = {}
    cursor = 0
    current: dict[str, Any] | None = None
    for row in sorted(market_rows, key=lambda r: r["trade_date"]):
        trade_date = row["trade_date"]
        while cursor < len(ordered) and ordered[cursor]["effective_from"] <= trade_date:
            current = ordered[cursor]
            cursor += 1
        result[trade_date] = _selected_fields(current)
    return result


# ── Oracle B: DuckDB ASOF LEFT JOIN (in-memory only) ──────────────────────


def duckdb_asof_join(
    market_rows: list[dict[str, Any]],
    states: list[dict[str, Any]],
    *,
    group: str = "series",
) -> dict[str, dict[str, Any] | None]:
    """Backward join via DuckDB ASOF LEFT JOIN in an isolated in-memory DB.

    The states table is re-sorted inside the engine by the ASOF key.  The join
    never touches the default database.
    """
    import duckdb

    ordered = dedup_states_by_effective_from(states)
    market_sorted = sorted(market_rows, key=lambda r: r["trade_date"])
    con = duckdb.connect(database=":memory:")
    try:
        con.execute("CREATE TABLE market(trade_date DATE, grp VARCHAR)")
        con.executemany(
            "INSERT INTO market VALUES (?, ?)",
            [(r["trade_date"], group) for r in market_sorted],
        )
        con.execute(
            "CREATE TABLE states(grp VARCHAR, effective_from DATE, financial_state_id VARCHAR)"
        )
        con.executemany(
            "INSERT INTO states VALUES (?, ?, ?)",
            [(group, s["effective_from"], s["financial_state_id"]) for s in ordered],
        )
        rows = con.execute(
            """
            WITH states_sorted AS (
                SELECT * FROM states ORDER BY grp, effective_from
            )
            SELECT m.trade_date, s.financial_state_id, s.effective_from
            FROM market m
            ASOF LEFT JOIN states_sorted s
              ON m.grp = s.grp AND m.trade_date >= s.effective_from
            ORDER BY m.trade_date
            """
        ).fetchall()
        result: dict[str, dict[str, Any] | None] = {}
        by_id = {s["financial_state_id"]: s for s in ordered}
        for trade_date, fid, _eff in rows:
            date_str = str(trade_date)
            if fid is None:
                result[date_str] = None
            else:
                result[date_str] = _selected_fields(by_id[fid])
        return result
    finally:
        con.close()


# ── Comparison ────────────────────────────────────────────────────────────


def compare_oracles(
    a: dict[str, dict[str, Any] | None],
    b: dict[str, dict[str, Any] | None],
) -> dict[str, Any]:
    """Row-by-row comparison of the two oracles.

    Compares the selected ``financial_state_id``, ``effective_from``,
    ``value_decimal``, ``status`` and ``input_fact_ids`` for every trade date.
    """
    all_dates = sorted(set(a) | set(b))
    mismatches: list[dict[str, Any]] = []
    for trade_date in all_dates:
        left = a.get(trade_date)
        right = b.get(trade_date)
        if left is None or right is None:
            if left != right:
                mismatches.append(
                    {
                        "trade_date": trade_date,
                        "left": left,
                        "right": right,
                        "reason": "presence",
                    }
                )
            continue
        for field in (
            "financial_state_id",
            "effective_from",
            "value_decimal",
            "status",
            "input_fact_ids",
        ):
            if left.get(field) != right.get(field):
                mismatches.append(
                    {
                        "trade_date": trade_date,
                        "field": field,
                        "python": left.get(field),
                        "duckdb": right.get(field),
                    }
                )
    return {
        "row_count": len(all_dates),
        "mismatch_count": len(mismatches),
        "identical": not mismatches,
        "mismatches": mismatches[:20],
    }
