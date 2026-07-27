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

    def to_dict(self) -> dict:
        """转为 JSON 可序列化字典。"""
        d = {}
        for key, value in self.entry.__dict__.items():
            if isinstance(value, datetime):
                d[key] = value.isoformat()
            else:
                d[key] = value
        return d

    def write_manifest(self, path: str | Path) -> str:
        """原子写入 manifest JSON。"""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        tmp_path = path.parent / f".{path.name}.tmp"
        try:
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(self.to_dict(), f, indent=2,
                          ensure_ascii=False, sort_keys=True)
            os.replace(tmp_path, str(path))
        except Exception:
            if tmp_path.exists():
                tmp_path.unlink()
            raise

        return str(path)
