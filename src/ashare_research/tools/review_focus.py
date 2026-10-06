"""Select original verified review rows; no arithmetic or new missingness labels."""

from __future__ import annotations

from typing import Any

from ashare_research.tools import delivered_research, research_review

SCHEMA = "m2_verified_focused_review_view_v1"
NOTES = (
    "缺失结果只指原记录 value 为 null，零值仍是有值结果。",
    "对比保留任一选中时点行对应的原始完整条目，另一时点可能已有值。",
    "各时点事实条数保留原速览总数，不是当前筛选行的输入事实数量。",
    "空选择不能证明指标或证据齐全；完整复核源和限制保留在 JSON 的 source_read。",
)


def validate_selectors(
    metrics: list[str] | None, years: list[int] | None,
) -> tuple[list[str], list[int]]:
    if any(not item.strip() for item in metrics or []) or any(year < 1 for year in years or []):
        raise delivered_research.ReadError("INVALID_ARGUMENTS")
    return sorted(set(metrics or [])), sorted(set(years or []))


def build_report(
    source_read: dict[str, Any], *, metrics: list[str] | None = None,
    years: list[int] | None = None, missing_only: bool = False,
) -> dict[str, Any]:
    metrics, years = validate_selectors(metrics, years)
    source = source_read["report"]
    if source_read["section"] != "review" or source["schema"] != research_review.SCHEMA:
        raise delivered_research.ReadError("INVALID_REVIEW_SOURCE")
    request = source["request"]
    if set(metrics) - set(request["metrics"]):
        raise delivered_research.ReadError("METRIC_NOT_SELECTED")
    if set(years) - set(request["years"]):
        raise delivered_research.ReadError("YEAR_NOT_SELECTED")
    views = []
    selected_keys = set()
    for view in source["views"]:
        rows = [row for row in view["rows"]
                if (not metrics or row["metric_id"] in metrics)
                and (not years or row["fiscal_year"] in years)
                and (not missing_only or row["value"] is None)]
        views.append({**view, "rows": rows})
        selected_keys.update((row["metric_id"], row["fiscal_year"]) for row in rows)
    comparison = source["comparison"]
    if comparison is not None:
        entries = [
            entry for entry in comparison["entries"]
            if (entry["metric_id"], entry["fiscal_year"]) in selected_keys
        ]
        comparison = {**comparison, "entries": entries, "states": {
            state: sum(entry["state"] == state for entry in entries)
            for state in comparison["states"]
        }}
    return {
        "schema": SCHEMA,
        "source_read": source_read,
        "selection": {"metrics": metrics, "years": years, "missing_only": missing_only},
        "review": {**source, "views": views, "comparison": comparison},
        "source_row_count": sum(len(view["rows"]) for view in source["views"]),
        "selected_row_count": sum(len(view["rows"]) for view in views),
        "selected_comparison_count": len(comparison["entries"]) if comparison else 0,
        "notes": list(NOTES),
    }


def render_markdown(report: dict[str, Any]) -> str:
    selection = report["selection"]
    metrics = ", ".join(selection["metrics"]) or "原请求全部指标"
    years = ", ".join(map(str, selection["years"])) or "原请求全部年度"
    lines = [
        "# 交付指标定向阅读", "",
        f"指标：{metrics}；年度：{years}；仅缺失结果：{selection['missing_only']}。", "",
        f"选中 {report['selected_row_count']} / {report['source_row_count']} 条时点指标行；"
        f"保留 {report['selected_comparison_count']} 条原始对比。", "",
    ]
    if not report["selected_row_count"]:
        lines.extend(["当前选择没有匹配项，不能据此判断指标或证据齐全。", ""])
    lines.extend(f"- {note}" for note in report["notes"])
    lines.extend(["", research_review.render_markdown(report["review"])])
    return "\n".join(lines)
