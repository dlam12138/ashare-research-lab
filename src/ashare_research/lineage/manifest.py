"""M2 Stage 1 — 运行级数据血缘 Manifest。"""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path


@dataclass
class ManifestEntry:
    """一次事实构建运行的完整明细。"""
    manifest_schema_version: str = "1.0"
    run_id: str = ""
    job_namespace: str = "ashare-research-lab"
    job_name: str = "build-official-value-facts"
    company_symbol: str = ""
    profile: str = ""
    started_at: str = ""
    completed_at: str = ""
    status: str = "pending"
    git_commit: str = ""
    git_branch: str = ""
    command: str = ""
    config_hash: str = ""
    code_version: str = ""
    input_datasets: list[str] = field(default_factory=list)
    input_sources: list[str] = field(default_factory=list)
    input_source_hashes: dict[str, str] = field(default_factory=dict)
    input_fact_ids: list[str] = field(default_factory=list)
    derivation_definitions: list[str] = field(default_factory=list)
    validation_rule_versions: str = ""
    output_datasets: list[str] = field(default_factory=list)
    output_files: list[str] = field(default_factory=list)
    output_hashes: dict[str, str] = field(default_factory=dict)
    reported_fact_count: int = 0
    derived_fact_count: int = 0
    warning_count: int = 0
    error_count: int = 0
    transaction_committed: bool = False
    failure_stage: str = ""
    reported_error_count: int = 0
    derived_error_count: int = 0
    context_error_count: int = 0
    checkpoint_status: str = ""
    requested_source_mode: str = ""
    source_tiers: list = field(default_factory=list)
    candidate_fact_count: int = 0
    official_fact_count: int = 0
    unverified_fact_count: int = 0
    verified_fact_count: int = 0
    reconciled_fact_count: int = 0
    mismatch_fact_count: int = 0
    fact_schema_version: str = "2.1"
    concept_registry_version: str = "2.0"
    # Store result breakdowns
    reported_requested: int = 0
    reported_inserted: int = 0
    reported_unchanged: int = 0
    reported_conflicts: int = 0
    derived_requested: int = 0
    derived_inserted: int = 0
    derived_unchanged: int = 0
    derived_conflicts: int = 0
    contexts_requested: int = 0
    contexts_inserted: int = 0
    contexts_unchanged: int = 0
    contexts_conflicts: int = 0


class LineageManifest:
    """运行血缘记录器。"""

    def __init__(self, symbol: str = "", profile: str = ""):
        self.entry = ManifestEntry(
            run_id=hashlib.sha256(
                f"{symbol}{datetime.now().isoformat()}".encode()
            ).hexdigest()[:12],
            company_symbol=symbol,
            profile=profile,
            started_at=datetime.now().isoformat(),
        )
        # 尝试获取 git commit
        try:
            import subprocess
            result = subprocess.run(
                ["git", "rev-parse", "--short", "HEAD"],
                capture_output=True, text=True, timeout=5,
            )
            if result.returncode == 0:
                self.entry.git_commit = result.stdout.strip()
            result2 = subprocess.run(
                ["git", "branch", "--show-current"],
                capture_output=True, text=True, timeout=5,
            )
            if result2.returncode == 0:
                self.entry.git_branch = result2.stdout.strip()
        except Exception:
            pass

    def add_input_source(self, name: str, file_hash: str = "") -> None:
        self.entry.input_sources.append(name)
        if file_hash:
            self.entry.input_source_hashes[name] = file_hash

    def add_output_file(
        self, path: str, fact_count: int = 0,
    ) -> None:
        self.entry.output_files.append(path)
        if os.path.exists(path):
            with open(path, "rb") as f:
                self.entry.output_hashes[path] = hashlib.sha256(
                    f.read()
                ).hexdigest()[:16]

    def complete_manifest(
        self, status: str, error_count: int = 0,
        warning_count: int = 0,
    ) -> None:
        self.entry.status = status
        self.entry.error_count = error_count
        self.entry.warning_count = warning_count
        self.entry.completed_at = datetime.now().isoformat()

    def complete_with_details(
        self,
        status: str,
        error_counts: dict | None = None,
        transaction_success: bool = False,
        failure_stage: str = "",
    ) -> None:
        """Complete manifest with granular error detail and
        transaction status.

        Parameters
        ----------
        status:
            Final run status (e.g. "success", "failed", "partial").
        error_counts:
            Dict with optional keys ``reported``, ``derived``,
            ``context``; missing keys default to 0.
        transaction_success:
            Whether the fact transaction was committed.
        failure_stage:
            Stage at which failure occurred, when status != "success".
        """
        self.entry.status = status
        self.entry.completed_at = datetime.now().isoformat()
        if error_counts is None:
            error_counts = {}
        self.entry.reported_error_count = error_counts.get("reported", 0)
        self.entry.derived_error_count = error_counts.get("derived", 0)
        self.entry.context_error_count = error_counts.get("context", 0)
        total = (
            self.entry.reported_error_count
            + self.entry.derived_error_count
            + self.entry.context_error_count
        )
        self.entry.error_count = total
        self.entry.transaction_committed = transaction_success
        self.entry.failure_stage = failure_stage

    def to_dict(self) -> dict:
        """转为 JSON 可序列化字典。"""
        d = {}
        for key, value in self.entry.__dict__.items():
            if isinstance(value, datetime):
                d[key] = value.isoformat()
            else:
                d[key] = value
        return d

    def _project_root(self) -> Path:
        """Return the project root directory (cached)."""
        if hasattr(self, "_cached_project_root"):
            return self._cached_project_root  # type: ignore[attr-defined]
        # Try git first.
        try:
            import subprocess
            result = subprocess.run(
                ["git", "rev-parse", "--show-toplevel"],
                capture_output=True, text=True, timeout=5,
            )
            if result.returncode == 0:
                root = Path(result.stdout.strip())
                self._cached_project_root = root  # type: ignore[attr-defined]
                return root
        except Exception:
            pass
        # Fallback: assume this file is at <root>/src/ashare_research/lineage/manifest.py
        root = Path(__file__).resolve().parents[3]
        self._cached_project_root = root  # type: ignore[attr-defined]
        return root

    @staticmethod
    def _rel_path(absolute: str, root: Path) -> str:
        """Convert an absolute path to a project-relative one.

        If the path is already relative or not under *root* it is
        returned unchanged.
        """
        try:
            p = Path(absolute)
            if not p.is_absolute():
                return absolute
            return str(p.resolve().relative_to(root)).replace("\\", "/")
        except (ValueError, OSError):
            return absolute

    def write_manifest(self, path: str | Path) -> str:
        """原子写入 manifest JSON（路径转为项目相对路径）。"""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        root = self._project_root()
        data = self.to_dict()

        # Strip paths in list/dict fields that carry file paths.
        for list_key in ("output_files", "output_datasets",
                         "input_sources", "input_datasets"):
            if list_key in data and isinstance(data[list_key], list):
                data[list_key] = [
                    self._rel_path(p, root) if isinstance(p, str) else p
                    for p in data[list_key]
                ]
        for dict_key in ("output_hashes", "input_source_hashes"):
            if dict_key in data and isinstance(data[dict_key], dict):
                data[dict_key] = {
                    self._rel_path(k, root) if isinstance(k, str) else k: v
                    for k, v in data[dict_key].items()
                }

        tmp_path = path.parent / f".{path.name}.tmp"
        try:
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2,
                          ensure_ascii=False, sort_keys=True)
            os.replace(tmp_path, str(path))
        except Exception:
            if tmp_path.exists():
                tmp_path.unlink()
            raise

        return str(path)
