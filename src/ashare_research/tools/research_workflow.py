"""Compose existing offline tools into one complete, navigable delivery."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import tempfile
from pathlib import Path
from typing import Any

from ashare_research.tools import evidence_audit, research_review, research_session, session_compare

MANIFEST_SCHEMA = "m2_complete_offline_research_workflow_v1"
NOTES = (
    "仅组合既有固定来源工具，不获取新数据，不改变计算、评分或研究资格。",
    "价值资料是混合日期汇编；事实和指标读取模型按本次请求日期选择，两者不可替代。",
    "固定快照33条事实、66个缺失原始父记录及历史发布/版本证据缺口保持不变。",
    "验证需要已安装的兼容固定基线与代码；不证明真实性、签名或历史可得性。",
)


class WorkflowError(Exception):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def _json_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode()


def _index(request: dict[str, Any], areas: list[str]) -> bytes:
    lines = [
        "# 完整离线研究工作流",
        "",
        f"时点：{request['as_of']}；对比：{request['compare_with'] or '未请求'}；"
        f"年度：{', '.join(map(str, request['years']))}；口径：{request['scope']}。",
        "",
        "## 从这里开始",
        "",
        "- [指标速览](review/review.md)：按请求日期浏览已有指标及两时点变化。",
        "- [证据缺口台账](audit/audit.md)：查看指标输入与未解决的原始证据。",
        "- [完整研究档案](session/index.md)：价值资料、事实、指标和固定快照。",
    ]
    if "compare" in areas:
        lines.append("- [两时点指标对比](compare/compare.md)：左侧 as_of，右侧 compare_with。")
    lines.extend(["", "## 复核与边界", ""])
    lines.append("各子目录均保留原有独立完整包格式，可分别使用 research verify 复核。")
    lines.append("本根目录同样支持 research verify --package DIR，逐字节复核全部交付内容。")
    lines.append("")
    lines.extend(f"- {note}" for note in NOTES)
    return ("\n".join(lines) + "\n").encode()


def build_workflow(request: dict[str, Any]) -> dict[str, bytes]:
    """Build only via existing public interfaces in an owned temporary root."""
    try:
        session = research_session.build_session(request)
        normalized = json.loads(session["manifest.json"])["request"]
        areas = ["session", "review", "audit"]
        with tempfile.TemporaryDirectory(prefix="m2-offline-workflow-") as runtime:
            root = Path(runtime)
            source = root / "session"
            source.mkdir()
            for name, payload in session.items():
                target = source / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(payload)
            research_review.export_review(source, root / "review")
            evidence_audit.export_audit(source, root / "audit")
            if normalized["compare_with"] is not None:
                session_compare.export_comparison(
                    source, source, root / "compare", right_view="compare_with"
                )
                areas.append("compare")
            files = {
                path.relative_to(root).as_posix(): path.read_bytes()
                for path in sorted(root.rglob("*"))
                if path.is_file()
            }
        files["index.md"] = _index(normalized, areas)
        entries = [
            {"path": name, "byte_count": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}
            for name, raw in sorted(files.items())
        ]
        files["manifest.json"] = _json_bytes(
            {
                "schema": MANIFEST_SCHEMA,
                "request": normalized,
                "packages": areas,
                "files": entries,
                "managed_file_count": len(entries),
                "total_file_count": len(entries) + 1,
                "total_byte_count": sum(entry["byte_count"] for entry in entries),
                "outer_manifest_is_integrity_inventory_only": True,
                "notes": list(NOTES),
            }
        )
        return files
    except (
        research_session.SessionError,
        research_review.ReviewError,
        evidence_audit.AuditError,
        session_compare.CompareError,
    ) as error:
        raise WorkflowError(error.code) from error
    except OSError as error:
        raise WorkflowError("COMPOSE_FAILED") from error


def _check_output(output: Path) -> None:
    if output.is_symlink() or output.exists():
        raise WorkflowError("OUTPUT_PATH_EXISTS")
    if any(parent.is_symlink() for parent in output.absolute().parents):
        raise WorkflowError("OUTPUT_PATH_INVALID")


def export_workflow(request: dict[str, Any], output: Path) -> dict[str, Any]:
    """Prebuild everything, then exclusively create a new output root.

    Publication is not atomic: a late write failure leaves owned partial output
    for inspection, never deletes caller paths, and returns no success result.
    """
    _check_output(output)
    files = build_workflow(request)
    _check_output(output)
    try:
        output.mkdir(parents=True, exist_ok=False)
    except FileExistsError as error:
        raise WorkflowError("OUTPUT_PATH_EXISTS") from error
    except OSError as error:
        raise WorkflowError("OUTPUT_WRITE_FAILED") from error
    try:
        for name, raw in sorted(files.items()):
            path = output / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)
    except OSError as error:
        raise WorkflowError("OUTPUT_WRITE_FAILED") from error
    return json.loads(files["manifest.json"])


class _Parser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise WorkflowError("INVALID_ARGUMENTS")


def main(argv: list[str] | None = None) -> int:
    parser = _Parser(description="一次生成完整离线研究交付目录", allow_abbrev=False)
    parser.add_argument("--as-of", required=True, metavar="DATE")
    parser.add_argument("--output", required=True, metavar="NEW_DIR")
    parser.add_argument("--compare-with", metavar="DATE")
    parser.add_argument("--year", action="append", type=int)
    parser.add_argument("--metric", action="append")
    parser.add_argument("--scope", default="consolidated")
    try:
        args = parser.parse_args(argv)
        manifest = export_workflow(
            {
                "as_of": args.as_of,
                "compare_with": args.compare_with,
                "years": args.year,
                "metrics": args.metric,
                "scope": args.scope,
            },
            Path(args.output),
        )
        text = f"exported complete workflow: {manifest['total_file_count']} files\n"
        sys.stdout.buffer.write(text.encode())
        sys.stdout.buffer.flush()
        return 0
    except SystemExit as error:
        return error.code if isinstance(error.code, int) else 2
    except Exception as error:  # noqa: BLE001 - no traceback or partial stdout
        code = error.code if isinstance(error, WorkflowError) else "UNEXPECTED_FAILURE"
        sys.stderr.buffer.write(f"error: {code}\n".encode())
        sys.stderr.buffer.flush()
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
