"""Compare original synthetic input diagnostics within an unchanged plan and domain."""

from __future__ import annotations

import argparse
import json
import sys
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
    parser.add_argument("--json", action="store_true")
    try:
        args = parser.parse_args(argv)
        report = build_report(
            Path(args.package if args.package is not None else args.archive),
            Path(args.left_inputs), Path(args.right_inputs), archive=args.archive is not None,
        )
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
