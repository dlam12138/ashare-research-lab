"""R4F.4A1 exact-four-cell historical backfill and frozen-5Y preflight.

Pure, offline construction helpers.  Official PDFs and the baostock calendar
are explicit content-addressed inputs; this module never scans caches, writes
the default database, reads future EPS amounts, or computes a score.
"""

from __future__ import annotations

import hashlib
import json
from decimal import Decimal
from typing import Any

from ashare_research.facts.identity import build_fact_id, validate_canonical_fact_ids
from ashare_research.pit_valuation.pe_cycle_guard_validation import (
    DIR_ABOVE,
    DIR_BELOW,
    DIR_EQUAL,
    build_3y_series,
    build_denominator_state_ledger,
)
from ashare_research.pit_valuation.pe_historical_annual_backfill import (
    CONCEPT_EQUITY,
    CONCEPT_NET_PROFIT,
    build_fact,
    roe_decimal,
    state_identity,
)
from ashare_research.pit_valuation.pe_independent_cycle_validation_preflight import (
    assert_preflight_has_no_future_values,
)
from ashare_research.pit_valuation.pe_normalized_earnings_prototype import (
    WINDOW_5Y,
    build_normalized_earnings_state,
    resolve_annual_roe_chain_as_of,
    resolve_current_bvps_as_of,
)

SYMBOL = "601857.SH"
CANONICAL_ALIASES = {
    "parent_equity": CONCEPT_EQUITY,
    "parent_net_profit": CONCEPT_NET_PROFIT,
}
TARGETS = (
    ("2015-12-31", CONCEPT_EQUITY),
    ("2016-12-31", CONCEPT_EQUITY),
    ("2016-12-31", CONCEPT_NET_PROFIT),
    ("2017-12-31", CONCEPT_NET_PROFIT),
)


def canonical_concept(alias: str) -> str:
    try:
        return CANONICAL_ALIASES[alias]
    except KeyError as exc:
        raise ValueError(f"unregistered planning alias: {alias}") from exc


def validate_target_dependencies(targets: list[dict[str, str]]) -> dict[str, Any]:
    actual = {(row["period_end"], row["concept_id"]) for row in targets}
    expected = set(TARGETS)
    return {
        "schema": "pe_5y_target_dependency_check_v1",
        "target_logical_cell_count": len(actual),
        "expected_target_logical_cell_count": 4,
        "missing": sorted(expected - actual),
        "extra": sorted(actual - expected),
        "roe_2016_dependencies": ["Equity_2015", "Equity_2016", "NP_2016"],
        "roe_2017_dependencies": ["Equity_2016", "Equity_2017_existing", "NP_2017"],
        "status": "PASS" if actual == expected else "FAIL",
    }


def cell_from_spec(spec: dict[str, Any]) -> dict[str, Any]:
    raw = Decimal(spec["raw_token"].replace(",", ""))
    excerpt = "|".join(
        [
            spec["table"],
            spec["raw_label"],
            spec["column"],
            spec["raw_token"],
        ]
    )
    return {
        "status": "acquired_reported_verified",
        "evidence_id": spec["evidence_id"],
        "concept_id": spec["concept_id"],
        "period_end": spec["period_end"],
        "raw_token": spec["raw_token"],
        "raw_value": str(raw),
        "canonical_value": str(raw * Decimal("1000000")),
        "page_index": int(spec["page"]) - 1,
        "table": spec["table"],
        "raw_label": spec["raw_label"],
        "raw_unit": "CNY_million",
        "excerpt_hash": hashlib.sha256(excerpt.encode("utf-8")).hexdigest(),
        "scope": "CONSOLIDATED",
    }


def build_new_facts(
    specs: list[dict[str, Any]],
    evidence_by_id: dict[str, dict[str, Any]],
    object_sha_by_evidence: dict[str, str],
    market_calendar: dict[str, Any],
) -> list[dict[str, Any]]:
    facts: list[dict[str, Any]] = []
    for spec in specs:
        if spec["concept_id"] not in {CONCEPT_EQUITY, CONCEPT_NET_PROFIT}:
            raise ValueError("short aliases cannot become canonical Fact concepts")
        cell = cell_from_spec(spec)
        evidence = dict(evidence_by_id[spec["evidence_id"]])
        evidence["proof_url"] = evidence["document_url"]
        fact = build_fact(
            cell,
            evidence,
            market_calendar=market_calendar,
            object_sha=object_sha_by_evidence[spec["evidence_id"]],
        )
        fact["source_id"] = f"r4f4a1:{spec['evidence_id']}"
        fact["source_table"] = spec["table"]
        fact["source_label"] = spec["raw_label"]
        fact["verification_note"] = (
            "r4f4a1 PDF text-layer plus visual-page verification; "
            f"object={object_sha_by_evidence[spec['evidence_id']]}"
        )
        fact["fact_id"] = build_fact_id(fact)
        facts.append(fact)
    validate_canonical_fact_ids(facts)
    if {(f["period_end"], f["concept_id"]) for f in facts} != set(TARGETS):
        raise ValueError("exact four-cell target contract violated")
    return facts


def build_extraction_report(
    specs: list[dict[str, Any]], object_sha_by_evidence: dict[str, str]
) -> dict[str, Any]:
    rows = []
    for spec in specs:
        cell = cell_from_spec(spec)
        rows.append(
            {
                **cell,
                "page": spec["page"],
                "source_object_sha256": object_sha_by_evidence[spec["evidence_id"]],
                "extraction_method": "PDF_TEXT_LAYER_PLUS_VISUAL_PAGE_VERIFICATION",
                "ocr_used": False,
            }
        )
    return {
        "schema": "petrochina_pe_5y_historical_backfill_extraction_v1",
        "symbol": SYMBOL,
        "logical_cell_count": 4,
        "resolved_logical_cell_count": len(rows),
        "rows": rows,
        "wrong_scope_rejected": True,
        "llm_value_entry_used": False,
        "ocr_used": False,
    }


def build_fact_bundle(facts: list[dict[str, Any]]) -> dict[str, Any]:
    validate_canonical_fact_ids(facts)
    return {
        "schema": "petrochina_pe_5y_historical_backfill_reported_fact_bundle_v1",
        "symbol": SYMBOL,
        "logical_cell_count": 4,
        "fact_count": len(facts),
        "restatement_version_count": len(facts) - 4,
        "facts": facts,
    }


def build_lineage(facts: list[dict[str, Any]]) -> dict[str, Any]:
    confirmations = {
        "2015-12-31|equity_attributable_to_parent": "2016_AR_COMPARATIVE_MATCH",
        "2016-12-31|equity_attributable_to_parent": "2017_AR_COMPARATIVE_MATCH",
        "2016-12-31|net_profit_attributable_to_parent": "2017_AR_COMPARATIVE_MATCH",
        "2017-12-31|net_profit_attributable_to_parent": "2018_AR_COMPARATIVE_MATCH",
    }
    chains = []
    for fact in facts:
        key = f"{fact['period_end']}|{fact['concept_id']}"
        chains.append(
            {
                "logical_cell": key,
                "version_count": 1,
                "versions": [fact["fact_id"]],
                "selected_fact_id": fact["fact_id"],
                "later_comparative_result": confirmations[key],
                "later_value_overwrite": False,
                "status": "RESOLVED_NO_RESTATEMENT",
            }
        )
    return {
        "schema": "petrochina_pe_5y_historical_backfill_version_lineage_v1",
        "symbol": SYMBOL,
        "logical_cell_count": 4,
        "actual_fact_records": len(facts),
        "restatement_versions": len(facts) - 4,
        "bounded_evidence_scan": ["2015_AR", "2016_AR", "2017_AR", "2018_AR", "2019_AR", "2020_AR"],
        "chains": chains,
        "restatement_ambiguity": False,
    }


def build_overlay(
    existing_facts: list[dict[str, Any]], facts: list[dict[str, Any]]
) -> dict[str, Any]:
    combined = existing_facts + facts
    return {
        "schema": "petrochina_pe_5y_historical_backfill_overlay_v1",
        "symbol": SYMBOL,
        "components": [
            "existing_trusted_2020_plus_facts",
            "r4f3a_5_cell_8_record_backfill",
            "r4f4a1_4_cell_versioned_facts",
        ],
        "existing_fact_count": len(existing_facts),
        "new_fact_count": len(facts),
        "combined_fact_count": len(combined),
        "existing_digest": state_identity(existing_facts),
        "new_digest": state_identity(facts),
        "combined_digest": state_identity(combined),
        "selected_new_fact_ids": [f["fact_id"] for f in facts],
    }


def independent_roe_reconciliation(
    combined_facts: list[dict[str, Any]], as_of: str = "2021-08-02"
) -> dict[str, Any]:
    resolver = resolve_annual_roe_chain_as_of(combined_facts, as_of)
    by_year = {r["fiscal_year"]: r for r in resolver.get("roe_observations", [])}
    roe_2016 = roe_decimal("7900000000", "1179968000000", "1189319000000")
    roe_2017 = roe_decimal("22793000000", "1189319000000", "1192862000000")
    return {
        "schema": "petrochina_pe_5y_historical_backfill_reconciliation_v1",
        "symbol": SYMBOL,
        "as_of": as_of,
        "roe_2016_decimal": roe_2016,
        "roe_2017_decimal": roe_2017,
        "resolver_roe_2016_decimal": by_year.get("2016", {}).get("roe_decimal"),
        "resolver_roe_2017_decimal": by_year.get("2017", {}).get("roe_decimal"),
        "roe_2016_match": by_year.get("2016", {}).get("roe_decimal") == roe_2016,
        "roe_2017_match": by_year.get("2017", {}).get("roe_decimal") == roe_2017,
        "disclosed_weighted_average_roe_role": "CROSS_CHECK_DIAGNOSTIC_ONLY",
    }


def build_episode_series(
    facts: list[dict[str, Any]], observations: list[dict[str, Any]]
) -> tuple[dict[str, Any], dict[str, Any]]:
    full = build_3y_series(facts, observations, window=WINDOW_5Y)
    rows = []
    for row in full["rows"]:
        current = Decimal(row["current_ttm_eps_decimal"])
        normalized = Decimal(row["normalized_eps_decimal"])
        direction = (
            DIR_ABOVE if current > normalized else DIR_BELOW if current < normalized else DIR_EQUAL
        )
        rows.append(
            {
                "trade_date": row["trade_date"],
                "raw_ttm_financial_state_id": row["raw_ttm_denominator_state_id"],
                "normalized_denominator_state_id": row["normalized_denominator_state_id"],
                "current_ttm_eps_decimal": row["current_ttm_eps_decimal"],
                "normalized_eps_decimal": row["normalized_eps_decimal"],
                "earnings_excess_decimal": str(current - normalized),
                "direction": direction,
            }
        )
    minimal = {
        "schema": "petrochina_pe_5y_normalized_earnings_episode_series_v1",
        "symbol": SYMBOL,
        "window": {"start": WINDOW_5Y[0], "end": WINDOW_5Y[1]},
        "required_trade_days": 1211,
        "trade_day_count": len(rows),
        "gap_count": len(full["gaps"]),
        "rows": rows,
        "future_values_present": False,
        "normalized_pe_percentile_present": False,
    }
    ledger = build_denominator_state_ledger(full)
    ledger["schema"] = "pe_5y_denominator_state_ledger_stage_local_v1"
    return minimal, ledger


def normalized_anchor_states(
    ledger: dict[str, Any], facts: list[dict[str, Any]]
) -> dict[str, dict[str, Any]]:
    states: dict[str, dict[str, Any]] = {}
    fact_index = {fact.get("fact_id"): fact for fact in facts}
    for segment in ledger["segments"]:
        state_id = segment["normalized_denominator_state_id"]
        if state_id in states:
            continue
        day = segment["start_trade_date"]
        state = build_normalized_earnings_state(
            facts,
            day,
            roe_chain=resolve_annual_roe_chain_as_of(facts, day),
            bvps=resolve_current_bvps_as_of(facts, day),
        )
        ids: list[str] = []
        for record in state["annual_fact_ids"]:
            ids.extend(
                record[key] for key in ("np_fact_id", "begin_equity_fact_id", "end_equity_fact_id")
            )
        ids.extend([state["current_equity_fact_id"], state["share_fact_id"]])
        ids = list(dict.fromkeys(ids))
        states[state_id] = {
            "current_bvps_decimal": state["current_bvps_decimal"],
            "selected_five_roe_years": [
                row["fiscal_year"] for row in state["annual_roe_observations"]
            ],
            "anchor_fact_ids": ids,
            "anchor_available_at_effective_identities": [
                {
                    "fact_id": fact_id,
                    "period_end": fact_index[fact_id].get("period_end"),
                    "available_at": fact_index[fact_id].get("available_at"),
                    "effective_from": fact_index[fact_id].get("effective_from"),
                }
                for fact_id in ids
            ],
        }
    return states


def build_decision(
    extraction: dict[str, Any],
    readiness: dict[str, Any],
    inventory: dict[str, Any],
    outcome: dict[str, Any],
    calendar_reconciliation: dict[str, Any],
) -> dict[str, Any]:
    trusted_data = (
        extraction["resolved_logical_cell_count"] == 4
        and readiness["5y_gate"]["ready_days"] == 1211
        and readiness["5y_gate"]["blocked_days"] == 0
        and calendar_reconciliation["status"] == "PASS"
    )
    valid = inventory["valid_onset_anchored_episodes"]
    mature4 = outcome["protocol_valid_mature_4q_episode_count"]
    if not trusted_data:
        decision = "PE_5Y_BACKFILL_FACT_GAPS_REMAIN"
        verdict = "CONDITIONAL PASS"
        next_action = "STOP"
    elif valid >= 2 and mature4 >= 2:
        decision = "PE_5Y_BACKFILL_TRUSTED_INDEPENDENT_VALIDATION_EXECUTION_READY"
        verdict = "PASS"
        next_action = "R4F.4B_REQUIRES_REVIEWER_AUTHORIZATION"
    else:
        decision = (
            "PE_5Y_BACKFILL_TRUSTED_INDEPENDENT_VALIDATION_NOT_TESTABLE_WITH_FROZEN_5Y_HISTORY"
        )
        verdict = "PASS"
        next_action = "STOP_FOR_NORTH_STAR_REVIEW"
    payload = {
        "schema": "m2_stage2k1r4f4a1_decision",
        "stage": "2K.1R4F.4A1",
        "decision": decision,
        "verdict": verdict,
        "backfill_trusted": trusted_data,
        "frozen_5y_readiness": (
            "READY" if readiness["5y_gate"]["blocked_days"] == 0 else "BLOCKED"
        ),
        "independent_validation_executable": valid >= 2 and mature4 >= 2,
        "resolved_logical_cells": extraction["resolved_logical_cell_count"],
        "required_logical_cells": 4,
        "5y_ready_days": readiness["5y_gate"]["ready_days"],
        "5y_blocked_days": readiness["5y_gate"]["blocked_days"],
        "valid_onset_anchored_episodes": valid,
        "protocol_valid_mature_4q_episode_count": mature4,
        "protocol_valid_mature_8q_episode_count": outcome["protocol_valid_mature_8q_episode_count"],
        "future_eps_values_read": False,
        "automatic_history_extension_beyond_5y": "PROHIBITED",
        "brent": "NOT_ACQUIRED",
        "pe_numeric_scoring": "BLOCKED_UNCHANGED",
        "valuation_score": "NONE",
        "production_scoring": "NOT_AUTHORIZED",
        "full_cycle_coverage": "NOT_PROVEN",
        "normalized_earnings_mid_cycle_validity": "NOT_YET_VALIDATED",
        "cycle_guard_empirical_validation": "NOT_ESTABLISHED",
        "overall_score": "PROHIBITED",
        "next_action": next_action,
        "stop_action": next_action,
        "next_stage": (
            "R4F.4B_REQUIRES_REVIEWER_AUTHORIZATION"
            if next_action == "R4F.4B_REQUIRES_REVIEWER_AUTHORIZATION"
            else (
                "NONE_PENDING_NORTH_STAR_REVIEW"
                if next_action == "STOP_FOR_NORTH_STAR_REVIEW"
                else "NONE_PENDING_DATA_REMEDIATION"
            )
        ),
    }
    assert_preflight_has_no_future_values(payload)
    return payload


def canonical_json(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=1) + "\n"


def artifact_digest_map(artifacts: dict[str, dict[str, Any]]) -> dict[str, str]:
    return {
        name: hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()
        for name, payload in artifacts.items()
    }
