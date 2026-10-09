"""Read-only M4-B registry comparison class summary: projection only, no writes."""

from __future__ import annotations

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
NEW_PRIVATE_HELPERS = {
    "_build_summary",
    "_record_field_classes",
    "_record_summary",
    "_render_summary_markdown",
    "_snapshot_summary",
    "_summary_fail",
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


def _advance(record, to_state: str = "LITERATURE_REVIEWED"):
    return transition_hypothesis_record(
        record,
        StateTransitionRequestV1(
            record.hypothesis_id,
            record.hypothesis_version,
            record.status,
            to_state,
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


def _summary(left: Path, right: Path, capsys) -> dict:
    output = _run_ok(
        [
            "research",
            "registry-compare",
            "--left",
            str(left),
            "--right",
            str(right),
            "--summary",
            "--json",
        ],
        capsys,
    )
    return json.loads(output)


def test_record_summary_exact_projection_and_entry_delegation(tmp_path, capsys):
    left_record = _record()
    right_record = _record(version=2, theory="SYNTHETIC_EXAMPLE_THEORY_V2")
    left_payload = _record_bytes(left_record)
    right_payload = _record_bytes(right_record)
    left = _write(tmp_path, "left.json", left_payload)
    right = _write(tmp_path, "right.json", right_payload)
    comparison = research_registry_compare.build_comparison(left_payload, right_payload)
    expected = research_registry_compare._build_summary(comparison)

    delegated = _run_ok(
        [
            "research",
            "registry-compare",
            "--summary",
            "--left",
            str(left),
            "--right",
            str(right),
            "--json",
        ],
        capsys,
    )
    assert delegated == research_registry_compare._json(expected) + "\n"
    assert research_registry_compare.main(
        ["--left", str(left), "--right", str(right), "--summary"],
    ) == 0
    direct = capsys.readouterr()
    assert direct.err == ""
    assert direct.out == research_registry_compare._render_summary_markdown(expected)

    assert expected["schema"] == research_registry_compare.SUMMARY_SCHEMA
    assert expected["status"] == research_registry_compare.SUMMARY_STATUS
    assert expected["kind"] == "record" and expected["byte_identical"] is False
    assert expected["boundary"] == research_registry.BOUNDARY
    assert expected["notes"] == list(research_registry_compare.SUMMARY_NOTES)
    payload = expected["summary"]
    assert payload["changed_field_class_counts"] == {"identity": 2, "mutable": 0, "digest": 2}
    assert payload["changed_fields_by_class"] == {
        "identity": ["hypothesis_version", "theory"],
        "mutable": [],
        "digest": ["identity_digest", "record_digest"],
    }
    assert payload["changed_field_count"] == 4
    assert payload["unchanged_field_count"] == 22 and payload["field_count"] == 26
    assert payload["record_equal"] is False
    assert payload["equality"] == {
        "hypothesis_id": True,
        "hypothesis_version": False,
        "status": True,
        "identity_digest": False,
        "record_digest": False,
        "state_count": True,
    }
    markdown = research_registry_compare._render_summary_markdown(expected)
    assert "| identity | 2 |" in markdown and "| digest | 2 |" in markdown
    assert "- identity: hypothesis_version、theory" in markdown
    assert "- mutable: （无变更）" in markdown
    assert "m4_registry_comparison_summary_v1" in research_registry_compare._json(expected)


def test_status_pair_class_partition_and_legacy_bytes_unchanged(tmp_path, capsys):
    left_record = _record()
    right_record = _advance(left_record)
    left_payload = _record_bytes(left_record)
    right_payload = _record_bytes(right_record)
    left = _write(tmp_path, "left.json", left_payload)
    right = _write(tmp_path, "right.json", right_payload)
    comparison = research_registry_compare.build_comparison(left_payload, right_payload)

    payload = _summary(left, right, capsys)["summary"]
    assert payload["changed_field_class_counts"] == {"identity": 0, "mutable": 2, "digest": 1}
    assert payload["changed_fields_by_class"]["mutable"] == ["status", "state_history"]
    assert payload["changed_fields_by_class"]["identity"] == []
    assert payload["changed_fields_by_class"]["digest"] == ["record_digest"]
    assert payload["equality"] == {
        "hypothesis_id": True,
        "hypothesis_version": True,
        "status": False,
        "identity_digest": True,
        "record_digest": False,
        "state_count": False,
    }

    legacy = json.loads(
        _run_ok(
            ["research", "registry-compare", "--left", str(left), "--right", str(right),
             "--json"],
            capsys,
        ),
    )
    assert legacy == comparison
    assert set(legacy) == {
        "schema", "status", "kind", "byte_identical", "left", "right", "differences",
        "boundary", "notes",
    }
    assert legacy["schema"] == research_registry_compare.SCHEMA
    legacy_markdown = _run_ok(
        ["research", "registry-compare", "--left", str(left), "--right", str(right)],
        capsys,
    )
    assert legacy_markdown == research_registry_compare.render_markdown(comparison)


def test_snapshot_summary_counts_rows_order_and_accounting(tmp_path, capsys):
    base = _record()
    bumped = _record(version=2, theory="SYNTHETIC_EXAMPLE_THEORY_V2")
    advanced = _advance(_record("SYNTH_EXAMPLE_0002"))
    left_payload = _snapshot_bytes(
        base, _record("SYNTH_EXAMPLE_0002"), _record("SYNTH_EXAMPLE_0003"),
    )
    right_payload = _snapshot_bytes(
        bumped, advanced, _record("SYNTH_EXAMPLE_0004"),
    )
    left = _write(tmp_path, "left.json", left_payload)
    right = _write(tmp_path, "right.json", right_payload)
    comparison = research_registry_compare.build_comparison(left_payload, right_payload)
    summary = research_registry_compare._build_summary(comparison)
    assert summary["kind"] == "snapshot" and summary["byte_identical"] is False
    payload = summary["summary"]
    assert payload["registry_equal"] is False
    assert payload["equality"] == {
        "registry_schema_version": True,
        "registry_version": True,
        "registry_digest": False,
        "record_count": True,
        "real_demo_candidate_count": True,
    }
    assert payload["record_change_counts"] == {
        "added": 2, "removed": 2, "changed": 1, "unchanged": 0,
    }
    assert payload["added"] == ["SYNTH_EXAMPLE_0001@2", "SYNTH_EXAMPLE_0004@1"]
    assert payload["removed"] == ["SYNTH_EXAMPLE_0001@1", "SYNTH_EXAMPLE_0003@1"]
    assert payload["changed"] == ["SYNTH_EXAMPLE_0002@1"]

    delegated = json.loads(
        _run_ok(
            ["research", "registry-compare", "--left", str(left), "--right", str(right),
             "--summary", "--json"],
            capsys,
        ),
    )
    assert delegated == json.loads(research_registry_compare._json(summary) + "\n")
    identical = research_registry_compare._build_summary(
        research_registry_compare.build_comparison(left_payload, left_payload),
    )
    assert identical["summary"]["registry_equal"] is True
    assert all(identical["summary"]["equality"].values())
    assert identical["summary"]["record_change_counts"] == {
        "added": 0, "removed": 0, "changed": 0, "unchanged": 3,
    }


def test_doctored_report_invariant_guards_fail_closed(tmp_path, capsys, monkeypatch):
    base = _record()
    advanced = _advance(base)
    left_payload = _record_bytes(base)
    right_payload = _record_bytes(advanced)
    left = _write(tmp_path, "left.json", left_payload)
    right = _write(tmp_path, "right.json", right_payload)
    record_comparison = research_registry_compare.build_comparison(left_payload, right_payload)
    snapshot_comparison = research_registry_compare.build_comparison(
        _snapshot_bytes(base, _record("SYNTH_EXAMPLE_0002")),
        _snapshot_bytes(advanced, _record("SYNTH_EXAMPLE_0002")),
    )

    def mismatch(comparison: dict) -> None:
        with pytest.raises(research_registry_compare.ComparisonError) as captured:
            research_registry_compare._build_summary(comparison)
        assert captured.value.code == "REGISTRY_COMPARISON_SUMMARY_MISMATCH"

    def clone(comparison: dict) -> dict:
        return json.loads(json.dumps(comparison))

    doctored = clone(record_comparison)
    doctored["differences"]["changed_field_count"] += 1
    mismatch(doctored)
    doctored = clone(record_comparison)
    doctored["differences"]["changed_fields"].pop()
    mismatch(doctored)
    doctored = clone(record_comparison)
    doctored["differences"]["record_equal"] = True
    mismatch(doctored)
    doctored = clone(record_comparison)
    doctored["differences"]["equality"]["status"] = True
    mismatch(doctored)
    doctored = clone(record_comparison)
    doctored["differences"]["changed_fields"].append(
        {"field": "unknown_field", "left": 1, "right": 2},
    )
    doctored["differences"]["changed_field_count"] += 1
    mismatch(doctored)
    doctored = clone(record_comparison)
    doctored["boundary"] = {**doctored["boundary"], "registry_written": True}
    mismatch(doctored)
    assert research_registry_compare._build_summary(record_comparison)["kind"] == "record"

    doctored = clone(snapshot_comparison)
    doctored["differences"]["added_count"] += 1
    mismatch(doctored)
    doctored = clone(snapshot_comparison)
    doctored["differences"]["changed"] = []
    mismatch(doctored)
    doctored = clone(snapshot_comparison)
    doctored["differences"]["changed"][0]["left"] = doctored["differences"]["changed"][0]["right"]
    mismatch(doctored)
    doctored = clone(snapshot_comparison)
    doctored["left"]["file_sha256"] = doctored["right"]["file_sha256"]
    mismatch(doctored)
    assert research_registry_compare._build_summary(snapshot_comparison)["kind"] == "snapshot"

    doctored_builder_report = clone(record_comparison)
    doctored_builder_report["differences"]["changed_field_count"] += 1
    monkeypatch.setattr(
        research_registry_compare,
        "build_comparison",
        lambda _left, _right: doctored_builder_report,
    )
    assert research_registry_compare.main(
        ["--left", str(left), "--right", str(right), "--summary"],
    ) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == "error: REGISTRY_COMPARISON_SUMMARY_MISMATCH\n"


def test_summary_argument_shapes_and_read_failures_rejected(tmp_path, capsys, monkeypatch):
    missing = tmp_path / "missing.json"
    shapes = (
        ["research", "registry-compare", "--summary"],
        ["research", "registry-compare", "--summary", "--left", str(missing)],
        ["research", "registry-compare", "--summary", "--right", str(missing)],
        ["research", "registry-compare", "--summary", "--left", str(missing), "--bogus"],
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
    assert "--summary" in help_text.out and "--left" in help_text.out
    _rejected(
        ["research", "registry-compare", "--left", str(missing), "--right", str(missing),
         "--summary"],
        "REGISTRY_READ_FAILED",
        capsys,
    )
    oversize = _write(tmp_path, "oversize.json", b"{" + b"0" * 1_048_576)
    _rejected(
        ["research", "registry-compare", "--left", str(oversize), "--right", str(oversize),
         "--summary"],
        "REGISTRY_TOO_LARGE",
        capsys,
    )


def test_summary_single_read_offline_no_write_and_determinism(tmp_path, capsys, monkeypatch):
    left_payload = _record_bytes(_record())
    right_payload = _record_bytes(_record(version=2, theory="SYNTHETIC_EXAMPLE_THEORY_V2"))
    left = _write(tmp_path, "left.json", left_payload)
    right = _write(tmp_path, "right.json", right_payload)
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
        "research", "registry-compare", "--left", str(left), "--right", str(right),
        "--summary", "--json",
    ]
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


def test_summary_surface_bounded_and_delegated_failure_codes(tmp_path, capsys):
    public = {name for name in registry.__all__ if inspect.isfunction(getattr(registry, name))}
    assert public == PUBLIC_FUNCTIONS and len(public) == 13
    module_functions = {
        name
        for name in dir(research_registry_compare)
        if not name.startswith("_")
        and inspect.isfunction(getattr(research_registry_compare, name))
        and getattr(research_registry_compare, name).__module__
        == "ashare_research.tools.research_registry_compare"
    }
    assert module_functions == {"build_comparison", "main", "render_markdown"}
    for name in NEW_PRIVATE_HELPERS:
        helper = getattr(research_registry_compare, name)
        assert callable(helper)
        assert FORBIDDEN_NAMES.search(name) is None
        assert "kwargs" not in str(inspect.signature(helper))
    classes = research_registry_compare._record_field_classes()
    assert len(classes) == 26
    assert sum(value == "identity" for value in classes.values()) == 22
    assert sum(value == "mutable" for value in classes.values()) == 2
    assert sum(value == "digest" for value in classes.values()) == 2
    assert classes["status"] == "mutable" and classes["state_history"] == "mutable"
    assert classes["identity_digest"] == "digest" and classes["record_digest"] == "digest"
    assert research_registry_compare.RECORD_CLASS_ORDER == ("identity", "mutable", "digest")
    assert research_registry_compare.DIGEST_COVERAGE == {
        "identity_digest": ("identity",),
        "record_digest": ("identity", "mutable"),
    }
    names = [command.name for command in research_entry.COMMANDS]
    command = research_entry.COMMANDS[names.index("registry-compare")]
    assert names.count("registry-compare") == 1
    assert len(command.usage) == 1
    assert "--left" in command.usage[0] and "--right" in command.usage[0]
    assert "--summary" in command.usage[0]

    left_payload = _record_bytes(_record())
    right_payload = _record_bytes(_record(version=2, theory="SYNTHETIC_EXAMPLE_THEORY_V2"))
    left = _write(tmp_path, "left.json", left_payload)
    right = _write(tmp_path, "right.json", right_payload)
    legacy = _run_ok(
        ["research", "registry-compare", "--left", str(left), "--right", str(right), "--json"],
        capsys,
    )
    assert legacy == research_registry_compare._json(
        research_registry_compare.build_comparison(left_payload, right_payload),
    ) + "\n"
    mixed = _write(tmp_path, "mixed.json", _snapshot_bytes(_record()))
    _rejected(
        ["research", "registry-compare", "--left", str(left), "--right", str(mixed),
         "--summary"],
        "INCOMPARABLE_ARTIFACT_KINDS",
        capsys,
    )
