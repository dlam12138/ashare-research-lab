"""Strictly-prior Brent observation-date alignment for the M3 oil control (v2).

Stage 3B-R2 formally supersedes the Stage 3B v1 publication-timestamp overspecification with a
strictly-prior Brent observation-date rule: each A-share trading day ``t`` anchors to the latest
Brent daily observation date ``d`` strictly before ``t`` and never uses the same-calendar-day
overseas close. This module never reads holdout data and never carries a stale anchor past the
frozen 7-day gate.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from ashare_research.exceptions import DuplicateKeyError
from ashare_research.mechanism.contracts import Stage3BContractError

HOLDOUT_DATE = pd.Timestamp("2023-01-01")
MAX_OIL_ANCHOR_AGE_CALENDAR_DAYS = 7

STATUS_OK = "OIL_ROW_OK"
STATUS_STALE_ANCHOR = "OIL_ROW_INVALID_STALE_ANCHOR"
STATUS_NO_ANCHOR = "OIL_ROW_INVALID_NO_ANCHOR"

ALIGNED_COLUMNS = [
    "a_share_trade_date",
    "oil_anchor_date",
    "oil_anchor_age_days",
    "oil_anchor_price",
    "previous_a_share_trade_date",
    "previous_oil_anchor_date",
    "previous_oil_anchor_price",
    "oil_return",
    "alignment_status",
]


def _strictly_prior_anchor(
    observation_dates: np.ndarray,  # sorted datetime64[ns]
    observation_prices: np.ndarray,  # float64 aligned to observation_dates
    target: np.datetime64,
) -> tuple[int | None, int]:
    """Return the index of the latest observation strictly before ``target`` and its age in days."""
    pos = int(np.searchsorted(observation_dates, target, side="left"))
    if pos < 1:
        return None, 0
    idx = pos - 1
    anchor = observation_dates[idx]
    age = int((target - anchor) / np.timedelta64(1, "D"))
    return int(idx), age


def align_oil_to_a_share(
    observations: pd.DataFrame,
    a_share_calendar: pd.Series,
    *,
    max_anchor_age_days: int = MAX_OIL_ANCHOR_AGE_CALENDAR_DAYS,
) -> pd.DataFrame:
    """Align Brent daily observations to A-share trading days on a strictly-prior basis.

    ``observations`` : per-day Brent close with columns ``observation_date`` and ``price``.
    ``a_share_calendar`` : the authorized A-share trading-date series (warm-up + development).

    For each A-share day ``t`` the anchor is the latest Brent observation date ``d`` with
    ``d < t`` (never ``d == t``). ``oil_return(t)`` divides the anchor price at ``t`` by the anchor
    price at the previous A-share day ``t_prev``; if the two anchors are the same date the return is
    zero (no new Brent observation between the two A-share points). An anchor older than
    ``max_anchor_age_days`` calendar days is ``OIL_ROW_INVALID_STALE_ANCHOR`` and is never carried
    forward. No holdout (2023+) row is accepted.
    """
    missing = {"observation_date", "price"} - set(observations.columns)
    if missing:
        raise Stage3BContractError(f"oil observations missing columns: {sorted(missing)}")
    obs = observations.copy()
    obs["observation_date"] = pd.to_datetime(obs["observation_date"], errors="coerce")
    if obs["observation_date"].isna().any():
        raise Stage3BContractError("oil observations have invalid observation_date")
    if (obs["observation_date"] >= HOLDOUT_DATE).any():
        raise Stage3BContractError("sealed holdout oil observation rejected")
    obs["price"] = pd.to_numeric(obs["price"], errors="coerce")
    if obs["price"].isna().any():
        raise Stage3BContractError("oil observations have invalid price")
    if obs["price"].le(0).any():
        raise Stage3BContractError("oil observations have non-positive price")
    if obs.duplicated("observation_date").any():
        raise DuplicateKeyError("duplicate oil observation_date")
    obs = obs.sort_values("observation_date").reset_index(drop=True)

    cal = pd.Series(pd.to_datetime(a_share_calendar, errors="coerce")).dropna().drop_duplicates()
    if (cal >= HOLDOUT_DATE).any():
        raise Stage3BContractError("sealed holdout A-share calendar row rejected")
    cal = cal.sort_values().reset_index(drop=True)
    if cal.empty:
        raise Stage3BContractError("empty A-share trading calendar")

    obs_dates = obs["observation_date"].to_numpy(dtype="datetime64[ns]")
    obs_prices = obs["price"].to_numpy(dtype="float64")

    rows: list[dict[str, object]] = []
    prev_anchor_idx: int | None = None
    prev_a_share_date = None
    for t in cal:
        idx, age = _strictly_prior_anchor(obs_dates, obs_prices, t.to_datetime64())
        if idx is None:
            rows.append(
                {
                    "a_share_trade_date": t.date().isoformat(),
                    "oil_anchor_date": None,
                    "oil_anchor_age_days": None,
                    "oil_anchor_price": None,
                    "previous_a_share_trade_date": (
                        prev_a_share_date.date().isoformat()
                        if prev_a_share_date is not None
                        else None
                    ),
                    "previous_oil_anchor_date": None,
                    "previous_oil_anchor_price": None,
                    "oil_return": None,
                    "alignment_status": STATUS_NO_ANCHOR,
                }
            )
            prev_a_share_date = t
            continue

        anchor_price = obs_prices[idx]
        stale = age > max_anchor_age_days
        if stale:
            status = STATUS_STALE_ANCHOR
            oil_return = None
        else:
            status = STATUS_OK
            if prev_anchor_idx is None:
                oil_return = None
            elif idx == prev_anchor_idx:
                oil_return = 0.0
            else:
                oil_return = anchor_price / obs_prices[prev_anchor_idx] - 1.0

        rows.append(
            {
                "a_share_trade_date": t.date().isoformat(),
                "oil_anchor_date": obs_dates[idx].astype("datetime64[D]").astype(str),
                "oil_anchor_age_days": int(age),
                "oil_anchor_price": float(anchor_price),
                "previous_a_share_trade_date": (
                    prev_a_share_date.date().isoformat() if prev_a_share_date is not None else None
                ),
                "previous_oil_anchor_date": (
                    obs_dates[prev_anchor_idx].astype("datetime64[D]").astype(str)
                    if prev_anchor_idx is not None
                    else None
                ),
                "previous_oil_anchor_price": (
                    float(obs_prices[prev_anchor_idx]) if prev_anchor_idx is not None else None
                ),
                "oil_return": oil_return,
                "alignment_status": status,
            }
        )
        prev_anchor_idx = idx
        prev_a_share_date = t

    aligned = pd.DataFrame(rows, columns=ALIGNED_COLUMNS)
    return aligned


def compare_oil_sources(
    eia: pd.DataFrame,
    fred: pd.DataFrame,
    *,
    tolerance: float = 1e-6,
) -> dict[str, object]:
    """Compare EIA RBRTE and FRED DCOILBRENTEU observations over their common date range.

    Both series ultimately originate from EIA, so FRED is a secondary distribution cross-check, not
    an independent economic source. A real value conflict (a common-date price differing by more
    than ``tolerance``) fails closed with ``OIL_SOURCE_CONFLICT``; it is never resolved by choosing
    the more favorable source.
    """
    for frame, name in ((eia, "eia"), (fred, "fred")):
        missing = {"observation_date", "price"} - set(frame.columns)
        if missing:
            raise Stage3BContractError(f"{name} source missing columns: {sorted(missing)}")
    e = pd.DataFrame(
        {
            "observation_date": pd.to_datetime(eia["observation_date"], errors="coerce"),
            "price": pd.to_numeric(eia["price"], errors="coerce"),
        }
    ).dropna()
    f = pd.DataFrame(
        {
            "observation_date": pd.to_datetime(fred["observation_date"], errors="coerce"),
            "price": pd.to_numeric(fred["price"], errors="coerce"),
        }
    ).dropna()
    for frame, name in ((e, "eia"), (f, "fred")):
        if (frame["observation_date"] >= HOLDOUT_DATE).any():
            raise Stage3BContractError(f"sealed holdout {name} source row rejected")
    if e.duplicated("observation_date").any() or f.duplicated("observation_date").any():
        raise DuplicateKeyError("duplicate oil source observation_date")
    e = e.set_index("observation_date")["price"].sort_index()
    f = f.set_index("observation_date")["price"].sort_index()
    common = e.index.intersection(f.index)
    conflicts = [d for d in common if abs(float(e[d]) - float(f[d])) > tolerance]
    return {
        "eia_rows": int(len(e)),
        "fred_rows": int(len(f)),
        "common_dates": int(len(common)),
        "conflicts": [d.date().isoformat() for d in conflicts],
        "status": "OIL_SOURCE_CONFLICT" if conflicts else "OIL_SOURCE_CONSISTENT",
    }


def assert_oil_v2_contract_envelope(contract: dict) -> None:
    """Validate the oil v2 contract envelope and its strictly-prior alignment semantics."""
    if contract.get("stage") != "M3_STAGE3BR2" or contract.get("schema_version") != "1.0.0":
        raise Stage3BContractError("unexpected Stage 3B-R2 oil contract envelope")
    if contract.get("type") != "OIL_CONTROL_V2_FROZEN_CONTRACT":
        raise Stage3BContractError("oil v2 contract must be OIL_CONTROL_V2_FROZEN_CONTRACT")
    if contract.get("alignment_definition", {}).get("alignment") != (
        "STRICTLY_PRIOR_BRENT_OBSERVATION_DATE"
    ):
        raise Stage3BContractError("oil v2 must freeze STRICTLY_PRIOR_BRENT_OBSERVATION_DATE")
    if contract.get("alignment_definition", {}).get(
        "same_calendar_day_overseas_close_allowed"
    ) is not (
        False
    ):
        raise Stage3BContractError("oil v2 must prohibit the same-calendar-day overseas close")
    if contract.get("staleness_gate", {}).get("max_oil_anchor_age_calendar_days") != 7:
        raise Stage3BContractError("oil v2 must freeze the 7-day staleness gate")
