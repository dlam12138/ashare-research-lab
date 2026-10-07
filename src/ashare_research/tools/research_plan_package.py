"""Portable compile-only plans; recompilation checks consistency, never authority."""

from __future__ import annotations

import hashlib
import stat
from pathlib import Path
from typing import Any

from ashare_research.tools.research_plan import (
    MAX_INPUT_BYTES,
    PlanError,
    _json,
    build_report_from_bytes,
    read_hypothesis_bytes,
    render_markdown,
)

SCHEMA = "m4_compile_only_plan_package_v1"
NAMES = frozenset({"hypothesis.json", "plan.json", "plan.md", "manifest.json"})
MAX_ARTIFACT_BYTES = 16 * MAX_INPUT_BYTES


def _json_bytes(value: Any) -> bytes:
    return (_json(value) + "\n").encode("utf-8")


def _files(payload: bytes) -> tuple[dict[str, bytes], dict[str, Any], dict[str, Any]]:
    report = build_report_from_bytes(payload)
    files = {
        "hypothesis.json": payload,
        "plan.json": _json_bytes(report),
        "plan.md": render_markdown(report).encode("utf-8"),
    }
    manifest = {
        "schema": SCHEMA,
        "integrity_inventory_only": True,
        "independent_seal_verified": False,
        "files": [
            {"path": name, "byte_count": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}
            for name, raw in sorted(files.items())
        ],
        "boundary": report["boundary"],
    }
    files["manifest.json"] = _json_bytes(manifest)
    if any(len(raw) > MAX_ARTIFACT_BYTES for raw in files.values()):
        raise PlanError("PLAN_ARTIFACT_TOO_LARGE")
    return files, manifest, report


def _check_path(path: Path) -> None:
    """Reject symlinks and Windows reparse points, including ancestor paths."""
    path = path.absolute()
    for candidate in (path, *path.parents):
        try:
            info = candidate.lstat()
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
            raise PlanError("LINKED_PACKAGE_PATH")


def export_package(source: Path, output: Path) -> dict[str, Any]:
    try:
        _check_path(output)
        if output.exists():
            raise PlanError("OUTPUT_PATH_EXISTS")
        files, manifest, _ = _files(read_hypothesis_bytes(source))
        # Compilation and rendering finish before exclusively claiming the destination.
        output.mkdir(exist_ok=False)
        for name, payload in sorted(files.items()):
            with (output / name).open("xb") as stream:
                stream.write(payload)
        return manifest
    except FileExistsError as error:
        raise PlanError("OUTPUT_PATH_EXISTS") from error
    except OSError as error:
        # Preserve partial output for inspection; never delete or overwrite a path.
        raise PlanError("OUTPUT_WRITE_FAILED") from error


def verify_package(directory: Path) -> dict[str, Any]:
    try:
        _check_path(directory)
        if not directory.is_dir():
            raise PlanError("INVALID_PLAN_PACKAGE")
        entries = list(directory.iterdir())
        if {entry.name for entry in entries} != NAMES:
            raise PlanError("INVALID_PLAN_PACKAGE_FILES")
        files = {}
        for entry in entries:
            _check_path(entry)
            if not stat.S_ISREG(entry.lstat().st_mode):
                raise PlanError("INVALID_PLAN_PACKAGE_FILES")
            limit = MAX_INPUT_BYTES if entry.name == "hypothesis.json" else MAX_ARTIFACT_BYTES
            with entry.open("rb") as stream:
                payload = stream.read(limit + 1)
            if len(payload) > limit:
                raise PlanError("PLAN_ARTIFACT_TOO_LARGE")
            files[entry.name] = payload
        expected, _, report = _files(files["hypothesis.json"])
        if files != expected:
            raise PlanError("PLAN_PACKAGE_MISMATCH")
        return {
            "schema": "m4_compile_only_plan_verification_v1",
            "status": "verified_against_current_compilers",
            "independent_seal_verified": False,
            "report": report,
        }
    except OSError as error:
        raise PlanError("PLAN_PACKAGE_READ_FAILED") from error
