"""Stage 1C Preflight - dual-source reconciliation rule (frozen).

Frozen rule: when two independent official sources (company website +
SSE announcement) report the same fact for the same context, a
``reconciled`` canonical fact is produced.  Only the reconciled fact is
``eligible_for_metrics``; the two source facts are retained as
``verified`` audit trail with ``eligible_for_metrics=False``.

The metrics query (``get_latest_available`` / ``query_facts`` default)
already filters ``eligible_for_metrics=TRUE``, so it returns exactly the
reconciled fact.  The audit query sees all three.  No ``source_id`` is
added to the business snapshot partition -- the reconciled fact's
``input_fact_ids`` preserves the full source provenance, and the
reconciled fact carries its own distinct ``source_id`` (e.g.
``reconciled:<src_a>+<src_b>``).

This module freezes the rule with tests.  The reconciliation engine
itself (fetching both sources, cross-verifying, emitting the reconciled
fact) is Stage 1C work.
"""

from __future__ import annotations

from pathlib import Path

from fact_test_helpers import make_test_fact

from ashare_research.facts.as_of import AsOfQuery
from ashare_research.facts.contexts import build_context_id
from ashare_research.facts.identity import build_fact_id
from ashare_research.facts.repository import FactRepository
from ashare_research.storage.duckdb_store import DuckDBStore

SYMBOL = "601857.SH"
CTX_ID = build_context_id(SYMBOL, 2024, "annual")
REVENUE_2024 = 2_350_000_000_000.0


def _setup_repo(db_path: str) -> FactRepository:
    store = DuckDBStore(db_path)
    repo = FactRepository(store)
    repo.ensure_schema()
    return repo


def _seed_context(repo: FactRepository) -> None:
    ctx = {
        "context_id": CTX_ID,
        "symbol": SYMBOL,
        "fiscal_year": 2024,
        "period_type": "annual",
        "period_start": "2024-01-01",
        "period_end": "2024-12-31",
        "instant_or_duration": "duration",
        "consolidation_scope": "consolidated",
        "accounting_standard": "CAS",
        "restatement_version": "original",
        "source_document": "",
        "filing_date": "2025-03-28",
        "created_at": "2026-07-28T00:00:00",
    }
    with repo.transaction() as conn:
        repo.store_contexts([ctx], conn=conn)


def _source_fact(*, source_id: str, source_provider: str) -> dict:
    """A verified official source fact, NOT eligible for metrics."""
    f = make_test_fact(
        symbol=SYMBOL,
        concept_id="revenue",
        context_id=CTX_ID,
        period_end="2024-12-31",
        value=REVENUE_2024,
        available_at="2025-03-28",
        announcement_date="2025-03-28",
        filing_date="2025-03-28",
        source_id=source_id,
        source_provider=source_provider,
        source_tier="company_official",
        verification_status="verified",
        verification_note=f"{source_provider} official report",
        eligible_for_metrics=False,
        fact_version=1,
        restatement_version="original",
    )
    f["fact_id"] = build_fact_id(f)
    return f


def _reconciled_fact(input_ids: list[str]) -> dict:
    """The reconciled canonical fact: eligible for metrics, references
    both sources via ``input_fact_ids`` / ``derived_from``."""
    joined = ",".join(input_ids)
    f = make_test_fact(
        symbol=SYMBOL,
        concept_id="revenue",
        context_id=CTX_ID,
        period_end="2024-12-31",
        value=REVENUE_2024,
        available_at="2025-03-29",  # reconciled after both sources landed
        announcement_date="2025-03-29",
        filing_date="2025-03-29",
        source_id="reconciled:petrochina_website+sse_announcement",
        source_provider="reconciliation",
        source_tier="company_official",
        verification_status="reconciled",
        verification_note="cross-verified petrochina website + SSE",
        eligible_for_metrics=True,
        is_derived=True,
        derived_from=joined,
        derivation_definition_id="dual_source_reconciliation",
        derivation_version="1",
        input_fact_ids=joined,
        fact_version=1,
        restatement_version="original",
    )
    f["fact_id"] = build_fact_id(f)
    return f


class TestDualSourceReconciliation:
    def _seed(self, repo: FactRepository) -> tuple[dict, dict, dict]:
        _seed_context(repo)
        src_a = _source_fact(
            source_id="petrochina_website",
            source_provider="petrochina_website",
        )
        src_b = _source_fact(
            source_id="sse_announcement",
            source_provider="sse_announcement",
        )
        rec = _reconciled_fact([src_a["fact_id"], src_b["fact_id"]])
        with repo.transaction() as conn:
            repo.store_facts([src_a, src_b, rec], conn=conn)
        return src_a, src_b, rec

    def test_three_distinct_facts_stored(self, tmp_path: Path):
        repo = _setup_repo(str(tmp_path / "t.duckdb"))
        src_a, src_b, rec = self._seed(repo)
        assert len({src_a["fact_id"], src_b["fact_id"], rec["fact_id"]}) == 3
        conn = repo.store.connect()
        n = conn.execute(
            "SELECT COUNT(*) FROM financial_facts WHERE symbol = ?",
            [SYMBOL],
        ).fetchone()[0]
        assert n == 3

    def test_metrics_query_returns_only_reconciled(self, tmp_path: Path):
        repo = _setup_repo(str(tmp_path / "t.duckdb"))
        src_a, src_b, rec = self._seed(repo)
        asof = AsOfQuery(repo)
        df = asof.get_latest_available(SYMBOL, as_of_date="2025-04-01")
        assert len(df) == 1
        assert df.iloc[0]["fact_id"] == rec["fact_id"]
        assert df.iloc[0]["verification_status"] == "reconciled"
        assert bool(df.iloc[0]["eligible_for_metrics"])

    def test_default_query_facts_returns_only_reconciled(self, tmp_path: Path):
        repo = _setup_repo(str(tmp_path / "t.duckdb"))
        src_a, src_b, rec = self._seed(repo)
        # default: verification_status IN (verified, reconciled)
        # AND eligible_for_metrics = TRUE -> only the reconciled fact
        df = repo.query_facts(SYMBOL)
        assert len(df) == 1
        assert df.iloc[0]["fact_id"] == rec["fact_id"]

    def test_audit_query_sees_all_three(self, tmp_path: Path):
        repo = _setup_repo(str(tmp_path / "t.duckdb"))
        src_a, src_b, rec = self._seed(repo)
        df = repo.get_all_versions_for_audit(SYMBOL)
        assert len(df) == 3
        fids = set(df["fact_id"].tolist())
        assert fids == {src_a["fact_id"], src_b["fact_id"], rec["fact_id"]}

    def test_source_facts_verified_but_not_eligible(self, tmp_path: Path):
        """The two source facts are retained as audit trail, never metrics."""
        repo = _setup_repo(str(tmp_path / "t.duckdb"))
        src_a, src_b, rec = self._seed(repo)
        conn = repo.store.connect()
        rows = conn.execute(
            """SELECT source_id, eligible_for_metrics, verification_status
               FROM financial_facts WHERE symbol = ?
               ORDER BY source_id""",
            [SYMBOL],
        ).fetchall()
        by_src = {r[0]: (r[1], r[2]) for r in rows}
        assert by_src["petrochina_website"] == (False, "verified")
        assert by_src["sse_announcement"] == (False, "verified")
        assert by_src["reconciled:petrochina_website+sse_announcement"] == (
            True, "reconciled",
        )

    def test_reconciled_fact_records_both_source_ids(self, tmp_path: Path):
        """The reconciled fact's input_fact_ids preserves full provenance."""
        repo = _setup_repo(str(tmp_path / "t.duckdb"))
        src_a, src_b, rec = self._seed(repo)
        conn = repo.store.connect()
        row = conn.execute(
            "SELECT input_fact_ids, derived_from FROM financial_facts "
            "WHERE fact_id = ?",
            [rec["fact_id"]],
        ).fetchone()
        stored_inputs = {s for s in row[0].split(",") if s}
        assert stored_inputs == {src_a["fact_id"], src_b["fact_id"]}
        assert row[1] == row[0]
