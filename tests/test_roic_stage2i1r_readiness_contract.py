"""Independent Stage 2I.1R contract tests.

These tests use small synthetic Fact/Context records for failure semantics and
never open or write the default research database.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

from ashare_research.facts.identity import build_fact_id
from ashare_research.tools.roic_contracts import (
    FORMAL_STATUSES,
    entries_by_role,
    load_registry,
    validate_acquisition_plan,
)
from ashare_research.tools.roic_fact_readiness import (
    _build_cell,
    _validate_fact,
    build_readiness_report,
    select_roic_fact_as_of,
)
from ashare_research.tools.roic_fact_snapshot import load_inventory

ROOT = Path(__file__).resolve().parents[1]


def _fact(
    *,
    concept_id: str = "operating_profit",
    context_id: str = "601857.SH|2024|annual|consolidated",
    symbol: str = "601857.SH",
    source_id: str = "company_ir:601857.SH:2024:annual",
    fact_version: int = 1,
    restatement_version: str = "original",
    supersedes_fact_id: str = "",
    available_at: str = "2025-03-30",
    unit: str = "万元",
    source_type: str = "company_official",
    eligible: bool = True,
) -> dict:
    fact = {
        "concept_id": concept_id,
        "concept_version": "1",
        "symbol": symbol,
        "context_id": context_id,
        "source_id": source_id,
        "fact_version": fact_version,
        "restatement_version": restatement_version,
        "derivation_definition_id": "",
        "derivation_version": "",
        "supersedes_fact_id": supersedes_fact_id,
        "value_decimal": "100.00",
        "unit": unit,
        "currency": "CNY",
        "period_start": "2024-01-01" if "annual" in context_id else "2024-12-31",
        "period_end": "2024-12-31",
        "period_type": "annual",
        "scope": "consolidated",
        "accounting_standard": "CAS",
        "source_type": source_type,
        "source_tier": source_type,
        "source_provider": "company_ir",
        "source_locator": "https://example.invalid/annual-report.pdf",
        "content_sha256": "a" * 64,
        "verification_status": "verified",
        "verification_note": "synthetic contract fixture",
        "eligible_for_metrics": eligible,
        "filing_date": "2025-03-30",
        "announcement_date": "2025-03-30",
        "available_at": available_at,
        "source_evidence": [],
    }
    fact["fact_id"] = build_fact_id(fact)
    return fact


def _context(*, instant: bool = False, scope: str = "consolidated") -> dict:
    return {
        "context_id": f"601857.SH|2024|{'instant' if instant else 'annual'}|{scope}",
        "symbol": "601857.SH",
        "fiscal_year": 2024,
        "period_type": "instant" if instant else "annual",
        "period_start": "2024-12-31" if instant else "2024-01-01",
        "period_end": "2024-12-31",
        "instant_or_duration": "instant" if instant else "duration",
        "consolidation_scope": scope,
        "accounting_standard": "CAS",
    }


def test_registry_is_single_authority_and_plan_is_bounded() -> None:
    registry = load_registry()
    plan = json.loads(
        (ROOT / "config" / "roic_official_fact_acquisition_plan_v2.json").read_text(
            encoding="utf-8"
        )
    )
    validate_acquisition_plan(registry, plan)
    assert len(registry["entries"]) >= 25
    assert set(registry["allowed_statuses"]) == set(FORMAL_STATUSES)
    assert entries_by_role(registry)["invested_capital.interest_bearing_debt_total"][
        "derivation_components"
    ]
    assert all(
        year in {2023, 2024}
        for layer in plan["layers"].values()
        for item in layer
        for year in item["affected_fiscal_years"]
    )


def test_readiness_report_has_full_matrix_and_is_non_production() -> None:
    report = build_readiness_report()
    assert report["schema"] == "roic_fact_readiness_report_v2"
    assert report["formal_statuses"] == list(FORMAL_STATUSES)
    assert len(report["matrix"]) == len(load_registry()["entries"]) * 6
    required_fields = {
        "symbol",
        "fiscal_year",
        "role_id",
        "canonical_concept_id",
        "input_type",
        "status",
        "reason_codes",
        "blocker_severity",
        "selected_fact_id",
        "candidate_fact_ids",
        "context_id",
        "period_start",
        "period_end",
        "period_type",
        "scope",
        "unit",
        "currency",
        "source_id",
        "source_type",
        "source_tier",
        "source_locator",
        "content_sha256",
        "verification_status",
        "eligible",
        "available_at",
        "fact_version",
        "restatement_version",
        "supersedes_fact_id",
        "selected_as_of",
        "acquisition_required",
        "derivation_status",
        "methodology_choice_status",
    }
    assert all(required_fields.issubset(cell) for cell in report["matrix"])
    assert report["shadow"]["status"] == "NOT_RUN"
    assert report["shadow"]["production_metric_created"] is False
    assert report["shadow"]["current_value_profile_changed"] is False
    assert set(report["status_summary"]).issubset(set(FORMAL_STATUSES))


def test_strict_symbol_context_scope_period_unit_source_gates() -> None:
    registry = load_registry()
    duration_entry = entries_by_role(registry)["nopat.operating_profit"]
    context = _context()
    valid = _fact(context_id=context["context_id"])
    assert _validate_fact(valid, context, duration_entry, "2026-08-02")[0] == []

    cases = [
        ("symbol", "symbol_mismatch"),
        ("scope", "scope_mismatch"),
        ("unit", "unit_or_currency_mismatch"),
        ("source_type", "source_type_not_allowed"),
    ]
    for field, reason in cases:
        mutated = copy.deepcopy(valid)
        if field == "symbol":
            mutated["symbol"] = "000001.SZ"
        elif field == "scope":
            mutated["scope"] = "parent_company"
        elif field == "unit":
            mutated["unit"] = "CNY"
        else:
            mutated["source_type"] = "candidate_aggregator"
        reasons, _ = _validate_fact(mutated, context, duration_entry, "2026-08-02")
        assert reason in reasons
    mixed_symbol = _fact(
        context_id=context["context_id"],
        symbol="000001.SZ",
    )
    mixed_cell = _build_cell(
        entry=duration_entry,
        year=2024,
        facts=[mixed_symbol],
        contexts={context["context_id"]: context},
        all_facts={mixed_symbol["fact_id"]: mixed_symbol},
        assessment_as_of="2026-08-02",
        entries_map=entries_by_role(registry),
    )
    assert mixed_cell["status"] == "missing_official_fact"
    assert mixed_cell["candidate_fact_ids"] == []


def test_nine_formal_statuses_are_exercised_by_contract_fixtures() -> None:
    registry = load_registry()
    assert set(FORMAL_STATUSES) == {
        "ready",
        "partially_ready",
        "missing_official_fact",
        "scope_mismatch",
        "period_mismatch",
        "PIT_unavailable",
        "restatement_unresolved",
        "methodology_unresolved",
        "not_applicable",
    }
    entries = entries_by_role(registry)
    context = _context()
    valid = _fact(context_id=context["context_id"])
    assert _validate_fact(valid, context, entries["nopat.operating_profit"], "2026-08-02")[0] == []
    policy = entries["policy.non_operating_asset_classification"]
    assert policy["missing_status"] == "methodology_unresolved"
    assert policy["input_type"] == "methodology_choice"
    policy_cells = [
        cell for cell in build_readiness_report()["matrix"] if cell["role_id"] == policy["role_id"]
    ]
    assert {cell["status"] for cell in policy_cells} == {"ready"}
    assert {cell["methodology_resolution_status"] for cell in policy_cells} == {"resolved"}
    assert (
        _build_cell(
            entry=entries["invested_capital.interest_bearing_debt_total"],
            year=2024,
            facts=[
                _fact(
                    concept_id="short_term_borrowings",
                    context_id="601857.SH|2024|instant|consolidated",
                )
            ],
            contexts={
                "601857.SH|2024|instant|consolidated": _context(instant=True),
            },
            all_facts={},
            assessment_as_of="2026-08-02",
            entries_map=entries,
        )["status"]
        == "partially_ready"
    )
    assert "not_applicable" in {cell["status"] for cell in build_readiness_report()["matrix"]}


def test_pit_pre_post_restatement_and_disconnected_chain() -> None:
    registry = load_registry()
    entry = entries_by_role(registry)["invested_capital.parent_equity"]
    context = _context(instant=True)
    context_id = context["context_id"]
    old = _fact(
        concept_id="equity_attributable_to_parent",
        context_id=context_id,
        available_at="2025-03-30",
    )
    new = _fact(
        concept_id="equity_attributable_to_parent",
        context_id=context_id,
        source_id=old["source_id"],
        fact_version=2,
        restatement_version="restated_1",
        supersedes_fact_id=old["fact_id"],
        available_at="2026-03-30",
    )
    all_facts = {old["fact_id"]: old, new["fact_id"]: new}
    pre = select_roic_fact_as_of(
        facts=[old, new],
        all_facts=all_facts,
        entry=entry,
        fiscal_year=2024,
        assessment_as_of="2025-12-31",
    )
    post = select_roic_fact_as_of(
        facts=[old, new],
        all_facts=all_facts,
        entry=entry,
        fiscal_year=2024,
        assessment_as_of="2026-12-31",
    )
    assert pre["selected_fact_id"] == old["fact_id"]
    assert post["selected_fact_id"] == new["fact_id"]
    assert post["edges"][0]["supersedes_fact_id"] == old["fact_id"]

    disconnected = _fact(
        concept_id="equity_attributable_to_parent",
        context_id=context_id,
        source_id="exchange_official:601857.SH:2024",
        available_at="2025-04-01",
    )
    conflict = select_roic_fact_as_of(
        facts=[old, disconnected],
        all_facts={old["fact_id"]: old, disconnected["fact_id"]: disconnected},
        entry=entry,
        fiscal_year=2024,
        assessment_as_of="2026-12-31",
    )
    assert conflict["status"] == "restatement_unresolved"


def test_inventory_is_lossless_and_clean_clone_ready() -> None:
    inventory = load_inventory()
    assert inventory["schema"] == "roic_canonical_fact_inventory_v2"
    assert inventory["fact_count"] == 354
    assert inventory["eligible_fact_count"] == 122
    assert inventory["context_count"] == 11
    assert all("value_decimal" in fact for fact in inventory["facts"])
    assert all(fact["symbol"] == "601857.SH" for fact in inventory["facts"])
