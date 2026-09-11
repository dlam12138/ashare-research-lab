"""Pure projection of a validated synthetic preparation into a frozen design matrix.

This module implements the accepted design ``docs/m4_analysis_matrix_design_v1.md``:
an immutable daily design matrix derived exclusively from ``plan.design_plan.ordered_terms``
and the already-validated ``complete_rows`` of a ``DatasetPreparationV1``.

Boundaries kept by this module:

* no provider, filesystem, database, clock, random, environment or network access;
* no regression, rank, estimability, bootstrap, robustness or evidence execution;
* canonical decimal strings only -- input values are never re-parsed, rounded, reformatted
  or converted to float;
* ``materialize_design_matrix`` is the only public materialization entry and always runs the
  existing four-argument ``validate_dataset`` source verification before the quality gate and
  the projection; ``_project_validated_matrix`` stays private and is not an entry point.

The four public callables are ``materialize_design_matrix``, ``matrix_to_canonical_dict``,
``serialize_matrix`` and ``validate_design_matrix``.  The frozen dataclasses and
``MatrixError`` are exported so callers and tests can construct and inspect the contract,
but they add no callable entry point.  A successful matrix states nothing about full rank,
estimability, significance, tradability or execution authorization.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, is_dataclass, replace
from datetime import date
from decimal import Decimal, InvalidOperation
from types import UnionType
from typing import Any, get_args, get_origin, get_type_hints

from ashare_research.mechanism.datasets.synthetic import (
    DatasetPreparationV1,
    validate_dataset,
)
from ashare_research.mechanism.model_digest import canonical_digest
from ashare_research.mechanism.planning import (
    DeterministicAnalysisPlan,
    plan_to_canonical_dict,
)

MATRIX_SCHEMA_VERSION = "M4_DESIGN_MATRIX_V1"
MATRIX_BUILDER_VERSION = "M4_DAILY_CONDITIONAL_DESIGN_MATRIX_V1"
PLAN_SCHEMA_VERSION = "M4_DETERMINISTIC_ANALYSIS_PLAN_V1"
READY_STATUS = "READY_SYNTHETIC"
REJECTED_STATUS = "REJECTED_QUALITY"
STATUS_WORDS = (READY_STATUS, REJECTED_STATUS)
MISSINGNESS_POLICIES = ("FAIL_CLOSED", "RETAIN_IN_DENOMINATOR")
FAILURE_DISPOSITIONS = ("FAIL", "INCONCLUSIVE")
INTERCEPT_TERM = "INTERCEPT"
FACTOR_TERM = "FACTOR_CONTINUOUS"
CONDITION_TERM = "CONDITION_INDICATOR"
FACTOR_ROLE = "FACTOR"
HASH_RE = re.compile(r"[0-9a-f]{64}")
DATE_RE = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")
CONTROL_TERM_RE = re.compile(r"CONTROL_[0-9]{4}")

__all__ = [
    "MatrixColumnV1",
    "MatrixError",
    "MatrixPreparationV1",
    "MatrixQualityV1",
    "MatrixRowV1",
    "materialize_design_matrix",
    "matrix_to_canonical_dict",
    "serialize_matrix",
    "validate_design_matrix",
]


class MatrixError(ValueError):
    """Matrix projection failure with a stable machine-readable code."""

    def __init__(self, code: str, message: str | None = None):
        self.code = code
        super().__init__(message or code)


def _fail(code: str, message: str | None = None) -> None:
    raise MatrixError(code, message)


def _shape(value: Any, expected: Any) -> None:
    """Reject mutable or forged runtime representations before any projection."""
    origin = get_origin(expected)
    if origin is UnionType:
        for kind in get_args(expected):
            if type(value) is kind:
                _shape(value, kind)
                return
        _fail("INVALID_INPUT_STRUCTURE")
    elif origin is tuple:
        if type(value) is not tuple:
            _fail("INVALID_INPUT_STRUCTURE")
        kinds = get_args(expected)
        if len(kinds) == 2 and kinds[1] is Ellipsis:
            for item in value:
                _shape(item, kinds[0])
        else:
            if len(value) != len(kinds):
                _fail("INVALID_INPUT_STRUCTURE")
            for item, kind in zip(value, kinds, strict=True):
                _shape(item, kind)
    else:
        if type(value) is not expected:
            _fail("INVALID_INPUT_STRUCTURE")
        if is_dataclass(expected):
            for name, kind in get_type_hints(expected).items():
                _shape(getattr(value, name), kind)


def _canonical_decimal(value: Any) -> str:
    """Return the accepted canonical decimal text; never repair a non-canonical value."""
    if type(value) is not str:
        _fail("INVALID_INPUT_STRUCTURE", "matrix cells must be canonical decimal strings")
    try:
        parsed = Decimal(value)
    except (InvalidOperation, ValueError):
        _fail("INVALID_INPUT_STRUCTURE", "matrix cells must be canonical decimal strings")
    if not parsed.is_finite():
        _fail("INVALID_INPUT_STRUCTURE", "matrix cells must be finite decimal strings")
    canonical = "0" if parsed == 0 else format(parsed, "f")
    if "." in canonical:
        canonical = canonical.rstrip("0").rstrip(".")
    if canonical != value:
        _fail("INVALID_INPUT_STRUCTURE", "matrix cells must be canonical decimal strings")
    return value


def _canonical_date(value: Any) -> str:
    if type(value) is not str or DATE_RE.fullmatch(value) is None:
        _fail("INVALID_INPUT_STRUCTURE", "matrix dates must be canonical ISO dates")
    try:
        parsed = date.fromisoformat(value)
    except ValueError:
        _fail("INVALID_INPUT_STRUCTURE", "matrix dates must be canonical ISO dates")
    if parsed.isoformat() != value:
        _fail("INVALID_INPUT_STRUCTURE", "matrix dates must be canonical ISO dates")
    return value


def _hash_text(value: Any) -> str:
    if type(value) is not str or HASH_RE.fullmatch(value) is None:
        _fail("INVALID_INPUT_STRUCTURE", "inherited digest fields must be 64 lowercase hex")
    return value


@dataclass(frozen=True)
class MatrixColumnV1:
    """One accepted design column.  ``source_role`` is audit metadata, not a dispatch key."""

    position: int
    term_role: str
    coefficient_role: str
    source_role: str | None


@dataclass(frozen=True)
class MatrixRowV1:
    trade_date: str
    cells: tuple[str, ...]


@dataclass(frozen=True)
class MatrixQualityV1:
    """Inherited quality facts: ``status`` from the preparation, seven fields from quality."""

    status: str
    coverage_numerator: int
    coverage_denominator: int
    coverage_gate: str
    missingness_policy: str
    failure_disposition: str
    reason_counts: tuple[tuple[str, int], ...]
    rejected_dates: tuple[str, ...]


@dataclass(frozen=True)
class MatrixPreparationV1:
    matrix_schema_version: str
    builder_version: str
    source_contract_digest: str
    plan_digest: str
    input_digest: str
    domain_digest: str
    dataset_digest: str
    role_order: tuple[str, ...]
    columns: tuple[MatrixColumnV1, ...]
    response_role: str
    rows: tuple[MatrixRowV1, ...]
    quality: MatrixQualityV1
    execution_authorized: bool
    statistics_computed: bool
    matrix_digest: str


def matrix_to_canonical_dict(matrix: MatrixPreparationV1) -> dict:
    """Return an independent canonical dictionary without ``matrix_digest``.

    The self digest is not part of the canonical payload (design section 6.5 constraint 5);
    it is added only by ``serialize_matrix``.  Every returned container is fresh, so mutating
    the result cannot change the matrix or any later serialization.
    """
    _shape(matrix, MatrixPreparationV1)
    return {
        "matrix_schema_version": matrix.matrix_schema_version,
        "builder_version": matrix.builder_version,
        "source_contract_digest": matrix.source_contract_digest,
        "plan_digest": matrix.plan_digest,
        "input_digest": matrix.input_digest,
        "domain_digest": matrix.domain_digest,
        "dataset_digest": matrix.dataset_digest,
        "role_order": list(matrix.role_order),
        "columns": [
            {
                "position": column.position,
                "term_role": column.term_role,
                "coefficient_role": column.coefficient_role,
                "source_role": column.source_role,
            }
            for column in matrix.columns
        ],
        "response_role": matrix.response_role,
        "rows": [
            {"trade_date": row.trade_date, "cells": list(row.cells)} for row in matrix.rows
        ],
        "quality": {
            "status": matrix.quality.status,
            "coverage_numerator": matrix.quality.coverage_numerator,
            "coverage_denominator": matrix.quality.coverage_denominator,
            "coverage_gate": matrix.quality.coverage_gate,
            "missingness_policy": matrix.quality.missingness_policy,
            "failure_disposition": matrix.quality.failure_disposition,
            "reason_counts": {key: count for key, count in matrix.quality.reason_counts},
            "rejected_dates": list(matrix.quality.rejected_dates),
        },
        "execution_authorized": matrix.execution_authorized,
        "statistics_computed": matrix.statistics_computed,
    }


def _expected_term_roles(role_order: tuple[str, ...]) -> list[str]:
    controls = [role for role in role_order if role.startswith("CONTROL_")]
    return [INTERCEPT_TERM, FACTOR_TERM, *controls, CONDITION_TERM]


def _known_term_role(term_role: str) -> bool:
    return term_role in (INTERCEPT_TERM, FACTOR_TERM, CONDITION_TERM) or (
        CONTROL_TERM_RE.fullmatch(term_role) is not None
    )


def _check_matrix_invariants(matrix: MatrixPreparationV1, payload: dict) -> None:
    """Check design section 4.4 invariants 1-9, then the self digest (invariant 10)."""
    if (
        matrix.matrix_schema_version != MATRIX_SCHEMA_VERSION
        or matrix.builder_version != MATRIX_BUILDER_VERSION
    ):
        _fail("INVALID_INPUT_STRUCTURE", "matrix builder identity is not the frozen version")
    for name in (
        "source_contract_digest",
        "plan_digest",
        "input_digest",
        "domain_digest",
        "dataset_digest",
    ):
        _hash_text(getattr(matrix, name))
    if not matrix.role_order or len(set(matrix.role_order)) != len(matrix.role_order):
        _fail("INVALID_INPUT_STRUCTURE", "role_order must be non-empty and unique")
    if not matrix.columns:
        _fail("INVALID_INPUT_STRUCTURE", "matrix must declare at least one column")
    if [column.position for column in matrix.columns] != list(range(1, len(matrix.columns) + 1)):
        _fail("INVALID_INPUT_STRUCTURE", "column positions must be contiguous from 1")
    if [column.term_role for column in matrix.columns] != _expected_term_roles(matrix.role_order):
        _fail("INVALID_INPUT_STRUCTURE", "column term roles must follow role_order")
    if matrix.response_role not in matrix.role_order:
        _fail("INVALID_INPUT_STRUCTURE", "response_role must be a role_order member")
    if matrix.response_role in [column.term_role for column in matrix.columns]:
        _fail("INVALID_INPUT_STRUCTURE", "response_role must not become a matrix column")
    previous_date: str | None = None
    for row in matrix.rows:
        _canonical_date(row.trade_date)
        if previous_date is not None and row.trade_date <= previous_date:
            _fail("INVALID_INPUT_STRUCTURE", "matrix rows must follow ascending date order")
        previous_date = row.trade_date
        if len(row.cells) != len(matrix.columns):
            _fail("INVALID_INPUT_STRUCTURE", "matrix row width must equal the column count")
        for cell in row.cells:
            _canonical_decimal(cell)
        if row.cells[0] != "1":
            _fail("INVALID_INPUT_STRUCTURE", "intercept cells must be the literal 1")
        if row.cells[-1] not in ("0", "1"):
            _fail("INVALID_INPUT_STRUCTURE", "condition cells must be 0 or 1")
    quality = matrix.quality
    if quality.status not in STATUS_WORDS:
        _fail("INVALID_INPUT_STRUCTURE", "quality status is not a frozen status word")
    if quality.coverage_denominator <= 0 or not (
        0 <= quality.coverage_numerator <= quality.coverage_denominator
    ):
        _fail("INVALID_INPUT_STRUCTURE", "coverage counts must satisfy 0 <= n <= d and d > 0")
    gate = _canonical_decimal(quality.coverage_gate)
    if not Decimal(0) <= Decimal(gate) <= Decimal(1):
        _fail("INVALID_INPUT_STRUCTURE", "coverage gate must be a canonical decimal in [0, 1]")
    if quality.missingness_policy not in MISSINGNESS_POLICIES:
        _fail("INVALID_INPUT_STRUCTURE", "missingness policy is not a frozen policy word")
    if quality.failure_disposition not in FAILURE_DISPOSITIONS:
        _fail("INVALID_INPUT_STRUCTURE", "failure disposition is not a frozen disposition word")
    reason_keys = [key for key, _ in quality.reason_counts]
    if reason_keys != sorted(set(reason_keys)):
        _fail("INVALID_INPUT_STRUCTURE", "reason counts must be uniquely sorted by reason")
    previous_rejected: str | None = None
    for rejected_date in quality.rejected_dates:
        _canonical_date(rejected_date)
        if previous_rejected is not None and rejected_date <= previous_rejected:
            _fail("INVALID_INPUT_STRUCTURE", "rejected dates must be in ascending order")
        previous_rejected = rejected_date
    if (quality.status == READY_STATUS) is not (len(matrix.rows) > 0):
        _fail("INVALID_INPUT_STRUCTURE", "ready status and non-empty rows must agree")
    if matrix.execution_authorized is not False or matrix.statistics_computed is not False:
        _fail("INVALID_INPUT_STRUCTURE", "execution and statistics flags must stay false")
    if matrix.matrix_digest != canonical_digest(payload):
        _fail("MATRIX_DIGEST_MISMATCH")


def _validated_matrix_payload(matrix: MatrixPreparationV1) -> dict:
    payload = matrix_to_canonical_dict(matrix)
    _check_matrix_invariants(matrix, payload)
    return payload


def _plan_terms(plan: Any) -> tuple[list[dict], str]:
    """Read the frozen design terms from the plan; column order comes only from the plan."""
    if plan.schema_version != PLAN_SCHEMA_VERSION:
        _fail("UNSUPPORTED_PLAN_SCHEMA")
    try:
        payload = plan_to_canonical_dict(plan)
    except (ValueError, TypeError) as exc:
        _fail("INVALID_INPUT_STRUCTURE", str(exc))
    design = payload.get("design_plan")
    if type(design) is not dict:
        _fail("INVALID_INPUT_STRUCTURE", "plan design section is missing")
    terms = design.get("ordered_terms")
    if type(terms) is not list or not terms:
        _fail("INVALID_INPUT_STRUCTURE", "plan ordered_terms must be a non-empty list")
    response_role = design.get("response_role")
    if type(response_role) is not str:
        _fail("PLAN_TERM_ROLE_MISMATCH", "plan response_role is missing")
    checked: list[dict] = []
    for term in terms:
        if type(term) is not dict:
            _fail("INVALID_INPUT_STRUCTURE", "plan ordered_terms entries must be objects")
        term_role = term.get("term_role")
        position = term.get("position")
        coefficient_role = term.get("coefficient_role")
        source_role = term.get("source_series_role")
        if type(term_role) is not str or type(coefficient_role) is not str:
            _fail("INVALID_INPUT_STRUCTURE", "plan term names must be strings")
        if type(position) is not int or (source_role is not None and type(source_role) is not str):
            _fail("INVALID_INPUT_STRUCTURE", "plan term position and source role are malformed")
        if not _known_term_role(term_role):
            _fail("UNSUPPORTED_TERM_ROLE")
        checked.append(
            {
                "position": position,
                "term_role": term_role,
                "coefficient_role": coefficient_role,
                "source_role": source_role,
            }
        )
    if [term["position"] for term in checked] != list(range(1, len(checked) + 1)):
        _fail("PLAN_TERM_ROLE_MISMATCH", "ordered term positions must be contiguous from 1")
    return checked, response_role


def _preparation_role_order(preparation: DatasetPreparationV1) -> tuple[str, ...]:
    role_order = preparation.role_order
    if not role_order or len(set(role_order)) != len(role_order):
        _fail("INVALID_INPUT_STRUCTURE", "preparation role_order must be non-empty and unique")
    if preparation.quality.coverage_denominator != len(preparation.audit_rows):
        _fail("INVALID_INPUT_STRUCTURE", "coverage denominator must equal the audit row count")
    for row in preparation.audit_rows:
        if tuple(cell.role for cell in row.cells) != role_order:
            _fail("INVALID_INPUT_STRUCTURE", "audit row cells must follow role_order")
    for _, values, _ in preparation.complete_rows:
        if len(values) != len(role_order):
            _fail("INVALID_INPUT_STRUCTURE", "complete row width must equal role_order")
    return role_order


def _project_rows(
    preparation: DatasetPreparationV1, terms: list[dict], role_order: tuple[str, ...]
) -> tuple[MatrixRowV1, ...]:
    if FACTOR_ROLE not in role_order:
        _fail("PLAN_TERM_ROLE_MISMATCH", "role_order must contain the factor role")
    index = {role: position for position, role in enumerate(role_order)}
    rows: list[MatrixRowV1] = []
    previous_date: str | None = None
    for trade_date, values, indicator in preparation.complete_rows:
        trade_date = _canonical_date(trade_date)
        if previous_date is not None and trade_date <= previous_date:
            _fail("INVALID_INPUT_STRUCTURE", "complete rows must follow ascending date order")
        previous_date = trade_date
        if type(indicator) is not int or indicator not in (0, 1):
            _fail("INVALID_INPUT_STRUCTURE", "condition indicator must be a strict 0 or 1 int")
        cells = []
        for term in terms:
            term_role = term["term_role"]
            if term_role == INTERCEPT_TERM:
                cell = "1"
            elif term_role == FACTOR_TERM:
                cell = values[index[FACTOR_ROLE]]
            elif term_role == CONDITION_TERM:
                cell = "1" if indicator == 1 else "0"
            else:
                cell = values[index[term_role]]
            cells.append(_canonical_decimal(cell))
        rows.append(MatrixRowV1(trade_date, tuple(cells)))
    return tuple(rows)


def _with_matrix_digest(matrix: MatrixPreparationV1) -> MatrixPreparationV1:
    digest = canonical_digest(matrix_to_canonical_dict(matrix))
    return replace(matrix, matrix_digest=digest)


def _project_validated_matrix(
    preparation: DatasetPreparationV1, plan: DeterministicAnalysisPlan
) -> MatrixPreparationV1:
    """Private shared projection.  It performs no source verification and is not an entry point."""
    if type(plan) is not DeterministicAnalysisPlan:
        _fail("INVALID_INPUT_STRUCTURE", "plan must be a DeterministicAnalysisPlan")
    _shape(preparation, DatasetPreparationV1)
    terms, response_role = _plan_terms(plan)
    role_order = _preparation_role_order(preparation)
    if [term["term_role"] for term in terms] != _expected_term_roles(role_order):
        _fail("PLAN_TERM_ROLE_MISMATCH")
    if response_role not in role_order:
        _fail("PLAN_TERM_ROLE_MISMATCH", "response_role must be a preparation role")
    if preparation.status != READY_STATUS or not preparation.complete_rows:
        _fail("DATASET_NOT_READY")
    matrix = MatrixPreparationV1(
        MATRIX_SCHEMA_VERSION,
        MATRIX_BUILDER_VERSION,
        preparation.source_contract_digest,
        preparation.plan_digest,
        preparation.input_digest,
        preparation.domain_digest,
        preparation.dataset_digest,
        tuple(role_order),
        tuple(
            MatrixColumnV1(
                term["position"],
                term["term_role"],
                term["coefficient_role"],
                term["source_role"],
            )
            for term in terms
        ),
        response_role,
        _project_rows(preparation, terms, role_order),
        MatrixQualityV1(
            preparation.status,
            preparation.quality.coverage_numerator,
            preparation.quality.coverage_denominator,
            preparation.quality.coverage_gate,
            preparation.quality.missingness_policy,
            preparation.quality.failure_disposition,
            tuple(sorted(preparation.quality.reason_counts)),
            tuple(preparation.quality.rejected_dates),
        ),
        False,
        False,
        "",
    )
    matrix = _with_matrix_digest(matrix)
    # Construction validates: the built object must satisfy every frozen invariant itself.
    _validated_matrix_payload(matrix)
    return matrix


def materialize_design_matrix(
    preparation: DatasetPreparationV1,
    contract: Any,
    plan: DeterministicAnalysisPlan,
    bound_inputs: Any,
) -> MatrixPreparationV1:
    """Verify the source with the existing four-argument validator, then project.

    Upstream ``AdapterError`` values propagate unchanged.  A preparation that is not ready
    raises ``MatrixError("DATASET_NOT_READY")`` before any projection; no partial or empty
    matrix object can be returned.
    """
    validate_dataset(preparation, contract, plan, bound_inputs)
    return _project_validated_matrix(preparation, plan)


def serialize_matrix(matrix: MatrixPreparationV1) -> bytes:
    """Validate then emit sorted, compact UTF-8 JSON with exactly one final newline."""
    payload = _validated_matrix_payload(matrix)
    payload["matrix_digest"] = matrix.matrix_digest
    return (
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
    ).encode("utf-8")


def validate_design_matrix(
    matrix: MatrixPreparationV1,
    preparation: DatasetPreparationV1,
    contract: Any,
    plan: DeterministicAnalysisPlan,
    bound_inputs: Any,
) -> None:
    """Validate the matrix object, re-run source verification, re-project and compare bytes."""
    _validated_matrix_payload(matrix)
    validate_dataset(preparation, contract, plan, bound_inputs)
    expected = _project_validated_matrix(preparation, plan)
    if serialize_matrix(matrix) != serialize_matrix(expected):
        _fail("IDENTITY_CONFLICT")
