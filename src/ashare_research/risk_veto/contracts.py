"""Versioned evidence, event, search and veto-observation contracts.

The module is intentionally deterministic.  It classifies only explicit,
structured inputs and never turns a missing search result into a negative
conclusion.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections import defaultdict
from datetime import date
from typing import Any

METHODOLOGY_VERSION = "risk_veto_methodology_v1"
CODE_VERSION = "stage2h_risk_veto_v1"
EVIDENCE_CONTRACT = "risk_evidence_record_v1"
EVENT_CONTRACT = "risk_event_record_v1"
OBSERVATION_CONTRACT = "risk_veto_observation_v1"
SEARCH_CONTRACT = "bounded_search_register_v1"

STATUS_VOCABULARY = (
    "observed",
    "not_observed_within_bounded_evidence",
    "not_evaluated",
    "missing_evidence",
)

TRUE_SOURCE_TYPES = {
    "issuer_official",
    "exchange_official",
    "regulator_official",
    "designated_disclosure_platform",
    "audit_report_official_attachment",
    "other_official",
}

RISK_IDS = (
    "modified_audit_opinion",
    "going_concern_material_uncertainty",
    "formal_regulatory_investigation_or_major_discipline",
    "material_error_restatement",
    "controlling_shareholder_pledge_risk",
    "material_related_party_transaction_risk",
    "controlling_shareholder_fund_occupation_or_related_guarantee",
    "repeated_equity_financing_or_material_dilution",
)

TRIGGER_RULES: dict[str, dict[str, Any]] = {
    "modified_audit_opinion": {
        "version": "modified_audit_opinion_v1",
        "trigger": "opinion_type in {qualified, adverse, disclaimer}",
    },
    "going_concern_material_uncertainty": {
        "version": "going_concern_material_uncertainty_v1",
        "trigger": "explicit_material_uncertainty == true",
    },
    "formal_regulatory_investigation_or_major_discipline": {
        "version": "formal_regulatory_investigation_or_major_discipline_v1",
        "trigger": "formal_investigation or major_discipline only",
    },
    "material_error_restatement": {
        "version": "material_error_restatement_v1",
        "trigger": "restatement_classification == prior_period_error_or_misstatement",
    },
    "controlling_shareholder_pledge_risk": {
        "version": "controlling_shareholder_pledge_risk_v1",
        "trigger": "direct_controller_pledge_ratio >= 0.20 or pledged_total_share_ratio >= 0.10",
        "thresholds": {"direct_controller_pledge_ratio": 0.20, "total_share_ratio": 0.10},
    },
    "material_related_party_transaction_risk": {
        "version": "material_related_party_transaction_risk_v1",
        "trigger": "non_market or approval_cap_breach or material_non_operating_finance",
    },
    "controlling_shareholder_fund_occupation_or_related_guarantee": {
        "version": "fund_occupation_or_related_guarantee_v1",
        "trigger": "fund_occupation or illegal_related_guarantee",
    },
    "repeated_equity_financing_or_material_dilution": {
        "version": "repeated_equity_financing_or_material_dilution_v1",
        "trigger": "completed_financing and realized_dilution_share_delta > 0",
    },
}

_HEX64 = re.compile(r"^[0-9a-f]{64}$")


class RiskVetoContractError(ValueError):
    """Raised when a Stage 2H contract is incomplete or non-deterministic."""


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def stable_id(prefix: str, value: Any) -> str:
    """Return a content-addressed ID without machine-specific paths."""

    return f"{prefix}_{hashlib.sha256(_canonical(value).encode('utf-8')).hexdigest()[:24]}"


def _require(record: dict[str, Any], fields: tuple[str, ...], label: str) -> None:
    missing = [field for field in fields if field not in record]
    if missing:
        raise RiskVetoContractError(f"{label} missing required fields: {', '.join(missing)}")


def _date_like(value: Any, field: str) -> None:
    if not isinstance(value, str) or not value:
        raise RiskVetoContractError(f"{field} must be a non-empty ISO date or timestamp")
    try:
        date.fromisoformat(value[:10])
    except ValueError as exc:
        raise RiskVetoContractError(f"{field} is not ISO date-like: {value}") from exc


def validate_evidence_record(record: dict[str, Any]) -> None:
    _require(
        record,
        (
            "contract",
            "source_evidence_id",
            "source_type",
            "source_id",
            "title",
            "announcement_date",
            "exact_url",
            "announcement_id",
            "locator_sha256",
            "content_sha256",
            "byte_size",
            "page_count",
            "retrieved_at",
            "available_at",
            "source_page",
            "source_section",
            "extraction_method",
            "status",
            "fields",
            "warnings",
            "logical_cache_object_key",
        ),
        "evidence record",
    )
    if record["contract"] != EVIDENCE_CONTRACT:
        raise RiskVetoContractError("unsupported evidence contract")
    if record["source_type"] not in TRUE_SOURCE_TYPES:
        raise RiskVetoContractError(f"untrusted source type: {record['source_type']}")
    _date_like(record["announcement_date"], "announcement_date")
    _date_like(record["retrieved_at"], "retrieved_at")
    _date_like(record["available_at"], "available_at")
    if not isinstance(record["exact_url"], str) or not record["exact_url"].startswith("https://"):
        raise RiskVetoContractError("exact_url must be an official HTTPS locator")
    if record["locator_sha256"] != hashlib.sha256(record["exact_url"].encode()).hexdigest():
        raise RiskVetoContractError(f"locator hash mismatch: {record['source_evidence_id']}")
    if not _HEX64.fullmatch(str(record["content_sha256"])):
        raise RiskVetoContractError(
            f"real content SHA-256 required: {record['source_evidence_id']}"
        )
    if not isinstance(record["byte_size"], int) or record["byte_size"] <= 0:
        raise RiskVetoContractError("evidence byte_size must be positive")
    if not isinstance(record["page_count"], int) or record["page_count"] <= 0:
        raise RiskVetoContractError("evidence page_count must be positive")
    object_key = str(record["logical_cache_object_key"])
    if (
        not object_key
        or object_key.startswith(("/", "~"))
        or ":" in object_key[:3]
        or ".." in object_key
    ):
        raise RiskVetoContractError("logical cache object key must be relative")
    if object_key != f"{record['content_sha256']}.pdf":
        raise RiskVetoContractError("cache key must be content-addressed")
    if record["status"] not in {"retrieved", "missing_evidence"}:
        raise RiskVetoContractError("unsupported evidence status")
    if not isinstance(record["warnings"], list) or not isinstance(record["fields"], dict):
        raise RiskVetoContractError("evidence fields/warnings have wrong type")


def validate_search_register(record: dict[str, Any]) -> None:
    _require(
        record,
        (
            "contract",
            "search_register_id",
            "risk_id",
            "systems",
            "date_range",
            "search_terms",
            "identifiers",
            "query_time",
            "result_count",
            "retrieved_count",
            "rejected_candidates",
            "anti_bot_gaps",
            "network_gaps",
            "completeness",
            "completeness_basis",
        ),
        "search register",
    )
    if record["contract"] != SEARCH_CONTRACT or record["risk_id"] not in RISK_IDS:
        raise RiskVetoContractError("invalid search register identity")
    if not isinstance(record["systems"], list) or not record["systems"]:
        raise RiskVetoContractError("bounded search systems are required")
    if not isinstance(record["date_range"], dict) or not {"start", "end"} <= set(
        record["date_range"]
    ):
        raise RiskVetoContractError("bounded search date range is required")
    _date_like(record["date_range"]["start"], "date_range.start")
    _date_like(record["date_range"]["end"], "date_range.end")
    _date_like(record["query_time"], "query_time")
    for field in ("result_count", "retrieved_count"):
        if not isinstance(record[field], int) or record[field] < 0:
            raise RiskVetoContractError(f"{field} must be a non-negative integer")
    if not isinstance(record["rejected_candidates"], list):
        raise RiskVetoContractError("rejected candidates must be a list")
    if not isinstance(record["completeness"], bool) or not record["completeness_basis"]:
        raise RiskVetoContractError("search completeness must be explicit")


def validate_event_record(record: dict[str, Any]) -> None:
    _require(
        record,
        (
            "contract",
            "event_id",
            "symbol",
            "risk_id",
            "event_type",
            "event_date",
            "available_at",
            "period",
            "evidence_ids",
            "source_types",
            "extraction_method",
            "classification",
            "trigger_version",
            "inputs",
            "status",
            "missing_reasons",
            "warnings",
            "supersedes",
            "code_version",
            "score_eligible",
        ),
        "event record",
    )
    if record["contract"] != EVENT_CONTRACT or record["risk_id"] not in RISK_IDS:
        raise RiskVetoContractError("invalid event identity")
    _date_like(record["event_date"], "event_date")
    _date_like(record["available_at"], "available_at")
    if record["status"] not in STATUS_VOCABULARY:
        raise RiskVetoContractError("invalid event status")
    if record["score_eligible"] is not False:
        raise RiskVetoContractError("Stage 2H events are not score eligible")
    if not isinstance(record["evidence_ids"], list) or not isinstance(record["source_types"], list):
        raise RiskVetoContractError("event evidence/source types must be lists")
    if any(source not in TRUE_SOURCE_TYPES for source in record["source_types"]):
        raise RiskVetoContractError("event contains an untrusted source type")
    expected = stable_id(
        "risk_event",
        {
            key: record[key]
            for key in (
                "symbol",
                "risk_id",
                "event_type",
                "event_date",
                "available_at",
                "period",
                "evidence_ids",
                "classification",
                "trigger_version",
                "inputs",
                "status",
                "supersedes",
            )
        },
    )
    if record["event_id"] != expected:
        raise RiskVetoContractError(f"event deterministic ID mismatch: {record['event_id']}")


def _triggered(risk_id: str, inputs: dict[str, Any]) -> bool:
    if risk_id == "modified_audit_opinion":
        return inputs.get("opinion_type") in {"qualified", "adverse", "disclaimer"}
    if risk_id == "going_concern_material_uncertainty":
        return inputs.get("explicit_material_uncertainty") is True
    if risk_id == "formal_regulatory_investigation_or_major_discipline":
        return inputs.get("formal_investigation") is True or inputs.get("major_discipline") is True
    if risk_id == "material_error_restatement":
        return inputs.get("restatement_classification") == "prior_period_error_or_misstatement"
    if risk_id == "controlling_shareholder_pledge_risk":
        return (
            float(inputs.get("direct_controller_pledge_ratio", 0))
            >= TRIGGER_RULES[risk_id]["thresholds"]["direct_controller_pledge_ratio"]
            or float(inputs.get("pledged_total_share_ratio", 0))
            >= TRIGGER_RULES[risk_id]["thresholds"]["total_share_ratio"]
        )
    if risk_id == "material_related_party_transaction_risk":
        return any(
            inputs.get(key) is True
            for key in ("non_market", "approval_cap_breach", "material_non_operating_finance")
        )
    if risk_id == "controlling_shareholder_fund_occupation_or_related_guarantee":
        return (
            inputs.get("fund_occupation") is True or inputs.get("illegal_related_guarantee") is True
        )
    if risk_id == "repeated_equity_financing_or_material_dilution":
        return (
            inputs.get("completed_financing") is True
            and float(inputs.get("realized_dilution_share_delta", 0)) > 0
        )
    raise RiskVetoContractError(f"unknown risk ID: {risk_id}")


def validate_observation(record: dict[str, Any]) -> None:
    _require(
        record,
        (
            "contract",
            "observation_id",
            "symbol",
            "risk_id",
            "as_of_date",
            "status",
            "event_ids",
            "evidence_ids",
            "search_register_id",
            "trigger_version",
            "inputs",
            "missing_reasons",
            "warnings",
            "deterministic_id",
            "supersedes",
            "code_version",
            "score_eligible",
        ),
        "observation record",
    )
    if record["contract"] != OBSERVATION_CONTRACT or record["risk_id"] not in RISK_IDS:
        raise RiskVetoContractError("invalid observation identity")
    if record["status"] not in STATUS_VOCABULARY or record["score_eligible"] is not False:
        raise RiskVetoContractError("invalid observation status or score eligibility")
    _date_like(record["as_of_date"], "as_of_date")
    if record["deterministic_id"] != stable_id(
        "risk_observation",
        {
            key: record[key]
            for key in (
                "symbol",
                "risk_id",
                "as_of_date",
                "status",
                "event_ids",
                "evidence_ids",
                "search_register_id",
                "trigger_version",
                "inputs",
                "missing_reasons",
            )
        },
    ):
        raise RiskVetoContractError("observation deterministic ID mismatch")


def evaluate_observations(
    *,
    symbol: str,
    as_of_date: str,
    events: list[dict[str, Any]],
    search_registers: list[dict[str, Any]],
    evidence: list[dict[str, Any]],
    code_version: str = CODE_VERSION,
) -> list[dict[str, Any]]:
    """Evaluate all eight risks using PIT-visible events and bounded searches."""

    for record in evidence:
        validate_evidence_record(record)
    for record in search_registers:
        validate_search_register(record)
    for record in events:
        validate_event_record(record)
    evidence_by_id = {record["source_evidence_id"]: record for record in evidence}
    registers = {record["risk_id"]: record for record in search_registers}
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for event in events:
        if event["symbol"] == symbol and event["available_at"][:10] <= as_of_date:
            grouped[event["risk_id"]].append(event)
    results: list[dict[str, Any]] = []
    for risk_id in RISK_IDS:
        risk_events = grouped[risk_id]
        register = registers.get(risk_id)
        event_ids = [event["event_id"] for event in risk_events]
        evidence_ids = sorted({item for event in risk_events for item in event["evidence_ids"]})
        missing_reasons = sorted(
            {reason for event in risk_events for reason in event["missing_reasons"] if reason}
        )
        warnings = sorted({warning for event in risk_events for warning in event["warnings"]})
        triggered = [event for event in risk_events if _triggered(risk_id, event["inputs"])]
        if triggered:
            status = "observed"
        elif any(event["status"] == "missing_evidence" for event in risk_events) or not register:
            status = "missing_evidence"
        elif not register["completeness"]:
            status = "missing_evidence"
            missing_reasons.append("bounded search register is incomplete")
        else:
            status = "not_observed_within_bounded_evidence"
        if not evidence_ids:
            available_at = as_of_date
        else:
            # An aggregate conclusion is not available until its latest
            # included source is available.  Using the earliest source would
            # create a silent look-ahead error in downstream PIT consumers.
            available_at = max(evidence_by_id[item]["available_at"][:10] for item in evidence_ids)
        inputs = {
            "triggered_event_count": len(triggered),
            "pit_visible_event_count": len(risk_events),
            "bounded_search_complete": bool(register and register["completeness"]),
        }
        record = {
            "contract": OBSERVATION_CONTRACT,
            "observation_id": stable_id(
                "risk_observation", {"symbol": symbol, "risk_id": risk_id, "as_of_date": as_of_date}
            ),
            "symbol": symbol,
            "risk_id": risk_id,
            "as_of_date": as_of_date,
            "available_at": available_at,
            "status": status,
            "event_ids": event_ids,
            "evidence_ids": evidence_ids,
            "search_register_id": register["search_register_id"] if register else None,
            "trigger_version": TRIGGER_RULES[risk_id]["version"],
            "inputs": inputs,
            "missing_reasons": missing_reasons,
            "warnings": warnings,
            "deterministic_id": "",
            "supersedes": None,
            "code_version": code_version,
            "score_eligible": False,
        }
        record["deterministic_id"] = stable_id(
            "risk_observation",
            {
                key: record[key]
                for key in (
                    "symbol",
                    "risk_id",
                    "as_of_date",
                    "status",
                    "event_ids",
                    "evidence_ids",
                    "search_register_id",
                    "trigger_version",
                    "inputs",
                    "missing_reasons",
                )
            },
        )
        record["observation_id"] = record["deterministic_id"]
        validate_observation(record)
        results.append(record)
    return results


def validate_contracts(
    *,
    evidence: list[dict[str, Any]],
    events: list[dict[str, Any]],
    search_registers: list[dict[str, Any]],
) -> dict[str, Any]:
    for record in evidence:
        validate_evidence_record(record)
    for record in events:
        validate_event_record(record)
    for record in search_registers:
        validate_search_register(record)
    if {record["risk_id"] for record in search_registers} != set(RISK_IDS):
        raise RiskVetoContractError("one bounded search register is required per risk")
    return {
        "status": "pass",
        "methodology_version": METHODOLOGY_VERSION,
        "evidence_count": len(evidence),
        "event_count": len(events),
        "search_register_count": len(search_registers),
        "risk_count": len(RISK_IDS),
        "score_eligible": False,
    }
