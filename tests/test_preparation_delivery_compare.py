"""Saved preparation comparisons retain exact verified diagnostics and boundaries."""

import hashlib
import json
import socket
import zipfile
from contextlib import contextmanager
from pathlib import Path

import duckdb
from test_preparation_diagnostics import EXAMPLES, _sources, _write_invented

from ashare_research import cli
from ashare_research.mechanism import execution, pipeline
from ashare_research.mechanism.model_digest import canonical_digest
from ashare_research.tools import preparation_archive as archive
from ashare_research.tools import preparation_compare as original
from ashare_research.tools import preparation_delivery_compare as compare
from ashare_research.tools import preparation_package as package
from ashare_research.tools import research_plan, research_plan_package, synthetic_prepare


def _pair(tmp_path):
    plan, _, right_input = _sources(tmp_path)
    left_input = tmp_path / "before.json"
    document = json.loads(right_input.read_bytes())
    document["observations"][0]["value"] = None
    document["observations"][0]["available_on"] = None
    _write_invented(document, left_input)
    left, right = tmp_path / "before", tmp_path / "after"
    package.export_package(plan, left_input, left)
    package.export_package(plan, right_input, right)
    left_zip, right_zip = tmp_path / "before.zip", tmp_path / "after.zip"
    archive.export_archive(left, left_zip)
    archive.export_archive(right, right_zip)
    return plan, left_input, right_input, left, right, left_zip, right_zip


def _args(left, right, *, left_archive=False, right_archive=False):
    return [
        "research", "prepare-delivery-compare",
        "--left-archive" if left_archive else "--left", str(left),
        "--right-archive" if right_archive else "--right", str(right), "--json",
    ]


def test_public_all_transports_exact_legacy_report_reversal_and_offline(
    tmp_path, monkeypatch, capsys,
):
    plan, left_input, right_input, left, right, left_zip, right_zip = _pair(tmp_path)
    expected = original.build_report(plan, left_input, right_input)
    sources = [left_input, right_input, left_zip, right_zip, *plan.iterdir(),
               *left.iterdir(), *right.iterdir()]
    snapshot = {path: path.read_bytes() for path in sources}

    def forbidden(*args, **kwargs):
        raise AssertionError("No extra input reads, services, extraction, writes or statistics")

    for name in ("load_config", "setup_logging", "_create_service"):
        monkeypatch.setattr(cli, name, forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(duckdb, "connect", forbidden)
    monkeypatch.setattr(pipeline, "run_synthetic_pipeline", forbidden)
    monkeypatch.setattr(execution, "execute_bounded_analysis", forbidden)
    monkeypatch.setattr(zipfile.ZipFile, "extract", forbidden)
    monkeypatch.setattr(zipfile.ZipFile, "extractall", forbidden)
    monkeypatch.setattr(Path, "mkdir", forbidden)
    monkeypatch.setattr(synthetic_prepare, "build_report", forbidden)
    for before, after, la, ra in (
        (left, right, False, False), (left, right_zip, False, True),
        (left_zip, right, True, False), (left_zip, right_zip, True, True),
    ):
        args = _args(before, after, left_archive=la, right_archive=ra)
        assert cli.main(args) == 0
        captured = capsys.readouterr()
        assert captured.err == "" and json.loads(captured.out) == expected
    assert expected["before"]["status"] == "REJECTED_QUALITY"
    assert expected["before"]["matrix_identity"] is None
    assert expected["after"]["status"] == "READY_SYNTHETIC"
    assert expected["before"]["quality"]["coverage_numerator"] == 3
    assert expected["after"]["quality"]["coverage_numerator"] == 4
    assert expected["counts"]["became_valid_cells"] == 1
    assert expected["counts"]["compared_cells"] == 16
    assert not any(value for key, value in expected["boundary"].items()
                   if key not in ("synthetic_observations_read", "outcome_read"))
    assert "value" not in expected["changes"][0]["after"]
    assert cli.main(_args(left, right)[:-1]) == 0
    assert capsys.readouterr().out == compare.render_markdown(expected)
    assert "--left-inputs" not in compare.render_markdown(expected)
    reverse = compare.build_report(right_zip, left, left_archive=True)
    assert reverse["counts"]["became_invalid_cells"] == 1
    assert reverse["changes"][0]["before"] == expected["changes"][0]["after"]
    assert {path: path.read_bytes() for path in sources} == snapshot


def test_format_equivalence_metadata_and_empty_inputs_keep_original_semantics(tmp_path):
    plan, _, inputs, _, ready, _, _ = _pair(tmp_path)
    raw = inputs.read_bytes()
    document = json.loads(raw)
    document["observations"].reverse()
    formatted_input = tmp_path / "formatted.json"
    formatted_input.write_text(json.dumps(document, sort_keys=True), encoding="utf-8")
    formatted = tmp_path / "formatted"
    package.export_package(plan, formatted_input, formatted)
    equivalent = compare.build_report(ready, formatted)
    assert equivalent == original.build_report(plan, inputs, formatted_input)
    assert equivalent["classification"] == "CANONICALLY_EQUIVALENT_INPUTS"
    assert equivalent["changes"] == [] and equivalent["counts"]["unchanged_cells"] == 16
    document = json.loads(raw)
    document["observations"][0]["value"] = "0.123"
    _write_invented(document, formatted_input)
    changed = tmp_path / "metadata"
    package.export_package(plan, formatted_input, changed)
    metadata = compare.build_report(ready, changed)
    assert metadata == original.build_report(plan, inputs, formatted_input)
    assert metadata["before"]["quality"] == metadata["after"]["quality"]
    assert metadata["counts"]["metadata_changed_cells"] == 1
    assert metadata["counts"]["became_valid_cells"] == 0
    document["observations"] = []
    _write_invented(document, formatted_input)
    empty = tmp_path / "empty"
    package.export_package(plan, formatted_input, empty)
    result = compare.build_report(empty, empty)
    assert result["classification"] == "IDENTICAL_INPUT_BYTES"
    assert not any(result["boundary"].values())
    assert result["before"]["quality"]["reason_counts"] == {"MISSING_OBSERVATION": 16}


def test_once_read_snapshot_handoff_and_identical_path_mode_reuse(tmp_path, monkeypatch):
    plan, left_input, right_input, left, right, left_zip, right_zip = _pair(tmp_path)
    expected = original.build_report(plan, left_input, right_input)
    expected_same = compare.build_report(right, right)
    files = {path: path.read_bytes() for path in left.iterdir()}
    files[right_zip] = right_zip.read_bytes()
    original_open = Path.open
    reads = []

    @contextmanager
    def mutate_after_read(path, mode="r", *rest, **kwargs):
        with original_open(path, mode, *rest, **kwargs) as stream:
            yield stream
        if mode == "rb" and path in files:
            reads.append(path)
            with original_open(path, "wb") as output:
                output.write(b"mutated after captured read")

    with monkeypatch.context() as scoped:
        scoped.setattr(Path, "open", mutate_after_read)
        assert compare.build_report(left, right_zip, right_archive=True) == expected
    assert len(reads) == 11 and set(reads) == set(files)
    for path, raw in files.items():
        path.write_bytes(raw)
    reads.clear()

    @contextmanager
    def counted(path, mode="r", *rest, **kwargs):
        with original_open(path, mode, *rest, **kwargs) as stream:
            yield stream
        if mode == "rb":
            reads.append(path)

    with monkeypatch.context() as scoped:
        scoped.setattr(Path, "open", counted)
        assert compare.build_report(right, right) == expected_same
        assert len(reads) == 10 and set(reads) == set(right.iterdir())
        reads.clear()
        assert compare.build_report(right_zip, right_zip, left_archive=True,
                                    right_archive=True) == expected_same
        assert reads == [right_zip]
        reads.clear()
        assert compare.build_report(left_zip, right_zip, left_archive=True,
                                    right_archive=True) == expected
        assert reads == [left_zip, right_zip]


def test_corrupt_forged_stale_sides_and_invalid_flags_fail_closed(tmp_path, monkeypatch, capsys):
    _, _, _, left, right, _, right_zip = _pair(tmp_path)
    snapshot = {path.name: path.read_bytes() for path in right.iterdir()}

    def rejected(args, code):
        assert cli.main(args) == 2
        captured = capsys.readouterr()
        assert captured.out == "" and captured.err == f"error: {code}\n"

    forged = dict(snapshot)
    report = json.loads(forged["preparation.json"])
    report["boundary"]["statistics_computed"] = True
    forged["preparation.json"] = json.dumps(report).encode()
    manifest = json.loads(forged["manifest.json"])
    entry = next(item for item in manifest["files"] if item["path"] == "preparation.json")
    entry["sha256"] = hashlib.sha256(forged["preparation.json"]).hexdigest()
    entry["byte_count"] = len(forged["preparation.json"])
    forged["manifest.json"] = json.dumps(manifest).encode()
    for name, raw in forged.items():
        (right / name).write_bytes(raw)
    rejected(_args(left, right), "PREPARATION_PACKAGE_MISMATCH")
    rejected(_args(right, left), "PREPARATION_PACKAGE_MISMATCH")
    right_zip.write_bytes(archive._encode(forged))
    rejected(_args(left, right_zip, right_archive=True), "PREPARATION_PACKAGE_MISMATCH")
    stale = dict(snapshot)
    document = json.loads(stale["inputs.json"])
    document["observations"][0]["value"] = "0.123"
    stale["inputs.json"] = json.dumps(document).encode()
    right_zip.write_bytes(archive._encode(stale))
    rejected(_args(right_zip, left, left_archive=True), "EVIDENCE_DIGEST_MISMATCH")
    right_zip.write_bytes(archive._encode(snapshot) + b"tail")
    rejected(_args(left, right_zip, right_archive=True), "PREPARATION_ARCHIVE_LAYOUT_INVALID")
    rejected(_args(left, left, right_archive=True), "PREPARATION_ARCHIVE_SOURCE_INVALID")
    with monkeypatch.context() as scoped:
        scoped.setattr(compare, "build_report", lambda *a, **kw: (
            (_ for _ in ()).throw(AssertionError("Invalid flags reject before IO"))
        ))
        for args in (
            ["research", "prepare-delivery-compare"],
            [*_args(left, right), "--left-archive", str(right_zip)],
            [*_args(left, right), "--output", "new"],
            [*_args(left, right), "--execute"],
            [*_args(left, right), "--left-inputs", "input.json"],
            ["research", "prepare-delivery-compare", "--left", str(left)],
        ):
            rejected(args, "INVALID_ARGUMENTS")


def test_individually_valid_changed_domain_plan_and_alias_reject(tmp_path, monkeypatch, capsys):
    plan, _, inputs, left, _, _, _ = _pair(tmp_path)

    def rejected(right, code):
        assert cli.main(_args(left, right)) == 2
        captured = capsys.readouterr()
        assert captured.out == "" and captured.err == f"error: {code}\n"

    changed_input = tmp_path / "changed.json"
    document = json.loads(inputs.read_bytes())
    domain = document["domain"]
    removed = domain["expected_dates"].pop(0)
    for key in ("calendar_evidence", "membership_evidence"):
        domain[key]["expected_dates"] = list(domain["expected_dates"])
        domain[key]["evidence_digest"] = canonical_digest({
            k: v for k, v in domain[key].items() if k != "evidence_digest"
        })
    document["observations"] = [row for row in document["observations"]
                                if row["trade_date"] != removed]
    _write_invented(document, changed_input)
    changed_domain = tmp_path / "changed-domain"
    package.export_package(plan, changed_input, changed_domain)
    assert package.verify_package(changed_domain)["report"]["dataset"]["quality"][
        "coverage_denominator"
    ] == 3
    rejected(changed_domain, "COMPARISON_DOMAIN_MISMATCH")
    hypothesis = json.loads((EXAMPLES / "m4_hypothesis.json").read_bytes())
    hypothesis["condition"]["threshold"] = "-0.02"
    hypothesis_path = tmp_path / "changed-hypothesis.json"
    hypothesis_path.write_text(json.dumps(hypothesis), encoding="utf-8")
    changed_plan = tmp_path / "changed-plan"
    research_plan_package.export_package(hypothesis_path, changed_plan)
    compiled = research_plan.build_report(hypothesis_path)
    document = json.loads(inputs.read_bytes())
    document["source_contract_digest"] = compiled["contract"]["contract_digest"]
    document["plan_digest"] = compiled["plan"]["plan_digest"]
    _write_invented(document, changed_input)
    changed = tmp_path / "changed-delivery"
    package.export_package(changed_plan, changed_input, changed)
    package.verify_package(changed)
    rejected(changed, "COMPARISON_PLAN_MISMATCH")
    alias = tmp_path / "alias"
    alias.mkdir()
    original_lstat = Path.lstat

    class Reparse:
        st_mode = 0o40755
        st_file_attributes = 0x400

    with monkeypatch.context() as scoped:
        scoped.setattr(Path, "resolve", lambda path, **kw: left)
        scoped.setattr(Path, "lstat", lambda path, **kw: (
            Reparse() if path == alias else original_lstat(path, **kw)
        ))
        rejected(alias, "LINKED_PREPARATION_PACKAGE_PATH")
