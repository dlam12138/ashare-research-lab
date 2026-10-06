"""Original verified metric comparisons with complete per-role evidence differences."""

import json
import zipfile

import pytest

from ashare_research import cli
from ashare_research.tools import evidence_comparison as evidence
from ashare_research.tools import package_archive, research_session, session_compare

METRIC = "cash_based_free_cash_flow_proxy"


@pytest.fixture(scope="module")
def delivery(tmp_path_factory):
    root = tmp_path_factory.mktemp("input-evidence")
    session = root / "session"
    request = {
        "as_of": "2024-03-31", "compare_with": "2025-03-31", "years": [2023, 2024],
        "metrics": [METRIC], "scope": "consolidated",
    }
    research_session.export_session(request, session)
    archive = root / "session.zip"
    package_archive.export_archive(session, archive)
    return session, archive, request


def test_original_comparison_bindings_changes_missing_and_default_compatibility(delivery, capsys):
    session, archive, _ = delivery
    before = archive.read_bytes()
    original = json.loads((session / "metrics/report.json").read_bytes())
    args = ["research", "compare", "--left", str(session), "--right-archive", str(archive)]
    assert cli.main([*args, "--right-view", "compare_with", "--evidence", "--json"]) == 0
    captured = capsys.readouterr()
    report = json.loads(captured.out)
    assert captured.err == "" and report["schema"] == evidence.SCHEMA
    comparison = report["comparison"]
    assert comparison["original_common_comparison"] == original["comparison"]
    assert comparison["left"]["boundary"] == original["boundary"]
    for entry in report["entries"]:
        for side, view in (("before", "as_of"), ("after", "compare_with")):
            row = next(r for r in original[view]["records"]
                       if r["fiscal_year"] == entry["fiscal_year"])
            compared = next(r for r in comparison["entries"]
                            if r["fiscal_year"] == entry["fiscal_year"])
            assert compared[side] == row
            assert entry["metric_state"] == compared["state"]
            assert {item["role"] for item in entry["inputs"]} == set(row["input_roles"])
            for item in entry["inputs"]:
                assert item[side] == next(b for b in row["inputs"] if b["role"] == item["role"])
    changed = next(row for row in report["entries"] if row["fiscal_year"] == 2023)
    cash = next(b for b in changed["inputs"] if b["role"] == "operating_cash_flow")
    fact_change = next(field for field in cash["field_changes"] if field["field"] == "fact_id")
    assert fact_change == {
        "field": "fact_id", "before_present": True, "after_present": True,
        "before": cash["before"]["fact_id"], "after": cash["after"]["fact_id"],
    }
    assert fact_change["before"] != fact_change["after"]
    missing = next(row for row in report["entries"] if row["fiscal_year"] == 2024)
    field = next(f for item in missing["inputs"] for f in item["field_changes"]
                 if f["field"] == "fact_id")
    assert field["before_present"] is False and field["before"] is None
    assert field["after_present"] is True and field["after"] is not None
    text = evidence.render_markdown(report)
    assert text.startswith(session_compare.render_markdown(comparison).rstrip())
    assert "17407700.000000000000" in text and "17433900.000000000000" in text
    assert "source_url" in text and "unresolved_absent_from_snapshot" in text
    assert "missing / 缺失" in text and "不等于变化原因" in text
    assert cli.main([*args, "--json"]) == 0
    default = json.loads(capsys.readouterr().out)
    assert default["schema"] == session_compare.SCHEMA and "field_changes" not in default
    unchanged = evidence.build_report(default)
    assert all(not b["field_changes"] for row in unchanged["entries"] for b in row["inputs"])
    assert cli.main(args) == 0
    # Canonical JSON sorts keys; the existing Markdown uses original label order.
    expected = {**default,
                "states": {key: default["states"][key] for key in session_compare.LABELS}}
    assert capsys.readouterr().out == session_compare.render_markdown(expected)
    assert archive.read_bytes() == before


def test_selector_changes_failures_outer_forgery_and_canonical_handoff(
    delivery, tmp_path, monkeypatch, capsys,
):
    session, archive, request = delivery
    subset = tmp_path / "subset"
    research_session.export_session({**request, "years": [2023]}, subset)
    compared = session_compare.build_comparison(subset, session)
    report = evidence.build_report(compared)
    added = next(row for row in report["entries"] if row["fiscal_year"] == 2024)
    assert added["before_metric_selected"] is False and added["after_metric_selected"] is True
    assert added["metric_state"] == "added"
    assert all(b["before"] is None and b["after"]["status"] == "missing"
               for b in added["inputs"])
    text = evidence.render_markdown(report)
    assert "指标未选择" in text and "missing / 缺失" in text
    assert all(not field["before_present"] for b in added["inputs"] for field in b["field_changes"])
    for extra in (["--output", str(tmp_path / "not-created")], ["--right-view", "unknown"]):
        assert cli.main([
            "research", "compare", "--left", "does-not-exist", "--right", "absent",
            "--evidence", *extra,
        ]) == 2
        captured = capsys.readouterr()
        assert captured.out == "" and captured.err == "error: INVALID_ARGUMENTS\n"
    assert not (tmp_path / "not-created").exists()
    with zipfile.ZipFile(archive) as source:
        files = {name: source.read(name) for name in source.namelist()}
    files["index.md"] += b"\nForged outer navigation\n"
    forged = tmp_path / "forged.zip"
    with zipfile.ZipFile(forged, "w") as target:
        for name, raw in files.items():
            target.writestr(name, raw)
    assert cli.main([
        "research", "compare", "--left", str(session), "--right-archive", str(forged),
        "--evidence", "--json",
    ]) == 2
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
    assert cli.main([
        "research", "compare", "--left", str(session), "--right-archive", str(handoff),
        "--evidence", "--json",
    ]) == 0
    assert calls == [handoff]
    assert json.loads(capsys.readouterr().out)["schema"] == evidence.SCHEMA
    assert cli.main([
        "research", "compare", "--left", str(session), "--right-archive", str(handoff),
        "--evidence",
    ]) == 2
    captured = capsys.readouterr()
    assert captured.out == "" and captured.err == "error: ARCHIVE_INVALID\n"
