"""Read-only M4-B registry transition preflight: frozen codes, no writes."""

from __future__ import annotations

import hashlib
import inspect
import json
import re
import socket
from contextlib import contextmanager
from pathlib import Path

import duckdb

from ashare_research import cli
from ashare_research.mechanism import execution, pipeline, registry
from ashare_research.mechanism.registry import (
    RECORD_SCHEMA_VERSION,
    StateTransitionRequestV1,
    build_hypothesis_registry_snapshot,
    hypothesis_record_digest,
    hypothesis_record_identity_digest,
    parse_hypothesis_record,
    serialize_hypothesis_record,
    serialize_hypothesis_registry_snapshot,
    transition_hypothesis_record,
)
from ashare_research.tools import research_entry, research_registry

FORBIDDEN_NAMES = re.compile(r"scan|rank|sort|promote|advance|select|optimize|search|auto_")
PUBLIC_FUNCTIONS = {
    "build_hypothesis_registry_snapshot",
    "count_real_demo_candidates",
    "hypothesis_record_digest",
    "hypothesis_record_identity_digest",
    "hypothesis_record_to_canonical_dict",
    "parse_hypothesis_record",
    "registry_snapshot_to_canonical_dict",
    "serialize_hypothesis_record",
    "serialize_hypothesis_registry_snapshot",
    "transition_hypothesis_record",
    "validate_hypothesis_record",
    "validate_hypothesis_registry_snapshot",
    "validate_state_transition",
}
EXPECTED_REQUEST_FIELDS = (
    "hypothesis_id",
    "hypothesis_version",
    "from_state",
    "to_state",
    "reason_code",
    "authorization_ref",
    "evidence_kind",
)


def _doc(identifier: str, *, version: int = 1) -> dict:
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


def _record(identifier: str = "SYNTH_EXAMPLE_0001", *, version: int = 1):
    document = _doc(identifier, version=version)
    document["identity_digest"] = hypothesis_record_identity_digest(document)
    document["record_digest"] = hypothesis_record_digest(document)
    return parse_hypothesis_record(document)


def _advance(record, to_state: str, reason: str, *, auth=None, evidence=None):
    request = StateTransitionRequestV1(
        record.hypothesis_id,
        record.hypothesis_version,
        record.status,
        to_state,
        reason,
        auth,
        evidence,
    )
    return transition_hypothesis_record(record, request)


def _to_oos(record=None, refs=("development-contract", "robustness-contract", "oos-contract")):
    record = _record() if record is None else record
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


def _request_doc(record, to_state: str, reason: str, *, auth=None, evidence=None) -> dict:
    return {
        "hypothesis_id": record.hypothesis_id,
        "hypothesis_version": record.hypothesis_version,
        "from_state": record.status,
        "to_state": to_state,
        "reason_code": reason,
        "authorization_ref": auth,
        "evidence_kind": evidence,
    }


def _canonical(document) -> bytes:
    return (
        json.dumps(document, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
    ).encode("utf-8")


def _write(tmp_path: Path, name: str, payload: bytes) -> Path:
    path = tmp_path / name
    path.write_bytes(payload)
    return path


def _run_ok(args, capsys) -> str:
    assert cli.main(args) == 0
    captured = capsys.readouterr()
    assert captured.err == "" and captured.out
    return captured.out


def _rejected(args, code: str, capsys) -> None:
    assert cli.main(args) == 2
    captured = capsys.readouterr()
    assert captured.out == "" and captured.err == f"error: {code}\n"


def test_first_edge_acceptance_exact_receipt_and_entry_delegation(tmp_path, capsys):
    record = _record()
    record_payload = serialize_hypothesis_record(record)
    request = _request_doc(record, "LITERATURE_REVIEWED", "SOURCE_REVIEWED")
    request_payload = _canonical(request)
    source = _write(tmp_path, "record.json", record_payload)
    explicit = _write(tmp_path, "request.json", request_payload)
    before = (source.read_bytes(), explicit.read_bytes())

    expected = research_registry.build_transition_preflight(record_payload, request_payload)
    delegated = _run_ok(
        [
            "research",
            "registry",
            "--record",
            str(source),
            "--transition",
            str(explicit),
            "--json",
        ],
        capsys,
    )
    assert delegated == research_registry._json(expected) + "\n"
    assert (
        research_registry.main(
            ["--record", str(source), "--transition", str(explicit), "--json"]
        )
        == 0
    )
    direct = capsys.readouterr()
    assert direct.err == "" and direct.out == delegated
    assert (
        research_entry.main(["registry", "--record", str(source), "--transition", str(explicit),
                             "--json"])
        == 0
    )
    entry = capsys.readouterr()
    assert entry.err == "" and entry.out == delegated
    assert (source.read_bytes(), explicit.read_bytes()) == before

    view = json.loads(delegated)
    assert view["schema"] == research_registry.SCHEMA_TRANSITION_PREFLIGHT
    assert view["schema"] == "m4_registry_transition_preflight_v1"
    assert view["status"] == research_registry.PREFLIGHT_STATUS
    assert view["status"] == "accepted_preflight_only"
    assert view["source_file_sha256"] == hashlib.sha256(record_payload).hexdigest()
    assert view["request_file_sha256"] == hashlib.sha256(request_payload).hexdigest()
    assert view["record"] == {
        "hypothesis_id": "SYNTH_EXAMPLE_0001",
        "hypothesis_version": 1,
        "status": "DISCOVERED",
        "identity_digest": record.identity_digest,
        "record_digest": record.record_digest,
        "state_count": 1,
    }
    assert view["request"] == request
    assert set(view["request"]) == set(EXPECTED_REQUEST_FIELDS)
    assert tuple(expected["request"]) == EXPECTED_REQUEST_FIELDS
    assert view["result"] == {
        "accepted": True,
        "would_be_ordinal": 2,
        "would_be_status": "LITERATURE_REVIEWED",
    }
    assert view["boundary"] == {
        "execution_authorized": False,
        "statistics_computed": False,
        "outcome_read": False,
        "holdout_accessed": False,
        "real_registry_dataset_loaded": False,
        "registry_written": False,
    }
    assert view["notes"] == [
        *research_registry.PREFLIGHT_NOTES,
        *research_registry.COMMON_NOTES,
    ]
    applied = transition_hypothesis_record(record, request)
    assert applied.status == view["result"]["would_be_status"]
    assert len(applied.state_history) == view["result"]["would_be_ordinal"]

    markdown = _run_ok(
        ["research", "registry", "--record", str(source), "--transition", str(explicit)],
        capsys,
    )
    assert markdown == research_registry.render_transition_markdown(expected)
    assert "# M4-B 状态转换只读预检" in markdown
    assert '"would_be_status": "LITERATURE_REVIEWED"' in markdown
    assert "## 执行边界" in markdown and "## 限制" in markdown


def test_execution_edge_acceptance_exact_receipt(tmp_path, capsys):
    record = _record()
    for state, reason in (
        ("LITERATURE_REVIEWED", "SOURCE_REVIEWED"),
        ("A_SHARE_FEASIBILITY_REVIEWED", "FEASIBILITY_ASSESSED"),
        ("NOT_TESTED", "CANDIDATE_REGISTERED"),
        ("PRE_REGISTERED", "PRE_REGISTRATION_REGISTERED"),
    ):
        record = _advance(record, state, reason)
    assert record.status == "PRE_REGISTERED" and len(record.state_history) == 5
    record_payload = serialize_hypothesis_record(record)
    request = _request_doc(
        record,
        "DEVELOPMENT_EXECUTED",
        "DEVELOPMENT_COMPLETED",
        auth="development-contract",
        evidence="FROZEN_DEVELOPMENT_EVIDENCE",
    )
    request_payload = _canonical(request)
    source = _write(tmp_path, "record.json", record_payload)
    explicit = _write(tmp_path, "request.json", request_payload)

    delegated = _run_ok(
        [
            "research",
            "registry",
            "--record",
            str(source),
            "--transition",
            str(explicit),
            "--json",
        ],
        capsys,
    )
    view = json.loads(delegated)
    assert view == research_registry.build_transition_preflight(record_payload, request_payload)
    assert view["record"]["status"] == "PRE_REGISTERED"
    assert view["record"]["state_count"] == 5
    assert view["request"] == request
    assert view["result"] == {
        "accepted": True,
        "would_be_ordinal": 6,
        "would_be_status": "DEVELOPMENT_EXECUTED",
    }
    source_after = source.read_bytes()
    assert source_after == record_payload
    applied = transition_hypothesis_record(record, request)
    assert applied.status == "DEVELOPMENT_EXECUTED"
    assert applied.identity_digest == record.identity_digest
    assert len(applied.state_history) == 6


def test_execution_evidence_rejections_have_exact_codes(tmp_path, capsys):
    record = _record()
    for state, reason in (
        ("LITERATURE_REVIEWED", "SOURCE_REVIEWED"),
        ("A_SHARE_FEASIBILITY_REVIEWED", "FEASIBILITY_ASSESSED"),
        ("NOT_TESTED", "CANDIDATE_REGISTERED"),
        ("PRE_REGISTERED", "PRE_REGISTRATION_REGISTERED"),
    ):
        record = _advance(record, state, reason)
    source = _write(tmp_path, "record.json", serialize_hypothesis_record(record))

    rejected = (
        ("no-auth.json", _request_doc(record, "DEVELOPMENT_EXECUTED", "DEVELOPMENT_COMPLETED"),
         "MISSING_AUTHORIZATION_REF"),
        ("empty-auth.json",
         _request_doc(record, "DEVELOPMENT_EXECUTED", "DEVELOPMENT_COMPLETED", auth="",
                      evidence="FROZEN_DEVELOPMENT_EVIDENCE"),
         "MISSING_AUTHORIZATION_REF"),
        ("bad-auth.json",
         _request_doc(record, "DEVELOPMENT_EXECUTED", "DEVELOPMENT_COMPLETED",
                      auth="Bad Ref!", evidence="FROZEN_DEVELOPMENT_EVIDENCE"),
         "INVALID_IDENTIFIER"),
        ("wrong-evidence.json",
         _request_doc(record, "DEVELOPMENT_EXECUTED", "DEVELOPMENT_COMPLETED",
                      auth="development-contract", evidence="REGISTERED_ROBUSTNESS_EVIDENCE"),
         "ILLEGAL_STATE_TRANSITION"),
    )
    for name, request, code in rejected:
        explicit = _write(tmp_path, name, _canonical(request))
        _rejected(
            ["research", "registry", "--record", str(source), "--transition", str(explicit)],
            code,
            capsys,
        )

    discovered = _record()
    plain = _write(tmp_path, "plain.json", serialize_hypothesis_record(discovered))
    decorated = _write(
        tmp_path,
        "decorated.json",
        _canonical(
            _request_doc(discovered, "LITERATURE_REVIEWED", "SOURCE_REVIEWED",
                         auth="some-contract"),
        ),
    )
    _rejected(
        ["research", "registry", "--record", str(plain), "--transition", str(decorated)],
        "INVALID_FIELD_TYPE",
        capsys,
    )

    duplicate_refs = _to_oos(refs=("development-contract", "development-contract",
                                   "oos-contract"))
    oos = _write(tmp_path, "oos.json", serialize_hypothesis_record(duplicate_refs))
    incomplete = _write(
        tmp_path,
        "incomplete-established.json",
        _canonical(_request_doc(duplicate_refs, "ESTABLISHED", "EVIDENCE_SUPPORTED")),
    )
    _rejected(
        ["research", "registry", "--record", str(oos), "--transition", str(incomplete)],
        "ESTABLISHED_EVIDENCE_INCOMPLETE",
        capsys,
    )

    complete = _to_oos()
    complete_source = _write(tmp_path, "oos-complete.json", serialize_hypothesis_record(complete))
    accepted = _write(
        tmp_path,
        "established.json",
        _canonical(_request_doc(complete, "ESTABLISHED", "EVIDENCE_SUPPORTED")),
    )
    accepted_view = json.loads(
        _run_ok(
            ["research", "registry", "--record", str(complete_source), "--transition",
             str(accepted), "--json"],
            capsys,
        ),
    )
    assert accepted_view["record"]["status"] == "OOS_EXECUTED"
    assert accepted_view["record"]["state_count"] == 8
    assert accepted_view["result"] == {
        "accepted": True,
        "would_be_ordinal": 9,
        "would_be_status": "ESTABLISHED",
    }


def test_transition_shape_rejections_use_frozen_codes(tmp_path, capsys):
    record = _record()
    source = _write(tmp_path, "record.json", serialize_hypothesis_record(record))

    illegal = _request_doc(record, "CANDIDATE_REGISTERED", "CANDIDATE_REGISTERED")
    from_mismatch = _request_doc(record, "A_SHARE_FEASIBILITY_REVIEWED", "FEASIBILITY_ASSESSED")
    from_mismatch["from_state"] = "LITERATURE_REVIEWED"
    reason_mismatch = _request_doc(record, "LITERATURE_REVIEWED", "PRE_REGISTRATION_REGISTERED")
    id_mismatch = _request_doc(record, "LITERATURE_REVIEWED", "SOURCE_REVIEWED")
    id_mismatch["hypothesis_id"] = "SYNTH_EXAMPLE_OTHER"
    version_mismatch = _request_doc(record, "LITERATURE_REVIEWED", "SOURCE_REVIEWED")
    version_mismatch["hypothesis_version"] = 2

    cases = (
        ("illegal-edge.json", illegal),
        ("from-mismatch.json", from_mismatch),
        ("reason-mismatch.json", reason_mismatch),
        ("id-mismatch.json", id_mismatch),
        ("version-mismatch.json", version_mismatch),
    )
    for name, request in cases:
        explicit = _write(tmp_path, name, _canonical(request))
        _rejected(
            ["research", "registry", "--record", str(source), "--transition", str(explicit),
             "--json"],
            "ILLEGAL_STATE_TRANSITION",
            capsys,
        )

    terminal = record
    for state, reason in (
        ("LITERATURE_REVIEWED", "SOURCE_REVIEWED"),
        ("A_SHARE_FEASIBILITY_REVIEWED", "FEASIBILITY_ASSESSED"),
        ("NOT_TESTED", "CANDIDATE_REGISTERED"),
        ("PRE_REGISTERED", "PRE_REGISTRATION_REGISTERED"),
    ):
        terminal = _advance(terminal, state, reason)
    terminal = _advance(
        terminal,
        "DEVELOPMENT_EXECUTED",
        "DEVELOPMENT_COMPLETED",
        auth="development-contract",
        evidence="FROZEN_DEVELOPMENT_EVIDENCE",
    )
    terminal = _advance(terminal, "NOT_ESTABLISHED", "EVIDENCE_NOT_SUPPORTED")
    assert terminal.status == "NOT_ESTABLISHED"
    terminal_source = _write(tmp_path, "terminal.json", serialize_hypothesis_record(terminal))
    revived = _write(
        tmp_path,
        "revived.json",
        _canonical(_request_doc(terminal, "PRE_REGISTERED", "PRE_REGISTRATION_REGISTERED")),
    )
    _rejected(
        ["research", "registry", "--record", str(terminal_source), "--transition", str(revived)],
        "TERMINAL_STATE_HAS_NO_OUTGOING_TRANSITION",
        capsys,
    )


def test_request_key_type_and_byte_failures(tmp_path, capsys):
    record = _record()
    source = _write(tmp_path, "record.json", serialize_hypothesis_record(record))
    base = _request_doc(record, "LITERATURE_REVIEWED", "SOURCE_REVIEWED")
    missing = dict(base)
    missing.pop("evidence_kind")
    extra = dict(base, extra_field="x")
    wrong_version = dict(base, hypothesis_version="1")
    wrong_type = dict(base, authorization_ref=7)

    cases = (
        ("missing.json", _canonical(missing), "MISSING_REQUIRED_FIELD"),
        ("extra.json", _canonical(extra), "UNKNOWN_RECORD_FIELD"),
        ("version.json", _canonical(wrong_version), "INVALID_FIELD_TYPE"),
        ("type.json", _canonical(wrong_type), "INVALID_FIELD_TYPE"),
        ("root.json", b"[1,2]\n", "INVALID_RECORD_STRUCTURE"),
        ("bom.json", b"\xef\xbb\xbf" + _canonical(base), "NON_CANONICAL_SERIALIZATION"),
        ("cr.json", _canonical(base).replace(b"\n", b"\r\n"), "NON_CANONICAL_SERIALIZATION"),
        ("no-lf.json", _canonical(base).rstrip(b"\n"), "NON_CANONICAL_SERIALIZATION"),
        ("double-lf.json", _canonical(base) + b"\n", "NON_CANONICAL_SERIALIZATION"),
        (
            "float.json",
            _canonical(base).replace(b'"hypothesis_version":1', b'"hypothesis_version":1.0'),
            "NON_CANONICAL_SERIALIZATION",
        ),
        (
            "duplicate.json",
            _canonical(base).replace(b'"from_state":"DISCOVERED"',
                                     b'"from_state":"DISCOVERED","from_state":"DISCOVERED"'),
            "NON_CANONICAL_SERIALIZATION",
        ),
        (
            "constant.json",
            _canonical(base).replace(b'"reason_code":"SOURCE_REVIEWED"',
                                     b'"reason_code":NaN'),
            "NON_CANONICAL_SERIALIZATION",
        ),
        (
            "pretty.json",
            (json.dumps(base, ensure_ascii=False, indent=2) + "\n").encode("utf-8"),
            "NON_CANONICAL_SERIALIZATION",
        ),
        (
            "pretty-missing.json",
            (json.dumps(missing, ensure_ascii=False, indent=2) + "\n").encode("utf-8"),
            "MISSING_REQUIRED_FIELD",
        ),
    )
    for name, payload, code in cases:
        explicit = _write(tmp_path, name, payload)
        _rejected(
            ["research", "registry", "--record", str(source), "--transition", str(explicit),
             "--json"],
            code,
            capsys,
        )


def test_argument_shapes_rejected_before_any_io(tmp_path, monkeypatch, capsys):
    missing_record = tmp_path / "missing-record.json"
    missing_request = tmp_path / "missing-request.json"
    shapes = (
        ["research", "registry", "--snapshot", str(missing_record), "--transition",
         str(missing_request)],
        ["research", "registry", "--transition", str(missing_request)],
        ["research", "registry", "--record", str(missing_record), "--snapshot",
         str(missing_request)],
        ["research", "registry", "--record", str(missing_record), "--bogus"],
        ["research", "registry", "--record", str(missing_record), "--transition"],
    )
    original_open = Path.open

    def tracked(path, *args, **kwargs):
        raise AssertionError(f"unexpected IO: {path}")

    with monkeypatch.context() as scoped:
        scoped.setattr(Path, "open", tracked)
        for args in shapes:
            _rejected(args, "INVALID_ARGUMENTS", capsys)
    assert Path.open is original_open

    assert cli.main(["research", "registry", "--help"]) == 0
    help_text = capsys.readouterr()
    assert help_text.err == "" and "--transition" in help_text.out
    assert (
        research_registry.main(["--record", str(missing_record), "--transition",
                                str(missing_request)]) == 2
    )
    direct = capsys.readouterr()
    assert direct.out == "" and direct.err == "error: REGISTRY_READ_FAILED\n"


def test_read_failures_one_read_counting_and_read_only(tmp_path, monkeypatch, capsys):
    record = _record()
    record_payload = serialize_hypothesis_record(record)
    request_payload = _canonical(_request_doc(record, "LITERATURE_REVIEWED", "SOURCE_REVIEWED"))
    source = _write(tmp_path, "record.json", record_payload)
    explicit = _write(tmp_path, "request.json", request_payload)

    _rejected(
        ["research", "registry", "--record", str(tmp_path / "absent.json"), "--transition",
         str(explicit)],
        "REGISTRY_READ_FAILED",
        capsys,
    )
    _rejected(
        ["research", "registry", "--record", str(source), "--transition",
         str(tmp_path / "absent.json")],
        "REGISTRY_READ_FAILED",
        capsys,
    )
    _rejected(
        ["research", "registry", "--record", str(source), "--transition", str(tmp_path)],
        "REGISTRY_READ_FAILED",
        capsys,
    )
    oversized = _write(
        tmp_path, "oversized.json", b"x" * (research_registry.MAX_INPUT_BYTES + 1),
    )
    _rejected(
        ["research", "registry", "--record", str(source), "--transition", str(oversized)],
        "REGISTRY_TOO_LARGE",
        capsys,
    )

    before = {path: path.read_bytes() for path in tmp_path.rglob("*") if path.is_file()}
    original_open = Path.open
    reads = []

    @contextmanager
    def tracker(path, mode="r", *rest, **kwargs):
        with original_open(path, mode, *rest, **kwargs) as stream:
            yield stream
        if mode == "rb":
            reads.append(Path(path))

    def forbidden(*args, **kwargs):
        raise AssertionError("No services/network/database/execution")

    for name in ("load_config", "setup_logging", "_create_service"):
        monkeypatch.setattr(cli, name, forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(duckdb, "connect", forbidden)
    monkeypatch.setattr(pipeline, "run_synthetic_pipeline", forbidden)
    monkeypatch.setattr(execution, "execute_bounded_analysis", forbidden)
    args = ["research", "registry", "--record", str(source), "--transition", str(explicit),
            "--json"]
    with monkeypatch.context() as scoped:
        scoped.setattr(Path, "open", tracker)
        first = _run_ok(args, capsys)
        assert reads == [source, explicit]
        reads.clear()
        second = _run_ok(args, capsys)
        assert reads == [source, explicit]
    assert first == second
    after = {path: path.read_bytes() for path in tmp_path.rglob("*") if path.is_file()}
    assert after == before


def test_surface_frozen_and_previous_views_unchanged(tmp_path, capsys):
    public = {name for name in registry.__all__ if inspect.isfunction(getattr(registry, name))}
    assert public == PUBLIC_FUNCTIONS and len(public) == 13
    assert research_registry.REQUEST_FIELDS == EXPECTED_REQUEST_FIELDS
    additions = ("build_transition_preflight", "render_transition_markdown")
    for name in additions:
        function = getattr(research_registry, name)
        assert "kwargs" not in str(inspect.signature(function))
        assert FORBIDDEN_NAMES.search(name) is None
    for name in ("build_record_view", "build_snapshot_view", "render_record_markdown",
                 "render_snapshot_markdown"):
        assert FORBIDDEN_NAMES.search(name) is None

    command = next(item for item in research_entry.COMMANDS if item.name == "registry")
    assert command.module == "ashare_research.tools.research_registry"
    assert len(command.usage) == 3
    assert any("--transition" in line and "只读预检" in line for line in command.usage)
    assert "--transition" in research_entry.USAGE

    record = _record()
    record_payload = serialize_hypothesis_record(record)
    source = _write(tmp_path, "record.json", record_payload)
    delegated_record = _run_ok(
        ["research", "registry", "--record", str(source), "--json"], capsys,
    )
    assert delegated_record == research_registry._json(
        research_registry.build_record_view(record_payload),
    ) + "\n"
    snapshot_payload = serialize_hypothesis_registry_snapshot(
        build_hypothesis_registry_snapshot((record,)),
    )
    snapshot = _write(tmp_path, "snapshot.json", snapshot_payload)
    delegated_snapshot = _run_ok(
        ["research", "registry", "--snapshot", str(snapshot), "--json"], capsys,
    )
    assert delegated_snapshot == research_registry._json(
        research_registry.build_snapshot_view(snapshot_payload),
    ) + "\n"
