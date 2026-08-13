"""Stage 2I ROIC methodology and readiness gates."""

from __future__ import annotations

import json
import re
from pathlib import Path

from ashare_research.tools.roic_fact_readiness import build_readiness_report

ROOT = Path(__file__).resolve().parents[1]


def test_roic_readiness_is_blocked_without_silent_fallbacks() -> None:
    report = build_readiness_report()
    second_report = build_readiness_report()

    assert report["report_sha256"] == second_report["report_sha256"]
    assert report["formula_candidate"] == "B_operating_profit_bridge_financing_view"
    assert report["evidence_gate"] == "BLOCKED_WITH_EXPLICIT_GAPS"
    assert report["shadow"]["status"] == "NOT_RUN"
    assert report["shadow"]["production_metric_created"] is False
    assert report["shadow"]["current_value_profile_changed"] is False
    assert "direct operating-tax" in report["shadow"]["reason"]
    assert any(
        gap["canonical_concept_id"] == "operating_tax_expense" for gap in report["blocking_gaps"]
    )
    assert any(
        gap["canonical_concept_id"] == "non_controlling_interest" for gap in report["blocking_gaps"]
    )
    assert any(gap["canonical_concept_id"] == "goodwill" for gap in report["blocking_gaps"])


def test_canonical_inventory_has_exact_fact_ids_and_pit_versions() -> None:
    report = build_readiness_report()
    cells = report["matrix"]
    ready_cells = [cell for cell in cells if cell["status"] == "ready"]

    assert len(ready_cells) >= 50
    assert all(
        re.fullmatch(r"[0-9a-f]{64}", fact_id)
        for cell in ready_cells
        for fact_id in cell["candidate_fact_ids"]
    )
    restated = [
        cell
        for cell in cells
        if cell["canonical_concept_id"] in {"equity_attributable_to_parent", "total_assets"}
        and cell["fiscal_year"] in {2022, 2023}
        and len(cell["candidate_fact_ids"]) > 1
    ]
    assert restated
    assert all(
        cell["pit_audit"]["visible_fact_ids"] == sorted(cell["pit_audit"]["visible_fact_ids"])
        for cell in restated
    )


def test_roic_contract_and_acquisition_plan_are_non_production() -> None:
    methodology = json.loads(
        (ROOT / "config" / "value_evaluation_methodology_roic_v1.json").read_text(encoding="utf-8")
    )
    plan = json.loads(
        (ROOT / "config" / "roic_official_fact_acquisition_plan_v2.json").read_text(
            encoding="utf-8"
        )
    )

    assert methodology["status"] == "frozen_stage2i1r2_acquisition_gate_only"
    assert methodology["concept_registry"] == "config/roic_concept_registry_v2.json"
    assert methodology["formula_dependency_graph"] == (
        "config/roic_formula_dependency_graph_v1.json"
    )
    assert methodology["production_metric_allowed"] is False
    assert methodology["score_eligible"] is False
    assert methodology["forbidden_nopat_inputs"] == [
        "net_profit",
        "net_profit_attributable_to_parent",
        "EBITDA",
        "llm_generated_adjustment",
        "manual_balancing_plug",
    ]
    assert plan["minimum_feasibility_year"] == 2024
    assert plan["opening_balance_year"] == 2023
    assert plan["production_effects"]["register_roic_metric"] is False
    assert plan["production_effects"]["run_scoring"] is False
