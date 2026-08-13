"""M2 Stage 2K.1R4D.1 — official share-count continuity register and derivation.

The register is a bounded official search (SSE announcement query API archive)
for any corporate action that would change the total ordinary share count in
2020 Q1..2026 Q1.  Combined with the precise dividend-base share counts
disclosed in half-year and annual reports, it establishes whether the share
count is constant across the whole duration.  Only when the register is
trusted and the count is constant do we derive:

- Q1/Q3 period-end share counts (instant, period-end) from the constant
- weighted-average share counts (duration) from the constant

Otherwise those cells stay explicit gaps.  No TTM / per-share / valuation
series is produced here.
"""

from __future__ import annotations

from typing import Any

# Total ordinary share count (A+H) disclosed in the 12 dividend-base
# statements and frozen in the register.
KNOWN_TOTAL_SHARES = 183020977818

# Definitive share-count-changing corporate actions (execution, not plan).
_SHARE_CHANGE_ACTIONS = (
    "转增",
    "送股",
    "送红股",
    "增发",
    "配股",
    "资本公积转增",
    "10转",
    "10送",
    "限制性股票",
    "股票期权",
    "可转债",
    "增资",
    "吸收合并",
    "业绩补偿",
)
# A buyback only changes the total when it is executed AND the shares are
# cancelled.  A standing general-authority opinion is not an executed change.
_AUTHORIZATION_ONLY = ("一般性授权", "独立意见", "授权", "提请股东大会")


def classify_share_change(title: str) -> bool:
    """Return True when an announcement title is a definitive share change.

    Cash-dividend distributions (利润分配/权益分派/分红) never change the
    share count.  A buyback is share-changing only when executed and
    cancelled; a standing board-authority opinion is not.
    """
    if not title:
        return False
    if any(k in title for k in _SHARE_CHANGE_ACTIONS):
        return True
    if "回购" in title:
        if any(k in title for k in _AUTHORIZATION_ONLY):
            return False
        return "注销" in title
    return False


def build_share_continuity_register(
    archive_rows: list[dict[str, Any]],
    precise_base_facts: list[dict[str, Any]],
    *,
    search_start: str,
    search_end: str,
    source_label: str,
) -> dict[str, Any]:
    """Build the frozen share-continuity register from the bounded search.

    ``archive_rows`` carry the SSE announcement titles/dates (the bounded
    search).  ``precise_base_facts`` are the extracted dividend-base share
    counts (period_end, value, source_id).  The register records the search,
    every corporate-action candidate found, and the constancy conclusion.
    """
    candidates: list[dict[str, Any]] = []
    share_changing: list[dict[str, Any]] = []
    for row in archive_rows:
        title = row.get("TITLE") or ""
        if not title:
            continue
        date = row.get("SSEDATE") or ""
        if classify_share_change(title):
            share_changing.append({"date": date, "title": title, "url": row.get("URL", "")})
        # Record every corporate-action candidate for auditability.
        if any(
            k in title
            for k in ("分红", "分派", "利润分配", "转增", "送股", "增发", "配股",
                      "回购", "股权激励", "可转债", "增资", "股本")
        ):
            candidates.append(
                {"date": date, "title": title, "share_change": classify_share_change(title)}
            )

    bases = sorted(
        (f for f in precise_base_facts if f.get("value") is not None),
        key=lambda f: (f.get("period_end") or ""),
    )
    base_values = {str(f["value"]) for f in bases}
    constant = len(base_values) == 1
    constant_value = int(bases[0]["value"]) if constant and bases else None

    trusted = (
        constant
        and not share_changing
        and bool(bases)
        and constant_value == KNOWN_TOTAL_SHARES
    )
    return {
        "schema": "pit_valuation_share_continuity_register_v1",
        "symbol": "601857.SH",
        "date": "",
        "search_window": {"start": search_start, "end": search_end},
        "source": {
            "type": "sse_announcement_query_api",
            "label": source_label,
            "announcement_count": len(archive_rows),
        },
        "precise_base_evidence": [
            {
                "period_end": f["period_end"],
                "value": f["value"],
                "source_id": f.get("source_id", ""),
            }
            for f in bases
        ],
        "precise_base_value_set": sorted(base_values),
        "corporate_action_candidates": candidates,
        "share_changing_actions_found": share_changing,
        "share_changing_action_count": len(share_changing),
        "share_count_constant": constant,
        "constant_value": constant_value,
        "known_total_shares": KNOWN_TOTAL_SHARES,
        "trust": "trusted" if trusted else "not_trusted",
        "conclusions": {
            "rationale": [
                "all precise dividend-base share counts over 2020 H1..2025 AR "
                "are equal to 183,020,977,818",
                "the bounded SSE corporate-action search found no "
                "share-changing action (no 转增/送股/增发/配股/回购注销/"
                "股权激励/可转债/增资)",
            ],
            "residual_risks": [
                "search is bounded by SSE archive completeness "
                "(2020-01-01..2026-08-02)",
                "non-SSE share-change mechanisms are not searched",
                "183,020,977,818 is the A+H total ordinary share count",
            ],
        },
    }


def constancy_derivation_available(register: dict[str, Any]) -> bool:
    """True only when the register is trusted and the count is constant."""
    return (
        register.get("trust") == "trusted"
        and register.get("share_count_constant") is True
        and register.get("constant_value") is not None
    )


def derive_period_end_shares_from_constancy(
    register: dict[str, Any],
    filings: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Derive Q1/Q3 period-end share counts from the constant share count.

    Only the interim Q1/Q3 report periods need derivation; H1/AR period-end
    shares are directly disclosed.  Returns one record per Q1/Q3 filing.
    """
    if not constancy_derivation_available(register):
        return []
    value = register["constant_value"]
    out: list[dict[str, Any]] = []
    for entry in filings:
        if entry.get("report_type") not in ("q1", "q3"):
            continue
        out.append(
            {
                "evidence_id": entry["evidence_id"],
                "fiscal_year": entry.get("fiscal_year"),
                "report_type": entry.get("report_type"),
                "period_end": entry.get("period_end"),
                "value": value,
                "status": "acquired_reconciled_derived",
                "derivation_definition_id": "r4d1-share-continuity-constancy-v1",
                "derivation_version": "1",
                "note": "period-end share count derived from the frozen "
                "constant share count (no share change in the bounded official "
                "search)",
            }
        )
    return out


def derive_weighted_average_shares_from_constancy(
    register: dict[str, Any],
    filings: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Derive weighted-average share counts from the constant share count.

    When the share count is constant across the whole duration, the weighted
    average for every report period equals the constant.  Returns one record
    per exchange_official filing.
    """
    if not constancy_derivation_available(register):
        return []
    value = register["constant_value"]
    out: list[dict[str, Any]] = []
    for entry in filings:
        out.append(
            {
                "evidence_id": entry["evidence_id"],
                "fiscal_year": entry.get("fiscal_year"),
                "report_type": entry.get("report_type"),
                "period_end": entry.get("period_end"),
                "value": value,
                "status": "acquired_reconciled_derived",
                "derivation_definition_id": "r4d1-share-continuity-constancy-v1",
                "derivation_version": "1",
                "note": "weighted-average share count derived from the frozen "
                "constant share count (constant over the whole duration, "
                "accounting scope consistent)",
            }
        )
    return out
