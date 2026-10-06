"""Original audit uses/omissions from freshly verified pinned directory and ZIP."""

import copy
import json
import zipfile

import pytest

from ashare_research import cli
from ashare_research.tools import (
    audit_focus,
    delivered_research,
    evidence_audit,
    package_archive,
    research_session,
)

METRIC = "cash_based_free_cash_flow_proxy"
YOY = "operating_cash_flow_yoy"


@pytest.fixture(scope="module")
def delivery(tmp_path_factory):
    root = tmp_path_factory.mktemp("audit-focus")
    session = root / "session"
    research_session.export_session({
        "as_of": "2024-03-31", "compare_with": "2025-03-31", "years": [2023, 2025],
        "metrics": [METRIC, YOY], "scope": "consolidated",
    }, session)
    audit = root / "audit"
    evidence_audit.export_audit(session, audit)
    archive = root / "audit.zip"
    package_archive.export_archive(audit, archive)
    original = delivered_research.read_report(archive, "audit", archive=True)
    fact = next(item["fact"] for item in original["report"]["source_facts"]
                if item["date"] == "2024-03-31" and item["fact"]["fiscal_year"] == 2023
                and item["fact"]["concept_id"] == "operating_cash_flow")
    return audit, archive, original, fact


def test_original_facts_use_year_parents_missing_empty_and_legacy(delivery, capsys):
    audit, archive, original, fact = delivery
    saved = copy.deepcopy(original)
    raw = archive.read_bytes()
    source = original["report"]
    args = ["research", "read", "--archive", str(archive), "--section", "audit"]
    assert cli.main([*args, "--metric", METRIC, "--metric", METRIC,
                     "--year", "2023", "--year", "2023", "--gaps-only", "--json"]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["schema"] == audit_focus.SCHEMA and report["source_read"] == original
    assert report["selection"] == {"metrics": [METRIC], "years": [2023],
                                   "facts": [], "gaps_only": True}
    expected = []
    for item in source["source_facts"]:
        uses = [use for use in item["uses"]
                if use["metric_id"] == METRIC and use["fiscal_year"] == 2023]
        if uses and item["gaps"]:
            expected.append({**item, "uses": uses})
    assert report["source_facts"] == expected and report["selected_fact_row_count"] == 4
    assert report["selected_use_count"] == 4 and report["missing_inputs"] == []
    assert all(item["fact"] in [row["fact"] for row in source["source_facts"]]
               for item in report["source_facts"])
    use_year = audit_focus.build_report(original, metrics=[YOY], years=[2023])
    assert any(item["fact"]["fiscal_year"] == 2022
               and any(use["fiscal_year"] == 2023 and use["role"] == "prior"
                       for use in item["uses"]) for item in use_year["source_facts"])
    parent = fact["parents"]["entries"][0]["fact_id"]
    for selected_fact, kind in ((fact["fact_id"], "input_fact"), (parent, "direct_parent")):
        selected = audit_focus.build_report(original, facts=[selected_fact, selected_fact])
        assert selected["selection"]["facts"] == [selected_fact]
        assert selected["missing_inputs"] == [] and selected["source_facts"]
        assert all(ref["reference_kinds"] == [kind] for ref in selected["fact_references"])
        for item in selected["source_facts"]:
            assert item in source["source_facts"]
        if kind == "direct_parent":
            assert all(ref["matched_parents"] == fact["parents"]["entries"][:1]
                       for ref in selected["fact_references"])
            assert "unresolved_absent_from_snapshot" in audit_focus.render_markdown(selected)
    combined = audit_focus.build_report(original, facts=[parent, fact["fact_id"]])
    assert {ref["requested_fact_id"] for ref in combined["fact_references"]} == {
        parent, fact["fact_id"],
    }
    missing = audit_focus.build_report(original, metrics=[METRIC], years=[2025], gaps_only=True)
    assert missing["missing_inputs"] == [item for item in source["missing_inputs"]
                                         if item["use"]["metric_id"] == METRIC
                                         and item["use"]["fiscal_year"] == 2025]
    assert missing["selected_missing_input_count"] == 4
    empty = audit_focus.build_report(original, years=[2025], facts=[fact["fact_id"]])
    assert empty["source_facts"] == [] and empty["missing_inputs"] == []
    assert "当前选择没有匹配项，不能据此判断证据齐全" in audit_focus.render_markdown(empty)
    assert all(note in report["notes"] for note in source["notes"])
    assert cli.main(["research", "read", "--package", str(audit), "--section", "audit",
                     "--metric", METRIC, "--year", "2023", "--gaps-only"]) == 0
    assert capsys.readouterr().out == audit_focus.render_markdown(report)
    assert cli.main([*args, "--json"]) == 0
    assert json.loads(capsys.readouterr().out) == original
    assert cli.main(args) == 0
    assert capsys.readouterr().out == evidence_audit.render_markdown(source)
    assert original == saved and archive.read_bytes() == raw


def test_invalid_unknown_outer_forgery_and_canonical_handoff(
    delivery, tmp_path, monkeypatch, capsys,
):
    _, archive, _, fact = delivery
    for section, extra in (("review", ["--gaps-only"]), ("compare", ["--metric", METRIC]),
                           ("audit", ["--metric", " "]), ("audit", ["--fact", ""]),
                           ("audit", ["--year", "0"]), ("audit", ["--year", "abc"])):
        assert cli.main(["research", "read", "--archive", "absent", "--section", section,
                         *extra]) == 2
        captured = capsys.readouterr()
        assert captured.out == "" and captured.err == "error: INVALID_ARGUMENTS\n"
    args = ["research", "read", "--archive", str(archive), "--section", "audit", "--json"]
    for extra, code in ((["--metric", "unknown"], "METRIC_NOT_SELECTED"),
                        (["--year", "1999"], "YEAR_NOT_SELECTED"),
                        (["--fact", "unknown", "--year", "2025"], "FACT_NOT_REFERENCED"),
                        (["--fact", fact["fact_id"], "--fact", "unknown"],
                         "FACT_NOT_REFERENCED")):
        assert cli.main([*args, *extra]) == 2
        captured = capsys.readouterr()
        assert captured.out == "" and captured.err == f"error: {code}\n"
    with zipfile.ZipFile(archive) as source:
        files = {name: source.read(name) for name in source.namelist()}
    files["audit.md"] += b"\nForged outer audit\n"
    forged = tmp_path / "forged.zip"
    with zipfile.ZipFile(forged, "w") as target:
        for name, content in files.items():
            target.writestr(name, content)
    assert cli.main(["research", "read", "--archive", str(forged), "--section", "audit",
                     "--gaps-only", "--json"]) == 2
    captured = capsys.readouterr()
    assert captured.out == "" and captured.err == "error: VERIFY_FILE_MISMATCH\n"
    handoff = tmp_path / "handoff.zip"
    handoff.write_bytes(archive.read_bytes())
    loader = package_archive.load_verified_archive
    calls = []

    def mutate_after_load(path):
        result = loader(path)
        calls.append(path)
        path.write_bytes(b"changed after verified map")
        return result

    monkeypatch.setattr(package_archive, "load_verified_archive", mutate_after_load)
    selected = ["research", "read", "--archive", str(handoff), "--section", "audit",
                "--metric", METRIC, "--year", "2023", "--gaps-only", "--json"]
    assert cli.main(selected) == 0
    assert calls == [handoff]
    assert json.loads(capsys.readouterr().out)["selected_fact_row_count"] == 4
    assert cli.main(selected) == 2
    captured = capsys.readouterr()
    assert captured.out == "" and captured.err == "error: ARCHIVE_INVALID\n"
