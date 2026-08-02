"""Shared ROIC readiness contract and concept-registry validation.

The registry is the only naming authority for the Stage 2I.1R audit.  This
module intentionally contains no metric or valuation calculation.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
REGISTRY_PATH = ROOT / "config" / "roic_concept_registry_v1.json"
FORMAL_STATUSES = (
    "ready",
    "partially_ready",
    "missing_official_fact",
    "scope_mismatch",
    "period_mismatch",
    "PIT_unavailable",
    "restatement_unresolved",
    "methodology_unresolved",
    "not_applicable",
)
INPUT_TYPES = ("direct_fact", "deterministic_derivation", "methodology_choice")
PERIOD_TYPES = ("annual_duration", "year_end_instant", "opening_instant")


def load_registry(path: Path | str = REGISTRY_PATH) -> dict[str, Any]:
    registry = json.loads(Path(path).read_text(encoding="utf-8"))
    validate_registry(registry)
    return registry


def validate_registry(registry: dict[str, Any]) -> None:
    """Validate schema, identity uniqueness, aliases and derivation edges."""
    if registry.get("schema") != "roic_concept_registry_v1":
        raise ValueError("unsupported ROIC concept registry schema")
    if not registry.get("symbol") or not registry.get("assessment_years"):
        raise ValueError("registry symbol and assessment_years are required")
    if tuple(registry.get("allowed_statuses", ())) != FORMAL_STATUSES:
        raise ValueError("registry status vocabulary must be the nine formal statuses")
    entries = registry.get("entries")
    if not isinstance(entries, list) or not entries:
        raise ValueError("registry entries must be a non-empty list")
    required = {
        "role_id",
        "canonical_concept_id",
        "concept_version_requirement",
        "display_name",
        "formula_candidate",
        "analytical_side",
        "input_type",
        "period_type",
        "expected_scope",
        "accounting_standard",
        "expected_unit",
        "expected_currency",
        "required_source_types",
        "verification_statuses",
        "eligible",
        "required_primary_formula",
        "required_shadow",
        "required_secondary",
        "fy2020_opening_policy",
        "derivation_components",
        "aliases",
        "forbidden_approximates",
        "missing_status",
        "blocker_severity",
        "acquisition_priority",
    }
    roles: set[str] = set()
    concepts: set[str] = set()
    aliases: set[str] = set()
    for entry in entries:
        missing = sorted(required - set(entry))
        if missing:
            raise ValueError(f"registry entry {entry.get('role_id')} missing {missing}")
        role = str(entry["role_id"])
        concept = str(entry["canonical_concept_id"])
        if role in roles or concept in concepts:
            raise ValueError(f"registry role/concept is not unique: {role}/{concept}")
        roles.add(role)
        concepts.add(concept)
        if entry["input_type"] not in INPUT_TYPES:
            raise ValueError(f"unsupported input_type for {role}")
        if entry["period_type"] not in PERIOD_TYPES:
            raise ValueError(f"unsupported period_type for {role}")
        if entry["missing_status"] not in FORMAL_STATUSES:
            raise ValueError(f"unsupported missing_status for {role}")
        if not isinstance(entry["eligible"], bool) or not isinstance(entry["aliases"], list):
            raise ValueError(f"invalid registry types for {role}")
        for alias in entry["aliases"]:
            if alias in aliases or alias in concepts:
                raise ValueError(f"registry alias collides with canonical concept: {alias}")
            aliases.add(alias)
    for entry in entries:
        for component in entry["derivation_components"]:
            if component not in roles and component not in concepts:
                raise ValueError(
                    f"derivation component {component} for {entry['role_id']} is not registered"
                )


def entries_by_role(registry: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {str(entry["role_id"]): entry for entry in registry["entries"]}


def entries_by_concept(registry: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {str(entry["canonical_concept_id"]): entry for entry in registry["entries"]}


def registry_digest(registry: dict[str, Any]) -> str:
    payload = json.dumps(registry, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def validate_registry_references(
    registry: dict[str, Any], references: list[dict[str, Any]]
) -> None:
    """Reject contract/config records that use an unregistered ROIC role."""
    roles = set(entries_by_role(registry))
    concepts = set(entries_by_concept(registry))
    for record in references:
        role = record.get("role_id")
        concept = record.get("canonical_concept_id")
        if role is not None and role not in roles:
            raise ValueError(f"unregistered ROIC role reference: {role}")
        if concept is not None and concept not in concepts:
            raise ValueError(f"unregistered ROIC concept reference: {concept}")


def validate_acquisition_plan(registry: dict[str, Any], plan: dict[str, Any]) -> None:
    """Validate that the minimum plan is a bounded registry-driven batch."""
    if plan.get("schema") != "roic_official_fact_acquisition_plan_v2":
        raise ValueError("unsupported ROIC acquisition plan schema")
    if plan.get("symbol") != registry.get("symbol"):
        raise ValueError("acquisition plan symbol does not match registry")
    roles = entries_by_role(registry)
    layers = plan.get("layers", {})
    expected_layers = {
        "A_primary_formula_hard_blockers",
        "B_scope_matching_hard_blockers",
        "C_secondary_reconciliation_or_sensitivity",
    }
    if set(layers) != expected_layers:
        raise ValueError("acquisition plan must contain exactly the three required layers")
    for layer, items in layers.items():
        if not isinstance(items, list) or not items:
            raise ValueError(f"acquisition layer is empty: {layer}")
        for item in items:
            role = item.get("role_id")
            if role not in roles:
                raise ValueError(f"acquisition item uses unregistered role: {role}")
            entry = roles[role]
            if item.get("canonical_concept_id") != entry["canonical_concept_id"]:
                raise ValueError(f"acquisition concept drift for {role}")
            if any(int(year) not in {2023, 2024} for year in item.get("affected_fiscal_years", [])):
                raise ValueError(f"minimum acquisition item is outside FY2023/FY2024: {role}")
            if (
                layer == "A_primary_formula_hard_blockers"
                and item.get("blocker_severity") != "hard"
            ):
                raise ValueError(f"primary item is not hard-blocked: {role}")
