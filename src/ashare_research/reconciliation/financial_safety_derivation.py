"""Stage 2E-B.1 evidence-backed current-portion derivation.

The statement line ``一年内到期的非流动负债`` is an aggregate disclosure,
not an automatically interest-bearing amount.  This module is deliberately
small: it accepts exactly three reconciled direct component facts and emits
one canonical derived Fact.  It never subtracts the aggregate, estimates a
component, or creates an average/other synthetic balance.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from ashare_research.facts.financial_safety_concepts import (
    CURRENT_PORTION_COMPONENT_CONCEPTS,
)
from ashare_research.facts.identity import build_fact_id

DERIVATION_DEFINITION_ID = "DERIVE_INTEREST_BEARING_CURRENT_PORTION_001"
DERIVATION_VERSION = "1"
DERIVATION_SOURCE_PROVIDER = "official_reconciliation"
DERIVATION_SOURCE_ID = DERIVATION_DEFINITION_ID
CURRENT_PORTION_CONCEPT_ID = (
    "current_portion_of_interest_bearing_non_current_liabilities"
)
CURRENT_PORTION_COMPONENT_IDS = tuple(
    concept.concept_id for concept in CURRENT_PORTION_COMPONENT_CONCEPTS
)


class CurrentPortionDerivationError(ValueError):
    """A direct component set cannot support the derived current portion."""


def build_current_portion_fact(
    component_facts: dict[str, dict[str, Any]],
    *,
    fact_version: int = 1,
    supersedes_fact_id: str = "",
    restatement_version: str = "original",
    created_at: str | None = None,
) -> dict[str, Any]:
    """Derive the interest-bearing current portion from three direct facts.

    The input order is the registered component order and is retained in
    ``input_fact_ids``/``derived_from`` so the lineage graph is auditable.
    """
    if tuple(component_facts) != CURRENT_PORTION_COMPONENT_IDS:
        raise CurrentPortionDerivationError(
            "component_facts must contain exactly the registered three "
            "current-portion components in registry order"
        )
    facts = [component_facts[concept] for concept in CURRENT_PORTION_COMPONENT_IDS]
    for concept, fact in zip(CURRENT_PORTION_COMPONENT_IDS, facts, strict=True):
        if fact.get("concept_id") != concept:
            raise CurrentPortionDerivationError(
                f"component concept mismatch for {concept}: "
                f"{fact.get('concept_id')}"
            )
        if fact.get("source_tier") != "reconciled_derived":
            raise CurrentPortionDerivationError(
                f"{concept} is not a reconciled direct component"
            )
        if not (
            fact.get("is_derived") is True
            and fact.get("derivation_definition_id")
            == "official_dual_source_reconciliation"
        ):
            raise CurrentPortionDerivationError(
                f"{concept} must be a direct component reconciled from the "
                "official company/exchange pair"
            )
        if fact.get("eligible_for_metrics") is not True:
            raise CurrentPortionDerivationError(
                f"{concept} is not eligible for the derivation"
            )
        if fact.get("unit") != "万元" or fact.get("value") is None:
            raise CurrentPortionDerivationError(
                f"{concept} must have a non-null value in 万元"
            )

    first = facts[0]
    stable_fields = ("symbol", "context_id", "period_end", "unit")
    for field in stable_fields:
        if any(fact.get(field) != first.get(field) for fact in facts[1:]):
            raise CurrentPortionDerivationError(
                f"current-portion components disagree on {field}"
            )
    input_ids = tuple(str(fact["fact_id"]) for fact in facts)
    available_at = max(str(fact["available_at"]) for fact in facts)
    total = sum(int(fact["value"]) for fact in facts)
    output = {
        "concept_id": CURRENT_PORTION_CONCEPT_ID,
        "concept_version": "1",
        "symbol": first["symbol"],
        "value": total,
        "unit": "万元",
        "context_id": first["context_id"],
        "is_derived": True,
        "derived_from": ",".join(input_ids),
        "derivation_definition_id": DERIVATION_DEFINITION_ID,
        "derivation_version": DERIVATION_VERSION,
        "input_fact_ids": ",".join(input_ids),
        "source_provider": DERIVATION_SOURCE_PROVIDER,
        "source_id": DERIVATION_SOURCE_ID,
        "source_tier": "reconciled_derived",
        "source_document": "official note component derivation",
        "source_url": "",
        "source_hash": "",
        "source_page": "see input reconciled component Facts",
        "source_table": "附注：一年内到期的长期借款/应付债券/租赁负债",
        "source_label": "一年内到期的有息非流动负债（派生）",
        "fact_version": fact_version,
        "restatement_version": restatement_version,
        "supersedes_fact_id": supersedes_fact_id,
        "fiscal_year": int(str(first["period_end"])[:4]),
        "report_type": "annual",
        "period_start": first.get("period_start", ""),
        "period_end": first["period_end"],
        "filing_date": max(str(fact["filing_date"]) for fact in facts),
        "announcement_date": available_at,
        "available_at": available_at,
        "raw_value": None,
        "raw_unit": "",
        "normalized_value": total,
        "normalization_rule": "SUM_RECONCILED_CURRENT_PORTION_COMPONENTS",
        "verification_status": "reconciled",
        "verification_note": (
            "Derived only as the sum of the three reconciled direct official "
            "components: current long-term borrowings, current bonds, and "
            "current lease liabilities; the disclosed current long-term "
            "payables component is excluded as non-interest-bearing."
        ),
        "eligible_for_metrics": True,
        "created_at": created_at or datetime.now().isoformat(),
    }
    output["fact_id"] = build_fact_id(output)
    return output
