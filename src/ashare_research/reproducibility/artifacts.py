"""Deterministic run artifact manifests and checksum verification."""

from __future__ import annotations

import hashlib
import json
import platform
import subprocess
from pathlib import Path
from typing import Any

ARTIFACT_MANIFEST = "artifact_manifest.json"
CHECKSUMS = "checksums.sha256"
REPRO_REPORT = "reproducibility_report.json"
METADATA_FILES = {ARTIFACT_MANIFEST, CHECKSUMS, REPRO_REPORT}
_LOGICAL_MANIFEST_FIELDS = (
    "contract",
    "mode",
    "deterministic_timestamp_policy",
    "network_used",
    "default_db_mutated",
    "inputs",
    "outputs",
    "evidence_gap_count",
    "rule007_eligibility_count",
    "score_eligible",
    "forbidden_feature_checks",
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, default=str) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def _logical_manifest_payload(manifest: dict[str, Any]) -> dict[str, Any]:
    """Return the canonical run identity without run/environment/path noise."""

    outputs = [
        {
            "logical_artifact": item["logical_artifact"],
            "sha256": item["sha256"],
            "size_bytes": item["size_bytes"],
        }
        for item in manifest.get("outputs", [])
    ]
    payload = {
        key: manifest.get(key)
        for key in _LOGICAL_MANIFEST_FIELDS
        if key != "outputs"
    }
    payload["outputs"] = sorted(outputs, key=lambda item: item["logical_artifact"])
    return payload


def logical_artifact_digest(manifest: dict[str, Any]) -> str:
    """Hash logical inputs/outputs, excluding run_id and output/environment paths."""

    return hashlib.sha256(
        json.dumps(
            _logical_manifest_payload(manifest),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


def _code_commit() -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=False
        )
        return result.stdout.strip() if result.returncode == 0 else "unknown"
    except OSError:
        return "unknown"


def _relative_files(run_dir: Path) -> list[Path]:
    return sorted(
        (
            path.relative_to(run_dir)
            for path in run_dir.rglob("*")
            if path.is_file() and path.name not in METADATA_FILES
        ),
        key=lambda path: path.as_posix(),
    )


def finalize_artifacts(
    run_dir: Path | str,
    *,
    run_id: str,
    mode: str,
    inputs: list[dict[str, Any]],
    evidence_gap_count: int = 0,
    rule007_eligible_count: int = 0,
    score_eligible: bool = False,
) -> dict[str, Any]:
    """Write a complete v2 artifact contract with relative paths only."""

    root = Path(run_dir)
    outputs = []
    for relative in _relative_files(root):
        path = root / relative
        outputs.append(
            {
                "logical_artifact": relative.as_posix(),
                "relative_path": relative.as_posix(),
                "sha256": sha256_file(path),
                "size_bytes": path.stat().st_size,
            }
        )
    artifact_manifest = {
        "contract": "artifact_manifest_v2",
        "run_id": run_id,
        "mode": mode,
        "code_commit": _code_commit(),
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "deterministic_timestamp_policy": (
            "fixed-run-contract-time; timestamps are not used in hashes"
        ),
        "network_used": False,
        "default_db_mutated": False,
        "inputs": inputs,
        "outputs": outputs,
        "evidence_gap_count": evidence_gap_count,
        "rule007_eligibility_count": rule007_eligible_count,
        "score_eligible": score_eligible,
        "forbidden_feature_checks": {
            "roic": "not_started",
            "scoring": "not_started",
            "target_price": "not_started",
            "recommendation": "not_started",
            "automatic_trading": "not_started",
            "market_mechanism": "not_started",
        },
    }
    artifact_manifest["logical_digest"] = logical_artifact_digest(artifact_manifest)
    write_json(root / ARTIFACT_MANIFEST, artifact_manifest)
    (root / CHECKSUMS).write_text(
        "".join(f"{item['sha256']}  {item['relative_path']}\n" for item in outputs),
        encoding="utf-8",
    )
    write_json(
        root / REPRO_REPORT,
        {
            "contract": "reproducibility_report_v2",
            "run_id": run_id,
            "mode": mode,
            "artifact_manifest_verified": True,
            "network_used": False,
            "default_db_mutated": False,
            "byte_identity_scope": "same Python/platform and identical logical inputs",
            "generated_at_policy": "deterministic contract time; not an input",
        },
    )
    return artifact_manifest


def verify_artifacts(run_dir: Path | str) -> dict[str, Any]:
    root = Path(run_dir)
    manifest_path = root / ARTIFACT_MANIFEST
    if not manifest_path.is_file():
        raise FileNotFoundError(f"artifact manifest missing: {manifest_path.name}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("contract") != "artifact_manifest_v2":
        raise ValueError("unsupported artifact manifest contract")
    if any(
        Path(item["relative_path"]).is_absolute() or ".." in Path(item["relative_path"]).parts
        for item in manifest.get("outputs", [])
    ):
        raise ValueError("artifact manifest contains an absolute output path")
    expected = {item["relative_path"]: item for item in manifest.get("outputs", [])}
    actual = {path.as_posix(): root / path for path in _relative_files(root)}
    missing = sorted(set(expected) - set(actual))
    extra = sorted(set(actual) - set(expected))
    changed = []
    for relative, item in expected.items():
        if relative in actual and sha256_file(actual[relative]) != item["sha256"]:
            changed.append(relative)
    if missing or extra or changed:
        raise ValueError(
            "artifact integrity failure: "
            f"missing={missing}, extra={extra}, changed={changed}"
        )
    checksums = root / CHECKSUMS
    expected_checksums = "".join(
        f"{expected[key]['sha256']}  {key}\n" for key in sorted(expected)
    )
    if not checksums.is_file() or checksums.read_text(encoding="utf-8") != expected_checksums:
        raise ValueError("checksums.sha256 does not match artifact manifest")
    report = json.loads((root / REPRO_REPORT).read_text(encoding="utf-8"))
    if report.get("run_id") != manifest.get("run_id") or not report.get(
        "artifact_manifest_verified"
    ):
        raise ValueError("reproducibility report does not match artifact manifest")
    expected_logical_digest = logical_artifact_digest(manifest)
    if manifest.get("logical_digest") != expected_logical_digest:
        raise ValueError("artifact manifest logical digest mismatch")
    serialized = json.dumps(manifest, ensure_ascii=False, sort_keys=True)
    if "D:\\" in serialized or "D:/" in serialized or "\\\\" in serialized:
        raise ValueError("artifact manifest contains a private or absolute path")
    return {
        "status": "pass",
        "run_id": manifest["run_id"],
        "mode": manifest["mode"],
        "output_count": len(expected),
        "sha256": hashlib.sha256(
            json.dumps(manifest, ensure_ascii=False, sort_keys=True).encode()
        ).hexdigest(),
        "logical_digest": expected_logical_digest,
    }


def compare_artifact_runs(left_dir: Path | str, right_dir: Path | str) -> dict[str, Any]:
    """Compare two independently written runs and fail closed on any diff."""

    left = Path(left_dir)
    right = Path(right_dir)
    left_verification = verify_artifacts(left)
    right_verification = verify_artifacts(right)
    left_manifest = json.loads((left / ARTIFACT_MANIFEST).read_text(encoding="utf-8"))
    right_manifest = json.loads((right / ARTIFACT_MANIFEST).read_text(encoding="utf-8"))
    left_report = json.loads((left / REPRO_REPORT).read_text(encoding="utf-8"))
    right_report = json.loads((right / REPRO_REPORT).read_text(encoding="utf-8"))
    differences: list[str] = []
    if _logical_manifest_payload(left_manifest) != _logical_manifest_payload(right_manifest):
        differences.append("logical_artifact_manifest_diff")
    if left_verification["logical_digest"] != right_verification["logical_digest"]:
        differences.append("logical_digest_diff")
    left_checksums = (left / CHECKSUMS).read_text(encoding="utf-8")
    right_checksums = (right / CHECKSUMS).read_text(encoding="utf-8")
    if left_checksums != right_checksums:
        differences.append("checksums_diff")
    left_report.pop("run_id", None)
    right_report.pop("run_id", None)
    if left_report != right_report:
        differences.append("reproducibility_report_diff")
    return {
        "status": "fail" if differences else "pass",
        "differences": differences,
        "left": {
            "run_id": left_manifest.get("run_id"),
            "logical_digest": left_verification["logical_digest"],
            "output_count": left_verification["output_count"],
        },
        "right": {
            "run_id": right_manifest.get("run_id"),
            "logical_digest": right_verification["logical_digest"],
            "output_count": right_verification["output_count"],
        },
    }
