from copy import deepcopy
from dataclasses import replace

import pytest

from ashare_research.metrics.definitions import MetricDefinitionRegistry
from ashare_research.metrics.engine import MetricEngine
from ashare_research.metrics.identity import MetricIdentityError, build_metric_result_id
from ashare_research.metrics.repository import (
    MetricRepository,
    MetricRepositoryError,
)


def _fact(concept: str, value: int, year: int = 2022) -> dict:
    return {
        "fact_id": f"{concept}-{year}-{value}",
        "value": value,
        "unit": "万元",
        "source_tier": "reconciled_derived",
        "eligible_for_metrics": True,
        "fact_version": 1,
        "restatement_version": "original",
        "available_at": f"{year + 1}-03-30",
        "period_end": f"{year}-12-31",
    }


def _result(version: int = 1, predecessor: str = ""):
    result, lineage = MetricEngine.compute(
        MetricDefinitionRegistry.get("revenue_yoy"),
        symbol="601857.SH",
        fiscal_year=2022,
        primary_fact=_fact("revenue", 11),
        secondary_fact=_fact("revenue", 10, 2021),
        result_version=version,
        supersedes_metric_result_id=predecessor,
        revision_review_status="reviewed_unchanged",
        as_of_date="2023-03-30",
        created_at="2026-07-30",
    )
    return result, lineage


@pytest.fixture
def repo(tmp_path):
    repository = MetricRepository(str(tmp_path / "metrics.duckdb"))
    repository.ensure_schema(applied_at="2026-07-30")
    yield repository
    repository.close()


def test_repository_uses_decimal_not_double(repo):
    row = repo.connect().execute(
        "SELECT data_type FROM information_schema.columns "
        "WHERE table_name='metric_results' AND column_name='value'"
    ).fetchone()
    assert row[0] == "DECIMAL(38,12)"


def test_canonical_insert_and_idempotent_repeat(repo):
    result, lineage = _result()
    assert repo.store_results([result], lineage) == (1, 2)
    assert repo.store_results([result], lineage) == (0, 0)


def test_semantic_conflict_rejected(repo):
    result, lineage = _result()
    repo.store_results([result], lineage)
    conflict = deepcopy(result)
    conflict.revision_review_status = "different"
    with pytest.raises(MetricRepositoryError, match="semantic conflict"):
        repo.store_results([conflict], lineage)


def test_legal_v2_chain(repo):
    first, first_lineage = _result()
    repo.store_results([first], first_lineage)
    second, second_lineage = _result(2, first.metric_result_id)
    assert repo.store_results([second], second_lineage) == (1, 2)
    assert second.supersedes_metric_result_id == first.metric_result_id


def test_missing_or_cross_metric_predecessor_rejected(repo):
    second, lineage = _result(2, "a" * 64)
    with pytest.raises(MetricRepositoryError, match="does not exist"):
        repo.store_results([second], lineage)

    first, first_lineage = _result()
    repo.store_results([first], first_lineage)
    wrong = replace(
        first,
        metric_id="operating_cash_flow_yoy",
        result_version=2,
        supersedes_metric_result_id=first.metric_result_id,
    )
    wrong = replace(wrong, metric_result_id=build_metric_result_id(wrong))
    with pytest.raises(MetricRepositoryError, match="stable field"):
        repo.store_results([wrong], [])


def test_transaction_failure_leaves_no_partial_results(repo):
    valid, lineage = _result()
    invalid = replace(valid, metric_result_id="not-canonical")
    with pytest.raises(MetricIdentityError), repo.transaction() as conn:
        repo.store_results([valid, invalid], lineage, conn=conn)
    assert repo.all_results() == []
