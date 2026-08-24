"""Stage 3C-A-R2 repository-root-independent digest identity tests."""

from __future__ import annotations

import json
import shutil
from hashlib import sha256
from pathlib import Path

import pytest

import ashare_research.mechanism.model_digest as model_digest_module
from ashare_research.mechanism.analysis_contracts import (
    UPSTREAM_INVENTORY_NAME,
    ExecutionGateError,
    enforce_execution_gate,
)
from ashare_research.mechanism.model_digest import (
    DIGEST_ALGORITHM,
    UpstreamBindingError,
    build_model_digest,
    build_pipeline_digest,
    repository_relative_key,
    source_hashes,
)
from ashare_research.tools.m3_stage3ca_pipeline import synthetic_fixture
from ashare_research.tools.m3_stage3car2_digest_probe import build_identity

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"
INVENTORY = REPORTS / UPSTREAM_INVENTORY_NAME
SOURCE_NAMES = (
    "analysis_contracts.py",
    "analysis_dataset.py",
    "crash.py",
    "regression.py",
    "bootstrap.py",
    "robustness.py",
    "evidence.py",
    "model_digest.py",
)
CONTRACT_NAMES = (
    "m3_stage3ca_analysis_pipeline_contract_v2.json",
    "m3_stage3ca_model_specification_v2.json",
    "m3_stage3ca_robustness_registry_v2.json",
    "m3_stage3ca_output_schema_v2.json",
    UPSTREAM_INVENTORY_NAME,
)


def _copy_digest_fixture(destination: Path) -> Path:
    inventory_target = destination / "reports" / UPSTREAM_INVENTORY_NAME
    inventory_target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(INVENTORY, inventory_target)
    for entry in json.loads(INVENTORY.read_text(encoding="utf-8"))["bindings"]:
        source = ROOT / entry["path"]
        target = destination / entry["path"]
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    for name in CONTRACT_NAMES[:-1]:
        source = REPORTS / name
        target = destination / "reports" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    for name in SOURCE_NAMES:
        source = ROOT / "src/ashare_research/mechanism" / name
        target = destination / "src/ashare_research/mechanism" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    return destination


def _digest_for_root(root: Path) -> tuple[str, str, dict, dict]:
    sources = [root / "src/ashare_research/mechanism" / name for name in SOURCE_NAMES]
    contracts = [root / "reports" / name for name in CONTRACT_NAMES]
    inventory = root / "reports" / UPSTREAM_INVENTORY_NAME
    pipeline, pipeline_payload = build_pipeline_digest(sources)
    model, model_payload = build_model_digest(
        pipeline_digest=pipeline,
        contract_paths=contracts,
        source_paths=sources,
        dependency_contract={"statsmodels": ">=0.14.6,<0.15", "numpy_rng": "PCG64"},
        upstream_inventory_path=inventory,
    )
    return pipeline, model, pipeline_payload, model_payload


def test_repository_relative_key_is_posix_and_has_no_absolute_root() -> None:
    key = repository_relative_key(ROOT / "reports" / UPSTREAM_INVENTORY_NAME)
    assert key == "reports/m3_stage3car_effective_upstream_sha_inventory_v1.json"
    assert ":" not in key
    assert not key.startswith(("/", "\\"))


def test_outside_repository_source_is_rejected(tmp_path: Path) -> None:
    outside = tmp_path / "outside.py"
    outside.write_text("outside = True\n", encoding="utf-8")
    with pytest.raises(UpstreamBindingError, match="DIGEST_PATH_OUTSIDE_REPOSITORY"):
        source_hashes([outside])


def test_missing_repository_source_is_rejected() -> None:
    with pytest.raises(UpstreamBindingError, match="DIGEST_SOURCE_PATH_INVALID"):
        source_hashes([ROOT / "src" / "does-not-exist.py"])


def test_source_hash_order_is_logical_path_order() -> None:
    paths = [ROOT / "src/ashare_research/mechanism" / name for name in SOURCE_NAMES]
    assert source_hashes(paths) == source_hashes(reversed(paths))


def test_symlink_resolving_outside_repository_is_rejected(tmp_path: Path) -> None:
    outside = tmp_path / "outside.py"
    outside.write_text("outside = True\n", encoding="utf-8")
    link = ROOT / "tmp" / "m3_stage3car2_outside_link.py"
    try:
        link.symlink_to(outside)
    except (OSError, NotImplementedError):
        pytest.skip("symlink creation is unavailable")
    try:
        with pytest.raises(UpstreamBindingError, match="DIGEST_PATH_OUTSIDE_REPOSITORY"):
            source_hashes([link])
    finally:
        link.unlink(missing_ok=True)


def test_pipeline_and_model_payloads_are_versioned_and_relative() -> None:
    identity = build_identity()
    assert identity["digest_algorithm"] == DIGEST_ALGORITHM
    assert identity["repository_absolute_path_in_payload"] is False
    assert identity["pipeline_payload"]["digest_algorithm"] == DIGEST_ALGORITHM
    assert identity["model_payload"]["digest_algorithm"] == DIGEST_ALGORITHM
    assert identity["model_payload"]["upstream_inventory_path"] == (
        "reports/m3_stage3car_effective_upstream_sha_inventory_v1.json"
    )


def test_same_bytes_under_different_roots_have_identical_payloads(
    tmp_path: Path, monkeypatch
) -> None:
    root_a = _copy_digest_fixture(tmp_path / "root-A" / "repo")
    root_b = _copy_digest_fixture(tmp_path / "a-completely-different-root with spaces" / "repo")
    monkeypatch.setattr(model_digest_module, "repository_root", lambda: root_a)
    identity_a = _digest_for_root(root_a)
    monkeypatch.setattr(model_digest_module, "repository_root", lambda: root_b)
    identity_b = _digest_for_root(root_b)
    assert identity_a == identity_b


def test_cross_root_digest_identity_is_not_the_old_nonportable_lock(
    tmp_path: Path, monkeypatch
) -> None:
    root_a = _copy_digest_fixture(tmp_path / "root-A" / "repo")
    monkeypatch.setattr(model_digest_module, "repository_root", lambda: root_a)
    _, model, _, _ = _digest_for_root(root_a)
    assert model != "28154ef29ac86984042c18d9d39292dd3d85ffa44450ef98d8f02add23b2ef11"
    assert model != "2b02d5a82aad0eca940f5decbce0e837086ef700dfcc3dfcba4740e82c20c85a"


def test_repo_local_contract_byte_change_changes_model_digest(
    tmp_path: Path, monkeypatch
) -> None:
    root = _copy_digest_fixture(tmp_path / "repo")
    monkeypatch.setattr(model_digest_module, "repository_root", lambda: root)
    pipeline, base, _, _ = _digest_for_root(root)
    contract = root / "reports" / "m3_stage3ca_model_specification_v2.json"
    contract.write_text(contract.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    sources = [root / "src/ashare_research/mechanism" / name for name in SOURCE_NAMES]
    contracts = [root / "reports" / name for name in CONTRACT_NAMES]
    changed, _ = build_model_digest(
        pipeline_digest=pipeline,
        contract_paths=contracts,
        source_paths=sources,
        dependency_contract={"statsmodels": ">=0.14.6,<0.15", "numpy_rng": "PCG64"},
        upstream_inventory_path=root / "reports" / UPSTREAM_INVENTORY_NAME,
    )
    assert base != changed


def test_inventory_sha_and_contract_bytes_remain_canonical() -> None:
    assert sha256(INVENTORY.read_bytes()).hexdigest() == (
        "f206780dcb6fd4c3b9d30a92025b75974284afd16eecd24770d2f812256f0031"
    )
    model_contract_sha = sha256(
        (REPORTS / "m3_stage3ca_model_specification_v2.json").read_bytes()
    ).hexdigest()
    assert model_contract_sha == (
        "3ffe410e801af507fe490c9cd88539a8859ecfc5b01a17b2a04160e3b07df23d"
    )


def test_real_development_and_holdout_gates_remain_closed() -> None:
    with pytest.raises(ExecutionGateError, match="REAL_ANALYSIS_NOT_AUTHORIZED"):
        enforce_execution_gate("development", synthetic_fixture("positive", n=8))
    frame = synthetic_fixture("positive", n=8)
    frame.loc[0, "trade_date"] = "2023-01-01"
    with pytest.raises(ExecutionGateError, match="HOLDOUT_SEALED"):
        enforce_execution_gate("synthetic", frame)
