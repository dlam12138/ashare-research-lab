"""Frozen Rule 003 earnings-quality reconciliation contract."""

from __future__ import annotations

import copy
from pathlib import Path

import pytest

from ashare_research.facts.identity import build_fact_id
from ashare_research.facts.repository import FactRepository
from ashare_research.reconciliation.engine import (
    CAPEX_CASH_RECONCILIATION_RULE,
    EARNINGS_QUALITY_RECONCILIATION_RULE,
    EARNINGS_QUALITY_RULE_ID,
    EARNINGS_QUALITY_RULE_VERSION,
    RULE_ID,
    RULE_VERSION,
    SUPPLEMENTAL_RULE_ID,
    SUPPLEMENTAL_RULE_VERSION,
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

BUNDLE = Path(
    "acceptance/fixtures/official_facts/601857.SH/2025_annual.json"
)
SUPPORTED = {
    "net_profit_excluding_non_recurring",
    "operating_cost",
    "operating_profit",
}
RULE_001_OUTPUT_IDS = {
    "revenue": (
        "460056dc565a2ee49c9906554a29816a89ef25669390ecf3c6af407e5721e0f1"
    ),
    "net_profit_attributable_to_parent": (
        "9009dbb2ddaf6981e33d68fafd2cce681c0c87e591d30a1fa366d0051b38df6c"
    ),
    "operating_cash_flow": (
        "ad3b6e2a3675ce7e8a8e16bda427597b72d28e30808281e17cd4aa549949357a"
    ),
}
RULE_002_OUTPUT_ID = (
    "5dc4c375138e6cac5a26866d2120fc9d6bc68b69a19dabd56902ae0a6660b34f"
)


def _base_facts() -> tuple[dict, dict, dict]:
    bundle = load_bundle(BUNDLE)
    facts = build_source_facts(bundle, created_at="frozen-created-at")
    company = {fact["concept_id"]: fact for fact in facts["company"]}
    exchange = {fact["concept_id"]: fact for fact in facts["exchange"]}
    return bundle, company, exchange


def _pair(
    concept_id: str = "operating_profit",
    *,
    company_value: int = 23457900,
    exchange_value: int = 23457900,
    company_unit: str = "万元",
    exchange_unit: str = "万元",
) -> tuple[dict, dict]:
    _, company, exchange = _base_facts()
    result = []
    for template, value, unit in (
        (company["revenue"], company_value, company_unit),
        (exchange["revenue"], exchange_value, exchange_unit),
    ):
        fact = copy.deepcopy(template)
        fact.update(
            {
                "concept_id": concept_id,
                "value": value,
                "unit": unit,
                "source_page": "PDF page 109 / printed page 107",
                "source_table": "2025年度合并及公司利润表",
                "source_label": concept_id,
                "raw_value": value,
                "raw_unit": unit,
                "normalized_value": value,
                "normalization_rule": "test_exact_value",
            }
        )
        fact["fact_id"] = build_fact_id(fact)
        result.append(fact)
    return result[0], result[1]


def test_rule_003_identity_and_supported_concepts_are_frozen():
    rule = EARNINGS_QUALITY_RECONCILIATION_RULE
    assert rule.rule_id == EARNINGS_QUALITY_RULE_ID
    assert rule.version == EARNINGS_QUALITY_RULE_VERSION
    assert rule.supported_concepts == SUPPORTED
    assert (EARNINGS_QUALITY_RULE_ID, EARNINGS_QUALITY_RULE_VERSION) == (
        "RECON_OFFICIAL_NUMERIC_003",
        "1",
    )


@pytest.mark.parametrize("concept_id", sorted(SUPPORTED))
def test_rule_003_exact_match_uses_canonical_identity(concept_id: str):
    company, exchange = _pair(concept_id)
    result = ReconciliationEngine(
        EARNINGS_QUALITY_RECONCILIATION_RULE
    ).reconcile_pair(company, exchange, now="created-at")

    assert result.status == ReconciliationStatus.matched
    assert result.rule_id == EARNINGS_QUALITY_RULE_ID
    assert result.rule_version == EARNINGS_QUALITY_RULE_VERSION
    assert result.output_fact is not None
    assert result.output_fact["fact_id"] == build_fact_id(result.output_fact)
    assert result.output_fact["source_id"] == build_reconciliation_source_id(
        "601857.SH",
        EARNINGS_QUALITY_RULE_ID,
        EARNINGS_QUALITY_RULE_VERSION,
    )
    assert result.output_fact["eligible_for_metrics"] is True


def test_rule_003_rejects_every_other_concept():
    company, exchange = _pair("revenue")
    result = ReconciliationEngine(
        EARNINGS_QUALITY_RECONCILIATION_RULE
    ).reconcile_pair(company, exchange)
    assert result.status == ReconciliationStatus.insufficient_evidence
    assert result.output_fact is None


def test_rule_003_cross_unit_conversion_is_exact():
    company, exchange = _pair(
        company_value=23457900,
        exchange_value=234579000000,
        company_unit="万元",
        exchange_unit="元",
    )
    result = ReconciliationEngine(
        EARNINGS_QUALITY_RECONCILIATION_RULE
    ).reconcile_pair(company, exchange)
    assert result.status == ReconciliationStatus.matched
    assert result.company_normalized_value == "23457900"
    assert result.exchange_normalized_value == "23457900.0000"
    assert result.output_fact is not None
    assert result.output_fact["value"] == 23457900


def test_rule_003_rejects_unsafe_integer():
    unsafe = 2**53
    company, exchange = _pair(
        company_value=unsafe,
        exchange_value=unsafe,
    )
    result = ReconciliationEngine(
        EARNINGS_QUALITY_RECONCILIATION_RULE
    ).reconcile_pair(company, exchange)
    assert result.status == ReconciliationStatus.insufficient_evidence
    assert result.output_fact is None
    assert "safe-integer" in result.decision_reason


def test_rule_003_mismatch_service_writes_nothing(tmp_path: Path):
    bundle, _, _ = _base_facts()
    company, exchange = _pair(exchange_value=23458000)
    store = DuckDBStore(str(tmp_path / "rule003_mismatch.duckdb"))
    repo = FactRepository(store)
    repo.ensure_schema()
    repo.store_contexts([build_context(bundle, created_at="created-at")])
    service = OfficialFactReconciliationService(
        repo,
        engine=ReconciliationEngine(EARNINGS_QUALITY_RECONCILIATION_RULE),
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


def test_rule_003_matched_service_persists_rule_specific_lineage(
    tmp_path: Path,
):
    bundle, _, _ = _base_facts()
    company, exchange = _pair()
    store = DuckDBStore(str(tmp_path / "rule003_match.duckdb"))
    repo = FactRepository(store)
    repo.ensure_schema()
    repo.store_contexts([build_context(bundle, created_at="created-at")])
    service = OfficialFactReconciliationService(
        repo,
        engine=ReconciliationEngine(EARNINGS_QUALITY_RECONCILIATION_RULE),
    )
    result = service.reconcile_official_pair(company, exchange)
    assert result.status == ReconciliationStatus.matched
    rows = store.connect().execute(
        """SELECT reconciliation_rule_id, reconciliation_rule_version
             FROM fact_lineage ORDER BY lineage_id"""
    ).fetchall()
    assert rows == [
        (EARNINGS_QUALITY_RULE_ID, EARNINGS_QUALITY_RULE_VERSION),
        (EARNINGS_QUALITY_RULE_ID, EARNINGS_QUALITY_RULE_VERSION),
        (EARNINGS_QUALITY_RULE_ID, EARNINGS_QUALITY_RULE_VERSION),
    ]
    store.close()


def test_rules_001_and_002_outputs_remain_frozen():
    _, company, exchange = _base_facts()
    rule_001 = ReconciliationEngine()
    for concept_id, expected_id in RULE_001_OUTPUT_IDS.items():
        result = rule_001.reconcile_pair(
            company[concept_id], exchange[concept_id]
        )
        assert (result.rule_id, result.rule_version) == (
            RULE_ID,
            RULE_VERSION,
        )
        assert result.output_fact is not None
        assert result.output_fact["fact_id"] == expected_id

    capex_company, capex_exchange = _pair(
        "cash_paid_for_fixed_assets",
        company_value=29278900,
        exchange_value=29278900,
    )
    rule_002_result = ReconciliationEngine(
        CAPEX_CASH_RECONCILIATION_RULE
    ).reconcile_pair(capex_company, capex_exchange)
    assert (rule_002_result.rule_id, rule_002_result.rule_version) == (
        SUPPLEMENTAL_RULE_ID,
        SUPPLEMENTAL_RULE_VERSION,
    )
    assert rule_002_result.output_fact is not None
    assert rule_002_result.output_fact["fact_id"] == RULE_002_OUTPUT_ID


def test_rule_003_unverified_input_writes_nothing(tmp_path: Path):
    bundle, _, _ = _base_facts()
    company, exchange = _pair()
    company["verification_status"] = "unverified"
    store = DuckDBStore(str(tmp_path / "rule003_invalid.duckdb"))
    repo = FactRepository(store)
    repo.ensure_schema()
    repo.store_contexts([build_context(bundle, created_at="created-at")])
    service = OfficialFactReconciliationService(
        repo,
        engine=ReconciliationEngine(EARNINGS_QUALITY_RECONCILIATION_RULE),
    )
    result = service.reconcile_official_pair(company, exchange)
    assert result.status == ReconciliationStatus.insufficient_evidence
    assert result.output_fact is None
    assert store.connect().execute(
        "SELECT COUNT(*) FROM financial_facts"
    ).fetchone()[0] == 0
    store.close()
