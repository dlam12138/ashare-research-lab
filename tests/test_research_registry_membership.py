"""Read-only M4-B registry snapshot membership check: mechanical, non-mutating."""

from __future__ import annotations

import hashlib
import inspect
import json
import re
from pathlib import Path

import pytest

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
from ashare_research.tools import (
    research_entry,
    research_registry,
    research_registry_membership,
)

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


def _record(identifier: str = "SYNTH_EXAMPLE_0001", *, version: int = 1):
    document = _doc(identifier, version=version)
    document["identity_digest"] = hypothesis_record_identity_digest(document)
    document["record_digest"] = hypothesis_record_digest(document)
    return parse_hypothesis_record(document)


def _advance(record):
    return transition_hypothesis_record(
        record,
        StateTransitionRequestV1(
            record.hypothesis_id,
            record.hypothesis_version,
            record.status,
            "LITERATURE_REVIEWED",
            "SOURCE_REVIEWED",
            None,
            None,
        ),
    )


def _record_bytes(record) -> bytes:
    return serialize_hypothesis_record(record)


def _snapshot_bytes(*records) -> bytes:
    return serialize_hypothesis_registry_snapshot(
        build_hypothesis_registry_snapshot(tuple(records)),
    )


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


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


def _membership(record: Path, snapshot: Path, capsys) -> dict:
    output = _run_ok(
        [
            "research",
            "registry-membership",
            "--record",
            str(record),
            "--snapshot",
            str(snapshot),
            "--json",
        ],
        capsys,
    )
    return json.loads(output)


def test_identical_membership_exact_report_and_delegation(tmp_path, capsys):
    alpha = _record()
    bravo = _record("SYNTH_EXAMPLE_0002")
    record_payload = _record_bytes(alpha)
    snapshot_payload = _snapshot_bytes(alpha, bravo)
    record_file = _write(tmp_path, "record.json", record_payload)
    snapshot_file = _write(tmp_path, "snapshot.json", snapshot_payload)
    built_snapshot = build_hypothesis_registry_snapshot((alpha, bravo))

    expected = research_registry_membership.build_membership(record_payload, snapshot_payload)
    delegated = _run_ok(
        [
            "research",
            "registry-membership",
            "--record",
            str(record_file),
            "--snapshot",
            str(snapshot_file),
            "--json",
        ],
        capsys,
    )
    assert delegated == research_registry_membership._json(expected) + "\n"
    assert research_registry_membership.main(
        ["--record", str(record_file), "--snapshot", str(snapshot_file)],
    ) == 0
    direct = capsys.readouterr()
    assert direct.err == ""
    assert direct.out == research_registry_membership.render_markdown(expected)

    assert expected["schema"] == "m4_registry_snapshot_membership_v1"
    assert expected["status"] == "registered_identical"
    assert expected["membership"] == {
        "found": True,
        "same_id_versions": [1],
        "canonical_equal": True,
        "changed_field_count": 0,
        "changed_fields": [],
        "equality": {
            "hypothesis_id": True,
            "hypothesis_version": True,
            "status": True,
            "identity_digest": True,
            "record_digest": True,
            "state_count": True,
        },
    }
    assert expected["record"] == {
        "file_sha256": _sha256(record_payload),
        "hypothesis_id": "SYNTH_EXAMPLE_0001",
        "hypothesis_version": 1,
        "status": "DISCOVERED",
        "identity_digest": alpha.identity_digest,
        "record_digest": alpha.record_digest,
        "state_count": 1,
    }
    assert expected["snapshot"] == {
        "file_sha256": _sha256(snapshot_payload),
        "registry_schema_version": built_snapshot.registry_schema_version,
        "registry_version": built_snapshot.registry_version,
        "registry_digest": built_snapshot.registry_digest,
        "record_count": 2,
        "real_demo_candidate_count": 2,
    }
    assert expected["boundary"] == research_registry.BOUNDARY
    assert expected["notes"] == list(research_registry_membership.NOTES)
    markdown = research_registry_membership.render_markdown(expected)
    assert markdown.startswith("# M4-B registry 记录成员关系只读检查")
    assert "- 状态：`registered_identical`（已登记且规范记录字节一致）" in markdown
    assert "m4_registry_snapshot_membership_v1" in research_registry_membership._json(expected)


def test_different_membership_changed_fields_sorted_and_equality(tmp_path, capsys):
    alpha = _record()
    bravo = _record("SYNTH_EXAMPLE_0002")
    advanced = _advance(alpha)
    record_payload = _record_bytes(advanced)
    snapshot_payload = _snapshot_bytes(alpha, bravo)
    record_file = _write(tmp_path, "record.json", record_payload)
    snapshot_file = _write(tmp_path, "snapshot.json", snapshot_payload)

    delegated = _run_ok(
        ["research", "registry-membership", "--record", str(record_file), "--snapshot",
         str(snapshot_file), "--json"],
        capsys,
    )
    report = json.loads(delegated)
    assert delegated == research_registry_membership._json(
        research_registry_membership.build_membership(record_payload, snapshot_payload),
    ) + "\n"
    assert report["status"] == "registered_different"
    payload = report["membership"]
    assert payload["found"] is True and payload["canonical_equal"] is False
    assert payload["same_id_versions"] == [1]
    assert payload["changed_field_count"] == 3
    assert [row["field"] for row in payload["changed_fields"]] == [
        "record_digest",
        "state_history",
        "status",
    ]
    rows = {row["field"]: row for row in payload["changed_fields"]}
    assert rows["status"]["record"] == "LITERATURE_REVIEWED"
    assert rows["status"]["snapshot"] == "DISCOVERED"
    assert rows["record_digest"]["record"] == advanced.record_digest
    assert rows["record_digest"]["snapshot"] == alpha.record_digest
    assert len(rows["state_history"]["record"]) == 2
    assert len(rows["state_history"]["snapshot"]) == 1
    assert payload["equality"] == {
        "hypothesis_id": True,
        "hypothesis_version": True,
        "status": False,
        "identity_digest": True,
        "record_digest": False,
        "state_count": False,
    }
    markdown = research_registry_membership.render_markdown(report)
    assert "| status | LITERATURE_REVIEWED | DISCOVERED |" in markdown
    assert "| record_digest |" in markdown and "| state_history |" in markdown


def test_absent_key_with_and_without_same_id_versions(tmp_path, capsys):
    alpha = _record()
    bravo = _record("SYNTH_EXAMPLE_0002")
    bumped = _record(version=2)
    other = _record("SYNTH_EXAMPLE_0009")
    bumped_file = _write(tmp_path, "record-v2.json", _record_bytes(bumped))
    other_file = _write(tmp_path, "record-other.json", _record_bytes(other))
    snapshot_file = _write(tmp_path, "snapshot.json", _snapshot_bytes(alpha, bravo))

    same_id = _membership(bumped_file, snapshot_file, capsys)
    assert same_id["status"] == "not_registered"
    payload = same_id["membership"]
    assert payload["found"] is False and payload["canonical_equal"] is False
    assert payload["same_id_versions"] == [1]
    assert payload["changed_field_count"] == 0 and payload["changed_fields"] == []
    assert not any(payload["equality"].values())
    assert set(payload["equality"]) == {
        "hypothesis_id",
        "hypothesis_version",
        "status",
        "identity_digest",
        "record_digest",
        "state_count",
    }

    absent = _membership(other_file, snapshot_file, capsys)
    assert absent["status"] == "not_registered"
    assert absent["membership"]["same_id_versions"] == []
    assert not any(absent["membership"]["equality"].values())
    markdown = research_registry_membership.render_markdown(absent)
    assert "（未登记（快照中没有该键））" in markdown
    assert "同 ID 版本：（无）" in markdown


def test_delegated_frozen_failure_codes(tmp_path, capsys):
    alpha = _record()
    record_payload = _record_bytes(alpha)
    snapshot_payload = _snapshot_bytes(alpha, _record("SYNTH_EXAMPLE_0002"))
    record_file = _write(tmp_path, "record.json", record_payload)
    snapshot_file = _write(tmp_path, "snapshot.json", snapshot_payload)

    bom = _write(tmp_path, "record-bom.json", b"\xef\xbb\xbf" + record_payload)
    _rejected(
        ["research", "registry-membership", "--record", str(bom), "--snapshot",
         str(snapshot_file)],
        "NON_CANONICAL_SERIALIZATION",
        capsys,
    )
    pretty_snapshot = _write(
        tmp_path,
        "snapshot-pretty.json",
        (
            json.dumps(
                json.loads(snapshot_payload), ensure_ascii=False, indent=2, sort_keys=True,
            )
            + "\n"
        ).encode("utf-8"),
    )
    _rejected(
        ["research", "registry-membership", "--record", str(record_file), "--snapshot",
         str(pretty_snapshot)],
        "REGISTRY_VIEW_MISMATCH",
        capsys,
    )
    pretty_record = _write(
        tmp_path,
        "record-pretty.json",
        (
            json.dumps(
                json.loads(record_payload), ensure_ascii=False, indent=2, sort_keys=True,
            )
            + "\n"
        ).encode("utf-8"),
    )
    _rejected(
        ["research", "registry-membership", "--record", str(pretty_record), "--snapshot",
         str(snapshot_file)],
        "NON_CANONICAL_SERIALIZATION",
        capsys,
    )
    _rejected(
        ["research", "registry-membership", "--record", str(tmp_path / "missing.json"),
         "--snapshot", str(snapshot_file)],
        "REGISTRY_READ_FAILED",
        capsys,
    )
    oversize = _write(tmp_path, "oversize.json", b"{" + b"0" * 1_048_576)
    _rejected(
        ["research", "registry-membership", "--record", str(oversize), "--snapshot",
         str(snapshot_file)],
        "REGISTRY_TOO_LARGE",
        capsys,
    )


def test_doctored_report_invariant_guards_fail_closed(tmp_path, capsys, monkeypatch):
    alpha = _record()
    advanced = _advance(alpha)
    different_payload = _record_bytes(advanced)
    snapshot_payload = _snapshot_bytes(alpha, _record("SYNTH_EXAMPLE_0002"))
    record_file = _write(tmp_path, "record.json", different_payload)
    snapshot_file = _write(tmp_path, "snapshot.json", snapshot_payload)
    different = research_registry_membership.build_membership(
        different_payload, snapshot_payload,
    )
    identical = research_registry_membership.build_membership(
        _record_bytes(alpha), snapshot_payload,
    )
    absent = research_registry_membership.build_membership(
        _record_bytes(_record(version=2)), snapshot_payload,
    )

    def mismatch(report: dict) -> None:
        with pytest.raises(research_registry_membership.MembershipError) as captured:
            research_registry_membership._verify_report(report)
        assert captured.value.code == "REGISTRY_MEMBERSHIP_MISMATCH"

    def clone(report: dict) -> dict:
        return json.loads(json.dumps(report))

    research_registry_membership._verify_report(identical)
    research_registry_membership._verify_report(different)
    research_registry_membership._verify_report(absent)

    doctored = clone(different)
    doctored["membership"]["changed_field_count"] += 1
    mismatch(doctored)
    doctored = clone(different)
    doctored["membership"]["changed_fields"].pop()
    mismatch(doctored)
    doctored = clone(different)
    doctored["membership"]["canonical_equal"] = True
    mismatch(doctored)
    doctored = clone(different)
    doctored["membership"]["equality"]["status"] = True
    mismatch(doctored)
    doctored = clone(different)
    doctored["membership"]["changed_fields"].append(
        {"field": "unknown_field", "record": 1, "snapshot": 2},
    )
    doctored["membership"]["changed_field_count"] += 1
    mismatch(doctored)
    doctored = clone(different)
    doctored["boundary"] = {**doctored["boundary"], "registry_written": True}
    mismatch(doctored)
    doctored = clone(different)
    doctored["status"] = "not_registered"
    mismatch(doctored)
    doctored = clone(different)
    doctored["membership"]["same_id_versions"] = [1, 1]
    mismatch(doctored)
    doctored = clone(identical)
    doctored["membership"]["same_id_versions"] = []
    mismatch(doctored)
    doctored = clone(absent)
    doctored["membership"]["equality"]["status"] = True
    mismatch(doctored)
    doctored = clone(identical)
    doctored["record"]["file_sha256"] = "not-a-digest"
    mismatch(doctored)
    doctored = clone(identical)
    doctored["notes"] = list(doctored["notes"])[:-1]
    mismatch(doctored)

    doctored_builder_report = clone(different)
    doctored_builder_report["membership"]["canonical_equal"] = True
    monkeypatch.setattr(
        research_registry_membership,
        "build_membership",
        lambda _record_payload, _snapshot_payload: doctored_builder_report,
    )
    assert research_registry_membership.main(
        ["--record", str(record_file), "--snapshot", str(snapshot_file)],
    ) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == "error: REGISTRY_MEMBERSHIP_MISMATCH\n"


def test_argument_shapes_and_read_failures_rejected(tmp_path, capsys, monkeypatch):
    missing = tmp_path / "missing.json"
    shapes = (
        ["research", "registry-membership"],
        ["research", "registry-membership", "--record", str(missing)],
        ["research", "registry-membership", "--snapshot", str(missing)],
        ["research", "registry-membership", "--record", str(missing), "--bogus"],
    )
    original_open = Path.open

    def tracked(path, *args, **kwargs):
        raise AssertionError(f"unexpected IO: {path}")

    with monkeypatch.context() as scoped:
        scoped.setattr(Path, "open", tracked)
        for args in shapes:
            _rejected(args, "INVALID_ARGUMENTS", capsys)
    assert Path.open is original_open

    assert cli.main(["research", "registry-membership", "--help"]) == 0
    help_text = capsys.readouterr()
    assert help_text.err == ""
    assert "--record" in help_text.out and "--snapshot" in help_text.out
    assert research_registry_membership.main(["--record", str(missing), "--snapshot",
                                             str(missing)]) == 2
    direct = capsys.readouterr()
    assert direct.out == "" and direct.err == "error: REGISTRY_READ_FAILED\n"


def test_single_read_offline_no_write_and_determinism(tmp_path, capsys, monkeypatch):
    record_file = _write(tmp_path, "record.json", _record_bytes(_record()))
    snapshot_file = _write(
        tmp_path,
        "snapshot.json",
        _snapshot_bytes(_record(), _record("SYNTH_EXAMPLE_0002")),
    )
    before = {path: path.read_bytes() for path in tmp_path.rglob("*") if path.is_file()}
    reads: list[Path] = []
    original_open = Path.open

    def tracker(path: Path, *args, **kwargs):
        reads.append(path)
        return original_open(path, *args, **kwargs)

    def forbidden(*_args, **_kwargs):
        raise AssertionError("forbidden mechanism entry called")

    monkeypatch.setattr(pipeline, "run_synthetic_pipeline", forbidden)
    monkeypatch.setattr(execution, "execute_bounded_analysis", forbidden)
    args = [
        "research",
        "registry-membership",
        "--record",
        str(record_file),
        "--snapshot",
        str(snapshot_file),
        "--json",
    ]
    with monkeypatch.context() as scoped:
        scoped.setattr(Path, "open", tracker)
        first = _run_ok(args, capsys)
        assert reads == [record_file, snapshot_file]
        reads.clear()
        second = _run_ok(args, capsys)
        assert reads == [record_file, snapshot_file]
    assert first == second
    after = {path: path.read_bytes() for path in tmp_path.rglob("*") if path.is_file()}
    assert after == before


def test_membership_surface_bounded_and_entry_shape():
    public = {name for name in registry.__all__ if inspect.isfunction(getattr(registry, name))}
    assert public == PUBLIC_FUNCTIONS and len(public) == 13
    module_functions = {
        name
        for name in dir(research_registry_membership)
        if not name.startswith("_")
        and inspect.isfunction(getattr(research_registry_membership, name))
        and getattr(research_registry_membership, name).__module__
        == "ashare_research.tools.research_registry_membership"
    }
    assert module_functions == {"build_membership", "main", "render_markdown"}
    for name in ("_embedded_entries", "_membership", "_verify_report", "_field_classes"):
        helper = getattr(research_registry_membership, name)
        assert callable(helper)
        assert FORBIDDEN_NAMES.search(name) is None
        assert "kwargs" not in str(inspect.signature(helper))
    assert research_registry_membership.SCHEMA == "m4_registry_snapshot_membership_v1"
    assert (
        research_registry_membership.STATUS_IDENTICAL,
        research_registry_membership.STATUS_DIFFERENT,
        research_registry_membership.STATUS_ABSENT,
    ) == ("registered_identical", "registered_different", "not_registered")
    assert research_registry_membership.IDENTITY_KEYS == (
        "hypothesis_id",
        "hypothesis_version",
        "status",
        "identity_digest",
        "record_digest",
        "state_count",
    )
    names = [command.name for command in research_entry.COMMANDS]
    assert names.count("registry-membership") == 1
    assert names.index("registry-membership") == names.index("registry") + 1
    command = research_entry.COMMANDS[names.index("registry-membership")]
    assert command.module == "ashare_research.tools.research_registry_membership"
    assert len(command.usage) == 1
    assert "--record" in command.usage[0] and "--snapshot" in command.usage[0]
