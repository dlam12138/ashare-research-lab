"""Public compile-only entry: original identities and fail-closed input boundaries."""

import copy
import hashlib
import json
import socket
from contextlib import contextmanager
from pathlib import Path

import duckdb

from ashare_research import cli
from ashare_research.mechanism import execution, pipeline
from ashare_research.mechanism.contract_compiler import (
    compile_hypothesis_config,
    config_to_canonical_dict,
    contract_to_canonical_dict,
)
from ashare_research.mechanism.hypothesis_config import parse_hypothesis_config
from ashare_research.mechanism.planning import build_analysis_plan, plan_to_canonical_dict
from ashare_research.tools import research_plan

EXAMPLE = Path(__file__).resolve().parents[1] / "docs/examples/m4_hypothesis.json"


def test_original_compilation_semantics_and_no_execution(tmp_path, monkeypatch, capsys):
    source = tmp_path / "假设.json"
    raw = EXAMPLE.read_bytes()
    source.write_bytes(raw)
    document = json.loads(raw)
    config = parse_hypothesis_config(document)
    contract = compile_hypothesis_config(config)
    plan = build_analysis_plan(contract)

    def forbidden(*args, **kwargs):
        raise AssertionError("No execution, service, network or database allowed")

    for name in ("load_config", "setup_logging", "_create_service"):
        monkeypatch.setattr(cli, name, forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(duckdb, "connect", forbidden)
    monkeypatch.setattr(pipeline, "run_synthetic_pipeline", forbidden)
    monkeypatch.setattr(execution, "execute_bounded_analysis", forbidden)
    args = ["research", "plan", "--hypothesis", str(source)]
    assert cli.main([*args, "--json"]) == 0
    captured = capsys.readouterr()
    assert captured.err == ""
    report = json.loads(captured.out)
    assert report["schema"] == research_plan.SCHEMA
    assert report["config"] == config_to_canonical_dict(config)
    assert report["contract"] == contract_to_canonical_dict(contract)
    assert report["plan"] == plan_to_canonical_dict(plan)
    assert report["plan"]["source_contract_digest"] == report["contract"]["contract_digest"]
    assert report["source_file_sha256"] == hashlib.sha256(raw).hexdigest()
    assert not any(report["boundary"].values())
    assert source.read_bytes() == raw
    assert cli.main(args) == 0
    markdown = capsys.readouterr().out
    assert markdown == research_plan.render_markdown(report)
    for role in ("TARGET_OUTCOME", "FACTOR", "CONTROL_0001", "CONTROL_0002"):
        assert role in markdown
    assert "独立封存" in markdown and '"execution_authorized": false' in markdown
    source.write_text(json.dumps(document, sort_keys=True), encoding="utf-8")
    reformatted = research_plan.build_report(source)
    assert reformatted["source_file_sha256"] != report["source_file_sha256"]
    assert reformatted["contract"] == report["contract"]
    assert reformatted["plan"] == report["plan"]
    changed = copy.deepcopy(document)
    changed["condition"]["threshold"] = "-0.02"
    changed["holdout_policy"] = {
        "start": "2023-01-01", "end": "2024-12-31", "policy_id": "SYNTH_SEALED_OOS",
        "max_accepted_primary_executions": 1,
    }
    source.write_text(json.dumps(changed), encoding="utf-8")
    altered = research_plan.build_report(source)
    assert altered["contract"]["contract_digest"] != report["contract"]["contract_digest"]
    assert altered["plan"]["plan_digest"] != report["plan"]["plan_digest"]
    assert altered["contract"]["condition"]["threshold"] == "-0.02"
    assert altered["plan"]["holdout_boundary"]["window"] == {
        "start": "2023-01-01", "end": "2024-12-31",
    }
    assert altered["plan"]["holdout_boundary"]["execution_authorized"] is False
    assert not any(altered["boundary"].values())


def test_json_limits_unsupported_policy_errors_and_one_read(tmp_path, monkeypatch, capsys):
    source = tmp_path / "hypothesis.json"
    raw = EXAMPLE.read_bytes()
    args = ["research", "plan", "--hypothesis", str(source), "--json"]
    for payload, code in ((b"[]", "INVALID_HYPOTHESIS_ROOT"),
                          (b'{"x":1,"x":2}', "DUPLICATE_JSON_KEY"),
                          (b'{"nested":{"x":1,"x":2}}', "DUPLICATE_JSON_KEY"),
                          (b'{"x":NaN}', "NONFINITE_JSON_NUMBER"),
                          (b'{"x":Infinity}', "NONFINITE_JSON_NUMBER"),
                          (b"\xff", "INVALID_HYPOTHESIS_JSON"),
                          (b"{", "INVALID_HYPOTHESIS_JSON")):
        source.write_bytes(payload)
        assert cli.main(args) == 2
        captured = capsys.readouterr()
        assert captured.out == "" and captured.err == f"error: {code}\n"
    document = json.loads(raw)
    document["target"]["identity_policy"] = "SECURITY_LEVEL_IDENTITY_V1"
    source.write_text(json.dumps(document), encoding="utf-8")
    assert cli.main(args) == 2
    assert capsys.readouterr().err == "error: INVALID_IDENTITY_POLICY\n"
    source.write_bytes(b" " * (research_plan.MAX_INPUT_BYTES + 1))
    assert cli.main(args) == 2
    assert capsys.readouterr().err == "error: HYPOTHESIS_TOO_LARGE\n"
    assert cli.main([*args, "--execute"]) == 2
    captured = capsys.readouterr()
    assert captured.out == "" and captured.err == "error: INVALID_ARGUMENTS\n"
    assert cli.main(["research", "plan", "--hypothesis", str(tmp_path / "absent")]) == 2
    assert capsys.readouterr().err == "error: HYPOTHESIS_READ_FAILED\n"
    source.write_bytes(raw)
    original_open = Path.open
    calls = []

    @contextmanager
    def mutate_after_read(path, mode="r", *rest, **kwargs):
        with original_open(path, mode, *rest, **kwargs) as stream:
            yield stream
        if path == source and mode == "rb":
            calls.append(path)
            with original_open(path, "wb") as target:
                target.write(b"changed after loaded bytes")

    monkeypatch.setattr(Path, "open", mutate_after_read)
    assert cli.main(args) == 0 and calls == [source]
    report = json.loads(capsys.readouterr().out)
    assert report["source_file_sha256"] == hashlib.sha256(raw).hexdigest()
    assert report["contract"]["hypothesis_id"] == "SYNTH_DAILY_CONTROLLED_001"
    assert cli.main(args) == 2 and calls == [source, source]
    captured = capsys.readouterr()
    assert captured.out == "" and captured.err == "error: INVALID_HYPOTHESIS_JSON\n"
