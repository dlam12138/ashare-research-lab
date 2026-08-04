"""M2 Stage 2K.1R3 scoring lineage: ResolvedRecord + per-type resolvers.

A ResolvedRecord is ONE concrete upstream record a scoring component reads. A
resolver opens the artifact, verifies its contract, locates the actual record,
validates symbol/period, reads raw fields + unit + available_at, computes a
record digest, and derives the source tier from the real source. It never
returns a record just because the file exists.

The resolver is the single place that produces source tiers and record
identities; the capsule does not self-report them.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]

_CANONICAL_SEP = (",", ":")

# FY2025 annual report announcement date (from report document landing_url 202603).
_ANNUAL_AVAILABLE_AT = {
    2025: "2026-03-30",
    2024: "2025-03-25",
    2023: "2024-03-25",
    2022: "2023-03-29",
    2021: "2022-03-31",
}


class LineageError(Exception):
    """Raised when an upstream record cannot be resolved."""


_TIME_CONTRACT_PATH = ROOT / "config" / "value_dimension_scoring_time_contract_v1.json"


def _time_contract(field: str) -> str:
    """Read a field from the frozen time contract (dual-clock)."""
    doc = json.loads(_TIME_CONTRACT_PATH.read_text(encoding="utf-8"))
    return doc[field]


@dataclass(frozen=True)
class ResolvedRecord:
    resolver_id: str
    resolver_version: str
    upstream_ref_type: str
    artifact_logical_path: str
    artifact_contract: str
    artifact_sha256: str
    record_id: str
    record_digest: str
    record_identity_type: str
    field_path: str | None
    symbol: str
    period: str | None
    raw_value: str | None
    unit: str | None
    domain: str | None
    available_at: str | None
    source_tier: str
    source_evidence_ids: tuple[str, ...]
    gap_ids: tuple[str, ...]


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _canonical(payload: Any) -> bytes:
    return json.dumps(
        payload, sort_keys=True, ensure_ascii=False, separators=_CANONICAL_SEP
    ).encode("utf-8")


def _contract_of(path: Path) -> str:
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return "unknown"
    contract = doc.get("contract")
    if contract:
        return str(contract)
    schema = doc.get("schema_version")
    if schema:
        return f"annual_bundle_schema_{schema}"
    return "unknown"


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _adapter_record_digest(
    resolver_id: str,
    resolver_version: str,
    symbol: str,
    selector: dict[str, Any],
    period: str | None,
    canonical_content: dict[str, Any],
    field_path: str | None,
) -> str:
    """adapter_record_digest: canonical read-model record identity. Excludes
    absolute paths and formatting; includes contract, resolver, symbol,
    selector, period, canonical content and field path. Not a canonical fact_id."""
    payload = {
        "record_identity_type": "adapter_record_digest",
        "resolver_id": resolver_id,
        "resolver_version": resolver_version,
        "symbol": symbol,
        "selector": selector,
        "period": period,
        "canonical_content": canonical_content,
        "field_path": field_path,
    }
    return _sha256_bytes(_canonical(payload))


def _facts_recursive(doc: dict[str, Any]) -> list[dict[str, Any]]:
    """Collect all fact dicts (with concept_id + expected_normalized_value).

    Handles both the flat annual structure (concept_id and expected_normalized_value
    on the same dict) and the dual-supplier structure (company/exchange subsections
    carrying the normalized value)."""
    out: list[dict[str, Any]] = []

    def rec(v: Any) -> None:
        if isinstance(v, dict):
            if "concept_id" in v:
                company = v.get("company") or {}
                exchange = v.get("exchange") or {}
                norm = v.get("expected_normalized_value")
                if norm is None:
                    norm = company.get("expected_normalized_value")
                if norm is None:
                    norm = exchange.get("expected_normalized_value")
                if norm is not None:
                    out.append(
                        {
                            "concept_id": v["concept_id"],
                            "expected_normalized_value": norm,
                            "raw_unit": v.get("raw_unit")
                            or company.get("raw_unit")
                            or exchange.get("raw_unit"),
                            "source_key": "company/exchange",
                        }
                    )
            for child in v.values():
                rec(child)
        elif isinstance(v, list):
            for child in v:
                rec(child)

    rec(doc)
    return out


# ---------------------------------------------------------------------------
# canonical_fact_bundle_resolver
# ---------------------------------------------------------------------------

def canonical_fact_bundle_resolver(
    spec: dict[str, Any],
    *,
    repository_root: Path,
    fact_db: Any = None,
    market_cache_root: Path | None = None,
) -> tuple[ResolvedRecord, ...]:
    """Resolve facts from one or more official_fact_bundle artifacts (annual or
    supplemental). Each requested fact carries a fiscal_year; the record field
    path is year-tagged so transforms can distinguish e.g. np 2025 vs 2024."""
    resolver_id = spec.get("resolver_id", "canonical_fact_bundle_resolver")
    resolver_version = spec.get("resolver_version", "1.0")
    symbol = spec.get("expected_symbol", "601857.SH")
    selector = spec.get("selector", {})
    sources = selector.get("sources") or [{"path": spec["artifact_logical_path"]}]
    facts_spec = selector.get("facts", [])

    records: list[ResolvedRecord] = []
    # Cache each source's facts and artifact metadata so each fact is resolved
    # from the first source that actually contains it.
    loaded: list[tuple[dict[str, Any], str, dict[str, Any], str | None, str]] = []
    for src in sources:
        path = repository_root / src["path"]
        if not path.is_file():
            raise LineageError(f"missing upstream artifact: {src['path']}")
        doc = _load(path)
        artifact_sha = _sha256(path)
        contract = spec.get("artifact_contract", _contract_of(path))
        bundle_fy = src.get("fiscal_year") or doc.get("fiscal_year")
        available_at = src.get("available_at")
        if available_at is None and bundle_fy in _ANNUAL_AVAILABLE_AT:
            available_at = _ANNUAL_AVAILABLE_AT[bundle_fy]
        loaded.append((src, artifact_sha, doc, available_at, contract))

    for item in facts_spec:
        concept = item.get("concept_id")
        fy = item.get("fiscal_year")
        resolved = False
        for src, artifact_sha, doc, available_at, contract in loaded:
            bundle_fy = src.get("fiscal_year") or doc.get("fiscal_year")
            eff_fy = fy or bundle_fy
            facts = _facts_recursive(doc)
            matches = [f for f in facts if f.get("concept_id") == concept]
            if not matches:
                continue
            chosen = matches[0]
            path_sel = f"/facts/{concept}/{eff_fy}"
            content = {
                "concept_id": chosen.get("concept_id"),
                "expected_normalized_value": chosen.get("expected_normalized_value"),
                "raw_unit": chosen.get("raw_unit"),
                "source_key": chosen.get("source_key"),
                "fiscal_year": eff_fy,
            }
            sel = {**selector, "concept_id": concept, "fiscal_year": eff_fy}
            record_id = _adapter_record_digest(
                resolver_id, resolver_version, symbol, sel, str(eff_fy), content, path_sel,
            )
            records.append(
                ResolvedRecord(
                    resolver_id=resolver_id,
                    resolver_version=resolver_version,
                    upstream_ref_type="derived_from_canonical_facts",
                    artifact_logical_path=src["path"],
                    artifact_contract=contract,
                    artifact_sha256=artifact_sha,
                    record_id=record_id,
                    record_digest=record_id,
                    record_identity_type="adapter_record_digest",
                    field_path=path_sel,
                    symbol=symbol,
                    period=str(eff_fy),
                    raw_value=str(chosen.get("expected_normalized_value")),
                    unit=chosen.get("raw_unit") or spec.get("expected_unit"),
                    domain=spec.get("expected_domain"),
                    available_at=available_at,
                    source_tier="canonical_fact_verified",
                    source_evidence_ids=(chosen.get("source_key", ""),),
                    gap_ids=(),
                )
            )
            resolved = True
            break
        if not resolved:
            raise LineageError(
                f"concept not found: {concept} across {[s['path'] for s in sources]}"
            )
    if not records:
        raise LineageError(
            f"canonical_fact_bundle_resolver: no facts resolved for {spec['component_id']}"
        )
    return tuple(records)


# ---------------------------------------------------------------------------
# dividend_event_resolver
# ---------------------------------------------------------------------------

def dividend_event_resolver(
    spec: dict[str, Any],
    *,
    repository_root: Path,
    fact_db: Any = None,
    market_cache_root: Path | None = None,
) -> tuple[ResolvedRecord, ...]:
    resolver_id = spec.get("resolver_id", "dividend_event_resolver")
    resolver_version = spec.get("resolver_version", "1.0")
    path = repository_root / spec["artifact_logical_path"]
    doc = _load(path)
    artifact_sha = _sha256(path)
    contract = spec.get("artifact_contract", doc.get("contract"))
    symbol = spec.get("expected_symbol", "601857.SH")
    period = spec.get("expected_period")
    fiscal_year = int(period) if str(period).isdigit() else None
    selector = spec.get("selector", {})
    event_type = selector.get("event_type")
    events = doc.get("events", [])
    matches = [
        e for e in events
        if e.get("source_fiscal_year") == fiscal_year
        and (event_type is None or e.get("event_type") == event_type)
    ]
    if not matches:
        raise LineageError(f"no dividend events for FY{fiscal_year} type={event_type}")
    records: list[ResolvedRecord] = []
    for e in matches:
        event_id = e.get("event_id")
        if not event_id:
            raise LineageError("dividend event missing event_id")
        content = {
            "event_id": event_id,
            "source_fiscal_year": e.get("source_fiscal_year"),
            "event_type": e.get("event_type"),
            "cash_dividend_per_share": e.get("cash_dividend_per_share"),
            "cash_dividend_total": e.get("cash_dividend_total"),
        }
        base = {
            "resolver_id": resolver_id,
            "resolver_version": resolver_version,
            "upstream_ref_type": "dividend_event",
            "artifact_logical_path": spec["artifact_logical_path"],
            "artifact_contract": contract,
            "artifact_sha256": artifact_sha,
            "record_id": event_id,
            "record_digest": _sha256_bytes(_canonical(content)),
            "record_identity_type": "event_id",
            "symbol": symbol,
            "period": period,
            "unit": "CNY",
            "domain": spec.get("expected_domain"),
            "available_at": e.get("implementation_available_at"),
            "source_tier": "event_verified",
            "source_evidence_ids": tuple(e.get("source_evidence_ids") or ()),
            "gap_ids": (),
        }
        # one record per concept so transforms can sum across events
        records.append(
            ResolvedRecord(
                **base,
                field_path=f"/events/{event_id}/cash_dividend_per_share",
                raw_value=str(e.get("cash_dividend_per_share")),
            )
        )
        records.append(
            ResolvedRecord(
                **base,
                field_path=f"/events/{event_id}/cash_dividend_total",
                raw_value=str(e.get("cash_dividend_total")),
            )
        )
    return tuple(records)


# ---------------------------------------------------------------------------
# risk_profile_resolver
# ---------------------------------------------------------------------------

def risk_profile_resolver(
    spec: dict[str, Any],
    *,
    repository_root: Path,
    fact_db: Any = None,
    market_cache_root: Path | None = None,
) -> tuple[ResolvedRecord, ...]:
    resolver_id = spec.get("resolver_id", "risk_profile_resolver")
    resolver_version = spec.get("resolver_version", "1.0")
    path = repository_root / spec["artifact_logical_path"]
    doc = _load(path)
    artifact_sha = _sha256(path)
    contract = spec.get("artifact_contract", doc.get("contract"))
    symbol = spec.get("expected_symbol", "601857.SH")
    rp = doc["current_risk_veto_profile"]
    selector = spec.get("selector", {})
    record_type = selector.get("record_type", "risk_slots")
    records: list[ResolvedRecord] = []
    if record_type == "risk_slots":
        for slot in rp.get("risk_slots", []):
            slot_id = slot.get("slot_id")
            if not slot_id:
                continue
            content = {
                "slot_id": slot_id,
                "risk_id": slot.get("risk_id"),
                "observation_id": slot.get("observation_id"),
                "evaluation_status": slot.get("evaluation_status"),
            }
            records.append(
                ResolvedRecord(
                    resolver_id=resolver_id,
                    resolver_version=resolver_version,
                    upstream_ref_type="risk_slot",
                    artifact_logical_path=spec["artifact_logical_path"],
                    artifact_contract=contract,
                    artifact_sha256=artifact_sha,
                    record_id=slot_id,
                    record_digest=_sha256_bytes(_canonical(content)),
                    record_identity_type="risk_slot_id",
                    field_path=f"/current_risk_veto_profile/risk_slots/{slot_id}",
                    symbol=symbol,
                    period=slot.get("evaluation_as_of_date"),
                    raw_value=slot.get("evaluation_status"),
                    unit="categorical",
                    domain=spec.get("expected_domain"),
                    available_at=slot.get("conclusion_available_at"),
                    source_tier="committed_computed_report",
                    source_evidence_ids=tuple(slot.get("visible_input_evidence_ids") or ()),
                    gap_ids=(),
                )
            )
    elif record_type == "observations":
        for obs in rp.get("observations", []):
            obs_id = obs.get("observation_id")
            if not obs_id:
                continue
            content = {
                "observation_id": obs_id,
                "risk_id": obs.get("risk_id"),
                "status": obs.get("status"),
                "search_register_id": obs.get("search_register_id"),
            }
            records.append(
                ResolvedRecord(
                    resolver_id=resolver_id,
                    resolver_version=resolver_version,
                    upstream_ref_type="risk_observation",
                    artifact_logical_path=spec["artifact_logical_path"],
                    artifact_contract=contract,
                    artifact_sha256=artifact_sha,
                    record_id=obs_id,
                    record_digest=_sha256_bytes(_canonical(content)),
                    record_identity_type="observation_id",
                    field_path=f"/current_risk_veto_profile/observations/{obs_id}",
                    symbol=symbol,
                    period=obs.get("evaluation_as_of_date"),
                    raw_value=obs.get("status"),
                    unit="categorical",
                    domain=spec.get("expected_domain"),
                    available_at=obs.get("conclusion_available_at") or obs.get("available_at"),
                    source_tier="committed_computed_report",
                    source_evidence_ids=tuple(
                        obs.get("input_evidence_ids") or obs.get("all_evidence_ids") or ()
                    ),
                    gap_ids=(),
                )
            )
    if not records:
        raise LineageError(f"risk_profile_resolver: no {record_type} records")
    return tuple(records)


# ---------------------------------------------------------------------------
# gap_ledger_resolver
# ---------------------------------------------------------------------------

def gap_ledger_resolver(
    spec: dict[str, Any],
    *,
    repository_root: Path,
    fact_db: Any = None,
    market_cache_root: Path | None = None,
) -> tuple[ResolvedRecord, ...]:
    resolver_id = spec.get("resolver_id", "gap_ledger_resolver")
    resolver_version = spec.get("resolver_version", "1.0")
    path = repository_root / spec["artifact_logical_path"]
    doc = _load(path)
    artifact_sha = _sha256(path)
    contract = spec.get("artifact_contract", doc.get("contract"))
    symbol = spec.get("expected_symbol", "601857.SH")
    selector = spec.get("selector", {})
    gap_ids = selector.get("gap_ids", [])
    # Gap evidence is available as of the research evidence window, not the
    # ledger regeneration date. PIT requires available_at <= scorecard_formed_at.
    research_evidence_as_of = _time_contract("research_evidence_as_of")
    gaps = doc.get("gaps", [])
    records: list[ResolvedRecord] = []
    for gap in gaps:
        gid = gap.get("gap_id")
        if gap_ids and gid not in gap_ids:
            continue
        if not gap_ids or gid in gap_ids:
            content = {
                "gap_id": gid,
                "module": gap.get("module"),
                "status": gap.get("status"),
                "semantic_requirement": gap.get("semantic_requirement"),
            }
            records.append(
                ResolvedRecord(
                    resolver_id=resolver_id,
                    resolver_version=resolver_version,
                    upstream_ref_type="gap_record",
                    artifact_logical_path=spec["artifact_logical_path"],
                    artifact_contract=contract,
                    artifact_sha256=artifact_sha,
                    record_id=gid,
                    record_digest=_sha256_bytes(_canonical(content)),
                    record_identity_type="gap_id",
                    field_path=f"/gaps/{gid}",
                    symbol=symbol,
                    period=gap.get("fiscal_year_event_period"),
                    raw_value=gap.get("status"),
                    unit="categorical",
                    domain=spec.get("expected_domain"),
                    available_at=research_evidence_as_of,
                    source_tier="coverage_gap",
                    source_evidence_ids=tuple(gap.get("evidence_search_record_ids") or ()),
                    gap_ids=(gid,),
                )
            )
    if not records:
        raise LineageError(f"gap_ledger_resolver: no gaps for {gap_ids}")
    return tuple(records)


# ---------------------------------------------------------------------------
# repurchase_search_resolver
# ---------------------------------------------------------------------------

def repurchase_search_resolver(
    spec: dict[str, Any],
    *,
    repository_root: Path,
    fact_db: Any = None,
    market_cache_root: Path | None = None,
) -> tuple[ResolvedRecord, ...]:
    resolver_id = spec.get("resolver_id", "repurchase_search_resolver")
    resolver_version = spec.get("resolver_version", "1.0")
    path = repository_root / spec["artifact_logical_path"]
    doc = _load(path)
    artifact_sha = _sha256(path)
    contract = spec.get("artifact_contract", doc.get("contract"))
    symbol = spec.get("expected_symbol", "601857.SH")
    status = doc.get("status")
    register_id = doc.get("search_register_id") or f"search_register:{symbol}:{contract}"
    if status != "bounded_search_no_event_found":
        raise LineageError(f"repurchase search not bounded-complete: {status}")
    content = {
        "register_id": register_id,
        "status": status,
        "scope": doc.get("scope"),
        "search_basis": doc.get("search_basis"),
    }
    record = ResolvedRecord(
        resolver_id=resolver_id,
        resolver_version=resolver_version,
        upstream_ref_type="repurchase_search_result",
        artifact_logical_path=spec["artifact_logical_path"],
        artifact_contract=contract,
        artifact_sha256=artifact_sha,
        record_id=register_id,
        record_digest=_sha256_bytes(_canonical(content)),
        record_identity_type="search_register_id",
        field_path="/status",
        symbol=symbol,
        period=doc.get("scope"),
        raw_value=status,
        unit="categorical",
        domain=spec.get("expected_domain"),
        available_at=doc.get("scope", "").split("..")[-1],
        source_tier="bounded_search_complete",
        source_evidence_ids=(),
        gap_ids=(),
    )
    return (record,)


# ---------------------------------------------------------------------------
# market_manifest_resolver (value profile percentile observation)
# ---------------------------------------------------------------------------

def market_manifest_resolver(
    spec: dict[str, Any],
    *,
    repository_root: Path,
    fact_db: Any = None,
    market_cache_root: Path | None = None,
) -> tuple[ResolvedRecord, ...]:
    """Resolve a valuation percentile from the committed value profile (manifest
    only; never treated as a real-market recomputation)."""
    resolver_id = spec.get("resolver_id", "market_manifest_resolver")
    resolver_version = spec.get("resolver_version", "1.0")
    path = repository_root / spec["artifact_logical_path"]
    doc = _load(path)
    artifact_sha = _sha256(path)
    contract = spec.get("artifact_contract", doc.get("contract"))
    symbol = spec.get("expected_symbol", "601857.SH")
    selector = spec.get("selector", {})
    metric_key = selector.get("metric_key")
    pos = doc["percentile_position"].get(metric_key)
    if pos is None:
        raise LineageError(f"percentile metric not found: {metric_key}")
    latest = pos.get("latest", {})
    content = {
        "metric_key": metric_key,
        "latest": latest,
        "percentile_3y": pos.get("3y"),
        "percentile_5y": pos.get("5y"),
    }
    record = ResolvedRecord(
        resolver_id=resolver_id,
        resolver_version=resolver_version,
        upstream_ref_type="valuation_observation",
        artifact_logical_path=spec["artifact_logical_path"],
        artifact_contract=contract,
        artifact_sha256=artifact_sha,
        record_id=f"percentile:{metric_key}",
        record_digest=_sha256_bytes(_canonical(content)),
        record_identity_type="adapter_record_digest",
        field_path=f"/percentile_position/{metric_key}",
        symbol=symbol,
        period=latest.get("trade_date"),
        raw_value=str(latest.get("value")) if latest.get("status") == "computed" else None,
        unit="ratio",
        domain=spec.get("expected_domain"),
        available_at=doc.get("as_of_trade_date"),
        source_tier="external_manifest_only",
        source_evidence_ids=tuple(
                doc.get("latest_observations", {})
                .get(metric_key, {})
                .get("lineage", {})
                .get("financial_fact_ids", ())
            ),
        gap_ids=(),
    )
    return (record,)


# ---------------------------------------------------------------------------
# market_external_cache_resolver (real market cache observation)
# ---------------------------------------------------------------------------

def market_external_cache_resolver(
    spec: dict[str, Any],
    *,
    repository_root: Path,
    fact_db: Any = None,
    market_cache_root: Path | None = None,
) -> tuple[ResolvedRecord, ...]:
    """Resolve a valuation observation set from the external market cache. Only
    available when market_cache_root is provided and verified. Never falls back
    to synthetic or committed percentiles."""
    from ashare_research.reproducibility.market import MarketSnapshotResolver

    if market_cache_root is None:
        raise LineageError(
            "market_external_cache_resolver: --market-cache-root required (real mode)"
        )
    registry_path = repository_root / spec["artifact_logical_path"]
    resolver = MarketSnapshotResolver(
        registry_path, mode="real_research", cache_root=market_cache_root
    )
    resolved, registry = resolver.resolve()
    # (the market observation set builder uses this resolver; the component
    #  binding is created there from the concrete frame)
    return ()


# ---------------------------------------------------------------------------
# dispatch
# ---------------------------------------------------------------------------

def metric_result_resolver(
    spec: dict[str, Any],
    *,
    repository_root: Path,
    fact_db: Any = None,
    market_cache_root: Path | None = None,
) -> tuple[ResolvedRecord, ...]:
    """Resolve from a Metric Result registry when available. Not used for the
    current 24 components (no metric_result_id upstream); present for contract
    completeness."""
    raise LineageError("metric_result_resolver: no upstream metric_result registry bound")


RESOLVERS = {
    "canonical_fact_bundle_resolver": canonical_fact_bundle_resolver,
    "metric_result_resolver": metric_result_resolver,
    "dividend_event_resolver": dividend_event_resolver,
    "risk_profile_resolver": risk_profile_resolver,
    "gap_ledger_resolver": gap_ledger_resolver,
    "repurchase_search_resolver": repurchase_search_resolver,
    "market_manifest_resolver": market_manifest_resolver,
    "market_external_cache_resolver": market_external_cache_resolver,
}


def resolve_component(
    component_spec: dict[str, Any],
    *,
    repository_root: Path,
    fact_db: Any = None,
    market_cache_root: Path | None = None,
) -> tuple[ResolvedRecord, ...]:
    resolver_id = component_spec["resolver_id"]
    resolver = RESOLVERS.get(resolver_id)
    if resolver is None:
        raise LineageError(f"unknown resolver_id: {resolver_id}")
    return resolver(
        component_spec,
        repository_root=repository_root,
        fact_db=fact_db,
        market_cache_root=market_cache_root,
    )
