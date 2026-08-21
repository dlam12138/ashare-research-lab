"""Separate deterministic pipeline and model digest construction."""

from __future__ import annotations

import json
from collections.abc import Iterable
from hashlib import sha256
from pathlib import Path

from ashare_research.mechanism.analysis_contracts import (
    EXPECTED_EFFECTIVE_IDS,
    UpstreamBindingError,
    repository_root,
)


def sha256_file(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def canonical_digest(payload: dict) -> str:
    encoded = json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode()
    return sha256(encoded).hexdigest()


def source_hashes(paths: Iterable[Path]) -> dict[str, str]:
    root = repository_root().resolve()
    result: dict[str, str] = {}
    for path in sorted(paths):
        resolved = path.resolve()
        try:
            key = resolved.relative_to(root).as_posix()
        except ValueError:
            key = resolved.as_posix()
        result[key] = sha256_file(resolved)
    return result


def verify_upstream_inventory(inventory_path: Path) -> dict:
    """Verify canonical upstream metadata and exact bytes; never use identity-only fallback."""

    try:
        inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise UpstreamBindingError("MODEL_DIGEST_UPSTREAM_BINDING_FAILURE") from exc
    if inventory.get("status") != "LOCKED_TO_CANONICAL_M3_BYTES":
        raise UpstreamBindingError("MODEL_DIGEST_UPSTREAM_BINDING_FAILURE")
    root = repository_root()
    bindings = {entry.get("role"): entry for entry in inventory.get("bindings", [])}
    for role, expected_id in EXPECTED_EFFECTIVE_IDS.items():
        entry = bindings.get(role)
        if not entry or entry.get("contract_id") != expected_id:
            raise UpstreamBindingError("MODEL_DIGEST_UPSTREAM_BINDING_FAILURE")
        if entry.get("effective_status", "").startswith("EFFECTIVE") is False:
            raise UpstreamBindingError("MODEL_DIGEST_UPSTREAM_BINDING_FAILURE")
        path = (root / entry["path"]).resolve()
        if root.resolve() not in path.parents or not path.is_file():
            raise UpstreamBindingError("MODEL_DIGEST_UPSTREAM_BINDING_FAILURE")
        actual = sha256_file(path)
        if actual != entry.get("sha256"):
            raise UpstreamBindingError("MODEL_DIGEST_UPSTREAM_BINDING_FAILURE")
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise UpstreamBindingError("MODEL_DIGEST_UPSTREAM_BINDING_FAILURE") from exc
        if payload.get("schema_version") != entry.get("version"):
            raise UpstreamBindingError("MODEL_DIGEST_UPSTREAM_BINDING_FAILURE")
    return inventory


def build_pipeline_digest(source_paths: Iterable[Path]) -> tuple[str, dict]:
    payload = {
        "scope": (
            "input_validation,join_order,crash,design_matrix,bootstrap,"
            "robustness,serialization"
        ),
        "implementation_source_hashes": source_hashes(source_paths),
    }
    return canonical_digest(payload), payload


def build_model_digest(
    *,
    pipeline_digest: str,
    contract_paths: Iterable[Path],
    source_paths: Iterable[Path],
    dependency_contract: dict,
    upstream_contract_identities: Iterable[str] | None = None,
    upstream_inventory_path: Path | None = None,
) -> tuple[str, dict]:
    if upstream_inventory_path is None:
        raise UpstreamBindingError("MODEL_DIGEST_UPSTREAM_BINDING_FAILURE")
    inventory = verify_upstream_inventory(upstream_inventory_path)
    upstream = {
        entry["contract_id"]: entry["sha256"]
        for entry in inventory["bindings"]
        if entry["role"] in inventory["effective_roles"]
    }
    if (
        upstream_contract_identities is not None
        and sorted(upstream_contract_identities) != sorted(upstream)
    ):
        # The old declared-identity API is accepted only as an exact consistency check.
        raise UpstreamBindingError("MODEL_DIGEST_UPSTREAM_BINDING_FAILURE")
    payload = {
        "scope": "frozen_research_contracts,model_configuration,pipeline_digest",
        "pipeline_digest": pipeline_digest,
        "contract_hashes": source_hashes(contract_paths),
        "implementation_source_hashes": source_hashes(source_paths),
        "dependency_version_contract": dependency_contract,
        "upstream_contract_identity_hashes": upstream,
        "upstream_inventory_path": str(upstream_inventory_path.as_posix()),
        "upstream_inventory_sha256": sha256_file(upstream_inventory_path),
    }
    return canonical_digest(payload), payload
