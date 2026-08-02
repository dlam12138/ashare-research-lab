"""Stage 2H.1R versioned PIT, supersession and evidence-lineage contracts."""

from __future__ import annotations

import hashlib
import json
import re
from collections import defaultdict
from datetime import UTC, date, datetime
from typing import Any

METHODOLOGY_VERSION = "risk_veto_methodology_v2"
CODE_VERSION = "stage2h1r_risk_veto_v1"
EVIDENCE_CONTRACT = "risk_evidence_record_v1"
EVENT_CONTRACT = "risk_event_record_v3"
OBSERVATION_CONTRACT = "risk_veto_observation_v3"
SEARCH_CONTRACT = "bounded_search_register_v2"
NORMALIZATION_CONTRACT = "risk_evidence_normalization_record_v1"
RISK_UNIVERSE_CONTRACT = "risk_universe_evaluation_v1"
RISK_SLOT_CONTRACT = "risk_evaluation_slot_v1"

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
    """Raised when a Stage 2H.1 contract is incomplete or unsafe."""


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def canonical_hash(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def stable_id(prefix: str, value: Any) -> str:
    """Return a content-addressed ID without machine-specific paths."""

    return f"{prefix}_{canonical_hash(value)[:24]}"


def _require(record: dict[str, Any], fields: tuple[str, ...], label: str) -> None:
    missing = [field for field in fields if field not in record]
    if missing:
        raise RiskVetoContractError(f"{label} missing required fields: {', '.join(missing)}")


def _parse_datetime(value: Any, field: str) -> datetime:
    if not isinstance(value, str) or not value:
        raise RiskVetoContractError(f"{field} must be a non-empty ISO date or timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        try:
            parsed = datetime.combine(date.fromisoformat(value), datetime.min.time())
        except ValueError as exc:
            raise RiskVetoContractError(f"{field} is not ISO date-like: {value}") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed


def _date_text(value: Any) -> str:
    return str(value)[:10]


def _not_after(left: str, right: str) -> bool:
    return _parse_datetime(left, "left") <= _parse_datetime(right, "right")


def _get_path(record: dict[str, Any], path: str) -> Any:
    value: Any = record
    for segment in path.split("."):
        if not isinstance(value, dict) or segment not in value:
            raise RiskVetoContractError(f"missing source field path: {path}")
        value = value[segment]
    return value


def _values_equal(left: Any, right: Any) -> bool:
    if isinstance(left, float) or isinstance(right, float):
        return abs(float(left) - float(right)) <= 1e-12
    return left == right


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
    _parse_datetime(record["announcement_date"], "announcement_date")
    _parse_datetime(record["retrieved_at"], "retrieved_at")
    _parse_datetime(record["available_at"], "available_at")
    if not isinstance(record["exact_url"], str) or not record["exact_url"].startswith("https://"):
        raise RiskVetoContractError("exact_url must be an official HTTPS locator")
    expected_locator = hashlib.sha256(record["exact_url"].encode()).hexdigest()
    if record["locator_sha256"] != expected_locator:
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
            "contract_version",
            "search_register_id",
            "risk_id",
            "coverage_start",
            "coverage_end",
            "query_started_at",
            "query_completed_at",
            "available_at",
            "systems",
            "terms",
            "identifiers",
            "completeness",
            "completeness_basis",
            "result_count",
            "retrieved_count",
            "rejected_count",
            "rejected_candidates",
            "anti_bot_gaps",
            "network_gaps",
            "supersedes_search_register_id",
            "code_version",
        ),
        "search register",
    )
    if record["contract"] != SEARCH_CONTRACT or record["contract_version"] != SEARCH_CONTRACT:
        raise RiskVetoContractError("unsupported search register contract")
    if record["risk_id"] not in RISK_IDS:
        raise RiskVetoContractError("invalid search register risk ID")
    for field in (
        "coverage_start",
        "coverage_end",
        "query_started_at",
        "query_completed_at",
        "available_at",
    ):
        _parse_datetime(record[field], field)
    if not _not_after(record["coverage_start"], record["coverage_end"]):
        raise RiskVetoContractError("search coverage dates are reversed")
    if not _not_after(record["query_started_at"], record["query_completed_at"]):
        raise RiskVetoContractError("search query timestamps are reversed")
    if not _not_after(record["query_completed_at"], record["available_at"]):
        raise RiskVetoContractError("search available_at precedes query completion")
    if not isinstance(record["systems"], list) or not record["systems"]:
        raise RiskVetoContractError("bounded search systems are required")
    if not isinstance(record["terms"], list) or not isinstance(record["identifiers"], list):
        raise RiskVetoContractError("search terms and identifiers must be lists")
    for field in ("result_count", "retrieved_count", "rejected_count"):
        if not isinstance(record[field], int) or record[field] < 0:
            raise RiskVetoContractError(f"{field} must be non-negative")
    if record["rejected_count"] != len(record["rejected_candidates"]):
        raise RiskVetoContractError("rejected_count does not match rejected_candidates")
    if not isinstance(record["completeness"], bool) or not record["completeness_basis"]:
        raise RiskVetoContractError("search completeness must be explicit")
    for field in ("anti_bot_gaps", "network_gaps"):
        if not isinstance(record[field], list):
            raise RiskVetoContractError(f"{field} must be a list")


def validate_search_register_chain(
    search_registers: list[dict[str, Any]], *, research_cutoff: str | None = None
) -> dict[str, Any]:
    """Validate all search versions before any PIT selection."""

    by_id: dict[str, dict[str, Any]] = {}
    for record in search_registers:
        validate_search_register(record)
        key = record["search_register_id"]
        if key in by_id:
            raise RiskVetoContractError(f"duplicate search register ID: {key}")
        by_id[key] = record
    if research_cutoff is not None:
        for record in search_registers:
            if not _not_after(record["coverage_end"], research_cutoff):
                raise RiskVetoContractError(
                    f"search coverage exceeds research cutoff: {record['search_register_id']}"
                )
    child_by_parent: dict[str, list[str]] = defaultdict(list)
    for record in search_registers:
        parent = record["supersedes_search_register_id"]
        if parent is None:
            continue
        if parent not in by_id:
            raise RiskVetoContractError(f"missing superseded search register: {parent}")
        prior = by_id[parent]
        if prior["risk_id"] != record["risk_id"]:
            raise RiskVetoContractError("search supersession crosses risk IDs")
        if not _not_after(prior["available_at"], record["available_at"]):
            raise RiskVetoContractError("search supersession has reverse availability order")
        child_by_parent[parent].append(record["search_register_id"])
    if any(len(children) > 1 for children in child_by_parent.values()):
        raise RiskVetoContractError("search supersession has conflicting branches")
    for start in by_id:
        seen: set[str] = set()
        cursor = start
        while cursor:
            if cursor in seen:
                raise RiskVetoContractError("search supersession cycle detected")
            seen.add(cursor)
            cursor = by_id[cursor]["supersedes_search_register_id"]
    return {"status": "pass", "register_count": len(by_id), "version_chain_valid": True}


def select_search_register_as_of(
    risk_id: str,
    as_of_date: str,
    search_registers: list[dict[str, Any]],
    *,
    research_cutoff: str | None = None,
) -> dict[str, Any] | None:
    """Select the latest valid PIT register, or return None fail-closed."""

    validate_search_register_chain(search_registers, research_cutoff=research_cutoff)
    records = [record for record in search_registers if record["risk_id"] == risk_id]
    visible = [record for record in records if _not_after(record["available_at"], as_of_date)]
    visible_ids = {record["search_register_id"] for record in visible}
    superseded_visible: set[str] = set()
    by_id = {record["search_register_id"]: record for record in records}
    for record in visible:
        cursor = record["supersedes_search_register_id"]
        while cursor and cursor in visible_ids:
            superseded_visible.add(cursor)
            cursor = by_id[cursor]["supersedes_search_register_id"]
    candidates = [
        record
        for record in visible
        if record["search_register_id"] not in superseded_visible
        and _not_after(record["coverage_end"], as_of_date)
    ]
    if not candidates:
        return None
    candidates.sort(
        key=lambda record: (
            record["available_at"],
            record["query_completed_at"],
            record["search_register_id"],
        )
    )
    selected = candidates[-1]
    if len(candidates) > 1 and (
        candidates[-1]["available_at"] == candidates[-2]["available_at"]
        and candidates[-1]["query_completed_at"] == candidates[-2]["query_completed_at"]
    ):
        raise RiskVetoContractError("search register selection has an unresolved tie")
    return selected


def validate_normalization_record(record: dict[str, Any]) -> None:
    _require(
        record,
        (
            "contract",
            "normalization_id",
            "risk_id",
            "event_semantic_key",
            "target_field",
            "source_evidence_id",
            "source_field_path",
            "raw_value",
            "raw_unit",
            "normalized_value",
            "normalized_unit",
            "transform",
            "denominator_fact_ids",
            "denominator_evidence_ids",
            "rounding_policy",
            "formula_version",
            "verification_status",
            "warnings",
            "available_at",
            "code_version",
        ),
        "normalization record",
    )
    if record["contract"] != NORMALIZATION_CONTRACT or record["risk_id"] not in RISK_IDS:
        raise RiskVetoContractError("invalid normalization contract or risk ID")
    if not isinstance(record["denominator_fact_ids"], list) or not isinstance(
        record["denominator_evidence_ids"], list
    ):
        raise RiskVetoContractError("normalization denominator IDs must be lists")
    if record["verification_status"] not in {"verified", "unresolved_conflict", "missing_evidence"}:
        raise RiskVetoContractError("invalid normalization verification status")
    if not isinstance(record["warnings"], list):
        raise RiskVetoContractError("normalization warnings must be a list")
    _parse_datetime(record["available_at"], "normalization.available_at")


def _transform_normalized_value(record: dict[str, Any], evidence: dict[str, Any]) -> Any:
    transform = record["transform"]
    raw = record["raw_value"]
    if transform == "identity" or transform == "reported_ratio_identity_v1":
        return raw
    if transform == "audit_opinion_to_class_v1":
        if raw in {"standard_unmodified", "unmodified", "unqualified"}:
            return "unmodified"
        if raw in {"qualified", "adverse", "disclaimer"}:
            return raw
        raise RiskVetoContractError(f"unknown audit opinion normalization: {raw}")
    if transform == "ratio_from_evidence_fields_v1":
        denominator_path = record.get("denominator_field_path")
        if not denominator_path:
            raise RiskVetoContractError("ratio normalization has no denominator path")
        denominator = _get_path(evidence, denominator_path)
        if float(denominator) == 0:
            raise RiskVetoContractError("ratio normalization has zero denominator")
        return float(raw) / float(denominator)
    raise RiskVetoContractError(f"unsupported normalization transform: {transform}")


def normalization_lineage_hash(records: list[dict[str, Any]]) -> str:
    return canonical_hash(
        [
            {
                key: record[key]
                for key in (
                    "normalization_id",
                    "target_field",
                    "source_evidence_id",
                    "source_field_path",
                    "raw_value",
                    "normalized_value",
                    "transform",
                    "denominator_fact_ids",
                    "denominator_evidence_ids",
                    "formula_version",
                )
            }
            for record in sorted(records, key=lambda item: item["normalization_id"])
        ]
    )


def validate_event_evidence_lineage(
    event: dict[str, Any],
    evidence: list[dict[str, Any]],
    normalizations: list[dict[str, Any]],
) -> dict[str, Any]:
    """Prove deterministic inputs and keep supplemental evidence out of lineage."""

    evidence_by_id = {record["source_evidence_id"]: record for record in evidence}
    normalization_by_id = {record["normalization_id"]: record for record in normalizations}
    for record in evidence:
        validate_evidence_record(record)
    for record in normalizations:
        validate_normalization_record(record)
    input_ids = list(event["input_evidence_ids"])
    supplemental_ids = list(event["supplemental_evidence_ids"])
    all_ids = list(event["all_evidence_ids"])
    if len(input_ids) != len(set(input_ids)) or len(supplemental_ids) != len(set(supplemental_ids)):
        raise RiskVetoContractError("event evidence IDs must be unique")
    if set(input_ids) & set(supplemental_ids):
        raise RiskVetoContractError("event input and supplemental evidence overlap")
    expected_all = sorted(set(input_ids) | set(supplemental_ids))
    if all_ids != expected_all:
        raise RiskVetoContractError("event all_evidence_ids is not the ordered union")
    for evidence_id in all_ids:
        if evidence_id not in evidence_by_id:
            raise RiskVetoContractError(f"event references unknown evidence: {evidence_id}")
    selected: list[dict[str, Any]] = []
    for normalization_id in event["normalization_ids"]:
        if normalization_id not in normalization_by_id:
            raise RiskVetoContractError(
                f"event references unknown normalization: {normalization_id}"
            )
        record = normalization_by_id[normalization_id]
        if (
            record["risk_id"] != event["risk_id"]
            or record["event_semantic_key"] != event["semantic_key"]
        ):
            raise RiskVetoContractError("normalization semantic identity does not match event")
        if record["verification_status"] != "verified":
            raise RiskVetoContractError(
                f"event uses unresolved normalization: {record['normalization_id']}"
            )
        source = evidence_by_id.get(record["source_evidence_id"])
        if source is None:
            raise RiskVetoContractError("normalization references unknown evidence")
        actual_raw = _get_path(source, record["source_field_path"])
        if not _values_equal(actual_raw, record["raw_value"]):
            raise RiskVetoContractError(
                f"normalization raw value mismatch: {record['normalization_id']}"
            )
        recalculated = _transform_normalized_value(record, source)
        if not _values_equal(recalculated, record["normalized_value"]):
            raise RiskVetoContractError(
                f"normalization transformed value mismatch: {record['normalization_id']}"
            )
        if not set(record["denominator_evidence_ids"]) <= set(input_ids):
            raise RiskVetoContractError("normalization denominator must be input evidence")
        if not _not_after(source["available_at"], record["available_at"]):
            raise RiskVetoContractError("normalization available_at precedes source evidence")
        selected.append(record)
    fields_seen: set[str] = set()
    for record in selected:
        if record["target_field"] in fields_seen:
            raise RiskVetoContractError(
                f"conflicting duplicate normalized field: {record['target_field']}"
            )
        fields_seen.add(record["target_field"])
    expected_inputs = {record["target_field"]: record["normalized_value"] for record in selected}
    if event["inputs"] != expected_inputs:
        raise RiskVetoContractError(f"event inputs are not reconstructible: {event['event_id']}")
    expected_input_ids = sorted(
        {
            item
            for record in selected
            for item in [record["source_evidence_id"], *record["denominator_evidence_ids"]]
        }
    )
    if input_ids != expected_input_ids:
        raise RiskVetoContractError(
            "event input evidence is not reconstructible from normalization"
        )
    expected_input_sources = sorted({evidence_by_id[item]["source_type"] for item in input_ids})
    expected_supplemental_sources = sorted(
        {evidence_by_id[item]["source_type"] for item in supplemental_ids}
    )
    if event["input_source_types"] != expected_input_sources:
        raise RiskVetoContractError(
            f"event input source types are not evidence-derived: {event['event_id']}"
        )
    if event["supplemental_source_types"] != expected_supplemental_sources:
        raise RiskVetoContractError(
            f"event supplemental source types are not evidence-derived: {event['event_id']}"
        )
    availability = [evidence_by_id[item]["available_at"] for item in all_ids]
    availability.extend(record["available_at"] for record in selected)
    if availability and not all(_not_after(item, event["available_at"]) for item in availability):
        raise RiskVetoContractError(f"event available_at precedes an input: {event['event_id']}")
    expected_hash = normalization_lineage_hash(selected)
    if expected_hash != event["input_lineage_hash"]:
        raise RiskVetoContractError(f"event input lineage hash mismatch: {event['event_id']}")
    return {
        "status": "pass",
        "normalization_ids": [record["normalization_id"] for record in selected],
        "input_evidence_ids": input_ids,
        "supplemental_evidence_ids": supplemental_ids,
        "all_evidence_ids": all_ids,
        "input_lineage_hash": expected_hash,
    }


def _event_identity_payload(record: dict[str, Any]) -> dict[str, Any]:
    return {
        key: record[key]
        for key in (
            "symbol",
            "risk_id",
            "semantic_key",
            "event_type",
            "event_date",
            "available_at",
            "period",
            "input_evidence_ids",
            "supplemental_evidence_ids",
            "all_evidence_ids",
            "normalization_ids",
            "input_lineage_hash",
            "classification",
            "trigger_version",
            "inputs",
            "status",
            "supersedes",
        )
    }


def validate_event_record(record: dict[str, Any]) -> None:
    _require(
        record,
        (
            "contract",
            "event_id",
            "symbol",
            "risk_id",
            "semantic_key",
            "event_type",
            "event_date",
            "available_at",
            "period",
            "input_evidence_ids",
            "supplemental_evidence_ids",
            "all_evidence_ids",
            "input_source_types",
            "supplemental_source_types",
            "extraction_method",
            "classification",
            "trigger_version",
            "inputs",
            "normalization_ids",
            "input_lineage_hash",
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
    for field in ("event_date", "available_at"):
        _parse_datetime(record[field], field)
    if record["status"] not in STATUS_VOCABULARY or record["score_eligible"] is not False:
        raise RiskVetoContractError("invalid event status or score eligibility")
    if any(
        not isinstance(record[field], list)
        for field in (
            "input_evidence_ids",
            "supplemental_evidence_ids",
            "all_evidence_ids",
            "input_source_types",
            "supplemental_source_types",
        )
    ):
        raise RiskVetoContractError("event evidence/source types must be lists")
    if set(record["input_evidence_ids"]) & set(record["supplemental_evidence_ids"]):
        raise RiskVetoContractError("event input and supplemental evidence overlap")
    if record["all_evidence_ids"] != sorted(
        set(record["input_evidence_ids"]) | set(record["supplemental_evidence_ids"])
    ):
        raise RiskVetoContractError("event all_evidence_ids is not the ordered union")
    if any(
        source not in TRUE_SOURCE_TYPES
        for field in ("input_source_types", "supplemental_source_types")
        for source in record[field]
    ):
        raise RiskVetoContractError("event contains an untrusted source type")
    if not isinstance(record["normalization_ids"], list) or not _HEX64.fullmatch(
        record["input_lineage_hash"]
    ):
        raise RiskVetoContractError("event normalization lineage is malformed")
    expected = stable_id("risk_event", _event_identity_payload(record))
    if record["event_id"] != expected:
        raise RiskVetoContractError(f"event deterministic ID mismatch: {record['event_id']}")


def validate_event_supersession_chain(events: list[dict[str, Any]]) -> dict[str, Any]:
    by_id: dict[str, dict[str, Any]] = {}
    for event in events:
        validate_event_record(event)
        if event["event_id"] in by_id:
            raise RiskVetoContractError(f"duplicate event ID: {event['event_id']}")
        by_id[event["event_id"]] = event
    children: dict[str, list[str]] = defaultdict(list)
    for event in events:
        parent_id = event["supersedes"]
        if parent_id is None:
            continue
        if parent_id == event["event_id"] or parent_id not in by_id:
            raise RiskVetoContractError(f"invalid superseded event: {parent_id}")
        parent = by_id[parent_id]
        if (parent["symbol"], parent["risk_id"], parent["semantic_key"]) != (
            event["symbol"],
            event["risk_id"],
            event["semantic_key"],
        ):
            raise RiskVetoContractError("event supersession crosses identity or semantic key")
        if not _not_after(parent["available_at"], event["available_at"]):
            raise RiskVetoContractError("event supersession has reverse availability order")
        children[parent_id].append(event["event_id"])
    if any(len(items) > 1 for items in children.values()):
        raise RiskVetoContractError("event supersession has conflicting branches")
    for start in by_id:
        seen: set[str] = set()
        cursor = start
        while cursor:
            if cursor in seen:
                raise RiskVetoContractError("event supersession cycle detected")
            seen.add(cursor)
            cursor = by_id[cursor]["supersedes"]
    return {"status": "pass", "event_count": len(by_id), "supersession_chain_valid": True}


def resolve_active_events_as_of(
    symbol: str,
    risk_id: str,
    as_of_date: str,
    events: list[dict[str, Any]],
) -> dict[str, Any]:
    """Return only active events visible at a PIT research date."""

    validate_event_supersession_chain(events)
    scoped = [
        event for event in events if event["symbol"] == symbol and event["risk_id"] == risk_id
    ]
    visible = [event for event in scoped if _not_after(event["available_at"], as_of_date)]
    visible_ids = {event["event_id"] for event in visible}
    by_id = {event["event_id"]: event for event in scoped}
    superseded: set[str] = set()
    edges: list[dict[str, str]] = []
    for event in visible:
        cursor = event["supersedes"]
        if cursor and cursor in visible_ids:
            edges.append({"superseder_event_id": event["event_id"], "superseded_event_id": cursor})
        while cursor and cursor in visible_ids:
            superseded.add(cursor)
            cursor = by_id[cursor]["supersedes"]
    active = [event for event in visible if event["event_id"] not in superseded]
    active.sort(key=lambda event: (event["event_date"], event["available_at"], event["event_id"]))
    return {
        "status": "pass",
        "active_events": active,
        "visible_event_ids": [event["event_id"] for event in visible],
        "active_event_ids": [event["event_id"] for event in active],
        "superseded_event_ids": sorted(superseded),
        "applied_supersession_edges": edges,
        "event_version_resolution_status": "pass",
    }


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


def _observation_identity_payload(record: dict[str, Any]) -> dict[str, Any]:
    return {
        key: record[key]
        for key in (
            "symbol",
            "risk_id",
            "evaluation_as_of_date",
            "conclusion_available_at",
            "status",
            "active_event_ids",
            "superseded_event_ids",
            "applied_supersession_edges",
            "event_version_resolution_status",
            "input_evidence_ids",
            "supplemental_evidence_ids",
            "all_evidence_ids",
            "search_register_id",
            "search_contract_version",
            "search_available_at",
            "search_coverage_end",
            "bounded_search_complete",
            "search_gap_reasons",
            "trigger_version",
            "inputs",
            "missing_reasons",
            "lineage_status",
        )
    }


def validate_observation(record: dict[str, Any]) -> None:
    _require(
        record,
        (
            "contract",
            "observation_id",
            "symbol",
            "risk_id",
            "evaluation_as_of_date",
            "available_at",
            "conclusion_available_at",
            "status",
            "active_event_ids",
            "superseded_event_ids",
            "applied_supersession_edges",
            "event_version_resolution_status",
            "input_evidence_ids",
            "supplemental_evidence_ids",
            "all_evidence_ids",
            "search_register_id",
            "search_contract_version",
            "search_available_at",
            "search_coverage_end",
            "bounded_search_complete",
            "search_gap_reasons",
            "trigger_version",
            "inputs",
            "missing_reasons",
            "warnings",
            "lineage_status",
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
    _parse_datetime(record["evaluation_as_of_date"], "evaluation_as_of_date")
    _parse_datetime(record["available_at"], "available_at")
    if record["available_at"] != record["conclusion_available_at"]:
        raise RiskVetoContractError("available_at must equal conclusion_available_at")
    if not _not_after(record["available_at"], record["evaluation_as_of_date"]):
        raise RiskVetoContractError("observation conclusion is not available at evaluation as-of")
    if record["search_available_at"] is not None:
        _parse_datetime(record["search_available_at"], "search_available_at")
        if not _not_after(record["search_available_at"], record["evaluation_as_of_date"]):
            raise RiskVetoContractError("search register is not PIT-visible")
    if record["search_coverage_end"] is not None and not _not_after(
        record["search_coverage_end"], record["evaluation_as_of_date"]
    ):
        raise RiskVetoContractError("search coverage exceeds evaluation as-of")
    if record["event_version_resolution_status"] != "pass":
        raise RiskVetoContractError("event version resolution did not pass")
    if not isinstance(record["applied_supersession_edges"], list):
        raise RiskVetoContractError("supersession edges must be a list")
    if any(
        not isinstance(record[field], list)
        for field in ("input_evidence_ids", "supplemental_evidence_ids", "all_evidence_ids")
    ):
        raise RiskVetoContractError("observation evidence fields must be lists")
    if set(record["input_evidence_ids"]) & set(record["supplemental_evidence_ids"]):
        raise RiskVetoContractError("observation input and supplemental evidence overlap")
    if record["all_evidence_ids"] != sorted(
        set(record["input_evidence_ids"]) | set(record["supplemental_evidence_ids"])
    ):
        raise RiskVetoContractError("observation all_evidence_ids is not the ordered union")
    expected = stable_id("risk_observation", _observation_identity_payload(record))
    if record["deterministic_id"] != expected or record["observation_id"] != expected:
        raise RiskVetoContractError("observation deterministic ID mismatch")


def evaluate_observations(
    *,
    symbol: str,
    as_of_date: str,
    events: list[dict[str, Any]],
    search_registers: list[dict[str, Any]],
    evidence: list[dict[str, Any]],
    normalizations: list[dict[str, Any]],
    code_version: str = CODE_VERSION,
) -> list[dict[str, Any]]:
    """Evaluate active, PIT-visible events and the PIT-selected search register."""

    for record in evidence:
        validate_evidence_record(record)
    validate_search_register_chain(search_registers)
    for record in events:
        validate_event_record(record)
        validate_event_evidence_lineage(record, evidence, normalizations)
    validate_event_supersession_chain(events)
    evidence_by_id = {record["source_evidence_id"]: record for record in evidence}
    results: list[dict[str, Any]] = []
    for risk_id in RISK_IDS:
        register = select_search_register_as_of(risk_id, as_of_date, search_registers)
        resolution = resolve_active_events_as_of(symbol, risk_id, as_of_date, events)
        active_events = resolution["active_events"]
        active_event_ids = resolution["active_event_ids"]
        input_evidence_ids = sorted(
            {item for event in active_events for item in event["input_evidence_ids"]}
        )
        supplemental_evidence_ids = sorted(
            {item for event in active_events for item in event["supplemental_evidence_ids"]}
        )
        all_evidence_ids = sorted(set(input_evidence_ids) | set(supplemental_evidence_ids))
        if set(input_evidence_ids) & set(supplemental_evidence_ids):
            raise RiskVetoContractError("active event evidence has input/supplemental overlap")
        missing_reasons = sorted(
            {reason for event in active_events for reason in event["missing_reasons"] if reason}
        )
        warnings = sorted({warning for event in active_events for warning in event["warnings"]})
        if register is None:
            missing_reasons.append("no PIT-visible search register with coverage_end <= as_of_date")
            status = "missing_evidence"
        elif not register["completeness"]:
            missing_reasons.append("bounded search register is incomplete")
            status = "missing_evidence"
        elif any(_triggered(risk_id, event["inputs"]) for event in active_events):
            status = "observed"
        elif not active_events:
            missing_reasons.append("no PIT-visible active event evidence")
            status = "missing_evidence"
        else:
            status = "not_observed_within_bounded_evidence"
        availability = [event["available_at"] for event in active_events]
        availability.extend(evidence_by_id[item]["available_at"] for item in all_evidence_ids)
        if register is not None:
            availability.append(register["available_at"])
        if not availability:
            # There is no conclusion to expose for a risk with no PIT-visible
            # input.  The public universe evaluator will publish its slot.
            continue
        conclusion_available_at = max(
            availability, key=lambda item: _parse_datetime(item, "available_at")
        ).replace("Z", "+00:00")
        if not _not_after(conclusion_available_at, as_of_date):
            continue
        search_gap_reasons = (
            list(register["network_gaps"] + register["anti_bot_gaps"])
            if register
            else ["search register not PIT-visible"]
        )
        inputs = {
            "triggered_event_count": sum(
                _triggered(risk_id, event["inputs"]) for event in active_events
            ),
            "pit_visible_event_count": len(active_events),
            "bounded_search_complete": bool(register and register["completeness"]),
        }
        record = {
            "contract": OBSERVATION_CONTRACT,
            "observation_id": "",
            "symbol": symbol,
            "risk_id": risk_id,
            "evaluation_as_of_date": as_of_date,
            "available_at": conclusion_available_at,
            "conclusion_available_at": conclusion_available_at,
            "status": status,
            "active_event_ids": active_event_ids,
            "superseded_event_ids": resolution["superseded_event_ids"],
            "applied_supersession_edges": resolution["applied_supersession_edges"],
            "event_version_resolution_status": resolution["event_version_resolution_status"],
            "input_evidence_ids": input_evidence_ids,
            "supplemental_evidence_ids": supplemental_evidence_ids,
            "all_evidence_ids": all_evidence_ids,
            "search_register_id": register["search_register_id"] if register else None,
            "search_contract_version": register["contract_version"] if register else None,
            "search_available_at": register["available_at"] if register else None,
            "search_coverage_end": register["coverage_end"] if register else None,
            "bounded_search_complete": bool(register and register["completeness"]),
            "search_gap_reasons": sorted(set(search_gap_reasons)),
            "trigger_version": TRIGGER_RULES[risk_id]["version"],
            "inputs": inputs,
            "missing_reasons": sorted(set(missing_reasons)),
            "warnings": warnings,
            "lineage_status": "pass" if all_evidence_ids or register else "missing_evidence",
            "deterministic_id": "",
            "supersedes": None,
            "code_version": code_version,
            "score_eligible": False,
        }
        record["deterministic_id"] = stable_id(
            "risk_observation", _observation_identity_payload(record)
        )
        record["observation_id"] = record["deterministic_id"]
        validate_observation(record)
        results.append(record)
    return results


def _risk_slot_identity_payload(record: dict[str, Any]) -> dict[str, Any]:
    return {
        key: record[key]
        for key in (
            "symbol",
            "risk_id",
            "evaluation_as_of_date",
            "evaluation_status",
            "observation_emitted",
            "observation_id",
            "conclusion_available_at",
            "selected_search_register_id",
            "visible_active_event_ids",
            "visible_input_evidence_ids",
            "missing_reasons",
            "lineage_status",
        )
    }


def validate_risk_universe_evaluation(record: dict[str, Any]) -> None:
    """Validate a complete, fixed-cardinality risk evaluation snapshot."""

    _require(
        record,
        (
            "contract",
            "symbol",
            "evaluation_as_of_date",
            "expected_risk_ids",
            "expected_risk_count",
            "emitted_observation_count",
            "slots",
            "observations",
            "completeness_status",
            "missing_slot_count",
            "deterministic_id",
            "score_eligible",
        ),
        "risk universe evaluation",
    )
    if record["contract"] != RISK_UNIVERSE_CONTRACT or record["score_eligible"] is not False:
        raise RiskVetoContractError("invalid risk universe contract or score eligibility")
    if record["expected_risk_ids"] != list(RISK_IDS) or record["expected_risk_count"] != len(
        RISK_IDS
    ):
        raise RiskVetoContractError("risk universe expected IDs are not the frozen eight")
    if len(record["slots"]) != len(RISK_IDS):
        raise RiskVetoContractError("risk universe must contain exactly eight slots")
    if {item.get("risk_id") for item in record["slots"]} != set(RISK_IDS):
        raise RiskVetoContractError("risk universe slot IDs are incomplete or unknown")
    if len({item["risk_id"] for item in record["slots"]}) != len(RISK_IDS):
        raise RiskVetoContractError("risk universe contains duplicate risk slots")
    observations = record["observations"]
    if len(observations) != record["emitted_observation_count"]:
        raise RiskVetoContractError("risk universe observation count mismatch")
    observation_by_id: dict[str, dict[str, Any]] = {}
    for observation in observations:
        validate_observation(observation)
        if observation["symbol"] != record["symbol"] or observation["evaluation_as_of_date"] != (
            record["evaluation_as_of_date"]
        ):
            raise RiskVetoContractError("observation is outside risk universe identity")
        if observation["observation_id"] in observation_by_id:
            raise RiskVetoContractError("duplicate risk observation ID in universe")
        observation_by_id[observation["observation_id"]] = observation
    emitted = 0
    expected_slots: list[dict[str, Any]] = []
    for slot in record["slots"]:
        _require(
            slot,
            (
                "contract",
                "slot_id",
                "symbol",
                "risk_id",
                "evaluation_as_of_date",
                "evaluation_status",
                "observation_emitted",
                "observation_id",
                "conclusion_available_at",
                "selected_search_register_id",
                "visible_active_event_ids",
                "visible_input_evidence_ids",
                "missing_reasons",
                "lineage_status",
                "score_eligible",
            ),
            "risk evaluation slot",
        )
        if slot["contract"] != RISK_SLOT_CONTRACT or slot["score_eligible"] is not False:
            raise RiskVetoContractError("invalid risk evaluation slot contract")
        if slot["symbol"] != record["symbol"] or slot["evaluation_as_of_date"] != (
            record["evaluation_as_of_date"]
        ):
            raise RiskVetoContractError("slot is outside risk universe identity")
        if slot["evaluation_status"] not in STATUS_VOCABULARY:
            raise RiskVetoContractError("invalid risk evaluation slot status")
        if not isinstance(slot["observation_emitted"], bool):
            raise RiskVetoContractError("slot observation_emitted must be boolean")
        if not isinstance(slot["missing_reasons"], list):
            raise RiskVetoContractError("slot missing_reasons must be a list")
        if not isinstance(slot["visible_active_event_ids"], list) or not isinstance(
            slot["visible_input_evidence_ids"], list
        ):
            raise RiskVetoContractError("slot visible lineage fields must be lists")
        if slot["observation_emitted"]:
            emitted += 1
            if slot["observation_id"] not in observation_by_id:
                raise RiskVetoContractError("emitted slot does not reference an observation")
            observation = observation_by_id[slot["observation_id"]]
            if observation["risk_id"] != slot["risk_id"] or observation["status"] != (
                slot["evaluation_status"]
            ):
                raise RiskVetoContractError("slot and observation status or risk ID mismatch")
            if slot["conclusion_available_at"] != observation["conclusion_available_at"]:
                raise RiskVetoContractError("slot conclusion availability mismatch")
            if slot["selected_search_register_id"] != observation["search_register_id"]:
                raise RiskVetoContractError("slot search-register identity mismatch")
            if slot["visible_active_event_ids"] != observation["active_event_ids"]:
                raise RiskVetoContractError("slot active-event identity mismatch")
            if slot["visible_input_evidence_ids"] != observation["input_evidence_ids"]:
                raise RiskVetoContractError("slot input-evidence identity mismatch")
        else:
            if slot["observation_id"] is not None or slot["conclusion_available_at"] is not None:
                raise RiskVetoContractError("unemitted slot contains a fabricated observation")
            if slot["evaluation_status"] != "missing_evidence":
                raise RiskVetoContractError("unemitted slot must be missing_evidence")
            if "no PIT-visible input" not in " ".join(slot["missing_reasons"]):
                raise RiskVetoContractError("unemitted slot must explain missing PIT input")
        expected_slots.append(slot)
        if stable_id("risk_slot", _risk_slot_identity_payload(slot)) != slot["slot_id"]:
            raise RiskVetoContractError("risk slot deterministic ID mismatch")
    if emitted != record["emitted_observation_count"]:
        raise RiskVetoContractError("emitted slot count does not match universe count")
    if set(observation_by_id) != {
        slot["observation_id"] for slot in record["slots"] if slot["observation_emitted"]
    }:
        raise RiskVetoContractError("every observation must be referenced by exactly one slot")
    if record["missing_slot_count"] != len(RISK_IDS) - emitted:
        raise RiskVetoContractError("risk universe missing slot count mismatch")
    expected_id = stable_id(
        "risk_universe",
        {
            "symbol": record["symbol"],
            "evaluation_as_of_date": record["evaluation_as_of_date"],
            "expected_risk_ids": record["expected_risk_ids"],
            "slots": record["slots"],
        },
    )
    if record["deterministic_id"] != expected_id:
        raise RiskVetoContractError("risk universe deterministic ID mismatch")


def evaluate_risk_universe_as_of(
    *,
    symbol: str,
    as_of_date: str,
    events: list[dict[str, Any]],
    search_registers: list[dict[str, Any]],
    evidence: list[dict[str, Any]],
    normalizations: list[dict[str, Any]],
    code_version: str = CODE_VERSION,
) -> dict[str, Any]:
    """Evaluate all eight risk slots without inventing unavailable observations."""

    observations = evaluate_observations(
        symbol=symbol,
        as_of_date=as_of_date,
        events=events,
        search_registers=search_registers,
        evidence=evidence,
        normalizations=normalizations,
        code_version=code_version,
    )
    observations_by_risk = {item["risk_id"]: item for item in observations}
    slots: list[dict[str, Any]] = []
    for risk_id in RISK_IDS:
        register = select_search_register_as_of(risk_id, as_of_date, search_registers)
        resolution = resolve_active_events_as_of(symbol, risk_id, as_of_date, events)
        active_events = resolution["active_events"]
        visible_input_evidence_ids = sorted(
            {item for event in active_events for item in event["input_evidence_ids"]}
        )
        observation = observations_by_risk.get(risk_id)
        if observation is not None:
            status = observation["status"]
            observation_emitted = True
            observation_id = observation["observation_id"]
            conclusion_available_at = observation["conclusion_available_at"]
            missing_reasons = observation["missing_reasons"]
            lineage_status = observation["lineage_status"]
            selected_search_register_id = observation["search_register_id"]
        else:
            status = "missing_evidence"
            observation_emitted = False
            observation_id = None
            conclusion_available_at = None
            missing_reasons = []
            if register is None:
                missing_reasons.append(
                    "no PIT-visible search register with coverage_end <= as_of_date"
                )
            if not active_events:
                missing_reasons.append("no PIT-visible active event evidence")
            if not register and not active_events and not visible_input_evidence_ids:
                missing_reasons.append("no PIT-visible input")
            missing_reasons = sorted(set(missing_reasons))
            lineage_status = "pass" if register or active_events else "missing_evidence"
            selected_search_register_id = None
        slot = {
            "contract": RISK_SLOT_CONTRACT,
            "slot_id": "",
            "symbol": symbol,
            "risk_id": risk_id,
            "evaluation_as_of_date": as_of_date,
            "evaluation_status": status,
            "observation_emitted": observation_emitted,
            "observation_id": observation_id,
            "conclusion_available_at": conclusion_available_at,
            "selected_search_register_id": selected_search_register_id,
            "visible_active_event_ids": resolution["active_event_ids"],
            "visible_input_evidence_ids": visible_input_evidence_ids,
            "missing_reasons": missing_reasons,
            "lineage_status": lineage_status,
            "code_version": code_version,
            "score_eligible": False,
        }
        slot["slot_id"] = stable_id("risk_slot", _risk_slot_identity_payload(slot))
        slots.append(slot)
    record = {
        "contract": RISK_UNIVERSE_CONTRACT,
        "symbol": symbol,
        "evaluation_as_of_date": as_of_date,
        "expected_risk_ids": list(RISK_IDS),
        "expected_risk_count": len(RISK_IDS),
        "emitted_observation_count": len(observations),
        "slots": slots,
        "observations": observations,
        "completeness_status": (
            "complete"
            if len(observations) == len(RISK_IDS)
            else "complete_with_explicit_missing_slots"
        ),
        "missing_slot_count": len(RISK_IDS) - len(observations),
        "deterministic_id": "",
        "code_version": code_version,
        "score_eligible": False,
    }
    record["deterministic_id"] = stable_id(
        "risk_universe",
        {
            "symbol": symbol,
            "evaluation_as_of_date": as_of_date,
            "expected_risk_ids": list(RISK_IDS),
            "slots": slots,
        },
    )
    validate_risk_universe_evaluation(record)
    return record


def validate_contracts(
    *,
    evidence: list[dict[str, Any]],
    events: list[dict[str, Any]],
    search_registers: list[dict[str, Any]],
    normalizations: list[dict[str, Any]],
) -> dict[str, Any]:
    for record in evidence:
        validate_evidence_record(record)
    validate_search_register_chain(search_registers)
    for record in events:
        validate_event_record(record)
        validate_event_evidence_lineage(record, evidence, normalizations)
    validate_event_supersession_chain(events)
    if {record["risk_id"] for record in search_registers} != set(RISK_IDS):
        raise RiskVetoContractError("one bounded search register is required per risk")
    return {
        "status": "pass",
        "methodology_version": METHODOLOGY_VERSION,
        "evidence_count": len(evidence),
        "event_count": len(events),
        "normalization_count": len(normalizations),
        "search_register_count": len(search_registers),
        "risk_count": len(RISK_IDS),
        "score_eligible": False,
    }
