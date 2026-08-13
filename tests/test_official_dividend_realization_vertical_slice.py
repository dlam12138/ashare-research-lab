"""Stage 2F dividend-event, Rule 007, metric, and offline-runner gates."""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

import pytest

from ashare_research.events.dividend import build_dividend_event_id, validate_dividend_event
from ashare_research.facts.identity import build_fact_id
from ashare_research.metrics.dividend_realization_definitions import (
    DividendRealizationMetricDefinitionRegistry,
)
from ashare_research.metrics.dividend_realization_engine import (
    DividendRealizationMetricEngine,
)
from ashare_research.metrics.engine import MetricInputError
from ashare_research.metrics.identity import build_metric_result_id
from ashare_research.reconciliation.dividend import (
    DIVIDEND_RULE_ID,
    DividendNumericReconciliationEngine,
)
from ashare_research.reconciliation.models import ReconciliationStatus
from ashare_research.tools.official_dividend_realization_vertical_slice import (
    EVENTS_PATH,
    _source_fact,
    _validate_event_ledger,
    run_dividend_realization_vertical_slice,
)


def _metric_fact(
    fact_id: str,
    value: str | int,
    *,
    available_at: str = "2026-01-01",
    unit: str = "万元",
) -> dict:
    return {
        "fact_id": fact_id,
        "fact_version": 1,
        "restatement_version": "original",
        "available_at": available_at,
        "period_end": "2025-12-31",
        "value": Decimal(str(value)),
        "unit": unit,
        "source_tier": "reconciled_derived",
        "eligible_for_metrics": True,
    }


def test_dividend_definition_contract_is_explicit_and_non_scoring():
    definitions = DividendRealizationMetricDefinitionRegistry.list_all()
    assert [item.metric_id for item in definitions] == [
        "cash_dividend_payout_ratio",
        "operating_cash_flow_dividend_coverage",
        "free_cash_flow_proxy_dividend_coverage",
        "implemented_cash_dividend_per_share",
    ]
    assert all(item.version == "1" and item.score_eligible is False for item in definitions)
    assert definitions[0].input_roles == ("implemented_dividend", "net_profit")
    assert definitions[1].input_roles == ("operating_cash_flow", "implemented_dividend")
    assert definitions[2].input_roles == (
        "operating_cash_flow",
        "cash_paid_for_fixed_assets",
        "implemented_dividend",
    )
    assert definitions[3].unit == "CNY_PER_SHARE"
    assert all("roic" not in item.metric_id for item in definitions)


def test_event_ledger_has_canonical_ids_full_chain_and_dual_official_sources():
    raw = json.loads(Path(EVENTS_PATH).read_text(encoding="utf-8"))
    assert raw["contract"] == "dividend_event_record_v1"
    assert len(raw["events"]) == 10
    events = _validate_event_ledger()
    assert len(events) == 10
    for event in events:
        assert event["event_id"] == build_dividend_event_id(
            "601857.SH", event["source_fiscal_year"], event["event_type"]
        )
        validate_dividend_event(event)
        assert [item["stage"] for item in event["event_chain"]] == [
            "proposal",
            "shareholder_approved",
            "implementation_announced",
            "paid/implemented",
        ]
        assert {item["source_tier"] for item in event["source_documents"]} == {
            "company_official",
            "exchange_official",
        }


def test_rule007_reconciles_exact_numeric_values_and_rejects_wrong_unit():
    event = _validate_event_ledger()[0]
    documents = {item["source_tier"]: item for item in event["source_documents"]}
    company = _source_fact(
        event, "cash_dividend_per_share", documents["company_official"], created_at="x"
    )
    exchange = _source_fact(
        event, "cash_dividend_per_share", documents["exchange_official"], created_at="x"
    )
    engine = DividendNumericReconciliationEngine()
    matched = engine.reconcile_pair(company, exchange)
    assert matched.status == ReconciliationStatus.matched
    assert matched.rule_id == DIVIDEND_RULE_ID
    assert matched.output_fact is not None
    assert matched.output_fact["eligible_for_metrics"] is True
    assert matched.output_fact["fact_id"] == build_fact_id(matched.output_fact)
    assert matched.output_fact["source_tier"] == "reconciled_derived"

    bad_exchange = dict(exchange)
    bad_exchange["unit"] = "CNY"
    rejected = engine.reconcile_pair(company, bad_exchange)
    assert rejected.status == ReconciliationStatus.not_comparable


def test_dividend_engine_uses_event_lists_decimal_quantum_and_one_to_one_lineage():
    definitions = {
        item.metric_id: item for item in DividendRealizationMetricDefinitionRegistry.list_all()
    }
    result, lineage = DividendRealizationMetricEngine.compute(
        definitions["cash_dividend_payout_ratio"],
        symbol="601857.SH",
        fiscal_year=2025,
        role_facts={
            "implemented_dividend": [_metric_fact("d1", "100000"), _metric_fact("d2", "50000")],
            "net_profit": [_metric_fact("np", "30", available_at="2026-03-30")],
        },
        revision_review_status="not_yet_reviewable",
        as_of_date="2026-07-01",
        created_at="2026-08-01T00:00:00+08:00",
    )
    assert result.status == "computed"
    assert result.value == Decimal("0.500000000000")
    assert result.available_at == "2026-03-30"
    assert result.metric_result_id == build_metric_result_id(result)
    assert result.input_fact_ids == ("d1", "d2", "np")
    assert [(row.input_fact_id, row.input_role) for row in lineage] == [
        ("d1", "implemented_dividend"),
        ("d2", "implemented_dividend"),
        ("np", "net_profit"),
    ]


@pytest.mark.parametrize(
    ("metric_id", "role_facts", "expected"),
    [
        (
            "operating_cash_flow_dividend_coverage",
            {
                "operating_cash_flow": [_metric_fact("ocf", "25")],
                "implemented_dividend": [_metric_fact("div", "100000")],
            },
            Decimal("2.500000000000"),
        ),
        (
            "free_cash_flow_proxy_dividend_coverage",
            {
                "operating_cash_flow": [_metric_fact("ocf", "25")],
                "cash_paid_for_fixed_assets": [_metric_fact("capex", "5")],
                "implemented_dividend": [_metric_fact("div", "100000")],
            },
            Decimal("2.000000000000"),
        ),
        (
            "implemented_cash_dividend_per_share",
            {
                "implemented_per_share": [
                    _metric_fact("p1", "0.21", unit="CNY_PER_SHARE"),
                    _metric_fact("p2", "0.22", unit="CNY_PER_SHARE"),
                ]
            },
            Decimal("0.430000000000"),
        ),
    ],
)
def test_dividend_engine_formulas_are_computed_from_bound_facts(metric_id, role_facts, expected):
    definition = DividendRealizationMetricDefinitionRegistry.get(metric_id)
    result, lineage = DividendRealizationMetricEngine.compute(
        definition,
        symbol="601857.SH",
        fiscal_year=2025,
        role_facts=role_facts,
        revision_review_status="reviewed_unchanged",
        as_of_date="2026-07-01",
        created_at="2026-08-01T00:00:00+08:00",
    )
    assert result.value == expected
    assert len(lineage) == len(result.input_fact_ids)


def test_dividend_engine_zero_missing_and_raw_boundaries():
    payout = DividendRealizationMetricDefinitionRegistry.get("cash_dividend_payout_ratio")
    zero, _ = DividendRealizationMetricEngine.compute(
        payout,
        symbol="601857.SH",
        fiscal_year=2025,
        role_facts={
            "implemented_dividend": [_metric_fact("zero", "0")],
            "net_profit": [_metric_fact("np", "30")],
        },
        revision_review_status="x",
        as_of_date="2026-07-01",
    )
    assert zero.status == "undefined_no_dividend"
    assert zero.value is None

    missing, missing_lineage = DividendRealizationMetricEngine.compute(
        payout,
        symbol="601857.SH",
        fiscal_year=2025,
        role_facts={"implemented_dividend": [], "net_profit": [_metric_fact("np", "30")]},
        revision_review_status="x",
        as_of_date="2026-07-01",
    )
    assert missing.status == "missing_input"
    assert "implemented_dividend" in missing.missing_input_description
    assert [row.input_fact_id for row in missing_lineage] == ["np"]

    raw = _metric_fact("raw", "100")
    raw["source_tier"] = "company_official"
    with pytest.raises(MetricInputError):
        DividendRealizationMetricEngine.compute(
            payout,
            symbol="601857.SH",
            fiscal_year=2025,
            role_facts={"implemented_dividend": [raw], "net_profit": [_metric_fact("np", "30")]},
            revision_review_status="x",
            as_of_date="2026-07-01",
        )


def test_official_runner_is_offline_run_scoped_complete_and_idempotent(tmp_path):
    result = run_dividend_realization_vertical_slice(tmp_path, run_id="stage2f_test_run")
    assert result["status"] == "passed"
    assert result["fact_counts"] == {
        "old_facts": 354,
        "new_rule007_facts": 90,
        "final_facts": 444,
    }
    assert result["dividend_metric_counts"] == {
        "definitions": 4,
        "results": 20,
        "computed": 20,
        "lineage": 60,
    }
    assert result["roic_computation"] == "not_performed"
    assert result["scoring"] == "not_implemented"
    assert result["default_db_sha256_before"] == result["default_db_sha256_after"]
    run_dir = Path(result["run_directory"])
    required = {
        "metrics.duckdb",
        "definitions.json",
        "results.json",
        "latest.json",
        "PIT.json",
        "transitions.json",
        "lineage.json",
        "run_manifest.json",
        "summary.md",
    }
    assert required <= {item.name for item in run_dir.iterdir()}
    assert not list(run_dir.rglob("*.pdf"))
    assert not list(run_dir.rglob("*.png"))
    assert all(
        item["status"] == "computed"
        for item in json.loads(
            (run_dir / "dividend_metric_results.json").read_text(encoding="utf-8")
        )
    )
    assert (
        json.loads((run_dir / "metric_pit_snapshots.json").read_text(encoding="utf-8"))[-1][
            "computed_metric_count"
        ]
        == 16
    )

    rerun = run_dividend_realization_vertical_slice(tmp_path, run_id="stage2f_test_run")
    assert rerun["status"] == "passed"
    assert rerun["combined_counts"] == result["combined_counts"]
    assert rerun["old_metric_baseline"] == result["old_metric_baseline"]
