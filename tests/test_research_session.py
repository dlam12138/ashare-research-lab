"""Four integration acceptance cases for the complete offline research archive."""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

import pytest

from ashare_research import cli
from ashare_research.tools import (
    pit_fact_explorer,
    pit_metric_replay,
    research_entry,
    research_session,
    value_research_bundle,
)


@pytest.fixture(scope="module")
def archive():
    request = pit_metric_replay.validate_request(
        as_of="2024-03-31",
        compare_with="2025-03-31",
        years=[2023],
        metrics=None,
        scope="consolidated",
    )
    return request, research_session.build_session(request)


def _write_archive(root: Path, files: dict[str, bytes]) -> None:
    root.mkdir()
    for relative, payload in files.items():
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(payload)


def _rehash(root: Path, relative: str) -> None:
    """Simulate tampering that also updates the declared digest and length."""
    manifest = json.loads((root / "manifest.json").read_bytes())
    payload = (root / relative).read_bytes()
    for entry in manifest["files"]:
        if entry["path"] == relative:
            entry["sha256"] = hashlib.sha256(payload).hexdigest()
            entry["byte_count"] = len(payload)
    manifest["total_byte_count"] = sum(entry["byte_count"] for entry in manifest["files"])
    (root / "manifest.json").write_bytes(
        (json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode()
    )


def test_complete_composition_preserves_existing_bytes_and_pit(archive, tmp_path):
    request, files = archive
    assert len(files) == 24
    manifest = json.loads(files["manifest.json"])
    assert manifest["request"] == request
    assert manifest["managed_file_count"] == 23
    assert manifest["total_byte_count"] == sum(
        len(payload) for name, payload in files.items() if name != "manifest.json"
    )
    assert {entry["path"] for entry in manifest["files"]} == set(files) - {"manifest.json"}
    for entry in manifest["files"]:
        assert entry["sha256"] == hashlib.sha256(files[entry["path"]]).hexdigest()
        assert entry["byte_count"] == len(files[entry["path"]])

    value_research_bundle.export_bundle(
        value_research_bundle.load_source_bundle(), tmp_path / "value"
    )
    facts = pit_fact_explorer.build_report(
        {
            "as_of": request["as_of"],
            "compare_with": request["compare_with"],
            "concepts": [],
            "period_end": None,
            "scope": request["scope"],
        }
    )
    pit_fact_explorer.export_report(facts, tmp_path / "facts")
    metrics = pit_metric_replay.build_report(request)
    pit_metric_replay.export_report(metrics, tmp_path / "metrics")
    for component in ("value", "facts", "metrics"):
        direct_files = list((tmp_path / component).rglob("*"))
        expected_names = {
            component + "/" + path.relative_to(tmp_path / component).as_posix()
            for path in direct_files
            if path.is_file()
        }
        assert expected_names == {name for name in files if name.startswith(component + "/")}
        for relative in expected_names:
            assert files[relative] == (tmp_path / relative).read_bytes()
    for name in pit_fact_explorer.PINNED_SOURCE_SHA256:
        assert (
            files["snapshot/" + name] == (pit_fact_explorer.COMMITTED_SNAPSHOT / name).read_bytes()
        )
    retained_facts = json.loads(files["facts/report.json"])
    assert retained_facts["selection_count"] == 16
    assert all(row["available_at"] <= request["as_of"] for row in retained_facts["selections"])
    assert all(
        row["available_at"] <= request["compare_with"]
        for row in retained_facts["compare_selections"]
    )
    retained_metrics = json.loads(files["metrics/report.json"])
    assert retained_metrics["comparison"]["states"]["value_changed"] == 7
    assert retained_metrics["boundary"]["historical_metric_publication_proven"] is False
    index = files["index.md"].decode()
    for target in ("value/report.md", "facts/report.md", "metrics/report.md", "manifest.json"):
        assert "](" + target + ")" in index
    assert "2024-03-31" in index and "2025-03-31" in index
    assert str(tmp_path) not in index


def test_export_relocates_and_verifies_with_matching_selector(archive, tmp_path):
    request, files = archive
    source = tmp_path / "generated"
    manifest = research_session.export_session(request, source)
    assert manifest == json.loads(files["manifest.json"])
    assert {p.relative_to(source).as_posix() for p in source.rglob("*") if p.is_file()} == set(
        files
    )
    for name, payload in files.items():
        assert (source / name).read_bytes() == payload
    relocated = tmp_path / "relocated"
    shutil.copytree(source, relocated)
    result = research_session.verify_session(relocated)
    assert isinstance(result, dict)
    assert result["request"] == request
    assert result["managed_file_count"] == 23
    assert research_session.verify_session(source) == result


def test_rehashed_tampering_manifest_extra_files_and_links_are_rejected(archive, tmp_path):
    _, files = archive
    for relative in ("metrics/report.json", "snapshot/facts.json"):
        root = tmp_path / relative.replace("/", "-")
        _write_archive(root, files)
        target = root / relative
        target.write_bytes(target.read_bytes() + b" ")
        _rehash(root, relative)
        before = target.read_bytes()
        with pytest.raises(research_session.SessionError):
            research_session.verify_session(root)
        assert target.read_bytes() == before
    metadata = tmp_path / "metadata"
    _write_archive(metadata, files)
    manifest = json.loads((metadata / "manifest.json").read_bytes())
    manifest["historical_publication_proven"] = True
    (metadata / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(research_session.SessionError):
        research_session.verify_session(metadata)
    extra = tmp_path / "extra"
    _write_archive(extra, files)
    sentinel = extra / "foreign.txt"
    sentinel.write_bytes(b"retain foreign bytes")
    with pytest.raises(research_session.SessionError):
        research_session.verify_session(extra)
    assert sentinel.read_bytes() == b"retain foreign bytes"
    missing = tmp_path / "missing"
    _write_archive(
        missing, {name: data for name, data in files.items() if name != "facts/report.md"}
    )
    with pytest.raises(research_session.SessionError):
        research_session.verify_session(missing)

    linked = tmp_path / "linked"
    _write_archive(linked, files)
    external = tmp_path / "external"
    external.mkdir()
    try:
        (linked / "foreign-link").symlink_to(external, target_is_directory=True)
    except OSError:  # Windows may not grant symlink creation; mandatory cases above still run.
        pass
    else:
        with pytest.raises(research_session.SessionError):
            research_session.verify_session(linked)
        assert list(external.iterdir()) == []


def test_cli_validation_existing_output_and_source_failure_leave_no_mutations(
    archive,
    tmp_path,
    monkeypatch,
    capsys,
):
    request, files = archive

    def forbidden(*args, **kwargs):
        raise AssertionError("legacy initialization forbidden")

    monkeypatch.setattr(cli, "load_config", forbidden)
    monkeypatch.setattr(cli, "setup_logging", forbidden)
    monkeypatch.setattr(cli, "_create_service", forbidden)
    assert "ashare-research research session --help" in research_entry.USAGE
    assert cli.main(["research", "session", "--help"]) == 0
    assert "--verify" in capsys.readouterr().out
    retained = tmp_path / "retained"
    _write_archive(retained, files)
    assert cli.main(["research", "session", "--verify", str(retained)]) == 0
    result = capsys.readouterr()
    assert result.err == ""
    assert json.loads(result.out)["managed_file_count"] == 23
    for arguments in (
        ["--as-of", "2024/03/31", "--output", str(tmp_path / "invalid")],
        [
            "--as-of",
            "2024-03-31",
            "--compare-with",
            "2023-03-31",
            "--output",
            str(tmp_path / "invalid"),
        ],
        ["--as-of", "2024-03-31", "--year", "2019", "--output", str(tmp_path / "invalid")],
        ["--output", str(tmp_path / "invalid")],
        ["--verify", str(retained), "--as-of", "2024-03-31"],
        ["--verify", str(retained), "--scope", "consolidated"],
    ):
        assert cli.main(["research", "session", *arguments]) == 2
        captured = capsys.readouterr()
        assert captured.out == "" and captured.err.startswith("error: ")
        assert "Traceback" not in captured.err
        assert not (tmp_path / "invalid").exists()

    foreign = tmp_path / "existing"
    foreign.mkdir()
    (foreign / "keep").write_bytes(b"foreign")
    with pytest.raises(research_session.SessionError):
        research_session.export_session(request, foreign)
    assert sorted(path.name for path in foreign.iterdir()) == ["keep"]
    assert (foreign / "keep").read_bytes() == b"foreign"

    def invalid_source():
        raise value_research_bundle.BundleError("SOURCE_DIGEST_MISMATCH")

    monkeypatch.setattr(value_research_bundle, "load_source_bundle", invalid_source)
    new_root = tmp_path / "absent-parent" / "new-root"
    with pytest.raises(research_session.SessionError):
        research_session.export_session(request, new_root)
    assert not new_root.parent.exists()
