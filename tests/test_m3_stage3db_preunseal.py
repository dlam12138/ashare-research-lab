"""Synthetic-only Stage 3D-B contract, boundary, and adapter-equivalence tests."""

from __future__ import annotations

import ast
import json
from pathlib import Path

import pandas as pd
import pytest

from ashare_research.exceptions import DuplicateKeyError
from ashare_research.mechanism.acquisition_cni import (
    build_cni_returns,
    prove_cni_bounded_raw_response,
    validate_cni_bounds,
)
from ashare_research.mechanism.acquisition_fred_public import (
    prove_bounded_raw_response,
    validate_fred_bounds,
)
from ashare_research.mechanism.contracts import Stage3BContractError
from ashare_research.mechanism.industry import build_industry_returns
from ashare_research.mechanism.oil import align_oil_to_a_share
from ashare_research.mechanism.proxy_v2 import build_market_ex_target_proxy_v2
from ashare_research.tools.m3_stage3cb_inputs import Stage3CBInputError, _materialize_target
from ashare_research.tools.m3_stage3db_oos_acquisition import prove_bounded_raw
from ashare_research.tools.m3_stage3db_oos_identity import (
    build_oos_execution_adapter_digest,
)
from ashare_research.tools.m3_stage3db_oos_inputs import (
    HOLDOUT_END,
    HOLDOUT_START,
    WARMUP_START,
    align_oil_to_a_share_oos,
    build_cni_returns_oos,
    build_market_ex_target_proxy_v2_oos,
    materialize_target_qfq_oos,
)
from ashare_research.tools.m3_stage3db_preunseal_check import validate_preunseal

ROOT = Path(__file__).resolve().parents[1]
OLD_TARGET_SOURCE = ROOT / "src/ashare_research/tools/m3_stage3cb_inputs.py"


def _calendar(*dates: str) -> pd.Series:
    return pd.Series(pd.to_datetime(list(dates)))


def _target(dates: list[str] | None = None) -> pd.DataFrame:
    dates = dates or ["2022-12-01", "2022-12-02", "2022-12-05"]
    return pd.DataFrame(
        {"date": dates, "code": "sh.601857", "close": [100.0, 101.0, 100.0][: len(dates)]}
    )


def _market_fixture() -> tuple[pd.DataFrame, pd.DataFrame, pd.Series]:
    dates = pd.to_datetime(["2022-12-01", "2022-12-02", "2022-12-05"])
    closes = pd.DataFrame(
        {
            "symbol": ["600001.SH", "600001.SH", "600002.SH", "600002.SH", "601857.SH"],
            "trade_date": [*dates[:2], *dates[:2], dates[0]],
            "close": [10.0, 10.2, 20.0, 19.0, 5.0],
        }
    )
    master = pd.DataFrame(
        {
            "symbol": ["600001.SH", "600002.SH", "601857.SH", "900001.SH"],
            "classification": [
                "A_SHARE_COMMON",
                "A_SHARE_COMMON",
                "A_SHARE_COMMON",
                "B_SHARE",
            ],
            "listing_date": pd.to_datetime(["2020-01-01"] * 4),
            "delisting_date": [None] * 4,
        }
    )
    return closes, master, pd.Series(dates)


def _oil_fixture() -> tuple[pd.DataFrame, pd.Series]:
    observations = pd.DataFrame(
        {
            "observation_date": pd.to_datetime(["2022-12-01", "2022-12-02"]),
            "price": [80.0, 82.0],
        }
    )
    return observations, _calendar("2022-12-01", "2022-12-02", "2022-12-05")


def _cni_fixture() -> tuple[pd.DataFrame, pd.Series]:
    closes = pd.DataFrame(
        {
            "trade_date": pd.to_datetime(["2022-12-01", "2022-12-02"]),
            "index_code": "399439",
            "close": [100.0, 101.0],
        }
    )
    return closes, _calendar("2022-12-01", "2022-12-02", "2022-12-05")


def test_preunseal_contract_is_ready_without_external_root() -> None:
    report = validate_preunseal(ROOT)
    assert report["status"] == "PASS"
    assert report["holdout_read"] is False
    assert report["holdout_download"] is False


@pytest.mark.parametrize(
    ("start", "end"),
    [(None, "2022-12-30"), ("2022-12-01", None), ("2023-01-01", "2023-01-02")],
)
def test_historical_fred_bounds_remain_fail_closed(start: str | None, end: str | None) -> None:
    with pytest.raises(Stage3BContractError):
        validate_fred_bounds(start, end)


@pytest.mark.parametrize(
    ("start", "end"),
    [(None, "2022-12-30"), ("2022-12-01", None), ("2023-01-01", "2023-01-02")],
)
def test_historical_cni_bounds_remain_fail_closed(start: str | None, end: str | None) -> None:
    with pytest.raises(Stage3BContractError):
        validate_cni_bounds(start, end)


@pytest.mark.parametrize(
    "frame",
    [
        _target(["2022-12-01", "2026-08-14"]),
    ],
)
def test_oos_target_rejects_after_frozen_end(frame: pd.DataFrame) -> None:
    with pytest.raises(ValueError, match="TARGET_DATE_ENVELOPE_FAILURE"):
        materialize_target_qfq_oos(frame)


def test_oos_target_is_qfq_simple_return_and_first_row_invalid() -> None:
    result = materialize_target_qfq_oos(_target())
    assert result["target_valid"].tolist() == [False, True, True]
    assert result.loc[1, "target_analysis_return"] == pytest.approx(0.01)


def test_old_target_adapter_still_rejects_holdout_in_memory(tmp_path: Path) -> None:
    path = tmp_path / "target.csv"
    _target(["2022-12-01", "2023-01-03"]).to_csv(path, index=False)
    with pytest.raises(Stage3CBInputError):
        _materialize_target(path)


def test_market_excludes_target_and_non_a_share() -> None:
    closes, master, calendar = _market_fixture()
    old_proxy, old_audit = build_market_ex_target_proxy_v2(closes, master, calendar)
    new_proxy, new_audit = build_market_ex_target_proxy_v2_oos(closes, master, calendar)
    pd.testing.assert_frame_equal(old_proxy, new_proxy)
    pd.testing.assert_frame_equal(old_audit, new_audit)
    assert "601857.SH" not in set(new_audit["symbol"])
    assert "900001.SH" not in set(new_audit["symbol"])


def test_market_pit_lag_and_suspension_carry_are_preserved() -> None:
    closes, master, calendar = _market_fixture()
    proxy, audit = build_market_ex_target_proxy_v2_oos(closes, master, calendar)
    first_day = audit.loc[audit["trade_date"] == pd.Timestamp("2022-12-01")]
    assert not first_day["in_expected_universe"].any()
    assert proxy["row_status"].iloc[1] == "PROXY_ROW_OK"


@pytest.mark.parametrize(
    "calendar",
    [_calendar("2022-12-01", "2023-01-01")],
)
def test_old_market_adapter_rejects_holdout_calendar(calendar: pd.Series) -> None:
    closes, master, _ = _market_fixture()
    with pytest.raises(Stage3BContractError):
        build_market_ex_target_proxy_v2(closes, master, calendar)


def test_oos_market_rejects_duplicate_symbol_date() -> None:
    closes, master, calendar = _market_fixture()
    duplicate = pd.concat([closes, closes.iloc[[0]]], ignore_index=True)
    with pytest.raises(DuplicateKeyError):
        build_market_ex_target_proxy_v2_oos(duplicate, master, calendar)


def test_oos_market_rejects_invalid_coverage_gate() -> None:
    closes, master, calendar = _market_fixture()
    with pytest.raises(ValueError, match="coverage_gate"):
        build_market_ex_target_proxy_v2_oos(closes, master, calendar, coverage_gate=0)


def test_oos_market_rejects_after_frozen_end() -> None:
    closes, master, calendar = _market_fixture()
    closes.loc[0, "trade_date"] = HOLDOUT_END + pd.Timedelta(days=1)
    with pytest.raises(ValueError, match="date envelope"):
        build_market_ex_target_proxy_v2_oos(closes, master, calendar)


def test_oil_old_and_new_adapters_match_on_pre_holdout_fixture() -> None:
    observations, calendar = _oil_fixture()
    old = align_oil_to_a_share(observations, calendar)
    new = align_oil_to_a_share_oos(observations, calendar)
    pd.testing.assert_frame_equal(old, new)


def test_oil_strictly_prior_same_anchor_is_zero() -> None:
    observations = pd.DataFrame(
        {"observation_date": pd.to_datetime(["2022-12-01"]), "price": [80.0]}
    )
    calendar = _calendar("2022-12-02", "2022-12-05")
    result = align_oil_to_a_share_oos(observations, calendar)
    assert result.loc[0, "oil_anchor_date"] == "2022-12-01"
    assert result.loc[1, "oil_return"] == 0.0


def test_oil_stale_anchor_is_invalid_not_filled() -> None:
    observations = pd.DataFrame(
        {"observation_date": pd.to_datetime(["2022-12-01"]), "price": [80.0]}
    )
    result = align_oil_to_a_share_oos(observations, _calendar("2022-12-10"))
    assert result.loc[0, "alignment_status"] == "OIL_ROW_INVALID_STALE_ANCHOR"
    assert pd.isna(result.loc[0, "oil_return"])


@pytest.mark.parametrize("bad_date", ["2026-08-14"])
def test_oos_oil_rejects_out_of_envelope(bad_date: str) -> None:
    observations = pd.DataFrame({"observation_date": pd.to_datetime([bad_date]), "price": [80.0]})
    with pytest.raises(ValueError, match="date envelope"):
        align_oil_to_a_share_oos(observations, _calendar("2022-12-02"))


def test_old_oil_adapter_rejects_holdout_observation() -> None:
    observations = pd.DataFrame(
        {"observation_date": pd.to_datetime(["2023-01-02"]), "price": [80.0]}
    )
    with pytest.raises(Stage3BContractError):
        align_oil_to_a_share(observations, _calendar("2022-12-05"))


def test_oil_duplicate_observation_is_rejected() -> None:
    observations, calendar = _oil_fixture()
    duplicate = pd.concat([observations, observations.iloc[[0]]], ignore_index=True)
    with pytest.raises(DuplicateKeyError):
        align_oil_to_a_share_oos(duplicate, calendar)


def test_cni_old_and_new_adapters_match_on_pre_holdout_fixture() -> None:
    closes, calendar = _cni_fixture()
    old = build_cni_returns(closes, calendar)
    new = build_cni_returns_oos(closes, calendar)
    pd.testing.assert_frame_equal(old, new)


def test_cni_missing_day_is_gap_without_forward_fill() -> None:
    closes = pd.DataFrame(
        {
            "trade_date": pd.to_datetime(["2022-12-01", "2022-12-05"]),
            "index_code": "399439",
            "close": [100.0, 105.0],
        }
    )
    result = build_cni_returns_oos(closes, _calendar("2022-12-01", "2022-12-02", "2022-12-05"))
    assert result.loc[1, "alignment_status"] == "INDUSTRY_ROW_INVALID_DATA_GAP"
    assert pd.isna(result.loc[1, "industry_return"])


@pytest.mark.parametrize("bad_code", ["801960", "399438"])
def test_cni_identity_is_exact(bad_code: str) -> None:
    closes, calendar = _cni_fixture()
    closes["index_code"] = bad_code
    with pytest.raises(ValueError, match="identity"):
        build_cni_returns_oos(closes, calendar)


def test_old_industry_adapter_remains_development_only() -> None:
    closes = pd.DataFrame(
        {
            "trade_date": pd.to_datetime(["2023-01-03"]),
            "symbol": "801960",
            "close": [100.0],
        }
    )
    with pytest.raises(Stage3BContractError):
        build_industry_returns(closes, _calendar("2023-01-03"))


@pytest.mark.parametrize("raw", [b"x 2026/08/14"])
def test_oos_bounded_raw_proof_rejects_future_date(raw: bytes) -> None:
    with pytest.raises(ValueError, match="UNBOUNDED"):
        prove_bounded_raw(raw)


def test_oos_bounded_raw_proof_accepts_exact_end() -> None:
    proof = prove_bounded_raw(b"DATE,DCOILBRENTEU\n2026-08-13,80\n")
    assert proof["raw_observation_date_max"] == "2026-08-13"


def test_fred_bounded_raw_proof_rejects_future_date() -> None:
    with pytest.raises(Stage3BContractError):
        prove_bounded_raw_response(b"DATE,DCOILBRENTEU\n2023-01-03,80\n", end="2022-12-30")


def test_cni_bounded_raw_proof_rejects_future_date() -> None:
    with pytest.raises(Stage3BContractError):
        prove_cni_bounded_raw_response(
            b'{"data":{"data":[["2026-08-14",0,0,80]]}}', end="2026-08-13"
        )


def test_authorization_freezes_single_execution_and_forbids_search() -> None:
    auth = json.loads((ROOT / "reports/m3_stage3db_execution_authorization_v1.json").read_text())
    assert auth["accepted_execution_max_count"] == 1
    assert auth["robustness_search_allowed"] is False
    assert auth["new_model_allowed"] is False
    assert auth["new_proxy_allowed"] is False


def test_result_schema_forbids_daily_and_bootstrap_vectors() -> None:
    schema = json.loads(
        (ROOT / "reports/m3_stage3db_holdout_primary_result_schema_v1.json").read_text()
    )
    forbidden = set(schema["forbidden_fields"])
    assert {"daily_matrix", "daily_crash_flags", "bootstrap_vector"} <= forbidden
    assert forbidden.isdisjoint(schema["allowed_fields"])


def test_adapter_digest_is_stable_and_repository_relative() -> None:
    digest, payload = build_oos_execution_adapter_digest(ROOT)
    assert len(digest) == 64
    encoded = json.dumps(payload, ensure_ascii=False)
    assert "D:\\" not in encoded
    assert all(not Path(key).is_absolute() for key in payload["source_hashes"])


def test_oos_inputs_have_no_network_or_statistical_imports() -> None:
    source = (ROOT / "src/ashare_research/tools/m3_stage3db_oos_inputs.py").read_text()
    tree = ast.parse(source)
    imported = {
        alias.name.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    assert not ({"requests", "urllib", "statsmodels", "scipy"} & imported)


def test_preunseal_validator_has_no_network_or_model_execution_calls() -> None:
    source = (ROOT / "src/ashare_research/tools/m3_stage3db_preunseal_check.py").read_text()
    tree = ast.parse(source)
    calls = {
        node.func.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
    }
    assert not ({"get", "post", "moving_block_bootstrap", "fit_primary_ols"} & calls)


def test_frozen_date_constants_are_exact() -> None:
    assert pd.Timestamp("2022-12-01") == WARMUP_START
    assert pd.Timestamp("2023-01-01") == HOLDOUT_START
    assert pd.Timestamp("2026-08-13") == HOLDOUT_END
