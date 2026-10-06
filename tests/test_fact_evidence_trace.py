"""Reverse references are original bindings, including missing direct parents."""

import json
import zipfile

import pytest

from ashare_research import cli
from ashare_research.tools import metric_evidence_trace as trace
from ashare_research.tools import package_archive, research_workflow


@pytest.fixture(scope="module")
def delivery(tmp_path_factory):
    root = tmp_path_factory.mktemp("fact-trace")
    workflow = root / "workflow"
    research_workflow.export_workflow({
        "as_of": "2024-03-31", "compare_with": "2025-03-31", "years": [2023, 2024],
        "metrics": ["cash_based_free_cash_flow_proxy",
                    "operating_cash_flow_to_attributable_net_profit"],
        "scope": "consolidated",
    }, workflow)
    archive = root / "workflow.zip"
    package_archive.export_archive(workflow, archive)
    metrics = json.loads((workflow / "session/metrics/report.json").read_bytes())
    binding = next(item for row in metrics["as_of"]["records"] for item in row["inputs"]
                   if item["role"] == "operating_cash_flow" and row["fiscal_year"] == 2023)
    return workflow, archive, metrics, binding


def test_all_original_shared_input_and_missing_parent_references(delivery, capsys):
    workflow, archive, metrics, binding = delivery
    before = archive.read_bytes()
    for fact_id, kind in ((binding["fact_id"], "input_fact"),
                          (binding["parents"]["entries"][0]["fact_id"], "direct_parent")):
        result = trace.trace_fact(archive, fact_id, archive=True)
        expected = []
        for metric, role in (("cash_based_free_cash_flow_proxy", "operating_cash_flow"),
                             ("operating_cash_flow_to_attributable_net_profit", "numerator")):
            row = next(r for r in metrics["as_of"]["records"]
                       if r["metric_id"] == metric and r["fiscal_year"] == 2023)
            item = next(b for b in row["inputs"] if b["role"] == role)
            expected.append({
                "view": "as_of", "date": "2024-03-31", "record": row, "input": item,
                "matched_parents": [] if kind == "input_fact" else
                [next(p for p in item["parents"]["entries"] if p["fact_id"] == fact_id)],
                "reference_kinds": [kind],
            })
        assert result["references"] == expected
        assert len({ref["record"]["metric_id"] for ref in expected}) == 2
        assert all(ref["reference_kinds"] == [kind] for ref in expected)
        assert result["request"] == metrics["request"]
        assert result["boundary"] == metrics["boundary"]
        assert result["metric_limitations"] == metrics["limitations_zh"]
        assert result["verification"]["compared_every_byte"]
        directory = trace.trace_fact(workflow / "session", fact_id)
        assert directory["references"] == expected and directory["archive_receipt"] is None
        text = trace.render_markdown(result)
        assert fact_id in text and "source_url" in text
        assert "不推断间接依赖或因果影响" in text
        if kind == "direct_parent":
            assert "直接父记录" in text and "unresolved_absent_from_snapshot" in text
            assert all(not parent["retained_in_snapshot"] for ref in expected
                       for parent in ref["matched_parents"])
        assert cli.main([
            "research", "trace", "--archive", str(archive), "--fact", fact_id, "--json",
        ]) == 0
        captured = capsys.readouterr()
        assert json.loads(captured.out) == result and captured.err == ""
    assert archive.read_bytes() == before


def test_reverse_selector_errors_tampering_and_verified_handoff(
    delivery, tmp_path, monkeypatch, capsys,
):
    workflow, archive, _, binding = delivery
    fact_id = binding["fact_id"]
    with pytest.raises(trace.TraceError, match="FACT_NOT_REFERENCED"):
        trace.trace_fact(workflow, "absent-fact")
    with pytest.raises(trace.TraceError, match="SESSION_PACKAGE_REQUIRED"):
        trace.trace_fact(workflow / "review", fact_id)
    for args in (["--fact", ""], ["--fact", " "], ["--fact", fact_id, "--year", "2023"],
                 ["--fact", fact_id, "--metric", "x"], [], ["--metric", "x"]):
        assert cli.main(["research", "trace", "--archive", str(archive), *args]) == 2
        captured = capsys.readouterr()
        assert captured.out == "" and captured.err == "error: INVALID_ARGUMENTS\n"
    with zipfile.ZipFile(archive) as source:
        files = {name: source.read(name) for name in source.namelist()}
    files["index.md"] += b"\nForged outer report\n"
    forged = tmp_path / "forged.zip"
    with zipfile.ZipFile(forged, "w") as target:
        for name, raw in files.items():
            target.writestr(name, raw)
    assert cli.main([
        "research", "trace", "--archive", str(forged), "--fact", fact_id,
    ]) == 2
    captured = capsys.readouterr()
    assert captured.out == "" and captured.err == "error: VERIFY_FILE_MISMATCH\n"
    handoff = tmp_path / "handoff.zip"
    handoff.write_bytes(archive.read_bytes())
    loader = package_archive.load_verified_archive
    calls = []

    def changed_after_load(path):
        verified = loader(path)
        calls.append(path)
        path.write_bytes(b"changed")
        return verified

    monkeypatch.setattr(package_archive, "load_verified_archive", changed_after_load)
    result = trace.trace_fact(handoff, fact_id, archive=True)
    assert calls == [handoff] and result["references"]
    with pytest.raises(trace.TraceError, match="ARCHIVE_INVALID"):
        trace.trace_fact(handoff, fact_id, archive=True)
