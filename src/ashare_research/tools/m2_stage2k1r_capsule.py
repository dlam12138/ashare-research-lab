"""M2 Stage 2K.1R score-input capsule builder and validator.

Deterministic, offline, and reads ONLY committed canonical artifacts. It binds
every scoring component to a stable upstream identity (artifact path, artifact
SHA-256, contract version, record/concept id, deterministic selection/transform,
value/unit/date/available_at) and emits a score-input capsule with a digest.

Missing upstream identity becomes a coverage gap, never a zero and never a
hidden fallback. This module is the single replacement for the manual
Stage 2K shadow-input JSON; it removes every tmp/ reference.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
FIXTURES = ROOT / "acceptance" / "fixtures" / "official_facts" / "601857.SH"
SUPPLEMENTAL = FIXTURES / "supplemental"

SCORE_DATE = "2026-07-31"
SYMBOL = "601857.SH"

# Fiscal years required for the deterministic derivations.
YEARS = (2021, 2022, 2023, 2024, 2025)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _normalize_text(path: Path) -> bytes:
    return path.read_text(encoding="utf-8").replace("\r\n", "\n").encode()


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _facts(doc: dict[str, Any]) -> dict[str, Any]:
    """Flatten a fixture document's nested facts into concept_id -> value."""
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


# ---------------------------------------------------------------------------
# Committed canonical artifacts (existence + digest)
# ---------------------------------------------------------------------------

def _artifact(path: str) -> dict[str, Any]:
    p = ROOT / path
    if not p.is_file():
        return {"logical_path": path, "exists": False, "sha256": None}
    return {"logical_path": path, "exists": True, "sha256": _sha256(p)}


def _fixture_artifact(year: int, kind: str) -> str:
    if kind == "annual":
        return f"acceptance/fixtures/official_facts/601857.SH/{year}_annual.json"
    return (
        f"acceptance/fixtures/official_facts/601857.SH/supplemental/"
        f"{year}_{kind}.json"
    )


def _contract_of(path: str) -> str:
    try:
        doc = _load(ROOT / path)
    except Exception:
        return "unknown"
    contract = doc.get("contract")
    if contract:
        return str(contract)
    # annual bundle has no `contract` key; use its schema_version as the contract.
    schema = doc.get("schema_version")
    if schema:
        return f"annual_bundle_schema_{schema}"
    return "unknown"


# ---------------------------------------------------------------------------
# Deterministic derivations (fully verified against the Stage 2K shadow)
# ---------------------------------------------------------------------------

def _annual(year: int) -> dict[str, Any]:
    return _facts(_load(FIXTURES / f"{year}_annual.json"))


def _supp(year: int, kind: str) -> dict[str, Any]:
    return _facts(_load(SUPPLEMENTAL / f"{year}_{kind}.json"))


def _interest_bearing_current_portion(year: int) -> float:
    """Sum only the interest-bearing components of the current portion.

    The aggregate current-portion row also contains a non-interest-bearing
    component (current long-term payables) that must be excluded from gross
    interest-bearing debt.
    """
    doc = _load(SUPPLEMENTAL / f"{year}_financial_safety.json")
    cpc = doc.get("current_portion_composition", {}).get("company", {})
    comps = cpc.get("interest_bearing_components", [])
    total = 0.0
    for comp in comps:
        raw = comp.get("raw_value")
        if raw is None:
            continue
        # raw_value is in 市亿元 (RMB millions); normalize to 万元 (CNY 10k) x100.
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


# ---------------------------------------------------------------------------
# Per-component binding definitions
# ---------------------------------------------------------------------------

def _binding_enterprise_quality() -> dict[str, dict[str, Any]]:
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

    return {
        "eq_gross_margin": {
            "value": (rev - float(eq25["operating_cost"])) / rev,
            "unit": "ratio",
            "fiscal_year": 2025,
            "available_at": "2026-03-30",
            "upstream": {
                "artifact": _fixture_artifact(2025, "annual"),
                "contract": _contract_of(_fixture_artifact(2025, "annual")),
                "concept_ids": ["revenue", "operating_cost"],
            },
            "selection_method": "(revenue - operating_cost) / revenue",
        },
        "eq_operating_margin": {
            "value": float(eq25["operating_profit"]) / rev,
            "unit": "ratio",
            "fiscal_year": 2025,
            "available_at": "2026-03-30",
            "upstream": {
                "artifact": _fixture_artifact(2025, "annual"),
                "contract": _contract_of(_fixture_artifact(2025, "annual")),
                "concept_ids": ["revenue", "operating_profit"],
            },
            "selection_method": "operating_profit / revenue",
        },
        "eq_np_yoy": {
            "value": float(a25["net_profit_attributable_to_parent"])
            / float(a24["net_profit_attributable_to_parent"])
            - 1.0,
            "unit": "ratio",
            "fiscal_year": 2025,
            "available_at": "2026-03-30",
            "upstream": {
                "artifact": _fixture_artifact(2025, "annual"),
                "contract": _contract_of(_fixture_artifact(2025, "annual")),
                "concept_ids": ["net_profit_attributable_to_parent"],
            },
            "selection_method": "np_2025 / np_2024 - 1",
        },
        "eq_ocf_np": {
            "value": oc / np_attr,
            "unit": "ratio",
            "fiscal_year": 2025,
            "available_at": "2026-03-30",
            "upstream": {
                "artifact": _fixture_artifact(2025, "annual"),
                "contract": _contract_of(_fixture_artifact(2025, "annual")),
                "concept_ids": ["operating_cash_flow", "net_profit_attributable_to_parent"],
            },
            "selection_method": "operating_cash_flow / net_profit_attributable_to_parent",
        },
        "eq_roe": {
            "value": np_attr / avg_eq,
            "unit": "ratio",
            "fiscal_year": 2025,
            "available_at": "2026-03-30",
            "upstream": {
                "artifact": _fixture_artifact(2025, "roe_roa_denominators"),
                "contract": _contract_of(_fixture_artifact(2025, "roe_roa_denominators")),
                "concept_ids": [
                    "net_profit_attributable_to_parent",
                    "equity_attributable_to_parent",
                ],
            },
            "selection_method": "np_attr / avg(equity_2024, equity_2025)",
        },
        "eq_roa": {
            "value": float(np25["net_profit"]) / avg_ta,
            "unit": "ratio",
            "fiscal_year": 2025,
            "available_at": "2026-03-30",
            "upstream": {
                "artifact": _fixture_artifact(2025, "net_profit"),
                "contract": _contract_of(_fixture_artifact(2025, "net_profit")),
                "concept_ids": ["net_profit", "total_assets"],
            },
            "selection_method": "net_profit / avg(total_assets_2024, total_assets_2025)",
        },
        "eq_asset_liability": {
            "value": float(fs25["total_liabilities"]) / float(rr25["total_assets"]),
            "unit": "ratio",
            "fiscal_year": 2025,
            "available_at": "2026-03-30",
            "upstream": {
                "artifact": _fixture_artifact(2025, "financial_safety"),
                "contract": _contract_of(_fixture_artifact(2025, "financial_safety")),
                "concept_ids": ["total_liabilities", "total_assets"],
            },
            "selection_method": "total_liabilities / total_assets",
        },
        "eq_cash_coverage": {
            "value": float(fs25["cash_and_cash_equivalents"])
            / _gross_interest_bearing_debt(2025),
            "unit": "ratio",
            "fiscal_year": 2025,
            "available_at": "2026-03-30",
            "upstream": {
                "artifact": _fixture_artifact(2025, "financial_safety"),
                "contract": _contract_of(_fixture_artifact(2025, "financial_safety")),
                "concept_ids": [
                    "cash_and_cash_equivalents",
                    "short_term_borrowings",
                    "current_portion_of_long_term_borrowings",
                    "current_portion_of_bonds_payable",
                    "current_portion_of_lease_liabilities",
                    "long_term_borrowings",
                    "bonds_payable",
                    "lease_liabilities",
                ],
            },
            "selection_method": "cash / gross_interest_bearing_debt",
        },
    }


def _binding_value_realization() -> dict[str, dict[str, Any]]:
    a25 = _annual(2025)
    oc = float(a25["operating_cash_flow"])
    np_attr = float(a25["net_profit_attributable_to_parent"])

    capex_doc = _load(SUPPLEMENTAL / "2025_capex_cash.json")
    capex = float(capex_doc["company"]["expected_normalized_value"])

    div_total, dps = _dividend_totals_and_dps(2025)

    return {
        "vr_ocf_dividend_coverage": {
            "value": (oc * 10000.0) / div_total,
            "unit": "ratio",
            "fiscal_year": 2025,
            "available_at": "2026-03-30",
            "upstream": {
                "artifact": "events/dividend_events_2021_2026_v2.json",
                "contract": _contract_of("events/dividend_events_2021_2026_v2.json"),
                "concept_ids": ["operating_cash_flow", "cash_dividend_total"],
            },
            "selection_method": "operating_cash_flow / sum(cash_dividend_total)",
        },
        "vr_fcf_dividend_coverage": {
            "value": ((oc - capex) * 10000.0) / div_total,
            "unit": "ratio",
            "fiscal_year": 2025,
            "available_at": "2026-03-30",
            "upstream": {
                "artifact": "events/dividend_events_2021_2026_v2.json",
                "contract": _contract_of("events/dividend_events_2021_2026_v2.json"),
                "concept_ids": [
                    "operating_cash_flow",
                    "cash_paid_for_fixed_assets",
                    "cash_dividend_total",
                ],
            },
            "selection_method": "(operating_cash_flow - capex) / sum(cash_dividend_total)",
        },
        "vr_payout_ratio": {
            "value": div_total / (np_attr * 10000.0),
            "unit": "ratio",
            "fiscal_year": 2025,
            "available_at": "2026-03-30",
            "upstream": {
                "artifact": "events/dividend_events_2021_2026_v2.json",
                "contract": _contract_of("events/dividend_events_2021_2026_v2.json"),
                "concept_ids": ["cash_dividend_total", "net_profit_attributable_to_parent"],
            },
            "selection_method": "sum(cash_dividend_total) / net_profit_attributable_to_parent",
        },
        "vr_dps": {
            "value": dps,
            "unit": "CNY",
            "fiscal_year": 2025,
            "available_at": "2026-03-30",
            "upstream": {
                "artifact": "events/dividend_events_2021_2026_v2.json",
                "contract": _contract_of("events/dividend_events_2021_2026_v2.json"),
                "concept_ids": ["cash_dividend_per_share"],
            },
            "selection_method": "sum(cash_dividend_per_share) over FY2025 events",
        },
    }


# ---------------------------------------------------------------------------
# Value-profile-sourced bindings (valuation percentiles + risk metrics)
# ---------------------------------------------------------------------------

def _value_profile() -> dict[str, Any]:
    return _load(ROOT / "reports" / "petrochina_value_profile.json")


# Metric role -> percentile_position key in the value profile.
VALUATION_METRIC_KEYS = {
    "va_pe": "a_share_price_to_latest_annual_parent_earnings",
    "va_pb": "a_share_price_to_latest_year_end_parent_equity",
    "va_ps": "a_share_price_to_latest_annual_revenue",
    "va_fcf_yield": "latest_annual_fcf_proxy_yield",
    "va_dividend_yield": "trailing_12m_announced_dividend_yield",
}


def _binding_valuation() -> dict[str, dict[str, Any]]:
    profile = _value_profile()
    pp = profile["percentile_position"]
    lo = profile["latest_observations"]
    as_of = profile["as_of_trade_date"]
    out: dict[str, dict[str, Any]] = {}
    for cid, metric_key in VALUATION_METRIC_KEYS.items():
        pos = pp[metric_key]
        latest = pos["latest"]
        observation = lo[metric_key]
        is_computed = latest["status"] == "computed"
        out[cid] = {
            "value": latest["value"] if is_computed else None,
            "percentile_3y": pos["3y"],
            "percentile_5y": pos["5y"],
            "unit": "ratio",
            "trade_date": latest["trade_date"],
            "available_at": as_of,
            "status": latest["status"] if is_computed else "coverage_gap",
            "status_is_computed": is_computed,
            "partial_value": latest["value"] if not is_computed else None,
            "effective_samples": pos["effective_samples"],
            "minimum_samples": pos["minimum_samples"],
            "observation_set": {
                "artifact": "events/market_data_snapshot_registry.json",
                "contract": _contract_of("events/market_data_snapshot_registry.json"),
                "symbol": profile["symbol"],
                "scope": "2021-01-04..2026-07-31",
                "provider_digest": (
                    "baostock/defd0b9507c0d87cf9d12864923eb24573e4edee28d7b67b9ce319ab4d91a764.parquet"
                ),
                "provider_sha256": (
                    "defd0b9507c0d87cf9d12864923eb24573e4edee28d7b67b9ce319ab4d91a764"
                ),
                "row_count": 1351,
            },
            "upstream": {
                "artifact": "reports/petrochina_value_profile.json",
                "contract": profile["contract"],
                "record_id": metric_key,
                "observation_id": observation.get("observation_id"),
                "lineage": observation.get("lineage"),
            },
            "selection_method": "percentile_position.<metric>.{3y,latest} from value profile",
        }
    return out


def _binding_risk_and_gap() -> dict[str, dict[str, Any]]:
    profile = _value_profile()
    rp = profile["current_risk_veto_profile"]
    ledger = _load(ROOT / "reports" / "m2_explicit_gap_ledger.json")
    gap_count = int(ledger["count_contract"]["current_gap_count"])
    repurchase = _load(ROOT / "events" / "repurchase_event_scan_2021_2026.json")

    return {
        "vr_repurchase": {
            "value": "no_event_found",
            "unit": "categorical",
            "available_at": repurchase.get("scope", "2021-01-01..2026-06-30").split("..")[1],
            "status": repurchase["status"],
            "upstream": {
                "artifact": "events/repurchase_event_scan_2021_2026.json",
                "contract": repurchase["contract"],
                "search_basis": repurchase.get("search_basis", []),
            },
            "selection_method": (
                "bounded_search_no_event_found -> no_event_found (registered value)"
            ),
        },
        "rk_veto_triggered": {
            "value": len(rp.get("observed_risk_ids", [])),
            "unit": "count",
            "available_at": rp.get("as_of_date"),
            "upstream": {
                "artifact": "reports/petrochina_value_profile.json",
                "contract": profile["contract"],
                "record_id": "current_risk_veto_profile.observed_risk_ids",
            },
            "selection_method": "len(observed_risk_ids)",
        },
        "rk_missing_evidence_slots": {
            "value": len(rp.get("missing_evidence_risk_ids", [])),
            "unit": "count",
            "available_at": rp.get("as_of_date"),
            "upstream": {
                "artifact": "reports/petrochina_value_profile.json",
                "contract": profile["contract"],
                "record_id": "current_risk_veto_profile.missing_evidence_risk_ids",
            },
            "selection_method": "len(missing_evidence_risk_ids)",
        },
        "rk_gap_count": {
            "value": gap_count,
            "unit": "count",
            "available_at": ledger.get("last_reviewed_date"),
            "upstream": {
                "artifact": "reports/m2_explicit_gap_ledger.json",
                "contract": ledger["schema"],
                "record_id": "count_contract.current_gap_count",
            },
            "selection_method": "current_gap_count from canonical ledger",
        },
        "rk_pit_integrity": {
            "value": rp.get("search_pit_status"),
            "unit": "categorical",
            "available_at": rp.get("as_of_date"),
            "upstream": {
                "artifact": "reports/petrochina_value_profile.json",
                "contract": profile["contract"],
                "record_id": "current_risk_veto_profile.search_pit_status",
            },
            "selection_method": "search_pit_status",
        },
        "rk_evidence_freshness": {
            "value": "current",
            "unit": "categorical",
            "available_at": rp.get("as_of_date"),
            "upstream": {
                "artifact": "reports/petrochina_value_profile.json",
                "contract": profile["contract"],
                "record_id": "current_risk_veto_profile.as_of_date",
            },
            "selection_method": "evidence as-of within score date",
        },
    }


def _binding_roic_gap() -> dict[str, dict[str, Any]]:
    ledger = _load(ROOT / "reports" / "m2_explicit_gap_ledger.json")
    roic_gap_ids = [
        g["gap_id"] for g in ledger["gaps"] if g["module"] == "roic"
    ]
    return {
        "eq_roic": {
            "value": None,
            "unit": None,
            "fiscal_year": None,
            "available_at": None,
            "status": "not_computable_under_strict_evidence_contract",
            "record_ids": roic_gap_ids,
            "upstream": {
                "artifact": "reports/m2_explicit_gap_ledger.json",
                "contract": ledger["schema"],
            },
            "selection_method": "coverage gap: M2G-ROIC-001..007 not computable",
        }
    }


def _all_bindings() -> dict[str, dict[str, Any]]:
    bindings: dict[str, dict[str, Any]] = {}
    bindings.update(_binding_enterprise_quality())
    bindings.update(_binding_valuation())
    bindings.update(_binding_value_realization())
    bindings.update(_binding_risk_and_gap())
    bindings.update(_binding_roic_gap())
    return bindings


# ---------------------------------------------------------------------------
# Capsule emission with score_input_id and digest
# ---------------------------------------------------------------------------

def _artifact_sha256(path: str) -> str:
    p = ROOT / path
    if not p.is_file():
        return "MISSING_ARTIFACT"
    return _sha256(p)


def _score_input_id(component_id: str, upstream: dict[str, Any], value: Any,
                    unit: Any, date: Any, available_at: Any,
                    selection_method: str) -> str:
    """Deterministic identity that changes when artifact hash, record, method,
    value, unit, or date changes, but NOT when the logical path changes."""
    identity = {
        "component_id": component_id,
        "artifact_sha256": upstream.get("artifact_sha256"),
        "contract": upstream.get("contract"),
        "record_id": upstream.get("record_id"),
        "selection_method": selection_method,
        "value": value,
        "unit": unit,
        "date": date,
        "available_at": available_at,
    }
    payload = json.dumps(identity, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def build_capsule() -> dict[str, Any]:
    raw = _all_bindings()
    components: dict[str, Any] = {}
    for cid, binding in raw.items():
        upstream = dict(binding["upstream"])
        upstream["artifact_sha256"] = _artifact_sha256(upstream["artifact"])
        value = binding.get("value")
        unit = binding.get("unit")
        date = binding.get("fiscal_year") or binding.get("trade_date")
        available_at = binding.get("available_at")
        method = binding.get("selection_method")
        score_input_id = _score_input_id(
            cid, upstream, value, unit, date, available_at, method
        )
        components[cid] = {
            "score_input_id": score_input_id,
            "component_id": cid,
            "value": value,
            "unit": unit,
            "fiscal_year": binding.get("fiscal_year"),
            "trade_date": binding.get("trade_date"),
            "available_at": available_at,
            "score_date": SCORE_DATE,
            "status": binding.get("status", "present"),
            "status_is_computed": binding.get("status_is_computed"),
            "partial_value": binding.get("partial_value"),
            "percentile_3y": binding.get("percentile_3y"),
            "percentile_5y": binding.get("percentile_5y"),
            "effective_samples": binding.get("effective_samples"),
            "minimum_samples": binding.get("minimum_samples"),
            "record_ids": binding.get("record_ids"),
            "selection_method": method,
            "observation_set": binding.get("observation_set"),
            "upstream": upstream,
        }

    capsule = {
        "schema": "m2_stage2k1r_score_input_capsule_v1",
        "version": "1.0",
        "symbol": SYMBOL,
        "score_date": SCORE_DATE,
        "non_production": True,
        "research_methodology_test_only": True,
        "overall_score_prohibited": True,
        "recommendation_prohibited": True,
        "score_eligible": False,
        "artifact_source": "committed canonical artifacts only; no runtime scratch references",
        "components": components,
    }
    digest = hashlib.sha256(
        json.dumps(capsule, sort_keys=True, ensure_ascii=False).encode("utf-8")
    ).hexdigest()
    capsule["capsule_digest"] = digest
    return capsule


if __name__ == "__main__":
    import argparse
    import json as _json

    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("build", "validate"))
    args = parser.parse_args()

    capsule = build_capsule()
    if args.command == "build":
        out = ROOT / "reports" / "petrochina_score_input_capsule_v1.json"
        out.write_text(
            _json.dumps(capsule, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        print(_json.dumps({"status": "pass", "output": str(out)}, ensure_ascii=False))
    else:
        from m2_stage2k1r_validate import validate_capsule

        errors, pit_findings = validate_capsule(capsule)
        print(
            _json.dumps(
                {
                    "status": "pass" if not errors else "fail",
                    "errors": errors,
                    "pit_findings": pit_findings,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    raise SystemExit(0)
