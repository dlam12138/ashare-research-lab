"""M2 Stage 1 — Point-in-Time query engine.

All downstream queries must pass through the as_of_date gate.
Direct reads of the unfiltered fact set are forbidden outside
of explicitly audited paths.
"""

from __future__ import annotations

import logging
from typing import Any

import pandas as pd

from ashare_research.exceptions import PointInTimeError
from ashare_research.facts.repository import FactRepository

logger = logging.getLogger(__name__)


def _validate_date_format(date_str: str, param_name: str) -> None:
    """Raise PointInTimeError if *date_str* is not a valid calendar date."""
    if not date_str:
        raise PointInTimeError(
            f"{param_name} must be a non-empty YYYY-MM-DD date string, "
            f"got: {date_str!r}"
        )
    try:
        from datetime import date
        date.fromisoformat(date_str)
    except (ValueError, TypeError) as e:
        raise PointInTimeError(
            f"{param_name} must be a valid YYYY-MM-DD date, "
            f"got: {date_str!r} — {e}"
        )


class AsOfQuery:
    """PIT query engine — every analytical path passes through this gate."""

    schema_version: str = "1.0"

    def __init__(self, repository: FactRepository) -> None:
        self.repository = repository

    # ── Core PIT query ──────────────────────────────────────────

    def query(
        self,
        symbol: str,
        concept_ids: list[str] | None = None,
        as_of_date: str = "",
        start_year: int | None = None,
        end_year: int | None = None,
        include_unverified: bool = False,
    ) -> pd.DataFrame:
        """Return facts available on or before *as_of_date*.

        Strict PIT enforcement:
          - ``available_at`` must be non-NULL, non-empty, and <= *as_of_date*.
          - Only ``verified`` / ``reconciled`` facts that are
            ``eligible_for_metrics`` are returned by default.

        Args:
            symbol: Stock code (e.g. ``000001.SZ``).
            concept_ids: Optional concept whitelist; ``None`` means all.
            as_of_date: PIT cut-off date in **YYYY-MM-DD** format
                (mandatory — pass the day you want the view from).
            start_year: Earliest fiscal year (inclusive).
            end_year: Latest fiscal year (inclusive).
            include_unverified: If ``True``, skip the verification and
                eligibility filters. **Only use in audit / debugging
                contexts.**

        Returns:
            DataFrame ordered by ``period_end``, ``concept_id``,
            ``fact_version DESC``.

        Raises:
            PointInTimeError: *as_of_date* is empty or not YYYY-MM-DD.
        """
        _validate_date_format(as_of_date, "as_of_date")

        return self.repository.query_facts(
            symbol=symbol,
            concept_ids=concept_ids,
            start_year=start_year,
            end_year=end_year,
            as_of_date=as_of_date,
            include_unverified=include_unverified,
        )

    # ── Latest-available snapshot ───────────────────────────────

    def get_latest_available(
        self,
        symbol: str,
        as_of_date: str,
        concept_ids: list[str] | None = None,
        consolidation_scope: str = "consolidated",
    ) -> pd.DataFrame:
        """Return the single latest version of each fact key as of *as_of_date*.

        A fact key is ``(symbol, concept_id, period_end,
        consolidation_scope)``.  Within each key the row with the highest
        ``available_at`` (then highest ``fact_version``) wins.

        Strict PIT:
          - ``available_at`` must be non-NULL, non-empty, and <= *as_of_date*.
          - Only ``verified`` / ``reconciled`` + ``eligible_for_metrics``
            facts are considered.

        Args:
            symbol: Stock code.
            as_of_date: PIT cut-off date in **YYYY-MM-DD** format
                (mandatory).
            concept_ids: Optional concept whitelist.
            consolidation_scope: ``consolidated`` (default) or
                ``parent_company``.

        Returns:
            DataFrame with exactly one row per fact key
            (``rn == 1``), ordered by ``period_end``, ``concept_id``.

        Raises:
            PointInTimeError: *as_of_date* is empty or not YYYY-MM-DD.
        """
        _validate_date_format(as_of_date, "as_of_date")

        return self.repository.get_latest_available(
            symbol=symbol,
            as_of_date=as_of_date,
            concept_ids=concept_ids,
            consolidation_scope=consolidation_scope,
        )

    # ── Audit / debugging escape hatch ──────────────────────────

    def get_all_versions_for_audit(
        self,
        symbol: str,
        concept_ids: list[str] | None = None,
    ) -> pd.DataFrame:
        """**Audit-only.** Return every fact version unconditionally.

        This call skips:
          - the ``available_at`` PIT gate,
          - the ``verification_status`` filter, and
          - the ``eligible_for_metrics`` filter.

        It must **never** be used in production analysis or metric
        calculation paths.  Its sole purpose is manual review of the
        raw fact table (e.g. investigating a reconciliation discrepancy
        or auditing a data pipeline run).
        """
        return self.repository.get_all_versions_for_audit(
            symbol=symbol,
            concept_ids=concept_ids,
        )

    # ── Version comparison (restatement detection) ──────────────

    def compare_versions(
        self,
        symbol: str,
        concept_ids: list[str],
        period_end: str,
        date1: str,
        date2: str,
        consolidation_scope: str = "consolidated",
    ) -> dict[str, Any]:
        """Compare fact values at two PIT dates — detect restatements.

        Fact keys are ``(concept_id, period_end, consolidation_scope)``.
        The method matches each key across both snapshots and reports
        the value at each date plus whether it changed.

        Args:
            symbol: Stock code.
            concept_ids: Concepts to compare.
            period_end: Report period end date (YYYY-MM-DD).  Pass
                ``""`` to compare across all periods.
            date1: First PIT date (YYYY-MM-DD).
            date2: Second PIT date (YYYY-MM-DD).
            consolidation_scope: ``consolidated`` or ``parent_company``.

        Returns:
            Dict keyed by ``(concept_id, period_end, consolidation_scope)``,
            each value::

                {
                    "concept_id": str,
                    "period_end": str,
                    "consolidation_scope": str,
                    "value_at_<date1>": float | None,
                    "value_at_<date2>": float | None,
                    "changed": bool | None,
                }

        Raises:
            PointInTimeError: any date is empty or not YYYY-MM-DD.
        """
        _validate_date_format(date1, "date1")
        _validate_date_format(date2, "date2")
        if period_end:
            _validate_date_format(period_end, "period_end")

        # Snapshot at each PIT date — use latest-available so we get
        # one row per fact key.
        snap1 = self.get_latest_available(
            symbol=symbol,
            as_of_date=date1,
            concept_ids=concept_ids,
            consolidation_scope=consolidation_scope,
        )
        snap2 = self.get_latest_available(
            symbol=symbol,
            as_of_date=date2,
            concept_ids=concept_ids,
            consolidation_scope=consolidation_scope,
        )

        # Index both snapshots by the fact key.
        _key_cols = ["concept_id", "period_end"]
        if "consolidation_scope" in snap1.columns:
            _key_cols.append("consolidation_scope")

        def _key_from_row(row: pd.Series) -> tuple:
            return tuple(row[c] for c in _key_cols)

        if not snap1.empty:
            snap1["_key"] = snap1.apply(_key_from_row, axis=1)
        else:
            snap1["_key"] = pd.Series(dtype="object")
        if not snap2.empty:
            snap2["_key"] = snap2.apply(_key_from_row, axis=1)
        else:
            snap2["_key"] = pd.Series(dtype="object")

        idx1: dict[tuple, float | None] = {}
        for _, row in snap1.iterrows():
            k = row["_key"]
            # Keep the first occurrence per key (should be unique after
            # get_latest_available, but be defensive).
            if k not in idx1:
                idx1[k] = row.get("value")

        idx2: dict[tuple, float | None] = {}
        for _, row in snap2.iterrows():
            k = row["_key"]
            if k not in idx2:
                idx2[k] = row.get("value")

        all_keys = set(idx1.keys()) | set(idx2.keys())

        comparison: dict[str, Any] = {}
        for key in sorted(all_keys):
            val1 = idx1.get(key)
            val2 = idx2.get(key)
            changed: bool | None = None
            if val1 is not None and val2 is not None:
                changed = val1 != val2
            kdict = dict(zip(_key_cols, key, strict=True))
            entry: dict[str, Any] = {**kdict}
            entry[f"value_at_{date1}"] = val1
            entry[f"value_at_{date2}"] = val2
            entry["changed"] = changed
            label = "|".join(str(v) for v in key)
            comparison[label] = entry

        return comparison
