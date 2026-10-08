"""Deliver and reproduce compile-only plans from captured original hypotheses."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
import sys
from pathlib import Path
from typing import Any

from ashare_research.mechanism.contract_compiler import ContractCompilationError
from ashare_research.mechanism.hypothesis_config import HypothesisConfigError
from ashare_research.tools.research_plan import (
    MAX_INPUT_BYTES,
    PlanError,
    build_report_from_bytes,
    read_hypothesis_bytes,
    render_markdown,
)

SCHEMA = "m4_compile_only_plan_package_v1"
FILE_LIMITS = {
    "hypothesis.json": MAX_INPUT_BYTES,
    "report.json": 16_777_216,
    "report.md": 16_777_216,
    "manifest.json": 65_536,
}


def _json_bytes(value: Any) -> bytes:
    return (json.dumps(
        value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False,
    ) + "\n").encode("utf-8")


def _linked(info: os.stat_result) -> bool:
    return stat.S_ISLNK(info.st_mode) or bool(
        getattr(info, "st_file_attributes", 0) & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
    )


def _plain_root(path: Path) -> Path:
    if ".." in path.parts:
        raise PlanError("UNSAFE_PACKAGE_PATH")
    root = path.absolute()
    for candidate in (root, *root.parents):
        try:
            info = candidate.lstat()
        except FileNotFoundError:
            continue
        except OSError as error:
            raise PlanError("UNSAFE_PACKAGE_PATH") from error
        if _linked(info) or (candidate != root and not stat.S_ISDIR(info.st_mode)):
            raise PlanError("UNSAFE_PACKAGE_PATH")
    return root


def _artifacts(source: bytes) -> tuple[dict[str, bytes], dict[str, Any]]:
    report = build_report_from_bytes(source)
    payloads = {
        "hypothesis.json": source,
        "report.json": _json_bytes(report),
        "report.md": render_markdown(report).encode("utf-8"),
    }
    manifest = {
        "schema": SCHEMA,
        "status": "compiled_pre_execution",
        "source_file_sha256": report["source_file_sha256"],
        "contract_digest": report["contract"]["contract_digest"],
        "plan_digest": report["plan"]["plan_digest"],
        "files": {
            name: {"sha256": hashlib.sha256(data).hexdigest(), "size_bytes": len(data)}
            for name, data in payloads.items()
        },
        "boundary": report["boundary"],
        "notes": [
            "Hashes bind captured bytes; verification also reproduces the original compilation.",
            "Self-consistency is not a signature, independent seal, or source evidence.",
            "Compatible frozen compilers and renderer are required for exact reproduction.",
        ],
    }
    payloads["manifest.json"] = _json_bytes(manifest)
    for name, data in payloads.items():
        if len(data) > FILE_LIMITS[name]:
            raise PlanError("PACKAGE_FILE_TOO_LARGE")
    return payloads, manifest


def _read_file(path: Path, limit: int) -> bytes:
    _plain_root(path.parent)
    info = path.lstat()
    if _linked(info) or not stat.S_ISREG(info.st_mode):
        raise PlanError("UNSAFE_PACKAGE_FILE")
    if info.st_size > limit:
        raise PlanError("PACKAGE_FILE_TOO_LARGE")
    with path.open("rb") as stream:
        opened = os.fstat(stream.fileno())
        if not stat.S_ISREG(opened.st_mode) or (opened.st_dev, opened.st_ino) != (
            info.st_dev, info.st_ino,
        ):
            raise PlanError("UNSAFE_PACKAGE_FILE")
        data = stream.read(limit + 1)
    if len(data) > limit:
        raise PlanError("PACKAGE_FILE_TOO_LARGE")
    return data


def _read_package(root: Path) -> dict[str, bytes]:
    try:
        info = root.lstat()
        if _linked(info) or not stat.S_ISDIR(info.st_mode):
            raise PlanError("INVALID_PACKAGE_DIRECTORY")
        names = []
        for entry in root.iterdir():
            names.append(entry.name)
            if len(names) > len(FILE_LIMITS):
                raise PlanError("PACKAGE_MEMBERSHIP_MISMATCH")
        if set(names) != set(FILE_LIMITS):
            raise PlanError("PACKAGE_MEMBERSHIP_MISMATCH")
        return {
            name: _read_file(root / name, limit) for name, limit in FILE_LIMITS.items()
        }
    except OSError as error:
        raise PlanError("PACKAGE_READ_FAILED") from error


def _receipt(status: str, manifest: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": "m4_compile_only_plan_package_receipt_v1",
        "status": status, "file_count": len(FILE_LIMITS), "manifest": manifest,
    }


def export_package(source: Path, output: Path) -> dict[str, Any]:
    root = _plain_root(output)
    if root.exists():
        raise PlanError("PACKAGE_OUTPUT_EXISTS")
    payloads, manifest = _artifacts(read_hypothesis_bytes(source))
    _plain_root(root)
    try:
        root.mkdir()
    except FileExistsError as error:
        raise PlanError("PACKAGE_OUTPUT_EXISTS") from error
    except OSError as error:
        raise PlanError("PACKAGE_WRITE_FAILED") from error
    try:
        claimed = root.lstat()
        for name, data in payloads.items():
            current = _plain_root(root).lstat()
            if _linked(current) or not stat.S_ISDIR(current.st_mode) or (
                current.st_dev, current.st_ino,
            ) != (claimed.st_dev, claimed.st_ino):
                raise PlanError("PACKAGE_OUTPUT_CHANGED")
            with (root / name).open("xb") as stream:
                if stream.write(data) != len(data):
                    raise PlanError("PACKAGE_WRITE_FAILED")
        if _read_package(root) != payloads:
            raise PlanError("PACKAGE_REPRODUCTION_MISMATCH")
    except OSError as error:
        # Retain owned partial output for inspection; never clean a caller directory.
        raise PlanError("PACKAGE_WRITE_FAILED") from error
    return _receipt("exported_pre_execution", manifest)


def verify_package(package: Path) -> dict[str, Any]:
    captured = _read_package(_plain_root(package))
    expected, manifest = _artifacts(captured["hypothesis.json"])
    if captured != expected:
        raise PlanError("PACKAGE_REPRODUCTION_MISMATCH")
    return _receipt("verified_pre_execution", manifest)


class _Parser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise PlanError("INVALID_ARGUMENTS")


def main(argv: list[str] | None = None) -> int:
    parser = _Parser(
        description="Export or reproduce a compile-only plan package", allow_abbrev=False,
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--hypothesis", metavar="JSON")
    mode.add_argument("--verify", metavar="DIR")
    parser.add_argument("--output", metavar="NEW_DIR")
    parser.add_argument("--json", action="store_true")
    try:
        args = parser.parse_args(argv)
        if args.verify is not None:
            if not args.verify or args.output is not None:
                raise PlanError("INVALID_ARGUMENTS")
            receipt = verify_package(Path(args.verify))
        else:
            if not args.hypothesis or not args.output:
                raise PlanError("INVALID_ARGUMENTS")
            receipt = export_package(Path(args.hypothesis), Path(args.output))
        if args.json:
            text = _json_bytes(receipt)
        else:
            text = (
                "# Compile-only plan package\n\n"
                f"Status: {receipt['status']}\n\n```json\n"
                + _json_bytes(receipt["manifest"]).decode("utf-8")
                + "```\n"
            ).encode("utf-8")
        sys.stdout.buffer.write(text)
        sys.stdout.buffer.flush()
        return 0
    except SystemExit as error:
        return error.code if isinstance(error.code, int) else 2
    except Exception as error:  # noqa: BLE001 - sanitized, no partial stdout
        code = error.code if isinstance(error, (
            PlanError, HypothesisConfigError, ContractCompilationError,
        )) else "PACKAGE_OPERATION_FAILED"
        sys.stderr.buffer.write(f"error: {code}\n".encode())
        sys.stderr.buffer.flush()
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
