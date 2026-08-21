"""Primary statsmodels OLS and abnormal-return semantics."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd
import statsmodels.api as sm

from ashare_research.mechanism.analysis_contracts import (
    DESIGN_COLUMNS,
    AnalysisContractError,
)


@dataclass(frozen=True)
class OLSResult:
    """Stable result surface used by primary and robustness layers."""

    fitted_model: object
    coefficients: dict[str, float]
    expected_control_return: pd.Series
    abnormal_return: pd.Series
    design_matrix: pd.DataFrame

    @property
    def gamma(self) -> float:
        return self.coefficients["gamma"]


def design_matrix(frame: pd.DataFrame) -> pd.DataFrame:
    required = [column for column in DESIGN_COLUMNS if column != "const"]
    missing = [column for column in required if column not in frame.columns]
    if missing:
        raise AnalysisContractError(f"missing regression columns: {missing}")
    matrix = pd.DataFrame(
        {
            "const": 1.0,
            "market_ex_target_return": frame["market_ex_target_return"],
            "oil_return": frame["oil_return"],
            "industry_return": frame["industry_return"],
            "Crash_t": frame["Crash_t"],
        },
        index=frame.index,
    )
    return matrix.loc[:, list(DESIGN_COLUMNS)]


def fit_primary_ols(frame: pd.DataFrame) -> OLSResult:
    """Fit the one production estimator with an explicit intercept."""

    matrix = design_matrix(frame)
    if "target_analysis_return" not in frame:
        raise AnalysisContractError("target_analysis_return is required")
    y = frame["target_analysis_return"]
    model = sm.OLS(y, matrix, missing="raise", hasconst=True)
    fitted = model.fit()
    params = fitted.params.reindex(list(DESIGN_COLUMNS))
    coefficients = {
        "alpha": float(params["const"]),
        "beta_market": float(params["market_ex_target_return"]),
        "beta_oil": float(params["oil_return"]),
        "beta_industry": float(params["industry_return"]),
        "gamma": float(params["Crash_t"]),
    }
    control_expected = (
        coefficients["alpha"]
        + coefficients["beta_market"] * frame["market_ex_target_return"]
        + coefficients["beta_oil"] * frame["oil_return"]
        + coefficients["beta_industry"] * frame["industry_return"]
    )
    return OLSResult(
        fitted_model=fitted,
        coefficients=coefficients,
        expected_control_return=control_expected,
        abnormal_return=frame["target_analysis_return"] - control_expected,
        design_matrix=matrix,
    )


def primary_positive_evidence(gamma: float, gamma_ci_lower: float) -> bool:
    return gamma > 0 and gamma_ci_lower > 0

