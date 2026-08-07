"""M2 Stage 2K.1R4B artifact manifest verifier.

A real verifier: unlike the earlier CLI behavior (which only listed
``artifact_logical_path`` values from the capsule and returned ``pass``), this
module actually recomputes each file's SHA-256 and byte size and compares them
against the manifest.

The current Stage 2K.1R4A manifest declares:

    sha256 over LF-normalized content
    byte_size is LF-normalized length

So the verifier normalizes line endings (CRLF -> LF, lone CR -> LF) *before*
computing both the SHA-256 and the byte_size, using the unified
``normalize_lf(bytes) -> bytes`` helper. No UTF-8 decode/re-encode is performed;
all other bytes are preserved verbatim. SHA-256 and byte_size are always computed
over the same normalized bytes -- never one raw and one normalized.

The manifest itself is not placed in its own ``files`` array (that would make
hashing recursive); if it is, the verifier warns. When a manifest identity is
needed it is computed separately as ``manifest_digest`` = SHA-256 of the canonical
JSON excluding the ``manifest_digest`` field.

Validation rules (1..10):
  1. manifest must be a JSON object
  2. schema must be in the explicit allowed list
  3. files must be an array
  4. every entry must have path, sha256, byte_size
  5. path must be a repository-relative logical path
  6. absolute paths are forbidden
  7. ``..`` path traversal is forbidden
  8. duplicate paths are forbidden
  9. the file must exist and be a regular file
  10. the hash is computed over LF-normalized content

The verifier must be able to detect: missing files, content tampering, byte_size
tampering, hash tampering, duplicate paths, absolute paths, parent traversal, and
unsupported schema.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ashare_research.scoring import content_digest as cd

_CANONICAL_SEP = (",", ":")

# Explicit allow-list of manifest schema versions this verifier understands.
ALLOWED_MANIFEST_SCHEMAS = frozenset(
    {
        "m2_stage2k1r4a_artifact_manifest_v1",
        "m2_stage2k1r4b_artifact_manifest_v1",
        "m2_stage2k1r4c_artifact_manifest_v1",
        "m2_stage2k1r4c1_artifact_manifest_v2",
        "m2_stage2k1r4e1_artifact_manifest_v2",
        "m2_stage2k1r4e2_artifact_manifest",
        "m2_stage2k1r4e3_artifact_manifest",
    }
)

REQUIRED_FILE_FIELDS = ("path", "sha256", "byte_size")

#: v2 entry field carrying the digest algorithm (ContentDigest contract).
V2_ALGORITHM_FIELD = "digest_algorithm"

#: v2 schemas: the digest is computed with the registered ContentDigest
#: algorithm instead of the v1 LF-normalized default.
V2_SCHEMAS = frozenset(
    {
        "m2_stage2k1r4c1_artifact_manifest_v2",
        "m2_stage2k1r4e1_artifact_manifest_v2",
        "m2_stage2k1r4e2_artifact_manifest",
        "m2_stage2k1r4e3_artifact_manifest",
    }
)


_KNOWN_ALGORITHMS = frozenset(cd._KNOWN_ALGORITHMS)


def normalize_lf(data: bytes) -> bytes:
    """Normalize line endings to LF without decoding/re-encoding UTF-8.

    - ``\\r\\n`` -> ``\\n``
    - lone ``\\r`` -> ``\\n``
    - all other bytes are preserved verbatim
    """
    return data.replace(b"\r\n", b"\n").replace(b"\r", b"\n")


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical(payload: Any) -> bytes:
    return json.dumps(
        payload, sort_keys=True, ensure_ascii=False, separators=_CANONICAL_SEP
    ).encode("utf-8")


def manifest_digest(manifest: dict[str, Any]) -> str:
    """Digest of the manifest structure itself, excluding the ``manifest_digest``
    field (avoids recursive hashing). Canonical JSON, sorted keys, compact."""
    payload = {k: v for k, v in manifest.items() if k != "manifest_digest"}
    return _sha256_bytes(_canonical(payload))


@dataclass
class ArtifactManifestVerification:
    """Result of verifying one artifact manifest against the repository."""

    status: str
    schema: str | None
    manifest_path: str
    verified_file_count: int
    missing_files: list[str] = field(default_factory=list)
    hash_mismatches: list[str] = field(default_factory=list)
    size_mismatches: list[str] = field(default_factory=list)
    duplicate_paths: list[str] = field(default_factory=list)
    invalid_paths: list[str] = field(default_factory=list)
    unexpected_contract_errors: list[str] = field(default_factory=list)
    verified_entries: list[dict[str, Any]] = field(default_factory=list)
    manifest_digest: str | None = None
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "schema": self.schema,
            "manifest_path": self.manifest_path,
            "verified_file_count": self.verified_file_count,
            "missing_files": self.missing_files,
            "hash_mismatches": self.hash_mismatches,
            "size_mismatches": self.size_mismatches,
            "duplicate_paths": self.duplicate_paths,
            "invalid_paths": self.invalid_paths,
            "unexpected_contract_errors": self.unexpected_contract_errors,
            "verified_entries": self.verified_entries,
            "manifest_digest": self.manifest_digest,
            "errors": self.errors,
            "warnings": self.warnings,
        }


def _is_valid_relative_logical_path(path: str) -> bool:
    """A valid manifest path is a forward-slash repository-relative logical path:
    not absolute, not rooted, no ``..`` traversal, no drive letter."""
    if not path or path.startswith("/") or path.startswith("\\"):
        return False
    if ".." in path.split("/"):
        return False
    p = Path(path)
    if p.is_absolute():
        return False
    # reject Windows drive letters (e.g. "C:/x")
    return not (len(path) >= 2 and path[1] == ":")


def _classify_entry(entry: Any, index: int, *, is_v2: bool) -> tuple[str | None, list[str]]:
    """Return (path, errors) for one manifest file entry. A non-dict or missing
    required field yields a contract error with no usable path. For v2 schemas
    the ``digest_algorithm`` field is required and must be a known algorithm."""
    if not isinstance(entry, dict):
        return None, [f"files[{index}] is not an object"]
    missing = [f for f in REQUIRED_FILE_FIELDS if f not in entry]
    if missing:
        return None, [f"files[{index}] missing required field(s): {', '.join(missing)}"]
    path = entry["path"]
    if not isinstance(path, str):
        return None, [f"files[{index}] path is not a string"]
    sha = entry["sha256"]
    size = entry["byte_size"]
    errs = []
    if not isinstance(sha, str) or len(sha) != 64:
        errs.append(f"files[{index}] sha256 must be a 64-char hex string")
    if not isinstance(size, int) or size < 0:
        errs.append(f"files[{index}] byte_size must be a non-negative integer")
    if not _is_valid_relative_logical_path(path):
        errs.append(f"files[{index}] path is not a valid relative logical path: {path!r}")
    if is_v2:
        algorithm = entry.get(V2_ALGORITHM_FIELD)
        if not isinstance(algorithm, str) or algorithm not in _KNOWN_ALGORITHMS:
            errs.append(
                f"files[{index}] missing or unknown {V2_ALGORITHM_FIELD}: {algorithm!r}"
            )
    return path, errs


def verify_artifact_manifest(
    manifest_path: Path,
    *,
    repository_root: Path,
) -> ArtifactManifestVerification:
    """Verify ``manifest_path`` against ``repository_root``.

    Returns a :class:`ArtifactManifestVerification`. ``status`` is ``"pass"`` only
    when every file verifies and there are no contract errors.
    """
    manifest_path = Path(manifest_path)

    # --- load + structure checks -----------------------------------------
    try:
        raw = manifest_path.read_bytes()
    except OSError as exc:  # pragma: no cover - defensive
        v = ArtifactManifestVerification(
            status="fail",
            schema=None,
            manifest_path=str(manifest_path),
            verified_file_count=0,
            unexpected_contract_errors=[f"manifest not readable: {exc}"],
        )
        v.errors = list(v.unexpected_contract_errors)
        return v

    try:
        manifest = json.loads(raw.decode("utf-8"))
    except (ValueError, UnicodeDecodeError) as exc:
        v = ArtifactManifestVerification(
            status="fail",
            schema=None,
            manifest_path=str(manifest_path),
            verified_file_count=0,
            unexpected_contract_errors=[f"manifest is not valid JSON: {exc}"],
        )
        v.errors = list(v.unexpected_contract_errors)
        return v

    if not isinstance(manifest, dict):
        v = ArtifactManifestVerification(
            status="fail",
            schema=None,
            manifest_path=str(manifest_path),
            verified_file_count=0,
            unexpected_contract_errors=["manifest must be a JSON object"],
        )
        v.errors = list(v.unexpected_contract_errors)
        return v

    schema = manifest.get("schema")
    contract_errors: list[str] = []
    if not isinstance(schema, str) or schema not in ALLOWED_MANIFEST_SCHEMAS:
        contract_errors.append(f"unsupported manifest schema: {schema!r}")
    is_v2 = isinstance(schema, str) and schema in V2_SCHEMAS

    files = manifest.get("files")
    if not isinstance(files, list):
        contract_errors.append("manifest 'files' must be an array")
        files = []

    errors: list[str] = list(contract_errors)

    # --- classify each entry ---------------------------------------------
    paths: list[str] = []
    entry_errors: list[tuple[str, list[str]]] = []
    for i, entry in enumerate(files):
        path, errs = _classify_entry(entry, i, is_v2=is_v2)
        if path is not None:
            paths.append(path)
        if errs:
            entry_errors.append((path, errs))

    # duplicate detection (order-preserving)
    seen: set[str] = set()
    duplicates: list[str] = []
    for path in paths:
        if path in seen and path not in duplicates:
            duplicates.append(path)
        seen.add(path)
    for dup in duplicates:
        errors.append(f"duplicate path: {dup}")

    # manifest self-inclusion is a contract violation (warning)
    manifest_abs = manifest_path.resolve()
    warnings: list[str] = []
    try:
        manifest_rel = manifest_abs.relative_to(repository_root.resolve())
        manifest_rel_str = manifest_rel.as_posix()
    except ValueError:
        manifest_rel_str = None
    if manifest_rel_str in seen:
        warnings.append(
            f"manifest lists itself in files array ({manifest_rel_str}); "
            "manifest_digest is computed separately and the self-file is not hashed"
        )

    # --- verify each unique file -----------------------------------------
    verified_entries: list[dict[str, Any]] = []
    missing_files: list[str] = []
    hash_mismatches: list[str] = []
    size_mismatches: list[str] = []
    invalid_paths: list[str] = []
    for i, entry in enumerate(files):
        path, errs = _classify_entry(entry, i, is_v2=is_v2)
        if errs:
            errors.extend(errs)
            if path is not None:
                invalid_paths.append(path)
            continue
        if path in duplicates:
            continue  # duplicate file is already reported; do not double-hash
        if not _is_valid_relative_logical_path(path):
            invalid_paths.append(path)
            errors.append(f"invalid relative logical path: {path!r}")
            continue
        target = (repository_root / path).resolve()
        try:
            target.relative_to(repository_root.resolve())
        except ValueError:
            invalid_paths.append(path)
            errors.append(f"path escapes repository root: {path!r}")
            continue
        if not target.is_file():
            missing_files.append(path)
            errors.append(f"missing file: {path}")
            continue
        if is_v2:
            digest = cd.digest_file(
                target, algorithm=entry[V2_ALGORITHM_FIELD]
            )
            actual_hash = digest.sha256
            actual_size = digest.byte_size
        else:
            data = target.read_bytes()
            norm = normalize_lf(data)
            actual_hash = _sha256_bytes(norm)
            actual_size = len(norm)
        entry_ok = True
        if actual_hash != entry["sha256"]:
            hash_mismatches.append(path)
            errors.append(f"hash mismatch: {path}")
            entry_ok = False
        if actual_size != entry["byte_size"]:
            size_mismatches.append(path)
            errors.append(f"byte_size mismatch: {path}")
            entry_ok = False
        if entry_ok:
            verified_entries.append(
                {"path": path, "sha256": actual_hash, "byte_size": actual_size}
            )

    # --- assemble result --------------------------------------------------
    status = "pass" if not errors else "fail"
    v = ArtifactManifestVerification(
        status=status,
        schema=schema if isinstance(schema, str) else None,
        manifest_path=str(manifest_path),
        verified_file_count=len(verified_entries),
        missing_files=missing_files,
        hash_mismatches=hash_mismatches,
        size_mismatches=size_mismatches,
        duplicate_paths=duplicates,
        invalid_paths=invalid_paths,
        unexpected_contract_errors=contract_errors,
        verified_entries=verified_entries,
        errors=errors,
        warnings=warnings,
    )
    v.manifest_digest = manifest_digest(manifest)
    return v
