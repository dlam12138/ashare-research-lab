"""Actual delivery reading and original financial-comparison compatibility."""

import hashlib
import json
import zipfile

import pytest

from ashare_research import cli
from ashare_research.tools import (
    delivered_research as reader,
)
from ashare_research.tools import (
    package_archive,
    package_verification,
    research_workflow,
    session_compare,
)


@pytest.fixture(scope="module")
def delivery(tmp_path_factory):
    root = tmp_path_factory.mktemp("delivered-research")
    request = {
        "as_of": "2024-03-31", "compare_with": "2025-03-31",
        "years": [2023], "metrics": None, "scope": "consolidated",
    }
    workflow = root / "workflow"
    research_workflow.export_workflow(request, workflow)
    archive = root / "workflow.zip"
    package_archive.export_archive(workflow, archive)
    return root, workflow, archive, request


def test_reports_and_zip_metric_comparison_preserve_original_evidence(delivery, tmp_path, capsys):
    root, workflow, archive, _ = delivery
    original = {p.relative_to(root): p.read_bytes() for p in root.rglob("*") if p.is_file()}
    for section, renderer in reader.RENDERERS.items():
        expected = json.loads((workflow / section / f"{section}.json").read_bytes())
        result = reader.read_report(archive, section, archive=True)
        assert result["report"] == expected
        assert result["verification"]["verified_file_count"] == 131
        assert result["archive_receipt"]["archive_sha256"] == hashlib.sha256(
            archive.read_bytes()
        ).hexdigest()
        standalone = reader.read_report(workflow / section, section)
        assert standalone["report"] == expected
        assert standalone["archive_receipt"] is None
        assert cli.main([
            "research", "read", "--package", str(workflow), "--section", section,
        ]) == 0
        captured = capsys.readouterr()
        assert captured.out == renderer(expected) and captured.err == ""
    assert cli.main([
        "research", "read", "--archive", str(archive), "--section", "audit", "--json",
    ]) == 0
    envelope = json.loads(capsys.readouterr().out)
    assert envelope["report"]["summary"]["unique_unresolved_parent_ids"] == 28
    assert envelope["verification"]["proves_historical_publication_or_authenticity"] is False

    session = workflow / "session"
    expected = session_compare.build_comparison(session, session, right_view="compare_with")
    assert expected["states"]["value_changed"] == 7
    session_zip = tmp_path / "session.zip"
    package_archive.export_archive(session, session_zip)
    actual = session_compare.build_comparison(
        archive, session_zip, left_archive=True, right_archive=True, right_view="compare_with",
    )
    assert actual == expected
    assert cli.main([
        "research", "compare", "--left", str(session), "--right-archive", str(archive),
        "--right-view", "compare_with", "--json",
    ]) == 0
    assert json.loads(capsys.readouterr().out) == expected
    output = tmp_path / "comparison"
    session_compare.export_comparison(
        archive, session_zip, output, left_archive=True, right_archive=True,
        right_view="compare_with",
    )
    assert package_verification.verify_package(output)["package_kind"] == "compare"
    assert json.loads((output / "compare.json").read_bytes()) == expected
    assert {p.relative_to(root): p.read_bytes() for p in root.rglob("*") if p.is_file()} == original


def test_invalid_deliveries_are_rejected_and_verified_bytes_are_not_reread(
    delivery, tmp_path, monkeypatch, capsys,
):
    _, workflow, archive, request = delivery
    for args in (
        ["read", "--archive", str(archive), "--package", str(workflow), "--section", "review"],
        ["read", "--archive", str(archive), "--section", "../manifest"],
        ["compare", "--left", str(workflow), "--left-archive", str(archive),
         "--right-archive", str(archive)],
    ):
        assert cli.main(["research", *args]) == 2
        captured = capsys.readouterr()
        assert captured.out == "" and captured.err == "error: INVALID_ARGUMENTS\n"
    with pytest.raises(reader.ReadError, match="SECTION_PACKAGE_MISMATCH"):
        reader.read_report(workflow / "session", "review")
    review_zip = tmp_path / "review.zip"
    package_archive.export_archive(workflow / "review", review_zip)
    with pytest.raises(session_compare.CompareError, match="SESSION_PACKAGE_REQUIRED"):
        session_compare.build_comparison(review_zip, archive, left_archive=True, right_archive=True)
    single = tmp_path / "single"
    research_workflow.export_workflow({**request, "compare_with": None}, single)
    with pytest.raises(reader.ReadError, match="SECTION_NOT_PRESENT"):
        reader.read_report(single, "compare")

    with zipfile.ZipFile(archive) as source:
        files = {name: source.read(name) for name in source.namelist()}
    # Forge an outer report while retaining untouched nested session metrics.
    name = "review/review.md"
    files[name] += b"\nForged outer claim\n"
    manifest = json.loads(files["manifest.json"])
    for entry in manifest["files"]:
        if entry["path"] == name:
            entry["byte_count"] = len(files[name])
            entry["sha256"] = hashlib.sha256(files[name]).hexdigest()
    manifest["total_byte_count"] = sum(entry["byte_count"] for entry in manifest["files"])
    files["manifest.json"] = json.dumps(manifest, sort_keys=True, indent=2).encode() + b"\n"
    forged = tmp_path / "forged.zip"
    with zipfile.ZipFile(forged, "w") as target:
        for name, raw in files.items():
            target.writestr(name, raw)
    before = forged.read_bytes()
    for args in (
        ["read", "--archive", str(forged), "--section", "audit", "--json"],
        ["compare", "--left-archive", str(forged), "--right-archive", str(archive), "--json"],
    ):
        assert cli.main(["research", *args]) == 2
        captured = capsys.readouterr()
        assert captured.out == ""
        assert captured.err.startswith("error: VERIFY_") and "Traceback" not in captured.err
    assert forged.read_bytes() == before

    handoff = tmp_path / "handoff.zip"
    handoff.write_bytes(archive.read_bytes())
    load = package_archive.load_verified_archive
    calls = []

    def change_after_verification(path):
        result = load(path)
        calls.append(path)
        path.write_bytes(b"changed after canonical handoff")
        return result

    with monkeypatch.context() as patch:
        patch.setattr(package_archive, "load_verified_archive", change_after_verification)
        result = reader.read_report(handoff, "review", archive=True)
    assert calls == [handoff] and result["report"]["views"]
    with pytest.raises(reader.ReadError, match="ARCHIVE_INVALID"):
        reader.read_report(handoff, "review", archive=True)
