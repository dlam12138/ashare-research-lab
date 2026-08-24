"""Offline R4 contract, bounded-transport, normalization, and readiness tests."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from ashare_research.exceptions import DuplicateKeyError
from ashare_research.mechanism.acquisition_cni import (
    CNI_ENDPOINT,
    CNI_INDEX_CODE,
    CNI_STATUS_DATA_GAP,
    CNI_STATUS_OK,
    acquire_cni_bounded,
    build_cni_returns,
    inspect_akshare_cni_source,
    parse_cni_response_bytes,
)
from ashare_research.mechanism.acquisition_cni import (
    STATUS_NOT_BOUNDED as CNI_NOT_BOUNDED,
)
from ashare_research.mechanism.acquisition_cni import (
    STATUS_RAW_HOLDOUT as CNI_HOLDOUT,
)
from ashare_research.mechanism.acquisition_cni import (
    STATUS_WRONG_IDENTITY as CNI_WRONG_IDENTITY,
)
from ashare_research.mechanism.acquisition_fred_public import (
    FRED_SERIES,
    acquire_fred_bounded,
    normalize_fred,
    parse_fred_csv_bytes,
)
from ashare_research.mechanism.acquisition_fred_public import (
    STATUS_INVALID_NUMERIC as FRED_INVALID_NUMERIC,
)
from ashare_research.mechanism.acquisition_fred_public import (
    STATUS_RAW_HOLDOUT as FRED_HOLDOUT,
)
from ashare_research.mechanism.acquisition_fred_public import (
    STATUS_REQUEST_UNBOUNDED as FRED_REQUEST_UNBOUNDED,
)
from ashare_research.mechanism.acquisition_fred_public import (
    STATUS_WRONG_SERIES as FRED_WRONG_SERIES,
)
from ashare_research.mechanism.alignment import build_tier1_readiness, summarize_readiness
from ashare_research.mechanism.contracts import (
    assert_no_restricted_research_outputs,
    verify_stage3a_frozen,
    verify_stage3b_v1_frozen,
    verify_stage3br1_frozen,
    verify_stage3br2_frozen,
    verify_stage3br3_frozen,
)
from ashare_research.mechanism.source_manifest import canonical_frame_digest

ROOT = Path(__file__).resolve().parents[1]


def _fred_bytes(value: str = "") -> bytes:
    return (
        f"DATE,DCOILBRENTEU\n2014-12-31,55.10\n2015-01-02,{value or '.'}\n2015-01-05,56.10\n"
    ).encode()


def _cni_bytes(*, holdout: bool = False, end_extra: bool = False, duplicate: bool = False) -> bytes:
    rows: list[list[object]] = [
        ["2014-12-30", "", "101", "100", "99", "100", "", "", "", "", "", ""],
        ["2015-01-05", "", "102", "101", "100", "101", "", "", "", "", "", ""],
    ]
    if end_extra:
        rows.append(["2022-12-30", "", "103", "102", "101", "102", "", "", "", "", "", ""])
    if holdout:
        rows.append(["2023-01-03", "", "104", "103", "102", "103", "", "", "", "", "", ""])
    if duplicate:
        rows.append(rows[-1].copy())
    return json.dumps({"data": {"data": rows}}, ensure_ascii=False).encode()


def test_all_prior_frozen_artifact_hashes_remain_unchanged() -> None:
    assert len(verify_stage3a_frozen(ROOT / "reports")) == 3
    assert len(verify_stage3b_v1_frozen(ROOT / "reports")) == 5
    assert len(verify_stage3br1_frozen(ROOT / "reports")) == 5
    assert len(verify_stage3br2_frozen(ROOT / "reports")) == 6
    assert len(verify_stage3br3_frozen(ROOT / "reports")) == 6


def test_r4_reports_are_pre_outcome_and_restricted_output_free() -> None:
    names = [
        "m3_stage3br4_source_amendment_v1.json",
        "m3_stage3br4_oil_transport_contract_v3.json",
        "m3_stage3br4_industry_contract_v2.json",
        "m3_stage3br4_source_registry_v1.json",
        "m3_stage3br4_development_input_manifest_v1.json",
        "m3_stage3br4_data_coverage_v1.json",
        "m3_stage3br4_tier1_readiness_v3.json",
    ]
    for name in names:
        payload = json.loads((ROOT / "reports" / name).read_text(encoding="utf-8"))
        assert_no_restricted_research_outputs(payload)
        assert payload["stage"] == "M3_STAGE3BR4"
        assert payload["holdout_status"] == "SEALED"


def test_fred_transport_has_no_api_key_and_requires_explicit_bounds(tmp_path: Path) -> None:
    calls: list[dict[str, object]] = []

    def http_get(url: str, *, params: dict[str, object]) -> bytes:
        calls.append({"url": url, **params})
        return _fred_bytes()

    result = acquire_fred_bounded(tmp_path, start="2014-12-01", end="2022-12-31", http_get=http_get)
    assert result["series_id"] == FRED_SERIES
    assert calls[0]["url"] != ""
    assert "api_key" not in calls[0]
    assert calls[0]["cosd"] == "2014-12-01" and calls[0]["coed"] == "2022-12-31"
    with pytest.raises(Exception, match=FRED_REQUEST_UNBOUNDED):
        acquire_fred_bounded(tmp_path, http_get=http_get)
    with pytest.raises(Exception, match=FRED_REQUEST_UNBOUNDED):
        acquire_fred_bounded(tmp_path, start="2014-12-01", end="2023-01-01", http_get=http_get)


def test_fred_raw_holdout_is_rejected_before_normalization() -> None:
    raw = _fred_bytes().replace(b"2015-01-05", b"2023-01-05")
    with pytest.raises(Exception, match=FRED_HOLDOUT):
        parse_fred_csv_bytes(raw, start="2014-12-01", end="2022-12-31")


def test_fred_identity_numeric_and_missing_value_rules() -> None:
    parsed = parse_fred_csv_bytes(_fred_bytes(), start="2014-12-01", end="2022-12-31")
    assert len(parsed) == 2
    assert parsed["series_id"].eq(FRED_SERIES).all()
    actual_header = _fred_bytes().replace(b"DATE,DCOILBRENTEU", b"observation_date,DCOILBRENTEU")
    assert len(parse_fred_csv_bytes(actual_header, start="2014-12-01", end="2022-12-31")) == 2
    with pytest.raises(Exception, match=FRED_WRONG_SERIES):
        parse_fred_csv_bytes(
            _fred_bytes().replace(b"DCOILBRENTEU", b"WRONG"), start="2014-12-01", end="2022-12-31"
        )
    with pytest.raises(Exception, match=FRED_INVALID_NUMERIC):
        parse_fred_csv_bytes(_fred_bytes("bad"), start="2014-12-01", end="2022-12-31")


def test_fred_duplicate_and_offline_ab_identity(tmp_path: Path) -> None:
    duplicate = b"DATE,DCOILBRENTEU\n2015-01-02,55\n2015-01-02,56\n"
    with pytest.raises(DuplicateKeyError):
        parse_fred_csv_bytes(duplicate, start="2014-12-01", end="2022-12-31")
    raw = tmp_path / "raw.csv"
    raw.write_bytes(_fred_bytes())
    a = tmp_path / "a.csv"
    b = tmp_path / "b.csv"
    normalize_fred(raw, a, start="2014-12-01", end="2022-12-31")
    normalize_fred(raw, b, start="2014-12-01", end="2022-12-31")
    assert canonical_frame_digest(pd.read_csv(a)) == canonical_frame_digest(pd.read_csv(b))


def test_akshare_cni_source_inspection_confirms_server_bounds() -> None:
    source = (
        "url = 'getIndexDailyDataWithDataFormat'; params = "
        "{'indexCode': symbol, 'startDate': start_date, 'endDate': end_date}"
    )
    inspected = inspect_akshare_cni_source(source)
    assert inspected["server_bounds_reach_endpoint"] is True
    assert inspected["local_filter_only"] is False
    assert CNI_ENDPOINT in inspected["underlying_endpoint"]
    rejected = inspect_akshare_cni_source("requests.get(url, params={'indexCode': symbol})")
    assert rejected["server_bounds_reach_endpoint"] is False


def test_cni_identity_and_bounded_raw_response() -> None:
    parsed = parse_cni_response_bytes(
        _cni_bytes(), index_code=CNI_INDEX_CODE, start="2014-12-01", end="2022-12-31"
    )
    assert len(parsed) == 2
    assert parsed["index_code"].eq(CNI_INDEX_CODE).all()
    with pytest.raises(Exception, match=CNI_WRONG_IDENTITY):
        parse_cni_response_bytes(
            _cni_bytes(), index_code="000928", start="2014-12-01", end="2022-12-31"
        )
    with pytest.raises(Exception, match=CNI_HOLDOUT):
        parse_cni_response_bytes(
            _cni_bytes(holdout=True),
            index_code=CNI_INDEX_CODE,
            start="2014-12-01",
            end="2022-12-31",
        )
    with pytest.raises(Exception, match=CNI_NOT_BOUNDED):
        parse_cni_response_bytes(
            _cni_bytes(end_extra=True),
            index_code=CNI_INDEX_CODE,
            start="2014-12-01",
            end="2022-01-01",
        )


def test_cni_duplicate_and_bounded_acquisition_does_not_filter_unbounded_response(
    tmp_path: Path,
) -> None:
    with pytest.raises(DuplicateKeyError):
        parse_cni_response_bytes(
            _cni_bytes(duplicate=True),
            index_code=CNI_INDEX_CODE,
            start="2014-12-01",
            end="2022-12-31",
        )

    calls: list[dict[str, object]] = []

    def http_get(url: str, *, params: dict[str, object]) -> bytes:
        calls.append({"url": url, **params})
        return _cni_bytes()

    result = acquire_cni_bounded(tmp_path, start="2014-12-01", end="2022-12-31", http_get=http_get)
    assert result["index_code"] == CNI_INDEX_CODE
    assert calls[0]["indexCode"] == CNI_INDEX_CODE
    assert calls[0]["startDate"] == "2014-12-01" and calls[0]["endDate"] == "2022-12-31"
    assert (tmp_path / "raw/cni_399439_response.json").is_file()


def test_cni_simple_return_missing_day_gap_and_no_forward_fill() -> None:
    closes = pd.DataFrame(
        [
            {"trade_date": "2015-01-05", "index_code": CNI_INDEX_CODE, "close": 100.0},
            {"trade_date": "2015-01-07", "index_code": CNI_INDEX_CODE, "close": 110.0},
        ]
    )
    result = build_cni_returns(closes, pd.Series(["2015-01-05", "2015-01-06", "2015-01-07"]))
    assert result.loc[1, "alignment_status"] == CNI_STATUS_DATA_GAP
    assert pd.isna(result.loc[1, "industry_return"])
    assert result.loc[2, "alignment_status"] == CNI_STATUS_OK
    assert result.loc[2, "industry_return"] == pytest.approx(0.10)


def test_joint_readiness_requires_market_oil_and_cni() -> None:
    dates = pd.Series(["2015-01-05", "2015-01-06"])
    oil = pd.DataFrame(
        [
            {
                "a_share_trade_date": "2015-01-05",
                "oil_return": None,
                "alignment_status": "OIL_ROW_OK",
            },
            {
                "a_share_trade_date": "2015-01-06",
                "oil_return": 0.1,
                "alignment_status": "OIL_ROW_OK",
            },
        ]
    )
    industry = build_cni_returns(
        pd.DataFrame(
            [
                {"trade_date": "2015-01-05", "index_code": CNI_INDEX_CODE, "close": 100.0},
                {"trade_date": "2015-01-06", "index_code": CNI_INDEX_CODE, "close": 101.0},
            ]
        ),
        dates,
    )
    proxy = pd.DataFrame({"trade_date": dates, "row_status": ["PROXY_ROW_OK", "PROXY_ROW_OK"]})
    readiness = build_tier1_readiness(proxy, oil, industry)
    assert readiness["tier1_joint_valid"].tolist() == [False, True]
    assert summarize_readiness(readiness)["joint_tier1_valid_dates"] == 1
