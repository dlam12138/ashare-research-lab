"""Pure, role-based implementation of the frozen M4-A.2 plan design.

Sections use A.1's immutable JSON representation. A digest detects modification;
it is a content identity, not a signature or authorization to execute research.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, fields, is_dataclass, replace
from types import UnionType
from typing import Any, get_args, get_origin, get_type_hints

from ashare_research.mechanism.contract_compiler import (
    FROZEN_CONTRACT_SCHEMA_VERSION,
    FrozenMechanismContract,
    compile_hypothesis_config,
    contract_to_canonical_dict,
    validate_contract,
)
from ashare_research.mechanism.hypothesis_config import (
    CONFIG_SCHEMA_VERSION,
    FrozenJSONList,
    FrozenJSONNumber,
    FrozenJSONObject,
    canonical_decimal,
    parse_hypothesis_config,
)
from ashare_research.mechanism.model_digest import canonical_digest

SCHEMA_VERSION = "M4_DETERMINISTIC_ANALYSIS_PLAN_V1"
PLAN_STATE = "DETERMINISTIC_PRE_EXECUTION_PLAN"
DIGEST_ALGORITHM = "M4_CANONICAL_ANALYSIS_PLAN_DIGEST_V1"
ANALYSIS_METHOD = "DAILY_CONDITIONAL_CONTROLLED_OLS_V1"


@dataclass(frozen=True)
class DeterministicAnalysisPlan:
    schema_version: str
    plan_state: str
    hypothesis_id: str
    source_contract_digest: str
    source_contract_schema_version: str
    analysis_method_id: str
    dataset_requirements: FrozenJSONObject
    sample_plan: FrozenJSONObject
    transform_plan: FrozenJSONObject
    design_plan: FrozenJSONObject
    conditional_summary_plan: FrozenJSONObject
    bootstrap_plan: FrozenJSONObject
    robustness_plan: FrozenJSONObject
    evidence_plan: FrozenJSONObject
    holdout_boundary: FrozenJSONObject
    plan_digest_algorithm: str
    plan_digest: str


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _check_json(value: Any) -> None:
    if value is None or type(value) in (str, bool, int):
        return
    if type(value) is FrozenJSONNumber:
        _require(type(value.value) is str, "INVALID_FROZEN_NUMBER")
        _require(canonical_decimal(value.value) == value.value, "NON_CANONICAL_NUMBER")
    elif type(value) is FrozenJSONList:
        _require(type(value.items) is tuple, "MUTABLE_JSON_LIST")
        for item in value.items:
            _check_json(item)
    elif type(value) is FrozenJSONObject:
        _require(type(value.items) is tuple, "MUTABLE_JSON_OBJECT")
        keys = []
        for pair in value.items:
            _require(type(pair) is tuple and len(pair) == 2, "INVALID_JSON_ENTRY")
            key, item = pair
            _require(type(key) is str, "INVALID_JSON_KEY")
            keys.append(key)
            _check_json(item)
        _require(keys == sorted(set(keys)), "NON_CANONICAL_JSON_KEYS")
    else:
        raise ValueError("INVALID_OR_MUTABLE_JSON_VALUE")


def _check_type(value: Any, expected: Any) -> None:
    """Check runtime construction, including bool/int and mutable-container traps."""
    if expected is Any:
        _check_json(value)
    elif get_origin(expected) is UnionType:
        matching = [kind for kind in get_args(expected) if type(value) is kind]
        _require(len(matching) == 1, "INVALID_FIELD_TYPE")
        _check_type(value, matching[0])
    elif get_origin(expected) is tuple:
        _require(type(value) is tuple, "MUTABLE_OR_INVALID_TUPLE")
        item_type, repeat = get_args(expected)
        _require(repeat is Ellipsis, "INVALID_TUPLE_SCHEMA")
        for item in value:
            _check_type(item, item_type)
    else:
        _require(type(value) is expected, "INVALID_FIELD_TYPE")
        if expected in (FrozenJSONObject, FrozenJSONList, FrozenJSONNumber):
            _check_json(value)
        elif is_dataclass(expected):
            for name, kind in get_type_hints(expected).items():
                _check_type(getattr(value, name), kind)


def _freeze(value: Any) -> Any:
    if type(value) is dict:
        return FrozenJSONObject(tuple((key, _freeze(item)) for key, item in sorted(value.items())))
    if type(value) in (tuple, list):
        return FrozenJSONList(tuple(_freeze(item) for item in value))
    return value


def _thaw(value: Any) -> Any:
    if type(value) is FrozenJSONObject:
        return {key: _thaw(item) for key, item in value.items}
    if type(value) is FrozenJSONList:
        return [_thaw(item) for item in value.items]
    if type(value) is FrozenJSONNumber:
        return value.value
    return value


def _validated_contract_dict(contract: FrozenMechanismContract) -> dict:
    _check_type(contract, FrozenMechanismContract)
    validate_contract(contract)
    payload = contract_to_canonical_dict(contract)
    # Reuse the existing semantic boundary; compare instead of accepting repairs.
    config_fields = (
        "hypothesis_id",
        "target",
        "universe",
        "factor",
        "condition",
        "outcome",
        "controls",
        "development",
        "data_quality_gates",
        "analysis_method",
        "bootstrap_policy",
        "robustness_registry",
        "evidence_rule",
    )
    document = {key: payload[key] for key in config_fields}
    document["schema_version"] = CONFIG_SCHEMA_VERSION
    if contract.holdout_policy is not None:
        document["holdout_policy"] = payload["holdout_policy"]
    rebuilt = compile_hypothesis_config(parse_hypothesis_config(document))
    _require(contract_to_canonical_dict(rebuilt) == payload, "NON_CANONICAL_CONTRACT")
    _require(contract.analysis_method.method_id == ANALYSIS_METHOD, "UNSUPPORTED_ANALYSIS_METHOD")
    return payload


def _terms(control_roles: list[str]) -> list[dict]:
    bindings = [("INTERCEPT", None, "alpha"), ("FACTOR_CONTINUOUS", "FACTOR", "beta_factor")]
    bindings.extend(
        (role, role, f"beta_control_{i:04d}") for i, role in enumerate(control_roles, 1)
    )
    bindings.append(("CONDITION_INDICATOR", "CONDITION_INDICATOR", "gamma_condition"))
    return [
        {"position": i, "term_role": role, "source_series_role": source, "coefficient_role": coef}
        for i, (role, source, coef) in enumerate(bindings, 1)
    ]


def _summary() -> dict:
    return {
        "dispatch_only": True,
        "condition_labels": ["CONDITION", "ORDINARY"],
        "required_statistic_roles": [
            "CONDITION_COUNT",
            "ORDINARY_COUNT",
            "CONDITION_MEAN",
            "ORDINARY_MEAN",
            "CONDITION_MEDIAN",
            "ORDINARY_MEDIAN",
            "CONDITION_MINUS_ORDINARY_MEAN",
            "CONDITION_MINUS_ORDINARY_MEDIAN",
        ],
        "source_roles": {"condition": "CONDITION_INDICATOR", "outcome": "TARGET_OUTCOME"},
    }


def _moving_blocks() -> dict:
    return {
        "method_id": "MOVING_BLOCK_BOOTSTRAP_V1",
        "block_length_policy_id": "N_CUBERT_ROUNDED_CLAMP_1_20_V1",
        "sampling": "non-circular overlapping moving blocks",
        "row_policy": "complete-row resampling",
    }


def _evidence_bindings() -> dict:
    return {
        "PRIMARY_EFFECT_ESTIMATE": "CONDITION_INDICATOR coefficient role gamma_condition",
        "PRIMARY_EFFECT_CI_LOWER": (
            "frozen bootstrap confidence interval lower bound for gamma_condition"
        ),
        "PRIMARY_EFFECT_CI_UPPER": (
            "frozen bootstrap confidence interval upper bound for gamma_condition"
        ),
    }


def build_analysis_plan(contract: FrozenMechanismContract) -> DeterministicAnalysisPlan:
    """Mechanically compile a validated contract; perform no IO or estimation."""
    source = _validated_contract_dict(contract)
    control_roles = [f"CONTROL_{i:04d}" for i in range(1, len(contract.controls) + 1)]
    role_specs = [
        ("TARGET_OUTCOME", contract.target.series_id, "OUTCOME_AS_DECLARED_BY_CONTRACT"),
        ("FACTOR", contract.factor.factor_id, contract.factor.transform_semantics),
        *[
            (role, series, "DAILY_RETURN")
            for role, series in zip(control_roles, contract.controls, strict=True)
        ],
    ]
    dataset = {
        "requirements": [
            {
                "role": role,
                "series_id": series,
                "transform_semantics": transform,
                "observation_timing": contract.outcome.observation_timing,
                "required_for_primary": True,
                "validity_requirement": "PIT_AND_IDENTITY_AND_FINITE",
            }
            for role, series, transform in role_specs
        ],
        "universe_requirement": source["universe"],
    }
    sample = {
        "window": source["development"],
        **source["data_quality_gates"],
        "selection_semantics": "QUALITY_BOUNDARY_BEFORE_COMPLETE_PRIMARY_ROWS",
        "coverage_denominator_policy": "NO_SILENT_ROLE_DATE_OR_SECURITY_DROPS",
    }
    transform = {
        "condition": {
            "source_role": "FACTOR",
            **source["condition"],
            "output_role": "CONDITION_INDICATOR",
            "true_value": 1,
            "false_value": 0,
        }
    }
    design = {
        "model_family": "OLS",
        "ordered_terms": _terms(control_roles),
        "response_role": "TARGET_OUTCOME",
    }
    bootstrap = {**source["bootstrap_policy"], "moving_block_semantics": _moving_blocks()}
    robustness = {
        "dispatch_only": True,
        "entries": source["robustness_registry"],
        "automatic_expansion": False,
        "automatic_selection": False,
    }
    evidence = {
        "dispatch_only": True,
        **source["evidence_rule"],
        "outcome_read": False,
        "required_statistic_roles": [
            "PRIMARY_EFFECT_ESTIMATE",
            "PRIMARY_EFFECT_CI_LOWER",
            "PRIMARY_EFFECT_CI_UPPER",
            "CONDITIONAL_MEAN_DIFFERENCE",
            "CONDITIONAL_MEDIAN_DIFFERENCE",
            "PRIMARY_SAMPLE_COVERAGE",
        ],
        "statistic_role_bindings": _evidence_bindings(),
    }
    holdout = {"policy_id": "NO_HOLDOUT_AUTHORIZED", "execution_authorized": False}
    if contract.holdout_policy is not None:
        policy = source["holdout_policy"]
        holdout = {
            "window": {"start": policy["start"], "end": policy["end"]},
            "policy_id": policy["policy_id"],
            "max_accepted_primary_executions": policy["max_accepted_primary_executions"],
            "execution_authorized": False,
        }
    plan = DeterministicAnalysisPlan(
        SCHEMA_VERSION,
        PLAN_STATE,
        contract.hypothesis_id,
        contract.contract_digest,
        contract.schema_version,
        contract.analysis_method.method_id,
        *map(
            _freeze,
            (
                dataset,
                sample,
                transform,
                design,
                _summary(),
                bootstrap,
                robustness,
                evidence,
                holdout,
            ),
        ),
        DIGEST_ALGORITHM,
        "",
    )
    plan = replace(plan, plan_digest=compute_plan_digest(plan))
    validate_analysis_plan(plan)
    return plan


def plan_to_canonical_dict(plan: DeterministicAnalysisPlan) -> dict:
    """Return an independent JSON-compatible envelope, without repairing identity."""
    _check_type(plan, DeterministicAnalysisPlan)
    return {field.name: _thaw(getattr(plan, field.name)) for field in fields(plan)}


def compute_plan_digest(plan: DeterministicAnalysisPlan) -> str:
    """Compute content identity excluding its self-reference; do not mutate the plan."""
    payload = plan_to_canonical_dict(plan)
    del payload["plan_digest"]
    return canonical_digest(payload)


def _keys(value: Any, names: str) -> None:
    _require(type(value) is dict and set(value) == set(names.split()), "INVALID_SECTION_FIELDS")


def _validate_dynamic_sections(payload: dict) -> None:
    """Reuse A.1 field semantics for the subset mechanically present in a plan."""
    dataset = payload["dataset_requirements"]
    _keys(dataset, "requirements universe_requirement")
    requirements = dataset["requirements"]
    for index, entry in enumerate(requirements):
        _keys(
            entry,
            "role series_id transform_semantics observation_timing "
            "required_for_primary validity_requirement",
        )
        _require(
            entry["required_for_primary"] is True
            and entry["validity_requirement"] == "PIT_AND_IDENTITY_AND_FINITE",
            "INVALID_REQUIREMENT_BOUNDARY",
        )
        _require(entry["observation_timing"] == "CLOSE_TO_CLOSE", "INVALID_OBSERVATION_TIMING")
        if index != 1:
            expected = "OUTCOME_AS_DECLARED_BY_CONTRACT" if index == 0 else "DAILY_RETURN"
            _require(entry["transform_semantics"] == expected, "INVALID_ROLE_TRANSFORM")
    sample = payload["sample_plan"]
    quality_keys = (
        "coverage_gate pit_required identity_required missingness_policy duplicate_policy"
    )
    _keys(sample, "window selection_semantics coverage_denominator_policy " + quality_keys)
    _require(
        sample["selection_semantics"] == "QUALITY_BOUNDARY_BEFORE_COMPLETE_PRIMARY_ROWS"
        and sample["coverage_denominator_policy"] == "NO_SILENT_ROLE_DATE_OR_SECURITY_DROPS",
        "INVALID_SAMPLE_BOUNDARY",
    )
    _keys(payload["transform_plan"], "condition")
    bootstrap = payload["bootstrap_plan"]
    bootstrap_keys = "enabled method_id replications seed rng confidence_level"
    _keys(bootstrap, bootstrap_keys + " moving_block_semantics")
    robustness = payload["robustness_plan"]
    _keys(robustness, "dispatch_only entries automatic_expansion automatic_selection")
    evidence = payload["evidence_plan"]
    evidence_keys = (
        "rule_id expected_direction confidence_requirement data_quality_failure_disposition"
    )
    _keys(
        evidence,
        evidence_keys + " dispatch_only outcome_read required_statistic_roles "
        "statistic_role_bindings",
    )
    _require(
        evidence["required_statistic_roles"]
        == [
            "PRIMARY_EFFECT_ESTIMATE",
            "PRIMARY_EFFECT_CI_LOWER",
            "PRIMARY_EFFECT_CI_UPPER",
            "CONDITIONAL_MEAN_DIFFERENCE",
            "CONDITIONAL_MEDIAN_DIFFERENCE",
            "PRIMARY_SAMPLE_COVERAGE",
        ],
        "INVALID_EVIDENCE_STATISTICS",
    )
    condition = payload["transform_plan"]["condition"]
    # Unmapped contract fields are placeholders used only to invoke A.1 validators.
    # They never enter the plan, its source identity, or the compilation output.
    document = {
        "schema_version": CONFIG_SCHEMA_VERSION,
        "hypothesis_id": payload["hypothesis_id"],
        "target": {
            "series_id": requirements[0]["series_id"],
            "identity_policy": "SYNTHETIC_FIXED_IDENTITY",
        },
        "universe": dataset["universe_requirement"],
        "factor": {
            "factor_id": requirements[1]["series_id"],
            "factor_kind": "SYNTHETIC_REGISTERED",
            "direction": "TWO_SIDED",
            "transform_semantics": requirements[1]["transform_semantics"],
        },
        "outcome": {
            "outcome_id": "PLAN_VALIDATION",
            "horizon": "1D",
            "observation_timing": requirements[0]["observation_timing"],
        },
        "condition": {key: condition[key] for key in ("operator", "threshold")},
        "controls": [entry["series_id"] for entry in requirements[2:]],
        "development": sample["window"],
        "data_quality_gates": {key: sample[key] for key in quality_keys.split()},
        "analysis_method": {"method_id": payload["analysis_method_id"]},
        "bootstrap_policy": {key: bootstrap[key] for key in bootstrap_keys.split()},
        "robustness_registry": robustness["entries"],
        "evidence_rule": {key: evidence[key] for key in evidence_keys.split()},
    }
    holdout = payload["holdout_boundary"]
    if "window" in holdout:
        _keys(holdout, "window policy_id max_accepted_primary_executions execution_authorized")
        document["holdout_policy"] = {
            **holdout["window"],
            "policy_id": holdout["policy_id"],
            "max_accepted_primary_executions": holdout["max_accepted_primary_executions"],
        }
    else:
        _keys(holdout, "policy_id execution_authorized")
        _require(holdout["policy_id"] == "NO_HOLDOUT_AUTHORIZED", "INVALID_ABSENT_HOLDOUT")
    canonical = contract_to_canonical_dict(
        compile_hypothesis_config(parse_hypothesis_config(document))
    )
    for key in (
        "development",
        "condition",
        "data_quality_gates",
        "bootstrap_policy",
        "evidence_rule",
    ):
        _require(canonical[key] == document[key], "NON_CANONICAL_PLAN_FIELD")
    if "holdout_policy" in document:
        _require(canonical["holdout_policy"] == document["holdout_policy"], "NON_CANONICAL_HOLDOUT")


def validate_analysis_plan(plan: DeterministicAnalysisPlan) -> None:
    """Reject invalid envelopes, mutable structures, role order and digest tampering."""
    payload = plan_to_canonical_dict(plan)
    _require(plan.schema_version == SCHEMA_VERSION, "INVALID_PLAN_VERSION")
    _require(plan.plan_state == PLAN_STATE, "INVALID_PLAN_STATE")
    _require(plan.analysis_method_id == ANALYSIS_METHOD, "UNSUPPORTED_ANALYSIS_METHOD")
    _require(plan.plan_digest_algorithm == DIGEST_ALGORITHM, "INVALID_PLAN_DIGEST_ALGORITHM")
    _require(
        plan.source_contract_schema_version == FROZEN_CONTRACT_SCHEMA_VERSION,
        "INVALID_SOURCE_SCHEMA",
    )
    _require(
        re.fullmatch(r"[0-9a-f]{64}", plan.source_contract_digest) is not None,
        "INVALID_SOURCE_IDENTITY",
    )
    _require(
        re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", plan.hypothesis_id) is not None,
        "INVALID_HYPOTHESIS_ID",
    )
    _require(compute_plan_digest(plan) == plan.plan_digest, "PLAN_DIGEST_MISMATCH")
    try:
        requirements = payload["dataset_requirements"]["requirements"]
        _require(type(requirements) is list and len(requirements) >= 2, "INVALID_DATASET_ROLES")
        controls = [f"CONTROL_{i:04d}" for i in range(1, len(requirements) - 1)]
        _require(
            [entry["role"] for entry in requirements] == ["TARGET_OUTCOME", "FACTOR", *controls],
            "INVALID_DATASET_ROLE_ORDER",
        )
        _require(
            payload["design_plan"]
            == {
                "model_family": "OLS",
                "ordered_terms": _terms(controls),
                "response_role": "TARGET_OUTCOME",
            },
            "INVALID_DESIGN_ROLE_ORDER",
        )
        _require(
            all(type(term["position"]) is int for term in payload["design_plan"]["ordered_terms"]),
            "INVALID_TERM_POSITION_TYPE",
        )
        condition = payload["transform_plan"]["condition"]
        _require(condition["operator"] in ("LT", "LTE", "GT", "GTE"), "INVALID_CONDITION")
        _require(
            type(condition["threshold"]) is str
            and canonical_decimal(condition["threshold"]) == condition["threshold"],
            "INVALID_CONDITION_THRESHOLD",
        )
        _require(
            condition
            == {
                "source_role": "FACTOR",
                "operator": condition["operator"],
                "threshold": condition["threshold"],
                "output_role": "CONDITION_INDICATOR",
                "true_value": 1,
                "false_value": 0,
            },
            "INVALID_CONDITION_ROLES",
        )
        _require(
            type(condition["true_value"]) is int and type(condition["false_value"]) is int,
            "INVALID_CONDITION_CODING_TYPE",
        )
        _require(payload["conditional_summary_plan"] == _summary(), "INVALID_SUMMARY_PLAN")
        _require(
            payload["conditional_summary_plan"]["dispatch_only"] is True, "INVALID_SUMMARY_BOUNDARY"
        )
        _require(
            payload["bootstrap_plan"]["moving_block_semantics"] == _moving_blocks(),
            "INVALID_BOOTSTRAP_SEMANTICS",
        )
        robustness = payload["robustness_plan"]
        _require(
            robustness["dispatch_only"] is True
            and robustness["automatic_expansion"] is False
            and robustness["automatic_selection"] is False,
            "INVALID_ROBUSTNESS_BOUNDARY",
        )
        evidence = payload["evidence_plan"]
        _require(
            evidence["dispatch_only"] is True
            and evidence["outcome_read"] is False
            and evidence["statistic_role_bindings"] == _evidence_bindings(),
            "INVALID_EVIDENCE_BOUNDARY",
        )
        _require(
            payload["holdout_boundary"]["execution_authorized"] is False,
            "HOLDOUT_EXECUTION_NOT_AUTHORIZED",
        )
        _validate_dynamic_sections(payload)
    except (KeyError, TypeError, IndexError) as exc:
        raise ValueError("INVALID_PLAN_STRUCTURE") from exc


def serialize_analysis_plan(plan: DeterministicAnalysisPlan) -> bytes:
    """Validate then emit sorted, compact UTF-8 JSON with exactly one final newline."""
    validate_analysis_plan(plan)
    return (
        json.dumps(
            plan_to_canonical_dict(plan), ensure_ascii=False, sort_keys=True, separators=(",", ":")
        )
        + "\n"
    ).encode("utf-8")
