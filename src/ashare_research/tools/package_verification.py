"""Rebuild and verify every file in an existing portable research package."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path, PurePosixPath
from typing import Any

from ashare_research.tools import (
    evidence_audit,
    research_review,
    research_session,
    research_workflow,
    session_compare,
    value_research_bundle,
)

SCHEMA = "m2_complete_research_package_verification_v1"
KINDS = {
    value_research_bundle.MANIFEST_SCHEMA: "value",
    research_session.MANIFEST_SCHEMA: "session",
    research_review.SCHEMA: "review",
    evidence_audit.SCHEMA: "audit",
    session_compare.SCHEMA: "compare",
    research_workflow.MANIFEST_SCHEMA: "workflow",
}
NOTES = (
    "验证依赖已安装的兼容固定基线与代码，证明完整包的可重现性和字节一致性。",
    "未证明真实性、数字签名、历史发布/可得性、财务质量或研究/生产资格。",
    "价值报告的混合日期、固定快照33条事实与66个缺失原始父记录等限制保持不变。",
    "外层清单自身仍只是文件目录；本命令另行重建并核对报告、证据与完整清单。",
)


class PackageError(Exception):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def _scan(root: Path) -> tuple[set[str], set[str]]:
    """Inspect only paths below root without following any symlink."""
    files, directories = set(), set()

    def unreadable(error: OSError) -> None:
        raise PackageError("VERIFY_LAYOUT_INVALID") from error

    for current, dirnames, filenames in os.walk(root, followlinks=False, onerror=unreadable):
        for name in sorted(dirnames):
            path = Path(current) / name
            if path.is_symlink():
                raise PackageError("VERIFY_LAYOUT_INVALID")
            directories.add(path.relative_to(root).as_posix())
        for name in sorted(filenames):
            path = Path(current) / name
            if path.is_symlink() or not path.is_file():
                raise PackageError("VERIFY_LAYOUT_INVALID")
            files.add(path.relative_to(root).as_posix())
    return files, directories


def _compare_views(manifest: dict[str, Any]) -> dict[str, str]:
    sides = manifest.get("sides")
    if not isinstance(sides, dict):
        raise PackageError("VERIFY_MANIFEST_INVALID")
    options = {}
    for side in ("left", "right"):
        item = sides.get(side)
        if not isinstance(item, dict) or item.get("selected_view") not in session_compare.VIEWS:
            raise PackageError("VERIFY_MANIFEST_INVALID")
        options[side + "_view"] = item["selected_view"]
    return options


def _regenerate(root: Path, kind: str, manifest: dict[str, Any]) -> dict[str, bytes]:
    """Use fixed subdirectories and public builders, never recorded file paths."""
    try:
        if kind == "session":
            return research_session.load_verified_session(root)[1]
        if kind == "workflow":
            request = manifest.get("request")
            if not isinstance(request, dict):
                raise PackageError("VERIFY_MANIFEST_INVALID")
            return research_workflow.build_workflow(request)
        with tempfile.TemporaryDirectory(prefix="m2-package-verification-") as runtime:
            output = Path(runtime) / "canonical"
            if kind == "value":
                value_research_bundle.export_bundle(
                    value_research_bundle.load_source_bundle(), output
                )
            elif kind == "review":
                research_review.export_review(root / "session", output)
            elif kind == "audit":
                evidence_audit.export_audit(root / "session", output)
            else:
                session_compare.export_comparison(
                    root / "left", root / "right", output, **_compare_views(manifest)
                )
            names, _ = _scan(output)
            return {name: (output / name).read_bytes() for name in sorted(names)}
    except (
        research_session.SessionError,
        research_review.ReviewError,
        evidence_audit.AuditError,
        session_compare.CompareError,
        value_research_bundle.BundleError,
        research_workflow.WorkflowError,
    ) as error:
        raise PackageError(error.code) from error
    except OSError as error:
        raise PackageError("VERIFY_REBUILD_FAILED") from error


def load_verified_package(directory: Path) -> tuple[dict[str, Any], dict[str, bytes]]:
    """Freshly verify a complete package and return its exact canonical bytes.

    Each call owns a new byte map; callers need not reread retained files after
    verification. This is not a cache or an archive-only authenticity check.
    """
    if directory.is_symlink() or not directory.is_dir():
        raise PackageError("VERIFY_DIRECTORY_MISSING")
    root = directory.resolve()
    _scan(root)
    try:
        raw_manifest = (root / "manifest.json").read_bytes()
        manifest = json.loads(raw_manifest.decode("utf-8"))
    except (OSError, UnicodeDecodeError, ValueError) as error:
        raise PackageError("VERIFY_MANIFEST_UNREADABLE") from error
    if not isinstance(manifest, dict) or not isinstance(manifest.get("schema"), str):
        raise PackageError("VERIFY_MANIFEST_INVALID")
    kind = KINDS.get(manifest["schema"])
    if kind is None:
        raise PackageError("UNSUPPORTED_PACKAGE")
    canonical = _regenerate(root, kind, manifest)
    expected_directories = {
        parent.as_posix()
        for name in canonical
        for parent in PurePosixPath(name).parents
        if parent.as_posix() != "."
    }
    observed_files, observed_directories = _scan(root)
    if observed_files != set(canonical) or observed_directories != expected_directories:
        raise PackageError("VERIFY_LAYOUT_INVALID")
    for name, expected in sorted(canonical.items()):
        try:
            path = root / name
            if path.is_symlink():
                raise PackageError("VERIFY_LAYOUT_INVALID")
            retained = path.read_bytes()
        except OSError as error:
            raise PackageError("VERIFY_LAYOUT_INVALID") from error
        if retained != expected:
            code = "VERIFY_MANIFEST_MISMATCH" if name == "manifest.json" else "VERIFY_FILE_MISMATCH"
            raise PackageError(code)
    canonical_manifest = json.loads(canonical["manifest.json"])
    result = {
        "schema": SCHEMA,
        "status": "verified",
        "package_kind": kind,
        "package_schema": canonical_manifest["schema"],
        "verified_file_count": len(canonical),
        "total_byte_count": sum(len(raw) for raw in canonical.values()),
        "package_manifest_sha256": hashlib.sha256(canonical["manifest.json"]).hexdigest(),
        "request": canonical_manifest.get("request"),
        "sides": canonical_manifest.get("sides"),
        "compared_every_byte": True,
        "canonical_manifest_compared": True,
        "manifest_paths_used_for_reading": False,
        "symlinks_rejected": True,
        "requires_installed_pinned_baseline": True,
        "proves_historical_publication_or_authenticity": False,
        "notes": list(NOTES),
    }
    return result, canonical


def verify_package(directory: Path) -> dict[str, Any]:
    """Keep the existing metadata-only result and error behavior."""
    return load_verified_package(directory)[0]


def render_summary(result: dict[str, Any]) -> str:
    lines = [
        f"完整研究包验证通过：{result['package_kind']}，{result['verified_file_count']} 个文件。",
        "报告、证据、路径布局和完整根清单均与重新生成的规范字节一致。",
        f"清单 SHA256：{result['package_manifest_sha256']}",
        "",
        *result["notes"],
    ]
    return "\n".join(lines) + "\n"


class _Parser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise PackageError("INVALID_ARGUMENTS")


def main(argv: list[str] | None = None) -> int:
    parser = _Parser(
        description="完整复核价值包、研究档案、速览、证据台账、对比包或工作流", allow_abbrev=False
    )
    parser.add_argument("--package", required=True, metavar="DIR")
    parser.add_argument("--json", action="store_true")
    try:
        args = parser.parse_args(argv)
        result = verify_package(Path(args.package))
        text = (
            json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
            if args.json
            else render_summary(result)
        )
        sys.stdout.buffer.write(text.encode())
        sys.stdout.buffer.flush()
        return 0
    except SystemExit as error:
        return error.code if isinstance(error.code, int) else 2
    except Exception as error:  # noqa: BLE001 - sanitized errors, no partial stdout
        code = error.code if isinstance(error, PackageError) else "UNEXPECTED_FAILURE"
        sys.stderr.buffer.write(f"error: {code}\n".encode())
        sys.stderr.buffer.flush()
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
