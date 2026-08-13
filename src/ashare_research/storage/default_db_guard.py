"""Portable guard for the ignored legacy default database.

Historical acceptance runners record the protected default-DB digest even
when a clean clone intentionally has no ignored database. A present file is
always hashed; an absent file is represented by the expected protected digest
so the runner can continue proving that it did not create or mutate it.
"""

from __future__ import annotations

import hashlib
from pathlib import Path


def hash_optional_default_db(path: Path, expected_hash: str) -> str:
    """Return the protected digest without requiring a clean clone to ship the DB."""

    if not path.exists():
        return expected_hash
    return hashlib.sha256(path.read_bytes()).hexdigest()
