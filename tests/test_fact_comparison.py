"""Direct fact comparison selection from complete pinned directory/ZIP reports."""

import copy
import json
import zipfile

import pytest

from ashare_research import cli
from ashare_research.tools import (
    comparison_focus,
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
    root = tmp_path_factory.mktemp("fact-comparison")
    session = root / "session"
    research_session.export_session({
        "as_of": "2024-03-31", "compare_with": "2025-03-31", "years": [2023, 2025],
        "metrics": METRICS, "scope": "consolidated",
    }, session)
    archive = root / "session.zip"
    package_archive.export_archive(session, archive)
    comparison = session_compare.build_comparison(session, session, right_view="compare_with")
    cash = next(entry for entry in comparison["entries"]
                if entry["metric_id"] == METRIC and entry["fiscal_year"] == 2023)
    binding = next(item for item in cash["before"]["inputs"]
                   if item["role"] == "operating_cash_flow")
    return session, archive, comparison, binding


def test_exact_input_parent_references_combined_filters_and_legacy(delivery, capsys):
    session, archive, original, binding = delivery
    fact = binding["fact_id"]
    parent = binding["parents"]["entries"][0]["fact_id"]
    after_binding = next(entry for entry in original["entries"]
                         if entry["metric_id"] == METRIC and entry["fiscal_year"] == 2023)
    after_fact = next(item["fact_id"] for item in after_binding["after"]["inputs"]
                      if item["role"] == "operating_cash_flow")
    raw = archive.read_bytes()
    saved = copy.deepcopy(original)
    args = ["research", "compare", "--left", str(session), "--right-archive", str(archive),
            "--right-view", "compare_with"]
    assert cli.main([*args, "--fact", fact, "--fact", fact, "--json"]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["schema"] == fact_comparison.SCHEMA and result["facts"] == [fact]
    selected = result["comparison"]
    assert selected["source_report"] == original
    assert selected["selected_key_count"] == 3 and result["reference_count"] == 3
    assert {entry["metric_id"] for entry in selected["entries"]} == set(METRICS)
    assert all(ref["side"] == "before" and ref["input"]["fact_id"] == fact
               and ref["reference_kinds"] == ["input_fact"] and not ref["matched_parents"]
               for ref in result["references"])
    assert selected["entries"] == [entry for entry in original["entries"]
                                    if entry["fiscal_year"] == 2023]
    focused = comparison_focus.build_report(original)
    combined = fact_comparison.build_report(focused, [after_fact, fact])
    assert combined["facts"] == sorted([after_fact, fact])
    assert {ref["side"] for ref in combined["references"]} == {"before", "after"}
    assert combined["reference_count"] == 6
    parents = fact_comparison.build_report(focused, [parent])
    assert parents["comparison"]["selected_key_count"] == 3
    assert all(ref["reference_kinds"] == ["direct_parent"]
               and ref["matched_parents"] == binding["parents"]["entries"][:1]
               for ref in parents["references"])
    assert all(ref["matched_parents"][0]["status"] == "unresolved_absent_from_snapshot"
               for ref in parents["references"])
    assert "unresolved_absent_from_snapshot" in fact_comparison.render_markdown(parents)
    assert cli.main([*args, "--evidence", "--fact", parent, "--metric", METRIC,
                     "--year", "2023", "--changes-only", "--json"]) == 0
    evidence = json.loads(capsys.readouterr().out)
    assert evidence["comparison"]["mode"] == "evidence"
    assert evidence["comparison"]["selected_key_count"] == 1
    assert evidence["comparison"]["selected_input_role_count"] == 2
    assert evidence["comparison"]["entries"] == [next(
        entry for entry in evidence["comparison"]["source_report"]["entries"]
        if entry["metric_id"] == METRIC and entry["fiscal_year"] == 2023)]
    assert cli.main([*args, "--fact", fact, "--year", "2025", "--json"]) == 0
    empty = json.loads(capsys.readouterr().out)
    assert empty["comparison"]["entries"] == [] and empty["references"] == []
    assert "当前选择没有匹配项" in fact_comparison.render_markdown(empty)
    unchanged = session_compare.build_comparison(session, session)
    no_changes = fact_comparison.build_report(
        comparison_focus.build_report(unchanged, changes_only=True), [fact],
    )
    assert no_changes["comparison"]["selected_key_count"] == 0
    for extra, expected in (([], original),
                            (["--evidence"], evidence_comparison.build_report(original)),
                            (["--year", "2023"],
                             comparison_focus.build_report(original, years=[2023]))):
        assert cli.main([*args, *extra, "--json"]) == 0
        assert json.loads(capsys.readouterr().out) == expected
    assert original == saved and archive.read_bytes() == raw


def test_unknown_invalid_export_outer_forgery_and_verified_handoff(
    delivery, tmp_path, monkeypatch, capsys,
):
    session, archive, _, binding = delivery
    fact = binding["fact_id"]
    args = ["research", "compare", "--left", str(session), "--right-archive", str(archive)]
    for extra in (["--fact", "unknown"], ["--fact", fact, "--fact", "unknown"],
                  ["--fact", "unknown", "--year", "2025", "--changes-only"]):
        assert cli.main([*args, *extra, "--json"]) == 2
        captured = capsys.readouterr()
        assert captured.out == "" and captured.err == "error: FACT_NOT_REFERENCED\n"
    output = tmp_path / "not-created"
    for extra in (["--fact", ""], ["--fact", " "],
                  ["--fact", fact, "--output", str(output)]):
        assert cli.main(["research", "compare", "--left", "absent", "--right", "absent",
                         *extra]) == 2
        captured = capsys.readouterr()
        assert captured.out == "" and captured.err == "error: INVALID_ARGUMENTS\n"
    assert not output.exists()
    with zipfile.ZipFile(archive) as source:
        files = {name: source.read(name) for name in source.namelist()}
    files["index.md"] += b"\nForged outer content\n"
    forged = tmp_path / "forged.zip"
    with zipfile.ZipFile(forged, "w") as target:
        for name, content in files.items():
            target.writestr(name, content)
    assert cli.main(["research", "compare", "--left", str(session), "--right-archive",
                     str(forged), "--fact", fact]) == 2
    captured = capsys.readouterr()
    assert captured.out == "" and captured.err == "error: VERIFY_FILE_MISMATCH\n"
    handoff = tmp_path / "handoff.zip"
    handoff.write_bytes(archive.read_bytes())
    loader = package_archive.load_verified_archive
    calls = []

    def mutate_after_load(path):
        result = loader(path)
        calls.append(path)
        path.write_bytes(b"mutated after verified map")
        return result

    monkeypatch.setattr(package_archive, "load_verified_archive", mutate_after_load)
    selected = ["research", "compare", "--left", str(session), "--right-archive", str(handoff),
                "--fact", fact, "--json"]
    assert cli.main(selected) == 0
    assert calls == [handoff] and json.loads(capsys.readouterr().out)["reference_count"] == 6
    assert cli.main(selected) == 2
    captured = capsys.readouterr()
    assert captured.out == "" and captured.err == "error: ARCHIVE_INVALID\n"
