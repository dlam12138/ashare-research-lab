"""只读比较两个显式规范 M4-B registry 产物

    ashare-research research registry-compare --left ARTIFACT.json --right ARTIFACT.json
        [--summary] [--json]

本模块只读取调用者显式给出的两个 JSON 文件（各一次，上限 1MiB），按与
``research registry`` 完全相同的严格字节规则解码，并把每一侧判定为 record 或
snapshot：解码文档只要含有七个冻结 snapshot 顶层键中的任意一个就按 snapshot
校验，否则按 record 校验；判定只决定使用哪套冻结校验，不放松任何规则。两侧
校验复用既有 view 入口（``build_record_view`` / ``build_snapshot_view``），
因此单侧失败保持既有冻结稳定错误码；两侧类型不同则以
``INCOMPARABLE_ARTIFACT_KINDS`` 失败。输出 schema ``m4_registry_comparison_v1``
只描述机械结构差异：不产生、不写入、不修复、不提升任何记录、快照或状态，
也不加载默认或真实候选数据集，不访问数据库、provider、网络、时钟或 holdout；
``mechanism/registry`` 包保持不变。``--summary`` 只投影同一次捕获比较的类别级
摘要：record 按身份（identity）／可变（mutable）／摘要（digest）三类的冻结字段
划分统计变更，snapshot 汇总 added/removed/changed/unchanged；不重新读取两侧
文件、不重新计算差异，也不写入任何产物。
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from ashare_research.mechanism.registry import RegistryError
from ashare_research.mechanism.registry.records import IDENTITY_FIELDS, RECORD_FIELDS
from ashare_research.tools import research_registry

SCHEMA = "m4_registry_comparison_v1"
STATUS = "read_only_comparison"
RECORD_KIND = "record"
SNAPSHOT_KIND = "snapshot"
SNAPSHOT_KEYS = frozenset(research_registry.SNAPSHOT_FIELDS)
IDENTITY_KEYS = (
    "hypothesis_id",
    "hypothesis_version",
    "status",
    "identity_digest",
    "record_digest",
    "state_count",
)
REGISTRY_EQUALITY_KEYS = (
    "registry_schema_version",
    "registry_version",
    "registry_digest",
    "record_count",
    "real_demo_candidate_count",
)
NOTES = (
    "比较只做只读机械差异：两侧文件分别经冻结 registry 入口校验，任何一侧失败即 fail-closed。",
    "两侧都必须通过规范字节复核，因此文件 SHA256 相同等价于规范内容相同；差异不判断哪一侧正确。",
    "身份摘要、记录摘要、状态与计数只比较两侧冻结重算结果，不构成证据、研究结论或执行授权。",
    "比较不写入、不修复、不提升，也不产生新记录、快照或回执；registry 元数据不是证据。",
    "本工具不加载默认或真实候选数据集，不访问数据库、provider、网络、时钟或 holdout。",
)
SUMMARY_SCHEMA = "m4_registry_comparison_summary_v1"
SUMMARY_STATUS = "read_only_comparison_summary"
RECORD_CLASS_ORDER = ("identity", "mutable", "digest")
MUTABLE_FIELDS = ("status", "state_history")
DIGEST_FIELDS = ("identity_digest", "record_digest")
DIGEST_COVERAGE = {
    "identity_digest": ("identity",),
    "record_digest": ("identity", "mutable"),
}
SUMMARY_NOTES = (
    "摘要只是既有只读比较结果的类别级投影：不重新读取两侧文件、不重新计算差异，"
    "也不写入、不修复、不提升任何记录或状态。",
    "record 类别划分取冻结 records 导出：identity 为身份承载字段，mutable 仅 "
    "status 与 state_history，digest 为两个派生摘要字段。",
    "身份承载字段在同一 (hypothesis_id, hypothesis_version) 内不可变；身份类字段变化"
    "意味着应作为新记录处理，本摘要不代替该流程。",
    "摘要不判断哪一侧正确，不构成证据、研究结论或执行授权；registry 元数据不是 A 股证据。",
    "本工具不加载默认或真实候选数据集，不访问数据库、provider、网络、时钟或 holdout。",
)


class ComparisonError(Exception):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def _classify(document: dict[str, Any]) -> str:
    return SNAPSHOT_KIND if SNAPSHOT_KEYS & set(document) else RECORD_KIND


def _record_identity(view: dict[str, Any]) -> dict[str, Any]:
    record = view["record"]
    return {
        "file_sha256": view["source_file_sha256"],
        "hypothesis_id": record["hypothesis_id"],
        "hypothesis_version": record["hypothesis_version"],
        "status": record["status"],
        "identity_digest": record["identity_digest"],
        "record_digest": record["record_digest"],
        "state_count": len(record["state_history"]),
    }


def _snapshot_identity(view: dict[str, Any]) -> dict[str, Any]:
    registry = view["registry"]
    return {
        "file_sha256": view["source_file_sha256"],
        "registry_schema_version": registry["registry_schema_version"],
        "registry_version": registry["registry_version"],
        "registry_digest": registry["registry_digest"],
        "record_count": registry["record_count"],
        "real_demo_candidate_count": registry["real_demo_candidate_count"],
    }


def _compare_records(left_view: dict[str, Any], right_view: dict[str, Any]) -> dict[str, Any]:
    left, right = left_view["record"], right_view["record"]
    left_identity, right_identity = _record_identity(left_view), _record_identity(right_view)
    changed = [
        {"field": name, "left": left[name], "right": right[name]}
        for name in sorted(left)
        if left[name] != right[name]
    ]
    return {
        "record_equal": left == right,
        "changed_field_count": len(changed),
        "changed_fields": changed,
        "equality": {
            name: left_identity[name] == right_identity[name] for name in IDENTITY_KEYS
        },
    }


def _record_key(item: dict[str, Any]) -> tuple[str, int]:
    return (item["hypothesis_id"], item["hypothesis_version"])


def _record_projection(item: dict[str, Any]) -> dict[str, Any]:
    return {name: item[name] for name in IDENTITY_KEYS}


def _compare_snapshots(left_view: dict[str, Any], right_view: dict[str, Any]) -> dict[str, Any]:
    left = {_record_key(item): item for item in left_view["records"]}
    right = {_record_key(item): item for item in right_view["records"]}
    added = [_record_projection(right[key]) for key in sorted(right.keys() - left.keys())]
    removed = [_record_projection(left[key]) for key in sorted(left.keys() - right.keys())]
    changed = []
    unchanged = 0
    for key in sorted(left.keys() & right.keys()):
        if left[key] == right[key]:
            unchanged += 1
            continue
        changed.append(
            {
                "hypothesis_id": key[0],
                "hypothesis_version": key[1],
                "left": _record_projection(left[key]),
                "right": _record_projection(right[key]),
            },
        )
    left_identity, right_identity = _snapshot_identity(left_view), _snapshot_identity(right_view)
    return {
        "registry_equal": left_view["registry"] == right_view["registry"],
        "equality": {
            name: left_identity[name] == right_identity[name] for name in REGISTRY_EQUALITY_KEYS
        },
        "added_count": len(added),
        "removed_count": len(removed),
        "changed_count": len(changed),
        "unchanged_count": unchanged,
        "added": added,
        "removed": removed,
        "changed": changed,
    }


def build_comparison(left_payload: bytes, right_payload: bytes) -> dict[str, Any]:
    """Compare two canonical registry artifacts through the frozen entry points."""
    left_kind = _classify(research_registry.strict_json_document(left_payload))
    right_kind = _classify(research_registry.strict_json_document(right_payload))
    if left_kind != right_kind:
        raise ComparisonError("INCOMPARABLE_ARTIFACT_KINDS")
    if left_kind == SNAPSHOT_KIND:
        left_view = research_registry.build_snapshot_view(left_payload)
        right_view = research_registry.build_snapshot_view(right_payload)
        left_identity = _snapshot_identity(left_view)
        right_identity = _snapshot_identity(right_view)
        differences = _compare_snapshots(left_view, right_view)
    else:
        left_view = research_registry.build_record_view(left_payload)
        right_view = research_registry.build_record_view(right_payload)
        left_identity = _record_identity(left_view)
        right_identity = _record_identity(right_view)
        differences = _compare_records(left_view, right_view)
    return {
        "schema": SCHEMA,
        "status": STATUS,
        "kind": left_kind,
        "byte_identical": left_payload == right_payload,
        "left": left_identity,
        "right": right_identity,
        "differences": differences,
        "boundary": dict(research_registry.BOUNDARY),
        "notes": list(NOTES),
    }


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False)


def _cell(value: Any) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ").replace("\r", " ")


def render_markdown(comparison: dict[str, Any]) -> str:
    lines = [
        "# M4-B registry 产物只读比较",
        "",
        "两侧产物已按冻结入口复核；比较只输出机械差异，不写入、不修复、不提升。",
        "",
        "## 比较对象",
        "",
        "```json",
        _json(
            {
                "kind": comparison["kind"],
                "byte_identical": comparison["byte_identical"],
                "left": comparison["left"],
                "right": comparison["right"],
            },
        ),
        "```",
    ]
    differences = comparison["differences"]
    if comparison["kind"] == RECORD_KIND:
        lines.extend(
            [
                "",
                "## 字段差异",
                "",
                "| field | left | right |",
                "| --- | --- | --- |",
                *(
                    "| " + " | ".join(map(_cell, (row["field"], row["left"], row["right"]))) + " |"
                    for row in differences["changed_fields"]
                ),
                "",
                "## 等价性",
                "",
                "```json",
                _json(
                    {
                        "record_equal": differences["record_equal"],
                        "changed_field_count": differences["changed_field_count"],
                        "equality": differences["equality"],
                    },
                ),
                "```",
            ],
        )
    else:
        lines.extend(
            [
                "",
                "## 记录差异",
                "",
                "```json",
                _json(
                    {
                        "registry_equal": differences["registry_equal"],
                        "equality": differences["equality"],
                        "added_count": differences["added_count"],
                        "removed_count": differences["removed_count"],
                        "changed_count": differences["changed_count"],
                        "unchanged_count": differences["unchanged_count"],
                        "added": differences["added"],
                        "removed": differences["removed"],
                        "changed": differences["changed"],
                    },
                ),
                "```",
            ],
        )
    lines.extend(
        ["", "## 执行边界", "", "```json", _json(comparison["boundary"]), "```"],
    )
    lines.extend(["", "## 限制", "", *(f"- {note}" for note in comparison["notes"])])
    return "\n".join(lines) + "\n"


def _summary_fail() -> None:
    raise ComparisonError("REGISTRY_COMPARISON_SUMMARY_MISMATCH")


def _record_field_classes() -> dict[str, str]:
    classes = {name: "identity" for name in IDENTITY_FIELDS}
    classes.update({name: "mutable" for name in MUTABLE_FIELDS})
    classes.update({name: "digest" for name in DIGEST_FIELDS})
    if (
        tuple(IDENTITY_FIELDS) != RECORD_FIELDS[: len(IDENTITY_FIELDS)]
        or set(classes) != set(RECORD_FIELDS)
        or len(classes) != len(RECORD_FIELDS)
    ):
        _summary_fail()
    return classes


def _record_summary(comparison: dict[str, Any]) -> dict[str, Any]:
    left, right = comparison["left"], comparison["right"]
    differences = comparison["differences"]
    side_keys = {"file_sha256", *IDENTITY_KEYS}
    if set(left) != side_keys or set(right) != side_keys:
        _summary_fail()
    if set(differences) != {"record_equal", "changed_field_count", "changed_fields", "equality"}:
        _summary_fail()
    if type(differences["record_equal"]) is not bool:
        _summary_fail()
    if type(differences["changed_field_count"]) is not int:
        _summary_fail()
    equality = differences["equality"]
    if type(equality) is not dict or set(equality) != set(IDENTITY_KEYS):
        _summary_fail()
    if any(type(equality[name]) is not bool for name in IDENTITY_KEYS):
        _summary_fail()
    if any(equality[name] != (left[name] == right[name]) for name in IDENTITY_KEYS):
        _summary_fail()
    rows = differences["changed_fields"]
    if type(rows) is not list:
        _summary_fail()
    classes = _record_field_classes()
    changed = []
    for row in rows:
        if type(row) is not dict or set(row) != {"field", "left", "right"}:
            _summary_fail()
        name = row["field"]
        if type(name) is not str or name not in classes:
            _summary_fail()
        changed.append(name)
    changed_set = set(changed)
    if len(changed_set) != len(changed):
        _summary_fail()
    if differences["changed_field_count"] != len(changed):
        _summary_fail()
    if differences["record_equal"] != (not changed):
        _summary_fail()
    if differences["record_equal"] and not all(equality[name] for name in IDENTITY_KEYS):
        _summary_fail()
    if left["file_sha256"] == right["file_sha256"] and not differences["record_equal"]:
        _summary_fail()
    for name in ("status", "identity_digest", "record_digest"):
        if equality[name] != (name not in changed_set):
            _summary_fail()
    changed_classes = {classes[name] for name in changed}
    for digest_field in DIGEST_FIELDS:
        coverage = set(DIGEST_COVERAGE[digest_field])
        if (digest_field in changed_set) != bool(coverage & changed_classes):
            _summary_fail()
    by_class = {
        name: [field for field in RECORD_FIELDS if field in changed_set and classes[field] == name]
        for name in RECORD_CLASS_ORDER
    }
    counts = {name: len(by_class[name]) for name in RECORD_CLASS_ORDER}
    if sum(counts.values()) != len(changed):
        _summary_fail()
    return {
        "record_equal": differences["record_equal"],
        "changed_field_count": len(changed),
        "unchanged_field_count": len(RECORD_FIELDS) - len(changed),
        "field_count": len(RECORD_FIELDS),
        "changed_field_class_counts": counts,
        "changed_fields_by_class": by_class,
        "equality": {name: equality[name] for name in IDENTITY_KEYS},
    }


def _snapshot_summary(comparison: dict[str, Any]) -> dict[str, Any]:
    left, right = comparison["left"], comparison["right"]
    differences = comparison["differences"]
    side_keys = {"file_sha256", *REGISTRY_EQUALITY_KEYS}
    if set(left) != side_keys or set(right) != side_keys:
        _summary_fail()
    if set(differences) != {
        "registry_equal",
        "equality",
        "added_count",
        "removed_count",
        "changed_count",
        "unchanged_count",
        "added",
        "removed",
        "changed",
    }:
        _summary_fail()
    if type(differences["registry_equal"]) is not bool:
        _summary_fail()
    for name in ("added_count", "removed_count", "changed_count", "unchanged_count"):
        if type(differences[name]) is not int or differences[name] < 0:
            _summary_fail()
    equality = differences["equality"]
    if type(equality) is not dict or set(equality) != set(REGISTRY_EQUALITY_KEYS):
        _summary_fail()
    if any(type(equality[name]) is not bool for name in REGISTRY_EQUALITY_KEYS):
        _summary_fail()
    if any(equality[name] != (left[name] == right[name]) for name in REGISTRY_EQUALITY_KEYS):
        _summary_fail()
    if differences["registry_equal"] and not all(equality.values()):
        _summary_fail()
    if left["file_sha256"] == right["file_sha256"] and not differences["registry_equal"]:
        _summary_fail()
    rows = {}
    for name in ("added", "removed", "changed"):
        if type(differences[name]) is not list:
            _summary_fail()
        rows[name] = differences[name]
    pairs = {}
    for name in ("added", "removed"):
        pair_list = []
        for row in rows[name]:
            if type(row) is not dict or set(row) != set(IDENTITY_KEYS):
                _summary_fail()
            pair = (row["hypothesis_id"], row["hypothesis_version"])
            if type(pair[0]) is not str or type(pair[1]) is not int:
                _summary_fail()
            pair_list.append(pair)
        pairs[name] = pair_list
    pair_list = []
    for row in rows["changed"]:
        if type(row) is not dict or set(row) != {
            "hypothesis_id",
            "hypothesis_version",
            "left",
            "right",
        }:
            _summary_fail()
        if type(row["left"]) is not dict or type(row["right"]) is not dict:
            _summary_fail()
        if set(row["left"]) != set(IDENTITY_KEYS) or set(row["right"]) != set(IDENTITY_KEYS):
            _summary_fail()
        if row["left"] == row["right"]:
            _summary_fail()
        pair = (row["hypothesis_id"], row["hypothesis_version"])
        if type(pair[0]) is not str or type(pair[1]) is not int:
            _summary_fail()
        if (row["left"]["hypothesis_id"], row["left"]["hypothesis_version"]) != pair:
            _summary_fail()
        if (row["right"]["hypothesis_id"], row["right"]["hypothesis_version"]) != pair:
            _summary_fail()
        pair_list.append(pair)
    pairs["changed"] = pair_list
    counts = {name: len(pairs[name]) for name in ("added", "removed", "changed")}
    for name in ("added", "removed", "changed"):
        if differences[f"{name}_count"] != counts[name]:
            _summary_fail()
        if len(set(pairs[name])) != counts[name] or pairs[name] != sorted(pairs[name]):
            _summary_fail()
    if (
        set(pairs["added"]) & set(pairs["removed"])
        or set(pairs["added"]) & set(pairs["changed"])
        or set(pairs["removed"]) & set(pairs["changed"])
    ):
        _summary_fail()
    unchanged = differences["unchanged_count"]
    if left["record_count"] != counts["removed"] + counts["changed"] + unchanged:
        _summary_fail()
    if right["record_count"] != counts["added"] + counts["changed"] + unchanged:
        _summary_fail()
    return {
        "registry_equal": differences["registry_equal"],
        "equality": {name: equality[name] for name in REGISTRY_EQUALITY_KEYS},
        "record_change_counts": {
            "added": counts["added"],
            "removed": counts["removed"],
            "changed": counts["changed"],
            "unchanged": unchanged,
        },
        "added": [f"{pair[0]}@{pair[1]}" for pair in pairs["added"]],
        "removed": [f"{pair[0]}@{pair[1]}" for pair in pairs["removed"]],
        "changed": [f"{pair[0]}@{pair[1]}" for pair in pairs["changed"]],
    }


def _build_summary(comparison: dict[str, Any]) -> dict[str, Any]:
    if type(comparison) is not dict:
        _summary_fail()
    if comparison.get("schema") != SCHEMA or comparison.get("status") != STATUS:
        _summary_fail()
    kind = comparison.get("kind")
    if kind not in (RECORD_KIND, SNAPSHOT_KIND):
        _summary_fail()
    left, right = comparison.get("left"), comparison.get("right")
    if type(left) is not dict or type(right) is not dict:
        _summary_fail()
    if type(comparison.get("byte_identical")) is not bool:
        _summary_fail()
    if comparison["byte_identical"] != (left.get("file_sha256") == right.get("file_sha256")):
        _summary_fail()
    if comparison.get("boundary") != research_registry.BOUNDARY:
        _summary_fail()
    if type(comparison.get("differences")) is not dict:
        _summary_fail()
    payload = _record_summary(comparison) if kind == RECORD_KIND else _snapshot_summary(comparison)
    return {
        "schema": SUMMARY_SCHEMA,
        "status": SUMMARY_STATUS,
        "kind": kind,
        "byte_identical": comparison["byte_identical"],
        "left": dict(left),
        "right": dict(right),
        "summary": payload,
        "boundary": dict(comparison["boundary"]),
        "notes": list(SUMMARY_NOTES),
    }


def _render_summary_markdown(summary: dict[str, Any]) -> str:
    lines = [
        "# M4-B registry 产物比较聚焦摘要",
        "",
        "两侧产物已按冻结入口复核；摘要只是既有只读比较的类别级投影，不重新读取或计算差异。",
        "",
        "## 比较对象",
        "",
        "```json",
        _json(
            {
                "kind": summary["kind"],
                "byte_identical": summary["byte_identical"],
                "left": summary["left"],
                "right": summary["right"],
            },
        ),
        "```",
    ]
    payload = summary["summary"]
    if summary["kind"] == RECORD_KIND:
        lines.extend(
            [
                "",
                "## 字段类别变更",
                "",
                "| class | changed |",
                "| --- | --- |",
                *(
                    f"| {name} | {payload['changed_field_class_counts'][name]} |"
                    for name in RECORD_CLASS_ORDER
                ),
            ],
        )
        lines.append("")
        for name in RECORD_CLASS_ORDER:
            fields = payload["changed_fields_by_class"][name]
            lines.append(f"- {name}: " + ("、".join(fields) if fields else "（无变更）"))
        lines.extend(
            [
                "",
                "## 等价性",
                "",
                "```json",
                _json(
                    {
                        "record_equal": payload["record_equal"],
                        "changed_field_count": payload["changed_field_count"],
                        "unchanged_field_count": payload["unchanged_field_count"],
                        "field_count": payload["field_count"],
                        "equality": payload["equality"],
                    },
                ),
                "```",
            ],
        )
    else:
        lines.extend(
            [
                "",
                "## 记录变更",
                "",
                "```json",
                _json(
                    {
                        "registry_equal": payload["registry_equal"],
                        "equality": payload["equality"],
                        "record_change_counts": payload["record_change_counts"],
                        "added": payload["added"],
                        "removed": payload["removed"],
                        "changed": payload["changed"],
                    },
                ),
                "```",
            ],
        )
    lines.extend(["", "## 执行边界", "", "```json", _json(summary["boundary"]), "```"])
    lines.extend(["", "## 限制", "", *(f"- {note}" for note in summary["notes"])])
    return "\n".join(lines) + "\n"


class _Parser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise ComparisonError("INVALID_ARGUMENTS")


def main(argv: list[str] | None = None) -> int:
    parser = _Parser(
        description="只读比较两个显式规范 M4-B registry 产物（record 或 snapshot）",
        allow_abbrev=False,
    )
    parser.add_argument("--left", metavar="JSON", required=True)
    parser.add_argument("--right", metavar="JSON", required=True)
    parser.add_argument(
        "--summary", action="store_true", help="只投影类别级聚焦摘要（不重新读取或计算）",
    )
    parser.add_argument("--json", action="store_true")
    try:
        args = parser.parse_args(argv)
        comparison = build_comparison(
            research_registry.read_registry_bytes(Path(args.left)),
            research_registry.read_registry_bytes(Path(args.right)),
        )
        if args.summary:
            summary = _build_summary(comparison)
            text = _json(summary) + "\n" if args.json else _render_summary_markdown(summary)
        else:
            text = _json(comparison) + "\n" if args.json else render_markdown(comparison)
        sys.stdout.buffer.write(text.encode("utf-8"))
        sys.stdout.buffer.flush()
        return 0
    except SystemExit as error:
        return error.code if isinstance(error.code, int) else 2
    except Exception as error:  # noqa: BLE001 - sanitized, no partial output
        code = (
            error.code
            if isinstance(
                error,
                (ComparisonError, research_registry.RegistryViewError, RegistryError),
            )
            else "REGISTRY_COMPARISON_FAILED"
        )
        sys.stderr.buffer.write(f"error: {code}\n".encode())
        sys.stderr.buffer.flush()
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
