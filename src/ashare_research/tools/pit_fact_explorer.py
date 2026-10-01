"""M2 指定时点（PIT）财务事实浏览器：最新可用事实、两时点版本对比与来源追踪。

本工具是**离线只读**批处理：唯一输入是仓库内已提交、字节哈希固定的规范事实快照
``tests/fixtures/stage2g/canonical_fact_snapshot_v1``。它不读取调用方数据库、不联网、
不获取新数据、不修改默认数据库或任何既有文件，也不产生任何新指标、比率、评分、排名、
资格判定或研究阶段结论。

选择路径只经过公开接口：``validate_snapshot`` / ``build_temp_fact_db`` 在工具自有的
``TemporaryDirectory`` 中重建临时 DuckDB（清理前先关闭连接），再用 ``FactRepository`` /
``AsOfQuery.get_latest_available`` 应用 PIT 门禁（``available_at`` 非空且 ``<= as-of``、
verification 通过、``eligible_for_metrics``）。因此未来事实永不进入选择，也不存在
“静默默认为今天”。

金额一律按选中的 ``fact_id`` 从快照还原原始 ``value_decimal`` 精确十进制字符串；两时点
比较使用 ``Decimal`` 数值相等，不经过引擎 DOUBLE，也不做浮点财务算术。

``created_at`` / ``recorded_at`` 是本地存储元数据，不是可得性证据。

已知失败退出码 2，只向 stderr 输出净化后的稳定错误码，stdout 保持为空。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import tempfile
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

import pandas as pd

from ashare_research.exceptions import PointInTimeError
from ashare_research.facts.as_of import AsOfQuery
from ashare_research.facts.dates import validate_pit_date
from ashare_research.facts.repository import FactRepository
from ashare_research.reproducibility.capsule import (
    CONTEXTS_FILE,
    FACTS_FILE,
    LINEAGE_FILE,
    SNAPSHOT_CONTRACT,
    SNAPSHOT_MANIFEST,
    build_temp_fact_db,
    validate_snapshot,
)
from ashare_research.storage.duckdb_store import DuckDBStore

ROOT = Path(__file__).resolve().parents[3]
COMMITTED_SNAPSHOT = ROOT / "tests" / "fixtures" / "stage2g" / "canonical_fact_snapshot_v1"

SYMBOL = "601857.SH"
EXPECTED_ROW_COUNT = 33
SCOPES: tuple[str, ...] = ("consolidated", "parent_company")
REPORT_SCHEMA = "m2_pit_fact_explorer_report_v1"
MANIFEST_SCHEMA = "m2_pit_fact_explorer_manifest_v1"
REPORT_MARKDOWN_NAME = "report.md"
REPORT_JSON_NAME = "report.json"
MANIFEST_NAME = "manifest.json"
MANAGED_FILE_NAMES: tuple[str, ...] = (REPORT_MARKDOWN_NAME, REPORT_JSON_NAME)

# 固定规范快照的五个概念及其中文名（来自 facts/concepts.py 的既有概念注册表）。
CONCEPT_LABELS_ZH: dict[str, str] = {
    "cash_paid_for_fixed_assets": "购建固定资产无形资产支付的现金",
    "equity_attributable_to_parent": "归属于母公司股东权益",
    "net_profit_attributable_to_parent": "归属于母公司股东的净利润",
    "operating_cash_flow": "经营活动现金流净额",
    "revenue": "营业收入",
}

# 四个来源文件的 SHA256，按已验证基线 9db39e85 固定。
PINNED_SOURCE_SHA256: dict[str, str] = {
    FACTS_FILE: "68d63be1e5a5c13f9e3e136ac1297d867e1a9a72cae46c1444342e5e6602d45f",
    CONTEXTS_FILE: "bb31f5302c987c93afafb41b4685349f38cb7c31b9ee330f50d2585125554678",
    LINEAGE_FILE: "e8cd2ee4447bb45dd2d04f793fa4412bc5c28901cea63da9e45fe275b1afc853",
    SNAPSHOT_MANIFEST: "78932c285f21ef161bc0b506327b71191f529d2162999a7beb5ae0ed9f06e5b3",
}

STATE_ADDED = "added"
STATE_REMOVED = "removed"
STATE_VALUE_CHANGED = "value_changed"
STATE_VERSION_CHANGED = "version_changed"
STATE_UNCHANGED = "unchanged"
COMPARISON_STATES: tuple[str, ...] = (
    STATE_ADDED,
    STATE_REMOVED,
    STATE_VALUE_CHANGED,
    STATE_VERSION_CHANGED,
    STATE_UNCHANGED,
)
STATE_LABELS_ZH: dict[str, str] = {
    STATE_ADDED: "新增（对比时点新可得）",
    STATE_REMOVED: "移除（对比时点不再可得）",
    STATE_VALUE_CHANGED: "数值变更（重述）",
    STATE_VERSION_CHANGED: "版本变更（数值未变）",
    STATE_UNCHANGED: "未变",
}

PARENT_RESOLVED = "resolved"
PARENT_ABSENT = "unresolved_absent_from_snapshot"
PARENT_NOT_AVAILABLE = "unresolved_not_available_at_as_of"
PARENT_LABELS_ZH: dict[str, str] = {
    PARENT_RESOLVED: "已解决（快照内保留且在 as-of 时点通过公开 PIT 门禁）",
    PARENT_ABSENT: "未解决（原始父事实不在固定快照内，本工具无法复原）",
    PARENT_NOT_AVAILABLE: "未解决（快照内保留但在 as-of 时点尚未通过公开 PIT 门禁）",
}

KNOWN_ERROR_CODES = frozenset(
    {
        "SOURCE_SNAPSHOT_MISSING",
        "SOURCE_DIGEST_MISMATCH",
        "SNAPSHOT_CONTRACT_UNEXPECTED",
        "SOURCE_VALUE_INVALID",
        "SELECTED_FACT_NOT_IN_SNAPSHOT",
        "INVALID_AS_OF_DATE",
        "INVALID_COMPARE_WITH",
        "INVALID_PERIOD_END",
        "INVALID_SCOPE",
        "UNKNOWN_CONCEPT",
        "COMPARE_BEFORE_AS_OF",
        "INVALID_ARGUMENTS",
        "OUTPUT_PATH_EXISTS",
        "OUTPUT_WRITE_FAILED",
        "UNEXPECTED_FAILURE",
    }
)


class PitExplorerError(Exception):
    """A known, sanitized explorer failure carrying one stable error code."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code if code in KNOWN_ERROR_CODES else "UNEXPECTED_FAILURE"


# --------------------------------------------------------------------------------------
# 来源校验与装载
# --------------------------------------------------------------------------------------


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _sha256_file(path: Path) -> str:
    try:
        return _sha256_bytes(path.read_bytes())
    except OSError as error:
        raise PitExplorerError("SOURCE_SNAPSHOT_MISSING") from error


def verify_pinned_sources(snapshot_dir: Path) -> list[dict[str, str]]:
    """Verify the four source digests against their fixed pins before anything else."""
    entries: list[dict[str, str]] = []
    for name in (FACTS_FILE, CONTEXTS_FILE, LINEAGE_FILE, SNAPSHOT_MANIFEST):
        path = snapshot_dir / name
        if not path.is_file() or path.is_symlink():
            raise PitExplorerError("SOURCE_SNAPSHOT_MISSING")
        digest = _sha256_file(path)
        if digest != PINNED_SOURCE_SHA256[name]:
            raise PitExplorerError("SOURCE_DIGEST_MISMATCH")
        entries.append({"name": name, "sha256": digest})
    return entries


def load_snapshot() -> dict[str, Any]:
    """Validate the fixed canonical snapshot and its expected contract shape."""
    files = verify_pinned_sources(COMMITTED_SNAPSHOT)
    try:
        snapshot = validate_snapshot(COMMITTED_SNAPSHOT)
    except (OSError, ValueError) as error:
        raise PitExplorerError("SNAPSHOT_CONTRACT_UNEXPECTED") from error
    manifest = snapshot["manifest"]
    coverage = manifest.get("concept_coverage")
    if (
        snapshot["row_count"] != EXPECTED_ROW_COUNT
        or manifest.get("symbol") != SYMBOL
        or not isinstance(coverage, dict)
        or set(coverage) != set(CONCEPT_LABELS_ZH)
    ):
        raise PitExplorerError("SNAPSHOT_CONTRACT_UNEXPECTED")
    return {"validation": snapshot, "files": files}


def _source_decimal(text: Any) -> Decimal:
    """Parse one raw ``value_decimal`` string; never a float financial value."""
    try:
        value = Decimal(text)
        if not value.is_finite():
            raise ValueError("non-finite source value")
        return value
    except (InvalidOperation, TypeError, ValueError) as error:
        raise PitExplorerError("SOURCE_VALUE_INVALID") from error


# --------------------------------------------------------------------------------------
# PIT 读取（工具自有临时目录，清理前关闭连接）
# --------------------------------------------------------------------------------------


def _pit_rows(
    frame: pd.DataFrame, period_end: str | None, scope: str,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if frame is None or frame.empty:
        return rows
    for record in frame.to_dict(orient="records"):
        if period_end is not None and str(record["period_end"]) != period_end:
            continue
        rows.append(
            {
                "fact_id": str(record["fact_id"]),
                "concept_id": str(record["concept_id"]),
                "period_end": str(record["period_end"]),
                # Public query filters context scope but returns f.* only.
                "consolidation_scope": scope,
                "available_at": str(record["available_at"]),
                "announcement_date": str(record.get("announcement_date") or ""),
                "filing_date": str(record.get("filing_date") or ""),
                "fact_version": int(record["fact_version"]),
                "restatement_version": str(record["restatement_version"]),
                "supersedes_fact_id": str(record.get("supersedes_fact_id") or ""),
                "verification_status": str(record["verification_status"]),
            }
        )
    return rows


def collect_pit_rows(
    *,
    as_of: str,
    compare_with: str | None,
    concept_ids: list[str] | None,
    period_end: str | None,
    scope: str,
) -> dict[str, Any]:
    """Read every PIT view inside one owned temporary directory, then close it."""
    with tempfile.TemporaryDirectory(prefix="m2-pit-fact-explorer-") as runtime:
        db_path = build_temp_fact_db(
            COMMITTED_SNAPSHOT, Path(runtime) / "temporary_fact.duckdb"
        )
        store = DuckDBStore(str(db_path))
        try:
            query = AsOfQuery(FactRepository(store))
            as_of_rows = _pit_rows(
                query.get_latest_available(
                    symbol=SYMBOL,
                    as_of_date=as_of,
                    concept_ids=concept_ids,
                    consolidation_scope=scope,
                ),
                period_end,
                scope,
            )
            compare_rows = None
            if compare_with is not None:
                compare_rows = _pit_rows(
                    query.get_latest_available(
                        symbol=SYMBOL,
                        as_of_date=compare_with,
                        concept_ids=concept_ids,
                        consolidation_scope=scope,
                    ),
                    period_end,
                    scope,
                )
            frame = query.query(symbol=SYMBOL, as_of_date=as_of)
            available_ids = sorted(str(value) for value in frame["fact_id"].tolist())
            compare_available_ids: list[str] = []
            if compare_with is not None:
                frame = query.query(symbol=SYMBOL, as_of_date=compare_with)
                compare_available_ids = sorted(str(value) for value in frame["fact_id"].tolist())
            return {
                "as_of_rows": as_of_rows,
                "compare_rows": compare_rows,
                "pit_available_ids": available_ids,
                "compare_pit_available_ids": compare_available_ids,
            }
        finally:
            store.close()


# --------------------------------------------------------------------------------------
# 精确值还原、来源追踪与两时点对比
# --------------------------------------------------------------------------------------


def _sort_key(entry: dict[str, Any]) -> tuple[str, str, str, str]:
    return (
        entry["concept_id"],
        entry["period_end"],
        entry["consolidation_scope"],
        entry["fact_id"],
    )


def _enrich_rows(
    rows: list[dict[str, Any]], facts_by_id: dict[str, dict[str, Any]]
) -> list[dict[str, Any]]:
    """Join each PIT-selected ``fact_id`` back to its exact source decimal and metadata."""
    enriched: list[dict[str, Any]] = []
    for row in rows:
        fact = facts_by_id.get(row["fact_id"])
        if fact is None:
            raise PitExplorerError("SELECTED_FACT_NOT_IN_SNAPSHOT")
        entry = dict(row)
        entry["concept_label_zh"] = CONCEPT_LABELS_ZH[row["concept_id"]]
        entry["value_decimal"] = str(fact["value_decimal"])
        _source_decimal(entry["value_decimal"])
        entry["unit"] = str(fact.get("unit") or "")
        entry["raw_unit"] = str(fact.get("raw_unit") or "")
        entry["period_type"] = str(fact.get("period_type") or "")
        entry["context_id"] = str(fact.get("context_id") or "")
        entry["source_reference"] = {
            key: fact.get(key, "")
            for key in (
                "source_id", "source_document", "source_provider", "source_tier",
                "source_url", "source_hash", "source_page", "source_table",
                "verification_note", "derivation_definition_id", "derivation_version",
                "input_fact_ids", "eligible_for_metrics",
            )
        }
        entry["missing_source_reference_fields"] = [
            key for key in ("source_url", "source_hash", "source_page", "source_table")
            if not fact.get(key)
        ]
        enriched.append(entry)
    return sorted(enriched, key=_sort_key)


def _split_parents(raw: str) -> list[str]:
    return [value.strip() for value in str(raw).split(",") if value.strip()]


def _resolve_parents(
    parent_ids: list[str], retained_ids: set[str], pit_ids: set[str]
) -> list[dict[str, Any]]:
    """Resolve parents through the public PIT gate; future parents stay unresolved."""
    entries: list[dict[str, Any]] = []
    for parent_id in parent_ids:
        retained = parent_id in retained_ids
        available = parent_id in pit_ids
        if not retained:
            status = PARENT_ABSENT
        elif not available:
            status = PARENT_NOT_AVAILABLE
        else:
            status = PARENT_RESOLVED
        entries.append(
            {
                "fact_id": parent_id,
                "status": status,
                "status_label_zh": PARENT_LABELS_ZH[status],
                "retained_in_snapshot": retained,
                "pit_available_at_as_of": available,
            }
        )
    return entries


def _trace_entry(
    entry: dict[str, Any],
    *,
    contexts_by_id: dict[str, dict[str, Any]],
    lineage_by_fact: dict[str, list[dict[str, Any]]],
    retained_ids: set[str],
    pit_ids: set[str],
) -> dict[str, Any]:
    fact_id = entry["fact_id"]
    context = contexts_by_id.get(entry["context_id"], {})
    context_view = {
        key: value for key, value in sorted(context.items()) if key != "created_at"
    }
    lineage_view: list[dict[str, Any]] = []
    parent_ids: list[str] = []
    recorded_at: list[str] = []
    for row in lineage_by_fact.get(fact_id, []):
        parent_ids.extend(_split_parents(row.get("parent_fact_ids", "")))
        recorded_at.append(str(row.get("recorded_at") or ""))
        lineage_view.append(
            {
                "lineage_id": int(row["lineage_id"]),
                "run_id": str(row.get("run_id") or ""),
                "role": str(row.get("role") or ""),
                "source_provider": str(row.get("source_provider") or ""),
                "source_tier": str(row.get("source_tier") or ""),
                "source_method": str(row.get("source_method") or ""),
                "reconciliation_rule_id": str(row.get("reconciliation_rule_id") or ""),
                "reconciliation_rule_version": str(
                    row.get("reconciliation_rule_version") or ""
                ),
                "parent_fact_ids_raw": str(row.get("parent_fact_ids") or ""),
            }
        )
    unique_parents = sorted(set(parent_ids))
    parents = _resolve_parents(unique_parents, retained_ids, pit_ids)
    traced = dict(entry)
    traced["context"] = context_view
    traced["lineage"] = lineage_view
    traced["parents"] = {
        "total": len(parents),
        "resolved": sum(1 for item in parents if item["status"] == PARENT_RESOLVED),
        "unresolved": sum(1 for item in parents if item["status"] != PARENT_RESOLVED),
        "entries": parents,
    }
    traced["storage_metadata"] = {
        "context_created_at": str(context.get("created_at") or ""),
        "lineage_recorded_at": sorted(value for value in recorded_at if value),
        "availability_proof": False,
        "note": "created_at / recorded_at 只是本地存储时间，不构成可得性证据",
    }
    return traced


def _side(entry: dict[str, Any] | None) -> dict[str, Any] | None:
    if entry is None:
        return None
    return {
        "fact_id": entry["fact_id"],
        "value_decimal": entry["value_decimal"],
        "available_at": entry["available_at"],
        "fact_version": entry["fact_version"],
        "restatement_version": entry["restatement_version"],
    }


def _key(entry: dict[str, Any]) -> tuple[str, str, str]:
    return (entry["concept_id"], entry["period_end"], entry["consolidation_scope"])


def build_comparison(
    before_rows: list[dict[str, Any]], after_rows: list[dict[str, Any]]
) -> dict[str, Any]:
    """Compare two PIT views by concept/period/scope with exact decimal equality."""
    before = {_key(entry): entry for entry in before_rows}
    after = {_key(entry): entry for entry in after_rows}
    counts = dict.fromkeys(COMPARISON_STATES, 0)
    entries: list[dict[str, Any]] = []
    for key in sorted(set(before) | set(after)):
        left = before.get(key)
        right = after.get(key)
        if left is None:
            state = STATE_ADDED
        elif right is None:
            state = STATE_REMOVED
        elif _source_decimal(left["value_decimal"]) != _source_decimal(
            right["value_decimal"]
        ):
            state = STATE_VALUE_CHANGED
        elif left["fact_id"] != right["fact_id"]:
            state = STATE_VERSION_CHANGED
        else:
            state = STATE_UNCHANGED
        counts[state] += 1
        concept_id, period_end, scope = key
        entries.append(
            {
                "concept_id": concept_id,
                "concept_label_zh": CONCEPT_LABELS_ZH[concept_id],
                "period_end": period_end,
                "consolidation_scope": scope,
                "state": state,
                "state_label_zh": STATE_LABELS_ZH[state],
                "before": _side(left),
                "after": _side(right),
            }
        )
    return {"states": counts, "entries": entries}


def _limitations() -> list[str]:
    return [
        "快照只保留 33 条已对账事实及其直接 lineage；lineage 中的 66 个 parent_fact_ids "
        "全部不在快照内，公司/交易所原始披露证据无法在本工具内复原，工具对每个父事实显式"
        "标记未解决，不伪造完整原始证据，也不声称重新证明了原始可得性。",
        "两个查询时点分别追踪各自 PIT 选中事实的父事实；"
        "父事实只有在快照内保留、且在对应时点通过公开 PIT 门禁时才算解决，未来父事实"
        "永不解决。",
        "上下文是快照保留的期间级元数据；其中 filing_date/source_document 不一定对应"
        "当前重述版本。事实级日期和来源字段分别保留，缺失的 URL、摘要、页码与表名"
        "显式列出，不据此补写披露证据。",
        "available_at 取自固定快照本身，工具只按公开 PIT 门禁使用它，不重新验证该日期；"
        "created_at / recorded_at 是 2026 年的本地存储元数据，不是可得性证据。",
        "快照是规范导出/读取模型（canonical export/read model; not a new source of truth），"
        "不是新的真值来源；本工具不做数据获取、来源准入或默认数据库读写。",
        "固定快照只有 601857.SH、5 个概念，且只有 consolidated 口径；"
        "--scope parent_company 会如实返回空结果，不回退到合并口径或更晚时点。",
        "本工具只做指定时点的原始事实选择与版本对比，不产生任何新指标、比率、评分、排名、"
        "资格判定或研究阶段结论，也不给出投资建议。",
    ]


# --------------------------------------------------------------------------------------
# 报告装配
# --------------------------------------------------------------------------------------


def build_report(request: dict[str, Any]) -> dict[str, Any]:
    """Validate the fixed sources, read PIT views and assemble the full report body."""
    loaded = load_snapshot()
    snapshot = loaded["validation"]
    facts_by_id = {str(row["fact_id"]): row for row in snapshot["facts"]}
    contexts_by_id = {str(row["context_id"]): row for row in snapshot["contexts"]}
    lineage_by_fact: dict[str, list[dict[str, Any]]] = {}
    for row in sorted(snapshot["lineage"], key=lambda item: int(item["lineage_id"])):
        lineage_by_fact.setdefault(str(row["fact_id"]), []).append(row)
    concept_ids = request["concepts"] or None
    pit = collect_pit_rows(
        as_of=request["as_of"],
        compare_with=request["compare_with"],
        concept_ids=concept_ids,
        period_end=request["period_end"],
        scope=request["scope"],
    )
    before_rows = _enrich_rows(pit["as_of_rows"], facts_by_id)
    retained_ids = set(facts_by_id)
    pit_ids = set(pit["pit_available_ids"])
    selections = [
        _trace_entry(
            entry,
            contexts_by_id=contexts_by_id,
            lineage_by_fact=lineage_by_fact,
            retained_ids=retained_ids,
            pit_ids=pit_ids,
        )
        for entry in before_rows
    ]
    comparison = None
    compare_selections: list[dict[str, Any]] = []
    if pit["compare_rows"] is not None:
        after_rows = _enrich_rows(pit["compare_rows"], facts_by_id)
        compare_selections = [
            _trace_entry(
                entry,
                contexts_by_id=contexts_by_id,
                lineage_by_fact=lineage_by_fact,
                retained_ids=retained_ids,
                pit_ids=set(pit["compare_pit_available_ids"]),
            )
            for entry in after_rows
        ]
        comparison = build_comparison(
            before_rows, after_rows
        )
    return {
        "schema": REPORT_SCHEMA,
        "symbol": SYMBOL,
        "request": dict(request),
        "source": {
            "contract": SNAPSHOT_CONTRACT,
            "symbol": SYMBOL,
            "row_count": snapshot["row_count"],
            "context_count": snapshot["context_count"],
            "lineage_count": snapshot["lineage_count"],
            "concept_count": len(CONCEPT_LABELS_ZH),
            "fact_set_sha256": snapshot["facts_sha256"],
            "files": loaded["files"],
        },
        "selection_count": len(selections),
        "selections": selections,
        "compare_selections": compare_selections,
        "comparison": comparison,
        "limitations_zh": _limitations(),
    }


def render_json(report: dict[str, Any]) -> str:
    return json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n"


def _scope_label(scope: str) -> str:
    suffix = "合并报表" if scope == "consolidated" else "母公司报表"
    return f"{scope}（{suffix}）"


def _table(header: tuple[str, ...], rows: list[tuple[str, ...]]) -> list[str]:
    lines = [
        "| " + " | ".join(header) + " |",
        "| " + " | ".join("---" for _ in header) + " |",
    ]
    lines.extend("| " + " | ".join(row) + " |" for row in rows)
    return lines


def _markdown_lines(report: dict[str, Any]) -> list[str]:
    request = report["request"]
    source = report["source"]
    lines: list[str] = [
        "# M2 指定时点（PIT）财务事实浏览器",
        "",
        "本报告由 `python -m ashare_research.tools.pit_fact_explorer` 离线生成：只读取仓库内"
        "字节固定的规范事实快照，不联网、不读调用方数据库、不修改任何既有文件。",
        "",
        "## 请求",
        "",
    ]
    concept_text = (
        "、".join(f"{CONCEPT_LABELS_ZH[item]}（{item}）" for item in request["concepts"])
        or "（全部 5 个概念）"
    )
    lines.extend(
        _table(
            ("项目", "值"),
            [
                ("as-of 时点", request["as_of"]),
                ("对比时点", request["compare_with"] or "（未请求）"),
                ("标的", report["symbol"]),
                ("合并范围口径", _scope_label(request["scope"])),
                ("概念过滤", concept_text),
                ("报告期过滤", request["period_end"] or "（未过滤）"),
            ],
        )
    )
    lines.extend(["", "## 来源与边界", ""])
    lines.append(
        f"- 事实快照 contract：`{source['contract']}`，{source['row_count']} 条事实、"
        f"{source['concept_count']} 个概念、{source['context_count']} 个上下文、"
        f"{source['lineage_count']} 条 lineage，标的 {source['symbol']}。"
    )
    lines.append(f"- 事实集 SHA256：`{source['fact_set_sha256']}`（与快照清单一致）。")
    lines.append("- 四个来源文件 SHA256（与固定 pin 一致）：")
    lines.append("")
    lines.extend(
        _table(("来源文件", "SHA256"), [(item["name"], item["sha256"]) for item in source["files"]])
    )
    lines.extend(
        [
            "",
            "- 金额一律是快照中按选中 `fact_id` 还原的**原始十进制字符串** `value_decimal`；"
            "两时点比较使用 `Decimal` 数值相等，不经过引擎 DOUBLE，也不做浮点财务算术。",
            "- `created_at` / `recorded_at` 只是本地存储元数据，不是可得性证据；可得性只由 "
            "`available_at` 与公开 PIT 门禁决定。",
            "",
            f"## PIT 选择结果（as-of {request['as_of']}）",
            "",
        ]
    )
    if report["selection_count"] == 0:
        lines.append(
            "本时点在所选概念/期间/口径下**没有任何通过 PIT 门禁的可用事实**"
            "（空结果如实保留，不回退到其他口径或更晚时点）。"
        )
    else:
        lines.append(
            f"共 {report['selection_count']} 条（每行是该事实键在 as-of 时点的最新可用版本）。"
        )
        lines.append("")
        lines.extend(
            _table(
                (
                    "概念", "报告期", "口径", "精确值（来源十进制）", "单位",
                    "可得日", "版本", "重述", "fact_id",
                ),
                [
                    (
                        f"{entry['concept_label_zh']}（{entry['concept_id']}）",
                        entry["period_end"],
                        entry["consolidation_scope"],
                        entry["value_decimal"],
                        entry["unit"],
                        entry["available_at"],
                        str(entry["fact_version"]),
                        entry["restatement_version"],
                        entry["fact_id"],
                    )
                    for entry in report["selections"]
                ],
            )
        )
    lines.extend(["", "## 两时点版本对比", ""])
    comparison = report["comparison"]
    if comparison is None:
        lines.append("未请求两时点对比（未提供 `--compare-with`）。")
    elif not comparison["entries"]:
        lines.append("两个时点在所选范围内都没有通过 PIT 门禁的事实，对比结果为空。")
    else:
        counts = comparison["states"]
        summary = "，".join(
            f"{STATE_LABELS_ZH[state]} {counts[state]} 条" for state in COMPARISON_STATES
        )
        lines.append(
            f"{request['as_of']} → {request['compare_with']}，共 {len(comparison['entries'])} 个"
            f"事实键：{summary}。"
        )
        lines.append("")
        lines.extend(
            _table(
                (
                    "概念", "报告期", "口径", "状态", "前值（as-of）", "前 fact_id",
                    "后值（对比）", "后 fact_id",
                ),
                [
                    (
                        f"{entry['concept_label_zh']}（{entry['concept_id']}）",
                        entry["period_end"],
                        entry["consolidation_scope"],
                        entry["state_label_zh"],
                        entry["before"]["value_decimal"] if entry["before"] else "—",
                        entry["before"]["fact_id"] if entry["before"] else "—",
                        entry["after"]["value_decimal"] if entry["after"] else "—",
                        entry["after"]["fact_id"] if entry["after"] else "—",
                    )
                    for entry in comparison["entries"]
                ],
            )
        )
        lines.append("")
        lines.append(
            "「数值变更」用精确十进制数值比较得出；「版本变更」表示两个时点选中的 `fact_id` "
            "不同但十进制数值相等。"
        )
    lines.extend(["", "## 来源追踪（各查询时点选中事实）", ""])
    traced_selections = [(request["as_of"], entry) for entry in report["selections"]]
    traced_selections.extend(
        (request["compare_with"], entry) for entry in report["compare_selections"]
    )
    if not traced_selections:
        lines.append("as-of 时点没有选中事实；对比时点亦无选中事实，因此没有可追踪的来源。")
    else:
        for index, (trace_date, entry) in enumerate(traced_selections, start=1):
            parents = entry["parents"]
            lines.append(
                f"### {index}. {entry['concept_label_zh']}（{entry['concept_id']}）｜"
                f"{entry['period_end']}｜{entry['consolidation_scope']}｜查询时点 {trace_date}"
            )
            lines.append("")
            lines.append(f"- 事实 ID：`{entry['fact_id']}`")
            lines.append(
                f"- 精确值：`{entry['value_decimal']}` {entry['unit']}"
                f"（raw_unit={entry['raw_unit'] or '—'}）"
            )
            supersedes = entry["supersedes_fact_id"] or "无"
            lines.append(
                f"- 版本：v{entry['fact_version']}（{entry['restatement_version']}）；"
                f"替代：{supersedes}"
            )
            lines.append(
                f"- 日期：period_end={entry['period_end']}，available_at={entry['available_at']}，"
                f"announcement_date={entry['announcement_date'] or '—'}，"
                f"filing_date={entry['filing_date'] or '—'}"
            )
            context = entry["context"]
            lines.append(
                f"- 上下文 `{entry['context_id']}`：期间 {context.get('period_start', '—')} ~ "
                f"{context.get('period_end', '—')}（{context.get('period_type', '—')}），"
                f"合并范围 {context.get('consolidation_scope', '—')}，"
                f"会计准则 {context.get('accounting_standard', '—')}，"
                f"来源文档：{context.get('source_document', '—') or '—'}"
            )
            lines.append(f"- 校验状态：{entry['verification_status']}")
            reference = entry["source_reference"]
            lines.append(
                f"- 事实级来源：{reference['source_document'] or '—'}；"
                f"source_id={reference['source_id'] or '—'}；"
                f"URL={reference['source_url'] or '—'}；"
                f"缺失字段：{', '.join(entry['missing_source_reference_fields']) or '无'}"
            )
            for row in entry["lineage"]:
                lines.append(
                    f"- 来源 lineage_id={row['lineage_id']}：role={row['role'] or '—'}，"
                    f"provider={row['source_provider'] or '—'}，tier={row['source_tier'] or '—'}，"
                    f"method={row['source_method'] or '—'}，"
                    f"规则={row['reconciliation_rule_id'] or '—'} "
                    f"v{row['reconciliation_rule_version'] or '—'}"
                )
            metadata = entry["storage_metadata"]
            lines.append(
                f"- 存储元数据（**非可得性证据**）：context.created_at="
                f"{metadata['context_created_at'] or '—'}，lineage.recorded_at="
                f"{'、'.join(metadata['lineage_recorded_at']) or '—'}"
            )
            lines.append(
                f"- 父事实（{parents['total']} 个，已解决 {parents['resolved']}，"
                f"未解决 {parents['unresolved']}）："
            )
            if not parents["entries"]:
                lines.append("  - 无 parent_fact_ids 记录。")
            for parent in parents["entries"]:
                lines.append(f"  - `{parent['fact_id']}`：{parent['status_label_zh']}")
            lines.append("")
    lines.extend(["## 未解决证据与限制", ""])
    lines.extend(f"- {item}" for item in report["limitations_zh"])
    lines.append("")
    return lines


def render_markdown(report: dict[str, Any]) -> str:
    return "\n".join(_markdown_lines(report))


# --------------------------------------------------------------------------------------
# 导出（先校验/渲染，再排他创建输出根）
# --------------------------------------------------------------------------------------


def build_manifest(report: dict[str, Any], files: dict[str, bytes]) -> dict[str, Any]:
    """Deterministic manifest: rendered file hashes, source digests and the selection."""
    entries = [
        {
            "path": name,
            "byte_count": len(files[name]),
            "sha256": _sha256_bytes(files[name]),
        }
        for name in MANAGED_FILE_NAMES
    ]
    comparison = report["comparison"]
    return {
        "schema": MANIFEST_SCHEMA,
        "report_schema": REPORT_SCHEMA,
        "managed_file_count": len(entries),
        "total_byte_count": sum(entry["byte_count"] for entry in entries),
        "files": entries,
        "request": report["request"],
        "source": report["source"],
        "selection": {
            "as_of": report["request"]["as_of"],
            "selection_count": report["selection_count"],
            "as_of_fact_ids": [entry["fact_id"] for entry in report["selections"]],
            "compare_with": report["request"]["compare_with"],
            "compare_with_fact_ids": (
                sorted(
                    entry["after"]["fact_id"]
                    for entry in comparison["entries"]
                    if entry["after"] is not None
                )
                if comparison is not None
                else []
            ),
            "comparison_count": len(comparison["entries"]) if comparison else 0,
        },
        "boundaries": {
            "network_used": False,
            "caller_database_read": False,
            "default_database_mutated": False,
            "new_metrics_produced": False,
            "current_timestamp_recorded": False,
        },
    }


def export_report(report: dict[str, Any], output: Path) -> dict[str, Any]:
    """Render everything first, then claim the new output root with an exclusive mkdir."""
    files = {
        REPORT_MARKDOWN_NAME: render_markdown(report).encode("utf-8"),
        REPORT_JSON_NAME: render_json(report).encode("utf-8"),
    }
    manifest = build_manifest(report, files)
    manifest_text = json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    manifest_bytes = manifest_text.encode("utf-8")
    try:
        if output.is_symlink() or output.exists():
            raise PitExplorerError("OUTPUT_PATH_EXISTS")
    except OSError as error:
        raise PitExplorerError("OUTPUT_PATH_EXISTS") from error
    try:
        output.mkdir(parents=True, exist_ok=False)
    except FileExistsError as error:
        raise PitExplorerError("OUTPUT_PATH_EXISTS") from error
    except OSError as error:
        raise PitExplorerError("OUTPUT_WRITE_FAILED") from error
    try:
        for name in MANAGED_FILE_NAMES:
            (output / name).write_bytes(files[name])
        (output / MANIFEST_NAME).write_bytes(manifest_bytes)
    except OSError as error:
        raise PitExplorerError("OUTPUT_WRITE_FAILED") from error
    return manifest


# --------------------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------------------


class _SanitizedParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:  # noqa: ARG002 - sanitized by design
        raise PitExplorerError("INVALID_ARGUMENTS")


def _build_parser() -> argparse.ArgumentParser:
    parser = _SanitizedParser(
        prog="python -m ashare_research.tools.pit_fact_explorer",
        description="离线读取固定规范快照，输出指定时点最新可用财务事实与两时点版本对比。",
        add_help=True,
        allow_abbrev=False,
    )
    parser.add_argument("--as-of", required=True, metavar="ISO_DATE", help="PIT 时点（YYYY-MM-DD）")
    parser.add_argument(
        "--compare-with", metavar="ISO_DATE", help="对比时点（YYYY-MM-DD，不得早于 --as-of）"
    )
    parser.add_argument(
        "--concept", action="append", metavar="CONCEPT_ID", help="概念过滤，可重复"
    )
    parser.add_argument("--period-end", metavar="ISO_DATE", help="报告期过滤（YYYY-MM-DD）")
    parser.add_argument(
        "--scope",
        default="consolidated",
        metavar="SCOPE",
        help="合并范围口径：consolidated 或 parent_company",
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--json", action="store_true", help="输出规范 JSON 而非 Markdown")
    mode.add_argument(
        "--output",
        metavar="NEW_DIR",
        help="导出到新目录（report.md/report.json/manifest.json）",
    )
    return parser


def _validated_date(value: str, code: str) -> str:
    try:
        validate_pit_date(value, "date")
    except PointInTimeError as error:
        raise PitExplorerError(code) from error
    return value


def _request_from_arguments(arguments: argparse.Namespace) -> dict[str, Any]:
    as_of = _validated_date(arguments.as_of, "INVALID_AS_OF_DATE")
    compare_with = None
    if arguments.compare_with is not None:
        compare_with = _validated_date(arguments.compare_with, "INVALID_COMPARE_WITH")
        if compare_with < as_of:
            raise PitExplorerError("COMPARE_BEFORE_AS_OF")
    period_end = None
    if arguments.period_end is not None:
        period_end = _validated_date(arguments.period_end, "INVALID_PERIOD_END")
    concepts = sorted({value for value in (arguments.concept or [])})
    if any(value not in CONCEPT_LABELS_ZH for value in concepts):
        raise PitExplorerError("UNKNOWN_CONCEPT")
    if arguments.scope not in SCOPES:
        raise PitExplorerError("INVALID_SCOPE")
    return {
        "as_of": as_of,
        "compare_with": compare_with,
        "concepts": concepts,
        "period_end": period_end,
        "scope": arguments.scope,
    }


def _fail(code: str) -> int:
    code = code if code in KNOWN_ERROR_CODES else "UNEXPECTED_FAILURE"
    sys.stderr.buffer.write(f"error: {code}\n".encode())
    sys.stderr.buffer.flush()
    return 2


def _emit(text: str) -> None:
    """Write UTF-8 bytes regardless of the ambient console encoding."""
    sys.stdout.buffer.write(text.encode("utf-8"))
    sys.stdout.buffer.flush()


def main(argv: list[str] | None = None) -> int:
    """Entry point.  Returns a process exit code; known failures print no stdout."""
    try:
        arguments = _build_parser().parse_args(sys.argv[1:] if argv is None else argv)
    except PitExplorerError:
        return _fail("INVALID_ARGUMENTS")
    except SystemExit as exit_request:  # argparse help / usage
        code = exit_request.code
        return code if isinstance(code, int) else 2
    try:
        request = _request_from_arguments(arguments)
        report = build_report(request)
        if arguments.output is not None:
            manifest = export_report(report, Path(arguments.output))
            _emit(
                "exported "
                + str(manifest["managed_file_count"])
                + " managed files, "
                + str(manifest["total_byte_count"])
                + " bytes\n"
            )
        elif arguments.json:
            _emit(render_json(report))
        else:
            _emit(render_markdown(report))
        return 0
    except PitExplorerError as error:
        return _fail(error.code)
    except Exception:  # noqa: BLE001 - known failures are sanitized, never traced
        return _fail("UNEXPECTED_FAILURE")


if __name__ == "__main__":
    raise SystemExit(main())
