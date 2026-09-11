"""Independent review regressions for the synthetic adapter's trust boundaries."""

import sys
from copy import deepcopy
from dataclasses import FrozenInstanceError, replace

import pytest
from test_m4_stage4a1_typed_contract import _compiled, _document
from test_m4_synthetic_dataset_adapter import _bound, _inputs

from ashare_research.mechanism.datasets import (
    AdapterError,
    BoundDatasetInputsV1,
    dataset_to_canonical_dict,
    materialize_analysis_dataset,
    serialize_dataset,
    validate_dataset,
)
from ashare_research.mechanism.datasets.synthetic import _input_payload
from ashare_research.mechanism.model_digest import canonical_digest
from ashare_research.mechanism.planning import build_analysis_plan, compute_plan_digest


def _bundle(document=None):
    contract = _compiled(document)
    plan = build_analysis_plan(contract)
    data = _input_payload(_bound(contract, plan, _inputs()))
    data["input_digest"] = canonical_digest(data)
    return contract, plan, data


def _seal(data):
    """Independently construct synthetic evidence, not using adapter internals."""
    for field in ("calendar_evidence", "membership_evidence"):
        evidence = data["domain"][field]
        evidence["evidence_digest"] = canonical_digest(
            {key: value for key, value in evidence.items() if key != "evidence_digest"}
        )
    bindings = {b["role"]: b for b in data["bindings"]}
    order = {b["role"]: i for i, b in enumerate(data["bindings"])}
    for row in data["observations"]:
        payload = {key: value for key, value in row.items() if key != "evidence_digest"}
        row["evidence_digest"] = canonical_digest({**payload, "binding": bindings[row["role"]]})
    data["observations"].sort(key=lambda row: (row["trade_date"], order[row["role"]]))
    data["input_digest"] = canonical_digest(
        {key: value for key, value in data.items() if key != "input_digest"}
    )
    return data


def _rehash(output):
    payload = dataset_to_canonical_dict(output)
    del payload["dataset_digest"]
    return replace(output, dataset_digest=canonical_digest(payload))


@pytest.mark.parametrize("conflict", [None, "source_record_id", "value", "available_on"])
def test_same_series_alias_requires_consistent_source_and_allows_valid_reuse(conflict):
    document = _document()
    document["controls"][0] = document["target"]["series_id"]
    contract, plan, data = _bundle(document)
    data["bindings"][2]["series_id"] = document["target"]["series_id"]
    targets = {
        row["trade_date"]: row for row in data["observations"] if row["role"] == "TARGET_OUTCOME"
    }
    for row in data["observations"]:
        if row["role"] == "CONTROL_0001":
            for key in ("source_record_id", "value", "available_on"):
                row[key] = targets[row["trade_date"]][key]
    if conflict:
        row = next(row for row in data["observations"] if row["role"] == "CONTROL_0001")
        row[conflict] = {
            "source_record_id": "SYNTH_CONFLICT",
            "value": "0.5",
            "available_on": "2020-01-01",
        }[conflict]
    _seal(data)
    if conflict:
        with pytest.raises(AdapterError, match="IDENTITY_CONFLICT"):
            materialize_analysis_dataset(contract, plan, data)
    else:
        output = materialize_analysis_dataset(contract, plan, data)
        assert output.status == "READY_SYNTHETIC"
        validate_dataset(output, contract, plan, data)


def test_no_controls_keeps_target_and_factor_roles():
    document = _document()
    document["controls"] = []
    contract, plan, data = _bundle(document)
    data["bindings"] = data["bindings"][:2]
    data["observations"] = [
        row for row in data["observations"] if row["role"] in ("TARGET_OUTCOME", "FACTOR")
    ]
    output = materialize_analysis_dataset(contract, plan, _seal(data))
    assert output.role_order == ("TARGET_OUTCOME", "FACTOR")
    assert len(output.complete_rows) == 3
    assert all(len(values) == 2 for _, values, _ in output.complete_rows)


@pytest.mark.parametrize("field", ["calendar_evidence", "membership_evidence"])
def test_unknown_nested_evidence_fields_are_not_silently_dropped(field):
    contract, plan, data = _bundle()
    data["domain"][field]["ignored_extra"] = True
    with pytest.raises(AdapterError, match="INVALID_INPUT_STRUCTURE"):
        materialize_analysis_dataset(contract, plan, data)


def test_explicit_domain_change_has_new_identity_and_stale_evidence_fails():
    contract, plan, data = _bundle()
    original = materialize_analysis_dataset(contract, plan, data)
    kept = data["domain"]["expected_dates"][:2]
    data["domain"]["expected_dates"] = kept
    with pytest.raises(AdapterError, match="EVIDENCE_DIGEST_MISMATCH"):
        materialize_analysis_dataset(contract, plan, data)
    for field in ("calendar_evidence", "membership_evidence"):
        data["domain"][field]["expected_dates"] = kept
    data["observations"] = [row for row in data["observations"] if row["trade_date"] in kept]
    changed = materialize_analysis_dataset(contract, plan, _seal(data))
    assert changed.quality.coverage_denominator == 2
    assert changed.input_digest != original.input_digest
    assert changed.domain_digest != original.domain_digest
    assert changed.dataset_digest != original.dataset_digest


def test_rehashed_plan_still_requires_original_contract_binding():
    contract, plan, data = _bundle()
    changed = replace(plan, source_contract_digest="0" * 64)
    changed = replace(changed, plan_digest=compute_plan_digest(changed))
    with pytest.raises(AdapterError, match="CONTRACT_PLAN_MISMATCH"):
        materialize_analysis_dataset(contract, changed, data)


@pytest.mark.parametrize(
    "mutate",
    [
        lambda p: replace(p, complete_rows=p.complete_rows[:1]),
        lambda p: replace(p, complete_rows=p.complete_rows[::-1]),
        lambda p: replace(p, quality=replace(p.quality, coverage_gate="2")),
        lambda p: replace(p, status="REJECTED_QUALITY", complete_rows=()),
        lambda p: replace(p, input_digest="not-a-hash"),
        lambda p: replace(p, audit_rows=(p.audit_rows[0],) * 3),
        lambda p: replace(p, audit_rows=list(p.audit_rows)),
        lambda p: replace(p, quality=replace(p.quality, coverage_denominator=True)),
        lambda p: replace(p, execution_authorized=True),
    ],
)
def test_rehashed_output_invariants_cannot_be_bypassed(mutate):
    contract, plan, data = _bundle()
    output = materialize_analysis_dataset(contract, plan, data)
    with pytest.raises(AdapterError):
        serialize_dataset(_rehash(mutate(output)))


def test_evidence_and_export_copies_are_actually_independent():
    contract, plan, data = _bundle()
    original = deepcopy(data)
    bound = BoundDatasetInputsV1.from_dict(data)
    output = materialize_analysis_dataset(contract, plan, bound)
    encoded = serialize_dataset(output)
    data["domain"]["calendar_evidence"]["expected_dates"].clear()
    data["observations"][0]["value"] = "99"
    with pytest.raises(FrozenInstanceError):
        bound.domain.calendar_evidence.domain_id = "MUTATED"
    exported = dataset_to_canonical_dict(output)
    exported["audit_rows"][0]["cells"][0]["value"] = "99"
    assert serialize_dataset(output) == encoded
    validate_dataset(output, contract, plan, original)


def test_future_pit_is_excluded_even_when_optional_quality_flags_are_false():
    document = _document()
    document["data_quality_gates"].update(
        pit_required=False,
        identity_required=False,
        coverage_gate="0.66",
        missingness_policy="RETAIN_IN_DENOMINATOR",
    )
    contract, plan, data = _bundle(document)
    row = next(
        row
        for row in data["observations"]
        if row["role"] == "CONTROL_0002" and row["trade_date"] == "2020-01-03"
    )
    row["available_on"] = "2020-01-06"
    output = materialize_analysis_dataset(contract, plan, _seal(data))
    assert output.status == "READY_SYNTHETIC"
    assert output.quality.coverage_numerator == 2
    assert output.quality.coverage_denominator == 3
    assert output.quality.reason_counts == (("PIT_NOT_AVAILABLE", 1),)
    assert tuple(td for td, _, _ in output.complete_rows) == ("2020-01-02", "2020-01-06")


def test_zero_coverage_gate_does_not_accept_an_empty_sample():
    document = _document()
    document["data_quality_gates"].update(
        coverage_gate="0",
        missingness_policy="RETAIN_IN_DENOMINATOR",
    )
    contract, plan, data = _bundle(document)
    data["observations"] = []
    output = materialize_analysis_dataset(contract, plan, _seal(data))
    assert output.status == "REJECTED_QUALITY"
    assert output.quality.coverage_numerator == 0
    assert output.quality.coverage_denominator == 3
    assert output.quality.reason_counts == (("MISSING_OBSERVATION", 12),)
    assert output.complete_rows == ()
    serialize_dataset(output)


@pytest.mark.parametrize("field", ["domain", "binding"])
def test_empty_domain_or_missing_binding_is_not_a_quality_gap(field):
    contract, plan, data = _bundle()
    if field == "domain":
        data["domain"]["expected_dates"] = []
        code = "EMPTY_EXPECTED_DOMAIN"
    else:
        data["bindings"].pop()
        code = "ROLE_BINDING_MISMATCH"
    with pytest.raises(AdapterError, match=code):
        materialize_analysis_dataset(contract, plan, data)


def test_adapter_does_not_call_statistical_or_data_engines():
    contract, plan, data = _bundle()

    def guard(frame, event, arg):
        if event == "call":
            module = frame.f_globals.get("__name__", "")
            assert not module.startswith(("pandas", "duckdb", "statsmodels", "requests"))
            assert frame.f_code.co_name not in ("fit_primary_ols", "moving_block_bootstrap")

    previous = sys.getprofile()
    try:
        sys.setprofile(guard)
        result = materialize_analysis_dataset(contract, plan, data)
        serialize_dataset(result)
        validate_dataset(result, contract, plan, data)
    finally:
        sys.setprofile(previous)
