"""Acceptance coverage for the M2 PIT fact explorer.

Five cases cover the real fixed snapshot end to end: (1) a real PIT boundary one day before and
on 2025-03-31 plus the 2023 net-profit restatement, with exact source decimals and no future
facts; (2) the truthful empty window before 2022-04-01 and the on-boundary selection; (3)
sanitized rejection of unknown concepts, invalid dates, reversed comparison order and illegal
scope; (4) exact source values, original context/lineage metadata and honestly unresolved raw
parent facts; (5) a real portable, repeatable export that never overwrites an existing path and
fails before creating its output root.

Every value asserted here is read from the committed fixture at
``tests/fixtures/stage2g/canonical_fact_snapshot_v1``; nothing recomputes research, reads a
caller database or the network, or writes into the repository.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from ashare_research.tools import pit_fact_explorer as explorer

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
SNAPSHOT = ROOT / "tests" / "fixtures" / "stage2g" / "canonical_fact_snapshot_v1"
MODULE_NAME = "ashare_research.tools.pit_fact_explorer"

_CHILD_ENVIRONMENT = dict(os.environ)
_CHILD_ENVIRONMENT["PYTHONPATH"] = str(SRC)

ORIGINAL_NP_2023 = "16114400.000000000000"
RESTATED_NP_2023 = "16141400.000000000000"
ORIGINAL_NP_2023_FACT_ID = "d9b223cb06f96359793d28cac41a30c068834b4979c358f48cca6af99734c2f4"
RESTATED_NP_2023_FACT_ID = "0263db7efe1b96fe00743e64af87eea76d75dce1365941139e9a87fe09be4129"
RESTATED_REVENUE_2023_FACT_ID = (
    "1e15d297a93bb8d290dd7a9282fa14473ccc38b1f2d4927caf1007ec5b2fb3f8"
)
NP_CONCEPT = "net_profit_attributable_to_parent"
REVENUE_CONCEPT = "revenue"
PERIOD_2023 = "2023-12-31"


def _run_module(*arguments: str, cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", MODULE_NAME, *arguments],
        cwd=cwd,
        env=_CHILD_ENVIRONMENT,
        capture_output=True,
        check=False,
    )


def _stdout(completed: subprocess.CompletedProcess) -> str:
    assert completed.returncode == 0, completed.stderr.decode("utf-8", "replace")
    return completed.stdout.decode("utf-8")


def _json_run(*arguments: str, cwd: Path) -> dict[str, Any]:
    return json.loads(_stdout(_run_module(*arguments, cwd=cwd)))


def _fixture(name: str) -> Any:
    return json.loads((SNAPSHOT / name).read_text(encoding="utf-8"))


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def test_pit_boundary_and_2023_net_profit_restatement(tmp_path: Path) -> None:
    before = _json_run(
        "--as-of", "2025-03-30", "--concept", NP_CONCEPT, "--period-end", PERIOD_2023,
        "--json", cwd=tmp_path,
    )
    assert before["selection_count"] == 1
    original = before["selections"][0]
    assert original["fact_id"] == ORIGINAL_NP_2023_FACT_ID
    assert original["value_decimal"] == ORIGINAL_NP_2023
    assert original["available_at"] == "2024-03-26"
    assert original["fact_version"] == 1
    assert original["restatement_version"] == "original"
    assert original["unit"] == "万元"
    assert before["comparison"] is None

    on_boundary = _json_run(
        "--as-of", "2025-03-31", "--concept", NP_CONCEPT, "--period-end", PERIOD_2023,
        "--json", cwd=tmp_path,
    )
    assert on_boundary["selection_count"] == 1
    restated = on_boundary["selections"][0]
    assert restated["fact_id"] == RESTATED_NP_2023_FACT_ID
    assert restated["value_decimal"] == RESTATED_NP_2023
    assert restated["available_at"] == "2025-03-31"
    assert restated["fact_version"] == 2
    assert restated["restatement_version"] == "restated_1"
    assert restated["supersedes_fact_id"] == ORIGINAL_NP_2023_FACT_ID

    comparison = _json_run(
        "--as-of", "2024-03-31", "--compare-with", "2025-03-31", "--concept", NP_CONCEPT,
        "--period-end", PERIOD_2023, "--json", cwd=tmp_path,
    )
    assert comparison["comparison"]["states"] == {
        "added": 0, "removed": 0, "value_changed": 1, "version_changed": 0, "unchanged": 0,
    }
    entry = comparison["comparison"]["entries"][0]
    assert entry["state"] == "value_changed"
    assert entry["before"]["fact_id"] == ORIGINAL_NP_2023_FACT_ID
    assert entry["before"]["value_decimal"] == ORIGINAL_NP_2023
    assert entry["after"]["fact_id"] == RESTATED_NP_2023_FACT_ID
    assert entry["after"]["value_decimal"] == RESTATED_NP_2023
    after_trace = comparison["compare_selections"][0]
    assert after_trace["fact_id"] == RESTATED_NP_2023_FACT_ID
    assert after_trace["available_at"] <= comparison["request"]["compare_with"]
    assert after_trace["parents"]["unresolved"] == 2
    assert after_trace["source_reference"]["eligible_for_metrics"] is True
    assert after_trace["missing_source_reference_fields"] == [
        "source_url", "source_hash", "source_page", "source_table",
    ]

    full = _json_run(
        "--as-of", "2024-03-31", "--compare-with", "2025-03-31", "--json", cwd=tmp_path
    )
    assert full["selection_count"] == 16
    assert {item["available_at"] for item in full["selections"]} == {
        "2022-04-01", "2023-03-30", "2024-03-26",
    }
    assert {item["period_end"] for item in full["selections"]} == {
        "2020-12-31", "2021-12-31", "2022-12-31", "2023-12-31",
    }
    assert full["comparison"]["states"] == {
        "added": 5, "removed": 0, "value_changed": 5, "version_changed": 0, "unchanged": 11,
    }
    assert RESTATED_NP_2023 not in json.dumps(full["selections"], ensure_ascii=False)

    markdown = _stdout(
        _run_module(
            "--as-of", "2024-03-31", "--concept", NP_CONCEPT, "--period-end", PERIOD_2023,
            cwd=tmp_path,
        )
    )
    assert ORIGINAL_NP_2023 in markdown
    assert RESTATED_NP_2023 not in markdown


def test_empty_window_and_on_boundary_selection(tmp_path: Path) -> None:
    empty = _json_run("--as-of", "2022-03-31", "--json", cwd=tmp_path)
    assert empty["selection_count"] == 0
    assert empty["selections"] == []
    assert empty["comparison"] is None

    empty_markdown = _stdout(_run_module("--as-of", "2022-03-31", cwd=tmp_path))
    assert "没有任何通过 PIT 门禁的可用事实" in empty_markdown
    assert "as-of 时点没有选中事实" in empty_markdown

    boundary = _json_run("--as-of", "2022-04-01", "--json", cwd=tmp_path)
    assert boundary["selection_count"] == 6
    assert {item["available_at"] for item in boundary["selections"]} == {"2022-04-01"}
    assert boundary["comparison"] is None

    parent_scope = _json_run(
        "--as-of", "2024-03-31", "--scope", "parent_company", "--json", cwd=tmp_path
    )
    assert parent_scope["selection_count"] == 0
    assert parent_scope["request"]["scope"] == "parent_company"


def test_invalid_selectors_fail_sanitized_without_stdout(tmp_path: Path) -> None:
    cases = [
        (("--as-of", "2024-03-31", "--concept", "not_a_concept"), "UNKNOWN_CONCEPT"),
        (("--as-of", "2024-03-31", "--compare-with", "2024-03-30"), "COMPARE_BEFORE_AS_OF"),
        (("--as-of", "2024-3-31"), "INVALID_AS_OF_DATE"),
        (("--as-of", "2024-02-30"), "INVALID_AS_OF_DATE"),
        (("--as-of", "2024-03-31", "--compare-with", "2025-13-01"), "INVALID_COMPARE_WITH"),
        (("--as-of", "2024-03-31", "--period-end", "2023-13-01"), "INVALID_PERIOD_END"),
        (("--as-of", "2024-03-31", "--scope", "combined"), "INVALID_SCOPE"),
        ((), "INVALID_ARGUMENTS"),
        (("--as-of", "2024-03-31", "--json", "--output", "both"), "INVALID_ARGUMENTS"),
    ]
    for arguments, code in cases:
        completed = _run_module(*arguments, cwd=tmp_path)
        assert completed.returncode == 2, (arguments, completed.stdout)
        assert completed.stdout == b"", arguments
        assert completed.stderr.decode("utf-8") == f"error: {code}\n", arguments
        assert b"Traceback" not in completed.stderr


def test_trace_shows_source_metadata_and_unresolved_raw_parents(tmp_path: Path) -> None:
    payload = _json_run(
        "--as-of", "2025-03-31", "--concept", REVENUE_CONCEPT, "--period-end", PERIOD_2023,
        "--json", cwd=tmp_path,
    )
    assert payload["selection_count"] == 1
    entry = payload["selections"][0]
    assert entry["fact_id"] == RESTATED_REVENUE_2023_FACT_ID
    assert entry["value_decimal"] == "301281200.000000000000"
    assert entry["unit"] == "万元"
    assert entry["raw_unit"] == "万元"
    assert entry["period_type"] == "annual"
    assert entry["context_id"] == "601857.SH|2023|annual|consolidated"

    context = entry["context"]
    assert context["period_start"] == "2023-01-01"
    assert context["period_end"] == PERIOD_2023
    assert context["consolidation_scope"] == "consolidated"
    assert context["accounting_standard"] == "CAS"
    assert context["filing_date"] == "2024-03-26"
    assert "2023" in context["source_document"]
    assert "created_at" not in context

    lineage = entry["lineage"]
    assert len(lineage) == 1
    assert lineage[0]["lineage_id"] == 57
    assert lineage[0]["role"] == "reconciliation_output"
    assert lineage[0]["source_provider"] == "official_reconciliation"
    assert lineage[0]["source_tier"] == "reconciled_derived"
    assert lineage[0]["source_method"] == "dual_source_reconciliation"
    assert lineage[0]["reconciliation_rule_id"] == "RECON_OFFICIAL_NUMERIC_001"
    assert lineage[0]["reconciliation_rule_version"] == "1"

    lineage_rows = {row["fact_id"]: row for row in _fixture("lineage.json")}
    fixture_lineage = lineage_rows[RESTATED_REVENUE_2023_FACT_ID]
    expected_parents = sorted(
        value.strip()
        for value in fixture_lineage["parent_fact_ids"].split(",")
        if value.strip()
    )
    assert len(expected_parents) == 2
    parents = entry["parents"]
    assert parents["total"] == 2
    assert parents["resolved"] == 0
    assert parents["unresolved"] == 2
    assert [item["fact_id"] for item in parents["entries"]] == expected_parents
    for parent in parents["entries"]:
        assert parent["status"] == "unresolved_absent_from_snapshot"
        assert parent["retained_in_snapshot"] is False
        assert parent["pit_available_at_as_of"] is False

    metadata = entry["storage_metadata"]
    assert metadata["availability_proof"] is False
    assert metadata["context_created_at"] == "2026-08-01T14:38:18.186504+08:00"
    assert metadata["lineage_recorded_at"] == ["2026-08-01T14:38:18.821658"]

    markdown = _stdout(
        _run_module(
            "--as-of", "2025-03-31", "--concept", REVENUE_CONCEPT, "--period-end", PERIOD_2023,
            cwd=tmp_path,
        )
    )
    assert "非可得性证据" in markdown
    assert "未解决（原始父事实不在固定快照内，本工具无法复原）" in markdown
    assert expected_parents[0] in markdown


def test_real_export_is_portable_repeatable_and_never_overwrites(
    tmp_path: Path, monkeypatch, capsys,
) -> None:
    unrelated = tmp_path / "unrelated"
    unrelated.mkdir()
    arguments = ("--as-of", "2024-03-31", "--compare-with", "2025-03-31")

    first = tmp_path / "export-a"
    second = tmp_path / "nested" / "export-b"
    for target in (first, second):
        completed = _run_module(*arguments, "--output", str(target), cwd=unrelated)
        assert completed.returncode == 0, completed.stderr.decode("utf-8", "replace")
        assert completed.stdout.decode("utf-8").startswith("exported 2 managed files, ")

    payloads: dict[Path, dict[str, bytes]] = {}
    for target in (first, second):
        payloads[target] = {
            name: (target / name).read_bytes()
            for name in (*explorer.MANAGED_FILE_NAMES, explorer.MANIFEST_NAME)
        }
    assert payloads[first] == payloads[second]

    manifest = json.loads(payloads[first][explorer.MANIFEST_NAME].decode("utf-8"))
    assert manifest["schema"] == explorer.MANIFEST_SCHEMA
    assert manifest["managed_file_count"] == 2
    assert manifest["request"]["as_of"] == "2024-03-31"
    assert manifest["request"]["compare_with"] == "2025-03-31"
    assert manifest["boundaries"]["current_timestamp_recorded"] is False
    assert manifest["boundaries"]["caller_database_read"] is False
    for entry in manifest["files"]:
        assert entry["sha256"] == _sha256(payloads[first][entry["path"]])
        assert entry["byte_count"] == len(payloads[first][entry["path"]])
    source_digests = {item["name"]: item["sha256"] for item in manifest["source"]["files"]}
    assert source_digests == explorer.PINNED_SOURCE_SHA256
    assert manifest["source"]["row_count"] == 33
    assert manifest["selection"]["selection_count"] == 16
    assert len(manifest["selection"]["as_of_fact_ids"]) == 16
    assert len(manifest["selection"]["compare_with_fact_ids"]) == 21

    report = json.loads(payloads[first][explorer.REPORT_JSON_NAME].decode("utf-8"))
    assert report["request"] == manifest["request"]
    assert report["selection_count"] == 16
    assert report["comparison"]["states"]["value_changed"] == 5
    assert "2024-03-31" in payloads[first][explorer.REPORT_MARKDOWN_NAME].decode("utf-8")

    sentinel = tmp_path / "existing"
    sentinel.mkdir()
    (sentinel / "keep.txt").write_bytes(b"foreign artifact\n")
    before_listing = sorted(item.name for item in sentinel.iterdir())
    rejected = _run_module(*arguments, "--output", str(sentinel), cwd=unrelated)
    assert rejected.returncode == 2
    assert rejected.stdout == b""
    assert rejected.stderr.decode("utf-8") == "error: OUTPUT_PATH_EXISTS\n"
    assert (sentinel / "keep.txt").read_bytes() == b"foreign artifact\n"
    assert sorted(item.name for item in sentinel.iterdir()) == before_listing

    file_target = tmp_path / "existing-file"
    file_target.write_bytes(b"not a directory\n")
    file_rejected = _run_module(*arguments, "--output", str(file_target), cwd=unrelated)
    assert file_rejected.returncode == 2
    assert file_rejected.stdout == b""
    assert file_rejected.stderr.decode("utf-8") == "error: OUTPUT_PATH_EXISTS\n"
    assert file_target.read_bytes() == b"not a directory\n"

    never_created = tmp_path / "never-created"
    invalid = _run_module(
        "--as-of", "2024-03-31", "--concept", "not_a_concept",
        "--output", str(never_created), cwd=unrelated,
    )
    assert invalid.returncode == 2
    assert invalid.stdout == b""
    assert invalid.stderr.decode("utf-8") == "error: UNKNOWN_CONCEPT\n"
    assert not never_created.exists()

    damaged = tmp_path / "damaged-source"
    damaged.mkdir()
    for name in explorer.PINNED_SOURCE_SHA256:
        (damaged / name).write_bytes((SNAPSHOT / name).read_bytes())
    (damaged / "facts.json").write_bytes(b"[]\n")
    monkeypatch.setattr(explorer, "COMMITTED_SNAPSHOT", damaged)
    assert explorer.main([*arguments, "--output", str(never_created)]) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == "error: SOURCE_DIGEST_MISMATCH\n"
    assert not never_created.exists()
