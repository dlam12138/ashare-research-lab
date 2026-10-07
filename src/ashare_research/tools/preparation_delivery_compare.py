"""Compare fully reproduced saved preparation directories or native ZIPs."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

from ashare_research.mechanism.contract_compiler import ContractCompilationError
from ashare_research.mechanism.datasets import AdapterError
from ashare_research.mechanism.hypothesis_config import HypothesisConfigError
from ashare_research.mechanism.planning.matrix import MatrixError
from ashare_research.tools import (
    preparation_archive,
    preparation_compare,
    preparation_diagnostics,
    preparation_package,
)
from ashare_research.tools.research_plan import PlanError
from ashare_research.tools.synthetic_prepare import PrepareError


def _verified_report(source: Path, archive: bool) -> dict[str, Any]:
    if archive:
        return preparation_archive.verify_archive(source)["verification"]["report"]
    return preparation_package.verify_package(source)["report"]


def build_report(
    left: Path, right: Path, *, left_archive: bool = False, right_archive: bool = False,
) -> dict[str, Any]:
    before = _verified_report(left, left_archive)
    # Reuse only identical caller paths and modes; aliases keep their own path gates.
    after = (before if (left, left_archive) == (right, right_archive)
             else _verified_report(right, right_archive))
    return preparation_compare.build_report_from_reports(before, after)


def render_markdown(report: dict[str, Any]) -> str:
    return preparation_compare.render_markdown(
        report, source_legend="left 为修改前的准备交付包；right 为修改后的准备交付包。",
    )


def render_summary_markdown(summary: dict[str, Any]) -> str:
    return preparation_compare.render_summary_markdown(
        summary,
        source_legend="left 为修改前的准备交付包；right 为修改后的准备交付包。",
    )


class _Parser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise PrepareError("INVALID_ARGUMENTS")


def main(argv: list[str] | None = None) -> int:
    parser = _Parser(description="完整复核并对比两份合成准备交付包", allow_abbrev=False)
    left = parser.add_mutually_exclusive_group(required=True)
    left.add_argument("--left", metavar="DIR")
    left.add_argument("--left-archive", metavar="ZIP")
    right = parser.add_mutually_exclusive_group(required=True)
    right.add_argument("--right", metavar="DIR")
    right.add_argument("--right-archive", metavar="ZIP")
    parser.add_argument("--summary", action="store_true")
    parser.add_argument("--role", action="append", default=[], metavar="ID")
    parser.add_argument("--json", action="store_true")
    try:
        args = parser.parse_args(argv)
        preparation_diagnostics.validate_options(args.summary, args.role, False)
        report = build_report(
            Path(args.left if args.left is not None else args.left_archive),
            Path(args.right if args.right is not None else args.right_archive),
            left_archive=args.left_archive is not None,
            right_archive=args.right_archive is not None,
        )
        if args.summary:
            summary = preparation_compare.build_summary(report, roles=args.role)
            text = (preparation_compare._json(summary) + "\n" if args.json
                    else render_summary_markdown(summary))
        else:
            text = (preparation_compare._json(report) + "\n" if args.json
                    else render_markdown(report))
        sys.stdout.buffer.write(text.encode("utf-8"))
        sys.stdout.buffer.flush()
        return 0
    except SystemExit as error:
        return error.code if isinstance(error.code, int) else 2
    except Exception as error:  # noqa: BLE001 - sanitized, no partial stdout
        code = error.code if isinstance(error, (
            PrepareError, PlanError, AdapterError, MatrixError,
            HypothesisConfigError, ContractCompilationError,
        )) else "PREPARATION_DELIVERY_COMPARISON_FAILED"
        sys.stderr.buffer.write(f"error: {code}\n".encode())
        sys.stderr.buffer.flush()
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
