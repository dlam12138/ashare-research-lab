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
        "prepare-delivery-compare",
        "ashare_research.tools.preparation_delivery_compare",
        "完整复核两份准备目录或 ZIP，再对比同一计划与样本域的原质量诊断",
        ("(--left DIR | --left-archive ZIP) (--right DIR | --right-archive ZIP) [--json]",
         "对比可用 [--summary [--role ID（可重复）]]（完整复核后查看角色诊断变更）"),
    ),
    ResearchCommand(
        "prepare-package",
        "ashare_research.tools.preparation_package",
        "交付原计划与合成输入准备结果，并从保存字节复算核对",
        ("(--package PLAN_DIR | --plan-archive PLAN_ZIP) --inputs JSON\n"
         "  (--output NEW_DIR | --output-archive NEW_ZIP) [--json]",
         "--verify DIR [--json]（当前编译器与适配器复算，不授权统计执行）",
         "--archive PREPARATION_DIR --output NEW_ZIP [--json]",
         "--verify-archive ZIP [--json]（直接复核原生 ZIP，无需解压）",
         "复核可用 [--summary [--role ID（可重复）] [--gaps-only]]（完整复算后查看原诊断）"),
    ),
    ResearchCommand(
        "prepare-compare",
        "ashare_research.tools.preparation_compare",
        "对比同一计划及声明样本域下两份合成输入的原质量诊断",
        ("(--package DIR | --archive ZIP) --left-inputs JSON --right-inputs JSON [--json]",
         "对比可用 [--summary [--role ID（可重复）]]（完整复核后查看角色诊断变更）"),
    ),
    ResearchCommand(
        "prepare",
        "ashare_research.tools.synthetic_prepare",
        "用显式合成输入检查数据质量并准备设计矩阵（不执行统计）",
        ("(--package DIR | --archive ZIP) --inputs JSON [--json]",
         "[--summary [--role ID（可重复）] [--gaps-only]]（按角色查看原质量诊断）"),
    ),
    ResearchCommand(
        "plan-compare",
        "ashare_research.tools.research_plan_compare",
        "对比已复核研究计划的配置、合同与数据／方法要求（不执行）",
        ("(--left DIR | --left-archive ZIP) (--right DIR | --right-archive ZIP) [--json]",
         "对比可用 [--summary [--section config|contract|plan（可重复）]]（按分区查看变更）"),
    ),
    ResearchCommand(
        "plan",
        "ashare_research.tools.research_plan",
        "从显式假设配置编译冻结合同、分析计划和数据要求（不执行）",
        ("--hypothesis JSON [--output NEW_DIR] [--json]（V1 合成身份，不授权真实执行）",
         "--verify DIR [--json]（重新编译并复核计划包，不验证独立封存）",
         "--hypothesis JSON --archive NEW_ZIP [--json]（单文件 ZIP 交付）",
         "--verify-archive ZIP [--json]（直接复核原生 ZIP，无需解压）",
         "编译或复核可用 [--summary [--section ID（可重复）]]（投影本次捕获的计划视图）",
         "  速览 ID：requirements|sample|condition|method|conditional|bootstrap|"
         "robustness|evidence|holdout"),
    ),
    ResearchCommand(
        "registry-compare",
        "ashare_research.tools.research_registry_compare",
        "只读比较两个显式 M4-B registry 产物（record 或 snapshot，不写入）",
        ("--left JSON --right JSON [--json]（机械字段/记录差异，不判断对错）",),
    ),
    ResearchCommand(
        "registry",
        "ashare_research.tools.research_registry",
        "只读复核显式 M4-B 规范记录、registry 快照或状态转换预检（不写入）",
        ("--record JSON [--json]（复算记录规范字节、身份摘要、记录摘要与状态历史）",
         "--snapshot JSON [--json]（复算快照记录、计数、规范顺序与 registry 摘要）",
         "--record JSON --transition REQUEST.json [--json]（只读预检，不产生记录）"),
    ),
    ResearchCommand(
        "trace",
        "ashare_research.tools.metric_evidence_trace",
        "追溯指标输入，或按事实 ID 反查指标及直接父引用",
        ("(--package DIR | --archive ZIP) (--metric ID --year YEAR | --fact ID) [--json]",),
    ),
    ResearchCommand(
        "read",
        "ashare_research.tools.delivered_research",
        "直接阅读交付包内的指标速览、证据台账和指标对比",
        ("(--package DIR | --archive ZIP) --section review|audit|compare [--json]",
         "audit 可用 [--metric ID] [--year YEAR] [--fact ID]（可重复）[--gaps-only]\n"
         "review 可用 [--metric ID] [--year YEAR]（可重复）[--missing-only]"),
    ),
    ResearchCommand(
        "diff",
        "ashare_research.tools.package_byte_diff",
        "两份已复核目录或 ZIP 的文件内容差异",
        ("(--left DIR | --left-archive ZIP) (--right DIR | --right-archive ZIP) [--json]",),
    ),
    ResearchCommand(
        "deliver",
        "ashare_research.tools.research_delivery",
        "一次生成完整复核的研究 ZIP 交付文件",
        ("--as-of DATE --output NEW_ZIP [--compare-with DATE] [查询参数] [--json]",),
    ),
    ResearchCommand(
        "archive",
        "ashare_research.tools.package_archive",
        "研究包 ZIP 交付、完整复核与恢复",
        (
            "(--package DIR | --restore ZIP) --output NEW_PATH [--json]",
            "--verify ZIP [--json]（不创建恢复目录）",
        ),
    ),
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
        (
            "(--left SESSION_DIR | --left-archive ZIP)",
            "(--right SESSION_DIR | --right-archive ZIP)",
            "[--left-view / --right-view] [--json | --output NEW_DIR | --evidence [--json]]",
            "[--metric ID（可重复）] [--year YEAR（可重复）] [--changes-only]"
            "（不可与 --output 混用）",
            "[--fact ID（可重复，匹配原始输入及直接父引用，可组合上述筛选）]",
            "[--summary [--json]（值、分类、证据角色与直接引用速览，不与 --output 混用）]",
        ),
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
        "常用流程（日期是固定示例；路径请替换为实际位置，输出必须是新路径）：",
        f"  {PROG} deliver --as-of 2024-03-31 --year 2023 --output new-delivery.zip",
        f"  {PROG} archive --verify new-delivery.zip",
        f"  {PROG} diff --left-archive old.zip --right-archive new-delivery.zip",
        "完整交付指南：docs/m2_delivery_handoff.md",
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
            *(f"  {PROG} {item.name} --help" for item in COMMANDS),
            "",
            "离线边界：入口不加载配置、不初始化日志或数据服务、不联网、不写默认数据库；",
            "子命令只读取固定报告、规范快照、纯合成输入或显式假设配置，不获取新数据，",
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
