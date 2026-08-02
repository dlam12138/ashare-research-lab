"""Platform-neutral Git-blob checks for protected text fixtures."""

from __future__ import annotations

import hashlib
from pathlib import Path

CRLF_LEGACY_BLOBS = {
    "acceptance/fixtures/official_facts/601857.SH/supplemental/2020_opening_roe_roa_denominators_from_2021.json",
    "acceptance/fixtures/official_facts/601857.SH/supplemental/2021_roe_roa_denominators.json",
    "acceptance/fixtures/official_facts/601857.SH/supplemental/2022_roe_roa_denominators.json",
    "acceptance/fixtures/official_facts/601857.SH/supplemental/2023_roe_roa_denominators.json",
    "acceptance/fixtures/restatements/601857.SH/roe_roa_denominators_2021_reviewed_by_2022.json",
    "acceptance/fixtures/restatements/601857.SH/roe_roa_denominators_2022_reviewed_by_2023.json",
    "acceptance/fixtures/restatements/601857.SH/roe_roa_denominators_2023_reviewed_by_2024.json",
}


def canonical_worktree_blob(path: Path) -> str:
    """Hash text using each protected fixture's historical line-ending contract."""

    content = path.read_bytes()
    relative = path.as_posix()
    if relative in CRLF_LEGACY_BLOBS and b"\r\n" not in content:
        content = content.replace(b"\n", b"\r\n")
    header = f"blob {len(content)}\0".encode()
    return hashlib.sha1(header + content).hexdigest()  # noqa: S324
