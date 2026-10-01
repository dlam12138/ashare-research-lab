"""Readable projections of verified fixed research archives; no new arithmetic."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

from ashare_research.tools import research_session

SCHEMA = "m2_verified_research_review_v1"
ROW_FIELDS = (
    "display_name_zh",
    "metric_id",
    "fiscal_year",
    "status",
    "value",
    "unit",
    "metric_result_id",
    "input_fact_ids",
    "input_available_at_bound",
    "missing_roles",
    "missing_fiscal_years",
    "revision_review_status",
    "result_version",
)
NOTES = (
    "价值报告是混合日期历史汇编，不能作为本次统一时点结论。",
    "数值与单位原样保留；ratio 是比例原值，未转换成百分数。缺失不是零。",
    "输入可用日期上界不证明指标历史发布；重放不是已发布的指标版本。",
    "固定快照只有33条事实，66个原始父记录缺失，可用日期未重新证明。",
    "复核依赖已安装的兼容固定基线和代码，不提供历史真实性或数字签名证明。",
)


class ReviewError(Exception):
    """A sanitized review failure."""

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def _json_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")


def _build(directory: Path) -> tuple[dict[str, Any], dict[str, bytes]]:
    try:
        verification = research_session.verify_session(directory)
        files = research_session.build_session(verification["request"])
    except research_session.SessionError as error:
        raise ReviewError(error.code) from error
    metrics = json.loads(files["metrics/report.json"])
    facts = json.loads(files["facts/report.json"])
    views = []
    for name in ("as_of", "compare_with"):
        block = metrics[name]
        if block is None:
            continue
        views.append(
            {
                "date": block["date"],
                "fact_count": facts["selection_count"]
                if name == "as_of"
                else len(facts["compare_selections"]),
                "rows": [{key: row[key] for key in ROW_FIELDS} for row in block["records"]],
            }
        )
    report = {
        "schema": SCHEMA,
        "symbol": metrics["symbol"],
        "request": verification["request"],
        "session_manifest_sha256": hashlib.sha256(files["manifest.json"]).hexdigest(),
        "views": views,
        "comparison": metrics["comparison"],
        "boundary": metrics["boundary"],
        "notes": list(NOTES),
        "metric_limitations": metrics["limitations_zh"],
        "sources": ["value/report.md", "facts/report.json", "metrics/report.json", "manifest.json"],
    }
    return report, files


def build_review(directory: Path) -> dict[str, Any]:
    """Verify the whole input and faithfully project its original metric records."""
    return _build(directory)[0]


def _cell(value: Any) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def _value(row: dict[str, Any]) -> str:
    return row["value"] if row["value"] is not None else "缺失"


def render_markdown(report: dict[str, Any], *, portable_links: bool = False) -> str:
    request = report["request"]
    lines = [
        "# 中石油研究速览",
        "",
        f"时点：{request['as_of']}；对比：{request['compare_with'] or '未请求'}；"
        f"口径：{request['scope']}；年度：{', '.join(map(str, request['years']))}。",
        "",
        "本页只整理已经复核的档案结果，不新增计算、评分或研究结论。",
        "",
    ]
    for view in report["views"]:
        lines.extend(
            [f"## {view['date']} 的年度指标", "", f"该时点可用事实：{view['fact_count']} 条。", ""]
        )
        years = sorted({row["fiscal_year"] for row in view["rows"]})
        for year in years:
            lines.extend(
                [
                    f"### {year} 年",
                    "",
                    "| 指标 | 数值原值 | 单位 | 状态 | 输入日期上界 | 缺失角色（年度） |",
                    "| --- | --- | --- | --- | --- | --- |",
                ]
            )
            for row in view["rows"]:
                if row["fiscal_year"] != year:
                    continue
                missing = (
                    "、".join(
                        f"{item['role']}（{item['fiscal_year']}）" for item in row["missing_roles"]
                    )
                    or "无"
                )
                cells = (
                    row["display_name_zh"],
                    _value(row),
                    row["unit"],
                    row["status"],
                    row["input_available_at_bound"] or "未知",
                    missing,
                )
                lines.append("| " + " | ".join(map(_cell, cells)) + " |")
            lines.append("")
    comparison = report["comparison"]
    lines.extend(["## 两时点变化", ""])
    if comparison is None:
        lines.append("未请求对比。")
    else:
        lines.extend(
            [
                "| 年度 | 指标 | 前值 | 后值 | 单位（前 / 后） | 原有对比状态 |",
                "| --- | --- | --- | --- | --- | --- |",
            ]
        )
        for row in comparison["entries"]:
            cells = (
                row["fiscal_year"],
                row["display_name_zh"],
                _value(row["before"]),
                _value(row["after"]),
                f"{row['before']['unit']} / {row['after']['unit']}",
                row["state_label_zh"],
            )
            lines.append("| " + " | ".join(map(_cell, cells)) + " |")
    lines.extend(["", "## 证据与限制", ""])
    for source in report["sources"]:
        lines.append(f"- [{source}](session/{source})" if portable_links else f"- `{source}`")
    lines.append("")
    lines.extend(f"- {note}" for note in report["notes"] + report["metric_limitations"])
    return "\n".join(lines) + "\n"


def export_review(directory: Path, output: Path) -> dict[str, Any]:
    """Export a view plus the complete unchanged verified archive in a new root."""
    if output.is_symlink() or output.exists():
        raise ReviewError("OUTPUT_PATH_EXISTS")
    report, session = _build(directory)
    files = {"session/" + name: payload for name, payload in session.items()}
    files["review.md"] = render_markdown(report, portable_links=True).encode("utf-8")
    files["review.json"] = _json_bytes(report)
    entries = [
        {"path": name, "byte_count": len(payload), "sha256": hashlib.sha256(payload).hexdigest()}
        for name, payload in sorted(files.items())
    ]
    manifest = {
        "schema": SCHEMA,
        "request": report["request"],
        "files": entries,
        "managed_file_count": len(entries),
        "total_byte_count": sum(e["byte_count"] for e in entries),
        "outer_manifest_is_integrity_inventory_only": True,
    }
    files["manifest.json"] = _json_bytes(manifest)
    try:
        output.mkdir(parents=True, exist_ok=False)
    except FileExistsError as error:
        raise ReviewError("OUTPUT_PATH_EXISTS") from error
    except OSError as error:
        raise ReviewError("OUTPUT_WRITE_FAILED") from error
    try:
        for name, payload in sorted(files.items()):
            target = output / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(payload)
    except OSError as error:
        raise ReviewError("OUTPUT_WRITE_FAILED") from error
    return manifest


class _Parser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise ReviewError("INVALID_ARGUMENTS")


def main(argv: list[str] | None = None) -> int:
    parser = _Parser(description="从已复核研究档案生成年度指标速览", allow_abbrev=False)
    parser.add_argument("--session", required=True, metavar="DIR")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--json", action="store_true")
    mode.add_argument("--output", metavar="NEW_DIR")
    try:
        arguments = parser.parse_args(argv)
        if arguments.output is not None:
            manifest = export_review(Path(arguments.session), Path(arguments.output))
            encoded = f"exported {manifest['managed_file_count']} managed files\n".encode()
        else:
            report = build_review(Path(arguments.session))
            encoded = (
                _json_bytes(report) if arguments.json else render_markdown(report).encode("utf-8")
            )
        sys.stdout.buffer.write(encoded)
        sys.stdout.buffer.flush()
        return 0
    except SystemExit as error:
        return error.code if isinstance(error.code, int) else 2
    except Exception as error:  # noqa: BLE001 - sanitize before any stdout is emitted
        code = error.code if isinstance(error, ReviewError) else "UNEXPECTED_FAILURE"
        sys.stderr.buffer.write(f"error: {code}\n".encode())
        sys.stderr.buffer.flush()
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
