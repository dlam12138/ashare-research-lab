"""Read original report sections from fully verified deliveries, without restoration."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from ashare_research.tools import (
    evidence_audit,
    package_archive,
    package_verification,
    research_review,
    session_compare,
)

SCHEMA = "m2_verified_delivered_research_view_v1"
RENDERERS = {
    "review": research_review.render_markdown,
    "audit": evidence_audit.render_markdown,
    "compare": session_compare.render_markdown,
}


class ReadError(Exception):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def read_report(source: Path, section: str, *, archive: bool = False) -> dict[str, Any]:
    """Select only fixed report paths from the complete fresh canonical byte map."""
    if section not in RENDERERS:
        raise ReadError("INVALID_SECTION")
    try:
        if archive:
            receipt, files = package_archive.load_verified_archive(source)
            verification = receipt["verification"]
        else:
            verification, files = package_verification.load_verified_package(source)
            receipt = None
    except (package_archive.ArchiveError, package_verification.PackageError) as error:
        raise ReadError(error.code) from error
    kind = verification["package_kind"]
    if kind not in ("workflow", section):
        raise ReadError("SECTION_PACKAGE_MISMATCH")
    name = f"{section}/{section}.json" if kind == "workflow" else f"{section}.json"
    if name not in files:
        raise ReadError("SECTION_NOT_PRESENT")
    return {
        "schema": SCHEMA,
        "status": "read",
        "section": section,
        "package_kind": kind,
        "verification": verification,
        "archive_receipt": receipt,
        "report": json.loads(files[name]),
    }


class _Parser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise ReadError("INVALID_ARGUMENTS")


def main(argv: list[str] | None = None) -> int:
    parser = _Parser(description="直接阅读完整复核交付包中的指标和证据", allow_abbrev=False)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--package", metavar="DIR")
    source.add_argument("--archive", metavar="ZIP")
    parser.add_argument("--section", required=True, choices=tuple(RENDERERS))
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--metric", action="append", metavar="ID")
    parser.add_argument("--year", action="append", type=int, metavar="YEAR")
    parser.add_argument("--fact", action="append", metavar="ID")
    parser.add_argument("--gaps-only", action="store_true", help="仅显示原台账缺口，限 audit")
    parser.add_argument(
        "--missing-only", action="store_true", help="仅显示原值为 null 的指标，限 review",
    )
    try:
        args = parser.parse_args(argv)
        focused = (args.metric is not None or args.year is not None
                   or args.fact is not None or args.gaps_only or args.missing_only)
        if focused:
            if args.section == "audit" and not args.missing_only:
                from ashare_research.tools import audit_focus as focus

                focus.validate_selectors(args.metric, args.year, args.fact)
            elif args.section == "review" and args.fact is None and not args.gaps_only:
                from ashare_research.tools import review_focus as focus

                focus.validate_selectors(args.metric, args.year)
            else:
                raise ReadError("INVALID_ARGUMENTS")
        result = read_report(
            Path(args.archive if args.archive is not None else args.package),
            args.section, archive=args.archive is not None,
        )
        renderer = RENDERERS[args.section]
        if focused:
            options = ({"facts": args.fact, "gaps_only": args.gaps_only}
                       if args.section == "audit" else {"missing_only": args.missing_only})
            result = focus.build_report(result, metrics=args.metric, years=args.year, **options)
            renderer = focus.render_markdown
        text = (
            json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
            if args.json else renderer(result if focused else result["report"])
        )
        sys.stdout.buffer.write(text.encode("utf-8"))
        sys.stdout.buffer.flush()
        return 0
    except SystemExit as error:
        return error.code if isinstance(error.code, int) else 2
    except Exception as error:  # noqa: BLE001 - sanitized errors, no partial output
        code = error.code if isinstance(error, ReadError) else "UNEXPECTED_FAILURE"
        sys.stderr.buffer.write(f"error: {code}\n".encode())
        sys.stderr.buffer.flush()
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
