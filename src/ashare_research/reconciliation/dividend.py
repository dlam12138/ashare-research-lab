"""Additive Rule 007 for official dividend and buyback numeric facts.

The frozen reconciliation engine only persists integral values in 万元.  Cash
dividend announcements are official CNY amounts (often with fen precision) and
per-share CNY values, so this extension keeps the exact Decimal value in its
declared canonical unit without changing Rules 001-006 or the generic Fact
Schema.
"""

from __future__ import annotations

import hashlib
import re
from decimal import Decimal, InvalidOperation
from typing import Any

from ashare_research.facts.identity import build_fact_id
from ashare_research.reconciliation.models import (
    ReconciliationResult,
    ReconciliationStatus,
)

DIVIDEND_RULE_ID = "RECON_OFFICIAL_NUMERIC_007"
DIVIDEND_RULE_VERSION = "1"
DIVIDEND_SUPPORTED_CONCEPTS = frozenset(
    {
        "cash_dividend_total",
        "cash_dividend_per_share",
        "share_capital",
        "shares_repurchased",
        "repurchase_amount",
    }
)
_HEX64 = re.compile(r"^[0-9a-f]{64}$")
_CANONICAL_UNITS = {
    "cash_dividend_total": "CNY",
    "cash_dividend_per_share": "CNY_PER_SHARE",
    "share_capital": "CNY",
    "shares_repurchased": "SHARE",
    "repurchase_amount": "CNY",
}


class DividendNumericReconciliationEngine:
    """Exact dual-official reconciliation for the Rule 007 concepts."""

    def __init__(self) -> None:
        self.rule_id = DIVIDEND_RULE_ID
        self.rule_version = DIVIDEND_RULE_VERSION

    def reconcile_pair(
        self,
        company_fact: dict[str, Any],
        exchange_fact: dict[str, Any],
        *,
        now: str = "",
    ) -> ReconciliationResult:
        company, exchange = self._normalize_order(company_fact, exchange_fact)
        company_id = str(company.get("fact_id", ""))
        exchange_id = str(exchange.get("fact_id", ""))
        recon_id = (
            "recon_"
            + hashlib.sha256(f"{self.rule_id}|{company_id}|{exchange_id}".encode()).hexdigest()
        )

        def result(
            status: ReconciliationStatus,
            reason: str,
            company_value: str = "",
            exchange_value: str = "",
            difference: str = "",
            output: dict[str, Any] | None = None,
        ) -> ReconciliationResult:
            return ReconciliationResult(
                reconciliation_id=recon_id,
                rule_id=self.rule_id,
                rule_version=self.rule_version,
                company_fact_id=company_id,
                exchange_fact_id=exchange_id,
                status=status,
                comparable=status in (ReconciliationStatus.matched, ReconciliationStatus.mismatch),
                company_normalized_value=company_value,
                exchange_normalized_value=exchange_value,
                absolute_difference=difference,
                decision_reason=reason,
                output_fact=output,
            )

        if {
            str(company.get("source_tier", "")),
            str(exchange.get("source_tier", "")),
        } != {"company_official", "exchange_official"}:
            return result(
                ReconciliationStatus.not_comparable,
                "Rule 007 requires one company_official and one exchange_official input",
            )
        if any(
            str(fact.get("verification_status", "")) != "verified"
            or fact.get("eligible_for_metrics") is not False
            for fact in (company, exchange)
        ):
            return result(
                ReconciliationStatus.insufficient_evidence,
                "Rule 007 inputs must be verified and ineligible",
            )
        for fact in (company, exchange):
            if any(
                not str(fact.get(field, "")).strip()
                for field in (
                    "source_id",
                    "source_document",
                    "source_url",
                    "source_hash",
                    "announcement_date",
                    "available_at",
                )
            ) or not _HEX64.fullmatch(str(fact.get("source_hash", ""))):
                return result(
                    ReconciliationStatus.insufficient_evidence,
                    "Rule 007 input evidence is incomplete",
                )
        identity_fields = (
            "symbol",
            "concept_id",
            "concept_version",
            "context_id",
            "period_end",
            "fact_version",
            "restatement_version",
        )
        mismatched = [
            field
            for field in identity_fields
            if str(company.get(field, "")) != str(exchange.get(field, ""))
        ]
        concept_id = str(company.get("concept_id", ""))
        if concept_id not in DIVIDEND_SUPPORTED_CONCEPTS:
            mismatched.append("unsupported_concept")
        if mismatched:
            return result(
                ReconciliationStatus.not_comparable,
                f"Rule 007 comparable identity differs: {mismatched}",
            )
        if str(company.get("unit", "")) != str(exchange.get("unit", "")):
            return result(
                ReconciliationStatus.not_comparable,
                "Rule 007 requires uniform canonical units",
            )
        canonical_unit = _CANONICAL_UNITS[concept_id]
        if company.get("unit") != canonical_unit:
            return result(
                ReconciliationStatus.not_comparable,
                f"Rule 007 canonical unit must be {canonical_unit}",
            )
        try:
            company_value = Decimal(str(company.get("value")))
            exchange_value = Decimal(str(exchange.get("value")))
        except (InvalidOperation, TypeError):
            return result(
                ReconciliationStatus.insufficient_evidence,
                "Rule 007 values are not Decimal-parsable",
            )
        if not company_value.is_finite() or not exchange_value.is_finite():
            return result(
                ReconciliationStatus.insufficient_evidence,
                "Rule 007 values must be finite",
            )
        difference = abs(company_value - exchange_value)
        if company_value != exchange_value:
            return result(
                ReconciliationStatus.mismatch,
                "company and exchange values differ exactly",
                str(company_value),
                str(exchange_value),
                str(difference),
            )
        output = self._build_output(company, exchange, company_value, now=now)
        return result(
            ReconciliationStatus.matched,
            "company and exchange values match exactly",
            str(company_value),
            str(exchange_value),
            str(difference),
            output,
        )

    @staticmethod
    def _normalize_order(
        company: dict[str, Any], exchange: dict[str, Any]
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        if (
            company.get("source_tier") == "exchange_official"
            and exchange.get("source_tier") == "company_official"
        ):
            return exchange, company
        return company, exchange

    def _build_output(
        self,
        company: dict[str, Any],
        exchange: dict[str, Any],
        value: Decimal,
        *,
        now: str,
    ) -> dict[str, Any]:
        input_ids = sorted([str(company["fact_id"]), str(exchange["fact_id"])])
        concept_id = str(company["concept_id"])
        event_id = str(company.get("event_id", ""))
        source_id = (
            f"reconciled:{company['symbol']}:{event_id}:{concept_id}:"
            f"{self.rule_id}:v{self.rule_version}"
        )
        announcement_date = max(
            str(company.get("announcement_date", "")),
            str(exchange.get("announcement_date", "")),
        )
        available_at = max(
            str(company.get("available_at", "")),
            str(exchange.get("available_at", "")),
        )
        output = {
            "concept_id": concept_id,
            "concept_version": str(company.get("concept_version", "1")),
            "symbol": str(company["symbol"]),
            "value": value,
            "unit": str(company["unit"]),
            "context_id": str(company["context_id"]),
            "is_derived": True,
            "derived_from": ",".join(input_ids),
            "derivation_definition_id": "official_dual_source_reconciliation",
            "derivation_version": self.rule_version,
            "input_fact_ids": ",".join(input_ids),
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
            "restatement_version": str(company.get("restatement_version", "original")),
            "supersedes_fact_id": "",
            "fiscal_year": int(company.get("fiscal_year", 0) or 0),
            "report_type": str(company.get("report_type", "annual")),
            "period_start": str(company.get("period_start", "")),
            "period_end": str(company.get("period_end", "")),
            "filing_date": announcement_date,
            "announcement_date": announcement_date,
            "available_at": available_at,
            "raw_value": value,
            "raw_unit": str(company["unit"]),
            "normalized_value": value,
            "normalization_rule": "identity",
            "verification_status": "reconciled",
            "verification_note": "cross-verified company_official + exchange_official",
            "eligible_for_metrics": True,
            "created_at": now,
            "event_id": event_id,
        }
        output["fact_id"] = build_fact_id(output)
        return output
