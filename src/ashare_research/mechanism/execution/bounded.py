"""Allow-listed bounded execution of the frozen M4 daily conditional OLS design.

This module implements ``docs/m4_bounded_execution_and_evidence_design_v1.md`` for
**synthetic fixtures only**.  It consumes the fully source-bound five-object chain
``(matrix, preparation, contract, plan, bound_inputs)``, always re-verifies the source with the
existing five-argument ``validate_design_matrix``, maps estimator inputs mechanically from the
plan's ``ordered_terms`` and the matrix cells, runs the allow-listed OLS and moving-block
bootstrap, computes conditional descriptives and the frozen evidence disposition, and emits
immutable, canonically serialized, digest-bound artifacts.

Boundaries kept by this module:

* no provider, filesystem, database, clock, environment, network or holdout access; the only
  randomness comes from the plan-declared ``seed`` with ``PCG64``;
* no M3 module (``regression``/``bootstrap``/``robustness``/``evidence``/``crash``/
  ``analysis_dataset``/``analysis_contracts``), no ``statsmodels`` and no ``pandas``;
* no matrix-only entry and no ``**kwargs``: every public entry needs the full five-object chain,
  so an undeclared keyword such as ``holdout`` is a ``TypeError`` rather than an ignored option;
* registered robustness is dispatch-only: request ids are validated, registry entries are bound
  and their complete canonical parameters are forwarded verbatim and immutably; **no** robustness
  statistic, selection, ranking or aggregate is computed or readable;
* ``execution_authorized`` is always ``False``; ``statistics_computed``/``outcome_read`` are
  ``True`` only on the synthetic primary artifact and strictly ``False`` on the dispatch artifact;
* the eight public entries never resolve a host, working directory, absolute path, session or
  environment identity, and the serializers reject such content mechanically.

The eight public callables are ``execute_bounded_analysis``,
``execution_artifact_to_canonical_dict``, ``serialize_execution_artifact``,
``validate_execution_artifact``, ``prepare_registered_robustness_dispatch``,
``robustness_artifact_to_canonical_dict``, ``serialize_robustness_artifact`` and
``validate_robustness_artifact``.  Private helpers (``_disposition``, ``_block_length``,
``_cell_to_float64`` and the other ``_``-prefixed functions) are implementation details; they are
not API and not acceptance entries.  A successful run states nothing about estimability,
statistical significance, economic validity, tradability or any A-share mechanism result.
"""

from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass, is_dataclass, replace
from decimal import ROUND_CEILING, ROUND_FLOOR, Decimal, InvalidOperation
from types import UnionType
from typing import Any, get_args, get_origin, get_type_hints

import numpy

from ashare_research.mechanism.contract_compiler import FrozenMechanismContract
from ashare_research.mechanism.datasets.synthetic import (
    BoundDatasetInputsV1,
    DatasetPreparationV1,
)
from ashare_research.mechanism.hypothesis_config import (
    FrozenJSONList,
    FrozenJSONNumber,
    FrozenJSONObject,
    HypothesisConfigError,
    canonical_decimal,
)
from ashare_research.mechanism.model_digest import canonical_digest
from ashare_research.mechanism.planning import DeterministicAnalysisPlan, plan_to_canonical_dict
from ashare_research.mechanism.planning.matrix import (
    FAILURE_DISPOSITIONS,
    MISSINGNESS_POLICIES,
    READY_STATUS,
    MatrixPreparationV1,
    validate_design_matrix,
)

ARTIFACT_SCHEMA_VERSION = "M4_BOUNDED_EXECUTION_ARTIFACT_V1"
ROBUSTNESS_ARTIFACT_SCHEMA_VERSION = "M4_REGISTERED_ROBUSTNESS_ARTIFACT_V1"
EXECUTOR_VERSION = "M4_BOUNDED_DAILY_CONDITIONAL_OLS_EXECUTOR_V1"
ESTIMATOR_CONTRACT_ID = "DAILY_CONDITIONAL_CONTROLLED_OLS_V1"
MODEL_FAMILY = "OLS"
NUMERIC_BACKEND = "numpy.linalg.lstsq"
MAX_ABS_CELL_DECIMAL = "1000000"
BLOCK_LENGTH_POLICY_ID = "N_CUBERT_ROUNDED_CLAMP_1_20_V1"
BOOTSTRAP_MIN_REPLICATIONS = 2
PROVENANCE_CLASS = "SYNTHETIC_TEST_ONLY"
PRIMARY_TERM_ROLE = "CONDITION_INDICATOR"
INTERCEPT_TERM_ROLE = "INTERCEPT"
SYNTHETIC_DATASET_MODE = "SYNTHETIC"
ALLOWED_ANALYSIS_METHODS = frozenset({ESTIMATOR_CONTRACT_ID})
ALLOWED_BOOTSTRAP_METHODS = frozenset({"MOVING_BLOCK_BOOTSTRAP_V1"})
ALLOWED_BOOTSTRAP_RNGS = frozenset({"PCG64"})
DISABLED_BOOTSTRAP_METHOD = "DISABLED"
EVIDENCE_DIRECTIONS = ("POSITIVE", "NEGATIVE", "TWO_SIDED")
DISPOSITIONS = (
    "POSITIVE_SUPPORTED",
    "NEGATIVE_SUPPORTED",
    "TWO_SIDED_SUPPORTED",
    "NOT_SUPPORTED",
    "INCONCLUSIVE",
)
REASONS = (
    "INTERVAL_ABOVE_ZERO",
    "INTERVAL_BELOW_ZERO",
    "INTERVAL_INCLUDES_ZERO",
    "BOOTSTRAP_DISABLED",
    "CONFIDENCE_BELOW_REQUIREMENT",
)
REQUIRED_EVIDENCE_STATISTIC_ROLES = (
    "PRIMARY_EFFECT_ESTIMATE",
    "PRIMARY_EFFECT_CI_LOWER",
    "PRIMARY_EFFECT_CI_UPPER",
    "CONDITIONAL_MEAN_DIFFERENCE",
    "CONDITIONAL_MEDIAN_DIFFERENCE",
    "PRIMARY_SAMPLE_COVERAGE",
)
INTERPRETATION_BOUNDARY = (
    "SYNTHETIC_TEST_ONLY: output of the frozen bounded executor on validated synthetic inputs. "
    "Not a research finding; not evidence of estimability, significance, economic validity or "
    "tradability; not an A-share mechanism result; not an authorization to execute on real data, "
    "on holdout data, or to enter M4-B."
)
FORBIDDEN_KEYS = frozenset(
    {
        "cwd",
        "worktree",
        "hostname",
        "username",
        "user",
        "home",
        "abspath",
        "absolute_path",
        "root_path",
        "env",
        "environment",
        "path",
        "session",
        "best",
        "best_result",
        "best_id",
        "selected",
        "selected_id",
        "winner",
        "aggregate",
        "ranking",
        "optimize",
        "tuned",
        "search",
    }
)
_IDENTIFIER_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]*")
_HASH_RE = re.compile(r"[0-9a-f]{64}")
_DATE_RE = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")
_ABSOLUTE_PATH_RE = re.compile(r"(?:[A-Za-z]:[\\/])|(?:\\\\)|(?:/[^/\s]+)")
_CONDITION_LABELS = ["CONDITION", "ORDINARY"]


class ExecutionError(ValueError):
    """Bounded-execution failure with a stable machine-readable code.

    ``disposition`` is populated only for ``DATA_QUALITY_REJECTED``, where it carries the plan's
    declared data-quality failure word verbatim (never a member of ``DISPOSITIONS``).
    """

    def __init__(
        self, code: str, message: str | None = None, disposition: str | None = None
    ) -> None:
        self.code = code
        self.disposition = disposition
        super().__init__(message or code)


def _fail(code: str, message: str | None = None, disposition: str | None = None) -> None:
    raise ExecutionError(code, message, disposition)


@dataclass(frozen=True)
class Float64ValueV1:
    """Normalized float64 rendering: exact binary identity plus a companion decimal text."""

    float64_hex: str
    canonical_decimal: str


@dataclass(frozen=True)
class SourceChainV1:
    contract_digest: str
    plan_digest: str
    input_digest: str
    domain_digest: str
    dataset_digest: str
    matrix_digest: str


@dataclass(frozen=True)
class ProvenanceV1:
    provenance_class: str
    synthetic_test_only: bool
    dataset_mode: str
    real_data_used: bool
    holdout_accessed: bool


@dataclass(frozen=True)
class TermRefV1:
    position: int
    term_role: str
    coefficient_role: str


@dataclass(frozen=True)
class MethodConfigurationV1:
    artifact_schema_version: str
    executor_version: str
    estimator_contract_id: str
    model_family: str
    numeric_backend: str
    numeric_runtime: str
    response_role: str
    terms: tuple[TermRefV1, ...]
    primary_effect_position: int
    primary_effect_role: str
    bootstrap_enabled: bool
    bootstrap_method_id: str
    block_length_policy_id: str
    bootstrap_replications: int
    bootstrap_seed: int
    bootstrap_rng: str
    bootstrap_confidence_level: str
    evidence_rule_id: str
    evidence_direction: str
    evidence_confidence_requirement: str
    data_quality_failure_disposition: str
    block_length: int | None


@dataclass(frozen=True)
class SampleBlockV1:
    row_count: int
    trade_dates: tuple[str, ...]
    coverage_numerator: int
    coverage_denominator: int
    coverage_gate: str
    coverage_gate_satisfied: bool
    coverage_complete: bool
    missingness_policy: str
    failure_disposition: str
    reason_counts: tuple[tuple[str, int], ...]
    rejected_dates: tuple[str, ...]


@dataclass(frozen=True)
class CoefficientV1:
    position: int
    term_role: str
    coefficient_role: str
    value: Float64ValueV1


@dataclass(frozen=True)
class EstimatorBlockV1:
    n_rows: int
    n_terms: int
    rank: int
    coefficients: tuple[CoefficientV1, ...]
    singular_values: tuple[Float64ValueV1, ...]
    residual_sum_of_squares: Float64ValueV1 | None
    primary_effect: Float64ValueV1


@dataclass(frozen=True)
class BootstrapBlockV1:
    enabled: bool
    method_id: str
    block_length: int | None
    replications: int | None
    seed: int | None
    rng: str | None
    confidence_level: str | None
    interval_alpha: str | None
    lower_index: int | None
    upper_index: int | None
    primary_effect_lower: Float64ValueV1 | None
    primary_effect_upper: Float64ValueV1 | None


@dataclass(frozen=True)
class StatisticValueV1:
    role: str
    kind: str
    count: int | None
    value: Float64ValueV1 | None


@dataclass(frozen=True)
class EvidenceBlockV1:
    rule_id: str
    expected_direction: str
    confidence_requirement: str
    data_quality_failure_disposition: str
    bootstrap_confidence_level: str | None
    confidence_requirement_satisfied: bool
    primary_effect_role: str
    primary_effect: Float64ValueV1
    interval_lower: Float64ValueV1 | None
    interval_upper: Float64ValueV1 | None
    disposition: str
    disposition_reason: str
    coverage_complete: bool
    interpretation_boundary: str


@dataclass(frozen=True)
class ExecutionArtifactV1:
    artifact_schema_version: str
    executor_version: str
    source_chain: SourceChainV1
    provenance: ProvenanceV1
    method_configuration: MethodConfigurationV1
    sample: SampleBlockV1
    estimator: EstimatorBlockV1
    bootstrap: BootstrapBlockV1
    conditional_descriptives: tuple[StatisticValueV1, ...]
    evidence: EvidenceBlockV1
    execution_authorized: bool
    statistics_computed: bool
    outcome_read: bool
    artifact_digest: str


@dataclass(frozen=True)
class RobustnessEntryDispatchV1:
    robustness_id: str
    request_ordinal: int
    registration_ordinal: int
    method_id: str
    parameters: FrozenJSONObject
    parameters_canonical_json: str


@dataclass(frozen=True)
class RobustnessDispatchV1:
    requested_ids: tuple[str, ...]
    registered_ids: tuple[str, ...]
    automatic_expansion: bool
    automatic_selection: bool
    parameters_interpreted: bool


@dataclass(frozen=True)
class RobustnessArtifactV1:
    artifact_schema_version: str
    executor_version: str
    source_chain: SourceChainV1
    provenance: ProvenanceV1
    method_configuration: MethodConfigurationV1
    sample: SampleBlockV1
    dispatch: RobustnessDispatchV1
    entries: tuple[RobustnessEntryDispatchV1, ...]
    execution_authorized: bool
    statistics_computed: bool
    outcome_read: bool
    artifact_digest: str


def _thaw_json(value: Any) -> Any:
    """Project a frozen JSON value to plain JSON (existing ``_thaw`` semantics).

    ``FrozenJSONObject`` / ``FrozenJSONList`` / ``FrozenJSONNumber`` are frozen dataclasses and
    cannot be serialized by ``canonical_digest``; only this projection enters a digest payload.
    Every call returns fresh containers, so returned dicts/lists are independent copies.
    """
    if type(value) is FrozenJSONObject:
        return {key: _thaw_json(item) for key, item in value.items}
    if type(value) is FrozenJSONList:
        return [_thaw_json(item) for item in value.items]
    if type(value) is FrozenJSONNumber:
        return value.value
    return value


def _frozen_json_shape(value: Any) -> None:
    if value is None or type(value) in (str, bool, int):
        return
    if type(value) is FrozenJSONNumber:
        if type(value.value) is not str:
            _fail("INVALID_INPUT_STRUCTURE")
        try:
            canonical = canonical_decimal(value.value)
        except HypothesisConfigError:
            _fail("INVALID_INPUT_STRUCTURE")
        if canonical != value.value:
            _fail("INVALID_INPUT_STRUCTURE")
        return
    if type(value) is FrozenJSONList:
        if type(value.items) is not tuple:
            _fail("INVALID_INPUT_STRUCTURE")
        for item in value.items:
            _frozen_json_shape(item)
        return
    if type(value) is FrozenJSONObject:
        if type(value.items) is not tuple:
            _fail("INVALID_INPUT_STRUCTURE")
        keys: list[str] = []
        for pair in value.items:
            if type(pair) is not tuple or len(pair) != 2 or type(pair[0]) is not str:
                _fail("INVALID_INPUT_STRUCTURE")
            keys.append(pair[0])
            _frozen_json_shape(pair[1])
        if keys != sorted(set(keys)):
            _fail("INVALID_INPUT_STRUCTURE")
        return
    _fail("INVALID_INPUT_STRUCTURE")


def _shape(value: Any, expected: Any) -> None:
    """Reject mutable or forged runtime representations before any projection."""
    if expected is Any:
        _frozen_json_shape(value)
        return
    origin = get_origin(expected)
    if origin is UnionType:
        for kind in get_args(expected):
            if type(value) is kind:
                _shape(value, kind)
                return
        _fail("INVALID_INPUT_STRUCTURE")
    if origin is tuple:
        if type(value) is not tuple:
            _fail("INVALID_INPUT_STRUCTURE")
        kinds = get_args(expected)
        if len(kinds) == 2 and kinds[1] is Ellipsis:
            for item in value:
                _shape(item, kinds[0])
            return
        if len(value) != len(kinds):
            _fail("INVALID_INPUT_STRUCTURE")
        for item, kind in zip(value, kinds, strict=True):
            _shape(item, kind)
        return
    if type(value) is not expected:
        _fail("INVALID_INPUT_STRUCTURE")
    if is_dataclass(expected):
        for name, kind in get_type_hints(expected).items():
            _shape(getattr(value, name), kind)


def _identifier_text(value: Any) -> bool:
    return type(value) is str and _IDENTIFIER_RE.fullmatch(value) is not None


def _date_text(value: Any) -> bool:
    return type(value) is str and _DATE_RE.fullmatch(value) is not None


def _canonical_decimal_text(value: Any, low: str, high: str) -> bool:
    """Strict canonical-decimal membership check with exact decimal comparison."""
    if type(value) is not str:
        return False
    try:
        parsed = Decimal(value)
    except (InvalidOperation, ValueError):
        return False
    if not parsed.is_finite() or canonical_decimal(value) != value:
        return False
    return Decimal(low) < parsed <= Decimal(high)


def _coverage_ge(numerator: int, denominator: int, gate: str) -> bool:
    """Exact rational coverage comparison ``n * q >= d * p`` (never float or percentages)."""
    p, q = Decimal(gate).as_integer_ratio()
    return numerator * q >= denominator * p


def _block_length(n: int) -> int:
    """Exact integer form of ``N_CUBERT_ROUNDED_CLAMP_1_20_V1`` (no floating ``pow``)."""
    k = 0
    while (2 * k + 1) ** 3 <= 8 * n:
        k += 1
    return max(1, min(20, k))


def _cell_to_float64(text: Any) -> float:
    """Single deterministic conversion: canonical decimal -> range gate -> float64 -> finite."""
    if type(text) is not str:
        _fail("INVALID_INPUT_STRUCTURE")
    try:
        parsed = Decimal(text)
    except (InvalidOperation, ValueError):
        _fail("INVALID_INPUT_STRUCTURE")
    if not parsed.is_finite():
        _fail("NON_FINITE_CELL")
    if abs(parsed) > Decimal(MAX_ABS_CELL_DECIMAL):
        _fail("CELL_OUT_OF_RANGE")
    value = float(parsed)
    if not math.isfinite(value):
        _fail("NON_FINITE_CELL")
    return value


def _float_value(value: float) -> Float64ValueV1:
    """Render one finite float64 as its exact hex identity plus companion decimal text."""
    if not math.isfinite(value):
        _fail("NON_FINITE_ESTIMATE")
    try:
        companion = canonical_decimal(repr(value))
    except HypothesisConfigError as exc:
        raise ExecutionError("NON_FINITE_ESTIMATE") from exc
    return Float64ValueV1(float.hex(value), companion)


def _check_float_value(value: Any) -> None:
    if type(value) is not Float64ValueV1:
        _fail("INVALID_INPUT_STRUCTURE")
    if type(value.float64_hex) is not str or type(value.canonical_decimal) is not str:
        _fail("INVALID_INPUT_STRUCTURE")
    try:
        parsed = float.fromhex(value.float64_hex)
    except ValueError:
        _fail("INVALID_INPUT_STRUCTURE")
    if not math.isfinite(parsed):
        _fail("NON_FINITE_ESTIMATE")
    if float.hex(parsed) != value.float64_hex:
        _fail("INVALID_INPUT_STRUCTURE")
    try:
        companion = canonical_decimal(repr(parsed))
    except HypothesisConfigError as exc:
        raise ExecutionError("NON_FINITE_ESTIMATE") from exc
    if companion != value.canonical_decimal:
        _fail("INVALID_INPUT_STRUCTURE")


def _check_plan_source(
    matrix: Any, preparation: Any, contract: Any, plan: Any, inputs: Any
) -> None:
    # X1 -- structure and type of the five source-bound objects
    _shape(matrix, MatrixPreparationV1)
    _shape(preparation, DatasetPreparationV1)
    _shape(plan, DeterministicAnalysisPlan)
    _shape(inputs, BoundDatasetInputsV1)
    _shape(contract, FrozenMechanismContract)
    # X2 -- the existing five-argument source verification; upstream errors propagate unchanged
    validate_design_matrix(matrix, preparation, contract, plan, inputs)


def _plan_sections(plan: DeterministicAnalysisPlan) -> dict:
    try:
        payload = plan_to_canonical_dict(plan)
    except (ValueError, TypeError) as exc:
        raise ExecutionError("INVALID_INPUT_STRUCTURE", str(exc)) from exc
    for key in (
        "design_plan",
        "bootstrap_plan",
        "robustness_plan",
        "evidence_plan",
        "conditional_summary_plan",
        "holdout_boundary",
    ):
        if type(payload.get(key)) is not dict:
            _fail("INVALID_INPUT_STRUCTURE", f"plan section {key} is missing")
    return payload


def _sample_block(matrix: MatrixPreparationV1) -> SampleBlockV1:
    quality = matrix.quality
    satisfied = _coverage_ge(
        quality.coverage_numerator, quality.coverage_denominator, quality.coverage_gate
    )
    return SampleBlockV1(
        len(matrix.rows),
        tuple(row.trade_date for row in matrix.rows),
        quality.coverage_numerator,
        quality.coverage_denominator,
        quality.coverage_gate,
        satisfied,
        quality.coverage_numerator == quality.coverage_denominator,
        quality.missingness_policy,
        quality.failure_disposition,
        quality.reason_counts,
        quality.rejected_dates,
    )


def _source_chain(matrix: MatrixPreparationV1) -> SourceChainV1:
    return SourceChainV1(
        matrix.source_contract_digest,
        matrix.plan_digest,
        matrix.input_digest,
        matrix.domain_digest,
        matrix.dataset_digest,
        matrix.matrix_digest,
    )


def _provenance(inputs: BoundDatasetInputsV1) -> ProvenanceV1:
    return ProvenanceV1(PROVENANCE_CLASS, True, inputs.mode, False, False)


@dataclass(frozen=True)
class _SourceContext:
    """Validated X1-X7 facts shared by both public entries (dispatch reuses them as R0-R6)."""

    source_chain: SourceChainV1
    provenance: ProvenanceV1
    method_configuration: MethodConfigurationV1
    sample: SampleBlockV1
    plan: DeterministicAnalysisPlan
    design: dict
    bootstrap_plan: dict
    robustness_plan: dict
    registered_entries: tuple[FrozenJSONObject, ...]
    evidence_plan: dict
    summary_plan: dict
    terms: tuple[TermRefV1, ...]
    primary_index: int
    primary_position: int
    primary_role: str
    condition_index: int
    indicator_cells: tuple[str, ...]
    rows: tuple[tuple[float, ...], ...]
    response: tuple[float, ...]
    n_rows: int
    n_terms: int


def _frozen_registry_entries(plan: DeterministicAnalysisPlan) -> tuple[FrozenJSONObject, ...]:
    """Read the registry entries in their frozen, immutable form (verbatim forwarding)."""
    entries_value: Any = None
    for key, value in plan.robustness_plan.items:
        if key == "entries":
            entries_value = value
    if type(entries_value) is not FrozenJSONList:
        _fail("INVALID_INPUT_STRUCTURE")
    entries: list[FrozenJSONObject] = []
    for item in entries_value.items:
        if type(item) is not FrozenJSONObject:
            _fail("INVALID_INPUT_STRUCTURE")
        entries.append(item)
    return tuple(entries)


def _frozen_entry_field(entry: FrozenJSONObject, name: str) -> Any:
    for key, value in entry.items:
        if key == name:
            return value
    _fail("INVALID_INPUT_STRUCTURE")


def _bootstrap_declaration(bootstrap: dict) -> tuple[bool, str, int, int, str, str]:
    """Read the plan-declared bootstrap block verbatim; perform no allow-list gate here.

    The allow-list and replication gates belong to X11 and must not run before X8-X10, so this
    helper only refuses malformed declarations (a structure failure) and never re-derives a value.
    """
    enabled = bootstrap.get("enabled")
    if type(enabled) is not bool:
        _fail("INVALID_INPUT_STRUCTURE", "bootstrap.enabled must be a strict boolean")
    method_id = bootstrap.get("method_id")
    replications = bootstrap.get("replications")
    seed = bootstrap.get("seed")
    rng = bootstrap.get("rng")
    confidence = bootstrap.get("confidence_level")
    if not _identifier_text(method_id) or not _identifier_text(rng):
        _fail("INVALID_INPUT_STRUCTURE")
    if type(replications) is not int or type(seed) is not int:
        _fail("INVALID_INPUT_STRUCTURE")
    if not _canonical_decimal_text(confidence, "0", "1"):
        _fail("INVALID_INPUT_STRUCTURE")
    semantics = bootstrap.get("moving_block_semantics")
    if type(semantics) is not dict or (
        semantics.get("block_length_policy_id") != BLOCK_LENGTH_POLICY_ID
    ):
        _fail("INVALID_INPUT_STRUCTURE")
    return enabled, method_id, replications, seed, rng, confidence


def _validated_source(
    matrix: MatrixPreparationV1,
    preparation: DatasetPreparationV1,
    contract: Any,
    plan: DeterministicAnalysisPlan,
    bound_inputs: Any,
) -> _SourceContext:
    """Run X1-X7 once; both public entries reuse this identical order as R0-R6."""
    _check_plan_source(matrix, preparation, contract, plan, bound_inputs)
    sections = _plan_sections(plan)
    design = sections["design_plan"]
    bootstrap = sections["bootstrap_plan"]
    robustness = sections["robustness_plan"]
    evidence = sections["evidence_plan"]
    summary = sections["conditional_summary_plan"]
    holdout = sections["holdout_boundary"]

    # X3 -- analysis method and model family allow-lists (no downgrade, no fallback)
    if plan.analysis_method_id not in ALLOWED_ANALYSIS_METHODS:
        _fail("UNSUPPORTED_ANALYSIS_METHOD")
    if design.get("model_family") != MODEL_FAMILY:
        _fail("UNSUPPORTED_MODEL_FAMILY")

    # X4 -- quality precondition; the failure word rides only on the refusal itself
    quality_word = evidence.get("data_quality_failure_disposition")
    if quality_word not in FAILURE_DISPOSITIONS:
        _fail("INVALID_INPUT_STRUCTURE", "quality failure disposition is not a frozen word")
    if matrix.quality.status != READY_STATUS or not matrix.rows:
        _fail("DATA_QUALITY_REJECTED", None, quality_word)
    if matrix.quality.missingness_policy not in MISSINGNESS_POLICIES:
        _fail("INVALID_INPUT_STRUCTURE", "missingness policy is not a frozen policy word")
    if not _coverage_ge(
        matrix.quality.coverage_numerator,
        matrix.quality.coverage_denominator,
        matrix.quality.coverage_gate,
    ):
        _fail("DATA_QUALITY_REJECTED", None, quality_word)

    # X5 -- synthetic-only dataset mode and the fail-closed holdout boundary
    if bound_inputs.mode != SYNTHETIC_DATASET_MODE:
        _fail("UNSUPPORTED_DATASET_MODE")
    if holdout.get("execution_authorized") is not False:
        _fail("HOLDOUT_NOT_AUTHORIZED")
    window = holdout.get("window")
    if window is not None:
        if type(window) is not dict:
            _fail("INVALID_INPUT_STRUCTURE")
        start, end = window.get("start"), window.get("end")
        if not _date_text(start) or not _date_text(end) or start > end:
            _fail("INVALID_INPUT_STRUCTURE")
        for row in matrix.rows:
            if start <= row.trade_date <= end:
                _fail("HOLDOUT_NOT_AUTHORIZED")

    # X6 -- plan/column term mapping, unique INTERCEPT/INDICATOR, row alignment
    ordered_terms = design.get("ordered_terms")
    if type(ordered_terms) is not list or not ordered_terms:
        _fail("PLAN_TERM_ROLE_MISMATCH")
    terms: list[TermRefV1] = []
    for term in ordered_terms:
        if type(term) is not dict:
            _fail("PLAN_TERM_ROLE_MISMATCH")
        position = term.get("position")
        term_role = term.get("term_role")
        coefficient_role = term.get("coefficient_role")
        if type(position) is not int or type(term_role) is not str:
            _fail("PLAN_TERM_ROLE_MISMATCH")
        if type(coefficient_role) is not str or not coefficient_role:
            _fail("PLAN_TERM_ROLE_MISMATCH")
        terms.append(TermRefV1(position, term_role, coefficient_role))
    if [(c.position, c.term_role, c.coefficient_role) for c in matrix.columns] != [
        (t.position, t.term_role, t.coefficient_role) for t in terms
    ]:
        _fail("PLAN_TERM_ROLE_MISMATCH")
    if [t.position for t in terms] != list(range(1, len(terms) + 1)):
        _fail("PLAN_TERM_ROLE_MISMATCH")
    if matrix.response_role != design.get("response_role"):
        _fail("PLAN_TERM_ROLE_MISMATCH")
    condition_positions = [i for i, t in enumerate(terms) if t.term_role == PRIMARY_TERM_ROLE]
    intercept_positions = [i for i, t in enumerate(terms) if t.term_role == INTERCEPT_TERM_ROLE]
    if len(condition_positions) != 1 or len(intercept_positions) != 1:
        _fail("PLAN_TERM_ROLE_MISMATCH")
    primary_index = condition_positions[0]
    primary_role = terms[primary_index].coefficient_role
    if matrix.response_role not in preparation.role_order:
        _fail("MATRIX_PREPARATION_ALIGNMENT_MISMATCH")
    outcome_index = preparation.role_order.index(matrix.response_role)
    if len(matrix.rows) != len(preparation.complete_rows):
        _fail("MATRIX_PREPARATION_ALIGNMENT_MISMATCH")
    if [row.trade_date for row in matrix.rows] != [
        trade_date for trade_date, _values, _indicator in preparation.complete_rows
    ]:
        _fail("MATRIX_PREPARATION_ALIGNMENT_MISMATCH")
    for row, (_date, _values, indicator) in zip(
        matrix.rows, preparation.complete_rows, strict=True
    ):
        try:
            cell_indicator = int(row.cells[primary_index])
        except (TypeError, ValueError):
            _fail("MATRIX_PREPARATION_ALIGNMENT_MISMATCH")
        if cell_indicator != indicator:
            _fail("MATRIX_PREPARATION_ALIGNMENT_MISMATCH")
    if summary.get("condition_labels") != _CONDITION_LABELS:
        _fail("PLAN_TERM_ROLE_MISMATCH")
    source_roles = summary.get("source_roles")
    if type(source_roles) is not dict:
        _fail("PLAN_TERM_ROLE_MISMATCH")
    if source_roles.get("condition") != PRIMARY_TERM_ROLE:
        _fail("PLAN_TERM_ROLE_MISMATCH")
    if source_roles.get("outcome") != matrix.response_role:
        _fail("PLAN_TERM_ROLE_MISMATCH")
    bindings = evidence.get("statistic_role_bindings")
    if type(bindings) is not dict:
        _fail("MISSING_REQUIRED_STATISTIC_ROLE")
    for role in ("PRIMARY_EFFECT_ESTIMATE", "PRIMARY_EFFECT_CI_LOWER", "PRIMARY_EFFECT_CI_UPPER"):
        if type(bindings.get(role)) is not str or not bindings[role]:
            _fail("MISSING_REQUIRED_STATISTIC_ROLE")
    if primary_role not in bindings["PRIMARY_EFFECT_ESTIMATE"]:
        _fail("MISSING_REQUIRED_STATISTIC_ROLE")

    # X7 -- single deterministic conversion and range gate for cells and response
    rows = tuple(
        tuple(_cell_to_float64(cell) for cell in row.cells) for row in matrix.rows
    )
    response = tuple(
        _cell_to_float64(values[outcome_index]) for _date, values, _indicator in (
            preparation.complete_rows
        )
    )
    (
        enabled,
        bootstrap_method_id,
        replications,
        seed,
        rng,
        confidence,
    ) = _bootstrap_declaration(bootstrap)
    method_configuration = MethodConfigurationV1(
        ARTIFACT_SCHEMA_VERSION,
        EXECUTOR_VERSION,
        ESTIMATOR_CONTRACT_ID,
        MODEL_FAMILY,
        NUMERIC_BACKEND,
        numpy.__version__,
        matrix.response_role,
        tuple(terms),
        terms[primary_index].position,
        primary_role,
        enabled,
        bootstrap_method_id,
        BLOCK_LENGTH_POLICY_ID,
        replications,
        seed,
        rng,
        confidence,
        evidence.get("rule_id") if type(evidence.get("rule_id")) is str else "",
        evidence.get("expected_direction")
        if type(evidence.get("expected_direction")) is str
        else "",
        evidence.get("confidence_requirement")
        if type(evidence.get("confidence_requirement")) is str
        else "",
        quality_word,
        None,
    )
    return _SourceContext(
        _source_chain(matrix),
        _provenance(bound_inputs),
        method_configuration,
        _sample_block(matrix),
        plan,
        design,
        bootstrap,
        robustness,
        _frozen_registry_entries(plan),
        evidence,
        summary,
        tuple(terms),
        primary_index,
        terms[primary_index].position,
        primary_role,
        primary_index,
        tuple(row.cells[primary_index] for row in matrix.rows),
        rows,
        response,
        len(matrix.rows),
        len(terms),
    )


def _estimate(context: _SourceContext) -> EstimatorBlockV1:
    """X8-X10: rank gate, allow-listed OLS, and finite-output validation."""
    design_matrix = numpy.asarray(context.rows, dtype=numpy.float64)
    response = numpy.asarray(context.response, dtype=numpy.float64)
    if design_matrix.shape != (context.n_rows, context.n_terms) or response.shape != (
        context.n_rows,
    ):
        _fail("INVALID_INPUT_STRUCTURE")
    # X8 -- design rank gate (no pseudoinverse, no dropped columns, no minimum-norm fallback)
    if int(numpy.linalg.matrix_rank(design_matrix)) != context.n_terms:
        _fail("SINGULAR_DESIGN")
    # X9 -- allow-listed estimator
    beta, residuals, rank_secondary, singular_values = numpy.linalg.lstsq(
        design_matrix, response, rcond=None
    )
    if int(rank_secondary) != context.n_terms:
        _fail("SINGULAR_DESIGN")
    if len(residuals) not in (0, 1):
        _fail("ESTIMATOR_FAILURE")
    # X10 -- every numeric output must be finite
    beta_values = [float(value) for value in beta]
    singular = [float(value) for value in singular_values]
    residual_sum = None if len(residuals) == 0 else float(residuals[0])
    for value in (*beta_values, *singular):
        if not math.isfinite(value):
            _fail("NON_FINITE_ESTIMATE")
    if residual_sum is not None and not math.isfinite(residual_sum):
        _fail("NON_FINITE_ESTIMATE")
    coefficients = tuple(
        CoefficientV1(
            term.position,
            term.term_role,
            term.coefficient_role,
            _float_value(beta_values[index]),
        )
        for index, term in enumerate(context.terms)
    )
    return EstimatorBlockV1(
        context.n_rows,
        context.n_terms,
        int(rank_secondary),
        coefficients,
        tuple(_float_value(value) for value in singular),
        None if residual_sum is None else _float_value(residual_sum),
        _float_value(beta_values[context.primary_index]),
    )


def _interval_indices(level_text: str, replications: int) -> tuple[Decimal, int, int]:
    """Exact order-statistic indices from exact decimal arithmetic (no library quantiles)."""
    level = Decimal(level_text)
    alpha = (Decimal(1) - level) / Decimal(2)
    count = Decimal(replications)
    low = int((count * alpha).to_integral_value(rounding=ROUND_FLOOR))
    high = int((count * (Decimal(1) - alpha)).to_integral_value(rounding=ROUND_CEILING)) - 1
    low = max(0, min(replications - 1, low))
    high = max(0, min(replications - 1, high))
    if low > high:
        _fail("INVALID_INTERVAL_ORDER")
    return alpha, low, high


def _bootstrap(
    context: _SourceContext,
) -> tuple[BootstrapBlockV1, Float64ValueV1 | None, Float64ValueV1 | None]:
    """X11-X13: preconditions, frozen resampling, exact endpoints."""
    bootstrap = context.bootstrap_plan
    enabled, method_id, replications, seed, rng, confidence = _bootstrap_declaration(bootstrap)
    # X11 -- bootstrap preconditions; enabled is the only dispatch switch and only the plan sets it
    if enabled:
        if method_id not in ALLOWED_BOOTSTRAP_METHODS:
            _fail("UNSUPPORTED_BOOTSTRAP_METHOD")
        if rng not in ALLOWED_BOOTSTRAP_RNGS:
            _fail("UNSUPPORTED_BOOTSTRAP_RNG")
        if replications < BOOTSTRAP_MIN_REPLICATIONS:
            _fail("INSUFFICIENT_REPLICATIONS")
    elif method_id != DISABLED_BOOTSTRAP_METHOD:
        _fail("INVALID_INPUT_STRUCTURE", "disabled bootstrap must declare DISABLED")
    if not enabled:
        return (
            BootstrapBlockV1(
                False,
                DISABLED_BOOTSTRAP_METHOD,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
            ),
            None,
            None,
        )
    n_rows = context.n_rows
    block_length = _block_length(n_rows)
    if block_length > n_rows:
        _fail("BLOCK_LENGTH_EXCEEDS_ROWS")
    design_matrix = numpy.asarray(context.rows, dtype=numpy.float64)
    response = numpy.asarray(context.response, dtype=numpy.float64)
    # X12 -- one generator per execution, one draw per replication in ascending order
    generator = numpy.random.Generator(numpy.random.PCG64(seed))
    block_count = (n_rows + block_length - 1) // block_length
    samples: list[float] = []
    for _ in range(replications):
        starts = generator.integers(
            0, n_rows - block_length + 1, size=block_count, endpoint=False
        )
        index = numpy.concatenate(
            [numpy.arange(int(start), int(start) + block_length) for start in starts]
        )[:n_rows]
        resampled_design = design_matrix[index]
        resampled_response = response[index]
        if int(numpy.linalg.matrix_rank(resampled_design)) != context.n_terms:
            _fail("SINGULAR_RESAMPLE")
        beta, residuals, rank_secondary, _singular = numpy.linalg.lstsq(
            resampled_design, resampled_response, rcond=None
        )
        if int(rank_secondary) != context.n_terms:
            _fail("SINGULAR_RESAMPLE")
        if len(residuals) not in (0, 1):
            _fail("BOOTSTRAP_FAILURE")
        value = float(beta[context.primary_index])
        if not math.isfinite(value):
            _fail("NON_FINITE_ESTIMATE")
        samples.append(value)
    # X13 -- exact order statistics, strict endpoint order
    alpha, lower_index, upper_index = _interval_indices(confidence, replications)
    ordered = sorted(samples)
    lower = ordered[lower_index]
    upper = ordered[upper_index]
    if lower > upper:
        _fail("INVALID_INTERVAL_ORDER")
    return (
        BootstrapBlockV1(
            True,
            method_id,
            block_length,
            replications,
            seed,
            rng,
            confidence,
            canonical_decimal(alpha),
            lower_index,
            upper_index,
            _float_value(lower),
            _float_value(upper),
        ),
        _float_value(lower),
        _float_value(upper),
    )


def _mean(values: list[float]) -> float | None:
    """Left-to-right float64 accumulation in row order (never pairwise/BLAS summation)."""
    if not values:
        return None
    total = 0.0
    for value in values:
        total += value
    return total / len(values)


def _median(values: list[float]) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[middle]
    return (ordered[middle - 1] + ordered[middle]) / 2.0


def _difference(left: float | None, right: float | None) -> float | None:
    if left is None or right is None:
        return None
    return left - right


def _conditional_descriptives(context: _SourceContext) -> tuple[StatisticValueV1, ...]:
    """X14 -- strict indicator coding, exact role set/order, frozen mean/median rules."""
    # X14 -- condition coding, exact role set/order, frozen mean/median rules
    indicators: list[int] = []
    for text in context.indicator_cells:
        if text not in ("0", "1"):
            _fail("INVALID_CONDITION_INDICATOR")
        indicators.append(int(text))
    condition_rows = [
        value for value, flag in zip(context.response, indicators, strict=True) if flag == 1
    ]
    ordinary_rows = [
        value for value, flag in zip(context.response, indicators, strict=True) if flag == 0
    ]
    if len(condition_rows) + len(ordinary_rows) != context.n_rows:
        _fail("INVALID_CONDITION_INDICATOR")
    condition_mean = _mean(condition_rows)
    ordinary_mean = _mean(ordinary_rows)
    condition_median = _median(condition_rows)
    ordinary_median = _median(ordinary_rows)
    computed: dict[str, tuple[str, int | None, float | None]] = {
        "CONDITION_COUNT": ("COUNT", len(condition_rows), None),
        "ORDINARY_COUNT": ("COUNT", len(ordinary_rows), None),
        "CONDITION_MEAN": ("MEAN", None, condition_mean),
        "ORDINARY_MEAN": ("MEAN", None, ordinary_mean),
        "CONDITION_MEDIAN": ("MEDIAN", None, condition_median),
        "ORDINARY_MEDIAN": ("MEDIAN", None, ordinary_median),
        "CONDITION_MINUS_ORDINARY_MEAN": (
            "DIFFERENCE",
            None,
            _difference(condition_mean, ordinary_mean),
        ),
        "CONDITION_MINUS_ORDINARY_MEDIAN": (
            "DIFFERENCE",
            None,
            _difference(condition_median, ordinary_median),
        ),
    }
    required = context.summary_plan.get("required_statistic_roles")
    if type(required) is not list or not required:
        _fail("MISSING_REQUIRED_STATISTIC_ROLE")
    values: list[StatisticValueV1] = []
    for role in required:
        if type(role) is not str or role not in computed:
            _fail("MISSING_REQUIRED_STATISTIC_ROLE")
        kind, count, value = computed[role]
        values.append(
            StatisticValueV1(role, kind, count, None if value is None else _float_value(value))
        )
    if [entry.role for entry in values] != [role for role in required]:
        _fail("MISSING_REQUIRED_STATISTIC_ROLE")
    evidence_roles = context.evidence_plan.get("required_statistic_roles")
    if type(evidence_roles) is not list or list(evidence_roles) != list(
        REQUIRED_EVIDENCE_STATISTIC_ROLES
    ):
        _fail("MISSING_REQUIRED_STATISTIC_ROLE")
    return tuple(values)


def _disposition(
    direction: str, requirement: str, level: str, enabled: bool, lower: float, upper: float
) -> tuple[str, str]:
    """The frozen D2-D10 precedence table with strict, tolerance-free zero comparisons."""
    if enabled is False:
        return "INCONCLUSIVE", "BOOTSTRAP_DISABLED"
    if Decimal(level) < Decimal(requirement):
        return "INCONCLUSIVE", "CONFIDENCE_BELOW_REQUIREMENT"
    if direction == "POSITIVE":
        if lower > 0:
            return "POSITIVE_SUPPORTED", "INTERVAL_ABOVE_ZERO"
        return "NOT_SUPPORTED", "INTERVAL_INCLUDES_ZERO"
    if direction == "NEGATIVE":
        if upper < 0:
            return "NEGATIVE_SUPPORTED", "INTERVAL_BELOW_ZERO"
        return "NOT_SUPPORTED", "INTERVAL_INCLUDES_ZERO"
    if lower > 0:
        return "TWO_SIDED_SUPPORTED", "INTERVAL_ABOVE_ZERO"
    if upper < 0:
        return "TWO_SIDED_SUPPORTED", "INTERVAL_BELOW_ZERO"
    return "NOT_SUPPORTED", "INTERVAL_INCLUDES_ZERO"


def _evidence_block(
    context: _SourceContext,
    estimator: EstimatorBlockV1,
    bootstrap: BootstrapBlockV1,
) -> EvidenceBlockV1:
    """X15 -- direction allow-list, frozen precedence table, explicit coverage fact."""
    # X15 -- direction allow-list and the frozen D2-D10 precedence table
    evidence = context.evidence_plan
    direction = evidence.get("expected_direction")
    if direction not in EVIDENCE_DIRECTIONS:
        _fail("UNSUPPORTED_EVIDENCE_DIRECTION")
    requirement = evidence.get("confidence_requirement")
    if not _canonical_decimal_text(requirement, "0", "1"):
        _fail("INVALID_INPUT_STRUCTURE")
    quality_word = evidence.get("data_quality_failure_disposition")
    if quality_word not in FAILURE_DISPOSITIONS:
        _fail("INVALID_INPUT_STRUCTURE")
    rule_id = evidence.get("rule_id")
    if not _identifier_text(rule_id):
        _fail("INVALID_INPUT_STRUCTURE")
    declared_level = context.method_configuration.bootstrap_confidence_level
    satisfied = Decimal(declared_level) >= Decimal(requirement)
    if bootstrap.enabled:
        if (
            bootstrap.primary_effect_lower is None
            or bootstrap.primary_effect_upper is None
            or bootstrap.confidence_level is None
        ):
            _fail("INVALID_INPUT_STRUCTURE")
        lower_value = float.fromhex(bootstrap.primary_effect_lower.float64_hex)
        upper_value = float.fromhex(bootstrap.primary_effect_upper.float64_hex)
        disposition, reason = _disposition(
            direction, requirement, bootstrap.confidence_level, True, lower_value, upper_value
        )
    else:
        disposition, reason = _disposition(direction, requirement, declared_level, False, 0.0, 0.0)
    return EvidenceBlockV1(
        rule_id,
        direction,
        requirement,
        quality_word,
        bootstrap.confidence_level,
        satisfied,
        context.primary_role,
        estimator.primary_effect,
        bootstrap.primary_effect_lower,
        bootstrap.primary_effect_upper,
        disposition,
        reason,
        context.sample.coverage_complete,
        INTERPRETATION_BOUNDARY,
    )


def _check_source_chain(source_chain: Any) -> None:
    if type(source_chain) is not SourceChainV1:
        _fail("INVALID_INPUT_STRUCTURE")
    for name in (
        "contract_digest",
        "plan_digest",
        "input_digest",
        "domain_digest",
        "dataset_digest",
        "matrix_digest",
    ):
        value = getattr(source_chain, name)
        if type(value) is not str or _HASH_RE.fullmatch(value) is None:
            _fail("INVALID_INPUT_STRUCTURE")


def _check_provenance(provenance: Any) -> None:
    if type(provenance) is not ProvenanceV1:
        _fail("INVALID_INPUT_STRUCTURE")
    if provenance.provenance_class != PROVENANCE_CLASS:
        _fail("INVALID_INPUT_STRUCTURE")
    if provenance.synthetic_test_only is not True:
        _fail("INVALID_INPUT_STRUCTURE")
    if provenance.dataset_mode != SYNTHETIC_DATASET_MODE:
        _fail("INVALID_INPUT_STRUCTURE")
    if provenance.real_data_used is not False or provenance.holdout_accessed is not False:
        _fail("INVALID_INPUT_STRUCTURE")


def _check_method_configuration(method: Any) -> None:
    if type(method) is not MethodConfigurationV1:
        _fail("INVALID_INPUT_STRUCTURE")
    if method.artifact_schema_version != ARTIFACT_SCHEMA_VERSION:
        _fail("INVALID_INPUT_STRUCTURE")
    if method.executor_version != EXECUTOR_VERSION:
        _fail("INVALID_INPUT_STRUCTURE")
    if method.estimator_contract_id != ESTIMATOR_CONTRACT_ID:
        _fail("INVALID_INPUT_STRUCTURE")
    if method.model_family != MODEL_FAMILY or method.numeric_backend != NUMERIC_BACKEND:
        _fail("INVALID_INPUT_STRUCTURE")
    if type(method.numeric_runtime) is not str or not method.numeric_runtime:
        _fail("INVALID_INPUT_STRUCTURE")
    if type(method.response_role) is not str or not method.response_role:
        _fail("INVALID_INPUT_STRUCTURE")
    if type(method.terms) is not tuple or not method.terms:
        _fail("INVALID_INPUT_STRUCTURE")
    for position, term in enumerate(method.terms, 1):
        if type(term) is not TermRefV1:
            _fail("INVALID_INPUT_STRUCTURE")
        if term.position != position or not _identifier_text(term.term_role):
            _fail("INVALID_INPUT_STRUCTURE")
        if type(term.coefficient_role) is not str or not term.coefficient_role:
            _fail("INVALID_INPUT_STRUCTURE")
    condition_terms = [t for t in method.terms if t.term_role == PRIMARY_TERM_ROLE]
    intercept_terms = [t for t in method.terms if t.term_role == INTERCEPT_TERM_ROLE]
    if len(condition_terms) != 1 or len(intercept_terms) != 1:
        _fail("INVALID_INPUT_STRUCTURE")
    if method.primary_effect_position != condition_terms[0].position:
        _fail("INVALID_INPUT_STRUCTURE")
    if method.primary_effect_role != condition_terms[0].coefficient_role:
        _fail("INVALID_INPUT_STRUCTURE")
    if type(method.bootstrap_enabled) is not bool:
        _fail("INVALID_INPUT_STRUCTURE")
    if method.block_length_policy_id != BLOCK_LENGTH_POLICY_ID:
        _fail("INVALID_INPUT_STRUCTURE")
    if not _identifier_text(method.bootstrap_method_id):
        _fail("INVALID_INPUT_STRUCTURE")
    if type(method.bootstrap_replications) is not int or method.bootstrap_replications <= 0:
        _fail("INVALID_INPUT_STRUCTURE")
    if type(method.bootstrap_seed) is not int:
        _fail("INVALID_INPUT_STRUCTURE")
    if not _identifier_text(method.bootstrap_rng):
        _fail("INVALID_INPUT_STRUCTURE")
    if not _canonical_decimal_text(method.bootstrap_confidence_level, "0", "1"):
        _fail("INVALID_INPUT_STRUCTURE")
    if not _identifier_text(method.evidence_rule_id):
        _fail("INVALID_INPUT_STRUCTURE")
    if method.evidence_direction not in EVIDENCE_DIRECTIONS:
        _fail("INVALID_INPUT_STRUCTURE")
    if not _canonical_decimal_text(method.evidence_confidence_requirement, "0", "1"):
        _fail("INVALID_INPUT_STRUCTURE")
    if method.data_quality_failure_disposition not in FAILURE_DISPOSITIONS:
        _fail("INVALID_INPUT_STRUCTURE")
    if method.block_length is not None and (
        type(method.block_length) is not int or method.block_length <= 0
    ):
        _fail("INVALID_INPUT_STRUCTURE")


def _check_sample(sample: Any) -> None:
    if type(sample) is not SampleBlockV1:
        _fail("INVALID_INPUT_STRUCTURE")
    if type(sample.row_count) is not int or sample.row_count <= 0:
        _fail("INVALID_INPUT_STRUCTURE")
    if type(sample.trade_dates) is not tuple or len(sample.trade_dates) != sample.row_count:
        _fail("INVALID_INPUT_STRUCTURE")
    if list(sample.trade_dates) != sorted(set(sample.trade_dates)):
        _fail("INVALID_INPUT_STRUCTURE")
    if type(sample.coverage_numerator) is not int or type(sample.coverage_denominator) is not int:
        _fail("INVALID_INPUT_STRUCTURE")
    if not 0 <= sample.coverage_numerator <= sample.coverage_denominator:
        _fail("INVALID_INPUT_STRUCTURE")
    if sample.coverage_denominator <= 0 or sample.coverage_numerator < sample.row_count:
        _fail("INVALID_INPUT_STRUCTURE")
    if not _canonical_decimal_text(sample.coverage_gate, "-1", "1"):
        _fail("INVALID_INPUT_STRUCTURE")
    if sample.coverage_gate_satisfied is not _coverage_ge(
        sample.coverage_numerator, sample.coverage_denominator, sample.coverage_gate
    ):
        _fail("INVALID_INPUT_STRUCTURE")
    if sample.coverage_complete is not (
        sample.coverage_numerator == sample.coverage_denominator
    ):
        _fail("INVALID_INPUT_STRUCTURE")
    if sample.missingness_policy not in MISSINGNESS_POLICIES:
        _fail("INVALID_INPUT_STRUCTURE")
    if sample.failure_disposition not in FAILURE_DISPOSITIONS:
        _fail("INVALID_INPUT_STRUCTURE")
    if type(sample.reason_counts) is not tuple:
        _fail("INVALID_INPUT_STRUCTURE")
    keys = [key for key, _ in sample.reason_counts]
    if keys != sorted(set(keys)):
        _fail("INVALID_INPUT_STRUCTURE")
    if list(sample.rejected_dates) != sorted(set(sample.rejected_dates)):
        _fail("INVALID_INPUT_STRUCTURE")


def _check_estimator(estimator: Any, sample: SampleBlockV1, method: MethodConfigurationV1) -> None:
    if type(estimator) is not EstimatorBlockV1:
        _fail("INVALID_INPUT_STRUCTURE")
    if estimator.n_rows != sample.row_count or estimator.n_terms != len(method.terms):
        _fail("INVALID_INPUT_STRUCTURE")
    if type(estimator.rank) is not int or estimator.rank != estimator.n_terms:
        _fail("INVALID_INPUT_STRUCTURE")
    if type(estimator.coefficients) is not tuple:
        _fail("INVALID_INPUT_STRUCTURE")
    if len(estimator.coefficients) != estimator.n_terms:
        _fail("INVALID_INPUT_STRUCTURE")
    for term, coefficient in zip(method.terms, estimator.coefficients, strict=True):
        if type(coefficient) is not CoefficientV1:
            _fail("INVALID_INPUT_STRUCTURE")
        if (coefficient.position, coefficient.term_role, coefficient.coefficient_role) != (
            term.position,
            term.term_role,
            term.coefficient_role,
        ):
            _fail("INVALID_INPUT_STRUCTURE")
        _check_float_value(coefficient.value)
    if type(estimator.singular_values) is not tuple:
        _fail("INVALID_INPUT_STRUCTURE")
    if len(estimator.singular_values) != estimator.n_terms:
        _fail("INVALID_INPUT_STRUCTURE")
    for value in estimator.singular_values:
        _check_float_value(value)
    if estimator.residual_sum_of_squares is not None:
        _check_float_value(estimator.residual_sum_of_squares)
    if (estimator.residual_sum_of_squares is None) is not (estimator.n_rows == estimator.n_terms):
        _fail("INVALID_INPUT_STRUCTURE")
    _check_float_value(estimator.primary_effect)
    if estimator.primary_effect != estimator.coefficients[
        method.primary_effect_position - 1
    ].value:
        _fail("INVALID_INPUT_STRUCTURE")


def _check_bootstrap(
    bootstrap: Any, estimator: EstimatorBlockV1, method: MethodConfigurationV1 | None = None
) -> None:
    if type(bootstrap) is not BootstrapBlockV1:
        _fail("INVALID_INPUT_STRUCTURE")
    if type(bootstrap.enabled) is not bool:
        _fail("INVALID_INPUT_STRUCTURE")
    method_fields = (
        bootstrap.block_length,
        bootstrap.replications,
        bootstrap.seed,
        bootstrap.rng,
        bootstrap.confidence_level,
        bootstrap.interval_alpha,
        bootstrap.lower_index,
        bootstrap.upper_index,
        bootstrap.primary_effect_lower,
        bootstrap.primary_effect_upper,
    )
    if bootstrap.enabled:
        if not _identifier_text(bootstrap.method_id):
            _fail("INVALID_INPUT_STRUCTURE")
        if any(value is None for value in method_fields):
            _fail("INVALID_INPUT_STRUCTURE")
        if type(bootstrap.block_length) is not int or bootstrap.block_length <= 0:
            _fail("INVALID_INPUT_STRUCTURE")
        if type(bootstrap.replications) is not int or bootstrap.replications < (
            BOOTSTRAP_MIN_REPLICATIONS
        ):
            _fail("INVALID_INPUT_STRUCTURE")
        if type(bootstrap.seed) is not int or type(bootstrap.rng) is not str:
            _fail("INVALID_INPUT_STRUCTURE")
        if not _canonical_decimal_text(bootstrap.confidence_level, "0", "1"):
            _fail("INVALID_INPUT_STRUCTURE")
        if not _canonical_decimal_text(bootstrap.interval_alpha, "0", "1"):
            _fail("INVALID_INPUT_STRUCTURE")
        if type(bootstrap.lower_index) is not int or type(bootstrap.upper_index) is not int:
            _fail("INVALID_INPUT_STRUCTURE")
        if not 0 <= bootstrap.lower_index <= bootstrap.upper_index < bootstrap.replications:
            _fail("INVALID_INPUT_STRUCTURE")
        _check_float_value(bootstrap.primary_effect_lower)
        _check_float_value(bootstrap.primary_effect_upper)
        lower = float.fromhex(bootstrap.primary_effect_lower.float64_hex)
        upper = float.fromhex(bootstrap.primary_effect_upper.float64_hex)
        if lower > upper:
            _fail("INVALID_INTERVAL_ORDER")
        # Declaration and execution must not fork (design 7.1): the artifact's method facts are
        # the plan's facts, not re-derived values.
        if method is not None and (
            bootstrap.method_id != method.bootstrap_method_id
            or bootstrap.replications != method.bootstrap_replications
            or bootstrap.seed != method.bootstrap_seed
            or bootstrap.rng != method.bootstrap_rng
            or bootstrap.confidence_level != method.bootstrap_confidence_level
        ):
            _fail("INVALID_INPUT_STRUCTURE")
    else:
        if bootstrap.method_id != DISABLED_BOOTSTRAP_METHOD:
            _fail("INVALID_INPUT_STRUCTURE")
        if any(value is not None for value in method_fields):
            _fail("INVALID_INPUT_STRUCTURE")
    if type(estimator) is not EstimatorBlockV1:
        _fail("INVALID_INPUT_STRUCTURE")


def _check_descriptives(values: Any) -> None:
    if type(values) is not tuple or not values:
        _fail("INVALID_INPUT_STRUCTURE")
    roles: list[str] = []
    for value in values:
        if type(value) is not StatisticValueV1:
            _fail("INVALID_INPUT_STRUCTURE")
        if type(value.role) is not str or not value.role:
            _fail("INVALID_INPUT_STRUCTURE")
        roles.append(value.role)
        if value.kind not in ("COUNT", "MEAN", "MEDIAN", "DIFFERENCE"):
            _fail("INVALID_INPUT_STRUCTURE")
        if value.kind == "COUNT":
            if type(value.count) is not int or value.value is not None:
                _fail("INVALID_INPUT_STRUCTURE")
        elif value.count is not None:
            _fail("INVALID_INPUT_STRUCTURE")
        if value.value is not None:
            _check_float_value(value.value)
    if len(set(roles)) != len(roles):
        _fail("INVALID_INPUT_STRUCTURE")


def _check_evidence(
    evidence: Any,
    estimator: EstimatorBlockV1,
    bootstrap: BootstrapBlockV1,
    sample: SampleBlockV1,
    method: MethodConfigurationV1,
) -> None:
    if type(evidence) is not EvidenceBlockV1:
        _fail("INVALID_INPUT_STRUCTURE")
    if not _identifier_text(evidence.rule_id):
        _fail("INVALID_INPUT_STRUCTURE")
    if evidence.expected_direction not in EVIDENCE_DIRECTIONS:
        _fail("INVALID_INPUT_STRUCTURE")
    if not _canonical_decimal_text(evidence.confidence_requirement, "0", "1"):
        _fail("INVALID_INPUT_STRUCTURE")
    if evidence.data_quality_failure_disposition not in FAILURE_DISPOSITIONS:
        _fail("INVALID_INPUT_STRUCTURE")
    if evidence.bootstrap_confidence_level is not None and not _canonical_decimal_text(
        evidence.bootstrap_confidence_level, "0", "1"
    ):
        _fail("INVALID_INPUT_STRUCTURE")
    if evidence.bootstrap_confidence_level != bootstrap.confidence_level:
        _fail("INVALID_INPUT_STRUCTURE")
    if type(evidence.confidence_requirement_satisfied) is not bool:
        _fail("INVALID_INPUT_STRUCTURE")
    satisfied = Decimal(method.bootstrap_confidence_level) >= Decimal(
        evidence.confidence_requirement
    )
    if evidence.confidence_requirement_satisfied is not satisfied:
        _fail("INVALID_INPUT_STRUCTURE")
    if evidence.primary_effect_role != method.primary_effect_role:
        _fail("INVALID_INPUT_STRUCTURE")
    _check_float_value(evidence.primary_effect)
    if evidence.primary_effect != estimator.primary_effect:
        _fail("INVALID_INPUT_STRUCTURE")
    for value in (evidence.interval_lower, evidence.interval_upper):
        if value is not None:
            _check_float_value(value)
    if evidence.interval_lower != bootstrap.primary_effect_lower:
        _fail("INVALID_INPUT_STRUCTURE")
    if evidence.interval_upper != bootstrap.primary_effect_upper:
        _fail("INVALID_INPUT_STRUCTURE")
    if evidence.disposition not in DISPOSITIONS:
        _fail("INVALID_INPUT_STRUCTURE")
    if evidence.disposition_reason not in REASONS:
        _fail("INVALID_INPUT_STRUCTURE")
    if type(evidence.coverage_complete) is not bool:
        _fail("INVALID_INPUT_STRUCTURE")
    if evidence.coverage_complete is not sample.coverage_complete:
        _fail("INVALID_INPUT_STRUCTURE")
    if evidence.interpretation_boundary != INTERPRETATION_BOUNDARY:
        _fail("INVALID_INPUT_STRUCTURE")


def _method_configuration_payload(method: MethodConfigurationV1) -> dict:
    return {
        "artifact_schema_version": method.artifact_schema_version,
        "executor_version": method.executor_version,
        "estimator_contract_id": method.estimator_contract_id,
        "model_family": method.model_family,
        "numeric_backend": method.numeric_backend,
        "numeric_runtime": method.numeric_runtime,
        "response_role": method.response_role,
        "terms": [
            {
                "position": term.position,
                "term_role": term.term_role,
                "coefficient_role": term.coefficient_role,
            }
            for term in method.terms
        ],
        "primary_effect_position": method.primary_effect_position,
        "primary_effect_role": method.primary_effect_role,
        "bootstrap_enabled": method.bootstrap_enabled,
        "bootstrap_method_id": method.bootstrap_method_id,
        "block_length_policy_id": method.block_length_policy_id,
        "bootstrap_replications": method.bootstrap_replications,
        "bootstrap_seed": method.bootstrap_seed,
        "bootstrap_rng": method.bootstrap_rng,
        "bootstrap_confidence_level": method.bootstrap_confidence_level,
        "evidence_rule_id": method.evidence_rule_id,
        "evidence_direction": method.evidence_direction,
        "evidence_confidence_requirement": method.evidence_confidence_requirement,
        "data_quality_failure_disposition": method.data_quality_failure_disposition,
        "block_length": method.block_length,
    }


def _float_payload(value: Float64ValueV1 | None) -> dict | None:
    if value is None:
        return None
    return {"float64_hex": value.float64_hex, "canonical_decimal": value.canonical_decimal}


def _execution_payload(artifact: ExecutionArtifactV1) -> dict:
    """Independent canonical payload without ``artifact_digest`` (the digest input)."""
    method = artifact.method_configuration
    sample = artifact.sample
    estimator = artifact.estimator
    bootstrap = artifact.bootstrap
    evidence = artifact.evidence
    return {
        "artifact_schema_version": artifact.artifact_schema_version,
        "executor_version": artifact.executor_version,
        "source_chain": {
            "contract_digest": artifact.source_chain.contract_digest,
            "plan_digest": artifact.source_chain.plan_digest,
            "input_digest": artifact.source_chain.input_digest,
            "domain_digest": artifact.source_chain.domain_digest,
            "dataset_digest": artifact.source_chain.dataset_digest,
            "matrix_digest": artifact.source_chain.matrix_digest,
        },
        "provenance": {
            "provenance_class": artifact.provenance.provenance_class,
            "synthetic_test_only": artifact.provenance.synthetic_test_only,
            "dataset_mode": artifact.provenance.dataset_mode,
            "real_data_used": artifact.provenance.real_data_used,
            "holdout_accessed": artifact.provenance.holdout_accessed,
        },
        "method_configuration": _method_configuration_payload(method),
        "sample": {
            "row_count": sample.row_count,
            "trade_dates": list(sample.trade_dates),
            "coverage_numerator": sample.coverage_numerator,
            "coverage_denominator": sample.coverage_denominator,
            "coverage_gate": sample.coverage_gate,
            "coverage_gate_satisfied": sample.coverage_gate_satisfied,
            "coverage_complete": sample.coverage_complete,
            "missingness_policy": sample.missingness_policy,
            "failure_disposition": sample.failure_disposition,
            "reason_counts": {key: count for key, count in sample.reason_counts},
            "rejected_dates": list(sample.rejected_dates),
        },
        "estimator": {
            "n_rows": estimator.n_rows,
            "n_terms": estimator.n_terms,
            "rank": estimator.rank,
            "coefficients": [
                {
                    "position": coefficient.position,
                    "term_role": coefficient.term_role,
                    "coefficient_role": coefficient.coefficient_role,
                    "value": _float_payload(coefficient.value),
                }
                for coefficient in estimator.coefficients
            ],
            "singular_values": [
                _float_payload(value) for value in estimator.singular_values
            ],
            "residual_sum_of_squares": _float_payload(estimator.residual_sum_of_squares),
            "primary_effect": _float_payload(estimator.primary_effect),
        },
        "bootstrap": {
            "enabled": bootstrap.enabled,
            "method_id": bootstrap.method_id,
            "block_length": bootstrap.block_length,
            "replications": bootstrap.replications,
            "seed": bootstrap.seed,
            "rng": bootstrap.rng,
            "confidence_level": bootstrap.confidence_level,
            "interval_alpha": bootstrap.interval_alpha,
            "lower_index": bootstrap.lower_index,
            "upper_index": bootstrap.upper_index,
            "primary_effect_lower": _float_payload(bootstrap.primary_effect_lower),
            "primary_effect_upper": _float_payload(bootstrap.primary_effect_upper),
        },
        "conditional_descriptives": [
            {
                "role": value.role,
                "kind": value.kind,
                "count": value.count,
                "value": _float_payload(value.value),
            }
            for value in artifact.conditional_descriptives
        ],
        "evidence": {
            "rule_id": evidence.rule_id,
            "expected_direction": evidence.expected_direction,
            "confidence_requirement": evidence.confidence_requirement,
            "data_quality_failure_disposition": evidence.data_quality_failure_disposition,
            "bootstrap_confidence_level": evidence.bootstrap_confidence_level,
            "confidence_requirement_satisfied": evidence.confidence_requirement_satisfied,
            "primary_effect_role": evidence.primary_effect_role,
            "primary_effect": _float_payload(evidence.primary_effect),
            "interval_lower": _float_payload(evidence.interval_lower),
            "interval_upper": _float_payload(evidence.interval_upper),
            "disposition": evidence.disposition,
            "disposition_reason": evidence.disposition_reason,
            "coverage_complete": evidence.coverage_complete,
            "interpretation_boundary": evidence.interpretation_boundary,
        },
        "execution_authorized": artifact.execution_authorized,
        "statistics_computed": artifact.statistics_computed,
        "outcome_read": artifact.outcome_read,
    }


def _parameters_canonical_json(parameters: FrozenJSONObject) -> str:
    return json.dumps(
        _thaw_json(parameters), ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )


def _robustness_payload(artifact: RobustnessArtifactV1) -> dict:
    """Independent canonical payload without ``artifact_digest`` (the digest input)."""
    method = artifact.method_configuration
    sample = artifact.sample
    return {
        "artifact_schema_version": artifact.artifact_schema_version,
        "executor_version": artifact.executor_version,
        "source_chain": {
            "contract_digest": artifact.source_chain.contract_digest,
            "plan_digest": artifact.source_chain.plan_digest,
            "input_digest": artifact.source_chain.input_digest,
            "domain_digest": artifact.source_chain.domain_digest,
            "dataset_digest": artifact.source_chain.dataset_digest,
            "matrix_digest": artifact.source_chain.matrix_digest,
        },
        "provenance": {
            "provenance_class": artifact.provenance.provenance_class,
            "synthetic_test_only": artifact.provenance.synthetic_test_only,
            "dataset_mode": artifact.provenance.dataset_mode,
            "real_data_used": artifact.provenance.real_data_used,
            "holdout_accessed": artifact.provenance.holdout_accessed,
        },
        "method_configuration": _method_configuration_payload(method),
        "sample": {
            "row_count": sample.row_count,
            "trade_dates": list(sample.trade_dates),
            "coverage_numerator": sample.coverage_numerator,
            "coverage_denominator": sample.coverage_denominator,
            "coverage_gate": sample.coverage_gate,
            "coverage_gate_satisfied": sample.coverage_gate_satisfied,
            "coverage_complete": sample.coverage_complete,
            "missingness_policy": sample.missingness_policy,
            "failure_disposition": sample.failure_disposition,
            "reason_counts": {key: count for key, count in sample.reason_counts},
            "rejected_dates": list(sample.rejected_dates),
        },
        "dispatch": {
            "requested_ids": list(artifact.dispatch.requested_ids),
            "registered_ids": list(artifact.dispatch.registered_ids),
            "automatic_expansion": artifact.dispatch.automatic_expansion,
            "automatic_selection": artifact.dispatch.automatic_selection,
            "parameters_interpreted": artifact.dispatch.parameters_interpreted,
        },
        "entries": [
            {
                "robustness_id": entry.robustness_id,
                "request_ordinal": entry.request_ordinal,
                "registration_ordinal": entry.registration_ordinal,
                "method_id": entry.method_id,
                "parameters": _thaw_json(entry.parameters),
                "parameters_canonical_json": entry.parameters_canonical_json,
            }
            for entry in artifact.entries
        ],
        "execution_authorized": artifact.execution_authorized,
        "statistics_computed": artifact.statistics_computed,
        "outcome_read": artifact.outcome_read,
    }


def _check_forbidden_content(payload: Any) -> None:
    """Reject host/path/session keys, selection/aggregation keys and absolute-path values."""
    if type(payload) is dict:
        for key, value in payload.items():
            if type(key) is not str or key.lower() in FORBIDDEN_KEYS:
                _fail("FORBIDDEN_ARTIFACT_CONTENT")
            _check_forbidden_content(value)
        return
    if type(payload) is list:
        for item in payload:
            _check_forbidden_content(item)
        return
    if type(payload) is str and _ABSOLUTE_PATH_RE.search(payload) is not None:
        _fail("FORBIDDEN_ARTIFACT_CONTENT")


def _check_execution_artifact(artifact: ExecutionArtifactV1) -> None:
    """V1 -- artifact structure, every internal invariant, content rules and self digest."""
    _shape(artifact, ExecutionArtifactV1)
    if artifact.artifact_schema_version != ARTIFACT_SCHEMA_VERSION:
        _fail("INVALID_INPUT_STRUCTURE")
    if artifact.executor_version != EXECUTOR_VERSION:
        _fail("INVALID_INPUT_STRUCTURE")
    if artifact.execution_authorized is not False:
        _fail("INVALID_INPUT_STRUCTURE")
    if artifact.statistics_computed is not True or artifact.outcome_read is not True:
        _fail("INVALID_INPUT_STRUCTURE")
    _check_source_chain(artifact.source_chain)
    _check_provenance(artifact.provenance)
    _check_method_configuration(artifact.method_configuration)
    _check_sample(artifact.sample)
    _check_estimator(artifact.estimator, artifact.sample, artifact.method_configuration)
    _check_bootstrap(artifact.bootstrap, artifact.estimator, artifact.method_configuration)
    _check_descriptives(artifact.conditional_descriptives)
    _check_evidence(
        artifact.evidence,
        artifact.estimator,
        artifact.bootstrap,
        artifact.sample,
        artifact.method_configuration,
    )
    payload = _execution_payload(artifact)
    if canonical_digest(payload) != artifact.artifact_digest:
        _fail("ARTIFACT_DIGEST_MISMATCH")
    _check_forbidden_content(payload)


def _check_robustness_artifact(artifact: RobustnessArtifactV1) -> None:
    """V1 -- dispatch artifact structure, invariants, content rules and self digest."""
    _shape(artifact, RobustnessArtifactV1)
    if artifact.artifact_schema_version != ROBUSTNESS_ARTIFACT_SCHEMA_VERSION:
        _fail("INVALID_INPUT_STRUCTURE")
    if artifact.executor_version != EXECUTOR_VERSION:
        _fail("INVALID_INPUT_STRUCTURE")
    if artifact.execution_authorized is not False:
        _fail("INVALID_INPUT_STRUCTURE")
    if artifact.statistics_computed is not False or artifact.outcome_read is not False:
        _fail("INVALID_INPUT_STRUCTURE")
    _check_source_chain(artifact.source_chain)
    _check_provenance(artifact.provenance)
    _check_method_configuration(artifact.method_configuration)
    _check_sample(artifact.sample)
    dispatch = artifact.dispatch
    if type(dispatch) is not RobustnessDispatchV1:
        _fail("INVALID_INPUT_STRUCTURE")
    if type(dispatch.requested_ids) is not tuple or not dispatch.requested_ids:
        _fail("INVALID_INPUT_STRUCTURE")
    if list(dispatch.requested_ids) != list(dict.fromkeys(dispatch.requested_ids)):
        _fail("INVALID_INPUT_STRUCTURE")
    if type(dispatch.registered_ids) is not tuple:
        _fail("INVALID_INPUT_STRUCTURE")
    if any(
        type(identifier) is not str
        for identifier in (*dispatch.requested_ids, *dispatch.registered_ids)
    ):
        _fail("INVALID_INPUT_STRUCTURE")
    if list(dispatch.registered_ids) != list(dict.fromkeys(dispatch.registered_ids)):
        _fail("INVALID_INPUT_STRUCTURE")
    if any(identifier not in dispatch.registered_ids for identifier in dispatch.requested_ids):
        _fail("INVALID_INPUT_STRUCTURE")
    if (
        dispatch.automatic_expansion is not False
        or dispatch.automatic_selection is not False
        or dispatch.parameters_interpreted is not False
    ):
        _fail("INVALID_INPUT_STRUCTURE")
    if type(artifact.entries) is not tuple or len(artifact.entries) != len(
        dispatch.requested_ids
    ):
        _fail("INVALID_INPUT_STRUCTURE")
    for ordinal, entry in enumerate(artifact.entries):
        if type(entry) is not RobustnessEntryDispatchV1:
            _fail("INVALID_INPUT_STRUCTURE")
        if entry.robustness_id != dispatch.requested_ids[ordinal]:
            _fail("INVALID_INPUT_STRUCTURE")
        if entry.request_ordinal != ordinal:
            _fail("INVALID_INPUT_STRUCTURE")
        if type(entry.registration_ordinal) is not int or not (
            0 <= entry.registration_ordinal < len(dispatch.registered_ids)
        ):
            _fail("INVALID_INPUT_STRUCTURE")
        if dispatch.registered_ids[entry.registration_ordinal] != entry.robustness_id:
            _fail("INVALID_INPUT_STRUCTURE")
        if not _identifier_text(entry.method_id):
            _fail("INVALID_INPUT_STRUCTURE")
        if type(entry.parameters) is not FrozenJSONObject:
            _fail("INVALID_INPUT_STRUCTURE")
        _frozen_json_shape(entry.parameters)
        if entry.parameters_canonical_json != _parameters_canonical_json(entry.parameters):
            _fail("INVALID_INPUT_STRUCTURE")
    payload = _robustness_payload(artifact)
    if canonical_digest(payload) != artifact.artifact_digest:
        _fail("ARTIFACT_DIGEST_MISMATCH")
    _check_forbidden_content(payload)


def _execute(context: _SourceContext) -> ExecutionArtifactV1:
    estimator = _estimate(context)
    bootstrap, _lower, _upper = _bootstrap(context)
    method = context.method_configuration
    if bootstrap.enabled:
        method = replace(method, block_length=bootstrap.block_length)
    descriptives = _conditional_descriptives(context)
    evidence = _evidence_block(context, estimator, bootstrap)
    # X16 -- immutable construction, self digest and forbidden-content rejection
    artifact = ExecutionArtifactV1(
        ARTIFACT_SCHEMA_VERSION,
        EXECUTOR_VERSION,
        context.source_chain,
        context.provenance,
        method,
        context.sample,
        estimator,
        bootstrap,
        descriptives,
        evidence,
        False,
        True,
        True,
        "",
    )
    artifact = replace(artifact, artifact_digest=canonical_digest(_execution_payload(artifact)))
    _check_execution_artifact(artifact)
    return artifact


def execute_bounded_analysis(
    matrix: MatrixPreparationV1,
    preparation: DatasetPreparationV1,
    contract: Any,
    plan: DeterministicAnalysisPlan,
    bound_inputs: Any,
) -> ExecutionArtifactV1:
    """The only statistical-execution entry: run the frozen OLS/bootstrap on synthetic input.

    The five-object source chain is mandatory (no matrix-only path, no ``**kwargs``), is fully
    re-verified through the existing ``validate_design_matrix`` before any value is trusted, and
    every failure is fail-closed: no partial, truncated or downgraded artifact is ever returned.
    """
    return _execute(_validated_source(matrix, preparation, contract, plan, bound_inputs))


def execution_artifact_to_canonical_dict(artifact: ExecutionArtifactV1) -> dict:
    """Return an independent canonical dictionary without the artifact's own digest."""
    _shape(artifact, ExecutionArtifactV1)
    return _execution_payload(artifact)


def serialize_execution_artifact(artifact: ExecutionArtifactV1) -> bytes:
    """Validate then emit sorted, compact UTF-8 JSON with exactly one final newline."""
    _check_execution_artifact(artifact)
    payload = _execution_payload(artifact)
    payload["artifact_digest"] = artifact.artifact_digest
    return (
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
    ).encode("utf-8")


def validate_execution_artifact(
    artifact: ExecutionArtifactV1,
    matrix: MatrixPreparationV1,
    preparation: DatasetPreparationV1,
    contract: Any,
    plan: DeterministicAnalysisPlan,
    bound_inputs: Any,
) -> None:
    """V1-V4: validate the artifact, re-verify the source, re-execute and compare bytes."""
    # V1 -- artifact structure, invariants, content rules and self digest
    _check_execution_artifact(artifact)
    # V2 -- source verification with the existing five-argument entry
    validate_design_matrix(matrix, preparation, contract, plan, bound_inputs)
    # V3 -- re-execute with the same matrix, plan and seed
    expected = _execute(_validated_source(matrix, preparation, contract, plan, bound_inputs))
    # V4 -- byte-for-byte identity
    if serialize_execution_artifact(artifact) != serialize_execution_artifact(expected):
        _fail("IDENTITY_CONFLICT")


def prepare_registered_robustness_dispatch(
    matrix: MatrixPreparationV1,
    preparation: DatasetPreparationV1,
    contract: Any,
    plan: DeterministicAnalysisPlan,
    bound_inputs: Any,
    robustness_ids: tuple[str, ...],
) -> RobustnessArtifactV1:
    """Bind an ordered, explicit request to registry entries; never compute a statistic.

    R0-R6 are exactly X1-X7 (source verification first: dispatch is not discussed before the
    source is verified).  R7 validates request order and registry membership, R8 binds the
    registered method id and complete canonical parameters, and R9 constructs the immutable
    dispatch artifact with ``statistics_computed = False`` and ``outcome_read = False``.  No
    parameter key set or parameter value is interpreted, defaulted, rewritten or dropped.
    """
    # R0-R6 -- identical source verification, method allow-list, quality gate, holdout gate,
    # term/alignment check and cell conversion as X1-X7
    context = _validated_source(matrix, preparation, contract, plan, bound_inputs)
    # R7 -- request validation: ordered, non-empty, duplicate-free and fully registered
    if type(robustness_ids) is not tuple:
        _fail("INVALID_INPUT_STRUCTURE")
    if not robustness_ids:
        _fail("EMPTY_ROBUSTNESS_DISPATCH")
    for identifier in robustness_ids:
        if type(identifier) is not str:
            _fail("INVALID_INPUT_STRUCTURE")
    if len(set(robustness_ids)) != len(robustness_ids):
        _fail("DUPLICATE_ROBUSTNESS_ID")
    if (
        context.robustness_plan.get("dispatch_only") is not True
        or context.robustness_plan.get("automatic_expansion") is not False
        or context.robustness_plan.get("automatic_selection") is not False
    ):
        _fail("INVALID_INPUT_STRUCTURE", "robustness plan boundary is not dispatch-only")
    entries = context.registered_entries
    registered: list[str] = []
    for entry in entries:
        entry_id = _frozen_entry_field(entry, "robustness_id")
        if type(entry_id) is not str:
            _fail("INVALID_INPUT_STRUCTURE")
        registered.append(entry_id)
    registered_ids = tuple(registered)
    for identifier in robustness_ids:
        if identifier not in registered_ids:
            _fail("UNREGISTERED_ROBUSTNESS_ID")
    # R8 -- registry binding: registered identifier and JSON-object parameters, forwarded whole
    bound: list[RobustnessEntryDispatchV1] = []
    ordinal_of = {identifier: index for index, identifier in enumerate(registered_ids)}
    for ordinal, identifier in enumerate(robustness_ids):
        entry = entries[ordinal_of[identifier]]
        method_id = _frozen_entry_field(entry, "method_id")
        parameters = _frozen_entry_field(entry, "parameters")
        if not _identifier_text(method_id):
            _fail("UNSUPPORTED_ROBUSTNESS_METHOD")
        if type(parameters) is not FrozenJSONObject:
            _fail("UNSUPPORTED_ROBUSTNESS_METHOD")
        _frozen_json_shape(parameters)
        bound.append(
            RobustnessEntryDispatchV1(
                identifier,
                ordinal,
                ordinal_of[identifier],
                method_id,
                parameters,
                _parameters_canonical_json(parameters),
            )
        )
    # R9 -- dispatch artifact construction: no statistic, no selection, no aggregation
    dispatch = RobustnessDispatchV1(tuple(robustness_ids), registered_ids, False, False, False)
    artifact = RobustnessArtifactV1(
        ROBUSTNESS_ARTIFACT_SCHEMA_VERSION,
        EXECUTOR_VERSION,
        context.source_chain,
        context.provenance,
        context.method_configuration,
        context.sample,
        dispatch,
        tuple(bound),
        False,
        False,
        False,
        "",
    )
    artifact = replace(artifact, artifact_digest=canonical_digest(_robustness_payload(artifact)))
    _check_robustness_artifact(artifact)
    return artifact


def robustness_artifact_to_canonical_dict(artifact: RobustnessArtifactV1) -> dict:
    """Return an independent canonical dictionary without the artifact's own digest."""
    _shape(artifact, RobustnessArtifactV1)
    return _robustness_payload(artifact)


def serialize_robustness_artifact(artifact: RobustnessArtifactV1) -> bytes:
    """Validate then emit sorted, compact UTF-8 JSON with exactly one final newline."""
    _check_robustness_artifact(artifact)
    payload = _robustness_payload(artifact)
    payload["artifact_digest"] = artifact.artifact_digest
    return (
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
    ).encode("utf-8")


def validate_robustness_artifact(
    artifact: RobustnessArtifactV1,
    matrix: MatrixPreparationV1,
    preparation: DatasetPreparationV1,
    contract: Any,
    plan: DeterministicAnalysisPlan,
    bound_inputs: Any,
) -> None:
    """V1-V4: validate the artifact, re-verify the source, re-dispatch and compare bytes."""
    # V1 -- artifact structure, invariants, content rules and self digest
    _check_robustness_artifact(artifact)
    # V2 -- source verification with the existing five-argument entry
    validate_design_matrix(matrix, preparation, contract, plan, bound_inputs)
    # V3 -- re-dispatch (never re-compute a statistic) in the artifact's request order
    expected = prepare_registered_robustness_dispatch(
        matrix, preparation, contract, plan, bound_inputs, artifact.dispatch.requested_ids
    )
    # V4 -- byte-for-byte identity
    if serialize_robustness_artifact(artifact) != serialize_robustness_artifact(expected):
        _fail("IDENTITY_CONFLICT")


__all__ = [
    "ALLOWED_ANALYSIS_METHODS",
    "ALLOWED_BOOTSTRAP_METHODS",
    "ALLOWED_BOOTSTRAP_RNGS",
    "ARTIFACT_SCHEMA_VERSION",
    "BLOCK_LENGTH_POLICY_ID",
    "BOOTSTRAP_MIN_REPLICATIONS",
    "BootstrapBlockV1",
    "CoefficientV1",
    "DISPOSITIONS",
    "ESTIMATOR_CONTRACT_ID",
    "EVIDENCE_DIRECTIONS",
    "EXECUTOR_VERSION",
    "EstimatorBlockV1",
    "EvidenceBlockV1",
    "ExecutionArtifactV1",
    "ExecutionError",
    "FORBIDDEN_KEYS",
    "Float64ValueV1",
    "INTERCEPT_TERM_ROLE",
    "INTERPRETATION_BOUNDARY",
    "MAX_ABS_CELL_DECIMAL",
    "MODEL_FAMILY",
    "MethodConfigurationV1",
    "NUMERIC_BACKEND",
    "PRIMARY_TERM_ROLE",
    "PROVENANCE_CLASS",
    "ProvenanceV1",
    "REASONS",
    "REQUIRED_EVIDENCE_STATISTIC_ROLES",
    "ROBUSTNESS_ARTIFACT_SCHEMA_VERSION",
    "RobustnessArtifactV1",
    "RobustnessDispatchV1",
    "RobustnessEntryDispatchV1",
    "SYNTHETIC_DATASET_MODE",
    "SampleBlockV1",
    "SourceChainV1",
    "StatisticValueV1",
    "TermRefV1",
    "execute_bounded_analysis",
    "execution_artifact_to_canonical_dict",
    "prepare_registered_robustness_dispatch",
    "robustness_artifact_to_canonical_dict",
    "serialize_execution_artifact",
    "serialize_robustness_artifact",
    "validate_execution_artifact",
    "validate_robustness_artifact",
]
