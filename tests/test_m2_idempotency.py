"""M2 Stage 1B — Idempotency, date validation, and output isolation tests.

Uses tmp_path + ephemeral DuckDB throughout.  No network dependency.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import pandas as pd
import pytest

from ashare_research.exceptions import (
    FactVersionConflictError,
)
from ashare_research.fact_sources.base import FactSourceProvider, SourceTier
from ashare_research.fact_sources.registry import FactSourceRegistry
from ashare_research.facts.repository import FactRepository
from ashare_research.facts.service import FactService
from ashare_research.storage.duckdb_store import DuckDBStore

# ── 常量 ───────────────────────────────────────────────────────

SYMBOL = "601857.SH"

FACT_COLS = [
    "fact_id", "concept_id", "concept_version", "symbol",
    "value", "unit", "context_id", "is_derived", "derived_from",
    "derivation_definition_id", "derivation_version",
    "input_fact_ids", "source_provider", "source_id",
    "source_tier", "source_document", "source_url",
    "source_hash", "source_page", "source_table", "source_label",
    "fact_version", "restatement_version",
    "supersedes_fact_id", "filing_date", "period_end",
    "announcement_date", "available_at", "raw_value",
    "raw_unit", "normalized_value", "normalization_rule",
    "verification_status", "verification_note",
    "eligible_for_metrics", "created_at",
]

NOW = datetime.now().isoformat()


# ── 辅助函数 ────────────────────────────────────────────────────


def _make_fact(**overrides) -> dict:
    """Create a minimal valid fact dict with sensible defaults."""
    import uuid

    fact_id = overrides.get("fact_id", uuid.uuid4().hex[:12])
    base: dict = {
        "fact_id": fact_id,
        "concept_id": "revenue",
        "concept_version": "1",
        "symbol": SYMBOL,
        "value": 1000.0,
        "unit": "CNY",
        "context_id": f"{SYMBOL}|2024|FY|consolidated|original",
        "is_derived": False,
        "derived_from": "",
        "derivation_definition_id": "",
        "derivation_version": "",
        "input_fact_ids": "",
        "source_provider": "test_provider",
        "source_id": f"src_{fact_id}",
        "source_tier": "candidate_aggregator",
        "source_document": "",
        "source_url": "",
        "source_hash": "",
        "source_page": "",
        "source_table": "",
        "source_label": "",
        "fact_version": 1,
        "restatement_version": "original",
        "supersedes_fact_id": "",
        "filing_date": "2025-03-28",
        "period_end": "2024-12-31",
        "announcement_date": "2025-03-28",
        "available_at": "2025-03-28",
        "raw_value": 1000.0,
        "raw_unit": "CNY",
        "normalized_value": 1000.0,
        "normalization_rule": "",
        "verification_status": "unverified",
        "verification_note": "",
        "eligible_for_metrics": False,
        "created_at": NOW,
    }
    base.update(overrides)
    base["fact_id"] = fact_id
    return base


def _new_repo(db_path: str) -> FactRepository:
    store = DuckDBStore(db_path)
    return FactRepository(store)


def _setup_repo(db_path: str) -> FactRepository:
    repo = _new_repo(db_path)
    repo.ensure_schema()
    return repo


def _count_table(repo: FactRepository, table: str) -> int:
    conn = repo.store.connect()
    row = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()
    return row[0] if row else 0


def _has_fact(repo: FactRepository, fact_id: str) -> bool:
    conn = repo.store.connect()
    row = conn.execute(
        "SELECT COUNT(*) FROM financial_facts WHERE fact_id = ?",
        [fact_id],
    ).fetchone()
    return (row[0] > 0) if row else False


def _get_fact_value(repo: FactRepository, fact_id: str):
    conn = repo.store.connect()
    row = conn.execute(
        "SELECT value FROM financial_facts WHERE fact_id = ?",
        [fact_id],
    ).fetchone()
    return row[0] if row else None


# ── 共享 Mock Provider ──────────────────────────────────────────


class _IdempotentProvider(FactSourceProvider):
    """Returns well-formed FY-only facts that avoid any derivation."""

    provider_name = "idempotent_test"
    source_tier = SourceTier.candidate_aggregator

    def __init__(self, raw_dir: str = ""):
        super().__init__(raw_dir=raw_dir)

    def get_financial_statements(self, symbol, start_year, end_year):
        facts = []
        for year in range(start_year, end_year + 1):
            for cid, val in [
                ("revenue", 1e11),
                ("total_assets", 2.5e11),
                ("net_profit_attributable_to_parent", 1e10),
            ]:
                facts.append({
                    "fact_id": f"{symbol}|{cid}|{year}|FY|reported",
                    "concept_id": cid,
                    "concept_version": "1",
                    "symbol": symbol,
                    "value": val,
                    "unit": "CNY",
                    "context_id": (
                        f"{symbol}|{year}|FY|consolidated|original"
                    ),
                    "source_provider": "idempotent_test",
                    "source_id": f"simple::{symbol}::{year}::{cid}",
                    "source_tier": "candidate_aggregator",
                    "fact_version": 1,
                    "fiscal_year": year,
                    "report_type": "FY",
                    "period_end": f"{year}-12-31",
                    "filing_date": f"{year + 1}-03-28",
                    "announcement_date": f"{year + 1}-03-28",
                    "available_at": f"{year + 1}-03-28",
                    "verification_status": "unverified",
                    "eligible_for_metrics": False,
                    "restatement_version": "original",
                    "raw_value": val,
                    "raw_unit": "CNY",
                    "normalized_value": val,
                    "created_at": "2026-07-28T00:00:00",
                })
        return pd.DataFrame(facts)

    def get_dividends(self, s, sy, ey):
        return pd.DataFrame()

    def get_buybacks(self, s, sy, ey):
        return pd.DataFrame()

    def get_shareholder_increases(self, s, sy, ey):
        return pd.DataFrame()

    def get_audit_opinions(self, s, sy, ey):
        return pd.DataFrame()


class _SingleFactProvider(FactSourceProvider):
    """Returns exactly one fact dict, as specified."""

    provider_name = "single_fact_test"
    source_tier = SourceTier.candidate_aggregator

    def __init__(self, fact_overrides: dict | None = None, raw_dir: str = ""):
        super().__init__(raw_dir=raw_dir)
        self._overrides = fact_overrides or {}

    def get_financial_statements(self, symbol, start_year, end_year):
        year = start_year
        base = {
            "fact_id": f"{symbol}|test|{year}|FY|reported",
            "concept_id": "revenue",
            "concept_version": "1",
            "symbol": symbol,
            "value": 1e11,
            "unit": "CNY",
            "context_id": f"{symbol}|{year}|FY|consolidated|original",
            "source_provider": "single_fact_test",
            "source_id": f"single::{symbol}::{year}",
            "source_tier": "candidate_aggregator",
            "fact_version": 1,
            "fiscal_year": year,
            "report_type": "FY",
            "period_end": f"{year}-12-31",
            "filing_date": f"{year + 1}-03-28",
            "announcement_date": f"{year + 1}-03-28",
            "available_at": f"{year + 1}-03-28",
            "verification_status": "unverified",
            "eligible_for_metrics": False,
            "restatement_version": "original",
            "raw_value": 1e11,
            "raw_unit": "CNY",
            "normalized_value": 1e11,
            "created_at": "2026-07-28T00:00:00",
        }
        base.update(self._overrides)
        return pd.DataFrame([base])

    def get_dividends(self, s, sy, ey):
        return pd.DataFrame()

    def get_buybacks(self, s, sy, ey):
        return pd.DataFrame()

    def get_shareholder_increases(self, s, sy, ey):
        return pd.DataFrame()

    def get_audit_opinions(self, s, sy, ey):
        return pd.DataFrame()


def _build_service(tmp_path: Path, output_root: str | None = None):
    """Create a FactService wired with _IdempotentProvider."""
    db_path = str(tmp_path / "test.duckdb")
    store = DuckDBStore(db_path)
    store.connect()
    repo = FactRepository(store)
    repo.ensure_schema()
    repo.seed_concepts()

    registry = FactSourceRegistry()
    registry.register_candidate(SYMBOL, _IdempotentProvider())

    svc = FactService(
        fact_repository=repo,
        source_registry=registry,
        output_root=output_root or str(tmp_path / "output"),
    )
    return svc, repo, store


def _list_manifests(output_root: str, symbol: str = SYMBOL) -> list[str]:
    """Return sorted list of manifest file paths under output_root for symbol."""
    runs_dir = Path(output_root) / symbol / "runs"
    if not runs_dir.is_dir():
        return []
    manifests = []
    for run_dir in sorted(runs_dir.iterdir()):
        mf = run_dir / "run_manifest.json"
        if mf.is_file():
            manifests.append(str(mf))
    return manifests


# ═══════════════════════════════════════════════════════════════════
# TestFactIdempotency
# ═══════════════════════════════════════════════════════════════════


class TestFactIdempotency:
    """Repository-level 幂等写入 and builder-level 重复运行。"""

    # ── Repository-level ──────────────────────────────────────

    def test_store_facts_first_write_returns_inserted(self, tmp_path: Path):
        """首次写入：全部事实为 inserted。"""
        db = str(tmp_path / "test.duckdb")
        repo = _setup_repo(db)

        facts = [
            _make_fact(fact_id="f_first_1", value=100.0),
            _make_fact(fact_id="f_first_2", value=200.0),
            _make_fact(fact_id="f_first_3", value=300.0),
        ]
        with repo.transaction() as conn:
            result = repo.store_facts(facts, conn=conn)

        assert result.requested == 3
        assert result.inserted == 3
        assert result.unchanged == 0
        assert result.conflicts == 0
        assert set(result.inserted_ids) == {"f_first_1", "f_first_2", "f_first_3"}

    def test_store_facts_identical_repeat_returns_unchanged(self, tmp_path: Path):
        """相同事实再次写入 → 全部 unchanged。"""
        db = str(tmp_path / "test.duckdb")
        repo = _setup_repo(db)

        facts = [
            _make_fact(fact_id="f_repeat_1", value=100.0),
            _make_fact(fact_id="f_repeat_2", value=200.0),
        ]
        # 首次写入
        with repo.transaction() as conn:
            repo.store_facts(facts, conn=conn)

        # 再次写入相同内容
        with repo.transaction() as conn:
            result = repo.store_facts(facts, conn=conn)

        assert result.requested == 2
        assert result.inserted == 0
        assert result.unchanged == 2
        assert result.conflicts == 0

    def test_store_facts_same_id_changed_value_raises_conflict(
        self, tmp_path: Path,
    ):
        """同一 fact_id 不同 value → FactVersionConflictError。"""
        db = str(tmp_path / "test.duckdb")
        repo = _setup_repo(db)

        f1 = _make_fact(fact_id="f_conflict", value=100.0)
        with repo.transaction() as conn:
            repo.store_facts([f1], conn=conn)

        f2 = _make_fact(fact_id="f_conflict", value=200.0)
        with pytest.raises(FactVersionConflictError, match="f_conflict"):
            with repo.transaction() as conn:
                repo.store_facts([f2], conn=conn)

        # 原值仍保留
        assert _get_fact_value(repo, "f_conflict") == 100.0

    def test_fact_conflict_rolls_back_entire_batch(self, tmp_path: Path):
        """事务中任一事实冲突 → 整批回滚，已写入的好事实不留存。"""
        db = str(tmp_path / "test.duckdb")
        repo = _setup_repo(db)

        # 先写入一条锚点事实（其 ID 将被后续冲突引用）
        anchor = _make_fact(fact_id="f_anchor", value=100.0)
        with repo.transaction() as conn:
            repo.store_facts([anchor], conn=conn)

        f_good = _make_fact(fact_id="f_good", value=200.0)
        f_bad = _make_fact(fact_id="f_anchor", value=999.0)

        with pytest.raises(FactVersionConflictError), repo.transaction() as conn:
            repo.store_facts([f_good], conn=conn)
            repo.store_facts([f_bad], conn=conn)

        # 回滚后 f_good 不应存在
        assert not _has_fact(repo, "f_good")
        # f_anchor 仍保留原值
        assert _get_fact_value(repo, "f_anchor") == 100.0

    def test_new_fact_version_preserves_old_fact(self, tmp_path: Path):
        """不同 fact_id 的同 concept 事实共存，旧事实不受影响。"""
        db = str(tmp_path / "test.duckdb")
        repo = _setup_repo(db)

        f_old = _make_fact(
            fact_id="f_old_version",
            concept_id="revenue",
            value=100.0,
            restatement_version="original",
            period_end="2023-12-31",
        )
        f_new = _make_fact(
            fact_id="f_new_version",
            concept_id="revenue",
            value=120.0,
            restatement_version="restated",
            period_end="2023-12-31",
        )

        with repo.transaction() as conn:
            repo.store_facts([f_old, f_new], conn=conn)

        assert _has_fact(repo, "f_old_version")
        assert _has_fact(repo, "f_new_version")
        assert _get_fact_value(repo, "f_old_version") == 100.0
        assert _get_fact_value(repo, "f_new_version") == 120.0

    # ── Builder-level 重复构建 ──────────────────────────────

    def test_repeated_build_second_run_commits_successfully(
        self, tmp_path: Path,
    ):
        """相同参数第二次 build_facts 提交成功（conditional_pass）。"""
        svc, repo, store = _build_service(tmp_path)

        r1 = svc.build_facts(SYMBOL, 2024, 2024, source_mode="candidate")
        r2 = svc.build_facts(SYMBOL, 2024, 2024, source_mode="candidate")

        # 两次运行均成功（conditional_pass 因 critical concepts 缺失）
        assert r1["status"] in ("passed", "conditional_pass")
        assert r2["status"] in ("passed", "conditional_pass")
        assert r2["total_error_count"] == 0

        store.close()

    def test_repeated_build_keeps_fact_row_count_unchanged(
        self, tmp_path: Path,
    ):
        """第二次 build 后 financial_facts 行数不变。"""
        svc, repo, store = _build_service(tmp_path)

        svc.build_facts(SYMBOL, 2024, 2024, source_mode="candidate")
        count_after_first = _count_table(repo, "financial_facts")

        svc.build_facts(SYMBOL, 2024, 2024, source_mode="candidate")
        count_after_second = _count_table(repo, "financial_facts")

        assert count_after_first > 0
        assert count_after_first == count_after_second

        store.close()

    def test_repeated_build_creates_second_lineage_run(self, tmp_path: Path):
        """第二次 build 追加新的 lineage 记录（run_id 不同）。"""
        svc, repo, store = _build_service(tmp_path)

        svc.build_facts(SYMBOL, 2024, 2024, source_mode="candidate")
        lineage_after_first = _count_table(repo, "fact_lineage")

        svc.build_facts(SYMBOL, 2024, 2024, source_mode="candidate")
        lineage_after_second = _count_table(repo, "fact_lineage")

        # 第二次运行应追加新的 lineage 记录
        assert lineage_after_second > lineage_after_first

        # 验证两批 lineage 使用不同的 run_id
        conn = repo.store.connect()
        run_ids = set(
            row[0]
            for row in conn.execute(
                "SELECT DISTINCT run_id FROM fact_lineage",
            ).fetchall()
            if row[0]
        )
        assert len(run_ids) >= 2

        store.close()

    def test_repeated_build_writes_second_manifest(self, tmp_path: Path):
        """两次 build 分别写入独立 manifest 文件。"""
        output_root = str(tmp_path / "app_output")
        svc, repo, store = _build_service(tmp_path, output_root=output_root)

        svc.build_facts(SYMBOL, 2024, 2024, source_mode="candidate")
        manifests_after_first = _list_manifests(output_root)
        assert len(manifests_after_first) == 1

        svc.build_facts(SYMBOL, 2024, 2024, source_mode="candidate")
        manifests_after_second = _list_manifests(output_root)
        assert len(manifests_after_second) == 2

        # 两份 manifest 的 run_id 不同
        def _read_run_id(mf_path: str) -> str:
            with open(mf_path, encoding="utf-8") as f:
                return json.load(f).get("run_id", "")

        r1 = _read_run_id(manifests_after_second[0])
        r2 = _read_run_id(manifests_after_second[1])
        assert r1 != r2

        store.close()


# ═══════════════════════════════════════════════════════════════════
# TestFactDates
# ═══════════════════════════════════════════════════════════════════


class TestFactDates:
    """日期字段校验：无效日期、时序约束、PIT 门禁。"""

    @staticmethod
    def _run_build(tmp_path: Path, fact_overrides: dict) -> dict:
        """Run build_facts with a single-fact provider and return result dict."""
        db_path = str(tmp_path / "test_dates.duckdb")
        store = DuckDBStore(db_path)
        store.connect()
        repo = FactRepository(store)
        repo.ensure_schema()
        repo.seed_concepts()

        registry = FactSourceRegistry()
        provider = _SingleFactProvider(fact_overrides=fact_overrides)
        registry.register_candidate(SYMBOL, provider)

        svc = FactService(
            fact_repository=repo,
            source_registry=registry,
            output_root=str(tmp_path / "output"),
        )
        result = svc.build_facts(SYMBOL, 2025, 2025, source_mode="candidate")
        store.close()
        return result

    def test_invalid_period_end_is_rejected(self, tmp_path: Path):
        """2025-02-30 是无效日历日期 → 构建失败。"""
        result = self._run_build(
            tmp_path,
            {
                "period_end": "2025-02-30",
                "filing_date": "2025-04-30",
                "announcement_date": "2025-04-30",
                "available_at": "2025-04-30",
            },
        )
        assert result["status"] == "failed"
        assert result["total_error_count"] > 0

    def test_verified_fact_requires_announcement_date(self, tmp_path: Path):
        """verified 事实必须提供 announcement_date。"""
        result = self._run_build(
            tmp_path,
            {
                "verification_status": "verified",
                "source_tier": "company_official",
                "source_id": "cninfo::2025::test",
                "eligible_for_metrics": True,
                "announcement_date": "",
                "available_at": "2025-04-30",
                "period_end": "2024-12-31",
                "filing_date": "2025-03-28",
            },
        )
        assert result["status"] == "failed"
        assert result["total_error_count"] > 0

    def test_announcement_before_period_end_is_rejected(self, tmp_path: Path):
        """announcement_date 早于 period_end → 校验失败。"""
        result = self._run_build(
            tmp_path,
            {
                "verification_status": "verified",
                "source_tier": "company_official",
                "source_id": "cninfo::2025::test",
                "eligible_for_metrics": True,
                "period_end": "2024-12-31",
                "announcement_date": "2024-06-30",
                "filing_date": "2024-06-30",
                "available_at": "2024-07-01",
            },
        )
        assert result["status"] == "failed"
        assert result["total_error_count"] > 0

    def test_invalid_available_at_is_rejected(self, tmp_path: Path):
        """2025-13-01 是无效月份 → 构建失败。"""
        result = self._run_build(
            tmp_path,
            {
                "available_at": "2025-13-01",
                "period_end": "2024-12-31",
                "filing_date": "2025-03-28",
                "announcement_date": "2025-03-28",
            },
        )
        assert result["status"] == "failed"
        assert result["total_error_count"] > 0

    def test_candidate_empty_available_at_is_allowed_when_ineligible(
        self, tmp_path: Path,
    ):
        """候选来源 + unverified + ineligible → 空 available_at 允许。"""
        result = self._run_build(
            tmp_path,
            {
                "verification_status": "unverified",
                "eligible_for_metrics": False,
                "available_at": "",
                "period_end": "2024-12-31",
                "filing_date": "2025-03-28",
                "announcement_date": "2025-03-28",
            },
        )
        # 不因日期原因失败（conditional_pass 因 critical concepts 缺失）
        assert result["status"] in ("passed", "conditional_pass")
        assert result["total_error_count"] == 0

    def test_eligible_fact_requires_available_at(self, tmp_path: Path):
        """eligible_for_metrics=True 但无 available_at → PIT 校验失败。"""
        result = self._run_build(
            tmp_path,
            {
                "verification_status": "verified",
                "source_tier": "company_official",
                "source_id": "cninfo::2025::test",
                "eligible_for_metrics": True,
                "available_at": "",
                "period_end": "2024-12-31",
                "filing_date": "2025-03-28",
                "announcement_date": "2025-03-28",
            },
        )
        assert result["status"] == "failed"
        assert result["total_error_count"] > 0


# ═══════════════════════════════════════════════════════════════════
# TestOutputIsolation
# ═══════════════════════════════════════════════════════════════════


class TestOutputIsolation:
    """Manifest 输出隔离：只写入指定 output_root，不互相覆盖。"""

    def test_service_writes_only_under_tmp_output_root(
        self, tmp_path: Path,
    ):
        """Manifest 文件完全位于指定的 tmp output_root 目录树下。"""
        output_root = str(tmp_path / "my_outputs")
        svc, repo, store = _build_service(tmp_path, output_root=output_root)

        result = svc.build_facts(SYMBOL, 2024, 2024, source_mode="candidate")
        run_id = result["run_id"]

        # 验证 manifest 路径在 output_root 下
        expected_dir = Path(output_root) / SYMBOL / "runs" / run_id
        expected_manifest = expected_dir / "run_manifest.json"
        assert expected_manifest.is_file(), (
            f"Expected manifest at {expected_manifest}"
        )

        # 验证 manifest 内容
        with open(expected_manifest, encoding="utf-8") as f:
            data = json.load(f)
        assert data.get("run_id") == run_id
        assert data.get("company_symbol") == SYMBOL
        assert data.get("transaction_committed") is True

        # 验证没有写入项目默认 output/value_assessment 目录
        default_root = Path("output/value_assessment")
        if default_root.exists():
            # 检查默认目录下是否有本次 run_id
            default_manifest = (
                default_root / SYMBOL / "runs" / run_id / "run_manifest.json"
            )
            assert not default_manifest.exists(), (
                "Manifest leaked into default output directory"
            )

        store.close()

    def test_second_run_does_not_overwrite_first_manifest(
        self, tmp_path: Path,
    ):
        """两次构建生成两份独立 manifest，第一份内容不变。"""
        output_root = str(tmp_path / "iso_output")
        svc, repo, store = _build_service(tmp_path, output_root=output_root)

        r1 = svc.build_facts(SYMBOL, 2024, 2024, source_mode="candidate")
        r2 = svc.build_facts(SYMBOL, 2024, 2024, source_mode="candidate")

        assert r1["run_id"] != r2["run_id"]

        manifests = _list_manifests(output_root)
        assert len(manifests) == 2

        # 读出两份 manifest 并确认 run_id 正确
        run_ids = set()
        for mf_path in manifests:
            with open(mf_path, encoding="utf-8") as f:
                data = json.load(f)
            run_ids.add(data.get("run_id", ""))
            assert data.get("transaction_committed") is True

        assert r1["run_id"] in run_ids
        assert r2["run_id"] in run_ids

        store.close()
