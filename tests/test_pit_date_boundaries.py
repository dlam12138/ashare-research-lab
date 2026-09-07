"""PIT cutoffs must not expose future facts through alternate ISO syntax."""

from datetime import date

import pytest
from fact_test_helpers import make_verified_fact

from ashare_research.exceptions import PointInTimeError
from ashare_research.facts.as_of import AsOfQuery
from ashare_research.facts.repository import FactRepository
from ashare_research.storage.duckdb_store import DuckDBStore


@pytest.fixture
def repo():
    store = DuckDBStore(":memory:")
    repository = FactRepository(store)
    repository.ensure_schema()
    fact = make_verified_fact(available_at="2025-12-31")
    repository.store_facts([fact])
    # The latest-snapshot query joins context scope; include a real context row.
    store.connect().execute(
        "INSERT INTO fact_contexts (context_id, symbol, fiscal_year, period_type) "
        "VALUES (?, ?, ?, ?)",
        [fact["context_id"], "000001.SZ", 2024, "annual"],
    )
    yield repository
    store.close()


@pytest.mark.parametrize("entry", ["query", "latest", "repo_query", "repo_latest"])
@pytest.mark.parametrize("cutoff", [
    "20250601", "2025-W22-7", "2025-06-01T00:00:00", " 2025-06-01",
    "2025-06-01 ", "2025-6-1", "2025-02-29", "2025-13-01", "", " ",
    20250601, False, [], date(2025, 6, 1),
])
def test_invalid_cutoff_never_becomes_an_unfiltered_or_future_query(repo, entry, cutoff):
    with pytest.raises(PointInTimeError):
        _query(repo, entry, cutoff)


def _query(repo, entry, cutoff):
    owner = repo if entry.startswith("repo_") else AsOfQuery(repo)
    method = owner.get_latest_available if entry.endswith("latest") else (
        owner.query_facts if owner is repo else owner.query
    )
    return method(symbol="000001.SZ", as_of_date=cutoff)


@pytest.mark.parametrize("entry", ["query", "latest", "repo_query", "repo_latest"])
@pytest.mark.parametrize("cutoff, count", [
    ("2024-02-29", 0), ("2025-06-01", 0), ("2025-12-30", 0),
    ("2025-12-31", 1), ("2026-01-01", 1),
])
def test_pit_calendar_boundary_is_inclusive(repo, entry, cutoff, count):
    assert len(_query(repo, entry, cutoff)) == count


def test_only_optional_repository_cutoff_allows_none(repo):
    assert len(repo.query_facts("000001.SZ")) == 1
    assert len(repo.query_facts("000001.SZ", as_of_date=None)) == 1
    for entry in ("query", "latest", "repo_latest"):
        with pytest.raises(PointInTimeError):
            _query(repo, entry, None)


@pytest.mark.parametrize("parameter", ["date1", "date2", "period_end"])
def test_comparison_validates_every_supplied_date(repo, parameter):
    args = dict(period_end="2024-12-31", date1="2025-06-01", date2="2025-12-31")
    args[parameter] = "20250601"
    with pytest.raises(PointInTimeError):
        AsOfQuery(repo).compare_versions("000001.SZ", ["revenue"], **args)
