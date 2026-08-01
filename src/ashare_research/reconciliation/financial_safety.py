"""Additive Stage 2E-B reconciliation contract.

The frozen reconciliation engine is intentionally unchanged.  This module
uses its immutable rule value object for the new seven-concept scope.
"""

from __future__ import annotations

from ashare_research.facts.financial_safety_concepts import (
    install_financial_safety_concepts,
)
from ashare_research.reconciliation.engine import NumericReconciliationRule

install_financial_safety_concepts()

FINANCIAL_SAFETY_RULE_ID = "RECON_OFFICIAL_NUMERIC_006"
FINANCIAL_SAFETY_RULE_VERSION = "1"

FINANCIAL_SAFETY_RECONCILIATION_RULE = NumericReconciliationRule(
    rule_id=FINANCIAL_SAFETY_RULE_ID,
    version=FINANCIAL_SAFETY_RULE_VERSION,
    supported_concepts=frozenset(
        {
            "total_liabilities",
            "short_term_borrowings",
            "current_portion_of_interest_bearing_non_current_liabilities",
            "long_term_borrowings",
            "bonds_payable",
            "lease_liabilities",
            "cash_and_cash_equivalents",
        }
    ),
)
