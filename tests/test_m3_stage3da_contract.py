"""Synthetic-only governance tests for the M3 Stage 3D-A contract freeze."""

from __future__ import annotations

import ast
import copy
import json
from pathlib import Path

import pytest

import ashare_research.tools.m3_stage3da_contract_check as check

ROOT = Path(__file__).resolve().parents[1]


def _contracts() -> tuple[dict, dict, dict]:
    return tuple(
        json.loads((ROOT / path).read_text(encoding="utf-8"))
        for path in (check.DECISION_PATH, check.EXECUTION_PATH, check.POLICY_PATH)
    )


def test_repository_contract_readiness_is_pass_and_holdout_is_sealed() -> None:
    report = check.verify_repository_contracts(ROOT)
    assert report["status"] == "PASS"
    assert report["holdout_status"] == "SEALED"
    assert report["holdout_read"] is False
    assert report["holdout_start"] == "2023-01-01"
    assert report["holdout_end"] == "2026-08-13"
    assert report["stage3db_status"] == "NOT_STARTED"
    assert report["stage3db_eligible_for_separate_authorization"] is True
    assert set(report["checks"].values()) == {"PASS"}


def test_canonical_identity_gate_is_frozen() -> None:
    _, execution, _ = _contracts()
    assert execution["expected_upstream_inventory_sha"] == check.UPSTREAM
    assert execution["expected_pipeline_digest"] == check.PIPELINE
    assert execution["expected_model_digest"] == check.MODEL
    assert execution["expected_stage3cb_execution_adapter_digest"] == check.ADAPTER
    assert execution["expected_development_data_manifest_digest"] == check.DATA_MANIFEST
    assert execution["expected_stage3cc_robustness_execution_digest"] == check.ROBUSTNESS_DIGEST


@pytest.mark.parametrize(
    "field",
    ["holdout_read", "holdout_download", "holdout_parse", "holdout_hash"],
)
def test_decision_contract_forbids_real_holdout_access(field: str) -> None:
    decision, _, _ = _contracts()
    mutated = copy.deepcopy(decision)
    mutated[field] = True
    with pytest.raises(check.Stage3DAContractError, match=field.upper()):
        check.validate_decision_contract(mutated)


@pytest.mark.parametrize("end", ["latest available date", "2026-08-14", "2026-08-23", "today"])
def test_holdout_dynamic_or_extended_end_is_rejected(end: str) -> None:
    decision, execution, _ = _contracts()
    decision["holdout_end"] = end
    execution["holdout_end"] = end
    with pytest.raises(check.Stage3DAContractError):
        check.validate_decision_contract(decision)
    with pytest.raises(check.Stage3DAContractError):
        check.validate_execution_contract(execution)


def test_holdout_start_is_exactly_frozen() -> None:
    decision, execution, _ = _contracts()
    for contract in (decision, execution):
        mutated = copy.deepcopy(contract)
        mutated["holdout_start"] = "2023-01-02"
        with pytest.raises(check.Stage3DAContractError, match="HOLDOUT_START"):
            validator = (
                check.validate_decision_contract
                if contract is decision
                else check.validate_execution_contract
            )
            validator(mutated)


def test_unseal_requires_separate_stage3db_authorization_and_does_not_unseal_now() -> None:
    decision, execution, _ = _contracts()
    assert decision["unseal_decision"] == check.DECISION
    assert decision["holdout_status"] == "SEALED"
    assert decision["stage3db_requires_separate_authorization"] is True
    assert execution["stage3db_authorization_required"] is True


def test_execution_scope_and_single_accepted_execution_are_frozen() -> None:
    _, execution, _ = _contracts()
    assert execution["execution_scope"] == "FROZEN_PRIMARY_ONLY"
    assert execution["accepted_execution_max_count"] == 1
    assert execution["ab_reproducibility_rerun_allowed"] is True


def test_ab_rerun_requires_identical_immutable_matrix() -> None:
    _, execution, _ = _contracts()
    mutated = copy.deepcopy(execution)
    mutated["ab_reproducibility_rerun_policy"][
        "requires_identical_immutable_analysis_matrix"
    ] = False
    with pytest.raises(check.Stage3DAContractError, match="AB_MATRIX"):
        check.validate_execution_contract(mutated)


@pytest.mark.parametrize(
    "field",
    [
        "new_threshold_allowed",
        "new_proxy_allowed",
        "new_controls_allowed",
        "robustness_search_allowed",
        "holdout_extension_allowed",
    ],
)
def test_forbidden_execution_mutations_are_rejected(field: str) -> None:
    _, execution, _ = _contracts()
    mutated = copy.deepcopy(execution)
    mutated[field] = True
    with pytest.raises(check.Stage3DAContractError, match="FORBIDDEN_OPTION"):
        check.validate_execution_contract(mutated)


def test_new_model_is_rejected() -> None:
    _, execution, _ = _contracts()
    mutated = copy.deepcopy(execution)
    mutated["new_model_allowed"] = True
    with pytest.raises(check.Stage3DAContractError, match="FORBIDDEN_OPTION:new_model_allowed"):
        check.validate_execution_contract(mutated)


def test_primary_rule_is_gamma_and_lower_ci_only() -> None:
    _, execution, _ = _contracts()
    assert execution["primary_decision_rule"]["positive"] == (
        "gamma_holdout > 0 AND holdout_bootstrap_95ci_lower > 0"
    )
    for key, value in execution["primary_decision_rule"].items():
        if key.endswith("_substitution_allowed"):
            assert value is False


def test_development_primary_reversal_is_rejected() -> None:
    decision, _, policy = _contracts()
    mutated_decision = copy.deepcopy(decision)
    mutated_decision["development_primary_decision"] = (
        "M3_PRIMARY_DEVELOPMENT_POSITIVE_ABNORMAL_PERFORMANCE_ESTABLISHED"
    )
    with pytest.raises(check.Stage3DAContractError, match="PRIMARY_REVERSAL"):
        check.validate_decision_contract(mutated_decision)
    mutated_policy = copy.deepcopy(policy)
    mutated_policy["holdout_can_reverse_development_primary"] = True
    with pytest.raises(check.Stage3DAContractError, match="POLICY_REVERSAL"):
        check.validate_interpretation_policy(mutated_policy)


def test_holdout_positive_cannot_map_to_overall_established() -> None:
    _, _, policy = _contracts()
    case_b = next(item for item in policy["cases"] if item["case_id"] == "B")
    assert case_b["holdout_primary"] == "POSITIVE"
    assert case_b["overall_primary_established"] is False
    mutated = copy.deepcopy(policy)
    next(item for item in mutated["cases"] if item["case_id"] == "B")[
        "overall_primary_established"
    ] = True
    with pytest.raises(check.Stage3DAContractError, match="POLICY_OVERALL:B"):
        check.validate_interpretation_policy(mutated)


def test_interpretation_policy_contains_all_three_fail_closed_paths() -> None:
    _, _, policy = _contracts()
    dispositions = {item["case_id"]: item["final_disposition"] for item in policy["cases"]}
    assert dispositions == {
        "A": "M3_DAILY_MECHANISM_NOT_SUPPORTED_ACROSS_DEVELOPMENT_AND_HOLDOUT",
        "B": "M3_DEVELOPMENT_NOT_ESTABLISHED_HOLDOUT_POSITIVE_CROSS_PERIOD_INSTABILITY",
        "C": "M3_HOLDOUT_PRIMARY_INCONCLUSIVE_TECHNICAL_OR_COVERAGE_GAP",
    }


def test_causal_actor_minute_and_index_interpretations_are_prohibited() -> None:
    decision, _, policy = _contracts()
    boundary = decision["interpretation_boundary"]
    assert boundary["causal_interpretation_allowed"] is False
    assert boundary["funding_actor_interpretation_allowed"] is False
    assert boundary["minute_level_auto_escalation_allowed"] is False
    assert decision["minute_level_authorized"] is False
    assert decision["index_contribution_authorized"] is False
    assert policy["causal_interpretation_allowed"] is False
    assert policy["funding_actor_interpretation_allowed"] is False
    assert policy["minute_level_auto_escalation_allowed"] is False


def test_stage3da_validator_has_no_network_or_research_execution_imports() -> None:
    source = (ROOT / "src/ashare_research/tools/m3_stage3da_contract_check.py").read_text(
        encoding="utf-8"
    )
    tree = ast.parse(source)
    imports = {
        alias.name.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    imports.update(
        node.module.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module
        for alias in node.names
    )
    assert imports.isdisjoint(
        {"requests", "urllib", "httpx", "akshare", "baostock", "pandas", "numpy"}
    )
    called = {
        node.func.attr if isinstance(node.func, ast.Attribute) else node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute | ast.Name)
    }
    assert called.isdisjoint(
        {"fit_primary_ols", "moving_block_bootstrap", "materialize_analysis_matrix", "urlopen"}
    )


def test_cli_emits_a_local_contract_readiness_report(tmp_path: Path) -> None:
    output = tmp_path / "readiness.json"
    report = check.verify_repository_contracts(ROOT)
    output.write_text(json.dumps(report, sort_keys=True), encoding="utf-8")
    persisted = json.loads(output.read_text(encoding="utf-8"))
    assert persisted["holdout_read"] is False
    assert persisted["status"] == "PASS"
