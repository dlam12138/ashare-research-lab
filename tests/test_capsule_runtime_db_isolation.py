"""Regressions for capsule runtime database isolation in ``run_test_capsule``.

The Stage 2G.2 runner must verify the capsule manifest first, then rebuild the
runtime database from the verified snapshot inside a task-owned temporary
directory outside the capsule, run formal processing and artifact verification
while that database exists, and only afterwards remove its own directory.  The
capsule's pre-built ``temporary_fact.duckdb`` cache is never read, changed or
deleted, whatever state it is in: stale, foreign, corrupt or absent.
"""

from __future__ import annotations

import hashlib
import json
import logging
import shutil
import tempfile
from collections.abc import Callable
from pathlib import Path
from typing import Any

import duckdb
import pytest

from ashare_research.facts.identity import build_fact_id
from ashare_research.reproducibility.artifacts import compare_artifact_runs
from ashare_research.reproducibility.capsule import (
    CAPSULE_MANIFEST,
    FACTS_FILE,
    SNAPSHOT_CONTRACT,
    SNAPSHOT_MANIFEST,
    build_test_capsule,
)
from ashare_research.tools import stage2g_reproducibility as runner

ROOT = Path(__file__).parents[1]
SNAPSHOT = ROOT / "tests" / "fixtures" / "stage2g" / "canonical_fact_snapshot_v1"
FACT_DIR = "canonical_fact_snapshot_v1"
FACTS_RELATIVE_PATH = f"{FACT_DIR}/{FACTS_FILE}"
CONTEXTS_FILE = "contexts.json"
LINEAGE_FILE = "lineage.json"
CACHE_NAME = "temporary_fact.duckdb"
FACT_COUNT = 33
MARKET_COUNT = 1351
OBSERVATION_COUNT = 8106
PROBE_CONCEPT = "net_profit_attributable_to_parent"
PROBE_YEAR = 2021
PROBE_DECIMAL = "9216101.000000000000000000"
CONTEXT_MARKER = "runtime-isolation-probe-document"
LINEAGE_MARKER = "runtime-isolation-probe-provider"


@pytest.fixture(scope="module")
def built_capsule(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Build one valid capsule per module; every test mutates its own copy."""

    capsule = tmp_path_factory.mktemp("runtime-db-capsule") / "capsule"
    build_test_capsule(capsule, committed_snapshot_dir=SNAPSHOT)
    return capsule


@pytest.fixture()
def capsule_dir(built_capsule: Path, tmp_path: Path) -> Path:
    copied = tmp_path / "capsule"
    shutil.copytree(built_capsule, copied)
    return copied


@pytest.fixture(scope="module")
def baseline_run(built_capsule: Path, tmp_path_factory: pytest.TempPathFactory) -> Path:
    """One real formal run on the pristine capsule, used as the comparison base."""

    output_root = tmp_path_factory.mktemp("runtime-db-baseline")
    runner.run_test_capsule(built_capsule, output_root=output_root, run_id="baseline")
    return output_root / "baseline"


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )


def _sha_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _logical_digest(manifest: dict[str, Any]) -> str:
    payload = {key: value for key, value in manifest.items() if key != "logical_digest"}
    return hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
            "utf-8"
        )
    ).hexdigest()


def _query(db: Path, sql: str, params: list[Any] | None = None) -> list[tuple[Any, ...]]:
    connection = duckdb.connect(str(db), read_only=True)
    try:
        return connection.execute(sql, params or []).fetchall()
    finally:
        connection.close()


def _snapshot_parts(
    capsule_dir: Path,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    snapshot_dir = capsule_dir / FACT_DIR
    return (
        _read_json(snapshot_dir / FACTS_FILE),
        _read_json(snapshot_dir / CONTEXTS_FILE),
        _read_json(snapshot_dir / LINEAGE_FILE),
    )


def _find_fact(facts: list[dict[str, Any]], concept_id: str, fiscal_year: int) -> dict[str, Any]:
    for fact in facts:
        if fact["concept_id"] == concept_id and fact["fiscal_year"] == fiscal_year:
            return fact
    raise AssertionError(f"fixture fact not found: {concept_id} {fiscal_year}")


def _publish_snapshot(
    capsule_dir: Path,
    facts: list[dict[str, Any]],
    contexts: list[dict[str, Any]],
    lineage: list[dict[str, Any]],
) -> dict[str, Any]:
    """Write edited snapshot files and re-bind both manifests to the new bytes."""

    snapshot_dir = capsule_dir / FACT_DIR
    _write_json(snapshot_dir / FACTS_FILE, facts)
    _write_json(snapshot_dir / CONTEXTS_FILE, contexts)
    _write_json(snapshot_dir / LINEAGE_FILE, lineage)
    snapshot_manifest = _read_json(snapshot_dir / SNAPSHOT_MANIFEST)
    snapshot_manifest["facts_sha256"] = _sha_of(snapshot_dir / FACTS_FILE)
    snapshot_manifest["row_count"] = len(facts)
    snapshot_manifest["context_count"] = len(contexts)
    snapshot_manifest["lineage_count"] = len(lineage)
    snapshot_manifest["concept_coverage"] = {
        concept_id: sum(fact["concept_id"] == concept_id for fact in facts)
        for concept_id in sorted({fact["concept_id"] for fact in facts})
    }
    _write_json(snapshot_dir / SNAPSHOT_MANIFEST, snapshot_manifest)
    capsule_manifest = _read_json(capsule_dir / CAPSULE_MANIFEST)
    capsule_manifest["inputs"]["canonical_fact_snapshot"]["sha256"] = snapshot_manifest[
        "facts_sha256"
    ]
    capsule_manifest["inputs"]["canonical_fact_snapshot"]["row_count"] = len(facts)
    for output in capsule_manifest["outputs"]:
        output["sha256"] = _sha_of(capsule_dir / output["relative_path"])
    capsule_manifest["logical_digest"] = _logical_digest(capsule_manifest)
    _write_json(capsule_dir / CAPSULE_MANIFEST, capsule_manifest)
    return capsule_manifest


class _StubRuntimeRun:
    """Stand in for formal processing and record the runtime database it receives."""

    def __init__(self, run_dir: Path, on_run: Callable[[], None] | None = None) -> None:
        self.run_dir = run_dir
        self.on_run = on_run
        self.calls: list[dict[str, Any]] = []
        self.runtime_dbs: list[Path] = []
        self.db_present_during_run = False
        self.db_present_during_verify = False
        self.fact_count = 0
        self.fact_values: dict[str, float] = {}
        self.context_documents: dict[str, str] = {}
        self.lineage_providers: dict[int, str] = {}

    @property
    def runtime_db(self) -> Path:
        assert self.runtime_dbs, "formal processing was never invoked"
        return self.runtime_dbs[-1]

    @property
    def runtime_dir(self) -> Path:
        return self.runtime_db.parent

    def capture(self, fact_db: Path) -> None:
        self.runtime_dbs.append(fact_db)
        self.db_present_during_run = fact_db.is_file()
        self.fact_values = {
            str(row[0]): float(row[1])
            for row in _query(fact_db, "SELECT fact_id, value FROM financial_facts")
        }
        self.fact_count = len(self.fact_values)
        self.context_documents = {
            str(row[0]): str(row[1])
            for row in _query(fact_db, "SELECT context_id, source_document FROM fact_contexts")
        }
        self.lineage_providers = {
            int(row[0]): str(row[1])
            for row in _query(fact_db, "SELECT lineage_id, source_provider FROM fact_lineage")
        }

    def run_formal(self, **kwargs: Any) -> dict[str, Any]:
        self.calls.append(dict(kwargs))
        self.capture(Path(kwargs["fact_db"]))
        if self.on_run is not None:
            self.on_run()
        self.run_dir.mkdir(parents=True, exist_ok=True)
        return {
            "run_dir": str(self.run_dir),
            "manifest": {
                "market_row_count": MARKET_COUNT,
                "observation_count": OBSERVATION_COUNT,
            },
        }

    def verify_artifacts(self, _run_dir: Path) -> dict[str, Any]:
        self.db_present_during_verify = self.runtime_db.is_file()
        return {"status": "pass"}


def _installed_stub(
    monkeypatch: pytest.MonkeyPatch,
    run_dir: Path,
    on_run: Callable[[], None] | None = None,
) -> _StubRuntimeRun:
    stub = _StubRuntimeRun(run_dir, on_run=on_run)
    monkeypatch.setattr(runner, "run_formal", stub.run_formal)
    monkeypatch.setattr(runner, "verify_artifacts", stub.verify_artifacts)
    return stub


def test_real_run_ignores_a_foreign_cache_and_preserves_its_bytes(
    capsule_dir: Path, baseline_run: Path, tmp_path: Path
) -> None:
    """A valid but stale cache must not influence a real formal run."""

    cache = capsule_dir / CACHE_NAME
    facts = _snapshot_parts(capsule_dir)[0]
    probe_id = _find_fact(facts, PROBE_CONCEPT, PROBE_YEAR)["fact_id"]
    original = _query(cache, "SELECT value FROM financial_facts WHERE fact_id = ?", [probe_id])[0][
        0
    ]
    connection = duckdb.connect(str(cache))
    try:
        connection.execute(
            "UPDATE financial_facts SET value = value + 100000.0, "
            "normalized_value = normalized_value + 100000.0, raw_value = raw_value + 100000.0 "
            "WHERE fact_id = ?",
            [probe_id],
        )
    finally:
        connection.close()
    foreign = _query(cache, "SELECT value FROM financial_facts WHERE fact_id = ?", [probe_id])[0][0]
    assert foreign != original
    cache_digest = _sha_of(cache)

    result = runner.run_test_capsule(
        capsule_dir, output_root=tmp_path / "runs", run_id="baseline"
    )

    assert result["status"] == "pass"
    assert result["artifact_verification"]["status"] == "pass"
    assert _sha_of(cache) == cache_digest
    assert (
        _query(cache, "SELECT value FROM financial_facts WHERE fact_id = ?", [probe_id])[0][0]
        == foreign
    )
    comparison = compare_artifact_runs(baseline_run, tmp_path / "runs" / "baseline")
    assert comparison["status"] == "pass"
    assert comparison["differences"] == []


@pytest.mark.parametrize("cache_state", ["corrupt", "missing"])
def test_real_run_ignores_corrupt_or_missing_cache(
    capsule_dir: Path, baseline_run: Path, tmp_path: Path, cache_state: str
) -> None:
    cache = capsule_dir / CACHE_NAME
    expected_digest: str | None = None
    if cache_state == "corrupt":
        cache.write_bytes(b"this is not a duckdb database\n")
        expected_digest = _sha_of(cache)
    else:
        cache.unlink()

    result = runner.run_test_capsule(
        capsule_dir, output_root=tmp_path / "runs", run_id="baseline"
    )

    assert result["status"] == "pass"
    assert result["artifact_verification"]["status"] == "pass"
    if expected_digest is None:
        assert not cache.exists()
    else:
        assert _sha_of(cache) == expected_digest
    comparison = compare_artifact_runs(baseline_run, tmp_path / "runs" / "baseline")
    assert comparison["status"] == "pass"


def test_runtime_database_is_built_in_an_empty_owned_directory(
    capsule_dir: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    observed: dict[str, Any] = {}
    real_build = runner.build_temp_fact_db

    def recording_build(snapshot_dir: Path, output_path: Path) -> Path:
        observed["entries_before_build"] = sorted(Path(output_path).parent.iterdir())
        observed["output_path"] = Path(output_path)
        observed["snapshot_dir"] = Path(snapshot_dir)
        return real_build(snapshot_dir, output_path)

    monkeypatch.setattr(runner, "build_temp_fact_db", recording_build)
    stub = _installed_stub(monkeypatch, tmp_path / "stub-run")

    result = runner.run_test_capsule(
        capsule_dir, output_root=tmp_path / "runs", run_id="fresh-directory"
    )

    runtime_db = observed["output_path"]
    runtime_dir = runtime_db.parent
    assert result["status"] == "pass"
    assert observed["entries_before_build"] == []
    assert observed["snapshot_dir"] == capsule_dir / FACT_DIR
    assert runtime_db.name == CACHE_NAME
    assert runtime_dir != capsule_dir
    assert capsule_dir not in runtime_dir.parents
    assert runtime_db != capsule_dir / CACHE_NAME
    assert stub.db_present_during_run is True
    assert stub.db_present_during_verify is True
    assert not runtime_dir.exists()


def test_changed_snapshot_values_are_consumed_and_cache_is_untouched(
    capsule_dir: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    facts, contexts, lineage = _snapshot_parts(capsule_dir)
    probe = _find_fact(facts, PROBE_CONCEPT, PROBE_YEAR)
    original_decimal = probe["value_decimal"]
    probe["value_decimal"] = PROBE_DECIMAL
    _publish_snapshot(capsule_dir, facts, contexts, lineage)
    cache = capsule_dir / CACHE_NAME
    cache_digest = _sha_of(cache)
    cache_value = _query(
        cache, "SELECT value FROM financial_facts WHERE fact_id = ?", [probe["fact_id"]]
    )[0][0]
    assert cache_value == float(original_decimal)

    stub = _installed_stub(monkeypatch, tmp_path / "stub-run")
    result = runner.run_test_capsule(
        capsule_dir, output_root=tmp_path / "runs", run_id="changed-values"
    )

    assert result["status"] == "pass"
    assert stub.fact_values[probe["fact_id"]] == float(PROBE_DECIMAL)
    assert stub.fact_values[probe["fact_id"]] != cache_value
    assert stub.calls[0]["fact_input_contract"] == {
        "logical_name": FACTS_RELATIVE_PATH,
        "schema_version": SNAPSHOT_CONTRACT,
        "sha256": _sha_of(capsule_dir / FACT_DIR / FACTS_FILE),
        "row_count": FACT_COUNT,
    }
    assert _sha_of(cache) == cache_digest


@pytest.mark.parametrize("edit", ["removed", "added"])
def test_missing_and_additional_snapshot_facts_are_consumed(
    capsule_dir: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, edit: str
) -> None:
    facts, contexts, lineage = _snapshot_parts(capsule_dir)
    cache = capsule_dir / CACHE_NAME
    cache_digest = _sha_of(cache)
    assert int(_query(cache, "SELECT count(*) FROM financial_facts")[0][0]) == FACT_COUNT

    if edit == "removed":
        victim = _find_fact(facts, PROBE_CONCEPT, PROBE_YEAR)
        removed_lineage = set(victim["lineage_ids"])
        facts = [fact for fact in facts if fact["fact_id"] != victim["fact_id"]]
        lineage = [row for row in lineage if row["lineage_id"] not in removed_lineage]
        referenced = {fact["context_id"] for fact in facts}
        contexts = [row for row in contexts if row["context_id"] in referenced]
        probe_id = victim["fact_id"]
        expected_count = FACT_COUNT - 1
        expected_present = False
    else:
        extra = dict(_find_fact(facts, PROBE_CONCEPT, PROBE_YEAR))
        extra["source_id"] = f"{extra['source_id']}-runtime-isolation-probe"
        extra["fact_id"] = build_fact_id(extra)
        extra["lineage_ids"] = []
        facts = [*facts, extra]
        probe_id = extra["fact_id"]
        expected_count = FACT_COUNT + 1
        expected_present = True

    _publish_snapshot(capsule_dir, facts, contexts, lineage)
    stub = _installed_stub(monkeypatch, tmp_path / "stub-run")
    result = runner.run_test_capsule(
        capsule_dir, output_root=tmp_path / "runs", run_id=f"{edit}-facts"
    )

    assert result["status"] == "pass"
    assert stub.fact_count == expected_count
    assert (probe_id in stub.fact_values) is expected_present
    assert stub.calls[0]["fact_input_contract"]["row_count"] == expected_count
    assert stub.calls[0]["fact_input_contract"]["sha256"] == _sha_of(
        capsule_dir / FACT_DIR / FACTS_FILE
    )
    assert _sha_of(cache) == cache_digest
    assert int(_query(cache, "SELECT count(*) FROM financial_facts")[0][0]) == FACT_COUNT


def test_changed_snapshot_contexts_and_lineage_are_consumed(
    capsule_dir: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    facts, contexts, lineage = _snapshot_parts(capsule_dir)
    context_row = contexts[0]
    lineage_row = lineage[0]
    context_row["source_document"] = CONTEXT_MARKER
    lineage_row["source_provider"] = LINEAGE_MARKER
    _publish_snapshot(capsule_dir, facts, contexts, lineage)
    cache = capsule_dir / CACHE_NAME
    cache_digest = _sha_of(cache)
    assert (
        _query(
            cache,
            "SELECT source_document FROM fact_contexts WHERE context_id = ?",
            [context_row["context_id"]],
        )[0][0]
        != CONTEXT_MARKER
    )
    assert (
        _query(
            cache,
            "SELECT source_provider FROM fact_lineage WHERE lineage_id = ?",
            [lineage_row["lineage_id"]],
        )[0][0]
        != LINEAGE_MARKER
    )

    stub = _installed_stub(monkeypatch, tmp_path / "stub-run")
    result = runner.run_test_capsule(
        capsule_dir, output_root=tmp_path / "runs", run_id="changed-contexts"
    )

    assert result["status"] == "pass"
    assert stub.context_documents[context_row["context_id"]] == CONTEXT_MARKER
    assert stub.lineage_providers[lineage_row["lineage_id"]] == LINEAGE_MARKER
    assert _sha_of(cache) == cache_digest


def test_repeated_runs_use_distinct_fresh_owned_paths(
    capsule_dir: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cache = capsule_dir / CACHE_NAME
    cache_digest = _sha_of(cache)
    stub = _installed_stub(monkeypatch, tmp_path / "stub-run")

    first = runner.run_test_capsule(
        capsule_dir, output_root=tmp_path / "runs", run_id="repeat-one"
    )
    second = runner.run_test_capsule(
        capsule_dir, output_root=tmp_path / "runs", run_id="repeat-two"
    )

    assert [result["status"] for result in (first, second)] == ["pass", "pass"]
    assert first["market_days"] == second["market_days"] == MARKET_COUNT
    assert first["observation_count"] == second["observation_count"] == OBSERVATION_COUNT
    assert stub.calls[0]["fact_input_contract"] == stub.calls[1]["fact_input_contract"]
    assert len(stub.runtime_dbs) == 2
    first_db, second_db = stub.runtime_dbs
    assert first_db != second_db
    assert first_db.name == second_db.name == CACHE_NAME
    for runtime_db in stub.runtime_dbs:
        assert runtime_db != capsule_dir / CACHE_NAME
        assert capsule_dir not in runtime_db.parents
        assert not runtime_db.exists()
        assert not runtime_db.parent.exists()
    assert _sha_of(cache) == cache_digest


def test_build_failure_cleans_owned_directory_and_preserves_primary_error(
    capsule_dir: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cache_digest = _sha_of(capsule_dir / CACHE_NAME)
    observed: dict[str, Path] = {}

    def failing_build(_snapshot_dir: Path, output_path: Path) -> Path:
        observed["runtime_dir"] = Path(output_path).parent
        raise RuntimeError("primary build failure")

    monkeypatch.setattr(runner, "build_temp_fact_db", failing_build)
    output_root = tmp_path / "runs"

    with pytest.raises(RuntimeError, match="primary build failure"):
        runner.run_test_capsule(capsule_dir, output_root=output_root, run_id="build-failure")

    assert not observed["runtime_dir"].exists()
    assert not output_root.exists()
    assert not (capsule_dir / "runs").exists()
    assert _sha_of(capsule_dir / CACHE_NAME) == cache_digest


def test_run_failure_preserves_existing_outputs_and_cleans_owned_directory(
    capsule_dir: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cache_digest = _sha_of(capsule_dir / CACHE_NAME)
    observed: dict[str, Path] = {}
    real_build = runner.build_temp_fact_db

    def recording_build(snapshot_dir: Path, output_path: Path) -> Path:
        observed["runtime_dir"] = Path(output_path).parent
        return real_build(snapshot_dir, output_path)

    monkeypatch.setattr(runner, "build_temp_fact_db", recording_build)
    output_root = tmp_path / "runs"
    existing_run = output_root / "existing-run"
    existing_run.mkdir(parents=True)
    sentinel = existing_run / "summary.json"
    sentinel.write_text("pre-existing output\n", encoding="utf-8")

    with pytest.raises(FileExistsError, match="overwrite existing Stage 2G run directory"):
        runner.run_test_capsule(capsule_dir, output_root=output_root, run_id="existing-run")

    assert sentinel.read_text(encoding="utf-8") == "pre-existing output\n"
    assert sorted(path.name for path in existing_run.iterdir()) == ["summary.json"]
    assert not observed["runtime_dir"].exists()
    assert _sha_of(capsule_dir / CACHE_NAME) == cache_digest


def test_artifact_failure_cleans_owned_directory_and_preserves_primary_error(
    capsule_dir: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cache_digest = _sha_of(capsule_dir / CACHE_NAME)
    stub = _installed_stub(monkeypatch, tmp_path / "stub-run")

    def failing_verify(_run_dir: Path) -> dict[str, Any]:
        assert stub.runtime_db.is_file(), "the runtime database must exist while verifying"
        raise ValueError("primary artifact failure")

    monkeypatch.setattr(runner, "verify_artifacts", failing_verify)

    with pytest.raises(ValueError, match="primary artifact failure"):
        runner.run_test_capsule(capsule_dir, output_root=tmp_path / "runs", run_id="artifact-fail")

    assert stub.run_dir.is_dir()
    assert not stub.runtime_dir.exists()
    assert _sha_of(capsule_dir / CACHE_NAME) == cache_digest


class _RecordingTemporaryDirectory(tempfile.TemporaryDirectory):
    """Keep every created temporary directory alive so retention stays assertable."""

    created: list[_RecordingTemporaryDirectory] = []

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        _RecordingTemporaryDirectory.created.append(self)


def _raise_cleanup_oserror() -> None:
    raise OSError("simulated runtime cleanup failure")


def _release_recorded_runtime_dirs() -> None:
    """Remove only the directories recorded by the failing-cleanup factory, then forget them."""

    try:
        for owned in _RecordingTemporaryDirectory.created:
            owned.__dict__.pop("cleanup", None)
            owned.cleanup()
    finally:
        _RecordingTemporaryDirectory.created.clear()


def test_owned_cleanup_oserror_is_logged_and_result_is_preserved(
    capsule_dir: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    _RecordingTemporaryDirectory.created.clear()
    monkeypatch.setattr(tempfile, "TemporaryDirectory", _RecordingTemporaryDirectory)

    def break_owned_cleanup() -> None:
        _RecordingTemporaryDirectory.created[0].cleanup = _raise_cleanup_oserror

    stub = _installed_stub(monkeypatch, tmp_path / "stub-run", on_run=break_owned_cleanup)
    output_root = tmp_path / "runs"

    with caplog.at_level(logging.WARNING, logger=runner.__name__):
        result = runner.run_test_capsule(
            capsule_dir, output_root=output_root, run_id="cleanup-oserror"
        )

    owned = _RecordingTemporaryDirectory.created[0]
    try:
        assert result["status"] == "pass"
        assert result["artifact_verification"]["status"] == "pass"
        assert stub.runtime_dir == Path(owned.name)
        assert Path(owned.name).is_dir()
        assert any(
            "cleanup failed" in record.getMessage() and owned.name in record.getMessage()
            for record in caplog.records
        )
    finally:
        _release_recorded_runtime_dirs()

    assert not Path(owned.name).exists()


def test_owned_cleanup_oserror_preserves_primary_run_error(
    capsule_dir: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    _RecordingTemporaryDirectory.created.clear()
    monkeypatch.setattr(tempfile, "TemporaryDirectory", _RecordingTemporaryDirectory)
    cache_digest = _sha_of(capsule_dir / CACHE_NAME)

    def failing_run_formal(**_kwargs: Any) -> dict[str, Any]:
        _RecordingTemporaryDirectory.created[0].cleanup = _raise_cleanup_oserror
        raise RuntimeError("primary run failure")

    monkeypatch.setattr(runner, "run_formal", failing_run_formal)
    monkeypatch.setattr(
        runner,
        "verify_artifacts",
        lambda _run_dir: pytest.fail("artifact verification must not run"),
    )
    output_root = tmp_path / "runs"

    with (
        caplog.at_level(logging.WARNING, logger=runner.__name__),
        pytest.raises(RuntimeError, match="primary run failure"),
    ):
        runner.run_test_capsule(capsule_dir, output_root=output_root, run_id="primary-run-error")

    owned = _RecordingTemporaryDirectory.created[0]
    try:
        assert Path(owned.name).is_dir()
        assert not output_root.exists()
        assert any(
            "cleanup failed" in record.getMessage() and owned.name in record.getMessage()
            for record in caplog.records
        )
        assert _sha_of(capsule_dir / CACHE_NAME) == cache_digest
    finally:
        _release_recorded_runtime_dirs()

    assert not Path(owned.name).exists()
