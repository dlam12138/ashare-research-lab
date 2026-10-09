"""只读检查一条显式规范 M4-B 记录是否已登记在显式 registry 快照中

    ashare-research research registry-membership --record RECORD.json
        --snapshot SNAPSHOT.json [--json]

本模块只读取调用者显式给出的两个 JSON 文件（各一次，上限 1MiB）：record
经冻结的 ``build_record_view`` 复核，snapshot 经冻结的 ``build_snapshot_view``
复核，因此单侧失败保持既有冻结稳定错误码。两侧都通过后，工具只回答机械成员
关系：快照中是否存在同 ``(hypothesis_id, hypothesis_version)`` 的登记项，以及
该登记项的规范记录字节是否与显式记录一致；同键但字节不同时输出机械字段差异
与等价性，键不存在时列出该假设 ID 在快照中出现的版本。工具不产生、不写入、
不修复、不提升任何记录、快照或状态，不重新实现任何 registry 语义校验，也不
加载默认或真实候选数据集，不访问数据库、provider、网络、时钟或 holdout。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

from ashare_research.mechanism.registry import (
    RegistryError,
    build_hypothesis_registry_snapshot,
    count_real_demo_candidates,
    hypothesis_record_digest,
    hypothesis_record_identity_digest,
    hypothesis_record_to_canonical_dict,
    parse_hypothesis_record,
    serialize_hypothesis_record,
)
from ashare_research.mechanism.registry.records import IDENTITY_FIELDS, RECORD_FIELDS
from ashare_research.tools import research_registry

SCHEMA = "m4_registry_snapshot_membership_v1"
STATUS_IDENTICAL = "registered_identical"
STATUS_DIFFERENT = "registered_different"
STATUS_ABSENT = "not_registered"
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
REGISTRY_VIEW_KEYS = (
    "registry_schema_version",
    "registry_version",
    "digest_algorithm",
    "record_count",
    "real_demo_candidate_count",
    "max_records_per_snapshot",
    "max_real_demo_candidates",
    "registry_digest",
)
RECORD_PROJECTION_KEYS = (
    "hypothesis_id",
    "hypothesis_version",
    "status",
    "source_type",
    "a_share_data_feasibility",
    "free_data_feasibility",
    "identity_digest",
    "record_digest",
    "state_count",
)
MUTABLE_FIELDS = ("status", "state_history")
DIGEST_FIELDS = ("identity_digest", "record_digest")
DIGEST_COVERAGE = {
    "identity_digest": ("identity",),
    "record_digest": ("identity", "mutable"),
}
NOTES = (
    "成员关系检查只做只读机械判断：两侧文件分别经冻结 registry 入口复核，"
    "任何一侧失败即 fail-closed。",
    "两侧都必须通过规范字节复核，因此规范字节一致等价于规范内容一致；不一致只描述机械差异。",
    "检查只回答“是否登记、登记项是否一致”，不判断哪一侧正确，也不构成证据、研究结论或执行授权。",
    "键不存在时每个等价性布尔一律为 false：没有可比对的登记项，不代表任何一侧有误。",
    "本工具不写入、不修复、不提升，也不加载默认或真实候选数据集，"
    "不访问数据库、provider、网络或 holdout。",
)


class MembershipError(Exception):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def _mismatch() -> None:
    raise MembershipError("REGISTRY_MEMBERSHIP_MISMATCH")


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _canonical_bytes(document: dict[str, Any]) -> bytes:
    return (
        json.dumps(document, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
    ).encode("utf-8")


def _field_classes() -> dict[str, str]:
    classes = {name: "identity" for name in IDENTITY_FIELDS}
    classes.update({name: "mutable" for name in MUTABLE_FIELDS})
    classes.update({name: "digest" for name in DIGEST_FIELDS})
    if (
        tuple(IDENTITY_FIELDS) != RECORD_FIELDS[: len(IDENTITY_FIELDS)]
        or set(classes) != set(RECORD_FIELDS)
        or len(classes) != len(RECORD_FIELDS)
    ):
        _mismatch()
    return classes


def _record_identity_block(view: dict[str, Any]) -> dict[str, Any]:
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


def _snapshot_identity_block(view: dict[str, Any]) -> dict[str, Any]:
    registry = view["registry"]
    return {
        "file_sha256": view["source_file_sha256"],
        "registry_schema_version": registry["registry_schema_version"],
        "registry_version": registry["registry_version"],
        "registry_digest": registry["registry_digest"],
        "record_count": registry["record_count"],
        "real_demo_candidate_count": registry["real_demo_candidate_count"],
    }


def _embedded_entries(
    document: dict[str, Any], projections: list[Any], registry: dict[str, Any],
) -> list[tuple[dict[str, Any], bytes]]:
    embedded = document["records"]
    if type(embedded) is not list or len(embedded) != len(projections):
        _mismatch()
    entries = []
    parsed_records = []
    for item, projection in zip(embedded, projections, strict=True):
        if type(item) is not dict:
            _mismatch()
        try:
            parsed = parse_hypothesis_record(_canonical_bytes(item))
            canonical = hypothesis_record_to_canonical_dict(parsed)
            payload = serialize_hypothesis_record(parsed)
            identity = hypothesis_record_identity_digest(parsed)
            digest = hypothesis_record_digest(parsed)
        except (RegistryError, TypeError, ValueError):
            _mismatch()
        if canonical["identity_digest"] != identity or canonical["record_digest"] != digest:
            _mismatch()
        expected_projection = {
            "hypothesis_id": canonical["hypothesis_id"],
            "hypothesis_version": canonical["hypothesis_version"],
            "status": canonical["status"],
            "source_type": canonical["source_type"],
            "a_share_data_feasibility": canonical["a_share_data_feasibility"],
            "free_data_feasibility": canonical["free_data_feasibility"],
            "identity_digest": canonical["identity_digest"],
            "record_digest": canonical["record_digest"],
            "state_count": len(canonical["state_history"]),
        }
        if projection != expected_projection:
            _mismatch()
        parsed_records.append(parsed)
        entries.append((canonical, payload))
    keys = [(entry[0]["hypothesis_id"], entry[0]["hypothesis_version"]) for entry in entries]
    if len(set(keys)) != len(keys) or keys != sorted(keys):
        _mismatch()
    if registry["record_count"] != len(entries):
        _mismatch()
    try:
        rebuilt = build_hypothesis_registry_snapshot(tuple(parsed_records))
        real_demo_count = count_real_demo_candidates(rebuilt)
    except (RegistryError, TypeError, ValueError):
        _mismatch()
    if registry["real_demo_candidate_count"] != real_demo_count:
        _mismatch()
    if registry["registry_digest"] != rebuilt.registry_digest:
        _mismatch()
    return entries


def _membership(
    record_payload: bytes,
    record_document: dict[str, Any],
    entries: list[tuple[dict[str, Any], bytes]],
) -> dict[str, Any]:
    record_id = record_document["hypothesis_id"]
    record_version = record_document["hypothesis_version"]
    same_id_versions = sorted(
        entry[0]["hypothesis_version"]
        for entry in entries
        if entry[0]["hypothesis_id"] == record_id
    )
    found = record_version in same_id_versions
    if found:
        entry_document, entry_payload = next(
            entry for entry in entries
            if (entry[0]["hypothesis_id"], entry[0]["hypothesis_version"])
            == (record_id, record_version)
        )
        changed = [
            {"field": name, "record": record_document[name], "snapshot": entry_document[name]}
            for name in sorted(record_document)
            if record_document[name] != entry_document[name]
        ]
        canonical_equal = entry_payload == record_payload
        equality = {
            name: record_document[name] == entry_document[name]
            for name in IDENTITY_KEYS
            if name != "state_count"
        }
        equality["state_count"] = (
            len(record_document["state_history"]) == len(entry_document["state_history"])
        )
    else:
        changed = []
        canonical_equal = False
        equality = {name: False for name in IDENTITY_KEYS}
    changed_names = [row["field"] for row in changed]
    if (
        len(set(changed_names)) != len(changed_names)
        or not set(changed_names) <= set(RECORD_FIELDS)
    ):
        _mismatch()
    if found:
        if canonical_equal != (not changed_names):
            _mismatch()
    elif changed_names or canonical_equal or any(equality.values()):
        _mismatch()
    if found:
        for name in ("status", "identity_digest", "record_digest"):
            if equality[name] != (name not in set(changed_names)):
                _mismatch()
    classes = _field_classes()
    changed_classes = {classes[name] for name in changed_names}
    for digest_field in DIGEST_FIELDS:
        coverage = set(DIGEST_COVERAGE[digest_field])
        if (digest_field in set(changed_names)) != bool(coverage & changed_classes):
            _mismatch()
    if found and len(same_id_versions) != len(set(same_id_versions)):
        _mismatch()
    for name in IDENTITY_KEYS:
        if type(equality[name]) is not bool:
            _mismatch()
    status = (
        STATUS_IDENTICAL if canonical_equal else
        STATUS_DIFFERENT if found else
        STATUS_ABSENT
    )
    return {
        "status": status,
        "membership": {
            "found": found,
            "same_id_versions": same_id_versions,
            "canonical_equal": canonical_equal,
            "changed_field_count": len(changed),
            "changed_fields": changed,
            "equality": {name: equality[name] for name in IDENTITY_KEYS},
        },
    }


REPORT_KEYS = ("schema", "status", "record", "snapshot", "membership", "boundary", "notes")
RECORD_BLOCK_KEYS = (
    "file_sha256",
    "hypothesis_id",
    "hypothesis_version",
    "status",
    "identity_digest",
    "record_digest",
    "state_count",
)
SNAPSHOT_BLOCK_KEYS = (
    "file_sha256",
    "registry_schema_version",
    "registry_version",
    "registry_digest",
    "record_count",
    "real_demo_candidate_count",
)
MEMBERSHIP_KEYS = (
    "found",
    "same_id_versions",
    "canonical_equal",
    "changed_field_count",
    "changed_fields",
    "equality",
)
CHANGED_FIELD_KEYS = ("field", "record", "snapshot")


def _verify_report(membership: dict[str, Any]) -> None:
    if type(membership) is not dict or set(membership) != set(REPORT_KEYS):
        _mismatch()
    if membership["schema"] != SCHEMA:
        _mismatch()
    if membership["boundary"] != research_registry.BOUNDARY:
        _mismatch()
    if membership["notes"] != list(NOTES):
        _mismatch()
    record = membership["record"]
    snapshot = membership["snapshot"]
    if type(record) is not dict or set(record) != set(RECORD_BLOCK_KEYS):
        _mismatch()
    if type(snapshot) is not dict or set(snapshot) != set(SNAPSHOT_BLOCK_KEYS):
        _mismatch()
    for block in (record, snapshot):
        for name in ("file_sha256", "identity_digest", "record_digest", "registry_digest"):
            value = block.get(name)
            if value is None:
                continue
            if (
                type(value) is not str
                or len(value) != 64
                or any(character not in "0123456789abcdef" for character in value)
            ):
                _mismatch()
    payload = membership["membership"]
    if type(payload) is not dict or set(payload) != set(MEMBERSHIP_KEYS):
        _mismatch()
    found = payload["found"]
    canonical_equal = payload["canonical_equal"]
    if type(found) is not bool or type(canonical_equal) is not bool:
        _mismatch()
    versions = payload["same_id_versions"]
    if (
        type(versions) is not list
        or any(type(version) is not int for version in versions)
        or versions != sorted(set(versions))
    ):
        _mismatch()
    if found != (record["hypothesis_version"] in versions):
        _mismatch()
    changed = payload["changed_fields"]
    if type(changed) is not list:
        _mismatch()
    for row in changed:
        if type(row) is not dict or set(row) != set(CHANGED_FIELD_KEYS):
            _mismatch()
    names = [row["field"] for row in changed]
    if len(set(names)) != len(names) or not set(names) <= set(RECORD_FIELDS):
        _mismatch()
    if payload["changed_field_count"] != len(changed):
        _mismatch()
    if canonical_equal != (found and not names):
        _mismatch()
    expected_status = (
        STATUS_IDENTICAL if canonical_equal else
        STATUS_DIFFERENT if found else
        STATUS_ABSENT
    )
    if membership["status"] != expected_status:
        _mismatch()
    equality = payload["equality"]
    if (
        type(equality) is not dict
        or set(equality) != set(IDENTITY_KEYS)
        or any(type(value) is not bool for value in equality.values())
    ):
        _mismatch()
    if not found and any(equality.values()):
        _mismatch()
    if found:
        for name in ("status", "identity_digest", "record_digest"):
            if equality[name] == (name in set(names)):
                _mismatch()
    classes = _field_classes()
    changed_classes = {classes[name] for name in names}
    for digest_field in DIGEST_FIELDS:
        coverage = set(DIGEST_COVERAGE[digest_field])
        if (digest_field in set(names)) != bool(coverage & changed_classes):
            _mismatch()


def build_membership(record_payload: bytes, snapshot_payload: bytes) -> dict[str, Any]:
    """Check one verified record against one verified snapshot through frozen entries."""
    record_view = research_registry.build_record_view(record_payload)
    snapshot_view = research_registry.build_snapshot_view(snapshot_payload)
    document = research_registry.strict_json_document(snapshot_payload)
    if record_view.get("schema") != research_registry.SCHEMA_RECORD_VIEW:
        _mismatch()
    if record_view.get("status") != research_registry.VIEW_STATUS:
        _mismatch()
    if record_view.get("source_file_sha256") != _sha256(record_payload):
        _mismatch()
    record_document = record_view.get("record")
    if type(record_document) is not dict or set(record_document) != set(RECORD_FIELDS):
        _mismatch()
    verification = record_view.get("verification")
    if (
        type(verification) is not dict
        or set(verification) != {
            "canonical_bytes_verified",
            "identity_digest_verified",
            "record_digest_verified",
        }
        or not all(value is True for value in verification.values())
    ):
        _mismatch()
    try:
        canonical = hypothesis_record_to_canonical_dict(parse_hypothesis_record(record_payload))
    except RegistryError:
        _mismatch()
    if canonical != record_document:
        _mismatch()
    if snapshot_view.get("schema") != research_registry.SCHEMA_SNAPSHOT_VIEW:
        _mismatch()
    if snapshot_view.get("status") != research_registry.VIEW_STATUS:
        _mismatch()
    if snapshot_view.get("source_file_sha256") != _sha256(snapshot_payload):
        _mismatch()
    registry = snapshot_view.get("registry")
    if type(registry) is not dict or set(registry) != set(REGISTRY_VIEW_KEYS):
        _mismatch()
    projections = snapshot_view.get("records")
    if type(projections) is not list:
        _mismatch()
    for projection in projections:
        if type(projection) is not dict or set(projection) != set(RECORD_PROJECTION_KEYS):
            _mismatch()
    if set(document) != set(research_registry.SNAPSHOT_FIELDS):
        _mismatch()
    entries = _embedded_entries(document, projections, registry)
    result = _membership(record_payload, record_document, entries)
    return {
        "schema": SCHEMA,
        "status": result["status"],
        "record": _record_identity_block(record_view),
        "snapshot": _snapshot_identity_block(snapshot_view),
        "membership": result["membership"],
        "boundary": dict(research_registry.BOUNDARY),
        "notes": list(NOTES),
    }


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False)


def _cell(value: Any) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ").replace("\r", " ")


STATUS_LABELS = {
    STATUS_IDENTICAL: "已登记且规范记录字节一致",
    STATUS_DIFFERENT: "已登记但规范记录字节不同",
    STATUS_ABSENT: "未登记（快照中没有该键）",
}


def render_markdown(membership: dict[str, Any]) -> str:
    payload = membership["membership"]
    lines = [
        "# M4-B registry 记录成员关系只读检查",
        "",
        "两侧产物已按冻结入口复核；本检查只回答机械成员关系，不写入、不修复、不提升。",
        "",
        "## 结论",
        "",
        f"- 状态：`{membership['status']}`（{STATUS_LABELS[membership['status']]}）",
        f"- 键：`{membership['record']['hypothesis_id']}` v"
        f"{membership['record']['hypothesis_version']}",
        "- 同 ID 版本："
        + (
            "、".join(str(version) for version in payload["same_id_versions"])
            if payload["same_id_versions"]
            else "（无）"
        ),
        "",
        "## 记录与快照身份",
        "",
        "```json",
        _json({"record": membership["record"], "snapshot": membership["snapshot"]}),
        "```",
    ]
    if payload["changed_fields"]:
        lines.extend(
            [
                "",
                "## 字段差异",
                "",
                "| field | record | snapshot |",
                "| --- | --- | --- |",
                *(
                    "| "
                    + " | ".join(map(_cell, (row["field"], row["record"], row["snapshot"])))
                    + " |"
                    for row in payload["changed_fields"]
                ),
            ],
        )
    lines.extend(
        [
            "",
            "## 等价性",
            "",
            "```json",
            _json(
                {
                    "found": payload["found"],
                    "canonical_equal": payload["canonical_equal"],
                    "changed_field_count": payload["changed_field_count"],
                    "equality": payload["equality"],
                },
            ),
            "```",
            "",
            "## 执行边界",
            "",
            "```json",
            _json(membership["boundary"]),
            "```",
            "",
            "## 限制",
            "",
            *(f"- {note}" for note in membership["notes"]),
        ],
    )
    return "\n".join(lines) + "\n"


class _Parser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise MembershipError("INVALID_ARGUMENTS")


def main(argv: list[str] | None = None) -> int:
    parser = _Parser(
        description="只读检查一条规范 M4-B 记录是否已登记在规范 registry 快照中",
        allow_abbrev=False,
    )
    parser.add_argument("--record", metavar="JSON", required=True)
    parser.add_argument("--snapshot", metavar="JSON", required=True)
    parser.add_argument("--json", action="store_true")
    try:
        args = parser.parse_args(argv)
        membership = build_membership(
            research_registry.read_registry_bytes(Path(args.record)),
            research_registry.read_registry_bytes(Path(args.snapshot)),
        )
        _verify_report(membership)
        text = _json(membership) + "\n" if args.json else render_markdown(membership)
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
                (MembershipError, research_registry.RegistryViewError, RegistryError),
            )
            else "REGISTRY_MEMBERSHIP_FAILED"
        )
        sys.stderr.buffer.write(f"error: {code}\n".encode())
        sys.stderr.buffer.flush()
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
