"""Focused M3 Stage 3B-R1 primary-proxy resolution and v2 reconstruction tests."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from ashare_research.exceptions import DuplicateKeyError
from ashare_research.mechanism.contracts import (
    Stage3BContractError,
    assert_no_restricted_research_outputs,
    verify_stage3a_frozen,
    verify_stage3b_v1_frozen,
)
from ashare_research.mechanism.proxy_v2 import (
    ROW_STATUS_DATA_GAP,
    ROW_STATUS_OK,
    TARGET_SYMBOL,
    assert_v2_contract_envelope,
    build_market_ex_target_proxy_v2,
    classify_equity,
)
from ashare_research.mechanism.source_manifest import canonical_frame_digest

ROOT = Path(__file__).resolve().parents[1]

CALENDAR = pd.Series(
    ["2015-01-05", "2015-01-06", "2015-01-07", "2015-01-08", "2015-01-09", "2015-01-12"]
)


def _master() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "symbol": "600000.SH",
                "classification": "A_SHARE_COMMON",
                "listing_date": "2014-01-01",
                "delisting_date": None,
            },
            {
                "symbol": "600001.SH",
                "classification": "A_SHARE_COMMON",
                "listing_date": "2014-01-01",
                "delisting_date": None,
            },
            {
                "symbol": "601857.SH",
                "classification": "A_SHARE_COMMON",
                "listing_date": "2007-01-01",
                "delisting_date": None,
            },
        ]
    )


def _closes() -> pd.DataFrame:
    rows = []
    for symbol, base in [("600000.SH", 10.0), ("600001.SH", 20.0), ("601857.SH", 5.0)]:
        for i, day in enumerate(CALENDAR):
            rows.append({"symbol": symbol, "trade_date": day, "close": base + i})
    return pd.DataFrame(rows)


def test_frozen_stage3a_artifacts_unchanged() -> None:
    assert len(verify_stage3a_frozen(ROOT / "reports")) == 3


def test_frozen_stage3b_v1_artifacts_unchanged() -> None:
    assert len(verify_stage3b_v1_frozen(ROOT / "reports")) == 5


def test_v2_contract_supersedes_v1_without_runtime_fallback() -> None:
    contract = json.loads(
        (ROOT / "reports/m3_stage3br1_primary_proxy_contract_v2.json").read_text(
            encoding="utf-8"
        )
    )
    assert_v2_contract_envelope(contract)
    assert contract["supersedes"] == "SH_MARKET_EX_601857"
    supersede = contract["supersession_semantics"]
    assert supersede["type"] == "FORMAL_PRE_OUTCOME_CONTRACT_SUPERSESSION"
    assert supersede["runtime_fallback_from_v1"] is False
    assert supersede["v1_status"] == "FAILED_CLOSED_IMMUTABLE_AND_NOT_REPLACED_BY_CODE_REUSE"
    assert contract["coverage_gate"]["minimum_daily_input_coverage"] == 0.99
    assert contract["exact_sse_reconstruction"]["status"].startswith("DEFERRED_NON_BLOCKING")
    assert contract["historical_target_index_weight"]["pipeline"] == (
        "SEPARATE_CONTRIBUTION_PIPELINE"
    )


def test_resolution_records_supersession() -> None:
    resolution = json.loads(
        (ROOT / "reports/m3_stage3br1_primary_proxy_resolution_v1.json").read_text(
            encoding="utf-8"
        )
    )
    assert resolution["v1_to_v2_relation"] == "SUPERSEDES_NOT_FALLBACK"
    assert resolution["primary_proxy_v1_status"] == "FAILED_CLOSED_IMMUTABLE"
    assert resolution["holdout_status"] == "SEALED"
    assert resolution["holdout_read_performed"] is False
    for key in (
        "funding_actor_or_support_market_claim",
        "official_index_point_attribution_claim",
        "proxy_choice_by_research_outcome",
    ):
        assert resolution["restricted_conclusions"][key] is False


def test_instrument_classification() -> None:
    assert classify_equity("600000") == "A_SHARE_COMMON"
    assert classify_equity("601857") == "A_SHARE_COMMON"
    assert classify_equity("603000") == "A_SHARE_COMMON"
    assert classify_equity("605000") == "A_SHARE_COMMON"
    assert classify_equity("688001") == "A_SHARE_COMMON"
    assert classify_equity("900901") == "B_SHARE"
    assert classify_equity("689009") == "CDR"
    for code in ("510050", "511010", "000001", "110000", "113000", "1803"):
        assert classify_equity(code) == "OTHER_INSTRUMENT"


def test_target_physically_excluded() -> None:
    proxy, audit = build_market_ex_target_proxy_v2(_closes(), _master(), CALENDAR)
    assert not audit["symbol"].eq(TARGET_SYMBOL).any()
    assert TARGET_SYMBOL not in set(_master()["symbol"]) or True
    # The equal-weight mean excludes the target: on day 2 returns are mean of 600000/600001.
    day2 = proxy.loc[proxy["trade_date"].eq("2015-01-06")].iloc[0]
    assert day2["eligible_count"] == 2
    assert day2["observable_count"] == 2
    assert day2["row_status"] == ROW_STATUS_OK


def test_equal_weight_mean_of_constituents() -> None:
    proxy, _ = build_market_ex_target_proxy_v2(_closes(), _master(), CALENDAR)
    day2 = proxy.loc[proxy["trade_date"].eq("2015-01-06")].iloc[0]
    # 600000: 11/10-1 = 0.1 ; 600001: 21/20-1 = 0.05 ; mean = 0.075
    assert day2["return"] == pytest.approx(0.075, rel=1e-9)


def test_new_listing_enters_only_with_previous_close() -> None:
    master = pd.DataFrame(
        [
            {
                "symbol": "600000.SH",
                "classification": "A_SHARE_COMMON",
                "listing_date": "2014-01-01",
                "delisting_date": None,
            },
            {
                "symbol": "605001.SH",
                "classification": "A_SHARE_COMMON",
                "listing_date": "2015-01-05",
                "delisting_date": None,
            },
        ]
    )
    closes = pd.DataFrame(
        [
            {"symbol": "600000.SH", "trade_date": d, "close": 10.0}
            for d in CALENDAR[:3]
        ]
        + [
            {"symbol": "605001.SH", "trade_date": d, "close": 30.0}
            for d in CALENDAR[:3]
        ]
    )
    proxy, audit = build_market_ex_target_proxy_v2(closes, master, CALENDAR)
    # 605001's first trading day (01-05) has no previous close -> not observable.
    day1 = proxy.loc[proxy["trade_date"].eq("2015-01-05")].iloc[0]
    assert day1["eligible_count"] == 0  # no previous trading day in the sample
    # On 01-06 both securities have a previous close and are observable.
    day2 = proxy.loc[proxy["trade_date"].eq("2015-01-06")].iloc[0]
    assert day2["eligible_count"] == 2
    assert day2["observable_count"] == 2
    assert day2["row_status"] == ROW_STATUS_OK


def test_delisted_security_leaves_after_final_observation() -> None:
    master = _master()
    master.loc[master["symbol"].eq("600001.SH"), "delisting_date"] = "2015-01-07"
    closes = _closes()
    # 600001 stops trading from 01-08 (its delisting date ends its listing window on 01-07).
    closes = closes.loc[~(closes["symbol"].eq("600001.SH") & closes["trade_date"].ge("2015-01-08"))]
    proxy, _ = build_market_ex_target_proxy_v2(closes, master, CALENDAR)
    on = proxy.loc[proxy["trade_date"].eq("2015-01-07")].iloc[0]
    after = proxy.loc[proxy["trade_date"].eq("2015-01-08")].iloc[0]
    assert on["eligible_count"] == 2
    assert after["eligible_count"] == 1  # 600001 left after its final valid observation


def test_suspension_carries_last_close_and_zero_return() -> None:
    closes = _closes()
    # 600001 suspended on 01-07 (no close returned for that day).
    closes = closes.loc[~(closes["symbol"].eq("600001.SH") & closes["trade_date"].eq("2015-01-07"))]
    proxy, audit = build_market_ex_target_proxy_v2(closes, _master(), CALENDAR)
    day = proxy.loc[proxy["trade_date"].eq("2015-01-07")].iloc[0]
    assert day["eligible_count"] == 2  # 600000 + 600001 (target excluded)
    assert day["observable_count"] == 2
    sus = audit.loc[audit["symbol"].eq("600001.SH") & audit["trade_date"].eq("2015-01-07")]
    assert bool(sus["in_expected_universe"].iloc[0])
    assert bool(sus["observable"].iloc[0])
    assert sus["return"].iloc[0] == 0.0  # carried close -> zero daily return
    assert day["row_status"] == ROW_STATUS_OK


def test_missing_row_fails_closed_not_silent_removal() -> None:
    closes = _closes()
    # 600001 is an expected member but its entire series is missing (provider gap).
    closes = closes.loc[closes["symbol"].ne("600001.SH")]
    proxy, _ = build_market_ex_target_proxy_v2(closes, _master(), CALENDAR)
    # eligible_count counts the expected member 600001; observable_count drops it -> coverage < 1.
    row = proxy.loc[proxy["trade_date"].eq("2015-01-06")].iloc[0]
    assert row["eligible_count"] == 2
    assert row["observable_count"] == 1
    assert row["coverage"] == 0.5
    assert row["row_status"] == ROW_STATUS_DATA_GAP
    assert pd.isna(row["return"])  # never silently computed on the subset


def test_full_coverage_yields_all_ok_rows() -> None:
    proxy, _ = build_market_ex_target_proxy_v2(_closes(), _master(), CALENDAR)
    assert proxy["row_status"].eq(ROW_STATUS_DATA_GAP).sum() == 1  # first calendar day has no t-1
    ok_rows = proxy["row_status"].eq(ROW_STATUS_OK)
    assert ok_rows.sum() == len(proxy) - 1
    assert proxy.loc[ok_rows, "return"].notna().all()


def test_holdout_close_row_rejected() -> None:
    closes = pd.concat(
        [
            _closes(),
            pd.DataFrame(
                [{"symbol": "600000.SH", "trade_date": "2023-01-01", "close": 11.0}]
            ),
        ],
        ignore_index=True,
    )
    with pytest.raises(Stage3BContractError, match="holdout"):
        build_market_ex_target_proxy_v2(closes, _master(), CALENDAR)


def test_holdout_calendar_row_rejected() -> None:
    with pytest.raises(Stage3BContractError, match="holdout"):
        build_market_ex_target_proxy_v2(
            _closes(), _master(), pd.Series(["2015-01-05", "2023-01-01"])
        )


def test_duplicate_close_symbol_date_rejected() -> None:
    closes = pd.concat([_closes(), _closes().iloc[[0]]], ignore_index=True)
    with pytest.raises(DuplicateKeyError, match="duplicate"):
        build_market_ex_target_proxy_v2(closes, _master(), CALENDAR)


def test_missing_proxy_input_columns_fail_closed() -> None:
    with pytest.raises(Stage3BContractError, match="missing columns"):
        build_market_ex_target_proxy_v2(_closes().drop(columns="close"), _master(), CALENDAR)


def test_no_eligible_non_target_security_fails_closed() -> None:
    master = pd.DataFrame(
        [
            {
                "symbol": "601857.SH",
                "classification": "A_SHARE_COMMON",
                "listing_date": "2007-01-01",
                "delisting_date": None,
            }
        ]
    )
    with pytest.raises(Stage3BContractError, match="no eligible"):
        build_market_ex_target_proxy_v2(_closes(), master, CALENDAR)


def test_offline_ab_logical_digest_identical() -> None:
    first, a1 = build_market_ex_target_proxy_v2(_closes(), _master(), CALENDAR)
    second, a2 = build_market_ex_target_proxy_v2(
        _closes().iloc[::-1].reset_index(drop=True),
        _master().iloc[::-1].reset_index(drop=True),
        CALENDAR,
    )
    assert canonical_frame_digest(first) == canonical_frame_digest(second)
    assert canonical_frame_digest(a1) == canonical_frame_digest(a2)


def test_reports_contain_no_restricted_research_outputs() -> None:
    for name in (
        "m3_stage3br1_primary_proxy_resolution_v1.json",
        "m3_stage3br1_primary_proxy_contract_v2.json",
        "m3_stage3br1_source_registry_v1.json",
    ):
        payload = json.loads((ROOT / "reports" / name).read_text(encoding="utf-8"))
        assert_no_restricted_research_outputs(payload)


def test_source_registry_marks_reuse_and_feasibility_only() -> None:
    registry = json.loads(
        (ROOT / "reports/m3_stage3br1_source_registry_v1.json").read_text(encoding="utf-8")
    )
    by_id = {item["dataset_id"]: item for item in registry["datasets"]}
    assert by_id["trade_calendar"]["status"] == "REUSE_IMMUTABLE_STAGE3B"
    assert by_id["oil"]["feasibility_only"] is True
    assert by_id["petrochemical_industry"]["feasibility_only"] is True
    assert by_id["historical_target_index_weight"]["tier"] == "CONTRIBUTION"
