"""Joint Tier-1 development-input readiness (structural coverage only).

Reuses the trusted ``SH_A_SHARE_EQUAL_WEIGHT_EX_601857_V2`` market proxy and combines it with the
oil and industry controls into a single structural readiness date table. This is data coverage, not
research: no crash indicator, no ``601857`` return, and no abnormal-return or correlation statistic
may appear. A date is ``tier1_joint_valid`` only when all three Tier-1 inputs are valid on it;
missing controls are never forward-filled to enlarge the sample.
"""

from __future__ import annotations

import pandas as pd

from ashare_research.mechanism.contracts import Stage3BContractError

JOINT_MARKET_OK_STATUS = "PROXY_ROW_OK"
JOINT_OIL_OK_STATUS = "OIL_ROW_OK"
JOINT_INDUSTRY_OK_STATUS = "INDUSTRY_ROW_OK"

READINESS_COLUMNS = [
    "trade_date",
    "market_proxy_valid",
    "oil_valid",
    "industry_valid",
    "tier1_joint_valid",
    "invalid_reason_codes",
]


def build_tier1_readiness(
    market_proxy: pd.DataFrame,
    oil_aligned: pd.DataFrame,
    industry_aligned: pd.DataFrame,
) -> pd.DataFrame:
    """Build the joint Tier-1 structural readiness date table.

    ``market_proxy`` : v2 proxy with ``trade_date`` and ``row_status``.
    ``oil_aligned`` : aligned oil with ``a_share_trade_date``, ``oil_return``, ``alignment_status``.
    ``industry_aligned`` : industry with ``trade_date``, ``industry_return``, ``alignment_status``.

    A date is market/oil/industry-valid when its input has a usable return on that date. A joint row
    is valid only when all three are valid. Missing controls are never forward-filled.
    """
    for frame, name in ((market_proxy, "market_proxy"), (oil_aligned, "oil_aligned"),
                        (industry_aligned, "industry_aligned")):
        if not isinstance(frame, pd.DataFrame) or frame.empty:
            raise Stage3BContractError(f"{name} readiness input is empty")

    proxy_valid = dict(
        zip(
            market_proxy["trade_date"].astype(str).to_numpy(),
            (market_proxy["row_status"].eq(JOINT_MARKET_OK_STATUS)).to_numpy(), strict=False,
        )
    )
    oil_status = dict(
        zip(
            oil_aligned["a_share_trade_date"].astype(str).to_numpy(),
            oil_aligned["alignment_status"].astype(str).to_numpy(), strict=False,
        )
    )
    oil_ret = dict(
        zip(
            oil_aligned["a_share_trade_date"].astype(str).to_numpy(),
            pd.to_numeric(oil_aligned["oil_return"], errors="coerce").to_numpy(), strict=False,
        )
    )
    industry_status = dict(
        zip(
            industry_aligned["trade_date"].astype(str).to_numpy(),
            industry_aligned["alignment_status"].astype(str).to_numpy(), strict=False,
        )
    )
    industry_ret = dict(
        zip(
            industry_aligned["trade_date"].astype(str).to_numpy(),
            pd.to_numeric(industry_aligned["industry_return"], errors="coerce").to_numpy(),
            strict=False,
        )
    )

    # Union of all A-share trading dates across the three aligned inputs.
    dates = sorted(
        set(market_proxy["trade_date"].astype(str))
        | set(oil_aligned["a_share_trade_date"].astype(str))
        | set(industry_aligned["trade_date"].astype(str))
    )

    rows: list[dict[str, object]] = []
    for d in dates:
        market_ok = bool(proxy_valid.get(d, False))
        oil_ok = oil_status.get(d) == JOINT_OIL_OK_STATUS and bool(pd.notna(oil_ret.get(d)))
        industry_ok = (
            industry_status.get(d) == JOINT_INDUSTRY_OK_STATUS
            and bool(pd.notna(industry_ret.get(d)))
        )
        joint = market_ok and oil_ok and industry_ok
        codes: list[str] = []
        if not market_ok:
            codes.append("MARKET_PROXY_INVALID")
        if not oil_ok:
            codes.append("OIL_INVALID")
        if not industry_ok:
            codes.append("INDUSTRY_INVALID")
        rows.append(
            {
                "trade_date": d,
                "market_proxy_valid": market_ok,
                "oil_valid": oil_ok,
                "industry_valid": industry_ok,
                "tier1_joint_valid": joint,
                "invalid_reason_codes": codes if codes else [],
            }
        )
    return pd.DataFrame(rows, columns=READINESS_COLUMNS)


def summarize_readiness(readiness: pd.DataFrame) -> dict[str, object]:
    """Summarize the structural readiness table (coverage only, no research result)."""
    if readiness.empty:
        raise Stage3BContractError("empty readiness table")
    joint = readiness["trade_date"].loc[readiness["tier1_joint_valid"]]
    gap_rows = readiness.loc[~readiness["tier1_joint_valid"]]
    gap_counts: dict[str, int] = {}
    for codes in gap_rows["invalid_reason_codes"]:
        for code in codes:
            gap_counts[code] = gap_counts.get(code, 0) + 1
    return {
        "total_trading_dates": int(len(readiness)),
        "market_proxy_valid_dates": int(readiness["market_proxy_valid"].sum()),
        "oil_valid_dates": int(readiness["oil_valid"].sum()),
        "industry_valid_dates": int(readiness["industry_valid"].sum()),
        "joint_tier1_valid_dates": int(readiness["tier1_joint_valid"].sum()),
        "first_joint_valid_date": joint.min() if not joint.empty else None,
        "last_joint_valid_date": joint.max() if not joint.empty else None,
        "gap_dates": int(len(gap_rows)),
        "gap_reason_counts": gap_counts,
    }
