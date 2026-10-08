"""Canonical plan ZIP reproduction, bounded parsing and output preservation."""

import hashlib
import io
import json
import os
import shutil
import socket
import stat
import struct
import subprocess
import zipfile
from contextlib import contextmanager
from pathlib import Path

import duckdb
import pytest

from ashare_research import cli
from ashare_research.mechanism import execution, pipeline
from ashare_research.tools import research_plan_archive as archive
from ashare_research.tools import research_plan_package as package
from ashare_research.tools.research_plan import PlanError

EXAMPLE = Path(__file__).resolve().parents[1] / "docs/examples/m4_hypothesis.json"


@pytest.fixture
def plan_package(tmp_path):
    root = tmp_path / "package"
    package.export_package(EXAMPLE, root)
    return root


def _captured(root):
    return {name: (root / name).read_bytes() for name in package.FILE_LIMITS}


def _zip(captured, mutate=None):
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w") as jar:
        for index, (name, data) in enumerate(captured.items()):
            member = zipfile.ZipInfo(name, archive.STAMP)
            member.create_system = 3
            member.external_attr = archive.MODE
            if mutate:
                mutate(member, index)
            jar.writestr(member, data)
    return stream.getvalue()


def test_public_delivery_determinism_relocation_and_offline_boundaries(
    plan_package, tmp_path, monkeypatch, capsys,
):
    before = _captured(plan_package)
    original = package.verify_package(plan_package)

    def forbidden(*args, **kwargs):
        raise AssertionError("No database, network, service, extraction or execution")

    for name in ("load_config", "setup_logging", "_create_service"):
        monkeypatch.setattr(cli, name, forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(duckdb, "connect", forbidden)
    monkeypatch.setattr(pipeline, "run_synthetic_pipeline", forbidden)
    monkeypatch.setattr(execution, "execute_bounded_analysis", forbidden)
    monkeypatch.setattr(zipfile.ZipFile, "extractall", forbidden)
    monkeypatch.setattr(zipfile.ZipFile, "extract", forbidden)
    left, right = tmp_path / "left.zip", tmp_path / "right.zip"
    for path in (left, right):
        assert cli.main([
            "research", "plan-archive", "--package", str(plan_package),
            "--output", str(path), "--json",
        ]) == 0
        output = capsys.readouterr()
        assert output.err == ""
        receipt = json.loads(output.out)
        assert receipt["status"] == "exported_pre_execution"
        assert receipt["manifest"] == original["manifest"]
        assert receipt["file_count"] == 4
        assert receipt["archive_sha256"] == hashlib.sha256(path.read_bytes()).hexdigest()
        assert receipt["archive_size_bytes"] == path.stat().st_size
        assert not any(receipt["manifest"]["boundary"].values())
        assert str(tmp_path) not in output.out
    assert left.read_bytes() == right.read_bytes()
    assert _captured(plan_package) == before
    assert package.verify_package(plan_package) == original
    moved = tmp_path / "renamed.zip"
    shutil.copyfile(left, moved)
    shutil.rmtree(plan_package)
    files_before = set(tmp_path.iterdir())
    assert cli.main(["research", "plan-archive", "--verify", str(moved), "--json"]) == 0
    output = capsys.readouterr()
    assert output.err == ""
    verified = json.loads(output.out)
    assert verified == {**receipt, "status": "verified_pre_execution"}
    assert set(tmp_path.iterdir()) == files_before
    assert cli.main(["research", "plan-archive", "--verify", str(moved)]) == 0
    assert "verified_pre_execution" in capsys.readouterr().out


def test_single_package_capture_and_single_archive_capture(
    plan_package, tmp_path, monkeypatch,
):
    original = _captured(plan_package)
    target = tmp_path / "archive.zip"
    original_open = Path.open
    reads = []

    @contextmanager
    def mutate_after_read(path, mode="r", *args, **kwargs):
        with original_open(path, mode, *args, **kwargs) as stream:
            yield stream
        if mode == "rb":
            reads.append(path)
            if path == plan_package / "hypothesis.json" or path == target:
                with original_open(path, "wb") as stream:
                    stream.write(b"mutated after capture")

    monkeypatch.setattr(Path, "open", mutate_after_read)
    receipt = archive.export_archive(plan_package, target)
    assert all(reads.count(plan_package / name) == 1 for name in original)
    assert receipt["manifest"]["source_file_sha256"] == hashlib.sha256(
        original["hypothesis.json"],
    ).hexdigest()
    # Export readback was captured before the simulated subsequent change.
    with original_open(target, "wb") as stream:
        stream.write(_zip(original))
    reads.clear()
    verified = archive.verify_archive(target)
    assert reads == [target]
    assert verified["manifest"] == receipt["manifest"]


@pytest.mark.parametrize("field", ["report.json", "report.md", "manifest.json", "hypothesis.json"])
def test_forged_member_content_fails_reproduction(plan_package, tmp_path, capsys, field):
    captured = _captured(plan_package)
    if field == "report.json":
        report = json.loads(captured[field])
        report["boundary"]["execution_authorized"] = True
        captured[field] = (json.dumps(report, sort_keys=True, indent=2) + "\n").encode()
        manifest = json.loads(captured["manifest.json"])
        manifest["files"][field] = {
            "sha256": hashlib.sha256(captured[field]).hexdigest(),
            "size_bytes": len(captured[field]),
        }
        captured["manifest.json"] = (json.dumps(manifest, sort_keys=True, indent=2) + "\n").encode()
    else:
        captured[field] += b" "
    target = tmp_path / "forged.zip"
    target.write_bytes(_zip(captured))
    assert cli.main(["research", "plan-archive", "--verify", str(target), "--json"]) == 2
    result = capsys.readouterr()
    assert result.out == "" and result.err == "error: PACKAGE_REPRODUCTION_MISMATCH\n"


@pytest.mark.parametrize("mutation", [
    "short", "count", "central_size", "central_offset", "disk", "comment",
    "prefix", "trailer", "extra_member", "traversal", "duplicate", "nul",
    "symlink", "compression", "encrypted", "member_extra", "member_comment",
    "timestamp", "oversize", "crc", "local_name",
])
def test_malformed_archives_rejected_before_success(
    plan_package, tmp_path, monkeypatch, mutation,
):
    captured = _captured(plan_package)
    data = _zip(captured)
    if mutation == "short":
        data = b"PK"
    elif mutation in ("count", "central_size", "central_offset", "disk"):
        fields = list(struct.unpack("<4s4H2LH", data[-22:]))
        if mutation == "count":
            fields[3] = fields[4] = 65535
        elif mutation == "central_size":
            fields[5] = 65535
        elif mutation == "central_offset":
            fields[6] += 1
        else:
            fields[1] = 1
        data = data[:-22] + struct.pack("<4s4H2LH", *fields)
        # EOCD checks must reject before opening ZipFile.
        monkeypatch.setattr(zipfile, "ZipFile", lambda *a, **k: pytest.fail("unbounded parsing"))
    elif mutation == "comment":
        data = data[:-2] + b"\x01\x00x"
    elif mutation == "prefix":
        # Even an offset-adjusted prefix recognized by ZIP readers must fail canonical bytes.
        fields = list(struct.unpack("<4s4H2LH", data[-22:]))
        fields[6] += 1
        data = b"x" + data[:-22] + struct.pack("<4s4H2LH", *fields)
    elif mutation == "trailer":
        data += b"x"
    elif mutation == "extra_member":
        data = _zip({**captured, "extra": b"x"})
    elif mutation in ("traversal", "duplicate"):
        def rename(member, index):
            if index == 1:
                member.filename = "../report.json" if mutation == "traversal" else "hypothesis.json"
        with pytest.warns(UserWarning) if mutation == "duplicate" else _no_warning():
            data = _zip(captured, rename)
    elif mutation in (
        "symlink", "compression", "member_extra", "member_comment", "timestamp",
    ):
        def metadata(member, index):
            if index == 0:
                if mutation == "symlink":
                    member.external_attr = (stat.S_IFLNK | 0o777) << 16
                elif mutation == "compression":
                    member.compress_type = zipfile.ZIP_DEFLATED
                elif mutation == "member_extra":
                    member.extra = b"\x99\x00\x00\x00"
                elif mutation == "member_comment":
                    member.comment = b"x"
                else:
                    member.date_time = (2026, 10, 8, 0, 0, 0)
        data = _zip(captured, metadata)
    elif mutation == "oversize":
        limits = dict(archive.FILE_LIMITS)
        limits["hypothesis.json"] = 1
        monkeypatch.setattr(archive, "FILE_LIMITS", limits)
    else:
        mutable = bytearray(data)
        central = mutable.index(b"PK\x01\x02")
        if mutation == "encrypted":
            struct.pack_into("<H", mutable, central + 8, 1)
        elif mutation == "crc":
            mutable[30 + len("hypothesis.json")] ^= 1
        elif mutation == "local_name":
            mutable[30] = ord("X")
        else:
            mutable[central + 46 + 3] = 0
        data = bytes(mutable)
    target = tmp_path / "invalid.zip"
    target.write_bytes(data)
    before = set(tmp_path.iterdir())
    with pytest.raises(PlanError):
        archive.verify_archive(target)
    assert target.read_bytes() == data
    assert set(tmp_path.iterdir()) == before


@contextmanager
def _no_warning():
    yield


def test_limits_collision_arguments_and_missing_parent(plan_package, tmp_path, monkeypatch, capsys):
    target = tmp_path / "owned.zip"
    target.write_bytes(b"preserve")
    with pytest.raises(PlanError, match="ARCHIVE_OUTPUT_EXISTS"):
        archive.export_archive(tmp_path / "missing", target)
    assert target.read_bytes() == b"preserve"
    with pytest.raises(PlanError, match="ARCHIVE_WRITE_FAILED"):
        archive.export_archive(plan_package, tmp_path / "missing" / "out.zip")
    assert not (tmp_path / "missing").exists()
    empty = tmp_path / "empty.zip"
    with monkeypatch.context() as context:
        context.setattr(archive, "MAX_ARCHIVE_BYTES", 1)
        with pytest.raises(PlanError, match="ARCHIVE_TOO_LARGE"):
            archive.export_archive(plan_package, empty)
        with pytest.raises(PlanError, match="PACKAGE_FILE_TOO_LARGE"):
            archive.verify_archive(target)
    assert not empty.exists()
    for args in (
        [], ["--package", str(plan_package)], ["--verify", ""],
        ["--package", "", "--output", str(empty)],
        ["--verify", str(target), "--output", str(empty)],
        ["--package", str(plan_package), "--verify", str(target)],
        ["--verify", str(target), "--restore"],
    ):
        assert cli.main(["research", "plan-archive", *args]) == 2
        output = capsys.readouterr()
        assert output.out == "" and output.err == "error: INVALID_ARGUMENTS\n"
    with pytest.raises(PlanError, match="ARCHIVE_READ_FAILED"):
        archive.verify_archive(tmp_path / "missing.zip")


def test_collision_race_and_partial_write_preserved(plan_package, tmp_path, monkeypatch):
    target = tmp_path / "race.zip"
    original_open = Path.open

    def other_owner(path, mode="r", *args, **kwargs):
        if path == target and mode == "xb":
            with original_open(path, "wb") as stream:
                stream.write(b"other owner")
        return original_open(path, mode, *args, **kwargs)

    with monkeypatch.context() as context:
        context.setattr(Path, "open", other_owner)
        with pytest.raises(PlanError, match="ARCHIVE_OUTPUT_EXISTS"):
            archive.export_archive(plan_package, target)
    assert target.read_bytes() == b"other owner"
    partial = tmp_path / "partial.zip"

    @contextmanager
    def fail_after_creation(path, mode="r", *args, **kwargs):
        with original_open(path, mode, *args, **kwargs) as stream:
            if path == partial and mode == "xb":
                stream.write(b"partial")
                raise OSError("simulated late failure")
            yield stream

    monkeypatch.setattr(Path, "open", fail_after_creation)
    with pytest.raises(PlanError, match="ARCHIVE_WRITE_FAILED"):
        archive.export_archive(plan_package, partial)
    assert partial.read_bytes() == b"partial"
    assert target.read_bytes() == b"other owner"


def _link(link, actual):
    if os.name == "nt":
        result = subprocess.run(
            ["cmd", "/c", "mklink", "/J", str(link), str(actual)],
            capture_output=True, check=False,
        )
        assert result.returncode == 0, result.stderr
    else:
        link.symlink_to(actual, target_is_directory=True)


def _unlink(link):
    if os.name == "nt":
        link.rmdir()
    else:
        link.unlink()


def test_junction_traversal_and_parent_swap_guards(plan_package, tmp_path, monkeypatch):
    actual, link = tmp_path / "actual", tmp_path / "link"
    actual.mkdir()
    archive.export_archive(plan_package, actual / "ok.zip")
    _link(link, actual)
    try:
        for target in (link / "new.zip", tmp_path / "unused" / ".." / "new.zip"):
            with pytest.raises(PlanError, match="UNSAFE_PACKAGE_PATH"):
                archive.export_archive(plan_package, target)
        with pytest.raises(PlanError, match="UNSAFE_PACKAGE_PATH"):
            archive.verify_archive(link / "ok.zip")
        with pytest.raises(PlanError, match="UNSAFE_PACKAGE_PATH"):
            archive.verify_archive(link)
        with pytest.raises(PlanError, match="UNSAFE_PACKAGE_FILE"):
            archive.verify_archive(actual)
    finally:
        _unlink(link)
    parent = tmp_path / "parent"
    parent.mkdir()
    original_capture = archive.capture_verified_package

    def swap_after_capture(source):
        result = original_capture(source)
        parent.rmdir()
        _link(parent, actual)
        return result

    monkeypatch.setattr(archive, "capture_verified_package", swap_after_capture)
    try:
        with pytest.raises(PlanError, match="UNSAFE_PACKAGE_PATH"):
            archive.export_archive(plan_package, parent / "new.zip")
        assert not (actual / "new.zip").exists()
    finally:
        _unlink(parent)


def test_capture_helper_membership_types_limits_and_legacy_compatibility(plan_package):
    captured, receipt = package.capture_verified_package(plan_package)
    assert package.verify_captured_files(captured) == receipt
    assert receipt == package.verify_package(plan_package)
    with pytest.raises(PlanError, match="PACKAGE_MEMBERSHIP_MISMATCH"):
        package.verify_captured_files({**captured, "extra": b""})
    with pytest.raises(PlanError, match="UNSAFE_PACKAGE_FILE"):
        package.verify_captured_files({**captured, "report.md": "not bytes"})
    with pytest.raises(PlanError, match="PACKAGE_FILE_TOO_LARGE"):
        package.verify_captured_files({
            **captured, "hypothesis.json": b"x" * (package.FILE_LIMITS["hypothesis.json"] + 1),
        })


def test_invalid_source_and_readback_change_never_report_success(
    plan_package, tmp_path, monkeypatch, capsys,
):
    target = tmp_path / "output.zip"
    source_before = _captured(plan_package)
    (plan_package / "report.md").write_bytes(b"forged")
    args = [
        "research", "plan-archive", "--package", str(plan_package),
        "--output", str(target), "--json",
    ]
    assert cli.main(args) == 2
    output = capsys.readouterr()
    assert output.out == "" and output.err == "error: PACKAGE_REPRODUCTION_MISMATCH\n"
    assert not target.exists()
    (plan_package / "report.md").write_bytes(source_before["report.md"])
    original_read = archive.read_regular_file

    def changed_before_readback(path, limit):
        if path == target:
            path.write_bytes(b"changed after write")
        return original_read(path, limit)

    monkeypatch.setattr(archive, "read_regular_file", changed_before_readback)
    assert cli.main(args) == 2
    output = capsys.readouterr()
    assert output.out == "" and output.err == "error: ARCHIVE_REPRODUCTION_MISMATCH\n"
    assert target.read_bytes() == b"changed after write"
    assert _captured(plan_package) == source_before
