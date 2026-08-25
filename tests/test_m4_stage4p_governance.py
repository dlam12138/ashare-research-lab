"""Governance locks for M4 Stage 4P; these tests perform no research execution."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CANONICAL_NORTH_STAR = ROOT / "A股个股研究与市场机制验证平台-项目北极星.md"
TEMPORARY_V2 = ROOT / "A股个股研究与市场机制验证平台-项目北极星-v2.md"
EXPECTED_V1_SHA256 = "ad297e609b49bc6f76421ae6b50d213a003f6cec11c964d7da27f20127bd570f"
EXPECTED_V2_SHA256 = "f411235a94396443c6ffabdc6501c096d5d4163d6fb54b41678109fb3fc6a307"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _aggregate(paths: list[Path]) -> str:
    rows = []
    for path in sorted(paths):
        relative = path.relative_to(ROOT).as_posix()
        rows.append(f"{relative}\t{_sha256(path)}")
    return hashlib.sha256(("\n".join(rows) + "\n").encode()).hexdigest()


def _report(name: str) -> dict:
    return json.loads((ROOT / "reports" / name).read_text(encoding="utf-8"))


def test_canonical_north_star_is_exact_v2_and_singleton() -> None:
    assert _sha256(CANONICAL_NORTH_STAR) == EXPECTED_V2_SHA256
    assert not TEMPORARY_V2.exists()
    assert EXPECTED_V1_SHA256 != EXPECTED_V2_SHA256


def test_north_star_v2_governance_markers_are_present() -> None:
    text = CANONICAL_NORTH_STAR.read_text(encoding="utf-8")
    for marker in (
        "Theory / Hypothesis Registry",
        "M4-A",
        "M4-B",
        "文献、教材和经典 anomaly 只提供",
        "literature evidence 不自动变成 project evidence",
        "统计显著 ≠ 可交易；历史可交易 ≠ 未来盈利",
        "多智能体自动交易平台",
        "100-anomaly 批量筛选",
    ):
        assert marker in text


def test_readme_m4_is_preflight_only() -> None:
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "Generic Mechanism Research Engine + Theory / Hypothesis Registry" in text
    assert "PREFLIGHT ONLY; IMPLEMENTATION NOT STARTED" in text
    assert "M3_DAILY_MECHANISM_NOT_ESTABLISHED" in text
    assert "holdout primary inconclusive" in text
    assert "M4 are not authorized" in text


def test_v1_v2_audit_passes_without_scope_expansion() -> None:
    audit = _report("m4_stage4p_north_star_v2_adoption_audit_v1.json")
    assert audit["audit_status"] == "PASS"
    assert audit["north_star_sources"]["v1_sha256"] == EXPECTED_V1_SHA256
    assert audit["north_star_sources"]["new_input_sha256"] == EXPECTED_V2_SHA256
    assert audit["scope_conflict_checks"]["research_scope_expanded"] is False
    assert audit["scope_conflict_checks"]["automatic_trading_scope_expanded"] is False
    assert audit["scope_conflict_checks"]["automatic_recommendation_scope_expanded"] is False
    assert audit["scope_conflict_checks"]["large_anomaly_mining_authorized"] is False
    assert audit["scope_conflict_checks"]["automatic_pnl_optimization_authorized"] is False


def test_preserved_and_new_governance_boundaries_are_locked() -> None:
    audit = _report("m4_stage4p_north_star_v2_adoption_audit_v1.json")
    assert all(audit["preserved_core_boundaries"].values())
    assert all(audit["new_governance"].values())


def test_m3_protected_aggregates_are_byte_identical() -> None:
    identity = _report("m4_stage4p_frozen_m1_m3_identity_v1.json")
    stage_artifacts = [
        path
        for parent in (ROOT / "reports", ROOT / "acceptance")
        for path in parent.iterdir()
        if path.is_file() and path.name.startswith(("m1_", "m2_", "m3_"))
    ]
    m3_artifacts = [path for path in stage_artifacts if path.name.startswith("m3_")]
    allowed_new_m4a1 = {"hypothesis_config.py", "contract_compiler.py"}
    mechanism = [
        path
        for path in (ROOT / "src" / "ashare_research" / "mechanism").iterdir()
        if path.is_file() and path.suffix == ".py" and path.name not in allowed_new_m4a1
    ]
    stage_scope = identity["protected_scopes"]["m1_m2_m3_reports_and_acceptance"]
    m3_scope = identity["protected_scopes"]["m3_reports_and_acceptance"]
    mechanism_scope = identity["protected_scopes"]["m3_mechanism_package"]
    assert len(stage_artifacts) == stage_scope["file_count"]
    assert _aggregate(stage_artifacts) == stage_scope["aggregate_sha256"]
    assert len(m3_artifacts) == m3_scope["file_count"]
    assert _aggregate(m3_artifacts) == m3_scope["aggregate_sha256"]
    assert len(mechanism) == mechanism_scope["file_count"]
    assert _aggregate(mechanism) == mechanism_scope["aggregate_sha256"]


def test_m3_reuse_inventory_covers_required_components() -> None:
    inventory = _report("m4_stage4p_m3_component_reuse_inventory_v1.json")
    paths = {entry["path"] for entry in inventory["components"]}
    for name in (
        "analysis_contracts.py",
        "analysis_dataset.py",
        "bootstrap.py",
        "contracts.py",
        "evidence.py",
        "model_digest.py",
        "regression.py",
        "robustness.py",
        "source_manifest.py",
    ):
        assert f"src/ashare_research/mechanism/{name}" in paths
    assert inventory["principle"] == "THIN_GENERIC_LAYER_OVER_PROVEN_M3_CORE"
    assert (
        "CNI 399439-specific industry selection"
        in inventory["petrochina_case_evidence_keep_outside_core"]
    )
    assert inventory["summary"]["bounded_extraction_required"] is True


def test_m4a_contract_is_bounded_and_not_implemented() -> None:
    contract = _report("m4_stage4p_m4a_generic_engine_contract_v1.json")
    assert contract["status"] == "FROZEN_PREFLIGHT_ONLY"
    assert contract["implementation_status"] == "NOT_STARTED"
    assert contract["not_implementation"] is True
    assert contract["architecture"]["config_and_frozen_research_contract_are_separate"] is True
    assert (
        contract["supported_first_slice"]["paradigm"]
        == "daily_conditional_controlled_mechanism_research"
    )
    forbidden = contract["minimum_hypothesis_config"]["forbidden_config_features"]
    assert "automatic provider searching" in forbidden
    assert "automatic portfolio construction" in forbidden
    assert "automatic recommendation" in forbidden
    assert len(contract["fail_closed_rules"]) == 7


def test_m4b_registry_is_provenance_only_and_three_unresearched_classes() -> None:
    registry = _report("m4_stage4p_m4b_hypothesis_registry_contract_v1.json")
    assert registry["status"] == "FROZEN_PREFLIGHT_ONLY"
    assert registry["implementation_status"] == "NOT_STARTED"
    assert registry["real_registry_dataset_authorized"] is False
    assert (
        registry["literature_provenance"]["literature_is_hypothesis_source_not_local_evidence"]
        is True
    )
    assert len(registry["initial_candidate_classes"]) == 3
    assert all(item["status"] == "NOT_TESTED" for item in registry["initial_candidate_classes"])
    assert all(
        not item["real_A_share_outcome_read"]
        for item in registry["initial_candidate_classes"]
    )
    assert registry["scale_boundary"]["MAX_REAL_DEMO_CANDIDATES"] == 3
    assert registry["scale_boundary"]["AUTOMATED_ANOMALY_SCAN"] == "PROHIBITED"


def test_future_tradability_is_separately_authorized() -> None:
    boundary = _report("m4_stage4p_future_tradability_boundary_v1.json")
    assert boundary["CURRENTLY_NOT_AUTHORIZED"] is True
    assert boundary["direct_M4A_M4B_implementation"] == "PROHIBITED"
    assert boundary["portfolio_alpha_research"] == "NOT_AUTHORIZED"
    assert "transaction cost" in boundary["future_separate_review_may_consider"]


def test_architecture_does_not_require_new_engine_package_or_database_now() -> None:
    decision = _report("m4_stage4p_architecture_decision_v1.json")
    assert decision["architecture"] == "THIN_GENERIC_LAYER_OVER_PROVEN_M3_CORE"
    answers = decision["answers"]
    assert answers["new_package_knowledge_required_now"] is False
    assert answers["engine_py_required_now"] is False
    assert answers["database_schema_change_required_now"] is False
    assert answers["real_data_required_now"] is False
    assert decision["real_hypothesis_execution"] == "NOT_AUTHORIZED"


def test_no_m4_production_surface_was_created() -> None:
    assert not (ROOT / "src" / "ashare_research" / "m4").exists()
    assert not (ROOT / "src" / "ashare_research" / "engine.py").exists()
    assert not (ROOT / "knowledge").exists()


def test_final_governance_status_is_frozen() -> None:
    governance_paths = [
        ROOT
        / "agent/goals/2026-08-24_m4_stage4p_north_star_v2_adoption_and_architecture_preflight.md",
        ROOT / "acceptance/m4_stage4p_north_star_v2_adoption_and_architecture_preflight.md",
        ROOT
        / "agent/record/2026-08-24_Stage4P_north_star_v2_adoption_and_architecture_preflight.md",
    ]
    governance_text = [path.read_text(encoding="utf-8") for path in governance_paths]
    assert "COMPLETED — READY_FOR_NORTH_STAR_V2_MERGE_REVIEW" in governance_text[0]
    assert "COMPLETED — READY_FOR_NORTH_STAR_V2_MERGE_REVIEW" in governance_text[2]
    for text in governance_text:
        assert "ACTIVE_GOVERNANCE_PREFLIGHT" not in text
        assert "STOP_FOR_NORTH_STAR_V2_FINAL_MERGE_REVIEW" in text
    assert "`PASS — READY_FOR_NORTH_STAR_V2_MERGE_REVIEW`" in governance_text[1]
    assert "M4_STAGE4P_NORTH_STAR_V2_ADOPTION_PASS" in governance_text[1]
