"""Read-only differences between fully verified compile-only M4 plans."""

from __future__ import annotations

import argparse
import html
import json
import sys
from pathlib import Path
from typing import Any

from ashare_research.mechanism.contract_compiler import ContractCompilationError
from ashare_research.mechanism.hypothesis_config import HypothesisConfigError
from ashare_research.tools import research_plan_archive, research_plan_package
from ashare_research.tools.research_plan import PlanError

SCHEMA = "m4_verified_compile_only_plan_comparison_v1"
SECTIONS = ("config", "contract", "plan")
IDENTITY_FIELDS = {
    "config": frozenset(),
    "contract": frozenset({"contract_digest", "source_config_digest"}),
    "plan": frozenset({"plan_digest", "source_contract_digest"}),
}
MISSING = object()
NOTES = (
    "两侧输入均通过现有编译器重新编译及完整内容复核；目录与原生 ZIP 可混用。",
    "源文件 SHA256 比较与规范内容比较分开，格式变化不等于方案语义变化。",
    "差异按规范对象及列表原始索引展示，不推断对象对齐，不评价哪份方案更好。",
    "摘要和内容复核不验证独立封存、作者、历史来源或真实研究就绪。",
    "本次不执行统计研究，不访问结果或 holdout，也不授权任何计划执行。",
)


class CompareError(Exception):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def _value(value: Any) -> dict[str, Any]:
    return {"present": value is not MISSING, "value": None if value is MISSING else value}


def _changes(left: Any, right: Any, pointer: str = "") -> list[dict[str, Any]]:
    if type(left) is dict and type(right) is dict:
        rows = []
        for key in sorted(left.keys() | right.keys()):
            token = key.replace("~", "~0").replace("/", "~1")
            rows.extend(_changes(left.get(key, MISSING), right.get(key, MISSING),
                                 f"{pointer}/{token}"))
        return rows
    if type(left) is list and type(right) is list:
        rows = []
        for index in range(max(len(left), len(right))):
            rows.extend(_changes(left[index] if index < len(left) else MISSING,
                                 right[index] if index < len(right) else MISSING,
                                 f"{pointer}/{index}"))
        return rows
    if type(left) is type(right) and left == right:
        return []
    return [{"pointer": pointer, "left": _value(left), "right": _value(right)}]


def _load(path: Path, archive: bool) -> dict[str, Any]:
    if archive:
        return research_plan_archive.verify_archive(path)["verification"]["report"]
    return research_plan_package.verify_package(path)["report"]


def _identity(report: dict[str, Any]) -> dict[str, str]:
    return {
        "hypothesis_id": report["contract"]["hypothesis_id"],
        "source_file_sha256": report["source_file_sha256"],
        "config_digest": report["contract"]["source_config_digest"],
        "contract_digest": report["contract"]["contract_digest"],
        "plan_digest": report["plan"]["plan_digest"],
    }


def build_comparison(
    left: Path, right: Path, *, left_archive: bool = False, right_archive: bool = False,
) -> dict[str, Any]:
    before = _load(left, left_archive)
    after = _load(right, right_archive)
    rows = []
    for section in SECTIONS:
        excluded = IDENTITY_FIELDS[section]
        old = {key: value for key, value in before[section].items() if key not in excluded}
        new = {key: value for key, value in after[section].items() if key not in excluded}
        rows.extend({"section": section, **row} for row in _changes(old, new))
    rows.sort(key=lambda row: (SECTIONS.index(row["section"]), row["pointer"]))
    old_identity, new_identity = _identity(before), _identity(after)
    return {
        "schema": SCHEMA,
        "status": "verified_pre_execution_comparison",
        "left": old_identity,
        "right": new_identity,
        "equality": {key: old_identity[key] == new_identity[key] for key in old_identity},
        "canonical_content_equal": not rows,
        "change_count": len(rows),
        "section_change_counts": {
            section: sum(row["section"] == section for row in rows) for section in SECTIONS
        },
        "changes": rows,
        "boundary": before["boundary"],
        "notes": list(NOTES),
    }


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False)


def _cell(value: Any) -> str:
    text = (html.escape(str(value), quote=False).replace("\\", "\\\\").replace("|", "\\|")
            .replace("`", "&#96;").replace("\r", "\\r").replace("\n", "\\n"))
    for character in "*_[]()":
        text = text.replace(character, f"\\{character}")
    return text


def _display(value: dict[str, Any]) -> str:
    if not value["present"]:
        return "（缺失）"
    return json.dumps(value["value"], ensure_ascii=False, sort_keys=True, allow_nan=False)


def render_markdown(report: dict[str, Any]) -> str:
    lines = ["# 研究计划对比（仅编译）", "", "两侧计划已完整复核；未执行统计研究。", "",
             "| 标识 | 左侧 | 右侧 | 相同 |", "| --- | --- | --- | --- |"]
    for key in ("hypothesis_id", "source_file_sha256", "config_digest",
                "contract_digest", "plan_digest"):
        lines.append("| " + " | ".join(map(_cell, (
            key, report["left"][key], report["right"][key], report["equality"][key],
        ))) + " |")
    lines.extend(["", f"规范内容变化：{report['change_count']} 项。", ""])
    if report["changes"]:
        lines.extend(["| 对象 | JSON Pointer | 左侧 | 右侧 |", "| --- | --- | --- | --- |"])
        for row in report["changes"]:
            lines.append("| " + " | ".join(map(_cell, (
                row["section"], row["pointer"], _display(row["left"]), _display(row["right"]),
            ))) + " |")
    else:
        lines.append("无规范内容变化。")
    lines.extend(["", "## 执行边界", "", "```json", _json(report["boundary"]), "```",
                  "", "## 限制", "", *(f"- {note}" for note in report["notes"]), ""])
    return "\n".join(lines)


class _Parser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise CompareError("INVALID_ARGUMENTS")


def main(argv: list[str] | None = None) -> int:
    parser = _Parser(description="对比两份已完整复核的仅编译研究计划", allow_abbrev=False)
    left = parser.add_mutually_exclusive_group(required=True)
    left.add_argument("--left", metavar="DIR")
    left.add_argument("--left-archive", metavar="ZIP")
    right = parser.add_mutually_exclusive_group(required=True)
    right.add_argument("--right", metavar="DIR")
    right.add_argument("--right-archive", metavar="ZIP")
    parser.add_argument("--json", action="store_true")
    try:
        args = parser.parse_args(argv)
        report = build_comparison(
            Path(args.left if args.left is not None else args.left_archive),
            Path(args.right if args.right is not None else args.right_archive),
            left_archive=args.left_archive is not None,
            right_archive=args.right_archive is not None,
        )
        text = _json(report) + "\n" if args.json else render_markdown(report)
        sys.stdout.buffer.write(text.encode("utf-8"))
        sys.stdout.buffer.flush()
        return 0
    except SystemExit as error:
        return error.code if isinstance(error.code, int) else 2
    except Exception as error:  # noqa: BLE001 - sanitized, never emit a partial report
        code = (error.code if isinstance(error, (
            CompareError, PlanError, HypothesisConfigError, ContractCompilationError,
        )) else "PLAN_COMPARISON_FAILED")
        sys.stderr.buffer.write(f"error: {code}\n".encode())
        sys.stderr.buffer.flush()
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
