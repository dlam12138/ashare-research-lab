"""Focused original records from fresh pinned comparisons, including empty results."""

import copy
import json
import zipfile

import pytest

from ashare_research import cli
from ashare_research.tools import comparison_focus as focus
from ashare_research.tools import (
    evidence_comparison,
    package_archive,
    research_session,
    session_compare,
)

METRIC = "cash_based_free_cash_flow_proxy"


@pytest.fixture(scope="module")
def delivery(tmp_path_factory):
    root = tmp_path_factory.mktemp("comparison-focus")
    session = root / "session"
    research_session.export_session({
        "as_of": "2024-03-31", "compare_with": "2025-03-31", "years": [2023, 2024, 2025],
        "metrics": [METRIC], "scope": "consolidated",
    }, session)
    archive = root / "session.zip"
    package_archive.export_archive(session, archive)
    return session, archive


def test_exact_filtered_records_changed_roles_empty_results_and_default(delivery, capsys):
    session, archive = delivery
    before = archive.read_bytes()
    args = ["research", "compare", "--left", str(session), "--right-archive", str(archive)]
    assert cli.main([*args, "--right-view", "compare_with", "--metric", METRIC,
                     "--metric", METRIC, "--year", "2023", "--year", "2023",
                     "--changes-only", "--json"]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["schema"] == focus.SCHEMA and report["mode"] == "metrics"
    assert report["selection"] == {"metrics": [METRIC], "years": [2023], "changes_only": True}
    assert report["selected_key_count"] == 1 and report["source_key_count"] == 3
    assert report["entries"] == [next(r for r in report["source_report"]["entries"]
                                     if r["fiscal_year"] == 2023)]
    assert report["entries"][0]["state"] == "value_changed"
    text = focus.render_markdown(report)
    assert "17407700.000000000000" in text and "17433900.000000000000" in text
    assert "匹配指标键：1 / 3" in text
    assert cli.main([*args, "--right-view", "compare_with", "--evidence", "--year", "2023",
                     "--changes-only", "--json"]) == 0
    evidence = json.loads(capsys.readouterr().out)
    assert evidence["mode"] == "evidence" and evidence["selected_input_role_count"] == 2
    expected = next(row for row in evidence["source_report"]["entries"]
                    if row["fiscal_year"] == 2023)
    assert evidence["entries"] == [expected]
    assert all(item["field_changes"] for item in evidence["entries"][0]["inputs"])
    assert "source_url" in focus.render_markdown(evidence)
    assert cli.main([*args, "--json"]) == 0
    original = json.loads(capsys.readouterr().out)
    assert original["schema"] == session_compare.SCHEMA
    snapshot = copy.deepcopy(original)
    empty = focus.build_report(original, changes_only=True)
    assert empty["entries"] == [] and empty["selected_key_count"] == 0
    assert "当前选择没有匹配项" in focus.render_markdown(empty)
    missing = focus.build_report(original, years=[2025])
    assert missing["entries"][0]["before"]["value"] is None
    assert missing["entries"][0]["after"]["value"] is None
    assert original == snapshot
    assert cli.main([*args, "--evidence", "--json"]) == 0
    old_evidence = json.loads(capsys.readouterr().out)
    assert old_evidence == evidence_comparison.build_report(original)
    assert focus.build_report(old_evidence, changes_only=True)["entries"] == []
    # Independent selection edge: a supplied original unchanged financial state
    # must not hide changed evidence or mutate the complete source report.
    specimen = copy.deepcopy(evidence["source_report"])
    specimen["entries"] = [copy.deepcopy(expected)]
    specimen["entries"][0]["metric_state"] = "unchanged"
    specimen["entries"][0]["inputs"][0]["field_changes"] = []
    saved = copy.deepcopy(specimen)
    selected = focus.build_report(specimen, changes_only=True)
    assert selected["entries"][0]["metric_state"] == "unchanged"
    assert selected["entries"][0]["inputs"] == [expected["inputs"][1]]
    assert selected["source_report"] == saved and specimen == saved
    assert archive.read_bytes() == before


def test_selector_errors_export_rejection_outer_forgery_and_canonical_handoff(
    delivery, tmp_path, monkeypatch, capsys,
):
    session, archive = delivery
    for extra, code in ((["--metric", "unknown"], "METRIC_NOT_COMPARED"),
                        (["--year", "1999"], "YEAR_NOT_COMPARED")):
        assert cli.main(["research", "compare", "--left", str(session),
                         "--right-archive", str(archive), *extra]) == 2
        captured = capsys.readouterr()
        assert captured.out == "" and captured.err == f"error: {code}\n"
    for extra in (["--metric", " "], ["--year", "0"], ["--year", "abc"],
                  ["--changes-only", "--output", str(tmp_path / "not-created")]):
        assert cli.main(["research", "compare", "--left", "absent", "--right", "absent",
                         *extra]) == 2
        captured = capsys.readouterr()
        assert captured.out == "" and captured.err == "error: INVALID_ARGUMENTS\n"
    assert not (tmp_path / "not-created").exists()
    with zipfile.ZipFile(archive) as source:
        files = {name: source.read(name) for name in source.namelist()}
    files["index.md"] += b"\nForged outer index\n"
    forged = tmp_path / "forged.zip"
    with zipfile.ZipFile(forged, "w") as target:
        for name, raw in files.items():
            target.writestr(name, raw)
    assert cli.main(["research", "compare", "--left", str(session), "--right-archive",
                     str(forged), "--metric", METRIC, "--json"]) == 2
    captured = capsys.readouterr()
    assert captured.out == "" and captured.err == "error: VERIFY_FILE_MISMATCH\n"
    handoff = tmp_path / "handoff.zip"
    handoff.write_bytes(archive.read_bytes())
    loader = package_archive.load_verified_archive
    calls = []

    def mutate_after_load(path):
        verified = loader(path)
        calls.append(path)
        path.write_bytes(b"changed after verification")
        return verified

    monkeypatch.setattr(package_archive, "load_verified_archive", mutate_after_load)
    args = ["research", "compare", "--left", str(session), "--right-archive", str(handoff),
            "--evidence", "--metric", METRIC, "--year", "2023", "--json"]
    assert cli.main(args) == 0
    assert calls == [handoff] and json.loads(capsys.readouterr().out)["selected_key_count"] == 1
    assert cli.main(args) == 2
    captured = capsys.readouterr()
    assert captured.out == "" and captured.err == "error: ARCHIVE_INVALID\n"
