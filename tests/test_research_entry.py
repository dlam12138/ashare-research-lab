"""Acceptance coverage for the unified offline research entry.

Four cases exercise the real ``ashare-research research`` entry: (1) discovery, help, safe
dispatch and unchanged legacy behaviour; (2) the real report and synthetic flows with forbidden
legacy-initialization guards, comparing the delegated bytes against a direct ``main(argv)`` run;
(3) actual dated facts and metric replay on the committed PIT snapshot, including future-fact
exclusion and the empty-window limit; (4) a real cross-process export, existing-output-path
safety, sanitized tool failures and rejection of global ``--config``/``--debug``.

Expected results come from the existing tools' own public output: the tests compare the delegated
run with a direct ``main(argv)`` run rather than recomputing any formula.  Nothing here reads the
network or a caller database, and nothing writes into the repository.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from ashare_research import cli, synthetic_demo
from ashare_research.mechanism.execution import INTERPRETATION_BOUNDARY
from ashare_research.mechanism.pipeline import PIPELINE_SCHEMA_VERSION, PIPELINE_STATE
from ashare_research.tools import (
    pit_fact_explorer,
    pit_metric_replay,
    research_entry,
    value_research_bundle,
)

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
CLI_MODULE = "ashare_research.cli"
FACTS_MODULE = "ashare_research.tools.pit_fact_explorer"
METRICS_MODULE = "ashare_research.tools.pit_metric_replay"

NP_CONCEPT = "net_profit_attributable_to_parent"
PERIOD_2023 = "2023-12-31"
ORIGINAL_NP_2023 = "16114400.000000000000"
RESTATED_NP_2023 = "16141400.000000000000"
ORIGINAL_NP_2023_FACT_ID = "d9b223cb06f96359793d28cac41a30c068834b4979c358f48cca6af99734c2f4"
RESTATED_NP_2023_FACT_ID = "0263db7efe1b96fe00743e64af87eea76d75dce1365941139e9a87fe09be4129"

_CHILD_ENVIRONMENT = dict(os.environ)
_CHILD_ENVIRONMENT["PYTHONPATH"] = str(SRC)
_CHILD_ENVIRONMENT["PYTHONIOENCODING"] = "utf-8"


def _run_module(module: str, *arguments: str, cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", module, *arguments],
        cwd=cwd,
        env=_CHILD_ENVIRONMENT,
        capture_output=True,
        check=False,
    )


def _stdout(completed: subprocess.CompletedProcess) -> str:
    assert completed.returncode == 0, completed.stderr.decode("utf-8", "replace")
    return completed.stdout.decode("utf-8")


def test_discovery_help_safe_dispatch_and_legacy_preservation(
    tmp_path: Path, monkeypatch, capsys,
) -> None:
    root_help = _run_module(CLI_MODULE, "--help", cwd=tmp_path)
    root_text = _stdout(root_help)
    assert "research" in root_text
    assert "统一离线研究入口" in root_text
    assert "init-db" in root_text and "build-value-facts" in root_text
    assert root_help.stderr == b""

    unified_help = _run_module(CLI_MODULE, "research", "--help", cwd=tmp_path)
    unified_text = _stdout(unified_help)
    for command, module in (
        ("report", "value_research_bundle"),
        ("facts", "pit_fact_explorer"),
        ("metrics", "pit_metric_replay"),
        ("demo", "synthetic_demo"),
    ):
        assert f"ashare-research research {command} --help" in unified_text
        assert module in unified_text
    assert "--as-of" in unified_text
    assert "不联网" in unified_text
    assert "--config" in unified_text and "退出码 2 拒绝" in unified_text
    assert unified_help.stderr == b""

    # The no-argument form prints the same unified help through both public entries.
    assert cli.main(["research"]) == 0
    assert capsys.readouterr().out == unified_text
    assert research_entry.main([]) == 0
    assert capsys.readouterr().out == unified_text

    for command, marker in (
        ("report", "--verify"),
        ("facts", "--compare-with"),
        ("metrics", "--metric"),
        ("demo", "--json"),
    ):
        completed = _run_module(CLI_MODULE, "research", command, "--help", cwd=tmp_path)
        assert marker in _stdout(completed)
        assert completed.stderr == b""

    unknown = _run_module(CLI_MODULE, "research", "bogus", cwd=tmp_path)
    assert unknown.returncode == 2
    assert unknown.stdout == b""
    unknown_error = unknown.stderr.decode("utf-8")
    assert "unknown research command 'bogus'" in unknown_error
    assert "Traceback" not in unknown_error

    legacy_unknown = _run_module(CLI_MODULE, "bogus", cwd=tmp_path)
    assert legacy_unknown.returncode == 2
    assert legacy_unknown.stdout == b""
    assert b"invalid choice" in legacy_unknown.stderr

    # Legacy commands keep working after the early research dispatch.
    config = {
        "storage": {
            "duckdb_path": str(tmp_path / "legacy.duckdb"),
            "raw_dir": str(tmp_path / "raw"),
            "parquet_dir": str(tmp_path / "parquet"),
        }
    }
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(cli, "load_config", lambda path=None: config)
    assert cli.main(["init-db"]) == 0
    legacy_run = capsys.readouterr()
    assert f"DuckDB initialized: {config['storage']['duckdb_path']}" in legacy_run.out
    assert legacy_run.err == ""

    # The legacy service_factory injection path still reaches build-value-facts unchanged.
    factory_calls: list[dict] = []

    def factory(loaded_config: dict):
        factory_calls.append(loaded_config)
        raise RuntimeError("service factory reached")

    monkeypatch.setattr(cli, "load_config", lambda path=None: {"storage": {}})
    assert cli.main(
        ["build-value-facts", "601857.SH", "--start-year", "2025", "--end-year", "2025"],
        service_factory=factory,
    ) == 1
    assert len(factory_calls) == 1
    assert "service factory reached" in capsys.readouterr().err


def test_report_and_synthetic_flows_skip_legacy_initialization(
    tmp_path: Path, monkeypatch, capsys,
) -> None:
    def forbidden(*args, **kwargs):
        raise AssertionError("legacy CLI initialization must not run for research")

    monkeypatch.setattr(cli, "load_config", forbidden)
    monkeypatch.setattr(cli, "setup_logging", forbidden)
    monkeypatch.setattr(cli, "_create_service", forbidden)

    assert cli.main(["research", "report", "--json"]) == 0
    delegated_report = capsys.readouterr().out
    assert cli.main(["research", "demo", "--json"]) == 0
    delegated_demo = capsys.readouterr().out

    # Direct existing main() runs, same public flows, for byte-level comparison.
    assert value_research_bundle.main(["--json"]) == 0
    direct_report = capsys.readouterr().out
    assert synthetic_demo.main(["--json"]) == 0
    direct_demo = capsys.readouterr().out

    assert delegated_report == direct_report
    assert delegated_demo == direct_demo

    payload = json.loads(delegated_report)
    assert payload["schema"] == value_research_bundle.SCHEMA_ID
    assert payload["symbol"] == "601857.SH"
    assert payload["compilation"]["unified_pit_as_of_query"] is False

    demo_payload = json.loads(delegated_demo)
    assert demo_payload["metadata"]["pipeline_state"] == PIPELINE_STATE
    assert demo_payload["metadata"]["pipeline_schema_version"] == PIPELINE_SCHEMA_VERSION
    assert demo_payload["metadata"]["interpretation_boundary"] == INTERPRETATION_BOUNDARY

    # A genuine child process reproduces exactly the direct main() bytes.
    child_report = _run_module(CLI_MODULE, "research", "report", "--json", cwd=tmp_path)
    assert child_report.returncode == 0 and child_report.stderr == b""
    assert child_report.stdout == direct_report.encode("utf-8")

    child_demo = _run_module(CLI_MODULE, "research", "demo", "--json", cwd=tmp_path)
    assert child_demo.returncode == 0 and child_demo.stderr == b""
    assert child_demo.stdout == direct_demo.encode("utf-8")


def test_dated_facts_and_metric_replay_match_direct_main(tmp_path: Path, capsys) -> None:
    facts_arguments = (
        "--as-of", "2024-03-31", "--compare-with", "2025-03-31",
        "--concept", NP_CONCEPT, "--period-end", PERIOD_2023, "--json",
    )
    child_facts = _run_module(CLI_MODULE, "research", "facts", *facts_arguments, cwd=tmp_path)
    direct_facts = _run_module(FACTS_MODULE, *facts_arguments, cwd=tmp_path)
    assert child_facts.returncode == direct_facts.returncode == 0
    assert child_facts.stdout == direct_facts.stdout
    assert child_facts.stderr == direct_facts.stderr == b""

    payload = json.loads(child_facts.stdout)
    assert payload["schema"] == pit_fact_explorer.REPORT_SCHEMA
    assert payload["symbol"] == "601857.SH"
    assert payload["selection_count"] == 1
    selection = payload["selections"][0]
    assert selection["fact_id"] == ORIGINAL_NP_2023_FACT_ID
    assert selection["value_decimal"] == ORIGINAL_NP_2023
    assert selection["available_at"] == "2024-03-26"
    assert selection["fact_version"] == 1
    assert selection["restatement_version"] == "original"
    assert selection["available_at"] <= payload["request"]["as_of"]
    after = payload["compare_selections"][0]
    assert after["fact_id"] == RESTATED_NP_2023_FACT_ID
    assert after["value_decimal"] == RESTATED_NP_2023
    assert after["available_at"] == "2025-03-31"
    assert after["available_at"] <= payload["request"]["compare_with"]

    # One day before the restatement became available the future fact is not selected.
    one_day_before = (
        "--as-of", "2025-03-30", "--concept", NP_CONCEPT, "--period-end", PERIOD_2023, "--json",
    )
    assert cli.main(["research", "facts", *one_day_before]) == 0
    before = json.loads(capsys.readouterr().out)
    assert before["selection_count"] == 1
    assert before["selections"][0]["fact_id"] == ORIGINAL_NP_2023_FACT_ID
    assert before["selections"][0]["available_at"] <= "2025-03-30"
    assert RESTATED_NP_2023 not in json.dumps(before, ensure_ascii=False)

    metrics_arguments = (
        "--as-of", "2024-03-31", "--compare-with", "2025-03-31", "--year", "2023", "--json",
    )
    assert cli.main(["research", "metrics", *metrics_arguments]) == 0
    delegated_metrics = capsys.readouterr()
    assert pit_metric_replay.main(list(metrics_arguments)) == 0
    direct_metrics = capsys.readouterr()
    assert delegated_metrics.out == direct_metrics.out
    assert delegated_metrics.err == direct_metrics.err == ""

    report = json.loads(delegated_metrics.out)
    for block_name, date in (("as_of", "2024-03-31"), ("compare_with", "2025-03-31")):
        block = report[block_name]
        index = block["selected_fact_index"]
        assert index and block["selection_count"] == len(index)
        assert all(row["available_at"] <= date for row in index)
    assert report["as_of"]["selection_count"] == 16
    assert report["compare_with"]["selection_count"] == 21
    assert {row["status"] for row in report["as_of"]["records"]} == {"computed"}
    assert report["comparison"]["states"]["value_changed"] == 7

    # Before the earliest available input the PIT selection is honestly empty, not defaulted.
    empty_window = ("--as-of", "2022-03-31", "--year", "2021", "--json")
    assert cli.main(["research", "metrics", *empty_window]) == 0
    empty = json.loads(capsys.readouterr().out)
    assert empty["as_of"]["selection_count"] == 0
    assert empty["as_of"]["selected_fact_index"] == []
    assert all(
        row["status"] == "missing_input" and row["value"] is None
        for row in empty["as_of"]["records"]
    )
    assert all(row["input_available_at_bound"] is None for row in empty["as_of"]["records"])


def test_export_existing_path_safety_and_rejected_options(tmp_path: Path, capsys) -> None:
    arguments = ("--as-of", "2024-03-31", "--compare-with", "2025-03-31", "--year", "2023")
    delegated_dir = tmp_path / "unified-export"
    direct_dir = tmp_path / "direct-export"

    delegated = _run_module(
        CLI_MODULE, "research", "metrics", *arguments,
        "--output", str(delegated_dir), cwd=tmp_path,
    )
    direct = _run_module(METRICS_MODULE, *arguments, "--output", str(direct_dir), cwd=tmp_path)
    assert delegated.returncode == direct.returncode == 0
    assert delegated.stdout == direct.stdout
    assert delegated.stderr == direct.stderr == b""
    assert delegated.stdout.decode("utf-8").startswith("exported 2 managed files, ")

    names = (*pit_metric_replay.MANAGED_FILE_NAMES, pit_metric_replay.MANIFEST_NAME)
    for name in names:
        assert (delegated_dir / name).read_bytes() == (direct_dir / name).read_bytes()
    manifest = json.loads(
        (delegated_dir / pit_metric_replay.MANIFEST_NAME).read_text(encoding="utf-8")
    )
    assert manifest["request"]["as_of"] == "2024-03-31"
    assert manifest["boundaries"]["current_timestamp_recorded"] is False
    assert manifest["boundaries"]["network_used"] is False
    assert manifest["boundaries"]["metric_database_written"] is False

    # An existing output path is rejected before anything is written and stays untouched.
    sentinel_dir = tmp_path / "existing"
    sentinel_dir.mkdir()
    sentinel = sentinel_dir / "keep.txt"
    sentinel.write_bytes(b"foreign artifact\n")
    rejected = _run_module(
        CLI_MODULE, "research", "metrics", *arguments, "--output", str(sentinel_dir), cwd=tmp_path,
    )
    assert rejected.returncode == 2
    assert rejected.stdout == b""
    assert rejected.stderr == b"error: OUTPUT_PATH_EXISTS\n"
    assert sentinel.read_bytes() == b"foreign artifact\n"
    assert sorted(item.name for item in sentinel_dir.iterdir()) == ["keep.txt"]

    # Sanitized failures still come from the tools' own implementations and exit codes.
    assert cli.main(["research", "facts", "--as-of", "2024/03/31"]) == 2
    captured = capsys.readouterr()
    assert captured.out == "" and captured.err == "error: INVALID_AS_OF_DATE\n"

    assert cli.main(["research", "metrics", "--as-of", "2024-03-31", "--year", "2019"]) == 2
    captured = capsys.readouterr()
    assert captured.out == "" and captured.err == "error: INVALID_YEAR\n"

    assert cli.main(["research", "report", "--not-an-option"]) == 1
    captured = capsys.readouterr()
    assert captured.out == "" and captured.err == "error: UNEXPECTED_FAILURE\n"

    # Global --config/--debug cannot apply to the offline entry: reject, never ignore silently.
    config_path = str(tmp_path / "config.yaml")
    for global_arguments in (
        ["--config", config_path, "research", "report"],
        ["--config=" + config_path, "research", "report"],
        ["--conf", config_path, "research", "report"],
        ["--debug", "research", "report"],
        ["research", "--config", config_path, "report"],
        ["research", "report", "--config", config_path],
    ):
        assert cli.main(global_arguments) == 2, global_arguments
        captured = capsys.readouterr()
        assert captured.out == "", global_arguments
        assert "cannot be combined with research" in captured.err, global_arguments
        assert "Traceback" not in captured.err

    top_level = _run_module(
        CLI_MODULE, "--config", config_path, "research", "report", cwd=tmp_path,
    )
    assert top_level.returncode == 2
    assert top_level.stdout == b""
    assert b"cannot be combined with research" in top_level.stderr
