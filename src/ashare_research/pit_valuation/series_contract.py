"""M2 Stage 2K.1R4E — PIT valuation series contract.

Loads and validates the frozen contracts for the candidate PE/PB/PS series:

- the formula registry (``config/pit_valuation_series_formula_registry_v1.json``)
- the v2 valuation methodology (``value_evaluation_methodology_valuation_pit_v2``)
- the market-data snapshot registry (``events/market_data_snapshot_registry.json``)
- the share-continuity register

It also freezes the shared Decimal rules (``Decimal(str(value))``, no
``Decimal(binary_float)``), the status enum, the canonical payload digest, and
the 3y/5y window rules.  It never computes a ratio, never opens the default
database, and never builds a valuation series.
"""

from __future__ import annotations

import hashlib
import json
from decimal import ROUND_HALF_EVEN, Decimal, getcontext
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]

FORMULA_REGISTRY_PATH = ROOT / "config" / "pit_valuation_series_formula_registry_v1.json"
METHODOLOGY_V2_PATH = ROOT / "config" / "value_evaluation_methodology_valuation_pit_v2.json"
MARKET_SNAPSHOT_REGISTRY_PATH = ROOT / "events" / "market_data_snapshot_registry.json"
SHARE_CONTINUITY_REGISTER_PATH = (
    ROOT / "config" / "pit_valuation_share_continuity_register_v1.json"
)

SYMBOL = "601857.SH"
VALUATION_MARKET = "SSE_A_SHARE"
PRICE_CONVENTION = "A_SHARE_PRICE_PER_SHARE"
CURRENCY = "CNY"

# Frozen evidence cutoffs (from the scoring double-clock contract).
RESEARCH_EVIDENCE_AS_OF = "2026-08-02"
SCORECARD_FORMED_AT = "2026-08-02"
MARKET_DATA_AS_OF = "2026-07-31"

# Frozen share constant (A+H total ordinary shares) and its proof.
CONSTANT_TOTAL_SHARES = Decimal("183020977818")
SHARE_CONTINUITY_PROOF_ID = "r4d1-share-continuity-constancy-v1"

# Frozen warm-up windows.
WINDOW_3Y_START = "2023-07-31"
WINDOW_5Y_START = "2021-07-31"
MIN_SAMPLES_3Y = 500
MIN_SAMPLES_5Y = 900

# Metric ids.
METRIC_PE = "PE_A_TTM"
METRIC_PB = "PB_A_MRQ"
METRIC_PS = "PS_A_TTM"
METRICS = (METRIC_PE, METRIC_PB, METRIC_PS)

# Ratio status enum (frozen).
STATUS_COMPUTED = "computed"
STATUS_MISSING_MARKET_CLOSE = "missing_market_close"
STATUS_MISSING_FINANCIAL_STATE = "missing_financial_state"
STATUS_MISSING_TTM_INPUT = "missing_ttm_input"
STATUS_UNMATCHED_EQUITY_SHARE = "unmatched_equity_share_context"
STATUS_UNSUPPORTED_VARIABLE_SHARE = "unsupported_variable_share_count"
STATUS_NONPOSITIVE_WA_SHARES = "nonpositive_weighted_average_shares"
STATUS_NONPOSITIVE_PE_SHARES = "nonpositive_period_end_shares"
STATUS_NONPOSITIVE_EQUITY = "nonpositive_equity"
STATUS_NONPOSITIVE_REVENUE = "nonpositive_revenue"
STATUS_NONPOSITIVE_EARNINGS = "nonpositive_earnings"
STATUS_ZERO_DENOMINATOR = "zero_denominator"
STATUS_NONFINITE = "nonfinite_result"
STATUS_OUTSIDE_WINDOW = "outside_required_window"
STATUS_NOT_AVAILABLE = "not_available_at_cutoff"
STATUS_BLOCKED_MARKET_CACHE = "BLOCKED_EXTERNAL_MARKET_CACHE_UNAVAILABLE"

STATUS_ENUM = (
    STATUS_COMPUTED,
    STATUS_MISSING_MARKET_CLOSE,
    STATUS_MISSING_FINANCIAL_STATE,
    STATUS_MISSING_TTM_INPUT,
    STATUS_UNMATCHED_EQUITY_SHARE,
    STATUS_UNSUPPORTED_VARIABLE_SHARE,
    STATUS_NONPOSITIVE_WA_SHARES,
    STATUS_NONPOSITIVE_PE_SHARES,
    STATUS_NONPOSITIVE_EQUITY,
    STATUS_NONPOSITIVE_REVENUE,
    STATUS_NONPOSITIVE_EARNINGS,
    STATUS_ZERO_DENOMINATOR,
    STATUS_NONFINITE,
    STATUS_OUTSIDE_WINDOW,
    STATUS_NOT_AVAILABLE,
    STATUS_BLOCKED_MARKET_CACHE,
)

# Report types in fiscal/period order.
REPORT_TYPES = ("q1", "half_year", "q3", "annual")
PERIOD_TYPE_BY_REPORT = {
    "q1": "quarter_ytd",
    "half_year": "half_year_ytd",
    "q3": "three_quarter_ytd",
    "annual": "annual",
}
PERIOD_END_BY_REPORT = {
    "q1": "03-31",
    "half_year": "06-30",
    "q3": "09-30",
    "annual": "12-31",
}

# Decimal context: frozen, explicit.
getcontext().prec = 28
getcontext().rounding = ROUND_HALF_EVEN


def parse_decimal(source_value: Any) -> Decimal:
    """Return ``Decimal(str(source_value))``.

    ``Decimal(binary_float)`` is prohibited because it propagates the binary
    float's full precision.  ``str()`` of an integer-valued float yields the
    exact integer, so ``Decimal(str(x))`` is lossless for the market/financial
    values used here.
    """
    if isinstance(source_value, Decimal):
        return source_value
    return Decimal(str(source_value))


def canonical_payload(value: Any) -> bytes:
    """Deterministic canonical JSON bytes for identity/digest hashing."""
    return json.dumps(
        value, sort_keys=True, ensure_ascii=False, separators=(",", ":")
    ).encode("utf-8")


def canonical_digest(value: Any) -> str:
    """SHA-256 over the canonical JSON payload."""
    return hashlib.sha256(canonical_payload(value)).hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def load_formula_registry() -> dict[str, Any]:
    return load_json(FORMULA_REGISTRY_PATH)


def load_methodology_v2() -> dict[str, Any]:
    return load_json(METHODOLOGY_V2_PATH)


def load_market_snapshot_registry() -> dict[str, Any]:
    return load_json(MARKET_SNAPSHOT_REGISTRY_PATH)


def load_share_continuity_register() -> dict[str, Any]:
    return load_json(SHARE_CONTINUITY_REGISTER_PATH)


def validate_formula_registry(registry: dict[str, Any]) -> None:
    if registry.get("schema") != "pit_valuation_series_formula_registry_v1":
        raise ValueError("unsupported formula registry schema")
    if registry.get("symbol") != SYMBOL:
        raise ValueError("formula registry symbol mismatch")
    if registry.get("valuation_market") != VALUATION_MARKET:
        raise ValueError("formula registry valuation_market mismatch")
    metric_ids = {f["metric_id"] for f in registry.get("formulas", [])}
    if set(METRICS) != metric_ids:
        raise ValueError(f"formula registry metric set mismatch: {metric_ids}")
    for formula in registry.get("formulas", []):
        if not formula.get("formula_id"):
            raise ValueError("formula missing formula_id")
        if formula.get("unit") != "dimensionless":
            raise ValueError("ratio must be dimensionless")
        if not formula.get("valid_domain_rule"):
            raise ValueError(f"formula {formula['metric_id']} missing valid_domain_rule")
        if not formula.get("prohibited_fallbacks"):
            raise ValueError(f"formula {formula['metric_id']} missing prohibited_fallbacks")
    statuses = set(registry.get("status_enum", []))
    if statuses != set(STATUS_ENUM):
        raise ValueError("formula registry status_enum does not match frozen enum")


def validate_methodology_v2(methodology: dict[str, Any]) -> None:
    if methodology.get("contract") != "value_evaluation_methodology_valuation_pit_v2":
        raise ValueError("unsupported methodology v2 contract")
    if methodology.get("supersedes") != "value_evaluation_methodology_valuation_pit_v1":
        raise ValueError("methodology v2 must supersede v1")
    if methodology.get("symbol") != SYMBOL:
        raise ValueError("methodology v2 symbol mismatch")
    if methodology.get("production_eligible") is not False:
        raise ValueError("methodology v2 must be non-production")
    if methodology.get("score_eligible") is not False:
        raise ValueError("methodology v2 must be score-ineligible")
    if methodology.get("percentile_computed") is not False:
        raise ValueError("methodology v2 must not have computed percentiles")


def validate_market_snapshot_registry(registry: dict[str, Any]) -> None:
    if registry.get("contract") != "market_data_snapshot_registry_v2":
        raise ValueError("unsupported market snapshot registry contract")
    if registry.get("symbol") != SYMBOL:
        raise ValueError("market snapshot registry symbol mismatch")
    providers = registry.get("providers", [])
    if len(providers) != 2:
        raise ValueError("market snapshot registry must have exactly two providers")
    names = {p.get("provider") for p in providers}
    if names != {"baostock", "akshare"}:
        raise ValueError(f"market snapshot registry providers mismatch: {names}")
    for p in providers:
        if len(p.get("sha256", "")) != 64:
            raise ValueError(f"market provider {p.get('provider')} missing sha256")
        if p.get("adjustment") != "none":
            raise ValueError(f"market provider {p.get('provider')} must be adjustment=none")
        if p.get("row_count") != 1351:
            raise ValueError(f"market provider {p.get('provider')} row_count != 1351")
    if registry.get("common_trade_days") != 1351:
        raise ValueError("market snapshot registry common_trade_days != 1351")
    if registry.get("reconciliation_status") != "pass":
        raise ValueError("market snapshot registry reconciliation_status must be pass")
    if registry.get("close_differences_within_0_01") is not True:
        raise ValueError("market snapshot registry close tolerance not satisfied")


def validate_share_continuity_register(register: dict[str, Any]) -> None:
    if register.get("schema") != "pit_valuation_share_continuity_register_v1":
        raise ValueError("unsupported share continuity register schema")
    if register.get("trust") != "trusted":
        raise ValueError("share continuity register must be trusted for constancy derivation")
    if register.get("share_count_constant") is not True:
        raise ValueError("share continuity register must record a constant conclusion")
    if Decimal(str(register.get("constant_value"))) != CONSTANT_TOTAL_SHARES:
        raise ValueError("share continuity register constant_value mismatch")


def validate_all_contracts() -> dict[str, str]:
    """Validate every R4E contract and return a digest of each."""
    registry = load_formula_registry()
    validate_formula_registry(registry)
    methodology = load_methodology_v2()
    validate_methodology_v2(methodology)
    market = load_market_snapshot_registry()
    validate_market_snapshot_registry(market)
    continuity = load_share_continuity_register()
    validate_share_continuity_register(continuity)
    return {
        "formula_registry_digest": canonical_digest(registry),
        "methodology_v2_digest": canonical_digest(methodology),
        "market_snapshot_registry_digest": canonical_digest(market),
        "share_continuity_register_digest": canonical_digest(continuity),
    }


def first_trade_day_at_or_after(cutoff: str, trade_dates: list[str]) -> str:
    """First real trade day at or after the cutoff; never fabricates a date."""
    for candidate in trade_dates:
        if candidate >= cutoff:
            return candidate
    raise ValueError(f"no trade day at or after {cutoff} in the verified calendar")
