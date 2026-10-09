"""Read-only M4-B registry artifact comparison: mechanical diffs, no writes."""

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
from ashare_research.tools import research_entry, research_registry, research_registry_compare

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
IDENTITY_KEYS = (
    "hypothesis_id",
    "hypothesis_version",
    "status",
    "identity_digest",
    "record_digest",
    "state_count",
)
BOUNDARY = {
    "execution_authorized": False,
    "statistics_computed": False,
    "outcome_read": False,
    "holdout_accessed": False,
    "real_registry_dataset_loaded": False,
    "registry_written": False,
}


def _doc(identifier: str = "SYNTH_EXAMPLE_0001", *, version: int = 1) -> dict:
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


def _finalize(document: dict):
    document["identity_digest"] = hypothesis_record_identity_digest(document)
    document["record_digest"] = hypothesis_record_digest(document)
    return parse_hypothesis_record(document)


def _record(
    identifier: str = "SYNTH_EXAMPLE_0001",
    *,
    version: int = 1,
    theory: str = "SYNTHETIC_EXAMPLE_THEORY",
):
    document = _doc(identifier, version=version)
    document["theory"] = theory
    return _finalize(document)


def _advance(record, to_state: str, reason: str):
    return transition_hypothesis_record(
        record,
        StateTransitionRequestV1(
            record.hypothesis_id,
            record.hypothesis_version,
            record.status,
            to_state,
            reason,
            None,
            None,
        ),
    )


def _canonical(document) -> bytes:
    return (
        json.dumps(document, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
    ).encode("utf-8")


def _record_bytes(record) -> bytes:
    return serialize_hypothesis_record(record)


def _snapshot_bytes(*records) -> bytes:
    return serialize_hypothesis_registry_snapshot(
        build_hypothesis_registry_snapshot(tuple(records)),
    )


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


def _compare(left: Path, right: Path, capsys) -> dict:
    output = _run_ok(
        ["research", "registry-compare", "--left", str(left), "--right", str(right), "--json"],
        capsys,
    )
    return json.loads(output)


def _projection(record, status: str) -> dict:
    return {
        "hypothesis_id": record.hypothesis_id,
        "hypothesis_version": record.hypothesis_version,
        "status": status,
        "identity_digest": record.identity_digest,
        "record_digest": record.record_digest,
        "state_count": len(record.state_history),
    }


def test_identical_pair_exact_report_and_entry_delegation(tmp_path, capsys):
    record = _record()
    payload = _record_bytes(record)
    left = _write(tmp_path, "left.json", payload)
    right = _write(tmp_path, "right.json", payload)
    expected = research_registry_compare.build_comparison(payload, payload)

    delegated = _run_ok(
        ["research", "registry-compare", "--left", str(left), "--right", str(right), "--json"],
        capsys,
    )
    assert delegated == research_registry_compare._json(expected) + "\n"
    assert research_registry_compare.main(["--left", str(left), "--right", str(right)]) == 0
    direct = capsys.readouterr()
    assert direct.err == "" and direct.out == research_registry_compare.render_markdown(expected)
    assert (
        research_entry.main(["registry-compare", "--left", str(left), "--right", str(right),
                             "--json"])
        == 0
    )
    entry = capsys.readouterr()
    assert entry.err == "" and entry.out == delegated

    view = json.loads(delegated)
    assert view["schema"] == research_registry_compare.SCHEMA
    assert view["schema"] == "m4_registry_comparison_v1"
    assert view["status"] == research_registry_compare.STATUS == "read_only_comparison"
    assert view["kind"] == "record" and view["byte_identical"] is True
    identity = {
        "file_sha256": hashlib.sha256(payload).hexdigest(),
        **_projection(record, "DISCOVERED"),
    }
    assert view["left"] == identity and view["right"] == identity
    assert view["differences"] == {
        "record_equal": True,
        "changed_field_count": 0,
        "changed_fields": [],
        "equality": {name: True for name in IDENTITY_KEYS},
    }
    assert view["boundary"] == BOUNDARY
    assert view["notes"] == list(research_registry_compare.NOTES)

    markdown = _run_ok(
        ["research", "registry-compare", "--left", str(left), "--right", str(right)],
        capsys,
    )
    assert markdown == research_registry_compare.render_markdown(expected)
    assert "# M4-B registry 产物只读比较" in markdown
    assert "## 字段差异" in markdown and "## 等价性" in markdown


def test_record_pair_differences_sorted_and_classified(tmp_path, capsys):
    first = _record()
    version_bump = _record(version=2, theory="SYNTHETIC_EXAMPLE_THEORY_REVISED")
    advanced = _advance(first, "LITERATURE_REVIEWED", "SOURCE_REVIEWED")
    left = _write(tmp_path, "left.json", _record_bytes(first))
    right_version = _write(tmp_path, "right-version.json", _record_bytes(version_bump))
    right_status = _write(tmp_path, "right-status.json", _record_bytes(advanced))

    versioned = _compare(left, right_version, capsys)
    rows = versioned["differences"]["changed_fields"]
    assert [row["field"] for row in rows] == sorted(row["field"] for row in rows)
    assert [row["field"] for row in rows] == [
        "hypothesis_version",
        "identity_digest",
        "record_digest",
        "theory",
    ]
    left_doc = json.loads(_record_bytes(first))
    right_doc = json.loads(_record_bytes(version_bump))
    assert all(row["left"] == left_doc[row["field"]] for row in rows)
    assert all(row["right"] == right_doc[row["field"]] for row in rows)
    assert versioned["differences"]["record_equal"] is False
    assert versioned["differences"]["equality"] == {
        "hypothesis_id": True,
        "hypothesis_version": False,
        "status": True,
        "identity_digest": False,
        "record_digest": False,
        "state_count": True,
    }

    status = _compare(left, right_status, capsys)
    assert [row["field"] for row in status["differences"]["changed_fields"]] == [
        "record_digest",
        "state_history",
        "status",
    ]
    assert status["differences"]["equality"] == {
        "hypothesis_id": True,
        "hypothesis_version": True,
        "status": False,
        "identity_digest": True,
        "record_digest": False,
        "state_count": False,
    }
    assert status["left"]["status"] == "DISCOVERED"
    assert status["right"]["status"] == "LITERATURE_REVIEWED"
    assert status["left"]["state_count"] == 1 and status["right"]["state_count"] == 2


def test_snapshot_pair_classification_counts_and_order(tmp_path, capsys):
    alpha = _record("SYNTH_EXAMPLE_0001")
    bravo = _record("SYNTH_EXAMPLE_0002")
    charlie = _record("SYNTH_EXAMPLE_0003")
    delta = _record("SYNTH_EXAMPLE_0004")
    bravo_moved = _advance(bravo, "LITERATURE_REVIEWED", "SOURCE_REVIEWED")

    left = _write(tmp_path, "left.json", _snapshot_bytes(alpha, bravo, charlie))
    right = _write(tmp_path, "right.json", _snapshot_bytes(alpha, bravo_moved, delta))
    assert left.read_bytes() != right.read_bytes()
    view = _compare(left, right, capsys)
    assert view["kind"] == "snapshot" and view["byte_identical"] is False
    assert view["left"]["record_count"] == 3 and view["right"]["record_count"] == 3
    assert view["left"]["real_demo_candidate_count"] == 3
    assert view["right"]["real_demo_candidate_count"] == 3
    differences = view["differences"]
    assert differences["registry_equal"] is False
    assert differences["equality"]["record_count"] is True
    assert differences["equality"]["registry_digest"] is False
    assert [item["hypothesis_id"] for item in differences["added"]] == ["SYNTH_EXAMPLE_0004"]
    assert [item["hypothesis_id"] for item in differences["removed"]] == ["SYNTH_EXAMPLE_0003"]
    assert differences["added"] == [_projection(delta, "DISCOVERED")]
    assert differences["removed"] == [_projection(charlie, "DISCOVERED")]
    assert len(differences["changed"]) == 1
    changed = differences["changed"][0]
    assert changed["hypothesis_id"] == "SYNTH_EXAMPLE_0002"
    assert changed["left"] == _projection(bravo, "DISCOVERED")
    assert changed["right"] == _projection(bravo_moved, "LITERATURE_REVIEWED")
    assert (
        differences["added_count"],
        differences["removed_count"],
        differences["changed_count"],
        differences["unchanged_count"],
    ) == (1, 1, 1, 1)

    same = _write(tmp_path, "same.json", left.read_bytes())
    identical = _compare(left, same, capsys)
    assert identical["byte_identical"] is True
    assert identical["differences"]["registry_equal"] is True
    assert identical["differences"]["added"] == []
    assert identical["differences"]["removed"] == []
    assert identical["differences"]["changed"] == []
    assert identical["differences"]["unchanged_count"] == 3
    assert all(identical["differences"]["equality"].values())

    revised = _write(
        tmp_path,
        "revised.json",
        _snapshot_bytes(alpha, _record("SYNTH_EXAMPLE_0002", version=2), charlie),
    )
    version_view = _compare(left, revised, capsys)
    assert version_view["differences"]["unchanged_count"] == 2
    assert version_view["differences"]["added_count"] == 1
    assert version_view["differences"]["removed_count"] == 1
    assert version_view["differences"]["changed_count"] == 0
    assert [item["hypothesis_version"] for item in version_view["differences"]["added"]] == [2]
    assert [item["hypothesis_version"] for item in version_view["differences"]["removed"]] == [1]
    markdown = _run_ok(
        ["research", "registry-compare", "--left", str(left), "--right", str(right)],
        capsys,
    )
    assert markdown == research_registry_compare.render_markdown(view)
    assert "## 记录差异" in markdown and "## 执行边界" in markdown


def test_mixed_kinds_and_frozen_side_failures(tmp_path, capsys):
    record = _record()
    record_payload = _record_bytes(record)
    snapshot_payload = _snapshot_bytes(record, _record("SYNTH_EXAMPLE_0002"))
    source = _write(tmp_path, "record.json", record_payload)
    snapshot = _write(tmp_path, "snapshot.json", snapshot_payload)
    _rejected(
        ["research", "registry-compare", "--left", str(source), "--right", str(snapshot)],
        "INCOMPARABLE_ARTIFACT_KINDS",
        capsys,
    )
    record_doc = json.loads(record_payload)
    snapshot_doc = json.loads(snapshot_payload)

    def rejected_pair(name: str, left_payload: bytes, right_payload: bytes, code: str) -> None:
        left = _write(tmp_path, f"{name}-left.json", left_payload)
        right = _write(tmp_path, f"{name}-right.json", right_payload)
        _rejected(
            ["research", "registry-compare", "--left", str(left), "--right", str(right),
             "--json"],
            code,
            capsys,
        )

    tampered_digest = dict(
        record_doc,
        identity_digest=("0" if record_doc["identity_digest"][0] != "0" else "1")
        + record_doc["identity_digest"][1:],
    )
    record_cases = (
        ("bom", b"\xef\xbb\xbf" + record_payload, "NON_CANONICAL_SERIALIZATION"),
        ("cr", record_payload.replace(b"\n", b"\r\n"), "NON_CANONICAL_SERIALIZATION"),
        ("no-lf", record_payload.rstrip(b"\n"), "NON_CANONICAL_SERIALIZATION"),
        (
            "duplicate",
            record_payload.replace(b'"status":"DISCOVERED"',
                                   b'"status":"DISCOVERED","status":"DISCOVERED"'),
            "NON_CANONICAL_SERIALIZATION",
        ),
        (
            "float",
            record_payload.replace(b'"hypothesis_version":1', b'"hypothesis_version":1.0'),
            "NON_CANONICAL_SERIALIZATION",
        ),
        (
            "pretty",
            (json.dumps(record_doc, ensure_ascii=False, indent=2) + "\n").encode("utf-8"),
            "NON_CANONICAL_SERIALIZATION",
        ),
        ("root", b"[1,2]\n", "INVALID_RECORD_STRUCTURE"),
        (
            "missing",
            _canonical({k: v for k, v in record_doc.items() if k != "theory"}),
            "MISSING_REQUIRED_FIELD",
        ),
        ("extra", _canonical(dict(record_doc, notes_extra="x")), "UNKNOWN_RECORD_FIELD"),
        ("digest", _canonical(tampered_digest), "IDENTITY_DIGEST_MISMATCH"),
    )
    for name, payload, code in record_cases:
        rejected_pair(f"left-{name}", payload, record_payload, code)
        rejected_pair(f"right-{name}", record_payload, payload, code)

    snapshot_cases = (
        (
            "order",
            _canonical(dict(snapshot_doc, records=list(reversed(snapshot_doc["records"])))),
            "INVALID_RECORD_STRUCTURE",
        ),
        (
            "count",
            _canonical(dict(snapshot_doc, real_demo_candidate_count=0)),
            "INVALID_FIELD_TYPE",
        ),
        (
            "digest",
            _canonical(dict(snapshot_doc, registry_digest="0" * 64)),
            "RECORD_DIGEST_MISMATCH",
        ),
        ("extra", _canonical(dict(snapshot_doc, extra=False)), "UNKNOWN_RECORD_FIELD"),
        (
            "missing",
            _canonical({k: v for k, v in snapshot_doc.items() if k != "registry_digest"}),
            "MISSING_REQUIRED_FIELD",
        ),
        (
            "pretty",
            json.dumps(snapshot_doc, ensure_ascii=False, indent=2).encode("utf-8"),
            "NON_CANONICAL_SERIALIZATION",
        ),
        (
            "pretty-lf",
            (json.dumps(snapshot_doc, ensure_ascii=False, indent=2) + "\n").encode("utf-8"),
            "REGISTRY_VIEW_MISMATCH",
        ),
    )
    for name, payload, code in snapshot_cases:
        rejected_pair(f"left-snapshot-{name}", payload, snapshot_payload, code)
        rejected_pair(f"right-snapshot-{name}", snapshot_payload, payload, code)

    stray = _canonical(dict(record_doc, records=[]))
    rejected_pair("left-stray", stray, snapshot_payload, "UNKNOWN_RECORD_FIELD")
    rejected_pair("right-stray", snapshot_payload, stray, "UNKNOWN_RECORD_FIELD")



def test_argument_shapes_rejected_before_any_io(tmp_path, monkeypatch, capsys):
    missing = tmp_path / "missing.json"
    shapes = (
        ["research", "registry-compare"],
        ["research", "registry-compare", "--left", str(missing)],
        ["research", "registry-compare", "--right", str(missing)],
        ["research", "registry-compare", "--left", str(missing), "--bogus"],
    )
    original_open = Path.open

    def tracked(path, *args, **kwargs):
        raise AssertionError(f"unexpected IO: {path}")

    with monkeypatch.context() as scoped:
        scoped.setattr(Path, "open", tracked)
        for args in shapes:
            _rejected(args, "INVALID_ARGUMENTS", capsys)
    assert Path.open is original_open

    assert cli.main(["research", "registry-compare", "--help"]) == 0
    help_text = capsys.readouterr()
    assert help_text.err == ""
    assert "--left" in help_text.out and "--right" in help_text.out
    assert research_registry_compare.main(
        ["--left", str(missing), "--right", str(missing)],
    ) == 2
    direct = capsys.readouterr()
    assert direct.out == "" and direct.err == "error: REGISTRY_READ_FAILED\n"


def test_read_failures_single_read_counting_and_read_only(tmp_path, monkeypatch, capsys):
    record = _record()
    payload = _record_bytes(record)
    left = _write(tmp_path, "left.json", payload)
    right = _write(tmp_path, "right.json", payload)

    _rejected(
        ["research", "registry-compare", "--left", str(tmp_path / "absent.json"), "--right",
         str(right)],
        "REGISTRY_READ_FAILED",
        capsys,
    )
    _rejected(
        ["research", "registry-compare", "--left", str(left), "--right",
         str(tmp_path / "absent.json")],
        "REGISTRY_READ_FAILED",
        capsys,
    )
    _rejected(
        ["research", "registry-compare", "--left", str(left), "--right", str(tmp_path)],
        "REGISTRY_READ_FAILED",
        capsys,
    )
    oversized = _write(
        tmp_path, "oversized.json", b"x" * (research_registry.MAX_INPUT_BYTES + 1),
    )
    _rejected(
        ["research", "registry-compare", "--left", str(left), "--right", str(oversized)],
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
    args = ["research", "registry-compare", "--left", str(left), "--right", str(right),
            "--json"]
    with monkeypatch.context() as scoped:
        scoped.setattr(Path, "open", tracker)
        first = _run_ok(args, capsys)
        assert reads == [left, right]
        reads.clear()
        second = _run_ok(args, capsys)
        assert reads == [left, right]
    assert first == second
    after = {path: path.read_bytes() for path in tmp_path.rglob("*") if path.is_file()}
    assert after == before


def test_surface_frozen_and_previous_outputs_unchanged(tmp_path, capsys):
    public = {name for name in registry.__all__ if inspect.isfunction(getattr(registry, name))}
    assert public == PUBLIC_FUNCTIONS and len(public) == 13
    module_functions = {
        name for name in dir(research_registry_compare)
        if not name.startswith("_")
        and inspect.isfunction(getattr(research_registry_compare, name))
        and getattr(research_registry_compare, name).__module__
        == "ashare_research.tools.research_registry_compare"
    }
    assert module_functions == {"build_comparison", "main", "render_markdown"}
    for name in module_functions:
        assert FORBIDDEN_NAMES.search(name) is None
        assert "kwargs" not in str(inspect.signature(getattr(research_registry_compare, name)))

    names = [command.name for command in research_entry.COMMANDS]
    assert names.count("registry-compare") == 1
    assert names.index("registry-compare") == names.index("registry") - 1
    command = research_entry.COMMANDS[names.index("registry-compare")]
    assert command.module == "ashare_research.tools.research_registry_compare"
    assert len(command.usage) == 1
    assert "--left" in command.usage[0] and "--right" in command.usage[0]
    assert "registry-compare" in research_entry.USAGE

    record = _record()
    record_payload = _record_bytes(record)
    source = _write(tmp_path, "record.json", record_payload)
    record_view = _run_ok(["research", "registry", "--record", str(source), "--json"], capsys)
    assert record_view == research_registry._json(
        research_registry.build_record_view(record_payload),
    ) + "\n"
    request = research_registry.strict_json_document(
        _canonical(
            {
                "hypothesis_id": record.hypothesis_id,
                "hypothesis_version": record.hypothesis_version,
                "from_state": record.status,
                "to_state": "LITERATURE_REVIEWED",
                "reason_code": "SOURCE_REVIEWED",
                "authorization_ref": None,
                "evidence_kind": None,
            },
        ),
    )
    request_bytes = _canonical(request)
    request_path = _write(tmp_path, "request.json", request_bytes)
    preflight = _run_ok(
        ["research", "registry", "--record", str(source), "--transition", str(request_path),
         "--json"],
        capsys,
    )
    assert preflight == research_registry._json(
        research_registry.build_transition_preflight(record_payload, request_bytes),
    ) + "\n"
    snapshot_payload = _snapshot_bytes(record)
    snapshot = _write(tmp_path, "snapshot.json", snapshot_payload)
    snapshot_view = _run_ok(
        ["research", "registry", "--snapshot", str(snapshot), "--json"], capsys,
    )
    assert snapshot_view == research_registry._json(
        research_registry.build_snapshot_view(snapshot_payload),
    ) + "\n"
