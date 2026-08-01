"""Stage 2D-F ROA definition, engine, and offline PIT integration tests."""

from __future__ import annotations

import json
from decimal import ROUND_HALF_EVEN, Context, Decimal, localcontext
from pathlib import Path

import pytest

from ashare_research.facts.as_of import AsOfQuery
from ashare_research.facts.repository import FactRepository
from ashare_research.metrics.capital_return_definitions import (
    CapitalReturnMetricDefinitionRegistry,
)
from ashare_research.metrics.engine import CANONICAL_QUANTUM, MetricEngine
from ashare_research.metrics.identity import build_metric_result_id
from ashare_research.metrics.models import MetricStatus
from ashare_research.storage.duckdb_store import DuckDBStore
from ashare_research.tools.official_roa_metric_extension import (
    ROA_METRIC_ID,
    run_roa_metric_extension,
)

ROOT = Path(__file__).resolve().parents[1]
ROA = CapitalReturnMetricDefinitionRegistry.get(ROA_METRIC_ID)


def _fact(
    value: int,
    *,
    fact_id: str = "f",
    version: int = 1,
    period_end: str = "2021-12-31",
    available_at: str = "2022-04-01",
    context_id: str = "601857.SH|2021|instant|consolidated",
):
    return {
        "fact_id": fact_id,
        "fact_version": version,
        "restatement_version": "original" if version == 1 else "restated_1",
        "available_at": available_at,
        "period_end": period_end,
        "value": value,
        "unit": "万元",
        "source_tier": "reconciled_derived",
        "eligible_for_metrics": True,
        "context_id": context_id,
    }


def _compute(
    *,
    numerator: dict | None,
    opening: dict | None,
    closing: dict | None,
    as_of_date: str = "2022-04-01",
):
    return MetricEngine.compute(
        ROA,
        symbol="601857.SH",
        fiscal_year=2021,
        primary_fact=numerator,
        secondary_fact=opening,
        tertiary_fact=closing,
        revision_review_status="reviewed_unchanged",
        as_of_date=as_of_date,
        created_at="2026-08-01T00:00:00+08:00",
    )


def test_roa_definition_contract_and_roe_legacy_view():
    assert ROA is not None
    assert ROA.metric_id == ROA_METRIC_ID
    assert ROA.version == "1"
    assert ROA.unit == "ratio"
    assert ROA.formula == (
        "net_profit / "
        "((opening_total_assets + closing_total_assets) / 2)"
    )
    assert ROA.input_concept_ids == ("net_profit", "total_assets", "total_assets")
    assert ROA.input_roles == ("numerator", "opening", "closing")
    assert ROA.score_eligible is False
    assert [
        item.metric_id
        for item in CapitalReturnMetricDefinitionRegistry.list_all(include_roa=True)
    ] == [
        "return_on_average_equity_attributable_to_parent",
        ROA_METRIC_ID,
    ]
    assert [
        item.metric_id for item in CapitalReturnMetricDefinitionRegistry.list_all()
    ] == ["return_on_average_equity_attributable_to_parent"]


def test_roa_does_not_bind_attributable_net_profit():
    assert ROA.input_concept_ids[0] == "net_profit"
    assert ROA.input_concept_ids[0] != "net_profit_attributable_to_parent"


def test_roa_formula_uses_three_roles_and_max_available_at():
    result, lineage = _compute(
        numerator=_fact(
            11468700,
            fact_id="np",
            context_id="601857.SH|2021|annual|consolidated",
            available_at="2022-04-01",
        ),
        opening=_fact(
            248840000,
            fact_id="opening",
            period_end="2020-12-31",
            context_id="601857.SH|2020|instant|consolidated",
            available_at="2022-04-01",
        ),
        closing=_fact(
            250253300,
            fact_id="closing",
            context_id="601857.SH|2021|instant|consolidated",
            available_at="2022-04-02",
        ),
    )
    assert result.status == MetricStatus.computed
    assert result.value == Decimal("0.045958140492")
    assert result.available_at == "2022-04-02"
    assert result.input_fact_ids == ("np", "opening", "closing")
    assert [item.input_role for item in lineage] == [
        "numerator", "opening", "closing"
    ]
    assert {item.input_fact_id for item in lineage} == set(result.input_fact_ids)
    assert result.metric_result_id == build_metric_result_id(result)


@pytest.mark.parametrize(
    ("opening_value", "closing_value", "status"),
    [
        (0, 0, MetricStatus.undefined_zero_denominator),
        (-100, -100, MetricStatus.not_comparable_negative_denominator),
        (-100, 100, MetricStatus.undefined_zero_denominator),
    ],
)
def test_roa_average_denominator_boundaries(opening_value, closing_value, status):
    result, _ = _compute(
        numerator=_fact(100, fact_id="np"),
        opening=_fact(opening_value, fact_id="opening", period_end="2020-12-31"),
        closing=_fact(closing_value, fact_id="closing"),
    )
    assert result.status == status
    assert result.value is None


def test_roa_any_missing_input_is_missing_input_and_roles_do_not_shift():
    result, lineage = _compute(
        numerator=_fact(100, fact_id="np"),
        opening=None,
        closing=_fact(100, fact_id="closing"),
    )
    assert result.status == MetricStatus.missing_input
    assert {item.input_fact_id: item.input_role for item in lineage} == {
        "np": "numerator",
        "closing": "closing",
    }


def _read(run: dict, filename: str):
    return json.loads(
        (run["run_directory"] / filename).read_text(encoding="utf-8")
    )


@pytest.fixture(scope="module")
def accepted_run(tmp_path_factory: pytest.TempPathFactory) -> dict:
    result = run_roa_metric_extension(
        tmp_path_factory.mktemp("roa_metric_extension"),
        run_id="roa_metric_extension_test",
    )
    assert result["status"] == "passed", result
    return result


def test_roa_and_combined_counts_and_pit_match_contract(accepted_run):
    assert accepted_run["roa_counts"] == {
        "definitions": 1,
        "result_versions": 7,
        "computed_versions": 7,
        "insufficient_history_versions": 0,
        "version_links": 2,
        "lineage_rows": 21,
        "final_latest": 5,
    }
    assert accepted_run["combined_counts"] == {
        "definitions": 12,
        "results": 77,
        "computed": 73,
        "insufficient_history": 4,
        "version_links": 17,
        "lineage": 164,
        "final_latest": 60,
        "final_computed": 56,
    }
    assert accepted_run["metric_pit_counts"] == [0, 12, 24, 36, 48, 60]
    assert accepted_run["metric_pit_computed_counts"] == [0, 8, 20, 32, 44, 56]
    assert accepted_run["metric_pit_insufficient_history_counts"] == [0, 4, 4, 4, 4, 4]


def test_roa_values_are_recomputed_from_foundation_facts(accepted_run):
    upstream_db = (
        accepted_run["run_directory"]
        / "upstream_net_profit_official_facts"
        / "net_profit.duckdb"
    )
    store = DuckDBStore(str(upstream_db))
    query = AsOfQuery(FactRepository(store))
    result_rows = _read(accepted_run, "metric_result_versions.json")
    roa_rows = [row for row in result_rows if row["metric_id"] == ROA_METRIC_ID]
    try:
        for as_of_date in ("2023-03-30", "2024-03-26", "2025-03-31", "2026-03-30"):
            numerators = {
                int(str(row["period_end"])[:4]): row
                for row in query.get_latest_available(
                    "601857.SH", as_of_date, ["net_profit"]
                ).to_dict("records")
            }
            assets = {
                int(str(row["period_end"])[:4]): row
                for row in query.get_latest_available(
                    "601857.SH", as_of_date, ["total_assets"]
                ).to_dict("records")
            }
            for fiscal_year in sorted(set(numerators) & set(assets)):
                if fiscal_year - 1 not in assets:
                    continue
                with localcontext(Context(prec=28, rounding=ROUND_HALF_EVEN)):
                    expected = (
                        Decimal(str(numerators[fiscal_year]["value"]))
                        / (
                            Decimal(str(assets[fiscal_year - 1]["value"]))
                            + Decimal(str(assets[fiscal_year]["value"]))
                        )
                        * Decimal(2)
                    ).quantize(CANONICAL_QUANTUM, rounding=ROUND_HALF_EVEN)
                candidates = [
                    row for row in roa_rows
                    if row["fiscal_year"] == fiscal_year
                    and row["available_at"] <= as_of_date
                ]
                assert candidates
                assert Decimal(candidates[-1]["value"]) == expected
    finally:
        store.close()


def test_roa_transitions_and_2024_opening_and_2025_status(accepted_run):
    rows = _read(accepted_run, "metric_result_versions.json")
    roa_rows = [row for row in rows if row["metric_id"] == ROA_METRIC_ID]
    assert len(roa_rows) == 7
    assert [
        (row["fiscal_year"], row["result_version"])
        for row in roa_rows if row["result_version"] > 1
    ] == [(2022, 2), (2023, 2)]
    transitions = _read(accepted_run, "roa_metric_transitions.json")
    assert [item["fiscal_year"] for item in transitions] == [2022, 2023]
    assert [item["pit_switch_date"] for item in transitions] == [
        "2024-03-26", "2025-03-31"
    ]
    roa_2024 = next(row for row in roa_rows if row["fiscal_year"] == 2024)
    assets_2023_v2 = next(
        row for row in _read(accepted_run, "metric_lineage.json")
        if row["metric_result_id"] == roa_2024["metric_result_id"]
        and row["input_role"] == "opening"
    )
    assert assets_2023_v2["input_fact_version"] == 2
    roa_2025 = next(row for row in roa_rows if row["fiscal_year"] == 2025)
    assert roa_2025["revision_review_status"] == "not_yet_reviewable"
    assert {row["fiscal_year"] for row in roa_rows} == set(range(2021, 2026))


def test_upstream_facts_old_results_and_no_roic_or_score(accepted_run):
    assert accepted_run["upstream"]["financial_facts"] == 201
    assert accepted_run["upstream"]["eligible_facts"] == 67
    assert accepted_run["upstream"]["latest_fact_pit"] == 52
    assert accepted_run["upstream"]["version_chain_links"] == 45
    assert accepted_run["upstream"]["stage2d_combined_counts"]["results"] == 70
    rows = _read(accepted_run, "metric_result_versions.json")
    assert all("roic" not in row["metric_id"].lower() for row in rows)
    assert all("score" not in row["metric_id"].lower() for row in rows)
    manifest = _read(accepted_run, "run_manifest.json")
    assert manifest["roic_computation"] == "not_performed"
    assert manifest["scoring"] == "not_implemented"


def test_roa_runner_is_idempotent(tmp_path_factory: pytest.TempPathFactory):
    first = run_roa_metric_extension(
        tmp_path_factory.mktemp("roa_idem1"), run_id="roa_idem1"
    )
    second = run_roa_metric_extension(
        tmp_path_factory.mktemp("roa_idem2"), run_id="roa_idem2"
    )
    assert first["status"] == "passed" and second["status"] == "passed"
    assert first["new_metric_result_ids"] == second["new_metric_result_ids"]
    assert first["combined_counts"] == second["combined_counts"]
    assert first["roa_latest_values"] == second["roa_latest_values"]


def test_run_outputs_are_run_scoped(accepted_run):
    run_dir = accepted_run["run_directory"]
    for name in (
        "metrics.duckdb",
        "metric_definitions.json",
        "metric_result_versions.json",
        "latest_metric_snapshot.json",
        "metric_pit_snapshots.json",
        "roa_metric_transitions.json",
        "metric_lineage.json",
        "run_manifest.json",
        "acceptance_summary.md",
    ):
        assert (run_dir / name).exists(), name
