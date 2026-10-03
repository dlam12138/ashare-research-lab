"""Compare exact canonical bytes of fully verified packages or ZIP deliveries."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

from ashare_research.tools import package_archive, package_verification

SCHEMA = "m2_verified_package_byte_comparison_v1"
LABELS = {"added": "新增文件", "removed": "移除文件", "changed": "内容变化", "unchanged": "相同"}
NOTES = (
    "仅比较两边完整复核后返回的规范文件字节；ZIP 编码不同不代表内容变化。",
    "文件变化不等于财务事实或历史发布版本变化，不推断原因或经济含义。",
    "需要兼容的已安装固定基线，不证明真实性、签名、历史可得性或研究资格。",
)


class ByteDiffError(Exception):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def _load(source: Path, archive: bool) -> tuple[dict[str, Any], dict[str, bytes]]:
    try:
        if archive:
            receipt, files = package_archive.load_verified_archive(source)
            return {
                "source_type": "archive",
                "archive_sha256": receipt["archive_sha256"],
                "archive_byte_count": receipt["archive_byte_count"],
                "verification": receipt["verification"],
            }, files
        verified, files = package_verification.load_verified_package(source)
        return {
            "source_type": "directory", "archive_sha256": None,
            "archive_byte_count": None, "verification": verified,
        }, files
    except (package_archive.ArchiveError, package_verification.PackageError) as error:
        raise ByteDiffError(error.code) from error


def _file_info(raw: bytes | None) -> dict[str, Any] | None:
    if raw is None:
        return None
    return {"byte_count": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def compare_packages(
    left: Path, right: Path, *, left_archive: bool = False, right_archive: bool = False
) -> dict[str, Any]:
    """Load fresh verified bytes once per side; never reread retained source files."""
    before, left_files = _load(left, left_archive)
    after, right_files = _load(right, right_archive)
    kind = before["verification"]["package_kind"]
    if kind != after["verification"]["package_kind"]:
        raise ByteDiffError("PACKAGE_KIND_MISMATCH")
    counts = dict.fromkeys(LABELS, 0)
    entries = []
    for name in sorted(left_files.keys() | right_files.keys()):
        old, new = left_files.get(name), right_files.get(name)
        state = (
            "added" if old is None else "removed" if new is None
            else "unchanged" if old == new else "changed"
        )
        counts[state] += 1
        entries.append({
            "path": name, "state": state, "before": _file_info(old), "after": _file_info(new),
        })
    return {
        "schema": SCHEMA, "status": "compared", "package_kind": kind,
        "left": before, "right": after, "states": counts, "entries": entries,
        "compared_file_count": len(entries),
        "same_content": not any(counts[state] for state in ("added", "removed", "changed")),
        "notes": list(NOTES),
    }


def render_summary(result: dict[str, Any]) -> str:
    lines = [
        f"已复核研究包文件对比：{result['package_kind']}，{result['compared_file_count']} 个文件。",
        "；".join(f"{LABELS[state]} {count}" for state, count in result["states"].items()),
    ]
    lines.extend(f"{LABELS[entry['state']]}：{entry['path']}"
                 for entry in result["entries"] if entry["state"] != "unchanged")
    lines.extend(["", *result["notes"]])
    return "\n".join(lines) + "\n"


class _Parser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise ByteDiffError("INVALID_ARGUMENTS")


def main(argv: list[str] | None = None) -> int:
    parser = _Parser(description="完整复核后比较研究目录或 ZIP 的文件内容", allow_abbrev=False)
    left = parser.add_mutually_exclusive_group(required=True)
    left.add_argument("--left", metavar="DIR")
    left.add_argument("--left-archive", metavar="ZIP")
    right = parser.add_mutually_exclusive_group(required=True)
    right.add_argument("--right", metavar="DIR")
    right.add_argument("--right-archive", metavar="ZIP")
    parser.add_argument("--json", action="store_true")
    try:
        args = parser.parse_args(argv)
        result = compare_packages(
            Path(args.left_archive if args.left_archive is not None else args.left),
            Path(args.right_archive if args.right_archive is not None else args.right),
            left_archive=args.left_archive is not None,
            right_archive=args.right_archive is not None,
        )
        text = (
            json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
            if args.json else render_summary(result)
        )
        sys.stdout.buffer.write(text.encode())
        sys.stdout.buffer.flush()
        return 0
    except SystemExit as error:
        return error.code if isinstance(error.code, int) else 2
    except Exception as error:  # noqa: BLE001 - sanitized failures, no partial stdout
        code = error.code if isinstance(error, ByteDiffError) else "UNEXPECTED_FAILURE"
        sys.stderr.buffer.write(f"error: {code}\n".encode())
        sys.stderr.buffer.flush()
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
