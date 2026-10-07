"""Public synthetic preparation, unchanged gates and no statistical execution."""

import copy
import hashlib
import json
import socket
from contextlib import contextmanager
from pathlib import Path

import duckdb

from ashare_research import cli
from ashare_research.mechanism import execution, pipeline
from ashare_research.mechanism.contract_compiler import compile_hypothesis_config
from ashare_research.mechanism.datasets import (
    BoundDatasetInputsV1,
    dataset_to_canonical_dict,
    materialize_analysis_dataset,
)
from ashare_research.mechanism.hypothesis_config import parse_hypothesis_config
from ashare_research.mechanism.model_digest import canonical_digest
from ashare_research.mechanism.planning import build_analysis_plan
from ashare_research.mechanism.planning.matrix import materialize_design_matrix, serialize_matrix
from ashare_research.tools import research_plan_archive, research_plan_package
from ashare_research.tools import synthetic_prepare as prepare

EXAMPLES = Path(__file__).resolve().parents[1] / "docs/examples"


def _inputs():
    return json.loads((EXAMPLES / "m4_bound_inputs.json").read_bytes())


def _package(tmp_path):
    source = EXAMPLES / "m4_hypothesis.json"
    directory, archive = tmp_path / "package", tmp_path / "plan.zip"
    inputs = tmp_path / "inputs.json"
    research_plan_package.export_package(source, directory)
    research_plan_archive.export_archive(source, archive)
    inputs.write_bytes((EXAMPLES / "m4_bound_inputs.json").read_bytes())
    return directory, archive, inputs


def _seal(document):
    bindings = {binding["role"]: binding for binding in document["bindings"]}
    for row in document["observations"]:
        payload = {key: value for key, value in row.items() if key != "evidence_digest"}
        row["evidence_digest"] = canonical_digest({**payload, "binding": bindings[row["role"]]})
    order = {binding["role"]: index for index, binding in enumerate(document["bindings"])}
    payload = {key: value for key, value in document.items() if key != "input_digest"}
    payload["observations"] = sorted(document["observations"],
                                     key=lambda row: (row["trade_date"], order[row["role"]]))
    document["input_digest"] = canonical_digest(payload)
    return document


def test_public_directory_zip_exact_apis_boundaries_and_immutable_inputs(
    tmp_path, monkeypatch, capsys,
):
    directory, archive, inputs = _package(tmp_path)
    contract = compile_hypothesis_config(parse_hypothesis_config(
        json.loads((EXAMPLES / "m4_hypothesis.json").read_bytes())
    ))
    plan = build_analysis_plan(contract)
    bound = BoundDatasetInputsV1.from_dict(_inputs())
    dataset = materialize_analysis_dataset(contract, plan, bound)
    matrix = materialize_design_matrix(dataset, contract, plan, bound)
    snapshots = {path: path.read_bytes() for path in (inputs, archive, *directory.iterdir())}

    def forbidden(*args, **kwargs):
        raise AssertionError("No service/network/database/pipeline/statistical execution")

    for name in ("load_config", "setup_logging", "_create_service"):
        monkeypatch.setattr(cli, name, forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(duckdb, "connect", forbidden)
    monkeypatch.setattr(pipeline, "run_synthetic_pipeline", forbidden)
    monkeypatch.setattr(execution, "execute_bounded_analysis", forbidden)
    args = ["research", "prepare", "--package", str(directory), "--inputs", str(inputs)]
    assert cli.main([*args, "--json"]) == 0
    captured = capsys.readouterr()
    report = json.loads(captured.out)
    assert captured.err == "" and report["schema"] == prepare.SCHEMA
    assert report["dataset"] == dataset_to_canonical_dict(dataset)
    assert report["matrix"] == json.loads(serialize_matrix(matrix))
    assert report["input_file_sha256"] == hashlib.sha256(inputs.read_bytes()).hexdigest()
    assert report["plan_identity"]["contract_digest"] == contract.contract_digest
    assert report["plan_identity"]["plan_digest"] == plan.plan_digest
    assert report["dataset"]["status"] == "READY_SYNTHETIC"
    assert len(report["matrix"]["rows"]) == 4 and len(report["matrix"]["columns"]) == 5
    assert report["boundary"]["outcome_read"] and report["boundary"]["synthetic_observations_read"]
    assert not any(value for key, value in report["boundary"].items()
                   if key not in ("outcome_read", "synthetic_observations_read"))
    assert not report["matrix"]["statistics_computed"]
    assert not report["dataset"]["execution_authorized"]
    assert cli.main(args) == 0
    assert capsys.readouterr().out == prepare.render_markdown(report)
    assert prepare.build_report(archive, inputs, archive=True) == report
    assert {path: path.read_bytes() for path in snapshots} == snapshots


def test_quality_rejection_preserves_denominator_and_invalid_bindings_fail_closed(
    tmp_path, monkeypatch, capsys,
):
    directory, _, inputs = _package(tmp_path)
    args = ["research", "prepare", "--package", str(directory), "--inputs", str(inputs), "--json"]
    original = _inputs()

    def write(document):
        inputs.write_text(json.dumps(document), encoding="utf-8")

    for reason, field, value in (
        ("MISSING_OBSERVATION", None, None), ("MISSING_VALUE", "value", None),
        ("PIT_UNPROVEN", "available_on", None),
        ("PIT_NOT_AVAILABLE", "available_on", "2020-01-03"),
    ):
        changed = copy.deepcopy(original)
        if field is None:
            changed["observations"].pop(0)
        else:
            changed["observations"][0][field] = value
        write(_seal(changed))
        with monkeypatch.context() as scoped:
            scoped.setattr(prepare, "materialize_design_matrix", lambda *a: (
                (_ for _ in ()).throw(AssertionError("No rejected matrix projection"))
            ))
            assert cli.main(args) == 0
        report = json.loads(capsys.readouterr().out)
        assert report["dataset"]["status"] == "REJECTED_QUALITY" and report["matrix"] is None
        quality = report["dataset"]["quality"]
        assert quality["coverage_numerator"] == 3 and quality["coverage_denominator"] == 4
        assert quality["reason_counts"] == {reason: 1}
        assert quality["rejected_dates"] == ["2020-01-02"]
        assert len(report["dataset"]["audit_rows"]) == 4
        assert report["dataset"]["complete_rows"] == []
        assert "REJECTED_QUALITY" in prepare.render_markdown(report)
    cases = []
    for key, value, code in (("mode", "REAL", "UNSUPPORTED_MODE"),
                             ("source_contract_digest", "0" * 64, "CONTRACT_PLAN_MISMATCH"),
                             ("input_digest", "0" * 64, "INPUT_DIGEST_MISMATCH")):
        changed = copy.deepcopy(original)
        changed[key] = value
        cases.append((changed, code))
    changed = copy.deepcopy(original)
    changed["bindings"][0]["unit"] = "PERCENT"
    cases.append((changed, "ROLE_BINDING_MISMATCH"))
    changed = copy.deepcopy(original)
    changed["observations"][0]["trade_date"] = "2023-01-02"
    cases.append((_seal(changed), "OUT_OF_DOMAIN"))
    changed = copy.deepcopy(original)
    changed["observations"][0]["value"] = "0.02"  # hashes intentionally not repaired
    cases.append((changed, "EVIDENCE_DIGEST_MISMATCH"))
    changed = copy.deepcopy(original)
    changed["observations"][0]["value"] = 1.0
    cases.append((changed, "INVALID_VALUE"))
    changed = copy.deepcopy(original)
    changed["domain"]["calendar_evidence"]["evidence_digest"] = "0" * 64
    cases.append((changed, "EVIDENCE_DIGEST_MISMATCH"))
    for document, code in cases:
        write(document)
        before = inputs.read_bytes()
        assert cli.main(args) == 2
        captured = capsys.readouterr()
        assert captured.out == "" and captured.err == f"error: {code}\n"
        assert inputs.read_bytes() == before


def test_strict_input_verification_paths_flags_and_single_read_snapshot(
    tmp_path, monkeypatch, capsys,
):
    directory, archive, inputs = _package(tmp_path)
    args = ["research", "prepare", "--archive", str(archive), "--inputs", str(inputs), "--json"]
    original = inputs.read_bytes()

    def rejected(code, custom=None):
        assert cli.main(args if custom is None else custom) == 2
        captured = capsys.readouterr()
        assert captured.out == "" and captured.err == f"error: {code}\n"

    for raw, code in ((b'{}', "INVALID_INPUT_STRUCTURE"), (b'[]', "INVALID_INPUT_ROOT"),
                      (b'\xff', "INVALID_INPUT_JSON"),
                      (b'{"x":1,"x":2}', "DUPLICATE_INPUT_JSON_KEY"),
                      (b'{"x":NaN}', "NONFINITE_INPUT_JSON_NUMBER"),
                      (b' ' * (prepare.MAX_INPUT_BYTES + 1), "INPUT_TOO_LARGE")):
        inputs.write_bytes(raw)
        rejected(code)
    inputs.write_bytes(original)
    for custom in (["research", "prepare"], [*args, "--package", str(directory)],
                   [*args, "--execute"], [*args, "--output", str(tmp_path / "new")]):
        rejected("INVALID_ARGUMENTS", custom)
    assert cli.main(["--debug", *args]) == 2
    captured = capsys.readouterr()
    assert captured.out == "" and captured.err == (
        "error: global option --debug cannot be combined with research\n"
        "usage: ashare-research research <command> [tool arguments...]\n"
    )
    assert not (tmp_path / "new").exists()
    rejected("INPUT_READ_FAILED", [*args[:-2], str(tmp_path / "missing.json"), "--json"])
    rejected("INVALID_INPUT_FILE", [*args[:-2], str(tmp_path), "--json"])
    original_lstat = Path.lstat

    class Reparse:
        st_mode = 0o100644
        st_file_attributes = 0x400

    with monkeypatch.context() as scoped:
        scoped.setattr(Path, "lstat", lambda path, **kw: (
            Reparse() if path == inputs else original_lstat(path, **kw)
        ))
        rejected("LINKED_INPUT_PATH")
    plan_json = directory / "plan.json"
    saved_plan = plan_json.read_bytes()
    plan_json.write_bytes(b'{}')
    rejected("PLAN_PACKAGE_MISMATCH", ["research", "prepare", "--package", str(directory),
                                        "--inputs", str(tmp_path / "missing.json"), "--json"])
    plan_json.write_bytes(saved_plan)
    reads = []
    original_open = Path.open

    @contextmanager
    def mutate_after_read(path, mode="r", *rest, **kwargs):
        with original_open(path, mode, *rest, **kwargs) as stream:
            yield stream
        if mode == "rb" and path in (archive, inputs):
            reads.append(path)
            if path == inputs:
                with original_open(path, "wb") as stream:
                    stream.write(b'changed after loaded snapshot')

    with monkeypatch.context() as scoped:
        scoped.setattr(Path, "open", mutate_after_read)
        assert cli.main(args) == 0
    report = json.loads(capsys.readouterr().out)
    assert reads == [archive, inputs]
    assert report["input_file_sha256"] == hashlib.sha256(original).hexdigest()
    assert report["dataset"]["status"] == "READY_SYNTHETIC"
    rejected("INVALID_INPUT_JSON")
