"""Acceptance coverage for the synthetic-only M4 bounded executor (AC-01..AC-19).

The fixtures follow the reproduction protocol of
``docs/m4_bounded_execution_acceptance_cases_v1.md``: the canonical base document/contract comes
from ``tests/test_m4_stage4a1_typed_contract.py`` and the base bound inputs from
``tests/test_m4_synthetic_dataset_adapter.py``.  Positive fixtures are synthetic ``n >= k``
full-rank variants of the same document; the untouched 3x5 fixture stays the singular negative.

Numerical expectations are limited to the frozen contract arithmetic (block length, interval
indices, endpoint order statistics) and to dispositions produced by the frozen table.  No test
asserts an expected coefficient magnitude, and nothing here reads real data, a provider, the
database, holdout or M4-B.
"""

from __future__ import annotations

import hashlib
import inspect
import json
import os
import re
import socket
import subprocess
import sys
from dataclasses import fields, replace
from decimal import Decimal
from functools import cache
from pathlib import Path
from typing import NamedTuple

import numpy
import pytest
from test_m4_stage4a1_typed_contract import _compiled, _document
from test_m4_synthetic_dataset_adapter import ROLES as BASE_ROLES
from test_m4_synthetic_dataset_adapter import _bound, _inputs

from ashare_research.mechanism import execution as execution_package
from ashare_research.mechanism.datasets import (
    AdapterError,
    BoundDatasetInputsV1,
    ExpectedDomainV1,
    ObservationV1,
    RoleBindingV1,
    dataset_to_canonical_dict,
    materialize_analysis_dataset,
    serialize_dataset,
)
from ashare_research.mechanism.execution import (
    ALLOWED_ANALYSIS_METHODS,
    ALLOWED_BOOTSTRAP_METHODS,
    ALLOWED_BOOTSTRAP_RNGS,
    ARTIFACT_SCHEMA_VERSION,
    BLOCK_LENGTH_POLICY_ID,
    DISPOSITIONS,
    ESTIMATOR_CONTRACT_ID,
    EVIDENCE_DIRECTIONS,
    EXECUTOR_VERSION,
    FORBIDDEN_KEYS,
    INTERPRETATION_BOUNDARY,
    MODEL_FAMILY,
    NUMERIC_BACKEND,
    PRIMARY_TERM_ROLE,
    PROVENANCE_CLASS,
    REASONS,
    ROBUSTNESS_ARTIFACT_SCHEMA_VERSION,
    BootstrapBlockV1,
    CoefficientV1,
    EstimatorBlockV1,
    EvidenceBlockV1,
    ExecutionError,
    Float64ValueV1,
    RobustnessArtifactV1,
    SampleBlockV1,
    StatisticValueV1,
    execute_bounded_analysis,
    execution_artifact_to_canonical_dict,
    prepare_registered_robustness_dispatch,
    robustness_artifact_to_canonical_dict,
    serialize_execution_artifact,
    serialize_robustness_artifact,
    validate_execution_artifact,
    validate_robustness_artifact,
)
from ashare_research.mechanism.execution import bounded as execution
from ashare_research.mechanism.hypothesis_config import (
    FrozenJSONList,
    FrozenJSONNumber,
    FrozenJSONObject,
    HypothesisConfigError,
    canonical_decimal,
    parse_hypothesis_config,
)
from ashare_research.mechanism.model_digest import canonical_digest
from ashare_research.mechanism.planning import build_analysis_plan, plan_to_canonical_dict
from ashare_research.mechanism.planning.matrix import (
    MatrixError,
    materialize_design_matrix,
    matrix_to_canonical_dict,
    serialize_matrix,
    validate_design_matrix,
)

ROOT = Path(__file__).resolve().parents[1]
SOURCE_PATH = ROOT / "src" / "ashare_research" / "mechanism" / "execution" / "bounded.py"
SERIES_BY_ROLE = {
    "TARGET_OUTCOME": "SYNTH_TARGET_A",
    "FACTOR": "SYNTH_FACTOR_A",
    "CONTROL_0001": "SYNTH_CONTROL_1",
    "CONTROL_0002": "SYNTH_CONTROL_2",
}
PUBLIC_ENTRIES = (
    "execute_bounded_analysis",
    "execution_artifact_to_canonical_dict",
    "serialize_execution_artifact",
    "validate_execution_artifact",
    "prepare_registered_robustness_dispatch",
    "robustness_artifact_to_canonical_dict",
    "serialize_robustness_artifact",
    "validate_robustness_artifact",
)
POSITIVE_ROWS = 24


class _Chain(NamedTuple):
    contract: object
    plan: object
    bound_inputs: object
    preparation: object
    matrix: object


def _dates(count: int) -> tuple[str, ...]:
    return tuple(f"2020-01-{day:02d}" for day in range(2, 2 + count))


def _row_values(count: int, variant: str) -> dict[str, tuple[str, ...]]:
    """Synthetic per-role values; the indicator is negative-factor conditioned (LTE -0.01)."""
    factor = [
        canonical_decimal(
            Decimal("-0.02") - Decimal("0.001") * index
            if index % 2 == 0
            else Decimal("0.01") + Decimal("0.001") * index
        )
        for index in range(count)
    ]
    control1 = [canonical_decimal(Decimal("0.005") * (index + 1)) for index in range(count)]
    control2 = [canonical_decimal(Decimal("0.002") * (index * index + 1)) for index in range(count)]
    levels = {
        "positive": "0.02",
        "negative": "-0.02",
        "weak": "0.001",
        "noisy": "0.02",
        "tiny": "0.000000000001",
        "zero": "0",
    }
    outcome = []
    for index in range(count):
        if variant == "zero":
            outcome.append(Decimal(0))
            continue
        indicator = Decimal(1) if index % 2 == 0 else Decimal(0)
        value = (
            Decimal(levels[variant]) * indicator
            + Decimal("0.001") * Decimal(control1[index])
            + Decimal("0.0005") * Decimal(control2[index])
        )
        if variant in ("noisy", "weak"):
            value += Decimal("0.0007") * Decimal(index % 3)
        outcome.append(value)
    return {
        "TARGET_OUTCOME": tuple(canonical_decimal(value) for value in outcome),
        "FACTOR": tuple(factor),
        "CONTROL_0001": tuple(control1),
        "CONTROL_0002": tuple(control2),
    }


def _execution_domain(dates: tuple[str, ...]) -> ExpectedDomainV1:
    calendar = {
        "evidence_kind": "SYNTHETIC_CALENDAR_V1",
        "domain_id": "SYNTH_DOMAIN_A",
        "development_start": "2020-01-01",
        "development_end": "2022-12-31",
        "expected_dates": list(dates),
    }
    membership = {
        "evidence_kind": "SYNTHETIC_FIXED_MEMBERSHIP_V1",
        "universe_id": "SYNTH_UNIVERSE_A",
        "target_series_id": "SYNTH_TARGET_A",
        "expected_dates": list(dates),
    }
    calendar["evidence_digest"] = canonical_digest(calendar)
    membership["evidence_digest"] = canonical_digest(membership)
    return ExpectedDomainV1.from_dict(
        {
            "domain_id": "SYNTH_DOMAIN_A",
            "universe_id": "SYNTH_UNIVERSE_A",
            "membership_policy": "SYNTHETIC_FIXED_UNIVERSE",
            "pit_policy": "EXPLICIT_PIT",
            "target_series_id": "SYNTH_TARGET_A",
            "identity_policy": "SYNTHETIC_FIXED_IDENTITY",
            "development_start": "2020-01-01",
            "development_end": "2022-12-31",
            "expected_dates": list(dates),
            "calendar_evidence": calendar,
            "membership_evidence": membership,
        }
    )


def _execution_inputs(dates, values, roles=BASE_ROLES, missing=None) -> BoundDatasetInputsV1:
    bindings = tuple(
        RoleBindingV1(
            role,
            SERIES_BY_ROLE[role],
            "DAILY_RETURN",
            "DECIMAL_RETURN",
            "SYNTHETIC_DECLARED_RETURN",
            "SYNTH_DAILY_RETURN" if role == "TARGET_OUTCOME" else None,
            "1D",
            "CLOSE_TO_CLOSE",
        )
        for role in roles
    )
    rows = []
    for role in roles:
        binding = bindings[roles.index(role)]
        for index, trade_date in enumerate(dates):
            if missing == (role, trade_date):
                continue
            value = values[role][index]
            payload = {
                "role": role,
                "trade_date": trade_date,
                "value": value,
                "available_on": trade_date,
                "source_record_id": f"SRC_{role}_{trade_date}",
                "binding": {
                    name: getattr(binding, name) for name in binding.__dataclass_fields__
                },
            }
            rows.append(
                ObservationV1(
                    role,
                    trade_date,
                    value,
                    trade_date,
                    payload["source_record_id"],
                    canonical_digest(payload),
                )
            )
    return BoundDatasetInputsV1(
        "M4_BOUND_SYNTHETIC_DATASET_V1",
        "SYNTHETIC",
        "contract",
        "plan",
        _execution_domain(dates),
        bindings,
        tuple(rows),
        "",
    )


def _scenario(
    *,
    dates,
    values,
    roles=BASE_ROLES,
    missing=None,
    root=None,
    quality=None,
    bootstrap=None,
    evidence=None,
    registry=None,
    holdout=None,
    build_matrix=True,
) -> _Chain:
    document = _document()
    document["development"] = {"start": "2020-01-01", "end": "2022-12-31"}
    document["condition"] = {"operator": "LTE", "threshold": "-0.0100"}
    for key, value in (root or {}).items():
        document[key] = value
    for key, value in (quality or {}).items():
        document["data_quality_gates"][key] = value
    for key, value in (bootstrap or {}).items():
        document["bootstrap_policy"][key] = value
    for key, value in (evidence or {}).items():
        document["evidence_rule"][key] = value
    if registry is not None:
        document["robustness_registry"] = registry
    if holdout is not None:
        document["holdout_policy"] = holdout
    contract = _compiled(document)
    plan = build_analysis_plan(contract)
    inputs = _bound(contract, plan, _execution_inputs(dates, values, roles=roles, missing=missing))
    preparation = materialize_analysis_dataset(contract, plan, inputs)
    matrix = (
        materialize_design_matrix(preparation, contract, plan, inputs) if build_matrix else None
    )
    return _Chain(contract, plan, inputs, preparation, matrix)


@cache
def _base_chain() -> _Chain:
    contract = _compiled()
    plan = build_analysis_plan(contract)
    inputs = _bound(contract, plan, _inputs())
    preparation = materialize_analysis_dataset(contract, plan, inputs)
    matrix = materialize_design_matrix(preparation, contract, plan, inputs)
    return _Chain(contract, plan, inputs, preparation, matrix)


@cache
def _positive_chain() -> _Chain:
    dates = _dates(POSITIVE_ROWS)
    return _scenario(dates=dates, values=_row_values(len(dates), "noisy"))


def _execute(chain: _Chain):
    return execute_bounded_analysis(
        chain.matrix, chain.preparation, chain.contract, chain.plan, chain.bound_inputs
    )


def _dispatch(chain: _Chain, robustness_ids):
    return prepare_registered_robustness_dispatch(
        chain.matrix,
        chain.preparation,
        chain.contract,
        chain.plan,
        chain.bound_inputs,
        robustness_ids,
    )


def _dispatch_with(chain: _Chain, preparation, plan, robustness_ids):
    return prepare_registered_robustness_dispatch(
        chain.matrix, preparation, chain.contract, plan, chain.bound_inputs, robustness_ids
    )


def _validate(artifact, chain: _Chain):
    return validate_execution_artifact(
        artifact, chain.matrix, chain.preparation, chain.contract, chain.plan, chain.bound_inputs
    )


def _validate_dispatch(artifact, chain: _Chain):
    return validate_robustness_artifact(
        artifact, chain.matrix, chain.preparation, chain.contract, chain.plan, chain.bound_inputs
    )


def _reforge(artifact, **changes):
    """Apply dataclass changes and recompute the self digest (deliberate forgery for V1/V4)."""
    forged = replace(artifact, **changes)
    payload = execution_artifact_to_canonical_dict(forged)
    return replace(forged, artifact_digest=canonical_digest(payload))


def _reforge_dispatch(artifact, **changes):
    forged = replace(artifact, **changes)
    payload = robustness_artifact_to_canonical_dict(forged)
    return replace(forged, artifact_digest=canonical_digest(payload))


def _rehashed_preparation(preparation):
    payload = dataset_to_canonical_dict(preparation)
    payload.pop("dataset_digest")
    return replace(preparation, dataset_digest=canonical_digest(payload))


def _float_of(value: Float64ValueV1) -> float:
    return float.fromhex(value.float64_hex)


def _walk_keys(payload) -> list[str]:
    found = []
    if type(payload) is dict:
        for key, value in payload.items():
            found.append(key)
            found.extend(_walk_keys(value))
    elif type(payload) is list:
        for item in payload:
            found.extend(_walk_keys(item))
    return found


def _walk_scalars(payload) -> list:
    found = []
    if type(payload) is dict:
        for value in payload.values():
            found.extend(_walk_scalars(value))
    elif type(payload) is list:
        for item in payload:
            found.extend(_walk_scalars(item))
    elif type(payload) is not bool:
        found.append(payload)
    return found


def _plan_design(chain: _Chain) -> dict:
    return plan_to_canonical_dict(chain.plan)["design_plan"]


def _plan_summary(chain: _Chain) -> dict:
    return plan_to_canonical_dict(chain.plan)["conditional_summary_plan"]


def _plan_bootstrap(chain: _Chain) -> dict:
    return plan_to_canonical_dict(chain.plan)["bootstrap_plan"]


def _plan_robustness(chain: _Chain) -> dict:
    return plan_to_canonical_dict(chain.plan)["robustness_plan"]


def _expected_block_length(n: int) -> int:
    """Independent transcription of the frozen integer rule N_CUBERT_ROUNDED_CLAMP_1_20_V1."""
    k = 0
    while (2 * k + 1) ** 3 <= 8 * n:
        k += 1
    return max(1, min(20, k))


def _expected_interval_indices(level: str, replications: int) -> tuple[str, int, int]:
    alpha = (Decimal(1) - Decimal(level)) / Decimal(2)
    low = int((Decimal(replications) * alpha).to_integral_value(rounding="ROUND_FLOOR"))
    high = (
        int(
            (Decimal(replications) * (Decimal(1) - alpha)).to_integral_value(
                rounding="ROUND_CEILING"
            )
        )
        - 1
    )
    return (
        canonical_decimal(alpha),
        max(0, min(replications - 1, low)),
        max(0, min(replications - 1, high)),
    )


def _independent_primary_effects(chain: _Chain, replications: int, seed: int) -> list[float]:
    """Recompute the frozen resampling contract from the design text (no executor code)."""
    matrix, preparation = chain.matrix, chain.preparation
    design = numpy.asarray(
        [[float(Decimal(cell)) for cell in row.cells] for row in matrix.rows],
        dtype=numpy.float64,
    )
    outcome_index = preparation.role_order.index(matrix.response_role)
    response = numpy.asarray(
        [float(Decimal(values[outcome_index])) for _, values, _ in preparation.complete_rows],
        dtype=numpy.float64,
    )
    n_rows, n_terms = design.shape
    term_roles = [column.term_role for column in matrix.columns]
    primary_index = term_roles.index(PRIMARY_TERM_ROLE)
    block_length = _expected_block_length(n_rows)
    block_count = (n_rows + block_length - 1) // block_length
    generator = numpy.random.Generator(numpy.random.PCG64(seed))
    samples = []
    for _ in range(replications):
        starts = generator.integers(0, n_rows - block_length + 1, size=block_count, endpoint=False)
        index = numpy.concatenate(
            [numpy.arange(int(start), int(start) + block_length) for start in starts]
        )[:n_rows]
        resampled = design[index]
        if int(numpy.linalg.matrix_rank(resampled)) != n_terms:
            raise AssertionError("independent recomputation found a singular resample")
        beta = numpy.linalg.lstsq(resampled, response[index], rcond=None)[0]
        samples.append(float(beta[primary_index]))
    return sorted(samples)


def _positive_chain_sha256() -> str:
    """Cross-process helper: the serialized positive artifact hash for this interpreter."""
    return hashlib.sha256(serialize_execution_artifact(_execute(_positive_chain()))).hexdigest()


def _freeze_entry(entry: dict):
    def freeze(value):
        if type(value) is dict:
            return FrozenJSONObject(
                tuple((key, freeze(item)) for key, item in sorted(value.items()))
            )
        if type(value) is list:
            return FrozenJSONList(tuple(freeze(item) for item in value))
        if type(value) is str:
            return value
        return FrozenJSONNumber(canonical_decimal(value))

    return FrozenJSONList((freeze(entry),))


def _replace_items(frozen: FrozenJSONObject, replacements: dict) -> FrozenJSONObject:
    return type(frozen)(
        tuple(
            (key, replacements[key]) if key in replacements else (key, value)
            for key, value in frozen.items
        )
    )


# --------------------------------------------------------------------------------------------
# Public surface and frozen constants
# --------------------------------------------------------------------------------------------


def test_public_surface_is_exactly_eight_entries_without_kwargs_escape_hatch():
    defined = {
        name
        for name, value in vars(execution).items()
        if inspect.isfunction(value)
        and not name.startswith("_")
        and value.__module__ == execution.__name__
    }
    assert defined == set(PUBLIC_ENTRIES)
    for name in PUBLIC_ENTRIES:
        signature = inspect.signature(getattr(execution, name))
        assert not any(
            parameter.kind is inspect.Parameter.VAR_KEYWORD
            for parameter in signature.parameters.values()
        ), name
    exported = set(execution.__all__)
    assert set(PUBLIC_ENTRIES) <= exported
    for private in ("_disposition", "_block_length", "_cell_to_float64"):
        assert private not in exported
        assert not hasattr(execution_package, private)


def test_implementation_has_no_forbidden_imports_or_io_surface():
    source = SOURCE_PATH.read_text(encoding="utf-8").lower()
    import_lines = [
        line for line in source.splitlines() if line.lstrip().startswith(("import ", "from "))
    ]
    joined = "\n".join(import_lines)
    for forbidden in (
        "statsmodels",
        "pandas",
        "socket",
        "pathlib",
        "subprocess",
        "import os",
        "requests",
        "duckdb",
        "regression",
        "bootstrap.py",
        "robustness",
        "evidence",
        "crash",
        "analysis_dataset",
        "analysis_contracts",
    ):
        assert forbidden not in joined, forbidden
    for forbidden_call in (
        r"\bopen\s*\(",
        r"\beval\s*\(",
        r"\bexec\s*\(",
        r"\bgetenv\b",
        r"\benviron\b",
    ):
        assert re.search(forbidden_call, source) is None, forbidden_call


def test_frozen_step_markers_follow_the_documented_order():
    source = SOURCE_PATH.read_text(encoding="utf-8")
    markers = re.findall(r"# (X\d+|R\d+(?:-R\d+)?|V\d+) ", source)
    assert [marker for marker in markers if marker.startswith("X")] == [
        f"X{index}" for index in range(1, 17)
    ]
    assert [marker for marker in markers if marker.startswith("R")] == ["R0-R6", "R7", "R8", "R9"]
    assert [marker for marker in markers if marker.startswith("V")] == [
        "V1",
        "V2",
        "V3",
        "V4",
        "V1",
        "V2",
        "V3",
        "V4",
    ]
    assert source.index("# X2 --") < source.index("# R7 --")
    assert source.index("# X2 --") < source.index("# X3 --")
    assert source.index("# R7 --") < source.index("# R8 --")


def test_frozen_constants_match_the_design():
    assert ARTIFACT_SCHEMA_VERSION == "M4_BOUNDED_EXECUTION_ARTIFACT_V1"
    assert ROBUSTNESS_ARTIFACT_SCHEMA_VERSION == "M4_REGISTERED_ROBUSTNESS_ARTIFACT_V1"
    assert EXECUTOR_VERSION == "M4_BOUNDED_DAILY_CONDITIONAL_OLS_EXECUTOR_V1"
    assert ESTIMATOR_CONTRACT_ID == "DAILY_CONDITIONAL_CONTROLLED_OLS_V1"
    assert MODEL_FAMILY == "OLS"
    assert NUMERIC_BACKEND == "numpy.linalg.lstsq"
    assert BLOCK_LENGTH_POLICY_ID == "N_CUBERT_ROUNDED_CLAMP_1_20_V1"
    assert PROVENANCE_CLASS == "SYNTHETIC_TEST_ONLY"
    assert PRIMARY_TERM_ROLE == "CONDITION_INDICATOR"
    allowed_methods = ALLOWED_ANALYSIS_METHODS
    allowed_bootstrap = ALLOWED_BOOTSTRAP_METHODS
    allowed_rngs = ALLOWED_BOOTSTRAP_RNGS
    dispositions = DISPOSITIONS
    reasons = REASONS
    assert allowed_methods == frozenset({ESTIMATOR_CONTRACT_ID})
    assert allowed_bootstrap == frozenset({"MOVING_BLOCK_BOOTSTRAP_V1"})
    assert allowed_rngs == frozenset({"PCG64"})
    assert dispositions == (
        "POSITIVE_SUPPORTED",
        "NEGATIVE_SUPPORTED",
        "TWO_SIDED_SUPPORTED",
        "NOT_SUPPORTED",
        "INCONCLUSIVE",
    )
    assert reasons == (
        "INTERVAL_ABOVE_ZERO",
        "INTERVAL_BELOW_ZERO",
        "INTERVAL_INCLUDES_ZERO",
        "BOOTSTRAP_DISABLED",
        "CONFIDENCE_BELOW_REQUIREMENT",
    )
    assert "FAIL" not in dispositions
    assert [_expected_block_length(n) for n in (1, 2, 3, 4, 5, 6, 8, 10, 20, 27, 64, 125, 216)] == [
        1,
        1,
        1,
        2,
        2,
        2,
        2,
        2,
        3,
        3,
        4,
        5,
        6,
    ]
    assert _expected_block_length(1000) == 10
    assert _expected_block_length(10000) == 20


# --------------------------------------------------------------------------------------------
# AC-01 positive artifact
# --------------------------------------------------------------------------------------------


def test_ac01_full_rank_synthetic_artifact_structure():
    chain = _positive_chain()
    artifact = _execute(chain)
    assert artifact.artifact_schema_version == ARTIFACT_SCHEMA_VERSION
    assert artifact.executor_version == EXECUTOR_VERSION
    assert artifact.source_chain.contract_digest == chain.contract.contract_digest
    assert artifact.source_chain.plan_digest == chain.plan.plan_digest
    assert artifact.source_chain.input_digest == chain.bound_inputs.input_digest
    assert artifact.source_chain.domain_digest == chain.preparation.domain_digest
    assert artifact.source_chain.dataset_digest == chain.preparation.dataset_digest
    assert artifact.source_chain.matrix_digest == chain.matrix.matrix_digest
    assert artifact.provenance.provenance_class == "SYNTHETIC_TEST_ONLY"
    assert artifact.provenance.synthetic_test_only is True
    assert artifact.provenance.dataset_mode == "SYNTHETIC"
    assert artifact.provenance.real_data_used is False
    assert artifact.provenance.holdout_accessed is False
    assert artifact.execution_authorized is False
    assert artifact.statistics_computed is True
    assert artifact.outcome_read is True

    ordered_terms = [
        (term["position"], term["term_role"], term["coefficient_role"])
        for term in _plan_design(chain)["ordered_terms"]
    ]
    assert [
        (term.position, term.term_role, term.coefficient_role)
        for term in artifact.method_configuration.terms
    ] == ordered_terms
    assert artifact.method_configuration.primary_effect_role == "gamma_condition"
    assert artifact.method_configuration.primary_effect_position == 5
    assert artifact.estimator.n_rows == len(chain.matrix.rows)
    assert artifact.estimator.n_terms == len(ordered_terms)
    assert artifact.estimator.rank == len(ordered_terms)
    assert len(artifact.estimator.coefficients) == len(ordered_terms)
    for term, coefficient in zip(
        artifact.method_configuration.terms, artifact.estimator.coefficients, strict=True
    ):
        assert (coefficient.position, coefficient.term_role, coefficient.coefficient_role) == (
            term.position,
            term.term_role,
            term.coefficient_role,
        )
        assert float.fromhex(coefficient.value.float64_hex) == _float_of(coefficient.value)
        assert (
            canonical_decimal(repr(_float_of(coefficient.value)))
            == coefficient.value.canonical_decimal
        )
    assert artifact.estimator.primary_effect == artifact.estimator.coefficients[4].value
    assert len(artifact.estimator.singular_values) == len(ordered_terms)
    assert artifact.estimator.residual_sum_of_squares is not None

    bootstrap = artifact.bootstrap
    assert bootstrap.enabled is True
    assert bootstrap.method_id == "MOVING_BLOCK_BOOTSTRAP_V1"
    assert bootstrap.replications == 1000
    assert bootstrap.seed == 42
    assert bootstrap.rng == "PCG64"
    assert bootstrap.confidence_level == "0.95"
    assert bootstrap.block_length == _expected_block_length(len(chain.matrix.rows)) == 3
    assert isinstance(bootstrap.primary_effect_lower, Float64ValueV1)
    assert isinstance(bootstrap.primary_effect_upper, Float64ValueV1)
    assert _float_of(bootstrap.primary_effect_lower) <= _float_of(bootstrap.primary_effect_upper)

    required_roles = _plan_summary(chain)["required_statistic_roles"]
    assert [value.role for value in artifact.conditional_descriptives] == required_roles
    assert len(required_roles) == 8
    counts = {value.role: value.count for value in artifact.conditional_descriptives}
    assert counts["CONDITION_COUNT"] + counts["ORDINARY_COUNT"] == artifact.estimator.n_rows
    assert artifact.evidence.disposition in DISPOSITIONS
    assert artifact.evidence.disposition_reason in REASONS
    assert artifact.evidence.interval_lower == bootstrap.primary_effect_lower
    assert artifact.evidence.interval_upper == bootstrap.primary_effect_upper
    assert artifact.evidence.primary_effect == artifact.estimator.primary_effect
    assert artifact.evidence.interpretation_boundary == INTERPRETATION_BOUNDARY

    payload = execution_artifact_to_canonical_dict(artifact)
    assert canonical_digest(payload) == artifact.artifact_digest
    encoded = serialize_execution_artifact(artifact)
    assert encoded.endswith(b"\n") and not encoded.endswith(b"\n\n")
    assert not encoded.startswith(b"\xef\xbb\xbf")
    assert encoded.decode("utf-8").encode("utf-8") == encoded
    assert b"\\u" not in encoded
    assert b'": ' not in encoded and b'", "' not in encoded
    assert _validate(artifact, chain) is None


# --------------------------------------------------------------------------------------------
# AC-02 singular base fixture
# --------------------------------------------------------------------------------------------


def test_ac02_base_fixture_is_rejected_as_singular():
    chain = _base_chain()
    values = numpy.asarray(
        [[float(Decimal(cell)) for cell in row.cells] for row in chain.matrix.rows]
    )
    assert values.shape == (3, 5)
    assert int(numpy.linalg.matrix_rank(values)) <= min(values.shape) < values.shape[1]
    with pytest.raises(ExecutionError) as caught:
        _execute(chain)
    assert caught.value.code == "SINGULAR_DESIGN"
    assert not isinstance(caught.value, AdapterError)
    assert not isinstance(caught.value, MatrixError)


# --------------------------------------------------------------------------------------------
# AC-03 source tamper
# --------------------------------------------------------------------------------------------


def test_ac03_source_tamper_is_an_upstream_error_at_x2():
    chain = _base_chain()
    tampered = _rehashed_preparation(
        replace(
            chain.preparation,
            complete_rows=tuple(
                (trade_date, cells, 1 - indicator)
                for trade_date, cells, indicator in chain.preparation.complete_rows
            ),
        )
    )
    assert serialize_dataset(tampered).endswith(b"\n")
    with pytest.raises(AdapterError) as caught:
        execute_bounded_analysis(
            chain.matrix, tampered, chain.contract, chain.plan, chain.bound_inputs
        )
    assert caught.value.code == "IDENTITY_CONFLICT"
    assert not isinstance(caught.value, ExecutionError)

    rows = list(chain.bound_inputs.observations)
    index = next(
        position
        for position, row in enumerate(rows)
        if row.role == "FACTOR" and row.trade_date == "2020-01-03"
    )
    payload = {
        "role": rows[index].role,
        "trade_date": rows[index].trade_date,
        "value": "-0.05",
        "available_on": rows[index].available_on,
        "source_record_id": rows[index].source_record_id,
        "binding": {
            name: getattr(chain.bound_inputs.bindings[1], name)
            for name in chain.bound_inputs.bindings[1].__dataclass_fields__
        },
    }
    rows[index] = replace(rows[index], value="-0.05", evidence_digest=canonical_digest(payload))
    rehashed = _bound(
        chain.contract, chain.plan, replace(chain.bound_inputs, observations=tuple(rows))
    )
    assert rehashed.input_digest != chain.bound_inputs.input_digest
    with pytest.raises(AdapterError) as caught:
        execute_bounded_analysis(
            chain.matrix, chain.preparation, chain.contract, chain.plan, rehashed
        )
    assert caught.value.code == "IDENTITY_CONFLICT"


# --------------------------------------------------------------------------------------------
# AC-04 matrix forgery and forged artifacts
# --------------------------------------------------------------------------------------------


def test_ac04_forged_matrix_and_forged_artifact_stages():
    chain = _positive_chain()
    artifact = _execute(chain)
    changed_row = replace(
        chain.matrix.rows[0], cells=("1", "-0.5") + chain.matrix.rows[0].cells[2:]
    )
    reinforced = replace(chain.matrix, rows=(changed_row,) + chain.matrix.rows[1:])
    recomputed = replace(
        reinforced, matrix_digest=canonical_digest(matrix_to_canonical_dict(reinforced))
    )
    with pytest.raises(MatrixError) as caught:
        execute_bounded_analysis(
            recomputed, chain.preparation, chain.contract, chain.plan, chain.bound_inputs
        )
    assert caught.value.code == "IDENTITY_CONFLICT"

    with pytest.raises(MatrixError) as caught:
        execute_bounded_analysis(
            reinforced, chain.preparation, chain.contract, chain.plan, chain.bound_inputs
        )
    assert caught.value.code == "MATRIX_DIGEST_MISMATCH"

    with pytest.raises(MatrixError) as caught:
        execute_bounded_analysis(
            replace(chain.matrix, execution_authorized=True),
            chain.preparation,
            chain.contract,
            chain.plan,
            chain.bound_inputs,
        )
    assert caught.value.code == "INVALID_INPUT_STRUCTURE"

    with pytest.raises(MatrixError) as caught:
        _validate(artifact, _Chain(chain.contract, chain.plan, chain.bound_inputs,
                                   chain.preparation, recomputed))
    assert caught.value.code == "IDENTITY_CONFLICT"

    forged_disposition = _reforge(
        artifact,
        evidence=replace(
            artifact.evidence,
            disposition="NOT_SUPPORTED",
            disposition_reason="INTERVAL_INCLUDES_ZERO",
        ),
    )
    with pytest.raises(ExecutionError) as caught:
        _validate(forged_disposition, chain)
    assert caught.value.code == "IDENTITY_CONFLICT"

    stale_digest = replace(
        artifact,
        sample=replace(artifact.sample, reason_counts=(("MISSING_VALUE", 1),)),
    )
    with pytest.raises(ExecutionError) as caught:
        _validate(stale_digest, chain)
    assert caught.value.code == "ARTIFACT_DIGEST_MISMATCH"


# --------------------------------------------------------------------------------------------
# AC-05 frozen validation order
# --------------------------------------------------------------------------------------------


def _out_of_range_chain() -> _Chain:
    dates = _dates(POSITIVE_ROWS)
    values = dict(_row_values(len(dates), "noisy"))
    values["CONTROL_0001"] = ("1000001",) + values["CONTROL_0001"][1:]
    return _scenario(dates=dates, values=values)


def test_ac05_order_source_errors_precede_method_quality_and_dispatch():
    chain = _base_chain()
    tampered = _rehashed_preparation(
        replace(
            chain.preparation,
            complete_rows=tuple(
                (trade_date, cells, 1 - indicator)
                for trade_date, cells, indicator in chain.preparation.complete_rows
            ),
        )
    )
    forged_plan = replace(chain.plan, analysis_method_id="OTHER_METHOD")
    with pytest.raises(AdapterError) as caught:
        execute_bounded_analysis(
            chain.matrix, tampered, chain.contract, forged_plan, chain.bound_inputs
        )
    assert caught.value.code == "CONTRACT_PLAN_MISMATCH"
    assert not isinstance(caught.value, ExecutionError)

    with pytest.raises(AdapterError) as caught:
        _dispatch_with(chain, tampered, chain.plan, ("SYNTH_UNREGISTERED",))
    assert caught.value.code == "IDENTITY_CONFLICT"
    assert not isinstance(caught.value, ExecutionError)

    out_of_range = _out_of_range_chain()
    with pytest.raises(MatrixError) as caught:
        execute_bounded_analysis(
            replace(out_of_range.matrix, execution_authorized=True),
            out_of_range.preparation,
            out_of_range.contract,
            out_of_range.plan,
            out_of_range.bound_inputs,
        )
    assert caught.value.code == "INVALID_INPUT_STRUCTURE"

    with pytest.raises(ExecutionError) as caught:
        _dispatch(chain, ())
    assert caught.value.code == "EMPTY_ROBUSTNESS_DISPATCH"

    with pytest.raises(ExecutionError) as caught:
        _dispatch(chain, ("SYNTH_UNREGISTERED",))
    assert caught.value.code == "UNREGISTERED_ROBUSTNESS_ID"


# --------------------------------------------------------------------------------------------
# AC-06 unsupported method family / bootstrap method / rng
# --------------------------------------------------------------------------------------------


def test_ac06_unsupported_methods_fail_closed_without_downgrade():
    chain = _base_chain()
    forged_method = replace(chain.plan, analysis_method_id="AUTOMATIC_MODEL_SELECTION")
    with pytest.raises(AdapterError) as caught:
        execute_bounded_analysis(
            chain.matrix, chain.preparation, chain.contract, forged_method, chain.bound_inputs
        )
    assert caught.value.code == "CONTRACT_PLAN_MISMATCH"

    forged_family = replace(
        chain.plan,
        design_plan=_replace_items(chain.plan.design_plan, {"model_family": "WLS"}),
    )
    with pytest.raises(AdapterError) as caught:
        execute_bounded_analysis(
            chain.matrix, chain.preparation, chain.contract, forged_family, chain.bound_inputs
        )
    assert caught.value.code == "CONTRACT_PLAN_MISMATCH"

    for key, value in (("method_id", "OTHER_BOOTSTRAP"), ("rng", "OTHER_RNG")):
        forged_bootstrap = replace(
            chain.plan,
            bootstrap_plan=_replace_items(chain.plan.bootstrap_plan, {key: value}),
        )
        with pytest.raises(AdapterError) as caught:
            execute_bounded_analysis(
                chain.matrix,
                chain.preparation,
                chain.contract,
                forged_bootstrap,
                chain.bound_inputs,
            )
        assert caught.value.code == "CONTRACT_PLAN_MISMATCH"

    assert _plan_bootstrap(chain)["method_id"] == "MOVING_BLOCK_BOOTSTRAP_V1"
    assert _plan_bootstrap(chain)["rng"] == "PCG64"


# --------------------------------------------------------------------------------------------
# AC-07 conversion and range gates
# --------------------------------------------------------------------------------------------


def test_ac07_cell_range_and_non_finite_gates():
    chain = _out_of_range_chain()
    with pytest.raises(ExecutionError) as caught:
        _execute(chain)
    assert caught.value.code == "CELL_OUT_OF_RANGE"
    with pytest.raises(ExecutionError) as caught:
        _dispatch(chain, ("SYNTH_ROBUSTNESS_1",))
    assert caught.value.code == "CELL_OUT_OF_RANGE"

    dates = _dates(8)
    values = dict(_row_values(len(dates), "noisy"))
    values["CONTROL_0001"] = ("1000000",) + values["CONTROL_0001"][1:]
    boundary = _scenario(
        dates=dates, values=values, bootstrap={"enabled": False, "method_id": "DISABLED"}
    )
    artifact = _execute(boundary)
    assert artifact.sample.row_count == len(dates)

    values = dict(_row_values(len(dates), "noisy"))
    values["CONTROL_0001"] = ("1000000000000000000",) + values["CONTROL_0001"][1:]
    with pytest.raises(ExecutionError) as caught:
        _execute(_scenario(dates=dates, values=values))
    assert caught.value.code == "CELL_OUT_OF_RANGE"

    artifact = _execute(_positive_chain())
    for bad_hex in ("inf", "nan", "-inf"):
        forged = _reforge(
            artifact,
            estimator=replace(
                artifact.estimator, primary_effect=Float64ValueV1(bad_hex, "0")
            ),
        )
        with pytest.raises(ExecutionError) as caught:
            serialize_execution_artifact(forged)
        assert caught.value.code == "NON_FINITE_ESTIMATE"


# --------------------------------------------------------------------------------------------
# AC-08 bootstrap enabled with exact endpoint indices
# --------------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("level", "replications", "alpha", "lower_index", "upper_index"),
    [
        ("0.95", 1000, "0.025", 25, 974),
        ("0.95", 8, "0.025", 0, 7),
        ("0.95", 3, "0.025", 0, 2),
        ("0.5", 8, "0.25", 2, 5),
        ("0.99", 1000, "0.005", 5, 994),
        ("0.9", 20, "0.05", 1, 18),
        ("0.95", 2, "0.025", 0, 1),
    ],
)
def test_ac08_bootstrap_enabled_exact_indices(level, replications, alpha, lower_index, upper_index):
    dates = _dates(POSITIVE_ROWS)
    chain = _scenario(
        dates=dates,
        values=_row_values(len(dates), "noisy"),
        bootstrap={"confidence_level": level, "replications": replications},
    )
    artifact = _execute(chain)
    assert (artifact.bootstrap.interval_alpha, artifact.bootstrap.lower_index) == (
        alpha,
        lower_index,
    )
    assert artifact.bootstrap.upper_index == upper_index
    assert _expected_interval_indices(level, replications) == (alpha, lower_index, upper_index)
    assert _float_of(artifact.bootstrap.primary_effect_lower) <= _float_of(
        artifact.bootstrap.primary_effect_upper
    )
    again = _execute(chain)
    assert serialize_execution_artifact(again) == serialize_execution_artifact(artifact)


def test_ac08_endpoints_are_exact_order_statistics_and_bounded_below_two_replications():
    dates = _dates(POSITIVE_ROWS)
    chain = _scenario(
        dates=dates,
        values=_row_values(len(dates), "noisy"),
        bootstrap={"replications": 8},
    )
    artifact = _execute(chain)
    samples = _independent_primary_effects(chain, 8, 42)
    assert len(set(samples)) > 1
    assert _float_of(artifact.bootstrap.primary_effect_lower) == samples[
        artifact.bootstrap.lower_index
    ]
    assert _float_of(artifact.bootstrap.primary_effect_upper) == samples[
        artifact.bootstrap.upper_index
    ]
    assert artifact.bootstrap.lower_index == 0 and artifact.bootstrap.upper_index == 7

    single = _scenario(
        dates=dates,
        values=_row_values(len(dates), "noisy"),
        bootstrap={"replications": 1},
    )
    with pytest.raises(ExecutionError) as caught:
        _execute(single)
    assert caught.value.code == "INSUFFICIENT_REPLICATIONS"


# --------------------------------------------------------------------------------------------
# AC-10 complete disposition table
# --------------------------------------------------------------------------------------------


def _exact_chain(variant: str, direction: str, requirement: str = "0.95") -> _Chain:
    dates = _dates(POSITIVE_ROWS)
    return _scenario(
        dates=dates,
        values=_row_values(len(dates), variant),
        evidence={"expected_direction": direction, "confidence_requirement": requirement},
    )


@pytest.mark.parametrize(
    ("variant", "direction", "disposition", "reason"),
    [
        ("positive", "POSITIVE", "POSITIVE_SUPPORTED", "INTERVAL_ABOVE_ZERO"),
        ("positive", "TWO_SIDED", "TWO_SIDED_SUPPORTED", "INTERVAL_ABOVE_ZERO"),
        ("negative", "NEGATIVE", "NEGATIVE_SUPPORTED", "INTERVAL_BELOW_ZERO"),
        ("negative", "TWO_SIDED", "TWO_SIDED_SUPPORTED", "INTERVAL_BELOW_ZERO"),
        ("zero", "POSITIVE", "NOT_SUPPORTED", "INTERVAL_INCLUDES_ZERO"),
        ("zero", "NEGATIVE", "NOT_SUPPORTED", "INTERVAL_INCLUDES_ZERO"),
        ("zero", "TWO_SIDED", "NOT_SUPPORTED", "INTERVAL_INCLUDES_ZERO"),
    ],
)
def test_ac10_disposition_table_all_directions(variant, direction, disposition, reason):
    artifact = _execute(_exact_chain(variant, direction))
    assert artifact.evidence.disposition == disposition
    assert artifact.evidence.disposition_reason == reason
    assert artifact.evidence.disposition in DISPOSITIONS
    assert artifact.evidence.disposition_reason in REASONS


def test_ac10_zero_endpoints_are_never_supported_and_confidence_precedes_direction():
    artifact = _execute(_exact_chain("zero", "POSITIVE"))
    lower = artifact.bootstrap.primary_effect_lower
    upper = artifact.bootstrap.primary_effect_upper
    assert lower.float64_hex == "0x0.0p+0" and upper.float64_hex == "0x0.0p+0"
    assert _float_of(lower) == 0.0 and _float_of(upper) == 0.0
    assert artifact.bootstrap.lower_index != artifact.bootstrap.upper_index
    assert artifact.evidence.disposition == "NOT_SUPPORTED"
    assert artifact.evidence.disposition_reason == "INTERVAL_INCLUDES_ZERO"
    assert not (0.0 > 0) and not (-0.0 > 0) and not (0.0 < 0) and not (-0.0 < 0)
    for direction in EVIDENCE_DIRECTIONS:
        assert _execute(_exact_chain("zero", direction)).evidence.disposition == "NOT_SUPPORTED"

    below = _execute(_exact_chain("positive", "POSITIVE", requirement="0.99"))
    assert below.evidence.confidence_requirement_satisfied is False
    assert below.evidence.disposition == "INCONCLUSIVE"
    assert below.evidence.disposition_reason == "CONFIDENCE_BELOW_REQUIREMENT"
    assert _float_of(below.bootstrap.primary_effect_lower) > 0

    tiny = _execute(_exact_chain("tiny", "POSITIVE"))
    assert _float_of(tiny.bootstrap.primary_effect_lower) > 0
    assert tiny.evidence.disposition == "POSITIVE_SUPPORTED"
    assert tiny.evidence.disposition_reason == "INTERVAL_ABOVE_ZERO"
    source = SOURCE_PATH.read_text(encoding="utf-8")
    assert "tolerance-free zero comparisons" in source
    for tolerance in ("isclose", "allclose", "epsilon", "round(", "approx"):
        assert tolerance not in source.lower(), tolerance


# --------------------------------------------------------------------------------------------
# AC-11 quality rejection and incomplete coverage
# --------------------------------------------------------------------------------------------


def _quality_chain(gate: str, missingness: str, missing, *, build_matrix: bool = True) -> _Chain:
    dates = _dates(8)
    return _scenario(
        dates=dates,
        values=_row_values(len(dates), "noisy"),
        missing=missing,
        quality={"coverage_gate": gate, "missingness_policy": missingness},
        bootstrap={"enabled": False, "method_id": "DISABLED"},
        build_matrix=build_matrix,
    )


def test_ac11_quality_rejection_produces_no_executable_matrix():
    dates = _dates(8)
    failed = _quality_chain("0.99", "FAIL_CLOSED", ("CONTROL_0002", dates[1]), build_matrix=False)
    assert failed.preparation.status == "REJECTED_QUALITY"
    assert failed.preparation.complete_rows == ()
    with pytest.raises(MatrixError) as caught:
        materialize_design_matrix(
            failed.preparation, failed.contract, failed.plan, failed.bound_inputs
        )
    assert caught.value.code == "DATASET_NOT_READY"

    retained = _quality_chain(
        "0.9", "RETAIN_IN_DENOMINATOR", ("CONTROL_0002", dates[1]), build_matrix=False
    )
    assert retained.preparation.status == "REJECTED_QUALITY"
    assert retained.preparation.complete_rows == ()

    error = ExecutionError("DATA_QUALITY_REJECTED", None, "FAIL")
    assert (error.code, error.disposition) == ("DATA_QUALITY_REJECTED", "FAIL")
    assert "FAIL" not in DISPOSITIONS
    assert _document()["evidence_rule"]["data_quality_failure_disposition"] == "INCONCLUSIVE"


def test_ac11_incomplete_coverage_is_explicit_and_does_not_rewrite_disposition():
    dates = _dates(8)
    incomplete = _quality_chain("0.85", "RETAIN_IN_DENOMINATOR", ("CONTROL_0002", dates[1]))
    assert incomplete.preparation.status == "READY_SYNTHETIC"
    assert incomplete.preparation.quality.coverage_numerator == 7
    assert incomplete.preparation.quality.coverage_denominator == 8
    artifact = _execute(incomplete)
    assert artifact.sample.row_count == 7
    assert artifact.sample.coverage_complete is False
    assert artifact.sample.coverage_gate_satisfied is True
    assert artifact.evidence.coverage_complete is False
    assert (artifact.evidence.disposition, artifact.evidence.disposition_reason) == (
        "INCONCLUSIVE",
        "BOOTSTRAP_DISABLED",
    )

    whole = _execute(_quality_chain("0.99", "FAIL_CLOSED", None))
    assert whole.sample.coverage_complete is True
    assert (whole.evidence.disposition, whole.evidence.disposition_reason) == (
        artifact.evidence.disposition,
        artifact.evidence.disposition_reason,
    )


# --------------------------------------------------------------------------------------------
# AC-12 registered robustness dispatch
# --------------------------------------------------------------------------------------------


def _registered_parameters(chain: _Chain, index: int):
    return _plan_robustness(chain)["entries"][index]["parameters"]


def test_ac12a_verbatim_registered_dispatch_on_the_unmodified_fixture():
    chain = _base_chain()
    artifact = _dispatch(chain, ("SYNTH_ROBUSTNESS_1",))
    assert artifact.artifact_schema_version == ROBUSTNESS_ARTIFACT_SCHEMA_VERSION
    assert artifact.executor_version == EXECUTOR_VERSION
    assert artifact.execution_authorized is False
    assert artifact.statistics_computed is False
    assert artifact.outcome_read is False
    assert artifact.dispatch.requested_ids == ("SYNTH_ROBUSTNESS_1",)
    assert artifact.dispatch.registered_ids == ("SYNTH_ROBUSTNESS_1",)
    assert artifact.dispatch.automatic_expansion is False
    assert artifact.dispatch.automatic_selection is False
    assert artifact.dispatch.parameters_interpreted is False
    assert len(artifact.entries) == 1
    entry = artifact.entries[0]
    assert entry.robustness_id == "SYNTH_ROBUSTNESS_1"
    assert entry.request_ordinal == 0
    assert entry.registration_ordinal == 0
    assert entry.method_id == "CONDITIONAL_DESCRIPTIVES_V1"
    assert entry.parameters_canonical_json == '{"trim":"0.0100","window":["1","2","3"]}'
    assert json.loads(entry.parameters_canonical_json) == {
        "trim": "0.0100",
        "window": ["1", "2", "3"],
    }
    assert isinstance(entry.parameters, FrozenJSONObject)
    assert json.loads(entry.parameters_canonical_json) == _registered_parameters(chain, 0)
    assert canonical_digest(robustness_artifact_to_canonical_dict(artifact)) == (
        artifact.artifact_digest
    )
    assert serialize_robustness_artifact(artifact).endswith(b"\n")
    assert _validate_dispatch(artifact, chain) is None
    payload = robustness_artifact_to_canonical_dict(artifact)
    assert payload["method_configuration"]["block_length"] is None
    assert {field.name for field in fields(RobustnessArtifactV1)}.isdisjoint(
        {"estimator", "bootstrap", "conditional_descriptives", "evidence"}
    )


def _two_entry_chain() -> _Chain:
    return _scenario(
        dates=_dates(3),
        values=_row_values(3, "noisy"),
        registry=[
            {
                "robustness_id": "SYNTH_ROBUSTNESS_1",
                "method_id": "CONDITIONAL_DESCRIPTIVES_V1",
                "parameters": {"trim": "0.0100", "window": [1, 2, 3]},
            },
            {
                "robustness_id": "SYNTH_ROBUSTNESS_2",
                "method_id": "CONDITIONAL_DESCRIPTIVES_V1",
                "parameters": {"trim": "0.0500", "window": [4, 5]},
            },
        ],
    )


def test_ac12_dispatch_request_validation_and_ordering_cases():
    chain = _base_chain()
    two = _two_entry_chain()
    second = _dispatch(two, ("SYNTH_ROBUSTNESS_2",))
    assert second.entries[0].registration_ordinal == 1
    assert second.dispatch.registered_ids == ("SYNTH_ROBUSTNESS_1", "SYNTH_ROBUSTNESS_2")
    assert len(second.entries) == 1
    forward = _dispatch(two, ("SYNTH_ROBUSTNESS_1", "SYNTH_ROBUSTNESS_2"))
    backward = _dispatch(two, ("SYNTH_ROBUSTNESS_2", "SYNTH_ROBUSTNESS_1"))
    assert [entry.robustness_id for entry in backward.entries] == [
        "SYNTH_ROBUSTNESS_2",
        "SYNTH_ROBUSTNESS_1",
    ]
    assert [entry.request_ordinal for entry in backward.entries] == [0, 1]
    assert [entry.registration_ordinal for entry in backward.entries] == [1, 0]
    assert backward.artifact_digest != forward.artifact_digest

    single_parameter = _scenario(
        dates=_dates(3),
        values=_row_values(3, "noisy"),
        registry=[
            {
                "robustness_id": "SYNTH_ROBUSTNESS_1",
                "method_id": "CONDITIONAL_DESCRIPTIVES_V1",
                "parameters": {"trim": "0.0100"},
            }
        ],
    )
    only_trim = _dispatch(single_parameter, ("SYNTH_ROBUSTNESS_1",))
    assert only_trim.entries[0].parameters_canonical_json == '{"trim":"0.0100"}'

    with pytest.raises(ExecutionError) as caught:
        _dispatch(chain, ("SYNTH_UNREGISTERED",))
    assert caught.value.code == "UNREGISTERED_ROBUSTNESS_ID"
    with pytest.raises(ExecutionError) as caught:
        _dispatch(chain, ())
    assert caught.value.code == "EMPTY_ROBUSTNESS_DISPATCH"
    with pytest.raises(ExecutionError) as caught:
        _dispatch(chain, ("SYNTH_ROBUSTNESS_1", "SYNTH_ROBUSTNESS_1"))
    assert caught.value.code == "DUPLICATE_ROBUSTNESS_ID"
    with pytest.raises(ExecutionError) as caught:
        _dispatch(chain, ["SYNTH_ROBUSTNESS_1"])
    assert caught.value.code == "INVALID_INPUT_STRUCTURE"

    empty = _scenario(dates=_dates(3), values=_row_values(3, "noisy"), registry=[])
    with pytest.raises(ExecutionError) as caught:
        _dispatch(empty, ("SYNTH_ROBUSTNESS_1",))
    assert caught.value.code == "UNREGISTERED_ROBUSTNESS_ID"


def test_ac12_defense_in_depth_registry_mutation_is_refused_upstream():
    chain = _base_chain()
    assert _plan_robustness(chain)["entries"][0]["method_id"] == "CONDITIONAL_DESCRIPTIVES_V1"
    for replacement_entry in (
        {
            "method_id": "",
            "parameters": {"trim": "0.0100"},
            "robustness_id": "SYNTH_ROBUSTNESS_1",
        },
        {
            "method_id": "CONDITIONAL_DESCRIPTIVES_V1",
            "parameters": ["trim"],
            "robustness_id": "SYNTH_ROBUSTNESS_1",
        },
    ):
        forged_plan = replace(
            chain.plan,
            robustness_plan=_replace_items(
                chain.plan.robustness_plan, {"entries": _freeze_entry(replacement_entry)}
            ),
        )
        with pytest.raises(AdapterError) as caught:
            _dispatch_with(chain, chain.preparation, forged_plan, ("SYNTH_ROBUSTNESS_1",))
        assert caught.value.code == "CONTRACT_PLAN_MISMATCH"


# --------------------------------------------------------------------------------------------
# AC-13 holdout refusal
# --------------------------------------------------------------------------------------------


def test_ac13_holdout_is_unreachable_by_signature_and_plan():
    chain = _positive_chain()
    for keyword in ("holdout", "window", "split", "real_data"):
        with pytest.raises(TypeError):
            execute_bounded_analysis(
                chain.matrix,
                chain.preparation,
                chain.contract,
                chain.plan,
                chain.bound_inputs,
                **{keyword: None},
            )
        with pytest.raises(TypeError):
            prepare_registered_robustness_dispatch(
                chain.matrix,
                chain.preparation,
                chain.contract,
                chain.plan,
                chain.bound_inputs,
                ("SYNTH_ROBUSTNESS_1",),
                **{keyword: None},
            )

    dates = _dates(POSITIVE_ROWS)
    declared = _scenario(
        dates=dates,
        values=_row_values(len(dates), "noisy"),
        holdout={
            "start": "2023-01-01",
            "end": "2023-12-31",
            "policy_id": "SYNTH_HOLDOUT_1",
            "max_accepted_primary_executions": 1,
        },
    )
    holdout = plan_to_canonical_dict(declared.plan)["holdout_boundary"]
    assert holdout["execution_authorized"] is False
    assert holdout["window"] == {"start": "2023-01-01", "end": "2023-12-31"}
    artifact = _execute(declared)
    assert artifact.provenance.holdout_accessed is False
    assert all(trade_date < "2023-01-01" for trade_date in artifact.sample.trade_dates)

    forged = replace(
        declared.plan,
        holdout_boundary=_replace_items(
            declared.plan.holdout_boundary, {"execution_authorized": True}
        ),
    )
    with pytest.raises(AdapterError) as caught:
        execute_bounded_analysis(
            declared.matrix,
            declared.preparation,
            declared.contract,
            forged,
            declared.bound_inputs,
        )
    assert caught.value.code == "CONTRACT_PLAN_MISMATCH"


# --------------------------------------------------------------------------------------------
# AC-14 permutation, key order and working-directory invariance
# --------------------------------------------------------------------------------------------


def test_ac14_input_permutation_key_order_and_cwd_invariance():
    chain = _positive_chain()
    artifact = _execute(chain)
    reversed_inputs = _bound(
        chain.contract,
        chain.plan,
        replace(chain.bound_inputs, observations=tuple(reversed(chain.bound_inputs.observations))),
    )
    assert reversed_inputs.input_digest == chain.bound_inputs.input_digest
    permuted = _Chain(chain.contract, chain.plan, reversed_inputs, chain.preparation, chain.matrix)
    other = _execute(permuted)
    assert other.artifact_digest == artifact.artifact_digest
    assert serialize_execution_artifact(other) == serialize_execution_artifact(artifact)

    payload = execution_artifact_to_canonical_dict(artifact)
    shuffled = {key: payload[key] for key in reversed(list(payload))}
    assert canonical_digest(shuffled) == artifact.artifact_digest

    previous = os.getcwd()
    try:
        os.chdir(ROOT / "src" / "ashare_research")
        moved = _execute(chain)
    finally:
        os.chdir(previous)
    assert moved.artifact_digest == artifact.artifact_digest
    assert serialize_execution_artifact(moved) == serialize_execution_artifact(artifact)


# --------------------------------------------------------------------------------------------
# AC-15 byte reproducibility and re-execution validation
# --------------------------------------------------------------------------------------------


def test_ac15_byte_reproducibility_roundtrip_and_cross_process():
    chain = _positive_chain()
    first = _execute(chain)
    second = _execute(chain)
    assert serialize_execution_artifact(first) == serialize_execution_artifact(second)
    assert first.artifact_digest == second.artifact_digest

    payload = execution_artifact_to_canonical_dict(first)
    mutated = execution_artifact_to_canonical_dict(first)
    mutated["estimator"]["rank"] = 0
    mutated["sample"]["trade_dates"].append("1999-01-01")
    assert execution_artifact_to_canonical_dict(first) == payload
    encoded = serialize_execution_artifact(first)
    expected = (
        json.dumps(
            {**payload, "artifact_digest": first.artifact_digest},
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n"
    ).encode("utf-8")
    assert encoded == expected
    assert json.loads(encoded.decode("utf-8")) == {
        **payload,
        "artifact_digest": first.artifact_digest,
    }
    assert canonical_digest(payload) == first.artifact_digest
    assert _validate(first, chain) is None

    environment = dict(os.environ)
    environment["PYTHONPATH"] = str(ROOT / "src") + os.pathsep + str(ROOT / "tests")
    completed = subprocess.run(
        [
            sys.executable,
            "-c",
            "from test_m4_bounded_execution import _positive_chain_sha256 as f; print(f())",
        ],
        cwd=ROOT,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert completed.stdout.strip() == hashlib.sha256(encoded).hexdigest()


# --------------------------------------------------------------------------------------------
# AC-16 nested mutations
# --------------------------------------------------------------------------------------------


def test_ac16_nested_mutations_change_every_identity_layer():
    dates = _dates(POSITIVE_ROWS)
    base = _scenario(dates=dates, values=_row_values(len(dates), "noisy"))
    base_artifact = _execute(base)
    base_dispatch = _dispatch(base, ("SYNTH_ROBUSTNESS_1",))

    trimmed = _scenario(
        dates=dates,
        values=_row_values(len(dates), "noisy"),
        registry=[
            {
                "robustness_id": "SYNTH_ROBUSTNESS_1",
                "method_id": "CONDITIONAL_DESCRIPTIVES_V1",
                "parameters": {"trim": "0.0200", "window": [1, 2, 3]},
            }
        ],
    )
    trimmed_artifact = _execute(trimmed)
    assert trimmed.contract.contract_digest != base.contract.contract_digest
    assert trimmed.plan.plan_digest != base.plan.plan_digest
    assert trimmed.preparation.dataset_digest != base.preparation.dataset_digest
    assert trimmed.matrix.matrix_digest != base.matrix.matrix_digest
    assert trimmed_artifact.artifact_digest != base_artifact.artifact_digest
    assert [coefficient.value for coefficient in trimmed_artifact.estimator.coefficients] == [
        coefficient.value for coefficient in base_artifact.estimator.coefficients
    ]

    relaxed = _scenario(
        dates=dates,
        values=_row_values(len(dates), "noisy"),
        evidence={"confidence_requirement": "0.90"},
    )
    relaxed_artifact = _execute(relaxed)
    assert relaxed_artifact.evidence.confidence_requirement == "0.9"
    assert relaxed_artifact.artifact_digest != base_artifact.artifact_digest
    strict = _scenario(
        dates=dates,
        values=_row_values(len(dates), "noisy"),
        evidence={"confidence_requirement": "0.99"},
    )
    strict_artifact = _execute(strict)
    assert strict_artifact.evidence.confidence_requirement_satisfied is False
    assert strict_artifact.artifact_digest != base_artifact.artifact_digest

    reseeded = _scenario(
        dates=dates, values=_row_values(len(dates), "noisy"), bootstrap={"seed": 43}
    )
    reseeded_artifact = _execute(reseeded)
    assert reseeded_artifact.bootstrap.seed == 43
    assert (
        reseeded_artifact.bootstrap.primary_effect_lower
        != base_artifact.bootstrap.primary_effect_lower
    )
    assert reseeded_artifact.artifact_digest != base_artifact.artifact_digest

    windowed = _scenario(
        dates=dates,
        values=_row_values(len(dates), "noisy"),
        registry=[
            {
                "robustness_id": "SYNTH_ROBUSTNESS_1",
                "method_id": "CONDITIONAL_DESCRIPTIVES_V1",
                "parameters": {"trim": "0.0100", "window": [1, 2, 999]},
            }
        ],
    )
    windowed_dispatch = _dispatch(windowed, ("SYNTH_ROBUSTNESS_1",))
    assert windowed_dispatch.entries[0].parameters_canonical_json == (
        '{"trim":"0.0100","window":["1","2","999"]}'
    )
    assert windowed_dispatch.artifact_digest != base_dispatch.artifact_digest
    assert _execute(windowed).artifact_digest != base_artifact.artifact_digest

    with pytest.raises(AdapterError) as caught:
        materialize_analysis_dataset(trimmed.contract, base.plan, base.bound_inputs)
    assert caught.value.code == "CONTRACT_PLAN_MISMATCH"


# --------------------------------------------------------------------------------------------
# AC-17 provenance, interpretation boundary and forbidden content
# --------------------------------------------------------------------------------------------


def test_ac17_synthetic_provenance_and_forbidden_content_rejection():
    chain = _positive_chain()
    artifact = _execute(chain)
    payload = execution_artifact_to_canonical_dict(artifact)
    assert artifact.provenance.provenance_class == "SYNTHETIC_TEST_ONLY"
    assert artifact.provenance.synthetic_test_only is True
    assert artifact.provenance.dataset_mode == "SYNTHETIC"
    assert artifact.provenance.real_data_used is False
    assert artifact.provenance.holdout_accessed is False
    assert artifact.execution_authorized is False
    assert artifact.evidence.interpretation_boundary == INTERPRETATION_BOUNDARY
    assert "Not a research finding" in artifact.evidence.interpretation_boundary
    assert "not an authorization to execute on real data" in (
        artifact.evidence.interpretation_boundary
    )
    assert FORBIDDEN_KEYS.isdisjoint({key.lower() for key in _walk_keys(payload)})
    for scalar in _walk_scalars(payload):
        if type(scalar) is str:
            assert not re.search(r"[A-Za-z]:[\\/]", scalar)
            assert not scalar.startswith("\\\\")
            assert "/" not in scalar
    rendered = serialize_execution_artifact(artifact).decode("utf-8")
    assert "worktree" not in rendered and str(ROOT) not in rendered

    absolute_path = _reforge(
        artifact,
        method_configuration=replace(
            artifact.method_configuration, numeric_runtime="D:/quantified/lab"
        ),
    )
    with pytest.raises(ExecutionError) as caught:
        serialize_execution_artifact(absolute_path)
    assert caught.value.code == "FORBIDDEN_ARTIFACT_CONTENT"

    upgraded = replace(
        artifact, provenance=replace(artifact.provenance, synthetic_test_only=False)
    )
    with pytest.raises(ExecutionError) as caught:
        serialize_execution_artifact(upgraded)
    assert caught.value.code == "INVALID_INPUT_STRUCTURE"

    forbidden_entry = _scenario(
        dates=_dates(3),
        values=_row_values(3, "noisy"),
        registry=[
            {
                "robustness_id": "SYNTH_ROBUSTNESS_1",
                "method_id": "CONDITIONAL_DESCRIPTIVES_V1",
                "parameters": {"best": "1"},
            }
        ],
    )
    with pytest.raises(ExecutionError) as caught:
        _dispatch(forbidden_entry, ("SYNTH_ROBUSTNESS_1",))
    assert caught.value.code == "FORBIDDEN_ARTIFACT_CONTENT"


# --------------------------------------------------------------------------------------------
# AC-18 two-layer identity
# --------------------------------------------------------------------------------------------


def test_ac18a_execution_never_writes_float64_back_upstream():
    chain = _positive_chain()
    before = (
        serialize_dataset(chain.preparation),
        serialize_matrix(chain.matrix),
        chain.plan.plan_digest,
        chain.matrix.matrix_digest,
    )
    artifact = _execute(chain)
    after = (
        serialize_dataset(chain.preparation),
        serialize_matrix(chain.matrix),
        chain.plan.plan_digest,
        chain.matrix.matrix_digest,
    )
    assert before == after
    assert artifact.source_chain.matrix_digest == chain.matrix.matrix_digest
    assert (
        validate_design_matrix(
            chain.matrix, chain.preparation, chain.contract, chain.plan, chain.bound_inputs
        )
        is None
    )


def test_ac18b_all_float64_outputs_are_normalized_and_runtime_is_bound():
    chain = _positive_chain()
    artifact = _execute(chain)
    floats = [
        *[coefficient.value for coefficient in artifact.estimator.coefficients],
        *artifact.estimator.singular_values,
        artifact.estimator.residual_sum_of_squares,
        artifact.estimator.primary_effect,
        artifact.bootstrap.primary_effect_lower,
        artifact.bootstrap.primary_effect_upper,
        *[value.value for value in artifact.conditional_descriptives],
        artifact.evidence.primary_effect,
        artifact.evidence.interval_lower,
        artifact.evidence.interval_upper,
    ]
    floats = [value for value in floats if value is not None]
    assert len(floats) >= 20
    for value in floats:
        assert isinstance(value, Float64ValueV1)
        assert float.hex(float.fromhex(value.float64_hex)) == value.float64_hex
    payload = execution_artifact_to_canonical_dict(artifact)
    assert not any(type(scalar) is float for scalar in _walk_scalars(payload))
    assert artifact.method_configuration.numeric_runtime == numpy.__version__
    rebound = _reforge(
        artifact,
        method_configuration=replace(artifact.method_configuration, numeric_runtime="0.0.0"),
    )
    assert rebound.artifact_digest != artifact.artifact_digest


def test_ac18c_18d_float64_hex_is_part_of_the_primary_identity():
    zero = _execute(_exact_chain("zero", "POSITIVE"))
    coefficient = zero.estimator.coefficients[0]
    assert coefficient.value.canonical_decimal == "0"
    flipped_value = Float64ValueV1(
        "-0x0.0p+0" if coefficient.value.float64_hex != "-0x0.0p+0" else "0x0.0p+0", "0"
    )
    forged_coefficients = (replace(coefficient, value=flipped_value),) + (
        zero.estimator.coefficients[1:]
    )
    forged = _reforge(
        zero, estimator=replace(zero.estimator, coefficients=forged_coefficients)
    )
    assert forged.artifact_digest != zero.artifact_digest
    stale = replace(zero, estimator=replace(zero.estimator, coefficients=forged_coefficients))
    with pytest.raises(ExecutionError) as caught:
        serialize_execution_artifact(stale)
    assert caught.value.code == "ARTIFACT_DIGEST_MISMATCH"

    lower = zero.bootstrap.primary_effect_lower
    flipped_endpoint = Float64ValueV1(
        "-0x0.0p+0" if lower.float64_hex != "-0x0.0p+0" else "0x0.0p+0", "0"
    )
    flipped = _reforge(
        zero,
        bootstrap=replace(zero.bootstrap, primary_effect_lower=flipped_endpoint),
        evidence=replace(zero.evidence, interval_lower=flipped_endpoint),
    )
    assert flipped.evidence.disposition == zero.evidence.disposition
    assert flipped.evidence.disposition_reason == zero.evidence.disposition_reason
    assert flipped.artifact_digest != zero.artifact_digest
    assert serialize_execution_artifact(flipped).endswith(b"\n")


def test_ac18f_18g_dispatch_artifact_binds_no_statistic_but_binds_everything_else():
    chain = _base_chain()
    artifact = _dispatch(chain, ("SYNTH_ROBUSTNESS_1",))
    assert artifact.statistics_computed is False
    payload = robustness_artifact_to_canonical_dict(artifact)
    for absent in ("estimator", "bootstrap", "conditional_descriptives", "evidence", "statistics"):
        assert absent not in payload
    assert not any(type(scalar) is float for scalar in _walk_scalars(payload))

    rebound = _reforge_dispatch(
        artifact, source_chain=replace(artifact.source_chain, matrix_digest="0" * 64)
    )
    assert rebound.artifact_digest != artifact.artifact_digest
    rebound = _reforge_dispatch(
        artifact,
        method_configuration=replace(artifact.method_configuration, numeric_runtime="0.0.0"),
    )
    assert rebound.artifact_digest != artifact.artifact_digest
    rebound = _reforge_dispatch(
        artifact,
        dispatch=replace(artifact.dispatch, registered_ids=("SYNTH_ROBUSTNESS_1", "OTHER")),
    )
    assert rebound.artifact_digest != artifact.artifact_digest
    rebound = _reforge_dispatch(
        artifact, entries=(replace(artifact.entries[0], method_id="OTHER_METHOD"),)
    )
    assert rebound.artifact_digest != artifact.artifact_digest
    rebound = _reforge_dispatch(
        artifact, provenance=replace(artifact.provenance, dataset_mode="REAL")
    )
    assert rebound.artifact_digest != artifact.artifact_digest
    rebound = _reforge_dispatch(
        artifact,
        entries=(
            replace(
                artifact.entries[0],
                parameters_canonical_json='{"trim":"0.0100","window":["1","2","999"]}',
            ),
        ),
    )
    assert rebound.artifact_digest != artifact.artifact_digest
    assert (
        payload["entries"][0]["parameters_canonical_json"]
        == artifact.entries[0].parameters_canonical_json
    )


# --------------------------------------------------------------------------------------------
# AC-19 bootstrap enabled is a strict plan copy (no runtime downgrade)
# --------------------------------------------------------------------------------------------


def test_ac19a_enabled_is_a_strict_copy_and_never_downgrades():
    chain = _positive_chain()
    artifact = _execute(chain)
    declared = _plan_bootstrap(chain)["enabled"]
    assert artifact.bootstrap.enabled is declared is True
    assert artifact.method_configuration.bootstrap_enabled is True
    assert artifact.bootstrap.primary_effect_lower is not None
    assert artifact.bootstrap.primary_effect_upper is not None

    failing = _scenario(
        dates=_dates(POSITIVE_ROWS),
        values=_row_values(POSITIVE_ROWS, "noisy"),
        bootstrap={"replications": 1},
    )
    with pytest.raises(ExecutionError) as caught:
        _execute(failing)
    assert caught.value.code == "INSUFFICIENT_REPLICATIONS"

    singular_resample = _scenario(
        dates=_dates(3),
        values=_row_values(3, "noisy"),
        roles=("TARGET_OUTCOME", "FACTOR"),
        root={"controls": []},
        bootstrap={"replications": 1000},
    )
    assert singular_resample.matrix.columns[-1].term_role == PRIMARY_TERM_ROLE
    with pytest.raises(ExecutionError) as caught:
        _execute(singular_resample)
    assert caught.value.code == "SINGULAR_RESAMPLE"


def test_ac19b_disabled_path_is_explicit_and_never_touches_randomness(monkeypatch):
    dates = _dates(8)
    chain = _scenario(
        dates=dates,
        values=_row_values(len(dates), "noisy"),
        bootstrap={"enabled": False, "method_id": "DISABLED"},
    )

    def forbidden(*args, **kwargs):
        raise AssertionError("randomness API used on the disabled bootstrap path")

    monkeypatch.setattr(execution.numpy.random, "Generator", forbidden)
    monkeypatch.setattr(execution.numpy.random, "PCG64", forbidden)
    artifact = _execute(chain)
    assert artifact.bootstrap.enabled is False
    assert artifact.bootstrap.method_id == "DISABLED"
    for value in (
        artifact.bootstrap.block_length,
        artifact.bootstrap.replications,
        artifact.bootstrap.seed,
        artifact.bootstrap.rng,
        artifact.bootstrap.confidence_level,
        artifact.bootstrap.interval_alpha,
        artifact.bootstrap.lower_index,
        artifact.bootstrap.upper_index,
        artifact.bootstrap.primary_effect_lower,
        artifact.bootstrap.primary_effect_upper,
    ):
        assert value is None
    assert artifact.evidence.bootstrap_confidence_level is None
    assert artifact.evidence.disposition == "INCONCLUSIVE"
    assert artifact.evidence.disposition_reason == "BOOTSTRAP_DISABLED"
    assert _validate(artifact, chain) is None


def test_ac19c_plan_level_pairing_error_propagates_and_is_not_loosened():
    for changes in (
        {"enabled": True, "method_id": "DISABLED"},
        {"enabled": False, "method_id": "MOVING_BLOCK_BOOTSTRAP_V1"},
    ):
        document = _document()
        document["bootstrap_policy"].update(changes)
        with pytest.raises(HypothesisConfigError) as caught:
            parse_hypothesis_config(document)
        assert caught.value.code == "INVALID_BOOTSTRAP_POLICY"
    source = SOURCE_PATH.read_text(encoding="utf-8")
    assert 'elif method_id != DISABLED_BOOTSTRAP_METHOD:' in source
    assert 'if method_id not in ALLOWED_BOOTSTRAP_METHODS:' in source


def test_artifact_field_names_match_the_frozen_schema():
    assert [field.name for field in fields(Float64ValueV1)] == [
        "float64_hex",
        "canonical_decimal",
    ]
    assert [field.name for field in fields(execution.SourceChainV1)] == [
        "contract_digest",
        "plan_digest",
        "input_digest",
        "domain_digest",
        "dataset_digest",
        "matrix_digest",
    ]
    assert [field.name for field in fields(execution.ProvenanceV1)] == [
        "provenance_class",
        "synthetic_test_only",
        "dataset_mode",
        "real_data_used",
        "holdout_accessed",
    ]
    assert [field.name for field in fields(execution.TermRefV1)] == [
        "position",
        "term_role",
        "coefficient_role",
    ]
    assert [field.name for field in fields(execution.MethodConfigurationV1)] == [
        "artifact_schema_version",
        "executor_version",
        "estimator_contract_id",
        "model_family",
        "numeric_backend",
        "numeric_runtime",
        "response_role",
        "terms",
        "primary_effect_position",
        "primary_effect_role",
        "bootstrap_enabled",
        "bootstrap_method_id",
        "block_length_policy_id",
        "bootstrap_replications",
        "bootstrap_seed",
        "bootstrap_rng",
        "bootstrap_confidence_level",
        "evidence_rule_id",
        "evidence_direction",
        "evidence_confidence_requirement",
        "data_quality_failure_disposition",
        "block_length",
    ]
    assert [field.name for field in fields(SampleBlockV1)] == [
        "row_count",
        "trade_dates",
        "coverage_numerator",
        "coverage_denominator",
        "coverage_gate",
        "coverage_gate_satisfied",
        "coverage_complete",
        "missingness_policy",
        "failure_disposition",
        "reason_counts",
        "rejected_dates",
    ]
    assert [field.name for field in fields(CoefficientV1)] == [
        "position",
        "term_role",
        "coefficient_role",
        "value",
    ]
    assert [field.name for field in fields(EstimatorBlockV1)] == [
        "n_rows",
        "n_terms",
        "rank",
        "coefficients",
        "singular_values",
        "residual_sum_of_squares",
        "primary_effect",
    ]
    assert [field.name for field in fields(BootstrapBlockV1)] == [
        "enabled",
        "method_id",
        "block_length",
        "replications",
        "seed",
        "rng",
        "confidence_level",
        "interval_alpha",
        "lower_index",
        "upper_index",
        "primary_effect_lower",
        "primary_effect_upper",
    ]
    assert [field.name for field in fields(StatisticValueV1)] == [
        "role",
        "kind",
        "count",
        "value",
    ]
    assert [field.name for field in fields(EvidenceBlockV1)] == [
        "rule_id",
        "expected_direction",
        "confidence_requirement",
        "data_quality_failure_disposition",
        "bootstrap_confidence_level",
        "confidence_requirement_satisfied",
        "primary_effect_role",
        "primary_effect",
        "interval_lower",
        "interval_upper",
        "disposition",
        "disposition_reason",
        "coverage_complete",
        "interpretation_boundary",
    ]
    assert [field.name for field in fields(execution.ExecutionArtifactV1)] == [
        "artifact_schema_version",
        "executor_version",
        "source_chain",
        "provenance",
        "method_configuration",
        "sample",
        "estimator",
        "bootstrap",
        "conditional_descriptives",
        "evidence",
        "execution_authorized",
        "statistics_computed",
        "outcome_read",
        "artifact_digest",
    ]
    assert [field.name for field in fields(execution.RobustnessEntryDispatchV1)] == [
        "robustness_id",
        "request_ordinal",
        "registration_ordinal",
        "method_id",
        "parameters",
        "parameters_canonical_json",
    ]
    assert [field.name for field in fields(execution.RobustnessDispatchV1)] == [
        "requested_ids",
        "registered_ids",
        "automatic_expansion",
        "automatic_selection",
        "parameters_interpreted",
    ]
    assert [field.name for field in fields(RobustnessArtifactV1)] == [
        "artifact_schema_version",
        "executor_version",
        "source_chain",
        "provenance",
        "method_configuration",
        "sample",
        "dispatch",
        "entries",
        "execution_authorized",
        "statistics_computed",
        "outcome_read",
        "artifact_digest",
    ]


def test_ac05_order_legal_source_with_multiple_defects_and_quality_first():
    chain = _base_chain()
    forged = replace(
        chain.plan,
        analysis_method_id="OTHER_METHOD",
        evidence_plan=_replace_items(
            chain.plan.evidence_plan, {"expected_direction": "SIDEWAYS"}
        ),
    )
    with pytest.raises(AdapterError) as caught:
        execute_bounded_analysis(
            chain.matrix, chain.preparation, chain.contract, forged, chain.bound_inputs
        )
    assert caught.value.code == "CONTRACT_PLAN_MISMATCH"
    assert not isinstance(caught.value, ExecutionError)
    with pytest.raises(AdapterError) as caught:
        execute_bounded_analysis(
            chain.matrix, chain.preparation, chain.contract, forged, chain.bound_inputs
        )
    assert caught.value.code == "CONTRACT_PLAN_MISMATCH"

    dates = _dates(8)
    values = dict(_row_values(len(dates), "noisy"))
    values["CONTROL_0001"] = ("1000001",) + values["CONTROL_0001"][1:]
    rejected = _scenario(
        dates=dates,
        values=values,
        missing=("CONTROL_0002", dates[1]),
        quality={"coverage_gate": "0.99", "missingness_policy": "FAIL_CLOSED"},
        build_matrix=False,
    )
    assert rejected.preparation.status == "REJECTED_QUALITY"
    with pytest.raises(MatrixError) as caught:
        materialize_design_matrix(
            rejected.preparation, rejected.contract, rejected.plan, rejected.bound_inputs
        )
    assert caught.value.code == "DATASET_NOT_READY"
    source = SOURCE_PATH.read_text(encoding="utf-8")
    assert source.index("# X2 --") < source.index("# X4 --") < source.index("# X7 --")


def test_public_entries_do_no_external_io(monkeypatch):
    chain = _positive_chain()
    dispatch_chain = _base_chain()

    def forbidden(*args, **kwargs):
        raise AssertionError("external I/O")

    monkeypatch.setattr("builtins.open", forbidden)
    monkeypatch.setattr(Path, "open", forbidden)
    monkeypatch.setattr(socket, "socket", forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)
    artifact = _execute(chain)
    assert serialize_execution_artifact(artifact).endswith(b"\n")
    dispatched = _dispatch(dispatch_chain, ("SYNTH_ROBUSTNESS_1",))
    assert serialize_robustness_artifact(dispatched).endswith(b"\n")


def test_dispatch_artifact_stale_digest_and_inconsistent_parameters_are_detected():
    chain = _base_chain()
    artifact = _dispatch(chain, ("SYNTH_ROBUSTNESS_1",))
    stale = replace(artifact, entries=(replace(artifact.entries[0], method_id="OTHER"),))
    with pytest.raises(ExecutionError) as caught:
        _validate_dispatch(stale, chain)
    assert caught.value.code == "ARTIFACT_DIGEST_MISMATCH"
    inconsistent = _reforge_dispatch(
        artifact, entries=(replace(artifact.entries[0], parameters_canonical_json="{"),)
    )
    with pytest.raises(ExecutionError) as caught:
        _validate_dispatch(inconsistent, chain)
    assert caught.value.code == "INVALID_INPUT_STRUCTURE"
    forged = _reforge_dispatch(
        artifact, entries=(replace(artifact.entries[0], method_id="OTHER"),)
    )
    with pytest.raises(ExecutionError) as caught:
        _validate_dispatch(forged, chain)
    assert caught.value.code == "IDENTITY_CONFLICT"


def test_artifacts_are_frozen_immutable_and_typed():
    from dataclasses import FrozenInstanceError

    chain = _base_chain()
    artifact = _dispatch(chain, ("SYNTH_ROBUSTNESS_1",))
    with pytest.raises(FrozenInstanceError):
        artifact.statistics_computed = True  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        artifact.entries[0].method_id = "OTHER"  # type: ignore[misc]
    assert isinstance(artifact.entries, tuple)
    assert isinstance(artifact.entries[0].parameters, FrozenJSONObject)
    executed = _execute(_positive_chain())
    assert isinstance(executed.conditional_descriptives, tuple)
    assert isinstance(executed.sample, SampleBlockV1)
    assert isinstance(executed.estimator, EstimatorBlockV1)
    assert isinstance(executed.bootstrap, BootstrapBlockV1)
    assert isinstance(executed.estimator.coefficients[0], CoefficientV1)
    assert isinstance(executed.conditional_descriptives[0], StatisticValueV1)
    assert isinstance(executed.evidence, EvidenceBlockV1)
    assert executed.estimator.residual_sum_of_squares is None or isinstance(
        executed.estimator.residual_sum_of_squares, Float64ValueV1
    )
