"""Plan snapshots deliver identical preparation artifacts without intermediate paths."""

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
from ashare_research.tools import preparation_package as package
from ashare_research.tools import research_plan_archive, synthetic_prepare


def _args(plan, inputs, output, *, plan_zip=False, output_zip=False):
    return [
        "research", "prepare-package", "--plan-archive" if plan_zip else "--package", str(plan),
        "--inputs", str(inputs), "--output-archive" if output_zip else "--output", str(output),
        "--json",
    ]


@pytest.mark.parametrize("rejected", [False, True])
def test_four_public_combinations_exact_legacy_bytes_receipts_and_offline(
    tmp_path, monkeypatch, capsys, rejected,
):
    plan, plan_zip, inputs = _sources(tmp_path)
    if rejected:
        document = json.loads(inputs.read_bytes())
        document["observations"][0]["value"] = None
        _write_invented(document, inputs)
    legacy = tmp_path / "legacy"
    legacy_receipt = package.export_package(plan, inputs, legacy)
    legacy_zip = tmp_path / "legacy.zip"
    zip_receipt = archive.export_archive(legacy, legacy_zip)
    original_files = {path.name: path.read_bytes() for path in legacy.iterdir()}
    original_zip = legacy_zip.read_bytes()
    verified = package.verify_package(legacy)
    sources = [inputs, plan_zip, *plan.iterdir()]
    snapshot = {path: path.read_bytes() for path in sources}

    def forbidden(*args, **kwargs):
        raise AssertionError("No services, extraction, statistics or intermediate directories")

    for name in ("load_config", "setup_logging", "_create_service"):
        monkeypatch.setattr(cli, name, forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(duckdb, "connect", forbidden)
    monkeypatch.setattr(pipeline, "run_synthetic_pipeline", forbidden)
    monkeypatch.setattr(execution, "execute_bounded_analysis", forbidden)
    monkeypatch.setattr(zipfile.ZipFile, "extract", forbidden)
    monkeypatch.setattr(zipfile.ZipFile, "extractall", forbidden)
    for zipped_plan in (False, True):
        source = plan_zip if zipped_plan else plan
        for zipped_output in (False, True):
            target = tmp_path / f"new-{zipped_plan}-{zipped_output}"
            args = _args(source, inputs, target, plan_zip=zipped_plan, output_zip=zipped_output)
            with monkeypatch.context() as scoped:
                if zipped_output:
                    scoped.setattr(Path, "mkdir", forbidden)
                assert cli.main(args) == 0
            captured = capsys.readouterr()
            receipt = json.loads(captured.out)
            assert captured.err == ""
            if zipped_output:
                assert receipt == zip_receipt and target.read_bytes() == original_zip
                assert archive.verify_archive(target)["verification"] == verified
            else:
                assert receipt == legacy_receipt
                assert {path.name: path.read_bytes() for path in target.iterdir()} == original_files
                assert package.verify_package(target) == verified
    assert verified["report"]["dataset"]["status"] == (
        "REJECTED_QUALITY" if rejected else "READY_SYNTHETIC"
    )
    assert (verified["report"]["matrix"] is None) is rejected
    assert not verified["report"]["boundary"]["statistics_computed"]
    assert {path: path.read_bytes() for path in sources} == snapshot


def test_each_source_read_once_survives_capture_handoff_for_all_combinations(tmp_path, monkeypatch):
    original_open = Path.open
    for zipped_plan in (False, True):
        for zipped_output in (False, True):
            case = tmp_path / f"case-{zipped_plan}-{zipped_output}"
            case.mkdir()
            plan, plan_zip, inputs = _sources(case)
            expected_files = package.build_package_files(plan, inputs)
            expected = package.verify_package_files(expected_files)
            source = plan_zip if zipped_plan else plan
            sources = [inputs, plan_zip] if zipped_plan else [inputs, *plan.iterdir()]
            snapshot = {path: path.read_bytes() for path in sources}
            reads = []

            @contextmanager
            def mutate_after_read(
                path, mode="r", *rest, _snapshot=snapshot, _reads=reads, **kwargs,
            ):
                with original_open(path, mode, *rest, **kwargs) as stream:
                    yield stream
                if mode == "rb" and path in _snapshot:
                    _reads.append(path)
                    with original_open(path, "wb") as output:
                        output.write(b"changed after captured read")

            output = case / "output"
            with monkeypatch.context() as scoped:
                scoped.setattr(Path, "open", mutate_after_read)
                if zipped_output:
                    receipt = archive.export_from_plan(
                        source, inputs, output, plan_archive=zipped_plan,
                    )
                    assert receipt["verification"] == expected
                else:
                    package.export_package(source, inputs, output, plan_archive=zipped_plan)
            assert len(reads) == len(snapshot) and set(reads) == set(snapshot)
            assert reads[-1] == inputs
            if zipped_output:
                assert archive.verify_archive(output)["verification"] == expected
                with zipfile.ZipFile(output) as view:
                    assert {name: view.read(name) for name in view.namelist()} == expected_files
            else:
                assert {path.name: path.read_bytes() for path in output.iterdir()} == expected_files


def test_invalid_plans_fail_before_inputs_and_keep_original_plan_errors(
    tmp_path, monkeypatch, capsys,
):
    plan, plan_zip, inputs = _sources(tmp_path)
    files = {path.name: path.read_bytes() for path in plan.iterdir()}
    bad_zip = tmp_path / "bad.zip"
    output = tmp_path / "new.zip"

    def forbidden(*args, **kwargs):
        raise AssertionError("Invalid plan must fail before reading inputs")

    monkeypatch.setattr(synthetic_prepare, "read_input_bytes", forbidden)

    def rejected(source, zipped, code, zipped_output=True):
        assert cli.main(_args(source, inputs, output, plan_zip=zipped,
                              output_zip=zipped_output)) == 2
        captured = capsys.readouterr()
        assert captured.out == "" and captured.err == f"error: {code}\n"
        assert not output.exists()

    forged = dict(files)
    forged["plan.json"] = b"{}"
    bad_zip.write_bytes(research_plan_archive._encode(forged))
    rejected(bad_zip, True, "PLAN_PACKAGE_MISMATCH")
    rejected(bad_zip, True, "PLAN_PACKAGE_MISMATCH", zipped_output=False)
    (plan / "plan.json").write_bytes(b"{}")
    rejected(plan, False, "PLAN_PACKAGE_MISMATCH")
    bad_zip.write_bytes(plan_zip.read_bytes() + b"tail")
    rejected(bad_zip, True, "PLAN_ARCHIVE_LAYOUT_INVALID")
    bad_zip.write_bytes(b"not a ZIP")
    rejected(bad_zip, True, "PLAN_ARCHIVE_INVALID")
    with monkeypatch.context() as scoped:
        scoped.setattr(research_plan_archive, "MAX_ARCHIVE_BYTES", 1)
        rejected(plan_zip, True, "PLAN_ARCHIVE_LIMIT_EXCEEDED")


def test_invalid_inputs_targets_and_flags_reject_before_writes_or_io(
    tmp_path, monkeypatch, capsys,
):
    plan, plan_zip, inputs = _sources(tmp_path)
    raw_inputs = inputs.read_bytes()
    output = tmp_path / "new.zip"

    def rejected(args, code):
        assert cli.main(args) == 2
        captured = capsys.readouterr()
        assert captured.out == "" and captured.err == f"error: {code}\n"

    args = _args(plan_zip, inputs, output, plan_zip=True, output_zip=True)
    document = json.loads(raw_inputs)
    document["observations"][0]["value"] = "0.123"
    inputs.write_text(json.dumps(document), encoding="utf-8")
    rejected(args, "EVIDENCE_DIGEST_MISMATCH")
    inputs.write_bytes(b'{"x":1,"x":2}')
    rejected(args, "DUPLICATE_INPUT_JSON_KEY")
    inputs.write_bytes(b" " * (package.MAX_SOURCE_BYTES + 1))
    rejected(args, "INPUT_TOO_LARGE")
    inputs.write_bytes(raw_inputs)
    assert not output.exists()
    output.write_bytes(b"existing output")

    def forbidden(*args, **kwargs):
        raise AssertionError("Target or invalid flags must reject before source IO")

    with monkeypatch.context() as scoped:
        scoped.setattr(package, "build_package_files", forbidden)
        rejected(args, "OUTPUT_PATH_EXISTS")
        for target in (plan / "new.zip", plan / ".." / plan.name / "alias.zip"):
            rejected(_args(plan, inputs, target, output_zip=True), "OUTPUT_INSIDE_SOURCE_PLAN")
            assert not target.exists()
    assert output.read_bytes() == b"existing output"
    linked = tmp_path / "linked"
    linked.mkdir()
    original_lstat = Path.lstat

    class Reparse:
        st_mode = 0o40755
        st_file_attributes = 0x400

    with monkeypatch.context() as scoped:
        scoped.setattr(Path, "lstat", lambda path, **kw: (
            Reparse() if path == linked else original_lstat(path, **kw)
        ))
        rejected(_args(plan_zip, inputs, linked / "new.zip", plan_zip=True, output_zip=True),
                 "LINKED_PREPARATION_PACKAGE_PATH")
    assert not (linked / "new.zip").exists()
    with monkeypatch.context() as scoped:
        for module, name in ((package, "export_package"), (archive, "export_from_plan"),
                             (archive, "export_archive"), (archive, "verify_archive"),
                             (package, "verify_package")):
            scoped.setattr(module, name, forbidden)
        for options in (
            [*args, "--output", "conflict"],
            [*args, "--package", str(plan)],
            ["research", "prepare-package", "--plan-archive", str(plan_zip), "--json"],
            ["research", "prepare-package", "--verify", str(plan),
             "--output-archive", str(output)],
            ["research", "prepare-package", "--archive", str(plan),
             "--output-archive", str(output)],
            ["research", "prepare-package", "--verify-archive", str(plan_zip),
             "--output-archive", str(output)],
            [*args, "--execute"],
        ):
            rejected(options, "INVALID_ARGUMENTS")
    assert inputs.read_bytes() == raw_inputs


def test_partial_owned_outputs_preserved_for_zip_and_directory(tmp_path, monkeypatch, capsys):
    plan, plan_zip, inputs = _sources(tmp_path)
    snapshot = {path: path.read_bytes() for path in (inputs, plan_zip, *plan.iterdir())}
    original_open = Path.open
    for zipped in (False, True):
        output = tmp_path / f"partial-{zipped}"

        @contextmanager
        def failing_write(path, mode="r", *rest, _target=output, **kwargs):
            with original_open(path, mode, *rest, **kwargs) as stream:
                if mode == "xb" and (path == _target or path.parent == _target):
                    stream.write(b"partial owned artifact")
                    raise OSError("injected write failure")
                yield stream

        args = _args(plan_zip, inputs, output, plan_zip=True, output_zip=zipped)
        with monkeypatch.context() as scoped:
            scoped.setattr(Path, "open", failing_write)
            assert cli.main(args) == 2
        captured = capsys.readouterr()
        code = "PREPARATION_ARCHIVE_WRITE_FAILED" if zipped else "PREPARATION_PACKAGE_WRITE_FAILED"
        assert captured.out == "" and captured.err == f"error: {code}\n"
        if zipped:
            assert output.read_bytes() == b"partial owned artifact"
        else:
            assert len(list(output.iterdir())) == 1
            assert next(output.iterdir()).read_bytes() == b"partial owned artifact"
        assert cli.main(args) == 2
        captured = capsys.readouterr()
        assert captured.out == "" and captured.err == "error: OUTPUT_PATH_EXISTS\n"
    assert {path: path.read_bytes() for path in snapshot} == snapshot


def test_snapshot_writer_verifies_bounds_before_encoding_or_claiming_output(tmp_path, monkeypatch):
    plan, _, inputs = _sources(tmp_path)
    files = package.build_package_files(plan, inputs)
    forged = dict(files)
    forged["preparation.json"] = b"{}"
    output = tmp_path / "new.zip"

    def forbidden(*args, **kwargs):
        raise AssertionError("Invalid snapshots must reject before encoding")

    monkeypatch.setattr(archive, "_encode", forbidden)
    with pytest.raises(synthetic_prepare.PrepareError, match="PREPARATION_PACKAGE_MISMATCH"):
        archive.export_package_files(forged, output)
    monkeypatch.setattr(package, "MAX_TOTAL_BYTES", 1)
    with pytest.raises(synthetic_prepare.PrepareError, match="PREPARATION_PACKAGE_LIMIT_EXCEEDED"):
        archive.export_package_files(files, output)
    assert not output.exists()
