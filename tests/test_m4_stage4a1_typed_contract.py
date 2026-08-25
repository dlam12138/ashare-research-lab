"""Synthetic-only tests for M4 Stage 4A.1 typed config and compiler."""

from __future__ import annotations

import re
from copy import deepcopy
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from ashare_research.mechanism.contract_compiler import (
    FROZEN_CONTRACT_SCHEMA_VERSION,
    ContractCompilationError,
    FrozenMechanismContract,
    compile_hypothesis_config,
    compute_contract_digest,
    contract_to_canonical_dict,
    serialize_frozen_contract,
    validate_contract,
)
from ashare_research.mechanism.hypothesis_config import (
    CONFIG_SCHEMA_VERSION,
    HypothesisConfigError,
    canonical_decimal,
    load_hypothesis_config,
    parse_hypothesis_config,
)


def _document() -> dict:
    return {
        "schema_version": CONFIG_SCHEMA_VERSION,
        "hypothesis_id": "SYNTH_DAILY_CONTROLLED_001",
        "target": {
            "series_id": "SYNTH_TARGET_A",
            "identity_policy": "SYNTHETIC_FIXED_IDENTITY",
        },
        "universe": {
            "universe_id": "SYNTH_UNIVERSE_A",
            "membership_policy": "SYNTHETIC_FIXED_UNIVERSE",
            "pit_policy": "EXPLICIT_PIT",
        },
        "factor": {
            "factor_id": "SYNTH_FACTOR_A",
            "factor_kind": "SYNTHETIC_REGISTERED",
            "direction": "POSITIVE",
            "transform_semantics": "RETURN",
        },
        "condition": {"operator": "LTE", "threshold": "-0.0100"},
        "outcome": {
            "outcome_id": "SYNTH_DAILY_RETURN",
            "horizon": "1D",
            "observation_timing": "CLOSE_TO_CLOSE",
        },
        "controls": ["SYNTH_CONTROL_1", "SYNTH_CONTROL_2"],
        "development": {"start": "2020-01-01", "end": "2022-12-31"},
        "data_quality_gates": {
            "coverage_gate": "0.9900",
            "pit_required": True,
            "identity_required": True,
            "missingness_policy": "FAIL_CLOSED",
            "duplicate_policy": "FAIL_CLOSED",
        },
        "analysis_method": {"method_id": "DAILY_CONDITIONAL_CONTROLLED_OLS_V1"},
        "bootstrap_policy": {
            "enabled": True,
            "method_id": "MOVING_BLOCK_BOOTSTRAP_V1",
            "replications": 1000,
            "seed": 42,
            "rng": "PCG64",
            "confidence_level": 0.95,
        },
        "robustness_registry": [
            {
                "robustness_id": "SYNTH_ROBUSTNESS_1",
                "method_id": "CONDITIONAL_DESCRIPTIVES_V1",
                "parameters": {"trim": "0.0100", "window": [1, 2, 3]},
            }
        ],
        "evidence_rule": {
            "rule_id": "SYNTH_EVIDENCE_RULE_1",
            "expected_direction": "POSITIVE",
            "confidence_requirement": "0.95",
            "data_quality_failure_disposition": "INCONCLUSIVE",
        },
    }


def _compiled(document: dict | None = None) -> FrozenMechanismContract:
    return compile_hypothesis_config(parse_hypothesis_config(document or _document()))


def _raises_code(code: str, func, *args, **kwargs) -> None:
    with pytest.raises((HypothesisConfigError, ContractCompilationError)) as caught:
        func(*args, **kwargs)
    assert caught.value.code == code


def test_valid_minimal_synthetic_config_compiles_to_distinct_frozen_type() -> None:
    contract = _compiled()
    assert isinstance(contract, FrozenMechanismContract)
    assert contract.schema_version == FROZEN_CONTRACT_SCHEMA_VERSION
    assert contract.contract_state == "FROZEN_PRE_EXECUTION"
    assert contract.target.series_id == "SYNTH_TARGET_A"
    assert contract.holdout_policy is None


def test_optional_holdout_is_concrete_and_disjoint() -> None:
    document = _document()
    document["holdout_policy"] = {
        "start": "2023-01-01",
        "end": "2023-12-31",
        "policy_id": "SYNTH_HOLDOUT_1",
        "max_accepted_primary_executions": 1,
    }
    contract = _compiled(document)
    assert contract.holdout_policy is not None
    assert contract.holdout_policy.start == "2023-01-01"


@pytest.mark.parametrize("field", ["target", "universe", "factor", "condition", "outcome"])
def test_missing_required_root_field_is_rejected(field: str) -> None:
    document = _document()
    del document[field]
    _raises_code("MISSING_REQUIRED_FIELD", parse_hypothesis_config, document)


def test_unknown_root_field_is_rejected() -> None:
    document = _document()
    document["optimize_threshold"] = False
    _raises_code("UNKNOWN_CONFIG_FIELD", parse_hypothesis_config, document)


def test_unknown_nested_field_is_rejected() -> None:
    document = _document()
    document["condition"]["expression"] = "x < 0"
    _raises_code("UNKNOWN_CONFIG_FIELD", parse_hypothesis_config, document)


def test_forbidden_false_feature_is_still_unknown() -> None:
    document = _document()
    document["provider_search"] = False
    _raises_code("UNKNOWN_CONFIG_FIELD", parse_hypothesis_config, document)


def test_wrong_schema_version_is_rejected() -> None:
    document = _document()
    document["schema_version"] = "M4_HYPOTHESIS_CONFIG_V0"
    _raises_code("INVALID_SCHEMA_VERSION", parse_hypothesis_config, document)


@pytest.mark.parametrize("value", ["", "bad/id", "https://example.com", "x y", "x:expr"])
def test_bad_hypothesis_id_is_rejected(value: str) -> None:
    document = _document()
    document["hypothesis_id"] = value
    _raises_code("INVALID_HYPOTHESIS_ID", parse_hypothesis_config, document)


def test_unsupported_factor_kind_is_rejected() -> None:
    document = _document()
    document["factor"]["factor_kind"] = "PYTHON_FUNCTION"
    _raises_code("UNSUPPORTED_FACTOR_KIND", parse_hypothesis_config, document)


def test_unsupported_condition_operator_is_rejected() -> None:
    document = _document()
    document["condition"]["operator"] = "AND"
    _raises_code("UNSUPPORTED_CONDITION_OPERATOR", parse_hypothesis_config, document)


@pytest.mark.parametrize("value", ["NaN", "Infinity", "-Infinity", float("nan"), float("inf")])
def test_nonfinite_threshold_is_rejected(value) -> None:
    document = _document()
    document["condition"]["threshold"] = value
    _raises_code("INVALID_NUMERIC_VALUE", parse_hypothesis_config, document)


def test_canonical_decimal_normalizes_forms_and_negative_zero() -> None:
    assert canonical_decimal("0.010") == "0.01"
    assert canonical_decimal("0.0100") == "0.01"
    assert canonical_decimal("-0.0100") == "-0.01"
    assert canonical_decimal("-0") == "0"
    assert canonical_decimal(0.010) == "0.01"


def test_duplicate_controls_are_rejected_and_order_is_preserved() -> None:
    document = _document()
    document["controls"] = ["SYNTH_CONTROL_1", "SYNTH_CONTROL_1"]
    _raises_code("DUPLICATE_CONTROL", parse_hypothesis_config, document)
    document = _document()
    document["controls"] = ["SYNTH_CONTROL_2", "SYNTH_CONTROL_1"]
    assert _compiled(document).controls == ("SYNTH_CONTROL_2", "SYNTH_CONTROL_1")


@pytest.mark.parametrize("field", ["start", "end"])
def test_bad_development_date_is_rejected(field: str) -> None:
    document = _document()
    document["development"][field] = "2020-02-30"
    _raises_code("INVALID_DATE", parse_hypothesis_config, document)


def test_reversed_development_window_is_rejected() -> None:
    document = _document()
    document["development"] = {"start": "2023-01-01", "end": "2022-12-31"}
    _raises_code("INVALID_DEVELOPMENT_WINDOW", parse_hypothesis_config, document)


def test_overlapping_holdout_window_is_rejected() -> None:
    document = _document()
    document["holdout_policy"] = {
        "start": "2022-12-31",
        "end": "2023-12-31",
        "policy_id": "SYNTH_HOLDOUT_1",
        "max_accepted_primary_executions": 1,
    }
    _raises_code("DEVELOPMENT_HOLDOUT_OVERLAP", parse_hypothesis_config, document)


@pytest.mark.parametrize(
    ("value", "expected_code"),
    [
        (-0.01, "INVALID_DATA_QUALITY_POLICY"),
        (1.01, "INVALID_DATA_QUALITY_POLICY"),
        ("NaN", "INVALID_NUMERIC_VALUE"),
    ],
)
def test_invalid_coverage_gate_is_rejected(value, expected_code: str) -> None:
    document = _document()
    document["data_quality_gates"]["coverage_gate"] = value
    _raises_code(expected_code, parse_hypothesis_config, document)


def test_unsupported_analysis_method_is_rejected() -> None:
    document = _document()
    document["analysis_method"]["method_id"] = "AUTOMATIC_MODEL_SELECTION"
    _raises_code("UNSUPPORTED_ANALYSIS_METHOD", parse_hypothesis_config, document)


def test_bootstrap_repetitions_must_be_positive_and_disabled_is_explicit() -> None:
    document = _document()
    document["bootstrap_policy"]["replications"] = 0
    _raises_code("INVALID_BOOTSTRAP_POLICY", parse_hypothesis_config, document)
    document = _document()
    document["bootstrap_policy"].update({"enabled": False, "method_id": "DISABLED"})
    assert _compiled(document).bootstrap_policy.enabled is False


def test_duplicate_robustness_id_is_rejected() -> None:
    document = _document()
    document["robustness_registry"].append(deepcopy(document["robustness_registry"][0]))
    _raises_code("DUPLICATE_ROBUSTNESS_ID", parse_hypothesis_config, document)


def test_noncanonicalizable_robustness_parameter_is_rejected() -> None:
    document = _document()
    document["robustness_registry"][0]["parameters"]["bad"] = object()
    _raises_code("NON_CANONICALIZABLE_VALUE", parse_hypothesis_config, document)


def test_evidence_rule_is_machine_readable() -> None:
    contract = _compiled()
    assert contract.evidence_rule.expected_direction == "POSITIVE"
    assert contract.evidence_rule.data_quality_failure_disposition == "INCONCLUSIVE"


def test_config_ab_semantic_identity_is_exact() -> None:
    document_a = _document()
    document_b = {
        "evidence_rule": document_a["evidence_rule"],
        "robustness_registry": document_a["robustness_registry"],
        "bootstrap_policy": {**document_a["bootstrap_policy"], "confidence_level": "0.9500"},
        "analysis_method": document_a["analysis_method"],
        "data_quality_gates": {**document_a["data_quality_gates"], "coverage_gate": 0.99},
        "development": {"end": "2022-12-31", "start": "2020-01-01"},
        "controls": list(document_a["controls"]),
        "outcome": document_a["outcome"],
        "condition": {"threshold": "-0.01", "operator": "LTE"},
        "factor": document_a["factor"],
        "universe": document_a["universe"],
        "target": document_a["target"],
        "hypothesis_id": document_a["hypothesis_id"],
        "schema_version": document_a["schema_version"],
    }
    contract_a, contract_b = _compiled(document_a), _compiled(document_b)
    assert contract_a.source_config_digest == contract_b.source_config_digest
    assert contract_to_canonical_dict(contract_a) == contract_to_canonical_dict(contract_b)
    assert serialize_frozen_contract(contract_a) == serialize_frozen_contract(contract_b)
    assert contract_a.contract_digest == contract_b.contract_digest


@pytest.mark.parametrize(
    ("section", "change"),
    [
        ("condition", lambda d: d["condition"].update(threshold="-0.02")),
        ("controls", lambda d: d.update(controls=["SYNTH_CONTROL_2", "SYNTH_CONTROL_1"])),
        ("development", lambda d: d["development"].update(end="2022-12-30")),
        ("coverage", lambda d: d["data_quality_gates"].update(coverage_gate="0.98")),
        ("seed", lambda d: d["bootstrap_policy"].update(seed=43)),
        (
            "robustness_parameter",
            lambda d: d["robustness_registry"][0]["parameters"].update(trim="0.0200"),
        ),
    ],
)
def test_meaningful_semantic_mutations_change_contract_digest(section: str, change) -> None:
    document = _document()
    changed = deepcopy(document)
    change(changed)
    assert _compiled(document).contract_digest != _compiled(changed).contract_digest


def test_nested_frozen_contract_values_cannot_be_mutated() -> None:
    contract = _compiled()
    with pytest.raises(FrozenInstanceError):
        contract.condition.threshold = "-0.02"  # type: ignore[misc]
    with pytest.raises(TypeError):
        contract.controls[0] = "OTHER"  # type: ignore[index]
    with pytest.raises(FrozenInstanceError):
        contract.robustness_registry.entries[0].method_id = "OTHER"  # type: ignore[misc]


def test_contract_self_validation_and_digest_exclude_self_reference() -> None:
    contract = _compiled()
    validate_contract(contract)
    assert compute_contract_digest(contract) == contract.contract_digest
    payload = contract_to_canonical_dict(contract)
    payload["contract_digest"] = "tampered"
    assert compute_contract_digest(contract) != payload["contract_digest"]


def test_serialization_is_utf8_canonical_json_with_fixed_newline() -> None:
    serialized = serialize_frozen_contract(_compiled())
    assert serialized.endswith(b"\n")
    assert serialized == serialized.decode("utf-8").encode("utf-8")
    assert b"\\u" not in serialized


def test_output_has_no_runtime_path_timestamp_or_user_metadata() -> None:
    payload = contract_to_canonical_dict(_compiled())
    rendered = serialize_frozen_contract(_compiled()).decode("utf-8")
    assert "D:\\" not in rendered
    assert "timestamp" not in payload
    assert "hostname" not in payload
    assert "username" not in payload
    assert "current_date" not in payload


def test_yaml_loader_requires_mapping_and_rejects_object_tags(tmp_path: Path) -> None:
    scalar = tmp_path / "scalar.yaml"
    scalar.write_text("- one\n- two\n", encoding="utf-8")
    _raises_code("INVALID_CONFIG_ROOT", load_hypothesis_config, scalar)
    unsafe = tmp_path / "unsafe.yaml"
    unsafe.write_text("!!python/object/apply:os.system ['echo bad']\n", encoding="utf-8")
    _raises_code("INVALID_CONFIG_DOCUMENT", load_hypothesis_config, unsafe)


def test_new_modules_have_no_forbidden_execution_or_acquisition_imports() -> None:
    root = Path(__file__).resolve().parents[1]
    source = "\n".join(
        Path(path).read_text(encoding="utf-8")
        for path in (
            root / "src/ashare_research/mechanism/hypothesis_config.py",
            root / "src/ashare_research/mechanism/contract_compiler.py",
        )
    )
    forbidden_imports = (
        r"(?:from|import)\s+.*\b(?:baostock|akshare|requests|statsmodels|pandas|regression|bootstrap)\b",
    )
    for forbidden in forbidden_imports:
        assert re.search(forbidden, source, re.IGNORECASE) is None
