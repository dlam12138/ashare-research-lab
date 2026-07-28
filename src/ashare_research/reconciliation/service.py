"""M2 Stage 1C-A.2 - Official fact reconciliation service.

Thin orchestration around the pure :class:`ReconciliationEngine`:

  load two facts -> call engine -> validate canonical id ->
  transactionally persist the reconciled fact -> write lineage ->
  return result.

It does NOT fetch from the network, parse documents, or register reports.
The two input facts are accepted as dicts (already loaded / constructed).
Both inputs are persisted (idempotent) so they are retained as audit
trail; only the reconciled fact is ``eligible_for_metrics``.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from ashare_research.facts.identity import (
    build_fact_id,
    validate_canonical_fact_ids,
)
from ashare_research.facts.repository import FactRepository
from ashare_research.reconciliation.engine import ReconciliationEngine
from ashare_research.reconciliation.models import ReconciliationResult

logger = logging.getLogger(__name__)

RECONCILIATION_SOURCE_PROVIDER = "official_reconciliation"
RECONCILIATION_METHOD = "dual_source_reconciliation"


class OfficialFactReconciliationService:
    """Reconcile a company-official fact against an exchange-official fact
    and persist the canonical reconciled fact when they match."""

    def __init__(
        self,
        repository: FactRepository,
        *,
        engine: ReconciliationEngine | None = None,
    ) -> None:
        self.repository = repository
        self.engine = engine or ReconciliationEngine()

    def reconcile_official_pair(
        self,
        company_fact: dict[str, Any],
        exchange_fact: dict[str, Any],
    ) -> ReconciliationResult:
        """Reconcile two official facts.

        Both inputs are stored (idempotent) so they are retained as
        ineligible audit trail.  When the engine reports ``matched``, the
        canonical reconciled fact is stored in the same transaction and a
        lineage row linking the two inputs is written.  Repeated
        reconciliation of the same pair is idempotent (same canonical
        fact_id -> repository returns unchanged).

        Raises ``FactVersionConflictError`` if a reconciled fact with the
        same canonical id but different payload already exists (evidence
        changed without an explicit version bump).
        """
        now = datetime.now().isoformat()
        result = self.engine.reconcile_pair(
            company_fact, exchange_fact, now=now,
        )
        if result.output_fact is None:
            return result

        # Defense in depth: the reconciled fact must be canonical.
        validate_canonical_fact_ids([result.output_fact])
        if result.output_fact["fact_id"] != build_fact_id(
            result.output_fact,
        ):
            # Should be unreachable (engine builds canonical ids), but the
            # service boundary must never trust the engine blindly.
            raise RuntimeError(
                "Reconciliation engine produced a non-canonical fact_id"
            )

        recon_run_id = f"recon_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
        parent_ids = ",".join(sorted([
            result.company_fact_id,
            result.exchange_fact_id,
        ]))

        with self.repository.transaction() as conn:
            # Retain both inputs as ineligible audit trail (idempotent).
            self.repository.store_facts(
                [company_fact, exchange_fact], conn=conn,
            )
            # Persist the reconciled fact (idempotent on repeat).
            self.repository.store_facts(
                [result.output_fact], conn=conn,
            )
            self.repository.store_lineage(
                fact_id=result.output_fact["fact_id"],
                run_id=recon_run_id,
                source_provider=RECONCILIATION_SOURCE_PROVIDER,
                source_tier="reconciled_derived",
                source_method=RECONCILIATION_METHOD,
                parent_fact_ids=parent_ids,
                conn=conn,
            )

        return result
