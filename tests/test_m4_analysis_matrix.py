"""Acceptance coverage for the frozen M4 synthetic design matrix contract.

Product assertions call the real ``ashare_research.mechanism.planning.matrix`` implementation
and the real adapter/compiler; fixtures are reused from the existing typed-contract and
synthetic-adapter test modules.  No mirror implementation of the production projection is used
as an oracle, no database, provider, real market input or statistic is touched, and every
expected digest is the value measured in ``docs/m4_analysis_matrix_design_v1.md``.
"""

from __future__ import annotations

import ast
import hashlib
import inspect
import re
from dataclasses import FrozenInstanceError, replace
from pathlib import Path

import pytest
from test_m4_stage4a1_typed_contract import _compiled, _document
from test_m4_synthetic_dataset_adapter import _bound, _inputs, _quality, _refresh

from ashare_research.mechanism.datasets import (
    AdapterError,
    BoundDatasetInputsV1,
    ObservationV1,
    RoleBindingV1,
    dataset_to_canonical_dict,
    materialize_analysis_dataset,
    serialize_dataset,
    validate_dataset,
)
from ashare_research.mechanism.datasets.synthetic import _input_payload
from ashare_research.mechanism.model_digest import canonical_digest
from ashare_research.mechanism.planning import build_analysis_plan, plan_to_canonical_dict
from ashare_research.mechanism.planning import matrix as matrix_module
from ashare_research.mechanism.planning.matrix import (
    MatrixError,
    materialize_design_matrix,
    matrix_to_canonical_dict,
    serialize_matrix,
    validate_design_matrix,
)

DATES = ("2020-01-02", "2020-01-03", "2020-01-06")
CONTROL_ROLES = ("CONTROL_0001", "CONTROL_0002")

CONTRACT_DIGEST = "ee450d1f23cc68fb88718f3aa607cdda0c5e0d2b3fe951eddcb6e9b7b007f457"
PLAN_DIGEST = "45a2461708863a8f4e9cb92f7774d2ffd1084558950c8f421838174059e21981"
INPUT_DIGEST = "c1f6c3d74066ee944dab4a56752da8b30ba8c647c3980a9051298c066409c602"
DOMAIN_DIGEST = "b78882e43d745e2095b55688ac1ea68da25fdd1c971cea9c77f50924c0e100da"
DATASET_DIGEST = "c3410933652b992c798ec981d7a25da91ad7816b10d396468e87f34efc28879b"
MATRIX_DIGEST = "a3c40269f34d4414b177fd3ed512798934443aeeb6cae2a218d426b2641e822a"
SERIALIZED_SHA256 = "70d9926e0bec6e440b8c692384cd67f4c03727e7fd7ee602affc009000b187fa"

BASE_ROWS = (
    ("2020-01-02", ("1", "-0.02", "0.01", "0.01", "1")),
    ("2020-01-03", ("1", "-0.01", "0.02", "0.02", "1")),
    ("2020-01-06", ("1", "0", "0.03", "0.03", "0")),
)
CANONICAL_DECIMAL_RE = re.compile(r"-?(0|[1-9][0-9]*)(\.[0-9]*[1-9])?")


def _base():
    contract = _compiled()
    plan = build_analysis_plan(contract)
    inputs = _bound(contract, plan, _inputs())
    preparation = materialize_analysis_dataset(contract, plan, inputs)
    return contract, plan, inputs, preparation


def _base_case():
    contract, plan, inputs, preparation = _base()
    matrix = materialize_design_matrix(preparation, contract, plan, inputs)
    return contract, plan, inputs, preparation, matrix


def _document_with(section: str, **changes):
    document = _document()
    document[section].update(changes)
    return document


def _scenario(*, gate=None, missingness=None, missing=None):
    contract = _compiled()
    if gate is not None or missingness is not None:
        contract = _quality(contract, gate=gate, missingness=missingness)
    plan = build_analysis_plan(contract)
    inputs = _bound(contract, plan, _inputs(missing))
    return contract, plan, inputs, materialize_analysis_dataset(contract, plan, inputs)


def _keep_roles(inputs, roles):
    return replace(
        inputs,
        bindings=tuple(binding for binding in inputs.bindings if binding.role in roles),
        observations=tuple(
            observation for observation in inputs.observations if observation.role in roles
        ),
    )


def _rebind(inputs):
    """Rebuild evidence digests after bindings change, leaving values untouched."""
    bindings = {binding.role: binding for binding in inputs.bindings}
    rows = []
    for row in inputs.observations:
        binding = bindings[row.role]
        payload = {
            "role": row.role,
            "trade_date": row.trade_date,
            "value": row.value,
            "available_on": row.available_on,
            "source_record_id": row.source_record_id,
            "binding": {k: getattr(binding, k) for k in binding.__dataclass_fields__},
        }
        rows.append(replace(row, evidence_digest=canonical_digest(payload)))
    return replace(inputs, observations=tuple(rows))


def _observation(role, series, trade_date, value):
    binding = RoleBindingV1(
        role,
        series,
        "DAILY_RETURN",
        "DECIMAL_RETURN",
        "SYNTHETIC_DECLARED_RETURN",
        None,
        "1D",
        "CLOSE_TO_CLOSE",
    )
    payload = {
        "role": role,
        "trade_date": trade_date,
        "value": value,
        "available_on": trade_date,
        "source_record_id": f"SRC_{role}_{trade_date}",
        "binding": {k: getattr(binding, k) for k in binding.__dataclass_fields__},
    }
    observation = ObservationV1(
        role, trade_date, value, trade_date, payload["source_record_id"], canonical_digest(payload)
    )
    return binding, observation


def _with_extra_control(inputs, role, series, values):
    pairs = zip(DATES, values, strict=True)
    rows = [_observation(role, series, trade_date, value) for trade_date, value in pairs]
    binding = rows[0][0]
    return replace(
        inputs,
        bindings=(*inputs.bindings, binding),
        observations=(*inputs.observations, *(observation for _, observation in rows)),
    )


def _rehash_preparation(preparation):
    payload = dataset_to_canonical_dict(preparation)
    payload.pop("dataset_digest")
    return replace(preparation, dataset_digest=canonical_digest(payload))


def _rehash_matrix(matrix):
    return replace(matrix, matrix_digest=canonical_digest(matrix_to_canonical_dict(matrix)))


def test_base_matrix_exact_shape_identity_and_serialized_bytes() -> None:
    contract, plan, inputs, preparation, matrix = _base_case()
    assert preparation.dataset_digest == DATASET_DIGEST
    assert (matrix.matrix_schema_version, matrix.builder_version) == (
        "M4_DESIGN_MATRIX_V1",
        "M4_DAILY_CONDITIONAL_DESIGN_MATRIX_V1",
    )
    assert matrix.source_contract_digest == preparation.source_contract_digest
    assert matrix.source_contract_digest == contract.contract_digest == CONTRACT_DIGEST
    assert matrix.plan_digest == preparation.plan_digest == PLAN_DIGEST
    assert matrix.input_digest == preparation.input_digest == inputs.input_digest == INPUT_DIGEST
    assert matrix.domain_digest == preparation.domain_digest == DOMAIN_DIGEST
    assert matrix.dataset_digest == preparation.dataset_digest == DATASET_DIGEST
    assert matrix.role_order == ("TARGET_OUTCOME", "FACTOR", "CONTROL_0001", "CONTROL_0002")
    assert [(c.position, c.term_role) for c in matrix.columns] == [
        (1, "INTERCEPT"),
        (2, "FACTOR_CONTINUOUS"),
        (3, "CONTROL_0001"),
        (4, "CONTROL_0002"),
        (5, "CONDITION_INDICATOR"),
    ]
    assert [c.coefficient_role for c in matrix.columns] == [
        "alpha",
        "beta_factor",
        "beta_control_0001",
        "beta_control_0002",
        "gamma_condition",
    ]
    assert [c.source_role for c in matrix.columns] == [
        None,
        "FACTOR",
        "CONTROL_0001",
        "CONTROL_0002",
        "CONDITION_INDICATOR",
    ]
    assert matrix.response_role == "TARGET_OUTCOME"
    assert matrix.response_role == plan_to_canonical_dict(plan)["design_plan"]["response_role"]
    assert [(row.trade_date, row.cells) for row in matrix.rows] == list(BASE_ROWS)
    assert matrix.matrix_digest == MATRIX_DIGEST
    assert hashlib.sha256(serialize_matrix(matrix)).hexdigest() == SERIALIZED_SHA256
    assert validate_design_matrix(matrix, preparation, contract, plan, inputs) is None


def test_canonical_payload_is_exactly_the_frozen_shape() -> None:
    _, _, _, _, matrix = _base_case()
    payload = matrix_to_canonical_dict(matrix)
    assert set(payload) == {
        "matrix_schema_version",
        "builder_version",
        "source_contract_digest",
        "plan_digest",
        "input_digest",
        "domain_digest",
        "dataset_digest",
        "role_order",
        "columns",
        "response_role",
        "rows",
        "quality",
        "execution_authorized",
        "statistics_computed",
    }
    # The self digest is emitted only by serialize_matrix and never enters its own digest.
    assert "matrix_digest" not in payload
    assert payload["quality"] == {
        "status": "READY_SYNTHETIC",
        "coverage_numerator": 3,
        "coverage_denominator": 3,
        "coverage_gate": "0.99",
        "missingness_policy": "FAIL_CLOSED",
        "failure_disposition": "INCONCLUSIVE",
        "reason_counts": {},
        "rejected_dates": [],
    }
    serialized = serialize_matrix(matrix)
    assert serialized.endswith(b"\n") and serialized.count(b"\n") == 1
    assert serialized == serialized.decode("utf-8").encode("utf-8")
    assert b"\\u" not in serialized
    assert b'"matrix_digest":"' + MATRIX_DIGEST.encode() + b'"' in serialized
    assert b"row_count" not in serialized and b"column_count" not in serialized
    assert b"column_roles" not in serialized


def test_no_control_plan_projects_exactly_three_columns() -> None:
    document = _document()
    document["controls"] = []
    contract = _compiled(document)
    plan = build_analysis_plan(contract)
    inputs = _bound(contract, plan, _keep_roles(_inputs(), {"TARGET_OUTCOME", "FACTOR"}))
    preparation = materialize_analysis_dataset(contract, plan, inputs)
    matrix = materialize_design_matrix(preparation, contract, plan, inputs)
    assert preparation.role_order == ("TARGET_OUTCOME", "FACTOR")
    assert [c.term_role for c in matrix.columns] == [
        "INTERCEPT",
        "FACTOR_CONTINUOUS",
        "CONDITION_INDICATOR",
    ]
    assert [c.coefficient_role for c in matrix.columns] == [
        "alpha",
        "beta_factor",
        "gamma_condition",
    ]
    assert preparation.dataset_digest == (
        "e0e52d46f078be3993e759b27c8bb84e71c3a590001282ef63eb1d02aff6728f"
    )
    assert matrix.matrix_digest == (
        "f6df25c471bc1a60f6f48c4863f30791388d26461b3210228a118975e5505db8"
    )
    assert [row.cells for row in matrix.rows] == [
        ("1", "-0.02", "1"),
        ("1", "-0.01", "1"),
        ("1", "0", "0"),
    ]


def test_three_controls_grow_the_matrix_to_six_columns() -> None:
    document = _document()
    document["controls"] = ["SYNTH_CONTROL_1", "SYNTH_CONTROL_2", "SYNTH_CONTROL_3"]
    contract = _compiled(document)
    plan = build_analysis_plan(contract)
    inputs = _with_extra_control(
        _inputs(), "CONTROL_0003", "SYNTH_CONTROL_3", ("0.04", "0.05", "0.06")
    )
    inputs = _bound(contract, plan, inputs)
    preparation = materialize_analysis_dataset(contract, plan, inputs)
    matrix = materialize_design_matrix(preparation, contract, plan, inputs)
    assert len(matrix.columns) == len(plan_to_canonical_dict(plan)["design_plan"]["ordered_terms"])
    assert [c.term_role for c in matrix.columns] == [
        "INTERCEPT",
        "FACTOR_CONTINUOUS",
        "CONTROL_0001",
        "CONTROL_0002",
        "CONTROL_0003",
        "CONDITION_INDICATOR",
    ]
    assert [c.coefficient_role for c in matrix.columns][-2:] == [
        "beta_control_0003",
        "gamma_condition",
    ]
    assert preparation.dataset_digest == (
        "4c0603288b168b067b9a117744ffba38c3e6a81a0be9668511702140f31bec0f"
    )
    assert matrix.matrix_digest == (
        "13c1830672434e1d6a56ae8a3548ab106b6baab86295b792a242e2f4b43f115e"
    )
    assert [row.cells for row in matrix.rows] == [
        ("1", "-0.02", "0.01", "0.01", "0.04", "1"),
        ("1", "-0.01", "0.02", "0.02", "0.05", "1"),
        ("1", "0", "0.03", "0.03", "0.06", "0"),
    ]


def test_reversed_control_registration_order_changes_identity_not_rows() -> None:
    document = _document()
    document["controls"] = ["SYNTH_CONTROL_2", "SYNTH_CONTROL_1"]
    contract = _compiled(document)
    plan = build_analysis_plan(contract)
    swapped = tuple(
        replace(
            binding,
            series_id={
                "SYNTH_CONTROL_1": "SYNTH_CONTROL_2",
                "SYNTH_CONTROL_2": "SYNTH_CONTROL_1",
            }[binding.series_id],
        )
        if binding.role in CONTROL_ROLES
        else binding
        for binding in _inputs().bindings
    )
    inputs = _bound(contract, plan, _rebind(replace(_inputs(), bindings=swapped)))
    preparation = materialize_analysis_dataset(contract, plan, inputs)
    matrix = materialize_design_matrix(preparation, contract, plan, inputs)
    assert inputs.input_digest == (
        "4a863864e3760a094a7d634c133aa3abe5badaf21f98d266372f08df992ae822"
    )
    assert preparation.role_order == ("TARGET_OUTCOME", "FACTOR", *CONTROL_ROLES)
    assert preparation.dataset_digest == (
        "d4cddef0269825e3d040d3170aeab323c6c42c6c0e2e61c21c02f57bea8b1e94"
    )
    assert matrix.matrix_digest == (
        "48f8a5b3930ecfad3abd29830d744ad8ec7cf368a130408d65f3fd90eab37f4f"
    )
    assert [row.cells for row in matrix.rows] == [cells for _, cells in BASE_ROWS]
    assert matrix.matrix_digest != MATRIX_DIGEST


@pytest.mark.parametrize(
    ("operator", "plan_digest", "indicators", "matrix_digest"),
    [
        (
            "LT",
            "44207cc23c608a0e33634a79db5810175a665409d3703296812e84ee3a8bab79",
            ("1", "1", "0"),
            "6b7687e32235393081554702b010b93958aa8fb92a27352ff0237e7f417cbff7",
        ),
        (
            "LTE",
            "798955e8c4987cdfe8b067f19d59454039f728aad67ebeaa44bb41e38481bedf",
            ("1", "1", "1"),
            "a862e23b64ea7f928d81f2442d83c7439853bc714c601d70a5a8ca6374a170ee",
        ),
        (
            "GT",
            "f4030af6d69f6009970c12ee895822837cab590c4ac5da256595da5aa88006f4",
            ("0", "0", "0"),
            "7b1703457786f09c1caaab0b801c55bdb6cb94b709d20dfee8759416f5775183",
        ),
        (
            "GTE",
            "f32b071c6c69afac21a6d6d1f95e7d9aaa3453b2d6d314802503374d8f544b41",
            ("0", "0", "1"),
            "7fbfcf8f3c5f196a0e06ab8e8ce514a371f4757aaa0dc6c3810d87b5c608d610",
        ),
    ],
)
def test_condition_operator_boundaries_are_exact_at_zero(
    operator: str, plan_digest: str, indicators: tuple[str, str, str], matrix_digest: str
) -> None:
    document = _document_with("condition", operator=operator, threshold="0")
    contract = _compiled(document)
    plan = build_analysis_plan(contract)
    inputs = _bound(contract, plan, _inputs())
    matrix = materialize_design_matrix(
        materialize_analysis_dataset(contract, plan, inputs), contract, plan, inputs
    )
    assert plan.plan_digest == plan_digest
    assert plan_to_canonical_dict(plan)["transform_plan"]["condition"]["threshold"] == "0"
    assert tuple(row.cells[-1] for row in matrix.rows) == indicators
    assert matrix.matrix_digest == matrix_digest


@pytest.mark.parametrize(
    ("operator", "indicators", "matrix_digest"),
    [
        ("LT", ("1", "0", "0"), "9d0c1f0986f4b7d78a5212bf25e11e6883d2ed58c1ef54b3fe1e88333fb7a49a"),
        ("LTE", ("1", "1", "0"), MATRIX_DIGEST),
        (
            "GT",
            ("0", "0", "1"),
            "e228c48e4b4c4b1b4bf3e50adb1fa719cade7a88f5db0a755169e9710ec77374",
        ),
        (
            "GTE",
            ("0", "1", "1"),
            "7a093d21de861de1e073eab51a66b9e82072f9021545361dacfa0ccbe271d1e0",
        ),
    ],
)
def test_condition_threshold_is_normalized_without_float_tolerance(
    operator: str, indicators: tuple[str, str, str], matrix_digest: str
) -> None:
    document = _document_with("condition", operator=operator, threshold="-0.0100")
    contract = _compiled(document)
    plan = build_analysis_plan(contract)
    inputs = _bound(contract, plan, _inputs())
    matrix = materialize_design_matrix(
        materialize_analysis_dataset(contract, plan, inputs), contract, plan, inputs
    )
    assert plan_to_canonical_dict(plan)["transform_plan"]["condition"]["threshold"] == "-0.01"
    assert tuple(row.cells[-1] for row in matrix.rows) == indicators
    assert matrix.matrix_digest == matrix_digest


@pytest.mark.parametrize(
    ("role", "trade_date", "dataset_digest", "matrix_digest"),
    [
        (
            "CONTROL_0002",
            "2020-01-03",
            "aff29dfda78a5db0a0a3fe4095eff7edb6211e0f084c774c1c14fcc40ae8d198",
            "09a1af5f1dd323522e5b628f57245fb0287e551d19ff6d96f5a9214f1065812e",
        ),
        (
            "CONTROL_0002",
            "2020-01-02",
            "f85b4a3701ee92be4ad86b9f31f9a123d2d06b1639ad07983efc421ee245dec8",
            "6e46e2a0bd3ba74bb2701dc465c889ca489c1d8cc3cab153accfcd1d601addac",
        ),
        (
            "CONTROL_0001",
            "2020-01-03",
            "e684cab7263b5d1491ec586ecb3241b2a9f88e293dd8ce8d84b5297613701557",
            "d995c832df5798f4fcd08b68f592f102a29b16342b148a57463378e627821d9d",
        ),
        (
            "TARGET_OUTCOME",
            "2020-01-03",
            "38b5d6ccb8008e9d1aa976949c735aa0a92c2115dc2f67de188746969c2f6910",
            "3c3b4158c7845e855b57c25e56509f104f3e4e14f58c065fe9a2d06510e05272",
        ),
        (
            "FACTOR",
            "2020-01-03",
            "8303d7e0fa0dc2d4c8ace978f85633ce6e63eb6c07e67abd714bfeb75932e27f",
            "5734473dd3f051351bbeae6647faf85f28f17ef5d79d9c62f7c64e7474a5a245",
        ),
    ],
)
def test_missing_rows_keep_the_denominator_and_a_distinct_identity(
    role: str, trade_date: str, dataset_digest: str, matrix_digest: str
) -> None:
    contract, plan, inputs, preparation = _scenario(
        gate="0.66", missingness="RETAIN_IN_DENOMINATOR", missing=(role, trade_date)
    )
    matrix = materialize_design_matrix(preparation, contract, plan, inputs)
    assert preparation.status == "READY_SYNTHETIC"
    assert (preparation.quality.coverage_numerator, preparation.quality.coverage_denominator) == (
        2,
        3,
    )
    assert matrix.quality.coverage_denominator == 3
    assert len(matrix.rows) == 2
    assert [row.trade_date for row in matrix.rows] == [
        date for date in DATES if date != trade_date
    ]
    assert preparation.dataset_digest == dataset_digest
    assert matrix.matrix_digest == matrix_digest


def test_exact_gate_comparison_separates_0_66_from_0_67() -> None:
    ready_contract, ready_plan, ready_inputs, ready = _scenario(
        gate="0.66", missingness="RETAIN_IN_DENOMINATOR", missing=("CONTROL_0002", "2020-01-03")
    )
    assert ready.status == "READY_SYNTHETIC"
    assert ready.quality.coverage_gate == "0.66"
    rejected_contract, rejected_plan, rejected_inputs, rejected = _scenario(
        gate="0.67", missingness="RETAIN_IN_DENOMINATOR", missing=("CONTROL_0002", "2020-01-03")
    )
    assert rejected.status == "REJECTED_QUALITY"
    assert rejected.dataset_digest == (
        "d1d287f7f0d657d8a36866e5392224c875cbcc5b647d43a8b31e38d48515487c"
    )
    ready_matrix = materialize_design_matrix(ready, ready_contract, ready_plan, ready_inputs)
    assert ready_matrix.quality.coverage_numerator == 2
    with pytest.raises(MatrixError) as caught:
        materialize_design_matrix(rejected, rejected_contract, rejected_plan, rejected_inputs)
    assert caught.value.code == "DATASET_NOT_READY"


@pytest.mark.parametrize(
    ("available_on", "reason", "dataset_digest", "matrix_digest"),
    [
        (
            None,
            "PIT_UNPROVEN",
            "5cc29781d464871d217dc7d9317a5c9443549c8c2a99c02557fba0f80847c559",
            "52298a8c57c01fc152497bd547e1e70c882b0a3b12c98fd8ab78c2fcb6a0b7ef",
        ),
        (
            "2020-01-06",
            "PIT_NOT_AVAILABLE",
            "09dea69c1998be598d8d266f4277dca35b39c37976d80132affc62da35120337",
            "fce3d11e2bda79fdcfc8a099f953d406e2fea7317b1546a5b05782797ddcdc5b",
        ),
    ],
)
def test_pit_invisible_rows_are_reasoned_and_identity_bearing(
    available_on: str | None, reason: str, dataset_digest: str, matrix_digest: str
) -> None:
    contract, plan, _, _ = _scenario(gate="0.66", missingness="RETAIN_IN_DENOMINATOR")
    rows = [
        replace(row, available_on=available_on)
        if (row.role, row.trade_date) == ("CONTROL_0002", "2020-01-03")
        else row
        for row in _inputs().observations
    ]
    inputs = _bound(contract, plan, replace(_inputs(), observations=_refresh(rows)))
    preparation = materialize_analysis_dataset(contract, plan, inputs)
    matrix = materialize_design_matrix(preparation, contract, plan, inputs)
    assert dict(preparation.quality.reason_counts) == {reason: 1}
    assert preparation.quality.rejected_dates == ("2020-01-03",)
    assert [row.trade_date for row in matrix.rows] == ["2020-01-02", "2020-01-06"]
    assert preparation.dataset_digest == dataset_digest
    assert matrix.matrix_digest == matrix_digest


@pytest.mark.parametrize(
    ("gate", "missingness", "value"),
    [
        ("0.99", "FAIL_CLOSED", "present"),
        ("0.66", "FAIL_CLOSED", "present"),
        ("0.99", "FAIL_CLOSED", None),
        ("0.67", "RETAIN_IN_DENOMINATOR", "present"),
    ],
)
def test_rejected_quality_never_returns_a_partial_matrix(
    gate: str, missingness: str, value: str | None
) -> None:
    if value is None:
        contract, plan, _, _ = _scenario()
        rows = [
            replace(row, value=None)
            if (row.role, row.trade_date) == ("CONTROL_0002", "2020-01-03")
            else row
            for row in _inputs().observations
        ]
        inputs = _bound(contract, plan, replace(_inputs(), observations=_refresh(rows)))
        preparation = materialize_analysis_dataset(contract, plan, inputs)
    else:
        contract, plan, inputs, preparation = _scenario(
            gate=gate, missingness=missingness, missing=("CONTROL_0002", "2020-01-03")
        )
    # A rejected preparation is a legal adapter product and passes source verification.
    validate_dataset(preparation, contract, plan, inputs)
    assert preparation.status == "REJECTED_QUALITY"
    assert preparation.complete_rows == ()
    with pytest.raises(MatrixError) as caught:
        materialize_design_matrix(preparation, contract, plan, inputs)
    assert caught.value.code == "DATASET_NOT_READY"
    assert type(caught.value) is MatrixError


def test_self_consistent_source_tamper_is_rejected_before_projection() -> None:
    contract, plan, inputs, preparation = _base()
    tampered = _rehash_preparation(
        replace(
            preparation,
            complete_rows=tuple(
                (trade_date, values, 1 - indicator)
                for trade_date, values, indicator in preparation.complete_rows
            ),
        )
    )
    assert tampered.dataset_digest == (
        "721584843f0f10448b0e1aecc28cc30a52018844be4c5852923c0acdab57b79f"
    )
    # The serializer accepts the self-consistent tamper; only the four-argument entry rejects it.
    assert serialize_dataset(tampered).endswith(b"\n")
    with pytest.raises(AdapterError) as caught:
        validate_dataset(tampered, contract, plan, inputs)
    assert (type(caught.value), caught.value.code) == (AdapterError, "IDENTITY_CONFLICT")
    with pytest.raises(AdapterError) as caught:
        materialize_design_matrix(tampered, contract, plan, inputs)
    assert (type(caught.value), caught.value.code) == (AdapterError, "IDENTITY_CONFLICT")


def test_forged_matrix_without_digest_refresh_fails_the_structure_stage() -> None:
    contract, plan, inputs, preparation, matrix = _base_case()
    date, cells = matrix.rows[0].trade_date, matrix.rows[0].cells
    forged = replace(
        matrix,
        rows=(replace(matrix.rows[0], cells=(cells[0], cells[1], cells[2], cells[3], "0")),)
        + matrix.rows[1:],
    )
    assert forged.matrix_digest == matrix.matrix_digest
    with pytest.raises(MatrixError) as caught:
        validate_design_matrix(forged, preparation, contract, plan, inputs)
    assert (type(caught.value), caught.value.code) == (MatrixError, "MATRIX_DIGEST_MISMATCH")
    with pytest.raises(MatrixError) as caught:
        serialize_matrix(forged)
    assert caught.value.code == "MATRIX_DIGEST_MISMATCH"
    assert date == "2020-01-02"


def test_rehashed_forged_matrix_fails_the_reprojection_stage() -> None:
    contract, plan, inputs, preparation, matrix = _base_case()
    cells = matrix.rows[0].cells
    forged = _rehash_matrix(
        replace(
            matrix,
            rows=(replace(matrix.rows[0], cells=(cells[0], cells[1], cells[2], cells[3], "0")),)
            + matrix.rows[1:],
        )
    )
    assert forged.matrix_digest == canonical_digest(matrix_to_canonical_dict(forged))
    # The object is self-consistent, so the structure stage passes and only the byte
    # comparison against the reprojection rejects it.
    with pytest.raises(MatrixError) as caught:
        validate_design_matrix(forged, preparation, contract, plan, inputs)
    assert (type(caught.value), caught.value.code) == (MatrixError, "IDENTITY_CONFLICT")
    shifted_control = _rehash_matrix(
        replace(
            matrix,
            rows=(
                replace(
                    matrix.rows[0],
                    cells=(*matrix.rows[0].cells[:2], "0.02", *matrix.rows[0].cells[3:]),
                ),
                *matrix.rows[1:],
            ),
        )
    )
    with pytest.raises(MatrixError) as caught:
        validate_design_matrix(shifted_control, preparation, contract, plan, inputs)
    assert caught.value.code == "IDENTITY_CONFLICT"


def test_rehashed_bound_inputs_are_rejected_by_the_source_gate() -> None:
    contract, plan, inputs, preparation = _base()
    rows = [
        replace(row, value="-0.05")
        if (row.role, row.trade_date) == ("FACTOR", "2020-01-03")
        else row
        for row in _inputs().observations
    ]
    rehashed_inputs = _bound(contract, plan, replace(_inputs(), observations=_refresh(rows)))
    rehashed = materialize_analysis_dataset(contract, plan, rehashed_inputs)
    assert rehashed_inputs.input_digest == (
        "e877c147b58b53ee3283e87bcce49592470643c161e7a675af1e06a51943b464"
    )
    assert rehashed.dataset_digest == (
        "2788e8ec06d370a3020b99fecbdcb4d7cb30d7568dbea33d0f22a63a063a7aea"
    )
    with pytest.raises(AdapterError) as caught:
        validate_dataset(rehashed, contract, plan, inputs)
    assert (type(caught.value), caught.value.code) == (AdapterError, "IDENTITY_CONFLICT")
    with pytest.raises(AdapterError) as caught:
        materialize_design_matrix(rehashed, contract, plan, inputs)
    assert (type(caught.value), caught.value.code) == (AdapterError, "IDENTITY_CONFLICT")


def test_nested_contract_change_moves_identity_but_not_cells() -> None:
    _, _, _, base_preparation, base_matrix = _base_case()
    document = _document()
    document["robustness_registry"][0]["parameters"]["trim"] = "0.0200"
    contract = _compiled(document)
    plan = build_analysis_plan(contract)
    inputs = _bound(contract, plan, _inputs())
    preparation = materialize_analysis_dataset(contract, plan, inputs)
    matrix = materialize_design_matrix(preparation, contract, plan, inputs)
    assert contract.contract_digest == (
        "f4c193cbbc9a32e9bc7d17bf9ba494c7702fc46acd3c723102d025e8084eed9f"
    )
    assert plan.plan_digest == (
        "8833ed844a7f50d9665945b7d18c07d2e1d72bde97b13cf8aeefcad24e2cc677"
    )
    assert plan_to_canonical_dict(plan)["robustness_plan"]["entries"][0]["parameters"][
        "trim"
    ] == "0.0200"
    assert preparation.dataset_digest == (
        "dfa395bb1dff0c694cad4d8cc3438d07c2896f92bdb72d20fdbcfe663eaf5c6d"
    )
    assert matrix.matrix_digest == (
        "b75877ee489f1a08bdcbbcc6fa0f0c57a9a1e1fcc940844ca04ea5ea7c2ddd5e"
    )
    assert matrix.matrix_digest != base_matrix.matrix_digest
    assert [row.cells for row in matrix.rows] == [row.cells for row in base_matrix.rows]
    assert base_preparation.dataset_digest != preparation.dataset_digest
    _, base_plan, base_inputs, _ = _base()
    with pytest.raises(AdapterError) as caught:
        materialize_design_matrix(preparation, contract, base_plan, base_inputs)
    assert (type(caught.value), caught.value.code) == (AdapterError, "CONTRACT_PLAN_MISMATCH")


def test_observation_permutation_and_roundtrip_preserve_identity() -> None:
    contract, plan, inputs, preparation, matrix = _base_case()
    permuted_inputs = _bound(
        contract, plan, replace(_inputs(), observations=tuple(reversed(_inputs().observations)))
    )
    permuted = materialize_design_matrix(
        materialize_analysis_dataset(contract, plan, permuted_inputs),
        contract,
        plan,
        permuted_inputs,
    )
    assert permuted_inputs.input_digest == inputs.input_digest
    assert permuted.matrix_digest == matrix.matrix_digest
    assert serialize_matrix(permuted) == serialize_matrix(matrix)
    payload = _input_payload(inputs)
    payload["input_digest"] = canonical_digest(
        {key: value for key, value in payload.items() if key != "input_digest"}
    )
    restored = BoundDatasetInputsV1.from_dict(payload)
    restored_matrix = materialize_design_matrix(
        materialize_analysis_dataset(contract, plan, restored), contract, plan, restored
    )
    assert restored_matrix.matrix_digest == matrix.matrix_digest
    assert serialize_matrix(restored_matrix) == serialize_matrix(matrix)


def test_key_order_and_working_directory_do_not_change_identity(monkeypatch) -> None:
    contract, plan, inputs, preparation, matrix = _base_case()
    payload = dict(matrix_to_canonical_dict(matrix))
    payload["matrix_digest"] = matrix.matrix_digest
    shuffled = {
        key: payload[key]
        for key in sorted(payload, key=lambda name: hashlib.sha256(name.encode()).hexdigest())
    }
    assert canonical_digest(
        {key: value for key, value in shuffled.items() if key != "matrix_digest"}
    ) == matrix.matrix_digest
    monkeypatch.chdir(Path(matrix_module.__file__).resolve().parents[2])
    elsewhere = materialize_design_matrix(
        materialize_analysis_dataset(contract, plan, inputs), contract, plan, inputs
    )
    assert elsewhere.dataset_digest == preparation.dataset_digest
    assert elsewhere.matrix_digest == matrix.matrix_digest
    assert serialize_matrix(elsewhere) == serialize_matrix(matrix)
    serialized = serialize_matrix(matrix)
    assert b"D:" not in serialized and b"D:\\\\" not in serialized
    assert b"worktree" not in serialized and b"hostname" not in serialized


@pytest.mark.parametrize("value", ["0", "0.01", "1", "-0.01"])
def test_canonical_decimal_values_are_accepted_by_the_source_layer(value: str) -> None:
    observation = ObservationV1("FACTOR", "2020-01-02", value, "2020-01-02", "SRC", "0" * 64)
    assert observation.value == value


@pytest.mark.parametrize("value", ["-0", "0.0", "0.0100", "1E-2", "1.0"])
def test_non_canonical_values_are_rejected_and_never_repaired(value: str) -> None:
    with pytest.raises(AdapterError) as caught:
        ObservationV1("FACTOR", "2020-01-02", value, "2020-01-02", "SRC", "0" * 64)
    assert (type(caught.value), caught.value.code) == (AdapterError, "INVALID_VALUE")


def test_matrix_cells_are_canonical_decimals_copied_without_reformatting() -> None:
    _, _, _, preparation, matrix = _base_case()
    factor_index = matrix.role_order.index("FACTOR")
    for row, (_, values, _) in zip(matrix.rows, preparation.complete_rows, strict=True):
        assert row.cells[0] == "1"
        assert row.cells[-1] in ("0", "1")
        assert row.cells[1] == values[factor_index]
        for cell in row.cells:
            assert CANONICAL_DECIMAL_RE.fullmatch(cell) is not None
            assert cell == str(cell)


@pytest.mark.parametrize("indicator", [True, False, "1"])
def test_boolean_and_text_indicators_are_rejected_at_source_construction(indicator) -> None:
    _, _, _, preparation = _base()
    trade_date, values, _ = preparation.complete_rows[0]
    with pytest.raises(AdapterError) as caught:
        replace(
            preparation,
            complete_rows=((trade_date, values, indicator), *preparation.complete_rows[1:]),
        )
    assert (type(caught.value), caught.value.code) == (AdapterError, "INVALID_INPUT_STRUCTURE")


@pytest.mark.parametrize("indicator", [2, -1])
def test_out_of_range_indicators_are_rejected_not_repaired(indicator: int) -> None:
    contract, plan, inputs, preparation = _base()
    trade_date, values, _ = preparation.complete_rows[0]
    tampered = replace(
        preparation,
        complete_rows=((trade_date, values, indicator), *preparation.complete_rows[1:]),
    )
    with pytest.raises(AdapterError) as caught:
        materialize_design_matrix(tampered, contract, plan, inputs)
    assert (type(caught.value), caught.value.code) == (AdapterError, "INVALID_INPUT_STRUCTURE")


def test_non_canonical_complete_row_value_is_rejected_not_repaired() -> None:
    contract, plan, inputs, preparation = _base()
    trade_date, values, indicator = preparation.complete_rows[0]
    tampered = replace(
        preparation,
        complete_rows=(
            (trade_date, ("0.0100", *values[1:]), indicator),
            *preparation.complete_rows[1:],
        ),
    )
    with pytest.raises(AdapterError) as caught:
        materialize_design_matrix(tampered, contract, plan, inputs)
    assert (type(caught.value), caught.value.code) == (AdapterError, "INVALID_INPUT_STRUCTURE")


def _unsupported_mode(contract, plan, inputs, preparation):
    return (preparation, contract, plan, replace(inputs, mode="REAL"))


def _bad_input_digest(contract, plan, inputs, preparation):
    return (preparation, contract, plan, replace(inputs, input_digest="0" * 64))


def _duplicate_observation(contract, plan, inputs, preparation):
    return (
        preparation,
        contract,
        plan,
        replace(inputs, observations=inputs.observations + (inputs.observations[0],)),
    )


def _zero_evidence_digest(contract, plan, inputs, preparation):
    return (
        preparation,
        contract,
        plan,
        replace(
            inputs,
            observations=(replace(inputs.observations[0], evidence_digest="0" * 64),)
            + inputs.observations[1:],
        ),
    )


def _out_of_domain(contract, plan, inputs, preparation):
    return (
        preparation,
        contract,
        plan,
        replace(
            inputs,
            observations=(replace(inputs.observations[0], trade_date="2023-01-03"),)
            + inputs.observations[1:],
        ),
    )


def _other_contract(contract, plan, inputs, preparation):
    other = _compiled(_document_with("condition", threshold="-0.02"))
    return (preparation, other, plan, inputs)


@pytest.mark.parametrize(
    ("builder", "expected_code"),
    [
        (_unsupported_mode, "UNSUPPORTED_MODE"),
        (_bad_input_digest, "INPUT_DIGEST_MISMATCH"),
        (_duplicate_observation, "DUPLICATE_OBSERVATION"),
        (_zero_evidence_digest, "EVIDENCE_DIGEST_MISMATCH"),
        (_out_of_domain, "OUT_OF_DOMAIN"),
        (_other_contract, "CONTRACT_PLAN_MISMATCH"),
    ],
)
def test_upstream_adapter_errors_propagate_unchanged(builder, expected_code: str) -> None:
    contract, plan, inputs, preparation = _base()
    with pytest.raises(AdapterError) as caught:
        materialize_design_matrix(*builder(contract, plan, inputs, preparation))
    assert type(caught.value) is AdapterError
    assert caught.value.code == expected_code


def test_validation_order_prefers_source_errors_over_the_quality_gate() -> None:
    _, plan, inputs, rejected = _scenario(
        gate="0.99", missingness="FAIL_CLOSED", missing=("CONTROL_0002", "2020-01-03")
    )
    assert rejected.status == "REJECTED_QUALITY"
    other = _compiled(_document_with("condition", threshold="-0.02"))
    with pytest.raises(AdapterError) as caught:
        materialize_design_matrix(rejected, other, plan, inputs)
    assert (type(caught.value), caught.value.code) == (AdapterError, "CONTRACT_PLAN_MISMATCH")
    contract, plan, inputs, preparation, matrix = _base_case()
    stale = replace(
        matrix,
        rows=(
            replace(matrix.rows[0], cells=(*matrix.rows[0].cells[:-1], "0")),
            *matrix.rows[1:],
        ),
    )
    tampered = _rehash_preparation(
        replace(
            preparation,
            complete_rows=tuple(
                (trade_date, values, 1 - indicator)
                for trade_date, values, indicator in preparation.complete_rows
            ),
        )
    )
    with pytest.raises(MatrixError) as caught:
        validate_design_matrix(stale, tampered, contract, plan, inputs)
    assert caught.value.code == "MATRIX_DIGEST_MISMATCH"
    with pytest.raises(AdapterError) as caught:
        validate_design_matrix(_rehash_matrix(stale), tampered, contract, plan, inputs)
    assert (type(caught.value), caught.value.code) == (AdapterError, "IDENTITY_CONFLICT")


def test_rows_columns_and_response_role_invariants() -> None:
    contract, plan, inputs, preparation, matrix = _base_case()
    ordered_terms = plan_to_canonical_dict(plan)["design_plan"]["ordered_terms"]
    assert len(matrix.columns) == len(ordered_terms)
    assert len(matrix.rows) == len(preparation.complete_rows)
    assert [row.trade_date for row in matrix.rows] == [
        trade_date for trade_date, _, _ in preparation.complete_rows
    ]
    assert [row.trade_date for row in matrix.rows] == sorted(inputs.domain.expected_dates)
    assert [column.position for column in matrix.columns] == list(
        range(1, len(matrix.columns) + 1)
    )
    assert all(len(row.cells) == len(matrix.columns) for row in matrix.rows)
    assert [column.term_role for column in matrix.columns] == [
        "INTERCEPT",
        "FACTOR_CONTINUOUS",
        *(role for role in preparation.role_order if role.startswith("CONTROL_")),
        "CONDITION_INDICATOR",
    ]
    assert matrix.response_role == "TARGET_OUTCOME"
    assert matrix.response_role in matrix.role_order
    assert matrix.response_role not in [column.term_role for column in matrix.columns]
    assert "beta_target_outcome" not in [column.coefficient_role for column in matrix.columns]


def test_quality_block_inherits_preparation_facts_without_rejudgement() -> None:
    contract, plan, inputs, preparation = _scenario(
        gate="0.66", missingness="RETAIN_IN_DENOMINATOR", missing=("CONTROL_0002", "2020-01-03")
    )
    matrix = materialize_design_matrix(preparation, contract, plan, inputs)
    assert matrix.quality.status == preparation.status == "READY_SYNTHETIC"
    assert matrix.quality.coverage_numerator == preparation.quality.coverage_numerator == 2
    assert matrix.quality.coverage_numerator == len(matrix.rows)
    assert matrix.quality.coverage_denominator == preparation.quality.coverage_denominator == 3
    assert matrix.quality.coverage_gate == preparation.quality.coverage_gate == "0.66"
    assert matrix.quality.missingness_policy == preparation.quality.missingness_policy
    assert matrix.quality.missingness_policy == "RETAIN_IN_DENOMINATOR"
    assert matrix.quality.failure_disposition == preparation.quality.failure_disposition
    assert matrix.quality.failure_disposition == "INCONCLUSIVE"
    assert matrix.quality.reason_counts == preparation.quality.reason_counts
    assert matrix.quality.reason_counts == (("MISSING_OBSERVATION", 1),)
    assert matrix.quality.rejected_dates == preparation.quality.rejected_dates == ("2020-01-03",)
    assert set(matrix_to_canonical_dict(matrix)["quality"]) == {
        "status",
        "coverage_numerator",
        "coverage_denominator",
        "coverage_gate",
        "missingness_policy",
        "failure_disposition",
        "reason_counts",
        "rejected_dates",
    }


def test_no_success_state_carries_execution_authorization() -> None:
    _, plan, _, _, matrix = _base_case()
    assert matrix.execution_authorized is False
    assert matrix.statistics_computed is False
    assert type(matrix.execution_authorized) is bool
    assert type(matrix.statistics_computed) is bool
    assert plan_to_canonical_dict(plan)["holdout_boundary"]["execution_authorized"] is False


def test_matrix_is_frozen_and_the_canonical_dict_is_a_defensive_copy() -> None:
    _, _, _, _, matrix = _base_case()
    assert isinstance(matrix.rows, tuple) and isinstance(matrix.columns, tuple)
    assert isinstance(matrix.rows[0].cells, tuple)
    assert isinstance(matrix.quality.reason_counts, tuple)
    with pytest.raises(FrozenInstanceError):
        matrix.matrix_digest = "0" * 64  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        matrix.columns[0].term_role = "OTHER"  # type: ignore[misc]
    with pytest.raises(TypeError):
        matrix.rows[0].cells[0] = "9"  # type: ignore[index]
    snapshot = matrix_to_canonical_dict(matrix)
    payload = matrix_to_canonical_dict(matrix)
    payload["rows"][0]["cells"][0] = "9"
    payload["columns"].append({"position": 99})
    payload["role_order"].append("EXTRA")
    payload["quality"]["reason_counts"]["TAMPERED"] = 1
    payload["quality"]["rejected_dates"].append("2020-01-09")
    assert matrix_to_canonical_dict(matrix) == snapshot
    assert snapshot["rows"][0]["cells"][0] == "1"
    assert matrix.rows[0].cells[0] == "1"
    assert len(matrix.columns) == 5
    assert matrix.role_order == ("TARGET_OUTCOME", "FACTOR", "CONTROL_0001", "CONTROL_0002")
    assert matrix.quality.reason_counts == ()
    assert matrix.quality.rejected_dates == ()
    assert hashlib.sha256(serialize_matrix(matrix)).hexdigest() == SERIALIZED_SHA256


def _forge(matrix, **changes):
    return replace(matrix, **changes)


def _drop_columns(matrix):
    return _forge(matrix, columns=())


def _shift_position(matrix):
    return _forge(
        matrix, columns=(replace(matrix.columns[0], position=7), *matrix.columns[1:])
    )


def _swap_term_role(matrix):
    return _forge(
        matrix, columns=(matrix.columns[0], replace(matrix.columns[1], term_role="CONTROL_0002"),
                         *matrix.columns[2:])
    )


def _unknown_term_role(matrix):
    return _forge(
        matrix, columns=(matrix.columns[0], replace(matrix.columns[1], term_role="SPLINE_X"),
                         *matrix.columns[2:])
    )


def _foreign_response_role(matrix):
    return _forge(matrix, response_role="OTHER_OUTCOME")


def _short_row(matrix):
    return _forge(matrix, rows=(replace(matrix.rows[0], cells=("1", "0")), *matrix.rows[1:]))


def _non_canonical_cell(matrix):
    return _forge(
        matrix,
        rows=(
            replace(matrix.rows[0], cells=("1", "-0.0200", "0.01", "0.01", "1")),
            *matrix.rows[1:],
        ),
    )


def _bad_intercept_cell(matrix):
    head = matrix.rows[0]
    return _forge(
        matrix, rows=(replace(head, cells=("2", *head.cells[1:])), *matrix.rows[1:])
    )


def _bad_condition_cell(matrix):
    head = matrix.rows[0]
    return _forge(
        matrix, rows=(replace(head, cells=(*head.cells[:-1], "2")), *matrix.rows[1:])
    )


def _descending_rows(matrix):
    return _forge(matrix, rows=matrix.rows[::-1])


def _list_cells(matrix):
    head = matrix.rows[0]
    return _forge(matrix, rows=(replace(head, cells=list(head.cells)), *matrix.rows[1:]))


def _wrong_version(matrix):
    return _forge(matrix, matrix_schema_version="M4_DESIGN_MATRIX_V0")


def _bad_digest_field(matrix):
    return _forge(matrix, dataset_digest="Z" * 64)


def _authorized_flag(matrix):
    return _forge(matrix, execution_authorized=True)


def _statistics_flag(matrix):
    return _forge(matrix, statistics_computed=True)


def _impossible_counts(matrix):
    return _forge(matrix, quality=replace(matrix.quality, coverage_numerator=9))


def _rejected_with_rows(matrix):
    return _forge(matrix, quality=replace(matrix.quality, status="REJECTED_QUALITY"))


def _bad_gate(matrix):
    return _forge(matrix, quality=replace(matrix.quality, coverage_gate="1.0"))


def _bad_policy(matrix):
    return _forge(matrix, quality=replace(matrix.quality, missingness_policy="RETAIN"))


@pytest.mark.parametrize(
    "forge",
    [
        _drop_columns,
        _shift_position,
        _swap_term_role,
        _unknown_term_role,
        _foreign_response_role,
        _short_row,
        _non_canonical_cell,
        _bad_intercept_cell,
        _bad_condition_cell,
        _descending_rows,
        _list_cells,
        _wrong_version,
        _bad_digest_field,
        _authorized_flag,
        _statistics_flag,
        _impossible_counts,
        _rejected_with_rows,
        _bad_gate,
        _bad_policy,
    ],
)
def test_structurally_forged_matrices_are_rejected_as_invalid(forge) -> None:
    contract, plan, inputs, preparation, matrix = _base_case()
    forged = forge(matrix)
    with pytest.raises(MatrixError) as caught:
        validate_design_matrix(forged, preparation, contract, plan, inputs)
    assert type(caught.value) is MatrixError
    assert caught.value.code == "INVALID_INPUT_STRUCTURE"


def test_module_exposes_only_the_frozen_public_surface() -> None:
    assert list(inspect.signature(materialize_design_matrix).parameters) == [
        "preparation",
        "contract",
        "plan",
        "bound_inputs",
    ]
    assert list(inspect.signature(validate_design_matrix).parameters) == [
        "matrix",
        "preparation",
        "contract",
        "plan",
        "bound_inputs",
    ]
    assert list(inspect.signature(matrix_to_canonical_dict).parameters) == ["matrix"]
    assert list(inspect.signature(serialize_matrix).parameters) == ["matrix"]
    assert "_project_validated_matrix" not in matrix_module.__all__
    assert matrix_module._project_validated_matrix.__name__.startswith("_")
    assert "materialize_design_matrix" in matrix_module.__all__
    own_functions = {
        name: member
        for name, member in inspect.getmembers(matrix_module, inspect.isfunction)
        if member.__module__ == matrix_module.__name__
    }
    public_functions = {
        name: member for name, member in own_functions.items() if not name.startswith("_")
    }
    assert set(public_functions) == {
        "materialize_design_matrix",
        "matrix_to_canonical_dict",
        "serialize_matrix",
        "validate_design_matrix",
    }
    assert not any(
        list(inspect.signature(member).parameters) == ["preparation"]
        for member in public_functions.values()
    )


def test_module_imports_no_statistics_database_or_provider_dependency() -> None:
    tree = ast.parse(Path(matrix_module.__file__).read_text(encoding="utf-8"))
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            modules.add(node.module)
    assert modules == {
        "__future__",
        "json",
        "re",
        "dataclasses",
        "datetime",
        "decimal",
        "types",
        "typing",
        "ashare_research.mechanism.datasets.synthetic",
        "ashare_research.mechanism.model_digest",
        "ashare_research.mechanism.planning",
    }
    assert {name.split(".")[0] for name in modules}.isdisjoint(
        {"pandas", "numpy", "scipy", "statsmodels", "duckdb", "sqlite3", "requests", "socket"}
    )
