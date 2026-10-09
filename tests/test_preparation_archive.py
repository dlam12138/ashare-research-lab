"""Native ZIP validation shares complete preparation reproduction without extraction."""

import hashlib
import io
import json
import socket
import stat
import struct
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


def _delivery(tmp_path, *, rejected=False):
    plan, _, inputs = _sources(tmp_path)
    if rejected:
        document = json.loads(inputs.read_bytes())
        document["observations"][0]["value"] = None
        _write_invented(document, inputs)
    directory = tmp_path / "delivery"
    package.export_package(plan, inputs, directory)
    return directory


def _zip(files, *, compression=zipfile.ZIP_STORED, prefix=b"", symlink=None, duplicate=False):
    stream = io.BytesIO()
    stream.write(prefix)
    with zipfile.ZipFile(stream, "w", compression=compression) as container:
        for name, raw in sorted(files.items()):
            name = "preparation.json" if duplicate and name == "diagnostics.json" else name
            entry = zipfile.ZipInfo(name, archive.FIXED_DATE)
            entry.create_system = 3
            entry.external_attr = ((stat.S_IFLNK if name == symlink else stat.S_IFREG)
                                   | 0o644) << 16
            entry.compress_type = compression
            container.writestr(entry, raw)
    return stream.getvalue()


def test_public_deterministic_zip_exact_directory_result_and_no_extraction(
    tmp_path, monkeypatch, capsys,
):
    source = _delivery(tmp_path)
    original = package.verify_package(source)
    snapshot = {path: path.read_bytes() for path in source.iterdir()}
    output, second = tmp_path / "result.zip", tmp_path / "second.zip"

    def forbidden(*args, **kwargs):
        raise AssertionError("No services, network, database, extraction or statistics")

    for name in ("load_config", "setup_logging", "_create_service"):
        monkeypatch.setattr(cli, name, forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(duckdb, "connect", forbidden)
    monkeypatch.setattr(pipeline, "run_synthetic_pipeline", forbidden)
    monkeypatch.setattr(execution, "execute_bounded_analysis", forbidden)
    monkeypatch.setattr(zipfile.ZipFile, "extract", forbidden)
    monkeypatch.setattr(zipfile.ZipFile, "extractall", forbidden)
    args = ["research", "prepare-package", "--archive", str(source), "--output", str(output)]
    assert cli.main([*args, "--json"]) == 0
    captured = capsys.readouterr()
    receipt = json.loads(captured.out)
    assert captured.err == "" and receipt["verification"] == original
    assert receipt["schema"] == archive.SCHEMA
    assert receipt["archive_sha256"] == hashlib.sha256(output.read_bytes()).hexdigest()
    archive.export_archive(source, second)
    assert output.read_bytes() == second.read_bytes()
    with zipfile.ZipFile(output) as container:
        assert container.namelist() == sorted(package.NAMES)
        assert all(entry.date_time == archive.FIXED_DATE for entry in container.infolist())
        assert all(entry.compress_type == zipfile.ZIP_STORED for entry in container.infolist())
        assert {name: container.read(name) for name in container.namelist()} == {
            path.name: raw for path, raw in snapshot.items()
        }
    with monkeypatch.context() as scoped:
        scoped.setattr(Path, "mkdir", forbidden)
        assert cli.main(["research", "prepare-package", "--verify-archive",
                         str(output), "--json"]) == 0
    verified = json.loads(capsys.readouterr().out)
    assert verified["verification"] == original
    assert verified["status"] == "verified_preparation_archive"
    assert cli.main(["research", "prepare-package", "--verify-archive", str(output)]) == 0
    assert capsys.readouterr().out == archive.render_markdown(verified)
    assert {path: path.read_bytes() for path in snapshot} == snapshot


def test_rejection_and_once_read_snapshot_handoff(tmp_path, monkeypatch):
    source = _delivery(tmp_path, rejected=True)
    original = package.verify_package(source)
    snapshots = {path: path.read_bytes() for path in source.iterdir()}
    output = tmp_path / "captured.zip"
    original_open = Path.open
    reads = []

    @contextmanager
    def mutate_after_read(path, mode="r", *rest, **kwargs):
        with original_open(path, mode, *rest, **kwargs) as stream:
            yield stream
        if mode == "rb" and path in snapshots:
            reads.append(path)
            with original_open(path, "wb") as target:
                target.write(b"changed after loaded snapshot")

    with monkeypatch.context() as scoped:
        scoped.setattr(Path, "open", mutate_after_read)
        archived = archive.export_archive(source, output)
    assert len(reads) == 10 and set(reads) == set(snapshots)
    assert archived["verification"] == original
    assert archived["verification"]["report"]["dataset"]["status"] == "REJECTED_QUALITY"
    assert archived["verification"]["report"]["matrix"] is None
    raw = output.read_bytes()
    archive_reads = []

    @contextmanager
    def mutate_archive(path, mode="r", *rest, **kwargs):
        with original_open(path, mode, *rest, **kwargs) as stream:
            yield stream
        if path == output and mode == "rb":
            archive_reads.append(path)
            with original_open(path, "wb") as target:
                target.write(b"changed after read")

    with monkeypatch.context() as scoped:
        scoped.setattr(Path, "open", mutate_archive)
        verified = archive.verify_archive(output)
    assert archive_reads == [output] and verified["verification"] == original
    assert verified["archive_sha256"] == hashlib.sha256(raw).hexdigest()


def test_forged_payload_malformed_members_crc_and_preflight(tmp_path, monkeypatch, capsys):
    source = _delivery(tmp_path)
    files = {path.name: path.read_bytes() for path in source.iterdir()}
    candidate = tmp_path / "candidate.zip"
    args = ["research", "prepare-package", "--verify-archive", str(candidate), "--json"]

    def rejected(raw, code):
        candidate.write_bytes(raw)
        assert cli.main(args) == 2
        captured = capsys.readouterr()
        assert captured.out == "" and captured.err == f"error: {code}\n"
        assert candidate.read_bytes() == raw

    forged = dict(files)
    document = json.loads(forged["preparation.json"])
    document["boundary"]["statistics_computed"] = True
    forged["preparation.json"] = json.dumps(document).encode("utf-8")
    manifest = json.loads(forged["manifest.json"])
    entry = next(item for item in manifest["files"] if item["path"] == "preparation.json")
    entry["sha256"] = hashlib.sha256(forged["preparation.json"]).hexdigest()
    entry["byte_count"] = len(forged["preparation.json"])
    forged["manifest.json"] = json.dumps(manifest).encode("utf-8")
    rejected(archive._encode(forged), "PREPARATION_PACKAGE_MISMATCH")
    stale = dict(files)
    changed_inputs = json.loads(stale["inputs.json"])
    changed_inputs["observations"][0]["value"] = "0.123"
    stale["inputs.json"] = json.dumps(changed_inputs).encode("utf-8")
    rejected(archive._encode(stale), "EVIDENCE_DIGEST_MISMATCH")
    rejected(_zip(files, compression=zipfile.ZIP_DEFLATED), "PREPARATION_ARCHIVE_UNSUPPORTED")
    rejected(_zip(files, symlink="inputs.json"), "PREPARATION_ARCHIVE_LAYOUT_INVALID")
    with pytest.warns(UserWarning, match="Duplicate name"):
        duplicate = _zip(files, duplicate=True)
    rejected(duplicate, "PREPARATION_ARCHIVE_LAYOUT_INVALID")
    wrong = dict(files)
    wrong["../inputs.json"] = wrong.pop("inputs.json")
    rejected(_zip(wrong), "PREPARATION_ARCHIVE_LAYOUT_INVALID")
    native = archive._encode(files)
    rejected(_zip(files, prefix=b"PK\x03\x04unused-prefix"), "PREPARATION_ARCHIVE_LAYOUT_INVALID")
    rejected(native + b"tail", "PREPARATION_ARCHIVE_LAYOUT_INVALID")
    rejected(b"not a ZIP", "PREPARATION_ARCHIVE_INVALID")
    damaged = bytearray(native)
    with zipfile.ZipFile(io.BytesIO(native)) as container:
        first = container.infolist()[0]
        payload_offset = first.header_offset + 30 + len(first.filename.encode("utf-8"))
    damaged[payload_offset] ^= 1
    rejected(bytes(damaged), "PREPARATION_ARCHIVE_INVALID")
    oversized = dict(files)
    oversized["inputs.json"] = b" " * (package.MAX_SOURCE_BYTES + 1)
    rejected(archive._encode(oversized), "PREPARATION_ARCHIVE_LIMIT_EXCEEDED")
    bad_count = bytearray(native)
    struct.pack_into("<H", bad_count, len(bad_count) - 22 + 10, 0xffff)

    def forbidden_parser(*args, **kwargs):
        raise AssertionError("Malformed transport must fail before member allocation")

    with monkeypatch.context() as scoped:
        scoped.setattr(zipfile, "ZipFile", forbidden_parser)
        rejected(bytes(bad_count), "PREPARATION_ARCHIVE_LAYOUT_INVALID")
        scoped.setattr(archive, "MAX_ARCHIVE_BYTES", 1)
        rejected(native, "PREPARATION_ARCHIVE_LIMIT_EXCEEDED")


def test_invalid_flags_destinations_links_and_partial_write_preserved(
    tmp_path, monkeypatch, capsys,
):
    source = _delivery(tmp_path)
    output = tmp_path / "result.zip"
    output.write_bytes(b"existing file")
    snapshots = {path: path.read_bytes() for path in source.iterdir()}
    args = ["research", "prepare-package", "--archive", str(source), "--output", str(output)]

    def rejected(options, code):
        assert cli.main(options) == 2
        captured = capsys.readouterr()
        assert captured.out == "" and captured.err == f"error: {code}\n"

    rejected(args, "OUTPUT_PATH_EXISTS")
    assert output.read_bytes() == b"existing file"
    for nested in (source / "new.zip", source / ".." / source.name / "nested.zip"):
        rejected([*args[:-1], str(nested)], "OUTPUT_INSIDE_SOURCE_PREPARATION")
        assert not nested.exists()
    with monkeypatch.context() as scoped:
        scoped.setattr(archive, "export_archive", lambda *a: (
            (_ for _ in ()).throw(AssertionError("Invalid flags reject before IO"))
        ))
        scoped.setattr(archive, "verify_archive", lambda *a: (
            (_ for _ in ()).throw(AssertionError("Invalid flags reject before IO"))
        ))
        for invalid in (
            ["research", "prepare-package", "--archive", str(source)],
            [*args, "--inputs", "unsupported.json"], [*args, "--verify", str(source)],
            ["research", "prepare-package", "--verify-archive", str(output), "--output", "new"],
            ["research", "prepare-package", "--verify-archive", str(output), "--execute"],
        ):
            rejected(invalid, "INVALID_ARGUMENTS")
    original_lstat = Path.lstat
    linked = tmp_path / "linked"
    linked.mkdir()

    class Reparse:
        st_mode = 0o40755
        st_file_attributes = 0x400

    with monkeypatch.context() as scoped:
        scoped.setattr(Path, "lstat", lambda path, **kw: (
            Reparse() if path == linked else original_lstat(path, **kw)
        ))
        rejected([*args[:-1], str(linked / "new.zip")], "LINKED_PREPARATION_PACKAGE_PATH")
    assert not (linked / "new.zip").exists()
    partial = tmp_path / "partial.zip"
    original_open = Path.open

    @contextmanager
    def failing_write(path, mode="r", *rest, **kwargs):
        with original_open(path, mode, *rest, **kwargs) as stream:
            if path == partial and mode == "xb":
                stream.write(b"partial owned ZIP")
                raise OSError("injected failure")
            yield stream

    with monkeypatch.context() as scoped:
        scoped.setattr(Path, "open", failing_write)
        rejected([*args[:-1], str(partial)], "PREPARATION_ARCHIVE_WRITE_FAILED")
    assert partial.read_bytes() == b"partial owned ZIP"
    rejected([*args[:-1], str(partial)], "OUTPUT_PATH_EXISTS")
    assert {path: path.read_bytes() for path in snapshots} == snapshots
