"""Immutable, metadata-only M4-B hypothesis records."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from dataclasses import dataclass, fields
from datetime import date
from enum import Enum
from typing import Any

from ashare_research.mechanism.model_digest import canonical_digest

RECORD_SCHEMA_VERSION = "M4_HYPOTHESIS_REGISTRY_RECORD_V1"
DIGEST_ALGORITHM_ID = "M4_HYPOTHESIS_REGISTRY_SHA256_CANONICAL_JSON_V1"
MAX_IDENTITY_DIGEST_LEN = 64
HYPOTHESIS_ID_MAX_LEN = 120
SHORT_TEXT_MAX_LEN = 500
LONG_TEXT_MAX_LEN = 2000
NOTES_MAX_LEN = 4000
CITATION_MAX_LEN = 1000
SOURCE_VERSION_MAX_LEN = 200
TARGET_HORIZON_MAX_LEN = 100
MAX_HYPOTHESIS_VERSION = 1000
UNKNOWN_SENTINEL = "UNKNOWN"

_IDENTIFIER_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")
_DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")
_ABSOLUTE_PATH_RE = re.compile(r"(?:[A-Za-z]:[\\/])|(?:\\\\)|(?:/[^/\s]+)")
_CREDENTIAL_RE = re.compile(
    r"(?i)(?:\bbearer\s+\S)|(?:\b(?:api[_-]?key|password|passwd|secret|token|cookie)\b\s*[:=])"
)


class RegistryError(ValueError):
    """Stable fail-closed registry error."""

    def __init__(self, code: str, message: str | None = None) -> None:
        self.code = code
        super().__init__(message or code)


class SourceType(Enum):
    PERSONAL_OBSERVATION = "PERSONAL_OBSERVATION"
    TEXTBOOK_THEORY = "TEXTBOOK_THEORY"
    ACADEMIC_PAPER = "ACADEMIC_PAPER"
    KNOWN_ANOMALY = "KNOWN_ANOMALY"
    OFFICIAL_MECHANISM = "OFFICIAL_MECHANISM"
    REPLICATION_EXTENSION = "REPLICATION_EXTENSION"


class ExpectedDirection(Enum):
    POSITIVE = "POSITIVE"
    NEGATIVE = "NEGATIVE"
    TWO_SIDED = "TWO_SIDED"


class AShareDataFeasibility(Enum):
    FEASIBLE_FREE = "FEASIBLE_FREE"
    FEASIBLE_PAID = "FEASIBLE_PAID"
    NOT_FEASIBLE = "NOT_FEASIBLE"
    UNKNOWN = "UNKNOWN"


class FreeDataFeasibility(Enum):
    SUFFICIENT = "SUFFICIENT"
    PARTIAL = "PARTIAL"
    INSUFFICIENT = "INSUFFICIENT"
    UNKNOWN = "UNKNOWN"


class HypothesisState(Enum):
    DISCOVERED = "DISCOVERED"
    LITERATURE_REVIEWED = "LITERATURE_REVIEWED"
    A_SHARE_FEASIBILITY_REVIEWED = "A_SHARE_FEASIBILITY_REVIEWED"
    NOT_TESTED = "NOT_TESTED"
    PRE_REGISTERED = "PRE_REGISTERED"
    DEVELOPMENT_EXECUTED = "DEVELOPMENT_EXECUTED"
    ROBUSTNESS_EXECUTED = "ROBUSTNESS_EXECUTED"
    OOS_EXECUTED = "OOS_EXECUTED"
    NOT_ESTABLISHED = "NOT_ESTABLISHED"
    ESTABLISHED = "ESTABLISHED"
    INCONCLUSIVE = "INCONCLUSIVE"
    DEFERRED = "DEFERRED"


class TransitionReasonCode(Enum):
    SOURCE_REVIEWED = "SOURCE_REVIEWED"
    FEASIBILITY_ASSESSED = "FEASIBILITY_ASSESSED"
    CANDIDATE_REGISTERED = "CANDIDATE_REGISTERED"
    PRE_REGISTRATION_REGISTERED = "PRE_REGISTRATION_REGISTERED"
    DEVELOPMENT_COMPLETED = "DEVELOPMENT_COMPLETED"
    ROBUSTNESS_COMPLETED = "ROBUSTNESS_COMPLETED"
    OOS_COMPLETED = "OOS_COMPLETED"
    EVIDENCE_NOT_SUPPORTED = "EVIDENCE_NOT_SUPPORTED"
    EVIDENCE_SUPPORTED = "EVIDENCE_SUPPORTED"
    EVIDENCE_INCONCLUSIVE = "EVIDENCE_INCONCLUSIVE"
    DEFERRED_BY_REVIEW = "DEFERRED_BY_REVIEW"


class EvidenceKind(Enum):
    FROZEN_DEVELOPMENT_EVIDENCE = "FROZEN_DEVELOPMENT_EVIDENCE"
    REGISTERED_ROBUSTNESS_EVIDENCE = "REGISTERED_ROBUSTNESS_EVIDENCE"
    INDEPENDENT_OOS_EVIDENCE = "INDEPENDENT_OOS_EVIDENCE"


@dataclass(frozen=True)
class StateTransitionV1:
    ordinal: int
    from_state: str | None
    to_state: str
    reason_code: str
    authorization_ref: str | None
    evidence_kind: str | None


@dataclass(frozen=True)
class HypothesisRecordV1:
    schema_version: str
    hypothesis_id: str
    hypothesis_version: int
    source_type: str
    source_title: str
    authors_or_issuer: str
    source_date: str
    citation_or_source_identity: str
    source_version: str
    source_notes: str
    theory: str
    original_market: str
    original_sample: str
    expected_direction: str
    candidate_signal: str
    target_horizon: str
    known_controls: tuple[str, ...]
    known_alternative_explanations: tuple[str, ...]
    known_replications: tuple[str, ...]
    known_failures_or_decay: tuple[str, ...]
    a_share_data_feasibility: str
    free_data_feasibility: str
    status: str
    state_history: tuple[StateTransitionV1, ...]
    identity_digest: str
    record_digest: str


RECORD_FIELDS = tuple(field.name for field in fields(HypothesisRecordV1))
TRANSITION_FIELDS = tuple(field.name for field in fields(StateTransitionV1))
IDENTITY_FIELDS = RECORD_FIELDS[:22]
_CONTAINER_FIELDS = (
    "known_controls",
    "known_alternative_explanations",
    "known_replications",
    "known_failures_or_decay",
    "state_history",
)
_TEXT_LIMITS = {
    "source_title": SHORT_TEXT_MAX_LEN,
    "authors_or_issuer": SHORT_TEXT_MAX_LEN,
    "citation_or_source_identity": CITATION_MAX_LEN,
    "source_version": SOURCE_VERSION_MAX_LEN,
    "source_notes": NOTES_MAX_LEN,
    "theory": LONG_TEXT_MAX_LEN,
    "original_market": SHORT_TEXT_MAX_LEN,
    "original_sample": LONG_TEXT_MAX_LEN,
    "candidate_signal": SHORT_TEXT_MAX_LEN,
    "target_horizon": TARGET_HORIZON_MAX_LEN,
}
_TUPLE_LIMITS = {
    "known_controls": SHORT_TEXT_MAX_LEN,
    "known_alternative_explanations": LONG_TEXT_MAX_LEN,
    "known_replications": SHORT_TEXT_MAX_LEN,
    "known_failures_or_decay": LONG_TEXT_MAX_LEN,
}
_SOURCE_TYPES = {item.value for item in SourceType}
_DIRECTIONS = {item.value for item in ExpectedDirection}
_A_SHARE_FEASIBILITY = {item.value for item in AShareDataFeasibility}
_FREE_FEASIBILITY = {item.value for item in FreeDataFeasibility}
_STATES = {item.value for item in HypothesisState}
_REASONS = {item.value for item in TransitionReasonCode}
_EVIDENCE_KINDS = {item.value for item in EvidenceKind}
_EXECUTION_EVIDENCE = {
    HypothesisState.DEVELOPMENT_EXECUTED.value: EvidenceKind.FROZEN_DEVELOPMENT_EVIDENCE.value,
    HypothesisState.ROBUSTNESS_EXECUTED.value: EvidenceKind.REGISTERED_ROBUSTNESS_EVIDENCE.value,
    HypothesisState.OOS_EXECUTED.value: EvidenceKind.INDEPENDENT_OOS_EVIDENCE.value,
}
_FORBIDDEN_OUTCOME_KEYS = {
    "abnormalreturn",
    "abnormalreturns",
    "adjrsquared",
    "alpha",
    "beta",
    "best",
    "bestresult",
    "bootstrapresult",
    "ci",
    "cilower",
    "ciupper",
    "coef",
    "coefficient",
    "coefficients",
    "conclusion",
    "confidence",
    "confidenceinterval",
    "confirmed",
    "correlation",
    "crashdaycount",
    "disposition",
    "drawdown",
    "effectsize",
    "estimate",
    "estimates",
    "evidence",
    "evidencelevel",
    "excessreturn",
    "finding",
    "findings",
    "fstat",
    "gamma",
    "hitrate",
    "interval",
    "outcome",
    "outcomes",
    "p",
    "pnl",
    "pointestimate",
    "positiveprobability",
    "profit",
    "proof",
    "pvalue",
    "pvalues",
    "rank",
    "ranking",
    "result",
    "results",
    "return",
    "returns",
    "robustresult",
    "rsquared",
    "score",
    "scores",
    "se",
    "selected",
    "sharpe",
    "significant",
    "significance",
    "stderr",
    "tstat",
    "tstatistic",
    "turnover",
    "validated",
    "verdict",
    "verified",
    "winner",
    "winrate",
    "zstat",
}
_FORBIDDEN_ENVIRONMENT_KEYS = {
    "hostname",
    "username",
    "user",
    "home",
    "cwd",
    "worktree",
    "path",
    "abspath",
    "absolutepath",
    "aggregate",
    "rootpath",
    "env",
    "environment",
    "session",
    "provider",
    "database",
    "best",
    "bestid",
    "bestresult",
    "selected",
    "selectedid",
    "winner",
    "sortkey",
    "tuned",
    "ranking",
    "promote",
    "optimize",
    "search",
}
_FORBIDDEN_CREDENTIAL_KEYS = {
    "apikey",
    "token",
    "secret",
    "cookie",
    "password",
    "passwd",
    "credential",
    "accesstoken",
    "refreshtoken",
    "privatekey",
}
_PIRATED_SOURCE_MARKERS = {
    "PIRATED",
    "PIRACY",
    "PHOTOCOPY",
    "TORRENT",
    "WAREZ",
    "SCAN",
    "NETDISK",
    "CLOUDDRIVE",
    "PDFAGGREGATOR",
}
_BLOG_SOURCE_MARKERS = {"BLOG", "FORUM", "CONTENTFARM", "SELFMEDIA"}
_LLM_MEMORY_MARKERS = {"LLM", "MODEL", "AI", "CHATGPT", "MEMORY", "RECALL"}


def _fail(code: str) -> None:
    raise RegistryError(code)


def _transition_dict(item: StateTransitionV1 | Mapping[str, Any]) -> dict[str, Any]:
    if isinstance(item, StateTransitionV1):
        return {name: getattr(item, name) for name in TRANSITION_FIELDS}
    return dict(item)


def _document(record: HypothesisRecordV1 | Mapping[str, Any]) -> dict[str, Any]:
    if isinstance(record, HypothesisRecordV1):
        return {name: getattr(record, name) for name in RECORD_FIELDS}
    if isinstance(record, Mapping):
        return dict(record)
    _fail("INVALID_RECORD_STRUCTURE")


def _pure_dict(
    record: HypothesisRecordV1 | Mapping[str, Any], *, include_digests: bool = True
) -> dict[str, Any]:
    doc = _document(record)
    result: dict[str, Any] = {}
    for name in RECORD_FIELDS:
        if not include_digests and name in {"identity_digest", "record_digest"}:
            continue
        value = doc[name]
        if name == "state_history":
            result[name] = [_transition_dict(item) for item in value]
        elif name in _TUPLE_LIMITS:
            result[name] = list(value)
        else:
            result[name] = value
    return result


def _valid_text(value: str) -> bool:
    if value and value != value.strip():
        return False
    for char in value:
        code = ord(char)
        if code < 0x20 or code == 0x7F or 0x80 <= code <= 0x9F:
            return False
        if char in {"\u200b", "\u200c", "\u200d", "\u2060", "\ufeff"}:
            return False
        if 0xFDD0 <= code <= 0xFDEF or (code & 0xFFFE) == 0xFFFE:
            return False
    return True


def _normalized_key(key: str) -> str:
    return re.sub(r"[-_ ]", "", key.lower())


def _scan_keys(value: Any, forbidden: set[str]) -> bool:
    if isinstance(value, Mapping):
        return any(
            _normalized_key(str(key)) in forbidden or _scan_keys(child, forbidden)
            for key, child in value.items()
        )
    if isinstance(value, (tuple, list)):
        return any(_scan_keys(child, forbidden) for child in value)
    return False


def _scan_values(value: Any) -> bool:
    if isinstance(value, str):
        return bool(_ABSOLUTE_PATH_RE.search(value) or _CREDENTIAL_RE.search(value))
    if isinstance(value, Mapping):
        return any(_scan_values(child) for child in value.values())
    if isinstance(value, (tuple, list)):
        return any(_scan_values(child) for child in value)
    return False


def _validate_v1_v8(record: HypothesisRecordV1 | Mapping[str, Any]) -> dict[str, Any]:
    doc = _document(record)
    for name in _CONTAINER_FIELDS:
        if name in doc and not isinstance(doc[name], tuple):
            _fail("INVALID_RECORD_STRUCTURE")
    if (
        "state_history" in doc
        and isinstance(doc["state_history"], tuple)
        and any(not isinstance(item, (StateTransitionV1, Mapping)) for item in doc["state_history"])
    ):
        _fail("INVALID_RECORD_STRUCTURE")

    extra = set(doc) - set(RECORD_FIELDS)
    if extra:
        _fail("UNKNOWN_RECORD_FIELD")
    missing = set(RECORD_FIELDS) - set(doc)
    if missing:
        _fail("MISSING_REQUIRED_FIELD")
    history = tuple(_transition_dict(item) for item in doc["state_history"])
    for item in history:
        if set(item) - set(TRANSITION_FIELDS):
            _fail("UNKNOWN_RECORD_FIELD")
        if set(TRANSITION_FIELDS) - set(item):
            _fail("MISSING_REQUIRED_FIELD")

    string_fields = [
        name
        for name in RECORD_FIELDS
        if name not in _CONTAINER_FIELDS and name != "hypothesis_version"
    ]
    for name in string_fields:
        if not isinstance(doc[name], str):
            _fail("INVALID_FIELD_TYPE")
        if not _valid_text(doc[name]):
            _fail("INVALID_FIELD_TYPE")
    if type(doc["hypothesis_version"]) is not int:
        _fail("INVALID_FIELD_TYPE")
    for name in _TUPLE_LIMITS:
        for item in doc[name]:
            if not isinstance(item, str) or not _valid_text(item):
                _fail("INVALID_FIELD_TYPE")
    for item in history:
        if type(item["ordinal"]) is not int:
            _fail("INVALID_FIELD_TYPE")
        for name in ("to_state", "reason_code"):
            if not isinstance(item[name], str):
                _fail("INVALID_FIELD_TYPE")
        for name in ("from_state", "authorization_ref", "evidence_kind"):
            if item[name] is not None and not isinstance(item[name], str):
                _fail("INVALID_FIELD_TYPE")
        execution = item["to_state"] in _EXECUTION_EVIDENCE
        if not execution and (
            item["authorization_ref"] is not None or item["evidence_kind"] is not None
        ):
            _fail("INVALID_FIELD_TYPE")

    if not _IDENTIFIER_RE.fullmatch(doc["hypothesis_id"]):
        _fail("INVALID_IDENTIFIER")
    if len(doc["hypothesis_id"]) > HYPOTHESIS_ID_MAX_LEN:
        _fail("INVALID_FIELD_LENGTH")
    if not 1 <= doc["hypothesis_version"] <= MAX_HYPOTHESIS_VERSION:
        _fail("INVALID_FIELD_LENGTH")
    for name, maximum in _TEXT_LIMITS.items():
        minimum = (
            0 if name in {"source_notes", "citation_or_source_identity", "source_version"} else 1
        )
        if not minimum <= len(doc[name]) <= maximum:
            _fail("INVALID_FIELD_LENGTH")
    for name, maximum in _TUPLE_LIMITS.items():
        if any(not 1 <= len(item) <= maximum for item in doc[name]):
            _fail("INVALID_FIELD_LENGTH")
    if not history:
        _fail("INVALID_FIELD_LENGTH")
    for digest_name in ("identity_digest", "record_digest"):
        if len(doc[digest_name]) != MAX_IDENTITY_DIGEST_LEN:
            _fail("INVALID_FIELD_LENGTH")
    for item in history:
        ref = item["authorization_ref"]
        if ref not in {None, ""} and not _IDENTIFIER_RE.fullmatch(ref):
            _fail("INVALID_IDENTIFIER")

    if not doc["source_type"]:
        _fail("INVALID_FIELD_LENGTH")
    if doc["source_type"] not in _SOURCE_TYPES:
        _fail("UNKNOWN_SOURCE_TYPE")
    enum_checks = (
        (doc["expected_direction"], _DIRECTIONS),
        (doc["a_share_data_feasibility"], _A_SHARE_FEASIBILITY),
        (doc["free_data_feasibility"], _FREE_FEASIBILITY),
        (doc["status"], _STATES),
    )
    if any(value not in allowed for value, allowed in enum_checks):
        _fail("INVALID_ENUM_VALUE")
    for item in history:
        if item["to_state"] not in _STATES or (
            item["from_state"] is not None and item["from_state"] not in _STATES
        ):
            _fail("INVALID_ENUM_VALUE")
        if item["reason_code"] not in _REASONS:
            _fail("INVALID_ENUM_VALUE")
        if item["evidence_kind"] is not None and item["evidence_kind"] not in _EVIDENCE_KINDS:
            _fail("INVALID_ENUM_VALUE")

    raw_date = doc["source_date"]
    try:
        if re.fullmatch(r"\d{4}", raw_date):
            date(int(raw_date), 1, 1)
        elif re.fullmatch(r"\d{4}-\d{2}", raw_date):
            year, month = map(int, raw_date.split("-"))
            date(year, month, 1)
        elif re.fullmatch(r"\d{4}-\d{2}-\d{2}", raw_date):
            date.fromisoformat(raw_date)
        else:
            _fail("INVALID_DATE")
    except (ValueError, TypeError):
        _fail("INVALID_DATE")

    if not doc["citation_or_source_identity"] or not doc["source_version"]:
        _fail("MISSING_PROVENANCE_FIELD")
    source_text = " ".join(
        str(doc[name]).upper()
        for name in (
            "citation_or_source_identity",
            "source_title",
            "source_version",
            "source_notes",
        )
    )
    tokens = set(re.findall(r"[A-Z0-9]+", source_text))
    compact_source = _normalized_key(source_text)
    pirated = bool(tokens & _PIRATED_SOURCE_MARKERS) or any(
        marker in compact_source for marker in _PIRATED_SOURCE_MARKERS
    )
    blog = bool(tokens & _BLOG_SOURCE_MARKERS) or any(
        marker in compact_source for marker in _BLOG_SOURCE_MARKERS
    )
    llm_memory = bool(tokens & _LLM_MEMORY_MARKERS)
    if (pirated and doc["source_type"] == SourceType.TEXTBOOK_THEORY.value) or blog or llm_memory:
        _fail("FORBIDDEN_CANONICAL_SOURCE")
    if doc["source_version"] == UNKNOWN_SENTINEL and doc["source_type"] in {
        SourceType.TEXTBOOK_THEORY.value,
        SourceType.ACADEMIC_PAPER.value,
        SourceType.KNOWN_ANOMALY.value,
        SourceType.REPLICATION_EXTENSION.value,
    }:
        _fail("FORBIDDEN_CANONICAL_SOURCE")

    payload = _pure_dict(doc)
    if _scan_keys(payload, _FORBIDDEN_OUTCOME_KEYS):
        _fail("FORBIDDEN_OUTCOME_FIELD")
    if _scan_keys(payload, _FORBIDDEN_ENVIRONMENT_KEYS):
        _fail("FORBIDDEN_ENVIRONMENT_FIELD")
    if _scan_keys(payload, _FORBIDDEN_CREDENTIAL_KEYS) or _scan_values(payload):
        _fail("FORBIDDEN_VALUE")
    return doc


def hypothesis_record_identity_digest(record: HypothesisRecordV1 | Mapping[str, Any]) -> str:
    doc = _validate_v1_v8(record)
    payload = {"digest_algorithm": DIGEST_ALGORITHM_ID, "digest_scope": "identity_bearing_fields"}
    payload.update({name: _pure_dict(doc)[name] for name in IDENTITY_FIELDS})
    return canonical_digest(payload)


def hypothesis_record_digest(record: HypothesisRecordV1 | Mapping[str, Any]) -> str:
    doc = _validate_v1_v8(record)
    pure = _pure_dict(doc)
    payload = {"digest_algorithm": DIGEST_ALGORITHM_ID, "digest_scope": "full_record"}
    payload.update({name: pure[name] for name in IDENTITY_FIELDS})
    payload.update(
        identity_digest=hypothesis_record_identity_digest(doc),
        status=doc["status"],
        state_history=pure["state_history"],
    )
    return canonical_digest(payload)


def validate_hypothesis_record(record: HypothesisRecordV1 | Mapping[str, Any]) -> None:
    doc = _validate_v1_v8(record)
    from .states import validate_record_state

    validate_record_state(doc)
    identity = hypothesis_record_identity_digest(doc)
    if doc["identity_digest"] != identity or not _DIGEST_RE.fullmatch(doc["identity_digest"]):
        _fail("IDENTITY_DIGEST_MISMATCH")
    if doc["record_digest"] != hypothesis_record_digest(doc) or not _DIGEST_RE.fullmatch(
        doc["record_digest"]
    ):
        _fail("RECORD_DIGEST_MISMATCH")


def hypothesis_record_to_canonical_dict(
    record: HypothesisRecordV1 | Mapping[str, Any],
) -> dict[str, Any]:
    validate_hypothesis_record(record)
    return _pure_dict(record)


def serialize_hypothesis_record(record: HypothesisRecordV1 | Mapping[str, Any]) -> bytes:
    return (
        json.dumps(
            hypothesis_record_to_canonical_dict(record),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n"
    ).encode("utf-8")


def _from_document(doc: Mapping[str, Any]) -> HypothesisRecordV1:
    values = dict(doc)
    values["known_controls"] = tuple(values.get("known_controls", ()))
    values["known_alternative_explanations"] = tuple(
        values.get("known_alternative_explanations", ())
    )
    values["known_replications"] = tuple(values.get("known_replications", ()))
    values["known_failures_or_decay"] = tuple(values.get("known_failures_or_decay", ()))
    values["state_history"] = tuple(
        item if isinstance(item, StateTransitionV1) else StateTransitionV1(**item)
        for item in values.get("state_history", ())
    )
    return HypothesisRecordV1(**values)


def parse_hypothesis_record(document: bytes | Mapping[str, Any]) -> HypothesisRecordV1:
    if isinstance(document, bytes):
        if (
            document.startswith(b"\xef\xbb\xbf")
            or b"\r" in document
            or not document.endswith(b"\n")
            or document.endswith(b"\n\n")
        ):
            _fail("NON_CANONICAL_SERIALIZATION")
        try:
            text = document.decode("utf-8")
            loaded = json.loads(
                text, parse_float=lambda _value: _fail("NON_CANONICAL_SERIALIZATION")
            )
        except (UnicodeDecodeError, json.JSONDecodeError):
            _fail("NON_CANONICAL_SERIALIZATION")
        if not isinstance(loaded, Mapping):
            _fail("INVALID_RECORD_STRUCTURE")
        loaded = dict(loaded)
        for name in _TUPLE_LIMITS:
            if isinstance(loaded.get(name), list):
                loaded[name] = tuple(loaded[name])
        if isinstance(loaded.get("state_history"), list):
            loaded["state_history"] = tuple(loaded["state_history"])
        record = _from_document(loaded)
        validate_hypothesis_record(record)
        if serialize_hypothesis_record(record) != document:
            _fail("NON_CANONICAL_SERIALIZATION")
        return record
    if not isinstance(document, Mapping):
        _fail("INVALID_RECORD_STRUCTURE")
    validate_hypothesis_record(document)
    return _from_document(document)
