"""Compare original synthetic input diagnostics within an unchanged plan and domain."""

from __future__ import annotations

import argparse
import copy
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

from ashare_research.mechanism.contract_compiler import ContractCompilationError
from ashare_research.mechanism.datasets import AdapterError
from ashare_research.mechanism.hypothesis_config import HypothesisConfigError
from ashare_research.mechanism.planning.matrix import MatrixError
from ashare_research.tools import preparation_diagnostics, synthetic_prepare
from ashare_research.tools.research_plan import PlanError
from ashare_research.tools.synthetic_prepare import PrepareError

SCHEMA = "m4_paired_synthetic_preparation_diagnostics_v1"
NOTES = (
    "只对比同一份复核计划及同一声明样本域下的虚构合成输入；未修补输入或摘要。",
    "有效性变化及计数只描述原审计单元，不代表统计效果、可估计或研究就绪。",
    "观测数值变化可能只表现为原证据摘要变化；本视图不显示观测值或矩阵单元。",
    "SYNTHETIC 标签、摘要一致或质量通过不证明真实来源，也不授权真实研究或 holdout。",
)
SUMMARY_SCHEMA = "m4_paired_synthetic_preparation_diagnostics_summary_v1"
TRANSITIONS = ("BECAME_VALID", "BECAME_INVALID", "DIAGNOSTIC_METADATA_CHANGED")
COUNT_FIELDS = (
    "compared_cells", "unchanged_cells", "became_valid_cells",
    "became_invalid_cells", "metadata_changed_cells",
)


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False)


def build_report(
    package: Path, left: Path, right: Path, *, archive: bool = False,
) -> dict[str, Any]:
    before_full = synthetic_prepare.build_report(package, left, archive=archive)
    # Only identical caller paths reuse a snapshot; aliases still pass the original link gate.
    after_full = (before_full if left == right else
                  synthetic_prepare.build_report(package, right, archive=archive))
    return build_report_from_reports(before_full, after_full)


def build_report_from_reports(
    before_full: dict[str, Any], after_full: dict[str, Any],
) -> dict[str, Any]:
    """Compare captured, fully reproduced preparation reports without further IO."""
    if before_full["plan_identity"] != after_full["plan_identity"]:
        raise PrepareError("COMPARISON_PLAN_MISMATCH")
    before_data, after_data = before_full["dataset"], after_full["dataset"]
    if (before_data["domain_digest"] != after_data["domain_digest"]
            or before_data["role_order"] != after_data["role_order"]
            or [row["trade_date"] for row in before_data["audit_rows"]] !=
            [row["trade_date"] for row in after_data["audit_rows"]]):
        raise PrepareError("COMPARISON_DOMAIN_MISMATCH")
    before = preparation_diagnostics.build_summary(before_full, roles=[], gaps_only=False)
    after = preparation_diagnostics.build_summary(after_full, roles=[], gaps_only=False)
    counts = {
        "compared_cells": 0, "unchanged_cells": 0, "became_valid_cells": 0,
        "became_invalid_cells": 0, "metadata_changed_cells": 0,
    }
    changes = []
    for left_row, right_row in zip(before["rows"], after["rows"], strict=True):
        for left_cell, right_cell in zip(left_row["cells"], right_row["cells"], strict=True):
            counts["compared_cells"] += 1
            if _json(left_cell) == _json(right_cell):
                counts["unchanged_cells"] += 1
                continue
            if not left_cell["valid"] and right_cell["valid"]:
                transition = "BECAME_VALID"
                counts["became_valid_cells"] += 1
            elif left_cell["valid"] and not right_cell["valid"]:
                transition = "BECAME_INVALID"
                counts["became_invalid_cells"] += 1
            else:
                transition = "DIAGNOSTIC_METADATA_CHANGED"
                counts["metadata_changed_cells"] += 1
            changes.append({
                "trade_date": left_row["trade_date"], "role": left_cell["role"],
                "transition": transition, "before": left_cell, "after": right_cell,
            })
    same_bytes = before["input_file_sha256"] == after["input_file_sha256"]
    same_input = before_data["input_digest"] == after_data["input_digest"]
    return {
        "schema": SCHEMA,
        "status": "compared_synthetic_diagnostics",
        "same_verified_plan": True, "same_declared_domain": True,
        "same_input_bytes": same_bytes, "same_bound_input_digest": same_input,
        "classification": (
            "IDENTICAL_INPUT_BYTES" if same_bytes else
            "CANONICALLY_EQUIVALENT_INPUTS" if same_input else "SYNTHETIC_INPUTS_CHANGED"
        ),
        "before": before, "after": after, "counts": counts, "changes": changes,
        "boundary": {key: value or after["boundary"][key]
                     for key, value in before["boundary"].items()},
        "notes": list(NOTES),
    }


def _side_summary(side: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": side["status"],
        "quality": copy.deepcopy(side["quality"]),
        "identity": {
            "plan_identity": copy.deepcopy(side["plan_identity"]),
            "input_file_sha256": side["input_file_sha256"],
            "dataset_identity": copy.deepcopy(side["dataset_identity"]),
            "matrix_identity": copy.deepcopy(side["matrix_identity"]),
        },
    }


def build_summary(report: dict[str, Any], *, roles: list[str]) -> dict[str, Any]:
    """Project a captured, fully verified comparison report without further IO."""
    preparation_diagnostics.validate_options(True, roles, False)
    role_order = list(report["before"]["selection"]["role_order"])
    requested = set(roles)
    if requested - set(role_order):
        raise PrepareError("UNKNOWN_ROLE")
    selected = [role for role in role_order if not requested or role in requested]
    diagnostics = {}
    for side in ("before", "after"):
        items = report[side]["role_diagnostics"]
        if [item["role"] for item in items] != role_order:
            raise PrepareError("COMPARISON_SUMMARY_MISMATCH")
        diagnostics[side] = {item["role"]: item for item in items}
    buckets: dict[str, Counter[str]] = {}
    for change in report["changes"]:
        role, transition = change["role"], change["transition"]
        if role not in role_order or transition not in TRANSITIONS:
            raise PrepareError("COMPARISON_SUMMARY_MISMATCH")
        buckets.setdefault(role, Counter())[transition] += 1
    totals = dict.fromkeys(COUNT_FIELDS, 0)
    role_summary = []
    for role in role_order:
        before, after = diagnostics["before"][role], diagnostics["after"][role]
        audited = before["audited_dates"]
        if audited != after["audited_dates"]:
            raise PrepareError("COMPARISON_SUMMARY_MISMATCH")
        counted = buckets.get(role, Counter())
        unchanged = audited - sum(counted.values())
        if unchanged < 0:
            raise PrepareError("COMPARISON_SUMMARY_MISMATCH")
        totals["compared_cells"] += audited
        totals["unchanged_cells"] += unchanged
        totals["became_valid_cells"] += counted["BECAME_VALID"]
        totals["became_invalid_cells"] += counted["BECAME_INVALID"]
        totals["metadata_changed_cells"] += counted["DIAGNOSTIC_METADATA_CHANGED"]
        if role in selected:
            role_summary.append({
                "role": role, "audited_dates": audited,
                "before_valid_cells": before["valid_cells"],
                "before_invalid_cells": before["invalid_cells"],
                "after_valid_cells": after["valid_cells"],
                "after_invalid_cells": after["invalid_cells"],
                "unchanged": unchanged, "became_valid": counted["BECAME_VALID"],
                "became_invalid": counted["BECAME_INVALID"],
                "metadata_changed": counted["DIAGNOSTIC_METADATA_CHANGED"],
            })
    if totals != report["counts"]:
        raise PrepareError("COMPARISON_SUMMARY_MISMATCH")
    changes = [copy.deepcopy(change) for change in report["changes"]
               if change["role"] in selected]
    return {
        "schema": SUMMARY_SCHEMA,
        "source_schema": report["schema"],
        "status": report["status"],
        "same_verified_plan": report["same_verified_plan"],
        "same_declared_domain": report["same_declared_domain"],
        "same_input_bytes": report["same_input_bytes"],
        "same_bound_input_digest": report["same_bound_input_digest"],
        "classification": report["classification"],
        "before": _side_summary(report["before"]),
        "after": _side_summary(report["after"]),
        "counts": copy.deepcopy(report["counts"]),
        "role_summary": role_summary,
        "selection": {
            "role_order": selected,
            "status": "MATCHED" if changes else "NO_MATCHING_CHANGES",
            "shown_changes": len(changes),
        },
        "changes": changes,
        "boundary": copy.deepcopy(report["boundary"]),
        "notes": [
            *report["notes"],
            "角色计数与全局审计计数完全一致；筛选只改变展示的角色与变更，"
            "不改变复核结果、质量、身份或读取边界。",
            "所选角色没有变化时明确提示；未知角色在完整对比后拒绝，不重新读取输入。",
        ],
    }


def render_markdown(
    report: dict[str, Any], *,
    source_legend: str = "--left-inputs 为修改前；--right-inputs 为修改后。",
) -> str:
    lines = [
        "# 合成输入诊断对比", "",
        source_legend, "",
        f"输入分类：`{report['classification']}`；计划及声明样本域一致。", "",
        "| 输入 | 原准备状态 | 原共同有效覆盖 | 原质量门槛 |",
        "| --- | --- | --- | --- |",
    ]
    for side in ("before", "after"):
        source = report[side]
        quality = source["quality"]
        lines.append(
            f"| {side} | {source['status']} | "
            f"{quality['coverage_numerator']}/{quality['coverage_denominator']} | "
            f"{quality['coverage_gate']} |"
        )
    lines.extend(["", "## 审计单元变更计数", "", "```json", _json(report["counts"]), "```", "",
                  "## 原始诊断变更", ""])
    if not report["changes"]:
        lines.append("无诊断单元变化；输入字节与绑定摘要是否一致见分类及原身份。")
    for change in report["changes"]:
        lines.extend(["```json", _json(change), "```", ""])
    for side in ("before", "after"):
        lines.extend(["", f"## {side} 原诊断与身份", "",
                      preparation_diagnostics.render_markdown(report[side])])
    lines.extend(["", "## 本次读取与执行边界", "", "```json", _json(report["boundary"]), "```",
                  "", *(f"- {note}" for note in report["notes"]), ""])
    return "\n".join(lines)


def render_summary_markdown(
    summary: dict[str, Any], *,
    source_legend: str = "--left-inputs 为修改前；--right-inputs 为修改后。",
) -> str:
    lines = [
        "# 准备诊断对比角色速览", "",
        source_legend, "",
        f"输入分类：`{summary['classification']}`；对比状态：`{summary['status']}`。", "",
        "| 侧 | 原准备状态 | 原共同有效覆盖 | 原质量门槛 |",
        "| --- | --- | --- | --- |",
    ]
    for side in ("before", "after"):
        item = summary[side]
        quality = item["quality"]
        lines.append(
            f"| {side} | {item['status']} | "
            f"{quality['coverage_numerator']}/{quality['coverage_denominator']} | "
            f"{quality['coverage_gate']} |"
        )
    lines.extend([
        "", "## 角色变更速览", "",
        f"角色范围：{len(summary['role_summary'])} 个；"
        f"展示变更：{summary['selection']['shown_changes']} 个"
        f"（{summary['selection']['status']}）。", "",
        "| 角色 | 审计日期数 | 修改前有效 | 修改前无效 | 修改后有效 | 修改后无效 "
        "| 未变化 | 转为有效 | 转为无效 | 原诊断变化 |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ])
    for item in summary["role_summary"]:
        lines.append("| " + " | ".join(str(item[key]) for key in (
            "role", "audited_dates", "before_valid_cells", "before_invalid_cells",
            "after_valid_cells", "after_invalid_cells", "unchanged", "became_valid",
            "became_invalid", "metadata_changed",
        )) + " |")
    lines.extend(["", "## 全局审计计数（完整对比原值）", "", "```json",
                  _json(summary["counts"]), "```", "", "## 选中角色变更", ""])
    if not summary["changes"]:
        lines.append("所选角色没有诊断单元变化；全局计数、质量、身份与边界保持原样。")
    for change in summary["changes"]:
        lines.extend(["```json", _json(change), "```", ""])
    lines.extend(["", "## 筛选范围", "", "```json", _json(summary["selection"]), "```"])
    identities = {
        "same_verified_plan": summary["same_verified_plan"],
        "same_declared_domain": summary["same_declared_domain"],
        "same_input_bytes": summary["same_input_bytes"],
        "same_bound_input_digest": summary["same_bound_input_digest"],
        "before": summary["before"]["identity"],
        "after": summary["after"]["identity"],
    }
    lines.extend(["", "## 输入与产物身份", "", "```json", _json(identities), "```"])
    lines.extend(["", "## 本次读取与执行边界", "", "```json", _json(summary["boundary"]),
                  "```", "", "## 限制", "",
                  *(f"- {note}" for note in summary["notes"]), ""])
    return "\n".join(lines)


class _Parser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise PrepareError("INVALID_ARGUMENTS")


def main(argv: list[str] | None = None) -> int:
    parser = _Parser(description="同一计划与声明样本域下的合成输入诊断对比", allow_abbrev=False)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--package", metavar="DIR")
    source.add_argument("--archive", metavar="ZIP")
    parser.add_argument("--left-inputs", required=True, metavar="JSON")
    parser.add_argument("--right-inputs", required=True, metavar="JSON")
    parser.add_argument("--summary", action="store_true")
    parser.add_argument("--role", action="append", default=[], metavar="ID")
    parser.add_argument("--json", action="store_true")
    try:
        args = parser.parse_args(argv)
        preparation_diagnostics.validate_options(args.summary, args.role, False)
        report = build_report(
            Path(args.package if args.package is not None else args.archive),
            Path(args.left_inputs), Path(args.right_inputs), archive=args.archive is not None,
        )
        if args.summary:
            summary = build_summary(report, roles=args.role)
            text = _json(summary) + "\n" if args.json else render_summary_markdown(summary)
        else:
            text = _json(report) + "\n" if args.json else render_markdown(report)
        sys.stdout.buffer.write(text.encode("utf-8"))
        sys.stdout.buffer.flush()
        return 0
    except SystemExit as error:
        return error.code if isinstance(error.code, int) else 2
    except Exception as error:  # noqa: BLE001 - sanitized, no partial stdout
        code = error.code if isinstance(error, (
            PrepareError, PlanError, AdapterError, MatrixError,
            HypothesisConfigError, ContractCompilationError,
        )) else "SYNTHETIC_COMPARISON_FAILED"
        sys.stderr.buffer.write(f"error: {code}\n".encode())
        sys.stderr.buffer.flush()
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
