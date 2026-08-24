"""Independent Stage 3D-B OOS input adapters.

The historical Stage 3B/3C adapters remain development-only and continue to reject
2023+.  This module contains the same frozen semantics with the separately authorized
2022-12-01..2026-08-13 acquisition envelope and a final 2023-01-01..2026-08-13 slice.
It has no network or statistical execution path.
"""

from __future__ import annotations

from bisect import bisect_left
from typing import Any

import numpy as np
import pandas as pd

from ashare_research.exceptions import DuplicateKeyError
from ashare_research.mechanism.proxy_v2 import TARGET_SYMBOL, _build_carried_close, _shift1
from ashare_research.mechanism.source_manifest import canonical_frame_digest

WARMUP_START = pd.Timestamp("2022-12-01")
HOLDOUT_START = pd.Timestamp("2023-01-01")
HOLDOUT_END = pd.Timestamp("2026-08-13")
MAX_OIL_ANCHOR_AGE_CALENDAR_DAYS = 7
OOS_PROXY_ID = "SH_A_SHARE_EQUAL_WEIGHT_EX_601857_V2"
PROXY_ROW_OK = "PROXY_ROW_OK"
PROXY_ROW_DATA_GAP = "PROXY_ROW_INVALID_DATA_GAP"
OIL_ROW_OK = "OIL_ROW_OK"
OIL_ROW_STALE = "OIL_ROW_INVALID_STALE_ANCHOR"
OIL_ROW_NO_ANCHOR = "OIL_ROW_INVALID_NO_ANCHOR"
INDUSTRY_ROW_OK = "INDUSTRY_ROW_OK"
INDUSTRY_ROW_NO_PREVIOUS = "INDUSTRY_ROW_NO_PREVIOUS_VALID"
INDUSTRY_ROW_DATA_GAP = "INDUSTRY_ROW_INVALID_DATA_GAP"


def _date_series(values: Any) -> pd.Series:
    dates = (
        pd.Series(pd.to_datetime(values, errors="coerce")).dropna().drop_duplicates().sort_values()
    )
    if dates.empty or dates.min() < WARMUP_START or dates.max() > HOLDOUT_END:
        raise ValueError("OOS_DATE_ENVELOPE_FAILURE")
    return dates.reset_index(drop=True)


def materialize_target_qfq_oos(frame: pd.DataFrame) -> pd.DataFrame:
    required = {"date", "code", "close"}
    if not required.issubset(frame.columns):
        raise ValueError("TARGET_QFQ_SCHEMA_FAILURE")
    if not frame["code"].astype(str).str.lower().eq("sh.601857").all():
        raise ValueError("TARGET_IDENTITY_FAILURE")
    dates = pd.to_datetime(frame["date"], errors="coerce")
    closes = pd.to_numeric(frame["close"], errors="coerce")
    if dates.isna().any() or closes.isna().any() or closes.le(0).any():
        raise ValueError("TARGET_QFQ_VALUE_FAILURE")
    if dates.duplicated().any() or dates.min() < WARMUP_START or dates.max() > HOLDOUT_END:
        raise ValueError("TARGET_DATE_ENVELOPE_FAILURE")
    source = frame.assign(date=dates, close=closes).sort_values("date", kind="mergesort")
    returns = source["close"].pct_change(fill_method=None)
    return pd.DataFrame(
        {
            "trade_date": source["date"].reset_index(drop=True),
            "target_analysis_return": returns.reset_index(drop=True),
            "target_valid": returns.notna().reset_index(drop=True),
        }
    )


def build_market_ex_target_proxy_v2_oos(
    closes: pd.DataFrame,
    master: pd.DataFrame,
    calendar: pd.Series,
    *,
    coverage_gate: float = 0.99,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """OOS-compatible copy of the frozen v2 PIT equal-weight ex-target semantics."""

    if {"symbol", "trade_date", "close"} - set(closes.columns):
        raise ValueError("v2 proxy close input missing columns")
    if {"symbol", "classification", "listing_date"} - set(master.columns):
        raise ValueError("v2 proxy master input missing columns")
    if not (0.0 < coverage_gate <= 1.0):
        raise ValueError("coverage_gate must be in (0, 1]")
    cal_index = pd.DatetimeIndex(_date_series(calendar))
    close = closes.copy()
    close["trade_date"] = pd.to_datetime(close["trade_date"], errors="coerce")
    close["close"] = pd.to_numeric(close["close"], errors="coerce")
    if (
        close["trade_date"].isna().any()
        or close["close"].isna().any()
        or close["close"].le(0).any()
    ):
        raise ValueError("v2 proxy close value failure")
    if close["trade_date"].min() < WARMUP_START or close["trade_date"].max() > HOLDOUT_END:
        raise ValueError("v2 proxy date envelope failure")
    if close.duplicated(["symbol", "trade_date"]).any():
        raise DuplicateKeyError("duplicate v2 proxy close symbol/date")
    prev_trading = pd.Series([pd.NaT] + list(cal_index[:-1]), index=cal_index)
    close_by_symbol = {
        sym: group.set_index("trade_date")["close"]
        for sym, group in close.groupby("symbol", sort=False)
    }
    rows: list[pd.DataFrame] = []
    for _, row in master.iterrows():
        symbol = str(row["symbol"]).strip()
        if symbol == TARGET_SYMBOL or str(row.get("classification", "")) != "A_SHARE_COMMON":
            continue
        listing = pd.to_datetime(row.get("listing_date"), errors="coerce")
        if pd.isna(listing):
            raise ValueError(f"eligible security missing listing_date: {symbol}")
        delisting = pd.to_datetime(row.get("delisting_date") or "", errors="coerce")
        delisting = None if pd.isna(delisting) else delisting
        carried = _build_carried_close(
            symbol,
            close_by_symbol.get(symbol, pd.Series(dtype="float64")),
            cal_index,
            delisting.strftime("%Y-%m-%d") if delisting is not None else None,
        )
        previous = _shift1(carried)
        expected = (listing <= prev_trading) & (
            pd.Series(True, index=cal_index) if delisting is None else (delisting > prev_trading)
        )
        expected = expected.fillna(False).astype(bool)
        observable = expected & previous.notna() & carried.notna()
        returns = (carried / previous - 1.0).where(observable)
        rows.append(
            pd.DataFrame(
                {
                    "trade_date": cal_index,
                    "symbol": symbol,
                    "in_expected_universe": expected.to_numpy(),
                    "observable": observable.to_numpy(),
                    "return": returns.to_numpy(),
                }
            )
        )
    if not rows:
        raise ValueError("no eligible non-target securities")
    detail = pd.concat(rows, ignore_index=True)
    daily = (
        detail.groupby("trade_date", sort=True, observed=True)
        .agg(
            eligible_count=("in_expected_universe", "sum"),
            observable_count=("observable", "sum"),
            proxy_return=("return", "mean"),
        )
        .reset_index()
    )
    daily["coverage"] = (daily["observable_count"] / daily["eligible_count"]).where(
        daily["eligible_count"] > 0
    )
    ok = daily["eligible_count"].gt(0) & daily["coverage"].ge(coverage_gate)
    daily["row_status"] = ok.map({True: PROXY_ROW_OK, False: PROXY_ROW_DATA_GAP})
    daily["return"] = daily["proxy_return"].where(ok)
    daily["value"] = (1.0 + daily["return"].where(ok).fillna(0.0)).cumprod() * 100.0
    proxy = daily.loc[
        :,
        [
            "trade_date",
            "eligible_count",
            "observable_count",
            "coverage",
            "return",
            "value",
            "row_status",
        ],
    ].copy()
    proxy["instrument_id"] = OOS_PROXY_ID
    proxy["dataset_id"] = "market_ex_target_v2"
    proxy["quality_status"] = "NORMALIZED_PIT_VERIFIED"
    audit = (
        detail.loc[:, ["trade_date", "symbol", "in_expected_universe", "observable", "return"]]
        .sort_values(["trade_date", "symbol"], kind="mergesort")
        .reset_index(drop=True)
    )
    return proxy, audit


def align_oil_to_a_share_oos(
    observations: pd.DataFrame,
    a_share_calendar: pd.Series,
    *,
    max_anchor_age_days: int = MAX_OIL_ANCHOR_AGE_CALENDAR_DAYS,
) -> pd.DataFrame:
    required = {"observation_date", "price"}
    if required - set(observations.columns):
        raise ValueError("oil observations missing columns")
    obs = observations.copy()
    obs["observation_date"] = pd.to_datetime(obs["observation_date"], errors="coerce")
    obs["price"] = pd.to_numeric(obs["price"], errors="coerce")
    if (
        obs["observation_date"].isna().any()
        or obs["price"].isna().any()
        or obs["price"].le(0).any()
    ):
        raise ValueError("oil observation value failure")
    if obs["observation_date"].min() < WARMUP_START or obs["observation_date"].max() > HOLDOUT_END:
        raise ValueError("oil observation date envelope failure")
    if obs.duplicated("observation_date").any():
        raise DuplicateKeyError("duplicate oil observation date")
    obs = obs.sort_values("observation_date").reset_index(drop=True)
    cal = _date_series(a_share_calendar)
    dates = obs["observation_date"].to_numpy(dtype="datetime64[ns]")
    prices = obs["price"].to_numpy(dtype="float64")
    rows: list[dict[str, object]] = []
    previous_index: int | None = None
    previous_date = None
    for current in cal:
        position = bisect_left(dates, current.to_datetime64()) - 1
        if position < 0:
            rows.append(
                {
                    "a_share_trade_date": current.date().isoformat(),
                    "oil_anchor_date": None,
                    "oil_anchor_age_days": None,
                    "oil_anchor_price": None,
                    "previous_a_share_trade_date": previous_date.date().isoformat()
                    if previous_date is not None
                    else None,
                    "previous_oil_anchor_date": None,
                    "previous_oil_anchor_price": None,
                    "oil_return": None,
                    "alignment_status": OIL_ROW_NO_ANCHOR,
                }
            )
            previous_date = current
            continue
        age = int((current.to_datetime64() - dates[position]) / np.timedelta64(1, "D"))
        stale = age > max_anchor_age_days
        status = OIL_ROW_STALE if stale else OIL_ROW_OK
        value = (
            None
            if stale or previous_index is None
            else (
                0.0
                if position == previous_index
                else prices[position] / prices[previous_index] - 1.0
            )
        )
        rows.append(
            {
                "a_share_trade_date": current.date().isoformat(),
                "oil_anchor_date": dates[position].astype("datetime64[D]").astype(str),
                "oil_anchor_age_days": age,
                "oil_anchor_price": float(prices[position]),
                "previous_a_share_trade_date": previous_date.date().isoformat()
                if previous_date is not None
                else None,
                "previous_oil_anchor_date": dates[previous_index]
                .astype("datetime64[D]")
                .astype(str)
                if previous_index is not None
                else None,
                "previous_oil_anchor_price": float(prices[previous_index])
                if previous_index is not None
                else None,
                "oil_return": value,
                "alignment_status": status,
            }
        )
        previous_index = position
        previous_date = current
    return pd.DataFrame(rows)


def build_cni_returns_oos(closes: pd.DataFrame, a_share_calendar: pd.Series) -> pd.DataFrame:
    required = {"trade_date", "index_code", "close"}
    if required - set(closes.columns):
        raise ValueError("CNI closes missing columns")
    frame = closes.copy()
    frame["trade_date"] = pd.to_datetime(frame["trade_date"], errors="coerce")
    frame["close"] = pd.to_numeric(frame["close"], errors="coerce")
    if (
        frame["trade_date"].isna().any()
        or frame["close"].isna().any()
        or frame["close"].le(0).any()
    ):
        raise ValueError("CNI value failure")
    if frame["trade_date"].min() < WARMUP_START or frame["trade_date"].max() > HOLDOUT_END:
        raise ValueError("CNI date envelope failure")
    if set(frame["index_code"].astype(str)) != {"399439"}:
        raise ValueError("CNI identity failure")
    if frame.duplicated(["index_code", "trade_date"]).any():
        raise DuplicateKeyError("duplicate CNI date")
    closes_by_date = frame.set_index("trade_date")["close"]
    calendar = _date_series(a_share_calendar)
    previous_date = None
    previous_close = None
    rows: list[dict[str, object]] = []
    for current in calendar:
        close = closes_by_date.get(current)
        if close is None:
            status, value = INDUSTRY_ROW_DATA_GAP, None
        elif previous_close is None:
            status, value = INDUSTRY_ROW_NO_PREVIOUS, None
        else:
            status, value = INDUSTRY_ROW_OK, float(close) / previous_close - 1.0
        rows.append(
            {
                "trade_date": current.date().isoformat(),
                "index_code": "399439",
                "close": float(close) if close is not None else None,
                "previous_trade_date": previous_date.date().isoformat()
                if previous_date is not None
                else None,
                "previous_close": previous_close,
                "industry_return": value,
                "alignment_status": status,
            }
        )
        if close is not None:
            previous_date, previous_close = current, float(close)
    return pd.DataFrame(rows)


def build_oos_analysis_matrix(
    target: pd.DataFrame,
    market: pd.DataFrame,
    oil: pd.DataFrame,
    industry: pd.DataFrame,
    readiness: pd.DataFrame,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    market_frame = market.loc[:, ["trade_date", "return", "row_status"]].rename(
        columns={"return": "market_ex_target_return"}
    )
    market_frame["market_valid"] = market_frame["row_status"].eq(PROXY_ROW_OK)
    oil_frame = oil.loc[:, ["a_share_trade_date", "oil_return", "alignment_status"]].rename(
        columns={"a_share_trade_date": "trade_date"}
    )
    oil_frame["oil_valid"] = oil_frame["alignment_status"].eq(OIL_ROW_OK)
    industry_frame = industry.loc[:, ["trade_date", "industry_return", "alignment_status"]].copy()
    industry_frame["industry_valid"] = industry_frame["alignment_status"].eq(INDUSTRY_ROW_OK)
    frames = [target, market_frame, oil_frame, industry_frame]
    matrix = frames[0]
    for other in frames[1:]:
        matrix = matrix.merge(other, on="trade_date", how="inner", validate="one_to_one")
    matrix = matrix.merge(readiness, on="trade_date", how="inner", validate="one_to_one")
    if (
        not matrix["tier1_joint_valid"]
        .eq(matrix["market_valid"] & matrix["oil_valid"] & matrix["industry_valid"])
        .all()
    ):
        raise ValueError("TIER1_JOINT_FLAG_MISMATCH")
    matrix["trade_date"] = pd.to_datetime(matrix["trade_date"], errors="raise")
    matrix = (
        matrix.loc[matrix["trade_date"].between(HOLDOUT_START, HOLDOUT_END)]
        .sort_values("trade_date", kind="mergesort")
        .reset_index(drop=True)
    )
    candidate = matrix.loc[matrix["target_valid"] & matrix["tier1_joint_valid"]].copy()
    if candidate.empty:
        raise ValueError("HOLDOUT_SAMPLE_EMPTY")
    return candidate, {
        "rows": int(len(matrix)),
        "target_valid_count": int(matrix["target_valid"].sum()),
        "tier1_valid_count": int(matrix["tier1_joint_valid"].sum()),
        "final_nobs": int(len(candidate)),
        "sample_start": candidate["trade_date"].min().date().isoformat(),
        "sample_end": candidate["trade_date"].max().date().isoformat(),
        "canonical_matrix_digest": canonical_frame_digest(candidate),
    }
