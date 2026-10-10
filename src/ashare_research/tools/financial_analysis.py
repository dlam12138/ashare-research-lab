"""CLI：任意标的多年度 PIT 核心财务分析（显式只读事实数据库）。

# AI provenance: action=created; model=GPT-5; agent=Codex; date=2026-10-10

参数校验、只读边界与错误码全部由 ``ashare_research.financial_analysis`` 核心实现负责；
本模块只负责 argparse 解析、stdout 渲染与输出目录保护。违反选择的失败退出码 2，只向
stderr 输出净化后的稳定错误码，stdout 保持为空。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from ashare_research import financial_analysis as core


class _SanitizedParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:  # noqa: ARG002 - sanitized by design
        raise core.FinancialAnalysisError("INVALID_ARGUMENTS")


def _build_parser() -> argparse.ArgumentParser:
    parser = _SanitizedParser(
        prog="python -m ashare_research.tools.financial_analysis",
        description=(
            "在显式只读事实数据库上，用公开 PIT 门禁与既有 12 个指标定义计算多年核心财务画像。"
        ),
        add_help=True,
        allow_abbrev=False,
    )
    parser.add_argument(
        "--database", required=True, metavar="PATH", help="显式只读 DuckDB 事实数据库路径"
    )
    parser.add_argument("--symbol", required=True, metavar="SYMBOL", help="A 股代码，如 601857.SH")
    parser.add_argument("--as-of", required=True, metavar="ISO_DATE", help="PIT 时点（YYYY-MM-DD）")
    parser.add_argument("--compare-with", metavar="ISO_DATE", help="对比时点，不得早于 --as-of")
    parser.add_argument(
        "--year", required=True, action="append", type=int, metavar="YEAR", help="年度，可重复"
    )
    parser.add_argument(
        "--metric", action="append", metavar="METRIC_ID", help="既有指标 ID，可重复；默认全部 12 个"
    )
    parser.add_argument(
        "--scope",
        default="consolidated",
        metavar="SCOPE",
        help="合并范围口径：consolidated 或 parent_company",
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--json", action="store_true", help="输出规范 JSON 而非 Markdown")
    mode.add_argument("--output", metavar="NEW_DIR", help="导出新目录（report.md/json、manifest）")
    return parser


def _fail(code: str) -> int:
    payload = f"error: {code if code in core.KNOWN_ERROR_CODES else 'UNEXPECTED_FAILURE'}\n"
    sys.stderr.buffer.write(payload.encode("utf-8"))
    sys.stderr.buffer.flush()
    return 2


def main(argv: list[str] | None = None) -> int:
    """Entry point. Returns a process exit code; known failures print no stdout."""
    try:
        arguments = _build_parser().parse_args(sys.argv[1:] if argv is None else argv)
    except core.FinancialAnalysisError:
        return _fail("INVALID_ARGUMENTS")
    except SystemExit as exit_request:  # argparse help / usage
        return exit_request.code if isinstance(exit_request.code, int) else 2
    try:
        report = core.build_report(
            database=arguments.database,
            symbol=arguments.symbol,
            as_of=arguments.as_of,
            compare_with=arguments.compare_with,
            years=arguments.year,
            metrics=arguments.metric,
            scope=arguments.scope,
        )
        if arguments.output is not None:
            manifest = core.export_report(report, Path(arguments.output))
            text = (
                f"exported {manifest['managed_file_count']} managed files, "
                f"{manifest['total_byte_count']} bytes\n"
            )
        else:
            text = core.render_json(report) if arguments.json else core.render_markdown(report)
        sys.stdout.buffer.write(text.encode("utf-8"))
        sys.stdout.buffer.flush()
        return 0
    except core.FinancialAnalysisError as error:
        return _fail(error.code)
    except Exception:  # noqa: BLE001 - known failures are sanitized, never traced
        return _fail("UNEXPECTED_FAILURE")


if __name__ == "__main__":
    raise SystemExit(main())
