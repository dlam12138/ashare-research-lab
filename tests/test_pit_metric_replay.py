"""Acceptance coverage for the M2 PIT metric replay read model.

Four cases exercise the real committed snapshot end to end: (1) the actual CLI replays the seven
existing approved metrics for fiscal year 2023 at both query dates, checked against the public
``MetricEngine`` and the existing registries fed with facts this test gates independently; (2)
2021 missing history keeps its known input-availability bound, the window before the earliest
availability has no inputs at all, ``parent_company`` is honestly empty and no future fact is
selected; (3) invalid date/order/year/metric/scope selectors are sanitized before any fact read;
(4) two cross-cwd real exports are byte-identical, foreign paths stay untouched and a corrupted
pinned source fails before the output root is created.

Expected values are produced by the existing public ``MetricEngine`` plus the existing registries
over facts selected here from the fixture (``available_at`` <= query date, reconciled, eligible,
latest version).  No private replay helper and no engine formula is copied into this test.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest

from ashare_research.metrics.capital_return_definitions import (
    CapitalReturnMetricDefinitionRegistry,
)
from ashare_research.metrics.cashflow_definitions import CashFlowMetricDefinitionRegistry
from ashare_research.metrics.definitions import MetricDefinitionRegistry
from ashare_research.metrics.engine import MetricEngine
from ashare_research.metrics.models import MetricDefinition
from ashare_research.tools import pit_fact_explorer, pit_metric_replay

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
SNAPSHOT = ROOT / "tests" / "fixtures" / "stage2g" / "canonical_fact_snapshot_v1"
MODULE_NAME = "ashare_research.tools.pit_metric_replay"
SYMBOL = "601857.SH"
ROE_METRIC_ID = "return_on_average_equity_attributable_to_parent"
FCF_METRIC_ID = "cash_based_free_cash_flow_proxy"
PROFIT = "net_profit_attributable_to_parent"
EQUITY = "equity_attributable_to_parent"
PRIOR_ROLES = frozenset({"prior", "opening"})
EXPECTED_METRIC_IDS = tuple(sorted((
    "cash_based_free_cash_flow_proxy",
    "cash_paid_for_fixed_assets_to_revenue",
    "net_profit_attributable_to_parent_yoy",
    "operating_cash_flow_to_attributable_net_profit",
    "operating_cash_flow_yoy",
    "return_on_average_equity_attributable_to_parent",
    "revenue_yoy",
)))
# 2024-03-31 与 2025-03-31 两个时点各自选中 16 / 21 条事实（与固定快照一致）。
SELECTION_COUNTS = {"as_of": 16, "compare_with": 21}
FACTS = json.loads((SNAPSHOT / "facts.json").read_text(encoding="utf-8"))
_CHILD_ENVIRONMENT = dict(os.environ)
_CHILD_ENVIRONMENT["PYTHONPATH"] = str(SRC)


def _run_module(*arguments: str, cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", MODULE_NAME, *arguments],
        cwd=cwd,
        env=_CHILD_ENVIRONMENT,
        capture_output=True,
        check=False,
    )


def _payload(*arguments: str, cwd: Path) -> dict[str, Any]:
    completed = _run_module(*arguments, cwd=cwd)
    assert completed.returncode == 0, completed.stderr.decode("utf-8", "replace")
    return json.loads(completed.stdout.decode("utf-8"))


def _definitions() -> dict[str, MetricDefinition]:
    """The seven existing approved definitions, taken straight from the existing registries."""
    definitions = {item.metric_id: item for item in MetricDefinitionRegistry.list_all()}
    definitions.update(
        {item.metric_id: item for item in CashFlowMetricDefinitionRegistry.list_all()}
    )
    roe = CapitalReturnMetricDefinitionRegistry.get(ROE_METRIC_ID)
    assert roe is not None
    definitions[roe.metric_id] = roe
    assert len(definitions) == 7 and sorted(definitions) == list(EXPECTED_METRIC_IDS)
    return definitions


def _selected_facts(date: str) -> dict[tuple[str, str], dict[str, Any]]:
    """Independent PIT gate over the committed fixture; never uses the replay implementation."""
    latest: dict[tuple[str, str], dict[str, Any]] = {}
    for fact in FACTS:
        if not fact["available_at"] or fact["available_at"] > date:
            continue
        if fact["verification_status"] != "reconciled" or fact["eligible_for_metrics"] is not True:
            continue
        key = (fact["concept_id"], fact["period_end"])
        current = latest.get(key)
        stamp = (fact["available_at"], fact["fact_version"])
        if current is None or stamp > (current["available_at"], current["fact_version"]):
            latest[key] = fact
    return latest


def _engine_fact(fact: dict[str, Any]) -> dict[str, Any]:
    """The public engine input contract, restored from one independently selected source fact."""
    return {
        "fact_id": fact["fact_id"],
        "value": Decimal(fact["value_decimal"]),
        "unit": fact["unit"],
        "source_tier": fact["source_tier"],
        "eligible_for_metrics": fact["eligible_for_metrics"],
        "period_end": fact["period_end"],
        "fact_version": fact["fact_version"],
        "restatement_version": fact["restatement_version"],
        "available_at": fact["available_at"],
    }


def _expected_result(metric_id: str, fiscal_year: int, date: str) -> tuple[Any, list[Any]]:
    """Expected result/lineage from the public engine over independently selected fixture facts."""
    definition = _definitions()[metric_id]
    facts = _selected_facts(date)
    bound: list[dict[str, Any] | None] = []
    for position, role in enumerate(definition.input_roles):
        year = fiscal_year - 1 if role in PRIOR_ROLES else fiscal_year
        fact = facts.get((definition.input_concept_ids[position], f"{year}-12-31"))
        bound.append(None if fact is None else _engine_fact(fact))
    return MetricEngine.compute(
        definition,
        symbol=SYMBOL,
        fiscal_year=fiscal_year,
        primary_fact=bound[0],
        secondary_fact=bound[1],
        tertiary_fact=bound[2] if len(bound) >= 3 else None,
        missing_prior_is_history=(
            definition.formula == "(current / prior) - 1" and fiscal_year == 2021
        ),
        result_version=1,
        revision_review_status="offline_replay_unreviewed",
        as_of_date=date,
        created_at="test-only-not-a-publication-time",
    )


def test_actual_cli_replays_seven_metrics_at_both_dates(tmp_path: Path) -> None:
    payload = _payload(
        "--as-of", "2024-03-31", "--compare-with", "2025-03-31", "--year", "2023",
        "--json", cwd=tmp_path,
    )
    assert payload["schema"] == pit_metric_replay.REPORT_SCHEMA
    assert payload["symbol"] == SYMBOL
    assert payload["request"] == {
        "as_of": "2024-03-31",
        "compare_with": "2025-03-31",
        "years": [2023],
        "metrics": list(EXPECTED_METRIC_IDS),
        "scope": "consolidated",
    }
    assert len(payload["selector_digest"]) == 64
    assert payload["comparison"] is not None

    records: dict[str, dict[tuple[str, int], dict[str, Any]]] = {}
    for block_name, date in (("as_of", "2024-03-31"), ("compare_with", "2025-03-31")):
        block = payload[block_name]
        assert block["date"] == date and block["scope"] == "consolidated"
        index = block["selected_fact_index"]
        assert index and block["selection_count"] == len(index)
        assert len(index) == SELECTION_COUNTS[block_name]
        assert all(row["available_at"] <= date for row in index)
        assert all(row["eligible_for_metrics"] is True for row in index)
        assert all(row["source_tier"] == "reconciled_derived" for row in index)
        assert all(row["period_end"] <= date for row in index)

        by_key = {(row["metric_id"], row["fiscal_year"]): row for row in block["records"]}
        assert sorted(by_key) == [(metric_id, 2023) for metric_id in EXPECTED_METRIC_IDS]
        facts = _selected_facts(date)
        for metric_id in EXPECTED_METRIC_IDS:
            record = by_key[(metric_id, 2023)]
            definition = _definitions()[metric_id]
            expected, _lineage = _expected_result(metric_id, 2023, date)
            assert record["status"] == str(expected.status) == "computed"
            assert isinstance(record["value"], str)
            assert record["value"] == format(expected.value, "f")
            assert record["metric_result_id"] == expected.metric_result_id
            assert record["input_fact_ids"] == list(expected.input_fact_ids)
            assert record["metric_definition_version"] == definition.version
            assert record["unit"] == definition.unit
            assert record["period_end"] == "2023-12-31"
            assert record["result_version"] == 1
            assert record["revision_review_status"] == "offline_replay_unreviewed"
            assert "created_at" not in record and "available_at" not in record
            assert record["missing_roles"] == [] and record["missing_fiscal_years"] == []
            assert [item["role"] for item in record["inputs"]] == list(definition.input_roles)
            assert record["input_available_at_bound"] == max(
                item["available_at"] for item in record["inputs"]
            )
            assert record["input_available_at_bound"] <= date
            assert [row["input_fact_id"] for row in record["lineage"]] == record["input_fact_ids"]
            assert [row["input_role"] for row in record["lineage"]] == [
                item["role"] for item in record["inputs"]
            ]
            assert {row["metric_result_id"] for row in record["lineage"]} == {
                record["metric_result_id"]
            }
            for item in record["inputs"]:
                assert item["status"] == "present"
                source = facts[(item["concept_id"], item["period_end"])]
                assert item["fact_id"] == source["fact_id"]
                assert item["value_decimal"] == source["value_decimal"]
                assert item["available_at"] == source["available_at"]
                assert item["source_reference"]["source_tier"] == "reconciled_derived"
                assert item["source_reference"]["eligible_for_metrics"] is True
        records[block_name] = by_key

    before, after = records["as_of"], records["compare_with"]
    assert before[(FCF_METRIC_ID, 2023)]["value"] == "17407700.000000000000"
    assert after[(FCF_METRIC_ID, 2023)]["value"] == "17433900.000000000000"

    facts_before = _selected_facts("2024-03-31")
    facts_after = _selected_facts("2025-03-31")
    roe_before = {item["role"]: item for item in before[(ROE_METRIC_ID, 2023)]["inputs"]}
    roe_after = {item["role"]: item for item in after[(ROE_METRIC_ID, 2023)]["inputs"]}
    assert sorted(roe_before) == ["closing", "numerator", "opening"]
    assert sorted(roe_after) == ["closing", "numerator", "opening"]
    for role, concept, period_end in (
        ("numerator", PROFIT, "2023-12-31"),
        ("opening", EQUITY, "2022-12-31"),
        ("closing", EQUITY, "2023-12-31"),
    ):
        source = facts_before[(concept, period_end)]
        assert roe_before[role]["concept_id"] == concept
        assert roe_before[role]["period_end"] == period_end
        assert roe_before[role]["fact_id"] == source["fact_id"]
        assert roe_before[role]["value_decimal"] == source["value_decimal"]
    assert roe_before["numerator"]["period_type"] == "annual"
    assert roe_before["numerator"]["fiscal_year"] == 2023
    assert roe_before["numerator"]["value_decimal"] == "16114400.000000000000"
    assert roe_before["opening"]["period_type"] == "instant"
    assert roe_before["opening"]["fiscal_year"] == 2022
    assert roe_before["opening"]["value_decimal"] == "136586600.000000000000"
    assert roe_before["opening"]["restatement_version"] == "restated_1"
    assert roe_before["closing"]["period_type"] == "instant"
    assert roe_before["closing"]["value_decimal"] == "144641000.000000000000"
    assert roe_before["closing"]["available_at"] == "2024-03-26"
    assert roe_before["closing"]["source_reference"]["source_tier"] == "reconciled_derived"
    assert roe_before["closing"]["source_reference"]["eligible_for_metrics"] is True
    assert roe_after["numerator"]["value_decimal"] == "16141400.000000000000"
    assert roe_after["closing"]["value_decimal"] == "145133300.000000000000"
    assert roe_after["closing"]["fact_version"] == 2
    assert roe_after["closing"]["fact_id"] == facts_after[(EQUITY, "2023-12-31")]["fact_id"]
    assert roe_after["closing"]["fact_id"] != roe_before["closing"]["fact_id"]
    assert roe_after["opening"]["fact_id"] == roe_before["opening"]["fact_id"]

    comparison = payload["comparison"]
    assert comparison["states"] == {
        "status_changed": 0, "value_changed": 7, "inputs_changed": 0, "unchanged": 0,
    }
    entries = {(entry["metric_id"], entry["fiscal_year"]): entry
               for entry in comparison["entries"]}
    assert sorted(entries) == [(metric_id, 2023) for metric_id in EXPECTED_METRIC_IDS]
    for (metric_id, fiscal_year), entry in entries.items():
        assert entry["state"] == "value_changed"
        left, right = before[(metric_id, fiscal_year)], after[(metric_id, fiscal_year)]
        assert entry["before"]["status"] == entry["after"]["status"] == "computed"
        assert entry["before"]["value"] != entry["after"]["value"]
        assert entry["before"]["metric_result_id"] == left["metric_result_id"]
        assert entry["after"]["metric_result_id"] == right["metric_result_id"]
        assert entry["before"]["unit"] == entry["after"]["unit"] == left["unit"]
        assert entry["before"]["input_available_at_bound"] == left["input_available_at_bound"]
        assert [item["fact_id"] for item in entry["before"]["input_roles"]] == [
            item["fact_id"] for item in left["inputs"]
        ]
        assert [item["role"] for item in entry["after"]["input_roles"]] == list(
            _definitions()[metric_id].input_roles
        )
    fcf_entry = entries[(FCF_METRIC_ID, 2023)]
    assert fcf_entry["before"]["value"] == "17407700.000000000000"
    assert fcf_entry["after"]["value"] == "17433900.000000000000"


def test_missing_history_known_bound_empty_scope_and_no_future_inputs() -> None:
    report = pit_metric_replay.build_report(pit_metric_replay.validate_request(
        as_of="2024-03-31", years=[2021, 2025]))
    assert report["compare_with"] is None and report["comparison"] is None
    records = {(row["metric_id"], row["fiscal_year"]): row
               for row in report["as_of"]["records"]}
    assert sorted(records) == [(metric_id, year) for metric_id in EXPECTED_METRIC_IDS
                               for year in (2021, 2025)]

    for metric_id in ("net_profit_attributable_to_parent_yoy", "operating_cash_flow_yoy",
                      "revenue_yoy"):
        record = records[(metric_id, 2021)]
        expected, _lineage = _expected_result(metric_id, 2021, "2024-03-31")
        assert record["status"] == str(expected.status) == "insufficient_history"
        assert record["value"] is None and expected.value is None
        assert record["input_available_at_bound"] is not None
        assert record["input_available_at_bound"] == "2022-04-01"
        assert record["missing_fiscal_years"] == [2020]
        assert [item["role"] for item in record["missing_roles"]] == ["prior"]
        missing_prior = record["missing_roles"][0]
        assert missing_prior["status"] == "missing"
        assert missing_prior["fiscal_year"] == 2020
        assert missing_prior["concept_id"] == record["input_concept_ids"][1]
        assert missing_prior["reason"] == "absent_from_pit_selection"
        assert "2020" in record["engine_missing_input_description"]
        present = [item for item in record["inputs"] if item["status"] == "present"]
        assert [item["role"] for item in present] == ["current"]
        assert present[0]["available_at"] == "2022-04-01"
        assert present[0]["fact_id"] in record["input_fact_ids"]
        assert record["input_available_at_bound"] == max(
            item["available_at"] for item in present
        )

    for metric_id in ("cash_based_free_cash_flow_proxy",
                      "cash_paid_for_fixed_assets_to_revenue",
                      "operating_cash_flow_to_attributable_net_profit", ROE_METRIC_ID):
        record = records[(metric_id, 2021)]
        expected, _lineage = _expected_result(metric_id, 2021, "2024-03-31")
        assert record["status"] == str(expected.status) == "computed"
        assert record["value"] == format(expected.value, "f")
        assert record["missing_roles"] == []

    index = report["as_of"]["selected_fact_index"]
    assert report["as_of"]["selection_count"] == len(index) == 16
    assert all(row["available_at"] <= "2024-03-31" for row in index)
    assert max(row["period_end"] for row in index) == "2023-12-31"
    for metric_id in EXPECTED_METRIC_IDS:
        record = records[(metric_id, 2025)]
        assert record["status"] == "missing_input" and record["value"] is None
        assert record["input_available_at_bound"] is None
        assert record["missing_roles"] and not record["input_fact_ids"]
        assert record["lineage"] == []
        assert all(item["status"] == "missing" for item in record["missing_roles"])
        assert all(item["reason"] == "absent_from_pit_selection"
                   for item in record["missing_roles"])
    assert records[(ROE_METRIC_ID, 2025)]["missing_fiscal_years"] == [2024, 2025]
    serialized = json.dumps(report, ensure_ascii=False)
    assert "16141400.000000000000" not in serialized
    assert "145133300.000000000000" not in serialized

    empty = pit_metric_replay.build_report(pit_metric_replay.validate_request(
        as_of="2022-03-31", years=[2021]))
    assert empty["as_of"]["selection_count"] == 0
    assert empty["as_of"]["selected_fact_index"] == []
    for record in empty["as_of"]["records"]:
        assert record["status"] == "missing_input" and record["value"] is None
        assert record["input_available_at_bound"] is None
        assert record["input_fact_ids"] == [] and record["lineage"] == []
        assert record["missing_fiscal_years"]
        assert {item["role"] for item in record["missing_roles"]} == set(record["input_roles"])
        assert all(item["reason"] == "absent_from_pit_selection"
                   for item in record["missing_roles"])

    boundary = pit_metric_replay.build_report(pit_metric_replay.validate_request(
        as_of="2022-04-01", years=[2021]))
    assert boundary["as_of"]["selection_count"] == 6
    assert all(row["available_at"] == "2022-04-01"
               for row in boundary["as_of"]["selected_fact_index"])
    boundary_records = {(row["metric_id"], row["fiscal_year"]): row
                        for row in boundary["as_of"]["records"]}
    assert boundary_records[("revenue_yoy", 2021)]["input_available_at_bound"] == "2022-04-01"

    parent = pit_metric_replay.build_report(pit_metric_replay.validate_request(
        as_of="2024-03-31", years=[2023], scope="parent_company"))
    assert parent["as_of"]["scope"] == "parent_company"
    assert parent["as_of"]["selection_count"] == 0
    assert parent["as_of"]["selected_fact_index"] == []
    assert len(parent["as_of"]["records"]) == len(EXPECTED_METRIC_IDS)
    for record in parent["as_of"]["records"]:
        assert record["fiscal_year"] == 2023
        assert record["status"] == "missing_input" and record["value"] is None
        assert record["input_available_at_bound"] is None
        assert record["input_fact_ids"] == [] and record["lineage"] == []

    partial = pit_metric_replay.build_report(pit_metric_replay.validate_request(
        as_of="2024-03-31", compare_with="2025-03-31", years=[2024, 2025]))
    assert partial["comparison"]["states"] == {
        "status_changed": 7, "value_changed": 0, "inputs_changed": 4, "unchanged": 3,
    }
    before_partial = {(row["metric_id"], row["fiscal_year"]): row
                      for row in partial["as_of"]["records"]}
    roe_2024 = before_partial[(ROE_METRIC_ID, 2024)]
    assert [row["input_role"] for row in roe_2024["lineage"]] == ["opening"]
    assert roe_2024["input_available_at_bound"] == "2024-03-26"
    assert [row["role"] for row in roe_2024["missing_roles"]] == ["numerator", "closing"]
    for entry in partial["comparison"]["entries"]:
        if entry["fiscal_year"] == 2025:
            assert entry["before"]["value"] is None and entry["after"]["value"] is None
            assert entry["state"] in {"inputs_changed", "unchanged"}


def test_invalid_selectors_are_sanitized_before_any_fact_read(
    tmp_path: Path, monkeypatch, capsys,
) -> None:
    def forbidden(request: dict) -> dict:
        raise AssertionError("invalid selectors must never reach the pinned fact read")

    monkeypatch.setattr(pit_fact_explorer, "build_report", forbidden)
    invalid_metric = "return_on_average_total_assets"
    base = {"compare_with": None, "years": [2023], "metrics": list(EXPECTED_METRIC_IDS),
            "scope": "consolidated"}
    for overrides, code in (
        ({"as_of": "2024/03/31"}, "INVALID_AS_OF_DATE"),
        ({"as_of": "2024-02-30"}, "INVALID_AS_OF_DATE"),
        ({"as_of": "2025-03-31", "compare_with": "2025-03-30"}, "COMPARE_BEFORE_AS_OF"),
        ({"as_of": "2025-03-31", "compare_with": "2025-13-01"}, "INVALID_COMPARE_WITH"),
        ({"as_of": "2024-03-31", "years": [2020]}, "INVALID_YEAR"),
        ({"as_of": "2024-03-31", "years": [2026]}, "INVALID_YEAR"),
        ({"as_of": "2024-03-31", "metrics": [invalid_metric]}, "UNKNOWN_METRIC"),
        ({"as_of": "2024-03-31", "scope": "parent"}, "INVALID_SCOPE"),
    ):
        with pytest.raises(pit_metric_replay.PitMetricReplayError) as info:
            pit_metric_replay.build_report({**base, **overrides})
        assert info.value.code == code
        assert str(info.value) == code

    for arguments, code in (
        ((), "INVALID_ARGUMENTS"),
        (("--as-of", "2024/03/31"), "INVALID_AS_OF_DATE"),
        (("--as-of", "2024-03-31", "--compare-with", "2024-03-30"), "COMPARE_BEFORE_AS_OF"),
        (("--as-of", "2024-03-31", "--year", "2019"), "INVALID_YEAR"),
        (("--as-of", "2024-03-31", "--metric", invalid_metric), "UNKNOWN_METRIC"),
        (("--as-of", "2024-03-31", "--scope", "combined"), "INVALID_SCOPE"),
        (("--as-of", "2024-03-31", "--json", "--output", "both"), "INVALID_ARGUMENTS"),
    ):
        assert pit_metric_replay.main(list(arguments)) == 2
        captured = capsys.readouterr()
        assert captured.out == ""
        assert captured.err == f"error: {code}\n"

    for arguments, code in (
        (("--as-of", "2024/03/31"), "INVALID_AS_OF_DATE"),
        (("--as-of", "2024-03-31", "--year", "2019"), "INVALID_YEAR"),
        (("--as-of", "2024-03-31", "--metric", invalid_metric), "UNKNOWN_METRIC"),
    ):
        completed = _run_module(*arguments, cwd=tmp_path)
        assert completed.returncode == 2
        assert completed.stdout == b""
        assert completed.stderr.decode("utf-8") == f"error: {code}\n"
        assert b"Traceback" not in completed.stderr


def test_cross_cwd_deterministic_export_foreign_paths_and_corrupted_source(
    tmp_path: Path, monkeypatch, capsys,
) -> None:
    arguments = ("--as-of", "2024-03-31", "--compare-with", "2025-03-31", "--year", "2023")
    first_dir = tmp_path / "run-a"
    second_dir = tmp_path / "run-b"
    unrelated = tmp_path / "elsewhere"
    unrelated.mkdir()
    first = _run_module(*arguments, "--output", str(first_dir), cwd=tmp_path)
    second = _run_module(*arguments, "--output", str(second_dir), cwd=unrelated)
    assert first.returncode == 0, first.stderr.decode("utf-8", "replace")
    assert second.returncode == 0, second.stderr.decode("utf-8", "replace")
    assert first.stdout == second.stdout
    assert first.stdout.decode("utf-8").startswith("exported 2 managed files, ")

    names = (*pit_metric_replay.MANAGED_FILE_NAMES, pit_metric_replay.MANIFEST_NAME)
    payloads = {name: (first_dir / name).read_bytes() for name in names}
    assert all(payloads.values())
    for name in names:
        assert payloads[name] == (second_dir / name).read_bytes()

    manifest = json.loads(payloads[pit_metric_replay.MANIFEST_NAME].decode("utf-8"))
    assert manifest["schema"] == pit_metric_replay.MANIFEST_SCHEMA
    assert manifest["report_schema"] == pit_metric_replay.REPORT_SCHEMA
    assert manifest["managed_file_count"] == len(pit_metric_replay.MANAGED_FILE_NAMES) == 2
    assert manifest["request"] == {
        "as_of": "2024-03-31",
        "compare_with": "2025-03-31",
        "years": [2023],
        "metrics": list(EXPECTED_METRIC_IDS),
        "scope": "consolidated",
    }
    for entry in manifest["files"]:
        assert entry["path"] in pit_metric_replay.MANAGED_FILE_NAMES
        assert entry["byte_count"] == len(payloads[entry["path"]])
        assert entry["sha256"] == hashlib.sha256(payloads[entry["path"]]).hexdigest()
    assert manifest["source"]["row_count"] == 33
    assert [item["name"] for item in manifest["source"]["files"]] == list(
        pit_fact_explorer.PINNED_SOURCE_SHA256
    )
    for item in manifest["source"]["files"]:
        pinned = hashlib.sha256((SNAPSHOT / item["name"]).read_bytes()).hexdigest()
        assert item["sha256"] == pinned == pit_fact_explorer.PINNED_SOURCE_SHA256[item["name"]]
    assert manifest["boundaries"]["current_timestamp_recorded"] is False
    assert manifest["boundaries"]["network_used"] is False
    assert manifest["boundaries"]["metric_database_written"] is False

    report = json.loads(payloads["report.json"].decode("utf-8"))
    selection = manifest["selection"]
    assert selection["as_of"] == "2024-03-31" and selection["compare_with"] == "2025-03-31"
    assert selection["as_of_fact_ids"] == [
        row["fact_id"] for row in report["as_of"]["selected_fact_index"]
    ]
    assert selection["compare_with_fact_ids"] == [
        row["fact_id"] for row in report["compare_with"]["selected_fact_index"]
    ]
    assert selection["as_of_metric_result_ids"] == [
        row["metric_result_id"] for row in report["as_of"]["records"]
    ]
    assert selection["compare_with_metric_result_ids"] == [
        row["metric_result_id"] for row in report["compare_with"]["records"]
    ]
    assert selection["comparison_states"] == report["comparison"]["states"]
    for block in (report["as_of"], report["compare_with"]):
        for record in block["records"]:
            assert "created_at" not in record and "available_at" not in record
            assert record["revision_review_status"] == "offline_replay_unreviewed"
    markdown = payloads["report.md"].decode("utf-8")
    assert "17407700.000000000000" in markdown
    assert "17433900.000000000000" in markdown
    assert "offline-replay-not-a-publication-time" in markdown

    sentinel_dir = tmp_path / "foreign-dir"
    sentinel_dir.mkdir()
    (sentinel_dir / "keep.txt").write_bytes(b"foreign artifact\n")
    listing_before = sorted(item.name for item in sentinel_dir.iterdir())
    rejected_dir = _run_module(*arguments, "--output", str(sentinel_dir), cwd=unrelated)
    assert rejected_dir.returncode == 2 and rejected_dir.stdout == b""
    assert rejected_dir.stderr.decode("utf-8") == "error: OUTPUT_PATH_EXISTS\n"
    assert (sentinel_dir / "keep.txt").read_bytes() == b"foreign artifact\n"
    assert sorted(item.name for item in sentinel_dir.iterdir()) == listing_before

    sentinel_file = tmp_path / "foreign-file"
    sentinel_file.write_bytes(b"not a directory\n")
    rejected_file = _run_module(*arguments, "--output", str(sentinel_file), cwd=unrelated)
    assert rejected_file.returncode == 2 and rejected_file.stdout == b""
    assert rejected_file.stderr.decode("utf-8") == "error: OUTPUT_PATH_EXISTS\n"
    assert sentinel_file.read_bytes() == b"not a directory\n"

    damaged = tmp_path / "damaged-snapshot"
    damaged.mkdir()
    for name in pit_fact_explorer.PINNED_SOURCE_SHA256:
        (damaged / name).write_bytes((SNAPSHOT / name).read_bytes())
    (damaged / "facts.json").write_bytes(b"[]\n")
    monkeypatch.setattr(pit_fact_explorer, "COMMITTED_SNAPSHOT", damaged)
    with pytest.raises(pit_metric_replay.PitMetricReplayError) as info:
        pit_metric_replay.build_report(pit_metric_replay.validate_request(
            as_of="2024-03-31", years=[2023]))
    assert info.value.code == "SOURCE_DIGEST_MISMATCH"
    never = tmp_path / "never-created"
    assert pit_metric_replay.main([*arguments, "--output", str(never)]) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == "error: SOURCE_DIGEST_MISMATCH\n"
    assert not never.exists()
