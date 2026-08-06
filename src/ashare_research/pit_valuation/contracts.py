"""M2 Stage 2K.1R4D — PIT valuation quarterly fact acquisition contracts.

This module loads and validates the frozen R4D contracts:

- execution plan (``pit_valuation_quarterly_fact_execution_plan_v1.json``)
- official source evidence register
- official cache registry
- quarterly fact role registry
- quarterly extraction specs

It also freezes the enumerations and the three-state decision gate used by
the acquisition pipeline.  It never acquires a Fact, opens the default
database, or constructs a valuation series.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]

EXECUTION_PLAN_PATH = ROOT / "config" / "pit_valuation_quarterly_fact_execution_plan_v1.json"
SOURCE_EVIDENCE_PATH = ROOT / "config" / "pit_valuation_official_source_evidence_v1.json"
CACHE_REGISTRY_PATH = ROOT / "config" / "pit_valuation_official_cache_registry_v1.json"
ROLE_REGISTRY_PATH = ROOT / "config" / "pit_valuation_quarterly_fact_role_registry_v1.json"
EXTRACTION_SPECS_PATH = ROOT / "config" / "pit_valuation_quarterly_extraction_specs_v1.json"
SHARE_CONTINUITY_REGISTER_PATH = (
    ROOT / "config" / "pit_valuation_share_continuity_register_v1.json"
)
MARKET_CALENDAR_REGISTRY_PATH = (
    ROOT / "config" / "pit_valuation_market_calendar_registry_v1.json"
)

SYMBOL = "601857.SH"
VALUATION_MARKET = "SSE_A_SHARE"
PRICE_CONVENTION = "A_SHARE_PRICE_PER_SHARE"
ACCOUNTING_SCOPE = "consolidated"
ACCOUNTING_STANDARD = "CAS"

# Evidence cutoff frozen in the scoring double-clock contract.
RESEARCH_EVIDENCE_AS_OF = "2026-08-02"
SCORECARD_FORMED_AT = "2026-08-02"

# Required verified-calendar coverage for every in-scope filing announcement.
# The calendar must be fetched from the start of 2020 (the earliest in-scope
# quarter) through the evidence cutoff, so that every announcement maps to a
# real next trading day.  The first trading day of 2020 is 2020-01-02 (the 1st
# is a statutory holiday); the data range still begins at 2020-01-01.
CALENDAR_COVERAGE_START = "2020-01-01"
CALENDAR_COVERAGE_END = RESEARCH_EVIDENCE_AS_OF


class CalendarCoverageGapError(ValueError):
    """Raised when the verified market calendar does not cover a required date.

    Fail-closed: an announcement earlier than the calendar's first trading day
    (or later than its last trading day) is never silently mapped to the
    nearest calendar boundary.  It is recorded as an explicit
    ``calendar_coverage_gap`` instead.
    """


# Gap classification: economic facts vs PIT time-contract coverage.
GAP_CLASS_ECONOMIC_FACT = "economic_fact"
GAP_CLASS_PIT_TIME_CONTRACT = "pit_time_contract"

# Frozen conservative PIT rule: date-only announcement -> effective next trading day.
EFFECTIVE_RULE_ID = "announcement-date-to-next-trading-day-v1"

# Cell acquisition statuses (coverage matrix).
CELL_STATUSES = (
    "acquired_reported_verified",
    "acquired_dual_official_reconciled",
    "acquired_reconciled_derived",
    "not_separately_disclosed",
    "weighted_average_share_ambiguous_due_to_eps_rounding",
    "extraction_marker_missing",
    "ambiguous_table_scope",
    "source_conflict",
    "unresolved_restatement",
    "missing_official_filing",
    "blocked_source_access",
    "unavailable_before_cutoff",
    "calendar_coverage_gap",
    "not_applicable",
)

# Weighted-average-share derivation outcomes.
WEIGHTED_SHARES_STATUSES = (
    "directly_disclosed",
    "exact_derivation",
    "ambiguous_due_to_eps_rounding",
    "missing_operands",
    "not_applicable",
)

# Three-state decision gate.
GATE_READY = "PIT_DENOMINATOR_FACTS_READY_FOR_SERIES_PREFLIGHT"
GATE_GAPS = "PIT_DENOMINATOR_FACT_GAPS_REMAIN"
GATE_NOT_TRUSTED = "PIT_DENOMINATOR_ACQUISITION_NOT_TRUSTED"
GATE_STATES = (GATE_READY, GATE_GAPS, GATE_NOT_TRUSTED)

# Roles required by each future metric.
REQUIRED_FOR = ("PE_TTM", "PB_MRQ", "PS_TTM")

# Report types in scope.
REPORT_TYPES = ("q1", "half_year", "q3", "annual")

# Frozen period mapping (section five of the R4D directive).
PERIOD_TYPE_BY_REPORT = {
    "q1": "quarter_ytd",
    "half_year": "half_year_ytd",
    "q3": "three_quarter_ytd",
    "annual": "annual",
}
PERIOD_END_BY_REPORT = {
    "q1": "03-31",
    "half_year": "06-30",
    "q3": "09-30",
    "annual": "12-31",
}


def canonical_digest(value: Any) -> str:
    """Deterministic SHA-256 of a JSON-serialisable value."""
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def load_plan() -> dict[str, Any]:
    return load_json(EXECUTION_PLAN_PATH)


def load_source_evidence() -> dict[str, Any]:
    return load_json(SOURCE_EVIDENCE_PATH)


def load_cache_registry() -> dict[str, Any]:
    return load_json(CACHE_REGISTRY_PATH)


def load_role_registry() -> dict[str, Any]:
    return load_json(ROLE_REGISTRY_PATH)


def load_extraction_specs() -> dict[str, Any]:
    return load_json(EXTRACTION_SPECS_PATH)


def load_share_continuity_register() -> dict[str, Any]:
    return load_json(SHARE_CONTINUITY_REGISTER_PATH)


def load_market_calendar_registry() -> dict[str, Any]:
    return load_json(MARKET_CALENDAR_REGISTRY_PATH)


def evidence_by_id() -> dict[str, dict[str, Any]]:
    return {e["evidence_id"]: e for e in load_source_evidence()["entries"]}


def validate_plan(plan: dict[str, Any]) -> None:
    """Validate the frozen execution plan against the R4D contract."""
    if plan.get("schema") != "pit_valuation_quarterly_fact_execution_plan_v1":
        raise ValueError("unsupported R4D execution plan schema")
    for field, expected in (
        ("symbol", SYMBOL),
        ("valuation_market", VALUATION_MARKET),
        ("price_convention", PRICE_CONVENTION),
        ("accounting_scope", ACCOUNTING_SCOPE),
        ("accounting_standard", ACCOUNTING_STANDARD),
        ("research_evidence_as_of", RESEARCH_EVIDENCE_AS_OF),
        ("scorecard_formed_at", SCORECARD_FORMED_AT),
    ):
        if plan.get(field) != expected:
            raise ValueError(f"R4D execution plan field {field!r} does not match frozen contract")
    if plan.get("effective_rule_id") != EFFECTIVE_RULE_ID:
        raise ValueError("R4D effective rule is not the frozen next-trading-day rule")
    forbidden = [
        "daily_pe_pb_ps",
        "ttm_metric_results",
        "mrq_metric_results",
        "single_quarter_metric_results",
        "historical_valuation_percentile",
        "valuation_attractiveness_shadow",
        "scoring_weights",
        "peer_acquisition",
        "production_scores",
        "canonical_value_profile",
        "m3_started",
        "default_db_writes",
    ]
    for key in forbidden:
        if plan.get("implementation", {}).get(key) is not False:
            raise ValueError(f"R4D execution plan must forbid {key!r}")


def validate_evidence_register(register: dict[str, Any]) -> None:
    """Validate the official source evidence register structure."""
    if register.get("schema") != "pit_valuation_official_source_evidence_v1":
        raise ValueError("unsupported source evidence schema")
    entries = register.get("entries", [])
    if not entries:
        raise ValueError("source evidence register has no entries")
    seen: set[str] = set()
    for entry in entries:
        eid = entry.get("evidence_id")
        if not eid or eid in seen:
            raise ValueError(f"duplicate or missing evidence_id: {eid!r}")
        seen.add(eid)
        for field in (
            "issuer",
            "symbol",
            "report_type",
            "fiscal_year",
            "period_start",
            "period_end",
            "announcement_date",
            "reporting_language",
            "source_role",
        ):
            if entry.get(field) in (None, ""):
                raise ValueError(f"evidence {eid!r} missing {field!r}")
        # A verified exchange_official filing must carry a proof URL; a
        # blocked issuer entry may record blocked_source_access without one.
        if entry.get("source_role") == "exchange_official" and not entry.get("proof_url"):
            raise ValueError(f"evidence {eid!r} missing 'proof_url'")
        # supersedes_document_id is legitimately null for an original filing.
        if "supersedes_document_id" not in entry:
            raise ValueError(f"evidence {eid!r} missing 'supersedes_document_id'")
        if entry.get("source_role") not in ("issuer_official", "exchange_official"):
            raise ValueError(f"evidence {eid!r} has invalid source_role")
        if entry.get("report_type") not in REPORT_TYPES:
            raise ValueError(f"evidence {eid!r} has invalid report_type")


def validate_cache_registry(registry: dict[str, Any]) -> None:
    """Validate the official cache registry structure."""
    if registry.get("schema") != "pit_valuation_official_cache_registry_v1":
        raise ValueError("unsupported cache registry schema")
    for obj in registry.get("objects", []):
        if not obj.get("object_key"):
            raise ValueError("cache object missing object_key")
        if len(obj.get("sha256", "")) != 64:
            raise ValueError(f"cache object {obj['object_key']} missing sha256")
        if not obj.get("evidence_ids"):
            raise ValueError(f"cache object {obj['object_key']} missing evidence_ids")
        if obj.get("media_type") != "application/pdf":
            raise ValueError(f"cache object {obj['object_key']} must be application/pdf")


def validate_role_registry(registry: dict[str, Any]) -> None:
    """Validate the fact role registry."""
    if registry.get("schema") != "pit_valuation_quarterly_fact_role_registry_v1":
        raise ValueError("unsupported role registry schema")
    roles = registry.get("roles", [])
    if not roles:
        raise ValueError("role registry has no roles")
    for role in roles:
        for field in (
            "role_id",
            "concept_id",
            "concept_version",
            "statement",
            "statement_scope",
            "instant_or_duration",
            "allowed_period_types",
            "canonical_unit",
            "direct_or_derived",
        ):
            if role.get(field) in (None, ""):
                raise ValueError(f"role {role.get('role_id')!r} missing {field!r}")
        if role.get("instant_or_duration") not in ("instant", "duration"):
            raise ValueError(f"role {role.get('role_id')!r} invalid instant_or_duration")


def validate_extraction_specs(specs: dict[str, Any]) -> None:
    """Validate the extraction specs."""
    if specs.get("schema") != "pit_valuation_quarterly_extraction_specs_v1":
        raise ValueError("unsupported extraction specs schema")
    for spec in specs.get("specs", []):
        for field in (
            "extraction_spec_id",
            "version",
            "role_id",
            "report_type",
            "named_capture_pattern",
            "capture_group",
            "raw_unit",
            "conversion_multiplier",
            "sign_rule",
            "decimal_transform_id",
            "extraction_method_version",
        ):
            if spec.get(field) in (None, ""):
                raise ValueError(f"spec {spec.get('extraction_spec_id')!r} missing {field!r}")
        if spec.get("expected_context") not in ("duration_cumulative", "instant_period_end"):
            raise ValueError(f"spec {spec.get('extraction_spec_id')!r} invalid expected_context")
        if spec.get("ocr_allowed") is not False or spec.get("llm_allowed") is not False:
            raise ValueError(f"spec {spec.get('extraction_spec_id')!r} must forbid OCR/LLM")


def validate_share_continuity_register(register: dict[str, Any]) -> None:
    """Validate the frozen share-continuity register."""
    if register.get("schema") != "pit_valuation_share_continuity_register_v1":
        raise ValueError("unsupported share continuity register schema")
    if register.get("symbol") != SYMBOL:
        raise ValueError("share continuity register symbol mismatch")
    if register.get("trust") not in ("trusted", "not_trusted"):
        raise ValueError("share continuity register has invalid trust")
    if register.get("share_count_constant") is not True:
        raise ValueError("share continuity register must record a constant conclusion")
    if not register.get("search_window", {}).get("start"):
        raise ValueError("share continuity register missing search window start")
    if not register.get("precise_base_evidence"):
        raise ValueError("share continuity register has no precise base evidence")
    if register.get("constant_value") is None:
        raise ValueError("share continuity register missing constant_value")
    if not isinstance(register.get("share_changing_actions_found"), list):
        raise ValueError("share continuity register missing share-changing actions list")


def validate_market_calendar_registry(registry: dict[str, Any]) -> None:
    """Validate the frozen verified-market-calendar registry.

    The registry pins the single content-addressed calendar object the loader
    may read.  The loader must never scan the cache directory or fall back to
    another parquet, so the registry records the exact object key, its sha256,
    and the structural facts (row count, first/last trading day, evidence
    cutoff) the loader verifies after reading.
    """
    if registry.get("schema") != "pit_valuation_market_calendar_registry_v1":
        raise ValueError("unsupported market calendar registry schema")
    if registry.get("symbol") != SYMBOL:
        raise ValueError("market calendar registry symbol mismatch")
    sha = registry.get("object_sha256", "")
    if len(sha) != 64:
        raise ValueError("market calendar registry missing object_sha256")
    registry_resolver = registry.get("resolver_contract")
    if registry_resolver != "explicit_content_addressed_object_no_scan_no_fallback":
        raise ValueError("market calendar registry must forbid scanning/fallback")
    object_key = registry.get("object_key", "")
    if Path(object_key).stem != sha:
        raise ValueError("market calendar registry object_key must be named by its sha256")
    if not isinstance(registry.get("row_count"), int) or registry.get("row_count") <= 0:
        raise ValueError("market calendar registry missing positive row_count")
    for field in ("first_trading_day", "last_trading_day", "evidence_cutoff"):
        if registry.get(field) in (None, ""):
            raise ValueError(f"market calendar registry missing {field!r}")


def validate_all_contracts() -> dict[str, Any]:
    """Validate every R4D contract and return a digest of each."""
    plan = load_plan()
    validate_plan(plan)
    evidence = load_source_evidence()
    validate_evidence_register(evidence)
    cache = load_cache_registry()
    validate_cache_registry(cache)
    roles = load_role_registry()
    validate_role_registry(roles)
    specs = load_extraction_specs()
    validate_extraction_specs(specs)
    continuity = load_share_continuity_register()
    validate_share_continuity_register(continuity)
    market_calendar = load_market_calendar_registry()
    validate_market_calendar_registry(market_calendar)
    return {
        "plan_digest": canonical_digest(plan),
        "source_evidence_digest": canonical_digest(evidence),
        "cache_registry_digest": canonical_digest(cache),
        "role_registry_digest": canonical_digest(roles),
        "extraction_specs_digest": canonical_digest(specs),
        "share_continuity_register_digest": canonical_digest(continuity),
        "market_calendar_registry_digest": canonical_digest(market_calendar),
    }


def decide_gate(
    *,
    cache_trusted: bool,
    extraction_trusted: bool,
    identity_trusted: bool,
    pit_trusted: bool,
    source_conflicts: int,
    explicit_gaps: int,
    warmup_ready: bool,
) -> str:
    """Three-state fail-closed decision gate.

    - READY only when every engineering layer is trusted, there are no source
      conflicts, and the frozen warm-up (3y or 5y) is satisfied.
    - GAPS_REMAIN when engineering is trusted but explicit official gaps exist.
    - NOT_TRUSTED if any verifying layer is not trusted (fail-closed).
    """
    if not (cache_trusted and extraction_trusted and identity_trusted and pit_trusted):
        return GATE_NOT_TRUSTED
    if source_conflicts > 0:
        return GATE_NOT_TRUSTED
    if explicit_gaps > 0 or not warmup_ready:
        return GATE_GAPS
    return GATE_READY
