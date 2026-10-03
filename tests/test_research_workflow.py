from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from ashare_research.tools import package_verification, research_entry, research_workflow

REQUEST = {
    "as_of": "2024-03-31",
    "compare_with": "2025-03-31",
    "years": [2023],
    "metrics": None,
    "scope": "consolidated",
}


def _bytes(root: Path) -> dict[str, bytes]:
    return {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob("*") if p.is_file()}


@pytest.fixture(scope="module")
def packages(tmp_path_factory):
    root = tmp_path_factory.mktemp("complete-workflow")
    for name, compare in (("two", REQUEST["compare_with"]), ("one", None)):
        research_workflow.export_workflow({**REQUEST, "compare_with": compare}, root / name)
    return root


def test_composition_is_reproducible_and_preserves_independent_packages(packages):
    two = packages / "two"
    before = _bytes(two)
    assert len(before) == 131
    assert research_workflow.build_workflow(REQUEST) == before
    assert len(_bytes(packages / "one")) == 80
    assert not (packages / "one" / "compare").exists()
    assert "compare/compare.md" not in (packages / "one" / "index.md").read_text("utf-8")
    for area, count in (("session", 24), ("review", 27), ("audit", 27), ("compare", 51)):
        result = package_verification.verify_package(two / area)
        assert result["verified_file_count"] == count
        assert result["proves_historical_publication_or_authenticity"] is False
    session = _bytes(two / "session")
    for area in ("review/session", "audit/session", "compare/left", "compare/right"):
        assert _bytes(two / area) == session
    for line in (two / "index.md").read_text("utf-8").splitlines():
        if line.startswith("- ["):
            assert (two / line.split("](", 1)[1].split(")", 1)[0]).is_file()
    assert _bytes(two) == before


def test_complete_verification_rejects_rehashed_reports_metadata_and_nested_tampering(
    packages, tmp_path
):
    result = package_verification.verify_package(packages / "two")
    assert result["package_kind"] == "workflow"
    assert result["verified_file_count"] == 131
    assert result["canonical_manifest_compared"] is True
    assert result["manifest_paths_used_for_reading"] is False
    assert package_verification.verify_package(packages / "one")["verified_file_count"] == 80
    for name, changed in (("index", "index.md"), ("nested", "review/review.md")):
        root = tmp_path / name
        shutil.copytree(packages / "two", root)
        raw = b"forged conclusion\n"
        (root / changed).write_bytes(raw)
        manifest = json.loads((root / "manifest.json").read_bytes())
        for entry in manifest["files"]:
            if entry["path"] == changed:
                entry.update(byte_count=len(raw), sha256=hashlib.sha256(raw).hexdigest())
        manifest["total_byte_count"] = sum(e["byte_count"] for e in manifest["files"])
        (root / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        with pytest.raises(package_verification.PackageError, match="VERIFY_"):
            package_verification.verify_package(root)
    root = tmp_path / "metadata"
    shutil.copytree(packages / "one", root)
    manifest = json.loads((root / "manifest.json").read_bytes())
    manifest["request"]["compare_with"] = REQUEST["compare_with"]
    manifest["files"][0]["path"] = "../../foreign"
    (root / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    foreign = tmp_path / "foreign"
    foreign.write_bytes(b"preserve me")
    with pytest.raises(package_verification.PackageError, match="VERIFY_"):
        package_verification.verify_package(root)
    assert foreign.read_bytes() == b"preserve me"


def test_output_guards_prebuild_and_late_failures_preserve_caller_paths(tmp_path, monkeypatch):
    existing = tmp_path / "existing"
    existing.mkdir()
    (existing / "foreign").write_bytes(b"preserve")

    def must_not_build(request):
        pytest.fail("existing output must be rejected before building")

    with monkeypatch.context() as patch:
        patch.setattr(research_workflow, "build_workflow", must_not_build)
        with pytest.raises(research_workflow.WorkflowError, match="OUTPUT_PATH_EXISTS"):
            research_workflow.export_workflow(REQUEST, existing)
    assert (existing / "foreign").read_bytes() == b"preserve"
    invalid = tmp_path / "invalid"
    with pytest.raises(research_workflow.WorkflowError, match="INVALID_AS_OF_DATE"):
        research_workflow.export_workflow({**REQUEST, "as_of": "bad"}, invalid)
    assert not invalid.exists()

    link = tmp_path / "link"
    original_is_symlink = Path.is_symlink
    try:
        link.symlink_to(existing, target_is_directory=True)
    except OSError:
        monkeypatch.setattr(
            Path, "is_symlink", lambda p: p == link or original_is_symlink(p)
        )
    with pytest.raises(research_workflow.WorkflowError, match="OUTPUT_PATH_INVALID"):
        research_workflow.export_workflow(REQUEST, link / "new")
    assert not (existing / "new").exists()
    monkeypatch.setattr(Path, "is_symlink", original_is_symlink)

    def prebuild_failure(request):
        raise research_workflow.WorkflowError("COMPOSE_FAILED")

    monkeypatch.setattr(research_workflow, "build_workflow", prebuild_failure)
    with pytest.raises(research_workflow.WorkflowError, match="COMPOSE_FAILED"):
        research_workflow.export_workflow(REQUEST, tmp_path / "prebuild")
    assert not (tmp_path / "prebuild").exists()
    late = tmp_path / "late"
    monkeypatch.setattr(
        research_workflow, "build_workflow", lambda request: {"a.txt": b"a", "b.txt": b"b"}
    )
    original_write = Path.write_bytes

    def fail_second(path, raw):
        if path == late / "b.txt":
            raise OSError("private detail")
        return original_write(path, raw)

    monkeypatch.setattr(Path, "write_bytes", fail_second)
    with pytest.raises(research_workflow.WorkflowError, match="OUTPUT_WRITE_FAILED"):
        research_workflow.export_workflow(REQUEST, late)
    assert (late / "a.txt").read_bytes() == b"a"
    assert not (late / "b.txt").exists()
    assert (existing / "foreign").read_bytes() == b"preserve"


def test_real_cli_success_failures_and_no_legacy_initialization(tmp_path, monkeypatch, capsys):
    from ashare_research import cli

    def forbidden(*args, **kwargs):
        pytest.fail("offline workflow must not initialize legacy services")

    monkeypatch.setattr(cli, "load_config", forbidden)
    monkeypatch.setattr(cli, "setup_logging", forbidden)
    assert research_entry.main(["workflow", "--help"]) == 0
    assert "--as-of" in capsys.readouterr().out
    assert (
        cli.main(["research", "workflow", "--as-of", "bad", "--output", str(tmp_path / "bad")])
        == 2
    )
    captured = capsys.readouterr()
    assert captured.out == "" and "INVALID_AS_OF_DATE" in captured.err
    assert not (tmp_path / "bad").exists()

    env = {**os.environ, "PYTHONPATH": str(Path(__file__).resolve().parents[1] / "src")}
    output = tmp_path / "delivery"
    command = [sys.executable, "-m", "ashare_research.cli", "research"]
    created = subprocess.run(
        command + ["workflow", "--as-of", "2024-03-31", "--year", "2023", "--output", str(output)],
        capture_output=True, env=env, check=False,
    )
    assert created.returncode == 0 and b"80 files" in created.stdout and created.stderr == b""
    moved = tmp_path / "moved"
    output.rename(moved)
    verified = subprocess.run(
        command + ["verify", "--package", str(moved), "--json"],
        capture_output=True, env=env, check=False,
    )
    assert verified.returncode == 0 and verified.stderr == b""
    assert json.loads(verified.stdout)["package_kind"] == "workflow"
    before = _bytes(moved)
    failed = subprocess.run(
        command + ["workflow", "--as-of", "2024-03-31", "--output", str(moved)],
        capture_output=True, env=env, check=False,
    )
    assert failed.returncode == 2 and failed.stdout == b""
    assert failed.stderr == b"error: OUTPUT_PATH_EXISTS\n"
    assert _bytes(moved) == before
    invalid = subprocess.run(command + ["workflow"], capture_output=True, env=env, check=False)
    assert invalid.returncode == 2 and invalid.stdout == b""
    assert invalid.stderr == b"error: INVALID_ARGUMENTS\n"
