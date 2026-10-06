"""Evidence trace acceptance against complete real fixed packages."""

import json
import zipfile

import pytest

from ashare_research import cli
from ashare_research.tools import metric_evidence_trace as trace
from ashare_research.tools import package_archive, research_session, research_workflow

METRIC = "cash_based_free_cash_flow_proxy"


@pytest.fixture(scope="module")
def delivery(tmp_path_factory):
    root = tmp_path_factory.mktemp("metric-trace")
    request = {
        "as_of": "2024-03-31", "compare_with": "2025-03-31",
        "years": [2023, 2024], "metrics": [METRIC], "scope": "consolidated",
    }
    workflow = root / "workflow"
    research_workflow.export_workflow(request, workflow)
    archive = root / "workflow.zip"
    package_archive.export_archive(workflow, archive)
    return root, workflow, archive, request


def test_exact_metric_rows_input_evidence_missing_values_and_public_formats(
    delivery, tmp_path, capsys,
):
    root, workflow, archive, request = delivery
    original = {p.relative_to(root): p.read_bytes() for p in root.rglob("*") if p.is_file()}
    metrics = json.loads((workflow / "session/metrics/report.json").read_bytes())
    result = trace.trace_metric(archive, METRIC, 2023, archive=True)
    assert result["request"] == metrics["request"]
    assert result["boundary"] == metrics["boundary"]
    assert result["metric_limitations"] == metrics["limitations_zh"]
    for view in result["views"]:
        expected = next(row for row in metrics[view["view"]]["records"]
                        if row["fiscal_year"] == 2023)
        assert view["record"] == expected
        assert view["date"] == metrics[view["view"]]["date"]
        for binding in view["record"]["inputs"]:
            assert binding["missing_source_reference_fields"]
            assert binding["parents"]["unresolved"] == 2
            assert binding["source_reference"] and binding["lineage"]
    expected_comparison = next(row for row in metrics["comparison"]["entries"]
                               if row["fiscal_year"] == 2023)
    assert result["comparison"] == expected_comparison
    assert result["comparison"]["state"] == "value_changed"
    markdown = trace.render_markdown(result)
    assert "17407700.000000000000" in markdown and "17433900.000000000000" in markdown
    assert "source_url" in markdown and "unresolved_absent_from_snapshot" in markdown
    for view in result["views"]:
        for binding in view["record"]["inputs"]:
            assert binding["fact_id"] in markdown
            assert all(p["fact_id"] in markdown for p in binding["parents"]["entries"])
    assert cli.main([
        "research", "trace", "--archive", str(archive), "--metric", METRIC,
        "--year", "2023", "--json",
    ]) == 0
    captured = capsys.readouterr()
    assert json.loads(captured.out) == result and captured.err == ""
    directory = trace.trace_metric(workflow, METRIC, 2023)
    assert directory["views"] == result["views"]
    assert directory["comparison"] == result["comparison"]
    assert directory["archive_receipt"] is None
    assert cli.main([
        "research", "trace", "--package", str(workflow / "session"),
        "--metric", METRIC, "--year", "2023",
    ]) == 0
    assert capsys.readouterr().out == markdown
    missing = trace.trace_metric(workflow / "session", METRIC, 2024)
    assert missing["views"][0]["record"]["value"] is None
    assert missing["views"][0]["record"]["missing_roles"]
    assert any(b["status"] == "missing" for b in missing["views"][0]["record"]["inputs"])
    assert "缺失" in trace.render_markdown(missing)
    single = tmp_path / "single"
    research_session.export_session({**request, "compare_with": None}, single)
    single_zip = tmp_path / "single.zip"
    package_archive.export_archive(single, single_zip)
    one = trace.trace_metric(single_zip, METRIC, 2023, archive=True)
    assert len(one["views"]) == 1 and one["comparison"] is None
    assert one["views"][0] == result["views"][0]
    assert {p.relative_to(root): p.read_bytes() for p in root.rglob("*") if p.is_file()} == original


def test_selector_errors_outer_tampering_and_fresh_canonical_handoff(
    delivery, tmp_path, monkeypatch, capsys,
):
    _, workflow, archive, _ = delivery
    for metric, year in (("unknown", 2023), (METRIC, 1999)):
        with pytest.raises(trace.TraceError, match="METRIC_NOT_SELECTED"):
            trace.trace_metric(archive, metric, year, archive=True)
    with pytest.raises(trace.TraceError, match="SESSION_PACKAGE_REQUIRED"):
        trace.trace_metric(workflow / "audit", METRIC, 2023)
    for extra in (
        ["--year", "0"], ["--year", "not-a-year"], [],
        ["--year", "2023", "--package", str(workflow)],
        ["--year", "2023", "--output", str(tmp_path / "not-created")],
    ):
        assert cli.main([
            "research", "trace", "--archive", str(archive), "--metric", METRIC, *extra,
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
    before = forged.read_bytes()
    assert cli.main([
        "research", "trace", "--archive", str(forged), "--metric", METRIC,
        "--year", "2023", "--json",
    ]) == 2
    captured = capsys.readouterr()
    assert captured.out == "" and captured.err == "error: VERIFY_FILE_MISMATCH\n"
    assert forged.read_bytes() == before
    handoff = tmp_path / "handoff.zip"
    handoff.write_bytes(archive.read_bytes())
    loader = package_archive.load_verified_archive
    calls = []

    def mutate_after_verification(path):
        verified = loader(path)
        calls.append(path)
        path.write_bytes(b"changed after verification")
        return verified

    with monkeypatch.context() as patch:
        patch.setattr(package_archive, "load_verified_archive", mutate_after_verification)
        result = trace.trace_metric(handoff, METRIC, 2023, archive=True)
    assert calls == [handoff] and len(result["views"]) == 2
    with pytest.raises(trace.TraceError, match="ARCHIVE_INVALID"):
        trace.trace_metric(handoff, METRIC, 2023, archive=True)
