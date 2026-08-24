"""Shenwan petroleum & petrochemicals industry price-index control (frozen primary).

Frozen Stage 3B semantics: Shenwan Petroleum and Petrochemicals Industry Price Index with a
SW_2014 regime (``801016``, through 2021-12-10) and a SW_2021 regime (``801960``, from
2021-12-13). Returns are simple price returns computed only within a single taxonomy regime; the
two index levels are never spliced or ratio-scaled into one continuous level. Missing A-share
trading-day closes fail closed (no forward-fill). No holdout (2023+) row is accepted.
"""

from __future__ import annotations

import pandas as pd

from ashare_research.exceptions import DuplicateKeyError
from ashare_research.mechanism.contracts import Stage3BContractError

HOLDOUT_DATE = pd.Timestamp("2023-01-01")

REGIME_1_SYMBOL = "801016"
REGIME_1_TAXONOMY = "SW_2014"
REGIME_1_THROUGH = pd.Timestamp("2021-12-10")
REGIME_2_SYMBOL = "801960"
REGIME_2_TAXONOMY = "SW_2021"
REGIME_2_FROM = pd.Timestamp("2021-12-13")

STATUS_OK = "INDUSTRY_ROW_OK"
STATUS_TRANSITION_GAP = "INDUSTRY_TAXONOMY_TRANSITION_GAP"
STATUS_DATA_GAP = "INDUSTRY_ROW_INVALID_DATA_GAP"
STATUS_NO_PREVIOUS_VALID = "INDUSTRY_ROW_NO_PREVIOUS_VALID"


def _regime_for(date: pd.Timestamp) -> tuple[str, str] | None:
    if date <= REGIME_1_THROUGH:
        return REGIME_1_SYMBOL, REGIME_1_TAXONOMY
    if date >= REGIME_2_FROM:
        return REGIME_2_SYMBOL, REGIME_2_TAXONOMY
    return None  # the 2021-12-11..2021-12-12 weekend gap is not a trading session


def build_industry_returns(
    closes: pd.DataFrame,
    a_share_calendar: pd.Series,
) -> pd.DataFrame:
    """Build within-regime simple price returns for the Shenwan industry index.

    ``closes`` : per-day industry close with columns ``trade_date``, ``close``, ``symbol``
        (the regime symbol ``801016`` or ``801960``).
    ``a_share_calendar`` : the authorized A-share trading-date series.

    A same-regime previous valid close is required to compute a return. The first day of the
    ``801960`` regime (2021-12-13) is explicitly ``INDUSTRY_TAXONOMY_TRANSITION_GAP`` and its first
    legal simple return exists once a same-regime previous close appears (the following 801960
    trading day). A missing close on an A-share trading day is ``INDUSTRY_ROW_INVALID_DATA_GAP`` and
    is never forward-filled into a fake zero return.
    """
    missing = {"trade_date", "close", "symbol"} - set(closes.columns)
    if missing:
        raise Stage3BContractError(f"industry closes missing columns: {sorted(missing)}")
    frame = closes.copy()
    frame["trade_date"] = pd.to_datetime(frame["trade_date"], errors="coerce")
    if frame["trade_date"].isna().any():
        raise Stage3BContractError("industry closes have invalid trade_date")
    if (frame["trade_date"] >= HOLDOUT_DATE).any():
        raise Stage3BContractError("sealed holdout industry close rejected")
    frame["close"] = pd.to_numeric(frame["close"], errors="coerce")
    if frame["close"].isna().any():
        raise Stage3BContractError("industry closes have invalid close")
    if frame["close"].le(0).any():
        raise Stage3BContractError("industry closes have non-positive close")
    bad_symbols = set(frame["symbol"].astype(str).str.strip()) - {
        REGIME_1_SYMBOL,
        REGIME_2_SYMBOL,
    }
    if bad_symbols:
        raise Stage3BContractError(f"unexpected industry regime symbol: {sorted(bad_symbols)}")
    if frame.duplicated(["symbol", "trade_date"]).any():
        raise DuplicateKeyError("duplicate industry symbol/date")
    frame["symbol"] = frame["symbol"].astype(str).str.strip()

    cal = pd.Series(pd.to_datetime(a_share_calendar, errors="coerce")).dropna().drop_duplicates()
    if (cal >= HOLDOUT_DATE).any():
        raise Stage3BContractError("sealed holdout A-share calendar row rejected")
    cal = cal.sort_values().reset_index(drop=True)

    by_symbol = {
        sym: grp.set_index("trade_date")["close"]
        for sym, grp in frame.groupby("symbol", sort=False)
    }

    rows: list[dict[str, object]] = []
    previous_date: pd.Timestamp | None = None
    previous_close: float | None = None
    previous_symbol: str | None = None
    for t in cal:
        regime = _regime_for(t)
        close = None
        if regime is not None:
            series = by_symbol.get(regime[0])
            if series is not None and t in series.index:
                close = float(series.loc[t])

        regime_changed = (
            previous_symbol is not None and regime is not None and regime[0] != previous_symbol
        )
        if regime is None:
            status = STATUS_DATA_GAP
            ret = None
        elif regime[0] == REGIME_2_SYMBOL and t == REGIME_2_FROM:
            status = STATUS_TRANSITION_GAP
            ret = None
        elif close is None:
            status = STATUS_DATA_GAP
            ret = None
        elif previous_date is None or previous_close is None or regime_changed:
            # First date of a regime, or the first date overall: no same-regime previous close.
            status = STATUS_NO_PREVIOUS_VALID
            ret = None
        else:
            status = STATUS_OK
            ret = close / previous_close - 1.0

        rows.append(
            {
                "trade_date": t.date().isoformat(),
                "symbol": regime[0] if regime is not None else None,
                "taxonomy": regime[1] if regime is not None else None,
                "close": close,
                "previous_trade_date": (
                    previous_date.date().isoformat() if previous_date is not None else None
                ),
                "previous_close": previous_close,
                "previous_symbol": previous_symbol,
                "industry_return": ret,
                "alignment_status": status,
            }
        )
        if close is not None:
            previous_date = t
            previous_close = close
            if regime is not None:
                previous_symbol = regime[0]

    return pd.DataFrame(rows)


def assert_industry_contract_envelope(contract: dict) -> None:
    """Validate the frozen industry regime semantics described in Stage 3B v1."""
    if contract.get("stage") != "M3_STAGE3B" or contract.get("schema_version") != "1.0.0":
        raise Stage3BContractError("unexpected Stage 3B industry contract envelope")
    regimes = {r["symbol"]: r for r in contract.get("industry", {}).get("symbol_regimes", [])}
    if regimes.get("801016", {}).get("taxonomy") != "SW_2014":
        raise Stage3BContractError("industry regime 801016 must be SW_2014")
    if regimes.get("801960", {}).get("taxonomy") != "SW_2021":
        raise Stage3BContractError("industry regime 801960 must be SW_2021")
    if contract.get("industry", {}).get("return_type") != "SIMPLE_PRICE_RETURN":
        raise Stage3BContractError("industry return type must be SIMPLE_PRICE_RETURN")
