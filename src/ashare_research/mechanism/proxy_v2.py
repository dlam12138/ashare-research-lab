"""PIT-safe equal-weight ex-target Shanghai A-share market proxy (v2).

Stage 3B-R1 formally supersedes the fail-closed Stage 3B v1 divisor-exact proxy with an
equal-weight ex-target proxy that matches the North Star's "exclude the target stock from the
market aggregate" semantics. This module never substitutes the exact SSE Composite reconstruction
and never reads holdout data.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from ashare_research.exceptions import DuplicateKeyError
from ashare_research.mechanism.contracts import Stage3BContractError

TARGET_SYMBOL = "601857.SH"
TARGET_CODE = "601857"

# Shanghai A-share common equity code prefixes (main board + STAR Market). B-shares are 900, the
# sole Shanghai CDR is 689, and indices/funds/bonds/reits use other prefixes.
MAIN_BOARD_PREFIXES = frozenset({"600", "601", "603", "605"})
STAR_PREFIXES = frozenset({"688"})
ELIGIBLE_PREFIXES = MAIN_BOARD_PREFIXES | STAR_PREFIXES
B_SHARE_PREFIXES = frozenset({"900"})
CDR_PREFIXES = frozenset({"689"})

DEFAULT_COVERAGE_GATE = 0.99
ROW_STATUS_OK = "PROXY_ROW_OK"
ROW_STATUS_DATA_GAP = "PROXY_ROW_INVALID_DATA_GAP"


def classify_equity(code: str) -> str:
    """Classify a 6-digit Shanghai security code into v2 instrument classes."""
    digits = str(code).strip().zfill(6)
    prefix = digits[:3]
    if prefix in ELIGIBLE_PREFIXES:
        return "A_SHARE_COMMON"
    if prefix in B_SHARE_PREFIXES:
        return "B_SHARE"
    if prefix in CDR_PREFIXES:
        return "CDR"
    return "OTHER_INSTRUMENT"


def _symbol(code: str) -> str:
    return f"{str(code).strip().zfill(6)}.SH"


def _shift1(series: pd.Series) -> pd.Series:
    """Positional one-step lag on a datetime-indexed series (no frequency assumption)."""
    values = series.to_numpy()
    out = np.full(len(values), np.nan)
    out[1:] = values[:-1]
    return pd.Series(out, index=series.index)


def _build_carried_close(
    symbol: str,
    close_series: pd.Series,
    calendar: pd.Index,
    delist_date: str | None,
) -> pd.Series:
    """Return a forward-filled close series over the trading calendar within the listing window.

    Suspension carries the last valid close; the window runs from the first observed close to
    either the frozen delisting date (delisted) or the end of the sample (still listed).
    """
    close = pd.Series(
        close_series.to_numpy(),
        index=pd.to_datetime(close_series.index),
        dtype="float64",
    )
    close = close[~close.index.duplicated(keep="last")].sort_index()
    frame = pd.DataFrame({"close": close.reindex(calendar)})
    first_trade = close.index.min()
    window_end = (
        pd.Timestamp(delist_date) if delist_date else calendar.max()
    )
    if pd.isna(first_trade) or window_end < first_trade:
        carried = pd.Series(float("nan"), index=calendar)
    else:
        carried = frame.loc[first_trade:window_end, "close"].ffill()
        carried = carried.reindex(calendar)
    return carried


def build_market_ex_target_proxy_v2(
    closes: pd.DataFrame,
    master: pd.DataFrame,
    calendar: pd.Series,
    *,
    coverage_gate: float = DEFAULT_COVERAGE_GATE,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Build the equal-weight ex-target daily proxy from PIT-safe membership.

    ``closes`` : per-security close series with columns ``symbol``, ``trade_date``, ``close``.
    ``master`` : per-security metadata with columns ``symbol``, ``classification``,
        ``listing_date``, ``delisting_date`` (optional).
    ``calendar`` : the authorized trading-date series (warm-up + development only).

    Membership is decided only from information available at the previous trading-day close:
    a security is an expected member at ``t-1`` when it is classified eligible, is not the target,
    was listed on or before ``t-1``, and is not yet delisted as of ``t-1``. It contributes a return
    on day ``t`` only when it also has valid carried closes on both ``t-1`` and ``t`` (new listings
    enter once a previous close exists; a security leaves after its final valid observation).
    ``eligible_count`` counts expected members; ``observable_count`` counts those with an observable
    return; a date is ``PROXY_ROW_INVALID_DATA_GAP`` when coverage falls below ``coverage_gate`` and
    is never silently computed on a subset.
    """
    missing = {"symbol", "trade_date", "close"} - set(closes.columns)
    if missing:
        raise Stage3BContractError(f"v2 proxy close input missing columns: {sorted(missing)}")
    master_missing = {"symbol", "classification", "listing_date"} - set(master.columns)
    if master_missing:
        raise Stage3BContractError(f"v2 proxy master missing columns: {sorted(master_missing)}")
    if not (0.0 < coverage_gate <= 1.0):
        raise Stage3BContractError("coverage_gate must be in (0, 1]")

    cal_series = (
        pd.Series(pd.to_datetime(calendar, errors="coerce"))
        .dropna()
        .drop_duplicates()
        .sort_values()
    )
    cal_index = pd.DatetimeIndex(cal_series)
    if len(cal_index) == 0:
        raise Stage3BContractError("empty trading calendar")
    if (cal_index >= pd.Timestamp("2023-01-01")).any():
        raise Stage3BContractError("sealed holdout calendar row rejected")

    close = closes.copy()
    close["trade_date"] = pd.to_datetime(close["trade_date"], errors="coerce")
    if close["trade_date"].isna().any():
        raise Stage3BContractError("v2 proxy close input has invalid trade_date")
    if (close["trade_date"] >= pd.Timestamp("2023-01-01")).any():
        raise Stage3BContractError("sealed holdout close row rejected")
    close["close"] = pd.to_numeric(close["close"], errors="coerce")
    if close["close"].isna().any():
        raise Stage3BContractError("v2 proxy close input has invalid close")
    if (close["close"] <= 0).any():
        raise Stage3BContractError("v2 proxy close input has non-positive close")
    if close.duplicated(["symbol", "trade_date"]).any():
        raise DuplicateKeyError("duplicate v2 proxy close symbol/date")

    cal_list = list(cal_index)
    prev_trading = pd.Series([pd.NaT] + cal_list[:-1], index=cal_index)

    # Index each symbol's close series once (O(N) total) instead of a full-frame scan per symbol.
    close_by_symbol = {
        sym: grp.set_index("trade_date")["close"]
        for sym, grp in close.groupby("symbol", sort=False)
    }

    rows: list[pd.DataFrame] = []
    for _, row in master.iterrows():
        sym = str(row["symbol"]).strip()
        if sym == TARGET_SYMBOL:
            continue
        if str(row.get("classification", "")) != "A_SHARE_COMMON":
            continue
        listing = pd.to_datetime(row.get("listing_date"), errors="coerce")
        if pd.isna(listing):
            raise Stage3BContractError(f"eligible security missing listing_date: {sym}")
        delisting = pd.to_datetime(row.get("delisting_date") or "", errors="coerce")
        delisting = None if pd.isna(delisting) else delisting

        series = close_by_symbol.get(sym, pd.Series(dtype="float64"))
        carried = _build_carried_close(
            sym,
            series,
            cal_index,
            delisting.strftime("%Y-%m-%d") if delisting is not None else None,
        )
        prev = _shift1(carried)
        expected = (listing <= prev_trading) & (
            pd.Series(True, index=cal_index)
            if delisting is None
            else (delisting > prev_trading)
        )
        expected = expected.fillna(False).astype(bool)
        observ = expected & prev.notna() & carried.notna()
        ret = (carried / prev - 1.0).where(observ)
        rows.append(
            pd.DataFrame(
                {
                    "trade_date": cal_index,
                    "symbol": sym,
                    "in_expected_universe": expected.to_numpy(),
                    "observable": observ.to_numpy(),
                    "return": ret.to_numpy(),
                }
            )
        )

    if not rows:
        raise Stage3BContractError("no eligible non-target securities in v2 proxy master")
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
    daily["coverage"] = (
        daily["observable_count"] / daily["eligible_count"]
    ).where(daily["eligible_count"] > 0)
    ok = daily["eligible_count"].gt(0) & daily["coverage"].ge(coverage_gate)
    daily["row_status"] = ok.map(
        {True: ROW_STATUS_OK, False: ROW_STATUS_DATA_GAP}
    )
    daily["return"] = daily["proxy_return"].where(ok)
    daily["value"] = (1.0 + daily["return"].where(ok).fillna(0.0)).cumprod() * 100.0

    proxy_cols = [
        "trade_date",
        "eligible_count",
        "observable_count",
        "coverage",
        "return",
        "value",
        "row_status",
    ]
    proxy = daily.loc[:, proxy_cols].copy()
    proxy["instrument_id"] = "SH_A_SHARE_EQUAL_WEIGHT_EX_601857_V2"
    proxy["dataset_id"] = "market_ex_target_v2"
    proxy["quality_status"] = "NORMALIZED_PIT_VERIFIED"

    audit = detail.loc[
        :, ["trade_date", "symbol", "in_expected_universe", "observable", "return"]
    ].sort_values(["trade_date", "symbol"], kind="mergesort").reset_index(drop=True)
    return proxy, audit


def assert_v2_contract_envelope(contract: dict) -> None:
    """Validate the superseding v2 contract envelope and its key semantics."""
    if contract.get("stage") != "M3_STAGE3BR1" or contract.get("schema_version") != "1.0.0":
        raise Stage3BContractError("unexpected Stage 3B-R1 contract envelope")
    if contract.get("coverage_gate", {}).get("minimum_daily_input_coverage") != 0.99:
        raise Stage3BContractError("missing frozen 0.99 coverage gate")
    supersedes = contract.get("supersedes")
    if supersedes != "SH_MARKET_EX_601857":
        raise Stage3BContractError("v2 contract must supersede SH_MARKET_EX_601857")
    if contract.get("supersession_semantics", {}).get("runtime_fallback_from_v1") is not False:
        raise Stage3BContractError("v2 must be a formal supersession, not a runtime fallback")
