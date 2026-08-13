"""Frozen Rule 004 balance-sheet instant denominator reconciliation contract.

Rule 004 reconciles ``total_assets`` and ``equity_attributable_to_parent``
-- both instant (balance-sheet) concepts -- across the company_official and
exchange_official paths.  This is dual-source verification, never subtraction,
so the narrowed ``FACT_INSTANT_001`` (which permits
``official_dual_source_reconciliation``) must let these reconciled instant
facts through while still blocking subtraction-derived instant facts.
"""

from __future__ import annotations

import copy
from pathlib import Path

import pytest

from ashare_research.facts.identity import build_fact_id
from ashare_research.facts.repository import FactRepository
from ashare_research.reconciliation.engine import (
    EARNINGS_QUALITY_RECONCILIATION_RULE,
    EARNINGS_QUALITY_RULE_ID,
    EARNINGS_QUALITY_RULE_VERSION,
    ROE_ROA_DENOMINATOR_RECONCILIATION_RULE,
    ROE_ROA_DENOMINATOR_RULE_ID,
    ROE_ROA_DENOMINATOR_RULE_VERSION,
    RULE_ID,
    RULE_VERSION,
    ReconciliationEngine,
    build_reconciliation_source_id,
)
from ashare_research.reconciliation.models import ReconciliationStatus
from ashare_research.reconciliation.service import (
    OfficialFactReconciliationService,
)
from ashare_research.storage.duckdb_store import DuckDBStore
from ashare_research.tools.official_fact_acceptance import (
    build_context,
    build_source_facts,
    load_bundle,
)
from ashare_research.validation.validator import FactValidator

BUNDLE = Path("acceptance/fixtures/official_facts/601857.SH/2024_annual.json")
SUPPORTED = {"total_assets", "equity_attributable_to_parent"}
INSTANT_CONTEXT_ID = "601857.SH|2024|instant|consolidated"
INSTANT_PERIOD = "2024-12-31"
# Real 2024 consolidated balance-sheet values (RMB million -> 万元 x100).
DENOMINATOR_VALUES = {
    "total_assets": 275300700,
    "equity_attributable_to_parent": 151537100,
}


def _base_facts() -> tuple[dict, dict, dict]:
    bundle = load_bundle(BUNDLE)
    facts = build_source_facts(bundle, created_at="frozen-created-at")
    company = {fact["concept_id"]: fact for fact in facts["company"]}
    exchange = {fact["concept_id"]: fact for fact in facts["exchange"]}
    return bundle, company, exchange


def _instant_pair(
    concept_id: str = "total_assets",
    *,
    company_value: int | None = None,
    exchange_value: int | None = None,
    company_unit: str = "万元",
    exchange_unit: str = "万元",
) -> tuple[dict, dict]:
    """Build a company/exchange instant-fact pair for one denominator concept."""
    bundle, company, _ = _base_facts()
    if company_value is None:
        company_value = DENOMINATOR_VALUES[concept_id]
    if exchange_value is None:
        exchange_value = DENOMINATOR_VALUES[concept_id]
    document = bundle["documents"]["company"]
    exchange_document = bundle["documents"]["exchange"]
    result = []
    for template, value, unit, doc in (
        (company["revenue"], company_value, company_unit, document),
        (company["revenue"], exchange_value, exchange_unit, exchange_document),
    ):
        fact = copy.deepcopy(template)
        fact.update(
            {
                "concept_id": concept_id,
                "value": value,
                "unit": unit,
                "context_id": INSTANT_CONTEXT_ID,
                "period_start": INSTANT_PERIOD,
                "period_end": INSTANT_PERIOD,
                "source_provider": doc["source_provider"],
                "source_id": doc["source_id"],
                "source_tier": doc["source_tier"],
                "source_document": doc["source_document"],
                "source_url": doc["final_pdf_url"],
                "source_hash": doc["sha256"],
                "source_page": "PDF page 113 / printed page 111",
                "source_table": "2024 年 12 月 31 日合并及公司资产负债表",
                "source_label": concept_id,
                "raw_value": value,
                "raw_unit": unit,
                "normalized_value": value,
                "normalization_rule": "test_exact_value",
                "filing_date": doc["announcement_date"],
                "announcement_date": doc["announcement_date"],
                "available_at": doc["announcement_date"],
            }
        )
        fact["fact_id"] = build_fact_id(fact)
        result.append(fact)
    return result[0], result[1]


def test_rule_004_identity_and_supported_concepts_are_frozen():
    rule = ROE_ROA_DENOMINATOR_RECONCILIATION_RULE
    assert rule.rule_id == ROE_ROA_DENOMINATOR_RULE_ID
    assert rule.version == ROE_ROA_DENOMINATOR_RULE_VERSION
    assert rule.supported_concepts == SUPPORTED
    assert (ROE_ROA_DENOMINATOR_RULE_ID, ROE_ROA_DENOMINATOR_RULE_VERSION) == (
        "RECON_OFFICIAL_NUMERIC_004",
        "1",
    )


@pytest.mark.parametrize("concept_id", sorted(SUPPORTED))
def test_rule_004_exact_match_uses_canonical_identity(concept_id: str):
    company, exchange = _instant_pair(concept_id)
    result = ReconciliationEngine(
        ROE_ROA_DENOMINATOR_RECONCILIATION_RULE
    ).reconcile_pair(company, exchange, now="created-at")

    assert result.status == ReconciliationStatus.matched
    assert result.rule_id == ROE_ROA_DENOMINATOR_RULE_ID
    assert result.rule_version == ROE_ROA_DENOMINATOR_RULE_VERSION
    assert result.output_fact is not None
    assert result.output_fact["fact_id"] == build_fact_id(result.output_fact)
    assert result.output_fact["source_id"] == build_reconciliation_source_id(
        "601857.SH",
        ROE_ROA_DENOMINATOR_RULE_ID,
        ROE_ROA_DENOMINATOR_RULE_VERSION,
    )
    assert result.output_fact["eligible_for_metrics"] is True
    assert result.output_fact["value"] == DENOMINATOR_VALUES[concept_id]


@pytest.mark.parametrize("concept_id", sorted(SUPPORTED))
def test_rule_004_reconciled_instant_fact_passes_validator(concept_id: str):
    """FACT_INSTANT_001 (narrowed) must not reject a dual-source reconciled
    instant fact."""
    company, exchange = _instant_pair(concept_id)
    output = ReconciliationEngine(
        ROE_ROA_DENOMINATOR_RECONCILIATION_RULE
    ).reconcile_pair(company, exchange, now="created-at").output_fact
    assert output is not None
    errors = [
        result
        for result in FactValidator().validate_single_fact(output)
        if result.severity == "error" and not result.passed
    ]
    assert not errors, errors


def test_fact_instant_001_still_blocks_subtraction_derivation():
    """A subtraction-derived instant fact (non-reconciliation derivation)
    must still fail FACT_INSTANT_001."""
    _, company, _ = _base_facts()
    fact = copy.deepcopy(company["revenue"])
    fact.update(
        {
            "concept_id": "total_assets",
            "context_id": INSTANT_CONTEXT_ID,
            "period_start": INSTANT_PERIOD,
            "period_end": INSTANT_PERIOD,
            "is_derived": True,
            "derivation_definition_id": "single_quarter_total_assets",
            "derivation_version": "1",
            "input_fact_ids": "a,b",
            "source_tier": "reconciled_derived",
            "source_provider": "official_reconciliation",
            "source_id": "reconciled:601857.SH:company_exchange:test:v1",
            "verification_status": "reconciled",
            "eligible_for_metrics": True,
        }
    )
    fact["fact_id"] = build_fact_id(fact)
    errors = [
        result
        for result in FactValidator().validate_single_fact(fact)
        if result.severity == "error" and not result.passed
    ]
    assert any(result.rule_id == "FACT_INSTANT_001" for result in errors)


def test_rule_004_rejects_every_other_concept():
    company, exchange = _instant_pair("total_assets")
    # Force an unsupported instant concept onto the pair.
    for fact in (company, exchange):
        fact["concept_id"] = "total_equity"
        fact["fact_id"] = build_fact_id(fact)
    result = ReconciliationEngine(
        ROE_ROA_DENOMINATOR_RECONCILIATION_RULE
    ).reconcile_pair(company, exchange)
    assert result.status == ReconciliationStatus.insufficient_evidence
    assert result.output_fact is None


def test_rule_004_cross_unit_conversion_is_exact():
    company, exchange = _instant_pair(
        company_value=275300700,
        exchange_value=2753007000000,
        company_unit="万元",
        exchange_unit="元",
    )
    result = ReconciliationEngine(
        ROE_ROA_DENOMINATOR_RECONCILIATION_RULE
    ).reconcile_pair(company, exchange)
    assert result.status == ReconciliationStatus.matched
    assert result.company_normalized_value == "275300700"
    assert result.exchange_normalized_value == "275300700.0000"
    assert result.output_fact is not None
    assert result.output_fact["value"] == 275300700


def test_rule_004_rejects_unsafe_integer():
    unsafe = 2**53
    company, exchange = _instant_pair(
        company_value=unsafe,
        exchange_value=unsafe,
    )
    result = ReconciliationEngine(
        ROE_ROA_DENOMINATOR_RECONCILIATION_RULE
    ).reconcile_pair(company, exchange)
    assert result.status == ReconciliationStatus.insufficient_evidence
    assert result.output_fact is None
    assert "safe-integer" in result.decision_reason


def _store_with_context(tmp_path: Path, bundle: dict) -> tuple[DuckDBStore, FactRepository]:
    store = DuckDBStore(str(tmp_path / "rule004.duckdb"))
    repo = FactRepository(store)
    repo.ensure_schema()
    repo.store_contexts([build_context(bundle, created_at="created-at")])
    return store, repo


def test_rule_004_mismatch_service_writes_nothing(tmp_path: Path):
    bundle, _, _ = _base_facts()
    company, exchange = _instant_pair(exchange_value=275300800)
    store, repo = _store_with_context(tmp_path, bundle)
    # The instant context must exist before the service will write.
    repo.store_contexts([
        {
            "context_id": INSTANT_CONTEXT_ID,
            "symbol": "601857.SH",
            "fiscal_year": 2024,
            "period_type": "instant",
            "period_start": INSTANT_PERIOD,
            "period_end": INSTANT_PERIOD,
            "instant_or_duration": "instant",
            "consolidation_scope": "consolidated",
            "accounting_standard": "CAS",
            "restatement_version": "original",
            "source_document": "2024 annual report",
            "filing_date": "2025-03-31",
            "created_at": "created-at",
        }
    ])
    service = OfficialFactReconciliationService(
        repo,
        engine=ReconciliationEngine(ROE_ROA_DENOMINATOR_RECONCILIATION_RULE),
    )
    result = service.reconcile_official_pair(company, exchange)
    assert result.status == ReconciliationStatus.mismatch
    assert result.output_fact is None
    assert store.connect().execute(
        "SELECT COUNT(*) FROM financial_facts"
    ).fetchone()[0] == 0
    assert store.connect().execute(
        "SELECT COUNT(*) FROM fact_lineage"
    ).fetchone()[0] == 0
    store.close()


def test_rule_004_matched_service_persists_rule_specific_lineage(tmp_path: Path):
    bundle, _, _ = _base_facts()
    company, exchange = _instant_pair()
    store, repo = _store_with_context(tmp_path, bundle)
    repo.store_contexts([
        {
            "context_id": INSTANT_CONTEXT_ID,
            "symbol": "601857.SH",
            "fiscal_year": 2024,
            "period_type": "instant",
            "period_start": INSTANT_PERIOD,
            "period_end": INSTANT_PERIOD,
            "instant_or_duration": "instant",
            "consolidation_scope": "consolidated",
            "accounting_standard": "CAS",
            "restatement_version": "original",
            "source_document": "2024 annual report",
            "filing_date": "2025-03-31",
            "created_at": "created-at",
        }
    ])
    service = OfficialFactReconciliationService(
        repo,
        engine=ReconciliationEngine(ROE_ROA_DENOMINATOR_RECONCILIATION_RULE),
    )
    result = service.reconcile_official_pair(company, exchange)
    assert result.status == ReconciliationStatus.matched
    rows = store.connect().execute(
        """SELECT reconciliation_rule_id, reconciliation_rule_version
             FROM fact_lineage ORDER BY lineage_id"""
    ).fetchall()
    assert rows == [
        (ROE_ROA_DENOMINATOR_RULE_ID, ROE_ROA_DENOMINATOR_RULE_VERSION),
        (ROE_ROA_DENOMINATOR_RULE_ID, ROE_ROA_DENOMINATOR_RULE_VERSION),
        (ROE_ROA_DENOMINATOR_RULE_ID, ROE_ROA_DENOMINATOR_RULE_VERSION),
    ]
    store.close()


def test_rules_001_and_003_still_reconcile_duration_concepts():
    """Rule 004's instant scope and the FACT_INSTANT_001 narrowing must not
    disturb Rule 001/003 duration reconciliation.  Exact Rule 001/002/003
    output Fact IDs remain frozen by ``test_earnings_quality_reconciliation_rule``.
    """
    _, company, exchange = _base_facts()
    rule_001 = ReconciliationEngine()
    for concept_id in ("revenue", "net_profit_attributable_to_parent", "operating_cash_flow"):
        result = rule_001.reconcile_pair(
            company[concept_id], exchange[concept_id]
        )
        assert (result.rule_id, result.rule_version) == (RULE_ID, RULE_VERSION)
        assert result.status == ReconciliationStatus.matched
        assert result.output_fact is not None
        assert result.output_fact["fact_id"] == build_fact_id(
            result.output_fact
        )

    # Rule 003 still rejects revenue (out of its scope).
    rule_003_result = ReconciliationEngine(
        EARNINGS_QUALITY_RECONCILIATION_RULE
    ).reconcile_pair(company["revenue"], exchange["revenue"])
    assert (rule_003_result.rule_id, rule_003_result.rule_version) == (
        EARNINGS_QUALITY_RULE_ID,
        EARNINGS_QUALITY_RULE_VERSION,
    )
    assert rule_003_result.status == ReconciliationStatus.insufficient_evidence
    assert rule_003_result.output_fact is None
