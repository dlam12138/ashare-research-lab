"""Document-scope contract for supplemental earnings-quality evidence.

The stable official source identity belongs to the issuer/year/source tier.
Each fact separately identifies the formal document that directly carries it.
"""

from __future__ import annotations

import copy
from typing import Any

CONTRACT = "earnings_quality_official_facts_v1"
EXPECTED_CONCEPTS = frozenset(
    {
        "net_profit_excluding_non_recurring",
        "operating_cost",
        "operating_profit",
    }
)
ALLOWED_DOCUMENT_SCOPES = frozenset(
    {
        "full_annual_report",
        "audited_financial_statements",
        "annual_results_announcement",
        "annual_report_summary",
    }
)
ADJUSTED_PROFIT_SCOPES = frozenset(
    {
        "full_annual_report",
        "annual_results_announcement",
        "annual_report_summary",
    }
)
STATEMENT_CONCEPT_SCOPES = frozenset(
    {"full_annual_report", "audited_financial_statements"}
)
EVIDENCE_SCOPES = frozenset(
    {
        "audited_statement_line_item",
        "full_annual_report_direct_disclosure",
        "annual_results_announcement_direct_disclosure",
    }
)


class EarningsQualityDocumentContractError(ValueError):
    """A supplemental evidence document or fact binding is invalid."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise EarningsQualityDocumentContractError(message)


def _source_url(document: dict[str, Any]) -> str:
    return str(
        document.get("final_pdf_url")
        or document.get("pdf_url")
        or document.get("source_url")
        or ""
    )


def _normalize_document(
    document: dict[str, Any],
    *,
    source_key: str,
    document_key: str,
) -> dict[str, Any]:
    normalized = copy.deepcopy(document)
    normalized["document_key"] = document_key
    normalized["source_key"] = source_key
    normalized["document_scope"] = str(
        normalized.get("document_scope") or "full_annual_report"
    )
    normalized["source_url"] = _source_url(normalized)
    normalized["source_hash"] = str(
        normalized.get("source_hash") or normalized.get("sha256") or ""
    )
    return normalized


def normalize_earnings_quality_evidence(
    evidence: dict[str, Any],
    base_bundle: dict[str, Any],
) -> dict[str, Any]:
    """Return normalized evidence with an explicit per-fact document registry.

    The frozen 2025 evidence predates per-fact bindings. It is normalized from
    the bound annual bundle without changing that committed evidence file.
    """

    normalized = copy.deepcopy(evidence)
    documents = normalized.get("documents")
    if not isinstance(documents, dict):
        documents = {}
        for source_key in ("company", "exchange"):
            document_key = f"{source_key}_full_annual_report"
            documents[document_key] = _normalize_document(
                base_bundle["documents"][source_key],
                source_key=source_key,
                document_key=document_key,
            )
        normalized["documents"] = documents
    else:
        normalized["documents"] = {
            key: _normalize_document(
                value,
                source_key=str(value.get("source_key", "")),
                document_key=key,
            )
            for key, value in documents.items()
        }

    normalized.setdefault("independent_content_sources", False)
    for source_key in ("company", "exchange"):
        source = normalized["sources"][source_key]
        default_key = f"{source_key}_full_annual_report"
        for fact in source["facts"]:
            document_key = str(fact.get("document_key") or default_key)
            document = normalized["documents"][document_key]
            fact["document_key"] = document_key
            fact.setdefault("source_document", str(document["source_document"]))
            fact.setdefault("document_scope", str(document["document_scope"]))
            fact.setdefault("source_url", str(document["source_url"]))
            fact.setdefault("source_hash", str(document["source_hash"]))
            fact.setdefault("pdf_page", _parse_page(fact["source_page"], "PDF page"))
            fact.setdefault(
                "printed_page",
                _parse_page(fact["source_page"], "printed page"),
            )
            fact.setdefault("official_direct_disclosure", True)
            fact.setdefault(
                "evidence_scope",
                (
                    "audited_statement_line_item"
                    if fact["concept_id"] in {"operating_cost", "operating_profit"}
                    else "full_annual_report_direct_disclosure"
                ),
            )
    return normalized


def _parse_page(value: str, prefix: str) -> int:
    for part in value.split("/"):
        text = part.strip()
        if text.startswith(prefix):
            return int(text.removeprefix(prefix).strip())
    raise EarningsQualityDocumentContractError(
        f"source_page does not contain {prefix}: {value}"
    )


def _validate_formal_annual_disclosure(
    document: dict[str, Any],
    *,
    symbol: str,
    fiscal_year: int,
) -> None:
    scope = document["document_scope"]
    if scope not in {"annual_results_announcement", "annual_report_summary"}:
        return
    required = {
        "issuer": "中国石油天然气股份有限公司",
        "stock_code": symbol.split(".", maxsplit=1)[0],
        "fiscal_year": fiscal_year,
        "formal_annual_disclosure": True,
        "direct_financial_data_disclosure": True,
    }
    for field, expected in required.items():
        _require(
            document.get(field) == expected,
            f"{document['document_key']}: {field} differs",
        )
    _require(
        "新闻稿" not in str(document["source_document"]),
        f"{document['document_key']}: ordinary news release is not accepted",
    )


def validate_earnings_quality_document_contract(
    evidence: dict[str, Any],
    base_bundle: dict[str, Any],
) -> dict[str, Any]:
    """Normalize and strictly validate supplemental evidence document binding."""

    normalized = normalize_earnings_quality_evidence(evidence, base_bundle)
    _require(normalized.get("contract") == CONTRACT, "evidence contract differs")
    _require(
        normalized.get("independent_content_sources") is False,
        "official publication paths are not independent content sources",
    )
    _require(
        set(normalized.get("sources", {})) == {"company", "exchange"},
        "exactly company and exchange sources are required",
    )
    documents = normalized.get("documents", {})
    _require(bool(documents), "document registry is required")
    stable_source_ids = {
        source_key: base_bundle["documents"][source_key]["source_id"]
        for source_key in ("company", "exchange")
    }
    for document_key, document in documents.items():
        source_key = document.get("source_key")
        _require(source_key in stable_source_ids, f"{document_key}: source differs")
        _require(
            document.get("source_tier") == f"{source_key}_official",
            f"{document_key}: source tier differs",
        )
        _require(
            document.get("source_id") == stable_source_ids[source_key],
            f"{document_key}: stable source identity differs",
        )
        _require(
            document.get("document_scope") in ALLOWED_DOCUMENT_SCOPES,
            f"{document_key}: document scope is not accepted",
        )
        for field in (
            "source_document",
            "source_url",
            "source_hash",
            "announcement_date",
        ):
            _require(bool(document.get(field)), f"{document_key}: {field} is required")
        _validate_formal_annual_disclosure(
            document,
            symbol=str(normalized["symbol"]),
            fiscal_year=int(normalized["fiscal_year"]),
        )

    for source_key, source in normalized["sources"].items():
        facts = source.get("facts", [])
        _require(
            {fact.get("concept_id") for fact in facts} == EXPECTED_CONCEPTS
            and len(facts) == len(EXPECTED_CONCEPTS),
            f"{source_key}: exactly three distinct concepts are required",
        )
        for fact in facts:
            concept_id = fact["concept_id"]
            document_key = fact.get("document_key")
            _require(
                document_key in documents,
                f"{source_key}/{concept_id}: document_key is not registered",
            )
            document = documents[document_key]
            _require(
                document["source_key"] == source_key,
                f"{source_key}/{concept_id}: document belongs to another source",
            )
            for fact_field, document_field in (
                ("source_document", "source_document"),
                ("document_scope", "document_scope"),
                ("source_url", "source_url"),
                ("source_hash", "source_hash"),
            ):
                _require(
                    fact.get(fact_field) == document.get(document_field),
                    f"{source_key}/{concept_id}: {fact_field} binding differs",
                )
            for field in (
                "source_page",
                "pdf_page",
                "printed_page",
                "source_table",
                "source_label",
            ):
                _require(
                    fact.get(field) not in (None, ""),
                    f"{source_key}/{concept_id}: {field} is required",
                )
            _require(
                fact.get("official_direct_disclosure") is True,
                f"{source_key}/{concept_id}: direct official disclosure is required",
            )
            _require(
                fact.get("evidence_scope") in EVIDENCE_SCOPES,
                f"{source_key}/{concept_id}: evidence_scope differs",
            )
            allowed_scopes = (
                ADJUSTED_PROFIT_SCOPES
                if concept_id == "net_profit_excluding_non_recurring"
                else STATEMENT_CONCEPT_SCOPES
            )
            _require(
                document["document_scope"] in allowed_scopes,
                f"{source_key}/{concept_id}: document scope cannot carry concept",
            )
            if concept_id in {"operating_cost", "operating_profit"}:
                _require(
                    fact["evidence_scope"] == "audited_statement_line_item",
                    f"{source_key}/{concept_id}: audited statement line is required",
                )
            if document["document_scope"] == "annual_results_announcement":
                _require(
                    fact["evidence_scope"]
                    == "annual_results_announcement_direct_disclosure",
                    f"{source_key}/{concept_id}: announcement scope is mislabeled",
                )
    return normalized
