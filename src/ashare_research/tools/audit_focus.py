"""Filter original audit uses and omissions from a complete verified read envelope."""

from __future__ import annotations

from typing import Any

from ashare_research.tools import delivered_research, evidence_audit

SCHEMA = "m2_verified_focused_audit_view_v1"
NOTES = (
    "指标年度按原引用用途筛选，不把输入事实年度当作指标年度。",
    "只看缺口沿用原 gap 代码和缺失输入；空结果不表示证据齐全。",
    "事实筛选仅匹配已选择事实及直接父引用，缺失输入没有已选择事实 ID。",
)


def validate_selectors(
    metrics: list[str] | None, years: list[int] | None, facts: list[str] | None,
) -> dict[str, list]:
    if any(not value or not value.strip() for value in [*(metrics or []), *(facts or [])]):
        raise delivered_research.ReadError("INVALID_ARGUMENTS")
    if any(year < 1 for year in years or []):
        raise delivered_research.ReadError("INVALID_ARGUMENTS")
    return {"metrics": sorted(set(metrics or [])), "years": sorted(set(years or [])),
            "facts": sorted(set(facts or []))}


def _references(source: dict, facts: list[str]) -> list[dict]:
    references = []
    for item in source["source_facts"]:
        for fact_id in facts:
            parents = [parent for parent in item["fact"]["parents"]["entries"]
                       if parent["fact_id"] == fact_id]
            kinds = []
            if item["fact"]["fact_id"] == fact_id:
                kinds.append("input_fact")
            if parents:
                kinds.append("direct_parent")
            if kinds:
                references.append({"date": item["date"], "fact_id": item["fact"]["fact_id"],
                                   "requested_fact_id": fact_id, "reference_kinds": kinds,
                                   "matched_parents": parents})
    return references


def build_report(
    source_read: dict[str, Any], *, metrics: list[str] | None = None,
    years: list[int] | None = None, facts: list[str] | None = None, gaps_only: bool = False,
) -> dict[str, Any]:
    selection = {**validate_selectors(metrics, years, facts), "gaps_only": gaps_only}
    source = source_read["report"]
    if source_read["section"] != "audit" or source["schema"] != evidence_audit.SCHEMA:
        raise delivered_research.ReadError("INVALID_AUDIT_SOURCE")
    if set(selection["metrics"]) - set(source["request"]["metrics"]):
        raise delivered_research.ReadError("METRIC_NOT_SELECTED")
    if set(selection["years"]) - set(source["request"]["years"]):
        raise delivered_research.ReadError("YEAR_NOT_SELECTED")
    references = _references(source, selection["facts"])
    if set(selection["facts"]) - {ref["requested_fact_id"] for ref in references}:
        raise delivered_research.ReadError("FACT_NOT_REFERENCED")

    def selected_use(use: dict) -> bool:
        return ((not selection["metrics"] or use["metric_id"] in selection["metrics"])
                and (not selection["years"] or use["fiscal_year"] in selection["years"]))

    matching = {(ref["date"], ref["fact_id"]) for ref in references}
    selected = []
    for item in source["source_facts"]:
        uses = [use for use in item["uses"] if selected_use(use)]
        if not uses or gaps_only and not item["gaps"]:
            continue
        if selection["facts"] and (item["date"], item["fact"]["fact_id"]) not in matching:
            continue
        selected.append({**item, "uses": uses})
    selected_keys = {(item["date"], item["fact"]["fact_id"]) for item in selected}
    references = [ref for ref in references if (ref["date"], ref["fact_id"]) in selected_keys]
    missing = [item for item in source["missing_inputs"]
               if not selection["facts"] and selected_use(item["use"])]
    return {
        "schema": SCHEMA, "source_read": source_read, "selection": selection,
        "source_facts": selected, "missing_inputs": missing, "fact_references": references,
        "source_fact_row_count": len(source["source_facts"]),
        "selected_fact_row_count": len(selected),
        "selected_use_count": sum(len(item["uses"]) for item in selected),
        "source_missing_input_count": len(source["missing_inputs"]),
        "selected_missing_input_count": len(missing), "notes": [*source["notes"], *NOTES],
    }


def _cell(value: Any) -> str:
    return str(value).replace("|", "\\|").replace("\r", " ").replace("\n", " ")


def render_markdown(report: dict[str, Any]) -> str:
    request = report["source_read"]["report"]["request"]
    selection = report["selection"]
    lines = ["# 聚焦指标证据缺口", "",
             f"原查询：{request['as_of']} → {request['compare_with'] or '未请求对比'}；"
             f"口径：{_cell(request['scope'])}。",
             f"指标：{_cell(', '.join(selection['metrics']) or '全部原选择')}；"
             f"年度：{', '.join(map(str, selection['years'])) or '全部原选择'}；"
             f"事实：{_cell(', '.join(selection['facts']) or '全部原引用')}；"
             f"只看缺口：{'是' if selection['gaps_only'] else '否'}。", "",
             f"事实行：{report['selected_fact_row_count']} / {report['source_fact_row_count']}；"
             f"显示用途：{report['selected_use_count']}；"
             f"缺失输入：{report['selected_missing_input_count']} / "
             f"{report['source_missing_input_count']}。", "",
             "| 时点 / 原事实 ID | 事实年度 / 概念 | 原值 / 单位 | 原 gap 代码 |"
             " 来源缺失字段 / 未解决父数 | 指标年度 / 指标 / 角色 |",
             "| --- | --- | --- | --- | --- | --- |"]
    for item in report["source_facts"]:
        fact = item["fact"]
        uses = "；".join(f"{use['fiscal_year']} / {use['display_name_zh']} / {use['role']}"
                        for use in item["uses"])
        fields = ", ".join(fact["missing_source_reference_fields"]) or "未列出"
        cells = (f"{item['date']} / {fact['fact_id']}",
                 f"{fact['fiscal_year']} / {fact['concept_id']}",
                 f"{fact['value_decimal']} {fact['unit']}", ", ".join(item["gaps"]) or "未列出",
                 f"{fields} / {fact['parents']['unresolved']}", uses)
        lines.append("| " + " | ".join(map(_cell, cells)) + " |")
    lines.extend(["", "## 缺失输入角色", ""])
    for item in report["missing_inputs"]:
        use, expected = item["use"], item["expected_input"]
        lines.append(f"- {_cell(item['date'])} / {use['fiscal_year']} / "
                     f"{_cell(use['display_name_zh'])} / {_cell(use['role'])}："
                     f"缺少 {expected['fiscal_year']} 年 {_cell(expected['concept_id'])}，"
                     f"原原因 {_cell(expected['reason'])}；"
                     f"原指标状态 {_cell(use['metric_status'])}。")
    if not report["missing_inputs"]:
        lines.append("本次筛选没有匹配的缺失输入；来源及父记录缺口仍按原记录保留。")
    if not report["source_facts"] and not report["missing_inputs"]:
        lines.extend(["", "当前选择没有匹配项，不能据此判断证据齐全。"])
    if selection["facts"]:
        lines.extend(["", "## 匹配的原始直接引用", ""])
        for ref in report["fact_references"]:
            kinds = ["指标输入" if kind == "input_fact" else "直接父引用"
                     for kind in ref["reference_kinds"]]
            status = ", ".join(parent["status"] for parent in ref["matched_parents"])
            lines.append(f"- {_cell(ref['date'])} / {_cell(ref['requested_fact_id'])} → "
                         f"{_cell(ref['fact_id'])}：{', '.join(kinds)}"
                         f"{' / ' + _cell(status) if status else ''}。")
    lines.extend(["", "## 原台账边界", "", *(f"- {note}" for note in report["notes"]),
                  "- JSON 的 source_read 保留完整原台账、复核说明、来源字段及父记录。"])
    return "\n".join(lines) + "\n"
