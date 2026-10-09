"""Original plan provenance, declared overlap and fail-closed batch boundaries."""

import hashlib
import json
import socket
from contextlib import contextmanager
from pathlib import Path

import duckdb
import pytest

from ashare_research import cli
from ashare_research.mechanism import execution, pipeline
from ashare_research.tools import research_hypothesis_batch as batch
from ashare_research.tools.research_plan import MAX_INPUT_BYTES, PlanError, build_report

EXAMPLE = Path(__file__).resolve().parents[1] / "docs/examples/m4_hypothesis.json"


def _sources(tmp_path):
    first, second = tmp_path / "first.json", tmp_path / "second.json"
    first.write_bytes(EXAMPLE.read_bytes())
    document = json.loads(first.read_bytes())
    document["hypothesis_id"] = "SYNTH_DAILY_CONTROLLED_002"
    document["target"]["series_id"] = "SYNTH_TARGET_B"
    document["factor"]["factor_id"] = "SYNTH_CONTROL_1"
    document["controls"] = ["SYNTH_CONTROL_2", "SYNTH_CONTROL_3"]
    document["development"]["start"] = "2021-01-01"
    document["data_quality_gates"]["coverage_gate"] = "0.98"
    document["universe"]["universe_id"] = "SYNTH_UNIVERSE_B"
    second.write_text(json.dumps(document), encoding="utf-8")
    return first, second


def _args(first, second):
    return [
        "research", "plan-batch", "--hypothesis", str(first),
        "--hypothesis", str(second),
    ]


def test_original_reports_role_overlap_and_unmerged_quality_scopes(tmp_path, monkeypatch, capsys):
    first, second = _sources(tmp_path)
    before = {path: path.read_bytes() for path in (first, second)}
    expected = {
        report["contract"]["hypothesis_id"]: report
        for report in (build_report(first), build_report(second))
    }

    def forbidden(*args, **kwargs):
        raise AssertionError("No network, database, service or execution allowed")

    for name in ("load_config", "setup_logging", "_create_service"):
        monkeypatch.setattr(cli, name, forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(duckdb, "connect", forbidden)
    monkeypatch.setattr(pipeline, "run_synthetic_pipeline", forbidden)
    monkeypatch.setattr(execution, "execute_bounded_analysis", forbidden)
    args = _args(first, second)
    assert cli.main([*args, "--json"]) == 0
    captured = capsys.readouterr()
    assert captured.err == ""
    report = json.loads(captured.out)
    assert report["schema"] == batch.SCHEMA
    assert report["sources"] == expected
    assert report["counts"] == {
        "hypotheses": 2, "role_requirements": 8,
        "declared_series": 6, "shared_declared_series": 2,
    }
    assert list(report["sources"]) == sorted(expected)
    assert not any(report["boundary"].values())
    indexed = {group["series_id"]: group for group in report["series_groups"]}
    assert list(indexed) == sorted(indexed)
    assert indexed["SYNTH_CONTROL_1"]["shared_declared_series"]
    assert indexed["SYNTH_CONTROL_1"]["role_independent_declarations_differ"]
    assert indexed["SYNTH_CONTROL_2"]["shared_declared_series"]
    assert not indexed["SYNTH_CONTROL_2"]["role_independent_declarations_differ"]
    assert not indexed["SYNTH_TARGET_A"]["shared_declared_series"]
    windows, gates, universes = set(), set(), set()
    for group in report["series_groups"]:
        for use in group["uses"]:
            original = expected[use["hypothesis_id"]]["plan"]
            index = use["requirement_index"]
            assert use["requirement"] == original["dataset_requirements"]["requirements"][index]
            assert use["source_plan_digest"] == original["plan_digest"]
            assert use["sample_plan"] == original["sample_plan"]
            assert use["universe_requirement"] == (
                original["dataset_requirements"]["universe_requirement"]
            )
            windows.add(use["sample_plan"]["window"]["start"])
            gates.add(use["sample_plan"]["coverage_gate"])
            universes.add(use["universe_requirement"]["universe_id"])
    assert windows == {"2020-01-01", "2021-01-01"}
    assert gates == {"0.99", "0.98"}
    assert universes == {"SYNTH_UNIVERSE_A", "SYNTH_UNIVERSE_B"}
    for source in report["sources"].values():
        assert source["plan"]["source_contract_digest"] == source["contract"]["contract_digest"]
        assert not any(source["boundary"].values())
    assert batch.build_inventory([second, first]) == report
    assert cli.main(_args(second, first) + ["--json"]) == 0
    assert json.loads(capsys.readouterr().out) == report
    assert cli.main(args) == 0
    markdown = capsys.readouterr().out
    assert markdown == batch.render_markdown(report)
    assert '"coverage_gate": "0.98"' in markdown and '"coverage_gate": "0.99"' in markdown
    assert '"execution_authorized": false' in markdown
    assert "not verified shared or reusable data" in markdown
    assert all(path.read_bytes() == raw for path, raw in before.items())
    assert str(tmp_path) not in json.dumps(report)
    assert cli.main(["research", "--help"]) == 0
    assert "plan-batch" in capsys.readouterr().out


def test_reformatting_and_single_captured_read_after_mutation(tmp_path, monkeypatch):
    first, second = _sources(tmp_path)
    original = batch.build_inventory([first, second])
    document = json.loads(second.read_bytes())
    second.write_text(json.dumps(document, sort_keys=True, indent=2), encoding="utf-8")
    reformatted = batch.build_inventory([first, second])
    second_id = document["hypothesis_id"]
    assert original["sources"][second_id]["source_file_sha256"] != (
        reformatted["sources"][second_id]["source_file_sha256"]
    )
    for section in ("config", "contract", "plan"):
        assert original["sources"][second_id][section] == reformatted["sources"][second_id][section]
    assert original["series_groups"] == reformatted["series_groups"]
    captured = {path: path.read_bytes() for path in (first, second)}
    original_open = Path.open
    reads = []

    @contextmanager
    def mutate_after_read(path, mode="r", *args, **kwargs):
        with original_open(path, mode, *args, **kwargs) as stream:
            yield stream
        if path in captured and mode == "rb":
            reads.append(path)
            with original_open(path, "wb") as stream:
                stream.write(b"mutated after source capture")

    monkeypatch.setattr(Path, "open", mutate_after_read)
    result = batch.build_inventory([second, first])
    assert reads == [second, first]
    assert result == reformatted
    for source in result["sources"].values():
        assert source["source_file_sha256"] in {
            hashlib.sha256(raw).hexdigest() for raw in captured.values()
        }


def test_duplicates_bad_counts_and_options_rejected_without_partial_result(
    tmp_path, monkeypatch, capsys,
):
    first, second = _sources(tmp_path)
    second.write_bytes(first.read_bytes())
    assert cli.main(_args(first, second) + ["--json"]) == 2
    captured = capsys.readouterr()
    assert captured.out == "" and captured.err == "error: DUPLICATE_HYPOTHESIS_ID\n"

    def forbidden(*args, **kwargs):
        raise AssertionError("Invalid options/count must fail before source load")

    monkeypatch.setattr(batch, "build_report", forbidden)
    too_many = ["research", "plan-batch"]
    for _ in range(batch.MAX_HYPOTHESES + 1):
        too_many.extend(["--hypothesis", str(first)])
    assert cli.main(too_many) == 2
    captured = capsys.readouterr()
    assert captured.out == "" and captured.err == "error: INVALID_HYPOTHESIS_COUNT\n"
    for args in (
        ["research", "plan-batch"],
        [*_args(first, second), "--execute"],
        ["research", "plan-batch", "--hypothesis", ""],
        [*_args(first, second), "--hyp", str(first)],
    ):
        assert cli.main(args) == 2
        captured = capsys.readouterr()
        assert captured.out == "" and captured.err == "error: INVALID_ARGUMENTS\n"
    with pytest.raises(PlanError, match="INVALID_HYPOTHESIS_COUNT"):
        batch.build_inventory([])


@pytest.mark.parametrize("side", [0, 1])
def test_invalid_source_fails_entire_inventory(tmp_path, capsys, side):
    paths = _sources(tmp_path)
    bad = paths[side]
    for payload, code in (
        (b"[]", "INVALID_HYPOTHESIS_ROOT"),
        (b'{"x":1,"x":2}', "DUPLICATE_JSON_KEY"),
        (b'{"x":Infinity}', "NONFINITE_JSON_NUMBER"),
        (b"{", "INVALID_HYPOTHESIS_JSON"),
        (b"\xff", "INVALID_HYPOTHESIS_JSON"),
        (b" " * (MAX_INPUT_BYTES + 1), "HYPOTHESIS_TOO_LARGE"),
    ):
        bad.write_bytes(payload)
        assert cli.main([*_args(*paths), "--json"]) == 2
        captured = capsys.readouterr()
        assert captured.out == "" and captured.err == f"error: {code}\n"
    document = json.loads(EXAMPLE.read_bytes())
    document["hypothesis_id"] = "SYNTH_BAD_REAL_POLICY"
    document["target"]["identity_policy"] = "SECURITY_LEVEL_IDENTITY_V1"
    bad.write_text(json.dumps(document), encoding="utf-8")
    assert cli.main([*_args(*paths), "--json"]) == 2
    captured = capsys.readouterr()
    assert captured.out == "" and captured.err == "error: INVALID_IDENTITY_POLICY\n"
    bad.unlink()
    assert cli.main([*_args(*paths), "--json"]) == 2
    captured = capsys.readouterr()
    assert captured.out == "" and captured.err == "error: HYPOTHESIS_READ_FAILED\n"


def test_output_limits_full_envelope_and_markdown_escaping(tmp_path, monkeypatch, capsys):
    first, second = _sources(tmp_path)
    result = batch.build_inventory([first, second])
    source_bytes = sum(len(batch._json(source).encode()) for source in result["sources"].values())
    assert source_bytes < len(batch._json(result).encode())
    with monkeypatch.context() as context:
        context.setattr(batch, "MAX_OUTPUT_BYTES", 1)
        assert cli.main([*_args(first, second), "--json"]) == 2
        captured = capsys.readouterr()
        assert captured.out == "" and captured.err == "error: BATCH_TOO_LARGE\n"
    with monkeypatch.context() as context:
        context.setattr(batch, "MAX_OUTPUT_BYTES", source_bytes + 1)
        assert cli.main(_args(first, second)) == 2
        captured = capsys.readouterr()
        assert captured.out == "" and captured.err == "error: BATCH_TOO_LARGE\n"
    with monkeypatch.context() as context:
        context.setattr(batch, "render_markdown", lambda report: "x" * (batch.MAX_OUTPUT_BYTES + 1))
        assert cli.main(_args(first, second)) == 2
        captured = capsys.readouterr()
        assert captured.out == "" and captured.err == "error: BATCH_TOO_LARGE\n"
    text = batch._cell("[link](https://invalid.example)|<img>*_`\\\n")
    assert "\\[link\\]" in text and "\\|" in text and "\\*" in text
    assert "<img>" not in text and "&lt;img&gt;" in text


@pytest.mark.parametrize("count", [1, batch.MAX_HYPOTHESES])
def test_minimum_and_maximum_allowed_batches_preserve_all_plans(tmp_path, count):
    paths = []
    document = json.loads(EXAMPLE.read_bytes())
    for index in range(count):
        document["hypothesis_id"] = f"SYNTH_BOUNDARY_{index:02d}"
        path = tmp_path / f"{index:02d}.json"
        path.write_text(json.dumps(document), encoding="utf-8")
        paths.append(path)
    report = batch.build_inventory(list(reversed(paths)))
    assert report["counts"] == {
        "hypotheses": count, "role_requirements": 4 * count, "declared_series": 4,
        "shared_declared_series": 4 if count > 1 else 0,
    }
    assert len(report["sources"]) == count
    for group in report["series_groups"]:
        assert len(group["uses"]) == count
        assert not group["role_independent_declarations_differ"]
    assert not any(report["boundary"].values())
