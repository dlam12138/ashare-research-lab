"""Focused M3 Stage 3B data-contract and fail-closed tests."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd
import pytest

from ashare_research.exceptions import DuplicateKeyError
from ashare_research.mechanism.contracts import (
    Stage3BContractError,
    assert_no_restricted_research_outputs,
    load_contract,
    study_sample,
    validate_development_dates,
    verify_stage3a_frozen,
)
from ashare_research.mechanism.market_proxy import build_market_ex_target_proxy
from ashare_research.mechanism.normalization import (
    align_latest_observable_before_a_share_close,
    normalize_daily_observations,
)
from ashare_research.mechanism.source_manifest import (
    build_coverage_metadata,
    canonical_frame_digest,
    verify_raw_manifest,
)

ROOT = Path(__file__).resolve().parents[1]


def _universe() -> pd.DataFrame:
    rows = []
    for trade_date, regime in [
        ("2020-07-21", "SSE_COMPOSITE_PRE_20200722"),
        ("2020-07-22", "SSE_COMPOSITE_FROM_20200722"),
    ]:
        for symbol, reference, price, shares in [
            ("600000.SH", 10.0, 10.2, 100.0),
            ("600001.SH", 20.0, 19.8, 50.0),
            ("601857.SH", 5.0, 5.5, 1_000.0),
        ]:
            rows.append(
                {
                    "trade_date": trade_date,
                    "symbol": symbol,
                    "eligible": True,
                    "eligibility_reason": "REGIME_ELIGIBLE",
                    "shares": shares,
                    "price": price,
                    "reference_price": reference,
                    "membership_is_pit": True,
                    "shares_are_pit": True,
                    "corporate_action_verified": True,
                    "methodology_regime": regime,
                    "universe_basis": "DATED_OFFICIAL_RULES",
                    "source_ref": "fixture",
                }
            )
    return pd.DataFrame(rows)


def _daily_input() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "trade_date": ["2015-01-06", "2014-12-31", "2015-01-05"],
            "observation_time": [
                "2015-01-06T07:00:00Z",
                "2014-12-31T07:00:00Z",
                "2015-01-05T07:00:00Z",
            ],
            "available_at": [
                "2015-01-06T07:01:00Z",
                "2014-12-31T07:01:00Z",
                "2015-01-05T07:01:00Z",
            ],
            "value": [12.0, 10.0, 11.0],
        }
    )


def _normalize(frame: pd.DataFrame) -> pd.DataFrame:
    return normalize_daily_observations(
        frame,
        dataset_id="fixture",
        instrument_id="FIXTURE",
        currency="CNY",
        adjustment="none",
        source_name="fixture",
        source_endpoint="fixture",
        source_version="v1",
        raw_sha256="a" * 64,
    )


def test_stage3a_frozen_artifacts_unchanged() -> None:
    assert len(verify_stage3a_frozen(ROOT / "reports")) == 3


def test_stage3b_contract_schema_and_fallback_locks() -> None:
    contract = load_contract(
        ROOT / "reports/m3_stage3b_primary_proxy_contract_v1.json",
        {"proxy_id", "methodology_regimes", "fallback_policy"},
    )
    assert contract["proxy_id"] == "SH_MARKET_EX_601857"
    assert contract["fallback_policy"]["fallback_to_sse_composite"] is False
    assert contract["fallback_policy"]["fallback_to_equal_weight"] is False
    assert contract["fallback_policy"]["survivorship_backfill_allowed"] is False
    assert contract["fallback_policy"]["future_constituent_information_allowed"] is False


def test_holdout_row_rejected() -> None:
    with pytest.raises(Stage3BContractError, match="holdout"):
        validate_development_dates(pd.DataFrame({"trade_date": ["2023-01-01"]}))


def test_warmup_rows_excluded_from_study_sample() -> None:
    frame = pd.DataFrame({"trade_date": ["2014-12-31", "2015-01-05"], "value": [1, 2]})
    assert study_sample(frame)["value"].tolist() == [2]


def test_normalization_canonicalizes_order() -> None:
    result = _normalize(_daily_input())
    assert result["trade_date"].dt.strftime("%Y-%m-%d").tolist() == [
        "2014-12-31",
        "2015-01-05",
        "2015-01-06",
    ]


def test_duplicate_daily_date_rejected() -> None:
    frame = pd.concat([_daily_input(), _daily_input().iloc[[0]]], ignore_index=True)
    with pytest.raises(DuplicateKeyError, match="duplicate trade_date"):
        _normalize(frame)


def test_raw_sha_is_required() -> None:
    with pytest.raises(Stage3BContractError, match="raw_sha256"):
        normalize_daily_observations(
            _daily_input(),
            dataset_id="fixture",
            instrument_id="FIXTURE",
            currency="CNY",
            adjustment="none",
            source_name="fixture",
            source_endpoint="fixture",
            source_version="v1",
            raw_sha256="bad",
        )


def test_available_at_cannot_precede_observation() -> None:
    frame = _daily_input()
    frame.loc[0, "available_at"] = "2015-01-06T06:59:00Z"
    with pytest.raises(Stage3BContractError, match="precedes"):
        _normalize(frame)


def test_oil_alignment_uses_latest_proven_available_observation() -> None:
    observations = pd.DataFrame(
        {
            "observation_time": ["2015-01-04T22:00:00Z", "2015-01-05T22:00:00Z"],
            "available_at": ["2015-01-05T03:00:00Z", "2015-01-05T08:00:00Z"],
            "value": [50.0, 51.0],
        }
    )
    aligned = align_latest_observable_before_a_share_close(
        pd.Series(["2015-01-05"]), observations
    )
    assert aligned.loc[0, "value"] == 50.0


def test_oil_same_day_future_close_rejected() -> None:
    observations = pd.DataFrame(
        {
            "observation_time": ["2015-01-05T22:00:00Z"],
            "available_at": ["2015-01-06T01:00:00Z"],
            "value": [51.0],
        }
    )
    with pytest.raises(Stage3BContractError, match="missing latest observable"):
        align_latest_observable_before_a_share_close(pd.Series(["2015-01-05"]), observations)


def test_primary_proxy_physically_excludes_target() -> None:
    proxy, audit = build_market_ex_target_proxy(_universe())
    assert len(proxy) == 2
    assert proxy["return"].round(8).tolist() == [0.005, 0.005]
    assert audit.loc[audit["symbol"].eq("601857.SH"), "target_excluded"].all()


def test_primary_proxy_duplicate_symbol_date_rejected() -> None:
    frame = pd.concat([_universe(), _universe().iloc[[0]]], ignore_index=True)
    with pytest.raises(DuplicateKeyError, match="symbol/date"):
        build_market_ex_target_proxy(frame)


@pytest.mark.parametrize("basis", ["CURRENT_CONSTITUENTS", "SURVIVORSHIP_ONLY"])
def test_non_pit_universe_rejected(basis: str) -> None:
    frame = _universe()
    frame["universe_basis"] = basis
    with pytest.raises(Stage3BContractError, match="survivorship"):
        build_market_ex_target_proxy(frame)


def test_future_methodology_backfill_rejected() -> None:
    frame = _universe()
    frame.loc[frame["trade_date"].eq("2020-07-21"), "methodology_regime"] = (
        "SSE_COMPOSITE_FROM_20200722"
    )
    with pytest.raises(Stage3BContractError, match="methodology"):
        build_market_ex_target_proxy(frame)


def test_unverified_tier1_input_fails_closed() -> None:
    frame = _universe()
    frame.loc[0, "shares_are_pit"] = False
    with pytest.raises(Stage3BContractError, match="shares_are_pit"):
        build_market_ex_target_proxy(frame)


def test_missing_tier1_column_fails_closed() -> None:
    with pytest.raises(Stage3BContractError, match="missing columns"):
        build_market_ex_target_proxy(_universe().drop(columns="shares"))


def test_raw_manifest_sha_passes_and_mismatch_fails(tmp_path: Path) -> None:
    raw = tmp_path / "raw"
    raw.mkdir()
    payload = b"locked raw input\n"
    (raw / "input.csv").write_bytes(payload)
    digest = hashlib.sha256(payload).hexdigest()
    entries = [{"raw_file_path": "input.csv", "raw_sha256": digest}]
    verify_raw_manifest(entries, raw)
    entries[0]["raw_sha256"] = "0" * 64
    with pytest.raises(Stage3BContractError, match="raw SHA mismatch"):
        verify_raw_manifest(entries, raw)


def test_offline_ab_logical_digest_identical() -> None:
    first = _normalize(_daily_input())
    second = _normalize(_daily_input().iloc[::-1].reset_index(drop=True))
    assert canonical_frame_digest(first) == canonical_frame_digest(second)


def test_restricted_research_output_key_rejected() -> None:
    with pytest.raises(Stage3BContractError, match="restricted"):
        assert_no_restricted_research_outputs({"coverage": {}, "gamma": 0.1})


def test_contracts_do_not_authorize_statistical_execution() -> None:
    contract = json.loads(
        (ROOT / "reports/m3_stage3b_return_and_timing_contract_v1.json").read_text(
            encoding="utf-8"
        )
    )
    assert contract["statistical_semantics_only"]["execution_authorized"] is False
    assert contract["oil"]["same_day_overseas_close_allowed"] is False
    assert contract["target"]["mixing_series_allowed"] is False


def test_coverage_payload_contains_quality_metadata_only() -> None:
    frame = pd.DataFrame({"trade_date": ["2015-01-05"], "value": [1.0]})
    payload = build_coverage_metadata(
        frame,
        dataset_id="fixture",
        expected_dates=pd.Series(["2015-01-05", "2015-01-06"]),
    )
    assert payload["rows"] == 1
    assert payload["missing_dates"] == ["2015-01-06"]
    assert payload["coverage_ratio"] == 0.5
    assert_no_restricted_research_outputs(payload)
