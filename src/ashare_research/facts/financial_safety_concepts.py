"""Runtime additive registration for Stage 2E-B safety concepts.

The frozen base ConceptRegistry remains byte-for-byte unchanged.  Importing
this extension installs the current-portion output concept plus the three
official direct component concepts used by the Stage 2E-B.1 derivation rule.
"""

from __future__ import annotations

from ashare_research.facts.concepts import ConceptRegistry
from ashare_research.facts.models import Concept, ConceptCategory, InstantOrDuration

FINANCIAL_SAFETY_CONCEPT = Concept(
    concept_id="current_portion_of_interest_bearing_non_current_liabilities",
    version="1",
    display_name="Current Portion of Interest-Bearing Non-Current Liabilities",
    display_name_zh="一年内到期的有息非流动负债",
    category=ConceptCategory.balance_sheet,
    canonical_unit="CNY",
    instant_or_duration=InstantOrDuration.instant,
    aliases=["一年内到期的非流动负债"],
)

CURRENT_PORTION_COMPONENT_CONCEPTS = (
    Concept(
        concept_id="current_portion_of_long_term_borrowings",
        version="1",
        display_name="Current Portion of Long-Term Borrowings",
        display_name_zh="一年内到期的长期借款",
        category=ConceptCategory.balance_sheet,
        canonical_unit="CNY",
        instant_or_duration=InstantOrDuration.instant,
        aliases=["一年内到期的长期借款"],
    ),
    Concept(
        concept_id="current_portion_of_bonds_payable",
        version="1",
        display_name="Current Portion of Bonds Payable",
        display_name_zh="一年内到期的应付债券",
        category=ConceptCategory.balance_sheet,
        canonical_unit="CNY",
        instant_or_duration=InstantOrDuration.instant,
        aliases=["一年内到期的应付债券"],
    ),
    Concept(
        concept_id="current_portion_of_lease_liabilities",
        version="1",
        display_name="Current Portion of Lease Liabilities",
        display_name_zh="一年内到期的租赁负债",
        category=ConceptCategory.balance_sheet,
        canonical_unit="CNY",
        instant_or_duration=InstantOrDuration.instant,
        aliases=["一年内到期的租赁负债"],
    ),
)


def install_financial_safety_concepts() -> None:
    """Install the additive concept without rewriting frozen source files."""

    ConceptRegistry.CONCEPTS.setdefault(
        FINANCIAL_SAFETY_CONCEPT.concept_id,
        {FINANCIAL_SAFETY_CONCEPT.version: FINANCIAL_SAFETY_CONCEPT},
    )
    for concept in CURRENT_PORTION_COMPONENT_CONCEPTS:
        ConceptRegistry.CONCEPTS.setdefault(
            concept.concept_id,
            {concept.version: concept},
        )
