"""Declarative Rule007 source-pair contract.

Only issuer_official + exchange_official is a Rule007 metric pair.  A
designated disclosure platform is supplemental evidence context, never the
exchange side.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from typing import Any

RULE007_SOURCE_PAIR_CONTRACT_V4 = "rule007_source_pair_contract_v4"
# Keep the old import name available to callers that only use the registry
# constant.  The serialized contract is the v4 contract above.
RULE007_SOURCE_PAIR_CONTRACT_V3 = RULE007_SOURCE_PAIR_CONTRACT_V4
_SOURCE_TYPES = (
    "issuer_official",
    "exchange_official",
    "designated_disclosure_platform",
)
_OFFICIAL_SOURCE_TYPES = {"issuer_official", "exchange_official"}
_REQUIRED_EXTRACTED_KEYS = {
    "cash_dividend_total",
    "cash_dividend_per_share",
    "share_capital",
    "currency",
    "share_scope",
}
RULE007_PAIR_REGISTRY: dict[str, dict[str, Any]] = {
    "issuer_exchange_rule007_eligible": {
        "source_types": ["issuer_official", "exchange_official"],
        "rule007_eligible": True,
        "supports_metric_input": True,
        "required_independent_extraction": True,
        "same_content_mirror": "recorded_but_not_independent",
        "warning": None,
        "supplemental_source_types": ["designated_disclosure_platform"],
    },
    "issuer_plus_designated_platform_verified": {
        "source_types": ["issuer_official", "designated_disclosure_platform"],
        "rule007_eligible": False,
        "supports_metric_input": False,
        "required_independent_extraction": True,
        "same_content_mirror": "recorded_but_not_independent",
        "warning": "designated_disclosure_platform_is_not_exchange_official",
        "supplemental_source_types": [],
    },
    "exchange_plus_designated_platform_verified": {
        "source_types": ["exchange_official", "designated_disclosure_platform"],
        "rule007_eligible": False,
        "supports_metric_input": False,
        "required_independent_extraction": True,
        "same_content_mirror": "recorded_but_not_independent",
        "warning": "designated_disclosure_platform_is_not_exchange_official",
        "supplemental_source_types": [],
    },
    "designated_platform_only": {
        "source_types": ["designated_disclosure_platform"],
        "rule007_eligible": False,
        "supports_metric_input": False,
        "required_independent_extraction": False,
        "same_content_mirror": "not_applicable",
        "warning": "designated_platform_only",
        "supplemental_source_types": [],
    },
    "issuer_only": {
        "source_types": ["issuer_official"],
        "rule007_eligible": False,
        "supports_metric_input": False,
        "required_independent_extraction": False,
        "same_content_mirror": "not_applicable",
        "warning": "missing_exchange_official",
        "supplemental_source_types": [],
    },
    "exchange_only": {
        "source_types": ["exchange_official"],
        "rule007_eligible": False,
        "supports_metric_input": False,
        "required_independent_extraction": False,
        "same_content_mirror": "not_applicable",
        "warning": "missing_issuer_official",
        "supplemental_source_types": [],
    },
    "no_retrieved_official_source": {
        "source_types": [],
        "rule007_eligible": False,
        "supports_metric_input": False,
        "required_independent_extraction": False,
        "same_content_mirror": "not_applicable",
        "warning": "no_retrieved_or_verified_official_source",
        "supplemental_source_types": [],
    },
    "conflicting_official_sources": {
        "source_types": ["issuer_official", "exchange_official"],
        "rule007_eligible": False,
        "supports_metric_input": False,
        "required_independent_extraction": True,
        "same_content_mirror": "not_applicable",
        "warning": "conflicting_official_source_candidates",
        "supplemental_source_types": [],
    },
    "incomplete_or_invalid_evidence": {
        "source_types": [],
        "rule007_eligible": False,
        "supports_metric_input": False,
        "required_independent_extraction": False,
        "same_content_mirror": "not_applicable",
        "warning": "incomplete_or_invalid_evidence",
        "supplemental_source_types": [],
    },
}


def _candidate_key(source: Mapping[str, Any]) -> tuple[str, str, str]:
    return (
        str(source.get("announcement_date", "")),
        str(source.get("announcement_id", "")),
        str(source.get("source_evidence_id", "")),
    )


def _candidate_fingerprint(source: Mapping[str, Any]) -> str:
    payload = {
        "content_sha256": source.get("content_sha256"),
        "extracted_values": source.get("extracted_values"),
        "currency": source.get("extracted_values", {}).get("currency")
        if isinstance(source.get("extracted_values"), Mapping)
        else None,
        "share_scope": source.get("extracted_values", {}).get("share_scope")
        if isinstance(source.get("extracted_values"), Mapping)
        else None,
    }
    return hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _is_verified_source(source: Mapping[str, Any]) -> bool:
    extracted = source.get("extracted_values")
    return bool(
        source.get("retrieval_status") == "retrieved"
        and source.get("content_sha256")
        and source.get("independently_extracted")
        and isinstance(extracted, Mapping)
        and _REQUIRED_EXTRACTED_KEYS.issubset(extracted)
    )


def _has_malformed_evidence(source: Mapping[str, Any]) -> bool:
    source_type = source.get("source_type")
    if not source.get("source_evidence_id") or source_type not in _SOURCE_TYPES:
        return True
    # An unavailable official endpoint is an explicit evidence gap, not an
    # invalid record.  A record claiming retrieval but missing its verified
    # payload is incomplete/invalid evidence.
    if source.get("retrieval_status") == "retrieved":
        extracted = source.get("extracted_values")
        return not (
            source.get("content_sha256")
            and source.get("independently_extracted")
            and isinstance(extracted, Mapping)
            and _REQUIRED_EXTRACTED_KEYS.issubset(extracted)
        )
    return False


def _normalised_value(value: Any) -> Any:
    if value is None:
        return None
    try:
        from decimal import Decimal

        return Decimal(str(value))
    except (ArithmeticError, TypeError, ValueError):
        return str(value)


def _official_values_conflict(
    issuer: Mapping[str, Any], exchange: Mapping[str, Any]
) -> bool:
    issuer_values = issuer.get("extracted_values")
    exchange_values = exchange.get("extracted_values")
    if not isinstance(issuer_values, Mapping) or not isinstance(exchange_values, Mapping):
        return True
    for key in _REQUIRED_EXTRACTED_KEYS:
        if key not in issuer_values or key not in exchange_values:
            return True
        if key in {"currency", "share_scope", "share_capital"}:
            if str(issuer_values[key]) != str(exchange_values[key]):
                return True
        elif _normalised_value(issuer_values[key]) != _normalised_value(exchange_values[key]):
            return True
    return False


def select_rule007_sources(
    linked_sources: list[dict[str, Any]],
) -> tuple[dict[str, Any], list[str]]:
    """Select candidates deterministically and return pair state/errors.

    Every real candidate is considered.  Equal-content duplicate candidates are
    ordered deterministically; contradictory candidates are a hard error.
    """

    errors: list[str] = []
    malformed = any(
        not isinstance(source, Mapping) or _has_malformed_evidence(source)
        for source in linked_sources
    )
    real = [
        source
        for source in linked_sources
        if isinstance(source, Mapping) and _is_verified_source(source)
    ]
    groups = {
        source_type: sorted(
            [source for source in real if source.get("source_type") == source_type],
            key=_candidate_key,
        )
        for source_type in (
            "issuer_official",
            "exchange_official",
            "designated_disclosure_platform",
        )
    }
    selected: dict[str, dict[str, Any] | None] = {}
    for source_type, candidates in groups.items():
        if len({_candidate_fingerprint(item) for item in candidates}) > 1:
            if source_type in _OFFICIAL_SOURCE_TYPES:
                errors.append(f"contradictory_{source_type}_candidates")
            selected[source_type] = None
        else:
            selected[source_type] = candidates[0] if candidates else None

    issuer = selected["issuer_official"]
    exchange = selected["exchange_official"]
    designated = selected["designated_disclosure_platform"]
    official_conflict = any(
        error.startswith("contradictory_issuer_official")
        or error.startswith("contradictory_exchange_official")
        for error in errors
    )
    if issuer and exchange and _official_values_conflict(issuer, exchange):
        errors.append("conflicting_official_source_values")
        official_conflict = True
    if official_conflict:
        status = "conflicting_official_sources"
    elif issuer and exchange:
        status = "issuer_exchange_rule007_eligible"
    elif issuer and designated:
        status = "issuer_plus_designated_platform_verified"
    elif exchange and designated:
        status = "exchange_plus_designated_platform_verified"
    elif designated:
        status = "designated_platform_only"
    elif issuer:
        status = "issuer_only"
    elif exchange:
        status = "exchange_only"
    elif malformed:
        status = "incomplete_or_invalid_evidence"
    else:
        status = "no_retrieved_official_source"
    contract = RULE007_PAIR_REGISTRY[status]
    candidates = []
    for source_type in groups:
        for source in groups[source_type]:
            selected_source = selected[source_type]
            candidates.append(
                {
                    "source_evidence_id": source["source_evidence_id"],
                    "source_type": source_type,
                    "selected": bool(selected_source and selected_source is source),
                    "reason": (
                        "selected_deterministically"
                        if selected_source is source
                        else "duplicate_or_rejected_candidate"
                    ),
                }
            )
    return (
        {
            "status": status,
            "contract": RULE007_SOURCE_PAIR_CONTRACT_V4,
            "rule007_eligible": bool(contract["rule007_eligible"] and not errors),
            "supports_metric_input": bool(contract["supports_metric_input"] and not errors),
            "selected": {
                "issuer_official": issuer,
                "exchange_official": exchange,
                "designated_disclosure_platform": designated,
            },
            "candidates": candidates,
            "warning": contract["warning"],
            "supplemental_sources": (
                [designated]
                if status == "issuer_exchange_rule007_eligible" and designated
                else []
            ),
            "errors": errors,
        },
        errors,
    )
