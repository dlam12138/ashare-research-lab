"""Runtime additive registration for Stage 2E-B direct safety concepts.

The frozen base ConceptRegistry remains byte-for-byte unchanged.  Importing
this extension installs only the new version-1 concept needed by Rule 006.
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


def install_financial_safety_concepts() -> None:
    """Install the additive concept without rewriting frozen source files."""

    ConceptRegistry.CONCEPTS.setdefault(
        FINANCIAL_SAFETY_CONCEPT.concept_id,
        {FINANCIAL_SAFETY_CONCEPT.version: FINANCIAL_SAFETY_CONCEPT},
    )
