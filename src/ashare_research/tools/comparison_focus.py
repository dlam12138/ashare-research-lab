"""Select original verified comparison keys and changed input roles for reading."""

from __future__ import annotations

from typing import Any

from ashare_research.tools import evidence_comparison, session_compare

SCHEMA = "m2_verified_focused_comparison_v1"
NOTES = (
    "筛选只改变阅读范围，完整原比较仍保留在 source_report 中。",
    "普通变化筛选沿用原指标状态；证据模式也保留输入字段变化，不解释原因。",
    "空结果只表示本次筛选没有匹配项，原报告限制保持不变。",
)


def validate_selectors(metrics: list[str] | None, years: list[int] | None) -> dict[str, list]:
    if any(not metric or not metric.strip() for metric in metrics or []):
        raise session_compare.CompareError("INVALID_ARGUMENTS")
    if any(year < 1 for year in years or []):
        raise session_compare.CompareError("INVALID_ARGUMENTS")
    return {"metrics": sorted(set(metrics or [])), "years": sorted(set(years or []))}


def build_report(
    source: dict[str, Any], *, metrics: list[str] | None = None,
    years: list[int] | None = None, changes_only: bool = False,
) -> dict[str, Any]:
    selection = {**validate_selectors(metrics, years), "changes_only": changes_only}
    evidence = source["schema"] == evidence_comparison.SCHEMA
    original = source["comparison"] if evidence else source
    available_metrics = {entry["metric_id"] for entry in original["entries"]}
    available_years = {entry["fiscal_year"] for entry in original["entries"]}
    if set(selection["metrics"]) - available_metrics:
        raise session_compare.CompareError("METRIC_NOT_COMPARED")
    if set(selection["years"]) - available_years:
        raise session_compare.CompareError("YEAR_NOT_COMPARED")
    entries = []
    for entry in source["entries"]:
        if selection["metrics"] and entry["metric_id"] not in selection["metrics"]:
            continue
        if selection["years"] and entry["fiscal_year"] not in selection["years"]:
            continue
        state = entry["metric_state"] if evidence else entry["state"]
        if evidence and changes_only:
            changed = [item for item in entry["inputs"] if item["field_changes"]]
            if state == "unchanged" and not changed:
                continue
            entry = {**entry, "inputs": changed}
        elif changes_only and state == "unchanged":
            continue
        entries.append(entry)
    return {
        "schema": SCHEMA, "mode": "evidence" if evidence else "metrics",
        "selection": selection, "source_report": source, "entries": entries,
        "source_key_count": len(source["entries"]), "selected_key_count": len(entries),
        "selected_input_role_count": sum(len(entry["inputs"]) for entry in entries)
        if evidence else None, "notes": list(NOTES),
    }


def render_markdown(report: dict[str, Any]) -> str:
    selection, source = report["selection"], report["source_report"]
    lines = ["# 聚焦研究档案比较", "",
             f"指标：{', '.join(selection['metrics']) or '全部原选择'}；"
             f"年度：{', '.join(map(str, selection['years'])) or '全部原选择'}；"
             f"只看变化：{'是' if selection['changes_only'] else '否'}。",
             f"匹配指标键：{report['selected_key_count']} / {report['source_key_count']}。", ""]
    evidence = report["mode"] == "evidence"
    original = source["comparison"] if evidence else source
    keys = {(entry["metric_id"], entry["fiscal_year"]) for entry in report["entries"]}
    metric_entries = [entry for entry in original["entries"]
                      if (entry["metric_id"], entry["fiscal_year"]) in keys]
    counts = dict.fromkeys(session_compare.LABELS, 0)
    for entry in metric_entries:
        counts[entry["state"]] += 1
    selected = {**original, "entries": metric_entries, "states": counts,
                "compared_key_count": len(metric_entries),
                "common_key_count": sum(entry["before"] is not None and entry["after"] is not None
                                        for entry in metric_entries)}
    if not keys:
        lines.extend(["当前选择没有匹配项。", ""])
    if evidence:
        view = {**source, "comparison": selected, "entries": report["entries"]}
        lines.append(f"显示输入角色：{report['selected_input_role_count']}。")
        rendered = evidence_comparison.render_markdown(view)
    else:
        rendered = session_compare.render_markdown(selected)
    lines.extend(["", rendered.rstrip(), "", "## 筛选边界", "",
                  *(f"- {note}" for note in report["notes"])])
    return "\n".join(lines) + "\n"
