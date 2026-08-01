"""Build PetroChina's 2021-2025 consolidated net_profit fact foundation.

Stage 2D-E offline runner.  It rebuilds and verifies the frozen Stage 2D-B
180-fact base and the frozen Stage 2D-D 70 Metric Result base (63 prior +
7 ROE), then registers the five annual duration ``net_profit`` facts --
the directly disclosed audited consolidated income statement "净利润"
line (parent + minority interests) -- via Rule 005
(``RECON_OFFICIAL_NUMERIC_005`` v1), and applies four comparison-column
restatement reviews (2021<-2022 .. 2024<-2025).  Only the two
concept-years that actually changed (R = 2: FY2022 and FY2023) get v2
three-role superseding facts; unchanged years never get fake versions and
FY2025 is ``not_yet_reviewable``.

The value is the direct disclosure line only: the
``net_profit_attributable_to_parent`` + minority-interest sum is an
evidence-stage cross-check (``income_statement_bridge``), never a fact
input.  Company/exchange values must be exactly equal; reconciliation is
dual-source verification with no tolerance, no averaging and no source
preference.

It emits ``net_profit_input_readiness.json`` registering the 2021-2025
latest reconciled facts as ready ROA-numerator inputs.  It never computes
ROA, ROIC or any score, never opens a PDF, never accesses the shared
cache or network, and never writes the default research database.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import shutil
import tempfile
from dataclasses import asdict
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

from ashare_research.facts.as_of import AsOfQuery
from ashare_research.facts.contexts import build_context_id
from ashare_research.facts.identity import build_fact_id
from ashare_research.facts.repository import FactRepository
from ashare_research.reconciliation.engine import (
    NET_PROFIT_RECONCILIATION_RULE,
    NET_PROFIT_RULE_ID,
    NET_PROFIT_RULE_VERSION,
    ReconciliationEngine,
)
from ashare_research.reconciliation.models import ReconciliationStatus
from ashare_research.reconciliation.service import (
    OfficialFactReconciliationService,
)
from ashare_research.storage.duckdb_store import DuckDBStore
from ashare_research.tools.official_earnings_quality_fact_foundation import (
    DEFAULT_DB,
    DEFAULT_DB_SHA256,
    REVIEW_DIR,
    SYMBOL,
)
from ashare_research.tools.official_fact_acceptance import load_bundle
from ashare_research.tools.official_roe_metric_extension import (
    COMBINED_EXPECTED,
    EXPECTED_COUNTS_REF_DIGEST,
    PRIOR_63_SEMANTIC_SHA256,
    ROE_EXPECTED,
    UPSTREAM_180_FACT_ID_SET_SHA256,
    run_roe_metric_extension,
)

ROOT = Path(__file__).resolve().parents[3]
BUNDLE_DIR = ROOT / "acceptance/fixtures/official_facts/601857.SH"
SUPP_DIR = BUNDLE_DIR / "supplemental"

CONTRACT = "net_profit_official_facts_v1"
REVIEW_CONTRACT = "net_profit_restatement_evidence_v1"
INTEGRATION_CONTRACT = "net_profit_2021_2025_foundation_v1"
READINESS_CONTRACT = "net_profit_input_readiness_v1"
YEARS = (2021, 2022, 2023, 2024, 2025)
CONCEPT = "net_profit"
UPSTREAM_FACT_COUNT = 180
UPSTREAM_ELIGIBLE_COUNT = 60
UPSTREAM_PIT_COUNT = 47
UPSTREAM_VERSION_LINKS = 39
UPSTREAM_132_FACT_ID_SET_SHA256 = (
    "1e5267022b8062acf96fb413f09ecfc737c706b786c9f02a0b1dc3834fab604d"
)
# Frozen Stage 2D-D combined 70 Metric Result ID set digest, computed as
# sha256("\n".join(sorted ids)) -- the format pinned by the Stage 2D-D
# role-binding-fix test.
COMBINED_70_RESULT_ID_SET_SHA256 = (
    "bdd9d4fee9777f0c28f31056711675ab3acf98786bc09090cde25ab7ef551df0"
)
# Contexts: 5 duration (2021-2025) + 6 instant (2020-2025); reused, no
# new context is registered by this stage.
EXPECTED_CONTEXTS = 11
# R = the number of changed concept-years across the 2021-2024 comparison
# reviews; FY2022 (Interpretation 16 / IAS 12) and FY2023 (common-control
# business combination) changed; FY2021 and FY2024 are unchanged.
EXPECTED_R = 2
EXPECTED_CHANGED_YEARS = (2022, 2023)

EVIDENCE_PATHS = {
    year: SUPP_DIR / f"{year}_net_profit.json" for year in YEARS
}
# target_year -> restatement evidence path (review by next year's report).
RESTATEMENT_PATHS = {
    year: REVIEW_DIR / f"net_profit_{year}_reviewed_by_{year + 1}.json"
    for year in (2021, 2022, 2023, 2024)
}
# Comparison-column pages in the RESTATING (next-year) report for v2
# facts: FY2022 v2 from the 2023 report, FY2023 v2 from the 2024 report.
V2_SOURCE_PAGES = {2022: (114, 112), 2023: (115, 113)}
# Annual report availability (max of company/exchange announcement dates).
ANNUAL_REPORT_DATES = {
    2021: "2022-04-01",
    2022: "2023-03-30",
    2023: "2024-03-26",
    2024: "2025-03-31",
    2025: "2026-03-30",
}
# Annual combined latest-Fact PIT including net_profit:
# upstream 11/20/29/38/47 + cumulative net_profit facts (1..5).
EXPECTED_ANNUAL_PIT = {2021: 12, 2022: 22, 2023: 32, 2024: 42, 2025: 52}
EXPECTED_FINAL_PIT = 52
REVISION_REVIEW_STATUS = {
    2021: "reviewed_unchanged",
    2022: "reviewed_changed",
    2023: "reviewed_changed",
    2024: "reviewed_unchanged",
    2025: "not_yet_reviewable",
}


class NetProfitFoundationError(ValueError):
    """A deterministic evidence or integration gate failed."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise NetProfitFoundationError(message)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git_blob_id(path: Path) -> str:
    content = path.read_bytes()
    header = f"blob {len(content)}\0".encode()
    return hashlib.sha1(header + content).hexdigest()  # noqa: S324


def _id_set_digest(ids: list[str]) -> str:
    payload = json.dumps(sorted(ids), separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()


def _newline_id_set_digest(ids: list[str]) -> str:
    return hashlib.sha256("\n".join(sorted(ids)).encode()).hexdigest()


def _jsonable(value: Any) -> Any:
    if isinstance(value, Path):
        return value.name
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, list | tuple):
        return [_jsonable(item) for item in value]
    if hasattr(value, "item"):
        return value.item()
    if isinstance(value, date | datetime):
        return value.isoformat()
    return value


def _write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(_jsonable(value), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _load_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    _require(isinstance(value, dict), f"{path.name}: expected JSON object")
    return value


def build_run_id(now: datetime | None = None) -> str:
    timestamp = (now or datetime.now()).strftime("%Y%m%d_%H%M%S_%f")
    return f"net_profit_601857_SH_2021_2025_{timestamp}"


def _duration_context_id(fiscal_year: int) -> str:
    return build_context_id(SYMBOL, fiscal_year, "annual", "consolidated")


def _validate_evidence_fact(item: dict[str, Any], source: str, year: int) -> None:
    _require(
        item.get("concept_id") == CONCEPT,
        f"{source}/{year}: evidence concept differs",
    )
    _require(
        isinstance(item.get("pdf_page"), int)
        and isinstance(item.get("printed_page"), int),
        f"{source}/{year}: page fields differ",
    )
    for field in (
        "source_page",
        "source_table",
        "source_label",
        "column_label",
        "raw_value",
        "raw_unit",
        "normalization_rule",
        "evidence_type",
        "manual_review_status",
    ):
        _require(
            bool(str(item.get(field, "")).strip()),
            f"{source}/{year}: missing {field}",
        )
    _require(
        item["source_label"] == "净利润",
        f"{source}/{year}: the direct '净利润' disclosure line is required",
    )
    _require(
        item["manual_review_status"] == "visually_verified_twice",
        f"{source}/{year}: manual review differs",
    )
    _require(
        item["evidence_type"] == "audited_consolidated_income_statement",
        f"{source}/{year}: evidence type differs",
    )
    _require(
        item.get("official_direct_disclosure") is True,
        f"{source}/{year}: direct disclosure flag differs",
    )
    raw = int(str(item["raw_value"]))
    normalized = int(item["expected_normalized_value"])
    _require(
        raw * 100 == normalized,
        f"{source}/{year}: million-to-10k conversion differs",
    )
    _require(
        abs(normalized) <= 2**53 - 1,
        f"{source}/{year}: exceeds safe integer range",
    )


def _resolve_document(
    evidence: dict[str, Any], bundle: dict[str, Any], source: str,
) -> dict[str, Any]:
    """Use an evidence-level documents override when present (2021 company
    = 555a24ed results announcement text layer), else the base bundle
    document."""
    override = evidence.get("documents")
    if isinstance(override, dict) and source in override:
        document = override[source]
        resolved = {
            "source_provider": document["source_provider"],
            "source_id": document["source_id"],
            "source_tier": document["source_tier"],
            "source_document": document["source_document"],
            "final_pdf_url": document["final_pdf_url"],
            "sha256": document["sha256"],
            "announcement_date": document["announcement_date"],
        }
    else:
        document = bundle["documents"][source]
        resolved = {
            "source_provider": document["source_provider"],
            "source_id": document["source_id"],
            "source_tier": document["source_tier"],
            "source_document": document["source_document"],
            "final_pdf_url": document["final_pdf_url"],
            "sha256": document["sha256"],
            "announcement_date": document["announcement_date"],
        }
    _require(
        resolved["source_tier"] == f"{source}_official",
        f"{source}: source tier differs",
    )
    for field, value in resolved.items():
        _require(
            bool(str(value).strip()), f"{source}: document missing {field}",
        )
    return resolved


def _validate_evidence(year: int, bundle: dict[str, Any]) -> dict[str, Any]:
    """Validate one supplemental net_profit evidence file in memory."""
    evidence = _load_object(EVIDENCE_PATHS[year])
    base_path = (ROOT / str(evidence.get("base_bundle_path", ""))).resolve()
    expected_base = Path(bundle["_bundle_path"]).resolve()  # type: ignore[arg-type]
    _require(base_path == expected_base, f"{year}: base bundle path differs")
    _require(
        evidence.get("base_bundle_sha256") == _sha256(expected_base),
        f"{year}: base bundle SHA-256 differs",
    )
    _require(
        evidence.get("base_bundle_git_blob") == _git_blob_id(expected_base),
        f"{year}: base bundle Git blob differs",
    )
    _require(evidence.get("contract") == CONTRACT, f"{year}: contract differs")
    _require(
        evidence.get("symbol") == SYMBOL and evidence.get("fiscal_year") == year,
        f"{year}: symbol/fiscal_year differs",
    )
    _require(
        evidence.get("period_type") == "duration"
        and evidence.get("period_start") == f"{year}-01-01"
        and evidence.get("period_end") == f"{year}-12-31",
        f"{year}: duration period differs",
    )
    _require(
        (
            evidence.get("reconciliation_rule_id"),
            evidence.get("reconciliation_rule_version"),
        )
        == (NET_PROFIT_RULE_ID, NET_PROFIT_RULE_VERSION),
        f"{year}: Rule 005 binding differs",
    )
    _require(
        evidence.get("revision_review_status")
        == REVISION_REVIEW_STATUS[year],
        f"{year}: revision review status differs",
    )
    # Income-statement bridge: attributable + minority == net_profit is a
    # cross-check only; the fact value is the direct disclosure line.
    bridge = evidence.get("income_statement_bridge", {})
    _require(
        bridge.get("scope") == "consolidated_only"
        and bridge.get("exact_tie_out") is True
        and int(bridge.get("net_profit_attributable_to_parent", -1))
        + int(bridge.get("minority_interest", -2))
        == int(bridge.get("net_profit_direct_disclosure_line", -3))
        == int(bridge.get("computed_attributable_plus_minority", -4)),
        f"{year}: income statement bridge does not tie exactly",
    )
    _require(
        bridge.get("bridge_status") == "cross_check_only_not_a_fact_input",
        f"{year}: bridge must not be a fact input",
    )
    sources = evidence.get("sources", {})
    _require(
        isinstance(sources, dict) and set(sources) == {"company", "exchange"},
        f"{year}: exactly company and exchange evidence are required",
    )
    by_source: dict[str, dict[str, Any]] = {}
    documents: dict[str, dict[str, Any]] = {}
    for source in ("company", "exchange"):
        document = _resolve_document(evidence, bundle, source)
        documents[source] = document
        facts = sources[source].get("facts", [])
        _require(
            isinstance(facts, list) and len(facts) == 1,
            f"{year}/{source}: expected exactly one net_profit fact",
        )
        item = facts[0]
        _validate_evidence_fact(item, source, year)
        by_source[source] = item
    _require(
        by_source["company"]["expected_normalized_value"]
        == by_source["exchange"]["expected_normalized_value"],
        f"{year}: company and exchange net_profit values differ",
    )
    return {"evidence": evidence, "by_source": by_source, "documents": documents}


def _build_net_profit_template(
    document: dict[str, Any], fiscal_year: int, *, created_at: str,
) -> dict[str, Any]:
    """A minimal shape carrier for duration net_profit fact construction.

    All identity-relevant fields are overwritten in
    ``_build_net_profit_fact``; this template only supplies the canonical
    fields required by the financial_fact schema.
    """
    return {
        "symbol": SYMBOL,
        "concept_id": CONCEPT,
        "concept_version": "1",
        "context_id": _duration_context_id(fiscal_year),
        "source_provider": document["source_provider"],
        "source_id": document["source_id"],
        "source_tier": document["source_tier"],
        "source_document": document["source_document"],
        "source_url": document["final_pdf_url"],
        "source_hash": document["sha256"],
        "fiscal_year": fiscal_year,
        "report_type": "annual",
        "period_start": f"{fiscal_year}-01-01",
        "period_end": f"{fiscal_year}-12-31",
        "filing_date": document["announcement_date"],
        "announcement_date": document["announcement_date"],
        "available_at": document["announcement_date"],
        "verification_status": "verified",
        "is_derived": False,
        "derived_from": "",
        "derivation_definition_id": "",
        "derivation_version": "",
        "input_fact_ids": "",
        "unit": "万元",
        "value": 0,
        "raw_value": 0,
        "raw_unit": "人民币百万元",
        "normalized_value": 0,
        "normalization_rule": "RMB_MILLION_TO_CNY_10K_X100",
        "fact_version": 1,
        "restatement_version": "original",
        "supersedes_fact_id": "",
        "eligible_for_metrics": False,
        "created_at": created_at,
    }


def _build_net_profit_fact(
    template: dict[str, Any],
    evidence_item: dict[str, Any],
    document: dict[str, Any],
    *,
    fiscal_year: int,
    created_at: str,
) -> dict[str, Any]:
    """Build one verified, ineligible duration net_profit fact from
    evidence (the direct "净利润" disclosure line)."""
    normalized = int(evidence_item["expected_normalized_value"])
    fact = copy.deepcopy(template)
    fact.update(
        {
            "concept_id": CONCEPT,
            "concept_version": "1",
            "value": normalized,
            "unit": "万元",
            "context_id": _duration_context_id(fiscal_year),
            "is_derived": False,
            "derived_from": "",
            "derivation_definition_id": "",
            "derivation_version": "",
            "input_fact_ids": "",
            "source_provider": document["source_provider"],
            "source_id": document["source_id"],
            "source_tier": document["source_tier"],
            "source_document": document["source_document"],
            "source_url": document["final_pdf_url"],
            "source_hash": document["sha256"],
            "source_page": evidence_item["source_page"],
            "source_table": evidence_item["source_table"],
            "source_label": evidence_item["source_label"],
            "raw_value": int(str(evidence_item["raw_value"])),
            "raw_unit": evidence_item["raw_unit"],
            "normalized_value": normalized,
            "normalization_rule": evidence_item["normalization_rule"],
            "fiscal_year": fiscal_year,
            "report_type": "annual",
            "period_start": f"{fiscal_year}-01-01",
            "period_end": f"{fiscal_year}-12-31",
            "filing_date": document["announcement_date"],
            "announcement_date": document["announcement_date"],
            "available_at": document["announcement_date"],
            "verification_status": "verified",
            "verification_note": (
                "manually verified twice against registered net_profit "
                "evidence (direct consolidated '净利润' disclosure line)"
            ),
            "fact_version": 1,
            "restatement_version": "original",
            "supersedes_fact_id": "",
            "eligible_for_metrics": False,
            "created_at": created_at,
        }
    )
    fact["fact_id"] = build_fact_id(fact)
    return fact


def preflight_evidence(*, created_at: str) -> dict[str, Any]:
    """Validate all five supplemental evidence files and preflight the
    Rule 005 reconciliation for every fiscal year."""
    bundles: dict[int, dict[str, Any]] = {}
    validated: dict[int, dict[str, Any]] = {}
    source_facts: dict[int, dict[str, dict[str, Any]]] = {}
    preflight_results = []
    engine = ReconciliationEngine(NET_PROFIT_RECONCILIATION_RULE)
    for year in YEARS:
        bundle = load_bundle(BUNDLE_DIR / f"{year}_annual.json")
        bundle["_bundle_path"] = BUNDLE_DIR / f"{year}_annual.json"
        bundles[year] = bundle
        validated[year] = _validate_evidence(year, bundle)
        docs = validated[year]["documents"]
        source_facts[year] = {}
        for source in ("company", "exchange"):
            template = _build_net_profit_template(
                docs[source], year, created_at=created_at,
            )
            source_facts[year][source] = _build_net_profit_fact(
                template,
                validated[year]["by_source"][source],
                docs[source],
                fiscal_year=year,
                created_at=created_at,
            )
        result = engine.reconcile_pair(
            source_facts[year]["company"],
            source_facts[year]["exchange"],
            now=created_at,
        )
        _require(
            result.status == ReconciliationStatus.matched
            and result.output_fact is not None,
            f"{year}: Rule 005 preflight did not match",
        )
        preflight_results.append(result)
    return {
        "bundles": bundles,
        "validated": validated,
        "source_facts": source_facts,
        "preflight_results": preflight_results,
    }


def _resolve_restatements(preflight: dict[str, Any]) -> dict[str, Any]:
    """Read all four restatement reviews, confirm the changed flag, and
    return the list of changed target years (R total)."""
    reviews: dict[int, dict[str, Any]] = {}
    changed: list[int] = []
    for target in (2021, 2022, 2023, 2024):
        review = _load_object(RESTATEMENT_PATHS[target])
        _require(
            review.get("contract") == REVIEW_CONTRACT,
            f"{target}: restatement contract differs",
        )
        _require(
            review.get("target_fiscal_year") == target
            and review.get("evidence_fiscal_year") == target + 1,
            f"{target}: restatement target/evidence years differ",
        )
        concepts = review.get("concepts", [])
        _require(
            len(concepts) == 1 and concepts[0].get("concept_id") == CONCEPT,
            f"{target}: restatement concepts differ",
        )
        item = concepts[0]
        original_fact = preflight["source_facts"][target]["company"]
        computed_changed = int(item["later_comparative_raw_value"]) != int(
            item["original_raw_value"]
        )
        _require(
            item["changed"] is computed_changed,
            f"{target}: changed flag differs",
        )
        _require(
            int(item["original_raw_value"]) == int(original_fact["raw_value"]),
            f"{target}: original value differs from preflight",
        )
        # Later comparative bridge: attributable + minority == net_profit.
        _require(
            item.get("later_comparative_bridge_exact") is True
            and int(item["later_comparative_attributable_to_parent"])
            + int(item["later_comparative_minority_interest"])
            == int(item["later_comparative_raw_value"]),
            f"{target}: later comparative bridge does not tie exactly",
        )
        if computed_changed:
            changed.append(target)
        reviews[target] = review
    r = len(changed)
    _require(r == EXPECTED_R, f"R differs: {r} (expected {EXPECTED_R})")
    _require(
        tuple(changed) == EXPECTED_CHANGED_YEARS,
        f"changed years differ: {changed} (expected {EXPECTED_CHANGED_YEARS})",
    )
    return {"reviews": reviews, "r": r, "changed": changed}


def _build_v2_raw_fact(
    predecessor: dict[str, Any],
    later_bundle: dict[str, Any],
    source: str,
    *,
    target_year: int,
    later_raw: int,
    created_at: str,
) -> dict[str, Any]:
    """Build one v2 raw duration net_profit fact from the next-year
    report's comparison column.

    Deep-copies the v1 predecessor (so ``source_id`` and the duration
    ``context_id`` carry over unchanged) and updates only the value, the
    restating-report source metadata, the available_at, and the version
    fields.  ``source_id`` is intentionally NOT updated, keeping the
    VersionChainValidator stable-identity check satisfied.
    """
    document = later_bundle["documents"][source]
    restating_year = target_year + 1
    pdf_p, printed_p = V2_SOURCE_PAGES[target_year]
    fact = copy.deepcopy(predecessor)
    fact.update(
        value=later_raw * 100,
        raw_value=later_raw,
        normalized_value=later_raw * 100,
        source_provider=document["source_provider"],
        source_tier=document["source_tier"],
        source_document=document["source_document"],
        source_url=document["final_pdf_url"],
        source_hash=document["sha256"],
        source_page=f"PDF page {pdf_p} / printed page {printed_p}",
        source_table=f"{restating_year}年度合并及公司利润表",
        source_label="净利润",
        filing_date=document["announcement_date"],
        announcement_date=document["announcement_date"],
        available_at=document["announcement_date"],
        fact_version=2,
        restatement_version="restated_1",
        supersedes_fact_id=predecessor["fact_id"],
        verification_note=(
            "visually verified twice against next-year comparative "
            "net_profit evidence (direct '净利润' disclosure line)"
        ),
        created_at=created_at,
    )
    fact["fact_id"] = build_fact_id(fact)
    return fact


def _verify_upstream_baseline(upstream: dict[str, Any]) -> None:
    """Assert the rebuilt Stage 2D-B 180-fact and Stage 2D-D 70-Result
    baselines against their frozen digests/counts."""
    _require(
        upstream.get("status") == "passed",
        "Stage 2D-D upstream metric extension failed",
    )
    up = upstream.get("upstream", {})
    _require(
        up.get("financial_facts") == UPSTREAM_FACT_COUNT
        and up.get("eligible_facts") == UPSTREAM_ELIGIBLE_COUNT
        and up.get("latest_fact_pit") == UPSTREAM_PIT_COUNT
        and up.get("version_chain_links") == UPSTREAM_VERSION_LINKS
        and up.get("fact_id_set_sha256") == UPSTREAM_180_FACT_ID_SET_SHA256,
        "Stage 2D-B frozen 180-fact baseline differs",
    )
    _require(
        upstream.get("combined_counts") == COMBINED_EXPECTED,
        "Stage 2D-D combined 70-Result counts differ",
    )
    _require(
        upstream.get("roe_counts") == ROE_EXPECTED,
        "Stage 2D-D ROE 7-version counts differ",
    )
    _require(
        upstream.get("prior_result_id_set_sha256")
        == EXPECTED_COUNTS_REF_DIGEST,
        "frozen prior-63 Result ID set differs",
    )
    _require(
        upstream.get("prior_result_semantic_sha256")
        == PRIOR_63_SEMANTIC_SHA256,
        "frozen prior-63 Result semantics differ",
    )


def _verify_metric_result_baseline(upstream_dir: Path) -> dict[str, Any]:
    """Read the rebuilt upstream metrics.duckdb and verify the frozen
    combined 70 Result ID set (read-only; hash checked before/after)."""
    metrics_path = upstream_dir / "metrics.duckdb"
    _require(metrics_path.exists(), "upstream metrics.duckdb missing")
    hash_before = _sha256(metrics_path)
    store = DuckDBStore(str(metrics_path))
    try:
        conn = store.connect()
        result_ids = [
            row[0]
            for row in conn.execute(
                "SELECT metric_result_id FROM metric_results "
                "ORDER BY metric_result_id"
            ).fetchall()
        ]
        roe_result_versions = conn.execute(
            "SELECT COUNT(*) FROM metric_results WHERE metric_id=?",
            ["return_on_average_equity_attributable_to_parent"],
        ).fetchone()[0]
        roa_count = conn.execute(
            "SELECT COUNT(*) FROM metric_results WHERE metric_id=?",
            ["return_on_average_total_assets"],
        ).fetchone()[0]
    finally:
        store.close()
    hash_after = _sha256(metrics_path)
    _require(
        hash_before == hash_after,
        "baseline verification modified upstream metrics.duckdb",
    )
    _require(
        len(result_ids) == COMBINED_EXPECTED["results"],
        f"70-Result baseline count differs: {len(result_ids)}",
    )
    _require(
        _newline_id_set_digest(result_ids)
        == COMBINED_70_RESULT_ID_SET_SHA256,
        "frozen combined 70 Result ID set differs",
    )
    _require(
        roe_result_versions == ROE_EXPECTED["result_versions"],
        "ROE 7-version baseline differs",
    )
    _require(roa_count == 0, "ROA results must not exist upstream")
    return {
        "result_count": len(result_ids),
        "id_set_sha256_newline": _newline_id_set_digest(result_ids),
        "id_set_sha256": _id_set_digest(result_ids),
        "roe_result_versions": roe_result_versions,
        "sha256_before": hash_before,
        "sha256_after": hash_after,
    }


def _collect_acceptance(
    repo: FactRepository,
    *,
    upstream_fact_ids: list[str],
    restatement: dict[str, Any],
) -> dict[str, Any]:
    conn = repo.store.connect()
    r = restatement["r"]
    counts = {
        "contexts": conn.execute(
            "SELECT COUNT(*) FROM fact_contexts"
        ).fetchone()[0],
        "financial_facts": conn.execute(
            "SELECT COUNT(*) FROM financial_facts"
        ).fetchone()[0],
        "raw_ineligible_facts": conn.execute(
            "SELECT COUNT(*) FROM financial_facts "
            "WHERE is_derived=FALSE AND eligible_for_metrics=FALSE"
        ).fetchone()[0],
        "reconciled_eligible_facts": conn.execute(
            "SELECT COUNT(*) FROM financial_facts "
            "WHERE source_tier='reconciled_derived' "
            "AND eligible_for_metrics=TRUE"
        ).fetchone()[0],
        "version_chain_links": conn.execute(
            "SELECT COUNT(*) FROM financial_facts "
            "WHERE supersedes_fact_id <> ''"
        ).fetchone()[0],
        "audit": len(AsOfQuery(repo).get_all_versions_for_audit(SYMBOL)),
        "lineage": conn.execute(
            "SELECT COUNT(*) FROM fact_lineage"
        ).fetchone()[0],
    }
    expected = {
        "contexts": EXPECTED_CONTEXTS,
        "financial_facts": 195 + 3 * r,
        "raw_ineligible_facts": 130 + 2 * r,
        "reconciled_eligible_facts": 65 + r,
        "version_chain_links": 39 + 3 * r,
        "audit": 195 + 3 * r,
        "lineage": 195 + 3 * r,
    }
    _require(
        counts == expected, f"counts differ: {counts} (expected {expected})",
    )

    current_upstream_ids = [
        row[0]
        for row in conn.execute(
            "SELECT fact_id FROM financial_facts "
            "WHERE fact_id IN (SELECT UNNEST(?)) ORDER BY fact_id",
            [upstream_fact_ids],
        ).fetchall()
    ]
    _require(
        current_upstream_ids == sorted(upstream_fact_ids)
        and _id_set_digest(current_upstream_ids)
        == UPSTREAM_180_FACT_ID_SET_SHA256,
        "upstream 180 Fact IDs changed",
    )
    # Rule 001/002/003 lineage must be unchanged from the upstream.
    for rule_id, expected_n in (
        ("RECON_OFFICIAL_NUMERIC_001", 57),
        ("RECON_OFFICIAL_NUMERIC_002", 18),
        ("RECON_OFFICIAL_NUMERIC_003", 57),
    ):
        _require(
            conn.execute(
                "SELECT COUNT(*) FROM fact_lineage "
                "WHERE reconciliation_rule_id=?",
                [rule_id],
            ).fetchone()[0] == expected_n,
            f"Rule {rule_id[-3:]} lineage changed",
        )
    # Rule 004 lineage unchanged: (12 v1 + 4 v2) x 3 roles = 48 rows.
    _require(
        conn.execute(
            "SELECT COUNT(*) FROM fact_lineage "
            "WHERE reconciliation_rule_id=?",
            ["RECON_OFFICIAL_NUMERIC_004"],
        ).fetchone()[0] == 48,
        "Rule 004 lineage changed",
    )
    # Rule 005 lineage: (5 v1 + R v2) x 3 roles.
    rule_005_lineage = conn.execute(
        """SELECT fact_id, source_tier, parent_fact_ids, role,
                  reconciliation_rule_id, reconciliation_rule_version
             FROM fact_lineage
            WHERE reconciliation_rule_id=?
            ORDER BY lineage_id""",
        [NET_PROFIT_RULE_ID],
    ).df().to_dict("records")
    _require(
        len(rule_005_lineage) == 15 + 3 * r
        and {row["reconciliation_rule_version"] for row in rule_005_lineage}
        == {NET_PROFIT_RULE_VERSION},
        "Rule 005 lineage differs",
    )

    as_of = AsOfQuery(repo)
    # Annual combined PIT: upstream + cumulative net_profit facts.
    for year, expected_pit in EXPECTED_ANNUAL_PIT.items():
        rows = as_of.get_latest_available(SYMBOL, ANNUAL_REPORT_DATES[year])
        _require(
            len(rows) == expected_pit,
            f"PIT at {year} report differs: {len(rows)} "
            f"(expected {expected_pit})",
        )

    # Each changed year switches v1 -> v2 on the restating report date.
    for target_year in restatement["changed"]:
        switch_date = ANNUAL_REPORT_DATES[target_year + 1]
        period_end = f"{target_year}-12-31"
        before = as_of.get_latest_available(
            SYMBOL,
            (date.fromisoformat(switch_date) - timedelta(days=1)).isoformat(),
            [CONCEPT],
        )
        on = as_of.get_latest_available(SYMBOL, switch_date, [CONCEPT])
        before_row = before[before["period_end"] == period_end]
        on_row = on[on["period_end"] == period_end]
        _require(
            len(before_row) == 1
            and int(before_row.iloc[0]["fact_version"]) == 1
            and len(on_row) == 1
            and int(on_row.iloc[0]["fact_version"]) == 2,
            f"{target_year}: PIT version switch differs",
        )
    # compare_versions must detect every changed year (and no unchanged one).
    for target_year in (2021, 2022, 2023, 2024):
        switch_date = ANNUAL_REPORT_DATES[target_year + 1]
        period_end = f"{target_year}-12-31"
        comparison = as_of.compare_versions(
            SYMBOL,
            [CONCEPT],
            period_end,
            (date.fromisoformat(switch_date) - timedelta(days=1)).isoformat(),
            switch_date,
        )
        match = [
            entry
            for entry in comparison.values()
            if entry.get("period_end") == period_end
        ]
        expected_changed = target_year in restatement["changed"]
        _require(
            len(match) == 1 and match[0]["changed"] is expected_changed,
            f"{target_year}: compare_versions change detection differs",
        )

    final = as_of.get_latest_available(SYMBOL, ANNUAL_REPORT_DATES[2025])
    _require(
        len(final) == EXPECTED_FINAL_PIT,
        f"final latest Fact PIT must contain {EXPECTED_FINAL_PIT} facts",
    )
    return {
        "counts": counts,
        "expected_counts": expected,
        "R": r,
        "annual_pit": {
            y: len(as_of.get_latest_available(SYMBOL, ANNUAL_REPORT_DATES[y]))
            for y in EXPECTED_ANNUAL_PIT
        },
        "final_pit": {
            "as_of_date": ANNUAL_REPORT_DATES[2025],
            "count": len(final),
            "fact_ids": final["fact_id"].tolist(),
        },
        "rule_005_lineage": rule_005_lineage,
        "upstream_fact_id_set_sha256": _id_set_digest(current_upstream_ids),
    }


def _build_readiness(repo: FactRepository) -> dict[str, Any]:
    """Register the 2021-2025 latest reconciled net_profit facts as ROA
    numerator inputs.  Readiness only -- no ROA/ROIC/score is computed."""
    as_of = AsOfQuery(repo)
    final_date = ANNUAL_REPORT_DATES[2025]
    latest = as_of.get_latest_available(SYMBOL, final_date, [CONCEPT])
    rows = latest[latest["source_tier"] == "reconciled_derived"].sort_values(
        "period_end"
    )
    _require(
        len(rows) == 5,
        f"expected five reconciled net_profit rows, got {len(rows)}",
    )
    years = []
    for _, row in rows.iterrows():
        fiscal_year = int(str(row["period_end"])[:4])
        scope = str(row["context_id"]).split("|")[-1]
        _require(
            scope == "consolidated", f"{fiscal_year}: scope differs",
        )
        years.append(
            {
                "fiscal_year": fiscal_year,
                "fact_id": str(row["fact_id"]),
                "value": int(row["value"]),
                "unit": str(row["unit"]),
                "available_at": str(row["available_at"]),
                "fact_version": int(row["fact_version"]),
                "restatement_version": str(row["restatement_version"]),
                "revision_review_status": REVISION_REVIEW_STATUS[fiscal_year],
                "scope": "consolidated",
                "ready_for_roa_numerator": True,
            }
        )
    _require(
        [entry["fiscal_year"] for entry in years] == list(YEARS),
        "readiness years differ",
    )
    return {
        "contract": READINESS_CONTRACT,
        "symbol": SYMBOL,
        "concept_id": CONCEPT,
        "scope": "consolidated",
        "unit": "万元",
        "as_of_date": final_date,
        "all_years_ready": True,
        "roa_numerator_fact_coverage_blocker_cleared": True,
        "roa_computation": "not_performed",
        "roic_computation": "not_performed",
        "scoring": "not_implemented",
        "note": (
            "readiness registry only; clearing the ROA numerator fact "
            "coverage blocker allows transparent ROA computation in a "
            "later stage -- no ROA/ROIC/score is computed here"
        ),
        "years": years,
    }


def _fact_database_path(upstream_dir: Path) -> Path:
    matches = list(upstream_dir.rglob("roe_roa_denominators.duckdb"))
    _require(len(matches) == 1, "upstream run-scoped DuckDB count differs")
    return matches[0]


def run_net_profit_foundation(
    output_root: str | Path,
    *,
    run_id: str | None = None,
) -> dict[str, Any]:
    """Execute the complete offline 2021-2025 net_profit foundation."""
    run_id = run_id or build_run_id()
    run_dir = (
        Path(output_root)
        / SYMBOL
        / "net_profit_official_facts"
        / "2021_2025"
        / run_id
    )
    run_dir.mkdir(parents=True, exist_ok=False)
    upstream_dir = run_dir / "upstream_roe_metric_extension"
    db_path = run_dir / "net_profit.duckdb"
    started_at = datetime.now().astimezone().isoformat()
    manifest: dict[str, Any] = {
        "run_id": run_id,
        "status": "failed",
        "transaction_committed": False,
        "offline": True,
        "network_access": False,
        "pdf_access": False,
        "cache_access": False,
        "downloaded": 0,
        "symbol": SYMBOL,
        "years": list(YEARS),
        "integration_contract": INTEGRATION_CONTRACT,
        "evidence_contract": CONTRACT,
        "reconciliation_rule_id": NET_PROFIT_RULE_ID,
        "reconciliation_rule_version": NET_PROFIT_RULE_VERSION,
        "metric_computation": "not_performed",
        "roa_computation": "blocked",
        "roic_computation": "not_performed",
        "scoring": "not_implemented",
        "investment_advice": "not_produced",
        "started_at": started_at,
    }
    store: DuckDBStore | None = None
    try:
        default_hash_before = _sha256(DEFAULT_DB)
        created_at = datetime.now().astimezone().isoformat()
        preflight = preflight_evidence(created_at=created_at)
        restatement = _resolve_restatements(preflight)
        with tempfile.TemporaryDirectory(prefix="m2_stage2de_") as temp_root:
            upstream = run_roe_metric_extension(temp_root, run_id="upstream")
            _verify_upstream_baseline(upstream)
            shutil.move(str(upstream["run_directory"]), str(upstream_dir))
        metric_baseline = _verify_metric_result_baseline(upstream_dir)

        source_db = _fact_database_path(upstream_dir)
        upstream_hash_before = _sha256(source_db)
        shutil.copy2(source_db, db_path)
        store = DuckDBStore(str(db_path))
        repo = FactRepository(store)
        conn = store.connect()
        upstream_fact_ids = [
            row[0]
            for row in conn.execute(
                "SELECT fact_id FROM financial_facts ORDER BY fact_id"
            ).fetchall()
        ]
        _require(
            len(upstream_fact_ids) == UPSTREAM_FACT_COUNT
            and _id_set_digest(upstream_fact_ids)
            == UPSTREAM_180_FACT_ID_SET_SHA256,
            "Stage 2D-B frozen 180 Fact ID set differs",
        )
        _require(
            conn.execute(
                "SELECT COUNT(*) FROM fact_contexts"
            ).fetchone()[0] == EXPECTED_CONTEXTS,
            "context count differs before net_profit registration",
        )

        service = OfficialFactReconciliationService(
            repo,
            engine=ReconciliationEngine(NET_PROFIT_RECONCILIATION_RULE),
        )
        # v1 reconciliations for all five concept-years.
        persisted = []
        v1_outputs: dict[int, dict[str, Any]] = {}
        for year in YEARS:
            result = service.reconcile_official_pair(
                preflight["source_facts"][year]["company"],
                preflight["source_facts"][year]["exchange"],
            )
            _require(
                result.status == ReconciliationStatus.matched
                and result.output_fact is not None,
                f"{year}: Rule 005 persistence failed",
            )
            persisted.append(asdict(result))
            v1_outputs[year] = result.output_fact

        # v2 reconciliations only for changed years (R-driven).
        v2_persisted = []
        transitions = []
        for target_year in restatement["changed"]:
            later_bundle = load_bundle(
                BUNDLE_DIR / f"{target_year + 1}_annual.json"
            )
            later_raw = int(
                restatement["reviews"][target_year]["concepts"][0][
                    "later_comparative_raw_value"
                ]
            )
            pair: dict[str, dict[str, Any]] = {}
            for source in ("company", "exchange"):
                predecessor = preflight["source_facts"][target_year][source]
                pair[source] = _build_v2_raw_fact(
                    predecessor,
                    later_bundle,
                    source,
                    target_year=target_year,
                    later_raw=later_raw,
                    created_at=created_at,
                )
            result = service.reconcile_official_pair(
                pair["company"],
                pair["exchange"],
                output_supersedes_fact_id=v1_outputs[target_year]["fact_id"],
            )
            _require(
                result.output_fact is not None,
                f"{target_year}: Rule 005 v2 failed",
            )
            v2_persisted.append(asdict(result))
            transitions.append(
                {
                    "target_fiscal_year": target_year,
                    "concept_id": CONCEPT,
                    "available_at": pair["company"]["available_at"],
                    "from_fact_id": v1_outputs[target_year]["fact_id"],
                    "to_fact_id": result.output_fact["fact_id"],
                }
            )
        all_reconciliations = persisted + v2_persisted

        acceptance = _collect_acceptance(
            repo,
            upstream_fact_ids=upstream_fact_ids,
            restatement=restatement,
        )
        readiness = _build_readiness(repo)
        _write_json(
            run_dir / "evidence_manifest.json",
            {
                "contract": CONTRACT,
                "logical_paths": [EVIDENCE_PATHS[y].name for y in YEARS],
                "restatements": [
                    RESTATEMENT_PATHS[y].name for y in (2021, 2022, 2023, 2024)
                ],
                "R": restatement["r"],
                "revision_review_status": REVISION_REVIEW_STATUS,
            },
        )
        _write_json(run_dir / "reconciliation_results.json", all_reconciliations)
        _write_json(run_dir / "restatement_results.json", transitions)
        _write_json(
            run_dir / "lineage_summary.json",
            {
                "count": len(acceptance["rule_005_lineage"]),
                "rows": acceptance["rule_005_lineage"],
            },
        )
        _write_json(run_dir / "latest_fact_snapshot.json", acceptance["final_pit"])
        _write_json(run_dir / "net_profit_input_readiness.json", readiness)
        upstream_hash_after = _sha256(source_db)
        _require(
            upstream_hash_before == upstream_hash_after,
            "foundation modified upstream foundation DuckDB",
        )
        default_hash_after = _sha256(DEFAULT_DB)
        _require(
            default_hash_before == default_hash_after == DEFAULT_DB_SHA256,
            "default research.duckdb changed",
        )
        manifest.update(
            {
                "status": "passed",
                "transaction_committed": True,
                "R": restatement["r"],
                "upstream": {
                    "status": upstream["status"],
                    "financial_facts": UPSTREAM_FACT_COUNT,
                    "eligible_facts": UPSTREAM_ELIGIBLE_COUNT,
                    "latest_fact_pit": UPSTREAM_PIT_COUNT,
                    "version_chain_links": UPSTREAM_VERSION_LINKS,
                    "fact_id_set_sha256": acceptance[
                        "upstream_fact_id_set_sha256"
                    ],
                    "combined_counts": upstream["combined_counts"],
                    "roe_counts": upstream["roe_counts"],
                    "prior_result_id_set_sha256": upstream[
                        "prior_result_id_set_sha256"
                    ],
                    "prior_result_semantic_sha256": upstream[
                        "prior_result_semantic_sha256"
                    ],
                    "metric_result_baseline": metric_baseline,
                    "sha256_before": upstream_hash_before,
                    "sha256_after": upstream_hash_after,
                },
                "counts": acceptance["counts"],
                "expected_counts": acceptance["expected_counts"],
                "annual_pit": acceptance["annual_pit"],
                "final_pit": acceptance["final_pit"],
                "new_raw_fact_ids": sorted(
                    preflight["source_facts"][year][source]["fact_id"]
                    for year in YEARS
                    for source in ("company", "exchange")
                ),
                "new_reconciled_fact_ids": sorted(
                    item["output_fact"]["fact_id"] for item in persisted
                ),
                "v2_reconciled_fact_ids": sorted(
                    item["output_fact"]["fact_id"] for item in v2_persisted
                ),
                "restatement_transitions": transitions,
                "net_profit_input_readiness": readiness,
                "default_db_sha256_before": default_hash_before,
                "default_db_sha256_after": default_hash_after,
                "completed_at": datetime.now().astimezone().isoformat(),
            }
        )
    except Exception as exc:
        manifest["error_type"] = type(exc).__name__
        manifest["error"] = str(exc)
        manifest["completed_at"] = datetime.now().astimezone().isoformat()
        if store is not None:
            store.close()
            store = None
        if db_path.exists():
            db_path.unlink()
    finally:
        if store is not None:
            store.close()

    _write_json(run_dir / "run_manifest.json", manifest)
    summary = (
        "# 2021-2025 consolidated net_profit official fact foundation\n\n"
        f"- run_id: `{run_id}`\n"
        f"- status: **{manifest['status']}**\n"
        "- offline: `true`\n"
        f"- transaction_committed: "
        f"`{str(manifest['transaction_committed']).lower()}`\n"
        "- ROA computation: `not performed`\n"
        "- ROIC computation: `not performed`\n"
        "- scoring: `not implemented`\n"
    )
    if "counts" in manifest:
        summary += "\n## Counts\n\n" + "\n".join(
            f"- {key}: {value}" for key, value in manifest["counts"].items()
        ) + "\n"
    if "error" in manifest:
        summary += f"\n## Failure\n\n{manifest['error']}\n"
    (run_dir / "acceptance_summary.md").write_text(summary, encoding="utf-8")
    return {**manifest, "run_directory": run_dir}


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", required=True)
    parser.add_argument("--run-id")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    result = run_net_profit_foundation(
        args.output_root,
        run_id=args.run_id,
    )
    print(json.dumps(_jsonable(result), ensure_ascii=False, indent=2))
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
