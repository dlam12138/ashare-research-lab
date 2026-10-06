"""Select compared original metric keys by direct input or parent fact references."""

from __future__ import annotations

from typing import Any

from ashare_research.tools import comparison_focus, session_compare

SCHEMA = "m2_verified_fact_comparison_v1"
NOTES = (
    "事实匹配按左右原始输入及直接父引用选择指标键，不推断间接依赖或变化原因。",
    "引用表列出匹配指标的原始引用；只看变化时也可包含未变化角色的引用。",
    "未留存父记录保持原状态；匹配引用不代表补齐证据或重新证明历史发布。",
)


def validate_facts(facts: list[str]) -> list[str]:
    if not facts or any(not fact or not fact.strip() for fact in facts):
        raise session_compare.CompareError("INVALID_ARGUMENTS")
    return sorted(set(facts))


def build_report(focused: dict[str, Any], facts: list[str]) -> dict[str, Any]:
    """Read only the original verified report already retained by the focus layer."""
    facts = validate_facts(facts)
    source = focused["source_report"]
    original = source["comparison"] if focused["mode"] == "evidence" else source
    references = []
    for entry in original["entries"]:
        for side in ("before", "after"):
            row = entry[side]
            if row is None:
                continue
            for binding in row["inputs"]:
                for fact in facts:
                    parents = [parent for parent in binding.get("parents", {}).get("entries", [])
                               if parent["fact_id"] == fact]
                    kinds = []
                    if binding.get("fact_id") == fact:
                        kinds.append("input_fact")
                    if parents:
                        kinds.append("direct_parent")
                    if kinds:
                        references.append({
                            "metric_id": entry["metric_id"], "fiscal_year": entry["fiscal_year"],
                            "side": side, "fact_id": fact, "role": binding["role"],
                            "reference_kinds": kinds, "input": binding, "matched_parents": parents,
                        })
    if set(facts) - {ref["fact_id"] for ref in references}:
        raise session_compare.CompareError("FACT_NOT_REFERENCED")
    matched = {(ref["metric_id"], ref["fiscal_year"]) for ref in references}
    entries = [entry for entry in focused["entries"]
               if (entry["metric_id"], entry["fiscal_year"]) in matched]
    selected_keys = {(entry["metric_id"], entry["fiscal_year"]) for entry in entries}
    references = [ref for ref in references
                  if (ref["metric_id"], ref["fiscal_year"]) in selected_keys]
    selected = {**focused, "entries": entries, "selected_key_count": len(entries),
                "selected_input_role_count": sum(len(entry["inputs"]) for entry in entries)
                if focused["mode"] == "evidence" else None}
    return {"schema": SCHEMA, "facts": facts, "comparison": selected,
            "references": references, "reference_count": len(references), "notes": list(NOTES)}


def _cell(value: Any) -> str:
    return str(value).replace("|", "\\|").replace("\r", " ").replace("\n", " ")


def render_markdown(report: dict[str, Any]) -> str:
    lines = ["# 按事实引用查看指标比较", "",
             f"事实 ID：{', '.join(map(_cell, report['facts']))}。",
             f"匹配原始引用：{report['reference_count']}。", "",
             comparison_focus.render_markdown(report["comparison"]).rstrip(), "",
             "## 匹配指标的原始直接引用", "",
             "| 左右 | 年度 / 指标 | 角色 | 事实 ID | 引用类型 | 匹配父记录原状态 |",
             "| --- | --- | --- | --- | --- | --- |"]
    for ref in report["references"]:
        kinds = ["指标输入" if kind == "input_fact" else "直接父引用"
                 for kind in ref["reference_kinds"]]
        parents = ", ".join(parent["status"] for parent in ref["matched_parents"])
        cells = ("左" if ref["side"] == "before" else "右",
                 f"{ref['fiscal_year']} / {ref['metric_id']}", ref["role"], ref["fact_id"],
                 ", ".join(kinds), parents or "无匹配父引用")
        lines.append("| " + " | ".join(map(_cell, cells)) + " |")
    lines.extend(["", "## 事实筛选边界", "", *(f"- {note}" for note in report["notes"])])
    return "\n".join(lines) + "\n"
