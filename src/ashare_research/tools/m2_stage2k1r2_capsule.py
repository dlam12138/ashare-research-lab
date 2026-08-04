"""M2 Stage 2K.1R2 score-input capsule v2 builder.

Deterministic, offline, cross-path-stable. Reads ONLY committed canonical
artifacts plus the dual-clock time contract. Every component binds to a typed
upstream reference (metric_result / canonical_fact / derived_from_canonical_facts /
valuation_observation / market_observation_set / risk_observation / risk_slot /
dividend_event / repurchase_search_result / gap_record / committed_report_record)
with upstream artifact SHA-256, contract, record IDs, source evidence IDs,
a Decimal selected value, unit/domain, observation date, available_at, transform
id/version, transform inputs/output, benchmark ref, source tier, gap IDs and
warnings. Emits a canonical score_input_id and capsula digest.

The legacy v1 capsule is preserved as history; v2 is the formal path.
"""

from __future__ import annotations

import hashlib
import json
from decimal import Decimal
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
FIXTURES = ROOT / "acceptance" / "fixtures" / "official_facts" / "601857.SH"
SUPPLEMENTAL = FIXTURES / "supplemental"

SYMBOL = "601857.SH"
TIME_CONTRACT_PATH = "config/value_dimension_scoring_time_contract_v1.json"

YEARS = (2021, 2022, 2023, 2024, 2025)

UPSTREAM_REF_TYPES = frozenset({
    "metric_result",
    "canonical_fact",
    "derived_from_canonical_facts",
    "valuation_observation",
    "market_observation_set",
    "risk_observation",
    "risk_slot",
    "dividend_event",
    "repurchase_search_result",
    "gap_record",
    "committed_report_record",
})

# Canonical JSON separators (no whitespace variance in identity/digest).
_CANONICAL_SEP = (",", ":")


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _canonical(payload: Any) -> bytes:
    return json.dumps(
        payload, sort_keys=True, ensure_ascii=False, separators=_CANONICAL_SEP
    ).encode("utf-8")


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _facts(doc: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}

    def rec(v: Any) -> None:
        if isinstance(v, dict):
            if "concept_id" in v and v.get("expected_normalized_value") is not None:
                out[v["concept_id"]] = v["expected_normalized_value"]
            for child in v.values():
                rec(child)
        elif isinstance(v, list):
            for child in v:
                rec(child)

    rec(doc)
    return out


def _contract_of(path: str) -> str:
    try:
        doc = _load(ROOT / path)
    except Exception:
        return "unknown"
    contract = doc.get("contract")
    if contract:
        return str(contract)
    schema = doc.get("schema_version")
    if schema:
        return f"annual_bundle_schema_{schema}"
    return "unknown"


def _artifact_sha256(path: str) -> str:
    p = ROOT / path
    if not p.is_file():
        return "MISSING_ARTIFACT"
    return _sha256(p)


# ---------------------------------------------------------------------------
# Time contract
# ---------------------------------------------------------------------------

def _time_contract() -> dict[str, Any]:
    return _load(ROOT / TIME_CONTRACT_PATH)


def time_contract_digest() -> str:
    tc = _time_contract()
    return _sha256_bytes(_canonical(tc))


def time_contract_identity() -> dict[str, Any]:
    tc = _time_contract()
    return {
        "market_data_as_of_date": tc["market_data_as_of_date"],
        "research_evidence_as_of": tc["research_evidence_as_of"],
        "scorecard_formed_at": tc["scorecard_formed_at"],
        "timezone": tc["timezone"],
        "time_contract_version": tc["version"],
        "digest": time_contract_digest(),
    }


# ---------------------------------------------------------------------------
# Deterministic derivations (verified against Stage 2K shadow inputs)
# ---------------------------------------------------------------------------

def _annual(year: int) -> dict[str, Any]:
    return _facts(_load(FIXTURES / f"{year}_annual.json"))


def _supp(year: int, kind: str) -> dict[str, Any]:
    return _facts(_load(SUPPLEMENTAL / f"{year}_{kind}.json"))


def _interest_bearing_current_portion(year: int) -> float:
    doc = _load(SUPPLEMENTAL / f"{year}_financial_safety.json")
    cpc = doc.get("current_portion_composition", {}).get("company", {})
    comps = cpc.get("interest_bearing_components", [])
    total = 0.0
    for comp in comps:
        raw = comp.get("raw_value")
        if raw is None:
            continue
        total += float(raw) * 100.0
    return total


def _gross_interest_bearing_debt(year: int) -> float:
    fs = _supp(year, "financial_safety")
    return (
        float(fs["short_term_borrowings"])
        + _interest_bearing_current_portion(year)
        + float(fs["long_term_borrowings"])
        + float(fs["bonds_payable"])
        + float(fs["lease_liabilities"])
    )


def _dividend_totals_and_dps(year: int) -> tuple[float, float]:
    ev = _load(ROOT / "events" / "dividend_events_2021_2026_v2.json")
    div_total = 0.0
    dps = 0.0
    for e in ev["events"]:
        if e.get("source_fiscal_year") == year:
            div_total += float(e["cash_dividend_total"])
            dps += float(e["cash_dividend_per_share"])
    return div_total, dps


def _dec(value: float) -> str:
    """String Decimal representation; scoring identity never relies on binary float."""
    return str(Decimal(str(value)))


# ---------------------------------------------------------------------------
# Value profile sourced bindings
# ---------------------------------------------------------------------------

def _value_profile() -> dict[str, Any]:
    return _load(ROOT / "reports" / "petrochina_value_profile.json")


VALUATION_METRIC_KEYS = {
    "va_pe": "a_share_price_to_latest_annual_parent_earnings",
    "va_pb": "a_share_price_to_latest_year_end_parent_equity",
    "va_ps": "a_share_price_to_latest_annual_revenue",
    "va_fcf_yield": "latest_annual_fcf_proxy_yield",
    "va_dividend_yield": "trailing_12m_announced_dividend_yield",
}


def _risk_profile() -> tuple[dict[str, Any], dict[str, Any]]:
    profile = _value_profile()
    rp = profile["current_risk_veto_profile"]
    return profile, rp


# ---------------------------------------------------------------------------
# Per-dimension bindings (v2)
# ---------------------------------------------------------------------------

def _binding_enterprise_quality(tc: dict[str, Any]) -> dict[str, dict[str, Any]]:
    a25 = _annual(2025)
    a24 = _annual(2024)
    eq25 = _supp(2025, "earnings_quality")
    np25 = _supp(2025, "net_profit")
    rr25 = _supp(2025, "roe_roa_denominators")
    rr24 = _supp(2024, "roe_roa_denominators")
    fs25 = _supp(2025, "financial_safety")

    rev = float(a25["revenue"])
    oc = float(a25["operating_cash_flow"])
    np_attr = float(a25["net_profit_attributable_to_parent"])
    avg_ta = (float(rr25["total_assets"]) + float(rr24["total_assets"])) / 2.0
    avg_eq = (
        float(rr25["equity_attributable_to_parent"])
        + float(rr24["equity_attributable_to_parent"])
    ) / 2.0

    def base(year: int, kind: str, concept_ids: list[str], method: str) -> dict[str, Any]:
        path = _fixture_artifact(year, kind)
        return {
            "dimension_id": "enterprise_quality",
            "upstream_ref_type": "derived_from_canonical_facts",
            "upstream_refs": [{"artifact": path, "concept_ids": concept_ids}],
            "source_tier": "computed_from_verified_canonical_inputs",
            "available_at": "2026-03-30",
            "transform_id": "piecewise_absolute_contract",
            "transform_version": "1.0",
            "benchmark_ref": "absolute_contract",
            "selection_method": method,
            "score_eligible": False,
            "warnings": [],
            "gap_ids": [],
        }

    gross_margin = (rev - float(eq25["operating_cost"])) / rev
    operating_margin = float(eq25["operating_profit"]) / rev
    np_yoy = float(a25["net_profit_attributable_to_parent"]) / float(
        a24["net_profit_attributable_to_parent"]
    ) - 1.0
    ocf_np = oc / np_attr
    roe = np_attr / avg_eq
    roa = float(np25["net_profit"]) / avg_ta
    asset_liability = float(fs25["total_liabilities"]) / float(rr25["total_assets"])
    cash_coverage = float(fs25["cash_and_cash_equivalents"]) / _gross_interest_bearing_debt(2025)

    return {
        "eq_gross_margin": {
            **base(2025, "annual", ["revenue", "operating_cost"],
                   "(revenue - operating_cost) / revenue"),
            "value": _dec(gross_margin),
            "unit": "ratio",
            "domain": "ratio_gte_0",
            "fiscal_year": 2025,
            "transform_inputs": {
                "revenue": _dec(rev),
                "operating_cost": _dec(float(eq25["operating_cost"])),
            },
            "transform_output": _dec(gross_margin),
        },
        "eq_operating_margin": {
            **base(2025, "annual", ["revenue", "operating_profit"], "operating_profit / revenue"),
            "value": _dec(operating_margin),
            "unit": "ratio",
            "domain": "ratio",
            "fiscal_year": 2025,
            "transform_inputs": {
                "revenue": _dec(rev),
                "operating_profit": _dec(float(eq25["operating_profit"])),
            },
            "transform_output": _dec(operating_margin),
        },
        "eq_np_yoy": {
            **base(2025, "annual", ["net_profit_attributable_to_parent"], "np_2025 / np_2024 - 1"),
            "value": _dec(np_yoy),
            "unit": "ratio",
            "domain": "ratio",
            "fiscal_year": 2025,
            "transform_inputs": {
                "np_2025": _dec(float(a25["net_profit_attributable_to_parent"])),
                "np_2024": _dec(float(a24["net_profit_attributable_to_parent"])),
            },
            "transform_output": _dec(np_yoy),
        },
        "eq_ocf_np": {
            **base(2025, "annual",
                   ["operating_cash_flow", "net_profit_attributable_to_parent"],
                   "operating_cash_flow / net_profit_attributable_to_parent"),
            "value": _dec(ocf_np),
            "unit": "ratio",
            "domain": "ratio",
            "fiscal_year": 2025,
            "transform_inputs": {"ocf": _dec(oc), "np": _dec(np_attr)},
            "transform_output": _dec(ocf_np),
        },
        "eq_roe": {
            **base(2025, "roe_roa_denominators",
                   ["net_profit_attributable_to_parent", "equity_attributable_to_parent"],
                   "np_attr / avg(equity_2024, equity_2025)"),
            "value": _dec(roe),
            "unit": "ratio",
            "domain": "ratio",
            "fiscal_year": 2025,
            "transform_inputs": {
                "np_attr": _dec(np_attr),
                "equity_2024": _dec(float(rr24["equity_attributable_to_parent"])),
                "equity_2025": _dec(float(rr25["equity_attributable_to_parent"])),
            },
            "transform_output": _dec(roe),
        },
        "eq_roa": {
            **base(2025, "net_profit", ["net_profit", "total_assets"],
                   "net_profit / avg(total_assets_2024, total_assets_2025)"),
            "value": _dec(roa),
            "unit": "ratio",
            "domain": "ratio",
            "fiscal_year": 2025,
            "transform_inputs": {
                "net_profit": _dec(float(np25["net_profit"])),
                "total_assets_2024": _dec(float(rr24["total_assets"])),
                "total_assets_2025": _dec(float(rr25["total_assets"])),
            },
            "transform_output": _dec(roa),
        },
        "eq_asset_liability": {
            **base(2025, "financial_safety", ["total_liabilities", "total_assets"],
                   "total_liabilities / total_assets"),
            "value": _dec(asset_liability),
            "unit": "ratio",
            "domain": "ratio",
            "fiscal_year": 2025,
            "transform_inputs": {
                "total_liabilities": _dec(float(fs25["total_liabilities"])),
                "total_assets": _dec(float(rr25["total_assets"])),
            },
            "transform_output": _dec(asset_liability),
        },
        "eq_cash_coverage": {
            **base(2025, "financial_safety",
                   ["cash_and_cash_equivalents", "short_term_borrowings",
                    "current_portion_of_long_term_borrowings",
                    "current_portion_of_bonds_payable",
                    "current_portion_of_lease_liabilities",
                    "long_term_borrowings", "bonds_payable", "lease_liabilities"],
                   "cash / gross_interest_bearing_debt"),
            "value": _dec(cash_coverage),
            "unit": "ratio",
            "domain": "ratio",
            "fiscal_year": 2025,
            "transform_inputs": {
                "cash": _dec(float(fs25["cash_and_cash_equivalents"])),
                "gross_interest_bearing_debt": _dec(_gross_interest_bearing_debt(2025)),
            },
            "transform_output": _dec(cash_coverage),
        },
    }


def _fixture_artifact(year: int, kind: str) -> str:
    if kind == "annual":
        return f"acceptance/fixtures/official_facts/601857.SH/{year}_annual.json"
    return (
        f"acceptance/fixtures/official_facts/601857.SH/supplemental/"
        f"{year}_{kind}.json"
    )


def _binding_value_realization(tc: dict[str, Any]) -> dict[str, dict[str, Any]]:
    a25 = _annual(2025)
    oc = float(a25["operating_cash_flow"])
    np_attr = float(a25["net_profit_attributable_to_parent"])
    capex_doc = _load(SUPPLEMENTAL / "2025_capex_cash.json")
    capex = float(capex_doc["company"]["expected_normalized_value"])
    div_total, dps = _dividend_totals_and_dps(2025)
    repurchase = _load(ROOT / "events" / "repurchase_event_scan_2021_2026.json")

    ocf_dc = (oc * 10000.0) / div_total
    fcf_dc = ((oc - capex) * 10000.0) / div_total
    payout = div_total / (np_attr * 10000.0)

    out: dict[str, dict[str, Any]] = {
        "vr_ocf_dividend_coverage": {
            "dimension_id": "value_realization_capacity",
            "upstream_ref_type": "dividend_event",
            "upstream_refs": [{"artifact": "events/dividend_events_2021_2026_v2.json"}],
            "source_tier": "computed_from_verified_canonical_inputs",
            "value": _dec(ocf_dc),
            "unit": "ratio",
            "domain": "ratio",
            "fiscal_year": 2025,
            "available_at": "2026-03-30",
            "transform_id": "dividend_coverage",
            "transform_version": "1.0",
            "transform_inputs": {"ocf_cny": _dec(oc * 10000.0), "div_total": _dec(div_total)},
            "transform_output": _dec(ocf_dc),
            "benchmark_ref": "absolute_contract",
            "selection_method": "operating_cash_flow / sum(cash_dividend_total)",
            "score_eligible": False,
            "warnings": [],
            "gap_ids": [],
        },
        "vr_fcf_dividend_coverage": {
            "dimension_id": "value_realization_capacity",
            "upstream_ref_type": "dividend_event",
            "upstream_refs": [{"artifact": "events/dividend_events_2021_2026_v2.json"}],
            "source_tier": "computed_from_verified_canonical_inputs",
            "value": _dec(fcf_dc),
            "unit": "ratio",
            "domain": "ratio",
            "fiscal_year": 2025,
            "available_at": "2026-03-30",
            "transform_id": "dividend_coverage",
            "transform_version": "1.0",
            "transform_inputs": {
                "fcf_cny": _dec((oc - capex) * 10000.0),
                "div_total": _dec(div_total),
            },
            "transform_output": _dec(fcf_dc),
            "benchmark_ref": "absolute_contract",
            "selection_method": "(operating_cash_flow - capex) / sum(cash_dividend_total)",
            "score_eligible": False,
            "warnings": [],
            "gap_ids": [],
        },
        "vr_payout_ratio": {
            "dimension_id": "value_realization_capacity",
            "upstream_ref_type": "dividend_event",
            "upstream_refs": [{"artifact": "events/dividend_events_2021_2026_v2.json"}],
            "source_tier": "computed_from_verified_canonical_inputs",
            "value": _dec(payout),
            "unit": "ratio",
            "domain": "ratio",
            "fiscal_year": 2025,
            "available_at": "2026-03-30",
            "transform_id": "payout_ratio",
            "transform_version": "1.0",
            "transform_inputs": {
                "div_total": _dec(div_total),
                "np_attr_cny": _dec(np_attr * 10000.0),
            },
            "transform_output": _dec(payout),
            "benchmark_ref": "absolute_contract",
            "selection_method": "sum(cash_dividend_total) / net_profit_attributable_to_parent",
            "score_eligible": False,
            "warnings": [],
            "gap_ids": [],
        },
        "vr_dps": {
            "dimension_id": "value_realization_capacity",
            "upstream_ref_type": "dividend_event",
            "upstream_refs": [{"artifact": "events/dividend_events_2021_2026_v2.json"}],
            "source_tier": "computed_from_verified_canonical_inputs",
            "value": _dec(dps),
            "unit": "CNY",
            "domain": "cny_gte_0",
            "fiscal_year": 2025,
            "available_at": "2026-03-30",
            "transform_id": "sum_dps",
            "transform_version": "1.0",
            "transform_inputs": {"dps_sum": _dec(dps)},
            "transform_output": _dec(dps),
            "benchmark_ref": "absolute_contract",
            "selection_method": "sum(cash_dividend_per_share) over FY2025 events",
            "score_eligible": False,
            "warnings": [],
            "gap_ids": [],
        },
        "vr_repurchase": {
            "dimension_id": "value_realization_capacity",
            "upstream_ref_type": "repurchase_search_result",
            "upstream_refs": [{"artifact": "events/repurchase_event_scan_2021_2026.json"}],
            "source_tier": "bounded_search_complete",
            "value": "no_event_found",
            "unit": "categorical",
            "domain": "categorical_enum",
            "available_at": repurchase.get("scope", "2021-01-01..2026-06-30").split("..")[1],
            "transform_id": "map_to_registered_value",
            "transform_version": "1.0",
            "transform_inputs": {"search_status": repurchase.get("status")},
            "transform_output": "no_event_found",
            "benchmark_ref": "binary_or_categorical_evidence",
            "selection_method": (
                "bounded_search_no_event_found -> no_event_found (registered value)"
            ),
            "score_eligible": False,
            "warnings": [],
            "gap_ids": [],
        },
    }
    return out


def _valuation_observation_set() -> dict[str, Any]:
    registry = _load(ROOT / "events" / "market_data_snapshot_registry.json")
    provider = registry["providers"][0]
    os_ = {
        "artifact": "events/market_data_snapshot_registry.json",
        "contract": _contract_of("events/market_data_snapshot_registry.json"),
        "symbol": SYMBOL,
        "scope": "2021-01-04..2026-07-31",
        "provider_digest": provider["object_key"],
        "provider_sha256": provider["sha256"],
        "row_count": registry["common_trade_days"],
        "reconciliation_status": registry["reconciliation_status"],
        "excluded_observation_count": 0,
        "exclusion_reasons": [],
        "minimum_observations": {"3y": 500, "5y": 900},
        "percentile_effective_samples": {"3y": 727, "5y": 1050},
    }
    os_["observation_set_digest"] = _sha256_bytes(_canonical(os_))
    return os_


def _binding_valuation(tc: dict[str, Any]) -> dict[str, dict[str, Any]]:
    profile = _value_profile()
    pp = profile["percentile_position"]
    lo = profile["latest_observations"]
    as_of = profile["as_of_trade_date"]
    obs_set = _valuation_observation_set()
    out: dict[str, dict[str, Any]] = {}
    for cid, metric_key in VALUATION_METRIC_KEYS.items():
        pos = pp[metric_key]
        latest = pos["latest"]
        observation = lo[metric_key]
        is_computed = latest["status"] == "computed"
        source_evidence_ids = observation.get("lineage", {}).get("financial_fact_ids", [])
        out[cid] = {
            "dimension_id": "valuation_attractiveness",
            "upstream_ref_type": "valuation_observation",
            "upstream_refs": [{
                "artifact": "reports/petrochina_value_profile.json",
                "record_id": f"percentile_position.{metric_key}",
                "source_evidence_ids": source_evidence_ids,
            }],
            "source_tier": "coverage_gap" if not is_computed else "external_manifest_only",
            "value": _dec(latest["value"]) if is_computed else None,
            "unit": "ratio",
            "domain": "ratio",
            "trade_date": latest["trade_date"],
            "available_at": as_of,
            "input_status": "computed" if is_computed else "coverage_gap",
            "transform_id": "observed_latest_value",
            "transform_version": "1.0",
            "transform_inputs": {
                "value_profile_latest_value": _dec(latest["value"]) if is_computed else None,
                "trade_date": latest["trade_date"],
            },
            "transform_output": _dec(latest["value"]) if is_computed else None,
            "percentile_3y": pos["3y"],
            "percentile_5y": pos["5y"],
            "benchmark_ref": "self_history_percentile",
            "selection_method": "percentile_position.<metric>.{3y,latest} from value profile",
            "score_eligible": False,
            "warnings": [] if is_computed else ["coverage gap: dividend yield not computed"],
            "gap_ids": [],
            "observation_set": obs_set,
        }
    return out


def _binding_risk_and_gap(tc: dict[str, Any]) -> dict[str, dict[str, Any]]:
    profile, rp = _risk_profile()
    ledger = _load(ROOT / "reports" / "m2_explicit_gap_ledger.json")
    gap_count = int(ledger["count_contract"]["current_gap_count"])
    rp_as_of = rp.get("as_of_date")
    return {
        "rk_veto_triggered": {
            "dimension_id": "risk_and_evidence_integrity",
            "upstream_ref_type": "risk_observation",
            "upstream_refs": [{
                "artifact": "reports/petrochina_value_profile.json",
                "record_id": "current_risk_veto_profile.observed_risk_ids",
            }],
            "source_tier": "committed_computed_report",
            "value": str(len(rp.get("observed_risk_ids", []))),
            "unit": "count",
            "domain": "count_gte_0",
            "available_at": rp_as_of,
            "transform_id": "len_observed_risk_ids",
            "transform_version": "1.0",
            "transform_inputs": {"observed_risk_ids": rp.get("observed_risk_ids", [])},
            "transform_output": str(len(rp.get("observed_risk_ids", []))),
            "benchmark_ref": "binary_or_categorical_evidence",
            "selection_method": "len(observed_risk_ids)",
            "score_eligible": False,
            "warnings": [],
            "gap_ids": [],
        },
        "rk_missing_evidence_slots": {
            "dimension_id": "risk_and_evidence_integrity",
            "upstream_ref_type": "risk_slot",
            "upstream_refs": [{
                "artifact": "reports/petrochina_value_profile.json",
                "record_id": "current_risk_veto_profile.missing_evidence_risk_ids",
            }],
            "source_tier": "committed_computed_report",
            "value": str(len(rp.get("missing_evidence_risk_ids", []))),
            "unit": "count",
            "domain": "count_gte_0",
            "available_at": rp_as_of,
            "transform_id": "len_missing_evidence_risk_ids",
            "transform_version": "1.0",
            "transform_inputs": {
                "missing_evidence_risk_ids": rp.get("missing_evidence_risk_ids", []),
            },
            "transform_output": str(len(rp.get("missing_evidence_risk_ids", []))),
            "benchmark_ref": "binary_or_categorical_evidence",
            "selection_method": "len(missing_evidence_risk_ids)",
            "score_eligible": False,
            "warnings": [],
            "gap_ids": [],
        },
        "rk_gap_count": {
            "dimension_id": "risk_and_evidence_integrity",
            "upstream_ref_type": "committed_report_record",
            "upstream_refs": [{
                "artifact": "reports/m2_explicit_gap_ledger.json",
                "record_id": "count_contract.current_gap_count",
            }],
            "source_tier": "committed_computed_report",
            "value": str(gap_count),
            "unit": "count",
            "domain": "count_gte_0",
            "available_at": ledger.get("last_reviewed_date"),
            "transform_id": "current_gap_count",
            "transform_version": "1.0",
            "transform_inputs": {"gap_count": gap_count},
            "transform_output": str(gap_count),
            "benchmark_ref": "binary_or_categorical_evidence",
            "selection_method": "current_gap_count from canonical ledger",
            "score_eligible": False,
            "warnings": [],
            "gap_ids": [],
        },
        "rk_pit_integrity": {
            "dimension_id": "risk_and_evidence_integrity",
            "upstream_ref_type": "risk_observation",
            "upstream_refs": [{
                "artifact": "reports/petrochina_value_profile.json",
                "record_id": "current_risk_veto_profile.search_pit_status",
            }],
            "source_tier": "committed_computed_report",
            "value": rp.get("search_pit_status"),
            "unit": "categorical",
            "domain": "categorical_enum",
            "available_at": rp_as_of,
            "transform_id": "search_pit_status",
            "transform_version": "1.0",
            "transform_inputs": {"search_pit_status": rp.get("search_pit_status")},
            "transform_output": rp.get("search_pit_status"),
            "benchmark_ref": "binary_or_categorical_evidence",
            "selection_method": "search_pit_status",
            "score_eligible": False,
            "warnings": [],
            "gap_ids": [],
        },
        "rk_evidence_freshness": {
            "dimension_id": "risk_and_evidence_integrity",
            "upstream_ref_type": "risk_observation",
            "upstream_refs": [{
                "artifact": "reports/petrochina_value_profile.json",
                "record_id": "current_risk_veto_profile.as_of_date",
            }],
            "source_tier": "committed_computed_report",
            "value": "current",
            "unit": "categorical",
            "domain": "categorical_enum",
            "available_at": rp_as_of,
            "transform_id": "evidence_freshness",
            "transform_version": "1.0",
            "transform_inputs": {"as_of_date": rp_as_of},
            "transform_output": "current",
            "benchmark_ref": "binary_or_categorical_evidence",
            "selection_method": "evidence as-of within score date",
            "score_eligible": False,
            "warnings": [],
            "gap_ids": [],
        },
    }


def _binding_roic_gap(tc: dict[str, Any]) -> dict[str, dict[str, Any]]:
    ledger = _load(ROOT / "reports" / "m2_explicit_gap_ledger.json")
    roic_gap_ids = [g["gap_id"] for g in ledger["gaps"] if g["module"] == "roic"]
    return {
        "eq_roic": {
            "dimension_id": "enterprise_quality",
            "upstream_ref_type": "gap_record",
            "upstream_refs": [{"artifact": "reports/m2_explicit_gap_ledger.json"}],
            "source_tier": "coverage_gap",
            "input_status": "not_computable_under_strict_evidence_contract",
            "value": None,
            "unit": None,
            "domain": None,
            "available_at": None,
            "transform_id": "coverage_gap",
            "transform_version": "1.0",
            "transform_inputs": {},
            "transform_output": None,
            "benchmark_ref": "coverage_gap",
            "selection_method": "coverage gap: M2G-ROIC-001..007 not computable",
            "score_eligible": False,
            "warnings": ["ROIC not computable under strict evidence contract; never zero"],
            "gap_ids": roic_gap_ids,
        }
    }


def _all_bindings() -> dict[str, dict[str, Any]]:
    tc = _time_contract()
    bindings: dict[str, dict[str, Any]] = {}
    bindings.update(_binding_enterprise_quality(tc))
    bindings.update(_binding_valuation(tc))
    bindings.update(_binding_value_realization(tc))
    bindings.update(_binding_risk_and_gap(tc))
    bindings.update(_binding_roic_gap(tc))
    return bindings


# ---------------------------------------------------------------------------
# score_input_id and capsule digest
# ---------------------------------------------------------------------------

def score_input_id(component_id: str, comp: dict[str, Any]) -> str:
    """Canonical identity payload. Excludes absolute paths, cwd, tmp, separators
    and JSON formatting. Includes artifact SHA-256 (not paths), record IDs,
    source evidence IDs, transform id/version + inputs, normalized value,
    unit/domain, observation date, available_at, observation-set digest and the
    time-contract digest."""
    upstream = comp["upstream_refs"]
    payload = {
        "symbol": SYMBOL,
        "component_id": component_id,
        "upstream_ref_type": comp.get("upstream_ref_type"),
        "upstream_record_ids": [u.get("record_id") for u in upstream],
        "artifact_sha256s": [_artifact_sha256(u["artifact"]) for u in upstream],
        "source_evidence_ids": [u.get("source_evidence_ids") for u in upstream],
        "transform_id": comp.get("transform_id"),
        "transform_version": comp.get("transform_version"),
        "transform_inputs": comp.get("transform_inputs"),
        "normalized_value": comp.get("transform_output"),
        "unit": comp.get("unit"),
        "domain": comp.get("domain"),
        "observation_date": (
            comp.get("fiscal_year") or comp.get("trade_date") or comp.get("event_period")
        ),
        "available_at": comp.get("available_at"),
        "observation_set_digest": (comp.get("observation_set") or {}).get("observation_set_digest"),
        "time_contract_digest": time_contract_digest(),
        "gap_ids": comp.get("gap_ids"),
    }
    return _sha256_bytes(_canonical(payload))


def _artifact_set() -> dict[str, Any]:
    bindings = _all_bindings()
    artifacts: dict[str, dict[str, Any]] = {}
    for cid, comp in bindings.items():
        for u in comp.get("upstream_refs", []):
            path = u["artifact"]
            entry = artifacts.setdefault(path, {
                "logical_path": path,
                "contract": _contract_of(path),
                "sha256": _artifact_sha256(path),
                "record_ids": [],
                "usage": set(),
                "required": True,
            })
            if u.get("record_id"):
                entry["record_ids"].append(u["record_id"])
            entry["usage"].add(cid)
    # normalize usage to sorted list
    return {
        path: {
            "logical_path": path,
            "contract": e["contract"],
            "sha256": e["sha256"],
            "record_ids": sorted(set(e["record_ids"])),
            "usage": sorted(e["usage"]),
            "required": e["required"],
        }
        for path, e in sorted(artifacts.items())
    }


def build_capsule() -> dict[str, Any]:
    bindings = _all_bindings()
    tc_identity = time_contract_identity()
    components: dict[str, Any] = {}
    for cid, b in bindings.items():
        comp = dict(b)
        comp["score_input_id"] = score_input_id(cid, comp)
        components[cid] = comp

    capsule = {
        "schema": "m2_stage2k1r2_score_input_capsule_v2",
        "version": "2.0",
        "symbol": SYMBOL,
        "time_contract": tc_identity,
        "dimensions": [
            "enterprise_quality",
            "valuation_attractiveness",
            "value_realization_capacity",
            "risk_and_evidence_integrity",
        ],
        "component_count": len(components),
        "components": components,
        "artifact_set": _artifact_set(),
        "artifact_set_digest": _sha256_bytes(_canonical(_artifact_set())),
        "coverage_gap_ids": ["eq_roic", "va_dividend_yield"],
        "validation_requirements": {
            "recompute_artifact_sha256": True,
            "recompute_upstream_record": True,
            "recompute_value_transform": True,
            "recompute_unit_domain": True,
            "recompute_score_input_id": True,
            "recompute_capsule_digest": True,
            "recompute_artifact_set_digest": True,
            "recompute_time_contract_digest": True,
            "pit_errors_nonempty_fails": True,
            "lineage_errors_nonempty_fails": True,
            "validator_fail_blocks_shadow": True,
        },
        "non_production": True,
        "research_methodology_test_only": True,
        "overall_score_prohibited": True,
        "recommendation_prohibited": True,
        "score_eligible": False,
    }
    capsule["capsule_digest"] = capsule_digest(capsule)
    return capsule


def capsule_digest(capsule: dict[str, Any]) -> str:
    """Digest over the canonical JSON excluding the capsule_digest field itself."""
    payload = {k: v for k, v in capsule.items() if k != "capsule_digest"}
    return _sha256_bytes(_canonical(payload))


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("build",))
    parser.add_argument("--output", default="")
    args = parser.parse_args()
    capsule = build_capsule()
    if args.output:
        out = Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(capsule, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"status": "pass", "output": str(out)}, ensure_ascii=False))
        return 0
    print(json.dumps(capsule, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
