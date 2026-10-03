from __future__ import annotations

import hashlib
import io
import json
import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

from ashare_research import cli
from ashare_research.tools import (
    package_archive,
    package_byte_diff,
    package_verification,
    research_workflow,
    value_research_bundle,
)


def _bytes(root):
    return {path.relative_to(root).as_posix(): path.read_bytes()
            for path in root.rglob("*") if path.is_file()}


def _zip(files, compression=zipfile.ZIP_STORED):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=compression) as archive:
        for name, raw in files.items():
            archive.writestr(name, raw)
    return buffer.getvalue()


@pytest.fixture(scope="module")
def packages(tmp_path_factory):
    root = tmp_path_factory.mktemp("package-byte-diff")
    request = {"as_of": "2024-03-31", "compare_with": "2025-03-31", "years": [2023]}
    research_workflow.export_workflow(request, root / "workflow")
    research_workflow.export_workflow({**request, "compare_with": None}, root / "single")
    value_research_bundle.export_bundle(value_research_bundle.load_source_bundle(), root / "value")
    paths = {kind: root / "workflow" / kind for kind in ("session", "review", "audit", "compare")}
    paths.update(value=root / "value", workflow=root / "workflow")
    receipts = {kind: package_archive.export_archive(path, root / f"{kind}.zip")
                for kind, path in paths.items()}
    return root, paths, receipts


def test_six_kinds_real_byte_diffs_encoding_independence_fresh_maps_and_cli(
    packages, tmp_path, monkeypatch, capsys
):
    root, paths, receipts = packages
    before = _bytes(root)
    for kind, source in paths.items():
        result = package_byte_diff.compare_packages(
            source, root / f"{kind}.zip", right_archive=True,
        )
        assert result["schema"] == package_byte_diff.SCHEMA
        assert result["package_kind"] == kind and result["same_content"] is True
        assert result["states"] == {
            "added": 0, "removed": 0, "changed": 0,
            "unchanged": receipts[kind]["verified_file_count"],
        }
        assert [entry["path"] for entry in result["entries"]] == sorted(_bytes(source))
        assert all(entry["before"] == entry["after"] for entry in result["entries"])
        assert result["right"]["archive_sha256"] == receipts[kind]["archive_sha256"]
        assert result["left"]["verification"] == result["right"]["verification"]
    old, new = _bytes(paths["workflow"]), _bytes(root / "single")
    changed = {name for name in old.keys() & new.keys() if old[name] != new[name]}
    forward = package_byte_diff.compare_packages(paths["workflow"], root / "single")
    assert forward["states"] == {
        "added": 0, "removed": 51, "changed": len(changed), "unchanged": 80 - len(changed),
    }
    assert changed and forward["same_content"] is False
    assert {e["path"] for e in forward["entries"] if e["state"] == "removed"} == {
        "compare/" + name for name in _bytes(paths["compare"])
    }
    assert {e["path"] for e in forward["entries"] if e["state"] == "changed"} == changed
    for entry in forward["entries"]:
        raw = old[entry["path"]]
        assert entry["before"] == {
            "byte_count": len(raw), "sha256": hashlib.sha256(raw).hexdigest(),
        }
        if entry["path"] in new:
            payload = new[entry["path"]]
            assert entry["after"] == {
                "byte_count": len(payload), "sha256": hashlib.sha256(payload).hexdigest(),
            }
    reverse = package_byte_diff.compare_packages(root / "single", paths["workflow"])
    assert reverse["states"] == {**forward["states"], "added": 51, "removed": 0}
    for left, right in zip(forward["entries"], reverse["entries"], strict=True):
        assert left["path"] == right["path"]
        assert left["before"] == right["after"] and left["after"] == right["before"]

    compressed = tmp_path / "compressed.zip"
    compressed.write_bytes(_zip(_bytes(paths["value"]), zipfile.ZIP_DEFLATED))
    result = package_byte_diff.compare_packages(
        root / "value.zip", compressed, left_archive=True, right_archive=True,
    )
    assert result["same_content"] and result["left"]["archive_sha256"] != result["right"][
        "archive_sha256"
    ]
    receipt, first = package_archive.load_verified_archive(root / "value.zip")
    assert receipt == {**receipts["value"], "status": "verified"}
    first["manifest.json"] = b"changed caller map"
    assert package_archive.load_verified_archive(root / "value.zip")[1] == _bytes(paths["value"])
    assert package_archive.verify_archive(root / "value.zip") == receipt

    def forbidden(*args, **kwargs):
        pytest.fail("read-only diff must not initialize legacy services")

    monkeypatch.setattr(cli, "load_config", forbidden)
    monkeypatch.setattr(cli, "setup_logging", forbidden)
    assert cli.main(["research", "diff", "--left", str(paths["value"]),
                     "--right-archive", str(compressed)]) == 0
    captured = capsys.readouterr()
    assert captured.err == "" and "相同 12" in captured.out
    process = subprocess.run(
        [sys.executable, "-m", "ashare_research.cli", "research", "diff",
         "--left", str(paths["workflow"]), "--right", str(root / "single"), "--json"],
        env={**os.environ, "PYTHONPATH": str(Path(__file__).resolve().parents[1] / "src")},
        capture_output=True, check=False,
    )
    assert process.returncode == 0 and process.stderr == b""
    assert json.loads(process.stdout) == forward
    assert _bytes(root) == before and set(tmp_path.iterdir()) == {compressed}


def test_invalid_inputs_tampering_and_canonical_handoff_never_reread(
    packages, tmp_path, monkeypatch, capsys
):
    root, paths, _ = packages

    def forbidden(*args, **kwargs):
        pytest.fail("invalid argument combinations must reject before source reads")

    with monkeypatch.context() as patch:
        patch.setattr(package_verification, "load_verified_package", forbidden)
        patch.setattr(package_archive, "load_verified_archive", forbidden)
        for args in ([], ["--left", "x"], ["--left", "x", "--left-archive", "y", "--right", "z"],
                     ["--left", "x", "--right", "y", "--right-archive", "z"],
                     ["--left", "x", "--right", "y", "--output", "z"]):
            assert cli.main(["research", "diff", *args]) == 2
            captured = capsys.readouterr()
            assert captured.out == "" and captured.err == "error: INVALID_ARGUMENTS\n"
    assert cli.main(["research", "diff", "--left", str(paths["value"]),
                     "--right", str(paths["session"]), "--json"]) == 2
    captured = capsys.readouterr()
    assert captured.out == "" and captured.err == "error: PACKAGE_KIND_MISMATCH\n"
    foreign = tmp_path / "foreign"
    foreign.write_bytes(b"preserve")
    forged = _bytes(paths["review"])
    forged["review.md"] = b"forged financial claim\n"
    manifest = json.loads(forged["manifest.json"])
    for item in manifest["files"]:
        if item["path"] == "review.md":
            item.update(byte_count=len(forged["review.md"]),
                        sha256=hashlib.sha256(forged["review.md"]).hexdigest())
    manifest["total_byte_count"] = sum(item["byte_count"] for item in manifest["files"])
    forged["manifest.json"] = (json.dumps(manifest, sort_keys=True, indent=2) + "\n").encode()
    corrupt = bytearray((root / "value.zip").read_bytes())
    with zipfile.ZipFile(io.BytesIO(corrupt)) as archive:
        entry = next(item for item in archive.infolist() if item.file_size)
    corrupt[entry.header_offset + 30 + len(entry.filename.encode()) + len(entry.extra)] ^= 1
    bad = tmp_path / "bad.zip"
    for raw, code in (
        (b"not a ZIP", "ARCHIVE_INVALID"),
        (bytes(corrupt), "ARCHIVE_INVALID"),
        (_zip({"manifest.json": b"{}", "../foreign": b"overwrite"}), "ARCHIVE_LAYOUT_INVALID"),
        (_zip({**_bytes(paths["value"]), "manifest.json": b"{}"}), "VERIFY_MANIFEST_INVALID"),
        (_zip(forged), "VERIFY_MANIFEST_MISMATCH"),
    ):
        bad.write_bytes(raw)
        snapshot = _bytes(tmp_path)
        assert cli.main(["research", "diff", "--left", str(paths["value"]),
                         "--right-archive", str(bad), "--json"]) == 2
        captured = capsys.readouterr()
        assert captured.out == "" and captured.err == f"error: {code}\n"
        assert _bytes(tmp_path) == snapshot

    source = tmp_path / "source"
    shutil.copytree(paths["value"], source)
    original = package_verification.load_verified_package
    calls = []

    def loaded_then_changed(path):
        calls.append(path)
        verified = original(path)
        if path == source:
            (source / "manifest.json").write_bytes(b"changed after verified handoff")
        return verified

    with monkeypatch.context() as patch:
        patch.setattr(package_verification, "load_verified_package", loaded_then_changed)
        result = package_byte_diff.compare_packages(source, paths["value"])
    assert calls == [source, paths["value"]] and result["same_content"]
    assert cli.main(["research", "diff", "--left", str(source),
                     "--right", str(paths["value"]), "--json"]) == 2
    captured = capsys.readouterr()
    assert captured.out == "" and captured.err == "error: VERIFY_MANIFEST_UNREADABLE\n"
    assert foreign.read_bytes() == b"preserve"
