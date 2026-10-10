"""Acceptance coverage for arbitrary-symbol multi-year core financial analysis.

The tool under test adds one explicit read-only database selector to the existing approved
metrics: it gates facts with the public PIT query, binds only year-end annual flows and
year-end instant balances, and reuses the twelve existing registries without new formulas.
These tests exercise it against (1) the committed stage2g snapshot rebuilt as a temporary
database, cross-checked against the public ``MetricEngine`` fed by an independent PIT
selection over the same committed facts; (2) synthetic multi-company/scope/revision and
parent-lineage databases; (3) precision and status boundaries (missing, zero/negative
denominators, non-integer, out-of-safe-range, wrong unit, wrong source tier); (4) real
CLI subprocess runs including export manifests and sanitized failures.  The database hash
and schema are checked to prove the analysis never mutates or creates a fact database.

# AI provenance: action=created; model=GPT-5; agent=Codex; date=2026-10-10
# AI provenance: action=modified; model=GPT-5; agent=Codex; date=2026-10-10
# AI provenance: action=modified; model=GPT-5; agent=Codex; date=2026-10-10
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from decimal import ROUND_HALF_EVEN, Decimal
from pathlib import Path
from typing import Any

import duckdb
import pytest
from fact_test_helpers import make_verified_fact

from ashare_research import financial_analysis as core
from ashare_research.facts.concepts import ConceptRegistry
from ashare_research.facts.repository import FactRepository
from ashare_research.metrics.engine import MetricEngine
from ashare_research.reproducibility.capsule import build_temp_fact_db
from ashare_research.storage.duckdb_store import DuckDBStore

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
SNAPSHOT = ROOT / "tests" / "fixtures" / "stage2g" / "canonical_fact_snapshot_v1"
MODULE_NAME = "ashare_research.tools.financial_analysis"
FIXTURE_SYMBOL = "601857.SH"
SYMBOL = "600519.SH"
OTHER_SYMBOL = "000002.SZ"
INSTANT_MISMATCH_SYMBOL = "600000.SH"
REVISION_SYMBOL = "601988.SH"
ROE = "return_on_average_equity_attributable_to_parent"
PRIOR_ROLES = frozenset({"prior", "opening"})
QUANTUM = Decimal("0.000000000001")
ANNUAL = "annual"
INSTANT = "instant"
CONSOLIDATED = "consolidated"
PARENT_COMPANY = "parent_company"
HISTORY_MISSING_REASON = "absent_from_pit_selection"
SEVEN_COMPUTED_2023 = (
    "cash_based_free_cash_flow_proxy",
    "cash_paid_for_fixed_assets_to_revenue",
    "net_profit_attributable_to_parent_yoy",
    "operating_cash_flow_to_attributable_net_profit",
    "operating_cash_flow_yoy",
    "return_on_average_equity_attributable_to_parent",
    "revenue_yoy",
)
FIVE_MISSING_2023 = (
    "gross_margin",
    "gross_profit",
    "net_profit_excluding_non_recurring_yoy",
    "operating_profit_margin",
    "return_on_average_total_assets",
)


_CHILD_ENVIRONMENT = dict(os.environ)
_CHILD_ENVIRONMENT["PYTHONPATH"] = str(SRC)
_CHILD_ENVIRONMENT["PYTHONIOENCODING"] = "utf-8"

FIXTURE_FACTS = json.loads((SNAPSHOT / "facts.json").read_text(encoding="utf-8"))


# ── helpers ──────────────────────────────────────────────────────────────


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _yoy(current: int, prior: int) -> str:
    value = Decimal(current) / Decimal(prior) - Decimal(1)
    return format(value.quantize(QUANTUM, rounding=ROUND_HALF_EVEN), "f")


def _fact(
    symbol: str,
    concept_id: str,
    year: int,
    value: float,
    available_at: str,
    *,
    period_type: str = ANNUAL,
    scope: str = CONSOLIDATED,
    fact_version: int = 1,
    restatement_version: str = "original",
    unit: str = core.ENGINE_FACT_UNIT,
    source_tier: str = core.ENGINE_SOURCE_TIER,
    verification_status: str = "reconciled",
    eligible: bool = True,
    supersedes_fact_id: str = "",
) -> tuple[dict[str, Any], dict[str, Any]]:
    """One metrics-eligible fixture fact plus the fact_contexts row it joins to."""
    context_id = f"{symbol}|{year}|{period_type}|{scope}"
    context: dict[str, Any] = {
        "context_id": context_id,
        "symbol": symbol,
        "fiscal_year": year,
        "period_type": period_type,
        "period_start": f"{year}-01-01" if period_type == ANNUAL else "",
        "period_end": f"{year}-12-31",
        "instant_or_duration": INSTANT if period_type == INSTANT else "duration",
        "consolidation_scope": scope,
        "accounting_standard": "CAS",
        "restatement_version": "original",
        "source_document": f"{year} annual report",
        "filing_date": available_at,
        "created_at": "2026-01-01T00:00:00",
    }
    fact = make_verified_fact(
        symbol=symbol,
        concept_id=concept_id,
        context_id=context_id,
        value=value,
        raw_value=value,
        normalized_value=value,
        unit=unit,
        raw_unit=unit,
        period_end=f"{year}-12-31",
        announcement_date=available_at,
        filing_date=available_at,
        available_at=available_at,
        fact_version=fact_version,
        restatement_version=restatement_version,
        supersedes_fact_id=supersedes_fact_id,
        source_id=f"src_{symbol}_{concept_id}_{year}_{period_type}_v{fact_version}",
        source_provider="test_fixture",
        source_document=f"{year} annual report",
        source_tier=source_tier,
        verification_status=verification_status,
        eligible_for_metrics=eligible,
    )
    return fact, context


def _seed(
    database: Path,
    spec: list[tuple[dict[str, Any], dict[str, Any]]],
    lineage: list[dict[str, Any]] | None = None,
) -> Path:
    """Build one temporary fact database and close the writer before analysis."""
    store = DuckDBStore(str(database))
    try:
        repository = FactRepository(store)
        repository.ensure_schema(git_commit="core-financial-analysis-test")
        contexts = {context["context_id"]: context for _fact, context in spec}
        repository.store_contexts(list(contexts.values()))
        repository.store_facts([fact for fact, _context in spec])
        for row in lineage or []:
            repository.store_lineage(
                row["fact_id"],
                parent_fact_ids=row.get("parent_fact_ids", ""),
                role=row.get("role", ""),
                source_provider="test_fixture",
            )
    finally:
        store.close()
    return database


def _table_names(database: Path) -> list[str]:
    connection = duckdb.connect(str(database), read_only=True)
    try:
        rows = connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name"
        ).fetchall()
    finally:
        connection.close()
    return [str(row[0]) for row in rows]


def _record(report: dict[str, Any], metric_id: str, year: int) -> dict[str, Any]:
    for row in report["as_of"]["records"]:
        if row["metric_id"] == metric_id and row["fiscal_year"] == year:
            return row
    raise AssertionError(f"missing record {metric_id}/{year}")


def _run_cli(*arguments: str, cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", MODULE_NAME, *arguments],
        cwd=cwd,
        env=_CHILD_ENVIRONMENT,
        capture_output=True,
        check=False,
    )


def _fixture_selected(date: str) -> dict[tuple[str, str, str], dict[str, Any]]:
    """Independent PIT gate over the committed snapshot; never imports the tool."""
    latest: dict[tuple[str, str, str], dict[str, Any]] = {}
    for fact in FIXTURE_FACTS:
        if fact["symbol"] != FIXTURE_SYMBOL:
            continue
        if not fact["available_at"] or fact["available_at"] > date:
            continue
        if fact["verification_status"] not in {"verified", "reconciled"}:
            continue
        if fact["eligible_for_metrics"] is not True:
            continue
        key = (fact["concept_id"], fact["period_end"], fact["consolidation_scope"])
        stamp = (
            fact["available_at"],
            fact["fact_version"],
            fact["restatement_version"],
            fact["created_at"],
        )
        current = latest.get(key)
        if current is None or stamp > (
            current["available_at"],
            current["fact_version"],
            current["restatement_version"],
            current["created_at"],
        ):
            latest[key] = fact
    return latest


def _fixture_engine_fact(fact: dict[str, Any]) -> dict[str, Any]:
    return {
        "fact_id": fact["fact_id"],
        "value": Decimal(fact["value_decimal"]),
        "unit": fact["unit"],
        "source_tier": fact["source_tier"],
        "eligible_for_metrics": True,
        "period_end": fact["period_end"],
        "fact_version": fact["fact_version"],
        "restatement_version": fact["restatement_version"],
        "available_at": fact["available_at"],
    }


def _fixture_expected(
    date: str, years: list[int], metrics: tuple[str, ...], symbol: str
) -> dict[tuple[str, int], tuple[str, str | None, tuple[str, ...]]]:
    """Expected status/value/inputs from the public engine over independently gated facts."""
    definitions = core.metric_definitions()
    selected = _fixture_selected(date)
    expected: dict[tuple[str, int], tuple[str, str | None, tuple[str, ...]]] = {}
    for metric_id in metrics:
        definition = definitions[metric_id]
        for year in years:
            bound: list[dict[str, Any] | None] = []
            for position, role in enumerate(definition.input_roles):
                fiscal_year = year - 1 if role in PRIOR_ROLES else year
                concept_id = definition.input_concept_ids[position]
                fact = selected.get((concept_id, f"{fiscal_year}-12-31", CONSOLIDATED))
                expected_type = INSTANT if ConceptRegistry.is_instant(concept_id) else ANNUAL
                bound.append(
                    None
                    if fact is None or fact["period_type"] != expected_type
                    else _fixture_engine_fact(fact)
                )
            result, _lineage = MetricEngine.compute(
                definition,
                symbol=symbol,
                fiscal_year=year,
                primary_fact=bound[0],
                secondary_fact=bound[1],
                tertiary_fact=bound[2] if len(bound) >= 3 else None,
                missing_prior_is_history=(
                    definition.formula == "(current / prior) - 1" and year == years[0]
                ),
                result_version=1,
                revision_review_status=core.REVISION_REVIEW_STATUS,
                as_of_date=date,
                created_at=core.ANALYSIS_CREATED_AT,
            )
            expected[(metric_id, year)] = (
                str(result.status),
                None if result.value is None else format(result.value, "f"),
                tuple(result.input_fact_ids),
            )
    return expected


@pytest.fixture(scope="module")
def fixture_db(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return build_temp_fact_db(SNAPSHOT, tmp_path_factory.mktemp("fixture") / "facts.duckdb")


# ── committed snapshot against the independent public engine ─────────────


def test_committed_fixture_matches_independent_public_engine(fixture_db: Path) -> None:
    date, years = "2024-03-31", [2022, 2023, 2024]
    report = core.build_report(database=fixture_db, symbol=FIXTURE_SYMBOL, as_of=date, years=years)
    records = {(row["metric_id"], row["fiscal_year"]): row for row in report["as_of"]["records"]}
    assert len(records) == len(core.METRIC_IDS) * len(years)
    for key, expected_value in _fixture_expected(
        date, years, core.METRIC_IDS, FIXTURE_SYMBOL
    ).items():
        row = records[key]
        actual = (row["status"], row["value"], tuple(row["input_fact_ids"]))
        assert actual == expected_value, key

    block = report["as_of"]
    assert block["selection_count"] > 0
    assert block["compatible_fact_count"] == block["selection_count"]
    assert block["excluded_inputs"] == []
    computed_2023 = {
        key[0]
        for key, row in records.items()
        if key[1] == 2023 and row["status"] == "computed"
    }
    missing_2023 = {
        key[0]
        for key, row in records.items()
        if key[1] == 2023 and row["status"] == "missing_input"
    }
    assert computed_2023 == set(SEVEN_COMPUTED_2023)
    assert missing_2023 == set(FIVE_MISSING_2023)
    assert set(SEVEN_COMPUTED_2023) | set(FIVE_MISSING_2023) == set(core.METRIC_IDS)
    assert all(row["missing_roles"] for row in records.values() if row["status"] != "computed")
    assert report["boundary"]["read_model"] is True
    assert json.loads(core.render_json(report)) == report


def test_committed_fixture_reports_unknown_symbol_as_absent(fixture_db: Path) -> None:
    report = core.build_report(
        database=fixture_db, symbol="600519.SH", as_of="2024-03-31", years=[2023]
    )
    block = report["as_of"]
    assert block["selection_count"] == 0
    assert block["excluded_inputs"] == []
    assert len(block["records"]) == len(core.METRIC_IDS)
    assert {row["status"] for row in block["records"]} == {"missing_input"}
    assert all(row["value"] is None for row in block["records"])
    assert all(
        item["reason"] == HISTORY_MISSING_REASON
        for row in block["records"]
        for item in row["missing_roles"]
    )


# ── isolation, scope, annual/instant binding ─────────────────────────────


def test_multi_company_and_scope_isolation(tmp_path: Path) -> None:
    a_prior, a_prior_ctx = _fact(SYMBOL, "revenue", 2022, 800.0, "2023-03-01")
    a_current, a_current_ctx = _fact(SYMBOL, "revenue", 2023, 1000.0, "2024-03-01")
    b_prior, b_prior_ctx = _fact(OTHER_SYMBOL, "revenue", 2022, 500000.0, "2023-03-01")
    b_current, b_current_ctx = _fact(OTHER_SYMBOL, "revenue", 2023, 600000.0, "2024-03-01")
    p_prior, p_prior_ctx = _fact(
        SYMBOL, "revenue", 2022, 50.0, "2023-03-01", scope=PARENT_COMPANY
    )
    p_current, p_current_ctx = _fact(
        SYMBOL, "revenue", 2023, 77.0, "2024-03-01", scope=PARENT_COMPANY
    )
    database = _seed(
        tmp_path / "isolation.duckdb",
        [
            (a_prior, a_prior_ctx),
            (a_current, a_current_ctx),
            (b_prior, b_prior_ctx),
            (b_current, b_current_ctx),
            (p_prior, p_prior_ctx),
            (p_current, p_current_ctx),
        ],
    )
    arguments = {
        "database": database,
        "as_of": "2024-06-30",
        "years": [2022, 2023],
        "metrics": ["revenue_yoy"],
    }
    consolidated = core.build_report(symbol=SYMBOL, **arguments)
    selected = {entry["fact_id"] for entry in consolidated["as_of"]["selected_fact_index"]}
    assert selected == {a_prior["fact_id"], a_current["fact_id"]}
    row = _record(consolidated, "revenue_yoy", 2023)
    assert row["status"] == "computed"
    assert Decimal(row["value"]) == Decimal("0.25")
    assert row["input_fact_ids"] == [a_current["fact_id"], a_prior["fact_id"]]

    other = core.build_report(symbol=OTHER_SYMBOL, **arguments)
    other_selected = {entry["fact_id"] for entry in other["as_of"]["selected_fact_index"]}
    assert other_selected == {b_prior["fact_id"], b_current["fact_id"]}
    other_row = _record(other, "revenue_yoy", 2023)
    assert Decimal(other_row["value"]) == Decimal("0.2")
    assert other_row["input_fact_ids"] == [b_current["fact_id"], b_prior["fact_id"]]

    parent = core.build_report(symbol=SYMBOL, **{**arguments, "scope": PARENT_COMPANY})
    parent_selected = {entry["fact_id"] for entry in parent["as_of"]["selected_fact_index"]}
    assert parent_selected == {p_prior["fact_id"], p_current["fact_id"]}
    parent_row = _record(parent, "revenue_yoy", 2023)
    assert Decimal(parent_row["value"]) == Decimal("0.54")
    assert parent_row["input_fact_ids"] == [p_current["fact_id"], p_prior["fact_id"]]
    assert parent["request"]["scope"] == PARENT_COMPANY
    assert consolidated["request"]["scope"] == CONSOLIDATED


def test_annual_flow_and_year_end_instant_bindings(tmp_path: Path) -> None:
    profit, profit_ctx = _fact(
        SYMBOL, "net_profit_attributable_to_parent", 2023, 105.0, "2024-03-01"
    )
    opening, opening_ctx = _fact(
        SYMBOL, "equity_attributable_to_parent", 2022, 1000.0, "2023-03-01", period_type=INSTANT
    )
    closing, closing_ctx = _fact(
        SYMBOL, "equity_attributable_to_parent", 2023, 1100.0, "2024-03-01", period_type=INSTANT
    )
    m_profit, m_profit_ctx = _fact(
        INSTANT_MISMATCH_SYMBOL, "net_profit_attributable_to_parent", 2023, 90.0, "2024-03-01"
    )
    m_opening, m_opening_ctx = _fact(
        INSTANT_MISMATCH_SYMBOL,
        "equity_attributable_to_parent",
        2022,
        800.0,
        "2023-03-01",
        period_type=INSTANT,
    )
    # The closing balance is declared as an annual flow context: the tool must not bind it.
    m_closing, m_closing_ctx = _fact(
        INSTANT_MISMATCH_SYMBOL, "equity_attributable_to_parent", 2023, 900.0, "2024-03-01"
    )
    database = _seed(
        tmp_path / "bindings.duckdb",
        [
            (profit, profit_ctx),
            (opening, opening_ctx),
            (closing, closing_ctx),
            (m_profit, m_profit_ctx),
            (m_opening, m_opening_ctx),
            (m_closing, m_closing_ctx),
        ],
    )
    report = core.build_report(
        database=database, symbol=SYMBOL, as_of="2024-06-30", years=[2023], metrics=[ROE]
    )
    row = _record(report, ROE, 2023)
    assert row["status"] == "computed"
    assert Decimal(row["value"]) == Decimal("0.1")
    assert row["missing_roles"] == []
    roles = {item["role"]: item for item in row["inputs"]}
    assert roles["numerator"]["fact_id"] == profit["fact_id"]
    assert roles["opening"]["fact_id"] == opening["fact_id"]
    assert roles["closing"]["fact_id"] == closing["fact_id"]
    assert roles["opening"]["fiscal_year"] == 2022
    assert roles["opening"]["period_end"] == "2022-12-31"
    assert roles["opening"]["period_type"] == INSTANT
    assert roles["numerator"]["period_type"] == ANNUAL

    mismatched = core.build_report(
        database=database,
        symbol=INSTANT_MISMATCH_SYMBOL,
        as_of="2024-06-30",
        years=[2023],
        metrics=[ROE],
    )
    row = _record(mismatched, ROE, 2023)
    assert row["status"] == "missing_input"
    assert row["value"] is None
    closing_binding = {item["role"]: item for item in row["missing_roles"]}["closing"]
    assert closing_binding["status"] == "missing"
    assert closing_binding["reason"] == "period_context_mismatch"
    assert closing_binding["expected_period_end"] == "2023-12-31"
    assert closing_binding["expected_period_type"] == INSTANT
    excluded = mismatched["as_of"]["excluded_inputs"]
    assert [entry["fact_id"] for entry in excluded] == [m_closing["fact_id"]]
    assert excluded[0]["exclusion_reasons"] == ["period_context_mismatch"]


# ── future facts, same-year revision, adjacent-year deltas ───────────────


def test_same_year_revision_and_adjacent_year_delta_stay_separate(tmp_path: Path) -> None:
    r21, r21_ctx = _fact(REVISION_SYMBOL, "revenue", 2021, 1000.0, "2022-04-01")
    r21_recast, r21_recast_ctx = _fact(
        REVISION_SYMBOL,
        "revenue",
        2021,
        1000.0,
        "2025-03-01",
        fact_version=2,
        restatement_version="restated_same_value",
    )
    r22, r22_ctx = _fact(REVISION_SYMBOL, "revenue", 2022, 1100.0, "2023-04-01")
    orig23, orig23_ctx = _fact(REVISION_SYMBOL, "revenue", 2023, 1200.0, "2024-03-01")
    restated23, restated23_ctx = _fact(
        REVISION_SYMBOL,
        "revenue",
        2023,
        1260.0,
        "2025-03-01",
        fact_version=2,
        restatement_version="restated_v2",
        supersedes_fact_id=orig23["fact_id"],
    )
    r24, r24_ctx = _fact(REVISION_SYMBOL, "revenue", 2024, 1500.0, "2025-06-01")
    too_new, too_new_ctx = _fact(REVISION_SYMBOL, "revenue", 2025, 1600.0, "2026-05-01")
    database = _seed(
        tmp_path / "revision.duckdb",
        [
            (r21, r21_ctx),
            (r21_recast, r21_recast_ctx),
            (r22, r22_ctx),
            (orig23, orig23_ctx),
            (restated23, restated23_ctx),
            (r24, r24_ctx),
            (too_new, too_new_ctx),
        ],
    )

    early = core.build_report(
        database=database,
        symbol=REVISION_SYMBOL,
        as_of="2024-06-30",
        years=[2022, 2023],
        metrics=["revenue_yoy"],
    )
    early_ids = {entry["fact_id"] for entry in early["as_of"]["selected_fact_index"]}
    assert early_ids == {r21["fact_id"], r22["fact_id"], orig23["fact_id"]}
    early_row = _record(early, "revenue_yoy", 2023)
    assert early_row["input_fact_ids"] == [orig23["fact_id"], r22["fact_id"]]
    assert early_row["value"] == _yoy(1200, 1100)

    bridged = core.build_report(
        database=database,
        symbol=REVISION_SYMBOL,
        as_of="2024-06-30",
        compare_with="2025-06-30",
        years=[2022, 2023, 2024],
        metrics=["gross_margin", "revenue_yoy"],
    )
    before_ids = {entry["fact_id"] for entry in bridged["as_of"]["selected_fact_index"]}
    after_ids = {entry["fact_id"] for entry in bridged["compare_with"]["selected_fact_index"]}
    assert before_ids == {r21["fact_id"], r22["fact_id"], orig23["fact_id"]}
    assert after_ids == {
        r21_recast["fact_id"],
        r22["fact_id"],
        restated23["fact_id"],
        r24["fact_id"],
    }
    assert too_new["fact_id"] not in before_ids | after_ids

    yoy = {
        (row["metric_id"], row["fiscal_year"]): row
        for row in bridged["as_of"]["year_over_year"]
    }
    delta = Decimal(_record(bridged, "revenue_yoy", 2023)["value"]) - Decimal(
        _record(bridged, "revenue_yoy", 2022)["value"]
    )
    assert yoy[("revenue_yoy", 2023)]["state"] == "computed_delta"
    assert yoy[("revenue_yoy", 2023)]["delta"] == format(delta, "f")
    assert "before" not in yoy[("revenue_yoy", 2023)]
    assert yoy[("revenue_yoy", 2024)]["state"] == "not_comparable"
    assert yoy[("revenue_yoy", 2024)]["delta"] is None

    comparison = {
        (entry["metric_id"], entry["fiscal_year"]): entry
        for entry in bridged["comparison"]["entries"]
    }
    assert comparison[("revenue_yoy", 2022)]["state"] == "inputs_changed"
    revised = comparison[("revenue_yoy", 2023)]
    assert revised["state"] == "value_changed"
    assert revised["before"]["input_fact_ids"] == [orig23["fact_id"], r22["fact_id"]]
    assert revised["after"]["input_fact_ids"] == [restated23["fact_id"], r22["fact_id"]]
    assert "delta" not in revised
    restated_fiscal_2024 = comparison[("revenue_yoy", 2024)]
    assert restated_fiscal_2024["state"] == "status_changed"
    assert restated_fiscal_2024["before"]["value"] is None
    assert restated_fiscal_2024["after"]["value"] == _yoy(1500, 1260)
    assert comparison[("gross_margin", 2022)]["state"] == "unchanged"
    assert bridged["comparison"]["states"] == {
        "status_changed": 1,
        "value_changed": 1,
        "inputs_changed": 3,
        "unchanged": 1,
    }

    later = core.build_report(
        database=database,
        symbol=REVISION_SYMBOL,
        as_of="2025-06-30",
        years=[2023, 2024],
        metrics=["revenue_yoy"],
    )
    later_2023 = _record(later, "revenue_yoy", 2023)
    assert later_2023["input_fact_ids"] == [restated23["fact_id"], r22["fact_id"]]
    assert later_2023["value"] == _yoy(1260, 1100)
    later_2024 = _record(later, "revenue_yoy", 2024)
    assert later_2024["input_fact_ids"] == [r24["fact_id"], restated23["fact_id"]]
    assert later_2024["value"] == _yoy(1500, 1260)


def test_parent_evidence_resolution_states(tmp_path: Path) -> None:
    derived, derived_ctx = _fact(
        SYMBOL, "net_profit_excluding_non_recurring", 2023, 500.0, "2024-03-01"
    )
    visible_parent, visible_ctx = _fact(
        SYMBOL, "net_profit_attributable_to_parent", 2023, 450.0, "2024-02-01"
    )
    later_parent, later_ctx = _fact(SYMBOL, "net_profit", 2023, 460.0, "2025-01-01")
    absent_parent_id = "0" * 64
    database = _seed(
        tmp_path / "parents.duckdb",
        [(derived, derived_ctx), (visible_parent, visible_ctx), (later_parent, later_ctx)],
        lineage=[
            {
                "fact_id": derived["fact_id"],
                "parent_fact_ids": ", ".join(
                    [
                        visible_parent["fact_id"],
                        later_parent["fact_id"],
                        absent_parent_id,
                    ]
                ),
                "role": "output",
            }
        ],
    )
    report = core.build_report(
        database=database,
        symbol=SYMBOL,
        as_of="2024-06-30",
        years=[2023],
        metrics=["net_profit_excluding_non_recurring_yoy"],
    )
    row = _record(report, "net_profit_excluding_non_recurring_yoy", 2023)
    assert row["status"] == "insufficient_history"
    binding = row["inputs"][0]
    assert binding["status"] == "present"
    assert binding["role"] == "current"
    assert binding["fact_id"] == derived["fact_id"]
    assert binding["lineage"][0]["role"] == "output"
    assert binding["parents"] == {
        visible_parent["fact_id"]: "resolved_available_at_as_of",
        later_parent["fact_id"]: "retained_not_available_at_as_of",
        absent_parent_id: "absent_from_selected_database",
    }
    assert binding["missing_source_reference_fields"] == [
        "source_url",
        "source_hash",
        "source_page",
        "source_table",
    ]
    assert {item["role"]: item for item in row["missing_roles"]}["prior"][
        "reason"
    ] == HISTORY_MISSING_REASON


# ── precision and status boundaries ──────────────────────────────────────


@pytest.mark.parametrize(
    ("value", "unit", "source_tier", "expected_reason"),
    [
        (1000.5, core.ENGINE_FACT_UNIT, core.ENGINE_SOURCE_TIER, "value_not_exact_integer"),
        (
            float(2**53),
            core.ENGINE_FACT_UNIT,
            core.ENGINE_SOURCE_TIER,
            "value_out_of_safe_integer_range",
        ),
        (1000.0, "CNY", core.ENGINE_SOURCE_TIER, "unit_not_wan_yuan"),
        (1000.0, core.ENGINE_FACT_UNIT, "company_official", "source_tier_not_reconciled_derived"),
    ],
)
def test_incompatible_inputs_are_excluded_not_coerced(
    tmp_path: Path,
    value: float,
    unit: str,
    source_tier: str,
    expected_reason: str,
) -> None:
    prior, prior_ctx = _fact(SYMBOL, "revenue", 2022, 800.0, "2023-03-01")
    bad, bad_ctx = _fact(
        SYMBOL, "revenue", 2023, value, "2024-03-01", unit=unit, source_tier=source_tier
    )
    database = _seed(tmp_path / "precision.duckdb", [(prior, prior_ctx), (bad, bad_ctx)])
    report = core.build_report(
        database=database, symbol=SYMBOL, as_of="2024-06-30", years=[2023], metrics=["revenue_yoy"]
    )
    block = report["as_of"]
    assert block["selection_count"] == 2
    assert block["compatible_fact_count"] == 1
    excluded = block["excluded_inputs"]
    assert len(excluded) == 1
    assert excluded[0]["fact_id"] == bad["fact_id"]
    assert excluded[0]["exclusion_reasons"] == [expected_reason]
    row = _record(report, "revenue_yoy", 2023)
    assert row["status"] == "missing_input"
    assert row["value"] is None
    binding = row["inputs"][0]
    assert binding["status"] == "excluded"
    assert binding["reason"] == core.ROLE_EXCLUDED
    assert binding["exclusion_reasons"] == [expected_reason]


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_non_finite_facts_remain_excluded_in_strict_json(
    tmp_path: Path, value: float
) -> None:
    prior, prior_ctx = _fact(SYMBOL, "revenue", 2022, 800.0, "2023-03-01")
    current, current_ctx = _fact(SYMBOL, "revenue", 2023, 1000.0, "2024-03-01")
    database = _seed(tmp_path / "non-finite.duckdb", [(prior, prior_ctx), (current, current_ctx)])
    connection = duckdb.connect(str(database))
    try:
        connection.execute(
            "UPDATE financial_facts SET value = ? WHERE fact_id = ?", [value, current["fact_id"]]
        )
    finally:
        connection.close()
    before_hash = _sha256(database)
    report = core.build_report(
        database=database, symbol=SYMBOL, as_of="2024-06-30", years=[2023], metrics=["revenue_yoy"]
    )

    def reject_constant(token: str) -> None:
        raise ValueError(f"nonstandard JSON constant: {token}")

    decoded = json.loads(core.render_json(report), parse_constant=reject_constant)
    entries = {entry["fact_id"]: entry for entry in decoded["as_of"]["selected_fact_index"]}
    assert entries[current["fact_id"]]["value"] is None
    assert entries[current["fact_id"]]["value_integer"] is None
    assert entries[current["fact_id"]]["compatible"] is False
    assert entries[current["fact_id"]]["exclusion_reasons"] == ["value_not_exact_integer"]
    assert entries[prior["fact_id"]]["value"] == 800.0
    row = _record(decoded, "revenue_yoy", 2023)
    assert row["status"] == "missing_input"
    assert row["value"] is None
    assert row["inputs"][0]["status"] == "excluded"
    assert decoded["as_of"]["compatible_fact_count"] == 1

    output = tmp_path / "report"
    manifest = core.export_report(report, output)
    exported = json.loads(
        (output / "report.json").read_text(encoding="utf-8"), parse_constant=reject_constant
    )
    assert exported == decoded
    for entry in manifest["files"]:
        assert _sha256(output / entry["path"]) == entry["sha256"]
    assert _sha256(database) == before_hash


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_non_finite_json_serialization_fails_closed(value: float) -> None:
    with pytest.raises(ValueError):
        core.render_json({"unexpected_non_finite_value": value})


@pytest.mark.parametrize(
    ("prior_value", "expected_status"),
    [(0.0, "undefined_zero_denominator"), (-100.0, "not_comparable_negative_prior")],
)
def test_zero_and_negative_denominators_stay_explicit(
    tmp_path: Path, prior_value: float, expected_status: str
) -> None:
    prior, prior_ctx = _fact(SYMBOL, "revenue", 2022, prior_value, "2023-03-01")
    current, current_ctx = _fact(SYMBOL, "revenue", 2023, 1000.0, "2024-03-01")
    next_year, next_ctx = _fact(SYMBOL, "revenue", 2024, 1200.0, "2024-06-01")
    database = _seed(
        tmp_path / "denominator.duckdb",
        [(prior, prior_ctx), (current, current_ctx), (next_year, next_ctx)],
    )
    report = core.build_report(
        database=database,
        symbol=SYMBOL,
        as_of="2024-06-30",
        years=[2023, 2024],
        metrics=["revenue_yoy"],
    )
    row = _record(report, "revenue_yoy", 2023)
    assert row["status"] == expected_status
    assert row["value"] is None
    assert row["input_fact_ids"] == [current["fact_id"], prior["fact_id"]]
    yoy = report["as_of"]["year_over_year"]
    assert len(yoy) == 1
    assert (yoy[0]["prior_fiscal_year"], yoy[0]["fiscal_year"]) == (2023, 2024)
    assert yoy[0]["state"] == "not_comparable"
    assert yoy[0]["delta"] is None
    assert _record(report, "revenue_yoy", 2024)["status"] == "computed"


def test_absent_window_is_missing_not_zero(tmp_path: Path) -> None:
    database = _seed(tmp_path / "absent.duckdb", [])
    report = core.build_report(
        database=database,
        symbol=SYMBOL,
        as_of="2024-06-30",
        years=[2022, 2023],
        metrics=["revenue_yoy"],
    )
    block = report["as_of"]
    assert block["selection_count"] == 0
    assert block["excluded_inputs"] == []
    row = _record(report, "revenue_yoy", 2023)
    assert row["status"] == "missing_input"
    assert row["value"] is None
    assert {item["reason"] for item in row["missing_roles"]} == {HISTORY_MISSING_REASON}
    assert row["input_available_at_bound"] is None
    assert block["year_over_year"][0]["state"] == "not_comparable"
    assert block["year_over_year"][0]["delta"] is None


# ── selector validation ──────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("selectors", "code"),
    [
        ({"symbol": "600519"}, "INVALID_SYMBOL"),
        ({"symbol": "600519.SH "}, "INVALID_SYMBOL"),
        ({"as_of": "2024-6-30"}, "INVALID_AS_OF_DATE"),
        ({"as_of": "2024-13-40"}, "INVALID_AS_OF_DATE"),
        ({"compare_with": "2024-6-30"}, "INVALID_COMPARE_WITH"),
        ({"as_of": "2025-06-30", "compare_with": "2024-06-30"}, "COMPARE_BEFORE_AS_OF"),
        ({"years": []}, "INVALID_YEAR"),
        ({"years": [2023, 1889]}, "INVALID_YEAR"),
        ({"years": list(range(1990, 2021))}, "INVALID_YEAR"),
        ({"metrics": ["not_a_metric"]}, "UNKNOWN_METRIC"),
        ({"scope": "hidden"}, "INVALID_SCOPE"),
    ],
)
def test_invalid_selectors_fail_before_database_access(
    tmp_path: Path, selectors: dict[str, Any], code: str
) -> None:
    database = tmp_path / "absent_database.duckdb"
    arguments: dict[str, Any] = {
        "database": database,
        "symbol": SYMBOL,
        "as_of": "2024-06-30",
        "years": [2023],
    }
    arguments.update(selectors)
    with pytest.raises(core.FinancialAnalysisError) as error:
        core.build_report(**arguments)
    assert error.value.code == code
    assert not database.exists()


def test_valid_selectors_with_missing_database_fail_as_not_found(tmp_path: Path) -> None:
    database = tmp_path / "never_created.duckdb"
    with pytest.raises(core.FinancialAnalysisError) as error:
        core.build_report(database=database, symbol=SYMBOL, as_of="2024-06-30", years=[2023])
    assert error.value.code == "DATABASE_NOT_FOUND"
    assert not database.exists()


def test_validate_request_normalises_window_and_metrics() -> None:
    validated = core.validate_request(
        symbol=SYMBOL,
        as_of="2024-06-30",
        years=[2023, 2022, 2023],
        metrics=["revenue_yoy", "gross_margin"],
    )
    assert validated == {
        "symbol": SYMBOL,
        "as_of": "2024-06-30",
        "compare_with": None,
        "years": [2022, 2023],
        "metrics": ["gross_margin", "revenue_yoy"],
        "scope": CONSOLIDATED,
    }
    defaulted = core.validate_request(symbol=SYMBOL, as_of="2024-06-30", years=[2023])
    assert defaulted["metrics"] == list(core.METRIC_IDS)


# ── real CLI, export manifest, read-only boundary ────────────────────────


def test_cli_json_markdown_export_and_sanitized_failures(tmp_path: Path) -> None:
    prior, prior_ctx = _fact(SYMBOL, "revenue", 2022, 800.0, "2023-03-01")
    current, current_ctx = _fact(SYMBOL, "revenue", 2023, 1000.0, "2024-03-01")
    database = _seed(tmp_path / "cli.duckdb", [(prior, prior_ctx), (current, current_ctx)])
    before_hash = _sha256(database)
    common = (
        "--database",
        str(database),
        "--symbol",
        SYMBOL,
        "--as-of",
        "2024-06-30",
        "--year",
        "2023",
        "--metric",
        "revenue_yoy",
    )

    payload = _run_cli(*common, "--json", cwd=tmp_path)
    assert payload.returncode == 0
    assert payload.stderr == b""
    report = json.loads(payload.stdout.decode("utf-8"))
    assert report["schema"] == core.REPORT_SCHEMA
    assert report["request"]["years"] == [2023]
    row = _record(report, "revenue_yoy", 2023)
    assert row["status"] == "computed"
    assert Decimal(row["value"]) == Decimal("0.25")

    markdown = _run_cli(*common, cwd=tmp_path)
    assert markdown.returncode == 0
    assert markdown.stderr == b""
    text = markdown.stdout.decode("utf-8")
    assert "核心公司财务分析" in text
    assert "0.250000000000" in text

    output = tmp_path / "export"
    exported = _run_cli(*common, "--output", str(output), cwd=tmp_path)
    assert exported.returncode == 0
    assert exported.stderr == b""
    assert "exported 2 managed files" in exported.stdout.decode("utf-8")
    assert sorted(path.name for path in output.iterdir()) == [
        "manifest.json",
        "report.json",
        "report.md",
    ]
    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["managed_file_count"] == 2
    for entry in manifest["files"]:
        exported_file = output / entry["path"]
        assert _sha256(exported_file) == entry["sha256"]
        assert exported_file.stat().st_size == entry["byte_count"]
    exported_report = json.loads((output / "report.json").read_text(encoding="utf-8"))
    assert exported_report["selector_digest"] == report["selector_digest"]

    rerun = _run_cli(*common, "--output", str(output), cwd=tmp_path)
    assert rerun.returncode == 2
    assert rerun.stdout == b""
    assert rerun.stderr.decode("utf-8").strip() == "error: OUTPUT_PATH_EXISTS"

    bad_symbol = _run_cli(
        "--database",
        str(database),
        "--symbol",
        "600519",
        "--as-of",
        "2024-06-30",
        "--year",
        "2023",
        cwd=tmp_path,
    )
    assert bad_symbol.returncode == 2
    assert bad_symbol.stdout == b""
    assert bad_symbol.stderr.decode("utf-8").strip() == "error: INVALID_SYMBOL"

    missing_year = _run_cli(
        "--database", str(database), "--symbol", SYMBOL, "--as-of", "2024-06-30", cwd=tmp_path
    )
    assert missing_year.returncode == 2
    assert missing_year.stdout == b""
    assert "INVALID_ARGUMENTS" in missing_year.stderr.decode("utf-8")

    assert _sha256(database) == before_hash


def test_cli_never_creates_a_database_file(tmp_path: Path) -> None:
    database = tmp_path / "absent.duckdb"
    completed = _run_cli(
        "--database",
        str(database),
        "--symbol",
        SYMBOL,
        "--as-of",
        "2024-06-30",
        "--year",
        "2023",
        cwd=tmp_path,
    )
    assert completed.returncode == 2
    assert completed.stdout == b""
    assert completed.stderr.decode("utf-8").strip() == "error: DATABASE_NOT_FOUND"
    assert not database.exists()
    assert list(tmp_path.iterdir()) == []


def test_read_only_analysis_leaves_database_and_schema_untouched(tmp_path: Path) -> None:
    prior, prior_ctx = _fact(SYMBOL, "revenue", 2022, 800.0, "2023-03-01")
    current, current_ctx = _fact(SYMBOL, "revenue", 2023, 1000.0, "2024-03-01")
    database = _seed(tmp_path / "read_only.duckdb", [(prior, prior_ctx), (current, current_ctx)])
    before_hash = _sha256(database)
    before_tables = _table_names(database)
    first = core.build_report(
        database=database, symbol=SYMBOL, as_of="2024-06-30", years=[2023], metrics=["revenue_yoy"]
    )
    core.build_report(
        database=database,
        symbol=SYMBOL,
        as_of="2024-06-30",
        compare_with="2024-12-31",
        years=[2023],
        metrics=["revenue_yoy"],
    )
    assert _sha256(database) == before_hash
    assert _table_names(database) == before_tables
    assert "financial_facts" in before_tables
    assert "fact_contexts" in before_tables
    assert first["database"]["opened_read_only"] is True
    assert first["database"]["sha256"] == before_hash
    assert first["boundary"] == {
        "read_model": True,
        "production_eligible": False,
        "score_eligible": False,
        "metric_publication_proven": False,
        "stored_metric_version_admitted": False,
        "database_mutated": False,
        "schema_created": False,
    }


def test_rendered_output_is_deterministic_and_path_free(tmp_path: Path) -> None:
    prior, prior_ctx = _fact(SYMBOL, "revenue", 2022, 800.0, "2023-03-01")
    current, current_ctx = _fact(SYMBOL, "revenue", 2023, 1000.0, "2024-03-01")
    database = _seed(
        tmp_path / "determinism.duckdb", [(prior, prior_ctx), (current, current_ctx)]
    )
    arguments = {
        "database": database,
        "symbol": SYMBOL,
        "as_of": "2024-06-30",
        "years": [2023],
        "metrics": ["revenue_yoy"],
    }
    first = core.build_report(**arguments)
    second = core.build_report(**arguments)
    assert core.render_json(first) == core.render_json(second)
    assert core.render_markdown(first) == core.render_markdown(second)
    for text in (core.render_json(first), core.render_markdown(first)):
        assert str(tmp_path) not in text
        assert database.name in text
    manifest_a = core.export_report(first, tmp_path / "export-a")
    manifest_b = core.export_report(second, tmp_path / "export-b")
    assert manifest_a == manifest_b
    for name in ("report.md", "report.json", "manifest.json"):
        assert (tmp_path / "export-a" / name).read_bytes() == (
            tmp_path / "export-b" / name
        ).read_bytes()


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("symbol", OTHER_SYMBOL),
        ("symbol", ""),
        ("fiscal_year", 2022),
        ("fiscal_year", 0),
        ("period_end", "2022-12-31"),
        ("period_end", "2023-06-30"),
        ("period_start", "2023-10-01"),
        ("period_start", "2022-01-01"),
        ("period_start", ""),
        ("instant_or_duration", INSTANT),
        ("instant_or_duration", ""),
    ],
)
def test_context_binding_rejects_inconsistent_annual_flow(
    tmp_path: Path, field: str, value: Any
) -> None:
    prior, prior_ctx = _fact(SYMBOL, "revenue", 2022, 800.0, "2023-03-01")
    current, current_ctx = _fact(SYMBOL, "revenue", 2023, 1000.0, "2024-03-01")
    current_ctx[field] = value
    database = _seed(
        tmp_path / "annual-context.duckdb", [(prior, prior_ctx), (current, current_ctx)]
    )
    before_hash = _sha256(database)
    report = core.build_report(
        database=database, symbol=SYMBOL, as_of="2024-06-30", years=[2023], metrics=["revenue_yoy"]
    )
    row = _record(report, "revenue_yoy", 2023)
    assert row["status"] == "missing_input"
    assert row["value"] is None
    assert row["inputs"][0]["status"] == "excluded"
    assert row["inputs"][0]["fact_id"] == current["fact_id"]
    assert row["inputs"][0]["exclusion_reasons"] == ["period_context_mismatch"]
    assert report["as_of"]["compatible_fact_count"] == 1
    assert _sha256(database) == before_hash


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("symbol", OTHER_SYMBOL),
        ("fiscal_year", 2022),
        ("fiscal_year", 0),
        ("period_end", "2022-12-31"),
        ("period_end", "2023-06-30"),
        ("period_start", "2023-01-01"),
        ("instant_or_duration", "duration"),
        ("instant_or_duration", ""),
    ],
)
def test_context_binding_rejects_inconsistent_instant_balance(
    tmp_path: Path, field: str, value: Any
) -> None:
    profit, profit_ctx = _fact(
        SYMBOL, "net_profit_attributable_to_parent", 2023, 105.0, "2024-03-01"
    )
    opening, opening_ctx = _fact(
        SYMBOL, "equity_attributable_to_parent", 2022, 1000.0, "2023-03-01", period_type=INSTANT
    )
    closing, closing_ctx = _fact(
        SYMBOL, "equity_attributable_to_parent", 2023, 1100.0, "2024-03-01", period_type=INSTANT
    )
    closing_ctx[field] = value
    database = _seed(
        tmp_path / "instant-context.duckdb",
        [(profit, profit_ctx), (opening, opening_ctx), (closing, closing_ctx)],
    )
    before_hash = _sha256(database)
    report = core.build_report(
        database=database, symbol=SYMBOL, as_of="2024-06-30", years=[2023], metrics=[ROE]
    )
    row = _record(report, ROE, 2023)
    assert row["status"] == "missing_input"
    assert row["value"] is None
    closing_binding = next(item for item in row["inputs"] if item["role"] == "closing")
    assert closing_binding["status"] == "excluded"
    assert closing_binding["fact_id"] == closing["fact_id"]
    assert closing_binding["exclusion_reasons"] == ["period_context_mismatch"]
    assert report["as_of"]["compatible_fact_count"] == 2
    assert _sha256(database) == before_hash


@pytest.mark.parametrize("start", ["", "2023-12-31"])
def test_context_binding_accepts_valid_instant_conventions(tmp_path: Path, start: str) -> None:
    profit, profit_ctx = _fact(
        SYMBOL, "net_profit_attributable_to_parent", 2023, 105.0, "2024-03-01"
    )
    opening, opening_ctx = _fact(
        SYMBOL, "equity_attributable_to_parent", 2022, 1000.0, "2023-03-01", period_type=INSTANT
    )
    closing, closing_ctx = _fact(
        SYMBOL, "equity_attributable_to_parent", 2023, 1100.0, "2024-03-01", period_type=INSTANT
    )
    closing_ctx["period_start"] = start
    database = _seed(
        tmp_path / "valid-context.duckdb",
        [(profit, profit_ctx), (opening, opening_ctx), (closing, closing_ctx)],
    )
    report = core.build_report(
        database=database, symbol=SYMBOL, as_of="2024-06-30", years=[2023], metrics=[ROE]
    )
    row = _record(report, ROE, 2023)
    assert row["status"] == "computed"
    assert Decimal(row["value"]) == Decimal("0.1")
    assert report["as_of"]["excluded_inputs"] == []


def test_context_binding_never_falls_back_to_an_older_version(tmp_path: Path) -> None:
    prior, prior_ctx = _fact(SYMBOL, "revenue", 2022, 800.0, "2023-03-01")
    original, original_ctx = _fact(SYMBOL, "revenue", 2023, 1000.0, "2024-03-01")
    revision, revision_ctx = _fact(
        SYMBOL, "revenue", 2023, 1200.0, "2025-03-01",
        fact_version=2, restatement_version="revision", supersedes_fact_id=original["fact_id"],
    )
    revision_ctx["context_id"] += "|revision"
    revision["context_id"] = revision_ctx["context_id"]
    revision = make_verified_fact(**revision)
    revision_ctx["period_start"] = "2023-10-01"
    database = _seed(
        tmp_path / "revision-context.duckdb",
        [(prior, prior_ctx), (original, original_ctx), (revision, revision_ctx)],
    )
    before_hash = _sha256(database)
    report = core.build_report(
        database=database, symbol=SYMBOL, as_of="2024-06-30", compare_with="2025-06-30",
        years=[2023], metrics=["revenue_yoy"],
    )
    before = _record(report, "revenue_yoy", 2023)
    assert before["status"] == "computed"
    assert Decimal(before["value"]) == Decimal("0.25")
    after = report["compare_with"]["records"][0]
    assert after["status"] == "missing_input"
    assert after["value"] is None
    assert after["inputs"][0]["fact_id"] == revision["fact_id"]
    assert after["inputs"][0]["status"] == "excluded"
    selected_ids = {
        entry["fact_id"] for entry in report["compare_with"]["selected_fact_index"]
    }
    assert revision["fact_id"] in selected_ids
    assert original["fact_id"] not in selected_ids
    assert _sha256(database) == before_hash
