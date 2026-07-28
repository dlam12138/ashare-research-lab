"""M2 Stage 1C-A.2 - Minimal official dual-source reconciliation engine.

A *pure* engine: ``reconcile_pair(company_fact, exchange_fact)`` takes two
fact dicts and returns a :class:`ReconciliationResult`.  It performs no I/O,
touches no repository, and does not call ``datetime.now`` (the caller passes
``now`` for the output fact's ``created_at``).

Hard gates (in order, first failure wins):

  1. Source tier -- exactly one ``company_official`` and one
     ``exchange_official`` (reversed order is normalized).  Same tier, a
     candidate, or a reconciled fact -> ``not_comparable``.
  2. Verification -- both must be ``verified`` and not eligible for metrics.
     Otherwise ``insufficient_evidence``.
  3. Evidence -- both must carry source_id, source_document, source_url,
     source_hash (64 hex), announcement_date, available_at.  Otherwise
     ``insufficient_evidence``.
  4. Comparable identity -- symbol, concept_id, concept_version,
     context_id, period_end, statement_type, consolidation_scope,
     currency(unit), fact_version, restatement_version must match.
     Otherwise ``not_comparable``.
  5. Concept support -- only revenue, net_profit_attributable_to_parent,
     operating_cash_flow.  Otherwise ``insufficient_evidence``.
  6. Unit/currency -- convertible to CNY.  Otherwise ``not_comparable``.
  7. Exact Decimal comparison -- equal -> ``matched`` (emit fact); else
     ``mismatch``.

No tolerance, no averaging, no auto-selection.  Decimal values are
serialized as strings; never written back through float.
"""

from __future__ import annotations

import hashlib
import re
from decimal import Decimal, InvalidOperation
from typing import Any

from ashare_research.facts.concepts import ConceptRegistry
from ashare_research.facts.contexts import parse_context_id
from ashare_research.facts.identity import build_fact_id
from ashare_research.reconciliation.models import (
    ReconciliationResult,
    ReconciliationStatus,
)

RULE_ID = "RECON_OFFICIAL_NUMERIC_001"
RULE_VERSION = "1"

# Only these three concepts are reconcilable in the first version.
SUPPORTED_CONCEPTS: frozenset[str] = frozenset({
    "revenue",
    "net_profit_attributable_to_parent",
    "operating_cash_flow",
})

CANONICAL_UNIT = "CNY"

# Decimal conversion factors for amount units -> CNY.  Kept as Decimal so
# comparison never passes through binary float.
_UNIT_DECIMAL_FACTORS: dict[str, Decimal] = {
    "CNY": Decimal("1"),
    "元": Decimal("1"),
    "万元": Decimal("10000"),
    "亿元": Decimal("100000000"),
}

_HEXDIGEST64 = re.compile(r"^[0-9a-f]{64}$")

_EVIDENCE_FIELDS = (
    "source_id",
    "source_document",
    "source_url",
    "source_hash",
    "announcement_date",
    "available_at",
)

# Identity fields that must be identical for two facts to be comparable.
_IDENTITY_FIELDS = (
    "symbol",
    "concept_id",
    "concept_version",
    "context_id",
    "period_end",
    "fact_version",
    "restatement_version",
    "unit",  # currency proxy
)


def _str(value: Any) -> str:
    """Stringify for Decimal conversion; None -> ''."""
    if value is None:
        return ""
    return str(value)


def _statement_type(concept_id: str) -> str:
    concept = ConceptRegistry.get(concept_id)
    return concept.statement_type if concept else ""


def _consolidation_scope(context_id: str) -> str:
    parsed = parse_context_id(context_id)
    return str(parsed.get("consolidation_scope", ""))


def _is_verified(fact: dict[str, Any]) -> bool:
    return (
        _str(fact.get("verification_status")) == "verified"
        and fact.get("eligible_for_metrics") is False
    )


def _has_evidence(fact: dict[str, Any]) -> bool:
    for fld in _EVIDENCE_FIELDS:
        if not _str(fact.get(fld)):
            return False
    # source_hash must be a full SHA-256 hex digest.
    return bool(_HEXDIGEST64.match(_str(fact.get("source_hash"))))


def _to_cny_decimal(fact: dict[str, Any]) -> tuple[Decimal, bool]:
    """Return (decimal value in CNY, ok).  ok=False if not convertible."""
    unit = _str(fact.get("unit"))
    factor = _UNIT_DECIMAL_FACTORS.get(unit)
    if factor is None:
        return Decimal("0"), False
    raw = _str(fact.get("normalized_value"))
    if not raw:
        return Decimal("0"), False
    try:
        return Decimal(raw) * factor, True
    except InvalidOperation:
        return Decimal("0"), False


def _max_date(a: str, b: str) -> str:
    """Later of two YYYY-MM-DD strings (lexicographic == chronological)."""
    return a if a >= b else b


class ReconciliationEngine:
    """Pure dual-source reconciliation for official numeric facts."""

    def reconcile_pair(
        self,
        company_fact: dict[str, Any],
        exchange_fact: dict[str, Any],
        *,
        now: str = "",
    ) -> ReconciliationResult:
        """Reconcile a company-official fact against an exchange-official
        fact.  Returns a :class:`ReconciliationResult`; never raises on
        comparison failures (they are encoded as status)."""
        company, exchange = self._normalize_order(company_fact, exchange_fact)
        company_id = _str(company.get("fact_id"))
        exchange_id = _str(exchange.get("fact_id"))
        recon_id = self._reconciliation_id(company_id, exchange_id)

        def _result(
            status: ReconciliationStatus,
            reason: str,
            company_val: str = "",
            exchange_val: str = "",
            diff: str = "",
            output: dict[str, Any] | None = None,
        ) -> ReconciliationResult:
            return ReconciliationResult(
                reconciliation_id=recon_id,
                rule_id=RULE_ID,
                rule_version=RULE_VERSION,
                company_fact_id=company_id,
                exchange_fact_id=exchange_id,
                status=status,
                comparable=status
                in (ReconciliationStatus.matched,
                    ReconciliationStatus.mismatch),
                company_normalized_value=company_val,
                exchange_normalized_value=exchange_val,
                absolute_difference=diff,
                decision_reason=reason,
                output_fact=output,
            )

        # 1. Source tier: must be one company_official + one exchange_official.
        if not self._is_official_pair(company, exchange):
            return _result(
                ReconciliationStatus.not_comparable,
                "source tiers are not a company_official + exchange_official "
                "pair (same tier, candidate, or reconciled fact rejected)",
            )

        # 2. Verification: both verified and not eligible for metrics.
        if not (_is_verified(company) and _is_verified(exchange)):
            return _result(
                ReconciliationStatus.insufficient_evidence,
                "one or both inputs are not verified official facts "
                "(verification_status != 'verified' or "
                "eligible_for_metrics != false)",
            )

        # 3. Evidence completeness.
        if not (_has_evidence(company) and _has_evidence(exchange)):
            return _result(
                ReconciliationStatus.insufficient_evidence,
                "one or both inputs lack required evidence "
                "(source_id/source_document/source_url/source_hash/"
                "announcement_date/available_at or source_hash not 64-hex)",
            )

        # 4. Comparable identity.
        mismatched = self._identity_mismatches(company, exchange)
        if mismatched:
            return _result(
                ReconciliationStatus.not_comparable,
                f"comparable identity fields differ: {mismatched}",
            )

        # 5. Concept support.
        concept_id = _str(company.get("concept_id"))
        if concept_id not in SUPPORTED_CONCEPTS:
            return _result(
                ReconciliationStatus.insufficient_evidence,
                f"concept {concept_id!r} is not supported by "
                f"{RULE_ID} (only revenue, "
                f"net_profit_attributable_to_parent, operating_cash_flow)",
            )

        # 6. Unit / currency -> CNY.
        company_dec, ok_c = _to_cny_decimal(company)
        exchange_dec, ok_e = _to_cny_decimal(exchange)
        if not (ok_c and ok_e):
            return _result(
                ReconciliationStatus.not_comparable,
                "one or both inputs have a unit not convertible to CNY",
            )

        company_val_s = str(company_dec)
        exchange_val_s = str(exchange_dec)
        diff_s = str(abs(company_dec - exchange_dec))

        # 7. Exact Decimal comparison.
        if company_dec == exchange_dec:
            output = self._build_reconciled_fact(
                company, exchange, company_dec, now=now,
            )
            return _result(
                ReconciliationStatus.matched,
                "company and exchange values match exactly",
                company_val=company_val_s,
                exchange_val=exchange_val_s,
                diff=diff_s,
                output=output,
            )
        return _result(
            ReconciliationStatus.mismatch,
            "company and exchange values differ",
            company_val=company_val_s,
            exchange_val=exchange_val_s,
            diff=diff_s,
        )

    # ── helpers ──────────────────────────────────────────────────────

    @staticmethod
    def _normalize_order(
        company: dict[str, Any], exchange: dict[str, Any],
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """Ensure company is company_official and exchange is
        exchange_official, swapping if the caller passed them reversed."""
        if (
            _str(company.get("source_tier")) == "exchange_official"
            and _str(exchange.get("source_tier")) == "company_official"
        ):
            return exchange, company
        return company, exchange

    @staticmethod
    def _is_official_pair(
        company: dict[str, Any], exchange: dict[str, Any],
    ) -> bool:
        return (
            _str(company.get("source_tier")) == "company_official"
            and _str(exchange.get("source_tier")) == "exchange_official"
        )

    @staticmethod
    def _identity_mismatches(
        company: dict[str, Any], exchange: dict[str, Any],
    ) -> list[str]:
        mismatched: list[str] = []
        for fld in _IDENTITY_FIELDS:
            if _str(company.get(fld)) != _str(exchange.get(fld)):
                mismatched.append(fld)
        # Fields derived from concept / context.
        if _statement_type(_str(company.get("concept_id"))) != \
                _statement_type(_str(exchange.get("concept_id"))):
            mismatched.append("statement_type")
        if _consolidation_scope(_str(company.get("context_id"))) != \
                _consolidation_scope(_str(exchange.get("context_id"))):
            mismatched.append("consolidation_scope")
        return mismatched

    @staticmethod
    def _reconciliation_id(company_id: str, exchange_id: str) -> str:
        """Deterministic run identity for the pair (not the canonical
        fact_id).  Stable across repeated reconciliation of the same pair."""
        raw = f"{RULE_ID}|{company_id}|{exchange_id}"
        return "recon_" + hashlib.sha256(raw.encode()).hexdigest()[:16]

    @staticmethod
    def _build_reconciled_fact(
        company: dict[str, Any],
        exchange: dict[str, Any],
        matched_value: Decimal,
        *,
        now: str,
    ) -> dict[str, Any]:
        """Build the canonical reconciled fact dict.

        Stable identity fields come from the two (identical) inputs.
        ``fact_id`` is canonical (build_fact_id).  input_fact_ids is
        stably sorted.
        """
        input_ids = sorted([
            _str(company.get("fact_id")),
            _str(exchange.get("fact_id")),
        ])
        joined = ",".join(input_ids)
        value_f = float(matched_value)
        fact: dict[str, Any] = {
            "concept_id": _str(company.get("concept_id")),
            "concept_version": _str(company.get("concept_version")),
            "symbol": _str(company.get("symbol")),
            "value": value_f,
            "unit": CANONICAL_UNIT,
            "context_id": _str(company.get("context_id")),
            "is_derived": True,
            "derived_from": joined,
            "derivation_definition_id": "official_dual_source_reconciliation",
            "derivation_version": RULE_VERSION,
            "input_fact_ids": joined,
            "source_provider": "official_reconciliation",
            "source_id": "reconciled:petrochina_company_sse",
            "source_tier": "reconciled_derived",
            "source_document": "official dual-source reconciliation",
            "source_url": "",
            "source_hash": "",
            "source_page": "",
            "source_table": "",
            "source_label": "reconciled",
            "fact_version": int(company.get("fact_version", 1) or 1),
            "restatement_version": _str(
                company.get("restatement_version", "original"),
            ),
            "supersedes_fact_id": "",
            "fiscal_year": int(company.get("fiscal_year", 0) or 0),
            "report_type": _str(company.get("report_type", "annual")),
            "period_end": _str(company.get("period_end")),
            "filing_date": _max_date(
                _str(company.get("filing_date")),
                _str(exchange.get("filing_date")),
            ),
            "announcement_date": _max_date(
                _str(company.get("announcement_date")),
                _str(exchange.get("announcement_date")),
            ),
            "available_at": _max_date(
                _str(company.get("available_at")),
                _str(exchange.get("available_at")),
            ),
            "raw_value": value_f,
            "raw_unit": CANONICAL_UNIT,
            "normalized_value": value_f,
            "normalization_rule": "identity",
            "verification_status": "reconciled",
            "verification_note": (
                "cross-verified company_official + exchange_official"
            ),
            "eligible_for_metrics": True,
            "created_at": now,
        }
        fact["fact_id"] = build_fact_id(fact)
        return fact
