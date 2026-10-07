"""Deterministic native four-member ZIPs; verification never extracts or executes."""

from __future__ import annotations

import hashlib
import io
import stat
import struct
import zipfile
from pathlib import Path
from typing import Any

from ashare_research.tools import research_plan_package as package
from ashare_research.tools.research_plan import MAX_INPUT_BYTES, PlanError, read_hypothesis_bytes

SCHEMA = "m4_compile_only_plan_archive_v1"
MAX_TOTAL_BYTES = 4 * package.MAX_ARTIFACT_BYTES
MAX_ARCHIVE_BYTES = MAX_TOTAL_BYTES + 1024
CENTRAL_BYTES = sum(46 + len(name.encode("utf-8")) for name in package.NAMES)
FIXED_DATE = (1980, 1, 1, 0, 0, 0)


def _encode(files: dict[str, bytes]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_STORED) as archive:
        for name, payload in sorted(files.items()):
            entry = zipfile.ZipInfo(name, FIXED_DATE)
            entry.create_system = 3
            entry.external_attr = (stat.S_IFREG | 0o644) << 16
            archive.writestr(entry, payload)
    return buffer.getvalue()


def _preflight(raw: bytes) -> None:
    """Bound central-directory parsing before ZipFile allocates member objects.

    Native ZIPs have exactly four names, no extras/comments, no ZIP64, no prefix
    or trailing bytes. These compact transport rules are not authenticity seals.
    """
    if len(raw) > MAX_ARCHIVE_BYTES:
        raise PlanError("PLAN_ARCHIVE_LIMIT_EXCEEDED")
    if len(raw) < 22 or not raw.startswith(b"PK\x03\x04"):
        raise PlanError("PLAN_ARCHIVE_INVALID")
    signature, disk, start_disk, disk_count, count, size, offset, comment = struct.unpack(
        "<4s4H2LH", raw[-22:],
    )
    if (signature != b"PK\x05\x06" or disk != 0 or start_disk != 0
            or disk_count != 4 or count != 4 or comment != 0 or size != CENTRAL_BYTES
            or offset + size != len(raw) - 22):
        raise PlanError("PLAN_ARCHIVE_LAYOUT_INVALID")


def _decode_verified(raw: bytes) -> dict[str, Any]:
    _preflight(raw)
    try:
        with zipfile.ZipFile(io.BytesIO(raw), "r") as archive:
            entries = archive.infolist()
            names = [entry.filename for entry in entries]
            if len(entries) != 4 or set(names) != package.NAMES:
                raise PlanError("PLAN_ARCHIVE_LAYOUT_INVALID")
            total = 0
            for entry in entries:
                mode = stat.S_IFMT(entry.external_attr >> 16)
                if (entry.filename != entry.orig_filename or entry.is_dir()
                        or entry.external_attr & 0x10 or mode not in (0, stat.S_IFREG)
                        or entry.extra or entry.comment):
                    raise PlanError("PLAN_ARCHIVE_LAYOUT_INVALID")
                if entry.flag_bits & ~0x808 or entry.compress_type != zipfile.ZIP_STORED:
                    raise PlanError("PLAN_ARCHIVE_UNSUPPORTED")
                limit = (MAX_INPUT_BYTES if entry.filename == "hypothesis.json"
                         else package.MAX_ARTIFACT_BYTES)
                if (not 0 <= entry.file_size <= limit
                        or entry.compress_size != entry.file_size):
                    raise PlanError("PLAN_ARCHIVE_LIMIT_EXCEEDED")
                total += entry.file_size
                if total > MAX_TOTAL_BYTES:
                    raise PlanError("PLAN_ARCHIVE_LIMIT_EXCEEDED")
            files = {}
            for entry in entries:
                with archive.open(entry) as stream:
                    payload = stream.read(entry.file_size + 1)
                if len(payload) != entry.file_size:
                    raise PlanError("PLAN_ARCHIVE_INVALID")
                files[entry.filename] = payload
        return package.verify_package_files(files)
    except (ValueError, RuntimeError, NotImplementedError, zipfile.BadZipFile) as error:
        raise PlanError("PLAN_ARCHIVE_INVALID") from error


def _receipt(raw: bytes, verified: dict[str, Any], status: str) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": status,
        "archive_sha256": hashlib.sha256(raw).hexdigest(),
        "archive_byte_count": len(raw),
        "independent_seal_verified": False,
        "verification": verified,
    }


def export_archive(source: Path, output: Path) -> dict[str, Any]:
    try:
        package._check_path(output)
        if output.exists():
            raise PlanError("OUTPUT_PATH_EXISTS")
        files, _, _ = package._files(read_hypothesis_bytes(source))
        raw = _encode(files)
        verified = _decode_verified(raw)
        receipt = _receipt(raw, verified, "archived")
        with output.open("xb") as stream:
            stream.write(raw)
        return receipt
    except FileExistsError as error:
        raise PlanError("OUTPUT_PATH_EXISTS") from error
    except OSError as error:
        raise PlanError("OUTPUT_WRITE_FAILED") from error


def verify_archive(source: Path) -> dict[str, Any]:
    try:
        package._check_path(source)
        if not stat.S_ISREG(source.lstat().st_mode):
            raise PlanError("PLAN_ARCHIVE_SOURCE_INVALID")
        with source.open("rb") as stream:
            raw = stream.read(MAX_ARCHIVE_BYTES + 1)
        verified = _decode_verified(raw)
        return _receipt(raw, verified, "verified_archive")
    except OSError as error:
        raise PlanError("PLAN_ARCHIVE_READ_FAILED") from error
