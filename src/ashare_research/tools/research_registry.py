"""只读复核显式给出的 M4-B 规范记录、registry 快照或状态转换请求。

    ashare-research research registry --record JSON | --snapshot JSON [--json]
    ashare-research research registry --record JSON --transition REQUEST.json [--json]

本模块只读取调用者显式给出的单个或两个文件（各最多 1MiB），并用冻结的 13 个注册表
入口重新解析与复算；默认输出紧凑中文 Markdown 视图，``--json`` 输出有界机器视图。
状态转换预检只调用冻结的 ``validate_state_transition``：不产生新记录、不写入、不
提升状态。工具不加载默认或真实候选数据集、不修复摘要，也不访问数据库、provider、
网络或 holdout。冻结的 ``mechanism/registry`` 公开面保持不变：全部 registry 语义
校验仍由该包完成，本模块只做严格字节解码、只读投影与渲染。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections.abc import Mapping
from dataclasses import fields
from pathlib import Path
from typing import Any

from ashare_research.mechanism.registry import (
    DIGEST_ALGORITHM_ID,
    INTERPRETATION_BOUNDARY,
    MAX_REAL_DEMO_CANDIDATES,
    MAX_RECORDS_PER_SNAPSHOT,
    REGISTRY_VERSION,
    SNAPSHOT_SCHEMA_VERSION,
    HypothesisRecordV1,
    RegistryError,
    StateTransitionRequestV1,
    build_hypothesis_registry_snapshot,
    hypothesis_record_digest,
    hypothesis_record_identity_digest,
    hypothesis_record_to_canonical_dict,
    parse_hypothesis_record,
    serialize_hypothesis_record,
    serialize_hypothesis_registry_snapshot,
    validate_state_transition,
)

_CONTAINER_FIELDS = tuple(
    item.name for item in fields(HypothesisRecordV1) if str(item.type).startswith("tuple[")
)
REQUEST_FIELDS = tuple(item.name for item in fields(StateTransitionRequestV1))
SCHEMA_RECORD_VIEW = "m4_registry_record_view_v1"
SCHEMA_SNAPSHOT_VIEW = "m4_registry_snapshot_view_v1"
SCHEMA_TRANSITION_PREFLIGHT = "m4_registry_transition_preflight_v1"
VIEW_STATUS = "validated_metadata_only"
PREFLIGHT_STATUS = "accepted_preflight_only"
MAX_INPUT_BYTES = 1_048_576
SNAPSHOT_FIELDS = (
    "registry_schema_version",
    "registry_version",
    "digest_algorithm",
    "interpretation_boundary",
    "records",
    "real_demo_candidate_count",
    "registry_digest",
)
BOUNDARY = {
    "execution_authorized": False,
    "statistics_computed": False,
    "outcome_read": False,
    "holdout_accessed": False,
    "real_registry_dataset_loaded": False,
    "registry_written": False,
}
RECORD_NOTE = "记录已用冻结入口复算规范字节、身份摘要、记录摘要与状态历史。"
SNAPSHOT_NOTE = (
    "快照已复算 registry_digest、记录规范顺序与规模上限"
    f"（记录 {MAX_RECORDS_PER_SNAPSHOT} 条、real-demo {MAX_REAL_DEMO_CANDIDATES} 条）。"
)
COMMON_NOTES = (
    "本视图只读：不写入、不修正、不提升状态，也不加载默认或真实候选数据集。",
    "DISCOVERED／LITERATURE_REVIEWED 等来源状态与 registry 元数据不是证据，"
    "也不构成研究结论或执行授权。",
)
PREFLIGHT_NOTES = (
    "预检只调用冻结状态机校验：不产生新记录、不写入、不提升任何状态。",
    "校验通过只表示请求满足冻结转换前置条件；authorization_ref 仅按标识符检查，"
    "工具不核实授权合同是否存在或已生效。",
)


class RegistryViewError(Exception):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def read_registry_bytes(source: Path) -> bytes:
    try:
        with source.open("rb") as stream:
            payload = stream.read(MAX_INPUT_BYTES + 1)
    except OSError as error:
        raise RegistryViewError("REGISTRY_READ_FAILED") from error
    if len(payload) > MAX_INPUT_BYTES:
        raise RegistryViewError("REGISTRY_TOO_LARGE")
    return payload


def _pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise RegistryError("NON_CANONICAL_SERIALIZATION")
        result[key] = value
    return result


def _float_token(_value: str) -> None:
    raise RegistryError("NON_CANONICAL_SERIALIZATION")


def _constant_token(_value: str) -> None:
    raise RegistryError("NON_CANONICAL_SERIALIZATION")


def strict_json_document(payload: bytes) -> dict[str, Any]:
    """Decode one canonical snapshot document; mirror the frozen record rules."""
    if (
        payload.startswith(b"\xef\xbb\xbf")
        or b"\r" in payload
        or not payload.endswith(b"\n")
        or payload.endswith(b"\n\n")
    ):
        raise RegistryError("NON_CANONICAL_SERIALIZATION")
    try:
        loaded = json.loads(
            payload.decode("utf-8"),
            object_pairs_hook=_pairs,
            parse_float=_float_token,
            parse_constant=_constant_token,
        )
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise RegistryError("NON_CANONICAL_SERIALIZATION") from None
    if not isinstance(loaded, dict):
        raise RegistryError("INVALID_RECORD_STRUCTURE")
    return loaded


def _canonical_bytes(document: Mapping[str, Any]) -> bytes:
    return (
        json.dumps(
            dict(document), ensure_ascii=False, sort_keys=True, separators=(",", ":"),
        )
        + "\n"
    ).encode("utf-8")


def _record_from_bytes(payload: bytes):
    try:
        return parse_hypothesis_record(payload)
    except TypeError:
        # The frozen byte path constructs HypothesisRecordV1 before its key-set
        # checks, so a missing or extra key surfaces as a bare TypeError there.
        # Re-enter the frozen mapping path (with the JSON container conversion
        # the byte path applies) so those inputs keep their documented codes.
        document = strict_json_document(payload)
        for name in _CONTAINER_FIELDS:
            if isinstance(document.get(name), list):
                document[name] = tuple(document[name])
        return parse_hypothesis_record(document)


def build_record_view(payload: bytes) -> dict[str, Any]:
    """Project one canonical record file through the frozen registry entries."""
    record = _record_from_bytes(payload)
    document = hypothesis_record_to_canonical_dict(record)
    identity = hypothesis_record_identity_digest(record)
    digest = hypothesis_record_digest(record)
    verification = {
        "canonical_bytes_verified": serialize_hypothesis_record(record) == payload,
        "identity_digest_verified": identity == document["identity_digest"],
        "record_digest_verified": digest == document["record_digest"],
    }
    if not all(verification.values()):
        raise RegistryViewError("REGISTRY_VIEW_MISMATCH")
    return {
        "schema": SCHEMA_RECORD_VIEW,
        "status": VIEW_STATUS,
        "source_file_sha256": _sha256(payload),
        "record": document,
        "digests": {
            "identity_digest": document["identity_digest"],
            "record_digest": document["record_digest"],
            "identity_digest_recomputed": identity,
            "record_digest_recomputed": digest,
        },
        "verification": verification,
        "boundary": dict(BOUNDARY),
        "notes": [RECORD_NOTE, *COMMON_NOTES],
    }


def build_snapshot_view(payload: bytes) -> dict[str, Any]:
    """Project one canonical snapshot file through the frozen registry entries."""
    loaded = strict_json_document(payload)
    if set(loaded) - set(SNAPSHOT_FIELDS):
        raise RegistryError("UNKNOWN_RECORD_FIELD")
    if set(SNAPSHOT_FIELDS) - set(loaded):
        raise RegistryError("MISSING_REQUIRED_FIELD")
    raw_records = loaded["records"]
    if type(raw_records) is not list:
        raise RegistryError("INVALID_RECORD_STRUCTURE")
    records = []
    for item in raw_records:
        if not isinstance(item, Mapping):
            raise RegistryError("INVALID_RECORD_STRUCTURE")
        records.append(parse_hypothesis_record(_canonical_bytes(item)))
    built = build_hypothesis_registry_snapshot(tuple(records))
    if (
        loaded["registry_schema_version"] != SNAPSHOT_SCHEMA_VERSION
        or loaded["registry_version"] != REGISTRY_VERSION
        or loaded["digest_algorithm"] != DIGEST_ALGORITHM_ID
        or loaded["interpretation_boundary"] != INTERPRETATION_BOUNDARY
    ):
        raise RegistryError("INVALID_ENUM_VALUE")
    expected_order = [
        (item.hypothesis_id, item.hypothesis_version) for item in built.records
    ]
    if [(item.hypothesis_id, item.hypothesis_version) for item in records] != expected_order:
        raise RegistryError("INVALID_RECORD_STRUCTURE")
    count = loaded["real_demo_candidate_count"]
    if type(count) is not int or count != built.real_demo_candidate_count:
        raise RegistryError("INVALID_FIELD_TYPE")
    if loaded["registry_digest"] != built.registry_digest:
        raise RegistryError("RECORD_DIGEST_MISMATCH")
    verification = {
        "canonical_bytes_verified": serialize_hypothesis_registry_snapshot(built) == payload,
        "registry_digest_verified": built.registry_digest == loaded["registry_digest"],
        "records_digests_verified": all(
            hypothesis_record_identity_digest(item) == item.identity_digest
            and hypothesis_record_digest(item) == item.record_digest
            for item in built.records
        ),
        "scale_limits_respected": (
            len(built.records) <= MAX_RECORDS_PER_SNAPSHOT
            and built.real_demo_candidate_count <= MAX_REAL_DEMO_CANDIDATES
        ),
    }
    if not all(verification.values()):
        raise RegistryViewError("REGISTRY_VIEW_MISMATCH")
    return {
        "schema": SCHEMA_SNAPSHOT_VIEW,
        "status": VIEW_STATUS,
        "source_file_sha256": _sha256(payload),
        "registry": {
            "registry_schema_version": built.registry_schema_version,
            "registry_version": built.registry_version,
            "digest_algorithm": built.digest_algorithm,
            "record_count": len(built.records),
            "real_demo_candidate_count": built.real_demo_candidate_count,
            "max_records_per_snapshot": MAX_RECORDS_PER_SNAPSHOT,
            "max_real_demo_candidates": MAX_REAL_DEMO_CANDIDATES,
            "registry_digest": built.registry_digest,
        },
        "records": [
            {
                "hypothesis_id": item.hypothesis_id,
                "hypothesis_version": item.hypothesis_version,
                "status": item.status,
                "source_type": item.source_type,
                "a_share_data_feasibility": item.a_share_data_feasibility,
                "free_data_feasibility": item.free_data_feasibility,
                "identity_digest": item.identity_digest,
                "record_digest": item.record_digest,
                "state_count": len(item.state_history),
            }
            for item in built.records
        ],
        "interpretation_boundary": INTERPRETATION_BOUNDARY,
        "verification": verification,
        "boundary": dict(BOUNDARY),
        "notes": [SNAPSHOT_NOTE, *COMMON_NOTES],
    }


def build_transition_preflight(record_payload: bytes, request_payload: bytes) -> dict[str, Any]:
    """Check one explicit transition request through the frozen state machine."""
    record = _record_from_bytes(record_payload)
    request = strict_json_document(request_payload)
    validate_state_transition(record, request)
    if request_payload != _canonical_bytes(request):
        raise RegistryError("NON_CANONICAL_SERIALIZATION")
    request_view = {name: request[name] for name in REQUEST_FIELDS}
    return {
        "schema": SCHEMA_TRANSITION_PREFLIGHT,
        "status": PREFLIGHT_STATUS,
        "source_file_sha256": _sha256(record_payload),
        "request_file_sha256": _sha256(request_payload),
        "record": {
            "hypothesis_id": record.hypothesis_id,
            "hypothesis_version": record.hypothesis_version,
            "status": record.status,
            "identity_digest": record.identity_digest,
            "record_digest": record.record_digest,
            "state_count": len(record.state_history),
        },
        "request": request_view,
        "result": {
            "accepted": True,
            "would_be_ordinal": len(record.state_history) + 1,
            "would_be_status": request_view["to_state"],
        },
        "boundary": dict(BOUNDARY),
        "notes": [*PREFLIGHT_NOTES, *COMMON_NOTES],
    }


def render_transition_markdown(preflight: dict[str, Any]) -> str:
    lines = [
        "# M4-B 状态转换只读预检",
        "",
        "记录与转换请求已按冻结入口复核；预检不产生新记录、不写入、不提升状态。",
    ]
    for title, value in (
        ("记录身份", preflight["record"]),
        ("转换请求", preflight["request"]),
        ("预检结果", preflight["result"]),
        ("执行边界", preflight["boundary"]),
    ):
        lines.extend(["", f"## {title}", "", "```json", _json(value), "```"])
    lines.extend(["", "## 限制", "", *(f"- {note}" for note in preflight["notes"])])
    return "\n".join(lines) + "\n"


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False)


def _cell(value: Any) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def render_record_markdown(view: dict[str, Any]) -> str:
    record = view["record"]
    scope = {
        key: record[key]
        for key in (
            "hypothesis_id",
            "hypothesis_version",
            "source_type",
            "expected_direction",
            "a_share_data_feasibility",
            "free_data_feasibility",
            "status",
            "identity_digest",
            "record_digest",
        )
    }
    lines = [
        "# M4-B 假设记录只读视图",
        "",
        "记录已按冻结 schema 与注册表入口复核；本视图不写入、不修改、不提升状态。",
        "",
        "## 记录身份",
        "",
        "```json",
        _json(scope),
        "```",
        "",
        "## 状态历史",
        "",
        "```json",
        _json(record["state_history"]),
        "```",
        "",
        "## 规范记录",
        "",
        "```json",
        _json(record),
        "```",
    ]
    for title, value in (
        ("复核检查", view["verification"]),
        ("执行边界", view["boundary"]),
    ):
        lines.extend(["", f"## {title}", "", "```json", _json(value), "```"])
    lines.extend(["", "## 限制", "", *(f"- {note}" for note in view["notes"])])
    return "\n".join(lines) + "\n"


def render_snapshot_markdown(view: dict[str, Any]) -> str:
    lines = [
        "# M4-B registry 快照只读视图",
        "",
        "快照已按冻结 schema、注册表入口与规范字节复核；本视图不写入、不修改。",
        "",
        "## Registry",
        "",
        "```json",
        _json(view["registry"]),
        "```",
        "",
        "## 记录",
        "",
        "| hypothesis_id | 版本 | 状态 | A股数据可行性 | 免费数据可行性 |",
        "| --- | --- | --- | --- | --- |",
    ]
    for item in view["records"]:
        cells = (
            item["hypothesis_id"],
            item["hypothesis_version"],
            item["status"],
            item["a_share_data_feasibility"],
            item["free_data_feasibility"],
        )
        lines.append("| " + " | ".join(map(_cell, cells)) + " |")
    lines.extend(["", "## 记录明细", "", "```json", _json(view["records"]), "```"])
    for title, value in (
        ("复核检查", view["verification"]),
        ("解释边界", view["interpretation_boundary"]),
        ("执行边界", view["boundary"]),
    ):
        lines.extend(["", f"## {title}", "", "```json", _json(value), "```"])
    lines.extend(["", "## 限制", "", *(f"- {note}" for note in view["notes"])])
    return "\n".join(lines) + "\n"


class _Parser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise RegistryViewError("INVALID_ARGUMENTS")


def main(argv: list[str] | None = None) -> int:
    parser = _Parser(
        description="只读复核显式 M4-B 规范记录、registry 快照或状态转换请求",
        allow_abbrev=False,
    )
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--record", metavar="JSON")
    source.add_argument("--snapshot", metavar="JSON")
    parser.add_argument("--transition", metavar="JSON")
    parser.add_argument("--json", action="store_true")
    try:
        args = parser.parse_args(argv)
        if args.snapshot is not None and args.transition is not None:
            raise RegistryViewError("INVALID_ARGUMENTS")
        if args.record is not None:
            payload = read_registry_bytes(Path(args.record))
            if args.transition is not None:
                request = read_registry_bytes(Path(args.transition))
                view = build_transition_preflight(payload, request)
                text = _json(view) + "\n" if args.json else render_transition_markdown(view)
            else:
                view = build_record_view(payload)
                text = _json(view) + "\n" if args.json else render_record_markdown(view)
        else:
            view = build_snapshot_view(read_registry_bytes(Path(args.snapshot)))
            text = _json(view) + "\n" if args.json else render_snapshot_markdown(view)
        sys.stdout.buffer.write(text.encode("utf-8"))
        sys.stdout.buffer.flush()
        return 0
    except SystemExit as error:
        return error.code if isinstance(error.code, int) else 2
    except Exception as error:  # noqa: BLE001 - sanitized, no partial output
        code = (
            error.code
            if isinstance(error, (RegistryViewError, RegistryError))
            else "REGISTRY_VIEW_FAILED"
        )
        sys.stderr.buffer.write(f"error: {code}\n".encode())
        sys.stderr.buffer.flush()
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
