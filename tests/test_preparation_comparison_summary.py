"""Role-transition summaries over captured, fully verified preparation comparisons."""

import copy
import hashlib
import json
import socket
import subprocess
import zipfile
from contextlib import contextmanager
from pathlib import Path

import duckdb
import pytest
from test_preparation_delivery_compare import _args as delivery_args
from test_preparation_delivery_compare import _pair
from test_preparation_diagnostics import _sources, _write_invented

from ashare_research import cli
from ashare_research.mechanism import execution, pipeline
from ashare_research.tools import preparation_archive as archive
from ashare_research.tools import preparation_compare as compare
from ashare_research.tools import preparation_delivery_compare as delivery
from ashare_research.tools import preparation_package as package
from ashare_research.tools import synthetic_prepare as prepare
from ashare_research.tools.synthetic_prepare import PrepareError

FULL_ROLE_ORDER = ["TARGET_OUTCOME", "FACTOR", "CONTROL_0001", "CONTROL_0002"]


def _rejected_right(tmp_path):
    """A plan plus before/after inputs where only one target cell turns valid."""
    plan, plan_archive, right = _sources(tmp_path)
    left = tmp_path / "before.json"
    document = json.loads(right.read_bytes())
    document["observations"][0]["value"] = None
    document["observations"][0]["available_on"] = None
    _write_invented(document, left)
    return plan, plan_archive, left, right


def _raw_args(plan, left, right):
    return ["research", "prepare-compare", "--package", str(plan),
            "--left-inputs", str(left), "--right-inputs", str(right)]


def test_summary_exact_projection_and_legacy_outputs_unchanged(tmp_path, capsys):
    plan, _, left, right = _rejected_right(tmp_path)
    report = compare.build_report(plan, left, right)
    summary = compare.build_summary(
        report, roles=["FACTOR", "TARGET_OUTCOME", "FACTOR"],
    )
    selected = ["TARGET_OUTCOME", "FACTOR"]
    assert summary["schema"] == compare.SUMMARY_SCHEMA
    assert summary["source_schema"] == report["schema"] == compare.SCHEMA
    assert summary["status"] == report["status"] == "compared_synthetic_diagnostics"
    assert summary["classification"] == "SYNTHETIC_INPUTS_CHANGED"
    assert summary["same_verified_plan"] and summary["same_declared_domain"]
    assert summary["same_input_bytes"] is False and summary["same_bound_input_digest"] is False
    assert summary["counts"] == report["counts"] == {
        "compared_cells": 16, "unchanged_cells": 15, "became_valid_cells": 1,
        "became_invalid_cells": 0, "metadata_changed_cells": 0,
    }
    assert summary["boundary"] == report["boundary"]
    assert summary["boundary"]["research_ready"] is False
    assert summary["changes"] == [
        change for change in report["changes"] if change["role"] in selected
    ]
    assert [change["transition"] for change in summary["changes"]] == ["BECAME_VALID"]
    assert summary["selection"] == {
        "role_order": selected, "status": "MATCHED", "shown_changes": 1,
    }
    assert [item["role"] for item in summary["role_summary"]] == selected
    assert summary["role_summary"][0] == {
        "role": "TARGET_OUTCOME", "audited_dates": 4, "before_valid_cells": 3,
        "before_invalid_cells": 1, "after_valid_cells": 4, "after_invalid_cells": 0,
        "unchanged": 3, "became_valid": 1, "became_invalid": 0, "metadata_changed": 0,
    }
    assert summary["role_summary"][1]["role"] == "FACTOR"
    assert summary["role_summary"][1]["unchanged"] == 4
    assert summary["role_summary"][1]["became_valid"] == 0
    for side in ("before", "after"):
        assert summary[side] == {
            "status": report[side]["status"],
            "quality": report[side]["quality"],
            "identity": {
                "plan_identity": report[side]["plan_identity"],
                "input_file_sha256": report[side]["input_file_sha256"],
                "dataset_identity": report[side]["dataset_identity"],
                "matrix_identity": report[side]["matrix_identity"],
            },
        }
    assert summary["before"]["status"] == "REJECTED_QUALITY"
    assert summary["before"]["quality"]["coverage_numerator"] == 3
    assert summary["before"]["identity"]["matrix_identity"] is None
    assert summary["after"]["status"] == "READY_SYNTHETIC"
    assert summary["after"]["quality"]["coverage_numerator"] == 4
    assert summary["after"]["identity"]["matrix_identity"] is not None
    assert summary["notes"][: len(report["notes"])] == list(report["notes"])
    assert len(summary["notes"]) == len(report["notes"]) + 2
    serialized = compare._json(summary)
    assert '"value":' not in serialized and '"observations"' not in serialized
    assert '"audit_rows"' not in serialized

    args = _raw_args(plan, left, right)
    assert cli.main([*args, "--json"]) == 0
    legacy = capsys.readouterr()
    assert legacy.err == "" and json.loads(legacy.out) == report
    assert cli.main(args) == 0
    assert capsys.readouterr().out == compare.render_markdown(report)
    custom = [*args, "--summary", "--role", "FACTOR", "--role", "TARGET_OUTCOME",
              "--role", "FACTOR"]
    assert cli.main([*custom, "--json"]) == 0
    captured = capsys.readouterr()
    assert captured.err == "" and json.loads(captured.out) == summary
    assert cli.main(custom) == 0
    markdown = capsys.readouterr().out
    assert markdown == compare.render_summary_markdown(summary)
    assert "| TARGET_OUTCOME |" in markdown and "| CONTROL_0001 |" not in markdown
    assert "--left-inputs 为修改前；--right-inputs 为修改后。" in markdown


def test_delivery_summary_all_transports_and_compact_markdown(tmp_path, capsys):
    plan, left_input, right_input, left, right, left_zip, right_zip = _pair(tmp_path)
    expected = delivery.build_report(left, right)
    full = compare.build_summary(expected, roles=[])
    assert full["selection"] == {
        "role_order": FULL_ROLE_ORDER, "status": "MATCHED", "shown_changes": 1,
    }
    assert full["before"]["status"] == "REJECTED_QUALITY"
    assert full["after"]["status"] == "READY_SYNTHETIC"
    for before, after, left_archive, right_archive in (
        (left, right, False, False), (left, right_zip, False, True),
        (left_zip, right, True, False), (left_zip, right_zip, True, True),
    ):
        base = delivery_args(before, after, left_archive=left_archive,
                             right_archive=right_archive)
        markdown_args = [*base[:-1], "--summary"]
        assert cli.main([*markdown_args, "--json"]) == 0
        captured = capsys.readouterr()
        assert captured.err == "" and json.loads(captured.out) == full
        assert captured.out == compare._json(full) + "\n"
        assert cli.main(markdown_args) == 0
        markdown = capsys.readouterr().out
        assert markdown == delivery.render_summary_markdown(full)
        assert "left 为修改前的准备交付包" in markdown
        assert "--left-inputs" not in markdown
    filtered = compare.build_summary(expected, roles=["TARGET_OUTCOME"])
    assert cli.main([*delivery_args(left, right), "--summary", "--role",
                     "TARGET_OUTCOME", "--json"]) == 0
    assert json.loads(capsys.readouterr().out) == filtered
    assert cli.main(delivery_args(left, right)[:-1]) == 0
    assert capsys.readouterr().out == delivery.render_markdown(expected)


def test_role_filter_order_dedupe_global_counts_and_no_matching_changes(tmp_path, capsys):
    plan, _, left, right = _rejected_right(tmp_path)
    report = compare.build_report(plan, left, right)
    everything = compare.build_summary(report, roles=[])
    assert everything["selection"]["role_order"] == FULL_ROLE_ORDER
    assert everything["selection"]["shown_changes"] == 1
    assert [item["role"] for item in everything["role_summary"]] == FULL_ROLE_ORDER
    reordered = compare.build_summary(report, roles=["CONTROL_0002", "TARGET_OUTCOME"])
    assert reordered["selection"]["role_order"] == ["TARGET_OUTCOME", "CONTROL_0002"]
    assert [item["role"] for item in reordered["role_summary"]] == [
        "TARGET_OUTCOME", "CONTROL_0002"]
    assert reordered["counts"] == everything["counts"] == report["counts"]
    assert len(reordered["changes"]) == 1
    clear = compare.build_summary(report, roles=["FACTOR", "CONTROL_0001"])
    assert clear["selection"] == {
        "role_order": ["FACTOR", "CONTROL_0001"], "status": "NO_MATCHING_CHANGES",
        "shown_changes": 0,
    }
    assert clear["changes"] == [] and clear["counts"] == report["counts"]
    assert clear["before"]["status"] == report["before"]["status"] == "REJECTED_QUALITY"
    assert clear["after"]["status"] == report["after"]["status"] == "READY_SYNTHETIC"
    assert clear["before"]["quality"] == report["before"]["quality"]
    assert clear["after"]["quality"] == report["after"]["quality"]
    assert [item["unchanged"] for item in clear["role_summary"]] == [4, 4]
    args = [*_raw_args(plan, left, right), "--summary", "--role", "FACTOR",
            "--role", "CONTROL_0001", "--json"]
    assert cli.main(args) == 0
    captured = capsys.readouterr()
    assert captured.err == "" and json.loads(captured.out) == clear


def test_summary_uses_captured_snapshot_without_extra_reads(tmp_path, monkeypatch, capsys):
    plan, _, left, right = _rejected_right(tmp_path)
    left_raw, right_raw = left.read_bytes(), right.read_bytes()
    original_build = prepare.build_report
    calls = []

    def counted(*arguments, **kwargs):
        calls.append(arguments)
        return original_build(*arguments, **kwargs)

    monkeypatch.setattr(prepare, "build_report", counted)
    args = [*_raw_args(plan, left, right), "--summary", "--role", "TARGET_OUTCOME"]
    assert cli.main([*args, "--json"]) == 0
    captured = capsys.readouterr()
    summary = json.loads(captured.out)
    assert captured.err == "" and len(calls) == 2
    assert calls[0][1] == left and calls[1][1] == right
    assert summary["selection"]["role_order"] == ["TARGET_OUTCOME"]
    assert [change["transition"] for change in summary["changes"]] == ["BECAME_VALID"]
    calls.clear()
    same = [*_raw_args(plan, left, left), "--summary", "--json"]
    assert cli.main(same) == 0
    same_summary = json.loads(capsys.readouterr().out)
    assert len(calls) == 1 and same_summary["changes"] == []
    assert same_summary["counts"]["unchanged_cells"] == 16
    original_open = Path.open

    @contextmanager
    def mutate_after_read(path, mode="r", *rest, **kwargs):
        with original_open(path, mode, *rest, **kwargs) as stream:
            yield stream
        if mode == "rb" and path in (left, right):
            with original_open(path, "wb") as target:
                target.write(b"mutated after captured read")

    with monkeypatch.context() as scoped:
        scoped.setattr(Path, "open", mutate_after_read)
        assert cli.main([*args, "--json"]) == 0
        captured = capsys.readouterr()
    assert captured.err == "" and json.loads(captured.out) == summary
    left.write_bytes(left_raw)
    right.write_bytes(right_raw)


def test_once_verified_delivery_pair_projects_without_rereads(tmp_path, monkeypatch):
    _, _, _, left, right, left_zip, right_zip = _pair(tmp_path)
    expected = compare.build_summary(delivery.build_report(left, right), roles=[])
    files = {path: path.read_bytes() for path in (*right.iterdir(), right_zip)}
    hashes = {path: hashlib.sha256(raw).hexdigest() for path, raw in files.items()}
    original_open = Path.open
    reads = []

    @contextmanager
    def counted(path, mode="r", *rest, **kwargs):
        with original_open(path, mode, *rest, **kwargs) as stream:
            yield stream
        if mode == "rb":
            reads.append(path)

    with monkeypatch.context() as scoped:
        scoped.setattr(Path, "open", counted)
        summary = compare.build_summary(
            delivery.build_report(left, right_zip, right_archive=True), roles=[],
        )
        assert summary == expected
        assert len(reads) == 11 and set(reads) == {*left.iterdir(), right_zip}
        reads.clear()
        summary = compare.build_summary(
            delivery.build_report(right, right), roles=["TARGET_OUTCOME"],
        )
        assert len(reads) == 10 and set(reads) == set(right.iterdir())
    assert summary["selection"]["role_order"] == ["TARGET_OUTCOME"]
    assert summary["selection"]["status"] == "NO_MATCHING_CHANGES"
    assert summary["changes"] == []
    assert summary["counts"]["unchanged_cells"] == 16
    assert {path: hashlib.sha256(path.read_bytes()).hexdigest()
            for path in files} == hashes


def test_unknown_role_after_complete_comparison_and_invalid_options_before_io(
    tmp_path, monkeypatch, capsys,
):
    plan, _, left, right = _rejected_right(tmp_path)
    args = _raw_args(plan, left, right)
    original_build = prepare.build_report
    calls = []

    def counted(*arguments, **kwargs):
        calls.append(arguments)
        return original_build(*arguments, **kwargs)

    monkeypatch.setattr(prepare, "build_report", counted)
    assert cli.main([*args, "--summary", "--role", "CONTROL_9999", "--json"]) == 2
    captured = capsys.readouterr()
    assert captured.out == "" and captured.err == "error: UNKNOWN_ROLE\n"
    assert len(calls) == 2
    calls.clear()

    def forbidden(*arguments, **kwargs):
        raise AssertionError("Invalid options must reject before any IO")

    with monkeypatch.context() as scoped:
        scoped.setattr(prepare, "build_report", forbidden)
        scoped.setattr(compare, "build_report", forbidden)
        for custom, code in (
            ([*args, "--role", "FACTOR"], "INVALID_ARGUMENTS"),
            ([*args, "--summary", "--role", "control_0001"], "INVALID_ROLE"),
            ([*args, "--summary", "--role", ""], "INVALID_ROLE"),
            ([*args, "--summary", "--role", "FACTOR", "--gaps-only"], "INVALID_ARGUMENTS"),
            ([*args, "--summary", "--execute"], "INVALID_ARGUMENTS"),
        ):
            assert cli.main(custom) == 2
            captured = capsys.readouterr()
            assert captured.out == "" and captured.err == f"error: {code}\n"
    assert calls == []


def test_delivery_unknown_role_after_verify_and_invalid_options_before_io(
    tmp_path, monkeypatch, capsys,
):
    _, _, _, left, right, _, _ = _pair(tmp_path)
    original_verify = package.verify_package
    calls = []

    def counted(*arguments, **kwargs):
        calls.append(arguments)
        return original_verify(*arguments, **kwargs)

    monkeypatch.setattr(package, "verify_package", counted)
    assert cli.main([*delivery_args(left, right), "--summary", "--role",
                     "CONTROL_9999"]) == 2
    captured = capsys.readouterr()
    assert captured.out == "" and captured.err == "error: UNKNOWN_ROLE\n"
    assert len(calls) == 2
    calls.clear()

    def forbidden(*arguments, **kwargs):
        raise AssertionError("Invalid options must reject before verification")

    with monkeypatch.context() as scoped:
        scoped.setattr(delivery, "build_report", forbidden)
        scoped.setattr(package, "verify_package", forbidden)
        scoped.setattr(archive, "verify_archive", forbidden)
        for custom, code in (
            ([*delivery_args(left, right), "--role", "FACTOR"], "INVALID_ARGUMENTS"),
            ([*delivery_args(left, right), "--summary", "--role", "TARGET"],
             "INVALID_ROLE"),
            ([*delivery_args(left, right), "--summary", "--gap"], "INVALID_ARGUMENTS"),
        ):
            assert cli.main(custom) == 2
            captured = capsys.readouterr()
            assert captured.out == "" and captured.err == f"error: {code}\n"
    assert calls == []


def test_summary_invariants_and_cli_failure_stay_sanitized(tmp_path, monkeypatch, capsys):
    plan, _, left, right = _rejected_right(tmp_path)
    report = compare.build_report(plan, left, right)

    def mismatch(document):
        with pytest.raises(PrepareError) as error:
            compare.build_summary(document, roles=[])
        assert error.value.code == "COMPARISON_SUMMARY_MISMATCH"
        return document

    doctored_counts = copy.deepcopy(report)
    doctored_counts["counts"]["unchanged_cells"] += 1
    mismatch(doctored_counts)
    doctored_roles = copy.deepcopy(report)
    doctored_roles["after"]["role_diagnostics"].pop()
    mismatch(doctored_roles)
    doctored_dates = copy.deepcopy(report)
    doctored_dates["after"]["role_diagnostics"][0]["audited_dates"] = 5
    mismatch(doctored_dates)
    doctored_transition = copy.deepcopy(report)
    doctored_transition["changes"][0]["transition"] = "BECAME_UNKNOWN"
    mismatch(doctored_transition)
    doctored_change_role = copy.deepcopy(report)
    doctored_change_role["changes"][0]["role"] = "CONTROL_9999"
    mismatch(doctored_change_role)
    doctored_extra_field = copy.deepcopy(report)
    doctored_extra_field["counts"]["unexpected_cells"] = 0
    mismatch(doctored_extra_field)

    with monkeypatch.context() as scoped:
        scoped.setattr(compare, "build_report", lambda *arguments, **kwargs: doctored_counts)
        assert cli.main([*_raw_args(plan, left, right), "--summary", "--json"]) == 2
        captured = capsys.readouterr()
        assert captured.out == ""
        assert captured.err == "error: COMPARISON_SUMMARY_MISMATCH\n"


def test_summary_stays_offline_no_extraction_no_write_and_links_rejected(
    tmp_path, monkeypatch, capsys,
):
    plan, _, left, right = _rejected_right(tmp_path)
    plan_files = {path: path.read_bytes() for path in plan.iterdir()}

    def forbidden(*arguments, **kwargs):
        raise AssertionError("Summary must stay offline, read-only and extract nothing")

    for name in ("load_config", "setup_logging", "_create_service"):
        monkeypatch.setattr(cli, name, forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(duckdb, "connect", forbidden)
    monkeypatch.setattr(pipeline, "run_synthetic_pipeline", forbidden)
    monkeypatch.setattr(execution, "execute_bounded_analysis", forbidden)
    args = [*_raw_args(plan, left, right), "--summary", "--role", "TARGET_OUTCOME"]
    assert cli.main([*args, "--json"]) == 0
    captured = capsys.readouterr()
    assert captured.err == "" and json.loads(captured.out)["selection"]["status"] == "MATCHED"
    assert {path: path.read_bytes() for path in plan.iterdir()} == plan_files

    case = tmp_path / "delivery"
    case.mkdir()
    _, _, _, delivery_left, delivery_right, _, _ = _pair(case)
    snapshot = {path: path.read_bytes() for path in delivery_left.iterdir()}
    with monkeypatch.context() as scoped:
        scoped.setattr(zipfile.ZipFile, "extract", forbidden)
        scoped.setattr(zipfile.ZipFile, "extractall", forbidden)
        scoped.setattr(Path, "mkdir", forbidden)
        markdown_args = [*delivery_args(delivery_left, delivery_right)[:-1], "--summary"]
        assert cli.main(markdown_args) == 0
        captured = capsys.readouterr()
        assert captured.err == "" and "角色变更速览" in captured.out
    assert {path: path.read_bytes() for path in delivery_left.iterdir()} == snapshot

    linked = tmp_path / "junction"
    created = subprocess.run(
        ["cmd", "/c", "mklink", "/J", str(linked), str(delivery_left)],
        capture_output=True,
    )
    assert created.returncode == 0, created.stderr
    assert cli.main([*delivery_args(linked, delivery_right), "--summary", "--json"]) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == "error: LINKED_PREPARATION_PACKAGE_PATH\n"
