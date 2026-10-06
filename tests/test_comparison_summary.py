"""Compact original values/contexts, including absent metrics and complete ZIP checks."""

import copy
import json
import zipfile

import pytest

from ashare_research import cli
from ashare_research.tools import (
    comparison_focus,
    comparison_summary,
    evidence_comparison,
    fact_comparison,
    package_archive,
    research_session,
    session_compare,
)

METRIC = "cash_based_free_cash_flow_proxy"
METRICS = [METRIC, "operating_cash_flow_to_attributable_net_profit", "operating_cash_flow_yoy"]


@pytest.fixture(scope="module")
def delivery(tmp_path_factory):
    root = tmp_path_factory.mktemp("comparison-summary")
    sessions = []
    for name, years in (("left", [2023]), ("right", [2023, 2025])):
        path = root / name
        research_session.export_session({
            "as_of": "2024-03-31", "compare_with": "2025-03-31", "years": years,
            "metrics": METRICS, "scope": "consolidated",
        }, path)
        sessions.append(path)
    archive = root / "right.zip"
    package_archive.export_archive(sessions[1], archive)
    original = session_compare.build_comparison(*sessions, right_view="compare_with")
    binding = next(item for entry in original["entries"]
                   if entry["metric_id"] == METRIC and entry["fiscal_year"] == 2023
                   for item in entry["before"]["inputs"] if item["role"] == "operating_cash_flow")
    return sessions[0], archive, original, binding["fact_id"]


def test_all_modes_exact_rows_roles_refs_contexts_empty_and_legacy(delivery, capsys):
    session, archive, original, fact = delivery
    raw = archive.read_bytes()
    snapshot = copy.deepcopy(original)
    evidence = evidence_comparison.build_report(original)
    focused = comparison_focus.build_report(evidence, years=[2023], changes_only=True)
    fact_report = fact_comparison.build_report(focused, [fact])
    sources = [original, evidence, comparison_focus.build_report(original, years=[2023]),
               focused, fact_report]
    args = ["research", "compare", "--left", str(session), "--right-archive", str(archive),
            "--right-view", "compare_with"]
    modes = [[], ["--evidence"], ["--year", "2023"],
             ["--evidence", "--year", "2023", "--changes-only"],
             ["--evidence", "--year", "2023", "--changes-only", "--fact", fact]]
    for extra, source in zip(modes, sources, strict=True):
        report = comparison_summary.build_report(source)
        assert report["schema"] == comparison_summary.SCHEMA
        assert report["source_report"] == source
        assert report["source_key_count"] == 6
        expected = original["entries"] if not extra or extra == ["--evidence"] else [
            entry for entry in original["entries"] if entry["fiscal_year"] == 2023]
        assert report["entries"] == expected
        assert report["selected_key_count"] == len(expected)
        text = comparison_summary.render_markdown(report)
        assert "17407700.000000000000 万元" in text
        assert "17433900.000000000000 万元" in text
        assert "2.833465720101 ratio" in text
        assert "2.830281140422 ratio" in text
        assert "2024-03-31 / as_of / consolidated" in text
        assert "2025-03-31 / compare_with / consolidated" in text
        assert original["left"]["session_manifest_sha256"] in text
        assert all(note in report["notes"] for note in original["notes"])
        assert "```json" not in text and "原始变化字段" not in text
        assert cli.main([*args, *extra, "--summary", "--json"]) == 0
        assert json.loads(capsys.readouterr().out) == report
    summary = comparison_summary.build_report(original)
    missing = next(entry for entry in summary["entries"] if entry["fiscal_year"] == 2025)
    assert missing["before"] is None and missing["after"]["value"] is None
    assert missing["state"] == "added"
    text = comparison_summary.render_markdown(summary)
    assert "未选择" in text and "缺失 万元" in text and "新增选择" in text
    report = comparison_summary.build_report(fact_report)
    assert report["selected_input_role_count"] == 6 and report["reference_count"] == 3
    assert report["evidence_entries"] == fact_report["comparison"]["entries"]
    assert report["fact_references"] == fact_report["references"]
    assert all(note in report["notes"] for source in (evidence, focused, fact_report)
               for note in source["notes"])
    assert fact in comparison_summary.render_markdown(report)
    empty = comparison_summary.build_report(fact_comparison.build_report(
        comparison_focus.build_report(evidence, years=[2025]), [fact],
    ))
    assert empty["entries"] == [] and empty["fact_references"] == []
    assert "当前选择没有匹配项" in comparison_summary.render_markdown(empty)
    assert cli.main([*args, "--summary"]) == 0
    assert capsys.readouterr().out == comparison_summary.render_markdown(summary)
    assert cli.main([*args, "--json"]) == 0
    assert json.loads(capsys.readouterr().out) == original
    assert original == snapshot and archive.read_bytes() == raw


def test_export_unknown_whole_forgery_and_canonical_handoff(
    delivery, tmp_path, monkeypatch, capsys,
):
    session, archive, _, fact = delivery
    output = tmp_path / "not-created"
    assert cli.main(["research", "compare", "--left", "absent", "--right", "absent",
                     "--summary", "--output", str(output)]) == 2
    captured = capsys.readouterr()
    assert captured.out == "" and captured.err == "error: INVALID_ARGUMENTS\n"
    assert not output.exists()
    args = ["research", "compare", "--left", str(session), "--right-archive", str(archive),
            "--summary", "--json"]
    assert cli.main([*args, "--fact", "unknown"]) == 2
    captured = capsys.readouterr()
    assert captured.out == "" and captured.err == "error: FACT_NOT_REFERENCED\n"
    with zipfile.ZipFile(archive) as source:
        files = {name: source.read(name) for name in source.namelist()}
    files["index.md"] += b"\nForged outer content\n"
    forged = tmp_path / "forged.zip"
    with zipfile.ZipFile(forged, "w") as target:
        for name, content in files.items():
            target.writestr(name, content)
    assert cli.main(["research", "compare", "--left", str(session), "--right-archive",
                     str(forged), "--summary"]) == 2
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
    selected = ["research", "compare", "--left", str(session), "--right-archive", str(handoff),
                "--fact", fact, "--summary", "--json"]
    assert cli.main(selected) == 0
    assert calls == [handoff] and json.loads(capsys.readouterr().out)["selected_key_count"] == 3
    assert cli.main(selected) == 2
    captured = capsys.readouterr()
    assert captured.out == "" and captured.err == "error: ARCHIVE_INVALID\n"
