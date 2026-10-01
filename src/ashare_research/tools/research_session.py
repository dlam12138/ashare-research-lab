"""M2 完整离线研究会话归档：日期化组装、导出与可重现性验证。

本工具把三个既有离线工作流在一次日期化调用中组装为一个只读归档目录，并可按固定布局重新
生成、逐字节验证该目录：

    value/      固定来源价值研究包的 12 个文件（混合日期的历史汇编）
    facts/      指定时点 PIT 财务事实浏览器的 3 个文件（本次请求日期化）
    metrics/    既有已批准年度指标 PIT 重放的 3 个文件（本次请求日期化）
    snapshot/   四个字节固定的规范快照来源文件（与工具内 pin 一致）
    index.md    相对链接导航、两类内容边界与缺失来源/发布限制
    manifest.json  根校验清单（23 个受管文件的 path/byte_count/sha256）

组装只经过既有公开接口：``value_research_bundle.load_source_bundle`` / ``export_bundle``、
``pit_fact_explorer.build_report`` / ``export_report``、``pit_metric_replay.validate_request`` /
``build_report`` / ``export_report``，全部在工具自有的 ``TemporaryDirectory`` 中完成，之后才排他
创建输出根。本模块不修改这些模块、不联网、不读调用方数据库、不写默认数据库，也不新增指标、
公式、评分、排名、资格判定或研究结论。

验证会按 manifest 记录的选择器在已安装的固定基线/代码上重新生成完整规范归档，并按固定期望
布局逐字节比较全部 24 个文件（含完整根 manifest），拒绝符号链接、缺失或多余路径；manifest 中
记录的任意路径不会被用来读取文件，也不做“只比哈希”的验证。验证只证明可重现性与完整性，
不证明历史发布、历史可得性、真实性或签名，并要求本机安装兼容的固定基线/代码。

已知失败退出码 2，只向 stderr 输出净化后的稳定错误码，stdout 保持为空。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any

from ashare_research.tools import pit_fact_explorer, pit_metric_replay, value_research_bundle

SESSION_SCHEMA = "m2_offline_research_session"
SCHEMA_VERSION = "1.0"
MANIFEST_SCHEMA = "m2_offline_research_session_manifest_v1"
MANIFEST_NAME = "manifest.json"
INDEX_NAME = "index.md"
VALUE_DIR = "value"
FACTS_DIR = "facts"
METRICS_DIR = "metrics"
SNAPSHOT_DIR = "snapshot"

# 固定归档形状：23 个受管文件 + 根 manifest.json = 24 个文件。
EXPECTED_MANAGED_FILE_COUNT = 23
EXPECTED_TOTAL_FILE_COUNT = 24
AREAS: tuple[str, ...] = (VALUE_DIR, FACTS_DIR, METRICS_DIR, SNAPSHOT_DIR)

KNOWN_ERROR_CODES = frozenset(
    {
        # 选择器 / 参数
        "INVALID_REQUEST",
        "INVALID_ARGUMENTS",
        "INVALID_AS_OF_DATE",
        "INVALID_COMPARE_WITH",
        "COMPARE_BEFORE_AS_OF",
        "INVALID_YEAR",
        "UNKNOWN_METRIC",
        "INVALID_SCOPE",
        # 固定来源（只读，不修改）
        "SOURCE_DIRECTORY_MISSING",
        "SOURCE_REPORT_MISSING",
        "SOURCE_HASH_MISMATCH",
        "SOURCE_SNAPSHOT_MISSING",
        "SOURCE_DIGEST_MISMATCH",
        "SNAPSHOT_CONTRACT_UNEXPECTED",
        "SOURCE_VALUE_INVALID",
        "METRIC_REGISTRY_INCOMPLETE",
        "METRIC_FACT_INVALID",
        # 组装与输出
        "COMPOSE_FAILED",
        "OUTPUT_PATH_EXISTS",
        "OUTPUT_WRITE_FAILED",
        # 验证
        "VERIFY_DIRECTORY_MISSING",
        "VERIFY_MANIFEST_UNREADABLE",
        "VERIFY_MANIFEST_INVALID",
        "VERIFY_REQUEST_INVALID",
        "VERIFY_LAYOUT_INVALID",
        "VERIFY_FILE_MISMATCH",
        "VERIFY_MANIFEST_MISMATCH",
        # 兜底
        "UNEXPECTED_FAILURE",
    }
)


class SessionError(Exception):
    """A known, sanitized session failure carrying one stable error code."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code if code in KNOWN_ERROR_CODES else "UNEXPECTED_FAILURE"


# 验证时只有选择器错误归为 VERIFY_REQUEST_INVALID；缺少固定基线/代码如实保留来源错误码。
_REQUEST_ERROR_CODES = frozenset(
    {
        "INVALID_REQUEST",
        "INVALID_AS_OF_DATE",
        "INVALID_COMPARE_WITH",
        "COMPARE_BEFORE_AS_OF",
        "INVALID_YEAR",
        "UNKNOWN_METRIC",
        "INVALID_SCOPE",
    }
)


def _mapped_code(code: str) -> str:
    """Keep an already-sanitized code from a fixed upstream tool, else stay generic."""
    return code if code in KNOWN_ERROR_CODES else "COMPOSE_FAILED"


def _canonical_json_bytes(body: dict[str, Any]) -> bytes:
    return (json.dumps(body, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _joined(values: list[Any]) -> str:
    return "、".join(str(value) for value in values)


# --------------------------------------------------------------------------------------
# 组装（全部在工具自有的 TemporaryDirectory 中完成，之后才创建输出根）
# --------------------------------------------------------------------------------------


def _validated_request(request: dict[str, Any]) -> dict[str, Any]:
    """Validate every selector through the fixed replay validator; no implicit today."""
    if not isinstance(request, dict):
        raise SessionError("INVALID_REQUEST")
    try:
        return pit_metric_replay.validate_request(
            as_of=request.get("as_of"),
            compare_with=request.get("compare_with"),
            years=request.get("years"),
            metrics=request.get("metrics"),
            scope=request.get("scope", "consolidated"),
        )
    except pit_metric_replay.PitMetricReplayError as error:
        raise SessionError(_mapped_code(error.code)) from error


def _collect_exported(root: Path, area: str) -> dict[str, bytes]:
    """Collect one just-exported area of the owned temporary directory as exact bytes."""
    collected: dict[str, bytes] = {}
    try:
        for current, dirnames, filenames in os.walk(root / area, followlinks=False):
            dirnames.sort()
            for name in dirnames:
                if (Path(current) / name).is_symlink():
                    raise SessionError("COMPOSE_FAILED")
            for name in sorted(filenames):
                path = Path(current) / name
                if path.is_symlink() or not path.is_file():
                    raise SessionError("COMPOSE_FAILED")
                collected[path.relative_to(root).as_posix()] = path.read_bytes()
    except OSError as error:
        raise SessionError("COMPOSE_FAILED") from error
    if not collected:
        raise SessionError("COMPOSE_FAILED")
    return collected


def _build_value_area(root: Path) -> dict[str, bytes]:
    try:
        bundle = value_research_bundle.load_source_bundle()
        value_research_bundle.export_bundle(bundle, root / VALUE_DIR)
    except value_research_bundle.BundleError as error:
        raise SessionError(_mapped_code(error.code)) from error
    except OSError as error:
        raise SessionError("COMPOSE_FAILED") from error
    return _collect_exported(root, VALUE_DIR)


def _build_facts_area(root: Path, request: dict[str, Any]) -> dict[str, bytes]:
    """Full PIT facts: all fixed concepts, no period filter, dated by this request."""
    try:
        report = pit_fact_explorer.build_report(
            {
                "as_of": request["as_of"],
                "compare_with": request["compare_with"],
                "concepts": [],
                "period_end": None,
                "scope": request["scope"],
            }
        )
        pit_fact_explorer.export_report(report, root / FACTS_DIR)
    except pit_fact_explorer.PitExplorerError as error:
        raise SessionError(_mapped_code(error.code)) from error
    except OSError as error:
        raise SessionError("COMPOSE_FAILED") from error
    return _collect_exported(root, FACTS_DIR)


def _build_metrics_area(root: Path, request: dict[str, Any]) -> dict[str, bytes]:
    """Existing approved metric definitions replayed in memory for this request."""
    try:
        report = pit_metric_replay.build_report(request)
        pit_metric_replay.export_report(report, root / METRICS_DIR)
    except pit_metric_replay.PitMetricReplayError as error:
        raise SessionError(_mapped_code(error.code)) from error
    except OSError as error:
        raise SessionError("COMPOSE_FAILED") from error
    return _collect_exported(root, METRICS_DIR)


def _snapshot_files() -> dict[str, bytes]:
    """Copy the four fixed canonical source files byte-exact, re-checking their pins."""
    snapshot = pit_fact_explorer.COMMITTED_SNAPSHOT
    pins = pit_fact_explorer.PINNED_SOURCE_SHA256
    try:
        pit_fact_explorer.verify_pinned_sources(snapshot)
    except pit_fact_explorer.PitExplorerError as error:
        raise SessionError(_mapped_code(error.code)) from error
    copied: dict[str, bytes] = {}
    for name in sorted(pins):
        try:
            raw = (snapshot / name).read_bytes()
        except OSError as error:
            raise SessionError("SOURCE_SNAPSHOT_MISSING") from error
        if hashlib.sha256(raw).hexdigest() != pins[name]:
            raise SessionError("SOURCE_DIGEST_MISMATCH")
        copied[f"{SNAPSHOT_DIR}/{name}"] = raw
    return copied


def _area_count(managed: dict[str, bytes], area: str) -> int:
    return sum(1 for name in managed if name.startswith(f"{area}/"))


def _render_index(request: dict[str, Any], managed: dict[str, bytes]) -> str:
    """Relative-link navigation with the mixed-date / dated-PIT boundary and all limits."""
    areas = (
        (VALUE_DIR, "固定来源价值研究包：**混合日期的历史汇编**，不是统一 as-of 的 PIT 查询"),
        (FACTS_DIR, "指定时点 PIT 财务事实浏览器：**本次请求的日期化读取模型**"),
        (METRICS_DIR, "既有已批准年度指标 PIT 重放：**本次请求的日期化读取模型**"),
        (SNAPSHOT_DIR, "字节固定的规范快照来源附件（与工具内 pin 完全一致）"),
    )
    lines: list[str] = [
        "# M2 完整离线研究会话归档",
        "",
        "本目录由 `python -m ashare_research.cli research session` 一次调用组装：既有固定来源"
        "价值包、指定时点（PIT）财务事实与既有年度指标 PIT 重放，连同四个字节固定的规范快照"
        "附件。不联网、不读调用方数据库、不写默认数据库，不新增指标、公式、评分、排名、"
        "资格判定或建议结论。",
        "",
        "## 一、本次请求（日期化选择器，无隐式当前日期）",
        "",
        f"- as-of（PIT 时点）：`{request['as_of']}`",
        f"- compare_with（对比时点）：`{request['compare_with'] or '（未请求）'}`",
        f"- years（年度）：{_joined(request['years'])}",
        f"- metrics（既有指标）：{_joined(request['metrics'])}",
        f"- scope（合并范围口径）：`{request['scope']}`",
        "",
        "## 二、目录结构（均为相对链接）",
        "",
    ]
    for area, description in areas:
        names = sorted(name for name in managed if name.startswith(f"{area}/"))
        lines.append(f"### `{area}/`（{len(names)} 个文件）")
        lines.append("")
        lines.append(description + "。")
        lines.append("")
        lines.extend(f"- [{name}]({name})" for name in names)
        lines.append("")
    lines.extend(
        [
            "### 根文件",
            "",
            f"- [{MANIFEST_NAME}]({MANIFEST_NAME})：{EXPECTED_MANAGED_FILE_COUNT} 个受管文件"
            "（含本文件 index.md）的 path/byte_count/sha256 与本次请求。",
            "",
            "## 三、两类内容的边界（不得互相替代）",
            "",
            f"- `{VALUE_DIR}/` 是**混合日期的历史汇编**：九个基线报告各自保留其原始日期字段，"
            "不是统一 as-of 时点的 PIT 查询，也不是研究刷新；其附件 SHA256 只用于完整性核对，"
            "不代表结论被重新验证。",
            f"- `{FACTS_DIR}/` 与 `{METRICS_DIR}/` 是**本次请求的日期化 PIT 读取模型**："
            f"as_of={request['as_of']}、compare_with={request['compare_with'] or '（未请求）'}、"
            f"scope={request['scope']}；未来事实永不进入选择，空结果如实保留、不回退到其他"
            "口径或更晚时点。",
            "- 两者不合并、不相加、不互相替换：混合日期汇编不能被当作 PIT 证据，"
            "PIT 读取模型也不重新验证或发布任何历史结论。",
            "",
            "## 四、缺失来源与发布/版本限制（如实保留）",
            "",
            "- 规范快照只保留 33 条已对账事实及其直接 lineage；lineage 中的 66 个 "
            "parent_fact_ids 全部不在快照内，原始披露证据无法在本归档内复原，父事实逐条"
            "标记未解决。",
            "- available_at 取自固定快照并按公开 PIT 门禁使用，本归档不重新证明原始可得性；"
            "created_at / recorded_at 只是本地存储元数据，不是可得性证据。",
            "- 指标是离线内存重放读取模型：不做历史发布证明，未获得新的指标版本、生产或评分"
            "准入；result_version=1 与 revision_review_status=offline_replay_unreviewed 是读取"
            "模型约定。",
            "- 现金口径自由现金流代理是**现金代理**，不是估值、贴现、股东自由现金流或 TTM "
            "口径；ROE 是既有年度平均归母权益约定，不是 TTM，也不是 ROIC。",
            "- 价值包各来源报告日期彼此不同；其正文引用的仓库路径（如 reports/、acceptance/）"
            "不在本目录内。规范快照只有 601857.SH、5 个概念、consolidated 口径。",
            "- 本目录不含当前时间戳，也不产生任何评分、排名、资格判定、建议或新研究结论。",
            "",
            "## 五、可重现性验证",
            "",
            "```",
            "python -m ashare_research.cli research session --verify <本目录>",
            "```",
            "",
            f"验证按固定期望布局重新生成完整规范归档（{EXPECTED_TOTAL_FILE_COUNT} 个文件，"
            "含完整根 manifest），逐字节比较全部文件，拒绝符号链接、缺失或多余路径；只从固定"
            "期望路径读取，不信任 manifest 中记录的任意路径或哈希。",
            "",
            "验证要求本机安装兼容的固定基线/代码；它只证明可重现性与完整性，不证明历史发布、"
            "历史可得性、真实性或签名。",
            "",
        ]
    )
    return "\n".join(lines)


def _build_manifest(request: dict[str, Any], managed: dict[str, bytes]) -> dict[str, Any]:
    """Deterministic root manifest over the exact managed file set (manifest excluded)."""
    entries = [
        {
            "path": name,
            "byte_count": len(managed[name]),
            "sha256": hashlib.sha256(managed[name]).hexdigest(),
        }
        for name in sorted(managed)
    ]
    return {
        "schema": MANIFEST_SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "session_schema": SESSION_SCHEMA,
        "request": request,
        "managed_file_count": len(entries),
        "total_file_count": len(entries) + 1,
        "total_byte_count": sum(entry["byte_count"] for entry in entries),
        "files": entries,
        "layout": {
            "value": _area_count(managed, VALUE_DIR),
            "facts": _area_count(managed, FACTS_DIR),
            "metrics": _area_count(managed, METRICS_DIR),
            "snapshot": _area_count(managed, SNAPSHOT_DIR),
            "index": 1,
        },
        "boundaries": {
            "network_used": False,
            "caller_database_read": False,
            "default_database_mutated": False,
            "new_metrics_produced": False,
            "source_selection": False,
            "current_timestamp_recorded": False,
        },
        "verification": {
            "regenerated_from_request": True,
            "compared_every_byte": True,
            "canonical_manifest_compared": True,
            "trusts_recorded_hashes": False,
            "manifest_paths_used_for_reading": False,
            "symlinks_rejected": True,
            "requires_installed_pinned_baseline": True,
            "proves_historical_publication_or_authenticity": False,
        },
    }


def build_session(request: dict[str, Any]) -> dict[str, bytes]:
    """Compose the complete canonical archive in memory, including the root manifest."""
    validated = _validated_request(request)
    files: dict[str, bytes] = {}
    try:
        with tempfile.TemporaryDirectory(prefix="m2-research-session-") as runtime:
            root = Path(runtime)
            files.update(_build_value_area(root))
            files.update(_build_facts_area(root, validated))
            files.update(_build_metrics_area(root, validated))
            files.update(_snapshot_files())
            files[INDEX_NAME] = _render_index(validated, files).encode("utf-8")
            if len(files) != EXPECTED_MANAGED_FILE_COUNT:
                raise SessionError("COMPOSE_FAILED")
            files[MANIFEST_NAME] = _canonical_json_bytes(_build_manifest(validated, files))
    except OSError as error:
        raise SessionError("COMPOSE_FAILED") from error
    if len(files) != EXPECTED_TOTAL_FILE_COUNT:
        raise SessionError("COMPOSE_FAILED")
    return files


# --------------------------------------------------------------------------------------
# 导出（先检查输出根，再渲染全部字节，最后排他 mkdir）
# --------------------------------------------------------------------------------------


def _assert_output_available(output: Path) -> None:
    """Reject any pre-existing file, directory or symlink before anything is created."""
    try:
        if output.is_symlink() or output.exists():
            raise SessionError("OUTPUT_PATH_EXISTS")
    except OSError as error:
        raise SessionError("OUTPUT_PATH_EXISTS") from error


def export_session(request: dict[str, Any], output: Path) -> dict[str, Any]:
    """Write the canonical archive into a new directory and return the root manifest."""
    _assert_output_available(output)
    files = build_session(request)
    manifest = json.loads(files[MANIFEST_NAME].decode("utf-8"))
    try:
        output.mkdir(parents=True, exist_ok=False)
    except FileExistsError as error:
        raise SessionError("OUTPUT_PATH_EXISTS") from error
    except OSError as error:
        raise SessionError("OUTPUT_WRITE_FAILED") from error
    try:
        for name in sorted(files):
            path = output / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(files[name])
    except OSError as error:
        # 迟到的 IO 失败保留已创建的自有目录，不做破坏性清理。
        raise SessionError("OUTPUT_WRITE_FAILED") from error
    return manifest


# --------------------------------------------------------------------------------------
# 验证（固定期望布局 + 从选择器重新生成 + 逐字节比较；不信任 manifest 记录的路径/哈希）
# --------------------------------------------------------------------------------------


def _recorded_managed_paths(manifest: dict[str, Any]) -> list[str]:
    """Structurally check the recorded entries; these paths are never used to read files."""
    entries = manifest.get("files")
    if not isinstance(entries, list) or manifest.get("managed_file_count") != len(entries):
        raise SessionError("VERIFY_MANIFEST_INVALID")
    recorded: list[str] = []
    for entry in entries:
        if not isinstance(entry, dict):
            raise SessionError("VERIFY_MANIFEST_INVALID")
        path = entry.get("path")
        byte_count = entry.get("byte_count")
        digest = entry.get("sha256")
        if not isinstance(path, str) or not path or path in recorded:
            raise SessionError("VERIFY_MANIFEST_INVALID")
        if not isinstance(byte_count, int) or not isinstance(digest, str):
            raise SessionError("VERIFY_MANIFEST_INVALID")
        recorded.append(path)
    return recorded


def _expected_directories(names: set[str]) -> set[str]:
    directories: set[str] = set()
    for name in names:
        parts = name.split("/")
        for index in range(1, len(parts)):
            directories.add("/".join(parts[:index]))
    return directories


def _verify_layout(root: Path, canonical: dict[str, bytes]) -> None:
    """Reject symlink files/directories and any path outside the fixed expected layout."""
    expected_files = set(canonical)
    expected_directories = _expected_directories(expected_files)
    observed: set[str] = set()
    for current, dirnames, filenames in os.walk(root, followlinks=False):
        dirnames.sort()
        for name in dirnames:
            path = Path(current) / name
            if path.is_symlink() or path.relative_to(root).as_posix() not in expected_directories:
                raise SessionError("VERIFY_LAYOUT_INVALID")
        for name in sorted(filenames):
            path = Path(current) / name
            relative = path.relative_to(root).as_posix()
            if path.is_symlink() or relative not in expected_files:
                raise SessionError("VERIFY_LAYOUT_INVALID")
            observed.add(relative)
    if observed != expected_files:
        raise SessionError("VERIFY_LAYOUT_INVALID")


def verify_session(directory: Path) -> dict[str, Any]:
    """Regenerate the canonical archive from the recorded request and compare every byte."""
    if directory.is_symlink() or not directory.is_dir():
        raise SessionError("VERIFY_DIRECTORY_MISSING")
    root = directory.resolve()
    manifest_path = root / MANIFEST_NAME
    if manifest_path.is_symlink() or not manifest_path.is_file():
        raise SessionError("VERIFY_MANIFEST_UNREADABLE")
    try:
        retained_manifest = manifest_path.read_bytes()
    except OSError as error:
        raise SessionError("VERIFY_MANIFEST_UNREADABLE") from error
    try:
        manifest = json.loads(retained_manifest.decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as error:
        raise SessionError("VERIFY_MANIFEST_UNREADABLE") from error
    if not isinstance(manifest, dict) or manifest.get("schema") != MANIFEST_SCHEMA:
        raise SessionError("VERIFY_MANIFEST_INVALID")
    request = manifest.get("request")
    if not isinstance(request, dict):
        raise SessionError("VERIFY_MANIFEST_INVALID")
    recorded = _recorded_managed_paths(manifest)

    try:
        canonical = build_session(request)
    except SessionError as error:
        if error.code in _REQUEST_ERROR_CODES:
            raise SessionError("VERIFY_REQUEST_INVALID") from error
        raise
    canonical_manifest = json.loads(canonical[MANIFEST_NAME].decode("utf-8"))
    if sorted(recorded) != sorted(name for name in canonical if name != MANIFEST_NAME):
        raise SessionError("VERIFY_MANIFEST_INVALID")

    _verify_layout(root, canonical)
    for name in sorted(canonical):
        try:
            retained = (root / name).read_bytes()
        except OSError as error:
            raise SessionError("VERIFY_LAYOUT_INVALID") from error
        if retained != canonical[name]:
            if name == MANIFEST_NAME:
                raise SessionError("VERIFY_MANIFEST_MISMATCH")
            raise SessionError("VERIFY_FILE_MISMATCH")
    return {
        "schema": SESSION_SCHEMA,
        "status": "verified",
        "request": canonical_manifest["request"],
        "managed_file_count": canonical_manifest["managed_file_count"],
        "total_file_count": len(canonical),
        "verified_file_count": len(canonical),
        "total_byte_count": sum(len(payload) for payload in canonical.values()),
        "managed_total_byte_count": canonical_manifest["total_byte_count"],
        "regenerated_from_request": True,
        "compared_every_byte": True,
        "canonical_manifest_compared": True,
        "manifest_paths_used_for_reading": False,
        "symlinks_rejected": True,
        "requires_installed_pinned_baseline": True,
        "proves_historical_publication_or_authenticity": False,
    }


# --------------------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------------------


class _SanitizedParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:  # noqa: ARG002 - sanitized by design
        raise SessionError("INVALID_ARGUMENTS")


def _build_parser() -> argparse.ArgumentParser:
    parser = _SanitizedParser(
        prog="python -m ashare_research.cli research session",
        description="组装/导出/验证完整离线研究会话归档（value/ facts/ metrics/ snapshot/）。",
        add_help=True,
        allow_abbrev=False,
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--output", metavar="NEW_DIR", help="导出到新目录（必须不存在）")
    mode.add_argument("--verify", metavar="DIR", help="按固定布局重新生成并逐字节验证")
    parser.add_argument("--as-of", metavar="ISO_DATE", help="PIT 时点（YYYY-MM-DD），导出必填")
    parser.add_argument("--compare-with", metavar="ISO_DATE", help="对比时点（YYYY-MM-DD）")
    parser.add_argument("--year", action="append", type=int, metavar="YEAR", help="年度，可重复")
    parser.add_argument(
        "--metric", action="append", metavar="METRIC_ID", help="既有指标 ID，可重复"
    )
    parser.add_argument(
        "--scope",
        metavar="SCOPE",
        help="合并范围口径：consolidated 或 parent_company（默认 consolidated）",
    )
    return parser


_SELECTOR_ATTRIBUTES = ("as_of", "compare_with", "year", "metric", "scope")


def _reject_selectors(arguments: argparse.Namespace) -> None:
    """Verification mode takes no selectors at all; scope defaults to None on purpose."""
    if any(getattr(arguments, name) is not None for name in _SELECTOR_ATTRIBUTES):
        raise SessionError("INVALID_ARGUMENTS")


def _request_from_arguments(arguments: argparse.Namespace) -> dict[str, Any]:
    if arguments.as_of is None:
        raise SessionError("INVALID_ARGUMENTS")
    return _validated_request(
        {
            "as_of": arguments.as_of,
            "compare_with": arguments.compare_with,
            "years": arguments.year,
            "metrics": arguments.metric,
            "scope": arguments.scope if arguments.scope is not None else "consolidated",
        }
    )


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
    except SessionError:
        return _fail("INVALID_ARGUMENTS")
    except SystemExit as exit_request:  # argparse help / usage
        code = exit_request.code
        return code if isinstance(code, int) else 2
    try:
        if arguments.verify is not None:
            _reject_selectors(arguments)
            result = verify_session(Path(arguments.verify))
            _emit(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
            return 0
        request = _request_from_arguments(arguments)
        manifest = export_session(request, Path(arguments.output))
        _emit(
            "exported "
            + str(manifest["total_file_count"])
            + " files, "
            + str(manifest["managed_file_count"])
            + " managed, "
            + str(manifest["total_byte_count"])
            + " bytes\n"
        )
        return 0
    except SessionError as error:
        return _fail(error.code)
    except Exception:  # noqa: BLE001 - known failures are sanitized, never traced
        return _fail("UNEXPECTED_FAILURE")


if __name__ == "__main__":
    raise SystemExit(main())
