"""Focused M3 Stage 3B-R2 oil/industry acquisition and Tier-1 alignment tests."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from ashare_research.exceptions import DuplicateKeyError
from ashare_research.mechanism.alignment import build_tier1_readiness, summarize_readiness
from ashare_research.mechanism.contracts import (
    Stage3BContractError,
    assert_no_restricted_research_outputs,
    verify_stage3a_frozen,
    verify_stage3b_v1_frozen,
    verify_stage3br1_frozen,
)
from ashare_research.mechanism.industry import (
    REGIME_1_SYMBOL,
    REGIME_2_SYMBOL,
    STATUS_DATA_GAP,
    STATUS_NO_PREVIOUS_VALID,
    STATUS_TRANSITION_GAP,
    _regime_for,
    assert_industry_contract_envelope,
    build_industry_returns,
)
from ashare_research.mechanism.industry import (
    STATUS_OK as INDUSTRY_OK,
)
from ashare_research.mechanism.oil import (
    STATUS_NO_ANCHOR,
    STATUS_STALE_ANCHOR,
    align_oil_to_a_share,
    assert_oil_v2_contract_envelope,
    compare_oil_sources,
)
from ashare_research.mechanism.oil import (
    STATUS_OK as OIL_OK,
)
from ashare_research.mechanism.source_manifest import canonical_frame_digest, verify_raw_manifest

ROOT = Path(__file__).resolve().parents[1]


def _obs(rows: list[tuple[str, float]]) -> pd.DataFrame:
    return pd.DataFrame(rows, columns=["observation_date", "price"])


def _ind_closes(rows: list[tuple[str, str, float]]) -> pd.DataFrame:
    return pd.DataFrame(rows, columns=["trade_date", "symbol", "close"])


# --------------------------------------------------------------------------- frozen hashes

def test_frozen_stage3a_artifacts_unchanged() -> None:
    assert len(verify_stage3a_frozen(ROOT / "reports")) == 3


def test_frozen_stage3b_v1_artifacts_unchanged() -> None:
    assert len(verify_stage3b_v1_frozen(ROOT / "reports")) == 5


def test_frozen_stage3br1_artifacts_unchanged() -> None:
    assert len(verify_stage3br1_frozen(ROOT / "reports")) == 5


# --------------------------------------------------------------------------- oil contract v2

def test_oil_contract_v2_explicit_supersession() -> None:
    contract = json.loads(
        (ROOT / "reports/m3_stage3br2_oil_contract_v2.json").read_text(encoding="utf-8")
    )
    assert_oil_v2_contract_envelope(contract)
    assert contract["supersedes"]["artifact_id"] == "m3_stage3b_return_and_timing_contract_v1.json"
    assert contract["supersession_semantics"]["runtime_fallback_from_v1"] is False
    assert contract["primary_benchmark"]["eia_series"] == "RBRTE"
    assert contract["primary_benchmark"]["fred_mirror"] == "DCOILBRENTEU"
    assert "WTI" in contract["primary_benchmark"]["not_substitutable_with"]


def test_oil_timing_resolution_supersedes_publication_timestamp() -> None:
    resolution = json.loads(
        (ROOT / "reports/m3_stage3br2_oil_timing_resolution_v1.json").read_text(encoding="utf-8")
    )
    assert resolution["type"] == "FORMAL_PRE_OUTCOME_TIMING_SUPERSESSION"
    assert resolution["frozen_policy"]["alignment"] == "STRICTLY_PRIOR_BRENT_OBSERVATION_DATE"
    ss = resolution["supersession_semantics"]
    assert ss["same_calendar_day_overseas_observation_still_prohibited"] is True
    assert ss["v1_publication_timestamp_requirement"] == "SUPERSEDED_PRE_OUTCOME"
    assert resolution["frozen_policy"]["stale_gate_override_allowed"] is False


# --------------------------------------------------------------------------- oil binding


def test_same_day_brent_observation_rejected() -> None:
    # A Brent observation dated the same calendar day as the A-share day is never its anchor.
    once = align_oil_to_a_share(
        _obs([("2015-01-02", 50.0), ("2015-01-05", 55.0)]),
        pd.Series(["2015-01-05"]),
    )
    row = once.iloc[0]
    assert row["oil_anchor_date"] == "2015-01-02"
    assert row["oil_anchor_price"] == 50.0
    assert row["alignment_status"] == OIL_OK


def test_strict_prior_brent_date_accepted() -> None:
    once = align_oil_to_a_share(
        _obs([("2015-01-02", 50.0)]),
        pd.Series(["2015-01-05"]),
    )
    row = once.iloc[0]
    assert row["oil_anchor_date"] == "2015-01-02"
    assert row["oil_anchor_age_days"] == 3
    assert row["alignment_status"] == OIL_OK


def test_weekend_uses_prior_friday_anchor() -> None:
    aligned = align_oil_to_a_share(
        _obs([("2015-01-02", 50.0), ("2015-01-05", 55.0)]),
        pd.Series(["2015-01-05", "2015-01-06"]),
    )
    mon = aligned.iloc[0]
    tue = aligned.iloc[1]
    assert mon["oil_anchor_date"] == "2015-01-02"
    assert mon["oil_anchor_price"] == 50.0
    assert tue["oil_anchor_date"] == "2015-01-05"
    assert tue["oil_anchor_price"] == 55.0
    assert tue["oil_return"] == pytest.approx(55.0 / 50.0 - 1.0, rel=1e-9)


def test_chinese_holiday_cumulative_anchor_behavior() -> None:
    # A long A-share break absorbs the entire Brent change between the two A-share anchor prices.
    aligned = align_oil_to_a_share(
        _obs([("2015-02-13", 100.0), ("2015-02-27", 110.0)]),
        pd.Series(["2015-02-16", "2015-03-02"]),
    )
    after = aligned.iloc[1]
    assert after["previous_oil_anchor_date"] == "2015-02-13"
    assert after["oil_anchor_date"] == "2015-02-27"
    assert after["oil_return"] == pytest.approx(110.0 / 100.0 - 1.0, rel=1e-9)


def test_same_anchor_yields_zero_return() -> None:
    aligned = align_oil_to_a_share(
        _obs([("2015-01-02", 50.0)]),
        pd.Series(["2015-01-05", "2015-01-06"]),
    )
    assert aligned.iloc[1]["oil_anchor_date"] == "2015-01-02"
    assert aligned.iloc[1]["oil_return"] == 0.0


def test_stale_anchor_rejected() -> None:
    aligned = align_oil_to_a_share(
        _obs([("2015-01-08", 50.0)]),
        pd.Series(["2015-01-20"]),
    )
    row = aligned.iloc[0]
    assert row["oil_anchor_age_days"] == 12
    assert row["alignment_status"] == STATUS_STALE_ANCHOR
    assert pd.isna(row["oil_return"])


def test_no_prior_observation_is_invalid_no_anchor() -> None:
    aligned = align_oil_to_a_share(
        _obs([("2015-01-06", 50.0)]),
        pd.Series(["2015-01-05"]),
    )
    assert aligned.iloc[0]["alignment_status"] == STATUS_NO_ANCHOR


def test_holdout_oil_observation_rejected() -> None:
    with pytest.raises(Stage3BContractError, match="holdout"):
        align_oil_to_a_share(
            _obs([("2023-01-01", 50.0)]),
            pd.Series(["2015-01-05"]),
        )


def test_duplicate_oil_observation_rejected() -> None:
    with pytest.raises(DuplicateKeyError, match="duplicate"):
        align_oil_to_a_share(
            pd.concat(
                [_obs([("2015-01-02", 50.0)]), _obs([("2015-01-02", 51.0)])],
                ignore_index=True,
            ),
            pd.Series(["2015-01-05"]),
        )


def test_eia_fred_source_conflict_fails_closed() -> None:
    eia = _obs([("2015-01-02", 50.0), ("2015-01-05", 55.0)])
    fred = _obs([("2015-01-02", 50.0), ("2015-01-05", 60.0)])
    result = compare_oil_sources(eia, fred)
    assert result["status"] == "OIL_SOURCE_CONFLICT"
    assert result["conflicts"] == ["2015-01-05"]


def test_eia_fred_source_consistent() -> None:
    eia = _obs([("2015-01-02", 50.0), ("2015-01-05", 55.0)])
    fred = _obs([("2015-01-02", 50.0), ("2015-01-05", 55.0)])
    assert compare_oil_sources(eia, fred)["status"] == "OIL_SOURCE_CONSISTENT"


# --------------------------------------------------------------------------- industry


def test_industry_801016_regime_boundary() -> None:
    assert _regime_for(pd.Timestamp("2021-12-10")) == ("801016", "SW_2014")
    assert _regime_for(pd.Timestamp("2021-11-01")) == ("801016", "SW_2014")


def test_industry_801960_regime_start() -> None:
    assert _regime_for(pd.Timestamp("2021-12-13")) == ("801960", "SW_2021")
    assert _regime_for(pd.Timestamp("2022-01-01")) == ("801960", "SW_2021")


def test_cross_taxonomy_return_rejected_and_transition_gap_explicit() -> None:
    cal = pd.Series(["2021-12-10", "2021-12-13", "2021-12-14"])
    closes = _ind_closes(
        [
            ("2021-12-10", REGIME_1_SYMBOL, 100.0),
            ("2021-12-13", REGIME_2_SYMBOL, 110.0),
            ("2021-12-14", REGIME_2_SYMBOL, 120.0),
        ]
    )
    ind = build_industry_returns(closes, cal)
    lex = {r["trade_date"]: r for _, r in ind.iterrows()}
    assert lex["2021-12-10"]["alignment_status"] == STATUS_NO_PREVIOUS_VALID
    assert lex["2021-12-13"]["alignment_status"] == STATUS_TRANSITION_GAP
    assert pd.isna(lex["2021-12-13"]["industry_return"])
    # The first legal 801960 return is only after a same-regime previous close exists.
    assert lex["2021-12-14"]["alignment_status"] == INDUSTRY_OK
    assert lex["2021-12-14"]["industry_return"] == pytest.approx(120.0 / 110.0 - 1.0, rel=1e-9)


def test_industry_missing_trading_date_fails_closed() -> None:
    cal = pd.Series(["2021-12-13", "2021-12-14", "2021-12-15"])
    closes = _ind_closes(
        [
            ("2021-12-13", REGIME_2_SYMBOL, 110.0),
            ("2021-12-15", REGIME_2_SYMBOL, 130.0),
        ]
    )
    ind = build_industry_returns(closes, cal)
    lex = {r["trade_date"]: r for _, r in ind.iterrows()}
    assert lex["2021-12-14"]["alignment_status"] == STATUS_DATA_GAP
    assert pd.isna(lex["2021-12-14"]["industry_return"])


def test_industry_forward_fill_rejected_not_fake_zero() -> None:
    cal = pd.Series(["2021-12-13", "2021-12-14", "2021-12-15"])
    closes = _ind_closes(
        [
            ("2021-12-13", REGIME_2_SYMBOL, 110.0),
            ("2021-12-15", REGIME_2_SYMBOL, 130.0),
        ]
    )
    ind = build_industry_returns(closes, cal)
    lex = {r["trade_date"]: r for _, r in ind.iterrows()}
    # 12-14 missing is NOT forward-filled to 110 with a fake zero return.
    assert pd.isna(lex["2021-12-14"]["industry_return"])
    assert lex["2021-12-14"]["alignment_status"] == STATUS_DATA_GAP


def test_holdout_industry_close_rejected() -> None:
    with pytest.raises(Stage3BContractError, match="holdout"):
        build_industry_returns(
            _ind_closes([("2023-01-03", REGIME_2_SYMBOL, 100.0)]),
            pd.Series(["2021-12-13"]),
        )


def test_industry_contract_envelope_frozen() -> None:
    contract = json.loads(
        (ROOT / "reports/m3_stage3b_return_and_timing_contract_v1.json").read_text(encoding="utf-8")
    )
    assert_industry_contract_envelope(contract)


# --------------------------------------------------------------------------- joint readiness


def _readiness_inputs() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    cal = pd.Series(["2015-01-05", "2015-01-06", "2015-01-07"])
    oil = align_oil_to_a_share(
        _obs([("2015-01-02", 50.0), ("2015-01-05", 55.0), ("2015-01-06", 56.0)]), cal
    )
    ind = build_industry_returns(
        _ind_closes(
            [
                ("2015-01-05", REGIME_1_SYMBOL, 100.0),
                ("2015-01-06", REGIME_1_SYMBOL, 101.0),
                ("2015-01-07", REGIME_1_SYMBOL, 102.0),
            ]
        ),
        cal,
    )
    proxy = pd.DataFrame(
        [
            {"trade_date": "2015-01-05", "row_status": "PROXY_ROW_OK"},
            {"trade_date": "2015-01-06", "row_status": "PROXY_ROW_OK"},
            {"trade_date": "2015-01-07", "row_status": "PROXY_ROW_OK"},
        ]
    )
    return oil, ind, proxy


def test_joint_readiness_requires_all_three_tier1_valid() -> None:
    oil, ind, proxy = _readiness_inputs()
    readiness = build_tier1_readiness(proxy, oil, ind)
    joint = readiness.loc[readiness["tier1_joint_valid"]]
    # First date has no previous oil anchor -> oil invalid -> not joint valid.
    assert readiness["tier1_joint_valid"].sum() == 2
    assert set(joint["trade_date"]) == {"2015-01-06", "2015-01-07"}


def test_market_proxy_r1_gap_remains_gap() -> None:
    oil, ind, proxy = _readiness_inputs()
    proxy.loc[proxy["trade_date"].eq("2015-01-07"), "row_status"] = (
        "PROXY_ROW_INVALID_DATA_GAP"
    )
    readiness = build_tier1_readiness(proxy, oil, ind)
    row = readiness.loc[readiness["trade_date"].eq("2015-01-07")].iloc[0]
    assert not bool(row["market_proxy_valid"])
    assert not bool(row["tier1_joint_valid"])
    assert "MARKET_PROXY_INVALID" in row["invalid_reason_codes"]


def test_no_restricted_research_outputs_in_readiness() -> None:
    oil, ind, proxy = _readiness_inputs()
    readiness = build_tier1_readiness(proxy, oil, ind)
    summary = summarize_readiness(readiness)
    assert_no_restricted_research_outputs(summary)
    for col in readiness.columns:
        assert_no_restricted_research_outputs({col: "x"})
    assert "601857" not in " ".join(readiness.columns)
    assert "crash" not in " ".join(readiness.columns).lower()


# --------------------------------------------------------------------------- offline identity


def test_offline_ab_logical_identity_oil() -> None:
    obs = _obs([("2015-01-02", 50.0), ("2015-01-05", 55.0), ("2015-01-06", 56.0)])
    cal = pd.Series(["2015-01-05", "2015-01-06", "2015-01-07"])
    a = align_oil_to_a_share(obs, cal)
    b = align_oil_to_a_share(
        obs.iloc[::-1].reset_index(drop=True), cal.iloc[::-1].reset_index(drop=True)
    )
    assert canonical_frame_digest(a) == canonical_frame_digest(b)


def test_offline_ab_logical_identity_industry() -> None:
    cal = pd.Series(["2021-12-13", "2021-12-14"])
    closes = _ind_closes(
        [
            ("2021-12-13", REGIME_2_SYMBOL, 110.0),
            ("2021-12-14", REGIME_2_SYMBOL, 121.0),
        ]
    )
    a = build_industry_returns(closes, cal)
    b = build_industry_returns(
        closes.iloc[::-1].reset_index(drop=True), cal.iloc[::-1].reset_index(drop=True)
    )
    assert canonical_frame_digest(a) == canonical_frame_digest(b)


def test_raw_hash_mismatch_fails_closed(tmp_path: Path) -> None:
    raw = tmp_path / "raw"
    raw.mkdir()
    (raw / "x.csv").write_text("a,b\n1,2\n", encoding="utf-8")
    with pytest.raises(Stage3BContractError, match="SHA"):
        verify_raw_manifest([{"raw_file_path": "x.csv", "raw_sha256": "0" * 64}], raw)


def test_r2_reports_contain_no_restricted_research_outputs() -> None:
    for name in (
        "m3_stage3br2_oil_timing_resolution_v1.json",
        "m3_stage3br2_oil_contract_v2.json",
        "m3_stage3br2_source_registry_v1.json",
        "m3_stage3br2_development_input_manifest_v1.json",
        "m3_stage3br2_data_coverage_v1.json",
        "m3_stage3br2_tier1_readiness_v1.json",
    ):
        payload = json.loads((ROOT / "reports" / name).read_text(encoding="utf-8"))
        assert_no_restricted_research_outputs(payload)


def test_r2_reports_declare_holdout_sealed_and_inputs_not_trusted() -> None:
    readiness = json.loads(
        (ROOT / "reports/m3_stage3br2_tier1_readiness_v1.json").read_text(encoding="utf-8")
    )
    assert readiness["holdout_status"] == "SEALED"
    assert readiness["holdout_read_performed"] is False
    assert readiness["market_ex_target"] == "TRUSTED"
    assert readiness["oil"] == "NOT_ACQUIRED"
    assert readiness["petrochemical_industry"] == "NOT_ACQUIRED"
    assert readiness["joint_tier1_dates"] == "NOT_READY"
    assert readiness["stage3c_status"] == "M3_STAGE3C_NOT_ALLOWED"
