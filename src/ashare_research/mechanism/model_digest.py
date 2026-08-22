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

DIGEST_ALGORITHM = "M3_REPOSITORY_RELATIVE_DIGEST_V2"


def sha256_file(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def canonical_digest(payload: dict) -> str:
    encoded = json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode()
    return sha256(encoded).hexdigest()


def repository_relative_key(path: Path) -> str:
    """Return a resolved repository-relative POSIX key, fail-closed."""

    root = repository_root().resolve()
    resolved = path.resolve()
    try:
        relative = resolved.relative_to(root)
    except ValueError as exc:
        raise UpstreamBindingError("DIGEST_PATH_OUTSIDE_REPOSITORY") from exc
    return relative.as_posix()


def source_hashes(paths: Iterable[Path]) -> dict[str, str]:
    entries: list[tuple[str, Path]] = []
    for path in paths:
        resolved = path.resolve()
        key = repository_relative_key(resolved)
        if not resolved.is_file():
            raise UpstreamBindingError("DIGEST_SOURCE_PATH_INVALID")
        entries.append((key, resolved))
    keys = [key for key, _ in entries]
    if len(keys) != len(set(keys)):
        raise UpstreamBindingError("DIGEST_SOURCE_PATH_COLLISION")
    return {
        key: sha256_file(resolved)
        for key, resolved in sorted(entries, key=lambda item: item[0])
    }


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
        try:
            repository_relative_key(path)
        except UpstreamBindingError:
            raise UpstreamBindingError("MODEL_DIGEST_UPSTREAM_BINDING_FAILURE") from None
        if not path.is_file():
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
        "digest_algorithm": DIGEST_ALGORITHM,
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
        "digest_algorithm": DIGEST_ALGORITHM,
        "scope": "frozen_research_contracts,model_configuration,pipeline_digest",
        "pipeline_digest": pipeline_digest,
        "contract_hashes": source_hashes(contract_paths),
        "implementation_source_hashes": source_hashes(source_paths),
        "dependency_version_contract": dependency_contract,
        "upstream_contract_identity_hashes": upstream,
        "upstream_inventory_path": repository_relative_key(upstream_inventory_path),
        "upstream_inventory_sha256": sha256_file(upstream_inventory_path),
    }
    return canonical_digest(payload), payload
