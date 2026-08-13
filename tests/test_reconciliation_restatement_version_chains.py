"""Service contract tests for official restatement version chains."""

from __future__ import annotations

from pathlib import Path

import pytest

from ashare_research.exceptions import ReconciliationValidationError
from ashare_research.facts.identity import build_fact_id
from ashare_research.facts.repository import FactRepository
from ashare_research.reconciliation.service import OfficialFactReconciliationService
from ashare_research.storage.duckdb_store import DuckDBStore

SYMBOL = "601857.SH"
CONTEXT_ID = "601857.SH|2022|annual|consolidated"
HASH64 = "a" * 64


def _repo(tmp_path: Path) -> FactRepository:
    store = DuckDBStore(str(tmp_path / "restatement.duckdb"))
    store.connect()
    repo = FactRepository(store)
    repo.ensure_schema()
    context = {
        "context_id": CONTEXT_ID,
        "symbol": SYMBOL,
        "fiscal_year": 2022,
        "period_type": "annual",
        "period_start": "2022-01-01",
        "period_end": "2022-12-31",
        "instant_or_duration": "duration",
        "consolidation_scope": "consolidated",
        "accounting_standard": "CAS",
        "restatement_version": "original",
        "source_document": "2022 annual report",
        "filing_date": "2023-03-30",
        "created_at": "2026-07-30T00:00:00",
    }
    with repo.transaction() as conn:
        repo.store_contexts([context], conn=conn)
    return repo


def _raw_fact(
    tier: str,
    *,
    concept_id: str = "revenue",
    value: int = 100,
    source_id: str | None = None,
) -> dict:
    source = "company" if tier == "company_official" else "exchange"
    fact = {
        "concept_id": concept_id,
        "concept_version": "1",
        "symbol": SYMBOL,
        "value": value,
        "unit": "万元",
        "context_id": CONTEXT_ID,
        "is_derived": False,
        "derived_from": "",
        "derivation_definition_id": "",
        "derivation_version": "",
        "input_fact_ids": "",
        "source_provider": f"{source}_provider",
        "source_id": source_id or f"{source}:601857.SH:2022:{concept_id}",
        "source_tier": tier,
        "source_document": "2022 annual report",
        "source_url": f"https://example.com/{source}/2022.pdf",
        "source_hash": HASH64,
        "source_page": "100",
        "source_table": "consolidated statement",
        "source_label": concept_id,
        "fact_version": 1,
        "restatement_version": "original",
        "supersedes_fact_id": "",
        "fiscal_year": 2022,
        "report_type": "annual",
        "period_end": "2022-12-31",
        "filing_date": "2023-03-30",
        "announcement_date": "2023-03-30",
        "available_at": "2023-03-30",
        "raw_value": value,
        "raw_unit": "万元",
        "normalized_value": value,
        "normalization_rule": "identity",
        "verification_status": "verified",
        "verification_note": "official",
        "eligible_for_metrics": False,
        "created_at": "2026-07-30T00:00:00",
    }
    fact["fact_id"] = build_fact_id(fact)
    return fact


def _v2(
    predecessor: dict,
    *,
    value: int = 101,
    available_at: str = "2024-03-26",
    **changes: object,
) -> dict:
    fact = {
        **predecessor,
        "value": value,
        "normalized_value": value,
        "raw_value": value,
        "fact_version": 2,
        "restatement_version": "restated_1",
        "supersedes_fact_id": predecessor["fact_id"],
        "source_document": "2023 annual report comparative column",
        "source_url": predecessor["source_url"].replace("2022", "2023"),
        "source_hash": "b" * 64,
        "source_page": "101",
        "filing_date": available_at,
        "announcement_date": available_at,
        "available_at": available_at,
        "created_at": "2026-07-30T01:00:00",
    }
    fact.update(changes)
    fact["fact_id"] = build_fact_id(fact)
    return fact


def _seed_v1(
    repo: FactRepository,
    *,
    concept_id: str = "revenue",
    value: int = 100,
) -> tuple[dict, dict, dict]:
    company = _raw_fact(
        "company_official", concept_id=concept_id, value=value
    )
    exchange = _raw_fact(
        "exchange_official", concept_id=concept_id, value=value
    )
    result = OfficialFactReconciliationService(repo).reconcile_official_pair(
        company, exchange
    )
    assert result.output_fact is not None
    return company, exchange, result.output_fact


def _counts(repo: FactRepository) -> tuple[int, int]:
    conn = repo.store.connect()
    facts = conn.execute("SELECT COUNT(*) FROM financial_facts").fetchone()[0]
    lineage = conn.execute("SELECT COUNT(*) FROM fact_lineage").fetchone()[0]
    return facts, lineage


def test_legal_company_and_exchange_v2_input_chains_pass(tmp_path: Path):
    repo = _repo(tmp_path)
    company_v1, exchange_v1, output_v1 = _seed_v1(repo)
    company_v2 = _v2(company_v1)
    exchange_v2 = _v2(exchange_v1)

    result = OfficialFactReconciliationService(repo).reconcile_official_pair(
        company_v2,
        exchange_v2,
        output_supersedes_fact_id=output_v1["fact_id"],
    )

    assert result.output_fact is not None
    assert result.output_fact["fact_version"] == 2
    assert _counts(repo) == (6, 6)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("supersedes_fact_id", "f" * 64, "non-existent"),
        ("fact_version", 3, "increment"),
        ("source_id", "changed-source-id", "stable identity"),
        ("available_at", "2023-03-29", "backwards"),
    ],
)
def test_invalid_input_chain_is_zero_write(
    tmp_path: Path,
    field: str,
    value: object,
    message: str,
):
    repo = _repo(tmp_path)
    company_v1, exchange_v1, output_v1 = _seed_v1(repo)
    company_v2 = _v2(company_v1, **{field: value})
    exchange_v2 = _v2(exchange_v1)
    before = _counts(repo)

    with pytest.raises(ReconciliationValidationError, match=message):
        OfficialFactReconciliationService(repo).reconcile_official_pair(
            company_v2,
            exchange_v2,
            output_supersedes_fact_id=output_v1["fact_id"],
        )

    assert _counts(repo) == before


def test_output_v2_requires_explicit_supersedes_id(tmp_path: Path):
    repo = _repo(tmp_path)
    company_v1, exchange_v1, _ = _seed_v1(repo)
    before = _counts(repo)

    with pytest.raises(ReconciliationValidationError, match="requires a complete"):
        OfficialFactReconciliationService(repo).reconcile_official_pair(
            _v2(company_v1),
            _v2(exchange_v1),
        )

    assert _counts(repo) == before


def test_output_v2_predecessor_must_exist(tmp_path: Path):
    repo = _repo(tmp_path)
    company_v1, exchange_v1, _ = _seed_v1(repo)
    before = _counts(repo)

    with pytest.raises(ReconciliationValidationError, match="non-existent"):
        OfficialFactReconciliationService(repo).reconcile_official_pair(
            _v2(company_v1),
            _v2(exchange_v1),
            output_supersedes_fact_id="f" * 64,
        )

    assert _counts(repo) == before


def test_output_v2_predecessor_must_have_same_concept(tmp_path: Path):
    repo = _repo(tmp_path)
    company_v1, exchange_v1, _ = _seed_v1(repo)
    _, _, other_output_v1 = _seed_v1(
        repo,
        concept_id="operating_cash_flow",
        value=500,
    )
    before = _counts(repo)

    with pytest.raises(ReconciliationValidationError, match="stable identity"):
        OfficialFactReconciliationService(repo).reconcile_official_pair(
            _v2(company_v1),
            _v2(exchange_v1),
            output_supersedes_fact_id=other_output_v1["fact_id"],
        )

    assert _counts(repo) == before


def test_legal_v2_output_is_canonical_and_supersedes_v1(tmp_path: Path):
    repo = _repo(tmp_path)
    company_v1, exchange_v1, output_v1 = _seed_v1(repo)

    result = OfficialFactReconciliationService(repo).reconcile_official_pair(
        _v2(company_v1),
        _v2(exchange_v1),
        output_supersedes_fact_id=output_v1["fact_id"],
    )

    output_v2 = result.output_fact
    assert output_v2 is not None
    assert output_v2["supersedes_fact_id"] == output_v1["fact_id"]
    assert output_v2["fact_id"] == build_fact_id(output_v2)
    assert output_v2["restatement_version"] == "restated_1"


def test_v1_output_rejects_supersedes_parameter(tmp_path: Path):
    repo = _repo(tmp_path)
    company = _raw_fact("company_official")
    exchange = _raw_fact("exchange_official")

    with pytest.raises(ReconciliationValidationError, match="Version 1"):
        OfficialFactReconciliationService(repo).reconcile_official_pair(
            company,
            exchange,
            output_supersedes_fact_id="f" * 64,
        )

    assert _counts(repo) == (0, 0)


def test_repeated_v2_run_is_fact_idempotent(tmp_path: Path):
    repo = _repo(tmp_path)
    company_v1, exchange_v1, output_v1 = _seed_v1(repo)
    company_v2 = _v2(company_v1)
    exchange_v2 = _v2(exchange_v1)
    service = OfficialFactReconciliationService(repo)

    first = service.reconcile_official_pair(
        company_v2,
        exchange_v2,
        output_supersedes_fact_id=output_v1["fact_id"],
    )
    facts_after_first, lineage_after_first = _counts(repo)
    second = service.reconcile_official_pair(
        company_v2,
        exchange_v2,
        output_supersedes_fact_id=output_v1["fact_id"],
    )
    facts_after_second, lineage_after_second = _counts(repo)

    assert first.output_fact["fact_id"] == second.output_fact["fact_id"]
    assert facts_after_first == facts_after_second == 6
    assert lineage_after_second == lineage_after_first + 3
