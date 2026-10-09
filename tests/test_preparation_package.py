"""Reproduction verifies source bytes and generated content, not just inventories."""

import hashlib
import json
import shutil
import socket
from contextlib import contextmanager
from pathlib import Path

import duckdb
from test_preparation_diagnostics import _sources, _write_invented

from ashare_research import cli
from ashare_research.mechanism import execution, pipeline
from ashare_research.tools import preparation_diagnostics, preparation_package, synthetic_prepare


def _args(plan, inputs, output):
    return ["research", "prepare-package", "--package", str(plan), "--inputs", str(inputs),
            "--output", str(output), "--json"]


def test_public_export_relocated_verify_exact_sources_quality_and_offline(
    tmp_path, monkeypatch, capsys,
):
    plan, _, inputs = _sources(tmp_path)
    report = synthetic_prepare.build_report(plan, inputs)
    source_paths = [inputs, *plan.iterdir()]
    originals = {path: path.read_bytes() for path in source_paths}
    output = tmp_path / "delivery"

    def forbidden(*args, **kwargs):
        raise AssertionError("No database, network, service, pipeline or statistical execution")

    for name in ("load_config", "setup_logging", "_create_service"):
        monkeypatch.setattr(cli, name, forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(duckdb, "connect", forbidden)
    monkeypatch.setattr(pipeline, "run_synthetic_pipeline", forbidden)
    monkeypatch.setattr(execution, "execute_bounded_analysis", forbidden)
    assert cli.main(_args(plan, inputs, output)) == 0
    captured = capsys.readouterr()
    assert captured.err == ""
    receipt = json.loads(captured.out)
    assert receipt["status"] == "exported_preparation"
    assert {path.name for path in output.iterdir()} == preparation_package.NAMES
    assert len(preparation_package.NAMES) == 10
    for name, saved in preparation_package.PLAN_NAMES.items():
        assert (output / saved).read_bytes() == originals[plan / name]
    assert (output / "inputs.json").read_bytes() == originals[inputs]
    assert json.loads((output / "preparation.json").read_bytes()) == report
    assert (output / "preparation.md").read_text("utf-8") == (
        synthetic_prepare.render_markdown(report)
    )
    expected_summary = preparation_diagnostics.build_summary(report, roles=[], gaps_only=False)
    assert json.loads((output / "diagnostics.json").read_bytes()) == expected_summary
    assert receipt["manifest"]["boundary"] == report["boundary"]
    for entry in receipt["manifest"]["files"]:
        raw = (output / entry["path"]).read_bytes()
        assert len(raw) == entry["byte_count"]
        assert hashlib.sha256(raw).hexdigest() == entry["sha256"]
    relocated = tmp_path / "relocated"
    shutil.copytree(output, relocated)
    saved = {path: path.read_bytes() for path in relocated.iterdir()}
    assert cli.main(["research", "prepare-package", "--verify", str(relocated), "--json"]) == 0
    verified = json.loads(capsys.readouterr().out)
    assert verified["report"] == report and verified["diagnostics"] == expected_summary
    assert verified["independent_seal_verified"] is False
    assert {path: path.read_bytes() for path in saved} == saved
    assert {path: path.read_bytes() for path in originals} == originals
    # Quality rejection remains a valid reproducible diagnostic delivery, not readiness.
    document = json.loads(originals[inputs])
    document["observations"][0]["value"] = None
    document["observations"][0]["available_on"] = None
    _write_invented(document, inputs)
    rejected_output = tmp_path / "rejected"
    assert cli.main(_args(plan, inputs, rejected_output)) == 0
    capsys.readouterr()
    assert cli.main(["research", "prepare-package", "--verify", str(rejected_output)]) == 0
    markdown = capsys.readouterr().out
    rejected = preparation_package.verify_package(rejected_output)
    assert rejected["report"]["dataset"]["status"] == "REJECTED_QUALITY"
    assert rejected["report"]["matrix"] is None
    assert rejected["report"]["dataset"]["quality"]["coverage_numerator"] == 3
    assert rejected["report"]["dataset"]["quality"]["coverage_denominator"] == 4
    assert rejected["report"]["boundary"]["statistics_computed"] is False
    assert "REJECTED_QUALITY" in markdown and "不是来源证明" in markdown


def test_forged_inventory_corruption_entries_and_limits_fail_closed(tmp_path, monkeypatch, capsys):
    plan, _, inputs = _sources(tmp_path)
    output = tmp_path / "delivery"
    preparation_package.export_package(plan, inputs, output)
    args = ["research", "prepare-package", "--verify", str(output), "--json"]
    snapshot = {path.name: path.read_bytes() for path in output.iterdir()}

    def rejected(code):
        assert cli.main(args) == 2
        captured = capsys.readouterr()
        assert captured.out == "" and captured.err == f"error: {code}\n"

    report = json.loads(snapshot["preparation.json"])
    report["boundary"]["statistics_computed"] = True
    forged = json.dumps(report).encode("utf-8")
    (output / "preparation.json").write_bytes(forged)
    manifest = json.loads(snapshot["manifest.json"])
    entry = next(item for item in manifest["files"] if item["path"] == "preparation.json")
    entry["byte_count"] = len(forged)
    entry["sha256"] = hashlib.sha256(forged).hexdigest()
    (output / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    rejected("PREPARATION_PACKAGE_MISMATCH")
    for name in ("preparation.json", "manifest.json"):
        (output / name).write_bytes(snapshot[name])
    (output / "plan-plan.json").write_bytes(b"{}")
    rejected("PLAN_PACKAGE_MISMATCH")
    (output / "plan-plan.json").write_bytes(snapshot["plan-plan.json"])
    stale = json.loads(snapshot["inputs.json"])
    stale["observations"][0]["value"] = "0.123"
    (output / "inputs.json").write_text(json.dumps(stale), encoding="utf-8")
    rejected("EVIDENCE_DIGEST_MISMATCH")
    (output / "inputs.json").write_bytes(snapshot["inputs.json"])
    extra = output / "extra"
    extra.mkdir()
    rejected("INVALID_PREPARATION_PACKAGE_FILES")
    extra.rmdir()
    moved = tmp_path / "missing.md"
    (output / "preparation.md").rename(moved)
    rejected("INVALID_PREPARATION_PACKAGE_FILES")
    (output / "preparation.md").mkdir()
    rejected("INVALID_PREPARATION_PACKAGE_FILES")
    (output / "preparation.md").rmdir()
    moved.rename(output / "preparation.md")
    (output / "inputs.json").write_bytes(b" " * (preparation_package.MAX_SOURCE_BYTES + 1))
    rejected("PREPARATION_PACKAGE_LIMIT_EXCEEDED")
    (output / "inputs.json").write_bytes(snapshot["inputs.json"])
    with monkeypatch.context() as scoped:
        scoped.setattr(preparation_package, "MAX_TOTAL_BYTES", 1)
        rejected("PREPARATION_PACKAGE_LIMIT_EXCEEDED")
    assert {path.name: path.read_bytes() for path in output.iterdir()} == snapshot


def test_once_read_capture_survives_source_mutation(tmp_path, monkeypatch):
    plan, _, inputs = _sources(tmp_path)
    expected = synthetic_prepare.build_report(plan, inputs)
    paths = [*plan.iterdir(), inputs]
    originals = {path: path.read_bytes() for path in paths}
    reads = []
    original_open = Path.open

    @contextmanager
    def mutate_after_read(path, mode="r", *rest, **kwargs):
        with original_open(path, mode, *rest, **kwargs) as stream:
            yield stream
        if mode == "rb" and path in originals:
            reads.append(path)
            with original_open(path, "wb") as target:
                target.write(b"changed after snapshot capture")

    output = tmp_path / "captured"
    with monkeypatch.context() as scoped:
        scoped.setattr(Path, "open", mutate_after_read)
        preparation_package.export_package(plan, inputs, output)
    assert len(reads) == 5 and set(reads) == set(paths)
    verified = preparation_package.verify_package(output)
    assert verified["report"] == expected
    assert (output / "inputs.json").read_bytes() == originals[inputs]
    for name, saved in preparation_package.PLAN_NAMES.items():
        assert (output / saved).read_bytes() == originals[plan / name]


def test_existing_linked_destinations_invalid_flags_and_partial_write_preserved(
    tmp_path, monkeypatch, capsys,
):
    plan, _, inputs = _sources(tmp_path)
    output = tmp_path / "existing"
    output.mkdir()
    sentinel = output / "sentinel"
    sentinel.write_bytes(b"preserve this")
    sources = {path: path.read_bytes() for path in (inputs, *plan.iterdir())}

    def rejected(args, code):
        assert cli.main(args) == 2
        captured = capsys.readouterr()
        assert captured.out == "" and captured.err == f"error: {code}\n"

    rejected(_args(plan, inputs, output), "OUTPUT_PATH_EXISTS")
    assert sentinel.read_bytes() == b"preserve this"
    rejected(_args(plan, inputs, plan / "new-delivery"), "OUTPUT_INSIDE_SOURCE_PLAN")
    assert not (plan / "new-delivery").exists()
    rejected(_args(plan, inputs, plan / ".." / plan.name / "nested"), "OUTPUT_INSIDE_SOURCE_PLAN")
    assert not (plan / "nested").exists()
    with monkeypatch.context() as scoped:
        scoped.setattr(preparation_package, "export_package", lambda *a: (
            (_ for _ in ()).throw(AssertionError("Invalid flags reject before IO"))
        ))
        scoped.setattr(preparation_package, "verify_package", lambda *a: (
            (_ for _ in ()).throw(AssertionError("Invalid flags reject before IO"))
        ))
        for args in (
            ["research", "prepare-package"],
            ["research", "prepare-package", "--package", str(plan)],
            ["research", "prepare-package", "--verify", str(output), "--inputs", str(inputs)],
            [*_args(plan, inputs, tmp_path / "invalid"), "--verify", str(output)],
            [*_args(plan, inputs, tmp_path / "invalid"), "--execute"],
        ):
            rejected(args, "INVALID_ARGUMENTS")
    assert not (tmp_path / "invalid").exists()
    original_lstat = Path.lstat

    class Reparse:
        st_mode = 0o40755
        st_file_attributes = 0x400

    linked = tmp_path / "linked"
    linked.mkdir()
    with monkeypatch.context() as scoped:
        scoped.setattr(Path, "lstat", lambda path, **kw: (
            Reparse() if path == linked else original_lstat(path, **kw)
        ))
        rejected(_args(plan, inputs, linked / "new"), "LINKED_PREPARATION_PACKAGE_PATH")
    assert not (linked / "new").exists()
    partial = tmp_path / "partial"
    original_open = Path.open

    def fail_write(path, mode="r", *rest, **kwargs):
        if path == partial / "preparation.json" and mode == "xb":
            raise OSError("injected write failure")
        return original_open(path, mode, *rest, **kwargs)

    with monkeypatch.context() as scoped:
        scoped.setattr(Path, "open", fail_write)
        rejected(_args(plan, inputs, partial), "PREPARATION_PACKAGE_WRITE_FAILED")
    assert partial.is_dir() and list(partial.iterdir())
    partial_snapshot = {path: path.read_bytes() for path in partial.iterdir()}
    rejected(_args(plan, inputs, partial), "OUTPUT_PATH_EXISTS")
    assert {path: path.read_bytes() for path in partial.iterdir()} == partial_snapshot
    assert {path: path.read_bytes() for path in sources} == sources
