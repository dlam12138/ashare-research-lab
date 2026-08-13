"""Stage 2H.1R PetroChina PIT/supersession/evidence-lineage vertical slice."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from ashare_research.reproducibility.artifacts import (
    compare_artifact_runs,
    finalize_artifacts,
    sha256_file,
    verify_artifacts,
    write_json,
)
from ashare_research.reproducibility.market import MarketSnapshotResolver
from ashare_research.risk_veto.contracts import (
    CODE_VERSION,
    EVENT_CONTRACT,
    METHODOLOGY_VERSION,
    NORMALIZATION_CONTRACT,
    OBSERVATION_CONTRACT,
    RISK_IDS,
    RISK_UNIVERSE_CONTRACT,
    SEARCH_CONTRACT,
    STATUS_VOCABULARY,
    TRIGGER_RULES,
    _get_path,
    _transform_normalized_value,
    canonical_hash,
    evaluate_risk_universe_as_of,
    normalization_lineage_hash,
    stable_id,
    validate_contracts,
    validate_normalization_record,
    validate_search_register_chain,
)
from ashare_research.tools.stage2g_reproducibility import (
    verify_clean_clone as verify_stage2g_clean_clone,
)
from ashare_research.tools.stage2g_reproducibility import (
    verify_contracts as verify_stage2g_contracts,
)

ROOT = Path(__file__).resolve().parents[3]
EVIDENCE_PATH = ROOT / "events" / "petrochina_risk_source_evidence_v1.json"
REGISTRY_PATH = ROOT / "events" / "petrochina_risk_evidence_registry_v2.json"
SEARCH_PATH = ROOT / "events" / "petrochina_bounded_search_register_v2.json"
EVENT_INPUT_PATH = ROOT / "events" / "petrochina_risk_event_inputs_v2.json"
NORMALIZATION_PATH = ROOT / "events" / "petrochina_risk_evidence_normalization_v1.json"


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _iso_max(values: list[str]) -> str:
    return max(values, key=lambda value: value.replace("Z", "+00:00"))


def _source_for_role(
    evidence_by_id: dict[str, dict[str, Any]], evidence_ids: list[str], spec: dict[str, Any]
) -> dict[str, Any]:
    role = spec["source_role"]
    candidates = [evidence_by_id[item] for item in evidence_ids]
    if role == "issuer":
        candidates = [item for item in candidates if item["source_type"] == "issuer_official"]
    elif role == "exchange":
        candidates = [item for item in candidates if item["source_type"] == "exchange_official"]
    elif role == "issuer_or_exchange":
        candidates.sort(key=lambda item: item["source_type"] != "issuer_official")
    else:
        raise ValueError(f"unsupported normalization source role: {role}")
    for candidate in candidates:
        try:
            _get_path(candidate, spec["source_field_path"])
        except ValueError:
            continue
        return candidate
    raise ValueError(f"no {role} evidence contains {spec['source_field_path']} for {evidence_ids}")


def _normalization_record(
    *,
    normalization_id: str,
    risk_id: str,
    semantic_key: str,
    source: dict[str, Any],
    spec: dict[str, Any],
) -> dict[str, Any]:
    raw = _get_path(source, spec["source_field_path"])
    record: dict[str, Any] = {
        "contract": NORMALIZATION_CONTRACT,
        "normalization_id": normalization_id,
        "risk_id": risk_id,
        "event_semantic_key": semantic_key,
        "target_field": spec["target_field"],
        "source_evidence_id": source["source_evidence_id"],
        "source_field_path": spec["source_field_path"],
        "raw_value": raw,
        "raw_unit": spec["raw_unit"],
        "normalized_value": raw,
        "normalized_unit": spec["normalized_unit"],
        "transform": spec["transform"],
        "denominator_fact_ids": [],
        "denominator_evidence_ids": [],
        "rounding_policy": "exact_float_v1",
        "formula_version": spec["formula_version"],
        "verification_status": "verified",
        "warnings": [],
        "available_at": source["available_at"],
        "code_version": CODE_VERSION,
    }
    if "denominator_field_path" in spec:
        record["denominator_field_path"] = spec["denominator_field_path"]
        record["denominator_evidence_ids"] = [source["source_evidence_id"]]
        record["denominator_fact_ids"] = [
            stable_id(
                "fact",
                {
                    "evidence_id": source["source_evidence_id"],
                    "field_path": spec["denominator_field_path"],
                },
            )
        ]
    record["normalized_value"] = _transform_normalized_value(record, source)
    return record


def _expanded_norm_ids(specs: list[dict[str, Any]], group: dict[str, Any]) -> list[str]:
    ids: list[str] = []
    for spec in specs:
        bundle = group["normalization_ids"][0]
        ids.append(f"{bundle}::{spec['target_field']}")
    return ids


def build_normalization_records(
    evidence: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Materialize field-level normalization records from the reviewed spec ledger."""

    evidence = evidence or _load(EVIDENCE_PATH)["entries"]
    grouped = _load(EVENT_INPUT_PATH)
    spec_ledger = _load(NORMALIZATION_PATH)
    specs_by_key = {
        (item["risk_id"], item["event_type"]): item["fields"]
        for item in spec_ledger["normalization_specs"]
    }
    evidence_by_id = {item["source_evidence_id"]: item for item in evidence}
    records: list[dict[str, Any]] = []
    groups: list[dict[str, Any]] = []
    for annual in grouped["annuals"]:
        groups.extend(
            {**group, "evidence_ids": annual["evidence_ids"]} for group in annual["event_groups"]
        )
    groups.extend(
        {**group, "risk_id": "material_error_restatement"} for group in grouped["restatements"]
    )
    for group in groups:
        specs = specs_by_key[(group["risk_id"], group["event_type"])]
        for spec in specs:
            source = _source_for_role(evidence_by_id, group["evidence_ids"], spec)
            record = _normalization_record(
                normalization_id=f"{group['normalization_ids'][0]}::{spec['target_field']}",
                risk_id=group["risk_id"],
                semantic_key=group["semantic_key"],
                source=source,
                spec=spec,
            )
            validate_normalization_record(record)
            records.append(record)
    return records


def _event(
    *,
    risk_id: str,
    event_type: str,
    semantic_key: str,
    event_date: str,
    available_at: str,
    period: str,
    input_evidence_ids: list[str],
    supplemental_evidence_ids: list[str],
    input_source_types: list[str],
    supplemental_source_types: list[str],
    classification: str,
    inputs: dict[str, Any],
    normalization_ids: list[str],
    input_lineage_hash: str,
    status: str = "not_observed_within_bounded_evidence",
    missing_reasons: list[str] | None = None,
    warnings: list[str] | None = None,
    supersedes: str | None = None,
) -> dict[str, Any]:
    values = {
        "symbol": "601857.SH",
        "risk_id": risk_id,
        "semantic_key": semantic_key,
        "event_type": event_type,
        "event_date": event_date,
        "available_at": available_at,
        "period": period,
        "input_evidence_ids": input_evidence_ids,
        "supplemental_evidence_ids": supplemental_evidence_ids,
        "all_evidence_ids": sorted(set(input_evidence_ids) | set(supplemental_evidence_ids)),
        "normalization_ids": normalization_ids,
        "input_lineage_hash": input_lineage_hash,
        "classification": classification,
        "trigger_version": TRIGGER_RULES[risk_id]["version"],
        "inputs": inputs,
        "status": status,
        "supersedes": supersedes,
    }
    return {
        "contract": EVENT_CONTRACT,
        "event_id": stable_id("risk_event", values),
        **values,
        "input_source_types": input_source_types,
        "supplemental_source_types": supplemental_source_types,
        "extraction_method": "formal_structured_rule_v2_from_normalized_evidence",
        "missing_reasons": missing_reasons or [],
        "warnings": warnings or [],
        "code_version": CODE_VERSION,
        "score_eligible": False,
    }


def _event_inputs(
    group: dict[str, Any], normalizations: list[dict[str, Any]]
) -> tuple[list[str], dict[str, Any], str]:
    bundle = group["normalization_ids"][0]
    ids = [
        item["normalization_id"]
        for item in normalizations
        if item["normalization_id"].startswith(f"{bundle}::")
    ]
    selected = sorted(
        (item for item in normalizations if item["normalization_id"] in ids),
        key=lambda item: item["target_field"],
    )
    return (
        ids,
        {item["target_field"]: item["normalized_value"] for item in selected},
        normalization_lineage_hash(selected),
    )


def _event_evidence_split(
    group_evidence_ids: list[str],
    normalization_ids: list[str],
    normalization_by_id: dict[str, dict[str, Any]],
) -> tuple[list[str], list[str]]:
    """Derive calculation inputs from norms; retain the rest as supplemental."""

    input_ids = sorted(
        {
            item
            for normalization_id in normalization_ids
            for item in (
                [normalization_by_id[normalization_id]["source_evidence_id"]]
                + normalization_by_id[normalization_id]["denominator_evidence_ids"]
            )
        }
    )
    supplemental_ids = sorted(set(group_evidence_ids) - set(input_ids))
    return input_ids, supplemental_ids


def build_event_records(
    evidence: list[dict[str, Any]] | None = None,
    normalizations: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Build v3 event records with deterministic and supplemental evidence split."""

    evidence = evidence or _load(EVIDENCE_PATH)["entries"]
    normalizations = normalizations or build_normalization_records(evidence)
    inputs = _load(EVENT_INPUT_PATH)
    evidence_by_id = {item["source_evidence_id"]: item for item in evidence}
    norm_by_id = {item["normalization_id"]: item for item in normalizations}
    records: list[dict[str, Any]] = []
    annual_event_types = {
        "modified_audit_opinion": "annual_audit_opinion",
        "going_concern_material_uncertainty": "annual_going_concern_review",
        "controlling_shareholder_pledge_risk": "annual_controller_pledge_disclosure",
        "material_related_party_transaction_risk": "annual_related_party_transaction_review",
        "controlling_shareholder_fund_occupation_or_related_guarantee": (
            "annual_fund_occupation_and_guarantee_review"
        ),
        "repeated_equity_financing_or_material_dilution": (
            "annual_equity_financing_and_share_change_review"
        ),
    }
    for annual in inputs["annuals"]:
        for group in annual["event_groups"]:
            group = {**group, "evidence_ids": annual["evidence_ids"]}
            ids, values, lineage = _event_inputs(group, normalizations)
            input_evidence_ids, supplemental_evidence_ids = _event_evidence_split(
                group["evidence_ids"], ids, norm_by_id
            )
            input_source_types = sorted(
                {evidence_by_id[item]["source_type"] for item in input_evidence_ids}
            )
            supplemental_source_types = sorted(
                {evidence_by_id[item]["source_type"] for item in supplemental_evidence_ids}
            )
            available_at = _iso_max(
                [evidence_by_id[item]["available_at"] for item in group["evidence_ids"]]
                + [norm_by_id[item]["available_at"] for item in ids]
            )
            risk_id = group["risk_id"]
            if risk_id == "modified_audit_opinion":
                classification = values["opinion_type"]
                warnings = ["key audit matters are separate from opinion modification"]
            elif risk_id == "going_concern_material_uncertainty":
                classification = (
                    "explicit_material_uncertainty"
                    if values["explicit_material_uncertainty"]
                    else "no_explicit_material_uncertainty_observed"
                )
                warnings = ["bounded annual-report scope; no permanent absence claim"]
            elif risk_id == "controlling_shareholder_pledge_risk":
                classification = "direct_controller_pledge_not_observed"
                warnings = [
                    "exchangeable-bond trust-account pledge is retained as raw exposure, "
                    "not direct controller pledge"
                ]
            elif risk_id == "material_related_party_transaction_risk":
                classification = "ordinary_operating_related_party_activity"
                warnings = [
                    "ordinary related-party transactions are not abuse without an explicit trigger"
                ]
            elif risk_id == "controlling_shareholder_fund_occupation_or_related_guarantee":
                classification = (
                    "no_official_non_operating_occupation_or_illegal_guarantee_observed"
                )
                warnings = [
                    "disclosed related-party balance is not itself an occupation classification"
                ]
            else:
                classification = (
                    "proposed_or_authorized_only"
                    if values["proposed_financing"]
                    else "no_completed_equity_financing_observed"
                )
                warnings = ["proposal or authorization is not realized dilution"]
            records.append(
                _event(
                    risk_id=risk_id,
                    event_type=annual_event_types[risk_id],
                    semantic_key=group["semantic_key"],
                    event_date=annual["event_date"],
                    available_at=available_at,
                    period=annual["period"],
                input_evidence_ids=input_evidence_ids,
                supplemental_evidence_ids=supplemental_evidence_ids,
                input_source_types=input_source_types,
                supplemental_source_types=supplemental_source_types,
                    classification=classification,
                    inputs=values,
                    normalization_ids=ids,
                    input_lineage_hash=lineage,
                    warnings=warnings,
                )
            )
    for restatement in inputs["restatements"]:
        ids, values, lineage = _event_inputs(restatement, normalizations)
        source = evidence_by_id[restatement["evidence_ids"][0]]
        input_evidence_ids, supplemental_evidence_ids = _event_evidence_split(
            restatement["evidence_ids"], ids, norm_by_id
        )
        records.append(
            _event(
                risk_id="material_error_restatement",
                event_type=restatement["event_type"],
                semantic_key=restatement["semantic_key"],
                event_date=restatement["event_date"],
                available_at=source["available_at"],
                period=restatement["period"],
                input_evidence_ids=input_evidence_ids,
                supplemental_evidence_ids=supplemental_evidence_ids,
                input_source_types=[source["source_type"]],
                supplemental_source_types=[],
                classification=values["restatement_classification"],
                inputs=values,
                normalization_ids=ids,
                input_lineage_hash=lineage,
                warnings=[
                    "ordinary accounting-policy, standard-change and common-control recasts "
                    "are not error risk"
                ],
            )
        )
    gap = inputs["regulatory_search_gap"]
    search = next(
        item
        for item in _load(SEARCH_PATH)["entries"]
        if item["search_register_id"] == gap["search_register_id"]
    )
    records.append(
        _event(
            risk_id="formal_regulatory_investigation_or_major_discipline",
            event_type="bounded_regulatory_search",
            semantic_key="bounded_regulatory_search:2021-2026",
            event_date=gap["event_date"],
            available_at=search["available_at"],
            period=gap["period"],
            input_evidence_ids=[],
            supplemental_evidence_ids=[],
            input_source_types=[],
            supplemental_source_types=[],
            classification="not_fully_retrieved",
            inputs={},
            normalization_ids=[],
            input_lineage_hash=canonical_hash([]),
            status="missing_evidence",
            missing_reasons=gap["missing_reasons"],
            warnings=gap["warnings"],
        )
    )
    return records


def _input_ledgers() -> tuple[
    list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]
]:
    evidence = _load(EVIDENCE_PATH)["entries"]
    searches = _load(SEARCH_PATH)["entries"]
    normalizations = build_normalization_records(evidence)
    events = build_event_records(evidence, normalizations)
    validate_contracts(
        evidence=evidence, events=events, search_registers=searches, normalizations=normalizations
    )
    return evidence, events, searches, normalizations


def verify_official_cache(cache_root: Path | str) -> dict[str, Any]:
    """Verify every retrieved evidence ID against the path-independent registry."""

    if cache_root is None:
        raise FileNotFoundError(
            "missing_external_research_input: --official-cache-root is required"
        )
    evidence, events, searches, normalizations = _input_ledgers()
    resolved, registry = MarketSnapshotResolver(
        REGISTRY_PATH, mode="real_research", cache_root=cache_root
    ).resolve()
    providers = registry["providers"]
    provider_by_id: dict[str, dict[str, Any]] = {}
    resolved_by_name = {record["logical_name"]: path for path, record in resolved}
    for provider in providers:
        aliases = provider.get("evidence_ids")
        if not isinstance(aliases, list) or not aliases:
            raise ValueError(
                f"registry provider has no evidence mapping: {provider['logical_name']}"
            )
        for evidence_id in aliases:
            if evidence_id in provider_by_id:
                raise ValueError(f"evidence mapped to multiple registry providers: {evidence_id}")
            provider_by_id[evidence_id] = provider
    expected_ids = {
        item["source_evidence_id"] for item in evidence if item["status"] == "retrieved"
    }
    if set(provider_by_id) != expected_ids:
        raise ValueError(
            "registry/evidence mapping mismatch: "
            f"expected={sorted(expected_ids)} actual={sorted(provider_by_id)}"
        )
    mismatches: list[str] = []
    for item in evidence:
        if item["status"] != "retrieved":
            continue
        provider = provider_by_id[item["source_evidence_id"]]
        checks = {
            "logical_cache_object_key": provider["object_key"] == item["logical_cache_object_key"],
            "sha256": provider["sha256"] == item["content_sha256"],
            "byte_size": provider["byte_size"] == item["byte_size"],
            "resolved": provider["logical_name"] in resolved_by_name,
        }
        if not all(checks.values()):
            mismatches.append(
                f"{item['source_evidence_id']}:"
                f"{','.join(key for key, ok in checks.items() if not ok)}"
            )
    if mismatches:
        raise ValueError(f"evidence registry verification failed: {mismatches}")
    return {
        "status": "pass",
        "mode": "real_research",
        "registry_contract": registry["contract"],
        "registry_provider_count": len(providers),
        "evidence_count": len(evidence),
        "verified_evidence_count": len(expected_ids),
        "unique_content_object_count": len(resolved),
        "evidence_registry_mapping_status": "complete",
        "event_count": len(events),
        "normalization_count": len(normalizations),
        "search_register_count": len(searches),
        "network_used": False,
        "default_db_mutated": False,
    }


def verify_contracts() -> dict[str, Any]:
    stage2g = verify_stage2g_contracts()
    evidence, events, searches, normalizations = _input_ledgers()
    registry = _load(REGISTRY_PATH)
    MarketSnapshotResolver.validate_registry_contract(registry)
    validate_search_register_chain(
        searches, research_cutoff=_load(SEARCH_PATH).get("research_cutoff")
    )
    return {
        "status": "pass_with_explicit_gaps"
        if any(not item["completeness"] for item in searches)
        else "pass",
        "methodology_version": METHODOLOGY_VERSION,
        "status_vocabulary": STATUS_VOCABULARY,
        "stage2g_contract_status": stage2g["status"],
        "risk_contract": validate_contracts(
            evidence=evidence,
            events=events,
            search_registers=searches,
            normalizations=normalizations,
        ),
        "official_registry": {
            "contract": registry["contract"],
            "provider_count": len(registry["providers"]),
            "evidence_alias_mapping": "complete",
            "path_independent": True,
        },
        "official_cache_required_for_formal": True,
        "score_eligible": False,
        "network_used": False,
    }


def _write_formal_run(
    root: Path,
    run_id: str,
    as_of_date: str,
    cache_status: dict[str, Any],
    evidence: list[dict[str, Any]],
    events: list[dict[str, Any]],
    searches: list[dict[str, Any]],
    normalizations: list[dict[str, Any]],
) -> dict[str, Any]:
    risk_universe = evaluate_risk_universe_as_of(
        symbol="601857.SH",
        as_of_date=as_of_date,
        events=events,
        search_registers=searches,
        evidence=evidence,
        normalizations=normalizations,
    )
    observations = risk_universe["observations"]
    root.mkdir(parents=True)
    write_json(
        root / "source_evidence.json", {"contract": "risk_evidence_ledger_v1", "entries": evidence}
    )
    write_json(root / "risk_event_input_grouping.json", _load(EVENT_INPUT_PATH))
    write_json(
        root / "risk_evidence_normalization.json",
        {"contract": NORMALIZATION_CONTRACT, "entries": normalizations},
    )
    write_json(root / "risk_events.json", {"contract": EVENT_CONTRACT, "events": events})
    write_json(
        root / "bounded_search_register.json",
        {"contract": "bounded_search_register_ledger_v2", "entries": searches},
    )
    write_json(
        root / "risk_veto_observations.json",
        {
            "contract": OBSERVATION_CONTRACT,
            "universe_contract": RISK_UNIVERSE_CONTRACT,
            "observations": observations,
            "slots": risk_universe["slots"],
            "risk_universe_evaluation_id": risk_universe["deterministic_id"],
        },
    )
    gap_count = sum(item["status"] == "missing_evidence" for item in observations)
    missing_slot_count = risk_universe["missing_slot_count"]
    summary = {
        "contract": "petrochina_risk_veto_vertical_slice_v3",
        "symbol": "601857.SH",
        "as_of_date": as_of_date,
        "methodology_version": METHODOLOGY_VERSION,
        "code_version": CODE_VERSION,
        "observation_count": len(observations),
        "risk_universe_contract": risk_universe["contract"],
        "risk_slot_contract": "risk_evaluation_slot_v1",
        "risk_universe_evaluation_id": risk_universe["deterministic_id"],
        "expected_risk_count": risk_universe["expected_risk_count"],
        "slot_count": len(risk_universe["slots"]),
        "missing_slot_count": missing_slot_count,
        "missing_evidence_count": gap_count,
        "observed_risk_ids": [
            item["risk_id"] for item in observations if item["status"] == "observed"
        ],
        "missing_evidence_risk_ids": [
            item["risk_id"]
            for item in risk_universe["slots"]
            if item["evaluation_status"] == "missing_evidence"
        ],
        "search_pit_status": "pass",
        "event_supersession_status": "pass",
        "evidence_lineage_status": "pass",
        "official_cache_verification": cache_status,
        "score_eligible": False,
        "network_used": False,
        "default_db_mutated": False,
        "external_cache_verified": True,
        "status": "conditional_pass" if gap_count or missing_slot_count else "pass",
        "warnings": [
            "missing evidence is not a negative conclusion",
            "KAMs are not modified opinions",
            "ordinary related-party activity is not abuse",
            "proposed financing is not realized dilution",
        ],
    }
    write_json(root / "summary.json", summary)
    inputs = [
        {"logical_name": path.name, "sha256": sha256_file(path), "contract": path.stem}
        for path in (
            EVIDENCE_PATH,
            EVENT_INPUT_PATH,
            NORMALIZATION_PATH,
            SEARCH_PATH,
            REGISTRY_PATH,
        )
    ]
    inputs.append(
        {
            "logical_name": "risk_contract_bundle",
            "contract": "risk_contract_bundle_v1",
            "versions": {
                "event": EVENT_CONTRACT,
                "observation": OBSERVATION_CONTRACT,
                "universe": RISK_UNIVERSE_CONTRACT,
                "slot": "risk_evaluation_slot_v1",
            },
            "sha256": canonical_hash(
                {
                    "event": EVENT_CONTRACT,
                    "observation": OBSERVATION_CONTRACT,
                    "universe": RISK_UNIVERSE_CONTRACT,
                    "slot": "risk_evaluation_slot_v1",
                }
            ),
        }
    )
    manifest = finalize_artifacts(
        root,
        run_id=run_id,
        mode="real_research_risk_veto",
        inputs=inputs,
        evidence_gap_count=gap_count,
        score_eligible=False,
    )
    artifact = verify_artifacts(root)
    report = {
        **summary,
        "run_id": run_id,
        "run_dir": run_id,
        "risk_universe_evaluation": risk_universe,
        "observations": observations,
        "artifact_verification": {
            "logical_digest": manifest["logical_digest"],
            "sha256": artifact["sha256"],
        },
    }
    return {
        "status": summary["status"],
        "run_dir": run_id,
        "summary": summary,
        "artifact_verification": artifact,
        "report": report,
    }


def run_formal(
    *,
    output_root: Path | str,
    run_id: str,
    as_of_date: str = "2026-08-02",
    official_cache_root: Path | str | None = None,
    publish_report: bool = False,
) -> dict[str, Any]:
    """Run real research only with an explicit, fully verified official cache."""

    if official_cache_root is None:
        raise FileNotFoundError(
            "missing_external_research_input: --official-cache-root is required"
        )
    root = Path(output_root) / run_id
    if root.exists():
        raise FileExistsError(f"refusing to overwrite existing run: {root}")
    cache_status = verify_official_cache(official_cache_root)
    evidence, events, searches, normalizations = _input_ledgers()
    result = _write_formal_run(
        root, run_id, as_of_date, cache_status, evidence, events, searches, normalizations
    )
    if publish_report:
        report_path = ROOT / "reports" / "petrochina_risk_veto_report.json"
        write_json(report_path, result["report"])
        result["published_report"] = report_path.as_posix()
    return result


def _synthetic_source() -> dict[str, Any]:
    content = b"stage2h1-synthetic-official-evidence"
    digest = hashlib.sha256(content).hexdigest()
    url = "https://example.invalid/stage2h1/synthetic-official-evidence.pdf"
    return {
        "contract": "risk_evidence_record_v1",
        "source_evidence_id": "synthetic-official-evidence",
        "source_type": "other_official",
        "source_id": "synthetic-test-only",
        "title": "Synthetic Stage 2H.1 evidence",
        "announcement_date": "2025-01-01",
        "exact_url": url,
        "announcement_id": "synthetic-stage2h1-001",
        "locator_sha256": hashlib.sha256(url.encode()).hexdigest(),
        "content_sha256": digest,
        "byte_size": len(content),
        "page_count": 1,
        "retrieved_at": "2025-01-01T00:00:00+00:00",
        "available_at": "2025-01-01T00:00:00+00:00",
        "source_page": "1",
        "source_section": "synthetic",
        "extraction_method": "synthetic_test_only",
        "status": "retrieved",
        "fields": {"synthetic": {}},
        "warnings": ["synthetic_test_only; never used for a real conclusion"],
        "logical_cache_object_key": f"{digest}.pdf",
    }


def _synthetic_registers() -> list[dict[str, Any]]:
    return [
        {
            "contract": SEARCH_CONTRACT,
            "contract_version": SEARCH_CONTRACT,
            "search_register_id": f"synthetic-{risk_id}-v1",
            "risk_id": risk_id,
            "coverage_start": "2021-01-01",
            "coverage_end": "2025-01-01",
            "query_started_at": "2025-01-01T00:00:00+00:00",
            "query_completed_at": "2025-01-02T00:00:00+00:00",
            "available_at": "2025-01-02T00:00:00+00:00",
            "systems": ["synthetic_test_only"],
            "terms": [risk_id],
            "identifiers": ["SYNTHETIC"],
            "completeness": True,
            "completeness_basis": "synthetic_test_only",
            "result_count": 1,
            "retrieved_count": 1,
            "rejected_count": 0,
            "rejected_candidates": [],
            "anti_bot_gaps": [],
            "network_gaps": [],
            "supersedes_search_register_id": None,
            "code_version": CODE_VERSION,
        }
        for risk_id in RISK_IDS
    ]


def _synthetic_event(
    source: dict[str, Any],
    risk_id: str,
    event_type: str,
    semantic_key: str,
    inputs: dict[str, Any],
    classification: str,
    available_at: str,
    status: str = "observed",
    supersedes: str | None = None,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    bucket_name = event_type.replace(":", "_")
    source["fields"]["synthetic"].setdefault(bucket_name, {}).update(inputs)
    normalizations: list[dict[str, Any]] = []
    for target_field, value in sorted(inputs.items()):
        transform = "audit_opinion_to_class_v1" if target_field == "opinion_type" else "identity"
        record = {
            "contract": NORMALIZATION_CONTRACT,
            "normalization_id": f"synthetic-norm-{event_type}-{semantic_key}-{target_field}",
            "risk_id": risk_id,
            "event_semantic_key": semantic_key,
            "target_field": target_field,
            "source_evidence_id": source["source_evidence_id"],
            "source_field_path": f"fields.synthetic.{bucket_name}.{target_field}",
            "raw_value": value,
            "raw_unit": "synthetic",
            "normalized_value": value
            if transform == "identity"
            else ("unmodified" if value == "unmodified" else value),
            "normalized_unit": "synthetic",
            "transform": transform,
            "denominator_fact_ids": [],
            "denominator_evidence_ids": [],
            "rounding_policy": "exact_float_v1",
            "formula_version": "synthetic_identity_v1",
            "verification_status": "verified",
            "warnings": [],
            "available_at": source["available_at"],
            "code_version": CODE_VERSION,
        }
        normalizations.append(record)
    event = _event(
        risk_id=risk_id,
        event_type=event_type,
        semantic_key=semantic_key,
        event_date="2025-01-01",
        available_at=available_at,
        period="SYNTHETIC",
        input_evidence_ids=[source["source_evidence_id"]],
        supplemental_evidence_ids=[],
        input_source_types=[source["source_type"]],
        supplemental_source_types=[],
        classification=classification,
        inputs={item["target_field"]: item["normalized_value"] for item in normalizations},
        normalization_ids=[item["normalization_id"] for item in normalizations],
        input_lineage_hash=normalization_lineage_hash(normalizations),
        status=status,
        supersedes=supersedes,
    )
    return event, normalizations


def run_test_capsule(output_root: Path | str, run_id: str) -> dict[str, Any]:
    """Run positive triggers, PIT correction and a complete synthetic search ledger."""

    source = _synthetic_source()
    specifications = [
        (
            "modified_audit_opinion",
            "synthetic_modified_opinion",
            {"opinion_type": "qualified"},
            "qualified",
        ),
        (
            "going_concern_material_uncertainty",
            "synthetic_going_concern",
            {"explicit_material_uncertainty": True},
            "explicit_material_uncertainty",
        ),
        (
            "controlling_shareholder_pledge_risk",
            "synthetic_pledge",
            {"direct_controller_pledge_ratio": 0.25, "pledged_total_share_ratio": 0.0},
            "high_direct_controller_pledge",
        ),
        (
            "material_related_party_transaction_risk",
            "synthetic_non_market_rpt",
            {
                "non_market": True,
                "approval_cap_breach": False,
                "material_non_operating_finance": False,
            },
            "non_market",
        ),
        (
            "controlling_shareholder_fund_occupation_or_related_guarantee",
            "synthetic_fund_occupation",
            {"fund_occupation": True, "illegal_related_guarantee": False},
            "fund_occupation",
        ),
        (
            "repeated_equity_financing_or_material_dilution",
            "synthetic_completed_financing",
            {"completed_financing": True, "realized_dilution_share_delta": 100},
            "completed_dilution",
        ),
        (
            "formal_regulatory_investigation_or_major_discipline",
            "synthetic_major_discipline",
            {"formal_investigation": False, "major_discipline": True},
            "major_discipline",
        ),
        (
            "material_error_restatement",
            "synthetic_prior_period_error",
            {"restatement_classification": "prior_period_error_or_misstatement"},
            "prior_period_error_or_misstatement",
        ),
    ]
    events: list[dict[str, Any]] = []
    normalizations: list[dict[str, Any]] = []
    for risk_id, event_type, inputs, classification in specifications:
        event, records = _synthetic_event(
            source,
            risk_id,
            event_type,
            f"{event_type}:SYNTHETIC",
            inputs,
            classification,
            "2025-01-02T00:00:00+00:00",
        )
        events.append(event)
        normalizations.extend(records)
    correction, correction_norms = _synthetic_event(
        source,
        "modified_audit_opinion",
        "synthetic_correction_unmodified",
        "synthetic_modified_opinion:SYNTHETIC",
        {"opinion_type": "unmodified"},
        "unmodified",
        "2025-01-03T00:00:00+00:00",
        status="not_observed_within_bounded_evidence",
        supersedes=events[0]["event_id"],
    )
    events.append(correction)
    normalizations.extend(correction_norms)
    registers = _synthetic_registers()
    validate_contracts(
        evidence=[source], events=events, search_registers=registers, normalizations=normalizations
    )
    before_universe = evaluate_risk_universe_as_of(
        symbol="601857.SH",
        as_of_date="2025-01-02",
        events=events,
        search_registers=registers,
        evidence=[source],
        normalizations=normalizations,
    )
    after_universe = evaluate_risk_universe_as_of(
        symbol="601857.SH",
        as_of_date="2025-01-03",
        events=events,
        search_registers=registers,
        evidence=[source],
        normalizations=normalizations,
    )
    run_dir = Path(output_root) / run_id
    if run_dir.exists():
        raise FileExistsError(f"refusing to overwrite existing run: {run_dir}")
    before = before_universe["observations"]
    after = after_universe["observations"]
    run_dir.mkdir(parents=True)
    write_json(run_dir / "synthetic_source_evidence.json", {"entries": [source]})
    write_json(run_dir / "synthetic_normalizations.json", {"entries": normalizations})
    write_json(run_dir / "synthetic_risk_events.json", {"events": events})
    write_json(run_dir / "synthetic_search_register.json", {"entries": registers})
    write_json(run_dir / "synthetic_observations_before.json", {"observations": before})
    write_json(run_dir / "synthetic_observations_after.json", {"observations": after})
    write_json(
        run_dir / "synthetic_risk_universe_before.json",
        before_universe,
    )
    write_json(
        run_dir / "synthetic_risk_universe_after.json",
        after_universe,
    )
    write_json(
        run_dir / "summary.json",
        {
            "contract": "stage2h1_synthetic_risk_capsule_v2",
            "before_triggered_risks": [
                item["risk_id"] for item in before if item["status"] == "observed"
            ],
            "after_triggered_risks": [
                item["risk_id"] for item in after if item["status"] == "observed"
            ],
            "correction_supersedes": correction["supersedes"],
            "pit_as_of_dates": ["2025-01-02", "2025-01-03"],
            "risk_slot_count": 8,
            "before_slot_count": len(before_universe["slots"]),
            "after_slot_count": len(after_universe["slots"]),
            "score_eligible": False,
            "network_used": False,
            "default_db_mutated": False,
        },
    )
    finalize_artifacts(
        run_dir,
        run_id=run_id,
        mode="synthetic_test_only_risk_veto",
        inputs=[
            {
                "logical_name": "synthetic_contracts",
                "sha256": stable_id("input", {"events": events, "normalizations": normalizations}),
                "contract": "risk_contract_bundle_v1",
                "versions": {
                    "event": EVENT_CONTRACT,
                    "observation": OBSERVATION_CONTRACT,
                    "universe": RISK_UNIVERSE_CONTRACT,
                    "slot": "risk_evaluation_slot_v1",
                },
            }
        ],
        evidence_gap_count=0,
        score_eligible=False,
    )
    return {
        "status": "pass",
        "run_dir": run_id,
        "artifact_verification": verify_artifacts(run_dir),
        "before": before,
        "after": after,
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("verify-contracts")
    preflight = sub.add_parser("acquisition-preflight")
    preflight.add_argument("--official-cache-root", type=Path, required=True)
    preflight.add_argument("--output", type=Path, required=True)
    formal = sub.add_parser("run-offline-formal")
    formal.add_argument("--output", type=Path, required=True)
    formal.add_argument("--run-id", required=True)
    formal.add_argument("--as-of-date", default="2026-08-02")
    formal.add_argument("--official-cache-root", type=Path, required=True)
    formal.add_argument("--publish-report", action="store_true")
    test = sub.add_parser("run-test-capsule")
    test.add_argument("--output", type=Path, required=True)
    test.add_argument("--run-id", default="stage2h1_test_capsule")
    compare = sub.add_parser("compare-runs")
    compare.add_argument("--left", type=Path, required=True)
    compare.add_argument("--right", type=Path, required=True)
    verify = sub.add_parser("verify-artifacts")
    verify.add_argument("--run-dir", type=Path, required=True)
    sub.add_parser("verify-clean-clone")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.command == "verify-contracts":
        result = verify_contracts()
    elif args.command == "acquisition-preflight":
        result = verify_official_cache(args.official_cache_root)
        write_json(args.output, result)
    elif args.command == "run-offline-formal":
        result = run_formal(
            output_root=args.output,
            run_id=args.run_id,
            as_of_date=args.as_of_date,
            official_cache_root=args.official_cache_root,
            publish_report=args.publish_report,
        )
    elif args.command == "run-test-capsule":
        result = run_test_capsule(args.output, args.run_id)
    elif args.command == "compare-runs":
        result = compare_artifact_runs(args.left, args.right)
    elif args.command == "verify-artifacts":
        result = verify_artifacts(args.run_dir)
    else:
        result = verify_stage2g_clean_clone()
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2, default=str))
    return 1 if result.get("status") == "fail" else 0


if __name__ == "__main__":
    raise SystemExit(main())
