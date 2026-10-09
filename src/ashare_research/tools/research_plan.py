"""Compile explicit user hypothesis JSON through the frozen M4 compilers only."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

from ashare_research.mechanism.contract_compiler import (
    ContractCompilationError,
    compile_hypothesis_config,
    config_to_canonical_dict,
    contract_to_canonical_dict,
)
from ashare_research.mechanism.hypothesis_config import (
    HypothesisConfigError,
    parse_hypothesis_config,
)
from ashare_research.mechanism.planning import build_analysis_plan, plan_to_canonical_dict

SCHEMA = "m4_compile_only_research_plan_view_v1"
MAX_INPUT_BYTES = 1_048_576
NOTES = (
    "当前 V1 只支持既有合成身份和假设词汇，未扩展真实数据语义。",
    "FROZEN 状态及摘要表示编译结果的内容身份，不是独立封存或执行授权。",
    "未校验来源、历史发布、数据覆盖或统计结果；研究就绪保持 false。",
    "合同中声明 holdout 窗口不会授权访问或执行 holdout。",
)
SUMMARY_SCHEMA = "m4_compile_only_plan_review_summary_v1"
SECTIONS = (
    "requirements", "sample", "condition", "method", "conditional",
    "bootstrap", "robustness", "evidence", "holdout",
)
BOUNDARY_KEYS = (
    "execution_authorized", "statistics_computed", "outcome_read",
    "holdout_accessed", "source_evidence_validated", "research_ready",
)
FROZEN_CONTRACT_STATE = "FROZEN_PRE_EXECUTION"
FROZEN_PLAN_STATE = "DETERMINISTIC_PRE_EXECUTION_PLAN"
SOURCE_LEGENDS = {
    "COMPILED_ONCE": "速览只投影本次编译一次捕获的计划视图；不重新编译，也不读取其他来源。",
    "VERIFIED_DIRECTORY_ONCE": "速览只投影本次目录完整复核一次的捕获报告；不重新读取或编译。",
    "VERIFIED_ARCHIVE_ONCE": "速览只投影本次原生 ZIP 完整复核一次的捕获报告；不重新读取或解压。",
}


class PlanError(Exception):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def _pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result = {}
    for key, value in pairs:
        if key in result:
            raise PlanError("DUPLICATE_JSON_KEY")
        result[key] = value
    return result


def _constant(value: str) -> None:
    raise PlanError("NONFINITE_JSON_NUMBER")


def read_hypothesis_bytes(source: Path) -> bytes:
    try:
        with source.open("rb") as stream:
            payload = stream.read(MAX_INPUT_BYTES + 1)
    except OSError as error:
        raise PlanError("HYPOTHESIS_READ_FAILED") from error
    if len(payload) > MAX_INPUT_BYTES:
        raise PlanError("HYPOTHESIS_TOO_LARGE")
    return payload


def _decode(payload: bytes) -> tuple[dict[str, Any], str]:
    if len(payload) > MAX_INPUT_BYTES:
        raise PlanError("HYPOTHESIS_TOO_LARGE")
    try:
        document = json.loads(
            payload.decode("utf-8"), object_pairs_hook=_pairs, parse_constant=_constant,
        )
    except (UnicodeError, ValueError, RecursionError) as error:
        raise PlanError("INVALID_HYPOTHESIS_JSON") from error
    if type(document) is not dict:
        raise PlanError("INVALID_HYPOTHESIS_ROOT")
    return document, hashlib.sha256(payload).hexdigest()


def build_report(source: Path) -> dict[str, Any]:
    return build_report_from_bytes(read_hypothesis_bytes(source))


def build_report_from_bytes(payload: bytes) -> dict[str, Any]:
    document, source_sha = _decode(payload)
    config = parse_hypothesis_config(document)
    contract = compile_hypothesis_config(config)
    plan = build_analysis_plan(contract)
    return {
        "schema": SCHEMA,
        "status": "compiled_pre_execution",
        "source_file_sha256": source_sha,
        "config": config_to_canonical_dict(config),
        "contract": contract_to_canonical_dict(contract),
        "plan": plan_to_canonical_dict(plan),
        "boundary": {
            "execution_authorized": False, "statistics_computed": False,
            "outcome_read": False, "holdout_accessed": False,
            "source_evidence_validated": False, "research_ready": False,
        },
        "notes": list(NOTES),
    }


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False)


def _changes(
    before: dict[str, Any], after: dict[str, Any], path: str = "",
) -> list[dict[str, Any]]:
    changes = []
    for key in sorted(before.keys() | after.keys()):
        pointer = path + "/" + key.replace("~", "~0").replace("/", "~1")
        left_present, right_present = key in before, key in after
        left, right = before.get(key), after.get(key)
        if left_present and right_present and type(left) is dict and type(right) is dict:
            changes.extend(_changes(left, right, pointer))
        elif left_present != right_present or _json(left) != _json(right):
            changes.append({
                "path": pointer, "before_present": left_present,
                "after_present": right_present, "before": left, "after": right,
            })
    return changes


def build_comparison(source: Path, comparison: Path) -> dict[str, Any]:
    before = build_report(source)
    after = before if source.resolve() == comparison.resolve() else build_report(comparison)
    changes = sorted(_changes(before["config"], after["config"]), key=lambda item: item["path"])
    same_bytes = before["source_file_sha256"] == after["source_file_sha256"]
    return {
        "schema": "m4_compile_only_plan_comparison_v1",
        "status": "compared_pre_execution",
        "same_source_bytes": same_bytes,
        "same_canonical_config": not changes,
        "classification": (
            "CANONICAL_CONFIG_CHANGED" if changes else
            "IDENTICAL_SOURCE_BYTES" if same_bytes else "CANONICALLY_EQUIVALENT_INPUTS"
        ),
        "before": before, "after": after, "changes": changes,
        "boundary": dict(before["boundary"]),
        "notes": [*NOTES, "变更列表只比较规范配置；列表顺序保留，不推断统计或研究效果。"],
    }


def render_comparison(report: dict[str, Any]) -> str:
    lines = [
        "# 假设研究计划对比（仅编译）", "",
        "--hypothesis 为修改前；--compare-with 为修改后。", "",
        f"分类：{report['classification']}；配置变更数：{len(report['changes'])}。",
        "", "## 规范配置变更", "",
    ]
    if report["changes"]:
        for change in report["changes"]:
            lines.extend([f"### `{_cell(change['path'])}`", "", "```json",
                          _json(change), "```", ""])
    else:
        lines.extend(["规范配置相同。源文件字节是否相同见分类和 SHA256。", ""])
    for label in ("before", "after"):
        lines.extend([f"## {label}", "", render_markdown(report[label])])
    lines.extend(["## 对比边界", "", "```json", _json(report["boundary"]), "```", "",
                  *(f"- {note}" for note in report["notes"])])
    return "\n".join(lines) + "\n"


def _cell(value: Any) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def render_markdown(report: dict[str, Any]) -> str:
    contract, plan = report["contract"], report["plan"]
    lines = [
        "# 假设研究计划（仅编译）", "",
        f"假设：{contract['hypothesis_id']}；状态：{contract['contract_state']}。", "",
        f"合同摘要：`{contract['contract_digest']}`", "",
        f"计划摘要：`{plan['plan_digest']}`", "",
        f"源文件 SHA256：`{report['source_file_sha256']}`", "",
        "## 所需数据", "",
        "| 角色 | 序列 | 转换 | 观测时序 | 主检验必需 | 有效性要求 |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for item in plan["dataset_requirements"]["requirements"]:
        cells = (item[key] for key in (
            "role", "series_id", "transform_semantics", "observation_timing",
            "required_for_primary", "validity_requirement",
        ))
        lines.append("| " + " | ".join(map(_cell, cells)) + " |")
    sections = (
        ("总体身份与成员要求", plan["dataset_requirements"]["universe_requirement"]),
        ("样本窗口与质量门槛", plan["sample_plan"]),
        ("条件定义", plan["transform_plan"]),
        ("统计方法与模型项", {"method": plan["analysis_method_id"], **plan["design_plan"]}),
        ("Bootstrap 计划", plan["bootstrap_plan"]),
        ("稳健性注册", plan["robustness_plan"]),
        ("证据判定要求", plan["evidence_plan"]),
        ("Holdout 边界", plan["holdout_boundary"]),
        ("本次执行状态", report["boundary"]),
    )
    for title, value in sections:
        lines.extend(["", f"## {title}", "", "```json", _json(value), "```"])
    lines.extend(["", "## 限制", "", *(f"- {note}" for note in report["notes"])])
    return "\n".join(lines) + "\n"


def validate_summary_options(summary: bool, sections: list[str]) -> None:
    if not summary and sections:
        raise PlanError("INVALID_ARGUMENTS")
    if any(section not in SECTIONS for section in sections):
        raise PlanError("INVALID_SECTION")


def _guard(condition: Any) -> None:
    if not condition:
        raise PlanError("PLAN_SUMMARY_MISMATCH")


def _summary_projection(report: dict[str, Any]) -> dict[str, Any]:
    """Fail closed unless a captured plan view keeps every frozen V1 invariant."""
    _guard(type(report) is dict)
    _guard(report["schema"] == SCHEMA and report["status"] == "compiled_pre_execution")
    boundary, contract, plan = report["boundary"], report["contract"], report["plan"]
    _guard(type(boundary) is dict and set(boundary) == set(BOUNDARY_KEYS))
    _guard(all(value is False for value in boundary.values()))
    _guard(type(contract) is dict and type(plan) is dict)
    _guard(contract["contract_state"] == FROZEN_CONTRACT_STATE)
    _guard(plan["plan_state"] == FROZEN_PLAN_STATE)
    _guard(
        type(contract["hypothesis_id"]) is str and contract["hypothesis_id"]
        and plan["hypothesis_id"] == contract["hypothesis_id"]
    )
    _guard(type(report["source_file_sha256"]) is str and report["source_file_sha256"])
    _guard(plan["source_contract_digest"] == contract["contract_digest"])
    for digest in (
        contract["contract_digest"], contract["source_config_digest"],
        plan["plan_digest"], plan["source_contract_digest"],
    ):
        _guard(type(digest) is str and digest)
    _guard(type(plan["analysis_method_id"]) is str and plan["analysis_method_id"])
    _guard(type(plan["dataset_requirements"]) is dict)
    requirements = plan["dataset_requirements"]["requirements"]
    _guard(type(requirements) is list and requirements)
    roles = []
    for item in requirements:
        _guard(type(item) is dict and type(item["role"]) is str and item["role"])
        roles.append(item["role"])
    _guard(len(set(roles)) == len(roles))
    design = plan["design_plan"]
    _guard(type(design) is dict and type(design["ordered_terms"]) is list)
    terms = []
    for term in design["ordered_terms"]:
        _guard(type(term) is dict and type(term["term_role"]) is str)
        terms.append(term)
    intercepts = [term for term in terms if term["term_role"] == "INTERCEPT"]
    indicators = [term for term in terms if term["term_role"] == "CONDITION_INDICATOR"]
    _guard(len(intercepts) == 1 and len(indicators) == 1)
    response = design["response_role"]
    _guard(type(response) is str and response in set(roles))
    other_sources = [
        term["source_series_role"] for term in terms
        if term["term_role"] not in ("INTERCEPT", "CONDITION_INDICATOR")
    ]
    _guard(all(type(source) is str for source in other_sources))
    _guard(sorted(other_sources) == sorted(role for role in roles if role != response))
    conditional = plan["conditional_summary_plan"]
    _guard(type(conditional) is dict)
    source_roles = conditional["source_roles"]
    _guard(type(source_roles) is dict and set(source_roles) == {"condition", "outcome"})
    _guard(source_roles["condition"] == indicators[0]["term_role"])
    _guard(source_roles["outcome"] == response)
    robustness = plan["robustness_plan"]["entries"]
    _guard(type(robustness) is list)
    enabled = plan["bootstrap_plan"]["enabled"]
    authorized = plan["holdout_boundary"]["execution_authorized"]
    _guard(type(enabled) is bool and type(authorized) is bool)
    notes = report["notes"]
    _guard(type(notes) is list and all(type(note) is str for note in notes))
    return {
        "identity": {
            "hypothesis_id": contract["hypothesis_id"],
            "source_file_sha256": report["source_file_sha256"],
            "contract_state": contract["contract_state"],
            "plan_state": plan["plan_state"],
            "contract_digest": contract["contract_digest"],
            "plan_digest": plan["plan_digest"],
            "source_config_digest": contract["source_config_digest"],
            "source_contract_digest": plan["source_contract_digest"],
        },
        "shape": {
            "requirement_roles": list(roles),
            "ordered_term_count": len(terms),
            "robustness_entry_count": len(robustness),
            "bootstrap_enabled": enabled,
            "holdout_authorized": authorized,
        },
        "payloads": {
            "requirements": copy.deepcopy(plan["dataset_requirements"]),
            "sample": copy.deepcopy(plan["sample_plan"]),
            "condition": copy.deepcopy(plan["transform_plan"]),
            "method": {
                "analysis_method_id": plan["analysis_method_id"],
                "design_plan": copy.deepcopy(plan["design_plan"]),
            },
            "conditional": copy.deepcopy(plan["conditional_summary_plan"]),
            "bootstrap": copy.deepcopy(plan["bootstrap_plan"]),
            "robustness": copy.deepcopy(plan["robustness_plan"]),
            "evidence": copy.deepcopy(plan["evidence_plan"]),
            "holdout": copy.deepcopy(plan["holdout_boundary"]),
        },
        "boundary": dict(boundary),
        "notes": list(notes),
    }


def build_summary(
    report: dict[str, Any], *, sections: list[str], source: str,
) -> dict[str, Any]:
    """Project one captured plan view; perform no IO and no recompilation."""
    validate_summary_options(True, sections)
    legend = SOURCE_LEGENDS.get(source)
    if legend is None:
        raise PlanError("INVALID_ARGUMENTS")
    try:
        projection = _summary_projection(report)
    except PlanError:
        raise
    except Exception as error:  # noqa: BLE001 - doctored captures fail closed
        raise PlanError("PLAN_SUMMARY_MISMATCH") from error
    requested = set(sections)
    selected = [section for section in SECTIONS if not requested or section in requested]
    return {
        "schema": SUMMARY_SCHEMA,
        "source_schema": report["schema"],
        "status": report["status"],
        "source": source,
        "identity": projection["identity"],
        "shape": projection["shape"],
        "selection": {"section_order": selected, "shown_sections": len(selected)},
        "sections": [
            {"section": section, "payload": projection["payloads"][section]}
            for section in selected
        ],
        "boundary": projection["boundary"],
        "notes": [*projection["notes"], legend],
    }


def render_summary_markdown(summary: dict[str, Any]) -> str:
    lines = [
        "# 研究计划速览（仅编译）", "",
        "计划已完整编译或复核一次；速览只投影本次捕获结果，未重新读取或计算。", "",
        "## 身份", "", "```json", _json(summary["identity"]), "```", "",
        "## 形状计数", "", "```json", _json(summary["shape"]), "```",
    ]
    for item in summary["sections"]:
        lines.extend([
            "", f"## {item['section']}", "", "```json", _json(item["payload"]), "```",
        ])
    for title, value in (
        ("选中分区", summary["selection"]),
        ("执行边界", summary["boundary"]),
    ):
        lines.extend(["", f"## {title}", "", "```json", _json(value), "```"])
    lines.extend(["", "## 限制", "", *(f"- {note}" for note in summary["notes"])])
    return "\n".join(lines) + "\n"


class _Parser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise PlanError("INVALID_ARGUMENTS")


def main(argv: list[str] | None = None) -> int:
    parser = _Parser(description="从显式假设 JSON 编译冻结合同及研究要求", allow_abbrev=False)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--hypothesis", metavar="JSON")
    source.add_argument("--verify", metavar="DIR")
    source.add_argument("--verify-archive", metavar="ZIP")
    output = parser.add_mutually_exclusive_group()
    output.add_argument("--output", metavar="NEW_DIR")
    output.add_argument("--archive", metavar="NEW_ZIP")
    parser.add_argument("--summary", action="store_true")
    parser.add_argument("--section", action="append", default=[], metavar="ID")
    parser.add_argument("--compare-with", metavar="JSON")
    parser.add_argument("--json", action="store_true")
    try:
        args = parser.parse_args(argv)
        if args.hypothesis is None and (args.output is not None or args.archive is not None):
            raise PlanError("INVALID_ARGUMENTS")
        if (args.output is not None or args.archive is not None) and (args.summary or args.section):
            raise PlanError("INVALID_ARGUMENTS")
        if args.compare_with is not None and (
            args.verify is not None or args.verify_archive is not None
            or args.output is not None or args.archive is not None
            or args.summary or args.section
        ):
            raise PlanError("INVALID_ARGUMENTS")
        validate_summary_options(args.summary, args.section)
        if args.archive is not None or args.verify_archive is not None:
            from ashare_research.tools import research_plan_archive

            if args.verify_archive is not None:
                receipt = research_plan_archive.verify_archive(Path(args.verify_archive))
                message = "verified compile-only plan archive\n"
                report, source = receipt["verification"]["report"], "VERIFIED_ARCHIVE_ONCE"
            else:
                receipt = research_plan_archive.export_archive(
                    Path(args.hypothesis), Path(args.archive),
                )
                message = "archived compile-only plan package (4 files)\n"
        elif args.verify is not None or args.output is not None:
            from ashare_research.tools import research_plan_package

            if args.verify is not None:
                if args.output is not None:
                    raise PlanError("INVALID_ARGUMENTS")
                receipt = research_plan_package.verify_package(Path(args.verify))
                message = "verified compile-only plan package\n"
                report, source = receipt["report"], "VERIFIED_DIRECTORY_ONCE"
            else:
                receipt = research_plan_package.export_package(
                    Path(args.hypothesis), Path(args.output),
                )
                message = "exported compile-only plan package (4 files)\n"
        elif args.compare_with is not None:
            report = build_comparison(Path(args.hypothesis), Path(args.compare_with))
            text = _json(report) + "\n" if args.json else render_comparison(report)
            sys.stdout.buffer.write(text.encode("utf-8"))
            sys.stdout.buffer.flush()
            return 0
        else:
            report = build_report(Path(args.hypothesis))
            if args.summary:
                summary = build_summary(report, sections=args.section, source="COMPILED_ONCE")
                text = _json(summary) + "\n" if args.json else render_summary_markdown(summary)
            else:
                text = _json(report) + "\n" if args.json else render_markdown(report)
            sys.stdout.buffer.write(text.encode("utf-8"))
            sys.stdout.buffer.flush()
            return 0
        if args.summary:
            summary = build_summary(report, sections=args.section, source=source)
            text = _json(summary) + "\n" if args.json else render_summary_markdown(summary)
        else:
            text = _json(receipt) + "\n" if args.json else message
        sys.stdout.buffer.write(text.encode("utf-8"))
        sys.stdout.buffer.flush()
        return 0
    except SystemExit as error:
        return error.code if isinstance(error.code, int) else 2
    except Exception as error:  # noqa: BLE001 - sanitized, no partial output
        code = (error.code if isinstance(error, (
            PlanError, HypothesisConfigError, ContractCompilationError,
        )) else "PLAN_COMPILATION_FAILED")
        sys.stderr.buffer.write(f"error: {code}\n".encode())
        sys.stderr.buffer.flush()
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
