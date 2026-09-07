"""Synthetic compile-only acceptance of the frozen A.2 design."""

import builtins
import json
import socket
from copy import deepcopy
from dataclasses import FrozenInstanceError, replace
from hashlib import sha256
from pathlib import Path

import pytest
from test_m4_stage4a1_typed_contract import _compiled, _document

from ashare_research.mechanism.contract_compiler import compute_contract_digest
from ashare_research.mechanism.hypothesis_config import FrozenJSONList, FrozenJSONObject
from ashare_research.mechanism.planning import (
    build_analysis_plan,
    compute_plan_digest,
    plan_to_canonical_dict,
    serialize_analysis_plan,
    validate_analysis_plan,
)

ROOT = Path(__file__).resolve().parents[1]


def _freeze(value):
    if isinstance(value, dict):
        return FrozenJSONObject(tuple((key, _freeze(item)) for key, item in sorted(value.items())))
    if isinstance(value, list):
        return FrozenJSONList(tuple(_freeze(item) for item in value))
    return value


def _rehash_contract(contract):
    return replace(contract, contract_digest=compute_contract_digest(contract))


def _changed_plan(plan, section, value, *, rehash=False):
    plan = replace(plan, **{section: _freeze(value)})
    return replace(plan, plan_digest=compute_plan_digest(plan)) if rehash else plan


def test_complete_plan_matches_frozen_design_and_contract():
    design = json.loads(
        (ROOT / "reports/m4_stage4a2_deterministic_analysis_plan_design_v1.json").read_text(
            encoding="utf-8"
        )
    )
    contract = _compiled()
    plan = build_analysis_plan(contract)
    data = plan_to_canonical_dict(plan)
    assert list(data) == design["plan_envelope"]["required_fields_in_ordered_schema"]
    assert data["schema_version"] == "M4_DETERMINISTIC_ANALYSIS_PLAN_V1"
    assert data["plan_state"] == design["plan_state"]
    assert data["source_contract_digest"] == contract.contract_digest
    assert data["source_contract_schema_version"] == contract.schema_version
    assert data["analysis_method_id"] == design["supported_analysis_method"]
    requirements = data["dataset_requirements"]["requirements"]
    assert requirements == [
        {
            "role": role,
            "series_id": series,
            "transform_semantics": transform,
            "observation_timing": "CLOSE_TO_CLOSE",
            "required_for_primary": True,
            "validity_requirement": "PIT_AND_IDENTITY_AND_FINITE",
        }
        for role, series, transform in [
            ("TARGET_OUTCOME", "SYNTH_TARGET_A", "OUTCOME_AS_DECLARED_BY_CONTRACT"),
            ("FACTOR", "SYNTH_FACTOR_A", "RETURN"),
            ("CONTROL_0001", "SYNTH_CONTROL_1", "DAILY_RETURN"),
            ("CONTROL_0002", "SYNTH_CONTROL_2", "DAILY_RETURN"),
        ]
    ]
    assert data["dataset_requirements"]["universe_requirement"] == _document()["universe"]
    assert data["sample_plan"] == {
        "window": {"start": "2020-01-01", "end": "2022-12-31"},
        "coverage_gate": "0.99",
        "pit_required": True,
        "identity_required": True,
        "missingness_policy": "FAIL_CLOSED",
        "duplicate_policy": "FAIL_CLOSED",
        "selection_semantics": "QUALITY_BOUNDARY_BEFORE_COMPLETE_PRIMARY_ROWS",
        "coverage_denominator_policy": "NO_SILENT_ROLE_DATE_OR_SECURITY_DROPS",
    }
    assert data["transform_plan"] == {
        "condition": {
            "source_role": "FACTOR",
            "operator": "LTE",
            "threshold": "-0.01",
            "output_role": "CONDITION_INDICATOR",
            "true_value": 1,
            "false_value": 0,
        }
    }
    terms = data["design_plan"]["ordered_terms"]
    assert [
        (term["position"], term["term_role"], term["source_series_role"], term["coefficient_role"])
        for term in terms
    ] == [
        (1, "INTERCEPT", None, "alpha"),
        (2, "FACTOR_CONTINUOUS", "FACTOR", "beta_factor"),
        (3, "CONTROL_0001", "CONTROL_0001", "beta_control_0001"),
        (4, "CONTROL_0002", "CONTROL_0002", "beta_control_0002"),
        (5, "CONDITION_INDICATOR", "CONDITION_INDICATOR", "gamma_condition"),
    ]
    assert data["design_plan"]["response_role"] == "TARGET_OUTCOME"
    assert data["design_plan"]["model_family"] == "OLS"
    for key in ("dispatch_only", "condition_labels", "required_statistic_roles", "source_roles"):
        assert data["conditional_summary_plan"][key] == design["conditional_summary_plan"][key]
    assert {key: data["bootstrap_plan"][key] for key in _document()["bootstrap_policy"]} == {
        **_document()["bootstrap_policy"],
        "confidence_level": "0.95",
    }
    for key, value in data["bootstrap_plan"]["moving_block_semantics"].items():
        assert value == design["bootstrap_plan"]["moving_block_semantics"][key]
    assert "block_length" not in data["bootstrap_plan"]
    assert data["robustness_plan"] == {
        "dispatch_only": True,
        "automatic_expansion": False,
        "automatic_selection": False,
        "entries": [
            {
                "robustness_id": "SYNTH_ROBUSTNESS_1",
                "method_id": "CONDITIONAL_DESCRIPTIVES_V1",
                "parameters": {"trim": "0.0100", "window": ["1", "2", "3"]},
            }
        ],
    }
    for key, value in _document()["evidence_rule"].items():
        assert data["evidence_plan"][key] == value
    for key in (
        "dispatch_only",
        "outcome_read",
        "required_statistic_roles",
        "statistic_role_bindings",
    ):
        assert data["evidence_plan"][key] == design["evidence_plan"][key]
    assert data["holdout_boundary"] == {
        "policy_id": "NO_HOLDOUT_AUTHORIZED",
        "execution_authorized": False,
    }
    assert data["plan_digest_algorithm"] == design["plan_identity"]["plan_digest_algorithm"]
    validate_analysis_plan(plan)


def test_fixed_synthetic_identity_and_canonical_serialization():
    contract = _compiled()
    plan = build_analysis_plan(contract)
    encoded = serialize_analysis_plan(plan)
    assert encoded == (
        json.dumps(
            plan_to_canonical_dict(plan), ensure_ascii=False, sort_keys=True, separators=(",", ":")
        )
        + "\n"
    ).encode("utf-8")
    assert encoded.endswith(b"\n") and not encoded.endswith(b"\n\n")
    assert contract.contract_digest == (
        "ee450d1f23cc68fb88718f3aa607cdda0c5e0d2b3fe951eddcb6e9b7b007f457"
    )
    assert plan.plan_digest == "45a2461708863a8f4e9cb92f7774d2ffd1084558950c8f421838174059e21981"
    assert sha256(encoded).hexdigest() == (
        "c2c2ea0bd541fb2640f47d5286af0a9121acbb77861ac1b363480a10773a9182"
    )
    assert compute_plan_digest(replace(plan, plan_digest="")) == plan.plan_digest


def test_semantic_ab_equivalence_and_cwd_independence(tmp_path, monkeypatch):
    a = _document()
    b = dict(reversed(list(deepcopy(a).items())))
    b["condition"] = {"threshold": -0.01, "operator": "LTE"}
    b["data_quality_gates"]["coverage_gate"] = 0.99
    b["bootstrap_policy"]["confidence_level"] = "0.9500"
    b["robustness_registry"][0]["parameters"] = {"window": [1.0, 2.0, 3.0], "trim": "0.0100"}
    original = build_analysis_plan(_compiled(a))
    monkeypatch.chdir(tmp_path)
    other = build_analysis_plan(_compiled(b))
    assert serialize_analysis_plan(original) == serialize_analysis_plan(other)
    assert original.plan_digest == other.plan_digest


@pytest.mark.parametrize(
    ("section", "field", "value"),
    [
        ("condition", "threshold", "-0.02"),
        ("condition", "operator", "LT"),
        ("development", "start", "2020-01-02"),
        ("development", "end", "2022-12-30"),
        ("data_quality_gates", "coverage_gate", "0.98"),
        ("data_quality_gates", "pit_required", False),
        ("data_quality_gates", "missingness_policy", "RETAIN_IN_DENOMINATOR"),
        ("bootstrap_policy", "seed", 43),
        ("bootstrap_policy", "replications", 999),
        ("bootstrap_policy", "confidence_level", "0.90"),
        ("evidence_rule", "confidence_requirement", "0.9"),
        ("evidence_rule", "expected_direction", "NEGATIVE"),
    ],
)
def test_semantic_changes_change_identity(section, field, value):
    document = _document()
    document[section][field] = value
    old, new = build_analysis_plan(_compiled()), build_analysis_plan(_compiled(document))
    assert old.plan_digest != new.plan_digest
    assert serialize_analysis_plan(old) != serialize_analysis_plan(new)


def test_controls_and_registry_keep_registration_order():
    document = _document()
    document["controls"].reverse()
    document["robustness_registry"].append(
        {
            "robustness_id": "AAA",
            "method_id": "UNIMPLEMENTED_DISPATCH_ONLY",
            "parameters": {"nested": {"values": [None, True, 0.25]}},
        }
    )
    first = build_analysis_plan(_compiled(document))
    data = plan_to_canonical_dict(first)
    assert [entry["series_id"] for entry in data["dataset_requirements"]["requirements"][2:]] == [
        "SYNTH_CONTROL_2",
        "SYNTH_CONTROL_1",
    ]
    assert [entry["robustness_id"] for entry in data["robustness_plan"]["entries"]] == [
        "SYNTH_ROBUSTNESS_1",
        "AAA",
    ]
    document["controls"].reverse()
    assert build_analysis_plan(_compiled(document)).plan_digest != first.plan_digest
    document["controls"].reverse()
    document["robustness_registry"].reverse()
    second = build_analysis_plan(_compiled(document))
    assert first.plan_digest != second.plan_digest
    document["robustness_registry"][0]["parameters"]["nested"]["values"][2] = 0.5
    assert second.plan_digest != build_analysis_plan(_compiled(document)).plan_digest


def test_optional_sections_and_holdout_are_declarative():
    document = _document()
    document["controls"] = []
    document["robustness_registry"] = []
    document["bootstrap_policy"].update(enabled=False, method_id="DISABLED")
    absent = build_analysis_plan(_compiled(document))
    data = plan_to_canonical_dict(absent)
    assert data["robustness_plan"]["entries"] == []
    assert data["bootstrap_plan"]["enabled"] is False
    assert data["bootstrap_plan"]["method_id"] == "DISABLED"
    assert len(data["design_plan"]["ordered_terms"]) == 3
    document["holdout_policy"] = {
        "start": "2023-01-01",
        "end": "2023-12-31",
        "policy_id": "SYNTH_HOLDOUT",
        "max_accepted_primary_executions": 1,
    }
    present = build_analysis_plan(_compiled(document))
    assert present.plan_digest != absent.plan_digest
    assert plan_to_canonical_dict(present)["holdout_boundary"] == {
        "window": {"start": "2023-01-01", "end": "2023-12-31"},
        "policy_id": "SYNTH_HOLDOUT",
        "max_accepted_primary_executions": 1,
        "execution_authorized": False,
    }


def test_deep_immutability_and_defensive_dictionary():
    plan = build_analysis_plan(_compiled())
    before = serialize_analysis_plan(plan)
    with pytest.raises(FrozenInstanceError):
        plan.plan_state = "EXECUTED"
    with pytest.raises(FrozenInstanceError):
        plan.robustness_plan.items = ()
    with pytest.raises(TypeError):
        plan.robustness_plan.items[0] = ("dispatch_only", False)
    registry = dict(plan.robustness_plan.items)["entries"]
    with pytest.raises(FrozenInstanceError):
        registry.items = ()
    data = plan_to_canonical_dict(plan)
    data["robustness_plan"]["entries"][0]["parameters"]["window"].append("999")
    data["dataset_requirements"]["requirements"][0]["series_id"] = "MUTATION"
    assert serialize_analysis_plan(plan) == before


@pytest.mark.parametrize("invalid", [None, {}, [], "contract", 1, True])
def test_wrong_public_input_types_fail(invalid):
    for function in (
        build_analysis_plan,
        plan_to_canonical_dict,
        compute_plan_digest,
        serialize_analysis_plan,
        validate_analysis_plan,
    ):
        with pytest.raises(ValueError):
            function(invalid)


@pytest.mark.parametrize(
    ("section", "field", "value"),
    [
        ("analysis_method", "method_id", "UNSUPPORTED"),
        ("condition", "operator", "EQ"),
        ("condition", "threshold", "NaN"),
        ("condition", "threshold", "-0.0100"),
        ("condition", "threshold", -0.01),
        ("bootstrap_policy", "seed", True),
        ("bootstrap_policy", "replications", 0),
        ("data_quality_gates", "coverage_gate", "1.1"),
        ("data_quality_gates", "pit_required", 1),
        ("development", "start", "20200101"),
    ],
)
def test_forged_contract_semantics_fail_even_with_rehashed_identity(section, field, value):
    contract = _compiled()
    contract = replace(contract, **{section: replace(getattr(contract, section), **{field: value})})
    with pytest.raises(ValueError):
        build_analysis_plan(_rehash_contract(contract))


def test_contract_digest_and_nested_mutability_rejected():
    contract = _compiled()
    with pytest.raises(ValueError, match="CONTRACT_DIGEST_MISMATCH"):
        build_analysis_plan(replace(contract, contract_digest="0" * 64))
    for changed in (
        replace(contract, controls=list(contract.controls)),
        replace(contract, condition={"operator": "LTE", "threshold": "-0.01"}),
        replace(contract, source_config_digest="0" * 64),
    ):
        with pytest.raises(ValueError):
            build_analysis_plan(changed)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("schema_version", "OTHER"),
        ("plan_state", "EXECUTED"),
        ("analysis_method_id", "OTHER"),
        ("source_contract_schema_version", "OTHER"),
        ("source_contract_digest", "bad"),
        ("plan_digest_algorithm", "OTHER"),
    ],
)
def test_plan_envelope_rejected_even_after_rehash(field, value):
    plan = replace(build_analysis_plan(_compiled()), **{field: value})
    plan = replace(plan, plan_digest=compute_plan_digest(plan))
    with pytest.raises(ValueError):
        validate_analysis_plan(plan)


@pytest.mark.parametrize("rehash", [False, True])
@pytest.mark.parametrize(
    "mutation",
    [
        "roles",
        "terms",
        "condition",
        "holdout",
        "sample",
        "bootstrap",
        "evidence",
        "extra",
    ],
)
def test_tampered_plan_boundaries_fail(mutation, rehash):
    plan = build_analysis_plan(_compiled())
    data = plan_to_canonical_dict(plan)
    section = {
        "roles": "dataset_requirements",
        "terms": "design_plan",
        "condition": "transform_plan",
        "holdout": "holdout_boundary",
        "sample": "sample_plan",
        "bootstrap": "bootstrap_plan",
        "evidence": "evidence_plan",
        "extra": "sample_plan",
    }[mutation]
    value = data[section]
    if mutation == "roles":
        value["requirements"].reverse()
    elif mutation == "terms":
        value["ordered_terms"][2:4] = reversed(value["ordered_terms"][2:4])
    elif mutation == "condition":
        value["condition"]["operator"] = "EQ"
    elif mutation == "holdout":
        value["execution_authorized"] = True
    elif mutation == "sample":
        value["coverage_gate"] = "-1"
    elif mutation == "bootstrap":
        value["moving_block_semantics"]["block_length"] = 5
    elif mutation == "evidence":
        value["required_statistic_roles"] = []
    else:
        value["timestamp"] = "RUNTIME_IDENTITY"
    with pytest.raises(ValueError):
        validate_analysis_plan(_changed_plan(plan, section, value, rehash=rehash))


def test_mutable_and_duplicate_json_structures_rejected():
    plan = build_analysis_plan(_compiled())
    for value in (
        {},
        FrozenJSONObject([]),
        FrozenJSONObject((("x", []),)),
        FrozenJSONObject((("x", True), ("x", False))),
    ):
        with pytest.raises(ValueError):
            validate_analysis_plan(replace(plan, sample_plan=value))
    with pytest.raises(ValueError, match="PLAN_DIGEST_MISMATCH"):
        serialize_analysis_plan(replace(plan, plan_digest="0" * 64))


@pytest.mark.parametrize("operator", ["LT", "LTE", "GT", "GTE"])
def test_all_frozen_condition_operators_are_copied(operator):
    document = _document()
    document["condition"] = {"operator": operator, "threshold": "0.025"}
    data = plan_to_canonical_dict(build_analysis_plan(_compiled(document)))
    assert data["transform_plan"]["condition"]["operator"] == operator
    assert data["transform_plan"]["condition"]["threshold"] == "0.025"


@pytest.mark.parametrize("section", ["design_plan", "transform_plan", "conditional_summary_plan"])
def test_booleans_cannot_impersonate_integer_plan_fields(section):
    plan = build_analysis_plan(_compiled())
    value = plan_to_canonical_dict(plan)[section]
    if section == "design_plan":
        value["ordered_terms"][0]["position"] = True
    elif section == "transform_plan":
        value["condition"]["true_value"] = True
    else:
        value["dispatch_only"] = 1
    with pytest.raises(ValueError):
        validate_analysis_plan(_changed_plan(plan, section, value, rehash=True))


def test_contract_source_identity_is_verified_not_only_self_digest():
    contract = _rehash_contract(replace(_compiled(), source_config_digest="0" * 64))
    with pytest.raises(ValueError, match="NON_CANONICAL_CONTRACT"):
        build_analysis_plan(contract)


def test_compilation_calls_a1_validation_but_no_io_or_statistics(monkeypatch):
    import ashare_research.mechanism.planning.compiler as compiler

    contract = _compiled()
    calls = []
    original = compiler.validate_contract

    def checked(value):
        calls.append(value.contract_digest)
        return original(value)

    def forbidden(*args, **kwargs):
        raise AssertionError("compile-only boundary crossed")

    monkeypatch.setattr(compiler, "validate_contract", checked)
    monkeypatch.setattr(builtins, "open", forbidden)
    monkeypatch.setattr(Path, "open", forbidden)
    monkeypatch.setattr(socket, "socket", forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)
    import sys

    def profile(frame, event, arg):
        if event == "call":
            module = frame.f_globals.get("__name__", "")
            assert not module.startswith(("pandas", "duckdb", "statsmodels", "requests"))
            assert frame.f_code.co_name not in ("fit_primary_ols", "moving_block_bootstrap")

    previous = sys.getprofile()
    try:
        sys.setprofile(profile)
        plan = build_analysis_plan(contract)
        serialize_analysis_plan(plan)
    finally:
        sys.setprofile(previous)
    assert calls == [contract.contract_digest]
