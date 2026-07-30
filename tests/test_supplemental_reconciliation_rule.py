"""Frozen rule 001 and supplemental rule 002 contracts."""

from __future__ import annotations

import copy
from pathlib import Path

from ashare_research.facts.identity import build_fact_id
from ashare_research.facts.repository import FactRepository
from ashare_research.reconciliation.engine import (
    CAPEX_CASH_RECONCILIATION_RULE,
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
LEGACY_OUTPUT_IDS = {
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


def _source_facts() -> tuple[dict, dict, dict]:
    bundle = load_bundle(BUNDLE)
    facts = build_source_facts(bundle, created_at="frozen-created-at")
    company = {fact["concept_id"]: fact for fact in facts["company"]}
    exchange = {fact["concept_id"]: fact for fact in facts["exchange"]}
    return bundle, company, exchange


def _capex_pair() -> tuple[dict, dict]:
    _, company, exchange = _source_facts()
    pair = []
    for source in (company["revenue"], exchange["revenue"]):
        fact = copy.deepcopy(source)
        fact.update(
            {
                "concept_id": "cash_paid_for_fixed_assets",
                "value": 29278900,
                "source_page": "PDF page 110 / printed page 108",
                "source_table": "2025年度合并及公司现金流量表",
                "source_label": (
                    "购建固定资产、油气资产、无形资产和其他长期资产支付的现金"
                ),
                "raw_value": 292789,
                "raw_unit": "人民币百万元",
                "normalized_value": 29278900,
                "normalization_rule": "RMB_MILLION_TO_CNY_10K_X100",
            }
        )
        fact["fact_id"] = build_fact_id(fact)
        pair.append(fact)
    return pair[0], pair[1]


def test_rule_001_all_three_outputs_and_identities_are_frozen():
    _, company, exchange = _source_facts()
    engine = ReconciliationEngine()

    for concept_id, expected_fact_id in LEGACY_OUTPUT_IDS.items():
        result = engine.reconcile_pair(
            company[concept_id],
            exchange[concept_id],
            now="different-created-at",
        )
        assert result.status == ReconciliationStatus.matched
        assert result.rule_id == RULE_ID
        assert result.rule_version == RULE_VERSION
        assert result.output_fact is not None
        assert result.output_fact["fact_id"] == expected_fact_id
        assert result.output_fact["source_id"] == build_reconciliation_source_id(
            "601857.SH", RULE_ID, RULE_VERSION
        )


def test_rule_001_rejects_supplemental_concept():
    company, exchange = _capex_pair()
    result = ReconciliationEngine().reconcile_pair(company, exchange)
    assert result.status == ReconciliationStatus.insufficient_evidence
    assert result.output_fact is None
    assert result.rule_id == RULE_ID


def test_rule_002_only_accepts_capex_cash():
    company, exchange = _capex_pair()
    engine = ReconciliationEngine(CAPEX_CASH_RECONCILIATION_RULE)
    result = engine.reconcile_pair(company, exchange, now="created-at")

    assert result.status == ReconciliationStatus.matched
    assert result.rule_id == SUPPLEMENTAL_RULE_ID
    assert result.rule_version == SUPPLEMENTAL_RULE_VERSION
    assert result.output_fact is not None
    assert result.output_fact["concept_id"] == "cash_paid_for_fixed_assets"
    assert result.output_fact["value"] == 29278900
    assert result.output_fact["source_id"] == build_reconciliation_source_id(
        "601857.SH", SUPPLEMENTAL_RULE_ID, SUPPLEMENTAL_RULE_VERSION
    )

    _, legacy_company, legacy_exchange = _source_facts()
    rejected = engine.reconcile_pair(
        legacy_company["revenue"], legacy_exchange["revenue"]
    )
    assert rejected.status == ReconciliationStatus.insufficient_evidence
    assert rejected.output_fact is None


def test_rule_002_mismatch_emits_no_output():
    company, exchange = _capex_pair()
    exchange["value"] += 100
    exchange["normalized_value"] += 100
    exchange["fact_id"] = build_fact_id(exchange)
    result = ReconciliationEngine(
        CAPEX_CASH_RECONCILIATION_RULE
    ).reconcile_pair(company, exchange)
    assert result.status == ReconciliationStatus.mismatch
    assert result.output_fact is None


def test_rule_002_service_persists_rule_specific_lineage(tmp_path: Path):
    bundle, _, _ = _source_facts()
    company, exchange = _capex_pair()
    store = DuckDBStore(str(tmp_path / "rule002.duckdb"))
    repo = FactRepository(store)
    repo.ensure_schema()
    repo.store_contexts([build_context(bundle, created_at="created-at")])
    service = OfficialFactReconciliationService(
        repo,
        engine=ReconciliationEngine(CAPEX_CASH_RECONCILIATION_RULE),
    )
    result = service.reconcile_official_pair(company, exchange)
    assert result.status == ReconciliationStatus.matched
    rows = store.connect().execute(
        """SELECT reconciliation_rule_id, reconciliation_rule_version
             FROM fact_lineage ORDER BY lineage_id"""
    ).fetchall()
    assert rows == [
        (SUPPLEMENTAL_RULE_ID, SUPPLEMENTAL_RULE_VERSION),
        (SUPPLEMENTAL_RULE_ID, SUPPLEMENTAL_RULE_VERSION),
        (SUPPLEMENTAL_RULE_ID, SUPPLEMENTAL_RULE_VERSION),
    ]
    store.close()
