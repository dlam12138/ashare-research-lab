"""Compact reading of selected original comparisons without new calculations."""

from __future__ import annotations

from typing import Any

from ashare_research.tools import (
    comparison_focus,
    evidence_comparison,
    fact_comparison,
    session_compare,
)

SCHEMA = "m2_verified_comparison_summary_v1"
NOTE = "速览省略证据字段展开；JSON 的 source_report 保留完整原报告及全部证据缺口。"


def build_report(source: dict[str, Any]) -> dict[str, Any]:
    layers = [source]
    facts = source if source["schema"] == fact_comparison.SCHEMA else None
    current = source["comparison"] if facts is not None else source
    if facts is not None:
        layers.append(current)
    focused = current if current["schema"] == comparison_focus.SCHEMA else None
    selected = current["entries"]
    if focused is not None:
        current = focused["source_report"]
        layers.append(current)
    evidence = current if current["schema"] == evidence_comparison.SCHEMA else None
    if evidence is not None:
        current = evidence["comparison"]
        layers.append(current)
    if current["schema"] != session_compare.SCHEMA:
        raise session_compare.CompareError("INVALID_SUMMARY_SOURCE")
    keys = {(entry["metric_id"], entry["fiscal_year"]) for entry in selected}
    entries = [entry for entry in current["entries"]
               if (entry["metric_id"], entry["fiscal_year"]) in keys]
    sides = {side: {key: current[side][key] for key in (
        "symbol", "request", "selected_view", "selected_date", "scope",
        "session_manifest_sha256", "boundary", "metric_limitations",
    )} for side in ("left", "right")}
    notes = [NOTE, *(note for layer in layers for note in layer["notes"])]
    return {
        "schema": SCHEMA, "source_report": source, "sides": sides, "entries": entries,
        "source_key_count": len(current["entries"]), "selected_key_count": len(entries),
        "selection": focused["selection"] if focused is not None else None,
        "evidence_entries": selected if evidence is not None else None,
        "selected_input_role_count": sum(len(entry["inputs"]) for entry in selected)
        if evidence is not None else None,
        "facts": facts["facts"] if facts is not None else None,
        "fact_references": facts["references"] if facts is not None else None,
        "reference_count": facts["reference_count"] if facts is not None else None,
        "notes": list(dict.fromkeys(notes)),
    }


def _cell(value: Any) -> str:
    return str(value).replace("|", "\\|").replace("\r", " ").replace("\n", " ")


def render_markdown(report: dict[str, Any]) -> str:
    lines = ["# 已复核指标比较速览", ""]
    for side, label in (("left", "左"), ("right", "右")):
        block = report["sides"][side]
        request = block["request"]
        lines.extend([
            f"{label}：{_cell(block['symbol'])} / {_cell(block['selected_date'])} / "
            f"{_cell(block['selected_view'])} / {_cell(block['scope'])}。",
            f"档案清单 SHA256：`{_cell(block['session_manifest_sha256'])}`。", "",
            f"原请求：{request['as_of']} → {request['compare_with'] or '未请求对比'}；"
            f"年度：{', '.join(map(str, request['years']))}；"
            f"指标：{_cell(', '.join(request['metrics']))}。", "",
        ])
    selection = report["selection"]
    if selection is not None:
        lines.append(f"指标筛选：{_cell(', '.join(selection['metrics']) or '全部原选择')}；"
                     f"年度：{', '.join(map(str, selection['years'])) or '全部原选择'}；"
                     f"只看变化：{'是' if selection['changes_only'] else '否'}。")
    if report["facts"] is not None:
        lines.append(f"事实筛选：{', '.join(map(_cell, report['facts']))}。")
    lines.extend([f"显示指标键：{report['selected_key_count']} / {report['source_key_count']}。"])
    if report["selected_input_role_count"] is not None:
        lines.append(f"显示证据角色：{report['selected_input_role_count']}。")
    if report["reference_count"] is not None:
        lines.append(f"匹配原始直接引用：{report['reference_count']}。")
    if not report["entries"]:
        lines.extend(["", "当前选择没有匹配项。"])
    lines.extend(["", "| 年度 / 指标 | 原比较分类 | 左原值 / 单位 / 状态 |"
                  " 右原值 / 单位 / 状态 | 显示证据角色 |",
                  "| --- | --- | --- | --- | --- |"])
    roles = {(entry["metric_id"], entry["fiscal_year"]): entry["inputs"]
             for entry in report["evidence_entries"] or []}
    for entry in report["entries"]:
        selected_roles = roles.get((entry["metric_id"], entry["fiscal_year"]), [])
        role_text = ((", ".join(item["role"] for item in selected_roles) or "无显示角色")
                     if report["evidence_entries"] is not None else "未启用证据比较")
        cells = (f"{entry['fiscal_year']} / {entry['display_name_zh']}", entry["state_label_zh"],
                 session_compare._value(entry["before"]), session_compare._value(entry["after"]),
                 role_text)
        lines.append("| " + " | ".join(map(_cell, cells)) + " |")
    if report["fact_references"] is not None:
        lines.extend(["", "## 匹配的原始直接引用", "",
                      "| 左右 | 年度 / 指标 ID | 角色 | 事实 ID | 类型 / 父记录原状态 |",
                      "| --- | --- | --- | --- | --- |"])
        for ref in report["fact_references"]:
            kinds = ["指标输入" if kind == "input_fact" else "直接父引用"
                     for kind in ref["reference_kinds"]]
            details = ", ".join([*kinds, *(p["status"] for p in ref["matched_parents"])])
            cells = ("左" if ref["side"] == "before" else "右",
                     f"{ref['fiscal_year']} / {ref['metric_id']}", ref["role"], ref["fact_id"],
                     details)
            lines.append("| " + " | ".join(map(_cell, cells)) + " |")
    lines.extend(["", "## 原始限制与阅读边界", "", *(f"- {note}" for note in report["notes"])])
    return "\n".join(lines) + "\n"
