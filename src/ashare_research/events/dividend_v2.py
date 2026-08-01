"""Corrected dividend event contract used by the Stage 2G valuation layer.

The v1 event ledger is historical evidence and remains intentionally unchanged.
This module makes the announcement/payment distinction explicit and keeps
source identity separate from retrieval metadata.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from datetime import date
from typing import Any

DIVIDEND_EVENT_V2_CONTRACT = "dividend_event_record_v2"
DIVIDEND_EVENT_V2_VERSION = "2"
DIVIDEND_EVENT_V2_STAGES = (
    "proposal",
    "approval_or_authorization",
    "implementation_announced",
    "payment_completed",
)


def build_dividend_event_v2_id(
    symbol: str, source_fiscal_year: int, event_type: str, version: str = "2"
) -> str:
    """Return a stable ID for one corrected event record version."""

    payload = "|".join(
        (DIVIDEND_EVENT_V2_CONTRACT, symbol, str(source_fiscal_year), event_type, version)
    )
    return "dve2_" + hashlib.sha256(payload.encode("utf-8")).hexdigest()[:24]


def _as_date(value: Any) -> date | None:
    if value in (None, ""):
        return None
    return date.fromisoformat(str(value))


def event_status_as_of(event: Mapping[str, Any], as_of: str | date) -> str:
    """Return the only stage visible at a point in time.

    A publication of the implementation notice is not payment.  The function
    deliberately has no ``implemented`` state.
    """

    point = as_of if isinstance(as_of, date) else date.fromisoformat(as_of)
    proposal = _as_date(event.get("proposal_date"))
    approval = _as_date(event.get("approval_or_authorization_date"))
    implementation = _as_date(event.get("implementation_available_at"))
    payment = _as_date(event.get("payment_date"))
    if payment and point >= payment:
        return "payment_completed"
    if implementation and point >= implementation:
        return "implementation_announced"
    if approval and point >= approval:
        return "approval_or_authorization"
    if proposal and point >= proposal:
        return "proposal"
    return "not_yet_visible"


def validate_dividend_event_v2(event: Mapping[str, Any]) -> list[str]:
    """Validate identity, chronology, source scope, and stage semantics."""

    errors: list[str] = []
    required = (
        "event_id",
        "version",
        "supersedes_event_id",
        "source_fiscal_year",
        "event_type",
        "proposal_date",
        "approval_or_authorization_date",
        "approval_type",
        "implementation_available_at",
        "payment_date",
        "source_evidence_ids",
    )
    for field in required:
        if field not in event:
            errors.append(f"missing:{field}")
    if errors:
        return errors
    if event["version"] != 2:
        errors.append("version_must_be_2")
    expected = build_dividend_event_v2_id(
        "601857.SH", int(event["source_fiscal_year"]), str(event["event_type"])
    )
    if event["event_id"] != expected:
        errors.append("event_id_not_canonical")
    if event.get("approval_type") not in {
        "shareholder_approval",
        "prior_shareholder_authorization",
    }:
        errors.append("invalid_approval_type")
    proposal = _as_date(event.get("proposal_date"))
    approval = _as_date(event.get("approval_or_authorization_date"))
    implementation = _as_date(event.get("implementation_available_at"))
    payment = _as_date(event.get("payment_date"))
    chronology = [proposal, approval, implementation, payment]
    if any(value is None for value in chronology):
        errors.append("incomplete_chronology")
    elif event.get("approval_type") == "prior_shareholder_authorization":
        if not (approval < proposal <= implementation <= payment):
            errors.append("prior_authorization_chronology_not_monotonic")
    elif not (proposal <= approval <= implementation <= payment):
        errors.append("chronology_not_monotonic")
    if (
        event.get("approval_type") == "prior_shareholder_authorization"
        and event.get("prior_authorization_is_event_specific") is not False
    ):
        errors.append("prior_authorization_flag_missing")
    if event.get("event_stage") in {"implemented", "paid/implemented", "paid"}:
        errors.append("ambiguous_or_legacy_stage")
    if event.get("event_stage") not in DIVIDEND_EVENT_V2_STAGES:
        errors.append("invalid_event_stage")
    if (
        event.get("currency") != "CNY"
        or event.get("share_scope") != "A_ordinary_share_entitlement_with_H_share_same_DPS"
    ):
        errors.append("currency_or_share_scope_not_explicit")
    if not event.get("source_evidence_ids"):
        errors.append("no_source_evidence")
    return errors


def validate_source_evidence(entry: Mapping[str, Any]) -> list[str]:
    """Reject generic locators and URL hashes masquerading as content hashes."""

    errors: list[str] = []
    required = (
        "source_type",
        "source_id",
        "announcement_id",
        "title",
        "announcement_date",
        "exact_url",
        "locator_hash",
        "content_sha256",
        "retrieval_status",
    )
    for field in required:
        if field not in entry:
            errors.append(f"missing:{field}")
    if errors:
        return errors
    if entry["source_type"] not in {
        "issuer_official",
        "exchange_official",
        "designated_disclosure_platform",
        "other_official",
    }:
        errors.append("unknown_source_type")
    url = str(entry["exact_url"])
    if "sse.com.cn" in url and (
        "/announcement/c/new/" not in url or not url.lower().endswith(".pdf")
    ):
        errors.append("generic_exchange_url")
    expected_locator = hashlib.sha256(url.encode("utf-8")).hexdigest()
    if entry["locator_hash"] != expected_locator:
        errors.append("locator_hash_mismatch")
    content = entry.get("content_sha256")
    if content is not None:
        if len(str(content)) != 64 or any(c not in "0123456789abcdef" for c in str(content)):
            errors.append("content_hash_not_sha256")
        if content == entry["locator_hash"]:
            errors.append("url_hash_used_as_content_hash")
    if entry["source_type"] == "issuer_official" and "cninfo" in url.lower():
        errors.append("designated_platform_mislabelled_issuer_official")
    return errors


def stable_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
