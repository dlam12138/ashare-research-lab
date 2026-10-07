"""Portable plans: public roundtrip and corruption/non-overwrite boundaries."""

import hashlib
import json
import shutil
import socket
from contextlib import contextmanager
from pathlib import Path

import duckdb

from ashare_research import cli
from ashare_research.mechanism import execution, pipeline
from ashare_research.tools import research_plan, research_plan_package

EXAMPLE = Path(__file__).resolve().parents[1] / "docs/examples/m4_hypothesis.json"


def test_portable_exact_original_bytes_once_and_offline(tmp_path, monkeypatch, capsys):
    source = tmp_path / "假设.json"
    raw = EXAMPLE.read_bytes()
    source.write_bytes(raw)
    expected = research_plan.build_report(source)

    def forbidden(*args, **kwargs):
        raise AssertionError("No services, network, database, statistics or execution")

    for name in ("load_config", "setup_logging", "_create_service"):
        monkeypatch.setattr(cli, name, forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(duckdb, "connect", forbidden)
    monkeypatch.setattr(pipeline, "run_synthetic_pipeline", forbidden)
    monkeypatch.setattr(execution, "execute_bounded_analysis", forbidden)
    original_open = Path.open
    calls = []

    @contextmanager
    def mutate_after_read(path, mode="r", *rest, **kwargs):
        with original_open(path, mode, *rest, **kwargs) as stream:
            yield stream
        if path == source and mode == "rb":
            calls.append(path)
            with original_open(path, "wb") as stream:
                stream.write(b"changed after original bytes were loaded")

    output = tmp_path / "计划包"
    with monkeypatch.context() as scoped:
        scoped.setattr(Path, "open", mutate_after_read)
        assert cli.main(["research", "plan", "--hypothesis", str(source),
                         "--output", str(output), "--json"]) == 0
    assert calls == [source]
    captured = capsys.readouterr()
    manifest = json.loads(captured.out)
    assert captured.err == "" and manifest["schema"] == research_plan_package.SCHEMA
    assert {file.name for file in output.iterdir()} == research_plan_package.NAMES
    assert (output / "hypothesis.json").read_bytes() == raw
    assert json.loads((output / "plan.json").read_bytes()) == expected
    assert (output / "plan.md").read_bytes() == research_plan.render_markdown(expected).encode()
    assert json.loads((output / "manifest.json").read_bytes()) == manifest
    assert not any(manifest["boundary"].values())
    assert manifest["independent_seal_verified"] is False
    assert manifest["integrity_inventory_only"] is True
    for entry in manifest["files"]:
        data = (output / entry["path"]).read_bytes()
        assert entry["sha256"] == hashlib.sha256(data).hexdigest()
        assert entry["byte_count"] == len(data)
    before = {file.name: file.read_bytes() for file in output.iterdir()}
    moved = tmp_path / "另一个位置"
    output.rename(moved)
    assert cli.main(["research", "plan", "--verify", str(moved), "--json"]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["report"] == expected
    assert result["status"] == "verified_against_current_compilers"
    assert result["independent_seal_verified"] is False
    assert {file.name: file.read_bytes() for file in moved.iterdir()} == before
    source.write_bytes(raw)
    second = tmp_path / "second"
    assert cli.main(["research", "plan", "--hypothesis", str(source),
                     "--output", str(second)]) == 0
    assert capsys.readouterr().out == "exported compile-only plan package (4 files)\n"
    assert {file.name: file.read_bytes() for file in second.iterdir()} == before
    assert cli.main(["research", "plan", "--verify", str(second)]) == 0
    assert capsys.readouterr().out == "verified compile-only plan package\n"


def test_corruption_rehashed_inventory_and_package_structure(tmp_path, monkeypatch, capsys):
    good = tmp_path / "good"
    research_plan_package.export_package(EXAMPLE, good)

    def rejected(directory, code):
        assert cli.main(["research", "plan", "--verify", str(directory), "--json"]) == 2
        captured = capsys.readouterr()
        assert captured.out == "" and captured.err == f"error: {code}\n"

    for index, name in enumerate(sorted(research_plan_package.NAMES)):
        altered = tmp_path / f"corrupted-{index}"
        shutil.copytree(good, altered)
        file = altered / name
        if name == "hypothesis.json":
            document = json.loads(file.read_bytes())
            document["condition"]["threshold"] = "-0.02"
            file.write_text(json.dumps(document), encoding="utf-8")
        elif name == "plan.json":
            document = json.loads(file.read_bytes())
            document["boundary"]["execution_authorized"] = True
            file.write_text(json.dumps(document), encoding="utf-8")
        else:
            file.write_bytes(file.read_bytes() + b" ")
        if name != "manifest.json":
            inventory = json.loads((altered / "manifest.json").read_bytes())
            for entry in inventory["files"]:
                data = (altered / entry["path"]).read_bytes()
                entry["sha256"] = hashlib.sha256(data).hexdigest()
                entry["byte_count"] = len(data)
            (altered / "manifest.json").write_text(json.dumps(inventory), encoding="utf-8")
        rejected(altered, "PLAN_PACKAGE_MISMATCH")
    for kind in ("extra", "missing", "nested"):
        altered = tmp_path / kind
        shutil.copytree(good, altered)
        if kind == "extra":
            (altered / "unmanaged.txt").write_text("extra")
        else:
            (altered / "plan.json").unlink()
            if kind == "nested":
                (altered / "plan.json").mkdir()
        rejected(altered, "INVALID_PLAN_PACKAGE_FILES")
    rejected(tmp_path / "absent", "INVALID_PLAN_PACKAGE")
    altered = tmp_path / "oversized"
    shutil.copytree(good, altered)
    (altered / "hypothesis.json").write_bytes(b" " * (research_plan.MAX_INPUT_BYTES + 1))
    rejected(altered, "PLAN_ARTIFACT_TOO_LARGE")
    with monkeypatch.context() as scoped:
        scoped.setattr(research_plan_package, "MAX_ARTIFACT_BYTES", 16)
        rejected(good, "PLAN_ARTIFACT_TOO_LARGE")
    # Junctions can be created on Windows without symlink privileges. Exercise
    # the same lstat reparse-point rejection through a portable injected attribute.
    original_lstat = Path.lstat

    class Reparse:
        st_mode = 0o100644
        st_file_attributes = 0x400

    for linked in (good, good / "plan.json", good.parent):
        with monkeypatch.context() as scoped:
            scoped.setattr(Path, "lstat", lambda path, linked=linked, **kw: (
                Reparse() if path == linked else original_lstat(path, **kw)
            ))
            rejected(good, "LINKED_PACKAGE_PATH")
    assert research_plan_package.verify_package(good)["report"]["boundary"][
        "research_ready"
    ] is False


def test_output_preservation_errors_flags_and_no_success_on_write_failure(
    tmp_path, monkeypatch, capsys,
):
    def run(args, code):
        assert cli.main(["research", "plan", *args]) == 2
        captured = capsys.readouterr()
        assert captured.out == "" and captured.err == f"error: {code}\n"

    existing = tmp_path / "existing"
    existing.mkdir()
    sentinel = existing / "mine.txt"
    sentinel.write_bytes(b"user content")
    args = ["--hypothesis", str(EXAMPLE), "--output", str(existing)]
    run(args, "OUTPUT_PATH_EXISTS")
    run(["--hypothesis", str(EXAMPLE), "--output", str(sentinel)], "OUTPUT_PATH_EXISTS")
    assert sentinel.read_bytes() == b"user content"
    for invalid in ([], ["--verify", str(existing), "--hypothesis", str(EXAMPLE)],
                    ["--verify", str(existing), "--output", str(tmp_path / "invalid")],
                    ["--hypothesis", str(EXAMPLE), "--execute"]):
        run(invalid, "INVALID_ARGUMENTS")
    assert not (tmp_path / "invalid").exists()
    source = tmp_path / "invalid.json"
    source.write_bytes(b'{"x":1,"x":2}')
    new = tmp_path / "not-created"
    run(["--hypothesis", str(source), "--output", str(new)], "DUPLICATE_JSON_KEY")
    assert not new.exists()
    run(["--hypothesis", str(EXAMPLE), "--output", str(tmp_path / "absent" / "new")],
        "OUTPUT_WRITE_FAILED")
    original_open = Path.open
    partial = tmp_path / "partial"

    def fail_write(path, mode="r", *rest, **kwargs):
        if path == partial / "plan.json" and mode == "xb":
            raise OSError("private path and details must not appear")
        return original_open(path, mode, *rest, **kwargs)

    with monkeypatch.context() as scoped:
        scoped.setattr(Path, "open", fail_write)
        run(["--hypothesis", str(EXAMPLE), "--output", str(partial)], "OUTPUT_WRITE_FAILED")
    assert partial.exists()
    assert (partial / "hypothesis.json").read_bytes() == EXAMPLE.read_bytes()
    run(["--verify", str(partial)], "INVALID_PLAN_PACKAGE_FILES")
    run(["--hypothesis", str(EXAMPLE), "--output", str(partial)], "OUTPUT_PATH_EXISTS")
    assert sentinel.read_bytes() == b"user content"
