"""Native ten-member preparation ZIPs with direct in-memory reproduction."""

from __future__ import annotations

import hashlib
import io
import stat
import struct
import zipfile
from pathlib import Path
from typing import Any

from ashare_research.tools import preparation_package as package
from ashare_research.tools.synthetic_prepare import PrepareError

SCHEMA = "m4_synthetic_preparation_archive_v1"
FIXED_DATE = (1980, 1, 1, 0, 0, 0)
CENTRAL_BYTES = sum(46 + len(name.encode("utf-8")) for name in package.NAMES)
LOCAL_BYTES = sum(30 + len(name.encode("utf-8")) for name in package.NAMES)
MAX_ARCHIVE_BYTES = package.MAX_TOTAL_BYTES + CENTRAL_BYTES + LOCAL_BYTES + 22


def _encode(files: dict[str, bytes]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_STORED) as archive:
        for name, raw in sorted(files.items()):
            entry = zipfile.ZipInfo(name, FIXED_DATE)
            entry.create_system = 3
            entry.external_attr = (stat.S_IFREG | 0o644) << 16
            archive.writestr(entry, raw)
    return buffer.getvalue()


def _preflight(raw: bytes) -> None:
    if len(raw) > MAX_ARCHIVE_BYTES:
        raise PrepareError("PREPARATION_ARCHIVE_LIMIT_EXCEEDED")
    if len(raw) < 22 or not raw.startswith(b"PK\x03\x04"):
        raise PrepareError("PREPARATION_ARCHIVE_INVALID")
    signature, disk, start_disk, disk_count, count, size, offset, comment = struct.unpack(
        "<4s4H2LH", raw[-22:],
    )
    # Bound directory allocation before ZipFile creates member objects.
    if (signature != b"PK\x05\x06" or disk != 0 or start_disk != 0
            or disk_count != len(package.NAMES) or count != len(package.NAMES)
            or comment != 0 or size != CENTRAL_BYTES or offset + size != len(raw) - 22):
        raise PrepareError("PREPARATION_ARCHIVE_LAYOUT_INVALID")


def _decode_verified(raw: bytes) -> dict[str, Any]:
    _preflight(raw)
    try:
        with zipfile.ZipFile(io.BytesIO(raw), "r") as archive:
            entries = archive.infolist()
            if (len(entries) != len(package.NAMES)
                    or {entry.filename for entry in entries} != package.NAMES
                    or min(entry.header_offset for entry in entries) != 0):
                raise PrepareError("PREPARATION_ARCHIVE_LAYOUT_INVALID")
            total = 0
            for entry in entries:
                if (entry.filename != entry.orig_filename or entry.is_dir()
                        or stat.S_IFMT(entry.external_attr >> 16) != stat.S_IFREG
                        or entry.external_attr & 0x10 or entry.extra or entry.comment):
                    raise PrepareError("PREPARATION_ARCHIVE_LAYOUT_INVALID")
                if entry.flag_bits or entry.compress_type != zipfile.ZIP_STORED:
                    raise PrepareError("PREPARATION_ARCHIVE_UNSUPPORTED")
                if (entry.file_size > package._limit(entry.filename)
                        or entry.compress_size != entry.file_size):
                    raise PrepareError("PREPARATION_ARCHIVE_LIMIT_EXCEEDED")
                total += entry.file_size
                if total > package.MAX_TOTAL_BYTES:
                    raise PrepareError("PREPARATION_ARCHIVE_LIMIT_EXCEEDED")
            files = {}
            for entry in entries:
                with archive.open(entry) as stream:
                    payload = stream.read(entry.file_size + 1)
                if len(payload) != entry.file_size:
                    raise PrepareError("PREPARATION_ARCHIVE_INVALID")
                files[entry.filename] = payload
        if _encode(files) != raw:
            raise PrepareError("PREPARATION_ARCHIVE_LAYOUT_INVALID")
    except (ValueError, RuntimeError, NotImplementedError, zipfile.BadZipFile) as error:
        raise PrepareError("PREPARATION_ARCHIVE_INVALID") from error
    return package.verify_package_files(files)


def _receipt(raw: bytes, verified: dict[str, Any], status: str) -> dict[str, Any]:
    return {
        "schema": SCHEMA, "status": status,
        "archive_sha256": hashlib.sha256(raw).hexdigest(), "archive_byte_count": len(raw),
        "independent_seal_verified": False, "verification": verified,
    }


def export_archive(source: Path, output: Path) -> dict[str, Any]:
    try:
        package._check_path(output)
        if output.exists():
            raise PrepareError("OUTPUT_PATH_EXISTS")
        files = package.read_package_files(source)
        if output.resolve().is_relative_to(source.resolve()):
            raise PrepareError("OUTPUT_INSIDE_SOURCE_PREPARATION")
        return export_package_files(files, output)
    except FileExistsError as error:
        raise PrepareError("OUTPUT_PATH_EXISTS") from error
    except OSError as error:
        raise PrepareError("PREPARATION_ARCHIVE_WRITE_FAILED") from error


def export_from_plan(
    plan: Path, inputs: Path, output: Path, *, plan_archive: bool = False,
) -> dict[str, Any]:
    """Build and deliver a preparation ZIP without intermediate filesystem artifacts."""
    try:
        package._check_path(output)
        if output.exists():
            raise PrepareError("OUTPUT_PATH_EXISTS")
        if not plan_archive and output.resolve().is_relative_to(plan.resolve()):
            raise PrepareError("OUTPUT_INSIDE_SOURCE_PLAN")
        files = package.build_package_files(plan, inputs, plan_archive=plan_archive)
        return export_package_files(files, output)
    except FileExistsError as error:
        raise PrepareError("OUTPUT_PATH_EXISTS") from error
    except OSError as error:
        raise PrepareError("PREPARATION_ARCHIVE_WRITE_FAILED") from error


def export_package_files(files: dict[str, bytes], output: Path) -> dict[str, Any]:
    """Verify the complete bounded snapshot before encoding and exclusive output."""
    try:
        package._check_path(output)
        if output.exists():
            raise PrepareError("OUTPUT_PATH_EXISTS")
        package.verify_package_files(files)
        raw = _encode(files)
        verified = _decode_verified(raw)
        receipt = _receipt(raw, verified, "archived_preparation")
        with output.open("xb") as stream:
            stream.write(raw)
        return receipt
    except FileExistsError as error:
        raise PrepareError("OUTPUT_PATH_EXISTS") from error
    except OSError as error:
        raise PrepareError("PREPARATION_ARCHIVE_WRITE_FAILED") from error


def verify_archive(source: Path) -> dict[str, Any]:
    try:
        package._check_path(source)
        if not stat.S_ISREG(source.lstat().st_mode):
            raise PrepareError("PREPARATION_ARCHIVE_SOURCE_INVALID")
        with source.open("rb") as stream:
            raw = stream.read(MAX_ARCHIVE_BYTES + 1)
        return _receipt(raw, _decode_verified(raw), "verified_preparation_archive")
    except OSError as error:
        raise PrepareError("PREPARATION_ARCHIVE_READ_FAILED") from error


def render_markdown(receipt: dict[str, Any]) -> str:
    return "\n".join([
        "# 合成准备 ZIP", "", f"状态：`{receipt['status']}`。",
        f"ZIP SHA256：`{receipt['archive_sha256']}`。",
        f"ZIP 字节数：{receipt['archive_byte_count']}。", "",
        package.render_markdown(receipt["verification"]),
    ])
