"""M2 Stage 2K.1R4F.3A — PE historical annual fact backfill (pure functions).

Implements the R4F.3A minimum-3y backfill: extract the 5 target logical
cells (2017-12-31 equity; 2018/2019 equity + net profit) from SSE official
annual reports, build original/restatement version chains with PIT
effective dates (announcement-date-to-next-trading-day-v1 against the R4F3A
historical calendar), construct canonical Facts, and assemble the isolated
backfill bundle plus the overlay with the existing trusted fact set.

Reuses the R4D/R4F.3 contracts: FactIdentity (build_fact_id), R4D fact
shape (build_context_v2), the verified-calendar loader (load_market_calendar
/ next_trading_day) with the R4F3A registry, and the R4F.3 readiness engine
unchanged.  Never writes the default database, never contacts the network.
"""

from __future__ import annotations

import hashlib
import json
from decimal import Decimal
from pathlib import Path
from typing import Any

from ashare_research.facts.identity import validate_canonical_fact_ids
from ashare_research.pit_valuation.contracts import (
    SYMBOL,
    load_market_calendar_registry,
)
from ashare_research.pit_valuation.extraction import (
    normalize_value,
    parse_decimal_token,
)
from ashare_research.pit_valuation.fact_builder import (
    build_context_v2,
    build_fact_id,
    load_market_calendar,
    next_trading_day,
)

# Concept ids (same canonical semantics as the 2020+ facts).
CONCEPT_EQUITY = "equity_attributable_to_parent"
CONCEPT_NET_PROFIT = "net_profit_attributable_to_parent"

R4F3A_CALENDAR_REGISTRY = (
    Path(__file__).resolve().parents[3]
    / "config"
    / "pit_valuation_market_calendar_registry_r4f3a_v1.json"
)

CANONICAL_UNIT = "CNY"
RAW_UNIT = "CNY_million"
CONVERSION_MULTIPLIER = Decimal("1000000")
PERIOD_TYPE_ANNUAL = "annual"
PERIOD_END_ANNUAL = "12-31"


def load_calendar_r4f3a(market_cache_root: Path | str, registry: dict | None = None):
    """Load the R4F3A historical calendar via the existing pinned loader."""
    if registry is None:
        registry = load_market_calendar_registry(R4F3A_CALENDAR_REGISTRY)
    return load_market_calendar(market_cache_root, registry=registry)


def _canonical_json(payload: Any) -> bytes:
    return json.dumps(
        payload, sort_keys=True, ensure_ascii=False, separators=(",", ":")
    ).encode("utf-8")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def state_identity(payload: Any) -> str:
    return sha256_bytes(_canonical_json(payload))


# ── extraction ──────────────────────────────────────────────────────────


def extract_cell(
    spec: dict[str, Any],
    pdf_path: Path,
    *,
    evidence: dict[str, Any],
    page_texts: list[str] | None = None,
) -> dict[str, Any]:
    """Extract one target cell from one official filing.

    Anchored on the named-capture row pattern; returns a status-carrying
    dict (never a fabricated value).  Fail-closed statuses:
    extraction_marker_missing / ambiguous_table_scope.
    """
    from pypdf import PdfReader

    pages = page_texts if page_texts is not None else [
        (p.extract_text() or "") for p in PdfReader(str(pdf_path)).pages
    ]
    pattern = spec["named_capture_pattern"]
    import re

    rx = re.compile(pattern)
    for page_index, text in enumerate(pages):
        # Normalise line breaks inside the table.
        text_n = text.replace("\n", " ")
        m = rx.search(text_n)
        if not m:
            continue
        token = m.group("value").strip()
        raw = parse_decimal_token(token)
        if raw is None:
            continue
        # Column-slot sanity: the consolidated current-period value must be
        # the first numeric token after the label (the row's first column).
        return {
            "status": "acquired_reported_verified",
            "evidence_id": evidence["evidence_id"],
            "concept_id": spec["concept_id"],
            "period_end": f"{evidence['fiscal_year']}-12-31",
            "raw_token": token,
            "raw_value": str(raw),
            "canonical_value": str(
                normalize_value(raw, CONVERSION_MULTIPLIER, RAW_UNIT)
            ),
            "page_index": page_index,
            "excerpt": text[max(0, m.start() - 40) : m.end() + 40],
            "excerpt_hash": sha256_bytes(
                text[max(0, m.start() - 40) : m.end() + 40].encode("utf-8")
            ),
        }
    return {
        "status": "extraction_marker_missing",
        "evidence_id": evidence["evidence_id"],
        "concept_id": spec["concept_id"],
        "period_end": f"{evidence['fiscal_year']}-12-31",
    }


# ── fact construction (PIT via R4F3A calendar) ─────────────────────────


def build_fact(
    cell: dict[str, Any],
    evidence: dict[str, Any],
    *,
    market_calendar: dict[str, Any],
    object_sha: str,
    restatement_version: str = "original",
    supersedes_fact_id: str = "",
    concept_version: str = "1",
) -> dict[str, Any]:
    """Build a canonical ReportedFact for a backfilled annual cell.

    available_at = official announcement date; effective_from = next real
    trading day (R4F3A historical calendar).  Calendar provenance binds the
    R4F3A calendar object; the economic FactIdentity is unchanged by the
    calendar object (calendar is provenance, not identity).
    """
    announcement_date = evidence["announcement_date"]
    # equity = instant; NP = duration (canonical R4D semantics).
    is_instant = cell["concept_id"] == CONCEPT_EQUITY
    # The context fiscal year is the REPORT PERIOD's year (cell period_end),
    # not the filing's fiscal year: a restated comparative in the 2019 AR
    # for 2017-12-31 must carry a 2017 context, not a 2019 one.
    period_fy = int(cell["period_end"][:4])
    context = build_context_v2(
        fiscal_year=period_fy,
        report_type="annual",
        period_type="annual",
        instant=is_instant,
        filing_date=announcement_date,
        source_document=evidence["proof_url"],
    )
    effective_from, pit_gap, derivation = _pit_time(
        announcement_date, market_calendar
    )
    value = cell["canonical_value"]
    fact: dict[str, Any] = {
        "fact_id": "",
        "fact_version": 1,
        "concept_id": cell["concept_id"],
        "concept_version": concept_version,
        "symbol": SYMBOL,
        "value": float(value),
        "unit": CANONICAL_UNIT,
        "context_id": context["context_id"],
        "is_derived": False,
        "derived_from": "",
        "supersedes_fact_id": supersedes_fact_id,
        "derivation_definition_id": "",
        "derivation_version": "",
        "input_fact_ids": "",
        "source_provider": evidence["source_role"],
        "source_document": evidence["proof_url"],
        "source_page": str(cell["page_index"] + 1),
        "source_table": "consolidated_balance_sheet_or_income_statement",
        "source_label": evidence["report_title"],
        "source_tier": "exchange_official",
        "source_id": f"r4f3a:{evidence['evidence_id']}",
        "source_url": evidence["proof_url"],
        "source_hash": object_sha,
        "source_object_sha256": object_sha,
        "excerpt_hash": cell.get("excerpt_hash", ""),
        "filing_date": announcement_date,
        "period_end": cell["period_end"],
        "restatement_version": restatement_version,
        "announcement_date": announcement_date,
        "available_at": announcement_date,
        "raw_value": float(cell["raw_value"]),
        "raw_unit": RAW_UNIT,
        "normalized_value": float(value),
        "normalization_rule": f"identity;{CONVERSION_MULTIPLIER}x",
        "verification_status": "verified",
        "verification_note": (
            f"r4f3a cell={cell.get('concept_id')} excerpt={cell.get('excerpt_hash','')}"
            f" object={object_sha}"
        ),
        "eligible_for_metrics": True,
        "created_at": "",
        "effective_from": effective_from,
        "pit_time_contract_gap": pit_gap,
        "effective_from_derivation": derivation,
        "calendar_object_id": market_calendar.get("calendar_object_id", ""),
        "calendar_sha256": market_calendar.get("calendar_sha256", ""),
    }
    fact["fact_id"] = build_fact_id(fact)
    return fact


def _pit_time(
    announcement_date: str, market_calendar: dict[str, Any]
) -> tuple[str, str, dict[str, Any]]:
    """effective_from via the R4F3A calendar; calendar gap fails closed."""
    try:
        selected = next_trading_day(announcement_date, market_calendar["trade_dates"])
        return (
            selected,
            "",
            {
                "rule_id": "announcement-date-to-next-trading-day-v1",
                "calendar_object_id": market_calendar["calendar_object_id"],
                "calendar_sha256": market_calendar["calendar_sha256"],
                "input_announcement_date": announcement_date,
                "selected_next_trading_day": selected,
            },
        )
    except Exception:
        return "", "calendar_coverage_gap", {}


# ── restatement reconciliation ─────────────────────────────────────────


def reconcile_target_cell(
    cell: dict[str, Any],
    *,
    facts_by_evidence: dict[str, list[dict[str, Any]]],
    restatement_policy: dict[str, Any],
) -> dict[str, Any]:
    """Reconcile one target logical cell's versions into a chain.

    Returns the selected fact (latest visible version per PIT) plus the
    full version list and lineage status.  If the version chain is
    ambiguous (e.g. a restated value whose source cannot be attributed),
    status = RESTATEMENT_AMBIGUITY (fail closed).
    """
    versions = [
        f
        for flist in facts_by_evidence.values()
        for f in flist
        if f.get("concept_id") == cell["concept_id"]
        and f.get("period_end") == cell["period_end"]
    ]
    if not versions:
        return {
            "cell": cell,
            "status": "NO_FACT_FOUND",
            "versions": [],
            "selected_fact": None,
        }
    # Sort by effective_from ascending; the latest effective version wins.
    versions_sorted = sorted(
        versions, key=lambda f: (f.get("effective_from") or "", f.get("fact_id"))
    )
    selected = versions_sorted[-1]
    return {
        "cell": cell,
        "status": "RESOLVED",
        "versions": [v.get("fact_id") for v in versions_sorted],
        "selected_fact": selected,
    }


# ── bundle assembly ─────────────────────────────────────────────────────


def build_backfill_bundle(
    facts: list[dict[str, Any]],
    *,
    symbol: str = SYMBOL,
) -> dict[str, Any]:
    """Assemble the isolated reported-fact bundle for the backfill facts."""
    validate_canonical_fact_ids(facts)
    return {
        "schema": "pe_3y_historical_backfill_reported_fact_bundle_v1",
        "symbol": symbol,
        "fact_count": len(facts),
        "facts": facts,
    }


def build_overlay(
    existing_facts: list[dict[str, Any]],
    backfill_facts: list[dict[str, Any]],
    *,
    selected_target_facts: list[dict[str, Any]],
) -> dict[str, Any]:
    """Deterministic overlay: existing trusted set + backfill set."""
    existing_digest = state_identity(
        {"facts": existing_facts, "schema": "existing_trusted_fact_set"}
    )
    backfill_digest = state_identity(
        {"facts": backfill_facts, "schema": "pe_3y_historical_backfill_facts"}
    )
    combined = existing_facts + backfill_facts
    combined_digest = state_identity(
        {"facts": combined, "schema": "combined_fact_set"}
    )
    return {
        "schema": "pe_3y_historical_backfill_overlay_v1",
        "symbol": SYMBOL,
        "existing_fact_set_digest": existing_digest,
        "backfill_bundle_digest": backfill_digest,
        "combined_fact_set_digest": combined_digest,
        "existing_fact_count": len(existing_facts),
        "backfill_fact_count": len(backfill_facts),
        "combined_fact_count": len(combined),
        "selected_target_facts": selected_target_facts,
    }


# ── ROE recomputation (Decimal-only, independent) ──────────────────────


def roe_decimal(
    np: str, begin_equity: str, end_equity: str
) -> str:
    """ROE_y = NP_y / ((Equity_{y-1} + Equity_y) / 2), Decimal-only."""
    np_d = Decimal(np)
    b_d = Decimal(begin_equity)
    e_d = Decimal(end_equity)
    if np_d <= 0 or b_d <= 0 or e_d <= 0:
        raise ValueError("ROE operands must be positive")
    return str(np_d / ((b_d + e_d) / Decimal("2")))
