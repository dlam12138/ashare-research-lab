"""Verified pre-execution plan differences, immutable inputs and fail-closed IO."""

import copy
import json
import socket
from contextlib import contextmanager
from pathlib import Path

import duckdb

from ashare_research import cli
from ashare_research.mechanism import execution, pipeline
from ashare_research.tools import research_plan, research_plan_archive, research_plan_package
from ashare_research.tools import research_plan_compare as compare

EXAMPLE = Path(__file__).resolve().parents[1] / "docs/examples/m4_hypothesis.json"


def _prepare(tmp_path, changed=None, *, stem="source"):
    source = tmp_path / f"{stem}.json"
    source.write_bytes(EXAMPLE.read_bytes() if changed is None else json.dumps(changed).encode())
    directory, archive = tmp_path / f"{stem}-package", tmp_path / f"{stem}.zip"
    report = research_plan.build_report(source)
    research_plan_package.export_package(source, directory)
    research_plan_archive.export_archive(source, archive)
    return source, directory, archive, report


def test_mixed_verified_semantic_changes_reversal_and_offline_boundaries(
    tmp_path, monkeypatch, capsys,
):
    old_source, old_dir, old_zip, original = _prepare(tmp_path)
    changed = json.loads(EXAMPLE.read_bytes())
    changed["condition"]["threshold"] = "-0.02"
    changed["controls"].pop()
    new_source, new_dir, new_zip, altered = _prepare(tmp_path, changed, stem="changed")
    before_files = {path: path.read_bytes() for directory in (old_dir, new_dir)
                    for path in directory.iterdir()}
    before_files.update({path: path.read_bytes() for path in (old_source, old_zip,
                                                            new_source, new_zip)})

    def forbidden(*args, **kwargs):
        raise AssertionError("No services/network/database/execution")

    for name in ("load_config", "setup_logging", "_create_service"):
        monkeypatch.setattr(cli, name, forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(duckdb, "connect", forbidden)
    monkeypatch.setattr(pipeline, "run_synthetic_pipeline", forbidden)
    monkeypatch.setattr(execution, "execute_bounded_analysis", forbidden)
    args = ["research", "plan-compare", "--left", str(old_dir),
            "--right-archive", str(new_zip)]
    assert cli.main([*args, "--json"]) == 0
    captured = capsys.readouterr()
    report = json.loads(captured.out)
    assert captured.err == "" and report["schema"] == compare.SCHEMA
    for side, expected in (("left", original), ("right", altered)):
        assert report[side]["source_file_sha256"] == expected["source_file_sha256"]
        assert report[side]["config_digest"] == expected["contract"]["source_config_digest"]
        assert report[side]["contract_digest"] == expected["contract"]["contract_digest"]
        assert report[side]["plan_digest"] == expected["plan"]["plan_digest"]
    assert not report["canonical_content_equal"] and report["change_count"] > 0
    assert report["change_count"] == len(report["changes"])
    assert sum(report["section_change_counts"].values()) == report["change_count"]
    assert all(report["section_change_counts"][section] > 0 for section in compare.SECTIONS)
    assert not report["equality"]["contract_digest"] and not report["equality"]["plan_digest"]
    assert not any(report["boundary"].values())
    config_rows = {row["pointer"]: row for row in report["changes"] if row["section"] == "config"}
    assert set(config_rows) == {"/condition/threshold", "/controls/1"}
    assert config_rows["/condition/threshold"]["left"] == {"present": True, "value": "-0.01"}
    assert config_rows["/condition/threshold"]["right"] == {"present": True, "value": "-0.02"}
    assert config_rows["/controls/1"]["right"] == {"present": False, "value": None}
    assert all(row["pointer"] not in ("/contract_digest", "/source_config_digest",
                                      "/plan_digest", "/source_contract_digest")
               for row in report["changes"])
    assert cli.main(args) == 0
    markdown = capsys.readouterr().out
    assert markdown == compare.render_markdown(report)
    assert "/condition/threshold" in markdown and "（缺失）" in markdown
    assert '"execution_authorized": false' in markdown and "独立封存" in markdown
    # Relocation and container choice do not change the semantic report.
    moved = tmp_path / "搬移后的包"
    old_dir.rename(moved)
    assert compare.build_comparison(moved, new_zip, right_archive=True) == report
    assert compare.build_comparison(old_zip, new_dir, left_archive=True) == report
    reverse = compare.build_comparison(new_dir, old_zip, right_archive=True)
    assert reverse["left"] == report["right"] and reverse["right"] == report["left"]
    assert reverse["changes"] == [
        {**row, "left": row["right"], "right": row["left"]} for row in report["changes"]
    ]
    for path, payload in before_files.items():
        current = moved / path.name if path.parent == old_dir else path
        assert current.read_bytes() == payload


def test_format_only_inputs_missing_null_types_pointer_and_markdown_escaping(tmp_path):
    source, directory, _, original = _prepare(tmp_path)
    document = json.loads(source.read_bytes())
    reformatted = tmp_path / "format.json"
    reformatted.write_text(json.dumps(document, sort_keys=True, indent=1), encoding="utf-8")
    format_zip = tmp_path / "format.zip"
    research_plan_archive.export_archive(reformatted, format_zip)
    result = compare.build_comparison(directory, format_zip, right_archive=True)
    assert not result["equality"]["source_file_sha256"]
    assert result["equality"]["config_digest"] and result["equality"]["contract_digest"]
    assert result["equality"]["plan_digest"] and result["canonical_content_equal"]
    assert result["changes"] == [] and result["change_count"] == 0
    assert result["left"]["plan_digest"] == original["plan"]["plan_digest"]
    assert "无规范内容变化。" in compare.render_markdown(result)
    old = {"a/b~": {"nullable": None, "flag": True, "list": [0, 1]}}
    new = {"a/b~": {"added": None, "flag": 1, "list": [0]}}
    rows = {row["pointer"]: row for row in compare._changes(old, new)}
    assert set(rows) == {"/a~1b~0/nullable", "/a~1b~0/added", "/a~1b~0/flag", "/a~1b~0/list/1"}
    assert rows["/a~1b~0/nullable"]["left"] == {"present": True, "value": None}
    assert rows["/a~1b~0/nullable"]["right"] == {"present": False, "value": None}
    assert rows["/a~1b~0/added"]["left"] == {"present": False, "value": None}
    assert rows["/a~1b~0/added"]["right"] == {"present": True, "value": None}
    assert type(rows["/a~1b~0/flag"]["left"]["value"]) is bool
    assert type(rows["/a~1b~0/flag"]["right"]["value"]) is int
    assert rows["/a~1b~0/list/1"]["right"]["present"] is False
    decorated = copy.deepcopy(result)
    decorated["changes"] = [{"section": "config", "pointer": "/<tag>|`\n",
                              "left": {"present": True, "value": "<tag>|`\n"},
                              "right": {"present": True, "value": None}}]
    decorated["change_count"] = 1
    markdown = compare.render_markdown(decorated)
    assert "<tag>" not in markdown and "&lt;tag&gt;" in markdown
    assert "\\|" in markdown and "&#96;" in markdown and "&amp;#96;" not in markdown
    assert "null" in markdown


def test_full_verification_failures_flags_links_and_single_snapshot(tmp_path, monkeypatch, capsys):
    _, left, _, _ = _prepare(tmp_path)
    _, right, right_zip, _ = _prepare(tmp_path, stem="right")
    base = ["research", "plan-compare"]

    def rejected(args, code):
        assert cli.main([*base, *args, "--json"]) == 2
        captured = capsys.readouterr()
        assert captured.out == "" and captured.err == f"error: {code}\n"

    args = ["--left", str(left), "--right", str(right)]
    plan = right / "plan.json"
    payload = plan.read_bytes()
    forged = json.loads(payload)
    forged["boundary"]["research_ready"] = True
    plan.write_text(json.dumps(forged), encoding="utf-8")
    rejected(args, "PLAN_PACKAGE_MISMATCH")
    rejected(["--left", str(right), "--right", str(left)], "PLAN_PACKAGE_MISMATCH")
    plan.write_bytes(payload)
    original_zip = right_zip.read_bytes()
    right_zip.write_bytes(b"not a ZIP")
    rejected(["--left", str(left), "--right-archive", str(right_zip)], "PLAN_ARCHIVE_INVALID")
    right_zip.write_bytes(original_zip)
    for invalid in ([], ["--left", str(left)],
                    [*args, "--left-archive", str(right_zip)],
                    [*args, "--output", str(tmp_path / "new")], [*args, "--execute"]):
        rejected(invalid, "INVALID_ARGUMENTS")
    assert not (tmp_path / "new").exists()
    rejected(["--left", str(tmp_path / "missing"), "--right", str(right)], "INVALID_PLAN_PACKAGE")
    rejected(["--left-archive", str(tmp_path / "missing.zip"), "--right", str(right)],
             "PLAN_ARCHIVE_READ_FAILED")
    original_lstat = Path.lstat

    class Reparse:
        st_mode = 0o100644
        st_file_attributes = 0x400

    with monkeypatch.context() as scoped:
        scoped.setattr(Path, "lstat", lambda path, **kw: (
            Reparse() if path == right else original_lstat(path, **kw)
        ))
        rejected(args, "LINKED_PACKAGE_PATH")
    original_open = Path.open
    reads = []

    @contextmanager
    def mutate_after_read(path, mode="r", *rest, **kwargs):
        with original_open(path, mode, *rest, **kwargs) as stream:
            yield stream
        if mode == "rb" and path in (left / "hypothesis.json", right_zip):
            reads.append(path)
            if path == right_zip:
                with original_open(path, "wb") as stream:
                    stream.write(b"changed after loaded snapshot")

    with monkeypatch.context() as scoped:
        scoped.setattr(Path, "open", mutate_after_read)
        assert cli.main([*base, "--left", str(left), "--right-archive", str(right_zip),
                         "--json"]) == 0
    compared = json.loads(capsys.readouterr().out)
    assert reads == [left / "hypothesis.json", right_zip]
    assert compared["canonical_content_equal"] and compared["changes"] == []
    rejected(
        ["--left", str(left), "--right-archive", str(right_zip)], "PLAN_ARCHIVE_INVALID"
    )
