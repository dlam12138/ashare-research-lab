"""Focused plan review summary: exact projection, single captures, fail-closed IO."""

import copy
import hashlib
import json
import socket
from contextlib import contextmanager
from pathlib import Path

import duckdb
import pytest

from ashare_research import cli
from ashare_research.mechanism import execution, pipeline
from ashare_research.tools import research_plan, research_plan_archive, research_plan_package

EXAMPLE = Path(__file__).resolve().parents[1] / "docs/examples/m4_hypothesis.json"
PACKAGE_FILES = ("hypothesis.json", "manifest.json", "plan.json", "plan.md")


def _prepare(tmp_path):
    source = tmp_path / "source.json"
    source.write_bytes(EXAMPLE.read_bytes())
    directory, archive = tmp_path / "plan-package", tmp_path / "plan.zip"
    report = research_plan.build_report(source)
    research_plan_package.export_package(source, directory)
    research_plan_archive.export_archive(source, archive)
    return source, directory, archive, report


def _run(args, capsys):
    assert cli.main(args) == 0
    captured = capsys.readouterr()
    assert captured.err == "" and captured.out
    return captured.out


def _summary(args, capsys):
    return json.loads(_run(args, capsys))


def test_exact_projection_across_transports_and_legacy_byte_equality(tmp_path, capsys):
    source, directory, archive, report = _prepare(tmp_path)
    plan = report["plan"]
    assert cli.main(["research", "plan", "--hypothesis", str(source)]) == 0
    assert capsys.readouterr().out == research_plan.render_markdown(report)
    assert cli.main(["research", "plan", "--hypothesis", str(source), "--json"]) == 0
    assert capsys.readouterr().out == research_plan._json(report) + "\n"
    assert cli.main(["research", "plan", "--verify", str(directory), "--json"]) == 0
    receipt = research_plan_package.verify_package(directory)
    assert capsys.readouterr().out == research_plan._json(receipt) + "\n"
    assert cli.main(["research", "plan", "--verify-archive", str(archive), "--json"]) == 0
    archive_receipt = research_plan_archive.verify_archive(archive)
    assert capsys.readouterr().out == research_plan._json(archive_receipt) + "\n"
    compiled = _summary(
        ["research", "plan", "--hypothesis", str(source), "--summary", "--json"], capsys,
    )
    assert compiled["schema"] == research_plan.SUMMARY_SCHEMA
    assert compiled["source_schema"] == report["schema"]
    assert compiled["status"] == report["status"] == "compiled_pre_execution"
    assert compiled["source"] == "COMPILED_ONCE"
    assert compiled["identity"] == {
        "hypothesis_id": report["contract"]["hypothesis_id"],
        "source_file_sha256": report["source_file_sha256"],
        "contract_state": report["contract"]["contract_state"],
        "plan_state": plan["plan_state"],
        "contract_digest": report["contract"]["contract_digest"],
        "plan_digest": plan["plan_digest"],
        "source_config_digest": report["contract"]["source_config_digest"],
        "source_contract_digest": plan["source_contract_digest"],
    }
    assert compiled["shape"] == {
        "requirement_roles": ["TARGET_OUTCOME", "FACTOR", "CONTROL_0001", "CONTROL_0002"],
        "ordered_term_count": 5,
        "robustness_entry_count": 1,
        "bootstrap_enabled": True,
        "holdout_authorized": False,
    }
    assert compiled["selection"] == {
        "section_order": list(research_plan.SECTIONS), "shown_sections": 9,
    }
    assert [item["section"] for item in compiled["sections"]] == list(research_plan.SECTIONS)
    payloads = {item["section"]: item["payload"] for item in compiled["sections"]}
    assert payloads == {
        "requirements": plan["dataset_requirements"],
        "sample": plan["sample_plan"],
        "condition": plan["transform_plan"],
        "method": {"analysis_method_id": plan["analysis_method_id"],
                   "design_plan": plan["design_plan"]},
        "conditional": plan["conditional_summary_plan"],
        "bootstrap": plan["bootstrap_plan"],
        "robustness": plan["robustness_plan"],
        "evidence": plan["evidence_plan"],
        "holdout": plan["holdout_boundary"],
    }
    assert compiled["boundary"] == report["boundary"]
    assert compiled["notes"] == [
        *report["notes"], research_plan.SOURCE_LEGENDS["COMPILED_ONCE"],
    ]
    directory_summary = _summary(
        ["research", "plan", "--verify", str(directory), "--summary", "--json"], capsys,
    )
    archive_summary = _summary(
        ["research", "plan", "--verify-archive", str(archive), "--summary", "--json"], capsys,
    )
    for summary, token in (
        (directory_summary, "VERIFIED_DIRECTORY_ONCE"),
        (archive_summary, "VERIFIED_ARCHIVE_ONCE"),
    ):
        assert summary["source"] == token
        assert summary["notes"] == [*report["notes"], research_plan.SOURCE_LEGENDS[token]]
        assert {**summary, "source": None, "notes": None} == {
            **compiled, "source": None, "notes": None,
        }


def test_section_selection_dedup_order_payloads_and_markdown(tmp_path, capsys):
    source, directory, _, report = _prepare(tmp_path)
    plan = report["plan"]
    full = _summary(
        ["research", "plan", "--hypothesis", str(source), "--summary", "--json"], capsys,
    )
    filtered = _summary([
        "research", "plan", "--hypothesis", str(source), "--summary",
        "--section", "holdout", "--section", "method", "--section", "holdout", "--json",
    ], capsys)
    assert filtered["selection"] == {"section_order": ["method", "holdout"], "shown_sections": 2}
    assert [item["section"] for item in filtered["sections"]] == ["method", "holdout"]
    assert filtered["sections"][0]["payload"] == {
        "analysis_method_id": plan["analysis_method_id"], "design_plan": plan["design_plan"],
    }
    assert filtered["sections"][1]["payload"] == plan["holdout_boundary"]
    for key in ("identity", "shape", "boundary", "notes", "source", "source_schema", "status"):
        assert filtered[key] == full[key]
    assert research_plan.build_summary(
        report, sections=["method", "holdout"], source="COMPILED_ONCE",
    ) == filtered
    assert cli.main(["research", "plan", "--hypothesis", str(source), "--summary"]) == 0
    markdown = capsys.readouterr().out
    assert markdown == research_plan.render_summary_markdown(full)
    assert "## holdout" in markdown and "## method" in markdown
    assert research_plan.SOURCE_LEGENDS["COMPILED_ONCE"] in markdown
    assert '"execution_authorized": false' in markdown
    assert cli.main(["research", "plan", "--verify", str(directory), "--summary"]) == 0
    verify_markdown = capsys.readouterr().out
    assert "## requirements" in verify_markdown
    assert research_plan.SOURCE_LEGENDS["VERIFIED_DIRECTORY_ONCE"] in verify_markdown
    assert research_plan.SOURCE_LEGENDS["VERIFIED_DIRECTORY_ONCE"] not in markdown


def test_invalid_selectors_and_export_modes_reject_before_io(tmp_path, capsys):
    source, directory, _, _ = _prepare(tmp_path)
    missing = tmp_path / "missing"

    def rejected(args, code):
        assert cli.main(args) == 2
        captured = capsys.readouterr()
        assert captured.out == "" and captured.err == f"error: {code}\n"

    rejected(["research", "plan", "--hypothesis", str(missing),
              "--section", "requirements"], "INVALID_ARGUMENTS")
    rejected(["research", "plan", "--hypothesis", str(missing),
              "--summary", "--section", "unknown"], "INVALID_SECTION")
    rejected(["research", "plan", "--hypothesis", str(missing),
              "--summary", "--section", ""], "INVALID_SECTION")
    rejected(["research", "plan", "--hypothesis", str(missing),
              "--summary", "--section", "METHOD"], "INVALID_SECTION")
    export = ["research", "plan", "--hypothesis", str(source)]
    rejected([*export, "--output", str(tmp_path / "new"), "--summary"], "INVALID_ARGUMENTS")
    rejected([*export, "--output", str(tmp_path / "new"),
              "--section", "sample"], "INVALID_ARGUMENTS")
    rejected([*export, "--output", str(tmp_path / "new"),
              "--summary", "--section", "unknown"], "INVALID_ARGUMENTS")
    rejected([*export, "--archive", str(tmp_path / "new.zip"), "--summary"], "INVALID_ARGUMENTS")
    rejected(["research", "plan", "--verify", str(missing),
              "--summary", "--section", "unknown"], "INVALID_SECTION")
    rejected(["research", "plan", "--verify-archive", str(missing),
              "--section", "holdout"], "INVALID_ARGUMENTS")
    rejected(["research", "plan", "--verify", str(directory),
              "--summary", "--section", "unknown"], "INVALID_SECTION")
    assert not (tmp_path / "new").exists() and not (tmp_path / "new.zip").exists()


def test_compile_summary_uses_one_snapshot(tmp_path, monkeypatch, capsys):
    source = tmp_path / "source.json"
    source.write_bytes(EXAMPLE.read_bytes())
    expected = research_plan.build_report(source)
    original_open = Path.open
    reads = []

    @contextmanager
    def mutate_after_read(path, mode="r", *rest, **kwargs):
        with original_open(path, mode, *rest, **kwargs) as stream:
            yield stream
        if mode == "rb":
            reads.append(Path(path))
            if Path(path) == source:
                with original_open(path, "wb") as stream:
                    stream.write(b"mutated after loaded snapshot")

    with monkeypatch.context() as scoped:
        scoped.setattr(Path, "open", mutate_after_read)
        summary = _summary(
            ["research", "plan", "--hypothesis", str(source), "--summary", "--json"], capsys,
        )
    assert reads == [source]
    assert summary == research_plan.build_summary(
        expected, sections=[], source="COMPILED_ONCE",
    )
    assert source.read_bytes() == b"mutated after loaded snapshot"


def test_verify_transports_read_once_and_project_captured_receipt(
    tmp_path, monkeypatch, capsys,
):
    _, directory, archive, _ = _prepare(tmp_path)
    expected_directory = research_plan_package.verify_package(directory)["report"]
    expected_archive = research_plan_archive.verify_archive(archive)["verification"]["report"]
    original_open = Path.open

    def tracker(mutate):
        reads = []

        @contextmanager
        def wrapper(path, mode="r", *rest, **kwargs):
            with original_open(path, mode, *rest, **kwargs) as stream:
                yield stream
            if mode == "rb":
                reads.append(Path(path))
                if mutate is not None and Path(path) == mutate:
                    with original_open(path, "wb") as stream:
                        stream.write(b"mutated after snapshot")

        return reads, wrapper

    reads, wrapper = tracker(directory / "hypothesis.json")
    with monkeypatch.context() as scoped:
        scoped.setattr(Path, "open", wrapper)
        directory_summary = _summary(
            ["research", "plan", "--verify", str(directory), "--summary", "--json"], capsys,
        )
    assert sorted(reads) == sorted(directory / name for name in PACKAGE_FILES)
    assert (directory / "hypothesis.json").read_bytes() == b"mutated after snapshot"
    reads, wrapper = tracker(archive)
    with monkeypatch.context() as scoped:
        scoped.setattr(Path, "open", wrapper)
        archive_summary = _summary(
            ["research", "plan", "--verify-archive", str(archive), "--summary", "--json"],
            capsys,
        )
    assert reads == [archive]
    assert archive.read_bytes() == b"mutated after snapshot"
    assert directory_summary == research_plan.build_summary(
        expected_directory, sections=[], source="VERIFIED_DIRECTORY_ONCE",
    )
    assert archive_summary == research_plan.build_summary(
        expected_archive, sections=[], source="VERIFIED_ARCHIVE_ONCE",
    )


def test_doctored_reports_fail_closed_and_option_units(tmp_path):
    _, _, _, report = _prepare(tmp_path)

    def duplicate_role(document):
        requirements = document["plan"]["dataset_requirements"]["requirements"]
        requirements.append(copy.deepcopy(requirements[1]))

    def duplicate_intercept(document):
        terms = document["plan"]["design_plan"]["ordered_terms"]
        terms.append(copy.deepcopy(terms[0]))

    def foreign_control_source(document):
        document["plan"]["design_plan"]["ordered_terms"][2]["source_series_role"] = "TARGET_OUTCOME"

    def conditional_outcome(document):
        document["plan"]["conditional_summary_plan"]["source_roles"]["outcome"] = "OTHER"

    def conditional_condition(document):
        document["plan"]["conditional_summary_plan"]["source_roles"]["condition"] = "OTHER"

    cases = (
        lambda document: document.__setitem__("schema", "other"),
        lambda document: document.__setitem__("status", "executed"),
        lambda document: document["boundary"].__setitem__("research_ready", True),
        lambda document: document["boundary"].pop("outcome_read"),
        lambda document: document["boundary"].__setitem__("extra_flag", False),
        lambda document: document["plan"].__setitem__("hypothesis_id", "OTHER"),
        lambda document: document["plan"].__setitem__("source_contract_digest", "0" * 64),
        lambda document: document["contract"].__setitem__("contract_state", "OTHER_STATE"),
        lambda document: document["plan"].__setitem__("plan_state", "OTHER_STATE"),
        lambda document: document["plan"]["design_plan"].__setitem__("response_role", "OTHER"),
        duplicate_role,
        duplicate_intercept,
        foreign_control_source,
        conditional_outcome,
        conditional_condition,
    )
    for case in cases:
        document = copy.deepcopy(report)
        case(document)
        with pytest.raises(research_plan.PlanError) as caught:
            research_plan.build_summary(document, sections=[], source="COMPILED_ONCE")
        assert caught.value.code == "PLAN_SUMMARY_MISMATCH"
    assert research_plan.build_summary(
        report, sections=[], source="COMPILED_ONCE",
    )["schema"] == research_plan.SUMMARY_SCHEMA
    with pytest.raises(research_plan.PlanError) as caught:
        research_plan.validate_summary_options(False, ["requirements"])
    assert caught.value.code == "INVALID_ARGUMENTS"
    with pytest.raises(research_plan.PlanError) as caught:
        research_plan.validate_summary_options(True, ["unknown"])
    assert caught.value.code == "INVALID_SECTION"
    research_plan.validate_summary_options(True, [])
    with pytest.raises(research_plan.PlanError) as caught:
        research_plan.build_summary(report, sections=[], source="OTHER")
    assert caught.value.code == "INVALID_ARGUMENTS"


def test_cli_frames_a_doctored_capture_as_sanitized_failure(tmp_path, monkeypatch, capsys):
    source, _, _, report = _prepare(tmp_path)
    doctored = copy.deepcopy(report)
    doctored["boundary"]["research_ready"] = True
    monkeypatch.setattr(research_plan, "build_report", lambda path: copy.deepcopy(doctored))
    assert cli.main([
        "research", "plan", "--hypothesis", str(source), "--summary", "--json",
    ]) == 2
    captured = capsys.readouterr()
    assert captured.out == "" and captured.err == "error: PLAN_SUMMARY_MISMATCH\n"


def test_verifier_failures_stay_sanitized_for_summary_requests(tmp_path, monkeypatch, capsys):
    _, directory, archive, _ = _prepare(tmp_path)

    def rejected(args, code):
        assert cli.main([*args, "--summary", "--json"]) == 2
        captured = capsys.readouterr()
        assert captured.out == "" and captured.err == f"error: {code}\n"

    plan_file, manifest_file = directory / "plan.json", directory / "manifest.json"
    plan_payload, manifest_payload = plan_file.read_bytes(), manifest_file.read_bytes()
    forged = json.loads(plan_payload)
    forged["boundary"]["research_ready"] = True
    plan_file.write_text(json.dumps(forged), encoding="utf-8")
    manifest = json.loads(manifest_payload)
    entry = next(row for row in manifest["files"] if row["path"] == "plan.json")
    entry["sha256"] = hashlib.sha256(plan_file.read_bytes()).hexdigest()
    entry["byte_count"] = len(plan_file.read_bytes())
    manifest_file.write_text(json.dumps(manifest), encoding="utf-8")
    rejected(["research", "plan", "--verify", str(directory)], "PLAN_PACKAGE_MISMATCH")
    plan_file.write_bytes(plan_payload)
    manifest_file.write_bytes(manifest_payload)
    original_zip = archive.read_bytes()
    archive.write_bytes(b"not a ZIP")
    rejected(["research", "plan", "--verify-archive", str(archive)], "PLAN_ARCHIVE_INVALID")
    archive.write_bytes(original_zip)
    rejected(["research", "plan", "--verify", str(tmp_path / "missing")], "INVALID_PLAN_PACKAGE")
    rejected(
        ["research", "plan", "--verify-archive", str(tmp_path / "missing.zip")],
        "PLAN_ARCHIVE_READ_FAILED",
    )
    original_lstat = Path.lstat

    class Reparse:
        st_mode = 0o100644
        st_file_attributes = 0x400

    with monkeypatch.context() as scoped:
        scoped.setattr(Path, "lstat", lambda path, **kw: (
            Reparse() if path == directory else original_lstat(path, **kw)
        ))
        rejected(["research", "plan", "--verify", str(directory)], "LINKED_PACKAGE_PATH")


def test_summary_stays_offline_and_creates_no_files(tmp_path, monkeypatch, capsys):
    source, directory, archive, _ = _prepare(tmp_path)
    before = {path: path.read_bytes() for path in tmp_path.rglob("*") if path.is_file()}

    def forbidden(*args, **kwargs):
        raise AssertionError("No services/network/database/execution")

    for name in ("load_config", "setup_logging", "_create_service"):
        monkeypatch.setattr(cli, name, forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(duckdb, "connect", forbidden)
    monkeypatch.setattr(pipeline, "run_synthetic_pipeline", forbidden)
    monkeypatch.setattr(execution, "execute_bounded_analysis", forbidden)
    for args in (
        ["research", "plan", "--hypothesis", str(source), "--summary", "--json"],
        ["research", "plan", "--verify", str(directory), "--summary", "--json"],
        ["research", "plan", "--verify-archive", str(archive), "--summary"],
    ):
        assert cli.main(args) == 0
        captured = capsys.readouterr()
        assert captured.err == "" and captured.out
    after = {path: path.read_bytes() for path in tmp_path.rglob("*") if path.is_file()}
    assert after == before
