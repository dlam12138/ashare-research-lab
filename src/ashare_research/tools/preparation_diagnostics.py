"""Project verified synthetic preparation audits into a focused diagnostic view."""

from __future__ import annotations

import copy
import json
import re
from collections import Counter
from typing import Any

from ashare_research.tools.synthetic_prepare import PrepareError

SCHEMA = "m4_synthetic_preparation_diagnostics_v1"
ROLE_PATTERN = re.compile(r"(?:TARGET_OUTCOME|FACTOR|CONTROL_[0-9]{4})")
CELL_FIELDS = ("role", "valid", "reasons", "available_on", "source_record_id", "evidence_digest")


def validate_options(summary: bool, roles: list[str], gaps_only: bool) -> None:
    if not summary and (roles or gaps_only):
        raise PrepareError("INVALID_ARGUMENTS")
    if any(ROLE_PATTERN.fullmatch(role) is None for role in roles):
        raise PrepareError("INVALID_ROLE")


def build_summary(
    report: dict[str, Any], *, roles: list[str], gaps_only: bool,
) -> dict[str, Any]:
    validate_options(True, roles, gaps_only)
    dataset = report["dataset"]
    requested = set(roles)
    if requested - set(dataset["role_order"]):
        raise PrepareError("UNKNOWN_ROLE")
    selected = [role for role in dataset["role_order"] if not requested or role in requested]
    diagnostics = []
    for role in selected:
        cells = [cell for row in dataset["audit_rows"] for cell in row["cells"]
                 if cell["role"] == role]
        reasons = Counter(reason for cell in cells for reason in cell["reasons"])
        valid_count = sum(cell["valid"] for cell in cells)
        diagnostics.append({
            "role": role, "audited_dates": len(cells),
            "valid_cells": valid_count, "invalid_cells": len(cells) - valid_count,
            "reason_counts": dict(sorted(reasons.items())),
        })
    rows = []
    for row in dataset["audit_rows"]:
        cells = [
            {field: copy.deepcopy(cell[field]) for field in CELL_FIELDS}
            for cell in row["cells"]
            if cell["role"] in selected and (not gaps_only or not cell["valid"])
        ]
        if cells:
            rows.append({
                "trade_date": row["trade_date"],
                "globally_valid": all(cell["valid"] for cell in row["cells"]),
                "cells": cells,
            })
    matrix = report["matrix"]
    return {
        "schema": SCHEMA,
        "source_schema": report["schema"],
        "status": dataset["status"],
        "plan_identity": copy.deepcopy(report["plan_identity"]),
        "input_file_sha256": report["input_file_sha256"],
        "dataset_identity": {key: dataset[key] for key in (
            "source_contract_digest", "plan_digest", "input_digest",
            "domain_digest", "dataset_digest",
        )},
        "matrix_identity": None if matrix is None else {
            "matrix_digest": matrix["matrix_digest"],
            "row_count": len(matrix["rows"]), "column_count": len(matrix["columns"]),
        },
        "quality": copy.deepcopy(dataset["quality"]),
        "selection": {
            "role_order": selected, "gaps_only": gaps_only,
            "status": "MATCHED" if rows else "NO_MATCHING_GAPS",
            "shown_dates": len(rows), "shown_cells": sum(len(row["cells"]) for row in rows),
        },
        "role_diagnostics": diagnostics,
        "rows": rows,
        "boundary": dict(report["boundary"]),
        "notes": [
            *report["notes"],
            "角色计数覆盖所有原审计日期；筛选只改变明细展示，不改变全局质量或覆盖分母。",
            "计数仅描述合成输入审计记录，不是统计估计；速览不显示观测数值或矩阵单元。",
        ],
    }


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False)


def _cell(value: Any) -> str:
    text = str(value).replace("\r", " ").replace("\n", " ")
    return re.sub(r"([\\`*_{}\[\]()<>|])", r"\\\1", text)


def render_markdown(report: dict[str, Any]) -> str:
    quality = report["quality"]
    lines = [
        "# 合成输入质量诊断速览", "",
        f"全局准备状态：`{report['status']}`。",
        f"全局共同有效覆盖：{quality['coverage_numerator']}/{quality['coverage_denominator']}；"
        f"原门槛：{quality['coverage_gate']}。", "",
        "角色计数覆盖全部审计日期；缺口筛选只影响下方明细。", "",
        "| 角色 | 审计日期数 | 有效单元 | 无效单元 | 原原因计数 |",
        "| --- | --- | --- | --- | --- |",
    ]
    for item in report["role_diagnostics"]:
        values = [item[key] for key in ("role", "audited_dates", "valid_cells", "invalid_cells")]
        values.append(json.dumps(item["reason_counts"], sort_keys=True))
        lines.append("| " + " | ".join(map(_cell, values)) + " |")
    lines.extend(["", "## 选中诊断明细", ""])
    if not report["rows"]:
        lines.append("所选角色没有匹配的缺口；全局准备状态及质量门槛保持原样。")
    else:
        lines.extend([
            "| 日期 | 全局有效 | 角色 | 单元有效 | 原原因 | 可用日期 | 原记录 ID | 原证据摘要 |",
            "| --- | --- | --- | --- | --- | --- | --- | --- |",
        ])
        for row in report["rows"]:
            for cell in row["cells"]:
                values = [
                    row["trade_date"], row["globally_valid"], cell["role"], cell["valid"],
                    json.dumps(cell["reasons"]), cell["available_on"],
                    cell["source_record_id"], cell["evidence_digest"],
                ]
                lines.append("| " + " | ".join(map(_cell, values)) + " |")
    for title, value in (
        ("原始全局质量", quality), ("筛选范围", report["selection"]),
        ("输入与产物身份", {key: report[key] for key in (
            "plan_identity", "input_file_sha256", "dataset_identity", "matrix_identity",
        )}),
        ("读取与执行边界", report["boundary"]),
    ):
        lines.extend(["", f"## {title}", "", "```json", _json(value), "```"])
    lines.extend(["", "## 限制", "", *(f"- {note}" for note in report["notes"]), ""])
    return "\n".join(lines)
