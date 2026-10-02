"""Four acceptance cases for fresh verified bytes and unchanged retained outputs."""

import hashlib
import json
import shutil

import pytest

from ashare_research import cli
from ashare_research.tools import evidence_audit, research_review, research_session, session_compare

# Actual retained pre-change report hashes, independently inspected at the base.
BASELINE_REPORT_SHA256 = {
    "review": "7acdb34156d4d705dded2121316ad347cb9708a6ed1cee54fb9b2d2fc8a688c2",
    "audit": "a75de99d9b159be5e628e6d125ce9eab8d5e83b73d4ad49512bfde0db14fc9ad",
    "compare": "07d2f801d782fd18abbf31193b7aa2c3364aab655e75e57439c70293e6ae136a",
}


@pytest.fixture(scope="module")
def archive(tmp_path_factory):
    root = tmp_path_factory.mktemp("verified-reuse") / "archive"
    research_session.export_session(
        {
            "as_of": "2024-03-31",
            "compare_with": "2025-03-31",
            "years": [2023],
            "metrics": None,
            "scope": "consolidated",
        },
        root,
    )
    return root


def _count_builds(monkeypatch):
    original = research_session.build_session
    calls = []

    def counted(request):
        calls.append(request)
        return original(request)

    monkeypatch.setattr(research_session, "build_session", counted)
    return calls


def test_loader_exact_bytes_legacy_metadata_and_single_build(archive, monkeypatch):
    calls = _count_builds(monkeypatch)
    verification, files = research_session.load_verified_session(archive)
    assert len(calls) == 1
    assert verification["verified_file_count"] == len(files) == 24
    assert verification["compared_every_byte"] is True
    assert verification["canonical_manifest_compared"] is True
    assert verification["proves_historical_publication_or_authenticity"] is False
    for path in archive.rglob("*"):
        if path.is_file():
            assert files[path.relative_to(archive).as_posix()] == path.read_bytes()
    assert research_session.verify_session(archive) == verification
    assert len(calls) == 2


def test_caller_mutations_and_post_load_tampering_do_not_poison_or_cache(archive, tmp_path):
    root = tmp_path / "copy"
    shutil.copytree(archive, root)
    verification, files = research_session.load_verified_session(root)
    retained = files["metrics/report.json"]
    files["index.md"] = b"caller-owned modification"
    verification["request"]["years"].append(2099)
    verification["status"] = "caller-modified"
    fresh_metadata, fresh_files = research_session.load_verified_session(root)
    assert fresh_metadata["status"] == "verified"
    assert fresh_metadata["request"]["years"] == [2023]
    assert fresh_files["index.md"] == (root / "index.md").read_bytes()
    (root / "metrics/report.json").write_bytes(b"changed after successful load")
    assert fresh_files["metrics/report.json"] == retained
    for loader in (research_session.load_verified_session, research_session.verify_session):
        with pytest.raises(research_session.SessionError, match="VERIFY_FILE_MISMATCH"):
            loader(root)


def test_each_consumer_halves_builds_and_preserves_prior_report_bytes(archive, monkeypatch):
    calls = _count_builds(monkeypatch)
    reports = {"review": research_review.build_review(archive)}
    assert len(calls) == 1
    reports["audit"] = evidence_audit.build_audit(archive)
    assert len(calls) == 2
    reports["compare"] = session_compare.build_comparison(
        archive, archive, right_view="compare_with"
    )
    assert len(calls) == 4  # Each side freshly verified even for the same directory.
    for name, report in reports.items():
        raw = (json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode()
        assert hashlib.sha256(raw).hexdigest() == BASELINE_REPORT_SHA256[name]


def test_rehashed_tamper_layout_and_real_cli_fail_without_output(archive, tmp_path, capsys):
    root = tmp_path / "tampered"
    shutil.copytree(archive, root)
    target = root / "metrics/report.json"
    target.write_bytes(b"{}\n")
    manifest = json.loads((root / "manifest.json").read_bytes())
    for entry in manifest["files"]:
        if entry["path"] == "metrics/report.json":
            entry["sha256"] = hashlib.sha256(target.read_bytes()).hexdigest()
            entry["byte_count"] = target.stat().st_size
    manifest["total_byte_count"] = sum(entry["byte_count"] for entry in manifest["files"])
    (root / "manifest.json").write_bytes(
        (json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode()
    )
    with pytest.raises(research_session.SessionError, match="VERIFY_"):
        research_session.load_verified_session(root)
    absent = tmp_path / "absent-parent" / "output"
    commands = (
        ["review", "--session", str(root)],
        ["audit", "--session", str(root)],
        ["compare", "--left", str(archive), "--right", str(root)],
    )
    for arguments in commands:
        assert cli.main(["research", *arguments, "--output", str(absent)]) == 2
        captured = capsys.readouterr()
        assert captured.out == "" and captured.err.startswith("error: VERIFY_")
        assert not absent.parent.exists()
    extra = tmp_path / "extra"
    shutil.copytree(archive, extra)
    (extra / "foreign.txt").write_bytes(b"foreign")
    with pytest.raises(research_session.SessionError, match="VERIFY_LAYOUT_INVALID"):
        research_session.load_verified_session(extra)
    assert (extra / "foreign.txt").read_bytes() == b"foreign"
    assert cli.main(["research", "session", "--verify", str(archive)]) == 0
    assert json.loads(capsys.readouterr().out)["verified_file_count"] == 24
