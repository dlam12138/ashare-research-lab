"""M2 offline research bundle: fixed-source assembly, export and verification.

This tool assembles nine *baseline* reports of the PetroChina (``601857.SH``) value
assessment into one readable Markdown document plus a canonical JSON projection, and it can
export that bundle together with byte-exact source attachments and a checksum manifest, then
verify the exported directory from its retained bytes alone.

It performs **no research computation**.  Every number, status, identifier, date and gap is a
faithful projection of the fixed source reports.  There is no overall score, no ranking, no
eligibility statement, no recommendation and no new metric.  Source dates are heterogeneous
historical dates: this is a mixed-date historical compilation, never a unified as-of PIT query
and never a refresh of the research.

Source hashes certify attachment integrity only.  Verification re-renders the reports from the
retained source bytes; it does not trust the manifest's own recorded hashes.

Only the standard library is used.  Known failures exit non-zero, print a sanitized error code
on stderr and write nothing to stdout.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

SCHEMA_ID = "m2_offline_research_bundle"
SCHEMA_VERSION = "1.0"
REPORT_MARKDOWN_NAME = "report.md"
REPORT_JSON_NAME = "report.json"
MANIFEST_NAME = "manifest.json"
MANIFEST_SCHEMA = "m2_offline_research_bundle_manifest_v1"
SOURCES_DIR = "sources"
SOURCES_REPORTS_DIR = "sources/reports"
NARRATIVE_MAX_BYTES = 32_768
FIELD_PREVIEW_LIMIT = 6

# Fixed source order.  The bundle never selects, sorts or re-orders its inputs.
SOURCE_REPORTS: tuple[str, ...] = (
    "petrochina_value_profile.json",
    "petrochina_dimension_scoring_shadow_v6.json",
    "petrochina_risk_veto_report.json",
    "m2_explicit_gap_ledger.json",
    "petrochina_pit_valuation_percentile_profile_v1.json",
    "petrochina_pit_financial_state_timeline_v2.json",
    "m2_stage2k1r4f4b_pe_disposition_decision_v1.json",
    "petrochina_value_profile_2021_2026.md",
    "petrochina_financial_safety_2021_2025.md",
)
JSON_SOURCE_REPORTS: tuple[str, ...] = SOURCE_REPORTS[:7]
MARKDOWN_SOURCE_REPORTS: tuple[str, ...] = SOURCE_REPORTS[7:]

# SHA256 of the fixed reports, pinned from the actual baseline commit 73a462f.
PINNED_SOURCE_SHA256: dict[str, str] = {
    "petrochina_value_profile.json": (
        "074b85646995d40206cabf25e12ba82718c11aed8dbb41cfe5859533ee3759ce"
    ),
    "petrochina_dimension_scoring_shadow_v6.json": (
        "a3c14ad9c4b5900ab8492b9f0e79608683fa66363d43e0c1c268f025356068fc"
    ),
    "petrochina_risk_veto_report.json": (
        "9ad347cf48c88be73bb2ae16aabf78866e5abbc61bd54132fe2cd1238ec4f956"
    ),
    "m2_explicit_gap_ledger.json": (
        "74ff95b18690187072850a462da5dcb90b4c9482717db7b99b7a06cf9555e0d4"
    ),
    "petrochina_pit_valuation_percentile_profile_v1.json": (
        "6636730a4d7c3c496579e1b95d799fc9ce7aeba4ad4c1df2aa0cb483dd24692f"
    ),
    "petrochina_pit_financial_state_timeline_v2.json": (
        "5be0f7353449e7ac8fe5ff64510c30c73fa0adad046f787965b6ec4f8b1880b5"
    ),
    "m2_stage2k1r4f4b_pe_disposition_decision_v1.json": (
        "fc6d8a472ffaf98ac450d443246c7d9d3722b462e1c84e2d3c0a6128735b7850"
    ),
    "petrochina_value_profile_2021_2026.md": (
        "e76765b37b880d24f1aefaff7987998aa2bce20010602daf5095a7ef72649bbc"
    ),
    "petrochina_financial_safety_2021_2025.md": (
        "f5d9f9fc1a7c75b33decbee72aad9a69e529f27466348bd1f69a3438c648c1d0"
    ),
}

# Original repository locations of the retained attachments, recorded for provenance only.
SOURCE_ORIGIN_PATHS: dict[str, str] = {
    "petrochina_value_profile.json": "reports/petrochina_value_profile.json",
    "petrochina_dimension_scoring_shadow_v6.json": (
        "reports/petrochina_dimension_scoring_shadow_v6.json"
    ),
    "petrochina_risk_veto_report.json": "reports/petrochina_risk_veto_report.json",
    "m2_explicit_gap_ledger.json": "reports/m2_explicit_gap_ledger.json",
    "petrochina_pit_valuation_percentile_profile_v1.json": (
        "reports/petrochina_pit_valuation_percentile_profile_v1.json"
    ),
    "petrochina_pit_financial_state_timeline_v2.json": (
        "reports/petrochina_pit_financial_state_timeline_v2.json"
    ),
    "m2_stage2k1r4f4b_pe_disposition_decision_v1.json": (
        "reports/m2_stage2k1r4f4b_pe_disposition_decision_v1.json"
    ),
    "petrochina_value_profile_2021_2026.md": "reports/petrochina_value_profile_2021_2026.md",
    "petrochina_financial_safety_2021_2025.md": (
        "reports/petrochina_financial_safety_2021_2025.md"
    ),
}

# Fixed semantic order of the risk observations, independent of any score or status.
RISK_ID_ORDER: tuple[str, ...] = (
    "modified_audit_opinion",
    "going_concern_material_uncertainty",
    "formal_regulatory_investigation_or_major_discipline",
    "material_error_restatement",
    "controlling_shareholder_pledge_risk",
    "material_related_party_transaction_risk",
    "controlling_shareholder_fund_occupation_or_related_guarantee",
    "repeated_equity_financing_or_material_dilution",
)

RISK_SPEC_FIELDS: tuple[tuple[str, str], ...] = (
    ("risk_id", "risk_id"),
    ("status", "status"),
    ("observation_id", "observation_id"),
    ("available_at", "available_at"),
    ("lineage_status", "lineage_status"),
    ("missing_reasons", "missing_reasons"),
)

RISK_EVIDENCE_FIELDS: tuple[str, ...] = (
    "all_evidence_ids",
    "input_evidence_ids",
    "supplemental_evidence_ids",
    "active_event_ids",
    "superseded_event_ids",
)

SHADOW_DIMENSION_ORDER: tuple[str, ...] = (
    "enterprise_quality",
    "valuation_attractiveness",
    "value_realization_capacity",
    "risk_and_evidence_integrity",
)

TIMELINE_METRIC_ORDER: tuple[str, ...] = ("PE_A_TTM", "PB_A_MRQ", "PS_A_TTM")

TIMELINE_SUMMARY_HEADER: tuple[str, ...] = (
    "metric",
    "state_count",
    "computed",
    "missing_ttm_input",
    "first_effective_from",
    "last_effective_from",
)

TIMELINE_STATE_HEADER: tuple[str, ...] = (
    "fiscal_year",
    "report_type",
    "period_end",
    "effective_from",
    "value_decimal",
    "status",
    "available_at_max",
    "input_available_at",
    "financial_state_id",
)

SOURCE_TABLE_HEADER: tuple[str, ...] = (
    "来源报告",
    "类型",
    "字节",
    "SHA256（完整性）",
    "源报告自身日期",
)

OBSERVATION_TABLE_HEADER: tuple[str, ...] = (
    "observation",
    "status",
    "trade_date",
    "value_decimal",
    "value",
    "score_eligible",
    "lineage",
)

PERCENTILE_TABLE_HEADER: tuple[str, ...] = (
    "metric_id",
    "window",
    "calendar_start",
    "effective_first_trade_date",
    "current_ratio_decimal",
    "strict_percentile_decimal",
    "weak_percentile_decimal",
    "midrank_percentile_decimal",
    "eligible",
    "excluded",
    "coverage_status",
    "percentile_record_id",
)

COVERAGE_TABLE_HEADER: tuple[str, ...] = (
    "dimension_id",
    "status",
    "coverage_ratio",
    "covered_weight",
    "missing_component_ids",
    "blocked_component_ids",
)

COMPONENT_TABLE_HEADER: tuple[str, ...] = (
    "dimension_id",
    "component_id",
    "status",
    "shadow_score",
    "eligible",
    "covered",
    "source",
    "note",
)

RISK_TABLE_HEADER: tuple[str, ...] = (
    "risk_id",
    "status",
    "observation_id",
    "available_at",
    "lineage_status",
    "missing_reasons",
    "证据条数（完整 ID 见 JSON）",
    "事件条数（完整 ID 见 JSON）",
    "search_register_id",
    "search_coverage_end",
)

TIMELINE_ROW_FIELDS: tuple[str, ...] = (
    "metric_id",
    "state_type",
    "concept",
    "fiscal_year",
    "report_type",
    "period_end",
    "effective_from",
    "value_decimal",
    "status",
    "available_at_max",
    "financial_state_id",
    "state_digest",
)

DECIMAL_POLICY_NOTE = (
    "原始十进制字符串按源报告逐字保留（例如 12.89158710139375214555441126）；"
    "本文件不重新计算、不舍入、不派生任何数值。"
)

SOURCE_DATE_FIELDS: tuple[str, ...] = (
    "as_of_trade_date",
    "as_of_date",
    "research_evidence_as_of",
    "market_data_as_of_date",
    "scorecard_formed_at",
    "last_reviewed_date",
    "evaluation_as_of_date",
    "search_coverage_end",
)

KNOWN_ERROR_CODES = frozenset(
    {
        "SOURCE_DIRECTORY_MISSING",
        "SOURCE_REPORT_MISSING",
        "SOURCE_HASH_MISMATCH",
        "SOURCE_UNREADABLE",
        "SOURCE_JSON_INVALID",
        "SOURCE_SHAPE_INVALID",
        "NARRATIVE_UNREADABLE",
        "OUTPUT_PATH_EXISTS",
        "OUTPUT_NOT_A_DIRECTORY",
        "OUTPUT_WRITE_FAILED",
        "VERIFY_DIRECTORY_MISSING",
        "VERIFY_MANIFEST_UNREADABLE",
        "VERIFY_MANIFEST_INVALID",
        "VERIFY_MANIFEST_MISMATCH",
        "VERIFY_SOURCE_MISSING",
        "VERIFY_SOURCE_CORRUPT",
        "VERIFY_COMPANION_MISSING",
        "VERIFY_RENDER_MISMATCH",
        "UNEXPECTED_FAILURE",
    }
)


class BundleError(Exception):
    """A known, sanitized bundle failure carrying one stable error code."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code if code in KNOWN_ERROR_CODES else "UNEXPECTED_FAILURE"


@dataclass(frozen=True)
class BundleSource:
    """One retained source report read as bytes, with its pinned baseline hash."""

    name: str
    origin_path: str
    relative_path: str
    sha256: str
    byte_count: int
    payload_bytes: bytes
    document: Any


@dataclass(frozen=True)
class SourceBundle:
    """The fixed, in-memory inputs of one bundle: nine ordered source reports."""

    sources: tuple[BundleSource, ...]

    def one(self, name: str) -> BundleSource:
        for source in self.sources:
            if source.name == name:
                return source
        raise BundleError("SOURCE_SHAPE_INVALID")

    def json_document(self, name: str) -> dict[str, Any]:
        document = self.one(name).document
        if not isinstance(document, dict):
            raise BundleError("SOURCE_SHAPE_INVALID")
        return document

    def metadata(self) -> list[dict[str, Any]]:
        rows = []
        for source in self.sources:
            rows.append(
                {
                    "name": source.name,
                    "attachment_path": source.relative_path,
                    "origin_path": source.origin_path,
                    "kind": "json" if source.name in JSON_SOURCE_REPORTS else "markdown",
                    "byte_count": source.byte_count,
                    "sha256": source.sha256,
                    "sha256_pinned_in_tool": PINNED_SOURCE_SHA256[source.name],
                    "original_source_dates": source_dates(source),
                }
            )
        return rows


# --------------------------------------------------------------------------------------
# Source loading
# --------------------------------------------------------------------------------------


def default_reports_directory() -> Path:
    """Return the repository ``reports`` directory beside this module."""
    return Path(__file__).resolve().parents[3] / "reports"


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _read_source_bytes(path: Path, code: str) -> bytes:
    try:
        return path.read_bytes()
    except FileNotFoundError as error:
        raise BundleError(code) from error
    except OSError as error:
        raise BundleError(code) from error


def load_source_bundle(reports_directory: Path | None = None) -> SourceBundle:
    """Read, hash, parse and validate the nine fixed source reports."""
    directory = default_reports_directory() if reports_directory is None else reports_directory
    if not directory.is_dir():
        raise BundleError("SOURCE_DIRECTORY_MISSING")
    sources: list[BundleSource] = []
    for name in SOURCE_REPORTS:
        pinned = PINNED_SOURCE_SHA256[name]
        raw = _read_source_bytes(directory / name, "SOURCE_REPORT_MISSING")
        if sha256_bytes(raw) != pinned:
            raise BundleError("SOURCE_HASH_MISMATCH")
        document: Any = None
        if name in JSON_SOURCE_REPORTS:
            try:
                document = json.loads(raw.decode("utf-8"))
            except (UnicodeDecodeError, ValueError) as error:
                raise BundleError("SOURCE_JSON_INVALID") from error
            if not isinstance(document, dict):
                raise BundleError("SOURCE_SHAPE_INVALID")
        else:
            try:
                document = raw.decode("utf-8")
            except UnicodeDecodeError as error:
                raise BundleError("NARRATIVE_UNREADABLE") from error
        sources.append(
            BundleSource(
                name=name,
                origin_path=SOURCE_ORIGIN_PATHS[name],
                relative_path=f"{SOURCES_REPORTS_DIR}/{name}",
                sha256=pinned,
                byte_count=len(raw),
                payload_bytes=raw,
                document=document,
            )
        )
    bundle = SourceBundle(sources=tuple(sources))
    validate_bundle(bundle)
    return bundle


def _require_list(parent: dict[str, Any], key: str) -> list[Any]:
    value = parent.get(key)
    if not isinstance(value, list):
        raise BundleError("SOURCE_SHAPE_INVALID")
    return value


def _require_dict(parent: dict[str, Any], key: str) -> dict[str, Any]:
    value = parent.get(key)
    if not isinstance(value, dict):
        raise BundleError("SOURCE_SHAPE_INVALID")
    return value


def validate_bundle(bundle: SourceBundle) -> None:
    """Check that every projection below has the source shape it needs."""
    profile = bundle.json_document("petrochina_value_profile.json")
    _require_dict(profile, "latest_observations")
    _require_dict(profile, "capital_return")
    _require_dict(profile, "integrated_layers")
    _require_dict(profile, "percentile_position")
    shadow = bundle.json_document("petrochina_dimension_scoring_shadow_v6.json")
    dimensions = _require_dict(shadow, "dimensions")
    if set(dimensions) != set(SHADOW_DIMENSION_ORDER):
        raise BundleError("SOURCE_SHAPE_INVALID")
    risk = bundle.json_document("petrochina_risk_veto_report.json")
    observations = _require_list(risk, "observations")
    if len(observations) != len(RISK_ID_ORDER):
        raise BundleError("SOURCE_SHAPE_INVALID")
    gaps = bundle.json_document("m2_explicit_gap_ledger.json")
    _require_list(gaps, "gaps")
    _require_dict(gaps, "count_contract")
    percentiles = bundle.json_document("petrochina_pit_valuation_percentile_profile_v1.json")
    _require_list(percentiles, "records")
    timeline = bundle.json_document("petrochina_pit_financial_state_timeline_v2.json")
    timelines = _require_dict(timeline, "timelines")
    if set(timelines) != set(TIMELINE_METRIC_ORDER):
        raise BundleError("SOURCE_SHAPE_INVALID")
    for metric in TIMELINE_METRIC_ORDER:
        rows = timelines[metric]
        if not isinstance(rows, list):
            raise BundleError("SOURCE_SHAPE_INVALID")
    decision = bundle.json_document("m2_stage2k1r4f4b_pe_disposition_decision_v1.json")
    _require_dict(decision, "pe_evidence")
    for name in MARKDOWN_SOURCE_REPORTS:
        text = bundle.one(name).document
        if not isinstance(text, str) or not text:
            raise BundleError("NARRATIVE_UNREADABLE")


def source_dates(source: BundleSource) -> dict[str, str]:
    """Collect the dates that the source itself records, in fixed field order."""
    if not isinstance(source.document, dict):
        return {}
    dates: dict[str, str] = {}
    for field in SOURCE_DATE_FIELDS:
        value = source.document.get(field)
        if isinstance(value, str) and value:
            dates[field] = value
    time_contract = source.document.get("time_contract", {})
    if isinstance(time_contract, dict):
        for field in SOURCE_DATE_FIELDS:
            value = time_contract.get(field)
            if isinstance(value, str) and value:
                dates[f"time_contract.{field}"] = value
    return dates


# --------------------------------------------------------------------------------------
# Projection
# --------------------------------------------------------------------------------------


def _scalar_number(value: Any) -> str:
    if isinstance(value, bool) or value is None:
        return ""
    if isinstance(value, (int, float)):
        return str(value)
    return ""


def _display(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float, str)):
        return str(value)
    if isinstance(value, list):
        return "[" + ", ".join(_display(item) for item in value) + "]"
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _cell(value: Any) -> str:
    text = _display(value)
    return text.replace("|", "\\|").replace("\n", " ")


def _nested_cell(value: Any) -> str:
    if not isinstance(value, dict):
        return ""
    return _cell(value)


def _table(header: tuple[str, ...], rows: list[tuple[str, ...]]) -> str:
    lines = ["| " + " | ".join(header) + " |", "| " + " | ".join("---" for _ in header) + " |"]
    lines.extend("| " + " | ".join(row) + " |" for row in rows)
    return "\n".join(lines)


def _field_rows(mapping: dict[str, Any]) -> list[tuple[str, str]]:
    return [(key, _cell(mapping.get(key))) for key in mapping]


def _build_sources_section(bundle: SourceBundle) -> list[dict[str, Any]]:
    return bundle.metadata()


def _build_value_profile(bundle: SourceBundle) -> dict[str, Any]:
    profile = bundle.json_document("petrochina_value_profile.json")
    latest = _require_dict(profile, "latest_observations")
    capital_return = _require_dict(profile, "capital_return")
    return {
        "source_name": "petrochina_value_profile.json",
        "contract": profile.get("contract"),
        "symbol": profile.get("symbol"),
        "as_of_trade_date": profile.get("as_of_trade_date"),
        "stage2g1_status": profile.get("stage2g1_status"),
        "latest_observations": {key: dict(latest[key]) for key in latest},
        "capital_return": {key: dict(capital_return[key]) for key in capital_return},
        "integrated_layers": dict(_require_dict(profile, "integrated_layers")),
    }


def _build_timeline(bundle: SourceBundle) -> dict[str, Any]:
    document = bundle.json_document("petrochina_pit_financial_state_timeline_v2.json")
    timelines = _require_dict(document, "timelines")
    return {
        "source_name": "petrochina_pit_financial_state_timeline_v2.json",
        "schema": document.get("schema"),
        "version": document.get("version"),
        "symbol": document.get("symbol"),
        "summary": dict(_require_dict(document, "summary")),
        "timelines": {
            metric: [dict(row) for row in timelines[metric]] for metric in TIMELINE_METRIC_ORDER
        },
    }


def _build_percentiles(bundle: SourceBundle) -> dict[str, Any]:
    document = bundle.json_document("petrochina_pit_valuation_percentile_profile_v1.json")
    return {
        "source_name": "petrochina_pit_valuation_percentile_profile_v1.json",
        "schema": document.get("schema"),
        "version": document.get("version"),
        "symbol": document.get("symbol"),
        "as_of_trade_date": document.get("as_of_trade_date"),
        "method": dict(_require_dict(document, "method")),
        "summary": dict(_require_dict(document, "summary")),
        "records": [dict(record) for record in _require_list(document, "records")],
    }


def _build_shadows(bundle: SourceBundle) -> dict[str, Any]:
    document = bundle.json_document("petrochina_dimension_scoring_shadow_v6.json")
    dimensions = _require_dict(document, "dimensions")
    ordered: dict[str, Any] = {}
    for name in SHADOW_DIMENSION_ORDER:
        dimension = dict(_require_dict(dimensions, name))
        components = dimension.get("components")
        if isinstance(components, dict):
            dimension["components"] = {key: dict(components[key]) for key in components}
        ordered[name] = dimension
    coverage = []
    for name in SHADOW_DIMENSION_ORDER:
        dimension = ordered[name]
        coverage.append(
            {
                "dimension_id": name,
                "status": dimension.get("status"),
                "missing_component_ids": dimension.get("missing_component_ids"),
                "blocked_component_ids": dimension.get("blocked_component_ids"),
                "coverage_ratio": dimension.get("coverage_ratio"),
                "covered_weight": dimension.get("covered_weight"),
                "numeric_score": _scalar_number(dimension.get("score")) or None,
            }
        )
    return {
        "source_name": "petrochina_dimension_scoring_shadow_v6.json",
        "schema": document.get("schema"),
        "version": document.get("version"),
        "symbol": document.get("symbol"),
        "non_production": document.get("non_production"),
        "overall_score_prohibited": document.get("overall_score_prohibited"),
        "recommendation_prohibited": document.get("recommendation_prohibited"),
        "score_eligible": document.get("score_eligible"),
        "status": document.get("status"),
        "dimension_order": list(SHADOW_DIMENSION_ORDER),
        "time_contract": dict(_require_dict(document, "time_contract")),
        "dimensions": ordered,
        "component_coverage": coverage,
    }


def _build_pe_disposition(bundle: SourceBundle) -> dict[str, Any]:
    document = bundle.json_document("m2_stage2k1r4f4b_pe_disposition_decision_v1.json")
    return {
        "source_name": "m2_stage2k1r4f4b_pe_disposition_decision_v1.json",
        "schema": document.get("schema"),
        "stage": document.get("stage"),
        "subject": document.get("subject"),
        "decision": document.get("decision"),
        "verdict": document.get("verdict"),
        "upstream_decision": document.get("upstream_decision"),
        "pe_evidence": dict(_require_dict(document, "pe_evidence")),
        "frozen_5y_evidence": dict(_require_dict(document, "frozen_5y_evidence")),
        "scoring_policy": dict(_require_dict(document, "scoring_policy")),
        "scope_boundary": dict(_require_dict(document, "scope_boundary")),
        "m2_status": dict(_require_dict(document, "m2_status")),
        "next_stage": dict(_require_dict(document, "next_stage")),
    }


def _build_risk(bundle: SourceBundle) -> dict[str, Any]:
    document = bundle.json_document("petrochina_risk_veto_report.json")
    by_id: dict[str, dict[str, Any]] = {}
    for observation in _require_list(document, "observations"):
        if not isinstance(observation, dict) or not isinstance(observation.get("risk_id"), str):
            raise BundleError("SOURCE_SHAPE_INVALID")
        by_id[observation["risk_id"]] = observation
    if set(by_id) != set(RISK_ID_ORDER):
        raise BundleError("SOURCE_SHAPE_INVALID")
    observations = []
    missing_reasons: list[dict[str, Any]] = []
    for risk_id in RISK_ID_ORDER:
        raw = by_id[risk_id]
        record: dict[str, Any] = {}
        for spec_field, source_field in RISK_SPEC_FIELDS:
            record[spec_field] = raw.get(source_field)
        record["evaluation_as_of_date"] = raw.get("evaluation_as_of_date")
        for field in RISK_EVIDENCE_FIELDS:
            record[field] = list(raw.get(field) or [])
        record["evidence_id_count"] = len(record["all_evidence_ids"])
        record["event_id_count"] = len(record["active_event_ids"])
        record["search_register_id"] = raw.get("search_register_id")
        record["search_coverage_end"] = raw.get("search_coverage_end")
        observations.append(record)
        reasons = record["missing_reasons"]
        if reasons:
            missing_reasons.append({"risk_id": risk_id, "reasons": list(reasons)})
    return {
        "source_name": "petrochina_risk_veto_report.json",
        "contract": document.get("contract"),
        "symbol": document.get("symbol"),
        "as_of_date": document.get("as_of_date"),
        "status": document.get("status"),
        "methodology_version": document.get("methodology_version"),
        "expected_risk_count": document.get("expected_risk_count"),
        "observation_count": document.get("observation_count"),
        "missing_evidence_count": document.get("missing_evidence_count"),
        "missing_evidence_risk_ids": list(document.get("missing_evidence_risk_ids") or []),
        "missing_slot_count": document.get("missing_slot_count"),
        "evidence_lineage_status": document.get("evidence_lineage_status"),
        "search_pit_status": document.get("search_pit_status"),
        "score_eligible": document.get("score_eligible"),
        "warnings": list(document.get("warnings") or []),
        "risk_id_order": list(RISK_ID_ORDER),
        "observations": observations,
        "missing_reason_records": missing_reasons,
    }


def _build_gaps(bundle: SourceBundle) -> dict[str, Any]:
    document = bundle.json_document("m2_explicit_gap_ledger.json")
    gaps = _require_list(document, "gaps")
    rows = []
    for gap in gaps:
        if not isinstance(gap, dict):
            raise BundleError("SOURCE_SHAPE_INVALID")
        rows.append({key: gap[key] for key in gap})
    return {
        "source_name": "m2_explicit_gap_ledger.json",
        "schema": document.get("schema"),
        "symbol": document.get("symbol"),
        "as_of_date": document.get("as_of_date"),
        "status": document.get("status"),
        "source_ledgers": list(document.get("source_ledgers") or []),
        "count_contract": dict(_require_dict(document, "count_contract")),
        "gap_count": len(rows),
        "declared_current_gap_count": _require_dict(document, "count_contract").get(
            "current_gap_count"
        ),
        "rows": rows,
    }


def build_payload(bundle: SourceBundle) -> dict[str, Any]:
    """Build the canonical JSON projection of the fixed sources."""
    sources = _build_sources_section(bundle)
    value_profile = _build_value_profile(bundle)
    timeline = _build_timeline(bundle)
    percentiles = _build_percentiles(bundle)
    shadows = _build_shadows(bundle)
    pe_disposition = _build_pe_disposition(bundle)
    risk = _build_risk(bundle)
    gaps = _build_gaps(bundle)
    payload: dict[str, Any] = {
        "schema": SCHEMA_ID,
        "schema_version": SCHEMA_VERSION,
        "compilation": {
            "nature": "mixed_date_historical_compilation",
            "unified_pit_as_of_query": False,
            "research_refresh": False,
            "source_selection": False,
            "new_metrics_computed": False,
            "overall_score": False,
            "ranking": False,
            "recommendation": False,
            "eligibility": False,
            "decimal_policy": DECIMAL_POLICY_NOTE,
            "source_dates_are_heterogeneous": True,
            "source_hash_purpose": "attachment_integrity_only",
        },
        "symbol": value_profile["symbol"],
        "sources": sources,
        "value_profile": value_profile,
        "timeline": timeline,
        "valuation_percentiles": percentiles,
        "shadow_dimensions": shadows,
        "pe_disposition": pe_disposition,
        "risk_observations": risk,
        "explicit_gaps": gaps,
        "nonproduction_boundary": {
            "score_eligible": False,
            "production_eligible": False,
            "overall_score_prohibited": True,
            "recommendation_prohibited": True,
            "ranking_produced": False,
            "eligibility_assessed": False,
            "inferred_conclusion": False,
            "notes": [
                "四个维度为影子（非生产）输出，覆盖缺口不是零分，也不是负面结论。",
                "PE 数值评分已暂缓冻结（decision 见 pe_disposition），仅保留描述性分位。",
                "缺失证据（股利、风险）既不是零，也不是负面缺失结论。",
            ],
        },
    }
    return payload


# --------------------------------------------------------------------------------------
# Markdown rendering
# --------------------------------------------------------------------------------------


def _md_sources_section(payload: dict[str, Any]) -> list[str]:
    lines = ["## 一、固定来源与日期（混合日期历史汇编）", ""]
    lines.append(
        "来源报告分别保留各自的日期字段，本汇编不把它们统一为单一 as-of 时点，"
        "也不刷新任何研究结论。"
    )
    lines.append("")
    rows = []
    for source in payload["sources"]:
        dates = "；".join(
            f"{key}={value}" for key, value in source["original_source_dates"].items()
        )
        rows.append(
            (
                _cell(source["name"]),
                _cell(source["kind"]),
                _cell(source["byte_count"]),
                _cell(source["sha256"]),
                _cell(dates) or "（未摘录单一日期；详见原始附件）",
            )
        )
    lines.append(_table(SOURCE_TABLE_HEADER, rows))
    lines.append("")
    attachment_rows = [
        (
            f'[{source["name"]}]({source["attachment_path"]})',
            _cell(source["origin_path"]),
        )
        for source in payload["sources"]
    ]
    lines.append(_table(("导出附件路径", "原仓库路径"), attachment_rows))
    lines.append("")
    return lines


def _md_value_profile_section(payload: dict[str, Any]) -> list[str]:
    profile = payload["value_profile"]
    lines = ["## 二、原始价值画像（value_profile）", ""]
    lines.append(
        f"来源 `{profile['source_name']}`；合同 `{profile['contract']}`；"
        f"as_of_trade_date `{profile['as_of_trade_date']}`。"
    )
    lines.append("")
    lines.append("### 2.1 latest_observations（原样状态与十进制）")
    lines.append("")
    rows = []
    for key, observation in profile["latest_observations"].items():
        rows.append(
            (
                _cell(key),
                _cell(observation.get("status")),
                _cell(observation.get("trade_date")),
                _cell(observation.get("value_decimal")),
                _cell(observation.get("value")),
                _cell(observation.get("score_eligible")),
                _cell(observation.get("lineage")),
            )
        )
    lines.append(_table(OBSERVATION_TABLE_HEADER, rows))
    lines.append("")
    lines.append(DECIMAL_POLICY_NOTE)
    lines.append("")
    lines.append("### 2.2 capital_return（含 ROIC 限制）")
    lines.append("")
    for metric, record in profile["capital_return"].items():
        lines.append(f"- `{metric}`")
        for key, value in record.items():
            lines.append(f"  - {key}: {_display(value)}")
    lines.append("")
    roic = profile["capital_return"]["roic"]
    lines.append(
        "**资本回报限制**：ROIC 为 `"
        + _display(roic.get("status"))
        + "`（"
        + _display(roic.get("decision_code"))
        + "）。缺失输入既不是 0，也不是负值，也不构成资本回报差的结论。"
    )
    lines.append("")
    lines.append("### 2.3 integrated_layers（原样状态，无新增综合分）")
    lines.append("")
    layer_rows = [(_cell(key), _cell(value)) for key, value in profile["integrated_layers"].items()]
    lines.append(_table(("layer", "status"), layer_rows))
    lines.append("")
    return lines


def _md_timeline_section(payload: dict[str, Any]) -> list[str]:
    timeline = payload["timeline"]
    lines = ["## 三、PIT 财务状态时间线（period_end / effective_from / value / status）", ""]
    lines.append(
        f"来源 `{timeline['source_name']}`；每个状态给出 period_end、effective_from、"
        "value_decimal、status 与来源 Fact/状态 ID。"
    )
    lines.append("")
    summary_rows = []
    for metric in TIMELINE_METRIC_ORDER:
        summary = timeline["summary"].get(metric, {})
        summary_rows.append(
            (
                _cell(metric),
                _cell(summary.get("state_count")),
                _cell(summary.get("computed_count")),
                _cell(summary.get("missing_ttm_input_count")),
                _cell(summary.get("first_effective_from")),
                _cell(summary.get("last_effective_from")),
            )
        )
    lines.append(
        _table(
            TIMELINE_SUMMARY_HEADER,
            summary_rows,
        )
    )
    lines.append("")
    for metric in TIMELINE_METRIC_ORDER:
        lines.append(f"### 3.{TIMELINE_METRIC_ORDER.index(metric) + 1} {metric}")
        lines.append("")
        rows = []
        for state in timeline["timelines"][metric]:
            rows.append(
                (
                    _cell(state.get("fiscal_year")),
                    _cell(state.get("report_type")),
                    _cell(state.get("period_end")),
                    _cell(state.get("effective_from")),
                    _cell(state.get("value_decimal")),
                    _cell(state.get("status")),
                    _cell(state.get("available_at_max")),
                    _nested_cell(state.get("input_available_at")),
                    _cell(state.get("financial_state_id")),
                )
            )
        lines.append(_table(TIMELINE_STATE_HEADER, rows))
        lines.append("")
    return lines


def _md_percentiles_section(payload: dict[str, Any]) -> list[str]:
    percentiles = payload["valuation_percentiles"]
    lines = ["## 四、原始 TTM/MRQ 估值分位（与非 TTM 年度估值倍数分开）", ""]
    lines.append(
        f"来源 `{percentiles['source_name']}`；"
        f"as_of_trade_date `{percentiles['as_of_trade_date']}`；"
        f"方法 `{_display(percentiles['method'].get('rank_method'))}`，"
        f"十进制策略 `{_display(percentiles['method'].get('decimal_policy'))}`。"
    )
    lines.append("")
    rows = []
    for record in percentiles["records"]:
        rows.append(
            (
                _cell(record.get("metric_id")),
                _cell(record.get("window_id")),
                _cell(record.get("calendar_start")),
                _cell(record.get("effective_first_trade_date")),
                _cell(record.get("current_ratio_decimal")),
                _cell(record.get("strict_percentile_decimal")),
                _cell(record.get("weak_percentile_decimal")),
                _cell(record.get("midrank_percentile_decimal")),
                _cell(record.get("eligible_sample_count")),
                _cell(record.get("excluded_sample_count")),
                _cell(record.get("coverage_status")),
                _cell(record.get("percentile_record_id")),
            )
        )
    lines.append(_table(PERCENTILE_TABLE_HEADER, rows))
    lines.append("")
    lines.append(
        "分位为描述性相对估值证据；低 PE 不自动等于低估。"
        "年度盈利估值倍数、FCF proxy 收益率等原始观测见第二节 latest_observations，"
        "两者不合并、不互换。"
    )
    lines.append("")
    return lines


def _md_shadows_section(payload: dict[str, Any]) -> list[str]:
    shadows = payload["shadow_dimensions"]
    lines = ["## 五、影子维度（非生产，不得作为评分或结论）", ""]
    lines.append(
        f"来源 `{shadows['source_name']}`；`non_production={_display(shadows['non_production'])}`、"
        f"`score_eligible={_display(shadows['score_eligible'])}`、"
        f"`overall_score_prohibited={_display(shadows['overall_score_prohibited'])}`、"
        f"`recommendation_prohibited={_display(shadows['recommendation_prohibited'])}`。"
    )
    lines.append("")
    coverage_rows = []
    for entry in shadows["component_coverage"]:
        coverage_rows.append(
            (
                _cell(entry["dimension_id"]),
                _cell(entry["status"]),
                _cell(entry["coverage_ratio"]),
                _cell(entry["covered_weight"]),
                _cell(entry["missing_component_ids"]),
                _cell(entry["blocked_component_ids"]),
            )
        )
    lines.append(_table(COVERAGE_TABLE_HEADER, coverage_rows))
    lines.append("")
    lines.append("### 5.1 组件明细（缺失=覆盖缺口，不是零分）")
    lines.append("")
    component_rows = []
    for dimension_id in shadows["dimension_order"]:
        dimension = shadows["dimensions"][dimension_id]
        components = dimension.get("components")
        if not isinstance(components, dict):
            representation = _display(dimension.get("representation"))
            lines.append(f"- `{dimension_id}`：`{representation}`（状态输出，无合并数值）")
            continue
        for component_id, component in components.items():
            component_rows.append(
                (
                    _cell(dimension_id),
                    _cell(component_id),
                    _cell(component.get("status")),
                    _cell(component.get("score")),
                    _cell(component.get("eligible")),
                    _cell(component.get("covered")),
                    _cell(component.get("source")),
                    _cell(component.get("note")),
                )
            )
    lines.append(_table(COMPONENT_TABLE_HEADER, component_rows))
    lines.append("")
    return lines


def _md_pe_section(payload: dict[str, Any]) -> list[str]:
    decision = payload["pe_disposition"]
    lines = ["## 六、PE 处置决定（数值评分已暂缓）", ""]
    lines.append(f"- decision: `{decision['decision']}`")
    lines.append(f"- verdict: `{decision['verdict']}`")
    lines.append(f"- upstream_decision: `{decision['upstream_decision']}`")
    lines.append(f"- stage: `{decision['stage']}`；subject: `{decision['subject']}`")
    lines.append("")
    evidence_rows = [(_cell(key), _cell(value)) for key, value in decision["pe_evidence"].items()]
    lines.append(_table(("pe_evidence", "value"), evidence_rows))
    lines.append("")
    policy_rows = [(_cell(key), _cell(value)) for key, value in decision["scoring_policy"].items()]
    lines.append(_table(("scoring_policy", "value"), policy_rows))
    lines.append("")
    lines.append("### 6.1 冻结 5 年证据计数（原样）")
    lines.append("")
    frozen_rows = [
        (_cell(key), _cell(value)) for key, value in decision["frozen_5y_evidence"].items()
    ]
    lines.append(_table(("frozen_5y_evidence", "value"), frozen_rows))
    lines.append("")
    m2_rows = [(_cell(key), _cell(value)) for key, value in decision["m2_status"].items()]
    lines.append(_table(("m2_status", "value"), m2_rows))
    lines.append("")
    return lines


def _md_risk_section(payload: dict[str, Any]) -> list[str]:
    risk = payload["risk_observations"]
    lines = ["## 七、风险观测（八个风险；缺失证据不是负面结论）", ""]
    lines.append(
        f"来源 `{risk['source_name']}`；合同 `{risk['contract']}`；"
        f"as_of_date `{risk['as_of_date']}`；状态 `{risk['status']}`；"
        f"expected_risk_count=`{_display(risk['expected_risk_count'])}`、"
        f"observation_count=`{_display(risk['observation_count'])}`、"
        f"missing_evidence_count=`{_display(risk['missing_evidence_count'])}`。"
    )
    lines.append("")
    rows = []
    for record in risk["observations"]:
        rows.append(
            (
                _cell(record.get("risk_id")),
                _cell(record.get("status")),
                _cell(record.get("observation_id")),
                _cell(record.get("available_at")),
                _cell(record.get("lineage_status")),
                _cell(record.get("missing_reasons")),
                _cell(record.get("evidence_id_count")),
                _cell(record.get("event_id_count")),
                _cell(record.get("search_register_id")),
                _cell(record.get("search_coverage_end")),
            )
        )
    lines.append(_table(RISK_TABLE_HEADER, rows))
    lines.append("")
    warning_rows = [
        (_cell(index + 1), _cell(warning)) for index, warning in enumerate(risk["warnings"])
    ]
    lines.append(_table(("警告序号", "原始警告文本"), warning_rows))
    lines.append("")
    return lines


def _md_gaps_section(payload: dict[str, Any]) -> list[str]:
    gaps = payload["explicit_gaps"]
    lines = ["## 八、显式缺口台账（全部 18 条，原样）", ""]
    lines.append(
        f"来源 `{gaps['source_name']}`；as_of_date `{gaps['as_of_date']}`；"
        f"声明缺口数 `{_display(gaps['declared_current_gap_count'])}`，"
        f"本次汇编实际输出 `{gaps['gap_count']}` 条。"
    )
    lines.append("")
    count_rows = [(_cell(key), _cell(value)) for key, value in gaps["count_contract"].items()]
    lines.append(_table(("count_contract", "value"), count_rows))
    lines.append("")
    for index, row in enumerate(gaps["rows"], start=1):
        lines.append(f"### 8.{index} `{_cell(row.get('gap_id'))}`")
        lines.append("")
        for key, value in row.items():
            lines.append(f"- {key}: {_display(value)}")
        lines.append("")
    return lines


def _md_narrative_section(source_name: str, text: str, link: str) -> list[str]:
    lines = [f"### {source_name}", ""]
    lines.append(f"原始说明：[{link}]({link})（内容为原报告的逐字副本）。")
    lines.append("")
    lines.extend(text.splitlines())
    lines.append("")
    return lines


def render_markdown(bundle: SourceBundle) -> str:
    """Render the readable Chinese Markdown compilation from the fixed sources."""
    payload = build_payload(bundle)
    lines: list[str] = [
        "# 中石油（601857.SH）M2 离线研究包",
        "",
        "本文件把九个已冻结的基线报告汇编为一份可读文档：固定来源、固定顺序、不新增计算。",
        "",
        "## 汇编性质与边界",
        "",
        "- 这是**混合日期的历史汇编**：原始日期分别按来源保留。",
        "- 这不是统一 as-of 时点的 PIT 查询，也不是研究刷新；"
        "本工具不重新获取、不重新计算任何证据。",
        "- 本工具**不选择输入来源**，不按分数排序，不产生任何总体评分、排名、资格判定或建议结论。",
        "- " + DECIMAL_POLICY_NOTE,
        "- 源报告的 SHA256 仅用于附件完整性核对，不代表研究结论被重新验证。",
        "- 导出目录中的源附件是原报告的逐字字节副本；附件内引用的路径属于原仓库上下文。",
        "",
    ]
    lines.extend(_md_sources_section(payload))
    lines.extend(_md_value_profile_section(payload))
    lines.extend(_md_timeline_section(payload))
    lines.extend(_md_percentiles_section(payload))
    lines.extend(_md_shadows_section(payload))
    lines.extend(_md_pe_section(payload))
    lines.extend(_md_risk_section(payload))
    lines.extend(_md_gaps_section(payload))
    lines.append("## 九、非生产边界（无总体评分、无结论）")
    lines.append("")
    boundary = payload["nonproduction_boundary"]
    for key in (
        "score_eligible",
        "production_eligible",
        "overall_score_prohibited",
        "recommendation_prohibited",
        "ranking_produced",
        "eligibility_assessed",
        "inferred_conclusion",
    ):
        lines.append(f"- {key}: `{_display(boundary[key])}`")
    lines.append("")
    for note in boundary["notes"]:
        lines.append(f"- {note}")
    lines.append("")
    lines.append("## 十、原报告叙事附录")
    lines.append("")
    lines.append(
        "以下两份原报告为固定来源清单中的叙事报告，按原字节保留并在导出目录中提供附件链接；"
        "其正文引用的路径属于原仓库上下文（例如 `acceptance/`、`docs/`、`events/`），"
        "不在本离线包内。"
    )
    lines.append("")
    for source in bundle.sources:
        if source.name in MARKDOWN_SOURCE_REPORTS:
            text = source.document
            if not isinstance(text, str):
                raise BundleError("NARRATIVE_UNREADABLE")
            if len(source.payload_bytes) <= NARRATIVE_MAX_BYTES:
                lines.extend(_md_narrative_section(source.name, text, source.relative_path))
            else:
                lines.extend(
                    _md_narrative_section(
                        source.name,
                        f"（原报告共 {len(source.payload_bytes)} 字节，"
                        f"完整逐字内容见附件 {source.relative_path}。）",
                        source.relative_path,
                    )
                )
    rendered = "\n".join(lines)
    if not rendered.endswith("\n"):
        rendered += "\n"
    return rendered


def render_json(bundle: SourceBundle) -> str:
    """Render the canonical JSON projection (sorted keys, one trailing newline)."""
    text = json.dumps(build_payload(bundle), ensure_ascii=False, indent=2, sort_keys=True)
    return text + "\n"


# --------------------------------------------------------------------------------------
# Export and verification
# --------------------------------------------------------------------------------------


def expected_managed_files() -> list[str]:
    """The exact eleven managed files: nine source attachments plus both rendered reports."""
    return [REPORT_MARKDOWN_NAME, REPORT_JSON_NAME] + [
        f"{SOURCES_REPORTS_DIR}/{name}" for name in SOURCE_REPORTS
    ]


def build_bundle_files(bundle: SourceBundle) -> dict[str, bytes]:
    """Assemble every managed artifact in memory before any output path is created."""
    files: dict[str, bytes] = {
        REPORT_MARKDOWN_NAME: render_markdown(bundle).encode("utf-8"),
        REPORT_JSON_NAME: render_json(bundle).encode("utf-8"),
    }
    for source in bundle.sources:
        files[source.relative_path] = source.payload_bytes
    return files


def build_manifest(files: dict[str, bytes]) -> dict[str, Any]:
    """Build the deterministic checksum manifest for the exact managed file set."""
    entries = []
    for name in expected_managed_files():
        payload = files[name]
        entries.append(
            {
                "path": name,
                "byte_count": len(payload),
                "sha256": sha256_bytes(payload),
            }
        )
    body = {
        "schema": MANIFEST_SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "managed_file_count": len(entries),
        "files": entries,
        "verification": {
            "recomputes_from_retained_sources": True,
            "re_renders_reports": True,
            "trusts_recorded_hashes": False,
            "pinned_source_hashes_enforced": True,
            "arbitrary_manifest_paths_accepted": False,
            "current_timestamp_recorded": False,
        },
        "total_byte_count": sum(entry["byte_count"] for entry in entries),
    }
    body["artifact_digest"] = sha256_bytes(manifest_digest_bytes(body))
    return body


def manifest_digest_bytes(manifest: dict[str, Any]) -> bytes:
    """Canonical serialization of a manifest body *without* its own digest field."""
    body = {key: manifest[key] for key in manifest if key != "artifact_digest"}
    return _canonical_json_bytes(body)


def canonical_manifest_bytes(manifest: dict[str, Any]) -> bytes:
    """Canonical serialization of a complete manifest, used for file bytes and re-hashing."""
    return _canonical_json_bytes(manifest)


def _canonical_json_bytes(body: dict[str, Any]) -> bytes:
    text = json.dumps(body, ensure_ascii=False, indent=2, sort_keys=True)
    return (text + "\n").encode("utf-8")


def _assert_output_available(output: Path) -> None:
    """Reject any pre-existing path, including a symlink, before anything is created."""
    try:
        if output.is_symlink():
            raise BundleError("OUTPUT_PATH_EXISTS")
        if output.exists():
            raise BundleError("OUTPUT_PATH_EXISTS")
    except OSError as error:
        raise BundleError("OUTPUT_PATH_EXISTS") from error


def _write_bytes(path: Path, payload: bytes) -> None:
    try:
        path.write_bytes(payload)
    except OSError as error:
        raise BundleError("OUTPUT_WRITE_FAILED") from error


def export_bundle(bundle: SourceBundle, output: Path) -> dict[str, Any]:
    """Write the assembled bundle into a new directory and return the manifest."""
    files = build_bundle_files(bundle)
    manifest = build_manifest(files)
    manifest_bytes = canonical_manifest_bytes(manifest)
    _assert_output_available(output)
    try:
        output.mkdir(parents=True, exist_ok=False)
        (output / SOURCES_REPORTS_DIR).mkdir(parents=True, exist_ok=False)
    except FileExistsError as error:
        raise BundleError("OUTPUT_PATH_EXISTS") from error
    except OSError as error:
        raise BundleError("OUTPUT_WRITE_FAILED") from error
    for name in expected_managed_files():
        _write_bytes(output / name, files[name])
    _write_bytes(output / MANIFEST_NAME, manifest_bytes)
    return manifest


def _manifest_file_entries(manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    entries = manifest.get("files")
    if not isinstance(entries, list):
        raise BundleError("VERIFY_MANIFEST_INVALID")
    by_path: dict[str, dict[str, Any]] = {}
    for entry in entries:
        if not isinstance(entry, dict):
            raise BundleError("VERIFY_MANIFEST_INVALID")
        path = entry.get("path")
        if not isinstance(path, str) or not path or path in by_path:
            raise BundleError("VERIFY_MANIFEST_INVALID")
        by_path[path] = entry
    return by_path


def verify_bundle(directory: Path) -> dict[str, Any]:
    """Verify an exported bundle from its retained bytes, independently of the repository."""
    if directory.is_symlink() or not directory.is_dir():
        raise BundleError("VERIFY_DIRECTORY_MISSING")
    for name in [MANIFEST_NAME, *expected_managed_files()]:
        path = directory / name
        if path.is_symlink() or not path.resolve().is_relative_to(directory.resolve()):
            raise BundleError("VERIFY_MANIFEST_INVALID")
    manifest_path = directory / MANIFEST_NAME
    if not manifest_path.is_file():
        raise BundleError("VERIFY_MANIFEST_UNREADABLE")
    try:
        manifest = json.loads(manifest_path.read_bytes().decode("utf-8"))
    except (OSError, UnicodeDecodeError, ValueError) as error:
        raise BundleError("VERIFY_MANIFEST_UNREADABLE") from error
    if not isinstance(manifest, dict) or manifest.get("schema") != MANIFEST_SCHEMA:
        raise BundleError("VERIFY_MANIFEST_INVALID")
    recorded_digest = manifest.get("artifact_digest")
    if not isinstance(recorded_digest, str):
        raise BundleError("VERIFY_MANIFEST_INVALID")
    if sha256_bytes(manifest_digest_bytes(manifest)) != recorded_digest:
        raise BundleError("VERIFY_MANIFEST_MISMATCH")
    entries = _manifest_file_entries(manifest)
    managed = expected_managed_files()
    if sorted(entries) != sorted(managed):
        raise BundleError("VERIFY_MANIFEST_INVALID")

    retained: list[BundleSource] = []
    for name in SOURCE_REPORTS:
        relative = f"{SOURCES_REPORTS_DIR}/{name}"
        path = directory / relative
        raw = _read_source_bytes(path, "VERIFY_SOURCE_MISSING")
        pinned = PINNED_SOURCE_SHA256[name]
        if sha256_bytes(raw) != pinned:
            raise BundleError("VERIFY_SOURCE_CORRUPT")
        record = entries[relative]
        if record.get("byte_count") != len(raw) or record.get("sha256") != pinned:
            raise BundleError("VERIFY_MANIFEST_MISMATCH")
        document: Any = None
        if name in JSON_SOURCE_REPORTS:
            try:
                document = json.loads(raw.decode("utf-8"))
            except (UnicodeDecodeError, ValueError) as error:
                raise BundleError("VERIFY_SOURCE_CORRUPT") from error
        else:
            try:
                document = raw.decode("utf-8")
            except UnicodeDecodeError as error:
                raise BundleError("VERIFY_SOURCE_CORRUPT") from error
        retained.append(
            BundleSource(
                name=name,
                origin_path=SOURCE_ORIGIN_PATHS[name],
                relative_path=relative,
                sha256=pinned,
                byte_count=len(raw),
                payload_bytes=raw,
                document=document,
            )
        )
    replay = SourceBundle(sources=tuple(retained))
    validate_bundle(replay)
    rendered = build_bundle_files(replay)
    for name in managed:
        path = directory / name
        if not path.is_file():
            raise BundleError("VERIFY_COMPANION_MISSING")
        raw = _read_source_bytes(path, "VERIFY_COMPANION_MISSING")
        record = entries[name]
        if record.get("byte_count") != len(raw) or record.get("sha256") != sha256_bytes(raw):
            raise BundleError("VERIFY_MANIFEST_MISMATCH")
        if raw != rendered[name]:
            raise BundleError("VERIFY_RENDER_MISMATCH")
    if manifest != build_manifest(rendered):
        raise BundleError("VERIFY_MANIFEST_MISMATCH")
    return {
        "schema": SCHEMA_ID,
        "status": "verified",
        "managed_file_count": len(managed),
        "verified_file_count": len(managed),
        "re_rendered_from_retained_sources": True,
        "pinned_source_hashes_enforced": True,
        "sources": [
            {
                "name": source.name,
                "attachment_path": source.relative_path,
                "byte_count": source.byte_count,
                "sha256": source.sha256,
                "original_source_dates": source_dates(source),
            }
            for source in retained
        ],
    }


# --------------------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------------------


class _SanitizedParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:  # noqa: ARG002 - sanitized by design
        raise BundleError("UNEXPECTED_FAILURE")


def _build_parser() -> argparse.ArgumentParser:
    parser = _SanitizedParser(
        prog="python -m ashare_research.tools.value_research_bundle",
        description="离线汇编中石油 M2 固定来源研究包（默认 Markdown 标准输出）。",
        add_help=True,
        allow_abbrev=False,
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--json", action="store_true", help="输出规范 JSON 而非 Markdown")
    mode.add_argument(
        "--output",
        metavar="NEW_DIR",
        help="导出到新目录（report.md/report.json/源附件/manifest.json）",
    )
    mode.add_argument("--verify", metavar="DIR", help="从保留字节独立复核已导出目录")
    return parser


def _fail(code: str) -> int:
    code = code if code in KNOWN_ERROR_CODES else "UNEXPECTED_FAILURE"
    sys.stderr.buffer.write(f"error: {code}\n".encode())
    sys.stderr.buffer.flush()
    return 1


def _emit(text: str) -> None:
    """Write UTF-8 bytes regardless of the ambient console encoding."""
    sys.stdout.buffer.write(text.encode("utf-8"))
    sys.stdout.buffer.flush()


def main(argv: list[str] | None = None) -> int:
    """Entry point.  Returns a process exit code; known failures print no stdout."""
    try:
        arguments = _build_parser().parse_args(sys.argv[1:] if argv is None else argv)
    except BundleError:
        return _fail("UNEXPECTED_FAILURE")
    except SystemExit as exit_request:  # argparse help / usage
        code = exit_request.code
        return code if isinstance(code, int) else 2
    try:
        if arguments.verify is not None:
            result = verify_bundle(Path(arguments.verify))
            _emit(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
            return 0
        if arguments.output is not None:
            bundle = load_source_bundle()
            manifest = export_bundle(bundle, Path(arguments.output))
            if arguments.json:
                _emit(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
            else:
                _emit(
                    "exported "
                    + str(manifest["managed_file_count"])
                    + " managed files, "
                    + str(manifest["total_byte_count"])
                    + " bytes\n"
                )
            return 0
        bundle = load_source_bundle()
        _emit(render_json(bundle) if arguments.json else render_markdown(bundle))
        return 0
    except BundleError as error:
        return _fail(error.code)
    except Exception:  # noqa: BLE001 - known failures are sanitized, never traced
        return _fail("UNEXPECTED_FAILURE")


if __name__ == "__main__":
    raise SystemExit(main())
