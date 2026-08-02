"""ROIC formula, registry, methodology and acquisition-gate contracts.

This module validates contracts only. It never acquires a Fact, calculates
ROIC, registers a Metric or writes the default database.
"""

from __future__ import annotations

import hashlib
import json
import re
from copy import deepcopy
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
REGISTRY_V1_PATH = ROOT / "config" / "roic_concept_registry_v1.json"
REGISTRY_PATH = ROOT / "config" / "roic_concept_registry_v2.json"
DEPENDENCY_GRAPH_PATH = ROOT / "config" / "roic_formula_dependency_graph_v1.json"
METHODOLOGY_DECISIONS_PATH = ROOT / "config" / "roic_methodology_decisions_v1.json"
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
FORMULA_MEMBERSHIPS = ("primary", "scope_matching", "secondary", "excluded")
ACQUISITION_BEHAVIORS = (
    "acquire_direct_fact",
    "derive_after_components",
    "resolve_methodology",
    "no_acquisition",
)
CONTRIBUTIONS = (
    "nopat_bridge",
    "operating_tax",
    "opening_invested_capital",
    "closing_invested_capital",
    "non_operating_asset_deduction",
    "scope_matching",
    "secondary_reconciliation",
)


def canonical_digest(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def load_dependency_graph(path: Path | str = DEPENDENCY_GRAPH_PATH) -> dict[str, Any]:
    graph = json.loads(Path(path).read_text(encoding="utf-8"))
    validate_dependency_graph(graph)
    return graph


def dependency_graph_digest(graph: dict[str, Any]) -> str:
    return canonical_digest(graph)


def validate_dependency_graph(graph: dict[str, Any]) -> None:
    if graph.get("schema") != "roic_formula_dependency_graph_v1":
        raise ValueError("unsupported ROIC dependency graph schema")
    required = {
        "role_id",
        "contribution_to",
        "dependency_type",
        "required_for_primary_formula",
        "required_for_shadow_year",
        "required_for_secondary_only",
        "parent_role_id",
        "included_in_parent",
        "contribution_sign",
        "double_count_exclusion_roles",
        "required_fiscal_years",
        "resolution_status",
        "rationale",
        "source_reference",
        "version",
    }
    nodes = graph.get("nodes")
    if not isinstance(nodes, list) or not nodes:
        raise ValueError("dependency graph nodes are required")
    roles: set[str] = set()
    for node in nodes:
        missing = sorted(required - set(node))
        if missing:
            raise ValueError(f"dependency node {node.get('role_id')} missing {missing}")
        role = str(node["role_id"])
        if role in roles:
            raise ValueError(f"duplicate dependency node: {role}")
        roles.add(role)
        if node["contribution_to"] not in CONTRIBUTIONS:
            raise ValueError(f"invalid contribution_to for {role}")
        if node["dependency_type"] not in {
            "independent_input",
            "component_of",
            "deterministic_derivation",
            "methodology_decision",
            "supporting_evidence",
        }:
            raise ValueError(f"invalid dependency_type for {role}")
        if node["contribution_sign"] not in {-1, 0, 1}:
            raise ValueError(f"invalid contribution sign for {role}")
        if node["included_in_parent"] != bool(node["parent_role_id"]):
            raise ValueError(f"parent inclusion mismatch for {role}")
        if node["required_for_primary_formula"] and node["required_for_secondary_only"]:
            raise ValueError(f"primary/secondary overlap for {role}")
    by_role = {node["role_id"]: node for node in nodes}
    for node in nodes:
        role = node["role_id"]
        parent = node["parent_role_id"]
        if parent and parent not in by_role:
            raise ValueError(f"unknown parent for {role}: {parent}")
        for excluded in node["double_count_exclusion_roles"]:
            if excluded not in by_role:
                raise ValueError(f"unknown double-count role for {role}: {excluded}")
        if node["included_in_parent"] and node["contribution_sign"] == 0:
            raise ValueError(f"included component must preserve its composition sign: {role}")
    finance = by_role.get("nopat.finance_cost_adjustment", {})
    lease = by_role.get("nopat.lease_interest_expense", {})
    composition = graph.get("finance_lease_composition", {})
    mode = composition.get("mode")
    if mode == "lease_included_in_composite":
        if finance.get("dependency_type") != "deterministic_derivation":
            raise ValueError("finance-cost adjustment must be a deterministic composite")
        if lease.get("parent_role_id") != "nopat.finance_cost_adjustment":
            raise ValueError("lease interest must be included in finance-cost adjustment")
        if composition.get("final_formula_contribution_roles") != ["nopat.finance_cost_adjustment"]:
            raise ValueError("finance composite must be the sole formula contribution")
    elif mode == "lease_excluded_and_independent":
        if lease.get("parent_role_id") is not None or lease.get("included_in_parent"):
            raise ValueError("excluded lease interest must be independent")
        if not lease.get("required_for_primary_formula"):
            raise ValueError("excluded lease interest must remain primary")
        if sorted(composition.get("final_formula_contribution_roles", [])) != sorted(
            ["nopat.finance_cost_adjustment", "nopat.lease_interest_expense"]
        ):
            raise ValueError("excluded lease interest must contribute independently")
    else:
        raise ValueError("finance/lease composition mode must be explicit")
    if lease.get("contribution_sign") != 1 or finance.get("contribution_sign") != 1:
        raise ValueError("finance/lease composition sign mismatch")
    if not composition.get("source_note_requirements") or not composition.get(
        "missing_component_behavior"
    ):
        raise ValueError("finance/lease source-note and missing-component rules are required")


def load_methodology_decisions(
    path: Path | str = METHODOLOGY_DECISIONS_PATH,
) -> dict[str, Any]:
    contract = json.loads(Path(path).read_text(encoding="utf-8"))
    if contract.get("schema") != "roic_methodology_decisions_v1":
        raise ValueError("unsupported methodology-decision schema")
    decisions = contract.get("decisions", [])
    ids: set[str] = set()
    for decision in decisions:
        required = {
            "decision_id",
            "decision_version",
            "resolution_status",
            "decision_rule",
            "supporting_fact_roles",
            "excluded_fact_roles",
            "classification_rules",
            "fallback_behavior",
            "limitations",
            "effective_from",
            "references",
        }
        if required - set(decision):
            raise ValueError(f"incomplete methodology decision: {decision.get('decision_id')}")
        decision_id = str(decision["decision_id"])
        if decision_id in ids:
            raise ValueError(f"duplicate methodology decision: {decision_id}")
        ids.add(decision_id)
        if decision["resolution_status"] not in {
            "resolved",
            "awaiting_supporting_facts",
            "unresolved",
        }:
            raise ValueError(f"invalid methodology status: {decision_id}")
        if not decision["decision_version"] or not decision["decision_rule"]:
            raise ValueError(f"decision rule/version required: {decision_id}")
    return contract


def decisions_by_id(contract: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {str(item["decision_id"]): item for item in contract["decisions"]}


def _materialize_v2(raw: dict[str, Any], path: Path) -> dict[str, Any]:
    migration = raw.get("migration", {})
    base_path = ROOT / migration.get("base_registry", "")
    if not base_path.is_file():
        raise ValueError("registry v2 base registry is missing")
    base = json.loads(base_path.read_text(encoding="utf-8"))
    registry = deepcopy(base)
    registry["schema"] = "roic_concept_registry_v2"
    registry["version"] = str(raw.get("version", "2"))
    registry["logical_path"] = path.relative_to(ROOT).as_posix()
    registry["migration"] = migration
    overrides = raw.get("entry_overrides", {})
    for entry in registry["entries"]:
        entry.update(deepcopy(overrides.get(entry["role_id"], {})))
    registry["entries"].extend(deepcopy(raw.get("new_entries", [])))
    graph = load_dependency_graph()
    graph_nodes = {node["role_id"]: node for node in graph["nodes"]}
    for entry in registry["entries"]:
        role = entry["role_id"]
        node = graph_nodes.get(role)
        if node is None:
            raise ValueError(f"registry role absent from dependency graph: {role}")
        entry["required_primary_formula"] = node["required_for_primary_formula"]
        entry["required_shadow"] = node["required_for_shadow_year"]
        entry["required_secondary"] = node["required_for_secondary_only"]
        entry["contribution_to"] = node["contribution_to"]
        if node["dependency_type"] == "deterministic_derivation":
            entry["input_type"] = "deterministic_derivation"
        elif node["dependency_type"] == "methodology_decision":
            entry["input_type"] = "methodology_choice"
        if node["contribution_to"] == "scope_matching":
            membership = "scope_matching"
        elif node["required_for_secondary_only"]:
            membership = "secondary"
        elif node["required_for_primary_formula"]:
            membership = "primary"
        else:
            membership = "excluded"
        entry["formula_membership"] = membership
        if entry["input_type"] == "deterministic_derivation":
            behavior = "derive_after_components"
        elif entry["input_type"] == "methodology_choice":
            behavior = "resolve_methodology"
        elif membership == "excluded":
            behavior = "no_acquisition"
        else:
            behavior = "acquire_direct_fact"
        entry["acquisition_behavior"] = behavior
        entry["included_in_role_id"] = node["parent_role_id"]
        entry["independent_formula_contribution"] = bool(
            node["contribution_sign"] and not node["included_in_parent"]
        )
        entry["contribution_sign"] = node["contribution_sign"]
        entry["decision_status_required"] = (
            "resolved" if entry["input_type"] == "methodology_choice" else None
        )
        entry.setdefault("methodology_decision_id", None)
        if entry["required_primary_formula"] and entry["blocker_severity"] not in {
            "hard",
            "scope",
        }:
            entry["blocker_severity"] = "hard"
    registry["dependency_graph_sha256"] = dependency_graph_digest(graph)
    registry["methodology_decisions_sha256"] = canonical_digest(load_methodology_decisions())
    return registry


def load_registry(path: Path | str = REGISTRY_PATH) -> dict[str, Any]:
    resolved = Path(path).resolve()
    raw = json.loads(resolved.read_text(encoding="utf-8"))
    registry = (
        _materialize_v2(raw, resolved) if raw.get("schema") == "roic_concept_registry_v2" else raw
    )
    validate_registry(registry)
    return registry


def validate_registry(registry: dict[str, Any]) -> None:
    """Validate identity, dependency, formula membership and acquisition rules."""
    if registry.get("schema") not in {"roic_concept_registry_v1", "roic_concept_registry_v2"}:
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
    if registry["schema"] == "roic_concept_registry_v2":
        required |= {
            "acquisition_behavior",
            "formula_membership",
            "included_in_role_id",
            "independent_formula_contribution",
            "decision_status_required",
            "methodology_decision_id",
            "contribution_to",
            "contribution_sign",
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
        if entry["input_type"] not in INPUT_TYPES or entry["period_type"] not in PERIOD_TYPES:
            raise ValueError(f"unsupported registry type for {role}")
        if entry["missing_status"] not in FORMAL_STATUSES:
            raise ValueError(f"unsupported missing_status for {role}")
        if entry["required_primary_formula"] and entry["required_secondary"]:
            raise ValueError(f"role cannot be both primary and secondary: {role}")
        if not isinstance(entry["eligible"], bool) or not isinstance(entry["aliases"], list):
            raise ValueError(f"invalid registry types for {role}")
        if registry["schema"] == "roic_concept_registry_v2":
            if entry["formula_membership"] not in FORMULA_MEMBERSHIPS:
                raise ValueError(f"invalid formula membership for {role}")
            if entry["acquisition_behavior"] not in ACQUISITION_BEHAVIORS:
                raise ValueError(f"invalid acquisition behavior for {role}")
            if (
                entry["input_type"] == "deterministic_derivation"
                and entry["acquisition_behavior"] != "derive_after_components"
            ):
                raise ValueError(f"derivation cannot be directly acquired: {role}")
            if (
                entry["input_type"] == "methodology_choice"
                and entry["acquisition_behavior"] != "resolve_methodology"
            ):
                raise ValueError(f"methodology choice cannot be directly acquired: {role}")
            if entry["included_in_role_id"] and entry["independent_formula_contribution"]:
                raise ValueError(f"composite component contributes independently: {role}")
        for alias in entry["aliases"]:
            if alias in aliases or alias in concepts:
                raise ValueError(f"registry alias collides with canonical concept: {alias}")
            aliases.add(alias)
    for entry in entries:
        for component in entry["derivation_components"]:
            if component not in roles and component not in concepts:
                raise ValueError(
                    f"unknown derivation component for {entry['role_id']}: {component}"
                )
    if registry["schema"] == "roic_concept_registry_v2":
        graph = load_dependency_graph()
        if registry.get("dependency_graph_sha256") != dependency_graph_digest(graph):
            raise ValueError("registry dependency-graph digest mismatch")
        graph_roles = {node["role_id"] for node in graph["nodes"]}
        if roles != graph_roles:
            raise ValueError("registry and dependency graph role sets differ")


def entries_by_role(registry: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {str(entry["role_id"]): entry for entry in registry["entries"]}


def entries_by_concept(registry: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {str(entry["canonical_concept_id"]): entry for entry in registry["entries"]}


def registry_digest(registry: dict[str, Any]) -> str:
    return canonical_digest(registry)


def validate_registry_references(
    registry: dict[str, Any], references: list[dict[str, Any]]
) -> None:
    roles = set(entries_by_role(registry))
    concepts = set(entries_by_concept(registry))
    for record in references:
        if record.get("role_id") is not None and record["role_id"] not in roles:
            raise ValueError(f"unregistered ROIC role reference: {record['role_id']}")
        if (
            record.get("canonical_concept_id") is not None
            and record["canonical_concept_id"] not in concepts
        ):
            raise ValueError(
                f"unregistered ROIC concept reference: {record['canonical_concept_id']}"
            )


def _validate_v2_plan(registry: dict[str, Any], plan: dict[str, Any]) -> dict[str, Any]:
    """Historical Stage 2I.1R validation retained for reproducibility."""
    if plan.get("symbol") != registry.get("symbol"):
        raise ValueError("acquisition plan symbol does not match registry")
    roles = entries_by_role(registry)
    expected = {
        "A_primary_formula_hard_blockers",
        "B_scope_matching_hard_blockers",
        "C_secondary_reconciliation_or_sensitivity",
    }
    if set(plan.get("layers", {})) != expected:
        raise ValueError("historical plan must contain its three layers")
    for layer, items in plan["layers"].items():
        if not isinstance(items, list) or not items:
            raise ValueError(f"historical acquisition layer is empty: {layer}")
        for item in items:
            role = item.get("role_id")
            if role not in roles:
                raise ValueError(f"acquisition item uses unregistered role: {role}")
            if item.get("canonical_concept_id") != roles[role]["canonical_concept_id"]:
                raise ValueError(f"acquisition concept drift for {role}")
            if any(int(year) not in {2023, 2024} for year in item["affected_fiscal_years"]):
                raise ValueError(f"historical minimum plan is out of range: {role}")
    return {"validation_status": "HISTORICAL_CONTRACT_ONLY"}


def _expected_layer(node: dict[str, Any], entry: dict[str, Any]) -> str:
    if node["contribution_to"] == "scope_matching":
        return "B_scope_matching_direct_fact_blockers"
    if entry.get("methodology_decision_id") or node["contribution_to"] == (
        "non_operating_asset_deduction"
    ):
        return "C_methodology_supporting_facts"
    if node["required_for_primary_formula"]:
        return "A_primary_formula_direct_fact_blockers"
    return "D_secondary_reconciliation_or_sensitivity"


def validate_acquisition_plan(
    registry: dict[str, Any],
    plan: dict[str, Any],
    dependency_graph: dict[str, Any] | None = None,
    readiness_report: dict[str, Any] | None = None,
    *,
    target_year: int = 2024,
    opening_year: int = 2023,
) -> dict[str, Any]:
    """Return complete plan coverage diagnostics; never stop at the first defect."""
    if plan.get("schema") == "roic_official_fact_acquisition_plan_v2":
        return _validate_v2_plan(registry, plan)
    graph = dependency_graph or load_dependency_graph()
    readiness = readiness_report or {}
    roles = entries_by_role(registry)
    nodes = {node["role_id"]: node for node in graph["nodes"]}
    expected_layers = {
        "A_primary_formula_direct_fact_blockers",
        "B_scope_matching_direct_fact_blockers",
        "C_methodology_supporting_facts",
        "D_secondary_reconciliation_or_sensitivity",
    }
    uncovered: list[dict[str, Any]] = []
    orphan: list[dict[str, Any]] = []
    mislayered: list[dict[str, Any]] = []
    duplicated: list[dict[str, Any]] = []
    covered: list[dict[str, Any]] = []
    methodology_dependencies: list[dict[str, Any]] = []
    ready_not_acquired: list[dict[str, Any]] = []
    layers = plan.get("layers", {})
    if set(layers) != expected_layers:
        mislayered.append({"reason": "layer_set_mismatch", "actual": sorted(layers)})
    items = [dict(item, layer=layer) for layer, rows in layers.items() for item in rows]
    matrix = {
        (cell["role_id"], int(cell["fiscal_year"])): cell for cell in readiness.get("matrix", [])
    }
    item_keys: dict[tuple[str, int], list[dict[str, Any]]] = {}
    acquisition_ids: set[str] = set()
    required_item_fields = {
        "acquisition_id",
        "role_id",
        "canonical_concept_id",
        "dependency_graph_node",
        "affected_fiscal_years",
        "period_type",
        "expected_scope",
        "statement_or_note",
        "exact_locator_requirement",
        "source_type",
        "source_content_hash_requirement",
        "expected_unit",
        "expected_currency",
        "context_shape",
        "available_at_rule",
        "fact_identity_shape",
        "restatement_behavior",
        "extraction_rule",
        "dual_source_rule",
        "downstream_formula_contribution",
        "included_in_parent_role",
        "double_count_guard",
        "expected_readiness_transition",
        "blocker_severity",
        "acceptance_criteria",
    }
    for item in items:
        role = str(item.get("role_id", ""))
        missing_fields = sorted(required_item_fields - set(item))
        if missing_fields:
            orphan.append(
                {"role_id": role, "reason": "missing_item_fields", "fields": missing_fields}
            )
        if item.get("acquisition_id") in acquisition_ids:
            duplicated.append({"role_id": role, "reason": "duplicate_acquisition_id"})
        acquisition_ids.add(str(item.get("acquisition_id")))
        if role not in roles or role not in nodes:
            orphan.append({"role_id": role, "reason": "unknown_role"})
            continue
        entry = roles[role]
        node = nodes[role]
        if item.get("canonical_concept_id") != entry["canonical_concept_id"]:
            orphan.append({"role_id": role, "reason": "canonical_concept_mismatch"})
        if item.get("dependency_graph_node") != role:
            orphan.append({"role_id": role, "reason": "dependency_node_mismatch"})
        if entry["input_type"] != "direct_fact":
            orphan.append({"role_id": role, "reason": f"{entry['input_type']}_cannot_be_acquired"})
        expected_layer = _expected_layer(node, entry)
        if item["layer"] != expected_layer:
            mislayered.append(
                {"role_id": role, "actual_layer": item["layer"], "expected_layer": expected_layer}
            )
        years = [int(year) for year in item.get("affected_fiscal_years", [])]
        if not years or any(year not in {opening_year, target_year} for year in years):
            orphan.append({"role_id": role, "reason": "year_outside_minimum_batch"})
        expected_years = (
            [target_year]
            if entry["period_type"] == "annual_duration"
            else [opening_year, target_year]
        )
        if years != expected_years:
            mislayered.append(
                {
                    "role_id": role,
                    "reason": "opening_closing_or_duration_year_mismatch",
                    "expected_years": expected_years,
                    "actual_years": years,
                }
            )
        for year in years:
            item_keys.setdefault((role, year), []).append(item)
            cell = matrix.get((role, year))
            if cell and cell["status"] == "ready" and not item.get("reacquisition_justification"):
                orphan.append({"role_id": role, "fiscal_year": year, "reason": "already_ready"})
    for key, matching in item_keys.items():
        if len(matching) > 1:
            duplicated.append(
                {"role_id": key[0], "fiscal_year": key[1], "reason": "duplicate_role_year"}
            )
    for item in items:
        role = item.get("role_id")
        if role not in nodes:
            continue
        parent = nodes[role]["parent_role_id"]
        if parent and any(other.get("role_id") == parent for other in items):
            duplicated.append(
                {
                    "role_id": role,
                    "parent_role_id": parent,
                    "reason": "parent_and_component_acquired",
                }
            )

    decisions = decisions_by_id(load_methodology_decisions())

    def is_covered(role: str, year: int, stack: tuple[str, ...] = ()) -> bool:
        if role in stack:
            return False
        entry = roles[role]
        cell = matrix.get((role, year), {})
        if entry["input_type"] == "methodology_choice":
            decision = decisions.get(entry.get("methodology_decision_id", ""), {})
            methodology_dependencies.append(
                {
                    "role_id": role,
                    "fiscal_year": year,
                    "resolution_status": decision.get("resolution_status"),
                    "supporting_fact_roles": decision.get("supporting_fact_roles", []),
                }
            )
            return bool(
                decision.get("resolution_status") == "resolved"
                and decision.get("decision_rule")
                and decision.get("decision_version")
            )
        if cell.get("status") in {"ready", "not_applicable"}:
            return True
        if entry["input_type"] == "direct_fact":
            return (role, year) in item_keys
        return all(
            is_covered(component, year, (*stack, role))
            for component in entry["derivation_components"]
        )

    for role, node in nodes.items():
        if not node["required_for_primary_formula"]:
            continue
        for year in node["required_fiscal_years"]:
            if year not in {opening_year, target_year}:
                continue
            if is_covered(role, year):
                covered.append({"role_id": role, "fiscal_year": year})
            else:
                uncovered.append({"role_id": role, "fiscal_year": year})
    decision = decisions["policy.non_operating_asset_classification"]
    for role in decision["supporting_fact_roles"]:
        if role not in roles:
            uncovered.append({"role_id": role, "reason": "supporting_role_not_registered"})
            continue
        for year in (
            [target_year]
            if roles[role]["period_type"] == "annual_duration"
            else [opening_year, target_year]
        ):
            cell = matrix.get((role, year), {})
            if cell.get("status") == "ready":
                ready_not_acquired.append({"role_id": role, "fiscal_year": year})
            elif (role, year) not in item_keys:
                uncovered.append(
                    {
                        "role_id": role,
                        "fiscal_year": year,
                        "reason": "methodology_supporting_fact_uncovered",
                    }
                )

    digest_errors = []
    expected_registry_digest = registry_digest(registry)
    expected_graph_digest = dependency_graph_digest(graph)
    expected_readiness_digest = readiness.get("report_sha256")
    if plan.get("registry_sha256") != expected_registry_digest:
        digest_errors.append("registry_digest_mismatch")
    if plan.get("dependency_graph_sha256") != expected_graph_digest:
        digest_errors.append("dependency_graph_digest_mismatch")
    if plan.get("readiness_report_sha256") != expected_readiness_digest:
        digest_errors.append("readiness_report_digest_mismatch")
    orphan.extend({"reason": reason} for reason in digest_errors)
    status = "PASS" if not (uncovered or orphan or mislayered or duplicated) else "FAIL"
    payload = deepcopy(plan)
    payload.pop("plan_digest", None)
    computed_plan_digest = canonical_digest(payload)
    declared_plan_digest = plan.get("plan_digest")
    if declared_plan_digest not in {
        None,
        "pending_validator_canonical_digest",
        computed_plan_digest,
    }:
        orphan.append({"reason": "plan_digest_mismatch"})
        status = "FAIL"
    return {
        "schema": "roic_acquisition_plan_coverage_v1",
        "validation_status": status,
        "target_year": target_year,
        "opening_year": opening_year,
        "covered_blockers": sorted(covered, key=lambda row: (row["role_id"], row["fiscal_year"])),
        "uncovered_blockers": uncovered,
        "orphan_items": orphan,
        "mislayered_items": mislayered,
        "duplicated_contributions": duplicated,
        "methodology_dependencies": methodology_dependencies,
        "ready_roles_not_acquired": ready_not_acquired,
        "registry_sha256": expected_registry_digest,
        "dependency_graph_sha256": expected_graph_digest,
        "readiness_report_sha256": expected_readiness_digest,
        "plan_digest": computed_plan_digest,
        "next_stage_acquisition": "ALLOWED" if status == "PASS" else "NOT_ALLOWED",
    }


_ABSOLUTE_PATH_PATTERNS = (
    re.compile(r"(?i)(?:^|[\s\"'])(?:[a-z]:[\\/])"),
    re.compile(r"(?i)(?:^|[\s\"'])(?:/home/|/users/|/tmp/|/var/tmp/|\\users\\)"),
    re.compile(r"(?i)(?:^|[\s\"'])(?:\\\\[^\\\s]+\\)"),
)


def find_absolute_path_leaks(
    text: str, *, current_working_directory: str | None = None
) -> list[str]:
    leaks = [pattern.pattern for pattern in _ABSOLUTE_PATH_PATTERNS if pattern.search(text)]
    if current_working_directory:
        normalized = current_working_directory.replace("\\", "/")
        if current_working_directory in text or normalized in text:
            leaks.append("current_working_directory")
    return leaks
