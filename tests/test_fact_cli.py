"""M2 Stage 1B.4.1 - CLI invocation-level tests.

Calls the real ``ashare_research.cli.main`` with a test factory so the
parser, config loading, exit-code mapping and output are exercised --
not just the service.  Provider registry, DuckDB path and output_root
are injected; the validator, repository transaction, manifest and
exit-code logic are never replaced.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from ashare_research.fact_sources.base import FactSourceProvider, SourceTier
from ashare_research.fact_sources.registry import FactSourceRegistry
from ashare_research.facts.identity import build_fact_id
from ashare_research.facts.repository import FactRepository
from ashare_research.facts.service import FactService
from ashare_research.storage.duckdb_store import DuckDBStore

SYMBOL = "601857.SH"


class StubProvider(FactSourceProvider):
    """Candidate provider returning canonical-id facts (no network)."""

    provider_name = "stub_candidate"
    source_tier = SourceTier.candidate_aggregator

    def get_financial_statements(self, symbol, start_year, end_year):
        from datetime import datetime
        now = datetime.now().isoformat()
        facts = []
        for year in range(start_year, end_year + 1):
            for cid, val in [
                ("revenue", 1e11),
                ("total_assets", 2.5e11),
                ("net_profit_attributable_to_parent", 1.4e10),
                ("operating_cash_flow", 5e10),
                ("capital_expenditure_cash", 3e10),
            ]:
                f = {
                    "concept_id": cid, "concept_version": "1",
                    "symbol": symbol, "value": val, "unit": "CNY",
                    "context_id": f"{symbol}|{year}|FY|consolidated",
                    "source_provider": self.provider_name,
                    "source_id": f"stub::{symbol}::{year}::{cid}",
                    "source_tier": "candidate_aggregator",
                    "fact_version": 1, "fiscal_year": year,
                    "report_type": "FY", "period_end": f"{year}-12-31",
                    "filing_date": f"{year + 1}-03-28",
                    "announcement_date": f"{year + 1}-03-28",
                    "available_at": f"{year + 1}-03-28",
                    "verification_status": "unverified",
                    "eligible_for_metrics": False,
                    "restatement_version": "original",
                    "raw_value": val, "raw_unit": "CNY",
                    "normalized_value": val,
                    "created_at": now,
                }
                f["fact_id"] = build_fact_id(f)
                facts.append(f)
        return pd.DataFrame(facts)

    def get_dividends(self, s, sy, ey): return pd.DataFrame()
    def get_buybacks(self, s, sy, ey): return pd.DataFrame()
    def get_shareholder_increases(self, s, sy, ey): return pd.DataFrame()
    def get_audit_opinions(self, s, sy, ey): return pd.DataFrame()


def _make_factory(tmp_path: Path, *, symbol: str = SYMBOL,
                  register_candidate: bool = True):
    """Build a service factory whose DuckDB + output live under tmp_path.

    Returns a callable ``config -> (service, repo, store)`` suitable for
    ``main(..., service_factory=...)``.  Counts of provider calls are
    tracked on the returned factory object as attributes.
    """

    db_path = str(tmp_path / "cli.duckdb")
    out_root = str(tmp_path / "cli_output")

    state = {"candidate_calls": 0, "official_calls": 0}

    class _CountingStub(StubProvider):
        def get_financial_statements(self, symbol, sy, ey):
            state["candidate_calls"] += 1
            return super().get_financial_statements(symbol, sy, ey)

    def factory(config):
        store = DuckDBStore(db_path)
        store.connect()
        repo = FactRepository(store)
        repo.ensure_schema()
        repo.seed_concepts()
        registry = FactSourceRegistry()
        if register_candidate:
            registry.register_candidate(symbol, _CountingStub())
        service = FactService(
            fact_repository=repo, source_registry=registry,
            output_root=out_root,
        )
        # expose call counts via the service for assertions
        service._test_call_counts = state  # type: ignore[attr-defined]
        return service, repo, store

    factory.call_counts = state  # type: ignore[attr-defined]
    factory.output_root = out_root  # type: ignore[attr-defined]
    factory.db_path = db_path  # type: ignore[attr-defined]
    return factory


# ── build-value-facts candidate -> exit code 2 ─────────────────────


class TestCLIBuildCandidate:
    def test_cli_build_candidate_returns_two(self, tmp_path: Path):
        from ashare_research.cli import main

        factory = _make_factory(tmp_path)
        rc = main(
            ["build-value-facts", SYMBOL,
             "--source", "candidate",
             "--start-year", "2025", "--end-year", "2025"],
            service_factory=factory,
        )
        assert rc == 2  # conditional_pass (candidate data unverified)

    def test_cli_candidate_writes_manifest_and_facts(self, tmp_path: Path):
        from ashare_research.cli import main

        factory = _make_factory(tmp_path)
        rc = main(
            ["build-value-facts", SYMBOL,
             "--source", "candidate",
             "--start-year", "2025", "--end-year", "2025"],
            service_factory=factory,
        )
        assert rc == 2
        # at least one manifest under output_root
        manifests = list(Path(factory.output_root).rglob("run_manifest.json"))
        assert len(manifests) >= 1
        import json
        with open(manifests[0], encoding="utf-8") as f:
            data = json.load(f)
        assert data["status"] == "conditional_pass"
        assert data["transaction_committed"] is True

    def test_cli_candidate_wrote_facts_to_duckdb(self, tmp_path: Path):
        from ashare_research.cli import main

        factory = _make_factory(tmp_path)
        main(
            ["build-value-facts", SYMBOL,
             "--source", "candidate",
             "--start-year", "2025", "--end-year", "2025"],
            service_factory=factory,
        )
        store = DuckDBStore(str(tmp_path / "cli.duckdb"))
        store.connect()
        n = store.connect().execute(
            "SELECT COUNT(*) FROM financial_facts WHERE symbol = ?",
            [SYMBOL],
        ).fetchone()[0]
        store.close()
        assert n > 0


# ── build-value-facts official -> exit code 1, no fallback ──────────


class TestCLIBuildOfficial:
    def test_cli_official_unavailable_returns_one(self, tmp_path: Path):
        from ashare_research.cli import main

        # factory that registers NO official provider
        factory = _make_factory(tmp_path, register_candidate=True)
        rc = main(
            ["build-value-facts", SYMBOL,
             "--source", "official",
             "--start-year", "2025", "--end-year", "2025"],
            service_factory=factory,
        )
        assert rc == 1

    def test_cli_official_does_not_fallback_to_candidate(self, tmp_path: Path):
        from ashare_research.cli import main

        factory = _make_factory(tmp_path)
        # capture stdout/stderr
        import contextlib
        import io
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            rc = main(
                ["build-value-facts", SYMBOL,
                 "--source", "official",
                 "--start-year", "2025", "--end-year", "2025"],
                service_factory=factory,
            )
        assert rc == 1
        out = err.getvalue()
        assert "official source unavailable" in out
        assert "no fallback" in out
        # candidate provider never called
        assert factory.call_counts["candidate_calls"] == 0
        # nothing written
        store = DuckDBStore(str(tmp_path / "cli.duckdb"))
        store.connect()
        n = store.connect().execute(
            "SELECT COUNT(*) FROM financial_facts WHERE symbol = ?",
            [SYMBOL],
        ).fetchone()[0]
        store.close()
        assert n == 0
        # a failed manifest exists
        manifests = list(Path(factory.output_root).rglob("run_manifest.json"))
        assert len(manifests) >= 1
        import json
        with open(manifests[0], encoding="utf-8") as f:
            data = json.load(f)
        assert data["status"] == "failed"


# ── verify-value-facts revalidates only the requested run ──────────


class TestCLIVerifyRun:
    def test_cli_verify_uses_requested_run_only(self, tmp_path: Path):
        from ashare_research.cli import main

        factory = _make_factory(tmp_path)
        # build run_a and run_b
        main(
            ["build-value-facts", SYMBOL,
             "--source", "candidate",
             "--start-year", "2025", "--end-year", "2025"],
            service_factory=factory,
        )
        # first build's run_id:
        run_a = self._latest_run_id(factory.output_root)

        # run_b builds a DIFFERENT year (2024) than run_a (2025), so the
        # two runs have disjoint canonical fact_id sets.  This makes the
        # isolation assertion meaningful: a buggy verify that loaded the
        # whole symbol would return run_a + run_b facts, not just run_a's.
        main(
            ["build-value-facts", SYMBOL,
             "--source", "candidate",
             "--start-year", "2024", "--end-year", "2024"],
            service_factory=factory,
        )
        run_b = self._latest_run_id(factory.output_root)
        assert run_a != run_b

        # verify only run_a
        import contextlib
        import io
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            rc = main(
                ["verify-value-facts", SYMBOL, "--run-id", run_a],
                service_factory=factory,
            )
        text = out.getvalue()
        assert rc == 0
        # both build run id and verification run id shown
        assert run_a in text
        assert "Verification Run:" in text or "Build Run:" in text

        # only run_a's facts were revalidated.  run_a (2025) and run_b
        # (2024) have DISJOINT canonical fact_id sets, so a buggy verify
        # that loaded the whole symbol would return both years' facts;
        # the correct verify returns only run_a's.
        store = DuckDBStore(str(tmp_path / "cli.duckdb"))
        store.connect()
        run_a_fids = {
            r[0] for r in store.connect().execute(
                "SELECT DISTINCT fact_id FROM fact_lineage "
                "WHERE run_id = ?",
                [run_a],
            ).fetchall()
        }
        run_b_fids = {
            r[0] for r in store.connect().execute(
                "SELECT DISTINCT fact_id FROM fact_lineage "
                "WHERE run_id = ?",
                [run_b],
            ).fetchall()
        }
        assert run_a_fids and run_b_fids
        # genuinely different fact sets -- this is what makes the
        # isolation assertion non-trivial (previously both runs shared
        # the same canonical fact_ids due to idempotent same-year builds).
        assert run_a_fids.isdisjoint(run_b_fids)
        # verify loaded exactly run_a's fact count (distinct fact_ids),
        # not the sum of both runs' lineage rows.
        distinct_run_a_facts = store.connect().execute(
            "SELECT COUNT(DISTINCT fact_id) FROM fact_lineage WHERE run_id = ?",
            [run_a],
        ).fetchone()[0]
        assert "Fact count:" in text
        # the printed fact count equals run_a's distinct fact count
        import re
        m = re.search(r"Fact count:\s*(\d+)", text)
        assert m is not None
        assert int(m.group(1)) == distinct_run_a_facts
        store.close()

    @staticmethod
    def _latest_run_id(output_root: str) -> str:
        import json
        manifests = sorted(
            Path(output_root).rglob("run_manifest.json"),
            key=lambda p: p.stat().st_mtime,
        )
        with open(manifests[-1], encoding="utf-8") as f:
            return json.load(f)["run_id"]
