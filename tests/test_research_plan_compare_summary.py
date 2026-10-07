"""Section summaries over captured, fully verified compile-only plan comparisons."""

import copy
import json
import socket
import subprocess
from contextlib import contextmanager
from pathlib import Path

import duckdb
import pytest
from test_research_plan_compare import EXAMPLE, _prepare

from ashare_research import cli
from ashare_research.mechanism import execution, pipeline
from ashare_research.tools import research_plan_archive, research_plan_package
from ashare_research.tools import research_plan_compare as compare

IDENTITY_FIELDS = ("hypothesis_id", "source_file_sha256", "config_digest",
                   "contract_digest", "plan_digest")


def _changed_pair(tmp_path):
    _, left, left_zip, _ = _prepare(tmp_path)
    changed = json.loads(EXAMPLE.read_bytes())
    changed["condition"]["threshold"] = "-0.02"
    changed["controls"].pop()
    _, right, right_zip, _ = _prepare(tmp_path, changed, stem="changed")
    return left, left_zip, right, right_zip


def _args(left, right, *, left_archive=False, right_archive=False):
    return ["research", "plan-compare",
            "--left-archive" if left_archive else "--left", str(left),
            "--right-archive" if right_archive else "--right", str(right)]


def test_summary_exact_projection_and_legacy_outputs_unchanged(tmp_path, capsys):
    left, _, right, right_zip = _changed_pair(tmp_path)
    report = compare.build_comparison(left, right_zip, right_archive=True)
    summary = compare.build_summary(report, sections=["plan", "config", "config"])
    selected = ["config", "plan"]
    assert summary["schema"] == compare.SUMMARY_SCHEMA
    assert summary["source_schema"] == report["schema"] == compare.SCHEMA
    assert summary["status"] == report["status"] == "verified_pre_execution_comparison"
    assert summary["left"] == report["left"] and summary["right"] == report["right"]
    assert summary["equality"] == report["equality"]
    assert summary["canonical_content_equal"] is False
    assert summary["change_count"] == report["change_count"] == len(report["changes"])
    assert summary["section_change_counts"] == report["section_change_counts"]
    assert all(count > 0 for count in summary["section_change_counts"].values())
    assert summary["boundary"] == report["boundary"]
    assert not any(summary["boundary"].values())
    assert summary["changes"] == [
        row for row in report["changes"] if row["section"] in selected
    ]
    assert 0 < len(summary["changes"]) < report["change_count"]
    assert summary["selection"] == {
        "section_order": selected, "status": "MATCHED",
        "shown_changes": len(summary["changes"]),
    }
    assert summary["notes"][: len(report["notes"])] == list(report["notes"])
    assert len(summary["notes"]) == len(report["notes"]) + 2
    serialized = compare._json(summary)
    assert '"execution_authorized": false' in serialized
    assert '"statistics_computed": false' in serialized

    args = _args(left, right_zip, right_archive=True)
    assert cli.main([*args, "--json"]) == 0
    legacy = capsys.readouterr()
    assert legacy.err == "" and json.loads(legacy.out) == report
    assert cli.main(args) == 0
    assert capsys.readouterr().out == compare.render_markdown(report)
    custom = [*args, "--summary", "--section", "plan", "--section", "config",
              "--section", "config"]
    assert cli.main([*custom, "--json"]) == 0
    captured = capsys.readouterr()
    assert captured.err == "" and json.loads(captured.out) == summary
    assert captured.out == compare._json(summary) + "\n"
    assert cli.main(custom) == 0
    markdown = capsys.readouterr().out
    assert markdown == compare.render_summary_markdown(summary)
    for section in compare.SECTIONS:
        assert f"| {section} | {report['section_change_counts'][section]} |" in markdown
    assert "JSON Pointer" in markdown and "执行边界" in markdown


def test_summary_all_transports_reorder_and_no_matching_changes(tmp_path):
    left, left_zip, right, right_zip = _changed_pair(tmp_path)
    expected = compare.build_summary(compare.build_comparison(left, right), sections=[])
    assert expected["selection"] == {
        "section_order": list(compare.SECTIONS), "status": "MATCHED",
        "shown_changes": expected["change_count"],
    }
    for before, after, left_archive, right_archive in (
        (left, right, False, False), (left, right_zip, False, True),
        (left_zip, right, True, False), (left_zip, right_zip, True, True),
    ):
        report = compare.build_comparison(
            before, after, left_archive=left_archive, right_archive=right_archive,
        )
        assert compare.build_summary(report, sections=[]) == expected
    reordered = compare.build_summary(
        compare.build_comparison(left, right), sections=["plan", "config"],
    )
    assert reordered["selection"]["section_order"] == ["config", "plan"]
    assert reordered["section_change_counts"] == expected["section_change_counts"]
    format_input = tmp_path / "format.json"
    document = json.loads((tmp_path / "source.json").read_bytes())
    format_input.write_text(json.dumps(document, sort_keys=True, indent=1), encoding="utf-8")
    format_zip = tmp_path / "format.zip"
    research_plan_archive.export_archive(format_input, format_zip)
    equal = compare.build_comparison(left, format_zip, right_archive=True)
    assert equal["canonical_content_equal"] and equal["change_count"] == 0
    assert equal["equality"]["source_file_sha256"] is False
    assert equal["equality"]["plan_digest"] is True
    clear = compare.build_summary(equal, sections=["plan"])
    assert clear["selection"] == {
        "section_order": ["plan"], "status": "NO_MATCHING_CHANGES", "shown_changes": 0,
    }
    assert clear["changes"] == []
    assert clear["section_change_counts"] == dict.fromkeys(compare.SECTIONS, 0)
    assert clear["equality"] == equal["equality"] and clear["boundary"] == equal["boundary"]


def test_summary_uses_captured_snapshot_without_extra_verification(
    tmp_path, monkeypatch, capsys,
):
    left, _, right, _ = _changed_pair(tmp_path)
    payloads = {directory / "hypothesis.json": (directory / "hypothesis.json").read_bytes()
                for directory in (left, right)}
    original_verify = research_plan_package.verify_package
    calls = []

    def counted(directory):
        calls.append(Path(directory))
        return original_verify(directory)

    monkeypatch.setattr(research_plan_package, "verify_package", counted)
    args = [*_args(left, right), "--summary", "--section", "config", "--json"]
    assert cli.main(args) == 0
    captured = capsys.readouterr()
    summary = json.loads(captured.out)
    assert captured.err == "" and calls == [left, right]
    assert summary["selection"]["section_order"] == ["config"]
    assert summary["changes"] == [row for row in compare.build_comparison(
        left, right)["changes"] if row["section"] == "config"]
    original_open = Path.open

    @contextmanager
    def mutate_after_read(path, mode="r", *rest, **kwargs):
        with original_open(path, mode, *rest, **kwargs) as stream:
            yield stream
        if mode == "rb" and path in payloads:
            with original_open(path, "wb") as target:
                target.write(b"mutated after captured read")

    calls.clear()
    with monkeypatch.context() as scoped:
        scoped.setattr(Path, "open", mutate_after_read)
        assert cli.main(args) == 0
        captured = capsys.readouterr()
    assert captured.err == "" and json.loads(captured.out) == summary
    assert calls == [left, right]
    for path, payload in payloads.items():
        path.write_bytes(payload)


def test_invalid_sections_and_flags_reject_before_io(tmp_path, monkeypatch, capsys):
    left, _, right, right_zip = _changed_pair(tmp_path)
    args = _args(left, right)

    def forbidden(*arguments, **kwargs):
        raise AssertionError("Invalid options must reject before any IO")

    with monkeypatch.context() as scoped:
        scoped.setattr(compare, "build_comparison", forbidden)
        scoped.setattr(research_plan_package, "verify_package", forbidden)
        scoped.setattr(research_plan_archive, "verify_archive", forbidden)
        for custom, code in (
            ([*args, "--section", "config", "--json"], "INVALID_ARGUMENTS"),
            ([*args, "--summary", "--section", "Config", "--json"], "INVALID_SECTION"),
            ([*args, "--summary", "--section", "", "--json"], "INVALID_SECTION"),
            ([*args, "--summary", "--section", "requirements", "--json"],
             "INVALID_SECTION"),
            ([*args, "--summary", "--section", "plan", "--execute", "--json"],
             "INVALID_ARGUMENTS"),
            ([*args, "--summary", "--gaps-only", "--json"], "INVALID_ARGUMENTS"),
            ([*args, "--summary", "--section", "plan", "--left-archive", str(right_zip),
              "--json"], "INVALID_ARGUMENTS"),
        ):
            assert cli.main(custom) == 2
            captured = capsys.readouterr()
            assert captured.out == "" and captured.err == f"error: {code}\n"


def test_summary_invariants_and_cli_failure_stay_sanitized(tmp_path, monkeypatch, capsys):
    left, _, right, _ = _changed_pair(tmp_path)
    report = compare.build_comparison(left, right)

    def mismatch(document):
        with pytest.raises(compare.CompareError) as error:
            compare.build_summary(document, sections=[])
        assert error.value.code == "COMPARISON_SUMMARY_MISMATCH"
        return document

    doctored_counts = copy.deepcopy(report)
    doctored_counts["section_change_counts"]["config"] += 1
    mismatch(doctored_counts)
    doctored_total = copy.deepcopy(report)
    doctored_total["change_count"] += 1
    mismatch(doctored_total)
    doctored_equality = copy.deepcopy(report)
    doctored_equality["canonical_content_equal"] = True
    mismatch(doctored_equality)
    doctored_section = copy.deepcopy(report)
    doctored_section["changes"][0]["section"] = "requirements"
    mismatch(doctored_section)
    doctored_flag = copy.deepcopy(report)
    doctored_flag["equality"]["plan_digest"] = "yes"
    mismatch(doctored_flag)
    doctored_side = copy.deepcopy(report)
    doctored_side["right"].pop("config_digest")
    mismatch(doctored_side)
    doctored_rows = copy.deepcopy(report)
    doctored_rows["changes"] = doctored_rows["changes"][:-1]
    mismatch(doctored_rows)

    with monkeypatch.context() as scoped:
        scoped.setattr(compare, "build_comparison", lambda *arguments, **kwargs:
                       doctored_counts)
        assert cli.main([*_args(left, right), "--summary", "--json"]) == 2
        captured = capsys.readouterr()
        assert captured.out == ""
        assert captured.err == "error: COMPARISON_SUMMARY_MISMATCH\n"


def test_summary_stays_offline_no_write_and_links_rejected(tmp_path, monkeypatch, capsys):
    left, _, right, right_zip = _changed_pair(tmp_path)
    snapshot = {path: path.read_bytes() for path in (*left.iterdir(), *right.iterdir())}
    snapshot[right_zip] = right_zip.read_bytes()

    def forbidden(*arguments, **kwargs):
        raise AssertionError("Summary must stay offline and read-only")

    for name in ("load_config", "setup_logging", "_create_service"):
        monkeypatch.setattr(cli, name, forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(duckdb, "connect", forbidden)
    monkeypatch.setattr(pipeline, "run_synthetic_pipeline", forbidden)
    monkeypatch.setattr(execution, "execute_bounded_analysis", forbidden)
    with monkeypatch.context() as scoped:
        scoped.setattr(Path, "mkdir", forbidden)
        args = [*_args(left, right_zip, right_archive=True), "--summary",
                "--section", "config", "--json"]
        assert cli.main(args) == 0
        captured = capsys.readouterr()
    assert captured.err == ""
    summary = json.loads(captured.out)
    assert summary["selection"]["section_order"] == ["config"]
    assert summary["selection"]["shown_changes"] > 0
    assert {path: path.read_bytes() for path in snapshot} == snapshot
    linked = tmp_path / "junction"
    created = subprocess.run(
        ["cmd", "/c", "mklink", "/J", str(linked), str(left)], capture_output=True,
    )
    assert created.returncode == 0, created.stderr
    assert cli.main([*_args(linked, right), "--summary", "--json"]) == 2
    captured = capsys.readouterr()
    assert captured.out == "" and captured.err == "error: LINKED_PACKAGE_PATH\n"
    assert {path: path.read_bytes() for path in snapshot} == snapshot
