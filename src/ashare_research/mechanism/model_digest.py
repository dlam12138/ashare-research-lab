"""Separate deterministic pipeline and model digest construction."""

from __future__ import annotations

import json
from collections.abc import Iterable
from hashlib import sha256
from pathlib import Path


def sha256_file(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def canonical_digest(payload: dict) -> str:
    encoded = json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode()
    return sha256(encoded).hexdigest()


def source_hashes(paths: Iterable[Path]) -> dict[str, str]:
    return {str(path.as_posix()): sha256_file(path) for path in sorted(paths)}


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
    upstream_contract_identities: Iterable[str],
) -> tuple[str, dict]:
    upstream = {
        identity: sha256(identity.encode("utf-8")).hexdigest()
        for identity in sorted(upstream_contract_identities)
    }
    payload = {
        "scope": "frozen_research_contracts,model_configuration,pipeline_digest",
        "pipeline_digest": pipeline_digest,
        "contract_hashes": source_hashes(contract_paths),
        "implementation_source_hashes": source_hashes(source_paths),
        "dependency_version_contract": dependency_contract,
        "upstream_contract_identity_hashes": upstream,
    }
    return canonical_digest(payload), payload
