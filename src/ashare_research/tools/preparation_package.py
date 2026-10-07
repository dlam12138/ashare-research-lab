"""Deliver and reproduce synthetic preparation from bounded original byte snapshots."""

from __future__ import annotations

import argparse
import hashlib
import json
import stat
import sys
from pathlib import Path
from typing import Any

from ashare_research.mechanism.contract_compiler import ContractCompilationError
from ashare_research.mechanism.datasets import AdapterError
from ashare_research.mechanism.hypothesis_config import HypothesisConfigError
from ashare_research.mechanism.planning.matrix import MatrixError
from ashare_research.tools import preparation_diagnostics, research_plan_package, synthetic_prepare
from ashare_research.tools.research_plan import PlanError
from ashare_research.tools.synthetic_prepare import PrepareError

SCHEMA = "m4_synthetic_preparation_package_v1"
MAX_SOURCE_BYTES = synthetic_prepare.MAX_INPUT_BYTES
MAX_ARTIFACT_BYTES = 16 * MAX_SOURCE_BYTES
MAX_TOTAL_BYTES = 64 * MAX_SOURCE_BYTES
PLAN_NAMES = {name: f"plan-{name}" for name in research_plan_package.NAMES}
NAMES = frozenset({
    *PLAN_NAMES.values(), "inputs.json", "preparation.json", "preparation.md",
    "diagnostics.json", "diagnostics.md", "manifest.json",
})


def _json_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False)
            + "\n").encode("utf-8")


def _check_path(path: Path) -> None:
    path = path.absolute()
    for candidate in (path, *path.parents):
        try:
            info = candidate.lstat()
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
            raise PrepareError("LINKED_PREPARATION_PACKAGE_PATH")


def _limit(name: str) -> int:
    return MAX_SOURCE_BYTES if name in ("hypothesis.json", "plan-hypothesis.json", "inputs.json") \
        else MAX_ARTIFACT_BYTES


def _read_files(directory: Path, names: frozenset[str]) -> dict[str, bytes]:
    try:
        _check_path(directory)
        if not directory.is_dir():
            raise PrepareError("INVALID_PREPARATION_PACKAGE")
        entries = list(directory.iterdir())
        if {entry.name for entry in entries} != names:
            raise PrepareError("INVALID_PREPARATION_PACKAGE_FILES")
        files = {}
        total = 0
        for entry in sorted(entries):
            _check_path(entry)
            if not stat.S_ISREG(entry.lstat().st_mode):
                raise PrepareError("INVALID_PREPARATION_PACKAGE_FILES")
            with entry.open("rb") as stream:
                raw = stream.read(min(_limit(entry.name), MAX_TOTAL_BYTES - total) + 1)
            total += len(raw)
            if len(raw) > _limit(entry.name) or total > MAX_TOTAL_BYTES:
                raise PrepareError("PREPARATION_PACKAGE_LIMIT_EXCEEDED")
            files[entry.name] = raw
        return files
    except OSError as error:
        raise PrepareError("PREPARATION_PACKAGE_READ_FAILED") from error


def _files(
    plan_files: dict[str, bytes], inputs: bytes, *, verified: dict[str, Any] | None = None,
) -> tuple[dict[str, bytes], dict[str, Any], dict[str, Any]]:
    if verified is None:
        verified = research_plan_package.verify_package_files(plan_files)["report"]
    report = synthetic_prepare.build_report_from_bytes(verified, inputs)
    summary = preparation_diagnostics.build_summary(report, roles=[], gaps_only=False)
    files = {PLAN_NAMES[name]: raw for name, raw in plan_files.items()}
    files.update({
        "inputs.json": inputs, "preparation.json": _json_bytes(report),
        "preparation.md": synthetic_prepare.render_markdown(report).encode("utf-8"),
        "diagnostics.json": _json_bytes(summary),
        "diagnostics.md": preparation_diagnostics.render_markdown(summary).encode("utf-8"),
    })
    manifest = {
        "schema": SCHEMA, "integrity_inventory_only": True,
        "independent_seal_verified": False,
        "files": [
            {"path": name, "byte_count": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}
            for name, raw in sorted(files.items())
        ],
        "boundary": dict(report["boundary"]),
        "notes": [
            "此清单及复算只验证保存内容的一致性，不证明真实来源、历史封存或研究授权。",
            "复核使用当前兼容编译器与适配器；质量拒绝也可作为原诊断交付。",
        ],
    }
    files["manifest.json"] = _json_bytes(manifest)
    if (any(len(raw) > _limit(name) for name, raw in files.items())
            or sum(map(len, files.values())) > MAX_TOTAL_BYTES):
        raise PrepareError("PREPARATION_PACKAGE_LIMIT_EXCEEDED")
    return files, manifest, report


def _read_plan_files(plan: Path, *, archive: bool) -> dict[str, bytes]:
    if archive:
        from ashare_research.tools import research_plan_archive

        return research_plan_archive.read_archive_files(plan)
    return _read_files(plan, research_plan_package.NAMES)


def build_package_files(
    plan: Path, inputs: Path, *, plan_archive: bool = False,
) -> dict[str, bytes]:
    """Capture plan and inputs once; reproduce the original preparation artifacts."""
    plan_files = _read_plan_files(plan, archive=plan_archive)
    verified = research_plan_package.verify_package_files(plan_files)["report"]
    files, _, _ = _files(
        plan_files, synthetic_prepare.read_input_bytes(inputs), verified=verified,
    )
    return files


def export_package(
    plan: Path, inputs: Path, output: Path, *, plan_archive: bool = False,
) -> dict[str, Any]:
    try:
        _check_path(output)
        if output.exists():
            raise PrepareError("OUTPUT_PATH_EXISTS")
        plan_files = _read_plan_files(plan, archive=plan_archive)
        if not plan_archive and output.resolve().is_relative_to(plan.resolve()):
            raise PrepareError("OUTPUT_INSIDE_SOURCE_PLAN")
        # Plan consistency fails before reading inputs; captured files are never re-read.
        verified = research_plan_package.verify_package_files(plan_files)["report"]
        files, manifest, _ = _files(
            plan_files, synthetic_prepare.read_input_bytes(inputs), verified=verified,
        )
        output.mkdir(exist_ok=False)
        for name, raw in sorted(files.items()):
            with (output / name).open("xb") as stream:
                stream.write(raw)
        return {"schema": SCHEMA, "status": "exported_preparation", "manifest": manifest}
    except FileExistsError as error:
        raise PrepareError("OUTPUT_PATH_EXISTS") from error
    except OSError as error:
        raise PrepareError("PREPARATION_PACKAGE_WRITE_FAILED") from error


def verify_package(directory: Path) -> dict[str, Any]:
    return verify_package_files(_read_files(directory, NAMES))


def read_package_files(directory: Path) -> dict[str, bytes]:
    """Return a once-read snapshot only after complete original reproduction."""
    files = _read_files(directory, NAMES)
    verify_package_files(files)
    return files


def verify_package_files(files: dict[str, bytes]) -> dict[str, Any]:
    """Reproduce a bounded file snapshot with the same rules as directory verification."""
    if type(files) is not dict or set(files) != NAMES:
        raise PrepareError("INVALID_PREPARATION_PACKAGE_FILES")
    if any(type(raw) is not bytes for raw in files.values()):
        raise PrepareError("INVALID_PREPARATION_PACKAGE_FILES")
    if (any(len(raw) > _limit(name) for name, raw in files.items())
            or sum(map(len, files.values())) > MAX_TOTAL_BYTES):
        raise PrepareError("PREPARATION_PACKAGE_LIMIT_EXCEEDED")
    plan_files = {name: files[saved] for name, saved in PLAN_NAMES.items()}
    expected, _, report = _files(plan_files, files["inputs.json"])
    if files != expected:
        raise PrepareError("PREPARATION_PACKAGE_MISMATCH")
    return {
        "schema": SCHEMA, "status": "reproduced_against_current_compilers_and_adapters",
        "independent_seal_verified": False, "report": report,
        "diagnostics": json.loads(expected["diagnostics.json"]),
    }


def render_markdown(receipt: dict[str, Any]) -> str:
    lines = [
        "# 合成准备交付包", "",
        f"状态：`{receipt['status']}`。", "",
        "保存内容可复算核对；清单不是来源证明、独立封存或统计执行授权。", "",
    ]
    if "report" in receipt:
        lines.append(preparation_diagnostics.render_markdown(receipt["diagnostics"]))
    else:
        lines.extend(["```json", _json_bytes(receipt["manifest"]).decode("utf-8").rstrip(), "```"])
    return "\n".join(lines) + "\n"


class _Parser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise PrepareError("INVALID_ARGUMENTS")


def main(argv: list[str] | None = None) -> int:
    parser = _Parser(description="交付并复算显式合成输入准备包", allow_abbrev=False)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--package", metavar="PLAN_DIR")
    source.add_argument("--plan-archive", metavar="PLAN_ZIP")
    source.add_argument("--verify", metavar="DIR")
    source.add_argument("--archive", metavar="PREPARATION_DIR")
    source.add_argument("--verify-archive", metavar="ZIP")
    parser.add_argument("--inputs", metavar="JSON")
    destination = parser.add_mutually_exclusive_group()
    destination.add_argument("--output", metavar="NEW_DIR_OR_ZIP")
    destination.add_argument("--output-archive", metavar="NEW_ZIP")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--summary", action="store_true")
    parser.add_argument("--role", action="append", default=[], metavar="ID")
    parser.add_argument("--gaps-only", action="store_true")
    try:
        args = parser.parse_args(argv)
        if args.summary and args.verify is None and args.verify_archive is None:
            raise PrepareError("INVALID_ARGUMENTS")
        preparation_diagnostics.validate_options(args.summary, args.role, args.gaps_only)
        renderer = render_markdown
        if args.archive is not None or args.verify_archive is not None:
            from ashare_research.tools import preparation_archive

            if args.inputs is not None or args.output_archive is not None:
                raise PrepareError("INVALID_ARGUMENTS")
            if args.archive is not None:
                if args.output is None:
                    raise PrepareError("INVALID_ARGUMENTS")
                receipt = preparation_archive.export_archive(Path(args.archive), Path(args.output))
            else:
                if args.output is not None:
                    raise PrepareError("INVALID_ARGUMENTS")
                receipt = preparation_archive.verify_archive(Path(args.verify_archive))
            renderer = preparation_archive.render_markdown
        elif args.verify is not None:
            if (args.inputs is not None or args.output is not None
                    or args.output_archive is not None):
                raise PrepareError("INVALID_ARGUMENTS")
            receipt = verify_package(Path(args.verify))
        else:
            if args.inputs is None or (args.output is None and args.output_archive is None):
                raise PrepareError("INVALID_ARGUMENTS")
            plan = Path(args.package if args.package is not None else args.plan_archive)
            if args.output_archive is not None:
                from ashare_research.tools import preparation_archive

                receipt = preparation_archive.export_from_plan(
                    plan, Path(args.inputs), Path(args.output_archive),
                    plan_archive=args.plan_archive is not None,
                )
                renderer = preparation_archive.render_markdown
            else:
                receipt = export_package(
                    plan, Path(args.inputs), Path(args.output),
                    plan_archive=args.plan_archive is not None,
                )
        if args.summary:
            report = (receipt["verification"]["report"] if args.verify_archive is not None
                      else receipt["report"])
            receipt = preparation_diagnostics.build_summary(
                report, roles=args.role, gaps_only=args.gaps_only,
            )
            renderer = preparation_diagnostics.render_markdown
        text = _json_bytes(receipt) if args.json else renderer(receipt).encode("utf-8")
        sys.stdout.buffer.write(text)
        sys.stdout.buffer.flush()
        return 0
    except SystemExit as error:
        return error.code if isinstance(error.code, int) else 2
    except Exception as error:  # noqa: BLE001 - sanitized, no partial stdout
        code = error.code if isinstance(error, (
            PrepareError, PlanError, AdapterError, MatrixError,
            HypothesisConfigError, ContractCompilationError,
        )) else "PREPARATION_PACKAGE_FAILED"
        sys.stderr.buffer.write(f"error: {code}\n".encode())
        sys.stderr.buffer.flush()
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
