"""Frozen Rule 005 consolidated net profit reconciliation contract.

Rule 005 (``RECON_OFFICIAL_NUMERIC_005`` v1) reconciles exactly one
concept -- ``net_profit`` (consolidated net profit, duration, the ROA
numerator) -- across the company_official and exchange_official paths.
It reuses the engine's gates 1-8 unchanged: exact Decimal equality in
canonical 万元, no tolerance, no averaging, no source preference.  The
value must be the directly disclosed audited consolidated income
statement "净利润" line; ``net_profit_attributable_to_parent`` +
minority interest is a cross-check only and is NOT supported by this
rule as a derivation.
"""

from __future__ import annotations

import copy
from pathlib import Path

import pytest

from ashare_research.facts.identity import build_fact_id
from ashare_research.reconciliation.engine import (
    CAPEX_CASH_RECONCILIATION_RULE,
    DEFAULT_NUMERIC_RECONCILIATION_RULE,
    EARNINGS_QUALITY_RECONCILIATION_RULE,
    EARNINGS_QUALITY_RULE_ID,
    EARNINGS_QUALITY_RULE_VERSION,
    NET_PROFIT_RECONCILIATION_RULE,
    NET_PROFIT_RULE_ID,
    NET_PROFIT_RULE_VERSION,
    ROE_ROA_DENOMINATOR_RECONCILIATION_RULE,
    ROE_ROA_DENOMINATOR_RULE_ID,
    ROE_ROA_DENOMINATOR_RULE_VERSION,
    RULE_ID,
    RULE_VERSION,
    SUPPLEMENTAL_RULE_ID,
    SUPPLEMENTAL_RULE_VERSION,
    ReconciliationEngine,
    build_reconciliation_source_id,
)
from ashare_research.reconciliation.models import ReconciliationStatus
from ashare_research.tools.official_fact_acceptance import (
    build_source_facts,
    load_bundle,
)
from ashare_research.validation.validator import FactValidator

BUNDLE = Path("acceptance/fixtures/official_facts/601857.SH/2024_annual.json")
SUPPORTED = frozenset({"net_profit"})
DURATION_CONTEXT_ID = "601857.SH|2024|annual|consolidated"
DURATION_START = "2024-01-01"
DURATION_END = "2024-12-31"
# Real 2024 consolidated "净利润" line (RMB million 183,747 -> 万元 x100).
NET_PROFIT_2024 = 18374700


def _base_facts() -> tuple[dict, dict, dict]:
    bundle = load_bundle(BUNDLE)
    facts = build_source_facts(bundle, created_at="frozen-created-at")
    company = {fact["concept_id"]: fact for fact in facts["company"]}
    exchange = {fact["concept_id"]: fact for fact in facts["exchange"]}
    return bundle, company, exchange


def _duration_pair(
    concept_id: str = "net_profit",
    *,
    company_value: int | None = None,
    exchange_value: int | None = None,
    company_unit: str = "万元",
    exchange_unit: str = "万元",
) -> tuple[dict, dict]:
    """Build a company/exchange duration-fact pair for one concept."""
    bundle, company, _ = _base_facts()
    if company_value is None:
        company_value = NET_PROFIT_2024
    if exchange_value is None:
        exchange_value = NET_PROFIT_2024
    document = bundle["documents"]["company"]
    exchange_document = bundle["documents"]["exchange"]
    result = []
    for value, unit, doc in (
        (company_value, company_unit, document),
        (exchange_value, exchange_unit, exchange_document),
    ):
        fact = copy.deepcopy(company["revenue"])
        fact.update(
            {
                "concept_id": concept_id,
                "value": value,
                "unit": unit,
                "context_id": DURATION_CONTEXT_ID,
                "period_start": DURATION_START,
                "period_end": DURATION_END,
                "source_provider": doc["source_provider"],
                "source_id": doc["source_id"],
                "source_tier": doc["source_tier"],
                "source_document": doc["source_document"],
                "source_url": doc["final_pdf_url"],
                "source_hash": doc["sha256"],
                "source_page": "PDF page 115 / printed page 113",
                "source_table": "2024年度合并及公司利润表",
                "source_label": "净利润",
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


def test_rule_005_identity_and_supported_concepts_are_frozen():
    rule = NET_PROFIT_RECONCILIATION_RULE
    assert rule.rule_id == NET_PROFIT_RULE_ID
    assert rule.version == NET_PROFIT_RULE_VERSION
    assert rule.supported_concepts == SUPPORTED
    assert (NET_PROFIT_RULE_ID, NET_PROFIT_RULE_VERSION) == (
        "RECON_OFFICIAL_NUMERIC_005",
        "1",
    )


def test_rules_001_to_004_identities_are_unchanged():
    """Adding Rule 005 must not touch any frozen rule's identity/scope."""
    assert (RULE_ID, RULE_VERSION) == ("RECON_OFFICIAL_NUMERIC_001", "1")
    assert DEFAULT_NUMERIC_RECONCILIATION_RULE.supported_concepts == frozenset(
        {"revenue", "net_profit_attributable_to_parent", "operating_cash_flow"}
    )
    assert (SUPPLEMENTAL_RULE_ID, SUPPLEMENTAL_RULE_VERSION) == (
        "RECON_OFFICIAL_NUMERIC_002",
        "1",
    )
    assert CAPEX_CASH_RECONCILIATION_RULE.supported_concepts == frozenset(
        {"cash_paid_for_fixed_assets"}
    )
    assert (EARNINGS_QUALITY_RULE_ID, EARNINGS_QUALITY_RULE_VERSION) == (
        "RECON_OFFICIAL_NUMERIC_003",
        "1",
    )
    assert EARNINGS_QUALITY_RECONCILIATION_RULE.supported_concepts == frozenset(
        {"net_profit_excluding_non_recurring", "operating_cost", "operating_profit"}
    )
    assert (ROE_ROA_DENOMINATOR_RULE_ID, ROE_ROA_DENOMINATOR_RULE_VERSION) == (
        "RECON_OFFICIAL_NUMERIC_004",
        "1",
    )
    assert ROE_ROA_DENOMINATOR_RECONCILIATION_RULE.supported_concepts == frozenset(
        {"total_assets", "equity_attributable_to_parent"}
    )


def test_rule_005_exact_match_uses_canonical_identity():
    company, exchange = _duration_pair()
    result = ReconciliationEngine(
        NET_PROFIT_RECONCILIATION_RULE
    ).reconcile_pair(company, exchange, now="created-at")

    assert result.status == ReconciliationStatus.matched
    assert result.rule_id == NET_PROFIT_RULE_ID
    assert result.rule_version == NET_PROFIT_RULE_VERSION
    assert result.comparable is True
    assert result.output_fact is not None
    output = result.output_fact
    assert output["fact_id"] == build_fact_id(output)
    assert output["source_id"] == build_reconciliation_source_id(
        "601857.SH", NET_PROFIT_RULE_ID, NET_PROFIT_RULE_VERSION,
    )
    assert output["source_tier"] == "reconciled_derived"
    assert output["eligible_for_metrics"] is True
    assert output["verification_status"] == "reconciled"
    assert output["value"] == NET_PROFIT_2024
    assert output["unit"] == "万元"
    assert output["context_id"] == DURATION_CONTEXT_ID
    assert output["period_end"] == DURATION_END
    assert output["restatement_version"] == "original"
    assert output["fact_version"] == 1
    assert sorted(output["input_fact_ids"].split(",")) == sorted(
        [company["fact_id"], exchange["fact_id"]]
    )


def test_rule_005_reconciled_duration_fact_passes_validator():
    company, exchange = _duration_pair()
    output = ReconciliationEngine(
        NET_PROFIT_RECONCILIATION_RULE
    ).reconcile_pair(company, exchange, now="created-at").output_fact
    assert output is not None
    errors = [
        result
        for result in FactValidator().validate_single_fact(output)
        if result.severity == "error" and not result.passed
    ]
    assert not errors, errors


def test_rule_005_mismatch_produces_no_fact():
    company, exchange = _duration_pair(exchange_value=NET_PROFIT_2024 + 100)
    result = ReconciliationEngine(
        NET_PROFIT_RECONCILIATION_RULE
    ).reconcile_pair(company, exchange)
    assert result.status == ReconciliationStatus.mismatch
    assert result.comparable is True
    assert result.output_fact is None
    assert result.absolute_difference == "100"


@pytest.mark.parametrize(
    "concept_id",
    [
        "net_profit_attributable_to_parent",
        "net_profit_excluding_non_recurring",
        "operating_profit",
        "profit_before_tax",
        "revenue",
        "total_assets",
    ],
)
def test_rule_005_rejects_every_other_concept(concept_id: str):
    """Rule 005 supports ONLY net_profit; in particular it must not accept
    the attributable-to-parent or ex-non-recurring profit lines."""
    company, exchange = _duration_pair(concept_id)
    result = ReconciliationEngine(
        NET_PROFIT_RECONCILIATION_RULE
    ).reconcile_pair(company, exchange)
    assert result.status == ReconciliationStatus.insufficient_evidence
    assert result.output_fact is None
    assert "not supported" in result.decision_reason


def test_rule_005_rejects_same_tier_pair():
    company, _ = _duration_pair()
    twin = copy.deepcopy(company)
    twin["fact_id"] = build_fact_id(twin)
    result = ReconciliationEngine(
        NET_PROFIT_RECONCILIATION_RULE
    ).reconcile_pair(company, twin)
    assert result.status == ReconciliationStatus.not_comparable
    assert result.output_fact is None


def test_rule_005_rejects_unverified_input():
    company, exchange = _duration_pair()
    company["verification_status"] = "unverified"
    company["fact_id"] = build_fact_id(company)
    result = ReconciliationEngine(
        NET_PROFIT_RECONCILIATION_RULE
    ).reconcile_pair(company, exchange)
    assert result.status == ReconciliationStatus.insufficient_evidence
    assert result.output_fact is None


def test_rule_005_rejects_eligible_raw_input():
    """Raw reconciliation inputs must be verified AND ineligible."""
    company, exchange = _duration_pair()
    company["eligible_for_metrics"] = True
    result = ReconciliationEngine(
        NET_PROFIT_RECONCILIATION_RULE
    ).reconcile_pair(company, exchange)
    assert result.status == ReconciliationStatus.insufficient_evidence
    assert result.output_fact is None


def test_rule_005_cross_unit_conversion_is_exact():
    """万元 vs 元 pair still matches exactly (gate 6), no float drift."""
    company, exchange = _duration_pair(
        company_value=NET_PROFIT_2024,
        exchange_value=NET_PROFIT_2024 * 10000,
        exchange_unit="元",
    )
    result = ReconciliationEngine(
        NET_PROFIT_RECONCILIATION_RULE
    ).reconcile_pair(company, exchange)
    assert result.status == ReconciliationStatus.matched
    assert result.company_normalized_value == str(NET_PROFIT_2024)
    assert result.output_fact is not None
    assert result.output_fact["value"] == NET_PROFIT_2024
    assert result.output_fact["unit"] == "万元"


def test_rule_005_rejects_unsafe_integer():
    unsafe = 2**53
    company, exchange = _duration_pair(
        company_value=unsafe, exchange_value=unsafe,
    )
    result = ReconciliationEngine(
        NET_PROFIT_RECONCILIATION_RULE
    ).reconcile_pair(company, exchange)
    assert result.status == ReconciliationStatus.insufficient_evidence
    assert result.output_fact is None
    assert "safe-integer" in result.decision_reason


def test_rule_005_source_id_is_distinct_from_other_rules():
    """The reconciled identity is rule-specific; extending coverage cannot
    collide with or shadow a frozen rule's reconciled facts."""
    ids = {
        build_reconciliation_source_id("601857.SH", rule.rule_id, rule.version)
        for rule in (
            DEFAULT_NUMERIC_RECONCILIATION_RULE,
            CAPEX_CASH_RECONCILIATION_RULE,
            EARNINGS_QUALITY_RECONCILIATION_RULE,
            ROE_ROA_DENOMINATOR_RECONCILIATION_RULE,
            NET_PROFIT_RECONCILIATION_RULE,
        )
    }
    assert len(ids) == 5
    assert build_reconciliation_source_id(
        "601857.SH", NET_PROFIT_RULE_ID, NET_PROFIT_RULE_VERSION,
    ) == "reconciled:601857.SH:company_exchange:RECON_OFFICIAL_NUMERIC_005:v1"
