"""Synthetic-only pre-execution gates for M3 Stage 3C-B."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from ashare_research.mechanism.analysis_contracts import ANALYSIS_COLUMNS
from ashare_research.tools.m3_stage3cb_development import (
    verify_adapter_lock,
    verify_frozen_lock,
)
from ashare_research.tools.m3_stage3cb_inputs import (
    ADAPTER_DIGEST_ALGORITHM,
    EXPECTED_INDUSTRY_ALIGNED_DIGEST,
    EXPECTED_MARKET_PROXY,
    EXPECTED_OIL_ALIGNED_DIGEST,
    EXPECTED_TIER1_READINESS_DIGEST,
    Stage3CBInputError,
    _read_hash_first,
    build_exact_date_analysis_matrix,
    build_execution_adapter_digest,
    materialize_qfq_close_to_close,
    validate_execution_mode,
    verify_authorization_contract,
    verify_result_schema,
)

ROOT = Path(__file__).resolve().parents[1]


def _small_inputs() -> tuple[pd.DataFrame, ...]:
    dates = pd.date_range("2015-03-16", periods=4, freq="B")
    target = pd.DataFrame(
        {
            "trade_date": dates,
            "target_analysis_return": [0.01, -0.02, 0.003, 0.004],
            "target_valid": [True] * 4,
        }
    )
    market = pd.DataFrame(
        {
            "trade_date": dates,
            "market_ex_target_return": [-0.012, 0.001, 0.002, -0.003],
            "market_valid": [True] * 4,
        }
    )
    oil = pd.DataFrame(
        {
            "trade_date": dates,
            "oil_return": [0.01, 0.0, -0.01, 0.002],
            "oil_aligned_valid": [True] * 4,
        }
    )
    industry = pd.DataFrame(
        {
            "trade_date": dates,
            "industry_return": [0.002, -0.001, 0.003, 0.001],
            "industry_aligned_valid": [True] * 4,
        }
    )
    readiness = pd.DataFrame(
        {
            "trade_date": dates,
            "market_proxy_valid": [True] * 4,
            "oil_valid": [True] * 4,
            "industry_valid": [True] * 4,
            "tier1_joint_valid": [True] * 4,
        }
    )
    return target, market, oil, industry, readiness


def test_preexecution_authorization_and_result_schema_are_frozen() -> None:
    authorization = verify_authorization_contract()
    schema = verify_result_schema()
    assert authorization["execution_mode"] == "DEVELOPMENT_PRIMARY_ONLY"
    assert authorization["robustness_allowed"] is False
    assert authorization["holdout_allowed"] is False
    assert schema["value_constraints"]["evidence_level"] is None
    assert "p_value" in schema["forbidden_fields"]


def test_relocked_identity_exact_and_old_locks_are_not_current() -> None:
    identity = verify_frozen_lock()
    assert identity["pipeline_digest"] == (
        "ab224492ff85f391a29048dfeec740f9bbffb376de3408a5645a4552b51b9d1b"
    )
    assert identity["model_digest"] == (
        "4958351a5c79c0eb96bbfda9ebaaca5e71ab2b07236eaa808b0a92ebc6e9756d"
    )
    assert identity["pipeline_digest"] not in {
        "f667598001e8f63734547f7da281c41cf571c70667d784e35e57b6eddd4e781b",
        "28154ef29ac86984042c18d9d39292dd3d85ffa44450ef98d8f02add23b2ef11",
        "2b02d5a82aad0eca940f5decbce0e837086ef700dfcc3dfcba4740e82c20c85a",
    }


def test_adapter_digest_is_repository_relative_and_locked() -> None:
    digest, payload = build_execution_adapter_digest()
    assert digest == verify_adapter_lock()
    assert payload["digest_algorithm"] == ADAPTER_DIGEST_ALGORITHM
    assert all(":\\" not in key and not key.startswith("/") for key in payload["source_hashes"])
    report = json.loads(
        (ROOT / "reports/m3_stage3cb_execution_adapter_digest_v1.json").read_text(
            encoding="utf-8"
        )
    )
    assert report["adapter_digest"] == digest


def test_hash_mismatch_and_holdout_scan_fail_before_parse(tmp_path: Path) -> None:
    path = tmp_path / "input.csv"
    path.write_bytes(b"date,close\n2022-12-30,1\n")
    with pytest.raises(Stage3CBInputError, match="REAL_INPUT_HASH_MISMATCH"):
        _read_hash_first(path, "0" * 64, "fixture")
    path.write_bytes(b"date,close\n2023-01-01,1\n")
    with pytest.raises(Stage3CBInputError, match="HOLDOUT_RAW_DATE_REJECTED"):
        _read_hash_first(path, None, "fixture")


def test_qfq_target_return_fixture_and_unadjusted_target_rejection() -> None:
    frame = pd.DataFrame(
        {
            "date": ["2015-03-16", "2015-03-17", "2015-03-18"],
            "code": ["sh.601857"] * 3,
            "close": [10.0, 11.0, 10.0],
        }
    )
    result = materialize_qfq_close_to_close(frame)
    assert result["target_valid"].tolist() == [False, True, True]
    assert result.loc[1, "target_analysis_return"] == pytest.approx(0.1)
    with pytest.raises(Stage3CBInputError, match="MUST_BE_QFQ"):
        materialize_qfq_close_to_close(frame, adjustment="unadjusted")


def test_target_identity_and_holdout_fixture_rejected() -> None:
    frame = pd.DataFrame(
        {
            "date": ["2015-03-16"],
            "code": ["sz.000001"],
            "close": [10.0],
        }
    )
    with pytest.raises(Stage3CBInputError, match="TARGET_IDENTITY_FAILURE"):
        materialize_qfq_close_to_close(frame)
    frame["code"] = "sh.601857"
    frame["date"] = "2023-01-01"
    with pytest.raises(Stage3CBInputError, match="TARGET_DATE_OR_HOLDOUT_FAILURE"):
        materialize_qfq_close_to_close(frame)


def test_exact_date_join_is_not_asof_and_no_double_shift() -> None:
    inputs = _small_inputs()
    matrix = build_exact_date_analysis_matrix(*inputs, enforce_expected_identity=False)
    assert list(matrix.columns) == list(ANALYSIS_COLUMNS)
    assert matrix["oil_return"].tolist() == inputs[2]["oil_return"].tolist()
    shifted = list(inputs)
    shifted[3] = shifted[3].assign(trade_date=shifted[3]["trade_date"] + pd.Timedelta(days=1))
    with pytest.raises(Stage3CBInputError, match="EXACT_DATE_JOIN_KEY_MISMATCH"):
        build_exact_date_analysis_matrix(*shifted, enforce_expected_identity=False)


def test_tier1_flags_are_consistent_and_alternative_proxy_is_not_accepted() -> None:
    inputs = _small_inputs()
    matrix = build_exact_date_analysis_matrix(*inputs, enforce_expected_identity=False)
    assert matrix["tier1_joint_valid"].all()
    bad = list(inputs)
    bad[4] = bad[4].assign(tier1_joint_valid=False)
    with pytest.raises(Stage3CBInputError, match="TIER1_JOINT_FLAG_MISMATCH"):
        build_exact_date_analysis_matrix(*bad, enforce_expected_identity=False)
    assert EXPECTED_MARKET_PROXY == "SH_A_SHARE_EQUAL_WEIGHT_EX_601857_V2"
    assert EXPECTED_OIL_ALIGNED_DIGEST.startswith("1de98bf2")
    assert EXPECTED_INDUSTRY_ALIGNED_DIGEST.startswith("a0bb7fa6")
    assert EXPECTED_TIER1_READINESS_DIGEST.startswith("801e8775")


def test_development_primary_mode_only() -> None:
    validate_execution_mode("development-primary")
    with pytest.raises(Stage3CBInputError, match="DEVELOPMENT_PRIMARY_ONLY"):
        validate_execution_mode("robustness")
    with pytest.raises(Stage3CBInputError, match="DEVELOPMENT_PRIMARY_ONLY"):
        validate_execution_mode("holdout")
