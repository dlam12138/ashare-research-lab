"""Strict, non-production ROIC official-fact readiness audit.

This module audits canonical Facts and their evidence.  It never registers a
Metric, calculates a shadow ROIC, writes the default database, or changes a
value profile.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import tempfile
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Any

from ashare_research.facts.identity import build_fact_id
from ashare_research.tools.roic_contracts import (
    DEPENDENCY_GRAPH_PATH,
    FORMAL_STATUSES,
    METHODOLOGY_DECISIONS_PATH,
    REGISTRY_PATH,
    canonical_digest,
    decisions_by_id,
    dependency_graph_digest,
    entries_by_role,
    load_dependency_graph,
    load_methodology_decisions,
    load_registry,
    registry_digest,
)
from ashare_research.tools.roic_fact_snapshot import (
    INVENTORY_V2_PATH,
    SYMBOL,
    export_inventory,
    load_inventory,
    repository_pit_probe,
)
from ashare_research.validation.version_chain import VersionChainValidator

YEARS = tuple(range(2020, 2026))
ROOT = Path(__file__).resolve().parents[3]


def _iso(value: Any) -> str:
    return "" if value is None else str(value).strip()


def _year(context: dict[str, Any], fact: dict[str, Any]) -> int | None:
    if context.get("fiscal_year") is not None:
        try:
            return int(context["fiscal_year"])
        except (TypeError, ValueError):
            pass
    period_end = _iso(fact.get("period_end"))
    try:
        return int(period_end[:4])
    except (TypeError, ValueError):
        return None


def _date_or_none(value: Any) -> date | None:
    try:
        return date.fromisoformat(_iso(value))
    except (TypeError, ValueError):
        return None


def _identity_ok(fact: dict[str, Any]) -> bool:
    identity = {
        "fact_id": fact.get("fact_id", ""),
        "concept_id": fact.get("concept_id", ""),
        "concept_version": fact.get("concept_version", "1"),
        "symbol": fact.get("symbol", ""),
        "context_id": fact.get("context_id", ""),
        "source_id": fact.get("source_id", ""),
        "fact_version": fact.get("fact_version", 1),
        "restatement_version": fact.get("restatement_version", "original"),
        "derivation_definition_id": fact.get("derivation_definition_id", ""),
        "derivation_version": fact.get("derivation_version", ""),
    }
    return bool(identity["fact_id"]) and build_fact_id(identity) == identity["fact_id"]


def _chain_audit(
    candidates: list[dict[str, Any]], all_facts: dict[str, dict[str, Any]]
) -> dict[str, Any]:
    """Validate legal version edges and return a complete chain audit."""
    edges: list[dict[str, Any]] = []
    errors: list[str] = []
    candidate_ids = {str(fact.get("fact_id")) for fact in candidates}
    for fact in candidates:
        fid = str(fact.get("fact_id", ""))
        version = fact.get("fact_version", 1)
        supersedes = _iso(fact.get("supersedes_fact_id"))
        if not isinstance(version, int) or version < 1:
            errors.append(f"invalid_fact_version:{fid}")
            continue
        if version == 1 and supersedes:
            errors.append(f"version_1_has_predecessor:{fid}")
        if version > 1:
            if not supersedes or supersedes == fid:
                errors.append(f"version_predecessor_missing_or_self:{fid}")
                continue
            old = all_facts.get(supersedes)
            if old is None:
                errors.append(f"predecessor_missing:{fid}:{supersedes}")
                continue
            stable = (
                "symbol",
                "concept_id",
                "concept_version",
                "context_id",
                "source_id",
                "derivation_definition_id",
                "derivation_version",
            )
            mismatched = [key for key in stable if _iso(fact.get(key)) != _iso(old.get(key))]
            if mismatched:
                errors.append(f"stable_identity_changed:{fid}:{','.join(mismatched)}")
            if old.get("fact_version") != version - 1:
                errors.append(f"version_not_strict_plus_one:{fid}")
            old_available = _date_or_none(old.get("available_at"))
            new_available = _date_or_none(fact.get("available_at"))
            if old_available and new_available and new_available < old_available:
                errors.append(f"available_at_moved_backwards:{fid}")
            if (
                old.get("symbol") != fact.get("symbol")
                or old.get("concept_id") != fact.get("concept_id")
                or old.get("context_id") != fact.get("context_id")
            ):
                errors.append(f"cross_identity_predecessor:{fid}")
            edges.append(
                {
                    "fact_id": fid,
                    "supersedes_fact_id": supersedes,
                    "old_fact_version": old.get("fact_version"),
                    "new_fact_version": version,
                }
            )

    class _SnapshotRepository:
        def __init__(self, rows: dict[str, dict[str, Any]]) -> None:
            self.rows = rows

        def _get_fact_by_id(self, fact_id: str, _conn: Any) -> dict[str, Any] | None:
            return self.rows.get(fact_id)

    # Reuse the repository-aware validator for strict +1, stable identity,
    # non-backward dates and cycle semantics. The small adapter keeps the
    # committed JSON inventory read-only while preserving the project gate.
    try:
        validator_results = VersionChainValidator(_SnapshotRepository(all_facts)).validate(
            candidates,
            conn=object(),
            now="2026-08-02T00:00:00+00:00",
        )
        errors.extend(
            f"version_chain_validator:{result.target_id}"
            for result in validator_results
            if not result.passed
        )
    except Exception as exc:  # the formal status is unresolved, never ready
        errors.append(f"version_chain_validator_exception:{type(exc).__name__}")
    # Walk every local chain for cycles, including predecessors outside the
    # candidate set so a restated visible row cannot hide a broken edge.
    for fact in candidates:
        seen: set[str] = set()
        current = str(fact.get("fact_id", ""))
        while current:
            if current in seen:
                errors.append(f"supersedes_cycle:{current}")
                break
            seen.add(current)
            current = _iso(all_facts.get(current, {}).get("supersedes_fact_id"))
            if current and current not in all_facts:
                break
    return {
        "candidate_fact_ids": sorted(candidate_ids),
        "edges": sorted(edges, key=lambda edge: (edge["fact_id"], edge["supersedes_fact_id"])),
        "chain_status": "valid" if not errors else "unresolved",
        "errors": sorted(set(errors)),
    }


def select_roic_fact_as_of(
    *,
    facts: list[dict[str, Any]],
    all_facts: dict[str, dict[str, Any]],
    entry: dict[str, Any],
    fiscal_year: int,
    assessment_as_of: str,
) -> dict[str, Any]:
    """Select the one legal visible chain tip for a registry role/year."""
    exact = [
        fact
        for fact in facts
        if fact.get("concept_id") == entry["canonical_concept_id"]
        and fact.get("symbol") == SYMBOL
        and _iso(fact.get("period_end")) == f"{fiscal_year}-12-31"
    ]
    audit = _chain_audit(exact, all_facts)
    visible = [
        fact
        for fact in exact
        if fact.get("eligible_for_metrics") is True
        and _date_or_none(fact.get("available_at")) is not None
        and _date_or_none(fact.get("available_at")) <= _date_or_none(assessment_as_of)
    ]
    superseded_visible = {
        str(fact.get("supersedes_fact_id"))
        for fact in visible
        if _iso(fact.get("supersedes_fact_id"))
    }
    tips = [fact for fact in visible if str(fact.get("fact_id")) not in superseded_visible]
    selected = tips[0] if len(tips) == 1 else None
    audit.update(
        {
            "visible_fact_ids": sorted(str(fact.get("fact_id")) for fact in visible),
            "selected_fact_id": selected.get("fact_id") if selected else None,
            "superseded_visible_fact_ids": sorted(superseded_visible - {""}),
            "selected_as_of": assessment_as_of,
        }
    )
    if audit["chain_status"] != "valid" or len(tips) > 1:
        audit["status"] = "restatement_unresolved"
    elif not exact or not visible:
        audit["status"] = "PIT_unavailable" if exact else "missing_official_fact"
    else:
        audit["status"] = "ready"
    return audit


def _validate_fact(
    fact: dict[str, Any], context: dict[str, Any], entry: dict[str, Any], assessment_as_of: str
) -> tuple[list[str], dict[str, Any]]:
    reasons: list[str] = []
    details: dict[str, Any] = {}
    if fact.get("symbol") != SYMBOL or context.get("symbol") != SYMBOL:
        reasons.append("symbol_mismatch")
    if not _identity_ok(fact):
        reasons.append("fact_identity_invalid")
    if fact.get("context_id") not in {context.get("context_id")}:  # explicit Context join
        reasons.append("context_missing_or_mismatched")
    if context.get("consolidation_scope") != entry["expected_scope"] or fact.get("scope") not in {
        None,
        entry["expected_scope"],
    }:
        reasons.append("scope_mismatch")
    if context.get("accounting_standard") != entry["accounting_standard"] or fact.get(
        "accounting_standard"
    ) not in {None, entry["accounting_standard"]}:
        reasons.append("accounting_standard_mismatch")
    expected_period = entry["period_type"]
    actual_period = (
        "year_end_instant" if context.get("period_type") == "instant" else "annual_duration"
    )
    if actual_period != expected_period:
        reasons.append("period_type_mismatch")
    if _iso(fact.get("period_end")) != _iso(context.get("period_end")):
        reasons.append("period_context_mismatch")
    if entry["period_type"] == "annual_duration":
        if _iso(fact.get("period_end")) != _iso(context.get("period_end")):
            reasons.append("duration_end_mismatch")
        if not _iso(fact.get("period_start")):
            # Facts exported from the repository carry period_start in Context;
            # an absent period start is not inferable for a duration fact.
            reasons.append("duration_start_missing")
    if (
        fact.get("unit") != entry["expected_unit"]
        or fact.get("currency") != entry["expected_currency"]
    ):
        reasons.append("unit_or_currency_mismatch")
    if fact.get("source_type") not in entry["required_source_types"]:
        reasons.append("source_type_not_allowed")
    source_hash = _iso(fact.get("content_sha256"))
    evidence = fact.get("source_evidence") or []
    if not _iso(fact.get("source_id")) or not _iso(fact.get("source_locator")):
        reasons.append("source_identity_missing")
    if fact.get("source_type") == "reconciled_derived":
        official_evidence = [
            row
            for row in evidence
            if row.get("source_type") in {"company_official", "exchange_official"}
            and _iso(row.get("content_sha256"))
        ]
        if len(official_evidence) < 2:
            reasons.append("official_source_hash_evidence_missing")
    elif not source_hash:
        reasons.append("source_content_hash_missing")
    if fact.get("verification_status") not in entry["verification_statuses"]:
        reasons.append("verification_not_allowed")
    if fact.get("eligible_for_metrics") is not True:
        reasons.append("fact_not_eligible")
    available = _date_or_none(fact.get("available_at"))
    as_of = _date_or_none(assessment_as_of)
    if available is None or as_of is None or available > as_of:
        reasons.append("available_at_not_visible")
    details.update(
        {
            "context_id": context.get("context_id"),
            "concept_version": fact.get("concept_version"),
            "period_start": context.get("period_start"),
            "period_end": fact.get("period_end"),
            "period_type": context.get("period_type"),
            "scope": context.get("consolidation_scope"),
            "accounting_standard": context.get("accounting_standard"),
            "unit": fact.get("unit"),
            "currency": fact.get("currency"),
            "source_id": fact.get("source_id"),
            "source_type": fact.get("source_type"),
            "source_tier": fact.get("source_tier"),
            "source_locator": fact.get("source_locator"),
            "content_sha256": fact.get("content_sha256"),
            "source_evidence": fact.get("source_evidence", []),
            "verification_status": fact.get("verification_status"),
            "eligible": fact.get("eligible_for_metrics"),
            "available_at": fact.get("available_at"),
        }
    )
    return sorted(set(reasons)), details


def _status_for_reasons(reasons: list[str], *, exact: bool, visible: bool) -> str:
    if "scope_mismatch" in reasons:
        return "scope_mismatch"
    if any(
        reason in reasons
        for reason in (
            "period_type_mismatch",
            "period_context_mismatch",
            "duration_end_mismatch",
            "duration_start_missing",
        )
    ):
        return "period_mismatch"
    if not exact:
        return "missing_official_fact"
    if not visible or "available_at_not_visible" in reasons:
        return "PIT_unavailable"
    return "missing_official_fact"


def _build_cell(
    *,
    entry: dict[str, Any],
    year: int,
    facts: list[dict[str, Any]],
    contexts: dict[str, dict[str, Any]],
    all_facts: dict[str, dict[str, Any]],
    assessment_as_of: str,
    entries_map: dict[str, dict[str, Any]],
    decisions_map: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    decisions_map = decisions_map or decisions_by_id(load_methodology_decisions())
    base = {
        "symbol": SYMBOL,
        "fiscal_year": year,
        "role_id": entry["role_id"],
        "canonical_concept_id": entry["canonical_concept_id"],
        "input_type": entry["input_type"],
        "status": "not_applicable",
        "reason_codes": [],
        "blocker_severity": entry["blocker_severity"],
        "selected_fact_id": None,
        "candidate_fact_ids": [],
        "context_id": None,
        "concept_version": None,
        "period_start": None,
        "period_end": None,
        "period_type": None,
        "scope": None,
        "accounting_standard": None,
        "unit": None,
        "currency": None,
        "source_id": None,
        "source_type": None,
        "source_tier": None,
        "source_locator": None,
        "content_sha256": None,
        "source_evidence": [],
        "verification_status": None,
        "eligible": None,
        "available_at": None,
        "fact_version": None,
        "restatement_version": None,
        "supersedes_fact_id": None,
        "selected_as_of": assessment_as_of,
        "acquisition_required": False,
        "derivation_status": "not_applicable",
        "methodology_choice_status": "not_applicable",
        "methodology_decision_id": entry.get("methodology_decision_id"),
        "methodology_decision_version": None,
        "methodology_resolution_status": None,
        "decision_rule_digest": None,
        "supporting_fact_roles": [],
        "supporting_fact_statuses": [],
        "unresolved_reasons": [],
        "score_eligible": False,
        "pit_audit": {},
    }
    if entry["input_type"] == "methodology_choice":
        decision_id = entry.get("methodology_decision_id")
        decision = decisions_map.get(str(decision_id), {})
        if not decision_id:
            base["reason_codes"] = ["deprecated_methodology_role_not_applicable"]
            base["methodology_choice_status"] = "not_applicable"
            return base
        supporting_roles = list(decision.get("supporting_fact_roles", []))
        supporting_statuses = []
        for supporting_role in supporting_roles:
            supporting_entry = entries_map.get(supporting_role)
            if supporting_entry is None:
                supporting_statuses.append(
                    {"role_id": supporting_role, "status": "missing_official_fact"}
                )
                continue
            supporting_cell = _build_cell(
                entry=supporting_entry,
                year=year,
                facts=facts,
                contexts=contexts,
                all_facts=all_facts,
                assessment_as_of=assessment_as_of,
                entries_map=entries_map,
                decisions_map=decisions_map,
            )
            supporting_statuses.append(
                {"role_id": supporting_role, "status": supporting_cell["status"]}
            )
        resolution = decision.get("resolution_status", "unresolved")
        unresolved_reasons = []
        if resolution in {"unresolved", "awaiting_supporting_facts"}:
            unresolved_reasons.append(f"decision_resolution_status:{resolution}")
        if not decision.get("decision_version") or not decision.get("decision_rule"):
            unresolved_reasons.append("decision_rule_or_version_missing")
        base.update(
            {
                "methodology_decision_version": decision.get("decision_version"),
                "methodology_resolution_status": resolution,
                "decision_rule_digest": canonical_digest(decision.get("decision_rule", "")),
                "supporting_fact_roles": supporting_roles,
                "supporting_fact_statuses": supporting_statuses,
                "unresolved_reasons": unresolved_reasons,
                "available_at": decision.get("effective_from"),
            }
        )
        if unresolved_reasons:
            base["status"] = "methodology_unresolved"
            base["reason_codes"] = unresolved_reasons
            base["methodology_choice_status"] = "methodology_unresolved"
            base["acquisition_required"] = False
        else:
            base["status"] = "ready"
            base["reason_codes"] = ["methodology_decision_resolved"]
            base["methodology_choice_status"] = "resolved"
        return base
    if entry["input_type"] == "deterministic_derivation":
        component_cells = [
            _build_cell(
                entry=entries_map[component],
                year=year,
                facts=facts,
                contexts=contexts,
                all_facts=all_facts,
                assessment_as_of=assessment_as_of,
                entries_map=entries_map,
                decisions_map=decisions_map,
            )
            for component in entry["derivation_components"]
        ]
        statuses = [cell["status"] for cell in component_cells]
        base["candidate_fact_ids"] = sorted(
            fact_id for cell in component_cells for fact_id in cell["candidate_fact_ids"]
        )
        base["derivation_status"] = (
            "ready" if all(status == "ready" for status in statuses) else "incomplete"
        )
        if all(status == "ready" for status in statuses):
            base["status"] = "ready"
            base["reason_codes"] = ["all_registry_components_ready"]
        elif any(status == "ready" for status in statuses):
            base["status"] = "partially_ready"
            base["reason_codes"] = ["one_or_more_registry_components_unready"]
        else:
            base["status"] = "missing_official_fact"
            base["reason_codes"] = ["registry_components_unready"]
        base["acquisition_required"] = bool(
            entry["required_primary_formula"] and base["status"] != "ready"
        )
        base["component_statuses"] = [
            {"role_id": component, "status": cell["status"]}
            for component, cell in zip(entry["derivation_components"], component_cells, strict=True)
        ]
        return base
    exact = [
        fact
        for fact in facts
        if fact.get("concept_id") == entry["canonical_concept_id"]
        and fact.get("symbol") == SYMBOL
        and _year(contexts.get(str(fact.get("context_id")), {}), fact) == year
    ]
    base["candidate_fact_ids"] = sorted(str(fact.get("fact_id")) for fact in exact)
    if not exact:
        base["status"] = entry["missing_status"]
        base["reason_codes"] = ["canonical_concept_absent_for_fiscal_year"]
        base["acquisition_required"] = bool(entry["required_primary_formula"])
        return base
    valid: list[dict[str, Any]] = []
    mismatches: list[str] = []
    detail_rows: list[dict[str, Any]] = []
    for fact in exact:
        context = contexts.get(str(fact.get("context_id")), {})
        reasons, details = _validate_fact(fact, context, entry, assessment_as_of)
        detail_rows.append(details)
        if not reasons:
            valid.append(fact)
        mismatches.extend(reasons)
    base["reason_codes"] = sorted(set(mismatches))
    base["acquisition_required"] = bool(entry["required_primary_formula"] and not valid)
    base["candidate_fact_ids"] = sorted(str(fact.get("fact_id")) for fact in exact)
    if detail_rows:
        # Preserve all candidate details for audit; top-level fields describe the
        # selected row once a legal PIT tip is found.
        base["candidate_details"] = detail_rows
    pit = select_roic_fact_as_of(
        facts=exact,
        all_facts=all_facts,
        entry=entry,
        fiscal_year=year,
        assessment_as_of=assessment_as_of,
    )
    base["pit_audit"] = pit
    if pit["status"] == "restatement_unresolved":
        base["status"] = "restatement_unresolved"
        return base
    if not valid:
        base["status"] = _status_for_reasons(
            base["reason_codes"], exact=True, visible=bool(pit["visible_fact_ids"])
        )
        return base
    selected_id = pit.get("selected_fact_id")
    selected = next((fact for fact in valid if fact.get("fact_id") == selected_id), None)
    if selected is None:
        base["status"] = "PIT_unavailable"
        base["reason_codes"] = sorted(set(base["reason_codes"] + ["no_valid_visible_tip"]))
        return base
    base.update(
        {
            "status": "ready",
            "selected_fact_id": selected.get("fact_id"),
            "context_id": selected.get("context_id"),
            "concept_version": selected.get("concept_version"),
            "period_start": selected.get("period_start"),
            "period_end": selected.get("period_end"),
            "period_type": selected.get("period_type"),
            "scope": selected.get("scope"),
            "accounting_standard": selected.get("accounting_standard"),
            "unit": selected.get("unit"),
            "currency": selected.get("currency"),
            "source_id": selected.get("source_id"),
            "source_type": selected.get("source_type"),
            "source_tier": selected.get("source_tier"),
            "source_locator": selected.get("source_locator"),
            "content_sha256": selected.get("content_sha256"),
            "source_evidence": selected.get("source_evidence", []),
            "verification_status": selected.get("verification_status"),
            "eligible": selected.get("eligible_for_metrics"),
            "available_at": selected.get("available_at"),
            "fact_version": selected.get("fact_version"),
            "restatement_version": selected.get("restatement_version"),
            "supersedes_fact_id": selected.get("supersedes_fact_id"),
            "reason_codes": [],
        }
    )
    return base


def build_readiness_report(
    *,
    fact_db: Path | None = None,
    inventory_path: Path = INVENTORY_V2_PATH,
    registry_path: Path = REGISTRY_PATH,
    dependency_graph_path: Path = DEPENDENCY_GRAPH_PATH,
    methodology_decisions_path: Path = METHODOLOGY_DECISIONS_PATH,
    assessment_as_of: str = "2026-08-02",
) -> dict[str, Any]:
    """Build a deterministic readiness report; no shadow calculation is run."""
    registry = load_registry(registry_path)
    dependency_graph = load_dependency_graph(dependency_graph_path)
    methodology_decisions = load_methodology_decisions(methodology_decisions_path)
    decisions_map = decisions_by_id(methodology_decisions)
    entries_map = entries_by_role(registry)
    if _date_or_none(assessment_as_of) is None:
        raise ValueError("assessment_as_of must be YYYY-MM-DD")
    if fact_db is not None:
        repository_probe = repository_pit_probe(
            fact_db,
            symbol=registry["symbol"],
            as_of_date=assessment_as_of,
        )
        with tempfile.TemporaryDirectory(prefix="roic_inventory_audit_") as directory:
            path = Path(directory) / "inventory.json"
            export_inventory(fact_db, path, symbol=registry["symbol"])
            inventory = load_inventory(path)
        inventory_source = "explicit_read_only_fact_db"
    else:
        repository_probe = None
        inventory = load_inventory(inventory_path)
        inventory_source = f"committed:{Path(inventory_path).name}"
    facts = list(inventory["facts"])
    contexts = {str(context["context_id"]): context for context in inventory["contexts"]}
    all_facts = {str(fact["fact_id"]): fact for fact in facts}
    matrix = [
        _build_cell(
            entry=entry,
            year=year,
            facts=facts,
            contexts=contexts,
            all_facts=all_facts,
            assessment_as_of=assessment_as_of,
            entries_map=entries_map,
            decisions_map=decisions_map,
        )
        for entry in registry["entries"]
        for year in registry["assessment_years"]
    ]
    blocking_gaps = [
        {
            "fiscal_year": cell["fiscal_year"],
            "role_id": cell["role_id"],
            "canonical_concept_id": cell["canonical_concept_id"],
            "status": cell["status"],
            "reason_codes": cell["reason_codes"],
            "blocker_severity": cell["blocker_severity"],
        }
        for cell in matrix
        if cell["status"] not in {"ready", "not_applicable"}
    ]
    primary_formula_blocking_gaps = [
        gap
        for gap in blocking_gaps
        if entries_by_role(registry)[gap["role_id"]]["required_primary_formula"]
    ]
    coverage_by_year = {}
    for year in registry["assessment_years"]:
        counts = Counter(cell["status"] for cell in matrix if cell["fiscal_year"] == year)
        coverage_by_year[str(year)] = {status: counts.get(status, 0) for status in FORMAL_STATUSES}
    report = {
        "schema": "roic_fact_readiness_report_v2",
        "symbol": registry["symbol"],
        "audit_years": list(registry["assessment_years"]),
        "assessment_as_of": assessment_as_of,
        "inventory_source": inventory_source,
        "inventory_snapshot_sha256": inventory["snapshot_sha256"],
        "inventory_fact_count": inventory["fact_count"],
        "inventory_context_count": inventory["context_count"],
        "repository_pit_probe": repository_probe,
        "registry_logical_path": "config/roic_concept_registry_v2.json",
        "registry_sha256": registry_digest(registry),
        "dependency_graph_logical_path": "config/roic_formula_dependency_graph_v1.json",
        "dependency_graph_sha256": dependency_graph_digest(dependency_graph),
        "methodology_decisions_logical_path": "config/roic_methodology_decisions_v1.json",
        "methodology_decisions_sha256": canonical_digest(methodology_decisions),
        "formula_candidate": registry["formula_candidate"],
        "formula_status": "frozen_primary_candidate_not_production_metric",
        "formal_statuses": list(FORMAL_STATUSES),
        "evidence_gate": "BLOCKED_WITH_EXPLICIT_GAPS"
        if primary_formula_blocking_gaps
        else "SUFFICIENT_FOR_ONE_YEAR_FEASIBILITY",
        "shadow": {
            "status": "NOT_RUN",
            "reason": (
                "direct operating-tax, scope-matched finance and non-operating "
                "asset evidence gate remains readiness-only; no shadow calculation "
                "was executed"
            ),
            "production_metric_created": False,
            "current_value_profile_changed": False,
        },
        "policy_freeze": registry["frozen_methodology"]
        | {
            "forbidden_nopat": [
                "net_profit",
                "net_profit_attributable_to_parent",
                "EBITDA",
                "manual_plug",
                "LLM_inference",
            ],
            "opening_balance": (
                "FY2020 opening is not fabricated; FY2021+ requires prior FY end balance"
            ),
        },
        "coverage_by_year": coverage_by_year,
        "status_summary": dict(sorted(Counter(cell["status"] for cell in matrix).items())),
        "blocking_gaps": blocking_gaps,
        "primary_formula_blocking_gaps": primary_formula_blocking_gaps,
        "matrix": matrix,
    }
    encoded = json.dumps(report, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    report["report_sha256"] = hashlib.sha256(encoded).hexdigest()
    return report


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# PetroChina ROIC official-fact readiness audit v2 (FY2020–FY2025)",
        "",
        f"- Formula candidate: `{report['formula_candidate']}`",
        f"- Assessment as-of: `{report['assessment_as_of']}`",
        f"- Evidence gate: **{report['evidence_gate']}**",
        f"- Shadow: **{report['shadow']['status']}**",
        f"- Registry SHA256: `{report['registry_sha256']}`",
        f"- Canonical inventory SHA256: `{report['inventory_snapshot_sha256']}`",
        "",
        (
            "This is an evidence gate. It does not calculate ROIC, create a Metric "
            "Result, or modify the value profile."
        ),
        "",
        "## Coverage by year",
        "",
        "| FY | Ready | Partial | Missing | Scope | Period | PIT | Restatement | "
        "Methodology | N/A |",
        "|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for year in report["audit_years"]:
        row = report["coverage_by_year"][str(year)]
        lines.append(
            f"| {year} | {row['ready']} | {row['partially_ready']} | "
            f"{row['missing_official_fact']} | {row['scope_mismatch']} | "
            f"{row['period_mismatch']} | {row['PIT_unavailable']} | "
            f"{row['restatement_unresolved']} | {row['methodology_unresolved']} | "
            f"{row['not_applicable']} |"
        )
    lines.extend(["", "## Primary-formula blocking gaps", ""])
    for gap in report["blocking_gaps"]:
        lines.append(
            f"- FY{gap['fiscal_year']} `{gap['role_id']}` / `{gap['canonical_concept_id']}`: "
            f"**{gap['status']}** ({', '.join(gap['reason_codes']) or 'no detail'})"
        )
    if not report["blocking_gaps"]:
        lines.append("- None")
    lines.extend(
        [
            "",
            "## Frozen controls",
            "",
            "- NOPAT is never net profit or parent-attributable profit.",
            "- Invested capital requires opening and closing balances; ending-only "
            "is not computable.",
            "- Cash is purpose-classified; all cash is never silently subtracted.",
            "- PIT selects the latest legal visible chain tip; disconnected chains are unresolved.",
        ]
    )
    return "\n".join(lines) + "\n"


def write_report(report: dict[str, Any], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "petrochina_roic_fact_readiness_2020_2025_v2.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (output_dir / "petrochina_roic_fact_readiness_2020_2025_v2.md").write_text(
        render_markdown(report), encoding="utf-8"
    )


def build_v1_v2_diff(
    v1_path: Path,
    v2_report: dict[str, Any],
    registry_path: Path = REGISTRY_PATH,
) -> dict[str, Any]:
    """Compare the current report with the historical v1 report."""
    old = json.loads(Path(v1_path).read_text(encoding="utf-8"))
    registry = load_registry(registry_path)
    aliases = {
        alias: entry["canonical_concept_id"]
        for entry in registry["entries"]
        for alias in entry["aliases"]
    }
    old_cells = {}
    for cell in old.get("matrix", []):
        concept = str(cell.get("concept_id", ""))
        old_cells[(int(cell["fiscal_year"]), aliases.get(concept, concept))] = cell
    new_cells = {
        (int(cell["fiscal_year"]), str(cell["canonical_concept_id"])): cell
        for cell in v2_report.get("matrix", [])
    }
    changed = []
    for key in sorted(set(old_cells) | set(new_cells)):
        old_cell = old_cells.get(key)
        new_cell = new_cells.get(key)
        old_status = old_cell.get("status") if old_cell else "not_present_in_v1"
        if old_status == "missing_canonical_fact":
            old_status = "missing_official_fact"
        new_status = new_cell.get("status") if new_cell else "not_present_in_v2"
        if old_status != new_status or (
            old_cell
            and new_cell
            and old_cell.get("canonical_fact_ids") != new_cell.get("candidate_fact_ids")
        ):
            changed.append(
                {
                    "fiscal_year": key[0],
                    "canonical_concept_id": key[1],
                    "v1_status": old_status,
                    "v2_status": new_status,
                    "v1_fact_ids": (old_cell or {}).get("canonical_fact_ids", []),
                    "v2_candidate_fact_ids": (new_cell or {}).get("candidate_fact_ids", []),
                }
            )
    diff = {
        "schema": "roic_fact_readiness_v1_to_v2_diff",
        "v1_report": "reports/petrochina_roic_fact_readiness_2020_2025.json",
        "v2_report": "reports/petrochina_roic_fact_readiness_2020_2025_v2.json",
        "v1_schema": old.get("schema"),
        "v2_schema": v2_report.get("schema"),
        "v1_inventory_fact_count": old.get("inventory_fact_count"),
        "v2_inventory_fact_count": v2_report.get("inventory_fact_count"),
        "v1_matrix_cells": len(old.get("matrix", [])),
        "v2_matrix_cells": len(v2_report.get("matrix", [])),
        "changed_cell_count": len(changed),
        "changed_cells": changed,
        "interpretation": (
            "v1 was a presence-only concept audit; v2 adds registry identity, "
            "Context/source evidence, strict period/scope/unit/PIT and legal "
            "restatement-chain fields"
        ),
    }
    diff["diff_sha256"] = hashlib.sha256(
        json.dumps(diff, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return diff


def write_v1_v2_diff(diff: dict[str, Any], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "petrochina_roic_fact_readiness_v1_to_v2_diff.json").write_text(
        json.dumps(diff, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    lines = [
        "# ROIC readiness v1 → v2 diff",
        "",
        f"- v1 matrix cells: `{diff['v1_matrix_cells']}`",
        f"- v2 matrix cells: `{diff['v2_matrix_cells']}`",
        f"- v1 inventory facts: `{diff['v1_inventory_fact_count']}`",
        f"- v2 inventory facts: `{diff['v2_inventory_fact_count']}`",
        f"- changed cells: `{diff['changed_cell_count']}`",
        "",
        diff["interpretation"],
        "",
    ]
    (output_dir / "petrochina_roic_fact_readiness_v1_to_v2_diff.md").write_text(
        "\n".join(lines), encoding="utf-8"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--fact-db", type=Path, help="explicit run-scoped canonical Fact DB (read-only)"
    )
    parser.add_argument("--inventory", type=Path, default=INVENTORY_V2_PATH)
    parser.add_argument("--registry", type=Path, default=REGISTRY_PATH)
    parser.add_argument("--assessment-as-of", default="2026-08-02")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "reports")
    args = parser.parse_args(argv)
    report = build_readiness_report(
        fact_db=args.fact_db,
        inventory_path=args.inventory,
        registry_path=args.registry,
        assessment_as_of=args.assessment_as_of,
    )
    write_report(report, args.output_dir)
    print(
        json.dumps(
            {
                "status": "passed",
                "evidence_gate": report["evidence_gate"],
                "report_sha256": report["report_sha256"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
