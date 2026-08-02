"""Independent Stage 2I.1R2 dependency and acquisition-gate tests."""

from __future__ import annotations

import copy
import json
import os
from pathlib import Path

import pytest

from ashare_research.tools.roic_contracts import (
    canonical_digest,
    decisions_by_id,
    entries_by_role,
    find_absolute_path_leaks,
    load_dependency_graph,
    load_methodology_decisions,
    load_registry,
    validate_acquisition_plan,
    validate_dependency_graph,
    validate_registry,
)
from ashare_research.tools.roic_fact_readiness import _build_cell, build_readiness_report

ROOT = Path(__file__).resolve().parents[1]
PLAN_PATH = ROOT / "config" / "roic_official_fact_acquisition_plan_v3.json"


def _contracts() -> tuple[dict, dict, dict, dict]:
    registry = load_registry()
    graph = load_dependency_graph()
    readiness = build_readiness_report()
    plan = json.loads(PLAN_PATH.read_text(encoding="utf-8"))
    return registry, graph, readiness, plan


def _validate(plan: dict, *, registry: dict | None = None, graph: dict | None = None) -> dict:
    actual_registry, actual_graph, readiness, _ = _contracts()
    return validate_acquisition_plan(
        registry or actual_registry,
        plan,
        graph or actual_graph,
        readiness,
        target_year=2024,
        opening_year=2023,
    )


def _item(plan: dict, acquisition_id: str) -> dict:
    return next(
        item
        for items in plan["layers"].values()
        for item in items
        if item["acquisition_id"] == acquisition_id
    )


def _methodology_cell(decision: dict) -> dict:
    registry = load_registry()
    entry = entries_by_role(registry)["policy.non_operating_asset_classification"]
    return _build_cell(
        entry=entry,
        year=2024,
        facts=[],
        contexts={},
        all_facts={},
        assessment_as_of="2026-08-02",
        entries_map=entries_by_role(registry),
        decisions_map={decision["decision_id"]: decision},
    )


def test_finance_lease_included_composite_has_one_formula_contribution() -> None:
    graph = load_dependency_graph()
    nodes = {node["role_id"]: node for node in graph["nodes"]}
    composition = graph["finance_lease_composition"]
    assert composition["mode"] == "lease_included_in_composite"
    assert composition["final_formula_contribution_roles"] == ["nopat.finance_cost_adjustment"]
    assert nodes["nopat.lease_interest_expense"]["included_in_parent"] is True
    assert nodes["nopat.lease_interest_expense"]["parent_role_id"] == (
        "nopat.finance_cost_adjustment"
    )


def test_finance_lease_excluded_design_requires_independent_contribution() -> None:
    graph = copy.deepcopy(load_dependency_graph())
    nodes = {node["role_id"]: node for node in graph["nodes"]}
    graph["finance_lease_composition"]["mode"] = "lease_excluded_and_independent"
    graph["finance_lease_composition"]["final_formula_contribution_roles"] = [
        "nopat.finance_cost_adjustment",
        "nopat.lease_interest_expense",
    ]
    nodes["nopat.finance_cost_adjustment"]["dependency_type"] = "independent_input"
    nodes["nopat.lease_interest_expense"]["parent_role_id"] = None
    nodes["nopat.lease_interest_expense"]["included_in_parent"] = False
    validate_dependency_graph(graph)
    nodes["nopat.lease_interest_expense"]["required_for_primary_formula"] = False
    with pytest.raises(ValueError, match="must remain primary"):
        validate_dependency_graph(graph)


def test_missing_lease_component_keeps_composite_unready() -> None:
    registry = load_registry()
    entries = entries_by_role(registry)
    cell = _build_cell(
        entry=entries["nopat.finance_cost_adjustment"],
        year=2024,
        facts=[],
        contexts={},
        all_facts={},
        assessment_as_of="2026-08-02",
        entries_map=entries,
    )
    assert cell["status"] == "missing_official_fact"
    assert cell["derivation_status"] == "incomplete"
    assert {row["role_id"] for row in cell["component_statuses"]} == {
        "nopat.finance_cost_excluding_lease_interest",
        "nopat.lease_interest_expense",
    }


def test_formula_duplicate_and_sign_drift_are_rejected() -> None:
    graph = copy.deepcopy(load_dependency_graph())
    nodes = {node["role_id"]: node for node in graph["nodes"]}
    nodes["nopat.lease_interest_expense"]["parent_role_id"] = None
    with pytest.raises(ValueError, match="parent inclusion mismatch"):
        validate_dependency_graph(graph)
    graph = copy.deepcopy(load_dependency_graph())
    nodes = {node["role_id"]: node for node in graph["nodes"]}
    nodes["nopat.lease_interest_expense"]["contribution_sign"] = -1
    with pytest.raises(ValueError, match="composition sign mismatch"):
        validate_dependency_graph(graph)


def test_minimum_plan_passes_with_empty_error_lists() -> None:
    registry, graph, readiness, plan = _contracts()
    result = validate_acquisition_plan(registry, plan, graph, readiness)
    assert result["validation_status"] == "PASS"
    assert result["next_stage_acquisition"] == "ALLOWED"
    assert result["uncovered_blockers"] == []
    assert result["orphan_items"] == []
    assert result["mislayered_items"] == []
    assert result["duplicated_contributions"] == []
    assert result["plan_digest"] == plan["plan_digest"]


def test_registry_primary_blocker_missing_plan_item_fails() -> None:
    *_, plan = _contracts()
    plan["layers"]["A_primary_formula_direct_fact_blockers"] = [
        item
        for item in plan["layers"]["A_primary_formula_direct_fact_blockers"]
        if item["role_id"] != "tax.operating_tax_expense"
    ]
    assert _validate(plan)["uncovered_blockers"]


def test_primary_in_secondary_and_secondary_marked_primary_fail() -> None:
    registry, graph, _, plan = _contracts()
    item = _item(plan, "A-2024-operating-tax")
    plan["layers"]["A_primary_formula_direct_fact_blockers"].remove(item)
    plan["layers"]["D_secondary_reconciliation_or_sensitivity"].append(item)
    assert _validate(plan)["mislayered_items"]
    registry = copy.deepcopy(registry)
    entry = entries_by_role(registry)["nopat.other_non_operating_income_expense"]
    entry["required_primary_formula"] = True
    entry["required_secondary"] = True
    with pytest.raises(ValueError, match="both primary and secondary"):
        validate_registry(registry)


@pytest.mark.parametrize(
    ("role_id", "expected_reason"),
    [
        ("nopat.finance_cost_adjustment", "deterministic_derivation_cannot_be_acquired"),
        ("policy.non_operating_asset_classification", "methodology_choice_cannot_be_acquired"),
    ],
)
def test_derivation_or_methodology_cannot_be_directly_acquired(
    role_id: str, expected_reason: str
) -> None:
    registry, _, _, plan = _contracts()
    entry = entries_by_role(registry)[role_id]
    forged = copy.deepcopy(_item(plan, "A-2024-operating-tax"))
    forged.update(
        {
            "acquisition_id": f"forged-{role_id}",
            "role_id": role_id,
            "canonical_concept_id": entry["canonical_concept_id"],
            "dependency_graph_node": role_id,
        }
    )
    plan["layers"]["A_primary_formula_direct_fact_blockers"].append(forged)
    result = _validate(plan)
    assert any(row.get("reason") == expected_reason for row in result["orphan_items"])


def test_orphan_year_boundary_and_digest_drift_fail() -> None:
    *_, plan = _contracts()
    orphan = copy.deepcopy(_item(plan, "A-2024-operating-tax"))
    orphan.update(
        {
            "acquisition_id": "unknown-role",
            "role_id": "unknown.role",
            "canonical_concept_id": "unknown",
            "dependency_graph_node": "unknown.role",
        }
    )
    plan["layers"]["A_primary_formula_direct_fact_blockers"].append(orphan)
    assert _validate(plan)["orphan_items"]
    *_, plan = _contracts()
    _item(plan, "B-2023-2024-nci")["affected_fiscal_years"] = [2024]
    assert _validate(plan)["mislayered_items"]
    *_, plan = _contracts()
    plan["registry_sha256"] = "0" * 64
    result = _validate(plan)
    assert any(row.get("reason") == "registry_digest_mismatch" for row in result["orphan_items"])


def test_duplicate_component_acquisition_is_rejected() -> None:
    registry, _, _, plan = _contracts()
    entry = entries_by_role(registry)["nopat.finance_cost_adjustment"]
    parent = copy.deepcopy(_item(plan, "A-2024-finance-core"))
    parent.update(
        {
            "acquisition_id": "forged-finance-parent",
            "role_id": entry["role_id"],
            "canonical_concept_id": entry["canonical_concept_id"],
            "dependency_graph_node": entry["role_id"],
        }
    )
    plan["layers"]["A_primary_formula_direct_fact_blockers"].append(parent)
    result = _validate(plan)
    assert result["duplicated_contributions"]


@pytest.mark.parametrize("status", ["unresolved", "awaiting_supporting_facts"])
def test_unresolved_or_awaiting_methodology_is_never_not_applicable(status: str) -> None:
    decision = copy.deepcopy(load_methodology_decisions()["decisions"][0])
    decision["resolution_status"] = status
    cell = _methodology_cell(decision)
    assert cell["status"] == "methodology_unresolved"
    assert cell["methodology_choice_status"] == "methodology_unresolved"
    assert cell["supporting_fact_roles"]


def test_resolved_methodology_requires_rule_version_and_has_identity() -> None:
    decision = copy.deepcopy(load_methodology_decisions()["decisions"][0])
    cell = _methodology_cell(decision)
    assert cell["status"] == "ready"
    assert cell["methodology_decision_version"] == "1"
    assert len(cell["decision_rule_digest"]) == 64
    decision["decision_rule"] = ""
    assert _methodology_cell(decision)["status"] == "methodology_unresolved"


def test_method_rule_change_changes_cell_and_report_identity(tmp_path: Path) -> None:
    contract = load_methodology_decisions()
    first = _methodology_cell(contract["decisions"][0])
    changed = copy.deepcopy(contract)
    changed["decisions"][0]["decision_rule"] += " Changed only for identity test."
    second = _methodology_cell(changed["decisions"][0])
    assert first["decision_rule_digest"] != second["decision_rule_digest"]
    path = tmp_path / "decisions.json"
    path.write_text(json.dumps(changed), encoding="utf-8")
    assert (
        build_readiness_report(methodology_decisions_path=path)["report_sha256"]
        != (build_readiness_report()["report_sha256"])
    )


def test_not_applicable_is_only_the_deprecated_mixed_role() -> None:
    report = build_readiness_report()
    roles = {cell["role_id"] for cell in report["matrix"] if cell["status"] == "not_applicable"}
    assert roles == {"invested_capital.non_operating_asset_boundary"}


def test_minimum_batch_classifications_are_consistent() -> None:
    registry, graph, _, plan = _contracts()
    roles = entries_by_role(registry)
    nodes = {node["role_id"]: node for node in graph["nodes"]}
    assert roles["nopat.asset_disposal_gain_loss"]["formula_membership"] == "primary"
    assert roles["nopat.other_non_operating_income_expense"]["formula_membership"] == ("secondary")
    assert nodes["nopat.asset_disposal_gain_loss"]["contribution_sign"] == -1
    assert nodes["nopat.other_non_operating_income_expense"]["contribution_sign"] == 0
    acquired_roles = {item["role_id"] for items in plan["layers"].values() for item in items}
    assert "policy.non_operating_asset_classification" not in acquired_roles
    assert "invested_capital.qualifying_non_operating_assets" not in acquired_roles
    assert "nopat.lease_interest_expense" in acquired_roles


def test_secondary_roles_do_not_block_primary_gate() -> None:
    registry, graph, readiness, plan = _contracts()
    assert any(
        cell["role_id"] == "invested_capital.goodwill" and cell["status"] == "missing_official_fact"
        for cell in readiness["matrix"]
    )
    assert (
        validate_acquisition_plan(registry, plan, graph, readiness)["validation_status"] == "PASS"
    )


def test_reports_are_path_clean_and_cwd_independent(tmp_path: Path) -> None:
    first = build_readiness_report()
    original = Path.cwd()
    try:
        os.chdir(tmp_path)
        second = build_readiness_report()
    finally:
        os.chdir(original)
    assert first["report_sha256"] == second["report_sha256"]
    text = json.dumps(first, ensure_ascii=False)
    assert find_absolute_path_leaks(text, current_working_directory=str(ROOT)) == []


def test_shadow_and_production_safeguards_remain_closed() -> None:
    report = build_readiness_report()
    plan = json.loads(PLAN_PATH.read_text(encoding="utf-8"))
    assert report["shadow"]["status"] == "NOT_RUN"
    assert report["shadow"]["production_metric_created"] is False
    assert report["shadow"]["current_value_profile_changed"] is False
    assert plan["production_effects"] == {
        "register_roic_metric": False,
        "insert_metric_result": False,
        "change_value_profile": False,
        "run_shadow": False,
        "run_scoring": False,
        "start_market_mechanism": False,
    }
    assert canonical_digest(decisions_by_id(load_methodology_decisions()))
