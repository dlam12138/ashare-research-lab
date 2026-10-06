"""Describe original input-binding differences in an already verified comparison."""

from __future__ import annotations

import json
from typing import Any

from ashare_research.tools import session_compare

SCHEMA = "m2_verified_input_evidence_comparison_v1"
NOTES = (
    "逐字段比较原始输入记录；字段变化不等于变化原因或证据质量判断。",
    "未选择指标、缺失输入、未记录字段与空值分别保留；没有补值或重新计算。",
    "只比较两边已请求的视图与指标；来源及未留存父记录的限制保持不变。",
)


def build_report(comparison: dict[str, Any]) -> dict[str, Any]:
    """Consume verified original rows only; never reopen either source."""
    entries = []
    for metric in comparison["entries"]:
        indexes = [{b["role"]: b for b in row["inputs"]} if row is not None else {}
                   for row in (metric["before"], metric["after"])]
        inputs = []
        for role in sorted(indexes[0].keys() | indexes[1].keys()):
            before, after = indexes[0].get(role), indexes[1].get(role)
            fields = []
            for key in sorted((before or {}).keys() | (after or {}).keys()):
                left_present = before is not None and key in before
                right_present = after is not None and key in after
                left_value, right_value = (before or {}).get(key), (after or {}).get(key)
                if left_present != right_present or left_value != right_value:
                    fields.append({
                        "field": key, "before_present": left_present,
                        "after_present": right_present, "before": left_value, "after": right_value,
                    })
            inputs.append({"role": role, "before": before, "after": after,
                           "before_binding_present": before is not None,
                           "after_binding_present": after is not None,
                           "field_changes": fields})
        entries.append({
            "metric_id": metric["metric_id"], "fiscal_year": metric["fiscal_year"],
            "metric_state": metric["state"], "metric_state_label_zh": metric["state_label_zh"],
            "before_metric_selected": metric["before"] is not None,
            "after_metric_selected": metric["after"] is not None, "inputs": inputs,
        })
    return {"schema": SCHEMA, "comparison": comparison, "entries": entries, "notes": list(NOTES)}


def _cell(value: Any) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def _binding(binding: dict | None, selected: bool) -> str:
    if not selected:
        return "指标未选择"
    if binding is None:
        return "角色未记录"
    value = binding.get("value_decimal")
    return (f"{binding['status']} / {value if value is not None else '缺失'} / "
            f"{binding.get('unit', '未记录单位')} / {binding.get('fact_id', '未选择事实')}")


def render_markdown(report: dict[str, Any]) -> str:
    # Keep the original financial comparison, units and classifications intact.
    lines = [session_compare.render_markdown(report["comparison"]).rstrip(), "",
             "## 逐角色原始输入证据对比", "",
             "| 年度 / 指标 / 角色 | 左状态 / 原始值 / 单位 / 事实 ID |"
             " 右状态 / 原始值 / 单位 / 事实 ID | 变化字段 |",
             "| --- | --- | --- | --- |"]
    for entry in report["entries"]:
        for item in entry["inputs"]:
            fields = ", ".join(field["field"] for field in item["field_changes"]) or "未变化"
            cells = (f"{entry['fiscal_year']} / {entry['metric_id']} / {item['role']}",
                     _binding(item["before"], entry["before_metric_selected"]),
                     _binding(item["after"], entry["after_metric_selected"]), fields)
            lines.append("| " + " | ".join(map(_cell, cells)) + " |")
    for entry in report["entries"]:
        for item in entry["inputs"]:
            lines.extend(["", f"### {entry['fiscal_year']} / {entry['metric_id']} / {item['role']}",
                          "", f"原指标比较类别：{entry['metric_state_label_zh']}。"])
            for side, label in (("before", "左"), ("after", "右")):
                binding = item[side]
                selected = entry[f"{side}_metric_selected"]
                lines.extend(["", f"{label}：{_binding(binding, selected)}"])
                if binding is not None:
                    evidence = {key: binding[key] for key in (
                        "source_reference", "missing_source_reference_fields", "parents",
                    ) if key in binding}
                    lines.extend(["", "原始来源及父记录：", "```json",
                                  json.dumps(evidence, ensure_ascii=False,
                                             sort_keys=True, indent=2),
                                  "```"])
            lines.extend(["", "原始变化字段（presence 区分未记录字段与空值）：", "```json",
                          json.dumps(item["field_changes"], ensure_ascii=False,
                                     sort_keys=True, indent=2), "```"])
    lines.extend(["", "## 证据比较边界", "", *(f"- {note}" for note in report["notes"])])
    return "\n".join(lines) + "\n"
