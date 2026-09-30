"""Regression tests binding capsule input declarations to verified artifacts.

The verifier must reject internally inconsistent, missing or mislabelled input
declarations even after the manifest logical digest is recomputed, and the
Stage 2G.2 runner must refuse such a capsule before it builds inputs or creates
any run output.
"""

from __future__ import annotations

import csv
import hashlib
import json
import shutil
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from ashare_research.reproducibility.capsule import (
    CANONICAL_PORTABLE_OUTPUT_PATHS,
    CAPSULE_MANIFEST,
    CAPSULE_SCHEMA_VERSION,
    DETERMINISTIC_BUILD_TIME,
    MARKET_FILE,
    MARKET_FIXTURE_DIR,
    SNAPSHOT_CONTRACT,
    SNAPSHOT_MANIFEST,
    build_test_capsule,
    compare_capsules,
    verify_capsule_manifest,
)
from ashare_research.tools import stage2g_reproducibility as runner

ROOT = Path(__file__).parents[1]
SNAPSHOT = ROOT / "tests" / "fixtures" / "stage2g" / "canonical_fact_snapshot_v1"
FACT_DIR = "canonical_fact_snapshot_v1"
FACTS_FILE_NAME = "facts.json"
MARKET_RELATIVE_PATH = f"{MARKET_FIXTURE_DIR}/{MARKET_FILE}"
REAL_INPUT_SEPARATION = (
    "test-only synthetic and canonical export/read-model inputs; never a real-mode fallback"
)
FACT_COUNT = 33
MARKET_COUNT = 1351
OBSERVATION_COUNT = 8106

MSG_MODE = "mode must be test_capsule"
MSG_NETWORK = "network_used must be false"
MSG_DB = "default_db_mutated must be false"
MSG_INPUTS = "inputs must contain exactly the declared snapshots"
MSG_FACT_SHAPE = "canonical fact input declaration has an invalid shape"
MSG_MARKET_SHAPE = "market input declaration has an invalid shape"
MSG_FACT_PATH = "canonical fact input declaration has an invalid path"
MSG_MARKET_PATH = "market input declaration has an invalid path"
MSG_FACT_LABELS = "canonical fact input declaration has invalid test labels"
MSG_MARKET_LABELS = "market input declaration has invalid test labels"
MSG_FACT_HASH = "canonical fact input declaration has an invalid SHA256"
MSG_MARKET_HASH = "market input declaration has an invalid SHA256"
MSG_FACT_COUNT = "canonical fact input declaration has an invalid row count"
MSG_MARKET_COUNT = "market input declaration has an invalid row count"
MSG_FACT_HASH_MISMATCH = "canonical fact input hash does not match validated snapshot"
MSG_FACT_COUNT_MISMATCH = "canonical fact input row count does not match validated snapshot"
MSG_FACT_VERSION = "canonical fact input contract version does not match snapshot"
MSG_MARKET_HASH_MISMATCH = "market input hash does not match verified CSV"
MSG_MARKET_COUNT_MISMATCH = "market input row count does not match verified CSV"
MSG_DIGEST = "capsule manifest logical digest mismatch"

_UNSET = object()


@pytest.fixture(scope="module")
def built_capsule(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Build one valid capsule per module; tests copy it before mutating."""

    capsule = tmp_path_factory.mktemp("capsule-build") / "capsule"
    build_test_capsule(capsule, committed_snapshot_dir=SNAPSHOT)
    return capsule


@pytest.fixture()
def capsule_dir(built_capsule: Path, tmp_path: Path) -> Path:
    copied = tmp_path / "capsule"
    shutil.copytree(built_capsule, copied)
    return copied


def _manifest(capsule_dir: Path) -> dict[str, Any]:
    return json.loads((capsule_dir / CAPSULE_MANIFEST).read_text(encoding="utf-8"))


def _logical_digest(manifest: dict[str, Any]) -> str:
    payload = {key: value for key, value in manifest.items() if key != "logical_digest"}
    return hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
            "utf-8"
        )
    ).hexdigest()


def _write_manifest(capsule_dir: Path, manifest: dict[str, Any]) -> None:
    (capsule_dir / CAPSULE_MANIFEST).write_text(
        json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )


def _rewrite_manifest(capsule_dir: Path, mutate: Callable[[dict[str, Any]], None]) -> None:
    """Mutate the manifest and recompute the logical digest.

    Every rejection case must be found by the input-binding contract itself, not
    by the logical digest guard, so the digest is always recomputed after the
    deliberate mutation.
    """

    manifest = _manifest(capsule_dir)
    mutate(manifest)
    manifest["logical_digest"] = _logical_digest(manifest)
    _write_manifest(capsule_dir, manifest)


def _mutator(*path: str, value: object = _UNSET) -> Callable[[dict[str, Any]], None]:
    """Return a mutation that sets (or, without a value, removes) a nested key."""

    def mutate(manifest: dict[str, Any]) -> None:
        target: Any = manifest
        for key in path[:-1]:
            target = target[key]
        if value is _UNSET:
            target.pop(path[-1])
        else:
            target[path[-1]] = value

    return mutate


def _fact(*path: str, value: object = _UNSET) -> Callable[[dict[str, Any]], None]:
    return _mutator("inputs", "canonical_fact_snapshot", *path, value=value)


def _market(*path: str, value: object = _UNSET) -> Callable[[dict[str, Any]], None]:
    return _mutator("inputs", "market_snapshot", *path, value=value)


def _add_extra_input(manifest: dict[str, Any]) -> None:
    manifest["inputs"]["third_snapshot"] = {"relative_path": "third"}


def _sha_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


REJECTED_INPUT_CASES = [
    pytest.param(_mutator("mode", value="real_research"), MSG_MODE, id="mode-real"),
    pytest.param(_mutator("mode"), MSG_MODE, id="mode-missing"),
    pytest.param(_mutator("network_used", value=True), MSG_NETWORK, id="network-true"),
    pytest.param(_mutator("network_used", value="false"), MSG_NETWORK, id="network-string"),
    pytest.param(_mutator("network_used"), MSG_NETWORK, id="network-missing"),
    pytest.param(_mutator("default_db_mutated", value=True), MSG_DB, id="db-mutated"),
    pytest.param(_mutator("default_db_mutated", value=0), MSG_DB, id="db-int"),
    pytest.param(_mutator("default_db_mutated"), MSG_DB, id="db-missing"),
    pytest.param(_mutator("inputs"), MSG_INPUTS, id="inputs-missing"),
    pytest.param(_mutator("inputs", value=None), MSG_INPUTS, id="inputs-null"),
    pytest.param(_mutator("inputs", value=[]), MSG_INPUTS, id="inputs-list"),
    pytest.param(_mutator("inputs", "market_snapshot"), MSG_INPUTS, id="market-mapping-missing"),
    pytest.param(_add_extra_input, MSG_INPUTS, id="inputs-extra-mapping"),
    pytest.param(_fact(value=None), MSG_FACT_SHAPE, id="fact-null"),
    pytest.param(_fact(value=["relative_path"]), MSG_FACT_SHAPE, id="fact-list"),
    pytest.param(_fact("row_count"), MSG_FACT_SHAPE, id="fact-count-missing"),
    pytest.param(_fact("authoritative"), MSG_FACT_SHAPE, id="fact-label-missing"),
    pytest.param(_fact("unknown", value=1), MSG_FACT_SHAPE, id="fact-extra-field"),
    pytest.param(_market(value="market"), MSG_MARKET_SHAPE, id="market-string"),
    pytest.param(_market("test_only"), MSG_MARKET_SHAPE, id="market-label-missing"),
    pytest.param(
        _market("contract_version", value=SNAPSHOT_CONTRACT),
        MSG_MARKET_SHAPE,
        id="market-version-extra",
    ),
    pytest.param(
        _fact("relative_path", value=FACT_DIR.removesuffix("_v1")),
        MSG_FACT_PATH,
        id="fact-path-wrong-name",
    ),
    pytest.param(
        _fact("relative_path", value=f"../{FACT_DIR}"),
        MSG_FACT_PATH,
        id="fact-path-traversal",
    ),
    pytest.param(
        _market("relative_path", value=MARKET_FIXTURE_DIR),
        MSG_MARKET_PATH,
        id="market-path-dir",
    ),
    pytest.param(
        _market("relative_path", value=f"{MARKET_FIXTURE_DIR}/other.csv"),
        MSG_MARKET_PATH,
        id="market-path-other-file",
    ),
    pytest.param(_fact("authoritative", value=True), MSG_FACT_LABELS, id="fact-authoritative-true"),
    pytest.param(_fact("authoritative", value=0), MSG_FACT_LABELS, id="fact-authoritative-int"),
    pytest.param(_fact("test_only", value=False), MSG_FACT_LABELS, id="fact-test-only-false"),
    pytest.param(_fact("test_only", value="true"), MSG_FACT_LABELS, id="fact-test-only-string"),
    pytest.param(
        _market("authoritative", value=True),
        MSG_MARKET_LABELS,
        id="market-authoritative-true",
    ),
    pytest.param(_market("test_only", value=1), MSG_MARKET_LABELS, id="market-test-only-int"),
    pytest.param(_fact("sha256", value="0" * 63), MSG_FACT_HASH, id="fact-hash-short"),
    pytest.param(_fact("sha256", value=123), MSG_FACT_HASH, id="fact-hash-int"),
    pytest.param(_fact("sha256", value="g" * 64), MSG_FACT_HASH, id="fact-hash-non-hex"),
    pytest.param(_fact("row_count", value=True), MSG_FACT_COUNT, id="fact-count-bool"),
    pytest.param(_fact("row_count", value=str(FACT_COUNT)), MSG_FACT_COUNT, id="fact-count-string"),
    pytest.param(_fact("row_count", value=-1), MSG_FACT_COUNT, id="fact-count-negative"),
    pytest.param(_market("sha256", value=None), MSG_MARKET_HASH, id="market-hash-null"),
    pytest.param(_market("sha256", value="A" * 64), MSG_MARKET_HASH, id="market-hash-upper"),
    pytest.param(_market("row_count", value=False), MSG_MARKET_COUNT, id="market-count-bool"),
    pytest.param(
        _market("row_count", value=float(MARKET_COUNT)),
        MSG_MARKET_COUNT,
        id="market-count-float",
    ),
    pytest.param(_fact("sha256", value="0" * 64), MSG_FACT_HASH_MISMATCH, id="fact-hash-mismatch"),
    pytest.param(
        _fact("row_count", value=FACT_COUNT + 1),
        MSG_FACT_COUNT_MISMATCH,
        id="fact-count-mismatch",
    ),
    pytest.param(_fact("row_count", value=0), MSG_FACT_COUNT_MISMATCH, id="fact-count-zero"),
    pytest.param(
        _fact("contract_version", value="other_contract"),
        MSG_FACT_VERSION,
        id="fact-version-other",
    ),
    pytest.param(_fact("contract_version", value=None), MSG_FACT_VERSION, id="fact-version-null"),
    pytest.param(
        _market("sha256", value="0" * 64),
        MSG_MARKET_HASH_MISMATCH,
        id="market-hash-mismatch",
    ),
    pytest.param(
        _market("row_count", value=MARKET_COUNT - 1),
        MSG_MARKET_COUNT_MISMATCH,
        id="market-count-mismatch",
    ),
]

REJECTED_RUNNER_CASES = [
    pytest.param(_mutator("mode", value="real_research"), MSG_MODE, id="mode-real"),
    pytest.param(_fact("sha256", value="0" * 64), MSG_FACT_HASH_MISMATCH, id="fact-hash"),
    pytest.param(_market("test_only", value=False), MSG_MARKET_LABELS, id="market-label"),
    pytest.param(
        _market("row_count", value=MARKET_COUNT - 1),
        MSG_MARKET_COUNT_MISMATCH,
        id="market-count",
    ),
]


@pytest.mark.parametrize(("mutate", "match"), REJECTED_INPUT_CASES)
def test_inconsistent_input_declaration_is_rejected(
    capsule_dir: Path,
    mutate: Callable[[dict[str, Any]], None],
    match: str,
) -> None:
    _rewrite_manifest(capsule_dir, mutate)
    with pytest.raises(ValueError, match=match):
        verify_capsule_manifest(capsule_dir)


def test_declared_bindings_match_actual_verified_artifacts(capsule_dir: Path) -> None:
    manifest = verify_capsule_manifest(capsule_dir)
    facts_path = capsule_dir / FACT_DIR / FACTS_FILE_NAME
    facts = json.loads(facts_path.read_text(encoding="utf-8"))
    market_path = capsule_dir / MARKET_RELATIVE_PATH
    with market_path.open("r", encoding="utf-8", newline="") as handle:
        market_rows = list(csv.DictReader(handle))
    snapshot_manifest = json.loads(
        (capsule_dir / FACT_DIR / SNAPSHOT_MANIFEST).read_text(encoding="utf-8")
    )

    assert manifest["inputs"]["canonical_fact_snapshot"] == {
        "relative_path": FACT_DIR,
        "sha256": _sha_of(facts_path),
        "row_count": len(facts),
        "authoritative": False,
        "test_only": True,
    }
    assert manifest["inputs"]["market_snapshot"] == {
        "relative_path": MARKET_RELATIVE_PATH,
        "sha256": _sha_of(market_path),
        "row_count": len(market_rows),
        "authoritative": False,
        "test_only": True,
    }
    assert snapshot_manifest["contract"] == SNAPSHOT_CONTRACT
    assert snapshot_manifest["facts_sha256"] == _sha_of(facts_path)
    assert snapshot_manifest["row_count"] == len(facts) == FACT_COUNT
    assert len(market_rows) == MARKET_COUNT


def test_builder_manifest_bytes_are_reproduced_from_artifacts(capsule_dir: Path) -> None:
    """Reconstruct the whole manifest, including its digest, from verified artifacts."""

    snapshot_manifest = json.loads(
        (capsule_dir / FACT_DIR / SNAPSHOT_MANIFEST).read_text(encoding="utf-8")
    )
    market_path = capsule_dir / MARKET_RELATIVE_PATH
    with market_path.open("r", encoding="utf-8", newline="") as handle:
        market_count = sum(1 for _ in csv.DictReader(handle))
    expected: dict[str, Any] = {
        "contract": CAPSULE_SCHEMA_VERSION,
        "generated_at": DETERMINISTIC_BUILD_TIME,
        "mode": "test_capsule",
        "network_used": False,
        "default_db_mutated": False,
        "inputs": {
            "canonical_fact_snapshot": {
                "relative_path": FACT_DIR,
                "sha256": snapshot_manifest["facts_sha256"],
                "row_count": snapshot_manifest["row_count"],
                "authoritative": False,
                "test_only": True,
            },
            "market_snapshot": {
                "relative_path": MARKET_RELATIVE_PATH,
                "sha256": _sha_of(market_path),
                "row_count": market_count,
                "authoritative": False,
                "test_only": True,
            },
        },
        "outputs": [
            {"relative_path": relative_path, "sha256": _sha_of(capsule_dir / relative_path)}
            for relative_path in sorted(CANONICAL_PORTABLE_OUTPUT_PATHS)
        ],
        "real_input_separation": REAL_INPUT_SEPARATION,
    }
    expected["logical_digest"] = _logical_digest(expected)
    expected_bytes = (
        json.dumps(expected, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    ).encode("utf-8")

    assert (capsule_dir / CAPSULE_MANIFEST).read_bytes() == expected_bytes


def test_stale_logical_digest_is_rejected(capsule_dir: Path) -> None:
    manifest = _manifest(capsule_dir)
    manifest["generated_at"] = "2026-01-01T00:00:00+08:00"
    _write_manifest(capsule_dir, manifest)
    with pytest.raises(ValueError, match=MSG_DIGEST):
        verify_capsule_manifest(capsule_dir)


def test_recomputed_digest_after_unrelated_change_verifies(capsule_dir: Path) -> None:
    """The mutation helper really recomputes the digest; other fields stay unbound."""

    _rewrite_manifest(
        capsule_dir,
        lambda manifest: manifest.update(generated_at="2026-01-01T00:00:00+08:00"),
    )
    manifest = verify_capsule_manifest(capsule_dir)
    assert manifest["generated_at"] == "2026-01-01T00:00:00+08:00"
    assert manifest["logical_digest"] == _logical_digest(manifest)


def test_optional_fact_contract_version_is_accepted(capsule_dir: Path) -> None:
    _rewrite_manifest(capsule_dir, _fact("contract_version", value=SNAPSHOT_CONTRACT))
    manifest = verify_capsule_manifest(capsule_dir)
    declaration = manifest["inputs"]["canonical_fact_snapshot"]
    assert declaration["contract_version"] == SNAPSHOT_CONTRACT
    assert set(declaration) == {
        "relative_path",
        "sha256",
        "row_count",
        "authoritative",
        "test_only",
        "contract_version",
    }


@pytest.mark.parametrize("declared_version", [None, SNAPSHOT_CONTRACT])
def test_valid_capsule_reaches_runner_with_declared_fact_contract(
    capsule_dir: Path,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    declared_version: str | None,
) -> None:
    if declared_version is not None:
        _rewrite_manifest(capsule_dir, _fact("contract_version", value=declared_version))
    manifest = _manifest(capsule_dir)
    captured: dict[str, Any] = {}
    stub_run_dir = tmp_path / "stub_run"
    stub_run_dir.mkdir()

    def fake_run_formal(**kwargs: Any) -> dict[str, Any]:
        captured.update(kwargs)
        return {
            "run_dir": str(stub_run_dir),
            "manifest": {
                "market_row_count": MARKET_COUNT,
                "observation_count": OBSERVATION_COUNT,
            },
        }

    monkeypatch.setattr(runner, "run_formal", fake_run_formal)
    monkeypatch.setattr(runner, "verify_artifacts", lambda _path: {"status": "pass"})

    result = runner.run_test_capsule(capsule_dir, output_root=tmp_path / "runs", run_id="stub")

    assert result["status"] == "pass"
    assert captured["fact_input_contract"] == {
        "logical_name": f"{FACT_DIR}/{FACTS_FILE_NAME}",
        "schema_version": declared_version or SNAPSHOT_CONTRACT,
        "sha256": manifest["inputs"]["canonical_fact_snapshot"]["sha256"],
        "row_count": manifest["inputs"]["canonical_fact_snapshot"]["row_count"],
    }
    assert captured["fact_db"] == capsule_dir / "temporary_fact.duckdb"
    assert captured["market_mode"] == "test_capsule"
    assert captured["publish_reports"] is False


@pytest.mark.parametrize(("mutate", "match"), REJECTED_RUNNER_CASES)
def test_runner_rejects_invalid_metadata_before_run_formal_or_output(
    capsule_dir: Path,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    mutate: Callable[[dict[str, Any]], None],
    match: str,
) -> None:
    calls: list[dict[str, Any]] = []

    def forbidden_run_formal(**kwargs: Any) -> dict[str, Any]:
        calls.append(kwargs)
        raise AssertionError("run_formal must not run for an invalid capsule")

    monkeypatch.setattr(runner, "run_formal", forbidden_run_formal)
    monkeypatch.setattr(
        runner,
        "build_temp_fact_db",
        lambda *_args, **_kwargs: pytest.fail("temporary fact DB must not be built"),
    )
    _rewrite_manifest(capsule_dir, mutate)
    output_root = tmp_path / "runs"

    with pytest.raises(ValueError, match=match):
        runner.run_test_capsule(capsule_dir, output_root=output_root, run_id="invalid")

    assert calls == []
    assert not output_root.exists()
    assert not (capsule_dir / "runs").exists()


def test_valid_capsule_run_and_comparison_remain_compatible(
    capsule_dir: Path, tmp_path: Path
) -> None:
    duplicate = tmp_path / "capsule-copy"
    shutil.copytree(capsule_dir, duplicate)
    comparison = compare_capsules(capsule_dir, duplicate)
    assert comparison["status"] == "pass"
    assert comparison["differences"] == []

    result = runner.run_test_capsule(
        capsule_dir,
        output_root=tmp_path / "runs",
        run_id="valid-capsule-compat",
    )
    assert result["status"] == "pass"
    assert result["market_days"] == MARKET_COUNT
    assert result["observation_count"] == OBSERVATION_COUNT
    assert result["artifact_verification"]["status"] == "pass"
    assert result["network_used"] is False
    assert result["default_db_mutated"] is False
