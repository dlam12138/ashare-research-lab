"""M2 Stage 2K.1R4D — canonical reported-fact construction.

Builds FactContext, ReportedFact and canonical FactIdentity for every
extracted cell; computes ``available_at`` (frozen conservative date rule) and
``effective_from`` from the verified market calendar; and writes the isolated
reported/reconciled fact bundles.  It never writes the default database and
never constructs a TTM / MRQ / valuation series.
"""

from __future__ import annotations

import hashlib
import json
from datetime import date
from pathlib import Path
from typing import Any

from ashare_research.facts.identity import build_fact_id, validate_canonical_fact_ids
from ashare_research.pit_valuation.contracts import (
    ACCOUNTING_SCOPE,
    ACCOUNTING_STANDARD,
    EFFECTIVE_RULE_ID,
    PERIOD_END_BY_REPORT,
    PERIOD_TYPE_BY_REPORT,
    SYMBOL,
    load_role_registry,
)
from ashare_research.pit_valuation.extraction import ExtractedCell

ROOT = Path(__file__).resolve().parents[3]

# Frozen conservative PIT rule: a date-only announcement becomes available at
# the announcement date and is effective from the next trading day.
AVAILABLE_AT_RULE_ID = "announcement-date-available-at-v1"


def canonical_fact_value(value: Any) -> float | None:
    """Convert a Decimal cell value to the canonical float Fact value."""
    if value is None:
        return None
    return float(str(value))


def build_context(
    *,
    fiscal_year: int,
    report_type: str,
    period_type: str,
    instant: bool,
    filing_date: str,
    source_document: str,
) -> dict[str, Any]:
    """Construct a FactContext-compatible dict for the R4D period mapping."""
    period_start = f"{fiscal_year}-01-01"
    actual_period_end = f"{fiscal_year}-{PERIOD_END_BY_REPORT[report_type]}"
    return {
        "context_id": f"{SYMBOL}|{fiscal_year}|{period_type}|{ACCOUNTING_SCOPE}",
        "symbol": SYMBOL,
        "fiscal_year": fiscal_year,
        "period_type": period_type,
        "period_start": period_start,
        "period_end": actual_period_end,
        "instant_or_duration": "instant" if instant else "duration",
        "consolidation_scope": ACCOUNTING_SCOPE,
        "accounting_standard": ACCOUNTING_STANDARD,
        "restatement_version": "original",
        "source_document": source_document,
        "filing_date": filing_date,
    }


def build_context_v2(
    *,
    fiscal_year: int,
    report_type: str,
    period_type: str,
    instant: bool,
    filing_date: str,
    source_document: str,
) -> dict[str, Any]:
    """Construct a FactContext-compatible dict with period-aware instant context.

    Context v2 fixes the instant-fact defect where every quarter of a year
    shared the same ``context_id`` (``SYMBOL|FY|instant|SCOPE``): the equity at
    2023-03-31, 2023-06-30, 2023-09-30 and 2023-12-31 all collapsed onto one
    context.  For an instant fact the as-of point is the report period end, so
    the period-end date is encoded into the ``context_id``, restoring the
    ``(concept_id, symbol, context_id)`` uniqueness contract.  A duration fact
    already carries its period type.  The context stays stable across
    restatements (``restatement_version`` is never encoded here).
    """
    actual_period_end = f"{fiscal_year}-{PERIOD_END_BY_REPORT[report_type]}"
    if instant:
        context_id = (
            f"{SYMBOL}|{fiscal_year}|instant|{ACCOUNTING_SCOPE}|{actual_period_end}"
        )
    else:
        context_id = f"{SYMBOL}|{fiscal_year}|{period_type}|{ACCOUNTING_SCOPE}"
    return {
        "context_id": context_id,
        "symbol": SYMBOL,
        "fiscal_year": fiscal_year,
        "period_type": period_type,
        "period_start": f"{fiscal_year}-01-01",
        "period_end": actual_period_end,
        "instant_or_duration": "instant" if instant else "duration",
        "consolidation_scope": ACCOUNTING_SCOPE,
        "accounting_standard": ACCOUNTING_STANDARD,
        "restatement_version": "original",
        "source_document": source_document,
        "filing_date": filing_date,
    }


def load_market_calendar(market_cache_root: Path | str) -> dict[str, Any]:
    """Load the verified trading-day calendar from the market cache.

    Only trade dates are used: the market cache is never used for financial
    values.  Returns the sorted trade-date list plus calendar provenance.
    """
    import pandas as pd

    root = Path(market_cache_root).resolve()
    parquet_files = sorted(root.rglob("*.parquet"))
    if not parquet_files:
        raise FileNotFoundError("no verified market parquet found in market cache root")
    matches = [p for p in parquet_files if p.name.startswith("defd0b9507c0d87c")]
    path = matches[0] if matches else parquet_files[0]
    sha = hashlib.sha256(path.read_bytes()).hexdigest()
    df = pd.read_parquet(path)
    trade_dates = sorted(
        str(d) for d in df.loc[df["is_trading"], "trade_date"].astype(str).tolist()
    )
    return {
        "calendar_object_id": path.name,
        "calendar_sha256": sha,
        "trade_dates": trade_dates,
    }


def next_trading_day(announcement_date: str, trade_dates: list[str]) -> str:
    """Next trading day strictly after the announcement date."""
    d = date.fromisoformat(announcement_date)
    for candidate in trade_dates:
        if date.fromisoformat(candidate) > d:
            return candidate
    raise ValueError(f"no trading day after {announcement_date} in the verified calendar")


def effective_from_derivation(announcement_date: str, calendar: dict[str, Any]) -> dict[str, Any]:
    """Record the effective-from derivation contract."""
    selected = next_trading_day(announcement_date, calendar["trade_dates"])
    return {
        "rule_id": EFFECTIVE_RULE_ID,
        "calendar_object_id": calendar["calendar_object_id"],
        "calendar_sha256": calendar["calendar_sha256"],
        "input_announcement_date": announcement_date,
        "selected_next_trading_day": selected,
    }


def build_reported_fact(
    cell: ExtractedCell,
    evidence: dict[str, Any],
    role: dict[str, Any],
    *,
    market_calendar: dict[str, Any],
    object_sha: str = "",
) -> dict[str, Any]:
    """Build a canonical ReportedFact from an extracted cell."""
    announcement_date = evidence["announcement_date"]
    context = build_context_v2(
        fiscal_year=cell.fiscal_year,
        report_type=cell.report_type,
        period_type=PERIOD_TYPE_BY_REPORT[cell.report_type]
        if role["instant_or_duration"] == "duration"
        else "instant",
        instant=role["instant_or_duration"] == "instant",
        filing_date=announcement_date,
        source_document=evidence["proof_url"],
    )
    derivation = effective_from_derivation(announcement_date, market_calendar)
    fact: dict[str, Any] = {
        "fact_id": "",
        "fact_version": 1,
        "concept_id": role["concept_id"],
        "concept_version": role["concept_version"],
        "symbol": SYMBOL,
        "value": canonical_fact_value(cell.normalized_value),
        "unit": role["canonical_unit"],
        "context_id": context["context_id"],
        "is_derived": False,
        "derived_from": "",
        "supersedes_fact_id": "",
        "derivation_definition_id": "",
        "derivation_version": "",
        "input_fact_ids": "",
        "source_provider": evidence["source_role"],
        "source_document": evidence["proof_url"],
        "source_page": str(cell.page_index + 1),
        "source_table": "main_accounting_data_cas",
        "source_label": evidence["report_title"],
        "source_tier": "exchange_official"
        if evidence["source_role"] == "exchange_official"
        else "company_official",
        "source_id": f"r4d:{evidence['evidence_id']}",
        "source_url": evidence["proof_url"],
        # source_hash is the official PDF content-object digest (verified in
        # the external cache); excerpt_hash is the captured-fragment digest.
        "source_hash": object_sha or cell.excerpt_hash,
        "source_object_sha256": object_sha,
        "excerpt_hash": cell.excerpt_hash,
        "filing_date": announcement_date,
        "period_end": context["period_end"],
        "restatement_version": "original",
        "announcement_date": announcement_date,
        "available_at": announcement_date,
        "raw_value": canonical_fact_value(cell.raw_value),
        "raw_unit": cell.unit,
        "normalized_value": canonical_fact_value(cell.normalized_value),
        "normalization_rule": f"{cell.sign_rule};{cell.conversion_multiplier}x",
        "verification_status": "verified",
        "verification_note": (
            f"cell={cell.extraction_spec_id} excerpt={cell.excerpt_hash}"
            f" object={object_sha}"
        ),
        "eligible_for_metrics": True,
        "created_at": "",
        "effective_from": derivation["selected_next_trading_day"],
    }
    fact["fact_id"] = build_fact_id(fact)
    return fact


def build_share_capital_fact(
    cell: ExtractedCell,
    evidence: dict[str, Any],
    role: dict[str, Any],
    *,
    market_calendar: dict[str, Any],
    object_sha: str = "",
) -> dict[str, Any]:
    """Build a canonical ReportedFact for the precise period-end share count."""
    announcement_date = evidence["announcement_date"]
    context = build_context_v2(
        fiscal_year=cell.fiscal_year,
        report_type=cell.report_type,
        period_type="instant",
        instant=True,
        filing_date=announcement_date,
        source_document=evidence["proof_url"],
    )
    derivation = effective_from_derivation(announcement_date, market_calendar)
    fact: dict[str, Any] = {
        "fact_id": "",
        "fact_version": 1,
        "concept_id": role["concept_id"],
        "concept_version": role["concept_version"],
        "symbol": SYMBOL,
        "value": canonical_fact_value(cell.normalized_value),
        "unit": role["canonical_unit"],
        "context_id": context["context_id"],
        "is_derived": False,
        "derived_from": "",
        "supersedes_fact_id": "",
        "derivation_definition_id": "",
        "derivation_version": "",
        "input_fact_ids": "",
        "source_provider": evidence["source_role"],
        "source_document": evidence["proof_url"],
        "source_page": str(cell.page_index + 1),
        "source_table": "dividend_share_capital_statement",
        "source_label": evidence["report_title"],
        "source_tier": "exchange_official"
        if evidence["source_role"] == "exchange_official"
        else "company_official",
        "source_id": f"r4d:{evidence['evidence_id']}",
        "source_url": evidence["proof_url"],
        "source_hash": object_sha or cell.excerpt_hash,
        "source_object_sha256": object_sha,
        "excerpt_hash": cell.excerpt_hash,
        "filing_date": announcement_date,
        "period_end": context["period_end"],
        "restatement_version": "original",
        "announcement_date": announcement_date,
        "available_at": announcement_date,
        "raw_value": canonical_fact_value(cell.raw_value),
        "raw_unit": cell.unit,
        "normalized_value": canonical_fact_value(cell.normalized_value),
        "normalization_rule": "identity",
        "verification_status": "verified",
        "verification_note": (
            f"cell={cell.extraction_spec_id} excerpt={cell.excerpt_hash}"
            f" object={object_sha}"
        ),
        "eligible_for_metrics": True,
        "created_at": "",
        "effective_from": derivation["selected_next_trading_day"],
    }
    fact["fact_id"] = build_fact_id(fact)
    return fact


def write_isolated_bundles(
    output_root: Path,
    *,
    reported: list[dict[str, Any]],
    reconciled: list[dict[str, Any]],
    evidence: dict[str, Any],
) -> dict[str, Any]:
    """Write the isolated reported/reconciled fact bundles (never the default DB).

    Validates canonical fact IDs before writing.  Returns output paths.
    """
    validate_canonical_fact_ids(reported)
    validate_canonical_fact_ids(reconciled)
    output_root.mkdir(parents=True, exist_ok=True)
    reported_path = output_root / "petrochina_pit_denominator_reported_fact_bundle_v1.json"
    reconciled_path = output_root / "petrochina_pit_denominator_reconciled_fact_bundle_v1.json"

    reported_payload = {
        "schema": "pit_denominator_reported_fact_bundle_v1",
        "symbol": SYMBOL,
        "generated_at": "",
        "fact_count": len(reported),
        "facts": reported,
    }
    reconciled_payload = {
        "schema": "pit_denominator_reconciled_fact_bundle_v1",
        "symbol": SYMBOL,
        "generated_at": "",
        "fact_count": len(reconciled),
        "facts": reconciled,
    }
    reported_path.write_text(
        json.dumps(reported_payload, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
    )
    reconciled_path.write_text(
        json.dumps(reconciled_payload, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
    )
    return {
        "reported_bundle": str(reported_path),
        "reconciled_bundle": str(reconciled_path),
        "reported_count": len(reported),
        "reconciled_count": len(reconciled),
    }


def load_role(role_id: str) -> dict[str, Any]:
    registry = load_role_registry()
    for role in registry["roles"]:
        if role["role_id"] == role_id:
            return role
    raise KeyError(f"unknown role {role_id}")


def migrate_fact_to_context_v2(old_fact: dict[str, Any]) -> tuple[str, str]:
    """Return the (context_id, fact_id) a fact would have under Context v2.

    Only instant facts change: their old context ``SYMBOL|FY|instant|SCOPE``
    gains the period-end date.  Duration facts keep their context and therefore
    their fact_id.  This drives the old->new fact-id migration report.
    """
    old_ctx = old_fact.get("context_id", "")
    if old_ctx.endswith("|instant|consolidated"):
        period_end = old_fact.get("period_end", "")
        new_ctx = f"{old_ctx}|{period_end}"
    else:
        new_ctx = old_ctx
    new = dict(old_fact)
    new["context_id"] = new_ctx
    return new_ctx, build_fact_id(new)


def build_fact_id_migration_report(
    old_facts: list[dict[str, Any]],
) -> dict[str, Any]:
    """Build the old->new fact-id migration report driven by Context v2.

    Compares the prior (R4D v1) reported bundle against the Context v2
    identity.  Instant facts that previously shared ``SYMBOL|FY|instant|SCOPE``
    now carry a period-end-qualified context, so their fact_id changes; every
    changed fact is listed with its old/new context_id and fact_id.
    """
    entries = []
    for f in sorted(
        old_facts,
        key=lambda x: (x.get("concept_id", ""), x.get("source_id", ""), x.get("context_id", "")),
    ):
        new_ctx, new_fid = migrate_fact_to_context_v2(f)
        entries.append(
            {
                "concept_id": f.get("concept_id", ""),
                "source_id": f.get("source_id", ""),
                "old_context_id": f.get("context_id", ""),
                "new_context_id": new_ctx,
                "old_fact_id": f.get("fact_id", ""),
                "new_fact_id": new_fid,
                "changed": (f.get("fact_id", "") != new_fid),
            }
        )
    changed = [e for e in entries if e["changed"]]
    return {
        "schema": "pit_denominator_fact_id_migration_v1",
        "rule": (
            "Context v2: instant facts gain the report period-end in the "
            "context_id; duration facts are unchanged"
        ),
        "entries": entries,
        "entry_count": len(entries),
        "changed_count": len(changed),
    }
