"""M2 Stage 2K.1R2 upstream resolver.

Maps every score-input capsule component to its deterministic upstream source:
artifact logical path, contract, artifact SHA-256, record identity, source
evidence IDs, and the reference type. Reading ONLY committed canonical artifacts
and the dual-clock time contract. Emits a resolution report that is the
lineage contract for the capsule's artifact_set.

The resolver is the single place that declares WHICH committed artifact a
component reads, so the validator and the shadow engine bind to the same
upstream identity.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]

# Canonical upstream source per component (artifact path -> record intent).
# The capsule builder reads exactly these; the resolver verifies accessibility
# and reports the contract + sha256 for each.
def _entry(
    artifact: str, record: str, available_at: str | None, *, gap: bool = False
) -> dict[str, Any]:
    return {"artifact": artifact, "record": record, "available_at": available_at, "gap": gap}


UPSTREAM_MAP: dict[str, dict[str, Any]] = {
    # --- enterprise quality (derived from canonical facts) ---
    "eq_gross_margin": _entry(
        "acceptance/fixtures/official_facts/601857.SH/2025_annual.json",
        "revenue, operating_cost", "2026-03-30"),
    "eq_operating_margin": _entry(
        "acceptance/fixtures/official_facts/601857.SH/2025_annual.json",
        "revenue, operating_profit", "2026-03-30"),
    "eq_np_yoy": _entry(
        "acceptance/fixtures/official_facts/601857.SH/2025_annual.json",
        "net_profit_attributable_to_parent (2025 vs 2024)", "2026-03-30"),
    "eq_ocf_np": _entry(
        "acceptance/fixtures/official_facts/601857.SH/2025_annual.json",
        "operating_cash_flow / net_profit_attributable_to_parent", "2026-03-30"),
    "eq_roe": _entry(
        "acceptance/fixtures/official_facts/601857.SH/supplemental/2025_roe_roa_denominators.json",
        "equity_attributable_to_parent (2024,2025)", "2026-03-30"),
    "eq_roa": _entry(
        "acceptance/fixtures/official_facts/601857.SH/supplemental/2025_net_profit.json",
        "net_profit, total_assets (2024,2025)", "2026-03-30"),
    "eq_asset_liability": _entry(
        "acceptance/fixtures/official_facts/601857.SH/supplemental/2025_financial_safety.json",
        "total_liabilities / total_assets", "2026-03-30"),
    "eq_cash_coverage": _entry(
        "acceptance/fixtures/official_facts/601857.SH/supplemental/2025_financial_safety.json",
        "cash / gross_interest_bearing_debt", "2026-03-30"),
    "eq_roic": _entry("reports/m2_explicit_gap_ledger.json", "M2G-ROIC-001..007", None, gap=True),
    # --- valuation (value profile percentile observations) ---
    "va_pe": _entry(
        "reports/petrochina_value_profile.json",
        "percentile_position.a_share_price_to_latest_annual_parent_earnings", "2026-07-31"),
    "va_pb": _entry(
        "reports/petrochina_value_profile.json",
        "percentile_position.a_share_price_to_latest_year_end_parent_equity", "2026-07-31"),
    "va_ps": _entry(
        "reports/petrochina_value_profile.json",
        "percentile_position.a_share_price_to_latest_annual_revenue", "2026-07-31"),
    "va_fcf_yield": _entry(
        "reports/petrochina_value_profile.json",
        "percentile_position.latest_annual_fcf_proxy_yield", "2026-07-31"),
    "va_dividend_yield": _entry(
        "reports/petrochina_value_profile.json",
        "percentile_position.trailing_12m_announced_dividend_yield", "2026-07-31", gap=True),
    # --- value realization (dividend events + repurchase scan) ---
    "vr_ocf_dividend_coverage": _entry(
        "events/dividend_events_2021_2026_v2.json", "cash_dividend_total (FY2025)", "2026-03-30"),
    "vr_fcf_dividend_coverage": _entry(
        "events/dividend_events_2021_2026_v2.json", "cash_dividend_total (FY2025)", "2026-03-30"),
    "vr_payout_ratio": _entry(
        "events/dividend_events_2021_2026_v2.json",
        "cash_dividend_total / net_profit_attributable_to_parent", "2026-03-30"),
    "vr_dps": _entry(
        "events/dividend_events_2021_2026_v2.json",
        "cash_dividend_per_share (FY2025)", "2026-03-30"),
    "vr_repurchase": _entry(
        "events/repurchase_event_scan_2021_2026.json",
        "bounded_search_no_event_found", "2026-06-30"),
    # --- risk / evidence integrity (value profile risk profile + gap ledger) ---
    "rk_veto_triggered": _entry(
        "reports/petrochina_value_profile.json",
        "current_risk_veto_profile.observed_risk_ids", "2026-08-02"),
    "rk_missing_evidence_slots": _entry(
        "reports/petrochina_value_profile.json",
        "current_risk_veto_profile.missing_evidence_risk_ids", "2026-08-02"),
    "rk_gap_count": _entry(
        "reports/m2_explicit_gap_ledger.json", "count_contract.current_gap_count", "2026-08-02"),
    "rk_pit_integrity": _entry(
        "reports/petrochina_value_profile.json",
        "current_risk_veto_profile.search_pit_status", "2026-08-02"),
    "rk_evidence_freshness": _entry(
        "reports/petrochina_value_profile.json",
        "current_risk_veto_profile.as_of_date", "2026-08-02"),
}


def _sha256(path: Path) -> str:
    import hashlib
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _contract_of(path: str) -> str:
    try:
        doc = json.loads((ROOT / path).read_text(encoding="utf-8"))
    except Exception:
        return "unknown"
    contract = doc.get("contract")
    if contract:
        return str(contract)
    schema = doc.get("schema_version")
    if schema:
        return f"annual_bundle_schema_{schema}"
    return "unknown"


def resolve() -> dict[str, Any]:
    resolutions: dict[str, Any] = {}
    for cid, spec in UPSTREAM_MAP.items():
        path = spec["artifact"]
        p = ROOT / path
        entry = {
            "component_id": cid,
            "artifact": path,
            "contract": _contract_of(path),
            "sha256": _sha256(p) if p.is_file() else "MISSING_ARTIFACT",
            "record": spec["record"],
            "available_at": spec["available_at"],
            "gap": spec.get("gap", False),
            "resolved": p.is_file(),
        }
        resolutions[cid] = entry

    missing = [k for k, v in resolutions.items() if not v["resolved"]]
    return {
        "schema": "m2_stage2k1r2_upstream_resolution_v1",
        "version": "1.0",
        "symbol": "601857.SH",
        "component_count": len(resolutions),
        "resolutions": resolutions,
        "missing_artifact_count": len(missing),
        "missing_components": missing,
        "status": "pass" if not missing else "fail",
    }


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("resolve",))
    parser.add_argument(
        "--output", default="reports/petrochina_score_input_upstream_resolution_v1.json"
    )
    args = parser.parse_args()
    result = resolve()
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "output": str(out)}, ensure_ascii=False))
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
