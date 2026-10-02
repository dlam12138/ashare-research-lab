"""Four real acceptance cases for evidence omissions and metric dependencies."""

import hashlib
import json
import shutil

import pytest

from ashare_research import cli
from ashare_research.tools import evidence_audit as audit
from ashare_research.tools import research_session as session


def _archive(root, **overrides):
    session.export_session(
        {
            "as_of": "2024-03-31",
            "compare_with": "2025-03-31",
            "years": [2023],
            "metrics": None,
            "scope": "consolidated",
            **overrides,
        },
        root,
    )
    return root


@pytest.fixture(scope="module")
def archive(tmp_path_factory):
    return _archive(tmp_path_factory.mktemp("audit") / "archive")


def test_original_traces_values_dedup_and_every_impacted_metric(archive):
    report = audit.build_audit(archive)
    original = json.loads((archive / "metrics/report.json").read_bytes())
    expected = set()
    for name in ("as_of", "compare_with"):
        view = original[name]
        for row in view["records"]:
            for binding in row["inputs"]:
                expected.add(
                    (
                        view["date"],
                        binding["fact_id"],
                        row["metric_id"],
                        row["fiscal_year"],
                        binding["role"],
                    )
                )
                matching = [
                    entry
                    for entry in report["source_facts"]
                    if entry["date"] == view["date"]
                    and entry["fact"]["fact_id"] == binding["fact_id"]
                ]
                assert len(matching) == 1
                assert matching[0]["fact"] == {k: v for k, v in binding.items() if k != "role"}
    observed = {
        (entry["date"], entry["fact"]["fact_id"], use["metric_id"], use["fiscal_year"], use["role"])
        for entry in report["source_facts"]
        for use in entry["uses"]
    }
    assert expected == observed
    assert report["missing_inputs"] == []
    assert report["summary"]["dated_fact_rows"] == 18
    assert report["summary"]["unique_fact_ids"] == 14
    assert report["summary"]["unique_unresolved_parent_ids"] == 28
    assert all(len(entry["gaps"]) == 2 for entry in report["source_facts"])
    assert any(len(entry["uses"]) > 1 for entry in report["source_facts"])
    text = audit.render_markdown(report)
    assert "45659600.000000000000" in text
    assert "财务质量" in text and "source_url" in text
    assert "](session/" not in text
    assert report["metric_boundary"]["historical_metric_publication_proven"] is False


def test_missing_history_empty_scope_and_equal_date_references(tmp_path):
    history = audit.build_audit(
        _archive(
            tmp_path / "history",
            as_of="2022-04-01",
            compare_with=None,
            years=[2021],
        )
    )
    missing_growth = [
        item
        for item in history["missing_inputs"]
        if item["use"]["metric_status"] == "insufficient_history"
    ]
    assert len(missing_growth) == 3
    assert all(item["expected_input"]["fiscal_year"] == 2020 for item in missing_growth)
    assert "2020" in audit.render_markdown(history)
    empty = audit.build_audit(_archive(tmp_path / "empty", scope="parent_company"))
    assert empty["source_facts"] == [] and empty["missing_inputs"]
    assert empty["evidence_gaps_present"] is True
    assert empty["summary"]["unique_unresolved_parent_ids"] == 0
    assert "不能把空结果视为证据齐全" in audit.render_markdown(empty)
    equal = audit.build_audit(_archive(tmp_path / "equal", compare_with="2024-03-31"))
    assert equal["summary"]["dated_fact_rows"] == 9
    for entry in equal["source_facts"]:
        assert len(entry["uses"]) == len(
            {(u["metric_id"], u["fiscal_year"], u["role"]) for u in entry["uses"]}
        )


def test_portable_export_exact_original_evidence_and_nested_verification(archive, tmp_path):
    root = tmp_path / "output"
    manifest = audit.export_audit(archive, root)
    assert manifest["managed_file_count"] == 26
    assert len([p for p in root.rglob("*") if p.is_file()]) == 27
    for entry in manifest["files"]:
        raw = (root / entry["path"]).read_bytes()
        assert entry["byte_count"] == len(raw)
        assert entry["sha256"] == hashlib.sha256(raw).hexdigest()
    for path in archive.rglob("*"):
        if path.is_file():
            assert (root / "session" / path.relative_to(archive)).read_bytes() == path.read_bytes()
    assert "](session/metrics/report.json)" in (root / "audit.md").read_text(encoding="utf-8")
    moved = tmp_path / "moved"
    shutil.copytree(root, moved)
    assert session.verify_session(moved / "session")["verified_file_count"] == 24
    assert json.loads((moved / "audit.json").read_bytes()) == audit.build_audit(archive)


def test_cli_tamper_invalid_options_and_foreign_output_are_safe(
    archive, tmp_path, monkeypatch, capsys
):
    def forbidden(*args, **kwargs):
        raise AssertionError("legacy initialization")

    monkeypatch.setattr(cli, "load_config", forbidden)
    monkeypatch.setattr(cli, "setup_logging", forbidden)
    assert cli.main(["research", "audit", "--help"]) == 0
    assert "--session" in capsys.readouterr().out
    assert cli.main(["research", "audit", "--session", str(archive), "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["schema"] == audit.SCHEMA
    foreign = tmp_path / "existing"
    foreign.mkdir()
    (foreign / "keep").write_bytes(b"foreign")
    with pytest.raises(audit.AuditError, match="OUTPUT_PATH_EXISTS"):
        audit.export_audit(archive, foreign)
    assert (foreign / "keep").read_bytes() == b"foreign"
    assert sorted(p.name for p in foreign.iterdir()) == ["keep"]
    tampered = tmp_path / "tampered"
    shutil.copytree(archive, tampered)
    (tampered / "index.md").write_bytes(b"unverified claims")
    absent = tmp_path / "absent-parent" / "output"
    assert cli.main(["research", "audit", "--session", str(tampered), "--output", str(absent)]) == 2
    captured = capsys.readouterr()
    assert captured.out == "" and captured.err.startswith("error: VERIFY_")
    assert not absent.parent.exists()
    for options in (["--bad"], ["--output", ""]):
        assert cli.main(["research", "audit", "--session", str(archive), *options]) == 2
        captured = capsys.readouterr()
        assert captured.out == "" and captured.err.startswith("error: ")
