"""M2 Stage 1C-A.2.1 - Official fact reconciliation service.

Orchestration around the pure :class:`ReconciliationEngine` with a full
validate-before-write contract:

  1. receive company_fact + exchange_fact
  2. canonical id validation on both inputs
  3. FactValidator on both inputs
 4. VersionChainValidator on versioned inputs
 5. context_id existence check (must be registered in fact_contexts)
 6. call the engine
 7. if status != matched -> return result, write nothing
 8. bind an explicit reconciled supersedes id for versioned output
 9. canonical id validation on the output fact
 10. FactValidator on the output fact
 11. FACT_RECON_INPUT_001 (one company_official + one exchange_official,
     both verified and ineligible; output provenance and all three lineage
     roles strictly bound to those actual inputs)
 12. VersionChainValidator if output.fact_version > 1
 13. any error severity -> raise ReconciliationValidationError, write nothing
 14. single transaction: idempotent store of both inputs + reconciled fact,
     then 3 lineage rows (input_company / input_exchange / output)
 15. commit and return

It does NOT fetch from the network, parse documents, or register reports.
The two input facts are accepted as dicts (already loaded / constructed).
Both inputs are persisted (idempotent) so they are retained as
ineligible audit trail; only the reconciled fact is ``eligible_for_metrics``.
"""

from __future__ import annotations

import logging
import re
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
_FACT_ID = re.compile(r"^[0-9a-f]{64}$")


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
        *,
        output_supersedes_fact_id: str = "",
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

        # 4. Repository-aware version-chain validation on both inputs.
        # Version 1 facts are ignored by VersionChainValidator.  Versioned
        # facts must prove their predecessor before the engine runs or any
        # transaction opens.
        input_errors.extend(
            self.version_chain_validator.validate(
                [company_fact, exchange_fact],
                conn=self.repository.store.connect(),
                now=now,
            )
        )
        input_errors.extend(
            self._check_input_source_tier_chains(
                company_fact, exchange_fact, now,
            )
        )
        self._raise_on_errors(input_errors)

        # 5. Context existence check (pre-transaction read).
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

        # 6. Engine.
        result = self.engine.reconcile_pair(
            company_fact, exchange_fact, now=now,
        )

        # 7. Non-matched -> return without writing.
        if result.output_fact is None:
            return result
        output_fact = result.output_fact

        # 8. Versioned reconciled output must explicitly bind its actual
        # predecessor. The pure engine deliberately never guesses this id.
        output_version = int(output_fact.get("fact_version", 1) or 1)
        if output_version == 1:
            if output_supersedes_fact_id:
                raise ReconciliationValidationError(
                    "Version 1 reconciled output must not specify "
                    "output_supersedes_fact_id; no facts or lineage written"
                )
        else:
            if _FACT_ID.fullmatch(output_supersedes_fact_id) is None:
                raise ReconciliationValidationError(
                    "Versioned reconciled output requires a complete "
                    "64-character lowercase output_supersedes_fact_id; "
                    "no facts or lineage written"
                )
            output_fact["supersedes_fact_id"] = output_supersedes_fact_id
            output_fact["fact_id"] = build_fact_id(output_fact)

        # 9. Canonical id validation on output after supersedes binding.
        validate_canonical_fact_ids([output_fact])
        if output_fact["fact_id"] != build_fact_id(output_fact):
            raise ReconciliationValidationError(
                "Reconciliation engine produced a non-canonical fact_id"
            )

        recon_run_id = (
            f"recon_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
        )
        lineage_rows = self._build_reconciliation_lineage(
            company_fact, exchange_fact, output_fact, recon_run_id,
        )
        for row in lineage_rows:
            row["reconciliation_rule_id"] = result.rule_id
            row["reconciliation_rule_version"] = result.rule_version

        # 10-12. Output validation + FACT_RECON_INPUT_001 + version chain.
        post_errors: list[FactValidationResult] = []
        post_errors.extend(self.validator.validate_single_fact(output_fact))
        post_errors.extend(
            self._check_recon_inputs(
                company_fact, exchange_fact, output_fact, result, now,
            )
        )
        post_errors.extend(
            self._check_recon_lineage(
                company_fact, exchange_fact, output_fact, lineage_rows, now,
            )
        )
        if output_version > 1:
            post_errors.extend(
                self.version_chain_validator.validate(
                    [output_fact], conn=self.repository.store.connect(),
                )
            )
        self._raise_on_errors(post_errors)

        # 14. Transactional write.
        with self.repository.transaction() as conn:
            # Retain both inputs as ineligible audit trail (idempotent).
            self.repository.store_facts(
                [company_fact, exchange_fact], conn=conn,
            )
            # Persist the reconciled fact (idempotent on repeat; raises
            # FactVersionConflictError on payload change).
            self.repository.store_facts([output_fact], conn=conn)

            # Lineage was fully bound and validated before opening the
            # transaction.  Persist exactly those three checked rows.
            for row in lineage_rows:
                self.repository.store_lineage(**row, conn=conn)

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

    def _check_input_source_tier_chains(
        self,
        company_fact: dict[str, Any],
        exchange_fact: dict[str, Any],
        now: str,
    ) -> list[FactValidationResult]:
        """Keep source_tier stable across versioned official raw facts.

        VersionChainValidator owns the shared stable-identity contract.
        ``source_tier`` is additionally enforced here because it is a
        service-level official-pair role rather than a FactIdentity field.
        """
        conn = self.repository.store.connect()
        errors: list[FactValidationResult] = []
        for fact in (company_fact, exchange_fact):
            version = fact.get("fact_version", 1)
            if not (isinstance(version, int) and version > 1):
                continue
            predecessor_id = str(fact.get("supersedes_fact_id", ""))
            predecessor = self.repository._get_fact_by_id(
                predecessor_id, conn,
            )
            if predecessor is None:
                continue
            old_tier = str(predecessor.get("source_tier", ""))
            new_tier = str(fact.get("source_tier", ""))
            if old_tier != new_tier:
                errors.append(FactValidationResult(
                    rule_id="FACT_VERSIONCHAIN_001",
                    rule_version="1",
                    target_id=str(fact.get("fact_id", "")),
                    severity="error",
                    passed=False,
                    expected=f"source_tier remains {old_tier!r}",
                    actual=f"source_tier={new_tier!r}",
                    message=(
                        "Versioned official input changes its stable "
                        "source_tier"
                    ),
                    checked_at=now,
                ))
        return errors

    @staticmethod
    def _check_recon_inputs(
        company_fact: dict[str, Any],
        exchange_fact: dict[str, Any],
        output_fact: dict[str, Any],
        result: ReconciliationResult,
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
        expected_ids = {
            str(company_fact.get("fact_id", "")),
            str(exchange_fact.get("fact_id", "")),
        }
        facts_by_tier = {
            str(fact.get("source_tier", "")): fact
            for fact in (company_fact, exchange_fact)
        }

        input_ids = OfficialFactReconciliationService._parse_fact_ids(
            output_fact.get("input_fact_ids", ""),
        )
        derived_ids = OfficialFactReconciliationService._parse_fact_ids(
            output_fact.get("derived_from", ""),
        )
        if len(input_ids) != 2 or set(input_ids) != expected_ids:
            results.append(OfficialFactReconciliationService._recon_error(
                output_fact.get("fact_id", ""),
                f"input_fact_ids exactly reference {sorted(expected_ids)}",
                f"input_fact_ids={input_ids}",
                "reconciled output must reference the actual official pair",
                now,
            ))
        if derived_ids != input_ids:
            results.append(OfficialFactReconciliationService._recon_error(
                output_fact.get("fact_id", ""),
                f"derived_from={input_ids}",
                f"derived_from={derived_ids}",
                "reconciled output derived_from must match input_fact_ids",
                now,
            ))
        expected_result_ids = (
            str(facts_by_tier.get(
                "company_official", company_fact,
            ).get("fact_id", "")),
            str(facts_by_tier.get(
                "exchange_official", exchange_fact,
            ).get("fact_id", "")),
        )
        actual_result_ids = (
            str(result.company_fact_id),
            str(result.exchange_fact_id),
        )
        if actual_result_ids != expected_result_ids:
            results.append(OfficialFactReconciliationService._recon_error(
                output_fact.get("fact_id", ""),
                f"result input ids={expected_result_ids}",
                f"result input ids={actual_result_ids}",
                "reconciliation result ids must identify the actual inputs",
                now,
            ))

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

    @staticmethod
    def _parse_fact_ids(value: Any) -> list[str]:
        """Parse a comma-separated provenance field without losing order."""
        if not isinstance(value, str):
            return []
        return [part.strip() for part in value.split(",") if part.strip()]

    @staticmethod
    def _recon_error(
        target_id: str,
        expected: str,
        actual: str,
        message: str,
        now: str,
    ) -> FactValidationResult:
        return FactValidationResult(
            rule_id="FACT_RECON_INPUT_001",
            target_id=str(target_id),
            severity="error",
            passed=False,
            expected=expected,
            actual=actual,
            message=message,
            checked_at=now,
        )

    @staticmethod
    def _build_reconciliation_lineage(
        company_fact: dict[str, Any],
        exchange_fact: dict[str, Any],
        output_fact: dict[str, Any],
        run_id: str,
        *,
        rule_id: str = RULE_ID,
        rule_version: str = RULE_VERSION,
    ) -> list[dict[str, Any]]:
        facts_by_tier = {
            str(fact.get("source_tier", "")): fact
            for fact in (company_fact, exchange_fact)
        }
        company_input = facts_by_tier.get("company_official", company_fact)
        exchange_input = facts_by_tier.get(
            "exchange_official", exchange_fact,
        )
        parent_ids = ",".join(sorted(
            OfficialFactReconciliationService._parse_fact_ids(
                output_fact.get("input_fact_ids", ""),
            )
        ))
        common = {
            "run_id": run_id,
            "source_provider": RECONCILIATION_SOURCE_PROVIDER,
            "source_method": RECONCILIATION_METHOD,
            "reconciliation_rule_id": rule_id,
            "reconciliation_rule_version": rule_version,
        }
        return [
            {
                **common,
                "fact_id": company_input.get("fact_id", ""),
                "source_tier": "company_official",
                "parent_fact_ids": "",
                "role": ROLE_INPUT_COMPANY,
            },
            {
                **common,
                "fact_id": exchange_input.get("fact_id", ""),
                "source_tier": "exchange_official",
                "parent_fact_ids": "",
                "role": ROLE_INPUT_EXCHANGE,
            },
            {
                **common,
                "fact_id": output_fact.get("fact_id", ""),
                "source_tier": "reconciled_derived",
                "parent_fact_ids": parent_ids,
                "role": ROLE_OUTPUT,
            },
        ]

    @staticmethod
    def _check_recon_lineage(
        company_fact: dict[str, Any],
        exchange_fact: dict[str, Any],
        output_fact: dict[str, Any],
        rows: list[dict[str, Any]],
        now: str,
    ) -> list[FactValidationResult]:
        facts_by_tier = {
            str(fact.get("source_tier", "")): fact
            for fact in (company_fact, exchange_fact)
        }
        expected_by_role = {
            ROLE_INPUT_COMPANY: str(facts_by_tier.get(
                "company_official", company_fact,
            ).get("fact_id", "")),
            ROLE_INPUT_EXCHANGE: str(facts_by_tier.get(
                "exchange_official", exchange_fact,
            ).get("fact_id", "")),
            ROLE_OUTPUT: str(output_fact.get("fact_id", "")),
        }
        actual_by_role = {
            str(row.get("role", "")): str(row.get("fact_id", ""))
            for row in rows
        }
        errors: list[FactValidationResult] = []
        if len(rows) != 3 or actual_by_role != expected_by_role:
            errors.append(OfficialFactReconciliationService._recon_error(
                output_fact.get("fact_id", ""),
                f"lineage roles={expected_by_role}",
                f"lineage roles={actual_by_role}, row_count={len(rows)}",
                "reconciliation lineage roles must identify the actual inputs "
                "and output",
                now,
            ))

        output_rows = [
            row for row in rows if row.get("role") == ROLE_OUTPUT
        ]
        lineage_parent_ids = (
            OfficialFactReconciliationService._parse_fact_ids(
                output_rows[0].get("parent_fact_ids", ""),
            )
            if len(output_rows) == 1 else []
        )
        output_input_ids = (
            OfficialFactReconciliationService._parse_fact_ids(
                output_fact.get("input_fact_ids", ""),
            )
        )
        if lineage_parent_ids != sorted(output_input_ids):
            errors.append(OfficialFactReconciliationService._recon_error(
                output_fact.get("fact_id", ""),
                f"output lineage parent_fact_ids={sorted(output_input_ids)}",
                f"output lineage parent_fact_ids={lineage_parent_ids}",
                "output lineage parents must match output input_fact_ids",
                now,
            ))
        return errors
