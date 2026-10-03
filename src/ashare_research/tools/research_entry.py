"""统一离线研究入口。

既有离线工作流及完整研究档案通过同一个顶层命令暴露：

    ashare-research research report   固定来源价值研究包 (value_research_bundle)
    ashare-research research facts    指定时点财务事实浏览器 (pit_fact_explorer)
    ashare-research research metrics  既有指标 PIT 重放 (pit_metric_replay)
    ashare-research research demo     冻结的合成机制演示 (synthetic_demo)
    ashare-research research session  完整研究档案及复核 (research_session)

本模块只做命令选择、帮助与惰性转发：每个子命令的参数列表原样交给对应模块既有的
``main(argv)``。参数校验、渲染、输出路径保护与错误码全部由既有工具实现负责；这里不复制
任何解析器，也不重新实现任何计算。

入口自身不读取配置、不初始化日志、数据服务或数据库，不联网，也不写默认数据库。全局
``--config``/``--debug`` 对离线入口没有任何作用，因此与 research 组合时一律以退出码 2
拒绝，而不是静默忽略。
"""

from __future__ import annotations

import importlib
import sys
from collections.abc import Sequence
from dataclasses import dataclass

__all__ = ["COMMANDS", "ResearchCommand", "main", "reject_global_options"]

PROG = "ashare-research research"
GLOBAL_OPTION_TOKENS = ("--config", "--debug")
USAGE_ERROR_EXIT = 2


@dataclass(frozen=True)
class ResearchCommand:
    """One existing offline workflow exposed by the unified entry."""

    name: str
    module: str
    summary: str
    usage: tuple[str, ...]


COMMANDS: tuple[ResearchCommand, ...] = (
    ResearchCommand(
        "workflow",
        "ashare_research.tools.research_workflow",
        "一次生成档案、速览、缺口台账与可选对比",
        ("--as-of DATE --output NEW_DIR [--compare-with DATE] [查询参数]",),
    ),
    ResearchCommand(
        "verify",
        "ashare_research.tools.package_verification",
        "完整导出包复核（含外层报告）",
        ("--package DIR [--json]",),
    ),
    ResearchCommand(
        "compare",
        "ashare_research.tools.session_compare",
        "两份已复核档案的指标对比",
        ("--left DIR --right DIR [--left-view / --right-view] [--json | --output NEW_DIR]",),
    ),
    ResearchCommand(
        "audit",
        "ashare_research.tools.evidence_audit",
        "指标输入证据缺口台账",
        ("--session DIR [--json | --output NEW_DIR]",),
    ),
    ResearchCommand(
        "review",
        "ashare_research.tools.research_review",
        "已复核档案研究速览",
        ("--session DIR [--json | --output NEW_DIR]",),
    ),
    ResearchCommand(
        "session",
        "ashare_research.tools.research_session",
        "完整研究档案及复核",
        (
            "--as-of YYYY-MM-DD [查询参数] --output NEW_DIR",
            "--verify DIR（使用已安装的兼容固定基线与代码复核）",
        ),
    ),
    ResearchCommand(
        "report",
        "ashare_research.tools.value_research_bundle",
        "固定来源价值研究包",
        ("--json | --output NEW_DIR | --verify DIR",),
    ),
    ResearchCommand(
        "facts",
        "ashare_research.tools.pit_fact_explorer",
        "指定时点财务事实浏览器",
        (
            "--as-of YYYY-MM-DD 必填",
            "--compare-with / --concept / --period-end / --scope / --json / --output 可选",
        ),
    ),
    ResearchCommand(
        "metrics",
        "ashare_research.tools.pit_metric_replay",
        "既有指标 PIT 重放",
        (
            "--as-of YYYY-MM-DD 必填",
            "--compare-with / --year / --metric / --scope / --json / --output 可选",
        ),
    ),
    ResearchCommand(
        "demo",
        "ashare_research.synthetic_demo",
        "冻结的合成机制演示",
        ("--json",),
    ),
)

_COMMANDS_BY_NAME = {item.name: item for item in COMMANDS}


def _usage_text() -> str:
    """Render the unified entry help without copying any subtool parser."""
    lines = [
        f"usage: {PROG} <command> [tool arguments...]",
        "",
        "统一离线研究入口：既有工作流与完整档案，参数原样转发给各自工具的 main(argv)。",
        "",
        "commands:",
    ]
    for item in COMMANDS:
        module_name = item.module.rsplit(".", 1)[-1]
        lines.append(f"  {item.name:<9}{item.summary} ({module_name})")
        lines.extend(f"           {usage}" for usage in item.usage)
    lines.extend(
        [
            "",
            "子命令自己的帮助、参数校验、输出与错误码由对应工具负责：",
            f"  {PROG} report --help",
            f"  {PROG} facts --help",
            f"  {PROG} metrics --help",
            f"  {PROG} demo --help",
            f"  {PROG} session --help",
            f"  {PROG} review --help",
            f"  {PROG} audit --help",
            f"  {PROG} compare --help",
            f"  {PROG} verify --help",
            f"  {PROG} workflow --help",
            "",
            "离线边界：入口不加载配置、不初始化日志或数据服务、不联网、不写默认数据库；",
            "子命令只读取仓库内固定报告、固定规范快照或纯合成输入，不获取新数据，",
            "也不产生评分、排名、建议或研究结论。",
            "全局 --config/--debug 与 research 组合会以退出码 2 拒绝，而不是静默忽略。",
        ]
    )
    return "\n".join(lines) + "\n"


USAGE = _usage_text()


def _write(stream, text: str) -> None:
    """Write UTF-8 bytes regardless of the ambient console encoding."""
    buffer = getattr(stream, "buffer", None)
    if buffer is None:
        stream.write(text)
        stream.flush()
        return
    buffer.write(text.encode("utf-8"))
    buffer.flush()


def _global_option(arguments: Sequence[str]) -> str | None:
    """Return the first global modifier that cannot apply to the offline entry."""
    for token in arguments:
        if token in GLOBAL_OPTION_TOKENS or token.startswith("--config="):
            return token
    return None


def _fail(message: str) -> int:
    _write(sys.stderr, f"error: {message}\nusage: {PROG} <command> [tool arguments...]\n")
    return USAGE_ERROR_EXIT


def reject_global_options(options: Sequence[str]) -> int:
    """Reject global modifiers combined with the research entry."""
    token = _global_option(options)
    if token is None:
        token = "unsupported modifier"
    token = token.split("=", 1)[0]
    return _fail(f"global option {token} cannot be combined with research")


def main(argv: Sequence[str] | None = None) -> int:
    """Select one offline workflow and delegate to its existing ``main``."""
    arguments = list(sys.argv[1:] if argv is None else argv)

    if not arguments or arguments[0] in ("-h", "--help"):
        _write(sys.stdout, USAGE)
        return 0

    global_option = _global_option(arguments)
    if global_option is not None:
        return reject_global_options([global_option])

    command = arguments[0]
    selected = _COMMANDS_BY_NAME.get(command)
    if selected is None:
        expected = ", ".join(item.name for item in COMMANDS)
        return _fail(f"unknown research command {command!r}; expected one of {expected}")

    module = importlib.import_module(selected.module)
    return module.main(arguments[1:])
