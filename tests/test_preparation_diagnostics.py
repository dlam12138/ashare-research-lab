"""Public diagnostic projection with unchanged source verification and quality gates."""

import copy
import json
import socket
from pathlib import Path

import duckdb

from ashare_research import cli
from ashare_research.mechanism import execution, pipeline
from ashare_research.mechanism.model_digest import canonical_digest
from ashare_research.tools import (
    preparation_diagnostics as diagnostics,
)
from ashare_research.tools import research_plan_archive, research_plan_package, synthetic_prepare

EXAMPLES = Path(__file__).resolve().parents[1] / "docs/examples"


def _sources(tmp_path):
    package, archive, inputs = tmp_path / "package", tmp_path / "plan.zip", tmp_path / "inputs.json"
    research_plan_package.export_package(EXAMPLES / "m4_hypothesis.json", package)
    research_plan_archive.export_archive(EXAMPLES / "m4_hypothesis.json", archive)
    inputs.write_bytes((EXAMPLES / "m4_bound_inputs.json").read_bytes())
    return package, archive, inputs


def _write_invented(document, inputs):
    bindings = {binding["role"]: binding for binding in document["bindings"]}
    for row in document["observations"]:
        payload = {key: value for key, value in row.items() if key != "evidence_digest"}
        row["evidence_digest"] = canonical_digest({**payload, "binding": bindings[row["role"]]})
    order = {binding["role"]: index for index, binding in enumerate(document["bindings"])}
    payload = {key: value for key, value in document.items() if key != "input_digest"}
    payload["observations"] = sorted(
        document["observations"], key=lambda row: (row["trade_date"], order[row["role"]]),
    )
    document["input_digest"] = canonical_digest(payload)
    inputs.write_text(json.dumps(document), encoding="utf-8")


def test_ready_summary_exact_identities_single_preparation_and_offline(
    tmp_path, monkeypatch, capsys,
):
    package, archive, inputs = _sources(tmp_path)
    expected = synthetic_prepare.build_report(package, inputs)
    snapshot = {path: path.read_bytes() for path in (archive, inputs, *package.iterdir())}
    original_build = synthetic_prepare.build_report
    calls = []

    def counted(*args, **kwargs):
        calls.append(args)
        return original_build(*args, **kwargs)

    def forbidden(*args, **kwargs):
        raise AssertionError("No database, service, network or statistical execution")

    for name in ("load_config", "setup_logging", "_create_service"):
        monkeypatch.setattr(cli, name, forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(duckdb, "connect", forbidden)
    monkeypatch.setattr(pipeline, "run_synthetic_pipeline", forbidden)
    monkeypatch.setattr(execution, "execute_bounded_analysis", forbidden)
    monkeypatch.setattr(synthetic_prepare, "build_report", counted)
    args = ["research", "prepare", "--package", str(package), "--inputs", str(inputs)]
    assert cli.main([*args, "--summary", "--json"]) == 0
    captured = capsys.readouterr()
    report = json.loads(captured.out)
    assert captured.err == "" and len(calls) == 1
    assert report["schema"] == diagnostics.SCHEMA and report["status"] == "READY_SYNTHETIC"
    assert report["quality"] == expected["dataset"]["quality"]
    assert report["plan_identity"] == expected["plan_identity"]
    assert report["input_file_sha256"] == expected["input_file_sha256"]
    assert report["dataset_identity"]["dataset_digest"] == expected["dataset"]["dataset_digest"]
    assert report["matrix_identity"] == {
        "matrix_digest": expected["matrix"]["matrix_digest"], "row_count": 4, "column_count": 5,
    }
    assert report["boundary"] == expected["boundary"]
    assert report["selection"]["shown_dates"] == 4 and report["selection"]["shown_cells"] == 16
    assert report["selection"]["role_order"] == expected["dataset"]["role_order"]
    for item in report["role_diagnostics"]:
        assert item["audited_dates"] == item["valid_cells"] == 4
        assert item["invalid_cells"] == 0 and item["reason_counts"] == {}
    for row, original in zip(report["rows"], expected["dataset"]["audit_rows"], strict=True):
        assert row["trade_date"] == original["trade_date"] and row["globally_valid"]
        for cell, full in zip(row["cells"], original["cells"], strict=True):
            assert cell == {key: full[key] for key in diagnostics.CELL_FIELDS}
            assert "value" not in cell
    assert cli.main([*args, "--summary"]) == 0
    assert capsys.readouterr().out == diagnostics.render_markdown(report)
    assert cli.main(["research", "prepare", "--archive", str(archive), "--inputs", str(inputs),
                     "--summary", "--json"]) == 0
    assert json.loads(capsys.readouterr().out) == report
    assert cli.main(args + ["--json"]) == 0
    assert json.loads(capsys.readouterr().out) == expected
    assert {path: path.read_bytes() for path in snapshot} == snapshot


def test_role_gaps_quality_denominator_and_known_empty_preserved(tmp_path, capsys):
    package, archive, inputs = _sources(tmp_path)
    document = json.loads(inputs.read_bytes())
    # Two original quality reasons on one cell remain two diagnostic occurrences.
    document["observations"][0]["value"] = None
    document["observations"][0]["available_on"] = None
    _write_invented(document, inputs)
    original = synthetic_prepare.build_report(package, inputs)
    preserved = copy.deepcopy(original)
    args = ["research", "prepare", "--archive", str(archive), "--inputs", str(inputs),
            "--summary", "--role", "FACTOR", "--role", "TARGET_OUTCOME",
            "--role", "FACTOR", "--gaps-only", "--json"]
    assert cli.main(args) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["status"] == "REJECTED_QUALITY" and report["matrix_identity"] is None
    assert report["quality"] == original["dataset"]["quality"]
    assert report["quality"]["coverage_numerator"] == 3
    assert report["quality"]["coverage_denominator"] == 4
    assert report["quality"]["reason_counts"] == {"MISSING_VALUE": 1, "PIT_UNPROVEN": 1}
    assert report["quality"]["rejected_dates"] == ["2020-01-02"]
    assert report["selection"]["role_order"] == ["TARGET_OUTCOME", "FACTOR"]
    assert report["selection"]["shown_dates"] == report["selection"]["shown_cells"] == 1
    assert report["role_diagnostics"] == [
        {"role": "TARGET_OUTCOME", "audited_dates": 4, "valid_cells": 3, "invalid_cells": 1,
         "reason_counts": {"MISSING_VALUE": 1, "PIT_UNPROVEN": 1}},
        {"role": "FACTOR", "audited_dates": 4, "valid_cells": 4, "invalid_cells": 0,
         "reason_counts": {}},
    ]
    cell = report["rows"][0]["cells"][0]
    expected_cell = original["dataset"]["audit_rows"][0]["cells"][0]
    assert cell == {key: expected_cell[key] for key in diagnostics.CELL_FIELDS}
    assert not report["rows"][0]["globally_valid"]
    assert report["boundary"] == original["boundary"]
    assert diagnostics.build_summary(original, roles=["FACTOR"], gaps_only=True)["selection"] == {
        "role_order": ["FACTOR"], "gaps_only": True, "status": "NO_MATCHING_GAPS",
        "shown_dates": 0, "shown_cells": 0,
    }
    empty_focus = diagnostics.build_summary(original, roles=["FACTOR"], gaps_only=True)
    assert empty_focus["quality"] == original["dataset"]["quality"]
    assert "没有匹配的缺口" in diagnostics.render_markdown(empty_focus)
    assert empty_focus["status"] == "REJECTED_QUALITY"
    document["observations"] = []
    _write_invented(document, inputs)
    assert cli.main(args) == 0
    empty = json.loads(capsys.readouterr().out)
    assert empty["quality"]["coverage_numerator"] == 0
    assert empty["quality"]["coverage_denominator"] == 4
    assert empty["quality"]["reason_counts"] == {"MISSING_OBSERVATION": 16}
    assert empty["selection"]["shown_cells"] == 8 and len(empty["rows"]) == 4
    assert not any(empty["boundary"].values())
    assert original == preserved
    # Renderer treats original source metadata as text, never Markdown syntax.
    malicious = copy.deepcopy(report)
    malicious["rows"][0]["cells"][0]["source_record_id"] = "[link](url)*|\n`"
    markdown = diagnostics.render_markdown(malicious)
    assert r"\[link\]\(url\)\*\| \`" in markdown


def test_invalid_selectors_before_reads_and_corruption_rejected(tmp_path, monkeypatch, capsys):
    package, archive, inputs = _sources(tmp_path)
    args = ["research", "prepare", "--package", str(package), "--inputs", str(inputs), "--json"]

    def rejected(options, code):
        assert cli.main([*args, *options]) == 2
        captured = capsys.readouterr()
        assert captured.out == "" and captured.err == f"error: {code}\n"

    with monkeypatch.context() as scoped:
        scoped.setattr(synthetic_prepare, "build_report", lambda *a, **k: (
            (_ for _ in ()).throw(AssertionError("Invalid options must reject before IO"))
        ))
        rejected(["--role", "FACTOR"], "INVALID_ARGUMENTS")
        rejected(["--gaps-only"], "INVALID_ARGUMENTS")
        rejected(["--summary", "--role", ""], "INVALID_ROLE")
        rejected(["--summary", "--role", "factor"], "INVALID_ROLE")
        rejected(["--summary", "--role", "CONTROL_001"], "INVALID_ROLE")
        rejected(["--summary", "--execute"], "INVALID_ARGUMENTS")
    rejected(["--summary", "--role", "CONTROL_9999"], "UNKNOWN_ROLE")
    saved = inputs.read_bytes()
    document = json.loads(saved)
    document["observations"][0]["value"] = "0.123"  # deliberately stale row evidence
    inputs.write_text(json.dumps(document), encoding="utf-8")
    rejected(["--summary", "--gaps-only"], "EVIDENCE_DIGEST_MISMATCH")
    inputs.write_bytes(saved)
    plan_file = package / "plan.json"
    saved_plan = plan_file.read_bytes()
    plan_file.write_bytes(b"{}")
    rejected(["--summary"], "PLAN_PACKAGE_MISMATCH")
    assert plan_file.read_bytes() == b"{}"
    plan_file.write_bytes(saved_plan)
    assert cli.main(["research", "prepare", "--archive", str(archive), "--inputs", str(inputs),
                     "--summary", "--role", "FACTOR", "--gaps-only", "--json"]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["selection"]["status"] == "NO_MATCHING_GAPS"
    assert report["status"] == "READY_SYNTHETIC"
