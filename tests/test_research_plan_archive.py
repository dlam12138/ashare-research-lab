"""Native plan ZIPs: original identities, single reads, hostile transport and IO."""

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

from ashare_research import cli
from ashare_research.mechanism import execution, pipeline
from ashare_research.tools import research_plan
from ashare_research.tools import research_plan_archive as archive
from ashare_research.tools import research_plan_package as package

EXAMPLE = Path(__file__).resolve().parents[1] / "docs/examples/m4_hypothesis.json"


def test_exact_portable_zip_identities_offline_and_single_read(tmp_path, monkeypatch, capsys):
    source = tmp_path / "假设.json"
    original = EXAMPLE.read_bytes()
    source.write_bytes(original)
    expected = research_plan.build_report(source)
    directory = tmp_path / "directory"
    package.export_package(source, directory)
    files = {file.name: file.read_bytes() for file in directory.iterdir()}

    def forbidden(*args, **kwargs):
        raise AssertionError("No services/network/database/statistics/extraction")

    for name in ("load_config", "setup_logging", "_create_service"):
        monkeypatch.setattr(cli, name, forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(duckdb, "connect", forbidden)
    monkeypatch.setattr(pipeline, "run_synthetic_pipeline", forbidden)
    monkeypatch.setattr(execution, "execute_bounded_analysis", forbidden)
    monkeypatch.setattr(zipfile.ZipFile, "extract", forbidden)
    monkeypatch.setattr(zipfile.ZipFile, "extractall", forbidden)
    original_open = Path.open
    reads = []

    @contextmanager
    def mutate_after_read(path, mode="r", *rest, **kwargs):
        with original_open(path, mode, *rest, **kwargs) as stream:
            yield stream
        if path == source and mode == "rb":
            reads.append(path)
            with original_open(path, "wb") as stream:
                stream.write(b"changed after read")

    output = tmp_path / "研究计划.zip"
    with monkeypatch.context() as scoped:
        scoped.setattr(Path, "open", mutate_after_read)
        assert cli.main(["research", "plan", "--hypothesis", str(source),
                         "--archive", str(output), "--json"]) == 0
    captured = capsys.readouterr()
    receipt = json.loads(captured.out)
    assert reads == [source] and captured.err == ""
    assert receipt["schema"] == archive.SCHEMA and receipt["status"] == "archived"
    assert receipt["verification"]["report"] == expected
    assert not receipt["independent_seal_verified"]
    assert not any(receipt["verification"]["report"]["boundary"].values())
    raw = output.read_bytes()
    assert receipt["archive_sha256"] == hashlib.sha256(raw).hexdigest()
    assert receipt["archive_byte_count"] == len(raw)
    with zipfile.ZipFile(io.BytesIO(raw)) as zip_view:
        assert zip_view.namelist() == sorted(package.NAMES)
        assert {name: zip_view.read(name) for name in zip_view.namelist()} == files
        assert all(entry.date_time == archive.FIXED_DATE and entry.create_system == 3
                   and stat.S_ISREG(entry.external_attr >> 16)
                   and entry.compress_type == zipfile.ZIP_STORED for entry in zip_view.infolist())
    source.write_bytes(original)
    second = tmp_path / "second.zip"
    assert cli.main(["research", "plan", "--hypothesis", str(source),
                     "--archive", str(second)]) == 0
    assert capsys.readouterr().out == "archived compile-only plan package (4 files)\n"
    assert second.read_bytes() == raw and source.read_bytes() == original
    relocated = tmp_path / "另一个位置.zip"
    output.rename(relocated)
    source = relocated
    reads.clear()
    with monkeypatch.context() as scoped:
        scoped.setattr(Path, "open", mutate_after_read)
        assert cli.main(["research", "plan", "--verify-archive", str(relocated),
                         "--json"]) == 0
    verified = json.loads(capsys.readouterr().out)
    assert reads == [relocated] and verified["archive_sha256"] == hashlib.sha256(raw).hexdigest()
    assert verified["status"] == "verified_archive"
    assert verified["verification"]["report"] == expected
    assert cli.main(["research", "plan", "--verify-archive", str(second)]) == 0
    assert capsys.readouterr().out == "verified compile-only plan archive\n"
    assert second.read_bytes() == raw
    assert {file.name: file.read_bytes() for file in directory.iterdir()} == files


def test_adversarial_members_crc_rehashed_artifacts_and_resource_bounds(
    tmp_path, monkeypatch, capsys,
):
    good = tmp_path / "good.zip"
    archive.export_archive(EXAMPLE, good)
    raw = good.read_bytes()
    with zipfile.ZipFile(io.BytesIO(raw)) as view:
        files = {name: view.read(name) for name in view.namelist()}
    candidate = tmp_path / "candidate.zip"

    def rejected(payload, code):
        candidate.write_bytes(payload)
        assert cli.main(["research", "plan", "--verify-archive", str(candidate), "--json"]) == 2
        captured = capsys.readouterr()
        assert captured.out == "" and captured.err == f"error: {code}\n"

    def custom(entries, compression=zipfile.ZIP_STORED):
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", compression=compression) as view:
            for name, payload, mode in entries:
                info = zipfile.ZipInfo(name, archive.FIXED_DATE)
                info.external_attr = mode << 16
                info.compress_type = compression
                view.writestr(info, payload)
        return buffer.getvalue()

    entries = [(name, data, stat.S_IFREG | 0o644) for name, data in sorted(files.items())]
    for name in ("../plan.md", "/plan.md", "plan\\md", "PLAN.md", "plan.md/", "extra.txt"):
        altered = [row if row[0] != "plan.md" else (name, row[1], row[2]) for row in entries]
        rejected(custom(altered), "PLAN_ARCHIVE_LAYOUT_INVALID")
    rejected(custom(entries[:-1]), "PLAN_ARCHIVE_LAYOUT_INVALID")
    rejected(custom([*entries, ("extra", b"x", stat.S_IFREG)]), "PLAN_ARCHIVE_LAYOUT_INVALID")
    with pytest.warns(UserWarning, match="Duplicate name"):
        duplicate = custom([*entries[:-1], entries[0]])
    rejected(duplicate, "PLAN_ARCHIVE_LAYOUT_INVALID")
    rejected(raw.replace(b"plan.md", b"plan.js"), "PLAN_ARCHIVE_LAYOUT_INVALID")
    rejected(raw.replace(b"plan.md", b"plan\x00md"), "PLAN_ARCHIVE_LAYOUT_INVALID")
    for mode in (stat.S_IFLNK, stat.S_IFDIR, stat.S_IFIFO):
        altered = [(name, data, mode if name == "plan.md" else old) for name, data, old in entries]
        rejected(custom(altered), "PLAN_ARCHIVE_LAYOUT_INVALID")
    rejected(custom(entries, zipfile.ZIP_DEFLATED), "PLAN_ARCHIVE_UNSUPPORTED")
    encrypted = bytearray(raw)
    central = raw.index(b"PK\x01\x02")
    struct.pack_into("<H", encrypted, central + 8, 1)
    rejected(bytes(encrypted), "PLAN_ARCHIVE_UNSUPPORTED")
    oversized = bytearray(raw)
    struct.pack_into("<L", oversized, central + 24, research_plan.MAX_INPUT_BYTES + 1)
    rejected(bytes(oversized), "PLAN_ARCHIVE_LIMIT_EXCEEDED")
    broken_crc = bytearray(raw)
    broken_crc[raw.index(b"{")] ^= 1
    rejected(bytes(broken_crc), "PLAN_ARCHIVE_INVALID")
    rejected(raw[:-1], "PLAN_ARCHIVE_LAYOUT_INVALID")
    rejected(raw + b"trailing", "PLAN_ARCHIVE_LAYOUT_INVALID")
    many_members = bytearray(raw)
    struct.pack_into("<H", many_members, len(raw) - 12, 65535)
    rejected(bytes(many_members), "PLAN_ARCHIVE_LAYOUT_INVALID")
    # The integrity inventory is forgeable; recompilation still rejects the change.
    altered_files = dict(files)
    document = json.loads(altered_files["plan.json"])
    document["boundary"]["research_ready"] = True
    altered_files["plan.json"] = json.dumps(document).encode()
    manifest = json.loads(altered_files["manifest.json"])
    for entry in manifest["files"]:
        payload = altered_files[entry["path"]]
        entry.update(byte_count=len(payload), sha256=hashlib.sha256(payload).hexdigest())
    altered_files["manifest.json"] = json.dumps(manifest).encode()
    rejected(archive._encode(altered_files), "PLAN_PACKAGE_MISMATCH")
    with monkeypatch.context() as scoped:
        scoped.setattr(archive, "MAX_ARCHIVE_BYTES", 32)
        rejected(raw, "PLAN_ARCHIVE_LIMIT_EXCEEDED")
    with monkeypatch.context() as scoped:
        scoped.setattr(archive, "MAX_TOTAL_BYTES", 1)
        rejected(raw, "PLAN_ARCHIVE_LIMIT_EXCEEDED")
    assert archive.verify_archive(good)["verification"]["report"]["boundary"][
        "execution_authorized"
    ] is False


def test_invalid_flags_non_overwrite_races_links_and_write_failure(tmp_path, monkeypatch, capsys):
    def rejected(args, code):
        assert cli.main(["research", "plan", *args]) == 2
        captured = capsys.readouterr()
        assert captured.out == "" and captured.err == f"error: {code}\n"

    output = tmp_path / "new.zip"
    base = ["--hypothesis", str(EXAMPLE)]
    for invalid in (["--verify-archive", "absent", "--output", str(output)],
                    ["--verify", "absent", "--archive", str(output)],
                    [*base, "--archive", str(output), "--output", "other"],
                    [*base, "--verify-archive", "absent"]):
        rejected(invalid, "INVALID_ARGUMENTS")
    assert not output.exists()
    output.write_bytes(b"user content")
    rejected([*base, "--archive", str(output)], "OUTPUT_PATH_EXISTS")
    assert output.read_bytes() == b"user content"
    rejected(["--verify-archive", str(tmp_path)], "PLAN_ARCHIVE_SOURCE_INVALID")
    rejected(["--verify-archive", str(tmp_path / "missing")], "PLAN_ARCHIVE_READ_FAILED")
    rejected([*base, "--archive", str(tmp_path / "missing" / "new.zip")], "OUTPUT_WRITE_FAILED")
    invalid_source = tmp_path / "invalid.json"
    invalid_source.write_bytes(b'{"x":1,"x":2}')
    not_created = tmp_path / "not-created.zip"
    rejected(["--hypothesis", str(invalid_source), "--archive", str(not_created)],
             "DUPLICATE_JSON_KEY")
    assert not not_created.exists()
    original_lstat = Path.lstat

    class Reparse:
        st_mode = stat.S_IFREG
        st_file_attributes = 0x400

    with monkeypatch.context() as scoped:
        scoped.chdir(tmp_path)
        scoped.setattr(Path, "lstat", lambda path, **kw: (
            Reparse() if path == tmp_path else original_lstat(path, **kw)
        ))
        rejected([*base, "--archive", "linked-parent.zip"], "LINKED_PACKAGE_PATH")
        rejected(["--verify-archive", "new.zip"], "LINKED_PACKAGE_PATH")
        assert not Path("linked-parent.zip").exists()
    original_open = Path.open
    raced = tmp_path / "raced.zip"

    def race_create(path, mode="r", *rest, **kwargs):
        if path == raced and mode == "xb":
            with original_open(path, "wb") as stream:
                stream.write(b"concurrent user content")
        return original_open(path, mode, *rest, **kwargs)

    with monkeypatch.context() as scoped:
        scoped.setattr(Path, "open", race_create)
        rejected([*base, "--archive", str(raced)], "OUTPUT_PATH_EXISTS")
    assert raced.read_bytes() == b"concurrent user content"
    partial = tmp_path / "partial.zip"

    @contextmanager
    def fail_write(path, mode="r", *rest, **kwargs):
        with original_open(path, mode, *rest, **kwargs) as stream:
            if path == partial and mode == "xb":
                stream.write(b"partial")
                raise OSError("private path or details must not be exposed")
            yield stream

    with monkeypatch.context() as scoped:
        scoped.setattr(Path, "open", fail_write)
        rejected([*base, "--archive", str(partial)], "OUTPUT_WRITE_FAILED")
    assert partial.read_bytes() == b"partial"
    rejected(["--verify-archive", str(partial)], "PLAN_ARCHIVE_INVALID")
    rejected([*base, "--archive", str(partial)], "OUTPUT_PATH_EXISTS")
