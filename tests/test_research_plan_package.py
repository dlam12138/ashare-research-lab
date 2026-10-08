"""Public portable plan delivery, original reproduction and filesystem boundaries."""

import hashlib
import json
import os
import shutil
import socket
import subprocess
from contextlib import contextmanager
from pathlib import Path

import duckdb
import pytest

from ashare_research import cli
from ashare_research.mechanism import execution, pipeline
from ashare_research.tools import research_plan
from ashare_research.tools import research_plan_package as package

EXAMPLE = Path(__file__).resolve().parents[1] / "docs/examples/m4_hypothesis.json"


def _args(source, output):
    return [
        "research", "plan-package", "--hypothesis", str(source),
        "--output", str(output), "--json",
    ]


def _bytes(root):
    return {path.name: path.read_bytes() for path in root.iterdir()}


def test_public_export_reproduce_relocate_and_original_boundaries(tmp_path, monkeypatch, capsys):
    source = tmp_path / "source.json"
    raw = EXAMPLE.read_bytes()
    source.write_bytes(raw)
    expected = research_plan.build_report(source)

    def forbidden(*args, **kwargs):
        raise AssertionError("No execution, network, service or database allowed")

    for name in ("load_config", "setup_logging", "_create_service"):
        monkeypatch.setattr(cli, name, forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(duckdb, "connect", forbidden)
    monkeypatch.setattr(pipeline, "run_synthetic_pipeline", forbidden)
    monkeypatch.setattr(execution, "execute_bounded_analysis", forbidden)
    left, right = tmp_path / "left", tmp_path / "right"
    assert cli.main(_args(source, left)) == 0
    captured = capsys.readouterr()
    assert captured.err == ""
    receipt = json.loads(captured.out)
    assert receipt["status"] == "exported_pre_execution"
    assert receipt["file_count"] == 4
    assert source.read_bytes() == raw == (left / "hypothesis.json").read_bytes()
    assert json.loads((left / "report.json").read_bytes()) == expected
    assert (left / "report.md").read_bytes() == research_plan.render_markdown(expected).encode()
    assert not any(receipt["manifest"]["boundary"].values())
    for name, entry in receipt["manifest"]["files"].items():
        data = (left / name).read_bytes()
        assert entry == {"size_bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
    assert cli.main(_args(source, right)) == 0
    capsys.readouterr()
    assert _bytes(left) == _bytes(right)
    moved = tmp_path / "moved"
    shutil.copytree(left, moved)
    source.unlink()
    before = _bytes(moved)
    assert cli.main(["research", "plan-package", "--verify", str(moved), "--json"]) == 0
    captured = capsys.readouterr()
    assert captured.err == ""
    verified = json.loads(captured.out)
    assert verified["status"] == "verified_pre_execution"
    assert verified["manifest"] == receipt["manifest"]
    assert _bytes(moved) == before
    assert cli.main(["research", "plan-package", "--verify", str(moved)]) == 0
    assert "verified_pre_execution" in capsys.readouterr().out
    assert str(tmp_path) not in json.dumps(verified)


def test_original_capture_once_and_each_package_file_read_once(tmp_path, monkeypatch):
    source, target = tmp_path / "source.json", tmp_path / "package"
    raw = EXAMPLE.read_bytes()
    source.write_bytes(raw)
    expected = research_plan.build_report(source)
    original_open = Path.open
    reads = []

    @contextmanager
    def mutate_after_read(path, mode="r", *rest, **kwargs):
        with original_open(path, mode, *rest, **kwargs) as stream:
            yield stream
        if mode == "rb":
            reads.append(path)
            if path == source:
                with original_open(path, "wb") as stream:
                    stream.write(b"changed after captured bytes")

    monkeypatch.setattr(Path, "open", mutate_after_read)
    receipt = package.export_package(source, target)
    assert reads.count(source) == 1
    assert receipt["manifest"]["source_file_sha256"] == hashlib.sha256(raw).hexdigest()
    with original_open(target / "report.json", "rb") as stream:
        assert json.load(stream) == expected
    reads.clear()
    package.verify_package(target)
    assert sorted(reads) == sorted(target / name for name in package.FILE_LIMITS)


def test_content_tampering_and_rehashed_forgery_fail_closed(tmp_path, capsys):
    source, root = EXAMPLE, tmp_path / "package"
    package.export_package(source, root)
    original = _bytes(root)
    args = ["research", "plan-package", "--verify", str(root), "--json"]
    for name in ("report.json", "report.md", "manifest.json"):
        (root / name).write_bytes(original[name] + b" ")
        assert cli.main(args) == 2
        captured = capsys.readouterr()
        assert captured.out == "" and captured.err == "error: PACKAGE_REPRODUCTION_MISMATCH\n"
        (root / name).write_bytes(original[name])
    forged = json.loads(original["report.json"])
    forged["boundary"]["execution_authorized"] = True
    forged["contract"]["condition"]["threshold"] = "-0.99"
    data = (json.dumps(forged, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode()
    manifest = json.loads(original["manifest.json"])
    manifest["files"]["report.json"] = {
        "size_bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(),
    }
    (root / "report.json").write_bytes(data)
    (root / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8",
    )
    assert json.loads((root / "manifest.json").read_bytes())["files"]["report.json"] == {
        "size_bytes": len(data),
        "sha256": hashlib.sha256((root / "report.json").read_bytes()).hexdigest(),
    }
    assert cli.main(args) == 2
    captured = capsys.readouterr()
    assert captured.out == "" and captured.err == "error: PACKAGE_REPRODUCTION_MISMATCH\n"
    for name, data in original.items():
        (root / name).write_bytes(data)
    (root / "hypothesis.json").write_bytes(original["hypothesis.json"] + b"\n")
    assert cli.main(args) == 2
    assert capsys.readouterr().err == "error: PACKAGE_REPRODUCTION_MISMATCH\n"
    (root / "hypothesis.json").write_bytes(original["hypothesis.json"])
    for mutation in ("extra", "missing", "directory"):
        if mutation == "extra":
            (root / "extra").write_bytes(b"extra")
        else:
            (root / "report.md").unlink()
            if mutation == "directory":
                (root / "report.md").mkdir()
        assert cli.main(args) == 2
        captured = capsys.readouterr()
        code = "UNSAFE_PACKAGE_FILE" if mutation == "directory" else "PACKAGE_MEMBERSHIP_MISMATCH"
        assert captured.out == "" and captured.err == f"error: {code}\n"
        if mutation == "extra":
            (root / "extra").unlink()
        else:
            if mutation == "directory":
                (root / "report.md").rmdir()
            (root / "report.md").write_bytes(original["report.md"])
    assert _bytes(root) == original


def test_invalid_input_arguments_and_existing_output_preservation(tmp_path, capsys):
    source, target = tmp_path / "input.json", tmp_path / "new"
    args = _args(source, target)
    for raw, code in (
        (b"[]", "INVALID_HYPOTHESIS_ROOT"),
        (b'{"x":1,"x":2}', "DUPLICATE_JSON_KEY"),
        (b'{"x":NaN}', "NONFINITE_JSON_NUMBER"),
        (b"{", "INVALID_HYPOTHESIS_JSON"),
        (b"\xff", "INVALID_HYPOTHESIS_JSON"),
        (b" " * (research_plan.MAX_INPUT_BYTES + 1), "HYPOTHESIS_TOO_LARGE"),
    ):
        source.write_bytes(raw)
        assert cli.main(args) == 2
        captured = capsys.readouterr()
        assert captured.out == "" and captured.err == f"error: {code}\n"
        assert not target.exists()
    document = json.loads(EXAMPLE.read_bytes())
    document["target"]["identity_policy"] = "SECURITY_LEVEL_IDENTITY_V1"
    source.write_text(json.dumps(document), encoding="utf-8")
    assert cli.main(args) == 2
    captured = capsys.readouterr()
    assert captured.out == "" and captured.err == "error: INVALID_IDENTITY_POLICY\n"
    assert not target.exists()
    for tool_args in (
        ["--hypothesis", str(EXAMPLE)],
        ["--verify", str(target), "--output", str(target)],
        ["--hypothesis", str(EXAMPLE), "--verify", str(target)],
        ["--verify", ""],
        ["--hypothesis", "", "--output", str(target)],
        ["--verify", str(target), "--execute"],
    ):
        assert cli.main(["research", "plan-package", *tool_args]) == 2
        captured = capsys.readouterr()
        assert captured.out == "" and captured.err == "error: INVALID_ARGUMENTS\n"
    target.mkdir()
    (target / "owned-by-user").write_bytes(b"keep")
    before = _bytes(target)
    assert cli.main(args) == 2
    captured = capsys.readouterr()
    assert captured.out == "" and captured.err == "error: PACKAGE_OUTPUT_EXISTS\n"
    assert _bytes(target) == before
    file = tmp_path / "file"
    file.write_bytes(b"keep")
    assert cli.main(_args(EXAMPLE, file)) == 2
    assert capsys.readouterr().err == "error: PACKAGE_OUTPUT_EXISTS\n"
    assert file.read_bytes() == b"keep"


def test_size_limits_missing_parent_and_late_write_preserve_owned_partial(tmp_path, monkeypatch):
    root = tmp_path / "package"
    limits = dict(package.FILE_LIMITS)
    limits["report.json"] = 1
    with monkeypatch.context() as context:
        context.setattr(package, "FILE_LIMITS", limits)
        with pytest.raises(research_plan.PlanError, match="PACKAGE_FILE_TOO_LARGE"):
            package.export_package(EXAMPLE, root)
        assert not root.exists()
    missing = tmp_path / "missing"
    with pytest.raises(research_plan.PlanError, match="PACKAGE_WRITE_FAILED"):
        package.export_package(EXAMPLE, missing / "package")
    assert not missing.exists()
    package.export_package(EXAMPLE, root)
    original = _bytes(root)
    with monkeypatch.context() as context:
        context.setattr(package, "FILE_LIMITS", limits)
        with pytest.raises(research_plan.PlanError, match="PACKAGE_FILE_TOO_LARGE"):
            package.verify_package(root)
    assert _bytes(root) == original
    output = tmp_path / "partial"
    original_open = Path.open

    def fail_late(path, mode="r", *args, **kwargs):
        if path == output / "report.json" and mode == "xb":
            raise OSError("simulated write failure")
        return original_open(path, mode, *args, **kwargs)

    monkeypatch.setattr(Path, "open", fail_late)
    with pytest.raises(research_plan.PlanError, match="PACKAGE_WRITE_FAILED"):
        package.export_package(EXAMPLE, output)
    assert output.is_dir()
    assert (output / "hypothesis.json").read_bytes() == EXAMPLE.read_bytes()
    assert sorted(p.name for p in output.iterdir()) == ["hypothesis.json"]
    assert _bytes(root) == original


def test_existing_collision_race_does_not_overwrite(tmp_path, monkeypatch):
    output = tmp_path / "race"
    original_mkdir = Path.mkdir

    def claim_by_other_writer(path, *args, **kwargs):
        if path == output:
            original_mkdir(path)
            (path / "other-owner").write_bytes(b"preserve")
        return original_mkdir(path, *args, **kwargs)

    monkeypatch.setattr(Path, "mkdir", claim_by_other_writer)
    with pytest.raises(research_plan.PlanError, match="PACKAGE_OUTPUT_EXISTS"):
        package.export_package(EXAMPLE, output)
    assert _bytes(output) == {"other-owner": b"preserve"}


def test_directory_link_ancestors_and_traversal_rejected(tmp_path):
    actual = tmp_path / "actual"
    actual.mkdir()
    package.export_package(EXAMPLE, actual / "package")
    before = _bytes(actual / "package")
    link = tmp_path / "link"
    if os.name == "nt":
        completed = subprocess.run(
            ["cmd", "/c", "mklink", "/J", str(link), str(actual)],
            capture_output=True, check=False,
        )
        assert completed.returncode == 0, completed.stderr
    else:
        link.symlink_to(actual, target_is_directory=True)
    for output in (link / "new", link, tmp_path / "unused" / ".." / "new"):
        with pytest.raises(research_plan.PlanError, match="UNSAFE_PACKAGE_PATH"):
            package.export_package(EXAMPLE, output)
    with pytest.raises(research_plan.PlanError, match="UNSAFE_PACKAGE_PATH"):
        package.verify_package(link / "package")
    assert not (actual / "new").exists()
    assert _bytes(actual / "package") == before
    # Junction unlink removes only the link, not its target.
    if os.name == "nt":
        link.rmdir()
    else:
        link.unlink()
    member = actual / "package" / "report.md"
    member.unlink()
    if os.name == "nt":
        completed = subprocess.run(
            ["cmd", "/c", "mklink", "/J", str(member), str(actual)],
            capture_output=True, check=False,
        )
        assert completed.returncode == 0, completed.stderr
    else:
        member.symlink_to(EXAMPLE)
    with pytest.raises(research_plan.PlanError, match="UNSAFE_PACKAGE_FILE"):
        package.verify_package(actual / "package")
    if os.name == "nt":
        member.rmdir()
    else:
        member.unlink()
    assert actual.is_dir()


def test_parent_changed_to_link_during_source_capture_cannot_redirect_export(tmp_path, monkeypatch):
    parent, outside = tmp_path / "parent", tmp_path / "outside"
    parent.mkdir()
    outside.mkdir()
    original_read = package.read_hypothesis_bytes

    def replace_parent_after_capture(source):
        data = original_read(source)
        parent.rmdir()
        if os.name == "nt":
            result = subprocess.run(
                ["cmd", "/c", "mklink", "/J", str(parent), str(outside)],
                capture_output=True, check=False,
            )
            assert result.returncode == 0, result.stderr
        else:
            parent.symlink_to(outside, target_is_directory=True)
        return data

    monkeypatch.setattr(package, "read_hypothesis_bytes", replace_parent_after_capture)
    with pytest.raises(research_plan.PlanError, match="UNSAFE_PACKAGE_PATH"):
        package.export_package(EXAMPLE, parent / "package")
    assert list(outside.iterdir()) == []
    if os.name == "nt":
        parent.rmdir()
    else:
        parent.unlink()
    assert outside.is_dir()
