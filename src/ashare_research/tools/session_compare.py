"""Compare verified retained metric views using the original comparison engine."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

from ashare_research.tools import pit_metric_replay, research_session

SCHEMA = "m2_verified_session_comparison_v1"
VIEWS = ("as_of", "compare_with")
LABELS = {"added": "新增选择", "removed": "移除选择", **pit_metric_replay.STATE_LABELS_ZH}
NOTES = (
    "新增/移除表示两份档案的指标或年度选择不同，不表示财务事实新增/消失。",
    "状态/数值/输入变化沿用既有比较规则，不推断变化原因；没有计算差额或收益。",
    "数值与单位原样保留；ratio 未转换百分数，缺失不是零。",
    "左右方向由调用者选择，不要求日期递增；同日相等不证明历史发布。",
    "价值报告是混合日期汇编；指标是离线读取模型，未获得历史发布或版本准入。",
    "固定快照33条事实、66个原始父记录缺失，历史可得性未重新证明。",
    "复核依赖已安装的兼容固定基线与代码，不证明真实性或签名。",
)


class CompareError(Exception):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def _json_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode()


def _load_zip(source: Path) -> tuple[dict[str, Any], dict[str, bytes]]:
    # Lazy import avoids the package verifier -> comparison builder import cycle.
    from ashare_research.tools import package_archive

    try:
        receipt, files = package_archive.load_verified_archive(source)
    except package_archive.ArchiveError as error:
        raise CompareError(error.code) from error
    kind = receipt["package_kind"]
    if kind not in ("session", "workflow"):
        raise CompareError("SESSION_PACKAGE_REQUIRED")
    if kind == "workflow":
        files = {name[len("session/"):]: raw for name, raw in files.items()
                 if name.startswith("session/")}
    # The whole parent has already been verified; never reopen retained members.
    return json.loads(files["manifest.json"]), files


def _load(
    directory: Path, view_name: str, *, archive_input: bool = False
) -> tuple[dict[str, Any], dict[str, bytes]]:
    if view_name not in VIEWS:
        raise CompareError("INVALID_VIEW")
    try:
        verified, archive = (
            _load_zip(directory) if archive_input
            else research_session.load_verified_session(directory)
        )
    except research_session.SessionError as error:
        raise CompareError(error.code) from error
    metrics = json.loads(archive["metrics/report.json"])
    view = metrics[view_name]
    if view is None:
        raise CompareError("VIEW_NOT_REQUESTED")
    return {
        "symbol": metrics["symbol"],
        "request": verified["request"],
        "selected_view": view_name,
        "selected_date": view["date"],
        "scope": view["scope"],
        "records": view["records"],
        "boundary": metrics["boundary"],
        "metric_limitations": metrics["limitations_zh"],
        "session_manifest_sha256": hashlib.sha256(archive["manifest.json"]).hexdigest(),
    }, archive


def _build(
    left: Path, right: Path, left_view: str, right_view: str,
    *, left_archive: bool = False, right_archive: bool = False,
) -> tuple[dict[str, Any], dict[str, dict[str, bytes]]]:
    before, left_files = _load(left, left_view, archive_input=left_archive)
    after, right_files = _load(right, right_view, archive_input=right_archive)
    if before["symbol"] != after["symbol"]:
        raise CompareError("SYMBOL_MISMATCH")
    if before["scope"] != after["scope"]:
        raise CompareError("SCOPE_MISMATCH")
    left_index = {(r["metric_id"], r["fiscal_year"]): r for r in before["records"]}
    right_index = {(r["metric_id"], r["fiscal_year"]): r for r in after["records"]}
    common = sorted(left_index.keys() & right_index.keys())
    original = pit_metric_replay.build_comparison(
        [left_index[key] for key in common], [right_index[key] for key in common]
    )
    common_states = {(e["metric_id"], e["fiscal_year"]): e["state"] for e in original["entries"]}
    counts = dict.fromkeys(LABELS, 0)
    entries = []
    for key in sorted(left_index.keys() | right_index.keys()):
        left_row, right_row = left_index.get(key), right_index.get(key)
        state = (
            "added" if left_row is None else "removed" if right_row is None else common_states[key]
        )
        counts[state] += 1
        entries.append(
            {
                "metric_id": key[0],
                "fiscal_year": key[1],
                "display_name_zh": (left_row or right_row)["display_name_zh"],
                "state": state,
                "state_label_zh": LABELS[state],
                "before": left_row,
                "after": right_row,
            }
        )
    return {
        "schema": SCHEMA,
        "left": before,
        "right": after,
        "states": counts,
        "entries": entries,
        "compared_key_count": len(entries),
        "common_key_count": len(common),
        "original_common_comparison": original,
        "notes": list(NOTES),
    }, {"left": left_files, "right": right_files}


def build_comparison(
    left: Path, right: Path, *, left_view: str = "as_of", right_view: str = "as_of",
    left_archive: bool = False, right_archive: bool = False,
) -> dict[str, Any]:
    return _build(
        left, right, left_view, right_view,
        left_archive=left_archive, right_archive=right_archive,
    )[0]


def _cell(value: Any) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def _value(row: dict[str, Any] | None) -> str:
    if row is None:
        return "未选择"
    return f"{row['value'] if row['value'] is not None else '缺失'} {row['unit']} ({row['status']})"


def render_markdown(report: dict[str, Any], *, portable_links: bool = False) -> str:
    lines = ["# 已复核研究档案对比", ""]
    for side, label in (("left", "左"), ("right", "右")):
        block, request = report[side], report[side]["request"]
        lines.extend(
            [
                f"{label}：{block['selected_date']} / `{block['selected_view']}` / "
                f"{block['scope']}。",
                f"年度：{', '.join(map(str, request['years']))}；"
                f"指标：{', '.join(request['metrics'])}；"
                f"档案请求日期：{request['as_of']} → {request['compare_with'] or '未请求对比'}。",
                f"档案清单 SHA256：`{block['session_manifest_sha256']}`。",
                "",
            ]
        )
    lines.extend(
        [
            f"键并集 {report['compared_key_count']}；共同选择 {report['common_key_count']}。",
            "；".join(f"{LABELS[state]} {count}" for state, count in report["states"].items()),
            "",
            "| 年度/指标 | 变化类别 | 左原始值/单位/状态 | 右原始值/单位/状态 |",
            "| --- | --- | --- | --- |",
        ]
    )
    for entry in report["entries"]:
        cells = (
            f"{entry['fiscal_year']} {entry['display_name_zh']}",
            entry["state_label_zh"],
            _value(entry["before"]),
            _value(entry["after"]),
        )
        lines.append("| " + " | ".join(map(_cell, cells)) + " |")
    lines.extend(["", "## 原始证据与边界", ""])
    for side in ("left", "right"):
        for name in ("metrics/report.json", "facts/report.json", "manifest.json"):
            path = f"{side}/{name}"
            lines.append(f"- [{path}]({path})" if portable_links else f"- `{path}`")
    lines.append("- JSON保留完整原始指标记录、输入小数值、来源缺失字段、父记录与缺失角色。")
    lines.extend(f"- {note}" for note in report["notes"])
    return "\n".join(lines) + "\n"


def export_comparison(
    left: Path,
    right: Path,
    output: Path,
    *,
    left_view: str = "as_of",
    right_view: str = "as_of",
    left_archive: bool = False,
    right_archive: bool = False,
) -> dict[str, Any]:
    if output.is_symlink() or output.exists():
        raise CompareError("OUTPUT_PATH_EXISTS")
    report, archives = _build(
        left, right, left_view, right_view,
        left_archive=left_archive, right_archive=right_archive,
    )
    files = {
        f"{side}/{name}": raw for side, archive in archives.items() for name, raw in archive.items()
    }
    files["compare.md"] = render_markdown(report, portable_links=True).encode()
    files["compare.json"] = _json_bytes(report)
    entries = [
        {"path": name, "byte_count": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}
        for name, raw in sorted(files.items())
    ]
    manifest = {
        "schema": SCHEMA,
        "sides": {
            side: {
                key: report[side][key]
                for key in ("request", "selected_view", "session_manifest_sha256")
            }
            for side in ("left", "right")
        },
        "files": entries,
        "managed_file_count": len(entries),
        "total_byte_count": sum(entry["byte_count"] for entry in entries),
        "outer_manifest_is_integrity_inventory_only": True,
    }
    files["manifest.json"] = _json_bytes(manifest)
    try:
        output.mkdir(parents=True, exist_ok=False)
    except FileExistsError as error:
        raise CompareError("OUTPUT_PATH_EXISTS") from error
    except OSError as error:
        raise CompareError("OUTPUT_WRITE_FAILED") from error
    try:
        for name, raw in sorted(files.items()):
            path = output / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)
    except OSError as error:
        raise CompareError("OUTPUT_WRITE_FAILED") from error
    return manifest


class _Parser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise CompareError("INVALID_ARGUMENTS")


def main(argv: list[str] | None = None) -> int:
    parser = _Parser(description="对比两个完整复核档案的原始指标视图", allow_abbrev=False)
    left_source = parser.add_mutually_exclusive_group(required=True)
    left_source.add_argument("--left", metavar="SESSION_DIR")
    left_source.add_argument("--left-archive", metavar="ZIP")
    right_source = parser.add_mutually_exclusive_group(required=True)
    right_source.add_argument("--right", metavar="SESSION_DIR")
    right_source.add_argument("--right-archive", metavar="ZIP")
    parser.add_argument("--left-view", choices=VIEWS, default="as_of")
    parser.add_argument("--right-view", choices=VIEWS, default="as_of")
    parser.add_argument("--evidence", action="store_true", help="同时比较原始输入及来源证据")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--json", action="store_true")
    mode.add_argument("--output", metavar="NEW_DIR")
    try:
        args = parser.parse_args(argv)
        if args.evidence and args.output is not None:
            raise CompareError("INVALID_ARGUMENTS")
        options = {
            "left_view": args.left_view, "right_view": args.right_view,
            "left_archive": args.left_archive is not None,
            "right_archive": args.right_archive is not None,
        }
        left = Path(args.left_archive if args.left_archive is not None else args.left)
        right = Path(args.right_archive if args.right_archive is not None else args.right)
        if args.output is not None:
            manifest = export_comparison(left, right, Path(args.output), **options)
            raw = f"exported {manifest['managed_file_count']} managed files\n".encode()
        else:
            report = build_comparison(left, right, **options)
            if args.evidence:
                from ashare_research.tools import evidence_comparison

                report = evidence_comparison.build_report(report)
                raw = (_json_bytes(report) if args.json else
                       evidence_comparison.render_markdown(report).encode())
            else:
                raw = _json_bytes(report) if args.json else render_markdown(report).encode()
        sys.stdout.buffer.write(raw)
        sys.stdout.buffer.flush()
        return 0
    except SystemExit as error:
        return error.code if isinstance(error.code, int) else 2
    except Exception as error:  # noqa: BLE001 - sanitized errors, no partial stdout
        code = error.code if isinstance(error, CompareError) else "UNEXPECTED_FAILURE"
        sys.stderr.buffer.write(f"error: {code}\n".encode())
        sys.stderr.buffer.flush()
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
