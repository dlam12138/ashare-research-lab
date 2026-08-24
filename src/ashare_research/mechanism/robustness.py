"""Registered descriptive and supporting robustness transforms."""

from __future__ import annotations

from collections.abc import Iterable

import numpy as np
import pandas as pd

from ashare_research.mechanism.analysis_contracts import ROBUSTNESS_THRESHOLDS
from ashare_research.mechanism.crash import add_crash_indicator
from ashare_research.mechanism.regression import OLSResult, fit_primary_ols


def conditional_summary(frame: pd.DataFrame) -> dict:
    crash = frame[frame["Crash_t"] == 1]["target_analysis_return"]
    ordinary = frame[frame["Crash_t"] == 0]["target_analysis_return"]
    return {
        "crash_count": int(len(crash)),
        "ordinary_count": int(len(ordinary)),
        "crash_mean": float(crash.mean()) if len(crash) else None,
        "ordinary_mean": float(ordinary.mean()) if len(ordinary) else None,
        "crash_median": float(crash.median()) if len(crash) else None,
        "ordinary_median": float(ordinary.median()) if len(ordinary) else None,
        "mean_difference": float(crash.mean() - ordinary.mean())
        if len(crash) and len(ordinary)
        else None,
        "median_difference": float(crash.median() - ordinary.median())
        if len(crash) and len(ordinary)
        else None,
    }


def descriptive_summary(frame: pd.DataFrame) -> dict:
    target = frame["target_analysis_return"]
    market = frame["market_ex_target_return"]
    correlation = target.corr(market)
    rolling = target.rolling(60, min_periods=60).corr(market).dropna()
    down = target[market < 0]
    crash = target[frame["Crash_t"] == 1]
    return {
        "full_sample_correlation": float(correlation) if pd.notna(correlation) else None,
        "rolling_60d_correlation": {
            "count": int(len(rolling)),
            "last": float(rolling.iloc[-1]) if len(rolling) else None,
        },
        "down_day_return": {
            "count": int(len(down)),
            "mean": float(down.mean()) if len(down) else None,
        },
        "crash_day_return": {
            "count": int(len(crash)),
            "mean": float(crash.mean()) if len(crash) else None,
        },
        "mean": float(target.mean()),
        "median": float(target.median()),
        "positive_probability": float((target > 0).mean()),
        "year_by_year": {
            str(year): {
                "count": int(len(group)),
                "mean": float(group["target_analysis_return"].mean()),
                "median": float(group["target_analysis_return"].median()),
            }
            for year, group in frame.groupby(frame["trade_date"].dt.year)
        },
        "volume_abnormality": {
            "status": "REGISTERED_NOT_EXECUTABLE_WITH_CURRENT_TIER1_INPUTS"
        },
        "market_regimes": {
            "status": "REGISTERED_NOT_EXECUTABLE_WITH_CURRENT_TIER1_INPUTS"
        },
    }


def remove_top_extreme_crash_days(
    frame: pd.DataFrame,
    primary_result: OLSResult,
    count: int,
) -> tuple[pd.DataFrame, list[str]]:
    crash_mask = frame["Crash_t"].eq(1)
    ranking = pd.DataFrame(
        {
            "trade_date": frame.loc[crash_mask, "trade_date"],
            "absolute_abnormal": primary_result.abnormal_return.loc[crash_mask].abs(),
        }
    ).sort_values(
        ["absolute_abnormal", "trade_date"],
        ascending=[False, True],
        kind="mergesort",
    )
    dates = [value.strftime("%Y-%m-%d") for value in ranking.head(count)["trade_date"]]
    filtered = frame[~frame["trade_date"].dt.strftime("%Y-%m-%d").isin(dates)].copy()
    return filtered.reset_index(drop=True), dates


def leave_one_year_out(frame: pd.DataFrame) -> dict[str, dict]:
    results: dict[str, dict] = {}
    for year in sorted(frame["trade_date"].dt.year.unique()):
        fit = fit_primary_ols(frame[frame["trade_date"].dt.year != year])
        results[str(year)] = {
            "gamma": fit.gamma,
            "nobs": int(len(frame) - (frame["trade_date"].dt.year == year).sum()),
        }
    return results


def threshold_robustness(
    frame: pd.DataFrame,
    thresholds: Iterable[float] = ROBUSTNESS_THRESHOLDS,
) -> list[dict]:
    results = []
    for threshold in thresholds:
        transformed = add_crash_indicator(
            frame.drop(columns=["Crash_t"], errors="ignore"), threshold
        )
        if transformed["Crash_t"].nunique() < 2:
            results.append(
                {
                    "threshold": float(threshold),
                    "crash_count": int(transformed["Crash_t"].sum()),
                    "estimable": False,
                    "gamma": None,
                    "pvalue_two_sided": None,
                }
            )
            continue
        fitted = fit_primary_ols(transformed)
        results.append(
            {
                "threshold": float(threshold),
                "crash_count": int(transformed["Crash_t"].sum()),
                "estimable": True,
                "gamma": fitted.gamma,
                "pvalue_two_sided": float(fitted.fitted_model.pvalues["Crash_t"]),
            }
        )
    return results


def benjamini_hochberg(p_values: Iterable[float], q: float = 0.05) -> dict:
    """Return BH adjusted values and exact reject decisions in original order."""
    values = np.asarray(list(p_values), dtype=float)
    if values.ndim != 1 or np.any(~np.isfinite(values)) or np.any((values < 0) | (values > 1)):
        raise ValueError("p_values must be finite values in [0, 1]")
    if not 0 < q <= 1:
        raise ValueError("q must be in (0, 1]")
    order = np.argsort(values, kind="mergesort")
    adjusted = np.empty(len(values), dtype=float)
    running = 1.0
    for rank in range(len(values), 0, -1):
        position = order[rank - 1]
        running = min(running, values[position] * len(values) / rank)
        adjusted[position] = running
    return {
        "q": q,
        "adjusted_p_values": adjusted.tolist(),
        "reject": (adjusted <= q).tolist(),
    }

