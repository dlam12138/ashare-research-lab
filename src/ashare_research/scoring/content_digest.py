"""Shared content-digest contract for M2 Stage 2K.1R4C.1.

Centralizes every artifact content digest used in the score-input identity
chain so that the same bytes are always hashed the same way, regardless of
which module (lineage, capsule, artifact manifest, validator) computes it.

Two algorithms, both fail-closed:

- ``sha256_lf_normalized_bytes_v1`` — for **text artifacts** (JSON, CSV, MD,
  YAML, ...). Line endings are normalized (CRLF -> LF, lone CR -> LF) *before*
  hashing, and the byte_size is the normalized length. No UTF-8 decode/re-encode
  is performed; all other bytes are preserved verbatim. This makes the digest
  of a text artifact identical whether the working tree carries LF or CRLF
  (e.g. a generated report that a Windows tool rewrote with CRLF while git's
  blob / CI clean clone is LF).
- ``sha256_raw_bytes_v1`` — for **binary artifacts** (Parquet, PDF, DuckDB,
  ZIP, images, ...). The exact file bytes are hashed with no normalization;
  byte_size is the raw length. Line-ending normalization must never be applied
  to binary data.

``digest_file`` requires the caller to pass the algorithm explicitly (a
mandatory keyword argument) and raises a contract error for any unknown
algorithm. There is no implicit default, so a future artifact cannot silently
fall back to the wrong hash.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

# ---------------------------------------------------------------------------
# Algorithms
# ---------------------------------------------------------------------------

ALGORITHM_LF_NORMALIZED_BYTES_V1 = "sha256_lf_normalized_bytes_v1"
ALGORITHM_RAW_BYTES_V1 = "sha256_raw_bytes_v1"

#: Media classes that map to a digest algorithm. ``text`` artifacts are
#: line-ending normalized; ``binary`` artifacts are hashed raw.
MEDIA_CLASS_TEXT = "text"
MEDIA_CLASS_BINARY = "binary"

_ALGORITHM_BY_MEDIA_CLASS = {
    MEDIA_CLASS_TEXT: ALGORITHM_LF_NORMALIZED_BYTES_V1,
    MEDIA_CLASS_BINARY: ALGORITHM_RAW_BYTES_V1,
}

_KNOWN_ALGORITHMS = frozenset(_ALGORITHM_BY_MEDIA_CLASS.values())


class ContentDigestError(ValueError):
    """Raised for an unknown digest algorithm or an unsupported media class."""


# ---------------------------------------------------------------------------
# Content digest value
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ContentDigest:
    """A content digest: algorithm, SHA-256 hex, and byte size.

    ``byte_size`` is always the length of the exact bytes that were hashed
    (normalized length for the LF-normalized algorithm, raw length for the raw
    algorithm) -- never a mix.
    """

    algorithm: str
    sha256: str
    byte_size: int

    def to_dict(self) -> dict[str, object]:
        return {
            "algorithm": self.algorithm,
            "sha256": self.sha256,
            "byte_size": self.byte_size,
        }


# ---------------------------------------------------------------------------
# Normalization
# ---------------------------------------------------------------------------


def normalize_lf(data: bytes) -> bytes:
    """Normalize line endings to LF without decoding/re-encoding UTF-8.

    - ``\\r\\n`` -> ``\\n``
    - lone ``\\r`` -> ``\\n``
    - all other bytes are preserved verbatim
    """
    return data.replace(b"\r\n", b"\n").replace(b"\r", b"\n")


# ---------------------------------------------------------------------------
# Digest functions
# ---------------------------------------------------------------------------


def _sha256_bytes(data: bytes) -> str:
    import hashlib

    return hashlib.sha256(data).hexdigest()


def digest_text_artifact(data: bytes) -> ContentDigest:
    """Digest text artifact bytes with LF normalization."""
    norm = normalize_lf(data)
    return ContentDigest(
        algorithm=ALGORITHM_LF_NORMALIZED_BYTES_V1,
        sha256=_sha256_bytes(norm),
        byte_size=len(norm),
    )


def digest_binary_artifact(data: bytes) -> ContentDigest:
    """Digest binary artifact bytes with no normalization."""
    return ContentDigest(
        algorithm=ALGORITHM_RAW_BYTES_V1,
        sha256=_sha256_bytes(data),
        byte_size=len(data),
    )


def digest_for_media_class(data: bytes, media_class: str) -> ContentDigest:
    """Digest bytes according to a media class (``text`` or ``binary``).

    Fail-closed: an unknown media class raises :class:`ContentDigestError`.
    """
    algorithm = _ALGORITHM_BY_MEDIA_CLASS.get(media_class)
    if algorithm is None:
        raise ContentDigestError(f"unknown media class: {media_class!r}")
    if algorithm == ALGORITHM_LF_NORMALIZED_BYTES_V1:
        return digest_text_artifact(data)
    return digest_binary_artifact(data)


def digest_file(path: Path, *, algorithm: str) -> ContentDigest:
    """Digest ``path`` with an explicitly passed algorithm.

    The algorithm is mandatory (no default) and must be a known algorithm;
    anything else raises :class:`ContentDigestError` (fail-closed).
    """
    if algorithm not in _KNOWN_ALGORITHMS:
        raise ContentDigestError(f"unknown digest algorithm: {algorithm!r}")
    data = Path(path).read_bytes()
    if algorithm == ALGORITHM_LF_NORMALIZED_BYTES_V1:
        return digest_text_artifact(data)
    return digest_binary_artifact(data)
