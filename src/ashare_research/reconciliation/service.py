"""M2 Stage 1C-A.2.1 - Official fact reconciliation service.

Orchestration around the pure :class:`ReconciliationEngine` with a full
validate-before-write contract:

  1. receive company_fact + exchange_fact
  2. canonical id validation on both inputs
  3. FactValidator on both inputs
  4. context_id existence check (must be registered in fact_contexts)
  5. call the engine
  6. if status != matched -> return result, write nothing
  7. canonical id validation on the output fact
  8. FactValidator on the output fact
  9. FACT_RECON_INPUT_001 (one company_official + one exchange_official,
     both verified, both ineligible)
 10. VersionChainValidator if output.fact_version > 1
 11. any error severity -> raise ReconciliationValidationError, write nothing
 12. single transaction: idempotent store of both inputs + reconciled fact,
     then 3 lineage rows (input_company / input_exchange / output)
 13. commit and return

It does NOT fetch from the network, parse documents, or register reports.
The two input facts are accepted as dicts (already loaded / constructed).
Both inputs are persisted (idempotent) so they are retained as
ineligible audit trail; only the reconciled fact is ``eligible_for_metrics``.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from ashare_research.exceptions import (
    ReconciliationValidationError,
)
from ashare_research.facts.identity import (
    build_fact_id,
    validate_canonical_fact_ids,
)
from ashare_research.facts.repository import FactRepository
from ashare_research.reconciliation.engine import (
    RULE_ID,
    RULE_VERSION,
    ReconciliationEngine,
)
from ashare_research.reconciliation.models import ReconciliationResult
from ashare_research.validation.results import FactValidationResult
from ashare_research.validation.validator import FactValidator
from ashare_research.validation.version_chain import VersionChainValidator

logger = logging.getLogger(__name__)

RECONCILIATION_SOURCE_PROVIDER = "official_reconciliation"
RECONCILIATION_METHOD = "dual_source_reconciliation"

ROLE_INPUT_COMPANY = "reconciliation_input_company"
ROLE_INPUT_EXCHANGE = "reconciliation_input_exchange"
ROLE_OUTPUT = "reconciliation_output"


class OfficialFactReconciliationService:
    """Reconcile a company-official fact against an exchange-official fact
    and persist the canonical reconciled fact when they match.

    The service does not bypass the FactValidator: both inputs and the
    output fact are validated in full before any write.  A missing
    context or any error-severity validation result aborts the write and
    raises :class:`ReconciliationValidationError`.
    """

    def __init__(
        self,
        repository: FactRepository,
        *,
        engine: ReconciliationEngine | None = None,
        validator: FactValidator | None = None,
    ) -> None:
        self.repository = repository
        self.engine = engine or ReconciliationEngine()
        self.validator = validator or FactValidator()
        self.version_chain_validator = VersionChainValidator(repository)

    # ── public entry ───────────────────────────────────────────────

    def reconcile_official_pair(
        self,
        company_fact: dict[str, Any],
        exchange_fact: dict[str, Any],
    ) -> ReconciliationResult:
        """Reconcile two official facts with full validation.

        Raises:
            ReconciliationValidationError: any input/output validation
                error, an invalid source-tier combination
                (FACT_RECON_INPUT_001), or a missing context_id.
            FactVersionConflictError: a reconciled fact with the same
                canonical id but different payload already exists.
        """
        now = datetime.now().isoformat()

        # 2. Canonical id validation on inputs.
        validate_canonical_fact_ids([company_fact, exchange_fact])

        # 3. FactValidator on inputs -> raise on any error severity.
        input_errors: list[FactValidationResult] = []
        input_errors.extend(self.validator.validate_single_fact(company_fact))
        input_errors.extend(self.validator.validate_single_fact(exchange_fact))
        self._raise_on_errors(input_errors)

        # 4. Context existence check (pre-transaction read).
        for fact, label in (
            (company_fact, "company"), (exchange_fact, "exchange"),
        ):
            ctx_id = fact.get("context_id", "")
            if not ctx_id or not self._context_exists(ctx_id):
                raise ReconciliationValidationError(
                    f"{label} input context_id {ctx_id!r} is not "
                    f"registered in fact_contexts; the service does not "
                    f"auto-create contexts (caller must register them)"
                )

        # 5. Engine.
        result = self.engine.reconcile_pair(
            company_fact, exchange_fact, now=now,
        )

        # 6. Non-matched -> return without writing.
        if result.output_fact is None:
            return result
        output_fact = result.output_fact

        # 7. Canonical id validation on output.
        validate_canonical_fact_ids([output_fact])
        if output_fact["fact_id"] != build_fact_id(output_fact):
            raise ReconciliationValidationError(
                "Reconciliation engine produced a non-canonical fact_id"
            )

        # 8-10. Output validation + FACT_RECON_INPUT_001 + version chain.
        post_errors: list[FactValidationResult] = []
        post_errors.extend(self.validator.validate_single_fact(output_fact))
        post_errors.extend(
            self._check_recon_inputs(
                company_fact, exchange_fact, now,
            )
        )
        if int(output_fact.get("fact_version", 1) or 1) > 1:
            post_errors.extend(
                self.version_chain_validator.validate(
                    [output_fact], conn=self.repository.store.connect(),
                )
            )
        self._raise_on_errors(post_errors)

        # 11. Transactional write.
        recon_run_id = (
            f"recon_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
        )
        parent_ids = ",".join(sorted([
            result.company_fact_id,
            result.exchange_fact_id,
        ]))

        with self.repository.transaction() as conn:
            # Retain both inputs as ineligible audit trail (idempotent).
            self.repository.store_facts(
                [company_fact, exchange_fact], conn=conn,
            )
            # Persist the reconciled fact (idempotent on repeat; raises
            # FactVersionConflictError on payload change).
            self.repository.store_facts([output_fact], conn=conn)

            # Lineage: 3 rows, roles distinguish company / exchange / output.
            self.repository.store_lineage(
                fact_id=result.company_fact_id,
                run_id=recon_run_id,
                source_provider=RECONCILIATION_SOURCE_PROVIDER,
                source_tier="company_official",
                source_method=RECONCILIATION_METHOD,
                parent_fact_ids="",
                role=ROLE_INPUT_COMPANY,
                reconciliation_rule_id=RULE_ID,
                reconciliation_rule_version=RULE_VERSION,
                conn=conn,
            )
            self.repository.store_lineage(
                fact_id=result.exchange_fact_id,
                run_id=recon_run_id,
                source_provider=RECONCILIATION_SOURCE_PROVIDER,
                source_tier="exchange_official",
                source_method=RECONCILIATION_METHOD,
                parent_fact_ids="",
                role=ROLE_INPUT_EXCHANGE,
                reconciliation_rule_id=RULE_ID,
                reconciliation_rule_version=RULE_VERSION,
                conn=conn,
            )
            self.repository.store_lineage(
                fact_id=output_fact["fact_id"],
                run_id=recon_run_id,
                source_provider=RECONCILIATION_SOURCE_PROVIDER,
                source_tier="reconciled_derived",
                source_method=RECONCILIATION_METHOD,
                parent_fact_ids=parent_ids,
                role=ROLE_OUTPUT,
                reconciliation_rule_id=RULE_ID,
                reconciliation_rule_version=RULE_VERSION,
                conn=conn,
            )

        return result

    # ── helpers ─────────────────────────────────────────────────────

    @staticmethod
    def _raise_on_errors(
        errors: list[FactValidationResult],
    ) -> None:
        """Raise ReconciliationValidationError on any error-severity result.

        No reconciled fact is written when validation fails; the caller
        sees a clear exception rather than a silent warning."""
        failed = [
            r for r in errors
            if r.severity == "error" and not r.passed
        ]
        if not failed:
            return
        detail = "; ".join(
            f"{r.rule_id}({r.target_id}): {r.message}" for r in failed
        )
        raise ReconciliationValidationError(
            f"Reconciliation validation failed ({len(failed)} error(s)); "
            f"no reconciled fact written: {detail}"
        )

    def _context_exists(self, context_id: str) -> bool:
        """Return True if context_id is registered in fact_contexts."""
        conn = self.repository.store.connect()
        row = conn.execute(
            "SELECT 1 FROM fact_contexts WHERE context_id = ?",
            [context_id],
        ).fetchone()
        return row is not None

    @staticmethod
    def _check_recon_inputs(
        company_fact: dict[str, Any],
        exchange_fact: dict[str, Any],
        now: str,
    ) -> list[FactValidationResult]:
        """FACT_RECON_INPUT_001: the two inputs must be one
        company_official + one exchange_official, both verified and both
        ineligible for metrics.  Returns a list of error results (empty
        when the combination is valid)."""
        tiers = {
            str(company_fact.get("source_tier", "")),
            str(exchange_fact.get("source_tier", "")),
        }
        results: list[FactValidationResult] = []

        if tiers != {"company_official", "exchange_official"}:
            results.append(FactValidationResult(
                rule_id="FACT_RECON_INPUT_001",
                target_id="reconciliation_inputs",
                severity="error", passed=False,
                expected=(
                    "one company_official + one exchange_official input"
                ),
                actual=f"source_tiers={sorted(tiers)}",
                message=(
                    "reconciled fact inputs must be a "
                    "company_official + exchange_official pair"
                ),
                checked_at=now,
            ))

        for fact, label in (
            (company_fact, "company"), (exchange_fact, "exchange"),
        ):
            if str(fact.get("verification_status", "")) != "verified":
                results.append(FactValidationResult(
                    rule_id="FACT_RECON_INPUT_001",
                    target_id=fact.get("fact_id", ""),
                    severity="error", passed=False,
                    expected=f"{label} input verification_status == verified",
                    actual=(
                        f"verification_status="
                        f"{fact.get('verification_status', '')}"
                    ),
                    message=(
                        f"{label} input to a reconciled fact must be "
                        f"verified"
                    ),
                    checked_at=now,
                ))
            if fact.get("eligible_for_metrics") is not False:
                results.append(FactValidationResult(
                    rule_id="FACT_RECON_INPUT_001",
                    target_id=fact.get("fact_id", ""),
                    severity="error", passed=False,
                    expected=(
                        f"{label} input eligible_for_metrics == false"
                    ),
                    actual=(
                        f"eligible_for_metrics="
                        f"{fact.get('eligible_for_metrics')}"
                    ),
                    message=(
                        f"{label} input to a reconciled fact must not be "
                        f"eligible for metrics"
                    ),
                    checked_at=now,
                ))

        return results
