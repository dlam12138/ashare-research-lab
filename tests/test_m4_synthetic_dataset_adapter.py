"""Focused acceptance coverage for the bounded synthetic M4 adapter."""

import hashlib
import socket
from dataclasses import replace
from pathlib import Path

import pytest
from test_m4_stage4a1_typed_contract import _compiled, _document

from ashare_research.mechanism.contract_compiler import compute_contract_digest
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
from ashare_research.mechanism.datasets.synthetic import _domain_dict, _input_payload
from ashare_research.mechanism.model_digest import canonical_digest
from ashare_research.mechanism.planning import build_analysis_plan

DATES = ("2020-01-02", "2020-01-03", "2020-01-06")
ROLES = ("TARGET_OUTCOME", "FACTOR", "CONTROL_0001", "CONTROL_0002")
SERIES = ("SYNTH_TARGET_A", "SYNTH_FACTOR_A", "SYNTH_CONTROL_1", "SYNTH_CONTROL_2")


def _domain():
    cal = {
        "evidence_kind": "SYNTHETIC_CALENDAR_V1",
        "domain_id": "SYNTH_DOMAIN_A",
        "development_start": "2020-01-01",
        "development_end": "2022-12-31",
        "expected_dates": list(DATES),
    }
    mem = {
        "evidence_kind": "SYNTHETIC_FIXED_MEMBERSHIP_V1",
        "universe_id": "SYNTH_UNIVERSE_A",
        "target_series_id": "SYNTH_TARGET_A",
        "expected_dates": list(DATES),
    }
    cal["evidence_digest"] = canonical_digest({k: v for k, v in cal.items()})
    mem["evidence_digest"] = canonical_digest({k: v for k, v in mem.items()})
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
            "expected_dates": list(DATES),
            "calendar_evidence": cal,
            "membership_evidence": mem,
        }
    )


def _inputs(missing=None, *, mode="SYNTHETIC"):
    bindings = tuple(
        RoleBindingV1(
            r,
            s,
            "DAILY_RETURN",
            "DECIMAL_RETURN",
            "SYNTHETIC_DECLARED_RETURN",
            "SYNTH_DAILY_RETURN" if r == "TARGET_OUTCOME" else None,
            "1D",
            "CLOSE_TO_CLOSE",
        )
        for r, s in zip(ROLES, SERIES, strict=True)
    )
    values = {
        "TARGET_OUTCOME": ("0.01", "0.02", "0.03"),
        "FACTOR": ("-0.02", "-0.01", "0"),
        "CONTROL_0001": ("0.01", "0.02", "0.03"),
        "CONTROL_0002": ("0.01", "0.02", "0.03"),
    }
    rows = []
    for role in ROLES:
        for i, td in enumerate(DATES):
            if missing == (role, td):
                continue
            value = values[role][i]
            payload = {
                "role": role,
                "trade_date": td,
                "value": value,
                "available_on": td,
                "source_record_id": f"SRC_{role}_{td}",
                "binding": {
                    k: getattr(bindings[ROLES.index(role)], k)
                    for k in bindings[ROLES.index(role)].__dataclass_fields__
                },
            }
            rows.append(
                ObservationV1(
                    role, td, value, td, payload["source_record_id"], canonical_digest(payload)
                )
            )
    base = BoundDatasetInputsV1(
        "M4_BOUND_SYNTHETIC_DATASET_V1",
        mode,
        "contract",
        "plan",
        _domain(),
        bindings,
        tuple(rows),
        "",
    )
    return replace(
        base,
        input_digest=canonical_digest(
            {
                "schema_version": base.schema_version,
                "mode": base.mode,
                "source_contract_digest": base.source_contract_digest,
                "plan_digest": base.plan_digest,
                "domain": _domain_dict(base.domain),
                "bindings": [{k: getattr(b, k) for k in b.__dataclass_fields__} for b in bindings],
                "observations": [
                    {k: getattr(o, k) for k in o.__dataclass_fields__}
                    for o in sorted(rows, key=lambda o: (o.trade_date, ROLES.index(o.role)))
                ],
            }
        ),
    )


def _bound(contract, plan, inputs):
    bound = replace(
        inputs, source_contract_digest=contract.contract_digest, plan_digest=plan.plan_digest
    )
    return replace(bound, input_digest=canonical_digest(_input_payload(bound)))


def _rehash_output(preparation):
    payload = dataset_to_canonical_dict(preparation)
    payload.pop("dataset_digest")
    return replace(preparation, dataset_digest=canonical_digest(payload))


def _scenario(**changes):
    contract = _compiled()
    for field, value in changes.items():
        contract = replace(contract, **{field: value})
    contract = replace(contract, contract_digest=compute_contract_digest(contract))
    return contract, build_analysis_plan(contract)


def _quality(contract, *, gate=None, missingness=None):
    document = _document()
    document["data_quality_gates"]["coverage_gate"] = (
        gate or document["data_quality_gates"]["coverage_gate"]
    )
    document["data_quality_gates"]["missingness_policy"] = (
        missingness or document["data_quality_gates"]["missingness_policy"]
    )
    return _compiled(document)


def _refresh(rows):
    binding = {b.role: b for b in _inputs().bindings}
    result = []
    for row in rows:
        payload = {
            "role": row.role,
            "trade_date": row.trade_date,
            "value": row.value,
            "available_on": row.available_on,
            "source_record_id": row.source_record_id,
            "binding": {
                k: getattr(binding[row.role], k) for k in binding[row.role].__dataclass_fields__
            },
        }
        result.append(replace(row, evidence_digest=canonical_digest(payload)))
    return tuple(result)


def test_full_materialization_golden_shape_and_canonical_bytes():
    contract = _compiled()
    plan = build_analysis_plan(contract)
    data = _bound(contract, plan, _inputs())
    # rebuild input digest after binding fields are changed
    raw = materialize_analysis_dataset(contract, plan, data)
    assert raw.status == "READY_SYNTHETIC"
    assert raw.quality.coverage_numerator == 3
    assert [r[2] for r in raw.complete_rows] == [1, 1, 0]
    assert serialize_dataset(raw).endswith(b"\n")
    assert serialize_dataset(raw) == serialize_dataset(
        materialize_analysis_dataset(contract, plan, data)
    )


def test_fixed_golden_input_output_and_serialized_sha256():
    contract = _compiled()
    plan = build_analysis_plan(contract)
    data = _bound(contract, plan, _inputs())
    raw = materialize_analysis_dataset(contract, plan, data)
    assert data.input_digest == "c1f6c3d74066ee944dab4a56752da8b30ba8c647c3980a9051298c066409c602"
    assert raw.dataset_digest == "c3410933652b992c798ec981d7a25da91ad7816b10d396468e87f34efc28879b"
    assert (
        hashlib.sha256(serialize_dataset(raw)).hexdigest()
        == "32533abc2e9cefc7f0fe66923afc9a3f5d6ca5b0def7d1228c33ead8d071a060"
    )


def test_cwd_and_from_dict_order_invariance(tmp_path, monkeypatch):
    contract = _compiled()
    plan = build_analysis_plan(contract)
    data = _bound(contract, plan, _inputs())
    payload = _input_payload(data)
    payload["input_digest"] = canonical_digest(
        {k: v for k, v in payload.items() if k != "input_digest"}
    )
    restored = BoundDatasetInputsV1.from_dict(payload)
    monkeypatch.chdir(tmp_path)
    assert serialize_dataset(
        materialize_analysis_dataset(contract, plan, restored)
    ) == serialize_dataset(materialize_analysis_dataset(contract, plan, data))


def test_missing_rows_retain_denominator_and_fail_closed_quality():
    contract = _compiled()
    plan = build_analysis_plan(contract)
    data = _bound(contract, plan, _inputs(("CONTROL_0002", DATES[1])))
    raw = materialize_analysis_dataset(contract, plan, data)
    assert raw.quality.coverage_denominator == 3
    assert raw.quality.coverage_numerator == 2
    assert raw.status == "REJECTED_QUALITY"


def test_domain_and_observation_errors_fail_closed():
    contract = _compiled()
    plan = build_analysis_plan(contract)
    data = _bound(contract, plan, _inputs())
    with pytest.raises(AdapterError):
        materialize_analysis_dataset(contract, plan, replace(data, mode="REAL"))
    with pytest.raises(AdapterError):
        materialize_analysis_dataset(
            contract, plan, replace(data, observations=data.observations + (data.observations[0],))
        )


def test_output_rehash_and_validate_bind_to_original_inputs():
    contract = _compiled()
    plan = build_analysis_plan(contract)
    data = _bound(contract, plan, _inputs())
    with pytest.raises(AdapterError):
        materialize_analysis_dataset(contract, plan, replace(data, input_digest="0" * 64))


def test_defensive_domain_copy_and_exact_gate():
    contract = _compiled()
    plan = build_analysis_plan(contract)
    raw = dict(_domain().calendar_evidence.as_dict())
    raw["x"] = 1
    assert "x" not in _domain().calendar_evidence.as_dict()
    assert build_analysis_plan(contract).plan_digest == plan.plan_digest


@pytest.mark.parametrize("trade_date", ["20200102", "2020-W01-4", "2020-02-30"])
def test_direct_observation_rejects_noncanonical_dates(trade_date):
    with pytest.raises(AdapterError) as err:
        ObservationV1("FACTOR", trade_date, "0.01", None, "SRC", "0" * 64)
    assert err.value.code == "INVALID_DATE"


@pytest.mark.parametrize("value", [True, 0.01, "0.0100", "NaN", "Infinity"])
def test_direct_observation_rejects_invalid_values(value):
    with pytest.raises(AdapterError) as err:
        ObservationV1("FACTOR", DATES[0], value, None, "SRC", "0" * 64)
    assert err.value.code == "INVALID_VALUE"


def test_direct_input_rejects_mutable_nested_sequences_and_unknown_none():
    with pytest.raises(AdapterError):
        BoundDatasetInputsV1(
            "M4_BOUND_SYNTHETIC_DATASET_V1", "SYNTHETIC", "a" * 64, "b" * 64, _domain(), [], (), ""
        )
    with pytest.raises(AdapterError) as err:
        materialize_analysis_dataset(None, None, None)
    assert err.value.code == "INVALID_INPUT_STRUCTURE"


def test_unknown_role_and_tampered_evidence_are_rejected_by_public_api():
    contract = _compiled()
    plan = build_analysis_plan(contract)
    data = _bound(contract, plan, _inputs())
    bad = replace(
        data, observations=(replace(data.observations[0], role="UNKNOWN"),) + data.observations[1:]
    )
    with pytest.raises(AdapterError) as err:
        materialize_analysis_dataset(contract, plan, bad)
    assert err.value.code == "ROLE_BINDING_MISMATCH"


@pytest.mark.parametrize(
    "gate, expected", [("0.66", "READY_SYNTHETIC"), ("0.67", "REJECTED_QUALITY")]
)
def test_retain_denominator_gate_boundary(gate, expected):
    contract, plan = _scenario()
    contract = _quality(contract, gate=gate, missingness="RETAIN_IN_DENOMINATOR")
    contract = replace(contract, contract_digest=compute_contract_digest(contract))
    plan = build_analysis_plan(contract)
    raw = materialize_analysis_dataset(
        contract, plan, _bound(contract, plan, _inputs(("CONTROL_0002", DATES[1])))
    )
    assert raw.status == expected and raw.quality.coverage_numerator == 2


def test_null_and_pit_gaps_are_retained_and_reasoned():
    contract, plan = _scenario()
    for mutation, reason in [(replace(_inputs().observations[0], value=None), "MISSING_VALUE")]:
        rows = list(_inputs().observations)
        rows[rows.index(_inputs().observations[0])] = mutation
        data = _bound(contract, plan, replace(_inputs(), observations=_refresh(rows)))
        raw = materialize_analysis_dataset(contract, plan, data)
        assert reason in dict(raw.quality.reason_counts)
    rows = list(_inputs().observations)
    idx = next(
        i for i, row in enumerate(rows) if row.role == "CONTROL_0002" and row.trade_date == DATES[1]
    )
    rows[idx] = replace(rows[idx], available_on=None)
    raw = materialize_analysis_dataset(
        contract, plan, _bound(contract, plan, replace(_inputs(), observations=_refresh(rows)))
    )
    assert "PIT_UNPROVEN" in dict(raw.quality.reason_counts)


def test_all_rows_absent_and_full_day_absent_retain_domain_denominator():
    contract, plan = _scenario()
    all_missing = _inputs()
    raw = materialize_analysis_dataset(
        contract, plan, _bound(contract, plan, replace(all_missing, observations=()))
    )
    assert raw.quality.coverage_denominator == 3 and raw.quality.coverage_numerator == 0
    rows = tuple(row for row in _inputs().observations if row.trade_date != DATES[1])
    raw = materialize_analysis_dataset(
        contract, plan, _bound(contract, plan, replace(_inputs(), observations=rows))
    )
    assert raw.quality.coverage_denominator == 3 and raw.quality.coverage_numerator == 2


@pytest.mark.parametrize(
    "operator, expected",
    [("LT", [1, 0, 0]), ("LTE", [1, 1, 0]), ("GT", [0, 0, 1]), ("GTE", [0, 1, 1])],
)
def test_condition_operators_are_exact(operator, expected):
    document = _document()
    document["condition"]["operator"] = operator
    contract = _compiled(document)
    plan = build_analysis_plan(contract)
    raw = materialize_analysis_dataset(contract, plan, _bound(contract, plan, _inputs()))
    assert [r[2] for r in raw.complete_rows] == expected


def test_source_tamper_conflict_shared_series_and_unknown_mode():
    contract, plan = _scenario()
    data = _bound(contract, plan, _inputs())
    with pytest.raises(AdapterError) as err:
        materialize_analysis_dataset(contract, plan, replace(data, mode="REAL"))
    assert err.value.code == "UNSUPPORTED_MODE"
    with pytest.raises(AdapterError) as err:
        materialize_analysis_dataset(
            contract,
            plan,
            replace(
                data,
                observations=(replace(data.observations[0], evidence_digest="0" * 64),)
                + data.observations[1:],
            ),
        )
    assert err.value.code == "EVIDENCE_DIGEST_MISMATCH"


def test_output_rehash_mutations_are_rejected_by_serializer():
    contract, plan = _scenario()
    raw = materialize_analysis_dataset(contract, plan, _bound(contract, plan, _inputs()))
    for changed in [
        _rehash_output(replace(raw, status="BAD")),
        _rehash_output(replace(raw, complete_rows=())),
        _rehash_output(replace(raw, complete_rows=((DATES[0], ("9",) * 4, 1),))),
    ]:
        with pytest.raises(AdapterError):
            serialize_dataset(changed)


def test_validate_dataset_rejects_changed_indicator_even_after_output_rehash():
    contract, plan = _scenario()
    data = _bound(contract, plan, _inputs())
    raw = materialize_analysis_dataset(contract, plan, data)
    changed = _rehash_output(
        replace(
            raw,
            complete_rows=tuple(
                (d, vals, 1 - indicator) for d, vals, indicator in raw.complete_rows
            ),
        )
    )
    with pytest.raises(AdapterError):
        from ashare_research.mechanism.datasets import validate_dataset

        validate_dataset(changed, contract, plan, data)


@pytest.mark.parametrize(
    "field, value, expected",
    [
        ("horizon", "5D", "UNSUPPORTED_OUTCOME"),
        ("transform_semantics", "STANDARDIZED", "UNSUPPORTED_BINDING_POLICY"),
    ],
)
def test_unsupported_contract_policies_fail_closed(field, value, expected):
    document = _document()
    section = "outcome" if field == "horizon" else "factor"
    document[section][field] = value
    contract = _compiled(document)
    plan = build_analysis_plan(contract)
    with pytest.raises(AdapterError) as err:
        materialize_analysis_dataset(contract, plan, _bound(contract, plan, _inputs()))
    assert err.value.code == expected


def test_key_and_row_order_are_semantically_invariant():
    contract, plan = _scenario()
    left = materialize_analysis_dataset(contract, plan, _bound(contract, plan, _inputs()))
    shuffled = _inputs()
    right = materialize_analysis_dataset(
        contract,
        plan,
        _bound(
            contract, plan, replace(shuffled, observations=tuple(reversed(shuffled.observations)))
        ),
    )
    assert serialize_dataset(left) == serialize_dataset(right)


def test_materialize_and_serialize_perform_no_external_io(monkeypatch):
    contract, plan = _scenario()
    data = _bound(contract, plan, _inputs())

    def forbidden(*args, **kwargs):
        raise AssertionError("external I/O")

    monkeypatch.setattr("builtins.open", forbidden)
    monkeypatch.setattr(Path, "open", forbidden)
    monkeypatch.setattr(socket, "socket", forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)
    raw = materialize_analysis_dataset(contract, plan, data)
    assert serialize_dataset(raw).endswith(b"\n")


def test_holdout_or_out_of_domain_observation_is_rejected():
    contract, plan = _scenario()
    row = _inputs().observations[0]
    outside = replace(row, trade_date="2023-01-03")
    with pytest.raises(AdapterError) as err:
        materialize_analysis_dataset(
            contract,
            plan,
            _bound(
                contract,
                plan,
                replace(_inputs(), observations=_refresh((outside,) + _inputs().observations[1:])),
            ),
        )
    assert err.value.code == "OUT_OF_DOMAIN"


def test_output_rejects_boolean_counters_and_fake_validity_reasons():
    contract, plan = _scenario()
    raw = materialize_analysis_dataset(contract, plan, _bound(contract, plan, _inputs()))
    with pytest.raises(AdapterError):
        bad_quality = replace(raw.quality, coverage_numerator=True)
        serialize_dataset(replace(raw, quality=bad_quality))
    with pytest.raises(AdapterError):
        fake = replace(raw.audit_rows[0].cells[0], valid=True, reasons=("MISSING_VALUE",))
        serialize_dataset(
            replace(
                raw,
                audit_rows=(
                    replace(raw.audit_rows[0], cells=(fake,) + raw.audit_rows[0].cells[1:]),
                ),
            )
        )
