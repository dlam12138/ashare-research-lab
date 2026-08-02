"""Deterministic Stage 2I ROIC official-fact readiness audit.

This module is a pre-production evidence audit.  It deliberately does not
define or register a Metric and it never writes the default DuckDB database.
The committed canonical inventory is the clean-clone fallback; a run-scoped
fact database may be supplied to verify the same inventory against actual
Fact rows.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
from collections.abc import Iterable
from pathlib import Path
from typing import Any

YEARS = tuple(range(2020, 2026))
SYMBOL = "601857.SH"
ROOT = Path(__file__).resolve().parents[3]
INVENTORY_PATH = ROOT / "config" / "roic_canonical_fact_inventory_v1.json"

# Candidate B is the only candidate carried forward.  The entries are inputs
# to an audit, not a promise that every item is currently registered.
INPUTS: tuple[dict[str, Any], ...] = (
    {
        "concept_id": "operating_profit",
        "role": "nopat_operating_profit",
        "kind": "duration",
        "required": True,
    },
    {
        "concept_id": "finance_cost",
        "role": "nopat_finance_adjustment",
        "kind": "duration",
        "required": True,
    },
    {
        "concept_id": "interest_expense",
        "role": "nopat_finance_adjustment",
        "kind": "duration",
        "required": True,
    },
    {
        "concept_id": "lease_interest_expense",
        "role": "nopat_finance_adjustment",
        "kind": "duration",
        "required": True,
    },
    {
        "concept_id": "investment_income",
        "role": "nopat_non_operating_exclusion",
        "kind": "duration",
        "required": True,
    },
    {
        "concept_id": "fair_value_change",
        "role": "nopat_non_operating_exclusion",
        "kind": "duration",
        "required": True,
    },
    {
        "concept_id": "other_non_operating_income",
        "role": "nopat_non_operating_exclusion",
        "kind": "duration",
        "required": True,
    },
    {
        "concept_id": "other_non_operating_expense",
        "role": "nopat_non_operating_exclusion",
        "kind": "duration",
        "required": True,
    },
    {
        "concept_id": "operating_tax_expense",
        "role": "nopat_tax",
        "kind": "duration",
        "required": True,
    },
    {
        "concept_id": "income_tax_expense",
        "role": "tax_bridge",
        "kind": "duration",
        "required": True,
    },
    {
        "concept_id": "deferred_tax_expense",
        "role": "tax_bridge",
        "kind": "duration",
        "required": True,
    },
    {"concept_id": "profit_before_tax", "role": "tax_anchor", "kind": "duration", "required": True},
    {
        "concept_id": "equity_attributable_to_parent",
        "role": "invested_capital",
        "kind": "balance",
        "required": True,
    },
    {"concept_id": "nci", "role": "invested_capital", "kind": "balance", "required": True},
    {
        "concept_id": "short_term_borrowings",
        "role": "invested_capital_debt",
        "kind": "balance",
        "required": True,
    },
    {
        "concept_id": "current_portion_of_long_term_borrowings",
        "role": "invested_capital_debt",
        "kind": "balance",
        "required": True,
    },
    {
        "concept_id": "current_portion_of_bonds_payable",
        "role": "invested_capital_debt",
        "kind": "balance",
        "required": True,
    },
    {
        "concept_id": "current_portion_of_lease_liabilities",
        "role": "invested_capital_debt",
        "kind": "balance",
        "required": True,
    },
    {
        "concept_id": "long_term_borrowings",
        "role": "invested_capital_debt",
        "kind": "balance",
        "required": True,
    },
    {
        "concept_id": "bonds_payable",
        "role": "invested_capital_debt",
        "kind": "balance",
        "required": True,
    },
    {
        "concept_id": "lease_liabilities",
        "role": "invested_capital_debt",
        "kind": "balance",
        "required": True,
    },
    {
        "concept_id": "interest_bearing_long_term_payables",
        "role": "invested_capital_debt",
        "kind": "balance",
        "required": True,
    },
    {
        "concept_id": "total_assets",
        "role": "operating_view_reconciliation",
        "kind": "balance",
        "required": True,
    },
    {
        "concept_id": "cash_and_cash_equivalents",
        "role": "cash_classification",
        "kind": "balance",
        "required": True,
    },
    {
        "concept_id": "monetary_funds",
        "role": "cash_classification",
        "kind": "balance",
        "required": True,
    },
    {
        "concept_id": "restricted_cash",
        "role": "cash_classification",
        "kind": "balance",
        "required": True,
    },
    {
        "concept_id": "financial_assets_at_fair_value",
        "role": "non_operating_assets",
        "kind": "balance",
        "required": True,
    },
    {
        "concept_id": "financial_assets_at_amortized_cost",
        "role": "non_operating_assets",
        "kind": "balance",
        "required": True,
    },
    {
        "concept_id": "associate_investment",
        "role": "associate_jv_scope",
        "kind": "balance",
        "required": True,
    },
    {
        "concept_id": "joint_venture_investment",
        "role": "associate_jv_scope",
        "kind": "balance",
        "required": True,
    },
    {"concept_id": "goodwill", "role": "goodwill_scope", "kind": "balance", "required": True},
    {
        "concept_id": "noninterest_bearing_operating_liabilities",
        "role": "operating_view_reconciliation",
        "kind": "balance",
        "required": True,
    },
)

READY_CONCEPTS = frozenset(
    {
        "operating_profit",
        "equity_attributable_to_parent",
        "short_term_borrowings",
        "current_portion_of_long_term_borrowings",
        "current_portion_of_bonds_payable",
        "current_portion_of_lease_liabilities",
        "long_term_borrowings",
        "bonds_payable",
        "lease_liabilities",
        "total_assets",
        "cash_and_cash_equivalents",
    }
)


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: object required")
    return value


def _inventory_from_duckdb(path: Path) -> list[dict[str, Any]]:
    import duckdb

    conn = duckdb.connect(str(path), read_only=True)
    rows = conn.execute(
        """
        SELECT fact_id, concept_id, period_end, fact_version,
               restatement_version, supersedes_fact_id, available_at,
               verification_status, source_document
        FROM financial_facts
        WHERE eligible_for_metrics = TRUE
        ORDER BY period_end, concept_id, fact_version, fact_id
        """
    ).fetchall()
    conn.close()
    return [
        {
            "fact_id": row[0],
            "concept_id": row[1],
            "fiscal_year": int(str(row[2])[:4]),
            "period_end": str(row[2]),
            "fact_version": int(row[3]),
            "restatement_version": row[4],
            "supersedes_fact_id": row[5] or None,
            "available_at": row[6],
            "verification_status": row[7],
            "source_document": row[8],
        }
        for row in rows
    ]


def _inventory_from_config(path: Path) -> list[dict[str, Any]]:
    return list(_load_json(path).get("facts", []))


def _group_inventory(
    facts: Iterable[dict[str, Any]],
) -> dict[tuple[int, str], list[dict[str, Any]]]:
    grouped: dict[tuple[int, str], list[dict[str, Any]]] = defaultdict(list)
    for fact in facts:
        grouped[(int(fact["fiscal_year"]), str(fact["concept_id"]))].append(fact)
    return grouped


def _status(item: dict[str, Any], year: int, rows: list[dict[str, Any]]) -> str:
    if item["kind"] == "duration" and year == 2020:
        return "not_applicable"
    if rows:
        return "ready"
    if item["concept_id"] in READY_CONCEPTS:
        return "missing_canonical_fact"
    return "missing"


def build_readiness_report(
    *, fact_db: Path | None = None, inventory_path: Path = INVENTORY_PATH
) -> dict[str, Any]:
    """Build the deterministic Stage 2I readiness report without a shadow value."""
    if fact_db is not None:
        facts = _inventory_from_duckdb(fact_db)
        inventory_source = f"run_scoped:{fact_db.name}"
    else:
        facts = _inventory_from_config(inventory_path)
        inventory_source = "committed:config/roic_canonical_fact_inventory_v1.json"
    grouped = _group_inventory(facts)

    matrix: list[dict[str, Any]] = []
    blocking_gaps: list[dict[str, Any]] = []
    for item in INPUTS:
        for year in YEARS:
            rows = sorted(
                grouped.get((year, item["concept_id"]), []),
                key=lambda row: (row.get("fact_version", 0), row["fact_id"]),
            )
            status = _status(item, year, rows)
            cell = {
                "fiscal_year": year,
                "concept_id": item["concept_id"],
                "role": item["role"],
                "kind": item["kind"],
                "required": item["required"],
                "status": status,
                "canonical_fact_ids": [row["fact_id"] for row in rows],
                "available_at": [row.get("available_at") for row in rows],
                "restatement_versions": [row.get("restatement_version") for row in rows],
            }
            matrix.append(cell)
            if item["required"] and status not in {"ready", "not_applicable"}:
                blocking_gaps.append(
                    {
                        "fiscal_year": year,
                        "concept_id": item["concept_id"],
                        "status": status,
                        "reason": (
                            "required input is absent from the canonical eligible "
                            "Fact inventory"
                        ),
                    }
                )

    by_year = {
        str(year): {
            "ready": sum(row["fiscal_year"] == year and row["status"] == "ready" for row in matrix),
            "missing": sum(
                row["fiscal_year"] == year
                and row["status"] in {"missing", "missing_canonical_fact"}
                for row in matrix
            ),
            "not_applicable": sum(
                row["fiscal_year"] == year and row["status"] == "not_applicable" for row in matrix
            ),
        }
        for year in YEARS
    }
    report = {
        "schema": "roic_fact_readiness_report_v1",
        "symbol": SYMBOL,
        "audit_years": list(YEARS),
        "inventory_source": inventory_source,
        "inventory_fact_count": len(facts),
        "formula_candidate": "B_operating_profit_bridge_financing_view",
        "formula_status": "frozen_primary_candidate_not_production_metric",
        "evidence_gate": "BLOCKED_WITH_EXPLICIT_GAPS"
        if blocking_gaps
        else "SUFFICIENT_FOR_ONE_YEAR_FEASIBILITY",
        "shadow": {
            "status": "NOT_RUN",
            "reason": (
                "the direct operating-tax, scope-matched finance and non-operating "
                "asset evidence gate is not satisfied"
            ),
            "production_metric_created": False,
            "current_value_profile_changed": False,
        },
        "policy_freeze": {
            "nopat": (
                "Candidate B: operating profit plus eligible finance adjustment minus "
                "matched non-operating items minus directly allocated operating tax"
            ),
            "invested_capital": (
                "primary financing view; parent equity plus NCI plus scope-matched "
                "interest-bearing debt and leases minus qualifying non-operating assets"
            ),
            "tax": (
                "direct operating tax required; current plus deferred bridge; no "
                "clipping and no silent fallback"
            ),
            "cash": (
                "never subtract all cash silently; classification and purpose "
                "evidence required"
            ),
            "average_balance": (
                "opening plus closing divided by two; missing opening balance is "
                "not computable"
            ),
            "pit": "available_at maximum and restatement version supersession",
            "restatement": "superseding canonical Fact replaces the prior version",
            "forbidden_nopat": [
                "net_profit",
                "net_profit_attributable_to_parent",
                "EBITDA",
                "manual_plug",
                "LLM_inference",
            ],
        },
        "coverage_by_year": by_year,
        "blocking_gaps": blocking_gaps,
        "matrix": matrix,
    }
    encoded = json.dumps(report, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    report["report_sha256"] = hashlib.sha256(encoded).hexdigest()
    return report


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# PetroChina ROIC official-fact readiness audit (FY2020–FY2025)",
        "",
        f"- Formula candidate: `{report['formula_candidate']}`",
        f"- Evidence gate: **{report['evidence_gate']}**",
        f"- Shadow: **{report['shadow']['status']}** — {report['shadow']['reason']}",
        f"- Canonical inventory facts audited: `{report['inventory_fact_count']}`",
        "",
        (
            "The matrix is an evidence gate, not a ROIC calculation. Missing "
            "values are not replaced with zero, and no production Metric Result "
            "or value profile is written."
        ),
        "",
        "## Coverage by year",
        "",
        "| FY | Ready | Missing | N/A |",
        "|---:|---:|---:|---:|",
    ]
    for year in YEARS:
        row = report["coverage_by_year"][str(year)]
        lines.append(f"| {year} | {row['ready']} | {row['missing']} | {row['not_applicable']} |")
    lines.extend(["", "## Blocking gaps", ""])
    for gap in report["blocking_gaps"]:
        lines.append(
            f"- FY{gap['fiscal_year']} `{gap['concept_id']}`: {gap['reason']} ({gap['status']})"
        )
    if not report["blocking_gaps"]:
        lines.append("- None")
    lines.extend(
        [
            "",
            "## Frozen controls",
            "",
            "- NOPAT cannot be net profit or parent-attributable profit.",
            (
                "- Invested capital uses opening and closing balances; ending "
                "balance alone is insufficient."
            ),
            "- Cash is classified by purpose; all cash is never silently subtracted.",
            "- PIT uses maximum `available_at`; restatements supersede earlier canonical facts.",
        ]
    )
    return "\n".join(lines) + "\n"


def write_report(report: dict[str, Any], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "petrochina_roic_fact_readiness_2020_2025.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (output_dir / "petrochina_roic_fact_readiness_2020_2025.md").write_text(
        render_markdown(report), encoding="utf-8"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fact-db", type=Path, help="optional run-scoped canonical Fact database")
    parser.add_argument("--inventory", type=Path, default=INVENTORY_PATH)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "reports")
    args = parser.parse_args(argv)
    report = build_readiness_report(fact_db=args.fact_db, inventory_path=args.inventory)
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
