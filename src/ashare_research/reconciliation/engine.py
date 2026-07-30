"""M2 Stage 1C-A.2.1 - Minimal official dual-source reconciliation engine.

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
     context_id, period_end, fact_version, restatement_version must match
     (plus derived statement_type / consolidation_scope).  ``unit`` is
     deliberately NOT compared here: it is resolved by the unit-conversion
     gate so that a company value in 万元 can match an exchange value in
     元.  Otherwise ``not_comparable``.
  5. Concept support -- only revenue, net_profit_attributable_to_parent,
     operating_cash_flow.  Otherwise ``insufficient_evidence``.
  6. Unit/currency -> canonical 万元 -- only CNY / 元 / 万元 / 亿元 are
     convertible.  Otherwise ``not_comparable``.
  7. Integral + safe-integer range -- each canonical value must be an
     exact integer and ``abs(value) <= 2**53 - 1`` (DOUBLE cannot
     represent every integer beyond 2^53).  Otherwise
     ``insufficient_evidence``.
  8. Exact Decimal comparison -- equal -> ``matched`` (emit fact); else
     ``mismatch``.

No tolerance, no averaging, no auto-selection.  Decimal is used for
comparison and unit normalization only; v1 persists only exact integral
canonical-unit (万元) values.  The output fact never passes through
``float()``.

This engine is symbol-agnostic: it contains no company-specific
literals.  The reconciled ``source_id`` is built from the symbol + rule,
so the same engine serves any company.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
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
SUPPLEMENTAL_RULE_ID = "RECON_OFFICIAL_NUMERIC_002"
SUPPLEMENTAL_RULE_VERSION = "1"

# Only these three concepts are reconcilable in the first version.
SUPPORTED_CONCEPTS: frozenset[str] = frozenset({
    "revenue",
    "net_profit_attributable_to_parent",
    "operating_cash_flow",
})

# v1 canonical storage unit.  Large-listed-company amounts expressed in 元
# can approach / exceed the DOUBLE safe-integer ceiling (2**53 - 1); 万元
# gives four orders of magnitude of headroom while remaining lossless for
# the three supported concepts' officially disclosed values.
CANONICAL_UNIT = "万元"


@dataclass(frozen=True)
class NumericReconciliationRule:
    """Explicit immutable contract for one official numeric rule.

    The default remains ``RECON_OFFICIAL_NUMERIC_001`` v1.  Supplemental
    concepts must opt into a separate rule so extending coverage cannot
    silently change the semantic scope or identities of the frozen rule.
    """

    rule_id: str
    version: str
    supported_concepts: frozenset[str]


DEFAULT_NUMERIC_RECONCILIATION_RULE = NumericReconciliationRule(
    rule_id=RULE_ID,
    version=RULE_VERSION,
    supported_concepts=SUPPORTED_CONCEPTS,
)

CAPEX_CASH_RECONCILIATION_RULE = NumericReconciliationRule(
    rule_id=SUPPLEMENTAL_RULE_ID,
    version=SUPPLEMENTAL_RULE_VERSION,
    supported_concepts=frozenset({"cash_paid_for_fixed_assets"}),
)

# Decimal conversion factors for amount units -> canonical 万元.  Kept as
# Decimal so comparison never passes through binary float.
_UNIT_DECIMAL_FACTORS: dict[str, Decimal] = {
    "CNY": Decimal("0.0001"),       # 元 -> 万元 (÷10000)
    "元": Decimal("0.0001"),         # 元 -> 万元 (÷10000)
    "万元": Decimal("1"),            # identity
    "亿元": Decimal("10000"),        # 亿元 -> 万元 (×10000)
}

# DOUBLE cannot represent every integer beyond 2**53 - 1; canonical values
# must stay within this range to be stored exactly.
_SAFE_INT_MAX = Decimal(2**53 - 1)

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
# NOTE: ``unit`` is intentionally absent -- it is resolved by the
# unit-conversion gate (gate 6) so cross-unit pairs (万元 vs 元) are
# comparable.  ``currency`` is CNY-only by construction (only CNY-family
# units are convertible), so it is enforced implicitly by gate 6.
_IDENTITY_FIELDS = (
    "symbol",
    "concept_id",
    "concept_version",
    "context_id",
    "period_end",
    "fact_version",
    "restatement_version",
)


def build_reconciliation_source_id(
    symbol: str,
    rule_id: str,
    rule_version: str,
) -> str:
    """Build the generic reconciled-fact ``source_id``.

    Format: ``reconciled:{symbol}:company_exchange:{rule_id}:v{rule_version}``

    Symbol-agnostic and stable: the same engine serves any company, and the
    same company + rule always yields the same source_id.  This is the
    ``source_id`` only (NOT the canonical ``fact_id``, which is always
    produced by :func:`build_fact_id`).
    """
    return (
        f"reconciled:{symbol}:company_exchange:{rule_id}:v{rule_version}"
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


def _to_canonical_decimal(
    fact: dict[str, Any],
) -> tuple[Decimal, bool]:
    """Return (decimal value in canonical 万元, ok).

    ok=False if the unit is not convertible or the value is missing.
    """
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


def _is_integral(value: Decimal) -> bool:
    """True if the Decimal is an exact integer value."""
    return value == value.to_integral_value()


def _max_date(a: str, b: str) -> str:
    """Later of two YYYY-MM-DD strings (lexicographic == chronological)."""
    return a if a >= b else b


class ReconciliationEngine:
    """Pure dual-source reconciliation for official numeric facts."""

    def __init__(
        self,
        rule: NumericReconciliationRule | None = None,
    ) -> None:
        self.rule = rule or DEFAULT_NUMERIC_RECONCILIATION_RULE

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
                rule_id=self.rule.rule_id,
                rule_version=self.rule.version,
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

        # 4. Comparable identity (unit excluded -- resolved in gate 6).
        mismatched = self._identity_mismatches(company, exchange)
        if mismatched:
            return _result(
                ReconciliationStatus.not_comparable,
                f"comparable identity fields differ: {mismatched}",
            )

        # 5. Concept support.
        concept_id = _str(company.get("concept_id"))
        if concept_id not in self.rule.supported_concepts:
            supported = ", ".join(sorted(self.rule.supported_concepts))
            return _result(
                ReconciliationStatus.insufficient_evidence,
                f"concept {concept_id!r} is not supported by "
                f"{self.rule.rule_id} (only {supported})",
            )

        # 6. Unit / currency -> canonical 万元.
        company_dec, ok_c = _to_canonical_decimal(company)
        exchange_dec, ok_e = _to_canonical_decimal(exchange)
        if not (ok_c and ok_e):
            return _result(
                ReconciliationStatus.not_comparable,
                "one or both inputs have a unit not convertible to "
                f"{CANONICAL_UNIT} (only CNY / 元 / 万元 / 亿元 supported)",
            )

        # 7. Integral + safe-integer range (v1 persistence contract).
        for label, dec in (("company", company_dec), ("exchange", exchange_dec)):
            if not _is_integral(dec):
                return _result(
                    ReconciliationStatus.insufficient_evidence,
                    f"{label} canonical value {dec} is not an exact integer; "
                    f"{self.rule.rule_id} v{self.rule.version} only supports "
                    "integral "
                    f"{CANONICAL_UNIT} values",
                )
            if abs(dec) > _SAFE_INT_MAX:
                return _result(
                    ReconciliationStatus.insufficient_evidence,
                    f"{label} canonical value {dec} exceeds the DOUBLE "
                    f"safe-integer range (2**53 - 1); cannot store exactly",
                )

        company_val_s = str(company_dec)
        exchange_val_s = str(exchange_dec)
        diff_s = str(abs(company_dec - exchange_dec))

        # 8. Exact Decimal comparison.
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

    def _reconciliation_id(
        self,
        company_id: str,
        exchange_id: str,
    ) -> str:
        """Deterministic run identity for the pair (not the canonical
        fact_id).  Stable across repeated reconciliation of the same pair.
        Uses the full SHA-256 hex digest (no truncation)."""
        raw = f"{self.rule.rule_id}|{company_id}|{exchange_id}"
        return "recon_" + hashlib.sha256(raw.encode()).hexdigest()

    def _build_reconciled_fact(
        self,
        company: dict[str, Any],
        exchange: dict[str, Any],
        matched_value: Decimal,
        *,
        now: str,
    ) -> dict[str, Any]:
        """Build the canonical reconciled fact dict.

        Stable identity fields come from the two (identical) inputs.
        ``fact_id`` is canonical (build_fact_id).  input_fact_ids is
        stably sorted.  The canonical value is persisted as an exact
        integer in 万元 -- never through ``float()``.
        """
        input_ids = sorted([
            _str(company.get("fact_id")),
            _str(exchange.get("fact_id")),
        ])
        joined = ",".join(input_ids)
        # Exact integer canonical value -- no float intermediary.
        canonical_int = int(matched_value.to_integral_value())
        symbol = _str(company.get("symbol"))
        source_id = build_reconciliation_source_id(
            symbol, self.rule.rule_id, self.rule.version,
        )
        fact: dict[str, Any] = {
            "concept_id": _str(company.get("concept_id")),
            "concept_version": _str(company.get("concept_version")),
            "symbol": symbol,
            "value": canonical_int,
            "unit": CANONICAL_UNIT,
            "context_id": _str(company.get("context_id")),
            "is_derived": True,
            "derived_from": joined,
            "derivation_definition_id": "official_dual_source_reconciliation",
            "derivation_version": self.rule.version,
            "input_fact_ids": joined,
            "source_provider": "official_reconciliation",
            "source_id": source_id,
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
            "raw_value": canonical_int,
            "raw_unit": CANONICAL_UNIT,
            "normalized_value": canonical_int,
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
