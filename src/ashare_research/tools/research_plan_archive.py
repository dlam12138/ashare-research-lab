"""Canonical ZIP delivery and direct reproduction of compile-only plan bytes."""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import stat
import struct
import sys
import zipfile
from pathlib import Path
from typing import Any

from ashare_research.mechanism.contract_compiler import ContractCompilationError
from ashare_research.mechanism.hypothesis_config import HypothesisConfigError
from ashare_research.tools.research_plan import PlanError
from ashare_research.tools.research_plan_package import (
    FILE_LIMITS,
    capture_verified_package,
    managed_path,
    read_regular_file,
    verify_captured_files,
)

MAX_ARCHIVE_BYTES = sum(FILE_LIMITS.values()) + 4096
MAX_CENTRAL_BYTES = 1024
STAMP = (1980, 1, 1, 0, 0, 0)
MODE = (stat.S_IFREG | 0o644) << 16


def _archive_bytes(captured: dict[str, bytes]) -> bytes:
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w", compression=zipfile.ZIP_STORED, allowZip64=False) as jar:
        for name in FILE_LIMITS:
            member = zipfile.ZipInfo(name, STAMP)
            member.create_system = 3
            member.external_attr = MODE
            jar.writestr(member, captured[name])
    data = stream.getvalue()
    if len(data) > MAX_ARCHIVE_BYTES:
        raise PlanError("ARCHIVE_TOO_LARGE")
    return data


def _capture_members(data: bytes) -> dict[str, bytes]:
    if len(data) > MAX_ARCHIVE_BYTES:
        raise PlanError("ARCHIVE_TOO_LARGE")
    if len(data) < 22:
        raise PlanError("INVALID_PLAN_ARCHIVE")
    # Bound metadata before ZipFile can allocate a record for each central entry.
    signature, disk, start_disk, count, total, size, offset, comment = struct.unpack(
        "<4s4H2LH", data[-22:],
    )
    if (
        signature != b"PK\x05\x06" or disk or start_disk or comment
        or count != len(FILE_LIMITS) or total != count
        or size > MAX_CENTRAL_BYTES or offset + size + 22 != len(data)
    ):
        raise PlanError("INVALID_PLAN_ARCHIVE")
    try:
        with zipfile.ZipFile(io.BytesIO(data), "r", allowZip64=False) as jar:
            members = jar.infolist()
            if [member.filename for member in members] != list(FILE_LIMITS):
                raise PlanError("ARCHIVE_MEMBERSHIP_MISMATCH")
            for member in members:
                if (
                    member.orig_filename != member.filename
                    or member.flag_bits or member.compress_type != zipfile.ZIP_STORED
                    or member.extra or member.comment or member.date_time != STAMP
                    or member.create_system != 3 or member.external_attr != MODE
                    or member.internal_attr or member.volume
                ):
                    raise PlanError("INVALID_PLAN_ARCHIVE")
                if (
                    member.file_size > FILE_LIMITS[member.filename]
                    or member.compress_size != member.file_size
                ):
                    raise PlanError("ARCHIVE_MEMBER_SIZE_INVALID")
            captured = {}
            for member in members:
                with jar.open(member) as stream:
                    payload = stream.read(FILE_LIMITS[member.filename] + 1)
                if len(payload) != member.file_size:
                    raise PlanError("ARCHIVE_MEMBER_SIZE_INVALID")
                captured[member.filename] = payload
    except (zipfile.BadZipFile, EOFError, ValueError, RuntimeError, OSError) as error:
        raise PlanError("INVALID_PLAN_ARCHIVE") from error
    if _archive_bytes(captured) != data:
        raise PlanError("NONCANONICAL_PLAN_ARCHIVE")
    return captured


def _receipt(status: str, data: bytes, verified: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": "m4_compile_only_plan_archive_receipt_v1",
        "status": status,
        "archive_sha256": hashlib.sha256(data).hexdigest(),
        "archive_size_bytes": len(data),
        "file_count": len(FILE_LIMITS),
        "manifest": verified["manifest"],
    }


def export_archive(package: Path, output: Path) -> dict[str, Any]:
    target = managed_path(output)
    if target.exists():
        raise PlanError("ARCHIVE_OUTPUT_EXISTS")
    captured, verified = capture_verified_package(package)
    data = _archive_bytes(captured)
    managed_path(target)
    try:
        with target.open("xb") as stream:
            if stream.write(data) != len(data):
                raise PlanError("ARCHIVE_WRITE_FAILED")
    except FileExistsError as error:
        raise PlanError("ARCHIVE_OUTPUT_EXISTS") from error
    except OSError as error:
        # Keep owned partial output for inspection; never remove caller files.
        raise PlanError("ARCHIVE_WRITE_FAILED") from error
    try:
        if read_regular_file(target, MAX_ARCHIVE_BYTES) != data:
            raise PlanError("ARCHIVE_REPRODUCTION_MISMATCH")
    except OSError as error:
        raise PlanError("ARCHIVE_READ_FAILED") from error
    return _receipt("exported_pre_execution", data, verified)


def verify_archive(archive: Path) -> dict[str, Any]:
    try:
        data = read_regular_file(managed_path(archive), MAX_ARCHIVE_BYTES)
    except OSError as error:
        raise PlanError("ARCHIVE_READ_FAILED") from error
    verified = verify_captured_files(_capture_members(data))
    return _receipt("verified_pre_execution", data, verified)


class _Parser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise PlanError("INVALID_ARGUMENTS")


def main(argv: list[str] | None = None) -> int:
    parser = _Parser(description="Deliver or reproduce a canonical plan ZIP", allow_abbrev=False)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--package", metavar="DIR")
    mode.add_argument("--verify", metavar="ZIP")
    parser.add_argument("--output", metavar="NEW_ZIP")
    parser.add_argument("--json", action="store_true")
    try:
        args = parser.parse_args(argv)
        if args.verify is not None:
            if not args.verify or args.output is not None:
                raise PlanError("INVALID_ARGUMENTS")
            receipt = verify_archive(Path(args.verify))
        else:
            if not args.package or not args.output:
                raise PlanError("INVALID_ARGUMENTS")
            receipt = export_archive(Path(args.package), Path(args.output))
        text = json.dumps(receipt, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False)
        if not args.json:
            text = "# Compile-only plan archive\n\n```json\n" + text + "\n```"
        sys.stdout.buffer.write((text + "\n").encode("utf-8"))
        sys.stdout.buffer.flush()
        return 0
    except SystemExit as error:
        return error.code if isinstance(error.code, int) else 2
    except Exception as error:  # noqa: BLE001 - sanitized, no partial stdout
        code = error.code if isinstance(error, (
            PlanError, HypothesisConfigError, ContractCompilationError,
        )) else "ARCHIVE_OPERATION_FAILED"
        sys.stderr.buffer.write(f"error: {code}\n".encode())
        sys.stderr.buffer.flush()
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
