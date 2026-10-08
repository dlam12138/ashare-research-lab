"""Focused saved-delivery views always follow complete original reproduction."""

import hashlib
import json
import socket
import zipfile
from contextlib import contextmanager
from pathlib import Path

import duckdb
import pytest
from test_preparation_diagnostics import _sources, _write_invented

from ashare_research import cli
from ashare_research.mechanism import execution, pipeline
from ashare_research.tools import preparation_archive as archive
from ashare_research.tools import preparation_diagnostics as diagnostics
from ashare_research.tools import preparation_package as package
from ashare_research.tools import synthetic_prepare


def _delivery(tmp_path, state="ready"):
    plan, _, inputs = _sources(tmp_path)
    if state != "ready":
        document = json.loads(inputs.read_bytes())
        if state == "empty":
            document["observations"] = []
        else:
            document["observations"][0]["value"] = None
            document["observations"][0]["available_on"] = None
        _write_invented(document, inputs)
    delivery, zipped = tmp_path / "delivery", tmp_path / "delivery.zip"
    package.export_package(plan, inputs, delivery)
    archive.export_archive(delivery, zipped)
    return plan, inputs, delivery, zipped


def _args(source, *, zipped=False):
    return ["research", "prepare-package", "--verify-archive" if zipped else "--verify",
            str(source), "--summary"]


@pytest.mark.parametrize("state", ["ready", "rejected", "empty"])
def test_public_exact_projector_sides_identities_legacy_and_offline(
    tmp_path, monkeypatch, capsys, state,
):
    plan, inputs, delivery, zipped = _delivery(tmp_path, state)
    original = synthetic_prepare.build_report(plan, inputs)
    expected = diagnostics.build_summary(original, roles=[], gaps_only=False)
    directory_receipt = package.verify_package(delivery)
    archive_receipt = archive.verify_archive(zipped)
    sources = [inputs, zipped, *plan.iterdir(), *delivery.iterdir()]
    snapshot = {path: path.read_bytes() for path in sources}

    def forbidden(*args, **kwargs):
        raise AssertionError("No external sources, services, extraction, writes or statistics")

    for name in ("load_config", "setup_logging", "_create_service"):
        monkeypatch.setattr(cli, name, forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(duckdb, "connect", forbidden)
    monkeypatch.setattr(pipeline, "run_synthetic_pipeline", forbidden)
    monkeypatch.setattr(execution, "execute_bounded_analysis", forbidden)
    monkeypatch.setattr(zipfile.ZipFile, "extract", forbidden)
    monkeypatch.setattr(zipfile.ZipFile, "extractall", forbidden)
    monkeypatch.setattr(Path, "mkdir", forbidden)
    monkeypatch.setattr(synthetic_prepare, "build_report", forbidden)
    monkeypatch.setattr(synthetic_prepare, "read_input_bytes", forbidden)
    for source, is_zip, receipt in (
        (delivery, False, directory_receipt), (zipped, True, archive_receipt),
    ):
        args = _args(source, zipped=is_zip)
        assert cli.main([*args, "--json"]) == 0
        captured = capsys.readouterr()
        assert captured.err == "" and json.loads(captured.out) == expected
        assert cli.main(args) == 0
        assert capsys.readouterr().out == diagnostics.render_markdown(expected)
        assert cli.main([*args[:-1], "--json"]) == 0
        assert json.loads(capsys.readouterr().out) == receipt
    assert expected["quality"] == original["dataset"]["quality"]
    assert expected["boundary"] == original["boundary"]
    assert expected["selection"]["shown_cells"] == 16
    assert expected["status"] == ("READY_SYNTHETIC" if state == "ready" else "REJECTED_QUALITY")
    assert not expected["boundary"]["statistics_computed"]
    if state == "empty":
        assert not any(expected["boundary"].values())
        assert expected["quality"]["coverage_denominator"] == 4
        assert expected["quality"]["reason_counts"] == {"MISSING_OBSERVATION": 16}
    assert {path: path.read_bytes() for path in sources} == snapshot


def test_repeated_roles_gaps_and_no_matching_gaps_keep_original_global_rejection(tmp_path, capsys):
    _, _, delivery, zipped = _delivery(tmp_path, "rejected")
    original = package.verify_package(delivery)["report"]
    options = ["--role", "FACTOR", "--role", "TARGET_OUTCOME", "--role", "FACTOR", "--gaps-only"]
    expected = diagnostics.build_summary(
        original, roles=["FACTOR", "TARGET_OUTCOME", "FACTOR"], gaps_only=True,
    )
    for source, is_zip in ((delivery, False), (zipped, True)):
        args = [*_args(source, zipped=is_zip), *options]
        assert cli.main([*args, "--json"]) == 0
        captured = capsys.readouterr()
        assert captured.err == "" and json.loads(captured.out) == expected
        assert expected["selection"]["role_order"] == ["TARGET_OUTCOME", "FACTOR"]
        assert expected["selection"]["shown_cells"] == expected["selection"]["shown_dates"] == 1
        assert expected["quality"]["coverage_numerator"] == 3
        assert expected["quality"]["coverage_denominator"] == 4
        assert expected["role_diagnostics"][0]["audited_dates"] == 4
        assert expected["role_diagnostics"][0]["reason_counts"] == {
            "MISSING_VALUE": 1, "PIT_UNPROVEN": 1,
        }
        assert expected["role_diagnostics"][1]["valid_cells"] == 4
        assert expected["matrix_identity"] is None
        cell = expected["rows"][0]["cells"][0]
        assert cell == {key: original["dataset"]["audit_rows"][0]["cells"][0][key]
                        for key in diagnostics.CELL_FIELDS}
        assert "value" not in cell
        assert cli.main(args) == 0
        assert capsys.readouterr().out == diagnostics.render_markdown(expected)
        assert cli.main([*_args(source, zipped=is_zip), "--role", "FACTOR",
                         "--gaps-only", "--json"]) == 0
        empty = json.loads(capsys.readouterr().out)
        assert empty == diagnostics.build_summary(original, roles=["FACTOR"], gaps_only=True)
        assert empty["selection"]["status"] == "NO_MATCHING_GAPS"
        assert empty["rows"] == [] and empty["status"] == "REJECTED_QUALITY"
        assert empty["quality"] == expected["quality"]
        assert "没有匹配的缺口" in diagnostics.render_markdown(empty)


@pytest.mark.parametrize("is_zip", [False, True])
def test_single_verifier_and_once_read_snapshot_handoff(tmp_path, monkeypatch, capsys, is_zip):
    _, _, delivery, zipped = _delivery(tmp_path, "rejected")
    report = package.verify_package(delivery)["report"]
    expected = diagnostics.build_summary(report, roles=["TARGET_OUTCOME"], gaps_only=True)
    source = zipped if is_zip else delivery
    snapshots = ({zipped: zipped.read_bytes()} if is_zip
                 else {path: path.read_bytes() for path in delivery.iterdir()})
    module = archive if is_zip else package
    name = "verify_archive" if is_zip else "verify_package"
    original_verify = getattr(module, name)
    calls = []
    reads = []
    original_open = Path.open

    def verified_once(path):
        calls.append(path)
        return original_verify(path)

    @contextmanager
    def mutate_after_read(path, mode="r", *rest, **kwargs):
        with original_open(path, mode, *rest, **kwargs) as stream:
            yield stream
        if mode == "rb" and path in snapshots:
            reads.append(path)
            with original_open(path, "wb") as output:
                output.write(b"changed after captured read")

    monkeypatch.setattr(module, name, verified_once)
    monkeypatch.setattr(Path, "open", mutate_after_read)
    assert cli.main([*_args(source, zipped=is_zip), "--role", "TARGET_OUTCOME",
                     "--gaps-only", "--json"]) == 0
    captured = capsys.readouterr()
    assert captured.err == "" and json.loads(captured.out) == expected
    assert calls == [source]
    assert len(reads) == (1 if is_zip else 10) and set(reads) == set(snapshots)


def test_hidden_forgery_stale_sources_and_all_files_fail_before_projection(
    tmp_path, monkeypatch, capsys,
):
    _, _, delivery, zipped = _delivery(tmp_path, "rejected")
    snapshot = {path.name: path.read_bytes() for path in delivery.iterdir()}
    forged = dict(snapshot)
    document = json.loads(forged["preparation.json"])
    # TARGET_OUTCOME will be hidden by FACTOR/gaps-only, but must still be verified.
    document["dataset"]["audit_rows"][0]["cells"][0]["source_record_id"] = "FORGED_UNSHOWN"
    forged["preparation.json"] = json.dumps(document).encode()
    manifest = json.loads(forged["manifest.json"])
    entry = next(row for row in manifest["files"] if row["path"] == "preparation.json")
    entry["sha256"] = hashlib.sha256(forged["preparation.json"]).hexdigest()
    entry["byte_count"] = len(forged["preparation.json"])
    forged["manifest.json"] = json.dumps(manifest).encode()

    def rejected(files, code):
        for name, raw in files.items():
            (delivery / name).write_bytes(raw)
        zipped.write_bytes(archive._encode(files))
        for source, is_zip in ((delivery, False), (zipped, True)):
            assert cli.main([*_args(source, zipped=is_zip), "--role", "FACTOR",
                             "--gaps-only", "--json"]) == 2
            captured = capsys.readouterr()
            assert captured.out == "" and captured.err == f"error: {code}\n"

    rejected(forged, "PREPARATION_PACKAGE_MISMATCH")
    altered = dict(snapshot)
    altered["diagnostics.md"] += b"changed saved Markdown"
    rejected(altered, "PREPARATION_PACKAGE_MISMATCH")
    altered = dict(snapshot)
    inputs = json.loads(altered["inputs.json"])
    inputs["observations"][0]["value"] = "0.123"
    altered["inputs.json"] = json.dumps(inputs).encode()
    rejected(altered, "EVIDENCE_DIGEST_MISMATCH")
    altered = dict(snapshot)
    altered["plan-plan.json"] = b"{}"
    rejected(altered, "PLAN_PACKAGE_MISMATCH")
    # An unknown selector cannot mask complete source corruption either.
    assert cli.main([*_args(delivery), "--role", "CONTROL_9999", "--json"]) == 2
    captured = capsys.readouterr()
    assert captured.out == "" and captured.err == "error: PLAN_PACKAGE_MISMATCH\n"


def test_invalid_selectors_before_io_unknown_after_verification_and_link_gate(
    tmp_path, monkeypatch, capsys,
):
    plan, inputs, delivery, zipped = _delivery(tmp_path)

    def rejected(options, code):
        assert cli.main(options) == 2
        captured = capsys.readouterr()
        assert captured.out == "" and captured.err == f"error: {code}\n"

    def forbidden(*args, **kwargs):
        raise AssertionError("Invalid mode/selector rejects before any verifier/exporter IO")

    with monkeypatch.context() as scoped:
        for module, name in ((package, "verify_package"), (archive, "verify_archive"),
                             (package, "export_package"), (archive, "export_from_plan"),
                             (archive, "export_archive")):
            scoped.setattr(module, name, forbidden)
        for source, is_zip in ((delivery, False), (zipped, True)):
            args = _args(source, zipped=is_zip)
            rejected([*args[:-1], "--role", "FACTOR"], "INVALID_ARGUMENTS")
            rejected([*args[:-1], "--gaps-only"], "INVALID_ARGUMENTS")
            for role in ("", "factor", "CONTROL_001"):
                rejected([*args, "--role", role], "INVALID_ROLE")
            rejected([*args, "--execute"], "INVALID_ARGUMENTS")
            rejected([*args, "--output", "new"], "INVALID_ARGUMENTS")
        for options in (
            ["--package", str(plan), "--inputs", str(inputs), "--output", "new"],
            ["--plan-archive", "plan.zip", "--inputs", str(inputs), "--output-archive", "new"],
            ["--archive", str(delivery), "--output", "new.zip"],
        ):
            rejected(["research", "prepare-package", *options, "--summary"], "INVALID_ARGUMENTS")
    original_verify = package.verify_package
    calls = []

    def counted(path):
        calls.append(path)
        return original_verify(path)

    with monkeypatch.context() as scoped:
        scoped.setattr(package, "verify_package", counted)
        rejected([*_args(delivery), "--role", "CONTROL_9999", "--json"], "UNKNOWN_ROLE")
    assert calls == [delivery]
    original_lstat = Path.lstat

    class Reparse:
        st_mode = 0o40755
        st_file_attributes = 0x400

    with monkeypatch.context() as scoped:
        scoped.setattr(Path, "lstat", lambda path, **kw: (
            Reparse() if path == delivery else original_lstat(path, **kw)
        ))
        rejected([*_args(delivery), "--role", "FACTOR", "--gaps-only", "--json"],
                 "LINKED_PREPARATION_PACKAGE_PATH")
