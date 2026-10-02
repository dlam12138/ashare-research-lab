"""Describe original evidence omissions and their metric dependencies, offline."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

from ashare_research.tools import research_session

SCHEMA = "m2_verified_evidence_audit_v1"
NOTES = (
    "本台账只描述留存证据与引用关系，不判断财务质量、研究就绪或生产资格。",
    "缺失来源字段不等于来源不存在；父记录未留存不等于事实数值错误。",
    "输入可用日期取自固定快照，不重新证明历史发布或原始可得性。",
    "统计仅针对所选指标使用的事实；固定快照整体33条事实、66个原始父记录缺失。",
    "价值报告是混合日期汇编；指标为离线读取模型，未获得历史发布/版本准入。",
)


class AuditError(Exception):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def _json_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode()


def _build(directory: Path) -> tuple[dict[str, Any], dict[str, bytes]]:
    try:
        verification = research_session.verify_session(directory)
        archive = research_session.build_session(verification["request"])
    except research_session.SessionError as error:
        raise AuditError(error.code) from error
    metrics = json.loads(archive["metrics/report.json"])
    indexed: dict[tuple[str, str], dict[str, Any]] = {}
    missing = []
    for name in ("as_of", "compare_with"):
        view = metrics[name]
        if view is None:
            continue
        for result in view["records"]:
            dependency = {
                "metric_id": result["metric_id"],
                "display_name_zh": result["display_name_zh"],
                "fiscal_year": result["fiscal_year"],
                "metric_result_id": result["metric_result_id"],
                "metric_status": result["status"],
            }
            for binding in result["inputs"]:
                use = {**dependency, "role": binding["role"]}
                if binding["status"] == "missing":
                    omission = {"date": view["date"], "use": use, "expected_input": binding}
                    if omission not in missing:
                        missing.append(omission)
                    continue
                key = (view["date"], binding["fact_id"])
                if key not in indexed:
                    fact = {k: v for k, v in binding.items() if k != "role"}
                    gaps = []
                    if fact["missing_source_reference_fields"]:
                        gaps.append("MISSING_RETAINED_SOURCE_FIELDS")
                    if fact["parents"]["unresolved"]:
                        gaps.append("UNRESOLVED_RETAINED_PARENTS")
                    indexed[key] = {"date": view["date"], "fact": fact, "gaps": gaps, "uses": []}
                if use not in indexed[key]["uses"]:
                    indexed[key]["uses"].append(use)
    facts = [indexed[key] for key in sorted(indexed)]
    parent_ids = {
        parent["fact_id"]
        for item in facts
        for parent in item["fact"]["parents"]["entries"]
        if parent["status"] == "unresolved_absent_from_snapshot"
    }
    report = {
        "schema": SCHEMA,
        "symbol": metrics["symbol"],
        "request": verification["request"],
        "source_facts": facts,
        "missing_inputs": missing,
        "summary": {
            "dated_fact_rows": len(facts),
            "unique_fact_ids": len({item["fact"]["fact_id"] for item in facts}),
            "unique_unresolved_parent_ids": len(parent_ids),
            "missing_input_roles": len(missing),
            "dated_facts_with_gaps": sum(bool(item["gaps"]) for item in facts),
        },
        "session_manifest_sha256": hashlib.sha256(archive["manifest.json"]).hexdigest(),
        "notes": list(NOTES),
        "metric_boundary": metrics["boundary"],
        "evidence_gaps_present": bool(missing or any(item["gaps"] for item in facts)),
    }
    return report, archive


def build_audit(directory: Path) -> dict[str, Any]:
    return _build(directory)[0]


def _cell(value: Any) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def render_markdown(report: dict[str, Any], *, portable_links: bool = False) -> str:
    request, counts = report["request"], report["summary"]
    lines = [
        "# 中石油指标证据缺口台账",
        "",
        f"查询时点：{request['as_of']}；对比：{request['compare_with'] or '未请求'}；"
        f"口径：{request['scope']}。",
        "",
        f"按时点去重事实行 {counts['dated_fact_rows']}；"
        f"跨时点唯一事实 ID {counts['unique_fact_ids']}；"
        f"使用事实涉及的唯一未解决父记录 ID {counts['unique_unresolved_parent_ids']}；"
        f"缺失输入角色 {counts['missing_input_roles']}。",
        "",
        "同一事实用于多个指标时合并列出引用；相同事实在不同查询时点保留各自记录。",
        "",
        "## 原始事实与受影响指标",
        "",
        "| 查询时点 | 事实年度/概念 | 原始小数值/单位 | 留存来源缺失字段 |"
        " 未解决父记录 | 指标年度/输入角色 |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for item in report["source_facts"]:
        fact = item["fact"]
        uses = "；".join(
            f"{use['fiscal_year']} {use['display_name_zh']} / {use['role']}" for use in item["uses"]
        )
        cells = (
            item["date"],
            f"{fact['fiscal_year']} / {fact['concept_id']}",
            f"{fact['value_decimal']} {fact['unit']}",
            "、".join(fact["missing_source_reference_fields"]) or "无",
            fact["parents"]["unresolved"],
            uses,
        )
        lines.append("| " + " | ".join(map(_cell, cells)) + " |")
    if not report["source_facts"]:
        lines.append("没有已选择的输入事实；不能把空结果视为证据齐全。")
    lines.extend(["", "## 缺失输入角色", ""])
    for omission in report["missing_inputs"]:
        use, expected = omission["use"], omission["expected_input"]
        lines.append(
            f"- {omission['date']}：{use['fiscal_year']} {use['display_name_zh']}，"
            f"角色 `{use['role']}` 缺少 {expected['fiscal_year']} 年 `{expected['concept_id']}`，"
            f"原因 `{expected['reason']}`；原指标状态 `{use['metric_status']}`。"
        )
    if not report["missing_inputs"]:
        lines.append("所选指标没有缺失输入角色；来源字段与父记录缺口仍按上表保留。")
    lines.extend(["", "## 逐条追溯与边界", ""])
    for path in ("metrics/report.json", "facts/report.json", "manifest.json"):
        lines.append(f"- [{path}](session/{path})" if portable_links else f"- `{path}`")
    lines.append(
        "- JSON输出（`--json`或导出的`audit.json`）保留完整事实、父记录 ID、来源字段和指标结果 ID。"
    )
    lines.extend(f"- {note}" for note in report["notes"])
    return "\n".join(lines) + "\n"


def export_audit(directory: Path, output: Path) -> dict[str, Any]:
    if output.is_symlink() or output.exists():
        raise AuditError("OUTPUT_PATH_EXISTS")
    report, archive = _build(directory)
    files = {"session/" + name: raw for name, raw in archive.items()}
    files["audit.md"] = render_markdown(report, portable_links=True).encode()
    files["audit.json"] = _json_bytes(report)
    entries = [
        {"path": name, "byte_count": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}
        for name, raw in sorted(files.items())
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
        raise AuditError("OUTPUT_PATH_EXISTS") from error
    except OSError as error:
        raise AuditError("OUTPUT_WRITE_FAILED") from error
    try:
        for name, raw in sorted(files.items()):
            path = output / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)
    except OSError as error:
        raise AuditError("OUTPUT_WRITE_FAILED") from error
    return manifest


class _Parser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise AuditError("INVALID_ARGUMENTS")


def main(argv: list[str] | None = None) -> int:
    parser = _Parser(description="复核研究档案并汇总原始证据缺口与指标引用", allow_abbrev=False)
    parser.add_argument("--session", required=True, metavar="DIR")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--json", action="store_true")
    mode.add_argument("--output", metavar="NEW_DIR")
    try:
        args = parser.parse_args(argv)
        if args.output is not None:
            manifest = export_audit(Path(args.session), Path(args.output))
            raw = f"exported {manifest['managed_file_count']} managed files\n".encode()
        else:
            report = build_audit(Path(args.session))
            raw = _json_bytes(report) if args.json else render_markdown(report).encode()
        sys.stdout.buffer.write(raw)
        sys.stdout.buffer.flush()
        return 0
    except SystemExit as error:
        return error.code if isinstance(error.code, int) else 2
    except Exception as error:  # noqa: BLE001 - stable sanitized errors, no partial stdout
        code = error.code if isinstance(error, AuditError) else "UNEXPECTED_FAILURE"
        sys.stderr.buffer.write(f"error: {code}\n".encode())
        sys.stderr.buffer.flush()
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
