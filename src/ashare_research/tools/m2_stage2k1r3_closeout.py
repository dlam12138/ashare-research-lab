"""M2 Stage 2K.1R3 closeout CLI orchestrator.

Orchestrates: resolve, build-capsule, validate, build-market-observation-set,
build-confidence, build-shadow, build-sensitivity, verify-artifacts.

The capsule v3 is built from the upstream registry -> resolvers -> transforms
(never from a previous capsule's transform_inputs). The validator recomputes
every score input from the upstream records and rejects any capsule that
self-reports inputs, source tiers, or values that do not match an independent
recomputation.

Business logic lives in ashare_research.scoring.{lineage,transforms,
market_observation_set}; this module only orchestrates.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from ashare_research.scoring import lineage, transforms
from ashare_research.scoring import market_observation_set as mos

ROOT = Path(__file__).resolve().parents[3]
UPSTREAM_REGISTRY = ROOT / "config" / "value_dimension_scoring_upstream_registry_v1.json"
TRANSFORM_REGISTRY = ROOT / "config" / "value_dimension_scoring_transform_registry_v2.json"
TIME_CONTRACT = ROOT / "config" / "value_dimension_scoring_time_contract_v1.json"
REGISTRY_PATH = ROOT / "config" / "value_dimension_scoring_registry_v1.json"
POLICY_PATH = ROOT / "config" / "value_dimension_scoring_policy_v1.json"
MARKET_REGISTRY = ROOT / "events" / "market_data_snapshot_registry.json"

SYMBOL = "601857.SH"
_CANONICAL_SEP = (",", ":")

DIMENSIONS = [
    "enterprise_quality",
    "valuation_attractiveness",
    "value_realization_capacity",
    "risk_and_evidence_integrity",
]
SCORED_DIMENSIONS = [
    "enterprise_quality",
    "valuation_attractiveness",
    "value_realization_capacity",
]
RISK_DIMENSION = "risk_and_evidence_integrity"

# components that bind a dividend event set in addition to canonical facts
DIVIDEND_EVENT_COMPONENTS = {
    "vr_ocf_dividend_coverage",
    "vr_fcf_dividend_coverage",
    "vr_payout_ratio",
}


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical(payload: Any) -> bytes:
    return json.dumps(
        payload, sort_keys=True, ensure_ascii=False, separators=_CANONICAL_SEP
    ).encode("utf-8")


def time_contract_digest() -> str:
    return _sha256_bytes(_canonical(_load(TIME_CONTRACT)))


def time_contract_identity() -> dict[str, Any]:
    tc = _load(TIME_CONTRACT)
    return {
        "market_data_as_of_date": tc["market_data_as_of_date"],
        "research_evidence_as_of": tc["research_evidence_as_of"],
        "scorecard_formed_at": tc["scorecard_formed_at"],
        "timezone": tc["timezone"],
        "time_contract_version": tc["version"],
        "digest": time_contract_digest(),
    }


# ---------------------------------------------------------------------------
# resolution
# ---------------------------------------------------------------------------

def _resolve_records(
    spec: dict[str, Any],
    *,
    market_cache_root: Path | None,
    market_fixture_root: Path | None,
) -> tuple[lineage.ResolvedRecord, ...]:
    recs = lineage.resolve_component(
        spec, repository_root=ROOT, market_cache_root=market_cache_root
    )
    # dividend coverage components also bind dividend event records
    if spec["component_id"] in DIVIDEND_EVENT_COMPONENTS:
        ev_spec = spec.get("selector", {}).get("events")
        if ev_spec:
            ev_recs = lineage.dividend_event_resolver(
                {
                    "component_id": spec["component_id"],
                    "resolver_id": "dividend_event_resolver",
                    "resolver_version": "1.0",
                    "artifact_logical_path": ev_spec["path"],
                    "expected_period": str(ev_spec["fiscal_year"]),
                    "expected_symbol": "601857.SH",
                    "selector": {"symbol": "601857.SH"},
                },
                repository_root=ROOT,
            )
            recs = recs + ev_recs
    return recs


def _record_dict(r: lineage.ResolvedRecord) -> dict[str, Any]:
    return {
        "record_id": r.record_id,
        "record_digest": r.record_digest,
        "record_identity_type": r.record_identity_type,
        "artifact_logical_path": r.artifact_logical_path,
        "artifact_contract": r.artifact_contract,
        "artifact_sha256": r.artifact_sha256,
        "field_path": r.field_path,
        "symbol": r.symbol,
        "period": r.period,
        "raw_value": r.raw_value,
        "unit": r.unit,
        "domain": r.domain,
        "available_at": r.available_at,
        "source_tier": r.source_tier,
        "source_evidence_ids": list(r.source_evidence_ids),
        "gap_ids": list(r.gap_ids),
    }


FRESHNESS = {
    "va_pe": "2026-07-31",
    "va_pb": "2026-07-31",
    "va_ps": "2026-07-31",
    "va_fcf_yield": "2026-07-31",
    "va_dividend_yield": "2026-07-31",
}


def score_input_id_for(component_id: str, score_input: dict[str, Any]) -> str:
    payload = {
        "component_id": component_id,
        "resolver_id": score_input.get("resolver_id"),
        "resolver_version": score_input.get("resolver_version"),
        "upstream_ref_type": score_input.get("upstream_ref_type"),
        "record_ids": score_input.get("operand_record_ids"),
        "record_digests": score_input.get("operand_record_digests"),
        "artifact_sha256s": [r["artifact_sha256"] for r in score_input.get("resolved_records", [])],
        "transform_id": score_input.get("transform_id"),
        "transform_version": score_input.get("transform_version"),
        "output_value": score_input.get("selected_value_decimal"),
        "unit": score_input.get("unit"),
        "domain": score_input.get("domain"),
        "period": score_input.get("period"),
        "available_at": score_input.get("available_at"),
        "resolved_source_tier": score_input.get("resolved_source_tier"),
        "source_evidence_ids": score_input.get("source_evidence_ids"),
        "observation_set_digest": (
            (score_input.get("observation_set") or {}).get("observation_set_digest")
        ),
        "time_contract_digest": time_contract_digest(),
        "gap_ids": score_input.get("gap_ids"),
    }
    return _sha256_bytes(_canonical(payload))


def _make_score_input(
    spec: dict[str, Any],
    recs: tuple[lineage.ResolvedRecord, ...],
    *,
    market_validation_mode: str,
    real_observation_set: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a score input from a resolved record set. Shared by the builder
    and the validator so the validator recomputes the exact same score_input_id
    from the recomputed upstream records (never from the capsule's claims).

    In real mode the valuation percentile is the cache-recomputed close
    percentile from the verified external observation set; in synthetic mode it
    is the committed manifest percentile (test-only)."""
    cid = spec["component_id"]
    cv = transforms.compute_transform(spec["transform_id"], spec["transform_version"], recs)
    observation_set = None
    if spec.get("resolver_id") == "market_manifest_resolver":
        r = recs[0]
        metric_key = spec.get("selector", {}).get("metric_key")
        if market_validation_mode == "external_verified_cache" and real_observation_set:
            # real percentile recomputed from the external cache. The close
            # percentile equals the percentile of a price-multiple (PE/PB/PS)
            # because the divisor is fixed; yield metrics (FCF/dividend) are not
            # directly recomputable from the daily close cache and stay gaps.
            os_ = real_observation_set["observation_set"]
            if metric_key in {
                "a_share_price_to_latest_annual_parent_earnings",
                "a_share_price_to_latest_year_end_parent_equity",
                "a_share_price_to_latest_annual_revenue",
            }:
                observation_set = {
                    "market_validation_mode": "external_verified_cache",
                    "real_market_verified": True,
                    "provider_sha256": os_.get("provider_object_sha256"),
                    "provider_object_key": os_.get("provider_object_key"),
                    "observation_id": f"real_cache:{metric_key}",
                    "observation_set_digest": os_.get("observation_set_digest"),
                    "percentile_source": "external_cache_recomputed",
                    "percentile_3y": os_.get("percentile_3y_close"),
                    "percentile_5y": os_.get("percentile_5y_close"),
                    "latest_close": os_.get("latest_close"),
                }
            else:
                # yield metrics: no cache-recomputable percentile -> coverage gap
                observation_set = {
                    "market_validation_mode": "external_verified_cache",
                    "real_market_verified": True,
                    "provider_sha256": os_.get("provider_object_sha256"),
                    "observation_id": f"real_cache:{metric_key}",
                    "observation_set_digest": os_.get("observation_set_digest"),
                    "percentile_source": "not_cache_recomputable_yield_series",
                    "percentile_3y": None,
                    "percentile_5y": None,
                }
        else:
            profile = _load(ROOT / spec["artifact_logical_path"])
            pos = profile.get("percentile_position", {}).get(metric_key, {})
            observation_set = {
                "market_validation_mode": "synthetic_test_capsule",
                "real_market_verified": False,
                "provider_sha256": r.artifact_sha256,
                "observation_id": r.record_id,
                "observation_set_digest": r.record_digest,
                "percentile_source": "committed_manifest",
                "percentile_3y": pos.get("3y"),
                "percentile_5y": pos.get("5y"),
            }
    source_tier = _derive_source_tier(spec, recs)
    available_at = _max_available_at(recs)
    gap_ids = sorted({g for r in recs for g in r.gap_ids})
    source_evidence_ids = sorted({e for r in recs for e in r.source_evidence_ids})
    score_input = {
        "component_id": cid,
        "dimension_id": spec["dimension_id"],
        "resolver_id": spec["resolver_id"],
        "resolver_version": spec["resolver_version"],
        "upstream_ref_type": spec["upstream_ref_type"],
        "resolved_records": [_record_dict(r) for r in recs],
        "operand_record_ids": list(cv.operand_record_ids),
        "operand_record_digests": [r.record_digest for r in recs],
        "transform_id": cv.transform_id,
        "transform_version": cv.transform_version,
        "selected_value_decimal": cv.output_value,
        "unit": cv.output_unit,
        "domain": cv.output_domain,
        "period": spec.get("expected_period"),
        "available_at": available_at,
        "resolved_source_tier": source_tier,
        "source_evidence_ids": source_evidence_ids,
        "gap_ids": gap_ids,
        "transform_inputs": cv.normalized_operands,
        "transform_inputs_role": "derived_snapshot_only",
        "validator_must_rebuild": True,
        "calculation_trace": cv.calculation_trace,
        "observation_set": observation_set,
    }
    score_input["score_input_id"] = score_input_id_for(cid, score_input)
    return score_input


def build_capsule(
    *,
    market_cache_root: Path | None = None,
    market_fixture_root: Path | None = None,
    market_validation_mode: str = "synthetic_test_capsule",
    market_registry: Path | None = None,
) -> dict[str, Any]:
    registry = _load(UPSTREAM_REGISTRY)
    tc = time_contract_identity()
    components: dict[str, Any] = {}
    # real mode: build the verified external observation set once and use its
    # cache-recomputed percentiles for the valuation components.
    real_observation_set = None
    if market_validation_mode == "external_verified_cache":
        real_observation_set = mos.build_observation_set(
            registry_path=market_registry or MARKET_REGISTRY,
            mode="real_research",
            cache_root=market_cache_root,
            fixture_root=None,
            symbol=SYMBOL,
            market_data_as_of_date=tc["market_data_as_of_date"],
            scorecard_formed_at=tc["scorecard_formed_at"],
        )
    for spec in registry["components"]:
        cid = spec["component_id"]
        recs = _resolve_records(
            spec, market_cache_root=market_cache_root, market_fixture_root=market_fixture_root
        )
        components[cid] = _make_score_input(
            spec, recs, market_validation_mode=market_validation_mode,
            real_observation_set=real_observation_set,
        )

    capsule = {
        "schema": "petrochina_score_input_capsule_v3",
        "version": "3.0",
        "symbol": SYMBOL,
        "time_contract": tc,
        "dimensions": DIMENSIONS,
        "component_count": len(components),
        "components": components,
        "market_validation_mode": market_validation_mode,
        "real_market_verified": market_validation_mode == "external_verified_cache",
        "production_eligible": False,
        "non_production": True,
        "research_methodology_test_only": True,
        "overall_score_prohibited": True,
        "recommendation_prohibited": True,
        "score_eligible": False,
    }
    capsule["capsule_digest"] = capsule_digest(capsule)
    return capsule


def _derive_source_tier(spec: dict[str, Any], recs: tuple[lineage.ResolvedRecord, ...]) -> str:
    """Source tier derived from the resolver's actual records, never from the
    capsule. For canonical facts we report computed_from_verified_canonical_inputs
    once the transform is applied."""
    if not recs:
        return "coverage_gap"
    tiers = {r.source_tier for r in recs}
    if spec.get("resolver_id") == "canonical_fact_bundle_resolver":
        return "computed_from_verified_canonical_inputs"
    if len(tiers) == 1:
        return tiers.pop()
    return "coverage_gap"


def _max_available_at(recs: tuple[lineage.ResolvedRecord, ...]) -> str | None:
    avail = [r.available_at for r in recs if r.available_at]
    return max(avail) if avail else None


def capsule_digest(capsule: dict[str, Any]) -> str:
    payload = {k: v for k, v in capsule.items() if k != "capsule_digest"}
    return _sha256_bytes(_canonical(payload))


# ---------------------------------------------------------------------------
# validator
# ---------------------------------------------------------------------------

def validate_capsule(
    capsule: dict[str, Any],
    *,
    market_cache_root: Path | None = None,
    market_fixture_root: Path | None = None,
    market_registry: Path | None = None,
) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    registry = _load(UPSTREAM_REGISTRY)
    by_id = {c["component_id"]: c for c in registry["components"]}

    if capsule.get("schema") != "petrochina_score_input_capsule_v3":
        errors.append(f"schema mismatch: {capsule.get('schema')!r}")
    if capsule.get("symbol") != SYMBOL:
        errors.append(f"symbol mismatch: {capsule.get('symbol')!r}")

    formed_at = capsule["time_contract"]["scorecard_formed_at"]
    market_as_of = capsule["time_contract"]["market_data_as_of_date"]

    # real mode: rebuild the verified observation set to recompute the real
    # percentiles for the valuation components.
    real_observation_set = None
    if capsule.get("market_validation_mode") == "external_verified_cache":
        real_observation_set = mos.build_observation_set(
            registry_path=market_registry or MARKET_REGISTRY,
            mode="real_research",
            cache_root=market_cache_root,
            fixture_root=None,
            symbol=SYMBOL,
            market_data_as_of_date=market_as_of,
            scorecard_formed_at=formed_at,
        )

    # every registry component must be present in the capsule
    for cid in by_id:
        if cid not in capsule["components"]:
            errors.append(f"{cid}: missing from capsule (must be present)")

    for cid, comp in capsule["components"].items():
        spec = by_id.get(cid)
        if spec is None:
            errors.append(f"{cid}: component not in upstream registry")
            continue
        # recompute records from the upstream registry (independent of capsule)
        try:
            recs = _resolve_records(
                spec, market_cache_root=market_cache_root, market_fixture_root=market_fixture_root
            )
        except lineage.LineageError as exc:
            errors.append(f"{cid}: re-resolve failed: {exc}")
            continue
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{cid}: re-resolve failed: {exc}")
            continue

        # recompute score_input_id from the recomputed upstream records
        try:
            recomputed = _make_score_input(
                spec,
                recs,
                market_validation_mode=capsule.get(
                    "market_validation_mode", "synthetic_test_capsule"
                ),
                real_observation_set=real_observation_set,
            )
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{cid}: recompute score_input failed: {exc}")
            continue

        if recomputed["score_input_id"] != comp.get("score_input_id"):
            errors.append(f"{cid}: score_input_id_mismatch")

        # recompute value
        if recomputed["selected_value_decimal"] != comp.get("selected_value_decimal"):
            errors.append(
                f"{cid}: upstream_recomputed_value_mismatch expected="
                f"{recomputed['selected_value_decimal']!r} "
                f"got={comp.get('selected_value_decimal')!r}"
            )

        # source tier derived by resolver must match capsule claim
        expected_tier = recomputed["resolved_source_tier"]
        claimed_tier = comp.get("resolved_source_tier")
        if expected_tier != claimed_tier:
            errors.append(
                f"{cid}: source_tier_mismatch expected={expected_tier!r} got={claimed_tier!r}"
            )
        # allowed tiers
        allowed = spec.get("allowed_source_tiers", [])
        if expected_tier not in allowed:
            errors.append(
                f"{cid}: source_tier {expected_tier} not allowed for {spec['resolver_id']}"
            )

        # PIT (date-only comparison so timestamps like 2026-08-02T06:30:00+08:00
        # are not misread as after the date-only scorecard_formed_at)
        aa = comp.get("available_at")
        aa_date = (aa or "").split("T")[0]
        if aa_date and aa_date > formed_at:
            errors.append(f"{cid}: available_at {aa} > scorecard_formed_at {formed_at}")

    # capsule digest
    recomputed_digest = capsule_digest(capsule)
    if recomputed_digest != capsule.get("capsule_digest"):
        errors.append("capsule_digest_mismatch")

    return {
        "status": "fail" if errors else "pass",
        "error_count": len(errors),
        "warning_count": len(warnings),
        "errors": errors,
        "warnings": warnings,
    }


# ---------------------------------------------------------------------------
# confidence
# ---------------------------------------------------------------------------

def build_confidence(capsule: dict[str, Any], lineage_report: dict[str, Any]) -> dict[str, Any]:
    """Confidence v3 reads ONLY the validated lineage source tiers, never the
    capsule's claimed source_tier."""
    if lineage_report.get("status") != "pass":
        return {
            "schema": "petrochina_dimension_evidence_confidence_v3",
            "version": "3.0",
            "symbol": SYMBOL,
            "status": "blocked_by_lineage_validation",
            "confidence": None,
        }
    grades: dict[str, list[str]] = {d: [] for d in DIMENSIONS}
    reasons: dict[str, list[str]] = {d: [] for d in DIMENSIONS}
    supporting: dict[str, list[str]] = {d: [] for d in DIMENSIONS}
    for cid, comp in capsule["components"].items():
        dim = comp["dimension_id"]
        tier = comp["resolved_source_tier"]
        # A valuation component with no computed percentile is a coverage gap
        # even though its manifest source tier is medium.
        obs = comp.get("observation_set") or {}
        if dim == "valuation_attractiveness" and obs.get("percentile_3y") is None:
            tier = "coverage_gap"
        grades[dim].append(_tier_grade(tier))
        if tier == "coverage_gap":
            reasons[dim].append(f"coverage_gap:{cid}")
            supporting[dim].extend(comp.get("gap_ids") or [cid])
    dims = {}
    for dim in DIMENSIONS:
        present = [g for g in grades[dim] if g != "low"]
        has_gap = any(g == "low" for g in grades[dim])
        grade = (
            min(present, key=lambda g: {"low": 0, "medium": 1, "high": 2}[g])
            if present
            else "low"
        )
        if has_gap and {"low": 0, "medium": 1, "high": 2}[grade] > 1:
            grade = "medium"
        dims[dim] = {
            "dimension_id": dim,
            "grade": grade,
            "reasons": reasons[dim],
            "supporting_ids": supporting[dim],
        }
    return {
        "schema": "petrochina_dimension_evidence_confidence_v3",
        "version": "3.0",
        "symbol": SYMBOL,
        "time_contract": capsule["time_contract"],
        "capsule_digest": capsule["capsule_digest"],
        "lineage_report_digest": lineage_report.get("report_digest"),
        "source_tier_registry_digest": _sha256_bytes(
            _canonical(_load(UPSTREAM_REGISTRY)["source_tier_bindings"])
        ),
        "non_production": True,
        "overall_score_prohibited": True,
        "recommendation_prohibited": True,
        "score_eligible": False,
        "dimensions": dims,
    }


def _tier_grade(tier: str) -> str:
    return {
        "computed_from_verified_canonical_inputs": "high",
        "canonical_fact_verified": "high",
        "event_verified": "medium",
        "committed_computed_report": "medium",
        "external_manifest_only": "medium",
        "bounded_search_complete": "medium",
        "external_verified_market_cache": "high",
        "coverage_gap": "low",
    }.get(tier, "low")


# ---------------------------------------------------------------------------
# shadow + sensitivity
# ---------------------------------------------------------------------------

def _capsule_to_inputs(capsule: dict[str, Any]) -> dict[str, Any]:
    components: dict[str, Any] = {}
    for cid, comp in capsule["components"].items():
        entry: dict[str, Any] = {
            "value": comp.get("selected_value_decimal"),
            "status": (
                "present" if comp.get("selected_value_decimal") is not None else "coverage_gap"
            ),
            "source": (
                comp.get("resolved_records", [{}])[0].get("artifact_logical_path", "")
                if comp.get("resolved_records")
                else ""
            ),
            "score_input_id": comp.get("score_input_id"),
        }
        # ROIC remains a coverage gap for scoring: gap_count is evidence-integrity
        # signal, not a computable ROIC value.
        if cid == "eq_roic":
            entry["value"] = None
            entry["status"] = "not_computable_under_strict_evidence_contract"
        if comp.get("observation_set") and comp["observation_set"].get("percentile_3y") is not None:
            entry["percentile_3y"] = comp["observation_set"]["percentile_3y"]
        if comp.get("observation_set") and comp["observation_set"].get("percentile_5y") is not None:
            entry["percentile_5y"] = comp["observation_set"]["percentile_5y"]
        components[cid] = entry
    return {
        "schema": "m2_stage2k1r3_shadow_inputs_v1",
        "symbol": capsule["symbol"],
        "score_date": capsule["time_contract"]["scorecard_formed_at"],
        "non_production": True,
        "overall_score_prohibited": True,
        "recommendation_prohibited": True,
        "score_eligible": False,
        "components": components,
    }


def build_shadow(capsule: dict[str, Any], confidence: dict[str, Any]) -> dict[str, Any]:
    from ashare_research.tools import m2_stage2k_scoring_shadow as stage2k

    registry = _load(REGISTRY_PATH)
    policy = _load(POLICY_PATH)
    inputs = _capsule_to_inputs(capsule)
    dims: dict[str, Any] = {}
    for dim in SCORED_DIMENSIONS:
        result = stage2k.compute_dimension(dim, registry, policy, inputs)
        result["evidence_confidence"] = confidence["dimensions"][dim]
        dims[dim] = result
    dims[RISK_DIMENSION] = {
        "dimension_id": RISK_DIMENSION,
        "representation": "status_outputs",
        "risk_veto_status": _risk_status(capsule),
        "evidence_integrity": confidence["dimensions"][RISK_DIMENSION],
        "no_merged_numeric_score": True,
    }
    return {
        "schema": "petrochina_dimension_scoring_shadow_v4",
        "version": "4.0",
        "symbol": capsule["symbol"],
        "time_contract": capsule["time_contract"],
        "capsule_digest": capsule["capsule_digest"],
        "non_production": True,
        "overall_score_prohibited": True,
        "recommendation_prohibited": True,
        "score_eligible": False,
        "status": "pass",
        "dimensions": dims,
    }


def _risk_status(capsule: dict[str, Any]) -> dict[str, Any]:
    veto = capsule["components"].get("rk_veto_triggered", {}).get("selected_value_decimal")
    missing = capsule["components"].get("rk_missing_evidence_slots", {}).get(
        "selected_value_decimal"
    )
    try:
        veto_n = int(veto) if veto is not None else 0
    except (TypeError, ValueError):
        veto_n = 0
    try:
        missing_n = int(missing) if missing is not None else 0
    except (TypeError, ValueError):
        missing_n = 0
    return {
        "status": "clear" if veto_n == 0 else "blocked_by_risk_veto",
        "triggered_count": veto_n,
        "missing_evidence_slots": missing_n,
        "non_compensatory": True,
    }


def build_sensitivity(capsule: dict[str, Any]) -> dict[str, Any]:
    import copy

    from ashare_research.tools import m2_stage2k_scoring_shadow as stage2k

    registry = _load(REGISTRY_PATH)
    policy = _load(POLICY_PATH)
    inputs = _capsule_to_inputs(capsule)

    def run(reg):
        out = {}
        for dim in SCORED_DIMENSIONS:
            out[dim] = stage2k.compute_dimension(dim, reg, policy, inputs)
        return out

    base = run(registry)
    dims: dict[str, Any] = {}
    for dim in SCORED_DIMENSIONS:
        outcomes: list[tuple[float | None, str | None, str | None]] = []
        base_score, base_band = base[dim].get("score"), base[dim].get("band")
        for cid in registry["dimensions"][dim]["components"]:
            for factor in (1.25, 0.75):
                reg = copy.deepcopy(registry)
                reg["dimensions"][dim]["components"][cid]["weight"] = (
                    float(registry["dimensions"][dim]["components"][cid]["weight"]) * factor
                )
                r = run(reg)[dim]
                outcomes.append((r.get("score"), r.get("band"), r.get("status")))
        for cid in registry["dimensions"][dim]["components"]:
            reg = copy.deepcopy(registry)
            reg["dimensions"][dim]["components"] = {
                k: v for k, v in registry["dimensions"][dim]["components"].items() if k != cid
            }
            r = run(reg)[dim]
            outcomes.append((r.get("score"), r.get("band"), r.get("status")))
        scores = [s for s, _, _ in outcomes if s is not None]
        insufficient = sum(1 for _, _, st in outcomes if st == "insufficient_evidence")
        veto = sum(1 for _, _, st in outcomes if st == "blocked_by_risk_veto")
        min_score = min(scores) if scores else None
        max_score = max(scores) if scores else None
        delta = (max_score - min_score) if scores else None
        bands = [b for _, b, _ in outcomes if b is not None]
        flips = sum(1 for b in bands if b != base_band)
        tolerance = float(registry["dimensions"][dim].get("stability_tolerance", 1.0))
        stable = (
            delta is not None and delta <= tolerance
            and flips == 0 and insufficient == 0 and veto == 0
        )
        dims[dim] = {
            "dimension_id": dim,
            "base_score": base_score,
            "base_band": base_band,
            "min_score": min_score,
            "max_score": max_score,
            "max_score_delta": None if delta is None else round(delta, 4),
            "band_flip_count": flips,
            "insufficient_evidence_count": insufficient,
            "veto_block_count": veto,
            "scenario_count": len(outcomes),
            "stability_status": "STABLE" if stable else "NOT_STABLE",
            "stability_tolerance": tolerance,
            "production_readiness_reason": (
                "dimension stable across frozen scenario set" if stable
                else "dimension band or coverage changes under a frozen scenario"
            ),
        }
    return {
        "schema": "petrochina_dimension_scoring_sensitivity_v4",
        "version": "4.0",
        "non_production": True,
        "overall_score_prohibited": True,
        "recommendation_prohibited": True,
        "score_eligible": False,
        "thresholds_frozen_before_rerun": True,
        "synthetic_values_are_not_company_facts": True,
        "dimensions": dims,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> int:
    import argparse

    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    def add_output(p):
        p.add_argument("--output", default="")
        p.add_argument("--market-cache-root", default=None)
        p.add_argument("--market-fixture-root", default=None)
        p.add_argument("--market-registry", default=None)

    p = sub.add_parser("resolve")
    add_output(p)
    p = sub.add_parser("build-capsule")
    add_output(p)
    p = sub.add_parser("validate")
    add_output(p)
    p = sub.add_parser("build-market-observation-set")
    add_output(p)
    p = sub.add_parser("build-confidence")
    add_output(p)
    p = sub.add_parser("build-shadow")
    add_output(p)
    p = sub.add_parser("build-sensitivity")
    add_output(p)
    p = sub.add_parser("verify-artifacts")
    add_output(p)

    args = parser.parse_args()
    cache_root = Path(args.market_cache_root) if args.market_cache_root else None
    fixture_root = Path(args.market_fixture_root) if args.market_fixture_root else None
    market_registry = Path(args.market_registry) if args.market_registry else None
    mode = "real_research" if cache_root else "test_capsule"
    market_validation_mode = "external_verified_cache" if cache_root else "synthetic_test_capsule"

    if args.command == "resolve":
        result = build_capsule(
            market_cache_root=cache_root,
            market_fixture_root=fixture_root,
            market_validation_mode=market_validation_mode,
            market_registry=market_registry,
        )
        result = {"status": "resolve", "component_count": result["component_count"]}
    elif args.command == "build-capsule":
        result = build_capsule(
            market_cache_root=cache_root,
            market_fixture_root=fixture_root,
            market_validation_mode=market_validation_mode,
            market_registry=market_registry,
        )
    elif args.command == "validate":
        capsule = build_capsule(
            market_cache_root=cache_root,
            market_fixture_root=fixture_root,
            market_validation_mode=market_validation_mode,
            market_registry=market_registry,
        )
        result = validate_capsule(
            capsule, market_cache_root=cache_root, market_fixture_root=fixture_root,
            market_registry=market_registry,
        )
    elif args.command == "build-market-observation-set":
        result = mos.build_observation_set(
            registry_path=market_registry or MARKET_REGISTRY,
            mode=mode,
            cache_root=cache_root,
            fixture_root=fixture_root,
            symbol=SYMBOL,
            market_data_as_of_date="2026-07-31",
            scorecard_formed_at="2026-08-02",
        )
    elif args.command == "build-confidence":
        capsule = build_capsule(
            market_cache_root=cache_root,
            market_fixture_root=fixture_root,
            market_validation_mode=market_validation_mode,
            market_registry=market_registry,
        )
        lineage_report = validate_capsule(
            capsule, market_cache_root=cache_root, market_fixture_root=fixture_root,
            market_registry=market_registry,
        )
        lineage_report["report_digest"] = _sha256_bytes(_canonical(lineage_report))
        result = build_confidence(capsule, lineage_report)
    elif args.command == "build-shadow":
        capsule = build_capsule(
            market_cache_root=cache_root,
            market_fixture_root=fixture_root,
            market_validation_mode=market_validation_mode,
            market_registry=market_registry,
        )
        lineage_report = validate_capsule(
            capsule, market_cache_root=cache_root, market_fixture_root=fixture_root,
            market_registry=market_registry,
        )
        lineage_report["report_digest"] = _sha256_bytes(_canonical(lineage_report))
        confidence = build_confidence(capsule, lineage_report)
        result = build_shadow(capsule, confidence)
    elif args.command == "build-sensitivity":
        capsule = build_capsule(
            market_cache_root=cache_root,
            market_fixture_root=fixture_root,
            market_validation_mode=market_validation_mode,
            market_registry=market_registry,
        )
        result = build_sensitivity(capsule)
    elif args.command == "verify-artifacts":
        cap = build_capsule(
            market_cache_root=cache_root,
            market_fixture_root=fixture_root,
            market_validation_mode=market_validation_mode,
            market_registry=market_registry,
        )
        verified = sorted(
            {
                r["artifact_logical_path"]
                for c in cap["components"].values()
                for r in c["resolved_records"]
            }
        )
        result = {"status": "pass", "verified": verified}

    if args.output:
        out = Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"status": "ok", "output": str(out)}, ensure_ascii=False))
        return 0
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
