"""Compare verified audit facts without changing the sample domain or sources."""

import json
import socket
from contextlib import contextmanager
from pathlib import Path

import duckdb
from test_preparation_diagnostics import EXAMPLES, _sources, _write_invented

from ashare_research import cli
from ashare_research.mechanism import execution, pipeline
from ashare_research.mechanism.model_digest import canonical_digest
from ashare_research.tools import (
    preparation_compare as compare,
)
from ashare_research.tools import preparation_diagnostics, research_plan, research_plan_package
from ashare_research.tools import synthetic_prepare as prepare


def test_public_quality_transition_exact_sides_reversal_and_offline(tmp_path, monkeypatch, capsys):
    package, archive, right = _sources(tmp_path)
    left = tmp_path / "before.json"
    document = json.loads(right.read_bytes())
    document["observations"][0]["value"] = None
    document["observations"][0]["available_on"] = None
    _write_invented(document, left)
    before = prepare.build_report(package, left)
    after = prepare.build_report(package, right)
    snapshot = {path: path.read_bytes() for path in (left, right, archive, *package.iterdir())}

    def forbidden(*args, **kwargs):
        raise AssertionError("No services, network, database or statistical execution")

    for name in ("load_config", "setup_logging", "_create_service"):
        monkeypatch.setattr(cli, name, forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(duckdb, "connect", forbidden)
    monkeypatch.setattr(pipeline, "run_synthetic_pipeline", forbidden)
    monkeypatch.setattr(execution, "execute_bounded_analysis", forbidden)
    args = ["research", "prepare-compare", "--package", str(package),
            "--left-inputs", str(left), "--right-inputs", str(right)]
    assert cli.main([*args, "--json"]) == 0
    captured = capsys.readouterr()
    assert captured.err == ""
    report = json.loads(captured.out)
    assert report["before"] == preparation_diagnostics.build_summary(
        before, roles=[], gaps_only=False,
    )
    assert report["after"] == preparation_diagnostics.build_summary(
        after, roles=[], gaps_only=False,
    )
    assert report["before"]["status"] == "REJECTED_QUALITY"
    assert report["after"]["status"] == "READY_SYNTHETIC"
    assert report["before"]["quality"]["coverage_numerator"] == 3
    assert report["after"]["quality"]["coverage_numerator"] == 4
    assert report["before"]["quality"]["coverage_denominator"] == 4
    assert report["after"]["quality"]["coverage_denominator"] == 4
    assert report["same_declared_domain"] and report["same_verified_plan"]
    assert report["counts"] == {
        "compared_cells": 16, "unchanged_cells": 15, "became_valid_cells": 1,
        "became_invalid_cells": 0, "metadata_changed_cells": 0,
    }
    assert report["changes"] == [{
        "trade_date": "2020-01-02", "role": "TARGET_OUTCOME", "transition": "BECAME_VALID",
        "before": report["before"]["rows"][0]["cells"][0],
        "after": report["after"]["rows"][0]["cells"][0],
    }]
    assert report["changes"][0]["before"]["reasons"] == ["MISSING_VALUE", "PIT_UNPROVEN"]
    assert report["changes"][0]["after"]["reasons"] == []
    assert report["classification"] == "SYNTHETIC_INPUTS_CHANGED"
    assert report["boundary"]["synthetic_observations_read"] and report["boundary"]["outcome_read"]
    assert not any(value for key, value in report["boundary"].items()
                   if key not in ("synthetic_observations_read", "outcome_read"))
    assert cli.main(args) == 0
    markdown = capsys.readouterr().out
    assert markdown == compare.render_markdown(report) and "3/4" in markdown
    assert cli.main(["research", "prepare-compare", "--archive", str(archive),
                     "--left-inputs", str(left), "--right-inputs", str(right), "--json"]) == 0
    assert json.loads(capsys.readouterr().out) == report
    reverse = compare.build_report(package, right, left)
    assert reverse["changes"][0]["transition"] == "BECAME_INVALID"
    assert reverse["changes"][0]["before"] == report["changes"][0]["after"]
    assert reverse["counts"]["became_invalid_cells"] == 1
    assert {path: path.read_bytes() for path in snapshot} == snapshot


def test_format_metadata_empty_and_loaded_snapshot_identity(tmp_path, monkeypatch, capsys):
    package, archive, left = _sources(tmp_path)
    right = tmp_path / "after.json"
    raw = left.read_bytes()
    document = json.loads(raw)
    # Existing input digest semantics permit observation-order changes.
    document["observations"].reverse()
    right.write_text(json.dumps(document, sort_keys=True), encoding="utf-8")
    report = compare.build_report(package, left, right)
    assert report["classification"] == "CANONICALLY_EQUIVALENT_INPUTS"
    assert report["same_bound_input_digest"] and not report["same_input_bytes"]
    assert report["changes"] == [] and report["counts"]["unchanged_cells"] == 16
    document = json.loads(raw)
    document["observations"][0]["value"] = "0.123"
    _write_invented(document, right)
    metadata = compare.build_report(package, left, right)
    assert metadata["before"]["quality"] == metadata["after"]["quality"]
    assert metadata["counts"]["metadata_changed_cells"] == 1
    assert metadata["counts"]["became_valid_cells"] == 0
    assert metadata["changes"][0]["transition"] == "DIAGNOSTIC_METADATA_CHANGED"
    assert "value" not in metadata["changes"][0]["after"]
    assert metadata["before"]["matrix_identity"]["matrix_digest"] != (
        metadata["after"]["matrix_identity"]["matrix_digest"]
    )
    document = json.loads(raw)
    document["observations"] = []
    _write_invented(document, right)
    empty = compare.build_report(package, right, right)
    assert empty["classification"] == "IDENTICAL_INPUT_BYTES"
    assert not any(empty["boundary"].values())
    assert empty["before"]["quality"]["reason_counts"] == {"MISSING_OBSERVATION": 16}
    right.write_bytes(raw)
    original_open = Path.open
    reads = []

    @contextmanager
    def loaded_then_mutated(path, mode="r", *rest, **kwargs):
        with original_open(path, mode, *rest, **kwargs) as stream:
            yield stream
        if mode == "rb" and path in (archive, left, right):
            reads.append(path)
            if path in (left, right):
                with original_open(path, "wb") as target:
                    target.write(b"mutated after read")

    with monkeypatch.context() as scoped:
        scoped.setattr(Path, "open", loaded_then_mutated)
        report = compare.build_report(archive, left, right, archive=True)
        assert reads == [archive, left, archive, right]
        assert report["classification"] == "IDENTICAL_INPUT_BYTES"
        left.write_bytes(raw)
        reads.clear()
        report = compare.build_report(archive, left, left, archive=True)
        assert reads == [archive, left]
        assert report["before"] == report["after"]
    left.write_bytes(raw)
    right.write_bytes(raw)
    args = ["research", "prepare-compare", "--package", str(package),
            "--left-inputs", str(left), "--right-inputs", str(right), "--json"]
    assert cli.main(args) == 0
    assert json.loads(capsys.readouterr().out)["changes"] == []


def test_domain_plan_drift_corruption_and_invalid_options_fail_closed(
    tmp_path, monkeypatch, capsys,
):
    package, archive, left = _sources(tmp_path)
    right = tmp_path / "right.json"
    raw = left.read_bytes()
    right.write_bytes(raw)
    args = ["research", "prepare-compare", "--package", str(package),
            "--left-inputs", str(left), "--right-inputs", str(right), "--json"]

    def rejected(code, custom=None):
        assert cli.main(args if custom is None else custom) == 2
        captured = capsys.readouterr()
        assert captured.out == "" and captured.err == f"error: {code}\n"

    changed = json.loads(raw)
    domain = changed["domain"]
    removed = domain["expected_dates"].pop(0)
    for key in ("calendar_evidence", "membership_evidence"):
        domain[key]["expected_dates"] = list(domain["expected_dates"])
        domain[key]["evidence_digest"] = canonical_digest({
            k: v for k, v in domain[key].items() if k != "evidence_digest"
        })
    changed["observations"] = [
        row for row in changed["observations"] if row["trade_date"] != removed
    ]
    _write_invented(changed, right)
    assert prepare.build_report(package, right)["dataset"]["quality"]["coverage_denominator"] == 3
    rejected("COMPARISON_DOMAIN_MISMATCH")
    right.write_bytes(raw)
    stale = json.loads(raw)
    stale["observations"][0]["value"] = "0.123"
    right.write_text(json.dumps(stale), encoding="utf-8")
    rejected("EVIDENCE_DIGEST_MISMATCH")
    right.write_bytes(b'{"x":1,"x":2}')
    rejected("DUPLICATE_INPUT_JSON_KEY")
    right.write_bytes(raw)
    plan_file = package / "plan.json"
    saved_plan = plan_file.read_bytes()
    plan_file.write_bytes(b"{}")
    rejected("PLAN_PACKAGE_MISMATCH")
    plan_file.write_bytes(saved_plan)
    original_lstat = Path.lstat

    class Reparse:
        st_mode = 0o100644
        st_file_attributes = 0x400

    with monkeypatch.context() as scoped:
        # An alias resolving to the left path must still traverse the right input's link gate.
        scoped.setattr(Path, "resolve", lambda path, **kw: left)
        scoped.setattr(Path, "lstat", lambda path, **kw: (
            Reparse() if path == right else original_lstat(path, **kw)
        ))
        rejected("LINKED_INPUT_PATH")
    with monkeypatch.context() as scoped:
        scoped.setattr(compare, "build_report", lambda *a, **k: (
            (_ for _ in ()).throw(AssertionError("Invalid flags must reject before IO"))
        ))
        for custom in ([*args, "--execute"], [*args, "--role", "FACTOR"],
                       [*args, "--archive", str(archive)], ["research", "prepare-compare"]):
            rejected("INVALID_ARGUMENTS", custom)

    # Two individually valid plans changed between reads must never be paired.
    hypothesis = json.loads((EXAMPLES / "m4_hypothesis.json").read_bytes())
    hypothesis["condition"]["threshold"] = "-0.02"
    source = tmp_path / "changed-hypothesis.json"
    source.write_text(json.dumps(hypothesis), encoding="utf-8")
    replacement = tmp_path / "replacement"
    research_plan_package.export_package(source, replacement)
    compiled = research_plan.build_report(source)
    changed = json.loads(raw)
    changed["source_contract_digest"] = compiled["contract"]["contract_digest"]
    changed["plan_digest"] = compiled["plan"]["plan_digest"]
    _write_invented(changed, right)
    original_build = prepare.build_report

    def change_plan_after_left(*arguments, **kwargs):
        report = original_build(*arguments, **kwargs)
        if arguments[1] == left:
            for file in replacement.iterdir():
                (package / file.name).write_bytes(file.read_bytes())
        return report

    with monkeypatch.context() as scoped:
        scoped.setattr(prepare, "build_report", change_plan_after_left)
        rejected("COMPARISON_PLAN_MISMATCH")
