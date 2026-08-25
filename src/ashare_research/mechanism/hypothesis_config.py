"""Typed, fail-closed configuration objects for the M4 Stage 4A.1 slice.

This module describes a bounded daily mechanism hypothesis.  It does not read
data, resolve providers, build an analysis plan, or execute a hypothesis.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from enum import StrEnum
from pathlib import Path
from typing import Any, TypeAlias

import yaml

CONFIG_SCHEMA_VERSION = "M4_HYPOTHESIS_CONFIG_V1"
_IDENTIFIER_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")
_HORIZON_RE = re.compile(r"^[1-9][0-9]*[DWMQY]$")


class HypothesisConfigError(ValueError):
    """A stable, machine-readable configuration error."""

    def __init__(self, code: str, message: str | None = None) -> None:
        self.code = code
        super().__init__(message or code)


class IdentityPolicy(StrEnum):
    SYNTHETIC_FIXED_IDENTITY = "SYNTHETIC_FIXED_IDENTITY"


class MembershipPolicy(StrEnum):
    SYNTHETIC_FIXED_UNIVERSE = "SYNTHETIC_FIXED_UNIVERSE"


class PITPolicy(StrEnum):
    EXPLICIT_PIT = "EXPLICIT_PIT"


class FactorKind(StrEnum):
    SYNTHETIC_REGISTERED = "SYNTHETIC_REGISTERED"


class FactorDirection(StrEnum):
    POSITIVE = "POSITIVE"
    NEGATIVE = "NEGATIVE"
    TWO_SIDED = "TWO_SIDED"


class FactorTransform(StrEnum):
    IDENTITY = "IDENTITY"
    RETURN = "RETURN"
    DIFFERENCE = "DIFFERENCE"
    STANDARDIZED = "STANDARDIZED"


class ConditionOperator(StrEnum):
    LT = "LT"
    LTE = "LTE"
    GT = "GT"
    GTE = "GTE"


class ObservationTiming(StrEnum):
    CLOSE_TO_CLOSE = "CLOSE_TO_CLOSE"


class MissingnessPolicy(StrEnum):
    FAIL_CLOSED = "FAIL_CLOSED"
    RETAIN_IN_DENOMINATOR = "RETAIN_IN_DENOMINATOR"


class DuplicatePolicy(StrEnum):
    FAIL_CLOSED = "FAIL_CLOSED"


class AnalysisMethod(StrEnum):
    DAILY_CONDITIONAL_CONTROLLED_OLS_V1 = "DAILY_CONDITIONAL_CONTROLLED_OLS_V1"


class BootstrapMethod(StrEnum):
    DISABLED = "DISABLED"
    MOVING_BLOCK_BOOTSTRAP_V1 = "MOVING_BLOCK_BOOTSTRAP_V1"


class RNGIdentity(StrEnum):
    PCG64 = "PCG64"


class EvidenceDirection(StrEnum):
    POSITIVE = "POSITIVE"
    NEGATIVE = "NEGATIVE"
    TWO_SIDED = "TWO_SIDED"


class EvidenceFailureDisposition(StrEnum):
    INCONCLUSIVE = "INCONCLUSIVE"
    FAIL = "FAIL"


FrozenJSONValue: TypeAlias = Any


@dataclass(frozen=True)
class FrozenJSONNumber:
    """A canonical numeric JSON value represented as a decimal string."""

    value: str


@dataclass(frozen=True)
class FrozenJSONList:
    items: tuple[FrozenJSONValue, ...]


@dataclass(frozen=True)
class FrozenJSONObject:
    items: tuple[tuple[str, FrozenJSONValue], ...]


def canonical_decimal(value: Any) -> str:
    """Return a finite, plain decimal string with insignificant zeros removed."""

    if isinstance(value, bool) or value is None:
        raise HypothesisConfigError("INVALID_NUMERIC_VALUE")
    try:
        decimal_value = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise HypothesisConfigError("INVALID_NUMERIC_VALUE") from exc
    if not decimal_value.is_finite():
        raise HypothesisConfigError("INVALID_NUMERIC_VALUE")
    if decimal_value == 0:
        return "0"
    plain = format(decimal_value.normalize(), "f")
    if "." in plain:
        plain = plain.rstrip("0").rstrip(".")
    return plain


def _canonical_json_value(value: Any) -> FrozenJSONValue:
    if value is None or isinstance(value, bool | str):
        return value
    if isinstance(value, int | float | Decimal) and not isinstance(value, bool):
        return FrozenJSONNumber(canonical_decimal(value))
    if isinstance(value, Mapping):
        items: list[tuple[str, FrozenJSONValue]] = []
        for key, item in value.items():
            if not isinstance(key, str):
                raise HypothesisConfigError("NON_CANONICALIZABLE_VALUE")
            items.append((key, _canonical_json_value(item)))
        return FrozenJSONObject(tuple(sorted(items, key=lambda entry: entry[0])))
    if isinstance(value, list | tuple):
        return FrozenJSONList(tuple(_canonical_json_value(item) for item in value))
    raise HypothesisConfigError("NON_CANONICALIZABLE_VALUE")


def _ensure_mapping(value: Any) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise HypothesisConfigError("INVALID_CONFIG_TYPE")
    if any(not isinstance(key, str) for key in value):
        raise HypothesisConfigError("INVALID_CONFIG_FIELD_NAME")
    return value


def _fields(
    value: Any,
    required: set[str],
    optional: set[str] | None = None,
) -> Mapping[str, Any]:
    if optional is None:
        optional = set()
    mapping = _ensure_mapping(value)
    unknown = set(mapping) - required - optional
    if unknown:
        raise HypothesisConfigError("UNKNOWN_CONFIG_FIELD")
    missing = required - set(mapping)
    if missing:
        raise HypothesisConfigError("MISSING_REQUIRED_FIELD")
    return mapping


def _identifier(value: Any, *, code: str = "INVALID_IDENTIFIER") -> str:
    if not isinstance(value, str) or not value or not _IDENTIFIER_RE.fullmatch(value):
        raise HypothesisConfigError(code)
    return value


def _enum(enum_type: type[StrEnum], value: Any, code: str) -> StrEnum:
    if not isinstance(value, str):
        raise HypothesisConfigError(code)
    try:
        return enum_type(value)
    except ValueError as exc:
        raise HypothesisConfigError(code) from exc


def _date(value: Any) -> date:
    if not isinstance(value, str):
        raise HypothesisConfigError("INVALID_DATE")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise HypothesisConfigError("INVALID_DATE") from exc


@dataclass(frozen=True)
class TargetSpec:
    series_id: str
    identity_policy: IdentityPolicy


@dataclass(frozen=True)
class UniverseSpec:
    universe_id: str
    membership_policy: MembershipPolicy
    pit_policy: PITPolicy


@dataclass(frozen=True)
class FactorSpec:
    factor_id: str
    factor_kind: FactorKind
    direction: FactorDirection
    transform_semantics: FactorTransform


@dataclass(frozen=True)
class ConditionSpec:
    operator: ConditionOperator
    threshold: Decimal


@dataclass(frozen=True)
class OutcomeSpec:
    outcome_id: str
    horizon: str
    observation_timing: ObservationTiming


@dataclass(frozen=True)
class DevelopmentWindow:
    start: date
    end: date


@dataclass(frozen=True)
class DataQualityPolicy:
    coverage_gate: Decimal
    pit_required: bool
    identity_required: bool
    missingness_policy: MissingnessPolicy
    duplicate_policy: DuplicatePolicy


@dataclass(frozen=True)
class AnalysisMethodSpec:
    method_id: AnalysisMethod


@dataclass(frozen=True)
class BootstrapPolicy:
    enabled: bool
    method_id: BootstrapMethod
    replications: int
    seed: int
    rng: RNGIdentity
    confidence_level: Decimal


@dataclass(frozen=True)
class RobustnessSpec:
    robustness_id: str
    method_id: str
    parameters: FrozenJSONObject


@dataclass(frozen=True)
class RobustnessRegistry:
    entries: tuple[RobustnessSpec, ...]


@dataclass(frozen=True)
class EvidenceRule:
    rule_id: str
    expected_direction: EvidenceDirection
    confidence_requirement: Decimal
    data_quality_failure_disposition: EvidenceFailureDisposition


@dataclass(frozen=True)
class HoldoutPolicy:
    start: date
    end: date
    policy_id: str
    max_accepted_primary_executions: int


@dataclass(frozen=True)
class HypothesisConfig:
    schema_version: str
    hypothesis_id: str
    target: TargetSpec
    universe: UniverseSpec
    factor: FactorSpec
    condition: ConditionSpec
    outcome: OutcomeSpec
    controls: tuple[str, ...]
    development: DevelopmentWindow
    data_quality_gates: DataQualityPolicy
    analysis_method: AnalysisMethodSpec
    bootstrap_policy: BootstrapPolicy
    robustness_registry: RobustnessRegistry
    evidence_rule: EvidenceRule
    holdout_policy: HoldoutPolicy | None = None


def _parse_target(value: Any) -> TargetSpec:
    fields = _fields(value, {"series_id", "identity_policy"})
    return TargetSpec(
        _identifier(fields["series_id"]),
        _enum(IdentityPolicy, fields["identity_policy"], "INVALID_IDENTITY_POLICY"),
    )


def _parse_universe(value: Any) -> UniverseSpec:
    fields = _fields(value, {"universe_id", "membership_policy", "pit_policy"})
    return UniverseSpec(
        _identifier(fields["universe_id"]),
        _enum(MembershipPolicy, fields["membership_policy"], "INVALID_MEMBERSHIP_POLICY"),
        _enum(PITPolicy, fields["pit_policy"], "INVALID_PIT_POLICY"),
    )


def _parse_factor(value: Any) -> FactorSpec:
    fields = _fields(value, {"factor_id", "factor_kind", "direction", "transform_semantics"})
    return FactorSpec(
        _identifier(fields["factor_id"]),
        _enum(FactorKind, fields["factor_kind"], "UNSUPPORTED_FACTOR_KIND"),
        _enum(FactorDirection, fields["direction"], "INVALID_FACTOR_DIRECTION"),
        _enum(FactorTransform, fields["transform_semantics"], "INVALID_FACTOR_TRANSFORM"),
    )


def _parse_condition(value: Any) -> ConditionSpec:
    fields = _fields(value, {"operator", "threshold"})
    try:
        threshold = Decimal(canonical_decimal(fields["threshold"]))
    except HypothesisConfigError as exc:
        raise HypothesisConfigError(exc.code) from exc
    return ConditionSpec(
        _enum(ConditionOperator, fields["operator"], "UNSUPPORTED_CONDITION_OPERATOR"),
        threshold,
    )


def _parse_outcome(value: Any) -> OutcomeSpec:
    fields = _fields(value, {"outcome_id", "horizon", "observation_timing"})
    horizon = fields["horizon"]
    if not isinstance(horizon, str) or not _HORIZON_RE.fullmatch(horizon):
        raise HypothesisConfigError("INVALID_OUTCOME_HORIZON")
    return OutcomeSpec(
        _identifier(fields["outcome_id"]),
        horizon,
        _enum(ObservationTiming, fields["observation_timing"], "INVALID_OBSERVATION_TIMING"),
    )


def _parse_development(value: Any) -> DevelopmentWindow:
    fields = _fields(value, {"start", "end"})
    start, end = _date(fields["start"]), _date(fields["end"])
    if start > end:
        raise HypothesisConfigError("INVALID_DEVELOPMENT_WINDOW")
    return DevelopmentWindow(start, end)


def _parse_quality(value: Any) -> DataQualityPolicy:
    fields = _fields(
        value,
        {
            "coverage_gate",
            "pit_required",
            "identity_required",
            "missingness_policy",
            "duplicate_policy",
        },
    )
    try:
        coverage = Decimal(canonical_decimal(fields["coverage_gate"]))
    except HypothesisConfigError as exc:
        raise HypothesisConfigError(exc.code) from exc
    if not 0 <= coverage <= 1:
        raise HypothesisConfigError("INVALID_DATA_QUALITY_POLICY")
    if not isinstance(fields["pit_required"], bool) or not isinstance(
        fields["identity_required"], bool
    ):
        raise HypothesisConfigError("INVALID_DATA_QUALITY_POLICY")
    return DataQualityPolicy(
        coverage,
        fields["pit_required"],
        fields["identity_required"],
        _enum(MissingnessPolicy, fields["missingness_policy"], "INVALID_DATA_QUALITY_POLICY"),
        _enum(DuplicatePolicy, fields["duplicate_policy"], "INVALID_DATA_QUALITY_POLICY"),
    )


def _parse_analysis(value: Any) -> AnalysisMethodSpec:
    fields = _fields(value, {"method_id"})
    return AnalysisMethodSpec(
        _enum(AnalysisMethod, fields["method_id"], "UNSUPPORTED_ANALYSIS_METHOD")
    )


def _parse_bootstrap(value: Any) -> BootstrapPolicy:
    fields = _fields(
        value,
        {"enabled", "method_id", "replications", "seed", "rng", "confidence_level"},
    )
    if not isinstance(fields["enabled"], bool):
        raise HypothesisConfigError("INVALID_BOOTSTRAP_POLICY")
    if isinstance(fields["replications"], bool) or not isinstance(fields["replications"], int):
        raise HypothesisConfigError("INVALID_BOOTSTRAP_POLICY")
    if fields["replications"] <= 0:
        raise HypothesisConfigError("INVALID_BOOTSTRAP_POLICY")
    if isinstance(fields["seed"], bool) or not isinstance(fields["seed"], int):
        raise HypothesisConfigError("INVALID_BOOTSTRAP_POLICY")
    try:
        confidence = Decimal(canonical_decimal(fields["confidence_level"]))
    except HypothesisConfigError as exc:
        raise HypothesisConfigError("INVALID_BOOTSTRAP_POLICY") from exc
    if not 0 < confidence < 1:
        raise HypothesisConfigError("INVALID_BOOTSTRAP_POLICY")
    method = _enum(BootstrapMethod, fields["method_id"], "INVALID_BOOTSTRAP_POLICY")
    if fields["enabled"] and method is BootstrapMethod.DISABLED:
        raise HypothesisConfigError("INVALID_BOOTSTRAP_POLICY")
    if not fields["enabled"] and method is not BootstrapMethod.DISABLED:
        raise HypothesisConfigError("INVALID_BOOTSTRAP_POLICY")
    return BootstrapPolicy(
        fields["enabled"],
        method,
        fields["replications"],
        fields["seed"],
        _enum(RNGIdentity, fields["rng"], "INVALID_BOOTSTRAP_POLICY"),
        confidence,
    )


def _parse_robustness(value: Any) -> RobustnessRegistry:
    if not isinstance(value, Sequence) or isinstance(value, str | bytes | bytearray):
        raise HypothesisConfigError("INVALID_CONFIG_TYPE")
    entries: list[RobustnessSpec] = []
    seen: set[str] = set()
    for item in value:
        fields = _fields(item, {"robustness_id", "method_id", "parameters"})
        robustness_id = _identifier(fields["robustness_id"])
        if robustness_id in seen:
            raise HypothesisConfigError("DUPLICATE_ROBUSTNESS_ID")
        seen.add(robustness_id)
        method_id = _identifier(fields["method_id"])
        parameters = _canonical_json_value(fields["parameters"])
        if not isinstance(parameters, FrozenJSONObject):
            raise HypothesisConfigError("NON_CANONICALIZABLE_VALUE")
        entries.append(RobustnessSpec(robustness_id, method_id, parameters))
    return RobustnessRegistry(tuple(entries))


def _parse_evidence(value: Any) -> EvidenceRule:
    fields = _fields(
        value,
        {
            "rule_id",
            "expected_direction",
            "confidence_requirement",
            "data_quality_failure_disposition",
        },
    )
    try:
        confidence = Decimal(canonical_decimal(fields["confidence_requirement"]))
    except HypothesisConfigError as exc:
        raise HypothesisConfigError("INVALID_EVIDENCE_RULE") from exc
    if not 0 < confidence <= 1:
        raise HypothesisConfigError("INVALID_EVIDENCE_RULE")
    return EvidenceRule(
        _identifier(fields["rule_id"]),
        _enum(EvidenceDirection, fields["expected_direction"], "INVALID_EVIDENCE_RULE"),
        confidence,
        _enum(
            EvidenceFailureDisposition,
            fields["data_quality_failure_disposition"],
            "INVALID_EVIDENCE_RULE",
        ),
    )


def _parse_holdout(value: Any) -> HoldoutPolicy:
    fields = _fields(value, {"start", "end", "policy_id", "max_accepted_primary_executions"})
    start, end = _date(fields["start"]), _date(fields["end"])
    if start > end:
        raise HypothesisConfigError("INVALID_HOLDOUT_WINDOW")
    maximum = fields["max_accepted_primary_executions"]
    if isinstance(maximum, bool) or not isinstance(maximum, int) or maximum <= 0:
        raise HypothesisConfigError("INVALID_HOLDOUT_WINDOW")
    return HoldoutPolicy(start, end, _identifier(fields["policy_id"]), maximum)


def parse_hypothesis_config(document: Mapping[str, Any]) -> HypothesisConfig:
    """Parse and strictly validate a mapping into a typed configuration."""

    fields = _fields(
        document,
        {
            "schema_version",
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
        },
        {"holdout_policy"},
    )
    if fields["schema_version"] != CONFIG_SCHEMA_VERSION:
        raise HypothesisConfigError("INVALID_SCHEMA_VERSION")
    hypothesis_id = fields["hypothesis_id"]
    if not isinstance(hypothesis_id, str) or not _IDENTIFIER_RE.fullmatch(hypothesis_id or ""):
        raise HypothesisConfigError("INVALID_HYPOTHESIS_ID")
    controls_value = fields["controls"]
    if not isinstance(controls_value, Sequence) or isinstance(
        controls_value, str | bytes | bytearray
    ):
        raise HypothesisConfigError("INVALID_CONFIG_TYPE")
    controls = tuple(_identifier(control) for control in controls_value)
    if len(controls) != len(set(controls)):
        raise HypothesisConfigError("DUPLICATE_CONTROL")
    development = _parse_development(fields["development"])
    holdout = _parse_holdout(fields["holdout_policy"]) if "holdout_policy" in fields else None
    if holdout is not None and not (
        development.end < holdout.start or holdout.end < development.start
    ):
        raise HypothesisConfigError("DEVELOPMENT_HOLDOUT_OVERLAP")
    return HypothesisConfig(
        CONFIG_SCHEMA_VERSION,
        hypothesis_id,
        _parse_target(fields["target"]),
        _parse_universe(fields["universe"]),
        _parse_factor(fields["factor"]),
        _parse_condition(fields["condition"]),
        _parse_outcome(fields["outcome"]),
        controls,
        development,
        _parse_quality(fields["data_quality_gates"]),
        _parse_analysis(fields["analysis_method"]),
        _parse_bootstrap(fields["bootstrap_policy"]),
        _parse_robustness(fields["robustness_registry"]),
        _parse_evidence(fields["evidence_rule"]),
        holdout,
    )


def load_hypothesis_config(path: str | Path) -> HypothesisConfig:
    """Load one YAML document with PyYAML's safe loader and parse it."""

    try:
        document = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, yaml.YAMLError) as exc:
        raise HypothesisConfigError("INVALID_CONFIG_DOCUMENT") from exc
    if not isinstance(document, Mapping):
        raise HypothesisConfigError("INVALID_CONFIG_ROOT")
    return parse_hypothesis_config(document)


__all__ = [
    "AnalysisMethod",
    "AnalysisMethodSpec",
    "BootstrapMethod",
    "BootstrapPolicy",
    "ConditionOperator",
    "ConditionSpec",
    "DataQualityPolicy",
    "DevelopmentWindow",
    "DuplicatePolicy",
    "EvidenceDirection",
    "EvidenceFailureDisposition",
    "EvidenceRule",
    "FactorDirection",
    "FactorKind",
    "FactorSpec",
    "FactorTransform",
    "FrozenJSONList",
    "FrozenJSONNumber",
    "FrozenJSONObject",
    "HypothesisConfig",
    "HypothesisConfigError",
    "IdentityPolicy",
    "MembershipPolicy",
    "MissingnessPolicy",
    "ObservationTiming",
    "PITPolicy",
    "RNGIdentity",
    "RobustnessRegistry",
    "RobustnessSpec",
    "TargetSpec",
    "UniverseSpec",
    "HoldoutPolicy",
    "OutcomeSpec",
    "canonical_decimal",
    "load_hypothesis_config",
    "parse_hypothesis_config",
]
