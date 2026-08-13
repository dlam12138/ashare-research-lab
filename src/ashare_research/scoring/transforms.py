"""M2 Stage 2K.1R3 pure-function transform registry (Decimal).

Every transform consumes ResolvedRecord operands (never capsule-supplied
inputs) and returns a ComputedValue with a calculation trace. Operands come
from the lineage resolver; the capsule's transform_inputs are audit snapshots
only and are never used as computation inputs.

Layer separation:
  Layer 1 (this module): upstream records -> financial/valuation metric values.
  Layer 2 (stage2k scoring): metric values -> dimension component scores.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

from ashare_research.scoring.lineage import ResolvedRecord


class TransformError(Exception):
    """Raised when a transform cannot be computed (missing operand, zero
    denominator, invalid input)."""


@dataclass(frozen=True)
class ComputedValue:
    transform_id: str
    transform_version: str
    operand_record_ids: tuple[str, ...]
    normalized_operands: dict[str, str]
    output_value: str | None
    output_unit: str | None
    output_domain: str | None
    calculation_trace: list[str] = field(default_factory=list)


def _num(v: Any) -> Decimal:
    if v is None:
        raise TransformError("missing operand")
    return Decimal(str(v))


def _ratio(trace: list[str], numerator: Decimal, denominator: Decimal, label: str) -> Decimal:
    if denominator == 0:
        raise TransformError(f"division by zero in {label}")
    trace.append(f"{label} = {numerator} / {denominator}")
    return numerator / denominator


def _sum(trace: list[str], values: list[Decimal], label: str) -> Decimal:
    total = sum(values, Decimal("0"))
    trace.append(f"{label} = sum({[str(v) for v in values]}) = {total}")
    return total


def _operand(records: tuple[ResolvedRecord, ...], concept: str) -> ResolvedRecord:
    r = _find_operand(records, concept)
    if r is None:
        raise TransformError(f"operand not found: {concept}")
    return r


def _find_operand(records: tuple[ResolvedRecord, ...], concept: str) -> ResolvedRecord | None:
    """Match an operand by concept (optionally concept:year). The record field
    path is year-tagged, e.g. /facts/net_profit_attributable_to_parent/2025."""
    if ":" in concept:
        base, year = concept.split(":", 1)
        for r in records:
            fp = r.field_path or ""
            if base in fp and year in fp:
                return r
        return None
    for r in records:
        if concept in (r.field_path or ""):
            return r
    return None


def _sum_operands(records: tuple[ResolvedRecord, ...], concept: str) -> Decimal:
    """Sum every matching operand record (e.g. all dividend events for a fiscal
    year). Raises TransformError if none match."""
    matches = [r for r in records if concept in (r.field_path or "") and r.raw_value is not None]
    if not matches:
        raise TransformError(f"operand not found: {concept}")
    return sum(_num(r.raw_value) for r in matches)


# ---------------------------------------------------------------------------
# transforms
# ---------------------------------------------------------------------------

def gross_margin_v1(records: tuple[ResolvedRecord, ...]) -> ComputedValue:
    trace: list[str] = []
    rev = _num(_operand(records, "revenue").raw_value)
    cost = _num(_operand(records, "operating_cost").raw_value)
    out = _ratio(trace, rev - cost, rev, "gross_margin")
    return ComputedValue(
        "gross_margin_v1", "1.0", tuple(r.record_id for r in records),
        {"revenue": str(rev), "operating_cost": str(cost)},
        str(out), "ratio", "ratio_gte_0", trace,
    )


def operating_margin_v1(records: tuple[ResolvedRecord, ...]) -> ComputedValue:
    trace: list[str] = []
    rev = _num(_operand(records, "revenue").raw_value)
    op = _num(_operand(records, "operating_profit").raw_value)
    out = _ratio(trace, op, rev, "operating_margin")
    return ComputedValue(
        "operating_margin_v1", "1.0", tuple(r.record_id for r in records),
        {"revenue": str(rev), "operating_profit": str(op)},
        str(out), "ratio", "ratio", trace,
    )


def np_yoy_v1(records: tuple[ResolvedRecord, ...]) -> ComputedValue:
    trace: list[str] = []
    np25 = _num(_operand(records, "net_profit_attributable_to_parent:2025").raw_value)
    np24 = _num(_operand(records, "net_profit_attributable_to_parent:2024").raw_value)
    out = _ratio(trace, np25 - np24, np24, "np_yoy")
    return ComputedValue(
        "np_yoy_v1", "1.0", tuple(r.record_id for r in records),
        {"np_2025": str(np25), "np_2024": str(np24)},
        str(out), "ratio", "ratio", trace,
    )


def ocf_to_net_profit_v1(records: tuple[ResolvedRecord, ...]) -> ComputedValue:
    trace: list[str] = []
    ocf = _num(_operand(records, "operating_cash_flow").raw_value)
    np = _num(_operand(records, "net_profit_attributable_to_parent").raw_value)
    out = _ratio(trace, ocf, np, "ocf_to_net_profit")
    return ComputedValue(
        "ocf_to_net_profit_v1", "1.0", tuple(r.record_id for r in records),
        {"ocf": str(ocf), "np": str(np)},
        str(out), "ratio", "ratio", trace,
    )


def roe_v1(records: tuple[ResolvedRecord, ...]) -> ComputedValue:
    trace: list[str] = []
    np = _num(_operand(records, "net_profit_attributable_to_parent").raw_value)
    eq25 = _num(_operand(records, "equity_attributable_to_parent:2025").raw_value)
    eq24 = _num(_operand(records, "equity_attributable_to_parent:2024").raw_value)
    avg_eq = (eq24 + eq25) / 2
    out = _ratio(trace, np, avg_eq, "roe")
    return ComputedValue(
        "roe_v1", "1.0", tuple(r.record_id for r in records),
        {"np": str(np), "equity_2024": str(eq24), "equity_2025": str(eq25)},
        str(out), "ratio", "ratio", trace,
    )


def roa_v1(records: tuple[ResolvedRecord, ...]) -> ComputedValue:
    trace: list[str] = []
    np = _num(_operand(records, "net_profit").raw_value)
    ta25 = _num(_operand(records, "total_assets:2025").raw_value)
    ta24 = _num(_operand(records, "total_assets:2024").raw_value)
    avg_ta = (ta24 + ta25) / 2
    out = _ratio(trace, np, avg_ta, "roa")
    return ComputedValue(
        "roa_v1", "1.0", tuple(r.record_id for r in records),
        {"net_profit": str(np), "total_assets_2024": str(ta24), "total_assets_2025": str(ta25)},
        str(out), "ratio", "ratio", trace,
    )


def asset_liability_v1(records: tuple[ResolvedRecord, ...]) -> ComputedValue:
    trace: list[str] = []
    liab = _num(_operand(records, "total_liabilities").raw_value)
    ta = _num(_operand(records, "total_assets").raw_value)
    out = _ratio(trace, liab, ta, "asset_liability")
    return ComputedValue(
        "asset_liability_v1", "1.0", tuple(r.record_id for r in records),
        {"total_liabilities": str(liab), "total_assets": str(ta)},
        str(out), "ratio", "ratio", trace,
    )


def cash_coverage_v1(records: tuple[ResolvedRecord, ...]) -> ComputedValue:
    trace: list[str] = []
    cash = _num(_operand(records, "cash_and_cash_equivalents").raw_value)
    debt = _sum(
        trace,
        [
            _num(_operand(records, "short_term_borrowings").raw_value),
            _num(
                _operand(
                    records, "current_portion_of_interest_bearing_non_current_liabilities"
                ).raw_value
            ),
            _num(_operand(records, "long_term_borrowings").raw_value),
            _num(_operand(records, "bonds_payable").raw_value),
            _num(_operand(records, "lease_liabilities").raw_value),
        ],
        "gross_interest_bearing_debt",
    )
    out = _ratio(trace, cash, debt, "cash_coverage")
    return ComputedValue(
        "cash_coverage_v1", "1.0", tuple(r.record_id for r in records),
        {"cash": str(cash), "gross_interest_bearing_debt": str(debt)},
        str(out), "ratio", "ratio", trace,
    )


def payout_ratio_v1(records: tuple[ResolvedRecord, ...]) -> ComputedValue:
    trace: list[str] = []
    div_total = _sum(
        trace,
        [_sum_operands(records, "cash_dividend_total")],
        "total_cash_dividend",
    )
    np = _num(_operand(records, "net_profit_attributable_to_parent").raw_value)
    out = _ratio(trace, div_total, np, "payout_ratio")
    return ComputedValue(
        "payout_ratio_v1", "1.0", tuple(r.record_id for r in records),
        {"total_cash_dividend": str(div_total), "net_profit": str(np)},
        str(out), "ratio", "ratio", trace,
    )


def sum_dps_v1(records: tuple[ResolvedRecord, ...]) -> ComputedValue:
    trace: list[str] = []
    dps = _sum(
        trace,
        [_sum_operands(records, "cash_dividend_per_share")],
        "sum_dps",
    )
    return ComputedValue(
        "sum_dps_v1", "1.0", tuple(r.record_id for r in records),
        {"dps": str(dps)}, str(dps), "CNY", "cny_gte_0", trace,
    )


def ocf_dividend_coverage_v1(records: tuple[ResolvedRecord, ...]) -> ComputedValue:
    trace: list[str] = []
    ocf = _num(_operand(records, "operating_cash_flow").raw_value)
    div_total = _sum(
        trace,
        [_sum_operands(records, "cash_dividend_total")],
        "total_cash_dividend",
    )
    out = _ratio(trace, ocf, div_total, "ocf_dividend_coverage")
    return ComputedValue(
        "ocf_dividend_coverage_v1", "1.0", tuple(r.record_id for r in records),
        {"ocf": str(ocf), "total_cash_dividend": str(div_total)},
        str(out), "ratio", "ratio", trace,
    )


def fcf_dividend_coverage_v1(records: tuple[ResolvedRecord, ...]) -> ComputedValue:
    trace: list[str] = []
    ocf = _num(_operand(records, "operating_cash_flow").raw_value)
    capex = _num(_operand(records, "cash_paid_for_fixed_assets").raw_value)
    div_total = _sum(
        trace,
        [_sum_operands(records, "cash_dividend_total")],
        "total_cash_dividend",
    )
    out = _ratio(trace, ocf - capex, div_total, "fcf_dividend_coverage")
    return ComputedValue(
        "fcf_dividend_coverage_v1", "1.0", tuple(r.record_id for r in records),
        {"ocf": str(ocf), "capex": str(capex), "total_cash_dividend": str(div_total)},
        str(out), "ratio", "ratio", trace,
    )


def risk_observed_count_v1(records: tuple[ResolvedRecord, ...]) -> ComputedValue:
    trace: list[str] = []
    observed = [
        r for r in records
        if r.upstream_ref_type == "risk_slot"
        and r.raw_value
        and "observed" in r.raw_value
        and "not_observed" not in r.raw_value
    ]
    out = len(observed)
    trace.append(f"risk_observed_count = {out}")
    return ComputedValue(
        "risk_observed_count_v1", "1.0", tuple(r.record_id for r in records),
        {"observed": str(out)}, str(out), "count", "count_gte_0", trace,
    )


def risk_missing_count_v1(records: tuple[ResolvedRecord, ...]) -> ComputedValue:
    trace: list[str] = []
    missing = [
        r for r in records
        if r.upstream_ref_type == "risk_slot"
        and (not r.raw_value or "missing" in r.raw_value)
    ]
    out = len(missing)
    trace.append(f"risk_missing_count = {out}")
    return ComputedValue(
        "risk_missing_count_v1", "1.0", tuple(r.record_id for r in records),
        {"missing": str(out)}, str(out), "count", "count_gte_0", trace,
    )


def gap_count_v1(records: tuple[ResolvedRecord, ...]) -> ComputedValue:
    trace: list[str] = []
    out = len(records)
    trace.append(f"gap_count = {out}")
    return ComputedValue(
        "gap_count_v1", "1.0", tuple(r.record_id for r in records),
        {"count": str(out)}, str(out), "count", "count_gte_0", trace,
    )


def categorical_pass_v1(records: tuple[ResolvedRecord, ...]) -> ComputedValue:
    trace: list[str] = []
    if not records:
        raise TransformError("categorical_pass_v1: no records")
    value = records[0].raw_value
    trace.append(f"categorical_pass = {value}")
    return ComputedValue(
        "categorical_pass_v1", "1.0", tuple(r.record_id for r in records),
        {"value": value or ""}, value, "categorical", "categorical_enum", trace,
    )


TRANSFORMS = {
    "gross_margin_v1": gross_margin_v1,
    "operating_margin_v1": operating_margin_v1,
    "np_yoy_v1": np_yoy_v1,
    "ocf_to_net_profit_v1": ocf_to_net_profit_v1,
    "roe_v1": roe_v1,
    "roa_v1": roa_v1,
    "asset_liability_v1": asset_liability_v1,
    "cash_coverage_v1": cash_coverage_v1,
    "payout_ratio_v1": payout_ratio_v1,
    "sum_dps_v1": sum_dps_v1,
    "ocf_dividend_coverage_v1": ocf_dividend_coverage_v1,
    "fcf_dividend_coverage_v1": fcf_dividend_coverage_v1,
    "risk_observed_count_v1": risk_observed_count_v1,
    "risk_missing_count_v1": risk_missing_count_v1,
    "gap_count_v1": gap_count_v1,
    "categorical_pass_v1": categorical_pass_v1,
}


def compute_transform(
    transform_id: str,
    transform_version: str,
    records: tuple[ResolvedRecord, ...],
) -> ComputedValue:
    fn = TRANSFORMS.get(transform_id)
    if fn is None:
        raise TransformError(f"unknown transform_id: {transform_id}")
    result = fn(records)
    if result.transform_version != transform_version:
        raise TransformError(
            f"transform version mismatch: {result.transform_version} != {transform_version}"
        )
    return result
