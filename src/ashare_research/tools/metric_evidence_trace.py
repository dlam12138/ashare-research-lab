"""Trace one original metric's evidence from a fully verified delivered package."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from ashare_research.tools import package_archive, package_verification

SCHEMA = "m2_verified_metric_evidence_trace_v1"
NOTES = (
    "仅筛选已复核档案中的原始指标及输入，没有重新计算或推断变化原因。",
    "缺失保持缺失；来源字段和未留存父记录按原档案展示，不代表已补齐证据。",
    "固定快照中的可用日期不重新证明历史发布；复核不授予研究或生产资格。",
)


class TraceError(Exception):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def trace_metric(
    source: Path, metric_id: str, fiscal_year: int, *, archive: bool = False,
) -> dict[str, Any]:
    if not metric_id or fiscal_year < 1:
        raise TraceError("INVALID_ARGUMENTS")
    try:
        if archive:
            receipt, files = package_archive.load_verified_archive(source)
            verification = receipt["verification"]
        else:
            verification, files = package_verification.load_verified_package(source)
            receipt = None
    except (package_archive.ArchiveError, package_verification.PackageError) as error:
        raise TraceError(error.code) from error
    kind = verification["package_kind"]
    if kind not in ("session", "workflow"):
        raise TraceError("SESSION_PACKAGE_REQUIRED")
    name = "session/metrics/report.json" if kind == "workflow" else "metrics/report.json"
    metrics = json.loads(files[name])
    views = []
    for view_name in ("as_of", "compare_with"):
        view = metrics[view_name]
        if view is None:
            continue
        record = next(
            (row for row in view["records"]
             if row["metric_id"] == metric_id and row["fiscal_year"] == fiscal_year), None,
        )
        if record is None:
            raise TraceError("METRIC_NOT_SELECTED")
        views.append({"view": view_name, "date": view["date"], "record": record})
    comparison = None
    if metrics["comparison"] is not None:
        comparison = next((entry for entry in metrics["comparison"]["entries"]
                           if entry["metric_id"] == metric_id
                           and entry["fiscal_year"] == fiscal_year), None)
    return {
        "schema": SCHEMA, "status": "traced", "symbol": metrics["symbol"],
        "metric_id": metric_id, "fiscal_year": fiscal_year, "request": metrics["request"],
        "views": views, "comparison": comparison, "boundary": metrics["boundary"],
        "metric_limitations": metrics["limitations_zh"], "notes": list(NOTES),
        "verification": verification, "archive_receipt": receipt,
    }


def _cell(value: Any) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def render_markdown(report: dict[str, Any]) -> str:
    lines = [f"# 指标证据追溯：{report['fiscal_year']} / {report['metric_id']}", ""]
    comparison = report["comparison"]
    if comparison is not None:
        lines.extend([f"原档案比较类别：{comparison['state_label_zh']}。", ""])
    for view in report["views"]:
        row = view["record"]
        value = row["value"] if row["value"] is not None else "缺失"
        lines.extend([
            f"## {view['date']} / {view['view']}", "",
            f"{row['display_name_zh']}：{value} {row['unit']}（{row['status']}）。",
            f"原定义：`{row['formula']}`；结果 ID：`{row['metric_result_id']}`。", "",
            "| 输入角色 | 状态 | 原始值 | 单位 | 事实 ID |",
            "| --- | --- | --- | --- | --- |",
        ])
        for binding in row["inputs"]:
            cells = (
                binding["role"], binding["status"],
                (binding.get("value_decimal")
                 if binding.get("value_decimal") is not None else "缺失"),
                binding.get("unit", "未记录"), binding.get("fact_id", "未选择"),
            )
            lines.append("| " + " | ".join(map(_cell, cells)) + " |")
        for binding in row["inputs"]:
            lines.extend(["", f"### 输入 `{binding['role']}`", ""])
            missing = binding.get("missing_source_reference_fields", [])
            lines.append(f"未留存来源字段：{', '.join(missing) if missing else '未列出'}。")
            if "source_reference" in binding:
                lines.extend(["", "原始来源引用：", "```json",
                              json.dumps(binding["source_reference"], ensure_ascii=False,
                                         sort_keys=True, indent=2), "```"])
            parents = binding.get("parents")
            if parents is not None:
                lines.append(f"父记录：总数 {parents['total']}，未解决 {parents['unresolved']}。")
                lines.extend(f"- `{parent['fact_id']}`：{parent['status']}"
                             for parent in parents["entries"])
            else:
                lines.append("该输入未选择到事实，原始缺失描述见 JSON。")
        missing_roles = ", ".join(
            f"{item['role']} / {item['concept_id']} / {item['fiscal_year']}"
            for item in row["missing_roles"]
        )
        lines.extend(["", f"缺失输入角色：{missing_roles or '未列出'}。", ""])
    lines.extend(["## 阅读边界", "", *(f"- {note}" for note in report["notes"])])
    return "\n".join(lines) + "\n"


class _Parser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise TraceError("INVALID_ARGUMENTS")


def main(argv: list[str] | None = None) -> int:
    parser = _Parser(description="逐项追溯交付包中指标的原始输入与证据", allow_abbrev=False)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--package", metavar="DIR")
    source.add_argument("--archive", metavar="ZIP")
    parser.add_argument("--metric", required=True, metavar="ID")
    parser.add_argument("--year", required=True, type=int)
    parser.add_argument("--json", action="store_true")
    try:
        args = parser.parse_args(argv)
        result = trace_metric(
            Path(args.archive if args.archive is not None else args.package),
            args.metric, args.year, archive=args.archive is not None,
        )
        text = (json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
                if args.json else render_markdown(result))
        sys.stdout.buffer.write(text.encode("utf-8"))
        sys.stdout.buffer.flush()
        return 0
    except SystemExit as error:
        return error.code if isinstance(error.code, int) else 2
    except Exception as error:  # noqa: BLE001 - sanitized errors, no partial stdout
        code = error.code if isinstance(error, TraceError) else "UNEXPECTED_FAILURE"
        sys.stderr.buffer.write(f"error: {code}\n".encode())
        sys.stderr.buffer.flush()
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
