"""Accept PetroChina's 2025 earnings-quality official facts.

This single-year runner is deliberately offline. It rebuilds the frozen
75-fact Stage 2B-A foundation, validates one committed evidence file, and
adds only three Rule 003 concepts. It never opens a PDF, accesses the shared
cache or network, computes a Metric, or writes the default research database.
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
from ashare_research.facts.identity import build_fact_id
from ashare_research.facts.repository import FactRepository
from ashare_research.reconciliation.engine import (
    EARNINGS_QUALITY_RECONCILIATION_RULE,
    EARNINGS_QUALITY_RULE_ID,
    EARNINGS_QUALITY_RULE_VERSION,
    ReconciliationEngine,
)
from ashare_research.reconciliation.models import ReconciliationStatus
from ashare_research.reconciliation.service import (
    OfficialFactReconciliationService,
)
from ashare_research.storage.duckdb_store import DuckDBStore
from ashare_research.tools.official_capex_cash_fact_foundation import (
    run_capex_cash_foundation,
)
from ashare_research.tools.official_cashflow_metric_extension import (
    STAGE2A_METRIC_RESULT_ID_SET_SHA256,
    STAGE2BA_FACT_ID_SET_SHA256,
)
from ashare_research.tools.official_fact_acceptance import (
    build_source_facts,
    load_bundle,
)
from ashare_research.validation.validator import FactValidator

ROOT = Path(__file__).resolve().parents[3]
BUNDLE_DIR = (
    ROOT / "acceptance" / "fixtures" / "official_facts" / "601857.SH"
)
RESTATEMENT_DIR = (
    ROOT / "acceptance" / "fixtures" / "restatements" / "601857.SH"
)
DEFAULT_EVIDENCE = BUNDLE_DIR / "supplemental" / "2025_earnings_quality.json"
DEFAULT_DB = ROOT / "data" / "research.duckdb"
DEFAULT_DB_SHA256 = (
    "4a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6"
)
BUNDLES = [BUNDLE_DIR / f"{year}_annual.json" for year in range(2021, 2026)]
UPSTREAM_EVIDENCE = [
    RESTATEMENT_DIR / f"{year}_reviewed_by_{year + 1}_annual.json"
    for year in range(2021, 2025)
]
SUPPLEMENTAL = [
    BUNDLE_DIR / "supplemental" / f"{year}_capex_cash.json"
    for year in range(2021, 2026)
]
CAPEX_REVIEWS = [
    RESTATEMENT_DIR / f"capex_cash_{year}_reviewed_by_{year + 1}.json"
    for year in range(2021, 2025)
]

CONTRACT = "earnings_quality_official_facts_v1"
INTEGRATION_CONTRACT = "earnings_quality_2025_acceptance_v1"
SYMBOL = "601857.SH"
FISCAL_YEAR = 2025
CONCEPTS = frozenset({
    "net_profit_excluding_non_recurring",
    "operating_cost",
    "operating_profit",
})
UPSTREAM_FACT_COUNT = 75
UPSTREAM_PIT_COUNT = 20
METRIC_RESULT_COUNT = 38
METRIC_RESULT_ID_SET_SHA256 = (
    "730484f4abe54298cc53ecdc44d3079c0d2e064a6981047a0b413f6466faa5fa"
)
EXPECTED_COUNTS = {
    "fact_contexts": 5,
    "upstream_financial_facts": 75,
    "new_company_facts": 3,
    "new_exchange_facts": 3,
    "new_reconciled_facts": 3,
    "raw_ineligible_facts": 56,
    "reconciled_eligible_facts": 28,
    "financial_facts": 84,
    "version_chain_links": 15,
    "audit": 84,
    "lineage": 84,
}


class EarningsQualityAcceptanceError(ValueError):
    """A deterministic evidence or integration gate failed."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise EarningsQualityAcceptanceError(message)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git_blob_id(path: Path) -> str:
    content = path.read_bytes()
    header = f"blob {len(content)}\0".encode()
    return hashlib.sha1(header + content).hexdigest()  # noqa: S324


def _id_set_digest(ids: list[str]) -> str:
    payload = json.dumps(sorted(ids), separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()


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
    return f"earnings_quality_601857_SH_2025_{timestamp}"


def _validate_evidence_fact(item: dict[str, Any], source: str) -> None:
    concept_id = str(item.get("concept_id", ""))
    _require(concept_id in CONCEPTS, f"{source}: unsupported concept")
    _require(
        isinstance(item.get("pdf_page"), int)
        and isinstance(item.get("printed_page"), int),
        f"{source}/{concept_id}: page fields differ",
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
        _require(bool(str(item.get(field, "")).strip()), (
            f"{source}/{concept_id}: missing {field}"
        ))
    _require(
        item["manual_review_status"] == "visually_verified_twice",
        f"{source}/{concept_id}: manual review differs",
    )
    raw = int(str(item["raw_value"]))
    normalized = int(item["expected_normalized_value"])
    _require(
        raw * 100 == normalized,
        f"{source}/{concept_id}: million-to-10k conversion differs",
    )
    expected_type = (
        "annual_report_direct_disclosure"
        if concept_id == "net_profit_excluding_non_recurring"
        else "audited_consolidated_income_statement"
    )
    _require(
        item["evidence_type"] == expected_type,
        f"{source}/{concept_id}: evidence type differs",
    )
    if concept_id == "operating_cost":
        _require(
            item.get("sign_convention") == "expense_magnitude_positive"
            and item["source_label"] == "减：营业成本",
            f"{source}: operating cost sign or label differs",
        )
    if concept_id == "operating_profit":
        _require(
            item["source_label"] == "营业利润",
            f"{source}: operating profit label differs",
        )


def _validate_bridge(bridge: dict[str, Any]) -> None:
    required = {
        "net_profit_attributable_to_parent",
        "net_profit_excluding_non_recurring",
        "attributable_difference",
        "items",
        "item_subtotal",
        "income_tax_effect",
        "minority_interest_effect",
        "reported_final_net_effect",
        "computed_final_net_effect",
        "sign_convention",
        "exact_tie_out",
        "bridge_status",
        "evidence_pages",
        "fact_creation",
    }
    _require(required <= bridge.keys(), "non-recurring bridge fields differ")
    item_total = sum(int(item["amount"]) for item in bridge["items"])
    _require(
        item_total == int(bridge["item_subtotal"]),
        "non-recurring item subtotal does not tie",
    )
    computed = (
        item_total
        + int(bridge["income_tax_effect"])
        + int(bridge["minority_interest_effect"])
    )
    attributable = (
        int(bridge["net_profit_attributable_to_parent"])
        - int(bridge["net_profit_excluding_non_recurring"])
    )
    _require(
        computed
        == attributable
        == int(bridge["attributable_difference"])
        == int(bridge["reported_final_net_effect"])
        == int(bridge["computed_final_net_effect"]),
        "non-recurring bridge does not reconcile exactly",
    )
    _require(
        bridge["bridge_status"] == "reconciled"
        and bridge["exact_tie_out"] is True,
        "non-recurring bridge is not reconciled",
    )
    _require(
        bridge["fact_creation"] == "not_a_financial_facts_input",
        "non-recurring bridge must not create a Fact",
    )
    _require(
        set(bridge["evidence_pages"]) == {"company", "exchange"}
        and all(bridge["evidence_pages"][key] for key in ("company", "exchange")),
        "bridge evidence pages differ",
    )


def _build_fact(
    template: dict[str, Any],
    evidence: dict[str, Any],
    *,
    created_at: str,
) -> dict[str, Any]:
    normalized = int(evidence["expected_normalized_value"])
    fact = copy.deepcopy(template)
    fact.update(
        {
            "concept_id": evidence["concept_id"],
            "concept_version": "1",
            "value": normalized,
            "unit": "万元",
            "source_page": evidence["source_page"],
            "source_table": evidence["source_table"],
            "source_label": evidence["source_label"],
            "raw_value": int(str(evidence["raw_value"])),
            "raw_unit": evidence["raw_unit"],
            "normalized_value": normalized,
            "normalization_rule": evidence["normalization_rule"],
            "verification_note": (
                "manually verified twice against registered 2025 official "
                "earnings-quality evidence"
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


def preflight_evidence(
    evidence_path: str | Path = DEFAULT_EVIDENCE,
    *,
    created_at: str,
) -> dict[str, Any]:
    """Validate committed evidence and reconcile all three pairs in memory."""
    path = Path(evidence_path)
    evidence = _load_object(path)
    base_path = (ROOT / str(evidence.get("base_bundle_path", ""))).resolve()
    expected_base = BUNDLES[-1].resolve()
    _require(base_path == expected_base, "base bundle path differs")
    _require(
        evidence.get("base_bundle_sha256") == _sha256(expected_base),
        "base bundle SHA-256 differs",
    )
    _require(
        evidence.get("base_bundle_git_blob") == _git_blob_id(expected_base),
        "base bundle Git blob differs",
    )
    bundle = load_bundle(expected_base)
    expected_metadata = {
        "symbol": SYMBOL,
        "fiscal_year": FISCAL_YEAR,
        "report_type": "annual",
        "accounting_standard": "CAS",
        "consolidation_scope": "consolidated",
        "language": "zh-CN",
        "document_relationship": "same_report_different_bytes",
    }
    _require(
        evidence.get("contract") == CONTRACT,
        "earnings-quality evidence contract differs",
    )
    for field, expected in expected_metadata.items():
        _require(
            evidence.get(field) == expected
            and bundle.get(field) == expected,
            f"{field} differs from 2025 annual bundle",
        )
    _require(
        (
            evidence.get("reconciliation_rule_id"),
            evidence.get("reconciliation_rule_version"),
        )
        == (EARNINGS_QUALITY_RULE_ID, EARNINGS_QUALITY_RULE_VERSION),
        "Rule 003 binding differs",
    )
    _require(
        evidence.get("revision_review_status") == "not_yet_reviewable",
        "2025 revision review status differs",
    )
    sources = evidence.get("sources", {})
    _require(
        isinstance(sources, dict) and set(sources) == {"company", "exchange"},
        "exactly company and exchange evidence are required",
    )
    by_source: dict[str, dict[str, dict[str, Any]]] = {}
    for source in ("company", "exchange"):
        document = bundle["documents"][source]
        _require(
            document["source_tier"] == f"{source}_official",
            f"{source}: source tier differs",
        )
        facts = sources[source].get("facts", [])
        _require(
            isinstance(facts, list)
            and len(facts) == 3
            and {item.get("concept_id") for item in facts} == CONCEPTS,
            f"{source}: expected exactly three target facts",
        )
        for item in facts:
            _validate_evidence_fact(item, source)
        by_source[source] = {
            str(item["concept_id"]): item for item in facts
        }
    for concept_id in CONCEPTS:
        _require(
            by_source["company"][concept_id]["expected_normalized_value"]
            == by_source["exchange"][concept_id]["expected_normalized_value"],
            f"{concept_id}: company and exchange values differ",
        )
    _validate_bridge(evidence.get("non_recurring_bridge", {}))

    annual_facts = build_source_facts(bundle, created_at=created_at)
    templates = {
        source: {fact["concept_id"]: fact for fact in annual_facts[source]}
        for source in ("company", "exchange")
    }
    source_facts: dict[str, dict[str, dict[str, Any]]] = {
        "company": {},
        "exchange": {},
    }
    validator = FactValidator()
    engine = ReconciliationEngine(EARNINGS_QUALITY_RECONCILIATION_RULE)
    preflight_results = []
    for concept_id in sorted(CONCEPTS):
        for source in ("company", "exchange"):
            fact = _build_fact(
                templates[source]["revenue"],
                by_source[source][concept_id],
                created_at=created_at,
            )
            errors = [
                result
                for result in validator.validate_single_fact(fact)
                if result.severity == "error" and not result.passed
            ]
            _require(not errors, f"{source}/{concept_id}: Fact validation failed")
            source_facts[source][concept_id] = fact
        result = engine.reconcile_pair(
            source_facts["company"][concept_id],
            source_facts["exchange"][concept_id],
            now=created_at,
        )
        _require(
            result.status == ReconciliationStatus.matched
            and result.output_fact is not None,
            f"{concept_id}: Rule 003 preflight did not match",
        )
        preflight_results.append(result)
    return {
        "path": path,
        "evidence": evidence,
        "bundle": bundle,
        "source_facts": source_facts,
        "preflight_results": preflight_results,
    }


def _database_path(upstream_dir: Path) -> Path:
    matches = list(upstream_dir.rglob("restatement_integration.duckdb"))
    _require(len(matches) == 1, "upstream run-scoped DuckDB count differs")
    return matches[0]


def _collect_acceptance(
    repo: FactRepository,
    *,
    upstream_fact_ids: list[str],
    reconciliations: list[dict[str, Any]],
    later_announcement_date: str,
) -> dict[str, Any]:
    conn = repo.store.connect()
    counts = {
        "fact_contexts": conn.execute(
            "SELECT COUNT(*) FROM fact_contexts"
        ).fetchone()[0],
        "upstream_financial_facts": conn.execute(
            "SELECT COUNT(*) FROM financial_facts WHERE concept_id NOT IN "
            "(SELECT UNNEST(?))",
            [sorted(CONCEPTS)],
        ).fetchone()[0],
        "new_company_facts": conn.execute(
            """SELECT COUNT(*) FROM financial_facts
                WHERE concept_id IN (SELECT UNNEST(?))
                  AND source_tier='company_official'""",
            [sorted(CONCEPTS)],
        ).fetchone()[0],
        "new_exchange_facts": conn.execute(
            """SELECT COUNT(*) FROM financial_facts
                WHERE concept_id IN (SELECT UNNEST(?))
                  AND source_tier='exchange_official'""",
            [sorted(CONCEPTS)],
        ).fetchone()[0],
        "new_reconciled_facts": conn.execute(
            """SELECT COUNT(*) FROM financial_facts
                WHERE concept_id IN (SELECT UNNEST(?))
                  AND source_tier='reconciled_derived'""",
            [sorted(CONCEPTS)],
        ).fetchone()[0],
        "raw_ineligible_facts": conn.execute(
            """SELECT COUNT(*) FROM financial_facts
                WHERE is_derived=FALSE AND eligible_for_metrics=FALSE"""
        ).fetchone()[0],
        "reconciled_eligible_facts": conn.execute(
            """SELECT COUNT(*) FROM financial_facts
                WHERE source_tier='reconciled_derived'
                  AND eligible_for_metrics=TRUE"""
        ).fetchone()[0],
        "financial_facts": conn.execute(
            "SELECT COUNT(*) FROM financial_facts"
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
    _require(counts == EXPECTED_COUNTS, f"fixed counts differ: {counts}")

    current_upstream_ids = [
        row[0]
        for row in conn.execute(
            "SELECT fact_id FROM financial_facts "
            "WHERE concept_id NOT IN (SELECT UNNEST(?)) ORDER BY fact_id",
            [sorted(CONCEPTS)],
        ).fetchall()
    ]
    _require(
        current_upstream_ids == sorted(upstream_fact_ids)
        and _id_set_digest(current_upstream_ids)
        == STAGE2BA_FACT_ID_SET_SHA256,
        "frozen 75 Fact IDs changed",
    )
    _require(
        conn.execute(
            """SELECT COUNT(*) FROM fact_lineage
                WHERE reconciliation_rule_id='RECON_OFFICIAL_NUMERIC_001'"""
        ).fetchone()[0]
        == 57,
        "Rule 001 lineage changed",
    )
    _require(
        conn.execute(
            """SELECT COUNT(*) FROM fact_lineage
                WHERE reconciliation_rule_id='RECON_OFFICIAL_NUMERIC_002'"""
        ).fetchone()[0]
        == 18,
        "Rule 002 lineage changed",
    )
    rule_003_lineage = conn.execute(
        """SELECT fact_id, source_tier, parent_fact_ids, role,
                  reconciliation_rule_id, reconciliation_rule_version
             FROM fact_lineage
            WHERE reconciliation_rule_id=?
            ORDER BY lineage_id""",
        [EARNINGS_QUALITY_RULE_ID],
    ).df().to_dict("records")
    _require(
        len(rule_003_lineage) == 9
        and {
            row["reconciliation_rule_version"] for row in rule_003_lineage
        }
        == {EARNINGS_QUALITY_RULE_VERSION},
        "Rule 003 lineage differs",
    )

    as_of = AsOfQuery(repo)
    before_date = (
        date.fromisoformat(later_announcement_date) - timedelta(days=1)
    ).isoformat()
    before = as_of.get_latest_available(
        SYMBOL, before_date, sorted(CONCEPTS)
    )
    on = as_of.get_latest_available(
        SYMBOL, later_announcement_date, sorted(CONCEPTS)
    )
    final = as_of.get_latest_available(SYMBOL, later_announcement_date)
    _require(len(before) == 0, "new facts leaked before availability date")
    _require(
        len(on) == 3
        and set(on["concept_id"]) == CONCEPTS
        and set(on["source_tier"]) == {"reconciled_derived"}
        and all(bool(value) for value in on["eligible_for_metrics"]),
        "new facts are not exactly visible on availability date",
    )
    _require(len(final) == 23, "final latest Fact PIT must contain 23 facts")
    per_year = {
        int(period_end[:4]): int(count)
        for period_end, count in final.groupby("period_end").size().items()
    }
    _require(
        per_year == {2021: 4, 2022: 4, 2023: 4, 2024: 4, 2025: 7},
        f"final per-year PIT differs: {per_year}",
    )
    new_facts = conn.execute(
        """SELECT * FROM financial_facts
            WHERE concept_id IN (SELECT UNNEST(?))
            ORDER BY concept_id, source_tier""",
        [sorted(CONCEPTS)],
    ).df().to_dict("records")
    _require(
        len(new_facts) == 9
        and all(int(item["fact_version"]) == 1 for item in new_facts)
        and {str(item["restatement_version"]) for item in new_facts}
        == {"original"}
        and not any(str(item["supersedes_fact_id"]) for item in new_facts),
        "new fact version contract differs",
    )
    output_ids = {
        item["output_fact"]["fact_id"] for item in reconciliations
    }
    _require(
        set(on["fact_id"]) == output_ids,
        "PIT Rule 003 outputs differ from reconciliation results",
    )
    return {
        "counts": counts,
        "before_pit": {
            "as_of_date": before_date,
            "count": len(before),
        },
        "on_pit": {
            "as_of_date": later_announcement_date,
            "count": len(on),
            "fact_ids": on["fact_id"].tolist(),
        },
        "final_pit": {
            "as_of_date": later_announcement_date,
            "count": len(final),
            "per_year": per_year,
            "fact_ids": final["fact_id"].tolist(),
        },
        "new_facts": new_facts,
        "rule_003_lineage": rule_003_lineage,
        "upstream_fact_id_set_sha256": _id_set_digest(current_upstream_ids),
    }


def run_earnings_quality_acceptance(
    evidence_path: str | Path,
    output_root: str | Path,
    *,
    run_id: str | None = None,
) -> dict[str, Any]:
    """Execute the complete offline 2025 earnings-quality acceptance."""
    run_id = run_id or build_run_id()
    run_dir = (
        Path(output_root)
        / SYMBOL
        / "earnings_quality_official_facts"
        / "2025"
        / run_id
    )
    run_dir.mkdir(parents=True, exist_ok=False)
    upstream_dir = run_dir / "upstream_capex_cash"
    default_hash_before = _sha256(DEFAULT_DB)
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
        "fiscal_year": FISCAL_YEAR,
        "integration_contract": INTEGRATION_CONTRACT,
        "evidence_contract": CONTRACT,
        "reconciliation_rule_id": EARNINGS_QUALITY_RULE_ID,
        "reconciliation_rule_version": EARNINGS_QUALITY_RULE_VERSION,
        "metric_computation": "not_performed",
        "scoring": "not_implemented",
        "started_at": started_at,
    }
    store: DuckDBStore | None = None
    db_path: Path | None = None
    try:
        created_at = datetime.now().astimezone().isoformat()
        preflight = preflight_evidence(
            evidence_path,
            created_at=created_at,
        )
        with tempfile.TemporaryDirectory(prefix="m2_stage2cb_") as temp_root:
            upstream = run_capex_cash_foundation(
                BUNDLES,
                UPSTREAM_EVIDENCE,
                SUPPLEMENTAL,
                CAPEX_REVIEWS,
                temp_root,
                run_id="upstream",
            )
            _require(upstream["status"] == "passed", "Stage 2B-A upstream failed")
            shutil.move(str(upstream["run_directory"]), str(upstream_dir))
        _require(
            upstream["counts"]["financial_facts"] == UPSTREAM_FACT_COUNT
            and upstream["latest_pit_snapshot"]["count"] == UPSTREAM_PIT_COUNT,
            "Stage 2B-A upstream counts differ",
        )
        db_path = _database_path(upstream_dir)
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
            == STAGE2BA_FACT_ID_SET_SHA256,
            "Stage 2B-A frozen Fact ID set differs",
        )
        service = OfficialFactReconciliationService(
            repo,
            engine=ReconciliationEngine(
                EARNINGS_QUALITY_RECONCILIATION_RULE
            ),
        )
        persisted = []
        for concept_id in sorted(CONCEPTS):
            result = service.reconcile_official_pair(
                preflight["source_facts"]["company"][concept_id],
                preflight["source_facts"]["exchange"][concept_id],
            )
            _require(
                result.status == ReconciliationStatus.matched
                and result.output_fact is not None,
                f"{concept_id}: Rule 003 persistence failed",
            )
            persisted.append(asdict(result))

        later_date = max(
            preflight["bundle"]["documents"]["company"]["announcement_date"],
            preflight["bundle"]["documents"]["exchange"]["announcement_date"],
        )
        acceptance = _collect_acceptance(
            repo,
            upstream_fact_ids=upstream_fact_ids,
            reconciliations=persisted,
            later_announcement_date=later_date,
        )
        _write_json(
            run_dir / "evidence_manifest.json",
            {
                "contract": CONTRACT,
                "logical_path": Path(evidence_path).name,
                "base_bundle": BUNDLES[-1].name,
                "bridge_status": (
                    preflight["evidence"]["non_recurring_bridge"][
                        "bridge_status"
                    ]
                ),
                "revision_review_status": "not_yet_reviewable",
            },
        )
        _write_json(run_dir / "reconciliation_results.json", persisted)
        _write_json(run_dir / "new_facts.json", acceptance["new_facts"])
        _write_json(
            run_dir / "latest_fact_snapshot.json",
            acceptance["final_pit"],
        )
        _write_json(
            run_dir / "lineage_summary.json",
            {
                "count": len(acceptance["rule_003_lineage"]),
                "rows": acceptance["rule_003_lineage"],
            },
        )
        manifest.update(
            {
                "status": "passed",
                "transaction_committed": True,
                "upstream": {
                    "status": upstream["status"],
                    "financial_facts": UPSTREAM_FACT_COUNT,
                    "latest_pit": UPSTREAM_PIT_COUNT,
                    "fact_id_set_sha256": (
                        acceptance["upstream_fact_id_set_sha256"]
                    ),
                },
                "frozen_metric_results": {
                    "count": METRIC_RESULT_COUNT,
                    "id_set_sha256": METRIC_RESULT_ID_SET_SHA256,
                    "stage2a_id_set_sha256": (
                        STAGE2A_METRIC_RESULT_ID_SET_SHA256
                    ),
                    "artifacts_accessed": False,
                },
                "counts": acceptance["counts"],
                "before_pit": acceptance["before_pit"],
                "on_pit": acceptance["on_pit"],
                "final_pit": acceptance["final_pit"],
                "new_raw_fact_ids": sorted(
                    item["fact_id"]
                    for item in acceptance["new_facts"]
                    if item["source_tier"]
                    in {"company_official", "exchange_official"}
                ),
                "new_reconciled_fact_ids": sorted(
                    item["output_fact"]["fact_id"] for item in persisted
                ),
                "reconciliation_statuses": [
                    item["status"] for item in persisted
                ],
                "bridge_status": "reconciled",
                "revision_review_status": "not_yet_reviewable",
                "default_db_sha256_before": default_hash_before,
                "default_db_sha256_after": _sha256(DEFAULT_DB),
                "completed_at": datetime.now().astimezone().isoformat(),
            }
        )
        _require(
            default_hash_before
            == manifest["default_db_sha256_after"]
            == DEFAULT_DB_SHA256,
            "default research.duckdb changed",
        )
    except Exception as exc:
        manifest["error_type"] = type(exc).__name__
        manifest["error"] = str(exc)
        manifest["completed_at"] = datetime.now().astimezone().isoformat()
        if store is not None:
            store.close()
            store = None
        if db_path is not None and db_path.exists():
            db_path.unlink()
    finally:
        if store is not None:
            store.close()

    _write_json(run_dir / "run_manifest.json", manifest)
    summary = (
        "# 2025 earnings-quality official fact acceptance\n\n"
        f"- run_id: `{run_id}`\n"
        f"- status: **{manifest['status']}**\n"
        "- offline: `true`\n"
        f"- transaction_committed: "
        f"`{str(manifest['transaction_committed']).lower()}`\n"
        "- Metric computation: `not performed`\n"
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
    parser.add_argument(
        "--evidence",
        default=str(DEFAULT_EVIDENCE),
    )
    parser.add_argument("--output-root", required=True)
    parser.add_argument("--run-id")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    result = run_earnings_quality_acceptance(
        args.evidence,
        args.output_root,
        run_id=args.run_id,
    )
    print(json.dumps(_jsonable(result), ensure_ascii=False, indent=2))
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
