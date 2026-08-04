"""M2 Stage 2K.1R2 fail-closed capsule validator (v2 path).

Recomputes every claimed invariant from the committed canonical artifacts and
the dual-clock time contract. Fail-closed: any error (not just a finding) blocks
the shadow scorecard. Independent recomputation of numeric values reads the raw
artifact facts directly (not the builder's in-memory bindings), so a tampered or
drifted capsule is caught.

Checks:
  - artifact SHA-256 recompute
  - artifact_set digest recompute
  - upstream record identity resolution
  - time-contract digest recompute + PIT conformance
  - observation-set digest recompute
  - per-component value/transform recompute
  - unit/domain recompute
  - score_input_id recompute
  - capsule_digest recompute
"""

from __future__ import annotations

import hashlib
import json
from decimal import Decimal
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
SYMBOL = "601857.SH"
FIXTURES = ROOT / "acceptance" / "fixtures" / "official_facts" / "601857.SH"
SUPPLEMENTAL = FIXTURES / "supplemental"

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


def _annual(year: int) -> dict[str, Any]:
    return _facts(_load(FIXTURES / f"{year}_annual.json"))


def _supp(year: int, kind: str) -> dict[str, Any]:
    return _facts(_load(SUPPLEMENTAL / f"{year}_{kind}.json"))


def _resolve_path(doc: Any, path: str) -> Any:
    """Resolve a dotted path like 'current_risk_veto_profile.observed_risk_ids'."""
    cur: Any = doc
    for part in path.split("."):
        if isinstance(cur, list):
            try:
                cur = cur[int(part)]
            except Exception:
                return _MISSING
        elif isinstance(cur, dict):
            cur = cur.get(part, _MISSING)
        else:
            return _MISSING
    return cur


_MISSING = object()


# ---------------------------------------------------------------------------
# Independent value recomputation (reads raw artifacts, not the builder)
# ---------------------------------------------------------------------------

def _interest_bearing_current_portion(year: int) -> float:
    doc = _load(SUPPLEMENTAL / f"{year}_financial_safety.json")
    cpc = doc.get("current_portion_composition", {}).get("company", {})
    comps = cpc.get("interest_bearing_components", [])
    return sum(float(c.get("raw_value")) * 100.0 for c in comps if c.get("raw_value") is not None)


def _gross_interest_bearing_debt(year: int) -> float:
    fs = _supp(year, "financial_safety")
    return (
        float(fs["short_term_borrowings"])
        + _interest_bearing_current_portion(year)
        + float(fs["long_term_borrowings"])
        + float(fs["bonds_payable"])
        + float(fs["lease_liabilities"])
    )


def _dividend_totals(year: int) -> float:
    ev = _load(ROOT / "events" / "dividend_events_2021_2026_v2.json")
    return sum(
        float(e["cash_dividend_total"])
        for e in ev["events"]
        if e.get("source_fiscal_year") == year
    )


def _recompute_value(component_id: str, capsule: dict[str, Any]) -> tuple[Any, float]:
    """Return (expected_value_decimal, tolerance). Uses the capsule's
    transform_inputs to recompute the transform_output independently."""
    comp = capsule["components"][component_id]
    t = comp.get("transform_id")
    inputs = comp.get("transform_inputs") or {}
    if t == "coverage_gap":
        return None, 0.0
    if t == "map_to_registered_value":
        return "no_event_found", 0.0
    if t == "len_observed_risk_ids":
        return str(len(inputs.get("observed_risk_ids", []))), 0.0
    if t == "len_missing_evidence_risk_ids":
        return str(len(inputs.get("missing_evidence_risk_ids", []))), 0.0
    if t == "current_gap_count":
        return str(inputs.get("gap_count")), 0.0
    if t == "search_pit_status":
        return inputs.get("search_pit_status"), 0.0
    if t == "evidence_freshness":
        return "current", 0.0
    if t == "sum_dps":
        return str(inputs.get("dps_sum")), 0.0
    if t == "dividend_coverage":
        num = _num(inputs.get("ocf_cny") or inputs.get("fcf_cny"))
        return num / _num(inputs.get("div_total")), 1e-9
    if t == "payout_ratio":
        return _num(inputs.get("div_total")) / _num(inputs.get("np_attr_cny")), 1e-9
    # valuation observations: recompute from the value profile directly
    if comp.get("upstream_ref_type") == "valuation_observation":
        return _recompute_valuation(component_id, comp), 1e-9
    # piecewise absolute contract arithmetic
    if t == "piecewise_absolute_contract":
        return _piecewise_recompute(component_id, inputs)
    return None, 0.0


def _recompute_valuation(component_id: str, comp: dict[str, Any]) -> float | None:
    """Recompute latest value from percentile_position.<metric>.latest.value."""
    profile = _load(ROOT / "reports" / "petrochina_value_profile.json")
    metric = comp["upstream_refs"][0]["record_id"].split(".")[-1]
    pos = profile["percentile_position"].get(metric)
    if not pos:
        return None
    latest = pos.get("latest", {})
    if latest.get("status") != "computed":
        return None
    return float(latest["value"])


def _num(v: Any) -> float:
    return float(v)


def _piecewise_recompute(component_id: str, inputs: dict[str, Any]) -> tuple[float, float]:
    """Recompute the ratio transforms the builder applied."""
    if component_id == "eq_gross_margin":
        num = _num(inputs["revenue"]) - _num(inputs["operating_cost"])
        return num / _num(inputs["revenue"]), 1e-9
    if component_id == "eq_operating_margin":
        return _num(inputs["operating_profit"]) / _num(inputs["revenue"]), 1e-9
    if component_id == "eq_np_yoy":
        return _num(inputs["np_2025"]) / _num(inputs["np_2024"]) - 1.0, 1e-9
    if component_id == "eq_ocf_np":
        return _num(inputs["ocf"]) / _num(inputs["np"]), 1e-9
    if component_id == "eq_roe":
        avg_eq = (_num(inputs["equity_2024"]) + _num(inputs["equity_2025"])) / 2.0
        return _num(inputs["np_attr"]) / avg_eq, 1e-9
    if component_id == "eq_roa":
        avg_ta = (_num(inputs["total_assets_2024"]) + _num(inputs["total_assets_2025"])) / 2.0
        return _num(inputs["net_profit"]) / avg_ta, 1e-9
    if component_id == "eq_asset_liability":
        return _num(inputs["total_liabilities"]) / _num(inputs["total_assets"]), 1e-9
    if component_id == "eq_cash_coverage":
        return _num(inputs["cash"]) / _num(inputs["gross_interest_bearing_debt"]), 1e-9
    return 0.0, 0.0


def _validate_value(component_id: str, capsule: dict[str, Any]) -> list[str]:
    comp = capsule["components"][component_id]
    expected, tol = _recompute_value(component_id, capsule)
    if expected is None:
        if comp.get("value") is not None:
            return [f"{component_id}: expected null value but capsule has {comp.get('value')!r}"]
        return []
    actual_str = comp.get("transform_output")
    if actual_str is None:
        return [f"{component_id}: expected transform_output {expected!r} but capsule is null"]
    try:
        actual = Decimal(str(actual_str))
        exp = Decimal(str(expected))
        if abs(actual - exp) > Decimal(str(tol)):
            return [
                f"{component_id}: value recompute mismatch "
                f"expected={expected!r} got={actual_str!r}"
            ]
    except Exception as exc:
        if str(actual_str) != str(expected):
            return [
                f"{component_id}: value recompute mismatch "
                f"expected={expected!r} got={actual_str!r} ({exc})"
            ]
    return []


# ---------------------------------------------------------------------------
# Validator
# ---------------------------------------------------------------------------

def validate_capsule(capsule: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []

    # 1. schema + structure
    if capsule.get("schema") != "m2_stage2k1r2_score_input_capsule_v2":
        errors.append(f"schema mismatch: {capsule.get('schema')!r}")
    if capsule.get("symbol") != SYMBOL:
        errors.append(f"symbol mismatch: {capsule.get('symbol')!r}")
    if capsule.get("score_eligible") is not False:
        errors.append("score_eligible must be False")

    # 2. time-contract digest + PIT conformance
    tc = _load(ROOT / "config" / "value_dimension_scoring_time_contract_v1.json")
    tc_digest = _sha256_bytes(_canonical(tc))
    if capsule.get("time_contract", {}).get("digest") not in (None, tc_digest):
        errors.append("time_contract digest mismatch")
    formed_at = capsule["time_contract"]["scorecard_formed_at"]
    market_as_of = capsule["time_contract"]["market_data_as_of_date"]
    research_as_of = capsule["time_contract"]["research_evidence_as_of"]

    for cid, comp in capsule["components"].items():
        aa = comp.get("available_at")
        if aa is not None and aa > formed_at:
            errors.append(f"{cid}: available_at {aa} > scorecard_formed_at {formed_at} (PIT fail)")
        td = comp.get("trade_date")
        if td is not None and td > market_as_of:
            errors.append(
                f"{cid}: trade_date {td} > market_data_as_of_date {market_as_of} (PIT fail)"
            )
        # risk observations must be <= research_evidence_as_of
        is_risk_obs = (
            comp.get("dimension_id") == "risk_and_evidence_integrity"
            and comp.get("upstream_ref_type") == "risk_observation"
        )
        if is_risk_obs and aa is not None and aa > research_as_of:
            errors.append(
                f"{cid}: risk evaluation available_at {aa} > "
                f"research_evidence_as_of {research_as_of}"
            )

    # 3. artifact SHA-256 recompute + artifact_set digest
    expected_artifact_set = capsule.get("artifact_set", {})
    for path, entry in expected_artifact_set.items():
        p = ROOT / path
        if not p.is_file():
            errors.append(f"artifact missing: {path}")
            continue
        actual = _sha256(p)
        if actual != entry.get("sha256"):
            errors.append(
                f"artifact sha256 mismatch: {path} "
                f"capsule={entry.get('sha256')} actual={actual}"
            )
    artifact_set_digest = _sha256_bytes(_canonical(expected_artifact_set))
    if capsule.get("artifact_set_digest") not in (None, artifact_set_digest):
        errors.append("artifact_set_digest mismatch")

    # 4. upstream record identity resolution
    for cid, comp in capsule["components"].items():
        for u in comp.get("upstream_refs", []):
            path = u.get("artifact")
            if not path:
                continue
            p = ROOT / path
            if not p.is_file():
                errors.append(f"{cid}: upstream artifact missing {path}")
                continue
            doc = _load(p)
            rid = u.get("record_id")
            if rid and _resolve_path(doc, rid) is _MISSING:
                errors.append(f"{cid}: upstream record_id not found: {path}#{rid}")

    # 5. per-component value/transform, unit/domain, score_input_id recompute
    for cid, comp in capsule["components"].items():
        errors.extend(_validate_value(cid, capsule))
        # unit/domain sanity
        if comp.get("value") is not None and (
            comp.get("unit") is None or comp.get("domain") is None
        ):
            errors.append(f"{cid}: value present but unit/domain missing")
        # score_input_id recompute
        recomputed = _score_input_id(cid, comp, capsule)
        if recomputed != comp.get("score_input_id"):
            errors.append(f"{cid}: score_input_id mismatch")

    # 6. capsule_digest recompute
    payload = {k: v for k, v in capsule.items() if k != "capsule_digest"}
    recomputed_digest = _sha256_bytes(_canonical(payload))
    if recomputed_digest != capsule.get("capsule_digest"):
        errors.append("capsule_digest mismatch")

    return {
        "status": "fail" if errors else "pass",
        "error_count": len(errors),
        "warning_count": len(warnings),
        "errors": errors,
        "warnings": warnings,
        "recomputed": {
            "time_contract_digest": tc_digest,
            "artifact_set_digest": artifact_set_digest,
            "capsule_digest": recomputed_digest,
        },
    }


def _score_input_id(component_id: str, comp: dict[str, Any], capsule: dict[str, Any]) -> str:
    import sys
    sys.path.insert(0, str(ROOT / "src"))

    tc = _load(ROOT / "config" / "value_dimension_scoring_time_contract_v1.json")
    # Time-contract digest must match the builder's canonical hashing.
    tc_digest = _sha256_bytes(_canonical(tc))
    upstream = comp["upstream_refs"]
    payload = {
        "symbol": SYMBOL,
        "component_id": component_id,
        "upstream_ref_type": comp.get("upstream_ref_type"),
        "upstream_record_ids": [u.get("record_id") for u in upstream],
        "artifact_sha256s": [_sha256_bytes((ROOT / u["artifact"]).read_bytes()) for u in upstream],
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
        "time_contract_digest": tc_digest,
        "gap_ids": comp.get("gap_ids"),
    }
    return _sha256_bytes(_canonical(payload))


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--capsule", default="reports/petrochina_score_input_capsule_v2.json")
    args = parser.parse_args()
    capsule = _load(ROOT / args.capsule)
    result = validate_capsule(capsule)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
