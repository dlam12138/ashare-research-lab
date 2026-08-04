"""M2 Stage 2K.1R4A capsule builder.

Builds the capsule v3 from the upstream registry -> resolvers -> transforms
(never from a previous capsule's transform_inputs). Provides the shared helpers
(time contract, canonical hashing, record resolution, score-input construction)
used by the validator, confidence, shadow, and sensitivity modules.

Business logic lives in ashare_research.scoring.{lineage,transforms,
market_observation_set}; this module only builds the capsule and its inputs.
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
        "artifact_digest_algorithm": r.artifact_digest_algorithm,
        "artifact_byte_size": r.artifact_byte_size,
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
        "artifact_digests": [
            {
                "artifact_logical_path": r["artifact_logical_path"],
                "algorithm": r["artifact_digest_algorithm"],
                "sha256": r["artifact_sha256"],
                "byte_size": r["artifact_byte_size"],
            }
            for r in score_input.get("resolved_records", [])
        ],
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
        "schema": "petrochina_score_input_capsule_v4",
        "version": "4.0",
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
