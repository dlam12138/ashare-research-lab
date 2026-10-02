"""Four full-package acceptance cases with actual fixed exports and forgery."""

import hashlib
import json
import os
import shutil
from pathlib import Path

import pytest

from ashare_research import cli
from ashare_research.tools import (
    evidence_audit,
    research_review,
    research_session,
    session_compare,
    value_research_bundle,
)
from ashare_research.tools import (
    package_verification as verification,
)


def _bytes(root):
    return {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob("*") if p.is_file()}


def _write_json(path, document):
    path.write_bytes(
        (json.dumps(document, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode()
    )


@pytest.fixture(scope="module")
def packages(tmp_path_factory):
    root = tmp_path_factory.mktemp("whole-package")
    session = root / "session"
    research_session.export_session(
        {
            "as_of": "2024-03-31",
            "compare_with": "2025-03-31",
            "years": [2023],
            "metrics": None,
            "scope": "consolidated",
        },
        session,
    )
    research_review.export_review(session, root / "review")
    evidence_audit.export_audit(session, root / "audit")
    session_compare.export_comparison(session, session, root / "compare", right_view="compare_with")
    value_research_bundle.export_bundle(value_research_bundle.load_source_bundle(), root / "value")
    return {name: root / name for name in ("value", "session", "review", "audit", "compare")}


def test_all_five_real_packages_verified_without_mutation(packages):
    expected = {"value": 12, "session": 24, "review": 27, "audit": 27, "compare": 51}
    for kind, root in packages.items():
        before = _bytes(root)
        result = verification.verify_package(root)
        assert result["package_kind"] == kind
        assert result["status"] == "verified"
        assert result["verified_file_count"] == len(before) == expected[kind]
        assert result["total_byte_count"] == sum(map(len, before.values()))
        assert (
            result["package_manifest_sha256"] == hashlib.sha256(before["manifest.json"]).hexdigest()
        )
        assert result["canonical_manifest_compared"] is True
        assert result["manifest_paths_used_for_reading"] is False
        assert result["proves_historical_publication_or_authenticity"] is False
        assert _bytes(root) == before


def test_rehashed_outer_reports_and_root_metadata_forgery_fail(packages, tmp_path):
    for kind, name in (("review", "review.md"), ("audit", "audit.json"), ("compare", "compare.md")):
        root = tmp_path / kind
        shutil.copytree(packages[kind], root)
        target = root / name
        target.write_bytes(b"forged financial claim\n")
        manifest = json.loads((root / "manifest.json").read_bytes())
        for entry in manifest["files"]:
            if entry["path"] == name:
                entry.update(
                    byte_count=target.stat().st_size,
                    sha256=hashlib.sha256(target.read_bytes()).hexdigest(),
                )
        manifest["total_byte_count"] = sum(e["byte_count"] for e in manifest["files"])
        _write_json(root / "manifest.json", manifest)
        assert (
            research_session.verify_session(root / ("left" if kind == "compare" else "session"))[
                "status"
            ]
            == "verified"
        )
        with pytest.raises(verification.PackageError, match="VERIFY_"):
            verification.verify_package(root)
    root = tmp_path / "metadata"
    shutil.copytree(packages["review"], root)
    manifest = json.loads((root / "manifest.json").read_bytes())
    manifest["request"]["years"] = [2025]
    _write_json(root / "manifest.json", manifest)
    with pytest.raises(verification.PackageError, match="VERIFY_MANIFEST_MISMATCH"):
        verification.verify_package(root)
    compare = tmp_path / "view"
    shutil.copytree(packages["compare"], compare)
    manifest = json.loads((compare / "manifest.json").read_bytes())
    manifest["sides"]["right"]["selected_view"] = "as_of"
    _write_json(compare / "manifest.json", manifest)
    with pytest.raises(verification.PackageError, match="VERIFY_"):
        verification.verify_package(compare)
    manifest["sides"]["right"]["selected_view"] = "arbitrary-path"
    _write_json(compare / "manifest.json", manifest)
    with pytest.raises(verification.PackageError, match="VERIFY_MANIFEST_INVALID"):
        verification.verify_package(compare)


def test_layout_confinement_extra_missing_links_and_unknown_schema(packages, tmp_path, monkeypatch):
    root = tmp_path / "layout"
    shutil.copytree(packages["review"], root)
    foreign = tmp_path / "foreign"
    foreign.write_bytes(b"foreign preserved")
    manifest = json.loads((root / "manifest.json").read_bytes())
    manifest["files"][0]["path"] = "../foreign"
    _write_json(root / "manifest.json", manifest)
    with pytest.raises(verification.PackageError, match="VERIFY_MANIFEST_MISMATCH"):
        verification.verify_package(root)
    assert foreign.read_bytes() == b"foreign preserved"
    (root / "manifest.json").write_bytes((packages["review"] / "manifest.json").read_bytes())
    extra = root / "extra-empty-directory"
    extra.mkdir()
    with pytest.raises(verification.PackageError, match="VERIFY_LAYOUT_INVALID"):
        verification.verify_package(root)
    extra.rmdir()
    (root / "review.md").unlink()
    with pytest.raises(verification.PackageError, match="VERIFY_LAYOUT_INVALID"):
        verification.verify_package(root)
    (root / "review.md").write_bytes((packages["review"] / "review.md").read_bytes())
    link = root / "escape"
    try:
        os.symlink(foreign, link)
    except OSError:
        original = Path.is_symlink
        monkeypatch.setattr(Path, "is_symlink", lambda p: p == link or original(p))
        link.write_bytes(b"reported symlink on hosts without symlink privileges")
    with pytest.raises(verification.PackageError, match="VERIFY_LAYOUT_INVALID"):
        verification.verify_package(root)
    assert foreign.read_bytes() == b"foreign preserved"
    unknown = tmp_path / "unknown"
    unknown.mkdir()
    _write_json(unknown / "manifest.json", {"schema": "unknown"})
    with pytest.raises(verification.PackageError, match="UNSUPPORTED_PACKAGE"):
        verification.verify_package(unknown)


def test_real_cli_portable_verification_and_sanitized_failures(
    packages, tmp_path, monkeypatch, capsys
):
    def forbidden(*args, **kwargs):
        raise AssertionError("legacy initialization")

    monkeypatch.setattr(cli, "load_config", forbidden)
    monkeypatch.setattr(cli, "setup_logging", forbidden)
    assert cli.main(["research", "verify", "--help"]) == 0
    assert "--package" in capsys.readouterr().out
    moved = tmp_path / "moved"
    shutil.copytree(packages["compare"], moved)
    before = _bytes(moved)
    assert cli.main(["research", "verify", "--package", str(moved), "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["verified_file_count"] == 51
    assert _bytes(moved) == before
    assert cli.main(["research", "verify", "--package", str(packages["audit"])]) == 0
    assert "27 个文件" in capsys.readouterr().out
    (moved / "compare.json").write_bytes(b"{}")
    for arguments in (
        ["--package", str(moved)],
        ["--package", str(moved), "--bad"],
        ["--package", str(tmp_path / "absent")],
        [],
    ):
        assert cli.main(["research", "verify", *arguments]) == 2
        captured = capsys.readouterr()
        assert captured.out == "" and captured.err.startswith("error: ")
        assert str(tmp_path) not in captured.err
    assert not (tmp_path / "absent").exists()
