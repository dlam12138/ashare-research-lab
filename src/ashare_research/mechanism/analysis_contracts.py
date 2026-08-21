"""Stage 3C-A frozen constants and fail-closed execution gates."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pandas as pd


class AnalysisContractError(ValueError):
    """Raised when a Stage 3C-A contract is violated."""


class ExecutionGateError(AnalysisContractError):
    """Raised when real development or holdout execution is requested."""


class UpstreamBindingError(AnalysisContractError):
    """Raised when canonical effective upstream bytes cannot be verified."""


ANALYSIS_COLUMNS = (
    "trade_date",
    "target_analysis_return",
    "market_ex_target_return",
    "oil_return",
    "industry_return",
    "target_valid",
    "market_valid",
    "oil_valid",
    "industry_valid",
    "tier1_joint_valid",
)
RETURN_COLUMNS = (
    "target_analysis_return",
    "market_ex_target_return",
    "oil_return",
    "industry_return",
)
DESIGN_COLUMNS = (
    "const",
    "market_ex_target_return",
    "oil_return",
    "industry_return",
    "Crash_t",
)
PRIMARY_CRASH_THRESHOLD = -0.010
ROBUSTNESS_THRESHOLDS = (-0.005, -0.015, -0.020)
BOOTSTRAP_REPLICATIONS = 5000
BOOTSTRAP_SEED = 20260813
BOOTSTRAP_RNG = "PCG64"
HOLDOUT_START = date(2023, 1, 1)
DEVELOPMENT_START = date(2015, 3, 16)
DEVELOPMENT_END = date(2022, 12, 30)
UPSTREAM_INVENTORY_NAME = "m3_stage3car_effective_upstream_sha_inventory_v1.json"
EXPECTED_EFFECTIVE_IDS = {
    "stage3a_hypothesis": "M3_STAGE3A_MECHANISM_HYPOTHESIS_CONTRACT_V1",
    "stage3a_statistical_protocol": "M3_STAGE3A_STATISTICAL_PROTOCOL_V1",
    "stage3a_data_requirements": "M3_STAGE3A_DATA_REQUIREMENTS_V1",
    "r1_effective_market_proxy": "SH_A_SHARE_EQUAL_WEIGHT_EX_601857_V2",
    "r2_oil_timing": "M3_STAGE3BR2_OIL_TIMING_RESOLUTION_V1",
    "r4_source_amendment": "M3_STAGE3BR4_SOURCE_AMENDMENT_V1",
    "r4_effective_oil_transport": "M3_OIL_CONTROL_V3_TRANSPORT_CONTRACT",
    "r4_effective_industry": "CNI_OIL_GAS_INDUSTRY_CONTROL_V2_CONTRACT",
    "r4_tier1_readiness": "M3_STAGE3BR4_TIER1_READINESS_V3",
}


def repository_root() -> Path:
    return Path(__file__).resolve().parents[3]


def contract_path(name: str) -> Path:
    return repository_root() / "reports" / name


def load_json_contract(name: str) -> dict:
    path = contract_path(name)
    if not path.is_file():
        raise AnalysisContractError(f"missing contract: {path}")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise AnalysisContractError(f"invalid JSON contract: {path}") from exc
    if not isinstance(value, dict) or not value.get("contract_id"):
        raise AnalysisContractError(f"malformed contract: {path}")
    return value


def enforce_execution_gate(mode: str, frame: pd.DataFrame) -> None:
    """Allow only synthetic execution and reject the sealed holdout boundary."""

    if mode != "synthetic":
        raise ExecutionGateError("REAL_ANALYSIS_NOT_AUTHORIZED")
    if "trade_date" in frame:
        dates = pd.to_datetime(frame["trade_date"], errors="raise")
        if (dates.dt.date >= HOLDOUT_START).any():
            raise ExecutionGateError("HOLDOUT_SEALED")


def is_development_date(value: object) -> bool:
    parsed = pd.Timestamp(value).date()
    return DEVELOPMENT_START <= parsed <= DEVELOPMENT_END
