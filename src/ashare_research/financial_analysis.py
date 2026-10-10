"""任意标的多年度 PIT 核心财务分析（显式只读事实数据库）。

# AI provenance: action=created; model=GPT-5; agent=Codex; date=2026-10-10

调用者显式指定只读 DuckDB 事实数据库、标的、as-of 时点、有界年度窗口与合并范围口径；
先用公开 PIT 门禁（``AsOfQuery.get_latest_available``）选出每个事实键在时点的最新可得
版本，再复用仓库**既有**的 12 个 MetricEngine 指标定义（4+2+4+2）在内存中计算多年核心
财务画像。只绑定年末年度流量与年末时点余额；缺失、不可比与不兼容输入都显式保留状态。

边界：不联网、不写数据库、不创建或迁移 schema、不读取默认数据库、不获取新数据、不生成
评分/排名/资格/建议，也不产生研究阶段结论。既有 DOUBLE 存储只在值为 2^53-1 以内有限
整数时精确使用；小数、越界、非万元单位或非 reconciled_derived 的输入逐条显式排除，
绝不四舍五入、强转或静默替代。已知失败以稳定错误码返回，不向 stdout 写部分结果。
"""

from __future__ import annotations

import contextlib
import hashlib
import json
import math
import re
from decimal import Decimal
from pathlib import Path
from typing import Any

import duckdb

from ashare_research.exceptions import PointInTimeError
from ashare_research.facts.as_of import AsOfQuery
from ashare_research.facts.concepts import ConceptRegistry
from ashare_research.facts.dates import validate_pit_date
from ashare_research.facts.repository import FactRepository
from ashare_research.metrics.capital_return_definitions import (
    CapitalReturnMetricDefinitionRegistry,
)
from ashare_research.metrics.cashflow_definitions import CashFlowMetricDefinitionRegistry
from ashare_research.metrics.definitions import MetricDefinitionRegistry
from ashare_research.metrics.earnings_quality_definitions import (
    EarningsQualityMetricDefinitionRegistry,
)
from ashare_research.metrics.engine import MetricEngine, MetricInputError
from ashare_research.metrics.models import MetricDefinition

REPORT_SCHEMA = "m2_core_financial_analysis_report_v1"
MANIFEST_SCHEMA = "m2_core_financial_analysis_manifest_v1"
MANAGED_FILE_NAMES: tuple[str, ...] = ("report.md", "report.json")
MANIFEST_NAME = "manifest.json"

SCOPES: tuple[str, ...] = ("consolidated", "parent_company")
YEAR_RANGE = (1990, 2100)
MAX_WINDOW_YEARS = 30
SYMBOL_PATTERN = re.compile(r"^\d{6}\.(SH|SZ)$")
SAFE_INTEGER_MAX = 2**53 - 1

# 既有注册表的 12 个指标（4 + 2 + 4 + 2），排序后即为唯一允许的 --metric 集合。
METRIC_IDS: tuple[str, ...] = (
    "cash_based_free_cash_flow_proxy",
    "cash_paid_for_fixed_assets_to_revenue",
    "gross_margin",
    "gross_profit",
    "net_profit_attributable_to_parent_yoy",
    "net_profit_excluding_non_recurring_yoy",
    "operating_cash_flow_to_attributable_net_profit",
    "operating_cash_flow_yoy",
    "operating_profit_margin",
    "return_on_average_equity_attributable_to_parent",
    "return_on_average_total_assets",
    "revenue_yoy",
)

PRIOR_ROLES = frozenset({"prior", "opening"})
MISSING_ABSENT = "absent_from_pit_selection"
MISSING_CONTEXT = "period_context_mismatch"
ROLE_EXCLUDED = "excluded_incompatible_input"

EXCLUDE_VALUE_NOT_EXACT_INTEGER = "value_not_exact_integer"
EXCLUDE_VALUE_OUT_OF_SAFE_RANGE = "value_out_of_safe_integer_range"
EXCLUDE_UNIT_NOT_WAN_YUAN = "unit_not_wan_yuan"
EXCLUDE_SOURCE_TIER = "source_tier_not_reconciled_derived"
EXCLUDE_CONTEXT_MISSING = "context_missing"
EXCLUDE_PERIOD_CONTEXT_MISMATCH = "period_context_mismatch"
EXCLUDE_PERIOD_END_INVALID = "period_end_invalid"
EXCLUSION_CODES: tuple[str, ...] = (
    EXCLUDE_VALUE_NOT_EXACT_INTEGER,
    EXCLUDE_VALUE_OUT_OF_SAFE_RANGE,
    EXCLUDE_UNIT_NOT_WAN_YUAN,
    EXCLUDE_SOURCE_TIER,
    EXCLUDE_CONTEXT_MISSING,
    EXCLUDE_PERIOD_CONTEXT_MISMATCH,
    EXCLUDE_PERIOD_END_INVALID,
)

PARENT_RESOLVED = "resolved_available_at_as_of"
PARENT_NOT_AVAILABLE = "retained_not_available_at_as_of"
PARENT_ABSENT = "absent_from_selected_database"

STATE_STATUS, STATE_VALUE = "status_changed", "value_changed"
STATE_INPUTS, STATE_UNCHANGED = "inputs_changed", "unchanged"
COMPARISON_STATES: tuple[str, ...] = (STATE_STATUS, STATE_VALUE, STATE_INPUTS, STATE_UNCHANGED)
STATE_LABELS_ZH = {
    STATE_STATUS: "状态变更",
    STATE_VALUE: "数值变更（重述）",
    STATE_INPUTS: "输入版本变更（数值未变）",
    STATE_UNCHANGED: "未变",
}
YOY_COMPUTED, YOY_NOT_COMPARABLE = "computed_delta", "not_comparable"
YOY_LABELS_ZH = {
    YOY_COMPUTED: "相邻年度算术差（描述性）",
    YOY_NOT_COMPARABLE: "不可比（相邻年度存在非 computed 状态）",
}

ANALYSIS_CREATED_AT = "offline-analysis-not-a-publication-time"
REVISION_REVIEW_STATUS = "offline_core_analysis_unreviewed"
ENGINE_FACT_UNIT = "万元"
ENGINE_SOURCE_TIER = "reconciled_derived"

KNOWN_ERROR_CODES = frozenset(
    {
        "INVALID_SYMBOL",
        "INVALID_AS_OF_DATE",
        "INVALID_COMPARE_WITH",
        "COMPARE_BEFORE_AS_OF",
        "INVALID_YEAR",
        "INVALID_SCOPE",
        "UNKNOWN_METRIC",
        "METRIC_REGISTRY_INCOMPLETE",
        "METRIC_FACT_INVALID",
        "DATABASE_NOT_FOUND",
        "DATABASE_OPEN_FAILED",
        "DATABASE_READ_FAILED",
        "DATABASE_SCHEMA_UNEXPECTED",
        "INVALID_ARGUMENTS",
        "OUTPUT_PATH_EXISTS",
        "OUTPUT_WRITE_FAILED",
        "UNEXPECTED_FAILURE",
    }
)

NOTES = (
    "指标结果来自既有 MetricEngine 与既有定义注册表；本模块不新增公式、口径或版本准入。",
    f"`created_at` 只收到固定标记 `{ANALYSIS_CREATED_AT}`；离线分析不是指标发布时间。",
    "不输出引擎 `available_at`；`input_available_at_bound` = 所选输入中最大的 `available_at`"
    "（无输入为 null），是输入可得性上界，不是指标发布时间，也不代表独立来源验证。",
    f"`result_version=1` 是读取模型约定；`revision_review_status` = `{REVISION_REVIEW_STATUS}`。",
    "数据库以只读方式在单个事务内打开；两次 PIT 视图读取共享同一只读快照。",
    "既有 DOUBLE 值只按 2^53-1 以内有限整数精确使用；不兼容输入逐条显式排除，不参与任何指标。",
    "缺失角色以本模块 `missing_roles` 为准（角色/概念/年度逐条）；引擎 "
    "`engine_missing_input_description` 仅原样保留供审计。",
    "相邻年度差值只是描述性算术差，不是趋势、显著性、评分或研究结论。",
)

LIMITATIONS_ZH = (
    "仅复用仓库中**既有**的 12 个指标定义（4+2+4+2）；没有新增公式、评分、排名、资格或建议，"
    "也没有 ROIC 替代、估值结论或价值兑现判断。",
    "调用者显式提供的数据库被当作事实输入；本模块不证明其内部数据的来源、可得性或独立性，"
    "也不重新验证 `available_at` 的真实性，只按公开 PIT 门禁使用它。",
    "输入值必须能由既有 DOUBLE 存储精确还原为 2^53-1 以内的整数（单位万元），否则逐条显式"
    "排除并保留排除原因；排除不是“缺失证据”，也不会触发任何替代、插值或回退。",
    "lineage 与父事实只来自所选数据库自身的 `fact_lineage` / `financial_facts`；未保留或未"
    "提供的原始披露证据无法在本工具内复原，父事实逐条给出解析状态。",
    "报告与 manifest 是确定性 UTF-8 读取模型，不含绝对路径与当前时间戳；文件摘要只证明内容"
    "一致性，不构成生产、评分、执行或研究授权。",
)


class FinancialAnalysisError(Exception):
    """A known, sanitized failure carrying one stable error code."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code if code in KNOWN_ERROR_CODES else "UNEXPECTED_FAILURE"


def metric_definitions() -> dict[str, MetricDefinition]:
    """Collect the twelve existing approved definitions; never a new formula."""
    definitions = {item.metric_id: item for item in MetricDefinitionRegistry.list_all()}
    definitions.update(
        {item.metric_id: item for item in CashFlowMetricDefinitionRegistry.list_all()}
    )
    definitions.update(
        {item.metric_id: item for item in EarningsQualityMetricDefinitionRegistry.list_all()}
    )
    definitions.update(
        {
            item.metric_id: item
            for item in CapitalReturnMetricDefinitionRegistry.list_all(include_roa=True)
        }
    )
    if sorted(definitions) != list(METRIC_IDS):
        raise FinancialAnalysisError("METRIC_REGISTRY_INCOMPLETE")
    for definition in definitions.values():
        if len(definition.input_concept_ids) != len(definition.input_roles):
            raise FinancialAnalysisError("METRIC_REGISTRY_INCOMPLETE")
        for concept_id in definition.input_concept_ids:
            if not ConceptRegistry.is_registered(concept_id):
                raise FinancialAnalysisError("METRIC_REGISTRY_INCOMPLETE")
    return definitions


def _expected_period_type(concept_id: str) -> str:
    return "instant" if ConceptRegistry.is_instant(concept_id) else "annual"


def validate_request(
    *,
    symbol: str,
    as_of: str,
    compare_with: str | None = None,
    years: list[int] | None = None,
    metrics: list[str] | None = None,
    scope: str = "consolidated",
) -> dict[str, Any]:
    """Validate every selector before any database path is touched."""
    metric_definitions()
    if not isinstance(symbol, str) or not SYMBOL_PATTERN.match(symbol):
        raise FinancialAnalysisError("INVALID_SYMBOL")
    for value, code in ((as_of, "INVALID_AS_OF_DATE"), (compare_with, "INVALID_COMPARE_WITH")):
        if value is None and code == "INVALID_COMPARE_WITH":
            continue
        try:
            validate_pit_date(value, "date")
        except PointInTimeError as error:
            raise FinancialAnalysisError(code) from error
    if compare_with is not None and compare_with < as_of:
        raise FinancialAnalysisError("COMPARE_BEFORE_AS_OF")
    try:
        selected_years = sorted({int(year) for year in (years or [])})
    except (TypeError, ValueError) as error:
        raise FinancialAnalysisError("INVALID_YEAR") from error
    if (
        not selected_years
        or len(selected_years) > MAX_WINDOW_YEARS
        or any(not YEAR_RANGE[0] <= year <= YEAR_RANGE[1] for year in selected_years)
    ):
        raise FinancialAnalysisError("INVALID_YEAR")
    selected_metrics = sorted({str(value) for value in (metrics or METRIC_IDS)})
    if not selected_metrics or any(value not in METRIC_IDS for value in selected_metrics):
        raise FinancialAnalysisError("UNKNOWN_METRIC")
    if scope not in SCOPES:
        raise FinancialAnalysisError("INVALID_SCOPE")
    return {
        "symbol": symbol,
        "as_of": as_of,
        "compare_with": compare_with,
        "years": selected_years,
        "metrics": selected_metrics,
        "scope": scope,
    }


def _needed_concepts(metrics: list[str]) -> tuple[str, ...]:
    definitions = metric_definitions()
    concepts = {
        concept_id
        for metric_id in metrics
        for concept_id in definitions[metric_id].input_concept_ids
    }
    return tuple(sorted(concepts))


class _ReadOnlyFactStore:
    """Minimal store adapter: one read-only DuckDB connection, no schema work."""

    def __init__(self, database: Path) -> None:
        self.database = database
        try:
            self._connection = duckdb.connect(str(database), read_only=True)
        except duckdb.Error as error:
            raise FinancialAnalysisError("DATABASE_OPEN_FAILED") from error

    def connect(self) -> duckdb.DuckDBPyConnection:
        return self._connection

    def close(self) -> None:
        self._connection.close()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError as error:
        raise FinancialAnalysisError("DATABASE_READ_FAILED") from error
    return digest.hexdigest()


def _fiscal_year(period_end: Any) -> int | None:
    text = str(period_end or "")
    if re.match(r"^\d{4}-\d{2}-\d{2}$", text):
        return int(text[:4])
    return None


def _select_rows(
    store: _ReadOnlyFactStore, *, symbol: str, date: str, scope: str, concepts: tuple[str, ...]
) -> list[dict[str, Any]]:
    query = AsOfQuery(FactRepository(store))
    try:
        frame = query.get_latest_available(
            symbol=symbol,
            as_of_date=date,
            concept_ids=list(concepts),
            consolidation_scope=scope,
        )
        return frame.to_dict(orient="records")
    except duckdb.Error as error:
        raise FinancialAnalysisError("DATABASE_READ_FAILED") from error


def _read_frame(store: _ReadOnlyFactStore, sql: str, params: list[Any]) -> list[dict[str, Any]]:
    try:
        return store.connect().execute(sql, params).df().to_dict(orient="records")
    except duckdb.CatalogException as error:
        raise FinancialAnalysisError("DATABASE_SCHEMA_UNEXPECTED") from error
    except duckdb.Error as error:
        raise FinancialAnalysisError("DATABASE_READ_FAILED") from error


def _load_contexts(
    store: _ReadOnlyFactStore, context_ids: list[str]
) -> dict[str, dict[str, Any]]:
    if not context_ids:
        return {}
    placeholders = ", ".join(["?"] * len(context_ids))
    rows = _read_frame(
        store,
        "SELECT context_id, fiscal_year, period_type, period_start, period_end, "
        "instant_or_duration, consolidation_scope, accounting_standard, "
        "restatement_version, source_document, filing_date "
        f"FROM fact_contexts WHERE context_id IN ({placeholders})",
        list(context_ids),
    )
    return {str(row["context_id"]): row for row in rows}


def _load_lineage(
    store: _ReadOnlyFactStore, fact_ids: list[str]
) -> dict[str, list[dict[str, Any]]]:
    if not fact_ids:
        return {}
    placeholders = ", ".join(["?"] * len(fact_ids))
    rows = _read_frame(
        store,
        "SELECT lineage_id, fact_id, run_id, source_provider, source_tier, source_method, "
        "parent_fact_ids, role, reconciliation_rule_id, reconciliation_rule_version, recorded_at "
        f"FROM fact_lineage WHERE fact_id IN ({placeholders}) ORDER BY lineage_id",
        list(fact_ids),
    )
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        grouped.setdefault(str(row["fact_id"]), []).append(row)
    return grouped


def _resolve_parents(
    store: _ReadOnlyFactStore, parent_ids: list[str], as_of: str
) -> dict[str, str]:
    if not parent_ids:
        return {}
    placeholders = ", ".join(["?"] * len(parent_ids))
    rows = _read_frame(
        store,
        "SELECT fact_id, available_at, verification_status, eligible_for_metrics "
        f"FROM financial_facts WHERE fact_id IN ({placeholders})",
        list(parent_ids),
    )
    retained = {str(row["fact_id"]): row for row in rows}
    resolution: dict[str, str] = {}
    for parent_id in parent_ids:
        row = retained.get(parent_id)
        if row is None:
            resolution[parent_id] = PARENT_ABSENT
            continue
        available_at = str(row.get("available_at") or "")
        visible = (
            bool(available_at)
            and available_at <= as_of
            and str(row.get("verification_status") or "") in {"verified", "reconciled"}
            and row.get("eligible_for_metrics") is True
        )
        resolution[parent_id] = PARENT_RESOLVED if visible else PARENT_NOT_AVAILABLE
    return resolution


def _classification(
    row: dict[str, Any], context: dict[str, Any] | None
) -> tuple[bool, int | None, list[str]]:
    """Return (compatible, exact integer value, exclusion reason codes)."""
    reasons: list[str] = []
    value = row.get("value")
    integer: int | None = None
    if isinstance(value, bool) or value is None:
        reasons.append(EXCLUDE_VALUE_NOT_EXACT_INTEGER)
    elif isinstance(value, float):
        if not math.isfinite(value) or not value.is_integer():
            reasons.append(EXCLUDE_VALUE_NOT_EXACT_INTEGER)
        else:
            integer = int(value)
    elif isinstance(value, int):
        integer = value
    elif isinstance(value, Decimal):
        if not value.is_finite() or value != value.to_integral_value():
            reasons.append(EXCLUDE_VALUE_NOT_EXACT_INTEGER)
        else:
            integer = int(value)
    else:
        reasons.append(EXCLUDE_VALUE_NOT_EXACT_INTEGER)
    if integer is not None and abs(integer) > SAFE_INTEGER_MAX:
        reasons.append(EXCLUDE_VALUE_OUT_OF_SAFE_RANGE)
        integer = None
    if str(row.get("unit") or "") != ENGINE_FACT_UNIT:
        reasons.append(EXCLUDE_UNIT_NOT_WAN_YUAN)
    if str(row.get("source_tier") or "") != ENGINE_SOURCE_TIER:
        reasons.append(EXCLUDE_SOURCE_TIER)
    if context is None:
        reasons.append(EXCLUDE_CONTEXT_MISSING)
    return (not reasons, integer, reasons)


def _enrich_row(
    row: dict[str, Any], *, date: str, scope: str, contexts: dict[str, dict[str, Any]]
) -> dict[str, Any]:
    context = contexts.get(str(row.get("context_id") or ""))
    compatible, integer, reasons = _classification(row, context)
    year = _fiscal_year(row.get("period_end"))
    period_type = str(context.get("period_type") or "") if context else ""
    if year is None:
        reasons = [*reasons, EXCLUDE_PERIOD_END_INVALID]
        compatible = False
    if (
        context is not None
        and year is not None
        and period_type != _expected_period_type(str(row.get("concept_id") or ""))
    ):
        reasons = [*reasons, EXCLUDE_PERIOD_CONTEXT_MISMATCH]
        compatible = False
    return {
        "fact_id": str(row.get("fact_id") or ""),
        "concept_id": str(row.get("concept_id") or ""),
        "period_end": str(row.get("period_end") or ""),
        "fiscal_year": year,
        "period_type": period_type,
        "consolidation_scope": scope,
        "value": float(row["value"]) if isinstance(row.get("value"), (int, float)) else None,
        "value_integer": integer,
        "unit": str(row.get("unit") or ""),
        "raw_unit": str(row.get("raw_unit") or ""),
        "fact_version": int(row.get("fact_version") or 0),
        "restatement_version": str(row.get("restatement_version") or ""),
        "supersedes_fact_id": str(row.get("supersedes_fact_id") or ""),
        "available_at": str(row.get("available_at") or ""),
        "announcement_date": str(row.get("announcement_date") or ""),
        "filing_date": str(row.get("filing_date") or ""),
        "verification_status": str(row.get("verification_status") or ""),
        "source_provider": str(row.get("source_provider") or ""),
        "source_id": str(row.get("source_id") or ""),
        "source_tier": str(row.get("source_tier") or ""),
        "source_document": str(row.get("source_document") or ""),
        "source_url": str(row.get("source_url") or ""),
        "source_hash": str(row.get("source_hash") or ""),
        "source_page": str(row.get("source_page") or ""),
        "source_table": str(row.get("source_table") or ""),
        "derivation_definition_id": str(row.get("derivation_definition_id") or ""),
        "derivation_version": str(row.get("derivation_version") or ""),
        "input_fact_ids": str(row.get("input_fact_ids") or ""),
        "eligible_for_metrics": row.get("eligible_for_metrics") is True,
        "selection_date": date,
        "compatible": compatible,
        "exclusion_reasons": reasons,
    }


SOURCE_REFERENCE_FIELDS = (
    "source_id",
    "source_document",
    "source_provider",
    "source_tier",
    "source_url",
    "source_hash",
    "source_page",
    "source_table",
    "verification_status",
    "derivation_definition_id",
    "derivation_version",
    "input_fact_ids",
)
MISSING_SOURCE_FIELDS = ("source_url", "source_hash", "source_page", "source_table")
BINDING_FACT_FIELDS = (
    "fact_id",
    "concept_id",
    "period_end",
    "period_type",
    "consolidation_scope",
    "value",
    "value_integer",
    "unit",
    "raw_unit",
    "fact_version",
    "restatement_version",
    "supersedes_fact_id",
    "available_at",
    "announcement_date",
    "filing_date",
    "verification_status",
    "eligible_for_metrics",
)


def _binding_from_entry(
    entry: dict[str, Any], role: str, *, lineage: dict[str, list[dict[str, Any]]],
    parents: dict[str, str],
) -> dict[str, Any]:
    binding = {
        "role": role,
        "concept_id": entry["concept_id"],
        "fiscal_year": entry["fiscal_year"],
        "selection_date": entry["selection_date"],
        "status": "present",
        "source_reference": {field: entry[field] for field in SOURCE_REFERENCE_FIELDS},
        "missing_source_reference_fields": [
            field for field in MISSING_SOURCE_FIELDS if not entry[field]
        ],
        "lineage": [dict(row) for row in lineage.get(entry["fact_id"], [])],
    }
    binding.update({field: entry[field] for field in BINDING_FACT_FIELDS})
    parent_ids = sorted(
        {
            parent.strip()
            for row in binding["lineage"]
            for parent in str(row.get("parent_fact_ids") or "").split(",")
            if parent.strip()
        }
    )
    binding["parents"] = {
        parent_id: parents.get(parent_id, PARENT_ABSENT) for parent_id in parent_ids
    }
    return binding


def _engine_fact(entry: dict[str, Any]) -> dict[str, Any]:
    """Restore the exact integer fact the public engine expects; memory only."""
    return {
        "fact_id": entry["fact_id"],
        "value": entry["value_integer"],
        "unit": entry["unit"],
        "source_tier": entry["source_tier"],
        "eligible_for_metrics": True,
        "period_end": entry["period_end"],
        "fact_version": entry["fact_version"],
        "restatement_version": entry["restatement_version"],
        "available_at": entry["available_at"],
    }


def _bind_role(
    index: dict[tuple[str, int], list[dict[str, Any]]],
    *,
    role: str,
    concept_id: str,
    year: int,
    date: str,
    lineage: dict[str, list[dict[str, Any]]],
    parents: dict[str, str],
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    expected_end = f"{year}-12-31"
    expected_type = _expected_period_type(concept_id)
    candidates = index.get((concept_id, year), [])
    matching = [
        entry
        for entry in candidates
        if entry["period_end"] == expected_end and entry["period_type"] == expected_type
    ]
    for entry in matching:
        if entry["compatible"]:
            return _binding_from_entry(entry, role, lineage=lineage, parents=parents), _engine_fact(
                entry
            )
    if matching:
        entry = matching[0]
        return (
            {
                "role": role,
                "concept_id": concept_id,
                "fiscal_year": year,
                "selection_date": date,
                "status": "excluded",
                "reason": ROLE_EXCLUDED,
                "exclusion_reasons": list(entry["exclusion_reasons"]),
                "fact_id": entry["fact_id"],
                "expected_period_end": expected_end,
                "expected_period_type": expected_type,
            },
            None,
        )
    reason = MISSING_CONTEXT if candidates else MISSING_ABSENT
    return (
        {
            "role": role,
            "concept_id": concept_id,
            "fiscal_year": year,
            "selection_date": date,
            "status": "missing",
            "reason": reason,
            "expected_period_end": expected_end,
            "expected_period_type": expected_type,
        },
        None,
    )


RESULT_FIELDS = (
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
)
LINEAGE_FIELDS = (
    "metric_result_id",
    "input_fact_id",
    "input_role",
    "input_fact_version",
    "input_restatement_version",
    "input_available_at",
)


def _serialize_result(result: Any) -> dict[str, Any]:
    record = {field: getattr(result, field) for field in RESULT_FIELDS}
    record["status"] = str(result.status)
    record["value"] = None if result.value is None else format(result.value, "f")
    record["input_fact_ids"] = list(result.input_fact_ids)
    record["engine_missing_input_description"] = result.missing_input_description
    return record


def _analyze_metric(
    definition: MetricDefinition,
    fiscal_year: int,
    *,
    first_year: int,
    date: str,
    symbol: str,
    index: dict[tuple[str, int], list[dict[str, Any]]],
    lineage: dict[str, list[dict[str, Any]]],
    parents: dict[str, str],
) -> dict[str, Any]:
    bindings: list[dict[str, Any]] = []
    facts: list[dict[str, Any] | None] = []
    for position, role in enumerate(definition.input_roles):
        binding, fact = _bind_role(
            index,
            role=role,
            concept_id=definition.input_concept_ids[position],
            year=fiscal_year - 1 if role in PRIOR_ROLES else fiscal_year,
            date=date,
            lineage=lineage,
            parents=parents,
        )
        bindings.append(binding)
        facts.append(fact)
    primary, secondary, tertiary = (facts + [None, None, None])[:3]
    try:
        result, result_lineage = MetricEngine.compute(
            definition,
            symbol=symbol,
            fiscal_year=fiscal_year,
            primary_fact=primary,
            secondary_fact=secondary,
            tertiary_fact=tertiary if len(definition.input_roles) >= 3 else None,
            missing_prior_is_history=(
                definition.formula == "(current / prior) - 1" and fiscal_year == first_year
            ),
            result_version=1,
            revision_review_status=REVISION_REVIEW_STATUS,
            as_of_date=date,
            created_at=ANALYSIS_CREATED_AT,
        )
    except MetricInputError as error:
        raise FinancialAnalysisError("METRIC_FACT_INVALID") from error
    record = _serialize_result(result)
    present = [item["available_at"] for item in bindings if item["status"] == "present"]
    record.update(
        display_name_zh=definition.display_name_zh,
        input_roles=list(definition.input_roles),
        input_concept_ids=list(definition.input_concept_ids),
        input_available_at_bound=max(present) if present else None,
        missing_roles=[item for item in bindings if item["status"] != "present"],
        inputs=bindings,
    )
    record["missing_fiscal_years"] = sorted(
        {int(item["fiscal_year"]) for item in record["missing_roles"]}
    )
    record["lineage"] = [
        {field: getattr(row, field) for field in LINEAGE_FIELDS} for row in result_lineage
    ]
    return record


def _year_over_year(
    records: list[dict[str, Any]], years: list[int], metrics: list[str]
) -> list[dict[str, Any]]:
    by_key = {(row["metric_id"], row["fiscal_year"]): row for row in records}
    entries: list[dict[str, Any]] = []
    for metric_id in metrics:
        for prior_year, current_year in zip(years, years[1:], strict=False):
            prior = by_key[(metric_id, prior_year)]
            current = by_key[(metric_id, current_year)]
            if prior["status"] == "computed" and current["status"] == "computed":
                state = YOY_COMPUTED
                delta = format(Decimal(current["value"]) - Decimal(prior["value"]), "f")
            else:
                state = YOY_NOT_COMPARABLE
                delta = None
            entries.append(
                {
                    "metric_id": metric_id,
                    "display_name_zh": current["display_name_zh"],
                    "unit": current["unit"],
                    "prior_fiscal_year": prior_year,
                    "fiscal_year": current_year,
                    "state": state,
                    "state_label_zh": YOY_LABELS_ZH[state],
                    "prior_status": prior["status"],
                    "current_status": current["status"],
                    "delta": delta,
                }
            )
    return entries


def _collect_view(
    store: _ReadOnlyFactStore, request: dict[str, Any], date: str
) -> dict[str, Any]:
    concepts = _needed_concepts(request["metrics"])
    rows = _select_rows(
        store, symbol=request["symbol"], date=date, scope=request["scope"], concepts=concepts
    )
    context_ids = sorted({str(row.get("context_id") or "") for row in rows} - {""})
    contexts = _load_contexts(store, context_ids)
    entries = [
        _enrich_row(row, date=date, scope=request["scope"], contexts=contexts) for row in rows
    ]
    window = range(request["years"][0] - 1, request["years"][-1] + 1)
    entries = [
        entry
        for entry in entries
        if entry["fiscal_year"] is None or entry["fiscal_year"] in window
    ]
    fact_ids = sorted({entry["fact_id"] for entry in entries if entry["fact_id"]})
    lineage = _load_lineage(store, fact_ids)
    parent_ids = sorted(
        {
            parent.strip()
            for rows_for_fact in lineage.values()
            for row in rows_for_fact
            for parent in str(row.get("parent_fact_ids") or "").split(",")
            if parent.strip()
        }
    )
    parents = _resolve_parents(store, parent_ids, date)
    index: dict[tuple[str, int], list[dict[str, Any]]] = {}
    for entry in entries:
        if entry["fiscal_year"] is not None:
            index.setdefault((entry["concept_id"], entry["fiscal_year"]), []).append(entry)
    definitions = metric_definitions()
    records = [
        _analyze_metric(
            definitions[metric_id],
            int(year),
            first_year=request["years"][0],
            date=date,
            symbol=request["symbol"],
            index=index,
            lineage=lineage,
            parents=parents,
        )
        for metric_id in request["metrics"]
        for year in request["years"]
    ]
    return {
        "date": date,
        "scope": request["scope"],
        "selection_count": len(entries),
        "compatible_fact_count": sum(1 for entry in entries if entry["compatible"]),
        "selected_fact_index": entries,
        "excluded_inputs": [
            {
                "fact_id": entry["fact_id"],
                "concept_id": entry["concept_id"],
                "period_end": entry["period_end"],
                "exclusion_reasons": list(entry["exclusion_reasons"]),
            }
            for entry in entries
            if not entry["compatible"]
        ],
        "records": records,
        "year_over_year": _year_over_year(records, request["years"], request["metrics"]),
    }


SIDE_FIELDS = ("metric_result_id", "status", "value", "unit", "input_available_at_bound")
ROLE_FIELDS = ("role", "concept_id", "fiscal_year", "fact_id")


def _side_view(record: dict[str, Any] | None) -> dict[str, Any] | None:
    if record is None:
        return None
    view = {field: record[field] for field in SIDE_FIELDS}
    view["input_fact_ids"] = list(record["input_fact_ids"])
    view["input_roles"] = [
        {key: item.get(key) for key in ROLE_FIELDS} for item in record["inputs"]
    ]
    return view


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


def build_report(
    *,
    database: str | Path,
    symbol: str,
    as_of: str,
    compare_with: str | None = None,
    years: list[int] | None = None,
    metrics: list[str] | None = None,
    scope: str = "consolidated",
) -> dict[str, Any]:
    """Validate selectors first, then open the explicit database read-only."""
    validated = validate_request(
        symbol=symbol,
        as_of=as_of,
        compare_with=compare_with,
        years=years,
        metrics=metrics,
        scope=scope,
    )
    database_path = Path(database)
    if not database_path.is_file() or database_path.is_symlink():
        raise FinancialAnalysisError("DATABASE_NOT_FOUND")
    database_sha256 = _sha256_file(database_path)
    store = _ReadOnlyFactStore(database_path)
    try:
        connection = store.connect()
        try:
            connection.execute("BEGIN TRANSACTION")
            as_of_view = _collect_view(store, validated, validated["as_of"])
            compare_view = (
                _collect_view(store, validated, validated["compare_with"])
                if validated["compare_with"] is not None
                else None
            )
            connection.execute("COMMIT")
        except BaseException:
            with contextlib.suppress(duckdb.Error):
                connection.execute("ROLLBACK")
            raise
    finally:
        store.close()
    comparison = None
    if compare_view is not None:
        comparison = build_comparison(as_of_view["records"], compare_view["records"])
    identity = {
        **validated,
        "database_sha256": database_sha256,
    }
    return {
        "schema": REPORT_SCHEMA,
        "symbol": validated["symbol"],
        "request": validated,
        "database": {
            "file_name": database_path.name,
            "sha256": database_sha256,
            "opened_read_only": True,
        },
        "boundary": {
            "read_model": True,
            "production_eligible": False,
            "score_eligible": False,
            "metric_publication_proven": False,
            "stored_metric_version_admitted": False,
            "database_mutated": False,
            "schema_created": False,
        },
        "selector_digest": hashlib.sha256(
            json.dumps(identity, ensure_ascii=False, sort_keys=True).encode("utf-8")
        ).hexdigest(),
        "notes": list(NOTES),
        "as_of": as_of_view,
        "compare_with": compare_view,
        "comparison": comparison,
        "limitations_zh": list(LIMITATIONS_ZH),
    }


def render_json(report: dict[str, Any]) -> str:
    return json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2, default=str) + "\n"


def _table(header: tuple[str, ...], rows: list[tuple[str, ...]]) -> list[str]:
    lines = ["| " + " | ".join(header) + " |", "| " + " | ".join("---" for _ in header) + " |"]
    lines += ["| " + " | ".join(row) + " |" for row in rows]
    return lines


def _metric_rows(record: dict[str, Any]) -> list[tuple[str, ...]]:
    value = record["value"] if record["value"] is not None else "—"
    head = (
        f"{record['metric_id']}",
        f"{record['fiscal_year']}",
        record["status"],
        value,
        record["unit"],
        record["input_available_at_bound"] or "—",
        record["metric_result_id"],
    )
    rows = [head]
    for item in record["missing_roles"]:
        detail = item.get("reason", "")
        if item["status"] == "excluded":
            detail = "；".join(item.get("exclusion_reasons", []))
        rows.append(
            (
                f"└ {record['metric_id']}",
                f"{record['fiscal_year']}",
                f"缺少输入：{item['role']}（{item['concept_id']} "
                f"FY{item['fiscal_year']}，{detail}）",
                "—",
                "",
                "",
                "",
            )
        )
    return rows


def _comparison_row(entry: dict[str, Any]) -> tuple[str, ...]:
    before, after = entry["before"], entry["after"]

    def side(view: dict[str, Any] | None) -> tuple[str, str, str]:
        if view is None:
            return "—", "—", "—"
        return view["status"], view["value"] if view["value"] is not None else "—", (
            view["metric_result_id"]
        )

    before_status, before_value, before_id = side(before)
    after_status, after_value, after_id = side(after)
    return (
        entry["metric_id"],
        str(entry["fiscal_year"]),
        entry["state_label_zh"],
        before_status,
        before_value,
        before_id,
        after_status,
        after_value,
        after_id,
    )


def render_markdown(report: dict[str, Any]) -> str:
    request, database = report["request"], report["database"]
    lines = [
        "# M2 核心公司财务分析（显式只读数据库）",
        "",
        "由 `python -m ashare_research.tools.financial_analysis` 离线生成：在调用者显式指定"
        "的只读事实数据库上，用公开 PIT 门禁选择事实，复用既有 12 个指标定义在内存中计算。"
        "不联网、不写数据库、不生成评分、排名、资格或建议。",
        "",
        "结果是离线读取模型，未经新的指标版本、生产或评分准入。",
        "",
        f"- 标的：{report['symbol']}；口径：{request['scope']}；"
        f"as-of：{request['as_of']}；对比时点：{request['compare_with'] or '（未请求）'}",
        f"- 年度：{'、'.join(map(str, request['years']))}；"
        f"指标：{'、'.join(request['metrics'])}",
        f"- 数据库：`{database['file_name']}`，SHA256：`{database['sha256']}`（只读打开，"
        "报告不放绝对路径）",
        f"- 选择器摘要 SHA256：`{report['selector_digest']}`（含数据库内容摘要，无当前时间戳）",
        "",
    ]
    lines += [f"- {note}" for note in report["notes"]]
    for block in (report["as_of"], report["compare_with"]):
        if block is None:
            continue
        lines += [
            "",
            f"## {block['date']}：PIT 选中事实 / 指标结果",
            "",
            f"- PIT 选中事实 {block['selection_count']} 条（其中兼容输入 "
            f"{block['compatible_fact_count']} 条）；完整索引与逐角色输入见 report.json。",
            "",
        ]
        lines += _table(
            ("指标", "年度", "状态", "精确值", "单位", "输入可得性上界", "metric_result_id"),
            [row for record in block["records"] for row in _metric_rows(record)],
        )
        if block["excluded_inputs"]:
            lines += ["", "### 显式排除的输入（不参与任何指标）", ""]
            lines += _table(
                ("fact_id", "概念", "期间", "排除原因"),
                [
                    (
                        item["fact_id"],
                        item["concept_id"],
                        item["period_end"],
                        "、".join(item["exclusion_reasons"]),
                    )
                    for item in block["excluded_inputs"]
                ],
            )
        lines += ["", "### 相邻年度数值差（描述性）", ""]
        lines += _table(
            ("指标", "年度", "对比上一年度", "状态", "算术差", "单位"),
            [
                (
                    row["metric_id"],
                    str(row["fiscal_year"]),
                    str(row["prior_fiscal_year"]),
                    row["state_label_zh"],
                    row["delta"] if row["delta"] is not None else "—",
                    row["unit"],
                )
                for row in block["year_over_year"]
            ],
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
            "`fact_id` 不同；缺失值保持 null/—，绝不当作 0。同一键是同一指标同一 fiscal_year；"
            "相邻年度差值不会混入两时点重述对比。",
        ]
    lines += ["", "## 未解决证据与限制", ""]
    lines += [f"- {item}" for item in report["limitations_zh"]] + [""]
    return "\n".join(lines)


def build_manifest(report: dict[str, Any], files: dict[str, bytes]) -> dict[str, Any]:
    """Deterministic manifest: rendered hashes, database digest, selectors and fact ids."""
    entries = [
        {
            "path": name,
            "byte_count": len(files[name]),
            "sha256": hashlib.sha256(files[name]).hexdigest(),
        }
        for name in MANAGED_FILE_NAMES
    ]

    def ids(block: dict[str, Any] | None, section: str, field: str) -> list[str]:
        return [row[field] for row in block[section]] if block else []

    return {
        "schema": MANIFEST_SCHEMA,
        "report_schema": REPORT_SCHEMA,
        "managed_file_count": len(entries),
        "total_byte_count": sum(entry["byte_count"] for entry in entries),
        "files": entries,
        "request": report["request"],
        "database": report["database"],
        "selector_digest": report["selector_digest"],
        "selection": {
            "as_of": report["request"]["as_of"],
            "compare_with": report["request"]["compare_with"],
            "as_of_fact_ids": ids(report["as_of"], "selected_fact_index", "fact_id"),
            "compare_with_fact_ids": ids(
                report["compare_with"], "selected_fact_index", "fact_id"
            ),
            "as_of_metric_result_ids": ids(report["as_of"], "records", "metric_result_id"),
            "compare_with_metric_result_ids": ids(
                report["compare_with"], "records", "metric_result_id"
            ),
            "comparison_states": (report["comparison"]["states"] if report["comparison"] else {}),
        },
        "boundaries": {
            "network_used": False,
            "database_mutated": False,
            "schema_created": False,
            "default_database_read": False,
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
            raise FinancialAnalysisError("OUTPUT_PATH_EXISTS")
        output.mkdir(parents=True, exist_ok=False)
    except FileExistsError as error:
        raise FinancialAnalysisError("OUTPUT_PATH_EXISTS") from error
    except OSError as error:
        raise FinancialAnalysisError("OUTPUT_WRITE_FAILED") from error
    try:
        for name in MANAGED_FILE_NAMES:
            (output / name).write_bytes(files[name])
        (output / MANIFEST_NAME).write_bytes(manifest_bytes)
    except OSError as error:
        raise FinancialAnalysisError("OUTPUT_WRITE_FAILED") from error
    return json.loads(manifest_bytes.decode("utf-8"))
