"""Compose public workflow and archive APIs into one verified ZIP delivery."""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path
from typing import Any

from ashare_research.tools import package_archive, research_workflow


class DeliveryError(Exception):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def deliver_workflow(request: dict[str, Any], output: Path) -> dict[str, Any]:
    """Build in owned staging and fully verify before exclusively creating ZIP.

    Late failure may retain an owned ZIP; publication is not atomic. Caller paths
    are never overwritten or cleaned up. Existing public APIs own all contents.
    """
    if output.is_symlink() or output.exists():
        raise DeliveryError("OUTPUT_PATH_EXISTS")
    if any(parent.is_symlink() for parent in output.absolute().parents):
        raise DeliveryError("OUTPUT_PATH_INVALID")
    try:
        with tempfile.TemporaryDirectory(prefix="m2-direct-delivery-") as runtime:
            staged = Path(runtime) / "workflow"
            research_workflow.export_workflow(request, staged)
            return package_archive.export_archive(staged, output)
    except (research_workflow.WorkflowError, package_archive.ArchiveError) as error:
        raise DeliveryError(error.code) from error
    except OSError as error:
        raise DeliveryError("DELIVERY_BUILD_FAILED") from error


class _Parser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise DeliveryError("INVALID_ARGUMENTS")


def main(argv: list[str] | None = None) -> int:
    parser = _Parser(description="一次生成完整复核的研究 ZIP 交付文件", allow_abbrev=False)
    parser.add_argument("--as-of", required=True, metavar="DATE")
    parser.add_argument("--output", required=True, metavar="NEW_ZIP")
    parser.add_argument("--compare-with", metavar="DATE")
    parser.add_argument("--year", action="append", type=int)
    parser.add_argument("--metric", action="append")
    parser.add_argument("--scope", default="consolidated")
    parser.add_argument("--json", action="store_true")
    try:
        args = parser.parse_args(argv)
        result = deliver_workflow(
            {
                "as_of": args.as_of,
                "compare_with": args.compare_with,
                "years": args.year,
                "metrics": args.metric,
                "scope": args.scope,
            },
            Path(args.output),
        )
        text = (
            json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
            if args.json
            else f"delivered verified workflow ZIP: {result['verified_file_count']} files\n"
            f"ZIP SHA256: {result['archive_sha256']}\n"
            "需要兼容固定基线；未证明真实性、历史可得性或研究资格。\n"
        )
        sys.stdout.buffer.write(text.encode())
        sys.stdout.buffer.flush()
        return 0
    except SystemExit as error:
        return error.code if isinstance(error.code, int) else 2
    except Exception as error:  # noqa: BLE001 - sanitized failures, no partial stdout
        code = error.code if isinstance(error, DeliveryError) else "UNEXPECTED_FAILURE"
        sys.stderr.buffer.write(f"error: {code}\n".encode())
        sys.stderr.buffer.flush()
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
