"""Validation of the complete portable test capsule output inventory."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from ashare_research.reproducibility import capsule as capsule_module
from ashare_research.reproducibility.capsule import (
    CANONICAL_PORTABLE_OUTPUT_PATHS,
    build_test_capsule,
    verify_capsule_manifest,
)

SNAPSHOT = Path(__file__).parent / "fixtures" / "stage2g" / "canonical_fact_snapshot_v1"


@pytest.fixture()
def capsule_dir(tmp_path: Path) -> Path:
    output = tmp_path / "capsule"
    build_test_capsule(output, committed_snapshot_dir=SNAPSHOT)
    return output


def _rewrite_manifest(capsule_dir: Path, mutate) -> None:
    path = capsule_dir / "capsule_manifest.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    mutate(manifest)
    payload = {key: value for key, value in manifest.items() if key != "logical_digest"}
    manifest["logical_digest"] = hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
            "utf-8"
        )
    ).hexdigest()
    path.write_text(
        json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )


@pytest.mark.parametrize("missing", CANONICAL_PORTABLE_OUTPUT_PATHS)
def test_missing_portable_output_is_rejected(capsule_dir: Path, missing: str) -> None:
    def remove(manifest: dict) -> None:
        manifest["outputs"] = [
            entry for entry in manifest["outputs"] if entry["relative_path"] != missing
        ]

    _rewrite_manifest(capsule_dir, remove)
    with pytest.raises(ValueError, match="complete inventory|incomplete"):
        verify_capsule_manifest(capsule_dir)


@pytest.mark.parametrize("outputs", [None, [], {}])
def test_empty_or_non_list_inventory_is_rejected(
    capsule_dir: Path, outputs: object, monkeypatch: pytest.MonkeyPatch
) -> None:
    _rewrite_manifest(capsule_dir, lambda manifest: manifest.update(outputs=outputs))
    monkeypatch.setattr(
        capsule_module, "sha256_file", lambda _path: pytest.fail("read output too early")
    )
    with pytest.raises(ValueError, match="complete inventory"):
        verify_capsule_manifest(capsule_dir)


def test_missing_inventory_is_rejected(capsule_dir: Path) -> None:
    _rewrite_manifest(capsule_dir, lambda manifest: manifest.pop("outputs"))
    with pytest.raises(ValueError, match="complete inventory"):
        verify_capsule_manifest(capsule_dir)


def test_non_dict_manifest_is_rejected(capsule_dir: Path) -> None:
    (capsule_dir / "capsule_manifest.json").write_text("[]\n", encoding="utf-8")
    with pytest.raises(ValueError, match="unsupported"):
        verify_capsule_manifest(capsule_dir)


def test_duplicate_output_is_rejected(capsule_dir: Path) -> None:
    def duplicate(manifest: dict) -> None:
        manifest["outputs"][1] = dict(manifest["outputs"][0])

    _rewrite_manifest(capsule_dir, duplicate)
    with pytest.raises(ValueError, match="invalid or unexpected path"):
        verify_capsule_manifest(capsule_dir)


@pytest.mark.parametrize(
    "entry",
    [
        None,
        {"relative_path": [], "sha256": "0" * 64},
        {"relative_path": "extra.json", "sha256": "0" * 64},
        {"relative_path": "../escape", "sha256": "0" * 64},
        {"relative_path": "canonical_fact_snapshot_v1\\facts.json", "sha256": "0" * 64},
        {"relative_path": "canonical_fact_snapshot_v1/facts.json", "sha256": "0" * 63},
        {"relative_path": "canonical_fact_snapshot_v1/facts.json", "sha256": "g" * 64},
        {"relative_path": "canonical_fact_snapshot_v1/facts.json"},
        {"relative_path": "canonical_fact_snapshot_v1/facts.json", "sha256": 1},
        {
            "relative_path": "canonical_fact_snapshot_v1/facts.json",
            "sha256": "0" * 64,
            "extra": True,
        },
    ],
)
def test_malformed_output_entry_is_rejected(capsule_dir: Path, entry: object) -> None:
    _rewrite_manifest(capsule_dir, lambda manifest: manifest["outputs"].__setitem__(0, entry))
    with pytest.raises(ValueError):
        verify_capsule_manifest(capsule_dir)


def test_valid_generated_capsule_has_shared_complete_inventory(capsule_dir: Path) -> None:
    manifest = verify_capsule_manifest(capsule_dir)
    assert {entry["relative_path"] for entry in manifest["outputs"]} == set(
        CANONICAL_PORTABLE_OUTPUT_PATHS
    )
    assert [entry["relative_path"] for entry in manifest["outputs"]] == sorted(
        CANONICAL_PORTABLE_OUTPUT_PATHS
    )


@pytest.mark.parametrize("digest", [None, 1, "0" * 63, "g" * 64])
def test_invalid_hash_rejected_before_file_reads(capsule_dir, monkeypatch, digest):
    def change_hash(manifest):
        manifest["outputs"][-1]["sha256"] = digest

    _rewrite_manifest(capsule_dir, change_hash)
    monkeypatch.setattr(
        capsule_module, "sha256_file", lambda _path: pytest.fail("read output too early")
    )
    with pytest.raises(ValueError, match="invalid SHA256"):
        verify_capsule_manifest(capsule_dir)
