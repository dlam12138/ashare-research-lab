from __future__ import annotations

import hashlib
import io
import json
import os
import shutil
import stat
import struct
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

from ashare_research import cli
from ashare_research.tools import (
    package_archive,
    package_verification,
    research_workflow,
    value_research_bundle,
)


def _bytes(root: Path) -> dict[str, bytes]:
    return {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob("*") if p.is_file()}


def _zip(files: dict[str, bytes], compression=zipfile.ZIP_STORED) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=compression) as archive:
        for name, raw in files.items():
            entry = zipfile.ZipInfo(name)
            # Preserve deliberately unsafe names even on Windows, where the
            # constructor otherwise normalizes backslashes before serialization.
            entry.filename = entry.orig_filename = name
            entry.compress_type = compression
            archive.writestr(entry, raw)
    return buffer.getvalue()


@pytest.fixture(scope="module")
def packages(tmp_path_factory):
    root = tmp_path_factory.mktemp("archive-packages")
    workflow = root / "workflow"
    research_workflow.export_workflow(
        {"as_of": "2024-03-31", "compare_with": "2025-03-31", "years": [2023]}, workflow
    )
    value_research_bundle.export_bundle(value_research_bundle.load_source_bundle(), root / "value")
    paths = {name: workflow / name for name in ("session", "review", "audit", "compare")}
    paths.update(value=root / "value", workflow=workflow)
    for kind, path in paths.items():
        package_archive.export_archive(path, root / f"{kind}.zip")
    return root, paths


def test_all_six_roundtrips_deterministic_metadata_and_fresh_verified_bytes(packages, tmp_path):
    root, paths = packages
    expected = {
        "value": 12, "session": 24, "review": 27, "audit": 27, "compare": 51, "workflow": 131,
    }
    for kind, source in paths.items():
        before = _bytes(source)
        receipt = package_archive.restore_archive(root / f"{kind}.zip", tmp_path / kind)
        assert receipt["package_kind"] == kind
        assert receipt["verified_file_count"] == expected[kind]
        assert receipt["canonical_verified_bytes_used"] is True
        assert receipt["verification"]["proves_historical_publication_or_authenticity"] is False
        assert _bytes(tmp_path / kind) == before == _bytes(source)
    second = tmp_path / "second.zip"
    package_archive.export_archive(paths["workflow"], second)
    assert second.read_bytes() == (root / "workflow.zip").read_bytes()
    with zipfile.ZipFile(second) as archive:
        assert archive.namelist() == sorted(_bytes(paths["workflow"]))
        assert archive.comment == b""
        for entry in archive.infolist():
            assert entry.date_time == package_archive.FIXED_DATE
            assert entry.compress_type == zipfile.ZIP_STORED
            assert entry.create_system == 3
            assert entry.external_attr >> 16 == stat.S_IFREG | 0o644

    meta, first = package_verification.load_verified_package(paths["value"])
    assert meta == package_verification.verify_package(paths["value"])
    first["manifest.json"] = b"mutated return map"
    assert package_verification.load_verified_package(paths["value"])[1] == _bytes(paths["value"])
    compressed = tmp_path / "compressed.zip"
    compressed.write_bytes(_zip(_bytes(paths["value"]), zipfile.ZIP_DEFLATED))
    package_archive.restore_archive(compressed, tmp_path / "compressed")
    assert _bytes(tmp_path / "compressed") == _bytes(paths["value"])


def test_unsafe_members_limits_malformed_and_crc_fail_before_destination(
    tmp_path, monkeypatch
):
    foreign = tmp_path / "foreign"
    foreign.write_bytes(b"preserve")
    manifest = b'{"schema":"unknown"}'
    names = (
        "../foreign", "/absolute", "C:/drive", "a\\b", "a//b", "./a", "a/../b",
        "CON.txt", "a/NUL", "a.", "a/", "a /b", "a\x00b", str(foreign),
    )
    raws = [
        (_zip({"manifest.json": manifest, name: b"bad"}), "ARCHIVE_LAYOUT_INVALID")
        for name in names
    ]
    raws.append((
        _zip({"manifest.json": manifest, "A/file": b"a", "a/other": b"b"}),
        "ARCHIVE_LAYOUT_INVALID",
    ))
    raws.append((
        _zip({"manifest.json": manifest, "a": b"a", "a/b": b"b"}),
        "ARCHIVE_LAYOUT_INVALID",
    ))
    for name in ("a" * (package_archive.MAX_NAME_BYTES + 1), "a/" * package_archive.MAX_PATH_PARTS):
        raws.append((_zip({"manifest.json": manifest, name: b"bad"}), "ARCHIVE_LIMIT_EXCEEDED"))
    with pytest.warns(UserWarning, match="Duplicate name"):
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as archive:
            archive.writestr("manifest.json", manifest)
            archive.writestr("manifest.json", manifest)
        raws.append((buffer.getvalue(), "ARCHIVE_LAYOUT_INVALID"))
    plain = _zip({"manifest.json": manifest})
    central = plain.index(b"PK\x01\x02")
    for offset, fmt, value, code in (
        (38, "<I", (stat.S_IFLNK | 0o777) << 16, "ARCHIVE_LAYOUT_INVALID"),
        (38, "<I", 0x10, "ARCHIVE_LAYOUT_INVALID"),
        (8, "<H", 1, "ARCHIVE_UNSUPPORTED"),
        (10, "<H", 99, "ARCHIVE_UNSUPPORTED"),
        (24, "<I", package_archive.MAX_MEMBER_BYTES + 1, "ARCHIVE_LIMIT_EXCEEDED"),
    ):
        altered = bytearray(plain)
        struct.pack_into(fmt, altered, central + offset, value)
        raws.append((bytes(altered), code))
    corrupted = bytearray(plain)
    start = 30 + struct.unpack_from("<H", corrupted, 26)[0]
    corrupted[start] ^= 1
    raws.extend((raw, "ARCHIVE_INVALID") for raw in (bytes(corrupted), plain[:-10], b"not a ZIP"))
    deflated = bytearray(_zip({"manifest.json": manifest}, zipfile.ZIP_DEFLATED))
    start = 30 + struct.unpack_from("<H", deflated, 26)[0]
    deflated[start] = 0xFF  # Reserved DEFLATE block type must map to a sanitized error.
    raws.append((bytes(deflated), "ARCHIVE_INVALID"))
    for index, (raw, code) in enumerate(raws):
        source, output = tmp_path / f"bad-{index}.zip", tmp_path / f"bad-{index}"
        source.write_bytes(raw)
        with pytest.raises(package_archive.ArchiveError, match=code):
            package_archive.restore_archive(source, output)
        assert not output.exists()
        assert foreign.read_bytes() == b"preserve"
    for attribute, limit in (("MAX_MEMBERS", 0), ("MAX_TOTAL_BYTES", 1), ("MAX_ARCHIVE_BYTES", 1)):
        with monkeypatch.context() as patch:
            patch.setattr(package_archive, attribute, limit)
            source = tmp_path / f"limit-{attribute}.zip"
            source.write_bytes(plain)
            output = tmp_path / f"limit-{attribute}"
            with pytest.raises(package_archive.ArchiveError, match="ARCHIVE_LIMIT_EXCEEDED"):
                package_archive.restore_archive(source, output)
            assert not output.exists()


def test_rehashed_tampering_source_failures_and_verified_byte_handoff(
    packages, tmp_path, monkeypatch
):
    _, paths = packages
    files = _bytes(paths["review"])
    files["review.md"] = b"forged financial claim\n"
    manifest = json.loads(files["manifest.json"])
    for entry in manifest["files"]:
        if entry["path"] == "review.md":
            entry.update(
                byte_count=len(files["review.md"]),
                sha256=hashlib.sha256(files["review.md"]).hexdigest(),
            )
    manifest["total_byte_count"] = sum(entry["byte_count"] for entry in manifest["files"])
    files["manifest.json"] = (json.dumps(manifest, sort_keys=True, indent=2) + "\n").encode()
    bad_zip = tmp_path / "forged.zip"
    bad_zip.write_bytes(_zip(files))
    # Sorted whole-package comparison rejects the rehashed root manifest first.
    with pytest.raises(package_archive.ArchiveError, match="VERIFY_MANIFEST_MISMATCH"):
        package_archive.restore_archive(bad_zip, tmp_path / "forged")
    assert not (tmp_path / "forged").exists()
    bad_source = tmp_path / "source"
    shutil.copytree(paths["value"], bad_source)
    (bad_source / "manifest.json").write_bytes(b"{}")
    with pytest.raises(package_archive.ArchiveError, match="VERIFY_MANIFEST_INVALID"):
        package_archive.export_archive(bad_source, tmp_path / "bad-source.zip")
    assert not (tmp_path / "bad-source.zip").exists()

    source = tmp_path / "handoff"
    shutil.copytree(paths["value"], source)
    before = _bytes(source)
    original = package_verification.load_verified_package
    calls = []

    def verified_then_changed(path):
        calls.append(path)
        result = original(path)
        (path / "manifest.json").write_bytes(b"changed after successful verification")
        return result

    with monkeypatch.context() as patch:
        patch.setattr(package_verification, "load_verified_package", verified_then_changed)
        package_archive.export_archive(source, tmp_path / "handoff.zip")
    assert calls == [source]
    package_archive.restore_archive(tmp_path / "handoff.zip", tmp_path / "restored")
    assert _bytes(tmp_path / "restored") == before
    with pytest.raises(package_verification.PackageError):
        original(source)


def test_real_cli_portable_delivery_output_guards_and_late_failure(
    packages, tmp_path, monkeypatch, capsys
):
    root, paths = packages

    def forbidden(*args, **kwargs):
        pytest.fail("legacy services must not initialize")

    monkeypatch.setattr(cli, "load_config", forbidden)
    monkeypatch.setattr(cli, "setup_logging", forbidden)
    assert cli.main(["research", "archive", "--help"]) == 0
    assert "--restore" in capsys.readouterr().out
    assert cli.main(["research", "archive"]) == 2
    captured = capsys.readouterr()
    assert captured.out == "" and captured.err == "error: INVALID_ARGUMENTS\n"
    existing = tmp_path / "existing.zip"
    existing.write_bytes(b"foreign")
    with monkeypatch.context() as patch:
        patch.setattr(package_verification, "load_verified_package", forbidden)
        with pytest.raises(package_archive.ArchiveError, match="OUTPUT_PATH_EXISTS"):
            package_archive.export_archive(paths["value"], existing)
    assert existing.read_bytes() == b"foreign"
    with pytest.raises(package_archive.ArchiveError, match="OUTPUT_PATH_INVALID"):
        package_archive.export_archive(paths["value"], paths["value"] / "inside.zip")
    link = tmp_path / "link"
    original_link = Path.is_symlink
    try:
        link.symlink_to(tmp_path, target_is_directory=True)
    except OSError:
        monkeypatch.setattr(Path, "is_symlink", lambda p: p == link or original_link(p))
    with pytest.raises(package_archive.ArchiveError, match="OUTPUT_PATH_INVALID"):
        package_archive.restore_archive(root / "value.zip", link / "escape")
    assert not (tmp_path / "escape").exists()
    monkeypatch.setattr(Path, "is_symlink", original_link)

    original_write = Path.write_bytes
    late = tmp_path / "late"

    def write_failure(path, raw):
        if path == late / "manifest.json":
            raise OSError("private machine detail")
        return original_write(path, raw)

    with monkeypatch.context() as patch:
        patch.setattr(Path, "write_bytes", write_failure)
        assert cli.main(
            ["research", "archive", "--restore", str(root / "value.zip"), "--output", str(late)]
        ) == 2
        captured = capsys.readouterr()
        assert captured.out == "" and captured.err == "error: OUTPUT_WRITE_FAILED\n"
    assert late.is_dir() and not (late / "manifest.json").exists()
    assert existing.read_bytes() == b"foreign"

    env = {**os.environ, "PYTHONPATH": str(Path(__file__).resolve().parents[1] / "src")}
    moved = tmp_path / "moved.zip"
    shutil.copyfile(root / "workflow.zip", moved)
    restored = tmp_path / "portable"
    command = [sys.executable, "-m", "ashare_research.cli", "research", "archive"]
    result = subprocess.run(
        command + ["--restore", str(moved), "--output", str(restored), "--json"],
        env=env, capture_output=True, check=False,
    )
    assert result.returncode == 0 and result.stderr == b""
    receipt = json.loads(result.stdout)
    assert receipt["status"] == "restored" and receipt["verified_file_count"] == 131
    assert _bytes(restored) == _bytes(paths["workflow"])
    archived = tmp_path / "portable.zip"
    result = subprocess.run(
        command + ["--package", str(restored), "--output", str(archived), "--json"],
        env=env, capture_output=True, check=False,
    )
    assert result.returncode == 0 and json.loads(result.stdout)["status"] == "archived"
    assert archived.read_bytes() == moved.read_bytes()
