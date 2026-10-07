"""Compile explicit user hypothesis JSON through the frozen M4 compilers only."""

from __future__ import annotations

import argparse
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


def _load(source: Path) -> tuple[dict[str, Any], str]:
    try:
        with source.open("rb") as stream:
            payload = stream.read(MAX_INPUT_BYTES + 1)
    except OSError as error:
        raise PlanError("HYPOTHESIS_READ_FAILED") from error
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
    document, source_sha = _load(source)
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


class _Parser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise PlanError("INVALID_ARGUMENTS")


def main(argv: list[str] | None = None) -> int:
    parser = _Parser(description="从显式假设 JSON 编译冻结合同及研究要求", allow_abbrev=False)
    parser.add_argument("--hypothesis", required=True, metavar="JSON")
    parser.add_argument("--json", action="store_true")
    try:
        args = parser.parse_args(argv)
        report = build_report(Path(args.hypothesis))
        text = _json(report) + "\n" if args.json else render_markdown(report)
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
