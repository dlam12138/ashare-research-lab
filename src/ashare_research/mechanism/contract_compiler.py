"""Pure compiler from a typed M4-A.1 config to a frozen contract.

The compiler performs no acquisition or statistical execution.  Its only
external identity dependency is the repository's existing canonical digest
helper, reused as the single canonical JSON SHA-256 implementation.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, replace
from datetime import date
from typing import Any

from ashare_research.mechanism.hypothesis_config import (
    FrozenJSONList,
    FrozenJSONNumber,
    FrozenJSONObject,
    HypothesisConfig,
    HypothesisConfigError,
    canonical_decimal,
    parse_hypothesis_config,
)
from ashare_research.mechanism.model_digest import canonical_digest

FROZEN_CONTRACT_SCHEMA_VERSION = "M4_FROZEN_MECHANISM_CONTRACT_V1"
CONTRACT_STATE = "FROZEN_PRE_EXECUTION"
COMPILER_VERSION = "M4_A1_COMPILER_V1"
CONTRACT_DIGEST_ALGORITHM = "M4_CANONICAL_CONTRACT_DIGEST_V1"
SOURCE_CONFIG_DIGEST_ALGORITHM = "M4_CANONICAL_CONFIG_DIGEST_V1"
NO_HOLDOUT = "NO_HOLDOUT_AUTHORIZED_BY_THIS_CONTRACT"


class ContractCompilationError(ValueError):
    """A stable, machine-readable contract compilation/validation error."""

    def __init__(self, code: str, message: str | None = None) -> None:
        self.code = code
        super().__init__(message or code)


@dataclass(frozen=True)
class FrozenTargetSpec:
    series_id: str
    identity_policy: str


@dataclass(frozen=True)
class FrozenUniverseSpec:
    universe_id: str
    membership_policy: str
    pit_policy: str


@dataclass(frozen=True)
class FrozenFactorSpec:
    factor_id: str
    factor_kind: str
    direction: str
    transform_semantics: str


@dataclass(frozen=True)
class FrozenConditionSpec:
    operator: str
    threshold: str


@dataclass(frozen=True)
class FrozenOutcomeSpec:
    outcome_id: str
    horizon: str
    observation_timing: str


@dataclass(frozen=True)
class FrozenDevelopmentWindow:
    start: str
    end: str


@dataclass(frozen=True)
class FrozenDataQualityPolicy:
    coverage_gate: str
    pit_required: bool
    identity_required: bool
    missingness_policy: str
    duplicate_policy: str


@dataclass(frozen=True)
class FrozenAnalysisMethodSpec:
    method_id: str


@dataclass(frozen=True)
class FrozenBootstrapPolicy:
    enabled: bool
    method_id: str
    replications: int
    seed: int
    rng: str
    confidence_level: str


@dataclass(frozen=True)
class FrozenRobustnessSpec:
    robustness_id: str
    method_id: str
    parameters: FrozenJSONObject


@dataclass(frozen=True)
class FrozenRobustnessRegistry:
    entries: tuple[FrozenRobustnessSpec, ...]


@dataclass(frozen=True)
class FrozenEvidenceRule:
    rule_id: str
    expected_direction: str
    confidence_requirement: str
    data_quality_failure_disposition: str


@dataclass(frozen=True)
class FrozenHoldoutPolicy:
    start: str
    end: str
    policy_id: str
    max_accepted_primary_executions: int


@dataclass(frozen=True)
class FrozenMechanismContract:
    schema_version: str
    contract_state: str
    hypothesis_id: str
    target: FrozenTargetSpec
    universe: FrozenUniverseSpec
    factor: FrozenFactorSpec
    condition: FrozenConditionSpec
    outcome: FrozenOutcomeSpec
    controls: tuple[str, ...]
    development: FrozenDevelopmentWindow
    data_quality_gates: FrozenDataQualityPolicy
    analysis_method: FrozenAnalysisMethodSpec
    bootstrap_policy: FrozenBootstrapPolicy
    robustness_registry: FrozenRobustnessRegistry
    evidence_rule: FrozenEvidenceRule
    holdout_policy: FrozenHoldoutPolicy | None
    source_config_digest: str
    source_config_digest_algorithm: str
    contract_digest_algorithm: str
    compiler_version: str
    contract_digest: str


def _date_string(value: date) -> str:
    return value.isoformat()


def _json_value(value: Any) -> Any:
    if isinstance(value, FrozenJSONNumber):
        return value.value
    if isinstance(value, FrozenJSONList):
        return [_json_value(item) for item in value.items]
    if isinstance(value, FrozenJSONObject):
        return {key: _json_value(item) for key, item in value.items}
    return value


def _config_to_dict(config: HypothesisConfig) -> dict[str, Any]:
    holdout: dict[str, Any] | None
    if config.holdout_policy is None:
        holdout = None
    else:
        holdout = {
            "end": _date_string(config.holdout_policy.end),
            "max_accepted_primary_executions": (
                config.holdout_policy.max_accepted_primary_executions
            ),
            "policy_id": config.holdout_policy.policy_id,
            "start": _date_string(config.holdout_policy.start),
        }
    return {
        "analysis_method": {"method_id": config.analysis_method.method_id.value},
        "bootstrap_policy": {
            "confidence_level": canonical_decimal(config.bootstrap_policy.confidence_level),
            "enabled": config.bootstrap_policy.enabled,
            "method_id": config.bootstrap_policy.method_id.value,
            "replications": config.bootstrap_policy.replications,
            "rng": config.bootstrap_policy.rng.value,
            "seed": config.bootstrap_policy.seed,
        },
        "condition": {
            "operator": config.condition.operator.value,
            "threshold": canonical_decimal(config.condition.threshold),
        },
        "controls": list(config.controls),
        "data_quality_gates": {
            "coverage_gate": canonical_decimal(config.data_quality_gates.coverage_gate),
            "duplicate_policy": config.data_quality_gates.duplicate_policy.value,
            "identity_required": config.data_quality_gates.identity_required,
            "missingness_policy": config.data_quality_gates.missingness_policy.value,
            "pit_required": config.data_quality_gates.pit_required,
        },
        "development": {
            "end": _date_string(config.development.end),
            "start": _date_string(config.development.start),
        },
        "evidence_rule": {
            "confidence_requirement": canonical_decimal(
                config.evidence_rule.confidence_requirement
            ),
            "data_quality_failure_disposition": (
                config.evidence_rule.data_quality_failure_disposition.value
            ),
            "expected_direction": config.evidence_rule.expected_direction.value,
            "rule_id": config.evidence_rule.rule_id,
        },
        "factor": {
            "direction": config.factor.direction.value,
            "factor_id": config.factor.factor_id,
            "factor_kind": config.factor.factor_kind.value,
            "transform_semantics": config.factor.transform_semantics.value,
        },
        "holdout_policy": holdout,
        "hypothesis_id": config.hypothesis_id,
        "outcome": {
            "horizon": config.outcome.horizon,
            "observation_timing": config.outcome.observation_timing.value,
            "outcome_id": config.outcome.outcome_id,
        },
        "robustness_registry": [
            {
                "method_id": entry.method_id,
                "parameters": _json_value(entry.parameters),
                "robustness_id": entry.robustness_id,
            }
            for entry in config.robustness_registry.entries
        ],
        "schema_version": config.schema_version,
        "target": {
            "identity_policy": config.target.identity_policy.value,
            "series_id": config.target.series_id,
        },
        "universe": {
            "membership_policy": config.universe.membership_policy.value,
            "pit_policy": config.universe.pit_policy.value,
            "universe_id": config.universe.universe_id,
        },
    }


def config_to_canonical_dict(config: HypothesisConfig) -> dict[str, Any]:
    """Return canonical semantic config fields used for source identity."""

    if not isinstance(config, HypothesisConfig):
        raise ContractCompilationError("INVALID_CONFIG_TYPE")
    try:
        _validate_typed_config(config)
        return _config_to_dict(config)
    except HypothesisConfigError as exc:
        raise ContractCompilationError(exc.code) from exc


def _validate_typed_config(config: HypothesisConfig) -> None:
    """Recheck direct dataclass construction before compilation."""

    try:
        parsed = parse_hypothesis_config(_config_to_input(config))
    except HypothesisConfigError:
        raise
    if _config_to_dict(parsed) != _config_to_dict(config):
        raise HypothesisConfigError("NON_CANONICALIZABLE_VALUE")


def _config_to_input(config: HypothesisConfig) -> dict[str, Any]:
    """Convert typed fields back to parser-shaped values for one strict recheck."""

    def enum_value(value: Any) -> Any:
        return value.value if hasattr(value, "value") else value

    def frozen_value(value: Any) -> Any:
        if isinstance(value, FrozenJSONNumber):
            return value.value
        if isinstance(value, FrozenJSONList):
            return [frozen_value(item) for item in value.items]
        if isinstance(value, FrozenJSONObject):
            return {key: frozen_value(item) for key, item in value.items}
        return value

    holdout = None
    if config.holdout_policy is not None:
        holdout = {
            "start": _date_string(config.holdout_policy.start),
            "end": _date_string(config.holdout_policy.end),
            "policy_id": config.holdout_policy.policy_id,
            "max_accepted_primary_executions": (
                config.holdout_policy.max_accepted_primary_executions
            ),
        }
    data = _config_to_dict(config)
    data["target"] = {
        "series_id": config.target.series_id,
        "identity_policy": enum_value(config.target.identity_policy),
    }
    data["universe"] = {
        "universe_id": config.universe.universe_id,
        "membership_policy": enum_value(config.universe.membership_policy),
        "pit_policy": enum_value(config.universe.pit_policy),
    }
    data["factor"] = {
        "factor_id": config.factor.factor_id,
        "factor_kind": enum_value(config.factor.factor_kind),
        "direction": enum_value(config.factor.direction),
        "transform_semantics": enum_value(config.factor.transform_semantics),
    }
    data["condition"] = {
        "operator": enum_value(config.condition.operator),
        "threshold": canonical_decimal(config.condition.threshold),
    }
    data["outcome"] = {
        "outcome_id": config.outcome.outcome_id,
        "horizon": config.outcome.horizon,
        "observation_timing": enum_value(config.outcome.observation_timing),
    }
    data["development"] = {
        "start": _date_string(config.development.start),
        "end": _date_string(config.development.end),
    }
    data["holdout_policy"] = holdout
    if holdout is None:
        data.pop("holdout_policy", None)
    data["data_quality_gates"] = {
        "coverage_gate": canonical_decimal(config.data_quality_gates.coverage_gate),
        "pit_required": config.data_quality_gates.pit_required,
        "identity_required": config.data_quality_gates.identity_required,
        "missingness_policy": enum_value(config.data_quality_gates.missingness_policy),
        "duplicate_policy": enum_value(config.data_quality_gates.duplicate_policy),
    }
    data["analysis_method"] = {"method_id": enum_value(config.analysis_method.method_id)}
    data["bootstrap_policy"] = {
        "enabled": config.bootstrap_policy.enabled,
        "method_id": enum_value(config.bootstrap_policy.method_id),
        "replications": config.bootstrap_policy.replications,
        "seed": config.bootstrap_policy.seed,
        "rng": enum_value(config.bootstrap_policy.rng),
        "confidence_level": canonical_decimal(config.bootstrap_policy.confidence_level),
    }
    data["robustness_registry"] = [
        {
            "robustness_id": entry.robustness_id,
            "method_id": entry.method_id,
            "parameters": frozen_value(entry.parameters),
        }
        for entry in config.robustness_registry.entries
    ]
    data["evidence_rule"] = {
        "rule_id": config.evidence_rule.rule_id,
        "expected_direction": enum_value(config.evidence_rule.expected_direction),
        "confidence_requirement": canonical_decimal(config.evidence_rule.confidence_requirement),
        "data_quality_failure_disposition": enum_value(
            config.evidence_rule.data_quality_failure_disposition
        ),
    }
    return data


def _frozen_contract_without_digest(contract: FrozenMechanismContract) -> dict[str, Any]:
    payload = contract_to_canonical_dict(contract)
    payload.pop("contract_digest", None)
    return payload


def _compile_contract(config: HypothesisConfig, source_digest: str) -> FrozenMechanismContract:
    holdout = config.holdout_policy
    frozen_holdout = None if holdout is None else FrozenHoldoutPolicy(
        _date_string(holdout.start),
        _date_string(holdout.end),
        holdout.policy_id,
        holdout.max_accepted_primary_executions,
    )
    return FrozenMechanismContract(
        FROZEN_CONTRACT_SCHEMA_VERSION,
        CONTRACT_STATE,
        config.hypothesis_id,
        FrozenTargetSpec(config.target.series_id, config.target.identity_policy.value),
        FrozenUniverseSpec(
            config.universe.universe_id,
            config.universe.membership_policy.value,
            config.universe.pit_policy.value,
        ),
        FrozenFactorSpec(
            config.factor.factor_id,
            config.factor.factor_kind.value,
            config.factor.direction.value,
            config.factor.transform_semantics.value,
        ),
        FrozenConditionSpec(
            config.condition.operator.value,
            canonical_decimal(config.condition.threshold),
        ),
        FrozenOutcomeSpec(
            config.outcome.outcome_id,
            config.outcome.horizon,
            config.outcome.observation_timing.value,
        ),
        config.controls,
        FrozenDevelopmentWindow(
            _date_string(config.development.start),
            _date_string(config.development.end),
        ),
        FrozenDataQualityPolicy(
            canonical_decimal(config.data_quality_gates.coverage_gate),
            config.data_quality_gates.pit_required,
            config.data_quality_gates.identity_required,
            config.data_quality_gates.missingness_policy.value,
            config.data_quality_gates.duplicate_policy.value,
        ),
        FrozenAnalysisMethodSpec(config.analysis_method.method_id.value),
        FrozenBootstrapPolicy(
            config.bootstrap_policy.enabled,
            config.bootstrap_policy.method_id.value,
            config.bootstrap_policy.replications,
            config.bootstrap_policy.seed,
            config.bootstrap_policy.rng.value,
            canonical_decimal(config.bootstrap_policy.confidence_level),
        ),
        FrozenRobustnessRegistry(
            tuple(
                FrozenRobustnessSpec(entry.robustness_id, entry.method_id, entry.parameters)
                for entry in config.robustness_registry.entries
            )
        ),
        FrozenEvidenceRule(
            config.evidence_rule.rule_id,
            config.evidence_rule.expected_direction.value,
            canonical_decimal(config.evidence_rule.confidence_requirement),
            config.evidence_rule.data_quality_failure_disposition.value,
        ),
        frozen_holdout,
        source_digest,
        SOURCE_CONFIG_DIGEST_ALGORITHM,
        CONTRACT_DIGEST_ALGORITHM,
        COMPILER_VERSION,
        "",
    )


def compile_hypothesis_config(config: HypothesisConfig) -> FrozenMechanismContract:
    """Validate and compile a typed config into an immutable contract."""

    try:
        canonical_config = config_to_canonical_dict(config)
    except ContractCompilationError:
        raise
    source_digest = canonical_digest(canonical_config)
    contract = _compile_contract(config, source_digest)
    digest = canonical_digest(_frozen_contract_without_digest(contract))
    return replace(contract, contract_digest=digest)


def contract_to_canonical_dict(contract: FrozenMechanismContract) -> dict[str, Any]:
    """Return the stable, JSON-compatible contract envelope."""

    if not isinstance(contract, FrozenMechanismContract):
        raise ContractCompilationError("INVALID_CONTRACT_TYPE")
    return {
        "analysis_method": {"method_id": contract.analysis_method.method_id},
        "bootstrap_policy": {
            "confidence_level": contract.bootstrap_policy.confidence_level,
            "enabled": contract.bootstrap_policy.enabled,
            "method_id": contract.bootstrap_policy.method_id,
            "replications": contract.bootstrap_policy.replications,
            "rng": contract.bootstrap_policy.rng,
            "seed": contract.bootstrap_policy.seed,
        },
        "condition": {
            "operator": contract.condition.operator,
            "threshold": contract.condition.threshold,
        },
        "contract_digest": contract.contract_digest,
        "contract_digest_algorithm": contract.contract_digest_algorithm,
        "contract_state": contract.contract_state,
        "controls": list(contract.controls),
        "data_quality_gates": {
            "coverage_gate": contract.data_quality_gates.coverage_gate,
            "duplicate_policy": contract.data_quality_gates.duplicate_policy,
            "identity_required": contract.data_quality_gates.identity_required,
            "missingness_policy": contract.data_quality_gates.missingness_policy,
            "pit_required": contract.data_quality_gates.pit_required,
        },
        "development": {
            "end": contract.development.end,
            "start": contract.development.start,
        },
        "evidence_rule": {
            "confidence_requirement": contract.evidence_rule.confidence_requirement,
            "data_quality_failure_disposition": (
                contract.evidence_rule.data_quality_failure_disposition
            ),
            "expected_direction": contract.evidence_rule.expected_direction,
            "rule_id": contract.evidence_rule.rule_id,
        },
        "factor": {
            "direction": contract.factor.direction,
            "factor_id": contract.factor.factor_id,
            "factor_kind": contract.factor.factor_kind,
            "transform_semantics": contract.factor.transform_semantics,
        },
        "holdout_policy": (
            NO_HOLDOUT
            if contract.holdout_policy is None
            else {
                "end": contract.holdout_policy.end,
                "max_accepted_primary_executions": (
                    contract.holdout_policy.max_accepted_primary_executions
                ),
                "policy_id": contract.holdout_policy.policy_id,
                "start": contract.holdout_policy.start,
            }
        ),
        "hypothesis_id": contract.hypothesis_id,
        "outcome": {
            "horizon": contract.outcome.horizon,
            "observation_timing": contract.outcome.observation_timing,
            "outcome_id": contract.outcome.outcome_id,
        },
        "robustness_registry": [
            {
                "method_id": entry.method_id,
                "parameters": _json_value(entry.parameters),
                "robustness_id": entry.robustness_id,
            }
            for entry in contract.robustness_registry.entries
        ],
        "schema_version": contract.schema_version,
        "source_config_digest": contract.source_config_digest,
        "source_config_digest_algorithm": contract.source_config_digest_algorithm,
        "target": {
            "identity_policy": contract.target.identity_policy,
            "series_id": contract.target.series_id,
        },
        "universe": {
            "membership_policy": contract.universe.membership_policy,
            "pit_policy": contract.universe.pit_policy,
            "universe_id": contract.universe.universe_id,
        },
        "compiler_version": contract.compiler_version,
    }


def serialize_frozen_contract(contract: FrozenMechanismContract) -> bytes:
    """Serialize a contract as UTF-8 canonical JSON with one final newline."""

    try:
        validate_contract(contract)
        payload = contract_to_canonical_dict(contract)
        serialized = json.dumps(
            payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        )
        return (serialized + "\n").encode("utf-8")
    except ContractCompilationError:
        raise


def compute_contract_digest(contract: FrozenMechanismContract) -> str:
    """Compute the digest from the envelope with its own digest excluded."""

    if not isinstance(contract, FrozenMechanismContract):
        raise ContractCompilationError("INVALID_CONTRACT_TYPE")
    return canonical_digest(_frozen_contract_without_digest(contract))


def validate_contract(contract: FrozenMechanismContract) -> None:
    """Validate the frozen envelope and its self-consistent digest."""

    if not isinstance(contract, FrozenMechanismContract):
        raise ContractCompilationError("INVALID_CONTRACT_TYPE")
    if contract.schema_version != FROZEN_CONTRACT_SCHEMA_VERSION:
        raise ContractCompilationError("INVALID_CONTRACT_SCHEMA_VERSION")
    if contract.contract_state != CONTRACT_STATE:
        raise ContractCompilationError("INVALID_CONTRACT_STATE")
    if not contract.contract_digest or (
        compute_contract_digest(contract) != contract.contract_digest
    ):
        raise ContractCompilationError("CONTRACT_DIGEST_MISMATCH")
    if contract.holdout_policy is not None and not (
        contract.development.end < contract.holdout_policy.start
        or contract.holdout_policy.end < contract.development.start
    ):
        raise ContractCompilationError("DEVELOPMENT_HOLDOUT_OVERLAP")


__all__ = [
    "COMPILER_VERSION",
    "CONTRACT_DIGEST_ALGORITHM",
    "CONTRACT_STATE",
    "ContractCompilationError",
    "FROZEN_CONTRACT_SCHEMA_VERSION",
    "FrozenMechanismContract",
    "compute_contract_digest",
    "compile_hypothesis_config",
    "config_to_canonical_dict",
    "contract_to_canonical_dict",
    "parse_hypothesis_config",
    "serialize_frozen_contract",
    "validate_contract",
]
