"""Deterministic ZIP delivery, verification and restoration of research packages."""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import re
import stat
import sys
import tempfile
import zipfile
import zlib
from pathlib import Path
from typing import Any

from ashare_research.tools import package_verification

SCHEMA = "m2_verified_package_archive_delivery_v1"
MAX_MEMBERS = 256
MAX_MEMBER_BYTES = 32 * 1024 * 1024
MAX_TOTAL_BYTES = 128 * 1024 * 1024
MAX_ARCHIVE_BYTES = 129 * 1024 * 1024
MAX_NAME_BYTES = 512
MAX_PATH_PARTS = 32
FIXED_DATE = (1980, 1, 1, 0, 0, 0)
_DEVICES = {"CON", "PRN", "AUX", "NUL"} | {
    prefix + str(number) for prefix in ("COM", "LPT") for number in range(1, 10)
}


class ArchiveError(Exception):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def _check_output(output: Path) -> None:
    if output.is_symlink() or output.exists():
        raise ArchiveError("OUTPUT_PATH_EXISTS")
    if any(parent.is_symlink() for parent in output.absolute().parents):
        raise ArchiveError("OUTPUT_PATH_INVALID")


def _check_members(entries: list[zipfile.ZipInfo]) -> None:
    if not entries or len(entries) > MAX_MEMBERS:
        raise ArchiveError("ARCHIVE_LIMIT_EXCEEDED")
    seen: set[str] = set()
    spelling: dict[str, str] = {}
    total = 0
    for entry in entries:
        name = entry.filename
        if len(name.encode("utf-8")) > MAX_NAME_BYTES or name.count("/") >= MAX_PATH_PARTS:
            raise ArchiveError("ARCHIVE_LIMIT_EXCEEDED")
        if name != entry.orig_filename or not re.fullmatch(r"[A-Za-z0-9_./-]+", name):
            raise ArchiveError("ARCHIVE_LAYOUT_INVALID")
        parts = name.split("/")
        if any(
            part in ("", ".", "..")
            or part.endswith((".", " "))
            or part.split(".", 1)[0].upper() in _DEVICES
            for part in parts
        ):
            raise ArchiveError("ARCHIVE_LAYOUT_INVALID")
        if name.casefold() in seen:
            raise ArchiveError("ARCHIVE_LAYOUT_INVALID")
        seen.add(name.casefold())
        for depth in range(1, len(parts) + 1):
            prefix = "/".join(parts[:depth])
            previous = spelling.setdefault(prefix.casefold(), prefix)
            if previous != prefix:
                raise ArchiveError("ARCHIVE_LAYOUT_INVALID")
        mode = stat.S_IFMT(entry.external_attr >> 16)
        if entry.is_dir() or entry.external_attr & 0x10 or mode not in (0, stat.S_IFREG):
            raise ArchiveError("ARCHIVE_LAYOUT_INVALID")
        if entry.flag_bits & 1 or entry.compress_type not in (
            zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED
        ):
            raise ArchiveError("ARCHIVE_UNSUPPORTED")
        if not 0 <= entry.file_size <= MAX_MEMBER_BYTES:
            raise ArchiveError("ARCHIVE_LIMIT_EXCEEDED")
        total += entry.file_size
        if total > MAX_TOTAL_BYTES:
            raise ArchiveError("ARCHIVE_LIMIT_EXCEEDED")
    for name in seen:
        parts = name.split("/")
        if any("/".join(parts[:depth]) in seen for depth in range(1, len(parts))):
            raise ArchiveError("ARCHIVE_LAYOUT_INVALID")
    if "manifest.json" not in seen:
        raise ArchiveError("ARCHIVE_LAYOUT_INVALID")


def _encode(files: dict[str, bytes]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_STORED) as archive:
        for name, raw in sorted(files.items()):
            entry = zipfile.ZipInfo(name, FIXED_DATE)
            entry.create_system = 3
            entry.external_attr = (stat.S_IFREG | 0o644) << 16
            entry.compress_type = zipfile.ZIP_STORED
            archive.writestr(entry, raw)
        _check_members(archive.infolist())
    result = buffer.getvalue()
    if len(result) > MAX_ARCHIVE_BYTES:
        raise ArchiveError("ARCHIVE_LIMIT_EXCEEDED")
    return result


def _receipt(raw: bytes, verified: dict[str, Any], status: str) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": status,
        "archive_sha256": hashlib.sha256(raw).hexdigest(),
        "archive_byte_count": len(raw),
        "package_kind": verified["package_kind"],
        "verified_file_count": verified["verified_file_count"],
        "package_manifest_sha256": verified["package_manifest_sha256"],
        "canonical_verified_bytes_used": True,
        "verification": verified,
    }


def export_archive(directory: Path, output: Path) -> dict[str, Any]:
    """Verify once, archive canonical bytes, then exclusively create the output file."""
    _check_output(output)
    if output.resolve().is_relative_to(directory.resolve()):
        raise ArchiveError("OUTPUT_PATH_INVALID")
    try:
        verified, files = package_verification.load_verified_package(directory)
        raw = _encode(files)
    except package_verification.PackageError as error:
        raise ArchiveError(error.code) from error
    _check_output(output)
    try:
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open("xb") as stream:
            stream.write(raw)
    except FileExistsError as error:
        raise ArchiveError("OUTPUT_PATH_EXISTS") from error
    except OSError as error:
        raise ArchiveError("OUTPUT_WRITE_FAILED") from error
    return _receipt(raw, verified, "archived")


def _decode_verified(raw: bytes) -> tuple[dict[str, Any], dict[str, bytes]]:
    """Confine decoding to an owned temporary root, then verify the whole package."""
    try:
        with zipfile.ZipFile(io.BytesIO(raw), "r") as archive:
            entries = archive.infolist()
            _check_members(entries)
            with tempfile.TemporaryDirectory(prefix="m2-package-archive-") as runtime:
                root = Path(runtime)
                for entry in entries:
                    with archive.open(entry) as stream:
                        payload = stream.read(min(entry.file_size, MAX_MEMBER_BYTES) + 1)
                    if len(payload) != entry.file_size:
                        raise ArchiveError("ARCHIVE_INVALID")
                    path = root / entry.filename
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_bytes(payload)
                return package_verification.load_verified_package(root)
    except package_verification.PackageError as error:
        raise ArchiveError(error.code) from error
    except (
        OSError, ValueError, RuntimeError, NotImplementedError, zipfile.BadZipFile, zlib.error
    ) as error:
        raise ArchiveError("ARCHIVE_INVALID") from error


def _load_verified_archive(
    source: Path,
) -> tuple[bytes, dict[str, Any], dict[str, bytes]]:
    """Read one bounded snapshot and share complete decoding across both modes."""
    if source.is_symlink() or not source.is_file():
        raise ArchiveError("ARCHIVE_SOURCE_INVALID")
    try:
        with source.open("rb") as stream:
            raw = stream.read(MAX_ARCHIVE_BYTES + 1)
    except OSError as error:
        raise ArchiveError("ARCHIVE_SOURCE_INVALID") from error
    if len(raw) > MAX_ARCHIVE_BYTES:
        raise ArchiveError("ARCHIVE_LIMIT_EXCEEDED")
    verified, files = _decode_verified(raw)
    return raw, verified, files


def load_verified_archive(source: Path) -> tuple[dict[str, Any], dict[str, bytes]]:
    """Freshly verify a ZIP and return its receipt and exact canonical byte map."""
    raw, verified, files = _load_verified_archive(source)
    return _receipt(raw, verified, "verified"), files


def verify_archive(source: Path) -> dict[str, Any]:
    """Keep the existing metadata-only receipt and complete verification behavior."""
    return load_verified_archive(source)[0]


def restore_archive(source: Path, output: Path) -> dict[str, Any]:
    """Decode/verify before creating destination, and publish only canonical bytes.

    Late output failure retains owned partial output. Neither file nor directory
    publication is claimed atomic, and caller paths are never cleaned up.
    """
    _check_output(output)
    raw, verified, files = _load_verified_archive(source)
    _check_output(output)
    try:
        output.mkdir(parents=True, exist_ok=False)
    except FileExistsError as error:
        raise ArchiveError("OUTPUT_PATH_EXISTS") from error
    except OSError as error:
        raise ArchiveError("OUTPUT_WRITE_FAILED") from error
    try:
        for name, payload in sorted(files.items()):
            path = output / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(payload)
    except OSError as error:
        raise ArchiveError("OUTPUT_WRITE_FAILED") from error
    return _receipt(raw, verified, "restored")


class _Parser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise ArchiveError("INVALID_ARGUMENTS")


def main(argv: list[str] | None = None) -> int:
    parser = _Parser(description="研究包 ZIP 交付、完整复核或恢复", allow_abbrev=False)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--package", metavar="DIR")
    mode.add_argument("--restore", metavar="ZIP")
    mode.add_argument("--verify", metavar="ZIP")
    parser.add_argument("--output", metavar="NEW_PATH")
    parser.add_argument("--json", action="store_true")
    try:
        args = parser.parse_args(argv)
        if args.verify is not None:
            if args.output is not None:
                raise ArchiveError("INVALID_ARGUMENTS")
            result = verify_archive(Path(args.verify))
        else:
            if args.output is None:
                raise ArchiveError("INVALID_ARGUMENTS")
            result = (
                export_archive(Path(args.package), Path(args.output))
                if args.package is not None
                else restore_archive(Path(args.restore), Path(args.output))
            )
        text = (
            json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
            if args.json
            else f"{result['status']}: {result['package_kind']}, "
            f"{result['verified_file_count']} files\n"
            f"ZIP SHA256: {result['archive_sha256']}\n"
            "需要兼容固定基线；未证明真实性、历史可得性或研究资格。\n"
        )
        sys.stdout.buffer.write(text.encode())
        sys.stdout.buffer.flush()
        return 0
    except SystemExit as error:
        return error.code if isinstance(error.code, int) else 2
    except Exception as error:  # noqa: BLE001 - sanitized failures, no partial stdout
        code = error.code if isinstance(error, ArchiveError) else "UNEXPECTED_FAILURE"
        sys.stderr.buffer.write(f"error: {code}\n".encode())
        sys.stderr.buffer.flush()
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
