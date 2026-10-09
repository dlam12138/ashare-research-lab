"""Review actual config changes through the public entry without executing them."""

import hashlib
import json
import socket
from contextlib import contextmanager
from pathlib import Path

import duckdb

from ashare_research import cli
from ashare_research.mechanism import execution, pipeline
from ashare_research.tools import research_plan

EXAMPLE = Path(__file__).resolve().parents[1] / "docs/examples/m4_hypothesis.json"


def test_semantic_comparison_preserves_original_reports(tmp_path, monkeypatch, capsys):
    before = tmp_path / "before.json"
    after = tmp_path / "after.json"
    raw = EXAMPLE.read_bytes()
    before.write_bytes(raw)
    document = json.loads(raw)
    document["condition"]["threshold"] = "-0.02"
    document["controls"].reverse()
    document["development"]["start"] = "2021-01-01"
    document["data_quality_gates"]["coverage_gate"] = "0.98"
    document["bootstrap_policy"]["replications"] = 2000
    document["holdout_policy"] = {
        "start": "2023-01-01", "end": "2024-12-31", "policy_id": "SYNTH_SEALED_OOS",
        "max_accepted_primary_executions": 1,
    }
    after.write_text(json.dumps(document), encoding="utf-8")
    expected_before = research_plan.build_report(before)
    expected_after = research_plan.build_report(after)
    after_bytes = after.read_bytes()

    def forbidden(*args, **kwargs):
        raise AssertionError("Comparison must not execute or acquire data")

    for name in ("load_config", "setup_logging", "_create_service"):
        monkeypatch.setattr(cli, name, forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(duckdb, "connect", forbidden)
    monkeypatch.setattr(pipeline, "run_synthetic_pipeline", forbidden)
    monkeypatch.setattr(execution, "execute_bounded_analysis", forbidden)
    args = ["research", "plan", "--hypothesis", str(before), "--compare-with", str(after)]
    assert cli.main([*args, "--json"]) == 0
    captured = capsys.readouterr()
    assert captured.err == ""
    report = json.loads(captured.out)
    assert report["classification"] == "CANONICAL_CONFIG_CHANGED"
    assert report["before"] == expected_before and report["after"] == expected_after
    assert not report["same_source_bytes"] and not report["same_canonical_config"]
    changes = {item["path"]: item for item in report["changes"]}
    assert list(changes) == sorted(changes)
    assert set(changes) == {
        "/condition/threshold", "/controls", "/development/start",
        "/data_quality_gates/coverage_gate", "/bootstrap_policy/replications",
        "/holdout_policy",
    }
    assert changes["/controls"]["before"] == ["SYNTH_CONTROL_1", "SYNTH_CONTROL_2"]
    assert changes["/controls"]["after"] == ["SYNTH_CONTROL_2", "SYNTH_CONTROL_1"]
    assert changes["/condition/threshold"]["after"] == "-0.02"
    assert changes["/holdout_policy"]["before"] is None
    assert changes["/holdout_policy"]["after"]["start"] == "2023-01-01"
    for side in ("before", "after"):
        assert not any(report[side]["boundary"].values())
        assert report[side]["plan"]["source_contract_digest"] == (
            report[side]["contract"]["contract_digest"]
        )
    assert not any(report["boundary"].values())
    assert cli.main(args) == 0
    markdown = capsys.readouterr().out
    assert markdown == research_plan.render_comparison(report)
    assert "/controls" in markdown and "不推断统计或研究效果" in markdown
    assert expected_after["plan"]["plan_digest"] in markdown
    assert before.read_bytes() == raw and after.read_bytes() == after_bytes
    # Presence distinguishes added null from a missing key, even in nested JSON.
    assert research_plan._changes({"a/b": {}}, {"a/b": {"~": None}}) == [{
        "path": "/a~1b/~0", "before_present": False, "after_present": True,
        "before": None, "after": None,
    }]
    assert research_plan._changes({"value": True}, {"value": 1}) == [{
        "path": "/value", "before_present": True, "after_present": True,
        "before": True, "after": 1,
    }]


def test_equivalence_single_read_and_invalid_comparison(tmp_path, monkeypatch, capsys):
    before = tmp_path / "before.json"
    after = tmp_path / "after.json"
    raw = EXAMPLE.read_bytes()
    before.write_bytes(raw)
    after.write_text(json.dumps(json.loads(raw), sort_keys=True), encoding="utf-8")
    args = ["research", "plan", "--hypothesis", str(before), "--compare-with", str(after)]
    assert cli.main([*args, "--json"]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["classification"] == "CANONICALLY_EQUIVALENT_INPUTS"
    assert report["changes"] == [] and report["same_canonical_config"]
    assert report["before"]["contract"] == report["after"]["contract"]
    assert report["before"]["plan"] == report["after"]["plan"]
    assert report["before"]["source_file_sha256"] != report["after"]["source_file_sha256"]
    after.write_bytes(raw)
    assert research_plan.build_comparison(before, after)["classification"] == (
        "IDENTICAL_SOURCE_BYTES"
    )
    original_open = Path.open
    calls = []

    @contextmanager
    def mutate_after_read(path, mode="r", *rest, **kwargs):
        with original_open(path, mode, *rest, **kwargs) as stream:
            yield stream
        if path in (before, after) and mode == "rb":
            calls.append(path)
            with original_open(path, "wb") as target:
                target.write(b"changed after loading")

    with monkeypatch.context() as scoped:
        scoped.setattr(Path, "open", mutate_after_read)
        report = research_plan.build_comparison(before, after)
        assert calls == [before, after]
        assert report["after"]["source_file_sha256"] == hashlib.sha256(raw).hexdigest()
        before.write_bytes(raw)
        calls.clear()
        report = research_plan.build_comparison(before, before)
        assert calls == [before] and report["before"] == report["after"]
    before.write_bytes(raw)
    for payload, code in (
        (b'{"x":1,"x":2}', "DUPLICATE_JSON_KEY"),
        (b"[]", "INVALID_HYPOTHESIS_ROOT"),
        (b'{"x":NaN}', "NONFINITE_JSON_NUMBER"),
        (b" " * (research_plan.MAX_INPUT_BYTES + 1), "HYPOTHESIS_TOO_LARGE"),
    ):
        after.write_bytes(payload)
        assert cli.main([*args, "--json"]) == 2
        captured = capsys.readouterr()
        assert captured.out == "" and captured.err == f"error: {code}\n"
    assert cli.main([*args, "--execute"]) == 2
    captured = capsys.readouterr()
    assert captured.out == "" and captured.err == "error: INVALID_ARGUMENTS\n"
    assert cli.main(["research", "plan", "--compare-with", str(after)]) == 2
    assert capsys.readouterr().out == ""
