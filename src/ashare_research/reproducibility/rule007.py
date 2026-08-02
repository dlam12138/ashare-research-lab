"""Declarative Rule007 source-pair contract.

Only issuer_official + exchange_official is a Rule007 metric pair.  A
designated disclosure platform is evidence context, never the exchange side.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from typing import Any

RULE007_SOURCE_PAIR_CONTRACT_V3 = "rule007_source_pair_contract_v3"
RULE007_PAIR_REGISTRY: dict[str, dict[str, Any]] = {
    "issuer_exchange_rule007_eligible": {
        "source_types": ["issuer_official", "exchange_official"],
        "rule007_eligible": True,
        "supports_metric_input": True,
        "required_independent_extraction": True,
        "same_content_mirror": "recorded_but_not_independent",
        "warning": None,
    },
    "issuer_plus_designated_platform_verified": {
        "source_types": ["issuer_official", "designated_disclosure_platform"],
        "rule007_eligible": False,
        "supports_metric_input": False,
        "required_independent_extraction": True,
        "same_content_mirror": "recorded_but_not_independent",
        "warning": "designated_disclosure_platform_is_not_exchange_official",
    },
    "exchange_plus_designated_platform_verified": {
        "source_types": ["exchange_official", "designated_disclosure_platform"],
        "rule007_eligible": False,
        "supports_metric_input": False,
        "required_independent_extraction": True,
        "same_content_mirror": "recorded_but_not_independent",
        "warning": "designated_disclosure_platform_is_not_exchange_official",
    },
    "designated_platform_only": {
        "source_types": ["designated_disclosure_platform"],
        "rule007_eligible": False,
        "supports_metric_input": False,
        "required_independent_extraction": False,
        "same_content_mirror": "not_applicable",
        "warning": "designated_platform_only",
    },
    "issuer_only": {
        "source_types": ["issuer_official"],
        "rule007_eligible": False,
        "supports_metric_input": False,
        "required_independent_extraction": False,
        "same_content_mirror": "not_applicable",
        "warning": "missing_exchange_official",
    },
    "exchange_only": {
        "source_types": ["exchange_official"],
        "rule007_eligible": False,
        "supports_metric_input": False,
        "required_independent_extraction": False,
        "same_content_mirror": "not_applicable",
        "warning": "missing_issuer_official",
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


def select_rule007_sources(
    linked_sources: list[dict[str, Any]],
) -> tuple[dict[str, Any], list[str]]:
    """Select candidates deterministically and return pair state/errors.

    Every real candidate is considered.  Equal-content duplicate candidates are
    ordered deterministically; contradictory candidates are a hard error.
    """

    errors: list[str] = []
    real = [
        source
        for source in linked_sources
        if source.get("retrieval_status") == "retrieved"
        and source.get("content_sha256")
        and source.get("independently_extracted")
        and isinstance(source.get("extracted_values"), Mapping)
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
            errors.append(f"contradictory_{source_type}_candidates")
            selected[source_type] = None
        else:
            selected[source_type] = candidates[0] if candidates else None

    issuer = selected["issuer_official"]
    exchange = selected["exchange_official"]
    designated = selected["designated_disclosure_platform"]
    if issuer and exchange:
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
    else:
        status = "issuer_only"
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
            "contract": RULE007_SOURCE_PAIR_CONTRACT_V3,
            "rule007_eligible": bool(contract["rule007_eligible"] and not errors),
            "supports_metric_input": bool(contract["supports_metric_input"] and not errors),
            "selected": {
                "issuer_official": issuer,
                "exchange_official": exchange,
                "designated_disclosure_platform": designated,
            },
            "candidates": candidates,
            "warning": contract["warning"],
            "errors": errors,
        },
        errors,
    )
