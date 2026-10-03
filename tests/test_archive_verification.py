from __future__ import annotations

import hashlib
import io
import json
import os
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

from ashare_research import cli
from ashare_research.tools import package_archive, research_workflow, value_research_bundle


def _snapshot(root):
    return {
        path.relative_to(root).as_posix(): path.read_bytes() if path.is_file() else None
        for path in root.rglob("*")
    }


def _zip(files):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for name, payload in files.items():
            archive.writestr(name, payload)
    return buffer.getvalue()


@pytest.fixture(scope="module")
def delivered(tmp_path_factory):
    root = tmp_path_factory.mktemp("direct-zip-verification")
    workflow = root / "workflow"
    research_workflow.export_workflow(
        {"as_of": "2024-03-31", "compare_with": "2025-03-31", "years": [2023]}, workflow
    )
    value_research_bundle.export_bundle(value_research_bundle.load_source_bundle(), root / "value")
    paths = {kind: workflow / kind for kind in ("session", "review", "audit", "compare")}
    paths.update(workflow=workflow, value=root / "value")
    receipts = {
        kind: package_archive.export_archive(path, root / f"{kind}.zip")
        for kind, path in paths.items()
    }
    return root, paths, receipts


def test_six_real_kinds_receipt_compatibility_no_destination_and_process_cli(
    delivered, monkeypatch, capsys
):
    root, _, receipts = delivered
    before = _snapshot(root)
    temporary = []
    original_temp = package_archive.tempfile.TemporaryDirectory

    def track_temp(*args, **kwargs):
        runtime = original_temp(*args, **kwargs)
        temporary.append(Path(runtime.name))
        return runtime

    monkeypatch.setattr(package_archive.tempfile, "TemporaryDirectory", track_temp)
    for kind, exported in receipts.items():
        verified = package_archive.verify_archive(root / f"{kind}.zip")
        assert verified == {**exported, "status": "verified"}
        assert verified["verification"]["compared_every_byte"] is True
        assert verified["verification"]["proves_historical_publication_or_authenticity"] is False
        assert str(root) not in json.dumps(verified)
    assert sum(path.name.startswith("m2-package-archive-") for path in temporary) == 6
    assert all(not path.exists() for path in temporary)
    assert _snapshot(root) == before

    def forbidden(*args, **kwargs):
        pytest.fail("offline verification must not initialize legacy services")

    monkeypatch.setattr(cli, "load_config", forbidden)
    monkeypatch.setattr(cli, "setup_logging", forbidden)
    assert cli.main(["research", "archive", "--verify", str(root / "value.zip")]) == 0
    text = capsys.readouterr()
    assert text.err == "" and "verified: value, 12 files" in text.out
    assert "ZIP SHA256:" in text.out
    assert cli.main(["research", "archive", "--help"]) == 0
    assert "--verify ZIP" in capsys.readouterr().out
    command = [sys.executable, "-m", "ashare_research.cli", "research", "archive"]
    result = subprocess.run(
        command + ["--verify", str(root / "workflow.zip"), "--json"],
        env={**os.environ, "PYTHONPATH": str(Path(__file__).resolve().parents[1] / "src")},
        capture_output=True, check=False,
    )
    assert result.returncode == 0 and result.stderr == b""
    assert json.loads(result.stdout) == {**receipts["workflow"], "status": "verified"}
    assert _snapshot(root) == before


def test_argument_source_and_content_failures_bounded_single_snapshot(
    delivered, tmp_path, monkeypatch, capsys
):
    root, paths, receipts = delivered
    foreign = tmp_path / "foreign"
    foreign.write_bytes(b"preserve caller file")

    def forbidden(*args, **kwargs):
        pytest.fail("invalid CLI combinations must fail before reading a source")

    invalid = (
        ["--verify", str(root / "value.zip"), "--output", str(foreign)],
        ["--verify", str(root / "value.zip"), "--package", str(paths["value"])],
        ["--verify", str(root / "value.zip"), "--restore", str(root / "value.zip")],
        ["--package", str(paths["value"])], ["--restore", str(root / "value.zip")],
        ["--verify"], ["--ver", str(root / "value.zip")],
    )
    with monkeypatch.context() as patch:
        patch.setattr(Path, "open", forbidden)
        for args in invalid:
            assert cli.main(["research", "archive", *args]) == 2
            captured = capsys.readouterr()
            assert captured.out == "" and captured.err == "error: INVALID_ARGUMENTS\n"
    for source in (tmp_path / "missing.zip", tmp_path):
        with pytest.raises(package_archive.ArchiveError, match="^ARCHIVE_SOURCE_INVALID$"):
            package_archive.verify_archive(source)
    with monkeypatch.context() as patch:
        patch.setattr(Path, "is_symlink", lambda path: path == root / "value.zip")
        with pytest.raises(package_archive.ArchiveError, match="^ARCHIVE_SOURCE_INVALID$"):
            package_archive.verify_archive(root / "value.zip")

    files = {
        path.relative_to(paths["review"]).as_posix(): path.read_bytes()
        for path in paths["review"].rglob("*") if path.is_file()
    }
    files["review.md"] = b"forged financial claim\n"
    manifest = json.loads(files["manifest.json"])
    for entry in manifest["files"]:
        if entry["path"] == "review.md":
            entry.update(byte_count=len(files["review.md"]),
                         sha256=hashlib.sha256(files["review.md"]).hexdigest())
    manifest["total_byte_count"] = sum(entry["byte_count"] for entry in manifest["files"])
    files["manifest.json"] = (json.dumps(manifest, sort_keys=True, indent=2) + "\n").encode()
    corrupt = bytearray((root / "value.zip").read_bytes())
    with zipfile.ZipFile(io.BytesIO(corrupt)) as archive:
        entry = next(item for item in archive.infolist() if item.file_size)
    corrupt[entry.header_offset + 30 + len(entry.filename.encode()) + len(entry.extra)] ^= 1
    bad = tmp_path / "bad.zip"
    for raw, code in (
        (b"not a ZIP", "ARCHIVE_INVALID"),
        (bytes(corrupt), "ARCHIVE_INVALID"),
        (_zip({"manifest.json": b"{}", "../foreign": b"overwrite"}), "ARCHIVE_LAYOUT_INVALID"),
        (_zip(files), "VERIFY_MANIFEST_MISMATCH"),
    ):
        bad.write_bytes(raw)
        before = _snapshot(tmp_path)
        assert cli.main(["research", "archive", "--verify", str(bad), "--json"]) == 2
        captured = capsys.readouterr()
        assert captured.out == "" and captured.err == f"error: {code}\n"
        assert _snapshot(tmp_path) == before

    raw = (root / "value.zip").read_bytes()
    source = tmp_path / "snapshot.zip"
    source.write_bytes(raw)
    reads = []
    original_open = Path.open

    class Snapshot(io.BytesIO):
        def read(self, size=-1):
            reads.append(size)
            with original_open(source, "wb") as changed:
                changed.write(b"changed after source snapshot")
            return super().read(size)

    def source_open(path, *args, **kwargs):
        return Snapshot(raw) if path == source else original_open(path, *args, **kwargs)

    with monkeypatch.context() as patch:
        patch.setattr(Path, "open", source_open)
        verified = package_archive.verify_archive(source)
    assert reads == [package_archive.MAX_ARCHIVE_BYTES + 1]
    assert verified == {**receipts["value"], "status": "verified"}
    assert source.read_bytes() == b"changed after source snapshot"
    with monkeypatch.context() as patch:
        patch.setattr(package_archive, "MAX_ARCHIVE_BYTES", 2)
        with pytest.raises(package_archive.ArchiveError, match="^ARCHIVE_LIMIT_EXCEEDED$"):
            package_archive.verify_archive(root / "value.zip")
    with monkeypatch.context() as patch:
        def unreadable(path, *args, **kwargs):
            if path == source:
                raise OSError("private machine detail")
            return original_open(path, *args, **kwargs)

        patch.setattr(Path, "open", unreadable)
        assert cli.main(["research", "archive", "--verify", str(source), "--json"]) == 2
        captured = capsys.readouterr()
        assert captured.out == "" and captured.err == "error: ARCHIVE_SOURCE_INVALID\n"
    assert foreign.read_bytes() == b"preserve caller file"
