"""Read-only M4-B registry view: exact projection, fail-closed bytes, no writes."""

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
    INTERPRETATION_BOUNDARY,
    RECORD_SCHEMA_VERSION,
    build_hypothesis_registry_snapshot,
    hypothesis_record_digest,
    hypothesis_record_identity_digest,
    hypothesis_record_to_canonical_dict,
    parse_hypothesis_record,
    serialize_hypothesis_record,
    serialize_hypothesis_registry_snapshot,
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


def _doc(identifier: str, *, version: int = 1, feasibility: str = "FEASIBLE_FREE") -> dict:
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
        "a_share_data_feasibility": feasibility,
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


def _record(identifier: str, *, version: int = 1, feasibility: str = "FEASIBLE_FREE"):
    document = _doc(identifier, version=version, feasibility=feasibility)
    document["identity_digest"] = hypothesis_record_identity_digest(document)
    document["record_digest"] = hypothesis_record_digest(document)
    return parse_hypothesis_record(document)


def _canonical(document: dict) -> bytes:
    return (
        json.dumps(document, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
    ).encode("utf-8")


def _write_record(tmp_path: Path, record, name: str = "record.json") -> Path:
    path = tmp_path / name
    path.write_bytes(serialize_hypothesis_record(record))
    return path


def _write_snapshot(tmp_path: Path, records, name: str = "snapshot.json") -> Path:
    path = tmp_path / name
    path.write_bytes(serialize_hypothesis_registry_snapshot(
        build_hypothesis_registry_snapshot(tuple(records))
    ))
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


def test_record_view_exact_projection_and_entry_delegation(tmp_path, capsys):
    record = _record("SYNTH_EXAMPLE_0001")
    payload = serialize_hypothesis_record(record)
    source = tmp_path / "record.json"
    source.write_bytes(payload)
    expected = research_registry.build_record_view(payload)

    delegated = _run_ok(
        ["research", "registry", "--record", str(source), "--json"], capsys,
    )
    assert delegated == research_registry._json(expected) + "\n"
    assert research_registry.main(["--record", str(source), "--json"]) == 0
    direct = capsys.readouterr()
    assert direct.err == "" and direct.out == delegated
    assert research_entry.main(["registry", "--record", str(source), "--json"]) == 0
    entry = capsys.readouterr()
    assert entry.err == "" and entry.out == delegated

    view = json.loads(delegated)
    assert view["schema"] == research_registry.SCHEMA_RECORD_VIEW
    assert view["status"] == research_registry.VIEW_STATUS == "validated_metadata_only"
    assert view["source_file_sha256"] == hashlib.sha256(payload).hexdigest()
    assert view["record"] == hypothesis_record_to_canonical_dict(record)
    assert view["digests"] == {
        "identity_digest": record.identity_digest,
        "record_digest": record.record_digest,
        "identity_digest_recomputed": hypothesis_record_identity_digest(record),
        "record_digest_recomputed": hypothesis_record_digest(record),
    }
    assert view["verification"] == {
        "canonical_bytes_verified": True,
        "identity_digest_verified": True,
        "record_digest_verified": True,
    }
    assert view["boundary"] == {
        "execution_authorized": False,
        "statistics_computed": False,
        "outcome_read": False,
        "holdout_accessed": False,
        "real_registry_dataset_loaded": False,
        "registry_written": False,
    }
    assert view["notes"] == [research_registry.RECORD_NOTE, *research_registry.COMMON_NOTES]

    assert "registry" in {item.name for item in research_entry.COMMANDS}
    assert "ashare-research research registry --help" in research_entry.USAGE
    markdown = _run_ok(["research", "registry", "--record", str(source)], capsys)
    assert markdown == research_registry.render_record_markdown(expected)
    assert "# M4-B 假设记录只读视图" in markdown
    assert '"hypothesis_id": "SYNTH_EXAMPLE_0001"' in markdown
    assert "## 状态历史" in markdown and "## 规范记录" in markdown


def test_snapshot_view_exact_projection_counts_and_order(tmp_path, capsys):
    first = _record("SYNTH_EXAMPLE_0001")
    second = _record("SYNTH_EXAMPLE_0002", feasibility="FEASIBLE_PAID")
    third = _record("SYNTH_EXAMPLE_0003", feasibility="NOT_FEASIBLE")
    snapshot = build_hypothesis_registry_snapshot((third, first, second))
    payload = serialize_hypothesis_registry_snapshot(snapshot)
    source = tmp_path / "snapshot.json"
    source.write_bytes(payload)

    delegated = _run_ok(
        ["research", "registry", "--snapshot", str(source), "--json"], capsys,
    )
    view = json.loads(delegated)
    assert view == research_registry.build_snapshot_view(payload)
    assert view["schema"] == research_registry.SCHEMA_SNAPSHOT_VIEW
    assert view["status"] == "validated_metadata_only"
    assert view["source_file_sha256"] == hashlib.sha256(payload).hexdigest()
    assert view["registry"] == {
        "registry_schema_version": "M4_HYPOTHESIS_REGISTRY_SNAPSHOT_V1",
        "registry_version": "M4_THEORY_HYPOTHESIS_REGISTRY_V1",
        "digest_algorithm": "M4_HYPOTHESIS_REGISTRY_SHA256_CANONICAL_JSON_V1",
        "record_count": 3,
        "real_demo_candidate_count": 2,
        "max_records_per_snapshot": 3,
        "max_real_demo_candidates": 3,
        "registry_digest": snapshot.registry_digest,
    }
    assert [item["hypothesis_id"] for item in view["records"]] == [
        "SYNTH_EXAMPLE_0001", "SYNTH_EXAMPLE_0002", "SYNTH_EXAMPLE_0003",
    ]
    assert [item["status"] for item in view["records"]] == ["DISCOVERED"] * 3
    assert [item["state_count"] for item in view["records"]] == [1, 1, 1]
    assert view["interpretation_boundary"] == INTERPRETATION_BOUNDARY
    assert view["verification"] == {
        "canonical_bytes_verified": True,
        "registry_digest_verified": True,
        "records_digests_verified": True,
        "scale_limits_respected": True,
    }
    assert all(value is False for value in view["boundary"].values())
    assert view["notes"] == [research_registry.SNAPSHOT_NOTE, *research_registry.COMMON_NOTES]

    markdown = _run_ok(["research", "registry", "--snapshot", str(source)], capsys)
    assert markdown == research_registry.render_snapshot_markdown(view)
    assert "# M4-B registry 快照只读视图" in markdown
    assert "| SYNTH_EXAMPLE_0001 | 1 | DISCOVERED | FEASIBLE_FREE | SUFFICIENT |" in markdown
    assert "REGISTRY_METADATA_ONLY" in markdown


def test_canonical_byte_violations_fail_closed(tmp_path, capsys):
    record_payload = serialize_hypothesis_record(_record("SYNTH_EXAMPLE_0001"))
    snapshot_payload = serialize_hypothesis_registry_snapshot(
        build_hypothesis_registry_snapshot((_record("SYNTH_EXAMPLE_0001"),))
    )
    floating = record_payload.replace(
        b'"hypothesis_version":1', b'"hypothesis_version":1.0',
    )
    assert floating != record_payload
    duplicated = record_payload.replace(
        b'"status":"DISCOVERED"', b'"status":"DISCOVERED","status":"DISCOVERED"',
    )
    assert duplicated != record_payload
    cases = (
        ("record-bom.json", b"\xef\xbb\xbf" + record_payload, "--record"),
        ("record-cr.json", record_payload.replace(b"\n", b"\r\n"), "--record"),
        ("record-no-lf.json", record_payload.rstrip(b"\n"), "--record"),
        ("record-double-lf.json", record_payload + b"\n", "--record"),
        ("record-float.json", floating, "--record"),
        ("record-duplicate-key.json", duplicated, "--record"),
        ("snapshot-bom.json", b"\xef\xbb\xbf" + snapshot_payload, "--snapshot"),
        ("snapshot-no-lf.json", snapshot_payload.rstrip(b"\n"), "--snapshot"),
    )
    for name, payload, flag in cases:
        source = tmp_path / name
        source.write_bytes(payload)
        _rejected(
            ["research", "registry", flag, str(source), "--json"],
            "NON_CANONICAL_SERIALIZATION", capsys,
        )


def test_record_integrity_failures_use_stable_codes(tmp_path, capsys):
    document = json.loads(serialize_hypothesis_record(_record("SYNTH_EXAMPLE_0001")))

    def mutated(name: str, mutate) -> Path:
        candidate = json.loads(json.dumps(document))
        mutate(candidate)
        path = tmp_path / name
        path.write_bytes(_canonical(candidate))
        return path

    def flip_field(field: str):
        return lambda candidate: candidate.__setitem__(
            field, ("0" if candidate[field][0] != "0" else "1") + candidate[field][1:],
        )

    def illegal_reason(candidate):
        candidate["status"] = "LITERATURE_REVIEWED"
        candidate["state_history"].append({
            "ordinal": 2,
            "from_state": "DISCOVERED",
            "to_state": "LITERATURE_REVIEWED",
            "reason_code": "PRE_REGISTRATION_REGISTERED",
            "authorization_ref": None,
            "evidence_kind": None,
        })

    cases = (
        ("identity.json", flip_field("identity_digest"), "IDENTITY_DIGEST_MISMATCH"),
        ("record-digest.json", flip_field("record_digest"), "RECORD_DIGEST_MISMATCH"),
        ("missing.json", lambda item: item.pop("theory"), "MISSING_REQUIRED_FIELD"),
        ("extra.json", lambda item: item.__setitem__("notes_extra", "x"),
         "UNKNOWN_RECORD_FIELD"),
        ("status.json", lambda item: item.__setitem__("status", "LITERATURE_REVIEWED"),
         "STATE_HISTORY_INCONSISTENT"),
        ("enum.json", lambda item: item.__setitem__("status", "BOGUS"),
         "INVALID_ENUM_VALUE"),
        ("transition.json", illegal_reason, "ILLEGAL_STATE_TRANSITION"),
    )
    for name, mutate, code in cases:
        source = mutated(name, mutate)
        _rejected(
            ["research", "registry", "--record", str(source), "--json"], code, capsys,
        )


def test_snapshot_integrity_failures_use_stable_codes(tmp_path, capsys):
    first = _record("SYNTH_EXAMPLE_0001")
    second = _record("SYNTH_EXAMPLE_0002", feasibility="NOT_FEASIBLE")
    snapshot = build_hypothesis_registry_snapshot((first, second))
    document = json.loads(serialize_hypothesis_registry_snapshot(snapshot))
    record_docs = [json.loads(serialize_hypothesis_record(item)) for item in (first, second)]

    def rewritten(name: str, mutate) -> Path:
        candidate = json.loads(json.dumps(document))
        mutate(candidate)
        path = tmp_path / name
        path.write_bytes(_canonical(candidate))
        return path

    def duplicate_same(candidate):
        candidate["records"].append(json.loads(json.dumps(record_docs[0])))

    def duplicate_rewrite(candidate):
        rewritten_doc = json.loads(json.dumps(record_docs[0]))
        for name in (
            "known_controls",
            "known_alternative_explanations",
            "known_replications",
            "known_failures_or_decay",
        ):
            rewritten_doc[name] = tuple(rewritten_doc[name])
        rewritten_doc["state_history"] = tuple(rewritten_doc["state_history"])
        rewritten_doc["source_title"] = "SYNTHETIC_EXAMPLE_TITLE_REWRITE"
        rewritten_doc["identity_digest"] = hypothesis_record_identity_digest(rewritten_doc)
        rewritten_doc["record_digest"] = hypothesis_record_digest(rewritten_doc)
        candidate["records"].append(json.loads(json.dumps(rewritten_doc)))

    def four_records(candidate):
        for suffix in ("0003", "0004"):
            extra = json.loads(serialize_hypothesis_record(
                _record(f"SYNTH_EXAMPLE_{suffix}", feasibility="NOT_FEASIBLE")
            ))
            candidate["records"].append(extra)
        candidate["records"].sort(key=lambda item: (item["hypothesis_id"], item[
            "hypothesis_version"]))

    cases = (
        ("order.json", lambda item: item["records"].reverse(), "INVALID_RECORD_STRUCTURE"),
        ("count.json", lambda item: item.__setitem__("real_demo_candidate_count", 0),
         "INVALID_FIELD_TYPE"),
        ("digest.json", lambda item: item.__setitem__("registry_digest", "0" * 64),
         "RECORD_DIGEST_MISMATCH"),
        ("version.json", lambda item: item.__setitem__("registry_version", "OTHER"),
         "INVALID_ENUM_VALUE"),
        ("boundary.json", lambda item: item.__setitem__("interpretation_boundary", "OTHER"),
         "INVALID_ENUM_VALUE"),
        ("extra.json", lambda item: item.__setitem__("extra", False),
         "UNKNOWN_RECORD_FIELD"),
        ("missing.json", lambda item: item.pop("registry_digest"),
         "MISSING_REQUIRED_FIELD"),
        ("records.json", lambda item: item.__setitem__("records", {}),
         "INVALID_RECORD_STRUCTURE"),
        ("scale.json", four_records, "SCALE_LIMIT_EXCEEDED"),
        ("duplicate.json", duplicate_same, "DUPLICATE_HYPOTHESIS_ID"),
        ("rewrite.json", duplicate_rewrite, "PROVENANCE_REWRITE"),
    )
    for name, mutate, code in cases:
        source = rewritten(name, mutate)
        _rejected(
            ["research", "registry", "--snapshot", str(source), "--json"], code, capsys,
        )
    pretty = tmp_path / "pretty.json"
    pretty.write_text(json.dumps(document, ensure_ascii=False, indent=2), encoding="utf-8")
    _rejected(
        ["research", "registry", "--snapshot", str(pretty), "--json"],
        "NON_CANONICAL_SERIALIZATION", capsys,
    )


def test_argument_shapes_and_read_failures(tmp_path, capsys):
    source = _write_record(tmp_path, _record("SYNTH_EXAMPLE_0001"))
    snapshot = _write_snapshot(tmp_path, (_record("SYNTH_EXAMPLE_0001"),))
    _rejected(["research", "registry"], "INVALID_ARGUMENTS", capsys)
    _rejected(
        ["research", "registry", "--record", str(source), "--snapshot", str(snapshot)],
        "INVALID_ARGUMENTS", capsys,
    )
    _rejected(
        ["research", "registry", "--record", str(source), "--bogus"],
        "INVALID_ARGUMENTS", capsys,
    )
    _rejected(
        ["research", "registry", "--record", str(tmp_path / "missing.json")],
        "REGISTRY_READ_FAILED", capsys,
    )
    _rejected(
        ["research", "registry", "--snapshot", str(tmp_path)],
        "REGISTRY_READ_FAILED", capsys,
    )
    oversized = tmp_path / "oversized.json"
    oversized.write_bytes(b"x" * (research_registry.MAX_INPUT_BYTES + 1))
    _rejected(
        ["research", "registry", "--record", str(oversized)],
        "REGISTRY_TOO_LARGE", capsys,
    )
    assert cli.main(["research", "registry", "--help"]) == 0
    help_text = capsys.readouterr()
    assert help_text.err == "" and "--snapshot" in help_text.out


def test_reads_once_and_never_writes(tmp_path, monkeypatch, capsys):
    source = _write_record(tmp_path, _record("SYNTH_EXAMPLE_0001"))
    snapshot = _write_snapshot(
        tmp_path,
        (_record("SYNTH_EXAMPLE_0001"), _record("SYNTH_EXAMPLE_0002", feasibility="NOT_FEASIBLE")),
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
    with monkeypatch.context() as scoped:
        scoped.setattr(Path, "open", tracker)
        _run_ok(["research", "registry", "--record", str(source), "--json"], capsys)
        assert reads == [source]
        reads.clear()
        _run_ok(["research", "registry", "--snapshot", str(snapshot)], capsys)
        assert reads == [snapshot]
    after = {path: path.read_bytes() for path in tmp_path.rglob("*") if path.is_file()}
    assert after == before


def test_registry_surface_and_view_are_deterministic(tmp_path, capsys):
    public = {
        name for name in registry.__all__ if inspect.isfunction(getattr(registry, name))
    }
    assert public == PUBLIC_FUNCTIONS and len(public) == 13
    view_functions = (
        "build_record_view", "build_snapshot_view", "main",
        "read_registry_bytes", "render_record_markdown", "render_snapshot_markdown",
        "strict_json_document",
    )
    for name in view_functions:
        function = getattr(research_registry, name)
        assert "kwargs" not in str(inspect.signature(function))
        assert FORBIDDEN_NAMES.search(name) is None
    record = _record("SYNTH_EXAMPLE_0001")
    payload = serialize_hypothesis_record(record)
    assert research_registry.build_record_view(payload) == research_registry.build_record_view(
        payload,
    )
    snapshot_payload = serialize_hypothesis_registry_snapshot(
        build_hypothesis_registry_snapshot((record,)),
    )
    first = research_registry.build_snapshot_view(snapshot_payload)
    second = research_registry.build_snapshot_view(snapshot_payload)
    assert first == second
    source = tmp_path / "record.json"
    source.write_bytes(payload)
    first_run = _run_ok(["research", "registry", "--record", str(source), "--json"], capsys)
    second_run = _run_ok(["research", "registry", "--record", str(source), "--json"], capsys)
    assert first_run == second_run
