"""M2 既有已批准指标的指定时点（PIT）重放读取模型。

离线只读批处理：用公开的 ``pit_fact_explorer.build_report`` 取得两个查询时点通过公开 PIT 门禁的
精确十进制事实与来源追踪，再用仓库中**既有、已批准**的定义与 ``MetricEngine`` 在内存中重放七个
年度指标；不联网、不读调用方数据库、不写指标数据库、不修改既有文件，也不引入新公式、新口径、
评分、排名或研究阶段结论。

角色绑定按 ``input_roles`` / ``input_concept_ids``：``prior`` 与 ``opening`` 要求 FY-1，其余角色
要求 FY；流量概念要求年末 annual 期间，权益存量要求 instant 期间。缺失角色逐条列出所需概念与年度，
不依赖引擎的 ``missing_input_description``；值从来源 ``value_decimal`` 还原为 ``Decimal``；引擎
``available_at`` 不作为指标发布时间暴露，只给出 ``input_available_at_bound``（已知输入可得性上界）。
已知失败退出码 2，只向 stderr 输出净化后的稳定错误码，stdout 保持为空。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from ashare_research.exceptions import PointInTimeError
from ashare_research.facts.dates import validate_pit_date
from ashare_research.metrics.capital_return_definitions import CapitalReturnMetricDefinitionRegistry
from ashare_research.metrics.cashflow_definitions import CashFlowMetricDefinitionRegistry
from ashare_research.metrics.definitions import MetricDefinitionRegistry
from ashare_research.metrics.engine import MetricEngine, MetricInputError
from ashare_research.metrics.models import MetricDefinition
from ashare_research.tools import pit_fact_explorer

SYMBOL = "601857.SH"
ROE_METRIC_ID = "return_on_average_equity_attributable_to_parent"
# 既有注册表的七个指标（4 + 2 + 1），排序后即为唯一允许的 --metric 集合。
METRIC_IDS = tuple(
    [
        "cash_based_free_cash_flow_proxy",
        "cash_paid_for_fixed_assets_to_revenue",
        "net_profit_attributable_to_parent_yoy",
        "operating_cash_flow_to_attributable_net_profit",
        "operating_cash_flow_yoy",
        "revenue_yoy",
        "return_on_average_equity_attributable_to_parent",
    ]
)
DEFAULT_YEARS = (2021, 2022, 2023, 2024, 2025)
YEAR_RANGE = (2021, 2025)
SCOPES = ("consolidated", "parent_company")
PRIOR_ROLES = frozenset({"prior", "opening"})
PERIOD_TYPE_BY_CONCEPT = {
    "cash_paid_for_fixed_assets": "annual",
    "operating_cash_flow": "annual",
    "revenue": "annual",
    "net_profit_attributable_to_parent": "annual",
    "equity_attributable_to_parent": "instant",
}
REPLAY_CREATED_AT = "offline-replay-not-a-publication-time"
REVISION_REVIEW_STATUS = "offline_replay_unreviewed"
REPORT_SCHEMA = "m2_pit_metric_replay_report_v1"
MANIFEST_SCHEMA = "m2_pit_metric_replay_manifest_v1"
MANAGED_FILE_NAMES = ("report.md", "report.json")
MANIFEST_NAME = "manifest.json"
STATE_STATUS, STATE_VALUE = "status_changed", "value_changed"
STATE_INPUTS, STATE_UNCHANGED = "inputs_changed", "unchanged"
COMPARISON_STATES = (STATE_STATUS, STATE_VALUE, STATE_INPUTS, STATE_UNCHANGED)
STATE_LABELS_ZH = {
    STATE_STATUS: "状态变更",
    STATE_VALUE: "数值变更（重述）",
    STATE_INPUTS: "输入版本变更（数值未变）",
    STATE_UNCHANGED: "未变",
}
BINDING_FIELDS = [
    "fact_id",
    "concept_id",
    "period_end",
    "period_type",
    "consolidation_scope",
    "value_decimal",
    "unit",
    "raw_unit",
    "fact_version",
    "restatement_version",
    "available_at",
    "announcement_date",
    "filing_date",
    "verification_status",
]
INDEX_FIELDS = [
    "fact_id",
    "concept_id",
    "period_end",
    "period_type",
    "value_decimal",
    "unit",
    "fact_version",
    "restatement_version",
    "available_at",
]
RESULT_FIELDS = [
    "metric_result_id",
    "metric_id",
    "metric_definition_version",
    "symbol",
    "fiscal_year",
    "period_end",
    "result_version",
    "unit",
    "formula",
    "revision_review_status",
]
SIDE_FIELDS = ("metric_result_id", "status", "value", "unit", "input_available_at_bound")
ROLE_FIELDS = ("role", "concept_id", "fiscal_year", "fact_id")
LINEAGE_FIELDS = [
    "metric_result_id",
    "input_fact_id",
    "input_role",
    "input_fact_version",
    "input_restatement_version",
    "input_available_at",
]
MISSING_ABSENT = "absent_from_pit_selection"
MISSING_CONTEXT = "period_context_mismatch"
KNOWN_ERROR_CODES = frozenset(
    [
        "SOURCE_SNAPSHOT_MISSING",
        "SOURCE_DIGEST_MISMATCH",
        "SNAPSHOT_CONTRACT_UNEXPECTED",
        "SOURCE_VALUE_INVALID",
        "SELECTED_FACT_NOT_IN_SNAPSHOT",
        "INVALID_AS_OF_DATE",
        "INVALID_COMPARE_WITH",
        "COMPARE_BEFORE_AS_OF",
        "INVALID_YEAR",
        "UNKNOWN_METRIC",
        "INVALID_SCOPE",
        "METRIC_REGISTRY_INCOMPLETE",
        "METRIC_FACT_INVALID",
        "INVALID_ARGUMENTS",
        "OUTPUT_PATH_EXISTS",
        "OUTPUT_WRITE_FAILED",
        "UNEXPECTED_FAILURE",
    ]
)
NOTES = (
    "比率以小数表示（0.1 对应 10%），现金代理的金额单位保持万元。",
    f"`created_at` 不写入结果：重放不是发布，引擎只收到固定标记 `{REPLAY_CREATED_AT}`。",
    "不输出引擎 `available_at`；`input_available_at_bound` = 所选输入中最大的 `available_at`"
    "（无输入为 null），是输入可得性上界，不是指标发布时间。",
    f"`result_version=1` 是本读取模型约定，不是已存储历史指标版本；`revision_review_status` = "
    f"`{REVISION_REVIEW_STATUS}`。",
    "缺失角色以本工具 `missing_roles` 为准（角色/概念/年度逐条）；引擎 "
    "`engine_missing_input_description` 仅原样保留供审计。",
    "两个查询时点各自独立通过公开 PIT 门禁选择事实；未来事实与未来父事实永不进入选择。",
)
LIMITATIONS_ZH = (
    "只重放仓库中**既有已批准**的七个指标定义（4+2+1），不新增公式、口径、评分、排名或研究结论；"
    "`metric_id` 是既有引擎身份，不是新版本准入。",
    "现金口径自由现金流代理 = 经营活动现金流净额 − 购建长期资产支付的现金，是**现金代理**，"
    "不是估值、自由现金流贴现、股东自由现金流或 TTM 口径。",
    "ROE 用既有年度平均归母权益约定：归母净利润 ÷ (（期初 + 期末归母权益）/ 2)，期初取 FY-1 年末、"
    "期末取 FY 年末，合并口径年度值；不是 TTM，也不是 ROIC。",
    "快照只保留 33 条已对账事实及其直接 lineage；lineage 的 66 个 parent_fact_ids 全部不在快照内，"
    "原始披露证据无法复原，父事实逐条显式标记未解决。",
    "available_at 取自固定快照本身，只按公开 PIT 门禁使用，不重新证明原始可得性；created_at / "
    "recorded_at 是本地存储元数据，不是可得性证据。",
    "上下文是期间级元数据，filing_date/source_document 不一定对应当前重述版本；事实级日期与来源"
    "字段分别保留，缺失的 URL、摘要、页码与表名显式列出。",
    "快照只有 601857.SH、5 个概念、33 条事实且只有 consolidated 口径；--scope parent_company 如实"
    "返回空选择与 missing_input，不回退到合并口径或更晚时点。",
    "指标在内存中计算，不写 MetricRepository 或任何指标/事实数据库；报告与 manifest 是确定性 UTF-8 "
    "读取模型，不含当前时间戳，也不做数据获取或来源准入。",
)


class PitMetricReplayError(Exception):
    """A known, sanitized replay failure carrying one stable error code."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code if code in KNOWN_ERROR_CODES else "UNEXPECTED_FAILURE"


def metric_definitions() -> dict[str, MetricDefinition]:
    """Collect the seven existing approved definitions; never a new formula."""
    definitions = {item.metric_id: item for item in MetricDefinitionRegistry.list_all()}
    definitions.update({i.metric_id: i for i in CashFlowMetricDefinitionRegistry.list_all()})
    roe = CapitalReturnMetricDefinitionRegistry.get(ROE_METRIC_ID)
    if roe is not None:
        definitions[roe.metric_id] = roe
    if sorted(definitions) != sorted(METRIC_IDS):
        raise PitMetricReplayError("METRIC_REGISTRY_INCOMPLETE")
    return definitions


def validate_request(
    *,
    as_of: str,
    compare_with: str | None = None,
    years: list[int] | None = None,
    metrics: list[str] | None = None,
    scope: str = "consolidated",
) -> dict:
    """Validate every selector; there is no implicit today and no silent fallback."""
    metric_definitions()
    for value, code in ((as_of, "INVALID_AS_OF_DATE"), (compare_with, "INVALID_COMPARE_WITH")):
        if value is None and code == "INVALID_COMPARE_WITH":
            continue
        try:
            validate_pit_date(value, "date")
        except PointInTimeError as error:
            raise PitMetricReplayError(code) from error
    if compare_with is not None and compare_with < as_of:
        raise PitMetricReplayError("COMPARE_BEFORE_AS_OF")
    try:
        selected_years = sorted({int(year) for year in (years or DEFAULT_YEARS)})
    except (TypeError, ValueError) as error:
        raise PitMetricReplayError("INVALID_YEAR") from error
    if not selected_years or any(
        not YEAR_RANGE[0] <= year <= YEAR_RANGE[1] for year in selected_years
    ):
        raise PitMetricReplayError("INVALID_YEAR")
    selected_metrics = sorted({str(value) for value in (metrics or METRIC_IDS)})
    if not selected_metrics or any(value not in METRIC_IDS for value in selected_metrics):
        raise PitMetricReplayError("UNKNOWN_METRIC")
    if scope not in SCOPES:
        raise PitMetricReplayError("INVALID_SCOPE")
    return {
        "as_of": as_of,
        "compare_with": compare_with,
        "years": selected_years,
        "metrics": selected_metrics,
        "scope": scope,
    }


def _fiscal_year(period_end: str) -> int:
    return int(str(period_end)[:4])


def _restore_decimal(entry: dict[str, Any]) -> Decimal:
    try:
        value = Decimal(str(entry["value_decimal"]))
    except (InvalidOperation, KeyError, TypeError, ValueError) as error:
        raise PitMetricReplayError("SOURCE_VALUE_INVALID") from error
    if not value.is_finite():
        raise PitMetricReplayError("SOURCE_VALUE_INVALID")
    return value


def _engine_fact(entry: dict[str, Any], selection_date: str) -> dict[str, Any]:
    """Restore the exact decimal fact the public MetricEngine expects, in memory only."""
    fact = dict(entry)
    reference = dict(entry["source_reference"])
    reference["pit_selection_date"] = selection_date
    fact["source_reference"] = reference
    fact["source_tier"] = str(reference.get("source_tier") or "")
    fact["eligible_for_metrics"] = reference.get("eligible_for_metrics") is True
    fact["value"] = _restore_decimal(entry)
    fact["fiscal_year"] = _fiscal_year(entry["period_end"])
    return fact


def _role_binding(
    index: dict[tuple[str, int], list[Any]], role: str, concept_id: str, year: int, date: str
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    """Bind one role to its annual flow / instant equity fact for the required year."""
    entry = next(
        (
            item
            for item in index.get((concept_id, year), [])
            if item["period_end"] == f"{year}-12-31"
            and item["period_type"] == PERIOD_TYPE_BY_CONCEPT.get(concept_id)
        ),
        None,
    )
    if entry is None:
        reason = MISSING_CONTEXT if index.get((concept_id, year)) else MISSING_ABSENT
        return {
            "role": role,
            "concept_id": concept_id,
            "fiscal_year": year,
            "selection_date": date,
            "status": "missing",
            "reason": reason,
            "expected_period_end": f"{year}-12-31",
            "expected_period_type": PERIOD_TYPE_BY_CONCEPT.get(concept_id, ""),
        }, None
    binding = {
        "role": role,
        "concept_id": concept_id,
        "fiscal_year": year,
        "selection_date": date,
        "status": "present",
        "source_reference": dict(entry["source_reference"]),
        "missing_source_reference_fields": list(entry["missing_source_reference_fields"]),
        "context": dict(entry["context"]),
        "lineage": [dict(row) for row in entry["lineage"]],
        "parents": dict(entry["parents"]),
    }
    binding.update({field: entry[field] for field in BINDING_FIELDS})
    return binding, _engine_fact(entry, date)


def _serialize_result(result: Any) -> dict[str, Any]:
    """Serialize the existing engine identity/status/value without clock metadata."""
    record = {field: getattr(result, field) for field in RESULT_FIELDS}
    record["status"] = str(result.status)
    record["value"] = None if result.value is None else format(result.value, "f")
    record["input_fact_ids"] = list(result.input_fact_ids)
    record["engine_missing_input_description"] = result.missing_input_description
    return record


def _replay_metric(
    definition: MetricDefinition,
    fiscal_year: int,
    date: str,
    index: dict[tuple[str, int], list[Any]],
) -> dict[str, Any]:
    bindings: list[dict[str, Any]] = []
    facts: list[dict[str, Any] | None] = []
    roles = definition.input_roles
    for position, role in enumerate(roles):
        binding, fact = _role_binding(
            index,
            role,
            definition.input_concept_ids[position],
            fiscal_year - 1 if role in PRIOR_ROLES else fiscal_year,
            date,
        )
        bindings.append(binding)
        facts.append(fact)
    primary, secondary, tertiary = (facts + [None, None, None])[:3]
    try:
        result, lineage = MetricEngine.compute(
            definition,
            symbol=SYMBOL,
            fiscal_year=fiscal_year,
            primary_fact=primary,
            secondary_fact=secondary,
            tertiary_fact=tertiary if len(roles) >= 3 else None,
            missing_prior_is_history=(
                definition.formula == "(current / prior) - 1" and fiscal_year == 2021
            ),
            result_version=1,
            revision_review_status=REVISION_REVIEW_STATUS,
            as_of_date=date,
            created_at=REPLAY_CREATED_AT,
        )
    except MetricInputError as error:
        raise PitMetricReplayError("METRIC_FACT_INVALID") from error
    record = _serialize_result(result)
    present = [item["available_at"] for item in bindings if item["status"] == "present"]
    # input_available_at_bound = 已知输入可得性上界；不是指标发布时间。
    record.update(
        display_name_zh=definition.display_name_zh,
        input_roles=list(roles),
        input_concept_ids=list(definition.input_concept_ids),
        input_available_at_bound=max(present) if present else None,
        missing_roles=[i for i in bindings if i["status"] == "missing"],
        inputs=bindings,
    )
    record["missing_fiscal_years"] = sorted(
        {int(item["fiscal_year"]) for item in record["missing_roles"]}
    )
    record["lineage"] = [
        {field: getattr(row, field) for field in LINEAGE_FIELDS} for row in lineage
    ]
    return record


def _side_view(record: dict[str, Any] | None) -> dict[str, Any] | None:
    if record is None:
        return None
    view = {field: record[field] for field in SIDE_FIELDS}
    view["input_fact_ids"] = list(record["input_fact_ids"])
    view["input_roles"] = [{key: item.get(key) for key in ROLE_FIELDS} for item in record["inputs"]]
    return view


def _side_block(
    date: str,
    selections: list[dict[str, Any]],
    definitions: dict[str, MetricDefinition],
    request: dict,
) -> dict[str, Any]:
    index: dict[tuple[str, int], list[Any]] = {}
    for entry in selections:
        index.setdefault((entry["concept_id"], _fiscal_year(entry["period_end"])), []).append(entry)
    fact_rows = []
    for entry in selections:
        row = {field: entry[field] for field in INDEX_FIELDS}
        reference = entry["source_reference"]
        row.update(
            concept_label_zh=entry["concept_label_zh"],
            consolidation_scope=entry["consolidation_scope"],
            period_type=entry["period_type"],
            verification_status=entry["verification_status"],
            source_tier=str(reference.get("source_tier") or ""),
            eligible_for_metrics=reference.get("eligible_for_metrics") is True,
        )
        fact_rows.append(row)
    return {
        "date": date,
        "scope": request["scope"],
        "selection_count": len(selections),
        "selected_fact_index": fact_rows,
        "records": [
            _replay_metric(definitions[metric_id], int(year), date, index)
            for metric_id in request["metrics"]
            for year in request["years"]
        ],
    }


def build_comparison(
    before_records: list[dict[str, Any]], after_records: list[dict[str, Any]]
) -> dict[str, Any]:
    """Compare the two dates per metric/fiscal-year with exact decimal equality."""
    before = {(row["metric_id"], row["fiscal_year"]): row for row in before_records}
    after = {(row["metric_id"], row["fiscal_year"]): row for row in after_records}
    counts = dict.fromkeys(COMPARISON_STATES, 0)
    entries: list[dict[str, Any]] = []
    for key in sorted(set(before) | set(after)):
        left, right = before.get(key), after.get(key)
        state = STATE_UNCHANGED
        if left is None or right is None or left["status"] != right["status"]:
            state = STATE_STATUS
        elif (None if left["value"] is None else Decimal(left["value"])) != (
            None if right["value"] is None else Decimal(right["value"])
        ):
            state = STATE_VALUE
        elif left["input_fact_ids"] != right["input_fact_ids"]:
            state = STATE_INPUTS
        counts[state] += 1
        entries.append(
            {
                "metric_id": key[0],
                "display_name_zh": (left or right)["display_name_zh"],
                "fiscal_year": key[1],
                "state": state,
                "state_label_zh": STATE_LABELS_ZH[state],
                "before": _side_view(left),
                "after": _side_view(right),
            }
        )
    return {"states": counts, "entries": entries}


def build_report(request: dict[str, Any]) -> dict[str, Any]:
    """Validate selectors first, then read both PIT views and replay in memory."""
    validated = validate_request(
        as_of=request["as_of"],
        compare_with=request.get("compare_with"),
        years=request.get("years"),
        metrics=request.get("metrics"),
        scope=request.get("scope", "consolidated"),
    )
    definitions = metric_definitions()
    try:
        explorer = pit_fact_explorer.build_report(
            {
                "as_of": validated["as_of"],
                "compare_with": validated["compare_with"],
                "concepts": [],
                "period_end": None,
                "scope": validated["scope"],
            }
        )
    except pit_fact_explorer.PitExplorerError as error:
        raise PitMetricReplayError(error.code) from error
    as_of_block = _side_block(validated["as_of"], explorer["selections"], definitions, validated)
    compare_block, comparison = None, None
    if validated["compare_with"] is not None:
        compare_block = _side_block(
            validated["compare_with"], explorer["compare_selections"], definitions, validated
        )
        comparison = build_comparison(as_of_block["records"], compare_block["records"])
    return {
        "schema": REPORT_SCHEMA,
        "symbol": SYMBOL,
        "request": validated,
        "boundary": {
            "read_model_replay": True,
            "production_eligible": False,
            "score_eligible": False,
            "historical_metric_publication_proven": False,
            "stored_metric_version_admitted": False,
        },
        "selector_digest": hashlib.sha256(
            json.dumps(validated, ensure_ascii=False, sort_keys=True).encode("utf-8")
        ).hexdigest(),
        "source": dict(explorer["source"]),
        "notes": list(NOTES),
        "as_of": as_of_block,
        "compare_with": compare_block,
        "comparison": comparison,
        "limitations_zh": list(LIMITATIONS_ZH),
    }


def render_json(report: dict[str, Any]) -> str:
    return json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n"


def _table(header: tuple[str, ...], rows: list[tuple[str, ...]]) -> list[str]:
    lines = ["| " + " | ".join(header) + " |", "| " + " | ".join("---" for _ in header) + " |"]
    lines.extend("| " + " | ".join(row) + " |" for row in rows)
    return lines


def _metric_rows(record: dict[str, Any]) -> list[tuple[str, ...]]:
    """One record row plus one trace row per role: value/unit/version/available_at."""
    missing = (
        "；".join(
            f"{i['role']}={i['concept_id']}@{i['fiscal_year']}（{i['reason']}）"
            for i in record["missing_roles"]
        )
        or "—"
    )
    rows = [
        (
            record["display_name_zh"],
            str(record["fiscal_year"]),
            "结果",
            record["status"],
            record["value"] if record["value"] is not None else "—",
            record["unit"],
            record["metric_result_id"],
            f"formula={record['formula']}；"
            f"inputs={'、'.join(record['input_fact_ids']) or '—'}；"
            f"bound={record['input_available_at_bound'] or '—'}；missing={missing}",
        )
    ]
    for item in record["inputs"]:
        head = (record["display_name_zh"], str(record["fiscal_year"]), item["role"])
        if item["status"] == "present":
            reference = item["source_reference"]
            rows.append(
                head
                + (
                    "present",
                    item["value_decimal"],
                    item["unit"],
                    f"v{item['fact_version']}；{item['fact_id']}",
                    f"{item['available_at']}；{item['period_end']}/{item['period_type']}；"
                    f"tier={reference.get('source_tier', '')}；"
                    f"eligible={reference.get('eligible_for_metrics')}；"
                    f"lineage={len(item['lineage'])}；"
                    f"parents={item['parents']['total']}",
                )
            )
        else:
            rows.append(
                head
                + (
                    f"missing:{item['reason']}",
                    "—",
                    "—",
                    "—",
                    f"需要 {item['expected_period_end']}（{item['expected_period_type']}）",
                )
            )
    return rows


def _comparison_row(entry: dict[str, Any]) -> tuple[str, ...]:
    def columns(record: dict[str, Any] | None, label: str) -> tuple[str, str, str]:
        if record is None:
            return ("—", "—", "—")
        value = record["value"] if record["value"] is not None else "—"
        return (f"{label}:{record['status']}", value, record["metric_result_id"])

    return (
        entry["display_name_zh"],
        str(entry["fiscal_year"]),
        entry["state"],
        *columns(entry["before"], "before"),
        *columns(entry["after"], "after"),
    )


def render_markdown(report: dict[str, Any]) -> str:
    request, source = report["request"], report["source"]
    lines = [
        "# M2 既有指标 PIT 重放读取模型",
        "",
        "由 `python -m ashare_research.tools.pit_metric_replay` 离线生成，读取仓库内固定规范"
        "快照，用既有已批准定义与内存引擎重放七个年度指标；不联网、不读调用方数据库、不写指标"
        "数据库、不修改既有文件。",
        "",
        "结果是离线读取模型，未经新的指标版本、生产或评分准入。",
        "",
        f"- as-of 时点：{request['as_of']}；对比时点：{request['compare_with'] or '（未请求）'}；"
        f"标的：{report['symbol']}；口径：{request['scope']}",
        f"- 年度：{'、'.join(map(str, request['years']))}；指标：{'、'.join(request['metrics'])}",
        f"- 选择器摘要 SHA256：`{report['selector_digest']}`（确定性、无当前时间戳）",
        f"- 规范快照 contract：`{source['contract']}`，{source['row_count']} 条事实、"
        f"{source['concept_count']} 个概念、{source['context_count']} 个上下文、"
        f"{source['lineage_count']} 条 lineage，标的 {source['symbol']}；事实集 SHA256："
        f"`{source['fact_set_sha256']}`",
        "",
    ]
    lines += [f"- 来源文件 `{item['name']}` SHA256：`{item['sha256']}`" for item in source["files"]]
    lines += [""] + [f"- {note}" for note in report["notes"]]
    for block in (report["as_of"], report["compare_with"]):
        if block is None:
            continue
        lines += ["", f"## {block['date']}：PIT 选中事实 / 指标结果与输入追踪", ""]
        if not block["selected_fact_index"]:
            lines += ["- 所选口径下没有任何通过 PIT 门禁的事实（空结果如实保留，不回退）。"]
        else:
            lines += [
                f"- PIT 选中事实 {block['selection_count']} 条，完整索引见 report.json；"
                "本次所需输入逐角色列于下表。"
            ]
        lines += [""]
        lines += _table(
            (
                "指标",
                "年度",
                "角色/来源",
                "状态",
                "精确值",
                "单位",
                "版本与结果 ID",
                "可得日与来源证据",
            ),
            [row for record in block["records"] for row in _metric_rows(record)],
        )
    comparison = report["comparison"]
    lines += ["", "## 两时点对比（按指标/年度）", ""]
    if comparison is None:
        lines += ["未请求对比时点（未提供 `--compare-with`）。"]
    elif not comparison["entries"]:
        lines += ["两个时点均无指标记录，对比为空。"]
    else:
        counts = comparison["states"]
        lines += [
            f"{request['as_of']} → {request['compare_with']}，共 "
            f"{len(comparison['entries'])} 个指标/年度键："
            + "，".join(
                f"{STATE_LABELS_ZH[state]} {counts[state]} 个" for state in COMPARISON_STATES
            )
            + "。",
            "",
        ]
        lines += _table(
            ("指标", "年度", "状态", "前状态", "前值", "前结果 ID", "后状态", "后值", "后结果 ID"),
            [_comparison_row(entry) for entry in comparison["entries"]],
        )
        lines += [
            "",
            "「数值变更」用精确十进制数值比较得出；「输入版本变更」表示数值相等但选中的 "
            "`fact_id` 不同；缺失值保持 null/—，绝不当作 0。",
        ]
    lines += ["", "## 未解决证据与限制", ""]
    lines += [f"- {item}" for item in report["limitations_zh"]] + [""]
    return "\n".join(lines)


def build_manifest(report: dict[str, Any], files: dict[str, bytes]) -> dict[str, Any]:
    """Deterministic manifest: rendered hashes, source digests, selectors and fact ids."""
    entries = [
        {
            "path": name,
            "byte_count": len(files[name]),
            "sha256": hashlib.sha256(files[name]).hexdigest(),
        }
        for name in MANAGED_FILE_NAMES
    ]
    as_of, compare = report["as_of"], report["compare_with"]

    def ids(block: dict[str, Any] | None, section: str, field: str) -> list[str]:
        return [row[field] for row in block[section]] if block else []

    return {
        "schema": MANIFEST_SCHEMA,
        "report_schema": REPORT_SCHEMA,
        "managed_file_count": len(entries),
        "total_byte_count": sum(entry["byte_count"] for entry in entries),
        "files": entries,
        "request": report["request"],
        "selector_digest": report["selector_digest"],
        "source": report["source"],
        "selection": {
            "as_of": report["request"]["as_of"],
            "compare_with": report["request"]["compare_with"],
            "as_of_fact_ids": ids(as_of, "selected_fact_index", "fact_id"),
            "compare_with_fact_ids": ids(compare, "selected_fact_index", "fact_id"),
            "as_of_metric_result_ids": ids(as_of, "records", "metric_result_id"),
            "compare_with_metric_result_ids": ids(compare, "records", "metric_result_id"),
            "comparison_states": (report["comparison"]["states"] if report["comparison"] else {}),
        },
        "boundaries": {
            "network_used": False,
            "caller_database_read": False,
            "default_database_mutated": False,
            "metric_database_written": False,
            "new_formulas_introduced": False,
            "current_timestamp_recorded": False,
        },
    }


def export_report(report: dict[str, Any], output: Path) -> dict[str, Any]:
    """Render everything first, then claim the new output root with an exclusive mkdir."""
    files = {
        "report.md": render_markdown(report).encode("utf-8"),
        "report.json": render_json(report).encode("utf-8"),
    }
    manifest_bytes = (
        json.dumps(build_manifest(report, files), ensure_ascii=False, sort_keys=True, indent=2)
        + "\n"
    ).encode("utf-8")
    try:
        if output.is_symlink() or output.exists():
            raise PitMetricReplayError("OUTPUT_PATH_EXISTS")
        output.mkdir(parents=True, exist_ok=False)
    except FileExistsError as error:
        raise PitMetricReplayError("OUTPUT_PATH_EXISTS") from error
    except OSError as error:
        raise PitMetricReplayError("OUTPUT_WRITE_FAILED") from error
    try:
        for name in MANAGED_FILE_NAMES:
            (output / name).write_bytes(files[name])
        (output / MANIFEST_NAME).write_bytes(manifest_bytes)
    except OSError as error:
        # 迟到的 IO 失败保留已创建的自有目录，不做破坏性清理。
        raise PitMetricReplayError("OUTPUT_WRITE_FAILED") from error
    return json.loads(manifest_bytes.decode("utf-8"))


class _SanitizedParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:  # noqa: ARG002 - sanitized by design
        raise PitMetricReplayError("INVALID_ARGUMENTS")


def _build_parser() -> argparse.ArgumentParser:
    parser = _SanitizedParser(
        prog="python -m ashare_research.tools.pit_metric_replay",
        description="离线重放既有已批准年度指标的指定时点（PIT）读取模型。",
        add_help=True,
        allow_abbrev=False,
    )
    parser.add_argument("--as-of", required=True, metavar="ISO_DATE", help="PIT 时点（YYYY-MM-DD）")
    parser.add_argument("--compare-with", metavar="ISO_DATE", help="对比时点，不得早于 --as-of")
    parser.add_argument("--year", action="append", type=int, metavar="YEAR", help="年度，可重复")
    parser.add_argument(
        "--metric", action="append", metavar="METRIC_ID", help="既有指标 ID，可重复"
    )
    parser.add_argument(
        "--scope",
        default="consolidated",
        metavar="SCOPE",
        help="合并范围口径：consolidated 或 parent_company",
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--json", action="store_true", help="输出规范 JSON 而非 Markdown")
    mode.add_argument("--output", metavar="NEW_DIR", help="导出新目录（report.md/json、manifest）")
    return parser


def _fail(code: str) -> int:
    payload = f"error: {code if code in KNOWN_ERROR_CODES else 'UNEXPECTED_FAILURE'}\n"
    sys.stderr.buffer.write(payload.encode("utf-8"))
    sys.stderr.buffer.flush()
    return 2


def main(argv: list[str] | None = None) -> int:
    """Entry point.  Returns a process exit code; known failures print no stdout."""
    try:
        arguments = _build_parser().parse_args(sys.argv[1:] if argv is None else argv)
    except PitMetricReplayError:
        return _fail("INVALID_ARGUMENTS")
    except SystemExit as exit_request:  # argparse help / usage
        return exit_request.code if isinstance(exit_request.code, int) else 2
    try:
        report = build_report(
            validate_request(
                as_of=arguments.as_of,
                compare_with=arguments.compare_with,
                years=arguments.year,
                metrics=arguments.metric,
                scope=arguments.scope,
            )
        )
        if arguments.output is not None:
            manifest = export_report(report, Path(arguments.output))
            text = (
                f"exported {manifest['managed_file_count']} managed files, "
                f"{manifest['total_byte_count']} bytes\n"
            )
        else:
            text = render_json(report) if arguments.json else render_markdown(report)
        sys.stdout.buffer.write(text.encode("utf-8"))
        sys.stdout.buffer.flush()
        return 0
    except PitMetricReplayError as error:
        return _fail(error.code)
    except Exception:  # noqa: BLE001 - known failures are sanitized, never traced
        return _fail("UNEXPECTED_FAILURE")


if __name__ == "__main__":
    raise SystemExit(main())
