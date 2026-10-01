"""Verified archive review acceptance: four real integration cases."""

import hashlib
import json
import shutil

import pytest

from ashare_research import cli
from ashare_research.tools import research_review as review
from ashare_research.tools import research_session as session


def _archive(root, **overrides):
    request = {
        "as_of": "2024-03-31",
        "compare_with": "2025-03-31",
        "years": [2023],
        "metrics": None,
        "scope": "consolidated",
        **overrides,
    }
    session.export_session(request, root)
    return root


@pytest.fixture(scope="module")
def archive(tmp_path_factory):
    return _archive(tmp_path_factory.mktemp("review") / "archive")


def test_original_precision_identity_and_comparison_are_preserved(archive):
    report = review.build_review(archive)
    original = json.loads((archive / "metrics/report.json").read_bytes())
    for view, name in zip(report["views"], ("as_of", "compare_with"), strict=True):
        for projected, row in zip(view["rows"], original[name]["records"], strict=True):
            assert projected == {field: row[field] for field in review.ROW_FIELDS}
    assert report["comparison"] == original["comparison"]
    text = review.render_markdown(report)
    assert "17407700.000000000000" in text and "17433900.000000000000" in text
    assert "2024-03-31" in text and "2025-03-31" in text
    assert "混合日期" in text and "缺失不是零" in text
    assert "](session/" not in text
    assert report["boundary"]["historical_metric_publication_proven"] is False


def test_missing_history_and_empty_scope_remain_explicit(tmp_path):
    history = review.build_review(
        _archive(
            tmp_path / "history",
            as_of="2022-04-01",
            compare_with=None,
            years=[2021],
        )
    )
    missing = [
        row for row in history["views"][0]["rows"] if row["status"] == "insufficient_history"
    ]
    assert len(missing) == 3
    assert all(row["value"] is None and row["missing_fiscal_years"] == [2020] for row in missing)
    text = review.render_markdown(history)
    assert "2020" in text and "insufficient_history" in text and "未请求对比" in text
    empty = review.build_review(_archive(tmp_path / "empty", scope="parent_company"))
    for view in empty["views"]:
        assert view["fact_count"] == 0
        assert all(
            row["value"] is None and row["status"] == "missing_input" for row in view["rows"]
        )
        assert all(row["input_available_at_bound"] is None for row in view["rows"])
    assert "未知" in review.render_markdown(empty)


def test_portable_export_keeps_exact_evidence_and_verifies_after_move(archive, tmp_path):
    output = tmp_path / "export"
    manifest = review.export_review(archive, output)
    assert manifest["managed_file_count"] == 26
    assert len([p for p in output.rglob("*") if p.is_file()]) == 27
    for entry in manifest["files"]:
        raw = (output / entry["path"]).read_bytes()
        assert len(raw) == entry["byte_count"]
        assert hashlib.sha256(raw).hexdigest() == entry["sha256"]
    for path in archive.rglob("*"):
        if path.is_file():
            assert (
                output / "session" / path.relative_to(archive)
            ).read_bytes() == path.read_bytes()
    assert "](session/metrics/report.json)" in (output / "review.md").read_text(encoding="utf-8")
    moved = tmp_path / "moved"
    shutil.copytree(output, moved)
    assert session.verify_session(moved / "session")["verified_file_count"] == 24
    assert json.loads((moved / "review.json").read_bytes()) == review.build_review(archive)


def test_cli_existing_output_and_rehashed_input_tamper_fail_safely(
    archive,
    tmp_path,
    monkeypatch,
    capsys,
):
    def forbidden(*args, **kwargs):
        raise AssertionError("legacy initialization")

    monkeypatch.setattr(cli, "load_config", forbidden)
    monkeypatch.setattr(cli, "setup_logging", forbidden)
    assert cli.main(["research", "review", "--help"]) == 0
    assert "--session" in capsys.readouterr().out
    assert cli.main(["research", "review", "--session", str(archive), "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["schema"] == review.SCHEMA
    existing = tmp_path / "existing"
    existing.mkdir()
    (existing / "keep").write_bytes(b"foreign")
    with pytest.raises(review.ReviewError, match="OUTPUT_PATH_EXISTS"):
        review.export_review(archive, existing)
    assert sorted(p.name for p in existing.iterdir()) == ["keep"]
    assert (existing / "keep").read_bytes() == b"foreign"
    tampered = tmp_path / "tampered"
    shutil.copytree(archive, tampered)
    changed = tampered / "metrics/report.json"
    document = json.loads(changed.read_bytes())
    document["as_of"]["records"][0]["value"] = "99999999.000000000000"
    raw = json.dumps(document, ensure_ascii=False).encode()
    changed.write_bytes(raw)
    manifest = json.loads((tampered / "manifest.json").read_bytes())
    for entry in manifest["files"]:
        if entry["path"] == "metrics/report.json":
            entry.update(sha256=hashlib.sha256(raw).hexdigest(), byte_count=len(raw))
    manifest["total_byte_count"] = sum(e["byte_count"] for e in manifest["files"])
    (tampered / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    absent = tmp_path / "absent-parent" / "output"
    assert (
        cli.main(
            [
                "research",
                "review",
                "--session",
                str(tampered),
                "--output",
                str(absent),
            ]
        )
        == 2
    )
    captured = capsys.readouterr()
    assert captured.out == "" and captured.err.startswith("error: VERIFY_")
    assert not absent.parent.exists()
    assert cli.main(["research", "review", "--session", str(archive), "--bad"]) == 2
    assert capsys.readouterr().err == "error: INVALID_ARGUMENTS\n"
    assert cli.main(["research", "review", "--session", str(archive), "--output", ""]) == 2
    captured = capsys.readouterr()
    assert captured.out == "" and captured.err == "error: OUTPUT_PATH_EXISTS\n"
