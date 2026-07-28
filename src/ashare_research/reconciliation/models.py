"""M2 Stage 1C-A.2 - Reconciliation models.

``ReconciliationStatus`` and ``ReconciliationResult`` are the only public
types.  Numeric fields are serialized as strings (Decimal) -- they must
never be written back through binary float.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class ReconciliationStatus(str, Enum):
    """Outcome of reconciling two official facts."""

    matched = "matched"                  # values exactly equal -> emit fact
    mismatch = "mismatch"               # values differ -> no fact
    not_comparable = "not_comparable"   # identity/source mismatch -> no fact
    insufficient_evidence = (
        "insufficient_evidence"
    )                                   # missing verification/evidence -> no fact


@dataclass(frozen=True)
class ReconciliationResult:
    """Result of one reconciliation attempt.

    Decimal-valued fields (``company_normalized_value``,
    ``exchange_normalized_value``, ``absolute_difference``) are string
    serializations of :class:`decimal.Decimal`; consumers must not coerce
    them back through float.

    ``output_fact`` is a fact dict (the canonical reconciled fact) when
    ``status == matched`` and ``None`` otherwise.  It is a dict rather than
    a ``Fact`` dataclass to stay consistent with the repository / identity
    layer, which uniformly operates on dicts.
    """

    reconciliation_id: str
    rule_id: str
    rule_version: str

    company_fact_id: str
    exchange_fact_id: str

    status: ReconciliationStatus
    comparable: bool

    company_normalized_value: str
    exchange_normalized_value: str
    absolute_difference: str

    decision_reason: str
    output_fact: dict[str, Any] | None
