"""Behavioral tests for the invented, in-memory M4 source-proof K1 fixture."""

import copy
import hashlib
import json
from dataclasses import replace

import pytest

from ashare_research.mechanism.datasets.real_daily_kernel import (
    BUNDLE_SCHEMA,
    KERNEL_VERSION,
    RAW_FORMAT,
    RealSourceAuditProofK1,
    RealSourceError,
    RealSourceRejectionK1,
    contract_digest,
    input_digest,
    serialize_proof,
    validate_real_source_proof_k1,
    verify_real_daily_source_proof_k1,
)

DATES = ["2022-01-04", "2022-01-05", "2022-01-06"]
ROLES = ["TARGET_OUTCOME", "FACTOR"]


def _bytes(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def _sha(value):
    return hashlib.sha256(_bytes(value)).hexdigest()


def _rows():
    rows = []
    for role in ROLES:
        for day in DATES:
            rows.append(
                {
                    "role": role,
                    "trade_date": day,
                    "value": "0.01",
                    "observation_at": f"{day}T15:00:00+08:00",
                    "published_at": f"{day}T18:00:00+08:00",
                    "available_at": f"{day}T19:00:00+08:00",
                    "available_at_basis": "SOURCE_PUBLICATION_VERIFIED",
                    "ingested_at": f"{day}T19:30:00+08:00",
                    "source_record_id": f"{role}-{day}",
                }
            )
    return rows


def _case(rows=None, *, gate="1/1", min_joint=2):
    rows = copy.deepcopy(_rows() if rows is None else rows)
    domain = {
        "expected_dates": DATES[:],
        "calendar_dates": DATES[:],
        "calendar_basis": "CALLER_FROZEN_UNVERIFIED",
    }
    runs, raw = [], {}
    for role in ROLES:
        locator = f"fixtures/{role}.json"
        data = _bytes({"format": RAW_FORMAT, "records": [r for r in rows if r["role"] == role]})
        raw[locator] = data
        runs.append(
            {
                "role": role,
                "run_id": f"RUN_{role}",
                "provider_id": "INVENTED",
                "endpoint_id": "OFFLINE_FIXTURE",
                "revision_id": "R1",
                "vintage_id": "V1",
                "raw_locator": locator,
                "raw_sha256": hashlib.sha256(data).hexdigest(),
                "raw_bytes_length": len(data),
                "normalization_rule_id": RAW_FORMAT,
            }
        )
    versions = [
        [
            r[k]
            for k in (
                "role",
                "run_id",
                "provider_id",
                "endpoint_id",
                "revision_id",
                "vintage_id",
                "raw_sha256",
                "normalization_rule_id",
            )
        ]
        for r in runs
    ]
    contract = {
        "study_id": "INVENTED_STUDY",
        "development_start": DATES[0],
        "development_end": DATES[-1],
        "holdout_start": "2023-01-01",
        "roles": ROLES[:],
        "source_versions": versions,
        "code_digest": "a" * 64,
        "signal_cutoff_local": "20:00",
        "timezone_offset": "+08:00",
        "coverage_gate": gate,
        "min_joint_dates": min_joint,
        "contract_digest": "",
    }
    contract["contract_digest"] = contract_digest(contract)
    lock = {
        "contract_digest": contract["contract_digest"],
        "domain_digest": _sha(domain),
        "sealed_before_outcome": True,
        "source_versions": versions,
        "code_digest": contract["code_digest"],
    }
    bundle = {
        "schema_version": BUNDLE_SCHEMA,
        "study_id": contract["study_id"],
        "contract_digest": contract["contract_digest"],
        "roles": ROLES[:],
        "source_runs": runs,
        "observations": rows,
        "input_digest": "",
    }
    bundle["input_digest"] = input_digest(bundle)
    return bundle, contract, domain, lock, _sha(lock), raw


def _verify(case):
    return verify_real_daily_source_proof_k1(*case)


def _error(case, code, stage):
    with pytest.raises(RealSourceError) as exc:
        _verify(case)
    assert (exc.value.code, exc.value.stage) == (code, stage)


def test_good_proof_is_only_an_offline_audit_and_revalidates_sources():
    case = _case()
    proof = _verify(case)
    assert type(proof) is RealSourceAuditProofK1
    assert (proof.coverage_numerator, proof.coverage_denominator, proof.joint_complete_dates) == (
        6,
        6,
        3,
    )
    assert proof.calendar_evidence_verified is False and proof.real_source_validated is False
    assert proof.execution_authorized is False and proof.statistics_computed is False
    assert proof.outcome_bytes_examined is True and proof.matrix is None
    assert serialize_proof(proof).endswith(b"\n")
    validate_real_source_proof_k1(proof, *case)
    assert KERNEL_VERSION.encode() in serialize_proof(proof)


def test_external_lock_or_holdout_fails_before_any_raw_read():
    bundle, contract, domain, lock, trusted, raw = _case()

    class NoRead(dict):
        def __contains__(self, key):
            raise AssertionError("raw bytes touched before lock")

    _error((bundle, contract, domain, lock, "0" * 64, NoRead(raw)), "REAL_POST_OUTCOME_MUTATION", 1)
    changed = copy.deepcopy(bundle)
    changed["observations"][0]["trade_date"] = "2023-01-02"
    _error((changed, contract, domain, lock, trusted, NoRead(raw)), "REAL_HOLDOUT_INJECTION", 1)


def test_malformed_locked_fields_fail_with_stable_error_before_reader():
    bundle, contract, domain, lock, trusted, raw = _case()

    class NoRead(dict):
        def __contains__(self, key):
            raise AssertionError("reader accessed on malformed lock")

    malformed = copy.deepcopy(contract)
    malformed["timezone_offset"] = "+14:30"
    _error(
        (bundle, malformed, domain, lock, trusted, NoRead(raw)), "REAL_INVALID_INPUT_STRUCTURE", 0
    )
    malformed = copy.deepcopy(contract)
    malformed["source_versions"] = [["FACTOR", 5]]
    _error(
        (bundle, malformed, domain, lock, trusted, NoRead(raw)), "REAL_INVALID_INPUT_STRUCTURE", 0
    )
    malformed_bundle = copy.deepcopy(bundle)
    malformed_bundle["source_runs"][0]["provider_id"] = ""
    _error(
        (malformed_bundle, contract, domain, lock, trusted, NoRead(raw)),
        "REAL_INVALID_INPUT_STRUCTURE",
        0,
    )
    changed_provider = copy.deepcopy(bundle)
    changed_provider["source_runs"][0]["provider_id"] = "OTHER"
    _error(
        (changed_provider, contract, domain, lock, trusted, NoRead(raw)),
        "REAL_POST_OUTCOME_MUTATION",
        1,
    )
    missing_revision = copy.deepcopy(bundle)
    missing_revision["source_runs"][0]["revision_id"] = ""
    _error(
        (missing_revision, contract, domain, lock, trusted, NoRead(raw)),
        "REAL_SOURCE_VERSION_MISSING",
        1,
    )


def test_raw_bytes_are_rehashed_and_declared_rows_must_match_parser():
    case = list(_case())
    bad_raw = dict(case[5])
    raw_key = "fixtures/FACTOR.json"
    bad_raw[raw_key] = bad_raw[raw_key].replace(b"0.01", b"0.02", 1)
    case[5] = bad_raw
    _error(case, "REAL_RAW_HASH_MISMATCH", 2)
    case = list(_case())
    case[0] = copy.deepcopy(case[0])
    case[0]["observations"][0]["value"] = "0.02"
    case[0]["input_digest"] = input_digest(case[0])
    _error(case, "REAL_SOURCE_IDENTITY_MISMATCH", 2)


def test_unsafe_locator_and_missing_source_fail_closed():
    case = list(_case())
    case[0] = copy.deepcopy(case[0])
    case[0]["source_runs"][0]["raw_locator"] = "../elsewhere.json"
    _error(case, "REAL_INVALID_INPUT_STRUCTURE", 0)
    case = list(_case())
    case[0] = copy.deepcopy(case[0])
    case[0]["source_runs"].pop()
    _error(case, "REAL_SOURCE_ROLE_MISSING", 1)


def test_duplicate_json_key_and_duplicate_cell_are_rejected():
    case = list(_case())
    key = "fixtures/FACTOR.json"
    raw = case[5][key].replace(b'"format":', b'"format":"X","format":', 1)
    case[5] = dict(case[5], **{key: raw})
    case[0] = copy.deepcopy(case[0])
    case[1] = copy.deepcopy(case[1])
    case[3] = copy.deepcopy(case[3])
    case[0]["source_runs"][1]["raw_sha256"] = hashlib.sha256(raw).hexdigest()
    case[0]["source_runs"][1]["raw_bytes_length"] = len(raw)
    case[1]["source_versions"][1][6] = hashlib.sha256(raw).hexdigest()
    case[1]["contract_digest"] = contract_digest(case[1])
    case[0]["contract_digest"] = case[1]["contract_digest"]
    case[3]["contract_digest"] = case[1]["contract_digest"]
    case[3]["source_versions"] = case[1]["source_versions"]
    case[0]["input_digest"] = input_digest(case[0])
    case[4] = _sha(case[3])
    _error(case, "REAL_INVALID_INPUT_STRUCTURE", 2)
    rows = _rows()
    duplicate = copy.deepcopy(rows[0])
    duplicate["source_record_id"] = "DIFFERENT"
    rows.append(duplicate)
    _error(_case(rows), "REAL_DUPLICATE_OBSERVATION", 6)


@pytest.mark.parametrize(
    "field,code",
    [
        ("published_at", "REAL_PUBLISHED_AT_MISSING"),
        ("available_at", "REAL_AVAILABLE_AT_MISSING"),
    ],
)
def test_missing_pit_timestamp_is_structural_failure(field, code):
    rows = _rows()
    rows[0][field] = None
    _error(_case(rows), code, 5)


def test_ingestion_is_not_pit_and_late_availability_is_a_gap():
    rows = _rows()
    rows[0]["available_at_basis"] = "INGESTION"
    _error(_case(rows), "REAL_INGESTED_AT_AS_PIT", 5)
    rows = _rows()
    rows[-1]["available_at"] = "2022-01-07T09:00:00+08:00"
    rows[-1]["ingested_at"] = "2022-01-07T09:30:00+08:00"
    result = _verify(_case(rows))
    assert type(result) is RealSourceRejectionK1
    assert (
        result.code,
        result.coverage_numerator,
        result.coverage_denominator,
        result.joint_complete_dates,
    ) == ("REAL_COVERAGE_BELOW_GATE", 5, 6, 2)
    assert result.gaps == (("2022-01-06", "FACTOR", "PIT_UNPROVEN"),)
    assert result.matrix is None and result.accepted_roles == ()
    assert result.outcome_bytes_examined is True


def test_inverted_event_publication_or_ingestion_times_fail():
    rows = _rows()
    rows[0]["observation_at"] = "2022-01-04T19:00:00+08:00"
    _error(_case(rows), "REAL_INVALID_INPUT_STRUCTURE", 5)
    rows = _rows()
    rows[0]["ingested_at"] = "2022-01-04T18:30:00+08:00"
    _error(_case(rows), "REAL_INVALID_INPUT_STRUCTURE", 5)


def test_missing_observation_and_exact_quality_boundaries():
    rows = [r for r in _rows() if not (r["role"] == "FACTOR" and r["trade_date"] == DATES[-1])]
    result = _verify(_case(rows))
    assert result.code == "REAL_COVERAGE_BELOW_GATE" and result.gaps[0][2] == "MISSING_OBSERVATION"
    rows = [r for r in _rows() if r["trade_date"] != DATES[-1]]
    passed = _verify(_case(rows, gate="2/3"))
    assert (
        passed.coverage_numerator,
        passed.coverage_denominator,
        passed.joint_complete_dates,
    ) == (4, 6, 2)
    assert passed.execution_authorized is False
    rows = [r for r in _rows() if not (r["role"] == "FACTOR" and r["trade_date"] in DATES[1:])]
    rejected = _verify(_case(rows, gate="2/3"))
    assert rejected.code == "REAL_JOINT_DATES_BELOW_MIN" and rejected.joint_complete_dates == 1


def test_nontrading_date_and_input_digest_tamper():
    rows = _rows()
    rows[0]["trade_date"] = "2022-01-08"
    _error(_case(rows), "REAL_NON_TRADING_DATE", 3)
    case = list(_case())
    case[0] = copy.deepcopy(case[0])
    case[0]["input_digest"] = "0" * 64
    _error(case, "REAL_DIGEST_MISMATCH", 6)


def test_reordering_and_host_directory_do_not_change_identity():
    case = list(_case())
    original = _verify(case)
    case[0] = copy.deepcopy(case[0])
    case[0]["source_runs"].reverse()
    case[0]["observations"].reverse()
    case[2] = copy.deepcopy(case[2])
    case[2]["expected_dates"].reverse()
    case[2]["calendar_dates"].reverse()
    case[0]["input_digest"] = input_digest(case[0])
    assert serialize_proof(_verify(case)) == serialize_proof(original)

    class RootedBytes(dict):
        def __init__(self, root, values):
            super().__init__(values)
            self.root = root

    other = list(_case())
    other[5] = RootedBytes("D:/elsewhere", other[5])
    assert serialize_proof(original) == serialize_proof(_verify(other))


def test_reader_callback_cannot_rewrite_the_verified_input_snapshot():
    case = list(_case())
    expected = serialize_proof(_verify(_case()))

    class MutatingBytes(dict):
        def __getitem__(self, key):
            case[0]["observations"][0]["value"] = "0.99"
            return super().__getitem__(key)

    case[5] = MutatingBytes(case[5])
    assert serialize_proof(_verify(case)) == expected
    assert case[0]["observations"][0]["value"] == "0.99"


def test_proof_tamper_and_synthetic_serializer_isolation():
    case = _case()
    proof = _verify(case)
    with pytest.raises(RealSourceError, match="REAL_DIGEST_MISMATCH"):
        serialize_proof(replace(proof, execution_authorized=True))
    with pytest.raises(RealSourceError, match="REAL_DIGEST_MISMATCH"):
        validate_real_source_proof_k1(replace(proof, proof_digest="0" * 64), *case)
    from ashare_research.mechanism.datasets.synthetic import AdapterError, serialize_dataset
    from ashare_research.mechanism.pipeline.orchestrator import (
        PipelineError,
        run_synthetic_pipeline,
    )

    with pytest.raises(AdapterError):
        serialize_dataset(proof)
    with pytest.raises(PipelineError) as exc:
        run_synthetic_pipeline(request=proof)
    assert exc.value.code == "PIPELINE_REQUEST_TYPE_INVALID"
