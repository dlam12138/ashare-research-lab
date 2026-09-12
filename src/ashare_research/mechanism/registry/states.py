"""Closed M4-B state machine and evidence-registration gates."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, replace
from typing import Any

from .records import (
    _EXECUTION_EVIDENCE,
    _IDENTIFIER_RE,
    EvidenceKind,
    HypothesisRecordV1,
    RegistryError,
    StateTransitionV1,
    _fail,
    hypothesis_record_digest,
    hypothesis_record_identity_digest,
    validate_hypothesis_record,
)

LEGAL_TRANSITIONS = {
    "DISCOVERED": ("LITERATURE_REVIEWED", "DEFERRED"),
    "LITERATURE_REVIEWED": ("A_SHARE_FEASIBILITY_REVIEWED", "DEFERRED"),
    "A_SHARE_FEASIBILITY_REVIEWED": ("NOT_TESTED", "DEFERRED"),
    "NOT_TESTED": ("PRE_REGISTERED", "DEFERRED"),
    "PRE_REGISTERED": ("DEVELOPMENT_EXECUTED", "DEFERRED"),
    "DEVELOPMENT_EXECUTED": ("ROBUSTNESS_EXECUTED", "NOT_ESTABLISHED", "INCONCLUSIVE"),
    "ROBUSTNESS_EXECUTED": ("OOS_EXECUTED", "NOT_ESTABLISHED", "INCONCLUSIVE"),
    "OOS_EXECUTED": ("NOT_ESTABLISHED", "ESTABLISHED", "INCONCLUSIVE"),
    "NOT_ESTABLISHED": (),
    "ESTABLISHED": (),
    "INCONCLUSIVE": (),
    "DEFERRED": ("NOT_TESTED",),
}
TERMINAL_STATES = {"NOT_ESTABLISHED", "ESTABLISHED", "INCONCLUSIVE"}
_REASON_BY_TARGET = {
    "LITERATURE_REVIEWED": {"SOURCE_REVIEWED"},
    "A_SHARE_FEASIBILITY_REVIEWED": {"FEASIBILITY_ASSESSED"},
    "NOT_TESTED": {"CANDIDATE_REGISTERED", "DEFERRED_BY_REVIEW"},
    "PRE_REGISTERED": {"PRE_REGISTRATION_REGISTERED"},
    "DEVELOPMENT_EXECUTED": {"DEVELOPMENT_COMPLETED"},
    "ROBUSTNESS_EXECUTED": {"ROBUSTNESS_COMPLETED"},
    "OOS_EXECUTED": {"OOS_COMPLETED"},
    "NOT_ESTABLISHED": {"EVIDENCE_NOT_SUPPORTED"},
    "ESTABLISHED": {"EVIDENCE_SUPPORTED"},
    "INCONCLUSIVE": {"EVIDENCE_INCONCLUSIVE"},
    "DEFERRED": {"DEFERRED_BY_REVIEW"},
}


@dataclass(frozen=True)
class StateTransitionRequestV1:
    hypothesis_id: str
    hypothesis_version: int
    from_state: str
    to_state: str
    reason_code: str
    authorization_ref: str | None
    evidence_kind: str | None


REQUEST_FIELDS = tuple(StateTransitionRequestV1.__dataclass_fields__)


def _history(record: HypothesisRecordV1 | Mapping[str, Any]) -> tuple[StateTransitionV1, ...]:
    raw = (
        record.state_history if isinstance(record, HypothesisRecordV1) else record["state_history"]
    )
    return tuple(
        item if isinstance(item, StateTransitionV1) else StateTransitionV1(**item) for item in raw
    )


def _complete_evidence(
    history: tuple[StateTransitionV1, ...], current_status: str, reason: str
) -> bool:
    wanted = (
        ("DEVELOPMENT_EXECUTED", EvidenceKind.FROZEN_DEVELOPMENT_EVIDENCE.value),
        ("ROBUSTNESS_EXECUTED", EvidenceKind.REGISTERED_ROBUSTNESS_EVIDENCE.value),
        ("OOS_EXECUTED", EvidenceKind.INDEPENDENT_OOS_EVIDENCE.value),
    )
    found: list[StateTransitionV1] = []
    cursor = -1
    for state, evidence in wanted:
        match = next(
            (
                item
                for item in history[cursor + 1 :]
                if item.to_state == state
                and item.evidence_kind == evidence
                and item.authorization_ref
            ),
            None,
        )
        if match is None:
            return False
        cursor = history.index(match)
        found.append(match)
    return (
        current_status == "OOS_EXECUTED"
        and len({item.authorization_ref for item in found}) == 3
        and reason == "EVIDENCE_SUPPORTED"
        and not any(
            item.reason_code in {"EVIDENCE_NOT_SUPPORTED", "EVIDENCE_INCONCLUSIVE"}
            for item in history
        )
    )


def validate_record_state(record: HypothesisRecordV1 | Mapping[str, Any]) -> None:
    status = record.status if isinstance(record, HypothesisRecordV1) else record["status"]
    history = _history(record)
    for index, item in enumerate(history, 1):
        if item.ordinal != index:
            _fail("STATE_HISTORY_INCONSISTENT")
        if index == 1:
            if item.from_state is not None:
                _fail("STATE_HISTORY_INCONSISTENT")
        elif item.from_state != history[index - 2].to_state:
            _fail("STATE_HISTORY_INCONSISTENT")
    if not history or history[-1].to_state != status:
        _fail("STATE_HISTORY_INCONSISTENT")

    if status == "ESTABLISHED":
        final = history[-1]
        if not _complete_evidence(history[:-1], final.from_state or "", final.reason_code):
            _fail("ESTABLISHED_EVIDENCE_INCOMPLETE")
    for index, item in enumerate(history):
        if index == 0:
            if item.to_state != "DISCOVERED":
                _fail("ILLEGAL_STATE_TRANSITION")
            continue
        if item.from_state in TERMINAL_STATES:
            _fail("TERMINAL_STATE_HAS_NO_OUTGOING_TRANSITION")
        if item.to_state not in LEGAL_TRANSITIONS.get(item.from_state or "", ()):
            _fail("ILLEGAL_STATE_TRANSITION")
        if item.reason_code not in _REASON_BY_TARGET[item.to_state]:
            _fail("ILLEGAL_STATE_TRANSITION")
        if item.to_state == "NOT_TESTED":
            expected = (
                "DEFERRED_BY_REVIEW" if item.from_state == "DEFERRED" else "CANDIDATE_REGISTERED"
            )
            if item.reason_code != expected:
                _fail("ILLEGAL_STATE_TRANSITION")
        if item.to_state in _EXECUTION_EVIDENCE:
            if not item.authorization_ref:
                _fail("MISSING_AUTHORIZATION_REF")
            if item.evidence_kind != _EXECUTION_EVIDENCE[item.to_state]:
                _fail("ILLEGAL_STATE_TRANSITION")


def _request(value: StateTransitionRequestV1 | Mapping[str, Any]) -> StateTransitionRequestV1:
    if isinstance(value, StateTransitionRequestV1):
        return value
    if not isinstance(value, Mapping):
        _fail("INVALID_RECORD_STRUCTURE")
    if set(value) - set(REQUEST_FIELDS):
        _fail("UNKNOWN_RECORD_FIELD")
    if set(REQUEST_FIELDS) - set(value):
        _fail("MISSING_REQUIRED_FIELD")
    try:
        return StateTransitionRequestV1(**value)
    except TypeError:
        _fail("INVALID_FIELD_TYPE")


def validate_state_transition(
    record: HypothesisRecordV1, request: StateTransitionRequestV1 | Mapping[str, Any]
) -> None:
    validate_hypothesis_record(record)
    req = _request(request)
    if not all(
        isinstance(value, str)
        for value in (req.hypothesis_id, req.from_state, req.to_state, req.reason_code)
    ):
        _fail("INVALID_FIELD_TYPE")
    if type(req.hypothesis_version) is not int:
        _fail("INVALID_FIELD_TYPE")
    if req.authorization_ref is not None and not isinstance(req.authorization_ref, str):
        _fail("INVALID_FIELD_TYPE")
    if req.evidence_kind is not None and not isinstance(req.evidence_kind, str):
        _fail("INVALID_FIELD_TYPE")
    if (
        req.hypothesis_id != record.hypothesis_id
        or req.hypothesis_version != record.hypothesis_version
        or req.from_state != record.status
    ):
        _fail("ILLEGAL_STATE_TRANSITION")
    if req.from_state in TERMINAL_STATES:
        _fail("TERMINAL_STATE_HAS_NO_OUTGOING_TRANSITION")
    if req.to_state == "ESTABLISHED" and not _complete_evidence(
        record.state_history, record.status, req.reason_code
    ):
        _fail("ESTABLISHED_EVIDENCE_INCOMPLETE")
    if req.to_state not in LEGAL_TRANSITIONS.get(req.from_state, ()):
        _fail("ILLEGAL_STATE_TRANSITION")
    if req.reason_code not in _REASON_BY_TARGET.get(req.to_state, set()):
        _fail("ILLEGAL_STATE_TRANSITION")
    if req.to_state in _EXECUTION_EVIDENCE:
        if not req.authorization_ref:
            _fail("MISSING_AUTHORIZATION_REF")
        if not _IDENTIFIER_RE.fullmatch(req.authorization_ref):
            _fail("INVALID_IDENTIFIER")
        if req.evidence_kind != _EXECUTION_EVIDENCE[req.to_state]:
            _fail("ILLEGAL_STATE_TRANSITION")
    elif req.authorization_ref is not None or req.evidence_kind is not None:
        _fail("INVALID_FIELD_TYPE")
    if (
        req.to_state == "A_SHARE_FEASIBILITY_REVIEWED"
        and record.a_share_data_feasibility == "UNKNOWN"
        and record.free_data_feasibility == "UNKNOWN"
    ):
        _fail("ILLEGAL_STATE_TRANSITION")
    if req.to_state == "NOT_TESTED":
        expected = "DEFERRED_BY_REVIEW" if req.from_state == "DEFERRED" else "CANDIDATE_REGISTERED"
        if req.reason_code != expected:
            _fail("ILLEGAL_STATE_TRANSITION")


def transition_hypothesis_record(
    record: HypothesisRecordV1, request: StateTransitionRequestV1 | Mapping[str, Any]
) -> HypothesisRecordV1:
    validate_state_transition(record, request)
    req = _request(request)
    item = StateTransitionV1(
        ordinal=len(record.state_history) + 1,
        from_state=req.from_state,
        to_state=req.to_state,
        reason_code=req.reason_code,
        authorization_ref=req.authorization_ref,
        evidence_kind=req.evidence_kind,
    )
    candidate = replace(record, status=req.to_state, state_history=record.state_history + (item,))
    identity = hypothesis_record_identity_digest(candidate)
    candidate = replace(candidate, identity_digest=identity)
    candidate = replace(candidate, record_digest=hypothesis_record_digest(candidate))
    validate_hypothesis_record(candidate)
    if identity != record.identity_digest:
        raise RegistryError("PROVENANCE_REWRITE")
    return candidate
