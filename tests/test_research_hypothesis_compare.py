"""Exercise canonical change provenance and fail-closed public comparison."""

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
from ashare_research.tools import research_hypothesis_compare as compare
from ashare_research.tools.research_plan import build_report

EXAMPLE = Path(__file__).resolve().parents[1] / "docs/examples/m4_hypothesis.json"


def test_original_envelopes_formatting_and_semantic_changes(tmp_path, monkeypatch, capsys):
    left, right = tmp_path / "left.json", tmp_path / "right.json"
    raw = EXAMPLE.read_bytes()
    left.write_bytes(raw)
    right.write_bytes(raw)
    expected = build_report(left)

    def forbidden(*args, **kwargs):
        raise AssertionError("No execution, network or database allowed")

    for name in ("load_config", "setup_logging", "_create_service"):
        monkeypatch.setattr(cli, name, forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(duckdb, "connect", forbidden)
    monkeypatch.setattr(pipeline, "run_synthetic_pipeline", forbidden)
    monkeypatch.setattr(execution, "execute_bounded_analysis", forbidden)
    args = ["research", "hypothesis-diff", "--left", str(left), "--right", str(right)]
    assert cli.main([*args, "--json"]) == 0
    captured = capsys.readouterr()
    assert captured.err == ""
    report = json.loads(captured.out)
    assert report["sources"] == {"left": expected, "right": expected}
    assert report["source_bytes_equal"]
    assert all(report["canonical_equal"].values()) and not report["changes"]
    assert not any(report["boundary"].values())

    document = json.loads(raw)
    right.write_text(json.dumps(document, sort_keys=True), encoding="utf-8")
    reformatted = compare.build_comparison(left, right)
    assert not reformatted["source_bytes_equal"]
    assert all(reformatted["canonical_equal"].values()) and not reformatted["changes"]
    altered = copy.deepcopy(document)
    altered["condition"]["threshold"] = "-0.02"
    altered["controls"].reverse()
    altered["holdout_policy"] = {
        "start": "2023-01-01", "end": "2024-12-31", "policy_id": "SYNTH_SEALED_OOS",
        "max_accepted_primary_executions": 1,
    }
    right.write_text(json.dumps(altered), encoding="utf-8")
    assert cli.main([*args, "--json"]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["sources"]["left"] == expected
    assert report["sources"]["right"] == build_report(right)
    assert not any(report["canonical_equal"].values())
    for side in ("left", "right"):
        original = report["sources"][side]
        assert original["plan"]["source_contract_digest"] == original["contract"]["contract_digest"]
        assert not any(original["boundary"].values())
    indexed = {(item["section"], item["path"]): item for item in report["changes"]}
    assert indexed["config", "/condition/threshold"]["left"] == "-0.01"
    assert indexed["config", "/condition/threshold"]["right"] == "-0.02"
    assert indexed["config", "/controls"]["right"] == list(reversed(document["controls"]))
    assert indexed["config", "/holdout_policy"]["left"] is None
    assert indexed["config", "/holdout_policy"]["left_present"] is True
    assert any(item["section"] == "plan" for item in report["changes"])
    assert all("digest" not in item["path"] for item in report["changes"])
    assert cli.main(args) == 0
    markdown = capsys.readouterr().out
    assert markdown == compare.render_markdown(report)
    assert "/condition/threshold" in markdown and '"execution_authorized": false' in markdown
    assert compare.build_comparison(left, right) == report
    assert left.read_bytes() == raw
    assert cli.main(["research", "--help"]) == 0
    assert "hypothesis-diff" in capsys.readouterr().out


def test_presence_types_order_and_markdown_escaping(tmp_path):
    left, right = tmp_path / "left.json", tmp_path / "right.json"
    document = json.loads(EXAMPLE.read_bytes())
    document["robustness_registry"][0]["parameters"] = {
        "add": None, "remove": None, "typed": [True], "a/b~c": "plain",
    }
    left.write_text(json.dumps(document), encoding="utf-8")
    document["robustness_registry"][0]["parameters"] = {
        "add": None, "new": None, "typed": [1],
        "a/b~c": "[link](https://invalid.example)|<img>*_`\\\n",
    }
    right.write_text(json.dumps(document), encoding="utf-8")
    report = compare.build_comparison(left, right)
    assert not report["canonical_equal"]["config"]
    change = next(item for item in report["changes"] if item["section"] == "config")
    assert change["path"] == "/robustness_registry"
    assert change["left"][0]["parameters"]["typed"] == [True]
    # The frozen compiler serializes numeric robustness parameters as decimals.
    assert change["right"][0]["parameters"]["typed"] == ["1"]
    assert report["sources"]["right"] == build_report(right)
    # Nested dictionaries remain positional; null and missing use separate presence flags.
    differences = compare._changes(
        {"null": None, "gone": None, "a/b~c": True},
        {"null": None, "new": None, "a/b~c": 1},
    )
    assert differences == [
        {"path": "/a~1b~0c", "kind": "changed", "left_present": True,
         "right_present": True, "left": True, "right": 1},
        {"path": "/gone", "kind": "removed", "left_present": True,
         "right_present": False, "left": None},
        {"path": "/new", "kind": "added", "left_present": False,
         "right_present": True, "right": None},
    ]
    markdown = compare.render_markdown(report)
    assert "<img>" not in markdown and "&lt;img&gt;" in markdown
    assert "\\[link\\]" in markdown and "\\*" in markdown and "\\|" in markdown
    assert compare._changes([1, 2], [2, 1])[0]["path"] == ""
    assert compare._changes([True], [1])[0]["right"] == [1]
    assert not compare._changes({"a": 1, "b": 2}, {"b": 2, "a": 1})


@pytest.mark.parametrize("side", ["left", "right"])
def test_invalid_side_never_emits_partial_output(tmp_path, capsys, side):
    left, right = tmp_path / "left.json", tmp_path / "right.json"
    raw = EXAMPLE.read_bytes()
    left.write_bytes(raw)
    right.write_bytes(raw)
    bad = left if side == "left" else right
    args = ["research", "hypothesis-diff", "--left", str(left), "--right", str(right), "--json"]
    for payload, code in (
        (b'{"x":1,"x":2}', "DUPLICATE_JSON_KEY"),
        (b'{"x":NaN}', "NONFINITE_JSON_NUMBER"),
        (b"[]", "INVALID_HYPOTHESIS_ROOT"),
        (b"{", "INVALID_HYPOTHESIS_JSON"),
        (b"\xff", "INVALID_HYPOTHESIS_JSON"),
        (b" " * 1_048_577, "HYPOTHESIS_TOO_LARGE"),
    ):
        bad.write_bytes(payload)
        assert cli.main(args) == 2
        captured = capsys.readouterr()
        assert captured.out == "" and captured.err == f"error: {code}\n"
    doc = json.loads(raw)
    doc["target"]["identity_policy"] = "SECURITY_LEVEL_IDENTITY_V1"
    bad.write_text(json.dumps(doc), encoding="utf-8")
    assert cli.main(args) == 2
    captured = capsys.readouterr()
    assert captured.out == "" and captured.err == "error: INVALID_IDENTITY_POLICY\n"
    bad.unlink()
    assert cli.main(args) == 2
    captured = capsys.readouterr()
    assert captured.out == "" and captured.err == "error: HYPOTHESIS_READ_FAILED\n"
    for extra in ("--execute", "--lef"):
        assert cli.main([*args, extra]) == 2
        captured = capsys.readouterr()
        assert captured.out == "" and captured.err == "error: INVALID_ARGUMENTS\n"


def test_each_side_consumed_once_and_source_mutation_cannot_change_report(
    tmp_path, monkeypatch, capsys,
):
    left, right = tmp_path / "left.json", tmp_path / "right.json"
    raw = EXAMPLE.read_bytes()
    left.write_bytes(raw)
    right.write_bytes(raw)
    original_open = Path.open
    calls = []

    @contextmanager
    def mutate_after_read(path, mode="r", *rest, **kwargs):
        with original_open(path, mode, *rest, **kwargs) as stream:
            yield stream
        if path in (left, right) and mode == "rb":
            calls.append(path)
            with original_open(path, "wb") as target:
                target.write(b"changed after loaded bytes")

    monkeypatch.setattr(Path, "open", mutate_after_read)
    args = ["research", "hypothesis-diff", "--left", str(left), "--right", str(right), "--json"]
    assert cli.main(args) == 0 and calls == [left, right]
    report = json.loads(capsys.readouterr().out)
    assert report["source_bytes_equal"] and not report["changes"]
    for source in report["sources"].values():
        assert source["source_file_sha256"] == hashlib.sha256(raw).hexdigest()
    assert cli.main(args) == 2 and calls == [left, right, left]
    captured = capsys.readouterr()
    assert captured.out == "" and captured.err == "error: INVALID_HYPOTHESIS_JSON\n"
