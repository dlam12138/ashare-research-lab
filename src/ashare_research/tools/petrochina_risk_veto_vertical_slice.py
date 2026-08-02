"""Stage 2H PetroChina risk-veto evidence vertical slice.

Acquisition is explicit and cache-only.  Formal evaluation is offline, PIT
aware, run-scoped, artifact-verified, and never publishes by default.
"""

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
    OBSERVATION_CONTRACT,
    RISK_IDS,
    SEARCH_CONTRACT,
    STATUS_VOCABULARY,
    TRIGGER_RULES,
    evaluate_observations,
    stable_id,
    validate_contracts,
)
from ashare_research.tools.stage2g_reproducibility import (
    verify_clean_clone as verify_stage2g_clean_clone,
)
from ashare_research.tools.stage2g_reproducibility import (
    verify_contracts as verify_stage2g_contracts,
)

ROOT = Path(__file__).resolve().parents[3]
EVIDENCE_PATH = ROOT / "events" / "petrochina_risk_source_evidence_v1.json"
REGISTRY_PATH = ROOT / "events" / "petrochina_risk_evidence_registry_v1.json"
SEARCH_PATH = ROOT / "events" / "petrochina_bounded_search_register_v1.json"
EVENT_INPUT_PATH = ROOT / "events" / "petrochina_risk_event_inputs_v1.json"


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _event(
    *,
    risk_id: str,
    event_type: str,
    event_date: str,
    available_at: str,
    period: str,
    evidence_ids: list[str],
    source_types: list[str],
    classification: str,
    inputs: dict[str, Any],
    status: str = "not_observed_within_bounded_evidence",
    missing_reasons: list[str] | None = None,
    warnings: list[str] | None = None,
    supersedes: str | None = None,
) -> dict[str, Any]:
    values = {
        "symbol": "601857.SH",
        "risk_id": risk_id,
        "event_type": event_type,
        "event_date": event_date,
        "available_at": available_at,
        "period": period,
        "evidence_ids": evidence_ids,
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
        "source_types": source_types,
        "extraction_method": "formal_structured_rule_v1",
        "missing_reasons": missing_reasons or [],
        "warnings": warnings or [],
        "code_version": CODE_VERSION,
        "score_eligible": False,
    }


def build_event_records() -> list[dict[str, Any]]:
    """Convert reviewed structured inputs into versioned deterministic events."""

    inputs = _load(EVENT_INPUT_PATH)
    records: list[dict[str, Any]] = []
    for annual in inputs["annuals"]:
        evidence_ids = annual["evidence_ids"]
        source_types = ["issuer_official", "exchange_official"]
        period = annual["period"]
        common = {
            "event_date": annual["event_date"],
            "available_at": annual["available_at"],
            "period": period,
            "evidence_ids": evidence_ids,
            "source_types": source_types,
        }
        records.append(
            _event(
                risk_id="modified_audit_opinion",
                event_type="annual_audit_opinion",
                classification=annual["audit_opinion"],
                inputs={"opinion_type": annual["audit_opinion"]},
                warnings=(
                    ["key audit matters are separate from opinion modification"]
                    if annual["key_audit_matters_missing"]
                    else []
                ),
                **common,
            )
        )
        records.append(
            _event(
                risk_id="going_concern_material_uncertainty",
                event_type="annual_going_concern_review",
                classification="no_explicit_material_uncertainty_observed",
                inputs={"explicit_material_uncertainty": annual["explicit_material_uncertainty"]},
                warnings=["bounded annual-report scope; no permanent absence claim"],
                **common,
            )
        )
        records.append(
            _event(
                risk_id="controlling_shareholder_pledge_risk",
                event_type="annual_controller_pledge_disclosure",
                classification="direct_controller_pledge_not_observed",
                inputs={
                    "direct_controller_pledge_ratio": annual["direct_controller_pledge_ratio"],
                    "pledged_total_share_ratio": annual["pledged_total_share_ratio"],
                    "threshold_basis": TRIGGER_RULES["controlling_shareholder_pledge_risk"][
                        "thresholds"
                    ],
                },
                warnings=[
                    "exchangeable-bond trust-account pledge is retained as raw exposure, "
                    "not direct controller pledge"
                ],
                **common,
            )
        )
        records.append(
            _event(
                risk_id="material_related_party_transaction_risk",
                event_type="annual_related_party_transaction_review",
                classification="ordinary_operating_related_party_activity",
                inputs={
                    "related_sales_million_cny": annual["related_sales_million_cny"],
                    "related_purchase_million_cny": annual["related_purchase_million_cny"],
                    "related_sales_ratio": annual["related_sales_ratio"],
                    "related_purchase_ratio": annual["related_purchase_ratio"],
                    "ordinary_operating": True,
                    "non_market": annual["non_market"],
                    "approval_cap_breach": annual["approval_cap_breach"],
                    "material_non_operating_finance": annual["material_non_operating_finance"],
                },
                warnings=[
                    "ordinary related-party transactions are not classified as abuse "
                    "without an explicit trigger"
                ],
                **common,
            )
        )
        records.append(
            _event(
                risk_id="controlling_shareholder_fund_occupation_or_related_guarantee",
                event_type="annual_fund_occupation_and_guarantee_review",
                classification="no_official_non_operating_occupation_or_illegal_guarantee_observed",
                inputs={
                    "company_provided_related_balance_million_cny": annual[
                        "company_provided_related_balance_million_cny"
                    ],
                    "fund_occupation": annual["fund_occupation"],
                    "illegal_related_guarantee": annual["illegal_related_guarantee"],
                },
                warnings=[
                    "disclosed related-party balance is not itself an occupation classification"
                ],
                **common,
            )
        )
        records.append(
            _event(
                risk_id="repeated_equity_financing_or_material_dilution",
                event_type="annual_equity_financing_and_share_change_review",
                classification=(
                    "proposed_or_authorized_only"
                    if annual["proposed_financing"]
                    else "no_completed_equity_financing_observed"
                ),
                inputs={
                    "completed_financing": annual["completed_financing"],
                    "realized_dilution_share_delta": annual["realized_dilution_share_delta"],
                    "proposed_financing": annual["proposed_financing"],
                },
                warnings=["proposal or authorization is not realized dilution"],
                **common,
            )
        )
    for restatement in inputs["restatements"]:
        records.append(
            _event(
                risk_id="material_error_restatement",
                event_type="comparative_period_version_change",
                event_date=restatement["event_date"],
                available_at=restatement["available_at"],
                period=restatement["period"],
                evidence_ids=restatement["evidence_ids"],
                source_types=["exchange_official"],
                classification=restatement["classification"],
                inputs={
                    "restatement_classification": restatement["classification"],
                    "reason": restatement["reason"],
                    "changed_fields": restatement["changed_fields"],
                },
                warnings=[
                    "ordinary accounting-policy, standard-change and common-control "
                    "recasts are not error risk"
                ],
            )
        )
    gap = inputs["regulatory_search_gap"]
    records.append(
        _event(
            risk_id="formal_regulatory_investigation_or_major_discipline",
            event_type="bounded_regulatory_search",
            event_date=gap["event_date"],
            available_at=gap["available_at"],
            period=gap["period"],
            evidence_ids=gap["evidence_ids"],
            source_types=[],
            classification="not_fully_retrieved",
            inputs={"formal_investigation": False, "major_discipline": False},
            status="missing_evidence",
            missing_reasons=gap["missing_reasons"],
            warnings=gap["warnings"],
        )
    )
    return records


def _input_ledgers() -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    evidence = _load(EVIDENCE_PATH)["entries"]
    searches = _load(SEARCH_PATH)["entries"]
    events = build_event_records()
    validate_contracts(evidence=evidence, events=events, search_registers=searches)
    evidence_ids = {item["source_evidence_id"] for item in evidence}
    for event in events:
        if not set(event["evidence_ids"]) <= evidence_ids:
            raise ValueError(f"event references unknown evidence: {event['event_id']}")
    return evidence, events, searches


def verify_official_cache(cache_root: Path | str) -> dict[str, Any]:
    """Resolve the official-document registry against an explicit cache root."""

    evidence, events, searches = _input_ledgers()
    resolved, registry = MarketSnapshotResolver(
        REGISTRY_PATH, mode="real_research", cache_root=cache_root
    ).resolve()
    resolved_names = {record["logical_name"] for _, record in resolved}
    expected_names = {
        item["source_evidence_id"] for item in evidence if item["status"] == "retrieved"
    }
    registry_names = {item["logical_name"] for item in registry["providers"]}
    if not {"pc-2023-issuer-annual", "pc-2023-exchange-annual"} <= expected_names:
        raise ValueError("2023 official source pair missing")
    if not resolved_names <= registry_names:
        raise ValueError("resolver returned an unregistered official object")
    return {
        "status": "pass",
        "mode": "real_research",
        "registry_contract": registry["contract"],
        "resolved_object_count": len(resolved),
        "evidence_count": len(evidence),
        "event_count": len(events),
        "search_register_count": len(searches),
        "network_used": False,
        "default_db_mutated": False,
    }


def verify_contracts() -> dict[str, Any]:
    stage2g = verify_stage2g_contracts()
    evidence, events, searches = _input_ledgers()
    registry = _load(REGISTRY_PATH)
    MarketSnapshotResolver.validate_registry_contract(registry)
    return {
        "status": "pass_with_explicit_gaps"
        if any(not item["completeness"] for item in searches)
        else "pass",
        "methodology_version": METHODOLOGY_VERSION,
        "status_vocabulary": STATUS_VOCABULARY,
        "stage2g_contract_status": stage2g["status"],
        "risk_contract": validate_contracts(
            evidence=evidence, events=events, search_registers=searches
        ),
        "official_registry": {
            "contract": registry["contract"],
            "provider_count": len(registry["providers"]),
            "path_independent": True,
        },
        "score_eligible": False,
        "network_used": False,
    }


def run_formal(
    *,
    output_root: Path | str,
    run_id: str,
    as_of_date: str = "2026-08-02",
    official_cache_root: Path | str | None = None,
    publish_report: bool = False,
) -> dict[str, Any]:
    """Run the formal risk-veto slice with no network and no default DB writes."""

    root = Path(output_root) / run_id
    if root.exists():
        raise FileExistsError(f"refusing to overwrite existing run: {root}")
    evidence, events, searches = _input_ledgers()
    cache_status = None
    if official_cache_root is not None:
        cache_status = verify_official_cache(official_cache_root)
    observations = evaluate_observations(
        symbol="601857.SH",
        as_of_date=as_of_date,
        events=events,
        search_registers=searches,
        evidence=evidence,
    )
    root.mkdir(parents=True)
    write_json(
        root / "source_evidence.json", {"contract": "risk_evidence_ledger_v1", "entries": evidence}
    )
    write_json(root / "risk_events.json", {"contract": "risk_event_ledger_v1", "events": events})
    write_json(
        root / "bounded_search_register.json",
        {"contract": "bounded_search_register_ledger_v1", "entries": searches},
    )
    write_json(
        root / "risk_veto_observations.json",
        {"contract": OBSERVATION_CONTRACT, "observations": observations},
    )
    gap_count = sum(item["status"] == "missing_evidence" for item in observations)
    summary = {
        "contract": "petrochina_risk_veto_vertical_slice_v1",
        "symbol": "601857.SH",
        "as_of_date": as_of_date,
        "methodology_version": METHODOLOGY_VERSION,
        "code_version": CODE_VERSION,
        "observation_count": len(observations),
        "missing_evidence_count": gap_count,
        "observed_risk_ids": [
            item["risk_id"] for item in observations if item["status"] == "observed"
        ],
        "missing_evidence_risk_ids": [
            item["risk_id"] for item in observations if item["status"] == "missing_evidence"
        ],
        "score_eligible": False,
        "network_used": False,
        "default_db_mutated": False,
        "external_cache_verified": bool(cache_status),
        "status": "conditional_pass" if gap_count else "pass",
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
        for path in (EVIDENCE_PATH, EVENT_INPUT_PATH, SEARCH_PATH, REGISTRY_PATH)
    ]
    manifest = finalize_artifacts(
        root,
        run_id=run_id,
        mode="offline_formal_risk_veto",
        inputs=inputs,
        evidence_gap_count=gap_count,
        score_eligible=False,
    )
    artifact = verify_artifacts(root)
    report = {
        **summary,
        "run_id": run_id,
        "run_dir": run_id,
        "artifact_manifest": {
            "logical_digest": manifest["logical_digest"],
            "sha256": artifact["sha256"],
        },
    }
    if publish_report:
        write_json(ROOT / "reports" / "petrochina_risk_veto_report.json", report)
    return {
        "status": summary["status"],
        "run_dir": run_id,
        "summary": summary,
        "artifact_verification": artifact,
    }


def _synthetic_source() -> dict[str, Any]:
    content_hash = hashlib.sha256(b"stage2h-synthetic-official-evidence").hexdigest()
    url = "https://example.invalid/stage2h/synthetic-official-evidence.pdf"
    return {
        "contract": "risk_evidence_record_v1",
        "source_evidence_id": "synthetic-official-evidence",
        "source_type": "other_official",
        "source_id": "synthetic-test-only",
        "title": "Synthetic Stage 2H evidence",
        "announcement_date": "2025-01-01",
        "exact_url": url,
        "announcement_id": "synthetic-stage2h-001",
        "locator_sha256": hashlib.sha256(url.encode()).hexdigest(),
        "content_sha256": content_hash,
        "byte_size": len(b"stage2h-synthetic-official-evidence"),
        "page_count": 1,
        "retrieved_at": "2026-08-02T00:00:00+08:00",
        "available_at": "2025-01-01T00:00:00+08:00",
        "source_page": "1",
        "source_section": "synthetic",
        "extraction_method": "synthetic_test_only",
        "status": "retrieved",
        "fields": {"synthetic": True},
        "warnings": ["synthetic_test_only; never used for a real conclusion"],
        "logical_cache_object_key": f"{content_hash}.pdf",
    }


def run_test_capsule(output_root: Path | str, run_id: str) -> dict[str, Any]:
    """Exercise positive triggers, corrections, PIT filtering and missingness."""

    source = _synthetic_source()
    registers = []
    for risk_id in RISK_IDS:
        registers.append(
            {
                "contract": SEARCH_CONTRACT,
                "search_register_id": f"synthetic-{risk_id}",
                "risk_id": risk_id,
                "systems": ["synthetic_test_only"],
                "date_range": {"start": "2021-01-01", "end": "2026-08-02"},
                "search_terms": [risk_id],
                "identifiers": ["SYNTHETIC"],
                "query_time": "2026-08-02T00:00:00+08:00",
                "result_count": 1,
                "retrieved_count": 1,
                "rejected_candidates": [],
                "anti_bot_gaps": [],
                "network_gaps": [],
                "completeness": True,
                "completeness_basis": "synthetic_test_only",
            }
        )
    events = [
        _event(
            risk_id="modified_audit_opinion",
            event_type="synthetic_modified_opinion",
            event_date="2025-01-01",
            available_at="2025-01-02T00:00:00+08:00",
            period="SYNTHETIC",
            evidence_ids=[source["source_evidence_id"]],
            source_types=[source["source_type"]],
            classification="qualified",
            inputs={"opinion_type": "qualified"},
            status="observed",
        ),
        _event(
            risk_id="going_concern_material_uncertainty",
            event_type="synthetic_going_concern",
            event_date="2025-01-01",
            available_at="2025-01-02T00:00:00+08:00",
            period="SYNTHETIC",
            evidence_ids=[source["source_evidence_id"]],
            source_types=[source["source_type"]],
            classification="explicit_material_uncertainty",
            inputs={"explicit_material_uncertainty": True},
            status="observed",
        ),
        _event(
            risk_id="controlling_shareholder_pledge_risk",
            event_type="synthetic_pledge",
            event_date="2025-01-01",
            available_at="2025-01-02T00:00:00+08:00",
            period="SYNTHETIC",
            evidence_ids=[source["source_evidence_id"]],
            source_types=[source["source_type"]],
            classification="high_direct_controller_pledge",
            inputs={"direct_controller_pledge_ratio": 0.25, "pledged_total_share_ratio": 0.0},
            status="observed",
        ),
        _event(
            risk_id="material_related_party_transaction_risk",
            event_type="synthetic_non_market_rpt",
            event_date="2025-01-01",
            available_at="2025-01-02T00:00:00+08:00",
            period="SYNTHETIC",
            evidence_ids=[source["source_evidence_id"]],
            source_types=[source["source_type"]],
            classification="non_market",
            inputs={
                "non_market": True,
                "approval_cap_breach": False,
                "material_non_operating_finance": False,
            },
            status="observed",
        ),
        _event(
            risk_id="controlling_shareholder_fund_occupation_or_related_guarantee",
            event_type="synthetic_fund_occupation",
            event_date="2025-01-01",
            available_at="2025-01-02T00:00:00+08:00",
            period="SYNTHETIC",
            evidence_ids=[source["source_evidence_id"]],
            source_types=[source["source_type"]],
            classification="fund_occupation",
            inputs={"fund_occupation": True, "illegal_related_guarantee": False},
            status="observed",
        ),
        _event(
            risk_id="repeated_equity_financing_or_material_dilution",
            event_type="synthetic_completed_financing",
            event_date="2025-01-01",
            available_at="2025-01-02T00:00:00+08:00",
            period="SYNTHETIC",
            evidence_ids=[source["source_evidence_id"]],
            source_types=[source["source_type"]],
            classification="completed_dilution",
            inputs={"completed_financing": True, "realized_dilution_share_delta": 100},
            status="observed",
        ),
        _event(
            risk_id="formal_regulatory_investigation_or_major_discipline",
            event_type="synthetic_major_discipline",
            event_date="2025-01-01",
            available_at="2025-01-02T00:00:00+08:00",
            period="SYNTHETIC",
            evidence_ids=[source["source_evidence_id"]],
            source_types=[source["source_type"]],
            classification="major_discipline",
            inputs={"formal_investigation": False, "major_discipline": True},
            status="observed",
        ),
        _event(
            risk_id="material_error_restatement",
            event_type="synthetic_prior_period_error",
            event_date="2025-01-01",
            available_at="2025-01-02T00:00:00+08:00",
            period="SYNTHETIC",
            evidence_ids=[source["source_evidence_id"]],
            source_types=[source["source_type"]],
            classification="prior_period_error_or_misstatement",
            inputs={"restatement_classification": "prior_period_error_or_misstatement"},
            status="observed",
        ),
    ]
    # A correction supersedes the first synthetic event and must receive a new ID.
    correction = _event(
        risk_id="modified_audit_opinion",
        event_type="synthetic_correction_unmodified",
        event_date="2025-01-01",
        available_at="2025-01-03T00:00:00+08:00",
        period="SYNTHETIC",
        evidence_ids=[source["source_evidence_id"]],
        source_types=[source["source_type"]],
        classification="unmodified",
        inputs={"opinion_type": "unmodified"},
        status="not_observed_within_bounded_evidence",
        supersedes=events[0]["event_id"],
    )
    events.append(correction)
    validate_contracts(evidence=[source], events=events, search_registers=registers)
    observations = evaluate_observations(
        symbol="601857.SH",
        as_of_date="2025-01-02",
        events=events,
        search_registers=registers,
        evidence=[source],
    )
    run_dir = Path(output_root) / run_id
    if run_dir.exists():
        raise FileExistsError(f"refusing to overwrite existing run: {run_dir}")
    run_dir.mkdir(parents=True)
    write_json(run_dir / "synthetic_source_evidence.json", {"entries": [source]})
    write_json(run_dir / "synthetic_risk_events.json", {"events": events})
    write_json(run_dir / "synthetic_search_register.json", {"entries": registers})
    write_json(run_dir / "synthetic_observations.json", {"observations": observations})
    write_json(
        run_dir / "summary.json",
        {
            "contract": "stage2h_synthetic_risk_capsule_v1",
            "triggered_risks": [
                item["risk_id"] for item in observations if item["status"] == "observed"
            ],
            "correction_supersedes": correction["supersedes"],
            "pit_as_of_date": "2025-01-02",
            "score_eligible": False,
            "network_used": False,
            "default_db_mutated": False,
        },
    )
    finalize_artifacts(
        run_dir,
        run_id=run_id,
        mode="synthetic_test_only_risk_veto",
        inputs=[{"logical_name": "synthetic_contracts", "sha256": stable_id("input", events)}],
        evidence_gap_count=0,
        score_eligible=False,
    )
    return {"status": "pass", "run_dir": run_id, "artifact_verification": verify_artifacts(run_dir)}


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
    formal.add_argument("--official-cache-root", type=Path)
    formal.add_argument("--publish-report", action="store_true")
    test = sub.add_parser("run-test-capsule")
    test.add_argument("--output", type=Path, required=True)
    test.add_argument("--run-id", default="stage2h_test_capsule")
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
