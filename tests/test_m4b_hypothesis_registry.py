from __future__ import annotations

import inspect
import os
import subprocess
import sys
from dataclasses import FrozenInstanceError, replace
from pathlib import Path

import pytest

import ashare_research.mechanism.registry as registry
from ashare_research.mechanism import hypothesis_config
from ashare_research.mechanism.contracts import RESTRICTED_RESEARCH_OUTPUT_KEYS
from ashare_research.mechanism.execution.bounded import FORBIDDEN_KEYS
from ashare_research.mechanism.registry import (
    DIGEST_ALGORITHM_ID,
    LEGAL_TRANSITIONS,
    RECORD_SCHEMA_VERSION,
    RegistryError,
    StateTransitionRequestV1,
    build_hypothesis_registry_snapshot,
    hypothesis_record_digest,
    hypothesis_record_identity_digest,
    hypothesis_record_to_canonical_dict,
    parse_hypothesis_record,
    records,
    serialize_hypothesis_record,
    serialize_hypothesis_registry_snapshot,
    transition_hypothesis_record,
    validate_hypothesis_record,
)

ROOT = Path(__file__).resolve().parents[1]


def _doc(identifier: str = "synthetic.h1", version: int = 1) -> dict[str, object]:
    return {
        "schema_version": RECORD_SCHEMA_VERSION,
        "hypothesis_id": identifier,
        "hypothesis_version": version,
        "source_type": "TEXTBOOK_THEORY",
        "source_title": "SYNTHETIC_EXAMPLE_TITLE",
        "authors_or_issuer": "SYNTHETIC_EXAMPLE_ISSUER",
        "source_date": "2000-01-01",
        "citation_or_source_identity": "SYNTHETIC_EXAMPLE_IDENTITY",
        "source_version": "SYNTHETIC_EXAMPLE_EDITION",
        "source_notes": "",
        "theory": "SYNTHETIC_EXAMPLE_THEORY",
        "original_market": "SYNTHETIC_EXAMPLE_MARKET",
        "original_sample": "SYNTHETIC_EXAMPLE_SAMPLE",
        "expected_direction": "POSITIVE",
        "candidate_signal": "SYNTHETIC_EXAMPLE_SIGNAL_TEXT",
        "target_horizon": "SYNTHETIC_EXAMPLE_HORIZON",
        "known_controls": ("SYNTHETIC_EXAMPLE_CONTROL",),
        "known_alternative_explanations": ("SYNTHETIC_EXAMPLE_ALT",),
        "known_replications": ("SYNTHETIC_EXAMPLE_REPLICATION",),
        "known_failures_or_decay": (),
        "a_share_data_feasibility": "FEASIBLE_FREE",
        "free_data_feasibility": "SUFFICIENT",
        "status": "DISCOVERED",
        "state_history": (
            {
                "ordinal": 1,
                "from_state": None,
                "to_state": "DISCOVERED",
                "reason_code": "SOURCE_REVIEWED",
                "authorization_ref": None,
                "evidence_kind": None,
            },
        ),
        "identity_digest": "0" * 64,
        "record_digest": "0" * 64,
    }


def _record(identifier: str = "synthetic.h1", version: int = 1, **changes: object):
    doc = _doc(identifier, version)
    doc.update(changes)
    doc["identity_digest"] = hypothesis_record_identity_digest(doc)
    doc["record_digest"] = hypothesis_record_digest(doc)
    return parse_hypothesis_record(doc)


def _request(record, to_state: str, reason: str, *, auth=None, evidence=None):
    return StateTransitionRequestV1(
        record.hypothesis_id,
        record.hypothesis_version,
        record.status,
        to_state,
        reason,
        auth,
        evidence,
    )


def _advance(record, to_state: str, reason: str, *, auth=None, evidence=None):
    return transition_hypothesis_record(
        record, _request(record, to_state, reason, auth=auth, evidence=evidence)
    )


def _to_oos(refs=("development-contract", "robustness-contract", "oos-contract")):
    record = _record()
    sequence = (
        ("LITERATURE_REVIEWED", "SOURCE_REVIEWED", None, None),
        ("A_SHARE_FEASIBILITY_REVIEWED", "FEASIBILITY_ASSESSED", None, None),
        ("NOT_TESTED", "CANDIDATE_REGISTERED", None, None),
        ("PRE_REGISTERED", "PRE_REGISTRATION_REGISTERED", None, None),
        ("DEVELOPMENT_EXECUTED", "DEVELOPMENT_COMPLETED", refs[0], "FROZEN_DEVELOPMENT_EVIDENCE"),
        ("ROBUSTNESS_EXECUTED", "ROBUSTNESS_COMPLETED", refs[1], "REGISTERED_ROBUSTNESS_EVIDENCE"),
        ("OOS_EXECUTED", "OOS_COMPLETED", refs[2], "INDEPENDENT_OOS_EVIDENCE"),
    )
    for state, reason, auth, evidence in sequence:
        record = _advance(record, state, reason, auth=auth, evidence=evidence)
    return record


def _error(code: str, callable_, *args):
    with pytest.raises(RegistryError) as caught:
        callable_(*args)
    assert caught.value.code == code


def test_ac01_valid_synthetic_record_round_trip():
    record = _record()
    assert len(hypothesis_record_to_canonical_dict(record)) == 26
    assert parse_hypothesis_record(serialize_hypothesis_record(record)) == record
    assert len(record.identity_digest) == len(record.record_digest) == 64


def test_ac02_unknown_source_type():
    _error(
        "UNKNOWN_SOURCE_TYPE", hypothesis_record_identity_digest, {**_doc(), "source_type": "OTHER"}
    )
    _error("INVALID_FIELD_TYPE", hypothesis_record_identity_digest, {**_doc(), "source_type": 123})


def test_ac03_missing_provenance():
    bad = _doc()
    del bad["source_version"]
    _error("MISSING_REQUIRED_FIELD", hypothesis_record_identity_digest, bad)
    _error(
        "MISSING_PROVENANCE_FIELD",
        hypothesis_record_identity_digest,
        {**_doc(), "source_version": ""},
    )


def test_ac04_forbidden_canonical_source():
    _error(
        "FORBIDDEN_CANONICAL_SOURCE",
        hypothesis_record_identity_digest,
        {**_doc(), "source_notes": "PIRATED COPY"},
    )
    _error(
        "FORBIDDEN_CANONICAL_SOURCE",
        hypothesis_record_identity_digest,
        {**_doc(), "source_version": "UNKNOWN"},
    )
    for marker in ("MODEL", "AI", "MEMORY"):
        _error(
            "FORBIDDEN_CANONICAL_SOURCE",
            hypothesis_record_identity_digest,
            {**_doc(), "citation_or_source_identity": marker},
        )


def test_ac05_unknown_top_level_and_nested_keys():
    _error("UNKNOWN_RECORD_FIELD", hypothesis_record_identity_digest, {**_doc(), "outcome": 1})
    doc = _doc()
    doc["state_history"] = ({**doc["state_history"][0], "note": "x"},)
    _error("UNKNOWN_RECORD_FIELD", hypothesis_record_identity_digest, doc)


def test_ac06_strict_bool_int_and_numeric_handling():
    _error(
        "INVALID_FIELD_TYPE",
        hypothesis_record_identity_digest,
        {**_doc(), "hypothesis_version": True},
    )
    _error(
        "INVALID_FIELD_TYPE",
        hypothesis_record_identity_digest,
        {**_doc(), "hypothesis_version": 1.0},
    )


def test_ac07_illegal_transition_and_from_mismatch():
    record = _record()
    _error(
        "ILLEGAL_STATE_TRANSITION",
        transition_hypothesis_record,
        record,
        _request(record, "NOT_TESTED", "CANDIDATE_REGISTERED"),
    )
    bad = replace(
        _request(record, "LITERATURE_REVIEWED", "SOURCE_REVIEWED"), from_state="NOT_TESTED"
    )
    _error("ILLEGAL_STATE_TRANSITION", transition_hypothesis_record, record, bad)


def test_ac08_established_needs_complete_distinct_evidence():
    record = _to_oos(("same", "same", "same"))
    _error(
        "ESTABLISHED_EVIDENCE_INCOMPLETE",
        transition_hypothesis_record,
        record,
        _request(record, "ESTABLISHED", "EVIDENCE_SUPPORTED"),
    )
    established = _advance(_to_oos(), "ESTABLISHED", "EVIDENCE_SUPPORTED")
    assert established.status == "ESTABLISHED"
    validate_hypothesis_record(established)


def test_ac09_outcome_and_environment_fields_fail_closed():
    _error("UNKNOWN_RECORD_FIELD", hypothesis_record_identity_digest, {**_doc(), "p_value": 0})
    _error(
        "FORBIDDEN_VALUE",
        hypothesis_record_identity_digest,
        {**_doc(), "source_notes": "C:\\secret"},
    )


def test_ac10_scale_is_a_hard_ceiling():
    records_ = tuple(_record(f"synthetic.h{i}") for i in range(4))
    _error("SCALE_LIMIT_EXCEEDED", build_hypothesis_registry_snapshot, records_)


def test_ac11_duplicate_id_is_unambiguous():
    record = _record()
    _error("DUPLICATE_HYPOTHESIS_ID", build_hypothesis_registry_snapshot, (record, record))


def test_ac12_and_13_canonical_bytes_are_order_and_cwd_independent(tmp_path, monkeypatch):
    record = _record()
    expected = serialize_hypothesis_record(record)
    reordered = dict(reversed(list(hypothesis_record_to_canonical_dict(record).items())))
    for name in (
        "known_controls",
        "known_alternative_explanations",
        "known_replications",
        "known_failures_or_decay",
        "state_history",
    ):
        reordered[name] = tuple(reordered[name])
    assert serialize_hypothesis_record(parse_hypothesis_record(reordered)) == expected
    monkeypatch.chdir(tmp_path)
    assert serialize_hypothesis_record(record) == expected
    child = (
        "import sys; from ashare_research.mechanism.registry import "
        "parse_hypothesis_record,serialize_hypothesis_record; "
        "data=bytes.fromhex(sys.argv[1]); "
        "sys.stdout.write(serialize_hypothesis_record(parse_hypothesis_record(data)).hex())"
    )
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT / "src")
    completed = subprocess.run(
        [sys.executable, "-c", child, expected.hex()],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        check=True,
        text=True,
    )
    assert completed.stdout == expected.hex()


def test_ac14_nested_identity_mutation_and_status_transition():
    record = _record()
    tampered = replace(record, known_controls=("CHANGED",))
    _error("IDENTITY_DIGEST_MISMATCH", validate_hypothesis_record, tampered)
    updated = _advance(record, "LITERATURE_REVIEWED", "SOURCE_REVIEWED")
    assert updated.identity_digest == record.identity_digest
    assert updated.record_digest != record.record_digest


def test_ac15_registry_is_metadata_only():
    snapshot = build_hypothesis_registry_snapshot((_record(),))
    payload = serialize_hypothesis_registry_snapshot(snapshot)
    assert b'"interpretation_boundary"' in payload
    assert not any(
        isinstance(value, float)
        for value in hypothesis_record_to_canonical_dict(snapshot.records[0]).values()
    )


@pytest.mark.parametrize("bad", [[], "x", None, 1])
def test_ac16_fail_closed_read_paths(bad):
    _error("INVALID_RECORD_STRUCTURE", parse_hypothesis_record, bad)


def test_ac17_execution_requires_authorization_and_exact_evidence():
    record = _record()
    _error(
        "ILLEGAL_STATE_TRANSITION",
        transition_hypothesis_record,
        record,
        _request(record, "DEVELOPMENT_EXECUTED", "DEVELOPMENT_COMPLETED"),
    )
    for state, reason in (
        ("LITERATURE_REVIEWED", "SOURCE_REVIEWED"),
        ("A_SHARE_FEASIBILITY_REVIEWED", "FEASIBILITY_ASSESSED"),
        ("NOT_TESTED", "CANDIDATE_REGISTERED"),
        ("PRE_REGISTERED", "PRE_REGISTRATION_REGISTERED"),
    ):
        record = _advance(record, state, reason)
    _error(
        "MISSING_AUTHORIZATION_REF",
        transition_hypothesis_record,
        record,
        _request(
            record,
            "DEVELOPMENT_EXECUTED",
            "DEVELOPMENT_COMPLETED",
            evidence="FROZEN_DEVELOPMENT_EVIDENCE",
        ),
    )


def test_ac18_terminal_and_deferred_rules():
    record = _advance(_record(), "DEFERRED", "DEFERRED_BY_REVIEW")
    recovered = _advance(record, "NOT_TESTED", "DEFERRED_BY_REVIEW")
    assert recovered.status == "NOT_TESTED"
    terminal = _advance(
        _to_oos(),
        "NOT_ESTABLISHED",
        "EVIDENCE_NOT_SUPPORTED",
    )
    _error(
        "TERMINAL_STATE_HAS_NO_OUTGOING_TRANSITION",
        transition_hypothesis_record,
        terminal,
        _request(terminal, "ESTABLISHED", "EVIDENCE_SUPPORTED"),
    )


def test_ac19_rewrite_rejected_and_version_is_distinct():
    first = _record()
    changed = _record(source_title="CHANGED")
    _error("PROVENANCE_REWRITE", build_hypothesis_registry_snapshot, (first, changed))
    assert len(build_hypothesis_registry_snapshot((first, _record(version=2))).records) == 2


def test_ac20_validation_is_idempotent_and_side_effect_free():
    record = _record()
    before = serialize_hypothesis_record(record)
    validate_hypothesis_record(record)
    validate_hypothesis_record(record)
    assert serialize_hypothesis_record(record) == before
    with pytest.raises(FrozenInstanceError):
        record.status = "NOT_TESTED"


def test_ac21_literature_is_not_local_evidence():
    record = _record(source_type="ACADEMIC_PAPER", source_version="PUBLISHED")
    assert record.status == "DISCOVERED"
    assert "Not evidence" in build_hypothesis_registry_snapshot((record,)).interpretation_boundary


def test_ac22_public_surface_import_boundary_and_twenty_edges():
    public_functions = {
        name for name in registry.__all__ if inspect.isfunction(getattr(registry, name))
    }
    assert len(public_functions) == 13
    assert all(
        "kwargs" not in str(inspect.signature(getattr(registry, name))) for name in public_functions
    )
    assert sum(map(len, LEGAL_TRANSITIONS.values())) == 20
    assert records._IDENTIFIER_RE.pattern == hypothesis_config._IDENTIFIER_RE.pattern
    assert DIGEST_ALGORITHM_ID == "M4_HYPOTHESIS_REGISTRY_SHA256_CANONICAL_JSON_V1"
    normalize = records._normalized_key
    assert {normalize(key) for key in RESTRICTED_RESEARCH_OUTPUT_KEYS} <= (
        records._FORBIDDEN_OUTCOME_KEYS
    )
    assert {normalize(key) for key in FORBIDDEN_KEYS} <= records._FORBIDDEN_ENVIRONMENT_KEYS
